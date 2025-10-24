import React from 'react';
import { useTheme } from '@mui/material/styles';
import { snakeToTitle } from '../../../../utils/ui/uiUtils';
import styles from './ModelCardHeader.module.css';

const ModelCardHeader = ({ 
    name, 
    children, 
    isMaximized = false, 
    onMaximizeToggle = null 
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
            <div className={styles.card_menu}>{children}</div>
        </div>
    )
}

export default ModelCardHeader;