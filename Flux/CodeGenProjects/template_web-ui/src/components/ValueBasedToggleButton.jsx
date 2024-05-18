import React, { useRef } from 'react';
import { ToggleButton, Tooltip } from '@mui/material';
import * as MuiIcon from '@mui/icons-material'
import PropTypes from 'prop-types';
import classes from './ValueBasedToggleButton.module.css';

const ValueBasedToggleButton = (props) => {
    let buttonClass = classes[props.color];
    const Icon = props.iconName ? MuiIcon[props.iconName] : null;

    const clickTimeout = useRef(null);

    const handleClicks = (e) => {
        if (clickTimeout.current !== null) {
            // double click event
            props.onClick(e, props.action, props.xpath, props.value, props.source, true);
            clearTimeout(clickTimeout.current);
            clickTimeout.current = null;
        } else {
            // single click event
            const timeout = setTimeout(() => {
                if (clickTimeout.current !== null) {
                    props.onClick(e, props.action, props.xpath, props.value, props.source);
                    clearTimeout(clickTimeout.current)
                    clickTimeout.current = null;
                }
            }, 300);
            clickTimeout.current = timeout;
        }
    }

    return (
        <Tooltip title={props.caption}>
            <ToggleButton
                className={`${classes.button} ${buttonClass}`}
                name={props.name}
                size={props.size}
                selected={true}
                disabled={props.disabled ? props.disabled : false}
                value={props.caption}
                onClick={handleClicks}>
                {props.iconName ? <Icon /> : props.caption}
            </ToggleButton>
        </Tooltip >
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;