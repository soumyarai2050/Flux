import { useRef, useEffect, useCallback } from 'react';

const DEFAULT_CLICK_DELAY = 350;

/**
 * @name useClickIntent
 * @description A custom React hook that distinguishes between single and double clicks. 
 * It forwards all arguments from the trigger to the appropriate callback.
 * @param {function} onSingleClick - Callback for single click. Receives all arguments passed to the handler.
 * @param {function} onDoubleClick - Callback for double click. Receives all arguments passed to the handler.
 * @param {number} [delay=DEFAULT_CLICK_DELAY] - The delay in ms to wait for a second click.
 * @returns {function(...args): void} A single, memoized event handler to attach to your component.
 */
export default function useClickIntent(onSingleClick, onDoubleClick, delay = DEFAULT_CLICK_DELAY) {
  const timerRef = useRef(null);
  const clickCountRef = useRef(0);
  // This ref will store the arguments from the latest invocation.
  const argsRef = useRef([]);

  // Auto-cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handler = useCallback((...args) => {
    // Store the latest arguments
    argsRef.current = args;
    clickCountRef.current += 1;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      if (clickCountRef.current === 1) {
        // Forward all stored arguments to the single click handler
        onSingleClick?.(...argsRef.current);
      } else if (clickCountRef.current >= 2) {
        // Forward all stored arguments to the double click handler
        onDoubleClick?.(...argsRef.current);
      }
      // Reset after the logic has run
      clickCountRef.current = 0;
    }, delay);
  }, [onSingleClick, onDoubleClick, delay]);

  return handler;
}