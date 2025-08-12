// third-party package imports
import { cloneDeep, get, isObject, has } from 'lodash';
// project imports
import { DATA_TYPES, MODES, SCHEMA_DEFINITIONS_XPATH, primitiveDataTypes } from '../../constants';
import { fluxOptions, complexFieldProps, fieldProps, arrayFieldProps } from './schemaConstants';


/**
 * Adds field-level Flux options (attributes) to a collection object.
 * This function iterates through predefined `fluxOptions` and applies corresponding values
 * from the `attributes` object to the `object`.
 * It also handles special cases for 'button', 'progress_bar', 'mapping_src', and 'mapping_underlying_meta_field' properties.
 * @param {Object} object - The collection object to which attributes will be added.
 * @param {Object} attributes - A dictionary of attributes (Flux options) set on the field.
 */
export function addFieldAttributes(object, attributes) {
    /* 
    function to add field level flux option on collection object.
    params:
        object: collection object
        attributes: attribute (flux option) dict set on the field
    */
    fluxOptions.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {
            if (isObject(attributes[propertyName])) {
                // If the attribute value is an object, check if it has a property matching the object's key.
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
    });
}


/**
 * This function appears to be a placeholder or incomplete, as it iterates through `fluxOptions`
 * but does not perform any operations on the `object` or `message` based on the attributes.
 * It might be intended for future use in adding message-specific attributes.
 * @param {Object} object - The collection object.
 * @param {Object} attributes - A dictionary of attributes.
 * @param {*} message - A message parameter (its type and usage are not defined in the current implementation).
 */
export function addMessageAttributes(object, attributes, message) {
    /* 
    function to add field level flux option on collection object.
    params:
        object: collection object
        attributes: attribute (flux option) dict set on the field
        message:
    */
    fluxOptions.forEach(({ propertyName, usageName }) => {
        if (attributes.hasOwnProperty(propertyName)) {
            // No operations are performed here in the current implementation.
        }
    });
}


export const KEY_INDICATOR_SEPARATOR = '@@@';


/**
 * Parses an autocomplete string into a dictionary of autocomplete configurations.
 * The autocomplete string can contain multiple field configurations separated by commas.
 * Each field configuration can specify options (using ':'), assignments (using '='),
 * or dynamic options (using '~').
 * @param {string} autocompleteValue - The autocomplete string (e.g., "field1:OptionList,field2=defaultValue,field3~DynamicOptions").
 * @returns {Object<string, string>} A dictionary where keys are constructed from the field path and an indicator (e.g., 'field1@@@options'), and values are the corresponding autocomplete settings.
 */
export function getAutocompleteDict(autocompleteValue) {
    let autocompleteFieldSet = autocompleteValue.split(',').map((field) => field.trim());
    let autocompleteDict = {};

    autocompleteFieldSet.forEach(fieldSet => {
        if (fieldSet.indexOf(':') > 0) {
            // Handle options (e.g., "field:OptionList").
            let [key, value] = fieldSet.split(':');
            key = key.trim();
            value = value.trim();
            const indicator = 'options';
            const pathNIndicator = key + KEY_INDICATOR_SEPARATOR + indicator;
            autocompleteDict[pathNIndicator] = value;
        } else if (fieldSet.indexOf('=') > 0) {
            // Handle assignments or server_populate (e.g., "field=defaultValue" or "field=server_populate").
            let [key, value] = fieldSet.split('=');
            key = key.trim();
            value = value.trim();
            const indicator = value === 'server_populate' ? 'server_populate' : 'assign';
            const pathNIndicator = key + KEY_INDICATOR_SEPARATOR + indicator;
            autocompleteDict[pathNIndicator] = value;
        } else {  // field separator is ~
            // Handle dynamic options (e.g., "field~DynamicOptions").
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


/**
 * Sets autocomplete-related properties on a collection object based on a parsed autocomplete dictionary.
 * This function applies options, dynamic autocomplete flags, or server-populate indicators
 * to the `object` if its path matches a key in `autocompleteDict`.
 * @param {Object} schema - The complete schema definition, used to retrieve autocomplete options.
 * @param {Object} object - The collection object to which autocomplete values will be applied.
 * @param {Object<string, string>} autocompleteDict - A dictionary of parsed autocomplete configurations.
 * @param {string} propname - The property name of the current field.
 * @param {string} usageName - The standardized usage name for the autocomplete property.
 */
export function setAutocompleteValue(schema, object, autocompleteDict, propname, usageName) {
    for (const pathNIndicator in autocompleteDict) {
        const [path, indicator] = pathNIndicator.split(KEY_INDICATOR_SEPARATOR);
        // Check if the current object's property name or its full XPath matches the autocomplete path.
        if (path === propname || object.xpath.endsWith(path)) {
            const value = autocompleteDict[pathNIndicator];
            object[usageName] = value;
            if (indicator === 'options') {
                // If it's an 'options' indicator, retrieve the actual options list from the schema.
                if (schema.autocomplete.hasOwnProperty(value)) {
                    object.options = schema.autocomplete[value];
                }
            } else if (indicator === 'dynamic_options') {
                // If it's a 'dynamic_options' indicator, set a flag and initialize options as empty.
                object.dynamic_autocomplete = true;
                object.options = [];
            } else if (indicator === 'server_populate') {
                // If it's 'server_populate', mark the object as server-populated and remove the usageName property.
                object.serverPopulate = true;
                delete object[usageName];
            }
        }
    }
}


/**
 * Converts an array of "key:value" strings into a dictionary.
 * @param {Array<string>} array - An array of strings, where each string is in the format "key:value".
 * @returns {Object<string, string>} A dictionary where keys are extracted from the string and values are their corresponding values.
 */
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


/**
 * Converts a `mappingSrc` array into a dictionary using `getKeyValueDictFromArray`.
 * @param {Array<string>} mappingSrc - An array of strings, where each string is in the format "key:value".
 * @returns {Object<string, string>} A dictionary representing the mapping source.
 */
export function getMappingSrcDict(mappingSrc) {
    return getKeyValueDictFromArray(mappingSrc)
}


/**
 * Converts a `metaFieldList` array into a dictionary using `getKeyValueDictFromArray`.
 * @param {Array<string>} metaFieldList - An array of strings, where each string is in the format "key:value".
 * @returns {Object<string, string>} A dictionary representing the meta field list.
 */
export function getMetaFieldDict(metaFieldList) {
    return getKeyValueDictFromArray(metaFieldList);
}

/**
 * Recursively creates a collection of schema properties, transforming them into a flat list of `collection` objects.
 * Each `collection` object represents a field with its attributes, including type, title, XPath, and other metadata.
 * This function handles primitive types, arrays, and nested objects, and applies various schema-defined properties.
 * @param {Object} schema - The complete schema definition.
 * @param {Object} currentSchema - The current schema (or sub-schema) being processed.
 * @param {Object} callerProps - Properties passed from the calling function, including `xpath`, `parentSchema`, and `mode`.
 * @param {Array<Object>} [collections=[]] - The array to accumulate the created collection objects.
 * @param {Object} [sequence={ sequence: 1 }] - An object to maintain a unique sequence number for each collection.
 * @param {string} [xpath] - The current XPath of the field being processed.
 * @param {string} [objectxpath] - The XPath of the parent object, used for `tableTitle`.
 * @param {string} [metaFieldId] - An ID for meta fields, used for `mapping_underlying_meta_field`.
 * @returns {Array<Object>} The array of created collection objects.
 */
export function createCollections(schema, currentSchema, callerProps, collections = [], sequence = { sequence: 1 }, xpath, objectxpath, metaFieldId) {
    currentSchema = cloneDeep(currentSchema);

    if (callerProps.xpath) {
        let currentSchemaMetadata = callerProps.parentSchema.properties[callerProps.xpath];

        complexFieldProps.forEach(({ propertyName }) => {
            if (currentSchemaMetadata.hasOwnProperty(propertyName)) {
                currentSchema[propertyName] = currentSchemaMetadata[propertyName];
            }
        });
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
            });

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
            });

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
            });

            arrayFieldProps.map(({ propertyName, usageName }) => {
                if (v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName];
                }
            });

            // for array of primitive data types
            if (!v.hasOwnProperty('items') || (v.hasOwnProperty('items') && primitiveDataTypes.includes(collection.underlyingtype))) {
                collections.push(collection);
                return;
            }

            let ref = v.items.$ref.split('/');
            let record = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            record = cloneDeep(record);

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    record[propertyName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                }
            });
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
            });

            let ref = v.items.$ref.split('/');
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
            });
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


/**
 * Generates a new object based on a given schema, populating it with default values and handling nested structures.
 * This function recursively traverses the schema properties and creates a corresponding JavaScript object.
 * It respects `server_populate` and `ui_update_only` flags, and handles different data types including arrays and objects.
 * @param {Object} schema - The complete schema definition.
 * @param {Object} currentSchema - The current schema (or sub-schema) from which to generate the object.
 * @param {Object} [additionalProps] - Additional properties to apply to the schema before object generation.
 * @param {string} [objectxpath] - The XPath of the parent object, used for constructing full XPaths.
 * @param {Object} [objToDup] - An optional object to duplicate values from, used during object creation.
 * @returns {Object} The newly generated object.
 */
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

        // For primitive types, always copy from objToDup if duplicating
        if (objToDup && [DATA_TYPES.STRING, DATA_TYPES.NUMBER, DATA_TYPES.BOOLEAN, DATA_TYPES.DATE_TIME, DATA_TYPES.ENUM].includes(metadata.type)) {
            object[propname] = get(objToDup, xpath);
            return;
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
                let ref = metadata.items.$ref.split('/');
                let enumdata = getEnumValues(schema, ref, metadata.type);
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
                //this makes sure when duplicating , array of objects are empty
                if (objToDup) {
                    object[propname] = get(objToDup, xpath) || [];
                } else {
                    object[propname] = [];
                }
            } else {
                let ref = metadata.items.$ref.split('/');
                let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
                childSchema = cloneDeep(childSchema);

                if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                    childSchema.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                }

                if (!childSchema.server_populate && !metadata.server_populate) {
                    if (objToDup) {
                        object[propname] = [];
                    } else {
                        object[propname] = [];
                        let child = generateObjectFromSchema(schema, childSchema, null, xpath, null);
                        object[propname].push(child);
                    }
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


/**
 * Retrieves the enumeration values from the schema based on a reference and type.
 * @param {Object} schema - The complete schema definition.
 * @param {Array<string>} ref - An array of strings representing the path to the enum definition within the schema (e.g., `['#', 'definitions', 'MyEnum']`).
 * @param {string} type - The data type, expected to be `DATA_TYPES.ENUM`.
 * @returns {Array<string>|Object} An array of enum values if the type is `DATA_TYPES.ENUM`, otherwise the referenced schema object.
 */
export function getEnumValues(schema, ref, type) {
    if (type === DATA_TYPES.ENUM) {
        // If the type is ENUM, return the 'enum' array from the referenced schema definition.
        return schema[ref[1]][ref[2]]['enum'];
    }
    // Otherwise, return the entire referenced schema object.
    return schema[ref[1]][ref[2]];
}

/**
 * Sorts the properties of a schema object based on their `sequence_number` attribute.
 * Properties with lower `sequence_number` values will appear earlier in the sorted object.
 * @param {Object} properties - An object where keys are property names and values are property metadata objects (expected to have `sequence_number`).
 * @returns {Object} A new object with properties sorted by `sequence_number`.
 */
export function sortSchemaProperties(properties) {
    return Object.keys(properties).sort(function (a, b) {
        // Compare based on sequence_number. If a.sequence_number is less than b.sequence_number, a comes first.
        if (properties[a].sequence_number < properties[b].sequence_number) return -1;
        else return 1;
    }).reduce(function (obj, key) {
        // Reconstruct the object with sorted properties.
        obj[key] = properties[key];
        return obj;
    }, {});
}

/**
 * Finds and returns the parent schema of a given schema by searching through the schema definitions.
 * A parent schema is identified if it is an object type and contains the `currentSchemaName` in its properties.
 * @param {Object} schema - The complete schema definition.
 * @param {string} currentSchemaName - The name of the schema for which to find the parent.
 * @returns {Object|undefined} The parent schema object, or `undefined` if no parent is found.
 */
export function getParentSchema(schema, currentSchemaName) {
    let parentSchema;
    // Iterate through all schema definitions.
    Object.keys(get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {
        let current = get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);
        // Check if the current schema is an object type and contains the target schema as a property.
        if (current.type === DATA_TYPES.OBJECT && has(current.properties, currentSchemaName)) {
            parentSchema = current;
        }
        return;
    });
    return parentSchema;
}

/**
 * Retrieves a model's schema definition from the overall schema object.
 * It first checks for a direct top-level model name, then falls back to searching within `SCHEMA_DEFINITIONS_XPATH`.
 * @param {string} modelName - The name of the model whose schema is to be retrieved.
 * @param {Object} schema - The complete schema definition object.
 * @returns {Object} The schema definition for the specified model.
 */
export function getModelSchema(modelName, schema) {
    // Attempt to retrieve the schema directly by modelName, or from within SCHEMA_DEFINITIONS_XPATH.
    return schema[modelName] || schema[SCHEMA_DEFINITIONS_XPATH][modelName];
}

