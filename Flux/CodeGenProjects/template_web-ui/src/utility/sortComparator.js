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
            retVal = SortComparator.descendingSort(a, b, sortOrder, nestedArray);
        } else { // order is asc
            retVal = -SortComparator.descendingSort(a, b, sortOrder, nestedArray);
        }
        if (retVal === 0) {
            retVal = SortComparator.comparator(a, b, sortOrders, index, nestedArray);
        }
        return retVal;
    }

    static descendingSort(a, b, sortOrder, nestedArray = false) {
        let updatedA = a;
        let updatedB = b;

        const orderBy = sortOrder.order_by;
        const useAbs = sortOrder.abs;
        if (nestedArray) {
            updatedA = a[0];
            updatedB = b[0];
        }
        let valA = updatedA[orderBy];
        let valB = updatedB[orderBy];

        if (valA === undefined || valA === null) return -1;
        if (valB === undefined || valB === null) return 1;

        if (useAbs) {
            valA = Math.abs(valA);
            valB = Math.abs(valB);
        }
        
        if (valB < valA) return -1;
        if (valB > valA) return 1;
        return 0;
    }
}