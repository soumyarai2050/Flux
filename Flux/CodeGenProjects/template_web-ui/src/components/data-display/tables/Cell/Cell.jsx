import React, { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { useSelector } from 'react-redux';
import _, { cloneDeep, debounce, isEqual } from 'lodash';
import PropTypes from 'prop-types';
import { NumericFormat } from 'react-number-format';
import { MenuItem, TableCell, Select, TextField, Checkbox, Autocomplete, Tooltip, ClickAwayListener, InputAdornment, IconButton } from '@mui/material';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { ContentCopy, Error, Clear } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { clearxpath } from '../../../../utils/core/dataAccess';
import { isValidJsonString, toCamelCase, capitalizeCamelCase } from '../../../../utils/core/stringUtils';
import { getSizeFromValue, getShapeFromValue, getHoverTextType, getReducerArrayFromCollections } from '../../../../utils/ui/uiUtils';
import { getResolvedColor, getColorTypeFromValue } from '../../../../utils/ui/colorUtils';
import { getValueFromReduxStoreFromXpath } from '../../../../utils/redux/reduxUtils';
import { floatToInt, getLocalizedValueAndSuffix } from '../../../../utils/formatters/numberUtils';
import { validateConstraints } from '../../../../utils/validation/validationUtils';
import { excludeNullFromObject, formatJSONObjectOrArray } from '../../../../utils/core/objectUtils';
import { getDateTimeFromInt } from '../../../../utils/formatters/dateUtils';
import { getDataSourceColor } from '../../../../utils/ui/themeUtils';
import { COLOR_TYPES, DATA_TYPES, HIGHLIGHT_STATES, MODEL_TYPES, MODES } from '../../../../constants';
import JsonView from '../../JsonView';
import VerticalDataTable from '../VerticalDataTable';
import ValueBasedToggleButton from '../../../ui/ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from '../../../ui/ValueBasedProgressBar';
import classes from './Cell.module.css';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import ClipboardCopier from '../../../utility/ClipboardCopier';
import AlertBubble from '../../../ui/AlertBubble';
import LinkText from '../../../ui/LinkText';
dayjs.extend(utc);
dayjs.extend(timezone);

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
        selected,
        stickyPosition,
        highlightDuration,
        onCellMouseDown,
        onCellMouseEnter,
        onCellMouseClick
    } = props;

    const theme = useTheme();
    const {collection} = props;
    // const state = useSelector(state => state);
    const reducerArray = useMemo(() => getReducerArrayFromCollections([props.collection]), [props.collection]);
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
    const [isDateTimePickerOpen, setIsDateTimePickerOpen] = useState(false);
    const [autocompleteInputValue, setAutocompleteInputValue] = useState('');
    const inputRef = useRef(null);
    const cursorPos = useRef(null);
    const autocompleteRef = useRef(null);
    const jsonTableRef = useRef(null);
    const onTextChangeRef = useRef(props.onTextChange);
    const initialValueChangeRef = useRef(true);

    useEffect(() => {
        onTextChangeRef.current = props.onTextChange;
    }, [props.onTextChange])

    useEffect(() => {
        setInputValue(currentValue);
    }, [props.index, mode, props.forceUpdate])

    useEffect(() => {
        if (mode === MODES.READ) {
            setInputValue(currentValue);
        }
    }, [currentValue])

    // Handle autocomplete blur with dropdown detection
    const handleAutocompleteBlur = useCallback(() => {
        setTimeout(() => {
            const autocompleteRoot = autocompleteRef.current?.closest('.MuiAutocomplete-root');
            const activeElement = document.activeElement;

            if (autocompleteRoot && !autocompleteRoot.contains(activeElement)) {
                const isInDropdown = activeElement?.closest('.MuiAutocomplete-popper') ||
                    activeElement?.closest('[role="listbox"]') ||
                    activeElement?.closest('.MuiAutocomplete-listbox');

                if (!isInDropdown) {
                    setActive(false);
                }
            }
        }, 100);
    }, []);

    // Global click handler to deactivate other autocomplete fields
    useEffect(() => {
        if (active && collection?.autocomplete) {
            const handleGlobalClick = (event) => {
                const currentAutocompleteRoot = autocompleteRef.current?.closest('.MuiAutocomplete-root');
                const clickedElement = event.target;

                // Check if click is in dropdown
                const isInDropdown = clickedElement?.closest('.MuiAutocomplete-popper') ||
                    clickedElement?.closest('[role="listbox"]') ||
                    clickedElement?.closest('.MuiAutocomplete-listbox');

                // If click is outside this autocomplete AND not in dropdown
                if (currentAutocompleteRoot && !currentAutocompleteRoot.contains(clickedElement) && !isInDropdown) {
                    setActive(false);
                }
            };

            document.addEventListener('mousedown', handleGlobalClick);
            return () => {
                document.removeEventListener('mousedown', handleGlobalClick);
            };
        }
    }, [active, collection?.autocomplete]);

    useEffect(() => {
        if (inputRef.current && active && cursorPos.current !== null) {
            if (inputRef.current.selectionStart !== cursorPos.current) {
                inputRef.current.setSelectionRange(cursorPos.current, cursorPos.current);
            }
        }
    }, [inputValue])

    // useEffect(() => {
    //     if (props.onFormUpdate && xpath) {
    //         props.onFormUpdate(xpath, validationError.current);
    //     }
    // }, [validationError.current])

    useEffect(() => {
        if (collection.highlightUpdate && collection.highlightUpdate !== HIGHLIGHT_STATES.NONE && mode === MODES.READ && currentValue !== oldValue) {
            if (collection.highlightUpdate === HIGHLIGHT_STATES.HIGH_LOW) {
                if (currentValue > oldValue) {
                    setNewUpdateClass(classes.new_update_increase);
                } else if (currentValue < oldValue) {
                    setNewUpdateClass(classes.new_update_decrease);
                }
            } else if (collection.highlightUpdate === HIGHLIGHT_STATES.CHANGE) {
                setNewUpdateClass(classes.new_update);
            }

            if (timeoutRef.current !== null) {
                clearTimeout(timeoutRef.current);
            }
            timeoutRef.current = setTimeout(() => {
                setNewUpdateClass("");
            }, highlightDuration * 1000);
            setOldValue(currentValue);
        }
    }, [currentValue, oldValue, timeoutRef, classes, mode, collection.highlightUpdate, highlightDuration])

    const stickyClass = {
        position: collection.frozenColumn ? 'sticky' : 'static',
        left: stickyPosition,
        zIndex: collection.frozenColumn ? 2 : 1
    }

    const onRowSelect = (e) => {
        if (!collection.commonGroupKey) {
            if (props.modelType === MODEL_TYPES.ROOT) {
                props.onRowSelect(e, rowindex);
            } else {
                props.onRowSelect(e, dataSourceId);
            }
        }
    }

    const handleCellMouseDown = (e) => {
        if (mode === MODES.READ && onCellMouseDown) {
            // Only use drag handlers in read mode
            const rowId = props.modelType === MODEL_TYPES.ROOT ? rowindex : dataSourceId;
            onCellMouseDown(e, rowId);
        }
        // In edit mode or when no drag handlers, don't interfere with default behavior
    }

    const handleCellMouseEnter = (e) => {
        if (mode === MODES.READ && onCellMouseEnter) {
            // Only use drag handlers in read mode
            const rowId = props.modelType === MODEL_TYPES.ROOT ? rowindex : dataSourceId;
            onCellMouseEnter(e, rowId);
        }
    }

    const handleCellMouseClick = (e) => {
        if (mode === MODES.EDIT) {
            // In edit mode, use focus behavior for cell editing
            onFocusIn(e);
        } else if (onCellMouseClick) {
            // In read mode with drag handlers, use drag-aware selection
            const rowId = props.modelType === MODEL_TYPES.ROOT ? rowindex : dataSourceId;
            onCellMouseClick(e, rowId);
        } else {
            // Fallback to regular row selection if no drag handler provided
            onRowSelect(e);
        }
    }

    // Debounced transformation to update rows from the source JSON.
    const debouncedTransform = useRef(
        debounce((e, type, xpath, value, dataxpath, validationRes, dataSourceId, source) => {
            onTextChangeRef.current(e, type, xpath, value, dataxpath, validationRes, dataSourceId, source);
        }, 300)
    ).current;

    const handleBlur = () => {
        debouncedTransform.flush();
    }

    const handleTextChange = (e, type, xpath, value, dataxpath, validationRes, dataSourceId, source) => {
        cursorPos.current = e?.target.selectionStart ?? null;
        setInputValue(value);
        debouncedTransform(e, type, xpath, value, dataxpath, validationRes, dataSourceId, source);
    }

    const handleKeyDown = (e, filteredOptions) => {
        if (e.keyCode === 13) {
            if (filteredOptions.length === 1) {
                props.onAutocompleteOptionChange(e, filteredOptions[0], dataxpath, xpath, dataSourceId, collection.source);
                setAutocompleteInputValue('');

                if (autocompleteRef.current) {
                    autocompleteRef.current.blur();
                }
            }
        }
    }

    const onFocusIn = (e) => {
        if (mode === MODES.EDIT) {
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
            if (typeof storedValue === DATA_TYPES.NUMBER && typeof updatedValue === DATA_TYPES.NUMBER) {
                const diffPercentage = Math.abs(updatedValue - storedValue) * 100 / Math.abs(storedValue);
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

    let type = DATA_TYPES.STRING;
    let enumValues = [];
    let required = false;

    let value = currentValue;
    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
        required = collection.required;

        if (collection.autocomplete) {
            value = value ? value : value === 0 ? '0' : null;
        } else if (type === DATA_TYPES.BOOLEAN) {
            value = value ? value : value === false ? false : null;
        } else if (type === DATA_TYPES.ENUM) {
            value = value ? value : null;
        } else if (type === DATA_TYPES.NUMBER) {
            value = (inputValue || inputValue === 0) ? inputValue : '';
            if (collection.displayType === DATA_TYPES.INTEGER) {
                if (value !== '') {
                    value = floatToInt(value);
                }
            }
        } else if (type === DATA_TYPES.DATE_TIME) {
            value = value || null;
        } else if (type === DATA_TYPES.STRING) {
            // if (mode === MODES.EDIT) {
            //     value = inputValue ? inputValue : inputValue;
            // }
            value = inputValue ?? '';
        } else if (collection.abbreviated === 'JSON') {
            if (typeof value === DATA_TYPES.OBJECT) {
                value = JSON.stringify(value);
            }
        }
    }
    let color = getColorTypeFromValue(collection, currentValue);
    const colorStyle = getResolvedColor(color, theme, null, true);
    let tableCellRemove = dataRemove ? classes.remove : dataAdd ? classes.add : '';
    let disabledClass = disabled ? classes.disabled : '';
    if (props.ignoreDisable) {
        disabledClass = "";
    }
    let textAlign = collection.textAlign ? collection.textAlign : 'center';
    let selectedClass = '';
    if (selected && !(collection.joinKey || collection.commonGroupKey)) {
        selectedClass = props.mostRecent ? classes.cell_selected_recent : classes.cell_selected;
    }

    if (props.nullCell) {
        const classesStr = `${classes.cell} ${disabledClass}`;
        return (
            <TableCell sx={stickyClass} className={classesStr} size='small' data-xpath={xpath} />
        )
    }

    if (disabled) {
        if (value === null) {
            value = '';
        }
        if (type === DATA_TYPES.DATE_TIME) {
            if (value !== '') {
                const dateTimeWithTimezone = getDateTimeFromInt(value);
                if (collection.displayType === 'datetime') {
                    value = dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
                } else {
                    value = dateTimeWithTimezone.isSame(dayjs(), 'day') ? dateTimeWithTimezone.format('HH:mm:ss.SSS') : dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
                }
            }
        }
        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
        value = v;
        if (typeof value === DATA_TYPES.NUMBER) {
            value = value.toLocaleString();
        }
        const classesStr = `${classes.cell} ${selectedClass} ${disabledClass} ${tableCellRemove} ${newUpdateClass}`;
        return (
            <TableCell
                className={classesStr}
                sx={{ backgroundColor: dataSourceColor, ...stickyClass, ...colorStyle }}
                align={textAlign}
                size='small'
                data-xpath={xpath}
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}
                onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}
                data-dataxpath={dataxpath}>
                {value}{numberSuffix}
            </TableCell>
        )
    }
    const placeholder = collection.placeholder ? collection.placeholder : !required ? 'optional' : null;

    if (mode === MODES.EDIT && active && !disabled && !([MODEL_TYPES.REPEATED_ROOT, MODEL_TYPES.ABBREVIATION_MERGE].includes(props.modelType) && !props.selected) && (!(collection.ormNoUpdate && !dataAdd)) && !collection.serverPopulate) {
        if (type !== DATA_TYPES.ENUM && collection.autocomplete) {
            validationError.current = validateConstraints(collection, value);

            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const inputProps = endAdornment ? {
                endAdornment: endAdornment
            } : {};

            if (collection.dynamic_autocomplete) {
                const dynamicValue = getValueFromReduxStoreFromXpath(reducerDict, collection.autocomplete);
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
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={(e) => {
                        handleCellMouseClick(e);
                        onFocusIn(e);
                    }}
                    onMouseDown={handleCellMouseDown}
                    onMouseEnter={handleCellMouseEnter}
                    onDoubleClick={(e) => props.onDoubleClick(e, rowindex, xpath)}>
                    <Autocomplete
                        id={collection.key}
                        options={collection.options}
                        getOptionLabel={(option) => option?.toString()}
                        isOptionEqualToValue={(option, value) => (
                            option === value || (option === 0 && value === 0)
                        )}
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
                        inputValue={autocompleteInputValue}
                        onInputChange={(e, newInputValue) => setAutocompleteInputValue(newInputValue)}
                        filterOptions={(options, { inputValue }) =>
                            options.filter(option => String(option).toLowerCase().includes(inputValue.toLowerCase()))
                        }
                        onBlur={handleAutocompleteBlur}
                        onFocus={onFocusIn}
                        onOpen={onFocusIn}
                        onClose={handleAutocompleteBlur}
                        autoFocus
                        onChange={(e, v) => {
                            props.onAutocompleteOptionChange(e, v, dataxpath, xpath, dataSourceId, collection.source);
                            setAutocompleteInputValue('');
                        }}
                        renderInput={(params) => {
                            const filteredOptions = collection.options.filter(option => String(option).toLowerCase().includes(autocompleteInputValue.toLowerCase()));
                            return (
                                <TextField
                                    {...params}
                                    name={collection.key}
                                    error={validationError.current !== null}
                                    placeholder={placeholder}
                                    onFocus={onFocusIn}
                                    onBlur={handleAutocompleteBlur}
                                    onKeyDown={(e) => handleKeyDown(e, filteredOptions)}
                                    inputRef={autocompleteRef}
                                    InputProps={{
                                        ...params.InputProps,
                                        ...inputProps
                                    }}
                                />
                            )
                        }}
                        componentsProps={{
                            popper: {
                                modifiers: [
                                    {
                                        name: 'setWidth',
                                        enabled: true,
                                        phase: 'beforeWrite',
                                        requires: ['computeStyles'],
                                        fn({ state }) {
                                            state.styles.popper.width = 'auto';
                                        },
                                    },
                                ],
                            },
                        }}
                    />
                </TableCell>
            )
        } else if (type === DATA_TYPES.BOOLEAN) {
            validationError.current = validateConstraints(collection, value);
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
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
        } else if (type === DATA_TYPES.ENUM) {
            validationError.current = validateConstraints(collection, value);
            const endAdornment = validationError.current ? (
                <InputAdornment position='end'><Tooltip title={validationError.current} disableInteractive><Error color='error' /></Tooltip></InputAdornment>
            ) : null;
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
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
        } else if (type === DATA_TYPES.NUMBER) {
            // round the decimal places for float. default precision is 2 digits for float
            let decimalScale = 2;
            if (collection.underlyingtype === DATA_TYPES.INT32 || collection.underlyingtype === DATA_TYPES.INT64) {
                decimalScale = 0;
            }
            if (collection.numberFormat && collection.numberFormat.includes(".")) {
                decimalScale = collection.numberFormat.split(".").pop();
                decimalScale = decimalScale * 1;
            }

            // min constrainsts for numeric field if set.
            let min = collection.min;
            if (typeof (min) === DATA_TYPES.STRING) {
                min = getValueFromReduxStoreFromXpath(reducerDict, min);
            }

            // max constrainsts for numeric field if set.
            let max = collection.max;
            if (typeof (max) === DATA_TYPES.STRING) {
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
                    {collection.numberFormat && collection.numberFormat === '$' && (
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
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;

            return (
                <TableCell
                    className={classesStr}
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onBlur={onFocusOut}
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
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
                        onValueChange={(values, sourceInfo) => handleTextChange(sourceInfo.event, type, xpath, values.value, dataxpath,
                            validateConstraints(collection, values.value, min, max), dataSourceId, collection.source)}
                        variant='outlined'
                        decimalScale={decimalScale}
                        placeholder={placeholder}
                        autoFocus
                        onBlur={handleBlur}
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
        } else if (type === DATA_TYPES.DATE_TIME) {
            validationError.current = validateConstraints(collection, value);
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
                if (collection.displayType !== 'datetime') {
                    if (dateTimeWithTimezone.isSame(dayjs(), 'day')) {
                        inputFormat = 'HH:mm:ss';
                    }
                    // else - use default input format
                }
                // else - use default input format
            }
            // else - use default input format
            const classesStr = `${classes.cell_input_field} ${selectedClass}`;
            return (
                <TableCell
                    className={classesStr}
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
                    onBlur={() => {
                        if (!isDateTimePickerOpen) {
                            onFocusOut();
                        }
                    }}
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
                            inputFormat={inputFormat}
                            InputProps={inputProps}
                            onChange={(newValue) => {
                                const newDate = new Date(newValue);
                                newDate.setSeconds(0, 0);
                                props.onDateTimeChange(dataxpath, xpath, newDate.toISOString(), dataSourceId, collection.source);
                            }}
                            inputProps={{
                                style: { padding: '6px 10px' },
                                dataxpath: dataxpath,
                                underlyingtype: collection.underlyingtype
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
                                            props.onDateTimeChange(dataxpath, xpath, newDate.toISOString(), dataSourceId, collection.source);
                                        }
                                        setIsDateTimePickerOpen(true);
                                    }}
                                    InputProps={{
                                        readOnly: true,
                                        endAdornment: (
                                            <InputAdornment position='end'>
                                                <IconButton
                                                    onClick={(e) => {
                                                        props.onDateTimeChange(dataxpath, xpath, null, dataSourceId, collection.source);
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
                </TableCell>
            )
        } else if (type === DATA_TYPES.STRING && !collection.abbreviated) {
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
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onKeyDown={onKeyDown}
                    onBlur={onFocusOut}
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
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
                        onBlur={handleBlur}
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
        const bubbleColor = value ? value[1] : COLOR_TYPES.DEFAULT;
        return (
            <TableCell
                className={classesStr}
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                // sx={{ width: 20 }}
                align='center'
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}>
                {bubbleCount > 0 && <AlertBubble content={bubbleCount} color={bubbleColor} />}
            </TableCell >
        )
    }

    // read-only checkbox component
    if (type === DATA_TYPES.BOOLEAN) {
        const classesStr = classesArray.join(' ');
        return (
            <TableCell
                className={classesStr}
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                align='center'
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}>
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
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
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
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                align='center'
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}>
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
                    hideCaption={collection.button.hide_caption}
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
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    size='small'
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}
                />
            )
        }

        const valueFieldName = props.name;
        let maxFieldName = collection.maxFieldName;
        let min = collection.min;
        if (typeof (min) === DATA_TYPES.STRING) {
            min = getValueFromReduxStoreFromXpath(reducerDict, min);
        }
        let max = collection.max;
        if (typeof (max) === DATA_TYPES.STRING) {
            maxFieldName = max.substring(max.lastIndexOf(".") + 1);
            max = getValueFromReduxStoreFromXpath(reducerDict, max);
        }
        const hoverType = getHoverTextType(collection.progressBar.hover_text_type);
        classesArray.push(classes.cell_no_padding);
        const classesStr = classesArray.join(' ');

        return (
            <TableCell
                className={classesStr}
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                align='center'
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}>
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
        if (type === DATA_TYPES.OBJECT || type === DATA_TYPES.ARRAY || (type === DATA_TYPES.STRING && isValidJsonString(updatedData))) {
            if (type === DATA_TYPES.OBJECT || type === DATA_TYPES.ARRAY) {
                updatedData = updatedData ? cloneDeep(updatedData) : null;
                if (updatedData) {
                    formatJSONObjectOrArray(updatedData, collection.subCollections, props.truncateDateTime);
                    updatedData = clearxpath(updatedData);
                }
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
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}>
                    {updatedData && (
                        <>
                            <div className={classes.abbreviated_json_cell} ref={jsonTableRef} onClick={(e) => { e.stopPropagation(); onOpenTooltip(e); }} style={{ cursor: 'pointer' }}>
                                <span>{JSON.stringify(updatedData)}</span>
                            </div>
                            <VerticalDataTable
                                isOpen={open}
                                data={updatedData}
                                onClose={onCloseTooltip}
                                usePopover={true}
                                anchorEl={jsonTableRef.current}
                                fieldsMetadata={collection.subCollections || []}
                            />
                        </>
                    )}
                    {/* <JsonView open={open} onClose={onCloseTooltip} src={updatedData} /> */}
                </TableCell>
            )
        } else if (type === DATA_TYPES.STRING && !isValidJsonString(updatedData)) {
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
            // classesArray.push(classes.abbreviated_json_cell);
            const classesStr = classesArray.join(' ');

            return (
                <TableCell
                    className={classesStr}
                    sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                    align='center'
                    size='small'
                    onClick={mode === MODES.EDIT ? onRowSelect : handleCellMouseClick}
                    onMouseDown={mode === MODES.READ ? handleCellMouseDown : undefined}
                    onMouseEnter={mode === MODES.READ ? handleCellMouseEnter : undefined}>
                    <ClipboardCopier text={clipboardText} />
                    {/* <ClickAwayListener onClickAway={onCloseTooltip}>
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
                    </ClickAwayListener> */}
                    <LinkText text={updatedData} onClick={onOpenTooltip} />
                </TableCell>
            )
        }
    }

    let min = collection.min;
    if (typeof (min) === DATA_TYPES.STRING) {
        min = getValueFromReduxStoreFromXpath(reducerDict, min);
    }

    let max = collection.max;
    if (typeof (max) === DATA_TYPES.STRING) {
        max = getValueFromReduxStoreFromXpath(reducerDict, max);
    }
    validationError.current = validateConstraints(collection, value, min, max);

    if (value === null) {
        value = '';
    }

    if (collection.type === DATA_TYPES.DATE_TIME) {
        let text, linkText = null;
        linkText = value;
        if (!linkText) {
            text = null;
        } else {
            const dateTimeWithTimezone = getDateTimeFromInt(linkText);
            if (collection.displayType === 'datetime') {
                text = dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
            } else {
                text = dateTimeWithTimezone.isSame(dayjs(), 'day') ? dateTimeWithTimezone.format('HH:mm:ss.SSS') : dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
            }
        }
        value = text;
    }
    let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
    value = v;
    if (typeof value === DATA_TYPES.NUMBER) {
        value = value.toLocaleString();
    }
    let dataModified = previousValue !== currentValue;
    // if (tableCellColorClass) {
    //     classesArray.push(tableCellColorClass);
    // }
    if (disabledClass) {
        classesArray.push(disabledClass);
    }

    if (mode === MODES.EDIT && dataModified && !collection.serverPopulate && !collection.ormNoUpdate) {
        let originalValue = previousValue !== undefined && previousValue !== null ? previousValue : '';
        if (collection.displayType === DATA_TYPES.INTEGER && typeof (originalValue) === DATA_TYPES.NUMBER) {
            originalValue = floatToInt(originalValue);
        }
        originalValue = originalValue.toLocaleString();

        const classesStr = classesArray.join(' ');
        return (
            <TableCell
                className={classesStr}
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                align={textAlign}
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}
                data-xpath={xpath}
                data-dataxpath={dataxpath}>
                <div style={colorStyle}>
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
                sx={{ backgroundColor: dataSourceColor, ...stickyClass }}
                align={textAlign}
                size='small'
                onClick={handleCellMouseClick}
                onMouseDown={handleCellMouseDown}
                onMouseEnter={handleCellMouseEnter}
                data-xpath={xpath}
                data-dataxpath={dataxpath}>
                <div style={colorStyle}>
                    {/* {collection.displayType === 'time' ? <LinkText text={text} linkText={linkText} /> :
                    // value ? <span>{value}{numberSuffix}</span> : <span>{value}</span>} */}
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
    mode: PropTypes.oneOf([MODES.READ, MODES.EDIT]).isRequired,
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