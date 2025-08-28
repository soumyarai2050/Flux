import React from 'react';
import styles from './ModelCard.module.css';
// import { useScrollableContext } from '../../../contexts/ScrollableContext';
// import { useClickHandler } from '../../../hooks';

const ModelCard = ({ children, id }) => {
    // const { setScrollableName } = useScrollableContext();

    // const handleSingleClick = () => {
    //     setScrollableName(id);
    // }

    // const handleDoubleClick = () => {
    //     setScrollableName(null);
    // }

    // const { onClick, onDoubleClick } = useClickHandler(
    //     handleSingleClick,
    //     handleDoubleClick
    // );

    return (
        <div
            aria-label='model-card'
            className={styles.card}
            // onClick={onClick}
            // onDoubleClick={onDoubleClick}
        >
            {children}
        </div>
    )
}

export default ModelCard;