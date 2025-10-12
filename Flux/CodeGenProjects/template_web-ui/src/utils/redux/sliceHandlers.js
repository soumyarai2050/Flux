/**
 * @fileoverview Generic slice handlers.
 *
 * This file contains common helper functions to register Redux Toolkit async thunks'
 * pending, fulfilled, and rejected cases for CRUD operations, as well as helper functions
 * for synchronous reducers. These handlers are intended to be used by the generic slice
 * factory.
 */

import { DB_ID, MODEL_TYPES, MODES, NEW_ITEM_ID } from '../../constants';
import { addxpath, clearxpath, getObjectWithLeastId } from '../core/dataAccess';
import { fastClone } from '../core/dataUtils';

/* Synchronous Reducer Handlers */

/**
 * Sets the state array for the entity.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {Array<object>} action.payload - The array of stored objects.
 * @param {Object} config - Configuration object containing:
 *   - {Object} modelKeys - Key dictionary for state properties.
 *   - {string} modelName - The name of the model.
 *   - {string} modelType - The model type.
 *   - {Object} initialState - The slice's initial state.
 *   - {boolean} isAbbreviationSource - Flag for abbreviation source models.
 */
export function setStoredArrayHandler(state, action, config) {
  const { modelKeys, modelName, modelType, initialState, isAbbreviationSource } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[storedArrayKey] = action.payload;
  // if (modelName === 'ui_layout') return;
  if ([MODEL_TYPES.ROOT, MODEL_TYPES.NON_ROOT].includes(modelType) && state[objIdKey] && state[objIdKey] !== NEW_ITEM_ID && !action.payload.find((o) => o[DB_ID] === state[objIdKey])) {
    state[objIdKey] = null;
  }
  if (state[objIdKey] && state[objIdKey] !== NEW_ITEM_ID) {
    const storedObj = action.payload.find((o) => o[DB_ID] === state[objIdKey]);
    if (!storedObj) {
      // Active entity was deleted; reset to initial state.
      state[objIdKey] = initialState[objIdKey];
      state[storedObjKey] = initialState[storedObjKey];
      state[updatedObjKey] = initialState[updatedObjKey];
    } else {
      if (state.mode === MODES.READ && state.allowUpdates) {
        state[storedObjKey] = storedObj;
        state[updatedObjKey] = addxpath(fastClone(storedObj));
      } else {
        state[storedObjKey] = storedObj;
        // NOTE: We intentionally do NOT update updatedObj in edit mode to preserve user changes
        // The conflict detection in RootModel will handle cases where the object was deleted
      }
    }
  } else {
    if (modelName === 'ui_layout') return;
    if ([MODEL_TYPES.ABBREVIATION_MERGE, MODEL_TYPES.ROOT, MODEL_TYPES.NON_ROOT].includes(modelType) && !isAbbreviationSource) {
      if (action.payload.length > 0) {
        const obj = getObjectWithLeastId(action.payload);
        state[objIdKey] = obj[DB_ID];
        state[storedObjKey] = obj;
        state[updatedObjKey] = addxpath(fastClone(obj));
      }
    }
  }
}

/**
 * Sets the entity object in state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {object} action.payload - The stored object.
 * @param {Object} config - Configuration object containing:
 *   - {Object} modelKeys - Key dictionary for state properties.
 *   - {Object} initialState - The slice's initial state.
 */
export function setStoredObjHandler(state, action, config) {
  const { modelKeys, initialState } = config;
  const { storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[storedObjKey] = action.payload;
  // If the payload is an empty object, reset the selected object ID and updated object.
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
 * @param {object} action.payload - The updated object.
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
 * @param {string|number|null} action.payload - The ID of the selected object.
 * @param {Object} config - Configuration object containing:
 *   - {Object} modelKeys - Key dictionary for state properties.
 *   - {Object} initialState - The slice's initial state.
 */
export function setObjIdHandler(state, action, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  state[objIdKey] = action.payload;
  // If the payload is null, reset stored and updated objects to their initial states.
  if (action.payload === null) {
    state[storedObjKey] = initialState[storedObjKey];
    state[updatedObjKey] = initialState[updatedObjKey];
  } else if (action.payload !== NEW_ITEM_ID) {
    // If the payload is a valid ID (not NEW_ITEM_ID), find the corresponding object in the stored array.
    const storedObj = state[storedArrayKey].find((o) => o[DB_ID] === action.payload);
    if (storedObj) {
      // If found, set the stored object and update the updated object with its xpath.
      state[storedObjKey] = storedObj;
      state[updatedObjKey] = addxpath(fastClone(storedObj));
    }
  }
}

/**
 * Set the mode field to its default state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {string} action.payload - The mode to set (e.g., MODES.READ, MODES.EDIT).
 * @param {Object} config - Configuration object.
 */
export function setModeHandler(state, action, config) {
  state.mode = action.payload;
}

/**
 * Set the isCreating field to its default state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {boolean} action.payload - The boolean value for isCreating.
 * @param {Object} config - Configuration object.
 */
export function setIsCreatingHandler(state, action, config) {
  state.isCreating = action.payload;
}


/**
 * Resets the error field to its default state.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {object|null} action.payload - The error object or null.
 * @param {Object} config - Configuration object.
 */
export function setErrorHandler(state, action, config) {
  state.error = action.payload;
}

/**
 * Sets the confirm save popup flag.
 *
 * @param {Object} state - Redux state.
 * @param {Object} action - Redux action.
 * @param {object} action.payload - An object containing popup status flags (e.g., { confirmSave: true }).
 * @param {Object} config - Configuration object.
 */
export function setPopupStatusHandler(state, action, config) {
  state.popupStatus = { ...state.popupStatus, ...action.payload };
}

/* Combined Async Reducer Handlers for CRUD Operations */

/**
 * Registers pending, fulfilled, and rejected cases for a getAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "getAll".
 * @param {Object} config - Configuration object containing:
 *   - {Object} modelKeys - Key dictionary for state properties.
 *   - {Object} initialState - The slice's initial state.
 *   - {string} modelName - The name of the model.
 *   - {boolean} isAbbreviationSource - Flag for abbreviation source models.
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
      state[updatedObjKey] = addxpath(fastClone(obj));
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
      state[updatedObjKey] = addxpath(fastClone(action.payload));
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
  const { modelKeys, initialState, modelName, isAbbreviationSource } = config;
  const { storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    if (modelName !== 'ui_layout') {
      state.isLoading = true;
    }
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    if (!Array.isArray(action.payload)) {
      state[storedObjKey] = action.payload;
      state[updatedObjKey] = action.payload;
      if (!isAbbreviationSource) {
        state[objIdKey] = action.payload[DB_ID];
      }
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedObj = clearxpath(fastClone(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(fastClone(state[storedObjKey]));
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
      state[updatedObjKey] = addxpath(fastClone(action.payload));
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedData = clearxpath(fastClone(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(fastClone(state[storedObjKey]));
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
      state[updatedObjKey] = addxpath(fastClone(action.payload));
    }
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const updatedData = clearxpath(fastClone(state[updatedObjKey]));
    state[updatedObjKey] = addxpath(fastClone(state[storedObjKey]));
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status, payload: updatedData };
    state.isLoading = false;
  });
}

/**
 * Registers pending, fulfilled, and rejected cases for a createAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "createAll".
 * @param {Object} config - Configuration object.
 */
export function handleCreateAll(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    if (Array.isArray(action.payload)) {
      // Append newly created items to the stored array
      state[storedArrayKey] = [...state[storedArrayKey], ...action.payload];
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
 * Registers pending, fulfilled, and rejected cases for an updateAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "updateAll".
 * @param {Object} config - Configuration object.
 */
export function handleUpdateAll(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    if (Array.isArray(action.payload)) {
      // Create a map of updated items by ID for efficient lookup
      const updatedMap = new Map(action.payload.map((item) => [item[DB_ID], item]));
      // Update the stored array by replacing items with matching IDs
      state[storedArrayKey] = state[storedArrayKey].map((o) =>
        updatedMap.has(o[DB_ID]) ? updatedMap.get(o[DB_ID]) : o
      );
      // If the currently selected object was updated, refresh it
      if (state[objIdKey] && updatedMap.has(state[objIdKey])) {
        const updatedObj = updatedMap.get(state[objIdKey]);
        state[storedObjKey] = updatedObj;
        state[updatedObjKey] = addxpath(fastClone(updatedObj));
      }
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
 * Registers pending, fulfilled, and rejected cases for a patchAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "patchAll".
 * @param {Object} config - Configuration object.
 */
export function handlePatchAll(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    if (Array.isArray(action.payload)) {
      // Create a map of patched items by ID for efficient lookup
      const patchedMap = new Map(action.payload.map((item) => [item[DB_ID], item]));
      // Update the stored array by replacing items with matching IDs
      state[storedArrayKey] = state[storedArrayKey].map((o) =>
        patchedMap.has(o[DB_ID]) ? patchedMap.get(o[DB_ID]) : o
      );
      // If the currently selected object was patched, refresh it
      if (state[objIdKey] && patchedMap.has(state[objIdKey])) {
        const patchedObj = patchedMap.get(state[objIdKey]);
        state[storedObjKey] = patchedObj;
        state[updatedObjKey] = addxpath(fastClone(patchedObj));
      }
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
 * Registers pending, fulfilled, and rejected cases for a delete thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "delete".
 * @param {Object} config - Configuration object.
 */
export function handleDelete(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    // action.meta.arg contains the original payload (with id)
    const deletedId = action.meta?.arg?.id;
    if (deletedId !== undefined) {
      // Remove the deleted item from the stored array
      state[storedArrayKey] = state[storedArrayKey].filter((o) => o[DB_ID] !== deletedId);
      // If the deleted item was selected, reset the selection
      if (state[objIdKey] === deletedId) {
        state[objIdKey] = initialState[objIdKey];
        state[storedObjKey] = initialState[storedObjKey];
        state[updatedObjKey] = initialState[updatedObjKey];
      }
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
 * Registers pending, fulfilled, and rejected cases for a deleteAll thunk.
 *
 * @param {Object} builder - Redux Toolkit builder.
 * @param {Object} thunk - The async thunk for "deleteAll".
 * @param {Object} config - Configuration object.
 */
export function handleDeleteAll(builder, thunk, config) {
  const { modelKeys, initialState } = config;
  const { storedArrayKey, storedObjKey, updatedObjKey, objIdKey } = modelKeys;
  builder.addCase(thunk.pending, (state) => {
    state.isLoading = true;
    state.error = null;
  });
  builder.addCase(thunk.fulfilled, (state, action) => {
    // Clear all items from the stored array
    state[storedArrayKey] = initialState[storedArrayKey];
    state[storedObjKey] = initialState[storedObjKey];
    state[updatedObjKey] = initialState[updatedObjKey];
    state[objIdKey] = initialState[objIdKey];
    state.isLoading = false;
  });
  builder.addCase(thunk.rejected, (state, action) => {
    const { code, message, detail, status } = action.payload || {};
    state.error = { code, message, detail, status };
    state.isLoading = false;
  });
}
