import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { withModelData } from '../../hoc/withModelData';
import RootModel from '../RootModel';
import RepeatedRootModel from '../RepeatedRootModel';
import AbbreviationMergeModel from '../AbbreviationMergeModel'
import ChartModel from '../ChartModel';
import { getModelTypeFromSchema } from '../../utils/dynamicSchemaUtils/modelTypeUtils'
import { MODEL_TYPES } from '../../constants';
import NonRootModel from '../NonRootModel';

/**
 * GenericModel component acts as a dynamic fallback wrapper.
 * Dynamically selects the appropriate container (RootModel, ChartModel, etc.) based on schema.
 * @returns {JSX.Element} The GenericModel component.
 */
const GenericModel = ({ modelName }) => {
  const { schema, abbreviationModelToSourcesMap, modelToDependencyMap } = useSelector((state) => state.schema);

  // Determine the model type from schema
  const modelType = useMemo(() => {
    if (!schema || !schema[modelName]) {
      console.warn(`[GenericModel] No schema found for model: ${modelName}`);
      return MODEL_TYPES.ROOT; // Default fallback
    }
    return getModelTypeFromSchema(schema[modelName]);
  }, [schema, modelName]);

  // Get dataSources for abbreviation merge models from the precomputed map
  const abbreviationDataSources = useMemo(() => {
    return abbreviationModelToSourcesMap?.[modelName] || [];
  }, [abbreviationModelToSourcesMap, modelName]);

  // Get modelDependencyMap from the precomputed map
  const dependencyMap = useMemo(() => {
    return modelToDependencyMap?.[modelName] || null;
  }, [modelToDependencyMap, modelName]);

  // Select the appropriate container component based on model type
  const ContainerComponent = useMemo(() => {
    switch (modelType) {
      case MODEL_TYPES.CHART:
        return ChartModel;
      case MODEL_TYPES.REPEATED_ROOT:
        return RepeatedRootModel;
      case MODEL_TYPES.NONROOT:
        return NonRootModel;
      case MODEL_TYPES.ROOT:
        return RootModel;
      case MODEL_TYPES.ABBREVIATION_MERGE:
        return AbbreviationMergeModel;
      default:
        return RootModel;
    }
  }, [modelType]);

  // Create the wrapped component with modelData HOC
  const WrappedComponent = useMemo(() => {
    const isAbbreviationMerge = modelType === MODEL_TYPES.ABBREVIATION_MERGE;

    return withModelData(ContainerComponent, {
      modelName,
      modelDependencyMap: dependencyMap ?? null,
      dataSources: isAbbreviationMerge ? abbreviationDataSources : []
    });
  }, [ContainerComponent, modelName, modelType, abbreviationDataSources, dependencyMap]);

  // Render the wrapped component
  return <WrappedComponent />;
};

export default GenericModel;