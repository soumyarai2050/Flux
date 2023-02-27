import React, { useState, useEffect } from 'react';
import WidgetContainer from './WidgetContainer';
import InfinityMenu from 'react-infinity-menu-plus';
import _, { cloneDeep } from 'lodash';
import { generateTreeStructure, generateObjectFromSchema, addxpath, getDataxpath, setTreeState, getXpathKeyValuePairFromObject } from '../utils';
import {Icon} from './Icon';
import { UnfoldMore, UnfoldLess, VisibilityOff, Visibility } from '@mui/icons-material';
import { MenuItem, Checkbox, FormControlLabel, Select } from '@mui/material';
import Alert from './Alert';
import PropTypes from 'prop-types';
import { DataTypes } from '../constants';
import classes from './TreeWidget.module.css';

const TreeWidget = (props) => {

    const [treeStructure, setTreeStructure] = useState([]);
    const [isOpen, setIsOpen] = useState(); // to set whether the node header is open or close.
    const [expand, setExpand] = useState(true);
    const [hide, setHide] = useState(true);
    const [showDataType, setShowDataType] = useState(false);
    const [openShowDropdown, setOpenShowDropdown] = useState(false);

    useEffect(() => {
        setTreeStructure(generateTreeStructure(cloneDeep(props.schema), props.name, {
            'data': props.data,
            'isOpen': isOpen,
            'hide': hide,
            'showDataType': showDataType,
            'originalData': props.originalData,
            'subtree': props.subtree,
            'mode': props.mode,
            'xpath': props.xpath,
            'onTextChange': props.onTextChange ? props.onTextChange : onTextChange,
            // 'onKeyDown': props.onKeyDown ? props.onKeyDown : onKeyDown,
            'onSelectItemChange': props.onSelectItemChange ? props.onSelectItemChange : onSelectItemChange,
            'onCheckboxChange': props.onCheckboxChange ? props.onCheckboxChange : onCheckboxChange,
            'onAutocompleteOptionChange': props.onAutocompleteOptionChange ? props.onAutocompleteOptionChange : onAutocompleteOptionChange,
            'onDateTimeChange': props.onDateTimeChange ? props.onDateTimeChange : onDateTimeChange
        }))
        setIsOpen();
    }, [props.schema, props.data, props.mode, props.subtree, props.xpath, isOpen, hide, showDataType])

    const onClose = () => {
        setOpenShowDropdown(false);
    }

    const onTreeChange = (value) => {
        setExpand(value);
        setIsOpen(value);
    }

    const onTextChange = (e, type, xpath, value) => {
        let updatedData = cloneDeep(props.data);
        let dataxpath = e.target.getAttribute('dataxpath');
        if (type === DataTypes.NUMBER) {
            value = value * 1;
        }

        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onDateTimeChange = (dataxpath, xpath, value) => {
        console.log(value);
        let updatedData = cloneDeep(props.data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onSelectItemChange = (e, dataxpath, xpath) => {
        let updatedData = cloneDeep(props.data);
        _.set(updatedData, dataxpath, e.target.value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.value);
    }

    const onCheckboxChange = (e, dataxpath, xpath) => {
        let updatedData = cloneDeep(props.data);
        _.set(updatedData, dataxpath, e.target.checked);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, e.target.checked);
    }

    const onAutocompleteOptionChange = (e, value, dataxpath, xpath) => {
        let updatedData = cloneDeep(props.data);
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onNodeMouseClick = (e, tree, node, level, keyPath) => {

        if (e.currentTarget.attributes['data-remove']) {
            let updatedData = cloneDeep(props.data);
            let xpath = e.currentTarget.attributes['data-remove'].value;
            xpath = getDataxpath(updatedData, xpath);
            let index = parseInt(xpath.substring(xpath.lastIndexOf('[') + 1, xpath.lastIndexOf(']')));
            let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
            let parentObject = _.get(updatedData, parentxpath);
            let changesDict = getXpathKeyValuePairFromObject(_.get(updatedData, xpath));
            props.onUserChange(undefined, undefined, true, changesDict);
            parentObject.splice(index, 1);
            console.log({ updatedData });
            props.onUpdate(updatedData, 'remove');
        } else if (e.currentTarget.attributes['data-add']) {
            let updatedData = cloneDeep(props.data);
            let xpath = e.currentTarget.attributes['data-add'].value;
            xpath = getDataxpath(updatedData, xpath);
            let index = parseInt(xpath.substring(xpath.lastIndexOf('[') + 1, xpath.lastIndexOf(']')));
            let parentxpath = xpath.substring(0, xpath.lastIndexOf('['));
            let originalindex = _.get(props.originalData, parentxpath) ? _.get(props.originalData, parentxpath).length : 0;
            let parentObject = _.get(updatedData, parentxpath);
            if (!parentObject) {
                _.set(updatedData, parentxpath, []);
                parentObject = _.get(updatedData, parentxpath);
            }
            let parentindex = 0;
            if (parentObject.length > 0) {
                let propname = _.keys(parentObject[parentObject.length - 1]).filter(key => key.startsWith('xpath_'))[0];
                let propxpath = parentObject[parentObject.length - 1][propname];
                parentindex = parseInt(propxpath.substring(propxpath.lastIndexOf('[') + 1, propxpath.lastIndexOf(']'))) + 1;
            }
            let max = originalindex > parentindex ? originalindex : parentindex;
            let ref = e.currentTarget.attributes['data-ref'].value;
            if (ref) {
                ref = ref.split('/');
            }
            let currentSchema = ref.length === 2 ? props.schema[ref[1]] : props.schema[ref[1]][ref[2]];
            let emptyObject = generateObjectFromSchema(props.schema, currentSchema);
            emptyObject = addxpath(emptyObject, parentxpath + '[' + max + ']');
            let changesDict = getXpathKeyValuePairFromObject(emptyObject);
            props.onUserChange(undefined, undefined, false, changesDict);
            parentObject.push(emptyObject);
            console.log({ updatedData });
            props.onUpdate(updatedData, 'add');
        } else {
            let xpath = e.currentTarget.attributes;
            if (xpath.hasOwnProperty('data-open')) {
                xpath = xpath['data-open'].value;
                setTreeState(xpath, true);
            } else if (xpath.hasOwnProperty('data-close')) {
                xpath = xpath['data-close'].value;
                setTreeState(xpath, false);
            }
            let newTree = cloneDeep(tree);
            setTreeStructure(newTree);
        }
    }

    let menu = (
        <>
            {props.headerProps.menu}
            {expand ? (
                <Icon className={classes.icon} name="Collapse" title='Collapse All' onClick={() => onTreeChange(false)}><UnfoldLess fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} name="Expand" title='Expand All' onClick={() => onTreeChange(true)}><UnfoldMore fontSize='small' /></Icon>
            )}
            <Icon className={classes.icon} name="Show" title='Show' onClick={() => setOpenShowDropdown(true)}><Visibility fontSize='small' /></Icon>
            <Select
                className={classes.dropdown}
                size='small'
                open={openShowDropdown}
                value=''
                onClose={onClose}>
                <MenuItem dense={true}>
                    <FormControlLabel size='small'
                        label='Show hidden fields'
                        control={
                            <Checkbox
                                size='small'
                                checked={hide ? false : true}
                                onChange={() => setHide(!hide)}
                            />
                        }
                    />
                </MenuItem>
                <MenuItem dense={true}>
                    <FormControlLabel size='small'
                        label='Show data type'
                        control={
                            <Checkbox
                                size='small'
                                checked={showDataType}
                                onChange={() => setShowDataType(!showDataType)}
                            />
                        }
                    />
                </MenuItem>
            </Select>
            {/* {hide ? (
                
            ) : (
                <Icon className={classes.icon} name="Hide" title='Hide hidden fields' onClick={() => setHide(true)}><VisibilityOff fontSize='small' /></Icon>
            )} */}

        </>
    )

    return (
        <WidgetContainer
            name={props.headerProps.name}
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            layout={props.headerProps.layout}
            onChangeMode={props.headerProps.onChangeMode}
            onChangeLayout={props.headerProps.onChangeLayout}
            onReload={props.headerProps.onReload}
            onSave={props.headerProps.onSave}
            menu={menu}
            menuRight={props.headerProps.menuRight}>
            <InfinityMenu
                tree={treeStructure}
                disableDefaultHeaderContent={true}
                onNodeMouseClick={onNodeMouseClick}
            />
            {props.error && <Alert open={props.error ? true : false} onClose={props.onResetError} severity='error'>{props.error}</Alert>}
        </WidgetContainer>
    )
}

TreeWidget.propTypes = {
    headerProps: PropTypes.object.isRequired,
    name: PropTypes.string.isRequired,
    schema: PropTypes.object.isRequired,
    data: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    originalData: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    mode: PropTypes.string.isRequired,
    onUpdate: PropTypes.func.isRequired,
    error: PropTypes.string,
    onResetError: PropTypes.func
}

export default TreeWidget;