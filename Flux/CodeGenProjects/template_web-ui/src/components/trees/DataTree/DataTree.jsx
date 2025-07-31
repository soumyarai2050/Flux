import React, { useState, useEffect, useCallback, useRef } from 'react';
import TreeView from 'react-accessible-treeview';
import { cloneDeep, get, set } from 'lodash';
import { BeatLoader } from 'react-spinners';
import { AnimatePresence } from 'framer-motion';
import { generateObjectFromSchema } from '../../../utils/core/schemaUtils';
import { addxpath, getDataxpath, getDataxpathById, clearxpath } from '../../../utils/core/dataAccess';
import { clearId } from '../../../utils/core/objectUtils';
import { DATA_TYPES, ITEMS_PER_PAGE } from '../../../constants';
import { xpathCacheManager } from '../../../cache/xpathCache';
import Node from '../../Node';
import HeaderField from '../../HeaderField';
import NodeBaseClasses from '../../Node.module.css';
import useTreeExpansion from '../../../hooks/useTreeExpansion'; // Import our custom hook
import useTreeAnimations from '../../../hooks/useTreeAnimations'; // Import our animation hook
import ProgressOverlay from '../../ProgressOverlay'; // Import the centralized progress overlay
import PropTypes from 'prop-types';
import TreeRenderer from '../TreeRenderer/TreeRenderer';


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
    enableQuickFilterPin = false,
    disablePagination = false
}) => {
    const [treeData, setTreeData] = useState([]);
    const [originalTree, setOriginalTree] = useState([]);
    const [paginatedNodes, setPaginatedNodes] = useState({});
    const [itemVisualStates, setItemVisualStates] = useState({});
    const [newlyAddedOrDuplicatedXPath, setNewlyAddedOrDuplicatedXPath] = useState(null); // Track the single node that should glow
    const [isWorkerProcessing, setIsWorkerProcessing] = useState(false);
    const [counter, setCounter] = useState(0);
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
    } = useTreeExpansion(projectSchema, updatedData, storedData, newlyAddedOrDuplicatedXPath);

    // Use our custom hook for animation management
    const {
        animatedNodeToggle,
        isNodeAnimating,
        getNodeTargetState,
        getNodeAnimationProps,
        batchAnimatedToggle,
        animatingNodes,
    } = useTreeAnimations(expandedNodeXPaths, handleNodeToggle);

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
            quickFilter, pinnedFilters: cleanPinnedFilters,
            disablePagination
        };
    }, [
        projectSchema, modelName, updatedData, storedData, subtree, mode, xpath,
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters, quickFilter, pinnedFilters, disablePagination
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
        selectedId, showHidden, paginatedNodes, enableObjectPagination, filters, quickFilter, pinnedFilters, disablePagination
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
            const { type, payload } = event.data;

            if (type === 'TREE_GENERATED' || type === 'TREE_GENERATION_FAILED') {
                setIsWorkerProcessing(false); // Stop loader for both success and handled failure cases
            }

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
                    workerRef.current.postMessage({ type: 'PROCESS_TREE', payload: latestPropsRef.current });
                    // Keep isWorkerProcessing as true since we're immediately processing another request
                } else {
                    setIsWorkerProcessing(false); // Worker is now free
                }
            } else if (type === 'SUBTREE_GENERATED') {
                const { subtree, nodeId } = payload;
                if (subtree && subtree.length > 0 && nodeId) {
                    // ... existing code ...
                }
            }
        };

        workerRef.current.onmessage = messageHandler;

        // Cleanup function for when the component unmounts
        return () => {
            if (workerRef.current) {
                workerRef.current.onmessage = null;
            }
        };
    }, []);

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
        // Get the value from the element, which is derived from updatedData
        const value = element.value;

        // Get the corresponding storedValue from the original storedData prop
        const storedValue = get(storedData, element.dataxpath);

        const nodeData = {
            ...element,
            value: value,
            storedValue: storedValue, // Add the storedValue to the node's props
            // ... (other props)
        };

        return (
            <TreeRenderer
                element={element}
                isBranch={isBranch}
                isExpanded={isExpanded}
                getNodeProps={getNodeProps}
                level={level}
                handleExpand={handleExpand}
                itemVisualStates={itemVisualStates}
                expandedNodeXPaths={expandedNodeXPaths}
                levelRef={levelRef}
                treeData={treeData}
                handleNodeToggle={animatedNodeToggle}
                handleTextChange={handleTextChange}
                handleSelectItemChange={handleSelectItemChange}
                handleCheckboxToggle={handleCheckboxToggle}
                handleAutocompleteChange={handleAutocompleteChange}
                handleDateTimeChange={handleDateTimeChange}
                onQuickFilterChange={onQuickFilterChange}
                onQuickFilterPin={onQuickFilterPin}
                onQuickFilterUnpin={onQuickFilterUnpin}
                pinnedFilters={pinnedFilters}
                updatedData={updatedData}
                storedData={storedData}
                projectSchema={projectSchema}
                handleExpandAll={handleExpandAll}
                handleCollapseAll={handleCollapseAll}
                enableQuickFilterPin={enableQuickFilterPin}
                handlePageChange={handlePageChange}
                setPaginatedNodes={setPaginatedNodes}
                needsFullRegenerationRef={needsFullRegenerationRef}
                expandNodeAndAllChildren={expandNodeAndAllChildren}
                onUpdate={onUpdate}
                setItemVisualStates={setItemVisualStates}
                setCounter={setCounter}
                isNodeAnimating={isNodeAnimating}
                getNodeTargetState={getNodeTargetState}
                getNodeAnimationProps={getNodeAnimationProps}
                animatingNodes={animatingNodes}
                originalHandleNodeToggle={handleNodeToggle}
                newlyAddedOrDuplicatedXPath={newlyAddedOrDuplicatedXPath}
                setNewlyAddedOrDuplicatedXPath={setNewlyAddedOrDuplicatedXPath}
            />
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

    // Auto-clear glow effect with timer
    useEffect(() => {
        // If a node is marked for glowing...
        if (newlyAddedOrDuplicatedXPath) {
            // Set a timer to turn off the glow after 3 seconds
            const glowClearTimer = setTimeout(() => {
                setNewlyAddedOrDuplicatedXPath(null); // Resetting state removes the glow on re-render
            }, 3000); // 3-second glow duration

            // Cleanup function to clear the timer if the component unmounts or the state changes again
            return () => {
                clearTimeout(glowClearTimer);
            };
        }
    }, [newlyAddedOrDuplicatedXPath]); // This effect runs only when the glow target changes

    // Auto-scroll to newly added node - moved to DataTree to avoid Framer Motion conflicts
    useEffect(() => {
        if (newlyAddedOrDuplicatedXPath) {
            // Function to find the best element to scroll to
            const findScrollTarget = () => {
                // First try to find the animated-tree-node
                const animatedNode = document.querySelector(`[data-xpath="${newlyAddedOrDuplicatedXPath}"]`);

                if (animatedNode) {
                    // Check if it's fully rendered (not mid-animation)
                    const computedStyle = window.getComputedStyle(animatedNode);
                    const opacity = parseFloat(computedStyle.opacity);

                    if (opacity >= 0.9) { // Fully visible
                        // Find the parent li.tree-branch-wrapper for better scroll target
                        const parentLi = animatedNode.closest('.tree-branch-wrapper') ||
                            animatedNode.closest('.tree-leaf-list-item');
                        return parentLi || animatedNode;
                    }
                }
                return null;
            };

            // Attempt to scroll with retries
            const attemptScroll = (attempt = 1, maxAttempts = 5) => {
                const targetElement = findScrollTarget();

                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center', // Scroll to center of the viewport
                        inline: 'nearest'
                    });
                } else if (attempt < maxAttempts) {
                    setTimeout(() => {
                        attemptScroll(attempt + 1, maxAttempts);
                    }, 300);
                }
            };

            // Start the scroll attempt after initial delay
            const scrollTimer = setTimeout(() => {
                attemptScroll();
            }, 800); // Longer initial delay for Framer Motion animations

            return () => clearTimeout(scrollTimer);
        }
    }, [newlyAddedOrDuplicatedXPath]);

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
                <AnimatePresence mode="wait">
                    <div className={`tree-view-container ${needsFullRegenerationRef.current ? 'no-animation' : ''}`}>
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
                </AnimatePresence>
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
    enableQuickFilterPin: PropTypes.bool,
    disablePagination: PropTypes.bool
};

DataTree.defaultProps = {
    selectedId: null,
    showHidden: false,
    enableObjectPagination: false,
    treeLevel: null,
    filters: [],
    isDisabled: false,
    enableQuickFilterPin: false,
    disablePagination: false
};

export default DataTree;