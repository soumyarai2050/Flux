import { cloneDeep } from 'lodash';
import { DB_ID, SEVERITY_TYPES } from '../../constants';
import { AlertCache } from '../../cache/alertCache';

/**
 * Applies a WebSocket update to a stored array of data. This function handles create, update, and delete operations.
 * It also manages a UI limit on the array size and has special handling for alert models.
 * @param {Array<Object>} storedArray - The current array of data.
 * @param {Object} updatedObj - The updated object received from the WebSocket.
 * @param {number} uiLimit - The maximum number of items to keep in the array.
 * @param {boolean} [isAlertModel=false] - Flag to indicate if the model is an alert model.
 * @returns {Array<Object>} The updated array.
 */
export function applyGetAllWebsocketUpdate(storedArray, updatedObj, uiLimit, isAlertModel = false) {
    // Filter out the object with the same DB_ID as the updatedObj. This handles deletion and prepares for update/creation.
    const updatedArray = storedArray.filter(obj => obj[DB_ID] !== updatedObj[DB_ID]);

    // If the updatedObj has more than just the DB_ID (i.e., it's not just a delete signal).
    if (Object.keys(updatedObj).length !== 1) {
        const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);

        // If an object with the same DB_ID already exists in the storedArray (update case).
        if (idx !== -1) {
            // If it's an alert model and the alert is dismissed, return the filtered array (effectively deleting it).
            if (isAlertModel && updatedObj.dismiss) {
                return updatedArray;
            } else {  // Either not an alert model or alert not dismissed, so update the existing object.
                updatedArray.splice(idx, 0, updatedObj);
            }
        } else { // New object is created.
            if (uiLimit) {
                // If uiLimit is positive, remove the oldest object (from the beginning) and add the new object at the end.
                if (uiLimit >= 0) {
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.shift();
                    }
                    updatedArray.push(updatedObj);
                } else {  // If uiLimit is negative, remove the oldest object (from the end) and add the new object at the beginning.
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        // Special handling for alert models with negative uiLimit for sorting.
                        if (isAlertModel) {
                            // If the new alert's severity is higher than the last one, replace the last one.
                            if (SEVERITY_TYPES[updatedObj.severity] > SEVERITY_TYPES[updatedArray[updatedArray.length - 1].severity]) {
                                updatedArray.pop();
                                updatedArray.push(updatedObj);
                            }
                            // Sort the alert array after modification.
                            sortAlertArray(updatedArray);
                            return updatedArray;
                        } else {
                            updatedArray.pop();
                        }
                    }
                    updatedArray.splice(0, 0, updatedObj);
                    return updatedArray;
                }
            } else {
                // If no uiLimit, just add the new object to the end.
                updatedArray.push(updatedObj);
            }
        }
    }
    // If the updatedObj only contains DB_ID, it means the object was deleted, which is already handled by the initial filter.
    return updatedArray;
}

/**
 * Applies a WebSocket update to a stored array. This is a general-purpose function for handling WebSocket data updates.
 * It handles creation, update, and deletion of objects based on their `DB_ID`.
 * @param {Array<Object>} storedArray - The current array of data.
 * @param {Object} updatedObj - The updated object from the WebSocket.
 * @param {number} uiLimit - The maximum size of the array. If positive, acts as a maximum length; if negative, acts as a minimum length.
 * @param {boolean} [isAlertModel=false] - Whether the data is for an alert model. (Note: Specific alert model logic is handled in `applyWebSocketUpdateForAlertModel`).
 * @returns {Array<Object>} The new, updated array.
 */
export function applyWebSocketUpdate(storedArray, updatedObj, uiLimit, isAlertModel = false) {
    // Filter out the object with the same DB_ID as the updatedObj. This handles deletion and prepares for update/creation.
    const updatedArray = storedArray.filter(obj => obj[DB_ID] !== updatedObj[DB_ID]);

    // If the updatedObj has more than just the DB_ID (i.e., it's not just a delete signal).
    if (Object.keys(updatedObj).length !== 1) {
        const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);

        // If an object with the same DB_ID already exists in the storedArray (update case).
        if (idx !== -1) {
            // If it's an alert model and the alert is dismissed, return the filtered array (effectively deleting it).
            if (isAlertModel && updatedObj.dismiss) {
                return updatedArray;
            } else {  // Either not an alert model or alert not dismissed, so update the existing object.
                updatedArray.splice(idx, 0, updatedObj);
            }
        } else { // New object is created.
            if (uiLimit) {
                // If uiLimit is positive, remove the oldest object (from the beginning) and add the new object at the end.
                if (uiLimit >= 0) {
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.shift();
                    }
                    updatedArray.push(updatedObj);
                } else {  // If uiLimit is negative, remove the oldest object (from the end) and add the new object at the beginning.
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.pop();
                    }
                    updatedArray.splice(0, 0, updatedObj);
                }
            } else {
                // If no uiLimit, just add the new object to the end.
                updatedArray.push(updatedObj);
            }
        }
    }
    // If the updatedObj only contains DB_ID, it means the object was deleted, which is already handled by the initial filter.
    return updatedArray;
}

/**
 * Applies a WebSocket update specifically for alert models, managing the AlertCache.
 * This function handles creation, update, and deletion of alert objects, and updates
 * the `AlertCache` based on severity and dismissal status.
 * @param {Array<Object>} storedArray - The current array of alerts.
 * @param {Object} updatedObj - The updated alert object.
 * @param {number} uiLimit - The maximum number of alerts to store. Positive for max size, negative for min size.
 * @param {string} modelName - The name of the model associated with the alerts.
 * @param {string|null} [id=null] - The ID of the specific alert. Used for cache updates.
 * @returns {Array<Object>} The updated array of alerts.
 */
export function applyWebSocketUpdateForAlertModel(storedArray, updatedObj, uiLimit, modelName, id = null) {
    const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);
    const updatedArray = cloneDeep(storedArray);

    // If the updatedObj has more than just the DB_ID (i.e., it's a create or update operation).
    if (Object.keys(updatedObj).length !== 1) {
        // If an object with the same DB_ID already exists (update case).
        if (idx !== -1) {
            const storedObj = storedArray[idx];
            // Remove the old object from the array.
            updatedArray.splice(idx, 1);
            // Decrement severity count in cache for the old object.
            AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);

            // If the existing alert is dismissed/cleared, return the array without the old object.
            if (updatedObj.dismiss) {
                return updatedArray;
            } else {
                // If the alert is updated (not dismissed), re-insert it at the correct severity-based index.
                const newIdx = AlertCache.getSeverityIndex(modelName, id, updatedObj.severity);
                updatedArray.splice(newIdx, 0, updatedObj);
                // Increment severity count in cache for the updated object.
                AlertCache.updateSeverityCache(modelName, id, updatedObj.severity, 1);
                return updatedArray;
            }
        } else {  // New object is created.
            // Apply UI limit logic.
            if (uiLimit) {
                // Positive array size limit: remove oldest if limit exceeded.
                if (uiLimit >= 0) {
                    if (updatedArray.length >= uiLimit) {
                        const storedObj = updatedArray[0];
                        updatedArray.shift();
                        AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
                    }
                } else {  // Negative array size limit: remove lowest severity if limit exceeded.
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        const storedObj = updatedArray[updatedArray.length - 1];
                        updatedArray.pop();
                        AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
                    }
                }
            }
            // Insert the new object at the correct severity-based index.
            const newIdx = AlertCache.getSeverityIndex(modelName, id, updatedObj.severity);
            updatedArray.splice(newIdx, 0, updatedObj);
            // Increment severity count in cache for the new object.
            AlertCache.updateSeverityCache(modelName, id, updatedObj.severity, 1);
            return updatedArray;
        }
    } else {
        // If the updatedObj only contains DB_ID, it means the object was deleted.
        if (idx !== -1) {
            const storedObj = storedArray[idx];
            // Remove the deleted object from the array.
            updatedArray.splice(idx, 1);
            // Decrement severity count in cache for the deleted object.
            AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
        } else {
            console.error('applyWebSocketUpdateForAlertModel failed. received delete update for id: ' + updatedObj[DB_ID] + ', but id not found in storedArray');
        }
    }
    return updatedArray;
}

/**
 * Sorts an array of alerts based on severity (highest first), then last update time (newest first),
 * and finally alert count (highest first).
 * @param {Array<Object>} alertArray - The array of alerts to sort.
 * @returns {Array<Object>} The sorted array of alerts.
 */
export function sortAlertArray(alertArray) {
    alertArray.sort((a, b) => {
        const severityA = SEVERITY_TYPES[a.severity];
        const severityB = SEVERITY_TYPES[b.severity];

        // Sort by severity (descending).
        if (severityA > severityB) {
            return -1;
        } else if (severityB > severityA) {
            return 1;
        } else {  // Same severity, sort by last update time.
            if (a.last_update_analyzer_time > b.last_update_analyzer_time) {
                return -1;
            } else if (b.last_update_analyzer_time > a.last_update_analyzer_time) {
                return 1;
            } else {  // Same last update time, sort by alert count.
                if (a.alert_count >= b.alert_count) {
                    return -1;
                }
                return 1;
            }
        }
    });
    return alertArray;

    // The commented-out section below represents a previous attempt at stable sorting,
    // which was reverted due to stability issues or other considerations.
    // reverted as not stable
    // const stabilized = alertArray.map((el, index) => [el, index]);
    // stabilized.sort((a, b) => {
    //     const alertA = a[0];
    //     const alertB = b[0];
    //     const severityA = SEVERITY_TYPES[alertA.severity];
    //     const severityB = SEVERITY_TYPES[alertB.severity];
    //     if (severityA > severityB) return -1;
    //     if (severityB > severityA) return 1;
    //     // same severity
    //     if (alertA.last_update_analyzer_time > alertB.last_update_analyzer_time) return -1;
    //     if (alertB.last_update_analyzer_time > alertA.last_update_analyzer_time) return 1;
    //     // same timestamp
    //     if (alertA.alert_count > alertB.alert_count) return -1;
    //     if (alertB.alert_count > alertA.alert_count) return 1;
    //     // fallback to original index for stability
    //     return a[1] - b[1];
    // });
    // return stabilized.map(pair => pair[0]);
}

/**
 * Checks if a WebSocket connection is currently active (either open or connecting).
 * @param {WebSocket} webSocket - The WebSocket instance to check.
 * @returns {boolean} True if the WebSocket is alive (readyState is OPEN or CONNECTING), false otherwise.
 */
export function isWebSocketAlive(webSocket) {
    if (webSocket) {
        // Check if the readyState is OPEN (1) or CONNECTING (0).
        if (webSocket.readyState === WebSocket.OPEN || webSocket.readyState === WebSocket.CONNECTING) {
            return true;
        }
    }
    return false;
}
