import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_ROOT_URL, DB_ID, Messages } from '../constants';

const initialState = {
    portfolioLimitsArray: [],
    portfolioLimits: {},
    modifiedPortfolioLimits: {},
    selectedPortfolioLimitsId: null,
    loading: true,
    error: null
}

export const getAllPortfolioLimits = createAsyncThunk('portfolioLimits/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-portfolio_limits`)
        .then(res => res.data);
})

export const getPortfolioLimits = createAsyncThunk('portfolioLimits/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-portfolio_limits/${id}`)
        .then(res => res.data);
})

export const createPortfolioLimits = createAsyncThunk('portfolioLimits/create', (payload) => {
    return axios.post(`${API_ROOT_URL}/create-portfolio_limits`, payload)
        .then(res => res.data);
})

export const updatePortfolioLimits = createAsyncThunk('portfolioLimits/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-portfolio_limits`, payload)
        .then(res => res.data);
})

const portfolioLimitsSlice = createSlice({
    name: 'portfolioLimits',
    initialState: initialState,
    reducers: {
        resetPortfolioLimits: (state) => {
            state.portfolioLimits = initialState.portfolioLimits;
        },
        setModifiedPortfolioLimits: (state, action) => {
            state.modifiedPortfolioLimits = action.payload;
        },
        setSelectedPortfolioLimitsId: (state, action) => {
            state.selectedPortfolioLimitsId = action.payload;
        },
        resetSelectedPortfolioLimitsId: (state) => {
            state.selectedPortfolioLimitsId = initialState.selectedPortfolioLimitsId;
        },
        resetError: (state) => {
            state.error = initialState.error;
        }
    },
    extraReducers: {
        [getAllPortfolioLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedPortfolioLimitsId = null;
        },
        [getAllPortfolioLimits.fulfilled]: (state, action) => {
            state.portfolioLimitsArray = action.payload;
            if (action.payload.length === 0) {
                state.portfolioLimits = initialState.portfolioLimits;
                state.modifiedPortfolioLimits = initialState.modifiedPortfolioLimits;
                state.selectedPortfolioLimitsId = initialState.selectedPortfolioLimitsId;
            } else if (action.payload.length === 1) {
                state.portfolioLimits = action.payload[0];
                state.modifiedPortfolioLimits = action.payload[0];
                state.selectedPortfolioLimitsId = state.portfolioLimits[DB_ID];
            }
            state.loading = false;
        },
        [getAllPortfolioLimits.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getPortfolioLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getPortfolioLimits.fulfilled]: (state, action) => {
            state.portfolioLimits = action.payload;
            state.modifiedPortfolioLimits = action.payload;
            state.selectedPortfolioLimitsId = state.portfolioLimits[DB_ID];
            state.loading = false;
        },
        [getPortfolioLimits.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createPortfolioLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createPortfolioLimits.fulfilled]: (state, action) => {
            state.portfolioLimits = action.payload;
            state.modifiedPortfolioLimits = action.payload;
            state.loading = false;
        },
        [createPortfolioLimits.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updatePortfolioLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updatePortfolioLimits.fulfilled]: (state, action) => {
            state.portfolioLimits = action.payload;
            state.modifiedPortfolioLimits = action.payload;
            state.loading = false;
        },
        [updatePortfolioLimits.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default portfolioLimitsSlice.reducer;

export const { resetPortfolioLimits, setModifiedPortfolioLimits, setSelectedPortfolioLimitsId, resetSelectedPortfolioLimitsId, resetError } = portfolioLimitsSlice.actions;
