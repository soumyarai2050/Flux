const connectionCache = new Map(); // modelName -> WebSocket connection

// Setter
export const setWebSocketConnection = (modelName, ws) => {
    connectionCache.set(modelName, ws);
};

// Getter
export const getWebSocketConnection = (modelName) => {
    return connectionCache.get(modelName);
};

// Clear a specific connection or all connections
export const clearWebSocketConnection = (modelName) => {
    if (modelName) {
        connectionCache.delete(modelName);
    } else {
        connectionCache.clear();
    }
};