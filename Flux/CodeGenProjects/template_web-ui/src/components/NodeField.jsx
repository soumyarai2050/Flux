import React from 'react';
import { useSelector } from 'react-redux';
import { ColorTypes, DataTypes, Modes } from '../constants';
import { Select, MenuItem, TextField, Autocomplete, Checkbox, InputAdornment } from '@mui/material';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { getColorTypeFromValue, getValueFromReduxStoreFromXpath, isAllowedNumericValue, floatToInt } from '../utils';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import classes from './NodeField.module.css';

const NodeField = (props) => {
    const state = useSelector(state => state);

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
        } else if (props.data.type === DataTypes.ENUM) {
            if (props.data.value.includes('UNSPECIFIED')) {
                error = true;
            }
        }
    }

    let color = '';
    if (props.data.color) {
        color = getColorTypeFromValue(props.data, props.data.value);
    }
    let colorClass = classes[color];

    let nodeFieldRemove = props.data['data-remove'] ? classes.remove : '';

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
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                required={props.data.required}
                value={props.data.value ? props.data.value : null}
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

        let min = props.data.min;
        if (typeof (min) === DataTypes.STRING) {
            min = getValueFromReduxStoreFromXpath(state, min);
        }

        let max = props.data.max;
        if (typeof (max) === DataTypes.STRING) {
            max = getValueFromReduxStoreFromXpath(state, max);
        }

        let value = props.data.value ? props.data.value : 0;

        let inputProps = {};
        if (props.data.numberFormat) {
            if (props.data.numberFormat === "%") {
                inputProps = {
                    endAdornment: <InputAdornment position="end">%</InputAdornment>
                }
            }
        }

        if (props.data.displayType == DataTypes.INTEGER) {
            value = floatToInt(value);
        }

        return (
            <NumericFormat
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                customInput={TextField}
                id={props.data.key}
                name={props.data.key}
                size='small'
                required={props.data.required}
                error={error}
                value={value}
                disabled={disabled}
                thousandSeparator=','
                isAllowed={(values) => isAllowedNumericValue(values.value, min, max)}
                onValueChange={(values, sourceInfo) => props.data.onTextChange(sourceInfo.event, props.data.type, props.data.xpath, values.value)}
                // onChange={(e) => props.data.onTextChange(e, props.data.type, props.data.xpath)}
                // onKeyDown={(e) => props.data.onKeyDown(e, props.data.type)}
                // type={props.data.type}
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
        return (
            <LocalizationProvider dateAdapter={AdapterDayjs}>
                <DateTimePicker
                    className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                    disabled={disabled}
                    error={error}
                    value={value}
                    inputFormat="DD-MM-YYYY HH:mm:ss"
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
        return (
            <TextField
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
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
