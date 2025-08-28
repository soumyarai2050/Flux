/**
 * @module AlertBubble
 * @description This module provides a component for displaying an alert bubble with a count.
 */

import React from 'react';
import PropTypes from 'prop-types';
import { Badge } from '@mui/material';
import classes from './AlertBubble.module.css';

/**
 * @function AlertBubble
 * @description A component to display an alert bubble with a count.
 * @param {object} props - The properties for the component.
 * @param {number} props.content - The content of the alert bubble (the count).
 * @param {string} [props.color] - The color of the alert bubble.
 * @returns {React.ReactElement} The rendered AlertBubble component.
 */
const AlertBubble = ({ content, color }) => {
    let alertBubbleClass = classes.alert_bubble;
    if (color) {
        alertBubbleClass += ` ${classes[color]}`;
    }

    return (
        <Badge className={alertBubbleClass} badgeContent={content} max={999} />
    );
};

AlertBubble.propTypes = {
    content: PropTypes.number.isRequired,
    color: PropTypes.string,
};

export default AlertBubble;