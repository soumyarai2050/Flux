/**
 * @module AlertBubble
 * @description This module provides a component for displaying an alert bubble with a count.
 */

import React from 'react';
import PropTypes from 'prop-types';
import Badge from '@mui/material/Badge';
import { useTheme } from '@mui/material/styles';
import { getResolvedColor } from '../../../utils/ui/colorUtils';
import { getContrastColor } from '../../../utils/ui/uiUtils';
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
    const theme = useTheme();

    // Resolve color using the centralized utility with animation support
    const colorStyleObj = getResolvedColor(color, theme, null, true);

    // Determine the final background color
    const backgroundColor = colorStyleObj ? (colorStyleObj.backgroundColor || colorStyleObj.color) : null;

    // Calculate the contrasting text color
    const textColor = backgroundColor ? getContrastColor(backgroundColor) : 'inherit';

    // Create sx styles for the dynamic color
    const colorSx = backgroundColor ? {
        '& .MuiBadge-badge': {
            // Spread all style properties (color, backgroundColor, animation, etc.)
            ...colorStyleObj,
            backgroundColor: backgroundColor,
            color: textColor // Apply the contrast color to the text
        }
    } : {};

    return (
        <Badge
            className={classes.alert_bubble}
            sx={colorSx}
            badgeContent={content}
            max={999}
        />
    );
};

AlertBubble.propTypes = {
    content: PropTypes.number.isRequired,
    color: PropTypes.string,
};

export default AlertBubble;