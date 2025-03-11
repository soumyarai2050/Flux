import React, { useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, get, isObject, set } from 'lodash';
import { DB_ID, LAYOUT_TYPES, MODEL_TYPES, MODES, NEW_ITEM_ID } from '../../constants';
import { addxpath, clearxpath, compareJSONObjects, generateObjectFromSchema, getAbbreviatedCollections, getNewItem, getWidgetOptionById, getWidgetTitle, sortColumns } from '../../utils';
import * as Selectors from '../../selectors';
import { FullScreenModalOptional } from '../../components/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/cards';
import AbbreviationMergeView from '../../components/AbbreviationMergeView';
import { centerJoinToggleHandler, columnOrdersChangeHandler, dataSourceColorsChangeHandler, flipToggleHandler, joinByChangeHandler, layoutTypeChangeHandler, modeToggleHandler, overrideChangeHandler, pinnedChangeHandler, rowsPerPageChangeHandler, showLessChangeHandler, sortOrdersChangeHandler } from '../../utils/genericModelHandler';
import { getIdFromAbbreviatedKey } from '../../workerUtils';
import { cleanAllCache } from '../../utility/attributeCache';
import MenuGroup from '../../components/MenuGroup';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { actions as LayoutActions } from '../../features/uiLayoutSlice';
import { utils, writeFileXLSX } from 'xlsx';
import { ConfirmSavePopup } from '../../components/Popup';
import styles from './AbbreviationMergeModel.module.css';

const getDataSourceObj = (dataSources, sourceName) => {
    const dataSource = dataSources.find(o => o.name === sourceName);
    if (!dataSource) {
        alert('error');
    }
    return dataSource;
}


const AbbreviationMergeModel = ({ modelName, modelDataSource, dataSources }) => {
    const { schema: projectSchema } = useSelector((state) => state.schema);
    const modelLayoutOption = useSelector((state) => Selectors.selectLayout(state, modelName), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const { storedArray, storedObj, updatedObj, objId, mode, error, isLoading, isConfirmSavePopupOpen } = useSelector(modelDataSource.selector);
    const dataSourcesStoredArrayDict = useSelector((state) => Selectors.selectDataSourcesStoredArray(state, dataSources), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const dataSourcesStoredObjDict = useSelector((state) => Selectors.selectDataSourcesStoredObj(state, dataSources), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const dataSourcesUpdatedObjDict = useSelector((state) => Selectors.selectDataSourcesUpdatedObj(state, dataSources), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const dataSourcesObjIdDict = useSelector((state) => Selectors.selectDataSourcesObjId(state, dataSources), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });
    const dataSourcesUpdatedArrayDict = useMemo(() => {
        return dataSources.reduce((acc, { name }) => {
            acc[name] = dataSourcesStoredArrayDict[name];
            const updatedObj = dataSourcesUpdatedObjDict[name];
            if (updatedObj && Object.keys(updatedObj).length > 0) {
                acc[name] = acc[name].map((o) => o[DB_ID] === updatedObj[DB_ID] ? updatedObj : o);
            }
            return acc;
        }, {})
    }, [dataSourcesStoredArrayDict, dataSourcesUpdatedObjDict])

    const [isMaximized, setIsMaximized] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [isWsDisabled, setIsWsDisabled] = useState(false);
    const [page, setPage] = useState(0);
    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [filteredCells, setFilteredCells] = useState([]);
    const [isCreate, setIsCreate] = useState(false);

    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);

    const modelObjDictRef = useRef({});
    const dataSourcesObjDictRef = useRef(dataSources.reduce((acc, { name }) => {
        acc[name] = {};
        return acc;
    }, {}));
    const workerRef = useRef(null);
    const isWorkerBusyRef = useRef(false);
    const wsRefs = useRef({});
    const pendingUpdateRef = useRef(null);
    const sourceRef = useRef(null);
    const changesRef = useRef({});

    const dispatch = useDispatch();
    const [isPending, startTransition] = useTransition();

    const modelSchema = modelDataSource.schema;
    const modelFieldsMetadata = modelDataSource.fieldsMetadata;

    const allowedLayoutTypes = useMemo(() => [LAYOUT_TYPES.ABBREVIATION_MERGE, LAYOUT_TYPES.CHART, LAYOUT_TYPES.PIVOT_TABLE], [])
    const dataSourcesMetadataDict = useMemo(() => {
        return dataSources.reduce((acc, { name, fieldsMetadata }) => {
            acc[name] = fieldsMetadata;
            return acc;
        }, {})
    }, [])
    const bufferedFieldMetadata = useMemo(() => modelFieldsMetadata.find(meta => meta.key.includes('buffer')), []);
    const loadedFieldMetadata = useMemo(() => modelFieldsMetadata.find(meta => meta.key.includes('load')), []);
    const abbreviationKey = loadedFieldMetadata.abbreviated;
    const modelItemFieldsMetadata = useMemo(() => getAbbreviatedCollections(dataSourcesMetadataDict, loadedFieldMetadata), []);
    const modelItemIdField = useMemo(() => modelItemFieldsMetadata.find(meta => meta.tableTitle === DB_ID)?.key);
    const modelAbbreviatedItems = useMemo(() => get(storedObj, loadedFieldMetadata.key) || [], [storedObj]);
    const modelAbbreviatedBufferItems = useMemo(() => get(storedObj, bufferedFieldMetadata.key) || [], [storedObj]);
    const modelLayoutData = useMemo(() => getWidgetOptionById(modelLayoutOption.widget_ui_data, objId), [modelLayoutOption, objId]);
    const [layoutType, setLayoutType] = useState(modelLayoutData.view_layout);
    const sortedCells = useMemo(() => {
        return sortColumns(filteredCells, modelLayoutData.column_orders || [], modelLayoutData.join_by && modelLayoutData.join_by.length > 0, modelLayoutData.joined_at_center, modelLayoutData.flip, true);
    }, [filteredCells, modelLayoutData.column_orders, modelLayoutData.join_by, modelLayoutData.joined_at_center, modelLayoutData.flip])
    const modelTitle = useMemo(() => getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj), [storedObj]);

    const modelHandlerConfig = useMemo(() => (
        {
            modelName,
            modelType: MODEL_TYPES.ABBREVIATION_MERGE,
            dispatch,
            objId,
            layoutOption: modelLayoutOption,
            onLayoutChangeCallback: LayoutActions.setStoredObjByName
        }
    ), [objId, modelLayoutOption])

    useEffect(() => {
        dispatch(modelDataSource.actions.getAll());
        dataSources.forEach(({ actions, url }) => {
            dispatch(actions.getAll({ url }));
        })
    }, [])

    useEffect(() => {
        workerRef.current = new Worker(new URL('../../workers/abbreviation-merge-model.worker.js', import.meta.url));

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
                items: modelAbbreviatedItems,
                itemsDataDict: dataSourcesUpdatedArrayDict,
                itemProps: modelItemFieldsMetadata,
                abbreviation: abbreviationKey,
                loadedProps: loadedFieldMetadata,
                page,
                pageSize: modelLayoutData.rows_per_page || 25,
                sortOrders: modelLayoutData.sort_orders || [],
                filters: modelLayoutOption.filters || [],
                joinBy: modelLayoutData.join_by || [],
                joinSort: modelLayoutOption.join_sort || null,
                mode,
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
        modelAbbreviatedItems, dataSourcesUpdatedArrayDict, modelItemFieldsMetadata, abbreviationKey,
        loadedFieldMetadata, modelLayoutData, modelLayoutOption, page, mode, showMore, moreAll, showHidden, showAll
    ])

    useEffect(() => {
        const socket = new WebSocket(`${modelDataSource.url.replace('http', 'ws')}/get-all-${modelName}-ws`);
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
        return () => {
            if (socket) socket.close();
        }
    }, [])

    useEffect(() => {
        const intervalId = setInterval(() => {
            if (Object.keys(modelObjDictRef.current).length > 0) {
                dispatch(modelDataSource.actions.setStoredArrayWs(cloneDeep(modelObjDictRef.current)));
                modelObjDictRef.current = {};
            }
        }, 500);
        return () => clearInterval(intervalId);
    }, [])

    useEffect(() => {
        if (isWsDisabled) {
            Object.keys(wsRefs.current).forEach((name) => {
                Object.keys(wsRefs.current[name]).forEach((id) => {
                    id = id * 1;
                    wsRefs.current[name][id].close();
                    delete wsRefs.current[name][id];
                })
            });
            return;
        }

        const activeObjIds = new Set();
        if (activeRows.length > 0) {
            activeRows.forEach((groupedRow) => {
                groupedRow.forEach((row) => {
                    const id = row[modelItemIdField];
                    if (id) {
                        activeObjIds.add(id);
                    }
                });
            });
        }

        dataSources.forEach(({ name, url }) => {
            if (!dataSourcesObjDictRef.current[name]) {
                dataSourcesObjDictRef.current[name] = {};
            }
            if (!wsRefs.current[name]) {
                wsRefs.current[name] = {};
            }

            activeObjIds.forEach((id) => {
                id = id * 1;
                if (!wsRefs.current[name][id]) {
                    const ws = new WebSocket(`${url.replace('http', 'ws')}/get-${name}-ws/${id}`);
                    ws.onmessage = (event) => {
                        const obj = JSON.parse(event.data);
                        dataSourcesObjDictRef.current[name][obj[DB_ID]] = obj;
                    };
                    wsRefs.current[name][id] = ws;
                }
            })
        });

        // Close and remove WebSockets that are no longer needed
        Object.keys(wsRefs.current).forEach((name) => {
            Object.keys(wsRefs.current[name]).forEach((id) => {
                id = id * 1;
                if (!activeObjIds.has(id)) {
                    wsRefs.current[name][id].close();
                    delete wsRefs.current[name][id];
                }
            })
        });
    }, [activeRows, isWsDisabled]);

    useEffect(() => {
        const intervalId = setInterval(() => {
            dataSources.forEach(({ name, actions }) => {
                if (dataSourcesObjDictRef.current[name] && Object.keys(dataSourcesObjDictRef.current[name]).length > 0) {
                    dispatch(actions.setStoredArrayWs(cloneDeep(dataSourcesObjDictRef.current[name])));
                    dataSourcesObjDictRef.current[name] = {};
                }
            })
        }, 500);
        return () => clearInterval(intervalId);
    }, [])

    useEffect(() => {
        if (modelAbbreviatedItems && modelAbbreviatedItems.length === 0) {
            const updatedAbbreviatedItems = get(updatedObj, loadedFieldMetadata.key);
            if (updatedAbbreviatedItems && updatedAbbreviatedItems.length === 0) {
                dataSources.forEach(({ actions }) => {
                    dispatch(actions.setObjId(null));
                })
                // todo - handle ws popup on edit mode if datasource id is selected
            }
        }
    }, [modelAbbreviatedItems, updatedObj, mode])

    useEffect(() => {
        const { disable_ws_on_edit } = modelLayoutOption;
        const { edit_layout, view_layout } = modelLayoutData;
        if (mode === MODES.EDIT) {
            if (edit_layout && view_layout !== edit_layout) {
                handleLayoutTypeChange(edit_layout);
            }
            if (disable_ws_on_edit) {
                setIsWsDisabled(true);
            }
        } else if (mode === MODES.READ) {
            if (disable_ws_on_edit) {
                setIsWsDisabled(false);
            }
        }
    }, [mode, modelLayoutOption, modelLayoutData])

    const handleFullScreenToggle = () => {
        setIsMaximized((prev) => !prev);
    }

    const handleSearchQueryChange = (_, value) => {
        setSearchQuery(value);
    }

    const handleReload = () => {
        dispatch(modelDataSource.actions.getAll());
        dataSources.forEach(({ url, actions }) => {
            dispatch(actions.getAll({ url }));
        })
        changesRef.current = {};
        sourceRef.current = null;
        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        setIsCreate(false);
        setSearchQuery('');
        cleanAllCache(modelName);
        dataSources.forEach(({ name }) => {
            cleanAllCache(name);
        })
    }

    const handleLoad = () => {
        const idx = modelAbbreviatedItems.indexOf(searchQuery);
        if (idx) {
            const modifiedObj = cloneDeep(storedObj);
            get(modifiedObj, bufferedFieldMetadata.key).splice(idx, 1);
            get(modifiedObj, loadedFieldMetadata.key).push(searchQuery);
            dispatch(modelDataSource.actions.setUpdatedObj(modifiedObj));
            dispatch(modelDataSource.actions.update({ url: modelDataSource.url, data: modifiedObj }));
            const id = getIdFromAbbreviatedKey(abbreviationKey, searchQuery);
            dataSources.forEach(({ actions }) => {
                dispatch(actions.setObjId(id));
            })
            setSearchQuery('');
        } else {
            console.error(`load failed for idx: ${idx}`);
        }
    }

    const handleRowSelect = (id) => {
        dataSources.forEach(({ actions }) => {
            dispatch(actions.setObjId(id));
        })
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

    const handleDataSourceColorsChange = (updatedDataSourceColors) => {
        dataSourceColorsChangeHandler(modelHandlerConfig, updatedDataSourceColors);
    }

    const handleOverrideChange = (updatedEnableOverride, updatedDisableOverride, updatedColumns) => {
        setHeadCells(updatedColumns);
        overrideChangeHandler(modelHandlerConfig, updatedEnableOverride, updatedDisableOverride);
    }

    const handleJoinByChange = (updatedJoinBy) => {
        joinByChangeHandler(modelHandlerConfig, updatedJoinBy);
    }

    const handleLayoutTypeChange = (updatedLayoutType) => {
        layoutTypeChangeHandler(modelHandlerConfig, updatedLayoutType, allowedLayoutTypes);
    }

    const handleCenterJoinToggle = () => {
        centerJoinToggleHandler(modelHandlerConfig, !modelLayoutData.joined_at_center);
    }

    const handleFlipToggle = () => {
        flipToggleHandler(modelHandlerConfig, !modelLayoutData.flip);
    }

    const handleModeToggle = () => {
        dispatch(modelDataSource.actions.setMode(mode === MODES.READ ? MODES.EDIT : MODES.READ));
    }

    const handleSave = (updatedObj, force = false) => {
        const dataSourceStoredObj = dataSourcesStoredObjDict[sourceRef.current];
        const dataSourceUpdatedObj = updatedObj || clearxpath(cloneDeep(dataSourcesUpdatedObjDict[sourceRef.current]));
        const fieldsMetadata = dataSourcesMetadataDict[sourceRef.current];
        if (isCreate) {
            delete dataSourceUpdatedObj[DB_ID];
        }
        const activeChanges = compareJSONObjects(dataSourceStoredObj, dataSourceUpdatedObj, fieldsMetadata, isCreate);
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
        const dataSource = getDataSourceObj(dataSources, sourceRef.current);
        if (!dataSource) {
            return;
        }
        dispatch(modelDataSource.actions.setIsConfirmSavePopupOpen(true));
    }

    const executeSave = () => {
        const changeDict = cloneDeep(changesRef.current.active);
        const dataSource = getDataSourceObj(dataSources, sourceRef.current);
        if (!dataSource) {
            return;
        }
        const { url, actions } = dataSource;
        if (changeDict[DB_ID]) {
            dispatch(actions.partialUpdate({ url, data: changeDict }));
        } else {
            dispatch(actions.create({ url, data: changeDict }));
            dispatch(actions.setMode(MODES.READ));
            setIsCreate(false);
        }
        changesRef.current = {};
        handleModeToggle();
        dispatch(modelDataSource.actions.setIsConfirmSavePopupOpen(false));
        sourceRef.current = null;
    }

    const handleObjUpdate = (updatedObj, source) => {
        const dataSource = getDataSourceObj(dataSources, source);
        if (!dataSource) {
            return;
        }
        dispatch(dataSource.actions.setUpdatedObj(updatedObj));
    }

    const handleItemSelect = (id) => {
        dataSources.forEach(({ actions }) => {
            dispatch(actions.setObjId(id));
        })
    }

    const handleUserChange = (xpath, updateDict, source, validationRes) => {
        if (sourceRef.current && sourceRef.current !== source) {
            if (changesRef.current.user && Object.keys(changesRef.current.user) > 0) {
                alert('error');
                return;
            }
        }
        sourceRef.current = source;
        changesRef.current.user = {
            ...changesRef.current.user,
            ...updateDict
        }
    }

    const handleDiscard = () => {
        dispatch(modelDataSource.actions.setUpdatedObj(storedObj));
    }

    const handleButtonToggle = (e, xpath, value, objId, source, force = false) => {
        if (changesRef.current.user && Object.keys(changesRef.current.user).length > 0) {
            if (sourceRef.current && sourceRef.current !== source) {
                alert('error');
                return;
            }
        }
        sourceRef.current = source;
        if (dataSourcesObjIdDict[source] !== objId) {
            alert('error');
            return;
        }
        const dataSourceStoredObj = dataSourcesStoredObjDict[source];
        const dataSourceUpdatedObj = clearxpath(cloneDeep(dataSourcesUpdatedObjDict[source]));
        const fieldsMetadata = dataSourcesMetadataDict[source];
        set(dataSourceUpdatedObj, xpath, value);
        if (force) {
            const activeChanges = compareJSONObjects(dataSourceStoredObj, dataSourceUpdatedObj, fieldsMetadata);
            changesRef.current.active = activeChanges;
            executeSave();
        } else if (dataSourceStoredObj[DB_ID]) {
            handleSave(dataSourceUpdatedObj, force);
        }
    }

    const handleCreate = () => {
        const { schema, actions, fieldsMetadata, name } = dataSources[0];
        sourceRef.current = name;
        const newObj = generateObjectFromSchema(projectSchema, schema);
        set(newObj, DB_ID, NEW_ITEM_ID);
        const dataSourceUpdateObj = addxpath(newObj);
        dispatch(actions.setStoredObj({}));
        dispatch(actions.setUpdatedObj(dataSourceUpdateObj));
        dispatch(actions.setObjId(NEW_ITEM_ID));
        dispatch(actions.setMode(MODES.EDIT));
        const newModelAbbreviatedItem = getNewItem(fieldsMetadata, abbreviationKey);
        const clonedUpdatedObj = cloneDeep(updatedObj);
        get(clonedUpdatedObj, loadedFieldMetadata.key).push(newModelAbbreviatedItem);
        dispatch(modelDataSource.actions.setUpdatedObj(clonedUpdatedObj));
        handleModeToggle();
        setIsCreate(true);
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

    const handleErrorClear = () => {
        dispatch(modelDataSource.actions.setError(null));
    }

    const handleConfirmSavePopupClose = () => {
        dispatch(modelDataSource.actions.setIsConfirmSavePopupOpen(false));
    }

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
                        fieldsMetadata={modelItemFieldsMetadata || []}
                        isCollectionModel={true}
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
                        // button query menu
                        modelSchema={modelSchema}
                        url={modelDataSource.url}
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.ABBREVIATION_MERGE}
                        pinned={modelLayoutData.pinned || []}
                        onPinToggle={handlePinnedChange}
                    />
                </ModelCardHeader>
                <ModelCardContent isDisabled={isCreate || isLoading} error={error} onClear={handleErrorClear}>
                    <CommonKeyWidget mode={mode} commonkeys={commonKeys} />
                    <AbbreviationMergeView
                        bufferedFieldMetadata={bufferedFieldMetadata}
                        loadedFieldMetadata={loadedFieldMetadata}
                        dataSourceStoredArray={dataSourcesStoredArrayDict[dataSources[0].name]}
                        modelAbbreviatedBufferItems={modelAbbreviatedBufferItems}
                        searchQuery={searchQuery}
                        onSearchQueryChange={handleSearchQueryChange}
                        onLoad={handleLoad}
                        mode={mode}
                        rows={groupedRows}
                        activeRows={activeRows}
                        cells={sortedCells}
                        sortOrders={modelLayoutData.sort_orders || []}
                        onSortOrdersChange={handleSortOrdersChange}
                        dataSourcesStoredArrayDict={dataSourcesStoredArrayDict}
                        dataSourcesUpdatedArrayDict={dataSourcesUpdatedArrayDict}
                        selectedId={dataSourcesObjIdDict[dataSources[0].name]}
                        onForceSave={() => { }}
                        dataSourceColors={modelLayoutData.data_source_colors || []}
                        page={page}
                        rowsPerPage={modelLayoutData.rows_per_page || 25}
                        onPageChange={handlePageChange}
                        onRowsPerPageChange={handleRowsPerPageChange}
                        onRowSelect={handleRowSelect}
                        onModeToggle={handleModeToggle}
                        onUpdate={handleObjUpdate}
                        onUserChange={handleUserChange}
                        onButtonToggle={handleButtonToggle}
                    />
                </ModelCardContent>
            </ModelCard>
            <ConfirmSavePopup
                title={sourceRef.current}
                open={isConfirmSavePopupOpen}
                onClose={handleConfirmSavePopupClose}
                onSave={executeSave}
                src={changesRef.current.active}
            />
        </FullScreenModalOptional>
    )
}

export default React.memo(AbbreviationMergeModel);