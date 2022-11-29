import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import PropTypes from 'prop-types';

const Icon = (props) => {
    return (
        <IconButton size='small' disabled={props.disabled} className={props.className} onClick={props.onClick}>
            <Tooltip title={props.title}>
                {props.children}
            </Tooltip>
        </IconButton>
    )
}

Icon.propTypes = {
    className: PropTypes.string,
    onClick: PropTypes.func,
    children: PropTypes.any.isRequired
}

export default Icon;