import React from 'react';
import { ToggleButton, Tooltip } from '@mui/material';
import * as MuiIcon from '@mui/icons-material'
import PropTypes from 'prop-types';
import classes from './ValueBasedToggleButton.module.css';

const ValueBasedToggleButton = (props) => {
    let buttonClass = classes[props.color];
    const Icon = props.iconName ? MuiIcon[props.iconName] : null;

    return (
        <Tooltip title={props.caption}>
            <ToggleButton
                className={`${classes.button} ${buttonClass}`}
                name={props.name}
                size={props.size}
                selected={true}
                disabled={props.disabled ? props.disabled : false}
                value={props.caption}
                onClick={(e) => props.onClick(e, props.action, props.xpath, props.value, props.source)}>
                {props.iconName ? <Icon /> : props.caption}
            </ToggleButton>
        </Tooltip >
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;