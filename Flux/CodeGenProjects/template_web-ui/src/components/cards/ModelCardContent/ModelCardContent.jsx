import React, { useState } from 'react';
import styles from './ModelCardContent.module.css';
import { BeatLoader } from 'react-spinners';
import { AlertErrorMessage } from '../../Alert';
import { LinkOff } from '@mui/icons-material';
import { Button } from '@mui/material';
import { useTheme } from '@emotion/react';

const ModelCardContent = ({ children, isDisabled, error, onClear, isDisconnected, onReconnect }) => {
    const [isScrollable, setIsScrollable] = useState(false);
    const theme = useTheme();

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

    const backgroundColor = theme.palette.primary.dark;
    return (
        <div className={cardContentClass} style={{ background: backgroundColor }} onClick={handleClick} onDoubleClick={handleDoubleClick}>
            {children}
            {(isDisabled || error || isDisconnected) && (
                <div className={styles.backdrop}>
                    {isDisabled && <BeatLoader color='yellow' />}
                    {isDisconnected && (
                        <>
                            <div className={styles.disconnect}>
                                <span>Websocket connection inactive...</span>
                                <LinkOff fontSize='large' color='error' />
                            </div>
                            <Button color='success' variant='contained' onClick={onReconnect}>Reconnect</Button>
                        </>

                    )}
                    {error && <AlertErrorMessage open={error ? true : false} onClose={onClear} severity='error' error={error} />}
                </div>)}
        </div>
    )
}

export default ModelCardContent;