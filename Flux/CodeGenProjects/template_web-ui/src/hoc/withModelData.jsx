/**
 * @file withModelData.js
 * @description
 * Higher-order component (HOC) that injects schema-derived metadata, Redux selectors,
 * and actions into model-driven components. Enables schema-based rendering and behavior
 * with minimal boilerplate.
 */

import React, { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { getModelSchema } from '../utils/core/schemaUtils';
import { getServerUrl } from '../utils/network/networkUtils';
import { sliceMapWithFallback } from '../models/sliceMap';

/**
 * HOC that injects model metadata and data source config into a component.
 *
 * @param {React.ComponentType<any>} ModelComponent - The component to wrap.
 * @param {object} config - Configuration for the HOC.
 * @param {string} config.modelName - Name of the primary model.
 * @param {string[]} [config.dataSources] - source models for AbbreviationMergeModel.
 * @param {boolean} [config.isAbbreviationSource=false] - Whether the model is an abbreviation source.
 * @param {string|null} [config.modelRootName=null] - Name of the root model if different from modelName.
 * @param {object|null} [config.modelDependencyMap=null] - Map with optional keys (urlOverride, crudOverride, defaultFilter) where each value is a dataSource name.
 *
 * @returns {React.FC} - Enhanced component with model metadata props.
 */
export function withModelData(ModelComponent, config) {
  const {
    modelName,
    dataSources: dataSourceNames = [],
    isAbbreviationSource = false,
    modelRootName = null,
    modelDependencyMap = null,
  } = config;

  /**
   * @function WrappedComponent
   * @description The component wrapped by withModelData HOC. It injects model-specific props.
   * @param {object} props - The original props passed to the wrapped component.
   * @returns {React.ReactElement} The ModelComponent with injected props.
   */
  return function WrappedComponent(props) {
    const { schema, schemaCollections } = useSelector((state) => state.schema);

    /**
     * Helper function to build dataSource object for a given model name.
     * @param {string} dsName - The model name to use for schema lookup
     * @param {string} [sliceLookupName] - Optional override for slice lookup (defaults to dsName)
     * @param {object} [extraProps] - Additional properties to merge into the dataSource
     */
    const buildDataSource = useMemo(() => (dsName, sliceLookupName, extraProps = {}) => {
      if (!schema || !schemaCollections) return null;

      const lookupName = sliceLookupName ?? dsName;
      const dsSchema = getModelSchema(dsName, schema);
      const dsSlice = sliceMapWithFallback[lookupName];

      if (!dsSlice) {
        console.warn(`[withModelData] Data source "${lookupName}" not found in sliceMapWithFallback.`);
        return null;
      }

      return {
        name: dsName,
        actions: dsSlice.actions,
        selector: dsSlice.selector,
        schema: dsSchema,
        url: getServerUrl(dsSchema),
        viewUrl: getServerUrl(dsSchema, undefined, undefined, undefined, true),
        fieldsMetadata: schemaCollections[dsName],
        ...extraProps,
      };
    }, [schema, schemaCollections]);

    /**
     * Generate metadata for the primary model.
     */
    const modelDataSource = useMemo(() => {
      const sliceLookupName = modelRootName ?? modelName;

      return buildDataSource(modelName, sliceLookupName, { isAbbreviationSource });
    }, [buildDataSource, modelName, modelRootName, isAbbreviationSource]);

    /**
     * Generate metadata for any secondary data sources.
     */
    const dataSources = useMemo(() => {
      if (!dataSourceNames?.length) return null;

      return dataSourceNames
        .map((dsName) => buildDataSource(dsName, null, {}))
        .filter(Boolean);
    }, [buildDataSource, dataSourceNames]);

    /**
     * Process modelDependencyMap by replacing dataSource names with their corresponding dataSource objects.
     * Only applicable for Root/NonRoot/RepeatedRoot models (not AbbreviationMergeModel).
     * Validates that the data source exists in schema before building it.
     */
    const processedModelDependencyMap = useMemo(() => {
      if (!modelDependencyMap || !schemaCollections) return null;

      const processed = {};
      const availableModelNames = Object.keys(schemaCollections);

      for (const [key, dsName] of Object.entries(modelDependencyMap)) {
        // Only build dataSource if the model exists in schema
        if (dsName && availableModelNames.includes(dsName)) {
          processed[key] = buildDataSource(dsName, null, {});
        } else {
          // Model doesn't exist in schema, set to null
          processed[key] = null;
        }
      }

      return processed;
    }, [modelDependencyMap, buildDataSource, schemaCollections]);

    /**
     * Inject props based on component type:
     * - AbbreviationMergeModel: only dataSources
     * - Root/NonRoot/RepeatedRoot models: only modelDependencyMap and modelRootName
     * NOTE: Relying on component name (ModelComponent?.name) is brittle and should be refactored
     * to a more robust mechanism (e.g., explicit prop in config) if possible.
     */
    const isAbbreviationMerge = ModelComponent?.displayName === 'AbbreviationMergeModel';

    const dataSourceProps = isAbbreviationMerge
      ? { dataSources }
      : { modelDependencyMap: processedModelDependencyMap, modelRootName };

    return (
      <ModelComponent
        modelName={modelName}
        modelDataSource={modelDataSource}
        {...dataSourceProps}
        {...props}
      />
    );
  };
}