import React from 'react';
import styles from './ModelCard.module.css';

const ModelCard = ({ children }) => {

    return (
        <div aria-label='model-card' className={styles.card}>
            {children}
        </div>
    )
}

export default ModelCard;