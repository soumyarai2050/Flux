import React, { useState, useEffect, useCallback, useRef } from 'react';
import TreeView from 'react-accessible-treeview';
import { cloneDeep, get, set } from 'lodash';
import { generateObjectFromSchema, addxpath, getDataxpath, /* setTreeState, */ clearxpath, clearId } from '../../../utils'; // Comment out setTreeState
import { DATA_TYPES, ITEMS_PER_PAGE } from '../../../constants';
import Node from '../../Node';
import HeaderField from '../../HeaderField';
import NodeBaseClasses from '../../Node.module.css'; // Added for glow effect
import PropTypes from 'prop-types';


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
    filters
}) => {

    const [treeData, setTreeData] = useState([]);
    const [originalTree, setOriginalTree] = useState([]);
    const [paginatedNodes, setPaginatedNodes] = useState({});
    const [itemVisualStates, setItemVisualStates] = useState({});
    const [isWorkerProcessing, setIsWorkerProcessing] = useState(false);
    const [expandedNodeXPaths, setExpandedNodeXPaths] = useState({ "root": true }); // Initialize with "root": true
    const [counter, setCounter] = useState(0);
    const [newlyAddedOrDuplicatedXPath, setNewlyAddedOrDuplicatedXPath] = useState(null); // Added state for scroll target
    const initialExpansionSetForCurrentTreeRef = useRef(false); // Ref to track initial expansion
    const workerRef = useRef(null);
    const levelRef = useRef(treeLevel ? treeLevel : xpath ? 3 : 2);

    useEffect(() => {
        levelRef.current = treeLevel ? treeLevel : xpath ? 3 : 2;
    }, [treeLevel, xpath]);

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
    }, [storedData]); // React to changes in storedData. `get` from lodash is a stable function reference.

    const latestPropsRef = useRef({});
    const pendingRequestRef = useRef(false);

    // Refs to store previous prop values for reload detection
    const prevUpdatedDataRef = useRef(updatedData);
    const prevStoredDataRef = useRef(storedData);

    // Update latestPropsRef whenever relevant props change.
    // This ref always holds the most current data to be sent to the worker.
    useEffect(() => {
        latestPropsRef.current = {
            projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
            selectedId, showHidden, paginatedNodes,
            ITEMS_PER_PAGE, DATA_TYPES,
            enableObjectPagination, filters
            // expandedNodeXPaths is managed locally, no need to send to worker for basic tree generation
        };
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters
    ]);

    // Main effect to communicate with the worker when props change.
    useEffect(() => {
        if (!workerRef.current) return;

        let isReloadScenario = false;
        // Detect reload: updatedData changed and now matches storedData, after being different from storedData
        if (updatedData !== prevUpdatedDataRef.current &&
            prevUpdatedDataRef.current !== prevStoredDataRef.current &&
            updatedData === storedData) {
            isReloadScenario = true;
            console.log("DataTree: Reload Scenario 1 detected (updatedData aligned with storedData).");
        }
        // Detect reload: storedData changed, and updatedData matches the new storedData
        else if (storedData !== prevStoredDataRef.current &&
            updatedData === storedData) {
            isReloadScenario = true;
            console.log("DataTree: Reload Scenario 2 detected (storedData changed, updatedData aligned).");
        }

        if (isReloadScenario) {
            console.log("DataTree: Resetting expanded nodes and initial expansion flag due to reload.");
            setExpandedNodeXPaths({ "root": true }); // Reset to only root expanded
            initialExpansionSetForCurrentTreeRef.current = false; // Allow re-application of initial expansion rules
            // Note: setPaginatedNodes({}); // Not resetting paginatedNodes for now, to keep it minimal
            // Note: setItemVisualStates({}); // Not resetting itemVisualStates for now
        }

        const processWithWorker = () => {
            console.log("Posting to worker with props:", latestPropsRef.current);
            setIsWorkerProcessing(true);
            pendingRequestRef.current = false; // Reset pending flag as we are processing now
            workerRef.current.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
        };

        if (isWorkerProcessing) {
            console.log("Worker is busy, flagging a pending request.");
            pendingRequestRef.current = true;
        } else {
            // Worker is not busy, so process the current latestProps
            processWithWorker();
        }

        // This effect is primarily triggered by changes in the props listed in its dependency array.
        // isWorkerProcessing is NOT in the dependency array to avoid loops.
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters
    ]);

    // Effect to update previous prop refs *after* all other effects for the render cycle.
    useEffect(() => {
        prevUpdatedDataRef.current = updatedData;
        prevStoredDataRef.current = storedData;
    }); // Runs after every render

    // Setup worker message handler once on component mount
    useEffect(() => {
        if (!workerRef.current) return;

        const messageHandler = (event) => {
            const { type, payload } = event.data;
            if (type === 'TREE_GENERATED') {
                console.log("Worker response received:", payload);
                setOriginalTree(payload.originalTree || []);
                const newTreeData = payload.treeData || [];
                setTreeData(newTreeData);
                setCounter((prev) => prev + 1);

                // Prune expandedNodeXPaths: Addressed Issue 1 here.
                // The old pruning was too aggressive, removing states for paginated-away items.
                // Actual pruning for deleted items is handled by specific 'remove' action handlers.
                // We primarily ensure 'root' consistency here, and preserve other user-set expansions.
                setExpandedNodeXPaths(prevExpandedPaths => {
                    const newExpandedState = { ...prevExpandedPaths }; // Start with a copy
                    let changed = false;
                    const rootNodePresentInNewTree = newTreeData.some(node => node.id === "root");

                    if (rootNodePresentInNewTree) {
                        if (newExpandedState.root !== true) {
                            newExpandedState.root = true;
                            changed = true;
                        }
                    } else {
                        // If root is not in the new tree (e.g., tree becomes empty)
                        // and 'root' was in the expanded state, we might clear it.
                        // However, other useEffects (e.g., on originalTree) often reset
                        // expandedNodeXPaths to {"root": true} when tree is empty or reloaded.
                        // To avoid conflicting logic, we can be conservative here.
                        // If root was true and is now gone, perhaps remove it from this state.
                        if (newExpandedState.hasOwnProperty('root')) {
                            delete newExpandedState.root; // Or set to false, depending on desired behavior for absent root.
                            changed = true;
                        }
                    }
                    // No other paths are pruned here. This fixes pagination issue.
                    return changed ? newExpandedState : prevExpandedPaths;
                });

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

                setIsWorkerProcessing(false); // Worker is now free

                // If there was a pending request while the worker was busy, process it now.
                if (pendingRequestRef.current) {
                    console.log("Processing pending request with latest props.");
                    // Directly call the processing logic again
                    setIsWorkerProcessing(true); // Mark as busy again for the new request
                    pendingRequestRef.current = false; // Reset pending flag
                    workerRef.current.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
                } else {
                    console.log("No pending requests, worker is idle.");
                }
            }
        };

        workerRef.current.onmessage = messageHandler;

        return () => {
            // Optional: Clean up worker message handler if component unmounts
            // dataTreeWorker.onmessage = null;
            // Consider terminating if worker is not shared: dataTreeWorker.terminate();
        };
    }, []); // Empty dependency array: setup message handler only once

    // Effect to scroll to newly added/duplicated item and manage glow timing
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
            }, 5000); // 5-second glow duration

            return () => {
                clearTimeout(scrollTimer);
                clearTimeout(glowClearTimer);
            };
        }
    }, [newlyAddedOrDuplicatedXPath, treeData, setNewlyAddedOrDuplicatedXPath]); // Dependencies

    // Handle page change for a paginated node
    const handlePageChange = useCallback((nodeId, direction, totalPagesForNode) => {
        setPaginatedNodes(prev => {
            const currentPage = prev[nodeId]?.page || 0;
            let newPage = currentPage;

            if (direction === 'next') {
                newPage = Math.min(currentPage + 1, totalPagesForNode - 1);
            } else if (direction === 'prev') {
                newPage = Math.max(currentPage - 1, 0);
            }

            return {
                ...prev,
                [nodeId]: { page: newPage }
            };
        });
        // paginatedNodes change will be caught by the main useEffect which updates latestPropsRef
        // and then triggers the worker communication useEffect.
    }, []);

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

    const handleFormUpdate = (xpath, dataxpath, value, validationRes = null) => {
        const updatedObj = cloneDeep(updatedData);
        set(updatedObj, dataxpath, value);
        if (onUpdate) onUpdate(updatedObj);
        if (onUserChange) onUserChange(xpath, value, validationRes, null);
        // updatedData change will be caught by the main useEffect which updates latestPropsRef
        // and then triggers the worker communication useEffect.
    };

    const handleNodeToggle = useCallback((nodeXPath, expand) => {
        setExpandedNodeXPaths(prev => ({
            ...prev,
            [nodeXPath]: expand
        }));
    }, []);

    const expandNodeAndAllChildren = useCallback((baseSchemaPathOfNewNode, newDataInstance, schemaOfNewNodeInstance, currentProjectSchema) => {
        const pathsToExpandRecursively = {};

        function discoverPaths(currentData, currentPathPrefix, currentSchemaDef) {
            // Allow null/undefined currentData to still discover structure if schema defines children
            // If currentData is primitive, no children to discover from it.
            if (!currentSchemaDef) return;

            const properties = currentSchemaDef.properties;
            if (!properties) return;

            for (const propName in properties) {
                const propSchema = properties[propName];
                if (!propSchema) continue;

                const childNodeSchemaPath = `${currentPathPrefix}.${propName}`;
                pathsToExpandRecursively[childNodeSchemaPath] = true; // Expand the child node itself

                // Determine childData, can be undefined if not present in currentData
                const childData = (currentData && typeof currentData === 'object' && currentData !== null) ? currentData[propName] : undefined;

                if (propSchema.type === DATA_TYPES.OBJECT) {
                    let subSchemaDefToRecurse = propSchema;
                    if (propSchema.items && propSchema.items.$ref) { // Object defined by $ref under items
                         const refParts = propSchema.items.$ref.split('/');
                         subSchemaDefToRecurse = refParts.length === 2 ? currentProjectSchema[refParts[1]] : currentProjectSchema[refParts[1]][refParts[2]];
                    }
                    // Only recurse if there's a schema definition for children
                    if ((subSchemaDefToRecurse && subSchemaDefToRecurse.properties) || (subSchemaDefToRecurse && subSchemaDefToRecurse.items && subSchemaDefToRecurse.items.$ref)) {
                        discoverPaths(childData, childNodeSchemaPath, subSchemaDefToRecurse);
                    }
                } else if (propSchema.type === DATA_TYPES.ARRAY && propSchema.items && propSchema.items.$ref) {
                    const itemRefParts = propSchema.items.$ref.split('/');
                    const itemSchemaDef = itemRefParts.length === 2 ? currentProjectSchema[itemRefParts[1]] : currentProjectSchema[itemRefParts[1]][itemRefParts[2]];
                    
                    if (Array.isArray(childData)) {
                        childData.forEach((itemData, index) => {
                            const itemSchemaPath = `${childNodeSchemaPath}[${index}]`;
                            pathsToExpandRecursively[itemSchemaPath] = true;
                            discoverPaths(itemData, itemSchemaPath, itemSchemaDef);
                        });
                    }
                    // Even if array is empty, its container (childNodeSchemaPath) is marked.
                }
            }
        }

        // Start discovery from the children of the new node.
        discoverPaths(newDataInstance, baseSchemaPathOfNewNode, schemaOfNewNodeInstance);
        
        setExpandedNodeXPaths(prevExpanded => ({
            ...prevExpanded,
            [baseSchemaPathOfNewNode]: true, // Ensure the base node itself is expanded
            ...pathsToExpandRecursively
        }));
    }, [setExpandedNodeXPaths, projectSchema, DATA_TYPES]); // projectSchema and DATA_TYPES are dependencies

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
                    console.log('[DataTree] Attempting OBJECT INITIALIZATION for:', xpathAttr, 'Node:', originalNode);
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
                        console.log('[DataTree] Container own props for GOS:', containerOwnProps);

                        let newObjectInstance = generateObjectFromSchema(
                            projectSchema,
                            cloneDeep(itemSchemaForObject),
                            containerOwnProps,
                            xpathAttr
                        );
                        console.log('[DataTree] New object instance from GOS:', newObjectInstance);

                        set(updatedObj, xpathAttr, newObjectInstance);
                        console.log('[DataTree] Data after setting new object:', updatedObj);

                        setItemVisualStates(prev => ({ ...prev, [xpathAttr]: 'added' }));
                        expandNodeAndAllChildren(xpathAttr, newObjectInstance, itemSchemaForObject, projectSchema);
                        onUpdate(updatedObj, 'add');
                        setNewlyAddedOrDuplicatedXPath(xpathAttr); // Scroll to the initialized object
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
                    const totalItems = currentArray.length;
                    const newItemPageIndex = Math.floor((totalItems - 1) / ITEMS_PER_PAGE);
                    setPaginatedNodes(prev => ({ ...prev, [xpathAttr]: { page: newItemPageIndex } }));
                    onUpdate(updatedObj, 'add');
                    setNewlyAddedOrDuplicatedXPath(schemaXpathForNewItem); // Scroll to the new array item
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


                if (duplicatedObject.sec_positions && Array.isArray(duplicatedObject.sec_positions)) {
                    duplicatedObject.sec_positions.forEach(secPos => {
                        if (secPos && (secPos.positions === undefined || secPos.positions === null)) {
                            secPos.positions = [];
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
                return; // Action handled
            }

            if (clickedRemove) {
                e.stopPropagation();
                const xpathAttr = clickedRemove.getAttribute('data-remove'); // Schema path of the item/object to remove

                // Handle removal of an object (setting it to null)
                if (originalNode.isObjectContainer && !xpathAttr.endsWith(']')) {
                    let updatedObj = cloneDeep(updatedData);
                    set(updatedObj, xpathAttr, null); // Set the object to null

                    // Clear visual states and expansion for the nulled object and its potential children
                    setItemVisualStates(prev => {
                        const newState = { ...prev };
                        delete newState[xpathAttr];
                        Object.keys(newState).forEach(key => {
                            if (key && key.startsWith(xpathAttr + '.')) delete newState[key];
                        });
                        return newState;
                    });
                    setExpandedNodeXPaths(prevExpandedPaths => {
                        const newExpandedPaths = { ...prevExpandedPaths };
                        let changed = false;
                        for (const key in newExpandedPaths) {
                            if (key === xpathAttr || key.startsWith(xpathAttr + '.')) {
                                delete newExpandedPaths[key];
                                changed = true;
                            }
                        }
                        // Keep root expanded
                        if (!newExpandedPaths["root"] && expandedNodeXPaths["root"]) newExpandedPaths["root"] = true;
                        return changed ? newExpandedPaths : prevExpandedPaths;
                    });

                    onUpdate(updatedObj, 'remove'); // 'remove' might signify data changed to null
                    return; // Action handled
                }
                // Handle removal of an array item (existing logic)
                else if (xpathAttr && xpathAttr.endsWith(']')) {
                    let updatedObj = cloneDeep(updatedData);
                    let itemDataPath = getDataxpath(updatedObj, xpathAttr); // Get data path for the array item
                    if (!itemDataPath) return; // Should not happen if UI shows remove for a valid item

                    let arrayItemIndex = parseInt(itemDataPath.substring(itemDataPath.lastIndexOf('[') + 1, itemDataPath.lastIndexOf(']')));
                    let parentArrayDataPath = itemDataPath.substring(0, itemDataPath.lastIndexOf('['));
                    let parentArrayObject = get(updatedObj, parentArrayDataPath);

                    if (parentArrayObject && typeof parentArrayObject.splice === 'function') {
                        parentArrayObject.splice(arrayItemIndex, 1);
                        // Clear visual states and expansion for the removed item and its children
                        setItemVisualStates(prev => {
                            const newState = { ...prev };
                            delete newState[xpathAttr]; // xpathAttr is the schema path of the removed item
                            Object.keys(newState).forEach(key => {
                                if (key && key.startsWith(xpathAttr + '.') || key.startsWith(xpathAttr + '[')) delete newState[key];
                            });
                            return newState;
                        });
                        setExpandedNodeXPaths(prevExpandedPaths => {
                            const newExpandedPaths = { ...prevExpandedPaths };
                            let changed = false;
                            for (const key in newExpandedPaths) {
                                if (key === xpathAttr || key.startsWith(xpathAttr + '.') || key.startsWith(xpathAttr + '[')) {
                                    delete newExpandedPaths[key];
                                    changed = true;
                                }
                            }
                            if (!newExpandedPaths["root"] && expandedNodeXPaths["root"]) newExpandedPaths["root"] = true;
                            return changed ? newExpandedPaths : prevExpandedPaths;
                        });
                        onUpdate(updatedObj, 'remove');
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
            if (explicitState === true) { // Explicitly expanded by user or previous default
                nodeIsOpen = true;
            } else if (explicitState === false) { // Explicitly collapsed by user
                nodeIsOpen = false;
            } else { // No explicit state (undefined)
                // Use levelRef.current for the comparison
                // Only expand if it's a container and within the default expansion level
                if (level <= levelRef.current && (originalNode?.isObjectContainer || originalNode?.isArrayContainer)) { 
                    nodeIsOpen = true;
                    isChanged = true; // Mark to persist this default decision
                }
                // else, if level > levelRef.current or not a container, and no explicit state, nodeIsOpen remains false (default collapsed)
            }
        } else {
            // Node does NOT have an XPath: apply no-XPath-based default level
            // Cannot have an explicit state in expandedNodeXPaths as it's keyed by XPath.
            // This default decision cannot be persisted in expandedNodeXPaths.
            //   if (level <= 2) { // Default expansion for nodes WITHOUT XPath up to level 2
            //       nodeIsOpen = true;
            //   }
            // isChanged remains false, as we can't persist state without an XPath key.
            // else, if level > 2, nodeIsOpen remains false (default collapsed)
            console.error('something went wrong. nodexpath found null' + xpath);
        }

        // This part is existing: if a default expansion was made FOR A NODE WITH AN XPATH, persist it.
        // isChanged will only be true if nodeXPath was defined and a default expansion (level <=3) was applied.
        if (isChanged) {
            handleNodeToggle(nodeXPath, true);
        }

        // Glow logic added here
        const shouldGlow = newlyAddedOrDuplicatedXPath && newlyAddedOrDuplicatedXPath === nodeXPath;

        const dataPayload = {
            ...originalNode,
            isOpen: nodeIsOpen,
            onTextChange: handleTextChange,
            onSelectItemChange: handleSelectItemChange,
            onCheckboxChange: handleCheckboxToggle,
            onAutocompleteOptionChange: handleAutocompleteChange,
            onDateTimeChange: handleDateTimeChange,
            updatedDataForColor: updatedData,
            storedDataForColor: storedData,
            visualState: visualState,
            // triggerGlowForXPath: newlyAddedOrDuplicatedXPath // This prop is now removed as HeaderField won't use it
        };

        if (originalNode.pagination) {
            dataPayload.pagination = {
                ...originalNode.pagination,
                onPageChange: (direction) => handlePageChange(element.id, direction, originalNode.pagination.totalPages)
            };
        }

        const commonProps = {
            data: dataPayload,
            isOpen: nodeIsOpen,
            updatedDataForColor: updatedData,
            storedDataForColor: storedData,
            visualState: visualState,
            // triggerGlowForXPath: newlyAddedOrDuplicatedXPath // This prop can be conditionally removed or 
        };
        
        // If HeaderField no longer needs triggerGlowForXPath, this prop can be conditionally removed or 
        // HeaderField can be updated to not expect it. For now, let's assume it might still be there
        // or will be cleaned up in the next step when editing HeaderField.jsx.

        return (
            <div
                {...nodeProps}
                style={{ paddingLeft: `${(level - 1) * 20}px`, width: 'max-content' }}
                className={shouldGlow ? NodeBaseClasses.datanodeNewlyAddedGlowTarget : ''} // Apply new glow target class
                data-xpath={nodeXPath} // Ensure data-xpath is on the outermost div for scrolling
            >
                <ComponentToRender {...commonProps} onClick={handleClick} />
            </div>
        );
    };

    const calculatedDefaultExpandedIds = React.useMemo(() => {
        // This is now less critical as we manage expansion in `expandedNodeXPaths` state.
        // We can use it to set the initial state of `expandedNodeXPaths`.
        const ids = ["root"];
        if (originalTree && originalTree.length > 0) {
            const firstActualNode = originalTree[0];
            if (firstActualNode && firstActualNode.xpath) {
                ids.push(firstActualNode.xpath);
            }
        }
        // Convert array of xpaths to an object for expandedNodeXPaths state
        const initialExpanded = {};
        ids.forEach(id => initialExpanded[id] = true);
        // We need to set the state here or ensure `expandedNodeXPaths` is initialized with this.
        // However, this useMemo runs on originalTree changes, which might be too late or cause loops if we set state here.
        // Better to initialize expandedNodeXPaths in its useState or a useEffect that runs once.
        return ids; // This is for TreeView's defaultExpandedIds, which we might not heavily rely on anymore.
    }, [originalTree]);

    // Effect to initialize/update expandedNodeXPaths
    useEffect(() => {
        if (originalTree && originalTree.length > 0) {
            if (!initialExpansionSetForCurrentTreeRef.current) {
                const firstActualNode = originalTree[0];
                if (firstActualNode && firstActualNode.xpath) {
                    setExpandedNodeXPaths(prevExpandedPaths => ({
                        ...prevExpandedPaths,
                        "root": true, // Ensure root is always true
                        [firstActualNode.xpath]: true // Expand the first actual node
                    }));
                } else {
                    // First node might not have an xpath or originalTree[0] is null/undefined
                    setExpandedNodeXPaths(prevExpandedPaths => ({
                        ...prevExpandedPaths,
                        "root": true
                    }));
                }
                initialExpansionSetForCurrentTreeRef.current = true;
            } else {
                // Initial expansion already done for this tree instance, ensure "root" is still set
                // This helps if something else inadvertently removes "root" from expandedNodeXPaths
                setExpandedNodeXPaths(prevExpandedPaths => {
                    if (prevExpandedPaths.root !== true) {
                        return { ...prevExpandedPaths, "root": true }
                    }
                    return prevExpandedPaths;
                });
            }
        } else if (!originalTree || originalTree.length === 0) {
            // Tree is empty or not yet loaded, reset the flag
            initialExpansionSetForCurrentTreeRef.current = false;
            // Ensure "root" is still in the base state for when tree loads
            setExpandedNodeXPaths(prevPaths => { // Changed to functional update
                if (Object.keys(prevPaths).length === 1 && prevPaths.root === true) return prevPaths; // Already minimal state
                return { "root": true }; // Reset to just root expanded if tree is empty
            });
        }
    }, [originalTree]);

    if (!treeData || treeData.length === 0) return null;

    const activeNodeIdsSet = new Set(treeData.map((node) => node.id));
    const updatedExpandedIds = Object.keys(expandedNodeXPaths)
        .filter(xpath => expandedNodeXPaths[xpath] && activeNodeIdsSet.has(xpath));

    return (
        <TreeView
            key={counter}
            data={treeData}
            aria-label={modelName}
            nodeRenderer={nodeRenderer}
            expandedIds={updatedExpandedIds} // Control TreeView expansion
            multiSelect={false}
            disableKeyboardNavigation={false}
        />
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
    filters: PropTypes.array
};

DataTree.defaultProps = {
    selectedId: null,
    showHidden: false,
    enableObjectPagination: false,
    treeLevel: null,
    filters: []
};

export default DataTree;