import { useRef, useState, useMemo, useCallback } from 'react';
import { cloneDeep, isEqual, get, isObject } from 'lodash';
import { DB_ID, MODES } from '../constants';
import { compareJSONObjects, getObjectsDiff } from '../utils/core/objectUtils';
import { clearxpath } from '../utils/core/dataAccess';

// Hook to handle conflict detection logic
export function useConflictDetection(storedObj, updatedObj, mode, fieldsMetadata, allowUpdates,isCreating = false) {
    const originalObjectSnapshotRef = useRef(null); // Keeps snapshot of data before edits.
    const [showConflictPopup, setShowConflictPopup] = useState(false); // Flags if conflict popup is visible.
    const [conflicts, setConflicts] = useState([]); // Holds detected conflicts.

    // Chooses which stored data to display (original or latest).
    const effectiveStoredData = useMemo(() => {
        const baseData = (mode === MODES.EDIT || !allowUpdates) && originalObjectSnapshotRef.current
            ? originalObjectSnapshotRef.current
            : storedObj;
        
        // For REPEATED_ROOT models, ensure we always return an array
        // This prevents null errors when storedObj is null
        return baseData || [];
    }, [mode, storedObj]);

    // Takes a snapshot of the object before edits.
    const takeSnapshot = useCallback(() => {
        originalObjectSnapshotRef.current = cloneDeep(storedObj);
    }, [storedObj]);

    // Clears the currently stored snapshot.
    const clearSnapshot = useCallback(() => {
        originalObjectSnapshotRef.current = null;
    }, []);

    // Detects conflicts by comparing snapshot, stored, and updated objects.
    const detectConflicts = useCallback(() => {
        if (!originalObjectSnapshotRef.current || isEqual(originalObjectSnapshotRef.current, storedObj)) {
            return [];
        }

        // Uses cleaned and cloned updated object for comparison.
        const modelUpdatedObj = clearxpath(cloneDeep(updatedObj));
        if (!originalObjectSnapshotRef.current || !modelUpdatedObj) {
            console.warn('Cannot detect conflicts: snapshot or updated object is null.');
            return [];
        }

        // Find which fields were changed by the user.
        const userModifiedFields = compareJSONObjects(
            originalObjectSnapshotRef.current,
            modelUpdatedObj,
            fieldsMetadata,
            isCreating
        );

        if (!userModifiedFields || Object.keys(userModifiedFields).length === 0) {
            return [];
        }

        const conflictsResult = [];
        const systemFields = [DB_ID];

        // Recursively check for field-level conflicts.
        const checkConflictsRecursively = (userChanges, snapshotData, currentServerData, path = '') => {
            for (const key in userChanges) {
                if (systemFields.includes(key)) continue;

                const newPath = path ? `${path}.${key}` : key;
                const userValue = userChanges[key];
                const snapshotValue = get(snapshotData, key);
                const serverValue = get(currentServerData, key);

                // Handle conflict detection for arrays of objects.
                if (Array.isArray(userValue) && Array.isArray(snapshotValue)) {
                    userValue.forEach((changedItem) => {
                        const itemId = changedItem[DB_ID];
                        if (!itemId) return;

                        const snapshotItem = snapshotValue.find(item => item[DB_ID] === itemId);
                        const serverItem = serverValue ? serverValue.find(item => item[DB_ID] === itemId) : undefined;

                        if (snapshotItem && !serverItem) {
                            // Item deleted in server but edited by user.
                            conflictsResult.push({
                                field: `${newPath}[id=${itemId}]`,
                                yourValue: `You modified a deleted item.`,
                                serverValue: 'Item does not exist on server.'
                            });
                        } else if (snapshotItem && serverItem) {
                            // Recursive check for conflicts in nested objects.
                            const itemChanges = getObjectsDiff(snapshotItem, changedItem);
                            checkConflictsRecursively(itemChanges, snapshotItem, serverItem, `${newPath}[id=${itemId}]`);
                        }
                    });

                    // Handle nested object conflict checks.
                } else if (isObject(userValue) && !Array.isArray(userValue)) {
                    if (snapshotValue && serverValue) {
                        checkConflictsRecursively(userValue, snapshotValue, serverValue, newPath);
                    }
                } else {
                    // Detects value conflicts for primitives and non-nested values.
                    if (!isEqual(snapshotValue, serverValue)) {
                        conflictsResult.push({
                            field: newPath,
                            yourValue: userValue,
                            serverValue: serverValue
                        });
                    }
                }
            }
        };

        checkConflictsRecursively(userModifiedFields, originalObjectSnapshotRef.current, storedObj);

        return conflictsResult;
    }, [storedObj, updatedObj, fieldsMetadata, isCreating]);

    // Checks for conflicts and shows the popup if any found.
    const checkAndShowConflicts = useCallback(() => {
        const detectedConflicts = detectConflicts();

        if (detectedConflicts.length > 0) {
            setConflicts(detectedConflicts);
            setShowConflictPopup(true);
            return true;
        }
        return false;
    }, [detectConflicts]);

    // Handles closing of conflict popup and clears conflicts.
    const handleConflictPopupClose = useCallback(() => {
        setShowConflictPopup(false);
        setConflicts([]);
    }, []);

    // Returns the object to use as the baseline for future comparisons.
    const getBaselineForComparison = useCallback(() => {
        const baseline = originalObjectSnapshotRef.current || storedObj;
        return baseline;
    }, [storedObj]);

    // Checks if a snapshot currently exists.
    const hasSnapshot = useCallback(() => {
        return originalObjectSnapshotRef.current !== null;
    }, []);

    // Exposes all core state and actions for conflict detection.
    return {
        showConflictPopup,
        conflicts,
        effectiveStoredData,
        takeSnapshot,
        clearSnapshot,
        checkAndShowConflicts,
        closeConflictPopup: handleConflictPopupClose,
        getBaselineForComparison,
        // hasSnapshot,
        setShowConflictPopup,
        setConflicts,
    };
}

export default useConflictDetection;
