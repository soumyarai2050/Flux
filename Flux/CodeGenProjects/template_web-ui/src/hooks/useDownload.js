import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { getApiUrlMetadata } from '../utils';

const useDownload = (modelName, fieldsMetadata, xpath, modelType = null) => {
    const workerRef = useRef(null);
    const [isDownloading, setIsDownloading] = useState(false);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        // Create and store the worker instance.
        workerRef.current = new Worker(new URL('../workers/downloader.worker.js', import.meta.url));
        return () => {
            workerRef.current.terminate();
        };
    }, []);

    const downloadCSV = (storedData = null, args = {}) => {
        return new Promise(async (resolve, reject) => {
            if (isDownloading) {
                console.warn('Download already is progress. ignoring this request');
                reject();
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
                    data = [];
                }
            } else {
                data = storedData;
            }

            let csvResult = "";
            setProgress(0);

            // Send the entire dataset to the worker.
            workerRef.current.postMessage({ fieldsMetadata, data, xpath, modelType });

            // Accumulate CSV chunks as they arrive.
            workerRef.current.onmessage = (e) => {
                const { csvChunk, currentRow, totalRows, done } = e.data;
                csvResult += csvChunk;
                if (totalRows) {
                    setProgress(Math.round((currentRow / totalRows) * 100));
                }
                if (done) {
                    workerRef.current.onmessage = null;
                    setIsDownloading(false);
                    resolve(csvResult);
                }
            };

            workerRef.current.onerror = (error) => {
                setIsDownloading(false);
                reject(error);
            };
        });
    };

    return { downloadCSV, isDownloading, progress };
};

export default useDownload;