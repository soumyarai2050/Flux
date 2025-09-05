import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import PropTypes from 'prop-types';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Box,
    Typography,
    Button,
    IconButton,
    Chip,
    Divider,
    Checkbox,
    FormControlLabel,
    Select,
    MenuItem,
    FormControl,
    useTheme
} from '@mui/material';
import {
    Close,
    Delete,
    Check,
    Clear
} from '@mui/icons-material';
import {
    ReactFlow,
    useNodesState,
    useEdgesState,
    Handle,
    Position,
    Controls,
    Background
} from '@xyflow/react';
import { getJoinColor } from '../../../../utils/ui/colorUtils';
import ColumnList from './ColumnList';

const TableCardNode = React.memo(({ data }) => {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const {
        label,
        selectedColumns,
        confirmedConnections,
        aiSuggestions,
        onColumnClick,
        selectedColumn,
        isSource,
        onAcceptAi,
        onRejectAi
    } = data;

    return (
        <Box
            style={{
                width: '300px',
                maxHeight: '350px',
                background: isDarkMode ? theme.palette.grey[800] : theme.palette.background.paper,
                border: `2px solid ${theme.palette.primary.main}`,
                borderRadius: '8px',
                overflow: 'hidden',
                boxShadow: isDarkMode
                    ? '0 4px 12px rgba(255, 255, 255, 0.1)'
                    : '0 4px 12px rgba(59, 130, 246, 0.2)'
            }}
        >
            {/* Header */}
            <Box
                style={{
                    background: theme.palette.primary.main,
                    color: theme.palette.primary.contrastText,
                    padding: '8px',
                    textAlign: 'center'
                }}
            >
                <Typography variant="subtitle1" style={{ fontWeight: 600 }}>
                    {label}
                </Typography>
            </Box>

            {/* Columns Display */}
            <Box style={{ padding: '12px', minHeight: '100px', maxHeight: '280px', overflow: 'auto' }}>
                {/* Selected Columns (from bottom checkboxes) */}
                {selectedColumns?.map((columnName, idx) => {
                    const connection = confirmedConnections.find(conn =>
                        (isSource && conn.sourceColumn === columnName) ||
                        (!isSource && conn.targetColumn === columnName)
                    );
                    const isConnected = !!connection;

                    // Check if this column is part of an AI suggestion
                    const hasAiSuggestion = aiSuggestions.some(suggestion =>
                        (isSource && suggestion.sourceColumn === columnName) ||
                        (!isSource && suggestion.targetColumn === columnName)
                    );

                    const isSelected = selectedColumn === columnName;

                    // Skip rendering if this column is part of an AI suggestion (it will be rendered separately)
                    if (hasAiSuggestion && !isConnected) {
                        return null;
                    }

                    if (isConnected) {
                        // Show connected column
                        return (
                            <Box
                                key={`connected-${idx}`}
                                style={{
                                    margin: '4px 0',
                                    padding: '8px',
                                    backgroundColor: isDarkMode
                                        ? theme.palette.success.dark + '30'
                                        : theme.palette.success.light + '30',
                                    borderRadius: '6px',
                                    border: `2px solid ${theme.palette.success.main}`,
                                    position: 'relative'
                                }}
                            >
                                <Handle
                                    type="source"
                                    position={Position.Right}
                                    id={`${label}-${columnName}-source`}
                                    style={{ opacity: 0, pointerEvents: 'none' }}
                                />
                                <Handle
                                    type="target"
                                    position={Position.Left}
                                    id={`${label}-${columnName}-target`}
                                    style={{ opacity: 0, pointerEvents: 'none' }}
                                />
                                <Box display="flex" alignItems="center" justifyContent="space-between">
                                    <Box flex={1}>
                                        <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                                            <Typography variant="body2" style={{ fontWeight: 600 }}>
                                                {columnName}
                                            </Typography>
                                            <Chip
                                                label="CONNECTED"
                                                size="small"
                                                style={{
                                                    backgroundColor: '#4CAF50',
                                                    color: 'white',
                                                    height: '18px',
                                                    fontSize: '10px'
                                                }}
                                            />
                                        </Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Join: {connection.joinType}
                                        </Typography>
                                    </Box>
                                    <IconButton
                                        size="small"
                                        onClick={() => data.onDeleteConnection?.(connection.id)}
                                        title="Delete connection"
                                        style={{ width: '24px', height: '24px' }}
                                    >
                                        <Delete style={{ fontSize: '14px', color: '#f44336' }} />
                                    </IconButton>
                                </Box>
                            </Box>
                        );
                    } else {
                        // Show selectable column
                        return (
                            <Box
                                key={`selectable-${idx}`}
                                style={{
                                    margin: '4px 0',
                                    padding: '8px',
                                    backgroundColor: isSelected
                                        ? (isDarkMode ? theme.palette.primary.dark : theme.palette.primary.light)
                                        : (isDarkMode ? theme.palette.grey[700] : theme.palette.action.hover),
                                    borderRadius: '6px',
                                    border: isSelected
                                        ? `2px solid ${theme.palette.primary.main}`
                                        : `1px solid ${isDarkMode ? theme.palette.grey[600] : theme.palette.primary.light}`,
                                    position: 'relative',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease'
                                }}
                                onClick={() => onColumnClick?.(columnName, isSource)}
                                title="Click to create manual connection"
                            >
                                <Handle
                                    type="source"
                                    position={Position.Right}
                                    id={`${label}-${columnName}-source`}
                                    style={{ opacity: 0, pointerEvents: 'none' }}
                                />
                                <Handle
                                    type="target"
                                    position={Position.Left}
                                    id={`${label}-${columnName}-target`}
                                    style={{ opacity: 0, pointerEvents: 'none' }}
                                />
                                <Typography variant="body2" style={{ fontWeight: 600 }}>
                                    {columnName}
                                    <Chip
                                        label={isSelected ? "CLICK TARGET" : "SELECTED"}
                                        size="small"
                                        color={isSelected ? "secondary" : "primary"}
                                        style={{ marginLeft: '8px', height: '18px', fontSize: '10px' }}
                                    />
                                </Typography>
                            </Box>
                        );
                    }
                })}

                {/* AI Suggestions */}
                {aiSuggestions?.filter(suggestion =>
                    (isSource && suggestion.sourceColumn) || (!isSource && suggestion.targetColumn)
                ).map((suggestion, idx) => {
                    const columnName = isSource ? suggestion.sourceColumn : suggestion.targetColumn;
                    const isColumnSelected = selectedColumns.includes(columnName);

                    // Only show if the column is selected in bottom panel
                    if (!isColumnSelected) return null;

                    return (
                        <Box
                            key={`ai-${idx}`}
                            style={{
                                margin: '4px 0',
                                padding: '8px',
                                backgroundColor: isDarkMode
                                    ? theme.palette.warning.dark + '20'
                                    : theme.palette.warning.light + '40',
                                borderRadius: '6px',
                                border: `1px dashed ${theme.palette.warning.main}`,
                                position: 'relative'
                            }}
                        >
                            <Handle
                                type="source"
                                position={Position.Right}
                                id={`${label}-${columnName}-source`}
                                style={{ opacity: 0, pointerEvents: 'none' }}
                            />
                            <Handle
                                type="target"
                                position={Position.Left}
                                id={`${label}-${columnName}-target`}
                                style={{ opacity: 0, pointerEvents: 'none' }}
                            />
                            <Box display="flex" alignItems="center" justifyContent="space-between">
                                <Box flex={1} display="flex" alignItems="center" gap={1}>
                                    <Typography variant="body2" style={{ fontWeight: 600 }}>
                                        {columnName}
                                    </Typography>
                                    <Chip
                                        label="AI SUGGESTION"
                                        size="small"
                                        style={{
                                            backgroundColor: '#FF9800',
                                            color: 'white',
                                            height: '16px',
                                            fontSize: '9px'
                                        }}
                                    />
                                </Box>
                                <Box display="flex" gap={0.5}>
                                    <IconButton
                                        size="small"
                                        onClick={() => onAcceptAi?.(suggestion.id)}
                                        style={{
                                            backgroundColor: '#4CAF50',
                                            color: 'white',
                                            width: '24px',
                                            height: '24px'
                                        }}
                                        title="Accept AI suggestion"
                                    >
                                        <Check style={{ fontSize: '14px' }} />
                                    </IconButton>
                                    <IconButton
                                        size="small"
                                        onClick={() => onRejectAi?.(suggestion.id)}
                                        style={{
                                            backgroundColor: '#f44336',
                                            color: 'white',
                                            width: '24px',
                                            height: '24px'
                                        }}
                                        title="Reject AI suggestion"
                                    >
                                        <Clear style={{ fontSize: '14px' }} />
                                    </IconButton>
                                </Box>
                            </Box>
                        </Box>
                    );
                })}

                {/* Empty State */}
                {selectedColumns?.filter(columnName => {
                    const hasAiSuggestion = aiSuggestions.some(suggestion =>
                        (isSource && suggestion.sourceColumn === columnName) ||
                        (!isSource && suggestion.targetColumn === columnName)
                    );
                    const isConnected = confirmedConnections.some(conn =>
                        (isSource && conn.sourceColumn === columnName) ||
                        (!isSource && conn.targetColumn === columnName)
                    );
                    return !hasAiSuggestion || isConnected;
                }).length === 0 && (!aiSuggestions || aiSuggestions.length === 0) && (
                        <Box style={{
                            padding: '40px 20px',
                            textAlign: 'center',
                            color: '#999',
                            fontStyle: 'italic'
                        }}>
                            Select columns below to see them here
                        </Box>
                    )}
            </Box>
        </Box>
    );
});

const nodeTypes = {
    tableCard: TableCardNode,
};

const DataJoinPopup = ({
    open,
    onClose,
    sourceNode,
    targetNode,
    existingJoins = [],
    onSave,
    graphAttributes,
    fieldsMetadata
}) => {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const attrs = useMemo(() => {
        // Default graphAttributes with fallbacks for backward compatibility
        const defaultGraphAttributes = {
            nodeNameField: 'name',
            nodeSelectedFieldsField: 'selected_fields',
            edgeBaseField: 'base_entity',
            edgeTargetField: 'join_entity',
            edgeTypeField: 'join_type',
            edgePairsField: 'join_pairs',
            edgeConfirmedField: 'user_confirmed',
            edgePairsBaseField: 'base_field',
            edgePairsJoinField: 'join_field',
            edgeAiSuggestedField: 'ai_suggested'
        };
        return { ...defaultGraphAttributes, ...graphAttributes }
    }, []);

    // Get join type options from fieldsMetadata
    const joinTypeOptions = useMemo(() => {
        const joinTypeField = fieldsMetadata?.find(field => 
            field.key === attrs.edgeTypeField && field.autocomplete_list
        );
        
        return joinTypeField?.autocomplete_list || [];
    }, [fieldsMetadata, attrs.edgeTypeField]);

    // ReactFlow state
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Local state for the modal
    const [selectedSourceColumns, setSelectedSourceColumns] = useState([]);
    const [selectedTargetColumns, setSelectedTargetColumns] = useState([]);
    const [confirmedConnections, setConfirmedConnections] = useState([]);
    const [aiSuggestions, setAiSuggestions] = useState([]);
    const [rejectedSuggestionIds, setRejectedSuggestionIds] = useState(new Set());
    const [selectedSourceColumn, setSelectedSourceColumn] = useState(null);
    const [selectedTargetColumn, setSelectedTargetColumn] = useState(null);
    const [globalJoinType, setGlobalJoinType] = useState('inner');

    // Snapshot ref for controlled state management (following DataJoinGraph pattern)
    const snapshotRef = useRef();
    snapshotRef.current = {
        selectedSourceColumns,
        selectedTargetColumns,
        confirmedConnections,
        aiSuggestions,
        rejectedSuggestionIds,
        selectedSourceColumn,
        selectedTargetColumn,
        globalJoinType
    };

    // Get node columns from cached data
    const sourceColumns = sourceNode?.columns || [];
    const targetColumns = targetNode?.columns || [];

    // Centralized function to update React Flow elements (controlled pattern)
    const updateFlowElements = () => {
        if (!open || !sourceNode || !targetNode) return;

        const currentSnapshot = snapshotRef.current;

        const sourceData = {
            label: sourceNode?.[attrs.nodeNameField] || '',
            selectedColumns: currentSnapshot.selectedSourceColumns,
            confirmedConnections: currentSnapshot.confirmedConnections,
            aiSuggestions: currentSnapshot.aiSuggestions.filter(s => !currentSnapshot.rejectedSuggestionIds.has(s.id)),
            onColumnClick: handleColumnClick,
            selectedColumn: currentSnapshot.selectedSourceColumn,
            isSource: true,
            onDeleteConnection: handleDeleteConnection,
            onAcceptAi: handleAcceptAiSuggestion,
            onRejectAi: handleRejectAiSuggestion
        };

        const targetData = {
            label: targetNode?.[attrs.nodeNameField] || '',
            selectedColumns: currentSnapshot.selectedTargetColumns,
            confirmedConnections: currentSnapshot.confirmedConnections,
            aiSuggestions: currentSnapshot.aiSuggestions.filter(s => !currentSnapshot.rejectedSuggestionIds.has(s.id)),
            onColumnClick: handleColumnClick,
            selectedColumn: currentSnapshot.selectedTargetColumn,
            isSource: false,
            onDeleteConnection: handleDeleteConnection,
            onAcceptAi: handleAcceptAiSuggestion,
            onRejectAi: handleRejectAiSuggestion
        };

        const newNodes = [
            {
                id: 'source-card',
                type: 'tableCard',
                position: { x: 50, y: 50 },
                data: sourceData
            },
            {
                id: 'target-card',
                type: 'tableCard',
                position: { x: 400, y: 50 },
                data: targetData
            }
        ];
        setNodes(newNodes);

        // Create edges for confirmed connections and AI suggestions
        const newEdges = [];

        const confirmedEdgeColor = getJoinColor(currentSnapshot.globalJoinType, true);
        const suggestedEdgeColor = getJoinColor(currentSnapshot.globalJoinType, false);

        // Confirmed connections - solid edges
        currentSnapshot.confirmedConnections.forEach((conn, idx) => {
            newEdges.push({
                id: `confirmed-${idx}`,
                source: 'source-card',
                target: 'target-card',
                sourceHandle: `${sourceNode[attrs.nodeNameField]}-${conn.sourceColumn}-source`,
                targetHandle: `${targetNode[attrs.nodeNameField]}-${conn.targetColumn}-target`,
                type: 'default',
                style: {
                    stroke: confirmedEdgeColor,
                    strokeWidth: 2
                },
                markerEnd: {
                    type: 'arrowclosed',
                    width: 8,
                    height: 8,
                    color: confirmedEdgeColor
                }
            });
        });

        // AI suggestions - dashed edges with same color
        currentSnapshot.aiSuggestions
            .filter(suggestion => !currentSnapshot.rejectedSuggestionIds.has(suggestion.id))
            .filter(suggestion =>
                currentSnapshot.selectedSourceColumns.includes(suggestion.sourceColumn) &&
                currentSnapshot.selectedTargetColumns.includes(suggestion.targetColumn)
            )
            .forEach((suggestion, idx) => {
                newEdges.push({
                    id: `ai-${idx}`,
                    source: 'source-card',
                    target: 'target-card',
                    sourceHandle: `${sourceNode[attrs.nodeNameField]}-${suggestion.sourceColumn}-source`,
                    targetHandle: `${targetNode[attrs.nodeNameField]}-${suggestion.targetColumn}-target`,
                    type: 'default',
                    style: {
                        stroke: suggestedEdgeColor,
                        strokeWidth: 2,
                        strokeDasharray: '6,3'
                    },
                    markerEnd: {
                        type: 'arrowclosed',
                        width: 6,
                        height: 6,
                        color: suggestedEdgeColor
                    }
                });
            });

        setEdges(newEdges);
    };

    // Initialize state when modal opens
    useEffect(() => {
        if (open && sourceNode && targetNode) {
            // Separate confirmed connections and AI suggestions from existing joins
            const connections = [];
            const suggestions = [];
            const autoSelectedSourceColumns = new Set();
            const autoSelectedTargetColumns = new Set();

            existingJoins.forEach((join, joinIndex) => {
                if (join[attrs.edgePairsField]?.length > 0) {
                    join[attrs.edgePairsField].forEach((pair, pairIndex) => {
                        // Determine correct field mapping based on join direction
                        const isReversed = join[attrs.edgeBaseField] === targetNode[attrs.nodeNameField];
                        const sourceColumn = isReversed ? pair[attrs.edgePairsJoinField] : pair[attrs.edgePairsBaseField];
                        const targetColumn = isReversed ? pair[attrs.edgePairsBaseField] : pair[attrs.edgePairsJoinField];

                        if (sourceColumn && targetColumn) {
                            if (pair[attrs.edgeConfirmedField] === true) {
                                // Confirmed connection
                                connections.push({
                                    id: `join_${joinIndex}_${pairIndex}`,
                                    sourceColumn,
                                    targetColumn,
                                    joinType: join[attrs.edgeTypeField]?.toLowerCase() || 'inner',
                                    originalJoinIndex: joinIndex,
                                    originalPairIndex: pairIndex
                                });
                                // Auto-select columns for confirmed connections
                                autoSelectedSourceColumns.add(sourceColumn);
                                autoSelectedTargetColumns.add(targetColumn);
                            } else if (pair[attrs.edgeAiSuggestedField] === true && pair[attrs.edgeConfirmedField] === false) {
                                // AI suggestion
                                suggestions.push({
                                    id: `ai_${joinIndex}_${pairIndex}`,
                                    sourceColumn,
                                    targetColumn,
                                    joinType: join[attrs.edgeTypeField]?.toLowerCase() || 'inner',
                                    originalJoinIndex: joinIndex,
                                    originalPairIndex: pairIndex,
                                    isAiSuggestion: true
                                });
                                // Auto-select columns for AI suggestions so they appear in cards
                                autoSelectedSourceColumns.add(sourceColumn);
                                autoSelectedTargetColumns.add(targetColumn);
                            }
                        }
                    });
                }
            });

            setConfirmedConnections(connections);
            setAiSuggestions(suggestions);
            setRejectedSuggestionIds(new Set());

            // Combine existing selected fields with auto-selected columns from AI suggestions
            // Extract field names from object format
            const sourceSelectedFieldNames = (sourceNode[attrs.nodeSelectedFieldsField] || []).map(field => field.selected_field);
            const targetSelectedFieldNames = (targetNode[attrs.nodeSelectedFieldsField] || []).map(field => field.selected_field);

            const allSourceSelected = [...new Set([
                ...sourceSelectedFieldNames,
                ...Array.from(autoSelectedSourceColumns)
            ])];

            const allTargetSelected = [...new Set([
                ...targetSelectedFieldNames,
                ...Array.from(autoSelectedTargetColumns)
            ])];

            setSelectedSourceColumns(allSourceSelected);
            setSelectedTargetColumns(allTargetSelected);

            // Set global join type from first existing join or default
            if (existingJoins.length > 0) {
                setGlobalJoinType(existingJoins[0][attrs.edgeTypeField]?.toLowerCase() || 'inner');
            } else {
                setGlobalJoinType('inner');
            }

            // Clear selections
            setSelectedSourceColumn(null);
            setSelectedTargetColumn(null);

            // Initial flow elements update after state initialization
            // Use setTimeout to ensure all state updates are applied first
            setTimeout(() => {
                if (open && sourceNode && targetNode) {
                    updateFlowElements();
                }
            }, 0);
        }
    }, [open, sourceNode, targetNode, existingJoins, attrs]);

    // Handle column selection in bottom panel
    const handleSourceColumnToggle = useCallback((columnName, isSelected) => {
        if (isSelected) {
            setSelectedSourceColumns(prev => {
                const updated = [...prev, columnName];
                snapshotRef.current.selectedSourceColumns = updated;
                return updated;
            });
        } else {
            setSelectedSourceColumns(prev => {
                const updated = prev.filter(col => col !== columnName);
                snapshotRef.current.selectedSourceColumns = updated;
                return updated;
            });
            // Remove any connections using this column
            setConfirmedConnections(prev => {
                const updated = prev.filter(conn => conn.sourceColumn !== columnName);
                snapshotRef.current.confirmedConnections = updated;
                return updated;
            });
            if (selectedSourceColumn === columnName) {
                setSelectedSourceColumn(null);
                snapshotRef.current.selectedSourceColumn = null;
            }
        }
        updateFlowElements();
    }, [selectedSourceColumn]);

    const handleTargetColumnToggle = useCallback((columnName, isSelected) => {
        if (isSelected) {
            setSelectedTargetColumns(prev => {
                const updated = [...prev, columnName];
                snapshotRef.current.selectedTargetColumns = updated;
                return updated;
            });
        } else {
            setSelectedTargetColumns(prev => {
                const updated = prev.filter(col => col !== columnName);
                snapshotRef.current.selectedTargetColumns = updated;
                return updated;
            });
            // Remove any connections using this column
            setConfirmedConnections(prev => {
                const updated = prev.filter(conn => conn.targetColumn !== columnName);
                snapshotRef.current.confirmedConnections = updated;
                return updated;
            });
            if (selectedTargetColumn === columnName) {
                setSelectedTargetColumn(null);
                snapshotRef.current.selectedTargetColumn = null;
            }
        }
        updateFlowElements();
    }, [selectedTargetColumn]);

    // Handle column click in top cards for manual connection
    const handleColumnClick = useCallback((columnName, isSource) => {
        if (isSource) {
            if (selectedSourceColumn === columnName) {
                setSelectedSourceColumn(null);
                snapshotRef.current.selectedSourceColumn = null;
            } else {
                setSelectedSourceColumn(columnName);
                snapshotRef.current.selectedSourceColumn = columnName;
                setSelectedTargetColumn(null);
                snapshotRef.current.selectedTargetColumn = null;
            }
        } else {
            const currentSnapshot = snapshotRef.current;
            if (currentSnapshot.selectedSourceColumn && currentSnapshot.selectedTargetColumn !== columnName) {
                // Create connection
                const existingConnection = currentSnapshot.confirmedConnections.find(conn =>
                    conn.sourceColumn === currentSnapshot.selectedSourceColumn && conn.targetColumn === columnName
                );

                if (!existingConnection) {
                    const newConnection = {
                        id: `manual_${Date.now()}`,
                        sourceColumn: currentSnapshot.selectedSourceColumn,
                        targetColumn: columnName,
                        joinType: currentSnapshot.globalJoinType,
                        isNew: true
                    };
                    setConfirmedConnections(prev => {
                        const updated = [...prev, newConnection];
                        snapshotRef.current.confirmedConnections = updated;
                        return updated;
                    });
                }

                setSelectedSourceColumn(null);
                snapshotRef.current.selectedSourceColumn = null;
                setSelectedTargetColumn(null);
                snapshotRef.current.selectedTargetColumn = null;
            } else if (selectedTargetColumn === columnName) {
                setSelectedTargetColumn(null);
                snapshotRef.current.selectedTargetColumn = null;
            } else {
                setSelectedTargetColumn(columnName);
                snapshotRef.current.selectedTargetColumn = columnName;
            }
        }
        updateFlowElements();
    }, [selectedSourceColumn, selectedTargetColumn]);

    // Handle connection deletion
    const handleDeleteConnection = useCallback((connectionId) => {
        setConfirmedConnections(prev => {
            const updated = prev.filter(conn => conn.id !== connectionId);
            snapshotRef.current.confirmedConnections = updated;
            return updated;
        });
        updateFlowElements();
    }, []);

    // Handle AI suggestion acceptance
    const handleAcceptAiSuggestion = useCallback((suggestionId) => {
        const currentSnapshot = snapshotRef.current;
        const suggestion = currentSnapshot.aiSuggestions.find(s => s.id === suggestionId);
        if (!suggestion) return;

        // Check if connection already exists
        const existingConnection = currentSnapshot.confirmedConnections.find(conn =>
            conn.sourceColumn === suggestion.sourceColumn && conn.targetColumn === suggestion.targetColumn
        );

        if (!existingConnection) {
            // Create new confirmed connection
            const newConnection = {
                id: `accepted_${suggestionId}`,
                sourceColumn: suggestion.sourceColumn,
                targetColumn: suggestion.targetColumn,
                joinType: suggestion.joinType,
                originalJoinIndex: suggestion.originalJoinIndex,
                originalPairIndex: suggestion.originalPairIndex,
                wasAiSuggestion: true
            };

            setConfirmedConnections(prev => {
                const updated = [...prev, newConnection];
                snapshotRef.current.confirmedConnections = updated;
                return updated;
            });

            // Ensure both columns are selected
            if (!currentSnapshot.selectedSourceColumns.includes(suggestion.sourceColumn)) {
                setSelectedSourceColumns(prev => {
                    const updated = [...prev, suggestion.sourceColumn];
                    snapshotRef.current.selectedSourceColumns = updated;
                    return updated;
                });
            }
            if (!currentSnapshot.selectedTargetColumns.includes(suggestion.targetColumn)) {
                setSelectedTargetColumns(prev => {
                    const updated = [...prev, suggestion.targetColumn];
                    snapshotRef.current.selectedTargetColumns = updated;
                    return updated;
                });
            }
        }

        // Remove from AI suggestions
        setAiSuggestions(prev => {
            const updated = prev.filter(s => s.id !== suggestionId);
            snapshotRef.current.aiSuggestions = updated;
            return updated;
        });
        updateFlowElements();
    }, []);

    // Handle AI suggestion rejection
    const handleRejectAiSuggestion = useCallback((suggestionId) => {
        const currentSnapshot = snapshotRef.current;
        const suggestion = currentSnapshot.aiSuggestions.find(s => s.id === suggestionId);
        if (suggestion) {
            // Remove columns from selection if they were only auto-selected for AI suggestions
            // and weren't manually selected by user
            const wasAutoSelected = (columnName, isSourceColumn) => {
                const nodeFields = isSourceColumn ?
                    (sourceNode[attrs.nodeSelectedFieldsField] || []) :
                    (targetNode[attrs.nodeSelectedFieldsField] || []);
                const fieldNames = nodeFields.map(field => field.selected_field);
                return !fieldNames.includes(columnName);
            };

            if (wasAutoSelected(suggestion.sourceColumn, true)) {
                setSelectedSourceColumns(prev => {
                    const updated = prev.filter(col => col !== suggestion.sourceColumn);
                    snapshotRef.current.selectedSourceColumns = updated;
                    return updated;
                });
            }
            if (wasAutoSelected(suggestion.targetColumn, false)) {
                setSelectedTargetColumns(prev => {
                    const updated = prev.filter(col => col !== suggestion.targetColumn);
                    snapshotRef.current.selectedTargetColumns = updated;
                    return updated;
                });
            }
        }

        setRejectedSuggestionIds(prev => {
            const updated = new Set([...prev, suggestionId]);
            snapshotRef.current.rejectedSuggestionIds = updated;
            return updated;
        });
        setAiSuggestions(prev => {
            const updated = prev.filter(s => s.id !== suggestionId);
            snapshotRef.current.aiSuggestions = updated;
            return updated;
        });
        updateFlowElements();
    }, [sourceNode, targetNode, attrs, updateFlowElements]);

    // Memoized node data
    const nodeData = useMemo(() => ({
        sourceData: {
            label: sourceNode?.[attrs.nodeNameField] || '',
            selectedColumns: selectedSourceColumns,
            confirmedConnections,
            aiSuggestions: aiSuggestions.filter(s => !rejectedSuggestionIds.has(s.id)),
            onColumnClick: handleColumnClick,
            selectedColumn: selectedSourceColumn,
            isSource: true,
            onDeleteConnection: handleDeleteConnection,
            onAcceptAi: handleAcceptAiSuggestion,
            onRejectAi: handleRejectAiSuggestion
        },
        targetData: {
            label: targetNode?.[attrs.nodeNameField] || '',
            selectedColumns: selectedTargetColumns,
            confirmedConnections,
            aiSuggestions: aiSuggestions.filter(s => !rejectedSuggestionIds.has(s.id)),
            onColumnClick: handleColumnClick,
            selectedColumn: selectedTargetColumn,
            isSource: false,
            onDeleteConnection: handleDeleteConnection,
            onAcceptAi: handleAcceptAiSuggestion,
            onRejectAi: handleRejectAiSuggestion
        }
    }), [sourceNode, targetNode, selectedSourceColumns, selectedTargetColumns,
        confirmedConnections, aiSuggestions, rejectedSuggestionIds, handleColumnClick,
        selectedSourceColumn, selectedTargetColumn, handleDeleteConnection,
        handleAcceptAiSuggestion, handleRejectAiSuggestion, attrs]);

    const handleSave = () => {
        // Create the updated entities and joins to pass back
        const updatedsourceNode = {
            ...sourceNode,
            [attrs.nodeSelectedFieldsField]: selectedSourceColumns.map(fieldName => ({
                selected_field: fieldName
            }))
        };

        const updatedtargetNode = {
            ...targetNode,
            [attrs.nodeSelectedFieldsField]: selectedTargetColumns.map(fieldName => ({
                selected_field: fieldName
            }))
        };

        // Build updated joins (deep copy to avoid read-only issues)
        const updatedJoins = existingJoins.map(join => ({
            ...join,
            [attrs.edgePairsField]: join[attrs.edgePairsField] ? join[attrs.edgePairsField].map(pair => ({ ...pair })) : []
        }));

        // Find or create join between these entities
        let joinIndex = updatedJoins.findIndex(join =>
            (join[attrs.edgeBaseField] === sourceNode[attrs.nodeNameField] && join[attrs.edgeTargetField] === targetNode[attrs.nodeNameField]) ||
            (join[attrs.edgeBaseField] === targetNode[attrs.nodeNameField] && join[attrs.edgeTargetField] === sourceNode[attrs.nodeNameField])
        );

        if (joinIndex === -1 && (confirmedConnections.length > 0 || aiSuggestions.length > 0)) {
            // Create new join
            const newJoin = {
                [attrs.edgeBaseField]: sourceNode[attrs.nodeNameField],
                [attrs.edgeTargetField]: targetNode[attrs.nodeNameField],
                [attrs.edgeTypeField]: globalJoinType.toUpperCase(),
                [attrs.edgePairsField]: []
            };
            updatedJoins.push(newJoin);
            joinIndex = updatedJoins.length - 1;
        }

        if (joinIndex !== -1) {
            // Update join pairs - PRESERVE existing pairs that aren't related to our two entities
            const join = updatedJoins[joinIndex];
            const isReversed = join[attrs.edgeBaseField] === targetNode[attrs.nodeNameField];

            // Keep existing join_pairs that don't involve our two entities
            const preservedPairs = join[attrs.edgePairsField].filter(pair => {
                const pairSourceColumn = isReversed ? pair[attrs.edgePairsJoinField] : pair[attrs.edgePairsBaseField];
                const pairTargetColumn = isReversed ? pair[attrs.edgePairsBaseField] : pair[attrs.edgePairsJoinField];

                // Keep pairs that don't match any of our current columns (they involve other entities)
                const isOurPair = (
                    sourceColumns.some(col => col.name === pairSourceColumn) &&
                    targetColumns.some(col => col.name === pairTargetColumn)
                );

                return !isOurPair; // Keep pairs that are NOT ours
            });

            // Add our new/updated pairs
            const ourNewPairs = [];

            // Add confirmed connections (user_confirmed: true)
            confirmedConnections.forEach(conn => {
                ourNewPairs.push({
                    [attrs.edgePairsBaseField]: isReversed ? conn.targetColumn : conn.sourceColumn,
                    [attrs.edgePairsJoinField]: isReversed ? conn.sourceColumn : conn.targetColumn,
                    [attrs.edgeConfirmedField]: true,
                    // [attrs.edgeAiSuggestedField]: conn.wasAiSuggestion ? true : undefined
                });
            });

            // Add remaining AI suggestions (ai_suggested: true, user_confirmed: false)
            aiSuggestions
                .filter(suggestion => !rejectedSuggestionIds.has(suggestion.id))
                .forEach(suggestion => {
                    // Don't add if it's already been confirmed
                    const alreadyConfirmed = confirmedConnections.some(conn =>
                        conn.sourceColumn === suggestion.sourceColumn &&
                        conn.targetColumn === suggestion.targetColumn
                    );

                    if (!alreadyConfirmed) {
                        ourNewPairs.push({
                            [attrs.edgePairsBaseField]: isReversed ? suggestion.targetColumn : suggestion.sourceColumn,
                            [attrs.edgePairsJoinField]: isReversed ? suggestion.sourceColumn : suggestion.targetColumn,
                            [attrs.edgeConfirmedField]: false,
                            // [attrs.edgeAiSuggestedField]: true
                        });
                    }
                });

            // Combine preserved pairs with our new pairs
            join[attrs.edgePairsField] = [...preservedPairs, ...ourNewPairs];
            join[attrs.edgeTypeField] = globalJoinType.toUpperCase();
        }

        onSave({
            sourceNode: updatedsourceNode,
            targetNode: updatedtargetNode,
            updatedJoins
        });

        onClose();
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="xl"
            fullWidth
            PaperProps={{
                style: { minHeight: '700px', maxHeight: '90vh' }
            }}
        >
            <DialogTitle style={{ padding: '16px 24px' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">
                        Join Configuration: {sourceNode?.[attrs.nodeNameField]} � {targetNode?.[attrs.nodeNameField]}
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                        <Typography variant="body2" color="text.secondary">
                            Join Type:
                        </Typography>
                        <FormControl size="small" style={{ minWidth: '100px' }}>
                            <Select
                                value={globalJoinType}
                                onChange={(e) => {
                                    setGlobalJoinType(e.target.value);
                                    snapshotRef.current.globalJoinType = e.target.value;
                                    updateFlowElements();
                                }}
                            >
                                {joinTypeOptions.map((option) => (
                                    <MenuItem key={option} value={option.toLowerCase()}>
                                        {option}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <IconButton onClick={onClose}>
                            <Close />
                        </IconButton>
                    </Box>
                </Box>
            </DialogTitle>

            <DialogContent style={{ padding: '16px' }}>
                {/* Visual Cards with Edges */}
                <Box style={{
                    height: '400px',
                    marginBottom: '20px',
                    backgroundColor: isDarkMode ? theme.palette.grey[900] : theme.palette.grey[50],
                    borderRadius: '8px',
                    border: `1px solid ${isDarkMode ? theme.palette.grey[700] : theme.palette.grey[300]}`
                }}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        nodeTypes={nodeTypes}
                        fitView
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={true}
                        nodesFocusable={false}
                        edgesFocusable={false}
                        panOnDrag={true}
                        zoomOnScroll={true}
                        zoomOnPinch={false}
                        preventScrolling={false}
                    >
                        <Controls
                            style={{
                                color: theme.palette.common.black,
                                border: `1px solid ${isDarkMode ? theme.palette.grey[600] : theme.palette.grey[300]}`,
                                borderRadius: '8px',
                                boxShadow: isDarkMode
                                    ? '0 2px 8px rgba(255, 255, 255, 0.1)'
                                    : '0 2px 8px rgba(0, 0, 0, 0.1)'
                            }}
                        />
                        <Background variant="dots" gap={12} size={1} />
                    </ReactFlow>
                </Box>

                <Divider />

                {/* Column Selection */}
                <Box display="flex" gap={3} marginTop={2}>
                    {/* Source Node Columns */}
                    <ColumnList
                        title={`Select from ${sourceNode?.[attrs.nodeNameField]}:`}
                        nodeName={targetNode?.[attrs.nodeNameField]}
                        columns={sourceColumns}
                        selectedColumns={selectedSourceColumns}
                        confirmedConnections={confirmedConnections}
                        aiSuggestions={aiSuggestions}
                        rejectedSuggestionIds={rejectedSuggestionIds}
                        onColumnToggle={handleSourceColumnToggle}
                        selectedColumn={selectedSourceColumn}
                        isSource={true}
                        theme={theme}
                        isDarkMode={isDarkMode}
                    />

                    {/* Center Indicator */}
                    <Box style={{
                        display: 'flex',
                        alignItems: 'center',
                        paddingTop: '40px',
                        flexDirection: 'column',
                        gap: '8px'
                    }}>
                        <Typography variant="body2" color="text.secondary">
                            Selection drives
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            ↕ Top Cards ↕
                        </Typography>
                    </Box>

                    {/* Target Node Columns */}
                    <ColumnList
                        title={`Select from ${targetNode?.[attrs.nodeNameField]}:`}
                        nodeName={sourceNode?.[attrs.nodeNameField]}
                        columns={targetColumns}
                        selectedColumns={selectedTargetColumns}
                        confirmedConnections={confirmedConnections}
                        aiSuggestions={aiSuggestions}
                        rejectedSuggestionIds={rejectedSuggestionIds}
                        onColumnToggle={handleTargetColumnToggle}
                        selectedColumn={selectedTargetColumn}
                        isSource={false}
                        theme={theme}
                        isDarkMode={isDarkMode}
                        selectedSourceColumn={selectedSourceColumn}
                    />
                </Box>
            </DialogContent>

            <DialogActions style={{ padding: '16px 24px' }}>
                <Box display="flex" justifyContent="space-between" width="100%" alignItems="center">
                    <Typography variant="body2" color="text.secondary">
                        Select columns with checkboxes • Click columns in top cards to create connections
                    </Typography>
                    <Box>
                        <Button onClick={onClose} style={{ marginRight: '12px' }}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            onClick={handleSave}
                            // disabled={confirmedConnections.length === 0}
                        >
                            Save Connections ({confirmedConnections.length})
                        </Button>
                    </Box>
                </Box>
            </DialogActions>
        </Dialog>
    );
};

DataJoinPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    sourceNode: PropTypes.object,
    targetNode: PropTypes.object,
    existingJoins: PropTypes.array,
    onSave: PropTypes.func.isRequired,
    graphAttributes: PropTypes.shape({
        nodeNameField: PropTypes.string,
        nodeSelectedFieldsField: PropTypes.string,
        edgeBaseField: PropTypes.string,
        edgeTargetField: PropTypes.string,
        edgeTypeField: PropTypes.string,
        edgePairsField: PropTypes.string,
        edgeConfirmedField: PropTypes.string,
        edgePairsBaseField: PropTypes.string,
        edgePairsJoinField: PropTypes.string,
        edgeAiSuggestedField: PropTypes.string
    }),
    fieldsMetadata: PropTypes.array
};

DataJoinPopup.defaultProps = {
    existingJoins: [],
    graphAttributes: {},
    fieldsMetadata: []
};

export default DataJoinPopup;