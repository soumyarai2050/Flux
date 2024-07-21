import React, { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, isEqual } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener, InputAdornment, IconButton } from '@mui/material';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { ContentCopy, Error } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import {
    clearxpath, isValidJsonString, getSizeFromValue, getShapeFromValue, getColorTypeFromValue,
    getHoverTextType, getValueFromReduxStoreFromXpath, floatToInt,
    validateConstraints, getLocalizedValueAndSuffix, excludeNullFromObject, formatJSONObjectOrArray, toCamelCase, capitalizeCamelCase, getReducerArrrayFromCollections,
    getDataSourceColor
} from '../utils';
import { ColorTypes, DataTypes, Modes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';
import classes from './Cell.module.css';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import CopyToClipboard from './CopyToClipboard';
import AlertBubble from './AlertBubble';
dayjs.extend(utc);
dayjs.extend(timezone);

const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

const Cell = (props) => {
    const {
        mode,
        rowindex,
        xpath,
        dataxpath,
        disabled,
        dataRemove,
        dataAdd,
        currentValue,
        previousValue,
        buttonDisable,
        dataSourceId,
        selected
    } = props;

    const theme = useTheme();
    const collection = cloneDeep(props.collection);
    // const state = useSelector(state => state);
    const reducerArray = useMemo(() => getReducerArrrayFromCollections([props.collection]), [props.collection]);
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
    const { schema } = useSelector(state => state.schema);
    const [active, setActive] = useState(false);
    const [open, setOpen] = useState(false);
    const [oldValue, setOldValue] = useState(null);
    const [newUpdateClass, setNewUpdateClass] = useState('');
    const [clipboardText, setClipboardText] = useState(null);
    const timeoutRef = useRef(null);
    const validationError = useRef(null);
    const [inputValue, setInputValue] = useState(currentValue);
    const inputRef = useRef(null);
    const cursorPos = useRef(null);

    useEffect(() => {
        setInputValue(currentValue);
    }, [props.index, mode])

    useEffect(() => {
        if (props.forceUpdate) {
            setInputValue(currentValue);
        }
    }, [props.forceUpdate])

    useEffect(() => {
        if (mode === Modes.READ_MODE) {
            setInputValue(currentValue);
        }
    }, [currentValue])

    useEffect(() => {
        if (inputRef.current && active && cursorPos.current !== null) {
            if (inputRef.current.selectionStart !== cursorPos.current) {
                inputRef.current.setSelectionRange(cursorPos.current, cursorPos.current);
            }
        }
    }, [inputValue])

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

    const onRowSelect = (e) => {
        if (props.widgetType === 'root') {
            props.onRowSelect(e, rowindex);
        } else {
            props.onRowSelect(e, dataSourceId);
        }
    }

    const handleTextChange = (e, type, xpath, value, dataxpath, validationRes) => {
        cursorPos.current = e.target.selectionStart;
        setInputValue(value);
        props.onTextChange(e, type, xpath, value, dataxpath, validationRes);
    }

    const onFocusIn = (e) => {
        if (mode === Modes.EDIT_MODE) {
            setActive(true);
        }
        onRowSelect(e);
    }

    const onFocusOut = useCallback(() => {
        setActive(false);
    }, [])

    const onOpenTooltip = (e) => {
        setOpen(true);
        onRowSelect(e);
    }

    const onCloseTooltip = useCallback(() => {
        setOpen(false);
    }, [])

    const handleDiffThreshold = (storedValue, updatedValue) => {
        if (collection.diffThreshold) {
            if (typeof storedValue === DataTypes.NUMBER && typeof updatedValue === DataTypes.NUMBER) {
                const diffPercentage = Math.abs(updatedValue - storedValue) * 100 / storedValue;
                if (diffPercentage < collection.diffThreshold) {
                    if (props.onForceSave) {
                        props.onForceSave();
                    }
                }
            }
        }
    }

    const onKeyDown = useCallback((e) => {
        if (e.keyCode === 13) {
            onFocusOut();
            handleDiffThreshold(previousValue, currentValue);
        }
    }, [previousValue, currentValue])

    const copyHandler = (text) => {
        setClipboardText(text);
    }

    const dataSourceColor = getDataSourceColor(theme, collection.sourceIndex, collection.joinKey, collection.commonGroupKey, props.dataSourceColors?.[collection.sourceIndex]);

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
            value = (value || value === 0) ? value : '';
            if (collection.displayType === DataTypes.INTEGER) {
                if (value !== '') {
                    value = floatToInt(value);
                }
            }
        } else if (type === DataTypes.DATE_TIME) {
            if (props.truncateDateTime) {
                value = value ? dayjs.utc(value).format('YYYY-MM-DD HH:mm') : null;
            } else {
                value = value ? value : null;
            }
        } else if (type === DataTypes.STRING) {
            // if (mode === Modes.EDIT_MODE) {
            //     value = inputValue ? inputValue : inputValue;
            // }
        } else if (collection.abbreviated === 'JSON') {
            if (typeof value === DataTypes.OBJECT) {
                value = JSON.stringify(value);
            }
        }
    }
    let color = getColorTypeFromValue(collection, currentValue);
    let tableCellColorClass = classes[color];
    let tableCellRemove = dataRemove ? classes.remove : dataAdd ? classes.add : '';
    let disabledClass = disabled ? classes.disabled : '';
    if (props.ignoreDisable) {
        disabledClass = "";
    }
    let textAlign = collection.textAlign ? collection.textAlign : 'center';
    let selectedClass = '';
    if (selected && !(collection.joinKey || collection.commonGroupKey)) {
        selectedClass = classes.cell_selected;
    }

    if (props.nullCell) {
        const classesStr = `${classes.cell} ${disabledClass}`;
        return (
            <TableCell className={classesStr} size='small' />
        )
    }

    if (disabled) {
        if (value === null) {
            value = '';
        }
        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
        value = v;
        if (typeof value === DataTypes.NUMBER) {
            value = value.toLocaleString();
        }
        const classesStr = `${classes.cell} ${selectedClass} ${disabledClass} ${tableCellColorClass} ${tableCellRemove} ${newUpdateClass}`;
        return (
            <TableCell
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}}
                align={textAlign}
                size='small'
                data-xpath={xpath}
                onClick={(e) => onRowSelect(e)}
                data-dataxpath={dataxpath}>
                {value}{numberSuffix}
            </TableCell>
        )
    }
    const placeholder = collection.placeholder ? collection.placeholder : !required ? 'optional' : null;

    if (mode === Modes.EDIT_MODE && active && !disabled && !(['repeatedRoot', 'abbreviatedFilter'].includes(props.widgetType) && !props.selected) && !collection.ormNoUpdate && !collection.serverPopulate) {
        if (collection.autocomplete) {
            validationError.current = validateConstraints(collection, value);

            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};

            if (collection.dynamic_autocomplete) {
                const widgetName = toCamelCase(collection.autocomplete.split('.')[0]);
                const dynamicValuePath = collection.autocomplete.substring(collection.autocomplete.indexOf('.') + 1);
                const dynamicValue = getValueFromReduxStoreFromXpath(reducerDict, dynamicValuePath);
                if (schema.autocomplete.hasOwnProperty(dynamicValue)) {
                    collection.options = schema.autocomplete[schema.autocomplete[dynamicValue]];
                    if (!collection.options.includes(collection.value) && !collection.ormNoUpdate && !collection.serverPopulate) {
                        collection.value = null;
                    }
                }
            }

            const classesStr = `${classes.cell_input_field} ${selectedClass}`;

            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onBlur={onFocusOut}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Autocomplete
                        id={collection.key}
                        options={collection.options}
                        getOptionLabel={(option) => option}
                        isOptionEqualToValue={(option, value) => option === value}
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
                        onChange={(e, v) => props.onAutocompleteOptionChange(e, v, dataxpath, xpath, dataSourceId, collection.source)}
                        renderInput={(params) => (
                            <TextField
                                {...params}
                                name={collection.key}
                                error={validationError.current !== null}
                                placeholder={placeholder}
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
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Checkbox
                        id={collection.key}
                        name={collection.key}
                        className={classes.checkbox}
                        defaultValue={false}
                        required={required}
                        checked={value}
                        disabled={disabled}
                        error={validationError.current}
                        onChange={(e) => props.onCheckboxChange(e, dataxpath, xpath, dataSourceId, collection.source)}
                        autoFocus
                    />
                </TableCell >
            )
        } else if (type === DataTypes.ENUM) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Select
                        id={collection.key}
                        name={collection.key}
                        className={classes.select}
                        value={value}
                        onChange={(e) => props.onSelectItemChange(e, dataxpath, xpath, dataSourceId, collection.source)}
                        size='small'
                        endAdornment={endAdornment}
                        error={validationError.current !== null}
                        required={required}
                        disabled={disabled}
                        open={active}
                        // onOpen={onFocusIn}
                        onClose={onFocusOut}
                        // ref={inputRef}
                        autoFocus>
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
                min = getValueFromReduxStoreFromXpath(reducerDict, min);
            }

            // max constrainsts for numeric field if set.
            let max = collection.max;
            if (typeof (max) === DataTypes.STRING) {
                max = getValueFromReduxStoreFromXpath(reducerDict, max);
            }

            validationError.current = validateConstraints(collection, value, min, max);
            const endAdornment = validationError.current || collection.numberFormat ? (
                <>
                    {collection.numberFormat && collection.numberFormat === '%' && (
                        <InputAdornment position='end'>%</InputAdornment>
                    )}
                    {collection.numberFormat && collection.numberFormat === 'bps' && (
                        <InputAdornment position='end'>bps</InputAdornment>
                    )}
                    {validationError.current && (
                        <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
                    )}
                </>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;

            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onBlur={onFocusOut}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
                            validateConstraints(collection, values.value, min, max), dataSourceId, collection.source)}
                        variant='outlined'
                        decimalScale={decimalScale}
                        placeholder={placeholder}
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
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
                            inputFormat="YYYY-MM-DD HH:mm:ss"
                            InputProps={inputProps}
                            onChange={(newValue) => props.onDateTimeChange(dataxpath, xpath, new Date(newValue).toISOString(), dataSourceId, collection.source)}
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
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onBlur={onFocusOut}
                    onClick={(e) => onRowSelect(e)}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
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
                        placeholder={placeholder}
                        onChange={(e) => handleTextChange(e, type, xpath, e.target.value, dataxpath,
                            validateConstraints(collection, e.target.value), dataSourceId, collection.source)}
                        variant='outlined'
                        InputProps={inputProps}
                        inputProps={{
                            ref: inputRef,
                            style: { padding: '6px 10px' },
                            dataxpath: dataxpath,
                            underlyingtype: collection.underlyingtype
                        }}
                    />
                </TableCell>
            )
        }
    }

    // components in read-only mode
    const classesArray = [classes.cell];
    if (selected) {
        classesArray.push(selectedClass);
    }

    // add column size class if column size is set
    if (collection.columnSize && classes[`column_size_${collection.columnSize}`]) {
        classesArray.push(classes['column_size_' + collection.columnSize]);
    }
    // add column direction (text direction) class if column direction is set
    if (collection.columnDirection && classes[`column_direction_${collection.columnDirection}`]) {
        classesArray.push(classes[`column_direction_${collection.columnDirection}`])
    }

    if (type === 'alert_bubble') {
        const classesStr = classesArray.join(' ');
        const bubbleCount = value ? value[0] : 0;
        const bubbleColor = value ? value[1] : ColorTypes.DEFAULT;
        return (
            <TableCell
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}}
                // sx={{ width: 20 }}
                align='center'
                size='small'
                onClick={(e) => onRowSelect(e)}>
                {bubbleCount > 0 && <AlertBubble content={bubbleCount} color={bubbleColor} />}
            </TableCell >
        )
    }

    // read-only checkbox component
    if (type === DataTypes.BOOLEAN) {
        const classesStr = classesArray.join(' ');
        return (
            <TableCell
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}}
                align='center'
                size='small'
                onClick={onFocusIn}>
                <Checkbox
                    className={classes.checkbox}
                    disabled
                    defaultValue={false}
                    checked={value}
                />
            </TableCell >
        )
    }

    // button components support click in both read and edit mode
    if (type === 'button') {
        // do not display button if value not set
        if (value === undefined || value === null) {
            classesArray.push(classes.disabled);
            if (dataRemove) {
                classesArray.push(classes.remove);
            }
            const classesStr = classesArray.join(' ');
            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    align='center'
                    size='small'
                    onClick={(e) => onRowSelect(e)}
                />
            )
        }

        const disabledValueCaptionDict = {};
        if (collection.button.disabled_captions) {
            collection.button.disabled_captions.split(',').forEach(valueCaptionPair => {
                const [buttonValue, caption] = valueCaptionPair.split('=');
                disabledValueCaptionDict[buttonValue] = caption;
            })
        }
        const isDisabledValue = disabledValueCaptionDict.hasOwnProperty(String(value));
        const disabledCaption = isDisabledValue ? disabledValueCaptionDict[String(value)] : '';
        const checked = String(value) === collection.button.pressed_value_as_text;
        const color = getColorTypeFromValue(collection, String(value));
        const size = getSizeFromValue(collection.button.button_size);
        const shape = getShapeFromValue(collection.button.button_type);
        let caption = String(value);

        if (isDisabledValue) {
            caption = disabledCaption;
        } else if (checked && collection.button.pressed_caption) {
            caption = collection.button.pressed_caption;
        } else if (!checked && collection.button.unpressed_caption) {
            caption = collection.button.unpressed_caption;
        }

        classesArray.push(classes.cell_no_padding);
        const classesStr = classesArray.join(' ');

        return (
            <TableCell
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}}
                align='center'
                size='small'
                onClick={(e) => onRowSelect(e)}>
                <ValueBasedToggleButton
                    size={size}
                    shape={shape}
                    color={color}
                    value={value}
                    caption={caption}
                    xpath={dataxpath}
                    disabled={!!(dataRemove || disabled || buttonDisable || isDisabledValue)}
                    action={collection.button.action}
                    allowForceUpdate={collection.button.allow_force_update}
                    dataSourceId={dataSourceId}
                    source={collection.source}
                    onClick={props.onButtonClick}
                    iconName={collection.button.button_icon_name}
                />
            </TableCell>
        )
    }

    if (type === 'progressBar') {
        if (value === undefined || value === null) {
            classesArray.push(classes.disabled);
            if (dataRemove) {
                classesArray.push(classes.remove);
            }
            const classesStr = classesArray.join(' ');

            return (
                <TableCell
                    className={classesStr}
                    sx={{backgroundColor: dataSourceColor}}
                    size='small'
                    onClick={(e) => onRowSelect(e)}
                />
            )
        }

        const valueFieldName = props.name;
        let maxFieldName = collection.maxFieldName;
        let min = collection.min;
        if (typeof (min) === DataTypes.STRING) {
            min = getValueFromReduxStoreFromXpath(reducerDict, min);
        }
        let max = collection.max;
        if (typeof (max) === DataTypes.STRING) {
            maxFieldName = max.substring(max.lastIndexOf(".") + 1);
            max = getValueFromReduxStoreFromXpath(reducerDict, max);
        }
        const hoverType = getHoverTextType(collection.progressBar.hover_text_type);
        classesArray.push(classes.cell_no_padding);
        const classesStr = classesArray.join(' ');

        return (
            <TableCell
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}}
                align='center'
                size='small'
                onClick={(e) => onRowSelect(e)}>
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
        if (dataRemove) {
            classesArray.push(classes.remove);
        }
        let updatedData = currentValue;
        if (type === DataTypes.OBJECT || type === DataTypes.ARRAY || (type === DataTypes.STRING && isValidJsonString(updatedData))) {
            if (type === DataTypes.OBJECT || type === DataTypes.ARRAY) {
                updatedData = updatedData ? cloneDeep(updatedData) : {};
                formatJSONObjectOrArray(updatedData, collection.subCollections, props.truncateDateTime);
                updatedData = clearxpath(updatedData);
            } else {
                updatedData = updatedData.replace(/\\/g, '');
                updatedData = JSON.parse(updatedData);
            }
            excludeNullFromObject(updatedData);
            classesArray.push(classes.abbreviated_json_cell);
            const classesStr = classesArray.join(' ');

            return (
                <TableCell 
                    className={classesStr} 
                    sx={{backgroundColor: dataSourceColor}}
                    align='center' 
                    size='small' 
                    onClick={onOpenTooltip}>
                    <AbbreviatedJson open={open} onClose={onCloseTooltip} src={updatedData} />
                </TableCell >
            )
        } else if (type === DataTypes.STRING && !isValidJsonString(updatedData)) {
            let tooltipText = '';
            if (updatedData !== null && updatedData !== undefined) {
                let lines = updatedData.replace(/\\n/g, '\n').split('\n');
                tooltipText = (
                    <>
                        {lines.map((line, idx) => (
                            <p key={idx}>
                                {idx === 0 && (
                                    <IconButton className={classes.icon} size='small' onClick={() => copyHandler(updatedData)}>
                                        <ContentCopy fontSize='small' />
                                    </IconButton>
                                )}
                                {line}
                            </p>
                        ))}
                    </>
                )
            }
            classesArray.push(classes.abbreviated_json_cell);
            const classesStr = classesArray.join(' ');

            return (
                <TableCell 
                    className={classesStr} 
                    sx={{backgroundColor: dataSourceColor}}
                    align='center' 
                    size='small' 
                    onClick={onOpenTooltip}>
                    <CopyToClipboard text={clipboardText} copy={clipboardText !== null} />
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
        min = getValueFromReduxStoreFromXpath(reducerDict, min);
    }

    let max = collection.max;
    if (typeof (max) === DataTypes.STRING) {
        max = getValueFromReduxStoreFromXpath(reducerDict, max);
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
    let text, linkText = null;
    if (collection.type === DataTypes.DATE_TIME) {
        linkText = value;
        if (!linkText) {
            text = null;
        } else {
            const localDateTime = dayjs.utc(linkText).tz(localTimezone);
            if (collection.displayType === 'datetime') {
                text = localDateTime.format('YYYY-MM-DD HH:mm:ss.SSS');
            } else {
                text = localDateTime.isSame(dayjs(), 'day') ? localDateTime.format('HH:mm:ss.SSS') : localDateTime.format('YYYY-MM-DD HH:mm:ss.SSS');
            }
        }
        value = text;
    }
    let dataModified = previousValue !== currentValue;
    // if (tableCellColorClass) {
    //     classesArray.push(tableCellColorClass);
    // }
    if (disabledClass) {
        classesArray.push(disabledClass);
    }

    if (mode === Modes.EDIT_MODE && dataModified && !collection.serverPopulate && !collection.ormNoUpdate) {
        let originalValue = previousValue !== undefined && previousValue !== null ? previousValue : '';
        if (collection.displayType === DataTypes.INTEGER && typeof (originalValue) === DataTypes.NUMBER) {
            originalValue = floatToInt(originalValue);
        }
        originalValue = originalValue.toLocaleString();

        const classesStr = classesArray.join(' ');
        return (
            <TableCell 
                className={classesStr}
                sx={{backgroundColor: dataSourceColor}} 
                align={textAlign} 
                size='small' 
                onClick={onFocusIn} 
                data-xpath={xpath} 
                data-dataxpath={dataxpath}>
                <div className={tableCellColorClass}>
                    {originalValue ? <span className={classes.previous}>{originalValue}{numberSuffix}</span> : <span className={classes.previous}>{originalValue}</span>}
                    {value ? <span className={classes.modified}>{value}{numberSuffix}</span> : <span className={classes.modified}>{value}</span>}
                    {validationError.current && (
                        <Tooltip sx={{ marginLeft: '20px' }} title={validationError.current} disableInteractive><Error color='error' /></Tooltip>
                    )}
                </div>
            </TableCell>
        )
    } else {
        if (tableCellRemove) {
            classesArray.push(tableCellRemove);
        }
        if (newUpdateClass) {
            classesArray.push(newUpdateClass);
        }
        const classesStr = classesArray.join(' ');
        return (
            <TableCell 
                className={classesStr} 
                sx={{backgroundColor: dataSourceColor}}
                align={textAlign} 
                size='small' 
                onClick={onFocusIn} 
                data-xpath={xpath} 
                data-dataxpath={dataxpath}>
                <div className={tableCellColorClass}>
                    {/* {collection.displayType === 'time' ? <LinkText text={text} linkText={linkText} /> : */}
                    {/* value ? <span>{value}{numberSuffix}</span> : <span>{value}</span>} */}
                    {value ? <span>{value}{numberSuffix}</span> : <span>{value}</span>}
                    {validationError.current && (
                        <Tooltip title={validationError.current} sx={{ marginLeft: '20px' }} disableInteractive><Error color='error' /></Tooltip>
                    )}
                </div>
            </TableCell>
        )
    }
}

Cell.propTypes = {
    mode: PropTypes.oneOf([Modes.READ_MODE, Modes.EDIT_MODE]).isRequired,
    rowindex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    name: PropTypes.string.isRequired,
    // elaborateTitle: PropTypes.string.isRequired,
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