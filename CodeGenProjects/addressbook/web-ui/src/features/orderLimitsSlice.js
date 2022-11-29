import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_ROOT_URL, DB_ID, Messages } from '../constants';

const initialState = {
    orderLimitsArray: [],
    orderLimits: {},
    modifiedOrderLimits: {},
    selectedOrderLimitsId: null,
    loading: true,
    error: null
}

export const getAllOrderLimits = createAsyncThunk('orderLimits/getAll', () => {
    return axios.get(`${API_ROOT_URL}/get-all-order_limits`)
        .then(res => res.data);
})

export const getOrderLimits = createAsyncThunk('orderLimits/get', (id) => {
    return axios.get(`${API_ROOT_URL}/get-order_limits/${id}`)
        .then(res => res.data);
})

export const createOrderLimits = createAsyncThunk('orderLimits/create', (payload) => {
    return axios.post(`${API_ROOT_URL}/create-order_limits`, payload)
        .then(res => res.data);
})

export const updateOrderLimits = createAsyncThunk('orderLimits/update', (payload) => {
    return axios.put(`${API_ROOT_URL}/put-order_limits`, payload)
        .then(res => res.data);
})

const orderLimitsSlice = createSlice({
    name: 'orderLimits',
    initialState: initialState,
    reducers: {
        resetOrderLimits: (state) => {
            state.orderLimits = initialState.orderLimits;
        },
        setModifiedOrderLimits: (state, action) => {
            state.modifiedOrderLimits = action.payload;
        },
        setSelectedOrderLimitsId: (state, action) => {
            state.selectedOrderLimitsId = action.payload;
        },
        resetSelectedOrderLimitsId: (state) => {
            state.selectedOrderLimitsId = initialState.selectedOrderLimitsId;
        },
        resetError: (state) => {
            state.error = initialState.error;
        }
    },
    extraReducers: {
        [getAllOrderLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
            state.selectedOrderLimitsId = null;
        },
        [getAllOrderLimits.fulfilled]: (state, action) => {
            state.orderLimitsArray = action.payload;
            if (action.payload.length === 0) {
                state.orderLimits = initialState.orderLimits;
                state.modifiedOrderLimits = initialState.modifiedOrderLimits;
                state.selectedOrderLimitsId = initialState.selectedOrderLimitsId;
            } else if (action.payload.length === 1) {
                state.orderLimits = action.payload[0];
                state.modifiedOrderLimits = action.payload[0];
                state.selectedOrderLimitsId = state.orderLimits[DB_ID];
            }
            state.loading = false;
        },
        [getAllOrderLimits.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [getOrderLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getOrderLimits.fulfilled]: (state, action) => {
            state.orderLimits = action.payload;
            state.modifiedOrderLimits = action.payload;
            state.selectedOrderLimitsId = state.orderLimits[DB_ID];
            state.loading = false;
        },
        [getOrderLimits.rejected]: (state, action) => {
            state.error = action.payload ? action.payload : Messages.ERROR_GET;
            state.loading = false;
        },
        [createOrderLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [createOrderLimits.fulfilled]: (state, action) => {
            state.orderLimits = action.payload;
            state.modifiedOrderLimits = action.payload;
            state.loading = false;
        },
        [createOrderLimits.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        },
        [updateOrderLimits.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [updateOrderLimits.fulfilled]: (state, action) => {
            state.orderLimits = action.payload;
            state.modifiedOrderLimits = action.payload;
            state.loading = false;
        },
        [updateOrderLimits.rejected]: (state, action) => {
            state.error = action.payload;
            state.loading = false;
        }
    }
})

export default orderLimitsSlice.reducer;

export const { resetOrderLimits, setModifiedOrderLimits, setSelectedOrderLimitsId, resetSelectedOrderLimitsId, resetError } = orderLimitsSlice.actions;
