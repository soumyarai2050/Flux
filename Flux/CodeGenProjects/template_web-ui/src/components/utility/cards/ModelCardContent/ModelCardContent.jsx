import React from 'react';
import styles from './ModelCardContent.module.css';
import { BeatLoader } from 'react-spinners';
import { AlertErrorMessage } from '../../../ui/Alert';
import { LinkOff } from '@mui/icons-material';
import { Backdrop, Button, LinearProgress } from '@mui/material';
import { useTheme } from '@emotion/react';
// import { useBoundaryScrollDetection } from '../../../hooks';

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
  // const { containerRef, isScrollable, enableScrolling, disableScrolling } = useBoundaryScrollDetection();
  const theme = useTheme();

  const handleClick = () => {
    // enableScrolling();
  };

  const handleDoubleClick = () => {
    // disableScrolling();
  };

  let cardContentClass = styles.card_content;
  // if (!isScrollable) {
  //   cardContentClass += ` ${styles.no_scroll}`;
  // }
  // if (isBouncing) {
  //   cardContentClass += ` ${styles.bounce}`;
  // }

  // const backgroundColor = 'var(--grey-light)';
  const isBackdropOpen = Boolean(isDisabled || error || isDisconnected);

  let backdropClass = styles.backdrop;
  if (isDisabled) {
    backdropClass += ` ${styles.enable_menu}`;
  }

  return (
    <div className={styles.card_content_container}>
      <div
        className={`${cardContentClass} card-content`}
        style={{ background: theme.palette.background.primary }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        // ref={containerRef}
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