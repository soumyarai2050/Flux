import { isObject, isEmpty, get, isEqual } from 'lodash';
import dayjs from 'dayjs';
import { DB_ID, DATA_TYPES, DATE_TIME_FORMATS, primitiveDataTypes } from '../../constants';
import { getLocalizedValueAndSuffix } from '../formatters/numberUtils';
import { getDateTimeFromInt } from '../formatters/dateUtils';
import { mergeObjects } from './dataAccess';


/**
 * Recursively removes properties with `null` values or enum values ending in `_UNSPECIFIED` from an object or array of objects.
 * This function modifies the object(s) in place.
 * @param {Object|Array} obj - The object or array of objects to clean.
 */
export function excludeNullFromObject(obj) {
    /* 
    Function to remove null values from mutable object inplace.
    obj: mutable object
    */
    if (isObject(obj)) {
        for (const key in obj) {
            if (obj[key] === null || (typeof obj[key] === DATA_TYPES.STRING && obj[key].includes('_UNSPECIFIED'))) {
                // delete key with null values or enum with UNSPECIFIED values
                delete obj[key];
            } else if (isObject(obj[key])) {
                excludeNullFromObject(obj[key]);
            } else if (Array.isArray(obj[key])) {
                for (let i = 0; i < obj[key].length; i++) {
                    excludeNullFromObject(obj[key][i]);
                }
            }
            // else not required
        }
    } else if (Array.isArray(obj)) {
        obj.forEach(o => {
            excludeNullFromObject(o);
        });
    }
    // else not required
}

/**
 * Recursively collects all leaf-node paths (paths to primitive values) within an object.
 * @param {Object} obj - The object to traverse.
 * @param {string} [prefix=''] - The current path prefix for recursion.
 * @param {Set<string>} [paths=new Set()] - A Set to store unique paths (used in recursion).
 * @returns {Array<string>} An array of unique paths to primitive values.
 */
function getAllObjectPaths(obj, prefix = '', paths = new Set()) {
    for (const key in obj) {
        const currentPath = prefix ? `${prefix}.${key}` : key;

        if (typeof obj[key] === 'object' && obj[key] !== null) {
            if (Array.isArray(obj[key])) {
                obj[key].forEach((item) => {
                    getAllObjectPaths(item, currentPath, paths);
                })
            } else {
                getAllObjectPaths(obj[key], currentPath, paths);
            }
        } else {
            paths.add(currentPath);  // Add path for primitive values
        }
    }
    return Array.from(paths);  // Covert set to array
}


export function compareJSONObjects(obj1, obj2, fieldsMetadata, isCreate = false) {
    /* 
    Function to compare two objects and clear null fields from diff
    obj1: initial / original object
    obj2: currrent object
    */
    if (!checkConstraints(obj1, obj2)) {
        return null;
    }
    let diff = {};
    if (isObject(obj1) && isObject(obj2)) {
        diff = getObjectsDiff(obj1, obj2);
    } else if (isObject(obj2)) {
        diff = obj2;
    }
    if (Object.keys(diff).length > 0) {
        // add the object ID if diff found and ID exists on initial object
        if (DB_ID in obj1) {
            diff[DB_ID] = obj1[DB_ID];
        } else {
            // removing null fields from diff if no ID exists on initial object
            excludeNullFromObject(diff);
        }
    }
    let confirmationCaptionDict = null;
    if (fieldsMetadata) {
        let subFieldsMetadata = [];
        fieldsMetadata
            .filter((meta) => meta.subCollections)
            .forEach((meta) => {
                subFieldsMetadata = [...subFieldsMetadata, ...meta.subCollections];
            })
        const combinedFieldsMetadata = [...fieldsMetadata, ...subFieldsMetadata];
        const paths = getAllObjectPaths(diff);

        for (const path of paths) {
            // ignore DB_ID
            if (path === DB_ID) {
                continue;
            }

            const metadata = combinedFieldsMetadata.find(col => col.tableTitle === path);

            if (!metadata) {
                const err_ = `ERROR: no collection obj (metadata) found for path: ${path}, likely UI bug. Please send screenshot to DEV for investigation`;
                console.error(err_);
                alert(err_);
                diff = null;
                return;
            }  // else not required - collection obj exists

            if (metadata.key === DB_ID) {
                continue;
            }

            if (metadata.serverPopulate) {
                const err_ = `CRITICAL: Update request discarded, unmodifiable field found in patch update for path: ${path}, likely UI bug. Please send screenshot to DEV for investigation`;
                console.error(err_);
                alert(err_);
                diff = null;
                return;
            }  // else not required - field is modifiable from UI

            if (metadata.type === 'button' && metadata.button.confirmation_caption) {
                const { confirmation_caption, confirmation_style = 'info' } = metadata.button;
                if (!confirmationCaptionDict) {
                    confirmationCaptionDict = {};
                }
                confirmationCaptionDict[path] = {
                    caption: confirmation_caption,
                    style: confirmation_style
                };
            }
        }
    }
    return [diff, confirmationCaptionDict];
}


/**
 * Computes the difference between two objects, `obj1` (initial) and `obj2` (current).
 * It recursively compares properties, handling nested objects and arrays.
 * For arrays, it identifies added, deleted, and modified items based on `DB_ID`.
 * @param {Object} obj1 - The initial or original object.
 * @param {Object} obj2 - The current or updated object.
 * @returns {Object} A `diff` object containing only the properties that have changed or been added.
 */
export function getObjectsDiff(obj1, obj2) {
    /* 
    Function to get difference between two objects.
    obj1: initial object
    obj2: current object
    */

    /**
     * Compares two arrays of objects and identifies differences (added, deleted, modified items).
     * Assumes array items are objects and have a `DB_ID` for identification.
     * @param {Array<Object>} arr1 - The initial array.
     * @param {Array<Object>} arr2 - The current array.
     * @returns {Array<Object>} An array containing the differences.
     */
    function compareArrays(arr1, arr2, parentKey) {
        /* 
        Function to compare two arrays containing items of type object.
        arr1: array of initial object
        arr2: array of current object
        */
        let arrDiff = [];

        arr1.forEach(element1 => {
            if (element1 instanceof Object && DB_ID in element1) {
                const found = arr2.some(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
                if (!found) {
                    // deleted item in array. store the array object ID in the diff
                    arrDiff.push({ [DB_ID]: element1[DB_ID] });
                } else {
                    // array object found with matching object ID. compare the nested object
                    let element2 = arr2.find(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
                    let nestedDiff = getObjectsDiff(element1, element2);
                    if (!isEmpty(nestedDiff)) {
                        // store the diff along with the nested object ID
                        arrDiff.push({ [DB_ID]: element1[DB_ID], ...nestedDiff });
                    }
                }
            }
        });

        arr2.forEach(element2 => {
            if (element2 instanceof Object && !(DB_ID in element2)) {
                // new item in the array. store the entire item in diff
                arrDiff.push(element2);
            }
            // else {
            //    // compare arrays of primitive data types
            //    if (!isEqual(arr1, arr2)) {
            //        arrDiff = arr2;
            //    }
            //
            //}
        })

        return arrDiff;
    }

    let diff = {};

    if (obj1 instanceof Object) {
        for (const key in obj1) {
            if (obj2 instanceof Object && obj2.hasOwnProperty(key)) {
                if (obj1[key] instanceof Array) {
                    if (obj2[key] instanceof Array) {
                        const arrDiff = compareArrays(obj1[key], obj2[key]);
                        if (!isEmpty(arrDiff)) {
                            diff[key] = arrDiff;
                        }
                        // else not required: no difference found
                    } else {
                        diff[key] = obj2[key];
                    }
                } else if (obj1[key] instanceof Object) {
                    if (obj2[key] instanceof Object) {
                        const nestedDiff = getObjectsDiff(obj1[key], obj2[key]);
                        if (!isEmpty(nestedDiff)) {
                            diff[key] = nestedDiff;
                        }
                        // else not required: no difference found
                    } else {
                        diff[key] = obj2[key];
                    }
                } else if (obj1[key] !== obj2[key]) {
                    diff[key] = obj2[key];
                }
            } else {
                diff = obj2;
            }
        }
    }

    if (obj2 instanceof Object) {
        for (const key in obj2) {
            if (obj1 instanceof Object && !obj1.hasOwnProperty(key)) {
                if (!diff.hasOwnProperty(key)) {
                    diff[key] = obj2[key];
                }
            }
        }
    }

    return diff;
}



/**
 * Merges two arrays of objects based on their `DB_ID` property.
 * If an item from `arr2` has a matching `DB_ID` in `mergedArr` (initially `arr1`),
 * their properties are merged using `mergeObjects`. Otherwise, the item from `arr2` is added to `mergedArr`.
 * @param {Array<Object>} arr1 - The base array.
 * @param {Array<Object>} arr2 - The array to merge into the base array.
 * @returns {Array<Object>} A new array containing the merged results.
 */
export function mergeArrays(arr1, arr2) {
    const mergedArr = [...arr1];

    for (const item2 of arr2) {
        const matchingItem = mergedArr.find((item1) => item1[DB_ID] === item2[DB_ID]);
        if (matchingItem) {
            const index = mergedArr.indexOf(matchingItem);
            mergedArr[index] = mergeObjects(matchingItem, item2);
        } else {
            mergedArr.push(item2);
        }
    }

    return mergedArr;
}



/**
 * Checks if an object is empty (has no enumerable own properties).
 * @param {Object} obj - The object to check.
 * @returns {boolean} `true` if the object is empty, `false` otherwise.
 */
export function isEmptyObject(obj) {
    return Object.keys(obj).length === 0;
}


/**
 * Recursively removes the `DB_ID` property from an object and its nested objects/arrays.
 * This function modifies the object(s) in place.
 * @param {Object} obj - The object from which `DB_ID` properties will be removed.
 */
export function clearId(obj) {
    if (isObject(obj)) {
        if (obj.hasOwnProperty(DB_ID)) {
            delete obj[DB_ID];
        }
        Object.entries(obj).forEach(([k, v]) => {
            if (Array.isArray(v)) {
                v.forEach(o => {
                    if (isObject(o)) {
                        clearId(o);
                    } // else not required - simple data type array
                })
            } else if (isObject(v)) {
                clearId(v);
            } // else not required - simple data type field
        })
    } else {
        const err_ = 'clearId failed, expected obj of type Object, received: ' + typeof obj;
        console.error(err_);
    }
}


/**
 * Checks if an object has a specified property and if its value is not `null` or `undefined`.
 * This is an extended version of `Object.prototype.hasOwnProperty.call()`.
 * @param {Object} obj - The object to check.
 * @param {string} property - The name of the property to check for.
 * @returns {boolean} `true` if the object has the property and its value is not `null` or `undefined`, `false` otherwise.
 */
export function hasOwnProperty(obj, property) {
    /* extended hasOwnProperty check with check for null values */
    if (obj.hasOwnProperty(property)) {
        if (obj[property] !== null && obj[property] !== undefined) {
            return true;
        }
    }
    return false;
}



/**
 * Checks for critical constraints between a stored object and an updated object.
 * Currently, it verifies that the `DB_ID` of both objects are identical if they exist.
 * If a mismatch is found, it logs an error and alerts the user.
 * @param {Object} storedObj - The object representing the stored state.
 * @param {Object} updatedObj - The object representing the updated state.
 * @returns {boolean} `true` if all constraints are met, `false` otherwise.
 */
export function checkConstraints(storedObj, updatedObj) {
    // DB_ID constraints - stored and updated obj DB_ID should be same
    if (storedObj.hasOwnProperty(DB_ID) && updatedObj.hasOwnProperty(DB_ID) && storedObj[DB_ID] !== updatedObj[DB_ID]) {
        const err_ = `CRITICAL: mismatch DB_ID found while preparing patch update. storedObj DB_ID: ${storedObj[DB_ID]}, 
        updatedObj DB_ID: ${updatedObj[DB_ID]}. Please send a screenshot to DEV for investigation;;;${JSON.stringify({ storedObj })}; 
        ${JSON.stringify({ updatedObj })}`;
        console.error(err_);
        alert(err_);
        return false;
    } // else not required - DB_ID check passed
    return true;
}


export function formatJSONObjectOrArray(json, fieldProps) {

    /**
     * Helper function to format an array of JSON objects.
     * @param {Array<Object>} arr - The array to format.
     * @param {Array<Object>} fieldProps - Field properties.
     */
    function formatJSONArray(arr, fieldProps) {
        for (let i = 0; i < arr.length; i++) {
            if (arr[i] instanceof Object) {
                formatJSONObjectOrArray(arr[i], fieldProps);
            }
        }
    }

    if (json instanceof Array) {
        formatJSONArray(json, fieldProps);
    } else if (json instanceof Object) {
        for (const key in json) {
            if (key.includes('xpath')) {
                continue;
            }
            const prop = fieldProps.find(p => p.key === key);
            if (prop) {
                if (json[key] instanceof Array) {
                    formatJSONArray(json[key], fieldProps);
                } else if (json[key] instanceof Object) {
                    formatJSONObjectOrArray(json[key], fieldProps);
                } else if (prop.type === DATA_TYPES.DATE_TIME) {
                    if (json[key]) {
                        const dateTimeWithTimezone = getDateTimeFromInt(json[key]);
                        if (prop.displayType === 'date') {
                            json[key] = dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATE);
                        } else if (prop.displayType === 'datetime') {
                            json[key] = dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATETIME);
                        } else {
                            json[key] = dateTimeWithTimezone.isSame(dayjs(), 'day') ? dateTimeWithTimezone.format(DATE_TIME_FORMATS.TIME) : dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATETIME);
                        }
                    }
                } else if (typeof json[key] === DATA_TYPES.NUMBER) {
                    const [suffix, v] = getLocalizedValueAndSuffix(prop, json[key]);
                    json[key] = v.toLocaleString() + suffix;
                }
                if (prop.hide) {
                    delete json[key];
                }
            }
        }
    }
}


/**
 * Recursively compares two objects (`updated` and `original`) and identifies paths to changed primitive values.
 * The `diff` array is populated with XPath-like strings representing these changed paths.
 * @param {Object} updated - The updated object.
 * @param {Object} original - The original object to compare against.
 * @param {Object} current - The current object being traversed (initially same as `updated`).
 * @param {string} [xpath] - The current XPath being built during recursion.
 * @param {Array<string>} [diff=[]] - An array to store the XPath of changed primitive values.
 */
export function compareObjects(updated, original, current, xpath, diff = []) {
    Object.entries(current).map(([k, v]) => {
        if (primitiveDataTypes.includes(typeof (v))) {
            let updatedxpath = xpath ? xpath + '.' + k : k;
            if ((!get(original, updatedxpath) && get(original, updatedxpath) !== false && get(original, updatedxpath) !== 0) || !isEqual(get(updated, updatedxpath), get(original, updatedxpath))) {
                if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                let updatedxpath = xpath ? xpath + '.' + k + '[' + i + ']' : k + '[' + i + ']';
                if (primitiveDataTypes.includes(typeof (v[0]))) {
                    if ((!get(original, updatedxpath) && get(original, updatedxpath) !== false && get(original, updatedxpath) !== 0) || !isEqual(get(updated, updatedxpath), get(original, updatedxpath))) {
                        if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
                    }
                } else {
                    compareObjects(updated, original, current[k][i], updatedxpath, diff);
                }
            }
        } else if (isObject(v)) {
            let updatedxpath = xpath ? xpath + '.' + k : k;
            compareObjects(updated, original, current[k], updatedxpath, diff);
        }
    })
    return diff;
}

