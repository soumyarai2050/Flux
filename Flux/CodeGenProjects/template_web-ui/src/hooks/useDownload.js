import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { getApiUrlMetadata } from '../utils/network/networkUtils';
import { getErrorDetails } from '../utils/core/errorUtils';

// --- Start of new shared logic ---

// 1. Create the worker instance once at the module level. It's now a singleton.
const sharedWorker = new Worker(new URL('../workers/downloader.worker.js', import.meta.url));

// 2. Create a Map to hold the callbacks for each active download request.
const listeners = new Map();
let downloadIdCounter = 0;

// 3. Set up a SINGLE, permanent message handler on the shared worker.
// This handler acts as a router, directing messages to the correct hook instance.
sharedWorker.onmessage = (e) => {
    const { downloadId, ...data } = e.data;
    if (listeners.has(downloadId)) {
        // Find the specific callback for this downloadId and call it.
        const callback = listeners.get(downloadId);
        callback(data);
    }
};

// Also handle top-level errors, though we'll handle specific errors via postMessage.
sharedWorker.onerror = (error) => {
    console.error("A critical error occurred in the shared download worker:", error);
    // You could optionally notify all active listeners of the failure.
    listeners.forEach(callback => callback({ error }));
    listeners.clear();
};

// --- End of new shared logic ---

/**
 * @function useDownload
 * @description A custom React hook for managing CSV file downloads, leveraging a Web Worker for background processing.
 * It handles data fetching (if needed), CSV generation, progress tracking, and error handling.
 * @param {string} modelName - The name of the model associated with the download.
 * @param {Array<object>} fieldsMetadata - Metadata for the fields to be included in the CSV.
 * @param {string|null} xpath - The XPath for the data, if applicable.
 * @param {string|null} [modelType=null] - The type of the model (e.g., MODEL_TYPES.ABBREVIATION_MERGE).
 * @returns {object} An object containing download control functions and status.
 * @property {function(Array<object>, object): Promise<string>} downloadCSV - Function to initiate the CSV download.
 * @property {boolean} isDownloading - True if a download is currently in progress.
 * @property {number} progress - The current download progress as a percentage (0-100).
 */
const useDownload = (modelName, fieldsMetadata, xpath, modelType = null) => {
    const [isDownloading, setIsDownloading] = useState(false);
    const [progress, setProgress] = useState(0);

    // This ref will now store the unique ID of the download initiated by this hook instance.
    const downloadIdRef = useRef(null);

    // This useEffect is now ONLY for cleanup. If the component unmounts
    // mid-download, we must remove its listener to prevent memory leaks.
    useEffect(() => {
        return () => {
            if (downloadIdRef.current) {
                listeners.delete(downloadIdRef.current);
            }
        };
    }, []);

    /**
     * @function downloadCSV
     * @description Initiates the CSV download process. Fetches data if not provided, then sends it to a Web Worker for CSV generation.
     * @param {Array<object>} [storedData=null] - Optional: The data array to convert to CSV. If null, data will be fetched via API.
     * @param {object} [args={}] - Arguments for API call if data needs to be fetched.
     * @param {string} [args.url] - Base URL for the API call.
     * @param {string} [args.endpoint] - Specific API endpoint to use.
     * @param {number} [args.uiLimit] - UI limit for the number of items.
     * @param {object} [args.params] - Query parameters for the API call.
     * @returns {Promise<string>} A promise that resolves with the generated CSV content string.
     */
    const downloadCSV = (storedData = null, args = {}) => {
        return new Promise(async (resolve, reject) => {
            if (isDownloading) {
                console.warn('Download already in progress. Ignoring this request.');
                reject(new Error('Download already in progress.'));
                return;
            }
            setIsDownloading(true);

            let dataToProcess;
            if (!storedData) {
                const defaultEndpoint = `get-all-${modelName}`;
                const { url, endpoint, uiLimit = null, params } = args;
                const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params, true);
                try {
                    const res = await axios.get(apiUrl, { params: apiParams });
                    dataToProcess = res.data;
                } catch (err) {
                    const errorDetails = getErrorDetails(err);
                    console.error('API data fetch failed:', errorDetails);
                    setIsDownloading(false);
                    reject(errorDetails);
                    return;
                }
            } else {
                dataToProcess = storedData;
            }

            let csvResult = "";
            setProgress(0);

            // Generate a new unique ID for this specific download.
            const downloadId = ++downloadIdCounter;
            downloadIdRef.current = downloadId;

            // Define the callback for this specific download.
            const onMessageCallback = ({ csvChunk, currentRow, totalRows, done, error }) => {
                if (error) {
                    setIsDownloading(false);
                    listeners.delete(downloadId);
                    downloadIdRef.current = null;
                    reject(error);
                    return;
                }

                csvResult += csvChunk || '';
                if (totalRows) {
                    setProgress(Math.round((currentRow / totalRows) * 100));
                }

                if (done) {
                    setIsDownloading(false);
                    listeners.delete(downloadId);
                    downloadIdRef.current = null;
                    resolve(csvResult);
                }
            };

            // Register the callback in our shared map.
            listeners.set(downloadId, onMessageCallback);

            sharedWorker.postMessage({ fieldsMetadata, data: dataToProcess, xpath, modelType, downloadId });
        });
    };

    return { downloadCSV, isDownloading, progress };
};

export default useDownload;