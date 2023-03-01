import React, { useState, useCallback, memo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, isEqual } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener } from '@mui/material';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import {
    clearxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue,
    getHoverTextType, getValueFromReduxStoreFromXpath, isAllowedNumericValue
} from '../utils';
import { DataTypes, Modes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';
import classes from './Cell.module.css';

const Cell = (props) => {
    const state = useSelector(state => state);
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);

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
        compare
    } = props;

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

    let type = DataTypes.STRING;
    let enumValues = [];

    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
    }

    if (mode === Modes.EDIT_MODE && active && !disabled) {
        if (collection.autocomplete) {
            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
            let value = currentValue ? currentValue : 0;

            let min = collection.min;
            if (typeof (min) === DataTypes.STRING) {
                min = getValueFromReduxStoreFromXpath(state, min);
            }

            let max = collection.max;
            if (typeof (max) === DataTypes.STRING) {
                max = getValueFromReduxStoreFromXpath(state, max);
            }

            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <NumericFormat
                        className={classes.text_field}
                        size='small'
                        value={value}
                        placeholder={collection.placeholder}
                        thousandSeparator=','
                        decimalScale={decimalScale}
                        autoFocus
                        disabled={disabled}
                        customInput={TextField}
                        isAllowed={(values) => isAllowedNumericValue(values.value, min, max)}
                        onValueChange={(values, sourceInfo) => props.onTextChange(sourceInfo.event, type, xpath, values.value)}
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
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
            let value = currentValue ? currentValue : '';
            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <TextField
                        className={classes.text_field}
                        size='small'
                        autoFocus
                        value={value}
                        placeholder={collection.placeholder}
                        disabled={disabled}
                        onChange={(e) => props.onTextChange(e, type, xpath, e.target.value)}
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

        let checked = String(value) === collection.button.pressed_value_as_text;
        let color = getColorTypeFromValue(collection, String(value));
        let size = getSizeFromValue(collection.button.button_size);
        let shape = getShapeFromValue(collection.button.button_type);
        let caption = String(value);

        if (checked && collection.button.pressed_caption) {
            caption = collection.button.pressed_caption;
        } else if (!checked && collection.button.unpressed_caption) {
            caption = collection.button.unpressed_caption;
        }

        return (
            <TableCell className={`${classes.cell} ${classes.button}`} align='center' size='medium'>
                <ValueBasedToggleButton
                    size={size}
                    shape={shape}
                    color={color}
                    value={value}
                    caption={caption}
                    xpath={dataxpath}
                    disabled={dataRemove ? true : false}
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

        let min = collection.min;
        if (typeof (min) === DataTypes.STRING) {
            min = getValueFromReduxStoreFromXpath(state, min);
        }

        let max = collection.max;
        if (typeof (max) === DataTypes.STRING) {
            max = getValueFromReduxStoreFromXpath(state, max);
        }
        let hoverType = getHoverTextType(collection.progressBar.hover_text_type);

        return (
            <TableCell className={classes.cell} align='center' size='medium'>
                <ValueBasedProgressBarWithHover
                    collection={collection}
                    value={value}
                    min={min}
                    max={max}
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
            return (
                <TableCell className={`${classes.cell} ${classes.abbreviated_json_cell} ${tableCellRemove}`} align='center' size='medium' onClick={onOpenTooltip}>
                    <ClickAwayListener onClickAway={onCloseTooltip}>
                        <div className={classes.abbreviated_json_cell}>
                            <Tooltip
                                title={updatedData}
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

    let value = currentValue !== undefined && currentValue !== null ? currentValue.toLocaleString() : '';
    if (compare && dataModified) {
        let originalValue = previousValue !== undefined && previousValue !== null ? previousValue.toLocaleString() : '';
        return (
            <TableCell className={`${classes.cell} ${tableCellColorClass} ${disabledClass}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span className={classes.previous}>{originalValue}</span>
                <span className={classes.modified}>{value}</span>
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${classes.cell} ${disabledClass} ${tableCellColorClass} ${tableCellRemove}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span>{value}</span>
            </TableCell>
        )
    }
}

Cell.propTypes = {
    mode: PropTypes.oneOf([Modes.READ_MODE, Modes.EDIT_MODE]).isRequired,
    rowindex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    name: PropTypes.string.isRequired,
    elaborateTitle: PropTypes.string.isRequired,
    currentValue: PropTypes.any,
    previousValue: PropTypes.any,
    collection: PropTypes.object.isRequired,
    compare: PropTypes.bool.isRequired,
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

Cell.defaultProps = {
    compare: true
}

export default memo(Cell, isEqual);