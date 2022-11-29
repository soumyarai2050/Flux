import React from 'react';
import { makeStyles } from '@mui/styles';
import { DataTypes, Modes } from '../constants';
import { Select, MenuItem, TextField, Autocomplete, Checkbox } from '@mui/material';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    autocomplete: {
        background: 'white',
        '& .Mui-disabled': {
            cursor: 'not-allowed !important',
            background: 'rgba(0,0,0,0.1)',
            '-webkit-text-fill-color': '#444 !important',
            fontWeight: 'bold'
        },
        '& .Mui-error': {
            background: 'rgba(242, 121, 129, 0.4)'
        }
    },
    checkbox: {
        padding: '6px !important'
    },
    select: {
        background: 'white',
        '& .MuiSelect-outlined': {
            padding: '6px 10px'
        },
        '& .Mui-disabled': {
            cursor: 'not-allowed !important',
            background: 'rgba(0,0,0,0.1)',
            '-webkit-text-fill-color': '#444 !important',
            fontWeight: 'bold'
        }
    },
    textField: {
        background: 'white',
        '& .Mui-disabled': {
            cursor: 'not-allowed',
            background: 'rgba(0,0,0,0.05)',
            '-webkit-text-fill-color': '#444 !important',
            fontWeight: 'bold'
        },
        '& .Mui-error': {
            background: 'rgba(242, 121, 129, 0.4)'
        }
    },
    nodeFieldRemove: {
        textDecoration: 'line-through'
    }
})

const NodeField = (props) => {

    const classes = useStyles();

    let disabled = true;
    if (props.data.mode === Modes.EDIT_MODE) {
        if (props.data.ormNoUpdate && !props.data['data-add']) {
            disabled = true;
        } else if (props.data['data-remove']) {
            disabled = true;
        } else {
            disabled = false;
        }
    }

    let error = false;
    if (props.data.required && props.data.mode === Modes.EDIT_MODE) {
        if (props.data.type === DataTypes.STRING) {
            if (!props.data.value || (props.data.value && props.data.value === '')) {
                error = true;
            }
        } else if (props.data.type === DataTypes.NUMBER) {
            if (!props.data.value && props.data.value !== 0) {
                error = true;
            }
        }
    }

    let nodeFieldRemove = props.data['data-remove'] ? classes.nodeFieldRemove : '';

    if (props.data.type === DataTypes.BOOLEAN) {
        return (
            <Checkbox
                className={`${classes.checkbox} ${nodeFieldRemove}`}
                defaultValue={false}
                checked={props.data.value ? props.data.value : false}
                disabled={disabled}
                onChange={(e) => props.data.onCheckboxChange(e, props.data.dataxpath)}
            />
        )
    } else if (props.data.type === DataTypes.ENUM) {
        if (props.data.customComponentType === 'autocomplete') {
            return (
                <Autocomplete
                    options={props.data.options}
                    getOptionLabel={(option) => option}
                    isOptionEqualToValue={(option, value) => option == value}
                    disableClearable
                    disabled={disabled}
                    variant='outlined'
                    size='small'
                    sx={{ minWidth: 160 }}
                    className={`${classes.textField} ${nodeFieldRemove}`}
                    required={props.data.required}
                    value={props.data.value}
                    onChange={(e, v) => props.data.onAutocompleteOptionChange(e, v, props.data.dataxpath)}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            error={error}
                        />
                    )}
                />
            )
        } else {
            return (
                <Select
                    className={`${classes.select} ${nodeFieldRemove}`}
                    value={props.data.value ? props.data.value : ''}
                    onChange={(e) => props.data.onSelectItemChange(e, props.data.dataxpath)}
                    size='small'
                    disabled={disabled}>
                    {props.data.dropdowndataset && props.data.dropdowndataset.map((val) => {
                        return <MenuItem key={val} value={val}>
                            {val}
                        </MenuItem>
                    })}
                </Select>
            )
        }
    } else {
        if (props.data.customComponentType === 'autocomplete') {
            return (
                <Autocomplete
                    options={props.data.options}
                    getOptionLabel={(option) => option}
                    isOptionEqualToValue={(option, value) => option == value}
                    disableClearable
                    disabled={disabled}
                    variant='outlined'
                    size='small'
                    sx={{ minWidth: 160 }}
                    className={`${classes.textField} ${nodeFieldRemove}`}
                    required={props.data.required}
                    value={props.data.value}
                    onChange={(e, v) => props.data.onAutocompleteOptionChange(e, v, props.data.dataxpath)}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            error={error}
                        />
                    )}
                />
            )
        }

        return (
            <TextField
                className={`${classes.textField} ${nodeFieldRemove}`}
                id={props.data.name}
                name={props.data.name}
                size='small'
                required={props.data.required}
                error={error}
                value={props.data.value ? props.data.value : props.data.type === DataTypes.NUMBER ? 0 : ''}
                disabled={disabled}
                onChange={(e) => props.data.onTextChange(e, props.data.type)}
                type={props.data.type}
                variant='outlined'
                inputProps={{
                    style: { padding: '6px 10px' },
                    xpath: props.data.dataxpath
                }}
            />
        )
    }
}

NodeField.propTypes = {
    data: PropTypes.object
}

export default NodeField;
