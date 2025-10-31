import { DB_ID } from '../constants';
import { getAlertSortComparator } from '../utils/network/websocketUtils';
import { stableSort } from '../utils/core/dataSorting';
import { SortComparator } from '../utils/core/sortUtils';

onmessage = (event) => {
    const { messages, snapshot, storedArray, uiLimit, isAlertModel, activeItemIdMap = null, sortOrders = null } = event.data;

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
    let newTopMarker = null;
    let newBottomMarker = null;

    // Build update map from the messages
    messages.forEach((msg) => {
        try {
            const updatedArrayOrObj = JSON.parse(msg);
            if (Array.isArray(updatedArrayOrObj)) {
                updatedArrayOrObj.forEach((o) => {
                    const id = o[DB_ID];

                    // Track pagination markers and remove marker attributes
                    if (o._new_top === true) {
                        newTopMarker = id;
                        delete o._new_top;
                    }
                    if (o._new_bottom === true) {
                        newBottomMarker = id;
                        delete o._new_bottom;
                    }

                    if (!activeItemIdMap || activeItemIdMap.get(id)) {
                        if (Object.keys(o).length === 1) {
                            updatesMap.set(id, null);
                        } else {
                            updatesMap.set(id, o);
                        }
                    }
                })
            } else {
                const id = updatedArrayOrObj[DB_ID];

                // Track pagination markers and remove marker attributes
                if (updatedArrayOrObj._new_top === true) {
                    newTopMarker = id;
                    delete updatedArrayOrObj._new_top;
                }
                if (updatedArrayOrObj._new_bottom === true) {
                    newBottomMarker = id;
                    delete updatedArrayOrObj._new_bottom;
                }

                if (!activeItemIdMap || activeItemIdMap.get(id)) {
                    if (Object.keys(updatedArrayOrObj).length === 1) {
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

    // Merge new updates with existing array.
    let finalArray = mergedArray.concat(newUpdates);

    // Apply sorting based on conditions
    if (sortOrders && sortOrders.length > 0) {
        // sortOrders exist: apply sortOrders (regardless of uiLimit)
        const comparator = SortComparator.getInstance(sortOrders);
        finalArray = stableSort(finalArray, comparator);
    } else if (!isAlertModel && uiLimit && (!sortOrders || sortOrders.length === 0)) {
        // Only uiLimit exists (no sortOrders): sort by _id based on uiLimit sign
        const idSortOrder = [{
            sort_by: DB_ID,
            sort_direction: uiLimit > 0 ? 'asc' : 'desc'
        }];
        const comparator = SortComparator.getInstance(idSortOrder);
        finalArray = stableSort(finalArray, comparator);
    }

    // Apply additional alert-specific sorting using stable sort
    if (isAlertModel) {
        const alertComparator = getAlertSortComparator();
        finalArray = stableSort(finalArray, alertComparator);
    }

    // Apply pagination pruning based on markers
    if (newTopMarker !== null || newBottomMarker !== null) {
        let topIndex = -1;
        let bottomIndex = -1;

        // Find indices of marker objects in sorted array
        if (newTopMarker !== null) {
            topIndex = finalArray.findIndex(item => item[DB_ID] === newTopMarker);
        }
        if (newBottomMarker !== null) {
            bottomIndex = finalArray.findIndex(item => item[DB_ID] === newBottomMarker);
        }

        // Slice array based on available markers
        if (newTopMarker !== null && newBottomMarker !== null) {
            // Both markers present
            if (topIndex !== -1 && bottomIndex !== -1) {
                finalArray = finalArray.slice(topIndex, bottomIndex + 1);
            } else {
                console.warn('Pagination markers found but objects not in array. Top:', topIndex, 'Bottom:', bottomIndex);
            }
        } else if (newTopMarker !== null) {
            // Only top marker present
            if (topIndex !== -1) {
                finalArray = finalArray.slice(topIndex);
            } else {
                console.warn('Top pagination marker found but object not in array.');
            }
        } else if (newBottomMarker !== null) {
            // Only bottom marker present
            if (bottomIndex !== -1) {
                finalArray = finalArray.slice(0, bottomIndex + 1);
            } else {
                console.warn('Bottom pagination marker found but object not in array.');
            }
        }
    }

    // Apply client-side limit using Math.abs(uiLimit)
    // Keep items from beginning (index 0 to Math.abs(uiLimit))
    if (uiLimit && Math.abs(uiLimit) > 0 && finalArray.length > Math.abs(uiLimit)) {
        finalArray = finalArray.slice(0, Math.abs(uiLimit));
    }

    postMessage(finalArray);
};

export { };
