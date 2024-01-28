import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ClickAwayListener, Tooltip } from '@mui/material';
import classes from './LinkText.module.css';

const LinkText = (props) => {
    const { text, linkText } = props;
    const [open, setOpen] = useState(false);

    const onClose = () => {
        setOpen(false);
    }

    const onOpen = () => {
        setOpen(true);
    }

    return (
        <ClickAwayListener onClickAway={onClose}>
            <div className={classes.link} onClick={onOpen}>
                <Tooltip
                    title={linkText}
                    placement="bottom-start"
                    open={open}
                    onClose={onClose}
                    disableFocusListener
                    disableHoverListener
                    disableTouchListener>
                    <span>{text}</span>
                </Tooltip >
            </div>
        </ClickAwayListener>
    )
}

LinkText.propTypes = {
    text: PropTypes.string,
    linkText: PropTypes.string,
}

export default LinkText;