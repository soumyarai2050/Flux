/**
 * @module parameterBindingUtils
 * @description Utilities for automatic parameter binding in query operations based on FluxFldQueryParamBind annotations.
 */

/**
 * Creates auto-bound parameters by extracting field values that have query_param_bind annotations.
 * @param {Array} fieldsMetadata - Array of field metadata objects containing query_param_bind properties.
 * @param {Object} currentData - The current object/form data to extract field values from.
 * @returns {Object} An object mapping query parameter names to their auto-bound values.
 * @example
 * const fieldsMetadata = [
 *   { xpath: "id", query_param_bind: "order_id", type: "string" },
 *   { xpath: "user_id", query_param_bind: "user_id", type: "string" },
 *   { xpath: "symbol", type: "string" }  // No query_param_bind
 * ];
 * const currentData = { id: "ORDER_123", user_id: "USER_456", symbol: "AAPL" };
 * const result = createAutoBoundParams(fieldsMetadata, currentData);
 * // Result: { order_id: "ORDER_123", user_id: "USER_456" }
 */
export const createAutoBoundParams = (fieldsMetadata, currentData) => {
    if (!fieldsMetadata || !currentData) {
        return {};
    }

    const autoBound = {};

    fieldsMetadata.forEach(fieldMeta => {
        // Check if field has query_param_bind property and current data has a value for this field
        if (fieldMeta.query_param_bind && fieldMeta.xpath &&
            currentData[fieldMeta.xpath] !== undefined && currentData[fieldMeta.xpath] !== null) {
            const paramName = fieldMeta.query_param_bind;
            autoBound[paramName] = currentData[fieldMeta.xpath];
        }
    });

    return autoBound;
};

/**
 * Filters query parameters to return only those that are not auto-bound.
 * @param {Array} queryParams - Array of query parameter definitions from schema.
 * @param {Object} autoBoundParams - Object containing auto-bound parameter names as keys.
 * @returns {Object} Object containing only user-editable parameters with their type information.
 * @example
 * const queryParams = [
 *   { QueryParamName: "order_id", QueryParamDataType: "str" },
 *   { QueryParamName: "user_id", QueryParamDataType: "str" },
 *   { QueryParamName: "reason", QueryParamDataType: "str" }
 * ];
 * const autoBoundParams = { order_id: "ORDER_123", user_id: "USER_456" };
 * const result = getEditableParams(queryParams, autoBoundParams);
 * // Result: { reason: { type: "str" } }
 */
export const getEditableParams = (queryParams = [], autoBoundParams = {}) => {
    return queryParams
        .filter(param => !autoBoundParams.hasOwnProperty(param.QueryParamName))
        .reduce((acc, param) => {
            acc[param.QueryParamName] = {
                type: param.QueryParamDataType || 'str'
            };
            return acc;
        }, {});
};

/**
 * Merges auto-bound parameters with user-provided parameters for query execution.
 * User-provided parameters take precedence over auto-bound ones in case of conflicts.
 * @param {Object} autoBoundParams - Parameters automatically bound from field values.
 * @param {Object} userParams - Parameters provided by user input.
 * @returns {Object} Merged parameters object ready for query execution.
 * @example
 * const autoBoundParams = { order_id: "ORDER_123", user_id: "USER_456" };
 * const userParams = { reason: "Customer request", priority: "high" };
 * const result = mergeQueryParams(autoBoundParams, userParams);
 * // Result: { order_id: "ORDER_123", user_id: "USER_456", reason: "Customer request", priority: "high" }
 */
export const mergeQueryParams = (autoBoundParams = {}, userParams = {}) => {
    return {
        ...autoBoundParams,
        ...userParams  // User params override auto-bound params if there's a conflict
    };
};

/**
 * Validates that all required query parameters are provided either through auto-binding or user input.
 * @param {Array} requiredParams - Array of required parameter names.
 * @param {Object} finalParams - Final merged parameters object.
 * @returns {Object} Validation result with isValid boolean and missing parameter names.
 * @example
 * const requiredParams = ["order_id", "user_id", "reason"];
 * const finalParams = { order_id: "ORDER_123", user_id: "USER_456" };
 * const result = validateRequiredParams(requiredParams, finalParams);
 * // Result: { isValid: false, missingParams: ["reason"] }
 */
export const validateRequiredParams = (requiredParams = [], finalParams = {}) => {
    const missingParams = requiredParams.filter(param =>
        finalParams[param] === undefined || finalParams[param] === null || finalParams[param] === ''
    );

    return {
        isValid: missingParams.length === 0,
        missingParams
    };
};

/**
 * Gets a summary of parameter binding for debugging or user feedback.
 * @param {Object} autoBoundParams - Auto-bound parameters.
 * @param {Object} userParams - User-provided parameters.
 * @param {Object} schema - Schema to get field name mappings.
 * @returns {Object} Summary object with parameter source information.
 */
export const getParameterBindingSummary = (autoBoundParams = {}, userParams = {}, schema = {}) => {
    const summary = {
        autoBound: [],
        userProvided: [],
        total: 0
    };

    // Find source field names for auto-bound parameters
    const properties = schema.properties || {};
    const paramToFieldMap = {};

    Object.entries(properties).forEach(([fieldName, fieldDef]) => {
        if (fieldDef?.query_param_bind) {
            paramToFieldMap[fieldDef.query_param_bind] = fieldName;
        }
    });

    // Categorize auto-bound parameters
    Object.entries(autoBoundParams).forEach(([paramName, value]) => {
        summary.autoBound.push({
            paramName,
            value,
            sourceField: paramToFieldMap[paramName] || 'unknown'
        });
    });

    // Categorize user-provided parameters
    Object.entries(userParams).forEach(([paramName, value]) => {
        summary.userProvided.push({
            paramName,
            value
        });
    });

    summary.total = summary.autoBound.length + summary.userProvided.length;

    return summary;
};