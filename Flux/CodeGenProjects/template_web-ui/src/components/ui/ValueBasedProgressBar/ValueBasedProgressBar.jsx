import React from 'react';
import { useSelector } from 'react-redux';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import { useTheme } from '@mui/material/styles';
import { HOVER_TEXT_TYPES } from '../../../constants';
import { getColorFromMapping } from '../../../utils/ui/colorUtils';
import { normalise } from '../../../utils/formatters/numberUtils';
import classes from './ValueBasedProgressBar.module.css';

export const ValueBasedProgressBarWithHover = (props) => {
    const theme = useTheme();
    const { schemaCollections } = useSelector(state => state.schema);

    // Determine the mode: 'standard' (default) or 'deviation'
    const mode = props.collection?.progressBar?.mode || 'standard';
    const isDeviationMode = mode === 'deviation';

    // === STANDARD MODE LOGIC ===
    let percentage = normalise(props.value, props.max, props.min);
    let reverse = props.collection.progressBar.is_reverse ? true : false;
    if (reverse) {
        percentage = normalise(props.max - props.value, props.max, props.min);
    }

    // === DEVIATION MODE LOGIC ===
    let deviationPercentage = null;
    let deviationValue = null;
    let target = props.collection.progressBar.target;
    if (isDeviationMode && target !== undefined) {
        // Calculate deviation: positive when value > target, negative when value < target
        deviationValue = props.value - target;
        // Simple percentage deviation from target
        // Formula: (value - target) / target * 100
        // This gives signed percentage: +50% if value is 50% above target, -50% if 50% below
        if (target !== 0) {
            deviationPercentage = (deviationValue / Math.abs(target)) * 100;
        } else {
            // If target is 0, use absolute value as denominator to avoid division by zero
            deviationPercentage = (deviationValue / (Math.abs(props.value) || 1)) * 100;
        }
        // Cap deviation percentage to -100 to +100 for bar display
        deviationPercentage = Math.max(-100, Math.min(100, deviationPercentage));
    }

    // Determine which percentage to use for color mapping
    const colorMappingPercentage = isDeviationMode ? deviationPercentage : percentage;
    const colorMappingValue = isDeviationMode ? deviationValue : props.value;

    // Support color_src for progress bars
    let color = getColorFromMapping(props.collection.progressBar, colorMappingValue, colorMappingPercentage, theme, null, false, props.data, schemaCollections);
    color = color ? color.toLowerCase() : null;

    // Map resolved CSS color to class if available, otherwise use inline style
    let progressBarColorClass = color && classes[color] ? classes[color] : '';
    let inlineStyle = color && classes[color] ? {} : (color ? { backgroundColor: color } : {});

    let maxFieldName = '';
    if (props.maxFieldName) {
        maxFieldName = props.maxFieldName + ': ';
    }

    let hoverText = '';
    if (props.hoverType === HOVER_TEXT_TYPES.VALUE) {
        hoverText = `${props.valueFieldName}: ${props.value ? props.value.toLocaleString() : ''}/${maxFieldName}${props.max ? props.max.toLocaleString() : ''}`;
    } else if (props.hoverType === HOVER_TEXT_TYPES.PERCENTAGE) {
        if (isDeviationMode && deviationPercentage !== null) {
            hoverText = `${deviationPercentage.toFixed(1)}%`;
        } else {
            hoverText = props.percentage + ' %';
        }
    } else if (props.hoverType === HOVER_TEXT_TYPES.VALUE_AND_PERCENTAGE) {
        hoverText = `${props.valueFieldName}: ${props.value ? props.value.toLocaleString() : ''}/${maxFieldName}${props.max ? props.max.toLocaleString() : ''}`;
        if (isDeviationMode && deviationPercentage !== null) {
            hoverText += `|${deviationPercentage.toFixed(1)}%`;
        } else {
            hoverText += `|${props.percentage} %`;
        }
    }

    let progressBarClass = classes.progress_bar;
    if (props.inlineTable) {
        progressBarClass = classes.progress_bar_cell;
    }

    // === RENDER DEVIATION MODE ===
    if (isDeviationMode && deviationPercentage !== null) {
        // Bar positioning: center = 50%, expand left (negative) or right (positive)
        const barWidth = Math.abs(deviationPercentage) / 2; // Max 50% on each side
        const barLeft = deviationPercentage < 0 ? (50 - barWidth) : 50;

        let deviationBarClass = classes.deviation_bar;
        if (props.inlineTable) {
            deviationBarClass = `${deviationBarClass} ${classes.deviation_bar_cell}`;
        }

        return (
            <Tooltip title={hoverText} disableInteractive>
                <div className={`${progressBarClass} ${classes.deviation_bar_track}`}>
                    <div
                        className={`${deviationBarClass} ${progressBarColorClass}`}
                        style={{
                            left: `${barLeft}%`,
                            width: `${barWidth}%`,
                            backgroundColor: inlineStyle.backgroundColor || undefined,
                            ...inlineStyle
                        }}
                    />
                </div>
            </Tooltip>
        );
    }

    // === RENDER STANDARD MODE ===
    return (
        <Tooltip title={hoverText} disableInteractive>
            <LinearProgress
                variant="determinate"
                color='secondary'
                value={percentage}
                className={`${progressBarClass} ${progressBarColorClass}`}
                sx={inlineStyle ? { '& .MuiLinearProgress-bar': { backgroundColor: color } } : {}}
            />
        </Tooltip>
    )
}