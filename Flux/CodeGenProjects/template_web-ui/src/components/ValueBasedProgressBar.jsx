import React from 'react';
import { LinearProgress, Tooltip } from '@mui/material';
import { HOVER_TEXT_TYPES } from '../constants';
import { getColorTypeFromPercentage, normalise } from '../utils/index.js';
import classes from './ValueBasedProgressBar.module.css';

export const ValueBasedProgressBarWithHover = (props) => {


    let percentage = normalise(props.value, props.max, props.min);
    let reverse = props.collection.progressBar.is_reverse ? true : false;
    if (reverse) {
        percentage = normalise(props.max - props.value, props.max, props.min);
    }

    let color = getColorTypeFromPercentage(props.collection, percentage);

    let progressBarColorClass = classes[color];

    let maxFieldName = '';
    if (props.maxFieldName) {
        maxFieldName = props.maxFieldName + ': ';
    }

    let hoverText = '';
    if (props.hoverType === HOVER_TEXT_TYPES.VALUE) {
        hoverText = `${props.valueFieldName}: ${props.value ? props.value.toLocaleString() : ''}/${maxFieldName}${props.max ? props.max.toLocaleString() : ''}`;
    } else if (props.hoverType === HOVER_TEXT_TYPES.PERCENTAGE) {
        hoverText = props.percentage + ' %';
    } else if (props.hoverType === HOVER_TEXT_TYPES.VALUE_AND_PERCENTAGE) {
        hoverText = `${props.valueFieldName}: ${props.value ? props.value.toLocaleString() : ''}/${maxFieldName}${props.max ? props.max.toLocaleString() : ''}|${props.percentage} %`;
    }

    let progressBarClass = classes.progress_bar;
    if (props.inlineTable) {
        progressBarClass = classes.progress_bar_cell;
    }

    return (
        <Tooltip title={hoverText} disableInteractive>
            <LinearProgress variant="determinate" color='secondary' value={percentage} className={`${progressBarClass} ${progressBarColorClass}`} />
        </Tooltip>
    )
}