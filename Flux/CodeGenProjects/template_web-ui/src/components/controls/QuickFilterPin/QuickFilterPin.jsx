import React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Switch from '@mui/material/Switch';
import IconButton from '@mui/material/IconButton';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Close from '@mui/icons-material/Close';
import styles from './QuickFilterPin.module.css';

const QuickFilterPin = ({ 
    nodeKey, 
    uniqueId,
    nodeTitle, 
    nodeValue, 
    nodeData,
    onValueChange, 
    onUnpin
}) => {

    const handleValueChange = (newValue) => {
        onValueChange(uniqueId, newValue);
    };

    const handleUnpin = () => {
        onUnpin(uniqueId);
    };

    // Render the appropriate input based on field type
    const renderFieldInput = () => {
        if (!nodeData) {
            // Fallback to boolean toggle if no nodeData
            return (
                <Switch
                    size="small"
                    checked={!!nodeValue}
                    onChange={(e) => handleValueChange(e.target.checked)}
                    onClick={(e) => e.stopPropagation()}
                />
            );
        }

        const { type, customComponentType, options, dropdowndataset } = nodeData;

        // Boolean field - render switch
        if (type === 'boolean') {
            return (
                <Switch
                    size="small"
                    checked={!!nodeValue}
                    onChange={(e) => handleValueChange(e.target.checked)}
                    onClick={(e) => e.stopPropagation()}
                />
            );
        }

        // Enum or autocomplete field - render dropdown
        if (type === 'enum' || customComponentType === 'autocomplete' || options || dropdowndataset) {
            const optionsList = options || dropdowndataset || [];
            
            if (optionsList.length > 0) {
                return (
                    <Select
                        size="small"
                        value={nodeValue || ''}
                        onChange={(e) => handleValueChange(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        className={styles.pin_select}
                    >
                        {optionsList.map((option) => (
                            <MenuItem key={option} value={option}>
                                {option}
                            </MenuItem>
                        ))}
                    </Select>
                );
            }
        }

        // Number field - render number input
        if (type === 'number') {
            return (
                <TextField
                    size="small"
                    type="number"
                    value={nodeValue || ''}
                    onChange={(e) => handleValueChange(Number(e.target.value))}
                    onClick={(e) => e.stopPropagation()}
                    className={styles.pin_input}
                />
            );
        }

        // String field - render text input
        if (type === 'string') {
            return (
                <TextField
                    size="small"
                    value={nodeValue || ''}
                    onChange={(e) => handleValueChange(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className={styles.pin_input}
                />
            );
        }

        // Default fallback - boolean switch
        return (
            <Switch
                size="small"
                checked={!!nodeValue}
                onChange={(e) => handleValueChange(e.target.checked)}
                onClick={(e) => e.stopPropagation()}
            />
        );
    };

    return (
        <Tooltip 
            title={`Path: ${nodeData?.dataxpath || uniqueId || 'N/A'}`}
            placement="top"
            arrow
        >
            <Box className={styles.pin_container}>
                <Chip 
                    label={
                        <Box className={styles.pin_content}>
                            <span className={styles.pin_title}>{nodeTitle}</span>
                            <Box className={styles.pin_input_container}>
                                {renderFieldInput()}
                            </Box>
                            <IconButton 
                                size="small" 
                                onClick={handleUnpin}
                                className={styles.close_button}
                            >
                                <Close fontSize="small" />
                            </IconButton>
                        </Box>
                    }
                    variant="outlined"
                    className={styles.pin_chip}
                />
            </Box>
        </Tooltip>
    );
};

export default QuickFilterPin; 