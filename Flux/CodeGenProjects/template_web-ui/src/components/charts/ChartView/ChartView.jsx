import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
// third-party package imports
import {
    Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText
} from '@mui/material';
import { cloneDeep, get, isEqual } from 'lodash';
import { Add, Close, Delete, Save } from '@mui/icons-material';
// project constants and common utility function imports
import { DATA_TYPES, MODES, API_ROOT_URL, MODEL_TYPES, DB_ID } from '../../../constants';
import { addxpath, clearxpath } from '../../../utils/core/dataAccess';
import { applyFilter, getChartFilterDict } from '../../../utils/core/dataFiltering';
import {
    genChartDatasets, genMetaFilters, getChartOption, mergeTsData, tooltipFormatter,
    updateChartDataObj, updateChartSchema, updatePartitionFldSchema
} from '../../../utils/core/chartUtils';
import { generateObjectFromSchema, getModelSchema } from '../../../utils/core/schemaUtils';
import { getIdFromAbbreviatedKey } from '../../../utils/core/dataUtils';
import { getCollectionByName } from '../../../utils/core/dataUtils';
// custom component imports
import Icon from '../../Icon';
import FullScreenModal from '../../Modal';
import EChart from '../../EChart';
import styles from './ChartView.module.css';
import { useTheme } from '@emotion/react';
import DataTree from '../../trees/DataTree/DataTree';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../cards';
import QuickFilterPin from '../../QuickFilterPin';

const CHART_SCHEMA_NAME = 'chart_data';

function ChartView({
    chartData,
    chartRows,
    fieldsMetadata,
    modelType,
    abbreviation,
    onRowSelect,
    onReload,
    onChartDataChange,
    // onChartDelete,
    onModeToggle,
    mode,
    onChartSelect,
    selectedChartName,
    chartEnableOverride,
    onChartPointSelect,
    children,
    quickFilters = [],
    onQuickFiltersChange
}) {
    // redux states
    const theme = useTheme();
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);

    const [storedChartObj, setStoredChartObj] = useState({});
    const [updatedChartObj, setUpdatedChartObj] = useState({});
    const [selectedIndex, setSelectedIndex] = useState(selectedChartName ? chartData.findIndex((o) => o.chart_name === selectedChartName) : null);
    const [isChartOptionOpen, setIsChartOptionOpen] = useState(false);
    const [isConfirmPopupOpen, setIsConfirmPopupOpen] = useState(false);
    // const [mode, setMode] = useState(MODES.READ);
    const [data, setData] = useState({});
    const [chartOption, setChartOption] = useState({});
    const [tsData, setTsData] = useState({});
    const [datasets, setDatasets] = useState([]);
    const [rows, setRows] = useState(chartRows);
    const [queryDict, setQueryDict] = useState({});
    // TODO: check if updateCounters are irrelevent
    const [chartUpdateCounter, setChartUpdateCounter] = useState(0);
    const [tsUpdateCounter, setTsUpdateCounter] = useState(0);
    const [datasetUpdateCounter, setDatasetUpdateCounter] = useState(0);
    const [reloadCounter, setReloadCounter] = useState(0);
    const [schema, setSchema] = useState(updateChartSchema(projectSchema, fieldsMetadata, modelType === MODEL_TYPES.ABBREVIATION_MERGE));
    const [selectedData, setSelectedData] = useState();
    const [isCreate, setIsCreate] = useState(false);
    const [pinnedFilters, setPinnedFilters] = useState([]);
    const [pinnedFiltersByChart, setPinnedFiltersByChart] = useState({});
    const pinnedFilterUpdateRef = useRef(false);
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
        const updatedIndex = selectedChartName ? chartData.findIndex((o) => o.chart_name === selectedChartName) : null;
        setSelectedIndex(updatedIndex);
    }, [selectedChartName, chartEnableOverride])

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
        } else {  // mode is EDIT
            setIsChartOptionOpen(true);
        }
    }, [chartRows, mode])

    useEffect(() => {
        // auto-select the chart obj if exists and not already selected
        if (chartData && chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredChartObj(chartData[0]);
                setUpdatedChartObj(addxpath(cloneDeep(chartData[0])));
            }
            else {
                setStoredChartObj(chartData[selectedIndex]);
                setUpdatedChartObj(addxpath(cloneDeep(chartData[selectedIndex])));
                const updatedSchema = updatePartitionFldSchema(schema, chartData[selectedIndex]);
                setSchema(updatedSchema);
            }
        }
        setChartUpdateCounter((prevCount) => prevCount + 1);
    }, [chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            const selectedChartOption = chartData[selectedIndex];
            setStoredChartObj(selectedChartOption);
            setUpdatedChartObj(addxpath(cloneDeep(selectedChartOption)));
            const updatedSchema = updatePartitionFldSchema(schema, selectedChartOption);
            setSchema(updatedSchema);
            onChartSelect(selectedChartOption.chart_name);
        } else {
            setStoredChartObj({});
            setUpdatedChartObj({});
            handleChartReset();
            onChartSelect(null);
        }
        setChartUpdateCounter(prevCount => prevCount + 1);
    }, [selectedIndex])

    useEffect(() => {
        setData(updatedChartObj);
        // Also sync pinned filters when data object changes
        if (updatedChartObj && Object.keys(updatedChartObj).length > 0) {
            // Update current pinned filters to show only the ones for this chart
            const chartSpecificFilters = pinnedFiltersByChart[updatedChartObj.chart_name] || [];
            setPinnedFilters(chartSpecificFilters);

            // Only sync if not currently updating from a pinned filter change
            if (!pinnedFilterUpdateRef.current) {
                syncPinnedFiltersWithData(updatedChartObj);
            }
        } else {
            setPinnedFilters([]);
        }
    }, [updatedChartObj, pinnedFiltersByChart])

    useEffect(() => {
        // identify if the chart configuration obj selected has a time series or not
        // for time series, selected y axis field should have mapping_src attribute set on it
        // and time_series should be checked
        if (storedChartObj.series) {
            let updatedQueryDict = {};
            storedChartObj.series.forEach((series, index) => {
                if (series.encode && series.encode.y) {
                    const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
                    if (storedChartObj.time_series && collection && collection.hasOwnProperty('mapping_src')) {
                        const [seriesWidgetName, ...mappingSrcField] = collection.mapping_src.split('.');
                        const srcField = mappingSrcField.join('.');
                        const seriesCollections = schemaCollections[seriesWidgetName];
                        if (seriesCollections) {
                            const mappedCollection = seriesCollections.find(col => col.tableTitle === srcField);
                            // fetch query details for time series
                            let name;
                            let params = [];
                            if (mappedCollection && mappedCollection.projections) {
                                mappedCollection.projections.forEach(projection => {
                                    // if query is found, dont proceed
                                    if (name) return;
                                    const [fieldName, queryName] = projection.split(':');
                                    if (fieldName === srcField) {
                                        name = queryName;
                                    }
                                });
                            }
                            seriesCollections.forEach(col => {
                                if (col.val_meta_field && col.required && ![DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(col.type)) {
                                    params.push(col.tableTitle);
                                }
                            })
                            updatedQueryDict[index] = { name, params };
                        }
                    }
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
            const filterDict = getChartFilterDict(storedChartObj.filters);
            if (Object.keys(filterDict).length > 0) {
                const metaFilters = genMetaFilters(rows, fieldsMetadata, filterDict, Object.keys(filterDict)[0], modelType === MODEL_TYPES.ABBREVIATION_MERGE);
                storedChartObj.series.forEach((series, index) => {
                    const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
                    if (collection.hasOwnProperty('mapping_src')) {
                        let rootUrl = API_ROOT_URL;
                        const mappingModelName = collection.mapping_src?.split('.')[0];
                        if (mappingModelName) {
                            const mappingModelSchema = getModelSchema(mappingModelName, projectSchema);
                            if (mappingModelSchema?.connection_details) {
                                const { host, port, project_name } = mappingModelSchema.connection_details;
                                rootUrl = `http://${host}:${port}/${project_name}`;
                            }
                        }
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
                                const socket = new WebSocket(`${rootUrl.replace('http', 'ws')}/ws-query-${query.name}?${paramStr}`);
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
            const updatedChartOption = updateChartDataObj(updatedObj, fieldsMetadata, rows, datasets, modelType === MODEL_TYPES.ABBREVIATION_MERGE, schemaCollections, queryDict);
            setChartOption(updatedChartOption);
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
                            onChartPointSelect([id]);
                        }
                    }
                }
            } else {
                let id = selectedData[idField];
                if (typeof id === DATA_TYPES.STRING) {
                    id = getIdFromAbbreviatedKey(abbreviation, id);
                }
                onRowSelect(id);
                onChartPointSelect([id]);
            }
        }
    }, [selectedData, queryDict])

    // on closing of modal, open a pop up to confirm/discard changes
    const handleChartOptionClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        if (!isEqual(updatedChartObj, data)) {
            setIsConfirmPopupOpen(true);
        } else {
            if (isCreate) {
                // If we cancel creation, restore the previously selected chart
                if (selectedIndex !== null && chartData[selectedIndex]) {
                    const selectedChartOption = chartData[selectedIndex];
                    setStoredChartObj(selectedChartOption);
                    setUpdatedChartObj(addxpath(cloneDeep(selectedChartOption)));
                    setData(addxpath(cloneDeep(selectedChartOption)));
                } else {
                    // Or clear if nothing was selected
                    setStoredChartObj({});
                    setUpdatedChartObj({});
                    setData({});
                }
            }
            setIsChartOptionOpen(false);
            setIsCreate(false);
            onModeToggle();
        }
    }

    const handleChartReset = () => {
        setRows(chartRows);
        setDatasets([]);
        setTsData({});
        setQueryDict({});
        setTsUpdateCounter(0);
        setDatasetUpdateCounter(0);
    }

    const handleSave = () => {
        // setMode(MODES.READ);
        onModeToggle();
        const wasCreating = isCreate; // Check if we were in create mode
        setIsCreate(false);
        setIsChartOptionOpen(false);
        setIsConfirmPopupOpen(false);
        const updatedObj = clearxpath(cloneDeep(data));
        const idx = chartData.findIndex((o) => o.chart_name === updatedObj.chart_name);
        const updatedChartData = cloneDeep(chartData);
        if (idx !== -1) {
            updatedChartData.splice(idx, 1, updatedObj);
        } else {
            updatedChartData.push(updatedObj);
        }
        onChartDataChange(updatedChartData);

        if (wasCreating) {
            // If a new chart was created, select it.
            const newIndex = updatedChartData.findIndex((o) => o.chart_name === updatedObj.chart_name);
            setSelectedIndex(newIndex);
        }
        setChartUpdateCounter((prevCount) => prevCount + 1);
    }

    // on closing of modal popup (discard), revert back the changes
    const handleConfirmClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        else {
            if (isCreate) {
                // If we were creating, restore previous selection
                if (selectedIndex !== null && chartData[selectedIndex]) {
                    const selectedChartOption = chartData[selectedIndex];
                    setStoredChartObj(selectedChartOption);
                    setUpdatedChartObj(addxpath(cloneDeep(selectedChartOption)));
                    setData(addxpath(cloneDeep(selectedChartOption)));
                } else {
                    // Or clear if nothing was selected
                    setStoredChartObj({});
                    setUpdatedChartObj({});
                    setData({});
                }
            } else {
                // If we were editing, just revert to the state before edits
                setData(updatedChartObj);
            }
            setIsChartOptionOpen(false);
            setIsConfirmPopupOpen(false);
            setIsCreate(false);
            onModeToggle();
        }
    }

    const handleReload = () => {
        // setMode(MODES.READ);
        onReload();
        setReloadCounter((prevCount) => prevCount + 1);
    }

    const handleChartCreate = () => {
        const chartSchema = getModelSchema(CHART_SCHEMA_NAME, schema);
        const updatedObj = addxpath(generateObjectFromSchema(schema, chartSchema));
        setUpdatedChartObj(updatedObj);
        setData(updatedObj);
        setStoredChartObj({});
        setIsCreate(true);
        // setMode(MODES.EDIT);
        onModeToggle();
        setIsChartOptionOpen(true);
    }

    const handleUserChange = () => {

    }

    const handleUpdate = (updatedData) => {
        setData(updatedData);

        // Only sync pinned filters if this update is NOT coming from a pinned filter change
        // We can detect this by checking if we're in the middle of handling a pinned filter change
        const isFromPinnedFilterChange = pinnedFilterUpdateRef.current;

        if (!isFromPinnedFilterChange) {
            syncPinnedFiltersWithData(updatedData);
        }

        const updatedSchema = cloneDeep(schema);
        const chartEncodeSchema = getModelSchema('chart_encode', updatedSchema);
        const filterSchema = getModelSchema('ui_filter', updatedSchema);
        // get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, 'ui_filter']);
        // const chartSchema = getModelSchema(CHART_SCHEMA_NAME, updatedSchema);
        // get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, CHART_SCHEMA_NAME]);
        if (updatedData.time_series) {
            filterSchema.auto_complete = 'fld_name:MetaFldList';
            // chartSchema.properties.partition_fld.hide = true;
            chartEncodeSchema.auto_complete = 'x:FldList,y:ProjFldList';
        } else {
            filterSchema.auto_complete = 'fld_name:FldList';
            // chartSchema.properties.partition_fld.hide = false;
            chartEncodeSchema.auto_complete = 'x:FldList,y:FldList';
        }
        setSchema(updatedSchema);
    }

    const handleSelect = (index) => {
        if (index !== selectedIndex) {
            setSelectedIndex(index);
            handleChartReset();
        }
    }

    const handleChartDelete = (e, chartName, index) => {
        e.stopPropagation();
        const updatedChartData = chartData.filter((o) => o.chart_name !== chartName);
        onChartDataChange(updatedChartData);
        // Clear pinned filters for the deleted chart
        setPinnedFiltersByChart(prev => {
            const newObj = { ...prev };
            delete newObj[chartName];
            return newObj;
        });
        // If the deleted chart was selected, also clear the visible pinned filters
        if (index === selectedIndex) {
            setPinnedFilters([]);
            setSelectedIndex();
            setStoredChartObj({});
            setUpdatedChartObj({});
        }
    }

    const handleDoubleClick = (index) => {
        handleSelect(index);
        if (mode === MODES.READ) {
            onModeToggle();
            setIsChartOptionOpen(true);
        }
    }

    const handleQuickFilterChange = (key, value) => {
        const updatedQuickFilters = cloneDeep(quickFilters);
        const quickFilter = updatedQuickFilters.find((quickFilter) => quickFilter.chart_name === data.chart_name);
        const newValue = value ? true : false;
        if (quickFilter) {
            quickFilter.filters = JSON.stringify({ ...JSON.parse(quickFilter.filters || '{}'), [key]: newValue });
        } else {
            updatedQuickFilters.push({
                chart_name: data.chart_name,
                filters: JSON.stringify({ [key]: newValue })
            })
        }
        onQuickFiltersChange(updatedQuickFilters);
    }

    const handleQuickFilterPin = (key, title, currentValue, nodeData) => {
        const uniqueId = nodeData.dataxpath || key;
        const currentChartName = data?.chart_name;
        const existingPin = pinnedFilters.find(pin => pin.uniqueId === uniqueId);

        if (!existingPin && currentChartName) {
            // Get current value from chart data or use provided value
            const currentChartValue = getCurrentChartFieldValue(key, nodeData) || currentValue || getDefaultValueForField(nodeData);

            const newPin = {
                key,
                uniqueId,
                title,
                value: currentChartValue,
                nodeData: nodeData // Store field metadata for rendering the correct input type
            };

            // Update chart-specific storage
            setPinnedFiltersByChart(prev => ({
                ...prev,
                [currentChartName]: [...(prev[currentChartName] || []), newPin]
            }));

            // Update current display
            setPinnedFilters(prev => [...prev, newPin]);
        }
    };

    // Helper function to get current value from chart configuration data using xpath
    const getCurrentChartFieldValue = (key, nodeData) => {
        if (!data || !nodeData || !nodeData.dataxpath) return null;

        const dataxpath = nodeData.dataxpath;
        const pathParts = dataxpath.split('.');
        let target = data;

        // Navigate through the path to get the current value
        for (const part of pathParts) {
            if (part.includes('[') && part.includes(']')) {
                // Handle array notation like 'series[0]'
                const arrayName = part.substring(0, part.indexOf('['));
                const index = parseInt(part.substring(part.indexOf('[') + 1, part.indexOf(']')));

                if (target[arrayName] && Array.isArray(target[arrayName]) && target[arrayName][index] !== undefined) {
                    target = target[arrayName][index];
                } else {
                    return null;
                }
            } else {
                if (target[part] !== undefined) {
                    target = target[part];
                } else {
                    return null;
                }
            }
        }

        return target;
    };

    // Helper function to determine default value based on field type
    const getDefaultValueForField = (nodeData) => {
        if (!nodeData) return false;

        switch (nodeData.type) {
            case 'boolean':
                return false;
            case 'enum':
                return nodeData.options?.[0] || nodeData.dropdowndataset?.[0] || null;
            case 'string':
                return '';
            case 'number':
                return 0;
            default:
                return null;
        }
    };

    // Function to sync pinned filter values with current data values
    const syncPinnedFiltersWithData = useCallback((updatedData) => {
        setPinnedFilters(prev => {
            if (prev.length === 0) return prev;

            const updatedPins = prev.map(pin => {
                // Get the current value from the updated data
                const currentValue = getCurrentChartFieldValueFromData(pin.key, pin.nodeData, updatedData);

                // Only update if the value has actually changed AND it's not undefined
                if (currentValue !== undefined && currentValue !== pin.value) {
                    return { ...pin, value: currentValue };
                }
                return pin;
            });

            // Only set state if something actually changed to avoid unnecessary re-renders
            const hasChanges = updatedPins.some((pin, index) => pin.value !== prev[index].value);
            return hasChanges ? updatedPins : prev;
        });
    }, []); // Empty dependency array since it only uses setPinnedFilters

    // Helper function to get current value from specific data object (used for syncing)
    const getCurrentChartFieldValueFromData = (key, nodeData, dataSource) => {
        if (!dataSource || !nodeData || !nodeData.dataxpath) return null;

        const dataxpath = nodeData.dataxpath;
        const pathParts = dataxpath.split('.');
        let target = dataSource;

        // Navigate through the path to get the current value
        for (const part of pathParts) {
            if (part.includes('[') && part.includes(']')) {
                // Handle array notation like 'series[0]'
                const arrayName = part.substring(0, part.indexOf('['));
                const index = parseInt(part.substring(part.indexOf('[') + 1, part.indexOf(']')));

                if (target[arrayName] && Array.isArray(target[arrayName]) && target[arrayName][index] !== undefined) {
                    target = target[arrayName][index];
                } else {
                    return null;
                }
            } else {
                if (target[part] !== undefined) {
                    target = target[part];
                } else {
                    return null;
                }
            }
        }

        return target;
    };

    const handlePinnedFilterChange = (uniqueId, value) => {
        const currentChartName = data?.chart_name;
        if (!currentChartName) {
            return;
        }

        // Set flag to indicate we're updating from a pinned filter
        pinnedFilterUpdateRef.current = true;

        // Update the pinned filter state for current display
        setPinnedFilters(prev => {
            const updated = prev.map(pin =>
                pin.uniqueId === uniqueId ? { ...pin, value } : pin
            );
            return updated;
        });

        // Update chart-specific storage
        setPinnedFiltersByChart(prev => {
            const updated = {
                ...prev,
                [currentChartName]: (prev[currentChartName] || []).map(pin =>
                    pin.uniqueId === uniqueId ? { ...pin, value } : pin
                )
            };
            return updated;
        });

        // Update the actual chart configuration data using xpath
        const updatedChartData = cloneDeep(data);
        const pinnedFilter = pinnedFilters.find(pin => pin.uniqueId === uniqueId);

        if (pinnedFilter && pinnedFilter.nodeData && pinnedFilter.nodeData.dataxpath) {
            // Use the dataxpath from nodeData to update the correct location
            const dataxpath = pinnedFilter.nodeData.dataxpath;

            // Split the path and navigate to set the value
            const pathParts = dataxpath.split('.');
            let target = updatedChartData;

            // Navigate to the parent object
            for (let i = 0; i < pathParts.length - 1; i++) {
                const part = pathParts[i];
                if (part.includes('[') && part.includes(']')) {
                    // Handle array notation like 'series[0]'
                    const arrayName = part.substring(0, part.indexOf('['));
                    const index = parseInt(part.substring(part.indexOf('[') + 1, part.indexOf(']')));

                    if (!target[arrayName]) {
                        target[arrayName] = [];
                    }
                    if (!target[arrayName][index]) {
                        target[arrayName][index] = {};
                    }
                    target = target[arrayName][index];
                } else {
                    if (!target[part]) {
                        target[part] = {};
                    }
                    target = target[part];
                }
            }

            // Set the final value
            const finalKey = pathParts[pathParts.length - 1];
            if (finalKey.includes('[') && finalKey.includes(']')) {
                // Handle array notation in final key
                const arrayName = finalKey.substring(0, finalKey.indexOf('['));
                const index = parseInt(finalKey.substring(finalKey.indexOf('[') + 1, finalKey.indexOf(']')));

                if (!target[arrayName]) {
                    target[arrayName] = [];
                }
                target[arrayName][index] = value;
            } else {
                target[finalKey] = value;
            }

            // Update the chart configuration in the main chartData array and call onChartDataChange
            const idx = chartData.findIndex((o) => o.chart_name === updatedChartData.chart_name);
            const updatedChartDataArray = [...chartData];
            if (idx !== -1) {
                updatedChartDataArray[idx] = clearxpath(cloneDeep(updatedChartData));
            } else {
                updatedChartDataArray.push(clearxpath(cloneDeep(updatedChartData)));
            }
            onChartDataChange(updatedChartDataArray);

            // Also update the local state for immediate UI feedback
            handleUpdate(updatedChartData);

            // Reset the flag after a short delay to allow the update to complete
            setTimeout(() => {
                pinnedFilterUpdateRef.current = false;
            }, 100);
        } else {
            // Reset flag even if update failed
            pinnedFilterUpdateRef.current = false;
        }

        // Also update the main quick filters for backward compatibility
        handleQuickFilterChange(uniqueId, value);
    };

    const handleUnpinFilter = (uniqueId) => {
        const currentChartName = data?.chart_name;
        if (!currentChartName) return;

        // Update current display
        setPinnedFilters(prev => {
            const newFilters = prev.filter(pin => pin.uniqueId !== uniqueId);
            return newFilters;
        });

        // Update chart-specific storage
        setPinnedFiltersByChart(prev => ({
            ...prev,
            [currentChartName]: (prev[currentChartName] || []).filter(pin => pin.uniqueId !== uniqueId)
        }));
    };

    const options = useMemo(() => getChartOption(clearxpath(cloneDeep(chartOption))), [chartOption]);
    const chartQuickFilter = quickFilters.find((quickFilter) => quickFilter.chart_name === data?.chart_name);

    let filterDict = {};
    if (chartQuickFilter) {
        filterDict = chartQuickFilter.filters ? JSON.parse(chartQuickFilter.filters) : {};
    }

    return (
        <>
            <Box className={styles.container}>
                <Box className={styles.list_container}>
                    <Button color='warning' variant='contained' onClick={handleChartCreate}>
                        <Add fontSize='small' />
                        Add new chart
                    </Button>
                    <List>
                        {chartData.map((item, index) => {
                            if (chartEnableOverride.includes(item.chart_name)) return;
                            return (
                                <ListItem
                                    className={styles.list_item}
                                    key={index}
                                    selected={selectedIndex === index}
                                    disablePadding
                                    onClick={() => handleSelect(index)}
                                    onDoubleClick={() => handleDoubleClick(index)}>
                                    <ListItemButton>
                                        <ListItemText>{item.chart_name}</ListItemText>
                                    </ListItemButton>
                                    <Icon title='Delete' onClick={(e) => handleChartDelete(e, item.chart_name, index)}>
                                        <Delete fontSize='small' />
                                    </Icon>
                                </ListItem>
                            )
                        })}
                    </List>
                </Box>
                <Divider orientation='vertical' flexItem />
                <Box className={styles.chart_container}>
                    {/* Pinned Filters Section */}
                    {pinnedFilters.length > 0 && (
                        <Box className={styles.pinned_filters_container}>
                            {pinnedFilters.map((pin) => (
                                <QuickFilterPin
                                    key={pin.uniqueId}
                                    nodeKey={pin.key}
                                    uniqueId={pin.uniqueId}
                                    nodeTitle={pin.title}
                                    nodeValue={pin.value}
                                    nodeData={pin.nodeData}
                                    onValueChange={handlePinnedFilterChange}
                                    onUnpin={handleUnpinFilter}
                                />
                            ))}
                        </Box>
                    )}
                    <Box className={styles.chart}>
                        {storedChartObj.chart_name ? (
                            rows.length > 0 ? (
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
                            ) : (
                                <Box className={styles.no_data_message}>
                                    No Data Available
                                </Box>
                            )
                        ) : (
                            <Box className={styles.no_data_message}>
                                No Chart Selected
                            </Box>
                        )}
                    </Box>
                    {children}
                </Box>
            </Box>
            <FullScreenModal
                id={'chart-option-modal'}
                open={isChartOptionOpen}
                onClose={handleChartOptionClose}
            >
                <ModelCard>
                    <ModelCardHeader name={CHART_SCHEMA_NAME} >
                        <Icon name='save' title='save' onClick={handleSave}><Save fontSize='small' color='white' /></Icon>
                        <Icon name='close' title='close' onClick={handleChartOptionClose}><Close fontSize='small' color='white' /></Icon>
                    </ModelCardHeader>
                    <ModelCardContent>
                        <DataTree
                            projectSchema={schema}
                            modelName={CHART_SCHEMA_NAME}
                            updatedData={data}
                            storedData={storedChartObj}
                            subtree={null}
                            mode={mode}
                            xpath={null}
                            onUpdate={handleUpdate}
                            onUserChange={handleUserChange}
                            quickFilter={!isCreate ? filterDict : null}
                            onQuickFilterChange={handleQuickFilterChange}
                            onQuickFilterPin={handleQuickFilterPin}
                            onQuickFilterUnpin={handleUnpinFilter}
                            pinnedFilters={pinnedFilters}
                            treeLevel={4}
                            enableQuickFilterPin={true}
                        />
                    </ModelCardContent>
                </ModelCard>
                <Dialog
                    open={isConfirmPopupOpen}
                    onClose={handleConfirmClose}>
                    <DialogTitle>Save Changes</DialogTitle>
                    <DialogContent>
                        <DialogContentText>Do you want to save changes?</DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button color='error' variant='contained' onClick={handleConfirmClose} autoFocus>Discard</Button>
                        <Button color='success' variant='contained' onClick={handleSave} autoFocus>Save</Button>
                    </DialogActions>
                </Dialog>
            </FullScreenModal>
        </>
    )
}

export default ChartView;