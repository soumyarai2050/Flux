import React from 'react';
import { Avatar, Box, IconButton, ToggleButton, Tooltip } from '@mui/material';
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
    let selectedAvatarClass = '';
    let selectedIconClass = '';
    if (props.selected) {
        selectedIconClass = classes.selected_icon;
        selectedAvatarClass = classes.selected_avatar;
    }

    return (
        <Tooltip title={props.title}>
            <ToggleButton
                className={`${classes.toggle_icon} ${selectedIconClass}`}
                size='small'
                name={props.name}
                selected={props.selected}
                value={props.name}
                onClick={() => props.onClick(props.name)}>
                <Avatar className={`${classes.avatar} ${selectedAvatarClass}`}>{props.children}</Avatar>
            </ToggleButton>
        </Tooltip>
    )
}