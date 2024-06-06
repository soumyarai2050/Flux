export const SortType = {
    SORT_TYPE_UNSPECIFIED: 'asc',
    ASCENDING: 'asc',
    DESCENDING: 'desc',
}

export class SortComparator {
    static getInstance(sortOrders) {
        return (a, b) => SortComparator.comparator(a, b, sortOrders);
    }

    static comparator(a, b, sortOrders, index = 0) {
        if (sortOrders.length <= index) {
            return 0;
        }
        const sortOrder = sortOrders[index];
        index += 1;
        let retVal;
        if (sortOrder.sort_type === SortType.DESCENDING) {
            retVal = SortComparator.descendingSort(a, b, sortOrder.order_by);
        } else { // order is asc
            retVal = -SortComparator.descendingSort(a, b, sortOrder.order_by);
        }
        if (retVal === 0) {
            retVal = SortComparator.comparator(a, b, sortOrders, index);
        }
        return retVal;
    }

    static descendingSort(a, b, orderBy) {
        if (a[orderBy] === undefined || a[orderBy] === null) {
            return -1;
        } else if (b[orderBy] === undefined || b[orderBy] === null) {
            return 1;
        } else if (b[orderBy] < a[orderBy]) {
            return -1;
        } else if (b[orderBy] > a[orderBy]) {
            return 1;
        }
        return 0;
    }
}