import { useCallback } from 'react';
import { useDispatch } from 'react-redux';
import {
  generateBulkPatchDiff,
  executePatches
} from '../utils/bulkPatchUtils';

/**
 * Custom Hook for Bulk Patch Operations
 * Encapsulates all bulk patch logic in a single reusable hook
 *
 * This hook eliminates ~50-100 lines of duplicated code per container
 * by abstracting common patterns into a single reusable interface.
 *
 * @param {string} modelType - One of MODEL_TYPES from constants.js
 *                             ('root', 'non_root', 'repeated_root', 'abbreviation_merge')
 * @param {Object} config - Configuration object
 *   @param {Object} config.diffConfig - Model-specific diff generation config
 *                                       Structure varies by modelType
 *   @param {Object} config.dispatchConfig - Model-specific dispatch setup
 *                                           Structure varies by modelType
 *
 * @returns {Function} handleBulkPatch(selectedRowIds)
 *   Returns: Promise<{
 *     success: boolean,
 *     message: string,
 *     rowsProcessed: number,
 *     successful: Array,
 *     failed: Array
 *   }>
 *
 * @example
 * // RootModel usage
 * const handleBulkPatch = useBulkPatch('root', {
 *   diffConfig: {
 *     storedObj: baselineForComparison(),
 *     updatedObj,
 *     rows,
 *     cells: sortedCells,
 *     fieldsMetadata
 *   },
 *   dispatchConfig: {
 *     url: modelSchema?.json_root?.url,
 *     action: actions.partialUpdate
 *   }
 * });
 * <DataTable onBulkPatch={handleBulkPatch} {...} />
 *
 * @example
 * // RepeatedRootModel usage
 * const handleBulkPatch = useBulkPatch('repeated_root', {
 *   diffConfig: {
 *     storedDataArray,
 *     updatedDataArray: rows,
 *     cells: sortedCells,
 *     fieldsMetadata
 *   },
 *   dispatchConfig: {
 *     url,
 *     action: actions.partialUpdate
 *   }
 * });
 *
 * @example
 * // AbbreviationMergeModel usage
 * const handleBulkPatch = useBulkPatch('abbreviation_merge', {
 *   diffConfig: {
 *     dataSourcesStoredArrayDict,
 *     dataSourcesUpdatedArrayDict,
 *     cells: sortedCells,
 *     dataSourcesMetadataDict
 *   },
 *   dispatchConfig: {
 *     urlsBySource: dataSourcesUrlDict,
 *     getActionBySource: (source) => dataSources[source].actions.partialUpdate
 *   }
 * });
 */
export const useBulkPatch = (modelType, config) => {
  const dispatch = useDispatch();

  const handleBulkPatch = useCallback(async (selectedRowIds, selectedButtonType = null) => {
    // Step 1: Validate input
    if (!selectedRowIds || selectedRowIds.length < 1) {
      const message = 'Bulk patch requires at least 1 selected row';
      console.warn(`[BulkPatch] ${message}`);
      return {
        success: false,
        error: message,
        rowsProcessed: 0,
        successful: [],
        failed: []
      };
    }

    try {
      // Step 2: Generate diffs
      console.log(`[BulkPatch] Generating diffs for ${selectedRowIds.length} rows (${modelType})${selectedButtonType ? ` [${selectedButtonType}]` : ''}`);

      const diffResult = generateBulkPatchDiff(
        modelType,
        selectedRowIds,
        config.diffConfig,
        selectedButtonType
      );

      // Check for empty results based on model type
      let hasChanges = false;
      if (modelType === 'abbreviation_merge') {
        // For merge view, check if there are any diffs in any source
        hasChanges = diffResult?.diffsBySource &&
                     Object.values(diffResult.diffsBySource).some(sourceDiffs => sourceDiffs.length > 0);
      } else {
        // For other models, check if diffs array has items
        hasChanges = diffResult && (Array.isArray(diffResult) ? diffResult.length > 0 : true);
      }

      if (!hasChanges) {
        const message = 'No changes found in selected rows';
        console.log(`[BulkPatch] ${message}`);
        return {
          success: false,
          error: message,
          rowsProcessed: 0,
          successful: [],
          failed: []
        };
      }

      // Step 3: Build dispatch configuration
      const dispatchConfig = buildDispatchConfig(modelType, dispatch, config.dispatchConfig);

      // Step 4: Execute patches sequentially
      console.log(`[BulkPatch] Executing patches for ${selectedRowIds.length} rows`);

      const results = await executePatches(dispatchConfig, diffResult, modelType);

      // Step 5: Format and return results
      const success = results.failed.length === 0;
      const message = success
        ? `Successfully patched ${results.successful.length} rows`
        : `Patched ${results.successful.length} rows with ${results.failed.length} failures`;

      console.log(`[BulkPatch] Complete:`, { success, message, results });

      return {
        success,
        message,
        rowsProcessed: selectedRowIds.length,
        successful: results.successful,
        failed: results.failed
      };

    } catch (error) {
      console.error('[BulkPatch] Error:', error);
      return {
        success: false,
        error: error.message,
        rowsProcessed: selectedRowIds.length,
        successful: [],
        failed: []
      };
    }

  }, [dispatch, modelType, config]);

  return handleBulkPatch;
};

/**
 * Helper: Build dispatch configuration based on model type
 * Abstracts the differences in dispatch setup for each model type
 *
 * @private
 */
const buildDispatchConfig = (modelType, dispatch, dispatchConfig) => {
  switch (modelType) {
    case 'root':
    case 'non_root':
    case 'repeated_root':
      // Single-source dispatch
      return {
        url: dispatchConfig.url,
        dispatcher: (payload) => dispatch(dispatchConfig.action(payload))
      };

    case 'abbreviation_merge':
      // Multi-source dispatch
      return {
        urlsBySource: dispatchConfig.urlsBySource,
        dispatcher: (source, payload) => {
          const action = dispatchConfig.getActionBySource(source);
          return dispatch(action(payload));
        }
      };

    default:
      throw new Error(`[BulkPatch] Unknown model type: ${modelType}`);
  }
};

export default useBulkPatch;