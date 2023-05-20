import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, isEqual, debounce } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener, InputAdornment } from '@mui/material';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import {
    clearxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue,
    getHoverTextType, getValueFromReduxStoreFromXpath, isAllowedNumericValue, floatToInt
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
    } = props;

    const state = useSelector(state => state);
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);
    const [oldValue, setOldValue] = useState(null);
    const [newUpdateClass, setNewUpdateClass] = useState("");
    const [inputValue, setInputValue] = useState(currentValue);
    const timeoutRef = useRef(null);

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

    const handleTextChangeDebounced = debounce((e, type, xpath, value) => {
        props.onTextChange(e, type, xpath, value);
    }, 500)

    const handleTextChange = (e, type, xpath, value) => {
        if (value === '') {
            value = null;
        }
        if (type === DataTypes.NUMBER) {
            if (value !== null) {
                value = value * 1;
            }
        }
        setInputValue(value);
        handleTextChangeDebounced(e, type, xpath, value);
    }

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

    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
    }

    if (mode === Modes.EDIT_MODE && active && !disabled) {
        if (collection.autocomplete) {
            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Autocomplete
                        sx={{ minWidth: 160 }}
                        className={classes.text_field}
                        variant='outlined'
                        size='small'
                        options={collection.options}
                        disableClearable
                        disabled={disabled}
                        clearOnBlur={false}
                        value={collection.value}
                        getOptionLabel={(option) => option}
                        isOptionEqualToValue={(option, value) => option == value}
                        onBlur={onFocusOut}
                        onChange={(e, v) => props.onAutocompleteOptionChange(e, v, dataxpath, xpath)}
                        renderInput={(params) => (
                            <TextField
                                {...params}
                                autoFocus
                                placeholder={collection.placeholder}
                            />
                        )}
                    />
                </TableCell>
            )
        } else if (type === DataTypes.ENUM) {
            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Select
                        className={classes.select}
                        size='small'
                        open={active}
                        disabled={disabled}
                        value={currentValue}
                        onOpen={onFocusIn}
                        onClose={onFocusOut}
                        onChange={(e) => props.onSelectItemChange(e, dataxpath, xpath)}>
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
        } else if (type === DataTypes.BOOLEAN) {
            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Checkbox
                        className={classes.checkbox}
                        defaultValue={false}
                        checked={currentValue}
                        disabled={disabled}
                        onChange={(e) => props.onCheckboxChange(e, dataxpath, xpath)}
                    />
                </TableCell >
            )
        } else if (type === DataTypes.NUMBER) {
            let decimalScale = 2;
            if (collection.underlyingtype === DataTypes.INT32 || collection.underlyingtype === DataTypes.INT64) {
                decimalScale = 0;
            }
            let value = inputValue ? inputValue : inputValue === 0 ? 0 : '';

            let min = collection.min;
            if (typeof (min) === DataTypes.STRING) {
                min = getValueFromReduxStoreFromXpath(state, min);
            }

            let max = collection.max;
            if (typeof (max) === DataTypes.STRING) {
                max = getValueFromReduxStoreFromXpath(state, max);
            }

            let inputProps = {};
            if (collection.numberFormat) {
                if (collection.numberFormat === "%") {
                    inputProps = {
                        endAdornment: <InputAdornment position="end">%</InputAdornment>
                    }
                }
            }

            if (collection.displayType === DataTypes.INTEGER) {
                value = floatToInt(value);
            }

            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <NumericFormat
                        className={classes.text_field}
                        size='small'
                        value={value}
                        placeholder={collection.placeholder}
                        thousandSeparator=','
                        decimalScale={decimalScale}
                        autoFocus
                        disabled={disabled}
                        InputProps={inputProps}
                        customInput={TextField}
                        isAllowed={(values) => isAllowedNumericValue(values.value, min, max)}
                        onValueChange={(values, sourceInfo) => handleTextChange(sourceInfo.event, type, xpath, values.value)}
                        inputProps={{
                            style: { padding: '6px 10px' },
                            dataxpath: dataxpath,
                            underlyingtype: collection.underlyingtype
                        }}
                    />
                </TableCell>
            )
        } else if (type === DataTypes.DATE_TIME) {
            let value = currentValue ? new Date(currentValue) : null;
            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                        <DateTimePicker
                            className={classes.text_field}
                            disabled={disabled}
                            value={value}
                            inputFormat="DD-MM-YYYY HH:mm:ss"
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
            let value = inputValue ? inputValue : '';
            return (
                <TableCell className={classes.cell} align='center' size='small' onKeyDown={onKeyDown} onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <TextField
                        className={classes.text_field}
                        size='small'
                        autoFocus
                        value={value}
                        placeholder={collection.placeholder}
                        disabled={disabled}
                        onChange={(e) => handleTextChange(e, type, xpath, e.target.value)}
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
                    checked={currentValue}
                />
            </TableCell >
        )
    }

    if (type === 'button') {
        let value = currentValue;
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
                    disabled={dataRemove || disabled || isDisabledValue ? true : false}
                    action={collection.button.action}
                    onClick={props.onButtonClick}
                />
            </TableCell>
        )
    }

    if (type === 'progressBar') {
        let value = currentValue;
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

    let color = getColorTypeFromValue(collection, currentValue);
    let tableCellColorClass = classes[color];

    let dataModified = previousValue !== currentValue;
    let tableCellRemove = dataRemove ? classes.remove : '';
    let disabledClass = disabled ? classes.disabled : '';
    if (props.ignoreDisable) {
        disabledClass = "";
    }


    let value = currentValue !== undefined && currentValue !== null ? currentValue : '';
    if (collection.displayType === DataTypes.INTEGER && typeof (value) === DataTypes.NUMBER) {
        value = floatToInt(value);
    }
    value = value.toLocaleString();
    let numberSuffix = ""
    if (collection.numberFormat) {
        if (collection.numberFormat === "%") {
            numberSuffix = " %"
        }
    }

    let textAlign = collection.textAlign ? collection.textAlign : 'center';

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
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${classes.cell} ${disabledClass} ${tableCellColorClass} ${tableCellRemove} ${newUpdateClass}`} align={textAlign} size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                {value ? <span>{value}{numberSuffix}</span> : <span>{value}</span>}
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