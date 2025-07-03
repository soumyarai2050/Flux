

/**
 * Recursively compares two objects to check if a new item has been added to any array within them.
 * This function traverses the objects and their nested arrays/objects.
 * It returns `true` if an array in `obj1` has a different length than the corresponding array in `obj2`,
 * indicating a new item might have been added. It also recursively calls itself for nested objects.
 * @param {Object} obj1 - The first object to compare. It is assumed to be the newer state.
 * @param {Object} obj2 - The second object to compare against. It is assumed to be the older state.
 * @returns {boolean} True if a new array item is detected (based on length difference), false otherwise.
 */
export function compareNCheckNewArrayItem(obj1, obj2) {
    for (const key in obj1) {
        // Check if both properties exist and are arrays.
        if (obj1[key] instanceof Array && obj2[key] instanceof Array) {
            // If array lengths differ, a new item has been added.
            if (obj1[key].length !== obj2[key].length) {
                return true;
            }
            // Recursively check items within the arrays if they are objects.
            for (let i = 0; i < obj1[key].length; i++) {
                // Ensure the corresponding item exists in obj2 before comparing.
                if (obj1[key][i] instanceof Object && obj2[key][i] instanceof Object) {
                    // Recursively call for nested objects within the array.
                    if (compareNCheckNewArrayItem(obj1[key][i], obj2[key][i])) {
                        return true;
                    }
                }
            }
        } else if (obj1[key] instanceof Object && obj2[key] instanceof Object) {
            // Recursively compare nested objects.
            if (compareNCheckNewArrayItem(obj1[key], obj2[key])) {
                return true;
            }
        }
    }
    return false;
}
