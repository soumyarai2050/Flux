import { useCallback, useEffect, useRef, useState } from 'react';
import { MODEL_TYPES, API_ROOT_URL, MODES } from '../constants';
import { genMetaFilters} from '../utils/core/chartUtils';
import { getCollectionByName } from '../utils/core/dataUtils';
import { getModelSchema } from '../utils/core/schemaUtils';
import { getChartFilterDict} from '../utils/core/dataFiltering';

/**
 * Custom React hook for managing time-series data through WebSocket connections and Web Workers.
 *
 * This hook extracts all time-series data handling logic from chart components,
 * providing a reusable interface for real-time data streaming, aggregation, and state management.
 *
 * Features:
 * - Manages WebSocket connections through dedicated workers
 * - Handles data aggregation and sliding window configurations
 * - Provides automatic stream registration/unregistration
 * - Supports external service mapping and query configurations
 *
 * @param {Object} params - Configuration object for the hook
 * @param {Object} params.chartConfig - The chart configuration object (storedChartObj)
 * @param {Array} params.chartRows - Static data array for generating meta-filters (rows)
 * @param {Object} params.fieldsMetadata - Metadata for all data fields
 * @param {Object} params.projectSchema - The overall project schema
 * @param {Object} params.schemaCollections - Collections from the project schema
 * @param {string} params.modelType - Model type (e.g., MODEL_TYPES.ABBREVIATION_MERGE)
 * @param {boolean} [params.isEnabled=true] - Flag to enable/disable hook operations
 * @param {string} [params.mode=MODES.READ] - Current component mode
 * @param {number|null} [params.slidingWindowSize=null] - Sliding window size for memory management
 *
 * @returns {Object} Hook return value
 * @returns {Object} returns.tsData - Aggregated time-series data from workers
 * @returns {Object} returns.queryDict - Dictionary mapping series indices to query details
 */
const useTimeSeriesData = ({
    chartConfig,
    chartRows,
    fieldsMetadata,
    projectSchema,
    schemaCollections,
    modelType,
    isEnabled = true,
    mode = MODES.READ,
    slidingWindowSize = null
}) => {
    // Time-series specific state
    const [tsData, setTsData] = useState({});
    const [queryDict, setQueryDict] = useState({});

    // Update counter for controlling cascading effects
    const [chartUpdateCounter, setChartUpdateCounter] = useState(0);

    // Worker management refs
    const chartDataWorkerRef = useRef(null);
    const webSocketWorkersRef = useRef(new Map()); // fingerprint -> WebSocket worker
    const registeredStreamsRef = useRef(new Set()); // Track registered streams

    /**
     * Initialize the specialized chart data worker
     * This worker handles all time-series data processing and state management
     */
    const initializeChartDataWorker = useCallback(() => {
        if (chartDataWorkerRef.current) {
            return chartDataWorkerRef.current;
        }

        const worker = new Worker(new URL('../workers/chart-data.worker.js', import.meta.url), { type: 'module' });

        // Handle messages from the specialized worker
        worker.onmessage = (event) => {
            const { type, data } = event.data;

            switch (type) {
                case 'AGGREGATED_DATA':
                    // Full replacement for aggregated data
                    if (mode === MODES.READ && data) {
                        setTsData(prevData => {
                            return data;
                        });
                    }
                    break;

                case 'INCREMENTAL_UPDATE':
                    // Merge incremental updates with existing data
                    if (mode === MODES.READ && data) {
                        setTsData(prevData => {
                            // Merge new data with existing data
                            const mergedData = { ...prevData, ...data };
                            return mergedData;
                        });
                    }
                    break;

                case 'STREAM_REGISTERED':
                    break;
                case 'STREAM_UNREGISTERED':
                    break;

                case 'ERROR':
                    break;

                case 'MEMORY_REPORT':
                    break;

                default:
                //for debugging point of view
            }
        };

        worker.onerror = (error) => {
            console.error('Chart Data Worker Error:', error);
        };

        chartDataWorkerRef.current = worker;
        return worker;
    }, [mode]);

    /**
     * Creates a stable fingerprint for a WebSocket connection
     */
    const createQueryFingerprint = useCallback((query, metaFilterDict, rootUrl) => {
        if (!query) return null;

        // Build parameter string from meta filters
        let paramStr = '';
        for (const key in metaFilterDict) {
            if (paramStr) {
                paramStr += `&${key}=${metaFilterDict[key]}`;
            } else {
                paramStr = `${key}=${metaFilterDict[key]}`;
            }
        }

        // Create unique fingerprint: URL + query + parameters
        return `${rootUrl}/ws-query-${query.name}?${paramStr}`;
    }, []);

    /**
     * Extracts worker information for a chart series, handling:
     * - Collection mapping validation
     * - Root URL determination (can be external service)
     * - Query extraction from queryDict
     *
     * Returns null if series doesn't support time-series data
     */
    const getSeriesWorkerInfo = useCallback((series, index) => {
        const collection = getCollectionByName(
            fieldsMetadata,
            series.encode.y,
            modelType === MODEL_TYPES.ABBREVIATION_MERGE
        );

        // Only process series that have time-series mapping
        if (!collection.hasOwnProperty('mapping_src')) {
            return null;
        }

        // Determine root URL - may be external service based on mapping model
        let rootUrl = API_ROOT_URL;
        const mappingModelName = collection.mapping_src?.split('.')[0];
        if (mappingModelName) {
            const mappingModelSchema = getModelSchema(mappingModelName, projectSchema);
            if (mappingModelSchema?.connection_details) {
                const { host, port, project_name } = mappingModelSchema.connection_details;
                rootUrl = `http://${host}:${port}/${project_name}`;
            }
        }

        const query = queryDict[index];
        if (!query) {
            return null;
        }

        return { collection, rootUrl, query };
    }, [fieldsMetadata, modelType, projectSchema, queryDict]);

    /**
     * Create a WebSocket worker for a specific stream
     * This connects to the WebSocket and forwards data to the specialized chart data worker
     */
    const createWebSocketWorker = useCallback((fingerprint, query) => {
        // Create WebSocket connection
        const wsUrl = fingerprint.replace('http', 'ws');
        const socket = new WebSocket(wsUrl);

        // Create WebSocket processing worker
        const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url), { type: 'module' });

        // Forward WebSocket messages to processing worker
        socket.onmessage = (event) => {
            worker.postMessage({
                messages: [event.data],
                storedArray: [],
                isAlertModel: false
            });
        };

        // Forward processed data to specialized chart data worker
        worker.onmessage = (event) => {
            const processedData = event.data;

            if (chartDataWorkerRef.current && Array.isArray(processedData) && processedData.length > 0) {
                chartDataWorkerRef.current.postMessage({
                    type: 'UPDATE_DATA',
                    fingerprint,
                    data: processedData
                });
            }
        };

        socket.onerror = (error) => {
            console.error(`❌ [useTimeSeriesData] WebSocket error for ${fingerprint}:`, error);
        };

        worker.onerror = (error) => {
            console.error(`❌ [useTimeSeriesData] WebSocket worker error for ${fingerprint}:`, error);
        };

        return { socket, worker };
    }, []);

    /**
     * Generates all required stream configurations for current chart configuration
     */
    const generateStreamConfigurations = useCallback((metaFilters) => {
        const configurations = new Map();

        chartConfig.series?.forEach((series, index) => {
            const workerInfo = getSeriesWorkerInfo(series, index);
            if (!workerInfo) return;

            const { query, rootUrl } = workerInfo;

            // Each meta filter creates a separate stream configuration
            metaFilters.forEach(metaFilterDict => {
                const fingerprint = createQueryFingerprint(query, metaFilterDict, rootUrl);
                if (fingerprint) {
                    configurations.set(fingerprint, {
                        index,
                        query,
                        rootUrl,
                        metaFilterDict,
                        queryName: query.name
                    });
                }
            });
        });

        return configurations;
    }, [chartConfig.series, getSeriesWorkerInfo, createQueryFingerprint]);

    /**
     * Register a new stream with the specialized chart data worker
     */
    const registerStream = useCallback((fingerprint, config) => {
        const chartWorker = initializeChartDataWorker();

        chartWorker.postMessage({
            type: 'REGISTER_STREAM',
            fingerprint,
            config: {
                queryName: config.queryName,
                rootUrl: config.rootUrl,
                metaFilterDict: config.metaFilterDict,
                slidingWindowSize: slidingWindowSize
            }
        });

        registeredStreamsRef.current.add(fingerprint);
    }, [initializeChartDataWorker, slidingWindowSize]);

    /**
     * Unregister a stream from the specialized chart data worker
     */
    const unregisterStream = useCallback((fingerprint) => {
        if (chartDataWorkerRef.current) {
            chartDataWorkerRef.current.postMessage({
                type: 'UNREGISTER_STREAM',
                fingerprint
            });
        }

        registeredStreamsRef.current.delete(fingerprint);

        // Cleanup WebSocket worker
        const wsWorker = webSocketWorkersRef.current.get(fingerprint);
        if (wsWorker) {
            const { socket, worker } = wsWorker;
            if (socket) socket.close();
            if (worker) worker.terminate();
            webSocketWorkersRef.current.delete(fingerprint);
        }
    }, []);

    /**
     * Effect to calculate and update queryDict based on chart configuration
     */
    useEffect(() => {
        if (chartConfig.series) {
            let updatedQueryDict = {};
            chartConfig.series.forEach((series, index) => {
                if (series.encode && series.encode.y) {
                    const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
                    if (chartConfig.time_series && collection && collection.hasOwnProperty('mapping_src')) {
                        const [seriesWidgetName, ...mappingSrcField] = collection.mapping_src.split('.');
                        const srcField = mappingSrcField.join('.');
                        const seriesCollections = schemaCollections[seriesWidgetName];
                        if (seriesCollections) {
                            const mappedCollection = seriesCollections.find(col => col.tableTitle === srcField);
                            // fetch query details for time series
                            let name;
                            let params = [];
                            if (mappedCollection && mappedCollection.projections) {
                                mappedCollection.projections.forEach(projection => {
                                    // if query is found, dont proceed
                                    if (name) return;
                                    const [fieldName, queryName] = projection.split(':');
                                    if (fieldName === srcField) {
                                        name = queryName;
                                    }
                                });
                            }
                            seriesCollections.forEach(col => {
                                if (col.val_meta_field && col.required && !['OBJECT', 'ARRAY'].includes(col.type)) {
                                    params.push(col.tableTitle);
                                }
                            })
                            updatedQueryDict[index] = { name, params };
                        }
                    }
                }
            })
            setQueryDict(updatedQueryDict);
        }
        setChartUpdateCounter((prevCount) => prevCount + 1);
    }, [chartConfig, fieldsMetadata, modelType, schemaCollections]);

    /**
     * Main effect for managing the specialized chart data worker and streams.
     * This replaces the old multiple-worker system with a single, efficient worker.
     */
    useEffect(() => {
        // Early exit if hook is disabled
        if (!isEnabled) {
            // Cleanup all WebSocket workers
            webSocketWorkersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            webSocketWorkersRef.current.clear();
            registeredStreamsRef.current.clear();

            // Clear all data in specialized worker
            if (chartDataWorkerRef.current) {
                chartDataWorkerRef.current.postMessage({ type: 'CLEAR_ALL_DATA' });
            }

            setTsData({});
            return;
        }

        // Early exit: cleanup everything if not time-series chart
        if (!chartConfig.series || !chartConfig.time_series) {
            // Cleanup all WebSocket workers
            webSocketWorkersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            webSocketWorkersRef.current.clear();
            registeredStreamsRef.current.clear();

            // Clear all data in specialized worker
            if (chartDataWorkerRef.current) {
                chartDataWorkerRef.current.postMessage({ type: 'CLEAR_ALL_DATA' });
            }

            setTsData({});
            return;
        }

        // Early exit: wait for queryDict to be populated for all time-series
        const expectedQueryCount = chartConfig.series.filter(series => {
            if (!series.encode?.y) return false;
            const collection = getCollectionByName(fieldsMetadata, series.encode.y, modelType === MODEL_TYPES.ABBREVIATION_MERGE);
            return collection && collection.hasOwnProperty('mapping_src');
        }).length;

        const currentQueryCount = Object.keys(queryDict).length;

        if (currentQueryCount < expectedQueryCount) {
            return;
        }

        // Get chart filters and generate meta filters
        const filterDict = getChartFilterDict(chartConfig.filters);
        if (Object.keys(filterDict).length === 0) return;

        // Generate meta filters for all filter fields
        let metaFilters = [];
        Object.keys(filterDict).forEach(filterFld => {
            const filtersForField = genMetaFilters(
                chartRows,
                fieldsMetadata,
                filterDict,
                filterFld,
                modelType === MODEL_TYPES.ABBREVIATION_MERGE
            );
            metaFilters = metaFilters.concat(filtersForField);
        });

        // Generate stream configurations
        const streamConfigurations = generateStreamConfigurations(metaFilters);

        // Initialize the specialized worker
        initializeChartDataWorker();

        // Determine which streams need to be added/removed
        const currentStreams = new Set(registeredStreamsRef.current);
        const newStreams = new Set(streamConfigurations.keys());

        const streamsChanged = currentStreams.size !== newStreams.size ||
            Array.from(newStreams).some(fp => !currentStreams.has(fp));

        // Early exit: no changes needed
        if (!streamsChanged) {
            return;
        }

        // Identify streams being removed and added
        const removedStreams = Array.from(currentStreams).filter(fp => !newStreams.has(fp));
        const addedStreams = Array.from(newStreams).filter(fp => !currentStreams.has(fp));

        // Unregister removed streams
        removedStreams.forEach(fingerprint => {
            unregisterStream(fingerprint);
        });

        // Register and create WebSocket workers for new streams
        addedStreams.forEach(fingerprint => {
            const config = streamConfigurations.get(fingerprint);
            if (config) {
                // Register stream with specialized worker
                registerStream(fingerprint, config);

                // Create WebSocket worker for this stream
                const wsWorker = createWebSocketWorker(fingerprint, config.query);
                webSocketWorkersRef.current.set(fingerprint, wsWorker);
            }
        });

    }, [
        isEnabled,
        chartConfig.series,
        chartConfig.time_series,
        chartConfig.filters,
        queryDict,
        projectSchema,
        fieldsMetadata,
        modelType,
        chartRows,
        mode,
        generateStreamConfigurations,
        initializeChartDataWorker,
        registerStream,
        unregisterStream,
        createWebSocketWorker
    ]);

    // Component unmount cleanup - ensure all workers are properly terminated
    useEffect(() => {
        return () => {
            // Cleanup all WebSocket workers
            webSocketWorkersRef.current.forEach(({ socket, worker }) => {
                if (socket) socket.close();
                if (worker) worker.terminate();
            });
            webSocketWorkersRef.current.clear();

            // Cleanup specialized chart data worker
            if (chartDataWorkerRef.current) {
                chartDataWorkerRef.current.terminate();
                chartDataWorkerRef.current = null;
            }

            registeredStreamsRef.current.clear();
        };
    }, []);

    return {
        tsData,
        queryDict
    };
};

export default useTimeSeriesData;