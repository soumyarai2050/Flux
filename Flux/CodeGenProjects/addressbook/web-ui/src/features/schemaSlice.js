import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import { API_PUBLIC_URL } from '../constants';

const initialState = {
    schema: {},
    loading: true,
    error: null
}

export const getSchema = createAsyncThunk('schema/get', () => {
    return axios.get(`${API_PUBLIC_URL}/schema.json`)
        .then(res => res.data)
})

const schemaSlice = createSlice({
    name: 'schema',
    initialState: initialState,
    reducers: {},
    extraReducers: {
        [getSchema.pending]: (state) => {
            state.loading = true;
            state.error = null;
        },
        [getSchema.fulfilled]: (state, action) => {
            state.schema = action.payload;
            state.loading = false;
        },
        [getSchema.rejected]: (state, action) => {
            state.error = action.error.code + ': ' + action.error.message;
            state.loading = false;
        }
    }
})

export default schemaSlice.reducer;