import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useSelector } from 'react-redux';
import { COLOR_TYPES, DATA_TYPES, MODES } from '../constants';
import { Select, MenuItem, TextField, Autocomplete, Checkbox, InputAdornment, Tooltip, IconButton } from '@mui/material';
import { Error, Clear } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { getColorTypeFromValue, getValueFromReduxStoreFromXpath, isAllowedNumericValue, floatToInt, validateConstraints, getReducerArrrayFromCollections, capitalizeCamelCase, getDateTimeFromInt } from '../utils';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import classes from './NodeField.module.css';
import { cloneDeep, debounce } from 'lodash';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
dayjs.extend(utc);
dayjs.extend(timezone);
const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;


const NodeField = (props) => {
    // const state = useSelector(state => state);
    const reducerArray = useMemo(() => getReducerArrrayFromCollections([props.data]), [props.data]);
    const reducerDict = useSelector(state => {
        const selected = {};
        reducerArray.forEach(reducerName => {
            const fieldName = 'modified' + capitalizeCamelCase(reducerName);
            selected[reducerName] = {
                [fieldName]: state[reducerName]?.[fieldName],
            }
        })
        return selected;
    }, (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    })
    const validationError = useRef(null);
    const [inputValue, setInputValue] = useState(props.data.value);
    const [focus, setFocus] = useState(false);
    const [isDateTimePickerOpen, setIsDateTimePickerOpen] = useState(false);
    const [autocompleteInputValue, setAutocompleteInputValue] = useState('');
    const inputRef = useRef(null);
    const cursorPos = useRef(null);
    const autocompleteRef = useRef(null);
    const onTextChangeRef = useRef(props.data.onTextChange);

    useEffect(() => {
        onTextChangeRef.current = props.data.onTextChange;
    }, [props.data.onTextChange])

    useEffect(() => {
        setInputValue(props.data.value);
    }, [props.data.index])

    // useEffect(() => {
    //     if (props.data.forceUpdate) {
    //         setInputValue(props.data.value);
    //     }
    // }, [props.data.forceUpdate])

    useEffect(() => {
        if (props.mode === MODES.READ) {
            setInputValue(props.data.value);
        }
    }, [props.data.value])

    useEffect(() => {
        if (inputRef.current && focus && cursorPos.current !== null) {
            if (inputRef.current.selectionStart !== cursorPos.current) {
                inputRef.current.setSelectionRange(cursorPos.current, cursorPos.current);
            }
        }
    }, [inputValue])

    // useEffect(() => {
    //     if (props.data.onFormUpdate) {
    //         props.data.onFormUpdate(props.data.xpath, validationError.current);
    //     }
    //     return () => {
    //         if (props.data.onFormUpdate) {
    //             props.data.onFormUpdate(props.data.xpath, null);
    //         }
    //     }
    // }, [props.data.onFormUpdate])

    // Debounced transformation to update rows from the source JSON.
    const debouncedTransform = useRef(
        debounce((e, type, xpath, value, dataxpath, validationRes) => {
            onTextChangeRef.current(e, type, xpath, value, dataxpath, validationRes);
        }, 300)
    ).current;

    const handleBlur = () => {
        debouncedTransform.flush();
        setFocus(false);
    }

    const handleFocus = () => {
        setFocus(true);
    }

    const handleTextChange = (e, type, xpath, value, dataxpath, validationRes) => {
        cursorPos.current = e?.target.selectionStart ?? null;
        setInputValue(value);
        debouncedTransform(e, type, xpath, value, dataxpath, validationRes);
    }

    const handleKeyDown = (e, filteredOptions) => {
        if (e.keyCode === 13) {
            if (filteredOptions.length === 1) {
                props.data.onAutocompleteOptionChange(e, filteredOptions[0], props.data.dataxpath, props.data.xpath);
                setAutocompleteInputValue('');

                if (autocompleteRef.current) {
                    autocompleteRef.current.blur();
                }
            }
        }
    }

    let disabled = true;
    if (props.data.mode === MODES.EDIT) {
        if (props.data.ormNoUpdate && !props.data['data-add']) {
            disabled = true;
        }
        // disabled to allow object with ui update only to be created and edited
        // else if (props.data.uiUpdateOnly && props.data['data-add']) {
        //    disabled = true;
        // }
        else if (props.data['data-remove']) {
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
    const placeholder = props.data.placeholder ? props.data.placeholder : !props.data.required ? 'optional' : null;

    if (props.data.customComponentType === 'autocomplete') {
        let value = props.data.value ? props.data.value : props.data.value === 0 ? '0' : null;
        validationError.current = validateConstraints(props.data, value);

        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};

        return (
            <Autocomplete
                id={props.data.key}
                options={props.data.options}
                getOptionLabel={(option) => option?.toString()}
                isOptionEqualToValue={(option, value) => (
                    option == value || (option === 0 && value === 0)
                )}
                // disableClearable
                disabled={disabled}
                forcePopupIcon={false}
                variant='outlined'
                size='small'
                fullWidth
                sx={{ minWidth: '150px !important' }}
                className={`${classes.text_field} ${nodeFieldRemove} ${colorClass}`}
                required={props.data.required}
                value={value}
                inputValue={autocompleteInputValue}
                onInputChange={(e, newInputValue) => setAutocompleteInputValue(newInputValue)}
                filterOptions={(options, { inputValue }) =>
                    options.filter(option => String(option).toLowerCase().includes(inputValue.toLowerCase()))
                }
                onChange={(e, v) => {
                    props.data.onAutocompleteOptionChange(e, v, props.data.dataxpath, props.data.xpath);
                    setAutocompleteInputValue('');
                }}
                // componentsProps={{ popper: { style: { minWidth: 'fit-content', width: 'parent' } } }}
                renderInput={(params) => {
                    const filteredOptions = props.data.options.filter(option => String(option).toLowerCase().includes(autocompleteInputValue.toLowerCase()));
                    return (
                        <TextField
                            {...params}
                            name={props.data.key}
                            error={validationError.current !== null}
                            placeholder={placeholder}
                            onKeyDown={(e) => handleKeyDown(e, filteredOptions)}
                            inputRef={autocompleteRef}
                            InputProps={{
                                ...params.InputProps,
                                ...inputProps
                            }}
                        />
                    )
                }}
            />
        )
    } else if (props.data.type === DATA_TYPES.BOOLEAN) {
        let value = props.data.value ? props.data.value : props.data.value === false ? false : null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
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
    } else if (props.data.type === DATA_TYPES.ENUM) {
        let value = props.data.value ? props.data.value : null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
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
    } else if (props.data.type === DATA_TYPES.NUMBER) {
        // round the decimal places for float. default precision is 2 digits for float
        let decimalScale = 2;
        if (props.data.underlyingtype === DATA_TYPES.INT32 || props.data.underlyingtype === DATA_TYPES.INT64) {
            decimalScale = 0;
        }
        if (props.data.numberFormat && props.data.numberFormat.includes(".")) {
            decimalScale = props.data.numberFormat.split(".").pop();
            decimalScale = decimalScale * 1;
        }

        // min constrainsts for numeric field if set.
        let min = props.data.min;
        if (typeof (min) === DATA_TYPES.STRING) {
            min = getValueFromReduxStoreFromXpath(reducerDict, min);
        }

        // max constrainsts for numeric field if set.
        let max = props.data.max;
        if (typeof (max) === DATA_TYPES.STRING) {
            max = getValueFromReduxStoreFromXpath(reducerDict, max);
        }

        // let value = props.data.value ? props.data.value : props.data.value === 0 ? 0 : props.data.value === -0 ? -0 : '';
        let value = inputValue ? cloneDeep(inputValue) : inputValue === 0 ? 0 : inputValue === -0 ? -0 : '';
        if (props.data.displayType == DATA_TYPES.INTEGER && value !== -0 && value !== '') {
            value = floatToInt(value);
        }
        validationError.current = validateConstraints(props.data, value, min, max);

        const endAdornment = validationError.current || props.data.numberFormat ? (
            <>
                {props.data.numberFormat && props.data.numberFormat === '%' && (
                    <InputAdornment position='end'>%</InputAdornment>
                )}
                {props.data.numberFormat && props.data.numberFormat === 'bps' && (
                    <InputAdornment position='end'>bps</InputAdornment>
                )}
                {props.data.numberFormat && props.data.numberFormat === '$' && (
                    <InputAdornment position='end'>$</InputAdornment>
                )}
                {validationError.current && (
                    <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
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
                onValueChange={(values, sourceInfo) => handleTextChange(sourceInfo.event, props.data.type, props.data.xpath, values.value, props.data.dataxpath,
                    validateConstraints(props.data, values.value, min, max))}
                variant='outlined'
                decimalScale={decimalScale}
                placeholder={placeholder}
                onBlur={handleBlur}
                InputProps={inputProps}
                inputProps={{
                    style: { padding: '6px 10px' },
                    dataxpath: props.data.dataxpath,
                    underlyingtype: props.data.underlyingtype
                }}
            />
        )
    } else if (props.data.type === DATA_TYPES.DATE_TIME) {
        let value = props.data.value || null;
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
        ) : null;
        const inputProps = endAdornment ? {
            endAdornment: endAdornment
        } : {};
        // default input format
        let inputFormat = 'YYYY-MM-DD HH:mm:ss'
        if (value) {
            const dateTimeWithTimezone = getDateTimeFromInt(value);
            if (props.data.displayType !== 'datetime') {
                if (dateTimeWithTimezone.isSame(dayjs(), 'day')) {
                    inputFormat = 'HH:mm:ss';
                }
                // else not same day - use default input format
            }
            // else displayType is datetime -  use default input format
        }
        // else date is null - use default input format

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
                    inputFormat={inputFormat}
                    InputProps={inputProps}
                    onChange={(newValue) => {
                        const newDate = new Date(newValue);
                        newDate.setSeconds(0, 0);
                        props.data.onDateTimeChange(props.data.dataxpath, props.data.xpath, newDate.toISOString());
                    }}
                    inputProps={{
                        style: { padding: '6px 10px' },
                        dataxpath: props.data.dataxpath,
                        underlyingtype: props.data.underlyingtype
                    }}
                    hideTabs={false}
                    disablePast
                    openTo='hours'
                    open={isDateTimePickerOpen}
                    onClose={() => setIsDateTimePickerOpen(false)}
                    renderInput={(dateTimePickerProps) =>
                        <TextField
                            {...dateTimePickerProps}
                            onClick={() => {
                                if (value === null) {
                                    const newDate = new Date();
                                    newDate.setSeconds(0, 0);
                                    props.data.onDateTimeChange(props.data.dataxpath, props.data.xpath, newDate.toISOString());
                                }
                                setIsDateTimePickerOpen(true);
                            }}
                            InputProps={{
                                readOnly: true,
                                endAdornment: (
                                    <InputAdornment position='end'>
                                        <IconButton
                                            onClick={(e) => {
                                                props.data.onDateTimeChange(props.data.dataxpath, props.data.xpath, null);
                                                e.stopPropagation();
                                            }}
                                            disabled={!value}
                                            size='small'>
                                            <Clear fontSize='small' />
                                        </IconButton>
                                    </InputAdornment>
                                )
                            }}
                        />
                    }
                />
            </LocalizationProvider>
        )
    } else {
        let value = inputValue ? inputValue : '';
        validationError.current = validateConstraints(props.data, value);
        const endAdornment = validationError.current ? (
            <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
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
                focused={focus}
                onFocus={handleFocus}
                onBlur={handleBlur}
                value={value}
                disabled={disabled}
                onChange={(e) => handleTextChange(e, props.data.type, props.data.xpath, e.target.value, props.data.dataxpath,
                    validateConstraints(props.data, e.target.value))}
                onInput={(e) => handleTextChange(e, props.data.type, props.data.xpath, e.target.value, props.data.dataxpath,
                    validateConstraints(props.data, e.target.value))}
                variant='outlined'
                placeholder={placeholder}
                InputProps={inputProps}
                inputProps={{
                    ref: inputRef,
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
