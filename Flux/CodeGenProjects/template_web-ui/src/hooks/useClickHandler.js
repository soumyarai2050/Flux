import { useCallback, useRef } from 'react';

function useClickHandler(onSingleClick, onDoubleClick, delay = 300) {
  const clickTimeoutRef = useRef(null);

  const handleClick = useCallback((event) => {
    clearTimeout(clickTimeoutRef.current);
    clickTimeoutRef.current = setTimeout(() => {
      onSingleClick?.(event);
    }, delay);
  }, [onSingleClick, delay]);

  const handleDoubleClick = useCallback((event) => {
    clearTimeout(clickTimeoutRef.current);
    onDoubleClick?.(event);
  }, [onDoubleClick]);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (clickTimeoutRef.current) {
      clearTimeout(clickTimeoutRef.current);
    }
  }, []);

  return {
    onClick: handleClick,
    onDoubleClick: handleDoubleClick,
    cleanup
  };
}

export default useClickHandler;