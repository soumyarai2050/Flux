import { get } from 'lodash';
import { MODEL_TYPES } from '../../constants';

/**
 * @fileoverview Pagination utilities for server-side data fetching with filter support
 * This module provides functions to process UI filters, sort orders, and pagination
 * parameters into the format expected by the backend APIs.
 */

/**
 * Converts a value to its appropriate data type based on schema's underlyingType
 * @param {string} val - The value to convert
 * @param {string} underlyingType - The underlying type from schema (e.g., 'string', 'int32', 'int64', 'float', 'double', 'bool')
 * @returns {number|boolean|string} The value converted to its schema-defined type
 */
export function convertToAppropriateType(val, underlyingType) {
  // Handle empty or null values
  if (val === null || val === undefined || val === '') {
    return val;
  }

  // Convert to string for processing (in case it's not already)
  const stringVal = String(val).trim();

  // Convert based on schema's underlyingType
  switch (underlyingType) {
    case 'string':
      return stringVal;

    case 'bool':
    case 'boolean':
      // Case-insensitive boolean conversion
      const lowerVal = stringVal.toLowerCase();
      if (lowerVal === 'true') return true;
      if (lowerVal === 'false') return false;
      return stringVal; // Return as-is if not valid boolean

    case 'int32':
    case 'int64':
    case 'integer':
      const intVal = parseInt(stringVal, 10);
      return !isNaN(intVal) ? intVal : stringVal;

    case 'float':
    case 'double':
    case 'number':
      const floatVal = parseFloat(stringVal);
      return !isNaN(floatVal) ? floatVal : stringVal;

    default:
      // If underlyingType is not recognized, return as string
      return stringVal;
  }
}

/**
 * Converts filter values from strings to their appropriate data types based on schema metadata.
 * This is intended to be used once at the container level to ensure
 * filters have the correct types before being passed to child components.
 *
 * @param {Array} filters - Array of filter objects, where filtered_values is a string.
 * @param {Array} fieldsMetadata - Array of field metadata objects containing underlyingtype information.
 * @returns {Array} A new array of filter objects with typed filtered_values.
 */
export function convertFilterTypes(filters, fieldsMetadata, modelType) {
  if (!filters) {
    return [];
  }

  return filters.map(filter => {
    // Determine how to match field metadata based on model type
    const matchField = (modelType === MODEL_TYPES.ABBREVIATION_MERGE)
      ? fieldsMetadata?.find(f => f.key === filter.column_name)
      : fieldsMetadata?.find(f => f.tableTitle === filter.column_name);

    const underlyingType = matchField?.underlyingtype || matchField?.type;

    const convertedFilter = {
      ...filter,
      filtered_values:
        filter.filtered_values
          ?.split(',')
          .map(val => convertToAppropriateType(val, underlyingType)) ?? null
    };
     //placeholder code to convert text filter also to appropriate type
    // Also convert text_filter to appropriate type if it exists
    // if (filter.text_filter !== undefined && filter.text_filter !== null && filter.text_filter !== '') {
    //   convertedFilter.text_filter = convertToAppropriateType(filter.text_filter, underlyingType);
    // }

    return convertedFilter;
  });
}


/**
 * Processes UI filters, sort orders, and pagination parameters for backend consumption
 * @param {Array} filters - Array of filter objects from modelLayoutOption.filters
 * @param {Array} sortOrders - Array of sort order objects from modelLayoutData.sort_orders
 * @param {number} page - Current page (0-indexed from UI)
 * @param {number} rowsPerPage - Number of rows per page
 * @returns {Object} Processed data for backend APIs
 */
export function massageDataForBackend(filters = [], sortOrders = [], page = 0, rowsPerPage = 25) {
  // 1. Process filters - convert UI format to backend format
  const processedFilters = filters.map(filter => {
    const processedFilter = {
      column_name: filter.column_name
    };

    // Handle filtered_values - filters are already type-converted at container level
    // Just ensure it's an array format
    if (filter.filtered_values !== undefined && filter.filtered_values !== null) {
      processedFilter.filtered_values = Array.isArray(filter.filtered_values)
        ? filter.filtered_values
        : [filter.filtered_values];
    }

    // Handle text filter
    if (filter.text_filter !== undefined && filter.text_filter !== null && filter.text_filter !== '') {
      processedFilter.text_filter = filter.text_filter;
    }

    // Handle text filter type
    if (filter.text_filter_type !== undefined && filter.text_filter_type !== null && filter.text_filter_type !== '') {
      processedFilter.text_filter_type = filter.text_filter_type;
    }

    return processedFilter;
  });

  // 2. Process sort orders - ensure correct format
  const processedSortOrders = sortOrders.map(sort => {
    const processedSort = {
      sort_by: sort.sort_by
    };

    // Convert sort direction to numeric format
    if (typeof sort.sort_direction === 'string') {
      processedSort.sort_direction = sort.sort_direction.toLowerCase() === 'asc' ? 1 : -1;
    } else if (typeof sort.sort_direction === 'number') {
      processedSort.sort_direction = sort.sort_direction;
    } else {
      // Default to ascending
      processedSort.sort_direction = 1;
    }

    // Handle absolute sort flag
    processedSort.is_absolute_sort = sort.is_absolute_sort || false;

    return processedSort;
  });

  // 3. Process pagination - convert to backend format
  const processedPagination = {
    page_number: page + 1, // UI is 0-indexed, backend expects 1-indexed
    page_size: rowsPerPage
  };

  return {
    filters: processedFilters,
    sortOrders: processedSortOrders,
    pagination: processedPagination
  };
}

/**
 * Builds query parameters for HTTP count queries
 * @param {Array} filters - Raw filters array from UI
 * @returns {URLSearchParams} Query parameters for count endpoint
 */
export function buildCountQueryParams(filters = []) {
  const params = new URLSearchParams();

  // Process filters to ensure proper data types (same as WebSocket)
  const processedData = massageDataForBackend(filters, [], 0, 25);

  // Only add filters if they exist and are not empty
  if (processedData.filters && processedData.filters.length > 0) {
    params.append('filters', JSON.stringify(processedData.filters));
  }

  return params;
}

/**
 * Builds query parameters for WebSocket queries - dynamically omits empty/null params
 * @param {Array} filters - Raw filters array from UI
 * @param {Array} sortOrders - Raw sort orders array from UI
 * @param {Object|null} pagination - Processed pagination object (null to omit) - for server-side pagination
 * @param {number|null} uiLimit - Client-side limit for non-paginated models (null to omit)
 * @param {boolean} isCppModel - Whether this is a C++ model
 * @returns {URLSearchParams} Query parameters for WebSocket endpoint
 */
export function buildWebSocketQueryParams(filters = [], sortOrders = [], pagination = null, uiLimit = null, isCppModel = false) {
  const params = new URLSearchParams();

  // Process filters and sort orders to ensure proper data types
  const processedData = massageDataForBackend(filters, sortOrders, 0, 25);

  // Only add filters if they exist and are not empty
  if (processedData.filters && processedData.filters.length > 0) {
    params.append('filters', JSON.stringify(processedData.filters));
  }

  // Only add sort orders if they exist and are not empty
  if (processedData.sortOrders && processedData.sortOrders.length > 0) {
    params.append('sort_order', JSON.stringify(processedData.sortOrders));
  }

  // Server-side pagination (takes priority)
  if (pagination) {
    params.append('pagination', JSON.stringify(pagination));
  }
  // Client-side limit (only when pagination is not used)
  // Note: uiLimit will already be null if server-side pagination is enabled
  // C++ models don't support limit_obj_count parameter
  else if (uiLimit && uiLimit > 0 && !isCppModel) {
    params.append('limit_obj_count', uiLimit);
  }

  return params;
}

/**
 * Determines if pagination should be applied based on total count and page size
 * @param {number} totalCount - Total number of records
 * @param {number} pageSize - Number of records per page
 * @returns {boolean} Whether pagination should be applied
 */
export function shouldUsePagination(totalCount, pageSize) {
  return totalCount > pageSize;
}

/**
 * Creates the count endpoint URL for a given model
 * @param {string} apiRoot - API root URL
 * @param {string} modelName - Model name
 * @returns {string} Count endpoint URL
 */
export function createCountEndpoint(apiRoot, modelName) {
  return `${apiRoot}/query-${modelName}_filtered_count`;
}

/**
 * Creates the WebSocket paginated query endpoint for a given model  -get all
 * @param {string} wsRoot - WebSocket root URL
 * @param {string} modelName - Model name
 * @returns {string} WebSocket endpoint URL
 */
export function createWebSocketPaginatedEndpoint(wsRoot, modelName) {
  return `${wsRoot}/get-all-${modelName}-ws`;
}

/**
 * Creates the WebSocket count endpoint URL for a given model
 * @param {string} wsRoot - WebSocket root URL
 * @param {string} modelName - Model name
 * @returns {string} WebSocket count endpoint URL
 */
export function createCountWebSocketEndpoint(wsRoot, modelName) {
  return `${wsRoot}/ws-query-${modelName}_filtered_count`;
}

/**
 * Builds default filters from dataSource using defaultFilterParamDict
 * Used in processedData useMemo to merge with UI filters
 *
 * @param {Object|null} dataSourceStoredObj - Stored object from dataSource selector
 * @param {Object|null} defaultFilterParamDict - Default filter param dict from model schema
 * @returns {Array} Array of filter objects [{column_name, filtered_values}]
 */
export function buildDefaultFilters(dataSourceStoredObj, defaultFilterParamDict) {
  const filters = [];

  if (!defaultFilterParamDict || Object.keys(defaultFilterParamDict).length === 0) {
    return filters;
  }

  Object.entries(defaultFilterParamDict).forEach(([key, paramConfig]) => {
    let value;

    if (paramConfig.type === 'src') {
      // Derived value - fetch from dataSource
      if (!dataSourceStoredObj || Object.keys(dataSourceStoredObj).length === 0) {
        return; // Skip this filter if dataSource is not available
      }
      value = get(dataSourceStoredObj, paramConfig.value);
    } else if (paramConfig.type === 'val') {
      value = paramConfig.value;
    }

    if (value !== null && value !== undefined) {
      filters.push({
        column_name: key,
        filtered_values: Array.isArray(value) ? value : [value]
      });
    }
  });

  return filters;
}

/**
 * Extracts params from dataSource using crudOverrideDict
 * Used in useEffect to build query params for custom CRUD endpoints
 *
 * Note: paramDict values are plain strings (field paths), not objects with type/value.
 * This is because ui_query_param in the schema only supports query_param_value_src (string),
 * unlike default_filter_param which supports both param_value_src and param_value.
 *
 * @param {Object|null} dataSourceStoredObj - Stored object from dataSource selector
 * @param {Object|null} crudOverrideDict - CRUD override dict from model schema
 * @param {Function} get - Lodash get function for nested property access
 * @returns {Object|null} Params object for query string, or null if none extracted
 */
export function extractCrudParams(dataSourceStoredObj, crudOverrideDict) {
  if (!crudOverrideDict?.GET_ALL) {
    return null;
  }

  const { paramDict } = crudOverrideDict.GET_ALL;
  if (!paramDict || Object.keys(paramDict).length === 0) {
    return null;
  }

  let extractedParams = {};
  Object.keys(paramDict).forEach((key) => {
    const paramConfig = paramDict[key];
    let paramValue;

    // Handle both object format {type: 'src', value: 'field'} and string format 'field'
    if (typeof paramConfig === 'string') {
      // String format - treat as 'src' type (derived from dataSource)
      if (!dataSourceStoredObj || Object.keys(dataSourceStoredObj).length === 0) {
        return; // Skip this param if dataSource is not available
      }
      paramValue = get(dataSourceStoredObj, paramConfig);
    } else if (paramConfig.type === 'src') {
      // Object format with 'src' type - derived value
      if (!dataSourceStoredObj || Object.keys(dataSourceStoredObj).length === 0) {
        return; // Skip this param if dataSource is not available
      }
      paramValue = get(dataSourceStoredObj, paramConfig.value);
    } else if (paramConfig.type === 'val') {
      // Object format with 'val' type - direct value
      paramValue = paramConfig.value;
    }

    if (paramValue !== null && paramValue !== undefined) {
      extractedParams[key] = paramValue;
    }
  });

  return Object.keys(extractedParams).length > 0 ? extractedParams : null;
}