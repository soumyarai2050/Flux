import React, { useState, useEffect, useCallback, Fragment, memo } from 'react';
import _, { cloneDeep } from 'lodash';
import {
    TableContainer, Table, TableBody, DialogTitle, DialogContent, DialogContentText,
    DialogActions, Button, Select, MenuItem, Checkbox, FormControlLabel, Dialog, TablePagination,
    Snackbar, Alert, TextField, Popover, Box
} from '@mui/material';
import { Settings, Close, Visibility, VisibilityOff, FileDownload, LiveHelp } from '@mui/icons-material';
import { utils, writeFileXLSX } from 'xlsx';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { generateRowTrees, generateRowsFromTree, getCommonKeyCollections, stableSort, getComparator, getTableRowsFromData, sortColumns } from '../utils';
import { DataTypes, DB_ID, Modes } from '../constants';
import TreeWidget from './TreeWidget';
import WidgetContainer from './WidgetContainer';
import TableHead from './TableHead';
import FullScreenModal from './Modal';
import Row from './Row';
import { Icon } from './Icon';
import { AlertErrorMessage } from './Alert';
import classes from './TableWidget.module.css';
import CopyToClipboard from './CopyToClipboard';

const TableWidget = (props) => {
    const [rowTrees, setRowTrees] = useState([]);
    const [rows, setRows] = useState(props.rows);
    const [headCells, setHeadCells] = useState(props.tableColumns);
    const [commonkeys, setCommonkeys] = useState(props.commonKeyCollections);
    const [selectedRow, setSelectedRow] = useState();
    const [selectedRows, setSelectedRows] = useState([]);
    const [data, setData] = useState(props.data);
    const [open, setOpen] = useState(false); // for full height modal
    const [openSettings, setOpenSettings] = useState(false);
    const [settingsArchorEl, setSettingsArcholEl] = useState();
    const [hide, setHide] = useState(true);
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [page, setPage] = useState(0);
    const [order, setOrder] = React.useState('asc');
    const [orderBy, setOrderBy] = React.useState('');
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [selectAll, setSelectAll] = useState(false);
    const [toastMessage, setToastMessage] = useState(null);
    const [clipboardText, setClipboardText] = useState(null);

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
        let commonKeyCollections = getCommonKeyCollections(rows, headCells, hide)
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
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
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

    const handleRequestSort = (event, property) => {
        const isAsc = orderBy === property && order === 'asc';
        setOrder(isAsc ? 'desc' : 'asc');
        setOrderBy(property);
        setPage(0);
    };

    const onSave = () => {
        props.onUpdate(data);
        setOpen(false);
        setOpenModalPopup(false);
    }

    const onRowClick = (e, index, xpath) => {
        if (props.mode === Modes.EDIT_MODE) {
            let selectedIndex = 0;
            setOpen(true);
            let updatedRows = generateRowsFromTree(rowTrees, props.collections, props.xpath);
            updatedRows.forEach((row, i) => {
                if (row['data-id'] === index) {
                    selectedIndex = i;
                }
            })
            setSelectedRow(selectedIndex);
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

    const onRowSelect = (e, index) => {
        if (props.mode !== Modes.EDIT_MODE) {
            if (e.ctrlKey) {
                if (selectedRows.filter(row => row === index).length === 0) {
                    setSelectedRows([...selectedRows, index]);
                }
            } else {
                setSelectedRows([index]);
            }
        }
    }

    const onRowDisselect = (e, index) => {
        if (props.mode !== Modes.EDIT_MODE) {
            let updatedData = selectedRows.filter(row => row !== index);
            setSelectedRows(updatedData);
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
        if (type === 'add' || type === 'remove') {
            setOpen(false);
            props.onUpdate(updatedData);
        } else {
            setData(updatedData);
        }
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
        if (value === '') {
            value = null;
        }
        if (type === DataTypes.NUMBER) {
            if (value !== null) {
                value = value * 1;
            }
        }
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
        if (props.onFormUpdate) {
            props.onFormUpdate(xpath, validationRes);
        }
    }, [data, props.onUpdate, props.onUserChange])

    const onSelectItemChange = useCallback((e, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.value);
    }, [data, props.onUpdate, props.onUserChange])

    const onCheckboxChange = useCallback((e, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, e.target.checked);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.checked);
    }, [data, props.onUpdate, props.onUserChange])

    const onAutocompleteOptionChange = useCallback((e, value, dataxpath, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }, [data, props.onUpdate, props.onUserChange])

    const onDateTimeChange = useCallback((dataxpath, xpath, value) => {
        let updatedData = cloneDeep(data);
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

    const exportToExcel = useCallback(() => {
        let originalRows = getTableRowsFromData(props.collections, props.originalData, props.xpath);
        originalRows.forEach(row => {
            delete row['data-id'];
        })
        const ws = utils.json_to_sheet(originalRows);
        const wb = utils.book_new();
        utils.book_append_sheet(wb, ws, "Sheet1");
        writeFileXLSX(wb, `${props.name}.xlsx`);
    }, [props.collections, props.originalData, props.xpath])

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
        props.onColumnOrdersChange(props.name, columnOrders);
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
                        <LiveHelp color='primary' />
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
                                        <LiveHelp color='primary' />
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
            mode={props.headerProps.mode}
            layout={props.headerProps.layout}
            menu={menu}
            onChangeMode={props.headerProps.onChangeMode}
            onChangeLayout={props.headerProps.onChangeLayout}
            onReload={props.headerProps.onReload}
            onSave={props.headerProps.onSave}
            commonkeys={commonkeys}
            truncateDateTime={props.truncateDateTime}
            supportedLayouts={props.headerProps.supportedLayouts}>

            {getFilteredCells().length > 0 && rows.length > 0 &&
                <Fragment>
                    <TableContainer className={classes.container}>
                        <Table
                            className={classes.table}
                            size='medium'>
                            <TableHead
                                headCells={getFilteredCells()}
                                mode={props.mode}
                                order={order}
                                orderBy={orderBy}
                                onRequestSort={handleRequestSort}
                                copyColumnHandler={copyColumnHandler}
                            />
                            <TableBody>
                                {stableSort(rows, getComparator(order, orderBy))
                                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
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
                    data={data}
                    originalData={props.originalData}
                    mode={props.mode}
                    onUpdate={onUpdate}
                    xpath={props.xpath}
                    subtree={rowTrees[selectedRow]}
                    onUserChange={props.onUserChange}
                />
                <Dialog
                    open={openModalPopup}
                    onClose={onConfirmClose}>
                    <DialogTitle>Save Changes</DialogTitle>
                    <DialogContent>
                        <DialogContentText>Do you want to save changes?</DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={onConfirmClose} autoFocus>Discard</Button>
                        <Button onClick={onSave} autoFocus>Save</Button>
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