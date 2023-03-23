import React, { useState, useEffect, useCallback, Fragment, memo } from 'react';
import _, { cloneDeep } from 'lodash';
import {
    TableContainer, Table, TableBody, DialogTitle, DialogContent, DialogContentText,
    DialogActions, Button, Select, MenuItem, Checkbox, FormControlLabel, Dialog, TablePagination
} from '@mui/material';
import { Settings, Close, Visibility, VisibilityOff, FileDownload, LiveHelp } from '@mui/icons-material';
import { utils, writeFileXLSX } from 'xlsx';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { generateRowTrees, generateRowsFromTree, getCommonKeyCollections, stableSort, getComparator, getTableRowsFromData } from '../utils';
import { DataTypes, DB_ID, Modes } from '../constants';
import TreeWidget from './TreeWidget';
import WidgetContainer from './WidgetContainer';
import TableHead from './TableHead';
import FullScreenModal from './Modal';
import Row from './Row';
import { Icon } from './Icon';
import { AlertErrorMessage } from './Alert';
import classes from './TableWidget.module.css';


const TableWidget = (props) => {

    const [rowTrees, setRowTrees] = useState([]);
    const [rows, setRows] = useState([]);
    const [headCells, setHeadCells] = useState([]);
    const [commonkeys, setCommonkeys] = useState([]);
    const [selectedRow, setSelectedRow] = useState();
    const [selectedRows, setSelectedRows] = useState([]);
    const [data, setData] = useState(props.data);
    const [open, setOpen] = useState(false); // for full height modal
    const [showSettings, setShowSettings] = useState(false);
    const [hide, setHide] = useState(true);

    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [page, setPage] = useState(0);
    const [order, setOrder] = React.useState('asc');
    const [orderBy, setOrderBy] = React.useState('');
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [selectAll, setSelectAll] = useState(false);

    useEffect(() => {
        setData(props.data);
        setRows(props.rows);
        setHeadCells(props.tableColumns);
        setCommonkeys(props.commonKeyCollections);
    }, [props.data]);

    useEffect(() => {
        let trees = generateRowTrees(cloneDeep(data), props.collections, props.xpath);
        setRowTrees(trees);
    }, [props.collections, data, props.xpath])

    useEffect(() => {
        let commonKeyCollections = getCommonKeyCollections(rows, headCells, hide)
        setCommonkeys(commonKeyCollections);
    }, [rows, headCells, props.mode, hide])

    function getFilteredCells() {
        let updatedCells = headCells;
        if (hide) {
            updatedCells = updatedCells.filter(cell => !cell.hide);
        }
        updatedCells = updatedCells.filter(cell => {
            if (commonkeys.filter(commonkey => commonkey.key === cell.key).length > 0 && props.mode !== Modes.EDIT_MODE) {
                return false;
            }
            return true;
        })
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
        if (!e.target.checked) {
            setSelectAll(false);
        }
        let updatedHeadCells = headCells.map((cell) => cell.tableTitle === key ? { ...cell, hide: !e.target.checked } : cell)
        setHeadCells(updatedHeadCells);
    }

    const onSettingsOpen = () => {
        setShowSettings(true);
    }

    const onSettingsClose = () => {
        setShowSettings(false);
    }

    const onTextChange = useCallback((e, type, xpath, value) => {
        if (type === DataTypes.NUMBER) {
            value = value * 1;
        }
        let dataxpath = e.target.getAttribute('dataxpath');
        let updatedData = cloneDeep(data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
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
            <Select
                className={classes.dropdown}
                open={showSettings}
                onOpen={onSettingsOpen}
                onClose={onSettingsClose}
                value=''
                onChange={() => { }}
                size='small'>
                <MenuItem dense={true}>
                    <FormControlLabel size='small'
                        label='Select All'
                        control={
                            <Checkbox
                                size='small'
                                checked={selectAll}
                                onChange={onSelectAll}
                            />
                        }
                    />
                </MenuItem>
                {headCells.map((cell, index) => {
                    return (
                        <MenuItem key={index} dense={true}>
                            <FormControlLabel size='small'
                                label={cell.elaborateTitle ? cell.tableTitle : cell.key}
                                control={
                                    <Checkbox
                                        size='small'
                                        checked={cell.hide ? false : true}
                                        onChange={(e) => onSettingsItemChange(e, cell.tableTitle)}
                                    />
                                }
                            />
                            {cell.help &&
                                <Icon title={cell.help}>
                                    <LiveHelp color='primary' />
                                </Icon>
                            }
                        </MenuItem>
                    )
                })}
            </Select>
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
            commonkeys={commonkeys}>

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
                            />
                            <TableBody>
                                {stableSort(rows, getComparator(order, orderBy))
                                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                                    .map((row, index) => {
                                        // for respecting sequenceNumber provided in the schema.
                                        // sorts the row keys based on sequenceNumber
                                        if (props.collections.length > 0) {
                                            row = Object.keys(row).sort(function (a, b) {
                                                if (a.startsWith('xpath_') && b.startsWith('xpath_')) return 0;
                                                else if (a.startsWith('xpath_') || a.startsWith(DB_ID)) return -1;
                                                else if (b.startsWith('xpath_') || b.startsWith(DB_ID)) return 1;
                                                else {
                                                    let colA = props.collections.filter(col => col.key === a)[0];
                                                    let colB = props.collections.filter(col => col.key === b)[0];
                                                    if (!colA || !colB) return 0;
                                                    if (colA.sequenceNumber < colB.sequenceNumber) return -1;
                                                    else return 1;
                                                }
                                            }).reduce(function (obj, key) {
                                                obj[key] = row[key];
                                                return obj;
                                            }, {})
                                        }

                                        let tableRowClass = '';
                                        if (row['data-add']) {
                                            tableRowClass = classes.add;
                                        } else if (row['data-remove']) {
                                            tableRowClass = classes.remove;
                                        }

                                        let cells = getFilteredCells();
                                        let selected = selectedRows.filter(id => id === row['data-id']).length > 0;

                                        return (
                                            <Row
                                                key={index}
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

            {props.error && <AlertErrorMessage open={props.error ? true : false} onClose={props.onResetError} severity='error' error={props.error} />}
        </WidgetContainer>
    )
}

export default memo(TableWidget);