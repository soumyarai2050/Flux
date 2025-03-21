import React, { Fragment, useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    Autocomplete, Box, Button, Chip, Divider, TextField, Table, TableContainer, TableBody, TableRow, TableCell,
    TablePagination, Select, MenuItem, FormControlLabel, Checkbox, Snackbar, Alert, Popover
} from '@mui/material';
import WidgetContainer from './WidgetContainer';
import { Download, Delete, Settings, FileDownload, Visibility, ColorLens } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { Icon } from './Icon';
import _, { cloneDeep } from 'lodash';
import { DB_ID, MODES, DATA_TYPES, COLOR_TYPES, Layouts } from '../constants';
import {
    getAlertBubbleColor, getAlertBubbleCount, getIdFromAbbreviatedKey, getAbbreviatedKeyFromId,
    getCommonKeyCollections, getTableColumns, sortColumns,
    getMaxRowSize,
    getGroupedTableColumns,
    getBufferAbbreviatedOptionLabel
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
import ChartWidget from './ChartWidget';
import CopyToClipboard from './CopyToClipboard';
import SkeletonField from './SkeletonField';
import { PageCache, PageSizeCache, SortOrderCache } from '../utility/attributeCache';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { DataSourceHexColorPopup } from './Popup';


function AbbreviatedFilterWidget(props) {
    const worker = useMemo(() => new Worker(new URL("../workers/abbreviatedRowsHandler.js", import.meta.url)), []);
    const [sortOrders, setSortOrders] = useState(SortOrderCache.getSortOrder(props.name));
    const [rowsPerPage, setRowsPerPage] = useState(props.rowsPerPage);
    const [page, setPage] = useState(PageCache.getPage(props.name));
    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [openSettings, setOpenSettings] = useState(false);
    // const [selectAll, setSelectAll] = useState(false);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [toastMessage, setToastMessage] = useState(null);
    const [clipboardText, setClipboardText] = useState(null);
    const [loading, setLoading] = useState(true);
    const [settingsArchorEl, setSettingsArcholEl] = useState();
    const [openVisibilityMenu, setOpenVisibilityMenu] = useState(false);
    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [visibilityMenuArchorEl, setVisibilityMenuAnchorEl] = useState();
    const [openDataSourceDialog, setOpenDataSourceDialog] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const visibilityMenuClickTimeout = useRef(null);

    const maxRowSize = useMemo(() => getMaxRowSize(activeRows), [activeRows]);

    // todo - check
    useEffect(() => {
        setLoading(true);
    }, [props.collectionIndex])

    // deprecated
    const items = useMemo(() => {
        return props.items.filter(item => {
            const itemId = getIdFromAbbreviatedKey(props.abbreviated, item);
            const metadata = props.itemsMetadata.find(metadata => _.get(metadata, DB_ID) === itemId);
            if (metadata) return true;
            return false;
        })
    }, [props.items, props.abbreviated, props.itemsMetadata])

    // deprecated
    useEffect(() => {
        if (window.Worker) {
            worker.postMessage({
                items,
                itemsDataDict: props.modifiedItemsMetadataDict,
                itemProps: props.collections,
                abbreviation: props.abbreviated,
                loadedProps: props.loadListFieldAttrs,
                page,
                pageSize: rowsPerPage,
                sortOrders,
                filters: props.filters,
                joinBy: props.joinBy,
                joinSort: props.joinSort
            });
        }
    }, [items, props.modifiedItemsMetadataDict, page, rowsPerPage, sortOrders, props.filters, props.joinBy])

    // deprecated
    useEffect(() => {
        if (window.Worker) {
            worker.onmessage = (e) => {
                const [updatedRows, updatedGroupedRows, updatedActiveRows] = e.data;
                setRows(updatedRows);
                setGroupedRows(updatedGroupedRows);
                setActiveRows(updatedActiveRows);
                setLoading(false);
            }
        }
        return () => {
            worker.terminate();
        }
    }, [worker])

    // deprecated
    useEffect(() => {
        const tableColumns = getTableColumns(props.collections, MODES.READ, props.enableOverride, props.disableOverride, props.showLess, true);
        const groupedTableColumns = getGroupedTableColumns(tableColumns, maxRowSize, groupedRows, props.joinBy, props.mode, true);
        setHeadCells(groupedTableColumns);
    }, [props.enableOverride, props.disableOverride, props.showLess, maxRowSize, groupedRows, props.joinBy, props.mode])

    // deprecated
    useEffect(() => {
        if (props.mode === MODES.EDIT) {
            setCommonKeys([]);
        } else {
            const commonKeyCollections = getCommonKeyCollections(activeRows, headCells, !showHidden && !showAll, true, false, !showMore && !moreAll);
            setCommonKeys(commonKeyCollections);
        }
    }, [activeRows, headCells, props.mode, showHidden, showMore, showAll, moreAll])

    // deprecated
    useEffect(() => {
        const activeItems = [];
        activeRows.map(row => {
            row.forEach(subRow => {
                const id = getAbbreviatedKeyFromId(items, props.abbreviated, subRow['data-id']);
                activeItems.push(id);
            })
        });
        if (!_.isEqual(activeItems, props.activeItems)) {
            props.setOldActiveItems(props.activeItems);
            props.setActiveItems(activeItems);
        }
    }, [activeRows, items, props.abbreviated])

    // todo
    useEffect(() => {
        if (items.length === 0) {
            props.setSelectedItem(null);
        }
    }, [items, props.setSelectedItem])

    // done
    const onButtonClick = (e, action, xpath, value, dataSourceId, source, confirmSave = false) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData, dataSourceId, source, confirmSave);
        } else if (action === 'flux_trigger_strat') {
            let updatedData = flux_trigger_strat(value);
            if (updatedData) {
                props.onButtonToggle(e, xpath, updatedData, dataSourceId, source, confirmSave);
            }
        }
    }

    // done
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
        SortOrderCache.setSortOrder(props.name, updatedSortOrders);
        props.onSortOrdersChange(updatedSortOrders);
        setPage(0);
        PageCache.setPage(props.name, 0);
    }

    // done
    const handleRemoveSort = (property) => {
        const updatedSortOrders = sortOrders.filter(o => o.order_by !== property);
        setSortOrders(updatedSortOrders);
        SortOrderCache.setSortOrder(props.name, updatedSortOrders);
        props.onSortOrdersChange(updatedSortOrders);
    }

    // done
    const onRowSelect = (e, id) => {
        // event (e) is added to make the onRowSelect interface symmetric. 
        // event is used to unselect the row, not implmented in collection view
        if (props.mode === MODES.READ) {
            props.onSelect(id);
            // TODO: below condition is preventing the switch to be efficient
            // if (props.selected !== id) {
                // props.onSelect(id);
            // }
        }
    }

    // done
    const handleChangePage = (event, newPage) => {
        setPage(newPage);
        PageCache.setPage(newPage);
    };

    // done
    const handleChangeRowsPerPage = (event) => {
        const size = parseInt(event.target.value, 10);
        setRowsPerPage(size);
        // PageSizeCache.setPageSize(props.name, size);
        props.onRowsPerPageChange(size);
        setPage(0);
        PageCache.setPage(0);
    };

    // deprecated
    const onSettingsOpen = (e) => {
        setOpenSettings(true);
        setSettingsArcholEl(e.currentTarget);
    }

    // deprecated
    const onSettingsClose = () => {
        setOpenSettings(false);
        setSettingsArcholEl(null);
    }

    // done
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

    // done
    const onRowDoubleClick = (e) => {
        if (props.mode === MODES.READ) {
            if (!e.target.closest('button')) {
                props.headerProps.onChangeMode();
            }
        }
    }

    // done
    const onSettingsItemChange = (e, action, key, value, dataSourceId, source) => {
        // const onSettingsItemChange = (e, key) => {
        // let hide = !e.target.checked;
        let hide = value;
        if (hide) {
            // setSelectAll(false);
            setShowAll(false);
        }
        let updatedHeadCells = headCells.map(cell => cell.key === key ? { ...cell, hide: hide } : cell)
        setHeadCells(updatedHeadCells);
        let collection = props.collections.find(c => c.key === key);
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

    // done
    const onShowLessChange = (e, action, key, value, dataSourceId, source) => {
        let less = value;
        let updatedHeadCells = headCells.map(cell => cell.key === key ? { ...cell, showLess: less } : cell)
        setHeadCells(updatedHeadCells);
        let collection = props.collections.find(c => c.key === key);
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
        props.onShowLessChange(showLessArray);
    }

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

    // done
    const showAllHandler = (e, action, key, value, dataSourceId, source) => {
        setShowAll(!value);
    }

    // done
    const moreAllHandler = (e, action, key, value, dataSourceId, source) => {
        setMoreAll(!value);
    }

    // todo
    const copyColumnHandler = (cell) => {
        const columnName = cell.key;
        let sourceIndex = cell.sourceIndex;
        if (sourceIndex === null || sourceIndex === undefined) {
            sourceIndex = 0;
        }
        const values = [columnName];
        groupedRows.map(r => {
            const row = r[sourceIndex];
            values.push(row[columnName]);
        })
        const text = values.join('\n');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text);
        } else {
            setClipboardText(text);
        }
        setToastMessage("column copied to clipboard: " + columnName);
    }

    // todo
    const onCloseToastMessage = () => {
        setClipboardText(null);
        setToastMessage(null);
    }

    // done
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

    // done
    const onTextChange = useCallback((e, type, xpath, value, dataxpath, validationRes, dataSourceId, source) => {
        if (value === '') {
            value = null;
        }
        if (type === DATA_TYPES.NUMBER) {
            if (value !== null) {
                value = value * 1;
            }
        }
        const data = props.modifiedItemsMetadataDict[source].find(o => o[DB_ID] === props.selected);
        if (data) {
            const updatedData = cloneDeep(data);
            _.set(updatedData, dataxpath, value);
            props.onUpdate(updatedData, source);
            const userChangeDict = {
                [DB_ID]: dataSourceId,
                [xpath]: value
            }
            props.onUserChange(xpath, value, userChangeDict, source);
            if (props.onFormUpdate) {
                props.onFormUpdate(xpath, validationRes);
            }
        }
    }, [props.onUpdate, props.onUserChange, props.modifiedItemsMetadataDict, props.selected])

    // done
    const onVisibilityMenuOpen = (e) => {
        setOpenVisibilityMenu(true);
        setVisibilityMenuAnchorEl(e.currentTarget);
    }

    // done
    const onVisibilityMenuClose = () => {
        setOpenVisibilityMenu(false);
        setVisibilityMenuAnchorEl(null);
    }

    // done
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
                        setShowHidden(false);
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

    // done
    const visibilityMenuDoubleClickHandler = (checked) => {
        if (checked) {
            setShowHidden(false);
            setShowMore(false);
        } else {
            setShowHidden(true);
        }
    }

    // done
    function getFilteredCells() {
        let updatedCells = cloneDeep(headCells);
        if (!showHidden && !showAll) {
            updatedCells = updatedCells.filter(cell => !cell.hide);
        }
        if (!showMore && !moreAll) {
            updatedCells = updatedCells.filter(cell => !cell.showLess);
        }
        updatedCells = updatedCells.filter(cell => commonKeys.filter(c => c.key === cell.key && c.sourceIndex === cell.sourceIndex).length === 0)
        return updatedCells;
    }

    const filteredHeadCells = sortColumns(getFilteredCells(), props.columnOrders, props.joinBy && props.joinBy.length > 0, props.centerJoin, props.flip, true);
    const maxSequence = Math.max(...headCells.map(cell => cell.sequenceNumber));

    // deprecated
    const dynamicMenu = (
        <>
            {Object.keys(props.modifiedItemsMetadataDict).map(metadataName => {
                return (
                    <DynamicMenu
                        key={metadataName}
                        name={props.headerProps.name}
                        collections={props.collections.filter(col => col.source === metadataName)}
                        commonKeyCollections={commonKeys.filter(col => col.source === metadataName)}
                        data={props.modifiedItemsMetadataDict[metadataName]}
                        filters={props.filters}
                        onFiltersChange={props.onFiltersChange}
                        collectionView={true}
                        onButtonToggle={props.onButtonToggle}
                    />
                )
            })}
        </>
    )
    const visibiltyColor = showMore ? 'warning' : showHidden ? 'success' : 'inherit';
    const visibilityMenu = (
        <>
            <Icon
                className={classes.icon}
                name='Visibility'
                title='Visibility'
                onClick={() => visibilityMenuClickHandler(showMore || showHidden)}
                onDoubleClick={() => visibilityMenuDoubleClickHandler(showMore || showHidden)}>
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
                                checked={showHidden}
                                onChange={() => setShowHidden(!showHidden)}
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
        <>
            {dynamicMenu}
            {visibilityMenu}
            <Icon className={classes.icon} name="Settings" title="Settings" onClick={onSettingsOpen}><Settings fontSize='small' /></Icon>
            <Icon className={classes.icon} name="Export" title="Export" onClick={exportToExcel}><FileDownload fontSize='small' /></Icon>
            {props.joinBy && props.joinBy.length > 0 && <Icon name='Data Source Hex Color' title='Data Source Hex Color' selected={openDataSourceDialog} onClick={() => setOpenDataSourceDialog(true)}><ColorLens fontSize='small' /></Icon>}
            <DataSourceHexColorPopup
                open={openDataSourceDialog}
                onClose={() => setOpenDataSourceDialog(false)}
                maxRowSize={maxRowSize}
                dataSourceColors={props.dataSourceColors}
                onSave={props.onDataSourceColorsChange}
            />
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
                        const columnOrder = props.columnOrders.find(column => column.column_name === cell.key);
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
                        <MenuItem key={cell.key} dense={true}>
                            <FormControlLabel
                                sx={{ display: 'flex', flex: 1 }}
                                size='small'
                                label={cell.key}
                                control={
                                    <ValueBasedToggleButton
                                        name={cell.key}
                                        size='small'
                                        selected={show}
                                        disabled={false}
                                        value={show}
                                        caption={showCaption}
                                        xpath={cell.key}
                                        color={showColor}
                                        onClick={onSettingsItemChange}
                                    />
                                    // <Checkbox
                                    //     size='small'
                                    //     checked={cell.hide ? false : true}
                                    //     onChange={(e) => onSettingsItemChange(e, cell.key)}
                                    // />
                                }
                            />
                            <Select
                                size='small'
                                value={sequence}
                                onChange={(e) => onColumnOrderChange(e.target.value, cell.key)}>
                                {[...Array(maxSequence).keys()].map((v, index) => (
                                    <MenuItem key={index} value={index + 1}>{index + 1}</MenuItem>
                                ))}
                            </Select>
                            <ValueBasedToggleButton
                                name={cell.key}
                                size='small'
                                selected={more}
                                disabled={moreDisabled}
                                value={more}
                                caption={moreCaption}
                                xpath={cell.key}
                                color={moreColor}
                                onClick={onShowLessChange}
                            />
                        </MenuItem>
                    )
                })}
            </Popover>
            {props.headerProps.menu}
        </>
    )

    if (loading || props.dependentLoading) {
        return <SkeletonField title={props.headerProps.title} />
    }

    return (
        <>
            {props.headerProps.layout === LAYOUT_TYPES.ABBREVIATION_MERGE ? (
                <WidgetContainer
                    name={props.headerProps.name}
                    title={props.headerProps.title}
                    mode={props.headerProps.mode}
                    menu={menu}
                    onChangeMode={props.headerProps.onChangeMode}
                    onSave={props.headerProps.onSave}
                    onReload={props.headerProps.onReload}
                    commonkeys={commonKeys}
                    layout={props.headerProps.layout}
                    supportedLayouts={props.headerProps.supportedLayouts}
                    scrollLock={props.scrollLock}
                    onChangeLayout={props.headerProps.onChangeLayout}>
                    <Fragment>
                        {!props.bufferListFieldAttrs.hide && (
                            <Box className={classes.dropdown_container}>
                                <Autocomplete
                                    className={classes.autocomplete_dropdown}
                                    disableClearable
                                    getOptionLabel={(option) => getBufferAbbreviatedOptionLabel(option, props.bufferListFieldAttrs, props.loadListFieldAttrs, props.itemsMetadata)}
                                    options={props.options}
                                    size='small'
                                    variant='outlined'
                                    value={props.searchValue ? props.searchValue : null}
                                    onChange={props.onChange}
                                    renderInput={(params) => <TextField {...params} label={props.bufferListFieldAttrs.title} />}
                                />
                                <Button
                                    color='primary'
                                    className={classes.button}
                                    disabled={props.searchValue ? false : true}
                                    disableElevation
                                    variant='contained'
                                    onClick={props.onLoad}>
                                    <Download fontSize='small' />
                                </Button>
                            </Box>
                        )}
                        <Divider textAlign='left'><Chip label={props.loadListFieldAttrs.title} /></Divider>
                        {groupedRows && groupedRows.length > 0 && (
                            <>
                                <TableContainer className={classes.container}>
                                    <Table
                                        className={classes.table}
                                        size='medium'>
                                        <TableHead
                                            // prefixCells={1}
                                            // suffixCells={props.bufferListFieldAttrs.hide ? 0 : 1}
                                            headCells={filteredHeadCells}
                                            // mode={MODES.READ}
                                            mode={props.headerProps.mode}
                                            sortOrders={sortOrders}
                                            onRequestSort={handleRequestSort}
                                            onRemoveSort={handleRemoveSort}
                                            copyColumnHandler={copyColumnHandler}
                                            collectionView={true}
                                        />
                                        <TableBody>
                                            {
                                                activeRows.map((row, index) => {
                                                    // let selected = cellRow["data-id"] === props.selected;
                                                    // let alertBubbleCount = 0;
                                                    // let alertBubbleColor = COLOR_TYPES.INFO;
                                                    // if (props.alertBubbleSource) {
                                                    //     let alertBubbleData;
                                                    //     const source = props.alertBubbleSource.split('.')[0];
                                                    //     const bubbleSourcePath = props.alertBubbleSource.substring(props.alertBubbleSource.indexOf('.') + 1);
                                                    //     if (props.linkedItemsMetadata) {
                                                    //         alertBubbleData = props.linkedItemsMetadata.find(o => _.get(o, DB_ID) === cellRow['data-id']);
                                                    //     } else {
                                                    //         alertBubbleData = props.modifiedItemsMetadataDict[source].find(meta => _.get(meta, DB_ID) === cellRow['data-id']);
                                                    //     }
                                                    //     alertBubbleCount = getAlertBubbleCount(alertBubbleData, bubbleSourcePath);
                                                    //     if (props.alertBubbleColorSource) {
                                                    //         const bubbleColorSourcePath = props.alertBubbleColorSource.substring(props.alertBubbleColorSource.indexOf('.') + 1);
                                                    //         alertBubbleColor = getAlertBubbleColor(alertBubbleData, props.itemCollectionsDict[source], bubbleSourcePath, bubbleColorSourcePath);
                                                    //     }
                                                    // }
                                                    let disabled = false;
                                                    const storedMetadaDict = {};

                                                    return (
                                                        <Fragment key={index}>
                                                            <TableRow
                                                                className={classes.row}
                                                                // selected={selected}
                                                                // onClick={() => onRowSelect(cellRow["data-id"])}
                                                                onDoubleClick={onRowDoubleClick}>
                                                                {/* <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                                    {alertBubbleCount > 0 && <AlertBubble content={alertBubbleCount} color={alertBubbleColor} />}
                                                                </TableCell> */}
                                                                {filteredHeadCells.map((cell, i) => {
                                                                    // if (cell.hide) return;
                                                                    let cellRow = row[cell.sourceIndex];
                                                                    const nullCell = Object.keys(cellRow).length === 0 && !cell.commonGroupKey;
                                                                    if (cellRow) {
                                                                        Object.keys(props.itemsMetadataDict).map((source) => {
                                                                            storedMetadaDict[source] = props.itemsMetadataDict[source].find(o => o[DB_ID] === cellRow?.['data-id']);
                                                                        })
                                                                    }
                                                                    let selected = cellRow ? cellRow["data-id"] === props.selected : false;
                                                                    const buttonDisable = cellRow ? props.selected !== cellRow["data-id"] : false;
                                                                    // let mode = MODES.READ;
                                                                    let mode = props.headerProps.mode;
                                                                    let rowindex = cellRow ? cellRow["data-id"] : i;
                                                                    // let collection = props.collections.find(c => c.key === cell.key);
                                                                    if (cell.type === "progressBar") {
                                                                        cell = _.cloneDeep(cell);
                                                                        if (typeof (cell.min) === DATA_TYPES.STRING) {
                                                                            let min = cell.min;
                                                                            const source = min.split('.')[0];
                                                                            cell.minFieldName = min.split('.').pop();
                                                                            const metadataArray = props.modifiedItemsMetadataDict[source];
                                                                            if (metadataArray) {
                                                                                const metadata = metadataArray.find(meta => _.get(meta, DB_ID) === cellRow['data-id']);
                                                                                if (metadata) {
                                                                                    cell.min = _.get(metadata, min.substring(min.indexOf('.') + 1));
                                                                                }
                                                                            }
                                                                        }
                                                                        if (typeof (cell.max) === DATA_TYPES.STRING) {
                                                                            let max = cell.max;
                                                                            const source = max.split('.')[0];
                                                                            cell.maxFieldName = max.split('.').pop();
                                                                            const metadataArray = props.modifiedItemsMetadataDict[source];
                                                                            if (metadataArray && cellRow) {
                                                                                const metadata = metadataArray.find(meta => _.get(meta, DB_ID) === cellRow['data-id']);
                                                                                if (metadata) {
                                                                                    cell.max = _.get(metadata, max.substring(max.indexOf('.') + 1));
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                    let xpath = cell.xpath;
                                                                    let value = cellRow ? cellRow[cell.key] : undefined;
                                                                    let storedValue;
                                                                    if (xpath.indexOf('-') !== -1) {
                                                                        const storedValueArray = xpath.split('-').map(path => _.get(storedMetadaDict[cell.source], path))
                                                                            .filter(val => val !== null && val !== undefined);
                                                                        storedValue = storedValueArray.join('-');
                                                                    } else {
                                                                        storedValue = _.get(storedMetadaDict[cell.source], xpath);
                                                                    }
                                                                    if (cell.joinKey || cell.commonGroupKey) {
                                                                        if (!value) {
                                                                            const joinedKeyCellRow = row.find(r => r?.[cell.key] !== null && r?.[cell.key] !== undefined);
                                                                            if (joinedKeyCellRow) {
                                                                                value = joinedKeyCellRow[cell.key];
                                                                            }
                                                                        }
                                                                    }

                                                                    return (
                                                                        <Cell
                                                                            key={i}
                                                                            mode={mode}
                                                                            selected={selected}
                                                                            rowindex={rowindex}
                                                                            name={cell.key}
                                                                            elaborateTitle={cell.tableTitle}
                                                                            currentValue={value}
                                                                            previousValue={storedValue}
                                                                            collection={cell}
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
                                                                            onTextChange={onTextChange}
                                                                            onSelectItemChange={() => { }}
                                                                            onAutocompleteOptionChange={() => { }}
                                                                            onDateTimeChange={() => { }}
                                                                            forceUpdate={props.mode === MODES.READ}
                                                                            truncateDateTime={props.truncateDateTime}
                                                                            widgetType='abbreviatedFilter'
                                                                            onForceSave={props.onForceSave}
                                                                            onRowSelect={onRowSelect}
                                                                            dataSourceId={cellRow ? cellRow['data-id'] : null}
                                                                            nullCell={nullCell}
                                                                            dataSourceColors={props.dataSourceColors}
                                                                        />
                                                                    )
                                                                })}
                                                                {/* {!props.bufferListFieldAttrs.hide && (
                                                                    <TableCell className={classes.cell} sx={{ width: 10 }}>
                                                                        <Icon title='Unload' onClick={() => props.onUnload(row["data-id"])}>
                                                                            <Delete fontSize='small' />
                                                                        </Icon>
                                                                    </TableCell>
                                                                )} */}
                                                            </TableRow>
                                                        </Fragment>
                                                    )
                                                })
                                            }
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                                {groupedRows.length > 6 &&
                                    <TablePagination
                                        rowsPerPageOptions={[25, 50]}
                                        component="div"
                                        count={groupedRows.length}
                                        rowsPerPage={rowsPerPage}
                                        page={page}
                                        onPageChange={handleChangePage}
                                        onRowsPerPageChange={handleChangeRowsPerPage}
                                    />
                                }
                            </>
                        )}
                        {props.error && <AlertErrorMessage open={props.error ? true : false} onClose={props.onResetError} severity='error' error={props.error} />}
                        {toastMessage && (
                            <Snackbar open={toastMessage !== null} autoHideDuration={2000} onClose={onCloseToastMessage}>
                                <Alert onClose={onCloseToastMessage} severity="success">{toastMessage}</Alert>
                            </Snackbar>
                        )}
                        <CopyToClipboard text={clipboardText} copy={clipboardText !== null} />
                    </Fragment>
                </WidgetContainer>
            ) : props.headerProps.layout === LAYOUT_TYPES.PIVOT_TABLE ? (
                <WidgetContainer
                    name={props.headerProps.name}
                    title={props.headerProps.title}
                    onReload={props.headerProps.onReload}
                    layout={props.headerProps.layout}
                    supportedLayouts={props.headerProps.supportedLayouts}
                    scrollLock={props.scrollLock}
                    onChangeLayout={props.headerProps.onChangeLayout}>
                    {rows.length > 0 && <PivotTable pivotData={rows} />}
                </WidgetContainer>
            ) : props.headerProps.layout === LAYOUT_TYPES.CHART ? (
                <ChartWidget
                    name={props.headerProps.name}
                    title={props.headerProps.title}
                    onReload={props.headerProps.onReload}
                    layout={props.headerProps.layout}
                    supportedLayouts={props.headerProps.supportedLayouts}
                    onChangeLayout={props.headerProps.onChangeLayout}
                    schema={props.schema}
                    mode={props.mode}
                    menu={dynamicMenu}
                    onChangeMode={props.headerProps.onChangeMode}
                    rows={rows}
                    chartData={props.chartData}
                    onChartDataChange={props.onChartDataChange}
                    onChartDelete={props.onChartDelete}
                    collections={props.collections}
                    filters={props.filters}
                    collectionView={true}
                    setSelectedId={onRowSelect}
                    abbreviated={props.abbreviated}
                />
            ) : (
                <WidgetContainer>
                    <h1>Unsupported Layout</h1>
                </WidgetContainer>
            )}
        </>
    )
}

AbbreviatedFilterWidget.propTypes = {
    headerProps: PropTypes.object.isRequired,
    options: PropTypes.array,
    searchValue: PropTypes.string,
    onChange: PropTypes.func,
    onLoad: PropTypes.func,
    selected: PropTypes.number,
    onSelect: PropTypes.func,
    onUnload: PropTypes.func
}

export default AbbreviatedFilterWidget = React.memo(AbbreviatedFilterWidget);