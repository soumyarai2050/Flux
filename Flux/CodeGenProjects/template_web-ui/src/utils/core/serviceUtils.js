
import axios from "axios";
import { API_ROOT_URL } from "../../config";
import { createCollections, getModelSchema, getServerUrl } from "../../utils";
import { genChartDatasets, getChartOption, updateChartDataObj } from '../../utils/core/chartUtils';
import { cloneDeep } from 'lodash';
import { removeRedundantFieldsFromRows } from '../../utils/core/dataTransformation';

/**
 * Transform ChartTileNode data to chart-compatible format.
 * This function ensures each data point has the necessary IDs for chart interaction.
 * @param {Array} chartTileNodeData - Data from ChartTileNode Redux storedArray
 * @returns {Array} Transformed data suitable for chart display
 */
export const transformChartTileData = (chartTileNodeData = []) => {
    if (!chartTileNodeData || chartTileNodeData.length === 0) {
        return [];
    }

    const transformedData = chartTileNodeData.map((item, index) => {
        const dataPoint = { ...item };

        // Ensure required chart interaction fields exist, providing fallbacks
        if (!dataPoint['_id']) {
            dataPoint['_id'] = item.id || `row_${index + 1}`;
        }
        if (!dataPoint['data-id']) {
            dataPoint['data-id'] = item.id || item._id || `row_${index + 1}`;
        }
        if (!dataPoint['chart_row_index']) {
            dataPoint['chart_row_index'] = index + 1;
        }

        return dataPoint;
    });

    // Apply the same data cleaning as other models
    return removeRedundantFieldsFromRows(transformedData);
};

/**
 * Transform fields metadata for chart-specific requirements
 * @param {Array} fieldsMetadata - Raw fields metadata from schema
 * @returns {Array} Transformed fields metadata for charts
 */
export const transformFieldsForChart = (fieldsMetadata) => {
    return fieldsMetadata.map((field) => ({
        key: field.tableTitle,
        title: field.title,
        tableTitle: field.tableTitle,
        type: field.type,
        xpath: field.xpath,
        displayType: field.displayType || 'normal'
    }));
};

/**
 * Fetch schema for a given model from the backend API
 * Uses the generic fetchModelSchema with chart-specific transformations
 * @param {string} modelName - The name of the model to fetch schema for
 * @param {string} baseUrl - The base URL for the model's API endpoint
 * @returns {Promise<Object>} Promise resolving to schema data and field metadata
 */
export const fetchChartSchema = async (modelName, baseUrl) => {
    if (!modelName) {
        throw new Error('Model name is required to fetch schema');
    }

    try {
        // Use the generic fetchModelSchema function
        const schemaData = await fetchModelSchema(modelName, baseUrl);

        // Apply chart-specific field transformation
        const transformedFieldsMetadata = transformFieldsForChart(schemaData.fieldsMetadata);

        return {
            projectSchema: schemaData.projectSchema,
            modelSchema: schemaData.modelSchema,
            fieldsMetadata: transformedFieldsMetadata
        };
    } catch (error) {
        console.error(`Error fetching schema for model ${modelName}:`, error);
        throw new Error(`Failed to fetch schema for model ${modelName}: ${error.message}`);
    }
};


/**
 * Packages real data from the ChartTileNode with its corresponding schema.
 * This function does not "fetch" but rather "processes" data passed to it.
 * @param {Array} realChartData - The actual data array from the ChartTileNode's Redux state.
 * @param {Object} schemaData - The live schema data fetched by fetchChartSchema.
 * @param {string} sourceModelName - Name of the source model for the data.
 * @param {string} sourceModelBaseUrl - Base URL for the source model.
 * @returns {Object} A complete data package for the chart node.
 */
export const packageChartDataWithSchema = (schemaData, sourceModelName, sourceModelBaseUrl) => {


    //  Extract the schema components
    const { projectSchema, modelSchema, fieldsMetadata } = schemaData;

    //  Assemble the final package in the structure expected by other components
    return {
        modelName: sourceModelName,
        modelSchema: modelSchema,
        projectSchema: projectSchema,
        fieldsMetadata: fieldsMetadata,
        url: sourceModelBaseUrl,
    };
}


// Generate chart option for detailed view
export const generateChartOption = (chart, chartData = null, fieldsMetadata = null) => {

    if (!chart) {
        return { chartOptions: {}, datasets: [] };
    }

    // Create a deep copy to avoid read-only array issues in chartUtils
    let actualData;
    if (chartData && chartData.length > 0) {
        actualData = cloneDeep(chartData);
    } 

    // Generate datasets using chart utilities
    const datasets = genChartDatasets(
        actualData,           // rows - actual data rows for non-time-series
        {},                   // tsData - empty for non-time-series
        chart,                // chartObj - chart configuration
        {},                   // queryDict - empty for non-time-series
        fieldsMetadata,       // collections - field metadata
        false                 // isCollectionType
    );

    // Create chart configuration
    const chartDataObj = updateChartDataObj(
        chart,                // chartObj
        fieldsMetadata,       // collections
        actualData,           // rows
        datasets,             // datasets
        false,                // isCollectionType
        {},                   // schemaCollections (empty for ChartModel)
        {}                    // queryDict (empty for non-time-series)
    );

    const finalOption = getChartOption(chartDataObj);

    // Return both chart options and datasets separately
    // This matches ChartView's pattern where datasets are manually added to EChart options
    return {
        chartOptions: finalOption,
        datasets: datasets
    };
};


//graph services 
/**
 * Fetch schema-only information for a given model
 * @param {string} modelName - The name of the model to fetch schema for
 * @param {string} [baseUrl] - Optional base URL for the model's API endpoint (defaults to API_ROOT_URL)
 * @returns {Promise<Object>} Promise resolving to schema data and field metadata
 */
export async function fetchModelSchema(modelName, baseUrl) {
    if (!modelName) {
        throw new Error('Model name is required to fetch schema');
    }

    try {
        const url = `${baseUrl}/query-get_${modelName}_schema`;
        const response = await axios.get(url);

        const projectSchema = response.data;
        const modelSchema = getModelSchema(modelName, projectSchema);
        const fieldsMetadata = createCollections(projectSchema, modelSchema, {});

        return {
            projectSchema,
            modelSchema,
            fieldsMetadata
        };
    } catch (error) {
        console.error(`Error fetching schema for model ${modelName}:`, error);
        throw new Error(`Failed to fetch schema for model ${modelName}: ${error.message}`);
    }
}

/**
 * Extract model name from analysis response data
 * @param {Object} responseData - The response data from join analysis
 * @returns {string} The model name extracted from the response
 */
export function getModelNameForAnalysis(responseData) {
    if (!responseData) {
        throw new Error('Response data is required to extract model name');
    }

    // First try to get modelName directly from the outer structure
    if (responseData.modelName) {
        return responseData.modelName;
    }

    // If not found, look in projectSchema definitions
    if (responseData.projectSchema?.definitions) {
        const definitionKeys = Object.keys(responseData.projectSchema.definitions);
        if (definitionKeys.length > 0) {
            return definitionKeys[0];
        }
    }

    // If not found in definitions, look for object with json_root: true and get its title
    if (responseData.projectSchema?.definitions) {
        for (const [key, definition] of Object.entries(responseData.projectSchema.definitions)) {
            if (definition.json_root === true && definition.title) {
                return key; // Return the key, not the title, as model name is typically the key
            }
        }
    }

    // If still not found, check if modelSchema has a title
    if (responseData.modelSchema?.title) {
        // Convert title to model name format (snake_case)
        return responseData.modelSchema.title.toLowerCase().replace(/\s+/g, '_');
    }

    throw new Error('Could not extract model name from analysis response');
}

/**
 * Fetch join analysis data from dedicated endpoint
 * @param {string} queryName - The query name for the join analysis
 * @returns {Promise<Object>} Promise resolving to joined analysis data
 */
export async function fetchJoinAnalysisData(queryName) {
    if (!queryName) {
        throw new Error('Query name is required for join analysis');
    }

    try {
        const url = `${API_ROOT_URL}/${queryName}`;
        const response = await axios.patch(url, {});
        const {schema: projectSchema , data} = response.data;
        const modelName = getModelNameForAnalysis({ projectSchema, data });
        const modelSchema = getModelSchema(modelName, projectSchema);

        const fieldsMetadata = createCollections(projectSchema, modelSchema, {});

        return {
            projectSchema,
            modelSchema,
            fieldsMetadata,
            modelName,
            data
        };

    } catch (error) {
        console.error(`Error fetching join analysis data for query ${queryName}:`, error);
        throw new Error(`Failed to fetch join analysis data: ${error.message}`);
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
    fetchModelSchema,
    fetchJoinAnalysisData,
    getModelNameForAnalysis,
    fetchNodeData,
    fetchMultipleNodeData,
    getCachedNodeData,
    isNodeDataCached,
    clearNodeDataCache,
    refreshNodeData,
    getNodeCacheStats,
    preloadNodeData,
    generateChartOption,
    transformChartTileData,
    transformFieldsForChart,
    fetchChartSchema
};