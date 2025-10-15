import React from 'react';
import KeyboardArrowRight from '@mui/icons-material/KeyboardArrowRight';
import KeyboardArrowLeft from '@mui/icons-material/KeyboardArrowLeft';
import styles from './ScrollIndicators.module.css';

const ScrollIndicators = ({
  showRightScrollIndicator = false,
  showLeftScrollIndicator = false,
  indicatorRightOffset = 16,
  onRightScrollClick,
  onLeftScrollClick,
  className = ''
}) => {
  return (
    <>
      {showRightScrollIndicator && (
        <div
          className={`${styles.rightScrollIndicator} ${className}`}
          style={{ right: `${indicatorRightOffset}px` }}
          onClick={onRightScrollClick}
          title="Click to scroll right"
        >
          <KeyboardArrowRight />
        </div>
      )}

      {showLeftScrollIndicator && (
        <div
          className={`${styles.leftScrollIndicator} ${className}`}
          onClick={onLeftScrollClick}
          title="Click to scroll left"
        >
          <KeyboardArrowLeft />
        </div>
      )}
    </>
  );
};

export default ScrollIndicators;