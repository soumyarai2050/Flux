/**
 * Manages caches for XPath to data index mappings, optimizing data retrieval and manipulation in arrays.
 * This class provides a robust mechanism to avoid costly full array scans by caching paths and IDs.
 * It maintains three types of caches:
 * 1. XPath to data index cache.
 * 2. Item ID to schema path cache.
 * 3. Item ID to current data path cache.
 * These caches are dynamically updated on item addition, removal, or movement.
 * @class XPathCacheManager
 */
export class XPathCacheManager {
    /**
     * Initializes the XPathCacheManager by creating new Map instances for the caches.
     * @constructor
     */
    constructor() {
        /** @private @type {Map<string, Map<string, number>>} */
        this.cache = new Map(); // xpath -> dataIndex cache
        /** @private @type {Map<string, string>} */
        this.idToXpathCache = new Map(); // id -> schemaPath cache
        /** @private @type {Map<string, string>} */
        this.idToDatapathCache = new Map(); // id -> currentDataPath cache
    }

    /**
     * Builds a cache for a given array of data.
     * This method iterates through the array, extracts XPath and ID information, and populates the caches.
     * It handles objects with `xpath_` properties and `_id` fields.
     * @param {Array<Object>} arrayData - The array of objects to cache. Each object should have an `xpath_` property and may have an `_id`.
     * @param {string} arrayPath - The base path of the array (e.g., "pair_strat_params.eligible_brokers").
     * @returns {Map<string, number>} The XPath cache for the specified array.
     */
    buildCacheForArray(arrayData, arrayPath) {
        const arrayCache = new Map();

        if (!Array.isArray(arrayData)) {
            return arrayCache;
        }

        arrayData.forEach((item, currentIndex) => {
            if (item && typeof item === 'object') {
                // Find xpath property
                const xpathProp = Object.keys(item).find(key => key.startsWith('xpath_'));
                if (xpathProp && item[xpathProp]) {
                    // Extract the full path from the xpath property
                    const fullXPath = item[xpathProp];
                    // Get the schema path (everything before the last '.')
                    const lastDotIndex = fullXPath.lastIndexOf('.');
                    const schemaPath = lastDotIndex > -1 ? fullXPath.substring(0, lastDotIndex) : fullXPath;

                    // Store mapping: schema path -> current index
                    arrayCache.set(schemaPath, currentIndex);

                    // Build ID-based caches if item has _id
                    if (item._id) {
                        const currentDataPath = `${arrayPath}[${currentIndex}]`;
                        this.idToXpathCache.set(item._id, schemaPath);
                        this.idToDatapathCache.set(item._id, currentDataPath);
                    }
                }
            }
        });

        // Store in main cache
        this.cache.set(arrayPath, arrayCache);
        return arrayCache;
    }

    /**
     * Retrieves the cached index for a given XPath and array path.
     * @param {string} xpath - The schema XPath to look up.
     * @param {string} arrayPath - The path of the array containing the item.
     * @returns {number|undefined} The cached index, or undefined if not found.
     */
    getCachedIndex(xpath, arrayPath) {
        const arrayCache = this.cache.get(arrayPath);
        return arrayCache ? arrayCache.get(xpath) : undefined;
    }

    /**
     * Updates the cache when a new item is added to an array.
     * This method shifts the indices of existing items and adds the new item to the cache.
     * @param {string} arrayPath - The path of the array where the item was added.
     * @param {string} xpath - The schema XPath of the new item.
     * @param {number} index - The index where the new item was added.
     */
    addItem(arrayPath, xpath, index) {
        let arrayCache = this.cache.get(arrayPath);
        if (!arrayCache) {
            arrayCache = new Map();
            this.cache.set(arrayPath, arrayCache);
        }

        // Update indices for items after the insertion point
        const updatedCache = new Map();
        arrayCache.forEach((currentIndex, itemXpath) => {
            if (currentIndex >= index) {
                updatedCache.set(itemXpath, currentIndex + 1);
            } else {
                updatedCache.set(itemXpath, currentIndex);
            }
        });

        // Add the new item
        updatedCache.set(xpath, index);
        this.cache.set(arrayPath, updatedCache);
    }

    /**
     * Updates the cache when an item is removed from an array.
     * This method shifts the indices of subsequent items to fill the gap.
     * @param {string} arrayPath - The path of the array from which the item was removed.
     * @param {string} xpath - The schema XPath of the removed item.
     * @param {number} index - The index of the removed item.
     */
    removeItem(arrayPath, xpath, index) {
        const arrayCache = this.cache.get(arrayPath);
        if (!arrayCache) return;

        // Update indices for items after the removal point
        const updatedCache = new Map();
        arrayCache.forEach((currentIndex, itemXpath) => {
            if (itemXpath !== xpath) {
                if (currentIndex > index) {
                    updatedCache.set(itemXpath, currentIndex - 1);
                } else {
                    updatedCache.set(itemXpath, currentIndex);
                }
            }
        });

        this.cache.set(arrayPath, updatedCache);
    }

    /**
     * Retrieves the data path for an item using its ID.
     * This provides a significant performance improvement over scanning arrays.
     * @param {string} id - The `_id` of the item.
     * @returns {string|undefined} The current data path, or undefined if not found.
     */
    getDataPathById(id) {
        return this.idToDatapathCache.get(id);
    }

    /**
     * Retrieves the schema path for an item using its ID.
     * @param {string} id - The `_id` of the item.
     * @returns {string|undefined} The schema path, or undefined if not found.
     */
    getSchemaPathById(id) {
        return this.idToXpathCache.get(id);
    }

    /**
     * Updates the data path for an item in the ID-based cache.
     * This is useful when an item's position changes within an array.
     * @param {string} id - The `_id` of the item to update.
     * @param {string} newDataPath - The new data path of the item.
     */
    updateItemDataPath(id, newDataPath) {
        if (this.idToDatapathCache.has(id)) {
            this.idToDatapathCache.set(id, newDataPath);
        }
    }

    /**
     * Clears the cache.
     * If an array path is provided, only the cache for that specific array is cleared.
     * Otherwise, all caches are cleared.
     * @param {string} [arrayPath] - The optional path of the array cache to clear.
     */
    clear(arrayPath) {
        if (arrayPath) {
            this.cache.delete(arrayPath);
        } else {
            this.cache.clear();
            this.idToXpathCache.clear();
            this.idToDatapathCache.clear();
        }
    }

    /**
     * Generates an optimized data path using the cache.
     * This method resolves array indices from the cache to create a direct data path.
     * If a path segment is not found in the cache, it falls back to the original index.
     * @param {Object} data - The data object (currently unused, consider for future enhancements).
     * @param {string} xpath - The schema XPath to optimize.
     * @returns {string|undefined} The optimized data path, or the original XPath if it cannot be optimized.
     */
    getOptimizedDataPath(data, xpath) {
        if (!xpath || xpath.includes('-1')) return xpath;

        // Parse the xpath to find array segments
        const segments = xpath.split(/(\[[^\]]+\])/);
        let dataPath = '';
        let schemaPath = '';

        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];

            if (segment.startsWith('[') && segment.endsWith(']')) {
                // This is an array index
                const index = segment.slice(1, -1);
                schemaPath += segment;

                // Check if we have a cached mapping for this array
                const arrayPath = schemaPath.substring(0, schemaPath.lastIndexOf('['));
                const cachedIndex = this.getCachedIndex(schemaPath, arrayPath);

                if (cachedIndex !== undefined) {
                    dataPath += `[${cachedIndex}]`;
                } else {
                    // Fallback to original index
                    dataPath += segment;
                }
            } else {
                // This is a property name
                dataPath += segment;
                schemaPath += segment;
            }
        }

        return dataPath;
    }
}

// Singleton instance
export const xpathCacheManager = new XPathCacheManager(); 