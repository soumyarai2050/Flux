import React, { useEffect, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { cloneDeep, get, isEqual, set } from 'lodash';
import { saveAs } from 'file-saver';
// project imports
import { DB_ID, DEFAULT_HIGHLIGHT_DURATION, LAYOUT_TYPES, MODEL_TYPES, MODES } from '../../constants';
import { clearxpath, addxpath } from '../../utils/core/dataAccess';
import { generateObjectFromSchema } from '../../utils/core/schemaUtils';
import { compareJSONObjects } from '../../utils/core/objectUtils';
import { getServerUrl, isWebSocketActive } from '../../utils/network/networkUtils';
import {
    getWidgetTitle, getCrudOverrideDict, getCSVFileName,
    updateFormValidation
} from '../../utils/ui/uiUtils';
import { cleanAllCache } from '../../cache/attributeCache';
import { useWebSocketWorker, useDownload, useModelLayout, useConflictDetection } from '../../hooks';
// custom components
import { FullScreenModalOptional } from '../../components/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/cards';
import MenuGroup from '../../components/MenuGroup';
import { ConfirmSavePopup, FormValidation } from '../../components/Popup';
import CommonKeyWidget from '../../components/CommonKeyWidget';
import { DataTable } from '../../components/tables';
import { DataTree } from '../../components/trees';
import ConflictPopup from '../../components/ConflictPopup';

function NonRootModel({ modelName, modelDataSource, dataSource, modelRootName }) {
    const { schema: projectSchema, schemaCollections } = useSelector((state) => state.schema);

    const { schema: modelSchema, fieldsMetadata, actions, selector, isAbbreviationSource = false } = modelDataSource;
    const modelRootFieldsMetadata = schemaCollections[modelRootName];
    const { storedObj, updatedObj, objId, mode, allowUpdates, isCreating, error, isLoading, popupStatus } = useSelector(selector);
    const { storedObj: dataSourceStoredObj } = useSelector(dataSource?.selector ?? (() => ({ storedObj: null })), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });

    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [sortedCells, setSortedCells] = useState([]);
    const [uniqueValues, setUniqueValues] = useState({});
    const [url, setUrl] = useState(modelDataSource.url);
    const [viewUrl, setViewUrl] = useState(modelDataSource.viewUrl);
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [params, setParams] = useState(null);

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
    } = useModelLayout(modelName, objId, MODEL_TYPES.NON_ROOT, setHeadCells, mode);

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
    const allowedLayoutTypesRef = useRef([LAYOUT_TYPES.TABLE, LAYOUT_TYPES.TREE]);
    // refs to identify change
    const optionsRef = useRef(null);

    // calculated fields
    const modelTitle = getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj);

    const { downloadCSV, isDownloading, progress } = useDownload(modelName, modelRootFieldsMetadata, modelName);

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
    } = useConflictDetection(storedObj, updatedObj, mode, modelRootFieldsMetadata, isCreating, allowUpdates);

    useEffect(() => {
        const url = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata);
        setUrl(url);
        const viewUrl = getServerUrl(modelSchema, dataSourceStoredObj, dataSource?.fieldsMetadata, undefined, true);
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
    }, [dataSourceStoredObj]);

    // useEffect(() => {
    //     if (viewUrl && !isAbbreviationSource) {
    //         let args = { url: viewUrl };
    //         if (crudOverrideDictRef.current?.GET_ALL) {
    //             const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
    //             if (!params && Object.keys(paramDict).length > 0) {
    //                 return;
    //             }
    //             args = { ...args, endpoint, params };
    //         }
    //         dispatch(actions.getAll({ ...args }));
    //     }
    // }, [viewUrl, params])

    useEffect(() => {
        workerRef.current = new Worker(new URL("../../workers/non-root-model.worker.js", import.meta.url));

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

    socketRef.current = useWebSocketWorker({
        url: (modelSchema.is_large_db_object || modelSchema.is_time_series || modelLayoutOption.depending_proto_model_for_cpp_port) ? url : viewUrl,
        modelName: modelRootName,
        isDisabled: false,
        reconnectCounter,
        isAbbreviationSource,
        selector,
        onWorkerUpdate: handleModelDataSourceUpdate,
        onReconnect: handleReconnect,
        params,
        crudOverrideDict: crudOverrideDictRef.current,
        isCppModel: modelLayoutOption.depending_proto_model_for_cpp_port
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

        const activeChanges = compareJSONObjects(baselineForComparison, modelUpdatedObj, modelRootFieldsMetadata, isCreating);

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

        const activeChanges = compareJSONObjects(baselineForComparison, modelUpdatedObj, modelRootFieldsMetadata, isCreating);
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

            const activeChanges = compareJSONObjects(baselineForComparison, modelUpdatedObj, modelRootFieldsMetadata);
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
                            filters={modelLayoutOption.filters || []}
                            onFiltersChange={handleFiltersChange}
                            uniqueValues={uniqueValues}
                            highlightDuration={modelLayoutData.highlight_duration ?? DEFAULT_HIGHLIGHT_DURATION}
                        />
                    </>
                );
            case LAYOUT_TYPES.TREE:
                return (
                    <DataTree
                        projectSchema={projectSchema}
                        modelName={modelRootName}
                        updatedData={updatedObj}
                        storedData={effectiveStoredData}
                        subtree={null}
                        mode={mode}
                        xpath={modelName}
                        onUpdate={handleUpdate}
                        onUserChange={handleUserChange}
                        selectedId={objId}
                        showHidden={showHidden}
                        filters={modelLayoutOption.filters || []}
                        isDisabled={isLoading || isProcessingUserActions}
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
                        modelType={MODEL_TYPES.NON_ROOT}
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
                    isDisconnected={!isCreating && !isWebSocketActive(socketRef.current, isAbbreviationSource ? modelRootName : null)}
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

export default NonRootModel;