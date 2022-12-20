import React from 'react';
import { makeStyles } from '@mui/styles';
import { ToggleButton } from '@mui/material';
import PropTypes from 'prop-types';
import { ColorTypes } from '../constants';

const useStyles = makeStyles({
    button: {
        margin: '0px 10px !important',
        padding: '5px 10px !important'
    },
    buttonSuccess: {
        color: 'white !important',
        background: 'green !important'
    },
    buttonCritical: {
        color: 'white !important',
        background: '#9C0006 !important',
        animation: `$blink 0.5s step-start infinite`
    },
    buttonError: {
        color: 'white !important',
        background: '#9C0006 !important'
    },
    buttonWarning: {
        color: 'white !important',
        background: '#99942c !important'
    },
    buttonInfo: {
        color: 'white !important',
        background: 'blue !important'
    },
    buttonDebug: {
        color: 'white !important',
        background: '#777 !important'
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

const ValueBasedToggleButton = (props) => {

    const classes = useStyles();

    let buttonClass = '';
    if (props.color === ColorTypes.CRITICAL) buttonClass = classes.buttonCritical;
    else if (props.color === ColorTypes.ERROR) buttonClass = classes.buttonError;
    else if (props.color === ColorTypes.WARNING) buttonClass = classes.buttonWarning;
    else if (props.color === ColorTypes.INFO) buttonClass = classes.buttonInfo;
    else if (props.color === ColorTypes.DEBUG) buttonClass = classes.buttonDebug;
    else if (props.color === ColorTypes.SUCCESS) buttonClass = classes.buttonSuccess;

    return (
        <ToggleButton
            className={`${classes.button} ${buttonClass}`}
            size={props.size}
            selected={true}
            value={props.caption}
            onClick={(e) => props.onClick(e, props.action, props.xpath, props.value)}>
            {props.caption}
        </ToggleButton>
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;