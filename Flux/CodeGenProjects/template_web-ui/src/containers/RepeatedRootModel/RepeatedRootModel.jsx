import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, get, isEqual, set } from 'lodash';
import { DB_ID, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import * as Selectors from '../../selectors';
import {
    clearxpath, getWidgetOptionById, sortColumns, generateObjectFromSchema,
    addxpath, compareJSONObjects, getWidgetTitle, getServerUrl,
    isWebSocketAlive, getCrudOverrideDict, removeRedundantFieldsFromRows
} from '../../utils';
import { FullScreenModalOptional } from '../../components/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/cards';
import MenuGroup from '../../components/MenuGroup';
import { cleanAllCache } from '../../utility/attributeCache';
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
    dataSourceColorsChangeHandler,
    joinByChangeHandler,
    centerJoinToggleHandler,
    flipToggleHandler,
    chartDataChangeHandler
} from '../../utils/genericModelHandler';
import { utils, writeFileXLSX } from 'xlsx';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { ConfirmSavePopup } from '../../components/Popup';
import { DataTable, PivotTable } from '../../components/tables';
import { ChartView } from '../../components/charts';
import { useWebSocketWorker } from '../../hooks';

function RepeatedRootModel({ modelName, modelDataSource, dataSource }) {
    const { schema: projectSchema } = useSelector((state) => state.schema);
    const modelLayoutOption = useSelector((state) => Selectors.selectModelLayout(state, modelName), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const { schema: modelSchema, fieldsMetadata, actions, selector } = modelDataSource;
    const { storedArray, storedObj, updatedObj, objId, mode, error, isLoading, isConfirmSavePopupOpen } = useSelector(selector);
    const { storedObj: dataSourceStoredObj } = useSelector(dataSource?.selector ?? (() => ({ storedObj: null })), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });

    const [isMaximized, setIsMaximized] = useState(false);
    const [isWsDisabled, setIsWsDisabled] = useState(false);
    const [page, setPage] = useState(0);
    const [rows, setRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [sortedCells, setSortedCells] = useState([]);
    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const [url, setUrl] = useState(modelDataSource.url);
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);
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

    useEffect(() => {
        const url = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata);
        setUrl(url);
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
        if (url) {
            let args = { url };
            if (crudOverrideDictRef.current?.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
                if (!params && Object.keys(paramDict).length > 0) {
                    return;
                }
                args = { ...args, endpoint, params, uiLimit };
            }
            dispatch(actions.getAll({ ...args }));
        }
    }, [url, params])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/repeated-root-model.worker.js", import.meta.url));

        workerRef.current.onmessage = (event) => {
            const { rows, activeRows, maxRowSize, headCells, commonKeys, sortedCells } = event.data;

            startTransition(() => {
                setRows(rows);
                setActiveRows(activeRows);
                setMaxRowSize(maxRowSize);
                setHeadCells(headCells);
                setCommonKeys(commonKeys);
                setSortedCells(sortedCells);

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
                disableOverrride: modelLayoutData.disable_override || [],
                showMore,
                moreAll,
                showLess: modelLayoutData.show_less || [],
                showHidden,
                showAll,
                columnOrders: modelLayoutData.column_orders || [],
                centerJoin: modelLayoutData.joined_at_center,
                flip: modelLayoutData.flip
            }

            const updatedOptionsRef = {
                mode,
                page,
                showMore,
                moreAll,
                showHidden,
                showAll,
                modelLayoutOption,
                modelLayoutData
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
        showMore, moreAll, showHidden, showAll
    ])

    const handleModelDataSourceUpdate = (updatedArray) => {
        dispatch(actions.setStoredArray(updatedArray));
    }

    const handleReconnect = () => {
        setReconnectCounter((prev) => prev + 1);
    }

    socketRef.current = useWebSocketWorker({
        url,
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
        const { disable_ws_on_edit } = modelLayoutOption;
        const { edit_layout, view_layout } = modelLayoutData;
        if (mode === MODES.EDIT) {
            if (edit_layout && view_layout !== edit_layout) {
                handleLayoutTypeChange(edit_layout);
                setLayoutType(edit_layout);
            }
            if (disable_ws_on_edit) {
                setIsWsDisabled(true);
            }
        } else if (mode === MODES.READ) {
            if (disable_ws_on_edit) {
                setIsWsDisabled(false);
            }
            setLayoutType(view_layout);
        }
    }, [mode, modelLayoutOption, modelLayoutData])

    const handleFullScreenToggle = () => {
        setIsMaximized((prev) => !prev);
    }

    const handleReload = () => {
        if (url) {
            let args = { url };
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

    const handleChartDataChange = (updatedChartData) => {
        chartDataChangeHandler(modelHandlerConfig, updatedChartData);
    }

    const handleDownload = () => {
        const updatedRows = cloneDeep(rows);
        updatedRows.forEach((row) => {
            delete row['data-id'];
        })
        const worksheet = utils.json_to_sheet(updatedRows);
        const workbook = utils.book_new();
        utils.book_append_sheet(workbook, worksheet, 'Data');
        writeFileXLSX(workbook, `${modelName}_${new Date().toISOString()}.xlsx`);
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

    const handleConfirmSavePopupClose = () => {
        dispatch(actions.setIsConfirmSavePopupOpen(false));
        handleReload();
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
        dispatch(actions.setIsConfirmSavePopupOpen(true));
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
        dispatch(actions.setIsConfirmSavePopupOpen(false));
    }

    const handleUpdate = (updatedObj) => {
        dispatch(actions.setUpdatedObj(updatedObj));
    }

    const handleUserChange = (xpath, updateDict, source, validationRes) => {
        changesRef.current.user = {
            ...changesRef.current.user,
            ...updateDict
        }
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
        switch (layoutType) {
            case LAYOUT_TYPES.TABLE:
                return (
                    <>
                        <CommonKeyWidget mode={mode} commonkeys={commonKeys} />
                        <DataTable
                            rows={rows}
                            activeRows={activeRows}
                            cells={sortedCells}
                            mode={mode}
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
                            isReadOnly={modelLayoutOption.is_read_only}
                        />
                    </>
                );
            case LAYOUT_TYPES.PIVOT_TABLE:
                return <PivotTable pivotData={cleanedRows} />;
            case LAYOUT_TYPES.CHART:
                return (
                    <ChartView
                        modelName={modelName}
                        onReload={handleReload}
                        chartRows={cleanedRows}
                        onChartDataChange={handleChartDataChange}
                        fieldsMetadata={fieldsMetadata}
                        chartData={modelLayoutOption.chart_data || []}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        onRowSelect={() => { }}
                        mode={mode}
                        onModeToggle={handleModeToggle}
                    />
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
            <ModelCard>
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
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                        onReload={handleReload}
                    />
                </ModelCardHeader>
                <ModelCardContent
                    isDisabled={isLoading || isProcessingUserActions}
                    error={error}
                    onClear={handleErrorClear}
                    isDisconnected={!isWsDisabled && !isWebSocketAlive(socketRef.current)}
                    onReconnect={handleReconnect}
                >
                    {renderContent()}
                </ModelCardContent>
            </ModelCard>
            <ConfirmSavePopup
                title={modelTitle}
                open={isConfirmSavePopupOpen}
                onClose={handleConfirmSavePopupClose}
                onSave={executeSave}
                src={changesRef.current.active}
            />
        </FullScreenModalOptional>
    )
}

export default RepeatedRootModel;