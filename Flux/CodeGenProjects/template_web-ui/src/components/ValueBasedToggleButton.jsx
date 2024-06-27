import React, { useRef } from 'react';
import { ToggleButton, Tooltip } from '@mui/material';
import * as MuiIcon from '@mui/icons-material'
import PropTypes from 'prop-types';
import classes from './ValueBasedToggleButton.module.css';

const ButtonWrapper = ({ condition, wrapper, children }) => {
    return condition ? wrapper(children) : children;
}

const ValueBasedToggleButton = (props) => {
    let buttonClass = classes[props.color];
    const Icon = props.iconName ? MuiIcon[props.iconName] : null;
    let disabledClass = '';
    if (props.disabled) {
        disabledClass = classes.disabled;
    }

    const clickTimeout = useRef(null);

    const handleClicks = (e) => {
        if (props.allowForceUpdate) {
            if (clickTimeout.current !== null) {
                // double click event
                props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source, true);
                clearTimeout(clickTimeout.current);
                clickTimeout.current = null;
            } else {
                // single click event
                const timeout = setTimeout(() => {
                    if (clickTimeout.current !== null) {
                        props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source);
                        clearTimeout(clickTimeout.current)
                        clickTimeout.current = null;
                    }
                }, 300);
                clickTimeout.current = timeout;
            }
        } else {
            props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source);
        }
    }

    return (
        <ButtonWrapper
            condition={!!props.disabled}
            wrapper={children => <Tooltip className={disabledClass} title={props.caption}>{children}</Tooltip>}>
            <ToggleButton
                className={`${classes.button} ${buttonClass} ${disabledClass}`}
                name={props.name}
                size={props.size}
                selected={true}
                disabled={props.disabled ? props.disabled : false}
                value={props.caption}
                onClick={handleClicks}>
                {props.iconName ? <Icon /> : props.caption}
            </ToggleButton>
        </ButtonWrapper>
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;