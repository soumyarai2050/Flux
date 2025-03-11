import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
// third-party package imports
import {
    Box, Divider, List, ListItem, ListItemButton, ListItemText
} from '@mui/material';
import { cloneDeep, get, isEqual } from 'lodash';
import { Add, Delete } from '@mui/icons-material';
// project constants and common utility function imports
import { DATA_TYPES, MODES, SCHEMA_DEFINITIONS_XPATH, API_ROOT_URL, MODEL_TYPES } from '../../../constants';
import {
    addxpath, applyFilter, clearxpath, genChartDatasets, genMetaFilters, generateObjectFromSchema,
    getChartOption, getCollectionByName, getFilterDict, getIdFromAbbreviatedKey, mergeTsData, tooltipFormatter,
    updateChartDataObj, updateChartSchema, updatePartitionFldSchema
} from '../../../utils';
// custom component imports
import Icon from '../../Icon';
import FullScreenModal from '../../Modal';
import EChart from '../../EChart';
import styles from './ChartView.module.css';
import { useTheme } from '@emotion/react';

const CHART_SCHEMA_NAME = 'chart_data';

function ChartView({
    chartData,
    chartRows,
    fieldsMetadata,
    modelType,
    abbreviation,
    modelName,
    onRowSelect,
    onReload,
    onChartDataChange,
    onChartDelete
}) {
    // redux states
    const theme = useTheme();
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);

    const [storedChartObj, setStoredChartObj] = useState({});
    const [modifiedChartObj, setModifiedChartObj] = useState({});
    const [selectedIndex, setSelectedIndex] = useState();
    const [open, setOpen] = useState(false);
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [mode, setMode] = useState(MODES.READ);
    const [data, setData] = useState({});
    // @deprecated - partition moved to chart option
    // const [openPartition, setOpenPartition] = useState(false);
    // const [anchorEl, setAnchorEl] = useState(null);
    const [chartObj, setChartObj] = useState({});
    const [tsData, setTsData] = useState({});
    const [datasets, setDatasets] = useState([]);
    const [rows, setRows] = useState(chartRows);
    const [queryDict, setQueryDict] = useState({});
    // TODO: check if updateCounters are irrelevent
    const [chartUpdateCounter, setChartUpdateCounter] = useState(0);
    const [tsUpdateCounter, setTsUpdateCounter] = useState(0);
    const [datasetUpdateCounter, setDatasetUpdateCounter] = useState(0);
    const [reloadCounter, setReloadCounter] = useState(0);
    const [schema, setSchema] = useState(projectSchema);
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
        const updatedSchema = updateChartSchema(projectSchema, fieldsMetadata, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
        setSchema(updatedSchema);
    }, [])

    useEffect(() => {
        // update the local row dataset on update from parent
        if (mode === MODES.READ) {
            let updatedRows = chartRows;
            if (storedChartObj.filters && storedChartObj.filters.length > 0) {
                updatedRows = applyFilter(chartRows, storedChartObj.filters, modelType === MODEL_TYPES.ABBREVIATION_MERGE, fieldsMetadata);
            }
            if (!storedChartObj.time_series || (storedChartObj.time_series && rows.length !== updatedRows.length)) {
                setRows(updatedRows);
            }
        }
    }, [chartRows])

    useEffect(() => {
        // auto-select the chart obj if exists and not already selected
        if (chartData && chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredChartObj(chartData[0]);
                setModifiedChartObj(addxpath(cloneDeep(chartData[0])));
            }
            else {
                setStoredChartObj(chartData[selectedIndex]);
                setModifiedChartObj(addxpath(cloneDeep(chartData[selectedIndex])));
                const updatedSchema = updatePartitionFldSchema(schema, chartData[selectedIndex]);
                setSchema(updatedSchema);
            }
        }
        setChartUpdateCounter(prevCount => prevCount + 1);
    }, [chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            setStoredChartObj(chartData[selectedIndex]);
            setModifiedChartObj(addxpath(cloneDeep(chartData[selectedIndex])));
            const updatedSchema = updatePartitionFldSchema(schema, chartData[selectedIndex]);
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
                const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
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
                        if (col.val_meta_field && ![DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(col.type)) {
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
                    const updatedRows = applyFilter(rows, storedChartObj.filters, modelType === MODEL_TYPES.ABBREVIATION_MERGE, fieldsMetadata);
                    setRows(updatedRows);
                } else {
                    setRows(chartRows);
                }
            }
        }
    }, [chartUpdateCounter])

    useEffect(() => {
        if (storedChartObj.series && storedChartObj.time_series) {
            const filterDict = getFilterDict(storedChartObj.filters);
            if (Object.keys(filterDict).length > 0) {
                const metaFilters = genMetaFilters(rows, fieldsMetadata, filterDict, Object.keys(filterDict)[0], modelType === MODEL_TYPES.ABBREVIATION_MERGE);
                storedChartObj.series.forEach((series, index) => {
                    const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
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
        const updatedDatasets = genChartDatasets(rows, tsData, storedChartObj, queryDict, fieldsMetadata, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
        setDatasets(updatedDatasets);
        setDatasetUpdateCounter(prevCount => prevCount + 1);
    }, [chartUpdateCounter, rows, tsUpdateCounter, queryDict])

    useEffect(() => {
        if (storedChartObj.series) {
            const updatedObj = addxpath(cloneDeep(storedChartObj));
            const updatedChartObj = updateChartDataObj(updatedObj, fieldsMetadata, rows, datasets, modelType === MODEL_TYPES.ABBREVIATION_MERGE, schemaCollections, queryDict);
            setChartObj(updatedChartObj)
        }
    }, [datasetUpdateCounter, queryDict])

    const flushGetAllWs = useCallback(() => {
        /* apply get-all websocket changes */
        if (Object.keys(getAllWsDict.current).length > 0 && mode === MODES.READ) {
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
        if (modelType === MODEL_TYPES.ABBREVIATION_MERGE && selectedData) {
            const idField = abbreviation.split(':')[0];
            if (storedChartObj.time_series) {
                const query = queryDict[selectedData.seriesIndex];
                if (query) {
                    const keys = query.params.map(param => {
                        const collection = fieldsMetadata.find(col => {
                            if (col.hasOwnProperty('mapping_underlying_meta_field')) {
                                const [, ...mappedFieldSplit] = col.mapping_underlying_meta_field.split('.');
                                const mappedField = mappedFieldSplit.join('.');
                                if (mappedField === param) {
                                    return true;
                                }
                            }
                            return false;
                        })
                        if (modelType === MODEL_TYPES.ABBREVIATION_MERGE) {
                            return collection.key;
                        } else {
                            return collection.tableTitle;
                        }
                    })
                    const filterCriteria = {};
                    query.params.forEach((param, index) => {
                        filterCriteria[keys[index]] = get(selectedData, param);
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
                            if (typeof id === DATA_TYPES.STRING) {
                                id = getIdFromAbbreviatedKey(abbreviation, id);
                            }
                            onRowSelect(id);
                        }
                    }
                }
            } else {
                let id = selectedData[idField];
                if (typeof id === DATA_TYPES.STRING) {
                    id = getIdFromAbbreviatedKey(abbreviation, id);
                }
                onRowSelect(id);
            }
        }
    }, [selectedData, queryDict])

    // on closing of modal, open a pop up to confirm/discard changes
    const onClose = (e) => {
        if (!isEqual(modifiedChartObj, data)) {
            setOpenModalPopup(true);
        } else {
            setOpen(false);
            setMode(MODES.READ);
        }
    }

    const resetChart = () => {
        setRows(chartRows);
        setDatasets([]);
        setTsData({});
        setQueryDict({});
        setTsUpdateCounter(0);
        setDatasetUpdateCounter(0);
    }

    const onSave = () => {
        setMode(MODES.READ);
        setOpen(false);
        setOpenModalPopup(false);
        const updatedObj = clearxpath(cloneDeep(data));
        onChartDataChange(modelName, updatedObj);
        setChartUpdateCounter(prevCount => prevCount + 1);
    }

    // on closing of modal popup (discard), revert back the changes
    const onConfirmClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        else {
            setData(modifiedChartObj);
            setOpen(false);
            setOpenModalPopup(false);
            setMode(MODES.READ);
        }
    }

    const onChangeMode = () => {
        setMode(MODES.EDIT);
        setOpen(true);
    }

    const handleReload = () => {
        setMode(MODES.READ);
        onReload();
        setReloadCounter(prevCount => prevCount + 1);
    }

    const onCreate = () => {
        let updatedObj = generateObjectFromSchema(schema, get(schema, [SCHEMA_DEFINITIONS_XPATH, CHART_SCHEMA_NAME]));
        updatedObj = addxpath(updatedObj);
        setModifiedChartObj(updatedObj);
        setData(updatedObj);
        setStoredChartObj({});
        setMode(MODES.EDIT);
        setOpen(true);
    }

    const onUserChange = () => {

    }

    const onUpdate = (updatedData) => {
        setData(updatedData);
        const updatedSchema = cloneDeep(schema);
        const filterSchema = get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, 'ui_filter']);
        const chartSchema = get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, CHART_SCHEMA_NAME]);
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

    const handleChartDelete = (chartName, index) => {
        onChartDelete(modelName, chartName);
        if (index === selectedIndex) {
            setSelectedIndex();
            setStoredChartObj({});
            setModifiedChartObj({});
        }
    }

    const options = getChartOption(clearxpath(cloneDeep(chartObj)));

    return (
        <>
            <Box className={styles.container}>
                <Box className={styles.list_container}>
                    <List>
                        {chartData && chartData.map((item, index) => (
                            <ListItem className={styles.list_item} key={index} selected={selectedIndex === index} disablePadding onClick={() => onSelect(index)}>
                                <ListItemButton>
                                    <ListItemText>{item.chart_name}</ListItemText>
                                </ListItemButton>
                                <Icon title='Delete' onClick={() => handleChartDelete(item.chart_name, index)}>
                                    <Delete fontSize='small' />
                                </Icon>
                            </ListItem>
                        ))}
                    </List>
                </Box>
                <Divider orientation='vertical' flexItem />
                <Box className={styles.chart_container}>
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
                            isCollectionType={modelType === MODEL_TYPES.ABBREVIATION_MERGE}
                        />
                    )}
                </Box>
            </Box>
            <FullScreenModal
                id={`${modelName}-modal`}
                open={open}
                onClose={onClose}
                onSave={onSave}
                popup={openModalPopup}
                onConfirmClose={onConfirmClose}>
                {/* <TreeWidget
                    name={CHART_SCHEMA_NAME}
                    schema={schema}
                    data={data}
                    originalData={storedChartObj}
                    mode={mode}
                    onUpdate={onUpdate}
                    onUserChange={onUserChange}
                    topLevel={false}
                /> */}
                {/* <Dialog
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
                </Dialog> */}
            </FullScreenModal>
        </>
    )
}

export default ChartView;