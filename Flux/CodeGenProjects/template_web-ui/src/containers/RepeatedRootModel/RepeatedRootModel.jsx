import React, { useCallback, useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { cloneDeep, isEqual, set } from 'lodash';
import { saveAs } from 'file-saver';
// project imports
import { DB_ID, DEFAULT_HIGHLIGHT_DURATION, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import { clearxpath, addxpath } from '../../utils/core/dataAccess';
import { generateObjectFromSchema, getModelSchema } from '../../utils/core/schemaUtils';
import { compareJSONObjects } from '../../utils/core/objectUtils';
import { getServerUrl, isWebSocketActive } from '../../utils/network/networkUtils';
import {
    getWidgetTitle, getCrudOverrideDict, getDefaultFilterParamDict, getCSVFileName,
    updateFormValidation,
    snakeToCamel
} from '../../utils/ui/uiUtils';
import { createAutoBoundParams } from '../../utils/core/parameterBindingUtils';
import { removeRedundantFieldsFromRows } from '../../utils/core/dataTransformation';
import { cleanAllCache } from '../../cache/attributeCache';
import { useWebSocketWorker, useDownload, useModelLayout, useConflictDetection, useCountQuery } from '../../hooks';
import { massageDataForBackend, shouldUsePagination, buildDefaultFilters, extractCrudParams } from '../../utils/core/paginationUtils';
// custom components
import { FullScreenModalOptional } from '../../components/ui/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/utility/cards';
import MenuGroup from '../../components/controls/MenuGroup';
import { ConfirmSavePopup, FormValidation } from '../../components/utility/Popup';
import CommonKeyWidget from '../../components/data-display/CommonKeyWidget';
import { DataTable, PivotTable } from '../../components/data-display/tables';
import { ChartView } from '../../components/data-display/charts';
import { sliceMapWithFallback as sliceMap } from '../../models/sliceMap';
import ConflictPopup from '../../components/utility/ConflictPopup';

function RepeatedRootModel({ modelName, modelDataSource, modelDependencyMap }) {
    const { schema: projectSchema, schemaCollections } = useSelector((state) => state.schema);

    const { actions, selector } = modelDataSource;
    const { storedArray, storedObj, updatedObj, objId, mode, allowUpdates, error, isLoading, popupStatus } = useSelector(selector);
    const { node, selectedDataPoints, lastSelectedDataPoint, isAnalysis } = useSelector(state => state[modelName] ?? {});
    const nodeModelName = useMemo(() => node?.modelName ?? null, [node]);
    const nodeUrl = useMemo(() => node?.url ?? null, [node]);
    const modelSchema = useMemo(() => node?.modelSchema ?? modelDataSource.schema, [node]);
    // Extract allowedOperations directly from schema's json_root
    const allowedOperations = useMemo(() => modelSchema?.json_root || null, [modelSchema])
    const fieldsMetadata = useMemo(() => node?.fieldsMetadata ?? modelDataSource.fieldsMetadata, [node]);
    const derivedModelName = useMemo(() => nodeModelName ?? modelName, [nodeModelName]);

    // Extract the three data sources from dictionary
    const urlOverrideDataSource = modelDependencyMap?.urlOverride ?? null;
    const crudOverrideDataSource = modelDependencyMap?.crudOverride ?? null;
    const defaultFilterDataSource = modelDependencyMap?.defaultFilter ?? null;

    // Create stable selector functions
    const urlOverrideSelector = useMemo(
        () => urlOverrideDataSource?.selector ?? (() => ({ storedObj: null })),
        [urlOverrideDataSource]
    );
    const crudOverrideSelector = useMemo(
        () => crudOverrideDataSource?.selector ?? (() => ({ storedObj: null })),
        [crudOverrideDataSource]
    );
    const defaultFilterSelector = useMemo(
        () => defaultFilterDataSource?.selector ?? (() => ({ storedObj: null })),
        [defaultFilterDataSource]
    );

    // Subscribe to each data source's Redux store using shallow equality
    const { storedObj: urlOverrideDataSourceStoredObj } = useSelector(urlOverrideSelector, shallowEqual);
    const { storedObj: crudOverrideDataSourceStoredObj } = useSelector(crudOverrideSelector, shallowEqual);
    const { storedObj: defaultFilterDataSourceStoredObj } = useSelector(defaultFilterSelector, shallowEqual);

    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [sortedCells, setSortedCells] = useState([]);
    const [uniqueValues, setUniqueValues] = useState({});
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [rowIds, setRowIds] = useState(null);

    const {
        modelLayoutOption,
        modelLayoutData,
        isMaximized,
        page,
        showHidden,
        showMore,
        showAll,
        moreAll,
        layoutType,
        setLayoutType,
        handleFullScreenToggle,
        handlePageChange,
        handleRowsPerPageChange,
        handleColumnOrdersChange,
        handleSortOrdersChange,
        handleShowLessChange,
        handlePinnedChange,
        handleOverrideChange,
        handleLayoutTypeChange,
        handleFiltersChange,
        handleStickyHeaderToggle,
        handleCommonKeyCollapseToggle,
        handleFrozenColumnsChange,
        handleColumnNameOverrideChange,
        handleHighlightUpdateOverrideChange,
        handleHighlightDurationChange,
        handleNoCommonKeyOverrideChange,
        handleDataSourceColorsChange,
        handleJoinByChange,
        handleCenterJoinToggle,
        handleFlipToggle,
        handleSelectedChartNameChange,
        handleChartEnableOverrideChange,
        handleChartDataChange,
        handleSelectedPivotNameChange,
        handlePivotEnableOverrideChange,
        handlePivotDataChange,
        handleQuickFiltersChange,
        handleVisibilityMenuClick,
        handleVisibilityMenuDoubleClick,
        handleShowAllToggle,
        handleMoreAllToggle,
        handleShowHiddenToggle,
        handleShowMoreToggle,
    } = useModelLayout(modelName, objId, MODEL_TYPES.REPEATED_ROOT, setHeadCells, mode);

    const crudOverrideDictRef = useRef(getCrudOverrideDict(modelSchema));
    const defaultFilterParamDictRef = useRef(getDefaultFilterParamDict(modelSchema));
    const hasReadByIdWsProperty = allowedOperations?.ReadByIDWebSocketOp === true;

    // Determine if server-side pagination is enabled from schema
    const serverSidePaginationEnabled = modelSchema.server_side_pagination === true && modelSchema.is_large_db_object !== true;

    // Extract ui_limit from schema ONLY when server-side pagination is disabled
    // When server-side is enabled, uiLimit will be null (limit handled by pagination)
    const uiLimit = !serverSidePaginationEnabled ? (modelSchema.ui_get_all_limit ?? null) : null;

    // Build default filters (server-side) for use in multiple places
    const defaultFilters = useMemo(() => {
        return buildDefaultFilters(defaultFilterDataSourceStoredObj, defaultFilterParamDictRef.current);
    }, [defaultFilterDataSourceStoredObj]);

    // Check if all required default filter values are ready
    const areDefaultFiltersReady = useMemo(() => {
        if (!defaultFilterParamDictRef.current || Object.keys(defaultFilterParamDictRef.current).length === 0) {
            return true; // No default filters required
        }
        // Check if all required default filters have valid values
        const filterMap = new Map(defaultFilters.map(f => [f.column_name, f.filtered_values]));
        return Object.keys(defaultFilterParamDictRef.current).every(key => {
            const filterValues = filterMap.get(key);
            return filterValues !== undefined && filterValues !== null &&
                   (!Array.isArray(filterValues) || filterValues.length > 0);
        });
    }, [defaultFilters]);

    // Construct base URLs using urlOverrideDataSource (must be before useCountQuery)
    const baseUrl = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    const baseViewUrl = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata, undefined, true),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    // Final URL values (overridden by nodeUrl if present)
    const url = useMemo(() => nodeUrl ?? baseUrl, [nodeUrl, baseUrl]);
    const viewUrl = useMemo(() => nodeUrl ?? baseViewUrl, [nodeUrl, baseViewUrl]);

    // Extract params for CRUD override using crudOverrideDataSource (must be before useEffects)
    const params = useMemo(() =>
        extractCrudParams(crudOverrideDataSourceStoredObj, crudOverrideDictRef.current),
        [crudOverrideDataSourceStoredObj]
    );

    // Process data for backend consumption
    // Use modelLayoutData with JSON.stringify to handle reference stability
    const processedData = useMemo(() => {
        const rowsPerPage = modelLayoutData.rows_per_page || 25;
        const filters = modelLayoutOption.filters || [];
        const sortOrders = modelLayoutData.sort_orders || [];

        // Merge UI filters with default filters
        const mergedFilters = [...filters, ...defaultFilters];

        const result = massageDataForBackend(mergedFilters, sortOrders, page, rowsPerPage);

        return result;
    }, [
        JSON.stringify(modelLayoutOption.filters),
        JSON.stringify(modelLayoutData.sort_orders),
        page,
        modelLayoutData.rows_per_page,
        defaultFilters
    ]);

    // Unified count query - automatically uses HTTP or WebSocket based on allowedOperations
    const {
        count,
        isLoading: isCountLoading,
        isSynced
    } = useCountQuery(
        url,
        derivedModelName,
        processedData.filters,
        serverSidePaginationEnabled && areDefaultFiltersReady,
        hasReadByIdWsProperty  // Pass hasReadByIdWsProperty to determine transport type
    );

    // Derive waiting state - only wait if server-side pagination is enabled
    const isWaitingForCount = serverSidePaginationEnabled && (count === null || isCountLoading || !isSynced);

    // Determine if pagination should be used
    const usePagination = useMemo(() => {
        // Short-circuit if server-side pagination is not enabled
        if (!serverSidePaginationEnabled) {
            return false;
        }
        if (isWaitingForCount) {
            return false;
        }
        const rowsPerPage = modelLayoutData.rows_per_page || 25;
        return shouldUsePagination(count, rowsPerPage);
    }, [serverSidePaginationEnabled, count, modelLayoutData.rows_per_page, isWaitingForCount]);

    // Local state multiselect pattern for non-ChartTileNode models
    // Node models use Redux-based selectedDataPoints/lastSelectedDataPoint
    const isChartModel = nodeModelName !== null && nodeModelName !== undefined;
    const [chartMultiSelectState, setChartMultiSelectState] = useState({});

    // Current multiselect state key (for local state pattern)
    // Apply chart-specific multiselect only when chart name exists
    const currentStateKey = layoutType === LAYOUT_TYPES.CHART && modelLayoutData.selected_chart_name
        ? modelLayoutData.selected_chart_name
        : modelName;
    const localMultiSelectedRows = chartMultiSelectState[currentStateKey]?.selectedRows || [];
    const localLastSelectedRowId = chartMultiSelectState[currentStateKey]?.lastSelectedRowId || null;

    // Final multiselect state - use Redux for ChartTileNode, local state for others
    // Different formats needed for ChartView (objects) vs DataTable (IDs)
    const finalSelectedRowObjects = isChartModel
        ? selectedDataPoints || []
        : (localMultiSelectedRows || []).map(id => storedArray.find(row => row._id === id)).filter(Boolean);
    const finalSelectedRowIds = isChartModel
        ? (selectedDataPoints || []).map(point => point._id)
        : localMultiSelectedRows;
    const finalLastSelectedRowId = isChartModel ? lastSelectedDataPoint?._id : localLastSelectedRowId;

    const dispatch = useDispatch();
    const [, startTransition] = useTransition();

    // refs
    const socketRef = useRef(null);
    const workerRef = useRef(null);
    const isWorkerBusyRef = useRef({
        isBusy: false,
        hasPendingUserActions: false,
    });
    const pendingUpdateRef = useRef(null);
    const changesRef = useRef({});
    const formValidationRef = useRef({});
    const allowedLayoutTypesRef = useRef([LAYOUT_TYPES.TABLE, LAYOUT_TYPES.PIVOT_TABLE, LAYOUT_TYPES.CHART]);
    // refs to identify change
    const optionsRef = useRef(null);
    const captionDictRef = useRef(null);

    // calculated fields
    const modelTitle = getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj);

    // Auto-bound parameters for query parameter binding - uses selected row data
    const autoBoundParams = useMemo(() => {
        const isEmpty = obj => obj && obj.constructor === Object && Object.keys(obj).length === 0;

        // Selected row data
        const currentData = !isEmpty(updatedObj)
            ? updatedObj
            : storedArray?.[0];
        if (!currentData || !fieldsMetadata) return {};

        return createAutoBoundParams(fieldsMetadata, currentData);
    }, [fieldsMetadata, updatedObj, storedArray]);

    const { downloadCSV, isDownloading, progress } = useDownload(derivedModelName, fieldsMetadata, null);

    // Conflict detection for handling websocket updates during editing
    const {
        showConflictPopup,
        conflicts,
        effectiveStoredData, // This is now a stable, memoized value
        takeSnapshot,
        clearSnapshot,
        checkAndShowConflicts,
        closeConflictPopup,
        getBaselineForComparison,
    } = useConflictDetection(storedObj, updatedObj, mode, fieldsMetadata, false, allowUpdates);

    const effectiveStoredArray = storedArray.map((obj) => effectiveStoredData && effectiveStoredData[DB_ID] === obj[DB_ID] ? effectiveStoredData : obj)

    // Initial GET_ALL request - only for models without WebSocket support
    useEffect(() => {
        // If ReadByIDWebSocketOp exists, skip HTTP GET_ALL (WebSocket will handle it)
        if (hasReadByIdWsProperty) {
            return;
        }

        // Wait for count query to complete if server-side pagination is enabled
        if (isWaitingForCount) {
            return;
        }

        // Wait for default filters to be ready
        if (!areDefaultFiltersReady) {
            return;
        }

        if (viewUrl) {
            let args = { url: viewUrl };

            // Add uiLimit to args (not queryParams) - it will be handled by sliceFactory
            if (uiLimit) {
                args.uiLimit = uiLimit;
            }

            // Build query params similar to WebSocket implementation
            // JSON-stringify filters, sortOrders, and pagination to match WebSocket format
            const queryParams = {};

            // Add filters if they exist (JSON-stringified)
            if (processedData.filters && processedData.filters.length > 0) {
                queryParams.filters = JSON.stringify(processedData.filters);
            }

            // Add sort orders if they exist (JSON-stringified)
            if (processedData.sortOrders && processedData.sortOrders.length > 0) {
                queryParams.sort_order = JSON.stringify(processedData.sortOrders);
            }

            // Only add pagination if server-side pagination is enabled and needed (JSON-stringified)
            if (serverSidePaginationEnabled && usePagination) {
                queryParams.pagination = JSON.stringify(processedData.pagination);
            }

            // Handle CRUD override - merge custom endpoint and params
            if (crudOverrideDictRef.current?.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
                if (!params && Object.keys(paramDict).length > 0) {
                    return;
                }
                // Merge CRUD params with query params (CRUD params are not JSON-stringified)
                args = { ...args, endpoint, params: { ...params, ...queryParams } };
            } else {
                // Standard endpoint - just pass query params
                args = { ...args, params: queryParams };
            }

            dispatch(actions.getAll(args));
        }
    }, [viewUrl, JSON.stringify(params), hasReadByIdWsProperty, processedData.filters, processedData.sortOrders, processedData.pagination, 
        serverSidePaginationEnabled, usePagination, isWaitingForCount, defaultFilters, uiLimit])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/repeated-root-model.worker.js", import.meta.url), { type: 'module' });

        workerRef.current.onmessage = (event) => {
            const { rows, groupedRows, activeRows, maxRowSize, headCells, commonKeys, uniqueValues, sortedCells } = event.data;

            startTransition(() => {
                setRows(rows);
                setGroupedRows(groupedRows);
                setActiveRows(activeRows);
                setMaxRowSize(maxRowSize);
                setHeadCells(headCells);
                setCommonKeys(commonKeys);
                setSortedCells(sortedCells);
                setUniqueValues(uniqueValues);

                // If a new update came in while the worker was busy, send it now.
                if (pendingUpdateRef.current) {
                    const pendingMessage = pendingUpdateRef.current;
                    pendingUpdateRef.current = null;
                    const { hasPendingUserActions } = isWorkerBusyRef.current;
                    isWorkerBusyRef.current = {
                        isBusy: true,
                        hasPendingUserActions: false
                    }
                    setIsProcessingUserActions(hasPendingUserActions);
                    workerRef.current.postMessage(pendingMessage);
                } else {
                    isWorkerBusyRef.current = {
                        isBusy: false,
                        hasPendingUserActions: false
                    }
                    setIsProcessingUserActions(false);
                }
            })
        }

        return (() => {
            if (workerRef.current) {
                workerRef.current.terminate();
                workerRef.current = null;
                isWorkerBusyRef.current = {
                    isBusy: false,
                    hasPendingUserActions: false
                }
                setIsProcessingUserActions(false);
            }
        })
    }, [])

    useEffect(() => {
        if (workerRef.current) {
            // Prepare the message data based on current state
            const messageData = {
                storedArray,
                updatedObj,
                fieldsMetadata,
                page,
                rowsPerPage: modelLayoutData.rows_per_page || 25,
                sortOrders: modelLayoutData.sort_orders || [],
                filters: modelLayoutOption.filters || [],
                mode,
                enableOverride: modelLayoutData.enable_override || [],
                disableOverride: modelLayoutData.disable_override || [],
                showMore,
                moreAll,
                showLess: modelLayoutData.show_less || [],
                showHidden,
                showAll,
                frozenColumns: modelLayoutData.frozen_columns || [],
                columnNameOverride: modelLayoutData.column_name_override || [],
                highlightUpdateOverride: modelLayoutData.highlight_update_override || [],
                columnOrders: modelLayoutData.column_orders || [],
                noCommonKeyOverride: modelLayoutData.no_common_key_override || [],
                joinBy: modelLayoutData.join_by || {},
                joinSort: modelLayoutOption.join_sort || null,
                centerJoin: modelLayoutData.joined_at_center,
                flip: modelLayoutData.flip,
                rowIds,
                serverSidePaginationEnabled, // Pass dynamic server-side pagination flag to worker
            }

            const updatedOptionsRef = {
                mode,
                page,
                showMore,
                moreAll,
                showHidden,
                showAll,
                modelLayoutOption,
                modelLayoutData,
                rowIds,
            }

            if (!isEqual(optionsRef.current, updatedOptionsRef)) {
                isWorkerBusyRef.current.hasPendingUserActions = true;
            }
            optionsRef.current = updatedOptionsRef;

            // If worker is busy, store the latest message in pendingUpdateRef
            if (isWorkerBusyRef.current.isBusy === true) {
                pendingUpdateRef.current = messageData;
            } else {
                const { hasPendingUserActions } = isWorkerBusyRef.current;
                isWorkerBusyRef.current = {
                    isBusy: true,
                    hasPendingUserActions: false
                }
                setIsProcessingUserActions(hasPendingUserActions);
                workerRef.current.postMessage(messageData);
            }
        }
    }, [
        storedArray, updatedObj, fieldsMetadata, modelLayoutData, modelLayoutOption, page, mode,
        showMore, moreAll, showHidden, showAll, rowIds, usePagination
    ])

    const handleModelDataSourceUpdate = (updatedArray) => {
        dispatch(actions.setStoredArray(updatedArray));
    }

    const handleReconnect = () => {
        setReconnectCounter((prev) => prev + 1);
    }

    // Determine if WebSocket should be disabled
    // 1. If model is in analysis mode
    // 2. If model doesn't support ReadByIDWebSocketOp
    const isWebSocketDisabled = (isAnalysis ?? false) || !hasReadByIdWsProperty;
    // Wait for count query to complete before establishing WebSocket connection
    // This prevents double connection (once without pagination, once with pagination)
    // isWaitingForCount handles both: (1) initial load and (2) filter changes
    // Also wait for default filters to be ready
    const isWebSocketDelayed = isWebSocketDisabled || isWaitingForCount || !areDefaultFiltersReady;

    socketRef.current = useWebSocketWorker({
        url: (modelSchema.is_large_db_object || modelSchema.is_time_series || modelLayoutOption.depending_proto_model_for_cpp_port) ? url : viewUrl,
        modelName: derivedModelName,
        isDisabled: isWebSocketDelayed,
        reconnectCounter,
        selector,
        onWorkerUpdate: handleModelDataSourceUpdate,
        onReconnect: handleReconnect,
        params,
        crudOverrideDict: crudOverrideDictRef.current,
        defaultFilterParamDict: defaultFilterParamDictRef.current,
        isAlertModel: modelLayoutOption.is_model_alert_type,
        isCppModel: modelLayoutOption.depending_proto_model_for_cpp_port,
        // Parameters for unified endpoint with dynamic parameter inclusion
        // Filters now include merged default filter params
        filters: processedData.filters,
        sortOrders: processedData.sortOrders,
        pagination: (serverSidePaginationEnabled && usePagination) ? processedData.pagination : null,
        uiLimit: uiLimit  // Client-side limit (null when server-side pagination is enabled)
    })

    const handleModeToggle = () => {
        const updatedMode = mode === MODES.READ ? MODES.EDIT : MODES.READ;

        // Take snapshot when entering EDIT mode for conflict detection
        if (updatedMode === MODES.EDIT) {
            takeSnapshot();
        }

        dispatch(actions.setMode(updatedMode));
        const layoutTypeKey = updatedMode === MODES.READ ? 'view_layout' : 'edit_layout';
        if (modelLayoutData[layoutTypeKey] && modelLayoutData[layoutTypeKey] !== layoutType) {
            handleLayoutTypeChange(modelLayoutData[layoutTypeKey], updatedMode);
        }
    }

    const handleReload = () => {
        handleDiscard();
        // Clear local chart multiselect state on reload for non-ChartNode models
        if (!isChartModel) {
            setChartMultiSelectState({});
        }
        dispatch(actions.setIsCreating(false));
        handleReconnect();
    }

    const cleanModelCache = () => {
        changesRef.current = {};
        formValidationRef.current = {};
        cleanAllCache(modelName);
    }

    const handleDiscard = () => {
        const updatedObj = addxpath(cloneDeep(storedObj));
        dispatch(actions.setUpdatedObj(updatedObj));
        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        cleanModelCache();
        clearSnapshot(); // Clear snapshot on discard
    }

    const handleDownload = async () => {
        let args = {
            url: viewUrl,
            filters: processedData.filters,
            sortOrders: processedData.sortOrders
        };
        if (crudOverrideDictRef.current?.GET_ALL) {
            const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
            if (!params && Object.keys(paramDict).length > 0) {
                return;
            }
            args = { ...args, endpoint, params };
        }
        const fileName = getCSVFileName(modelName);
        try {
            // Pass null as storedData to fetch complete dataset with filters/sorting
            const csvContent = await downloadCSV(null, args);
            const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
            saveAs(blob, fileName);
        } catch (error) {
            console.error('CSV download failed:', error);
        }
    }

    const handlePopupClose = (popupName) => {
        dispatch(actions.setPopupStatus({ [popupName]: false }));
        handleReload();
    }

    const handleConfirmSavePopupClose = () => {
        handlePopupClose('confirmSave');
    }

    const handleFormValidationPopupClose = () => {
        handlePopupClose('formValidation');
    }

    const handleContinue = () => {
        dispatch(actions.setPopupStatus({ formValidation: false }));
    }

    const handleCreate = () => {
        const newObj = generateObjectFromSchema(projectSchema, modelSchema);
        const modelUpdatedObj = addxpath(newObj);
        dispatch(actions.setStoredObj({}));
        dispatch(actions.setUpdatedObj(modelUpdatedObj));
        dispatch(actions.setMode(MODES.EDIT));
        handleModeToggle();
    }

    const handleSave = (modifiedObj, force = false, bypassConflictCheck = false) => {
        if (!bypassConflictCheck && checkAndShowConflicts()) {
            return;
        }

        if (Object.keys(formValidationRef.current).length > 0) {
            dispatch(actions.setPopupStatus({ formValidation: true }));
            return;
        }
        const modelUpdatedObj = modifiedObj || clearxpath(cloneDeep(updatedObj));

        // Use getBaselineForComparison() instead of storedObj directly
        const baselineForComparison = getBaselineForComparison();

        if (!baselineForComparison || !modelUpdatedObj) {
            console.warn('Cannot compare objects: baselineForComparison or modelUpdatedObj is null');
            return;
        }

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, fieldsMetadata, false) || [null, null];
        captionDictRef.current = captionDict;

        if (!activeChanges || Object.keys(activeChanges).length === 0) {
            changesRef.current = {};
            dispatch(actions.setMode(MODES.READ));
            return;
        }
        changesRef.current.active = activeChanges;
        const changesCount = Object.keys(activeChanges).length;
        if (force) {
            if (changesCount === 1) {
                executeSave();
                return;
            }
        }
        dispatch(actions.setPopupStatus({ confirmSave: true }));
    };

    const executeSave = () => {
        const changeDict = cloneDeep(changesRef.current.active);
        if (changeDict[DB_ID]) {
            dispatch(actions.partialUpdate({ url, data: changeDict }));
        } else {
            dispatch(actions.create({ url, data: changeDict }));
            dispatch(actions.setMode(MODES.READ));
        }
        changesRef.current = {};
        // dispatch(actions.setMode(MODES.READ));
        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        dispatch(actions.setPopupStatus({ confirmSave: false }));
        clearSnapshot(); // Clear snapshot after successful save
    }

    // Conflict resolution handlers - defined after all dependencies are available
    const handleDiscardChanges = () => {
        handleDiscard();
        closeConflictPopup();
    }

    const handleOverwriteChanges = () => {
        closeConflictPopup();

        const modelUpdatedObj = clearxpath(cloneDeep(updatedObj));
        const baselineForComparison = getBaselineForComparison();

        if (!baselineForComparison || !modelUpdatedObj) {
            console.warn('Cannot compare objects in handleOverwriteChanges: baselineForComparison or modelUpdatedObj is null');
            return;
        }

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, fieldsMetadata, false) || [null, null];
        captionDictRef.current = captionDict;
        if (!activeChanges || Object.keys(activeChanges).length === 0) {
            changesRef.current = {};
            dispatch(actions.setMode(MODES.READ));
            return;
        }
        changesRef.current.active = activeChanges;
        handleSave(modelUpdatedObj, false, true);
    }

    const handleUpdate = (updatedObj) => {
        dispatch(actions.setUpdatedObj(updatedObj));
    }

    const handleUserChange = (xpath, updateDict, validationRes, source) => {
        changesRef.current.user = {
            ...changesRef.current.user,
            ...updateDict
        }
        updateFormValidation(formValidationRef, xpath, validationRes);
    }

    const handleButtonToggle = (e, xpath, value, objId, source, force = false) => {
        const modelUpdatedObj = clearxpath(cloneDeep(updatedObj));
        set(modelUpdatedObj, xpath, value);
        if (force) {
            // Use getBaselineForComparison() instead of storedObj directly
            const baselineForComparison = getBaselineForComparison();

            if (!baselineForComparison || !modelUpdatedObj) {
                console.warn('Cannot compare objects in handleButtonToggle: baselineForComparison or modelUpdatedObj is null');
                return;
            }

            const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, fieldsMetadata) || [null, null];
            captionDictRef.current = captionDict;
            changesRef.current.active = activeChanges;
            executeSave();
        } else if (storedObj[DB_ID]) {
            handleSave(modelUpdatedObj, force);
        }
    }

    const handleErrorClear = () => {
        dispatch(actions.setError(null));
    }

    const handleRowSelect = (id) => {
        dispatch(actions.setObjId(id));
    }

    const nodeActions = useMemo(() => sliceMap[modelName]?.actions, []);

    const handleTableSelectionChange = (newSelectedIds, mostRecentId) => {
        const safeSelectedIds = Array.isArray(newSelectedIds) ? newSelectedIds : (newSelectedIds ? [newSelectedIds] : []);

        if (isChartModel) {
            // Redux pattern for ChartTileNode models
            const newSelectedDataPoints = safeSelectedIds.map(id => {
                return storedArray.find(row => row['_id'] === id);
            }).filter(Boolean);

            const newLastSelectedDataPoint = mostRecentId
                ? storedArray.find(row => row['_id'] === mostRecentId)
                : null;

            if (nodeActions && typeof nodeActions.setSelectedDataPoints === 'function') {
                dispatch(nodeActions.setSelectedDataPoints(newSelectedDataPoints));
            }

            if (nodeActions && typeof nodeActions.setLastSelectedDataPoint === 'function') {
                dispatch(nodeActions.setLastSelectedDataPoint(newLastSelectedDataPoint));
            }
        } else {
            // Local state pattern for other RepeatedRoot models
            if (currentStateKey) {
                setChartMultiSelectState(prev => ({
                    ...prev,
                    [currentStateKey]: {
                        selectedRows: safeSelectedIds,
                        lastSelectedRowId: mostRecentId || null
                    }
                }));
            }
        }
    }

    const handleChartMultiSelectChange = useCallback((selectedIds, mostRecentId) => {
        if (isChartModel) {
            // Redux pattern for ChartTileNode models - delegate to existing handler
            handleTableSelectionChange(selectedIds, mostRecentId);
        } else {
            // Local state pattern for other RepeatedRoot models
            if (currentStateKey) {
                setChartMultiSelectState(prev => ({
                    ...prev,
                    [currentStateKey]: {
                        selectedRows: selectedIds || [],
                        lastSelectedRowId: mostRecentId || null
                    }
                }));
            }

            // Update row selection for data binding (similar to AbbreviatedMergeModel)
            if (mostRecentId) {
                dispatch(actions.setObjId(mostRecentId));
            } else if (!selectedIds || selectedIds.length === 0) {
                dispatch(actions.setObjId(null));
            }
        }
    }, [isChartModel, currentStateKey, dispatch, actions, handleTableSelectionChange]);

    const cleanedRows = useMemo(() => {
        if ([LAYOUT_TYPES.CHART, LAYOUT_TYPES.PIVOT_TABLE].includes(layoutType)) {
            return removeRedundantFieldsFromRows(rows);
        }
        return [];
    }, [rows, layoutType])

    // A helper function to decide which content to render based on layoutType
    const renderContent = () => {
        let Wrapper = React.Fragment;
        let wrapperProps = {};
        let wrapperMode = mode;
        let isReadOnly = modelLayoutOption.is_read_only ?? false;
        switch (layoutType) {
            case LAYOUT_TYPES.PIVOT_TABLE:
                Wrapper = PivotTable;
                wrapperProps = {
                    pivotData: modelLayoutOption.pivot_data || [],
                    data: cleanedRows,
                    mode: mode,
                    onModeToggle: handleModeToggle,
                    onPivotSelect: handleSelectedPivotNameChange,
                    selectedPivotName: modelLayoutData.selected_pivot_name ?? null,
                    pivotEnableOverride: modelLayoutData.pivot_enable_override ?? [],
                    onPivotDataChange: handlePivotDataChange,
                    onPivotCellSelect: setRowIds,
                };
                wrapperMode = MODES.READ;
                isReadOnly = true;
                break;
            case LAYOUT_TYPES.CHART:
                Wrapper = ChartView
                wrapperProps = {
                    modelName: derivedModelName,
                    sourceBaseUrl: url,
                    onReload: handleReload,
                    chartRows: cleanedRows,
                    onChartDataChange: handleChartDataChange,
                    fieldsMetadata: fieldsMetadata,
                    chartData: modelLayoutOption.chart_data || [],
                    modelType: MODEL_TYPES.REPEATED_ROOT,
                    onRowSelect: handleRowSelect,
                    mode: mode,
                    onModeToggle: handleModeToggle,
                    onChartSelect: handleSelectedChartNameChange,
                    selectedChartName: modelLayoutData.selected_chart_name ?? null,
                    chartEnableOverride: modelLayoutData.chart_enable_override ?? [],
                    onChartPointSelect: handleChartMultiSelectChange,
                    quickFilters: modelLayoutData.quick_filters ?? [],
                    onQuickFiltersChange: handleQuickFiltersChange,
                    selectedRowId: objId,
                    selectedRows: finalSelectedRowObjects,
                    lastSelectedRowId: finalLastSelectedRowId,
                };
                wrapperMode = MODES.READ;
                isReadOnly = true;
                break;
            default:
                break;
        }

        return (
            <Wrapper {...wrapperProps}>
                <CommonKeyWidget mode={wrapperMode} commonkeys={commonKeys} collapse={modelLayoutData.common_key_collapse} />
                <DataTable
                    rows={groupedRows}
                    activeRows={activeRows}
                    cells={sortedCells}
                    mode={wrapperMode}
                    sortOrders={modelLayoutData.sort_orders || []}
                    onSortOrdersChange={handleSortOrdersChange}
                    page={page}
                    rowsPerPage={modelLayoutData.rows_per_page || 25}
                    totalCount={count}
                    dataSourceColors={modelLayoutData.data_source_colors || []}
                    selectedId={objId}
                    onPageChange={handlePageChange}
                    onRowsPerPageChange={handleRowsPerPageChange}
                    onRowSelect={handleRowSelect}
                    onModeToggle={handleModeToggle}
                    onUpdate={handleUpdate}
                    onUserChange={handleUserChange}
                    onButtonToggle={handleButtonToggle}
                    modelType={MODEL_TYPES.REPEATED_ROOT}
                    storedData={effectiveStoredArray}
                    updatedData={rows}
                    modelName={modelName}
                    fieldsMetadata={fieldsMetadata}
                    isReadOnly={isReadOnly}
                    onColumnOrdersChange={handleColumnOrdersChange}
                    stickyHeader={modelLayoutData.sticky_header ?? true}
                    frozenColumns={modelLayoutData.frozen_columns || []}
                    filters={modelLayoutOption.filters || []}
                    onFiltersChange={handleFiltersChange}
                    uniqueValues={uniqueValues}
                    highlightDuration={modelLayoutData.highlight_duration ?? DEFAULT_HIGHLIGHT_DURATION}
                    maxRowSize={maxRowSize ?? 1}
                    selectedRows={finalSelectedRowIds}
                    lastSelectedRowId={finalLastSelectedRowId}
                    onSelectionChange={handleTableSelectionChange}
                />
            </Wrapper>
        )
    };

    return (
        <FullScreenModalOptional
            id={modelName}
            open={isMaximized}
            onClose={handleFullScreenToggle}
        >
            <ModelCard id={modelName}>
                <ModelCardHeader
                    name={modelTitle}
                    isMaximized={isMaximized}
                    onMaximizeToggle={handleFullScreenToggle}
                >
                    <MenuGroup
                        // column settings
                        columns={headCells}
                        columnOrders={modelLayoutData.column_orders || []}
                        showAll={showAll}
                        moreAll={moreAll}
                        onShowAllToggle={handleShowAllToggle}
                        onMoreAllToggle={handleMoreAllToggle}
                        onColumnsChange={handleOverrideChange}
                        onColumnOrdersChange={handleColumnOrdersChange}
                        onShowLessChange={handleShowLessChange}
                        // filter
                        filters={modelLayoutOption.filters || []}
                        fieldsMetadata={fieldsMetadata || []}
                        onFiltersChange={handleFiltersChange}
                        uniqueValues={uniqueValues}
                        // visibility
                        showMore={showMore}
                        showHidden={showHidden}
                        onVisibilityMenuClick={handleVisibilityMenuClick}
                        onVisibilityMenuDoubleClick={handleVisibilityMenuDoubleClick}
                        onShowHiddenToggle={handleShowHiddenToggle}
                        onShowMoreToggle={handleShowMoreToggle}
                        // data source colors
                        joinBy={modelLayoutData.join_by || []}
                        maxRowSize={maxRowSize ?? 0}
                        dataSourceColors={modelLayoutData.data_source_colors || []}
                        onDataSourceColorsChange={handleDataSourceColorsChange}
                        // join
                        centerJoin={modelLayoutData.joined_at_center ?? false}
                        flip={modelLayoutData.flip ?? false}
                        onJoinByChange={handleJoinByChange}
                        onCenterJoinToggle={handleCenterJoinToggle}
                        onFlipToggle={handleFlipToggle}
                        // create
                        mode={mode}
                        onCreate={handleCreate}
                        // download
                        onDownload={handleDownload}
                        // edit save
                        isReadOnly={modelLayoutOption.is_read_only ?? false}
                        onModeToggle={handleModeToggle}
                        onSave={handleSave}
                        // layout switch
                        layout={layoutType}
                        onLayoutSwitch={handleLayoutTypeChange}
                        supportedLayouts={allowedLayoutTypesRef.current}
                        // maximize
                        isMaximized={isMaximized}
                        onMaximizeToggle={handleFullScreenToggle}
                        // dynamic menu
                        commonKeys={commonKeys}
                        onButtonToggle={handleButtonToggle}
                        // button query menu
                        modelSchema={modelSchema}
                        url={url}
                        viewUrl={viewUrl}
                        autoBoundParams={autoBoundParams}
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                        onReload={handleReload}
                        onDiscard={handleDiscard}
                        // chart
                        charts={modelLayoutOption.chart_data || []}
                        onChartToggle={handleChartEnableOverrideChange}
                        chartEnableOverride={modelLayoutData.chart_enable_override || []}
                        // pivot
                        pivots={modelLayoutOption.pivot_data || []}
                        onPivotToggle={handlePivotEnableOverrideChange}
                        pivotEnableOverride={modelLayoutData.pivot_enable_override || []}
                        // table settings
                        stickyHeader={modelLayoutData.sticky_header ?? true}
                        onStickyHeaderToggle={handleStickyHeaderToggle}
                        frozenColumns={modelLayoutData.frozen_columns || []}
                        onFrozenColumnsChange={handleFrozenColumnsChange}
                        commonKeyCollapse={modelLayoutData.common_key_collapse ?? false}
                        onCommonKeyCollapseToggle={handleCommonKeyCollapseToggle}
                        columnNameOverride={modelLayoutData.column_name_override || []}
                        onColumnNameOverrideChange={handleColumnNameOverrideChange}
                        highlightUpdateOverride={modelLayoutData.highlight_update_override || []}
                        onHighlightUpdateOverrideChange={handleHighlightUpdateOverrideChange}
                        sortOrders={modelLayoutData.sort_orders || []}
                        onSortOrdersChange={handleSortOrdersChange}
                        groupedRows={groupedRows}
                        highlightDuration={modelLayoutData.highlight_duration}
                        onHighlightDurationChange={handleHighlightDurationChange}
                        noCommonKeyOverride={modelLayoutData.no_common_key_override || []}
                        onNoCommonKeyOverrideChange={handleNoCommonKeyOverrideChange}
                    />
                </ModelCardHeader>
                <ModelCardContent
                    isDisabled={isLoading || isProcessingUserActions}
                    error={error}
                    onClear={handleErrorClear}
                    isDisconnected={!isWebSocketActive(socketRef.current) && !isWebSocketDisabled}
                    onReconnect={handleReconnect}
                    isDownloading={isDownloading}
                    progress={progress}
                >
                    {renderContent()}
                </ModelCardContent>
            </ModelCard>
            <ConfirmSavePopup
                title={modelTitle}
                open={popupStatus.confirmSave}
                onClose={handleConfirmSavePopupClose}
                onSave={executeSave}
                src={changesRef.current.active}
                captionDict={captionDictRef.current}
            />
            <FormValidation
                title={modelTitle}
                open={popupStatus.formValidation}
                onClose={handleFormValidationPopupClose}
                onContinue={handleContinue}
                src={formValidationRef.current}
            />
            <ConflictPopup
                open={showConflictPopup}
                onClose={closeConflictPopup}
                onDiscardChanges={handleDiscardChanges}
                onOverwriteChanges={handleOverwriteChanges}
                conflicts={conflicts}
                title={`Conflict Detected - ${modelTitle}`}
            />
        </FullScreenModalOptional>
    )
}

export default RepeatedRootModel;