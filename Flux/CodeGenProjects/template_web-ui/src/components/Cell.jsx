import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, isEqual } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener, InputAdornment } from '@mui/material';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { Error } from '@mui/icons-material';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import {
    clearxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue,
    getHoverTextType, getValueFromReduxStoreFromXpath, isAllowedNumericValue, floatToInt, validateConstraints, getLocalizedValueAndSuffix
} from '../utils';
import { DataTypes, Modes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';
import classes from './Cell.module.css';

const Cell = (props) => {
    const {
        mode,
        rowindex,
        collection,
        xpath,
        dataxpath,
        disabled,
        dataRemove,
        currentValue,
        previousValue,
        buttonDisable
    } = props;

    const state = useSelector(state => state);
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);
    const [oldValue, setOldValue] = useState(null);
    const [newUpdateClass, setNewUpdateClass] = useState("");
    const timeoutRef = useRef(null);
    const validationError = useRef(null);

    useEffect(() => {
        if (props.onFormUpdate && xpath) {
            props.onFormUpdate(xpath, validationError.current);
        }
    }, [validationError.current])

    useEffect(() => {
        if (props.highlightUpdate && currentValue !== oldValue) {
            setNewUpdateClass(classes.new_update);
            if (timeoutRef.current !== null) {
                clearTimeout(timeoutRef.current);
            }
            timeoutRef.current = setTimeout(() => {
                setNewUpdateClass("");
            }, 1500);
            setOldValue(currentValue);
        }
    }, [currentValue, oldValue, timeoutRef, classes, props.highlightUpdate])

    const onFocusIn = useCallback(() => {
        setActive(true);
    }, [])

    const onFocusOut = useCallback(() => {
        setActive(false);
    }, [])

    const onOpenTooltip = useCallback(() => {
        setOpen(true);
    }, [])

    const onCloseTooltip = useCallback(() => {
        setOpen(false);
    }, [])

    const onKeyDown = useCallback((e) => {
        if (e.keyCode == 13) {
            onFocusOut();
        }
    }, [])

    let type = DataTypes.STRING;
    let enumValues = [];
    let required = false;

    let value = currentValue;
    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
        required = collection.required;

        if (collection.autocomplete) {
            value = value ? value : null;
        } else if (type === DataTypes.BOOLEAN) {
            value = value ? value : value === false ? false : null;
        } else if (type === DataTypes.ENUM) {
            value = value ? value : null;
        } else if (type === DataTypes.NUMBER) {
            value = value ? value : value === 0 ? 0 : '';
            if (collection.displayType === DataTypes.INTEGER) {
                if (value !== '') {
                    value = floatToInt(value);
                }
            }
        } else if (type === DataTypes.DATE_TIME) {
            value = value ? value : null;
        } else if (type === DataTypes.STRING) {
            value = value ? value : '';
        }
    }
    let color = getColorTypeFromValue(collection, currentValue);
    let tableCellColorClass = classes[color];
    let tableCellRemove = dataRemove ? classes.remove : '';
    let disabledClass = disabled ? classes.disabled : '';
    if (props.ignoreDisable) {
        disabledClass = "";
    }
    let textAlign = collection.textAlign ? collection.textAlign : 'center';

    if (disabled) {
        if (value === null) {
            value = '';
        }
        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
        value = v;
        if (typeof value === DataTypes.NUMBER) {
            value = value.toLocaleString();
        }
        return <TableCell className={`${classes.cell} ${disabledClass} ${tableCellColorClass} ${tableCellRemove} ${newUpdateClass}`} align={textAlign} size='medium' data-xpath={xpath} data-dataxpath={dataxpath}>{value}{numberSuffix}</TableCell>
    }

    if (mode === Modes.EDIT_MODE && active && !disabled) {
        if (collection.autocomplete) {
            validationError.current = validateConstraints(collection, value);

            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};

            return (
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Autocomplete
                        id={collection.key}
                        options={collection.options}
                        getOptionLabel={(option) => option}
                        isOptionEqualToValue={(option, value) => option == value}
                        disableClearable
                        disabled={disabled}
                        forcePopupIcon={false}
                        variant='outlined'
                        size='small'
                        sx={{ minWidth: '120px !important' }}
                        className={classes.text_field}
                        required={required}
                        // clearOnBlur={false}
                        value={collection.value}
                        onBlur={onFocusOut}
                        autoFocus
                        onChange={(e, v) => props.onAutocompleteOptionChange(e, v, dataxpath, xpath)}
                        renderInput={(params) => (
                            <TextField
                                {...params}
                                name={collection.key}
                                error={validationError.current !== null}
                                placeholder={collection.placeholder}
                                InputProps={{
                                    ...params.InputProps,
                                    ...inputProps
                                }}
                            />
                        )}
                    />
                </TableCell>
            )
        } else if (type === DataTypes.BOOLEAN) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            return (
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Checkbox
                        id={collection.key}
                        name={collection.key}
                        className={classes.checkbox}
                        defaultValue={false}
                        required={required}
                        checked={value}
                        disabled={disabled}
                        error={validationError.current}
                        // ref={inputRef}
                        onChange={(e) => props.onCheckboxChange(e, dataxpath, xpath)}
                        // InputProps={inputProps}
                        autoFocus
                    />
                </TableCell >
            )
        } else if (type === DataTypes.ENUM) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            return (
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Select
                        id={collection.key}
                        name={collection.key}
                        className={classes.select}
                        value={value}
                        onChange={(e) => props.onSelectItemChange(e, dataxpath, xpath)}
                        size='small'
                        endAdornment={endAdornment}
                        error={validationError.current !== null}
                        required={required}
                        disabled={disabled}
                        open={active}
                        // onOpen={onFocusIn}
                        onClose={onFocusOut}
                        // ref={inputRef}
                        autoFocus
                    >
                        {enumValues.map((val) => {
                            return (
                                <MenuItem key={val} value={val}>
                                    {val}
                                </MenuItem>
                            )
                        })}
                    </Select>
                </TableCell >
            )
        } else if (type === DataTypes.NUMBER) {
            // round the decimal places for float. default precision is 2 digits for float
            let decimalScale = 2;
            if (collection.underlyingtype === DataTypes.INT32 || collection.underlyingtype === DataTypes.INT64) {
                decimalScale = 0;
            }
            if (collection.numberFormat && collection.numberFormat.includes(".")) {
                decimalScale = collection.numberFormat.split(".").pop();
                decimalScale = decimalScale * 1;
            }

            // min constrainsts for numeric field if set.
            let min = collection.min;
            if (typeof (min) === DataTypes.STRING) {
                min = getValueFromReduxStoreFromXpath(state, min);
            }

            // max constrainsts for numeric field if set.
            let max = collection.max;
            if (typeof (max) === DataTypes.STRING) {
                max = getValueFromReduxStoreFromXpath(state, max);
            }

            validationError.current = validateConstraints(collection, value, min, max);
            const endAdornment = validationError.current || collection.numberFormat ? (
                <>
                    {collection.numberFormat && collection.numberFormat === '%' && (
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
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <NumericFormat
                        className={classes.text_field}
                        customInput={TextField}
                        id={collection.key}
                        name={collection.key}
                        size='small'
                        required={required}
                        error={validationError.current !== null}
                        value={value}
                        disabled={disabled}
                        thousandSeparator=','
                        onValueChange={(values, sourceInfo) => props.onTextChange(sourceInfo.event, type, xpath, values.value, dataxpath,
                            validateConstraints(collection, values.value, min, max))}
                        variant='outlined'
                        decimalScale={decimalScale}
                        placeholder={collection.placeholder}
                        autoFocus
                        // ref={inputRef}
                        InputProps={inputProps}
                        // isAllowed={(values) => isAllowedNumericValue(values.value, min, max)}
                        inputProps={{
                            style: { padding: '6px 10px' },
                            dataxpath: dataxpath,
                            underlyingtype: collection.underlyingtype
                        }}
                    />
                </TableCell>
            )
        } else if (type === DataTypes.DATE_TIME) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            return (
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                        <DateTimePicker
                            id={collection.key}
                            name={collection.key}
                            className={classes.text_field}
                            disabled={disabled}
                            autoFocus
                            // ref={inputRef}
                            error={validationError.current !== null}
                            value={value}
                            required={required}
                            inputFormat="DD-MM-YYYY HH:mm:ss"
                            InputProps={inputProps}
                            onChange={(newValue) => props.onDateTimeChange(dataxpath, xpath, new Date(newValue).toISOString())}
                            inputProps={{
                                style: { padding: '6px 10px' },
                                dataxpath: dataxpath,
                                underlyingtype: collection.underlyingtype
                            }}
                            renderInput={(props) => <TextField {...props} />}
                        />
                    </LocalizationProvider>
                </TableCell>
            )
        } else if (type === DataTypes.STRING && !collection.abbreviated) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current}><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            return (
                <TableCell className={classes.cell_input_field} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <TextField
                        className={classes.text_field}
                        id={collection.key}
                        name={collection.key}
                        size='small'
                        autoFocus
                        required={required}
                        error={validationError.current !== null}
                        value={value}
                        disabled={disabled}
                        // ref={inputRef}
                        placeholder={collection.placeholder}
                        onChange={(e) => props.onTextChange(e, type, xpath, e.target.value, dataxpath,
                            validateConstraints(collection, e.target.value))}
                        variant='outlined'
                        InputProps={inputProps}
                        inputProps={{
                            style: { padding: '6px 10px' },
                            dataxpath: dataxpath,
                            underlyingtype: collection.underlyingtype
                        }}
                    />
                </TableCell>
            )
        }
    }

    if (type === DataTypes.BOOLEAN) {
        return (
            <TableCell className={classes.cell} align='center' size='small' onClick={onFocusIn}>
                <Checkbox
                    className={classes.checkbox}
                    disabled
                    defaultValue={false}
                    checked={value}
                />
            </TableCell >
        )
    }

    if (type === 'button') {
        if (value === undefined || value === null) {
            let tableCellRemove = dataRemove ? classes.remove : '';
            return (
                <TableCell className={`${classes.cell} ${classes.disabled} ${tableCellRemove}`} />
            )
        }

        let disabledCaptions = {};
        if (collection.button.disabled_captions) {
            collection.button.disabled_captions.split(',').forEach(valueCaptionPair => {
                let [buttonValue, caption] = valueCaptionPair.split('=');
                disabledCaptions[buttonValue] = caption;
            })
        }
        let isDisabledValue = _.keys(disabledCaptions).includes(String(value)) ? true : false;
        let disabledCaption = isDisabledValue ? disabledCaptions[String(value)] : '';
        let checked = String(value) === collection.button.pressed_value_as_text;
        let color = getColorTypeFromValue(collection, String(value));
        let size = getSizeFromValue(collection.button.button_size);
        let shape = getShapeFromValue(collection.button.button_type);
        let caption = String(value);

        if (isDisabledValue) {
            caption = disabledCaption;
        } else if (checked && collection.button.pressed_caption) {
            caption = collection.button.pressed_caption;
        } else if (!checked && collection.button.unpressed_caption) {
            caption = collection.button.unpressed_caption;
        }

        return (
            <TableCell className={`${classes.cell} ${classes.cell_no_padding}`} align='center' size='medium'>
                <ValueBasedToggleButton
                    size={size}
                    shape={shape}
                    color={color}
                    value={value}
                    caption={caption}
                    xpath={dataxpath}
                    disabled={dataRemove || disabled || buttonDisable || isDisabledValue ? true : false}
                    action={collection.button.action}
                    onClick={props.onButtonClick}
                />
            </TableCell>
        )
    }

    if (type === 'progressBar') {
        if (value === undefined || value === null) {
            let tableCellRemove = dataRemove ? classes.remove : '';
            return (
                <TableCell className={`${classes.cell} ${classes.disabled} ${tableCellRemove}`} />
            )
        }

        let maxFieldName = collection.maxFieldName;
        let valueFieldName = props.name;
        let min = collection.min;
        if (typeof (min) === DataTypes.STRING) {
            min = getValueFromReduxStoreFromXpath(state, min);
        }

        let max = collection.max;
        if (typeof (max) === DataTypes.STRING) {
            maxFieldName = max.substring(max.lastIndexOf(".") + 1);
            max = getValueFromReduxStoreFromXpath(state, max);
        }
        let hoverType = getHoverTextType(collection.progressBar.hover_text_type);

        return (
            <TableCell className={`${classes.cell} ${classes.cell_no_padding}`} align='center' size='medium'>
                <ValueBasedProgressBarWithHover
                    inlineTable={true}
                    collection={collection}
                    value={value}
                    min={min}
                    max={max}
                    valueFieldName={valueFieldName}
                    maxFieldName={maxFieldName}
                    hoverType={hoverType}
                />
            </TableCell>
        )
    }

    if (collection.abbreviated && collection.abbreviated === "JSON") {
        let tableCellRemove = dataRemove ? classes.remove : '';
        let updatedData = currentValue;
        if (type === DataTypes.OBJECT || type === DataTypes.ARRAY || (type === DataTypes.STRING && isValidJsonString(updatedData))) {
            if (type === DataTypes.OBJECT || type === DataTypes.ARRAY) {
                updatedData = updatedData ? clearxpath(cloneDeep(updatedData)) : {};
            } else {
                updatedData = updatedData.replace(/\\/g, '');
                updatedData = JSON.parse(updatedData);
            }

            return (
                <TableCell className={`${classes.cell} ${classes.abbreviated_json_cell} ${tableCellRemove}`} align='center' size='medium' onClick={onOpenTooltip}>
                    <AbbreviatedJson open={open} onClose={onCloseTooltip} src={updatedData} />
                </TableCell >
            )
        } else if (type === DataTypes.STRING && !isValidJsonString(updatedData)) {
            let tooltipText = "";
            if (updatedData !== null && updatedData !== undefined) {
                let lines = updatedData.split("\n");
                tooltipText = (
                    <>
                        {lines.map((line, idx) => (
                            <p key={idx}>{line}</p>
                        ))}
                    </>
                )
            }
            return (
                <TableCell className={`${classes.cell} ${classes.abbreviated_json_cell} ${tableCellRemove}`} align='center' size='medium' onClick={onOpenTooltip}>
                    <ClickAwayListener onClickAway={onCloseTooltip}>
                        <div className={classes.abbreviated_json_cell}>
                            <Tooltip
                                title={tooltipText}
                                open={open}
                                placement="bottom-start"
                                onClose={onCloseTooltip}
                                disableFocusListener
                                disableHoverListener
                                disableTouchListener>
                                <span>{updatedData}</span>
                            </Tooltip >
                        </div>
                    </ClickAwayListener>
                </TableCell>
            )
        }
    }

    let min = collection.min;
    if (typeof (min) === DataTypes.STRING) {
        min = getValueFromReduxStoreFromXpath(state, min);
    }

    let max = collection.max;
    if (typeof (max) === DataTypes.STRING) {
        max = getValueFromReduxStoreFromXpath(state, max);
    }
    validationError.current = validateConstraints(collection, value, min, max);

    if (value === null) {
        value = '';
    }
    let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
    value = v;
    if (typeof value === DataTypes.NUMBER) {
        value = value.toLocaleString();
    }
    let dataModified = previousValue !== currentValue;

    if (mode === Modes.EDIT_MODE && dataModified) {
        let originalValue = previousValue !== undefined && previousValue !== null ? previousValue : '';
        if (collection.displayType === DataTypes.INTEGER && typeof (originalValue) === DataTypes.NUMBER) {
            originalValue = floatToInt(originalValue);
        }
        originalValue = originalValue.toLocaleString();
        return (
            <TableCell className={`${classes.cell} ${tableCellColorClass} ${disabledClass}`} align={textAlign} size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                {originalValue ? <span className={classes.previous}>{originalValue}{numberSuffix}</span> : <span className={classes.previous}>{originalValue}</span>}
                {value ? <span className={classes.modified}>{value}{numberSuffix}</span> : <span className={classes.modified}>{value}</span>}
                {validationError.current && (
                    <Tooltip sx={{ marginLeft: '20px' }} title={validationError.current}><Error color='error' /></Tooltip>
                )}
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${classes.cell} ${disabledClass} ${tableCellColorClass} ${tableCellRemove} ${newUpdateClass}`} align={textAlign} size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                {value ? <span>{value}{numberSuffix}</span> : <span>{value}</span>}
                {validationError.current && (
                    <Tooltip title={validationError.current} sx={{ marginLeft: '20px' }}><Error color='error' /></Tooltip>
                )}
            </TableCell>
        )
    }
}

Cell.propTypes = {
    mode: PropTypes.oneOf([Modes.READ_MODE, Modes.EDIT_MODE]).isRequired,
    rowindex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    name: PropTypes.string.isRequired,
    elaborateTitle: PropTypes.string.isRequired,
    currentValue: PropTypes.any,
    previousValue: PropTypes.any,
    collection: PropTypes.object.isRequired,
    xpath: PropTypes.string,
    dataxpath: PropTypes.string,
    dataAdd: PropTypes.bool.isRequired,
    dataRemove: PropTypes.bool.isRequired,
    disabled: PropTypes.bool.isRequired,
    onUpdate: PropTypes.func.isRequired,
    onDoubleClick: PropTypes.func.isRequired,
    onButtonClick: PropTypes.func.isRequired,
    onCheckboxChange: PropTypes.func.isRequired,
    onTextChange: PropTypes.func.isRequired,
    onSelectItemChange: PropTypes.func.isRequired,
    onAutocompleteOptionChange: PropTypes.func.isRequired,
    onDateTimeChange: PropTypes.func.isRequired
}

export default memo(Cell, isEqual);