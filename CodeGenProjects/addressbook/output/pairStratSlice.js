import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { cloneDeep } from 'lodash';
import { API_ROOT_URL, DB_ID, Modes, Messages, NEW_ITEM_ID } from '../constants';
import { updateStratCollection } from './stratCollectionSlice';

const initialState = {
    pairStratArray: [],
    pairStrat: {},
    modifiedPairStrat: {},
    selectedPairStratId: null,
    loading: true,
    error: null,
    mode: Modes.READ_MODE,
    createMode: false
}

export const getAllPairStrat = createAsyncThunk('pairStrat/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-pair_strat`)
        .then(res => res.data);
})

export const getPairStrat = createAsyncThunk('pairStrat/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-pair_strat/${id}`)
        .then(res => res.data);
})

export const createPairStrat = createAsyncThunk('pairStrat/create', (payload, { dispatch, getState }) => {
    return axios.post(`${API_ROOT_URL}/create-pair_strat`, payload)
        .then(res => {
            let state = getState();
            let updatedData = cloneDeep(state.stratCollection.modifiedStratCollection);
            let updatedLoaded = updatedData.loaded_strat_keys.map((key) => {
                let id = key.split('-').pop() * 1;
                if (id !== NEW_ITEM_ID) return key;
                else {
                    key = key.replace(id, res.data[DB_ID]);
                    return key;
                }
            })
            updatedData.loaded_strat_keys = updatedLoaded;
            dispatch(updateStratCollection(updatedData));
            return res.data;
        });
})

export const updatePairStrat = createAsyncThunk('pairStrat/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-pair_strat`, payload)
        .then(res => res.data);
})

const pairStratSlice = createSlice({
    name: 'pairStrat',
    initialState: initialState,
    reducers: {
        resetPairStrat: (state) => {
            state.pairStrat = initialState.pairStrat;
        },
        setModifiedPairStrat: (state, action) => {
            state.modifiedPairStrat = action.payload;
        },
        setSelectedPairStratId: (state, action) => {
            state.selectedPairStratId = action.payload;
        },
        resetSelectedPairStratId: (state) => {
            state.selectedPairStratId = initialState.selectedPairStratId;
        },
        resetError: (state) => {
            state.error = null;
        },
        setMode: (state, action) => {
            state.mode = action.payload;
        },
        setCreateMode: (state, action) => {
            state.createMode = action.payload;
        }
    },
    extraReducers: {
        [getAllPairStrat.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedPairStratId = null;
        },
        [getAllPairStrat.fulfilled]: (state, action) => {
            state.pairStratArray = action.payload;
            state.pairStrat = initialState.pairStrat;
            state.modifiedPairStrat = initialState.modifiedPairStrat;
            state.selectedPairStratId = initialState.selectedPairStratId;
            state.loading = false;
        },
        [getAllPairStrat.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getPairStrat.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getPairStrat.fulfilled]: (state, action) => {
            state.pairStrat = action.payload;
            state.modifiedPairStrat = action.payload;
            state.selectedPairStratId = state.pairStrat[DB_ID];
            state.loading = false;
        },
        [getPairStrat.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createPairStrat.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createPairStrat.fulfilled]: (state, action) => {
            state.pairStrat = action.payload;
            state.modifiedPairStrat = action.payload;
            state.loading = false;
        },
        [createPairStrat.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updatePairStrat.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updatePairStrat.fulfilled]: (state, action) => {
            state.pairStrat = action.payload;
            state.modifiedPairStrat = action.payload;
            state.loading = false;
        },
        [updatePairStrat.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default pairStratSlice.reducer;

export const { resetPairStrat, setModifiedPairStrat, setSelectedPairStratId, resetSelectedPairStratId, resetError, setMode, setCreateMode } = pairStratSlice.actions;
