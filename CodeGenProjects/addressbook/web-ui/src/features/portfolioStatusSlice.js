import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_ROOT_URL, DB_ID, Messages } from '../constants';

const initialState = {
    portfolioStatusArray: [],
    portfolioStatus: {},
    modifiedPortfolioStatus: {},
    selectedPortfolioStatusId: null,
    loading: true,
    error: null
}

export const getAllPortfolioStatus = createAsyncThunk('portfolioStatus/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-portfolio_status`)
        .then(res => res.data);
})

export const getPortfolioStatus = createAsyncThunk('portfolioStatus/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-portfolio_status/${id}`)
        .then(res => res.data);
})

export const createPortfolioStatus = createAsyncThunk('portfolioStatus/create', (payload) => {
    return axios.post(`${API_ROOT_URL}/create-portfolio_status`, payload)
        .then(res => res.data);
})

export const updatePortfolioStatus = createAsyncThunk('portfolioStatus/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-portfolio_status`, payload)
        .then(res => res.data);
})

const portfolioStatusSlice = createSlice({
    name: 'portfolioStatus',
    initialState: initialState,
    reducers: {
        resetPortfolioStatus: (state) => {
            state.portfolioStatus = initialState.portfolioStatus;
        },
        setModifiedPortfolioStatus: (state, action) => {
            state.modifiedPortfolioStatus = action.payload;
        },
        setSelectedPortfolioStatusId: (state, action) => {
            state.selectedPortfolioStatusId = action.payload;
        },
        resetSelectedPortfolioStatusId: (state) => {
            state.selectedPortfolioStatusId = initialState.selectedPortfolioStatusId;
        },
        resetError: (state) => {
            state.error = initialState.error;
        }
    },
    extraReducers: {
        [getAllPortfolioStatus.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedPortfolioStatusId = null;
        },
        [getAllPortfolioStatus.fulfilled]: (state, action) => {
            state.portfolioStatusArray = action.payload;
            if (action.payload.length === 0) {
                state.portfolioStatus = initialState.portfolioStatus;
                state.modifiedPortfolioStatus = initialState.modifiedPortfolioStatus;
                state.selectedPortfolioStatusId = initialState.selectedPortfolioStatusId;
            } else if (action.payload.length === 1) {
                state.portfolioStatus = action.payload[0];
                state.modifiedPortfolioStatus = action.payload[0];
                state.selectedPortfolioStatusId = state.portfolioStatus[DB_ID];
            }
            state.loading = false;
        },
        [getAllPortfolioStatus.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getPortfolioStatus.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getPortfolioStatus.fulfilled]: (state, action) => {
            state.portfolioStatus = action.payload;
            state.modifiedPortfolioStatus = action.payload;
            state.selectedPortfolioStatusId = state.portfolioStatus[DB_ID];
            state.loading = false;
        },
        [getPortfolioStatus.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createPortfolioStatus.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createPortfolioStatus.fulfilled]: (state, action) => {
            state.portfolioStatus = action.payload;
            state.modifiedPortfolioStatus = action.payload;
            state.loading = false;
        },
        [createPortfolioStatus.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updatePortfolioStatus.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updatePortfolioStatus.fulfilled]: (state, action) => {
            state.portfolioStatus = action.payload;
            state.modifiedPortfolioStatus = action.payload;
            state.loading = false;
        },
        [updatePortfolioStatus.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default portfolioStatusSlice.reducer;

export const { resetPortfolioStatus, setModifiedPortfolioStatus, setSelectedPortfolioStatusId, resetSelectedPortfolioStatusId, resetError } = portfolioStatusSlice.actions;
