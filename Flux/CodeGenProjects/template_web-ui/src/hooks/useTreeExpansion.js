import { useState, useCallback, useRef } from 'react';
import { get } from 'lodash';
import { DATA_TYPES } from '../constants';

/**
 * Custom hook for managing tree expansion state and operations
 * This separates all expansion logic from the main DataTree component
 */
const useTreeExpansion = (projectSchema, updatedData, storedData, newlyAddedOrDuplicatedXPath = null) => {
    // State for tracking which nodes are expanded
    const [expandedNodeXPaths, setExpandedNodeXPaths] = useState({ "root": true });

    // State for batched expansion
    const [isExpanding, setIsExpanding] = useState(false);
    const [expansionProgress, setExpansionProgress] = useState({ current: 0, total: 0 });
    const [expandingNodePath, setExpandingNodePath] = useState(''); // Track which node is being expanded

    // Ref to track if initial expansion has been set for current tree
    const initialExpansionSetForCurrentTreeRef = useRef(false);

    // Ref to track expansion cancellation
    const expansionCancelledRef = useRef(false);

    /**
     * Toggle expansion state of a single node
     * Also handles parent/child relationship consistency
     */
    const handleNodeToggle = useCallback((nodeXPath, expand) => {
        setExpandedNodeXPaths(prev => {
            const newState = { ...prev };

            if (expand) {
                // When expanding, ensure all parent paths are also expanded
                const parentPaths = [];
                let currentPath = '';
                let i = 0;

                while (i < nodeXPath.length) {
                    const char = nodeXPath[i];
                    currentPath += char;

                    // When we hit a dot or opening bracket, the current path (minus the delimiter) is a parent
                    if (char === '.' || char === '[') {
                        const parentPath = currentPath.slice(0, -1); // Remove the delimiter
                        if (parentPath && parentPath !== 'root' && !parentPaths.includes(parentPath)) {
                            parentPaths.push(parentPath);
                        }
                    }
                    // When we hit a closing bracket, the current path is a complete array element parent
                    else if (char === ']') {
                        if (currentPath && currentPath !== 'root' && !parentPaths.includes(currentPath)) {
                            parentPaths.push(currentPath);
                        }
                    }

                    i++;
                }

                // Expand all parent paths
                parentPaths.forEach(parentPath => {
                    newState[parentPath] = true;
                });

                // Expand the target node
                newState[nodeXPath] = true;
            } else {
                // When collapsing, only collapse THIS node
                // Children keep expansion memory but won't show due to hierarchical filtering
                newState[nodeXPath] = false;
            }

            return newState;
        });
    }, []);

    /**
     * Chunked expand all - expands nodes in batches to keep UI responsive
     */
    const handleExpandAll = useCallback(async (nodeXPath, treeData, chunkSize = 15) => {
        if (isExpanding) {
            // Cancel current expansion if already running
            expansionCancelledRef.current = true;
            return;
        }

        setIsExpanding(true);
        setExpandingNodePath(nodeXPath);
        expansionCancelledRef.current = false;

        try {
            // Find all child nodes that need to be expanded
            const findChildNodes = (parentXPath, nodes = treeData) => {
                const children = [];

                nodes.forEach(node => {
                    const nodeId = node.id;
                    // Check if this node is a child of the parent we're expanding
                    if (nodeId.startsWith(parentXPath + '.') || nodeId.startsWith(parentXPath + '[')) {
                        children.push(nodeId);
                    }
                });

                return children;
            };

            const allChildNodes = findChildNodes(nodeXPath);
            const totalNodes = allChildNodes.length + 1; // +1 for parent

            setExpansionProgress({ current: 0, total: totalNodes });

            // First expand the parent node
            setExpandedNodeXPaths(prev => ({ ...prev, [nodeXPath]: true }));
            setExpansionProgress(prev => ({ ...prev, current: 1 }));

            // Give the browser time to render the parent
            await new Promise(resolve => setTimeout(resolve, 50));

            // Expand children in chunks
            for (let i = 0; i < allChildNodes.length; i += chunkSize) {
                // Check if expansion was cancelled
                if (expansionCancelledRef.current) {
                    break;
                }

                const chunk = allChildNodes.slice(i, i + chunkSize);

                // Expand this chunk of nodes
                setExpandedNodeXPaths(prev => {
                    const newState = { ...prev };
                    chunk.forEach(childXPath => {
                        newState[childXPath] = true;
                    });
                    return newState;
                });

                // Update progress
                setExpansionProgress(prev => ({
                    ...prev,
                    current: Math.min(prev.current + chunk.length, totalNodes)
                }));

                // Give the browser time to render this chunk
                // Use requestAnimationFrame for smooth animation
                await new Promise(resolve => requestAnimationFrame(() => {
                    setTimeout(resolve, 16); // ~60fps
                }));
            }

        } finally {
            setIsExpanding(false);
            setExpansionProgress({ current: 0, total: 0 });
            setExpandingNodePath('');
            expansionCancelledRef.current = false;
        }
    }, [isExpanding]);

    /**
     * Cancel the current expansion operation
     */
    const cancelExpansion = useCallback(() => {
        if (isExpanding) {
            expansionCancelledRef.current = true;
        }
    }, [isExpanding]);

    /**
     * Quick collapse all - can be synchronous since hiding is faster than showing
     * Collapses all children of a specific node instantly
     */
    const handleCollapseAll = useCallback((nodeXPath) => {
        setExpandedNodeXPaths(prev => {
            const newState = { ...prev };

            // Find all child nodes of this node and collapse them instantly
            Object.keys(prev).forEach(xpath => {
                // If this xpath is a child of the node we're collapsing, set it to false
                if (xpath.startsWith(nodeXPath + '.') || xpath.startsWith(nodeXPath + '[')) {
                    newState[xpath] = false;
                }
            });

            return newState;
        });
    }, []);

    /**
     * Recursively expand a node and all its children based on schema definition
     * Used when adding new objects/arrays to auto-expand them
     */
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
    }, []);

    /**
     * Update expanded state based on tree data changes
     * Ensures root is always expanded and removes invalid paths
     */
    const updateExpandedStateForTreeData = useCallback((newTreeData) => {
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
                if (newExpandedState.hasOwnProperty('root')) {
                    delete newExpandedState.root;
                    changed = true;
                }
            }
            return changed ? newExpandedState : prevExpandedPaths;
        });
    }, []);

    /**
     * Initialize expansion state for a new tree
     * Sets up initial expansion for root and first actual node
     */
    const initializeExpansionForTree = useCallback((originalTree) => {
        if (originalTree && originalTree.length > 0) {
            if (!initialExpansionSetForCurrentTreeRef.current) {
                const firstActualNode = originalTree[0];
                if (firstActualNode && firstActualNode.xpath) {
                    setExpandedNodeXPaths(prevExpandedPaths => ({
                        ...prevExpandedPaths,
                        "root": true,
                        [firstActualNode.xpath]: true
                    }));
                } else {
                    setExpandedNodeXPaths(prevExpandedPaths => ({
                        ...prevExpandedPaths,
                        "root": true
                    }));
                }
                initialExpansionSetForCurrentTreeRef.current = true;
            } else {
                // Initial expansion already done for this tree instance, ensure "root" is still set
                setExpandedNodeXPaths(prevExpandedPaths => {
                    if (prevExpandedPaths.root !== true) {
                        return { ...prevExpandedPaths, "root": true }
                    }
                    return prevExpandedPaths;
                });
            }
        } else {
            // Tree is empty or not yet loaded, reset the flag
            initialExpansionSetForCurrentTreeRef.current = false;
            // Ensure "root" is still in the base state for when tree loads
            setExpandedNodeXPaths(prevPaths => {
                if (Object.keys(prevPaths).length === 1 && prevPaths.root === true) return prevPaths;
                return { "root": true };
            });
        }
    }, []);

    /**
     * Auto-expand newly created objects based on the specific newly added/duplicated XPath
     * Only expands the most recently created node, not all previously created nodes
     */
    const autoExpandNewlyCreatedObjects = useCallback((originalTree) => {
        if (originalTree && originalTree.length > 0 && newlyAddedOrDuplicatedXPath) {
            const expandNewlyCreatedObjects = (node) => {
                // Only expand if this specific node matches the newly added/duplicated XPath
                if (node.xpath === newlyAddedOrDuplicatedXPath) {
                    const nodeData = get(updatedData, node.xpath);
                    if (nodeData) {
                        let objectSchema = null;
                        if (node.ref) {
                            const schemaRefParts = node.ref.split('/');
                            objectSchema = schemaRefParts.length === 2 ?
                                projectSchema[schemaRefParts[1]] :
                                projectSchema[schemaRefParts[1]][schemaRefParts[2]];
                        }
                        if (!objectSchema && typeof nodeData === 'object' && nodeData !== null) {
                            objectSchema = { properties: {} };
                            Object.keys(nodeData).forEach(key => {
                                if (!key.startsWith('xpath_') && key !== 'data-id') {
                                    objectSchema.properties[key] = {
                                        type: Array.isArray(nodeData[key]) ? 'array' :
                                            typeof nodeData[key] === 'object' && nodeData[key] !== null ? 'object' :
                                                typeof nodeData[key]
                                    };
                                }
                            });
                        }
                        if (objectSchema) {
                            expandNodeAndAllChildren(node.xpath, nodeData, objectSchema, projectSchema);
                        } else {
                            setExpandedNodeXPaths(prevExpanded => ({
                                ...prevExpanded,
                                [node.xpath]: true
                            }));
                        }
                    }
                }

                if (node.children && Array.isArray(node.children)) {
                    node.children.forEach(child => {
                        expandNewlyCreatedObjects(child);
                    });
                }
            };

            originalTree.forEach(node => {
                expandNewlyCreatedObjects(node);
            });
        }
    }, [updatedData, storedData, projectSchema, expandNodeAndAllChildren, newlyAddedOrDuplicatedXPath]);

    /**
     * Reset expansion state for a new tree instance
     */
    const resetExpansionState = useCallback(() => {
        initialExpansionSetForCurrentTreeRef.current = false;
        setExpandedNodeXPaths({ "root": true });
    }, []);

    return {
        // State
        expandedNodeXPaths,
        setExpandedNodeXPaths,

        // Batched expansion state
        isExpanding,
        expansionProgress,
        expandingNodePath,

        // Functions
        handleNodeToggle,
        handleExpandAll,
        handleCollapseAll,
        cancelExpansion,
        expandNodeAndAllChildren,
        updateExpandedStateForTreeData,
        initializeExpansionForTree,
        autoExpandNewlyCreatedObjects,
        resetExpansionState,

        // Refs
        initialExpansionSetForCurrentTreeRef
    };
};

export default useTreeExpansion;
