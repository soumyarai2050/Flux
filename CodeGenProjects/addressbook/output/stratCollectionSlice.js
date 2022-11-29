import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_ROOT_URL, DB_ID, Messages } from '../constants';

const initialState = {
    stratCollectionArray: [],
    stratCollection: {},
    modifiedStratCollection: {},
    selectedStratCollectionId: null,
    loading: true,
    error: null
}

export const getAllStratCollection = createAsyncThunk('stratCollection/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-strat_collection`)
        .then(res => res.data);
})

export const getStratCollection = createAsyncThunk('stratCollection/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-strat_collection/${id}`)
        .then(res => res.data);
})

export const createStratCollection = createAsyncThunk('stratCollection/create', (payload) => {
    return axios.post(`${API_ROOT_URL}/create-strat_collection`, payload)
        .then(res => res.data);
})

export const updateStratCollection = createAsyncThunk('stratCollection/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-strat_collection`, payload)
        .then(res => res.data);
})

const stratCollectionSlice = createSlice({
    name: 'stratCollection',
    initialState: initialState,
    reducers: {
        resetStratCollection: (state) => {
            state.stratCollection = initialState.stratCollection;
        },
        setModifiedStratCollection: (state, action) => {
            state.modifiedStratCollection = action.payload;
        },
        setSelectedStratCollectionId: (state, action) => {
            state.selectedStratCollectionId = action.payload;
        },
        resetSelectedStratCollectionId: (state) => {
            state.selectedStratCollectionId = initialState.selectedStratCollectionId;
        },
        resetError: (state) => {
            state.error = initialState.error;
        }
    },
    extraReducers: {
        [getAllStratCollection.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedStratCollectionId = null;
        },
        [getAllStratCollection.fulfilled]: (state, action) => {
            state.stratCollectionArray = action.payload;
            if (action.payload.length === 0) {
                state.stratCollection = initialState.stratCollection;
                state.modifiedStratCollection = initialState.modifiedStratCollection;
                state.selectedStratCollectionId = initialState.selectedStratCollectionId;
            } else if (action.payload.length === 1) {
                state.stratCollection = action.payload[0];
                state.modifiedStratCollection = action.payload[0];
                state.selectedStratCollectionId = state.stratCollection[DB_ID];
            }
            state.loading = false;
        },
        [getAllStratCollection.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getStratCollection.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getStratCollection.fulfilled]: (state, action) => {
            state.stratCollection = action.payload;
            state.modifiedStratCollection = action.payload;
            state.selectedStratCollectionId = state.stratCollection[DB_ID];
            state.loading = false;
        },
        [getStratCollection.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createStratCollection.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createStratCollection.fulfilled]: (state, action) => {
            state.stratCollection = action.payload;
            state.modifiedStratCollection = action.payload;
            state.loading = false;
        },
        [createStratCollection.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updateStratCollection.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updateStratCollection.fulfilled]: (state, action) => {
            state.stratCollection = action.payload;
            state.modifiedStratCollection = action.payload;
            state.loading = false;
        },
        [updateStratCollection.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default stratCollectionSlice.reducer;

export const { resetStratCollection, setModifiedStratCollection, setSelectedStratCollectionId, resetSelectedStratCollectionId, resetError } = stratCollectionSlice.actions;
