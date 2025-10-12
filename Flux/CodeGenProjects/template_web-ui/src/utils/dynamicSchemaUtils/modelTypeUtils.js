/**
 * @file modelTypeUtils.js
 * @description Utility functions for determining model types from schema data
 */

import { MODEL_TYPES } from "../../constants";

/**
 * Determines the model type based on schema properties
 * @param {Object} modelSchema - The schema object for a specific model
 * @returns {string} The determined model type
 */
export function getModelTypeFromSchema(modelSchema) {
  if (!modelSchema) {
    return MODEL_TYPES.ROOT; // Safe default
  }

  // Rule 1: Chart Model (most specific)
  if (modelSchema?.widget_ui_data_element?.model_type === 'CHART') {
    return MODEL_TYPES.CHART;
  }

  // Rule 2: Repeated Root Model
  if (modelSchema?.widget_ui_data_element?.is_repeated === true) {
    return MODEL_TYPES.REPEATED_ROOT;
  }

  // Rule 3: Abbreviation Model (placeholder for now)
  if (modelSchema?.widget_ui_data_element?.widget_ui_data?.[0]?.view_layout === 'UI_ABBREVIATED_FILTER') {
    return MODEL_TYPES.ABBREVIATION_MERGE;
  }

  // Rule 4: Non ROot model , it has widget ui data element and without json root property
  if (modelSchema?.widget_ui_data_element && !modelSchema?.json_root) {
    return MODEL_TYPES.NONROOT;
  }

  // If it's not a recognized widget model at all, return a safe default
  return MODEL_TYPES.ROOT;
}

/**
 * Extracts slice configuration from schema
 * @param {Object} modelSchema - The schema object for a specific model
 * @param {string} modelName - The name of the model (needed for abbreviation source lookup)
 * @returns {Object} Configuration object with isAlertModel, isAbbreviationSource, extraState, and injectedReducers
 */
export function getSliceConfig(modelSchema, modelName) {
  const sliceConfig = {};

  // Check if this is an alert model
  if (modelSchema?.widget_ui_data_element?.is_model_alert_type === true) {
    sliceConfig.isAlertModel = true;
  }

  // Check if this is an abbreviation source (deduced property)
  // A model is an abbreviation source if it's used as a data source by any abbreviated model
  // This is a deduced property computed during schema load and stored in Redux as an array
  if (typeof window !== 'undefined' && window.store && modelName) {
    const state = window.store.getState();
    const abbreviationSourcesSet = state.schema?.abbreviationSourcesSet;

    if (Array.isArray(abbreviationSourcesSet) && abbreviationSourcesSet.includes(modelName)) {
      sliceConfig.isAbbreviationSource = true;
    }
  }

  // Check for graph node model
  if (modelSchema?.widget_ui_data_element?.is_graph_node_model === true) {
    sliceConfig.extraState = {
      node: null,
      selectedDataPoints: [],
      lastSelectedDataPoint: null,
      isAnalysis: false
    };
    sliceConfig.injectedReducers = {
      setNode(state, action) {
        state.node = action.payload;
      },
      setSelectedDataPoints(state, action) {
        state.selectedDataPoints = action.payload;
      },
      setLastSelectedDataPoint(state, action) {
        state.lastSelectedDataPoint = action.payload;
      },
      setIsAnalysis(state, action) {
        state.isAnalysis = action.payload;
      }
    };
  }
  // Check for graph model
  else if (modelSchema?.widget_ui_data_element?.is_graph_model === true) {
    sliceConfig.extraState = {
      contextId: null
    };
    sliceConfig.injectedReducers = {
      setContextId(state, action) {
        state.contextId = action.payload;
      }
    };
  }
  // Default: no extraState or injectedReducers (will be undefined)

  return sliceConfig;
}