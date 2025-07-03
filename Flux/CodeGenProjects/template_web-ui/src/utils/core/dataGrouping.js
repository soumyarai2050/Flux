import { get, groupBy } from 'lodash';
import { SortComparator, SortType } from './sortUtils';
import { stableSort } from './dataSorting';

/**
 * Groups common keys in an array, marking the start and end of each group.
 * A group is defined by consecutive elements having the same `parentxpath`.
 * If a group contains only one element, the `groupStart` and `groupEnd` flags are removed.
 * @param {Array<Object>} commonKeys - An array of objects, each expected to have a `parentxpath` property.
 * @returns {Array<Object>} The modified array with `groupStart` and `groupEnd` flags added to relevant objects.
 */
export function groupCommonKeys(commonKeys) {
    let groupStart = false; // Flag to track if currently inside a group.
    commonKeys = commonKeys.map((commonKeyObj, idx) => {
        if (commonKeyObj.parentxpath) {
            // Check if a new group is starting.
            if (!groupStart) {
                groupStart = true;
                commonKeyObj.groupStart = true;
            }
            // If inside a group, check if the group is ending.
            if (groupStart) {
                let nextIdx = idx + 1;
                if (nextIdx < commonKeys.length) {
                    let nextCommonKeyObj = commonKeys[nextIdx];
                    // If the next item has a different parentxpath, the current group ends.
                    if (commonKeyObj.parentxpath !== nextCommonKeyObj.parentxpath) {
                        commonKeyObj.groupEnd = true;
                        groupStart = false;
                    }
                } else {
                    // If it's the last item, the current group ends.
                    commonKeyObj.groupEnd = true;
                    groupStart = false;
                }
            }
        }
        // Remove grouping flags if only one element is present in the group (i.e., it's a group of one).
        if (commonKeyObj.groupStart && commonKeyObj.groupEnd) {
            delete commonKeyObj.groupStart;
            delete commonKeyObj.groupEnd;
        }
        return commonKeyObj;
    });
    return commonKeys;
}

/**
 * Ensures symmetry across nested arrays based on a specified field and its maximum counts.
 * This function is typically used to normalize data structures where certain fields
 * might have varying occurrences across different sub-arrays, by padding with empty objects.
 * @param {Array<Array<Object>>} arr - An array of arrays, where each inner array contains objects.
 * @param {Object} joinSort - An object containing sorting and placeholder information.
 * @param {Object} joinSort.sort_order - Defines the field to sort by (`sort_by`) and sort direction (`sort_direction`).
 * @param {string} joinSort.sort_order.sort_by - The field name to use for calculating max counts and grouping.
 * @param {string} joinSort.sort_order.sort_direction - The sort direction, e.g., `SortType.DESCENDING`.
 * @param {Array<string>} [joinSort.placeholders] - Optional array of placeholder keys to ensure are present in `maxCounts`.
 * @returns {Array<Array<Object>>} The array with inner arrays made symmetric by padding with empty objects.
 */
export function ensureSymmetry(arr, joinSort) {
    // Step 1: Calculate max counts for the specified field dynamically across all inner arrays.
    const field = joinSort.sort_order.sort_by;
    const sortType = joinSort.sort_order.sort_direction;
    let maxCounts = {};

    arr.forEach(innerArr => {
        let innerArrMaxCounts = {}; // Counts for the current inner array.
        innerArr.forEach(obj => {
            let fieldValue = obj[field];
            if (!innerArrMaxCounts.hasOwnProperty(fieldValue)) {
                innerArrMaxCounts[fieldValue] = 0;
            }
            innerArrMaxCounts[fieldValue]++;
        });
        // Merge counts from the current inner array into the overall maxCounts.
        if (maxCounts) {
            Object.keys(innerArrMaxCounts).forEach(key => {
                if (!maxCounts.hasOwnProperty(key) || maxCounts[key] < innerArrMaxCounts[key]) {
                    maxCounts[key] = innerArrMaxCounts[key];
                }
            });
        } else {
            maxCounts = { ...innerArrMaxCounts };
        }
    });

    // Ensure specified placeholders are included in maxCounts, with a minimum count of 1.
    if (joinSort.placeholders && joinSort.placeholders.length > 0) {
        joinSort.placeholders.forEach(key => {
            if (!maxCounts.hasOwnProperty(key)) {
                maxCounts[key] = 1;
            }
        });
    }

    // Step 2: Ensure symmetry based on calculated max counts.
    let grouped = arr.map(innerArr => {
        // Group objects by the specified field.
        let groupedObj = {};
        // Initialize groupedObj with keys from maxCounts, sorted according to sortType.
        if (sortType === SortType.DESCENDING) {
            Object.keys(maxCounts).sort().reverse().map(key => {
                groupedObj[key] = [];
            });
        } else {
            Object.keys(maxCounts).sort().map(key => {
                groupedObj[key] = [];
            });
        }

        // Populate groupedObj with actual objects from the inner array.
        let grouped = innerArr.reduce((acc, obj) => {
            let fieldValue = obj[field];
            if (!acc[fieldValue]) {
                acc[fieldValue] = [];
            }
            acc[fieldValue].push(obj);
            return acc;
        }, groupedObj);

        // Ensure each group has exactly maxCounts[field] objects by adding empty objects if necessary.
        Object.keys(grouped).forEach((key) => {
            let currentLength = grouped[key].length;
            if (currentLength < maxCounts[key]) {
                // Add empty objects to make it symmetric.
                for (let i = currentLength; i < maxCounts[key]; i++) {
                    grouped[key].push({});
                }
            }
        });

        // Flatten the grouped objects back into an array.
        let result = [];
        Object.keys(grouped).forEach((key) => {
            result.push(...grouped[key]);
        });

        return result;
    });

    return grouped;
}

/**
 * Groups table rows based on an array of grouping fields and optionally applies sorting and symmetry.
 * If `groupByArray` is provided, rows are grouped into nested arrays. Otherwise, each row becomes its own group.
 * If `joinSort` is provided, each group is sorted and then made symmetric.
 * @param {Array<Object>} tableRows - The original array of table row objects.
 * @param {Array<string>} groupByArray - An array of field names (or xpaths) to group the rows by.
 * @param {Object} [joinSort=null] - Optional. An object containing sorting and symmetry configuration.
 * @returns {Array<Array<Object>>} An array of grouped rows. Each element is an array of row objects.
 */
export function getGroupedTableRows(tableRows, groupByArray, joinSort = null) {
    if (groupByArray && groupByArray.length > 0) {
        // Group rows using lodash's groupBy, creating a composite key from grouping fields.
        const groupedRowsDict = groupBy(tableRows, item => {
            const groupKeys = [];
            groupByArray.forEach(groupingField => {
                groupKeys.push(get(item, groupingField));
            });
            return groupKeys.join('_'); // Join keys to form a unique group identifier.
        });
        tableRows = Object.values(groupedRowsDict);

        // If joinSort is provided, sort each inner group and then ensure symmetry.
        if (joinSort) {
            // Sort each group using stableSort based on the provided joinSort configuration.
            tableRows = tableRows.map(rows => stableSort(rows, SortComparator.getInstance([joinSort.sort_order])));
            tableRows = ensureSymmetry(tableRows, joinSort);
        }
    } else {
        // If no grouping fields, each row becomes a single-element array (a group of one).
        tableRows = tableRows.map(row => [row]);
    }
    return tableRows;
}

/**
 * Calculates the maximum size (number of elements) among all inner arrays in a nested array structure.
 * This is useful for determining the widest row in a grouped table structure.
 * @param {Array<Array<Object>>} rows - An array of arrays, where each inner array represents a group of rows.
 * @returns {number} The maximum number of elements found in any inner array. Defaults to 1 if no rows are present.
 */
export function getMaxRowSize(rows) {
    let maxSize = 1;
    // Iterate through each inner array to find the maximum length.
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].length > maxSize) {
            maxSize = rows[i].length;
        }
    }
    return maxSize;
}