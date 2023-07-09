import React, { Fragment, useState, useEffect, useMemo } from 'react';
import { Autocomplete, Box, TextField, Button, Divider, Chip, Table, TableContainer, TableBody, TableRow, TableCell, TablePagination, Select, MenuItem, FormControlLabel, Checkbox } from '@mui/material';
import WidgetContainer from './WidgetContainer';
import { Download, Delete, Settings, FileDownload, LiveHelp } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { Icon } from './Icon';
import _, { cloneDeep } from 'lodash';
import { DB_ID, Modes, DataTypes, ColorTypes, Layouts } from '../constants';
import {
    getAlertBubbleColor, getAlertBubbleCount, getIdFromAbbreviatedKey, getAbbreviatedKeyFromId, applyFilter
} from '../utils';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { AlertErrorMessage } from './Alert';
import AlertBubble from './AlertBubble';
import TableHead from './TableHead';
import DynamicMenu from './DynamicMenu';
import Cell from './Cell';
import PivotTable from './PivotTable';
import classes from './AbbreviatedFilterWidget.module.css';
import { utils, writeFileXLSX } from 'xlsx';


function AbbreviatedFilterWidget(props) {
    const worker = useMemo(() => new Worker(new URL("../workers/abbreviatedRowsHandler.js", import.meta.url)), []);
    const [order, setOrder] = useState('asc');
    const [orderBy, setOrderBy] = useState('');
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [page, setPage] = useState(0);
    const [filter, setFilter] = useState({});
    const [rows, setRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [showSettings, setShowSettings] = useState(false);
    const [selectAll, setSelectAll] = useState(false);
    const [headCells, setHeadCells] = useState([]);

    const items = useMemo(() => {
        return props.items.filter(item => {
            const itemId = getIdFromAbbreviatedKey(props.abbreviated, item);
            const metadata = props.itemsMetadata.find(metadata => _.get(metadata, DB_ID) === itemId);
            if (metadata) {
                if (applyFilter([metadata], filter).length > 0) {
                    return true;
                }
            } else {
                return true;
            }
            return false;
        })
    }, [props.items, props.abbreviated, props.itemsMetadata, getIdFromAbbreviatedKey, applyFilter, filter])

    const bufferCollection = useMemo(() => {
        return props.collections.filter(col => col.key === props.bufferedKeyName)[0];
    }, [props.collections, props.bufferedKeyName])

    const loadedCollection = useMemo(() => {
        return props.collections.filter(col => col.key === props.loadedKeyName)[0];
    }, [props.collections, props.loadedKeyName])

    const collections = useMemo(() => {
        let collections = [];
        if (props.abbreviated && props.itemCollections.length > 0) {
            props.abbreviated.split('^').forEach(field => {
                let title;
                let source = field;
                if (source.indexOf(":") !== -1) {
                    title = field.split(":")[0];
                    source = field.split(":")[1];
                }
                let xpath = source.split("-").map(path => path = path.substring(path.indexOf(".") + 1));
                xpath = xpath.join("-");
                let subCollections = xpath.split("-").map(path => {
                    return props.itemCollections.map(col => Object.assign({}, col))
                        .filter(col => col.tableTitle === path)[0];
                })
                source = xpath.split("-")[0];
                let collection = props.itemCollections.map(col => Object.assign({}, col)).filter(col => col.tableTitle === source)[0];
                collection.xpath = xpath;
                collection.tableTitle = xpath;
                collection.elaborateTitle = false;
                collection.hide = false;
                collection.subCollections = subCollections;
                if (xpath.indexOf('-') !== -1) {
                    collection.type = DataTypes.STRING;
                }
                if (title) {
                    collection.title = title;
                }
                collections.push(collection);
            })
        }
        return collections
    }, [props.abbreviated, props.itemCollections])

    useEffect(() => {
        if (window.Worker) {
            worker.postMessage({ items, itemsData: props.itemsMetadata, itemProps: collections, abbreviation: props.abbreviated, loadedProps: loadedCollection, page, pageSize: rowsPerPage, order, orderBy });
        }
    }, [items, props.itemsMetadata, page, rowsPerPage, order, orderBy])

    useEffect(() => {
        if (window.Worker) {
            worker.onmessage = (e) => {
                const [updatedRows, updatedActiveRows] = e.data;
                setRows(updatedRows);
                setActiveRows(updatedActiveRows);
            }
        }
        return () => {
            worker.terminate();
        }
    }, [worker])

    useEffect(() => {
        setHeadCells(collections);
    }, [])

    useEffect(() => {
        let activeItems = activeRows.map(row => getAbbreviatedKeyFromId(items, props.abbreviated, row['data-id']));
        if (!_.isEqual(activeItems, props.activeItems)) {
            props.setOldActiveItems(props.activeItems);
            props.setActiveItems(activeItems);
        }
    }, [activeRows, items, props.abbreviated])

    useEffect(() => {
        if (items.length === 0) {
            props.setSelectedItem(null);
        }
    }, [items, props.setSelectedItem])

    const onButtonClick = (e, action, xpath, value) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData);
        } else if (action === 'flux_trigger_strat') {
            let updatedData = flux_trigger_strat(value);
            if (updatedData) {
                props.onButtonToggle(e, xpath, updatedData);
            }
        }
    }

    const handleRequestSort = (event, property) => {
        const isAsc = orderBy === property && order === 'asc';
        setOrder(isAsc ? 'desc' : 'asc');
        setOrderBy(property);
        setPage(0);
    }

    const onRowSelect = (id) => {
        if (props.mode === Modes.READ_MODE) {
            props.onSelect(id);
        }
    }

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const onSettingsOpen = () => {
        setShowSettings(true);
    }

    const onSettingsClose = () => {
        setShowSettings(false);
    }

    const exportToExcel = () => {
        const updatedRows = cloneDeep(rows);
        updatedRows.forEach(row => {
            delete row['data-id'];
        })
        const ws = utils.json_to_sheet(updatedRows);
        const wb = utils.book_new();
        utils.book_append_sheet(wb, ws, "Sheet1");
        writeFileXLSX(wb, `${props.name}.xlsx`);
    }

    const onSettingsItemChange = (e, key) => {
        let hide = !e.target.checked;
        if (hide) {
            setSelectAll(false);
        }
        let updatedHeadCells = headCells.map((cell) => cell.tableTitle === key ? { ...cell, hide: hide } : cell)
        setHeadCells(updatedHeadCells);
    }

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

    let menu = (
        <>
            <DynamicMenu
                collections={props.itemCollections}
                currentSchema={props.itemSchema}
                data={props.itemsMetadata}
                filter={filter}
                onFilterChange={setFilter}
            />
            <Icon className={classes.icon} name="Settings" title="Settings" onClick={onSettingsOpen}><Settings fontSize='small' /></Icon>
            <Icon className={classes.icon} name="Export" title="Export" onClick={exportToExcel}><FileDownload fontSize='small' /></Icon>
            <Select
                style={{display: showSettings ? 'inherit' : 'none'}}
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
            {props.headerProps.menu}
        </>
    )

    return (
        <WidgetContainer
            name={props.headerProps.name}
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            menu={menu}
            onChangeMode={props.headerProps.onChangeMode}
            onSave={props.headerProps.onSave}
            onReload={props.headerProps.onReload}
            layout={props.headerProps.layout}
            supportedLayouts={props.headerProps.supportedLayouts}
            onChangeLayout={props.headerProps.onChangeLayout}>
            {props.headerProps.layout === Layouts.ABBREVIATED_FILTER_LAYOUT ? (
                <Fragment>
                    {!bufferCollection.hide && (
                        <Box className={classes.dropdown_container}>
                            <Autocomplete
                                className={classes.autocomplete_dropdown}
                                disableClearable
                                getOptionLabel={(option) => option}
                                options={props.options}
                                size='small'
                                variant='outlined'
                                value={props.searchValue ? props.searchValue : null}
                                onChange={props.onChange}
                                renderInput={(params) => <TextField {...params} label={props.bufferedLabel} />}
                            />
                            <Button
                                className={classes.button}
                                disabled={props.searchValue ? false : true}
                                disableElevation
                                variant='contained'
                                onClick={props.onLoad}>
                                <Download fontSize='small' />
                            </Button>
                        </Box>
                    )}
                    <Divider textAlign='left'><Chip label={props.loadedLabel} /></Divider>
                    {rows && rows.length > 0 && (
                        <>
                            <TableContainer className={classes.container}>
                                <Table
                                    className={classes.table}
                                    size='medium'>
                                    <TableHead
                                        prefixCells={1}
                                        suffixCells={bufferCollection.hide ? 0 : 1}
                                        headCells={headCells}
                                        mode={Modes.READ_MODE}
                                        order={order}
                                        orderBy={orderBy}
                                        onRequestSort={handleRequestSort}
                                    />
                                    <TableBody>
                                        {
                                            activeRows.map((row, index) => {
                                                let selected = row["data-id"] === props.selected;
                                                let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === row["data-id"])[0];
                                                let alertBubbleCount = 0;
                                                let alertBubbleColor = ColorTypes.INFO;
                                                if (props.alertBubbleSource) {
                                                    let alertBubbleData = metadata;
                                                    if (props.linkedItemsMetadata) {
                                                        alertBubbleData = props.linkedItemsMetadata.filter(o => _.get(o, DB_ID) === row["data-id"])[0];
                                                    }
                                                    alertBubbleCount = getAlertBubbleCount(alertBubbleData, props.alertBubbleSource);
                                                    if (props.alertBubbleColorSource) {
                                                        alertBubbleColor = getAlertBubbleColor(alertBubbleData, props.itemCollections, props.alertBubbleSource, props.alertBubbleColorSource);
                                                    }
                                                }
                                                let disabled = false;
                                                const buttonDisable = props.selected !== row["data-id"];

                                                return (
                                                    <Fragment key={index}>
                                                        <TableRow
                                                            selected={selected}
                                                            onClick={() => onRowSelect(row["data-id"])}>
                                                            <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                                {alertBubbleCount > 0 && <AlertBubble content={alertBubbleCount} color={alertBubbleColor} />}
                                                            </TableCell>
                                                            {headCells.map((cell, i) => {

                                                                if (cell.hide) return;
                                                                let mode = Modes.READ_MODE;
                                                                let rowindex = row["data-id"];
                                                                let collection = collections.filter(c => c.tableTitle === cell.tableTitle)[0];
                                                                if (collection.type === "progressBar") {
                                                                    collection = _.cloneDeep(collection);
                                                                    let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === rowindex)[0];
                                                                    if (typeof (collection.min) === DataTypes.STRING) {
                                                                        let min = collection.min;
                                                                        collection.min = _.get(metadata, min.substring(min.indexOf('.') + 1));
                                                                    }
                                                                    if (typeof (collection.max) === DataTypes.STRING) {
                                                                        let max = collection.max;
                                                                        collection.maxFieldName = max.substring(max.lastIndexOf('.') + 1);
                                                                        collection.max = _.get(metadata, max.substring(max.indexOf('.') + 1))
                                                                    }

                                                                }
                                                                let xpath = collection.xpath;
                                                                let value = row[collection.xpath];

                                                                return (
                                                                    <Cell
                                                                        key={i}
                                                                        mode={mode}
                                                                        rowindex={rowindex}
                                                                        name={cell.key}
                                                                        elaborateTitle={cell.tableTitle}
                                                                        currentValue={value}
                                                                        previousValue={value}
                                                                        collection={collection}
                                                                        xpath={xpath}
                                                                        dataxpath={xpath}
                                                                        dataAdd={false}
                                                                        dataRemove={false}
                                                                        disabled={disabled}
                                                                        buttonDisable={buttonDisable}
                                                                        ignoreDisable={true}
                                                                        onUpdate={() => { }}
                                                                        onDoubleClick={() => { }}
                                                                        onButtonClick={onButtonClick}
                                                                        onCheckboxChange={() => { }}
                                                                        onTextChange={() => { }}
                                                                        onSelectItemChange={() => { }}
                                                                        onAutocompleteOptionChange={() => { }}
                                                                        onDateTimeChange={() => { }}
                                                                    />
                                                                )
                                                            })}
                                                            {!bufferCollection.hide && (
                                                                <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                                    <Icon title='Unload' onClick={() => props.onUnload(row["data-id"])}>
                                                                        <Delete fontSize='small' />
                                                                    </Icon>
                                                                </TableCell>
                                                            )}
                                                        </TableRow>
                                                    </Fragment>
                                                )
                                            })
                                        }
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
                        </>
                    )}
                    {props.error && <AlertErrorMessage open={props.error ? true : false} onClose={props.onResetError} severity='error' error={props.error} />}
                </Fragment>
            ) : props.headerProps.layout === Layouts.PIVOT_TABLE ? (
                <Fragment>
                    {rows.length > 0 && <PivotTable pivotData={rows} />}
                </Fragment>
            ) : <h1>Unsupported Layout</h1>}
        </WidgetContainer>
    )
}

AbbreviatedFilterWidget.propTypes = {
    headerProps: PropTypes.object.isRequired,
    options: PropTypes.array,
    searchValue: PropTypes.string,
    onChange: PropTypes.func,
    bufferedLabel: PropTypes.string,
    onLoad: PropTypes.func,
    loadedLabel: PropTypes.string,
    selected: PropTypes.number,
    onSelect: PropTypes.func,
    onUnload: PropTypes.func
}

export default AbbreviatedFilterWidget = React.memo(AbbreviatedFilterWidget);