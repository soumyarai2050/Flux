import React from 'react';
import { makeStyles } from '@mui/styles';
import { Badge } from '@mui/material';
import { ColorTypes } from '../constants';

const useStyles = makeStyles({
    alertBubble: {
        margin: '0px 10px',
        color: 'white !important',
    },
    alertBubbleCritical: {
        "& .MuiBadge-badge": {
            background: '#9C0006 !important',
            animation: `$blink 0.5s step-start infinite`
        }
    },
    alertBubbleError: {
        "& .MuiBadge-badge": {
            color: 'white !important',
            background: '#9C0006 !important'
        }
    },
    alertBubbleWarning: {
        "& .MuiBadge-badge": {
            color: 'white !important',
            background: '#99942c !important'
        }
    },
    alertBubbleInfo: {
        "& .MuiBadge-badge": {
            color: 'white !important',
            background: 'blue !important'
        }
    },
    alertBubbleSuccess: {
        "& .MuiBadge-badge": {
            color: 'white !important',
            background: 'green !important'
        }
    },
    alertBubbleDebug: {
        "& .MuiBadge-badge": {
            color: 'white !important',
            background: '#777 !important'
        }
    },
    "@keyframes blink": {
        "from": {
            opacity: 1
        },
        "50%": {
            opacity: 0.8
        },
        "to": {
            opacity: 1
        }
    }
})

const AlertBubble = (props) => {

    const classes = useStyles();

    let alertBubbleClass = '';
    if (props.color === ColorTypes.CRITICAL) alertBubbleClass = classes.alertBubbleCritical;
    else if (props.color === ColorTypes.ERROR) alertBubbleClass = classes.alertBubbleError;
    else if (props.color === ColorTypes.WARNING) alertBubbleClass = classes.alertBubbleWarning;
    else if (props.color === ColorTypes.SUCCESS) alertBubbleClass = classes.alertBubbleSuccess;
    else if (props.color === ColorTypes.INFO) alertBubbleClass = classes.alertBubbleInfo;
    else if (props.color === ColorTypes.DEBUG) alertBubbleClass = classes.alertBubbleDebug;

    return (
        <Badge className={`${classes.alertBubble} ${alertBubbleClass}`} badgeContent={props.content} />
    )
}

export default AlertBubble;