import React from 'react';
import { Avatar, Box, IconButton, ToggleButton, Tooltip } from '@mui/material';
import classes from './Icon.module.css';

export const Icon = (props) => {
    let selectedClass = '';
    if (props.selected) {
        selectedClass = classes.icon_selected;
    }
    const classesStr = `${classes.icon} ${selectedClass}`
    return (
        <Tooltip title={props.title} disableInteractive>
            <IconButton
                className={classesStr}
                disabled={props.disabled}
                name={props.name}
                size='small'
                onClick={props.onClick}
                onDoubleClick={props.onDoubleClick ? props.onDoubleClick : () => { }}>
                {props.children}
            </IconButton>
        </Tooltip>
    )
}

export default Icon;

export const ToggleIcon = (props) => {
    let selectedAvatarClass = '';
    let selectedIconClass = '';
    if (props.selected) {
        selectedIconClass = classes.selected_icon;
        selectedAvatarClass = classes.selected_avatar;
    }

    return (
        <Tooltip title={props.title} disableInteractive>
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