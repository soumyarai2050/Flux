import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, isEqual, isObject, set } from 'lodash';
import { DB_ID, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import * as Selectors from '../../selectors';
import {
    clearxpath, getWidgetOptionById, sortColumns, generateObjectFromSchema,
    addxpath, compareJSONObjects, getServerUrl, getWidgetTitle,
    isWebSocketAlive
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
} from '../../utils/genericModelHandler';
import { utils, writeFileXLSX } from 'xlsx';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { DataTable } from '../../components/tables';
import { ConfirmSavePopup } from '../../components/Popup';
import DataTree from '../../components/trees/DataTree/DataTree';


function NonRootModel({ modelName, modelDataSource, dataSource, modelRootName }) {
    const { schema: projectSchema, schemaCollections } = useSelector((state) => state.schema);
    const modelLayoutOption = useSelector((state) => Selectors.selectLayout(state, modelName), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const { schema: modelSchema, fieldsMetadata, actions, selector } = modelDataSource;
    const modelRootFieldsMetadata = schemaCollections[modelRootName];
    const { storedArray, storedObj, updatedObj, objId, mode, error, isLoading, isConfirmSavePopupOpen } = useSelector(selector);
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
    const [filteredCells, setFilteredCells] = useState([]);
    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const [url, setUrl] = useState(modelDataSource.url);
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);

    const socketRef = useRef(null);
    const workerRef = useRef(null);
    const modelObjDictRef = useRef({});
    const isWorkerBusyRef = useRef({
        isBusy: false,
        hasPendingUserActions: false,
    });
    const pendingUpdateRef = useRef(null);
    const changesRef = useRef({});

    const dispatch = useDispatch();
    const [_, startTransition] = useTransition();

    const allowedLayoutTypes = useMemo(() => [LAYOUT_TYPES.TABLE, LAYOUT_TYPES.TREE], [])
    const modelLayoutData = useMemo(() => getWidgetOptionById(modelLayoutOption.widget_ui_data, objId), [modelLayoutOption, objId]);
    const [layoutType, setLayoutType] = useState(modelLayoutData.view_layout);
    const sortedCells = useMemo(() => {
        return sortColumns(filteredCells, modelLayoutData.column_orders || [], false, false, false, false);
    }, [filteredCells, modelLayoutData.column_orders])
    const modelTitle = useMemo(() => getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj), [storedObj]);

    // refs to identify change
    const optionsRef = useRef(null);

    const modelHandlerConfig = useMemo(() => (
        {
            modelName,
            modelType: MODEL_TYPES.NON_ROOT,
            dispatch,
            objId,
            layoutOption: modelLayoutOption,
            onLayoutChangeCallback: LayoutActions.setStoredObjByName
        }
    ), [objId, modelLayoutOption])

    useEffect(() => {
        const url = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata);
        setUrl(url);
    }, [dataSourceStoredObj])

    useEffect(() => {
        if (url) {
            dispatch(actions.getAll({ url }));
        }
    }, [url])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/non-root-model.worker.js", import.meta.url));

        workerRef.current.onmessage = (event) => {
            const { rows, groupedRows, activeRows, maxRowSize, headCells, commonKeys, filteredCells } = event.data;

            startTransition(() => {
                setRows(rows);
                setGroupedRows(groupedRows);
                setActiveRows(activeRows);
                setMaxRowSize(maxRowSize);
                setHeadCells(headCells);
                setCommonKeys(commonKeys);
                setFilteredCells(filteredCells);

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
                filters: modelLayoutOption.filters || [],
                mode,
                enableOverride: modelLayoutData.enable_override || [],
                disableOverrride: modelLayoutData.disable_override || [],
                showMore,
                moreAll,
                showLess: modelLayoutData.show_less || [],
                showHidden,
                showAll,
                xpath: modelName
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
        storedObj, updatedObj, fieldsMetadata, modelLayoutData, modelLayoutOption, page, mode,
        showMore, moreAll, showHidden, showAll
    ])

    useEffect(() => {
        if (!url || isWsDisabled) return;

        const socket = new WebSocket(`${url.replace('http', 'ws')}/get-all-${modelRootName}-ws`);
        socketRef.current = socket;
        socket.onmessage = (event) => {
            const updatedArrayOrObj = JSON.parse(event.data);
            if (Array.isArray(updatedArrayOrObj)) {
                updatedArrayOrObj.forEach((o) => {
                    modelObjDictRef.current[o[DB_ID]] = o;
                })
            } else if (isObject(updatedArrayOrObj)) {
                modelObjDictRef.current[updatedArrayOrObj[DB_ID]] = updatedArrayOrObj;
            } else {
                console.error(`excepected either array or object, received: ${updatedArrayOrObj}`)
            }
        }
        socket.onerror = () => {
            socketRef.current = null;
        }

        return () => {
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
        }
    }, [url, isWsDisabled])

    useEffect(() => {
        const intervalId = setInterval(() => {
            if (Object.keys(modelObjDictRef.current).length > 0) {
                dispatch(actions.setStoredArrayWs(cloneDeep(modelObjDictRef.current)));
                modelObjDictRef.current = {};
            }
        }, 500);
        return () => clearInterval(intervalId);
    }, [])

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
            dispatch(actions.getAll({ url }));
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
        const activeChanges = compareJSONObjects(storedObj, modelUpdatedObj, modelRootFieldsMetadata);
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
            const activeChanges = compareJSONObjects(storedObj, modelUpdatedObj, modelRootFieldsMetadata);
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
                            onRowSelect={() => { }}
                            onModeToggle={handleModeToggle}
                            onUpdate={handleUpdate}
                            onUserChange={handleUserChange}
                            onButtonToggle={handleButtonToggle}
                            modelType={MODEL_TYPES.ROOT}
                            storedData={storedObj}
                            updatedData={updatedObj}
                            modelName={modelName}
                            fieldsMetadata={fieldsMetadata}
                            isReadOnly={modelLayoutOption.is_read_only}
                        />
                    </>
                );
            case LAYOUT_TYPES.TREE:
                return (
                    <DataTree
                        projectSchema={projectSchema}
                        modelName={modelRootName}
                        updatedData={updatedObj}
                        storedData={storedObj}
                        subtree={null}
                        mode={mode}
                        xpath={modelName}
                        onUpdate={handleUpdate}
                        onUserChange={handleUserChange}
                        selectedId={objId}
                        showHidden={showHidden}
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
                        // download
                        onDownload={handleDownload}
                        // edit save
                        onModeToggle={handleModeToggle}
                        onSave={handleSave}
                        // layout switch
                        layout={layoutType}
                        onLayoutSwitch={handleLayoutTypeChange}
                        supportedLayouts={allowedLayoutTypes}
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
                        modelType={MODEL_TYPES.NON_ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                    />
                </ModelCardHeader>
                <ModelCardContent isDisabled={isLoading || isProcessingUserActions} error={error} onClear={handleErrorClear} isDisconnected={!isWsDisabled && !isWebSocketAlive(socketRef.current)}>
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

export default NonRootModel;