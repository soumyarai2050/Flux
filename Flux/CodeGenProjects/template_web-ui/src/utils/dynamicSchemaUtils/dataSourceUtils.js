
export function getDataSourcesFromSchema(modelSchema) {
  if (!modelSchema) {
    return [];
  }

  const dataSourcesSet = new Set();

  // Rule 1: Check for depending_proto_model_name (non-abbreviated models)
  const dependingModelName = modelSchema?.widget_ui_data_element?.depending_proto_model_name;
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
  const defaultFilter = modelSchema?.default_filter_param;
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

  // Extract urlOverride (from depending_proto_model_name)
  const dependingModelName = modelSchema?.widget_ui_data_element?.depending_proto_model_name;
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
  const defaultFilter = modelSchema?.default_filter_param;
  if (defaultFilter && typeof defaultFilter === 'object' && defaultFilter?.param_src_model_name) {
    dependencyMap.defaultFilter = defaultFilter.param_src_model_name;
  }

  // Extract idDependent (from depending_proto_model_name_for_id)
  const idDependentModelName = modelSchema?.depending_proto_model_name_for_id;
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
