import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import _ from 'lodash';
import { API_PUBLIC_URL, MODES, SCHEMA_AUTOCOMPLETE_XPATH, SCHEMA_DEFINITIONS_XPATH } from '../constants';
import { createCollections, getParentSchema, FileOptions } from '../utils/index.js';
import { computeModelToDependentMap } from '../utils/dynamicSchemaUtils/dataSourceUtils.js';

const initialState = {
    schema: {},
    schemaCollections: {},
    abbreviationModelToSourcesMap: {},
    modelToDependencyMap: {},
    abbreviationSourcesSet: [], // Array instead of Set for Redux serialization
    loading: true,
    error: null
}

export const getSchema = createAsyncThunk('schema/get', () => {
    return axios.get(`${API_PUBLIC_URL}/schema.json`, {
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    })
        .then(res => res.data)
})

const schemaSlice = createSlice({
    name: 'schema',
    initialState: initialState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(getSchema.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(getSchema.fulfilled, (state, action) => {
                state.schema = action.payload;
                // Compute abbreviation sources map, dependency map, and abbreviation sources set in single pass
                const { abbreviationModelToSourcesMap, modelToDependencyMap, abbreviationSourcesSet } = computeModelToDependentMap(state.schema);
                state.abbreviationModelToSourcesMap = abbreviationModelToSourcesMap;
                state.modelToDependencyMap = modelToDependencyMap;
                // Convert Set to Array for Redux serialization
                state.abbreviationSourcesSet = Array.from(abbreviationSourcesSet);

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

                state.loading = false;
            })
            .addCase(getSchema.rejected, (state, action) => {
                state.error = action.error.code + ': ' + action.error.message;
                state.loading = false;
            });
    }
})

export default schemaSlice.reducer;