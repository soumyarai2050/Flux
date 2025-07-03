import { get, cloneDeep, isObject, isNull, isEqual } from 'lodash';
import { DB_ID, DATA_TYPES, primitiveDataTypes } from '../../constants';
import { mergeArrays } from './objectUtils';


/**
 * Resolves a given XPath-like string to an actual data path within a JavaScript object.
 * This function is crucial for navigating complex, potentially nested data structures where
 * array indices might change due to dynamic updates. It reconstructs the path by matching
 * `xpath_` prefixed properties in the data.
 * @param {Object} data - The JavaScript object to navigate.
 * @param {string} xpath - The XPath-like string (e.g., 'field1[0].nestedField', '[0].rootField').
 * @returns {string|undefined} The resolved data path if found, otherwise `undefined`.
 */
export function getDataxpath(data, xpath) {
    if (!xpath) return;
    if (xpath.includes('-1')) return xpath;
    let updatedxpath = '';
    let originalxpath = '';
    // Iterate through each segment of the xpath, split by ']' to handle array indices.
    for (let i = 0; i < xpath.split(']').length - 1; i++) {
        let currentxpath = xpath.split(']')[i];
        let index = currentxpath.split('[')[1];
        currentxpath = currentxpath.split('[')[0];
        originalxpath = originalxpath + currentxpath + '[' + index + ']';

        let found = false;
        if (get(data, updatedxpath + currentxpath)) {
            // Iterate through array elements to find a match based on 'xpath_' properties.
            get(data, updatedxpath + currentxpath).forEach((obj, idx) => {
                let propname = Object.keys(obj).find(key => key.startsWith('xpath_'));
                if (!propname) return; // Skip if no 'xpath_' property is found.
                let propxpath = obj[propname].substring(0, obj[propname].lastIndexOf('.'));
                // If the 'xpath_' property matches the original xpath segment, update the index.
                if (propxpath === originalxpath) {
                    index = idx;
                    found = true;
                }
            })
        } else if (xpath.startsWith('[')) {  // Special handling for repeated root widgets where xpath starts with an array.
            found = true;
        }
        if (found) {
            updatedxpath = updatedxpath + currentxpath + '[' + index + ']';
        } else {
            return;
        }
    }
    // Append the final part of the xpath (after the last ']').
    updatedxpath = updatedxpath + xpath.split(']')[xpath.split(']').length - 1];
    return updatedxpath;
}


// Optimized version that uses a cache when available
/**
 * Resolves a given XPath-like string to an actual data path within a JavaScript object, utilizing a cache for performance.
 * This function first attempts to retrieve the resolved path from the `xpathCache`. If found, it reconstructs the path
 * using the cached index. If not found in the cache, it falls back to the `getDataxpath` function for resolution.
 * @param {Object} data - The JavaScript object to navigate.
 * @param {string} xpath - The XPath-like string (e.g., 'field1[0].nestedField').
 * @param {Map<string, number>} xpathCache - A cache mapping xpaths to their resolved array indices.
 * @returns {string|undefined} The resolved data path if found, otherwise `undefined`.
 */
export function getDataxpathWithCache(data, xpath, xpathCache) {
    // Return early if xpath is null, undefined, or contains a special '-1' indicator.
    if (!xpath) return;
    if (xpath.includes('-1')) return xpath;
    
    // If we have a cache and the xpath is directly in it, use it
    if (xpathCache && xpathCache.has(xpath)) {
        const cachedIndex = xpathCache.get(xpath);
        // Build the data path using the cached index
        const pathParts = xpath.split(/[\[\]]/); // Split xpath into parts (field names and indices).
        let dataPath = '';
        for (let i = 0; i < pathParts.length; i++) {
            if (i % 2 === 0) {
                // Property name
                dataPath += pathParts[i];
            } else {
                // Index - use cached value for the final array index
                if (i === pathParts.length - 2 && cachedIndex !== undefined) {
                    dataPath += '[' + cachedIndex + ']';
                } else {
                    dataPath += '[' + pathParts[i] + ']';
                }
            }
        }
        return dataPath;
    }
    
    // Fallback to regular getDataxpath if not found in cache.
    return getDataxpath(data, xpath);
}


// ID-based data path resolution - much faster after index shifts
/**
 * Resolves a given XPath-like string to an actual data path within a JavaScript object,
 * prioritizing ID-based lookup for faster resolution after index shifts.
 * This function attempts to find the item in `storedData` using the provided `xpath`,
 * then uses its `_id` to query the `cacheManager` for the current data path. If a valid
 * cached path is found and the item still exists at that path, it's returned. Otherwise,
 * it falls back to the `getDataxpath` function for resolution.
 * @param {Object} data - The current JavaScript object to navigate.
 * @param {string} xpath - The XPath-like string (e.g., 'field1[0].nestedField').
 * @param {Object} storedData - The previously stored data object, used to retrieve the original item by xpath.
 * @param {Object} cacheManager - An object with a `getDataPathById` method for ID-based path lookup.
 * @returns {string|undefined} The resolved data path if found, otherwise `undefined`.
 */
export function getDataxpathById(data, xpath, storedData, cacheManager) {
    if (!xpath || !xpath.endsWith(']') || !storedData || !cacheManager) {
        return getDataxpath(data, xpath); 
    }
    
    try {
        // Get the item from stored data using schema path.
        const originalItem = get(storedData, xpath);
        // If the original item exists and has an _id, try to find its current path using the cache.
        if (originalItem && typeof originalItem === 'object' && originalItem._id) {
            // Try to get current data path from ID cache
            const cachedDataPath = cacheManager.getDataPathById(originalItem._id);
            if (cachedDataPath) {
                // Verify the item still exists at this path and its _id matches.
                const currentItem = get(data, cachedDataPath);
                if (currentItem && currentItem._id === originalItem._id) {
                    return cachedDataPath;
                }
            }
        }
    } catch (error) {
        console.warn('ID-based lookup failed:', error);
    }
    
    // Fallback to normal resolution if ID-based lookup fails.
    return getDataxpath(data, xpath);
}


/**
 * Resolves a given XPath-like string to an actual data path within a JavaScript object.
 * This is an optimized version of `getDataxpath` that aims for better performance
 * by caching split operations and using a `for` loop for early exit.
 * It reconstructs the path by matching `xpath_` prefixed properties in the data.
 * @param {Object} data - The JavaScript object to navigate.
 * @param {string} xpath - The XPath-like string (e.g., 'field1[0].nestedField', '[0].rootField').
 * @returns {string|undefined} The resolved data path if found, otherwise `undefined`.
 */
export function getDataxpathV2(data, xpath) {
    // Early returns for edge cases
    if (!xpath) return;
    if (xpath.includes('-1')) return xpath;

    // Cache the split operation to avoid repeated splits
    const xpathParts = xpath.split(']');
    const partsLength = xpathParts.length - 1;

    // Handle special case for repeated root widget
    const isRepeatedRoot = xpath.startsWith('[');

    let updatedXpath = '';
    let originalXpath = '';

    for (let i = 0; i < partsLength; i++) {
        const currentPart = xpathParts[i];
        const bracketIndex = currentPart.indexOf('[');

        // Extract current xpath and index more efficiently
        const currentXpath = currentPart.substring(0, bracketIndex);
        let index = currentPart.substring(bracketIndex + 1);

        originalXpath += currentXpath + '[' + index + ']';

        let found = isRepeatedRoot && i === 0; // Handle repeated root case

        if (!found) {
            const dataAtPath = get(data, updatedXpath + currentXpath);

            if (dataAtPath?.length) {
                // Use for loop instead of forEach for better performance and early exit
                for (let idx = 0; idx < dataAtPath.length; idx++) {
                    const obj = dataAtPath[idx];

                    // Find xpath property more efficiently
                    const xpathProp = Object.keys(obj).find(key => key.startsWith('xpath_'));

                    if (xpathProp) {
                        const propXpath = obj[xpathProp].substring(0, obj[xpathProp].lastIndexOf('.'));

                        if (propXpath === originalXpath) {
                            index = idx;
                            found = true;
                            break; // Early exit when found
                        }
                    }
                }
            }
        }

        if (found) {
            updatedXpath += currentXpath + '[' + index + ']';
        } else {
            return; // Early return if not found
        }
    }

    // Append the final part (after the last ']')
    return updatedXpath + xpathParts[partsLength];
}


/**
 * Recursively adds XPath-like properties to all primitive values within a JavaScript object or array.
 * These `xpath_` properties store the full path to each primitive value, enabling later resolution
 * of data paths even if array indices change.
 * @param {Object|Array} jsondata - The data structure to which XPath properties will be added.
 * @param {string} [xpath] - The base XPath for the current `jsondata` (used in recursive calls).
 * @returns {Object|Array} The `jsondata` with XPath properties added.
 */
export function addxpath(jsondata, xpath) {
    if (Array.isArray(jsondata)) {
        for (let i = 0; i < jsondata.length; i++) {
            let dataxpath = "[" + i + "]";
            if (xpath) {
                dataxpath = xpath + dataxpath;
            }
            _addxpath(jsondata[i], dataxpath)
        }
    } else if (isObject(jsondata)) {
        _addxpath(jsondata, xpath);
    }
    return jsondata;
}


/**
 * Internal helper function for `addxpath`.
 * Recursively adds XPath-like properties to primitive values within a single JavaScript object.
 * @param {Object} jsondata - The object to which XPath properties will be added.
 * @param {string} xpath - The base XPath for the current `jsondata`.
 */
function _addxpath(jsondata, xpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (isNull(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (Array.isArray(v)) {
            if (v.length > 0 && isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    let childxpath = xpath ? `${xpath}.${k}[${i}]` : `${k}[${i}]`;
                    addxpath(jsondata[k][i], childxpath);
                }
            } else {
                jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            }
        } else if (isObject(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            let childxpath = xpath ? xpath + '.' + k : k;
            addxpath(jsondata[k], childxpath)
        }
        return;
    });
}


/**
 * Recursively removes XPath-like properties (`xpath_` prefixed) and `data-id` properties
 * from a JavaScript object or array. This is typically used to clean up data before
 * sending it to a backend or for display purposes where these internal properties are not needed.
 * @param {Object|Array} jsondata - The data structure from which XPath properties will be removed.
 * @returns {Object|Array} The `jsondata` with XPath properties removed.
 */
export function clearxpath(jsondata) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            // remove data-id for repeated_root model_types
            if (k.startsWith('xpath_') || k === 'data-id') {
                delete jsondata[k];
            }
        } else if (Array.isArray(v)) {
            if (v.length > 0 && isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    clearxpath(jsondata[k][i]);
                }
            }
        } else if (isObject(v)) {
            clearxpath(jsondata[k])
        }
    });
    return jsondata;
}


/**
 * Generates a list of tree-like structures (rows) from a given JSON data object or array.
 * This function is used to transform flat data into a hierarchical representation suitable for tree views.
 * It can optionally process a subset of the data specified by an XPath.
 * @param {Object|Array} jsondata - The source JSON data.
 * @param {Array<Object>} collections - An array of collection definitions, used for processing abbreviated JSON.
 * @param {string} [xpath] - An optional XPath to specify a subset of `jsondata` to process.
 * @returns {Array<Object>} An array of tree-like objects, each representing a row.
 */
export function generateRowTrees(jsondata, collections, xpath) {
    const trees = [];
    // if xpath is present, jsondata is subset of data
    if (xpath) {
        jsondata = get(jsondata, xpath);
    }
    if (!jsondata) {
        return trees;
    }

    while (true) {
        if (Array.isArray(jsondata)) {
            for (let i = 0; i < jsondata.length; i++) {
                let tree = {};
                createTree(tree, jsondata[i], null, { delete: 1 }, collections);

                if (Object.keys(tree).length === 0) break;

                // Assign a data-id to the tree, typically from the DB_ID.
                tree['data-id'] = jsondata[i][DB_ID];

                if (trees.length > 0 && isEqual(trees[trees.length - 1], tree)) {
                    continue;
                }
                trees.push(tree);
            }
            break;
        } else {
            let tree = {};
            Object.entries(jsondata).map(([k, v]) => {
                if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
                    tree[k] = v;
                } else if (isNull(v)) {
                    tree[k] = null;
                } else if (Array.isArray(v)) {
                    tree[k] = [];
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections);
                    if (tree[k][0]?.hasOwnProperty('data-id')) {
                        tree['data-id'] = tree[k][0]['data-id'];
                    }
                } else if (isObject(v)) {
                    tree[k] = {};
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections);
                }
            })

            if (Object.keys(tree).length === 0) break;

            if (!constainsArray(tree)) {
                tree['data-id'] = 0;
            }

            if (trees.length > 0 && isEqual(trees[trees.length - 1], tree)) {
                break;
            }
            trees.push(tree);
        }
    }
    return trees;
}


/**
 * Recursively checks if an object or any of its nested objects/arrays contain an array.
 * @param {Object} obj - The object to check.
 * @returns {boolean} `true` if the object or its descendants contain an array, `false` otherwise.
 * @throws {Error} If the input `obj` is not an object or null.
 */
function constainsArray(obj) {
    if (isObject(obj)) {
        for (const key in obj) {
            if (Array.isArray(obj[key])) {
                return true;
            } else if (isObject(obj[key])) {
                const hasArray = constainsArray(obj[key]);
                if (hasArray) {
                    return true;
                }
            }
        }
    } else if (obj === null) {
        return false;
    } else {
        throw new Error('constainsArray function failed. unsupported obj type: ' + typeof obj + ', expected object type.')
    }
    return false;
}


/**
 * Recursively builds a tree structure from a JSON object or array.
 * This function is a helper for `generateRowTrees` and handles the hierarchical transformation
 * of data, including special handling for abbreviated JSON and `data-id` assignment.
 * @param {Object} tree - The tree object being built (passed by reference).
 * @param {Object|Array} currentjson - The current JSON data being processed.
 * @param {string|null} propname - The name of the property in the parent `tree` that `currentjson` corresponds to.
 * @param {Object} count - An object used to manage deletion count for array processing.
 * @param {Array<Object>} collections - An array of collection definitions, used for processing abbreviated JSON.
 */
function createTree(tree, currentjson, propname, count, collections) {
    if (Array.isArray(currentjson)) {
        if (currentjson.length === 0) return;

        tree[propname] = [];
        if (collections.some(c => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
            tree[propname] = currentjson;
        } else {
            if (currentjson[0] === null || currentjson[0] === undefined || primitiveDataTypes.includes(typeof currentjson[0])) {
                return;
            } else {
                let node = {};
                tree[propname].push(node);
                let xpath = currentjson[0][Object.keys(currentjson[0]).find(k => k.startsWith('xpath_'))];
                xpath = xpath ? xpath.substring(0, xpath.lastIndexOf('.')) : xpath;
                node['data-id'] = currentjson[0].hasOwnProperty(DB_ID) ? currentjson[0][DB_ID] : xpath;
                createTree(tree[propname], currentjson[0], 0, count, collections);
                if (currentjson.length > 1 && count.delete > 0) {
                    count.delete -= 1;
                    currentjson.splice(0, 1);
                }
            }
        }
    } else if (isNull(currentjson)) {
        tree[propname] = null;
    } else if (isObject(currentjson)) {
        if (collections.some(c => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
            tree[propname] = currentjson;
        } else {
            let node = tree[propname];
            if (!node) {
                node = tree;
            }
            Object.entries(currentjson).map(([k, v]) => {
                if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
                    node[k] = v;
                } else if (isNull(v)) {
                    node[k] = null;
                } else if (Array.isArray(v)) {
                    node[k] = [];
                    createTree(node, currentjson[k], k, count, collections);
                    if (node[k][0]?.hasOwnProperty('data-id')) {
                        node['data-id'] = node[k][0]['data-id'];
                    }
                } else if (isObject(v)) {
                    node[k] = {};
                    createTree(node, currentjson[k], k, count, collections);
                }
            })
        }
    }
}



/**
 * Recursively flattens a nested JavaScript object into a single-level object.
 * This function is used to transform hierarchical data into a flat structure,
 * optionally preserving a specific XPath and handling abbreviated JSON.
 * @param {Object} jsondata - The nested JSON data to flatten.
 * @param {Object} object - The object to which flattened properties will be added (passed by reference).
 * @param {Array<Object>} collections - An array of collection definitions, used for processing abbreviated JSON.
 * @param {string} [xpath] - An optional XPath to specify a subset of `jsondata` to flatten.
 * @param {string} [parentxpath] - The XPath of the parent object (used in recursive calls).
 */
function flattenObject(jsondata, object, collections, xpath, parentxpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            if (parentxpath && k !== 'data-id') {
                if (xpath && xpath === parentxpath) {
                    object[k] = v;
                } else {
                    object[parentxpath + '.' + k] = v;
                }
            } else {
                object[k] = v;
            }
        } else if (isNull(v)) {
            if (parentxpath) {
                if (xpath && xpath === parentxpath) {
                    object[k] = v;
                } else {
                    object[parentxpath + '.' + k] = v;
                }
            } else {
                object[k] = v;
            }
        } else if (Array.isArray(v)) {
            if (collections.some((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
                if (parentxpath) {
                    object[parentxpath + '.' + k] = v;
                } else {
                    object[k] = v;
                }
            } else if (v.length > 0) {
                let updatedParentxpath = parentxpath ? parentxpath + '.' + k : k;
                flattenObject(jsondata[k][0], object, collections, xpath, updatedParentxpath);
            }
        } else if (isObject(v)) {
            if (collections.some((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
                if (parentxpath) {
                    object[parentxpath + '.' + k] = v;
                } else {
                    object[k] = v;
                }
            } else {
                let updatedParentxpath = parentxpath ? parentxpath + '.' + k : k;
                flattenObject(jsondata[k], object, collections, xpath, updatedParentxpath);
            }
        }
    });
}


/**
 * Converts a list of tree-like objects (generated by `generateRowTrees`) into a flat array of rows.
 * Each tree is flattened into a single row using `flattenObject`.
 * @param {Array<Object>} trees - An array of tree-like objects.
 * @param {Array<Object>} collections - An array of collection definitions, passed to `flattenObject`.
 * @param {string} [xpath] - An optional XPath, passed to `flattenObject`.
 * @returns {Array<Object>} A flat array of row objects.
 */
export function generateRowsFromTree(trees, collections, xpath) {
    let rows = [];
    trees.forEach((tree) => {
        let row = {};
        flattenObject(tree, row, collections, xpath);
        if (Object.keys(row).length > 0) {
            rows.push(row);
        }
    })
    return rows;
}


/**
 * Recursively extracts key-value pairs from an object, where the key is the XPath
 * of the value (derived from `xpath_` properties).
 * @param {Object} object - The object to extract key-value pairs from.
 * @param {Object} [dict={}] - The dictionary to populate with XPath-value pairs (used in recursive calls).
 * @returns {Object} A dictionary mapping XPath strings to their corresponding values.
 */
export function getXpathKeyValuePairFromObject(object, dict = {}) {
    Object.entries(object).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (isNull(v)) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                getXpathKeyValuePairFromObject(object[k][i], dict);
            }
        } else if (isObject(v)) {
            getXpathKeyValuePairFromObject(object[k], dict);
        }
        return;
    });
    return dict;
}


/**
 * Creates a single merged object from a dictionary of XPath-value pairs.
 * This function iterates through the dictionary, creating a partial object for each XPath-value pair
 * using `createObjectFromXpathDict`, and then merges these partial objects into a single result.
 * @param {Object} obj - The base object to use for creating new objects (typically contains `DB_ID`).
 * @param {Object} dict - A dictionary mapping XPath strings to their corresponding values.
 * @returns {Object} A single merged object constructed from the XPath-value pairs.
 */
export function createObjectFromDict(obj, dict = {}) {
    let objArray = [];
    Object.entries(dict).map(([k, v]) => {
        let updatedObj = createObjectFromXpathDict(obj, k, v);
        objArray.push(updatedObj);
        return;
    })
    let mergedObj = {};
    objArray.forEach(obj => {
        mergedObj = mergeObjects(mergedObj, obj);
    })
    return mergedObj;
}


/**
 * Creates a nested JavaScript object from a single XPath and its corresponding value.
 * This function constructs the object structure based on the XPath, assigning the value
 * at the specified path. It also handles array indices within the XPath.
 * @param {Object} obj - The base object to use for cloning existing data (typically contains `DB_ID`).
 * @param {string} xpath - The XPath string representing the path to the value (e.g., 'field1.nestedField[0].value').
 * @param {*} value - The value to be assigned at the specified XPath.
 * @returns {Object} A new object with the value assigned at the given XPath.
 */
export function createObjectFromXpathDict(obj, xpath, value) {
    let o = { [DB_ID]: obj[DB_ID] };
    let currentObj = o;
    let currentXpath;
    xpath.split('.').forEach((f, i) => {
        currentXpath = currentXpath ? currentXpath + '.' + f : f;
        let fieldName = f.indexOf('[') === -1 ? f : f.substring(0, f.indexOf('['));
        let fieldType = f.indexOf('[') === -1 ? DATA_TYPES.OBJECT : DATA_TYPES.ARRAY;
        Object.keys(currentObj).forEach(k => {
            if (k !== DB_ID) {
                delete currentObj[k];
            }
        })
        if (fieldType === DATA_TYPES.OBJECT) {
            currentObj[fieldName] = cloneDeep(get(obj, currentXpath));
            if (i === xpath.split('.').length - 1) {
                currentObj[fieldName] = value;
            }
            currentObj = currentObj[fieldName];
        } else {
            currentObj[fieldName] = [cloneDeep(get(obj, currentXpath))];
            currentObj = currentObj[fieldName][0];
        }
    })
    return o;
}


/**
 * Finds the object with the smallest `DB_ID` from an array of objects.
 * The input array is cloned to avoid modifying the original, and then sorted based on `DB_ID`.
 * @param {Array<Object>} objectArray - An array of objects, each expected to have a `DB_ID` property.
 * @returns {Object} The object with the least `DB_ID`.
 */
export function getObjectWithLeastId(objectArray) {
    objectArray = cloneDeep(objectArray);
    objectArray.sort(function (a, b) {
        if (a[DB_ID] > b[DB_ID]) {
            return 1;
        }
        return -1;
    });
    return objectArray[0];
}



/**
 * Checks if a given XPath exists in the data and has a non-null/non-undefined value.
 * It also considers 0, false, and empty string as valid existing values.
 * @param {Object} data - The data object to check within.
 * @param {string} xpath - The XPath to check for existence.
 * @returns {boolean} `true` if the XPath exists and has a value (including 0, false, or empty string), `false` otherwise.
 */
export function hasxpath(data, xpath) {
    if (get(data, xpath)) return true;
    else {
        let value = get(data, xpath);
        if (value === 0 || value === false || value === '') return true;
    }
    return false;
}


/**
 * Merges two JavaScript objects, handling nested objects and arrays recursively.
 * If both objects have the same property, arrays are merged using `mergeArrays`,
 * nested objects are merged recursively, and primitive values from `obj1` take precedence.
 * @param {Object} obj1 - The primary object to merge.
 * @param {Object} obj2 - The secondary object to merge.
 * @returns {Object} A new object representing the merged result.
 */
export function mergeObjects(obj1, obj2) {
    const mergedObj = {};

    for (const prop in obj1) {
        if (obj1.hasOwnProperty(prop)) {
            if (Array.isArray(obj1[prop]) && Array.isArray(obj2[prop])) {
                mergedObj[prop] = mergeArrays(obj1[prop], obj2[prop]);
            } else if (typeof obj1[prop] === DATA_TYPES.OBJECT && typeof obj2[prop] === DATA_TYPES.OBJECT) {
                mergedObj[prop] = mergeObjects(obj1[prop], obj2[prop]);
            } else {
                mergedObj[prop] = obj1[prop];
            }
        }
    }

    for (const prop in obj2) {
        if (obj2.hasOwnProperty(prop) && !mergedObj.hasOwnProperty(prop)) {
            mergedObj[prop] = obj2[prop];
        }
    }

    return mergedObj;
}