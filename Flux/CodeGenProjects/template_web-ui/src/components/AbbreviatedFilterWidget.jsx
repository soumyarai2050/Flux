import React, { Fragment, useState, useEffect, useMemo } from 'react';
import { Autocomplete, Box, TextField, Button, Divider, Chip, Table, TableContainer, TableBody, TableRow, TableCell, TablePagination } from '@mui/material';
import WidgetContainer from './WidgetContainer';
import { Download, Delete } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { Icon } from './Icon';
import _ from 'lodash';
import { DB_ID, Modes, DataTypes, ColorTypes } from '../constants';
import {
    getAlertBubbleColor, getAlertBubbleCount, getIdFromAbbreviatedKey, getComparator, stableSort, getAbbreviatedKeyFromId, applyFilter, getLocalizedValueAndSuffix
} from '../utils';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { AlertErrorMessage } from './Alert';
import AlertBubble from './AlertBubble';
import TableHead from './TableHead';
import DynamicMenu from './DynamicMenu';
import Cell from './Cell';
import classes from './AbbreviatedFilterWidget.module.css';

const AbbreviatedFilterWidget = (props) => {
    const [order, setOrder] = useState('asc');
    const [orderBy, setOrderBy] = useState('');
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [page, setPage] = useState(0);
    const [filter, setFilter] = useState({});

    const itemsMetadata = useMemo(() => {
        if (props.itemsMetadata && props.itemsMetadata.length > 0) {
            return applyFilter(props.itemsMetadata, filter);
        }
        // return empty array if not set or no metadata found
        return [];
    }, [applyFilter, props.itemsMetadata, filter]);

    const items = useMemo(() => {
        if (itemsMetadata.length > 0) {
            let items = props.items.filter(item => {
                let id = getIdFromAbbreviatedKey(props.abbreviated, item);
                let metadata = itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === id)[0];
                if (metadata) return true;
                return false;
            })
            return items;
        }
        // return empty array if no metadata found
        return [];
    }, [props.items, props.abbreviated, itemsMetadata, getAbbreviatedKeyFromId])

    let bufferCollection = useMemo(() => {
        return props.collections.filter(col => col.key === props.bufferedKeyName)[0];
    }, [props.collections, props.bufferedKeyName])

    let loadedCollection = useMemo(() => {
        return props.collections.filter(col => col.key === props.loadedKeyName)[0];
    }, [props.collections, props.loadedKeyName])

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
                    return props.itemCollections.map(col =>  Object.assign({}, col))
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

    const headCells = _.cloneDeep(collections);

    const rows = useMemo(() => {
        let rows = [];
        if (items) {
            items.map((item, i) => {
                let row = {};
                let id = getIdFromAbbreviatedKey(props.abbreviated, item);
                let metadata = itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === id)[0];
                row['data-id'] = id;
                collections.forEach(c => {
                    let value = null;
                    if (c.xpath.indexOf("-") !== -1) {
                        value = c.xpath.split("-").map(xpath => {
                            let collection = c.subCollections.filter(col => col.tableTitle === xpath)[0];
                            let val = _.get(metadata, xpath);
                            if (val === undefined || val === null) {
                                val = "";
                            }
                            let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                            val = v + numberSuffix;
                            return val;
                        })
                        if (loadedCollection.microSeparator) {
                            value = value.join(loadedCollection.microSeparator);
                        } else {
                            value = value.join("-");
                        }
                    } else {
                        value = _.get(metadata, c.xpath);
                        if (value === undefined || value === null) {
                            value = "";
                        }
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(c, value);
                        value = v;
                    }
                    row[c.xpath] = value;
                })
                rows.push(row);
            })
        }
        return rows;
    }, [items, props.abbreviated, itemsMetadata, collections])

    const activeRows = useMemo(() => {
        return stableSort(rows, getComparator(order, orderBy))
            .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
    }, [rows, order, orderBy, page, rowsPerPage])

    useEffect(() => {
        let activeItems = activeRows.map(row => getAbbreviatedKeyFromId(items, props.abbreviated, row['data-id']));
        if (!_.isEqual(activeItems, props.activeItems)) {
            props.setOldActiveItems(props.activeItems);
            props.setActiveItems(activeItems);
        }
    }, [activeRows, items, props.abbreviated])

    let menu = (
        <>
            <DynamicMenu
                collections={props.itemCollections}
                currentSchema={props.itemSchema}
                data={itemsMetadata}
                filter={filter}
                onFilterChange={setFilter}
            />
            {props.headerProps.menu}
        </>
    )

    return (
        <WidgetContainer
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            menu={menu}
            onChangeMode={props.headerProps.onChangeMode}
            onSave={props.headerProps.onSave}
            onReload={props.headerProps.onReload}>
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
                                        let metadata = itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === row["data-id"])[0];
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
                                        const buttonDisable = row["data-id"] === props.selected ? false : true;

                                        return (
                                            <Fragment key={index}>
                                                <TableRow
                                                    selected={selected}
                                                    onClick={() => onRowSelect(row["data-id"])}>
                                                    <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                        {alertBubbleCount > 0 && <AlertBubble content={alertBubbleCount} color={alertBubbleColor} />}
                                                    </TableCell>
                                                    {headCells.map((cell, i) => {
                                                        let mode = Modes.READ_MODE;
                                                        let rowindex = row["data-id"];
                                                        let collection = collections.filter(c => c.tableTitle === cell.tableTitle)[0];
                                                        if (collection.type === "progressBar") {
                                                            collection = _.cloneDeep(collection);
                                                            let metadata = itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === rowindex)[0];
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

export default AbbreviatedFilterWidget;