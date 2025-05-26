import React, { useState, useEffect, useCallback, useRef } from 'react';
import TreeView from 'react-accessible-treeview';
import { cloneDeep, get, set } from 'lodash';
import { generateObjectFromSchema, addxpath, getDataxpath, /* setTreeState, */ clearxpath, clearId } from '../../../utils'; // Comment out setTreeState
import { DATA_TYPES, ITEMS_PER_PAGE } from '../../../constants';
import Node from '../../Node';
import HeaderField from '../../HeaderField';

// Worker instantiation
let dataTreeWorker;
if (typeof Worker !== 'undefined') {
    dataTreeWorker = new Worker(new URL('../../../workers/dataTree.worker.js', import.meta.url), { type: 'module' });
}
//

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
    showHidden
}) => {
    const [treeData, setTreeData] = useState([]);
    const [originalTree, setOriginalTree] = useState([]);
    const [paginatedNodes, setPaginatedNodes] = useState({});
    const [itemVisualStates, setItemVisualStates] = useState({});
    const [isWorkerProcessing, setIsWorkerProcessing] = useState(false);
    const [expandedNodeXPaths, setExpandedNodeXPaths] = useState({ "root": true }); // Initialize with "root": true
    const initialExpansionSetForCurrentTreeRef = useRef(false); // Ref to track initial expansion

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
            ITEMS_PER_PAGE, DATA_TYPES
            // expandedNodeXPaths is managed locally, no need to send to worker for basic tree generation
        };
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes
    ]);

    // Main effect to communicate with the worker when props change.
    useEffect(() => {
        if (!dataTreeWorker) return;

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
            dataTreeWorker.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
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
        selectedId, showHidden, paginatedNodes // Key data props that should trigger processing
    ]);

    // Effect to update previous prop refs *after* all other effects for the render cycle.
    useEffect(() => {
        prevUpdatedDataRef.current = updatedData;
        prevStoredDataRef.current = storedData;
    }); // Runs after every render

    // Setup worker message handler once on component mount
    useEffect(() => {
        if (!dataTreeWorker) return;

        const messageHandler = (event) => {
            const { type, payload } = event.data;
            if (type === 'TREE_GENERATED') {
                console.log("Worker response received:", payload);
                setOriginalTree(payload.originalTree || []);
                const newTreeData = payload.treeData || [];
                setTreeData(newTreeData);

                // Prune expandedNodeXPaths to only include xpaths present in the newTreeData
                const validNodeIds = new Set(newTreeData.map(node => node.id));
                setExpandedNodeXPaths(prevExpandedPaths => {
                    const newExpandedPaths = {};
                    let changed = false;
                    for (const xpathKey in prevExpandedPaths) {
                        if (validNodeIds.has(xpathKey) && prevExpandedPaths[xpathKey]) {
                            newExpandedPaths[xpathKey] = true;
                        } else {
                            changed = true; // Indicates an xpath was removed
                        }
                    }
                    // Ensure root is always expanded if it exists (it should always be in newTreeData if data is present)
                    if (validNodeIds.has("root")) {
                        if (!newExpandedPaths["root"]) {
                            newExpandedPaths["root"] = true;
                            changed = true;
                        }
                    } else if (Object.keys(newExpandedPaths).length > 0) {
                        // This case should ideally not happen if treeData always has a root when it's not empty.
                        // If root is missing but other nodes are expanded, it's an inconsistent state.
                        // For safety, clear expansions if root is gone but other expansions exist.
                        // Or, ensure 'root' is always added by the worker if there's any data.
                        // Based on current worker logic, root is always present.
                    }

                    return changed || Object.keys(prevExpandedPaths).length !== Object.keys(newExpandedPaths).length 
                           ? newExpandedPaths 
                           : prevExpandedPaths;
                });

                // Prune itemVisualStates to only include xpaths present in the newTreeData
                setItemVisualStates(prevStates => {
                    const nextStates = {};
                    let changed = false;
                    for (const xpathKey in prevStates) {
                        if (validNodeIds.has(xpathKey)) {
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
                    dataTreeWorker.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
                } else {
                    console.log("No pending requests, worker is idle.");
                }
            }
        };

        dataTreeWorker.onmessage = messageHandler;

        return () => {
            // Optional: Clean up worker message handler if component unmounts
            // dataTreeWorker.onmessage = null;
            // Consider terminating if worker is not shared: dataTreeWorker.terminate();
        };
    }, []); // Empty dependency array: setup message handler only once


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
    }, [onUpdate,onUserChange]);

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

    const nodeRenderer = ({ element, isBranch, isExpanded, getNodeProps, level, handleExpand }) => {
        if (element.id === "root") return null;

        const nodeProps = getNodeProps();
        const originalNode = element.metadata;
        const visualState = itemVisualStates[originalNode?.xpath];

        if (!originalNode) {
            console.warn("Node metadata is missing for element:", element);
            return <div {...nodeProps} style={{ paddingLeft: `${(level - 1) * 20}px` }}>Loading...</div>;
        }

        const Component = originalNode.children && Array.isArray(originalNode.children) && originalNode.children.length > 0 ? HeaderField : Node;

        const handleClick = (e) => {
            const nodeXPath = originalNode?.xpath;
            if (!nodeXPath) return; // Should not happen if originalNode is valid

            // Determine what was clicked using data attributes by checking e.target and its parents
            const clickedArrow = e.target.closest('[data-open], [data-close]');
            const clickedTitle = e.target.closest('[data-header-title="true"]');
            const clickedAdd = e.target.closest('[data-add]');
            const clickedDuplicate = e.target.closest('[data-duplicate]');
            const clickedRemove = e.target.closest('[data-remove]');

            if (clickedArrow) {
                e.stopPropagation();
                if (clickedArrow.hasAttribute('data-open')) {
                    handleNodeToggle(nodeXPath, true);
                } else if (clickedArrow.hasAttribute('data-close')) {
                    handleNodeToggle(nodeXPath, false);
                }
                return;
            }

            if (clickedTitle) {
                e.stopPropagation();
                if (isBranch) {
                    handleNodeToggle(nodeXPath, !expandedNodeXPaths[nodeXPath]);
                }
                return;
            }

            // Handle Action Clicks (add, duplicate, remove)
            // These actions should have their own specific data attributes on the clickable elements (e.g., IconButton in HeaderOptions)
            if (clickedAdd) {
                e.stopPropagation();
                const xpathAttr = clickedAdd.getAttribute('data-add');
                const ref = clickedAdd.getAttribute('data-ref');
                const additionalPropsStr = clickedAdd.getAttribute('data-prop');
                if (!xpathAttr || xpathAttr.endsWith(']')) return; 
                
                let updatedObj = cloneDeep(updatedData);
                let containerXpath = getDataxpath(updatedObj, xpathAttr);
                let additionalProps = additionalPropsStr ? JSON.parse(additionalPropsStr) : {};

                if (!containerXpath) {
                    set(updatedObj, xpathAttr, []);
                    containerXpath = xpathAttr;
                }
                let parentObject = get(updatedObj, containerXpath);
                if (!parentObject || !Array.isArray(parentObject)) {
                    set(updatedObj, containerXpath, []);
                    parentObject = get(updatedObj, containerXpath);
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
                const itemsInStoredData = get(storedData, xpathAttr);
                let maxIndexInStoredData = -1;
                if (Array.isArray(itemsInStoredData)) {
                    maxIndexInStoredData = itemsInStoredData.length > 0 ? itemsInStoredData.length - 1 : -1;
                }
                let nextIndex = Math.max(maxIndexInUpdatedData, maxIndexInStoredData) + 1;

                if ([DATA_TYPES.NUMBER, DATA_TYPES.STRING].includes(ref)) {
                    parentObject.push(null);
                } else {
                    const refParts = ref.split('/');
                    let currentItemSchema = refParts.length === 2 ? projectSchema[refParts[1]] : projectSchema[refParts[1]][refParts[2]];
                    if (currentItemSchema.hasOwnProperty('enum') && Object.keys(currentItemSchema).length === 1) {
                        parentObject.push(currentItemSchema.enum[0]);
                    } else {
                        let emptyObject = generateObjectFromSchema(projectSchema, cloneDeep(currentItemSchema), additionalProps);
                        emptyObject = addxpath(emptyObject, containerXpath + '[' + nextIndex + ']');
                        const schemaXpathForNewItem = xpathAttr + '[' + nextIndex + ']'; 
                        setItemVisualStates(prev => ({ ...prev, [schemaXpathForNewItem]: 'added' }));
                        parentObject.push(emptyObject);
                        handleNodeToggle(containerXpath, true); // Expand parent
                        const totalItems = parentObject.length; 
                        const newItemPageIndex = Math.floor((totalItems - 1) / ITEMS_PER_PAGE);
                        setPaginatedNodes(prev => ({ ...prev, [containerXpath]: { page: newItemPageIndex } }));
                    }
                }
                onUpdate(updatedObj, 'add');
                return;
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

                // Post-processing: Ensure nested 'positions' arrays within sec_positions are initialized as empty arrays.
                // This guarantees consistency with newly added items, even if generateObjectFromSchema or overrides resulted in null/undefined.
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
                handleNodeToggle(parentDataXpath, true); // Expand parent
                const totalItems = parentObject.length;
                const newItemPageIndex = Math.floor((totalItems - 1) / ITEMS_PER_PAGE);
                setPaginatedNodes(prev => ({ ...prev, [parentDataXpath]: { page: newItemPageIndex } }));
                onUpdate(updatedObj, 'add'); 
                return;
            }

            if (clickedRemove) {
                e.stopPropagation();
                const xpathAttr = clickedRemove.getAttribute('data-remove');
                if (!xpathAttr || !xpathAttr.endsWith(']')) return;

                let updatedObj = cloneDeep(updatedData);
                let itemXpath = getDataxpath(updatedObj, xpathAttr);
                if (!itemXpath) return;

                let index = parseInt(itemXpath.substring(itemXpath.lastIndexOf('[') + 1, itemXpath.lastIndexOf(']')));
                let parentXpath = itemXpath.substring(0, itemXpath.lastIndexOf('['));
                let parentObject = get(updatedObj, parentXpath);

                if (parentObject && typeof parentObject.splice === 'function') {
                    parentObject.splice(index, 1);
                    setItemVisualStates(prev => {
                        const newState = { ...prev };
                        delete newState[xpathAttr];
                        Object.keys(newState).forEach(key => {
                            if (key && key.startsWith(xpathAttr)) delete newState[key];
                        });
                        return newState;
                    });
                    setExpandedNodeXPaths(prevExpandedPaths => {
                        const newExpandedPaths = { ...prevExpandedPaths };
                        let changed = false;
                        for (const key in newExpandedPaths) {
                            if (key === xpathAttr || key.startsWith(xpathAttr + '[') || key.startsWith(xpathAttr + '.')) {
                                delete newExpandedPaths[key];
                                changed = true;
                            }
                        }
                        return changed ? newExpandedPaths : prevExpandedPaths;
                    });
                    onUpdate(updatedObj, 'remove');
                }
                return;
            }
            
            // If no specific interactive element was clicked, do nothing.
            // This prevents clicks on padding or background from toggling the node.
        };

        const nodeIsOpen = !!expandedNodeXPaths[originalNode?.xpath];

        const dataPayload = {
            ...originalNode,
            isOpen: nodeIsOpen,
            onTextChange: handleTextChange,
            onSelectItemChange: handleSelectItemChange,
            onCheckboxChange: handleCheckboxToggle,
            onAutocompleteOptionChange: handleAutocompleteChange,
            onDateTimeChange: handleDateTimeChange,
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
            visualState: visualState
        };

        return (
            <div 
                {...nodeProps} 
                style={{ paddingLeft: `${(level - 1) * 20}px` }}
                onClick={handleClick}
            >
                <Component {...commonProps} />
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
                setExpandedNodeXPaths(prevExpandedPaths => ({
                    ...prevExpandedPaths,
                    "root": true
                }));
            }
        } else if (!originalTree || originalTree.length === 0) {
            // Tree is empty or not yet loaded, reset the flag
            initialExpansionSetForCurrentTreeRef.current = false;
            // Ensure "root" is still in the base state for when tree loads
            setExpandedNodeXPaths({ "root": true });
        }
    }, [originalTree]);

    return treeData.length > 0 ? (
        <TreeView
            data={treeData}
            aria-label={modelName}
            nodeRenderer={nodeRenderer}
            expandedIds={Object.keys(expandedNodeXPaths).filter(xpath => expandedNodeXPaths[xpath])} // Control TreeView expansion
            multiSelect={false}
            disableKeyboardNavigation={false}
        />
    ) : null;
};

export default DataTree;