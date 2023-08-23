import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List,
    ListItem, ListItemButton, ListItemText, Button, RadioGroup, Radio, FormControlLabel, Popover
} from '@mui/material';
import _, { cloneDeep } from 'lodash';
import { Add, AltRoute } from '@mui/icons-material';
import { DataTypes, Modes, SCHEMA_DEFINITIONS_XPATH, API_ROOT_URL } from '../constants';
import {
    addxpath, applyFilter, clearxpath, genChartDatasets, generateObjectFromSchema, getChartOption,
    getCollectionByName, getFilterDict, mergeTsData, updateChartDataObj, updateChartSchema
} from '../utils';
import WidgetContainer from './WidgetContainer';
import { Icon } from './Icon';
import FullScreenModal from './Modal';
import TreeWidget from './TreeWidget';
import EChart from './EChart';
import classes from './ChartWidget.module.css';
import { useSelector } from 'react-redux';
import axios from 'axios';

const CHART_SCHEMA_NAME = 'chart_data';

function ChartWidget(props) {
    // redux states
    const { schemaCollections } = useSelector(state => state.schema);
    // local react states
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
    const [theme, setTheme] = useState('light');
    const [hasTimeSeries, setHasTimeSeries] = useState(false);
    const [tsData, setTsData] = useState([]);
    const [datasets, setDatasets] = useState([]);
    const [rows, setRows] = useState(props.rows);
    const [query, setQuery] = useState();
    const [seriesFieldAttributesList, setSeriesFieldAttributesList] = useState([]);
    // TODO: check if updateCounters are irrelevent
    const [tsUpdateCounter, setTsUpdateCounter] = useState(0);
    const [datasetUpdateCounter, setDatasetUpdateCounter] = useState(0);
    const getAllWsList = useRef([]);

    // 1. update chart schema to add flux properties to necessary fields
    // 2. identify is chart configuration has time series field in y-axis (limitation) 
    // 3. create datasets based on chart configuration (for both time-series and non time-series)
    //    - default rows to be already present in dataset. set name of dataset as default
    //    - if chart configuration has time series, time series data is fetched from query (oe queries) 
    //      based on applied filter 
    //    - if not time-series, apply filter on rows 
    //    - TODO: add only the necessary field in filter dropdown for time-series
    // 4. create expanded chart configuration object to be used by echart using stored chart configuration and datasets 

    const schema = updateChartSchema(props.schema, props.collections, props.collectionView);

    useEffect(() => {
        // set the theme of chart from browser preferences
        // TODO: add listener to listen for preferences changes
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme('dark');
        }
    }, [])
    
    useEffect(() => {
        // update the local row dataset on update from parent
        setRows(props.rows);
    }, [props.rows])

    useEffect(() => {
        // auto-select the chart obj if exists and not already selected
        if (props.chartData && props.chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && props.chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredChartObj(props.chartData[0]);
                setModifiedChartObj(addxpath(cloneDeep(props.chartData[0])));
            } else {
                setStoredChartObj(props.chartData[selectedIndex]);
                setModifiedChartObj(addxpath(cloneDeep(props.chartData[selectedIndex])));
            }
        }
    }, [props.chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            setStoredChartObj(props.chartData[selectedIndex]);
            setModifiedChartObj(addxpath(cloneDeep(props.chartData[selectedIndex])));
        } else {
            setStoredChartObj({});
            setModifiedChartObj({});
            resetChart();
        }
    }, [selectedIndex])

    useEffect(() => {
        setData(modifiedChartObj);
    }, [modifiedChartObj])

    useEffect(() => {
        // identify if the chart configuration obj selected has a time series or not
        // for time series, selected y axis field should have mapping_src attribute set on it
        // and underlying_time_series should be checked
        if (storedChartObj.series) {
            let timeSeries = false;
            storedChartObj.series.forEach(series => {
                const collection = getCollectionByName(props.collections, series.encode.y, props.collectionView);
                if (collection.mapping_src && series.underlying_time_series) {
                    timeSeries = true;
                    const [seriesWidgetName, mappingSrcField] = collection.mapping_src.split('.', 2);
                    const seriesCollections = schemaCollections[seriesWidgetName];
                    setSeriesFieldAttributesList(seriesCollections);
                    let seriesCollection = seriesCollections.find(col => col.tableTitle === mappingSrcField);
                    let name;
                    let param;
                    seriesCollection.projections.forEach(projection => {
                        // if query is found, dont proceed
                        if (name) return;
                        const [fieldName, queryName] = projection.split(':');
                        if (fieldName === mappingSrcField) {
                            name = queryName;
                        }
                    })
                    seriesCollection = seriesCollections.find(col => col.hasOwnProperty('mapping_projection_query_field'));
                    seriesCollection.mapping_projection_query_field.forEach(queryNQueryParam => {
                        // if param is found, dont proceed
                        if (param) return;
                        const [queryName, queryParam] = queryNQueryParam.split(':');
                        if (queryName === name) {
                            param = queryParam;
                        }
                    })
                    setQuery({ name, param });
                }
            })
            if (timeSeries) {
                setHasTimeSeries(true);
            } else {
                // if not time series, apply the filters on rows
                if (storedChartObj.filters && storedChartObj.filters.length > 0) {
                    const updatedRows = applyFilter(rows, storedChartObj.filters, props.collectionView, props.collections);
                    setRows(updatedRows);
                }
                setHasTimeSeries(false);
            }
        }
    }, [storedChartObj])

    useEffect(() => {
        // create the datasets for chart configuration (time-series and non time-series both)
        const updatedDatasets = genChartDatasets(rows, tsData, storedChartObj, hasTimeSeries, query ? query.param : null);
        setDatasets(updatedDatasets);
        setDatasetUpdateCounter(prevCount => prevCount + 1);
    }, [storedChartObj, rows, tsData, hasTimeSeries, tsUpdateCounter])

    useEffect(() => {
        if (storedChartObj.series && hasTimeSeries) {
            const filterDict = getFilterDict(storedChartObj.filters);
            const collectionWithFilter = seriesFieldAttributesList.find(col => col.hasOwnProperty('mapping_projection_query_field'));
            let seriesFilterField;
            collectionWithFilter.mapping_projection_query_field.forEach(projectionQueryField => {
                if (seriesFilterField) return;
                const [queryName, filterField] = projectionQueryField.split(':');
                if (queryName === query.name) {
                    seriesFilterField = filterField;
                }
            })
            const collection = props.collections.find(col => col.hasOwnProperty('mapping_underlying_meta_field') && col.mapping_underlying_meta_field.filter(meta => meta.includes(seriesFilterField)).length > 0);
            const filterFieldName = props.collectionView ? collection.key : collection.tableTitle;
            const filterValues = filterDict[filterFieldName].split(',').map(filterValue => filterValue.trim());
            const series = storedChartObj.series.find(series => series.underlying_time_series === true);
            if (series) {
                // TODO: uncomment after websocket query is available
                // setTsData([]);
                // filterValues.forEach(value => {
                //     const socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}/ws-query-${query.name}?${query.param.substring(query.param.lastIndexOf('.') + 1)}=${value}`);
                //     socket.onmessage = (event) => {
                //         let updatedData = JSON.parse(event.data);
                //         getAllWsList.current = getAllWsList.current.push(...updatedData);
                //     }
                //     /* close the websocket on cleanup */
                //     return () => socket.close();
                // });
                const updatedTsData = [];
                filterValues.forEach(value => {
                    axios.get(`${API_ROOT_URL}/query-${query.name}?${query.param.substring(query.param.lastIndexOf('.') + 1)}=${value}`).then(res => {
                        updatedTsData.push(...res.data);
                        setTsData([...updatedTsData]);
                        setTsUpdateCounter(prevCount => prevCount + 1);
                    })
                })
            }
        }
    }, [storedChartObj, hasTimeSeries])

    useEffect(() => {
        if (storedChartObj.series) {
            const updatedObj = addxpath(cloneDeep(storedChartObj));
            const updatedChartObj = updateChartDataObj(updatedObj, props.collections, rows, datasets, props.collectionView, schemaCollections);
            setChartObj(updatedChartObj)
        }
    }, [datasets, datasetUpdateCounter])

    // TODO: uncomment after websocket query is available
    // const flushGetAllWs = useCallback(() => {
    //     /* apply get-all websocket changes */
    //     if (getAllWsList.current.length > 0) {
    //         if (query && query.param) {
    //             const updatedTsData = mergeTsData(tsData, getAllWsList.current, query.param);
    //             setTsData(updatedTsData);
    //         }
    //         getAllWsList.current = [];
    //     }
    // }, [tsData, query])


    // useEffect(() => {
    //     const intervalId = setInterval(flushGetAllWs, 500);
    //     return () => {
    //         clearInterval(intervalId);
    //     }
    // }, [])

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
        setHasTimeSeries(false);
        setTsData([]);
        setQuery();
        setSeriesFieldAttributesList([]);
        setTsUpdateCounter(0);
        setDatasetUpdateCounter(0);
    }

    const onSave = () => {
        setMode(Modes.READ_MODE);
        setOpen(false);
        setOpenModalPopup(false);
        const updatedObj = clearxpath(cloneDeep(data));
        props.onChartDataChange(props.name, updatedObj);
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
    }

    const onSelect = (index) => {
        if (index !== selectedIndex) {
            setSelectedIndex(index);
            resetChart();
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
                            </ListItem>
                        ))}
                    </List>
                </Box>
                <Divider orientation="vertical" flexItem />
                <Box className={classes.chart_container}>
                    <EChart
                        loading={false}
                        theme={theme}
                        option={{
                            legend: {},
                            tooltip: {
                                trigger: 'axis',
                                axisPointer: {
                                    type: 'cross'
                                }
                            },
                            dataZoom: {
                                type: 'inside'
                            },
                            dataset: datasets,
                            ...options
                        }}
                    />
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