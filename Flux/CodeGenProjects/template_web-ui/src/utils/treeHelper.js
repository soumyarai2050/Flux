import { cloneDeep, get } from 'lodash';
import { MODES, DATA_TYPES, } from '../constants';
import {
    getEnumValues, getModelSchema, hasxpath, setAutocompleteValue, primitiveDataTypes, getDataxpath,
    isNodeInSubtree, complexFieldProps, treeState, fieldProps, getAutocompleteDict, getMetaFieldDict, getMappingSrcDict, compareNodes
} from '../utils';
import Node from '../components/Node';
import HeaderField from '../components/HeaderField';

export function generateTreeStructure(schema, currentSchemaName, callerProps) {
    // return if full schema is not present
    let tree = [];
    if (schema === undefined || schema === null || Object.keys(schema).length === 0) return tree;

    let currentSchema = getModelSchema(currentSchemaName, schema);
    let childNode;
    // if (currentSchema.widget_ui_data_element && currentSchema.widget_ui_data_element.is_repeated) {
    //     childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DATA_TYPES.ARRAY, callerProps, currentSchemaName, currentSchemaName);
    //     for (let i = 0; i < callerProps.data.length; i++) {
    //         let dataxpath = '[' + i + ']';
    //         let node = addHeaderNode(childNode, currentSchema, currentSchemaName, DATA_TYPES.OBJECT, callerProps, dataxpath, dataxpath);
    //         Object.keys(currentSchema.properties).map((propname) => {
    //             if (callerProps.xpath && callerProps.xpath !== propname) return;
    //             let metadataProp = currentSchema.properties[propname];
    //             if (metadataProp.hasOwnProperty('type') && primitiveDataTypes.includes(metadataProp.type)) {
    //                 addSimpleNode(node, schema, currentSchema, propname, callerProps, dataxpath, null, dataxpath);
    //             }
    //             else {
    //                 dataxpath += dataxpath + '.' + propname;
    //                 addNode(node, schema, metadataProp, propname, callerProps, dataxpath, null, dataxpath);
    //             }
    //         });
    //     }
    // } else {
    childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DATA_TYPES.OBJECT, callerProps, currentSchemaName, currentSchemaName);
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
    // }
    return tree;
}

function addNode(tree, schema, currentSchema, propname, callerProps, dataxpath, type, xpath) {
    const data = callerProps.data;
    const originalData = callerProps.originalData;
    let currentSchemaType = type ? type : currentSchema.type;

    if (currentSchema.hasOwnProperty('items') && currentSchemaType === DATA_TYPES.OBJECT) {
        if (get(data, dataxpath) === undefined && get(originalData, xpath) === undefined) return;
        let headerState = {};
        if (get(originalData, xpath) === undefined) {
            if (get(data, xpath) === null) {
                headerState.add = true;
                headerState.remove = false;
            } else {
                headerState.add = false;
                headerState.remove = true;
            }
        } else if (currentSchema.hasOwnProperty('orm_no_update')) {
            if (get(originalData, xpath) !== undefined) {
                headerState.add = false;
                headerState.remove = false;
            }
        } else if (!currentSchema.hasOwnProperty('orm_no_update')) {
            if (get(data, dataxpath) === null) {
                headerState.add = true;
                headerState.remove = false;
            } else {
                headerState.add = false;
                headerState.remove = true;
            }
        }
        if (callerProps.mode === MODES.EDIT && currentSchema.hasOwnProperty('server_populate')) return;
        let childNode = addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, dataxpath, xpath, currentSchema.items.$ref, headerState);
        if (get(data, dataxpath) === null && (get(originalData, xpath) === undefined || get(originalData, xpath) === null)) return;
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
            if (callerProps.mode === MODES.EDIT) return;
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
                    metadataProp.auto_complete = metadataProp.auto_complete ?? metadata.auto_complete;
                }
                if (metadataProp.hasOwnProperty('type') && (metadataProp.type === DATA_TYPES.OBJECT)) {
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
    } else if (currentSchema.hasOwnProperty('items') && currentSchema.type === DATA_TYPES.ARRAY && !primitiveDataTypes.includes(currentSchema.underlying_type)) {
        if (callerProps.mode === MODES.EDIT && currentSchema.hasOwnProperty('server_populate')) return;
        if (((get(data, dataxpath) && get(data, dataxpath).length === 0) || (Object.keys(data).length > 0 && !get(data, dataxpath))) &&
            ((get(originalData, xpath) && get(originalData, xpath).length === 0) || !get(originalData, xpath))) {
            let childxpath = dataxpath + '[-1]';
            let updatedxpath = xpath + '[-1]';
            addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, childxpath, updatedxpath, currentSchema.items.$ref);
        } else {
            let paths = [];
            if (get(originalData, xpath)) {
                for (let i = 0; i < get(originalData, xpath).length; i++) {
                    let updatedxpath = xpath + '[' + i + ']';
                    let childxpath = dataxpath + '[' + i + ']';
                    childxpath = getDataxpath(data, updatedxpath);
                    paths.push(updatedxpath);
                    if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) continue;
                    addNode(tree, schema, currentSchema, propname, callerProps, childxpath, DATA_TYPES.OBJECT, updatedxpath);
                }
            }
            if (get(data, dataxpath)) {
                get(data, dataxpath).map((childobject, i) => {
                    let subpropname = Object.keys(childobject).find(key => key.startsWith('xpath_'));
                    if (!subpropname) return;
                    let propxpath = childobject[subpropname];
                    let propindex = propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'));
                    let updatedxpath = xpath + '[' + propindex + ']';
                    if (paths.includes(updatedxpath)) return;
                    let childxpath = dataxpath + '[' + i + ']';
                    if (!isNodeInSubtree(callerProps, xpath, updatedxpath)) return;
                    addNode(tree, schema, currentSchema, propname, callerProps, childxpath, DATA_TYPES.OBJECT, updatedxpath);
                    paths.push(childxpath);

                })

            }
        }
    } else if (currentSchema.type === DATA_TYPES.ARRAY) {
        // array of simple data types
        if ((get(originalData, xpath) === undefined) && get(data, dataxpath) === undefined) return;
        let arrayDataType = currentSchema.underlying_type;
        if ([DATA_TYPES.INT32, DATA_TYPES.INT64, DATA_TYPES.INTEGER, DATA_TYPES.FLOAT].includes(arrayDataType)) {
            arrayDataType = DATA_TYPES.NUMBER;
        }
        let ref = arrayDataType;
        const additionalProps = {};
        additionalProps.underlyingtype = currentSchema.underlying_type;
        if (currentSchema.underlying_type === DATA_TYPES.ENUM) {
            ref = currentSchema.items.$ref;
            let refSplit = ref.split('/');
            let metadata = refSplit.length === 2 ? schema[refSplit[1]] : schema[refSplit[1]][refSplit[2]];
            additionalProps.options = metadata.enum;
        }
        let childxpath = dataxpath + '[-1]';
        let updatedxpath = xpath + '[-1]';
        const objectState = { add: true, remove: false };
        const childNode = addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, childxpath, updatedxpath, ref, objectState);
        if (get(data, dataxpath)) {
            get(data, dataxpath).forEach((value, i) => {
                let childxpath = dataxpath + '[' + i + ']';
                let updatedxpath = xpath + '[' + i + ']';
                addSimpleNode(childNode, schema, arrayDataType, null, callerProps, childxpath, updatedxpath, additionalProps);
            })
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

function addSimpleNode(tree, schema, currentSchema, propname, callerProps, dataxpath, xpath, additionalProps) {
    let node = {};
    const data = callerProps.data;
    const originalData = callerProps.originalData;

    // do not add field if not present in both modified data and original data.
    if ((Object.keys(data).length === 0 && Object.keys(originalData).length === 0) || (dataxpath && get(data, dataxpath) === undefined && get(originalData, xpath) === undefined)) return;

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

        if (node.type === DATA_TYPES.ENUM) {
            node.dropdowndataset = additionalProps.options;
            node.onSelectItemChange = callerProps.onSelectItemChange;
        }

        node.value = dataxpath ? get(data, dataxpath) : undefined;
        tree.push(node);
        return;
    }

    let attributes = currentSchema.properties[propname];
    if (attributes.hasOwnProperty('type') && primitiveDataTypes.includes(attributes.type)) {
        node.id = propname;
        node.key = propname;
        node.required = currentSchema.required.some(p => p === propname);
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

        node.value = dataxpath ? hasxpath(data, dataxpath) ? get(data, dataxpath)[propname] : undefined : data[propname];

        if (attributes.type === DATA_TYPES.BOOLEAN) {
            node.onCheckboxChange = callerProps.onCheckboxChange;
        }

        if (attributes.type === DATA_TYPES.ENUM) {
            let ref = attributes.items.$ref.split('/')
            let enumdata = getEnumValues(schema, ref, attributes.type);
            node.dropdowndataset = enumdata;
            node.onSelectItemChange = callerProps.onSelectItemChange;
        }

        if (attributes.type === DATA_TYPES.DATE_TIME) {
            node.onDateTimeChange = callerProps.onDateTimeChange;
        }

        complexFieldProps.map(({ propertyName, usageName }) => {
            if (currentSchema.hasOwnProperty(propertyName) || attributes.hasOwnProperty(propertyName)) {
                const propertyValue = attributes[propertyName] ? attributes[propertyName] : currentSchema[propertyName];

                if (propertyName === 'auto_complete') {
                    let autocompleteDict = getAutocompleteDict(propertyValue);
                    setAutocompleteValue(schema, node, autocompleteDict, propname, usageName);
                    if (node.hasOwnProperty('options')) {
                        if (node.hasOwnProperty('dynamic_autocomplete')) {
                            const dynamicValuePath = node.autocomplete.substring(node.autocomplete.indexOf('.') + 1);
                            const dynamicValue = get(data, dynamicValuePath);
                            if (dynamicValue && schema.autocomplete.hasOwnProperty(dynamicValue)) {
                                node.options = schema.autocomplete[schema.autocomplete[dynamicValue]];
                                if (!node.options.includes(node.value) && callerProps.mode === MODES.EDIT && !node.ormNoUpdate && !node.serverPopulate) {
                                    node.value = null;
                                }
                            }
                        }
                        node.customComponentType = 'autocomplete';
                        node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
                    }
                }

                if (propertyName === 'mapping_underlying_meta_field' || propertyName === 'mapping_src') {
                    let dict;
                    if (propertyName === 'mapping_underlying_meta_field') {
                        dict = getMetaFieldDict(propertyValue);
                    } else {
                        dict = getMappingSrcDict(propertyValue);
                    }
                    for (const field in dict) {
                        if (node.xpath.endsWith(field)) {
                            node[usageName] = dict[field];
                        }
                    }
                }
                if (!['auto_complete', 'mapping_underlying_meta_field', 'mapping_src'].includes(propertyName)) {
                    node[usageName] = propertyValue;
                }
            }
        })

        let newprop = compareNodes(originalData, data, dataxpath, propname, xpath);
        node = { ...node, ...newprop };

        let isRedundant = true;
        if (!(node.serverPopulate && callerProps.mode === MODES.EDIT) && !(node.hide && callerProps.hide) && !(node.uiUpdateOnly && node.value === undefined)) {
            isRedundant = false;
            if (node.type === DATA_TYPES.BOOLEAN && node.button && callerProps.mode === MODES.EDIT) {
                isRedundant = true;
            }
        }

        if (!isRedundant) {
            tree.push({ ...node });
        }
    }
}
