import React from 'react';
import { useTheme } from '@emotion/react';
import { snakeToTitle } from '../../../utils/ui/uiUtils';
import styles from './ModelCardHeader.module.css';

const ModelCardHeader = ({ name, children }) => {
    const theme = useTheme();

    const backgroundColor = theme.palette.primary.dark;
    return (
        <div className={styles.card_header} style={{ background: backgroundColor }}>
            <div className={styles.card_title}>{snakeToTitle(name)}</div>
            <div className={styles.card_menu}>{children}</div>
        </div>
    )
}

export default ModelCardHeader;