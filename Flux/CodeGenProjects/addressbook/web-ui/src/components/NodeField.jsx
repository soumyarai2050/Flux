import React from 'react';
import { makeStyles } from '@mui/styles';
import { ColorTypes, DataTypes, Modes } from '../constants';
import { Select, MenuItem, TextField, Autocomplete, Checkbox } from '@mui/material';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { getColorTypeFromValue } from '../utils';

const useStyles = makeStyles({
    autocomplete: {
        background: 'white',
        '& .Mui-disabled': {
            cursor: 'not-allowed !important',
            background: 'rgba(0,0,0,0.1)',
            '-webkit-text-fill-color': '#444 !important',
            fontWeight: 'bold'
        },
        // '& .Mui-error': {
        //     background: 'rgba(242, 121, 129, 0.4)'
        // }
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
        // '& .Mui-error': {
        //     background: 'rgba(242, 121, 129, 0.4)'
        // }
    },
    nodeFieldRemove: {
        textDecoration: 'line-through'
    },
    nodeFieldCritical: {
        color: '#9C0006 !important',
        background: '#ffc7ce',
        animation: `$blink 0.5s step-start infinite`
    },
    nodeFieldError: {
        color: '#9C0006 !important',
        background: '#ffc7ce'
    },
    nodeFieldWarning: {
        color: '#9c6500 !important',
        background: '#ffeb9c'
    },
    nodeFieldInfo: {
        color: 'blue !important',
        background: '#c2d1ff'
    },
    nodeFieldSuccess: {
        color: 'darkgreen !important',
        background: '#c6efce !important'
    },
    nodeFieldDebug: {
        color: 'black !important',
        background: '#ccc'
    },
    "@keyframes blink": {
        "from": {
            opacity: 1
        },
        "50%": {
            opacity: 0.8
        },
        "to": {
            opacity: 1
        }
    }
})

const NodeField = (props) => {

    const classes = useStyles();

    let disabled = true;
    if (props.data.mode === Modes.EDIT_MODE) {
        if (props.data.ormNoUpdate && !props.data['data-add']) {
            disabled = true;
        } else if (props.data.uiUpdateOnly && props.data['data-add']) {
            disabled = true;
        } else if (props.data['data-remove']) {
            disabled = true;
        } else {
            disabled = false;
        }
    }

    let error = false;
    if (props.data.required && props.data.mode === Modes.EDIT_MODE && props.data['data-add']) {
        if (props.data.type === DataTypes.STRING) {
            if (!props.data.value || (props.data.value && props.data.value === '')) {
                error = true;
            }
        } else if (props.data.type === DataTypes.NUMBER) {
            if (!props.data.value) {
                error = true;
            }
        } else if(props.data.type === DataTypes.ENUM) {
            if(props.data.value.includes('UNSPECIFIED')) {
                error = true;
            }
        }
    }

    let color = '';
    let colorClass = '';
    if(props.data.color) {
        color = getColorTypeFromValue(props.data, props.data.value);
    } 
    if (color === ColorTypes.CRITICAL) colorClass = classes.nodeFieldCritical;
    else if (color === ColorTypes.ERROR) colorClass = classes.nodeFieldError;
    else if (color === ColorTypes.WARNING) colorClass = classes.nodeFieldWarning;
    else if (color === ColorTypes.INFO) colorClass = classes.nodeFieldInfo;
    else if (color === ColorTypes.DEBUG) colorClass = classes.nodeFieldDebug;
    else if (color === ColorTypes.SUCCESS) colorClass = classes.nodeFieldSuccess;

    let nodeFieldRemove = props.data['data-remove'] ? classes.nodeFieldRemove : '';

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
                className={`${classes.textField} ${nodeFieldRemove} ${colorClass}`}
                required={props.data.required}
                value={props.data.value}
                onChange={(e, v) => props.data.onAutocompleteOptionChange(e, v, props.data.dataxpath, props.data.xpath)}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        error={error}
                        placeholder={props.data.placeholder}
                    />
                )}
            />
        )
    } else if (props.data.type === DataTypes.BOOLEAN) {
        return (
            <Checkbox
                className={`${classes.checkbox} ${nodeFieldRemove} ${colorClass}`}
                defaultValue={false}
                checked={props.data.value ? props.data.value : false}
                disabled={disabled}
                onChange={(e) => props.data.onCheckboxChange(e, props.data.dataxpath, props.data.xpath)}
            />
        )
    } else if (props.data.type === DataTypes.ENUM) {
        return (
            <Select
                className={`${classes.select} ${nodeFieldRemove} ${colorClass}`}
                value={props.data.value ? props.data.value : ''}
                onChange={(e) => props.data.onSelectItemChange(e, props.data.dataxpath, props.data.xpath)}
                size='small'
                error={error}
                disabled={disabled}>
                {props.data.dropdowndataset && props.data.dropdowndataset.map((val) => {
                    return <MenuItem key={val} value={val}>
                        {val}
                    </MenuItem>
                })}
            </Select>
        )
    } else if (props.data.type === DataTypes.NUMBER) {
        let decimalScale = 2;
        if (props.data.underlyingtype === DataTypes.INT32 || props.data.underlyingtype === DataTypes.INT64) {
            decimalScale = 0;
        }
        let value = props.data.value ? props.data.value : 0;
        return (
            <NumericFormat
                className={`${classes.textField} ${nodeFieldRemove} ${colorClass}`}
                customInput={TextField}
                id={props.data.key}
                name={props.data.key}
                size='small'
                required={props.data.required}
                error={error}
                value={value}
                disabled={disabled}
                thousandSeparator=','
                onValueChange={(values, sourceInfo) => props.data.onTextChange(sourceInfo.event, props.data.type, props.data.xpath, values.value)}
                // onChange={(e) => props.data.onTextChange(e, props.data.type, props.data.xpath)}
                // onKeyDown={(e) => props.data.onKeyDown(e, props.data.type)}
                // type={props.data.type}
                variant='outlined'
                decimalScale={decimalScale}
                placeholder={props.data.placeholder}
                inputProps={{
                    style: { padding: '6px 10px' },
                    dataxpath: props.data.dataxpath,
                    underlyingtype: props.data.underlyingtype
                }}
            />
        )
    } else {
        let value = props.data.value ? props.data.value : '';
        return (
            <TextField
                className={`${classes.textField} ${nodeFieldRemove} ${colorClass}`}
                id={props.data.key}
                name={props.data.key}
                size='small'
                required={props.data.required}
                error={error}
                value={value}
                disabled={disabled}
                onChange={(e) => props.data.onTextChange(e, props.data.type, props.data.xpath, e.target.value)}
                // onKeyDown={(e) => props.data.onKeyDown(e, props.data.type)}
                // type={props.data.type}
                variant='outlined'
                placeholder={props.data.placeholder}
                inputProps={{
                    style: { padding: '6px 10px' },
                    dataxpath: props.data.dataxpath,
                    underlyingtype: props.data.underlyingtype
                }}
            />
        )
    }
}

NodeField.propTypes = {
    data: PropTypes.object
}

export default NodeField;
