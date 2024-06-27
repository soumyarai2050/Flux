export const SortType = {
    SORT_TYPE_UNSPECIFIED: 'asc',
    ASCENDING: 'asc',
    DESCENDING: 'desc',
}

export class SortComparator {
    static getInstance(sortOrders, nestedArray = false) {
        return (a, b) => SortComparator.comparator(a, b, sortOrders, undefined, nestedArray);
    }

    static comparator(a, b, sortOrders, index = 0, nestedArray = false) {
        if (sortOrders.length <= index) {
            return 0;
        }
        const sortOrder = sortOrders[index];
        index += 1;
        let retVal;
        if (sortOrder.sort_type === SortType.DESCENDING) {
            retVal = SortComparator.descendingSort(a, b, sortOrder.order_by, nestedArray);
        } else { // order is asc
            retVal = -SortComparator.descendingSort(a, b, sortOrder.order_by, nestedArray);
        }
        if (retVal === 0) {
            retVal = SortComparator.comparator(a, b, sortOrders, index, nestedArray);
        }
        return retVal;
    }

    static descendingSort(a, b, orderBy, nestedArray = false) {
        let updatedA = a;
        let updatedB = b;
        if (nestedArray) {
            updatedA = a[0];
            updatedB = b[0];
        }
        if (updatedA[orderBy] === undefined || updatedA[orderBy] === null) {
            return -1;
        } else if (updatedB[orderBy] === undefined || updatedB[orderBy] === null) {
            return 1;
        } else if (updatedB[orderBy] < updatedA[orderBy]) {
            return -1;
        } else if (updatedB[orderBy] > updatedA[orderBy]) {
            return 1;
        }
        return 0;
    }
}