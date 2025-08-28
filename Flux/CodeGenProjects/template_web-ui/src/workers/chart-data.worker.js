import { DB_ID } from '../constants';

const GLOBAL_ARCHIVE = new Map();

class ChartDataWorker {
    constructor() {


        // Core data storage - Map provides O(1) lookups
        this.tsDataMap = new Map(); // fingerprint -> data array
        this.metaFieldsCache = new Map(); // fingerprint -> meta fields array
        this.webSocketWorkers = new Map(); // fingerprint -> WebSocket worker reference
        this.streamConfigs = new Map(); // fingerprint -> stream configuration

        // Performance optimization
        this.batchUpdates = new Map(); // fingerprint -> pending updates array
        this.batchTimeout = null;
        this.BATCH_DELAY_MS = 16; // ~60fps update rate

        // Memory management
        this.CLEANUP_INTERVAL = 30000; // 30 seconds
        this.lastCleanup = Date.now();

        // Parent-controlled sliding window configuration
        this.slidingWindowSize = null; // Set by parent via REGISTER_STREAM message

        // Bind methods
        this.handleMessage = this.handleMessage.bind(this);
        this.processBatchedUpdates = this.processBatchedUpdates.bind(this);
    }

    /**
     * Main message handler for all worker communications
     */
    handleMessage(event) {
        const { type, fingerprint, data, config } = event.data;


        try {
            switch (type) {
                case 'REGISTER_STREAM':
                    this.registerStream(fingerprint, config);
                    break;

                case 'UNREGISTER_STREAM':
                    this.unregisterStream(fingerprint);
                    break;

                case 'UPDATE_DATA':
                    this.updateData(fingerprint, data);
                    break;

                case 'GET_AGGREGATED_DATA':
                    this.getAggregatedData();
                    break;

                case 'UPDATE_GLOBAL_SLIDING_WINDOW':
                    this.updateGlobalSlidingWindow(data.windowSize);
                    break;

                case 'CLEAR_ALL_DATA':
                    this.clearAllData();
                    break;

                case 'GET_STREAM_INFO':
                    this.getStreamInfo();
                    break;

                case 'GET_ARCHIVED_DATA':
                    this.getArchivedData(fingerprint);
                    break;

                case 'GET_ALL_ARCHIVED_DATA':
                    this.getAllArchivedData();
                    break;

                default:
                    console.warn('Unknown message type:', type);
            }
        } catch (error) {
            this.postError('MESSAGE_HANDLER_ERROR', error, { type, fingerprint });
        }

        // Periodic cleanup
        this.performPeriodicCleanup();
    }

    /**
     * Register a new time-series stream
     */
    registerStream(fingerprint, config) {

        if (this.tsDataMap.has(fingerprint)) {
            console.warn('⚠️ [ChartDataWorker] Stream already registered:', fingerprint);
            return;
        }

        // Initialize data structures for this stream
        this.tsDataMap.set(fingerprint, []);
        this.metaFieldsCache.set(fingerprint, null);
        this.streamConfigs.set(fingerprint, {
            queryName: config.queryName,
            rootUrl: config.rootUrl,
            metaFilterDict: config.metaFilterDict,
            registeredAt: Date.now()
        });

        // Set sliding window configuration from parent
        if (config.slidingWindowSize !== undefined) {
            this.slidingWindowSize = config.slidingWindowSize;
        }

        this.postMessage({
            type: 'STREAM_REGISTERED',
            fingerprint,
            success: true
        });
    }

    /**
     * Unregister and cleanup a time-series stream
     */
    unregisterStream(fingerprint) {
        // Cleanup all data structures
        this.tsDataMap.delete(fingerprint);
        this.metaFieldsCache.delete(fingerprint);
        this.streamConfigs.delete(fingerprint);
        this.batchUpdates.delete(fingerprint);

        this.postMessage({
            type: 'STREAM_UNREGISTERED',
            fingerprint,
            success: true
        });
    }

    /**
     * Process incremental data updates with intelligent merging
     */
    updateData(fingerprint, newData) {
        if (!Array.isArray(newData) || newData.length === 0) {
            return;
        }

        if (!this.tsDataMap.has(fingerprint)) {
            console.warn('⚠️ [ChartDataWorker] Attempting to update unregistered stream:', fingerprint);
            return;
        }


        // Add to batch processing for performance
        if (!this.batchUpdates.has(fingerprint)) {
            this.batchUpdates.set(fingerprint, []);
        }
        this.batchUpdates.get(fingerprint).push(...newData);

        // Schedule batched processing
        this.scheduleBatchProcessing();
    }

    /**
     * Schedule batched updates to avoid overwhelming the main thread
     */
    scheduleBatchProcessing() {
        if (this.batchTimeout) {
            return; // Already scheduled
        }

        this.batchTimeout = setTimeout(() => {
            this.processBatchedUpdates();
            this.batchTimeout = null;
        }, this.BATCH_DELAY_MS);
    }

    /**
     * Process all batched updates efficiently
     */
    processBatchedUpdates() {
        const updatedFingerprints = [];

        for (const [fingerprint, pendingUpdates] of this.batchUpdates.entries()) {
            if (pendingUpdates.length === 0) continue;

            try {
                const dataBefore = this.tsDataMap.get(fingerprint)?.length || 0;
                this.mergeDataForStream(fingerprint, pendingUpdates);
                const dataAfterMerge = this.tsDataMap.get(fingerprint)?.length || 0;
                updatedFingerprints.push(fingerprint);

                // Apply sliding window if configured
                this.applyStreamConstraints(fingerprint);

            } catch (error) {
                this.postError('BATCH_UPDATE_ERROR', error, { fingerprint });
            }
        }

        // Clear processed batches
        this.batchUpdates.clear();

        // Notify main thread of updates
        if (updatedFingerprints.length > 0) {
            this.sendAggregatedUpdate(updatedFingerprints);
        }
    }

    /**
     * Intelligent data merging with O(1) meta field detection
     */
    mergeDataForStream(fingerprint, newDataArray) {
        const existingData = this.tsDataMap.get(fingerprint);
        let metaFields = this.metaFieldsCache.get(fingerprint);


        // Detect meta fields on first update (cache for performance)
        if (!metaFields && newDataArray.length > 0) {
            metaFields = this.detectMetaFields(newDataArray[0]);
            this.metaFieldsCache.set(fingerprint, metaFields);
        }

        // Fast path: no meta fields, simple append
        if (!metaFields || metaFields.length === 0) {
            existingData.push(...newDataArray);
            return;
        }


        // Optimized merging using Map for O(1) lookups
        const existingDataMap = new Map();
        existingData.forEach((item, index) => {
            const key = this.generateMetaKey(item, metaFields);
            if (!existingDataMap.has(key)) {
                existingDataMap.set(key, []);
            }
            existingDataMap.get(key).push({ item, index });
        });


        // Process new data
        let mergedCount = 0;
        let newCount = 0;

        newDataArray.forEach(newItem => {
            const metaKey = this.generateMetaKey(newItem, metaFields);
            const existing = existingDataMap.get(metaKey);


            if (existing && existing.length > 0) {
                // Merge with existing item (append projection_models)
                const existingItem = existing[0].item;
                this.mergeProjectionModels(existingItem, newItem);
                mergedCount++;
            } else {
                // Add as new item
                existingData.push(newItem);
                newCount++;
            }
        });

    }

    /**
     * Detect meta fields efficiently
     */
    detectMetaFields(dataObject) {
        if (!dataObject || typeof dataObject !== 'object') {
            return [];
        }

        const knownDataFields = ['projection_models', 'seriesIndex', 'DB_ID', 'data-id'];
        return Object.keys(dataObject).filter(field =>
            !knownDataFields.includes(field) &&
            typeof dataObject[field] === 'object' &&
            dataObject[field] !== null
        );
    }

    /**
     * Generate a unique key for meta field combinations
     */
    generateMetaKey(dataObject, metaFields) {
        const keyParts = metaFields.map(field => {
            const value = dataObject[field];
            if (typeof value === 'object' && value !== null) {
                return JSON.stringify(value); // Deterministic object stringification
            }
            return String(value);
        });

        return keyParts.join('|');
    }

    /**
     * Merge projection_models efficiently
     */
    mergeProjectionModels(existingItem, newItem) {

        if (existingItem.projection_models && newItem.projection_models) {
            existingItem.projection_models.push(...newItem.projection_models);
        } else if (newItem.projection_models) {
            existingItem.projection_models = [...newItem.projection_models];
        }

        // Merge other array fields
        Object.keys(newItem).forEach(key => {
            if (Array.isArray(newItem[key]) &&
                key !== 'projection_models' &&
                existingItem[key]) {
                existingItem[key].push(...newItem[key]);
            }
        });

    }

    /**
     * Apply parent-controlled sliding window constraints to a stream
     */
    applyStreamConstraints(fingerprint) {
        // Check if sliding window is disabled (null/undefined from parent)
        if (!this.slidingWindowSize) {
            return;
        }

        const data = this.tsDataMap.get(fingerprint);
        let totalDroppedPoints = 0;


        // Apply sliding window to projection_models within each dataset item
        data.forEach((item, index) => {
            if (!item.projection_models || !Array.isArray(item.projection_models)) {
                return;
            }

            const projectionCount = item.projection_models.length;

            if (projectionCount <= this.slidingWindowSize) {
                return;
            }

            const itemsToRemove = projectionCount - this.slidingWindowSize;

            // Always use keep_latest strategy (simplified)
            const droppedPoints = item.projection_models.slice(0, itemsToRemove);
            item.projection_models.splice(0, itemsToRemove);


            // Archive dropped points
            if (droppedPoints.length > 0) {
                totalDroppedPoints += droppedPoints.length;

                // Initialize archive for this fingerprint if needed
                if (!GLOBAL_ARCHIVE.has(fingerprint)) {
                    GLOBAL_ARCHIVE.set(fingerprint, []);
                }

                // Store dropped points with metadata
                const archivedEntry = {
                    timestamp: Date.now(),
                    datasetIndex: index,
                    droppedPoints: [...droppedPoints], // Deep copy
                    windowSize: this.slidingWindowSize
                };

                GLOBAL_ARCHIVE.get(fingerprint).push(archivedEntry);
            }
        });
    }

    /**
     * Get aggregated data for chart rendering
     * IMPORTANT: Preserve unique keys to maintain separate datasets for different filters
     */
    getAggregatedData() {
        const aggregated = {};

        // Keep fingerprint-based structure to preserve individual filter streams
        for (const [fingerprint, data] of this.tsDataMap.entries()) {
            const config = this.streamConfigs.get(fingerprint);
            if (!config) continue;

            // Create unique key combining query name and fingerprint (like original architecture)
            const uniqueKey = `${config.queryName}__${fingerprint}`;
            aggregated[uniqueKey] = data;
        }

        this.postMessage({
            type: 'AGGREGATED_DATA',
            data: aggregated,
            timestamp: Date.now()
        });
    }

    /**
     * Send incremental updates to main thread
     * IMPORTANT: Preserve unique keys to maintain separate datasets for different filters
     */
    sendAggregatedUpdate(updatedFingerprints) {
        const partialUpdate = {};


        for (const fingerprint of updatedFingerprints) {
            const config = this.streamConfigs.get(fingerprint);
            const data = this.tsDataMap.get(fingerprint);

            if (config && data) {
                // Create unique key combining query name and fingerprint (like original architecture)
                const uniqueKey = `${config.queryName}__${fingerprint}`;
                partialUpdate[uniqueKey] = data;
            }
        }


        this.postMessage({
            type: 'INCREMENTAL_UPDATE',
            data: partialUpdate,
            updatedFingerprints,
            timestamp: Date.now()
        });
    }

    /**
     * Update parent-controlled sliding window size
     * null = disabled (unlimited), number = window size
     */
    updateGlobalSlidingWindow(newSize) {
        const oldSize = this.slidingWindowSize;
        this.slidingWindowSize = newSize;

        console.log(`🌐 [Config] Parent sliding window updated: ${oldSize || 'UNLIMITED'} -> ${newSize || 'UNLIMITED'}`);

        // If disabling sliding window (null), restore archived data
        if (!newSize && oldSize) {
            this.restoreAllArchivedData();
        }

        // If enabling or changing window size, apply to all existing streams
        if (newSize) {
            for (const fingerprint of this.tsDataMap.keys()) {
                this.applyStreamConstraints(fingerprint);
            }
        }

        this.postMessage({
            type: 'GLOBAL_SLIDING_WINDOW_UPDATED',
            oldSize,
            newSize,
            timestamp: Date.now()
        });
    }

    /**
     * Restore archived data back to active memory for all streams
     */
    restoreAllArchivedData() {

        for (const [fingerprint, archivedEntries] of GLOBAL_ARCHIVE.entries()) {
            this.restoreArchivedData(fingerprint);
        }

    }

    /**
     * Restore archived data for a specific stream
     */
    restoreArchivedData(fingerprint) {
        const activeData = this.tsDataMap.get(fingerprint);
        const archivedEntries = GLOBAL_ARCHIVE.get(fingerprint) || [];

        if (archivedEntries.length === 0) {
            return;
        }


        // Collect all archived points in chronological order
        const allArchivedPoints = [];
        archivedEntries.forEach(entry => {
            allArchivedPoints.push(...entry.droppedPoints);
        });


        // Restore archived points to projection_models
        activeData.forEach((dataset, index) => {
            if (dataset.projection_models && Array.isArray(dataset.projection_models)) {
                const beforeCount = dataset.projection_models.length;

                // Prepend archived points to existing projection_models
                dataset.projection_models = [
                    ...allArchivedPoints,
                    ...dataset.projection_models
                ];

                const afterCount = dataset.projection_models.length;
            }
        });

        // Clear archive after successful restoration
        GLOBAL_ARCHIVE.delete(fingerprint);
    }

    /**
     * Get archived data for a specific stream
     */
    getArchivedData(fingerprint) {
        const archivedData = GLOBAL_ARCHIVE.get(fingerprint) || [];

        // Calculate total archived points
        const totalArchivedPoints = archivedData.reduce((total, entry) =>
            total + (entry.droppedPoints?.length || 0), 0
        );


        this.postMessage({
            type: 'ARCHIVED_DATA',
            fingerprint,
            data: archivedData,
            totalEntries: archivedData.length,
            totalPoints: totalArchivedPoints,
            timestamp: Date.now()
        });
    }

    /**
     * Get all archived data across all streams
     */
    getAllArchivedData() {
        const allArchived = {};
        let totalEntries = 0;
        let totalPoints = 0;

        for (const [fingerprint, entries] of GLOBAL_ARCHIVE.entries()) {
            const entryPoints = entries.reduce((total, entry) =>
                total + (entry.droppedPoints?.length || 0), 0
            );

            allArchived[fingerprint] = {
                entries,
                entryCount: entries.length,
                pointCount: entryPoints
            };

            totalEntries += entries.length;
            totalPoints += entryPoints;
        }


        this.postMessage({
            type: 'ALL_ARCHIVED_DATA',
            data: allArchived,
            streamCount: Object.keys(allArchived).length,
            totalEntries,
            totalPoints,
            timestamp: Date.now()
        });
    }

    /**
     * Clear all data
     */
    clearAllData() {
        const beforeStreams = this.tsDataMap.size;
        const beforeArchiveEntries = GLOBAL_ARCHIVE.size;

        this.tsDataMap.clear();
        this.metaFieldsCache.clear();
        this.streamConfigs.clear();
        this.batchUpdates.clear();
        //Intentionally NOT clearing GLOBAL_ARCHIVE to preserve history


        this.postMessage({
            type: 'ALL_DATA_CLEARED',
            timestamp: Date.now()
        });
    }

    /**
     * Get stream information for debugging
     */
    getStreamInfo() {
        const streamInfo = [];

        for (const [fingerprint, config] of this.streamConfigs.entries()) {
            const dataCount = this.tsDataMap.get(fingerprint)?.length || 0;
            const metaFields = this.metaFieldsCache.get(fingerprint) || [];
            const archivedEntries = GLOBAL_ARCHIVE.get(fingerprint) || [];
            const archivedPoints = archivedEntries.reduce((total, entry) =>
                total + (entry.droppedPoints?.length || 0), 0
            );

            streamInfo.push({
                fingerprint,
                queryName: config.queryName,
                dataCount,
                metaFields,
                parentSlidingWindowSize: this.slidingWindowSize,
                archivedEntries: archivedEntries.length,
                archivedPoints,
                registeredAt: config.registeredAt
            });
        }

        this.postMessage({
            type: 'STREAM_INFO',
            data: streamInfo,
            totalStreams: streamInfo.length,
            totalDataPoints: Array.from(this.tsDataMap.values()).reduce((sum, arr) => sum + arr.length, 0)
        });
    }

    /**
     * Periodic cleanup and maintenance
     */
    performPeriodicCleanup() {
        const now = Date.now();
        if (now - this.lastCleanup < this.CLEANUP_INTERVAL) {
            return;
        }

        this.lastCleanup = now;

        // Apply sliding window constraints to all streams
        for (const fingerprint of this.tsDataMap.keys()) {
            this.applyStreamConstraints(fingerprint);
        }

        // Optional: Report memory usage
        this.reportMemoryUsage();
    }

    /**
     * Report memory usage for monitoring
     */
    reportMemoryUsage() {
        const totalDataPoints = Array.from(this.tsDataMap.values())
            .reduce((sum, arr) => sum + arr.length, 0);

        this.postMessage({
            type: 'MEMORY_REPORT',
            totalStreams: this.tsDataMap.size,
            totalDataPoints,
            cacheSize: this.metaFieldsCache.size,
            timestamp: Date.now()
        });
    }

    /**
     * Post error messages to main thread
     */
    postError(errorType, error, context = {}) {
        this.postMessage({
            type: 'ERROR',
            errorType,
            message: error.message,
            stack: error.stack,
            context,
            timestamp: Date.now()
        });
    }

    /**
     * Wrapper for postMessage
     */
    postMessage(data) {
        postMessage(data);
    }
}

// Initialize worker instance
const chartDataWorker = new ChartDataWorker();

// Set up message listener
onmessage = chartDataWorker.handleMessage;

// Export for testing (if needed)
export { ChartDataWorker };