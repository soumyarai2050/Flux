
/**
 * Extracts relevant error details from an error object, particularly for Axios-like error responses.
 * @param {Object} error - The error object, which may contain `code`, `message`, and `response` properties.
 * @param {string} [error.code] - The error code.
 * @param {string} [error.message] - The error message.
 * @param {Object} [error.response] - The HTTP response object, if the error originated from an HTTP request.
 * @param {Object} [error.response.data] - The data payload from the HTTP response.
 * @param {string} [error.response.data.detail] - A detailed error message from the response data.
 * @param {number} [error.response.status] - The HTTP status code from the response.
 * @returns {Object} An object containing extracted error details: `code`, `message`, `detail`, and `status`.
 */
export function getErrorDetails(error) {
    return {
        code: error.code,
        message: error.message,
        detail: error.response ? (error.response.data ? error.response.data.detail : '') : '',
        status: error.response ? error.response.status : ''
    };
}

/**
 * Defines standard error messages for common validation scenarios.
 * @enum {string}
 */
export const Message = {
    /** Message for fields that are required but found to be null. */
    REQUIRED_FIELD: 'required field cannot be null',
    /** Message for required enum fields that are unset or unspecified. */
    UNSPECIFIED_FIELD: 'required enum field cannot be unset / UNSPECIFIED',
    /** Message for field values that exceed the maximum allowed limit. */
    MAX: 'field value exceeds the max limit',
    /** Message for field values that are below the minimum allowed limit. */
    MIN: 'field value exceeds the min limit'
};
