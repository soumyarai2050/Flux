import React, { useCallback, useEffect, useMemo, useRef, useState, useTransition } from 'react';
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { cloneDeep, get, isEqual, set, isObject, debounce } from 'lodash';
import { saveAs } from 'file-saver';
// project imports
import { DB_ID, DEFAULT_HIGHLIGHT_DURATION, LAYOUT_TYPES, MODEL_TYPES, MODES, NEW_ITEM_ID } from '../../constants';
import * as Selectors from '../../selectors';
import { clearxpath, addxpath } from '../../utils/core/dataAccess';
import { generateObjectFromSchema } from '../../utils/core/schemaUtils';
import { compareJSONObjects } from '../../utils/core/objectUtils';
import { getNewItem, getIdFromAbbreviatedKey } from '../../utils/core/dataUtils';
import { isWebSocketActive, getServerUrl } from '../../utils/network/networkUtils';
import {
    getWidgetTitle, getDataSourcesCrudOverrideDict, getCrudOverrideDict, getDefaultFilterParamDict, getCSVFileName, getAbbreviatedCollections,
    getDataSourceObj, updateFormValidation, getDataSourcesDefaultFilterParamDict
} from '../../utils/ui/uiUtils';
import { createAutoBoundParams } from '../../utils/core/parameterBindingUtils';
import { removeRedundantFieldsFromRows } from '../../utils/core/dataTransformation';
import { dataSourcesSelectorEquality } from '../../utils/redux/selectorUtils';
import { cleanAllCache } from '../../cache/attributeCache';
import { useWebSocketWorker, useDataSourcesWebsocketWorker, useDownload, useModelLayout, useConflictDetection, useCountQuery, useBulkPatch } from '../../hooks';
import { massageDataForBackend, convertFilterTypes, extractCrudParams, buildDefaultFilters } from '../../utils/core/paginationUtils';
import { buildAvailableModelsMap, extractChildDataSourceDependencies, resolveDataSourceDependencies } from '../../utils/dynamicSchemaUtils/dataSourceUtils';
// custom components
import { FullScreenModalOptional } from '../../components/ui/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/utility/cards';
import MenuGroup from '../../components/controls/MenuGroup';
import { ConfirmSavePopup, FormValidation } from '../../components/utility/Popup';
import CommonKeyWidget from '../../components/data-display/CommonKeyWidget';
import { PivotTable } from '../../components/data-display/tables';
import { ChartView } from '../../components/data-display/charts';
import AbbreviationMergeView from '../../components/data-display/AbbreviationMergeView';
import ConflictPopup from '../../components/utility/ConflictPopup';

function getEffectiveStoredArrayDict(dataSourcesStoredArrayDict, effectiveStoredObjDict) {

    const dict = {};
    for (const sourceName in dataSourcesStoredArrayDict) {
        // dict[sourceName] = dataSourcesStoredArrayDict[sourceName].map((o) => effectiveStoredObjDict[sourceName][DB_ID] === o[DB_ID] ? effectiveStoredObjDict[sourceName] : o);
        dict[sourceName] = dataSourcesStoredArrayDict[sourceName].map((o) => {
            if (
                effectiveStoredObjDict &&
                effectiveStoredObjDict[sourceName] &&
                effectiveStoredObjDict[sourceName][DB_ID] === o[DB_ID]
            ) {
                return effectiveStoredObjDict[sourceName];
            }
            return o;
        });
    };

    return dict;
}

function AbbreviationMergeModel({ modelName, modelDataSource, modelDependencyMap, dataSources }) {
    const { schema: projectSchema, schemaCollections } = useSelector((state) => state.schema);

    const { schema: modelSchema, fieldsMetadata: modelFieldsMetadata, actions, selector } = modelDataSource;
    const { storedObj, updatedObj, objId, mode, isCreating, error, isLoading, popupStatus } = useSelector(selector);
    // Extract allowedOperations directly from schema's json_root
    const allowedOperations = useMemo(() => modelSchema?.json_root || null, [modelSchema]);
    const {
        storedArrayDict: dataSourcesStoredArrayDict,
        storedObjDict: dataSourcesStoredObjDict,
        updatedObjDict: dataSourcesUpdatedObjDict,
        objIdDict: dataSourcesObjIdDict,
        modeDict: dataSourcesModeDict,
    } = useSelector((state) => Selectors.selectDataSourcesDictionaries(state, dataSources), dataSourcesSelectorEquality);
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

    const connectionDependency = useMemo(() => {
        return modelSchema.connection_dependency?.[0];
    }, [modelSchema]);

    // Extract data sources from modelDependencyMap
    const urlOverrideDataSource = modelDependencyMap?.urlOverride ?? null;
    const crudOverrideDataSource = modelDependencyMap?.crudOverride ?? null;
    const defaultFilterDataSource = modelDependencyMap?.defaultFilter ?? null;
    const idDependentDataSource = modelDependencyMap?.idDependent ?? null;

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
    const idDependentSelector = useMemo(
        () => idDependentDataSource?.selector ?? (() => ({ objId: null })),
        [idDependentDataSource]
    );

    // Subscribe to each data source's Redux store using shallow equality
    const { storedObj: urlOverrideDataSourceStoredObj } = useSelector(urlOverrideSelector, shallowEqual);
    const { storedObj: crudOverrideDataSourceStoredObj } = useSelector(crudOverrideSelector, shallowEqual);
    const { storedObj: defaultFilterDataSourceStoredObj } = useSelector(defaultFilterSelector, shallowEqual);
    const { objId: idDependentDataSourceObjId } = useSelector(idDependentSelector, shallowEqual);

    // Build available dependency providers for child data sources
    // Includes parent model + parent's 4 dependencies
    const childAvailableDependencyProviders = useMemo(() => {
        const providers = buildAvailableModelsMap([
            // Parent Model
            { name: modelName, storedObj, fieldsMetadata: modelFieldsMetadata },
            // Parent's Dependencies
            { name: urlOverrideDataSource?.name, storedObj: urlOverrideDataSourceStoredObj, fieldsMetadata: urlOverrideDataSource?.fieldsMetadata },
            { name: crudOverrideDataSource?.name, storedObj: crudOverrideDataSourceStoredObj, fieldsMetadata: crudOverrideDataSource?.fieldsMetadata },
            { name: defaultFilterDataSource?.name, storedObj: defaultFilterDataSourceStoredObj, fieldsMetadata: defaultFilterDataSource?.fieldsMetadata },
            { name: idDependentDataSource?.name, storedObj: idDependentDataSourceObjId ? { [DB_ID]: idDependentDataSourceObjId } : null, fieldsMetadata: idDependentDataSource?.fieldsMetadata }
        ]);
        return providers;
    }, [
        modelName, storedObj, modelFieldsMetadata,
        urlOverrideDataSource, urlOverrideDataSourceStoredObj,
        crudOverrideDataSource, crudOverrideDataSourceStoredObj,
        defaultFilterDataSource, defaultFilterDataSourceStoredObj,
        idDependentDataSource, idDependentDataSourceObjId
    ]);

    // Extract child data source dependency requirements from schemas (Note idDepedency is not supported by child as they controlled by collection)
    const childDependencyRequirements = useMemo(() => {
        return extractChildDataSourceDependencies(dataSources, Object.keys(childAvailableDependencyProviders));
    }, [dataSources, childAvailableDependencyProviders]);

    // Resolve dependencies - map requirements to actual storedObj + fieldsMetadata
    const resolvedChildDependencies = useMemo(() => {
        return resolveDataSourceDependencies(childDependencyRequirements, childAvailableDependencyProviders);
    }, [childDependencyRequirements, childAvailableDependencyProviders]);

    // Construct URLs using urlOverrideDataSource (must be before useCountQuery)
    const url = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    // HTTP View URL - always uses view URL for HTTP GET/GET_ALL requests
    const httpViewUrl = useMemo(() =>
        getServerUrl(modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata, undefined, true),
        [modelSchema, urlOverrideDataSourceStoredObj, urlOverrideDataSource?.fieldsMetadata]
    );

    // Build URL configuration dict for child data sources using resolved dependencies
    // Similar to parent, calculate url, httpViewUrl, and wsViewUrl for each child data source
    const dataSourcesUrlConfig = useMemo(() => {
        return dataSources.reduce((acc, { name, schema, modelLayoutOption }) => {
            // Check for a specific urlOverride dependency for the current child data source
            const childUrlOverrideDep = resolvedChildDependencies[name]?.urlOverride;

            // Determine the stored object and metadata to use for URL generation
            const urlStoredObj = childUrlOverrideDep?.storedObj || urlOverrideDataSourceStoredObj;
            const urlFieldsMetadata = childUrlOverrideDep?.fieldsMetadata || urlOverrideDataSource?.fieldsMetadata;

            // Base URL (for mutations and base operations)
            const childUrl = getServerUrl(schema, urlStoredObj, urlFieldsMetadata, undefined, false);

            // HTTP View URL (always uses view URL for HTTP GET/GET_ALL requests)
            const childHttpViewUrl = getServerUrl(schema, urlStoredObj, urlFieldsMetadata, undefined, true);

            // Determine if WebSocket should use base URL instead of view URL
            const childShouldUseBaseUrl = schema.is_large_db_object || schema.is_time_series ||
                connectionDependency?.use_cpp_port ||
                false; // Child data sources don't support server-side pagination/filter/sort

            // WebSocket View URL - uses base URL when childShouldUseBaseUrl, otherwise uses view URL
            const childWsViewUrl = childShouldUseBaseUrl ? childUrl : childHttpViewUrl;

            acc[name] = {
                url: childUrl,
                httpViewUrl: childHttpViewUrl,
                wsViewUrl: childWsViewUrl
            };
            return acc;
        }, {});
    }, [dataSources, resolvedChildDependencies, urlOverrideDataSourceStoredObj, urlOverrideDataSource]);

    const [searchQuery, setSearchQuery] = useState([]);
    const [rows, setRows] = useState([]);
    const [groupedRows, setGroupedRows] = useState([]);
    const [activeRows, setActiveRows] = useState([]);
    const [activeIds, setActiveIds] = useState([]);
    const [maxRowSize, setMaxRowSize] = useState(null);
    const [headCells, setHeadCells] = useState([]);
    const [columns, setColumns] = useState([]);
    const [commonKeys, setCommonKeys] = useState([]);
    const [sortedCells, setSortedCells] = useState([]);
    const [uniqueValues, setUniqueValues] = useState({});
    // const [url, setUrl] = useState(modelDataSource.url);
    // const [httpViewUrl, setHttpViewUrl] = useState(modelDataSource.viewUrl);
    const [isProcessingUserActions, setIsProcessingUserActions] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [rowIds, setRowIds] = useState(null);
    const [dataSourcesParams, setDataSourcesParams] = useState(null);
    const [objIdToSourceIdDict, setObjIdToSourceIdDict] = useState({});

    // Multiselect state for chart-table synchronization (chart-specific)
    const [chartMultiSelectState, setChartMultiSelectState] = useState({});

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
    } = useModelLayout(modelName, objId, MODEL_TYPES.ABBREVIATION_MERGE, setHeadCells, mode);

    // Current chart's multiselect state (derived after modelLayoutData is available)
    const currentChartName = modelLayoutData.selected_chart_name;
    const multiSelectedRows = chartMultiSelectState[currentChartName]?.selectedRows || [];
    const lastSelectedRowId = chartMultiSelectState[currentChartName]?.lastSelectedRowId || null;

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
    const sourceRef = useRef(null);
    const availableModelNames = useMemo(() => Object.keys(schemaCollections), [schemaCollections]);
    const crudOverrideDictRef = useRef(getCrudOverrideDict(modelSchema, availableModelNames));
    const defaultFilterParamDictRef = useRef(getDefaultFilterParamDict(modelSchema, availableModelNames));

    // Build CRUD override dict for child data sources
    const dataSourcesCrudOverrideDictRef = useRef(getDataSourcesCrudOverrideDict(dataSources, availableModelNames));

    // Build default filter param dict for child data sources
    const dataSourcesDefaultFilterParamDict = useMemo(() => {
        return getDataSourcesDefaultFilterParamDict(dataSources, availableModelNames);
    }, [dataSources, availableModelNames]);

    // Build default filters for each child data source using resolved dependencies
    const dataSourcesDefaultFilters = useMemo(() => {
        const filtersDict = {};

        dataSources.forEach(({ name, schema }) => {
            const paramDict = dataSourcesDefaultFilterParamDict?.[name];
            if (!paramDict) return;

            // Determine source storedObj for default filter resolution
            let sourceStoredObj = null;

            // First check if child has explicit defaultFilter dependency
            const childDeps = resolvedChildDependencies[name];
            if (childDeps?.defaultFilter?.storedObj) {
                sourceStoredObj = childDeps.defaultFilter.storedObj;
            } else {
                // Otherwise, check schema's param_src_model_name and resolve from available providers
                const paramSrcModelName = schema?.default_filter_param?.[0]?.param_src_model_name;
                if (paramSrcModelName && childAvailableDependencyProviders[paramSrcModelName]) {
                    sourceStoredObj = childAvailableDependencyProviders[paramSrcModelName].storedObj;
                } else {
                    // Final fallback to parent's defaultFilterDataSourceStoredObj
                    sourceStoredObj = defaultFilterDataSourceStoredObj;
                }
            }

            // Build default filters array for this data source
            const filtersArray = buildDefaultFilters(sourceStoredObj, paramDict);

            if (filtersArray.length > 0) {
                filtersDict[name] = filtersArray;
            }
        });

        return filtersDict;
    }, [dataSources, dataSourcesDefaultFilterParamDict, resolvedChildDependencies, childAvailableDependencyProviders, defaultFilterDataSourceStoredObj]);

    const allowedLayoutTypesRef = useRef([LAYOUT_TYPES.ABBREVIATION_MERGE, LAYOUT_TYPES.PIVOT_TABLE, LAYOUT_TYPES.CHART]);
    // refs to identify change
    const optionsRef = useRef(null);
    const captionDictRef = useRef(null);
    const baselineDictionaryRef = useRef(null);

    // calculated fields
    const effectiveStoredArrayDict = getEffectiveStoredArrayDict(dataSourcesStoredArrayDict, baselineDictionaryRef.current || {});

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
    const modelAbbreviatedItems = useMemo(() => get(storedObj, loadedFieldMetadata.key) || [], [storedObj]);
    const modelAbbreviatedBufferItems = useMemo(() => get(storedObj, bufferedFieldMetadata.key) || [], [storedObj]);
    const modelTitle = getWidgetTitle(modelLayoutOption, modelSchema, modelName, storedObj);

    // Auto-bound parameters for query parameter binding - uses selected row from combined abbreviation view
    const autoBoundParams = useMemo(() => {
        // For AbbreviationMergeModel, use the selected row data from the first data source
        const currentData = dataSourcesUpdatedObjDict[dataSources[0]?.name];
        if (!currentData || !modelItemFieldsMetadata) return {};

        return createAutoBoundParams(modelItemFieldsMetadata, currentData);
    }, [modelItemFieldsMetadata, dataSourcesUpdatedObjDict]);

    const { downloadCSV, isDownloading, progress } = useDownload(modelName, modelItemFieldsMetadata, null, MODEL_TYPES.ABBREVIATION_MERGE);

    const hasReadByIdWsProperty = allowedOperations?.ReadByIDWebSocketOp === true;

    // Collection views do not support server-side-pagination as the backend is not aware of these tables
    const serverSidePaginationEnabled = false;
    const serverSideFilterSortEnabled = false;

    // Determine if WebSocket should use base URL instead of view URL
    const shouldUseBaseUrl = useMemo(() =>
        modelSchema.is_large_db_object || modelSchema.is_time_series ||
        connectionDependency?.use_cpp_port ||
        serverSidePaginationEnabled || serverSideFilterSortEnabled,
        [modelSchema.is_large_db_object, modelSchema.is_time_series,
        connectionDependency?.use_cpp_port,
            serverSidePaginationEnabled, serverSideFilterSortEnabled]
    );

    // WebSocket View URL - uses base URL when shouldUseBaseUrl, otherwise uses view URL
    const wsViewUrl = useMemo(() =>
        shouldUseBaseUrl ? url : httpViewUrl,
        [shouldUseBaseUrl, url, httpViewUrl]
    );

    // Extract params for CRUD override using crudOverrideDataSource (for main model)
    const params = useMemo(() => {
        const extractedParams = extractCrudParams(crudOverrideDataSourceStoredObj, crudOverrideDictRef.current);
        return extractedParams;
    }, [crudOverrideDataSourceStoredObj]);

    // Build default filters in array format using buildDefaultFilters
    const defaultFilters = useMemo(() => {
        const paramDict = defaultFilterParamDictRef.current;

        if (!paramDict) return [];

        // Use buildDefaultFilters to convert paramDict to array format
        const filtersArray = buildDefaultFilters(defaultFilterDataSourceStoredObj, paramDict);

        return filtersArray;
    }, [defaultFilterDataSourceStoredObj]);

    // Check if default filters are ready (all required 'src' type params have values)
    const areDefaultFiltersReady = useMemo(() => {
        const paramDict = defaultFilterParamDictRef.current;
        if (!paramDict) return true; // No filters defined, so ready

        // Check if all 'src' type params have their values available
        for (const paramName in paramDict) {
            const paramConfig = paramDict[paramName];
            if (paramConfig.type === 'src') {
                // Need to wait for data source to be loaded
                if (!defaultFilterDataSourceStoredObj || !get(defaultFilterDataSourceStoredObj, paramConfig.value)) {
                    return false;
                }
            }
        }
        return true;
    }, [defaultFilterDataSourceStoredObj]);

    const uiFilters = useMemo(() => {
        const layoutFilters = modelLayoutOption.filters || [];
        return convertFilterTypes(layoutFilters, modelItemFieldsMetadata, MODEL_TYPES.ABBREVIATION_MERGE);
    }, [JSON.stringify(modelLayoutOption.filters), modelItemFieldsMetadata]);

    // Process data for backend consumption
    // Use modelLayoutData with JSON.stringify to handle reference stability
    // IMPORTANT: Only default filters go to backend, UI filters are client-side only
    const processedData = useMemo(() => {
        const rowsPerPage = modelLayoutData.rows_per_page || 25;
        const sortOrders = modelLayoutData.sort_orders || [];

        // Only default filters go to backend (UI filters are view-only, not merged)
        const result = massageDataForBackend(defaultFilters, sortOrders, page, rowsPerPage);

        return result;
    }, [
        defaultFilters,
        JSON.stringify(modelLayoutData.sort_orders),
        page,
        modelLayoutData.rows_per_page
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
        serverSidePaginationEnabled,
        hasReadByIdWsProperty
    );

    // Derive waiting state - true if no count yet OR if count doesn't match current filters OR if loading
    const isWaitingForCount = serverSidePaginationEnabled && (count === null || isCountLoading || !isSynced);

    //Keeping it false to enforce client side pagination
    const usePagination = false;


    // Conflict detection for handling websocket updates during editing
    const {
        showConflictPopup,
        conflicts,
        closeConflictPopup,
        getBaselineForComparison,
        setConflicts, // needed for manual trigger
        setShowConflictPopup, // needed for manual trigger
    } = useConflictDetection(storedObj, updatedObj, mode, modelFieldsMetadata, isCreating);

    const takeSnapshot = () => {
        // Disable updates for all data sources
        dataSources.forEach(({ actions: dsActions }) => {
            dispatch(dsActions.setAllowUpdates(false));
        });

        const baselineDict = {};
        for (const sourceName in dataSourcesStoredObjDict) {
            baselineDict[sourceName] = cloneDeep(dataSourcesStoredObjDict[sourceName]);
        }
        baselineDictionaryRef.current = baselineDict;
    }

    const clearSnapshot = () => {
        dataSources.forEach(({ actions: dsActions }) => {
            dispatch(dsActions.setAllowUpdates(true));
        })
        baselineDictionaryRef.current = null;
    }

    const checkAndShowConflicts = (modifiedObj) => {
        const sourceName = sourceRef.current;
        // Check for conflicts by comparing baseline snapshot with current server state.
        if (baselineDictionaryRef.current) {
            const baselineSnapshot = baselineDictionaryRef.current[sourceName];
            const currentServerState = dataSourcesStoredObjDict[sourceName];

            // Detect changes between baseline and server state.
            if (baselineSnapshot && !isEqual(baselineSnapshot, currentServerState)) {
                // Prepare user-updated object and compare with baseline for conflicts.
                const userUpdatedObj = modifiedObj || clearxpath(cloneDeep(dataSourcesUpdatedObjDict[sourceName]));
                const [userChanges, captionDict] = compareJSONObjects(baselineSnapshot, userUpdatedObj, dataSourcesMetadataDict[sourceName], isCreating) || [null, null];
                captionDictRef.current = captionDict;

                // Identify and store conflicts if user and server data differ.
                if (userChanges && Object.keys(userChanges).length > 0) {
                    console.error("CONFLICT DETECTED! Server data and user data both changed.");
                    const conflictsResult = [];
                    // Recursively find exact conflicts in nested objects.
                    const findExactConflicts = (changes, snapshot, server, path = '') => {
                        for (const key in changes) {
                            if (key === DB_ID) continue;
                            const newPath = path ? `${path}.${key}` : key;
                            const userValue = get(changes, key);
                            const snapshotValue = get(snapshot, key);
                            const serverValue = get(server, key);
                            // Handle nested objects recursively.
                            if (isObject(userValue) && !Array.isArray(userValue)) {
                                if (snapshotValue && serverValue) {
                                    findExactConflicts(userValue, snapshotValue, serverValue, newPath);
                                }
                            } else if (!isEqual(snapshotValue, serverValue)) {
                                // Log conflicts for differing values.
                                conflictsResult.push({ field: newPath, yourValue: userValue, serverValue: serverValue });
                            }
                        }
                    };
                    findExactConflicts(userChanges, baselineSnapshot, currentServerState);
                    if (conflictsResult.length > 0) {
                        // Show conflict popup if conflicts are found.
                        setConflicts(conflictsResult);
                        setShowConflictPopup(true);
                        return true; // Indicate conflict found
                    }
                }
            }
        }
        return false; // Indicate no conflict found
    }

    useEffect(() => {
        let updatedParams = null;
        if (storedObj && Object.keys(storedObj).length > 0) {
            dataSources.forEach(({ name }) => {
                const crudOverrideDict = dataSourcesCrudOverrideDictRef.current?.[name];
                if (crudOverrideDict?.GET_ALL) {
                    const { paramDict } = crudOverrideDict.GET_ALL;
                    if (paramDict && Object.keys(paramDict).length > 0) {
                        // Check if this child data source has a crudOverride dependency
                        const childDeps = resolvedChildDependencies[name];
                        const sourceStoredObj = childDeps?.crudOverride?.storedObj || storedObj;

                        // Only extract params if source has data
                        if (sourceStoredObj && Object.keys(sourceStoredObj).length > 0) {
                            Object.keys(paramDict).forEach((k) => {
                                const paramSrc = paramDict[k];
                                const paramValue = get(sourceStoredObj, paramSrc);
                                if (paramValue !== null && paramValue !== undefined) {
                                    if (!updatedParams) {
                                        updatedParams = {
                                            [name]: {}
                                        }
                                    } else if (!updatedParams[name]) {
                                        updatedParams[name] = {};
                                    }
                                    updatedParams[name][k] = paramValue;
                                }
                            })
                        }
                    }
                }
            })
        }
        setDataSourcesParams((prev) => {
            if (JSON.stringify(prev) === JSON.stringify(updatedParams)) {
                return prev;
            }
            return updatedParams;
        });
    }, [storedObj, dataSources, resolvedChildDependencies])

    useEffect(() => {
        if (hasReadByIdWsProperty) {
            return;
        }

        // Wait for default filters to be ready before executing GETALL
        if (!areDefaultFiltersReady) {
            return;
        }

        let args = { url: httpViewUrl };

        // Handle CRUD override - merge custom endpoint and params
        if (crudOverrideDictRef.current?.GET_ALL) {
            const { endpoint, paramDict } = crudOverrideDictRef.current.GET_ALL;
            // If paramDict requires params but they're not ready yet, wait
            if (paramDict && Object.keys(paramDict).length > 0 && !params) {
                return;
            }
            // Merge CRUD params
            args = { ...args, endpoint, params };
        }

        // for GET_ALL only add processed default filters
        if (processedData.filters && processedData.filters.length > 0) {
            args = { ...args, filters: processedData.filters };
        }

        dispatch(actions.getAll(args));
    }, [httpViewUrl, JSON.stringify(params), JSON.stringify(processedData.filters), hasReadByIdWsProperty])

    useEffect(() => {
        if (dataSourcesCrudOverrideDictRef.current) return;
        if (bufferedFieldMetadata.hide) return;
        dataSources.forEach(({ actions: dsActions, name, url, viewUrl }) => {
            // Use HTTP View URL from config if available, otherwise use default viewUrl
            const effectiveUrl = dataSourcesUrlConfig[name]?.httpViewUrl || viewUrl;
            let args = { url: effectiveUrl };

            const crudOverrideDict = dataSourcesCrudOverrideDictRef.current?.[name];
            const params = dataSourcesParams?.[name];
            const filters = dataSourcesDefaultFilters?.[name];

            if (crudOverrideDict?.GET_ALL) {
                const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
                if (!params && Object.keys(paramDict).length > 0) {
                    return;
                }
                args = { ...args, endpoint, params };
            }

            // Add default filters if available
            if (filters && filters.length > 0) {
                args = { ...args, filters };
            }

            dispatch(dsActions.getAll({ ...args }));
        })
    }, [dataSourcesParams, dataSourcesDefaultFilters, dataSourcesUrlConfig])

    useEffect(() => {
        workerRef.current = new Worker(new URL('../../workers/abbreviation-merge-model.worker.js', import.meta.url), { type: 'module' });

        workerRef.current.onmessage = (event) => {
            const { rows, groupedRows, activeRows, maxRowSize, headCells, columns, commonKeys, uniqueValues, sortedCells, activeIds } = event.data;

            startTransition(() => {
                setRows(rows);
                setGroupedRows(groupedRows);
                setActiveRows(activeRows);
                setActiveIds(activeIds);
                setMaxRowSize(maxRowSize);
                setHeadCells(headCells);
                setColumns(columns);
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
                items: modelAbbreviatedItems,
                itemsDataDict: dataSourcesUpdatedArrayDict,
                itemProps: modelItemFieldsMetadata,
                abbreviation: abbreviationKey,
                loadedProps: loadedFieldMetadata,
                page,
                pageSize: modelLayoutData.rows_per_page || 25,
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
                joinBy: modelLayoutData.join_by || {},
                joinSort: modelLayoutOption.join_sort || null,
                centerJoin: modelLayoutData.joined_at_center,
                flip: modelLayoutData.flip,
                rowIds: layoutType === LAYOUT_TYPES.PIVOT_TABLE ? rowIds : null,
                serverSidePaginationEnabled: false // Pass this false as in case of Abbreviation Merge Model we want to enforce client side pagination control in both cases 
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
                rowIds: layoutType === LAYOUT_TYPES.PIVOT_TABLE ? rowIds : null,
                objId
            }

            if (optionsRef.current?.objId !== objId) {
                setRowIds(null);
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
        modelAbbreviatedItems, dataSourcesUpdatedArrayDict, modelItemFieldsMetadata, abbreviationKey,
        loadedFieldMetadata, modelLayoutData, modelLayoutOption, page, mode, showMore, moreAll, showHidden, showAll, rowIds, objId
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
    // Also wait for default filters to be ready before connecting
    const isWebSocketDelayed = isWebSocketDisabled || isWaitingForCount || !areDefaultFiltersReady;

    socketRef.current = useWebSocketWorker({
        url: wsViewUrl,
        modelName,
        isDisabled: isWebSocketDelayed,
        reconnectCounter,
        selector,
        onWorkerUpdate: handleModelDataSourceUpdate,
        onReconnect: handleReconnect,
        params,
        crudOverrideDict: crudOverrideDictRef.current,
        isCppModel: connectionDependency?.use_cpp_port,
        // Parameters for unified endpoint with dynamic parameter inclusion
        // Pass processed default filters to WebSocket for collection views
        filters: processedData.filters,
        sortOrders: null,
        pagination: null
    })

    useDataSourcesWebsocketWorker({
        dataSources,
        isWsDisabled: false,
        reconnectCounter,
        onReconnect: handleReconnect,
        storedArrayDict: dataSourcesStoredArrayDict,
        dataSourcesCrudOverrideDict: dataSourcesCrudOverrideDictRef.current,
        dataSourcesParams,
        dataSourcesDefaultFilters,
        connectionByGetAll: modelLayoutOption.ws_connection_by_get_all,
        activeIds,
        dataSourcesUrlConfig
    });

    // ID Dependency: Auto-assign parent objId based on dependent model's selection
    useEffect(() => {
        if (idDependentDataSource && idDependentDataSourceObjId !== null && objId !== idDependentDataSourceObjId) {
            // Dispatch setObjId to update parent model's ID to match the dependent model's ID
            dispatch(actions.setObjId(idDependentDataSourceObjId));
        }
    }, [idDependentDataSourceObjId, idDependentDataSource, objId]);

    useEffect(() => {
        if (modelAbbreviatedItems && !isCreating) {
            if (modelAbbreviatedItems.length === 0) {
                const updatedAbbreviatedItems = get(updatedObj, loadedFieldMetadata.key);
                if (updatedAbbreviatedItems && updatedAbbreviatedItems.length === 0) {
                    dataSources.forEach(({ actions: dsActions }) => {
                        dispatch(dsActions.setObjId(null));
                    })
                    handleSelectedSourceIdChangeHandler(null);
                    // todo - handle ws popup on edit mode if datasource id is selected
                }
            }
            else {
                const dsObjId = dataSourcesObjIdDict[dataSources[0].name];
                const sourceObjId = objIdToSourceIdDict[String(objId)] ?? null;
                if (!sourceObjId) {
                    if (!dsObjId || !activeIds.includes(dsObjId)) {
                        const id = getIdFromAbbreviatedKey(abbreviationKey, modelAbbreviatedItems[0]);
                        dataSources.forEach(({ actions: dsActions }) => {
                            dispatch(dsActions.setObjId(id));
                        })
                        handleSelectedSourceIdChangeHandler(id);
                    }
                } else {
                    if (dsObjId !== sourceObjId) {
                        dataSources.forEach(({ actions: dsActions }) => {
                            dispatch(dsActions.setObjId(sourceObjId));
                        })
                    }
                }
            }
        }
    }, [modelAbbreviatedItems, updatedObj, mode, objId, JSON.stringify(objIdToSourceIdDict)])

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
    };

    const handleReload = () => {
        handleDiscard();
        setSearchQuery([]);
        // Clear chart-specific multiselect state on reload
        setChartMultiSelectState({});
        dispatch(actions.setIsCreating(false));
        dataSources.forEach(({ actions: dsActions }) => {
            dispatch(dsActions.setIsCreating(false));
        })
        handleReconnect();
    }

    const cleanModelCache = () => {
        changesRef.current = {};
        formValidationRef.current = {};
        sourceRef.current = null;
        cleanAllCache(modelName);
        dataSources.forEach(({ name }) => {
            cleanAllCache(name);
        })
    }

    const handleDiscard = () => {
        dispatch(actions.setUpdatedObj(storedObj));
        dataSources.forEach(({ name, actions: dsActions }) => {
            const dsStoredObj = dataSourcesStoredObjDict[name];
            const dsUpdatedObj = addxpath(cloneDeep(dsStoredObj));
            dispatch(dsActions.setUpdatedObj(dsUpdatedObj));
        })

        // Clear creating states like handleReload does
        dispatch(actions.setIsCreating(false));
        dataSources.forEach(({ actions: dsActions }) => {
            dispatch(dsActions.setIsCreating(false));
            dispatch(dsActions.setMode(MODES.READ));
        });

        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        cleanModelCache();
        clearSnapshot(); // Clear snapshot on discard
        dispatch(actions.setPopupStatus({ confirmSave: false }));
    }

    const handleSearchQueryChange = (_, value) => {
        setSearchQuery(value);
    }

    const handleLoad = () => {
        if (!searchQuery || searchQuery.length == 0) return;
        const modifiedObj = cloneDeep(storedObj);
        let mostRecentId;
        searchQuery.forEach((item) => {
            const idx = get(modifiedObj, bufferedFieldMetadata.key).indexOf(item);
            if (idx === -1) {
                console.error(`load failed for idx: ${idx}`);
                return;
            }
            get(modifiedObj, bufferedFieldMetadata.key).splice(idx, 1);
            get(modifiedObj, loadedFieldMetadata.key).push(item);
            mostRecentId = getIdFromAbbreviatedKey(abbreviationKey, item);
        })
        dispatch(actions.setUpdatedObj(modifiedObj));
        dispatch(actions.update({ url: modelDataSource.url, data: modifiedObj }));
        dataSources.forEach(({ actions: dsActions }) => {
            dispatch(dsActions.setObjId(mostRecentId));
        })
        handleSelectedSourceIdChangeHandler(mostRecentId);
        setSearchQuery([]);
    }

    const handleSelectedSourceIdChangeHandler = (updatedSelectedSourceId) => {
        setObjIdToSourceIdDict((prev) => ({ ...prev, [String(objId)]: updatedSelectedSourceId }));
    }

    const handleDownload = async () => {
        const fileName = getCSVFileName(modelName);
        try {
            const csvContent = await downloadCSV(rows);
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
        const { schema, actions: dsActions, fieldsMetadata, name } = dataSources[0];
        sourceRef.current = name;
        const newObj = generateObjectFromSchema(projectSchema, schema);
        set(newObj, DB_ID, NEW_ITEM_ID);
        const dataSourceUpdateObj = addxpath(newObj);
        dispatch(dsActions.setStoredObj({}));
        dispatch(dsActions.setUpdatedObj(dataSourceUpdateObj));
        dispatch(dsActions.setObjId(NEW_ITEM_ID));
        dispatch(dsActions.setMode(MODES.EDIT));
        dispatch(dsActions.setIsCreating(true));
        const newModelAbbreviatedItem = getNewItem(fieldsMetadata, abbreviationKey);
        const clonedUpdatedObj = cloneDeep(updatedObj);
        get(clonedUpdatedObj, loadedFieldMetadata.key).push(newModelAbbreviatedItem);
        dispatch(actions.setUpdatedObj(clonedUpdatedObj));
        handleModeToggle();
        dispatch(actions.setIsCreating(true));
        clearSnapshot(); // Clear conflict detection snapshot
    }

    const handleSave = (modifiedObj, force = false, bypassConflictCheck = false) => {
        if (!sourceRef.current) {
            // If no source name, switch to read mode and clear baseline reference.
            if (mode !== MODES.READ) {
                handleModeToggle();
                clearSnapshot();
            }
            return;
        }
        if (!bypassConflictCheck && checkAndShowConflicts(modifiedObj)) {
            return;
        }

        if (Object.keys(formValidationRef.current).length > 0) {
            dispatch(actions.setPopupStatus({ formValidation: true }));
            return;
        }
        const dataSourceStoredObj = dataSourcesStoredObjDict[sourceRef.current];
        const dataSourceUpdatedObj = modifiedObj || clearxpath(cloneDeep(dataSourcesUpdatedObjDict[sourceRef.current]));
        const fieldsMetadata = dataSourcesMetadataDict[sourceRef.current];
        if (isCreating) {
            delete dataSourceUpdatedObj[DB_ID];
        }
        const baselineForComparison = baselineDictionaryRef.current?.[sourceRef.current] || dataSourcesStoredObjDict[sourceRef.current];

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, dataSourceUpdatedObj, fieldsMetadata, isCreating) || [null, null];
        captionDictRef.current = captionDict;

        if (!activeChanges || Object.keys(activeChanges).length === 0) {
            changesRef.current = {};
            dispatch(actions.setMode(MODES.READ));
            baselineDictionaryRef.current = null;
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
        const dataSource = getDataSourceObj(dataSources, sourceRef.current);
        if (!dataSource) {
            return;
        }
        const { url, actions: dsActions, name } = dataSource;
        if (changeDict[DB_ID]) {
            dispatch(dsActions.partialUpdate({ url, data: changeDict }));
        } else {
            let args = { url };
            const crudOverrideDict = dataSourcesCrudOverrideDictRef.current?.[name];
            if (crudOverrideDict?.CREATE) {
                const { endpoint } = crudOverrideDict.CREATE;
                args = { ...args, endpoint };
            }
            dispatch(dsActions.create({ ...args, data: changeDict }));
            dispatch(dsActions.setMode(MODES.READ));
            dispatch(dsActions.setIsCreating(false));
            dispatch(actions.setIsCreating(false));
        }
        changesRef.current = {};
        // dispatch(actions.setMode(MODES.READ));
        if (mode !== MODES.READ) {
            handleModeToggle();
        }
        dispatch(actions.setPopupStatus({ confirmSave: false }));
        clearSnapshot(); // Clear snapshot after successful save
        sourceRef.current = null;
    }

    // Conflict resolution handlers - defined after all dependencies are available
    const handleDiscardChanges = () => {
        handleDiscard();
        closeConflictPopup();
    }

    const handleOverwriteChanges = () => {
        closeConflictPopup();
        const sourceName = sourceRef.current;
        if (!sourceName) return;

        const baselineForComparison = baselineDictionaryRef.current?.[sourceName] || dataSourcesStoredObjDict[sourceName];
        const modelUpdatedObj = clearxpath(cloneDeep(dataSourcesUpdatedObjDict[sourceName]));

        if (!baselineForComparison || !modelUpdatedObj) {
            console.warn('Cannot compare objects in handleOverwriteChanges: baselineForComparison or modelUpdatedObj is null');
            return;
        }

        const [activeChanges, captionDict] = compareJSONObjects(baselineForComparison, modelUpdatedObj, dataSourcesMetadataDict[sourceName], isCreating) || [null, null];
        captionDictRef.current = captionDict;
        if (!activeChanges || Object.keys(activeChanges).length === 0) {
            changesRef.current = {};
            dispatch(actions.setMode(MODES.READ));
            return;
        }

        handleSave(modelUpdatedObj, false, true);
    }

    const handleUpdate = (updatedObj, source) => {
        const dataSource = getDataSourceObj(dataSources, source);
        if (!dataSource) {
            return;
        }
        dispatch(dataSource.actions.setUpdatedObj(updatedObj));
    }

    const handleUserChange = (xpath, updateDict, validationRes, source) => {
        if (sourceRef.current && sourceRef.current !== source) {
            if (changesRef.current.user && Object.keys(changesRef.current.user).length > 0) {
                alert('error');
                return;
            }
        }
        sourceRef.current = source;
        changesRef.current.user = {
            ...changesRef.current.user,
            ...updateDict
        }
        updateFormValidation(formValidationRef, xpath, validationRes);
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
            const [activeChanges, captionDict] = compareJSONObjects(dataSourceStoredObj, dataSourceUpdatedObj, fieldsMetadata) || [null, null];
            captionDictRef.current = captionDict;
            changesRef.current.active = activeChanges;
            executeSave();
        } else if (dataSourceStoredObj[DB_ID]) {
            handleSave(dataSourceUpdatedObj, force);
        }
    }

    const handleErrorClear = () => {
        dispatch(actions.setError(null));
    }

    const debouncedRowSelect = useRef(
        debounce((id) => {
            dataSources.forEach(({ actions: dsActions }) => {
                dispatch(dsActions.setObjId(id));
            })
            handleSelectedSourceIdChangeHandler(id);
        }, 1000)
    ).current;

    const handleRowSelect = (id) => {
        if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
            return;
        }
        debouncedRowSelect(id);
    }

    const cleanedRows = useMemo(() => {
        if ([LAYOUT_TYPES.CHART, LAYOUT_TYPES.PIVOT_TABLE].includes(layoutType)) {
            return removeRedundantFieldsFromRows(rows);
        }
        return [];
    }, [rows, layoutType])

    const handleMultiSelectChange = useCallback((selectedIds, mostRecentId) => {
        if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
            return;
        }

        // Update chart-specific multiselect state
        if (currentChartName) {
            // Convert IDs to row objects for ChartView
            const selectedRowObjects = (selectedIds || [])
                .map(id => cleanedRows.find(row => row['data-id'] === id || row[DB_ID] === id))
                .filter(Boolean); // Remove any undefined entries

            setChartMultiSelectState(prev => ({
                ...prev,
                [currentChartName]: {
                    selectedRows: selectedRowObjects,
                    lastSelectedRowId: mostRecentId || null
                }
            }));
        }

        // Data binding follows most recent selection
        if (mostRecentId) {
            dataSources.forEach(({ actions: dsActions }) => {
                dispatch(dsActions.setObjId(mostRecentId));
            });
            handleSelectedSourceIdChangeHandler(mostRecentId);
        } else if (!selectedIds || selectedIds.length === 0) {
            // Clear selection if no items selected
            dataSources.forEach(({ actions: dsActions }) => {
                dispatch(dsActions.setObjId(null));
            });
            handleSelectedSourceIdChangeHandler(null);
        }
    }, [dataSources, dataSourcesModeDict, dispatch, currentChartName, cleanedRows])

    /**
     * Handle bulk patch operations for multiple rows across data sources
     */
    const handleBulkPatch = useBulkPatch(MODEL_TYPES.ABBREVIATION_MERGE, {
        diffConfig: {
            dataSourcesStoredArrayDict,
            dataSourcesUpdatedArrayDict,
            cells: sortedCells,
            dataSourcesMetadataDict
        },
        dispatchConfig: {
            urlsBySource: Object.fromEntries(
                dataSources.map(({ name, schema }) => {
                    const childUrlOverrideDep = resolvedChildDependencies[name]?.urlOverride;
                    const urlStoredObj = childUrlOverrideDep?.storedObj || urlOverrideDataSourceStoredObj;
                    const urlFieldsMetadata = childUrlOverrideDep?.fieldsMetadata || urlOverrideDataSource?.fieldsMetadata;
                    return [name, getServerUrl(schema, urlStoredObj, urlFieldsMetadata)];
                })
            ),
            getActionBySource: (source) => {
                const dataSource = dataSources.find(ds => ds.name === source);
                if (!dataSource) {
                    throw new Error(`Data source ${source} not found`);
                }
                return dataSource.actions.partialUpdate;
            }
        }
    });

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
                    modelName: modelName,
                    columns: columns
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
                    fieldsMetadata: modelItemFieldsMetadata,
                    chartData: modelLayoutOption.chart_data || [],
                    modelType: MODEL_TYPES.ABBREVIATION_MERGE,
                    onRowSelect: handleRowSelect,
                    mode: mode,
                    abbreviation: abbreviationKey,
                    onModeToggle: handleModeToggle,
                    onChartSelect: handleSelectedChartNameChange,
                    selectedChartName: modelLayoutData.selected_chart_name ?? null,
                    chartEnableOverride: modelLayoutData.chart_enable_override ?? [],
                    onChartPointSelect: handleMultiSelectChange,
                    selectedRows: multiSelectedRows,
                    lastSelectedRowId: lastSelectedRowId,
                    quickFilters: modelLayoutData.quick_filters ?? [],
                    onQuickFiltersChange: handleQuickFiltersChange,
                    selectedRowId: dataSourcesObjIdDict[dataSources[0].name]
                };
                wrapperMode = MODES.READ;
                isReadOnly = true;
                break;
            default:
                break;
        }

        return (
            <Wrapper {...wrapperProps} >
                <CommonKeyWidget mode={wrapperMode} commonkeys={commonKeys} collapse={modelLayoutData.common_key_collapse} />
                <AbbreviationMergeView
                    bufferedFieldMetadata={bufferedFieldMetadata}
                    loadedFieldMetadata={loadedFieldMetadata}
                    dataSourceStoredArray={dataSourcesStoredArrayDict[dataSources[0].name]}
                    modelAbbreviatedBufferItems={modelAbbreviatedBufferItems}
                    searchQuery={searchQuery}
                    onSearchQueryChange={handleSearchQueryChange}
                    onLoad={handleLoad}
                    mode={wrapperMode}
                    rows={groupedRows}
                    activeRows={activeRows}
                    cells={sortedCells}
                    sortOrders={modelLayoutData.sort_orders || []}
                    onSortOrdersChange={handleSortOrdersChange}
                    dataSourcesStoredArrayDict={effectiveStoredArrayDict}
                    dataSourcesUpdatedArrayDict={dataSourcesUpdatedArrayDict}
                    selectedId={dataSourcesObjIdDict[dataSources[0].name]}
                    onForceSave={() => { }}
                    dataSourceColors={modelLayoutData.data_source_colors || []}
                    page={page}
                    rowsPerPage={modelLayoutData.rows_per_page || 25}
                    totalCount={rows.length} //in AbbreviationMergeModel we dont depend on count query count for total rows
                    onPageChange={handlePageChange}
                    onRowsPerPageChange={handleRowsPerPageChange}
                    onRowSelect={handleRowSelect}
                    onModeToggle={handleModeToggle}
                    onUpdate={handleUpdate}
                    onUserChange={handleUserChange}
                    onButtonToggle={handleButtonToggle}
                    isReadOnly={isReadOnly}
                    onColumnOrdersChange={handleColumnOrdersChange}
                    onBulkPatch={handleBulkPatch}
                    selectedRows={multiSelectedRows}
                    lastSelectedRowId={lastSelectedRowId}
                    onSelectionChange={handleMultiSelectChange}
                    stickyHeader={modelLayoutData.sticky_header ?? true}
                    frozenColumns={modelLayoutData.frozen_columns || []}
                    filters={uiFilters || []}
                    onFiltersChange={handleFiltersChange}
                    uniqueValues={uniqueValues}
                    highlightDuration={modelLayoutData.highlight_duration ?? DEFAULT_HIGHLIGHT_DURATION}
                    baselineDictionary={baselineDictionaryRef.current}
                    dataSourcesModeDict={dataSourcesModeDict}
                    maxRowSize={maxRowSize}
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
                        filters={uiFilters || []}
                        fieldsMetadata={modelItemFieldsMetadata || []}
                        onFiltersChange={handleFiltersChange}
                        uniqueValues={uniqueValues}
                        serverSideFilterSortEnabled={false} //this model does not support this
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
                        viewUrl={httpViewUrl}
                        autoBoundParams={autoBoundParams}
                        // misc
                        enableOverride={modelLayoutData.enable_override || []}
                        disableOverride={modelLayoutData.disable_override || []}
                        showLess={modelLayoutData.show_less || []}
                        modelType={MODEL_TYPES.ABBREVIATION_MERGE}
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
                    isDisabled={isLoading || isCreating || isProcessingUserActions}
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
                title={sourceRef.current}
                open={popupStatus.confirmSave}
                onClose={handleConfirmSavePopupClose}
                onSave={executeSave}
                src={changesRef.current.active}
                captionDict={captionDictRef.current}
            />
            <FormValidation
                title={sourceRef.current || ''}
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

const MemoizedAbbreviationMergeModel = React.memo(AbbreviationMergeModel);
MemoizedAbbreviationMergeModel.displayName = 'AbbreviationMergeModel';
export default MemoizedAbbreviationMergeModel;