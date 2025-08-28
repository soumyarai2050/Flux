import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ClickAwayListener, Tooltip } from '@mui/material';
import classes from './LinkText.module.css';

const LinkText = (props) => {
    // Add maxLength, keep linkText as optional
    const { text, linkText, maxLength = 25 } = props;
    
    const [open, setOpen] = useState(false);

    // Determine if the text is longer than the max length
    const isLongText = text && text.length > maxLength;

    // Decide what content to show in the tooltip.
    // Use linkText if it's provided, otherwise fall back to the full original text.
    const tooltipContent = linkText || text;

    const onClose = () => {
        setOpen(false);
    };

    const onOpen = () => {
        setOpen(true);
    };

    // If the text is NOT long, return a simple span with no special behavior.
    if (!isLongText) {
        return <span>{text}</span>;
    }

    // If the text IS long, return the component with the tooltip and link styling.
    return (
        <ClickAwayListener onClickAway={onClose}>
            <div className={classes.link} onClick={onOpen}>
                <Tooltip
                    // Use the determined tooltip content
                    title={tooltipContent}
                    placement="bottom-start"
                    open={open}
                    onClose={onClose}
                    disableFocusListener
                    disableHoverListener
                    disableTouchListener>
                    {/* The displayed text is always the 'text' prop, which CSS will truncate */}
                    <span>{text}</span>
                </Tooltip >
            </div>
        </ClickAwayListener>
    );
};

LinkText.propTypes = {
    /** The text to display. It will be truncated if it exceeds maxLength. */
    text: PropTypes.string.isRequired,
    /** Optional: The text to show in the tooltip. If not provided, the full 'text' prop is used. */
    linkText: PropTypes.string,
    /** The character count threshold to determine if the text is "long". */
    maxLength: PropTypes.number,
};

export default LinkText;