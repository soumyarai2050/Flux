import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_ROOT_URL, DB_ID, Messages } from '../constants';

const initialState = {
    uiLayoutArray: [],
    uiLayout: {},
    modifiedUILayout: {},
    selectedUILayoutId: null,
    loading: true,
    error: null
}

export const getAllUILayout = createAsyncThunk('uiLayout/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-ui_layout`)
        .then(res => res.data);
})

export const getUILayout = createAsyncThunk('uiLayout/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-ui_layout/${id}`)
        .then(res => res.data);
})

export const createUILayout = createAsyncThunk('uiLayout/create', (payload) => {
    return axios.post(`${API_ROOT_URL}/create-ui_layout`, payload)
        .then(res => res.data);
})

export const updateUILayout = createAsyncThunk('uiLayout/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-ui_layout`, payload)
        .then(res => res.data);
})

const uiLayoutSlice = createSlice({
    name: 'uiLayout',
    initialState: initialState,
    reducers: {
        resetUILayout: (state) => {
            state.uiLayout = initialState.uiLayout;
        },
        setModifiedUILayout: (state, action) => {
            state.modifiedUILayout = action.payload;
        },
        setSelectedUILayoutId: (state, action) => {
            state.selectedUILayoutId = action.payload;
        },
        resetSelectedUILayoutId: (state) => {
            state.selectedUILayoutId = initialState.selectedUILayoutId;
        },
        resetError: (state) => {
            state.error = initialState.error;
        }
    },
    extraReducers: {
        [getAllUILayout.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedUILayoutId = null;
        },
        [getAllUILayout.fulfilled]: (state, action) => {
            state.uiLayoutArray = action.payload;
            state.loading = false;
        },
        [getAllUILayout.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getUILayout.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getUILayout.fulfilled]: (state, action) => {
            state.uiLayout = action.payload;
            state.modifiedUILayout = action.payload;
            state.selectedUILayoutId = state.uiLayout[DB_ID];
            state.loading = false;
        },
        [getUILayout.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createUILayout.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createUILayout.fulfilled]: (state, action) => {
            state.uiLayout = action.payload;
            state.modifiedUILayout = action.payload;
            state.loading = false;
        },
        [createUILayout.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updateUILayout.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updateUILayout.fulfilled]: (state, action) => {
            state.uiLayout = action.payload;
            state.modifiedUILayout = action.payload;
            state.loading = false;
        },
        [updateUILayout.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default uiLayoutSlice.reducer;

export const { resetUILayout, setModifiedUILayout, setSelectedUILayoutId, resetSelectedUILayoutId, resetError } = uiLayoutSlice.actions;
