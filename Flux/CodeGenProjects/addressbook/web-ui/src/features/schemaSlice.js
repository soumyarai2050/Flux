import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import _ from 'lodash';
import { API_PUBLIC_URL, Modes, SCHEMA_AUTOCOMPLETE_XPATH, SCHEMA_DEFINITIONS_XPATH } from '../constants';
import { createCollections, getParentSchema } from '../utils';

const initialState = {
    schema: {},
    schemaCollections: {},
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
            Object.keys(state.schema).map(schemaName => {
                if ([SCHEMA_AUTOCOMPLETE_XPATH, SCHEMA_DEFINITIONS_XPATH].includes(schemaName)) return;
                let schema = state.schema;
                let currentSchema = _.get(schema, schemaName);
                let isJsonRoot = currentSchema.json_root ? currentSchema.json_root : false;
                let xpath;
                let callerProps = {};
                if (!isJsonRoot) {
                    xpath = schemaName;
                    callerProps.xpath = xpath;
                    callerProps.parentSchema = getParentSchema(schema, schemaName);
                    callerProps.mode = Modes.READ_MODE;
                }
                state.schemaCollections[schemaName] = createCollections(schema, currentSchema, callerProps, undefined, undefined, xpath);
            });
            state.loading = false;
            return;
        },
        [getSchema.rejected]: (state, action) => {
            state.error = action.error.code + ': ' + action.error.message;
            state.loading = false;
        }
    }
})

export default schemaSlice.reducer;