import { DB_ID } from '../constants';
import { sortAlertArray } from '../utils/network/websocketUtils';

onmessage = (event) => {
    const { messages, snapshot, storedArray, uiLimit, isAlertModel, activeItemIdMap = null } = event.data;
    
    // If snapshot is provided, process it as full replacement
    if (snapshot) {
        try {
            const snapshotData = JSON.parse(snapshot);
            // Send snapshot data as the new full array
            postMessage(Array.isArray(snapshotData) ? snapshotData : [snapshotData]);
            return;
        } catch (e) {
            console.error('Error parsing snapshot:', e);
            postMessage(storedArray); // Fallback to stored array
            return;
        }
    }

    const updatesMap = new Map();

    // Build update map from the messages
    messages.forEach((msg) => {
        try {
            const updatedArrayOrObj = JSON.parse(msg);
            if (Array.isArray(updatedArrayOrObj)) {
                updatedArrayOrObj.forEach((o) => {
                    const id = o[DB_ID];
                    if (!activeItemIdMap || activeItemIdMap.get(id)) {
                        if ((isAlertModel && o.dismiss) || Object.keys(o).length === 1) {
                            updatesMap.set(id, null);
                        } else {
                            updatesMap.set(id, o);
                        }
                    }
                })
            } else {
                const id = updatedArrayOrObj[DB_ID];
                if (!activeItemIdMap || activeItemIdMap.get(id)) {
                    if ((isAlertModel && updatedArrayOrObj.dismiss) || Object.keys(updatedArrayOrObj).length === 1) {
                        updatesMap.set(id, null);
                    } else {
                        updatesMap.set(id, updatedArrayOrObj);
                    }
                }
            }
        } catch (e) {
            console.error('Error parsing message:', e);
        }
    });

    // Merge updates with the existing stored array.
    // For each existing item, apply the update if available (or remove if deletion).
    const mergedArray = [];
    for (const item of storedArray) {
        if (updatesMap.has(item[DB_ID])) {
            const update = updatesMap.get(item[DB_ID]);
            if (update !== null) {
                mergedArray.push(update);
            }
            updatesMap.delete(item[DB_ID]);
        } else {
            mergedArray.push(item);
        }
    }

    // Collect new updates that weren't in the stored array.
    const newUpdates = [];
    for (const [_, update] of updatesMap.entries()) {
        if (update !== null) {
            newUpdates.push(update);
        }
    }

    // Merge new updates based on uiLimit.
    // If uiLimit is negative, batch prepend new updates; otherwise, append them.
    let finalArray;
    if (uiLimit !== null && uiLimit < 0) {
        // Prepend new updates in one operation to avoid multiple unshift calls.
        finalArray = newUpdates.concat(mergedArray);
    } else {
        finalArray = mergedArray.concat(newUpdates);
    }

    // If a UI limit is set, trim the final array to the limit.
    if (uiLimit !== null) {
        const limit = Math.abs(uiLimit);
        if (finalArray.length > limit) {
            finalArray = uiLimit >= 0
                ? finalArray.slice(finalArray.length - limit) // For positive uiLimit, keep latest items.
                : finalArray.slice(0, limit);                  // For negative uiLimit, keep from the start.
        }
    }

    // For negative uiLimit in alert mode, apply additional sorting if required.
    if (uiLimit !== null && uiLimit < 0 && isAlertModel) {
        sortAlertArray(finalArray);
    }

    postMessage(finalArray);
};

export { };
