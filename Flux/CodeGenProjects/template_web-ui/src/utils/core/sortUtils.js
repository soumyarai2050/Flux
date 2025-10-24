/**
 * @enum {string} SortType - Defines the types of sorting directions.
 */
export const SortType = {
    /** Unspecified sort type, defaults to ascending. */
    SORT_TYPE_UNSPECIFIED: 'asc',
    /** Ascending sort order. */
    ASCENDING: 'asc',
    /** Descending sort order. */
    DESCENDING: 'desc',
};

/**
 * @class SortComparator
 * @description Provides static methods for generating and executing comparison functions for sorting arrays.
 * Supports multi-level sorting and absolute value sorting.
 */
export class SortComparator {
    /**
     * Returns a comparison function based on the provided sort orders.
     * This static method acts as a factory for creating a comparator function that can be used with `Array.prototype.sort()`.
     * @param {Array<object>} sortOrders - An array of sort order objects, each with `sort_by` (field name) and `sort_direction` (asc/desc).
     * @param {boolean} [nestedArray=false] - If true, assumes the array contains nested arrays and sorts based on the first element of the nested array.
     * @returns {function(object, object): number} A comparison function suitable for `Array.prototype.sort()`.
     */
    static getInstance(sortOrders, nestedArray = false) {
        return (a, b) => SortComparator.comparator(a, b, sortOrders, undefined, nestedArray);
    }

    /**
     * Recursively compares two objects based on a list of sort orders.
     * This method is the core logic for multi-level sorting. It iterates through `sortOrders`,
     * applying each sort criterion sequentially until a non-zero comparison result is found.
     * @param {object} a - The first object for comparison.
     * @param {object} b - The second object for comparison.
     * @param {Array<object>} sortOrders - The array of sort order objects.
     * @param {number} [index=0] - The current index in the `sortOrders` array for multi-level sorting.
     * @param {boolean} [nestedArray=false] - If true, assumes the objects are elements of a nested array.
     * @returns {number} A negative value if `a` comes before `b`, a positive value if `a` comes after `b`, or 0 if they are equal.
     */
    static comparator(a, b, sortOrders, index = 0, nestedArray = false) {
        // If all sort orders have been processed, consider the objects equal.
        if (sortOrders.length <= index) {
            return 0;
        }
        const sortOrder = sortOrders[index];
        index += 1;
        let retVal;

        // Apply descending or ascending sort based on `sort_direction`.
        // Handle both string format ('desc', 'asc') and numeric format (-1, 1)
        const isDescending = sortOrder.sort_direction === SortType.DESCENDING || sortOrder.sort_direction === -1;

        if (isDescending) {
            retVal = SortComparator.descendingSort(a, b, sortOrder, nestedArray);
        } else { // order is asc
            // For ascending sort, negate the result of descending sort.
            retVal = -SortComparator.descendingSort(a, b, sortOrder, nestedArray);
        }

        // If the current sort criterion results in equality, move to the next sort order.
        if (retVal === 0) {
            retVal = SortComparator.comparator(a, b, sortOrders, index, nestedArray);
        }
        return retVal;
    }

    /**
     * Compares two objects in descending order based on a single sort order.
     * It extracts values from objects based on `sort_by` and optionally applies absolute value sorting.
     * Handles `undefined` or `null` values by placing them at the beginning (for descending sort).
     * @param {object} a - The first object for comparison.
     * @param {object} b - The second object for comparison.
     * @param {object} sortOrder - The sort order object, containing `sort_by` (field name) and `is_absolute_sort` (boolean).
     * @param {boolean} [nestedArray=false] - If true, assumes the objects are elements of a nested array and accesses the first element.
     * @returns {number} A negative value if `a` comes before `b` (in descending order), a positive value if `a` comes after `b`, or 0 if they are equal.
     */
    static descendingSort(a, b, sortOrder, nestedArray = false) {
        let updatedA = a;
        let updatedB = b;

        const orderBy = sortOrder.sort_by;
        const useAbs = sortOrder.is_absolute_sort;

        // If sorting nested arrays, use the first element of the inner array.
        if (nestedArray) {
            updatedA = a[0];
            updatedB = b[0];
        }

        let valA = updatedA[orderBy];
        let valB = updatedB[orderBy];

        // Handle undefined or null values: place them at the beginning in descending sort.
        if (valA === undefined || valA === null) return -1;
        if (valB === undefined || valB === null) return 1;

        // Apply absolute value sorting if `is_absolute_sort` is true.
        if (useAbs) {
            valA = Math.abs(valA);
            valB = Math.abs(valB);
        }
        
        // Perform descending comparison.
        if (valB < valA) return -1;
        if (valB > valA) return 1;
        return 0;
    }
}