import React from 'react';
import { makeStyles } from '@mui/styles';
import { LinearProgress, Tooltip } from '@mui/material';
import { ColorTypes, HoverTextType } from '../constants';
import { getColorTypeFromPercentage, normalise } from '../utils';

const useStyles = makeStyles({
    progressBar: {
        height: '10px !important',
        borderRadius: 10,
        width: '100%'
    },
    success: {
        '& .MuiLinearProgress-bar1Determinate': {
            background: 'green !important'
        }
    },
    critical: {
        '& .MuiLinearProgress-bar1Determinate': {
            background: '#9C0006 !important',
            animation: `$blink 0.5s step-start infinite`
        }
    },
    error: {
        '& .MuiLinearProgress-bar1Determinate': {
            background: '#9C0006 !important'
        }
    },
    warning: {
        '& .MuiLinearProgress-bar1Determinate': {
            background: '#99942c !important'
        }
    },
    info: {
        '& .MuiLinearProgress-bar1Determinate': {
            background: 'blue !important'
        }
    },
    debug: {
        '& .MuiLinearProgress-bar1Determinate': {
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

export const ValueBasedProgressBarWithHover = (props) => {

    const classes = useStyles();

    let percentage = normalise(props.value, props.max, props.min);
    let reverse = props.collection.progressBar.is_reverse ? true : false;
    if(reverse) {
        percentage = normalise(props.max - props.value, props.max, props.min);
    }

    let color = getColorTypeFromPercentage(props.collection, percentage);

    let progressBarColorClass = '';
    if (color === ColorTypes.CRITICAL) progressBarColorClass = classes.critical;
    else if (color === ColorTypes.ERROR) progressBarColorClass = classes.error;
    else if (color === ColorTypes.WARNING) progressBarColorClass = classes.warning;
    else if (color === ColorTypes.INFO) progressBarColorClass = classes.info;
    else if (color === ColorTypes.DEBUG) progressBarColorClass = classes.debug;
    else if (color === ColorTypes.SUCCESS) progressBarColorClass = classes.success;

    let hoverText = '';
    if(props.hoverType === HoverTextType.HoverTextType_VALUE) {
        hoverText = props.value + '/' + props.max;
    } else if(props.hoverType === HoverTextType.HoverTextType_PERCENTAGE) {
        hoverText = props.percentage + '%';
    } else if(props.hoverType === HoverTextType.HoverTextType_VALUE_AND_PERCENTAGE) {
        hoverText = props.value + '/' + props.max + ' | ' + props.percentage + '%';  
    }

    return (
        <Tooltip title={hoverText}>
            <LinearProgress variant="determinate" value={percentage} className={`${classes.progressBar} ${progressBarColorClass}`} />
        </Tooltip>
    )
}