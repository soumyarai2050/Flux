import React, { Fragment, useRef } from 'react';
import _ from 'lodash';
import { Typography, Box } from '@mui/material';
import { Save, Cached, Edit, AccountTree, TableView } from '@mui/icons-material';
import { Icon } from './Icon';
import { Modes, Layouts } from '../constants';
import PropTypes from 'prop-types';
import CommonKeyWidget from './CommonKeyWidget';
import classes from './WidgetContainer.module.css';

const WidgetContainer = (props) => {
    const commonkeyRef = useRef(null);

    let modeMenu = '';
    if (props.onSave && props.mode === Modes.EDIT_MODE) {
        modeMenu = <Icon className={classes.icon} name="Save" title="Save" onClick={props.onSave}><Save fontSize='small' /></Icon>
    } else if (props.onChangeMode && props.mode === Modes.READ_MODE) {
        modeMenu = <Icon className={classes.icon} name="Edit" title="Edit" onClick={props.onChangeMode}><Edit fontSize='small' /></Icon>
    }

    let layoutMenu = '';
    if (props.layout === Layouts.TABLE_LAYOUT) {
        layoutMenu = <Icon className={classes.icon} name="Tree" title="Tree View" onClick={() => props.onChangeLayout(props.name, Layouts.TREE_LAYOUT)} ><AccountTree fontSize='small' /></Icon>
    } else if (props.layout === Layouts.TREE_LAYOUT) {
        layoutMenu = <Icon className={classes.icon} name="Table" title="Table View" onClick={() => props.onChangeLayout(props.name, Layouts.TABLE_LAYOUT)} ><TableView fontSize='small' /></Icon>
    }

    let commonkeys = props.commonkeys ? props.commonkeys.filter(commonkey => {
        if (commonkey.value === null || commonkey.value === undefined) return false;
        else if (_.isObject(commonkey.value) && _.keys(commonkey.value).length === 0) return false;
        else if (Array.isArray(commonkey.value) && commonkey.value.length === 0) return false;
        else if (Number.isInteger(commonkey.value) && commonkey.value === 0) {
            if (commonkey.displayZero) return true;
            return false;
        }
        else return true;
    }) : [];

    let height = 0;
    if (commonkeyRef.current !== null) {
        height = commonkeyRef.current.offsetHeight;
    }

    return (
        <Fragment>
            <Typography variant='h6'>
                <div className={classes.widget_header}>
                    <span>{props.title}</span>
                    <span>{props.centerText}</span>
                    <div className={classes.menu_container}>
                        {props.menu}
                        {modeMenu}
                        {layoutMenu}
                        {props.onReload && <Icon className={classes.icon} name="Reload" title="Reload" onClick={props.onReload}><Cached fontSize='small' /></Icon>}
                        {props.menuRight}
                    </div>
                </div>
            </Typography>
            {commonkeys.length > 0 && props.mode !== Modes.EDIT_MODE && <CommonKeyWidget ref={commonkeyRef} commonkeys={commonkeys} lineBreakStart={props.lineBreakStart} lineBreakEnd={props.lineBreakEnd} />}
            <Box style={{ height: `calc(100% - 42px - ${height}px` }} className={`${classes.widget_body} ${props.mode === Modes.EDIT_MODE ? classes.edit : ''}`}>
                {props.children}
            </Box>
        </Fragment >
    )
}

WidgetContainer.propTypes = {
    title: PropTypes.string,
    centerText: PropTypes.string,
    menu: PropTypes.oneOfType([PropTypes.element, PropTypes.string]),
    mode: PropTypes.string,
    layout: PropTypes.string,
    commonkeys: PropTypes.array.isRequired,
    onChangeMode: PropTypes.func,
    onChangeLayout: PropTypes.func,
    onSave: PropTypes.func,
    children: PropTypes.any,
    lineBreakStart: PropTypes.bool,
    lineBreakEnd: PropTypes.bool
}

WidgetContainer.defaultProps = {
    commonkeys: [],
    lineBreakStart: true,
    lineBreakEnd: true
}

export default WidgetContainer;