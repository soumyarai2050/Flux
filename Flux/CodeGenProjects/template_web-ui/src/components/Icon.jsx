/**
 * @module Icon
 * @description This module provides components for rendering interactive icons with tooltips.
 */

import React from 'react';
import PropTypes from 'prop-types';
import { Avatar, IconButton, ToggleButton, Tooltip } from '@mui/material';
import classes from './Icon.module.css';

/**
 * @function Icon
 * @description A reusable icon component with a tooltip and customizable styling.
 * @param {object} props - The properties for the component.
 * @param {string} props.title - The text to display in the tooltip.
 * @param {boolean} [props.selected=false] - If true, applies a selected style to the icon.
 * @param {boolean} [props.disabled=false] - If true, disables the icon and its click events.
 * @param {string} [props.name] - The name attribute for the IconButton.
 * @param {function} [props.onClick] - Callback function for click events.
 * @param {function} [props.onDoubleClick] - Callback function for double-click events.
 * @param {React.ReactNode} props.children - The content to be rendered inside the icon (e.g., an MUI icon component).
 * @returns {React.ReactElement} The rendered Icon component.
 */
export const Icon = ({ title, selected = false, disabled = false, name, onClick, onDoubleClick, children }) => {
    const selectedClass = selected ? classes.icon_selected : '';
    const classesStr = `${classes.icon} ${selectedClass}`;

    return (
        <Tooltip title={title} disableInteractive>
            <IconButton
                className={classesStr}
                disabled={disabled}
                name={name}
                size='small'
                onClick={onClick}
                onDoubleClick={onDoubleClick || (() => {})} // Provide a default empty function if not provided
            >
                {children}
            </IconButton>
        </Tooltip>
    );
};

Icon.propTypes = {
    title: PropTypes.string.isRequired,
    selected: PropTypes.bool,
    disabled: PropTypes.bool,
    name: PropTypes.string,
    onClick: PropTypes.func,
    onDoubleClick: PropTypes.func,
    children: PropTypes.node.isRequired,
};

/**
 * @function ToggleIcon
 * @description A toggleable icon component with a tooltip, typically used for selection or state indication.
 * @param {object} props - The properties for the component.
 * @param {string} props.title - The text to display in the tooltip.
 * @param {boolean} props.selected - If true, indicates the icon is in a toggled/selected state.
 * @param {string} props.name - The name attribute for the ToggleButton and value for onClick.
 * @param {function} props.onClick - Callback function for click events, receives the `name` prop as an argument.
 * @param {React.ReactNode} props.children - The content to be rendered inside the Avatar (e.g., a single character or an icon).
 * @returns {React.ReactElement} The rendered ToggleIcon component.
 */
export const ToggleIcon = ({ title, selected, name, onClick, children }) => {
    const selectedIconClass = selected ? classes.selected_icon : '';
    const selectedAvatarClass = selected ? classes.selected_avatar : '';

    return (
        <Tooltip title={title} disableInteractive>
            <ToggleButton
                className={`${classes.toggle_icon} ${selectedIconClass}`}
                size='small'
                name={name}
                selected={selected}
                value={name}
                onClick={() => onClick(name)}
            >
                <Avatar className={`${classes.avatar} ${selectedAvatarClass}`}>{children}</Avatar>
            </ToggleButton>
        </Tooltip>
    );
};

ToggleIcon.propTypes = {
    title: PropTypes.string.isRequired,
    selected: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired,
    children: PropTypes.node.isRequired,
};

export default Icon;
