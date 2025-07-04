import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, get, isEqual, set } from 'lodash';
import { DB_ID, DEFAULT_HIGHLIGHT_DURATION, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import * as Selectors from '../../selectors';
import {
    clearxpath, getWidgetOptionById, generateObjectFromSchema,
    addxpath, compareJSONObjects, getServerUrl, getWidgetTitle,
    getCrudOverrideDict, getCSVFileName, isWebSocketActive, removeRedundantFieldsFromRows,
    updateFormValidation
} from '../../utils/index.js';
import { FullScreenModalOptional } from '../../components/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/cards';
import MenuGroup from '../../components/MenuGroup';
import { cleanAllCache } from '../../cache/attributeCache';
import { actions as LayoutActions } from '../../features/uiLayoutSlice';
import {
    sortOrdersChangeHandler,
    rowsPerPageChangeHandler,
    layoutTypeChangeHandler,
    columnOrdersChangeHandler,
    showLessChangeHandler,
    overrideChangeHandler,
    pinnedChangeHandler,
    filtersChangeHandler,
    stickyHeaderToggleHandler,
    commonKeyCollapseToggleHandler,
    frozenColumnsChangeHandler,
    columnNameOverrideHandler,
    highlightUpdateOverrideHandler,
    highlightDurationChangeHandler,
    noCommonKeyOverrideChangeHandler,
    dataSourceColorsChangeHandler,
    joinByChangeHandler,
    centerJoinToggleHandler,
    flipToggleHandler,
    chartDataChangeHandler,
    selectedChartNameChangeHandler,
    chartEnableOverrideChangeHandler,
    selectedPivotNameChangeHandler,
    pivotEnableOverrideChangeHandler,
    pivotDataChangeHandler,
    quickFiltersChangeHandler
} from '../../utils/index.js';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { ConfirmSavePopup, FormValidation } from '../../components/Popup';
import { DataTable, PivotTable } from '../../components/tables';
import { ChartView } from '../../components/charts';
import { useWebSocketWorker, useDownload } from '../../hooks';
import { saveAs } from 'file-saver';

function RepeatedRootModel({ modelName, modelDataSource, dataSource }) {
    const { schema: projectSchema } = useSelector((state) => state.schema);
    const modelLayoutOption = useSelector((state) => Selectors.selectModelLayout(state, modelName), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const { schema: modelSchema, fieldsMetadata, actions, selector } = modelDataSource;
    const { storedArray, storedObj, updatedObj, objId, mode, error, isLoading, popupStatus } = useSelector(selector);
    const { storedObj: dataSourceStoredObj } = useSelector(dataSource?.selector ?? (() => ({ storedObj: null })), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });

    const [isMaximized, setIsMaximized] = useState(false);
    const [isWsDisabled, setIsWsDisabled] = useState(false);
    const [page, setPage] = useState(0);
    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [sortedCells, setSortedCells] = useState([]);
    const [uniqueValues, setUniqueValues] = useState({});
    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const [url, setUrl] = useState(modelDataSource.url);
    const [viewUrl, setViewUrl] = useState(modelDataSource.viewUrl);
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [rowIds, setRowIds] = useState(null);
    const [params, setParams] = useState(null);
    const modelLayoutData = useMemo(() => getWidgetOptionById(modelLayoutOption.widget_ui_data, objId), [modelLayoutOption, objId]);
    // layout type initial only available after getting modelLayoutOption
    const [layoutType, setLayoutType] = useState(modelLayoutData.view_layout);

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
    const crudOverrideDictRef = useRef(getCrudOverrideDict(modelSchema));
    const allowedLayoutTypesRef = useRef([LAYOUT_TYPES.TABLE, LAYOUT_TYPES.PIVOT_TABLE, LAYOUT_TYPES.CHART]);
    // refs to identify change
    const optionsRef = useRef(null);

    // calculated fields
    const modelTitle = useMemo(() => getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj), [storedObj]);
    const modelHandlerConfig = useMemo(() => (
        {
            modelName,
            modelType: MODEL_TYPES.REPEATED_ROOT,
            dispatch,
            objId,
            layoutOption: modelLayoutOption,
            onLayoutChangeCallback: LayoutActions.setStoredObjByName
        }
    ), [objId, modelLayoutOption])
    const uiLimit = modelSchema.ui_get_all_limit ?? null;

    const { downloadCSV, isDownloading, progress } = useDownload(modelName, fieldsMetadata, null);

    useEffect(() => {
        const url = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata);
        setUrl(url);
        const viewUrl = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata, null, true);
        setViewUrl(viewUrl);
        let updatedParams = null;
        if (dataSourceStoredObj && Object.keys(dataSourceStoredObj).length > 0 && crudOverrideDictRef.current?.GET_ALL) {
            const { paramDict } = crudOverrideDictRef.current.GET_ALL;
            if (Object.keys(paramDict).length > 0) {
                Object.keys(paramDict).forEach((k) => {
                    const paramSrc = paramDict[k];
                    const paramValue = get(dataSourceStoredObj, paramSrc);
                    if (paramValue !== null && paramValue !== undefined) {
                        if (!updatedParams) {
                            updatedParams = {};
                        }
                        updatedParams[k] = paramValue;
                    }
                })
            }
        }
        setParams((prev) => {
            if (JSON.stringify(prev) === JSON.stringify(updatedParams)) {
                return prev;
            }
            return updatedParams;
        })
    }, [dataSourceStoredObj])

    useEffect(() => {
        if (viewUrl) {
            let args = { url: viewUrl };
            if (crudOverrideDictRef.current?.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
                if (!params && Object.keys(paramDict).length > 0) {
                    return;
                }
                args = { ...args, endpoint, params, uiLimit };
            }
            dispatch(actions.getAll({ ...args }));
        }
    }, [viewUrl, params])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/repeated-root-model.worker.js", import.meta.url));

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
                joinBy: modelLayoutData.join_by || {},
                joinSort: modelLayoutOption.join_sort || null,
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
                centerJoin: modelLayoutData.joined_at_center,
                flip: modelLayoutData.flip,
                rowIds
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
        showMore, moreAll, showHidden, showAll, rowIds
    ])

    const handleModelDataSourceUpdate = (updatedArray) => {
        dispatch(actions.setStoredArray(updatedArray));
    }

    const handleReconnect = () => {
        setReconnectCounter((prev) => prev + 1);
    }

    socketRef.current = useWebSocketWorker({
        url: (modelSchema.is_large_db_object || modelSchema.is_time_series) ? url : viewUrl,
        modelName,
        isDisabled: isWsDisabled,
        reconnectCounter,
        selector,
        onWorkerUpdate: handleModelDataSourceUpdate,
        onReconnect: handleReconnect,
        params,
        crudOverrideDict: crudOverrideDictRef.current,
        uiLimit,
        isAlertModel: modelLayoutOption.is_model_alert_type
    })

    useEffect(() => {
        // const { disable_ws_on_edit } = modelLayoutOption;
        const { edit_layout, view_layout } = modelLayoutData;
        if (mode === MODES.EDIT) {
            if (edit_layout && view_layout !== edit_layout) {
                handleLayoutTypeChange(edit_layout);
                setLayoutType(edit_layout);
            }
            // if (disable_ws_on_edit) {
            //     setIsWsDisabled(true);
            // }
        } else if (mode === MODES.READ) {
            // if (disable_ws_on_edit) {
            //     setIsWsDisabled(false);
            // }
            setLayoutType(view_layout);
        }
    }, [mode, modelLayoutOption, modelLayoutData])

    const handleFullScreenToggle = () => {
        setIsMaximized((prev) => !prev);
    }

    const handleReload = () => {
        if (viewUrl) {
            let args = { url: viewUrl };
            if (crudOverrideDictRef.current?.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
                if (!params && Object.keys(paramDict).length > 0) {
                    return;
                }
                args = { ...args, endpoint, params, uiLimit };
            }
            dispatch(actions.getAll({ ...args }));
        }
        changesRef.current = {};
        formValidationRef.current = {};
        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        cleanAllCache(modelName);
    }

    const handlePageChange = (updatedPage) => {
        setPage(updatedPage);
    }

    const handleRowsPerPageChange = (updatedRowsPerPage) => {
        rowsPerPageChangeHandler(modelHandlerConfig, updatedRowsPerPage);
    }

    const handleColumnOrdersChange = (updatedColumnOrders) => {
        columnOrdersChangeHandler(modelHandlerConfig, updatedColumnOrders);
    }

    const handleSortOrdersChange = (updatedSortOrders) => {
        setPage(0);
        sortOrdersChangeHandler(modelHandlerConfig, updatedSortOrders);
    }

    const handleShowLessChange = (updatedShowLess, updatedColumns) => {
        setHeadCells(updatedColumns);
        showLessChangeHandler(modelHandlerConfig, updatedShowLess);
    }

    const handlePinnedChange = (updatedPinned) => {
        pinnedChangeHandler(modelHandlerConfig, updatedPinned);
    }

    const handleOverrideChange = (updatedEnableOverride, updatedDisableOverride, updatedColumns) => {
        setHeadCells(updatedColumns);
        overrideChangeHandler(modelHandlerConfig, updatedEnableOverride, updatedDisableOverride);
    }

    const handleLayoutTypeChange = (updatedLayoutType) => {
        const layoutTypeKey = mode === MODES.READ ? 'view_layout' : 'edit_layout';
        layoutTypeChangeHandler(modelHandlerConfig, updatedLayoutType, layoutTypeKey);
        setLayoutType(updatedLayoutType);
    }

    const handleModeToggle = () => {
        dispatch(actions.setMode(mode === MODES.READ ? MODES.EDIT : MODES.READ));
    }

    const handleFiltersChange = (updatedFilters) => {
        filtersChangeHandler(modelHandlerConfig, updatedFilters);
    }

    const handleStickyHeaderToggle = () => {
        stickyHeaderToggleHandler(modelHandlerConfig, !modelLayoutData.sticky_header);
    }

    const handleCommonKeyCollapseToggle = () => {
        commonKeyCollapseToggleHandler(modelHandlerConfig, !modelLayoutData.common_key_collapse);
    }

    const handleFrozenColumnsChange = (updatedFrozenColumns, updatedColumns) => {
        setHeadCells(updatedColumns);
        frozenColumnsChangeHandler(modelHandlerConfig, updatedFrozenColumns);
    }

    const handleColumnNameOverrideChange = (updatedColumnNameOverride) => {
        columnNameOverrideHandler(modelHandlerConfig, updatedColumnNameOverride);
    }

    const handleHighlightUpdateOverrideChange = (updatedHighlightUpdateOverride) => {
        highlightUpdateOverrideHandler(modelHandlerConfig, updatedHighlightUpdateOverride);
    }

    const handleHighlightDurationChange = (updatedHighlightDuration) => {
        highlightDurationChangeHandler(modelHandlerConfig, updatedHighlightDuration);
    }

    const handleNoCommonKeyOverrideChange = (updatedNoCommonKeyOverride, updatedColumns) => {
        setHeadCells(updatedColumns);
        noCommonKeyOverrideChangeHandler(modelHandlerConfig, updatedNoCommonKeyOverride);
    }

    const handleDataSourceColorsChange = (updatedDataSourceColors) => {
        dataSourceColorsChangeHandler(modelHandlerConfig, updatedDataSourceColors);
    }

    const handleJoinByChange = (updatedJoinBy) => {
        joinByChangeHandler(modelHandlerConfig, updatedJoinBy);
    }

    const handleCenterJoinToggle = () => {
        centerJoinToggleHandler(modelHandlerConfig, !modelLayoutData.joined_at_center);
    }

    const handleFlipToggle = () => {
        flipToggleHandler(modelHandlerConfig, !modelLayoutData.flip);
    }

    const handleSelectedChartNameChange = (updatedChartName) => {
        selectedChartNameChangeHandler(modelHandlerConfig, updatedChartName);
    }

    const handleChartEnableOverrideChange = (updatedChartEnableOverride) => {
        chartEnableOverrideChangeHandler(modelHandlerConfig, updatedChartEnableOverride);
    }

    const handleChartDataChange = (updatedChartData) => {
        chartDataChangeHandler(modelHandlerConfig, updatedChartData);
    }

    const handleSelectedPivotNameChange = (updatedPivotName) => {
        selectedPivotNameChangeHandler(modelHandlerConfig, updatedPivotName);
    }

    const handlePivotEnableOverrideChange = (updatedPivotEnableOverride) => {
        pivotEnableOverrideChangeHandler(modelHandlerConfig, updatedPivotEnableOverride);
    }

    const handlePivotDataChange = (updatedPivotData) => {
        pivotDataChangeHandler(modelHandlerConfig, updatedPivotData);
    }

    const handleQuickFiltersChange = (updatedQuickFilters) => {
        quickFiltersChangeHandler(modelHandlerConfig, updatedQuickFilters);
    }

    const handleDownload = async () => {
        let args = { url: viewUrl };
        if (crudOverrideDictRef.current?.GET_ALL) {
            const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
            if (!params && Object.keys(paramDict).length > 0) {
                return;
            }
            args = { ...args, endpoint, params };
        }
        const fileName = getCSVFileName(modelName);
        try {
            const csvContent = await downloadCSV(uiLimit ? null : storedArray, args);
            const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
            saveAs(blob, fileName);
        } catch (error) {
            console.error('CSV download failed:', error);
        }
    }

    const handleVisibilityMenuClick = (isChecked) => {
        if (isChecked) {
            setShowHidden(false);
            setShowMore(false);
        } else {
            setShowMore(true);
            setShowHidden(false);
        }
    }

    const handleVisibilityMenuDoubleClick = (isChecked) => {
        if (isChecked) {
            setShowHidden(false);
            setShowMore(false);
        } else {
            setShowHidden(true);
            setShowMore(true);
        }
    }

    const handleShowAllToggle = () => {
        setShowAll((prev) => !prev);
    }

    const handleMoreAllToggle = () => {
        setMoreAll((prev) => !prev);
    }

    const handleShowHiddenToggle = () => {
        setShowHidden((prev) => !prev);
    }

    const handleShowMoreToggle = () => {
        setShowMore((prev) => !prev);
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

    const handleSave = (modifiedObj, force = false) => {
        if (Object.keys(formValidationRef.current).length > 0) {
            dispatch(actions.setPopupStatus({ formValidation: true }));
            return;
        }
        const modelUpdatedObj = modifiedObj || clearxpath(cloneDeep(updatedObj));
        const activeChanges = compareJSONObjects(storedObj, modelUpdatedObj, fieldsMetadata);
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
    }

    const executeSave = () => {
        const changeDict = cloneDeep(changesRef.current.active);
        if (changeDict[DB_ID]) {
            dispatch(actions.partialUpdate({ url, data: changeDict }));
        } else {
            dispatch(actions.create({ url, data: changeDict }));
            dispatch(actions.setMode(MODES.READ));
        }
        changesRef.current = {};
        dispatch(actions.setMode(MODES.READ));
        dispatch(actions.setPopupStatus({ confirmSave: false }));
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
            const activeChanges = compareJSONObjects(storedObj, modelUpdatedObj, fieldsMetadata);
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
                    onChartPointSelect: setRowIds,
                    quickFilters: modelLayoutData.quick_filters ?? [],
                    onQuickFiltersChange: handleQuickFiltersChange
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
                    storedData={storedArray}
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
                <ModelCardHeader name={modelTitle}>
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
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                        onReload={handleReload}
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
                    isDisconnected={!isWebSocketActive(socketRef.current)}
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
            />
            <FormValidation
                title={modelTitle}
                open={popupStatus.formValidation}
                onClose={handleFormValidationPopupClose}
                onContinue={handleContinue}
                src={formValidationRef.current}
            />
        </FullScreenModalOptional>
    )
}

export default RepeatedRootModel;