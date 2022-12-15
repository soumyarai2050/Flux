import _, { cloneDeep } from 'lodash';
import Node from './components/Node';
import HeaderField from './components/HeaderField';
import { ColorPriority, ColorTypes, DataTypes, DB_ID, Modes, NEW_ITEM_ID } from './constants';

const treeState = {};

export function setTreeState(xpath, state) {
    treeState[xpath] = state;
}

export function createCollections(schema, currentSchema, callerProps, collections = [], sequence = { sequence: 1 }, parentxpath) {
    currentSchema = cloneDeep(currentSchema);
    currentSchema.properties = sortSchemaProperties(currentSchema.properties);
    // if (currentSchema.hasOwnProperty('server_populate') && currentSchema.server_populate) {
    //     Object.entries(currentSchema.properties).map(([k, v]) => {
    //         currentSchema.properties[k].server_populate = true;
    //     })
    // }
    Object.entries(currentSchema.properties).map(([k, v]) => {
        let collection = {};
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM].includes(v.type)) {
            collection.key = k;
            collection.type = v.type;
            collection.title = v.title;
            collection.hide = v.hasOwnProperty('hide') ? v.hide : false;
            collection.tableTitle = parentxpath ? parentxpath + '.' + k : k;
            collection.sequenceNumber = sequence.sequence;

            if (v.hasOwnProperty('default')) {
                collection.default = v.default;
            }

            if (v.type === DataTypes.ENUM) {
                let ref = v.items.$ref.split('/');
                collection.autocomplete_list = getAutoCompleteData(schema, ref, v.type);
            }

            if (v.hasOwnProperty('underlying_type')) {
                collection.underlyingtype = v.underlying_type;
            }

            if (v.hasOwnProperty('ui_placeholder')) {
                collection.placeholder = v.ui_placeholder;
            }

            if (v.switch) {
                collection.type = 'switch';
            }

            if (v.hasOwnProperty('color')) {
                collection.color = v.color;
            }

            if (currentSchema.hasOwnProperty('orm_no_update') || v.hasOwnProperty('orm_no_update')) {
                collection.ormNoUpdate = v.orm_no_update ? v.orm_no_update : currentSchema.orm_no_update;
            }

            if (currentSchema.hasOwnProperty('server_populate') || v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate ? v.server_populate : currentSchema.server_populate;
            }

            if (currentSchema.hasOwnProperty('auto_complete') || v.hasOwnProperty('auto_complete')) {
                let autocomplete = v.auto_complete ? v.auto_complete : currentSchema.auto_complete;
                let autocompleteFields = autocomplete.split(',').map((field) => field.trim());
                let autocompleteFieldDict = {};

                autocompleteFields.map((field) => {
                    if (field.indexOf(':') > 0) {
                        let [k, v] = field.split(':');
                        autocompleteFieldDict[k] = v;
                    } else {
                        let [k, v] = field.split('=');
                        autocompleteFieldDict[k] = v;
                    }
                })
                if (autocompleteFieldDict.hasOwnProperty(k)) {
                    collection.autocomplete = autocompleteFieldDict[k];
                    if (schema.autocomplete.hasOwnProperty(collection.autocomplete)) {
                        collection.options = schema.autocomplete[collection.autocomplete];
                    } else {
                        collection.options = [collection.autocomplete];
                        // collection.value = collection.autocomplete;
                    }
                }
            }

            if (collections.filter(c => c.tableTitle === collection.tableTitle).length === 0) {
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                    sequence.sequence += 1;
                    collections.push(collection);
                }
            }
        } else if (v.type === DataTypes.ARRAY) {
            collection.key = k;
            collection.title = v.title;
            collection.tableTitle = parentxpath ? parentxpath + '.' + k : k;
            collection.type = v.type;
            collection.abbreviated = v.abbreviated;

            if (currentSchema.hasOwnProperty('server_populate') || v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate ? v.server_populate : currentSchema.server_populate;
            }

            if (v.hasOwnProperty('alert_bubble_source')) {
                collection.alertBubbleSource = v.alert_bubble_source;
                collection.alertBubbleColor = v.alert_bubble_color;
            }
            if (!v.hasOwnProperty('items')) {
                collections.push(collection);
                return;
            }
            let ref = v.items.$ref.split('/')
            let record = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            collection.properties = record.properties;
            if (collection.abbreviated === "JSON") {
                collection.sequenceNumber = sequence.sequence;
                sequence.sequence += 1;
            }
            if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                collections.push(collection);
                if (collection.abbreviated !== "JSON") {
                    createCollections(schema, record, callerProps, collections, sequence);
                }
            }
        } else if (v.type === DataTypes.OBJECT) {

            let ref = v.items.$ref.split('/')
            let record = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
            record = cloneDeep(record);
            collection.key = k;
            collection.title = v.title;
            collection.tableTitle = parentxpath ? parentxpath + '.' + k : k;
            collection.type = v.type;
            collection.properties = record.properties;
            collection.abbreviated = v.abbreviated;

            if (currentSchema.hasOwnProperty('server_populate') || v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate ? v.server_populate : currentSchema.server_populate;
                record.server_populate = v.server_populate ? v.server_populate : currentSchema.server_populate;
            }

            if (currentSchema.hasOwnProperty('orm_no_update') || v.hasOwnProperty('orm_no_update')) {
                record.orm_no_update = v.orm_no_update ? v.orm_no_update : currentSchema.orm_no_update;
            }

            if (currentSchema.hasOwnProperty('auto_complete') || v.hasOwnProperty('auto_complete')) {
                record.auto_complete = v.auto_complete ? v.auto_complete : currentSchema.auto_complete;
            }

            if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                if (collection.abbreviated !== "JSON") {
                    createCollections(schema, record, callerProps, collections, sequence, k);
                } else {
                    collection.sequenceNumber = sequence.sequence;
                    sequence.sequence += 1;
                    collections.push(collection);
                }
            }

        }
    });
    return collections;
}

export function generateObjectFromSchema(schema, currentSchema) {
    let object = {};
    Object.keys(currentSchema.properties).map((propname) => {
        let metadata = currentSchema.properties[propname];
        // do not add field if populated from server.
        if (metadata.server_populate) return;

        if (metadata.type === DataTypes.STRING) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : '';
            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteFields = autocomplete.split(',').map((field) => field.trim());
                let autocompleteFieldDict = {};

                autocompleteFields.map((field) => {
                    if (field.indexOf(':') > 0) {
                        let [k, v] = field.split(':');
                        autocompleteFieldDict[k] = v;
                    } else {
                        let [k, v] = field.split('=');
                        autocompleteFieldDict[k] = v;
                    }
                })
                if (autocompleteFieldDict.hasOwnProperty(propname)) {
                    if (!schema.autocomplete.hasOwnProperty(autocompleteFieldDict[propname])) {
                        object[propname] = autocompleteFieldDict[propname];
                    }
                }
            }
        } else if (metadata.type === DataTypes.NUMBER) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : 0;
        } else if (metadata.type === DataTypes.BOOLEAN) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : false;
        } else if (metadata.type === DataTypes.ENUM) {
            let ref = metadata.items.$ref.split('/')
            let enumdata = getAutoCompleteData(schema, ref, metadata.type)
            object[propname] = enumdata ? enumdata[0] : '';
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : enumdata ? enumdata[0] : '';
            if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
                let autocomplete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
                let autocompleteFields = autocomplete.split(',').map((field) => field.trim());
                let autocompleteFieldDict = {};

                autocompleteFields.map((field) => {
                    if (field.indexOf(':') > 0) {
                        let [k, v] = field.split(':');
                        autocompleteFieldDict[k] = v;
                    } else {
                        let [k, v] = field.split('=');
                        autocompleteFieldDict[k] = v;
                    }
                })
                if (autocompleteFieldDict.hasOwnProperty(propname)) {
                    if (!schema.autocomplete.hasOwnProperty(autocompleteFieldDict[propname])) {
                        object[propname] = autocompleteFieldDict[propname];
                    }
                }
            }
        } else if (metadata.type === DataTypes.ARRAY) {
            if (!metadata.hasOwnProperty('items')) {
                // for handling the cases where array are of simple type
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
            if (!childSchema.server_populate) {
                object[propname] = generateObjectFromSchema(schema, childSchema);
            }
        }
    });
    return object;
}

function getAutoCompleteData(schema, ref, type) {
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
    if (dataxpath || xpath) {
        let current = _.get(data, dataxpath) ? _.get(data, dataxpath)[propname] : undefined;
        let original = _.get(originalData, xpath) ? _.get(originalData, xpath)[propname] : undefined;
        if (current !== undefined && original !== undefined && (current !== original)) {
            object['data-modified'] = true;
        } else if (current !== undefined && original === undefined) {
            object['data-add'] = true;
        } else if (current === undefined && original !== undefined) {
            object['data-remove'] = true;
            object.value = original;
        }
    } else {
        let current = data[propname];
        let original = originalData[propname];
        if (current !== undefined && original !== undefined && (current !== original)) {
            object['data-modified'] = true;
        } else if (current !== undefined && original === undefined) {
            object['data-add'] = true;
        } else if (current === undefined && original !== undefined) {
            object['data-remove'] = true;
            object.value = original;
        }
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
    if (attributes.hasOwnProperty('type') && [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM].includes(attributes.type)) {
        node.id = propname;
        node.key = propname;
        node.name = propname;
        node.title = attributes.title;
        node.type = attributes.type;
        node.mode = callerProps.mode;
        node.hide = attributes.hasOwnProperty('hide') ? attributes.hide : false;
        node.help = attributes.help;
        node.required = currentSchema.required.filter(p => p === propname) ? true : false;
        node.default = attributes.default;
        node.value = dataxpath && _.get(data, dataxpath) && (_.get(data, dataxpath)[propname] || (!_.get(data, dataxpath)[propname] && _.get(data, dataxpath)[propname] === 0)) ?
            _.get(data, dataxpath)[propname] : data[propname];
        node.xpath = xpath ? xpath + '.' + propname : propname;
        node.dataxpath = dataxpath ? dataxpath + '.' + propname : propname;
        node.parentcollection = currentSchema.title;
        node.customComponent = Node;
        node.onTextChange = callerProps.onTextChange;
        node.onKeyDown = callerProps.onKeyDown;

        if (attributes.type === DataTypes.BOOLEAN) {
            node.onCheckboxChange = callerProps.onCheckboxChange;
        }

        if (attributes.type === DataTypes.ENUM) {
            let ref = attributes.items.$ref.split('/')
            let enumdata = getAutoCompleteData(schema, ref, attributes.type);
            node.dropdowndataset = enumdata;
            node.onSelectItemChange = callerProps.onSelectItemChange;
        }

        if (attributes.hasOwnProperty('underlying_type')) {
            node.underlyingtype = attributes.underlying_type;
        }

        if (attributes.hasOwnProperty('ui_placeholder')) {
            node.placeholder = attributes.ui_placeholder;
        }

        if (currentSchema.hasOwnProperty('server_populate') || attributes.hasOwnProperty('server_populate')) {
            node.serverPopulate = attributes.server_populate ? attributes.server_populate : currentSchema.server_populate;
        }

        if (currentSchema.hasOwnProperty('orm_no_update') || attributes.hasOwnProperty('orm_no_update')) {
            node.ormNoUpdate = attributes.orm_no_update ? attributes.orm_no_update : currentSchema.orm_no_update;
        }

        if (currentSchema.hasOwnProperty('auto_complete') || attributes.hasOwnProperty('auto_complete')) {
            let autocomplete = attributes.auto_complete ? attributes.auto_complete : currentSchema.auto_complete;
            let autocompleteFields = autocomplete.split(',').map((field) => field.trim());
            let autocompleteFieldDict = {};

            autocompleteFields.map((field) => {
                if (field.indexOf(':') > 0) {
                    let [k, v] = field.split(':');
                    autocompleteFieldDict[k] = v;
                } else {
                    let [k, v] = field.split('=');
                    autocompleteFieldDict[k] = v;
                }
            })
            if (autocompleteFieldDict.hasOwnProperty(propname)) {
                node.autocomplete = autocompleteFieldDict[propname];
                node.customComponentType = 'autocomplete';
                if (schema.autocomplete.hasOwnProperty(node.autocomplete)) {
                    node.options = schema.autocomplete[node.autocomplete];
                } else {
                    node.options = [node.autocomplete];
                    // node.value = node.autocomplete;
                }
                node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
            }
        }

        let newprop = compareNodes(originalData, data, dataxpath, propname, xpath);
        node = { ...node, ...newprop };

        if ((!node.serverPopulate || callerProps.mode !== Modes.EDIT_MODE) && (!node.hide || !callerProps.hide)) {
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
    let childNode = addHeaderNode(tree, currentSchema, currentSchemaName, DataTypes.OBJECT, callerProps, currentSchemaName, currentSchemaName);
    Object.keys(currentSchema.properties).map((propname) => {
        if (callerProps.xpath && callerProps.xpath !== propname) return;
        let metadataProp = currentSchema.properties[propname];
        if (metadataProp.hasOwnProperty('type') && [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM].includes(metadataProp.type)) {
            addSimpleNode(childNode, schema, currentSchema, propname, callerProps);
        }
        else {
            addNode(childNode, schema, metadataProp, propname, callerProps, propname, null, propname);
        }
    });
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

        if (currentSchema.hasOwnProperty('orm_no_update') || metadata.hasOwnProperty('orm_no_update')) {
            metadata.orm_no_update = metadata.no_orm_update ? metadata.no_orm_update : currentSchema.orm_no_update;
        }

        if (currentSchema.hasOwnProperty('server_populate') || metadata.hasOwnProperty('server_populate')) {
            metadata.server_populate = metadata.server_populate ? metadata.server_populate : currentSchema.server_populate;
            if(callerProps.mode === Modes.EDIT_MODE) return;
        }

        if (currentSchema.hasOwnProperty('auto_complete') || metadata.hasOwnProperty('auto_complete')) {
            metadata.auto_complete = metadata.auto_complete ? metadata.auto_complete : currentSchema.auto_complete;
        }

        if (metadata.hasOwnProperty('properties')) {
            Object.keys(metadata.properties).forEach((prop) => {
                let metadataProp = metadata.properties[prop];
                // if (currentSchema.hasOwnProperty('orm_no_update')) {
                //     metadataProp['orm_no_update'] = currentSchema.orm_no_update;
                // }
                // if (currentSchema.hasOwnProperty('auto_complete')) {
                //     let autocompleteFields = currentSchema.auto_complete.split(',').map((field) => field.trim());
                //     let autocompleteFieldDict = {};

                //     autocompleteFields.map((field) => {
                //         if (field.indexOf(':') > 0) {
                //             let [k, v] = field.split(':');
                //             autocompleteFieldDict[k] = v;
                //         } else {
                //             let [k, v] = field.split('=');
                //             autocompleteFieldDict[k] = v;
                //         }
                //     })
                //     if (autocompleteFieldDict.hasOwnProperty(prop)) {
                //         metadataProp.auto_complete = autocompleteFieldDict[prop];
                //     }
                // }
                if (metadataProp.hasOwnProperty('type') && (metadataProp.type === DataTypes.OBJECT)) {
                    let childxpath = dataxpath;
                    if (childxpath) {
                        childxpath = childxpath + '.' + prop;
                    }
                    let updatedxpath = xpath + '.' + prop;
                    addNode(childNode, schema, metadataProp, prop, callerProps, childxpath, null, updatedxpath);
                } else if (metadataProp.hasOwnProperty('type') && [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER, DataTypes.ENUM].includes(metadataProp.type)) {
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
        if (_.get(data, dataxpath) && _.get(data, dataxpath).length === 0 && _.get(originalData, xpath) && _.get(originalData, xpath).length === 0) {
            let childxpath = dataxpath + '[-1]';
            let updatedxpath = xpath + '[-1]';
            addHeaderNode(tree, currentSchema, propname, currentSchema.type, callerProps, childxpath, updatedxpath, currentSchema.items.$ref);
        } else {
            let paths = [];
            if (_.get(originalData, xpath)) {
                for (let i = 0; i < _.get(originalData, xpath).length; i++) {
                    let childxpath = dataxpath + '[' + i + ']';
                    childxpath = getDataxpath(data, childxpath);
                    let updatedxpath = xpath + '[' + i + ']';
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

export function generateRowTrees(jsondata, collections, xpath) {
    let trees = [];
    if (xpath) jsondata = _.get(jsondata, xpath);
    if (!jsondata) return trees;

    while (true) {
        let tree = {};
        Object.entries(jsondata).map(([k, v]) => {
            if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
                tree[k] = v;
            } else if (Array.isArray(v)) {
                tree[k] = {};
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

        if (trees.length > 0 && _.isEqual(trees[trees.length - 1], tree)) {
            break;
        }
        trees.push(tree);
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
    } else if (_.isObject(currentjson)) {
        if (collections.filter((c) => c.key === propname && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
            tree[propname] = currentjson;
        } else {
            let node = tree[propname];
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
    Object.entries(jsondata).map(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                let childxpath = xpath ? `${xpath}.${k}[${i}]` : `${k}[${i}]`;
                addxpath(jsondata[k][i], childxpath);
            }
        } else if (_.isObject(v)) {
            jsondata['xpath_' + k] = xpath ? xpath + '.' + k : k;
            let childxpath = xpath ? xpath + '.' + k : k;
            addxpath(jsondata[k], childxpath)
        }
    });
    return jsondata;
}

export function clearxpath(jsondata) {
    Object.entries(jsondata).map(([k, v]) => {
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(typeof (v))) {
            if (k.startsWith('xpath_')) {
                delete jsondata[k];
            }
        } else if (Array.isArray(v)) {
            for (let i = 0; i < v.length; i++) {
                clearxpath(jsondata[k][i]);
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
                object[k] = v;
            } else if (v.length > 0) {
                flattenObject(jsondata[k][0], object, collections, xpath);
            }
        } else if (_.isObject(v)) {
            if (collections.filter((c) => c.key === k && c.hasOwnProperty('abbreviated') && c.abbreviated === "JSON").length > 0) {
                object[k] = v;
            } else {
                flattenObject(jsondata[k], object, collections, xpath, k);
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
    let abbreviatedSplit = abbreviated.split('-');
    let newItem = '';
    for (let i = 0; i < abbreviatedSplit.length - 1; i++) {
        let key = abbreviatedSplit[i].split('.').pop();
        let collection = collections.filter(collection => collection.key === key)[0];
        let value = 'XXXX';
        if (collection) {
            if (collection.placeholder) {
                value = collection.placeholder;
            } else if (collection.default) {
                value = collection.default;
            }
        }
        newItem += value + '-';
    }
    newItem += NEW_ITEM_ID;
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
    objectArray.sort(function (a, b) {
        if (a[DB_ID] > b[DB_ID]) {
            return 1;
        }
        return -1;
    });
    return objectArray[0];
}