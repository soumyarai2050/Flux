import React from 'react';
import { cloneDeep, get, set } from 'lodash';
import PropTypes from 'prop-types';

import { generateObjectFromSchema } from '../../../utils/core/schemaUtils';
import { addxpath, getDataxpath, getDataxpathById, clearxpath } from '../../../utils/core/dataAccess';
import { clearId } from '../../../utils/core/objectUtils';
import { DATA_TYPES, ITEMS_PER_PAGE } from '../../../constants';
import { xpathCacheManager } from '../../../cache/xpathCache';
import Node from '../../Node';
import '../TreeRenderer/TreeRenderer.module.css';
import HeaderField from '../../HeaderField';

import AnimatedTreeNode from '../AnimatedTreeNode/AnimatedTreeNode';
import classes from './TreeRenderer.module.css';

const TreeRenderer = ({
    element,
    isBranch,
    getNodeProps,
    level,
    // From DataTree state and props
    itemVisualStates,
    expandedNodeXPaths,
    levelRef,
    treeData,
    updatedData,
    storedData,
    projectSchema,
    pinnedFilters,
    enableQuickFilterPin,
    needsFullRegenerationRef,
    // From DataTree handlers
    handleNodeToggle,
    handleTextChange,
    handleSelectItemChange,
    handleCheckboxToggle,
    handleAutocompleteChange,
    handleDateTimeChange,
    onQuickFilterChange,
    onQuickFilterPin,
    onQuickFilterUnpin,
    handleExpandAll,
    handleCollapseAll,
    handlePageChange,
    setPaginatedNodes,
    expandNodeAndAllChildren,
    onUpdate,
    setItemVisualStates,
    setCounter,
    // Animation props
    isNodeAnimating,
    getNodeTargetState,
    getNodeAnimationProps,
    animatingNodes,
    // Original toggle function for default expansion
    originalHandleNodeToggle,
    // Glow props
    newlyAddedOrDuplicatedXPath,
    setNewlyAddedOrDuplicatedXPath,
}) => {
    if (element.id === "root") return null;


    const nodeXPath = element.metadata?.xpath;
    // Glow for the node itself or any descendant of the newly added/duplicated node
    // const shouldGlow = newlyAddedOrDuplicatedXPath && nodeXPath && nodeXPath.startsWith(newlyAddedOrDuplicatedXPath);
    const shouldGlow = newlyAddedOrDuplicatedXPath && newlyAddedOrDuplicatedXPath === nodeXPath;
    const nodeProps = getNodeProps();

    // Apply glow class to the li element (tree branch wrapper) for newly added/duplicated items
    if (shouldGlow) {
        nodeProps.className = `${nodeProps.className || ''} ${classes['datanode-newly-added-glow']}`.trim();
    }

    const originalNode = element.metadata;
    const visualState = itemVisualStates[originalNode?.xpath];

    // Get animation properties for this node
    // const animationProps = getNodeAnimationProps ? getNodeAnimationProps(nodeXPath) : {};
    const nodeIsAnimating = isNodeAnimating ? isNodeAnimating(nodeXPath) : false;

    if (!originalNode) {
        console.warn("Node metadata is missing for element:", element);
        return <div {...nodeProps} style={{ paddingLeft: `${(level - 1) * 20}px` }}>Loading...</div>;
    }

    // Determine if the node should be rendered as a HeaderField (container) or a Node (simple field)
    // Prioritize isObjectContainer and isArrayContainer flags from treeHelper
    let ComponentToRender;
    let componentSpecificProps = {};

    if (originalNode.isObjectContainer || originalNode.isArrayContainer) {
        ComponentToRender = HeaderField;
    } else {
        // Fallback for primitive types or other simple nodes
        ComponentToRender = Node;
        // For Node, we enrich the data prop with the live storedValue
        const storedValue = get(storedData, originalNode.dataxpath);
        componentSpecificProps.data = {
            ...originalNode,
            storedValue: storedValue
        };
    }

    /**
     * Handles all click events within a node, including add, duplicate, remove, and expansion toggles.
     * It uses event delegation to identify the clicked action icon or element.
     */
    const handleClick = (e) => {
        const nodeXPath = originalNode?.xpath;
        if (!nodeXPath) return;

        // 1. Handle Action Clicks (add, duplicate, remove)
        const clickedAdd = e.target.closest('[data-add]');
        const clickedDuplicate = e.target.closest('[data-duplicate]');
        const clickedRemove = e.target.closest('[data-remove]');

        if (clickedAdd) {
            e.stopPropagation();
            const xpathAttr = clickedAdd.getAttribute('data-add'); // Schema path of the container (e.g., pair_strat_params.strat_leg2)
            const schemaRefString = clickedAdd.getAttribute('data-ref'); // Schema ref for item OR for object's own structure

            const containerPropsStr = clickedAdd.getAttribute('data-prop'); // Full props of the container node (originalNode)

            const isObjectInitialization = originalNode.isObjectContainer &&
                originalNode.canInitialize &&
                originalNode.schemaRef && // For object container, this is ref to its own item's schema (e.g. #/definitions/strat_leg)
                (get(updatedData, xpathAttr) === null || get(updatedData, xpathAttr) === undefined);

            const isArrayItemAddition = originalNode.isArrayContainer && schemaRefString; // For array, schemaRefString is for the *type* of item in array

            if (isObjectInitialization) {
                try {
                    let updatedObj = cloneDeep(updatedData);
                    const objectSchemaDefinitionPath = originalNode.schemaRef.split('/');

                    if (objectSchemaDefinitionPath.length < 2) {
                        console.error('[DataTree] Invalid schemaRef for object initialization:', originalNode.schemaRef);
                        return;
                    }

                    const itemSchemaForObject = objectSchemaDefinitionPath.length === 2 ?
                        projectSchema[objectSchemaDefinitionPath[1]] :
                        projectSchema[objectSchemaDefinitionPath[1]][objectSchemaDefinitionPath[2]];

                    if (!itemSchemaForObject) {
                        console.error('[DataTree] Could not find itemSchema for object ref:', originalNode.schemaRef, projectSchema);
                        return;
                    }

                    const containerOwnProps = containerPropsStr ? JSON.parse(containerPropsStr) : {};

                    let newObjectInstance = generateObjectFromSchema(
                        projectSchema,
                        cloneDeep(itemSchemaForObject),
                        containerOwnProps,
                        xpathAttr
                    );


                    set(updatedObj, xpathAttr, newObjectInstance);


                    // Only mark as 'added' if the object never existed in the original stored data.
                    // If it existed (even as null), re-initializing is a modification, not a new addition.
                    if (get(storedData, xpathAttr) === undefined) {
                        setItemVisualStates(prev => ({ ...prev, [xpathAttr]: 'added' }));
                    }

                    // Set the glow effect for the newly created object
                    setNewlyAddedOrDuplicatedXPath(xpathAttr);

                    expandNodeAndAllChildren(xpathAttr, newObjectInstance, itemSchemaForObject, projectSchema);
                    onUpdate(updatedObj, 'add');

                    // Mark that full regeneration is needed for structural changes
                    needsFullRegenerationRef.current = true;
                    return;
                } catch (err) {
                    console.error('[DataTree] ERROR during OBJECT INITIALIZATION for:', xpathAttr, err);
                    return;
                }
            } else if (isArrayItemAddition) {
                // ARRAY ITEM ADDITION LOGIC
                let updatedObj = cloneDeep(updatedData);
                // xpathAttr is the schema path of the array itself (e.g. pair_strat_params.some_array_field)
                // schemaRefString is the $ref for the items within that array (e.g. #/definitions/array_item_type)
                let arrayDataPath = getDataxpath(updatedObj, xpathAttr);
                let currentArray = get(updatedObj, arrayDataPath);

                if (!Array.isArray(currentArray)) {
                    // This case should ideally not be hit if originalNode.isArrayContainer is true and data is consistent
                    // However, as a fallback, initialize it as an empty array.
                    currentArray = [];
                    set(updatedObj, arrayDataPath, currentArray);
                }

                const arrayItemSchemaPathParts = schemaRefString.split('/');
                const arrayItemSchema = arrayItemSchemaPathParts.length === 2 ?
                    projectSchema[arrayItemSchemaPathParts[1]] :
                    projectSchema[arrayItemSchemaPathParts[1]][arrayItemSchemaPathParts[2]];

                let nextIndex = 0;
                const itemsInUpdatedDataForIdx = currentArray || [];
                let maxIndexInUpdatedData = -1;
                itemsInUpdatedDataForIdx.forEach(item => {
                    if (item && typeof item === 'object') {
                        const itemXpathProp = Object.keys(item).find(key => key.startsWith('xpath_'));
                        if (itemXpathProp && item[itemXpathProp]) {
                            const itemIndexPath = item[itemXpathProp];
                            try {
                                const extractedIndex = parseInt(itemIndexPath.substring(itemIndexPath.lastIndexOf('[') + 1, itemIndexPath.lastIndexOf(']')));
                                if (!isNaN(extractedIndex)) {
                                    maxIndexInUpdatedData = Math.max(maxIndexInUpdatedData, extractedIndex);
                                }
                            } catch (err) { /* ignore */ }
                        }
                    }
                });
                if (maxIndexInUpdatedData === -1 && itemsInUpdatedDataForIdx.length > 0 &&
                    !itemsInUpdatedDataForIdx.some(i => typeof i === 'object' && Object.keys(i).find(key => key.startsWith('xpath_')))) {
                    maxIndexInUpdatedData = itemsInUpdatedDataForIdx.length - 1;
                }
                const itemsInStoredData = get(storedData, xpathAttr);
                let maxIndexInStoredData = -1;
                if (Array.isArray(itemsInStoredData)) {
                    maxIndexInStoredData = itemsInStoredData.length > 0 ? itemsInStoredData.length - 1 : -1;
                }
                nextIndex = Math.max(maxIndexInUpdatedData, maxIndexInStoredData) + 1;

                const propsForArrayItemContext = containerPropsStr ? JSON.parse(containerPropsStr) : {};

                let newArrayItem = generateObjectFromSchema(
                    projectSchema,
                    cloneDeep(arrayItemSchema),
                    propsForArrayItemContext,
                    `${arrayDataPath}[${nextIndex}]`
                );
                newArrayItem = addxpath(newArrayItem, `${arrayDataPath}[${nextIndex}]`);

                currentArray.push(newArrayItem);

                const schemaXpathForNewItem = `${xpathAttr}[${nextIndex}]`;
                setItemVisualStates(prev => ({ ...prev, [schemaXpathForNewItem]: 'added' }));

                // Set the glow effect for the newly created array item
                setNewlyAddedOrDuplicatedXPath(schemaXpathForNewItem);

                handleNodeToggle(xpathAttr, true);
                expandNodeAndAllChildren(schemaXpathForNewItem, newArrayItem, arrayItemSchema, projectSchema);

                const newItemPageIndex = Math.floor(nextIndex / ITEMS_PER_PAGE);
                setPaginatedNodes(prev => ({ ...prev, [xpathAttr]: { page: newItemPageIndex } }));
                onUpdate(updatedObj, 'add');

                // Mark that full regeneration is needed for structural changes
                needsFullRegenerationRef.current = true;
                return;
            } else {
                // Fallback or error: Unhandled add click scenario
                console.warn("Unhandled add click for node:", originalNode, "with xpathAttr:", xpathAttr, "and schemaRef:", schemaRefString);
            }
        }

        if (clickedDuplicate) {
            e.stopPropagation();
            const xpathAttr = clickedDuplicate.getAttribute('data-duplicate');
            const ref = clickedDuplicate.getAttribute('data-ref');
            const additionalPropsStr = clickedDuplicate.getAttribute('data-prop');
            if (!xpathAttr || !xpathAttr.endsWith(']')) return;

            let updatedObj = cloneDeep(updatedData);
            let itemXpath = getDataxpath(updatedObj, xpathAttr);
            let additionalProps = additionalPropsStr ? JSON.parse(additionalPropsStr) : {};
            let objectToCopy = cloneDeep(get(updatedObj, itemXpath));

            if (!objectToCopy) return;
            objectToCopy = clearxpath(objectToCopy);
            clearId(objectToCopy);

            let parentDataXpath = itemXpath.substring(0, itemXpath.lastIndexOf('['));
            let parentOriginalXpath = xpathAttr.substring(0, xpathAttr.lastIndexOf('['));
            let parentObject = get(updatedObj, parentDataXpath);
            if (!parentObject || !Array.isArray(parentObject)) {
                set(updatedObj, parentDataXpath, []);
                parentObject = get(updatedObj, parentDataXpath);
            }

            const itemsInUpdatedData = parentObject || [];
            let maxIndexInUpdatedData = -1;
            itemsInUpdatedData.forEach(item => {
                if (item && typeof item === 'object') {
                    const xpathProp = Object.keys(item).find(key => key.startsWith('xpath_'));
                    if (xpathProp && item[xpathProp]) {
                        const itemIndexPath = item[xpathProp];
                        try {
                            const extractedIndex = parseInt(itemIndexPath.substring(itemIndexPath.lastIndexOf('[') + 1, itemIndexPath.lastIndexOf(']')));
                            if (!isNaN(extractedIndex)) {
                                maxIndexInUpdatedData = Math.max(maxIndexInUpdatedData, extractedIndex);
                            }
                        } catch (err) { /* ignore */ }
                    }
                }
            });
            if (maxIndexInUpdatedData === -1 && itemsInUpdatedData.length > 0 && !itemsInUpdatedData.some(i => typeof i === 'object' && Object.keys(i).find(key => key.startsWith('xpath_')))) {
                maxIndexInUpdatedData = itemsInUpdatedData.length - 1;
            }
            const itemsInStoredData = get(storedData, parentOriginalXpath);
            let maxIndexInStoredData = -1;
            if (Array.isArray(itemsInStoredData)) {
                maxIndexInStoredData = itemsInStoredData.length > 0 ? itemsInStoredData.length - 1 : -1;
            }
            let nextIndex = Math.max(maxIndexInUpdatedData, maxIndexInStoredData) + 1;

            const refParts = ref.split('/');
            let currentItemSchema = refParts.length === 2 ? projectSchema[refParts[1]] : projectSchema[refParts[1]][refParts[2]];
            let duplicatedObject = generateObjectFromSchema(projectSchema, cloneDeep(currentItemSchema), additionalProps, null, objectToCopy, false);

            duplicatedObject = addxpath(duplicatedObject, parentDataXpath + '[' + nextIndex + ']');
            const schemaXpathForDuplicatedItem = parentOriginalXpath + '[' + nextIndex + ']';
            setItemVisualStates(prev => ({ ...prev, [schemaXpathForDuplicatedItem]: 'duplicated' }));

            // Set the glow effect for the newly duplicated item
            setNewlyAddedOrDuplicatedXPath(schemaXpathForDuplicatedItem);

            parentObject.push(duplicatedObject);
            handleNodeToggle(parentOriginalXpath, true); // Expand parent
            expandNodeAndAllChildren(schemaXpathForDuplicatedItem, duplicatedObject, currentItemSchema, projectSchema);
            const totalItems = parentObject.length;
            const newItemPageIndex = Math.floor((totalItems - 1) / ITEMS_PER_PAGE);
            setPaginatedNodes(prev => ({ ...prev, [parentDataXpath]: { page: newItemPageIndex } }));
            onUpdate(updatedObj, 'add');

            // Mark that full regeneration is needed for structural changes
            needsFullRegenerationRef.current = true;
            // setCounter(prev => prev + 1);
            return; // Action handled
        }

        if (clickedRemove) {
            e.stopPropagation();
            const xpathAttr = clickedRemove.getAttribute('data-remove'); // Schema path of the item/object to remove

            // Handle removal of an object (setting it to null)
            if (originalNode.isObjectContainer && !xpathAttr.endsWith(']')) {
                let updatedObj = cloneDeep(updatedData);

                // Resolve the stale schema path to a current data path before setting to null,
                // to handle cases where parent array indexes have shifted due to other deletions.
                let dataPathForObject = xpathAttr; // Default to schema path

                if (xpathAttr.includes('[')) {
                    // This is a property inside an array item. We need to resolve its path.
                    // Use a regex to find the parent array item's path and the subsequent property path.
                    const match = xpathAttr.match(/(.*\[\d+\])(.*)/);

                    if (match) {
                        const parentItemSchemaPath = match[1]; // e.g., '...sec_positions[2]'
                        const propertySuffix = match[2];       // e.g., '.security' or '.security.name'

                        // Use our ID-based resolver to find the current data path of the parent array item.
                        const parentItemDataPath = getDataxpathById(updatedObj, parentItemSchemaPath, storedData, xpathCacheManager);

                        if (parentItemDataPath) {
                            // Construct the final, correct data path.
                            dataPathForObject = parentItemDataPath + propertySuffix;
                        } else {
                            console.warn(`Could not resolve current data path for parent ${parentItemSchemaPath}. Deletion may fail.`);
                        }
                    }
                }

                set(updatedObj, dataPathForObject, null); // Use the resolved data path

                onUpdate(updatedObj, 'remove'); // 'remove' might signify data changed to null

                // Mark that full regeneration is needed for structural changes
                needsFullRegenerationRef.current = true;
                setCounter(prev => prev + 1); // Force immediate regeneration
                return; // Action handled
            }
            // Handle removal of an array item - FIXED: Physically remove from updatedData (like table logic)
            else if (xpathAttr && xpathAttr.endsWith(']')) {
                let updatedObj = cloneDeep(updatedData);

                // Try ID-based lookup first (faster after index shifts), then fallback to normal getDataxpath
                let itemDataPath = getDataxpathById(updatedObj, xpathAttr, storedData, xpathCacheManager);

                if (!itemDataPath) {
                    console.warn('No data path found for array item deletion (even with ID lookup):', xpathAttr);
                    return;
                }

                // Extract array path and item index from the data path
                const lastBracketIndex = itemDataPath.lastIndexOf('[');
                if (lastBracketIndex === -1) {
                    console.warn('Invalid array item path for deletion:', itemDataPath);
                    return;
                }

                const arrayPath = itemDataPath.substring(0, lastBracketIndex);
                const itemIndex = parseInt(itemDataPath.substring(lastBracketIndex + 1, itemDataPath.lastIndexOf(']')));

                if (isNaN(itemIndex)) {
                    console.warn('Invalid array index for deletion:', itemDataPath);
                    return;
                }

                // Get the array and physically remove the item (like table logic)
                const parentArray = get(updatedObj, arrayPath);
                if (Array.isArray(parentArray) && itemIndex >= 0 && itemIndex < parentArray.length) {
                    // Physically remove the item from updatedData
                    parentArray.splice(itemIndex, 1);
                    // Set the modified array back
                    set(updatedObj, arrayPath, parentArray);

                    // Update the xpath cache to reflect the index shift after removal
                    xpathCacheManager.removeItem(arrayPath, xpathAttr, itemIndex);

                    onUpdate(updatedObj, 'remove');

                    // Mark that full regeneration is needed for structural changes
                    needsFullRegenerationRef.current = true;
                    setCounter(prev => prev + 1);
                } else {
                    console.warn('Array or item index not found for deletion:', arrayPath, itemIndex, parentArray);
                }
                return; // Action handled
            }
        }

        const clickedArrow = e.target.closest('[data-open], [data-close]');
        if (clickedArrow) {
            e.stopPropagation();
            if (clickedArrow.hasAttribute('data-open')) {
                handleNodeToggle(nodeXPath, true);
            } else if (clickedArrow.hasAttribute('data-close')) {
                handleNodeToggle(nodeXPath, false);
            }
            return;
        }

        const clickedTitle = e.target.closest('[data-header-title="true"]');
        if (clickedTitle) {
            e.stopPropagation();
            if (isBranch) { // isBranch is from react-accessible-treeview, refers to having children in the view model
                handleNodeToggle(nodeXPath, !expandedNodeXPaths[nodeXPath]);
            }
            return;
        }

        // Fallback for general click on the component itself if it's a branch
        // if (isBranch) {
        //     handleNodeToggle(nodeXPath, !expandedNodeXPaths[nodeXPath]);
        // }
    };

    let nodeIsOpen = false;
    let isChanged = false; // True if a default expansion decision is made AND can be persisted

    if (nodeXPath) {
        // Node has an XPath: check for explicit state or apply XPath-based default level
        const explicitState = expandedNodeXPaths[nodeXPath];

        if (explicitState === undefined) {
            // No explicit state - apply default level-based expansion
            if (level <= levelRef.current && (originalNode?.isObjectContainer || originalNode?.isArrayContainer)) {
                nodeIsOpen = true;
                isChanged = true; // Mark to persist this default decision
            }
        } else {
            // An explicit state exists (true or false), so we just use it.
            nodeIsOpen = explicitState;
        }
    } else {
        console.error('something went wrong. nodexpath found null' + nodeXPath);
    }


    if (isChanged) {
        // Use original toggle function for default expansion to avoid animation delays
        if (originalHandleNodeToggle) {
            originalHandleNodeToggle(nodeXPath, true);
        } else {
            handleNodeToggle(nodeXPath, true, true); // Skip animation flag
        }
    }


    const dataPayload = {
        ...originalNode,
        isOpen: nodeIsOpen,
        onTextChange: handleTextChange,
        onSelectItemChange: handleSelectItemChange,
        onCheckboxChange: handleCheckboxToggle,
        onAutocompleteOptionChange: handleAutocompleteChange,
        onDateTimeChange: handleDateTimeChange,
        onQuickFilterChange: onQuickFilterChange,
        onQuickFilterPin: onQuickFilterPin,
        onQuickFilterUnpin: onQuickFilterUnpin,
        pinnedFilters: pinnedFilters,
        updatedDataForColor: updatedData,
        storedDataForColor: storedData,
        visualState: visualState,
        projectSchema: projectSchema, // Pass the project schema for identifier resolution
        // Add expansion controls
        hasChildren: isBranch,
        onExpandAll: handleExpandAll,
        onCollapseAll: handleCollapseAll,
        onNodeToggle: handleNodeToggle,
        treeData: treeData,
        expandedNodeXPaths: expandedNodeXPaths,
        enableQuickFilterPin
    };

    if (originalNode.pagination) {
        dataPayload.pagination = {
            ...originalNode.pagination,
            onPageChange: (directionOrPage) => {
                // If a number is passed, jump to that page directly
                if (typeof directionOrPage === 'number') {
                    setPaginatedNodes(prev => ({
                        ...prev,
                        [element.id]: { page: directionOrPage }
                    }));
                    needsFullRegenerationRef.current = true;
                } else {
                    // Otherwise, use next/prev logic
                    handlePageChange(element.id, directionOrPage, originalNode.pagination.totalPages);
                }
            }
        };
    }

    const commonProps = {
        data: dataPayload,
        isOpen: nodeIsOpen,
    };




    // Use AnimatedTreeNode only for container nodes during normal operations
    // Use regular div during tree regeneration to avoid unwanted animations
    const shouldUseAnimation = !needsFullRegenerationRef.current && (ComponentToRender === HeaderField);

    const nodeStyle = {
        paddingLeft: `${(level - 1) * 20}px`,
        width: 'max-content',
        ...(nodeIsAnimating && { transform: 'translateZ(0)' }) // Hardware acceleration during animation
    };

    if (shouldUseAnimation) {
        // Use AnimatedTreeNode for smooth accordion animation during expand/collapse
        return (
            <AnimatedTreeNode
                animationKey={`${nodeXPath}-${level}`}
                level={level}
                isContainer={ComponentToRender === HeaderField}
                style={nodeStyle}
                data-xpath={nodeXPath}
                {...nodeProps}
            >
                <ComponentToRender {...commonProps} onClick={handleClick} />
            </AnimatedTreeNode>
        );
    } else {
        // Use regular div during tree regeneration or for simple nodes
        return (
            <li {...nodeProps} style={nodeStyle}>
                <ComponentToRender
                    data={
                        ComponentToRender === Node ?
                            { ...originalNode, storedValue: get(storedData, originalNode.dataxpath) } :
                            originalNode
                    }
                    onClick={handleClick}
                    onTextChange={handleTextChange}
                    onSelectItemChange={handleSelectItemChange}
                    onCheckboxChange={handleCheckboxToggle}
                    onAutocompleteChange={handleAutocompleteChange}
                    onDateTimeChange={handleDateTimeChange}
                    onQuickFilterChange={onQuickFilterChange}
                    onQuickFilterPin={onQuickFilterPin}
                    onQuickFilterUnpin={onQuickFilterUnpin}
                    visualState={visualState}
                    pinnedFilters={pinnedFilters}
                    enableQuickFilterPin={enableQuickFilterPin}
                    triggerGlowForXPath={newlyAddedOrDuplicatedXPath}
                />
            </li>
        );
    }
};

TreeRenderer.propTypes = {
    element: PropTypes.object.isRequired,
    isBranch: PropTypes.bool.isRequired,
    getNodeProps: PropTypes.func.isRequired,
    level: PropTypes.number.isRequired,
    itemVisualStates: PropTypes.object.isRequired,
    expandedNodeXPaths: PropTypes.object.isRequired,
    levelRef: PropTypes.object.isRequired,
    treeData: PropTypes.array.isRequired,
    updatedData: PropTypes.object.isRequired,
    storedData: PropTypes.object.isRequired,
    projectSchema: PropTypes.object.isRequired,
    pinnedFilters: PropTypes.array.isRequired,
    enableQuickFilterPin: PropTypes.bool.isRequired,
    needsFullRegenerationRef: PropTypes.object.isRequired,
    handleNodeToggle: PropTypes.func.isRequired,
    handleTextChange: PropTypes.func.isRequired,
    handleSelectItemChange: PropTypes.func.isRequired,
    handleCheckboxToggle: PropTypes.func.isRequired,
    handleAutocompleteChange: PropTypes.func.isRequired,
    handleDateTimeChange: PropTypes.func.isRequired,
    onQuickFilterChange: PropTypes.func,
    onQuickFilterPin: PropTypes.func,
    onQuickFilterUnpin: PropTypes.func,
    handleExpandAll: PropTypes.func.isRequired,
    handleCollapseAll: PropTypes.func.isRequired,
    handlePageChange: PropTypes.func.isRequired,
    setPaginatedNodes: PropTypes.func.isRequired,
    expandNodeAndAllChildren: PropTypes.func.isRequired,
    onUpdate: PropTypes.func.isRequired,
    setItemVisualStates: PropTypes.func.isRequired,
    setCounter: PropTypes.func.isRequired,
    // Animation props
    isNodeAnimating: PropTypes.func,
    getNodeTargetState: PropTypes.func,
    getNodeAnimationProps: PropTypes.func,
    animatingNodes: PropTypes.instanceOf(Set),
    originalHandleNodeToggle: PropTypes.func,
    // Glow props
    newlyAddedOrDuplicatedXPath: PropTypes.string,
    setNewlyAddedOrDuplicatedXPath: PropTypes.func.isRequired,
};

export default TreeRenderer; 