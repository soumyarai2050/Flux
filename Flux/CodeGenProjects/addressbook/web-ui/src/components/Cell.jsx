import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener } from '@mui/material';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import { clearxpath, getDataxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue, toCamelCase, capitalizeCamelCase, getValueFromReduxStore, normalise, getColorTypeFromPercentage } from '../utils';
import { ColorTypes, DataTypes, Modes } from '../constants';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { AbbreviatedJsonTooltip } from './AbbreviatedJsonWidget';
import { flux_toggle } from '../projectSpecificUtils';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBar } from './ValueBasedProgressBar';

const useStyles = makeStyles({
    previousValue: {
        color: 'red',
        textDecoration: 'line-through',
        marginRight: 10
    },
    modifiedValue: {
        color: 'green'
    },
    abbreviatedJsonCell: {
        maxWidth: 150,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        textDecoration: 'underline',
        color: 'blue !important',
        fontWeight: 'bold !important'
    },
    tableCellCritical: {
        color: '#9C0006 !important',
        background: '#ffc7ce',
        animation: `$blink 0.5s step-start infinite`
    },
    tableCellError: {
        color: '#9C0006 !important',
        background: '#ffc7ce'
    },
    tableCellWarning: {
        color: '#9c6500 !important',
        background: '#ffeb9c'
    },
    tableCellInfo: {
        color: 'blue !important',
        background: '#c2d1ff'
    },
    tableCellDebug: {
        color: 'black !important',
        background: '#ccc'
    },
    tableCellRemove: {
        textDecoration: 'line-through !important',
        background: '#ffc7ce !important'
    },
    tableCellDisabled: {
        background: '#ccc'
    },
    tableCellButton: {
        padding: '0px !important'
    },
    select: {
        background: 'white',
        '& .MuiSelect-outlined': {
            padding: '6px 10px'
        }
    },
    checkbox: {
        padding: '6px !important'
    },
    textField: {
        background: 'white',
        minWidth: '50px !important'
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

const Cell = (props) => {
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);
    const state = useSelector(state => state);
    const { data, originalData, row, propname, proptitle, mode, collections } = props;
    const classes = useStyles();

    const onFocusIn = () => {
        setActive(true);
    }

    const onFocusOut = () => {
        setActive(false);
    }

    const onOpenTooltip = () => {
        setOpen(true);
    }

    const onCloseTooltip = () => {
        setOpen(false);
    }

    const onTextChange = (e, type, xpath, value) => {
        if (type === DataTypes.NUMBER) {
            value = value * 1;
        }
        let dataxpath = e.target.getAttribute('dataxpath');
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onSelectItemChange = (e, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.value);
    }

    const onCheckboxChange = (e, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.checked);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.checked);
    }

    const onAutocompleteOptionChange = (e, value, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onButtonClick = (e, action, xpath, value) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData);
        }
    }

    let collection = collections.filter(col => col.tableTitle === proptitle)[0];
    let type = DataTypes.STRING;
    let enumValues = [];
    let xpath = proptitle ? proptitle.indexOf('.') > 0 ? row[proptitle.split('.')[0] + '.xpath_' + propname] : row['xpath_' + propname] : row['xpath_' + propname];
    let dataxpath = getDataxpath(data, xpath)
    let disabled = true;

    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
    }

    if (mode === Modes.EDIT_MODE) {
        if (collection && collection.ormNoUpdate && !row['data-add']) {
            disabled = true;
        } else if (collection.uiUpdateOnly && row['data-add']) {
            disabled = true;
        } else if (row['data-remove']) {
            disabled = true;
        } else if (type === DataTypes.STRING && row[proptitle] === undefined) {
            disabled = true;
        } else if (type === DataTypes.BOOLEAN && (row[proptitle] === undefined)) {
            disabled = true;
        } else if (type === DataTypes.NUMBER && row[proptitle] === undefined) {
            disabled = true;
        } else if (type === DataTypes.ENUM && !row[proptitle]) {
            disabled = true;
        } else {
            disabled = false;
        }
    } else {
        disabled = false;
    }

    if (active && mode === Modes.EDIT_MODE && !disabled) {
        if (collection.autocomplete) {
            return (
                <TableCell align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Autocomplete
                        options={collection.options}
                        getOptionLabel={(option) => option}
                        isOptionEqualToValue={(option, value) => option == value}
                        disableClearable
                        disabled={disabled}
                        variant='outlined'
                        size='small'
                        onBlur={onFocusOut}
                        sx={{ minWidth: 160 }}
                        clearOnBlur={false}
                        className={classes.textField}
                        value={collection.value}
                        onChange={(e, v) => onAutocompleteOptionChange(e, v, dataxpath, xpath)}
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
                <TableCell align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Select
                        className={classes.select}
                        size='small'
                        open={active}
                        disabled={disabled}
                        onOpen={onFocusIn}
                        onClose={onFocusOut}
                        value={row[proptitle]}
                        onChange={(e) => onSelectItemChange(e, dataxpath, xpath)}>

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
                <TableCell align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Checkbox
                        className={classes.checkbox}
                        defaultValue={false}
                        checked={row[proptitle]}
                        disabled={disabled}
                        onChange={(e) => onCheckboxChange(e, dataxpath, xpath)}
                    />
                </TableCell >
            )
        } else if (type === DataTypes.NUMBER) {
            let decimalScale = 2;
            if (props.data.underlyingtype === DataTypes.INT32 || props.data.underlyingtype === DataTypes.INT64) {
                decimalScale = 0;
            }
            let value = row[proptitle] ? row[proptitle] : 0;
            return (
                <TableCell align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <NumericFormat
                        className={classes.textField}
                        customInput={TextField}
                        autoFocus
                        size='small'
                        disabled={disabled}
                        onValueChange={(values, sourceInfo) => onTextChange(sourceInfo.event, type, xpath, values.value)}
                        // onChange={(e) => onTextChange(e, type, xpath)}
                        // onKeyDown={(e) => onKeyDown(e, type)}
                        inputProps={{ style: { padding: '6px 10px' }, dataxpath: dataxpath, underlyingtype: collection.underlyingtype }}
                        value={value}
                        // type={type}
                        placeholder={collection.placeholder}
                        thousandSeparator=','
                        decimalScale={decimalScale}
                    />
                </TableCell>
            )
        } else if (type === DataTypes.STRING && !collection.abbreviated) {
            let value = row[proptitle];
            return (
                <TableCell align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <TextField
                        className={classes.textField}
                        autoFocus
                        size='small'
                        disabled={disabled}
                        onChange={(e) => onTextChange(e, type, xpath, e.target.value)}
                        // onKeyDown={(e) => onKeyDown(e, type)}
                        inputProps={{ style: { padding: '6px 10px' }, dataxpath: dataxpath, underlyingtype: collection.underlyingtype }}
                        value={value}
                        // type={type}
                        placeholder={collection.placeholder}
                    />
                </TableCell>
            )
        }
    }

    if (type === DataTypes.BOOLEAN) {
        return (
            <TableCell align='center' size='small' onClick={onFocusIn}>
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
        if (value === undefined) return;

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
            <TableCell className={classes.tableCellButton} align='center' size='medium'>
                <ValueBasedToggleButton
                    size={size}
                    shape={shape}
                    color={color}
                    value={value}
                    caption={caption}
                    xpath={dataxpath}
                    action={collection.button.action}
                    onClick={onButtonClick}
                />
            </TableCell>
        )
    }

    if (type === 'progressBar') {
        let value = row[proptitle];
        if (value === undefined) return;

        let min = collection.min;
        if (typeof (min) === DataTypes.STRING) {
            let sliceName = toCamelCase(min.split('.')[0]);
            let propertyName = 'modified' + capitalizeCamelCase(min.split('.')[0]);
            let minxpath = min.substring(min.indexOf('.') + 1);
            min = getValueFromReduxStore(state, sliceName, propertyName, minxpath);
        }
        let max = collection.max;
        if (typeof (max) === DataTypes.STRING) {
            let sliceName = toCamelCase(max.split('.')[0]);
            let propertyName = 'modified' + capitalizeCamelCase(max.split('.')[0]);
            let maxxpath = max.substring(max.indexOf('.') + 1);
            max = 10;
            max = getValueFromReduxStore(state, sliceName, propertyName, maxxpath);
        }

        let percentage = normalise(value, max, min);
        let color = getColorTypeFromPercentage(collection, percentage);

        return (
            <TableCell align='center' size='medium'>
                <ValueBasedProgressBar percentage={percentage} value={value} color={color} min={min} max={max} />
            </TableCell>
        )

    }

    if (collection.abbreviated && collection.abbreviated === "JSON") {
        let updatedData = row[proptitle];
        if (type === DataTypes.OBJECT || type === DataTypes.ARRAY || (type === DataTypes.STRING && isValidJsonString(updatedData))) {
            if (type === DataTypes.OBJECT || type === DataTypes.ARRAY) {
                updatedData = updatedData ? clearxpath(cloneDeep(updatedData)) : {};
            } else {
                updatedData = updatedData.replace(/\\/g, '');
                updatedData = JSON.parse(updatedData);
            }

            return (
                <TableCell className={classes.abbreviatedJsonCell} align='center' size='medium' onClick={onOpenTooltip}>
                    <AbbreviatedJsonTooltip open={open} onClose={onCloseTooltip} src={updatedData} />
                </TableCell >
            )
        } else if (type === DataTypes.STRING && !isValidJsonString(updatedData)) {
            return (
                <TableCell className={classes.abbreviatedJsonCell} align='center' size='medium' onClick={onOpenTooltip}>
                    <ClickAwayListener onClickAway={onCloseTooltip}>
                        <div className={classes.abbreviatedJsonCell}>
                            <Tooltip
                                title={updatedData}
                                open={open}
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

    let color = ColorTypes.UNSPECIFIED;
    if (collection) {
        if (collection.color) {
            collection.color.split(',').map((colorSet) => {
                colorSet = colorSet.trim();
                let [key, value] = colorSet.split('=');
                if (key === row[proptitle]) {
                    color = ColorTypes[value];
                }
            });
        }
    }

    let tableCellColorClass = '';
    if (color === ColorTypes.CRITICAL) tableCellColorClass = classes.tableCellCritical;
    else if (color === ColorTypes.ERROR) tableCellColorClass = classes.tableCellError;
    else if (color === ColorTypes.WARNING) tableCellColorClass = classes.tableCellWarning;
    else if (color === ColorTypes.INFO) tableCellColorClass = classes.tableCellInfo;
    else if (color === ColorTypes.DEBUG) tableCellColorClass = classes.tableCellDebug;

    let dataModified = _.get(originalData, xpath) !== row[proptitle];
    let tableCellRemove = row['data-remove'] ? classes.tableCellRemove : '';
    let disabledClass = disabled ? classes.tableCellDisabled : '';

    let currentValue = row[proptitle] !== undefined ? row[proptitle].toLocaleString() : '';
    if (dataModified) {
        let originalValue = _.get(originalData, xpath) !== undefined ? _.get(originalData, xpath).toLocaleString() : '';
        return (
            <TableCell className={`${tableCellColorClass} ${disabledClass}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span className={classes.previousValue}>{originalValue}</span>
                <span className={classes.modifiedValue}>{currentValue}</span>
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${disabledClass} ${tableCellColorClass} ${tableCellRemove}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
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

export default Cell;