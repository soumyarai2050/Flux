import React from 'react';
import { LinearProgress, Tooltip } from '@mui/material';
import { HoverTextType } from '../constants';
import { getColorTypeFromPercentage, normalise } from '../utils';
import classes from './ValueBasedProgressBar.module.css';

export const ValueBasedProgressBarWithHover = (props) => {


    let percentage = normalise(props.value, props.max, props.min);
    let reverse = props.collection.progressBar.is_reverse ? true : false;
    if(reverse) {
        percentage = normalise(props.max - props.value, props.max, props.min);
    }

    let color = getColorTypeFromPercentage(props.collection, percentage);

    let progressBarColorClass = classes[color];

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
            <LinearProgress variant="determinate" value={percentage} className={`${classes.progress_bar} ${progressBarColorClass}`} />
        </Tooltip>
    )
}