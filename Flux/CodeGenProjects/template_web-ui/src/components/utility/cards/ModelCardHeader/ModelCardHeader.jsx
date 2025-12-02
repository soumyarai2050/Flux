import React from 'react';
import { useTheme } from '@mui/material/styles';
import IconButton from '@mui/material/IconButton';
import Close from '@mui/icons-material/Close';
import { snakeToTitle } from '../../../../utils/ui/uiUtils';
import styles from './ModelCardHeader.module.css';

const ModelCardHeader = ({
    name,
    children,
    isMaximized = false,
    onMaximizeToggle = null,
    isInPopover = false,
    onRemoveFromPopover = null
}) => {
    const theme = useTheme();

    const backgroundColor = theme.palette.primary.dark;

    // Handle double-click to toggle maximize/restore
    const handleDoubleClick = (e) => {
        // Only trigger if the double-click originated from the header itself,
        if (onMaximizeToggle && e.target === e.currentTarget) {
            onMaximizeToggle();
        }
    };

    return (
        <div
            className={styles.card_header}
            style={{ background: backgroundColor }}
            onDoubleClick={handleDoubleClick}
        >
            <div className={styles.card_title}>{snakeToTitle(name)}</div>
            <div className={styles.card_menu}>
                {children}
                {isInPopover && onRemoveFromPopover && (
                    <IconButton
                        size="small"
                        onClick={onRemoveFromPopover}
                        title="Remove from popover"
                        sx={{
                            color: '#ff4444',
                            ml: 0.5,
                            '&:hover': {
                                color: '#ff0000'
                            }
                        }}
                    >
                        <Close sx={{ fontSize: '14px' }} />
                    </IconButton>
                )}
            </div>
        </div>
    )
}

export default ModelCardHeader;