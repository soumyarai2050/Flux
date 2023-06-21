import React, { useEffect, useState, useRef } from 'react';
import { useSelector } from 'react-redux';
import { ColorTypes, DataTypes, Modes } from '../constants';
import { Select, MenuItem, TextField, Autocomplete, Checkbox, InputAdornment, Tooltip } from '@mui/material';
import { Error } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { getColorTypeFromValue, getValueFromReduxStoreFromXpath, isAllowedNumericValue, floatToInt, validateConstraints } from '../utils';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import classes from './NodeField.module.css';

const NodeField = (props) => {
    const state = useSelector(state => state);
    const validationError = useRef(null);

    useEffect(() => {
        if (props.data.onFormUpdate) {
            props.data.onFormUpdate(props.data.xpath, validationError.current);
        }
    }, [props.data.onFormUpdate])

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

    let color = '';
    if (props.data.color) {
        color = getColorTypeFromValue(props.data, props.data.value);
    }
    let colorClass = classes[color];

    let nodeFieldRemove = props.data['data-remove'] ? classes.remove : '';

    if (props.data.customComponentType === 'autocomplete') {
        let value = props.data.value ? props.data.value : null;
        validationError.current = validateConstraints(props.data, value);

        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};

        return (
            <Autocomplete
                id={props.data.key}
                options={props.data.options}
                getOptionLabel={(option) => option}
                isOptionEqualToValue={(option, value) => option == value}
                disableClearable
                disabled={disabled}
                forcePopupIcon={false}
                variant='outlined'
                size='small'
                sx={{ minWidth: '150px !important' }}
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                required={props.data.required}
                value={value}
                onChange={(e, v) => props.data.onAutocompleteOptionChange(e, v, props.data.dataxpath, props.data.xpath)}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        name={props.data.key}
                        error={validationError.current !== null}
                        placeholder={props.data.placeholder}
                        InputProps={{
                            ...params.InputProps,
                            ...inputProps
                        }}
                    />
                )}
            />
        )
    } else if (props.data.type === DataTypes.BOOLEAN) {
        let value = props.data.value ? props.data.value : props.data.value === false ? false : null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};
        return (
            <Checkbox
                id={props.data.key}
                name={props.data.key}
                className={`${classes.checkbox} ${nodeFieldRemove} ${colorClass}`}
                defaultValue={false}
                required={props.data.required}
                checked={value}
                disabled={disabled}
                error={validationError.current}
                onChange={(e) => props.data.onCheckboxChange(e, props.data.dataxpath, props.data.xpath)}
            />
        )
    } else if (props.data.type === DataTypes.ENUM) {
        let value = props.data.value ? props.data.value : null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        return (
            <Select
                id={props.data.key}
                name={props.data.key}
                className={`${classes.select} ${nodeFieldRemove} ${colorClass}`}
                value={value}
                onChange={(e) => props.data.onSelectItemChange(e, props.data.dataxpath, props.data.xpath)}
                size='small'
                endAdornment={endAdornment}
                error={validationError.current !== null}
                required={props.data.required}
                disabled={disabled}>
                {props.data.dropdowndataset && props.data.dropdowndataset.map((val) => {
                    return <MenuItem key={val} value={val}>
                        {val}
                    </MenuItem>
                })}
            </Select>
        )
    } else if (props.data.type === DataTypes.NUMBER) {
        // round the decimal places for float. default precision is 2 digits for float
        let decimalScale = 2;
        if (props.data.underlyingtype === DataTypes.INT32 || props.data.underlyingtype === DataTypes.INT64) {
            decimalScale = 0;
        }
        if (props.data.numberFormat && props.data.numberFormat.includes(".")) {
            decimalScale = props.data.numberFormat.split(".").pop();
            decimalScale = decimalScale * 1;
        }

        // min constrainsts for numeric field if set.
        let min = props.data.min;
        if (typeof (min) === DataTypes.STRING) {
            min = getValueFromReduxStoreFromXpath(state, min);
        }

        // max constrainsts for numeric field if set.
        let max = props.data.max;
        if (typeof (max) === DataTypes.STRING) {
            max = getValueFromReduxStoreFromXpath(state, max);
        }

        let value = props.data.value ? props.data.value : props.data.value === 0 ? 0 : '';
        if (props.data.displayType == DataTypes.INTEGER) {
            if (value !== '') {
                value = floatToInt(value);
            }
        }
        validationError.current = validateConstraints(props.data, value, min, max);

        const endAdornment = validationError.current || props.data.numberFormat ? (
            <>
                {props.data.numberFormat && props.data.numberFormat === '%' && (
                    <InputAdornment position='end'>%</InputAdornment>
                )}
                {validationError.current && (
                    <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
                )}

            </>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};

        return (
            <NumericFormat
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                customInput={TextField}
                id={props.data.key}
                name={props.data.key}
                size='small'
                required={props.data.required}
                error={validationError.current !== null}
                value={value}
                disabled={disabled}
                thousandSeparator=','
                // isAllowed={(values) => isAllowedNumericValue(values.value, min, max)}
                onValueChange={(values, sourceInfo) => props.data.onTextChange(sourceInfo.event, props.data.type, props.data.xpath, values.value, props.data.dataxpath,
                    validateConstraints(props.data, values.value, min, max))}
                variant='outlined'
                decimalScale={decimalScale}
                placeholder={props.data.placeholder}
                InputProps={inputProps}
                inputProps={{
                    style: { padding: '6px 10px' },
                    dataxpath: props.data.dataxpath,
                    underlyingtype: props.data.underlyingtype
                }}
            />
        )
    } else if (props.data.type === DataTypes.DATE_TIME) {
        let value = props.data.value ? new Date(props.data.value) : null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};

        return (
            <LocalizationProvider dateAdapter={AdapterDayjs}>
                <DateTimePicker
                    id={props.data.key}
                    name={props.data.key}
                    className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                    disabled={disabled}
                    error={validationError.current !== null}
                    value={value}
                    required={props.data.required}
                    inputFormat="DD-MM-YYYY HH:mm:ss"
                    InputProps={inputProps}
                    onChange={(newValue) => props.data.onDateTimeChange(props.data.dataxpath, props.data.xpath, new Date(newValue).toISOString())}
                    inputProps={{
                        style: { padding: '6px 10px' },
                        dataxpath: props.data.dataxpath,
                        underlyingtype: props.data.underlyingtype
                    }}
                    renderInput={(props) => <TextField {...props} />}
                />
            </LocalizationProvider>
        )
    } else {
        let value = props.data.value ? props.data.value : '';
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};
        return (
            <TextField
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                id={props.data.key}
                name={props.data.key}
                size='small'
                required={props.data.required}
                error={validationError.current !== null}
                value={value}
                disabled={disabled}
                onChange={(e) => props.data.onTextChange(e, props.data.type, props.data.xpath, e.target.value, props.data.dataxpath,
                    validateConstraints(props.data, e.target.value))}
                variant='outlined'
                placeholder={props.data.placeholder}
                InputProps={inputProps}
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
