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
import CloseIcon from '@mui/icons-material/Close';
import {
    ReactFlow,
    Controls,
    Background,
    Handle,
    Position,
    applyNodeChanges,
    applyEdgeChanges
} from '@xyflow/react';
import DataJoinPopup from '../DataJoinPopup/DataJoinPopup';
import CustomEdge from '../Edges/CustomEdge';
import NodeSelector from '../NodeSelector';
import { fetchNodeData, getCachedNodeData, fetchAnalysedData } from '../../../../services/GraphNodeService';
import { sliceMap } from '../../../../models/sliceMap';
import { DB_ID, MODES } from '../../../../constants';
import { generateObjectFromSchema, getModelSchema, snakeToCamel } from '../../../../utils';
import { getJoinColor, createColorMapFromString, getNodeTypeColor } from '../../../../utils/ui/colorUtils';
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

// Helper function to calculate nodes
const calculateNodes = (params) => {
    const {
        activeContext,
        graphAttributes,
        selectedNodes,
        visibleNodes,
        nodesWithChildren,
        nodeTypeColorMap,
        existingNodes = []
    } = params;

    if (!activeContext) return [];

    // Create a map of existing positions
    const existingPositions = {};
    existingNodes.forEach(node => {
        existingPositions[node.id] = node.position;
    });

    const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];

    const allNodes = contextNodes.map((node, index) => {
        const nodeName = get(node, graphAttributes.nodeNameField);

        // Use existing position if available, otherwise calculate new position
        const position = existingPositions[nodeName] || {
            x: (index % 3) * 300 + 100,
            y: Math.floor(index / 3) * 250 + 100
        };

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
            position,
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

    // Filter based on visible nodes
    return allNodes.filter(node => visibleNodes.has(node.id));
};

// Helper function to calculate edges
const calculateEdges = (params) => {
    const {
        activeContext,
        graphAttributes,
        selectedAnalyzeButton,
        visibleNodes,
        joinTypeColorMapping,
        theme
    } = params;

    if (!activeContext) return [];

    const contextNodes = get(activeContext, graphAttributes.nodesPath) || [];
    const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];

    const allEdges = contextEdges.map((edge, index) => {
        const edgePairs = get(edge, graphAttributes.edgePairsField) || [];

        // Check if any pairs are AI suggestions that haven't been confirmed
        const hasUnconfirmedAiSuggestions = edgePairs.some(p =>
            get(p, graphAttributes.edgeAiSuggestedField) === true &&
            get(p, graphAttributes.edgeConfirmedField) === false
        );

        // For rendering: AI suggestions (ai_suggested=true, user_confirmed=false) should appear in light color
        const isConfirmed = !hasUnconfirmedAiSuggestions;

        const edgeType = get(edge, graphAttributes.edgeTypeField);
        const baseNode = get(edge, graphAttributes.edgeBaseField);
        const targetNode = get(edge, graphAttributes.edgeTargetField);
        const color = getJoinColor(edgeType, joinTypeColorMapping, theme, isConfirmed);
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
    return allEdges.filter(edge =>
        visibleNodes.has(edge.source) && visibleNodes.has(edge.target)
    );
};

// Initial state factory
const createInitialState = () => ({
    selectedNodes: [],
    selectedAnalyzeButton: null,
    nodeDataCache: {},
    visibleNodes: new Set(),
    expandedNodes: new Set(),
    nodes: [],
    edges: [],
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
    UPDATE_GRAPH: 'UPDATE_GRAPH',
    CLEAR_SELECTION: 'CLEAR_SELECTION',
    NODES_CHANGE: 'NODES_CHANGE',
    EDGES_CHANGE: 'EDGES_CHANGE'
};

// Main reducer function
const graphReducer = (state, action) => {
    switch (action.type) {
        case ACTION_TYPES.RESET_STATE: {
            return createInitialState();
        }

        case ACTION_TYPES.INITIALIZE: {
            const { rootNodeIds, ...params } = action.payload;

            const nodes = calculateNodes({
                ...params,
                selectedNodes: [],
                visibleNodes: rootNodeIds,
                existingNodes: []
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: null,
                visibleNodes: rootNodeIds
            });

            return {
                ...state,
                visibleNodes: rootNodeIds,
                expandedNodes: new Set(),
                nodes,
                edges
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

            const nodes = calculateNodes({
                ...params,
                selectedNodes: newSelectedNodes,
                visibleNodes: state.visibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: null,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedNodes: newSelectedNodes,
                selectedAnalyzeButton: null,
                nodes,
                edges
            };
        }

        case ACTION_TYPES.SELECT_ANALYZE_BUTTON: {
            const { edgeId, ...params } = action.payload;

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: edgeId,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedAnalyzeButton: edgeId,
                edges
            };
        }

        case ACTION_TYPES.EXPAND_NODE: {
            const { nodeId, children, ...params } = action.payload;
            const newVisibleNodes = new Set([...state.visibleNodes, ...children]);
            const newExpandedNodes = new Set([...state.expandedNodes, nodeId]);

            const nodes = calculateNodes({
                ...params,
                selectedNodes: state.selectedNodes,
                visibleNodes: newVisibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: newVisibleNodes
            });

            return {
                ...state,
                visibleNodes: newVisibleNodes,
                expandedNodes: newExpandedNodes,
                nodes,
                edges
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

            const nodes = calculateNodes({
                ...params,
                selectedNodes: newSelectedNodes,
                visibleNodes: newVisibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: newVisibleNodes
            });

            return {
                ...state,
                selectedNodes: newSelectedNodes,
                visibleNodes: newVisibleNodes,
                expandedNodes: newExpandedNodes,
                nodes,
                edges
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

            const nodes = calculateNodes({
                ...params,
                selectedNodes: state.selectedNodes,
                visibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes
            });

            return {
                ...state,
                visibleNodes,
                nodes,
                edges
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

        case ACTION_TYPES.UPDATE_GRAPH: {
            const { ...params } = action.payload;

            const nodes = calculateNodes({
                ...params,
                selectedNodes: state.selectedNodes,
                visibleNodes: state.visibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: state.selectedAnalyzeButton,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                nodes,
                edges
            };
        }

        case ACTION_TYPES.CLEAR_SELECTION: {
            const { ...params } = action.payload;

            const nodes = calculateNodes({
                ...params,
                selectedNodes: [],
                visibleNodes: state.visibleNodes,
                existingNodes: state.nodes
            });

            const edges = calculateEdges({
                ...params,
                selectedAnalyzeButton: null,
                visibleNodes: state.visibleNodes
            });

            return {
                ...state,
                selectedNodes: [],
                selectedAnalyzeButton: null,
                nodes,
                edges
            };
        }

        case ACTION_TYPES.NODES_CHANGE: {
            const { changes } = action.payload;
            return {
                ...state,
                nodes: applyNodeChanges(changes, state.nodes)
            };
        }

        case ACTION_TYPES.EDGES_CHANGE: {
            const { changes } = action.payload;
            return {
                ...state,
                edges: applyEdgeChanges(changes, state.edges)
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
    const { contextId } = useSelector(state => state[snakeToCamel(modelName)]);
    const reduxDispatch = useDispatch();

    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';
    const isInitializedRef = useRef(false);

    // Initialize reducer
    const [state, dispatch] = useReducer(graphReducer, createInitialState());

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

        const nodeMetaQuerySchemaName = nodesMeta?.node_meta_query;
        const nodeMetaQueryName = 'query-' + nodeMetaQuerySchemaName;

        const edgeMetaQuerySchemaName = edgesMeta?.edge_meta_query;
        const edgeMetaQueryName = 'query-' + edgeMetaQuerySchemaName;

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
            nodeMetaQueryName,
            nodeMetaParamName: 'entity_name',
            edgeMetaQueryName,
            edgeMetaParamName: 'join_configuration',
            nodeSelectedFieldsField: 'field_selections',
            edgeBaseField: 'base_entity_selection.entity_name',
            edgeTargetField: 'join_entity_selection.entity_name',
            edgeTypeField: 'join_type',
            edgePairsField: 'join_pairs',
            edgeConfirmedField: 'user_confirmed',
            edgeAiSuggestedField: 'ai_suggested',
            edgeFilterOperator: 'filter_operator'
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

    const joinTypeColorMapping = useMemo(() => {
        const joinTypeMeta = fieldsMetadata.find(f => f.key === graphAttributes.edgeTypeField);
        return joinTypeMeta?.color || '';
    }, [fieldsMetadata, graphAttributes.edgeTypeField]);

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

        const payload = {
            activeContext,
            graphAttributes,
            nodesWithChildren,
            nodeTypeColorMap,
            joinTypeColorMapping,
            theme
        };

        if (mode === MODES.READ) {
            if (!isInitializedRef.current) {
                dispatch({
                    type: ACTION_TYPES.INITIALIZE, payload: {
                        ...payload,
                        rootNodeIds,
                    }
                });
                isInitializedRef.current = true;
            } else {
                // In READ mode, always update when context changes
                dispatch({ type: ACTION_TYPES.UPDATE_GRAPH, payload });
            }
        } else if (mode === MODES.EDIT) {
            if (!isInitializedRef.current) {
                dispatch({
                    type: ACTION_TYPES.INITIALIZE, payload: {
                        ...payload,
                        rootNodeIds,
                    }
                });
                isInitializedRef.current = true;
            }
        }
    }, [mode, activeContext, contextId, rootNodeIds, graphAttributes, nodesWithChildren, nodeTypeColorMap, joinTypeColorMapping, theme]);

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
                sourceNodeData = await fetchNodeData(graphAttributes.nodeMetaQueryName, graphAttributes.nodeMetaParamName, sourceNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: nodeName1, data: sourceNodeData }
                });
            }

            if (!targetNodeData) {
                console.log(`Cache miss for ${nodeName2}. Fetching...`);
                targetNodeData = await fetchNodeData(graphAttributes.nodeMetaQueryName, graphAttributes.nodeMetaParamName, targetNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: nodeName2, data: targetNodeData }
                });
            }
        } catch (error) {
            console.error('Failed to fetch node data for modal:', error);
            return;
        }

        const sourceNodeWithColumns = { ...sourceNode, columns: sourceNodeData?.nodeColumns || [] };
        const targetNodeWithColumns = { ...targetNode, columns: targetNodeData?.nodeColumns || [] };

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
                    nodeTypeColorMap,
                    joinTypeColorMapping,
                    theme
                }
            });

            const { sourceNode, targetNode, edgeInfo } = edgeData;

            if (!sourceNode || !targetNode) {
                console.error('Missing node information for analysis');
                return;
            }

            const sourceName = get(sourceNode, graphAttributes.nodeNameField);
            const targetName = get(targetNode, graphAttributes.nodeNameField);

            // Fetch source node data
            let sourceNodeData = state.nodeDataCache[sourceName] || getCachedNodeData(sourceName);
            if (!sourceNodeData) {
                sourceNodeData = await fetchNodeData(graphAttributes.nodeMetaQueryName, graphAttributes.nodeMetaParamName, sourceNode);
                dispatch({
                    type: ACTION_TYPES.CACHE_NODE_DATA,
                    payload: { nodeId: sourceName, data: sourceNodeData }
                });
            }

            // Fetch target node data (commented out for now)
            // let targetNodeData = state.nodeDataCache[targetName] || getCachedNodeData(targetName);
            // if (!targetNodeData) {
            //     targetNodeData = await fetchNodeData(graphAttributes.nodeMetaQueryName, graphAttributes.nodeMetaParamName, targetNode);
            //     dispatch({
            //         type: ACTION_TYPES.CACHE_NODE_DATA,
            //         payload: { nodeId: targetName, data: targetNodeData }
            //     });
            // }

            // Dispatch source node data to Redux 
            const modelNodeName = `${modelName}_node`;
            const nodeActions = sliceMap[modelNodeName]?.actions;
            const { nodeSchema, nodeProjectSchema, nodeData: nodeSampleData, nodeUrl, nodeFieldsMetadata } = sourceNodeData;
            reduxDispatch(nodeActions.setNode({
                modelName: sourceName,
                modelSchema: nodeSchema,
                projectSchema: nodeProjectSchema,
                fieldsMetadata: nodeFieldsMetadata,
                url: nodeUrl
            }));
            reduxDispatch(nodeActions.setStoredArray(nodeSampleData || []));

        } catch (error) {
            console.error('Analysis error:', error);
            console.error(`Analysis failed: ${error.message}`);
        }
    }, [activeContext, graphAttributes, nodesWithChildren, nodeTypeColorMap, joinTypeColorMapping, theme, state.nodeDataCache, reduxDispatch]);

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
                nodeTypeColorMap,
                joinTypeColorMapping,
                theme
            }
        });

        // Handle model node display
        const nodeName = newSelection[0];
        const modelNodeName = `${modelName}_node`;
        const nodeActions = sliceMap[modelNodeName]?.actions;
        if (newSelection.length !== 1) {
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

        if (selectedNode) {  //  && isExpanded
            const nodeName = get(selectedNode, graphAttributes.nodeNameField);
            if (!state.nodeDataCache[nodeName] && !getCachedNodeData(nodeName)) {
                try {
                    const nodeData = await fetchNodeData(graphAttributes.nodeMetaQueryName, graphAttributes.nodeMetaParamName, selectedNode);
                    dispatch({
                        type: ACTION_TYPES.CACHE_NODE_DATA,
                        payload: { nodeId: nodeName, data: nodeData }
                    });
                    if (newSelection.length === 1) {
                        const { nodeSchema, nodeProjectSchema, nodeData: nodeSampleData, nodeUrl, nodeFieldsMetadata } = nodeData;
                        reduxDispatch(nodeActions.setNode({
                            modelName: nodeName,
                            modelSchema: nodeSchema,
                            projectSchema: nodeProjectSchema,
                            fieldsMetadata: nodeFieldsMetadata,
                            url: nodeUrl
                        }));
                        reduxDispatch(nodeActions.setStoredArray(nodeSampleData || []));
                    }
                } catch (error) {
                    console.error(`Failed to fetch data for node: ${nodeName}`, error);
                }
            } else {
                if (newSelection.length === 1) {
                    const nodeData = state.nodeDataCache[nodeName];
                    const { nodeSchema, nodeProjectSchema, nodeData: nodeSampleData, nodeUrl, nodeFieldsMetadata } = nodeData;
                    reduxDispatch(nodeActions.setNode({
                        modelName: nodeName,
                        modelSchema: nodeSchema,
                        projectSchema: nodeProjectSchema,
                        fieldsMetadata: nodeFieldsMetadata,
                        url: nodeUrl
                    }));
                    reduxDispatch(nodeActions.setStoredArray(nodeSampleData || []));
                }
            }
        }
    }, [activeContext, state.selectedNodes, state.expandedNodes, state.nodeDataCache, nodesWithChildren,
        graphAttributes, nodeTypeColorMap, joinTypeColorMapping, theme, mode, modelName, projectSchema, schemaCollections,
        reduxDispatch, prepareAndOpenModal]);

    // Handle node double click (expand/collapse)
    const handleNodeDoubleClick = useCallback((_, node) => {
        if (!activeContext) return;

        const childrenIds = nodesWithChildren.get(node.id) || [];
        const isExpanded = state.expandedNodes.has(node.id);

        const payload = {
            activeContext,
            graphAttributes,
            nodesWithChildren,
            nodeTypeColorMap,
            joinTypeColorMapping,
            theme
        };

        if (childrenIds.size > 0) {
            if (isExpanded) {
                const descendants = getNodeDescendants(node.id, nodesWithChildren);
                dispatch({
                    type: ACTION_TYPES.COLLAPSE_NODE,
                    payload: { ...payload, nodeId: node.id, descendants }
                });
            } else {
                dispatch({
                    type: ACTION_TYPES.EXPAND_NODE,
                    payload: { ...payload, nodeId: node.id, children: childrenIds }
                });
            }
        }
    }, [activeContext, state.expandedNodes, nodesWithChildren, getNodeDescendants,
        graphAttributes, nodeTypeColorMap, joinTypeColorMapping, theme]);


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
        if (!activeContext || !reduxDispatch) return;

        const sourceName = get(state.modalNodes.source, graphAttributes.nodeNameField);
        const targetName = get(state.modalNodes.target, graphAttributes.nodeNameField);

        if (!sourceName || !targetName) {
            return;
        }

        const contextEdges = get(activeContext, graphAttributes.edgesPath) || [];
        let newCompleteEdgesArray;

        // saveData is the updatedJoinObject from the popup
        const updatedJoin = saveData;

        // CASE 1: DELETE - when no join pairs are left
        if (updatedJoin.join_pairs.length === 0) {

            // Find if a connection already exists
            const existingEdgeIndex = contextEdges.findIndex(edge => {
                const baseNode = get(edge, graphAttributes.edgeBaseField);
                const targetNodeField = get(edge, graphAttributes.edgeTargetField);
                return ((baseNode === sourceName && targetNodeField === targetName) ||
                    (baseNode === targetName && targetNodeField === sourceName));
            });

            //  If no connection existed, do nothing.
            if (existingEdgeIndex === -1) {
                newCompleteEdgesArray = contextEdges; // Array remains unchanged
            } else {
                // If connection existed, delete it using splice.
                // TO ask: mutation ? 

                const clonedEdges = cloneDeep(contextEdges);
                clonedEdges.splice(existingEdgeIndex, 1); // Deletes 1 element at the found index

                newCompleteEdgesArray = clonedEdges;
            }

        } else { // CASE 2: ADD/UPDATE
            //Find if a connection already exists 
            const existingEdgeIndex = contextEdges.findIndex(edge => {
                const baseNode = get(edge, graphAttributes.edgeBaseField);
                const targetNodeField = get(edge, graphAttributes.edgeTargetField);
                return ((baseNode === sourceName && targetNodeField === targetName) ||
                    (baseNode === targetName && targetNodeField === sourceName));
            })

            const clonedEdges = cloneDeep(contextEdges);
            if (existingEdgeIndex !== -1) {
                //join exists 
                clonedEdges.splice(existingEdgeIndex, 1, updatedJoin);

            }
            else {
                //new one 
                clonedEdges.push(updatedJoin)
            }
            newCompleteEdgesArray = clonedEdges;
        }

        const updatedContext = cloneDeep(activeContext);
        set(updatedContext, graphAttributes.edgesPath, newCompleteEdgesArray);

        const updatedData = cloneDeep(updatedObj);
        const contexts = get(updatedData, graphAttributes.contextPath) || [];
        const contextIndex = contexts.findIndex((o) => o[DB_ID] === activeContext[DB_ID]);
        if (contextIndex !== -1) {
            contexts.splice(contextIndex, 1, updatedContext);
        }
        reduxDispatch(actions.setUpdatedObj(updatedData));

        const newNodesWithChildren = new Map();
        const currentEdges = get(updatedContext, graphAttributes.edgesPath) || []
        currentEdges.forEach(edge => {
            const baseNode = get(edge, graphAttributes.edgeBaseField)
            const targetNode = get(edge, graphAttributes.edgeTargetField);
            if (!newNodesWithChildren.has(baseNode)) {
                newNodesWithChildren.set(baseNode, new Set());
            }
            newNodesWithChildren.get(baseNode).add(targetNode);
        });

        dispatch({
            type: ACTION_TYPES.UPDATE_GRAPH,
            payload: {
                activeContext: updatedContext,
                graphAttributes,
                nodesWithChildren: newNodesWithChildren,
                nodeTypeColorMap,
                joinTypeColorMapping,
                theme
            }
        });
    }, [activeContext, reduxDispatch, updatedObj, graphAttributes, actions, nodesWithChildren, nodeTypeColorMap, joinTypeColorMapping, theme, state.modalNodes]);

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
                nodeTypeColorMap,
                joinTypeColorMapping,
                theme
            }
        });
    };

    // Handle ReactFlow node changes (dragging, etc.)
    const handleNodesChange = useCallback((changes) => {
        dispatch({
            type: ACTION_TYPES.NODES_CHANGE,
            payload: { changes }
        });
    }, []);

    // Handle ReactFlow edge changes
    const handleEdgesChange = useCallback((changes) => {
        dispatch({
            type: ACTION_TYPES.EDGES_CHANGE,
            payload: { changes }
        });
    }, []);

    const availableNodes = useMemo(() => projectSchema.autocomplete['EntityNType_List'] || [], [projectSchema]);

    const joinColorMapForLegend = useMemo(() => {
        return createColorMapFromString(joinTypeColorMapping);
    }, [joinTypeColorMapping]);

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
                            nodes={state.nodes}
                            edges={state.edges}
                            onNodesChange={handleNodesChange}
                            onEdgesChange={handleEdgesChange}
                            onNodeClick={handleNodeSelection}
                            onNodeDoubleClick={handleNodeDoubleClick}
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
                                    color: "#808080 !important"

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
                                                    nodeTypeColorMap,
                                                    joinTypeColorMapping,
                                                    theme
                                                }
                                            });
                                        }}
                                        disabled={state.selectedNodes.length === 0}
                                    >
                                        <CloseIcon fontSize="small" />
                                    </IconButton>
                                </span>
                            </Tooltip>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, flexWrap: 'wrap' }}>
                            {Object.entries(joinColorMapForLegend).map(([joinType, schemaColor]) => {
                                if (joinType === 'JOIN_TYPE_UNSPECIFIED') return null;
                                const color = getNodeTypeColor(schemaColor, theme)?.main;
                                if (!color) return null;
                                return (
                                    <React.Fragment key={joinType}>
                                        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                                            {joinType.replace('_', ' ').toLowerCase()}:
                                        </Typography>
                                        <Box sx={{ width: 20, height: 2, bgcolor: color }} />
                                    </React.Fragment>
                                );
                            })}
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
            {state.modalOpen && state.modalNodes.source && state.modalNodes.target && (() => {
                const existingJoins = getNodePairEdges(
                    get(state.modalNodes.source, graphAttributes.nodeNameField),
                    get(state.modalNodes.target, graphAttributes.nodeNameField)
                );

                const existingJoin = existingJoins.length > 0 ? existingJoins[0] : null;
                const joinTypeOptions = fieldsMetadata?.find(field => field.key === graphAttributes.edgeTypeField)?.autocomplete_list || [];
                const filterOperators = fieldsMetadata?.find(field => field.key === graphAttributes.edgeFilterOperator)?.autocomplete_list;

                return (
                    <DataJoinPopup
                        open={state.modalOpen}
                        onClose={() => dispatch({ type: ACTION_TYPES.CLOSE_MODAL })}
                        sourceNode={state.modalNodes.source}
                        targetNode={state.modalNodes.target}
                        existingJoin={existingJoin}
                        onSave={handleModalSave}
                        graphAttributes={graphAttributes}
                        metadata={{
                            joinTypeOptions,
                            filterOperators,
                            joinTypeColorMapping
                        }}
                    />
                );
            })()}
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