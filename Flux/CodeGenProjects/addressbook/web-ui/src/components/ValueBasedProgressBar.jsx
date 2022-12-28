import React from 'react';
import { makeStyles } from '@mui/styles';
import { LinearProgress, Box, Typography, Grid } from '@mui/material';
import PropTypes from 'prop-types';
import { ColorTypes } from '../constants';

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

export const ValueBasedProgressBar = (props) => {

    const classes = useStyles();

    let progressBarColorClass = '';
    if (props.color === ColorTypes.CRITICAL) progressBarColorClass = classes.critical;
    else if (props.color === ColorTypes.ERROR) progressBarColorClass = classes.error;
    else if (props.color === ColorTypes.WARNING) progressBarColorClass = classes.warning;
    else if (props.color === ColorTypes.INFO) progressBarColorClass = classes.info;
    else if (props.color === ColorTypes.DEBUG) progressBarColorClass = classes.debug;
    else if (props.color === ColorTypes.SUCCESS) progressBarColorClass = classes.success;

    return (
            <LinearProgress variant="determinate" value={props.percentage} className={`${classes.progressBar} ${progressBarColorClass}`} />
    )
}

export const ValueBasedProgressBarWithLabel = (props) => {

    const classes = useStyles();

    let progressBarColorClass = '';
    if (props.color === ColorTypes.CRITICAL) progressBarColorClass = classes.critical;
    else if (props.color === ColorTypes.ERROR) progressBarColorClass = classes.error;
    else if (props.color === ColorTypes.WARNING) progressBarColorClass = classes.warning;
    else if (props.color === ColorTypes.INFO) progressBarColorClass = classes.info;
    else if (props.color === ColorTypes.DEBUG) progressBarColorClass = classes.debug;
    else if (props.color === ColorTypes.SUCCESS) progressBarColorClass = classes.success;

    return (

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box sx={{ width: '100%', mr: 1 }}>
                <LinearProgress variant="determinate" value={props.percentage} className={`${classes.progressBar} ${progressBarColorClass}`} />
            </Box>
            <Box sx={{ minWidth: 35 }}>
                <Typography variant="body2" color="text.secondary">
                    {props.value}/{props.max}
                </Typography>
            </Box>
        </Box>
    )
}