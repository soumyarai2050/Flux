const connectionCache = new Map(); // modelName -> WebSocket connection

/**
 * @function setWebSocketConnection
 * @description Stores a WebSocket connection in the cache associated with a model name.
 * For BY-ID mode, use composite key format: `${modelName}-${id}`
 * @param {string} modelName - The name of the model (or composite key for BY-ID mode).
 * @param {WebSocket} ws - The WebSocket connection object.
 */
export const setWebSocketConnection = (modelName, ws) => {
    connectionCache.set(modelName, ws);
};

/**
 * @function getWebSocketConnection
 * @description Retrieves a WebSocket connection from the cache by model name.
 * For BY-ID mode, use composite key format: `${modelName}-${id}`
 * @param {string} modelName - The name of the model (or composite key for BY-ID mode).
 * @returns {WebSocket|undefined} The WebSocket connection object, or undefined if not found.
 */
export const getWebSocketConnection = (modelName) => {
    return connectionCache.get(modelName);
};

/**
 * @function clearWebSocketConnection
 * @description Clears a specific WebSocket connection from the cache, or all connections if no model name is provided.
 * For BY-ID mode, use composite key format: `${modelName}-${id}`
 * @param {string} [modelName] - The name of the model (or composite key for BY-ID mode) whose connection should be cleared. If omitted, all connections are cleared.
 */
export const clearWebSocketConnection = (modelName) => {
    if (modelName) {
        connectionCache.delete(modelName);
    } else {
        connectionCache.clear();
    }
};