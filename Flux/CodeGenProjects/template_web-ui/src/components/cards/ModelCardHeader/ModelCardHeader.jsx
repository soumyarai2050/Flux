import React from 'react';
import { useTheme } from '@emotion/react';
import styles from './ModelCardHeader.module.css';

const ModelCardHeader = ({ name, children }) => {
    const theme = useTheme();

    const backgroundColor = theme.palette.primary.dark;
    return (
        <div className={styles.card_header} style={{ background: backgroundColor }}>
            <span className={styles.card_title}>{name}</span>
            <span>{children}</span>
        </div>
    )
}

export default ModelCardHeader;