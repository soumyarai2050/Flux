import React from 'react';
import { Paper } from '@mui/material';
import {Icon} from './Icon';
import { DoNotTouch, PanTool, Save } from '@mui/icons-material';
import PropTypes from 'prop-types';
import classes from './SideDrawer.module.css';

const SideDrawer = (props) => {

    return (
        <Paper className={classes.side_drawer} elevation={3}>
            {props.draggable ? (
                <Icon className={classes.icon} name="DisableDrag" title='Disable Drag' onClick={props.onToggleDrag}>
                    <DoNotTouch fontSize='medium' />
                </Icon>

            ) : (
                <Icon className={classes.icon} name="EnableDrag" title='Enable Drag' onClick={props.onToggleDrag}>
                    <PanTool fontSize='medium' />
                </Icon>
            )}
            {props.children}
        </Paper>
    )
}

SideDrawer.propTypes = {
    draggable: PropTypes.bool.isRequired,
    onToggleDrag: PropTypes.func.isRequired
}

export default SideDrawer;