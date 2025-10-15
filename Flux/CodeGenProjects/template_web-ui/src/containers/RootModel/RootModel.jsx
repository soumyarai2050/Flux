import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { cloneDeep, get, isEqual, set } from 'lodash';
import { saveAs } from 'file-saver';
// project imports
import { DB_ID, DEFAULT_HIGHLIGHT_DURATION, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import { clearxpath, addxpath } from '../../utils/core/dataAccess';
import { generateObjectFromSchema } from '../../utils/core/schemaUtils';
import { compareJSONObjects } from '../../utils/core/objectUtils';
import { getServerUrl, isWebSocketActive } from '../../utils/network/networkUtils';
import {
    getWidgetTitle, getCrudOverrideDict, getDefaultFilterParamDict, getCSVFileName,
    updateFormValidation
} from '../../utils/ui/uiUtils';
import { createAutoBoundParams } from '../../utils/core/parameterBindingUtils';
import { cleanAllCache } from '../../cache/attributeCache';
import { useWebSocketWorker, useDownload, useModelLayout, useConflictDetection, useCountQuery } from '../../hooks';
import { massageDataForBackend, shouldUsePagination, buildDefaultFilters, extractCrudParams, convertFilterTypes } from '../../utils/core/paginationUtils';
// custom components
import { FullScreenModalOptional } from '../../components/ui/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/utility/cards';
import MenuGroup from '../../components/controls/MenuGroup';
import { ConfirmSavePopup, FormValidation } from '../../components/utility/Popup';
import CommonKeyWidget from '../../components/data-display/CommonKeyWidget';
import { DataTable } from '../../components/data-display/tables';
import { DataTree } from '../../components/data-display/trees';
import ConflictPopup from '../../components/utility/ConflictPopup';
import DataJoinGraph from '../../components/data-display/graphs/DataJoinGraph/DataJoinGraph';
import ChatView from '../../components/data-display/ChatView';
import Box from '@mui/material/Box';

function RootModel({ modelName, modelDataSource, modelDependencyMap }) {
    const { schema: projectSchema } = useSelector((state) => state.schema);

    const { schema: modelSchema, fieldsMetadata, actions, selector, isAbbreviationSource = false } = modelDataSource;
    const { storedObj, updatedObj, objId, mode, allowUpdates, isCreating, error, isLoading, popupStatus } = useSelector(selector);
    // Extract allowedOperations directly from schema's json_root
    const allowedOperations = useMemo(() => modelSchema?.json_root || null, [modelSchema]);

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
        // handleDataSourceColorsChange,
        // handleJoinByChange,
        // handleCenterJoinToggle,
        // handleFlipToggle,
        // handleSelectedChartNameChange,
        // handleChartEnableOverrideChange,
        // handleChartDataChange,
        // handleSelectedPivotNameChange,
        // handlePivotEnableOverrideChange,
        // handlePivotDataChange,
        // handleQuickFiltersChange,
        handleVisibilityMenuClick,
        handleVisibilityMenuDoubleClick,
        handleShowAllToggle,
        handleMoreAllToggle,
        handleShowHiddenToggle,
        handleShowMoreToggle,
    } = useModelLayout(modelName, objId, MODEL_TYPES.ROOT, setHeadCells, mode);

    const crudOverrideDictRef = useRef(getCrudOverrideDict(modelSchema));
    const defaultFilterParamDictRef = useRef(getDefaultFilterParamDict(modelSchema));
    const hasReadByIdWsProperty = allowedOperations?.ReadByIDWebSocketOp === true;

    // Determine if server-side pagination is enabled from schema
    const serverSidePaginationEnabled = modelSchema.server_side_pagination === true && modelSchema.is_large_db_object !== true;
    const serverSideFilterSortEnabled = modelSchema.server_side_filter_sort === true;

    // Extract ui_limit from schema unconditionally for RootModel (client-side pagination enforced)
    // RootModel always uses client-side pagination regardless of server-side settings
    const uiLimit = modelSchema.ui_get_all_limit ?? null;

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

    const uiFilters = useMemo(() => {
        const layoutFilters = modelLayoutOption.filters || [];
        return convertFilterTypes(layoutFilters, fieldsMetadata, MODEL_TYPES.ROOT);
    }, [JSON.stringify(modelLayoutOption.filters), fieldsMetadata]);

    // Construct URLs using urlOverrideDataSource (must be before useCountQuery)
    const url = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    const viewUrl = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata, undefined, true),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    // Extract params for CRUD override using crudOverrideDataSource (must be before useEffects)
    const params = useMemo(() =>
        extractCrudParams(crudOverrideDataSourceStoredObj, crudOverrideDictRef.current),
        [crudOverrideDataSourceStoredObj]
    );

    // Process data for backend consumption
    // Use modelLayoutData with JSON.stringify to handle reference stability
    const processedData = useMemo(() => {
        const rowsPerPage = modelLayoutData.rows_per_page || 25;
        const sortOrders = modelLayoutData.sort_orders || [];

        // Merge UI filters with default filters
        const mergedFilters = [...uiFilters, ...defaultFilters];

        const result = massageDataForBackend(mergedFilters, sortOrders, page, rowsPerPage);

        return result;
    }, [
        uiFilters,
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
        modelName,
        processedData.filters,
        serverSidePaginationEnabled && areDefaultFiltersReady,
        hasReadByIdWsProperty
    );

    // Derive waiting state - true if no count yet OR if count doesn't match current filters OR if loading
    const isWaitingForCount = serverSidePaginationEnabled && (count === null || isCountLoading || !isSynced);

    // Keeping it false to enforce client side pagination
    const usePagination = false;

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
    const allowedLayoutTypesRef = useRef([
        LAYOUT_TYPES.TABLE,
        LAYOUT_TYPES.TREE,
        ...(modelSchema?.widget_ui_data_element.is_graph_model ? [LAYOUT_TYPES.GRAPH] : [])
    ]);
    // refs to identify change
    const optionsRef = useRef(null);
    const captionDictRef = useRef(null);

    const hasChatContext = useMemo(() => fieldsMetadata.find((o) => o?.chat_context === true), []);

    // calculated fields
    const modelTitle = getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj);

    // Auto-bound parameters for query parameter binding
    const autoBoundParams = useMemo(() => {
        const currentData = updatedObj;
        if (!currentData || !fieldsMetadata) return {};

        return createAutoBoundParams(fieldsMetadata, currentData);
    }, [fieldsMetadata, updatedObj]);

    const { downloadCSV, isDownloading, progress } = useDownload(modelName, fieldsMetadata, null);

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
    } = useConflictDetection(storedObj, updatedObj, mode, fieldsMetadata, isCreating, allowUpdates);

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

        if (viewUrl && !isAbbreviationSource) {
            let args = { url: viewUrl };

            // Add uiLimit to args (not queryParams) - it will be handled by sliceFactory
            if (uiLimit) {
                args.uiLimit = uiLimit;
            }

            // Build query params similar to WebSocket implementation
            // JSON-stringify filters, sortOrders, and pagination to match WebSocket format
            const queryParams = {};

            // Add filters if they exist (JSON-stringified)
            if (serverSideFilterSortEnabled && processedData.filters && processedData.filters.length > 0) {
                queryParams.filters = JSON.stringify(processedData.filters);
            }

            // Add sort orders if they exist (JSON-stringified)
            if (serverSideFilterSortEnabled && processedData.sortOrders && processedData.sortOrders.length > 0) {
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
        serverSidePaginationEnabled, usePagination, isWaitingForCount, defaultFilters, uiLimit, serverSideFilterSortEnabled])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/root-model.worker.js", import.meta.url), { type: 'module' });

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
                storedObj,
                updatedObj,
                fieldsMetadata,
                page,
                rowsPerPage: modelLayoutData.rows_per_page || 25,
                sortOrders: modelLayoutData.sort_orders || [],
                filters: uiFilters || [],
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
                serverSidePaginationEnabled: false // Pass this false as in case of RootModel we want to enforce client side pagination control in both cases 
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
                objId
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
        storedObj, updatedObj, objId, fieldsMetadata, modelLayoutData, modelLayoutOption, page, mode,
        showMore, moreAll, showHidden, showAll
    ])

    const handleModelDataSourceUpdate = (updatedArray) => {
        dispatch(actions.setStoredArray(updatedArray));
    }

    const handleReconnect = () => {
        setReconnectCounter((prev) => prev + 1);
    }

    // Determine if WebSocket should be disabled
    const isWebSocketDisabled = !hasReadByIdWsProperty;
    // Wait for count query to complete before establishing WebSocket connection
    // This prevents double connection (once without pagination, once with pagination)
    // isWaitingForCount handles both: (1) initial load and (2) filter changes
    // Also wait for default filters to be ready
    const isWebSocketDelayed = isWebSocketDisabled || isWaitingForCount || !areDefaultFiltersReady;

    socketRef.current = useWebSocketWorker({
        url: (modelSchema.is_large_db_object || modelSchema.is_time_series || modelLayoutOption.depending_proto_model_for_cpp_port) ? url : viewUrl,
        modelName,
        isDisabled: isWebSocketDelayed,
        reconnectCounter,
        isAbbreviationSource,
        selector,
        onWorkerUpdate: handleModelDataSourceUpdate,
        onReconnect: handleReconnect,
        params,
        crudOverrideDict: crudOverrideDictRef.current,
        defaultFilterParamDict: defaultFilterParamDictRef.current,
        isCppModel: modelLayoutOption.depending_proto_model_for_cpp_port,
        // Parameters for unified endpoint with dynamic parameter inclusion
        // Filters now include merged default filter params
        filters: serverSideFilterSortEnabled ? processedData.filters : null,
        sortOrders: serverSideFilterSortEnabled ? processedData.sortOrders : null,
        pagination: (serverSidePaginationEnabled && usePagination) ? processedData.pagination : null,
        uiLimit: uiLimit  // Client-side limit (always enabled for RootModel)
    })

    const handleModeToggle = () => {
        const updatedMode = mode === MODES.READ ? MODES.EDIT : MODES.READ;

        // Take snapshot when entering EDIT mode for conflict detection
        if (updatedMode === MODES.EDIT) {
            takeSnapshot();
        }

        dispatch(actions.setMode(updatedMode));
        if (layoutType === LAYOUT_TYPES.GRAPH) return;
        const layoutTypeKey = updatedMode === MODES.READ ? 'view_layout' : 'edit_layout';
        if (modelLayoutData[layoutTypeKey] && modelLayoutData[layoutTypeKey] !== layoutType) {
            handleLayoutTypeChange(modelLayoutData[layoutTypeKey], updatedMode);
        }
    }

    const handleReload = () => {
        handleDiscard();
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
        const fileName = getCSVFileName(modelName);
        try {
            const csvContent = await downloadCSV(storedObj);
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
        dispatch(actions.setIsCreating(true));
    }

    const handleSave = (modifiedObj, force = false, bypassConflictCheck = false, forceConfirmSave = false) => {
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

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, fieldsMetadata, isCreating) || [null, null];
        captionDictRef.current = captionDict;

        if (!activeChanges || Object.keys(activeChanges).length === 0) {
            changesRef.current = {};
            dispatch(actions.setMode(MODES.READ));
            return;
        }
        changesRef.current.active = activeChanges;
        const changesCount = Object.keys(activeChanges).length;
        if (force || forceConfirmSave) {
            if (forceConfirmSave || changesCount === 1) {
                executeSave();
                return;
            }
        }
        dispatch(actions.setPopupStatus({ confirmSave: true }));
    }

    const executeSave = () => {
        const changeDict = cloneDeep(changesRef.current.active);
        if (changeDict[DB_ID]) {
            dispatch(actions.partialUpdate({ url, data: changeDict }));
        } else {
            dispatch(actions.create({ url, data: changeDict }));
            dispatch(actions.setMode(MODES.READ));
            dispatch(actions.setIsCreating(false));
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

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, fieldsMetadata, isCreating) || [null, null];
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

    // A helper function to decide which content to render based on layoutType
    const renderContent = () => {
        switch (layoutType) {
            case LAYOUT_TYPES.TABLE:
                return (
                    <>
                        <CommonKeyWidget mode={mode} commonkeys={commonKeys} collapse={modelLayoutData.common_key_collapse} />
                        <DataTable
                            rows={groupedRows}
                            activeRows={activeRows}
                            cells={sortedCells}
                            mode={mode}
                            sortOrders={modelLayoutData.sort_orders || []}
                            onSortOrdersChange={handleSortOrdersChange}
                            page={page}
                            rowsPerPage={modelLayoutData.rows_per_page || 25}
                            totalCount={rows.length} //In Root Models we will depend on the rows rather than count 
                            dataSourceColors={modelLayoutData.data_source_colors || []}
                            selectedId={objId}
                            onPageChange={handlePageChange}
                            onRowsPerPageChange={handleRowsPerPageChange}
                            onRowSelect={() => { }}
                            onModeToggle={handleModeToggle}
                            onUpdate={handleUpdate}
                            onUserChange={handleUserChange}
                            onButtonToggle={handleButtonToggle}
                            modelType={MODEL_TYPES.ROOT}
                            storedData={effectiveStoredData}
                            updatedData={updatedObj}
                            modelName={modelName}
                            fieldsMetadata={fieldsMetadata}
                            isReadOnly={modelLayoutOption.is_read_only}
                            onColumnOrdersChange={handleColumnOrdersChange}
                            stickyHeader={modelLayoutData.sticky_header ?? true}
                            frozenColumns={modelLayoutData.frozen_columns || []}
                            filters={uiFilters || []}
                            onFiltersChange={handleFiltersChange}
                            uniqueValues={uniqueValues}
                            highlightDuration={modelLayoutData.highlight_duration ?? DEFAULT_HIGHLIGHT_DURATION}
                            serverSideFilterSortEnabled={serverSideFilterSortEnabled}
                        />
                    </>
                );
            case LAYOUT_TYPES.TREE:
                return (
                    <DataTree
                        projectSchema={projectSchema}
                        modelName={modelName}
                        updatedData={updatedObj}
                        storedData={effectiveStoredData}
                        subtree={null}
                        mode={mode}
                        xpath={null}
                        onUpdate={handleUpdate}
                        onUserChange={handleUserChange}
                        selectedId={objId}
                        showHidden={showHidden}
                        filters={modelLayoutOption.filters || []}
                        isDisabled={isLoading || isProcessingUserActions}
                    />
                );
            case LAYOUT_TYPES.GRAPH:
                return (
                    <Box sx={{ display: 'flex', height: '100%' }}>
                        {hasChatContext && (
                            <Box sx={{ maxWidth: '30%' }}>
                                <ChatView
                                    modelName={modelName}
                                    modelDataSource={modelDataSource}
                                    onModeToggle={handleModeToggle}
                                    onSave={handleSave}
                                />
                            </Box>
                        )}
                        <DataJoinGraph modelDataSource={modelDataSource} modelName={modelName} />
                    </Box>
                );
            default:
                return null;
        }
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
                        filters={uiFilters || []}
                        fieldsMetadata={fieldsMetadata || []}
                        onFiltersChange={handleFiltersChange}
                        uniqueValues={uniqueValues}
                        serverSideFilterSortEnabled={serverSideFilterSortEnabled}
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
                        onDataSourceColorsChange={() => { }}
                        // join
                        centerJoin={modelLayoutData.joined_at_center ?? false}
                        flip={modelLayoutData.flip ?? false}
                        onJoinByChange={() => { }}
                        onCenterJoinToggle={() => { }}
                        onFlipToggle={() => { }}
                        // create
                        mode={mode}
                        onCreate={handleCreate}
                        disableCreate={rows.length > 0}
                        // download
                        onDownload={handleDownload}
                        // edit save
                        onModeToggle={handleModeToggle}
                        isReadOnly={modelLayoutOption.is_read_only ?? false}
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
                        modelType={MODEL_TYPES.ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                        isAbbreviationSource={isAbbreviationSource}
                        isCreating={isCreating}
                        onReload={handleReload}
                        onDiscard={handleDiscard}
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
                    isDisconnected={!isCreating && !isWebSocketActive(socketRef.current, isAbbreviationSource ? modelName : null) && !isWebSocketDisabled}
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

export default RootModel;