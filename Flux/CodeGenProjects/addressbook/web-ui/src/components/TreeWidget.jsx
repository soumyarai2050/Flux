import React, { useState, useEffect } from 'react';
import WidgetContainer from './WidgetContainer';
import InfinityMenu from 'react-infinity-menu-plus';
import _, { cloneDeep } from 'lodash';
import { generateTreeStructure, generateObjectFromSchema, addxpath, getDataxpath, setTreeState } from '../utils';
import Icon from './Icon';
import { UnfoldMore, UnfoldLess, VisibilityOff, Visibility } from '@mui/icons-material';
import { makeStyles } from '@mui/styles';
import Alert from './Alert';
import PropTypes from 'prop-types';
import { DataTypes } from '../constants';

const useStyles = makeStyles({
    icon: {
        backgroundColor: '#ccc !important',
        marginRight: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    }
})

const TreeWidget = (props) => {

    const [treeStructure, setTreeStructure] = useState([]);
    const [isOpen, setIsOpen] = useState(); // to set whether the node header is open or close.
    const [expand, setExpand] = useState(true);
    const [hide, setHide] = useState(true);
    const classes = useStyles();

    useEffect(() => {
        setTreeStructure(generateTreeStructure(cloneDeep(props.schema), props.name, {
            'data': props.data,
            'isOpen': isOpen,
            'hide': hide,
            'originalData': props.originalData,
            'subtree': props.subtree,
            'mode': props.mode,
            'xpath': props.xpath,
            'onTextChange': props.onTextChange ? props.onTextChange : onTextChange,
            'onKeyDown': props.onKeyDown ? props.onKeyDown : onKeyDown,
            'onSelectItemChange': props.onSelectItemChange ? props.onSelectItemChange : onSelectItemChange,
            'onCheckboxChange': props.onCheckboxChange ? props.onCheckboxChange : onCheckboxChange,
            'onAutocompleteOptionChange': props.onAutocompleteOptionChange ? props.onAutocompleteOptionChange : onAutocompleteOptionChange
        }))
        setIsOpen();
    }, [props.schema, props.data, props.mode, props.subtree, props.xpath, isOpen, hide])

    const onTreeChange = (value) => {
        setExpand(value);
        setIsOpen(value);
    }

    const onTextChange = (e, type, xpath) => {
        let updatedData = cloneDeep(props.data);
        let dataxpath = e.target.getAttribute('dataxpath');
        let value = e.target.value;
        if (type === DataTypes.NUMBER) {
            value = value * 1;
        }
        _.set(updatedData, dataxpath, value);
        props.onUpdate(updatedData);
        props.onUserChange(xpath, value);
    }

    const onKeyDown = (e, type) => {
        let underlyingtype = e.target.getAttribute('underlyingtype');
        if (type === DataTypes.NUMBER && underlyingtype === DataTypes.INT32) {
            if (e.keyCode === 110) {
                e.preventDefault();
            }
        }
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
            emptyObject = addxpath(emptyObject, parentxpath + '[' + max + ']')
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
                <Icon className={classes.icon} title='Collapse All' onClick={() => onTreeChange(false)}><UnfoldLess fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} title='Expand All' onClick={() => onTreeChange(true)}><UnfoldMore fontSize='small' /></Icon>
            )}
            {hide ? (
                <Icon className={classes.icon} title='Show hidden fields' onClick={() => setHide(false)}><Visibility fontSize='small' /></Icon>
            ) : (
                <Icon className={classes.icon} title='Hide hidden fields' onClick={() => setHide(true)}><VisibilityOff fontSize='small' /></Icon>
            )}
        </>
    )

    return (
        <WidgetContainer
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
    data: PropTypes.object,
    originalData: PropTypes.object,
    mode: PropTypes.string.isRequired,
    onUpdate: PropTypes.func.isRequired,
    error: PropTypes.string,
    onResetError: PropTypes.func
}

export default TreeWidget;