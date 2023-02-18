import React, { useState, useCallback, memo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, isEqual } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import {
    clearxpath, getDataxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue,
    getHoverTextType, getValueFromReduxStoreFromXpath, isAllowedNumericValue
} from '../utils';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener } from '@mui/material';
import { ColorTypes, DataTypes, Modes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import classes from './Cell.module.css';

const Cell = (props) => {
    const state = useSelector(state => state);
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);

    const { data, originalData, row, propname, proptitle, mode, collections } = props;

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

    let collection = collections.filter(col => col.tableTitle === proptitle)[0];
    let type = DataTypes.STRING;
    let enumValues = [];
    let xpath = row['xpath_' + propname];
    if (proptitle && proptitle.indexOf('.') > -1) {
        xpath = row[proptitle.substring(0, proptitle.lastIndexOf('.')) + '.xpath_' + propname]
    }
    let dataxpath = getDataxpath(data, xpath);
    let disabled = false;

    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
    }

    if (row[proptitle] === undefined) {
        disabled = true;
    } else if (mode === Modes.EDIT_MODE) {
        if (collection && collection.ormNoUpdate && !row['data-add']) {
            disabled = true;
        } else if (collection.uiUpdateOnly && row['data-add']) {
            disabled = true;
        } else if (row['data-remove']) {
            disabled = true;
        }
    }

    if (mode === Modes.EDIT_MODE && active && !disabled) {
        if (collection.autocomplete) {
            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
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
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Select
                        className={classes.select}
                        size='small'
                        open={active}
                        disabled={disabled}
                        value={row[proptitle]}
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
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Checkbox
                        className={classes.checkbox}
                        defaultValue={false}
                        checked={row[proptitle]}
                        disabled={disabled}
                        onChange={(e) => props.onCheckboxChange(e, dataxpath, xpath)}
                    />
                </TableCell >
            )
        } else if (type === DataTypes.NUMBER) {
            let decimalScale = 2;
            if (props.data.underlyingtype === DataTypes.INT32 || props.data.underlyingtype === DataTypes.INT64) {
                decimalScale = 0;
            }
            let value = row[proptitle] ? row[proptitle] : 0;

            let min = collection.min;
            if (typeof (min) === DataTypes.STRING) {
                min = getValueFromReduxStoreFromXpath(state, min);
            }

            let max = collection.max;
            if (typeof (max) === DataTypes.STRING) {
                max = getValueFromReduxStoreFromXpath(state, max);
            }

            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
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
            let value = row[proptitle] ? new Date(row[proptitle]) : null;
            return (
                <TableCell className={classes.cell} align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                        <DateTimePicker
                            className={classes.text_field}
                            disabled={disabled}
                            value={value}
                            inputFormat="DD-MM-YYYY HH:mm:ss"
                            onChange={(newValue) => props.onDateTimeChange(props.data.dataxpath, props.data.xpath, new Date(newValue).toISOString())}
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
            let value = row[proptitle] ? row[proptitle] : '';
            return (
                <TableCell className={classes.cell} align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
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
                    checked={row[proptitle]}
                />
            </TableCell >
        )
    }

    if (type === 'button') {
        let value = row[proptitle];
        if (value === undefined || value === null) {
            let tableCellRemove = row['data-remove'] ? classes.remove : '';
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
                    disabled={row['data-remove'] ? true : false}
                    action={collection.button.action}
                    onClick={props.onButtonClick}
                />
            </TableCell>
        )
    }

    if (type === 'progressBar') {
        let value = row[proptitle];
        if (value === undefined || value === null) {
            let tableCellRemove = row['data-remove'] ? classes.remove : '';
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
        let tableCellRemove = row['data-remove'] ? classes.remove : '';
        let updatedData = row[proptitle];
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

    let color = getColorTypeFromValue(collection, row[proptitle]);
    let tableCellColorClass = classes[color];

    let dataModified = _.get(originalData, xpath) !== row[proptitle];
    let tableCellRemove = row['data-remove'] ? classes.remove : '';
    let disabledClass = disabled ? classes.disabled : '';

    let currentValue = row[proptitle] !== undefined && row[proptitle] !== null ? row[proptitle].toLocaleString() : '';
    if (dataModified) {
        let originalValue = _.get(originalData, xpath) !== undefined && _.get(originalData, xpath) !== null ? _.get(originalData, xpath).toLocaleString() : '';
        return (
            <TableCell className={`${classes.cell} ${tableCellColorClass} ${disabledClass}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span className={classes.previous}>{originalValue}</span>
                <span className={classes.modified}>{currentValue}</span>
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${classes.cell} ${disabledClass} ${tableCellColorClass} ${tableCellRemove}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span>{currentValue}</span>
            </TableCell>
        )
    }
}

Cell.propTypes = {
    data: PropTypes.object.isRequired,
    originalData: PropTypes.object.isRequired,
    row: PropTypes.object.isRequired,
    propname: PropTypes.string.isRequired,
    proptitle: PropTypes.string,
    mode: PropTypes.string.isRequired,
    collections: PropTypes.array.isRequired
}

export default memo(Cell, isEqual);