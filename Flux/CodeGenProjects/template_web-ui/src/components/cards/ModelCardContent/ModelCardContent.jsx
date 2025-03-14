import React, { useState } from 'react';
import styles from './ModelCardContent.module.css';
import { BeatLoader } from 'react-spinners';
import { AlertErrorMessage } from '../../Alert';
import { LinkOff } from '@mui/icons-material';

const ModelCardContent = ({ children, isDisabled, error, onClear, isDisconnected }) => {
    const [isScrollable, setIsScrollable] = useState(false);

    const handleClick = (e) => {
        // e.stopPropagation();
        setIsScrollable(true);
    }

    const handleDoubleClick = (e) => {
        // e.stopPropagation();
        setIsScrollable(false);
    }

    let cardContentClass = styles.card_content;
    if (!isScrollable) {
        cardContentClass += ` ${styles.no_scroll}`;
    }

    return (
        <div className={cardContentClass} onClick={handleClick} onDoubleClick={handleDoubleClick}>
            {children}
            {(isDisabled || error || isDisconnected) && (
                <div className={styles.backdrop}>
                    {isDisabled && <BeatLoader color='yellow' />}
                    {isDisconnected && (
                        <div className={styles.disconnect}>
                            <span>Websocket connection lost...</span>
                            <LinkOff fontSize='large' color='error' />
                        </div>
                    )}
                    {error && <AlertErrorMessage open={error ? true : false} onClose={onClear} severity='error' error={error} />}
                </div>)}
        </div>
    )
}

export default ModelCardContent;