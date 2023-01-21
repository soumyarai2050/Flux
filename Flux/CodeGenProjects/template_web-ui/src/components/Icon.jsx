import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';

const Icon = (props) => {
    return (
        <Tooltip title={props.title}>
            <IconButton size='small' name={props.name} disabled={props.disabled} className={props.className} onClick={props.onClick}>
                {props.children}
            </IconButton>
        </Tooltip>
    )
}

Icon.propTypes = {
    className: PropTypes.string,
    onClick: PropTypes.func,
    children: PropTypes.any.isRequired
}

export default Icon;