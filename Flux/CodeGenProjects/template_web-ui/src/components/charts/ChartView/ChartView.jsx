import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
// third-party package imports
import {
    Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText
} from '@mui/material';
import { cloneDeep, get, isEqual } from 'lodash';
import { Add, Close, Delete, Save, ContentCopy, Error } from '@mui/icons-material';
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
import ClipboardCopier from '../../ClipboardCopier';

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
    // WEBSOCKET WORKER MANAGEMENT SYSTEM
    // =============================================

    /**
     * Refs for stable worker management across re-renders
     * - workersRef: Map of fingerprint -> {worker, socket, queryName}
     * - currentQueriesRef: Tracks current active query fingerprints for comparison
     */
    const workersRef = useRef(new Map());
    const currentQueriesRef = useRef(new Map());

    /**
     * Creates a stable fingerprint for a WebSocket connection based on:
     * - Root URL (can vary based on connection details)
     * - Query name (identifies the data stream)
     * - Meta filter parameters (affects data filtering)
     * 
     * This ensures each unique combination gets its own worker/socket
     */

    const createQueryFingerprint = useCallback((seriesIndex, query, metaFilterDict, rootUrl) => {
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
     * Generates all required worker fingerprints for current chart configuration
     * Each series can generate multiple fingerprints based on meta filters
     * 
     * Returns Map of fingerprint -> {index, query, rootUrl, metaFilterDict}
     */
    const generateAllFingerprints = useCallback((metaFilters) => {
        const fingerprints = new Map();

        storedChartObj.series?.forEach((series, index) => {
            const workerInfo = getSeriesWorkerInfo(series, index);
            if (!workerInfo) return;

            const { query, rootUrl } = workerInfo;

            // Each meta filter creates a separate worker/connection
            metaFilters.forEach(metaFilterDict => {
                const fingerprint = createQueryFingerprint(index, query, metaFilterDict, rootUrl);
                if (fingerprint) {
                    fingerprints.set(fingerprint, { index, query, rootUrl, metaFilterDict });
                }
            });
        });

        return fingerprints;
    }, [storedChartObj.series, getSeriesWorkerInfo, createQueryFingerprint]);

    /**
     * Creates a new WebSocket worker for a specific fingerprint
     * Sets up the data flow: WebSocket -> Worker -> React State
     */
    const createWorker = useCallback((fingerprint, query) => {

        // Create worker for data processing
        const worker = new Worker(new URL('../../../workers/websocket-update.worker.js', import.meta.url));

        // Create WebSocket connection (convert http URL to ws)
        const wsUrl = fingerprint.replace('http', 'ws');
        const socket = new WebSocket(wsUrl);

        // Forward WebSocket messages to worker for processing
        socket.onmessage = (event) => {
            worker.postMessage({
                messages: [event.data],
                storedArray: [],
                uiLimit: null,
                isAlertModel: false
            });
        };

        // Handle processed data from worker
        worker.onmessage = (event) => {
            const processedData = event.data;

            // Only update state when in read mode and data is valid
            if (mode === MODES.READ && processedData && Array.isArray(processedData)) {
                setTsData(prevTsData => {
                    const updatedTsData = { ...prevTsData };

                    // Create a unique key that combines query name and fingerprint
                    const uniqueKey = `${query.name}__${fingerprint}`;

                    // Append new data to existing query data or create new entry
                    if (updatedTsData[uniqueKey]) {
                        updatedTsData[uniqueKey] = [...updatedTsData[uniqueKey], ...processedData];
                    } else {
                        updatedTsData[uniqueKey] = processedData;
                    }

                    return updatedTsData;
                });
            }
        };

        // Store worker reference for cleanup
        workersRef.current.set(fingerprint, { socket, worker, queryName: query.name });
    }, [mode]);

    /**
     * Cleans up a specific worker and its WebSocket connection
     */
    const cleanupWorker = useCallback((fingerprint) => {
        const workerInfo = workersRef.current.get(fingerprint);
        if (workerInfo) {
            const { socket, worker } = workerInfo;

            if (socket) socket.close();
            if (worker) worker.terminate();
            workersRef.current.delete(fingerprint);
        }
    }, []);

    // =============================================
    // MAIN WORKER MANAGEMENT EFFECT
    // =============================================

    /**
     * This is the core effect that manages WebSocket workers for time-series data.
     * It runs when chart configuration, queries, or filters change.
     * 
     * Flow:
     * 1. Check if time-series is enabled
     * 2. Generate required worker fingerprints
     * 3. Compare with existing workers
     * 4. Cleanup outdated workers
     * 5. Create new workers as needed
     */

    useEffect(() => {
        // Early exit: cleanup everything if not time-series chart
        if (!storedChartObj.series || !storedChartObj.time_series) {
            workersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            workersRef.current.clear();
            currentQueriesRef.current.clear();
            setTsData({});
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

        // Get chart filters and generate meta filters for WebSocket queries
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

        // Generate all required fingerprints for current configuration
        const allFingerprints = generateAllFingerprints(metaFilters);

        // Check if worker configuration has changed
        const currentFingerprints = new Set(Array.from(workersRef.current.keys()));
        const newFingerprints = new Set(Array.from(allFingerprints.keys()));

        const fingerprintsChanged = currentFingerprints.size !== newFingerprints.size ||
            Array.from(newFingerprints).some(fp => !currentFingerprints.has(fp));

        // Early exit: no changes needed
        if (!fingerprintsChanged) {
            return;
        }

        // Identify fingerprints being removed
        const removedFingerprints = Array.from(currentFingerprints).filter(fp => !newFingerprints.has(fp));
        const addedFingerprints = Array.from(newFingerprints).filter(fp => !currentFingerprints.has(fp));


        // Only clear tsData for fingerprints that are being removed
        if (removedFingerprints.length > 0) {
            setTsData(prevTsData => {
                const updatedTsData = { ...prevTsData };
                removedFingerprints.forEach(fingerprint => {
                    // Find and remove all tsData keys that end with this fingerprint
                    Object.keys(updatedTsData).forEach(key => {
                        if (key.endsWith(`__${fingerprint}`)) {
                            delete updatedTsData[key];
                        }
                    });
                });
                return updatedTsData;
            });
        }

        // Cleanup workers that are no longer needed
        workersRef.current.forEach(({ socket, worker }, fingerprint) => {
            if (!newFingerprints.has(fingerprint)) {
                cleanupWorker(fingerprint);
            }
        });

        // Create workers for new fingerprints
        allFingerprints.forEach(({ query }, fingerprint) => {
            if (!workersRef.current.has(fingerprint)) {
                createWorker(fingerprint, query);
            }
        });

        // Update tracking reference
        currentQueriesRef.current = new Map(Array.from(newFingerprints).map(fp => [fp, fp]));

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
        generateAllFingerprints,
        createWorker,
        cleanupWorker
    ]);

    // Component unmount cleanup - ensure all workers are properly terminated
    useEffect(() => {
        return () => {
            workersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            workersRef.current.clear();
            currentQueriesRef.current.clear();
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
        }
    }, [chartUpdateCounter])

    useEffect(() => {
        // Transform uniqueKey-based tsData back to query-name-based for chart rendering
        // Aggregate data from multiple fingerprints that share the same query name
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


        // create the datasets for chart configuration (time-series and non time-series both)
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
        setData(updatedData);

        const isFromPinnedFilterChange = pinnedFilterUpdateRef.current;

        if (!isFromPinnedFilterChange) {
            syncPinnedFiltersWithData(updatedData);
        }

        const updatedSchema = cloneDeep(schema);
        const chartEncodeSchema = getModelSchema('chart_encode', updatedSchema);
        const filterSchema = getModelSchema('ui_filter', updatedSchema);

        if (updatedData.time_series) {
            filterSchema.auto_complete = 'fld_name:MetaFldList';
            chartEncodeSchema.auto_complete = 'x:FldList,y:ProjFldList';
        } else {
            filterSchema.auto_complete = 'fld_name:FldList';
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