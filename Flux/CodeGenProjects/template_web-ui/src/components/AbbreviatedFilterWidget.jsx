import React, { Fragment, useState, useMemo } from 'react';
import { Autocomplete, Box, TextField, Button, Divider, Chip, Table, TableContainer, TableBody, TableRow, TableCell } from '@mui/material';
import WidgetContainer from './WidgetContainer';
import { Download, Delete } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { Icon } from './Icon';
import _ from 'lodash';
import { DB_ID, Modes, DataTypes } from '../constants';
import {
    getAlertBubbleColor, getAlertBubbleCount, getIdFromAbbreviatedKey, getComparator, stableSort
} from '../utils';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { AlertErrorMessage } from './Alert';
import AlertBubble from './AlertBubble';
import TableHead from './TableHead';
import Cell from './Cell';
import classes from './AbbreviatedFilterWidget.module.css';

const AbbreviatedFilterWidget = (props) => {

    const [order, setOrder] = useState('asc');
    const [orderBy, setOrderBy] = useState('');

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

    const collections = useMemo(() => {
        let collections = [];
        if (props.abbreviated && props.itemCollections.length > 0) {
            props.abbreviated.split('$').forEach(field => {
                let title;
                let source = field;
                if (source.indexOf(":") !== -1) {
                    title = field.split(":")[0];
                    source = field.split(":")[1];
                }
                let xpath = source.split("-").map(path => path = path.substring(path.indexOf(".") + 1));
                xpath = xpath.join("-");
                source = source.split("-")[0];
                let key = source.split('.').pop();
                let collection = props.itemCollections.filter(col => col.key === key)[0];
                collection.xpath = xpath;
                if (title) {
                    collection.title = title;
                    collection.tableTitle = title;
                }
                collections.push(collection);
            })
        }
        return collections
    }, [props.abbreviated, props.itemCollections])

    const headCells = _.cloneDeep(collections);

    const rows = useMemo(() => {
        let rows = [];
        if (props.items) {
            props.items.map((item, i) => {
                let row = {};
                let id = getIdFromAbbreviatedKey(props.abbreviated, item);
                let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === id)[0];
                row['data-id'] = id;
                collections.forEach(c => {
                    let value = "";
                    if (c.xpath.indexOf("-") !== -1) {
                        value = c.xpath.split("-").map(xpath => {
                            return _.get(metadata, xpath);
                        })
                        value = value.join("-");
                    } else {
                        value = _.get(metadata, c.xpath);
                    }
                    row[c.xpath] = value;
                })
                rows.push(row);
            })
        }
        return rows;
    }, [props.items, props.abbreviated, props.itemsMetadata, collections])


    return (
        <WidgetContainer
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            menu={props.headerProps.menu}
            onChangeMode={props.headerProps.onChangeMode}
            onSave={props.headerProps.onSave}
            onReload={props.headerProps.onReload}>
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
            <Divider textAlign='left'><Chip label={props.loadedLabel} /></Divider>
            {rows && rows.length > 0 && (
                <TableContainer className={classes.container}>
                    <Table
                        className={classes.table}
                        size='medium'>
                        <TableHead
                            prefixCells={1}
                            suffixCells={1}
                            headCells={headCells}
                            mode={Modes.READ_MODE}
                            order={order}
                            orderBy={orderBy}
                            onRequestSort={handleRequestSort}
                        />
                        <TableBody>
                            {
                                stableSort(rows, getComparator(order, orderBy)).map((row, index) => {
                                    let selected = row["data-id"] === props.selected;
                                    let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === row["data-id"])[0];
                                    let alertBubbleCount = getAlertBubbleCount(metadata, props.alertBubbleSource);
                                    let alertBubbleColor = getAlertBubbleColor(metadata, props.itemCollections, props.alertBubbleSource, props.alertBubbleColorSource);
                                    let disabled = props.selected !== row["data-id"] ? true : false;

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
                                                    let collection = collections.filter(c => c.key === cell.key)[0];
                                                    if (collection.type === "progressBar") {
                                                        collection = _.cloneDeep(collection);
                                                        let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === rowindex)[0];
                                                        if (typeof (collection.min) === DataTypes.STRING) {
                                                            let min = collection.min;
                                                            collection.min = _.get(metadata, min.substring(min.indexOf('.') + 1));
                                                        }
                                                        if (typeof (collection.max) === DataTypes.STRING) {
                                                            let max = collection.max;
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

                                                <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                    <Icon title='Unload' onClick={() => props.onUnload(row["data-id"])}>
                                                        <Delete fontSize='small' />
                                                    </Icon>
                                                </TableCell>
                                            </TableRow>
                                        </Fragment>
                                    )
                                })
                            }
                        </TableBody>
                    </Table>
                </TableContainer>
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