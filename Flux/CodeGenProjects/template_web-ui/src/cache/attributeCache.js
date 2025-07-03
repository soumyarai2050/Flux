export const DEFAULT_PAGE = 0;
export const DEFAULT_ROWS_PER_PAGE = 25;

/**
 * @class SortOrderCache
 * @description Manages the caching of sort orders for different models/views.
 */
export class SortOrderCache {
    /** @type {object} */
    static sortOrderDict = {};

    /**
     * Retrieves the sort orders for a given name.
     * @param {string} name - The name of the model/view.
     * @returns {Array<object>} The array of sort orders, or an empty array if not found.
     */
    static getSortOrder(name) {
        return SortOrderCache.sortOrderDict?.[name] ?? [];
    }

    /**
     * Sets the sort orders for a given name.
     * @param {string} name - The name of the model/view.
     * @param {Array<object>} sortOrders - The array of sort orders to cache.
     */
    static setSortOrder(name, sortOrders) {
        SortOrderCache.sortOrderDict[name] = sortOrders;
    }

    /**
     * Cleans (deletes) the cached sort orders for a given name.
     * @param {string} name - The name of the model/view.
     */
    static cleanSortOrder(name) {
        if (SortOrderCache.sortOrderDict.hasOwnProperty(name)) {
            delete SortOrderCache.sortOrderDict[name];
        }
    }
}

/**
 * @class HideCache
 * @description Manages the caching of hide states for UI elements.
 */
export class HideCache {
    /** @type {object} */
    static hideDict = {};

    /**
     * Retrieves the hide state for a given name and path.
     * @param {string} name - The name of the model/view.
     * @param {string} path - The path of the UI element.
     * @returns {boolean} The hide state, or false if not found.
     */
    static getHide(name, path) {
        return HideCache.hideDict?.[name]?.[path] ?? false;
    }

    /**
     * Sets the hide state for a given name and path.
     * @param {string} name - The name of the model/view.
     * @param {string} path - The path of the UI element.
     * @param {boolean} value - The hide state value to set.
     */
    static setHide(name, path, value) {
        if (!HideCache.hideDict[name]) {
            HideCache.hideDict[name] = {};
        }
        HideCache.hideDict[name][path] = value;
    }

    /**
     * Cleans (deletes) the cached hide states for a given name.
     * @param {string} name - The name of the model/view.
     */
    static cleanHide(name) {
        if (HideCache.hideDict.hasOwnProperty(name)) {
            delete HideCache.hideDict[name];
        }
    }
}

/**
 * @class PageCache
 * @description Manages the caching of current page numbers for different models/views.
 */
export class PageCache {
    /** @type {object} */
    static pageDict = {};

    /**
     * Retrieves the current page number for a given name.
     * @param {string} name - The name of the model/view.
     * @returns {number} The current page number, or DEFAULT_PAGE if not found.
     */
    static getPage(name) {
        return PageCache.pageDict?.[name] ?? DEFAULT_PAGE;
    }

    /**
     * Sets the current page number for a given name.
     * @param {string} name - The name of the model/view.
     * @param {number} page - The page number to cache.
     */
    static setPage(name, page) {
        PageCache.pageDict[name] = page;
    }

    /**
     * Cleans (deletes) the cached page number for a given name.
     * @param {string} name - The name of the model/view.
     */
    static cleanPage(name) {
        if (PageCache.pageDict.hasOwnProperty(name)) {
            delete PageCache.pageDict[name];
        }
    }
}

/**
 * @class PageSizeCache
 * @description Manages the caching of page sizes (rows per page) for different models/views.
 */
export class PageSizeCache {
    /** @type {object} */
    static pageSizeDict = {};

    /**
     * Retrieves the page size for a given name.
     * @param {string} name - The name of the model/view.
     * @param {number} [defaultSize] - Optional: The default page size to use if not found in cache.
     * @returns {number} The page size, or the provided defaultSize, or DEFAULT_ROWS_PER_PAGE if neither is found.
     */
    static getPageSize(name, defaultSize) {
        if (defaultSize !== undefined) {
            return PageSizeCache.pageSizeDict?.[name] ?? defaultSize;
        } else {
            return PageSizeCache.pageSizeDict?.[name] ?? DEFAULT_ROWS_PER_PAGE;
        }
    }

    /**
     * Sets the page size for a given name.
     * @param {string} name - The name of the model/view.
     * @param {number} pageSize - The page size to cache.
     */
    static setPageSize(name, pageSize) {
        PageSizeCache.pageSizeDict[name] = pageSize;
    }

    /**
     * Cleans (deletes) the cached page size for a given name.
     * @param {string} name - The name of the model/view.
     */
    static cleanPageSize(name) {
        if (PageSizeCache.pageSizeDict.hasOwnProperty(name)) {
            delete PageSizeCache.pageSizeDict[name];
        }
    }
}

/**
 * @function cleanAllCache
 * @description Cleans all cached attributes (sort order, hide state, page, page size) for a given model/view name.
 * @param {string} name - The name of the model/view to clean caches for.
 */
export function cleanAllCache(name) {
    SortOrderCache.cleanSortOrder(name);
    HideCache.cleanHide(name);
    PageCache.cleanPage(name);
    PageSizeCache.cleanPageSize(name);
}
