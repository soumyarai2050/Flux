import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
// third-party package imports
import {
    Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText
} from '@mui/material';
import { cloneDeep, get, isEqual } from 'lodash';
import { Add, Close, Delete, Save, ContentCopy, Error } from '@mui/icons-material';
// project constants and common utility function imports
import { DATA_TYPES, MODES, API_ROOT_URL, MODEL_TYPES, DB_ID } from '../../../../constants';
import { addxpath, clearxpath } from '../../../../utils/core/dataAccess';
import { applyFilter, getChartFilterDict } from '../../../../utils/core/dataFiltering';
import {
    genChartDatasets, genMetaFilters, getChartOption, tooltipFormatter,
    updateChartDataObj, updateChartSchema, updatePartitionFldSchema
} from '../../../../utils/core/chartUtils';
import { generateObjectFromSchema, getModelSchema } from '../../../../utils/core/schemaUtils';
import { getIdFromAbbreviatedKey } from '../../../../utils/core/dataUtils';
import { getCollectionByName } from '../../../../utils/core/dataUtils';
// custom component imports
import Icon from '../../../ui/Icon';
import FullScreenModal from '../../../ui/Modal';
import EChart from '../EChart';
import styles from './ChartView.module.css';
import { useTheme } from '@emotion/react';
import DataTree from '../../trees/DataTree';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../../utility/cards';
import QuickFilterPin from '../../../controls/QuickFilterPin';
import ClipboardCopier from '../../../utility/ClipboardCopier';

const CHART_SCHEMA_NAME = 'chart_data';

// 🪟 Sliding Window Configuration - Controls memory management for time-series data
// Set to number (e.g., 10) for sliding window with that many points
// Set to null for unlimited data growth (no sliding window)

const SLIDING_WINDOW_SIZE = null;

function ChartView({
    chartData,
    chartRows,
    fieldsMetadata,
    modelType,
    abbreviation,
    onRowSelect,
    onReload,
    onChartDataChange,
    onModeToggle,
    mode,
    onChartSelect,
    selectedChartName,
    chartEnableOverride,
    onChartPointSelect,
    children,
    quickFilters = [],
    onQuickFiltersChange,
    selectedRowId,
    selectedRows = [],
    lastSelectedRowId
}) {
    // redux states
    const theme = useTheme();
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);

    // Core chart state
    const [storedChartObj, setStoredChartObj] = useState({});     // Original chart configuration from props
    const [updatedChartObj, setUpdatedChartObj] = useState({});  // Chart config with xpath for editing
    const [selectedIndex, setSelectedIndex] = useState(
        selectedChartName ? chartData.findIndex((o) => o.chart_name === selectedChartName) : null
    );

    // UI state
    const [isChartOptionOpen, setIsChartOptionOpen] = useState(false);
    const [isConfirmPopupOpen, setIsConfirmPopupOpen] = useState(false);
    const [isValidationErrorOpen, setIsValidationErrorOpen] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);
    const [isCreate, setIsCreate] = useState(false);
    const [data, setData] = useState({});                        // Current editing data

    // Chart rendering state
    const [chartOption, setChartOption] = useState({});          // Final ECharts configuration
    const [datasets, setDatasets] = useState([]);               // Chart datasets for rendering
    const [rows, setRows] = useState(chartRows);                // Filtered chart data rows

    // Time-series specific state
    const [tsData, setTsData] = useState({});                    // Collected time-series data from WebSockets
    const [queryDict, setQueryDict] = useState({});             // Maps series index to query configuration

    // Update counters for controlling cascading effects
    const [chartUpdateCounter, setChartUpdateCounter] = useState(0);
    const [datasetUpdateCounter, setDatasetUpdateCounter] = useState(0);
    const [reloadCounter, setReloadCounter] = useState(0);

    // Schema and filter state
    const [schema, setSchema] = useState(
        updateChartSchema(projectSchema, fieldsMetadata, modelType === MODEL_TYPES.ABBREVIATION_MERGE)
    );
    const [selectedData, setSelectedData] = useState([]);
    const [selectedSeriesIdx, setSelectedSeriesIdx] = useState(null);

    // Pinned filters state
    const [pinnedFilters, setPinnedFilters] = useState([]);
    const [pinnedFiltersByChart, setPinnedFiltersByChart] = useState({});
    const [textToCopy, setTextToCopy] = useState('');
    const pinnedFilterUpdateRef = useRef(false);

    // =============================================
    // SPECIALIZED CHART DATA WORKER SYSTEM
    // =============================================

    /**
     * Single specialized worker for all chart data management
     * Handles all WebSocket connections, data merging, and state management
     * Provides O(1) performance with Map-based data structures
     */
    const chartDataWorkerRef = useRef(null);
    const webSocketWorkersRef = useRef(new Map()); // fingerprint -> WebSocket worker
    const registeredStreamsRef = useRef(new Set()); // Track registered streams

    /**
     * Initialize the specialized chart data worker
     * This worker handles all time-series data processing and state management
     */
    const initializeChartDataWorker = useCallback(() => {
        if (chartDataWorkerRef.current) {
            return chartDataWorkerRef.current;
        }

        const worker = new Worker(new URL('../../../../workers/chart-data.worker.js', import.meta.url));

        // Handle messages from the specialized worker
        worker.onmessage = (event) => {
            const { type, data } = event.data;

            switch (type) {
                case 'AGGREGATED_DATA':
                    // Full replacement for aggregated data
                    if (mode === MODES.READ && data) {
                        setTsData(prevData => {
                            return data;
                        });
                    }
                    break;

                case 'INCREMENTAL_UPDATE':
                    // Merge incremental updates with existing data
                    if (mode === MODES.READ && data) {
                        setTsData(prevData => {

                            // Merge new data with existing data
                            const mergedData = { ...prevData, ...data };

                            return mergedData;
                        });
                    }
                    break;

                case 'STREAM_REGISTERED':
                    break;
                case 'STREAM_UNREGISTERED':
                    break;

                case 'ERROR':
                    break;

                case 'MEMORY_REPORT':
                    break;

                default:
                //for debugging point of view
            }
        };

        worker.onerror = (error) => {
            console.error('Chart Data Worker Error:', error);
        };

        chartDataWorkerRef.current = worker;
        return worker;
    }, [mode]);

    /**
     * Creates a stable fingerprint for a WebSocket connection
     */
    const createQueryFingerprint = useCallback((query, metaFilterDict, rootUrl) => {
        if (!query) return null;

        // Build parameter string from meta filters
        let paramStr = '';
        for (const key in metaFilterDict) {
            if (paramStr) {
                paramStr += `&${key}=${metaFilterDict[key]}`;
            } else {
                paramStr = `${key}=${metaFilterDict[key]}`;
            }
        }

        // Create unique fingerprint: URL + query + parameters
        return `${rootUrl}/ws-query-${query.name}?${paramStr}`;
    }, []);

    /**
     * Extracts worker information for a chart series, handling:
     * - Collection mapping validation
     * - Root URL determination (can be external service)
     * - Query extraction from queryDict
     * 
     * Returns null if series doesn't support time-series data
     */

    const getSeriesWorkerInfo = useCallback((series, index) => {
        const collection = getCollectionByName(
            fieldsMetadata,
            series.encode.y,
            modelType === MODEL_TYPES.ABBREVIATION_MERGE
        );

        // Only process series that have time-series mapping
        if (!collection.hasOwnProperty('mapping_src')) {
            return null;
        }

        // Determine root URL - may be external service based on mapping model
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
        if (!query) {
            return null;
        }

        return { collection, rootUrl, query };
    }, [fieldsMetadata, modelType, projectSchema, queryDict]);

    /**
     * Create a WebSocket worker for a specific stream
     * This connects to the WebSocket and forwards data to the specialized chart data worker
     */
    const createWebSocketWorker = useCallback((fingerprint, query) => {

        // Create WebSocket connection
        const wsUrl = fingerprint.replace('http', 'ws');
        const socket = new WebSocket(wsUrl);

        // Create WebSocket processing worker
        const worker = new Worker(new URL('../../../../workers/websocket-update.worker.js', import.meta.url));

        // Forward WebSocket messages to processing worker
        socket.onmessage = (event) => {
            worker.postMessage({
                messages: [event.data],
                storedArray: [],
                uiLimit: null,
                isAlertModel: false
            });
        };

        // Forward processed data to specialized chart data worker
        worker.onmessage = (event) => {
            const processedData = event.data;

            if (chartDataWorkerRef.current && Array.isArray(processedData) && processedData.length > 0) {
                chartDataWorkerRef.current.postMessage({
                    type: 'UPDATE_DATA',
                    fingerprint,
                    data: processedData
                });
            }
        };

        // socket.onopen = () => {
        //     console.log(`✅ [ChartView] WebSocket connected: ${fingerprint}`);
        // };

        socket.onerror = (error) => {
            console.error(`❌ [ChartView] WebSocket error for ${fingerprint}:`, error);
        };

        // socket.onclose = (event) => {
        //     console.log(`🗑️ [ChartView] WebSocket closed for ${fingerprint}:`, event.code, event.reason);
        // };

        worker.onerror = (error) => {
            console.error(`❌ [ChartView] WebSocket worker error for ${fingerprint}:`, error);
        };

        return { socket, worker };
    }, []);

    /**
     * Generates all required stream configurations for current chart configuration
     */
    const generateStreamConfigurations = useCallback((metaFilters) => {
        const configurations = new Map();

        storedChartObj.series?.forEach((series, index) => {
            const workerInfo = getSeriesWorkerInfo(series, index);
            if (!workerInfo) return;

            const { query, rootUrl } = workerInfo;

            // Each meta filter creates a separate stream configuration
            metaFilters.forEach(metaFilterDict => {
                const fingerprint = createQueryFingerprint(query, metaFilterDict, rootUrl);
                if (fingerprint) {
                    configurations.set(fingerprint, {
                        index,
                        query,
                        rootUrl,
                        metaFilterDict,
                        queryName: query.name
                    });
                }
            });
        });

        return configurations;
    }, [storedChartObj.series, getSeriesWorkerInfo, createQueryFingerprint]);

    /**
     * Register a new stream with the specialized chart data worker
     */
    const registerStream = useCallback((fingerprint, config) => {
        const chartWorker = initializeChartDataWorker();

        chartWorker.postMessage({
            type: 'REGISTER_STREAM',
            fingerprint,
            config: {
                queryName: config.queryName,
                rootUrl: config.rootUrl,
                metaFilterDict: config.metaFilterDict,
                slidingWindowSize: SLIDING_WINDOW_SIZE // Pass from parent
            }
        });

        registeredStreamsRef.current.add(fingerprint);
    }, [initializeChartDataWorker]);

    /**
     * Unregister a stream from the specialized chart data worker
     */
    const unregisterStream = useCallback((fingerprint) => {
        if (chartDataWorkerRef.current) {
            chartDataWorkerRef.current.postMessage({
                type: 'UNREGISTER_STREAM',
                fingerprint
            });
        }

        registeredStreamsRef.current.delete(fingerprint);

        // Cleanup WebSocket worker
        const wsWorker = webSocketWorkersRef.current.get(fingerprint);
        if (wsWorker) {
            const { socket, worker } = wsWorker;
            if (socket) socket.close();
            if (worker) worker.terminate();
            webSocketWorkersRef.current.delete(fingerprint);
        }
    }, []);

    /**
     * Request aggregated data from the specialized chart data worker
     */
    const requestAggregatedData = useCallback(() => {
        if (chartDataWorkerRef.current) {
            chartDataWorkerRef.current.postMessage({
                type: 'GET_AGGREGATED_DATA'
            });
        }
    }, []);

    /**
     * Update sliding window configuration for the worker
     * This allows runtime configuration changes without worker restart
     */
    const updateSlidingWindowConfig = useCallback((newSize) => {
        if (chartDataWorkerRef.current) {
            console.log(`🔧 [ChartView] Updating sliding window size: ${SLIDING_WINDOW_SIZE} -> ${newSize}`);
            chartDataWorkerRef.current.postMessage({
                type: 'UPDATE_GLOBAL_SLIDING_WINDOW',
                data: { windowSize: newSize }
            });
        }
    }, []);

    // =============================================
    // SPECIALIZED CHART DATA WORKER MANAGEMENT
    // =============================================

    /**
     * Main effect for managing the specialized chart data worker and streams.
     * This replaces the old multiple-worker system with a single, efficient worker.
     * 
     * New Flow:
     * 1. Initialize specialized chart data worker
     * 2. Generate stream configurations for all required data
     * 3. Register/unregister streams as needed
     * 4. Let the specialized worker handle all data processing
     */

    useEffect(() => {
        // Early exit: cleanup everything if not time-series chart
        if (!storedChartObj.series || !storedChartObj.time_series) {
            // Cleanup all WebSocket workers
            webSocketWorkersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            webSocketWorkersRef.current.clear();
            registeredStreamsRef.current.clear();

            // Clear all data in specialized worker
            if (chartDataWorkerRef.current) {
                chartDataWorkerRef.current.postMessage({ type: 'CLEAR_ALL_DATA' });
            }

            setTsData({});
            setDatasets([]);
            return;
        }

        // Early exit: wait for queryDict to be populated for all time-series
        const expectedQueryCount = storedChartObj.series.filter(series => {
            if (!series.encode?.y) return false;
            const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
            return collection && collection.hasOwnProperty('mapping_src');
        }).length;

        const currentQueryCount = Object.keys(queryDict).length;

        if (currentQueryCount < expectedQueryCount) {
            return;
        }

        // Get chart filters and generate meta filters
        const filterDict = getChartFilterDict(storedChartObj.filters);
        if (Object.keys(filterDict).length === 0) return;

        // Generate meta filters for all filter fields
        let metaFilters = [];
        Object.keys(filterDict).forEach(filterFld => {
            const filtersForField = genMetaFilters(
                rows,
                fieldsMetadata,
                filterDict,
                filterFld,
                modelType === MODEL_TYPES.ABBREVIATION_MERGE
            );
            metaFilters = metaFilters.concat(filtersForField);
        });

        // Generate stream configurations
        const streamConfigurations = generateStreamConfigurations(metaFilters);

        // Initialize the specialized worker
        initializeChartDataWorker();

        // Determine which streams need to be added/removed
        const currentStreams = new Set(registeredStreamsRef.current);
        const newStreams = new Set(streamConfigurations.keys());

        const streamsChanged = currentStreams.size !== newStreams.size ||
            Array.from(newStreams).some(fp => !currentStreams.has(fp));

        // Early exit: no changes needed
        if (!streamsChanged) {
            return;
        }

        // Identify streams being removed and added
        const removedStreams = Array.from(currentStreams).filter(fp => !newStreams.has(fp));
        const addedStreams = Array.from(newStreams).filter(fp => !currentStreams.has(fp));

        // Unregister removed streams
        removedStreams.forEach(fingerprint => {
            unregisterStream(fingerprint);
        });

        // Register and create WebSocket workers for new streams
        addedStreams.forEach(fingerprint => {
            const config = streamConfigurations.get(fingerprint);
            if (config) {

                // Register stream with specialized worker
                registerStream(fingerprint, config);

                // Create WebSocket worker for this stream
                const wsWorker = createWebSocketWorker(fingerprint, config.query);
                webSocketWorkersRef.current.set(fingerprint, wsWorker);
            }
        });

    }, [
        storedChartObj.series,
        storedChartObj.time_series,
        storedChartObj.filters,
        queryDict,
        projectSchema,
        fieldsMetadata,
        modelType,
        rows,
        mode,
        generateStreamConfigurations,
        initializeChartDataWorker,
        registerStream,
        unregisterStream,
        createWebSocketWorker
    ]);

    // Component unmount cleanup - ensure all workers are properly terminated
    useEffect(() => {
        return () => {
            // Cleanup all WebSocket workers
            webSocketWorkersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            webSocketWorkersRef.current.clear();

            // Cleanup specialized chart data worker
            if (chartDataWorkerRef.current) {
                chartDataWorkerRef.current.terminate();
                chartDataWorkerRef.current = null;
            }

            registeredStreamsRef.current.clear();
        };
    }, []);

    // =============================================
    // EXISTING CHARTVIEW LOGIC
    // =============================================

    useEffect(() => {
        const updatedIndex = selectedChartName ? chartData.findIndex((o) => o.chart_name === selectedChartName) : null;
        setSelectedIndex(updatedIndex);
    }, [selectedChartName, chartEnableOverride])

    // Sync local selectedData state with props from parent
    useEffect(() => {
        if (selectedRows && selectedRows.length > 0) {
            setSelectedData(prevData => {
                if (!isEqual(prevData, selectedRows)) {
                    return selectedRows;
                }
                return prevData;
            });
        } else {
            setSelectedData(prevData => {
                if (prevData.length > 0) {
                    return [];
                }
                return prevData;
            });
        }
    }, [selectedRows])

    useEffect(() => {
        // update the local row dataset on update from parent
        if (mode === MODES.READ) {
            let updatedRows;
            if (storedChartObj.filters?.length > 0) {

                //Use getChartFilterDict for both time-series and non-time-series charts
                const filterDict = getChartFilterDict(storedChartObj.filters);

                // Convert to the format expected by applyFilter
                const updatedFilters = Object.entries(filterDict).map(([fld_name, fld_value]) => ({
                    column_name: fld_name,
                    filtered_values: fld_value
                }));

                updatedRows = applyFilter(chartRows, updatedFilters);
            } else {
                updatedRows = chartRows;
            }
            setRows(updatedRows);
        } else {  // mode is EDIT
            setIsChartOptionOpen(true);
        }
    }, [chartRows, mode, storedChartObj.filters])

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
            let updatedSchema = handleDynamicSchemaUpdate(selectedChartOption);
            // updatedSchema = updatePartitionFldSchema(schema, selectedChartOption);
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
        }
    }, [chartUpdateCounter])

    useEffect(() => {
        // Transform unique-key tsData back to query-based structure for chart rendering
        // This preserves compatibility with existing chart rendering logic
        const queryBasedTsData = {};

        Object.keys(tsData).forEach(uniqueKey => {
            if (uniqueKey.includes('__')) {
                const [queryName] = uniqueKey.split('__');
                if (!queryBasedTsData[queryName]) {
                    queryBasedTsData[queryName] = [];
                }
                queryBasedTsData[queryName] = queryBasedTsData[queryName].concat(tsData[uniqueKey]);
            }
        });


        const updatedDatasets = genChartDatasets(rows, queryBasedTsData, storedChartObj, queryDict, fieldsMetadata, modelType === MODEL_TYPES.ABBREVIATION_MERGE);

        setDatasets(updatedDatasets);
        setDatasetUpdateCounter(prevCount => prevCount + 1);
    }, [chartUpdateCounter, rows, tsData, queryDict])

    useEffect(() => {
        if (storedChartObj.series) {
            const updatedObj = addxpath(cloneDeep(storedChartObj));
            const updatedChartOption = updateChartDataObj(updatedObj, fieldsMetadata, rows, datasets, modelType === MODEL_TYPES.ABBREVIATION_MERGE, schemaCollections, queryDict);
            setChartOption(updatedChartOption);
        }
    }, [datasetUpdateCounter, queryDict])

    const handleSelectDataChange = (e, dataId, seriesIdx) => {
        if (storedChartObj.time_series) return;

        let updatedSelectedData;
        if (e.ctrlKey && selectedSeriesIdx === seriesIdx) {
            if (selectedData.includes(dataId)) {
                updatedSelectedData = selectedData.filter((item) => item !== dataId);
            } else {
                updatedSelectedData = [...selectedData, dataId];
            }
        } else {
            updatedSelectedData = [dataId];
        }
        setSelectedData(updatedSelectedData);
        setSelectedSeriesIdx(seriesIdx);

        // Determine most recent selection
        const mostRecentItemId = updatedSelectedData.length > 0
            ? updatedSelectedData[updatedSelectedData.length - 1]
            : null;

        // Call legacy onRowSelect for backward compatibility
        if (mostRecentItemId) {
            onRowSelect(mostRecentItemId);
        } else {
            onRowSelect(null);
        }

        // Call new multiselect handler with both selected IDs and most recent
        onChartPointSelect(updatedSelectedData, mostRecentItemId);
    }

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
        setDatasetUpdateCounter(0);

        // Clear all data in specialized chart data worker
        if (chartDataWorkerRef.current) {
            chartDataWorkerRef.current.postMessage({ type: 'CLEAR_ALL_DATA' });
        }
    }

    const validateChartData = (chartData) => {
        const errors = [];

        // Check for required chart_name field
        if (!chartData.chart_name || chartData.chart_name.trim() === '') {
            errors.push('Chart name is required');
        }

        // Check series validation
        if (chartData.series && chartData.series.length > 0) {
            chartData.series.forEach((series, index) => {
                // Check for required type field
                if (!series.type || series.type.trim() === '') {
                    errors.push(`Series ${index + 1}: Type is required`);
                } else if (series.type === 'CHART_TYPE_UNSPECIFIED') {
                    errors.push(`Series ${index + 1}: Please select a valid chart type`);
                }

                // Check for required encode field
                if (!series.encode) {
                    errors.push(`Series ${index + 1}: Encode is required`);
                } else {
                    // Check for required y field in encode
                    if (!series.encode.y || series.encode.y.trim() === '') {
                        errors.push(`Series ${index + 1}: Y axis field is required`);
                    }

                    // Check for required x field in encode (conditional)
                    // x is required unless it's time-series and field on y-axis has projection
                    if (!chartData.time_series) {
                        // If not time-series, x is required
                        if (!series.encode.x || series.encode.x.trim() === '') {
                            errors.push(`Series ${index + 1}: X axis field is required when time-series is disabled`);
                        }
                    }
                }
            });
        } else {
            errors.push('At least one series is required');
        }

        // Check filters validation
        if (chartData.filters && chartData.filters.length > 0) {
            chartData.filters.forEach((filter, index) => {
                // Check for required fld_name field
                if (!filter.fld_name || filter.fld_name.trim() === '') {
                    errors.push(`Filter ${index + 1}: Field name is required`);
                }

                // Check for required fld_value field
                if (!filter.fld_value || (Array.isArray(filter.fld_value) && filter.fld_value.length === 0)) {
                    errors.push(`Filter ${index + 1}: Field value is required`);
                }
            });
        }

        return errors;
    }

    const handleSave = () => {
        const updatedObj = clearxpath(cloneDeep(data));

        // Validate the chart data before saving
        const errors = validateChartData(updatedObj);
        if (errors.length > 0) {
            setValidationErrors(errors);
            setIsValidationErrorOpen(true);
            return; // Don't save if validation fails
        }

        onModeToggle();
        const wasCreating = isCreate;
        setIsCreate(false);
        setIsChartOptionOpen(false);
        setIsConfirmPopupOpen(false);
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

    const handleValidationErrorClose = () => {
        setIsValidationErrorOpen(false);
        setValidationErrors([]);
    }

    const handleReload = () => {
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
        onModeToggle();
        setIsChartOptionOpen(true);
    }

    const handleUserChange = () => {
        // Placeholder for user change handling
    }

    const handleUpdate = (updatedData) => {
        if (updatedData.time_series) {
            updatedData.partition_fld = null;
            updatedData.series?.forEach((series) => {
                series.encode.x = null;
            })
        } else {
            updatedData.filters = [];
        }
        setData(updatedData);

        const isFromPinnedFilterChange = pinnedFilterUpdateRef.current;

        if (!isFromPinnedFilterChange) {
            syncPinnedFiltersWithData(updatedData);
        }

        const updatedSchema = handleDynamicSchemaUpdate(updatedData);
        setSchema(updatedSchema);
    }

    const handleDynamicSchemaUpdate = (chartOptionObj) => {
        const updatedSchema = cloneDeep(schema);
        const chartDataSchema = getModelSchema('chart_data', updatedSchema);
        const chartEncodeSchema = getModelSchema('chart_encode', updatedSchema);

        if (chartOptionObj.time_series) {
            chartDataSchema.properties.filters.server_populate = false;
            chartEncodeSchema.auto_complete = 'x:FldList,y:ProjFldList';
            chartEncodeSchema.required = ['y'];
        } else {
            chartDataSchema.properties.filters.server_populate = true;
            chartEncodeSchema.auto_complete = 'x:FldList,y:FldList';
            chartEncodeSchema.required = ['x', 'y'];
        }
        return updatedSchema;
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

        setPinnedFiltersByChart(prev => {
            const newObj = { ...prev };
            delete newObj[chartName];
            return newObj;
        });

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

    // =============================================
    // PINNED FILTER MANAGEMENT (extracted to reduce duplication)
    // =============================================

    const handleQuickFilterPin = (key, title, currentValue, nodeData) => {
        const uniqueId = nodeData.dataxpath || key;
        const currentChartName = data?.chart_name;
        const existingPin = pinnedFilters.find(pin => pin.uniqueId === uniqueId);

        if (!existingPin && currentChartName) {
            const currentChartValue = getCurrentChartFieldValue(key, nodeData) || currentValue || getDefaultValueForField(nodeData);

            const newPin = {
                key,
                uniqueId,
                title,
                value: currentChartValue,
                nodeData: nodeData
            };

            const updatedFilters = [...pinnedFilters, newPin];

            // Update local state
            setPinnedFiltersByChart(prev => ({
                ...prev,
                [currentChartName]: updatedFilters
            }));
            setPinnedFilters(updatedFilters);

            // Save to quickFilters for persistence
            savePinnedFiltersToQuickFilters(updatedFilters, currentChartName);
        }
    };

    /**
     * Utility function to navigate object path using xpath notation
     * Handles both object properties and array indices like 'series[0].encode.y'
     */
    const navigateObjectPath = useCallback((obj, pathParts) => {
        let target = obj;

        for (const part of pathParts) {
            if (part.includes('[') && part.includes(']')) {
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
    }, []);

    const getCurrentChartFieldValue = useCallback((key, nodeData) => {
        if (!data || !nodeData || !nodeData.dataxpath) return null;

        const dataxpath = nodeData.dataxpath;
        const pathParts = dataxpath.split('.');
        return navigateObjectPath(data, pathParts);
    }, [data, navigateObjectPath]);

    const getDefaultValueForField = useCallback((nodeData) => {
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
    }, []);

    const syncPinnedFiltersWithData = useCallback((updatedData) => {
        setPinnedFilters(prev => {
            if (prev.length === 0) return prev;

            const updatedPins = prev.map(pin => {
                const currentValue = navigateObjectPath(updatedData, pin.nodeData.dataxpath?.split('.') || []);

                if (currentValue !== undefined && currentValue !== pin.value) {
                    return { ...pin, value: currentValue };
                }
                return pin;
            });

            const hasChanges = updatedPins.some((pin, index) => pin.value !== prev[index].value);
            return hasChanges ? updatedPins : prev;
        });
    }, [navigateObjectPath]);

    //handlePinnedFilterChange : updates local state, chartData and calls the function savePinnedFiltersToQuickFilters(updatedFilters, currentChartName);
    //this doesnt change the pin list , that function is handleQuickFilterPin 

    const handlePinnedFilterChange = (uniqueId, value) => {
        const currentChartName = data?.chart_name;
        if (!currentChartName) {
            return;
        }

        pinnedFilterUpdateRef.current = true;

        setPinnedFilters(prev => {
            if (!Array.isArray(prev)) {
                console.warn('⚠️ pinnedFilters is not an array:', prev);
                return [];
            }
            const updated = prev.map(pin =>
                pin.uniqueId === uniqueId ? { ...pin, value } : pin
            );
            return updated;
        });

        setPinnedFiltersByChart(prev => {
            const updated = {
                ...prev,
                [currentChartName]: (prev[currentChartName] || []).map(pin =>
                    pin.uniqueId === uniqueId ? { ...pin, value } : pin
                )
            };
            return updated;
        });

        const updatedChartData = cloneDeep(data);
        const pinnedFilter = pinnedFilters.find(pin => pin.uniqueId === uniqueId);

        if (pinnedFilter && pinnedFilter.nodeData && pinnedFilter.nodeData.dataxpath) {
            const dataxpath = pinnedFilter.nodeData.dataxpath;
            const pathParts = dataxpath.split('.');
            let target = updatedChartData;

            // Navigate to the parent object
            for (let i = 0; i < pathParts.length - 1; i++) {
                const part = pathParts[i];
                if (part.includes('[') && part.includes(']')) {
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

        // Save updated pinned filters to quickFilters for persistence
        if (Array.isArray(pinnedFilters)) {
            const updatedFilters = pinnedFilters.map(pin =>
                pin.uniqueId === uniqueId ? { ...pin, value } : pin
            );
            savePinnedFiltersToQuickFilters(updatedFilters, currentChartName);
        }
    };

    const handleUnpinFilter = (uniqueId) => {
        const currentChartName = data?.chart_name;
        if (!currentChartName) return;

        // Calculate the new filters after removal
        if (!Array.isArray(pinnedFilters)) {
            console.warn('⚠️ pinnedFilters is not an array in handleUnpinFilter:', pinnedFilters);
            return;
        }

        const updatedFilters = pinnedFilters.filter(pin => pin.uniqueId !== uniqueId);

        // Update current display
        setPinnedFilters(updatedFilters);

        // Update chart-specific storage
        setPinnedFiltersByChart(prev => ({
            ...prev,
            [currentChartName]: updatedFilters
        }));

        // Save updated pinned filters to quickFilters for persistence
        savePinnedFiltersToQuickFilters(updatedFilters, currentChartName);
    };

    const handleCopyChartName = (e, chartName) => {
        e.stopPropagation();
        setTextToCopy(chartName);
    };

    // =============================================
    // MEMOIZED VALUES FOR PERFORMANCE
    // =============================================

    const options = useMemo(() => getChartOption(clearxpath(cloneDeep(chartOption))), [chartOption]);

    const chartQuickFilter = useMemo(() => {
        if (!Array.isArray(quickFilters)) {
            console.warn('⚠️ quickFilters is not an array:', quickFilters);
            return undefined;
        }
        return quickFilters.find((quickFilter) => quickFilter.chart_name === data?.chart_name);
    }, [quickFilters, data?.chart_name]);

    // Initialize pinned filters from quickFilters when component mounts or chart changes
    useEffect(() => {


        if (data?.chart_name && chartQuickFilter?.filters) {
            try {
                const deserializedFilters = JSON.parse(chartQuickFilter.filters);

                // Ensure we're setting an array
                if (Array.isArray(deserializedFilters)) {
                    setPinnedFilters(deserializedFilters);
                } else {
                    setPinnedFilters([]);
                }

                // Update chart-specific storage to sync with the rest of the component
                if (Array.isArray(deserializedFilters)) {
                    setPinnedFiltersByChart(prev => ({
                        ...prev,
                        [data.chart_name]: deserializedFilters
                    }));
                }
            } catch (error) {
                console.warn('⚠️ Failed to parse quickFilters.filters:', error);
                setPinnedFilters([]);
            }
        } else if (data?.chart_name) {
            // No saved filters for this chart
            setPinnedFilters([]);
        }
    }, [data?.chart_name, chartQuickFilter?.filters]);

    // Helper function to save pinned filters to quickFilters
    const savePinnedFiltersToQuickFilters = useCallback((updatedFilters, chartName) => {
        if (!onQuickFiltersChange || !chartName) {
            console.warn('⚠️ Cannot save pinned filters - missing onQuickFiltersChange or chartName');
            return;
        }

        if (!Array.isArray(updatedFilters)) {
            console.warn('⚠️ updatedFilters is not an array:', updatedFilters);
            return;
        }



        // Create updated quickFilters array
        const currentQuickFilters = Array.isArray(quickFilters) ? quickFilters : [];
        const updatedQuickFilters = [...currentQuickFilters];
        const existingIndex = updatedQuickFilters.findIndex(qf => qf.chart_name === chartName);

        const filtersString = JSON.stringify(updatedFilters);

        if (existingIndex >= 0) {
            // Update existing entry
            updatedQuickFilters[existingIndex] = {
                ...updatedQuickFilters[existingIndex],
                filters: filtersString
            };
        } else {
            // Create new entry
            updatedQuickFilters.push({
                chart_name: chartName,
                filters: filtersString
            });
        }

        onQuickFiltersChange(updatedQuickFilters);
    }, [quickFilters, onQuickFiltersChange]);

    const filterDict = useMemo(() => {
        if (chartQuickFilter) {
            return chartQuickFilter.filters ? JSON.parse(chartQuickFilter.filters) : {};
        }
        return {};
    }, [chartQuickFilter]);

    return (
        <>
            <ClipboardCopier text={textToCopy} />
            <Box className={styles.container}>
                <Box className={styles.list_container}>
                    <Button color='warning' variant='contained' onClick={handleChartCreate}>
                        <Add fontSize='small' />
                        Add new chart
                    </Button>
                    <List>
                        {chartData.map((item, index) => {
                            if (chartEnableOverride.includes(item.chart_name)) return null;
                            return (
                                <ListItem
                                    className={styles.list_item}
                                    key={index}
                                    selected={selectedIndex === index}
                                    disablePadding
                                    onClick={() => handleSelect(index)}
                                    sx={{ color: item.time_series ? 'var(--blue-info)' : undefined }}
                                    onDoubleClick={() => handleDoubleClick(index)}>
                                    <ListItemButton>
                                        <ListItemText>{item.chart_name}</ListItemText>
                                    </ListItemButton>
                                    <Icon title='Copy chart name' onClick={(e) => handleCopyChartName(e, item.chart_name)}>
                                        <ContentCopy fontSize='small' />
                                    </Icon>
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
                                    selectedSeriesIdx={selectedSeriesIdx ?? 0}
                                    selectedData={selectedData}
                                    activeDataId={lastSelectedRowId || selectedRowId}
                                    onSelectDataChange={handleSelectDataChange}
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
                <Dialog
                    open={isValidationErrorOpen}
                    onClose={handleValidationErrorClose}
                    maxWidth="sm"
                    fullWidth>
                    <DialogTitle sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        color: 'error.main',
                        borderBottom: '1px solid',
                        borderColor: 'divider'
                    }}>
                        <Error color="error" />
                        Validation Error
                    </DialogTitle>
                    <DialogContent sx={{ pt: 2 }}>
                        <DialogContentText sx={{ mb: 2, fontWeight: 500 }}>
                            Please fix the following issues before saving:
                        </DialogContentText>
                        <Box component="ul" sx={{
                            margin: 0,
                            padding: 0,
                            listStyle: 'none'
                        }}>
                            {validationErrors.map((error, index) => (
                                <Box component="li" key={index} sx={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: 1,
                                    mb: 1.5,
                                    p: 1,
                                    borderRadius: 1,
                                    bgcolor: 'error.lighter',
                                    border: '1px solid',
                                    borderColor: 'error.light'
                                }}>
                                    <Error
                                        color="error"
                                        fontSize="small"
                                        sx={{ mt: 0.25, flexShrink: 0 }}
                                    />
                                    <Box sx={{
                                        color: 'error.dark',
                                        fontSize: '0.875rem',
                                        lineHeight: 1.4
                                    }}>
                                        {error}
                                    </Box>
                                </Box>
                            ))}
                        </Box>
                    </DialogContent>
                    <DialogActions sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Button
                            color='primary'
                            variant='contained'
                            onClick={handleValidationErrorClose}
                            autoFocus
                            sx={{ minWidth: '100px' }}
                        >
                            OK
                        </Button>
                    </DialogActions>
                </Dialog>
            </FullScreenModal>
        </>
    )
}

export default ChartView;