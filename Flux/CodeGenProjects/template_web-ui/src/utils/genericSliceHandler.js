/**
 * @fileoverview Generic slice handlers.
 *
 * This file contains common helper functions to register Redux Toolkit async thunks'
 * pending, fulfilled, and rejected cases for CRUD operations, as well as helper functions
 * for synchronous reducers. These handlers are intended to be used by the generic slice
 * factory.
 */

import { cloneDeep, isObject } from 'lodash';
import { DB_ID, MODEL_TYPES, MODES, NEW_ITEM_ID } from '../constants';
import {
  addxpath,
  clearxpath,
  applyGetAllWebsocketUpdate,
  getObjectWithLeastId,
  sortAlertArray
} from '../utils';

/**
 * Handles websocket updates on the stored array.
 *
 * @param {any} payload - The payload from the websocket.
 * @param {Array} storedArray - The current state array.
 * @param {number|null} uiLimit - Optional limit for UI display.
 * @param {boolean} isAlertModel - Flag indicating alert model behavior.
 * @returns {Array} The updated stored array.
 */
function wsUpdateHandler(payload, storedArray, uiLimit = null, isAlertModel = false) {
  let data;
  if (Array.isArray(payload)) {
    data = payload;
  } else if (isObject(payload)) {
    data = Object.values(payload);
  } else {
    console.error(`Invalid payload, expected array or object, received: ${payload}`);
    return storedArray;
  }
  data.forEach((o) => {
    storedArray = applyGetAllWebsocketUpdate(storedArray, o, uiLimit, isAlertModel);
  });
  return storedArray;
}

/**
 * Optimized WebSocket update handler.
 *
 * This function merges incoming WebSocket updates into the stored array.
 * It builds a map of updates (keyed by DB_ID), applies those updates to existing items,
 * and then batches new updates (inserting them at the beginning or end based on uiLimit).
 *
 * @param {Array|Object} payload - The incoming update payload (array or object).
 * @param {Array} storedArray - The current array of stored items.
 * @param {number|null} uiLimit - Optional UI limit. If positive, new items are appended;
 *                                if negative, new items are prepended.
 * @param {boolean} isAlertModel - Indicates if this is an alert model (affects deletion logic).
 * @returns {Array} - The updated array after merging WebSocket updates.
 */
function optimizedWsUpdateHandler(payload, storedArray, uiLimit = null, isAlertModel = false) {
  // Normalize payload to an array.
  let data;
  if (Array.isArray(payload)) {
    data = payload;
  } else if (payload && typeof payload === 'object') {
    data = Object.values(payload);
  } else {
    console.error(`Invalid payload, expected array or object, received: ${payload}`);
    return storedArray;
  }

  // Build a map of updates keyed by DB_ID.
  // For deletion cases (alert dismissed or update with only DB_ID), we store a null.
  const updatesMap = new Map();
  for (const update of data) {
    if ((isAlertModel && update.dismiss) || Object.keys(update).length === 1) {
      updatesMap.set(update[DB_ID], null);
    } else {
      updatesMap.set(update[DB_ID], update);
    }
  }

  // Merge updates with the existing stored array.
  // For each existing item, apply the update if available (or remove if deletion).
  const mergedArray = [];
  for (const item of storedArray) {
    if (updatesMap.has(item[DB_ID])) {
      const update = updatesMap.get(item[DB_ID]);
      if (update !== null) {
        mergedArray.push(update);
      }
      updatesMap.delete(item[DB_ID]);
    } else {
      mergedArray.push(item);
    }
  }

  // Collect new updates that weren't in the stored array.
  const newUpdates = [];
  for (const [id, update] of updatesMap.entries()) {
    if (update !== null) {
      newUpdates.push(update);
    }
  }

  // Merge new updates based on uiLimit.
  // If uiLimit is negative, batch prepend new updates; otherwise, append them.
  let finalArray;
  if (uiLimit !== null && uiLimit < 0) {
    // Prepend new updates in one operation to avoid multiple unshift calls.
    finalArray = newUpdates.concat(mergedArray);
  } else {
    finalArray = mergedArray.concat(newUpdates);
  }

  // If a UI limit is set, trim the final array to the limit.
  if (uiLimit !== null) {
    const limit = Math.abs(uiLimit);
    if (finalArray.length > limit) {
      finalArray = uiLimit >= 0
        ? finalArray.slice(finalArray.length - limit) // For positive uiLimit, keep latest items.
        : finalArray.slice(0, limit);                  // For negative uiLimit, keep from the start.
    }
  }

  // For negative uiLimit in alert mode, apply additional sorting if required.
  if (uiLimit !== null && uiLimit < 0 && isAlertModel) {
    sortAlertArray(finalArray);
  }

  return finalArray;
}

/* Synchronous Reducer Handlers */

/**
 * Sets the state array for the entity.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object containing:
 *   - modelKeys: {Object} Key dictionary for state properties.
 *   - initialState: {Object} The slice's initial state.
 *   - modelType: {string} The model type.
 *   - isAlertModel: {boolean} Flag for alert models.
 */
export function setStoredArrayHandler(state, action, config) {
  const { modelKeys, modelType, initialState, isAbbreviationSource } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[storedArrayKey] = action.payload;
  if (state[objIdKey]) {
    const storedObj = action.payload.find((o) => o[DB_ID] === state[objIdKey]);
    if (!storedObj) {
      // Active entity was deleted; reset to initial state.
      state[objIdKey] = initialState[objIdKey];
      state[storedObjKey] = initialState[storedObjKey];
      state[updatedObjKey] = initialState[updatedObjKey];
    } else {
      state[storedObjKey] = storedObj;
      if (state.mode === MODES.READ) {
        state[updatedObjKey] = addxpath(cloneDeep(storedObj));
      } else {  // mode is MODES.EDIT
        if (modelType === MODEL_TYPES.ABBREVIATION_MERGE) {
          state[updatedObjKey] = addxpath(cloneDeep(storedObj));
        }
        // TODO: handle ws update conflict
      }
    }
  } else {
    if ([MODEL_TYPES.ABBREVIATION_MERGE, MODEL_TYPES.ROOT, MODEL_TYPES.NON_ROOT].includes(modelType) && !isAbbreviationSource) {
      if (action.payload.length > 0) {
        const obj = getObjectWithLeastId(action.payload);
        console.log(obj);
        state[objIdKey] = obj[DB_ID];
        state[storedObjKey] = obj;
        state[updatedObjKey] = addxpath(cloneDeep(obj));
      }
    }
  }
}

/**
 * Handles websocket updates on the state array.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object containing:
 *   - modelKeys: {Object} Key dictionary.
 *   - initialState: {Object} Initial slice state.
 *   - modelType: {string} The model type.
 *   - isAlertModel: {boolean} Flag for alert models.
 */
export function setStoredArrayWsHandler(state, action, config) {
  const { modelKeys, initialState, isAlertModel, modelType } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  // const updatedArray = wsUpdateHandler(action.payload, state[storedArrayKey], null, isAlertModel);
  // Update the stored array with incoming WebSocket updates.
  const updatedArray = optimizedWsUpdateHandler(action.payload, state[storedArrayKey], null, isAlertModel);
  state[storedArrayKey] = updatedArray;
  if (state[objIdKey]) {
    const storedObj = updatedArray.find((o) => o[DB_ID] === state[objIdKey]);
    if (!storedObj) {
      // Active entity was deleted; reset to initial state.
      state[objIdKey] = initialState[objIdKey];
      state[storedObjKey] = initialState[storedObjKey];
      state[updatedObjKey] = initialState[updatedObjKey];
    } else {
      state[storedObjKey] = storedObj;
      if (state.mode === MODES.READ) {
        state[updatedObjKey] = addxpath(cloneDeep(storedObj));
      } else {  // mode is MODES.EDIT
        if (modelType === MODEL_TYPES.ABBREVIATION_MERGE) {
          state[updatedObjKey] = addxpath(cloneDeep(storedObj));
        }
        // TODO: handle ws update conflict
      }
    }
  }
}

/**
 * Sets the entity object in state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object containing modelKeys, initialState, modelType, and isAlertModel.
 */
export function setStoredObjHandler(state, action, config) {
  const { modelKeys, initialState } = config;
  const { storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[storedObjKey] = action.payload;
  if (Object.keys(action.payload).length === 0) {
    state[objIdKey] = initialState[objIdKey];
    state[updatedObjKey] = initialState[updatedObjKey];
  }
}

/**
 * Sets the modified (updated) entity in state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setUpdatedObjHandler(state, action, config) {
  const { modelKeys } = config;
  const { updatedObjKey } = modelKeys;
  state[updatedObjKey] = action.payload;
}

/**
 * Sets the selected entity ID.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setObjIdHandler(state, action, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[objIdKey] = action.payload;
  if (action.payload === null) {
    state[storedObjKey] = initialState[storedObjKey];
    state[updatedObjKey] = initialState[updatedObjKey];
  } else if (action.payload !== NEW_ITEM_ID) {
    const storedObj = state[storedArrayKey].find((o) => o[DB_ID] === action.payload);
    if (storedObj) {
      state[storedObjKey] = storedObj;
      state[updatedObjKey] = addxpath(cloneDeep(storedObj));
    }
  }
}

/**
 * Set the mode field to its default state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setModeHandler(state, action, config) {
  state.mode = action.payload;
}

/**
 * Resets the error field to its default state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setErrorHandler(state, action, config) {
  state.error = action.payload;
}

/**
 * Sets the websocket popup flag.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setIsWsPopupOpenHandler(state, action, config) {
  state.isWsPopupOpen = action.payload;
}

/**
 * Sets the confirm save popup flag.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Object} config - Configuration object.
 */
export function setIsConfirmSavePopupOpenHandler(state, action, config) {
  state.isConfirmSavePopupOpen = action.payload;
}

/* Combined Async Reducer Handlers for CRUD Operations */

/**
 * Registers pending, fulfilled, and rejected cases for a getAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "getAll".
 * @param {Object} config - Configuration object containing modelKeys, initialState, modelType, and isAlertModel.
 */
export function handleGetAll(builder, thunk, config) {
  const { modelKeys, initialState, modelName, isAbbreviationSource } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state[storedArrayKey] = initialState[storedArrayKey];
    state[storedObjKey] = initialState[storedObjKey];
    state[updatedObjKey] = initialState[updatedObjKey];
    state[objIdKey] = initialState[objIdKey];
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    state[storedArrayKey] = action.payload || [];
    if (!action.payload || action.payload.length === 0) {
      // no action required - all state already cleared in pending
    } else if (modelName !== 'ui_layout' && !isAbbreviationSource) {
      const obj = getObjectWithLeastId(action.payload);
      state[objIdKey] = obj[DB_ID];
      state[storedObjKey] = obj;
      state[updatedObjKey] = addxpath(cloneDeep(obj));
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status };
    state.isLoading = false;
  });
}

/**
 * Registers pending, fulfilled, and rejected cases for a get thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "get".
 * @param {Object} config - Configuration object.
 */
export function handleGet(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    state[storedObjKey] = action.payload;
    if (!state[objIdKey]) {
      state[updatedObjKey] = addxpath(cloneDeep(action.payload));
    } else {
      // TODO: handle applying user changes
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status };
    state.isLoading = false;
  });
}

/**
 * Registers pending, fulfilled, and rejected cases for a create thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "create".
 * @param {Object} config - Configuration object.
 */
export function handleCreate(builder, thunk, config) {
  const { modelKeys, initialState, modelName } = config;
  const { storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    if (modelName !== 'ui_layout') {
      state.isLoading = true;
    }
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    state[storedObjKey] = action.payload;
    state[updatedObjKey] = action.payload;
    state[objIdKey] = action.payload[DB_ID];
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedObj = clearxpath(cloneDeep(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(cloneDeep(state[storedObjKey]));
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status, payload: updatedObj };
    state.isLoading = false;
  });
}

/**
 * Registers pending, fulfilled, and rejected cases for an update thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "update".
 * @param {Object} config - Configuration object.
 */
export function handleUpdate(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    state[storedArrayKey] = state[storedArrayKey].map((o) => o[DB_ID] === action.payload[DB_ID] ? action.payload : o);
    if (state[objIdKey] && state[objIdKey] === action.payload[DB_ID]) {
      state[storedObjKey] = action.payload;
      state[updatedObjKey] = addxpath(cloneDeep(action.payload));
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedData = clearxpath(cloneDeep(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(cloneDeep(state[storedObjKey]));
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status, payload: updatedData };
    state.isLoading = false;
  });
}

/**
 * Registers pending, fulfilled, and rejected cases for a partial update thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "partialUpdate".
 * @param {Object} config - Configuration object.
 */
export function handlePartialUpdate(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    state[storedArrayKey] = state[storedArrayKey].map((o) => o[DB_ID] === action.payload[DB_ID] ? action.payload : o);
    if (state[objIdKey] && state[objIdKey] === action.payload[DB_ID]) {
      state[storedObjKey] = action.payload;
      state[updatedObjKey] = addxpath(cloneDeep(action.payload));
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedData = clearxpath(cloneDeep(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(cloneDeep(state[storedObjKey]));
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status, payload: updatedData };
    state.isLoading = false;
  });
}
