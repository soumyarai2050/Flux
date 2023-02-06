import React from 'react';
import { ToggleButton } from '@mui/material';
import PropTypes from 'prop-types';
import classes from './ValueBasedToggleButton.module.css';

const ValueBasedToggleButton = (props) => {

    let buttonClass = classes[props.color];

    return (
        <ToggleButton
            className={`${classes.button} ${buttonClass}`}
            name={props.name}
            size={props.size}
            selected={true}
            disabled={props.disabled ? props.disabled : false}
            value={props.caption}
            onClick={(e) => props.onClick(e, props.action, props.xpath, props.value)}>
            {props.caption}
        </ToggleButton>
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;