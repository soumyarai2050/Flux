import _, { cloneDeep } from 'lodash';
import {
    ColorPriority, ColorTypes, DataTypes, HoverTextType, Modes, ShapeType, SizeType,
    DB_ID, NEW_ITEM_ID, SCHEMA_DEFINITIONS_XPATH
} from './constants';
import Node from './components/Node';
import HeaderField from './components/HeaderField';

// stores the tree expand/collapse states
const treeState = {};
const primitiveDataTypes = [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM, DataTypes.DATE_TIME];

// complex field properties that are to be passed to the child components
const complexFieldProps = [
    { propertyName: "server_populate", usageName: "serverPopulate" },
    { propertyName: "ui_update_only", usageName: "uiUpdateOnly" },
    { propertyName: "orm_no_update", usageName: "ormNoUpdate" },
    { propertyName: "auto_complete", usageName: "autocomplete" },
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    { propertyName: "filter_enable", usageName: "filterEnable" },
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
    { propertyName: "display_zero", usageName: "displayZero" }
]

// properties supported explicitly on the array types
const arrayFieldProps = [
    { propertyName: "alert_bubble_source", usageName: "alertBubbleSource" },
    { propertyName: "alert_bubble_color", usageName: "alertBubbleColor" }
]

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
            } else {
                object.options = [autocomplete];
            }
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
            if (!v.hasOwnProperty('items')) {
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
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE) && collection.abbreviated === "JSON") {
                    isRedundant = false;
                }
            }
            if (!isRedundant) {
                collections.push(collection);
            }

            if (collection.abbreviated !== "JSON") {
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
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE) && collection.abbreviated === "JSON") {
                    isRedundant = false;
                }
            }

            if (!isRedundant) {
                collections.push(collection);
            }

            if (collection.abbreviated !== "JSON") {
                createCollections(schema, record, callerProps, collections, sequence, updatedxpath, elaborateTitle);
            }
        }
    });
    return collections;
}

export function generateObjectFromSchema(schema, currentSchema) {
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
            if (!metadata.hasOwnProperty('items')) {
                object[propname] = [];
            } else {
                let ref = metadata.items.$ref.split('/');
                let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];

                if (!childSchema.server_populate) {
                    let child = generateObjectFromSchema(schema, childSchema);;
                    object[propname] = [];
                    object[propname].push(child);
                }
            }
        } else if (metadata.type === DataTypes.OBJECT) {
            let ref = metadata.items.$ref.split('/');
            let childSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            childSchema = cloneDeep(childSchema);

            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                childSchema.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
            }

            if (!(childSchema.server_populate || childSchema.ui_update_only)) {
                object[propname] = generateObjectFromSchema(schema, childSchema);
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

function addSimpleNode(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath) {
    let node = {};
    const data = callerProps.data;
    const originalData = callerProps.originalData;

    // do not add field if not present in both modified data and original data.
    if ((Object.keys(data).length === 0 && Object.keys(originalData).length === 0) || (dataxpath && !_.get(data, dataxpath) && !_.get(originalData, xpath))) return;

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

        fieldProps.map(({ propertyName, usageName }) => {
            if (attributes.hasOwnProperty(propertyName)) {
                node[usageName] = attributes[propertyName];
            }
        })

        node.value = dataxpath ? hasxpath(data, node.dataxpath) ? _.get(data, dataxpath)[propname] : undefined : data[propname];

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

function addHeaderNode(node, currentSchema, propname, type, callerProps, dataxpath, xpath, ref) {
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
    headerNode.uiUpdateOnly = currentSchema.ui_update_only;

    if (!dataxpath) {
        headerNode['data-remove'] = true;
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

export function generateTreeStructure(schema, currentSchemaName, callerProps) {
    // return if full schema is not present
    let tree = [];
    if (schema === undefined || schema === null || Object.keys(schema).length === 0) return tree;

    let currentSchema = _.get(schema, currentSchemaName);
    let childNode;
    if (currentSchema.widget_ui_data && currentSchema.widget_ui_data.is_repeated) {
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
        if (!_.get(data, dataxpath) && !_.get(originalData, xpath)) return;

        let childNode = addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, dataxpath, xpath, currentSchema.items.$ref);
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
    } else if (currentSchema.hasOwnProperty('items') && currentSchema.type === DataTypes.ARRAY) {
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
        // TODO: add support for array for primitive data types
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
    let trees = [];
    if (xpath) jsondata = _.get(jsondata, xpath);
    if (!jsondata) return trees;

    while (true) {
        if (_.isArray(jsondata)) {
            for (let i = 0; i < jsondata.length; i++) {
                let tree = {};
                createTree(tree, jsondata[i], null, { delete: 1 }, collections);

                if (Object.keys(tree).length === 0) break;

                if (!hasArrayField(tree)) {
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

            if (!hasArrayField(tree)) {
                tree['data-id'] = 0;
            }
            if (!tree.hasOwnProperty('data-id')) {
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

function hasArrayField(obj, hasArray = false) {
    Object.entries(obj).forEach(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) return;
        else if (Array.isArray(v)) {
            hasArray = true;
            return;
        } else if (_.isObject(v)) {
            hasArrayField(obj[k], hasArray);
        }
    })
    return hasArray;
}


function createTree(tree, currentjson, propname, count, collections) {
    if (Array.isArray(currentjson)) {
        if (currentjson.length === 0) return;

        tree[propname] = [];
        if (collections.filter((c) => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
            tree[propname] = currentjson;
        } else {
            let node = {};
            tree[propname].push(node);
            let xpath = currentjson[0][_.keys(currentjson[0]).filter(k => k.startsWith('xpath_'))[0]];
            xpath = xpath ? xpath.substring(0, xpath.lastIndexOf('.')) : xpath;
            node['data-id'] = xpath;
            createTree(tree[propname], currentjson[0], 0, count, collections)
            if (currentjson.length > 1 && count.delete > 0) {
                count.delete -= 1;
                currentjson.splice(0, 1);
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
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            let updatedxpath = xpath ? xpath + '.' + k : k;
            if ((!_.get(original, updatedxpath) && _.get(original, updatedxpath) !== false && _.get(original, updatedxpath) !== 0) || !_.isEqual(_.get(updated, updatedxpath), _.get(original, updatedxpath))) {
                if (!diff.includes(updatedxpath)) diff.push(updatedxpath);
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                let updatedxpath = xpath ? xpath + '.' + k + '[' + i + ']' : k + '[' + i + ']';
                if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v[0]))) {
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
    const abbreviatedKeyPath = abbreviated.split('$')[0].split(':').pop();
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
        if (value === 0 || value === false || value === '' || value === null) return true;
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

export function getCommonKeyCollections(rows, tableColumns, hide = true) {
    if (rows.length > 1) {
        tableColumns = tableColumns.map(column => Object.assign({}, column)).filter(column => !column.noCommonKey);
    }
    let commonKeyCollections = [];
    if (rows.length > 0) {
        tableColumns.map((column) => {
            if (hide && column.hide) return;

            let found = true;
            for (let i = 0; i < rows.length - 1; i++) {
                if (!_.isEqual(rows[i][column.tableTitle], rows[i + 1][column.tableTitle])) {
                    found = false;
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

export function applyFilter(arr, filter) {
    if (arr && arr.length > 0) {
        let updatedArr = cloneDeep(arr);
        Object.keys(filter).forEach(key => {
            let values = filter[key].split(",").map(val => val.trim()).filter(val => val !== "");
            updatedArr = updatedArr.filter(data => values.includes(_.get(data, key)));
        })
        return updatedArr;
    }
    return [];
}

export function floatToInt(number) {
    if (number > 0) {
        return Math.floor(number);
    } else {
        return Math.ceil(number);
    }
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

export function compareJSONObjects(obj1, obj2) {
    const differences = getJSONDifferences(obj1, obj2);
    if (_.keys(differences).length > 0) {
        if (DB_ID in obj1) {
            differences[DB_ID] = obj1[DB_ID];
        }
    }
    return differences;
}

function getJSONDifferences(obj1, obj2) {
    const differences = {};

    function compareNestedArrays(arr1, arr2, parentKey) {
        const arrDifferences = [];

        arr1.forEach(element1 => {
            let found = false;

            if (element1 instanceof Object && DB_ID in element1) {
                found = arr2.some(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
            }

            if (!found) {
                arrDifferences.push({ [DB_ID]: element1[DB_ID] });
            } else {
                let element2 = arr2.find(element2 => element2 instanceof Object && DB_ID in element2 && element2[DB_ID] === element1[DB_ID]);
                let nestedDifferences = compareJSONObjects(element1, element2);
                if (Object.keys(nestedDifferences).length > 0) {
                    arrDifferences.push({ [DB_ID]: element1[DB_ID], ...nestedDifferences });
                }
            }
        });

        arr2.forEach(element2 => {
            if (element2 instanceof Object && !(DB_ID in element2)) {
                arrDifferences.push(element2);
            }
        })

        return arrDifferences;
    }

    for (const key in obj1) {
        if (obj1.hasOwnProperty(key) && obj2.hasOwnProperty(key)) {
            if (Array.isArray(obj1[key]) && Array.isArray(obj2[key])) {
                const nestedDifferences = compareNestedArrays(obj1[key], obj2[key], key);
                if (nestedDifferences.length > 0) {
                    differences[key] = nestedDifferences;
                }
            } else if (typeof obj1[key] === DataTypes.OBJECT && typeof obj2[key] === DataTypes.OBJECT) {
                const nestedDifferences = compareJSONObjects(obj1[key], obj2[key]);
                if (Object.keys(nestedDifferences).length > 0) {
                    differences[key] = nestedDifferences;
                }
            } else if (obj1[key] !== obj2[key]) {
                differences[key] = obj2[key];
            }
        }
    }

    for (const key in obj2) {
        if (obj2.hasOwnProperty(key) && !obj1.hasOwnProperty(key)) {
            if (!differences.hasOwnProperty(key)) {
                differences[key] = obj2[key];
            }
        }
    }
    return differences;
}

export function validateConstraints(collection, value, min, max) {
    if (collection.serverPopulate) {
        return null;
    }
    if (value === '') {
        value = null;
    }
    const errors = [];
    if (collection.required && (value === null || value === undefined)) {
        errors.push("required field cannot be None");
    }
    if (collection.type === DataTypes.ENUM && value && value.includes('UNSPECIFIED')) {
        errors.push('enum field cannot be UNSPECIFIED');
    }
    if (min) {
        if (value && value < min) {
            errors.push("field value is less than min value: " + min);
        }
    }
    if (max) {
        if (value && value > max) {
            errors.push("field value is greater than max value: " + max);
        }
    }
    return errors.length > 0 ? errors.join(", ") : null;
}