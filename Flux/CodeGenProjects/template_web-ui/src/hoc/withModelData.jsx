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
import { sliceMap } from '../models/sliceMap';

/**
 * HOC that injects model metadata and data source config into a component.
 *
 * @param {React.ComponentType<any>} ModelComponent - The component to wrap.
 * @param {object} config - Configuration for the HOC.
 * @param {string} config.modelName - Name of the primary model.
 * @param {string[]} [config.dataSources] - Optional secondary models used by the component.
 * @param {boolean} [config.isAbbreviationSource=false] - Whether the model is an abbreviation source.
 * @param {string|null} [config.modelRootName=null] - Name of the root model if different from modelName.
 *
 * @returns {React.FC} - Enhanced component with model metadata props.
 */
export function withModelData(ModelComponent, config) {
  const {
    modelName,
    dataSources: dataSourceNames = [],
    isAbbreviationSource = false,
    modelRootName = null,
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
     * Generate metadata for the primary model.
     */
    const modelDataSource = useMemo(() => {
      if (!schema || !schemaCollections) return null;

      const modelSchema = getModelSchema(modelName, schema);
      const slice = sliceMap[modelRootName ?? modelName];

      if (!slice) {
        console.warn(`[withModelData] Model "${modelName}" not found in sliceMap.`);
        return null;
      }

      return {
        name: modelName,
        actions: slice.actions,
        selector: slice.selector,
        schema: modelSchema,
        url: getServerUrl(modelSchema),
        viewUrl: getServerUrl(modelSchema, undefined, undefined, undefined, true),
        fieldsMetadata: schemaCollections[modelName],
        isAbbreviationSource,
      };
    }, [schema, schemaCollections]);

    /**
     * Generate metadata for any secondary data sources.
     */
    const dataSources = useMemo(() => {
      if (!schema || !schemaCollections || !dataSourceNames?.length) return null;

      return dataSourceNames.map((dsName) => {
        const dsSchema = getModelSchema(dsName, schema);
        const dsSlice = sliceMap[dsName];

        if (!dsSlice) {
          console.warn(`[withModelData] Data source "${dsName}" not found in sliceMap.`);
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
        };
      }).filter(Boolean); // Remove nulls due to missing slices
    }, [schema, schemaCollections]);

    /**
     * Inject either `dataSource` or `dataSources` prop based on component type.
     * NOTE: Relying on component name (ModelComponent?.name) is brittle and should be refactored
     * to a more robust mechanism (e.g., explicit prop in config) if possible.
     */
    const dataSourceProps = ModelComponent?.displayName === 'AbbreviationMergeModel'
      ? { dataSources, modelRootName }
      : { dataSource: dataSources?.[0] ?? null, modelRootName };

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