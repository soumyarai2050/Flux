import { get } from 'lodash';
import axios from 'axios';
import { API_ROOT_VIEW_URL, API_ROOT_URL } from '../../constants';
import { getWebSocketConnection } from '../../cache/websocketConnectionCache';

/**
 * Constructs a server URL based on widget schema, linked object data, and request type.
 * This function dynamically builds HTTP or WebSocket URLs, considering dynamic host/port configurations
 * and server readiness status.
 * @param {Object} widgetSchema - The schema of the widget, containing connection details and UI data elements.
 * @param {Object} linkedObj - The linked object data, used for dynamic host/port resolution.
 * @param {Array<Object>} linkedFieldsMetadata - Metadata for linked fields, used to find server readiness status.
 * @param {string} [requestType='http'] - The type of request ('http' or 'ws').
 * @param {boolean} [isViewUrl=false] - If true, constructs a view URL; otherwise, a regular API URL.
 * @returns {string|null} The constructed server URL, or `null` if the URL cannot be determined (e.g., server not ready, missing dynamic values).
 */
export function getServerUrl(widgetSchema, linkedObj, linkedFieldsMetadata, requestType = 'http', isViewUrl = false) {
    if (widgetSchema.connection_details) {
        const connectionDetails = widgetSchema.connection_details;
        const { host, port, view_port, project_name } = connectionDetails;

        // Set url only if linkedObj running field is set to true for dynamic as well as static
        if (widgetSchema.widget_ui_data_element?.depending_proto_model_name) {
            const serverReadyStatusFld = linkedFieldsMetadata?.find(col => col.hasOwnProperty('server_ready_status')).key;
            const requiredStateLvl = widgetSchema.widget_ui_data_element.server_running_status_lvl || 0;

            // Check if the linked object exists and its server readiness status meets the requirement.
            if (linkedObj && Object.keys(linkedObj).length && get(linkedObj, serverReadyStatusFld) >= requiredStateLvl) {
                if (connectionDetails.dynamic_url) {
                    // Resolve dynamic host and port from the linked object.
                    const hostxpath = host.substring(host.indexOf('.') + 1);
                    const portFld = isViewUrl ? view_port : port;
                    const portxpath = portFld.substring(port.indexOf('.') + 1);
                    const hostVal = get(linkedObj, hostxpath);
                    const portVal = get(linkedObj, portxpath);

                    if (!hostVal || !portVal) return null; // Cannot construct URL without host or port.

                    // Construct URL based on request type.
                    if (requestType === 'http') {
                        if (widgetSchema.widget_ui_data_element?.depending_proto_model_for_cpp_port) {
                            return `http://${hostVal}:${portVal}`;
                        }
                        return `http://${hostVal}:${portVal}/${project_name}`;
                    } else if (requestType === 'ws') {
                        if (widgetSchema.widget_ui_data_element?.depending_proto_model_for_cpp_port) {
                            return `ws://${hostVal}:${portVal}`;
                        }
                        return `ws://${hostVal}:${portVal}/${project_name}`;
                    } else {
                        const err_ = `getServerUrl failed, unsupported ${jsonify(requestType)}. allowed [http, ws]`;
                        console.error(err_);
                    }
                } else {
                    // Handle static URL for dynamic connection details.
                    const portVal = isViewUrl ? view_port : port;
                    return `http://${host}:${portVal}/${project_name}`;
                }
            }
        } else {
            // Handle cases without `depending_proto_model_name` or when server is not ready.
            const portVal = isViewUrl ? view_port : port;
            return `http://${host}:${portVal}/${project_name}`;
        }
    }
    // Fallback to global API root URLs if no connection details are provided in the schema.
    else {
        return isViewUrl ? API_ROOT_VIEW_URL : API_ROOT_URL;
    }
    return null;
}

/**
 * Returns the appropriate Axios HTTP method function based on the provided query route type.
 * @param {string} queryRouteType - The type of HTTP query route (e.g., 'get', 'post', 'patch'). Case-insensitive.
 * @returns {Function} The corresponding Axios method (e.g., `axios.get`, `axios.post`).
 * @throws {Error} If an unsupported `queryRouteType` is provided.
 */
export function getAxiosMethod(queryRouteType) {
    switch (queryRouteType.toLowerCase()) {
        case 'get':
            return axios.get;
        case 'post':
            return axios.post;
        case 'patch':
            return axios.patch;
        default:
            throw new Error(`Unsupported queryRouteType: ${queryRouteType}`);
    }
}

/**
 * Checks if a WebSocket connection is active (i.e., in the OPEN state).
 * Can check a provided WebSocket object directly or retrieve it from a cache using a model name.
 * If a composite key (e.g., "dash-115") is not found in the cache, it will fallback to checking
 * the base model name (e.g., "dash") before returning false.
 * @param {WebSocket} webSocket - The WebSocket object to check.
 * @param {string} [modelName=null] - Optional. The name of the model to retrieve the WebSocket connection from the cache.
 * @returns {boolean} True if the WebSocket connection is active and open, false otherwise.
 */
export function isWebSocketActive(webSocket, modelName = null) {
    let websocketToCheck = webSocket;
    // If a modelName is provided, retrieve the WebSocket connection from the cache.
    if (modelName) {
        websocketToCheck = getWebSocketConnection(modelName);

        // If composite key not found , try base model name
        if (!websocketToCheck && modelName.includes('-')) {
            const baseModelName = modelName.substring(0, modelName.lastIndexOf('-'));
            websocketToCheck = getWebSocketConnection(baseModelName);
        }
    }
    // If a WebSocket object is available, check its readyState.
    if (websocketToCheck) {
        if (websocketToCheck.readyState === WebSocket.OPEN) {
            return true;
        }
    }
    return false;
}

/**
 * Converts an object to a JSON string. This is a helper function primarily used for error logging.
 * @param {Object} obj - The object to convert to a JSON string.
 * @returns {string} The JSON string representation of the object.
 */
function jsonify(obj) {
    return JSON.stringify({ obj });
}

/**
 * Utility function to build API URL and parameters.
 * It constructs the full API URL by combining a base URL and an endpoint,
 * and adds a `limit_obj_count` parameter if `uiLimit` is provided.
 * @param {string} defaultEndpoint - The default endpoint string (e.g., 'data', 'config').
 * @param {string} overrideUrl - Optional. A URL to override the default base URL (API_ROOT_URL or API_ROOT_VIEW_URL).
 * @param {string} overrideEndpoint - Optional. An endpoint to override the `defaultEndpoint`.
 * @param {Object} params - Additional parameters to be included in the API request.
 * @param {boolean} [isViewUrl=false] - If true, uses `API_ROOT_VIEW_URL` as the base URL; otherwise, `API_ROOT_URL`.
 * @param {number} [uiLimit=null] - The UI limit for the number of items to retrieve. If provided, it's added as `limit_obj_count` to parameters.
 * @returns {[string, Object]} A tuple containing the constructed API URL and the parameters object.
 */
export function getApiUrlMetadata(defaultEndpoint, overrideUrl, overrideEndpoint, params, isViewUrl = false, uiLimit = null) {
    const baseUrl = overrideUrl || (isViewUrl ? API_ROOT_VIEW_URL : API_ROOT_URL);
    const baseEndpoint = overrideEndpoint || defaultEndpoint;
    const apiUrl = `${baseUrl}/${baseEndpoint}`;
    const apiParams = params ? { ...params } : {};
    // If uiLimit is provided, add it as 'limit_obj_count' to the parameters.
    if (uiLimit) {
        apiParams['limit_obj_count'] = uiLimit;
    }
    return [apiUrl, apiParams];
}
