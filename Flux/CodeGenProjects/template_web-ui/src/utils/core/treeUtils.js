import { get, isEqual, cloneDeep } from 'lodash';
import { DATA_TYPES, MODES, ITEMS_PER_PAGE, primitiveDataTypes } from '../../constants';
import { fieldProps, complexFieldProps } from './schemaConstants';
import { getModelSchema, getEnumValues, getAutocompleteDict, getMetaFieldDict, getMappingSrcDict, setAutocompleteValue } from './schemaUtils';
import { getDataxpath, hasxpath } from './dataAccess';


// stores the tree expand/collapse states
export const treeState = {};

/**
 * Checks if a given node (identified by its XPath) is part of a specified subtree.
 * This function is primarily used to determine if a node should be rendered or processed
 * within the context of a collapsed or expanded subtree in the UI.
 * @param {Object} callerProps - Properties from the calling component, including `subtree` and `xpath`.
 * @param {string} xpath - The XPath of the node to check (can contain array indices).
 * @param {string} dataxpath - The data XPath of the node to check (can contain array indices).
 * @returns {boolean} True if the node is within the subtree, false otherwise.
 */
export function isNodeInSubtree(callerProps, xpath, dataxpath) {
    // Normalize xpath by replacing all array indices with '[0]' for consistent comparison.
    xpath = xpath.replace(/\[\d+\]/g, '[0]');
    if (callerProps.subtree) {
        // If callerProps has an xpath, adjust the current xpath relative to it.
        if (callerProps.xpath) {
            xpath = xpath.substring(xpath.indexOf('.') + 1);
        }
        // Check if the subtree contains the normalized xpath.
        if (!get(callerProps.subtree, xpath + '[0]')) return false;
        else {
            // Find the xpath property within the subtree node.
            let propname = Object.keys(get(callerProps.subtree, xpath + '[0]')).find(key => key.startsWith('xpath_'));
            if (!propname) return false;
            // Construct the full xpath for comparison.
            let propxpath = xpath + '[0].' + propname;
            propxpath = get(callerProps.subtree, propxpath);
            propxpath = propxpath.substring(0, propxpath.lastIndexOf(']') + 1);
            // Compare the extracted xpath with the dataxpath.
            if (propxpath !== dataxpath) return false;
        }
    }
    return true;
}


/**
 * Stores the expansion/collapse state of a tree node.
 * @param {string} xpath - The XPath of the tree node.
 * @param {boolean} state - The expansion state (true for expanded, false for collapsed).
 */
export function setTreeState(xpath, state) {
    treeState[xpath] = state;
}


// New helper function to determine data status
/**
 * Determines the status of data (new, deleted, modified, unchanged) by comparing old and new values.
 * This helper function is used to apply visual cues in the UI based on data changes.
 * @param {*} oldValue - The previous value of the data.
 * @param {*} newValue - The current value of the data.
 * @param {boolean} oldExists - True if `oldValue` exists (is not undefined).
 * @param {boolean} newExists - True if `newValue` exists (is not undefined).
 * @returns {('new'|'deleted'|'modified'|'unchanged')} The status of the data.
 */
function determineDataStatus(oldValue, newValue, oldExists, newExists) {
    if (newExists && !oldExists) {
        return 'new';
    } else if (!newExists && oldExists) {
        return 'deleted';
    } else if (newExists && oldExists) {
        // Special case for objects/arrays that become null (effectively deleted/cleared)
        if (newValue === null && oldValue !== null && (typeof oldValue === 'object' || Array.isArray(oldValue))) {
            return 'deleted'; // Or 'cleared', depending on desired visual distinction
        }
        // If both exist, check for equality to determine if modified or unchanged.
        if (!isEqual(oldValue, newValue)) {
            return 'modified';
        }
    }
    return 'unchanged'; // No changes detected.
}


// Helper function to strip array indices from an XPath
// e.g., "eligible_brokers[0].sec_positions[1].security.sec_id" -> "eligible_brokers.sec_positions.security.sec_id"
/**
 * Strips array indices from an XPath string.
 * For example, "eligible_brokers[0].sec_positions[1].security.sec_id" becomes "eligible_brokers.sec_positions.security.sec_id".
 * This is useful for converting a data-specific XPath to a more generic schema XPath.
 * @param {string} xpath - The XPath string to process.
 * @returns {string} The XPath string with all array indices removed.
 */
function stripIndices(xpath) {
    if (!xpath) return '';
    return xpath.replace(/\[\d+\]/g, '');
}


// Helper function to check if a node is a child of a deleted CONTAINER parent (objects with items)
// Only cascades deletion from container objects, not simple objects
/**
 * Checks if a node is a child of a deleted CONTAINER parent.
 * A "CONTAINER" parent is an object that has a complex structure (multiple properties or nested arrays/objects).
 * This function cascades deletion status from such parents to their children.
 * @param {Object} data - The current data object.
 * @param {string} xpath - The XPath of the node to check.
 * @returns {boolean} True if the node is a child of a deleted container, false otherwise.
 */
function checkIfChildOfDeletedContainer(data, xpath) {
    if (!xpath || !data) return false;

    let currentPath = xpath;

    // Check array parent paths - go up the hierarchy
    while (currentPath.includes('.') || currentPath.includes('[')) {
        // Remove the last segment (either after a dot or bracket)
        let parentPath;

        if (currentPath.includes('.')) {
            const lastDotIndex = currentPath.lastIndexOf('.');
            parentPath = currentPath.substring(0, lastDotIndex);
        } else if (currentPath.includes('[')) {
            const lastBracketStart = currentPath.lastIndexOf('[');
            parentPath = currentPath.substring(0, lastBracketStart);
        } else {
            break;
        }

        if (!parentPath) break;

        // Get the data path for this parent xpath using getDataxpath
        let parentDataPath;
        try {
            parentDataPath = getDataxpath(data, parentPath);
        } catch (e) {
            parentDataPath = parentPath;
        }

        // Check if parent exists and is marked for deletion
        const parentValue = get(data, parentDataPath);
        if (parentValue && typeof parentValue === 'object' && parentValue['data-remove']) {
            // Additional check: only cascade if the parent is a CONTAINER (has complex structure)
            // Containers typically have multiple properties or nested arrays/objects
            const allKeys = Object.keys(parentValue);
            const dataKeys = allKeys.filter(key => !key.startsWith('xpath_') && !key.startsWith('__'));

            // A container typically has multiple data properties or nested structures
            const hasMultipleProperties = dataKeys.length > 2;
            const hasNestedStructures = dataKeys.some(key => {
                const childValue = parentValue[key];
                return childValue && typeof childValue === 'object' &&
                    (Array.isArray(childValue) ||
                        (typeof childValue === 'object' && Object.keys(childValue).length > 1));
            });

            if (hasMultipleProperties || hasNestedStructures) {
                return true; // This is a container being deleted, cascade the deletion
            }
        }

        currentPath = parentPath;
    }

    return false;
}


// Helper function to get the schema definition for a specific path, handling arrays and $refs.
/**
 * Retrieves the schema definition for a specific path within the project schema.
 * This function handles nested objects and arrays, resolving `$ref` references to find the correct schema.
 * @param {Object} projectSchema - The complete project schema definition.
 * @param {string} modelName - The name of the top-level model (e.g., 'basket_order').
 * @param {string} path - The dot-separated path to the desired schema (e.g., 'eligible_brokers.sec_positions.security').
 * @returns {Object|null} The schema definition for the given path, or `null` if not found.
 */
function getSchemaForPath(projectSchema, modelName, path) {
    if (!path || !projectSchema || !modelName) return null;

    const parts = path.split('.');
    let currentSchema = getModelSchema(modelName, projectSchema);

    for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        if (!currentSchema || !currentSchema.properties) return null;

        const propertyName = part.replace(/\[\d+\]$/, ''); // Remove potential trailing index for direct property lookup
        currentSchema = currentSchema.properties[propertyName];

        if (!currentSchema) return null;

        // If it's an array and we're not at the last part, we need to look into its items' schema.
        if (currentSchema.type === DATA_TYPES.ARRAY && currentSchema.items && currentSchema.items.$ref && i < parts.length - 1) {
            const refParts = currentSchema.items.$ref.split('/');
            if (refParts.length < 2) return null;
            const refSchemaName = refParts.length === 2 ? refParts[1] : refParts[2]; // e.g. "Broker" or "SecPosition"
            const mainSchemaContainer = refParts.length === 3 ? refParts[1] : null; // e.g. "definitions"

            if (mainSchemaContainer && projectSchema[mainSchemaContainer] && projectSchema[mainSchemaContainer][refSchemaName]) {
                currentSchema = projectSchema[mainSchemaContainer][refSchemaName];
            } else if (projectSchema[refSchemaName]) {
                currentSchema = projectSchema[refSchemaName];
            } else {
                return null; // Referenced schema not found
            }
        } else if (currentSchema.type === DATA_TYPES.OBJECT && currentSchema.items && currentSchema.items.$ref && i < parts.length - 1) {
            // This handles objects that are defined by a $ref in their 'items' property (uncommon but possible)
            const refParts = currentSchema.items.$ref.split('/');
            if (refParts.length < 2) return null;
            const refSchemaName = refParts.length === 2 ? refParts[1] : refParts[2];
            const mainSchemaContainer = refParts.length === 3 ? refParts[1] : null;

            if (mainSchemaContainer && projectSchema[mainSchemaContainer] && projectSchema[mainSchemaContainer][refSchemaName]) {
                currentSchema = projectSchema[mainSchemaContainer][refSchemaName];
            } else if (projectSchema[refSchemaName]) {
                currentSchema = projectSchema[refSchemaName];
            } else {
                return null;
            }
        }
    }
    return currentSchema;
}


// Helper function to check if a node's value matches any of the comma-separated filter values (partial, case-insensitive).
/**
 * Checks if a node's value matches any of the comma-separated filter values (partial, case-insensitive).
 * @param {*} nodeValue - The value of the node to check.
 * @param {string} filterValuesString - A comma-separated string of filter values.
 * @returns {boolean} True if the node value matches any of the filter values, false otherwise.
 */
function checkMatch(nodeValue, filterValuesString) {
    // If the filter string is empty or invalid, no match can be made.
    if (filterValuesString === null || filterValuesString === undefined || filterValuesString.trim() === '') {
        return false; // An empty filter string means no active filter criteria from this source.
    }
    // If the node has no value, it cannot match.
    if (nodeValue === null || nodeValue === undefined) {
        return false; // Node has no value, cannot match.
    }
    // Split filter values, trim whitespace, convert to lowercase, and remove empty tokens.
    const filterTokens = filterValuesString.split(',').map(fv => fv.trim().toLowerCase()).filter(token => token !== ''); // Ensure tokens are not empty strings
    if (filterTokens.length === 0) {
        return false; // No valid filter tokens after trimming and filtering empty ones.
    }
    // Convert the node value to a string and lowercase for case-insensitive comparison.
    const valueStr = String(nodeValue).toLowerCase();

    // Return true if any non-empty filter token is included in the node's value string.
    return filterTokens.some(token => valueStr.includes(token));
}


// Helper function to check if an array item matches a specific filter
/**
 * Checks if an array item (or any of its nested properties) matches a specific filter.
 * This function recursively searches through the item's properties, including nested objects and arrays,
 * to find a field that matches the filter's `column_name` and `filtered_values`.
 * @param {Object} itemData - The data object representing an item in an array.
 * @param {Object} filter - The filter object, containing `column_name` and `filtered_values`.
 * @param {Object} schema - The complete project schema definition.
 * @param {string} itemSchemaRef - The `$ref` string pointing to the schema definition of the array item.
 * @returns {boolean} True if the item or any of its descendants match the filter, false otherwise.
 */
function checkItemAgainstFilter(itemData, filter, schema, itemSchemaRef) {
    if (!itemData || !filter || !filter.column_name || !filter.filtered_values) {
        return false;
    }

    // Get the schema definition for the array items
    let itemSchema = null;
    if (itemSchemaRef) {
        const refParts = itemSchemaRef.split('/');
        if (refParts.length >= 2) {
            itemSchema = refParts.length === 2 ?
                schema[refParts[1]] :
                schema[refParts[1]][refParts[2]];
        }
    }

    if (!itemSchema || !itemSchema.properties) {
        return false;
    }

    // Recursively search through the item's properties for a matching field
    function searchItemForMatch(currentData, currentSchema, pathPrefix = '') {
        if (!currentSchema || !currentSchema.properties) {
            return false;
        }

        for (const propName in currentSchema.properties) {
            const propSchema = currentSchema.properties[propName];
            const currentPath = pathPrefix ? `${pathPrefix}.${propName}` : propName;
            const propValue = currentData ? currentData[propName] : undefined;

            // Check if this property matches the filter
            if (propSchema.filter_enable && filter.column_name.endsWith(`.${propName}`)) {
                if (checkMatch(propValue, filter.filtered_values)) {
                    return true;
                }
            }

            // Recursively check nested objects
            if (propSchema.type === DATA_TYPES.OBJECT && propSchema.items && propSchema.items.$ref) {
                if (propValue && typeof propValue === 'object') {
                    const nestedRefParts = propSchema.items.$ref.split('/');
                    const nestedSchema = nestedRefParts.length === 2 ?
                        schema[nestedRefParts[1]] :
                        schema[nestedRefParts[1]][nestedRefParts[2]];

                    if (nestedSchema && searchItemForMatch(propValue, nestedSchema, currentPath)) {
                        return true;
                    }
                }
            }
            // Recursively check nested arrays
            else if (propSchema.type === DATA_TYPES.ARRAY && propSchema.items && propSchema.items.$ref) {
                if (Array.isArray(propValue)) {
                    const arrayItemRefParts = propSchema.items.$ref.split('/');
                    const arrayItemSchema = arrayItemRefParts.length === 2 ?
                        schema[arrayItemRefParts[1]] :
                        schema[arrayItemRefParts[1]][arrayItemRefParts[2]];

                    if (arrayItemSchema) {
                        for (const item of propValue) {
                            if (searchItemForMatch(item, arrayItemSchema, currentPath)) {
                                return true; // Found a match in one of the array items
                            }
                        }
                    }
                }
            }
        }

        return false;
    }

    return searchItemForMatch(itemData, itemSchema);
}


// New helper function to check if a node and its descendants match ALL active filters.
/**
 * Checks if a node and its descendants match ALL active filters.
 * This function recursively traverses the node's children to find if any primitive field
 * matches the filter criteria. It applies an AND logic across all active filters.
 * @param {Object} node - The current node (object or array container) to check.
 * @param {Object} projectSchema - The complete project schema definition.
 * @param {string} modelName - The name of the top-level model.
 * @param {Array<Object>} activeFilters - An array of active filter objects.
 * @returns {boolean} True if the node (or its descendants) matches all active filters, false otherwise.
 */
function objectMatchesAllFilters(node, projectSchema, modelName, activeFilters) {
    if (!activeFilters || activeFilters.length === 0) {
        return true; // No active filters means the object "matches".
    }

    for (const filter of activeFilters) {
        let matchFoundForThisFilter = false;

        // Recursively search within the node for a match for the current filter.
        function searchForMatch(currentNode) {
            if (matchFoundForThisFilter) return; // Optimization: stop if we found a match for this filter.

            // Check if the current node is a primitive field that matches the filter.
            if (!(currentNode.isObjectContainer || currentNode.isArrayContainer) && currentNode.xpath && currentNode.value !== undefined) {
                const genericPath = stripIndices(currentNode.xpath);
                const fieldSchema = getSchemaForPath(projectSchema, modelName, genericPath);
                if (fieldSchema && fieldSchema.filter_enable && filter.column_name === genericPath) {
                    if (checkMatch(currentNode.value, filter.filtered_values)) {
                        matchFoundForThisFilter = true;
                        return;
                    }
                }
            }

            // If no match yet, recurse into children.
            if (currentNode.children) {
                for (const child of currentNode.children) {
                    searchForMatch(child);
                    if (matchFoundForThisFilter) return; // Exit early if a child found a match.
                }
            }
        }

        searchForMatch(node);

        // If after searching the entire subtree of the object, no match was found for this filter,
        // then the object does not satisfy the AND condition.
        if (!matchFoundForThisFilter) {
            return false;
        }
    }

    // If we get here, it means the object had at least one matching descendant for EVERY active filter.
    return true;
}


// Recursive function to filter a single node based on the new requirements.
/**
 * Recursively filters a single node and its descendants based on a set of filter criteria.
 * This function determines whether a node should be kept in the tree structure based on direct matches
 * or matches within its children. It handles object containers, array containers, and simple field nodes.
 * @param {Object} node - The current node to filter.
 * @param {Object} projectSchema - The complete project schema definition.
 * @param {string} modelName - The name of the top-level model.
 * @param {Array<Object>} filters - An array of filter objects.
 * @returns {Object|null} The filtered node (potentially with filtered children), or `null` if the node does not match the filters.
 */
function filterNodeRecursive(node, projectSchema, modelName, filters) {
    if (!node) return null;

    // Clone the node to avoid modifying the original tree structure during the filter check iteration.
    const newNode = cloneDeep(node);

    let isDirectFieldMatch = false;
    // Check if the current node is a primitive field that directly matches a filter.
    if (!(node.isObjectContainer || node.isArrayContainer) && node.xpath && node.value !== undefined) {
        const genericPath = stripIndices(node.xpath);
        const fieldSchema = getSchemaForPath(projectSchema, modelName, genericPath);
        if (fieldSchema && fieldSchema.filter_enable) {
            const relevantFilter = filters.find(f => f.column_name === genericPath && f.filtered_values && f.filtered_values.trim() !== '');
            if (relevantFilter && checkMatch(node.value, relevantFilter.filtered_values)) {
                isDirectFieldMatch = true;
            }
        }
    }

    if (node.isObjectContainer) {
        let hasMatchingDescendant = false;
        const processedChildren = [];
        // Recursively filter children.
        for (const child of (node.children || [])) {
            const filteredChild = filterNodeRecursive(child, projectSchema, modelName, filters);
            if (filteredChild) {
                hasMatchingDescendant = true; // Indicates that some descendant (primitive, object, or array item) matched.
                processedChildren.push(filteredChild);
            }
        }

        // An object is kept if one of its direct primitive fields matched OR if it has any kept children (recursively).
        // Check direct primitive children of the *original* node for matches.
        let hasDirectPrimitiveChildMatch = false;
        if (node.children) {
            for (const originalChild of node.children) {
                if (!(originalChild.isObjectContainer || originalChild.isArrayContainer) && originalChild.xpath && originalChild.value !== undefined) {
                    const genericChildPath = stripIndices(originalChild.xpath);
                    const childSchema = getSchemaForPath(projectSchema, modelName, genericChildPath);
                    if (childSchema && childSchema.filter_enable) {
                        const relevantChildFilter = filters.find(f => f.column_name === genericChildPath && f.filtered_values && f.filtered_values.trim() !== '');
                        if (relevantChildFilter && checkMatch(originalChild.value, relevantChildFilter.filtered_values)) {
                            hasDirectPrimitiveChildMatch = true;
                            break;
                        }
                    }
                }
            }
        }

        if (hasDirectPrimitiveChildMatch || hasMatchingDescendant) {
            // If the object itself is kept, reconstruct its children:
            const finalChildren = [];
            (node.children || []).forEach(originalChild => {
                if (!(originalChild.isObjectContainer || originalChild.isArrayContainer)) {
                    finalChildren.push(cloneDeep(originalChild)); // Keep all original primitive fields
                } else { // originalChild is a container (object or array)
                    const correspondingFilteredChild = processedChildren.find(pc => pc.id === originalChild.id);

                    if (correspondingFilteredChild) {
                        // This child container (or its descendants) matched some filter(s).
                        finalChildren.push(correspondingFilteredChild);
                    } else {
                        // This child container (originalChild) and its descendants did NOT match ANY active filters.
                        // If the parent object (node) was kept due to a direct primitive match OR a descendant match,
                        // then we should include this originalChild container as it was (unfiltered by this pass).
                        if (hasDirectPrimitiveChildMatch || hasMatchingDescendant) {
                            finalChildren.push(cloneDeep(originalChild));
                        }
                    }
                }
            });
            newNode.children = finalChildren;
            return newNode;
        }
        return null; // Object not kept

    } else if (node.isArrayContainer) {
        const activeFilters = filters.filter(f => f.filtered_values && f.filtered_values.trim() !== '');
        if (activeFilters.length === 0) {
            return newNode; // No filters, so don't filter this array at all.
        }

        const itemMatches = [];
        if (node.children) {
            for (const item of node.children) {
                // For array items, we apply AND logic. An item is kept only if it matches ALL active filters.
                if (objectMatchesAllFilters(item, projectSchema, modelName, activeFilters)) {
                    // If it matches, we keep the entire item, un-pruned.
                    itemMatches.push(cloneDeep(item));
                }
            }
        }
        if (itemMatches.length > 0) {
            newNode.children = itemMatches;
            return newNode; // Array kept with only matching items
        }
        return null; // Array not kept (no items matched)

    } else { // Simple Field Node
        if (isDirectFieldMatch) {
            return newNode; // Keep the matching field
        }
        return null; // Field not kept
    }
}


/**
 * Generates a tree structure from a given schema and data, suitable for UI rendering.
 * This function recursively traverses the schema, creating nodes for properties, objects, and arrays.
 * It applies filtering, pagination, and highlights data changes (add, remove, modify).
 * @param {Object} schema - The complete project schema definition.
 * @param {string} currentSchemaName - The name of the top-level schema to generate the tree for.
 * @param {Object} callerProps - Properties from the calling component, including `data`, `originalData`, `mode`, `filters`, `paginatedNodes`, and `isOpen`.
 * @returns {Array<Object>} An array of tree nodes, representing the structured data.
 */
export function generateTreeStructure(schema, currentSchemaName, callerProps) {
    if (!schema || Object.keys(schema).length === 0) return [];

    const currentSchema = getModelSchema(currentSchemaName, schema);
    let tree = [];

    // Add the root header node for the current schema.
    const childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DATA_TYPES.OBJECT, callerProps, currentSchemaName, currentSchemaName);

    // Iterate over properties of the current schema to add them as child nodes.
    Object.keys(currentSchema.properties).forEach(propname => {
        // If a specific xpath is provided in callerProps, only process that property.
        if (callerProps.xpath && callerProps.xpath !== propname) return;

        const metadataProp = currentSchema.properties[propname];
        // Ensure required property is an array for consistency.
        metadataProp.required = currentSchema.required.includes(propname) ? metadataProp.required : [];

        // Differentiate between object/array containers and simple primitive fields.
        if (metadataProp.type === DATA_TYPES.OBJECT && metadataProp.items) {
            addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
        } else if (metadataProp.type && primitiveDataTypes.includes(metadataProp.type)) {
            addSimpleNode(childNode, schema, currentSchema, propname, callerProps);
        } else {
            addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
        }
    });

    // OPTIMIZATION: Skip final filtering since early filtering is more efficient and accurate
    // The early filtering (in processArrayItems/processArrayItemsSimple) already handles
    // the filtering correctly with container-aware logic. Final filtering is redundant
    // and can cause issues with deeply nested structures.

    return tree;
}


/**
 * Adds a node to the tree structure, handling different data types (object with items, array with items, simple array).
 * This function acts as a dispatcher, calling specific handlers based on the schema type.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} currentSchema - The schema definition for the current node.
 * @param {string} propname - The property name of the current node.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the current node.
 * @param {string} type - The data type of the current node (e.g., DATA_TYPES.OBJECT, DATA_TYPES.ARRAY).
 * @param {string} xpath - The schema XPath of the current node.
 */
function addNode(tree, schema, currentSchema, propname, callerProps, dataxpath, type, xpath) {
    const { data, originalData, mode } = callerProps;
    const currentSchemaType = type || currentSchema.type;

    // Handle object type with items (complex objects defined by a $ref).
    if (currentSchema.items && currentSchemaType === DATA_TYPES.OBJECT) {
        handleObjectWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    }
    // Handle array type with items (complex arrays defined by a $ref).
    else if (currentSchema.items && currentSchema.type === DATA_TYPES.ARRAY) {
        handleArrayWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    }
    // Handle simple array type (arrays of primitive types).
    else if (currentSchema.type === DATA_TYPES.ARRAY) {
        handleSimpleArray(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    }
}


/**
 * Handles the creation and processing of object nodes that have `items` (i.e., complex objects defined by a $ref).
 * This function creates a header node for the object and then recursively processes its properties.
 * It also handles cases where the object is new, deleted, or modified.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} currentSchema - The schema definition for the current object node.
 * @param {string} propname - The property name of the current object node.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the current object node.
 * @param {string} xpath - The schema XPath of the current object node.
 */
function handleObjectWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    // Always create the container node
    let schemaForHeaderNode = currentSchema;
    let itemRefForHeaderNode = currentSchema.items?.$ref;
    let effectivePropName = propname;
    const headerState = determineHeaderState(callerProps.data, callerProps.originalData, xpath, currentSchema); // We'll use dataStatus instead

    if (currentSchema.type === DATA_TYPES.ARRAY && currentSchema.items && currentSchema.items.$ref) {
        const ref = currentSchema.items.$ref.split('/');
        schemaForHeaderNode = ref.length === 2 ? cloneDeep(schema[ref[1]]) : cloneDeep(schema[ref[1]][ref[2]]);
        const propertiesToInherit = ['orm_no_update', 'server_populate', 'ui_update_only', 'help'];
        propertiesToInherit.forEach(p => {
            if (currentSchema.hasOwnProperty(p) && !schemaForHeaderNode.hasOwnProperty(p)) {
                schemaForHeaderNode[p] = currentSchema[p];
            }
        });
        if (currentSchema.required) {
            schemaForHeaderNode.required = schemaForHeaderNode.required || [];
        }
    } else if (currentSchema.items && currentSchema.type === DATA_TYPES.OBJECT && currentSchema.items.$ref) {
        itemRefForHeaderNode = currentSchema.items.$ref;
    }

    if (get(callerProps.data, dataxpath) === undefined && get(callerProps.originalData, xpath) === undefined) return;

    // Create the header node and add it to the tree. addHeaderNode pushes the node into 'tree'.
    addHeaderNode(
        tree,
        schemaForHeaderNode,
        effectivePropName,
        DATA_TYPES.OBJECT,
        callerProps,
        dataxpath,
        xpath,
        itemRefForHeaderNode,
        headerState // Removed: will be handled by dataStatus logic within addHeaderNode
    );

    // Get the actual header node that was just added (it's the last one in the 'tree' array)
    const actualHeaderNode = tree[tree.length - 1];

    const currentValue = get(callerProps.data, dataxpath);
    const originalValue = get(callerProps.originalData, xpath);
    const neverExisted = (currentValue === null && originalValue === null);
    const isDeleted = (currentValue === null && originalValue !== null);

    if (neverExisted || isDeleted) {
        // Set canInitialize for both cases: an object that never existed or one that was just deleted.
        actualHeaderNode.canInitialize = true;
        actualHeaderNode.schemaRef = itemRefForHeaderNode;

        if (neverExisted) {
            // If it never existed, there are no children to process, so we can exit early.
            return;
        }
        // If it was just deleted, we continue on. This allows the logic to process its
        // children from the originalValue, showing them with a strike-through style.
    }

    // If not null, then process its properties and add them to actualHeaderNode.children
    let metadata;
    if (schemaForHeaderNode.properties) {
        metadata = processMetadata(cloneDeep(schemaForHeaderNode), currentSchema);
    } else if (currentSchema.items && currentSchema.items.$ref) { // Fallback for direct $ref items like object with items pointing to a definition
        const ref = currentSchema.items.$ref.split('/');
        metadata = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
        metadata = processMetadata(cloneDeep(metadata), currentSchema);
    }

    if (metadata && metadata.properties) {
        // Pass actualHeaderNode.children to processMetadataProperties, as it expects an array to push child nodes into
        processMetadataProperties(metadata, actualHeaderNode.children, schema, callerProps, dataxpath, xpath);
    }
}


/**
 * Handles the creation and processing of array nodes that have `items` (i.e., complex arrays defined by a $ref).
 * This function creates a header node for the array and then processes its items, handling pagination and filtering.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} currentSchema - The schema definition for the current array node.
 * @param {string} propname - The property name of the current array node.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the current array node.
 * @param {string} xpath - The schema XPath of the current array node.
 */
function handleArrayWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {

    if (callerProps.mode === MODES.EDIT && currentSchema.server_populate) {
        console.log(`Skipping ${xpath} due to server_populate in EDIT mode`);
        return;
    }

    const { data, originalData } = callerProps;
    const hasEmptyData = isEmptyArrayData(data, originalData, dataxpath, xpath);

    if (get(callerProps.data, dataxpath) === undefined && get(callerProps.originalData, xpath) === undefined) {
        console.log(`Both data and original data undefined for ${xpath}, returning`);
        return;
    }

    // Create a container node for the array (e.g., "eligible brokers")
    // addHeaderNode pushes the main array container node into the 'tree' array.
    addHeaderNode(
        tree,
        currentSchema,
        propname,
        DATA_TYPES.ARRAY,
        callerProps,
        dataxpath,
        xpath,
        currentSchema.items?.$ref
    );

    // If the array is empty, we've added its container.
    // The container itself (via HeaderField UI) will show the "+" to add items.
    if (hasEmptyData) {
        return;
    }

    // If data is not empty, process the actual items.
    // Get the children array of the main array container node that was just added.
    const mainArrayContainerNode = tree[tree.length - 1];
    const mainArrayContainerNode_Children = mainArrayContainerNode.children;
    processArrayItems(mainArrayContainerNode_Children, schema, currentSchema, propname, callerProps, dataxpath, xpath, mainArrayContainerNode);
}

/**
 * Handles the creation and processing of simple array nodes (arrays of primitive types).
 * This function creates a header node for the array and then processes its items, handling pagination if necessary.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} currentSchema - The schema definition for the current array node.
 * @param {string} propname - The property name of the current array node.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the current array node.
 * @param {string} xpath - The schema XPath of the current array node.
 */
function handleSimpleArray(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    if ((get(callerProps.originalData, xpath) === undefined) && get(callerProps.data, dataxpath) === undefined) return;

    const arrayDataType = getArrayDataType(currentSchema);
    const additionalProps = buildArrayAdditionalProps(schema, currentSchema);

    // Create container node first
    const containerNode = addHeaderNode(
        tree,
        currentSchema,
        propname,
        DATA_TYPES.ARRAY, // Type as object for the container
        callerProps,
        dataxpath,
        xpath,
        currentSchema.items?.$ref,
    );

    const childxpath = `${dataxpath}[-1]`;
    const updatedxpath = `${xpath}[-1]`;
    const objectState = { add: true, remove: false }; // Replaced by dataStatus logic

    const childNode = addHeaderNode(
        containerNode, // Add to container node instead of tree
        currentSchema,
        propname,
        currentSchema.type,
        callerProps,
        childxpath,
        updatedxpath,
        arrayDataType,
        objectState // Replaced by dataStatus logic
    );

    if (get(callerProps.data, dataxpath)) {
        const items = get(callerProps.data, dataxpath);
        const totalItems = items.length;
        const needsPagination = totalItems > ITEMS_PER_PAGE;

        if (needsPagination) {
            // Add pagination info to the parent node
            containerNode[containerNode.length - 1].pagination = {
                totalItems,
                totalPages: Math.ceil(totalItems / ITEMS_PER_PAGE),
                currentPage: 0,
                paginationId: `pagination_${xpath}`
            };

            // Create pagination controls
            const paginationNode = {
                id: containerNode[containerNode.length - 1].pagination.paginationId,
                key: 'pagination',
                name: `Page 1 of ${containerNode[containerNode.length - 1].pagination.totalPages}`,
                isPagination: true,
                xpath: `${xpath}_pagination`,
                prevPage: 0, // Initially disabled
                nextPage: 1,
                onPageChange: true // Flag to handle pagination in the component
            };

            // Add the pagination node
            containerNode.push(paginationNode);

            // Only process items for the first page
            const startIndex = 0;
            const endIndex = Math.min(ITEMS_PER_PAGE, totalItems);

            for (let i = startIndex; i < endIndex; i++) {
                const itemXpath = `${dataxpath}[${i}]`;
                const updatedItemXpath = `${xpath}[${i}]`;
                addSimpleNode(childNode, schema, arrayDataType, null, callerProps, itemXpath, updatedItemXpath, additionalProps);
            }
        } else {
            // If pagination not needed, process all items
            items.forEach((value, i) => {
                const itemXpath = `${dataxpath}[${i}]`;
                const updatedItemXpath = `${xpath}[${i}]`;
                addSimpleNode(childNode, schema, arrayDataType, null, callerProps, itemXpath, updatedItemXpath, additionalProps);
            });
        }
    }
}

/**
 * Adds a header node to the tree structure. This node typically represents an object or an array container.
 * It sets various properties on the header node, including ID, key, title, type, and data status flags (add, remove, modified).
 * It also handles UI-related properties like `canInitialize`, `schemaRef`, and `isOpen` (for expand/collapse).
 * @param {Array<Object>} node - The array representing the tree structure to which the header node will be added.
 * @param {Object} currentSchema - The schema definition for the current node.
 * @param {string} propname - The property name of the current node.
 * @param {string} type - The data type of the current node (e.g., DATA_TYPES.OBJECT, DATA_TYPES.ARRAY).
 * @param {Object} callerProps - Properties from the calling component, including `data`, `originalData`, `mode`, `isOpen`, and `forceDataRemove`.
 * @param {string} dataxpath - The data XPath of the current node.
 * @param {string} xpath - The schema XPath of the current node.
 * @param {string} [ref] - Optional. The `$ref` to the schema definition of the items within this node (if it's a container).
 * @param {Object} [objectState] - Optional. An object containing `add` and `remove` flags for object state (used for array item templates).
 * @returns {Array<Object>} The `children` array of the newly added header node, allowing for chaining.
 */
function addHeaderNode(node, currentSchema, propname, type, callerProps, dataxpath, xpath, ref, objectState) {
    if (currentSchema.server_populate && callerProps.mode === MODES.EDIT) {
        return; // Don't render server-populated containers in edit mode
    }

    const headerNode = {
        id: xpath,
        key: propname,
        title: currentSchema.title,
        name: propname,
        type,
        ref,
        help: currentSchema.help,
        mode: callerProps.mode,
        xpath,
        dataxpath,
        children: []
    };

    // Determine dataStatus for the header node itself - REPLACED by data-add/remove/modified flags
    const oldValue = get(callerProps.originalData, xpath);
    const newValue = get(callerProps.data, dataxpath);
    const oldExists = oldValue !== undefined;
    const newExists = newValue !== undefined;

    // Check if this item is marked for deletion (for array items)
    const isMarkedForDeletion = newValue && typeof newValue === 'object' && newValue['data-remove'];

    // Check if this item is being forced to show as deleted (from ID-based deletion detection)
    const isForcedDeleted = callerProps.forceDataRemove && callerProps.forceDataRemove === xpath;

    // Check if any CONTAINER parent in the path is marked for deletion (cascading deletion)
    // Only use flag-based detection for now to avoid over-cascading
    const isChildOfDeletedContainer = checkIfChildOfDeletedContainer(callerProps.data, xpath);

    if (isMarkedForDeletion || isChildOfDeletedContainer || isForcedDeleted) {
        headerNode['data-remove'] = true;
    }
    else if (newExists && !oldExists) {
        headerNode['data-add'] = true;
    }
    else if ((!newExists || newValue === null) && oldExists && oldValue !== null) {
        headerNode['data-remove'] = true;
        // For deleted array items, we might not have newValue, so we can use oldValue for display
        // headerNode.value = oldValue; // Storing oldValue on headerNode might not be standard, usually for fields
    } else if (newExists && oldExists && !isEqual(oldValue, newValue)) {
        headerNode['data-modified'] = true;
    }

    // Add field properties
    fieldProps.forEach(({ propertyName, usageName }) => {
        if (currentSchema[propertyName]) {
            headerNode[usageName] = currentSchema[propertyName];
        }
    });

    // Add complex field properties
    complexFieldProps.forEach(({ propertyName, usageName }) => {
        if (currentSchema[propertyName]) {
            headerNode[usageName] = currentSchema[propertyName];
        }
    });

    // Set specific container flags
    if (type === DATA_TYPES.ARRAY) {
        headerNode.isArrayContainer = true;
    } else if (type === DATA_TYPES.OBJECT) {

        headerNode.isObjectContainer = true;
    }

    headerNode.required = !ref ? true : currentSchema.required ? currentSchema.required.includes(propname) : true;
    headerNode.uiUpdateOnly = currentSchema.ui_update_only;

    if (objectState) { // This was passed for array item template node, maybe not for general headers.
        const { add, remove } = objectState;
        if (add) headerNode['object-add'] = true;
        if (remove) headerNode['object-remove'] = true;
    } else {
        // Simplified logic for add/remove capabilities on containers based on type
        // This is for UI action buttons, not the dataStatus color.
        if (type === DATA_TYPES.ARRAY) {
            headerNode['object-add'] = true; // Can add items to array
        } else if (type === DATA_TYPES.OBJECT) {
            // Check if object editing is disabled by orm_no_update
            const hasOrmNoUpdate = currentSchema.orm_no_update;

            if (!hasOrmNoUpdate && callerProps.mode === MODES.EDIT) {
                const currentValue = get(callerProps.data, dataxpath);
                const isCurrentlyNull = (currentValue === null || currentValue === undefined);

                // Can initialize if null/undefined and has a schema reference
                if (isCurrentlyNull && ref) {
                    headerNode['object-add'] = true;
                    headerNode.canInitialize = true;
                    headerNode.schemaRef = ref;
                }

                // Can remove (set to null) if it has a value and is not required
                if (!isCurrentlyNull && !currentSchema.required) {
                    headerNode['object-remove'] = true;
                }

                // Special handling for array items - they can always be duplicated/removed
                if (xpath && xpath.endsWith(']')) {
                    headerNode['object-add'] = true; // For duplication
                    headerNode['object-remove'] = true; // For removal
                }
            }
        }
    }

    // Handle tree state
    if (treeState.hasOwnProperty(xpath)) {
        treeState[xpath] = callerProps.isOpen ? true : callerProps.isOpen === false ? false : treeState[xpath];
    } else {
        treeState[xpath] = true;
    }
    headerNode.isOpen = treeState[xpath];

    node.push(headerNode);
    return headerNode.children;
}

/**
 * Adds a simple node (primitive field or primitive array item) to the tree structure.
 * This function handles the creation of nodes for primitive data types, including their values,
 * and applies data status flags (new, deleted, modified) based on comparison with original data.
 * It also handles visibility based on `visible_if` attributes.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} currentSchema - The schema definition for the current node's parent or the node itself if it's a primitive array.
 * @param {string} propname - The property name of the current node.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the current node.
 * @param {string} xpath - The schema XPath of the current node.
 * @param {Object} [additionalProps={}] - Additional properties for the node, especially for primitive array items.
 */
function addSimpleNode(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath, additionalProps = {}) {
    // If this is an object with items, always treat as container
    if (currentSchema.properties && currentSchema.properties[propname]) {
        const attributes = currentSchema.properties[propname];
        if (attributes.type === DATA_TYPES.OBJECT && attributes.items) {
            addNode(tree, schema, attributes, propname, callerProps, dataxpath, attributes.type, xpath);
            return;
        }
    }

    const { data, originalData /*, mode*/ } = callerProps; // mode is unused, callerProps.mode is used

    // Skip if data not present in both modified and original data
    if ((Object.keys(data).length === 0 && Object.keys(originalData).length === 0)) { // General check
        return;
    }
    // More specific check for the current property path:
    const nodeSchemaPath = xpath ? `${xpath}.${propname}` : propname;
    const nodeDataPath = dataxpath ? `${dataxpath}.${propname}` : propname;

    if (propname !== null && // For array items where propname might be null
        get(data, nodeDataPath) === undefined &&
        get(originalData, nodeSchemaPath) === undefined) {
        return;
    }


    if (primitiveDataTypes.includes(currentSchema)) {
        // For primitive arrays, currentSchema is the type string (e.g., "string")
        // propname is null. xpath is like "path.to.array[i]", dataxpath is also "path.to.array[i]"
        const val = dataxpath ? get(callerProps.data, dataxpath) : undefined;
        const oldVal = xpath ? get(callerProps.originalData, xpath) : undefined;
        const valExists = val !== undefined;
        const oldValExists = oldVal !== undefined;
        const status = determineDataStatus(oldVal, val, valExists, oldValExists);
        addPrimitiveNode(tree, currentSchema, dataxpath, xpath, callerProps, additionalProps, status, oldVal);
        return;
    }

    const attributes = currentSchema.properties[propname];
    if (!attributes?.type || !primitiveDataTypes.includes(attributes.type)) return;

    const node = createSimpleNode(attributes, propname, dataxpath, xpath, data, currentSchema, callerProps);

    // Add field properties
    addNodeProperties(node, attributes, currentSchema, schema, data, callerProps);

    if (attributes.visible_if) {
        let invisible = true;
        const [fieldNamePath, fieldValuesStr] = attributes.visible_if.split('=');
        let fieldName;
        let dataSource;
        if (fieldNamePath.includes('.')) {
            dataSource = data;
            fieldName = fieldNamePath.substring(fieldNamePath.indexOf('.') + 1);
        } else {
            dataSource = get(data, dataxpath);
            fieldName = fieldNamePath;
        }
        const fieldValues = fieldValuesStr
            .split(',')
            .map((val) => {
                if (val === 'true') return true;
                if (val === 'false') return false;
                // todo: add support for numerical values
                return val;
            });

        if (dataSource && fieldValues.includes(get(dataSource, fieldName))) {
            invisible = false;
        }
        node.data_invisible = invisible;
    }

    // Compare with original data - replaced by dataStatus
    const comparedProps = compareNodes(originalData, data, dataxpath, propname, xpath);
    Object.assign(node, comparedProps);

    // Check if node should be added
    if (!shouldAddNode(node, callerProps)) return;

    tree.push(node);
}

/**
 * Adds a primitive node (a simple field within an object or an item in a primitive array) to the tree structure.
 * This function creates a node with its value, type, and data status flags (new, deleted, modified).
 * It also handles dropdown options for ENUM types.
 * @param {Array<Object>} tree - The array representing the tree structure to which the node will be added.
 * @param {string} type - The data type of the primitive node (e.g., DATA_TYPES.STRING, DATA_TYPES.NUMBER, DATA_TYPES.ENUM).
 * @param {string} dataxpath - The data XPath of the current node.
 * @param {string} xpath - The schema XPath of the current node.
 * @param {Object} callerProps - Properties from the calling component, including `data`, `originalData`, `mode`, `showDataType`, `onTextChange`, `onFormUpdate`, `onSelectItemChange`.
 * @param {Object} additionalProps - Additional properties for the node, such as `underlyingtype` and `options` for ENUMs.
 * @param {('new'|'deleted'|'modified'|'unchanged')} dataStatus - The data status of the node.
 * @param {*} originalValueForDeleted - The original value of the node if it has been deleted.
 */
function addPrimitiveNode(tree, type, dataxpath, xpath, callerProps, additionalProps, dataStatus, originalValueForDeleted) {
    const node = {
        id: dataxpath, // For primitive array items, dataxpath is the direct path like "array[0]"
        required: true, // Primitive items in an array are part of the array structure
        xpath, // Schema path
        dataxpath, // Data path
        onTextChange: callerProps.onTextChange,
        onFormUpdate: callerProps.onFormUpdate,
        mode: callerProps.mode,
        showDataType: callerProps.showDataType,
        type,
        underlyingtype: additionalProps.underlyingtype,
        value: dataxpath ? get(callerProps.data, dataxpath) : undefined,
    };

    // Check if this node is being forced to show as deleted (from ID-based deletion detection)
    const isForcedDeleted = callerProps.forceDataRemove && callerProps.forceDataRemove === xpath;

    if (dataStatus === 'new') {
        node['data-add'] = true;
    } else if (dataStatus === 'deleted' || isForcedDeleted) {
        node['data-remove'] = true;
        node.value = originalValueForDeleted; // Set original value if deleted
    } else if (dataStatus === 'modified') {
        node['data-modified'] = true;
    }


    if (type === DATA_TYPES.ENUM) {
        node.dropdowndataset = additionalProps.options;
        node.onSelectItemChange = callerProps.onSelectItemChange;
    }

    tree.push(node);
}

/**
 * Creates a simple node object for a primitive field.
 * This function constructs a node with properties like ID, key, required status, XPath, and event handlers.
 * It also checks for deletion flags inherited from parent containers or forced deletion.
 * @param {Object} attributes - The attributes of the field from the schema.
 * @param {string} propname - The property name of the field.
 * @param {string} dataxpath - The data XPath of the field.
 * @param {string} xpath - The schema XPath of the field.
 * @param {Object} data - The current data object.
 * @param {Object} currentSchema - The schema of the current object (parent of this field).
 * @param {Object} callerProps - Properties from the calling component.
 * @returns {Object} The created simple node object.
 */
function createSimpleNode(attributes, propname, dataxpath, xpath, data, currentSchema, callerProps) {
    const nodeXpath = xpath ? `${xpath}.${propname}` : propname;
    const nodeDataXpath = dataxpath ? `${dataxpath}.${propname}` : propname;

    const node = {
        id: nodeXpath,
        key: propname,
        required: currentSchema.required.includes(propname),
        xpath: nodeXpath,
        dataxpath: nodeDataXpath,
        parentcollection: currentSchema.title,
        onTextChange: callerProps.onTextChange,
        onFormUpdate: callerProps.onFormUpdate,
        mode: callerProps.mode,
        showDataType: callerProps.showDataType,
        index: callerProps.index,
        forceUpdate: callerProps.forceUpdate,
        value: dataxpath ?
            (hasxpath(data, dataxpath) ? get(data, dataxpath)[propname] : undefined) :
            data[propname]
    };

    // Check if this node is a child of a deleted CONTAINER parent (not simple objects)
    const isChildOfDeletedContainer = checkIfChildOfDeletedContainer(callerProps.data, nodeXpath);

    // Check if this node is being forced to show as deleted (from ID-based deletion detection)
    const isForcedDeleted = callerProps.forceDataRemove && callerProps.forceDataRemove === nodeXpath;

    if (isChildOfDeletedContainer || isForcedDeleted) {
        node['data-remove'] = true;
    }

    return node;
}

/**
 * Determines whether a node should be added to the tree based on various conditions.
 * Conditions include `serverPopulate`, `hide`, `uiUpdateOnly`, and `mode`.
 * @param {Object} node - The node object to check.
 * @param {Object} callerProps - Properties from the calling component, including `mode` and `hide`.
 * @returns {boolean} True if the node should be added, false otherwise.
 */
function shouldAddNode(node, callerProps) {
    // Do not add if server-populated in edit mode, or hidden, or UI-update-only and value is undefined.
    if ((node.serverPopulate && callerProps.mode === MODES.EDIT) ||
        (node.hide && callerProps.hide) ||
        (node.uiUpdateOnly && node.value === undefined)) {
        return false;
    }

    // Special handling for boolean buttons in edit mode.
    if (node.type === DATA_TYPES.BOOLEAN && node.button && callerProps.mode === MODES.EDIT) {
        return false;
    }

    return true;
}

/**
 * Adds properties to a node based on its attributes and schema definitions.
 * This function applies regular field properties, complex field properties (like autocomplete and mapping),
 * and type-specific handlers (e.g., for boolean, enum, and date-time fields).
 * @param {Object} node - The node object to which properties will be added.
 * @param {Object} attributes - The attributes of the field from the schema.
 * @param {Object} currentSchema - The schema of the current object (parent of this field).
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} data - The current data object.
 * @param {Object} callerProps - Properties from the calling component.
 */
function addNodeProperties(node, attributes, currentSchema, schema, data, callerProps) {
    // Add regular field properties
    fieldProps.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {
            node[usageName] = attributes[propertyName];
        }
    });

    node.quickFilter = callerProps.quickFilter;

    // Add complex field properties
    complexFieldProps.forEach(({ propertyName, usageName }) => {
        if (currentSchema.hasOwnProperty(propertyName) || attributes.hasOwnProperty(propertyName)) {
            const propertyValue = attributes[propertyName] || currentSchema[propertyName];

            if (propertyName === 'auto_complete') {
                const autocompleteDict = getAutocompleteDict(propertyValue);
                setAutocompleteValue(schema, node, autocompleteDict, node.key, usageName);

                if (node.options) {
                    if (node.hasOwnProperty('dynamic_autocomplete')) {
                        const dynamicValuePath = node.autocomplete.substring(node.autocomplete.indexOf('.') + 1);
                        const dynamicValue = get(data, dynamicValuePath);
                        if (dynamicValue && schema.autocomplete.hasOwnProperty(dynamicValue)) {
                            node.options = schema.autocomplete[schema.autocomplete[dynamicValue]];
                            if (!node.options.includes(node.value) && callerProps.mode === MODES.EDIT && !node.ormNoUpdate && !node.serverPopulate) {
                                node.value = null;
                            }
                        }
                    }
                    node.customComponentType = 'autocomplete';
                    node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
                }
            } else if (propertyName === 'mapping_underlying_meta_field') {
                const dict = getMetaFieldDict(propertyValue);
                for (const field in dict) {
                    if (node.xpath.endsWith(field)) {
                        node[usageName] = dict[field];
                    }
                }
            } else if (propertyName === 'mapping_src') {
                const dict = getMappingSrcDict(propertyValue);
                for (const field in dict) {
                    if (node.xpath.endsWith(field)) {
                        node[usageName] = dict[field];
                    }
                }
            } else {
                node[usageName] = propertyValue;
            }
        }
    });

    // Add type-specific handlers
    if (attributes.type === DATA_TYPES.BOOLEAN) {
        node.onCheckboxChange = callerProps.onCheckboxChange;
    }

    if (attributes.type === DATA_TYPES.ENUM) {
        node.onSelectItemChange = callerProps.onSelectItemChange;
        // Set dropdown options for enum fields
        if (attributes.enum) {
            node.dropdowndataset = attributes.enum;
        } else if (attributes.$ref) {
            const ref = attributes.$ref.split('/');
            node.dropdowndataset = getEnumValues(schema, ref, DATA_TYPES.ENUM);
        } else if (attributes.items && attributes.items.$ref) {
            // Handle enum references inside items
            const ref = attributes.items.$ref.split('/');
            node.dropdowndataset = getEnumValues(schema, ref, DATA_TYPES.ENUM);
        }
    }

    if (attributes.type === DATA_TYPES.DATE_TIME) {
        node.onDateTimeChange = callerProps.onDateTimeChange;
    }
}

/**
 * Determines the state of a header node (add, remove, or no change) based on comparison between current and original data.
 * This function is used to set flags on header nodes for UI representation of data changes.
 * @param {Object} data - The current data object.
 * @param {Object} originalData - The original data object.
 * @param {string} xpath - The XPath of the node being evaluated.
 * @param {Object} currentSchema - The schema definition for the current node.
 * @returns {Object} An object containing `add` and `remove` boolean flags.
 */
function determineHeaderState(data, originalData, xpath, currentSchema) {
    let headerState = {};
    if (get(originalData, xpath) === undefined) {
        if (get(data, xpath) === null) { // Check data path for current value
            headerState.add = true;
            headerState.remove = false;
        } else if (get(data, xpath) !== undefined) { // Only allow remove if it exists in current data
            headerState.add = false;
            headerState.remove = true;
        } else { // Doesn't exist in original or current (potentially)
            headerState.add = true; // Default to add if it's an optional field not yet present
            headerState.remove = false;
        }
    } else if (currentSchema.hasOwnProperty('orm_no_update')) {
        if (get(originalData, xpath) !== undefined) {
            headerState.add = false;
            headerState.remove = false;
        }
    } else if (!currentSchema.hasOwnProperty('orm_no_update')) {
        if (get(data, xpath) === null) {
            headerState.add = true;
            headerState.remove = false;
        } else if (get(data, xpath) !== undefined) {
            headerState.add = false;
            headerState.remove = true;
        } else { // Existed in original, but not in current (and not null) -> implies removed by parent action
            headerState.add = false; // Cannot add back directly if structure removed
            headerState.remove = false; // Cannot remove if not there
        }
    }
    // Ensure required fields that are null (but shouldn't be if not optional) don't show 'add'
    if (currentSchema.required && currentSchema.required.includes(xpath.split('.').pop()) && get(data, xpath) === null) {
        // This logic might be too simplistic for complex paths
    }
    return headerState;
}

/**
 * Processes metadata by copying specific properties from `currentSchema` to `metadata` if they are not already present in `metadata`.
 * This ensures that certain inherited properties (like `orm_no_update`, `server_populate`, `ui_update_only`, and `auto_complete`)
 * are correctly propagated to the metadata object.
 * @param {Object} metadata - The metadata object to be updated.
 * @param {Object} currentSchema - The current schema from which properties might be inherited.
 * @returns {Object} The updated metadata object.
 */
function processMetadata(metadata, currentSchema) {
    const propertiesToCopy = ['orm_no_update', 'server_populate', 'ui_update_only', 'auto_complete'];

    propertiesToCopy.forEach(prop => {
        // If the property exists in currentSchema and is not already defined in metadata, copy it.
        if (currentSchema.hasOwnProperty(prop) || metadata.hasOwnProperty(prop)) {
            metadata[prop] = metadata[prop] || currentSchema[prop];
        }
    });

    return metadata;
}

/**
 * Processes metadata properties, inheriting properties from parent metadata and recursively adding child nodes.
 * This function iterates through the properties of the provided `metadata` and creates corresponding tree nodes.
 * It also handles inheritance of properties like `ui_update_only`, `server_populate`, `orm_no_update`, and `auto_complete`.
 * @param {Object} metadata - The metadata object containing properties to process.
 * @param {Array<Object>} childNodes - The array to which the created child nodes will be added.
 * @param {Object} schema - The complete project schema definition.
 * @param {Object} callerProps - Properties from the calling component.
 * @param {string} dataxpath - The data XPath of the parent node.
 * @param {string} xpath - The schema XPath of the parent node.
 */
function processMetadataProperties(metadata, childNodes, schema, callerProps, dataxpath, xpath) {
    Object.keys(metadata.properties).forEach((prop) => {
        let metadataProp = metadata.properties[prop];
        if (!metadata.required.includes(prop)) {
            metadataProp.required = [];
        }

        const propertiesToInherit = ['ui_update_only', 'server_populate', 'orm_no_update', 'auto_complete'];
        propertiesToInherit.forEach(property => {
            if (metadata.hasOwnProperty(property)) {
                metadataProp[property] = metadataProp[property] ?? metadata[property];
            }
        });

        const childxpath = dataxpath ? `${dataxpath}.${prop}` : prop;
        const updatedxpath = `${xpath}.${prop}`;

        // Inherit deletion state for child nodes - if parent is marked for deletion, children should be too
        let modifiedCallerProps = callerProps;
        if (callerProps.forceDataRemove) {
            // If parent was deleted, children should also be marked as deleted
            modifiedCallerProps = {
                ...callerProps,
                forceDataRemove: updatedxpath // Mark this child path for deletion too
            };
        }

        if (metadataProp.type === DATA_TYPES.OBJECT) {
            addNode(childNodes, schema, metadataProp, prop, modifiedCallerProps, childxpath, null, updatedxpath);
        } else if (primitiveDataTypes.includes(metadataProp.type)) {
            addSimpleNode(childNodes, schema, metadata, prop, modifiedCallerProps, dataxpath, xpath);
        } else {
            addNode(childNodes, schema, metadataProp, prop, modifiedCallerProps, childxpath, null, updatedxpath);
        }
    });
}

/**
 * Checks if an array is empty in both current and original data, considering various scenarios.
 * This function helps determine if an array container should be rendered as empty or if it contains data.
 * @param {Object} data - The current data object.
 * @param {Object} originalData - The original data object.
 * @param {string} dataxpath - The data XPath of the array.
 * @param {string} xpath - The schema XPath of the array.
 * @returns {boolean} True if the array is empty in both current and original data, false otherwise.
 */
function isEmptyArrayData(data, originalData, dataxpath, xpath) {
    return ((get(data, dataxpath) && get(data, dataxpath).length === 0) ||
        (Object.keys(data).length > 0 && !get(data, dataxpath))) &&
        ((get(originalData, xpath) && get(originalData, xpath).length === 0) ||
            !get(originalData, xpath));
}

function processArrayItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath, parentNode = null) {
    const { data, originalData } = callerProps;

    // SAFETY: Check if this array actually has data or should be processed
    const originalDataExists = get(originalData, xpath) !== undefined;
    const currentDataExists = get(data, dataxpath) !== undefined;

    // If neither exists, there's nothing to process
    if (!originalDataExists && !currentDataExists) {
        return;
    }

    // OPTIMIZATION: Fast count calculation to determine if we need pagination
    const originalDataArray = get(originalData, xpath) || [];
    const currentDataArray = get(data, dataxpath) || [];

    // Calculate maxItems based on the highest schema index, not just physical length
    let maxSchemaIndex = -1;
    const findMaxIndex = (item) => {
        if (!item || typeof item !== 'object') return;
        const subpropname = Object.keys(item).find(key => key.startsWith('xpath_'));
        if (!subpropname) return;
        const propxpath = item[subpropname];
        try {
            const propindex = parseInt(propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']')));
            if (!isNaN(propindex) && propindex > maxSchemaIndex) {
                maxSchemaIndex = propindex;
            }
        } catch (e) { /* ignore */ }
    };
    originalDataArray.forEach(findMaxIndex);
    currentDataArray.forEach(findMaxIndex);
    const maxItems = maxSchemaIndex > -1 ? maxSchemaIndex + 1 : Math.max(originalDataArray.length, currentDataArray.length);

    const needsPagination = maxItems > ITEMS_PER_PAGE;

    // If no pagination needed, use simplified processing
    if (!needsPagination) {
        return processArrayItemsSimple(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    }

    // OPTIMIZATION: For pagination, calculate page range FIRST

    // Use the parent node passed in, or try to find it
    if (!parentNode) {
        for (let i = tree.length - 1; i >= 0; i--) {
            if (tree[i].xpath === xpath) {
                parentNode = tree[i];
                break;
            }
        }
    }

    if (!parentNode) {
        return;
    }

    const currentPage = callerProps.paginatedNodes?.[xpath]?.page || 0;
    const totalPages = Math.ceil(maxItems / ITEMS_PER_PAGE);
    const validCurrentPage = Math.max(0, Math.min(currentPage, totalPages - 1));

    // Check if we have active filters - this determines our approach
    const hasActiveFilters = callerProps.filters && callerProps.filters.length > 0 &&
        callerProps.filters.some(f => f.filtered_values && f.filtered_values.trim() !== '');

    let pageItemMetadata = [];
    let totalFilteredCount = maxItems; // Store total filtered count for display
    const lazyXpathCache = new Map();
    const paths = [];

    if (hasActiveFilters) {
        // FILTER-FIRST APPROACH: When filters are active, collect ALL items first, then filter, then paginate
        const allItemMetadata = [];

        // Collect ALL current data items
        currentDataArray.forEach((childobject, currentIndex) => {
            if (!childobject || typeof childobject !== 'object') return;

            const subpropname = Object.keys(childobject).find(key => key.startsWith('xpath_'));
            if (!subpropname) return;

            const propxpath = childobject[subpropname];
            const propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
            const originalIndex = parseInt(propindex);
            const schemaPath = `${xpath}[${propindex}]`;

            // Cache the mapping: schema path -> current data index
            lazyXpathCache.set(schemaPath, currentIndex);

            if (!isNodeInSubtree(callerProps, xpath, schemaPath)) return;

            allItemMetadata.push({
                originalIndex: originalIndex,
                currentIndex: currentIndex,
                schemaPath: schemaPath,
                dataPath: `${dataxpath}[${currentIndex}]`,
                fromOriginal: false
            });
            paths.push(schemaPath);
        });

        // Collect ALL original data items
        for (let i = 0; i < originalDataArray.length; i++) {
            const schemaPath = `${xpath}[${i}]`;

            if (!isNodeInSubtree(callerProps, xpath, schemaPath)) continue;

            // Only add if not already processed from current data
            if (!paths.includes(schemaPath)) {
                allItemMetadata.push({
                    originalIndex: i,
                    schemaPath: schemaPath,
                    fromOriginal: true
                });
                paths.push(schemaPath);
            }
        }

        // Sort all items by their original index
        allItemMetadata.sort((a, b) => a.originalIndex - b.originalIndex);

        // Apply filtering to ALL items
        const activeFilters = callerProps.filters.filter(f => f.filtered_values && f.filtered_values.trim() !== '');
        const allFilteredItems = allItemMetadata.filter(item => {
            // Get the actual data for this item to check against filters
            let itemData;
            if (item.dataPath) {
                itemData = get(data, item.dataPath);
            } else if (lazyXpathCache.has(item.schemaPath)) {
                const currentIdx = lazyXpathCache.get(item.schemaPath);
                itemData = get(data, `${dataxpath}[${currentIdx}]`);
            } else {
                // Fallback to original data if current data not available
                itemData = get(originalData, item.schemaPath);
            }

            if (!itemData) return false;

            // Apply the same filtering logic
            return activeFilters.every(filter => {
                // First check if the item directly matches
                const directMatch = checkItemAgainstFilter(itemData, filter, schema, currentSchema.items?.$ref);
                if (directMatch) {
                    return true;
                }

                // Check nested containers
                let itemSchema = null;
                if (currentSchema.items?.$ref) {
                    const refParts = currentSchema.items.$ref.split('/');
                    if (refParts.length >= 2) {
                        itemSchema = refParts.length === 2 ?
                            schema[refParts[1]] :
                            schema[refParts[1]][refParts[2]];
                    }
                }

                if (itemSchema && itemSchema.properties) {
                    for (const propName in itemSchema.properties) {
                        const propSchema = itemSchema.properties[propName];
                        if (propSchema.type === DATA_TYPES.ARRAY ||
                            (propSchema.type === DATA_TYPES.OBJECT && propSchema.items)) {

                            const nestedData = itemData[propName];
                            if (nestedData && typeof nestedData === 'object') {
                                if (propSchema.type === DATA_TYPES.OBJECT) {
                                    const nestedMatch = checkItemAgainstFilter(nestedData, filter, schema, propSchema.items?.$ref);
                                    if (nestedMatch) {
                                        return true;
                                    }
                                }
                                else if (propSchema.type === DATA_TYPES.ARRAY && Array.isArray(nestedData)) {
                                    for (const nestedItem of nestedData) {
                                        const nestedMatch = checkItemAgainstFilter(nestedItem, filter, schema, propSchema.items?.$ref);
                                        if (nestedMatch) {
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                return false;
            });
        });

        // Store the total filtered count for display purposes
        totalFilteredCount = allFilteredItems.length;

        //Recalculate valid current page based on filtered results
        const filteredTotalPages = Math.ceil(allFilteredItems.length / ITEMS_PER_PAGE);
        const validFilteredCurrentPage = Math.max(0, Math.min(currentPage, filteredTotalPages - 1));

        // Now paginate the filtered results using the corrected page
        const filteredPageStartIndex = validFilteredCurrentPage * ITEMS_PER_PAGE;
        const filteredPageEndIndex = Math.min(filteredPageStartIndex + ITEMS_PER_PAGE, allFilteredItems.length);
        pageItemMetadata = allFilteredItems.slice(filteredPageStartIndex, filteredPageEndIndex);

    } else {
        // NO FILTERS: Use original optimized approach - paginate first, then process
        const pageStartIndex = validCurrentPage * ITEMS_PER_PAGE;
        const pageEndIndex = Math.min(pageStartIndex + ITEMS_PER_PAGE, maxItems);

        // Process current data items - but only scan for items in our page range
        currentDataArray.forEach((childobject, currentIndex) => {
            if (!childobject || typeof childobject !== 'object') return;

            const subpropname = Object.keys(childobject).find(key => key.startsWith('xpath_'));
            if (!subpropname) return;

            const propxpath = childobject[subpropname];
            const propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
            const originalIndex = parseInt(propindex);
            const schemaPath = `${xpath}[${propindex}]`;

            // Only include items in our page range
            if (originalIndex >= pageStartIndex && originalIndex < pageEndIndex) {
                // Cache the mapping: schema path -> current data index
                lazyXpathCache.set(schemaPath, currentIndex);

                if (!isNodeInSubtree(callerProps, xpath, schemaPath)) return;

                pageItemMetadata.push({
                    originalIndex: originalIndex,
                    currentIndex: currentIndex,
                    schemaPath: schemaPath,
                    dataPath: `${dataxpath}[${currentIndex}]`,
                    fromOriginal: false
                });
                paths.push(schemaPath);
            }
        });

        // Process original data items - but only for items in our page range
        for (let i = pageStartIndex; i < Math.min(pageEndIndex, originalDataArray.length); i++) {
            const schemaPath = `${xpath}[${i}]`;

            if (!isNodeInSubtree(callerProps, xpath, schemaPath)) continue;

            // Only add if not already processed from current data
            if (!paths.includes(schemaPath)) {
                pageItemMetadata.push({
                    originalIndex: i,
                    schemaPath: schemaPath,
                    fromOriginal: true
                });
                paths.push(schemaPath);
            }
        }

        // Sort items by their original index to maintain order
        pageItemMetadata.sort((a, b) => a.originalIndex - b.originalIndex);
    }

    // Filtering is now handled above in the main logic based on hasActiveFilters
    let filteredPageItems = pageItemMetadata;


    // Calculate filtered count for display (but keep original count for structural operations)
    let filteredDisplayCount = maxItems; // Default to original count
    let filteredDisplayPages = totalPages; // Default to original pages

    // When filters are active, use the count we already calculated in the main logic
    if (hasActiveFilters) {
        filteredDisplayCount = totalFilteredCount;
        filteredDisplayPages = Math.ceil(filteredDisplayCount / ITEMS_PER_PAGE);
    }

    // Calculate the correct current page based on whether filters are active
    let displayCurrentPage = validCurrentPage;
    if (hasActiveFilters) {
        // When filters are active, validate current page against filtered total pages
        displayCurrentPage = Math.max(0, Math.min(currentPage, filteredDisplayPages - 1));
    }

    // Enhanced pagination info - keeps original for structural operations, adds display info
    parentNode.pagination = {
        totalItems: maxItems,               // Original count (80) - used for new item placement
        totalPages: totalPages,             // Original pages (8) - used for new item placement
        displayItems: filteredDisplayCount, // Filtered count (40) - used for UI display
        displayPages: filteredDisplayPages, // Filtered pages (4) - used for UI display
        currentPage: displayCurrentPage,    // Corrected current page for display
        paginationId: `pagination_${xpath}`,
        xpathCache: Array.from(lazyXpathCache.entries()),
        hasActiveFilters: hasActiveFilters
    };

    // ID-based deletion detection (like table logic) for paginated items
    const originalItemIds = new Set();
    const updatedItemIds = new Set();

    if (get(originalData, xpath)) {
        get(originalData, xpath).forEach(item => {
            if (item && typeof item === 'object' && item._id) {
                originalItemIds.add(item._id);
            }
        });
    }

    if (get(data, dataxpath)) {
        get(data, dataxpath).forEach(item => {
            if (item && typeof item === 'object' && item._id) {
                updatedItemIds.add(item._id);
            }
        });
    }

    // Create nodes only for filtered page items
    filteredPageItems.forEach(item => {
        // Use cached data path if available, otherwise compute it
        let childDataPath;
        let isDeleted = false;

        // Check if this item was deleted (exists in original but not in updated)
        if (item.fromOriginal) {
            const originalItem = get(originalData, item.schemaPath);
            if (originalItem && typeof originalItem === 'object' && originalItem._id) {
                isDeleted = originalItemIds.has(originalItem._id) && !updatedItemIds.has(originalItem._id);
            }
        }

        if (item.dataPath) {
            childDataPath = item.dataPath;
        } else if (lazyXpathCache.has(item.schemaPath)) {
            const currentIdx = lazyXpathCache.get(item.schemaPath);
            childDataPath = `${dataxpath}[${currentIdx}]`;
        } else {
            // Fallback to traditional resolution only for this specific item
            childDataPath = getDataxpath(data, item.schemaPath);
        }

        // If item exists in originalData but not in updatedData (deleted), show it from originalData
        if (!childDataPath && item.fromOriginal) {
            childDataPath = item.schemaPath; // Use schema path as fallback
            isDeleted = true;
        }

        if (childDataPath) {
            // Create a modified callerProps for deleted items to force data-remove flag
            let modifiedCallerProps = callerProps;
            if (isDeleted) {
                // For deleted items, we want to show data from originalData with data-remove flag
                modifiedCallerProps = {
                    ...callerProps,
                    // Force the node creation to use originalData for deleted items
                    data: originalData,
                    // Mark that this item should get data-remove flag
                    forceDataRemove: item.schemaPath
                };
                // Use the original data path for deleted items
                childDataPath = item.schemaPath;
            }

            addNode(tree, schema, currentSchema, propname, modifiedCallerProps,
                childDataPath, DATA_TYPES.OBJECT, item.schemaPath);
        } else {
            console.warn(`No childDataPath found for ${item.schemaPath}`);
        }
    });
}

// Simplified processing for arrays that don't need pagination
function processArrayItemsSimple(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    const paths = [];
    const { data, originalData } = callerProps;
    const itemMetadata = [];

    // Collect all items (since array is small)
    if (get(originalData, xpath)) {
        for (let i = 0; i < get(originalData, xpath).length; i++) {
            const updatedxpath = `${xpath}[${i}]`;
            paths.push(updatedxpath);

            if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) continue;

            itemMetadata.push({
                originalIndex: i,
                schemaPath: updatedxpath,
                fromOriginal: true
            });
        }
    }

    // Build xpath resolution cache for current data
    const xpathCache = new Map();
    if (get(data, dataxpath)) {
        get(data, dataxpath).forEach((childobject, currentIndex) => {
            if (!childobject || typeof childobject !== 'object') return;

            const subpropname = Object.keys(childobject).find(key => key.startsWith('xpath_'));
            if (!subpropname) return;

            const propxpath = childobject[subpropname];
            const propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
            const updatedxpath = `${xpath}[${propindex}]`;

            // Cache the mapping: schema path -> current data index
            xpathCache.set(updatedxpath, currentIndex);

            if (paths.includes(updatedxpath)) return;

            if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) return;

            itemMetadata.push({
                originalIndex: parseInt(propindex),
                currentIndex: currentIndex,
                schemaPath: updatedxpath,
                dataPath: `${dataxpath}[${currentIndex}]`,
                fromOriginal: false
            });
            paths.push(updatedxpath);
        });
    }

    // Sort and process all items
    itemMetadata.sort((a, b) => a.originalIndex - b.originalIndex);

    // Apply filtering to all items
    let filteredItemMetadata = itemMetadata;
    if (callerProps.filters && callerProps.filters.length > 0 &&
        callerProps.filters.some(f => f.filtered_values && f.filtered_values.trim() !== '')) {

        const activeFilters = callerProps.filters.filter(f => f.filtered_values && f.filtered_values.trim() !== '');

        filteredItemMetadata = itemMetadata.filter(item => {
            let itemData;
            if (item.dataPath) {
                itemData = get(data, item.dataPath);
            } else if (xpathCache.has(item.schemaPath)) {
                const currentIdx = xpathCache.get(item.schemaPath);
                itemData = get(data, `${dataxpath}[${currentIdx}]`);
            } else {
                itemData = get(originalData, item.schemaPath);
            }

            if (!itemData) {
                return false;
            }

            return activeFilters.every(filter => {
                // First check if the item directly matches
                const directMatch = checkItemAgainstFilter(itemData, filter, schema, currentSchema.items?.$ref);
                if (directMatch) {
                    return true;
                }

                // Check if this is a nested array that should inherit parent's filter context
                // If the filter field path doesn't apply to this level, check if parent already matched
                const filterPath = filter.column_name;
                const currentArrayPath = xpath;

                // If the filter path doesn't include the current array path, it means this array
                // is nested under something that should be filtered at a higher level
                if (!filterPath.includes(currentArrayPath.replace(/\[\d+\]/g, ''))) {
                    return true; // Keep all items - parent level filtering already applied
                }

                // If no direct match, check if this item contains nested arrays/objects that might match
                // Get the schema for this item to see if it has nested containers
                let itemSchema = null;
                if (currentSchema.items?.$ref) {
                    const refParts = currentSchema.items.$ref.split('/');
                    if (refParts.length >= 2) {
                        itemSchema = refParts.length === 2 ?
                            schema[refParts[1]] :
                            schema[refParts[1]][refParts[2]];
                    }
                }

                // If item has nested arrays/objects, check if they actually contain matching data
                if (itemSchema && itemSchema.properties) {
                    for (const propName in itemSchema.properties) {
                        const propSchema = itemSchema.properties[propName];
                        if (propSchema.type === DATA_TYPES.ARRAY ||
                            (propSchema.type === DATA_TYPES.OBJECT && propSchema.items)) {

                            // Check if this nested container actually contains matching data
                            const nestedData = itemData[propName];
                            if (nestedData && typeof nestedData === 'object') {
                                // For nested objects, check if they contain the matching field
                                if (propSchema.type === DATA_TYPES.OBJECT) {
                                    const nestedMatch = checkItemAgainstFilter(nestedData, filter, schema, propSchema.items?.$ref);
                                    if (nestedMatch) {
                                        return true;
                                    }
                                }
                                // For nested arrays, check if any item in the array matches
                                else if (propSchema.type === DATA_TYPES.ARRAY && Array.isArray(nestedData)) {
                                    for (const nestedItem of nestedData) {
                                        const nestedMatch = checkItemAgainstFilter(nestedItem, filter, schema, propSchema.items?.$ref);
                                        if (nestedMatch) {
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                return false; // No direct match and no nested containers
            });
        });

    }

    // ID-based deletion detection (like table logic)
    // Build ID sets for comparison
    const originalItemIds = new Set();
    const updatedItemIds = new Set();

    if (get(originalData, xpath)) {
        get(originalData, xpath).forEach(item => {
            if (item && typeof item === 'object' && item._id) {
                originalItemIds.add(item._id);
            }
        });
    }

    if (get(data, dataxpath)) {
        get(data, dataxpath).forEach(item => {
            if (item && typeof item === 'object' && item._id) {
                updatedItemIds.add(item._id);
            }
        });
    }

    // Create nodes for all filtered items
    filteredItemMetadata.forEach(item => {
        let childDataPath = item.dataPath || getDataxpath(data, item.schemaPath);
        let isDeleted = false;

        // Check if this item was deleted (exists in original but not in updated)
        if (item.fromOriginal) {
            const originalItem = get(originalData, item.schemaPath);
            if (originalItem && typeof originalItem === 'object' && originalItem._id) {
                isDeleted = originalItemIds.has(originalItem._id) && !updatedItemIds.has(originalItem._id);
            }
        }

        // If item exists in originalData but not in updatedData (deleted), show it from originalData
        if (!childDataPath && item.fromOriginal) {
            // This item was deleted from updatedData but exists in originalData
            // We'll use the originalData path for display, but the node creation will handle the comparison
            childDataPath = item.schemaPath; // Use schema path as fallback
            isDeleted = true;
        }

        if (childDataPath) {
            // Create a modified callerProps for deleted items to force data-remove flag
            let modifiedCallerProps = callerProps;
            if (isDeleted) {
                // For deleted items, we want to show data from originalData with data-remove flag
                modifiedCallerProps = {
                    ...callerProps,
                    // Force the node creation to use originalData for deleted items
                    data: originalData,
                    // Mark that this item should get data-remove flag
                    forceDataRemove: item.schemaPath
                };
                // Use the original data path for deleted items
                childDataPath = item.schemaPath;
            }

            addNode(tree, schema, currentSchema, propname, modifiedCallerProps,
                childDataPath, DATA_TYPES.OBJECT, item.schemaPath);
        } else {
            console.warn(`No childDataPath found for ${item.schemaPath}`);
        }
    });
}

function getArrayDataType(currentSchema) {
    let arrayDataType = currentSchema.underlying_type;
    // Normalize integer types to a generic NUMBER type for array data.
    if ([DATA_TYPES.INT32, DATA_TYPES.INT64, DATA_TYPES.INTEGER, DATA_TYPES.FLOAT].includes(arrayDataType)) {
        arrayDataType = DATA_TYPES.NUMBER;
    }
    return arrayDataType;
}

function buildArrayAdditionalProps(schema, currentSchema) {
    const additionalProps = {
        underlyingtype: currentSchema.underlying_type
    };

    if (currentSchema.underlying_type === DATA_TYPES.ENUM) {
        const ref = currentSchema.items.$ref;
        const refSplit = ref.split('/');
        const metadata = refSplit.length === 2 ? schema[refSplit[1]] : schema[refSplit[1]][refSplit[2]];
        additionalProps.options = metadata.enum;
    }

    return additionalProps;
}


export function compareNodes(originalData, data, dataxpath, propname, xpath) {
    let object = {};
    let current = data[propname];
    let original = originalData[propname];
    if (dataxpath || xpath) {
        current = hasxpath(data, dataxpath) ? get(data, dataxpath)[propname] : undefined;
        original = hasxpath(originalData, xpath) ? get(originalData, xpath)[propname] : undefined;
    }
    if (current !== undefined && original !== undefined && (current !== original)) {
        object['data-modified'] = true;
    } else if (current !== undefined && original === undefined) {
        object['data-add'] = true;
    } else if (current === undefined && original !== undefined) {
        object['data-remove'] = true;
        object.value = original;
    }
    return object;
}
