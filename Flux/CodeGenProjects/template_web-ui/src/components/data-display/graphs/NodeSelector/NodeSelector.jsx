import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
    Autocomplete,
    TextField,
    Checkbox,
    Box,
    Chip,
    Typography,
    useTheme
} from '@mui/material';

const NodeSelector = ({ 
    availableNodes = [], 
    selectedNodes = [],
    nodeTypeColorMap = {},
    mode = 'edit',
    onChange,
    nodeNameField,
    nodeTypeField,
    nodeAccessField,
    placeholder = "Search nodes...",
    label = ""
}) => {
    const theme = useTheme();

    // Parse node string format: "name|type|availability"
    const parseNodeString = (nodeString) => {
        if (!nodeString || typeof nodeString !== 'string') return null;
        
        const parts = nodeString.split('|'); 
        
        const [name, nodeType, availabilityPart] = parts;
        const isAvailable = availabilityPart.includes('true'); 
        
        return {
            [nodeNameField]: name.trim(),
            displayName: name.trim(), // Keep original for display
            [nodeTypeField]: nodeType.trim(),
            [nodeAccessField]: isAvailable,
            originalString: nodeString
        };
    };

    // Parse all available nodes from strings
    const parsedNodes = useMemo(() => {
        return availableNodes
            .map(nodeString => parseNodeString(nodeString))
            .filter(Boolean);
    }, [availableNodes]);

    // Get color for node type from MUI theme
    const getNodeTypeColor = (nodeType) => {
        const colorType = nodeTypeColorMap[nodeType];
        if (!colorType) return theme.palette.grey[500]; // Grey fallback
        
        const colorMap = {
            critical: theme.palette.error.main,
            error: theme.palette.error.main,
            warning: theme.palette.warning.main,
            info: theme.palette.info.main,
            debug: theme.palette.grey[600],
            success: theme.palette.success.main
        };
        
        return colorMap[colorType] || theme.palette.grey[500];
    };

    // Handle autocomplete change
    const handleAutocompleteChange = (event, selectedOptions) => {
        if (mode === 'read' || !onChange) return;

        onChange(selectedOptions);
    };

    // Convert selectedNodes to format expected by autocomplete
    const selectedOptions = useMemo(() => {
        return selectedNodes.map(node => ({
            [nodeNameField]: node[nodeNameField],
            displayName: node[nodeNameField],
            [nodeTypeField]: node[nodeTypeField],
            [nodeAccessField]: node[nodeAccessField]
        }));
    }, [selectedNodes, nodeNameField, nodeTypeField, nodeAccessField]);

    return (
        <Box sx={{ minWidth: 280, maxWidth: 450 }}>
            <Autocomplete
                multiple
                disableCloseOnSelect
                value={selectedOptions}
                onChange={handleAutocompleteChange}
                options={parsedNodes}
                size="small"
                getOptionLabel={(option) => option.displayName}
                isOptionEqualToValue={(option, value) => option[nodeNameField] === value[nodeNameField]}
                filterOptions={(options, { inputValue }) => {
                    return options.filter(option => 
                        option.displayName.toLowerCase().includes(inputValue.toLowerCase()) ||
                        option[nodeTypeField].toLowerCase().includes(inputValue.toLowerCase())
                    );
                }}
                renderOption={(props, option, { selected }) => (
                    <Box component="li" {...props} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, py: 0.5 }}>
                        <Checkbox
                            checked={selected}
                            size="small"
                            sx={{ mr: 0.5, p: 0.5 }}
                        />
                        <Box 
                            sx={{ 
                                width: 10, 
                                height: 10, 
                                borderRadius: '50%',
                                backgroundColor: getNodeTypeColor(option[nodeTypeField]),
                                border: option[nodeAccessField] ? 'none' : `2px dotted ${getNodeTypeColor(option[nodeTypeField])}`, 
                                backgroundColor: option[nodeAccessField] ? getNodeTypeColor(option[nodeTypeField]) : 'transparent',
                                mr: 0.5
                            }}
                        />
                        <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.875rem' }}>
                            {option.displayName}
                        </Typography>
                    </Box>
                )}
                renderTags={(tagValue, getTagProps) =>
                    tagValue.map((option, index) => (
                        <Chip
                            key={option[nodeNameField]}
                            label={option.displayName}
                            {...getTagProps({ index })}
                            size="small"
                            variant="outlined"
                            sx={{
                                height: 24,
                                fontSize: '0.75rem',
                                borderColor: getNodeTypeColor(option[nodeTypeField]),
                                color: getNodeTypeColor(option[nodeTypeField]),
                                '& .MuiChip-deleteIcon': {
                                    color: getNodeTypeColor(option[nodeTypeField]),
                                    fontSize: '1rem'
                                }
                            }}
                        />
                    ))
                }
                renderInput={(params) => {
                    let displayValue = '';
                    if (selectedOptions.length === 1) {
                        displayValue = selectedOptions[0].displayName;
                    } else if (selectedOptions.length > 1) {
                        displayValue = `${selectedOptions.length} nodes selected`;
                    }
                    
                    return (
                        <TextField
                            {...params}
                            label={label}
                            placeholder={selectedOptions.length === 0 ? placeholder : ""}
                            variant="outlined"
                            size="small"
                            disabled={mode === 'read'}
                            InputProps={{
                                ...params.InputProps,
                                startAdornment: selectedOptions.length > 0 ? (
                                    <Typography variant="body2" sx={{ mr: 1, color: 'text.primary' }}>
                                        {displayValue}
                                    </Typography>
                                ) : params.InputProps.startAdornment
                            }}
                            sx={{
                                '& .MuiOutlinedInput-root': {
                                    minHeight: 40,
                                    padding: '4px 8px',
                                },
                                '& .MuiInputLabel-root': {
                                    fontSize: '0.875rem'
                                }
                            }}
                        />
                    );
                }}
                ListboxProps={{
                    style: {
                        maxHeight: 250,
                    }
                }}
                disabled={mode === 'read'}
            />
        </Box>
    );
};

NodeSelector.propTypes = {
    availableNodes: PropTypes.arrayOf(PropTypes.string),
    selectedNodes: PropTypes.arrayOf(PropTypes.object),
    nodeTypeColorMap: PropTypes.objectOf(PropTypes.oneOf(['critical', 'error', 'warning', 'info', 'debug', 'success'])),
    mode: PropTypes.oneOf(['edit', 'read']),
    onChange: PropTypes.func,
    nodeNameField: PropTypes.string.isRequired,
    nodeTypeField: PropTypes.string.isRequired,
    nodeAccessField: PropTypes.string.isRequired,
    placeholder: PropTypes.string,
    label: PropTypes.string
};

export default React.memo(NodeSelector);