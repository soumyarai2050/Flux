import { cloneDeep, get, set } from 'lodash';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { compareJSONObjects } from './core/objectUtils';
import { clearxpath } from './core/dataAccess';
import { DB_ID } from '../constants';

/**
 * Check if any cells have button actions
 * @param {Array} cells - Cell metadata array
 * @returns {boolean} True if at least one cell has a button action
 */
export const hasButttonActions = (cells) => {
  if (!cells || cells.length === 0) return false;
  return cells.some(cell =>
    cell.button &&
    cell.button.action &&
    (cell.button.action === 'flux_toggle' || cell.button.action === 'flux_trigger_strat')
  );
};

/**
 * Extract button metadata from a row
 * Looks for cells with action metadata (flux_toggle, flux_trigger_strat)
 *
 * @param {Object} row - The row data (can be nested from grouped rows)
 * @param {Array} cells - Cell metadata array
 * @returns {Array} Array of button actions found in the row
 */
export const extractButtonActionsFromRow = (row, cells) => {
  if (!row || !cells) return [];

  const actions = [];

  cells.forEach(cell => {
    // Check if cell has a button action (nested in cell.button.action)
    if (cell.button && cell.button.action && (cell.button.action === 'flux_toggle' || cell.button.action === 'flux_trigger_strat')) {
      // Get current value from the row
      // For abbreviation_merge: use cell.tableTitle (which contains the actual field name)
      // For other models: also use cell.tableTitle
      // NOTE: cell.key is the display name (e.g., "Unload"), not the actual field name
      const fieldToCheck = cell.tableTitle;
      const currentValue = get(row, fieldToCheck);

      // Skip if no current value (button field not present in this row)
      if (currentValue === undefined || currentValue === null) {
        return;
      }

      // For xpath, determine what to use for set operation
      // For all models: use jsonPath if available, otherwise tableTitle
      const xpath = cell.jsonPath || cell.tableTitle;

      actions.push({
        action: cell.button.action,
        xpath,
        currentValue,
        cellMetadata: cell,
      });
    }
  });

  return actions;
};

/**
 * Calculate new value based on button action type
 *
 * @param {string} action - The action type (flux_toggle or flux_trigger_strat)
 * @param {*} currentValue - The current value
 * @returns {*} The new value after action transformation
 */
export const calculateNewValue = (action, currentValue) => {
  if (action === 'flux_toggle') {
    return flux_toggle(currentValue);
  } else if (action === 'flux_trigger_strat') {
    return flux_trigger_strat(currentValue);
  }
  return currentValue;
};

/**
 * Check if a button field is disabled via field metadata
 *
 * @param {String} fieldName - The field name (e.g., 'bkr_disable', 'pos_disable')
 * @param {Object} cell - Cell metadata object from schema
 * @returns {Boolean} true if field is disabled (serverPopulate=true)
 */
export const isButtonActionDisabled = (fieldName, cell) => {
  if (!fieldName || !cell) return false;
  return cell.serverPopulate === true;   //TODO: add more flags here which prevent button to go in disabled state 
};

/**
 * Aggregate button actions from selected rows grouped by button type
 * Returns all available buttons with counts and disabled status
 *
 * @param {Array} selectedRowIds - Array of selected row IDs
 * @param {Array} rows - Row data array (for RootModel/NonRootModel with xpath_ fields)
 * @param {Array} cells - Cell metadata array
 * @param {Object} fieldsMetadata - Field metadata for disabled checks
 * @param {String} modelType - Model type: 'root', 'non_root', 'repeated_root', or 'merge'
 * @returns {Object} Aggregated buttons: {buttonName: {count, action, isDisabled, affectedRowIds, cellMetadata}}
 *
 **/

export const aggregateButtonActionsByType = (
  selectedRowIds,
  rows,
  cells,
  modelType = 'root'
) => {
  if (!selectedRowIds || selectedRowIds.length === 0) return {};
  if (!rows || !cells) return {};

  const aggregatedButtons = {};

  // Simple approach: Find all cells that have button actions
  // Then check if those buttons exist in the selected rows
  const buttonCells = cells.filter(c => c.button && c.button.action);

  buttonCells.forEach(cell => {
    const tableTitle = cell.tableTitle;
    const key = cell.key; // Also try cell.key
    const affectedRowIds = [];

    // Check each selected row to see if it has this button field
    selectedRowIds.forEach(selectedId => {
      const row = rows.find(r => r['data-id'] === selectedId || r.DB_ID === selectedId);
      if (!row) return;

      // For abbreviation_merge model, use cell.key instead of tableTitle
      const fieldToCheck = modelType === 'abbreviation_merge' ? key : tableTitle;

      // Check if this row has the button field with a value
      // Try both tableTitle and key as fallback
      const hasField = (row[fieldToCheck] !== undefined && row[fieldToCheck] !== null) ||
        (row[tableTitle] !== undefined && row[tableTitle] !== null) ||
        (row[key] !== undefined && row[key] !== null);

      if (modelType === 'abbreviation_merge' && !hasField) {
        console.log(`[Bulk Patch] Field check for ${key}: fieldToCheck=${fieldToCheck}, row keys sample:`, Object.keys(row).slice(0, 15));
      }

      if (hasField) {
        affectedRowIds.push(selectedId);
      }
    });

    // Only add button if it affects at least one selected row
    if (affectedRowIds.length > 0) {
      // For abbreviation_merge, use cell.key as the primary identifier
      const fieldIdentifier = modelType === 'abbreviation_merge' ? key : (key || tableTitle);
      const displayTableTitle = modelType === 'abbreviation_merge' ? key : tableTitle;

      // Extract just the field name for display (last part after dot)
      const displayName = cell.title;

      aggregatedButtons[displayName] = {
        tableTitle: displayTableTitle,
        displayName: displayName,
        action: cell.button.action,
        count: affectedRowIds.length,
        affectedRowIds,
        isDisabled: isButtonActionDisabled(fieldIdentifier, cell),
        cellMetadata: cell,
      };
    }
  });

  return aggregatedButtons;
};

/**
 * Generate diffs for bulk patch operations (RepeatedRootModel)
 * Creates individual diffs for each selected row with updated values
 *
 * @param {Array} selectedRowIds - Array of selected row IDs
 * @param {Array} storedDataArray - Array of stored objects (e.g., storedPairStratArray)
 * @param {Array} updatedDataArray - Array of updated objects (e.g., updatedPairStratArray)
 * @param {Array} cells - Cell metadata array
 * @param {Object} fieldsMetadata - Field metadata for validation
 * @param {String} selectedButtonType - Optional: Only process this button type (field name)
 * @returns {Array} Array of {rowId, diff} for patching
 */
export const generateBulkPatchDiffs = (
  selectedRowIds,
  storedDataArray,
  updatedDataArray,
  cells,
  fieldsMetadata,
  selectedButtonType = null
) => {
  if (!selectedRowIds || selectedRowIds.length === 0) return [];

  const diffs = [];

  selectedRowIds.forEach(rowId => {
    const storedObj = storedDataArray.find(obj => obj[DB_ID] === rowId);
    const updatedObj = updatedDataArray.find(obj => obj[DB_ID] === rowId);

    if (!storedObj || !updatedObj) {
      console.warn(`Cannot find stored or updated object for ID: ${rowId}`);
      return;
    }

    // Clone and clear xpath from both objects
    const baselineObj = clearxpath(cloneDeep(storedObj));
    let patchObj = clearxpath(cloneDeep(updatedObj));

    // Extract button actions and apply transformations
    const allActions = extractButtonActionsFromRow(updatedObj, cells);

    // Filter actions by selectedButtonType if specified
    const actions = selectedButtonType
      ? allActions.filter(action => action.cellMetadata.tableTitle === selectedButtonType)
      : allActions;

    if (selectedButtonType && actions.length === 0) {
      console.log(`[BulkPatch] No actions found for button type: ${selectedButtonType} in row ${rowId}`);
    }

    actions.forEach(action => {
      const newValue = calculateNewValue(action.action, action.currentValue);
      set(patchObj, action.xpath, newValue);
    });

    // Generate diff using compareJSONObjects
    // For bulk patch operations, we only need the diff, not the captionDict
    const [diff] = compareJSONObjects(baselineObj, patchObj, fieldsMetadata) || [null];

    if (diff && Object.keys(diff).length > 0) {
      diffs.push({
        rowId,
        diff,
      });
    }
  });

  return diffs;
};

/**
 * Generate diff for RootModel with multiple rows (single object)
 *
 * KEY INSIGHT: Each row already contains xpath_ fields with complete xpaths!
 * For example, if a button field is 'bkr_disable', the row will have 'xpath_bkr_disable'
 * that contains the complete path like "eligible_brokers[2].bkr_disable".
 * We just need to extract these xpaths and use lodash.get/set to apply transformations.
 *
 * @param {Array} selectedRowIds - Array of selected row IDs (for tables with multiple rows in single object)
 * @param {Object} storedObj - The single stored/baseline object
 * @param {Object} updatedObj - The single updated object
 * @param {Array} rows - Array of row objects from the table (containing xpath_ fields)
 * @param {Array} cells - Cell metadata array
 * @param {Object} fieldsMetadata - Field metadata for validation
 * @param {String} selectedButtonType - Optional: Only process this button type (field name)
 * @returns {Object|null} {diff} or null if no changes
 */
export const generateBulkPatchDiffForRootModel = (
  selectedRowIds,
  storedObj,
  updatedObj,
  rows,
  cells,
  fieldsMetadata,
  selectedButtonType = null
) => {
  if (!selectedRowIds || selectedRowIds.length === 0) return null;
  if (!storedObj || !updatedObj || !rows) {
    console.warn('Cannot generate diff - missing stored, updated object, or rows');
    return null;
  }

  // Build button action map from cells using tableTitle (not cell.key)
  const buttonActionMap = {};
  cells.forEach(cell => {
    if (cell.button && cell.button.action) {
      const buttonName = cell.tableTitle;

      // Extract short name for filtering and map key
      const shortName = buttonName.includes('.')
        ? buttonName.substring(buttonName.lastIndexOf('.') + 1)
        : buttonName;

      // Filter by selectedButtonType if specified
      // selectedButtonType can be either full path or short name
      if (selectedButtonType && buttonName !== selectedButtonType && shortName !== selectedButtonType) {
        return;
      }

      // Store using SHORT name as key (since xpath_ keys extract to short names)
      buttonActionMap[shortName] = cell.button.action;
    }
  });

  const allXpathsToUpdate = [];

  // Process each selected row ID
  selectedRowIds.forEach(selectedId => {
    // Find matching row
    const row = rows.find(r => r['data-id'] === selectedId || r.DB_ID === selectedId);
    if (!row) {
      console.warn(`Row not found for ID: ${selectedId}`);
      return;
    }
    // Find all keys with xpath_ and process them
    Object.keys(row).forEach(key => {
      if (!key.includes('xpath_')) return;

      const lastDotIndex = key.lastIndexOf('.');
      const afterLastDot = lastDotIndex !== -1 ? key.substring(lastDotIndex + 1) : key;
      const fieldName = afterLastDot.startsWith('xpath_') ? afterLastDot.substring(6) : null;

      if (!fieldName || !buttonActionMap[fieldName]) return;

      const xpath = row[key];
      if (!xpath) return;

      // Get current value
      const currentValue = get(updatedObj, xpath);
      if (currentValue === undefined) return;

      // Calculate new value
      const newValue = calculateNewValue(buttonActionMap[fieldName], currentValue);

      if (currentValue !== newValue) {
        console.log(`  ${fieldName}: ${currentValue} -> ${newValue}`);
        allXpathsToUpdate.push({
          xpath: xpath,
          newValue,
          rowId: selectedId,
        });
      }
    });
  });

  if (allXpathsToUpdate.length === 0) {
    console.log('No transformations needed');
    return null;
  }

  // Clone and apply all transformations
  const modelUpdatedObj = clearxpath(cloneDeep(updatedObj));

  allXpathsToUpdate.forEach(({ xpath, newValue }) => {
    set(modelUpdatedObj, xpath, newValue);
  });

  // Compare stored vs updated with transformations applied
  // For bulk patch operations, we only need the diff, not the captionDict
  const [diff] = compareJSONObjects(
    clearxpath(cloneDeep(storedObj)),
    modelUpdatedObj,
    fieldsMetadata
  ) || [null];

  if (diff && Object.keys(diff).length > 0) {
    return {
      diff,
    };
  }

  console.log('No diff generated - no actual changes after transformations');
  return null;
};

/**
 * Generate diffs for AbbreviationMergeView with multiple data sources and grouped rows
 *
 * KEY ARCHITECTURE:
 * - selectedRowIds: Array of row IDs that appear across multiple data sources
 * - dataSourcesUpdatedArrayDict: {source1: [rows], source2: [rows], ...}
 * - dataSourcesStoredArrayDict: {source1: [rows], source2: [rows], ...}
 * - cells: Contains sourceIndex and source metadata for multi-source lookup
 *
 * For each selected rowId:
 *   1. Find matching row in EACH data source array
 *   2. Extract button actions for cells from that source
 *   3. Build patch for each source independently
 *
 * Returns diffs grouped by data source so we can execute them separately
 *
 * @param {Array} selectedRowIds - Array of row IDs selected by user
 * @param {Object} dataSourcesStoredArrayDict - Map of source -> stored array
 * @param {Object} dataSourcesUpdatedArrayDict - Map of source -> updated array
 * @param {Array} cells - Cell metadata array (includes source, sourceIndex)
 * @param {Object} dataSourcesMetadataDict - Map of source -> fieldsMetadata
 * @param {String} selectedButtonType - Optional: Only process this button type (field name)
 * @returns {Object} {diffsBySource: {source1: [...diffs], source2: [...diffs]}}
 */
export const generateBulkPatchDiffsForMergeView = (
  selectedRowIds,
  dataSourcesStoredArrayDict,
  dataSourcesUpdatedArrayDict,
  cells,
  dataSourcesMetadataDict,
  selectedButtonType = null
) => {
  if (!selectedRowIds || selectedRowIds.length === 0) {
    console.warn('No rows selected for bulk patch');
    return { diffsBySource: {}, captionDict: {} };
  }

  const diffsBySource = {};

  // Iterate through each data source
  Object.keys(dataSourcesUpdatedArrayDict).forEach(source => {
    const storedArray = dataSourcesStoredArrayDict[source];
    const updatedArray = dataSourcesUpdatedArrayDict[source];
    const fieldsMetadata = dataSourcesMetadataDict[source];

    if (!storedArray || !updatedArray || !fieldsMetadata) {
      console.warn(`Incomplete metadata for source: ${source}`);
      return;
    }

    const sourceDiffs = [];

    // For each selected row ID, find it in this source and build a patch
    selectedRowIds.forEach(rowId => {
      const storedObj = storedArray.find(obj => obj[DB_ID] === rowId);
      const updatedObj = updatedArray.find(obj => obj[DB_ID] === rowId);

      // Skip if this row doesn't exist in this source
      if (!storedObj || !updatedObj) {
        return;
      }

      // Clone and clear xpath from both objects
      const baselineObj = clearxpath(cloneDeep(storedObj));
      let patchObj = clearxpath(cloneDeep(updatedObj));

      // Get cells that belong to this source
      const sourceCells = cells.filter(cell => cell.source === source);

      // Extract button actions from cells of this source
      const allActions = extractButtonActionsFromRow(updatedObj, sourceCells);

      if (allActions.length === 0) {
        console.log(`  [${source}] No button actions extracted. sourceCells with buttons: ${sourceCells.filter(c => c.button && c.button.action).length}`);
        sourceCells.filter(c => c.button && c.button.action).forEach(c => {
          console.log(`    - cell.key=${c.key}, found in row=${updatedObj[c.key.includes('.') ? c.key.substring(c.key.lastIndexOf('.') + 1) : c.key] !== undefined}`);
        });
      }

      // Filter actions by selectedButtonType if specified
      const actions = selectedButtonType
        ? allActions.filter(action => {
          // Match by:
          // 1. Full tableTitle match
          // 2. Short name match (last part after dot)
          // 3. cell.key match (for abbreviation_merge)
          // 4. Short name extracted from cell.key
          const fullMatch = action.cellMetadata.tableTitle === selectedButtonType;
          const shortName = action.cellMetadata.tableTitle.includes('.')
            ? action.cellMetadata.tableTitle.substring(action.cellMetadata.tableTitle.lastIndexOf('.') + 1)
            : action.cellMetadata.tableTitle;
          const shortMatch = shortName === selectedButtonType;
          const keyMatch = action.cellMetadata.key === selectedButtonType;

          // Also try extracting short name from cell.key
          const keyShortName = action.cellMetadata.key.includes('.')
            ? action.cellMetadata.key.substring(action.cellMetadata.key.lastIndexOf('.') + 1)
            : action.cellMetadata.key;
          const keyShortMatch = keyShortName === selectedButtonType;

          const matched = fullMatch || shortMatch || keyMatch || keyShortMatch;
          if (!matched && allActions.length > 0) {
            console.log(`[BulkPatch] Action NOT matched: tableTitle=${action.cellMetadata.tableTitle}, key=${action.cellMetadata.key}, selectedButtonType=${selectedButtonType}`);
          }
          return matched;
        })
        : allActions;

      if (actions.length > 0) {
        console.log(`  Found ${actions.length} button actions`);
      }

      // Apply transformations
      actions.forEach(action => {
        const newValue = calculateNewValue(action.action, action.currentValue);
        console.log(`  Applying: ${action.xpath} = ${newValue}`);
        set(patchObj, action.xpath, newValue);
      });

      // Generate diff using compareJSONObjects
      // For bulk patch operations, we only need the diff, not the captionDict
      const [diff] = compareJSONObjects(
        baselineObj,
        patchObj,
        fieldsMetadata
      ) || [null];

      if (diff && Object.keys(diff).length > 0) {
        sourceDiffs.push({
          rowId,
          diff,
        });
      }
    });

    if (sourceDiffs.length > 0) {
      diffsBySource[source] = sourceDiffs;
    }
  });

  return {
    diffsBySource,
  };
};

/**
 * ============================================================================
 * UNIFIED API - Use these functions instead of calling generators directly
 * ============================================================================
 * These unified functions provide a single entry point for all model types
 * using the MODEL_TYPES enum for type-safe routing
 */

/**
 * Unified diff generation function for all model types
 * Routes to appropriate generator based on MODEL_TYPES enum
 *
 * @param {string} modelType - One of MODEL_TYPES (ROOT, NON_ROOT, REPEATED_ROOT, ABBREVIATION_MERGE)
 * @param {Array} selectedRowIds - Selected row IDs
 * @param {Object} config - Model-specific configuration object
 * @returns {Object|Array|null} Diff result (varies by model type)
 *
 * @example
 * // For ROOT model
 * const result = generateBulkPatchDiff(MODEL_TYPES.ROOT, selectedIds, {
 *   storedObj, updatedObj, rows, cells, fieldsMetadata
 * });
 *
 * // For REPEATED_ROOT model
 * const result = generateBulkPatchDiff(MODEL_TYPES.REPEATED_ROOT, selectedIds, {
 *   storedDataArray, updatedDataArray, cells, fieldsMetadata
 * });
 *
 * // For ABBREVIATION_MERGE model
 * const result = generateBulkPatchDiff(MODEL_TYPES.ABBREVIATION_MERGE, selectedIds, {
 *   dataSourcesStoredArrayDict, dataSourcesUpdatedArrayDict, cells, dataSourcesMetadataDict
 * });
 */
export const generateBulkPatchDiff = (modelType, selectedRowIds, config, selectedButtonType = null) => {
  if (!selectedRowIds?.length) {
    console.warn('[BulkPatch] No rows selected for bulk patch');
    return modelType === 'abbreviation_merge'
      ? { diffsBySource: {}, captionDict: {} }
      : null;
  }

  switch (modelType) {
    case 'root':
    case 'non_root':
      // Both use same function, config structure:
      // { storedObj, updatedObj, rows, cells, fieldsMetadata, rootPathPrefix? }
      console.log(`[BulkPatch] Generating diff for ${modelType} model`);
      return generateBulkPatchDiffForRootModel(
        selectedRowIds,
        config.storedObj,
        config.updatedObj,
        config.rows,
        config.cells,
        config.fieldsMetadata,
        selectedButtonType
      );

    case 'repeated_root':
      // Config structure: { storedDataArray, updatedDataArray, cells, fieldsMetadata }
      console.log(`[BulkPatch] Generating diffs for ${modelType} model`);
      return generateBulkPatchDiffs(
        selectedRowIds,
        config.storedDataArray,
        config.updatedDataArray,
        config.cells,
        config.fieldsMetadata,
        selectedButtonType
      );

    case 'abbreviation_merge':
      // Config structure: { dataSourcesStoredArrayDict, dataSourcesUpdatedArrayDict, cells, dataSourcesMetadataDict }
      console.log(`[BulkPatch] Generating diffs for ${modelType} model`);
      return generateBulkPatchDiffsForMergeView(
        selectedRowIds,
        config.dataSourcesStoredArrayDict,
        config.dataSourcesUpdatedArrayDict,
        config.cells,
        config.dataSourcesMetadataDict,
        selectedButtonType
      );

    default:
      throw new Error(`[BulkPatch] Unknown model type: ${modelType}`);
  }
};

/**
 * Unified patch execution for all model types
 * Handles both single-URL and multi-source scenarios
 *
 * @param {Object} dispatchConfig - Dispatch configuration
 *   For single-source: { url, dispatcher: (payload) => dispatch(...) }
 *   For multi-source: { urlsBySource, dispatcher: (source, payload) => dispatch(...) }
 * @param {Object|Array} diffs - Diff result from generateBulkPatchDiff
 * @param {string} modelType - MODEL_TYPES enum value
 * @returns {Promise<Object>} { successful: [], failed: [] }
 *
 * @example
 * // Single-source execution
 * const results = await executePatches(
 *   { url: 'api/patch', dispatcher: (payload) => dispatch(action(payload)) },
 *   diffs,
 *   'root'
 * );
 *
 * // Multi-source execution
 * const results = await executePatches(
 *   { urlsBySource: {src1: 'url1'}, dispatcher: (src, payload) => dispatch(action(src, payload)) },
 *   diffsBySource,
 *   'abbreviation_merge'
 * );
 */
export const executePatches = async (dispatchConfig, diffs, modelType) => {
  if (modelType === 'abbreviation_merge') {
    return executePatchesMultiSource(dispatchConfig, diffs);
  } else {
    return executePatchesSingleUrl(dispatchConfig, diffs);
  }
};

/**
 * Internal: Single URL execution (ROOT, NON_ROOT, REPEATED_ROOT)
 * @private
 */
const executePatchesSingleUrl = async (dispatchConfig, diffs) => {
  const results = {
    successful: [],
    failed: []
  };

  // Handle null result (no changes)
  if (!diffs) {
    console.log('[BulkPatch] No diffs to execute');
    return results;
  }

  // Handle both single diff {diff, captionDict} and array of diffs [{rowId, diff}]
  const diffArray = Array.isArray(diffs) ? diffs : [diffs];

  for (const diffItem of diffArray) {
    try {
      const patchPayload = {
        url: dispatchConfig.url,
        data: diffItem.diff,
        force: true
      };

      await dispatchConfig.dispatcher(patchPayload);

      const identifier = diffItem.rowId || 'root';
      results.successful.push(identifier);
      console.log(`[BulkPatch] ✓ Patch successful for ${identifier}`);
    } catch (error) {
      const identifier = diffItem.rowId || 'root';
      results.failed.push({
        identifier,
        error: error.message
      });
      console.error(`[BulkPatch] ✗ Patch failed for ${identifier}:`, error);
    }
  }

  return results;
};

/**
 * Internal: Multi-source execution (ABBREVIATION_MERGE)
 * @private
 */
const executePatchesMultiSource = async (dispatchConfig, diffResult) => {
  const results = {
    successful: [],
    failed: []
  };

  // diffResult has { diffsBySource, captionDict }
  const diffsBySource = diffResult.diffsBySource || diffResult;

  for (const source of Object.keys(diffsBySource)) {
    const diffs = diffsBySource[source];
    const url = dispatchConfig.urlsBySource[source];

    if (!url) {
      console.warn(`[BulkPatch] No URL configured for source: ${source}`);
      continue;
    }

    for (const diffItem of diffs) {
      try {
        const patchPayload = {
          url,
          data: diffItem.diff,
          force: true
        };

        await dispatchConfig.dispatcher(source, patchPayload);

        const identifier = `${source}:${diffItem.rowId}`;
        results.successful.push(identifier);
        console.log(`[BulkPatch] ✓ Patch successful for ${identifier}`);
      } catch (error) {
        const identifier = `${source}:${diffItem.rowId}`;
        results.failed.push({
          identifier,
          error: error.message
        });
        console.error(`[BulkPatch] ✗ Patch failed for ${identifier}:`, error);
      }
    }
  }

  return results;
};
