import _, { cloneDeep } from 'lodash';
import {
    ColorPriority, ColorTypes, DataTypes, HoverTextType, Modes, ShapeType, SizeType,
    DB_ID, NEW_ITEM_ID, SCHEMA_DEFINITIONS_XPATH
} from './constants';
import Node from './components/Node';
import HeaderField from './components/HeaderField';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
dayjs.extend(utc);

// stores the tree expand/collapse states
const treeState = {};
const primitiveDataTypes = [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM, DataTypes.DATE_TIME, DataTypes.INT64, DataTypes.FLOAT];

export const FLOAT_POINT_PRECISION = 2;
export const Message = {
    REQUIRED_FIELD: 'required field cannot be null',
    UNSPECIFIED_FIELD: 'enum field cannot be unset / UNSPECIFIED',
    MAX: 'field value exceeds the max limit',
    MIN: 'field value exceeds the min limit'
}

// complex field properties that are to be passed to the child components
const complexFieldProps = [
    { propertyName: "server_populate", usageName: "serverPopulate" },
    { propertyName: "ui_update_only", usageName: "uiUpdateOnly" },
    { propertyName: "orm_no_update", usageName: "ormNoUpdate" },
    { propertyName: "auto_complete", usageName: "autocomplete" },
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    { propertyName: "filter_enable", usageName: "filterEnable" }
]

const fieldProps = [
    { propertyName: "type", usageName: "type" },
    { propertyName: "title", usageName: "title" },
    { propertyName: "hide", usageName: "hide" },
    { propertyName: "help", usageName: "help" },
    { propertyName: "cmnt", usageName: "description" },
    { propertyName: "default", usageName: "default" },
    { propertyName: "underlying_type", usageName: "underlyingtype" },
    { propertyName: "ui_placeholder", usageName: "placeholder" },
    { propertyName: "color", usageName: "color" },
    { propertyName: "button", usageName: "button" },
    { propertyName: "abbreviated", usageName: "abbreviated" },
    { propertyName: "val_max", usageName: "max" },
    { propertyName: "val_min", usageName: "min" },
    { propertyName: "default_value_placeholder_string", usageName: "defaultValuePlaceholderString" },
    { propertyName: "val_sort_weight", usageName: "sortWeight" },
    { propertyName: "val_is_date_time", usageName: "dateTime" },
    { propertyName: "index", usageName: "index" },
    { propertyName: "sticky", usageName: "sticky" },
    { propertyName: "size_max", usageName: "sizeMax" },
    { propertyName: "progress_bar", usageName: "progressBar" },
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    { propertyName: "name_color", usageName: "nameColor" },
    { propertyName: "number_format", usageName: "numberFormat" },
    { propertyName: "no_common_key", usageName: "noCommonKey" },
    { propertyName: "display_type", usageName: "displayType" },
    { propertyName: "text_align", usageName: "textAlign" },
    { propertyName: "display_zero", usageName: "displayZero" },
    { propertyName: "micro_separator", usageName: "microSeparator" }
]

// properties supported explicitly on the array types
const arrayFieldProps = [
    { propertyName: "alert_bubble_source", usageName: "alertBubbleSource" },
    { propertyName: "alert_bubble_color", usageName: "alertBubbleColor" }
]

const timeIt = (target, property, descriptor) => {
    const callback = descriptor.value;

    descriptor.value = function (...args) {
        console.time(property);
        const res = callback.apply(this, args);
        console.timeEnd(property);
        return res;
    };

    return descriptor;
}

export function setTreeState(xpath, state) {
    treeState[xpath] = state;
}

function getAutocompleteDict(autocompleteValue) {
    let autocompleteFieldSet = autocompleteValue.split(',').map((field) => field.trim());
    let autocompleteDict = {};

    autocompleteFieldSet.map((fieldSet) => {
        if (fieldSet.indexOf(':') > 0) {
            let [key, value] = fieldSet.split(':');
            autocompleteDict[key] = value;
        } else {
            let [key, value] = fieldSet.split('=');
            autocompleteDict[key] = value;
        }
    })
    return autocompleteDict;
}

function setAutocompleteValue(schema, object, autocompleteDict, propname, usageName) {
    if (autocompleteDict.hasOwnProperty(propname)) {
        object[usageName] = autocompleteDict[propname];
        let autocomplete = autocompleteDict[propname];
        if (schema.autocomplete.hasOwnProperty(object[usageName])) {
            object.options = schema.autocomplete[autocomplete];
        } else {
            if (autocomplete === 'server_populate') {
                object.serverPopulate = true;
                delete object[usageName];
            }
            //  else {
            //     // set enum with default value and prevent reducing the enum options
            //     // object.options = [autocomplete];
            //     object.value = autocomplete;
            // }
        }
    }
}

export function createCollections(schema, currentSchema, callerProps, collections = [], sequence = { sequence: 1 }, xpath, objectxpath) {
    currentSchema = cloneDeep(currentSchema);

    if (callerProps.xpath) {
        let currentSchemaMetadata = callerProps.parentSchema.properties[callerProps.xpath];

        complexFieldProps.map(({ propertyName }) => {
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
            collection.required = currentSchema.required.filter(p => p === k).length > 0 ? true : false;
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

            if (v.type === DataTypes.ENUM) {
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
                }
            })

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];

                    if (propertyName === 'auto_complete') {
                        let autocompleteDict = getAutocompleteDict(collection[usageName]);
                        setAutocompleteValue(schema, collection, autocompleteDict, k, usageName);
                        if (!collection.hasOwnProperty('options')) {
                            delete collection[usageName];
                        }
                    }
                }
            })

            let isRedundant = true;
            if (collections.filter(col => col.tableTitle === collection.tableTitle).length === 0) {
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                    isRedundant = false;
                }
            }

            if (!isRedundant) {
                collections.push(collection);
            }

        } else if (v.type === DataTypes.ARRAY) {
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
            if (collections.filter(col => col.tableTitle === collection.tableTitle).length === 0) {
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                    isRedundant = false;
                }
            }
            if (!isRedundant) {
                collections.push(collection);
            }

            if (collection.abbreviated === 'JSON') {
                const sc = createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
                collection.subCollections = cloneDeep(sc);
            } else {
                createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
            }
        } else if (v.type === DataTypes.OBJECT) {
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

            complexFieldProps.map(({ propertyName, usageName }) => {
                if (currentSchema.hasOwnProperty(propertyName) || v.hasOwnProperty(propertyName)) {
                    collection[usageName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                    record[propertyName] = v[propertyName] ? v[propertyName] : currentSchema[propertyName];
                }
            })
            collection.properties = record.properties;

            let isRedundant = true;
            if (collections.filter(col => col.tableTitle === collection.tableTitle).length === 0) {
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                    isRedundant = false;
                }
            }

            if (!isRedundant) {
                collections.push(collection);
            }
            if (collection.abbreviated === 'JSON') {
                const sc = createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
                collection.subCollections = cloneDeep(sc);
            } else {
                createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
            }
        }
    });
    return collections;
}

export function generateObjectFromSchema(schema, currentSchema, additionalProps) {
    if (additionalProps && additionalProps instanceof Object) {
        for (const key in additionalProps) {
            const prop = complexFieldProps.find(({ usageName }) => usageName === key);
            if (prop) {
                currentSchema[prop.propertyName] = additionalProps[key]
            } else {
                delete additionalProps[key];
            }
        }
    }

    let object = {};
    Object.keys(currentSchema.properties).map((propname) => {
        let metadata = currentSchema.properties[propname];

        // do not create fields if populated from server or creation is not allowed on the fields.
        if (metadata.server_populate || metadata.ui_update_only) return;

        if (metadata.type === DataTypes.STRING) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : null;
            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteDict = getAutocompleteDict(autocomplete);

                if (autocompleteDict.hasOwnProperty(propname)) {
                    if (!schema.autocomplete.hasOwnProperty(autocompleteDict[propname])) {
                        if (autocompleteDict[propname] === 'server_populate') {
                            delete object[propname];
                        } else {
                            object[propname] = autocompleteDict[propname];
                        }
                    }
                }
            }
        } else if (metadata.type === DataTypes.NUMBER) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : null;
        } else if (metadata.type === DataTypes.BOOLEAN) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : false;
        } else if (metadata.type === DataTypes.ENUM) {
            let ref = metadata.items.$ref.split('/')
            let enumdata = getEnumValues(schema, ref, metadata.type)
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : enumdata ? enumdata[0] : null;

            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteDict = getAutocompleteDict(autocomplete);

                if (autocompleteDict.hasOwnProperty(propname)) {
                    if (!schema.autocomplete.hasOwnProperty(autocompleteDict[propname])) {
                        if (autocompleteDict[propname] === 'server_populate') {
                            delete object[propname];
                        } else {
                            object[propname] = autocompleteDict[propname];
                        }
                    }
                }
            }
        } else if (metadata.type === DataTypes.ARRAY) {
            // for arrays of primitive data types
            if (!metadata.hasOwnProperty('items') || (metadata.hasOwnProperty('items') && primitiveDataTypes.includes(metadata.underlying_type))) {
                object[propname] = [];
            } else {
                let ref = metadata.items.$ref.split('/');
                let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];

                if (!childSchema.server_populate && !metadata.server_populate) {
                    let child = generateObjectFromSchema(schema, childSchema);;
                    object[propname] = [];
                    object[propname].push(child);
                }
            }
        } else if (metadata.type === DataTypes.OBJECT) {
            let ref = metadata.items.$ref.split('/');
            let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            childSchema = cloneDeep(childSchema);
            const required = currentSchema.required.filter(prop => prop === propname).length > 0 ? true : false;

            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                childSchema.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
            }

            if (!(childSchema.server_populate || childSchema.ui_update_only)) {
                if (required) {
                    object[propname] = generateObjectFromSchema(schema, childSchema);
                } else {
                    object[propname] = null;
                }

            }
        }
    });
    return object;
}

function getEnumValues(schema, ref, type) {
    if (type == DataTypes.ENUM) {
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
        if (_.get(data, updatedxpath + currentxpath)) {
            _.get(data, updatedxpath + currentxpath).forEach((obj, idx) => {
                let propname = _.keys(obj).filter(key => key.startsWith('xpath_'))[0];
                if (!propname) return;
                let propxpath = obj[propname].substring(0, obj[propname].lastIndexOf('.'));
                if (propxpath === originalxpath) {
                    index = idx;
                    found = true;
                }
            })
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

function compareNodes(originalData, data, dataxpath, propname, xpath) {
    let object = {};
    let current = data[propname];
    let original = originalData[propname];
    if (dataxpath || xpath) {
        current = hasxpath(data, dataxpath) ? _.get(data, dataxpath)[propname] : undefined;
        original = hasxpath(originalData, xpath) ? _.get(originalData, xpath)[propname] : undefined;
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

function addSimpleNode(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath, additionalProps) {
    let node = {};
    const data = callerProps.data;
    const originalData = callerProps.originalData;

    // do not add field if not present in both modified data and original data.
    if ((Object.keys(data).length === 0 && Object.keys(originalData).length === 0) || (dataxpath && _.get(data, dataxpath) === undefined && _.get(originalData, xpath) === undefined)) return;

    if (primitiveDataTypes.includes(currentSchema)) {
        node.id = dataxpath;
        node.required = true;
        node.xpath = xpath;
        node.dataxpath = dataxpath;
        node.customComponent = Node;
        node.onTextChange = callerProps.onTextChange;
        node.onFormUpdate = callerProps.onFormUpdate;
        node.mode = callerProps.mode;
        node.showDataType = callerProps.showDataType;
        node.type = currentSchema;
        node.underlyingtype = additionalProps.underlyingtype;

        if (node.type === DataTypes.ENUM) {
            node.dropdowndataset = additionalProps.options;
            node.onSelectItemChange = callerProps.onSelectItemChange;
        }

        node.value = dataxpath ? _.get(data, dataxpath) : undefined;
        tree.push(node);
        return;
    }

    let attributes = currentSchema.properties[propname];
    if (attributes.hasOwnProperty('type') && primitiveDataTypes.includes(attributes.type)) {
        node.id = propname;
        node.key = propname;
        node.required = currentSchema.required.filter(p => p === propname).length > 0 ? true : false;
        node.xpath = xpath ? xpath + '.' + propname : propname;
        node.dataxpath = dataxpath ? dataxpath + '.' + propname : propname;
        node.parentcollection = currentSchema.title;
        node.customComponent = Node;
        node.onTextChange = callerProps.onTextChange;
        node.onFormUpdate = callerProps.onFormUpdate;
        node.mode = callerProps.mode;
        node.showDataType = callerProps.showDataType;
        node.index = callerProps.index;
        node.forceUpdate = callerProps.forceUpdate;

        fieldProps.map(({ propertyName, usageName }) => {
            if (attributes.hasOwnProperty(propertyName)) {
                node[usageName] = attributes[propertyName];
            }
        })

        node.value = dataxpath ? hasxpath(data, dataxpath) ? _.get(data, dataxpath)[propname] : undefined : data[propname];

        if (attributes.type === DataTypes.BOOLEAN) {
            node.onCheckboxChange = callerProps.onCheckboxChange;
        }

        if (attributes.type === DataTypes.ENUM) {
            let ref = attributes.items.$ref.split('/')
            let enumdata = getEnumValues(schema, ref, attributes.type);
            node.dropdowndataset = enumdata;
            node.onSelectItemChange = callerProps.onSelectItemChange;
        }

        if (attributes.type === DataTypes.DATE_TIME) {
            node.onDateTimeChange = callerProps.onDateTimeChange;
        }

        complexFieldProps.map(({ propertyName, usageName }) => {
            if (currentSchema.hasOwnProperty(propertyName) || attributes.hasOwnProperty(propertyName)) {
                node[usageName] = attributes[propertyName] ? attributes[propertyName] : currentSchema[propertyName];

                if (propertyName === 'auto_complete') {
                    let autocompleteDict = getAutocompleteDict(node[usageName]);
                    setAutocompleteValue(schema, node, autocompleteDict, propname, usageName);
                    if (node.hasOwnProperty('options')) {
                        node.customComponentType = 'autocomplete';
                        node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
                    } else {
                        delete node[usageName];
                    }
                }
            }
        })

        let newprop = compareNodes(originalData, data, dataxpath, propname, xpath);
        node = { ...node, ...newprop };

        let isRedundant = true;
        if (!(node.serverPopulate && callerProps.mode === Modes.EDIT_MODE) && !(node.hide && callerProps.hide) && !(node.uiUpdateOnly && node.value === undefined)) {
            isRedundant = false;
            if (node.type === DataTypes.BOOLEAN && node.button && callerProps.mode === Modes.EDIT_MODE) {
                isRedundant = true;
            }
        }

        if (!isRedundant) {
            tree.push({ ...node });
        }
    }
}

function addHeaderNode(node, currentSchema, propname, type, callerProps, dataxpath, xpath, ref, objectState) {
    let headerNode = {};
    headerNode.id = Math.random();
    headerNode.key = propname;
    headerNode.title = currentSchema.title;
    headerNode.name = propname;
    headerNode.type = type
    headerNode.ref = ref;
    headerNode.help = currentSchema.help;
    headerNode.mode = callerProps.mode;
    headerNode.customComponent = HeaderField;
    headerNode.xpath = xpath;
    fieldProps.map(({ propertyName, usageName }) => {
        if (currentSchema.hasOwnProperty(propertyName)) {
            headerNode[usageName] = currentSchema[propertyName];
        }
    })

    complexFieldProps.map(({ propertyName, usageName }) => {
        if (currentSchema.hasOwnProperty(propertyName)) {
            headerNode[usageName] = currentSchema[propertyName];
        }
    })

    headerNode.required = !ref ? true : currentSchema.required ? currentSchema.required.some(prop => prop === propname) : true;
    headerNode.uiUpdateOnly = currentSchema.ui_update_only;

    if (!dataxpath) {
        headerNode['data-remove'] = true;
    }

    if (objectState) {
        const { add, remove } = objectState;
        if (add) {
            headerNode['object-add'] = true;
        }
        if (remove) {
            headerNode['object-remove'] = true;
        }
    }

    if (treeState.hasOwnProperty(xpath)) {
        treeState[xpath] = callerProps.isOpen ? true : callerProps.isOpen === false ? false : treeState[xpath];
    } else {
        treeState[xpath] = true;
    }

    headerNode.isOpen = treeState[xpath];
    headerNode.children = [];
    node.push(headerNode);
    return headerNode.children;
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

export function generateTreeStructure(schema, currentSchemaName, callerProps, topLevel = true) {
    // return if full schema is not present
    let tree = [];
    if (schema === undefined || schema === null || Object.keys(schema).length === 0) return tree;

    let currentSchema;
    if (topLevel) {
        currentSchema = _.get(schema, currentSchemaName);
    } else {
        currentSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, currentSchemaName]);
    }
    let childNode;
    if (currentSchema.widget_ui_data_element && currentSchema.widget_ui_data_element.is_repeated) {
        childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DataTypes.ARRAY, callerProps, currentSchemaName, currentSchemaName);
        for (let i = 0; i < callerProps.data.length; i++) {
            let dataxpath = "[" + i + "]";
            let node = addHeaderNode(childNode, currentSchema, currentSchemaName, DataTypes.OBJECT, callerProps, dataxpath, dataxpath);
            Object.keys(currentSchema.properties).map((propname) => {
                if (callerProps.xpath && callerProps.xpath !== propname) return;
                let metadataProp = currentSchema.properties[propname];
                if (metadataProp.hasOwnProperty('type') && primitiveDataTypes.includes(metadataProp.type)) {
                    addSimpleNode(node, schema, currentSchema, propname, callerProps, dataxpath, null, dataxpath);
                }
                else {
                    dataxpath += dataxpath + "." + propname;
                    addNode(node, schema, metadataProp, propname, callerProps, dataxpath, null, dataxpath);
                }
            });
        }
    } else {
        childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DataTypes.OBJECT, callerProps, currentSchemaName, currentSchemaName);
        Object.keys(currentSchema.properties).map((propname) => {
            if (callerProps.xpath && callerProps.xpath !== propname) return;
            let metadataProp = currentSchema.properties[propname];
            if (!currentSchema.required.includes(propname)) {
                metadataProp.required = [];
            }
            if (metadataProp.hasOwnProperty('type') && primitiveDataTypes.includes(metadataProp.type)) {
                addSimpleNode(childNode, schema, currentSchema, propname, callerProps);
            }
            else {
                addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
            }
        });
    }
    return tree;
}

function addNode(tree, schema, currentSchema, propname, callerProps, dataxpath, type, xpath) {
    const data = callerProps.data;
    const originalData = callerProps.originalData;
    let currentSchemaType = type ? type : currentSchema.type;

    if (currentSchema.hasOwnProperty('items') && currentSchemaType === DataTypes.OBJECT) {
        if (_.get(data, dataxpath) === undefined && _.get(originalData, xpath) === undefined) return;
        let headerState = {};
        if (_.get(originalData, xpath) === undefined) {
            if (_.get(data, xpath) === null) {
                headerState.add = true;
                headerState.remove = false;
            } else {
                headerState.add = false;
                headerState.remove = true;
            }
        } else if (currentSchema.hasOwnProperty('orm_no_update')) {
            if (_.get(originalData, xpath) !== undefined) {
                headerState.add = false;
                headerState.remove = false;
            }
        } else if (!currentSchema.hasOwnProperty('orm_no_update')) {
            if (_.get(data, dataxpath) === null) {
                headerState.add = true;
                headerState.remove = false;
            } else {
                headerState.add = false;
                headerState.remove = true;
            }
        }
        if (callerProps.mode === Modes.EDIT_MODE && currentSchema.hasOwnProperty('server_populate')) return;
        let childNode = addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, dataxpath, xpath, currentSchema.items.$ref, headerState);
        if (_.get(data, dataxpath) === null && (_.get(originalData, xpath) === undefined || _.get(originalData, xpath) === null)) return;
        let ref = currentSchema.items.$ref.split('/');
        let metadata = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
        metadata = cloneDeep(metadata);

        // if (currentSchema.hasOwnProperty('required') && currentSchema.required.length === 0) {
        //     metadata.required = [];
        // }

        if (currentSchema.hasOwnProperty('orm_no_update') || metadata.hasOwnProperty('orm_no_update')) {
            metadata.orm_no_update = metadata.no_orm_update ? metadata.no_orm_update : currentSchema.orm_no_update;
        }

        if (currentSchema.hasOwnProperty('server_populate') || metadata.hasOwnProperty('server_populate')) {
            metadata.server_populate = metadata.server_populate ? metadata.server_populate : currentSchema.server_populate;
            if (callerProps.mode === Modes.EDIT_MODE) return;
        }

        if (currentSchema.hasOwnProperty('ui_update_only') || metadata.hasOwnProperty('ui_update_only')) {
            metadata.ui_update_only = metadata.ui_update_only ? metadata.ui_update_only : currentSchema.ui_update_only;
        }

        if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
            metadata.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
        }

        if (metadata.hasOwnProperty('properties')) {
            Object.keys(metadata.properties).forEach((prop) => {
                let metadataProp = metadata.properties[prop];
                if (!metadata.required.includes(prop)) {
                    metadataProp.required = [];
                }
                if (metadata.hasOwnProperty('ui_update_only')) {
                    metadataProp.ui_update_only = metadata.ui_update_only;
                }
                if (metadata.hasOwnProperty('server_populate')) {
                    metadataProp.ui_update_only = metadata.server_populate;
                }
                if (metadata.hasOwnProperty('orm_no_update')) {
                    metadataProp.orm_no_update = metadata.orm_no_update;
                }
                if (metadata.hasOwnProperty('auto_complete')) {
                    metadataProp.auto_complete = metadata.auto_complete;
                }
                if (metadataProp.hasOwnProperty('type') && (metadataProp.type === DataTypes.OBJECT)) {
                    let childxpath = dataxpath;
                    if (childxpath) {
                        childxpath = childxpath + '.' + prop;
                    }
                    let updatedxpath = xpath + '.' + prop;
                    addNode(childNode, schema, metadataProp, prop, callerProps, childxpath, null, updatedxpath);
                } else if (metadataProp.hasOwnProperty('type') && primitiveDataTypes.includes(metadataProp.type)) {
                    addSimpleNode(childNode, schema, metadata, prop, callerProps, dataxpath, xpath);
                } else {
                    let childxpath = dataxpath;
                    if (childxpath) {
                        childxpath = childxpath + '.' + prop;
                    }
                    let updatedxpath = xpath + '.' + prop;
                    addNode(childNode, schema, metadataProp, prop, callerProps, childxpath, null, updatedxpath);
                }
            });
        }
    } else if (currentSchema.hasOwnProperty('items') && currentSchema.type === DataTypes.ARRAY && !primitiveDataTypes.includes(currentSchema.underlying_type)) {
        if (callerProps.mode === Modes.EDIT_MODE && currentSchema.hasOwnProperty('server_populate')) return;
        if (((_.get(data, dataxpath) && _.get(data, dataxpath).length === 0) || (_.keys(data).length > 0 && !_.get(data, dataxpath))) &&
            ((_.get(originalData, xpath) && _.get(originalData, xpath).length === 0) || !_.get(originalData, xpath))) {
            let childxpath = dataxpath + '[-1]';
            let updatedxpath = xpath + '[-1]';
            addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, childxpath, updatedxpath, currentSchema.items.$ref);
        } else {
            let paths = [];
            if (_.get(originalData, xpath)) {
                for (let i = 0; i < _.get(originalData, xpath).length; i++) {
                    let updatedxpath = xpath + '[' + i + ']';
                    let childxpath = dataxpath + '[' + i + ']';
                    childxpath = getDataxpath(data, updatedxpath);
                    paths.push(updatedxpath);
                    if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) continue;
                    addNode(tree, schema, currentSchema, propname, callerProps, childxpath, DataTypes.OBJECT, updatedxpath);
                }
            }
            if (_.get(data, dataxpath)) {
                _.get(data, dataxpath).map((childobject, i) => {
                    let subpropname = _.keys(childobject).filter(key => key.startsWith('xpath_'))[0];
                    if (!subpropname) return;
                    let propxpath = childobject[subpropname];
                    let propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
                    let updatedxpath = xpath + '[' + propindex + ']';
                    if (paths.includes(updatedxpath)) return;
                    let childxpath = dataxpath + '[' + i + ']';
                    if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) return;
                    addNode(tree, schema, currentSchema, propname, callerProps, childxpath, DataTypes.OBJECT, updatedxpath);
                    paths.push(childxpath);

                })

            }
        }
    } else if (currentSchema.type === DataTypes.ARRAY) {
        // array of simple data types
        if ((_.get(originalData, xpath) === undefined) && _.get(data, dataxpath) === undefined) return;
        let arrayDataType = currentSchema.underlying_type;
        if ([DataTypes.INT32, DataTypes.INT64, DataTypes.INTEGER, DataTypes.FLOAT].includes(arrayDataType)) {
            arrayDataType = DataTypes.NUMBER;
        }
        let ref = arrayDataType;
        const additionalProps = {};
        additionalProps.underlyingtype = currentSchema.underlying_type;
        if (currentSchema.underlying_type === DataTypes.ENUM) {
            ref = currentSchema.items.$ref;
            let refSplit = ref.split('/');
            let metadata = refSplit.length === 2 ? schema[refSplit[1]] : schema[refSplit[1]][refSplit[2]];
            additionalProps.options = metadata.enum;
        }
        let childxpath = dataxpath + '[-1]';
        let updatedxpath = xpath + '[-1]';
        const objectState = { add: true, remove: false };
        const childNode = addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, childxpath, updatedxpath, ref, objectState);
        if (_.get(data, dataxpath)) {
            _.get(data, dataxpath).forEach((value, i) => {
                let childxpath = dataxpath + '[' + i + ']';
                let updatedxpath = xpath + '[' + i + ']';
                addSimpleNode(childNode, schema, arrayDataType, null, callerProps, childxpath, updatedxpath, additionalProps);
            })
        }
    }
}

function isNodeInSubtree(callerProps, xpath, dataxpath) {
    xpath = xpath.replace(/\[.\]/g, '[0]');
    if (callerProps.subtree) {
        if (callerProps.xpath) {
            xpath = xpath.substring(xpath.indexOf('.') + 1);
        }
        if (!_.get(callerProps.subtree, xpath + '[0]')) return false;
        else {
            let propname = _.keys(_.get(callerProps.subtree, xpath + '[0]')).filter(key => key.startsWith('xpath_'))[0];
            if (!propname) return false;
            let propxpath = xpath + '[0].' + propname
            propxpath = _.get(callerProps.subtree, propxpath);
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
        jsondata = _.get(jsondata, xpath);
    }
    if (!jsondata) {
        return trees;
    }

    while (true) {
        if (_.isArray(jsondata)) {
            for (let i = 0; i < jsondata.length; i++) {
                let tree = {};
                createTree(tree, jsondata[i], null, { delete: 1 }, collections);

                if (Object.keys(tree).length === 0) break;

                if (!constainsArray(tree)) {
                    tree['data-id'] = i;
                }

                if (trees.length > 0 && _.isEqual(trees[trees.length - 1], tree)) {
                    continue;
                }
                trees.push(tree);
            }
            break;
        } else {
            let tree = {};
            Object.entries(jsondata).map(([k, v]) => {
                if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
                    tree[k] = v;
                } else if (_.isNull(v)) {
                    tree[k] = null;
                } else if (Array.isArray(v)) {
                    tree[k] = [];
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections);
                } else if (_.isObject(v)) {
                    tree[k] = {};
                    createTree(tree, jsondata[k], k, { delete: 1 }, collections)
                }
            })

            if (Object.keys(tree).length === 0) break;

            if (!constainsArray(tree)) {
                tree['data-id'] = 0;
            }

            if (trees.length > 0 && _.isEqual(trees[trees.length - 1], tree)) {
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
        if (collections.filter((c) => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
            tree[propname] = currentjson;
        } else {
            if (currentjson[0] === null || primitiveDataTypes.includes(typeof currentjson[0])) {
                return;
            } else {
                let node = {};
                tree[propname].push(node);
                let xpath = currentjson[0][_.keys(currentjson[0]).filter(k => k.startsWith('xpath_'))[0]];
                xpath = xpath ? xpath.substring(0, xpath.lastIndexOf('.')) : xpath;
                node['data-id'] = xpath;
                createTree(tree[propname], currentjson[0], 0, count, collections);
                if (currentjson.length > 1 && count.delete > 0) {
                    count.delete -= 1;
                    currentjson.splice(0, 1);
                }
            }
        }
    } else if (_.isNull(currentjson)) {
        tree[propname] = null;
    } else if (_.isObject(currentjson)) {
        if (collections.filter((c) => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
            tree[propname] = currentjson;
        } else {
            let node = tree[propname];
            if (!node) {
                node = tree;
            }
            Object.entries(currentjson).map(([k, v]) => {
                if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
                    node[k] = v;
                } else if (typeof (v) === DataTypes.OBJECT) {
                    node[k] = {};
                    createTree(node, currentjson[k], k, count, collections);
                } else if (typeof (v) === DataTypes.ARRAY) {
                    node[k] = {};
                    createTree(node, currentjson[k], k, count, collections);
                }
            })
        }
    }
}


export function addxpath(jsondata, xpath) {
    if (_.isArray(jsondata)) {
        for (let i = 0; i < jsondata.length; i++) {
            let dataxpath = "[" + i + "]";
            if (xpath) {
                dataxpath = xpath + dataxpath;
            }
            _addxpath(jsondata[i], dataxpath)
        }
    } else {
        _addxpath(jsondata, xpath);
    }
    return jsondata;
}

function _addxpath(jsondata, xpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (_.isNull(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (Array.isArray(v)) {
            if (v.length > 0 && _.isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    let childxpath = xpath ? `${xpath}.${k}[${i}]` : `${k}[${i}]`;
                    addxpath(jsondata[k][i], childxpath);
                }
            } else {
                jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            }
        } else if (_.isObject(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            let childxpath = xpath ? xpath + '.' + k : k;
            addxpath(jsondata[k], childxpath)
        }
        return;
    });
}

export function clearxpath(jsondata) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            if (k.startsWith('xpath_')) {
                delete jsondata[k];
            }
        } else if (Array.isArray(v)) {
            if (v.length > 0 && _.isObject(v[0])) {
                for (let i = 0; i < v.length; i++) {
                    clearxpath(jsondata[k][i]);
                }
            }
        } else if (_.isObject(v)) {
            clearxpath(jsondata[k])
        }
    });
    return jsondata;
}

function flattenObject(jsondata, object, collections, xpath, parentxpath) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            if (parentxpath && k !== 'data-id') {
                if (xpath && xpath === parentxpath) {
                    object[k] = v;
                } else {
                    object[parentxpath + '.' + k] = v;
                }
            } else {
                object[k] = v;
            }
        } else if (_.isNull(v)) {
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
            if (collections.filter((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
                if (parentxpath) {
                    object[parentxpath + '.' + k] = v;
                } else {
                    object[k] = v;
                }
            } else if (v.length > 0) {
                let updatedParentxpath = parentxpath ? parentxpath + '.' + k : k;
                flattenObject(jsondata[k][0], object, collections, xpath, updatedParentxpath);
            }
        } else if (_.isObject(v)) {
            if (collections.filter((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
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
            if ((!_.get(original, updatedxpath) && _.get(original, updatedxpath) !== false && _.get(original, updatedxpath) !== 0) || !_.isEqual(_.get(updated, updatedxpath), _.get(original, updatedxpath))) {
                if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                let updatedxpath = xpath ? xpath + '.' + k + '[' + i + ']' : k + '[' + i + ']';
                if (primitiveDataTypes.includes(typeof (v[0]))) {
                    if ((!_.get(original, updatedxpath) && _.get(original, updatedxpath) !== false && _.get(original, updatedxpath) !== 0) || !_.isEqual(_.get(updated, updatedxpath), _.get(original, updatedxpath))) {
                        if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
                    }
                } else {
                    compareObjects(updated, original, current[k][i], updatedxpath, diff);
                }
            }
        } else if (_.isObject(v)) {
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
            let collection = collections.filter(c => c.key === key)[0];
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

export function getIdFromAbbreviatedKey(abbreviated, abbreviatedKey) {
    let abbreviatedSplit = abbreviated.split('-');
    let idIndex = -1;
    abbreviatedSplit.map((text, index) => {
        if (text.indexOf(DB_ID) > 0) {
            idIndex = index;
        }
    })
    if (idIndex !== -1) {
        let abbreviatedKeySplit = abbreviatedKey.split('-');
        let abbreviatedKeyId = parseInt(abbreviatedKeySplit[idIndex]);
        return abbreviatedKeyId;
    } else {
        // abbreviated key id not found. returning -1
        return idIndex;
    }
}

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

export function getAlertBubbleCount(data, alertBubbleSourceXpath) {
    let alertBubbleCount = 0;
    if (_.get(data, alertBubbleSourceXpath)) {
        alertBubbleCount = _.get(data, alertBubbleSourceXpath).length;
    }
    return alertBubbleCount;
}

export function getColorTypeFromValue(collection, value) {
    let color = ColorTypes.UNSPECIFIED;
    if (collection && collection.color) {
        let colorSplit = collection.color.split(',');
        for (let i = 0; i < colorSplit.length; i++) {
            let valueColorSet = colorSplit[i].trim();
            let [val, colorType] = valueColorSet.split('=');
            if (val === value) {
                color = ColorTypes[colorType];
                break;
            }
        }
    }
    return color;
}

export function getColorTypeFromPercentage(collection, percentage) {
    let color = ColorTypes.UNSPECIFIED;
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
                        color = ColorTypes[colorType];
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
                        color = ColorTypes[colorType];
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
            if (ColorPriority[a] > ColorPriority[b]) {
                return -1;
            }
            return 1;
        })
        return colorTypesArray[0];
    } else {
        return ColorTypes.UNSPECIFIED;
    }
}

export function getAlertBubbleColor(data, collections, alertBubbleSourceXpath, alertBubbleColorXpath) {
    let alertBubbleColorKey = alertBubbleColorXpath.split('.').pop();
    let collection = collections.filter(col => col.key === alertBubbleColorKey)[0];
    let alertBubbleColorRelativePath = alertBubbleColorXpath.replace(alertBubbleSourceXpath, '');
    let alertBubbleColorTypes = new Set();
    if (_.get(data, alertBubbleSourceXpath) && _.get(data, alertBubbleSourceXpath).length > 0) {
        for (let i = 0; i < _.get(data, alertBubbleSourceXpath).length; i++) {
            let value = _.get(data, alertBubbleSourceXpath + '[' + i + ']' + alertBubbleColorRelativePath);
            let colorType = getColorTypeFromValue(collection, value);
            alertBubbleColorTypes.add(colorType);
        }
    }
    return getPriorityColorType(alertBubbleColorTypes);
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
    if (SizeType.hasOwnProperty(size)) {
        return SizeType[size];
    }
    return SizeType.UNSPECIFIED;

}

export function getShapeFromValue(value) {
    let shape = value.split('_').pop();
    if (ShapeType.hasOwnProperty(shape)) {
        return ShapeType[shape];
    }
    return ShapeType.UNSPECIFIED;
}

export function isValidJsonString(jsonString) {
    if (typeof (jsonString) !== DataTypes.STRING) return false;
    jsonString = jsonString.replace(/\\/g, '');
    try {
        JSON.parse(jsonString);
    } catch (e) {
        return false;
    }
    return true;
}

export function hasxpath(data, xpath) {
    if (_.get(data, xpath)) return true;
    else {
        let value = _.get(data, xpath);
        if (value === 0 || value === false || value === '') return true;
    }
    return false;
}

export function getTableColumns(collections, mode, enableOverride = [], disableOverride = []) {
    let columns = collections
        .map(collection => Object.assign({}, collection))
        .map(collection => {
            if (enableOverride.includes(collection.tableTitle)) {
                collection.hide = true;
            }
            if (disableOverride.includes(collection.tableTitle)) {
                collection.hide = false;
            }
            return collection;
        })
        .filter(collection => {
            if (collection.serverPopulate && mode === Modes.EDIT_MODE) {
                return false;
            } else if (primitiveDataTypes.includes(collection.type)) {
                return true;
            } else if (collection.abbreviated && collection.abbreviated === "JSON") {
                return true;
            } else if (collection.type === 'button' && !collection.rootLevel) {
                return true;
            } else if (collection.type === 'progressBar') {
                return true;
            }
            return false;
        })
    return columns;
}

export function getCommonKeyCollections(rows, tableColumns, hide = true, collectionView = false) {
    if (rows.length > 1) {
        tableColumns = tableColumns.map(column => Object.assign({}, column)).filter(column => !column.noCommonKey);
    }
    let commonKeyCollections = [];
    if (rows.length > 0) {
        tableColumns.map((column) => {
            if (hide && column.hide) return;
            if (collectionView) {
                if (column.type === 'button' || column.type === 'progressBar') {
                    return;
                }
            }

            let found = true;
            for (let i = 0; i < rows.length - 1; i++) {
                if (!_.isEqual(rows[i][column.tableTitle], rows[i + 1][column.tableTitle])) {
                    const values = [rows[i][column.tableTitle], rows[i + 1][column.tableTitle]];
                    for (let i = 0; i < values.length; i++) {
                        let val = values[i];
                        if (val) {
                            if (typeof val === DataTypes.STRING) {
                                val = val.trim();
                            }
                        }
                        if (![null, undefined, ''].includes(val)) {
                            found = false;
                            break;
                        }
                    }
                }
                if (!found) {
                    break;
                }
            }
            if (found) {
                let collection = column;
                collection.value = rows[0][column.tableTitle];
                commonKeyCollections.push(collection);
            }
            return column;
        })
    }
    return commonKeyCollections;
}

export function getTableRowsFromData(collections, data, xpath) {
    let trees = generateRowTrees(cloneDeep(data), collections, xpath);
    let rows = generateRowsFromTree(trees, collections, xpath);
    return rows;
}

export function getTableRows(collections, mode, originalData, data, xpath) {
    let tableRows = [];
    if (mode === Modes.READ_MODE) {
        tableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
    } else {
        let originalDataTableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
        tableRows = getTableRowsFromData(collections, data, xpath);

        // combine the original and modified data rows
        for (let i = 0; i < originalDataTableRows.length; i++) {
            if (i < tableRows.length) {
                if (originalDataTableRows[i]['data-id'] !== tableRows[i]['data-id']) {
                    if (!tableRows.filter(row => row['data-id'] === originalDataTableRows[i]['data-id'])[0]) {
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
            if (!originalDataTableRows.filter(row => row['data-id'] === tableRows[i]['data-id'])[0]) {
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
                return _.get(object, xpath);
            }
        }
        return null;
    }
}

export function normalise(value, max, min) {
    if (typeof (value) === DataTypes.NUMBER && typeof (min) === DataTypes.NUMBER && typeof (max) === DataTypes.NUMBER) {
        let percentage = ((value - min) * 100) / (max - min);
        return percentage > 100 ? 100 : percentage;
    }
    return 0;
}

export function getHoverTextType(value) {
    let hoverType = value.trim();
    if (HoverTextType.hasOwnProperty(hoverType)) {
        return HoverTextType[hoverType];
    }
    return HoverTextType.HoverTextType_NONE;
}

export function getParentSchema(schema, currentSchemaName) {
    let parentSchema;
    _.keys(_.get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {
        let current = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);
        if (current.type === DataTypes.OBJECT && _.has(current.properties, currentSchemaName)) {
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
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (_.isNull(v)) {
            if (!k.startsWith('xpath_')) {
                let xpath = object['xpath_' + k];
                dict[xpath] = v;
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                getXpathKeyValuePairFromObject(object[k][i], dict);
            }
        } else if (_.isObject(v)) {
            getXpathKeyValuePairFromObject(object[k], dict);
        }
        return;
    });
    return dict;
}

export function getComparator(order, orderBy) {
    return order === 'desc'
        ? (a, b) => descendingComparator(a, b, orderBy)
        : (a, b) => -descendingComparator(a, b, orderBy);
}

export function descendingComparator(a, b, orderBy) {
    if (a[orderBy] === undefined || a[orderBy] === null) {
        return -1;
    }
    if (b[orderBy] === undefined || b[orderBy] === null) {
        return 1;
    }
    if (b[orderBy] < a[orderBy]) {
        return -1;
    }
    if (b[orderBy] > a[orderBy]) {
        return 1;
    }
    return 0;
}

// This method is created for cross-browser compatibility, if you don't
// need to support IE11, you can use Array.prototype.sort() directly
export function stableSort(array, comparator) {
    const stabilizedThis = array.map((el, index) => [el, index]);
    stabilizedThis.sort((a, b) => {
        const order = comparator(a[0], b[0]);
        if (order !== 0) {
            return order;
        }
        return a[1] - b[1];
    });
    return stabilizedThis.map((el) => el[0]);
}

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
    _.entries(dict).map(([k, v]) => {
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
        let fieldType = f.indexOf('[') === -1 ? DataTypes.OBJECT : DataTypes.ARRAY;
        _.keys(currentObj).forEach(k => {
            if (k !== DB_ID) {
                delete currentObj[k];
            }
        })
        if (fieldType === DataTypes.OBJECT) {
            currentObj[fieldName] = _.cloneDeep(_.get(obj, currentXpath));
            if (i === xpath.split('.').length - 1) {
                currentObj[fieldName] = value;
            }
            currentObj = currentObj[fieldName];
        } else {
            currentObj[fieldName] = [_.cloneDeep(_.get(obj, currentXpath))];
            currentObj = currentObj[fieldName][0];
        }
    })
    return o;
}

export function applyWebSocketUpdate(arr, obj, uiLimit) {
    let updatedArr = arr.filter(o => o[DB_ID] !== obj[DB_ID]);
    // if obj is not deleted object
    if (Object.keys(obj) !== 1) {
        let index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
        // if index is not equal to -1, it is updated obj. If updated, replace the obj at the index
        if (index !== -1) {
            updatedArr.splice(index, 0, obj);
        } else {
            if (uiLimit) {
                // if uiLimit is positive, remove the top object and add the latest obj at the end
                // otherwise remove the last object and add the latest obj at the top
                if (uiLimit >= 0) {
                    if (updatedArr.length >= Math.abs(uiLimit)) {
                        updatedArr.shift();
                    }
                    updatedArr.push(obj);
                } else {
                    if (updatedArr.length >= Math.abs(uiLimit)) {
                        updatedArr.pop();
                    }
                    updatedArr.splice(0, 0, obj);
                }
            } else {
                updatedArr.push(obj);
            }
        }
    }
    return updatedArr;
}

export function applyGetAllWebsocketUpdate(arr, obj, uiLimit) {
    let updatedArr = arr.filter(o => o[DB_ID] !== obj[DB_ID]);
    // if obj is not deleted object
    if (Object.keys(obj) !== 1) {
        let index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
        // if index is not equal to -1, it is updated obj. If updated, replace the obj at the index
        if (index !== -1) {
            updatedArr.splice(index, 0, obj);
        } else {
            updatedArr.push(obj);
        }
    }
    return updatedArr;
}

export function applyFilter(arr, filters = []) {
    if (arr && arr.length > 0) {
        let updatedArr = cloneDeep(arr);
        const filterDict = getFilterDict(filters);
        Object.keys(filterDict).forEach(key => {
            let values = filterDict[key].split(",").map(val => val.trim()).filter(val => val !== "");
            updatedArr = updatedArr.filter(data => values.includes(String(_.get(data, key))));
        })
        return updatedArr;
    }
    return [];
}

export function floatToInt(value) {
    /* 
    Function to convert floating point numbers to integer.
    value: integer or floating point number
    */
    if (typeof value === DataTypes.NUMBER) {
        if (Number.isInteger(value)) {
            return value;
        } else {
            // floating point number
            if (value > 0) {
                return Math.floor(value);
            } else {
                return Math.ceil(value);
            }
        }
    }

    return value;
}

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
            } else if (typeof obj1[prop] === DataTypes.OBJECT && typeof obj2[prop] === DataTypes.OBJECT) {
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

export function roundNumber(value, precision = FLOAT_POINT_PRECISION) {
    /* 
    Function to round floating point numbers.
    value: floating point number
    precision: decimal digits to round off to. default 2 (FLOAT_POINT_PRECISION)
    */
    if (typeof value === DataTypes.NUMBER) {
        if (Number.isInteger(value) || precision === 0) {
            return value;
        } else {
            return +value.toFixed(precision);
        }
    }
    return value;
}

export function getLocalizedValueAndSuffix(metadata, value) {
    /* 
    Function to normalize numbers and return adornments if any
    metadata: contains all properties of the field
    value: field value
    */
    let adornment = '';

    if (typeof value !== DataTypes.NUMBER) {
        return [adornment, value];
    }
    if (metadata.numberFormat && metadata.numberFormat.includes('%')) {
        adornment = '%';
    }
    if (metadata.displayType === DataTypes.INTEGER) {
        return [adornment, floatToInt(value)]
    }
    if (metadata.numberFormat && metadata.numberFormat.includes('.')) {
        let precision = metadata.numberFormat.split(".").pop();
        precision *= 1;
        value = roundNumber(value, precision);
    } else {
        value = roundNumber(value);
    }

    return [adornment, value];
}

export function excludeNullFromObject(obj) {
    /* 
    Function to remove null values from mutable object inplace.
    obj: mutable object
    */
    if (_.isObject(obj)) {
        for (const key in obj) {
            if (obj[key] === null) {
                // delete key with null values
                delete obj[key];
            } else if (_.isObject(obj[key])) {
                excludeNullFromObject(obj[key]);
            } else if (Array.isArray(obj[key])) {
                for (let i = 0; i < obj[key].length; i++) {
                    excludeNullFromObject(obj[key][i]);
                }
            }
            // else not required
        }
    } else if (_.isArray(obj)) {
        obj.forEach(o => {
            excludeNullFromObject(o);
        })
    }
    // else not required
}

export function compareJSONObjects(obj1, obj2) {
    /* 
    Function to compare two objects and clear null fields from diff
    obj1: initial / original object
    obj2: currrent object
    */
    let diff = {};
    if (_.isObject(obj1) && _.isObject(obj2)) {
        diff = getObjectsDiff(obj1, obj2);
    } else if (_.isObject(obj2)) {
        diff = obj2;
    }
    if (_.keys(diff).length > 0) {
        // add the object ID if diff found and ID exists on initial object
        if (DB_ID in obj1) {
            diff[DB_ID] = obj1[DB_ID];
        } else {
            // removing null fields from diff if no ID exists on initial object
            excludeNullFromObject(diff);
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
                    if (!_.isEmpty(nestedDiff)) {
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
            //    if (!_.isEqual(arr1, arr2)) {
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
                        if (!_.isEmpty(arrDiff)) {
                            diff[key] = arrDiff;
                        }
                        // else not required: no difference found
                    } else {
                        diff[key] = obj2[key];
                    }
                } else if (obj1[key] instanceof Object) {
                    if (obj2[key] instanceof Object) {
                        const nestedDiff = getObjectsDiff(obj1[key], obj2[key]);
                        if (!_.isEmpty(nestedDiff)) {
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
    if (metadata.type === DataTypes.ENUM) {
        if (value && value.includes('UNSPECIFIED')) {
            errors.push(Message.UNSPECIFIED_FIELD);
        }
        // else not required: value is set
    }
    // Check if field violates minimum requirement    
    if (typeof min === DataTypes.NUMBER) {
        if (value !== undefined && value !== null && value < min) {
            errors.push(Message.MIN + ': ' + min);
        }
    }
    // Check if field violates maximum requirement
    if (typeof max === DataTypes.NUMBER) {
        if (value !== undefined && value !== null && value > max) {
            errors.push(Message.MAX + ': ' + max);
        }
    }

    // If no constraints are violated, return null
    return errors.length ? errors.join(', ') : null;
}

export function removeRedundantFieldsFromRows(rows) {
    rows = rows.map(row => {
        _.keys(row).forEach(key => {
            if (key.includes('xpath')) {
                delete row[key];
            }
            if (key === 'data-id') {
                delete row[key];
            }
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
            let metadata = itemsData.filter(metadata => _.get(metadata, DB_ID) === id)[0];
            row['data-id'] = id;
            itemFieldProperties.forEach(c => {
                let value = null;
                if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.filter(col => col.tableTitle === xpath)[0];
                        let val = _.get(metadata, xpath);
                        if (val === undefined || val === null) {
                            val = "";
                        }
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                        if (typeof v === DataTypes.NUMBER && collection.type === DataTypes.NUMBER) {
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
                    value = _.get(metadata, c.xpath);
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

export function getActiveRows(rows, page, pageSize, order, orderBy) {
    return stableSort(rows, getComparator(order, orderBy))
        .slice(page * pageSize, page * pageSize + pageSize);
}

export function compareNCheckNewArrayItem(obj1, obj2) {
    for (const key in obj1) {
        if (obj1[key] instanceof Array && obj2[key] instanceof Array) {
            if (obj1[key].length !== obj2.length) {
                return true;
            }
            for (let i = 0; obj1[key].length; i++) {
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
                } else if (typeof json[key] === DataTypes.NUMBER) {
                    const [suffix, v] = getLocalizedValueAndSuffix(prop, json[key]);
                    json[key] = v.toLocaleString() + suffix;
                } else if (prop.type === DataTypes.DATE_TIME && truncateDateTime) {
                    if (json[key]) {
                        json[key] = dayjs.utc(json[key]).format('YYYY-MM-DD HH:mm');
                    }
                }
                if (prop.hide) {
                    delete json[key];
                }
            }
        }
    }
}

export function isObject(value) {
    return value !== null && typeof value === DataTypes.OBJECT;
}

export function getWidgetOptionById(widgetOptions, id, isIdBound = false) {
    let widgetOption = widgetOptions[0];
    if (isIdBound) {
        const dataElement = widgetOptions.find(data => data.hasOwnProperty('bind_id_val') && String(data.bind_id_val) === String(id));
        if (dataElement) {
            widgetOption = dataElement;
        }
    }
    widgetOption = cloneDeep(widgetOption);
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
            const value = _.get(data, fieldxpath);
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
    CHART_AXIS_TYPE_UNSPECIFIED: 'CHART_AXIS_TYPE_UNSPECIFIED',
    CATEGORY: 'category',
    TIME: 'time',
    VALUE: 'value'
}

function getChartAxisTypeAndName(encode, collections) {
    const collection = collections.find(collection => collection.tableTitle === encode);
    let name = null;
    if (collection) {
        name = collection.title;
        if (collection.type === DataTypes.STRING) {
            return [ChartAxisType.CATEGORY, name];
        } else if (collection.type === DataTypes.NUMBER) {
            return [ChartAxisType.VALUE, name];
        } else if (collection.type === DataTypes.DATE_TIME) {
            return [ChartAxisType.TIME, name];
        }
    }
    return [ChartAxisType.VALUE, name];
}

function getAxisMax(rows, field, index) {
    let max = 0;
    rows.forEach(row => {
        const value = _.get(row, field);
        if (value > max) {
            max = value;
        }
    })
    max = Math.ceil(max);
    const scale = 1.5 - 0.25 * index;
    return max * scale;
}

export function updateChartDataObj(chartDataObj, collections, rows, datasets, partitionFld) {
    chartDataObj = cloneDeep(chartDataObj);
    const xEndodes = [];
    const yEncodes = [];
    const xAxis = [];
    const yAxis = [];
    const series = [];
    let prevYEncode;
    let prevYEncodeIndex = 0;
    chartDataObj.series.forEach(chartSeries => {
        const xEncode = chartSeries.encode.x;
        const yEncode = chartSeries.encode.y;
        if (!prevYEncode) {
            prevYEncode = yEncode;
        } else if (prevYEncode !== yEncode) {
            prevYEncodeIndex += 1;
            chartSeries.yAxisIndex = prevYEncodeIndex;
        }
        if (!xEndodes.includes(xEncode)) {
            xEndodes.push(xEncode);
        }
        if (!yEncodes.includes(yEncode)) {
            yEncodes.push(yEncode);
        }
        chartSeries.name = yEncode;
        if (partitionFld) {
            datasets.forEach((dataset, index) => {
                const newSeries = cloneDeep(chartSeries);
                newSeries.datasetIndex = index;
                newSeries.name = _.get(dataset.source[0], partitionFld) + ' ' + newSeries.encode.y;
                if (newSeries.type === 'line') {
                    newSeries.showSymbol = false;
                }
                newSeries.animation = false;
                series.push(newSeries);
            })
        } else {
            series.push(chartSeries);
        }
    })
    xEndodes.forEach((xEncode) => {
        const [xAxisType, xAxisName] = getChartAxisTypeAndName(xEncode, collections);
        // only two x-axis is allowed per chart.
        // if more than 2 x-axis is present, only considers the first 2 x-axis
        // this limitation is added to avoid unsupported configurations
        if (xAxis.length === 0) {
            xAxis.push({
                type: xAxisType,
                name: xAxisName
            })
        }
    })
    yEncodes.forEach((yEncode, index) => {
        const [yAxisType, yAxisName] = getChartAxisTypeAndName(yEncode, collections);
        const max = getAxisMax(rows, yEncode, index);
        // only two y-axis is allowed per chart.
        // if more than 2 y-axis is present, only considers the first 2 y-axis
        // this limitation is added to avoid unsupported configurations
        if (yAxis.length < 2) {
            yAxis.push({
                type: yAxisType,
                name: yAxisName,
                splitNumber: 5,
                max: max,
                interval: max / 5
            })
        }
    })
    chartDataObj.xAxis = xAxis;
    chartDataObj.yAxis = yAxis;
    chartDataObj.series = series;
    return chartDataObj;
}

function updateChartAttributesInSchema(schema, currentSchema) {
    if (currentSchema.hasOwnProperty('properties')) {
        for (const key in currentSchema.properties) {
            const attributes = currentSchema.properties[key];
            if (primitiveDataTypes.includes(attributes.type)) {
                if (key === DB_ID) {
                    attributes.server_populate = true;
                } else if (['xAxisIndex', 'yAxisIndex', 'datasetIndex', 'max', 'splitNumber', 'interval'].includes(key)) {
                    attributes.hide = true;
                } else if (key === 'chart_name') {
                    attributes.orm_no_update = true;
                }
            } else if ([DataTypes.OBJECT, DataTypes.ARRAY].includes(attributes.type)) {
                const ref = attributes.items.$ref.split('/')
                const nestedSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
                updateChartAttributesInSchema(schema, nestedSchema);
            }
        }
    }
}

export function updateChartSchema(schema, collections) {
    schema = cloneDeep(schema);
    const chartDataSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_data']);
    updateChartAttributesInSchema(schema, chartDataSchema);
    const chartEncodeSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_encode']);
    chartEncodeSchema.auto_complete = 'x:FldList,y:FldList';
    const fldList = collections.map(collection => collection.tableTitle);
    schema.autocomplete['FldList'] = fldList;
    return schema;
}


export function getFilterDict(filters) {
    const filterDict = {};
    if (filters) {
        filters.forEach(filter => {
            if (filter.fld_value) {
                filterDict[filter.fld_name] = filter.fld_value;
            }
        })
    }
    return filterDict;
}

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

export function getChartDatasets(rows, partitionFld) {
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
