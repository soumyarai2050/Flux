import React, { useState, useEffect, useCallback, Fragment, memo } from 'react';
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
    const [sortOrders, setSortOrders] = useState(SortOrderCache.getSortOrder(props.name));
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [selectAll, setSelectAll] = useState(false);
    const [toastMessage, setToastMessage] = useState(null);
    const [clipboardText, setClipboardText] = useState(null);
    const [userChanges, setUserChanges] = useState({});

    useEffect(() => {
        setData(props.data);
        setRows(props.rows);
        setHeadCells(props.tableColumns);
        setCommonkeys(props.commonKeyCollections);
    }, [props.data, props.rows]);

    useEffect(() => {
        let trees = generateRowTrees(cloneDeep(data), props.collections, props.xpath);
        setRowTrees(trees);
    }, [props.collections, data, props.xpath])

    useEffect(() => {
        let commonKeyCollections = getCommonKeyCollections(rows, headCells, hide, false, props.widgetType === 'repeatedRoot' ? true : false);
        setCommonkeys(commonKeyCollections);
    }, [rows, headCells, props.mode, hide])

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
        if (hide) {
            updatedCells = updatedCells.filter(cell => !cell.hide);
        }
        updatedCells = updatedCells.filter(cell => {
            if (commonkeys.filter(commonkey => commonkey.key === cell.key && commonkey.tableTitle === cell.tableTitle).length > 0 && props.mode !== Modes.EDIT_MODE) {
                return false;
            }
            return true;
        })
        updatedCells = sortColumns(updatedCells, props.columnOrders);
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

    const onSelectAll = (e) => {
        let updatedHeadCells = cloneDeep(headCells);
        if (e.target.checked) {
            updatedHeadCells = updatedHeadCells.map(cell => {
                cell.hide = false;
                return cell;
            })
        } else {
            updatedHeadCells = updatedHeadCells.map(cell => {
                cell.hide = true;
                return cell;
            })
        }
        setSelectAll(e.target.checked);
        setHeadCells(updatedHeadCells);
    }

    const handleRequestSort = (event, property, retainSortLevel = false) => {
        let updatedSortOrders = cloneDeep(sortOrders);
        if (!retainSortLevel) {
            updatedSortOrders = updatedSortOrders.filter(o => o.orderBy === property);
        }
        const sortOrder = updatedSortOrders.find(o => o.orderBy === property);
        if (sortOrder) {
            // sort level already exists for this property
            sortOrder.sortType = sortOrder.sortType === 'asc' ? 'desc' : 'asc';
        } else {
            // add a new sort level
            updatedSortOrders.push({ orderBy: property, sortType: 'asc' });
        }
        setSortOrders(updatedSortOrders);
        SortOrderCache.setSortOrder(props.name, updatedSortOrders);
        setPage(0);
        PageCache.setPage(props.name, 0);
    }

    const handleRemoveSort = (property) => {
        const updatedSortOrders = sortOrders.filter(o => o.orderBy !== property);
        setSortOrders(updatedSortOrders);
        SortOrderCache.setSortOrder(props.name, updatedSortOrders);
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
        if (props.mode !== Modes.EDIT_MODE) {
            let updatedSelectedRows;
            if (e.ctrlKey) {
                if (selectedRows.find(row => row === rowId)) {
                    // rowId already selected. unselect the row
                    updatedSelectedRows = selectedRows.filter(row => row !== rowId);
                } else {
                    // new selected row. add it to selected array
                    updatedSelectedRows = [...selectedRows, rowId];
                }
            } else {
                updatedSelectedRows = [rowId];
            }
            setSelectedRows(updatedSelectedRows);
            if (props.widgetType === 'repeatedRoot') {
                if (updatedSelectedRows.length === 1) {
                    props.onSelectRow(rowId);
                } else {
                    props.onSelectRow(null);
                }
            }
        }
    }

    const onRowDisselect = (e, rowId) => {
        if (props.mode !== Modes.EDIT_MODE) {
            const updatedSelectedRows = selectedRows.filter(row => row !== rowId);
            setSelectedRows(updatedSelectedRows);
            if (props.widgetType === 'repeatedRoot') {
                if (updatedSelectedRows.length === 1) {
                    props.onSelectRow(updatedSelectedRows[0]);
                } else {
                    props.onSelectRow(null);
                }
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
                console.log(idx);
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

    const onSettingsItemChange = (e, key) => {
        let hide = !e.target.checked;
        if (hide) {
            setSelectAll(false);
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

    const onSettingsOpen = (e) => {
        setOpenSettings(true);
        setSettingsArcholEl(e.currentTarget);
    }

    const onSettingsClose = (e) => {
        setOpenSettings(false);
        setSettingsArcholEl(null);
    }

    const onTextChange = useCallback((e, type, xpath, value, dataxpath, validationRes) => {
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
        props.onUserChange(xpath, value);
        if (props.onFormUpdate) {
            props.onFormUpdate(xpath, validationRes);
        }
    }, [data, props.onUpdate, props.onUserChange])

    const onSelectItemChange = useCallback((e, dataxpath, xpath) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.value);
    }, [data, props.onUpdate, props.onUserChange])

    const onCheckboxChange = useCallback((e, dataxpath, xpath) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.checked);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.checked);
    }, [data, props.onUpdate, props.onUserChange])

    const onAutocompleteOptionChange = useCallback((e, value, dataxpath, xpath) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }, [data, props.onUpdate, props.onUserChange])

    const onDateTimeChange = useCallback((dataxpath, xpath, value) => {
        let updatedData;
        if (props.widgetType === 'repeatedRoot') {
            updatedData = cloneDeep(data.find(obj => obj[DB_ID] === selectedRows[0]));
        } else {
            updatedData = cloneDeep(data);
        }
        // let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }, [data, props.onUpdate, props.onUserChange])

    const onButtonClick = useCallback((e, action, xpath, value) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData);
        } else if (action === 'flux_trigger_strat') {
            let updatedData = flux_trigger_strat(value);
            if (updatedData) {
                props.onButtonToggle(e, xpath, updatedData);
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
        originalRows.forEach(row => {
            delete row['data-id'];
        })
        const ws = utils.json_to_sheet(originalRows);
        const wb = utils.book_new();
        utils.book_append_sheet(wb, ws, "Sheet1");
        writeFileXLSX(wb, `${props.name}.xlsx`);
    }, [props.collections, props.name, props.xpath])

    const copyColumnHandler = useCallback((xpath) => {
        let columnName = xpath.split('.').pop();
        let values = [columnName];
        rows.map(row => {
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

    const maxSequence = Math.max(...headCells.map(cell => cell.sequenceNumber));

    let menu = (
        <Fragment>
            {props.headerProps.menu}
            {hide ? (
                <Icon className={classes.icon} name="Show" title='Show hidden fields' onClick={() => setHide(false)}><Visibility fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} name="Hide" title='Hide hidden fields' onClick={() => setHide(true)}><VisibilityOff fontSize='small' /></Icon>
            )}
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
                        label='Select All / Unselect All'
                        control={
                            <Checkbox
                                size='small'
                                checked={selectAll}
                                onChange={onSelectAll}
                            />
                        }
                    />
                    <Icon title='show/hide all fields'>
                        <Help />
                    </Icon>
                </MenuItem>
                {headCells.map((cell, index) => {
                    let sequence = cell.sequenceNumber;
                    if (props.columnOrders) {
                        const columnOrder = props.columnOrders.find(column => column.column_name === cell.tableTitle);
                        if (columnOrder) {
                            sequence = columnOrder.sequence;
                        }
                    }
                    return (
                        <MenuItem key={index} dense={true}>
                            <FormControlLabel
                                sx={{ display: 'flex', flex: 1 }}
                                size='small'
                                label={cell.elaborateTitle ? cell.tableTitle : cell.key}
                                control={
                                    <Checkbox
                                        size='small'
                                        checked={cell.hide ? false : true}
                                        onChange={(e) => onSettingsItemChange(e, cell.tableTitle)}
                                    />
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
                                {getActiveRows(rows, page, rowsPerPage, sortOrders)
                                    .map((row, index) => {
                                        let tableRowClass = '';
                                        if (row['data-add']) {
                                            tableRowClass = classes.add;
                                        } else if (row['data-remove']) {
                                            tableRowClass = classes.remove;
                                        }

                                        let cells = getFilteredCells();
                                        let selected = selectedRows.filter(id => id === row['data-id']).length > 0;
                                        let rowKey = row['data-id'];
                                        if (Number.isInteger(rowKey)) {
                                            rowKey = index;
                                        }

                                        return (
                                            <Row
                                                key={rowKey}
                                                className={tableRowClass}
                                                cells={cells}
                                                collections={props.collections}
                                                data={props.data}
                                                onAutocompleteOptionChange={onAutocompleteOptionChange}
                                                onButtonClick={onButtonClick}
                                                onCheckboxChange={onCheckboxChange}
                                                onDateTimeChange={onDateTimeChange}
                                                onRowClick={onRowClick}
                                                onRowDisselect={onRowDisselect}
                                                onRowSelect={onRowSelect}
                                                onSelectItemChange={onSelectItemChange}
                                                onTextChange={onTextChange}
                                                onUpdate={onUpdate}
                                                originalData={props.originalData}
                                                row={row}
                                                selected={selected}
                                                mode={props.mode}
                                                onFormUpdate={props.onFormUpdate}
                                                index={props.index}
                                                forceUpdate={props.forceUpdate}
                                                truncateDateTime={props.truncateDateTime}
                                                widgetType={props.widgetType}
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