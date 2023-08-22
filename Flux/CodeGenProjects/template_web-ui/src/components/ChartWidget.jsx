import React, { useEffect, useRef, useState } from 'react';
import {
    Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List,
    ListItem, ListItemButton, ListItemText, Button, RadioGroup, Radio, FormControlLabel, Popover
} from '@mui/material';
import _, { cloneDeep } from 'lodash';
import { Add, AltRoute } from '@mui/icons-material';
import { DataTypes, Modes, SCHEMA_DEFINITIONS_XPATH, API_ROOT_URL } from '../constants';
import {
    addxpath, applyFilter, clearxpath, genChartDatasets, generateObjectFromSchema, getChartOption,
    getCollectionByName, getFilterDict, updateChartDataObj, updateChartSchema
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
    const { schemaCollections } = useSelector(state => state.schema);
    const [storedData, setStoredData] = useState({});
    const [modifiedData, setModifiedData] = useState({});
    const [selectedIndex, setSelectedIndex] = useState();
    const [open, setOpen] = useState(false);
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [mode, setMode] = useState(Modes.READ_MODE);
    const [data, setData] = useState({});
    const [openPartition, setOpenPartition] = useState(false);
    const [anchorEl, setAnchorEl] = useState(null);
    const [chartObj, setChartObj] = useState({});
    const [theme, setTheme] = useState('light');
    const [hasTimeSeries, setHasTimeSeries] = useState(false);
    const [tsData, setTsData] = useState([]);
    const [datasets, setDatasets] = useState([]);
    const [rows, setRows] = useState(props.rows);
    const [query, setQuery] = useState();
    // const [rows, setRows] = useState(props.rows);
    // const [seriesName, setSeriesName] = useState();
    // const [projectionField, setProjectionField] = useState();
    // const getAllWsList = useRef([]);
    const socketDict = useRef({});

    const schema = updateChartSchema(props.schema, props.collections, props.collectionView);

    // 1. update chart schema to add flux properties to necessary fields - Done
    // 2. identify is chart configuration has time series field in y-axis (limitation) - Done
    // 3. create datasets based on chart configuration (for both time-series and non time-series)
    //    - default rows to be already present in dataset. set name of dataset as default - Done
    //    - if chart configuration has time series, time series data is fetched from query (oe queries) 
    //      based on applied filter - Done
    //    - if not time-series, apply filter on rows - Done
    //    - TODO: add only the necessary field in filter dropdown for time-series
    // 4. create expanded chart configuration object to be used by echart using stored chart configuration and datasets - Done

    useEffect(() => {
        // set the theme of chart from browser preferences
        // TODO: add listener to listen for preferences changes
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme('dark');
        }
    }, [])

    useEffect(() => {
        // identify if the chart configuration obj selected has a time series or not
        // for time series, selected y axis field should have mapping_src attribute set on it
        // and underlying_time_series should be checked
        if (storedData.series) {
            let timeSeries = false;
            storedData.series.forEach(series => {
                const collection = getCollectionByName(props.collections, series.encode.y, props.collectionView);
                if (collection.mapping_src) {
                    timeSeries = true;
                    const [seriesWidgetName, mappingSrcField] = collection.mapping_src.split('.', 1);
                    const seriesCollections = schemaCollections[seriesWidgetName];
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
                        if (queryName === query) {
                            param = queryParam;
                        }
                    })
                    setQuery({ name, param });
                }
            })
            if (timeSeries && storedData.underlying_time_series) {
                setHasTimeSeries(true);
            } else {
                // if not time series, apply the filters on rows
                if (storedData.filters && storedData.filters.length > 0) {
                    const updatedRows = applyFilter(rows, storedData.filters, props.collectionView, props.collections);
                    setRows(updatedRows);
                }
                setHasTimeSeries(false);
            }
        }
    }, [storedData])

    useEffect(() => {
        // create the datasets for chart configuration (time-series and non time-series both)
        const updatedDatasets = genChartDatasets(rows, tsData, storedData, hasTimeSeries, query.param);
        setDatasets(updatedDatasets);
    }, [rows, tsData, hasTimeSeries])

    useEffect(() => {
        if (storedData.series && hasTimeSeries) {
            const filterDict = getFilterDict(storedData.filters);
            // TODO: filter on CB hardcoded. need logic
            // relation rt_dash.leg1.sec.sec_id -> CB -> bar_data.symbol_n_exch_id.symbol
            const filterValues = filterDict['CB'].split(',').map(filterValue => filterValue.trim());
            const series = storedData.series.find(series => series.underlying_time_series === true);
            if (series) {
                // TODO: uncomment after websocket query is available
                // let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}/${queryName}-ws`);
                // socket.onmessage = (event) => {
                //     let updatedData = JSON.parse(event.data);
                //     if (Array.isArray(updatedData)) {
                //         getAllWsList.current = updatedData;
                //     } else if (_.isObject(updatedData)) {
                //         getAllWsList.current = [updatedData];
                //     }
                // }
                // /* close the websocket on cleanup */
                // return () => socket.close();
                for (const value in filterValues) {
                    axios.get(`${API_ROOT_URL}/query-${query.name}?${query.param.substring(query.param.lastIndexOf('.') + 1)}=${value}`).then(res => {
                        setTsData(prevTsData => [...prevTsData, res.data]);
                    })
                }
            }
        }
    }, [storedData, hasTimeSeries])

    useEffect(() => {
        if (storedData.series) {
            const updatedObj = addxpath(cloneDeep(storedData));
            const updatedChartObj = updateChartDataObj(updatedObj, props.collections, rows, datasets, props.collectionView, schemaCollections);
            setChartObj(updatedChartObj)
        }
    }, [datasets])

    // const datasets = getChartDatasets(rows, props.partitionFld, chartObj, props.collections, schemaCollections);

    // useEffect(() => {
    //     if (!storedData.underlying_time_series) {
    //         setRows(props.rows);
    //     }
    // }, [props.rows, storedData])



    // TODO: uncomment after websocket query is available
    // const flushGetAllWs = useCallback(() => {
    //     /* apply get-all websocket changes */
    //     if (getAllWsList.current.length > 0) {
    //         setRows(prevRows => [...prevRows, ...cloneDeep(getAllWsList.current)]);
    //         getAllWsList.current = [];
    //     }
    // }, [])


    // useEffect(() => {
    //     const intervalId = setInterval(flushGetAllWs, 500);
    //     return () => {
    //         clearInterval(intervalId);
    //     }
    // }, [])

    // useEffect(() => {
    //     if (Object.keys(storedData).length > 0) {
    //         const updatedObj = addxpath(cloneDeep(storedData));
    //         const [updatedChartObj, seriesName, projectionFieldName] = updateChartDataObj(updatedObj, props.collections, rows, datasets, props.partitionFld, props.collectionView, schemaCollections);
    //         setChartObj(updatedChartObj);
    //         setSeriesName(seriesName);
    //         setProjectionField(projectionFieldName);
    //     }
    // }, [storedData, props.filters, props.partitionFld, rows])

    useEffect(() => {
        if (props.chartData && props.chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && props.chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredData(props.chartData[0]);
                setModifiedData(addxpath(cloneDeep(props.chartData[0])));
            } else {
                setStoredData(props.chartData[selectedIndex]);
                setModifiedData(addxpath(cloneDeep(props.chartData[selectedIndex])));
            }
        }
    }, [props.chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            setStoredData(props.chartData[selectedIndex]);
            setModifiedData(addxpath(cloneDeep(props.chartData[selectedIndex])));
        } else {
            setStoredData({});
            setModifiedData({});
        }
    }, [selectedIndex])

    useEffect(() => {
        setData(modifiedData);
    }, [modifiedData])

    // on closing of modal, open a pop up to confirm/discard changes
    const onClose = (e) => {
        if (!_.isEqual(modifiedData, data)) {
            setOpenModalPopup(true);
        } else {
            setOpen(false);
            setMode(Modes.READ_MODE);
        }
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
            setData(modifiedData);
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
        setModifiedData(updatedObj);
        setData(updatedObj);
        setStoredData({});
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
            setQuery();
        }
    }

    const onPartitionOpen = (e) => {
        setOpenPartition(true);
        setAnchorEl(e.currentTarget);
    }

    const onPartitionClose = () => {
        setOpenPartition(false);
        setAnchorEl(null);
    }

    const onPartitionFldChange = (e, value) => {
        if (value === '') {
            value = null;
        }
        props.onPartitionFldChange(props.name, value);
        onPartitionClose();
    }

    let createMenu = '';
    if (mode === Modes.READ_MODE) {
        createMenu = <Icon title='Create' name='Create' onClick={onCreate}><Add fontSize='small' /></Icon>;
    }
    const partitionMenu = (
        <>
            <Icon className={classes.icon} name="Partition" title={"Partition: " + props.partitionFld} onClick={onPartitionOpen}><AltRoute fontSize='small' /></Icon>
            <Popover
                id={props.name + '_partitionFld'}
                open={openPartition}
                anchorEl={anchorEl}
                anchorOrigin={{
                    vertical: "bottom",
                    horizontal: "center"
                }}
                onClose={onPartitionClose}>
                <RadioGroup
                    defaultValue=''
                    name="partition_fld"
                    value={props.partitionFld ? props.partitionFld : ''}
                    onChange={onPartitionFldChange}>
                    <FormControlLabel size='small'
                        sx={{ paddingLeft: 1 }}
                        label='None'
                        value=''
                        control={
                            <Radio checked={!props.partitionFld} size='small' />
                        }
                    />
                    {props.collections.map(collection => {
                        if (collection.type === DataTypes.STRING) {
                            let label = collection.elaborateTitle ? collection.tableTitle : collection.title;
                            let value = collection.tableTitle;
                            if (props.collectionView) {
                                label = collection.key;
                                value = collection.key;
                            }
                            return (
                                <FormControlLabel size='small' key={label}
                                    sx={{ paddingLeft: 1 }}
                                    label={label}
                                    value={value}
                                    control={
                                        <Radio checked={props.partitionFld === value} size='small' />
                                    }
                                />
                            )
                        }
                    })}
                </RadioGroup>
            </Popover>
        </>
    )
    const menu = (
        <>
            {createMenu}
            {partitionMenu}
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
                    {rows.length > 0 &&
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
                    }
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
                    originalData={storedData}
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