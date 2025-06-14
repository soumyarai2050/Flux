import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { getApiUrlMetadata } from '../utils';

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


const useDownload = (modelName, fieldsMetadata, xpath, modelType = null) => {
    // The hook's state remains the same.
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

    const downloadCSV = (storedData = null, args = {}) => {
        return new Promise(async (resolve, reject) => {
            if (isDownloading) {
                console.warn('Download already in progress. ignoring this request');
                reject(new Error('Download already in progress.'));
                return;
            }
            setIsDownloading(true);

            let data;
            // Fetch data if not provided.
            if (!storedData) {
                const defaultEndpoint = `get-all-${modelName}`;
                const { url, endpoint, uiLimit = null, params } = args;
                const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
                try {
                    const res = await axios.get(apiUrl, { params: apiParams });
                    data = res.data;
                } catch (error) {
                    console.error(error);
                    setIsDownloading(false);
                    reject(error);
                    return;
                }
            } else {
                data = storedData;
            }

            let csvResult = "";
            setProgress(0);

            // Generate a new unique ID for this specific download.
            const downloadId = ++downloadIdCounter;
            downloadIdRef.current = downloadId; // Store it for potential cleanup.

            // Define the callback for this specific download.
            const onMessageCallback = ({ csvChunk, currentRow, totalRows, done, error }) => {
                if (error) {
                    setIsDownloading(false);
                    listeners.delete(downloadId); // Clean up listener
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
                    listeners.delete(downloadId); // Clean up listener
                    downloadIdRef.current = null;
                    resolve(csvResult);
                }
            };

            // Register the callback in our shared map.
            listeners.set(downloadId, onMessageCallback);

            // Send the data to the worker, now including the unique downloadId.
            sharedWorker.postMessage({ fieldsMetadata, data, xpath, modelType, downloadId });
        });
    };

    return { downloadCSV, isDownloading, progress };
};

export default useDownload;