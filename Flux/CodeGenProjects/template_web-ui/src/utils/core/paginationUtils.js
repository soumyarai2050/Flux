import { get } from 'lodash';

/**
 * @fileoverview Pagination utilities for server-side data fetching with filter support
 * This module provides functions to process UI filters, sort orders, and pagination
 * parameters into the format expected by the backend APIs.
 */

/**
 * Converts a string value to its appropriate data type (number, boolean, or string)
 * @param {string} val - The string value to convert
 * @returns {number|boolean|string} The value converted to its appropriate type
 */
function convertToAppropriateType(val) {
  // Handle empty or null values
  if (val === null || val === undefined || val === '') {
    return val;
  }

  // Convert to string for processing (in case it's not already)
  const stringVal = String(val).trim();

  // Check for boolean values first (case-insensitive)
  const lowerVal = stringVal.toLowerCase();
  if (lowerVal === 'true') {
    return true;
  }
  if (lowerVal === 'false') {
    return false;
  }

  // Check if it's a valid number (including decimals, negatives, etc.)
  const num = Number(stringVal);
  if (!isNaN(num) && stringVal !== '' && !isNaN(parseFloat(stringVal)) && isFinite(num)) {
    return num;
  }

  // If it's neither boolean nor number, return as string
  return stringVal;
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

    // Handle filtered_values - ensure it's an  and preserve numeric types
    if (filter.filtered_values !== undefined && filter.filtered_values !== null) {
      if (Array.isArray(filter.filtered_values)) {
        processedFilter.filtered_values = filter.filtered_values;
      } else if (typeof filter.filtered_values === 'string') {
        // Split comma-separated values and convert to appropriate types
        const values = filter.filtered_values.split(',').map(val => val.trim()).filter(val => val.length > 0);

        // Convert each value to its appropriate type (number, boolean, or string)
        processedFilter.filtered_values = values.map(convertToAppropriateType);
      } else {
        // Convert single value to array, preserving type
        processedFilter.filtered_values = [convertToAppropriateType(filter.filtered_values)];
      }
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
      // Direct value - use as-is, convert to appropriate type
      value = convertToAppropriateType(paramConfig.value);
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

    if (paramConfig.type === 'src') {
      // Derived value - fetch from dataSource
      if (!dataSourceStoredObj || Object.keys(dataSourceStoredObj).length === 0) {
        return; // Skip this param if dataSource is not available
      }
      paramValue = get(dataSourceStoredObj, paramConfig.value);
    } else if (paramConfig.type === 'val') {
      // Direct value - use as-is, convert to appropriate type
      paramValue = convertToAppropriateType(paramConfig.value);
    }

    if (paramValue !== null && paramValue !== undefined) {
      extractedParams[key] = paramValue;
    }
  });

  return Object.keys(extractedParams).length > 0 ? extractedParams : null;
}