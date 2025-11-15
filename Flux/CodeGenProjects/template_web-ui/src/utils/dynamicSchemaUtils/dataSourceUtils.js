
export function getDataSourcesFromSchema(modelSchema) {
  if (!modelSchema) {
    return [];
  }

  const dataSourcesSet = new Set();

  const connectionDependency = modelSchema.connection_dependency?.[0];

  // Rule 1: Check for connection_dependency (non-abbreviated models)
  const dependingModelName = connectionDependency?.source_model_name;
  if (dependingModelName) {
    dataSourcesSet.add(dependingModelName);
  }

  // Rule 1b: Check override_default_crud for query_src_model_name
  const overrideCrud = modelSchema?.override_default_crud;
  if (Array.isArray(overrideCrud)) {
    overrideCrud.forEach((crud) => {
      if (crud?.query_src_model_name) {
        dataSourcesSet.add(crud.query_src_model_name);
      }
    });
  }

  // Rule 1c: Check default_filter_param for query_src_model_name
  const defaultFilter = modelSchema?.default_filter_param?.[0];
  if (defaultFilter && typeof defaultFilter === 'object'){
    if (defaultFilter?.param_src_model_name) {
      dataSourcesSet.add(defaultFilter.param_src_model_name);
    }
  }

  // Rule 2: Check for abbreviated fields (abbreviated/filter models ONLY)
  // First, check if this is an abbreviated/filter model by checking view_layout
  const widgetUiData = modelSchema?.widget_ui_data_element?.widget_ui_data;
  const isAbbreviatedModel = widgetUiData?.some(
    (uiData) => uiData?.view_layout === 'UI_ABBREVIATED_FILTER'
  );

  // Validate non-abbreviated models should have at most 1 data source
  if (!isAbbreviatedModel && dataSourcesSet.size > 1) {
    const allDataSources = Array.from(dataSourcesSet);
    console.warn(`⚠️ Non-abbreviated model has ${dataSourcesSet.size} data sources: [${allDataSources.join(', ')}]. Using first: ${allDataSources[0]}`);
    // Keep only the first data source
    dataSourcesSet.clear();
    dataSourcesSet.add(allDataSources[0]);
  }

  if (isAbbreviatedModel) {

    // Dynamically find fields containing "load" or "buffer" with "abbreviated" property
    const properties = modelSchema?.properties || {};
    const abbreviatedFieldNames = Object.keys(properties).filter((fieldName) => {
      const lowerName = fieldName.toLowerCase();
      const hasAbbreviated = properties[fieldName]?.abbreviated;
      return hasAbbreviated && (lowerName.includes('load') || lowerName.includes('buffer'));
    });


    abbreviatedFieldNames.forEach((fieldName) => {
      const field = properties[fieldName];
      const abbreviatedString = field?.abbreviated;

      if (abbreviatedString) {

        // Parse abbreviated string: "Key1:model1.field^Key2:model2.field^..."
        // Split by ^ to get individual key:value pairs
        const pairs = abbreviatedString.split('^');

        pairs.forEach((pair) => {
          // Split by : to separate display key from model path
          const [_, modelPath] = pair.split(':');

          if (modelPath) {
            // Extract model name (first part before the dot)
            // e.g., "pair_strat.pair_strat_params.strat_leg1.side" → "pair_strat"
            // e.g., "strat_view.balance_notional" → "strat_view"
            const modelName = modelPath.split('.')[0];

            if (modelName) {
              dataSourcesSet.add(modelName);
            }
          }
        });
      }
    });
  }

  const dataSources = Array.from(dataSourcesSet);

  return dataSources;
}

/**
 * Extract modelDependencyMap from schema.
 * Returns an object with optional keys (urlOverride, crudOverride, defaultFilter, idDependent)
 * where each value is a dataSource name.
 * Applicable for all model types (Root/NonRoot/RepeatedRoot/AbbreviationMerge).
 *
 * @param {object} modelSchema - The schema for a specific model
 * @returns {object|null} - Map of dependency configurations or null
 */
export function getModelDependencyMap(modelSchema) {
  if (!modelSchema) {
    return null;
  }

  const dependencyMap = {};

  const connectionDependency = modelSchema.connection_dependency?.[0];

  // Extract urlOverride (from connection_dependency)
  const dependingModelName = connectionDependency?.source_model_name;
  if (dependingModelName) {
    dependencyMap.urlOverride = dependingModelName;
  }

  // Extract crudOverride (from override_default_crud)
  const overrideCrud = modelSchema?.override_default_crud;
  if (Array.isArray(overrideCrud) && overrideCrud.length > 0) {
    // Take the first query_src_model_name if multiple exist
    const crudSource = overrideCrud.find(crud => crud?.query_src_model_name);
    if (crudSource?.query_src_model_name) {
      dependencyMap.crudOverride = crudSource.query_src_model_name;
    }
  }

  // Extract defaultFilter (from default_filter_param)
  const defaultFilter = modelSchema?.default_filter_param?.[0];
  if (defaultFilter && typeof defaultFilter === 'object' && defaultFilter?.param_src_model_name) {
    dependencyMap.defaultFilter = defaultFilter.param_src_model_name;
  }

  // Extract idDependent (from id_dependency)
  const idDependentModelName = modelSchema?.id_dependency?.[0]?.source_model_name;
  if (idDependentModelName) {
    dependencyMap.idDependent = idDependentModelName;
  }

  // Return null if no dependencies found, otherwise return the map
  return Object.keys(dependencyMap).length > 0 ? dependencyMap : null;
}


/**
 * Computes model-to-dependent mappings for all widget models in the schema.
 * This function processes both abbreviated and non-abbreviated models to extract:
 *
 * 1. abbreviationModelToSourcesMap: Maps abbreviated models to their data source models
 * 2. modelToDependencyMap: Maps all models to their dependency configurations
 *    (urlOverride, crudOverride, defaultFilter, idDependent)
 * 3. abbreviationSourcesSet: Set of all models that serve as data sources for abbreviated models
 *
 * @param {object} schema - The complete schema object containing all model definitions
 * @returns {object} - Object with three properties:
 *   - abbreviationModelToSourcesMap: { [modelName]: string[] }
 *   - modelToDependencyMap: { [modelName]: { urlOverride?, crudOverride?, defaultFilter?, idDependent? } }
 *   - abbreviationSourcesSet: Set<string>
 */
export function computeModelToDependentMap(schema) {
  if (!schema || typeof schema !== 'object') {
    console.warn('[computemodelToDependentMap] Invalid schema provided');
    return {
      abbreviationModelToSourcesMap: {},
      modelToDependencyMap: {},
      abbreviationSourcesSet: new Set()
    };
  }


  const abbreviationModelToSourcesMap = {};
  const modelToDependencyMap = {};
  const abbreviationSourcesSet = new Set();
  const modelNames = Object.keys(schema);

  modelNames.forEach((modelName) => {
    const modelSchema = schema[modelName];

    // Skip non-widget models (like definitions, autocomplete, file_options)
    if (!modelSchema?.json_root && !modelSchema?.widget_ui_data_element) {
      return;
    }

    // Check if this model is an abbreviated model (UI_ABBREVIATED_FILTER)
    const widgetUiData = modelSchema?.widget_ui_data_element?.widget_ui_data;
    const isAbbreviatedModel = widgetUiData?.some(
      (uiData) => uiData?.view_layout === 'UI_ABBREVIATED_FILTER'
    );

    if (isAbbreviatedModel) {
      // For abbreviated models: compute and store dataSources array
      const dataSources = getDataSourcesFromSchema(modelSchema);
      abbreviationModelToSourcesMap[modelName] = dataSources;

      // Add all data sources to abbreviation sources set
      if (dataSources.length > 0) {
        dataSources.forEach((source) => {
          abbreviationSourcesSet.add(source);
        });
      }
    }

    // Compute modelDependencyMap for ALL models (both abbreviated and non-abbreviated)
    const dependencyMap = getModelDependencyMap(modelSchema);
    if (dependencyMap) {
      modelToDependencyMap[modelName] = dependencyMap;
    }
  });

  return { abbreviationModelToSourcesMap, modelToDependencyMap, abbreviationSourcesSet };
}

/**
 * Extracts source model name with fallback strategy.
 * Priority: 1) Use direct model name field (query_src_model_name/param_src_model_name)
 *          2) Extract from value source string (query_param_value_src/param_value_src)
 *
 * @param {string} directModelName - Direct field like query_src_model_name or param_src_model_name
 * @param {string} valueSrc - Value source like "model_name.field.path"
 * @returns {string|null} - Extracted model name or null
 */
export function extractSourceModelName(directModelName, valueSrc) {
  if (directModelName) {
    return directModelName;
  }
  if (valueSrc && typeof valueSrc === 'string') {
    return valueSrc.split('.')[0] || null;
  }
  return null;
}

/**
 * Builds a lookup of available models with their storedObj and fieldsMetadata.
 * Filters out models with null/undefined storedObj or name.
 *
 * @param {Array<{name: string, storedObj: object, fieldsMetadata: Array}>} modelConfigs - Array of model configurations
 * @returns {Object} Map of modelName → { storedObj, fieldsMetadata }
 *
 * @example
 * buildAvailableModelsMap([
 *   { name: "abc", storedObj: {...}, fieldsMetadata: [...] },
 *   { name: "def", storedObj: {...}, fieldsMetadata: [...] }
 * ])
 * // Returns: { a : { storedObj: {...}, fieldsMetadata: [...] }, ... }
 */
export function buildAvailableModelsMap(modelConfigs) {
  const models = {};

  if (!Array.isArray(modelConfigs)) {
    return models;
  }

  modelConfigs.forEach(({ name, storedObj, fieldsMetadata }) => {
    // Only add models with valid name and storedObj
    if (name && storedObj) {
      models[name] = { storedObj, fieldsMetadata };
    }
  });

  return models;
}

/**
 * Extracts which models each child dataSource depends on for each dependency type.
 * Checks schema fields with fallback strategy:
 * - urlOverride: connection_dependency[].source_model_name
 * - crudOverride: override_default_crud[].query_src_model_name OR query_param_value_src
 * - defaultFilter: default_filter_param[].param_src_model_name OR param_value_src
 *
 * @param {Array<{name: string, schema: object}>} dataSources - Array of child data source objects
 * @param {Array<string>} availableModelNames - List of valid model names for validation
 * @returns {Object} Map of dataSourceName → { urlOverride?: modelName, crudOverride?: modelName, defaultFilter?: modelName }
 *
 * @example
 */
export function extractChildDataSourceDependencies(dataSources, availableModelNames) {
  const requirements = {};

  if (!Array.isArray(dataSources)) {
    return requirements;
  }

  dataSources.forEach(({ name, schema }) => {
    if (!schema) return;

    const deps = {};

    const connectionDependency = schema.connection_dependency?.[0];

    // Extract urlOverride dependency
    const urlOverrideDep = connectionDependency?.source_model_name;
    if (urlOverrideDep) {
      deps.urlOverride = urlOverrideDep;
    }

    // Extract crudOverride dependency from query_src_model_name or query_param_value_src
    const crudOverrideSrc = schema?.override_default_crud?.find(crud =>
      crud?.query_src_model_name || crud?.ui_query_params?.length > 0
    );
    if (crudOverrideSrc) {
      const firstParam = crudOverrideSrc.ui_query_params?.[0];
      const sourceModelName = extractSourceModelName(
        crudOverrideSrc.query_src_model_name,
        firstParam?.query_param_value_src
      );

      if (sourceModelName && (!availableModelNames || availableModelNames.includes(sourceModelName))) {
        deps.crudOverride = sourceModelName;
      }
    }

    // Extract defaultFilter dependency from param_src_model_name or param_value_src
    const defaultFilterSrc = schema?.default_filter_param?.[0];
    if (defaultFilterSrc?.ui_filter_params && defaultFilterSrc.ui_filter_params.length > 0) {
      // Get the source model name from the first filter param that has param_value_src
      const firstSrcParam = defaultFilterSrc.ui_filter_params.find(p => p.param_value_src);
      const sourceModelName = extractSourceModelName(
        defaultFilterSrc.param_src_model_name,
        firstSrcParam?.param_value_src
      );

      if (sourceModelName && (!availableModelNames || availableModelNames.includes(sourceModelName))) {
        deps.defaultFilter = sourceModelName;
      }
    }

    if (Object.keys(deps).length > 0) {
      requirements[name] = deps;
    }
  });

  return requirements;
}

/**
 * Resolves dependency requirements to actual storedObjs and fieldsMetadata from availableModels map.
 * - urlOverride: Returns { storedObj, fieldsMetadata } (both needed for URL construction)
 * - crudOverride/defaultFilter: Returns { storedObj } only (fieldsMetadata not needed)
 * Logs warnings for unresolved dependencies.
 *
 * @param {Object} dependencyRequirements - Output from extractChildDataSourceDependencies
 * @param {Object} availableModels - Output from buildAvailableModelsMap
 * @returns {Object} Map of dataSourceName → { urlOverride: {storedObj, fieldsMetadata?}, crudOverride: {storedObj}, defaultFilter: {storedObj} }
 */
 
export function resolveDataSourceDependencies(dependencyRequirements, availableModels) {
  const dict = {};

  if (!dependencyRequirements || typeof dependencyRequirements !== 'object') {
    return dict;
  }

  if (!availableModels || typeof availableModels !== 'object') {
    return dict;
  }

  Object.keys(dependencyRequirements).forEach((dataSourceName) => {
    const deps = dependencyRequirements[dataSourceName];
    const resolvedDeps = {};

    Object.keys(deps).forEach((depType) => {
      const requiredModelName = deps[depType];
      const modelData = availableModels[requiredModelName];

      if (modelData) {
        // Only include fieldsMetadata for urlOverride dependency
        if (depType === 'urlOverride') {
          resolvedDeps[depType] = modelData; // Stores { storedObj, fieldsMetadata }
        } else {
          // For crudOverride and defaultFilter, only include storedObj
          resolvedDeps[depType] = { storedObj: modelData.storedObj };
        }
      } else {
        console.warn(
          `Child dataSource "${dataSourceName}" requires ${depType} from model "${requiredModelName}" ` +
          `but it's not available in parent's scope. Available models: ${Object.keys(availableModels).join(', ')}`
        );
      }
    });

    if (Object.keys(resolvedDeps).length > 0) {
      dict[dataSourceName] = resolvedDeps;
    }
  });

  return dict;
}
