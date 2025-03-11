import React, { useState } from 'react';
import styles from './ModelCardContent.module.css';
import { BeatLoader } from 'react-spinners';
import { AlertErrorMessage } from '../../Alert';

const ModelCardContent = ({ children, isDisabled, error, onClear }) => {
    const [isScrollable, setIsScrollable] = useState(false);

    const handleClick = (e) => {
        e.stopPropagation();
        setIsScrollable(true);
    }

    const handleDoubleClick = (e) => {
        e.stopPropagation();
        setIsScrollable(false);
    }

    let cardContentClass = styles.card_content;
    if (!isScrollable) {
        cardContentClass += ` ${styles.no_scroll}`;
    }

    return (
        <div className={cardContentClass} onClick={handleClick} onDoubleClick={handleDoubleClick}>
            {children}
            {(isDisabled || error) && (
                <div className={styles.backdrop}>
                    {isDisabled && <BeatLoader color='yellow' />}
                    {error && <AlertErrorMessage open={error ? true : false} onClose={onClear} severity='error' error={error} />}
                </div>)}
        </div>
    )
}

export default ModelCardContent;