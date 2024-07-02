import React, { useState, useEffect, useCallback, useRef, Fragment, memo } from 'react';
import _, { cloneDeep } from 'lodash';
import {
    TableContainer, Table, TableBody, DialogTitle, DialogContent, DialogContentText,
    DialogActions, Button, Select, MenuItem, Checkbox, FormControlLabel, Dialog, TablePagination,
    Snackbar, Alert, TextField, Popover, Box
} from '@mui/material';
import axios from 'axios';
import { Settings, Close, Visibility, VisibilityOff, FileDownload, LiveHelp, Help } from '@mui/icons-material';
import { utils, writeFileXLSX } from 'xlsx';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { generateRowTrees, generateRowsFromTree, getCommonKeyCollections, getTableRowsFromData, sortColumns, getActiveRows } from '../utils';
import { API_ROOT_URL, DataTypes, DB_ID, Modes } from '../constants';
import TreeWidget from './TreeWidget';
import WidgetContainer from './WidgetContainer';
import TableHead from './TableHead';
import FullScreenModal from './Modal';
import Row from './Row';
import { Icon } from './Icon';
import { AlertErrorMessage } from './Alert';
import classes from './TableWidget.module.css';
import CopyToClipboard from './CopyToClipboard';
import { PageCache, PageSizeCache, SortOrderCache } from '../utility/attributeCache';
import ValueBasedToggleButton from './ValueBasedToggleButton';

const TableWidget = (props) => {
    const [rowTrees, setRowTrees] = useState([]);
    const [rows, setRows] = useState(props.rows);
    const [headCells, setHeadCells] = useState(props.tableColumns);
    const [commonkeys, setCommonkeys] = useState(props.commonKeyCollections);
    // index of the item in row
    const [selectedRow, setSelectedRow] = useState();
    const [selectedRows, setSelectedRows] = useState([]);
    const [data, setData] = useState(props.data);
    const [open, setOpen] = useState(false); // for full height modal
    const [openSettings, setOpenSettings] = useState(false);
    const [settingsArchorEl, setSettingsArcholEl] = useState();
    const [hide, setHide] = useState(true);
    const [rowsPerPage, setRowsPerPage] = useState(PageSizeCache.getPageSize(props.name));
    const [page, setPage] = useState(PageCache.getPage(props.name));
    const [sortOrders, setSortOrders] = useState(props.sortOrders ? props.sortOrders : []);
    const [openModalPopup, setOpenModalPopup] = useState(false);
    // const [selectAll, setSelectAll] = useState(false);
    const [toastMessage, setToastMessage] = useState(null);
    const [clipboardText, setClipboardText] = useState(null);
    const [userChanges, setUserChanges] = useState({});
    const [openVisibilityMenu, setOpenVisibilityMenu] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [visibilityMenuArchorEl, setVisibilityMenuAnchorEl] = useState();
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const visibilityMenuClickTimeout = useRef(null);

    useEffect(() => {
        setData(props.data);
        setRows(props.rows);
        setHeadCells(props.tableColumns);
        // creates column flickering if enabled
        // setCommonkeys(props.commonKeyCollections);
    }, [props.data, props.rows]);

    useEffect(() => {
        let trees = generateRowTrees(cloneDeep(data), props.collections, props.xpath);
        setRowTrees(trees);
    }, [props.collections, data, props.xpath])

    useEffect(() => {
        if (props.sortOrders) {
            setSortOrders(props.sortOrders);
        } else {
            setSortOrders([]);
        }
    }, [props.sortOrders])

    useEffect(() => {
        let commonKeyCollections = getCommonKeyCollections(rows, headCells, hide && !showAll, false, props.widgetType === 'repeatedRoot' ? true : false, !showMore && !moreAll);
        setCommonkeys(commonKeyCollections);
    }, [rows, headCells, props.mode, hide, showMore, showAll, moreAll])

    useEffect(() => {
        if (rows.length === 0) {
            let updatedData = cloneDeep(props.formValidation);
            if (props.xpath) {
                for (const key in updatedData) {
                    if (key.startsWith(props.xpath)) {
                        props.onFormUpdate(key, null);
                    }
                }
            } else {
                for (const key in updatedData) {
                    props.onFormUpdate(key, null);
                }
            }
        }
    }, [rows, props.xpath])

    function getFilteredCells() {
        let updatedCells = cloneDeep(headCells);
        if (hide && !showAll) {
            updatedCells = updatedCells.filter(cell => !cell.hide);
        }
        if (!showMore && !moreAll) {
            updatedCells = updatedCells.filter(cell => !cell.showLess);
        }
        updatedCells = updatedCells.filter(cell => {
            if (commonkeys.filter(commonkey => commonkey.key === cell.key && commonkey.tableTitle === cell.tableTitle && commonkey.sourceIndex === cell.sourceIndex).length > 0 && props.mode !== Modes.EDIT_MODE) {
                return false;
            }
            return true;
        })
        updatedCells = sortColumns(updatedCells, props.columnOrders, props.groupBy, props.centerJoin, props.flip);
        return updatedCells;
    }

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
        PageCache.setPage(props.name, newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        const size = parseInt(event.target.value, 10);
        setRowsPerPage(size);
        PageSizeCache.setPageSize(props.name, size);
        setPage(0);
        PageCache.setPage(props.name, 0);
    };

    // const onSelectAll = (e) => {
    //     let updatedHeadCells = cloneDeep(headCells);
    //     if (e.target.checked) {
    //         updatedHeadCells = updatedHeadCells.map(cell => {
    //             cell.hide = false;
    //             return cell;
    //         })
    //     } else {
    //         updatedHeadCells = updatedHeadCells.map(cell => {
    //             cell.hide = true;
    //             return cell;
    //         })
    //     }
    //     setSelectAll(e.target.checked);
    //     setHeadCells(updatedHeadCells);
    // }

    const showAllHandler = (e, action, key, value, dataSourceId, source) => {
        setShowAll(!value);
    }

    const moreAllHandler = (e, action, key, value, dataSourceId, source) => {
        setMoreAll(!value);
    }

    const handleRequestSort = (event, property, retainSortLevel = false) => {
        let updatedSortOrders = cloneDeep(sortOrders);
        if (!retainSortLevel) {
            updatedSortOrders = updatedSortOrders.filter(o => o.order_by === property);
        }
        const sortOrder = updatedSortOrders.find(o => o.order_by === property);
        if (sortOrder) {
            // sort level already exists for this property
            sortOrder.sort_type = sortOrder.sort_type === 'asc' ? 'desc' : 'asc';
        } else {
            // add a new sort level
            updatedSortOrders.push({ order_by: property, sort_type: 'asc' });
        }
        setSortOrders(updatedSortOrders);
        props.onSortOrdersChange(updatedSortOrders);
        // SortOrderCache.setSortOrder(props.name, updatedSortOrders);
        setPage(0);
        PageCache.setPage(props.name, 0);
    }

    const handleRemoveSort = (property) => {
        const updatedSortOrders = sortOrders.filter(o => o.order_by !== property);
        setSortOrders(updatedSortOrders);
        // SortOrderCache.setSortOrder(props.name, updatedSortOrders);
        props.onSortOrdersChange(updatedSortOrders);
    }

    const onSave = () => {
        if (props.widgetType === 'repeatedRoot') {
            const updatedObj = data.find(obj => obj[DB_ID] === selectedRows[0]);
            if (updatedObj) {
                props.onUpdate(updatedObj);
            } else {
                console.error('updatedObj not found');
            }
        } else {
            props.onUpdate(data);
        }
        setOpen(false);
        setOpenModalPopup(false);
    }

    const onRowClick = (e, index, xpath) => {
        if (props.mode === Modes.EDIT_MODE) {
            setOpen(true);
            if (props.widgetType === 'repeatedRoot') {
                const idx = rowTrees.findIndex(row => row[DB_ID] === index);
                if (idx !== -1) {
                    setSelectedRow(idx);
                }
            } else {
                let updatedRows = generateRowsFromTree(rowTrees, props.collections, props.xpath);
                const idx = updatedRows.findIndex(row => row['data-id'] === index);
                if (idx !== -1) {
                    setSelectedRow(idx);
                }
            }
            setTimeout(() => {
                let modalId = props.name + '_modal';
                if (props.xpath) {
                    modalId = props.name + '_' + props.xpath + '_modal';
                }
                document.getElementById(modalId).querySelectorAll("[data-xpath='" + xpath + "']").forEach(el => {
                    el.classList.add(classes.highlight)
                })
            }, 500)
        }
    }

    const onRowSelect = (e, rowId) => {
        // event (e) is used to identify whether to select/unselect the row
        if (props.mode !== Modes.EDIT_MODE) {
            if (e.ctrlKey) {
                setSelectedRows([]);
                if (props.onSelectRow) {
                    props.onSelectRow(null);
                }
            } else {
                setSelectedRows([rowId]);
                if (props.onSelectRow) {
                    props.onSelectRow(rowId);
                }
            }
            // TODO: below condition is preventing the switch to be efficient
            // if (!selectedRows.includes(rowId)) {
                // setSelectedRows([rowId]);
                // props.onSelectRow(rowId);
            // }
        }
        // TODO: multiple row select removed
        // let updatedSelectedRows;
        // if (e.ctrlKey) {
        //     if (selectedRows.find(row => row === rowId)) {
        //         // rowId already selected. unselect the row
        //         updatedSelectedRows = selectedRows.filter(row => row !== rowId);
        //     } else {
        //         // new selected row. add it to selected array
        //         updatedSelectedRows = [...selectedRows, rowId];
        //     }
        // } else {
        //     updatedSelectedRows = [rowId];
        // }
        // setSelectedRows(updatedSelectedRows);
        // if (props.widgetType === 'repeatedRoot') {
        //     if (updatedSelectedRows.length === 1) {
        //         props.onSelectRow(rowId);
        //     } else {
        //         props.onSelectRow(null);
        //     }
        // }
    }

    const onRowDoubleClick = (e) => {
        if (props.mode === Modes.READ_MODE) {
            if (!e.target.closest('button')) {
                props.headerProps.onChangeMode();
            }
        }
    }

    // on closing of modal, open a pop up to confirm/discard changes
    const onClose = (e) => {
        if (!_.isEqual(props.data, data)) {
            setOpenModalPopup(true);
        } else {
            setOpen(false);
        }
    }

    // on closing of modal popup (discard), revert back the changes
    const onConfirmClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        else {
            setData(props.data);
            setOpen(false);
            setOpenModalPopup(false);
        }
    }

    const onUpdate = (updatedData, type) => {
        // add and remove only supported on non-repeated widgets
        if (type === 'add' || type === 'remove') {
            setOpen(false);
            props.onUpdate(updatedData);
            props.onUserChange(null, null, userChanges);
        } else {
            if (props.widgetType === 'repeatedRoot') {
                const idx = data.findIndex(obj => obj[DB_ID] === selectedRows[0]);
                if (idx !== -1) {
                    const updatedArray = cloneDeep(data);
                    updatedArray[idx] = updatedData;
                    setData(updatedArray);
                }
            } else {
                console.error('else case');
                setData(updatedData);
            }
        }
    }

    const onUserChange = (xpath, value) => {
        let updatedData = cloneDeep(userChanges);
        updatedData = { ...updatedData, [xpath]: value };
        setUserChanges(updatedData);
    }

    const onSettingsItemChange = (e, action, key, value, dataSourceId, source) => {
    // const onSettingsItemChange = (e, key) => {
        // let hide = !e.target.checked;
        let hide = value;
        if (hide) {
            // setSelectAll(false);
            setShowAll(false);
        }
        let updatedHeadCells = headCells.map((cell) => cell.tableTitle === key ? { ...cell, hide: hide } : cell)
        setHeadCells(updatedHeadCells);
        let collection = props.collections.filter(c => c.tableTitle === key)[0];
        let enableOverride = cloneDeep(props.enableOverride);
        let disableOverride = cloneDeep(props.disableOverride);
        if (hide) {
            if (collection.hide !== hide) {
                if (!enableOverride.includes(key)) {
                    enableOverride.push(key);
                }
            }
            let index = disableOverride.indexOf(key);
            if (index !== -1) {
                disableOverride.splice(index, 1);
            }
        } else {
            if (collection.hide !== undefined && collection.hide !== hide) {
                if (!disableOverride.includes(key)) {
                    disableOverride.push(key);
                }
            }
            let index = enableOverride.indexOf(key);
            if (index !== -1) {
                enableOverride.splice(index, 1);
            }
        }
        props.onOverrideChange(enableOverride, disableOverride);
    }

    const onShowLessChange = (e, action, key, value, dataSourceId, source) => {
        let less = value;
        let updatedHeadCells = headCells.map(cell => cell.tableTitle === key ? { ...cell, showLess: less } : cell)
        setHeadCells(updatedHeadCells);
        let collection = props.collections.filter(c => c.tableTitle === key)[0];
        const showLessArray = cloneDeep(props.showLess);
        if (less) {
            if (collection.showLess !== less) {
                if (!showLessArray.includes(key)) {
                    showLessArray.push(key);
                }
            }
        } else {
            let index = showLessArray.indexOf(key);
            if (index !== -1) {
                showLessArray.splice(index, 1);
            }
        }
        if (props.onShowLessChange) {
            props.onShowLessChange(showLessArray);
        }
    }

    const onSettingsOpen = (e) => {
        setOpenSettings(true);
        setSettingsArcholEl(e.currentTarget);
    }

    const onSettingsClose = (e) => {
        setOpenSettings(false);
        setSettingsArcholEl(null);
    }

    const onTextChange = useCallback((e, type, xpath, value, dataxpath, validationRes, dataSourceId, source = null) => {
        let updatedData;
        if (value === '') {
            value = null;
        }
        if (type === DataTypes.NUMBER) {
            if (value !== null) {
                value = value * 1;
            }
        }
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        const userChangeDict = {
            [DB_ID]: dataSourceId, 
            [xpath]: value
        }
        props.onUserChange(xpath, value, userChangeDict);
        if (props.onFormUpdate) {
            props.onFormUpdate(xpath, validationRes);
        }
    }, [data, props.onUpdate, props.onUserChange])

    const onSelectItemChange = useCallback((e, dataxpath, xpath, dataSourceId, source = null) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.value);
        props.onUpdate(updatedData);
        const userChangeDict = {
            [DB_ID]: dataSourceId, 
            [xpath]: e.target.value
        }
        props.onUserChange(xpath, e.target.value, userChangeDict);
    }, [data, props.onUpdate, props.onUserChange])

    const onCheckboxChange = useCallback((e, dataxpath, xpath, dataSourceId, source = null) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.checked);
        props.onUpdate(updatedData);
        const userChangeDict = {
            [DB_ID]: dataSourceId, 
            [xpath]: e.target.checked
        }
        props.onUserChange(xpath, e.target.checked, userChangeDict);
    }, [data, props.onUpdate, props.onUserChange])

    const onAutocompleteOptionChange = useCallback((e, value, dataxpath, xpath, dataSourceId, source = null) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        const userChangeDict = {
            [DB_ID]: dataSourceId, 
            [xpath]: value
        }
        props.onUserChange(xpath, value, userChangeDict);
    }, [data, props.onUpdate, props.onUserChange])

    const onDateTimeChange = useCallback((dataxpath, xpath, value, dataSourceId, source = null) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        const userChangeDict = {
            [DB_ID]: dataSourceId, 
            [xpath]: value
        }
        props.onUserChange(xpath, value, userChangeDict);
    }, [data, props.onUpdate, props.onUserChange])

    const onButtonClick = useCallback((e, action, xpath, value, dataSourceId, source = null, confirmSave = false) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData, dataSourceId, source, confirmSave);
        } else if (action === 'flux_trigger_strat') {
            let updatedData = flux_trigger_strat(value);
            if (updatedData) {
                props.onButtonToggle(e, xpath, updatedData, dataSourceId, source, confirmSave);
            }
        }
    }, [flux_toggle, flux_trigger_strat, props.onButtonToggle])

    const exportToExcel = useCallback(async () => {
        // let originalRows = getTableRowsFromData(props.collections, props.originalData, props.xpath);
        const widgetType = props.widgetType === 'repeatedRoot' ? props.widgetType : 'root';
        const url = props.url ? props.url : API_ROOT_URL;
        const res = await axios.get(`${url}/get-all-${props.name}`);
        const storedData = widgetType === 'root' && res.data.length > 0 ? res.data[0] : res.data;
        let originalRows = getTableRowsFromData(props.collections, storedData, props.xpath);
        originalRows.forEach(row => {;
            Object.entries(row).forEach(([k, v]) => {
                if (v !== null && typeof v === DataTypes.OBJECT) {
                    row[k] = JSON.stringify(v)
                }
            })
            delete row['data-id'];
        })
        const ws = utils.json_to_sheet(originalRows);
        const wb = utils.book_new();
        utils.book_append_sheet(wb, ws, "Sheet1");
        writeFileXLSX(wb, `${props.name}.xlsx`);
    }, [props.collections, props.name, props.xpath])

    const copyColumnHandler = useCallback((cell) => {
        let sourceIndex = cell.sourceIndex;
        const xpath = cell.tableTitle;
        if (sourceIndex === null || sourceIndex === undefined) {
            sourceIndex = 0;
        }
        let columnName = xpath.split('.').pop();
        let values = [columnName];
        rows.map(r => {
            const row = r[sourceIndex];
            values.push(row[xpath]);
        })
        const text = values.join('\n');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text);
        } else {
            setClipboardText(text);
        }
        setToastMessage("column copied to clipboard: " + columnName);
    }, [rows])

    const onCloseToastMessage = useCallback(() => {
        setClipboardText(null);
        setToastMessage(null);
    }, [])

    const onColumnOrderChange = (value, xpath) => {
        let columnOrders = cloneDeep(props.columnOrders);
        if (columnOrders) {
            const columnOrder = columnOrders.find(column => column.column_name === xpath);
            if (columnOrder) {
                columnOrder.sequence = value;
            } else {
                columnOrders.push({ column_name: xpath, sequence: value });
            }
        } else {
            columnOrders = [{ column_name: xpath, sequence: value }]
        }
        props.onColumnOrdersChange(columnOrders);
    }

    const onVisibilityMenuOpen = (e) => {
        setOpenVisibilityMenu(true);
        setVisibilityMenuAnchorEl(e.currentTarget);
    }

    const onVisibilityMenuClose = () => {
        setOpenVisibilityMenu(false);
        setVisibilityMenuAnchorEl(null);
    }

    const visibilityMenuClickHandler = (checked) => {
        if (visibilityMenuClickTimeout.current !== null) {
            // double click event
            clearTimeout(visibilityMenuClickTimeout.current);
            visibilityMenuClickTimeout.current = null;
        } else {
            // single click event
            const timeout = setTimeout(() => {
                if (visibilityMenuClickTimeout.current !== null) {
                    if (checked) {
                        setHide(true);
                        setShowMore(false);
                    } else {
                        setShowMore(true);
                    }
                    clearTimeout(visibilityMenuClickTimeout.current)
                    visibilityMenuClickTimeout.current = null;
                }
            }, 300);
            visibilityMenuClickTimeout.current = timeout;
        }
    }

    const visibilityMenuDoubleClickHandler = (checked) => {
        if (checked) {
            setHide(true);
            setShowMore(false);
        } else {
            setHide(false);
        }
    }

    const maxSequence = Math.max(...headCells.map(cell => cell.sequenceNumber));

    const visibiltyColor = showMore ? 'info' : !hide ? 'success' : 'inherit';
    const visibilityMenu = (
        <>
            <Icon
                className={classes.icon}
                name='Visibility'
                title='Visibility'
                onClick={() => visibilityMenuClickHandler(showMore || !hide)}
                onDoubleClick={() => visibilityMenuDoubleClickHandler(showMore || !hide)}>
                <Visibility fontSize='small' color={visibiltyColor} />
            </Icon>
            <Popover
                id={`${props.name}_visibility_menu`}
                open={openVisibilityMenu}
                anchorEl={visibilityMenuArchorEl}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                onClose={onVisibilityMenuClose}>
                <MenuItem dense={true}>
                    <FormControlLabel size='small'
                        label='Show hidden fields'
                        control={
                            <Checkbox
                                size='small'
                                checked={!hide}
                                onChange={() => setHide(!hide)}
                            />
                        }
                    />
                </MenuItem>
                <MenuItem dense={true}>
                    <FormControlLabel size='small'
                        label='Show More'
                        control={
                            <Checkbox
                                size='small'
                                checked={showMore}
                                onChange={() => setShowMore(!showMore)}
                            />
                        }
                    />
                </MenuItem>
            </Popover>
        </>
    )

    let menu = (
        <Fragment>
            {props.headerProps.menu}
            {visibilityMenu}
            {/* {hide ? (
                <Icon className={classes.icon} name="Show" title='Show hidden fields' onClick={() => setHide(false)}><Visibility fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} name="Hide" title='Hide hidden fields' onClick={() => setHide(true)}><VisibilityOff fontSize='small' /></Icon>
            )} */}
            <Icon className={classes.icon} name="Settings" title="Settings" onClick={onSettingsOpen}><Settings fontSize='small' /></Icon>
            <Icon className={classes.icon} name="Export" title="Export" onClick={exportToExcel}><FileDownload fontSize='small' /></Icon>
            <Popover
                id={`${props.name}_table_settings`}
                open={openSettings}
                anchorEl={settingsArchorEl}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                onClose={onSettingsClose}>
                <MenuItem dense={true}>
                    <FormControlLabel
                        sx={{ display: 'flex', flex: 1 }}
                        size='small'
                        control={
                            <ValueBasedToggleButton
                                name='HideShowAll'
                                size='small'
                                selected={showAll}
                                value={showAll}
                                caption={showAll ? 'Show Default' : 'Show All'}
                                xpath='HideShowAll'
                                color={showAll ? 'debug' : 'success'}
                                onClick={showAllHandler}
                            />
                        }
                    />
                    <ValueBasedToggleButton
                        name='MoreLessAll'
                        size='small'
                        selected={moreAll}
                        value={moreAll}
                        caption={moreAll ? 'More Default' : 'More All'}
                        xpath='MoreLessAll'
                        color={moreAll ? 'debug' : 'info'}
                        onClick={moreAllHandler}
                    />
                </MenuItem>
                {headCells.map((cell, index) => {
                    if (cell.sourceIndex !== 0) return;
                    let sequence = cell.sequenceNumber;
                    if (props.columnOrders) {
                        const columnOrder = props.columnOrders.find(column => column.column_name === cell.tableTitle);
                        if (columnOrder) {
                            sequence = columnOrder.sequence;
                        }
                    }
                    const show = !cell.hide;
                    const showCaption = cell.hide ? 'Show' : 'Hide';
                    const showColor = show ? 'success' : 'debug';
                    const more = !cell.showLess;
                    const moreDisabled = cell.hide;
                    const moreCaption = more ? 'Less' : 'More';
                    const moreColor = more ? 'info' : 'debug';
                    return (
                        <MenuItem key={index} dense={true}>
                            <FormControlLabel
                                sx={{ display: 'flex', flex: 1 }}
                                size='small'
                                label={cell.elaborateTitle ? cell.tableTitle : cell.key}
                                control={
                                    <ValueBasedToggleButton
                                        name={cell.tableTitle}
                                        size='small'
                                        selected={show}
                                        disabled={false}
                                        value={show}
                                        caption={showCaption}
                                        xpath={cell.tableTitle}
                                        color={showColor}
                                        onClick={onSettingsItemChange}
                                    />
                                    // <Checkbox
                                    //     size='small'
                                    //     checked={cell.hide ? false : true}
                                    //     onChange={(e) => onSettingsItemChange(e, cell.tableTitle)}
                                    // />
                                }
                            />
                            <Select
                                size='small'
                                value={sequence}
                                onChange={(e) => onColumnOrderChange(e.target.value, cell.tableTitle)}>
                                {[...Array(maxSequence).keys()].map((v, index) => (
                                    <MenuItem key={index} value={index + 1}>{index + 1}</MenuItem>
                                ))}
                            </Select>
                            <ValueBasedToggleButton
                                name={cell.tableTitle}
                                size='small'
                                selected={more}
                                disabled={moreDisabled}
                                value={more}
                                caption={moreCaption}
                                xpath={cell.tableTitle}
                                color={moreColor}
                                onClick={onShowLessChange}
                            />
                            <Box sx={{ minWidth: '30px' }}>
                                {cell.help &&
                                    <Icon title={cell.help}>
                                        <Help />
                                    </Icon>
                                }
                            </Box>
                        </MenuItem>
                    )
                })}
            </Popover>
        </Fragment>
    )

    let modalCloseMenu = <Icon className={classes.icon} title="Close" onClick={onClose} ><Close fontSize='small' /></Icon>
    let modalId = props.name + '_modal';
    if (props.xpath) {
        modalId = props.name + '_' + props.xpath + '_modal';
    }

    return (
        <WidgetContainer
            name={props.headerProps.name}
            title={props.headerProps.title}
            mode={props.widgetType === 'repeatedRoot' ? selectedRows.length === 1 ? props.headerProps.mode : null : props.headerProps.mode}
            layout={props.headerProps.layout}
            menu={menu}
            onChangeMode={props.headerProps.onChangeMode}
            onChangeLayout={props.headerProps.onChangeLayout}
            onReload={props.headerProps.onReload}
            onSave={props.headerProps.onSave}
            commonkeys={commonkeys}
            truncateDateTime={props.truncateDateTime}
            supportedLayouts={props.headerProps.supportedLayouts}
            scrollLock={props.scrollLock}>

            {getFilteredCells().length > 0 && rows.length > 0 &&
                <Fragment>
                    <TableContainer className={classes.container}>
                        <Table
                            className={classes.table}
                            size='medium'>
                            <TableHead
                                headCells={getFilteredCells()}
                                mode={props.mode}
                                sortOrders={sortOrders}
                                onRequestSort={handleRequestSort}
                                onRemoveSort={handleRemoveSort}
                                copyColumnHandler={copyColumnHandler}
                            />
                            <TableBody>
                                {getActiveRows(rows, page, rowsPerPage, sortOrders, true)
                                    .map((row, index) => {
                                        let cells = getFilteredCells();
                                        // let selected = selectedRows.filter(id => id === row[0]['data-id']).length > 0;
                                        let rowKey = row[0]['data-id'];
                                        if (Number.isInteger(rowKey)) {
                                            rowKey = index;
                                        }

                                        return (
                                            <Row
                                                key={rowKey}
                                                // className={tableRowClass}
                                                cells={cells}
                                                collections={props.collections}
                                                data={props.data}
                                                onAutocompleteOptionChange={onAutocompleteOptionChange}
                                                onButtonClick={onButtonClick}
                                                onCheckboxChange={onCheckboxChange}
                                                onDateTimeChange={onDateTimeChange}
                                                onRowClick={onRowClick}
                                                onRowDoubleClick={onRowDoubleClick}
                                                onRowSelect={onRowSelect}
                                                onSelectItemChange={onSelectItemChange}
                                                onTextChange={onTextChange}
                                                onUpdate={onUpdate}
                                                originalData={props.originalData}
                                                row={row}
                                                selectedRows={selectedRows}
                                                // selected={selected}
                                                mode={props.mode}
                                                onFormUpdate={props.onFormUpdate}
                                                index={props.index}
                                                forceUpdate={props.forceUpdate}
                                                truncateDateTime={props.truncateDateTime}
                                                widgetType={props.widgetType}
                                                onForceSave={props.onForceSave}
                                                // rowId={props.widgetType === 'root' ? props.index : row[0]['data-id']}
                                                dataSourceColors={props.dataSourceColors}
                                            />
                                        )
                                    })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    {rows.length > 6 &&
                        <TablePagination
                            rowsPerPageOptions={[25, 50]}
                            component="div"
                            count={rows.length}
                            rowsPerPage={rowsPerPage}
                            page={page}
                            onPageChange={handleChangePage}
                            onRowsPerPageChange={handleChangeRowsPerPage}
                        />
                    }
                </Fragment>
            }

            <FullScreenModal
                id={modalId}
                open={open}
                onClose={onClose}
                onSave={onSave}
                popup={openModalPopup}
                onConfirmClose={onConfirmClose}>
                <TreeWidget
                    headerProps={{
                        title: props.headerProps.title,
                        mode: props.headerProps.mode,
                        menuRight: modalCloseMenu,
                        onSave: onSave
                    }}
                    name={props.name}
                    schema={props.schema}
                    data={props.widgetType === 'repeatedRoot' ? selectedRow !== null ? data[selectedRow] : {} : data}
                    originalData={props.widgetType === 'repeatedRoot' ? selectedRow !== null ? props.originalData[selectedRow] : {} : props.originalData}
                    mode={props.mode}
                    onUpdate={onUpdate}
                    xpath={props.xpath}
                    subtree={props.widgetType === 'repeatedRoot' ? null : rowTrees[selectedRow]}
                    onUserChange={onUserChange}
                    scrollLock={false}
                />
                <Dialog
                    open={openModalPopup}
                    onClose={onConfirmClose}>
                    <DialogTitle>Save Changes</DialogTitle>
                    <DialogContent>
                        <DialogContentText>Do you want to save changes?</DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button variant='contained' color='error' onClick={onConfirmClose} autoFocus>Discard</Button>
                        <Button variant='contained' color='success' onClick={onSave} autoFocus>Save</Button>
                    </DialogActions>
                </Dialog>
            </FullScreenModal>
            {toastMessage && (
                <Snackbar open={toastMessage !== null} autoHideDuration={2000} onClose={onCloseToastMessage}>
                    <Alert onClose={onCloseToastMessage} severity="success">{toastMessage}</Alert>
                </Snackbar>
            )}

            {props.error && <AlertErrorMessage open={props.error ? true : false} onClose={props.onResetError} severity='error' error={props.error} />}
            <CopyToClipboard text={clipboardText} copy={clipboardText !== null} />
        </WidgetContainer>
    )
}

export default memo(TableWidget);