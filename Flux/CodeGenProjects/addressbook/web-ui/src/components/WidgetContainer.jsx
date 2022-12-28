import React, { Fragment, useState, useCallback } from 'react';
import { Typography, Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { Save, Cached, Edit, AccountTree, TableView } from '@mui/icons-material';
import Icon from './Icon';
import { Modes, Layouts } from '../constants';
import PropTypes from 'prop-types';
import CommonKeyWidget from './CommonKeyWidget';

const useStyles = makeStyles({
    widgetHeader: {
        background: '#0097a7',
        color: 'white',
        minHeight: 40,
        display: 'flex',
        alignItems: 'center',
        padding: '0 20px',
        justifyContent: 'space-between'
    },
    widgetBody: {
        padding: 10,
        height: 'calc(100% - 40px)',
        overflow: 'auto'
    },
    widgetBodyEdit: {
        background: 'beige'
    },
    icon: {
        backgroundColor: '#ccc !important',
        marginRight: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    },
    menuContainer: {
        display: 'inline-flex',
        alignItems: 'center'
    }
})

const WidgetContainer = (props) => {
    const [commonkeyHeight, setCommonkeyHeight] = useState(0);
    const classes = useStyles();

    const commonkey = useCallback(node => {
        if (node !== null) {
            setCommonkeyHeight(node.offsetHeight);
        } else {
            setCommonkeyHeight(0);
        }
    }, [])

    let modeMenu = '';
    if (props.onSave && props.mode === Modes.EDIT_MODE) {
        modeMenu = <Icon className={classes.icon} title="Save" onClick={props.onSave}><Save fontSize='small' /></Icon>
    } else if (props.onChangeMode && props.mode === Modes.READ_MODE) {
        modeMenu = <Icon className={classes.icon} title="Edit" onClick={props.onChangeMode}><Edit fontSize='small' /></Icon>
    }

    let layoutMenu = '';
    if (props.layout === Layouts.TABLE_LAYOUT) {
        layoutMenu = <Icon className={classes.icon} title="Tree View" onClick={props.onChangeLayout} ><AccountTree fontSize='small' /></Icon>
    } else if (props.layout === Layouts.TREE_LAYOUT) {
        layoutMenu = <Icon className={classes.icon} title="Table View" onClick={props.onChangeLayout} ><TableView fontSize='small' /></Icon>
    }

    return (
        <Fragment>
            <Typography variant='h6'>
                <div className={classes.widgetHeader}>
                    <span>{props.title}</span>
                    <span>{props.centerText}</span>
                    <div className={classes.menuContainer}>
                        {props.menu}
                        {modeMenu}
                        {layoutMenu}
                        {props.onReload && <Icon className={classes.icon} title="Reload" onClick={props.onReload}><Cached fontSize='small' /></Icon>}
                        {props.menuRight}
                    </div>
                </div>
            </Typography>
            {props.commonkeys && Object.keys(props.commonkeys).length > 0 && props.mode !== Modes.EDIT_MODE && <CommonKeyWidget ref={commonkey} commonkeys={props.commonkeys} />}
            <Box style={{ height: `calc(100% - 40px - ${commonkeyHeight}px` }} className={`${classes.widgetBody} ${props.mode === Modes.EDIT_MODE ? classes.widgetBodyEdit : ''}`}>
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