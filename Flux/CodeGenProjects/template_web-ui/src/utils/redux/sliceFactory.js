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
} from './sliceHandlers';


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
 * @returns {Object} An object containing the slice reducer and actions.
 */
export function createGenericSlice({
  modelName,
  extraState = {},
  modelType,
  isAlertModel = false,
  injectedReducers = {},
  isAbbreviationSource = false
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
    isAbbreviationSource
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
    const defaultEndpoint = `get-all-${endpointBase}`;
    let apiUrl, apiParams;
    // Determine API URL and parameters based on payload or defaults.
    if (payload) {
      const { url, endpoint, uiLimit, params } = payload;
      [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params, true);
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
   * @param {number} [payload.uiLimit] - UI limit for the number of items.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the fetched entity.
   */
  const getThunk = createAsyncThunk(`${capModelName}/get`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `get-${endpointBase}`;
    const { url, endpoint, uiLimit, params, id } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params, true);
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
   * @param {number} [payload.uiLimit] - UI limit for the number of items.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the created entity.
   */
  const createThunk = createAsyncThunk(`${capModelName}/create`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `create-${endpointBase}`;
    const { url, endpoint, uiLimit, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
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
   * @param {number} [payload.uiLimit] - UI limit for the number of items.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the updated entity.
   */
  const updateThunk = createAsyncThunk(`${capModelName}/update`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `put-${endpointBase}`;
    const { url, endpoint, uiLimit, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
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
   * @param {number} [payload.uiLimit] - UI limit for the number of items.
   * @param {object} [payload.params] - Query parameters for the API call.
   * @returns {Promise<object>} A promise that resolves with the partially updated entity.
   */
  const partialUpdateThunk = createAsyncThunk(`${capModelName}/partialUpdate`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `patch-${endpointBase}`;
    const { url, endpoint, uiLimit, params, data } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
    try {
      const res = await axios.patch(apiUrl, data, { params: apiParams });
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
      ...slice.actions,
    },
  };
}

export default createGenericSlice;
