import React, { Fragment, useState, useCallback } from 'react';
import { Typography, Box } from '@mui/material';
import { Save, Cached, Edit, AccountTree, TableView } from '@mui/icons-material';
import { Icon } from './Icon';
import { Modes, Layouts } from '../constants';
import PropTypes from 'prop-types';
import CommonKeyWidget from './CommonKeyWidget';
import classes from './WidgetContainer.module.css';

const WidgetContainer = (props) => {
    const [commonkeyHeight, setCommonkeyHeight] = useState(0);

    const commonkey = useCallback(node => {
        if (node !== null) {
            setCommonkeyHeight(node.offsetHeight);
        } else {
            setCommonkeyHeight(0);
        }
    }, [])

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
        if (commonkey.value == {} || commonkey.value == []) return false;
        return true;
    }) : [];

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
            {commonkeys.length > 0 && props.mode !== Modes.EDIT_MODE && <CommonKeyWidget ref={commonkey} commonkeys={commonkeys} />}
            <Box style={{ height: `calc(100% - 40px - ${commonkeyHeight}px` }} className={`${classes.widget_body} ${props.mode === Modes.EDIT_MODE ? classes.edit : ''}`}>
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
    onChangeMode: PropTypes.func,
    onChangeLayout: PropTypes.func,
    onSave: PropTypes.func,
    children: PropTypes.any
}

export default WidgetContainer;