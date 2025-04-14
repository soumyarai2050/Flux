import React, { useEffect, useRef, useState, useCallback } from 'react';
import styles from './ModelCardContent.module.css';
import { BeatLoader } from 'react-spinners';
import { AlertErrorMessage } from '../../Alert';
import { LinkOff } from '@mui/icons-material';
import { Backdrop, Button, LinearProgress } from '@mui/material';
import { useTheme } from '@emotion/react';

const ModelCardContent = ({
  children,
  isDisabled,
  error,
  onClear,
  isDisconnected,
  onReconnect,
  isDownloading = false,
  progress = 0
}) => {
  const [isScrollable, setIsScrollable] = useState(false);
  const theme = useTheme();

  // TODO: commented implementation to scroll body due to lag
  // const [isBouncing, setIsBouncing] = useState(false);
  // const cardRef = useRef(null);
  // const scrollCount = useRef(0);
  // const scrollTimeout = useRef(null);
  // const isScrollScheduled = useRef(false);
  // const deltaYRef = useRef(0);

  // const updateScrollState = () => {
  //   if (!cardRef.current) return;
  //   const deltaY = deltaYRef.current;
  //   deltaYRef.current = 0;
  //   const { scrollTop, scrollHeight, clientHeight } = cardRef.current;
  //   const maxScrollTop = scrollHeight - clientHeight;

  //   // Check if at the top or near the bottom
  //   if (scrollTop === 0 || scrollTop > (maxScrollTop * 0.95)) {
  //     setIsBouncing(true);

  //     // If scrolled repeatedly, disable scroll
  //     if (scrollCount.current > 2) {
  //       // setIsScrollable(false);
  //       document.documentElement.scrollBy({
  //         top: deltaY,
  //         behavior: 'smooth',
  //       });
  //       // Reset the scroll counter after 1 second
  //       setTimeout(() => {
  //         scrollCount.current = 0;
  //       }, 1000);
  //     }

  //     // Use a timeout to aggregate scroll events
  //     if (scrollTimeout.current) clearTimeout(scrollTimeout.current);
  //     scrollTimeout.current = setTimeout(() => {
  //       scrollCount.current += 1;
  //     }, 250);
  //   } else {
  //     setIsBouncing(false);
  //   }
  //   isScrollScheduled.current = false;
  // };

  // const handleScroll = useCallback((event) => {
  //   // Use requestAnimationFrame to throttle scroll event work
  //   deltaYRef.current += event.deltaY;
  //   if (!isScrollScheduled.current) {
  //     isScrollScheduled.current = true;
  //     window.requestAnimationFrame(updateScrollState);
  //   }
  // }, []);

  // useEffect(() => {
  //   const card = cardRef.current;
  //   if (!card) return;

  //   // Attach the scroll event with passive option for better performance
  //   card.addEventListener('wheel', handleScroll, { passive: true });

  //   return () => {
  //     card.removeEventListener('wheel', handleScroll);
  //     if (scrollTimeout.current) clearTimeout(scrollTimeout.current);
  //   };
  // }, [handleScroll]);

  const handleClick = useCallback(() => {
    setIsScrollable(true);
  }, []);

  const handleDoubleClick = useCallback(() => {
    setIsScrollable(false);
  }, []);

  let cardContentClass = styles.card_content;
  if (!isScrollable) {
    cardContentClass += ` ${styles.no_scroll}`;
  }
  // if (isBouncing) {
  //   cardContentClass += ` ${styles.bounce}`;
  // }

  const backgroundColor = theme.palette.primary.dark;
  const isBackdropOpen = Boolean(isDisabled || error || isDisconnected);

  let backdropClass = styles.backdrop;
  if (isDisabled) {
    backdropClass += ` ${styles.enable_menu}`;
  }

  return (
    <div className={styles.card_content_container}>
      <div
        className={`${cardContentClass} card-content`}
        style={{ background: backgroundColor }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        // ref={cardRef}
      >
        {isDownloading && (
          <LinearProgress
            variant={progress === 0 ? 'indeterminate' : 'determinate'}
            color={progress === 0 ? 'inherit' : 'success'}
            value={progress}
          />
        )}
        <Backdrop className={backdropClass} open={isBackdropOpen}>
          {isDisabled && <BeatLoader color='yellow' />}
          {isDisconnected && (
            <>
              <div className={styles.disconnect}>
                <span>Websocket connection inactive...</span>
                <LinkOff fontSize='large' color='error' />
              </div>
              <Button color='success' variant='contained' onClick={onReconnect}>
                Reconnect
              </Button>
            </>
          )}
          {error && (
            <AlertErrorMessage
              open={Boolean(error)}
              onClose={onClear}
              severity='error'
              error={error}
            />
          )}
        </Backdrop>
        {children}
      </div>
    </div>
  );
};

export default ModelCardContent;