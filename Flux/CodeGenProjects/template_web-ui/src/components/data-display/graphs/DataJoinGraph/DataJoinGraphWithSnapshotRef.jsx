import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import { cloneDeep, get, set } from 'lodash';
import {
    Box,
    Typography,
    useTheme,
    Button,
    IconButton,
    Tooltip,
    Chip
} from '@mui/material';
import {
    ReactFlow,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    Handle,
    Position,
} from '@xyflow/react';
import DataJoinPopup from '../DataJoinPopup/DataJoinPopup';
import CustomEdge from '../Edges/CustomEdge';
import NodeSelector from '../NodeSelector';
import useClickIntent from '../../../../hooks/useClickIntent';
import { fetchNodeData, getCachedNodeData, fetchAnalysedData } from '../../../../services/GraphNodeService';
import { sliceMapWithFallback as sliceMap } from '../../../../models/sliceMap';
import { DB_ID, MODES } from '../../../../constants';
import { generateObjectFromSchema, getModelSchema, snakeToCamel } from '../../../../utils';
import { getJoinColor } from '../../../../utils/ui/colorUtils';
import { API_ROOT_URL } from '../../../../config';  // TODO: remove
import '@xyflow/react/dist/style.css';
import styles from './DataJoinGraph.module.css';

/**
 * Enhanced table node component with selection/loading states for the data join graph
 * @param {Object} props - Component props
 * @param {Object} props.data - Node data configuration
 * @param {string} props.data.label - Display label for the node
 * @param {boolean} props.data.isSelected - Whether the node is currently selected
 * @param {boolean} props.data.hasChildren - Whether the node has child nodes
 * @param {boolean} props.data.isExpanded - Whether the node is currently expanded
 * @returns {JSX.Element} Rendered table node component
 */
const TableNode = ({ data }) => {
    const { label, isSelected, hasChildren, isExpanded, nodeType, nodeTypeColor } = data;
    const theme = useTheme();

    const shouldHighlight = (hasChildren) && !isExpanded;
    const isExpandedRoot = (hasChildren) && isExpanded;

    return (
        <Box
            style={{
                cursor: 'pointer',
                backgroundColor: shouldHighlight
                    ? theme.palette.warning.dark
                    : isExpandedRoot
                        ? theme.palette.info.light
                        : theme.palette.background.paper,
                border: `${isSelected ? '2px' : '1px'} solid ${isSelected
                    ? theme.palette.primary.main
                    : theme.palette.divider
                    }`,
                borderRadius: '12px',
                padding: '6px',
                boxShadow: isSelected
                    ? `0 2px 8px ${theme.palette.primary.main}40`
                    : 'none',
                transition: 'all 0.2s ease'
            }}
        >
            <Handle type="source" position={Position.Right} />
            <Handle type="target" position={Position.Left} />
            <Chip size='small' label={label} color={nodeTypeColor} />
            {/* <Typography
                variant="subtitle2"
                style={{
                    fontWeight: 600,
                    color: nodeTypeColor ? 
                        (nodeTypeColor.contrastText || theme.palette.getContrastText(nodeTypeColor.main)) : 
                        theme.palette.text.primary,
                    backgroundColor: nodeTypeColor ? nodeTypeColor.main : 'transparent',
                    padding: nodeTypeColor ? '4px 8px' : '0',
                    borderRadius: nodeTypeColor ? '12px' : '0',
                    fontSize: '0.875rem'
                }}
            >
                {label}
            </Typography> */}
        </Box>
    );
};

TableNode.propTypes = {
    data: PropTypes.shape({
        label: PropTypes.string.isRequired,
        isSelected: PropTypes.bool.isRequired,
        hasChildren: PropTypes.bool.isRequired,
        isExpanded: PropTypes.bool.isRequired,
        nodeType: PropTypes.string,
        nodeTypeColor: PropTypes.string
    }).isRequired
};

const nodeTypes = {
    tableNode: TableNode,
};

const edgeTypes = {
    custom: CustomEdge,
};

/**
 * DataJoinGraph component for visualizing and managing node relationships in a graph format.
 * Provides interactive nodes and edges for data join operations with support for:
 * - Node selection and expansion/collapse
 * - Join configuration between nodes
 * - Visual representation of different join types
 * - Node data fetching and caching
 * - Read and edit modes
 * 
 * @param {Object} props - Component props
 * @param {string} props.modelName - Name of the model being visualized
 * @param {Object} props.modelDataSource - Data source configuration for the model
 * @param {Object} props.modelDataSource.selector - Redux selector for model data
 * @param {Object} props.modelDataSource.actions - Redux actions for model operations
 * @param {Array} props.modelDataSource.fieldsMetadata - Metadata for model fields
 * @returns {JSX.Element} Rendered DataJoinGraph component
 */
const DataJoinGraph = ({ modelName, modelDataSource }) => {
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);
    const { selector, actions, fieldsMetadata } = modelDataSource;
    const { updatedObj, mode } = useSelector(selector);
    const { contextId } = useSelector(state => state[modelName]);
    const dispatch = useDispatch();

    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    // Generic field attributes mapping (similar to ChatView's chatAttributes)
    const graphAttributes = useMemo(() => {
        const contextMeta = fieldsMetadata.find((o) => o.graph);
        const contextRefs = contextMeta?.$ref?.split('/');
        const contextSchemaName = contextRefs?.[contextRefs.length - 1];
        const contextPath = contextMeta?.tableTitle;
        const contextParentPath = contextMeta?.parentxpath;

        const nodesMeta = fieldsMetadata.find((o) => o.node);
        const edgesMeta = fieldsMetadata.find((o) => o.edge);

        const nodesPath = nodesMeta?.key;
        const edgesPath = edgesMeta?.key;

        const nodeNameMeta = fieldsMetadata.find((o) => o.node_name);
        const nodeTypeMeta = fieldsMetadata.find((o) => o.node_type);
        const nodeAccessMeta = fieldsMetadata.find((o) => o.node_access);
        const nodeUrlMeta = fieldsMetadata.find((o) => o.node_url);

        const nodeNameField = nodeNameMeta?.key;
        const nodeTypeField = nodeTypeMeta?.key;
        const nodeAccessField = nodeAccessMeta?.key;
        const nodeUrlField = nodeUrlMeta?.key;

        return {
            contextParentPath,
            contextSchemaName,
            contextPath,
            nodesPath,
            edgesPath,
            // Node field names (these are standardized in the schema)
            nodeNameField,
            nodeUrlField,
            nodeTypeField,
            nodeAccessField,
            nodeSelectedFieldsField: 'field_selections',
            // Edge field names (these are standardized in the schema)
            edgeBaseField: 'base_entity_selection.entity_name',
            edgeTargetField: 'join_entity_selection.entity_name',
            edgeTypeField: 'join_type',
            edgePairsField: 'join_pairs',
            edgeConfirmedField: 'user_confirmed'
        };
    }, [fieldsMetadata]);

    // Ref to track initialization
    const isInitializedRef = useRef(false);

    // Node selection and data fetching states
    const [selectedNodes, setSelectedNodes] = useState([]);
    const [selectedAnalyzeButton, setSelectedAnalyzeButton] = useState(null);
    const [nodeDataCache, setNodeDataCache] = useState({});
    // for expand collapse 
    const [visibleNodes, setVisibleNodes] = useState(new Set());
    const [expandedNodes, setExpandedNodes] = useState(new Set());
    const [modalOpen, setModalOpen] = useState(false);
    const [modalNodes, setModalNodes] = useState({ source: null, target: null });

    const snapshotRef = useRef();
    snapshotRef.current = {
        contextId,
        selectedNodes,
        selectedAnalyzeButton,
        nodeDataCache,
        expandedNodes,
        visibleNodes
    }

    // Initialize ReactFlow hooks
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    const contexts = useMemo(() => get(updatedObj, graphAttributes.contextPath) || [], [updatedObj, graphAttributes.contextPath]);

    const activeContext = useMemo(() => {
        if (contextId && contexts.length > 0) {
            return contexts.find((o) => o[DB_ID] === contextId);
        }
        return null;
    }, [contexts, contextId]);

    const { rootNodeIds, nodesWithChildren } = useMemo(() => {
        if (!activeContext) {
            return { rootNodeIds: new Set(), nodesWithChildren: new Map() };
        }
        const nodes = get(activeContext, graphAttributes.nodesPath) || [];
        const edges = get(activeContext, graphAttributes.edgesPath) || [];

        const allNodeIds = new Set(nodes.map(n => get(n, graphAttributes.nodeNameField)));
        const targetNodeIds = new Set(edges.map(e => get(e, graphAttributes.edgeTargetField)));
        const rootNodeIds = new Set(
            [...allNodeIds].filter(nodeId => !targetNodeIds.has(nodeId))
        );

        const nodesWithChildren = new Map();
        edges.forEach(edge => {
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNode = get(edge, graphAttributes.edgeTargetField);
            if (!nodesWithChildren.has(baseNode)) {
                nodesWithChildren.set(baseNode, new Set());
            }
            nodesWithChildren.get(baseNode).add(targetNode);
        });

        return { rootNodeIds, nodesWithChildren };
    }, [activeContext, graphAttributes]);

    // Create node type color mapping from schema metadata
    const nodeTypeColorMap = useMemo(() => {
        const nodeTypeMeta = fieldsMetadata.find((o) => o.key === graphAttributes.nodeTypeField);
        const colorMap = {};
        nodeTypeMeta?.color?.split(',').forEach((typeNColor) => {
            const [type, color] = typeNColor.split('=');
            colorMap[type.trim()] = color.trim().toLowerCase();
        })
        return colorMap;
    }, [fieldsMetadata, graphAttributes.nodeTypeField]);

    const calculateNodesAndEdges = useCallback((updatedContext = null) => {
        if (!activeContext) {
            return { nodes: [], edges: [] };
        }

        const currentContext = updatedContext || activeContext;
        const contextNodes = get(currentContext, graphAttributes.nodesPath) || [];
        const contextEdges = get(currentContext, graphAttributes.edgesPath) || [];

        const { selectedNodes, selectedAnalyzeButton, expandedNodes, visibleNodes } = snapshotRef.current;

        const allNodes = contextNodes.map((node, index) => {
            const x = (index % 3) * 300 + 100;
            const y = Math.floor(index / 3) * 250 + 100;
            const nodeName = get(node, graphAttributes.nodeNameField);
            const hasChildren = nodesWithChildren.has(nodeName);

            // Check if children are actually visible (effective expansion)
            const areChildrenVisible = hasChildren &&
                Array.from(nodesWithChildren.get(nodeName) || [])
                    .some(childId => visibleNodes.has(childId));

            const isExpanded = !hasChildren || areChildrenVisible;

            // Extract node type and get corresponding color
            const nodeType = get(node, graphAttributes.nodeTypeField);
            const schemaColorType = nodeTypeColorMap[nodeType] || 'default';
            const nodeTypeColor = schemaColorType === 'debug' ? 'default' : schemaColorType;

            return {
                id: nodeName,
                type: 'tableNode',
                position: { x, y },
                data: {
                    label: nodeName,
                    isSelected: selectedNodes.includes(nodeName),
                    hasChildren,
                    isExpanded,
                    nodeType,
                    nodeTypeColor,
                },
            };
        });

        const allEdges = contextEdges.map((edge, index) => {
            const edgePairs = get(edge, graphAttributes.edgePairsField) || [];
            const isConfirmed = edgePairs.every(p => get(p, graphAttributes.edgeConfirmedField)) ?? true;
            const edgeType = get(edge, graphAttributes.edgeTypeField);
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNode = get(edge, graphAttributes.edgeTargetField);
            const color = getJoinColor(edgeType, isConfirmed);
            const edgeId = `edge-${baseNode}-${targetNode}-${index}`;

            // Find the source and target node objects
            const sourceNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === baseNode);
            const targetNodeObj = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === targetNode);

            return {
                id: edgeId,
                source: baseNode,
                target: targetNode,
                type: 'custom',
                data: {
                    edgeType: edgeType,
                    edgeInfo: edge,
                    sourceNode: sourceNode,
                    targetNode: targetNodeObj,
                    isSelected: edgeId === selectedAnalyzeButton,
                },
                style: { stroke: color, strokeWidth: 2 },
                markerEnd: {
                    type: 'arrowclosed',
                    width: 20,
                    height: 20,
                    color: color,
                },
            };
        });

        // NEW FILTERING LOGIC
        const filteredNodes = allNodes.filter(node => visibleNodes.has(node.id));
        const filteredEdges = allEdges.filter(edge =>
            visibleNodes.has(edge.source) && visibleNodes.has(edge.target)
        );

        return { nodes: filteredNodes, edges: filteredEdges };
    }, [
        activeContext,
        rootNodeIds,
        nodesWithChildren,
        theme,
        nodeTypeColorMap
    ]);

    // Helper function to update nodes/edges
    const updateNodesAndEdges = useCallback((updatedContext = null) => {
        const { nodes: newNodes, edges: newEdges } = calculateNodesAndEdges(updatedContext);

        setNodes((prevNodes) => {
            const existingPositions = {};
            prevNodes.forEach((node) => {
                existingPositions[node.id] = node.position;
            });
            return newNodes.map((node) => ({
                ...node,
                position: existingPositions[node.id] || node.position
            }));
        });
        setEdges(newEdges);
    }, [calculateNodesAndEdges]);

    useEffect(() => {
        // context id can only be changed in read mode and only by other layout
        // if changes - reinitialize everything
        setSelectedNodes([]);
        setSelectedAnalyzeButton(null);
        setNodeDataCache({});
        setVisibleNodes(new Set());
        setExpandedNodes(new Set());
        setNodes([]);
        setEdges([]);
        // if context id is changing - means modal is already closed
        isInitializedRef.current = false;
        // prevContextIdRef.current = contextId;
    }, [contextId])

    // Core useEffect for READ vs EDIT mode logic
    useEffect(() => {
        if (mode === MODES.READ) {
            if (activeContext && activeContext[DB_ID] === snapshotRef.current.contextId && !isInitializedRef.current) {
                setVisibleNodes(rootNodeIds);
                snapshotRef.current.visibleNodes = rootNodeIds;
                isInitializedRef.current = true;
            }
            // READ mode - always recalculate when:
            // - active context changes
            // - entities/joins get updated
            updateNodesAndEdges();
        } else if (mode === MODES.EDIT) {
            if (activeContext && activeContext[DB_ID] === snapshotRef.current.contextId && !isInitializedRef.current) {
                // EDIT mode - initialize once from store data
                // rest updates from event handlers
                setVisibleNodes(rootNodeIds);
                snapshotRef.current.visibleNodes = rootNodeIds;
                updateNodesAndEdges();
                isInitializedRef.current = true;
            }
        }
    }, [mode, activeContext, rootNodeIds, updateNodesAndEdges]);

    // Helper function to get all descendants of a node recursively
    const getNodeDescendants = useCallback((nodeId, nodesWithChildrenMap) => {
        const descendants = new Set();
        const childrenIds = nodesWithChildrenMap.get(nodeId) || [];

        for (const childId of childrenIds) {
            descendants.add(childId);
            // Recursively get descendants of children
            const childDescendants = getNodeDescendants(childId, nodesWithChildrenMap);
            childDescendants.forEach(descendant => descendants.add(descendant));
        }

        return descendants;
    }, []);

    // Helper function to collapse a node and clean up state
    const collapseNode = useCallback((nodeId) => {
        const descendants = getNodeDescendants(nodeId, nodesWithChildren);

        const { selectedNodes, visibleNodes, expandedNodes } = snapshotRef.current;

        // Remove all descendants from visible nodes
        setVisibleNodes(prevVisible => {
            const newVisible = new Set(prevVisible);
            descendants.forEach(descendant => newVisible.delete(descendant));
            return newVisible;
        });
        descendants.forEach(descendant => visibleNodes.delete(descendant));

        // Remove the collapsed node from expanded nodes and clean up any descendant expanded nodes
        setExpandedNodes(prevExpanded => {
            const newExpanded = new Set(prevExpanded);
            newExpanded.delete(nodeId);
            // Remove any descendants that were also expanded
            descendants.forEach(descendant => newExpanded.delete(descendant));
            return newExpanded;
        });
        expandedNodes.delete(nodeId);
        descendants.forEach(descendant => expandedNodes.delete(descendant));

        // Clean up selected nodes that are no longer visible
        setSelectedNodes(prevSelected =>
            prevSelected.filter(selectedId =>
                selectedId === nodeId || !descendants.has(selectedId)
            )
        );
        const newSelectedNodes = snapshotRef.current.selectedNodes.filter(id => id === nodeId || !descendants.has(id));
        snapshotRef.current.selectedNodes = newSelectedNodes;
    }, [getNodeDescendants, nodesWithChildren]);


    const prepareAndOpenModal = useCallback(async (nodeName1, nodeName2) => {
        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const sourceNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === nodeName1);
        const targetNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === nodeName2);

        if (!sourceNode || !targetNode) {
            console.error("Could not find selected nodes in context.");
            return;
        }

        let sourceNodeData = nodeDataCache[nodeName1] || getCachedNodeData(nodeName1);
        let targetNodeData = nodeDataCache[nodeName2] || getCachedNodeData(nodeName2);

        try {
            if (!sourceNodeData) {
                console.log(`Cache miss for ${nodeName1}. Fetching...`);
                sourceNodeData = await fetchNodeData(sourceNode);
                setNodeDataCache(prev => ({ ...prev, [nodeName1]: sourceNodeData }));
                snapshotRef.current.nodeDataCache = { ...snapshotRef.current.nodeDataCache, [nodeName1]: sourceNodeData };
            }

            if (!targetNodeData) {
                console.log(`Cache miss for ${nodeName2}. Fetching...`);
                targetNodeData = await fetchNodeData(targetNode);
                setNodeDataCache(prev => ({ ...prev, [nodeName2]: targetNodeData }));
                snapshotRef.current.nodeDataCache = { ...snapshotRef.current.nodeDataCache, [nodeName2]: targetNodeData };
            }
        } catch (error) {
            console.error('Failed to fetch node data for modal:', error);
            return; // Popup mat kholo agar fetch fail ho gaya
        }

        const sourceNodeWithColumns = { ...sourceNode, columns: sourceNodeData?.columns || [] };
        const targetNodeWithColumns = { ...targetNode, columns: targetNodeData?.columns || [] };

        setModalNodes({
            source: sourceNodeWithColumns,
            target: targetNodeWithColumns
        });
        setModalOpen(true);

    }, [activeContext, graphAttributes.nodesPath, nodeDataCache]);

    // Handle analysis from edge
    const handleAnalyse = useCallback(async (edgeId, edgeData) => {
        try {
            // Toggle selection of analyze button
            setSelectedAnalyzeButton(edgeId);
            snapshotRef.current.selectedAnalyzeButton = edgeId;

            // Force re-render of edges to show selection state
            updateNodesAndEdges();

            const { sourceNode, targetNode, edgeInfo } = edgeData;

            if (!sourceNode || !targetNode) {
                console.error('Missing node information for analysis');
                return;
            }

            // Check if both nodes have cached data, fetch if not
            const sourceName = get(sourceNode, graphAttributes.nodeNameField);
            const targetName = get(targetNode, graphAttributes.nodeNameField);
            let sourceNodeData = nodeDataCache[sourceName] || getCachedNodeData(sourceName);
            let targetNodeData = nodeDataCache[targetName] || getCachedNodeData(targetName);

            // Fetch missing node data
            if (!sourceNodeData) {
                sourceNodeData = await fetchNodeData(sourceNode);
                setNodeDataCache(prev => ({ ...prev, [sourceName]: sourceNodeData }));
            }

            if (!targetNodeData) {
                targetNodeData = await fetchNodeData(targetNode);
                setNodeDataCache(prev => ({ ...prev, [targetName]: targetNodeData }));
            }

            // Fetch analysed data
            const result = await fetchAnalysedData(sourceNode, targetNode, edgeInfo);

            // Format the data for display
            let alertMessage = `Analysis Results:\n`;
            alertMessage += `Source: ${result.source_node}\n`;
            alertMessage += `Target: ${result.target_node}\n`;
            alertMessage += `Records: ${result.record_count}\n\n`;

            // Show column headers
            if (result.analysed_columns && result.analysed_columns.length > 0) {
                alertMessage += `Columns: ${result.analysed_columns.map(col => col.name).join(', ')}\n\n`;
            }

            // Show sample data
            if (result.analysed_data && result.analysed_data.length > 0) {
                alertMessage += `Sample Data:\n`;
                result.analysed_data.forEach((record, index) => {
                    alertMessage += `Row ${index + 1}: ${JSON.stringify(record)}\n`;
                });
            }

            alert(alertMessage);

        } catch (error) {
            console.error('Analysis error:', error);
            console.error(`Analysis failed: ${error.message}`);
        }
    }, [nodeDataCache, fetchNodeData, fetchAnalysedData, updateNodesAndEdges]);

    // Handle node selection with node data fetching
    const handleNodeSelection = useCallback(async (e, node) => {
        // Clear analyze button selection when node is clicked
        setSelectedAnalyzeButton(null);
        snapshotRef.current.selectedAnalyzeButton = null;

        const nodeId = node.id
        const isCtrlPressed = e.ctrlKey || e.metaKey;
        // 1. Calculate new selection state
        const { selectedNodes, nodeDataCache, expandedNodes } = snapshotRef.current;
        const isSelected = selectedNodes.includes(nodeId);
        let newSelection;

        if (isCtrlPressed) {
            newSelection = isSelected
                ? selectedNodes.filter(id => id !== nodeId)
                : [...selectedNodes, nodeId];
        } else {
            newSelection = [nodeId];
        }

        // set the underlying node model for display
        const nodeName = newSelection[0];
        const modelNodeName = `${modelName}_node`;
        const nodeActions = sliceMap[modelNodeName]?.actions;
        if (newSelection.length === 1) {
            dispatch(nodeActions.setNode({
                modelName: nodeName,
                modelSchema: getModelSchema(nodeName, projectSchema),
                fieldsMetadata: schemaCollections[nodeName],
                url: API_ROOT_URL
            }));
        } else {
            dispatch(nodeActions.setNode(null));
        }

        // 2. Update selection state (this will trigger nodes recalculation via useEffect)
        setSelectedNodes(newSelection);
        snapshotRef.current.selectedNodes = newSelection;

        if (newSelection.length === 2 && mode === MODES.EDIT) {
            prepareAndOpenModal(newSelection[0], newSelection[1]);
        }

        // 3. Fetch node data if needed
        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const selectedNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === nodeId);
        const hasChildren = nodesWithChildren.has(nodeId);
        const isExpanded = !hasChildren || (hasChildren && expandedNodes.has(nodeId));

        // Fetch data only if the node has no children, or if it has children and is expanded.
        if (selectedNode && isExpanded) {
            const nodeName = get(selectedNode, graphAttributes.nodeNameField);
            if (!nodeDataCache[nodeName] && !getCachedNodeData(nodeName)) {
                try {
                    const nodeData = await fetchNodeData(selectedNode);
                    setNodeDataCache(prev => ({ ...prev, [nodeName]: nodeData }));
                    snapshotRef.current.nodeDataCache = { ...nodeDataCache, [nodeName]: nodeData };
                } catch (error) {
                    console.error(`❌ Failed to fetch data for node: ${get(selectedNode, graphAttributes.nodeNameField)}`, error);
                }
            }
        }
        updateNodesAndEdges();
    }, [activeContext, nodesWithChildren, updateNodesAndEdges]);

    // handler for expanding/collapsing a node (toggle functionality)
    const handleNodeDoubleClick = useCallback((_, node) => {
        if (!activeContext) return;

        const { expandedNodes, visibleNodes } = snapshotRef.current;
        const childrenIds = nodesWithChildren.get(node.id) || [];
        const isExpanded = expandedNodes.has(node.id);

        if (childrenIds.size > 0) {
            if (isExpanded) {
                // Node is expanded - collapse it
                collapseNode(node.id);
            } else {
                // Node is not expanded - expand it
                setVisibleNodes(prevVisible => new Set([...prevVisible, ...childrenIds]));
                snapshotRef.current.visibleNodes = new Set([...visibleNodes, ...childrenIds]);
                setExpandedNodes(prevExpanded => new Set([...prevExpanded, node.id]));
                snapshotRef.current.expandedNodes = new Set([...expandedNodes, node.id]);
            }
        }
        updateNodesAndEdges();
    }, [activeContext, nodesWithChildren, expandedNodes, collapseNode]);

    const clickHandler = useClickIntent(handleNodeSelection, handleNodeDoubleClick);

    // Get existing edges between two nodes
    const getNodePairEdges = useCallback((sourceNodeName, targetNodeName) => {
        const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];

        return contextEdges.filter(edge => {
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNode = get(edge, graphAttributes.edgeTargetField);
            return (baseNode === sourceNodeName && targetNode === targetNodeName) ||
                (baseNode === targetNodeName && targetNode === sourceNodeName);
        });
    }, [activeContext, graphAttributes]);

    // Handle save from DataJoinPopup
    const handleModalSave = useCallback((saveData) => {
        const { sourceNode, targetNode, updatedJoins: updatedEdges } = saveData;

        if (!activeContext || !dispatch) return;

        // CASE 1: Handle null response (no connections initially, no connections at end)
        if (updatedEdges === null) {
            // Do nothing - this maintains consistency as requested
            console.log('No join changes needed - maintaining current state');
            return;
        }

        // Get the names of the nodes we are working with
        const sourceName = get(sourceNode, graphAttributes.nodeNameField);
        const targetName = get(targetNode, graphAttributes.nodeNameField);

        // Filter the original edges array to REMOVE the old edges for this specific pair
        const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];
        const otherEdges = contextEdges.filter(edge => {
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNodeField = get(edge, graphAttributes.edgeTargetField);
            return !((baseNode === sourceName && targetNodeField === targetName) ||
                (baseNode === targetName && targetNodeField === sourceName));
        });

        // CASE 2 & 3: Handle updated edges array (deletions already handled in DataJoinPopup)
        const newCompleteEdgesArray = [...otherEdges, ...updatedEdges];

        // Create updated context with modified edges 
        const updatedContext = cloneDeep(activeContext);

        // Update edges
        set(updatedContext, graphAttributes.edgesPath, newCompleteEdgesArray);

        // Update Redux with the modified context
        const updatedData = cloneDeep(updatedObj);
        const contexts = get(updatedData, graphAttributes.contextPath) || [];
        const contextIndex = contexts.findIndex((o) => o[DB_ID] === activeContext[DB_ID]);
        if (contextIndex !== -1) {
            contexts.splice(contextIndex, 1, updatedContext);
        }
        dispatch(actions.setUpdatedObj(updatedData));
        updateNodesAndEdges(updatedContext);
    }, [activeContext, dispatch, updatedObj, graphAttributes]);

    // Handle edge click to open DataJoinPopup in edit mode
    const handleEdgeClick = useCallback(async (event, edge) => {
        // Check if click target is the analyze div (check for text content "Analyze")
        const isAnalyzeClick = event.target.textContent === 'Analyze' ||
            event.target.closest('[class*="nodrag nopan"]')?.textContent?.includes('Analyze');

        if (isAnalyzeClick) {
            // Call handleAnalyse for analyze div clicks
            await handleAnalyse(edge.id, edge.data);
            return;
        }

        // Only process edge clicks in EDIT mode
        if (mode !== MODES.EDIT) return;

        const { sourceNode, targetNode } = edge.data;

        if (sourceNode && targetNode) {
            // Get cached node data for columns
            const sourceName = get(sourceNode, graphAttributes.nodeNameField);
            const targetName = get(targetNode, graphAttributes.nodeNameField);
            prepareAndOpenModal(sourceName, targetName);

        }
    }, [mode, nodeDataCache, getCachedNodeData, graphAttributes, handleAnalyse]);

    const handleNodeSelectorChange = (selectedOptions) => {

        function trimLastPath(xpath) {
            return xpath?.substring(0, Math.max(xpath.lastIndexOf("."), xpath.lastIndexOf("]")));
        }

        const newNodes = new Set();

        // Create updated nodes array with existing selectedNodes data for matched items
        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const updatedNodes = selectedOptions.map(option => {
            // Try to find existing node with same name
            const existingNode = contextNodes.find(node =>
                get(node, graphAttributes.nodeNameField) === get(option, graphAttributes.nodeNameField)
            );

            if (existingNode) {
                // Return existing node to preserve _id and other fields
                return existingNode;
            }

            const parentPath = trimLastPath(activeContext['xpath__id']);
            const nodeSchema = getModelSchema('entity', projectSchema);
            const newObject = generateObjectFromSchema(projectSchema, nodeSchema, undefined, parentPath);

            const optionName = get(option, graphAttributes.nodeNameField) || option.displayName;
            set(newObject, graphAttributes.nodeNameField, optionName);
            set(newObject, graphAttributes.nodeTypeField, get(option, graphAttributes.nodeTypeField));
            set(newObject, graphAttributes.nodeAccessField, get(option, graphAttributes.nodeAccessField));

            newNodes.add(optionName);

            return newObject
        });

        const nodesSet = new Set(updatedNodes.map((node) => get(node, graphAttributes.nodeNameField)));
        const updatedData = cloneDeep(updatedObj);
        const contexts = get(updatedData, graphAttributes.contextPath) || [];
        const updatedContext = contexts.find((o) => o[DB_ID] === contextId);
        if (!updatedContext) return;

        set(updatedContext, graphAttributes.nodesPath, updatedNodes);
        const contextEdges = get(updatedContext, graphAttributes.edgesPath) || [];
        const filteredEdges = contextEdges.filter((edge) => {
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNode = get(edge, graphAttributes.edgeTargetField);
            return nodesSet.has(baseNode) && nodesSet.has(targetNode);
        });
        set(updatedContext, graphAttributes.edgesPath, filteredEdges);
        dispatch(actions.setUpdatedObj(updatedData));
        setVisibleNodes((prev) => {
            const newSet = new Set(
                [...prev].filter(nodeId => nodesSet.has(nodeId))
            );
            newNodes.forEach(nodeId => newSet.add(nodeId));
            return newSet;
        })
        const filteredVisibleNodes = new Set(
            [...snapshotRef.current.visibleNodes].filter(nodeId => nodesSet.has(nodeId))
        );
        newNodes.forEach(nodeId => filteredVisibleNodes.add(nodeId));
        snapshotRef.current.visibleNodes = filteredVisibleNodes;
        updateNodesAndEdges(updatedContext);
    }

    const availableNodes = useMemo(() => projectSchema.autocomplete['EntityNType_List'] || []);

    return (
        <>
            {updatedObj && activeContext && (
                <Box className={styles.container} data-theme={isDarkMode ? 'dark' : 'light'}>
                    <Box className={styles.header}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Typography variant="h6">
                                {updatedObj?.name}
                            </Typography>
                        </Box>
                        <Box className={styles.metadata} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <NodeSelector
                                availableNodes={availableNodes}
                                selectedNodes={get(activeContext, graphAttributes.nodesPath) || []}
                                nodeTypeColorMap={nodeTypeColorMap}
                                mode={mode}
                                onChange={handleNodeSelectorChange}
                                nodeNameField={graphAttributes.nodeNameField}
                                nodeTypeField={graphAttributes.nodeTypeField}
                                nodeAccessField={graphAttributes.nodeAccessField}
                            />
                        </Box>
                    </Box>

                    <Box className={styles.flowContainer} sx={{ height: '100vh' }}>
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onNodeClick={clickHandler}
                            onNodeDoubleClick={clickHandler}
                            onEdgeClick={handleEdgeClick}
                            nodeTypes={nodeTypes}
                            edgeTypes={edgeTypes}
                            fitView={false}
                            className={styles.reactFlow}
                            selectNodesOnDrag={false}
                            elementsSelectable={true}
                            zoomOnScroll={false}
                            proOptions={{ hideAttribution: true }}
                        >
                            <Controls
                                style={{
                                    color: theme.palette.common.black,
                                    border: `1px solid ${isDarkMode ? theme.palette.grey[600] : theme.palette.grey[300]} `,
                                    borderRadius: '8px',
                                    boxShadow: isDarkMode
                                        ? '0 2px 8px rgba(255, 255, 255, 0.1)'
                                        : '0 2px 8px rgba(0, 0, 0, 0.1)'
                                }}
                            />

                            <Background
                                variant="dots"
                                gap={12}
                                size={1}
                                color={isDarkMode ? theme.palette.grey[600] : theme.palette.grey[400]}
                                style={{
                                    backgroundColor: isDarkMode ? theme.palette.grey[900] : theme.palette.grey[50]
                                }}
                            />
                        </ReactFlow>
                    </Box>

                    <Box className={styles.controls} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Button variant="outlined"
                                size="small"
                                sx={{
                                    color: "#0000",
                                    borderColor: "#3B82F6",
                                    borderRadius: "6px",
                                    padding: "2px 10px",
                                    fontSize: "12px",
                                    textTransform: "none"
                                }}
                                disabled={selectedNodes.length !== 2 || mode === MODES.READ}
                                onClick={() => {
                                    if (selectedNodes.length === 2) {
                                        // Get the two selected nodes and their data
                                        prepareAndOpenModal(selectedNodes[0], selectedNodes[1]);
                                    }
                                }}
                            >
                                Configure ({selectedNodes.length}/2)
                            </Button>
                            <Tooltip title="Clear Selection">
                                <span>
                                    <IconButton
                                        size="small"
                                        onClick={() => {
                                            setSelectedNodes([]);
                                            snapshotRef.current.selectedNodes = [];
                                            updateNodesAndEdges();
                                        }}
                                        disabled={selectedNodes.length === 0}
                                    >
                                        <Typography variant="button">X</Typography>
                                    </IconButton>
                                </span>
                            </Tooltip>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                                Inner:
                            </Typography>
                            <Box sx={{ width: 20, height: 2, bgcolor: '#3B82F6' }} />

                            <Typography variant="caption" color="text.secondary">
                                Left/Outer:
                            </Typography>
                            <Box sx={{ width: 20, height: 2, bgcolor: '#EF4444' }} />

                            <Typography variant="caption" color="text.secondary">
                                Full:
                            </Typography>
                            <Box sx={{ width: 20, height: 2, bgcolor: '#10B981' }} />

                            <Typography variant="caption" color="text.secondary">
                                Right:
                            </Typography>
                            <Box sx={{ width: 20, height: 2, bgcolor: '#F59E0B' }} />
                            <Typography variant="caption">
                                AI suggestions are displayed in light color •• Unknown Joins are in Grey
                            </Typography>
                        </Box>
                    </Box>
                </Box>
            )}
            {/* //for now not using !activeContext */}
            {!updatedObj && (
                <Box sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    p: 3,
                    textAlign: 'center'
                }}>
                    <Box>
                        <div style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
                            No DataLab Selected
                        </div>
                        <div style={{ color: 'text.secondary' }}>
                            Select a DataLab from the collection to view its graph visualization
                        </div>
                    </Box>
                </Box>
            )}

            {/* DataJoinPopup Modal */}
            {modalOpen && modalNodes.source && modalNodes.target && (
                <DataJoinPopup
                    open={modalOpen}
                    onClose={() => {
                        setModalOpen(false);
                        setModalNodes({ source: null, target: null });
                    }}
                    sourceNode={modalNodes.source}
                    targetNode={modalNodes.target}
                    existingJoins={getNodePairEdges(
                        get(modalNodes.source, graphAttributes.nodeNameField),
                        get(modalNodes.target, graphAttributes.nodeNameField)
                    )}
                    onSave={handleModalSave}
                    graphAttributes={graphAttributes}
                    fieldsMetadata={fieldsMetadata}
                />
            )}
        </>
    )
}

DataJoinGraph.propTypes = {
    modelName: PropTypes.string.isRequired,
    modelDataSource: PropTypes.shape({
        selector: PropTypes.func.isRequired,
        actions: PropTypes.object.isRequired,
        fieldsMetadata: PropTypes.array.isRequired
    }).isRequired
};

export default React.memo(DataJoinGraph);
