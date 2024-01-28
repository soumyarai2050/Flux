const DEFAULT_PAGE = 0;
const DEFAULT_PAGE_SIZE = 25;

export class SortOrderCache {
    static sortOrderDict = {};

    static getSortOrder(name) {
        return SortOrderCache.sortOrderDict?.[name] ?? [];
    }

    static setSortOrder(name, sortOrders) {
        SortOrderCache.sortOrderDict[name] = sortOrders;
    }

    static cleanSortOrder(name) {
        if (SortOrderCache.sortOrderDict.hasOwnProperty(name)) {
            delete SortOrderCache.sortOrderDict[name];
        }
    }
}

export class HideCache {
    static hideDict = {};

    static getHide(name, path) {
        return HideCache.hideDict?.[name]?.[path] ?? false;
    }

    static setHide(name, path, value) {
        HideCache.hideDict[name][path] = value;
    }

    static cleanHide(name) {
        if (HideCache.hideDict.hasOwnProperty(name)) {
            delete HideCache.hideDict[name];
        }
    }
}

export class PageCache {
    static pageDict = {};
    static pageSizeDict = {}; 

    static getPage(name) {
        return PageCache.pageDict?.[name] ?? DEFAULT_PAGE;
    }

    static setPage(name, page) {
        PageCache.pageDict[name] = page;
    }

    static cleanPage(name) {
        if (PageCache.pageDict.hasOwnProperty(name)) {
            delete PageCache.pageDict[name];
        }
    }
}

export class PageSizeCache {
    static pageSizeDict = {};

    static getPageSize(name) {
        return PageSizeCache.pageSizeDict?.[name] ?? DEFAULT_PAGE_SIZE;
    }

    static setPageSize(name, pageSize) {
        PageSizeCache.pageSizeDict[name] = pageSize;
    }

    static cleanPageSize(name) {
        if (PageSizeCache.pageSizeDict.hasOwnProperty(name)) {
            delete PageSizeCache.pageSizeDict[name];
        }
    }
}

export function cleanAllCache(name) {
    SortOrderCache.cleanSortOrder(name);
    HideCache.cleanHide(name);
    PageCache.cleanPage(name);
    PageSizeCache.cleanPageSize(name);
}
