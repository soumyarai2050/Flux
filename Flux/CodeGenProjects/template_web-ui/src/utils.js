// third-party package imports
import { cloneDeep, get, isObject, isEmpty, isNull, isEqual, has } from 'lodash';
import dayjs from 'dayjs';
import axios from 'axios';
import utc from 'dayjs/plugin/utc';
import * as XLSX from 'xlsx';
// project imports
import {
    COLOR_PRIORITY, COLOR_TYPES, DATA_TYPES, HOVER_TEXT_TYPES, MODES, SHAPE_TYPES, SIZE_TYPES,
    DB_ID, NEW_ITEM_ID, SCHEMA_DEFINITIONS_XPATH, API_ROOT_URL, SEVERITY_TYPES, API_ROOT_VIEW_URL
} from './constants';
import * as workerUtils from './workerUtils';
import { AlertCache } from './utility/alertCache';
import { getWebSocketConnection } from './cache/websocketConnectionCache';
export const { applyFilter, applyGetAllWebsocketUpdate, floatToInt, getRowsFromAbbreviation,
    getActiveRows, getFilterDict, getIdFromAbbreviatedKey, getLocalizedValueAndSuffix,
    roundNumber, stableSort, sortAlertArray, getColorTypeFromValue, getGroupedTableRows,
} = workerUtils;
const LOCAL_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

// add utc support for datetime
dayjs.extend(utc);

// stores the tree expand/collapse states
export const treeState = {};
// tree state setter
export function setTreeState(xpath, state) {
    treeState[xpath] = state;
}

export const FileOptions = {};

// support primitive data types
export const primitiveDataTypes = [
    DATA_TYPES.STRING,
    DATA_TYPES.BOOLEAN,
    DATA_TYPES.NUMBER,
    DATA_TYPES.ENUM,  // pre-defined set of values in schema.json file
    DATA_TYPES.DATE_TIME,
    DATA_TYPES.INT64,
    DATA_TYPES.FLOAT
];
// default floating point precision for floating point values
export const FLOAT_POINT_PRECISION = 2;
// message constants
export const Message = {
    REQUIRED_FIELD: 'required field cannot be null',
    UNSPECIFIED_FIELD: 'required enum field cannot be unset / UNSPECIFIED',
    MAX: 'field value exceeds the max limit',
    MIN: 'field value exceeds the min limit'
}
// support column sizes
export const ColumnSize = {
    SMALL: 'small',
    MEDIUM: 'medium',
    LARGE: 'large',
}
// supported column direction of text
export const ColumnDirection = {
    LTR: 'ltr',
    RTL: 'rtl',
}

// complex (object and array) field properties. applies/passed to child components also
export const complexFieldProps = [
    // if set to true, field not shown in edit mode
    { propertyName: "server_populate", usageName: "serverPopulate" },
    // if set to true, field not shown while creation but can be subsequently modified
    { propertyName: "ui_update_only", usageName: "uiUpdateOnly" },
    // if set to true, field cannot be modified once created. shown in edit mode but not editable
    { propertyName: "orm_no_update", usageName: "ormNoUpdate" },
    // if set, provides a set of options allowed on field (':'), and (or) assigns a default 
    // value to field (=), and (or) set server populate on field (server_populate) 
    { propertyName: "auto_complete", usageName: "autocomplete" },
    // if set to true, overrides the default title of field with their xpath
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    // if set to true, allow filter to be applied on the field
    { propertyName: "filter_enable", usageName: "filterEnable" },
    // chart projections related options
    { propertyName: "mapping_underlying_meta_field", usageName: "mapping_underlying_meta_field" },
    { propertyName: "mapping_src", usageName: "mapping_src" },
    { propertyName: "val_meta_field", usageName: "val_meta_field" },
    // if set to true, field is hidden by default
    { propertyName: "hide", usageName: "hide" },
]

// simple field flux properties supported by project
export const fieldProps = [
    // sets data type of field
    { propertyName: "type", usageName: "type" },
    // sets display title of field
    { propertyName: "title", usageName: "title" },
    // if set to true, field is hidden by default
    { propertyName: "hide", usageName: "hide" },
    // sets help text for the field
    { propertyName: "help", usageName: "help" },
    // TODO: not supported
    { propertyName: "cmnt", usageName: "description" },
    // sets default value of field, assigned when field is created
    { propertyName: "default", usageName: "default" },
    // sets sub data type of field
    { propertyName: "underlying_type", usageName: "underlyingtype" },
    // sets placeholder for the field, displays when field is unset
    { propertyName: "ui_placeholder", usageName: "placeholder" },
    // sets associated value color map for the field
    { propertyName: "color", usageName: "color" },
    // displays field as a button
    { propertyName: "button", usageName: "button" },
    // if set to JSON, field is displayed as JSON, otherwise holds metadata for field 
    // in collection (abbreviated filter) view
    { propertyName: "abbreviated", usageName: "abbreviated" },
    // sets max constraint on the field
    { propertyName: "val_max", usageName: "max" },
    // sets min constraint on the field
    { propertyName: "val_min", usageName: "min" },
    // TODO: not supported
    { propertyName: "default_value_placeholder_string", usageName: "defaultValuePlaceholderString" },
    // TODO: not supported
    { propertyName: "val_sort_weight", usageName: "sortWeight" },
    // sets field as datetime field
    { propertyName: "val_is_date_time", usageName: "dateTime" },
    // TODO: not supported
    { propertyName: "index", usageName: "index" },
    // TODO: not supported
    { propertyName: "sticky", usageName: "sticky" },
    // TODO: not supported
    { propertyName: "size_max", usageName: "sizeMax" },
    // display field as a progress bar
    { propertyName: "progress_bar", usageName: "progressBar" },
    // if set to True, overrides the default title of field with their xpath
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    // sets the color of field key
    { propertyName: "name_color", usageName: "nameColor" },
    // sets the number formating (floating point precision, prefix, suffix) on the field
    { propertyName: "number_format", usageName: "numberFormat" },
    // if set to True, field is not added to common key
    { propertyName: "no_common_key", usageName: "noCommonKey" },
    // sets the field value display type (float to display as int)
    { propertyName: "display_type", usageName: "displayType" },
    // sets the alignment of text in table
    { propertyName: "text_align", usageName: "textAlign" },
    // if set to True, field with 0 values are displayed
    { propertyName: "display_zero", usageName: "displayZero" },
    // sets the separator for multi-value field defined in abbreviated
    { propertyName: "micro_separator", usageName: "microSeparator" },
    // chart projection related fields
    { propertyName: "val_time_field", usageName: "val_time_field" },
    { propertyName: "projections", usageName: "projections" },
    { propertyName: "mapping_projection_query_field", usageName: "mapping_projection_query_field" },
    { propertyName: "mapping_underlying_meta_field", usageName: "mapping_underlying_meta_field" },
    { propertyName: "mapping_src", usageName: "mapping_src" },
    // indicates underlying server ready status is derivied from this field
    { propertyName: "server_ready_status", usageName: "server_ready_status" },
    // sets column size of field in table
    { propertyName: "column_size", usageName: "columnSize" },
    // sets column (text) direction of field in table
    { propertyName: "column_direction", usageName: "columnDirection" },
    // sets the allowed diff % on field which is saved without confirmation 
    { propertyName: "diff_threshold", usageName: "diffThreshold" },
    { propertyName: "zero_as_none", usageName: "zeroAsNone" },
]

// additional properties supported only on array fields
const arrayFieldProps = [
    // sets the source field to fetch bubble count
    { propertyName: "alert_bubble_source", usageName: "alertBubbleSource" },
    // sets the source field to fetch bubble color
    { propertyName: "alert_bubble_color", usageName: "alertBubbleColor" }
]

const optimizer = (fn) => {
    /**
     * higher order function to 
     */
}

// TODO: generalise supported flux options by project
const fluxOptions = []

function addFieldAttributes(object, attributes) {
    /* 
    function to add field level flux option on collection object.
    params:
        object: collection object
        attributes: attribute (flux option) dict set on the field
    */
    fluxOptions.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {
            if (isObject(attributes[propertyName])) {
                if (attributes.hasOwnProperty(object.key)) {
                    object[usageName] = attributes[propertyName][object.key];
                } // else not required - attribute not set on the object
            } else {
                object[usageName] = attributes[propertyName];
                // additional handling for ui component fields
                switch (propertyName) {
                    case 'button':
                        object.type = 'button';
                        object.color = attributes.button.value_color_map;
                        break;
                    case 'progress_bar':
                        object.type = 'progressBar';
                        object.color = attributes.progress_bar.value_color_map;
                        break;
                    case 'mapping_src':
                    case 'mapping_underlying_meta_field':
                        object[usageName] = object[usageName][0];
                        break;
                }
            }
        } // else not required - flux option not found in attribute list
    })
}

function addMessageAttributes(object, attributes, message) {
    /* 
    function to add field level flux option on collection object.
    params:
        object: collection object
        attributes: attribute (flux option) dict set on the field
        message:
    */
    fluxOptions.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {

        }
    })
}

const KEY_INDICATOR_SEPARATOR = '@@@';

export function getAutocompleteDict(autocompleteValue) {
    let autocompleteFieldSet = autocompleteValue.split(',').map((field) => field.trim());
    let autocompleteDict = {};

    autocompleteFieldSet.forEach(fieldSet => {
        if (fieldSet.indexOf(':') > 0) {
            let [key, value] = fieldSet.split(':');
            key = key.trim();
            value = value.trim();
            const indicator = 'options'
            const pathNIndicator = key + KEY_INDICATOR_SEPARATOR + indicator;
            autocompleteDict[pathNIndicator] = value;
        } else if (fieldSet.indexOf('=') > 0) {
            let [key, value] = fieldSet.split('=');
            key = key.trim();
            value = value.trim();
            const indicator = value === 'server_populate' ? 'server_populate' : 'assign';
            const pathNIndicator = key + KEY_INDICATOR_SEPARATOR + indicator;
            autocompleteDict[pathNIndicator] = value;
        } else {  // field separator is ~
            let [key, value] = fieldSet.split('~');
            key = key.trim();
            value = value.trim();
            const indicator = 'dynamic_options';
            const pathNIndicator = key + KEY_INDICATOR_SEPARATOR + indicator;
            autocompleteDict[pathNIndicator] = value;
        }
    })
    return autocompleteDict;
}

export function setAutocompleteValue(schema, object, autocompleteDict, propname, usageName) {
    for (const pathNIndicator in autocompleteDict) {
        const [path, indicator] = pathNIndicator.split(KEY_INDICATOR_SEPARATOR);
        if (path === propname || object.xpath.endsWith(path)) {
            const value = autocompleteDict[pathNIndicator];
            object[usageName] = value;
            if (indicator === 'options') {
                if (schema.autocomplete.hasOwnProperty(value)) {
                    object.options = schema.autocomplete[value];
                }
            } else if (indicator === 'dynamic_options') {
                object.dynamic_autocomplete = true;
                object.options = [];
            } else if (indicator === 'server_populate') {
                object.serverPopulate = true;
                delete object[usageName];
            }
        }
    }
}

function getKeyValueDictFromArray(array) {
    const dict = {};
    if (Array.isArray(array)) {
        array.forEach(arrayItem => {
            const [key, value] = arrayItem.split(':');
            dict[key] = value;
        })
    }
    return dict;
}

export function getMappingSrcDict(mappingSrc) {
    return getKeyValueDictFromArray(mappingSrc)
}

export function getMetaFieldDict(metaFieldList) {
    return getKeyValueDictFromArray(metaFieldList);
}

export function createCollections(schema, currentSchema, callerProps, collections = [], sequence = { sequence: 1 }, xpath, objectxpath, metaFieldId) {
    currentSchema = cloneDeep(currentSchema);

    if (callerProps.xpath) {
        let currentSchemaMetadata = callerProps.parentSchema.properties[callerProps.xpath];

        complexFieldProps.forEach(({ propertyName }) => {
            if (currentSchemaMetadata.hasOwnProperty(propertyName)) {
                currentSchema[propertyName] = currentSchemaMetadata[propertyName];
            }
        })
        callerProps.parent = callerProps.xpath;
        callerProps.xpath = null;
    }
    currentSchema.properties = sortSchemaProperties(currentSchema.properties);

    Object.entries(currentSchema.properties).map(([k, v]) => {
        let collection = {};
        if (primitiveDataTypes.includes(v.type)) {
            collection.key = k;
            collection.tableTitle = objectxpath ? objectxpath + '.' + k : k;
            collection.sequenceNumber = sequence.sequence;
            sequence.sequence += 1;
            collection.xpath = xpath ? xpath + '.' + k : k;
            collection.path = collection.xpath.replaceAll('[0]', '');
            collection.required = currentSchema.required.some(p => p === k);
            let parentxpath = xpath ? xpath !== callerProps.parent ? xpath : null : null;
            if (parentxpath) {
                if (callerProps.parent) {
                    parentxpath = parentxpath.replace(callerProps.parent + '.', '');
                }
                collection.parentxpath = parentxpath;
            }
            if (collection.xpath.indexOf('.') === -1 || (callerProps.parentSchema && collection.xpath.substring(collection.xpath.indexOf('.') + 1).indexOf('.') === -1)) {
                collection.rootLevel = true;
            }

            if (v.type === DATA_TYPES.ENUM) {
                let ref = v.items.$ref.split('/');
                collection.autocomplete_list = getEnumValues(schema, ref, v.type);
            }

            if ((currentSchema.hasOwnProperty('abbreviated') && currentSchema.abbreviated === 'JSON') || currentSchema.noColumn) {
                collection.noColumn = true;
            }

            fieldProps.map(({ propertyName, usageName }) => {
                if (v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName];

                    if (propertyName === "button") {
                        collection.type = "button";
                        collection.color = v.button.value_color_map;
                    }

                    if (propertyName === "progress_bar") {
                        collection.type = "progressBar";
                        collection.color = v.progress_bar.value_color_map;
                    }
                    if (propertyName === 'mapping_underlying_meta_field' || propertyName === 'mapping_src') {
                        collection[usageName] = v[propertyName][0];
                    }
                }
            })

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    const propertyValue = v[propertyName] ? v[propertyName] : currentSchema[propertyName];

                    if (propertyName === 'auto_complete') {
                        let autocompleteDict = getAutocompleteDict(propertyValue);
                        setAutocompleteValue(schema, collection, autocompleteDict, k, usageName);
                    }

                    if (propertyName === 'mapping_underlying_meta_field' || propertyName === 'mapping_src') {
                        let dict;
                        if (propertyName === 'mapping_underlying_meta_field') {
                            dict = getMetaFieldDict(propertyValue);
                        } else {
                            dict = getMappingSrcDict(propertyValue);
                        }
                        for (const field in dict) {
                            if (collection.xpath.endsWith(field)) {
                                collection[usageName] = dict[field];
                                collection.metaFieldId = metaFieldId;
                            }
                        }
                    }
                    if (!['auto_complete', 'mapping_underlying_meta_field', 'mapping_src'].includes(propertyName)) {
                        collection[usageName] = propertyValue;
                    }
                }
            })

            let isRedundant = true;
            if (collections.every(col => col.tableTitle !== collection.tableTitle)) {
                if (!(collection.serverPopulate && callerProps.mode === MODES.EDIT)) {
                    isRedundant = false;
                }
            }

            if (!isRedundant) {
                collections.push(collection);
            }

        } else if (v.type === DATA_TYPES.ARRAY) {
            collection.key = k;
            let elaborateTitle = objectxpath ? objectxpath + '.' + k : k;
            collection.tableTitle = elaborateTitle;
            collection.sequenceNumber = sequence.sequence;
            sequence.sequence += 1;
            let updatedxpath = xpath ? xpath + '.' + k : k;
            updatedxpath = updatedxpath + '[0]';
            collection.xpath = updatedxpath;
            let parentxpath = xpath ? xpath !== callerProps.parent ? xpath : null : null;
            if (parentxpath) {
                if (callerProps.parent) {
                    parentxpath = parentxpath.replace(callerProps.parent + '.', '');
                }
                collection.parentxpath = parentxpath;
            }

            if ((currentSchema.hasOwnProperty('abbreviated') && currentSchema.abbreviated === 'JSON') || currentSchema.noColumn) {
                collection.noColumn = true;
            }

            fieldProps.map(({ propertyName, usageName }) => {
                if (v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName];
                }
            })

            arrayFieldProps.map(({ propertyName, usageName }) => {
                if (v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName];
                }
            })

            // for array of primitive data types
            if (!v.hasOwnProperty('items') || (v.hasOwnProperty('items') && primitiveDataTypes.includes(collection.underlyingtype))) {
                collections.push(collection);
                return;
            }

            let ref = v.items.$ref.split('/')
            let record = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            record = cloneDeep(record);

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    record[propertyName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                }
            })
            collection.properties = record.properties;

            let isRedundant = true;
            if (collections.every(col => col.tableTitle !== collection.tableTitle)) {
                if (!(collection.serverPopulate && callerProps.mode === MODES.EDIT)) {
                    isRedundant = false;
                }
            }
            if (!isRedundant) {
                collections.push(collection);
            }
            if (collection.abbreviated === 'JSON') {
                const sc = createCollections(schema, record, callerProps, [], sequence, updatedxpath, elaborateTitle);
                collection.subCollections = cloneDeep(sc);
            } else {
                createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
            }
        } else if (v.type === DATA_TYPES.OBJECT) {
            collection.key = k;
            let elaborateTitle = objectxpath ? objectxpath + '.' + k : k;
            collection.tableTitle = elaborateTitle;
            collection.sequenceNumber = sequence.sequence;
            sequence.sequence += 1;
            let updatedxpath = xpath ? xpath + '.' + k : k;
            collection.xpath = updatedxpath;
            let parentxpath = xpath ? xpath !== callerProps.parent ? xpath : null : null;
            if (parentxpath) {
                if (callerProps.parent) {
                    parentxpath = parentxpath.replace(callerProps.parent + '.', '');
                }
                collection.parentxpath = parentxpath;
            }

            if ((currentSchema.hasOwnProperty('abbreviated') && currentSchema.abbreviated === 'JSON') || currentSchema.noColumn) {
                collection.noColumn = true;
            }

            fieldProps.map(({ propertyName, usageName }) => {
                if (v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName];
                }
            })

            let ref = v.items.$ref.split('/')
            let record = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            record = cloneDeep(record);

            let metaId = metaFieldId;
            if (v.hasOwnProperty('mapping_underlying_meta_field')) {
                if (!metaId) {
                    metaId = collection.xpath;
                }
            }

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                    record[propertyName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                }
            })
            collection.properties = record.properties;

            let isRedundant = true;
            if (collections.every(col => col.tableTitle !== collection.tableTitle)) {
                if (!(collection.serverPopulate && callerProps.mode === MODES.EDIT)) {
                    isRedundant = false;
                }
            }
            if (!isRedundant) {
                collections.push(collection);
            }
            if (collection.abbreviated === 'JSON') {
                const sc = createCollections(schema, record, callerProps, [], sequence, updatedxpath, elaborateTitle);
                collection.subCollections = cloneDeep(sc);
            } else {
                createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle, metaId);
            }
        }
    });
    return collections;
}

export function generateObjectFromSchema(schema, currentSchema, additionalProps, objectxpath, objToDup) {
    if (additionalProps && additionalProps instanceof Object) {
        for (const key in additionalProps) {
            const prop = complexFieldProps.find(({ usageName }) => usageName === key);
            if (prop) {
                currentSchema[prop.propertyName] = additionalProps[key];
            } else {
                delete additionalProps[key];
            }
        }
    }

    let object = {};
    Object.keys(currentSchema.properties).map(propname => {
        let metadata = currentSchema.properties[propname];
        const xpath = objectxpath ? objectxpath + '.' + propname : propname;

        // do not create fields if populated from server or creation is not allowed on the fields.
        if (metadata.server_populate || metadata.ui_update_only) return;

        if (objToDup) {
            // if reached here, server_populate and ui_update_only fields are already ignored
            if ([DATA_TYPES.STRING, DATA_TYPES.NUMBER, DATA_TYPES.BOOLEAN, DATA_TYPES.DATE_TIME, DATA_TYPES.ENUM].includes(metadata.type)) {
                object[propname] = get(objToDup, xpath);
                return;
            }
        }

        if (metadata.type === DATA_TYPES.STRING) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : null;
            // autocomplete overrides the default if set on string. Set default via autocomplete
            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteDict = getAutocompleteDict(autocomplete);

                for (const pathNIndicator in autocompleteDict) {
                    const [path, indicator] = pathNIndicator.split(KEY_INDICATOR_SEPARATOR);
                    if (propname === path || xpath.endsWith(path)) {
                        const value = autocompleteDict[pathNIndicator];
                        if (indicator === 'server_populate') {
                            delete object[propname];
                        } else if (indicator === 'assign') {
                            // TODO: check if value is present in available options
                            object[propname] = value;
                        }
                    }
                }
            }
        } else if (metadata.type === DATA_TYPES.NUMBER) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : null;
        } else if (metadata.type === DATA_TYPES.BOOLEAN) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : false;
        } else if (metadata.type === DATA_TYPES.DATE_TIME) {
            // default date-time is null (unassigned)
            object[propname] = null;
        } else if (metadata.type === DATA_TYPES.ENUM) {
            // Ensure 'default' is prioritized for ENUMs
            if (metadata.hasOwnProperty('default')) {
                object[propname] = metadata.default;
            } else {
                let ref = metadata.items.$ref.split('/')
                let enumdata = getEnumValues(schema, ref, metadata.type)
                object[propname] = enumdata && enumdata.length > 0 ? enumdata[0] : null;
            }

            // Autocomplete logic for ENUM (can override the default or first enum value)
            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteDict = getAutocompleteDict(autocomplete);

                for (const pathNIndicator in autocompleteDict) {
                    const [path, indicator] = pathNIndicator.split(KEY_INDICATOR_SEPARATOR);
                    if (propname === path || xpath.endsWith(path)) {
                        const value = autocompleteDict[pathNIndicator];
                        if (indicator === 'server_populate') {
                            delete object[propname]; // Remove if server_populate indicates it shouldn't exist yet
                        } else if (indicator === 'assign') {
                            // TODO: check if value is present in available options from enumdata
                            object[propname] = value;
                        }
                    }
                }
            }
        } else if (metadata.type === DATA_TYPES.ARRAY) {
            // for arrays of primitive data types
            if (!metadata.hasOwnProperty('items') || (metadata.hasOwnProperty('items') && primitiveDataTypes.includes(metadata.underlying_type))) {
                object[propname] = [];
            } else {
                let ref = metadata.items.$ref.split('/');
                let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
                childSchema = cloneDeep(childSchema);

                if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                    childSchema.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                }

                if (!childSchema.server_populate && !metadata.server_populate) {
                    let child = generateObjectFromSchema(schema, childSchema, null, xpath, objToDup);
                    object[propname] = [];
                    object[propname].push(child);
                }
            }
        } else if (metadata.type === DATA_TYPES.OBJECT) {
            let ref = metadata.items.$ref.split('/');
            let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            childSchema = cloneDeep(childSchema);
            const required = currentSchema.required.some(prop => prop === propname);

            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                childSchema.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
            }

            if (!(childSchema.server_populate || childSchema.ui_update_only)) {
                if (required) {
                    object[propname] = generateObjectFromSchema(schema, childSchema, null, xpath, objToDup);
                } else {
                    object[propname] = null;
                }
            }
        }
    });
    return object;
}

export function getEnumValues(schema, ref, type) {
    if (type === DATA_TYPES.ENUM) {
        return schema[ref[1]][ref[2]]['enum'];
    }
    return schema[ref[1]][ref[2]];
}

export function getDataxpath(data, xpath) {
    if (!xpath) return;
    if (xpath.includes('-1')) return xpath;
    let updatedxpath = '';
    let originalxpath = '';
    for (let i = 0; i < xpath.split(']').length - 1; i++) {
        let currentxpath = xpath.split(']')[i];
        let index = currentxpath.split('[')[1];
        currentxpath = currentxpath.split('[')[0];
        originalxpath = originalxpath + currentxpath + '[' + index + ']';

        let found = false;
        if (get(data, updatedxpath + currentxpath)) {
            get(data, updatedxpath + currentxpath).forEach((obj, idx) => {
                let propname = Object.keys(obj).find(key => key.startsWith('xpath_'));
                if (!propname) return;
                let propxpath = obj[propname].substring(0, obj[propname].lastIndexOf('.'));
                if (propxpath === originalxpath) {
                    index = idx;
                    found = true;
                }
            })
        } else if (xpath.startsWith('[')) {  // repeated root widget. xpath starts with []
            found = true;
        }
        if (found) {
            updatedxpath = updatedxpath + currentxpath + '[' + index + ']';
        } else {
            return;
        }
    }
    updatedxpath = updatedxpath + xpath.split(']')[xpath.split(']').length - 1];
    return updatedxpath;
}

export function compareNodes(originalData, data, dataxpath, propname, xpath) {
    let object = {};
    let current = data[propname];
    let original = originalData[propname];
    if (dataxpath || xpath) {
        current = hasxpath(data, dataxpath) ? get(data, dataxpath)[propname] : undefined;
        original = hasxpath(originalData, xpath) ? get(originalData, xpath)[propname] : undefined;
    }
    if (current !== undefined && original !== undefined && (current !== original)) {
        object['data-modified'] = true;
    } else if (current !== undefined && original === undefined) {
        object['data-add'] = true;
    } else if (current === undefined && original !== undefined) {
        object['data-remove'] = true;
        object.value = original;
    }
    return object;
}

function sortSchemaProperties(properties) {
    return Object.keys(properties).sort(function (a, b) {
        if (properties[a].sequence_number < properties[b].sequence_number) return -1;
        else return 1;
    }).reduce(function (obj, key) {
        obj[key] = properties[key];
        return obj;
    }, {})
}


export function isNodeInSubtree(callerProps, xpath, dataxpath) {
    xpath = xpath.replace(/\[\d+\]/g, '[0]');
    if (callerProps.subtree) {
        if (callerProps.xpath) {
            xpath = xpath.substring(xpath.indexOf('.') + 1);
        }
        if (!get(callerProps.subtree, xpath + '[0]')) return false;
        else {
            let propname = Object.keys(get(callerProps.subtree, xpath + '[0]')).find(key => key.startsWith('xpath_'));
            if (!propname) return false;
            let propxpath = xpath + '[0].' + propname
            propxpath = get(callerProps.subtree, propxpath);
            propxpath = propxpath.substring(0, propxpath.lastIndexOf(']') + 1);
            if (propxpath !== dataxpath) return false;
        }
    }
    return true;
}

export function capitalizeFirstLetter(text) {
    if (text && text.length > 0) {
        return text.charAt(0).toUpperCase() + text.slice(1);
    }
    return text;
}

export function lowerFirstLetter(text) {
    if (text && text.length > 0) {
        return text.charAt(0).toLowerCase() + text.slice(1);
    }
    return text;
}

export function capitalizeCamelCase(text) {
    if (text && text.length > 0) {
        let textSplit = text.split('_').map(t => t.charAt(0).toUpperCase() + t.slice(1));
        return textSplit.join('');
    }
    return text;
}

export function toCamelCase(text) {
    if (text && text.length > 0) {
        let textSplit = text.split('_');
        for (let i = 1; i < textSplit.length; i++) {
            let value = textSplit[i];
            value = value.charAt(0).toUpperCase() + value.slice(1);
            textSplit[i] = value;
        }
        return textSplit.join('');
    }
    return text;
}

export function generateRowTrees(jsondata, collections, xpath) {
    const trees = [];
    // if xpath is present, jsondata is subset of data
    if (xpath) {
        jsondata = get(jsondata, xpath);
    }
    if (!jsondata) {
        return trees;
    }

    while (true) {
        if (Array.isArray(jsondata)) {
            for (let i = 0; i < jsondata.length; i++) {
                let tree = {};
                createTree(tree, jsondata[i], null, { delete: 1 }, collections);

                if (Object.keys(tree).length === 0) break;

                // if (!constainsArray(tree)) {
                //     tree['data-id'] = i;
                // }
                // array object should be of flat-type
                tree['data-id'] = jsondata[i][DB_ID];

                if (trees.length > 0 && isEqual(trees[trees.length - 1], tree)) {
                    continue;
                }
                trees.push(tree);
            }
            break;
        } else {
            let tree = {};
            Object.entries(jsondata).map(([k, v]) => {
                if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
                    tree[k] = v;
                } else if (isNull(v)) {
                    tree[k] = null;
                } else if (Array.isArray(v)) {
                    tree[k] = [];
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections);
                    if (tree[k][0]?.hasOwnProperty('data-id')) {
                        tree['data-id'] = tree[k][0]['data-id'];
                    }
                } else if (isObject(v)) {
                    tree[k] = {};
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections);
                }
            })

            if (Object.keys(tree).length === 0) break;

            if (!constainsArray(tree)) {
                tree['data-id'] = 0;
            }

            if (trees.length > 0 && isEqual(trees[trees.length - 1], tree)) {
                break;
            }
            trees.push(tree);
        }
    }
    return trees;
}

function constainsArray(obj) {
    if (isObject(obj)) {
        for (const key in obj) {
            if (Array.isArray(obj[key])) {
                return true;
            } else if (isObject(obj[key])) {
                const hasArray = constainsArray(obj[key]);
                if (hasArray) {
                    return true;
                }
            }
        }
    } else if (obj === null) {
        return false;
    } else {
        throw new Error('constainsArray function failed. unsupported obj type: ' + typeof obj + ', expected object type.')
    }
    return false;
}


function createTree(tree, currentjson, propname, count, collections) {
    if (Array.isArray(currentjson)) {
        if (currentjson.length === 0) return;

        tree[propname] = [];
        if (collections.some(c => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
            tree[propname] = currentjson;
        } else {
            if (currentjson[0] === null || currentjson[0] === undefined || primitiveDataTypes.includes(typeof currentjson[0])) {
                return;
            } else {
                let node = {};
                tree[propname].push(node);
                let xpath = currentjson[0][Object.keys(currentjson[0]).find(k => k.startsWith('xpath_'))];
                xpath = xpath ? xpath.substring(0, xpath.lastIndexOf('.')) : xpath;
                node['data-id'] = currentjson[0].hasOwnProperty(DB_ID) ? currentjson[0][DB_ID] : xpath;
                createTree(tree[propname], currentjson[0], 0, count, collections);
                if (currentjson.length > 1 && count.delete > 0) {
                    count.delete -= 1;
                    currentjson.splice(0, 1);
                }
            }
        }
    } else if (isNull(currentjson)) {
        tree[propname] = null;
    } else if (isObject(currentjson)) {
        if (collections.some(c => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
            tree[propname] = currentjson;
        } else {
            let node = tree[propname];
            if (!node) {
                node = tree;
            }
            Object.entries(currentjson).map(([k, v]) => {
                if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
                    node[k] = v;
                } else if (isNull(v)) {
                    node[k] = null;
                } else if (Array.isArray(v)) {
                    node[k] = [];
                    createTree(node, currentjson[k], k, count, collections);
                    if (node[k][0]?.hasOwnProperty('data-id')) {
                        node['data-id'] = node[k][0]['data-id'];
                    }
                } else if (isObject(v)) {
                    node[k] = {};
                    createTree(node, currentjson[k], k, count, collections);
                }
            })
        }
    }
}


export function addxpath(jsondata, xpath) {
    if (Array.isArray(jsondata)) {
        for (let i = 0; i < jsondata.length; i++) {
            let dataxpath = "[" + i + "]";
            if (xpath) {
                dataxpath = xpath + dataxpath;
            }
            _addxpath(jsondata[i], dataxpath)
        }
    } else if (isObject(jsondata)) {
        _addxpath(jsondata, xpath);
    }
    return jsondata;
}

function _addxpath(jsondata, xpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (isNull(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (Array.isArray(v)) {
            if (v.length > 0 && isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    let childxpath = xpath ? `${xpath}.${k}[${i}]` : `${k}[${i}]`;
                    addxpath(jsondata[k][i], childxpath);
                }
            } else {
                jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            }
        } else if (isObject(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            let childxpath = xpath ? xpath + '.' + k : k;
            addxpath(jsondata[k], childxpath)
        }
        return;
    });
}

export function clearxpath(jsondata) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            // remove data-id for repeated_root model_types
            if (k.startsWith('xpath_') || k === 'data-id') {
                delete jsondata[k];
            }
        } else if (Array.isArray(v)) {
            if (v.length > 0 && isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    clearxpath(jsondata[k][i]);
                }
            }
        } else if (isObject(v)) {
            clearxpath(jsondata[k])
        }
    });
    return jsondata;
}

function flattenObject(jsondata, object, collections, xpath, parentxpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            if (parentxpath && k !== 'data-id') {
                if (xpath && xpath === parentxpath) {
                    object[k] = v;
                } else {
                    object[parentxpath + '.' + k] = v;
                }
            } else {
                object[k] = v;
            }
        } else if (isNull(v)) {
            if (parentxpath) {
                if (xpath && xpath === parentxpath) {
                    object[k] = v;
                } else {
                    object[parentxpath + '.' + k] = v;
                }
            } else {
                object[k] = v;
            }
        } else if (Array.isArray(v)) {
            if (collections.some((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
                if (parentxpath) {
                    object[parentxpath + '.' + k] = v;
                } else {
                    object[k] = v;
                }
            } else if (v.length > 0) {
                let updatedParentxpath = parentxpath ? parentxpath + '.' + k : k;
                flattenObject(jsondata[k][0], object, collections, xpath, updatedParentxpath);
            }
        } else if (isObject(v)) {
            if (collections.some((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON")) {
                if (parentxpath) {
                    object[parentxpath + '.' + k] = v;
                } else {
                    object[k] = v;
                }
            } else {
                let updatedParentxpath = parentxpath ? parentxpath + '.' + k : k;
                flattenObject(jsondata[k], object, collections, xpath, updatedParentxpath);
            }
        }
    });
}

export function generateRowsFromTree(trees, collections, xpath) {
    let rows = [];
    trees.forEach((tree) => {
        let row = {};
        flattenObject(tree, row, collections, xpath);
        if (Object.keys(row).length > 0) {
            rows.push(row);
        }
    })
    return rows;
}

export function compareObjects(updated, original, current, xpath, diff = []) {
    Object.entries(current).map(([k, v]) => {
        if (primitiveDataTypes.includes(typeof (v))) {
            let updatedxpath = xpath ? xpath + '.' + k : k;
            if ((!get(original, updatedxpath) && get(original, updatedxpath) !== false && get(original, updatedxpath) !== 0) || !isEqual(get(updated, updatedxpath), get(original, updatedxpath))) {
                if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                let updatedxpath = xpath ? xpath + '.' + k + '[' + i + ']' : k + '[' + i + ']';
                if (primitiveDataTypes.includes(typeof (v[0]))) {
                    if ((!get(original, updatedxpath) && get(original, updatedxpath) !== false && get(original, updatedxpath) !== 0) || !isEqual(get(updated, updatedxpath), get(original, updatedxpath))) {
                        if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
                    }
                } else {
                    compareObjects(updated, original, current[k][i], updatedxpath, diff);
                }
            }
        } else if (isObject(v)) {
            let updatedxpath = xpath ? xpath + '.' + k : k;
            compareObjects(updated, original, current[k], updatedxpath, diff);
        }
    })
    return diff;
}

export function getNewItem(collections, abbreviated) {
    const abbreviatedKeyPath = abbreviated.split('^')[0].split(':').pop();
    const fields = abbreviatedKeyPath.split('-');
    let newItem = '';
    fields.forEach(field => {
        let key = field.split('.').pop();
        // DB_ID must be the last field in abbreviated key
        if (key === DB_ID) {
            newItem += NEW_ITEM_ID
        } else {
            let defaultValue = 'XXXX';
            let collection = collections.find(c => c.key === key);
            if (collection) {
                if (collection.placeholder) {
                    defaultValue = collection.placeholder;
                } else if (collection.default) {
                    defaultValue = collection.default;
                }
            }
            newItem += defaultValue + '-';
        }

    })
    return newItem;
}

// export function getIdFromAbbreviatedKey(abbreviated, abbreviatedKey) {
//     let abbreviatedSplit = abbreviated.split('-');
//     let idIndex = -1;
//     abbreviatedSplit.map((text, index) => {
//         if (text.indexOf(DB_ID) > 0) {
//             idIndex = index;
//         }
//     })
//     if (idIndex !== -1) {
//         let abbreviatedKeySplit = abbreviatedKey.split('-');
//         let abbreviatedKeyId = parseInt(abbreviatedKeySplit[idIndex]);
//         return abbreviatedKeyId;
//     } else {
//         // abbreviated key id not found. returning -1
//         return idIndex;
//     }
// }

export function getAbbreviatedKeyFromId(keyArray, abbreviated, id) {
    let abbreviatedKey;
    keyArray.forEach(key => {
        let keyId = getIdFromAbbreviatedKey(abbreviated, key);
        if (keyId === id) {
            abbreviatedKey = key;
        }
    })
    return abbreviatedKey;
}

export function getAlertBubbleCount(data, bubbleSourcePath) {
    let bubbleCount = 0;
    const bubbleSource = get(data, bubbleSourcePath);
    if (bubbleSource) {
        if (typeof bubbleSource === DATA_TYPES.NUMBER) {
            bubbleCount = bubbleSource;
        } else if (Array.isArray(bubbleSource)) {
            bubbleCount = bubbleSource.length;
        }
    }
    return bubbleCount;
}

export function getColorTypeFromPercentage(collection, percentage) {
    let color = COLOR_TYPES.DEFAULT;
    if (collection && collection.color) {
        let colorSplit = collection.color.split(',');
        for (let i = 0; i < colorSplit.length; i++) {
            let valueColorSet = colorSplit[i].trim();
            if (valueColorSet.indexOf('=') !== -1) {
                let [val, colorType] = valueColorSet.split('=');
                val = val.replace('%', '');
                try {
                    val = parseInt(val);
                    if (val === percentage) {
                        color = COLOR_TYPES[colorType];
                        break;
                    }
                } catch (e) {
                    break;
                }
            } else if (valueColorSet.indexOf('>') !== -1) {
                let [val, colorType] = valueColorSet.split('>');
                val = val.replace('%', '');
                try {
                    val = parseInt(val);
                    if (val < percentage) {
                        color = COLOR_TYPES[colorType];
                        break;
                    }
                } catch (e) {
                    break;
                }
            }
        }
    }
    return color;
}

export function getPriorityColorType(colorTypesSet) {
    let colorTypesArray = Array.from(colorTypesSet);
    if (colorTypesArray.length > 0) {
        colorTypesArray.sort(function (a, b) {
            if (COLOR_PRIORITY[a] > COLOR_PRIORITY[b]) {
                return -1;
            }
            return 1;
        })
        return colorTypesArray[0];
    } else {
        return COLOR_TYPES.DEFAULT;
    }
}

export function getAlertBubbleColor(data, collections, bubbleSourcePath, bubbleColorSourcePath) {
    // let alertBubbleColorKey = alertBubbleColorXpath.split('.').pop();
    // let collection = collections.find(col => col.key === alertBubbleColorKey);
    // let alertBubbleColorRelativePath = alertBubbleColorXpath.replace(alertBubbleSourceXpath, '');
    // let alertBubbleColorTypes = new Set();
    // if (get(data, alertBubbleSourceXpath) && get(data, alertBubbleSourceXpath).length > 0) {
    //     for (let i = 0; i < get(data, alertBubbleSourceXpath).length; i++) {
    //         let value = get(data, alertBubbleSourceXpath + '[' + i + ']' + alertBubbleColorRelativePath);
    //         let colorType = getColorTypeFromValue(collection, value);
    //         alertBubbleColorTypes.add(colorType);
    //     }
    // }
    // return getPriorityColorType(alertBubbleColorTypes);
    const collection = collections.find(col => col.tableTitle === bubbleColorSourcePath);
    if (collection) {
        const value = get(data, bubbleColorSourcePath);
        const colorType = getColorTypeFromValue(collection, value);
        return colorType;
    }
    return COLOR_TYPES.DEFAULT;
}

export function getObjectWithLeastId(objectArray) {
    objectArray = cloneDeep(objectArray);
    objectArray.sort(function (a, b) {
        if (a[DB_ID] > b[DB_ID]) {
            return 1;
        }
        return -1;
    });
    return objectArray[0];
}

export function getIconText(text) {
    let textSplit = text.split('_');
    let iconText = '';
    for (let i = 0; i < textSplit.length; i++) {
        iconText += textSplit[i][0].toUpperCase();
    }
    return iconText;
}

export function getSizeFromValue(value) {
    let size = value.split('_').pop();
    if (SIZE_TYPES.hasOwnProperty(size)) {
        return SIZE_TYPES[size];
    }
    return SIZE_TYPES.UNSPECIFIED;

}

export function getShapeFromValue(value) {
    let shape = value.split('_').pop();
    if (SHAPE_TYPES.hasOwnProperty(shape)) {
        return SHAPE_TYPES[shape];
    }
    return SHAPE_TYPES.UNSPECIFIED;
}

export function isValidJsonString(jsonString) {
    if (typeof (jsonString) !== DATA_TYPES.STRING) return false;
    jsonString = jsonString.replace(/\\/g, '');
    try {
        JSON.parse(jsonString);
    } catch (e) {
        return false;
    }
    return true;
}

export function hasxpath(data, xpath) {
    if (get(data, xpath)) return true;
    else {
        let value = get(data, xpath);
        if (value === 0 || value === false || value === '') return true;
    }
    return false;
}

// export function getTableColumns(collections, mode, enableOverride = [], disableOverride = [], showLess = [], collectionView = false, repeatedView = false) {
//     let tableColumns = collections
//         .map(collection => Object.assign({}, collection))
//         .map(collection => {
//             let fieldName = collection.tableTitle;
//             if (collectionView) {
//                 fieldName = collection.key;
//             }
//             if (enableOverride.includes(fieldName)) {
//                 collection.hide = true;
//             }
//             if (disableOverride.includes(fieldName)) {
//                 collection.hide = false;
//             }
//             if (showLess.includes(fieldName)) {
//                 collection.showLess = true;
//             }
//             if (repeatedView) {
//                 collection.rootLevel = false;
//             }
//             return collection;
//         })
//         .filter(collection => {
//             // add all exclusion cases
//             if (collection.serverPopulate && mode === MODES.EDIT) {
//                 return false;
//             } else if (primitiveDataTypes.includes(collection.type)) {
//                 return true;
//             } else if (collection.abbreviated && collection.abbreviated === "JSON") {
//                 return true;
//             } else if (collection.type === 'button' && !collection.rootLevel) {
//                 if (mode === MODES.EDIT && collection.button.read_only) {
//                     return false;
//                 }
//                 return true;
//             } else if (collection.type === 'progressBar') {
//                 return true;
//             } else if (collection.type === 'alert_bubble') {
//                 return true;
//             }
//             // TODO: what other cases are ignored?
//             return false;
//         })

//     return tableColumns;
// }

// export function getGroupedTableColumns(columns, maxRowSize, rows, groupBy = [], mode, collectionView = false) {
//     let tableColumns = []
//     let maxSequence = 0;
//     columns.forEach(column => {
//         if (column.sequenceNumber > maxSequence) {
//             maxSequence = column.sequenceNumber;
//         }
//     })
//     for (let i = 0; i < maxRowSize; i++) {
//         const updatedColumns = columns.map(column => {
//             column = Object.assign({}, column);
//             column.sourceIndex = i;
//             column.sequenceNumber = column.sequenceNumber + i * maxSequence;
//             return column;
//         })
//         tableColumns = [...tableColumns, ...updatedColumns];
//     }
//     if (mode === MODES.READ && groupBy && groupBy.length > 0) {
//         const commonColumns = [];
//         columns.forEach(column => {
//             if (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble') {
//                 return;
//             }
//             if (column.noCommonKey) {
//                 return;
//             }
//             let fieldName = column.tableTitle;
//             if (collectionView) {
//                 fieldName = column.key;
//             }
//             let found = true;
//             for (let i = 0; i < rows.length; i++) {
//                 const groupedRow = rows[i];
//                 let firstValue = null;
//                 for (let j = 0; j < maxRowSize; j++) {
//                     const value = groupedRow?.[j]?.[fieldName];
//                     if (!(value === null || value === undefined || value === '')) {
//                         firstValue = value;
//                         break;
//                     }
//                 }
//                 let matched = true;
//                 for (let j = 0; j < groupedRow.length; j++) {
//                     const value = groupedRow[j][fieldName];
//                     if (!(value === null || value === undefined || value === '')) {
//                         if (value !== firstValue) {
//                             matched = false;
//                             break;
//                         }
//                     }
//                 }
//                 if (!matched) {
//                     found = false;
//                     break;
//                 }
//             }
//             if (found) {
//                 commonColumns.push(fieldName);
//             }
//         })
//         tableColumns = tableColumns.filter(column => {
//             let fieldName = column.tableTitle;
//             if (collectionView) {
//                 fieldName = column.key;
//             }
//             if (commonColumns.includes(fieldName) && column.sourceIndex !== 0) {
//                 // exclude all common columns from non-zeroth source index
//                 return false;
//             }
//             return true;
//         })
//         tableColumns = tableColumns.map(column => {
//             let fieldName = column.tableTitle;
//             if (collectionView) {
//                 fieldName = column.key;
//             }
//             if (commonColumns.includes(fieldName)) {
//                 column.commonGroupKey = true;
//             }
//             if (groupBy.includes(fieldName)) {
//                 column.joinKey = true;
//             }
//             return column;
//         })
//     }
//     return tableColumns;
// }

// export function getCommonKeyCollections(rows, tableColumns, hide = true, collectionView = false, repeatedView = false, showLess = false) {
//     if (rows.length > 1) {
//         // exclude column with 'noCommonKey' as it cannot be added in common key
//         tableColumns = tableColumns.map(column => Object.assign({}, column)).filter(column => !column.noCommonKey);
//     }
//     let commonKeyCollections = [];
//     if (rows.length === 1 && (collectionView || repeatedView)) {
//         const hasButtonType = tableColumns.find(obj => obj.type === 'button');
//         if (hasButtonType) {
//             tableColumns.forEach(column => {
//                 if (hide && column.hide) return;
//                 if (column.joinKey || column.commonGroupKey) return;
//                 if (showLess && column.showLess) return;
//                 let fieldName = column.tableTitle;
//                 if (collectionView) {
//                     if (rows.length > 1 && (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
//                         return;
//                     }
//                     fieldName = column.key;
//                 }
//                 const value = rows[0][column.sourceIndex]?.[fieldName];
//                 if (!column.noCommonKey) {
//                     if (value === null || value === undefined) {
//                         commonKeyCollections.push(column);
//                     } else if (value === 0 && !column.displayZero) {
//                         commonKeyCollections.push(column);
//                     }
//                 }
//             })
//             return commonKeyCollections;
//         }
//     }
//     if (rows.length > 0) {
//         tableColumns.map((column) => {
//             if (hide && column.hide) return;
//             if (column.joinKey || column.commonGroupKey) return;
//             if (showLess && column.showLess) return;
//             let fieldName = column.tableTitle;
//             if (collectionView) {
//                 if (rows.length > 1 && (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
//                     return;
//                 }
//                 fieldName = column.key;
//             }
//             let found = true;
//             let firstValue = null;
//             for (let i = 0; i < rows.length; i++) {
//                 const value = rows[i][column.sourceIndex]?.[fieldName];
//                 if (!(value === null || value === undefined || value === '')) {
//                     firstValue = value;
//                     break;
//                 }
//             }
//             // const value = rows[0][column.sourceIndex]?.[fieldName];
//             // for (let i = 1; i < rows.length; i++) {
//             for (let i = 0; i < rows.length; i++) {
//                 const value = rows[i][column.sourceIndex]?.[fieldName];
//                 if (value !== firstValue && firstValue !== null) {
//                     if (column.type === DATA_TYPES.NUMBER && column.zeroAsNone && firstValue === 0 && value === null) {
//                         continue;
//                     } else {
//                         found = false;
//                         break;
//                     }
//                 }
//                 // if (!(value === null || value === undefined || value === '')) {
//                 //     if (value !== firstValue) {
//                 //         found = false;
//                 //         break;
//                 //     }
//                 // }
//                 // if (rows[i][column.sourceIndex] && rows[i+1][column.sourceIndex]) {
//                 //     if (!isEqual(rows[i][column.sourceIndex][fieldName], rows[i + 1][column.sourceIndex][fieldName])) {
//                 //         const values = [rows[i][column.sourceIndex][fieldName], rows[i + 1][column.sourceIndex][fieldName]];
//                 //         for (let i = 0; i < values.length; i++) {
//                 //             let val = values[i];
//                 //             if (val) {
//                 //                 if (typeof val === DATA_TYPES.STRING) {
//                 //                     val = val.trim();
//                 //                 }
//                 //             }
//                 //             if (![null, undefined, ''].includes(val)) {
//                 //                 found = false;
//                 //                 break;
//                 //             }
//                 //         }
//                 //     }
//                 // }

//                 // if (rows[i][column.sourceIndex]?.[fieldName] !== value) {
//                 //     found = false;
//                 // }

//                 if (!found) {
//                     break;
//                 }
//             }
//             if (found) {
//                 let collection = column;
//                 collection.value = firstValue;
//                 commonKeyCollections.push(collection);
//             }
//             return column;
//         })
//     }
//     return commonKeyCollections;
// }

export function getTableRowsFromData(collections, data, xpath) {
    let trees = generateRowTrees(cloneDeep(data), collections, xpath);
    let rows = generateRowsFromTree(trees, collections, xpath);
    return rows;
}

export function getTableRows(collections, mode, originalData, data, xpath, repeatedView = false) {
    let tableRows = [];
    if (mode === MODES.READ) {
        if (repeatedView) {
            tableRows = getTableRowsFromData(collections, data, xpath);
        } else {
            tableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
        }
    } else {
        let originalDataTableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
        tableRows = getTableRowsFromData(collections, data, xpath);

        // combine the original and modified data rows
        for (let i = 0; i < originalDataTableRows.length; i++) {
            if (i < tableRows.length) {
                if (originalDataTableRows[i]['data-id'] !== tableRows[i]['data-id']) {
                    if (!tableRows.find(row => row['data-id'] === originalDataTableRows[i]['data-id'])) {
                        let row = originalDataTableRows[i];
                        row['data-remove'] = true;
                        tableRows.splice(i, 0, row);
                    }
                }
            } else {
                let row = originalDataTableRows[i];
                row['data-remove'] = true;
                tableRows.splice(i, 0, row);
            }
        }
        for (let i = 0; i < tableRows.length; i++) {
            if (!originalDataTableRows.find(row => row['data-id'] === tableRows[i]['data-id'])) {
                tableRows[i]['data-add'] = true;
            }
        }
    }
    return tableRows;
}

export function getValueFromReduxStoreFromXpath(state, xpath) {
    let sliceName = toCamelCase(xpath.split('.')[0]);
    let propertyName = 'modified' + capitalizeCamelCase(xpath.split('.')[0]);
    let propxpath = xpath.substring(xpath.indexOf('.') + 1);
    return getValueFromReduxStore(state, sliceName, propertyName, propxpath);
}

export function getValueFromReduxStore(state, sliceName, propertyName, xpath) {
    if (state && state.hasOwnProperty(sliceName)) {
        let slice = state[sliceName];
        if (slice) {
            let object = slice[propertyName];
            if (object && hasxpath(object, xpath)) {
                return get(object, xpath);
            }
        }
        return null;
    }
}

export function normalise(value, max, min) {
    if (typeof (value) === DATA_TYPES.NUMBER && typeof (min) === DATA_TYPES.NUMBER && typeof (max) === DATA_TYPES.NUMBER) {
        let percentage = ((value - min) * 100) / (max - min);
        return percentage > 100 ? 100 : percentage;
    }
    return 0;
}

export function getHoverTextType(value) {
    let hoverType = value.trim();
    // if (HOVER_TEXT_TYPES.hasOwnProperty(hoverType)) {
    //     return HOVER_TEXT_TYPES[hoverType];
    // }
    // return HOVER_TEXT_TYPES.NONE;
    return hoverType;
}

export function getParentSchema(schema, currentSchemaName) {
    let parentSchema;
    Object.keys(get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {
        let current = get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);
        if (current.type === DATA_TYPES.OBJECT && has(current.properties, currentSchemaName)) {
            parentSchema = current;
        }
        return;
    })
    return parentSchema;
}

export function isAllowedNumericValue(value, min, max) {
    if (min !== undefined && max !== undefined) {
        return min <= value && value <= max;
    } else if (min !== undefined) {
        return min <= value;
    } else if (max !== undefined) {
        return value <= max;
    }
    return true;
}

export function getXpathKeyValuePairFromObject(object, dict = {}) {
    Object.entries(object).map(([k, v]) => {
        if ([DATA_TYPES.STRING, DATA_TYPES.BOOLEAN, DATA_TYPES.NUMBER].includes(typeof (v))) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (isNull(v)) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                getXpathKeyValuePairFromObject(object[k][i], dict);
            }
        } else if (isObject(v)) {
            getXpathKeyValuePairFromObject(object[k], dict);
        }
        return;
    });
    return dict;
}

// export function getComparator(order, orderBy) {
//     return order === 'desc'
//         ? (a, b) => descendingComparator(a, b, orderBy)
//         : (a, b) => -descendingComparator(a, b, orderBy);
// }

// export function descendingComparator(a, b, orderBy) {
//     if (a[orderBy] === undefined || a[orderBy] === null) {
//         return -1;
//     }
//     if (b[orderBy] === undefined || b[orderBy] === null) {
//         return 1;
//     }
//     if (b[orderBy] < a[orderBy]) {
//         return -1;
//     }
//     if (b[orderBy] > a[orderBy]) {
//         return 1;
//     }
//     return 0;
// }

// This method is created for cross-browser compatibility, if you don't
// need to support IE11, you can use Array.prototype.sort() directly
// export function stableSort(array, comparator) {
//     const stabilizedThis = array.map((el, index) => [el, index]);
//     stabilizedThis.sort((a, b) => {
//         const order = comparator(a[0], b[0]);
//         if (order !== 0) {
//             return order;
//         }
//         return a[1] - b[1];
//     });
//     return stabilizedThis.map((el) => el[0]);
// }

export function getErrorDetails(error) {
    return {
        code: error.code,
        message: error.message,
        detail: error.response ? error.response.data ? error.response.data.detail : '' : '',
        status: error.response ? error.response.status : ''
    }
}

export function createObjectFromDict(obj, dict = {}) {
    let objArray = [];
    Object.entries(dict).map(([k, v]) => {
        let updatedObj = createObjectFromXpathDict(obj, k, v);
        objArray.push(updatedObj);
        return;
    })
    let mergedObj = {};
    objArray.forEach(obj => {
        mergedObj = mergeObjects(mergedObj, obj);
    })
    // return _.merge(...objArray);
    return mergedObj;
}

export function createObjectFromXpathDict(obj, xpath, value) {
    let o = { [DB_ID]: obj[DB_ID] };
    let currentObj = o;
    let currentXpath;
    xpath.split('.').forEach((f, i) => {
        currentXpath = currentXpath ? currentXpath + '.' + f : f;
        let fieldName = f.indexOf('[') === -1 ? f : f.substring(0, f.indexOf('['));
        let fieldType = f.indexOf('[') === -1 ? DATA_TYPES.OBJECT : DATA_TYPES.ARRAY;
        Object.keys(currentObj).forEach(k => {
            if (k !== DB_ID) {
                delete currentObj[k];
            }
        })
        if (fieldType === DATA_TYPES.OBJECT) {
            currentObj[fieldName] = cloneDeep(get(obj, currentXpath));
            if (i === xpath.split('.').length - 1) {
                currentObj[fieldName] = value;
            }
            currentObj = currentObj[fieldName];
        } else {
            currentObj[fieldName] = [cloneDeep(get(obj, currentXpath))];
            currentObj = currentObj[fieldName][0];
        }
    })
    return o;
}

export function applyWebSocketUpdate(storedArray, updatedObj, uiLimit, isAlertModel = false) {
    const updatedArray = storedArray.filter(obj => obj[DB_ID] !== updatedObj[DB_ID]);
    // create or update case
    if (Object.keys(updatedObj).length !== 1) {
        const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);
        // obj with DB_ID already exists. update obj case. update the existing obj at the index
        if (idx !== -1) {
            // ws update received for alert model. if alert is dismissed, return the filtered array
            if (isAlertModel && updatedObj.dismiss) {
                return updatedArray;
            } else {  // either not alert model or alert not dismissed or received ws update on existing obj. 
                updatedArray.splice(idx, 0, updatedObj);
            }
        } else {
            if (uiLimit) {
                // if uiLimit is positive, remove the top object and add the latest obj at the end
                // otherwise remove the last object and add the latest obj at the top
                if (uiLimit >= 0) {
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.shift();
                    }
                    updatedArray.push(updatedObj);
                } else {  // negative uiLimit
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.pop();
                    }
                    updatedArray.splice(0, 0, updatedObj);
                }
            } else {
                updatedArray.push(updatedObj);
            }
        }
    }  // else not required - obj is deleted. already filtered above
    return updatedArray;
}

export function applyWebSocketUpdateForAlertModel(storedArray, updatedObj, uiLimit, modelName, id = null) {
    const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);
    const updatedArray = cloneDeep(storedArray);

    // obj is created or updated
    if (Object.keys(updatedObj).length !== 1) {
        // obj already exists. received update on obj
        if (idx !== -1) {
            const storedObj = storedArray[idx];
            // removing stored
            updatedArray.splice(idx, 1);
            AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
            // existing alert is dismissed/cleared
            if (updatedObj.dismiss) {
                return updatedArray;
            } else {  // alert is updated (except dismiss)
                const newIdx = AlertCache.getSeverityIndex(modelName, id, updatedObj.severity);
                updatedArray.splice(newIdx, 0, updatedObj);
                AlertCache.updateSeverityCache(modelName, id, updatedObj.severity, 1);
                return updatedArray;
            }
        } else {  // new obj is created
            // uiLimit (array max size) limit is set
            if (uiLimit) {
                // positive array size limit
                if (uiLimit >= 0) {
                    if (updatedArray.length >= uiLimit) {
                        const storedObj = updatedArray[0];
                        updatedArray.shift();
                        AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
                    }
                } else {  // negative array size limit
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        const storedObj = updatedArray[updatedArray.length - 1];
                        updatedArray.pop();
                        AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
                    }
                }
            }
            const newIdx = AlertCache.getSeverityIndex(modelName, id, updatedObj.severity);
            updatedArray.splice(newIdx, 0, updatedObj);
            AlertCache.updateSeverityCache(modelName, id, updatedObj.severity, 1);
            return updatedArray;
        }
    } else {  // obj is deleted
        if (idx !== -1) {
            const storedObj = storedArray[idx];
            // removing stored
            updatedArray.splice(idx, 1);
            AlertCache.updateSeverityCache(modelName, id, storedObj.severity, -1);
        } else {
            console.error('applyWebSocketUpdateForAlertModel failed. received delete update for id: ' + updatedObj[DB_ID] + ', but id not found in storedArray');
        }
    }
    return updatedArray;
}

// export function applyGetAllWebsocketUpdate(arr, obj, uiLimit) {
//     let updatedArr = arr.filter(o => o[DB_ID] !== obj[DB_ID]);
//     // if obj is not deleted object
//     if (Object.keys(obj) !== 1) {
//         let index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
//         // if index is not equal to -1, it is updated obj. If updated, replace the obj at the index
//         if (index !== -1) {
//             updatedArr.splice(index, 0, obj);
//         } else {
//             updatedArr.push(obj);
//         }
//     }
//     return updatedArr;
// }

// export function applyFilter(arr, filters = [], collectionView = false, collections) {
//     if (arr && arr.length > 0) {
//         let updatedArr = cloneDeep(arr);
//         const filterDict = getFilterDict(filters);
//         Object.keys(filterDict).forEach(key => {
//             let values = filterDict[key].split(",").map(val => val.trim()).filter(val => val !== "");
//             updatedArr = updatedArr.filter(data => values.includes(String(get(data, key))));
//         })
//         return updatedArr;
//     }
//     return [];
// }

// export function floatToInt(value) {
//     /* 
//     Function to convert floating point numbers to integer.
//     value: integer or floating point number
//     */
//     if (typeof value === DATA_TYPES.NUMBER) {
//         if (Number.isInteger(value)) {
//             return value;
//         } else {
//             // floating point number
//             if (value > 0) {
//                 return Math.floor(value);
//             } else {
//                 return Math.ceil(value);
//             }
//         }
//     }

//     return value;
// }

export function groupCommonKeys(commonKeys) {
    let groupStart = false;
    commonKeys = commonKeys.map((commonKeyObj, idx) => {
        if (commonKeyObj.parentxpath) {
            if (!groupStart) {
                groupStart = true;
                commonKeyObj.groupStart = true;
            }
            if (groupStart) {
                let nextIdx = idx + 1;
                if (nextIdx < commonKeys.length) {
                    let nextCommonKeyObj = commonKeys[nextIdx];
                    if (commonKeyObj.parentxpath !== nextCommonKeyObj.parentxpath) {
                        commonKeyObj.groupEnd = true;
                        groupStart = false;
                    }
                } else {
                    commonKeyObj.groupEnd = true;
                    groupStart = false;
                }
            }
        }
        // remove grouping if only one element is present in group
        if (commonKeyObj.groupStart && commonKeyObj.groupEnd) {
            delete commonKeyObj.groupStart;
            delete commonKeyObj.groupEnd;
        }
        return commonKeyObj;
    })
    return commonKeys;
}

function mergeObjects(obj1, obj2) {
    const mergedObj = {};

    for (const prop in obj1) {
        if (obj1.hasOwnProperty(prop)) {
            if (Array.isArray(obj1[prop]) && Array.isArray(obj2[prop])) {
                mergedObj[prop] = mergeArrays(obj1[prop], obj2[prop]);
            } else if (typeof obj1[prop] === DATA_TYPES.OBJECT && typeof obj2[prop] === DATA_TYPES.OBJECT) {
                mergedObj[prop] = mergeObjects(obj1[prop], obj2[prop]);
            } else {
                mergedObj[prop] = obj1[prop];
            }
        }
    }

    for (const prop in obj2) {
        if (obj2.hasOwnProperty(prop) && !mergedObj.hasOwnProperty(prop)) {
            mergedObj[prop] = obj2[prop];
        }
    }

    return mergedObj;
}

function mergeArrays(arr1, arr2) {
    const mergedArr = [...arr1];

    for (const item2 of arr2) {
        const matchingItem = mergedArr.find((item1) => item1[DB_ID] === item2[DB_ID]);
        if (matchingItem) {
            const index = mergedArr.indexOf(matchingItem);
            mergedArr[index] = mergeObjects(matchingItem, item2);
        } else {
            mergedArr.push(item2);
        }
    }

    return mergedArr;
}

// export function roundNumber(value, precision = FLOAT_POINT_PRECISION) {
//     /* 
//     Function to round floating point numbers.
//     value: floating point number
//     precision: decimal digits to round off to. default 2 (FLOAT_POINT_PRECISION)
//     */
//     if (typeof value === DATA_TYPES.NUMBER) {
//         if (Number.isInteger(value) || precision === 0) {
//             return value;
//         } else {
//             return +value.toFixed(precision);
//         }
//     }
//     return value;
// }

// export function getLocalizedValueAndSuffix(metadata, value) {
//     /* 
//     Function to normalize numbers and return adornments if any
//     metadata: contains all properties of the field
//     value: field value
//     */
//     let adornment = '';

//     if (typeof value !== DATA_TYPES.NUMBER) {
//         return [adornment, value];
//     }
//     if (metadata.numberFormat) {
//         if (metadata.numberFormat.includes('%')) {
//             adornment = ' %';
//         } else if (metadata.numberFormat.includes('bps')) {
//             adornment = ' bps';
//         }
//     }
//     if (metadata.displayType === DATA_TYPES.INTEGER) {
//         return [adornment, floatToInt(value)]
//     }
//     if (metadata.numberFormat && metadata.numberFormat.includes('.')) {
//         let precision = metadata.numberFormat.split(".").pop();
//         precision *= 1;
//         value = roundNumber(value, precision);
//     } else {
//         value = roundNumber(value);
//     }

//     return [adornment, value];
// }

export function excludeNullFromObject(obj) {
    /* 
    Function to remove null values from mutable object inplace.
    obj: mutable object
    */
    if (isObject(obj)) {
        for (const key in obj) {
            if (obj[key] === null || (typeof obj[key] === DATA_TYPES.STRING && obj[key].includes('_UNSPECIFIED'))) {
                // delete key with null values or enum with UNSPECIFIED values
                delete obj[key];
            } else if (isObject(obj[key])) {
                excludeNullFromObject(obj[key]);
            } else if (Array.isArray(obj[key])) {
                for (let i = 0; i < obj[key].length; i++) {
                    excludeNullFromObject(obj[key][i]);
                }
            }
            // else not required
        }
    } else if (Array.isArray(obj)) {
        obj.forEach(o => {
            excludeNullFromObject(o);
        })
    }
    // else not required
}

function getAllObjectPaths(obj, prefix = '', paths = new Set()) {
    for (const key in obj) {
        const currentPath = prefix ? `${prefix}.${key}` : key;

        if (typeof obj[key] === 'object' && obj[key] !== null) {
            if (Array.isArray(obj[key])) {
                obj[key].forEach((item) => {
                    getAllObjectPaths(item, currentPath, paths);
                })
            } else {
                getAllObjectPaths(obj[key], currentPath, paths);
            }
        } else {
            paths.add(currentPath);  // Add path for primitive values
        }
    }
    return Array.from(paths);  // Covert set to array
}

export function compareJSONObjects(obj1, obj2, fieldsMetadata, isCreate = false) {
    /* 
    Function to compare two objects and clear null fields from diff
    obj1: initial / original object
    obj2: currrent object
    */
    if (!checkConstraints(obj1, obj2)) {
        return null;
    }
    let diff = {};
    if (isObject(obj1) && isObject(obj2)) {
        diff = getObjectsDiff(obj1, obj2);
    } else if (isObject(obj2)) {
        diff = obj2;
    }
    if (Object.keys(diff).length > 0) {
        // add the object ID if diff found and ID exists on initial object
        if (DB_ID in obj1) {
            diff[DB_ID] = obj1[DB_ID];
        } else {
            // removing null fields from diff if no ID exists on initial object
            excludeNullFromObject(diff);
        }
    }
    if (fieldsMetadata) {
        let subFieldsMetadata = [];
        fieldsMetadata
            .filter((meta) => meta.subCollections)
            .forEach((meta) => {
                subFieldsMetadata = [...subFieldsMetadata, ...meta.subCollections];
            })
        const combinedFieldsMetadata = [...fieldsMetadata, ...subFieldsMetadata];
        const paths = getAllObjectPaths(diff);
        for (const path of paths) {
            // ignore DB_ID
            if (path === DB_ID) {
                continue;
            }

            const metadata = combinedFieldsMetadata.find(col => col.tableTitle === path);

            if (!metadata) {
                const err_ = `ERROR: no collection obj (metadata) found for path: ${path}, likely UI bug. Please send screenshot to DEV for investigation`;
                console.error(err_);
                alert(err_);
                diff = null;
                return;
            }  // else not required - collection obj exists

            if (metadata.key === DB_ID) {
                continue;
            }

            if (metadata.serverPopulate) {
                const err_ = `CRITICAL: Update request discarded, unmodifiable field found in patch update for path: ${path}, likely UI bug. Please send screenshot to DEV for investigation`;
                console.error(err_);
                alert(err_);
                diff = null;
                return;
            }  // else not required - field is modifiable from UI
        }
    }
    return diff;
}

export function getObjectsDiff(obj1, obj2) {
    /* 
    Function to get difference between two objects.
    obj1: initial object
    obj2: current object
    */

    function compareArrays(arr1, arr2, parentKey) {
        /* 
        Function to compare two arrays containing items of type object.
        arr1: array of initial object
        arr2: array of current object
        */
        let arrDiff = [];

        arr1.forEach(element1 => {
            if (element1 instanceof Object && DB_ID in element1) {
                const found = arr2.some(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
                if (!found) {
                    // deleted item in array. store the array object ID in the diff
                    arrDiff.push({ [DB_ID]: element1[DB_ID] });
                } else {
                    // array object found with matching object ID. compare the nested object
                    let element2 = arr2.find(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
                    let nestedDiff = getObjectsDiff(element1, element2);
                    if (!isEmpty(nestedDiff)) {
                        // store the diff along with the nested object ID
                        arrDiff.push({ [DB_ID]: element1[DB_ID], ...nestedDiff });
                    }
                }
            }
        });

        arr2.forEach(element2 => {
            if (element2 instanceof Object && !(DB_ID in element2)) {
                // new item in the array. store the entire item in diff
                arrDiff.push(element2);
            }
            // else {
            //    // compare arrays of primitive data types
            //    if (!isEqual(arr1, arr2)) {
            //        arrDiff = arr2;
            //    }
            //
            //}
        })

        return arrDiff;
    }

    let diff = {};

    if (obj1 instanceof Object) {
        for (const key in obj1) {
            if (obj2 instanceof Object && obj2.hasOwnProperty(key)) {
                if (obj1[key] instanceof Array) {
                    if (obj2[key] instanceof Array) {
                        const arrDiff = compareArrays(obj1[key], obj2[key]);
                        if (!isEmpty(arrDiff)) {
                            diff[key] = arrDiff;
                        }
                        // else not required: no difference found
                    } else {
                        diff[key] = obj2[key];
                    }
                } else if (obj1[key] instanceof Object) {
                    if (obj2[key] instanceof Object) {
                        const nestedDiff = getObjectsDiff(obj1[key], obj2[key]);
                        if (!isEmpty(nestedDiff)) {
                            diff[key] = nestedDiff;
                        }
                        // else not required: no difference found
                    } else {
                        diff[key] = obj2[key];
                    }
                } else if (obj1[key] !== obj2[key]) {
                    diff[key] = obj2[key];
                }
            } else {
                diff = obj2;
            }
        }
    }

    if (obj2 instanceof Object) {
        for (const key in obj2) {
            if (obj1 instanceof Object && !obj1.hasOwnProperty(key)) {
                if (!diff.hasOwnProperty(key)) {
                    diff[key] = obj2[key];
                }
            }
        }
    }

    return diff;
}

export function validateConstraints(metadata, value, min, max) {
    /* 
    Function to check if value violates any constraints on the field.
    metadata: contains all properties (and constraints) of the field
    value: field value
    min: min limit if any
    max: max limit if any
    */
    const errors = [];

    // disabled ignoring constraint checks on serverPopulate field
    // if (metadata.serverPopulate) {
    //     // if field is populated from server, ignore constaint checks
    //     return null;
    // }

    // Treat empty strings as null or unset
    if (value === '') {
        value = null;
    }
    // Check if required field is missing
    if (metadata.required) {
        if (value === null) {
            errors.push(Message.REQUIRED_FIELD);
        }
        // else not required: value is set
    }
    // Check if enum field has "UNSPECIFIED" value
    if (metadata.type === DATA_TYPES.ENUM && metadata.required) {
        if (value && value.includes('UNSPECIFIED')) {
            errors.push(Message.UNSPECIFIED_FIELD);
        }
        // else not required: value is set
    }
    // Check if field violates minimum requirement    
    if (typeof min === DATA_TYPES.NUMBER) {
        if (value !== undefined && value !== null && value < min) {
            errors.push(Message.MIN + ': ' + min);
        }
    }
    // Check if field violates maximum requirement
    if (typeof max === DATA_TYPES.NUMBER) {
        if (value !== undefined && value !== null && value > max) {
            errors.push(Message.MAX + ': ' + max);
        }
    }

    // If no constraints are violated, return null
    return errors.length ? errors.join(', ') : null;
}

export function removeRedundantFieldsFromRows(rows) {
    rows = rows.map(row => {
        Object.keys(row).forEach(key => {
            if (key.includes('xpath')) {
                delete row[key];
            }
            // if (key === 'data-id') {
            //     delete row[key];
            // }
        })
        return row;
    })
    return rows;
}

export function getRowsFromAbbreviatedItems(items, itemsData, itemFieldProperties, abbreviation, loadedProps) {
    const rows = [];
    if (items) {
        items.map((item, i) => {
            let row = {};
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            let metadata = itemsData.find(metadata => get(metadata, DB_ID) === id);
            row['data-id'] = id;
            itemFieldProperties.forEach(c => {
                let value = null;
                if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.find(col => col.tableTitle === xpath);
                        let val = get(metadata, xpath);
                        if (val === undefined || val === null) {
                            val = "";
                        }
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                        if (typeof v === DATA_TYPES.NUMBER && collection.type === DATA_TYPES.NUMBER) {
                            v = v.toLocaleString();
                        }
                        val = v + numberSuffix;
                        return val;
                    })
                    if (loadedProps.microSeparator) {
                        value = value.join(loadedProps.microSeparator);
                    } else {
                        value = value.join("-");
                    }
                } else {
                    value = get(metadata, c.xpath);
                    if (value === undefined || value === null) {
                        value = null;
                    }
                    let [, v] = getLocalizedValueAndSuffix(c, value);
                    value = v;
                }
                row[c.xpath] = value;
            })
            rows.push(row);
        })
    }
    return rows;
}

export function compareNCheckNewArrayItem(obj1, obj2) {
    for (const key in obj1) {
        if (obj1[key] instanceof Array && obj2[key] instanceof Array) {
            if (obj1[key].length !== obj2[key].length) {
                return true;
            }
            for (let i = 0; i < obj1[key].length; i++) {
                if (obj1[key] instanceof Object) {
                    compareNCheckNewArrayItem(obj1[key], obj2[key]);
                }
            }
        } else if (obj1[key] instanceof Object && obj2[key] instanceof Object) {
            compareNCheckNewArrayItem(obj1[key], obj2[key]);
        }
    }
    return false;
}

export function formatJSONObjectOrArray(json, fieldProps, truncateDateTime = false) {

    function formatJSONArray(arr, fieldProps, truncateDateTime) {
        for (let i = 0; i < arr.length; i++) {
            if (arr[i] instanceof Object) {
                formatJSONObjectOrArray(arr[i], fieldProps, truncateDateTime);
            }
        }
    }

    if (json instanceof Array) {
        formatJSONArray(json, fieldProps, truncateDateTime);
    } else if (json instanceof Object) {
        for (const key in json) {
            if (key.includes('xpath')) {
                continue;
            }
            const prop = fieldProps.find(p => p.key === key);
            if (prop) {
                if (json[key] instanceof Array) {
                    formatJSONArray(json[key], fieldProps, truncateDateTime);
                } else if (json[key] instanceof Object) {
                    formatJSONObjectOrArray(json[key], fieldProps, truncateDateTime);
                } else if (prop.type === DATA_TYPES.DATE_TIME) {
                    if (json[key]) {
                        const dateTimeWithTimezone = getDateTimeFromInt(json[key]);
                        if (prop.displayType === 'datetime') {
                            json[key] = dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
                        } else {
                            json[key] = dateTimeWithTimezone.isSame(dayjs(), 'day') ? dateTimeWithTimezone.format('HH:mm:ss.SSS') : dateTimeWithTimezone.format('YYYY-MM-DD HH:mm:ss.SSS');
                        }
                    }
                } else if (typeof json[key] === DATA_TYPES.NUMBER) {
                    const [suffix, v] = getLocalizedValueAndSuffix(prop, json[key]);
                    json[key] = v.toLocaleString() + suffix;
                }
                if (prop.hide) {
                    delete json[key];
                }
            }
        }
    }
}

export function getWidgetOptionById(widgetOptions, id, isIdBound = false) {
    let widgetOption = cloneDeep(widgetOptions[0]);
    if (isIdBound) {
        const dataElement = widgetOptions.find(data => data.hasOwnProperty('bind_id_val') && String(data.bind_id_val) === String(id));
        if (dataElement) {
            widgetOption = cloneDeep(dataElement);
        } else {
            widgetOption.bind_id_val = String(id);
        }
    }
    // widgetOption = cloneDeep(widgetOption);
    if (!widgetOption.enable_override) {
        widgetOption.enable_override = [];
    }
    if (!widgetOption.disable_override) {
        widgetOption.disable_override = [];
    }
    for (const key in widgetOption) {
        if (widgetOption[key] === null) {
            delete widgetOption[key];
        }
    }
    return widgetOption;
}

export function getWidgetTitle(widgetOption, widgetSchema, widgetName, data) {
    if (widgetSchema.widget_ui_data_element.hasOwnProperty('dynamic_widget_title_fld')) {
        const dynamicWidgetTitleField = widgetSchema.widget_ui_data_element.dynamic_widget_title_fld;
        const name = dynamicWidgetTitleField.split('.')[0];
        if (name === widgetName) {
            const fieldxpath = dynamicWidgetTitleField.substring(dynamicWidgetTitleField.indexOf('.') + 1);
            const value = get(data, fieldxpath);
            if (value) {
                return value;
            }
        }
        // TODO: fetching dynamic name for other widget fields
    }
    return widgetSchema.hasOwnProperty('title') ? widgetSchema.title : widgetName;
}

export function hasOwnProperty(obj, property) {
    /* extended hasOwnProperty check with check for null values */
    if (obj.hasOwnProperty(property)) {
        if (obj[property] !== null && obj[property] !== undefined) {
            return true;
        }
    }
    return false;
}

export function getChartOption(chartDataObj) {
    chartDataObj = cloneDeep(chartDataObj);
    if (chartDataObj && Object.keys(chartDataObj).length > 0) {
        chartDataObj.xAxis.forEach(axis => {
            delete axis[DB_ID];
        })
        chartDataObj.yAxis.forEach(axis => {
            delete axis[DB_ID];
        })
        chartDataObj.series.forEach(series => {
            delete series[DB_ID];
        })
        return chartDataObj;
    } else {
        return { xAxis: [], yAxis: [], series: [] };
    }
}

const ChartAxisType = {
    CATEGORY: 'category', // for string data type
    TIME: 'time', // for time series
    VALUE: 'value' // for numeric data type
}

function getChartAxisTypeAndName(collections, axisField, isCollectionType = false) {
    /* 
        Params:
        - collections (Array[Object]): list of dict of widget field and their attributes
        - axisField (String): axis field name or xpath
        - isCollectionType (Boolean): true if widget is of collection type else false
    */
    if (!collections) {
        throw new Error('getChartAxisTypeAndName failed. collections list is null or undefined, collections: ' + collections);
    }
    const collection = getCollectionByName(collections, axisField, isCollectionType);
    let axisName = collection.title;
    let axisType = ChartAxisType.VALUE;
    if (collection.type === DATA_TYPES.STRING) {
        axisType = ChartAxisType.CATEGORY;
    } else if (collection.type === DATA_TYPES.NUMBER) {
        axisType = ChartAxisType.VALUE;
    } else if (collection.type === DATA_TYPES.DATE_TIME) {
        axisType = ChartAxisType.TIME;
    }
    return [axisType, axisName];
}

function getAxisMax(rows, field, index = 0) {
    /* 
        Params:
        - rows (Array[Object]): list of dict of table rows dataset
        - field (String): field name
        - index (Number): index of axis. default 0
    */

    if (!rows) {
        throw new Error('getAxisMax failed. rows list is null or undefined, rows: ' + rows);
    }
    let max;
    rows.forEach(row => {
        if (row.hasOwnProperty(field)) {
            const value = row[field];
            if (max === undefined || max === null) {
                if (value !== undefined && value !== null) {
                    max = value;
                }
            } else if (value > max) {
                max = value;
            }
        }
    })
    // max = Math.ceil(max);
    // const scale = 1.5 - 0.25 * index;
    // const scale = 1.25;
    // return max * scale;
    if (!max) return 0;
    return max;
}

function getAxisMin(rows, field, index = 0) {
    /* 
        Params:
        - rows (Array[Object]): list of dict of table rows dataset
        - field (String): field name
        - index (Number): index of axis. default 0
    */

    if (!rows) {
        throw new Error('getAxisMax failed. rows list is null or undefined, rows: ' + rows);
    }
    let min;
    rows.forEach(row => {
        if (row.hasOwnProperty(field)) {
            const value = row[field];
            if (min === undefined || min === null) {
                if (value !== undefined && value !== null) {
                    min = value;
                }
            } else if (value < min) {
                min = value;
            }
        }
    })
    // min = Math.floor(min);
    // const scale = 1.5 - 0.25 * index;
    // const scale = 1.25;
    // return min / scale;
    if (!min) return 0;
    return min;
}

export function getCollectionByName(collections, name, isCollectionType = false) {
    /* 
        Params:
        - collections (Array[Object]): list of dict of widget field and their attributes
        - name (String): field name or xpath
        - isCollectionType (Boolean): true if widget is of collection type else false
    */
    if (!collections) {
        throw new Error('getCollectionByName failed. collections list is null or undefined, collections: ' + collections);
    }
    let collection;
    if (isCollectionType) {
        collection = collections.find(collection => collection.key === name);
    } else {
        collection = collections.find(collection => collection.tableTitle === name);
    }
    if (!collection) {
        throw new Error('getCollectionByName failed. no collection obj found for name: ' + name);
    }
    return collection;
}

function updateChartTypeSpecificOptions(chartSeries, dataset) {
    if (chartSeries.type === 'line') {
        if (dataset.source.length > 10) {
            chartSeries.showSymbol = false;
        }
        chartSeries.symbolSize = 10;
    } else if (chartSeries.type === 'scatter') {
        chartSeries.symbolSize = 7;
    }
}

function getYAxisIndex(encodes = [], yEncode, isStack = false) {
    if (encodes.length === 0) {
        return 0;
    } else {
        let index = -1;
        encodes.forEach((encode, i) => {
            if (encode.encode === yEncode) {
                index = i;
            }
        })
        if (index === -1) return encodes.length;
        return index;
    }
}

export function updateChartDataObj(chartDataObj, collections, rows, datasets, isCollectionType = false, schemaCollections, queryDict) {
    chartDataObj = cloneDeep(chartDataObj);
    const xEndodes = [];
    const yEncodes = [];
    const xAxis = [];
    const yAxis = [];
    const seriesList = [];
    let prevYEncode;
    let prevYEncodeIndex = 0;
    chartDataObj.series.forEach((series, seriesIndex) => {
        let xEncode = series.encode.x;
        let yEncode = series.encode.y;
        let yMax = 0;
        let yMin = 0;
        let forceMin = false;
        let forceMax = false;
        let chartSeriesCollections = collections;
        let updatedSeries;
        if (chartDataObj.time_series) {
            const collection = getCollectionByName(collections, series.encode.y, isCollectionType);
            if (collection.hasOwnProperty('mapping_src')) {
                const [seriesWidgetName, ...mappingSrcField] = collection.mapping_src.split('.');
                const srcField = mappingSrcField.join('.');
                const seriesCollections = schemaCollections[seriesWidgetName];
                const query = queryDict[seriesIndex];
                if (query) {
                    const xCollection = seriesCollections.find(col => col.val_time_field === true);
                    xEncode = xCollection.tableTitle;
                    const yCollection = seriesCollections.find(col => col.tableTitle === srcField);
                    yEncode = yCollection.tableTitle;
                    // series.encode.x = xEncode;
                    // series.encode.y = yEncode;
                    const tsRows = [];
                    datasets.forEach((dataset, index) => {
                        if (dataset.type === 'time_series' && dataset.query === query.name && dataset.series_type === series.type) {
                            updatedSeries = cloneDeep(series);
                            updatedSeries.datasetIndex = index;
                            updatedSeries.name = dataset.name + ' ' + series.encode.y + ' ' + series.type;
                            updatedSeries.animation = false;
                            updateChartTypeSpecificOptions(updatedSeries, dataset);
                            updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                            if (updatedSeries.yAxisIndex < 2) {
                                seriesList.push(updatedSeries);
                                tsRows.push(...dataset.source)
                            }
                        }
                    })
                    if (series.y_min || series.y_min === 0) {
                        yMin = series.y_min;
                        forceMin = true;
                    }
                    if (series.y_max || series.y_max === 0) {
                        yMax = series.y_max;
                        forceMax = true;
                    }
                    if (!forceMin) {
                        yMin = getAxisMin(tsRows, yEncode, yEncodes.length);
                    }
                    if (!forceMax) {
                        yMax = getAxisMax(tsRows, yEncode, yEncodes.length);
                    }
                    chartSeriesCollections = seriesCollections;
                }
            }
        } else {
            if (chartDataObj.partition_fld) {
                const partitionRows = [];
                datasets.forEach((dataset, index) => {
                    if (dataset.type === 'partition' && dataset.series_type === series.type) {
                        updatedSeries = cloneDeep(series);
                        updatedSeries.datasetIndex = index;
                        updatedSeries.name = dataset.name + ' ' + series.encode.y + ' ' + series.type;
                        updatedSeries.animation = false;
                        updateChartTypeSpecificOptions(updatedSeries, dataset);
                        updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                        if (updatedSeries.yAxisIndex < 2) {
                            seriesList.push(updatedSeries);
                            partitionRows.push(...dataset.source);
                        }
                    }
                })
                if (series.y_min || series.y_min === 0) {
                    yMin = series.y_min;
                    forceMin = true;
                }
                if (series.y_max || series.y_max === 0) {
                    yMax = series.y_max;
                    forceMax = true;
                }
                if (!forceMin) {
                    yMin = getAxisMin(partitionRows, yEncode, yEncodes.length);
                }
                if (!forceMax) {
                    yMax = getAxisMax(partitionRows, yEncode, yEncodes.length);
                }
            } else {
                const dataset = datasets.find(dataset => dataset.type === 'default');
                if (dataset) {
                    updatedSeries = cloneDeep(series);
                    updatedSeries.datasetIndex = datasets.indexOf(dataset);
                    updatedSeries.name = series.encode.y + ' ' + series.type;
                    updatedSeries.animation = false;
                    updateChartTypeSpecificOptions(updatedSeries, dataset);
                    updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                    if (updatedSeries.yAxisIndex < 2) {
                        seriesList.push(updatedSeries);
                    };
                    if (series.y_min || series.y_min === 0) {
                        yMin = series.y_min;
                        forceMin = true;
                    }
                    if (series.y_max || series.y_max === 0) {
                        yMax = series.y_max;
                        forceMax = true;
                    }
                    if (!forceMin) {
                        yMin = getAxisMin(rows, yEncode, yEncodes.length);
                    }
                    if (!forceMax) {
                        yMax = getAxisMax(rows, yEncode, yEncodes.length);
                    }
                }
            }
        }
        if (updatedSeries) {
            if (xEncode && yEncode) {
                // unused
                // if (!prevYEncode) {
                //     prevYEncode = yEncode;
                // } else if (prevYEncode !== yEncode) {
                //     prevYEncodeIndex += 1;
                // }
                if (!xEndodes.find(encode => encode.encode === xEncode)) {
                    xEndodes.push({ encode: xEncode, seriesCollections: chartSeriesCollections, isCollectionType: !chartDataObj.time_series });
                }
                // if already stack - new stack does not add encode
                if (series.stack) {
                    if (!yEncodes.find((encode) => encode.stack)) {
                        yEncodes.push({ encode: yEncode, seriesCollections: chartSeriesCollections, isCollectionType: !chartDataObj.time_series, max: yMax, min: yMin, forceMin, forceMax, stack: series.stack });
                        prevYEncodeIndex += 1;
                    }
                    // else not create new encode if stack already exists
                } else if (!yEncodes.find(encode => encode.encode === yEncode && !encode.stack)) {
                    yEncodes.push({ encode: yEncode, seriesCollections: chartSeriesCollections, isCollectionType: !chartDataObj.time_series, max: yMax, min: yMin, forceMin, forceMax });
                    prevYEncodeIndex += 1;
                }
                updatedSeries.yAxisIndex = prevYEncodeIndex - 1;
                if (updatedSeries.stack) {
                    updatedSeries.stack = 'total';
                    if (updatedSeries.type === 'line') {
                        updatedSeries.areaStyle = {};
                        updatedSeries.emphasis = {
                            focus: 'series'
                        }
                    }
                }
            }
        }
    })
    xEndodes.forEach(({ encode, seriesCollections, isCollectionType }) => {
        const [xAxisType, xAxisName] = getChartAxisTypeAndName(seriesCollections, encode, isCollectionType);
        // only one x-axis is allowed per chart.
        // if more than 1 x-axis is present, only considers the first x-axis
        // this limitation is added to avoid unsupported configurations
        if (xAxis.length === 0) {
            const axis = {
                type: xAxisType,
                name: xAxisName,
                encode: encode
            }
            if (axis.type === ChartAxisType.VALUE) {
                const max = getAxisMax(rows, encode, 0);
                const min = getAxisMin(rows, encode, 0);
                axis.max = max + (max - min);
                axis.min = min >= 0 && min - (max - min) < 0 ? 0 : min - (max - min);
                axis.onZero = false;
                axis.axisLabel = {
                    formatter: (val) => tooltipFormatter(val)
                }
                axis.axisPointer = {
                    label: {
                        formatter: (param) => tooltipFormatter(param.value)
                    }
                }
            }
            xAxis.push(axis);
        }
    })
    yEncodes.forEach(({ encode, seriesCollections, isCollectionType, max, min, forceMin, forceMax, stack = false }) => {
        const [yAxisType, yAxisName] = getChartAxisTypeAndName(seriesCollections, encode, isCollectionType);
        // only two y-axis is allowed per chart.
        // if more than 2 y-axis is present, only considers the first 2 y-axis
        // this limitation is added to avoid unsupported configurations
        const axisMax = forceMax ? max : max + (max - min);
        const axisMin = forceMin ? min : min >= 0 && min - (max - min) < 0 ? 0 : min - (max - min);
        if (yAxis.length < 2) {
            let axis = {
                type: yAxisType,
                name: yAxisName,
                encode: encode,
                splitNumber: 5,
                // max: axisMax,
                // interval: (axisMax - axisMin) / 5,
                // min: axisMin,
                // onZero: false,
                axisLabel: {
                    formatter: (val) => tooltipFormatter(val)
                },
                axisPointer: {
                    label: {
                        formatter: (param) => tooltipFormatter(param.value)
                    }
                }
            }
            if (!stack) {
                const nonStackProps = {
                    max: axisMax,
                    interval: (axisMax - axisMin) / 5,
                    min: axisMin,
                    onZero: false,
                    axisLabel: {
                        formatter: (val) => tooltipFormatter(val)
                    },
                    axisPointer: {
                        label: {
                            formatter: (param) => tooltipFormatter(param.value)
                        }
                    }
                }
                axis = { ...axis, ...nonStackProps };
            }
            yAxis.push(axis);
        }
    })
    chartDataObj.xAxis = xAxis;
    chartDataObj.yAxis = yAxis;
    chartDataObj.series = seriesList;
    return chartDataObj;
}

function updateChartAttributesInSchema(schema, currentSchema) {
    if (currentSchema.hasOwnProperty('properties')) {
        for (const key in currentSchema.properties) {
            const attributes = currentSchema.properties[key];
            if (primitiveDataTypes.includes(attributes.type)) {
                if (key === DB_ID) {
                    attributes.server_populate = true;
                    attributes.hide = true;
                    attributes.orm_no_update = true;
                } else if (key === 'chart_name') {
                    attributes.orm_no_update = true;
                } else if (['y_min', 'y_max'].includes(key)) {
                    attributes.hide = true;
                }
            } else if ([DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(attributes.type)) {
                const ref = attributes.items.$ref.split('/')
                const nestedSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
                updateChartAttributesInSchema(schema, nestedSchema);
            }
        }
    }
}

export function updateChartSchema(schema, collections, isCollectionType = false) {
    schema = cloneDeep(schema);
    const chartDataSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_data']);
    updateChartAttributesInSchema(schema, chartDataSchema);
    chartDataSchema.auto_complete = 'partition_fld:StrFldList';
    const chartEncodeSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_encode']);
    chartEncodeSchema.auto_complete = 'x:FldList,y:FldList';
    const filterSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'ui_filter']);
    filterSchema.auto_complete = 'fld_name:FldList';
    let fldList;
    let strFldList;
    let metaFldList;
    if (isCollectionType) {
        fldList = collections.map(collection => collection.key);
        strFldList = collections.filter(collection => collection.type === DATA_TYPES.STRING).map(collection => collection.key);
        metaFldList = collections.filter(collection => collection.hasOwnProperty('mapping_underlying_meta_field')).map(collection => collection.key);
    } else {
        fldList = collections.map(collection => collection.tableTitle);
        strFldList = collections.filter(collection => collection.type === DATA_TYPES.STRING).map(collection => collection.tableTitle);
        metaFldList = collections.filter(collection => collection.hasOwnProperty('mapping_underlying_meta_field')).map(collection => collection.tableTitle);
    }
    schema.autocomplete['FldList'] = fldList;
    schema.autocomplete['StrFldList'] = strFldList;
    schema.autocomplete['MetaFldList'] = metaFldList;
    return schema;
}

// export function getFilterDict(filters) {
//     const filterDict = {};
//     if (filters) {
//         filters.forEach(filter => {
//             if (filter.fld_value) {
//                 filterDict[filter.fld_name] = filter.fld_value;
//             }
//         })
//     }
//     return filterDict;
// }

export function getFiltersFromDict(filterDict) {
    const filters = [];
    Object.keys(filterDict).forEach(key => {
        filters.push({
            fld_name: key,
            fld_value: filterDict[key]
        })
    })
    return filters;
}

export function getChartDatasets(rows, partitionFld, chartObj) {
    /* 
        function to generate list of datasets by grouping and 
        options from chart option obj
        Params:
        - rows (Array[Object]): list of dict of table rows
        - partitionFld (String): field name or xpath to group the rows on
        - chartObj (Object): chart configuration/option 
    */
    if (rows.length === 0) {
        return [];
    } else {
        const datasets = [];
        const dimensions = Object.keys(rows[0]);
        let groups;
        if (partitionFld) {
            const groupsDict = rows.reduce((acc, cur) => {
                acc[cur[partitionFld]] = [...acc[cur[partitionFld]] || [], cur];
                return acc;
            }, {});
            groups = [];
            for (const key in groupsDict) {
                groups.push(groupsDict[key]);
            }
        } else {
            groups = [rows];
        }
        if (chartObj.xAxis) {
            const axis = chartObj.xAxis[0];
            groups.forEach(group => {
                group.sort((a, b) => get(a, axis.encode) > get(b, axis.encode) ? 1 : get(a, axis.encode) < get(b, axis.encode) ? -1 : 0);
            })
        }
        groups.forEach(group => {
            const dateset = {
                dimensions: dimensions,
                source: group
            }
            datasets.push(dateset);
        })
        return datasets;
    }
}

export function genChartDatasets(rows = [], tsData, chartObj, queryDict, collections, isCollectionType = false) {
    const datasets = [];
    if (chartObj.series) {
        chartObj.series.forEach((series, index) => {
            if (chartObj.time_series) {
                const collection = getCollectionByName(collections, series.encode.y, isCollectionType);
                if (collection.hasOwnProperty('mapping_src')) {
                    const query = queryDict[index];
                    if (query) {
                        const seriesTsData = tsData[query.name];
                        if (seriesTsData) {
                            seriesTsData.forEach(ts => {
                                if (ts.projection_models && ts.projection_models.length > 0) {
                                    let name = query.params.map(param => get(ts, param)).join(' ');
                                    const { projection_models, ...meta } = ts;
                                    const metaFieldName = Object.keys(meta)[0];
                                    ts.projection_models.map(projection => {
                                        projection[metaFieldName] = meta[metaFieldName];
                                        projection['seriesIndex'] = index;
                                        return projection;
                                    })
                                    datasets.push({
                                        dimensions: Object.keys(ts.projection_models[0]),
                                        source: ts.projection_models,
                                        name: name,
                                        type: 'time_series',
                                        query: query.name,
                                        series_type: series.type
                                    })
                                }
                            })
                        }
                    }
                }
            } else if (rows.length > 0) {
                if (chartObj.partition_fld) {
                    const groupsDict = rows.reduce((acc, cur) => {
                        acc[cur[chartObj.partition_fld]] = [...acc[cur[chartObj.partition_fld]] || [], cur];
                        return acc;
                    }, {});
                    const sortAxis = series.encode.x;
                    for (const groupName in groupsDict) {
                        const group = groupsDict[groupName];
                        if (sortAxis) {
                            group.sort((a, b) => get(a, sortAxis) > get(b, sortAxis) ? 1 : get(a, sortAxis) < get(b, sortAxis) ? -1 : 0);
                        }
                        datasets.push({
                            dimensions: Object.keys(rows[0]),
                            source: group,
                            name: groupName,
                            type: 'partition',
                            series_type: series.type
                        })
                    }
                } else {
                    const sortAxis = series.encode.x;
                    if (sortAxis) {
                        rows.sort((a, b) => get(a, sortAxis) > get(b, sortAxis) ? 1 : get(a, sortAxis) < get(b, sortAxis) ? -1 : 0);
                    }
                    datasets.push({
                        dimensions: Object.keys(rows[0]),
                        source: rows,
                        name: 'default',
                        type: 'default'
                    })
                }
            }
        })
    }
    return datasets;
}

export function mergeTsData(tsData, updatedData, queryDict) {
    for (const queryName in updatedData) {
        const dataList = updatedData[queryName];
        let query;
        Object.entries(queryDict).forEach(([index, queryProps]) => {
            if (query) return;
            if (queryProps.name === queryName) {
                query = queryProps;
            }
        })
        if (query) {
            if (!tsData.hasOwnProperty(queryName)) {
                tsData[queryName] = [];
            }
            dataList.forEach(data => {
                const timeSeries = tsData[queryName].find(ts => {
                    let found = true;
                    query.params.forEach(param => {
                        if (get(ts, param) !== get(data, param)) {
                            found = false;
                        }
                    })
                    if (found) return true;
                    return false;
                })
                if (timeSeries) {
                    timeSeries.projection_models.push(...data.projection_models);
                } else {
                    tsData[queryName].push(data);
                }
            })
        }
    }
    return tsData;
}

export function genMetaFilters(arr, collections, filterDict, filterFld, isCollectionType = false) {
    const filters = [];
    const fldMappingDict = {};
    const metaCollection = collections.find(col => {
        if (isCollectionType) {
            return col.key === filterFld;
        } else {
            return col.tableTitle = filterFld;
        }
    })
    const metaId = metaCollection.metaFieldId;
    collections.forEach(col => {
        if (col.hasOwnProperty('mapping_underlying_meta_field') && col.metaFieldId === metaId) {
            const metaField = col.mapping_underlying_meta_field.split('.').pop();
            if (isCollectionType) {
                fldMappingDict[col.key] = metaField;
            } else {
                fldMappingDict[col.tableTitle] = metaField;
            }
        }
    })
    let values = filterDict[filterFld].split(",").map(val => val.trim()).filter(val => val !== "");
    arr.forEach(row => {
        if (values.includes(get(row, filterFld))) {
            const filter = {};
            for (const key in fldMappingDict) {
                filter[fldMappingDict[key]] = get(row, key);
            }
            filters.push(filter);
        }
    })
    return filters;
}

export function tooltipFormatter(value) {
    if (typeof value === DATA_TYPES.NUMBER) {
        if (Number.isInteger(value)) {
            return value.toLocaleString();
        } else {
            return roundNumber(value, 2).toLocaleString();
        }
    }
    return value;
}

export function updatePartitionFldSchema(schema, chartObj) {
    const updatedSchema = cloneDeep(schema);
    const chartSchema = get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, 'chart_data']);
    if (chartObj.time_series) {
        chartSchema.properties.partition_fld.hide = true;
    } else {
        chartSchema.properties.partition_fld.hide = false;
    }
    return updatedSchema;
}

function jsonify(obj) {
    return JSON.stringify({ obj });
}

export function getServerUrl(widgetSchema, linkedObj, linkedFieldsMetadata, requestType = 'http', isViewUrl = false) {
    if (widgetSchema.connection_details) {
        const connectionDetails = widgetSchema.connection_details;
        const { host, port, view_port, project_name } = connectionDetails;
        // set url only if linkedObj running field is set to true for dynamic as well as static
        if (widgetSchema.widget_ui_data_element?.depending_proto_model_name) {
            const serverReadyStatusFld = linkedFieldsMetadata?.find(col => col.hasOwnProperty('server_ready_status')).key;
            const requiredStateLvl = widgetSchema.widget_ui_data_element.server_running_status_lvl || 0;
            if (linkedObj && Object.keys(linkedObj).length && get(linkedObj, serverReadyStatusFld) >= requiredStateLvl) {
                if (connectionDetails.dynamic_url) {
                    const hostxpath = host.substring(host.indexOf('.') + 1);
                    const portFld = isViewUrl ? view_port : port;
                    const portxpath = portFld.substring(port.indexOf('.') + 1);
                    const hostVal = get(linkedObj, hostxpath);
                    const portVal = get(linkedObj, portxpath);
                    if (!hostVal || !portVal) return null;
                    if (requestType === 'http') {
                        if (widgetSchema.widget_ui_data_element?.depending_proto_model_for_cpp_port) {
                            return `http://${hostVal}:${portVal}`;
                        }
                        return `http://${hostVal}:${portVal}/${project_name}`;
                    } else if (requestType === 'ws') {
                        if (widgetSchema.widget_ui_data_element?.depending_proto_model_for_cpp_port) {
                            return `ws://${hostVal}:${portVal}`;
                        }
                        return `ws://${hostVal}:${portVal}/${project_name}`;
                    } else {
                        const err_ = `getServerUrl failed, unsupported ${jsonify(requestType)}. allowed [http, ws]`;
                        console.error(err_);
                    }
                } else {
                    const portVal = isViewUrl ? view_port : port;
                    return `http://${host}:${portVal}/${project_name}`;
                }
            }
        } else {
            const portVal = isViewUrl ? view_port : port;
            return `http://${host}:${portVal}/${project_name}`;
        }
    } else {
        return isViewUrl ? API_ROOT_VIEW_URL : API_ROOT_URL;
    }
    return null;
}

export function getAbbreviatedCollections(widgetCollectionsDict, loadListFieldAttrs) {
    const abbreviated = loadListFieldAttrs.abbreviated;
    const abbreviatedCollections = [];
    let sequenceNumber = 1;
    // alert bubble is the first column always
    if (loadListFieldAttrs.alertBubbleSource) {
        let collection = {};
        collection.key = '';
        collection.title = '';
        collection.elaborateTitle = false;
        collection.sequenceNumber = sequenceNumber;
        collection.type = 'alert_bubble'
        // source to fetch value of bubble
        const bubbleSource = loadListFieldAttrs.alertBubbleSource;
        collection.alertBubbleSource = bubbleSource;
        collection.source = bubbleSource.split('.')[0];
        collection.xpath = bubbleSource.substring(bubbleSource.indexOf('.') + 1);
        // source to fetch color of bubble
        const bubbleColorSource = loadListFieldAttrs.alertBubbleColor;
        if (bubbleColorSource) {
            const colorSource = bubbleColorSource.substring(bubbleColorSource.indexOf('.') + 1);
            collection.colorSource = colorSource
            collection.colorCollection = widgetCollectionsDict[collection.source].find(col => col.tableTitle === colorSource);
        }
        abbreviatedCollections.push(collection);
        sequenceNumber += 1;
    }
    abbreviated.split('^').forEach((titlePathPair, index) => {
        let title;
        let source;
        // title in collection view is always expected to be present
        if (titlePathPair.indexOf(':') !== -1) {
            title = titlePathPair.split(':')[0];
            source = titlePathPair.split(':')[1];
        } else {
            throw new Error('no title found in abbreviated split. expected title followed by colon (:)')
        }
        // expected all the fields in abbreviated is from its abbreviated dependent source
        const widgetName = source.split('.')[0];
        let xpath = source.split('-').map(path => path = path.substring(path.indexOf('.') + 1));
        xpath = xpath.join('-');
        const subCollections = xpath.split('-').map(path => {
            return widgetCollectionsDict[widgetName].map(col => Object.assign({}, col))
                .find(col => col.tableTitle === path);
        })
        // if a single field has values from multiple source separated by hyphen, then
        // attributes of all fields are combined
        source = xpath.split('-')[0];
        const collectionsCopy = widgetCollectionsDict[widgetName].map(col => Object.assign({}, col));
        const collection = collectionsCopy.find(col => col.tableTitle === source);
        if (collection) {
            xpath.split('-').forEach(path => {
                const pathCollection = collectionsCopy.find(col => col.tableTitle === path);
                // additional handling to prevent override
                Object.keys(pathCollection).forEach(key => {
                    if (['serverPopulate', 'ormNoUpdate'].includes(key)) {
                        if (!(collection.hasOwnProperty(key) && collection[key]) && pathCollection.hasOwnProperty(key)) {
                            collection[key] = pathCollection[key];
                        }
                    } else {
                        collection[key] = pathCollection[key];
                    }
                })
            })
            if (xpath === DB_ID) {
                collection.noCommonKey = true;
            }
            // create a custom collection object
            collection.sequenceNumber = sequenceNumber;
            collection.source = widgetName;
            collection.rootLevel = false;
            collection.key = title;
            collection.title = title;
            // TODO: check the scenario in which xpath and tableTitle are different
            collection.tableTitle = xpath;
            collection.xpath = xpath;
            // remove default properties set on the fields
            collection.elaborateTitle = false;
            collection.hide = false;
            collection.subCollections = subCollections;
            // if field has values from multiple source, it's data-type is considered STRING
            if (xpath.indexOf('-') !== -1) {
                collection.type = DATA_TYPES.STRING;
            }
            abbreviatedCollections.push(collection);
            sequenceNumber += 1;
        } else {
            throw new Error('no collection (field attributes) found for the field with xpath ' + source);
        }
    })
    return abbreviatedCollections;
}

export function getAbbreviatedDependentWidgets(loadListFieldAttrs) {
    const widgetSet = new Set();
    loadListFieldAttrs.abbreviated.split('^').forEach((keyValuePair) => {
        const [, fieldxpath] = keyValuePair.split(':');
        const name = fieldxpath.split('.')[0];
        widgetSet.add(name);
    });
    const bubbleSource = loadListFieldAttrs.alertBubbleSource;
    if (bubbleSource) {
        const name = bubbleSource.split('.')[0];
        widgetSet.add(name);
    }
    const bubbleColorSource = loadListFieldAttrs.alertBubbleColorSource;
    if (bubbleColorSource) {
        const name = bubbleColorSource.split('.')[0];
        widgetSet.add(name);
    }
    return Array.from(widgetSet);
}

export function snakeToCamel(snakeCase) {
    return snakeCase.replace(/_([a-z])/g, function (match, letter) {
        return letter.toUpperCase();
    });
}

export function sortColumns(collections, columnOrders, groupBy = false, center = false, flip = false, isCollectionType = false) {
    function handleEqualSequence(seqA, seqB, orderA, orderB, isReverse = false) {
        if (orderA && orderB) {
            if (orderA.sequence < orderB.sequence) {
                if (isReverse) return 1;
                return -1;
            }
            if (isReverse) return -1;
            return 1;
        } else if (orderA) {
            if (orderA.sequence <= seqB) {
                if (isReverse) return 1;
                return -1;
            }
            if (isReverse) return -1;
            return 1;
        } else if (orderB) {
            if (orderB.sequence <= seqA) {
                if (isReverse) return -1;
                return 1;
            }
            if (isReverse) return 1;
            return -1;
        }
    }
    collections.sort(function (a, b) {
        let seqA = a.sequenceNumber;
        let seqB = b.sequenceNumber;
        let orderA;
        let orderB;
        if (columnOrders) {
            let fieldName = 'tableTitle';
            if (isCollectionType) {
                fieldName = 'key';
            }
            orderA = columnOrders.find(order => order.column_name === a[fieldName]);
            orderB = columnOrders.find(order => order.column_name === b[fieldName]);
            if (orderA) {
                seqA = orderA.sequence;
            }
            if (orderB) {
                seqB = orderB.sequence;
            }
        }
        if (groupBy) {
            if (center && a.sourceIndex === 0 && b.sourceIndex === 0) {
                if (a.joinKey && b.joinKey) {
                    if (seqA < seqB) return -1;
                    else if (seqB < seqA) return 1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
                } else if (a.joinKey) {
                    return 1;
                } else if (b.joinKey) {
                    return -1
                } else if (a.commonGroupKey && b.commonGroupKey) {
                    if (seqA < seqB) return -1;
                    else if (seqB < seqA) return 1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
                } else if (a.commonGroupKey) {
                    return 1;
                } else if (b.commonGroupKey) {
                    return -1
                } else if (seqA < seqB) {
                    return -1;
                } else if (seqB < seqA) {
                    return 1
                } else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            }
            else if (a.joinKey && b.joinKey) {
                if (seqA < seqB) return -1;
                else if (seqB < seqA) return 1;
                else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            } else if (a.joinKey) {
                return -1;
            } else if (b.joinKey) {
                return 1;
            } else if (a.commonGroupKey && b.commonGroupKey) {
                if (seqA < seqB) return -1;
                else if (seqB < seqA) return 1;
                else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            } else if (a.commonGroupKey) {
                return -1;
            } else if (b.commonGroupKey) {
                return 1;
            } else if (flip) {
                if (a.sourceIndex === b.sourceIndex && a.sourceIndex > 0) {
                    if (seqA < seqB) return 1;
                    else if (seqB < seqA) return -1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB, true);  // seqA === seqB with flip
                } else if (a.sourceIndex < b.sourceIndex) {
                    return -1;
                } else if (b.sourceIndex < a.sourceIndex) {
                    return 1;
                }
            } else if (a.sourceIndex < b.sourceIndex) {
                return -1;
            } else if (b.sourceIndex < a.sourceIndex) {
                return 1;
            }
        }
        if (seqA < seqB) return -1;
        else if (seqB < seqA) return 1;
        else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
    })
    return collections;
}

export function isWebSocketAlive(webSocket) {
    if (webSocket) {
        if (webSocket.readyState === WebSocket.OPEN || webSocket.readyState === WebSocket.CONNECTING) {
            return true;
        }
    }
    return false;
}

export function getReducerArrrayFromCollections(collections) {
    const reducerArray = [];
    collections
        .filter(col => typeof col.min === DATA_TYPES.STRING || typeof col.max === DATA_TYPES.STRING || col.dynamic_autocomplete)
        .map(col => {
            const dynamicListenProperties = ['min', 'max', 'autocomplete'];
            dynamicListenProperties.forEach(property => {
                if (col.hasOwnProperty(property) && typeof col[property] === DATA_TYPES.STRING) {
                    if (property === 'autocomplete' && !col.dynamic_autocomplete) {
                        return;
                    }
                    const reducerName = toCamelCase(col[property].split('.')[0]);
                    if (!reducerArray.includes(reducerName)) {
                        reducerArray.push(reducerName);
                    }
                }
            })
        });
    return reducerArray;

}

export function getRepeatedWidgetModifiedArray(storedArray, selectedId, updatedObj) {
    let updatedArray = addxpath(cloneDeep(storedArray));
    if (selectedId && updatedObj[DB_ID] === selectedId) {
        const idx = updatedArray.findIndex(obj => obj[DB_ID] === selectedId);
        if (idx !== -1) {
            updatedArray[idx] = updatedObj;
        }
    }
    return updatedArray;
}

// export function getMaxRowSize(rows) {
//     let maxSize = 1;
//     for (let i = 0; i < rows.length; i++) {
//         if (rows[i].length > maxSize) {
//             maxSize = rows[i].length;
//         }
//     }
//     return maxSize;
// }

export function getBufferAbbreviatedOptionLabel(bufferOption, bufferListFieldAttrs, loadListFieldAttrs, storedArray) {
    if (!bufferListFieldAttrs.abbreviated) {
        return bufferOption;
    }
    if (bufferOption === '') return bufferOption;
    const id = getIdFromAbbreviatedKey(loadListFieldAttrs.abbreviated, bufferOption);
    const storedObj = storedArray.find(obj => obj[DB_ID] === id);
    if (storedObj) {
        let abbreviatedSplit = bufferListFieldAttrs.abbreviated.split('^')[0].split(':')[1].split('-');
        abbreviatedSplit = abbreviatedSplit.map(xpath => xpath.substring(xpath.indexOf('.') + 1));
        const values = [];
        abbreviatedSplit.forEach(xpath => {
            values.push(get(storedObj, xpath));
        })
        return values.join('-');
    }
    return bufferOption;
}

function getContrastColor(color) {
    // Function to convert hex to RGB
    function hexToRgb(hex) {
        hex = hex.replace(/^#/, '');
        if (hex.length === 3) {
            hex = hex.split('').map(function (hex) {
                return hex + hex;
            }).join('');
        }
        var bigint = parseInt(hex, 16);
        return [bigint >> 16 & 255, bigint >> 8 & 255, bigint & 255];
    }

    // Function to convert color to RGB
    function colorToRgb(color) {
        // Check if the color is in hex format
        if (color.startsWith('#')) {
            return hexToRgb(color);
        }
        // If it's already in rgb format
        if (color.startsWith('rgb')) {
            var match = color.match(/(\d+), (\d+), (\d+)/);
            return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
        }
        // Add other color formats if needed
        throw new Error('Unsupported color format');
    }

    // Function to convert RGB to hex
    function rgbToHex(r, g, b) {
        return '#' + [r, g, b].map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        }).join('');
    }

    // Get RGB components of the color
    const rgb = colorToRgb(color);

    // Calculate complementary color
    const compRgb = rgb.map(c => 255 - c);

    // Convert complementary RGB to hex
    return rgbToHex(compRgb[0], compRgb[1], compRgb[2]);
}

function getTextWidthInPx(characters, fontSize = 14) {
    // Create a temporary canvas element
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');

    // Set the font size on the canvas context
    context.font = `${fontSize}px sans-serif`; // Using a default font (sans-serif)

    // Measure the text width
    const metrics = context.measureText(characters);

    // Calculate the zoom level
    const zoomLevel = window.devicePixelRatio;

    // Return the width adjusted for the zoom level
    return metrics.width * zoomLevel;
}

export function isEmptyObject(obj) {
    return Object.keys(obj).length === 0;
}

export function clearId(obj) {
    if (isObject(obj)) {
        if (obj.hasOwnProperty(DB_ID)) {
            delete obj[DB_ID];
        }
        Object.entries(obj).forEach(([k, v]) => {
            if (Array.isArray(v)) {
                v.forEach(o => {
                    if (isObject(o)) {
                        clearId(o);
                    } // else not required - simple data type array
                })
            } else if (isObject(v)) {
                clearId(v);
            } // else not required - simple data type field
        })
    } else {
        const err_ = 'clearId failed, expected obj of type Object, received: ' + typeof obj;
        console.error(err_);
    }
}

function checkConstraints(storedObj, updatedObj) {
    // DB_ID constraints - stored and updated obj DB_ID should be same
    if (storedObj.hasOwnProperty(DB_ID) && updatedObj.hasOwnProperty(DB_ID) && storedObj[DB_ID] !== updatedObj[DB_ID]) {
        const err_ = `CRITICAL: mismatch DB_ID found while preparing patch update. storedObj DB_ID: ${storedObj[DB_ID]}, 
        updatedObj DB_ID: ${updatedObj[DB_ID]}. Please send a screenshot to DEV for investigation;;;${JSON.stringify({ storedObj })}; 
        ${JSON.stringify({ updatedObj })}`;
        console.error(err_);
        alert(err_);
        return false;
    } // else not required - DB_ID check passed
    return true;
}

export function getAxiosMethod(queryRouteType) {
    switch (queryRouteType.toLowerCase()) {
        case 'get':
            return axios.get;
        case 'post':
            return axios.post;
        case 'patch':
            return axios.patch;
        default:
            throw new Error(`Unsupported queryRouteType: ${queryRouteType}`);
    }
}

export function getDateTimeFromInt(value) {
    const dateTime = dayjs(value).utc();
    let dateTimeWithTimezone;
    if (FileOptions.date_time_print_timezone === 'LOCAL') {
        dateTimeWithTimezone = dateTime.tz(LOCAL_TZ);
    } else {
        dateTimeWithTimezone = dateTime.tz(FileOptions.date_time_print_timezone);
    }
    return dateTimeWithTimezone;
}

export function getModelSchema(modelName, schema) {
    return schema[modelName] || schema[SCHEMA_DEFINITIONS_XPATH][modelName];
}

/**
 * Converts a snake_case string to PascalCase.
 * @param {string} snakeStr - The snake_case string.
 * @returns {string} - The PascalCase string.
 */
export function snakeToPascal(snakeStr) {
    return snakeStr
        .split('_')
        .map(word => word === 'ui' ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1))
        .join('');
}

/**
 * Converts a snake_case string to TitleCase.
 * @param {string} snakeStr - The snake_case string.
 * @returns {string} - The PascalCase string.
 */
export function snakeToTitle(snakeStr) {
    return snakeStr
        .split('_')
        .map(word => word === 'ui' ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

/**
 * Utility function to build API URL and parameters.
 *
 * @param {string} defaultEndpoint - Default endpoint string.
 * @param {string} overrideUrl - Optional URL override.
 * @param {string} overrideEndpoint - Optional endpoint override.
 * @param {number} uiLimit - UI limit for number of items.
 * @param {Object} params - Additional parameters.
 * @returns {[string, Object]} The API URL and parameters.
 */
export function getApiUrlMetadata(defaultEndpoint, overrideUrl, overrideEndpoint, uiLimit, params, isViewUrl = false) {
    const baseUrl = overrideUrl || (isViewUrl ? API_ROOT_VIEW_URL : API_ROOT_URL);
    const baseEndpoint = overrideEndpoint || defaultEndpoint;
    const apiUrl = `${baseUrl}/${baseEndpoint}`;
    const apiParams = params ? { ...params } : {};
    if (uiLimit) {
        apiParams['limitObjCount'] = uiLimit;
    }
    return [apiUrl, apiParams];
}

export const getDataSourceObj = (dataSources, sourceName) => {
    const dataSource = dataSources.find(o => o.name === sourceName);
    if (!dataSource) {
        alert('error');
    }
    return dataSource;
}

export function getCrudOverrideDict(modelSchema) {
    return modelSchema.override_default_crud?.reduce((acc, { ui_crud_type, query_name, ui_query_params }) => {
        let paramDict = null;
        ui_query_params?.forEach(({ query_param_name, query_param_value_src }) => {
            const param_value_src = query_param_value_src.substring(query_param_value_src.indexOf('.') + 1);
            if (!paramDict) {
                paramDict = {};
            }
            paramDict[query_param_name] = param_value_src;
        })
        acc[ui_crud_type] = { endpoint: `query-${query_name}`, paramDict };
        return acc;
    }, {}) || null;
}

export function getDataSourcesCrudOverrideDict(dataSources) {
    const dataSourcesCrudOverrideDict = {};
    dataSources.forEach(({ name, schema }) => {
        const crudOverrideDict = getCrudOverrideDict(schema);
        if (crudOverrideDict) {
            dataSourcesCrudOverrideDict[name] = crudOverrideDict;
        }
    });
    if (Object.keys(dataSourcesCrudOverrideDict).length === 0) {
        return null;
    }
    return dataSourcesCrudOverrideDict;
}

export function fastClone(obj) {
    if (obj === undefined || obj === null) return obj;
    return JSON.parse(JSON.stringify(obj));
}

export function getActiveIds(activeRows, idField) {
    const activeObjIds = new Set();
    if (activeRows.length > 0) {
        activeRows.forEach((groupedRow) => {
            groupedRow.forEach((row) => {
                const id = row[idField];
                if (id) {
                    activeObjIds.add(id);
                }
            });
        });
    }
    return Array.from(activeObjIds);
}

export function generateExcel(rows, fileName, csv = false) {
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Data');
    const bookType = csv ? 'csv' : 'xlsx'
    XLSX.writeFile(wb, fileName, { bookType: bookType });
}

export function getCSVFileName(modelName) {
    return `${modelName}_${new Date().toISOString()}.csv`;
}

export function isWebSocketActive(webSocket, modelName = null) {
    let websocketToCheck = webSocket;
    if (modelName) {
        websocketToCheck = getWebSocketConnection(modelName);
    }
    if (websocketToCheck) {
        if (websocketToCheck.readyState === WebSocket.OPEN) {
            return true;
        }
    }
    return false;
}

export function updateFormValidation(formValidationRef, xpath, validation) {
    if (!formValidationRef?.current) {
        console.error('form validation ref found null');
        return;
    }

    if (validation) {
        formValidationRef.current = { ...formValidationRef.current, [xpath]: validation };
    } else {
        if (xpath in formValidationRef.current) {
            delete formValidationRef.current[xpath];
        }
    }
}

function updatePivotAttributesInSchema(schema, currentSchema) {
    if (currentSchema.hasOwnProperty('properties')) {
        for (const key in currentSchema.properties) {
            const attributes = currentSchema.properties[key];
            if (primitiveDataTypes.includes(attributes.type)) {
                if (key === DB_ID) {
                    attributes.server_populate = true;
                    attributes.hide = true;
                    attributes.orm_no_update = true;
                } else if (key === 'pivot_name') {
                    attributes.orm_no_update = true;
                } else {
                    attributes.server_populate = true;
                }
            } else if ([DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(attributes.type)) {
                attributes.server_populate = true;
                attributes.hide = true;
            }
        }
    }
}

export function updatePivotSchema(schema) {
    schema = cloneDeep(schema);
    const pivotDataSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'pivot_data']);
    updatePivotAttributesInSchema(schema, pivotDataSchema);
    return schema;
}

export function applyRowIdsFilter(rows, rowIds) {
    if (rowIds) {
        const updatedRows = rows.filter((row) => rowIds.includes(row['data-id']));
        return updatedRows;
    }
    return rows;
}

export function getSortOrdersWithAbs(sortOrders, absoluteSorts) {
    const sortOrdersWithAbs = sortOrders.map((sortOrder) => {
        if (absoluteSorts.includes(sortOrder.order_by)) {
            sortOrder.abs = true;
        }
        return sortOrder;
    })
    return sortOrdersWithAbs;
}
