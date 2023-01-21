import React from 'react';
import { Paper } from '@mui/material';
import Icon from './Icon';
import { makeStyles } from '@mui/styles';
import { DoNotTouch, PanTool, Save } from '@mui/icons-material';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    sideDrawer: {
        width: '45px',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '10px 0',
        background: 'rgba(0,0,0,0.85) !important',
        borderRadius: '0 !important'
    },
    icon: {
        backgroundColor: '#ccc !important',
        margin: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    }
})

const SideDrawer = (props) => {

    const classes = useStyles();

    return (
        <Paper className={classes.sideDrawer} elevation={3}>
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