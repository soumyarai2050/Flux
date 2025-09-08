import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Box,
    Typography,
    Button,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    IconButton
} from '@mui/material';
import { Close } from '@mui/icons-material';

const FieldFilterPopup = ({
    open,
    onClose,
    onSave,
    columnName,
    existingFilter,
    filterOperators = []
}) => {
    const [formData, setFormData] = useState({
        user_natural_language_filter: '',
        operator: 'EQUALS',
        filter_values: ''
    });

    // Initialize form data when dialog opens or existingFilter changes
    useEffect(() => {
        if (open) {
            if (existingFilter) {
                setFormData({
                    user_natural_language_filter: existingFilter.user_natural_language_filter || '',
                    operator: existingFilter.operator || 'EQUALS',
                    filter_values: existingFilter.filter_values || ''
                });
            } else {
                setFormData({
                    user_natural_language_filter: '',
                    operator: filterOperators.length > 0 ? filterOperators[0] : 'EQUALS',
                    filter_values: ''
                });
            }
        }
    }, [open, existingFilter, filterOperators]);

    const handleInputChange = (field) => (event) => {
        setFormData(prev => ({
            ...prev,
            [field]: event.target.value
        }));
    };

    const handleSave = () => {
        // Create the filter object according to the schema
        const filterData = {
            user_natural_language_filter: formData.user_natural_language_filter.trim(),
            operator: formData.operator,
            filter_values: formData.filter_values.trim()
        };

        onSave(filterData);
        onClose();
    };

    const handleCancel = () => {
        onClose();
    };

    const isFormValid = () => {
        return formData.operator && (
            formData.user_natural_language_filter.trim() ||
            formData.filter_values.trim()
        );
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{
                style: { minHeight: '200px' }
            }}
        >
            <DialogTitle>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">
                        Field Filter: {columnName}
                    </Typography>
                    <IconButton onClick={handleCancel} size="small">
                        <Close />
                    </IconButton>
                </Box>
            </DialogTitle>

            <DialogContent style={{ padding: '10px' }}>
                <Box display="flex" flexDirection="column" gap={3}>
                    {/* Natural Language Filter Input */}
                    <TextField
                        fullWidth
                        label="Description (Natural Language)"
                        placeholder="e.g., 'Show only active orders' or 'Filter by last 30 days'"
                        value={formData.user_natural_language_filter}
                        onChange={handleInputChange('user_natural_language_filter')}
                        multiline
                        rows={2}
                        variant="outlined"
                    />

                    {/* Operator Selection */}
                    <FormControl fullWidth variant="outlined">
                        <InputLabel>Operator</InputLabel>
                        <Select
                            value={formData.operator}
                            onChange={handleInputChange('operator')}
                            label="Operator"
                        >
                            {filterOperators.map((operator) => (
                                <MenuItem key={operator} value={operator}>
                                    {operator.replace(/_/g, ' ')}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    {/* Filter Values Input */}
                    <TextField
                        fullWidth
                        label="Filter Values"
                        placeholder="e.g., 'value1,value2' or 'active' or '100'"
                        value={formData.filter_values}
                        onChange={handleInputChange('filter_values')}
                        variant="outlined"
                        helperText="For multiple values, separate with commas (e.g., value1,value2)"
                    />

                </Box>
            </DialogContent>

            <DialogActions style={{ padding: '8px 12px' }}>
                <Button onClick={handleCancel} color="inherit">
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    variant="contained"
                    color="primary"
                    disabled={!isFormValid()}
                >
                    Save Filter
                </Button>
            </DialogActions>
        </Dialog>
    );
};

FieldFilterPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    columnName: PropTypes.string,
    existingFilter: PropTypes.shape({
        user_natural_language_filter: PropTypes.string,
        operator: PropTypes.string,
        filter_values: PropTypes.string
    }),
    filterOperators: PropTypes.arrayOf(PropTypes.string)
};

FieldFilterPopup.defaultProps = {
    columnName: '',
    existingFilter: null,
    filterOperators: [
        'EQUALS',
        'NOT_EQUALS',
        'GREATER_THAN',
        'GREATER_THAN_OR_EQUAL',
        'LESS_THAN',
        'LESS_THAN_OR_EQUAL',
        'LIKE',
        'NOT_LIKE',
        'IN',
        'NOT_IN',
        'IS_NULL',
        'IS_NOT_NULL'
    ]
};

export default FieldFilterPopup;