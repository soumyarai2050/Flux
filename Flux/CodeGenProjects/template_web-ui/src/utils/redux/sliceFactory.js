/**
 * @fileoverview Generic slice factory.
 *
 * This file defines a factory function to create Redux slices with common CRUD functionality.
 * The generated slice includes async thunks for getAll, get, create, update, and partialUpdate operations,
 * as well as synchronous reducers that delegate to handler functions in genericSliceHandler.js.
 * Additional reducer functions can be injected via the injectedReducers configuration option.
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { camelCase } from 'lodash';
import { API_ROOT_URL, API_ROOT_VIEW_URL, MODES } from '../../constants';
import { snakeToPascal } from '../core/stringUtils';
import { getErrorDetails } from '../core/errorUtils';
import { getApiUrlMetadata } from '../network/networkUtils';
import {
  setStoredArrayHandler,
  setStoredObjHandler,
  setUpdatedObjHandler,
  setObjIdHandler,
  setModeHandler,
  setIsCreatingHandler,
  setErrorHandler,
  setPopupStatusHandler,
  handleGetAll,
  handleGet,
  handleCreate,
  handleUpdate,
  handlePartialUpdate,
  handleCreateAll,
  handleUpdateAll,
  handlePatchAll,
  handleDelete,
  handleDeleteAll,
} from './sliceHandlers';

/**
 * Helper function to check if an operation is allowed based on json_root configuration.
 *
 * @param {Object|null} allowedOperations - The json_root object from schema defining allowed operations.
 * @param {string} operationKey - The operation key to check (e.g., 'CreateOp', 'UpdateOp', 'PatchOp').
 * @param {string} modelName - The model name for error messaging.
 * @returns {true|Object} - Returns true if operation is allowed, error object if not allowed.
 */
function checkOperationAllowed(allowedOperations, operationKey, modelName) {
  // Allow if operation key exists and has a value
  if (allowedOperations && allowedOperations.hasOwnProperty(operationKey) && allowedOperations[operationKey] === true) {
    return true; // ALLOWED
  }

  // Block if key is missing or has no value - return error object
  const operationName = operationKey.replace('Op', '').replace('All', ' All');
  return {
    code: 'OPERATION_NOT_ALLOWED',
    message: `${operationName} operation is not allowed for ${modelName}`,
    detail: `The operation key is missing or has no value in json_root configuration`,
    status: 403
  };
}

/**
 * Factory function to create a generic Redux slice.
 *
 * @param {Object} config - Configuration object.
 * @param {string} config.modelName - The name of the entity (e.g., 'window').
 * @param {Object} [config.extraState] - Additional state properties to include.
 * @param {string|null} [config.modelType] - Optional model type.
 * @param {boolean} [config.isAlertModel] - Optional flag for alert types.
 * @param {Object} [config.injectedReducers] - Additional reducer functions to inject.
 *        Each key should be a reducer name and its value a function with signature (state, action).
 * @param {boolean} [config.isAbbreviationSource] - Optional flag indicating if the model is an abbreviation source.
 * @param {Object|null} [config.allowedOperations] - Optional object defining allowed CRUD operations from json_root.
 * @returns {Object} An object containing the slice reducer and actions.
 */
export function createGenericSlice({
  modelName,
  extraState = {},
  modelType,
  isAlertModel = false,
  injectedReducers = {},
  isAbbreviationSource = false,
  allowedOperations = null,
  isIdDependent = false
}) {
  // Dynamically construct keys for state properties based on modelName.
  const endpointBase = modelName;
  const reducerName = camelCase(modelName);
  const capModelName = snakeToPascal(modelName);

  const storedArrayKey = `stored${capModelName}Array`;
  const storedObjKey = `stored${capModelName}Obj`;
  const updatedObjKey = `updated${capModelName}Obj`;
  const objIdKey = `selected${capModelName}Id`;

  const modelKeys = {
    storedArrayKey,
    storedObjKey,
    updatedObjKey,
    objIdKey,
  };

  // Define the initial state for the Redux slice.
  const initialState = {
    [storedArrayKey]: [],
    [storedObjKey]: {},
    [updatedObjKey]: {},
    [objIdKey]: null,
    mode: MODES.READ,
    allowUpdates: true,
    isCreating: false,
    error: null,
    isLoading: false,
    popupStatus: {
      confirmSave: false,
      formValidation: false,
      wsConflict: false,
    },
    ...extraState, // Merge any additional state properties provided.
  };

  // Consolidate constants into a single config object.
  const sliceConfig = {
    modelName,
    modelKeys,
    modelType,
    isAlertModel,
    initialState,
    isAbbreviationSource,
    isIdDependent
  };

  /* Async Thunks for CRUD Operations */

  /**
   * @function getAllThunk
   * @description Fetches all entities of the model from the API.
   * @param {object} [payload] - Optional payload for the request.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {number} [payload.uiLimit] - UI limit for the number of items.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<Array<object>>} A promise that resolves with an array of entities.
   */
  const getAllThunk = createAsyncThunk(`${capModelName}/getAll`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'ReadAllOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `get-all-${endpointBase}`;
    let apiUrl, apiParams;
    // Determine API URL and parameters based on payload or defaults.
    if (payload) {
      const { url, endpoint, uiLimit, params } = payload;
      [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params, true, uiLimit);
    } else {
      apiUrl = `${API_ROOT_VIEW_URL}/${defaultEndpoint}`;
      apiParams = {};
    }
    try {
      const res = await axios.get(apiUrl, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function getThunk
   * @description Fetches a single entity of the model by ID from the API.
   * @param {object} payload - Payload for the request.
   * @param {string} payload.id - The ID of the entity to fetch.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the fetched entity.
   */
  const getThunk = createAsyncThunk(`${capModelName}/get`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'ReadOp', modelName);
    //use !==true cuz in case of false we receive an error object
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `get-${endpointBase}`;
    const { url, endpoint, params, id } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params, true);
    try {
      const res = await axios.get(`${apiUrl}/${id}`, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function createThunk
   * @description Creates a new entity of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {object} payload.data - The data for the new entity.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the created entity.
   */
  const createThunk = createAsyncThunk(`${capModelName}/create`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'CreateOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `create-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.post(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function updateThunk
   * @description Updates an existing entity of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {object} payload.data - The data to update the entity with.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the updated entity.
   */
  const updateThunk = createAsyncThunk(`${capModelName}/update`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'UpdateOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `put-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.put(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function partialUpdateThunk
   * @description Partially updates an existing entity of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {object} payload.data - The partial data to update the entity with.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the partially updated entity.
   */
  const partialUpdateThunk = createAsyncThunk(`${capModelName}/partialUpdate`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'PatchOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `patch-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.patch(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function createAllThunk
   * @description Creates multiple entities of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {Array<object>} payload.data - The array of data for the new entities.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<Array<object>>} A promise that resolves with the created entities.
   */
  const createAllThunk = createAsyncThunk(`${capModelName}/createAll`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'CreateAllOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `create-all-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.post(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function updateAllThunk
   * @description Updates multiple entities of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {Array<object>} payload.data - The array of data to update entities with.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<Array<object>>} A promise that resolves with the updated entities.
   */
  const updateAllThunk = createAsyncThunk(`${capModelName}/updateAll`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'UpdateAllOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `put-all-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.put(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function patchAllThunk
   * @description Partially updates multiple entities of the model via the API.
   * @param {object} payload - Payload for the request.
   * @param {Array<object>} payload.data - The array of partial data to update entities with.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<Array<object>>} A promise that resolves with the partially updated entities.
   */
  const patchAllThunk = createAsyncThunk(`${capModelName}/patchAll`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'PatchAllOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `patch-all-${endpointBase}`;
    const { url, endpoint, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.patch(apiUrl, data, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function deleteThunk
   * @description Deletes a single entity of the model by ID via the API.
   * @param {object} payload - Payload for the request.
   * @param {string|number} payload.id - The ID of the entity to delete.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the deletion response.
   */
  const deleteThunk = createAsyncThunk(`${capModelName}/delete`, async (payload, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'DeleteOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `delete-${endpointBase}`;
    const { url, endpoint, params, id } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.delete(`${apiUrl}/${id}`, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /**
   * @function deleteAllThunk
   * @description Deletes all entities of the model via the API.
   * @param {object} [payload] - Optional payload for the request.
   * @param {string} [payload.url] - Base URL for the API call.
   * @param {string} [payload.endpoint] - Specific API endpoint to use.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the deletion response.
   */
  const deleteAllThunk = createAsyncThunk(`${capModelName}/deleteAll`, async (payload = {}, { rejectWithValue }) => {
    // Check if operation is allowed
    const isAllowed = checkOperationAllowed(allowedOperations, 'DeleteAllOp', modelName);
    if (isAllowed !== true) {
      return rejectWithValue(isAllowed);
    }

    const defaultEndpoint = `delete-all-${endpointBase}`;
    const { url, endpoint, params } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, params);
    try {
      const res = await axios.delete(apiUrl, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  /* Create the Redux slice with default reducers and any injected reducers. */
  const slice = createSlice({
    name: reducerName,
    initialState,
    reducers: {
      setStoredArray(state, action) {
        setStoredArrayHandler(state, action, sliceConfig);
      },
      setStoredObj(state, action) {
        setStoredObjHandler(state, action, sliceConfig);
      },
      setUpdatedObj(state, action) {
        setUpdatedObjHandler(state, action, sliceConfig);
      },
      setObjId(state, action) {
        setObjIdHandler(state, action, sliceConfig);
      },
      setMode(state, action) {
        setModeHandler(state, action, sliceConfig);
      },
      setAllowUpdates(state, action) {
        state.allowUpdates = action.payload;
      },
      setIsCreating(state, action) {
        setIsCreatingHandler(state, action, sliceConfig);
      },
      setError(state, action) {
        setErrorHandler(state, action, sliceConfig);
      },
      setPopupStatus(state, action) {
        setPopupStatusHandler(state, action, sliceConfig);
      },
      // Merge in additional reducers injected by the caller.
      ...injectedReducers,
    },
    extraReducers: (builder) => {
      // Register CRUD handlers using the combined functions.
      handleGetAll(builder, getAllThunk, sliceConfig);
      handleGet(builder, getThunk, sliceConfig);
      handleCreate(builder, createThunk, sliceConfig);
      handleUpdate(builder, updateThunk, sliceConfig);
      handlePartialUpdate(builder, partialUpdateThunk, sliceConfig);
      handleCreateAll(builder, createAllThunk, sliceConfig);
      handleUpdateAll(builder, updateAllThunk, sliceConfig);
      handlePatchAll(builder, patchAllThunk, sliceConfig);
      handleDelete(builder, deleteThunk, sliceConfig);
      handleDeleteAll(builder, deleteAllThunk, sliceConfig);
    },
  });

  return {
    reducer: slice.reducer,
    actions: {
      getAll: getAllThunk,
      get: getThunk,
      create: createThunk,
      update: updateThunk,
      partialUpdate: partialUpdateThunk,
      createAll: createAllThunk,
      updateAll: updateAllThunk,
      patchAll: patchAllThunk,
      delete: deleteThunk,
      deleteAll: deleteAllThunk,
      ...slice.actions,
    },
  };
}

export default createGenericSlice;
