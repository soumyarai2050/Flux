import React, { useState, useEffect, useCallback, useRef } from 'react';
import TreeView from 'react-accessible-treeview';
import { cloneDeep, get, set } from 'lodash';
import { BeatLoader } from 'react-spinners';
import { generateObjectFromSchema, addxpath, getDataxpath, getDataxpathById, clearxpath, clearId } from '../../../utils/index.js';
import { DATA_TYPES, ITEMS_PER_PAGE } from '../../../constants';
import { xpathCacheManager } from '../../../cache/xpathCache';
import Node from '../../Node';
import HeaderField from '../../HeaderField';
import NodeBaseClasses from '../../Node.module.css';
import useTreeExpansion from '../../../hooks/useTreeExpansion'; // Import our custom hook
import ProgressOverlay from '../../ProgressOverlay'; // Import the centralized progress overlay
import PropTypes from 'prop-types';


/**
 * Renders a dynamic and interactive tree view for complex data structures based on a provided schema.
 * It offloads heavy tree processing to a web worker to maintain UI responsiveness.
 */
const DataTree = ({
    projectSchema,
    modelName,
    updatedData,
    storedData,
    subtree,
    mode,
    xpath,
    onUpdate,
    onUserChange,
    selectedId,
    showHidden,
    enableObjectPagination = false,
    treeLevel,
    filters,
    quickFilter = null,
    onQuickFilterChange,
    onQuickFilterPin,
    onQuickFilterUnpin,
    pinnedFilters = [],
    isDisabled = false,
    enableQuickFilterPin = false
}) => {

    const [treeData, setTreeData] = useState([]);
    const [originalTree, setOriginalTree] = useState([]);
    const [paginatedNodes, setPaginatedNodes] = useState({});
    const [itemVisualStates, setItemVisualStates] = useState({});
    const [isWorkerProcessing, setIsWorkerProcessing] = useState(false);
    const [counter, setCounter] = useState(0);
    const [newlyAddedOrDuplicatedXPath, setNewlyAddedOrDuplicatedXPath] = useState(null); // Added state for scroll target
    const workerRef = useRef(null);
    const levelRef = useRef(treeLevel ? treeLevel : xpath ? 3 : 2);
    const treeDataRef = useRef([]); //Track current treeData for worker handler

    // Use our custom hook for expansion management
    const {
        expandedNodeXPaths,
        handleNodeToggle,
        handleExpandAll,
        handleCollapseAll,
        isExpanding,
        expansionProgress,
        expandingNodePath,
        cancelExpansion,
        expandNodeAndAllChildren,
        updateExpandedStateForTreeData,
        initializeExpansionForTree,
        autoExpandNewlyCreatedObjects,
    } = useTreeExpansion(projectSchema, updatedData, storedData);

    // ref to track when full regeneration is needed
    const needsFullRegenerationRef = useRef(false);
    const isInitialMount = useRef(true);

    // Recalculates the default expansion level when treeLevel or xpath props change.
    useEffect(() => {
        levelRef.current = treeLevel ? treeLevel : xpath ? 3 : 2;
    }, [treeLevel, xpath]);


    // Initializes and terminates the data processing web worker.
    useEffect(() => {
        if (!workerRef.current) {
            workerRef.current = new Worker(new URL('../../../workers/dataTree.worker.js', import.meta.url));
        }

        return () => {
            workerRef.current?.terminate();
            workerRef.current = null;
        }
    }, [])

    // useEffect to clear transient visual states like 'added' or 'duplicated' from itemVisualStates
    // when storedData prop changes, implying these items are now persisted.
    // Clears transient visual states (e.g., 'added', 'duplicated') when data is persisted.
    useEffect(() => {
        setItemVisualStates(prevStates => {
            const nextStates = { ...prevStates };
            let changed = false;
            for (const xpathKey in prevStates) {
                if (prevStates[xpathKey] === 'added' || prevStates[xpathKey] === 'duplicated') {
                    // If an item was marked 'added' or 'duplicated',
                    // and its schema xpath (xpathKey) now corresponds to an item in storedData,
                    // clear its transient visual state.
                    if (get(storedData, xpathKey) !== undefined) {
                        delete nextStates[xpathKey];
                        changed = true;
                    }
                }
            }
            // Only update state if an actual change occurred to avoid unnecessary re-renders.
            return changed ? nextStates : prevStates;
        });
    }, [storedData]);

    const latestPropsRef = useRef({});
    const pendingRequestRef = useRef(false);
    const lastProcessedPropsRef = useRef(null);

    // Update latestPropsRef whenever relevant props change.
    // Caches the latest props in a ref to avoid stale data in worker communication.
    useEffect(() => {
        // Clean pinnedFilters for worker - remove functions and keep only serializable data
        const cleanPinnedFilters = pinnedFilters.map(pin => ({
            key: pin.key,
            title: pin.title,
            value: pin.value,
            // Only include serializable parts of nodeData
            nodeData: pin.nodeData ? {
                key: pin.nodeData.key,
                type: pin.nodeData.type,
                title: pin.nodeData.title,
                name: pin.nodeData.name,
                dataxpath: pin.nodeData.dataxpath,
                xpath: pin.nodeData.xpath,
                autocomplete: pin.nodeData.autocomplete,
                options: pin.nodeData.options,
                dropdowndataset: pin.nodeData.dropdowndataset,
                filterEnable: pin.nodeData.filterEnable
            } : null
        }));

        latestPropsRef.current = {
            projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
            selectedId, showHidden, paginatedNodes,
            ITEMS_PER_PAGE, DATA_TYPES,
            enableObjectPagination, filters,
            quickFilter, pinnedFilters: cleanPinnedFilters
        };
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters, quickFilter, pinnedFilters
    ]);

    // Main effect to communicate with the worker when props change.
    // Triggers the web worker to process tree data when relevant props change.
    useEffect(() => {
        if (!workerRef.current) return;

        const processWithWorker = () => {
            setIsWorkerProcessing(true);
            pendingRequestRef.current = false; // Reset pending flag as we are processing now

            // Set flag for initial mount
            if (isInitialMount.current) {
                needsFullRegenerationRef.current = true;
                isInitialMount.current = false;
            }

            console.log('Data sent to worker:', { type: 'PROCESS_TREE', payload: latestPropsRef.current });
            workerRef.current.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
            lastProcessedPropsRef.current = JSON.stringify(latestPropsRef.current); // Track what we sent
        };

        // Simple change detection - only process if props actually changed
        const currentPropsString = JSON.stringify(latestPropsRef.current);
        const hasChanged = lastProcessedPropsRef.current !== currentPropsString;

        if (!hasChanged && lastProcessedPropsRef.current !== null) {
            return;
        }



        if (isWorkerProcessing) {
            pendingRequestRef.current = true;
        } else {
            // Process immediately - inputs already handle debouncing at NodeField level
            processWithWorker();
        }
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters, quickFilter, pinnedFilters
    ]);

    // Resets the full regeneration flag after a forced remount.
    useEffect(() => {
        needsFullRegenerationRef.current = false;
    }, [counter]);

    // Keeps a ref synchronized with the latest treeData state to prevent stale closures in worker handlers.
    useEffect(() => {
        treeDataRef.current = treeData;
    }, [treeData]);

    // Setup worker message handler once on component mount
    // Sets up a one-time message handler to receive processed tree data from the worker.
    useEffect(() => {
        if (!workerRef.current) return;

        const messageHandler = (event) => {
            console.log('Data received from worker:', event.data);
            const { type, payload } = event.data;
            if (type === 'TREE_GENERATED') {
                const newTreeData = payload.treeData || [];
                // Using ref to get current tree length (avoid stale closure)
                const previousTreeLength = treeDataRef.current.length;
                // A structural change is detected if the number of top-level nodes changes.
                // This is a reliable heuristic for additions/removals that should force a remount.

                const structuralChangeDetected = newTreeData.length !== previousTreeLength;

                setOriginalTree(payload.originalTree || []);
                setTreeData(newTreeData);

                // Updated condition for remounting the TreeView.
                // A remount is forced if it was pre-flagged (e.g., by filter/mode change/reload)
                // OR if the worker response indicates a significant structural change (the length check).
                if (needsFullRegenerationRef.current || structuralChangeDetected) {
                    setCounter((prev) => prev + 1);
                }

                // Use our custom hook function to update the expanded state for the tree data
                updateExpandedStateForTreeData(newTreeData);

                // Prune itemVisualStates to only include xpaths present in the newTreeData
                setItemVisualStates(prevStates => {
                    const nextStates = {};
                    let changed = false;
                    for (const xpathKey in prevStates) {
                        if (newTreeData.some(node => node.id === xpathKey)) {
                            nextStates[xpathKey] = prevStates[xpathKey];
                        } else {
                            changed = true; // Indicates an xpath was removed
                        }
                    }
                    return changed || Object.keys(prevStates).length !== Object.keys(nextStates).length
                        ? nextStates
                        : prevStates;
                });

                // Handle worker completion and pending requests atomically to avoid race conditions
                const hasPendingRequest = pendingRequestRef.current;
                if (hasPendingRequest) {
                    pendingRequestRef.current = false;
                    console.log('Data sent to worker (pending request):', { type: 'PROCESS_TREE', payload: latestPropsRef.current });
                    workerRef.current.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
                    // Keep isWorkerProcessing as true since we're immediately processing another request
                } else {
                    setIsWorkerProcessing(false); // Worker is now free
                }
            }
        };

        workerRef.current.onmessage = messageHandler;

        return () => {
            // Cleanup handled by worker termination in main cleanup effect
        };
    }, []);

    // Effect to scroll to newly added/duplicated item and manage glow timing
    // Scrolls to newly added or duplicated items and applies a temporary highlight effect.
    useEffect(() => {
        if (newlyAddedOrDuplicatedXPath) {
            // Timer for scrolling (short delay)
            const scrollTimer = setTimeout(() => {
                let finalTargetXPath = newlyAddedOrDuplicatedXPath; // Default target

                // Helper to find a node by its ID (XPath) in the current treeData
                const findNodeById = (id) => treeData.find(node => node.id === id);

                const parentNode = findNodeById(newlyAddedOrDuplicatedXPath);

                if (parentNode && parentNode.children && parentNode.children.length > 0) {
                    // Try to go one level down
                    const firstChildId = parentNode.children[0];
                    const firstChildNode = findNodeById(firstChildId);

                    if (firstChildNode) {
                        finalTargetXPath = firstChildId; // Target the first child

                        // Try to go two levels down (grandchild)
                        if (firstChildNode.children && firstChildNode.children.length > 0) {
                            const grandChildId = firstChildNode.children[0];
                            const grandChildNode = findNodeById(grandChildId);
                            if (grandChildNode) {
                                finalTargetXPath = grandChildId; // Target the grandchild
                            }
                        }
                    }
                }

                const elementToScrollTo = document.querySelector(`[data-xpath="${finalTargetXPath}"]`);
                if (elementToScrollTo) {
                    elementToScrollTo.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    // Fallback: if the deeper target isn't found, try original XPath
                    if (finalTargetXPath !== newlyAddedOrDuplicatedXPath) {
                        const originalElement = document.querySelector(`[data-xpath="${newlyAddedOrDuplicatedXPath}"]`);
                        if (originalElement) {
                            originalElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        } else {
                            console.warn(`Scroll Warning: Target element not found for primary XPath: ${newlyAddedOrDuplicatedXPath} nor deeper XPath: ${finalTargetXPath}.`);
                        }
                    } else {
                        console.warn(`Scroll Warning: Target element not found for XPath: ${finalTargetXPath}.`);
                    }
                }
                // DO NOT reset newlyAddedOrDuplicatedXPath here; it's for the glow timer
            }, 150); // Short delay for DOM updates before scrolling

            // Timer for clearing the glow (long delay)
            const glowClearTimer = setTimeout(() => {
                setNewlyAddedOrDuplicatedXPath(null); // Reset after 5 seconds to stop the glow
            }, 3000); // 3-second glow duration

            return () => {
                clearTimeout(scrollTimer);
                clearTimeout(glowClearTimer);
            };
        }
    }, [newlyAddedOrDuplicatedXPath, treeData]);


    // Handle page change for a paginated node
    // Handles pagination for nodes with a large number of children.
    const handlePageChange = useCallback((nodeId, direction, totalPagesForNode) => {
        setPaginatedNodes(prev => {
            const currentPage = prev[nodeId]?.page || 0;
            let newPage = currentPage;

            if (direction === 'next') {
                newPage = Math.min(currentPage + 1, totalPagesForNode - 1);
            } else if (direction === 'prev') {
                newPage = Math.max(currentPage - 1, 0);
            }

            // Only trigger remount if we're actually changing pages
            if (newPage !== currentPage) {
                // Check if there are any expanded nodes under this paginated container
                const hasExpandedChildren = Object.keys(expandedNodeXPaths).some(xpath =>
                    xpath.startsWith(nodeId + '.') || xpath.startsWith(nodeId + '[')
                );

                if (hasExpandedChildren) {
                    // Pagination requires remount because TreeView's internal state can get out of sync
                    // with our expansion states when the data structure changes significantly
                    needsFullRegenerationRef.current = true;
                }
            }

            return {
                ...prev,
                [nodeId]: { page: newPage }
            };
        });

        needsFullRegenerationRef.current = true;
    }, [expandedNodeXPaths]);

    // Callbacks for handling value changes from various input field types within the tree nodes.
    const handleTextChange = useCallback((e, type, xpath, value, dataxpath, validationRes) => {
        if (value === '') value = null;
        if (type === DATA_TYPES.NUMBER && value !== null) value = Number(value);
        if (type === DATA_TYPES.STRING || (type === DATA_TYPES.NUMBER && !isNaN(value))) {
            handleFormUpdate(xpath, dataxpath, value, validationRes);
        }
    }, [onUpdate, onUserChange]);

    const handleDateTimeChange = useCallback((dataxpath, xpath, value) => {
        handleFormUpdate(xpath, dataxpath, value);
    }, [onUpdate, onUserChange]);

    const handleSelectItemChange = useCallback((e, dataxpath, xpath) => {
        handleFormUpdate(xpath, dataxpath, e.target.value);
    }, [onUpdate, onUserChange]);

    const handleCheckboxToggle = useCallback((e, dataxpath, xpath) => {
        handleFormUpdate(xpath, dataxpath, e.target.checked);
    }, [onUpdate, onUserChange]);

    const handleAutocompleteChange = useCallback((e, value, dataxpath, xpath) => {
        handleFormUpdate(xpath, dataxpath, value);
    }, [onUpdate, onUserChange]);

    // Central function to update the component's state when any form input changes.
    const handleFormUpdate = (xpath, dataxpath, value, validationRes = null) => {
        const updatedObj = cloneDeep(updatedData);
        set(updatedObj, dataxpath, value);
        if (onUpdate) onUpdate(updatedObj);
        if (onUserChange) onUserChange(xpath, value, validationRes, null);
    };

    /**
     * Custom renderer for each node in the tree.
     * It determines whether to render a HeaderField (for containers) or a Node (for simple fields)
     * and attaches all necessary props and event handlers.
     */
    const nodeRenderer = ({ element, isBranch, isExpanded, getNodeProps, level, handleExpand }) => {
        if (element.id === "root") return null;

        const nodeProps = getNodeProps();
        const originalNode = element.metadata;
        const visualState = itemVisualStates[originalNode?.xpath];
        const nodeXPath = originalNode?.xpath; // Get node's XPath

        if (!originalNode) {
            console.warn("Node metadata is missing for element:", element);
            return <div {...nodeProps} style={{ paddingLeft: `${(level - 1) * 20}px` }}>Loading...</div>;
        }

        // Determine if the node should be rendered as a HeaderField (container) or a Node (simple field)
        // Prioritize isObjectContainer and isArrayContainer flags from treeHelper
        let ComponentToRender;
        if (originalNode.isObjectContainer || originalNode.isArrayContainer) {
            ComponentToRender = HeaderField;
        } else {
            // Fallback for primitive types or other simple nodes
            ComponentToRender = Node;
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


                        expandNodeAndAllChildren(xpathAttr, newObjectInstance, itemSchemaForObject, projectSchema);
                        onUpdate(updatedObj, 'add');
                        setNewlyAddedOrDuplicatedXPath(xpathAttr); // Scroll to the initialized object

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
                    handleNodeToggle(xpathAttr, true);
                    expandNodeAndAllChildren(schemaXpathForNewItem, newArrayItem, arrayItemSchema, projectSchema);

                    const newItemPageIndex = Math.floor(nextIndex / ITEMS_PER_PAGE);
                    setPaginatedNodes(prev => ({ ...prev, [xpathAttr]: { page: newItemPageIndex } }));
                    onUpdate(updatedObj, 'add');
                    setNewlyAddedOrDuplicatedXPath(schemaXpathForNewItem); // Scroll to the new array item

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
                let duplicatedObject = generateObjectFromSchema(projectSchema, cloneDeep(currentItemSchema), additionalProps, null, objectToCopy);

                // Regenerate nested objects fresh from schema to ensure proper initialization
                // Keep broker-level fields from original, but create nested structures fresh
                if (duplicatedObject.sec_positions && Array.isArray(duplicatedObject.sec_positions)) {
                    duplicatedObject.sec_positions.forEach(secPos => {
                        if (secPos) {
                            // Regenerate security object fresh from schema
                            const securityRefParts = projectSchema.definitions?.sec_position?.properties?.security?.items?.$ref?.split('/');
                            if (securityRefParts && securityRefParts.length >= 2) {
                                const securitySchema = securityRefParts.length === 2 ?
                                    projectSchema[securityRefParts[1]] :
                                    projectSchema[securityRefParts[1]][securityRefParts[2]];
                                if (securitySchema) {
                                    secPos.security = generateObjectFromSchema(
                                        projectSchema,
                                        cloneDeep(securitySchema),
                                        null,
                                        null,
                                        null  // No objToDup - create fresh from schema
                                    );
                                }
                            }

                            // Regenerate positions array fresh from schema
                            const positionRefParts = projectSchema.definitions?.sec_position?.properties?.positions?.items?.$ref?.split('/');
                            if (positionRefParts && positionRefParts.length >= 2) {
                                const positionSchema = positionRefParts.length === 2 ?
                                    projectSchema[positionRefParts[1]] :
                                    projectSchema[positionRefParts[1]][positionRefParts[2]];
                                if (positionSchema) {
                                    const freshPosition = generateObjectFromSchema(
                                        projectSchema,
                                        cloneDeep(positionSchema),
                                        null,
                                        null,
                                        null  // No objToDup - create fresh from schema
                                    );
                                    secPos.positions = [freshPosition];
                                } else {
                                    secPos.positions = [];
                                }
                            } else {
                                secPos.positions = [];
                            }
                        }
                    });
                }

                duplicatedObject = addxpath(duplicatedObject, parentDataXpath + '[' + nextIndex + ']');
                const schemaXpathForDuplicatedItem = parentOriginalXpath + '[' + nextIndex + ']';
                setItemVisualStates(prev => ({ ...prev, [schemaXpathForDuplicatedItem]: 'duplicated' }));
                parentObject.push(duplicatedObject);
                handleNodeToggle(parentOriginalXpath, true); // Expand parent
                expandNodeAndAllChildren(schemaXpathForDuplicatedItem, duplicatedObject, currentItemSchema, projectSchema);
                const totalItems = parentObject.length;
                const newItemPageIndex = Math.floor((totalItems - 1) / ITEMS_PER_PAGE);
                setPaginatedNodes(prev => ({ ...prev, [parentDataXpath]: { page: newItemPageIndex } }));
                onUpdate(updatedObj, 'add');
                setNewlyAddedOrDuplicatedXPath(schemaXpathForDuplicatedItem); // Scroll to the duplicated item

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
            if (isBranch) {
                handleNodeToggle(nodeXPath, !expandedNodeXPaths[nodeXPath]);
            }
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
            console.error('something went wrong. nodexpath found null' + xpath);
        }


        if (isChanged) {
            handleNodeToggle(nodeXPath, true);
        }


        const shouldGlow = newlyAddedOrDuplicatedXPath && newlyAddedOrDuplicatedXPath === nodeXPath;


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


        return (
            <div
                {...nodeProps}
                style={{ paddingLeft: `${(level - 1) * 20}px`, width: 'max-content' }}
                className={shouldGlow ? NodeBaseClasses.datanodeNewlyAddedGlowTarget : ''}
                data-xpath={nodeXPath}
            >
                <ComponentToRender {...commonProps} onClick={handleClick} />
            </div>
        );
    };



    // Use our custom hook function for tree initialization
    // Initializes the default expansion state for the tree when it's first loaded.
    useEffect(() => {
        initializeExpansionForTree(originalTree);
    }, [originalTree, initializeExpansionForTree]);

    // Use our custom hook function for auto-expansion
    // Automatically expands nodes that represent newly created objects.
    useEffect(() => {
        autoExpandNewlyCreatedObjects(originalTree);
    }, [originalTree, autoExpandNewlyCreatedObjects]);

    if (!treeData || treeData.length === 0) return null;

    const activeNodeIdsSet = new Set(treeData.map((node) => node.id));
    const updatedExpandedIds = Object.keys(expandedNodeXPaths)
        .filter(xpath => {
            // First check if this node exists and is marked for expansion
            if (!expandedNodeXPaths[xpath] || !activeNodeIdsSet.has(xpath)) {
                return false;
            }

            // Ensure hierarchical consistency: all parent paths must also be expanded
            // Split xpath into parts and check each parent level
            if (xpath === 'root') return true; // Root is always valid

            // Helper function to build parent path progressively
            /**
             * A helper function to derive all parent paths for a given node XPath.
             * This ensures that a child node is only considered "expanded" if all its ancestors are also expanded.
             */
            const getParentPaths = (path) => {
                const parents = [];

                // Handle array indices and nested properties
                // Examples: "eligible_brokers[0].sec_positions[0]" -> ["eligible_brokers", "eligible_brokers[0]", "eligible_brokers[0].sec_positions"]
                let currentPath = '';
                let i = 0;

                while (i < path.length) {
                    const char = path[i];
                    currentPath += char;

                    // When we hit a dot or opening bracket, the current path (minus the delimiter) is a parent
                    if (char === '.' || char === '[') {
                        const parentPath = currentPath.slice(0, -1); // Remove the delimiter
                        if (parentPath && parentPath !== 'root' && !parents.includes(parentPath)) {
                            parents.push(parentPath);
                        }
                    }
                    // When we hit a closing bracket, the current path is a complete array element parent
                    else if (char === ']') {
                        if (currentPath && currentPath !== 'root' && !parents.includes(currentPath)) {
                            parents.push(currentPath);
                        }
                    }

                    i++;
                }

                return parents;
            };

            const parentPaths = getParentPaths(xpath);

            // Check if all parent paths are expanded
            for (const parentPath of parentPaths) {
                if (!expandedNodeXPaths[parentPath]) {
                    return false; // Parent is collapsed, so child shouldn't be expanded
                }
            }

            return true;
        });

    const treeViewKey = counter;

    return (
        <div style={{ overflow: 'auto', height: '100%' }}>
            <div style={{ position: 'relative' }}>
                {isWorkerProcessing && !isDisabled && needsFullRegenerationRef.current && (
                    <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        zIndex: 1000,
                        borderRadius: '8px',
                        padding: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                        border: '1px solid rgba(0, 0, 0, 0.1)'
                    }}>
                        <BeatLoader color='yellow' size={20} />
                    </div>
                )}
                <TreeView
                    key={treeViewKey}
                    data={treeData}
                    aria-label={modelName}
                    nodeRenderer={nodeRenderer}
                    expandedIds={updatedExpandedIds} // Control TreeView expansion
                    multiSelect={false}
                    onKeyDown={(e) => {
                        e.stopPropagation();
                        e.preventDefault(); // Fully disables default keyboard behavior
                    }}
                />
            </div>

            {/* Centralized Progress Overlay */}
            <ProgressOverlay
                isVisible={isExpanding}
                current={expansionProgress.current}
                total={expansionProgress.total}
                title={`Expanding: ${expandingNodePath || 'Tree Nodes'}`}
                onCancel={cancelExpansion}
            />
        </div>
    );
};

DataTree.propTypes = {
    projectSchema: PropTypes.object.isRequired,
    modelName: PropTypes.string.isRequired,
    updatedData: PropTypes.object.isRequired,
    storedData: PropTypes.object.isRequired,
    subtree: PropTypes.object.isRequired,
    mode: PropTypes.string.isRequired,
    xpath: PropTypes.string,
    onUpdate: PropTypes.func.isRequired,
    onUserChange: PropTypes.func.isRequired,
    selectedId: PropTypes.string,
    showHidden: PropTypes.bool,
    enableObjectPagination: PropTypes.bool,
    treeLevel: PropTypes.number,
    filters: PropTypes.array,
    quickFilter: PropTypes.string,
    onQuickFilterChange: PropTypes.func,
    onQuickFilterPin: PropTypes.func,
    onQuickFilterUnpin: PropTypes.func,
    pinnedFilters: PropTypes.array,
    isDisabled: PropTypes.bool,
    enableQuickFilterPin: PropTypes.bool
};

DataTree.defaultProps = {
    selectedId: null,
    showHidden: false,
    enableObjectPagination: false,
    treeLevel: null,
    filters: [],
    isDisabled: false,
    enableQuickFilterPin: false
};

export default DataTree;