import axios from "axios";
import { NODE_DATA_SCHEMAS } from "./MockData";
import { API_ROOT_URL } from "../config";
import { createCollections, getModelSchema, getServerUrl } from "../utils";



/**
 * Generate simple analysed data by combining selected columns from both entities
 * @param {Object} sourceNodeData - Source node data from cache
 * @param {Object} targetNodeData - Target node data from cache 
 * @param {Object} joinInfo - Join information (optional)
 * @returns {Object} Analysed data with selected columns from both nodes
 */



function generateAnalysedData(sourceNodeData, targetNodeData, joinInfo = null) {
    if (!sourceNodeData || !targetNodeData) {
        throw new Error('Missing required node data for analysis');
    }

    const sourceData = sourceNodeData.sample_data || [];
    const targetData = targetNodeData.sample_data || [];
    const sourceColumns = sourceNodeData.columns || [];
    const targetColumns = targetNodeData.columns || [];

    // Select subset of columns from each node (3 from source, 2 from target)
    const selectedSourceColumns = sourceColumns.slice(0, 3).map(col => col.name);
    const selectedTargetColumns = targetColumns.slice(0, 2).map(col => col.name);

    // Combine the data
    const analysedData = [];
    const maxRecords = Math.min(sourceData.length, targetData.length, 5); // Limit to 5 records for demo

    for (let i = 0; i < maxRecords; i++) {
        const sourceRecord = sourceData[i] || {};
        const targetRecord = targetData[i] || {};
        const combinedRecord = {};

        // Add selected columns from source node
        selectedSourceColumns.forEach(colName => {
            if (sourceRecord.hasOwnProperty(colName)) {
                combinedRecord[colName] = sourceRecord[colName];
            }
        });

        // Add selected columns from target node
        selectedTargetColumns.forEach(colName => {
            if (targetRecord.hasOwnProperty(colName)) {
                combinedRecord[colName] = targetRecord[colName];
            }
        });

        analysedData.push(combinedRecord);
    }

    // Create combined column definitions
    const analysedColumns = [
        ...sourceColumns.slice(0, 3),
        ...targetColumns.slice(0, 2)
    ];

    return {
        source_node: sourceNodeData.node_name,
        target_node: targetNodeData.node_name,
        analysed_columns: analysedColumns,
        analysed_data: analysedData,
        record_count: analysedData.length,
        generated_at: new Date().toISOString()
    };
}

/**
 * Fetch analysed data combining two entities
 * @param {Object} sourceNode - Source node object with entity_base_url and name
 * @param {Object} targetNode - Target node object with entity_base_url and name  
 * @param {Object} joinInfo - Join information (optional)
 * @returns {Promise<Object>} Promise resolving to analysed data
 */
export async function fetchAnalysedData(sourceNode, targetNode, joinInfo = null) {
    if (!sourceNode || !targetNode) {
        throw new Error('Both source and target nodes are required for analysis');
    }

    try {
        // Check if both entities have cached data, if not fetch them
        let sourceNodeData = nodeCache.getCached(sourceNode.name);
        let targetNodeData = nodeCache.getCached(targetNode.name);

        // Fetch missing node data
        if (!sourceNodeData) {
            sourceNodeData = await fetchNodeData(sourceNode);
        }

        if (!targetNodeData) {
            targetNodeData = await fetchNodeData(targetNode);
        }

        // Generate and return analysed data
        const analysedResult = generateAnalysedData(sourceNodeData, targetNodeData, joinInfo);

        return {
            ...analysedResult,
            status: 'success'
        };

    } catch (error) {
        console.error('Error fetching analysed data:', error);
        throw new Error(`Failed to generate analysed data: ${error.message}`);
    }
}

/**
 * In-memory cache for node data
 * Structure: Map<node_base_url, { data, timestamp, loading }>
 */
class NodeDataCache {
    constructor() {
        this.cache = new Map();
        this.loadingPromises = new Map(); // Prevent duplicate requests
        this.CACHE_TTL = 5 * 60 * 1000; // 5 minutes cache TTL
    }

    /**
     * Check if cached data is still valid
     * @param {string} cacheKey - The cache key (node_base_url)
     * @returns {boolean} True if cache is valid
     */
    isCacheValid(cacheKey) {
        const cached = this.cache.get(cacheKey);
        if (!cached) return false;

        const now = Date.now();
        return (now - cached.timestamp) < this.CACHE_TTL;
    }

    /**
     * Get cached data if valid
     * @param {string} cacheKey - The cache key (node_base_url)
     * @returns {Object|null} Cached data or null
     */
    getCached(cacheKey) {
        if (this.isCacheValid(cacheKey)) {
            return this.cache.get(cacheKey).data;
        }
        return null;
    }

    /**
     * Set cached data
     * @param {string} cacheKey - The cache key (node_base_url)
     * @param {Object} data - The data to cache
     */
    setCached(cacheKey, data) {
        this.cache.set(cacheKey, {
            data,
            timestamp: Date.now()
        });
    }

    /**
     * Check if a request is currently in progress
     * @param {string} cacheKey - The cache key (node_base_url)
     * @returns {Promise|null} Promise if loading, null otherwise
     */
    getLoadingPromise(cacheKey) {
        return this.loadingPromises.get(cacheKey) || null;
    }

    /**
     * Set loading promise to prevent duplicate requests
     * @param {string} cacheKey - The cache key (node_base_url)
     * @param {Promise} promise - The loading promise
     */
    setLoadingPromise(cacheKey, promise) {
        this.loadingPromises.set(cacheKey, promise);

        // Clean up when promise resolves
        promise.finally(() => {
            this.loadingPromises.delete(cacheKey);
        }).catch(() => {
            // Ignore errors in cleanup
        });
    }

    /**
     * Force refresh cache for a specific key
     * @param {string} cacheKey - The cache key to refresh
     */
    invalidateCache(cacheKey) {
        this.cache.delete(cacheKey);
        this.loadingPromises.delete(cacheKey);
    }

    /**
     * Clear entire cache
     */
    clearCache() {
        this.cache.clear();
        this.loadingPromises.clear();
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getCacheStats() {
        return {
            cacheSize: this.cache.size,
            loadingRequests: this.loadingPromises.size,
            cacheKeys: Array.from(this.cache.keys())
        };
    }
}

// Global cache instance
const nodeCache = new NodeDataCache();

/**
 * Mock API call to fetch node data
 * Simulates: GET {node_base_url}/data
 * @param {string} nodeBaseUrl - Base URL for the node
 * @param {string} nodeName - Node name for display
 * @returns {Promise<Object>} Promise resolving to node data
 */
async function mockFetchNodeData(nodeBaseUrl, nodeName) {
    // Use node name directly as schema key since it matches NODE_DATA_SCHEMAS keys
    const nodeSchemaKey = nodeName;
    const schema = NODE_DATA_SCHEMAS[nodeSchemaKey];

    // Simulate network delay (100-300ms)
    const delay = 50;
    await new Promise(resolve => setTimeout(resolve, delay));

    if (!schema) {
        throw new Error(`Unknown node type: ${nodeSchemaKey}`);
    }

    return {
        node_name: nodeName,
        node_base_url: nodeBaseUrl,
        node_schema_key: nodeSchemaKey,
        columns: schema.columns,
        sample_data: schema.sample_data,
        data_count: schema.sample_data.length,
        fetched_at: new Date().toISOString(),
        status: 'success'
    };
}

/**
 * Fetch node data with caching
 * @param {Object} node - Node object from DataLab response
 * @returns {Promise<Object>} Promise resolving to node data with caching
 */
export async function fetchNodeData(queryName, queryParamName, node) {
    const { name } = node;

    if (!name) {
        throw new Error(`Node "${name}" is missing node_base_url`);
    }

    const cacheKey = name;

    // Check cache first
    const cached = nodeCache.getCached(cacheKey);
    if (cached) {
        return cached;
    }

    // Check if request is already in progress
    const loadingPromise = nodeCache.getLoadingPromise(cacheKey);
    if (loadingPromise) {
        try {
            return await loadingPromise;
        } catch (error) {
            // If the existing promise failed, we'll retry below
        }
    }

    // Make new request
    // const fetchPromise = mockFetchNodeData(entity_base_url, name);
    const url = `${API_ROOT_URL}/${queryName}`
    const fetchPromise = axios.patch(url, { [queryParamName]: name });

    // Store loading promise to prevent duplicates
    nodeCache.setLoadingPromise(cacheKey, fetchPromise);

    try {
        const res = await fetchPromise;
        const { schema: nodeProjectSchema, data: nodeData } = res.data;
        const nodeSchema = getModelSchema(name, nodeProjectSchema);
        const nodeFieldsMetadata = createCollections(nodeProjectSchema, nodeSchema, {});
        const nodeColumns = nodeFieldsMetadata.map((o) => {
            const updatedColumn = Object.assign({}, o);
            updatedColumn.name = updatedColumn.tableTitle;
            return updatedColumn;
        });
        const nodeUrl = getServerUrl(nodeSchema);
        const data = {
            nodeProjectSchema,
            nodeSchema,
            nodeData,
            nodeFieldsMetadata,
            nodeColumns,
            nodeUrl
        };
        // Cache the result
        nodeCache.setCached(cacheKey, data);
        return data;
    } catch (error) {
        // Clear the loading promise on error so it can be retried
        nodeCache.loadingPromises.delete(cacheKey);
        throw error;
    }
}

/**
 * Fetch multiple nodes in parallel with error handling
 * @param {Array} nodes - Array of node objects
 * @returns {Promise<Object>} Promise resolving to { success: [], errors: [] }
 */
export async function fetchMultipleNodeData(nodes) {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        return { success: [], errors: [] };
    }

    const results = await Promise.allSettled(
        nodes.map(node => fetchNodeData(node))
    );

    const success = [];
    const errors = [];

    results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
            success.push(result.value);
        } else {
            errors.push({
                node: nodes[index],
                error: result.reason
            });
        }
    });

    return { success, errors };
}

/**
 * Get cached node data without making a request
 * @param {string} nodeName - Node name
 * @returns {Object|null} Cached data or null
 */
export function getCachedNodeData(nodeName) {
    return nodeCache.getCached(nodeName);
}

/**
 * Check if node data is cached and valid
 * @param {string} nodeName - Node name
 * @returns {boolean} True if cached and valid
 */
export function isNodeDataCached(nodeName) {
    return nodeCache.isCacheValid(nodeName);
}

/**
 * Clear all cached node data
 */
export function clearNodeDataCache() {
    nodeCache.clearCache();
}

/**
 * Force refresh specific node data
 * @param {string} nodeName - Node name to refresh
 */
export function refreshNodeData(nodeName) {
    nodeCache.invalidateCache(nodeName);
}

/**
 * Get cache statistics for debugging
 * @returns {Object} Cache statistics
 */
export function getNodeCacheStats() {
    return nodeCache.getCacheStats();
}

/**
 * Preload node data for multiple nodes
 * Useful for warming the cache when DataLab is loaded
 * @param {Array} nodes - Array of node objects
 * @returns {Promise<void>} Promise that resolves when preloading is complete
 */
export async function preloadNodeData(nodes) {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        return;
    }

    try {
        await fetchMultipleNodeData(nodes);
    } catch (error) {
        console.error('Error during node data preloading:', error);
    }
}

export default {
    fetchNodeData,
    fetchMultipleNodeData,
    getCachedNodeData,
    isNodeDataCached,
    clearNodeDataCache,
    refreshNodeData,
    getNodeCacheStats,
    preloadNodeData,
    fetchAnalysedData
};