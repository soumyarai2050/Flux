
/**
 * Converts an array of sort order objects into a dictionary, keyed by the `sort_by` field.
 * Each item in the dictionary will also include a `sort_level` indicating its original position in the array (1-based index).
 * @param {Array<Object>} sortOrders - An array of objects, where each object defines a sort order (e.g., `{ sort_by: 'columnName', sort_direction: 'asc' }`).
 * @returns {Object<string, Object>} A dictionary where keys are `sort_by` values and values are the sort order objects with an added `sort_level`.
 */
export function getSortOrderDict(sortOrders) {
    return sortOrders.reduce((acc, item, idx) => {
        acc[item.sort_by] = {
            ...item,
            sort_level: idx + 1 // Assign a 1-based sort level based on the item's position in the original array.
        };
        return acc;
    }, {});
}

/**
 * Sorts an array of elements in a stable manner, preserving the relative order of equal elements.
 * This is achieved by augmenting each element with its original index before sorting.
 * @param {Array<*>} array - The array to be sorted.
 * @param {Function} comparator - A comparison function that defines the sort order. It takes two elements `a` and `b` and returns a negative, zero, or positive value indicating their relative order.
 * @returns {Array<*>} A new array containing the sorted elements, maintaining stability.
 */
export function stableSort(array, comparator) {
    // Augment each element with its original index to ensure stability.
    const stabilizedThis = array.map((el, index) => [el, index]);

    // Sort the augmented array.
    stabilizedThis.sort((a, b) => {
        // Compare elements using the provided comparator.
        const order = comparator(a[0], b[0]);
        // If elements are equal according to the comparator, use their original index to maintain stability.
        if (order !== 0) {
            return order;
        }
        return a[1] - b[1]; // Use original index for stable sorting.
    });

    // Return the sorted elements, stripping off the added index.
    return stabilizedThis.map((el) => el[0]);
}