import React, { useState, useEffect, useCallback, Fragment, memo } from 'react';
import _, { cloneDeep, isEqual } from 'lodash';
import { makeStyles } from '@mui/styles';
import {
    TableContainer, Table, TableBody, TableRow, TableCell, DialogTitle, DialogContent, DialogContentText,
    DialogActions, Button, Select, MenuItem, Checkbox, FormControlLabel, Dialog, TablePagination
} from '@mui/material';
import { generateRowTrees, generateRowsFromTree, addxpath, clearxpath, getTableRows, getTableColumns, getCommonKeyCollections } from '../utils';
import { Settings, Close, Visibility, VisibilityOff } from '@mui/icons-material';
import { DataTypes, DB_ID, Modes } from '../constants';
import TreeWidget from './TreeWidget';
import WidgetContainer from './WidgetContainer';
import TableHead from './TableHead';
import FullScreenModal from './FullScreenModal';
import Cell from './Cell';
import Icon from './Icon';
import Alert from './Alert';
import AbbreviatedJsonWidget from './AbbreviatedJsonWidget';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';

const useStyles = makeStyles({
    tableContainer: {
        background: 'white'
    },
    table: {
        minWidth: 750
    },
    tableRow: {
        '&:nth-of-type(even)': {
            background: '#eee'
        }
    },
    tableRowAdd: {
        background: '#c6efce !important'
    },
    tableRowRemove: {
        background: '#ffc7ce !important'
    },
    icon: {
        backgroundColor: '#ccc !important',
        marginRight: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    },
    settings: {
        width: 0,
        display: 'inherit',
        '& .MuiSelect-outlined': {
            padding: 0
        },
        '& .css-jedpe8-MuiSelect-select-MuiInputBase-input-MuiOutlinedInput-input': {
            paddingRight: '0px !important'
        }
    },
    nodeContainerHighlighted: {
        background: 'orange'
    }
})

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
    const [abbreviatedJson, setAbbreviatedJson] = useState({});
    const [showAbbreviatedJson, setShowAbbreviatedJson] = useState(false);
    const [hide, setHide] = useState(true);

    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [page, setPage] = useState(0);
    const [order, setOrder] = React.useState('asc');
    const [orderBy, setOrderBy] = React.useState('');
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const classes = useStyles();

    useEffect(() => {
        setData(props.data);
        setRows(props.rows);
        setHeadCells(props.tableColumns);
        setCommonkeys(props.commonKeyCollections);
    }, [props.data]);

    useEffect(() => {
        let trees = generateRowTrees(cloneDeep(data), props.collections, props.xpath);
        // let tableRows = getTableRows(props.collections, props.originalData, data, props.xpath);
        setRowTrees(trees);
        // setRows(tableRows);
    }, [props.collections, data, props.xpath])

    // useEffect(() => {
    //     let tableColumns = getTableColumns(props.collections);
    //     setHeadCells(tableColumns);
    // }, [props.collections, props.mode, hide])

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

    function getComparator(order, orderBy) {
        return order === 'desc'
            ? (a, b) => descendingComparator(a, b, orderBy)
            : (a, b) => -descendingComparator(a, b, orderBy);
    }

    function descendingComparator(a, b, orderBy) {
        if (b[orderBy] < a[orderBy]) {
            return -1;
        }
        if (b[orderBy] > a[orderBy]) {
            return 1;
        }
        return 0;
    }

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    // This method is created for cross-browser compatibility, if you don't
    // need to support IE11, you can use Array.prototype.sort() directly
    function stableSort(array, comparator) {
        const stabilizedThis = array.map((el, index) => [el, index]);
        stabilizedThis.sort((a, b) => {
            const order = comparator(a[0], b[0]);
            if (order !== 0) {
                return order;
            }
            return a[1] - b[1];
        });
        return stabilizedThis.map((el) => el[0]);
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
                    el.classList.add(classes.nodeContainerHighlighted)
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
        let updatedHeadCells = headCells.map((cell) => cell.key === key ? { ...cell, hide: !e.target.checked } : cell)
        setHeadCells(updatedHeadCells);
    }

    const onAbbreviatedFieldOpen = (jsonData) => {
        setAbbreviatedJson(clearxpath(cloneDeep(jsonData)));
        setShowAbbreviatedJson(true);
    }

    const onAbbreviatedFieldClose = () => {
        setShowAbbreviatedJson(false);
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

    let menu = (
        <Fragment>
            {props.headerProps.menu}
            {hide ? (
                <Icon className={classes.icon} name="Show" title='Show hidden fields' onClick={() => setHide(false)}><Visibility fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} name="Hide" title='Hide hidden fields' onClick={() => setHide(true)}><VisibilityOff fontSize='small' /></Icon>
            )}
            <Icon className={classes.icon} name="Settings" title="Settings" onClick={onSettingsOpen}><Settings fontSize='small' /></Icon>
            <Select
                className={classes.settings}
                open={showSettings}
                onOpen={onSettingsOpen}
                onClose={onSettingsClose}
                value=''
                onChange={() => { }}
                size='small'>
                {headCells.map((cell, index) => {
                    return (
                        <MenuItem key={index} dense={true}>
                            <FormControlLabel size='small'
                                label={cell.title}
                                control={
                                    <Checkbox
                                        size='small'
                                        checked={cell.hide ? false : true}
                                        onChange={(e) => onSettingsItemChange(e, cell.key)}
                                    />
                                }
                            />
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
                    <TableContainer className={classes.tableContainer}>
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
                                        tableRowClass = classes.tableRowAdd;
                                    } else if (row['data-remove']) {
                                        tableRowClass = classes.tableRowRemove;
                                    }

                                    return (
                                        <TableRow
                                            key={index}
                                            className={`${classes.tableRow} ${tableRowClass}`}
                                            hover
                                            selected={selectedRows.filter(id => id === row['data-id']).length > 0}
                                            onDoubleClick={(e) => onRowDisselect(e, row['data-id'])}
                                            onClick={(e) => onRowSelect(e, row['data-id'])}>

                                            {/* {props.mode === Modes.EDIT_MODE &&
                                            <TableCell align='center' size='small'>
                                                <Icon title="Expand" onClick={(e) => onRowClick(e, index)}><MoreHoriz /></Icon>
                                            </TableCell>
                                        } */}

                                            {getFilteredCells().map((cell, i) => {
                                                // don't show cells that are hidden
                                                if (cell.hide) return;
                                                return (
                                                    <Cell
                                                        key={i}
                                                        row={row}
                                                        rowindex={row['data-id']}
                                                        propname={cell.key}
                                                        proptitle={cell.tableTitle}
                                                        mode={props.mode}
                                                        data={props.data}
                                                        originalData={props.originalData}
                                                        collections={props.collections}
                                                        onUpdate={props.onUpdate}
                                                        onAbbreviatedFieldOpen={onAbbreviatedFieldOpen}
                                                        onDoubleClick={onRowClick}
                                                        // onButtonToggle={onButtonToggle}
                                                        onButtonClick={onButtonClick}
                                                        onCheckboxChange={onCheckboxChange}
                                                        onTextChange={onTextChange}
                                                        onSelectItemChange={onSelectItemChange}
                                                        onAutocompleteOptionChange={onAutocompleteOptionChange}
                                                    // onUserChange={props.onUserChange}
                                                    />
                                                )
                                            })}
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                    <TablePagination
                        rowsPerPageOptions={[25, 50]}
                        component="div"
                        count={rows.length}
                        rowsPerPage={rowsPerPage}
                        page={page}
                        onPageChange={handleChangePage}
                        onRowsPerPageChange={handleChangeRowsPerPage}
                    />
                </Fragment>
            }

            <AbbreviatedJsonWidget open={showAbbreviatedJson} onClose={onAbbreviatedFieldClose} json={abbreviatedJson} />

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

            {props.error && <Alert open={props.error ? true : false} onClose={props.onResetError} severity='error'>{props.error}</Alert>}
        </WidgetContainer>
    )
}

export default memo(TableWidget);