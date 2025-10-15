import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Chip from '@mui/material/Chip';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import Search from '@mui/icons-material/Search';
import Clear from '@mui/icons-material/Clear';

const ColumnList = ({
    title,
    nodeName,
    columns,
    selectedColumns,
    confirmedConnections,
    aiSuggestions,
    rejectedSuggestionIds,
    onColumnToggle,
    selectedColumn,
    isSource,
    theme,
    isDarkMode,
    selectedSourceColumn
}) => {
    const [filterText, setFilterText] = useState('');

    const filteredColumns = useMemo(() => {
        if (!filterText.trim()) {
            return columns;
        }
        return columns.filter(column =>
            column.name.toLowerCase().includes(filterText.toLowerCase())
        );
    }, [columns, filterText]);

    const handleClearFilter = () => {
        setFilterText('');
    };

    return (
        <Box flex={1}>
            <Typography variant="subtitle2" gutterBottom color="primary">
                {title}
            </Typography>

            <TextField
                size="small"
                placeholder="Filter columns..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <Search style={{ fontSize: '18px' }} />
                        </InputAdornment>
                    ),
                    endAdornment: filterText && (
                        <InputAdornment position="end">
                            <IconButton
                                size="small"
                                onClick={handleClearFilter}
                                style={{ padding: '4px' }}
                            >
                                <Clear style={{ fontSize: '16px' }} />
                            </IconButton>
                        </InputAdornment>
                    )
                }}
                style={{
                    marginBottom: '12px',
                    backgroundColor: isDarkMode ? theme.palette.grey[800] : theme.palette.background.paper
                }}
                fullWidth
            />

            {selectedColumn && isSource && (
                <Typography variant="caption" style={{
                    color: theme.palette.primary.main,
                    fontWeight: 600,
                    backgroundColor: isDarkMode
                        ? theme.palette.primary.dark + '40'
                        : theme.palette.primary.light + '40',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    display: 'inline-block',
                    marginBottom: '8px'
                }}>
                    Selected: {selectedColumn} - Click a {nodeName} column above to connect
                </Typography>
            )}
            {selectedColumn && !isSource && !selectedSourceColumn && (
                <Typography variant="caption" style={{
                    color: theme.palette.warning.main,
                    fontWeight: 600,
                    backgroundColor: isDarkMode
                        ? theme.palette.warning.dark + '40'
                        : theme.palette.warning.light + '40',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    display: 'inline-block',
                    marginBottom: '8px'
                }}>
                    Select a {nodeName} column first
                </Typography>
            )}
            <Box style={{
                maxHeight: '200px',
                overflow: 'auto',
                border: `1px solid ${isDarkMode ? theme.palette.grey[600] : theme.palette.grey[300]}`,
                borderRadius: '8px',
                padding: '8px',
                backgroundColor: isDarkMode ? theme.palette.grey[800] : theme.palette.grey[50]
            }}>
                {filteredColumns.map((column, idx) => {
                    const isSelected = selectedColumns.some(col => col.field_name === column.name);
                    const selectedColumnObj = selectedColumns.find(col => col.field_name === column.name);
                    const hasFilters = selectedColumnObj?.field_filters?.length > 0;
                    const isConnected = confirmedConnections.some(conn =>
                        isSource ? conn.sourceColumn === column.name : conn.targetColumn === column.name
                    );
                    const hasAiSuggestion = aiSuggestions.some(suggestion =>
                        (isSource ? suggestion.sourceColumn === column.name : suggestion.targetColumn === column.name) &&
                        !rejectedSuggestionIds.has(suggestion.id)
                    );

                    return (
                        <Box key={idx} style={{
                            margin: '4px 0',
                            padding: '6px 8px',
                            backgroundColor: isSelected
                                ? (isDarkMode ? theme.palette.primary.dark + '40' : theme.palette.primary.light + '40')
                                : (isDarkMode ? theme.palette.grey[700] : theme.palette.background.paper),
                            borderRadius: '6px',
                            border: isConnected
                                ? `1px solid ${theme.palette.success.main}`
                                : isSelected
                                    ? `1px solid ${theme.palette.primary.main}`
                                    : `1px solid ${isDarkMode ? theme.palette.grey[600] : theme.palette.grey[300]}`
                        }}>
                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={isSelected}
                                        onChange={(e) => onColumnToggle(column.name, e.target.checked)}
                                        size="small"
                                    />
                                }
                                label={
                                    <Box>
                                        <Typography variant="body2" style={{
                                            fontWeight: isSelected || isConnected ? 600 : 400
                                        }}>
                                            {column.name}
                                            {isConnected && (
                                                <Chip
                                                    label="Connected"
                                                    size="small"
                                                    style={{
                                                        backgroundColor: '#4CAF50',
                                                        color: 'white',
                                                        marginLeft: '8px',
                                                        height: '16px',
                                                        fontSize: '9px'
                                                    }}
                                                />
                                            )}
                                            {hasFilters && (
                                                <Chip
                                                    label="Filtered"
                                                    size="small"
                                                    style={{
                                                        backgroundColor: '#2196F3',
                                                        color: 'white',
                                                        marginLeft: '4px',
                                                        height: '16px',
                                                        fontSize: '9px'
                                                    }}
                                                />
                                            )}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {column.type}
                                        </Typography>
                                    </Box>
                                }
                            />
                        </Box>
                    );
                })}

                {filteredColumns.length === 0 && filterText.trim() && (
                    <Box style={{
                        padding: '20px',
                        textAlign: 'center',
                        color: theme.palette.text.secondary,
                        fontStyle: 'italic'
                    }}>
                        <Typography variant="body2">
                            No columns match "{filterText}"
                        </Typography>
                    </Box>
                )}
            </Box>
        </Box>
    );
};

ColumnList.propTypes = {
    title: PropTypes.string.isRequired,
    nodeName: PropTypes.string.isRequired,
    columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.string.isRequired,
        primary: PropTypes.bool
    })).isRequired,
    selectedColumns: PropTypes.arrayOf(PropTypes.shape({
        field_name: PropTypes.string.isRequired,
        field_filters: PropTypes.array
    })).isRequired,
    confirmedConnections: PropTypes.arrayOf(PropTypes.object).isRequired,
    aiSuggestions: PropTypes.arrayOf(PropTypes.object).isRequired,
    rejectedSuggestionIds: PropTypes.instanceOf(Set).isRequired,
    onColumnToggle: PropTypes.func.isRequired,
    selectedColumn: PropTypes.string,
    isSource: PropTypes.bool.isRequired,
    theme: PropTypes.object.isRequired,
    isDarkMode: PropTypes.bool.isRequired,
    selectedSourceColumn: PropTypes.string
};

export default ColumnList;