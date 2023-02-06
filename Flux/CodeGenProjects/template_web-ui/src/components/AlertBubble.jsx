import React from 'react';
import classes from './AlertBubble.module.css';
import { Badge } from '@mui/material';

const AlertBubble = (props) => {
    let alertBubbleClass = classes.alert_bubble;
    if (props.color) {
        alertBubbleClass += ' ' + classes[props.color];
    }

    return (
        <Badge className={alertBubbleClass} badgeContent={props.content} />
    )
}

export default AlertBubble;