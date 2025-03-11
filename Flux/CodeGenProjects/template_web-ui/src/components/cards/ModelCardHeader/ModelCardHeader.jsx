import React from 'react';
import styles from './ModelCardHeader.module.css';

const ModelCardHeader = ({ name, children }) => {
    return (
        <div className={styles.card_header}>
            <span>{name}</span>
            <span>{children}</span>
        </div>
    )
}

export default ModelCardHeader;