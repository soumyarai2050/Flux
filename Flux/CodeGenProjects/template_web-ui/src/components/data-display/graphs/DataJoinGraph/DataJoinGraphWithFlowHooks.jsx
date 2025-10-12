import React, { useReducer, useEffect, useCallback, useMemo, useRef } from 'react';
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
import { API_ROOT_URL } from '../../../../config';
import '@xyflow/react/dist/style.css';
import styles from './DataJoinGraph.module.css';

/**
 * Enhanced table node component with selection/loading states for the data join graph
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

// Helper function to calculate nodes and edges
const calculateNodesAndEdges = (params) => {
    const {
        activeContext,
        graphAttributes,
        selectedNodes,
        selectedAnalyzeButton,
        visibleNodes,
        nodesWithChildren,
        nodeTypeColorMap
    } = params;

    if (!activeContext) {
        return { computedNodes: [], computedEdges: [] };
    }

    const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
    const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];

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

    // Filter based on visible nodes
    const filteredNodes = allNodes.filter(node => visibleNodes.has(node.id));
    const filteredEdges = allEdges.filter(edge =>
        visibleNodes.has(edge.source) && visibleNodes.has(edge.target)
    );

    return { computedNodes: filteredNodes, computedEdges: filteredEdges };
};

// Initial state factory
const createInitialState = () => ({
    selectedNodes: [],
    selectedAnalyzeButton: null,
    nodeDataCache: {},
    visibleNodes: new Set(),
    expandedNodes: new Set(),
    computedNodes: [],
    computedEdges: [],
    modalOpen: false,
    modalNodes: { source: null, target: null }
});

// Reducer actions
const ACTION_TYPES = {
    RESET_STATE: 'RESET_STATE',
    INITIALIZE: 'INITIALIZE',
    SELECT_NODE: 'SELECT_NODE',
    SELECT_ANALYZE_BUTTON: 'SELECT_ANALYZE_BUTTON',
    EXPAND_NODE: 'EXPAND_NODE',
    COLLAPSE_NODE: 'COLLAPSE_NODE',
    CACHE_NODE_DATA: 'CACHE_NODE_DATA',
    SET_VISIBLE_NODES: 'SET_VISIBLE_NODES',
    OPEN_MODAL: 'OPEN_MODAL',
    CLOSE_MODAL: 'CLOSE_MODAL',
    UPDATE_NODES_AND_EDGES: 'UPDATE_NODES_AND_EDGES',
    CLEAR_SELECTION: 'CLEAR_SELECTION'
};

// Main reducer function
const graphReducer = (state, action) => {
    switch (action.type) {
        case ACTION_TYPES.RESET_STATE: {
            return createInitialState();
        }

        case ACTION_TYPES.INITIALIZE: {
            const { rootNodeIds, ...params } = action.payload;
            const newState = {
                ...state,
                visibleNodes: rootNodeIds,
                expandedNodes: new Set()
            };
            
            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: newState.selectedNodes,
                selectedAnalyzeButton: newState.selectedAnalyzeButton,
                visibleNodes: newState.visibleNodes
            });

            return {
                ...newState,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.SELECT_NODE: {
            const { nodeId, isCtrlPressed, ...params } = action.payload;
            const isSelected = state.selectedNodes.includes(nodeId);
            
            let newSelectedNodes;
            if (isCtrlPressed) {
                newSelectedNodes = isSelected
                    ? state.selectedNodes.filter(id => id !== nodeId)
                    : [...state.selectedNodes, nodeId];
            } else {
                newSelectedNodes = [nodeId];
            }

            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: newSelectedNodes,
                selectedAnalyzeButton: null,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedNodes: newSelectedNodes,
                selectedAnalyzeButton: null,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.SELECT_ANALYZE_BUTTON: {
            const { edgeId, ...params } = action.payload;
            
            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: state.selectedNodes,
                selectedAnalyzeButton: edgeId,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedAnalyzeButton: edgeId,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.EXPAND_NODE: {
            const { nodeId, children, ...params } = action.payload;
            const newVisibleNodes = new Set([...state.visibleNodes, ...children]);
            const newExpandedNodes = new Set([...state.expandedNodes, nodeId]);

            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: state.selectedNodes,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: newVisibleNodes
            });

            return {
                ...state,
                visibleNodes: newVisibleNodes,
                expandedNodes: newExpandedNodes,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.COLLAPSE_NODE: {
            const { nodeId, descendants, ...params } = action.payload;
            
            const newVisibleNodes = new Set(state.visibleNodes);
            const newExpandedNodes = new Set(state.expandedNodes);
            
            descendants.forEach(descendant => {
                newVisibleNodes.delete(descendant);
                newExpandedNodes.delete(descendant);
            });
            newExpandedNodes.delete(nodeId);

            const newSelectedNodes = state.selectedNodes.filter(
                selectedId => selectedId === nodeId || !descendants.has(selectedId)
            );

            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: newSelectedNodes,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: newVisibleNodes
            });

            return {
                ...state,
                selectedNodes: newSelectedNodes,
                visibleNodes: newVisibleNodes,
                expandedNodes: newExpandedNodes,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.CACHE_NODE_DATA: {
            const { nodeId, data } = action.payload;
            return {
                ...state,
                nodeDataCache: { ...state.nodeDataCache, [nodeId]: data }
            };
        }

        case ACTION_TYPES.SET_VISIBLE_NODES: {
            const { visibleNodes, ...params } = action.payload;

            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: state.selectedNodes,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes
            });

            return {
                ...state,
                visibleNodes,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.OPEN_MODAL: {
            const { source, target } = action.payload;
            return {
                ...state,
                modalOpen: true,
                modalNodes: { source, target }
            };
        }

        case ACTION_TYPES.CLOSE_MODAL: {
            return {
                ...state,
                modalOpen: false,
                modalNodes: { source: null, target: null }
            };
        }

        case ACTION_TYPES.UPDATE_NODES_AND_EDGES: {
            const { ...params } = action.payload;
            
            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: state.selectedNodes,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                computedNodes,
                computedEdges
            };
        }

        case ACTION_TYPES.CLEAR_SELECTION: {
            const { ...params } = action.payload;
            
            const { computedNodes, computedEdges } = calculateNodesAndEdges({
                ...params,
                selectedNodes: [],
                selectedAnalyzeButton: null,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedNodes: [],
                selectedAnalyzeButton: null,
                computedNodes,
                computedEdges
            };
        }

        default:
            return state;
    }
};

/**
 * DataJoinGraph component for visualizing and managing node relationships in a graph format.
 */
const DataJoinGraph = ({ modelName, modelDataSource }) => {
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);
    const { selector, actions, fieldsMetadata } = modelDataSource;
    const { updatedObj, mode } = useSelector(selector);
    const { contextId } = useSelector(state => state[modelName]);
    const reduxDispatch = useDispatch();

    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';
    const isInitializedRef = useRef(false);

    // Initialize reducer
    const [state, dispatch] = useReducer(graphReducer, createInitialState());

    // Initialize ReactFlow hooks
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Graph attributes mapping
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
            nodeNameField,
            nodeUrlField,
            nodeTypeField,
            nodeAccessField,
            nodeSelectedFieldsField: 'field_selections',
            edgeBaseField: 'base_entity_selection.entity_name',
            edgeTargetField: 'join_entity_selection.entity_name',
            edgeTypeField: 'join_type',
            edgePairsField: 'join_pairs',
            edgeConfirmedField: 'user_confirmed'
        };
    }, [fieldsMetadata]);

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

    // Node type color mapping
    const nodeTypeColorMap = useMemo(() => {
        const nodeTypeMeta = fieldsMetadata.find((o) => o.key === graphAttributes.nodeTypeField);
        const colorMap = {};
        nodeTypeMeta?.color?.split(',').forEach((typeNColor) => {
            const [type, color] = typeNColor.split('=');
            colorMap[type.trim()] = color.trim().toLowerCase();
        })
        return colorMap;
    }, [fieldsMetadata, graphAttributes.nodeTypeField]);

    // Helper function to get all descendants of a node recursively
    const getNodeDescendants = useCallback((nodeId, nodesWithChildrenMap) => {
        const descendants = new Set();
        const childrenIds = nodesWithChildrenMap.get(nodeId) || [];

        for (const childId of childrenIds) {
            descendants.add(childId);
            const childDescendants = getNodeDescendants(childId, nodesWithChildrenMap);
            childDescendants.forEach(descendant => descendants.add(descendant));
        }

        return descendants;
    }, []);

    // Update ReactFlow nodes and edges when computed values change
    useEffect(() => {
        setNodes((prevNodes) => {
            const existingPositions = {};
            prevNodes.forEach((node) => {
                existingPositions[node.id] = node.position;
            });
            return state.computedNodes.map((node) => ({
                ...node,
                position: existingPositions[node.id] || node.position
            }));
        });
        setEdges(state.computedEdges);
    }, [state.computedNodes, state.computedEdges, setNodes, setEdges]);

    // Reset state when context changes
    useEffect(() => {
        dispatch({ type: ACTION_TYPES.RESET_STATE });
        isInitializedRef.current = false;
    }, [contextId]);

    // Initialize or update based on mode
    useEffect(() => {
        if (!activeContext || activeContext[DB_ID] !== contextId) {
            return;
        }

        if (mode === MODES.READ) {
            if (!isInitializedRef.current) {
                dispatch({
                    type: ACTION_TYPES.INITIALIZE,
                    payload: {
                        rootNodeIds,
                        activeContext,
                        graphAttributes,
                        nodesWithChildren,
                        nodeTypeColorMap
                    }
                });
                isInitializedRef.current = true;
            } else {
                // In READ mode, always update when context changes
                dispatch({
                    type: ACTION_TYPES.UPDATE_NODES_AND_EDGES,
                    payload: {
                        activeContext,
                        graphAttributes,
                        nodesWithChildren,
                        nodeTypeColorMap
                    }
                });
            }
        } else if (mode === MODES.EDIT) {
            if (!isInitializedRef.current) {
                dispatch({
                    type: ACTION_TYPES.INITIALIZE,
                    payload: {
                        rootNodeIds,
                        activeContext,
                        graphAttributes,
                        nodesWithChildren,
                        nodeTypeColorMap
                    }
                });
                isInitializedRef.current = true;
            }
        }
    }, [mode, activeContext, contextId, rootNodeIds, graphAttributes, nodesWithChildren, nodeTypeColorMap]);

    // Prepare and open modal
    const prepareAndOpenModal = useCallback(async (nodeName1, nodeName2) => {
        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const sourceNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === nodeName1);
        const targetNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === nodeName2);

        if (!sourceNode || !targetNode) {
            console.error("Could not find selected nodes in context.");
            return;
        }

        let sourceNodeData = state.nodeDataCache[nodeName1] || getCachedNodeData(nodeName1);
        let targetNodeData = state.nodeDataCache[nodeName2] || getCachedNodeData(nodeName2);

        try {
            if (!sourceNodeData) {
                console.log(`Cache miss for ${nodeName1}. Fetching...`);
                sourceNodeData = await fetchNodeData(sourceNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: nodeName1, data: sourceNodeData }
                });
            }

            if (!targetNodeData) {
                console.log(`Cache miss for ${nodeName2}. Fetching...`);
                targetNodeData = await fetchNodeData(targetNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: nodeName2, data: targetNodeData }
                });
            }
        } catch (error) {
            console.error('Failed to fetch node data for modal:', error);
            return;
        }

        const sourceNodeWithColumns = { ...sourceNode, columns: sourceNodeData?.columns || [] };
        const targetNodeWithColumns = { ...targetNode, columns: targetNodeData?.columns || [] };

        dispatch({
            type: ACTION_TYPES.OPEN_MODAL,
            payload: { source: sourceNodeWithColumns, target: targetNodeWithColumns }
        });
    }, [activeContext, graphAttributes.nodesPath, state.nodeDataCache]);

    // Handle analysis from edge
    const handleAnalyse = useCallback(async (edgeId, edgeData) => {
        try {
            dispatch({
                type: ACTION_TYPES.SELECT_ANALYZE_BUTTON,
                payload: {
                    edgeId,
                    activeContext,
                    graphAttributes,
                    nodesWithChildren,
                    nodeTypeColorMap
                }
            });

            const { sourceNode, targetNode, edgeInfo } = edgeData;

            if (!sourceNode || !targetNode) {
                console.error('Missing node information for analysis');
                return;
            }

            const sourceName = get(sourceNode, graphAttributes.nodeNameField);
            const targetName = get(targetNode, graphAttributes.nodeNameField);
            let sourceNodeData = state.nodeDataCache[sourceName] || getCachedNodeData(sourceName);
            let targetNodeData = state.nodeDataCache[targetName] || getCachedNodeData(targetName);

            if (!sourceNodeData) {
                sourceNodeData = await fetchNodeData(sourceNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: sourceName, data: sourceNodeData }
                });
            }

            if (!targetNodeData) {
                targetNodeData = await fetchNodeData(targetNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: targetName, data: targetNodeData }
                });
            }

            const result = await fetchAnalysedData(sourceNode, targetNode, edgeInfo);

            let alertMessage = `Analysis Results:\n`;
            alertMessage += `Source: ${result.source_node}\n`;
            alertMessage += `Target: ${result.target_node}\n`;
            alertMessage += `Records: ${result.record_count}\n\n`;

            if (result.analysed_columns && result.analysed_columns.length > 0) {
                alertMessage += `Columns: ${result.analysed_columns.map(col => col.name).join(', ')}\n\n`;
            }

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
    }, [activeContext, graphAttributes, nodesWithChildren, nodeTypeColorMap, state.nodeDataCache]);

    // Handle node selection
    const handleNodeSelection = useCallback(async (e, node) => {
        const isCtrlPressed = e.ctrlKey || e.metaKey;
        const isSelected = state.selectedNodes.includes(node.id);
        
        let newSelection;
        if (isCtrlPressed) {
            newSelection = isSelected
                ? state.selectedNodes.filter(id => id !== node.id)
                : [...state.selectedNodes, node.id];
        } else {
            newSelection = [node.id];
        }

        dispatch({
            type: ACTION_TYPES.SELECT_NODE,
            payload: {
                nodeId: node.id,
                isCtrlPressed,
                activeContext,
                graphAttributes,
                nodesWithChildren,
                nodeTypeColorMap
            }
        });

        // Handle model node display
        const nodeName = newSelection[0];
        const modelNodeName = `${modelName}_node`;
        const nodeActions = sliceMap[modelNodeName]?.actions;
        if (newSelection.length === 1) {
            reduxDispatch(nodeActions.setNode({
                modelName: nodeName,
                modelSchema: getModelSchema(nodeName, projectSchema),
                fieldsMetadata: schemaCollections[nodeName],
                url: API_ROOT_URL
            }));
        } else {
            reduxDispatch(nodeActions.setNode(null));
        }

        if (newSelection.length === 2 && mode === MODES.EDIT) {
            prepareAndOpenModal(newSelection[0], newSelection[1]);
        }

        // Fetch node data if needed
        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const selectedNode = contextNodes.find(n => get(n, graphAttributes.nodeNameField) === node.id);
        const hasChildren = nodesWithChildren.has(node.id);
        const isExpanded = !hasChildren || (hasChildren && state.expandedNodes.has(node.id));

        if (selectedNode && isExpanded) {
            const nodeName = get(selectedNode, graphAttributes.nodeNameField);
            if (!state.nodeDataCache[nodeName] && !getCachedNodeData(nodeName)) {
                try {
                    const nodeData = await fetchNodeData(selectedNode);
                    dispatch({
                        type: ACTION_TYPES.CACHE_NODE_DATA,
                        payload: { nodeId: nodeName, data: nodeData }
                    });
                } catch (error) {
                    console.error(`Failed to fetch data for node: ${nodeName}`, error);
                }
            }
        }
    }, [activeContext, state.selectedNodes, state.expandedNodes, state.nodeDataCache, nodesWithChildren, 
        graphAttributes, nodeTypeColorMap, mode, modelName, projectSchema, schemaCollections, 
        reduxDispatch, prepareAndOpenModal]);

    // Handle node double click (expand/collapse)
    const handleNodeDoubleClick = useCallback((_, node) => {
        if (!activeContext) return;

        const childrenIds = nodesWithChildren.get(node.id) || [];
        const isExpanded = state.expandedNodes.has(node.id);

        if (childrenIds.size > 0) {
            if (isExpanded) {
                const descendants = getNodeDescendants(node.id, nodesWithChildren);
                dispatch({
                    type: ACTION_TYPES.COLLAPSE_NODE,
                    payload: {
                        nodeId: node.id,
                        descendants,
                        activeContext,
                        graphAttributes,
                        nodesWithChildren,
                        nodeTypeColorMap
                    }
                });
            } else {
                dispatch({
                    type: ACTION_TYPES.EXPAND_NODE,
                    payload: {
                        nodeId: node.id,
                        children: childrenIds,
                        activeContext,
                        graphAttributes,
                        nodesWithChildren,
                        nodeTypeColorMap
                    }
                });
            }
        }
    }, [activeContext, state.expandedNodes, nodesWithChildren, getNodeDescendants, 
        graphAttributes, nodeTypeColorMap]);

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

        if (!activeContext || !reduxDispatch) return;

        if (updatedEdges === null) {
            console.log('No join changes needed - maintaining current state');
            return;
        }

        const sourceName = get(sourceNode, graphAttributes.nodeNameField);
        const targetName = get(targetNode, graphAttributes.nodeNameField);

        const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];
        const otherEdges = contextEdges.filter(edge => {
            const baseNode = get(edge, graphAttributes.edgeBaseField);
            const targetNodeField = get(edge, graphAttributes.edgeTargetField);
            return !((baseNode === sourceName && targetNodeField === targetName) ||
                (baseNode === targetName && targetNodeField === sourceName));
        });

        const newCompleteEdgesArray = [...otherEdges, ...updatedEdges];

        const updatedContext = cloneDeep(activeContext);
        set(updatedContext, graphAttributes.edgesPath, newCompleteEdgesArray);

        const updatedData = cloneDeep(updatedObj);
        const contexts = get(updatedData, graphAttributes.contextPath) || [];
        const contextIndex = contexts.findIndex((o) => o[DB_ID] === activeContext[DB_ID]);
        if (contextIndex !== -1) {
            contexts.splice(contextIndex, 1, updatedContext);
        }
        reduxDispatch(actions.setUpdatedObj(updatedData));
        
        // Update computed nodes and edges with new context
        dispatch({
            type: ACTION_TYPES.UPDATE_NODES_AND_EDGES,
            payload: {
                activeContext: updatedContext,
                graphAttributes,
                nodesWithChildren,
                nodeTypeColorMap
            }
        });
    }, [activeContext, reduxDispatch, updatedObj, graphAttributes, actions, nodesWithChildren, nodeTypeColorMap]);

    // Handle edge click
    const handleEdgeClick = useCallback(async (event, edge) => {
        const isAnalyzeClick = event.target.textContent === 'Analyze' ||
            event.target.closest('[class*="nodrag nopan"]')?.textContent?.includes('Analyze');

        if (isAnalyzeClick) {
            await handleAnalyse(edge.id, edge.data);
            return;
        }

        if (mode !== MODES.EDIT) return;

        const { sourceNode, targetNode } = edge.data;

        if (sourceNode && targetNode) {
            const sourceName = get(sourceNode, graphAttributes.nodeNameField);
            const targetName = get(targetNode, graphAttributes.nodeNameField);
            prepareAndOpenModal(sourceName, targetName);
        }
    }, [mode, graphAttributes, handleAnalyse, prepareAndOpenModal]);

    // Handle node selector change
    const handleNodeSelectorChange = (selectedOptions) => {
        function trimLastPath(xpath) {
            return xpath?.substring(0, Math.max(xpath.lastIndexOf("."), xpath.lastIndexOf("]")));
        }

        const newNodes = new Set();

        const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
        const updatedNodes = selectedOptions.map(option => {
            const existingNode = contextNodes.find(node =>
                get(node, graphAttributes.nodeNameField) === get(option, graphAttributes.nodeNameField)
            );

            if (existingNode) {
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
            return newObject;
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
        reduxDispatch(actions.setUpdatedObj(updatedData));
        
        // Update visible nodes and recompute
        const filteredVisibleNodes = new Set(
            [...state.visibleNodes].filter(nodeId => nodesSet.has(nodeId))
        );
        newNodes.forEach(nodeId => filteredVisibleNodes.add(nodeId));
        
        dispatch({
            type: ACTION_TYPES.SET_VISIBLE_NODES,
            payload: {
                visibleNodes: filteredVisibleNodes,
                activeContext: updatedContext,
                graphAttributes,
                nodesWithChildren,
                nodeTypeColorMap
            }
        });
    };

    const availableNodes = useMemo(() => projectSchema.autocomplete['EntityNType_List'] || [], [projectSchema]);

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
                                disabled={state.selectedNodes.length !== 2 || mode === MODES.READ}
                                onClick={() => {
                                    if (state.selectedNodes.length === 2) {
                                        prepareAndOpenModal(state.selectedNodes[0], state.selectedNodes[1]);
                                    }
                                }}
                            >
                                Configure ({state.selectedNodes.length}/2)
                            </Button>
                            <Tooltip title="Clear Selection">
                                <span>
                                    <IconButton
                                        size="small"
                                        onClick={() => {
                                            dispatch({
                                                type: ACTION_TYPES.CLEAR_SELECTION,
                                                payload: {
                                                    activeContext,
                                                    graphAttributes,
                                                    nodesWithChildren,
                                                    nodeTypeColorMap
                                                }
                                            });
                                        }}
                                        disabled={state.selectedNodes.length === 0}
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
            {state.modalOpen && state.modalNodes.source && state.modalNodes.target && (
                <DataJoinPopup
                    open={state.modalOpen}
                    onClose={() => dispatch({ type: ACTION_TYPES.CLOSE_MODAL })}
                    sourceNode={state.modalNodes.source}
                    targetNode={state.modalNodes.target}
                    existingJoins={getNodePairEdges(
                        get(state.modalNodes.source, graphAttributes.nodeNameField),
                        get(state.modalNodes.target, graphAttributes.nodeNameField)
                    )}
                    onSave={handleModalSave}
                    graphAttributes={graphAttributes}
                    fieldsMetadata={fieldsMetadata}
                />
            )}
        </>
    );
};

DataJoinGraph.propTypes = {
    modelName: PropTypes.string.isRequired,
    modelDataSource: PropTypes.shape({
        selector: PropTypes.func.isRequired,
        actions: PropTypes.object.isRequired,
        fieldsMetadata: PropTypes.array.isRequired
    }).isRequired
};

export default React.memo(DataJoinGraph);