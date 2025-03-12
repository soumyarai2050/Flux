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
import { API_ROOT_URL, MODES } from '../constants';
import { getApiUrlMetadata, snakeToPascal, getErrorDetails } from '../utils';
import {
  setStoredArrayHandler,
  setStoredArrayWsHandler,
  setStoredObjHandler,
  setUpdatedObjHandler,
  setObjIdHandler,
  setModeHandler,
  setErrorHandler,
  setIsConfirmSavePopupOpenHandler,
  setIsWsPopupOpenHandler,
  handleGetAll,
  handleGet,
  handleCreate,
  handleUpdate,
  handlePartialUpdate,
} from './genericSliceHandler';


/**
 * Factory function to create a generic Redux slice.
 *
 * @param {Object} config - Configuration object.
 * @param {string} config.modelName - The name of the entity (e.g., 'window').
 * @param {string} config.endpointBase - The API endpoint base (e.g., 'window').
 * @param {Object} [config.extraState] - Additional state properties to include.
 * @param {string|null} [config.modelType] - Optional model type.
 * @param {boolean} [config.isAlertModel] - Optional flag for alert types.
 * @param {Object} [config.injectedReducers] - Additional reducer functions to inject.
 *        Each key should be a reducer name and its value a function with signature (state, action).
 * @returns {Object} An object containing the slice reducer and actions.
 */
export function createGenericSlice({
  modelName,
  extraState = {},
  modelType,
  isAlertModel = false,
  injectedReducers = {},
}) {
  // Dynamically construct keys for state properties.
  const endpointBase = modelName;
  const reducerName = camelCase(modelName);
  const capModelName = snakeToPascal(modelName);

  const storedArrayKey = `stored${capModelName}Array`;
  const storedObjDictKey = `stored${capModelName}ObjDict`;
  const storedObjKey = `stored${capModelName}Obj`;
  const updatedObjKey = `updated${capModelName}Obj`;
  const objIdKey = `selected${capModelName}Id`;

  const modelKeys = {
    storedArrayKey,
    storedObjDictKey,
    storedObjKey,
    updatedObjKey,
    objIdKey,
  };

  // Define the initial state.
  const initialState = {
    [storedArrayKey]: [],
    [storedObjDictKey]: {},
    [storedObjKey]: {},
    [updatedObjKey]: {},
    [objIdKey]: null,
    mode: MODES.READ,
    error: null,
    isLoading: false,
    isConfirmSavePopupOpen: false,
    isWsPopupOpen: false,
    ...extraState,
  };

  // Consolidate constants into a single config object.
  const sliceConfig = {
    modelName,
    modelKeys,
    modelType,
    isAlertModel,
    initialState
  };

  /* Async Thunks for CRUD Operations */

  const getAllThunk = createAsyncThunk(`${capModelName}/getAll`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `get-all-${endpointBase}`;
    let apiUrl, apiParams;
    if (payload) {
      const { url, endpoint, uiLimit, params } = payload;
      [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
    } else {
      apiUrl = `${API_ROOT_URL}/${defaultEndpoint}`;
      apiParams = {};
    }
    try {
      const res = await axios.get(apiUrl, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

  const getThunk = createAsyncThunk(`${capModelName}/get`, async (payload, { rejectWithValue }) => {
    const defaultEndpoint = `get-${endpointBase}`;
    const { url, endpoint, uiLimit, params, id } = payload;
    const [apiUrl, apiParams] = getApiUrlMetadata(defaultEndpoint, url, endpoint, uiLimit, params);
    try {
      const res = await axios.get(`${apiUrl}/${id}`, { params: apiParams });
      return res.data;
    } catch (err) {
      return rejectWithValue(getErrorDetails(err));
    }
  });

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
      setStoredArrayWs(state, action) {
        setStoredArrayWsHandler(state, action, sliceConfig);
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
      setError(state, action) {
        setErrorHandler(state, action, sliceConfig);
      },
      setIsConfirmSavePopupOpen(state, action) {
        setIsConfirmSavePopupOpenHandler(state, action, sliceConfig);
      },
      setIsWsPopupOpen(state, action) {
        setIsWsPopupOpenHandler(state, action, sliceConfig);
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
