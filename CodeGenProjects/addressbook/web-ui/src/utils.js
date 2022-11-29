import _, { cloneDeep } from 'lodash';
import Node from './components/Node';
import HeaderField from './components/HeaderField';
import { DataTypes, Modes } from './constants';
import { defaultItem } from './projectSpecificUtils';

const treeState = {};

export function setTreeState(xpath, state) {
    treeState[xpath] = state;
}

export function createCollections(schema, currentSchema, callerProps, collections = [], sequence = { sequence: 1 }, parentxpath) {
    currentSchema = cloneDeep(currentSchema);
    currentSchema.properties = sortSchemaProperties(currentSchema.properties);
    if (currentSchema.hasOwnProperty('server_populate') && currentSchema.server_populate) {
        Object.entries(currentSchema.properties).map(([k, v]) => {
            currentSchema.properties[k].server_populate = true;
        })
    }
    Object.entries(currentSchema.properties).map(([k, v]) => {
        let collection = {};
        if ([DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(v.type)) {
            collection.key = k;
            collection.type = v.type;
            collection.title = v.title;
            collection.hide = v.hide;
            collection.tableTitle = parentxpath ? parentxpath + '.' + k : k;
            collection.sequenceNumber = sequence.sequence;

            if (v.switch) {
                collection.type = 'switch';
            }
            if (v.hasOwnProperty('color')) {
                collection.color = v.color;
            }
            if (v.hasOwnProperty('orm_no_update')) {
                collection.ormNoUpdate = v.orm_no_update;
                delete v.orm_no_update;
            }
            if (v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate;
            }

            if (collections.filter(c => c.tableTitle === collection.tableTitle).length === 0) {
                if (!(collection.serverPopulate && callerProps.mode === Modes.EDIT_MODE)) {
                    sequence.sequence += 1;
                    collections.push(collection);
                }
            }
        } else if (v.type === DataTypes.ENUM) {
            let ref = v.items.$ref.split('/');
            collection.key = k;
            collection.title = v.title;
            collection.type = 'enum';
            collection.tableTitle = parentxpath ? parentxpath + '.' + k : k;
            collection.sequenceNumber = sequence.sequence;
            if (v.hasOwnProperty('color')) {
                collection.color = v.color;
            }
            if (v.hasOwnProperty('orm_no_update')) {
                collection.ormNoUpdate = v.orm_no_update;
                delete v.orm_no_update;
            }
            if (v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate;
            }
            collection.autocomplete_list = getAutoCompleteData(schema, ref, v.type);
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

            if (v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate;
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

            if (v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate;
            }

            if (v.hasOwnProperty('server_populate')) {
                collection.serverPopulate = v.server_populate;
            }

            if (v.hasOwnProperty('orm_no_update') && v.orm_no_update) {
                Object.entries(record.properties).map(([propname, prop]) => {
                    record.properties[propname].orm_no_update = true;
                })
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
        } else if (metadata.type === DataTypes.NUMBER) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : 0;
        } else if (metadata.type === DataTypes.BOOLEAN) {
            object[propname] = metadata.hasOwnProperty('default') ? metadata.default : false;
        } else if (metadata.type === DataTypes.ENUM) {
            let ref = metadata.items.$ref.split('/')
            let enumdata = getAutoCompleteData(schema, ref, metadata.type)
            object[propname] = enumdata ? enumdata[0] : '';
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

function compareNodes(originalData, data, xpath, propname, actualxpath) {
    let object = {};
    if (xpath || actualxpath) {
        let current = _.get(data, xpath) ? _.get(data, xpath)[propname] : undefined;
        let original = _.get(originalData, actualxpath) ? _.get(originalData, actualxpath)[propname] : undefined;
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

function addSimpleNode(tree, schema, currentSchema, propname, callerProps, xpath, actualxpath) {
    let node = {};
    const data = callerProps.data;
    const originalData = callerProps.originalData;

    // do not add field if not present in both modified data and original data.
    if ((Object.keys(data).length === 0 && Object.keys(originalData).length === 0) || (xpath && !_.get(data, xpath) && !_.get(originalData, xpath))) return;

    let attributes = currentSchema.properties[propname];
    if (attributes.hasOwnProperty('type') && [DataTypes.STRING, DataTypes.BOOLEAN, DataTypes.NUMBER].includes(attributes.type)) {
        node.id = propname;
        node.key = propname;
        node.name = propname;
        node.title = attributes.title;
        node.required = currentSchema.required.filter(p => p === propname) ? true : false;
        node.children = [];
        node.value = xpath && _.get(data, xpath) && (_.get(data, xpath)[propname] || (!_.get(data, xpath)[propname] && _.get(data, xpath)[propname] === 0)) ?
            _.get(data, xpath)[propname] : data[propname];
        node.xpath = actualxpath ? actualxpath + '.' + propname : propname;
        node.dataxpath = xpath ? xpath + '.' + propname : propname;
        node.hide = attributes.hasOwnProperty('hide') ? attributes.hide : false;
        node.help = attributes.help;
        node.parentcollection = currentSchema.title;
        node.type = attributes.type;
        node.mode = callerProps.mode;
        node.customComponent = Node;
        node.onTextChange = callerProps.onTextChange;
        node.onNodeDblClick = callerProps.onNodeDblClick;
        node.serverPopulate = attributes.server_populate;

        if (attributes.hasOwnProperty('orm_no_update')) {
            node.ormNoUpdate = attributes.orm_no_update;
            delete attributes.orm_no_update;
        }

        if (attributes.type === DataTypes.BOOLEAN) {
            node.onCheckboxChange = callerProps.onCheckboxChange;
        }

        if (attributes.hasOwnProperty('auto_complete')) {
            node.customComponentType = 'autocomplete'
            if (schema.autocomplete.hasOwnProperty(attributes.auto_complete)) {
                node.options = schema.autocomplete[attributes.auto_complete];
            } else {
                node.options = [attributes.auto_complete];
                node.value = attributes.auto_complete;
            }
            node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
            delete attributes.auto_complete;
        }

        let newprop = compareNodes(originalData, data, xpath, propname, actualxpath);
        node = { ...node, ...newprop };

        if ((!node.serverPopulate || callerProps.mode !== Modes.EDIT_MODE) && (!node.hide || !callerProps.hide)) {
            tree.push({ ...node });
        }
    } else if (attributes.hasOwnProperty('type') && (attributes.type === DataTypes.ENUM)) {
        let ref = attributes.items.$ref.split('/')
        let enumdata = getAutoCompleteData(schema, ref, attributes.type);
        node.id = propname;
        node.key = propname;
        node.name = propname;
        node.title = attributes.title;
        node.help = attributes.help;
        node.type = attributes.type;
        node.mode = callerProps.mode;
        node.hide = attributes.hasOwnProperty('hide') ? attributes.hide : false;
        node.required = currentSchema.required.filter((p) => p === propname) ? true : false;
        node.dropdowndataset = enumdata;
        node.value = xpath && _.get(data, xpath) && (_.get(data, xpath)[propname] || (!_.get(data, xpath)[propname] && _.get(data, xpath)[propname] === 0)) ?
            _.get(data, xpath)[propname] : data[propname];
        node.onSelectItemChange = callerProps.onSelectItemChange;
        node.parentcollection = currentSchema.title;
        node.customComponent = Node;
        node.xpath = actualxpath ? actualxpath + '.' + propname : propname;
        node.dataxpath = xpath ? xpath + '.' + propname : propname;
        node.onNodeDblClick = callerProps.onNodeDblClick;
        node.serverPopulate = attributes.server_populate;

        if (attributes.hasOwnProperty('orm_no_update')) {
            node.ormNoUpdate = attributes.orm_no_update;
            delete attributes.orm_no_update;
        }

        if (attributes.hasOwnProperty('auto_complete')) {
            node.customComponentType = 'autocomplete'
            if (schema.autocomplete.hasOwnProperty(attributes.auto_complete)) {
                node.options = schema.autocomplete[attributes.auto_complete];
            } else {
                node.options = [attributes.auto_complete];
                node.value = attributes.auto_complete;
            }
            node.onAutocompleteOptionChange = callerProps.onAutocompleteOptionChange;
            delete attributes.auto_complete;
        }

        let newprop = compareNodes(originalData, data, xpath, propname, actualxpath);
        node = { ...node, ...newprop };

        if ((!node.serverPopulate || callerProps.mode !== Modes.EDIT_MODE) && (!node.hide || !callerProps.hide)) {
            tree.push({ ...node });
        }
    }
}

function addHeaderNode(node, currentSchema, propname, type, callerProps, xpath, actualxpath, ref) {
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
    headerNode.onNodeDblClick = callerProps.onNodeDblClick;
    headerNode.xpath = actualxpath;
    if (!xpath) {
        headerNode['data-remove'] = true;
    }
    if (treeState.hasOwnProperty(actualxpath)) {
        treeState[actualxpath] = callerProps.isOpen ? true : callerProps.isOpen === false ? false : treeState[actualxpath];
    } else {
        treeState[actualxpath] = true;
    }
    headerNode.isOpen = treeState[actualxpath];
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

        if (metadata.hasOwnProperty('properties')) {
            Object.keys(metadata.properties).forEach((prop) => {
                let metadataProp = metadata.properties[prop];
                if (currentSchema.hasOwnProperty('orm_no_update')) {
                    metadataProp['orm_no_update'] = currentSchema.orm_no_update;
                }
                if (currentSchema.hasOwnProperty('auto_complete')) {
                    let autocompleteFields = currentSchema.auto_complete.split(',').map((field) => field.trim());
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
                    if (autocompleteFieldDict.hasOwnProperty(prop)) {
                        metadataProp.auto_complete = autocompleteFieldDict[prop];
                    }
                }
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

export function getNewItem(abbreviated) {
    let item = abbreviated.split('-').map((field) => {
        return defaultItem[field];
    })
    return item.join('-');
}