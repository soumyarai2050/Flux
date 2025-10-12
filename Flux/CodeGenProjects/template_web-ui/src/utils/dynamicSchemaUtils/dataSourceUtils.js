
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
 * Returns an object with optional keys (urlOverride, crudOverride, defaultFilter)
 * where each value is a dataSource name.
 * Only applicable for non-abbreviated models (Root/NonRoot/RepeatedRoot).
 *
 * @param {object} modelSchema - The schema for a specific model
 * @returns {object|null} - Map of dependency configurations or null
 */
export function getModelDependencyMap(modelSchema) {
  if (!modelSchema) {
    return null;
  }

  // Check if this is an abbreviated model
  const widgetUiData = modelSchema?.widget_ui_data_element?.widget_ui_data;
  const isAbbreviatedModel = widgetUiData?.some(
    (uiData) => uiData?.view_layout === 'UI_ABBREVIATED_FILTER'
  );

  // ModelDependencyMap only applies to non-abbreviated models
  if (isAbbreviatedModel) {
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

  // Return null if no dependencies found, otherwise return the map
  return Object.keys(dependencyMap).length > 0 ? dependencyMap : null;
}


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
    } else {
      // For non-abbreviated models: compute modelDependencyMap
      const dependencyMap = getModelDependencyMap(modelSchema);
      if (dependencyMap) {
        modelToDependencyMap[modelName] = dependencyMap;
      }
    }
  });

  return { abbreviationModelToSourcesMap, modelToDependencyMap, abbreviationSourcesSet };
}
