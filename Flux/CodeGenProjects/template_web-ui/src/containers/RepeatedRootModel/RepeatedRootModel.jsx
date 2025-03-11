import { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, get, isObject, set } from 'lodash';
import { LAYOUT_TYPES, MODEL_TYPES, MODES, DB_ID } from '../../constants';
import * as Selectors from '../../selectors';
import { clearxpath, getWidgetOptionById, sortColumns, generateObjectFromSchema, addxpath, compareJSONObjects, getServerUrl, getApiUrlMetadata, getWidgetTitle, } from '../../utils';
import { FullScreenModalOptional } from '../../components/Modal';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../components/cards';
import MenuGroup from '../../components/MenuGroup';
import { cleanAllCache } from '../../utility/attributeCache';
import { actions as LayoutActions } from '../../features/uiLayoutSlice';
import {
    sortOrdersChangeHandler,
    rowsPerPageChangeHandler,
    layoutTypeChangeHandler,
    dataSourceColorsChangeHandler,
    columnOrdersChangeHandler,
    showLessChangeHandler,
    overrideChangeHandler,
    joinByChangeHandler,
    centerJoinToggleHandler,
    flipToggleHandler,
    pinnedChangeHandler
} from '../../utils/genericModelHandler';
import { utils, writeFileXLSX } from 'xlsx';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { DataTable, PivotTable } from '../../components/tables';
import { ConfirmSavePopup } from '../../components/Popup';
import { ChartView } from '../../components/charts';


function RepeatedRootModel({ modelName, modelDataSource, dataSource }) {
    const { schema: projectSchema } = useSelector((state) => state.schema);
    const modelLayoutOption = useSelector((state) => Selectors.selectLayout(state, modelName), (prev, curr) => {
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
    const [params, setParams] = useState(null);

    const socketRef = useRef(null);
    const workerRef = useRef(null);
    const modelObjDictRef = useRef({});
    const isWorkerBusyRef = useRef(false);
    const pendingUpdateRef = useRef(null);
    const changesRef = useRef({});

    const dispatch = useDispatch();
    const [isPending, startTransition] = useTransition();

    const allowedLayoutTypes = useMemo(() => [LAYOUT_TYPES.TABLE, LAYOUT_TYPES.PIVOT_TABLE, LAYOUT_TYPES.CHART], [])
    const modelLayoutData = useMemo(() => getWidgetOptionById(modelLayoutOption.widget_ui_data, objId), [modelLayoutOption, objId]);
    const [layoutType, setLayoutType] = useState(modelLayoutData.view_layout);
    const sortedCells = useMemo(() => {
        return sortColumns(filteredCells, modelLayoutData.column_orders || [], modelLayoutData.join_by && modelLayoutData.join_by.length > 0, modelLayoutData.joined_at_center, modelLayoutData.flip, true);
    }, [filteredCells, modelLayoutData.column_orders, modelLayoutData.join_by, modelLayoutData.joined_at_center, modelLayoutData.flip])
    const modelTitle = useMemo(() => getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj), [storedObj]);
    const crudOverrideDict = useMemo(() => {
        return modelSchema.widget_ui_data_element.override_default_crud?.reduce((acc, { ui_crud_type, query_name, ui_query_params }) => {
            const paramDict = {};
            ui_query_params.forEach(queryParam => {
                let fieldSrc = queryParam.query_param_field_src;
                fieldSrc = fieldSrc.substring(fieldSrc.indexOf('.') + 1);
                paramDict[queryParam.query_param_field] = fieldSrc;
            })
            acc[ui_crud_type] = { endpoint: `query-${query_name}`, paramDict };
            return acc;
        }, {}) || {};
    }, [])
    const uiLimit = useMemo(() => modelSchema.ui_get_all_limit ?? null, []);

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

    useEffect(() => {
        const url = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata);
        setUrl(url);
        if (dataSourceStoredObj && Object.keys(dataSourceStoredObj).length > 0 && crudOverrideDict.GET_ALL) {
            const { paramDict } = crudOverrideDict.GET_ALL;
            const params = Object.keys(paramDict).length > 0 ? {} : null;
            Object.keys(paramDict).forEach((k) => {
                const paramSrc = paramDict[k];
                const paramValue = get(dataSourceStoredObj, paramSrc);
                params[k] = paramValue;
            })
            setParams(params);
        } else {
            setParams(null);
        }
    }, [dataSourceStoredObj])

    useEffect(() => {
        if (url) {
            let args = { url };
            if (crudOverrideDict.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
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
            const { rows, groupedRows, activeRows, maxRowSize, headCells, commonKeys, filteredCells } = event.data;

            startTransition(() => {
                setRows(rows);
                setGroupedRows(groupedRows);
                setActiveRows(activeRows);
                setMaxRowSize(maxRowSize);
                setHeadCells(headCells);
                setCommonKeys(commonKeys);
                setFilteredCells(filteredCells);
                isWorkerBusyRef.current = false;

                // If a new update came in while the worker was busy, send it now.
                if (pendingUpdateRef.current) {
                    const pendingMessage = pendingUpdateRef.current;
                    pendingUpdateRef.current = null;
                    isWorkerBusyRef.current = true;
                    workerRef.current.postMessage(pendingMessage);
                }
            })
        }

        return (() => {
            if (workerRef.current) {
                workerRef.current.terminate();
                workerRef.current = null;
                isWorkerBusyRef.current = false;
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
                showAll
            }

            // If worker is busy, store the latest message in pendingUpdateRef
            if (isWorkerBusyRef.current === true) {
                pendingUpdateRef.current = messageData;
            } else {
                isWorkerBusyRef.current = true;
                workerRef.current.postMessage(messageData);
            }
        }
    }, [
        storedArray, updatedObj, fieldsMetadata, modelLayoutData, modelLayoutOption, page, mode,
        showMore, moreAll, showHidden, showAll
    ])

    useEffect(() => {
        if (!url || isWsDisabled) return;

        const wsUrl = url.replace('http', 'ws');
        let apiUrl = `${wsUrl}/get-all-${modelName}-ws`;
        if (crudOverrideDict.GET_ALL) {
            const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
            if (!params && Object.keys(paramDict).length > 0) {
                return;
            }
            apiUrl = `${wsUrl}/ws-${endpoint}`;
            if (params) {
                const paramsStr = '?' + Object.keys(params).map((k) => `${k}=${params[k]}`).join('&');
                apiUrl += paramsStr;
            }
        }

        const socket = new WebSocket(apiUrl);
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
        socket.onclose = () => { }

        return () => {
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
        }
    }, [url, params, isWsDisabled])

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
            let args = { url };
            if (crudOverrideDict.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
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
        layoutTypeChangeHandler(modelHandlerConfig, updatedLayoutType, allowedLayoutTypes);
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

    const handleModeToggle = () => {
        dispatch(actions.setMode(mode === MODES.READ ? MODES.EDIT : MODES.READ));
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

    const handleFiltersChange = () => {

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
        handleModeToggle();
    }

    const handleSave = (modifiedObj, force = false) => {
        const modelUpdatedObj = modifiedObj || clearxpath(cloneDeep(updatedObj));
        const activeChanges = compareJSONObjects(storedObj, modelUpdatedObj, fieldsMetadata);
        if (!activeChanges) {
            changesRef.current = {};
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
                return <PivotTable />;
            case LAYOUT_TYPES.CHART:
                return (
                    <ChartView
                        modelName={modelName}
                        onReload={handleReload}
                        chartRows={[]}
                        onChartDataChange={() => { }}
                        onChartDelete={() => { }}
                        fieldsMetadata={fieldsMetadata}
                        chartData={modelLayoutOption.chart_data}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        onRowSelect={handleRowSelect}
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
                        isCollectionModel={false}
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
                        supportedLayouts={allowedLayoutTypes}
                        // maximize
                        isMaximized={isMaximized}
                        onMaximizeToggle={handleFullScreenToggle}
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.REPEATED_ROOT}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                    />
                </ModelCardHeader>
                <ModelCardContent isDisabled={isLoading} error={error} onClear={handleErrorClear}>
                    {renderContent()}
                </ModelCardContent>
            </ModelCard>
            <ConfirmSavePopup
                title={modelName}
                open={isConfirmSavePopupOpen}
                onClose={handleConfirmSavePopupClose}
                onSave={executeSave}
                src={changesRef.current.active}
            />
        </FullScreenModalOptional>
    )
}

export default RepeatedRootModel;