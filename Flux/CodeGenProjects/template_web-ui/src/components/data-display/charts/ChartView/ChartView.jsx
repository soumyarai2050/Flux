import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux'; // TODO: SPOOFING - useDispatch added for testing without backend
// third-party package imports
import {
    Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText
} from '@mui/material';
import { cloneDeep, get, isEqual } from 'lodash';
import { Add, Close, Delete, Save, Error, Publish } from '@mui/icons-material';
// project constants and common utility function imports
import { DATA_TYPES, MODES, API_ROOT_URL, MODEL_TYPES, DB_ID } from '../../../../constants';
import { addxpath, clearxpath } from '../../../../utils/core/dataAccess';
import { applyFilter, getChartFilterDict } from '../../../../utils/core/dataFiltering';
import {
    genChartDatasets, genMetaFilters, getChartOption, tooltipFormatter,
    updateChartDataObj, updateChartSchema, updatePartitionFldSchema
} from '../../../../utils/core/chartUtils';
import { generateObjectFromSchema, getModelSchema } from '../../../../utils/core/schemaUtils';
import { sliceMapWithFallback as sliceMap } from '../../../../models/sliceMap'; // TODO: SPOOFING - for chart_tile injection
// custom component imports
import Icon from '../../../ui/Icon';
import FullScreenModal from '../../../ui/Modal';
import Resizer from '../../../ui/Resizer/Resizer';
import EChart from '../EChart';
import ListPanel from '../../../ui/ListPanel/ListPanel';
import styles from './ChartView.module.css';
import { useTheme } from '@emotion/react';
import DataTree from '../../trees/DataTree';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../../utility/cards';
import QuickFilterPin from '../../../controls/QuickFilterPin';
import ContentCopier from '../../../ui/ContentCopier';
import { CHART_PUBLISH_URL } from '../../../../config';
// custom hooks
import useTimeSeriesData from '../../../../hooks/useTimeSeriesData';

const CHART_SCHEMA_NAME = 'chart_data';

function ChartView({
    modelName,
    sourceBaseUrl,
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
    const dispatch = useDispatch(); // TODO: SPOOFING - dispatch for testing without backend -remove when backend is ready
    const theme = useTheme();
    const { schema: projectSchema, schemaCollections } = useSelector(state => state.schema);
    // TODO: SPOOFING - Get chart_tile Redux state for spoofing
    const chartTileState = useSelector(sliceMap['chart_tile']?.selector || (() => ({ storedArray: [] })));

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

    // Time-series data from custom hook
    const { tsData, queryDict } = useTimeSeriesData({
        chartConfig: storedChartObj,
        chartRows: chartRows,
        fieldsMetadata,
        projectSchema,
        schemaCollections,
        modelType,
        isEnabled: mode === MODES.READ,
        mode,
        slidingWindowSize: 20
    });

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
    const pinnedFilterUpdateRef = useRef(false);

    // Resizer state for adjustable heights
    const [chartHeight, setChartHeight] = useState(500);
    const containerRef = useRef(null);


    // =============================================
    // EXISTING CHARTVIEW LOGIC
    // =============================================

    useEffect(() => {
        const updatedIndex = selectedChartName ? chartData.findIndex((o) => o.chart_name === selectedChartName) : null;
        setSelectedIndex(updatedIndex);
    }, [selectedChartName, chartEnableOverride])

    // Sync local selectedData state with props from parent
    useEffect(() => {
        const newSelectedIds = selectedRows ? selectedRows.map(row => row['data-id'] || row['_id']) : [];
        setSelectedData(prevData => {
            // Create a sorted version of both arrays for a consistent comparison
            const sortedPrevData = [...prevData].sort();
            const sortedNewData = [...newSelectedIds].sort();

            if (!isEqual(sortedPrevData, sortedNewData)) {
                return newSelectedIds;
            }
            return prevData;
        });
    }, [selectedRows]);

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

    const handlePublish = (e, chart) => {
        e.stopPropagation();

        // Validate that we have the required metadata
        if (!modelName || !sourceBaseUrl) {
            console.error('Cannot publish: missing source metadata', { modelName, sourceBaseUrl });
            return;
        }

        // Prepare the payload
        const publishPayload = {
            _id: Date.now(), // Generate temp ID
            chart_data: clearxpath(cloneDeep(chart)),
            source_model_name: modelName,
            source_model_base_url: sourceBaseUrl
        };

        console.log('PUBLISH PAYLOAD:', JSON.stringify(publishPayload, null, 2));

        // ========================================
        // TODO: SPOOFING - Direct Redux injection for testing without backend
        // Remove this section when backend is ready
        // ========================================
        try {
            const chartTileSlice = sliceMap['chart_tile'];
            if (chartTileSlice && chartTileSlice.actions) {
                // Use chartTileState from top-level useSelector
                const updatedArray = [...(chartTileState.storedArray || []), publishPayload];

                // Dispatch to Redux store
                dispatch(chartTileSlice.actions.setStoredArray(updatedArray));
            } else {
                console.warn('⚠️ chart_tile slice not found in sliceMap');
            }
        } catch (error) {
            console.error('❌ SPOOFING failed:', error);
        }
        // ========================================
        // End SPOOFING section
        // ========================================

        // TODO: Real backend call (uncomment when ready)
        // axios.post(`${CHART_PUBLISH_URL}`, publishPayload)
        //     .then(response => {
        //         console.log('Chart published successfully:', response.data);
        //     })
        //     .catch(error => {
        //         console.error('Failed to publish chart:', error);
        //     });
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

    // Resizer handlers
    const handleChartResize = useCallback((newHeight) => {
        setChartHeight(newHeight);
    }, []);

    // Initialize chart height based on container
    useEffect(() => {
        if (containerRef.current) {
            const containerHeight = containerRef.current.clientHeight;
            const initialChartHeight = Math.max(300, containerHeight * 0.9);
            setChartHeight(initialChartHeight);
        }
    }, []);

    return (
        <>
            <Box className={styles.container}>
                <ListPanel
                    items={chartData}
                    selectedIndex={selectedIndex}
                    onSelect={handleSelect}
                    onCreate={handleChartCreate}
                    onDelete={handleChartDelete}
                    itemNameKey="chart_name"
                    addButtonText="Add new chart"
                    enableOverride={chartEnableOverride}
                    collapse={true}
                    mode={mode}
                    onDoubleClick={handleDoubleClick}
                    additionalActions={(item, index, mode, selectedIndex) => (

                        <>
                            <ContentCopier text={item.chart_name} />
                            <Icon title='Publish' onClick={(e) => handlePublish(e, item)}>
                                <Publish fontSize='small' />
                            </Icon>
                            <Icon title='Delete' onClick={(e) => handleChartDelete(e, item.chart_name, index)}>
                                <Delete fontSize='small' />
                            </Icon>
                        </>
                    )}
                />
                <Divider orientation='vertical' flexItem />
                <Box ref={containerRef} className={styles.chart_container}>
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

                    {/* Resizable Chart Section */}
                    <Box className={styles.resizable_content}>
                        <Box
                            className={styles.chart}
                            style={{ height: chartHeight }}
                        >
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

                        {/* Resizer Component */}
                        {children && (
                            <Resizer
                                direction="horizontal"
                                onResize={handleChartResize}
                                minSize={100}
                                maxSize={containerRef.current ? containerRef.current.clientHeight - 200 : 800}
                                className={styles.chart_resizer}
                            />
                        )}

                        {/* Children (AbbreviationMergeView) Section */}
                        {children && (
                            <Box className={styles.children_container}>
                                {children}
                            </Box>
                        )}
                    </Box>
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