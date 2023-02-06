import React from 'react';
import { Avatar, Box, IconButton, ToggleButton, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';
import classes from './Icon.module.css';

export const Icon = (props) => {
    return (
        <Tooltip title={props.title}>
            <IconButton
                className={classes.icon}
                disabled={props.disabled}
                name={props.name}
                size='small'
                onClick={props.onClick}>
                {props.children}
            </IconButton>
        </Tooltip>
    )
}

export const ToggleIcon = (props) => {
    return (
        <Tooltip title={props.title}>
            <Box className={classes.toggle_icon_container}>
                <ToggleButton
                    className={classes.toggle_icon}
                    size='small'
                    name={props.name}
                    selected={props.selected}
                    value={props.name}
                    onClick={() => props.onClick(props.name)}>
                    <Avatar className={classes.avatar}>{props.children}</Avatar>
                </ToggleButton>
            </Box>
        </Tooltip>
    )
}