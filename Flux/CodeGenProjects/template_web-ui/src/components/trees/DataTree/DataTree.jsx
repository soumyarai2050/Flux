import React, { useState, useEffect } from 'react';
import InfinityMenu from 'react-infinity-menu-plus';
import { cloneDeep, get, set } from 'lodash';
import { generateObjectFromSchema, addxpath, getDataxpath, setTreeState, clearxpath, clearId } from '../../../utils';
import { DATA_TYPES } from '../../../constants';
import { generateTreeStructure } from '../../../utils/treeHelper';

const DataTree = ({
    projectSchema,
    modelName,
    updatedData,
    storedData,
    subtree,
    mode,
    xpath,
    onUpdate,
    onUserChange,
    selectedId,
    showHidden
}) => {

    const [dataTree, setDataTree] = useState([]);

    useEffect(() => {
        setDataTree(generateTreeStructure(cloneDeep(projectSchema), modelName, {
            'data': updatedData,
            'isOpen': true,
            'hide': !showHidden ?? false,
            'showDataType': false,
            'originalData': storedData,
            'subtree': subtree,
            'mode': mode,
            'xpath': xpath,
            'onTextChange': handleTextChange,
            'onSelectItemChange': handleSelectItemChange,
            'onCheckboxChange': handleCheckboxToggle,
            'onAutocompleteOptionChange': handleAutocompleteChange,
            'onDateTimeChange': handleDateTimeChange,
            'index': selectedId,
            'forceUpdate': false
        }))
    }, [projectSchema, storedData, updatedData, mode, subtree, xpath, selectedId, showHidden])

    const handleFormUpdate = (xpath, dataxpath, value, validationRes = null) => {
        const updatedObj = cloneDeep(updatedData);
        set(updatedObj, dataxpath, value);
        if (onUpdate) {
            onUpdate(updatedObj);
        }
        if (onUserChange) {
            onUserChange(xpath, value, validationRes, null);
        }
    }

    const handleTextChange = (e, type, xpath, value, dataxpath, validationRes) => {
        if (value === '') {
            value = null;
        }
        if (type === DATA_TYPES.NUMBER) {
            if (value !== null) {
                value = Number(value);
            }
        }
        if (type === DATA_TYPES.STRING || (type === DATA_TYPES.NUMBER && !isNaN(value))) {
            handleFormUpdate(xpath, dataxpath, value, validationRes);
        }
    }

    const handleDateTimeChange = (dataxpath, xpath, value) => {
        handleFormUpdate(xpath, dataxpath, value);
    }

    const handleSelectItemChange = (e, dataxpath, xpath) => {
        const value = e.target.value;
        handleFormUpdate(xpath, dataxpath, value);
    }

    const handleCheckboxToggle = (e, dataxpath, xpath) => {
        const value = e.target.checked;
        handleFormUpdate(xpath, dataxpath, value);
    }

    const handleAutocompleteChange = (e, value, dataxpath, xpath) => {
        handleFormUpdate(xpath, dataxpath, value);
    }

    const onNodeMouseClick = (e, tree, node, level, keyPath) => {

        if (e.currentTarget.attributes['data-remove']) {
            let updatedObj = cloneDeep(updatedData);
            let xpath = e.currentTarget.attributes['data-remove'].value;
            xpath = getDataxpath(updatedObj, xpath);
            const isArray = xpath.endsWith(']');
            if (isArray) {
                let index = parseInt(xpath.substring(xpath.lastIndexOf('[') + 1, xpath.lastIndexOf(']')));
                let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                let parentObject = get(updatedObj, parentxpath);
                parentObject.splice(index, 1);
            } else {
                set(updatedObj, xpath, null);
            }
            // let changesDict = getXpathKeyValuePairFromObject(get(updatedObj, xpath));
            onUpdate(updatedObj, 'remove');
        } else if (e.currentTarget.attributes['data-add']) {
            let updatedObj = cloneDeep(updatedData);
            let xpath = e.currentTarget.attributes['data-add'].value;
            xpath = getDataxpath(updatedObj, xpath);
            let ref = e.currentTarget.attributes['data-ref'].value;
            const isArray = xpath.endsWith(']');
            let emptyObject = {};
            if (isArray) {
                if ([DATA_TYPES.NUMBER, DATA_TYPES.STRING].includes(ref)) {
                    let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                    let parentObject = get(updatedObj, parentxpath);
                    parentObject.push(null)
                } else {
                    ref = ref.split('/');
                    let currentSchema = ref.length === 2 ? projectSchema[ref[1]] : projectSchema[ref[1]][ref[2]];
                    if (currentSchema.hasOwnProperty('enum') && Object.keys(currentSchema).length === 1) {
                        let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                        let parentObject = get(updatedObj, parentxpath);
                        parentObject.push(currentSchema.enum[0]);
                    } else {
                        let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                        let originalindex = get(storedData, parentxpath) ? get(storedData, parentxpath).length : 0;
                        let parentObject = get(updatedObj, parentxpath);
                        if (!parentObject) {
                            set(updatedObj, parentxpath, []);
                            parentObject = get(updatedObj, parentxpath);
                        }
                        let parentindex = 0;
                        if (parentObject.length > 0) {
                            let propname = Object.keys(parentObject[parentObject.length - 1]).find(key => key.startsWith('xpath_'));
                            let propxpath = parentObject[parentObject.length - 1][propname];
                            parentindex = parseInt(propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'))) + 1;
                        }
                        let max = originalindex > parentindex ? originalindex : parentindex;
                        let additionalProps = JSON.parse(e.currentTarget.attributes['data-prop'].value);
                        emptyObject = generateObjectFromSchema(projectSchema, cloneDeep(currentSchema), additionalProps);
                        emptyObject = addxpath(emptyObject, parentxpath + '[' + max + ']');
                        parentObject.push(emptyObject);
                    }
                }
            } else {
                ref = ref.split('/');
                let currentSchema = ref.length === 2 ? projectSchema[ref[1]] : projectSchema[ref[1]][ref[2]];
                let additionalProps = JSON.parse(e.currentTarget.attributes['data-prop'].value);
                emptyObject = generateObjectFromSchema(projectSchema, cloneDeep(currentSchema), additionalProps);
                emptyObject = addxpath(emptyObject, xpath);
                set(updatedObj, xpath, emptyObject);
            }
            // let changesDict = getXpathKeyValuePairFromObject(emptyObject);
            onUpdate(updatedObj, 'add');
        }
        else if (e.currentTarget.attributes['data-addcopy']) {
            let updatedObj = cloneDeep(updatedData);
            let xpath = e.currentTarget.attributes['data-addcopy'].value;
            xpath = getDataxpath(updatedObj, xpath);
            let ref = e.currentTarget.attributes['data-ref'].value;
            const isArray = xpath.endsWith(']');
            let dupObj = {};
            let storedObj = cloneDeep(get(updatedObj, xpath));
            if (!storedObj) return;
            storedObj = clearxpath(storedObj);
            if (isArray) {
                clearId(storedObj);
                if ([DATA_TYPES.NUMBER, DATA_TYPES.STRING].includes(ref)) {
                    let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                    let parentObject = get(updatedObj, parentxpath);
                    parentObject.push(null)
                } else {
                    ref = ref.split('/');
                    let currentSchema = ref.length === 2 ? projectSchema[ref[1]] : projectSchema[ref[1]][ref[2]];
                    if (currentSchema.hasOwnProperty('enum') && Object.keys(currentSchema).length === 1) {
                        let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                        let parentObject = get(updatedObj, parentxpath);
                        parentObject.push(currentSchema.enum[0]);
                    } else {
                        let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
                        let originalindex = get(storedData, parentxpath) ? get(storedData, parentxpath).length : 0;
                        let parentObject = get(updatedObj, parentxpath);
                        if (!parentObject) {
                            set(updatedObj, parentxpath, []);
                            parentObject = get(updatedObj, parentxpath);
                        }
                        let parentindex = 0;
                        if (parentObject.length > 0) {
                            let propname = Object.keys(parentObject[parentObject.length - 1]).find(key => key.startsWith('xpath_'));
                            let propxpath = parentObject[parentObject.length - 1][propname];
                            parentindex = parseInt(propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'))) + 1;
                        }
                        let max = originalindex > parentindex ? originalindex : parentindex;
                        let additionalProps = JSON.parse(e.currentTarget.attributes['data-prop'].value);
                        dupObj = generateObjectFromSchema(projectSchema, cloneDeep(currentSchema), additionalProps, null, storedObj);
                        dupObj = addxpath(dupObj, parentxpath + '[' + max + ']');
                        parentObject.push(dupObj);
                    }
                }
            } else {
                console.error('duplicate on object is not supported')
            }
            // let changesDict = getXpathKeyValuePairFromObject(emptyObject);
            onUpdate(updatedObj, 'add');
        }
        else {
            let xpath = e.currentTarget.attributes;
            if (xpath.hasOwnProperty('data-open')) {
                xpath = xpath['data-open'].value;
                setTreeState(xpath, true);
            } else if (xpath.hasOwnProperty('data-close')) {
                xpath = xpath['data-close'].value;
                setTreeState(xpath, false);
            }
            let newTree = cloneDeep(tree);
            setDataTree(newTree);
        }
    }

    const onLeafMouseClick = (event, leaf) => {
        const dataxpath = leaf.dataxpath;
        const parentxpath = dataxpath.substring(0, dataxpath.lastIndexOf('['));
        const index = parseInt(dataxpath.substring(dataxpath.lastIndexOf('[') + 1, dataxpath.lastIndexOf(']')));
        let updatedObj = cloneDeep(updatedData);
        const parent = get(updatedObj, parentxpath);
        parent.splice(index, 1);
        set(updatedObj, parentxpath, parent);
        onUpdate(updatedObj, 'remove');
    }

    return (
        <InfinityMenu
            tree={dataTree}
            disableDefaultHeaderContent={true}
            onNodeMouseClick={onNodeMouseClick}
            onLeafMouseClick={onLeafMouseClick}
        />
    )
}

export default DataTree;