import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import _ from 'lodash';
import { API_PUBLIC_URL, MODES, SCHEMA_AUTOCOMPLETE_XPATH, SCHEMA_DEFINITIONS_XPATH } from '../constants';
import { createCollections, getParentSchema, FileOptions } from '../utils/index.js';

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
            state.loading = false;
            Object.keys(state.schema).forEach(schemaName => {
                if ([SCHEMA_AUTOCOMPLETE_XPATH].includes(schemaName)) return;
                if ('file_options' === schemaName) {
                    for (const option in state.schema[schemaName]) {
                        FileOptions[option] = state.schema[schemaName][option];
                    }
                    return;
                }
                let schema = state.schema;
                let currentSchema = _.get(schema, schemaName);
                let isJsonRoot = currentSchema.json_root ? currentSchema.json_root : false;
                let xpath;
                let callerProps = {};
                if (schemaName === SCHEMA_DEFINITIONS_XPATH) {
                    const schemaDefinitions = state.schema[SCHEMA_DEFINITIONS_XPATH]
                    for (const messageName in schemaDefinitions) {
                        const messageAttributes = schemaDefinitions[messageName];
                        if (messageAttributes.hasOwnProperty('json_root')) {
                            state.schemaCollections[messageName] = createCollections(schema, messageAttributes, callerProps, undefined, undefined, xpath);
                        }
                    }
                } else {
                    if (!isJsonRoot) {
                        xpath = schemaName;
                        callerProps.xpath = xpath;
                        callerProps.parentSchema = getParentSchema(schema, schemaName);
                        callerProps.mode = MODES.READ;
                    }
                    state.schemaCollections[schemaName] = createCollections(schema, currentSchema, callerProps, undefined, undefined, xpath);
                }
            });
        },
        [getSchema.rejected]: (state, action) => {
            state.error = action.error.code + ': ' + action.error.message;
            state.loading = false;
        }
    }
})

export default schemaSlice.reducer;