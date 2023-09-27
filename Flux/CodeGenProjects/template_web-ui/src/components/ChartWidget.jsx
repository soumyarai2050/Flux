import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
// third-party package imports
import {
    Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, 
    List, ListItem, ListItemButton, ListItemText 
} from '@mui/material';
import _, { cloneDeep } from 'lodash';
import { Add, Delete } from '@mui/icons-material';
// project constants and common utility function imports
import { DataTypes, Modes, SCHEMA_DEFINITIONS_XPATH, API_ROOT_URL } from '../constants';
import {
    addxpath, applyFilter, clearxpath, genChartDatasets, genMetaFilters, generateObjectFromSchema, 
    getChartOption, getCollectionByName, getFilterDict, getIdFromAbbreviatedKey, mergeTsData, tooltipFormatter, 
    updateChartDataObj, updateChartSchema, updatePartitionFldSchema
} from '../utils';
// custom component imports
import WidgetContainer from './WidgetContainer';
import { Icon } from './Icon';
import FullScreenModal from './Modal';
import TreeWidget from './TreeWidget';
import EChart from './EChart';
import classes from './ChartWidget.module.css';
import { useTheme } from '@emotion/react';

const CHART_SCHEMA_NAME = 'chart_data';

function ChartWidget(props) {
    // redux states
    const { schemaCollections } = useSelector(state => state.schema);
    // local react states
    const theme = useTheme();
    const [storedChartObj, setStoredChartObj] = useState({});
    const [modifiedChartObj, setModifiedChartObj] = useState({});
    const [selectedIndex, setSelectedIndex] = useState();
    const [open, setOpen] = useState(false);
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [mode, setMode] = useState(Modes.READ_MODE);
    const [data, setData] = useState({});
    // @deprecated - partition moved to chart option
    // const [openPartition, setOpenPartition] = useState(false);
    // const [anchorEl, setAnchorEl] = useState(null);
    const [chartObj, setChartObj] = useState({});
    const [tsData, setTsData] = useState({});
    const [datasets, setDatasets] = useState([]);
    const [rows, setRows] = useState(props.rows);
    const [queryDict, setQueryDict] = useState({});
    // TODO: check if updateCounters are irrelevent
    const [chartUpdateCounter, setChartUpdateCounter] = useState(0);
    const [tsUpdateCounter, setTsUpdateCounter] = useState(0);
    const [datasetUpdateCounter, setDatasetUpdateCounter] = useState(0);
    const [reloadCounter, setReloadCounter] = useState(0);
    const [schema, setSchema] = useState(props.schema);
    const [selectedData, setSelectedData] = useState();
    const socketList = useRef([]);
    const getAllWsDict = useRef({});

    // 1. update chart schema to add flux properties to necessary fields
    // 2. identify is chart configuration has time series field in y-axis (limitation) 
    // 3. create datasets based on chart configuration (for both time-series and non time-series)
    //    - default rows to be already present in dataset. set name of dataset as default
    //    - if chart configuration has time series, time series data is fetched from query (oe queries) 
    //      based on applied filter 
    //    - if not time-series, apply filter on rows 
    //    - add only the necessary field in filter dropdown for time-series
    // 4. create expanded chart configuration object to be used by echart using stored chart configuration and datasets 

    useEffect(() => {
        const updatedSchema = updateChartSchema(props.schema, props.collections, props.collectionView);
        setSchema(updatedSchema);
    }, [])

    useEffect(() => {
        // update the local row dataset on update from parent
        if (mode === Modes.READ_MODE) {
            let updatedRows = props.rows;
            if (storedChartObj.filters && storedChartObj.filters.length > 0) {
                updatedRows = applyFilter(props.rows, storedChartObj.filters, props.collectionView, props.collections);
            }
            if (!storedChartObj.time_series || (storedChartObj.time_series && rows.length !== updatedRows.length)) {
                setRows(updatedRows);
            }
        }
    }, [props.rows])

    useEffect(() => {
        // auto-select the chart obj if exists and not already selected
        if (props.chartData && props.chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && props.chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredChartObj(props.chartData[0]);
                setModifiedChartObj(addxpath(cloneDeep(props.chartData[0])));
            }
            else {
                setStoredChartObj(props.chartData[selectedIndex]);
                setModifiedChartObj(addxpath(cloneDeep(props.chartData[selectedIndex])));
                const updatedSchema = updatePartitionFldSchema(schema, props.chartData[selectedIndex]);
                setSchema(updatedSchema);
            }
        }
        setChartUpdateCounter(prevCount => prevCount + 1);
    }, [props.chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            setStoredChartObj(props.chartData[selectedIndex]);
            setModifiedChartObj(addxpath(cloneDeep(props.chartData[selectedIndex])));
            const updatedSchema = updatePartitionFldSchema(schema, props.chartData[selectedIndex]);
            setSchema(updatedSchema);
        } else {
            setStoredChartObj({});
            setModifiedChartObj({});
            resetChart();
        }
        setChartUpdateCounter(prevCount => prevCount + 1);
    }, [selectedIndex])

    useEffect(() => {
        setData(modifiedChartObj);
    }, [modifiedChartObj])

    useEffect(() => {
        // identify if the chart configuration obj selected has a time series or not
        // for time series, selected y axis field should have mapping_src attribute set on it
        // and time_series should be checked
        if (storedChartObj.series) {
            let updatedQueryDict = {};
            storedChartObj.series.forEach((series, index) => {
                const collection = getCollectionByName(props.collections, series.encode.y, props.collectionView);
                if (storedChartObj.time_series && collection.hasOwnProperty('mapping_src')) {
                    const [seriesWidgetName, ...mappingSrcField] = collection.mapping_src.split('.');
                    const srcField = mappingSrcField.join('.');
                    const seriesCollections = schemaCollections[seriesWidgetName];
                    const mappedCollection = seriesCollections.find(col => col.tableTitle === srcField);
                    // fetch query details for time series
                    let name;
                    let params = [];
                    mappedCollection.projections.forEach(projection => {
                        // if query is found, dont proceed
                        if (name) return;
                        const [fieldName, queryName] = projection.split(':');
                        if (fieldName === srcField) {
                            name = queryName;
                        }
                    })
                    seriesCollections.forEach(col => {
                        if (col.val_meta_field && ![DataTypes.OBJECT, DataTypes.ARRAY].includes(col.type)) {
                            params.push(col.tableTitle);
                        }
                    })
                    updatedQueryDict[index] = { name, params };
                }
            })
            setQueryDict(updatedQueryDict);
            if (!storedChartObj.time_series) {
                // if not time series, apply the filters on rows
                if (storedChartObj.filters && storedChartObj.filters.length > 0) {
                    const updatedRows = applyFilter(rows, storedChartObj.filters, props.collectionView, props.collections);
                    setRows(updatedRows);
                } else {
                    setRows(props.rows);
                }
            }
        }
    }, [chartUpdateCounter])

    useEffect(() => {
        if (storedChartObj.series && storedChartObj.time_series) {
            const filterDict = getFilterDict(storedChartObj.filters);
            if (Object.keys(filterDict).length > 0) {
                const metaFilters = genMetaFilters(rows, props.collections, filterDict, Object.keys(filterDict)[0], props.collectionView);
                storedChartObj.series.forEach((series, index) => {
                    const collection = getCollectionByName(props.collections, series.encode.y, props.collectionView);
                    if (collection.hasOwnProperty('mapping_src')) {
                        const query = queryDict[index];
                        if (query) {
                            metaFilters.forEach(metaFilterDict => {
                                let paramStr;
                                for (const key in metaFilterDict) {
                                    if (paramStr) {
                                        paramStr += `&${key}=${metaFilterDict[key]}`;
                                    } else {
                                        paramStr = `${key}=${metaFilterDict[key]}`;
                                    }
                                }
                                const socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}/ws-query-${query.name}?${paramStr}`);
                                socketList.current.push(socket);
                                socket.onmessage = (event) => {
                                    let updatedData = JSON.parse(event.data);
                                    if (getAllWsDict.current[query.name]) {
                                        getAllWsDict.current[query.name].push(...updatedData);
                                    } else {
                                        getAllWsDict.current[query.name] = updatedData;
                                    }
                                }
                            })
                        }
                    }
                })
            }
        }
        return () => {
            socketList.current.forEach(socket => {
                if (socket) {
                    socket.close();
                }
            })
            socketList.current = [];
            getAllWsDict.current = {};
            setTsData({});
        }
    }, [chartUpdateCounter, reloadCounter, queryDict, rows])

    useEffect(() => {
        // create the datasets for chart configuration (time-series and non time-series both)
        const updatedDatasets = genChartDatasets(rows, tsData, storedChartObj, queryDict, props.collections, props.collectionView);
        setDatasets(updatedDatasets);
        setDatasetUpdateCounter(prevCount => prevCount + 1);
    }, [chartUpdateCounter, rows, tsUpdateCounter, queryDict])

    useEffect(() => {
        if (storedChartObj.series) {
            const updatedObj = addxpath(cloneDeep(storedChartObj));
            const updatedChartObj = updateChartDataObj(updatedObj, props.collections, rows, datasets, props.collectionView, schemaCollections, queryDict);
            setChartObj(updatedChartObj)
        }
    }, [datasetUpdateCounter, queryDict])

    const flushGetAllWs = useCallback(() => {
        /* apply get-all websocket changes */
        if (Object.keys(getAllWsDict.current).length > 0 && mode === Modes.READ_MODE) {
            const updatedWsDict = cloneDeep(getAllWsDict.current);
            getAllWsDict.current = {}
            const updatedTsData = mergeTsData(tsData, updatedWsDict, queryDict);
            setTsData(updatedTsData);
            setTsUpdateCounter(prevCount => prevCount + 1);
        }
    }, [tsData, queryDict, mode])

    useEffect(() => {
        const intervalId = setInterval(flushGetAllWs, 500);
        return () => {
            clearInterval(intervalId);
        }
    }, [tsData, queryDict, mode])

    useEffect(() => {
        if (props.collectionView && selectedData) {
            const idField = props.abbreviated.split(':')[0];
            if (storedChartObj.time_series) {
                const query = queryDict[selectedData.seriesIndex];
                if (query) {
                    const keys = query.params.map(param => {
                        const collection = props.collections.find(col => {
                            if (col.hasOwnProperty('mapping_underlying_meta_field')) {
                                const [, ...mappedFieldSplit] = col.mapping_underlying_meta_field.split('.');
                                const mappedField = mappedFieldSplit.join('.');
                                if (mappedField === param) {
                                    return true;
                                }
                            }
                            return false;
                        })
                        if (props.collectionView) {
                            return collection.key;
                        } else {
                            return collection.tableTitle;
                        }
                    })
                    const filterCriteria = {};
                    query.params.forEach((param, index) => {
                        filterCriteria[keys[index]] = _.get(selectedData, param);
                    })
                    const row = rows.find(row => {
                        let found = true;
                        Object.keys(filterCriteria).forEach(field => {
                            if (row[field] !== filterCriteria[field]) {
                                found = false;
                            }
                        })
                        if (found) return true;
                        return false;
                    })
                    if (row) {
                        if (row.hasOwnProperty(idField)) {
                            let id = row[idField];
                            if (typeof id === DataTypes.STRING) {
                                id = getIdFromAbbreviatedKey(props.abbreviated, id);
                            }
                            props.setSelectedId(id);
                        }
                    }
                }
            } else {
                let id = selectedData[idField];
                if (typeof id === DataTypes.STRING) {
                    id = getIdFromAbbreviatedKey(props.abbreviated, id);
                }
                props.setSelectedId(id);
            }
        }
    }, [selectedData, queryDict])

    // on closing of modal, open a pop up to confirm/discard changes
    const onClose = (e) => {
        if (!_.isEqual(modifiedChartObj, data)) {
            setOpenModalPopup(true);
        } else {
            setOpen(false);
            setMode(Modes.READ_MODE);
        }
    }

    const resetChart = () => {
        setRows(props.rows);
        setDatasets([]);
        setTsData({});
        setQueryDict({});
        setTsUpdateCounter(0);
        setDatasetUpdateCounter(0);
    }

    const onSave = () => {
        setMode(Modes.READ_MODE);
        setOpen(false);
        setOpenModalPopup(false);
        const updatedObj = clearxpath(cloneDeep(data));
        props.onChartDataChange(props.name, updatedObj);
        setChartUpdateCounter(prevCount => prevCount + 1);
    }

    // on closing of modal popup (discard), revert back the changes
    const onConfirmClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        else {
            setData(modifiedChartObj);
            setOpen(false);
            setOpenModalPopup(false);
            setMode(Modes.READ_MODE);
        }
    }

    const onChangeMode = () => {
        setMode(Modes.EDIT_MODE);
        setOpen(true);
    }

    const onReload = () => {
        setMode(Modes.READ_MODE);
        props.onReload();
        setReloadCounter(prevCount => prevCount + 1);
    }

    const onCreate = () => {
        let updatedObj = generateObjectFromSchema(schema, _.get(schema, [SCHEMA_DEFINITIONS_XPATH, CHART_SCHEMA_NAME]));
        updatedObj = addxpath(updatedObj);
        setModifiedChartObj(updatedObj);
        setData(updatedObj);
        setStoredChartObj({});
        setMode(Modes.EDIT_MODE);
        setOpen(true);
    }

    const onUserChange = () => {

    }

    const onUpdate = (updatedData) => {
        setData(updatedData);
        const updatedSchema = cloneDeep(schema);
        const filterSchema = _.get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, 'ui_filter']);
        const chartSchema = _.get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, CHART_SCHEMA_NAME]);
        if (updatedData.time_series) {
            filterSchema.auto_complete = 'fld_name:MetaFldList';
            chartSchema.properties.partition_fld.hide = true;
        } else {
            filterSchema.auto_complete = 'fld_name:FldList';
            chartSchema.properties.partition_fld.hide = false;
        }
        setSchema(updatedSchema);
    }

    const onSelect = (index) => {
        if (index !== selectedIndex) {
            setSelectedIndex(index);
            resetChart();
        }
    }

    const onChartDelete = (chartName, index) => {
        props.onChartDelete(props.name, chartName);
        if (index === selectedIndex) {
            setSelectedIndex();
            setStoredChartObj({});
            setModifiedChartObj({});
        }
    }

    // @deprecated
    // partition is moved to chart option
    // const onPartitionOpen = (e) => {
    //     setOpenPartition(true);
    //     setAnchorEl(e.currentTarget);
    // }
    // const onPartitionClose = () => {
    //     setOpenPartition(false);
    //     setAnchorEl(null);
    // }
    // const onPartitionFldChange = (e, value) => {
    //     if (value === '') {
    //         value = null;
    //     }
    //     props.onPartitionFldChange(props.name, value);
    //     onPartitionClose();
    // }
    // const partitionMenu = (
    //     <>
    //         <Icon className={classes.icon} name="Partition" title={"Partition: " + props.partitionFld} onClick={onPartitionOpen}><AltRoute fontSize='small' /></Icon>
    //         <Popover
    //             id={props.name + '_partitionFld'}
    //             open={openPartition}
    //             anchorEl={anchorEl}
    //             anchorOrigin={{
    //                 vertical: "bottom",
    //                 horizontal: "center"
    //             }}
    //             onClose={onPartitionClose}>
    //             <RadioGroup
    //                 defaultValue=''
    //                 name="partition_fld"
    //                 value={props.partitionFld ? props.partitionFld : ''}
    //                 onChange={onPartitionFldChange}>
    //                 <FormControlLabel size='small'
    //                     sx={{ paddingLeft: 1 }}
    //                     label='None'
    //                     value=''
    //                     control={
    //                         <Radio checked={!props.partitionFld} size='small' />
    //                     }
    //                 />
    //                 {props.collections.map(collection => {
    //                     if (collection.type === DataTypes.STRING) {
    //                         let label = collection.elaborateTitle ? collection.tableTitle : collection.title;
    //                         let value = collection.tableTitle;
    //                         if (props.collectionView) {
    //                             label = collection.key;
    //                             value = collection.key;
    //                         }
    //                         return (
    //                             <FormControlLabel size='small' key={label}
    //                                 sx={{ paddingLeft: 1 }}
    //                                 label={label}
    //                                 value={value}
    //                                 control={
    //                                     <Radio checked={props.partitionFld === value} size='small' />
    //                                 }
    //                             />
    //                         )
    //                     }
    //                 })}
    //             </RadioGroup>
    //         </Popover>
    //     </>
    // )

    let createMenu = '';
    if (mode === Modes.READ_MODE) {
        createMenu = <Icon title='Create' name='Create' onClick={onCreate}><Add fontSize='small' /></Icon>;
    }

    const menu = (
        <>
            {createMenu}
            {props.menu}
        </>
    )

    const options = getChartOption(clearxpath(cloneDeep(chartObj)));

    return (
        <WidgetContainer
            name={props.name}
            title={props.title}
            onReload={onReload}
            layout={props.layout}
            supportedLayouts={props.supportedLayouts}
            onChangeLayout={props.onChangeLayout}
            mode={mode}
            onSave={onSave}
            menu={menu}
            onChangeMode={onChangeMode}>
            <Box className={classes.container}>
                <Box className={classes.list_container}>
                    <List>
                        {props.chartData && props.chartData.map((item, index) => (
                            <ListItem className={classes.list_item} key={index} selected={selectedIndex === index} disablePadding onClick={() => onSelect(index)}>
                                <ListItemButton>
                                    <ListItemText>{item.chart_name}</ListItemText>
                                </ListItemButton>
                                <Icon title='Delete' onClick={() => onChartDelete(item.chart_name, index)}>
                                    <Delete fontSize='small' />
                                </Icon>
                            </ListItem>
                        ))}
                    </List>
                </Box>
                <Divider orientation="vertical" flexItem />
                <Box className={classes.chart_container}>
                    {storedChartObj.chart_name && (
                        <EChart
                            loading={false}
                            theme={theme.palette.mode}
                            option={{
                                legend: {},
                                tooltip: {
                                    trigger: 'axis',
                                    axisPointer: {
                                        type: 'cross'
                                    },
                                    valueFormatter: (value) => tooltipFormatter(value)
                                },
                                dataZoom: [
                                    {
                                        type: 'inside',
                                        filterMode: 'filter',
                                        xAxisIndex: [0, 1]
                                    },
                                    {
                                        type: 'inside',
                                        filterMode: 'empty',
                                        yAxisIndex: [0, 1]
                                    },
                                    {
                                        type: 'slider',
                                        filterMode: 'filter',
                                        xAxisIndex: [0, 1]
                                    },
                                    {
                                        type: 'slider',
                                        filterMode: 'empty',
                                        yAxisIndex: [0, 1]
                                    }
                                ],
                                dataset: datasets,
                                ...options
                            }}
                            setSelectedData={setSelectedData}
                            isCollectionType={props.collectionView}
                        />
                    )}
                </Box>
            </Box>
            <FullScreenModal
                id={selectedIndex}
                open={open}
                onClose={onClose}
                onSave={onSave}
                popup={openModalPopup}
                onConfirmClose={onConfirmClose}>
                <TreeWidget
                    headerProps={{
                        title: props.title,
                        mode: mode,
                        // menuRight: modalCloseMenu,
                        onSave: onSave
                    }}
                    name={CHART_SCHEMA_NAME}
                    schema={schema}
                    data={data}
                    originalData={storedChartObj}
                    mode={mode}
                    onUpdate={onUpdate}
                    onUserChange={onUserChange}
                    topLevel={false}
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
        </WidgetContainer>
    )
}

export default ChartWidget;