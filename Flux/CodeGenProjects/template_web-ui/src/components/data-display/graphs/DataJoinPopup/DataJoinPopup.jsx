import React, { useReducer, useEffect, useCallback, useMemo, useState } from 'react';
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
    useTheme,
    Tooltip
} from '@mui/material';
import {
    Close,
    Delete,
    Check,
    Clear,
    FilterList
} from '@mui/icons-material';
import {
    ReactFlow,
    Handle,
    Position,
    Controls,
    Background
} from '@xyflow/react';
import { getJoinColor } from '../../../../utils/ui/colorUtils';
import { DB_ID } from '../../../../constants';
import ColumnList from './ColumnList';
import FieldFilterPopup from '../FieldFilterPopup/FieldFilterPopup';

// Helper functions for business logic
const connectionLogic = {
    // Create new manual connection between columns
    addManualConnection: (state, sourceColumn, targetColumn) => {
        const existingConnection = state.connections.find(conn =>
            conn.sourceColumn === sourceColumn && conn.targetColumn === targetColumn
        );

        if (existingConnection) return state.connections;

        const newConnection = {
            id: `manual_${Date.now()}`,
            sourceColumn,
            targetColumn,
            joinType: state.joinType,
            status: 'new',
            tolerance: Math.floor(Math.random() * 100)
        };

        return [...state.connections, newConnection];
    },

    // Remove connection by ID
    removeConnection: (state, connectionId) => {
        const updatedConnections = state.connections.filter(conn => conn.id !== connectionId);
        return { connections: updatedConnections };
    }
};

const aiSuggestionLogic = {
    // Accept AI suggestion and convert to confirmed connection
    acceptSuggestion: (state, suggestionId) => {
        const suggestion = state.suggestions.find(s => s.id === suggestionId);
        if (!suggestion) return state;

        const existingConnection = state.connections.find(conn =>
            conn.sourceColumn === suggestion.sourceColumn && conn.targetColumn === suggestion.targetColumn
        );
        if (existingConnection) return state;

        const newConnection = {
            id: `accepted_${suggestionId}`,
            originalDbId: suggestion.originalDbId,
            sourceColumn: suggestion.sourceColumn,
            targetColumn: suggestion.targetColumn,
            joinType: suggestion.joinType,
            status: suggestion.originalDbId ? 'modified' : 'new',
            wasAiSuggestion: true,
            tolerance: suggestion.tolerance
        };

        const updatedConnections = [...state.connections, newConnection];
        const updatedSuggestions = state.suggestions.filter(s => s.id !== suggestionId);

        // Auto-select columns if not already selected
        let updatedSourceColumns = state.sourceSelectedColumns;
        let updatedTargetColumns = state.targetSelectedColumns;

        if (!state.sourceSelectedColumns.some(col => col.field_name === suggestion.sourceColumn)) {
            updatedSourceColumns = [...state.sourceSelectedColumns, { field_name: suggestion.sourceColumn }];
        }
        if (!state.targetSelectedColumns.some(col => col.field_name === suggestion.targetColumn)) {
            updatedTargetColumns = [...state.targetSelectedColumns, { field_name: suggestion.targetColumn }];
        }

        return {
            connections: updatedConnections,
            suggestions: updatedSuggestions,
            sourceSelectedColumns: updatedSourceColumns,
            targetSelectedColumns: updatedTargetColumns
        };
    },

    // Reject AI suggestion
    rejectSuggestion: (state, suggestionId) => {
        return {
            suggestions: state.suggestions.filter(s => s.id !== suggestionId),
            rejectedSuggestionIds: new Set([...state.rejectedSuggestionIds, suggestionId])
        };
    }
};

const columnLogic = {
    // Toggle column selection and clean up related connections
    toggleColumnSelection: (state, columnName, isSelected, isSource) => {
        const targetKey = isSource ? 'sourceSelectedColumns' : 'targetSelectedColumns';

        if (isSelected) {
            return {
                [targetKey]: [...state[targetKey], { field_name: columnName }]
            };
        } else {
            const updatedColumns = state[targetKey].filter(col => col.field_name !== columnName);
            const updatedConnections = state.connections.filter(conn =>
                isSource ? conn.sourceColumn !== columnName : conn.targetColumn !== columnName
            );

            const selectedColumnKey = isSource ? 'selectedSourceColumn' : 'selectedTargetColumn';
            const clearedSelection = state[selectedColumnKey] === columnName ? null : state[selectedColumnKey];

            return {
                [targetKey]: updatedColumns,
                connections: updatedConnections,
                [selectedColumnKey]: clearedSelection
            };
        }
    },

    // Update filter on selected column
    updateColumnFilter: (state, columnName, isSource, filterData, attrs) => {
        const targetKey = isSource ? 'sourceSelectedColumns' : 'targetSelectedColumns';

        const updatedColumns = state[targetKey].map(columnObj => {
            if (columnObj.field_name === columnName) {
                return {
                    ...columnObj,
                    [attrs.edgeFilterOperator]: filterData.operator,
                    [attrs.edgeFilterValue]: filterData.filter_values,
                    [attrs.edgeNaturalLanguageFilter]: filterData.user_natural_language_filter
                };
            }
            return columnObj;
        });

        return { [targetKey]: updatedColumns };
    }
};

// Create minimal initial state - no UI derivation
const createInitialState = ({ sourceNode, targetNode, existingJoin, graphAttributes }) => {
    const attrs = {
        nodeNameField: 'name',
        nodeSelectedFieldsField: 'field_selections',
        edgeBaseField: 'base_entity_selection',
        edgeTargetField: 'join_entity_selection',
        edgeTypeField: 'join_type',
        edgePairsField: 'join_pairs',
        edgeConfirmedField: 'user_confirmed',
        edgePairsBaseField: 'base_field',
        edgePairsJoinField: 'join_field',
        edgeAiSuggestedField: 'ai_suggested',
        edgeToleranceField: 'tolerance',
        ...graphAttributes
    };

    const sourceNodeName = sourceNode?.[attrs.nodeNameField] || '';
    const targetNodeName = targetNode?.[attrs.nodeNameField] || '';

    let joinType = 'inner';
    let confirmedConnections = [];
    let aiSuggestions = [];
    let sourceSelectedColumns = [];
    let targetSelectedColumns = [];

    // Parse existing join data if available
    if (existingJoin) {
        joinType = existingJoin[attrs.edgeTypeField]?.toLowerCase() || 'inner';

        existingJoin[attrs.edgePairsField]?.forEach((pair, pairIndex) => {
            const baseEntityName = existingJoin.base_entity_selection?.entity_name;
            const isReversed = baseEntityName === targetNodeName;
            const sourceColumn = isReversed ? pair[attrs.edgePairsJoinField] : pair[attrs.edgePairsBaseField];
            const targetColumn = isReversed ? pair[attrs.edgePairsBaseField] : pair[attrs.edgePairsJoinField];

            if (sourceColumn && targetColumn) {
                const connectionBase = {
                    id: `existing_${pairIndex}`,
                    originalDbId: existingJoin[DB_ID],
                    sourceColumn,
                    targetColumn,
                    joinType,
                    status: 'existing'
                };

                if (pair[attrs.edgeConfirmedField] === true) {
                    // Check if this confirmed connection was originally an AI suggestion
                    const wasAiSuggestion = pair[attrs.edgeAiSuggestedField] === true;
                    confirmedConnections.push({
                        ...connectionBase,
                        wasAiSuggestion,
                        tolerance: pair[attrs.edgeToleranceField] ?? Math.floor(Math.random() * 100)
                    });
                } else if (pair[attrs.edgeAiSuggestedField] === true && pair[attrs.edgeConfirmedField] === false) {
                    aiSuggestions.push({
                        ...connectionBase,
                        id: `ai_${pairIndex}`,
                        isAiSuggestion: true,
                        tolerance: pair[attrs.edgeToleranceField] ?? Math.floor(Math.random() * 100)
                    });
                }
            }
        });

        // Parse selected columns from existing join
        const baseSelection = existingJoin.base_entity_selection?.field_selections || [];
        const joinSelection = existingJoin.join_entity_selection?.field_selections || [];

        if (existingJoin.base_entity_selection?.entity_name === sourceNodeName) {
            sourceSelectedColumns = baseSelection.map(field => {
                const result = { field_name: field.field_name };
                // Only include filter properties if they actually exist in the original field
                if (field.hasOwnProperty(attrs.edgeFilterOperator)) result[attrs.edgeFilterOperator] = field[attrs.edgeFilterOperator];
                if (field.hasOwnProperty(attrs.edgeFilterValue)) result[attrs.edgeFilterValue] = field[attrs.edgeFilterValue];
                if (field.hasOwnProperty(attrs.edgeNaturalLanguageFilter)) result[attrs.edgeNaturalLanguageFilter] = field[attrs.edgeNaturalLanguageFilter];
                return result;
            });
            targetSelectedColumns = joinSelection.map(field => {
                const result = { field_name: field.field_name };
                // Only include filter properties if they actually exist in the original field
                if (field.hasOwnProperty(attrs.edgeFilterOperator)) result[attrs.edgeFilterOperator] = field[attrs.edgeFilterOperator];
                if (field.hasOwnProperty(attrs.edgeFilterValue)) result[attrs.edgeFilterValue] = field[attrs.edgeFilterValue];
                if (field.hasOwnProperty(attrs.edgeNaturalLanguageFilter)) result[attrs.edgeNaturalLanguageFilter] = field[attrs.edgeNaturalLanguageFilter];
                return result;
            });
        } else {
            targetSelectedColumns = baseSelection.map(field => {
                const result = { field_name: field.field_name };
                // Only include filter properties if they actually exist in the original field
                if (field.hasOwnProperty(attrs.edgeFilterOperator)) result[attrs.edgeFilterOperator] = field[attrs.edgeFilterOperator];
                if (field.hasOwnProperty(attrs.edgeFilterValue)) result[attrs.edgeFilterValue] = field[attrs.edgeFilterValue];
                if (field.hasOwnProperty(attrs.edgeNaturalLanguageFilter)) result[attrs.edgeNaturalLanguageFilter] = field[attrs.edgeNaturalLanguageFilter];
                return result;
            });
            sourceSelectedColumns = joinSelection.map(field => {
                const result = { field_name: field.field_name };
                // Only include filter properties if they actually exist in the original field
                if (field.hasOwnProperty(attrs.edgeFilterOperator)) result[attrs.edgeFilterOperator] = field[attrs.edgeFilterOperator];
                if (field.hasOwnProperty(attrs.edgeFilterValue)) result[attrs.edgeFilterValue] = field[attrs.edgeFilterValue];
                if (field.hasOwnProperty(attrs.edgeNaturalLanguageFilter)) result[attrs.edgeNaturalLanguageFilter] = field[attrs.edgeNaturalLanguageFilter];
                return result;
            });
        }
    }

    // Return only core state - no UI derivation
    return {
        joinType,
        sourceNodeName,
        targetNodeName,
        sourceSelectedColumns,
        targetSelectedColumns,
        connections: confirmedConnections,
        suggestions: aiSuggestions,
        selectedSourceColumn: null,
        selectedTargetColumn: null,
        rejectedSuggestionIds: new Set()
    };
};

// Simplified reducer focused only on core state management
const joinReducer = (state, action) => {
    switch (action.type) {
        case 'SELECT_COLUMN': {
            const { columnName, isSource } = action.payload;
            if (isSource) {
                const selectedSourceColumn = state.selectedSourceColumn === columnName ? null : columnName;
                return {
                    ...state,
                    selectedSourceColumn,
                    selectedTargetColumn: selectedSourceColumn ? null : state.selectedTargetColumn
                };
            } else {
                // Create connection if source column selected
                if (state.selectedSourceColumn && state.selectedTargetColumn !== columnName) {
                    const newConnections = connectionLogic.addManualConnection(state, state.selectedSourceColumn, columnName);
                    if (newConnections !== state.connections) {
                        return {
                            ...state,
                            connections: newConnections,
                            selectedSourceColumn: null,
                            selectedTargetColumn: null
                        };
                    }
                }

                const selectedTargetColumn = state.selectedTargetColumn === columnName ? null : columnName;
                return { ...state, selectedTargetColumn };
            }
        }

        case 'DELETE_CONNECTION': {
            const { connectionId } = action.payload;
            const result = connectionLogic.removeConnection(state, connectionId);
            return { ...state, ...result };
        }

        case 'ACCEPT_SUGGESTION': {
            const { suggestionId } = action.payload;
            const result = aiSuggestionLogic.acceptSuggestion(state, suggestionId);
            return { ...state, ...result };
        }

        case 'REJECT_SUGGESTION': {
            const { suggestionId } = action.payload;
            const result = aiSuggestionLogic.rejectSuggestion(state, suggestionId);
            return { ...state, ...result };
        }

        case 'TOGGLE_COLUMN_SELECTION': {
            const { columnName, isSelected, isSource } = action.payload;
            const result = columnLogic.toggleColumnSelection(state, columnName, isSelected, isSource);
            return { ...state, ...result };
        }

        case 'UPDATE_FILTER': {
            const { columnName, isSource, filterData, attrs } = action.payload;
            const result = columnLogic.updateColumnFilter(state, columnName, isSource, filterData, attrs);
            return { ...state, ...result };
        }

        case 'SET_JOIN_TYPE': {
            const { joinType } = action.payload;
            return { ...state, joinType };
        }

        case 'INITIALISE_STATE':
            return createInitialState(action.payload);

        default:
            return state;
    }
};

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
        onRejectAi,
        attrs
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
                {selectedColumns?.map((columnObj, idx) => {
                    const columnName = columnObj.field_name;
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

                    // Check if this column has filters applied
                    const hasFilters = columnObj[attrs.edgeFilterOperator] && columnObj[attrs.edgeFilterValue];

                    const isSelected = selectedColumn === columnName;

                    // Skip rendering if this column is part of an AI suggestion (it will be rendered separately)
                    if (hasAiSuggestion && !isConnected) {
                        return null;
                    }

                    const filterTooltip = hasFilters
                        ? `${columnObj[attrs.edgeFilterOperator]},  ${Array.isArray(columnObj[attrs.edgeFilterValue]) ? columnObj[attrs.edgeFilterValue].join(', ') : columnObj[attrs.edgeFilterValue]}`
                        : "Add filter";

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
                                                label="Connected"
                                                size="small"
                                                style={{
                                                    backgroundColor: '#4CAF50',
                                                    color: 'white',
                                                    height: '12px',
                                                    fontSize: '8px'
                                                }}
                                            />
                                            {connection.wasAiSuggestion && (
                                                <Chip
                                                    label="AI"
                                                    size="small"
                                                    style={{
                                                        backgroundColor: '#FF9800',
                                                        color: 'white',
                                                        height: '12px',
                                                        fontSize: '7px'
                                                    }}
                                                />
                                            )}
                                            {/* {hasFilters && (
                                                <Chip
                                                    label="FILTERED"
                                                    size="small"
                                                    style={{
                                                        backgroundColor: '#2196F3',
                                                        color: 'white',
                                                        height: '18px',
                                                        fontSize: '10px'
                                                    }}
                                                />
                                            )} */}
                                        </Box>
                                    </Box>
                                    <Box display="flex" gap={0.5}>
                                        <Tooltip title={filterTooltip}>
                                            <IconButton
                                                size="small"
                                                onClick={() => data.onFilterClick?.(columnName, isSource, columnObj)}
                                                style={{ width: '24px', height: '24px' }}
                                            >
                                                <FilterList style={{
                                                    fontSize: '14px',
                                                    color: hasFilters ? '#2196F3' : '#666'
                                                }} />
                                            </IconButton>
                                        </Tooltip>
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
                                <Box display="flex" alignItems="center" justifyContent="space-between">
                                    <Box flex={1}>
                                        <Typography variant="body2" style={{ fontWeight: 600 }}>
                                            {columnName}
                                            <Chip
                                                label={isSelected ? "Click Target" : "Selected"}
                                                size="small"
                                                color={isSelected ? "secondary" : "primary"}
                                                style={{ marginLeft: '8px', height: '12px', fontSize: '8px' }}
                                            />
                                            {hasFilters && (
                                                <Chip
                                                    label="Filtered"
                                                    size="small"
                                                    style={{
                                                        backgroundColor: '#2196F3',
                                                        color: 'white',
                                                        height: '12px',
                                                        fontSize: '8px',
                                                        marginLeft: '4px'
                                                    }}
                                                />
                                            )}
                                        </Typography>
                                    </Box>
                                    <Tooltip title={filterTooltip}>
                                        <IconButton
                                            size="small"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                data.onFilterClick?.(columnName, isSource, columnObj);
                                            }}
                                            style={{ width: '24px', height: '24px' }}
                                        >
                                            <FilterList style={{
                                                fontSize: '14px',
                                                color: hasFilters ? '#2196F3' : '#666'
                                            }} />
                                        </IconButton>
                                    </Tooltip>
                                </Box>
                            </Box>
                        );
                    }
                })}

                {/* AI Suggestions */}
                {aiSuggestions?.filter(suggestion =>
                    (isSource && suggestion.sourceColumn) || (!isSource && suggestion.targetColumn)
                ).map((suggestion, idx) => {
                    const columnName = isSource ? suggestion.sourceColumn : suggestion.targetColumn;
                    const isColumnSelected = selectedColumns.some(col => col.field_name === columnName);

                    // Only show if the column is selected in bottom panel
                    if (!isColumnSelected) return null;

                    return (
                        <Box
                            key={`ai-${idx}`}
                            style={{
                                margin: '4px 0',
                                padding: '8px',
                                backgroundColor: isDarkMode
                                    ? theme.palette.warning.dark + '40'
                                    : theme.palette.warning.light + '60',
                                borderRadius: '6px',
                                border: `2px solid ${theme.palette.warning.main}`,
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
                {selectedColumns?.filter(columnObj => {
                    const columnName = columnObj.field_name;
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
    existingJoin = null,
    onSave,
    graphAttributes,
    metadata
}) => {
    const theme = useTheme();
    const isDarkMode = theme.palette.mode === 'dark';

    const attrs = useMemo(() => {
        const defaultGraphAttributes = {
            nodeNameField: 'name',
            nodeSelectedFieldsField: 'field_selections',
            edgeBaseField: 'base_entity_selection',
            edgeTargetField: 'join_entity_selection',
            edgeTypeField: 'join_type',
            edgePairsField: 'join_pairs',
            edgeConfirmedField: 'user_confirmed',
            edgePairsBaseField: 'base_field',
            edgePairsJoinField: 'join_field',
            edgeAiSuggestedField: 'ai_suggested',
            edgeFilterOperator: 'filter_operator',
            edgeFilterValue: 'filter_values',
            edgeNaturalLanguageFilter: 'user_natural_language_filter'
        };
        return { ...defaultGraphAttributes, ...graphAttributes }
    }, []);

    const joinTypeOptions = metadata?.joinTypeOptions || [];
    const filterOperators = metadata?.filterOperators || [
        'EQUALS', 'NOT_EQUALS', 'GREATER_THAN', 'GREATER_THAN_OR_EQUAL',
        'LESS_THAN', 'LESS_THAN_OR_EQUAL', 'LIKE', 'NOT_LIKE',
        'IN', 'NOT_IN', 'IS_NULL', 'IS_NOT_NULL'
    ];

    const [state, dispatch] = useReducer(joinReducer, {
        sourceNode,
        targetNode,
        existingJoin,
        graphAttributes: attrs
    }, createInitialState);

    const [filterPopupState, setFilterPopupState] = useState({
        open: false,
        columnName: null,
        isSource: null,
        existingFilter: null
    });

    const sourceColumns = sourceNode?.columns || [];
    const targetColumns = targetNode?.columns || [];

    // INITIALISE state when modal opens or props change
    useEffect(() => {
        if (open) {
            dispatch({
                type: 'INITIALISE_STATE',
                payload: { sourceNode, targetNode, existingJoin, graphAttributes: attrs }
            });
        }
    }, [open, sourceNode, targetNode, existingJoin, attrs]);

    // Stable event handlers wrapped in useCallback
    const handleSourceColumnToggle = useCallback((columnName, isSelected) => {
        dispatch({
            type: 'TOGGLE_COLUMN_SELECTION',
            payload: { columnName, isSelected, isSource: true }
        });
    }, []);

    const handleTargetColumnToggle = useCallback((columnName, isSelected) => {
        dispatch({
            type: 'TOGGLE_COLUMN_SELECTION',
            payload: { columnName, isSelected, isSource: false }
        });
    }, []);

    const handleColumnClick = useCallback((columnName, isSource) => {
        dispatch({
            type: 'SELECT_COLUMN',
            payload: { columnName, isSource }
        });
    }, []);

    const handleDeleteConnection = useCallback((connectionId) => {
        dispatch({
            type: 'DELETE_CONNECTION',
            payload: { connectionId }
        });
    }, []);

    const handleAcceptAiSuggestion = useCallback((suggestionId) => {
        dispatch({
            type: 'ACCEPT_SUGGESTION',
            payload: { suggestionId }
        });
    }, []);

    const handleRejectAiSuggestion = useCallback((suggestionId) => {
        dispatch({
            type: 'REJECT_SUGGESTION',
            payload: { suggestionId }
        });
    }, []);

    const handleFilterClick = useCallback((columnName, isSource, existingFilter = null) => {
        setFilterPopupState({
            open: true,
            columnName,
            isSource,
            existingFilter
        });
    }, []);

    const handleFilterSave = useCallback((filterData) => {
        const { columnName, isSource } = filterPopupState;
        dispatch({
            type: 'UPDATE_FILTER',
            payload: { columnName, isSource, filterData, attrs }
        });
        setFilterPopupState({ open: false, columnName: null, isSource: null, existingFilter: null });
    }, [filterPopupState, attrs]);

    const handleFilterClose = useCallback(() => {
        setFilterPopupState({ open: false, columnName: null, isSource: null, existingFilter: null });
    }, []);

    // Derive UI state (nodes & edges) from reducer state using useMemo
    const { nodes, edges } = useMemo(() => {
        // Create ReactFlow nodes with current data
        const calculatedNodes = [
            {
                id: 'source-card',
                type: 'tableCard',
                position: { x: 50, y: 50 },
                data: {
                    label: state.sourceNodeName,
                    selectedColumns: state.sourceSelectedColumns,
                    confirmedConnections: state.connections,
                    aiSuggestions: state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id)),
                    selectedColumn: state.selectedSourceColumn,
                    isSource: true,
                    onColumnClick: handleColumnClick,
                    onDeleteConnection: handleDeleteConnection,
                    onAcceptAi: handleAcceptAiSuggestion,
                    onRejectAi: handleRejectAiSuggestion,
                    onFilterClick: handleFilterClick,
                    attrs
                }
            },
            {
                id: 'target-card',
                type: 'tableCard',
                position: { x: 400, y: 50 },
                data: {
                    label: state.targetNodeName,
                    selectedColumns: state.targetSelectedColumns,
                    confirmedConnections: state.connections,
                    aiSuggestions: state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id)),
                    selectedColumn: state.selectedTargetColumn,
                    isSource: false,
                    onColumnClick: handleColumnClick,
                    onDeleteConnection: handleDeleteConnection,
                    onAcceptAi: handleAcceptAiSuggestion,
                    onRejectAi: handleRejectAiSuggestion,
                    onFilterClick: handleFilterClick,
                    attrs
                }
            }
        ];

        // Create ReactFlow edges for connections and suggestions
        const calculatedEdges = [];
        const confirmedEdgeColor = getJoinColor(state.joinType, metadata.joinTypeColorMapping, theme, true);
        const suggestedEdgeColor = getJoinColor(state.joinType, metadata.joinTypeColorMapping, theme, false);

        // Confirmed connections - solid edges
        state.connections.forEach((conn, idx) => {
            calculatedEdges.push({
                id: `confirmed-${idx}`,
                source: 'source-card',
                target: 'target-card',
                sourceHandle: `${state.sourceNodeName}-${conn.sourceColumn}-source`,
                targetHandle: `${state.targetNodeName}-${conn.targetColumn}-target`,
                type: 'default',
                label: `T: ${conn.tolerance}`,
                labelShowBg: false,
                labelStyle: {
                    fill: confirmedEdgeColor,  
                    fontWeight: 200,
                    fontSize: '10px',
                    transform: 'translateY(-15px)',
                    textAnchor: 'middle',
                    dominantBaseline: 'middle'
                },
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

        // AI suggestions - solid opaque edges (same as main graph)
        state.suggestions
            .filter(suggestion => !state.rejectedSuggestionIds.has(suggestion.id))
            .forEach((suggestion, idx) => {
                calculatedEdges.push({
                    id: `ai-${idx}`,
                    source: 'source-card',
                    target: 'target-card',
                    sourceHandle: `${state.sourceNodeName}-${suggestion.sourceColumn}-source`,
                    targetHandle: `${state.targetNodeName}-${suggestion.targetColumn}-target`,
                    type: 'default',
                    label: `T: ${suggestion.tolerance}`,
                    labelShowBg: false,
                    labelStyle: {
                        fill: suggestedEdgeColor,
                        fontWeight: 600,
                        fontSize: '12px',
                        transform: 'translateY(-15px)',
                        textAnchor: 'middle',
                        dominantBaseline: 'middle'
                    },
                    style: {
                        stroke: suggestedEdgeColor,
                        strokeWidth: 2
                    },
                    markerEnd: {
                        type: 'arrowclosed',
                        width: 8,
                        height: 8,
                        color: suggestedEdgeColor
                    }
                });
            });

        return { nodes: calculatedNodes, edges: calculatedEdges };
    }, [
        state,
        handleColumnClick,
        handleDeleteConnection,
        handleAcceptAiSuggestion,
        handleRejectAiSuggestion,
        handleFilterClick,
        metadata.joinTypeColorMapping,
        theme,
        attrs
    ]);

    // Check if there are pending AI suggestions (not accepted or rejected)
    const hasPendingAiSuggestions = useMemo(() => {
        return state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id)).length > 0;
    }, [state.suggestions, state.rejectedSuggestionIds]);

    // Pure handleSave function - depends only on final state
    const handleSave = useCallback(() => {
        // Safety check: prevent save if there are pending AI suggestions
        const pendingSuggestions = state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id));
        if (pendingSuggestions.length > 0) {
            return; // Early return - should not happen due to UI disabled state
        }

        // Helper function to merge field selections while preserving xpath metadata AND original order
        const mergeFieldSelections = (newFieldSelections, originalFieldSelections = []) => {

            // Create a Map for quick lookup of new fields by field_name
            const newFieldsMap = new Map();
            newFieldSelections.forEach(field => {
                newFieldsMap.set(field.field_name, field);
            });

            // Start with existing fields that are still selected, preserve their order and metadata
            const updatedFields = originalFieldSelections
                .filter(existingField => newFieldsMap.has(existingField.field_name))
                .map(existingField => {
                    const newField = newFieldsMap.get(existingField.field_name);
                    // Remove this field from the map so we track what's been processed
                    newFieldsMap.delete(existingField.field_name);

                    // Start with the complete existing field to preserve ALL properties (xpath, ids, etc.)
                    const result = { ...existingField };

                    // Only update filter-related fields if they exist in newField AND have actually changed
                    if (newField.hasOwnProperty(attrs.edgeFilterOperator) && newField[attrs.edgeFilterOperator] !== undefined) {
                        result[attrs.edgeFilterOperator] = newField[attrs.edgeFilterOperator];
                    }
                    if (newField.hasOwnProperty(attrs.edgeFilterValue) && newField[attrs.edgeFilterValue] !== undefined) {
                        result[attrs.edgeFilterValue] = newField[attrs.edgeFilterValue];
                    }
                    if (newField.hasOwnProperty(attrs.edgeNaturalLanguageFilter) && newField[attrs.edgeNaturalLanguageFilter] !== undefined) {
                        result[attrs.edgeNaturalLanguageFilter] = newField[attrs.edgeNaturalLanguageFilter];
                    }

                    return result;
                });

            // Add any completely new fields at the end (these weren't in originalFieldSelections)
            const newFields = Array.from(newFieldsMap.values()).map(newField => ({
                field_name: newField.field_name,
                [attrs.edgeFilterOperator]: newField[attrs.edgeFilterOperator] || null,
                [attrs.edgeFilterValue]: newField[attrs.edgeFilterValue] || null,
                [attrs.edgeNaturalLanguageFilter]: newField[attrs.edgeNaturalLanguageFilter] || null
            }));

            return [...updatedFields, ...newFields];
        };

        // Helper function to merge join pairs while preserving xpath metadata
        const mergeJoinPairs = (newJoinPairs, originalJoinPairs = []) => {
            return newJoinPairs.map((newPair) => {
                // Try to find existing pair by matching base_field and join_field
                const existingPair = originalJoinPairs.find(
                    originalPair =>
                        originalPair[attrs.edgePairsBaseField] === newPair[attrs.edgePairsBaseField] &&
                        originalPair[attrs.edgePairsJoinField] === newPair[attrs.edgePairsJoinField]
                );

                if (existingPair) {
                    // Preserve original pair but update the confirmation status
                    return {
                        ...existingPair,
                        [attrs.edgeConfirmedField]: newPair[attrs.edgeConfirmedField]
                    };
                } else {
                    // New pair - just return as is (will need xpath generation in parent)
                    return newPair;
                }
            });
        };

        // Determine direction based on original existingJoin if it existed
        const isReversed = existingJoin &&
            existingJoin.base_entity_selection?.entity_name === targetNode[attrs.nodeNameField];

        let newJoinObject;

        if (existingJoin) {
            // START WITH EXISTING JOIN to preserve all xpath metadata
            newJoinObject = {
                ...existingJoin,
                // Update join type
                [attrs.edgeTypeField]: state.joinType.toUpperCase()
            };

            // Update base_entity_selection field_selections while preserving xpath metadata
            const newBaseFieldSelections = (isReversed ? state.targetSelectedColumns : state.sourceSelectedColumns).map(columnObj => ({
                field_name: columnObj.field_name,
                [attrs.edgeFilterOperator]: columnObj[attrs.edgeFilterOperator],
                [attrs.edgeFilterValue]: columnObj[attrs.edgeFilterValue],
                [attrs.edgeNaturalLanguageFilter]: columnObj[attrs.edgeNaturalLanguageFilter]
            }));

            newJoinObject.base_entity_selection = {
                ...newJoinObject.base_entity_selection,
                field_selections: mergeFieldSelections(
                    newBaseFieldSelections,
                    existingJoin.base_entity_selection?.field_selections
                )
            };

            // Update join_entity_selection field_selections while preserving xpath metadata
            const newJoinFieldSelections = (isReversed ? state.sourceSelectedColumns : state.targetSelectedColumns).map(columnObj => ({
                field_name: columnObj.field_name,
                [attrs.edgeFilterOperator]: columnObj[attrs.edgeFilterOperator],
                [attrs.edgeFilterValue]: columnObj[attrs.edgeFilterValue],
                [attrs.edgeNaturalLanguageFilter]: columnObj[attrs.edgeNaturalLanguageFilter]
            }));

            newJoinObject.join_entity_selection = {
                ...newJoinObject.join_entity_selection,
                field_selections: mergeFieldSelections(
                    newJoinFieldSelections,
                    existingJoin.join_entity_selection?.field_selections
                )
            };
        } else {
            // NEW JOIN - Create from scratch (no xpath metadata to preserve)
            newJoinObject = {
                base_entity_selection: {
                    entity_name: isReversed ? targetNode[attrs.nodeNameField] : sourceNode[attrs.nodeNameField],
                    field_selections: (isReversed ? state.targetSelectedColumns : state.sourceSelectedColumns).map(columnObj => ({
                        field_name: columnObj.field_name,
                        [attrs.edgeFilterOperator]: columnObj[attrs.edgeFilterOperator],
                        [attrs.edgeFilterValue]: columnObj[attrs.edgeFilterValue],
                        [attrs.edgeNaturalLanguageFilter]: columnObj[attrs.edgeNaturalLanguageFilter]
                    }))
                },
                join_entity_selection: {
                    entity_name: isReversed ? sourceNode[attrs.nodeNameField] : targetNode[attrs.nodeNameField],
                    field_selections: (isReversed ? state.sourceSelectedColumns : state.targetSelectedColumns).map(columnObj => ({
                        field_name: columnObj.field_name,
                        [attrs.edgeFilterOperator]: columnObj[attrs.edgeFilterOperator],
                        [attrs.edgeFilterValue]: columnObj[attrs.edgeFilterValue],
                        [attrs.edgeNaturalLanguageFilter]: columnObj[attrs.edgeNaturalLanguageFilter]
                    }))
                },
                [attrs.edgeTypeField]: state.joinType.toUpperCase(),
                [attrs.edgePairsField]: []
            };
        }

        // Reconstruct join_pairs from current state
        const joinPairs = [];

        // Add confirmed connections
        state.connections.forEach(conn => {
            joinPairs.push({
                [attrs.edgePairsBaseField]: isReversed ? conn.targetColumn : conn.sourceColumn,
                [attrs.edgePairsJoinField]: isReversed ? conn.sourceColumn : conn.targetColumn,
                [attrs.edgeConfirmedField]: true
            });
        });

        // Add remaining AI suggestions (non-rejected)
        state.suggestions
            .filter(suggestion => !state.rejectedSuggestionIds.has(suggestion.id))
            .forEach(suggestion => {
                // Don't add if already confirmed
                const alreadyConfirmed = state.connections.some(conn =>
                    conn.sourceColumn === suggestion.sourceColumn &&
                    conn.targetColumn === suggestion.targetColumn
                );

                if (!alreadyConfirmed) {
                    joinPairs.push({
                        [attrs.edgePairsBaseField]: isReversed ? suggestion.targetColumn : suggestion.sourceColumn,
                        [attrs.edgePairsJoinField]: isReversed ? suggestion.sourceColumn : suggestion.targetColumn,
                        [attrs.edgeConfirmedField]: false
                    });
                }
            });

        // Update join_pairs while preserving xpath metadata for existing pairs
        if (existingJoin) {
            newJoinObject[attrs.edgePairsField] = mergeJoinPairs(
                joinPairs,
                existingJoin[attrs.edgePairsField]
            );
        } else {
            newJoinObject[attrs.edgePairsField] = joinPairs;
        }

        onSave(newJoinObject);
        onClose();
    }, [state, sourceNode, targetNode, existingJoin, attrs, onSave, onClose]);

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
            <DialogTitle style={{ padding: '12px 18px' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">
                        Join Configuration: {sourceNode?.[attrs.nodeNameField]}  {targetNode?.[attrs.nodeNameField]}
                    </Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                        <Typography variant="body2" color="text.secondary">
                            Join Type:
                        </Typography>
                        <FormControl size="small" style={{ minWidth: '100px' }}>
                            <Select
                                value={state.joinType}
                                onChange={(e) => {
                                    dispatch({
                                        type: 'SET_JOIN_TYPE',
                                        payload: { joinType: e.target.value }
                                    });
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
                        onNodesChange={() => { }} // No-op since we don't need node changes
                        onEdgesChange={() => { }} // No-op since we don't need edge changes
                        nodeTypes={nodeTypes}
                        defaultViewport={{ x: 300, y: 10, zoom: 1 }}

                        // fitView
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={true}
                        nodesFocusable={false}
                        edgesFocusable={false}
                        panOnDrag={true}
                        proOptions={{ hideAttribution: true }}
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
                        selectedColumns={state.sourceSelectedColumns}
                        confirmedConnections={state.connections}
                        aiSuggestions={state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id))}
                        rejectedSuggestionIds={state.rejectedSuggestionIds}
                        onColumnToggle={handleSourceColumnToggle}
                        selectedColumn={state.selectedSourceColumn}
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
                        selectedColumns={state.targetSelectedColumns}
                        confirmedConnections={state.connections}
                        aiSuggestions={state.suggestions.filter(s => !state.rejectedSuggestionIds.has(s.id))}
                        rejectedSuggestionIds={state.rejectedSuggestionIds}
                        onColumnToggle={handleTargetColumnToggle}
                        selectedColumn={state.selectedTargetColumn}
                        isSource={false}
                        theme={theme}
                        isDarkMode={isDarkMode}
                        selectedSourceColumn={state.selectedSourceColumn}
                    />
                </Box>
            </DialogContent>

            <DialogActions style={{ padding: '16px 24px' }}>
                <Box display="flex" justifyContent="space-between" width="100%" alignItems="center">
                    <Box display="flex">
                        <Typography variant="body2" color="text.secondary">
                            Select columns with checkboxes • Click columns in top cards to create connections
                        </Typography>
                        {hasPendingAiSuggestions && (
                            <Typography variant="body2" color="warning.main" sx={{ ml: 5, mt: 1 }}>
                                Please accept or reject all AI suggestions before saving manual connections.
                            </Typography>
                        )}
                    </Box>
                    <Box>
                        <Button onClick={onClose} style={{ marginRight: '12px' }}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            onClick={handleSave}
                            disabled={hasPendingAiSuggestions}
                        >
                            Save Connections ({state.connections.length})
                        </Button>
                    </Box>
                </Box>
            </DialogActions>

            {/* Field Filter Popup */}
            <FieldFilterPopup
                open={filterPopupState.open}
                onClose={handleFilterClose}
                onSave={handleFilterSave}
                columnName={filterPopupState.columnName}
                existingFilter={filterPopupState.existingFilter}
                filterOperators={filterOperators}
            />
        </Dialog>
    );
};

DataJoinPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    sourceNode: PropTypes.shape({
        name: PropTypes.string,
        columns: PropTypes.arrayOf(PropTypes.shape({
            name: PropTypes.string.isRequired,
            type: PropTypes.string,
            primary: PropTypes.bool
        }))
    }),
    targetNode: PropTypes.shape({
        name: PropTypes.string,
        columns: PropTypes.arrayOf(PropTypes.shape({
            name: PropTypes.string.isRequired,
            type: PropTypes.string,
            primary: PropTypes.bool
        }))
    }),
    existingJoin: PropTypes.object,
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
    metadata: PropTypes.shape({
        joinTypeOptions: PropTypes.arrayOf(PropTypes.string),
        filterOperators: PropTypes.arrayOf(PropTypes.string),
        joinTypeColorMapping: PropTypes.string
    })
};

DataJoinPopup.defaultProps = {
    existingJoin: null,
    graphAttributes: {},
    metadata: {
        joinTypeOptions: [],
        filterOperators: [],
        joinTypeColorMapping: ''
    }
};

export default DataJoinPopup;
