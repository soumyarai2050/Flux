import { cloneDeep, get, isEqual } from 'lodash';
import { MODES, DATA_TYPES ,ITEMS_PER_PAGE} from '../constants';
import {
    getEnumValues, getModelSchema, hasxpath, setAutocompleteValue, primitiveDataTypes, getDataxpath,
    isNodeInSubtree, complexFieldProps, treeState, fieldProps, getAutocompleteDict, getMetaFieldDict, 
    getMappingSrcDict, compareNodes
} from '../utils';

// New helper function to determine data status
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
        if (!isEqual(oldValue, newValue)) {
            return 'modified';
        }
    }
    return 'unchanged';
}

// Helper function to strip array indices from an XPath
// e.g., "eligible_brokers[0].sec_positions[1].security.sec_id" -> "eligible_brokers.sec_positions.security.sec_id"
function stripIndices(xpath) {
    if (!xpath) return '';
    return xpath.replace(/\[\d+\]/g, '');
}

// Helper function to get the schema definition for a specific path, handling arrays and $refs.
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
        } else if (currentSchema.type === DATA_TYPES.OBJECT && currentSchema.items && currentSchema.items.$ref && i < parts.length -1) {
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
function checkMatch(nodeValue, filterValuesString) {
    if (filterValuesString === null || filterValuesString === undefined || filterValuesString.trim() === '') {
        return false; // An empty filter string means no active filter criteria from this source.
    }
    if (nodeValue === null || nodeValue === undefined) {
        return false; // Node has no value, cannot match.
    }
    const filterTokens = filterValuesString.split(',').map(fv => fv.trim().toLowerCase()).filter(token => token !== ''); // Ensure tokens are not empty strings
    if (filterTokens.length === 0) {
        return false; // No valid filter tokens after trimming and filtering empty ones.
    }
    const valueStr = String(nodeValue).toLowerCase();

    // Return true if any non-empty filter token is included in the node's value string.
    return filterTokens.some(token => valueStr.includes(token));
}

// Recursive function to filter a single node based on the new requirements.
function filterNodeRecursive(node, projectSchema, modelName, filters) {
    if (!node) return null;

    // Clone the node to avoid modifying the original tree structure during the filter check iteration.
    const newNode = cloneDeep(node);

    let isDirectFieldMatch = false;
    if (!(node.isObjectContainer || node.isArrayContainer) && node.xpath && node.value !== undefined) {
        const genericPath = stripIndices(node.xpath);
        const fieldSchema = getSchemaForPath(projectSchema, modelName, genericPath);
        if (fieldSchema && fieldSchema.filter_enable) {
            const relevantFilter = filters.find(f => f.fld_name === genericPath && f.fld_value && f.fld_value.trim() !== '');
            if (relevantFilter && checkMatch(node.value, relevantFilter.fld_value)) {
                isDirectFieldMatch = true;
            }
        }
    }

    if (node.isObjectContainer) {
        let hasMatchingDescendant = false;
        const processedChildren = [];
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
                        const relevantChildFilter = filters.find(f => f.fld_name === genericChildPath && f.fld_value && f.fld_value.trim() !== '');
                        if (relevantChildFilter && checkMatch(originalChild.value, relevantChildFilter.fld_value)) {
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
                        // If the parent object (node) was kept due to a direct primitive match,
                        // then we should include this originalChild container as it was (unfiltered by this pass).
                        if (hasDirectPrimitiveChildMatch) { 
                            finalChildren.push(cloneDeep(originalChild));
                        } else if (originalChild.isArrayContainer) {
                            // Parent was kept due to *other* descendants, not its own primitives.
                            // This array child didn't match anything, so it becomes an empty array.
                            const emptyArray = cloneDeep(originalChild);
                            emptyArray.children = [];
                            finalChildren.push(emptyArray);
                        }
                        // If originalChild is an object and we are in this 'else' block (no correspondingFilteredChild)
                        // and the parent was NOT kept due to hasDirectPrimitiveChildMatch (i.e., parent was kept due to other descendants),
                        // then this object child (which didn't match anything) is pruned.
                    }
                }
            });
            newNode.children = finalChildren;
            return newNode;
        }
        return null; // Object not kept

    } else if (node.isArrayContainer) {
        const itemMatches = [];
        if (node.children) {
            for (const item of node.children) {
                const filteredItem = filterNodeRecursive(item, projectSchema, modelName, filters);
                if (filteredItem) {
                    itemMatches.push(filteredItem);
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

export function generateTreeStructure(schema, currentSchemaName, callerProps) {
    if (!schema || Object.keys(schema).length === 0) return [];

    const currentSchema = getModelSchema(currentSchemaName, schema);
    let tree = [];
    
    const childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DATA_TYPES.OBJECT, callerProps, currentSchemaName, currentSchemaName);
    
    Object.keys(currentSchema.properties).forEach(propname => {
        if (callerProps.xpath && callerProps.xpath !== propname) return;
        
        const metadataProp = currentSchema.properties[propname];
        metadataProp.required = currentSchema.required.includes(propname) ? metadataProp.required : [];

        if (metadataProp.type === DATA_TYPES.OBJECT && metadataProp.items) {
            addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
        } else if (metadataProp.type && primitiveDataTypes.includes(metadataProp.type)) {
            addSimpleNode(childNode, schema, currentSchema, propname, callerProps);
        } else {
            addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
        }
    });

    // Apply filtering if filters are provided and at least one filter is active
    if (callerProps.filters && callerProps.filters.length > 0 && 
        callerProps.filters.some(f => f.fld_value && f.fld_value.trim() !== '')) {
        
        const filteredResultTree = [];
        for (const topLevelNode of tree) { // Assuming `tree` contains the root(s) of your generated structure
            const filteredNode = filterNodeRecursive(topLevelNode, schema, currentSchemaName, callerProps.filters);
            if (filteredNode) {
                filteredResultTree.push(filteredNode);
            }
        }
        tree = filteredResultTree;
    } else {
        // No active filters, or no filters array, return the original tree.
        // This path is implicitly handled as `tree` remains unchanged.
    }

    return tree;
}

function addNode(tree, schema, currentSchema, propname, callerProps, dataxpath, type, xpath) {
    const { data, originalData, mode } = callerProps;
    const currentSchemaType = type || currentSchema.type;

    // Handle object type with items
    if (currentSchema.items && currentSchemaType === DATA_TYPES.OBJECT) {
        handleObjectWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    } 
    // Handle array type with items
    else if (currentSchema.items && currentSchema.type === DATA_TYPES.ARRAY) {
        handleArrayWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    } 
    // Handle simple array type
    else if (currentSchema.type === DATA_TYPES.ARRAY) {
        handleSimpleArray(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath);
    }
}

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

    const isNull = (get(callerProps.data, dataxpath) === null || get(callerProps.originalData, xpath) === null);

    if (isNull) {
        // Set properties on the actualHeaderNode itself, not its children array
        actualHeaderNode.canInitialize = true;
        actualHeaderNode.schemaRef = itemRefForHeaderNode; 
        // actualHeaderNode.children is already initialized as [] by addHeaderNode and should remain empty
        return; // No children properties processed if null
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

function handleArrayWithItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    if (callerProps.mode === MODES.EDIT && currentSchema.server_populate) return;

    const { data, originalData } = callerProps;
    const hasEmptyData = isEmptyArrayData(data, originalData, dataxpath, xpath);

    if (get(callerProps.data, dataxpath) === undefined && get(callerProps.originalData, xpath) === undefined) return;

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
    const mainArrayContainerNode_Children = tree[tree.length - 1].children;
    processArrayItems(mainArrayContainerNode_Children, schema, currentSchema, propname, callerProps, dataxpath, xpath);
}

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

function addHeaderNode(node, currentSchema, propname, type, callerProps, dataxpath, xpath, ref, objectState) {
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

    if (newExists && !oldExists) {
        headerNode['data-add'] = true;
    } else if ((newValue === null || !newExists) && oldExists && oldValue !== null) {
        headerNode['data-remove'] = true;
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

    // if (!dataxpath) { // This seems problematic, dataxpath can be valid but point to null
    //     headerNode['data-remove'] = true;
    // }
    // The 'data-remove', 'object-add', 'object-remove' flags relate to UI interaction capabilities,
    // distinct from dataStatus which is about data comparison. Retain them if they drive UI buttons.
    // For simplicity, let's assume objectState (add/remove capability) is still determined by schema props mostly.
    // This part might need further refinement based on how these flags are used for action buttons.
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
            // If object exists, can it be removed (set to null)? If null, can it be initialized?
            const isCurrentlyNull = get(callerProps.data, dataxpath) === null;
            if (isCurrentlyNull && !currentSchema.required && ref) { // Optional and has a schema to initialize from
                 headerNode['object-add'] = true; // Can initialize
            }
            if (!isCurrentlyNull && !currentSchema.required) {
                 headerNode['object-remove'] = true; // Can remove (set to null)
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

    // Compare with original data - replaced by dataStatus
    const comparedProps = compareNodes(originalData, data, dataxpath, propname, xpath);
    Object.assign(node, comparedProps);

    // Check if node should be added
    if (!shouldAddNode(node, callerProps)) return;

    tree.push(node);
}

// Helper functions for addSimpleNode
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

    if (dataStatus === 'new') {
        node['data-add'] = true;
    } else if (dataStatus === 'deleted') {
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

function createSimpleNode(attributes, propname, dataxpath, xpath, data, currentSchema, callerProps) {
    const nodeXpath = xpath ? `${xpath}.${propname}` : propname;
    const nodeDataXpath = dataxpath ? `${dataxpath}.${propname}` : propname;

    return {
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
}

function shouldAddNode(node, callerProps) {
    if ((node.serverPopulate && callerProps.mode === MODES.EDIT) || 
        (node.hide && callerProps.hide) || 
        (node.uiUpdateOnly && node.value === undefined)) {
        return false;
    }

    if (node.type === DATA_TYPES.BOOLEAN && node.button && callerProps.mode === MODES.EDIT) {
        return false;
    }

    return true;
}

function addNodeProperties(node, attributes, currentSchema, schema, data, callerProps) {
    // Add regular field properties
    fieldProps.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {
            node[usageName] = attributes[propertyName];
        }
    });

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

function processMetadata(metadata, currentSchema) {
    const propertiesToCopy = ['orm_no_update', 'server_populate', 'ui_update_only', 'auto_complete'];
    
    propertiesToCopy.forEach(prop => {
        if (currentSchema.hasOwnProperty(prop) || metadata.hasOwnProperty(prop)) {
            metadata[prop] = metadata[prop] || currentSchema[prop];
        }
    });

    return metadata;
}

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

        if (metadataProp.type === DATA_TYPES.OBJECT) {
            addNode(childNodes, schema, metadataProp, prop, callerProps, childxpath, null, updatedxpath);
        } else if (primitiveDataTypes.includes(metadataProp.type)) {
            addSimpleNode(childNodes, schema, metadata, prop, callerProps, dataxpath, xpath);
        } else {
            addNode(childNodes, schema, metadataProp, prop, callerProps, childxpath, null, updatedxpath);
        }
    });
}

function isEmptyArrayData(data, originalData, dataxpath, xpath) {
    return ((get(data, dataxpath) && get(data, dataxpath).length === 0) || 
            (Object.keys(data).length > 0 && !get(data, dataxpath))) &&
           ((get(originalData, xpath) && get(originalData, xpath).length === 0) || 
            !get(originalData, xpath));
}

function processArrayItems(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    const paths = [];
    const { data, originalData } = callerProps;
    
    // First, collect all items that need to be processed
    const itemsToProcess = [];
    
    // Process original data items
    if (get(originalData, xpath)) {
        for (let i = 0; i < get(originalData, xpath).length; i++) {
            const updatedxpath = `${xpath}[${i}]`;
            let childxpath = `${dataxpath}[${i}]`;
            childxpath = getDataxpath(data, updatedxpath);
            paths.push(updatedxpath);
            
            if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) continue;
            
            itemsToProcess.push({
                index: i,
                childxpath,
                updatedxpath,
                fromOriginal: true
            });
        }
    }

    // Process modified data items
    if (get(data, dataxpath)) {
        get(data, dataxpath).forEach((childobject, i) => {
            const subpropname = Object.keys(childobject).find(key => key.startsWith('xpath_'));
            if (!subpropname) return;
            
            const propxpath = childobject[subpropname];
            const propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
            const updatedxpath = `${xpath}[${propindex}]`;
            
            if (paths.includes(updatedxpath)) return;
            
            const childxpath = `${dataxpath}[${i}]`;
            if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) return;
            
            itemsToProcess.push({
                index: i,
                childxpath,
                updatedxpath,
                fromOriginal: false
            });
            paths.push(childxpath);
        });
    }
    
    // Add pagination information to the parent node
    const totalItems = itemsToProcess.length;
    const needsPagination = totalItems > ITEMS_PER_PAGE;
    
    // If we need pagination, create pagination controls
    if (needsPagination) {
        // Find the parent node (assuming it's the last one added to tree)
        let parentNode = null;
        for (let i = tree.length - 1; i >= 0; i--) {
            if (tree[i].xpath === xpath) {
                parentNode = tree[i];
                break;
            }
        }
        
        if (parentNode) {
            // Add pagination info to the parent node
            parentNode.pagination = {
                totalItems,
                totalPages: Math.ceil(totalItems / ITEMS_PER_PAGE),
                currentPage: 0,
                paginationId: `pagination_${xpath}`
            };
            
            // Create pagination controls
            const paginationNode = {
                id: parentNode.pagination.paginationId,
                key: 'pagination',
                name: `Page 1 of ${parentNode.pagination.totalPages}`,
                isPagination: true,
                xpath: `${xpath}_pagination`,
                prevPage: 0, // Initially disabled
                nextPage: 1,
                onPageChange: true // Flag to handle pagination in the component
            };
            
            // Add the pagination node to the tree
            tree.push(paginationNode);
            
            // Only process items for the current page (first page)
            const startIndex = 0;
            const endIndex = Math.min(ITEMS_PER_PAGE, totalItems);
            itemsToProcess.slice(startIndex, endIndex).forEach(item => {
                addNode(tree, schema, currentSchema, propname, callerProps, item.childxpath, DATA_TYPES.OBJECT, item.updatedxpath);
            });
        } else {
            // If no parent node found, process all items (fallback)
            itemsToProcess.forEach(item => {
                addNode(tree, schema, currentSchema, propname, callerProps, item.childxpath, DATA_TYPES.OBJECT, item.updatedxpath);
            });
        }
    } else {
        // If we don't need pagination, process all items
        itemsToProcess.forEach(item => {
            addNode(tree, schema, currentSchema, propname, callerProps, item.childxpath, DATA_TYPES.OBJECT, item.updatedxpath);
        });
    }
}

function getArrayDataType(currentSchema) {
    let arrayDataType = currentSchema.underlying_type;
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