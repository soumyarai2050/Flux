import { useState, useEffect, useRef } from 'react';

function useBoundaryScrollDetection(options = {}) {
  const {
    timeWindow = 2000, // Time window to count boundary hits (1 second)
    hitThreshold = 5, // Number of boundary hits to trigger disabling
    bottomThreshold = 10, // Pixels threshold for bottom detection
    gestureTimeout = 500, // Time to consider wheel events as part of the same gesture
  } = options;

  const containerRef = useRef(null);
  const [isScrollable, setIsScrollable] = useState(false);
  const boundaryHitsRef = useRef([]);
  const lastGestureTimeRef = useRef(0);
  const gestureInProgressRef = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Timer for detecting end of a scroll gesture
    let gestureTimer = null;

    const handleWheel = (e) => {
      if (isScrollable) {
        // e.preventDefault();
        return;
      }

      if (gestureInProgressRef.current) {
        e.preventDefault();
        return;
      }

      const { scrollTop, scrollHeight, clientHeight } = container;

      // Precise boundary detection
      const isAtTop = scrollTop <= 0;
      const distanceFroBottom = scrollHeight - scrollTop - clientHeight;
      const isAtBottom = distanceFroBottom <= bottomThreshold;

      // Check if we're at boundary AND trying to scroll beyond it
      const isAttemptingPastBoundary =
        (isAtTop && e.deltaY < 0) ||
        (isAtBottom && e.deltaY > 0);

      if (isAttemptingPastBoundary) {
        const now = Date.now();

        // Only register this as a new boundary hit if not already in a gesture
        if (!gestureInProgressRef.current) {
          console.log(`New boundary hit at ${isAtTop ? 'top' : 'bottom'}`);
        }

        // Mark that we're in an active gesture
        gestureInProgressRef.current = true;
        lastGestureTimeRef.current = now;

        // Add this gesture as a boundary hit
        boundaryHitsRef.current.push(now);

        // Filter to keep only hits within time window
        boundaryHitsRef.current = boundaryHitsRef.current.filter(
          time => now - time < timeWindow
        );

        // If hit threshold reached, disable scrolling
        if (boundaryHitsRef.current.length >= hitThreshold) {
          console.log(`Disabling scroll after ${boundaryHitsRef.current.length} boundary hits`);
          setIsScrollable(false);
          e.preventDefault();
        }
      }

      // Reset timer that tracks the end of a scroll gesture
      clearTimeout(gestureTimer);
      gestureTimer = setTimeout(() => {
        gestureInProgressRef.current = false;
        console.log('Scroll gesture ended');
      }, gestureTimeout);

      // Always prevent default when at boundary
      e.preventDefault();
    };

    // Add wheel event listener
    container.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      container.removeEventListener('wheel', handleWheel);
      if (gestureTimer) clearTimeout(gestureTimer);
    };
  }, [timeWindow, hitThreshold, isScrollable, bottomThreshold, gestureTimeout]);

  const enableScrolling = () => {
    boundaryHitsRef.current = [];
    gestureInProgressRef.current = false;
    setIsScrollable(true);
  };

  // Provide a function to disable scrolling when needed
  const disableScrolling = () => {
    boundaryHitsRef.current = [];
    gestureInProgressRef.current = false;
    setIsScrollable(false);
  };

  return {
    containerRef,
    isScrollable,
    enableScrolling,
    disableScrolling,
  };
}

export default useBoundaryScrollDetection;