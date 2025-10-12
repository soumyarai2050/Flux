/**
 * @file layoutUtils.js
 * @description Utility functions for generating dynamic layouts from schema
 */

/**
 * Generates dynamic layouts from runtime schema for models not in static layouts
 * @param {Object} schemaFromStore - Optional schema object from Redux store
 * @param {Array} staticLayouts - Array of static layout configurations to exclude
 * @returns {Array} Array of dynamic layout objects
 */
export const addDynamicLayouts = (schemaFromStore = null, staticLayouts = []) => {
  let schema = {};

  if (schemaFromStore) {
    // Use schema passed from React component
    schema = schemaFromStore?.schema || {};
  } else if (typeof window !== 'undefined' && window.store) {
    // Fallback to window.store if available
    const state = window.store.getState();
    schema = state.schema?.schema || {};
  } else {
    return [];
  }

  try {
    const dynamicLayouts = [];
    if (Object.keys(schema).length === 0) {
      return dynamicLayouts; // Return empty array if schema not loaded
    }

    Object.keys(schema).forEach(modelName => {

      // Skip "definitions" - it's a JSON Schema metadata container, not a widget
      if (modelName === 'definitions') {
        return;
      }

      // Skip if already in static layouts
      if (!staticLayouts.find(l => l.i === modelName)) {
        const model = schema[modelName];
        const widgetData = model?.widget_ui_data_element;

        // Include ANY model that has widget_ui_data_element
        // This covers ROOT, REPEATED_ROOT, CHART, and NON_ROOT models
        if (widgetData) {
          dynamicLayouts.push({
            i: modelName,
            x: widgetData?.x || 0,
            y: widgetData?.y || 0,
            w: widgetData?.w || 4,
            h: widgetData?.h || 6,
            widget_ui_data: widgetData?.widget_ui_data || [{ "view_layout": "UI_TABLE" }],
            ...widgetData // Include any other properties from schema
          });
        }
      }
    });

    return dynamicLayouts;
  } catch (error) {
    console.error('Error generating dynamic layouts:', error);
    return [];
  }
};

/**
 * Combines static and dynamic layouts at runtime
 * @param {Array} staticLayouts - Array of static layout configurations
 * @param {Object} schemaFromStore - Optional schema object from Redux store
 * @returns {Array} Combined array of all layout objects
 */
export const getAllLayouts = (staticLayouts, schemaFromStore = null) => {
  const dynamicLayouts = addDynamicLayouts(schemaFromStore, staticLayouts);
  return [...staticLayouts, ...dynamicLayouts];
};