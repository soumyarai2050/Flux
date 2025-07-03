import { useCallback, useRef } from 'react';

const DEFAULT_CLICK_DELAY = 300; // milliseconds

/**
 * @function useClickHandler
 * @description A custom React hook that provides handlers to distinguish between single and double clicks.
 * It executes a `onSingleClick` callback for single clicks and `onDoubleClick` for double clicks within a specified delay.
 * @param {function} [onSingleClick] - Callback function to execute on a single click.
 * @param {function} [onDoubleClick] - Callback function to execute on a double click.
 * @param {number} [delay=DEFAULT_CLICK_DELAY] - The maximum time (in milliseconds) between two clicks to be considered a double click.
 * @returns {object} An object containing click handlers and a cleanup function.
 * @property {function(Event): void} onClick - The click handler to attach to a DOM element.
 * @property {function(Event): void} onDoubleClick - The double-click handler to attach to a DOM element.
 * @property {function(): void} cleanup - A function to clear any pending click timeouts, useful on component unmount.
 */
function useClickHandler(onSingleClick, onDoubleClick, delay = DEFAULT_CLICK_DELAY) {
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