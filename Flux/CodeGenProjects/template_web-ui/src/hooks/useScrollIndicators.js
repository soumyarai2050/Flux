import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Custom hook for managing horizontal scroll indicators in table containers
 * @param {Array} dependencies - Dependencies that trigger scroll checking when changed
 * @returns {Object} Hook return object with states, handlers, and ref
 */
const useScrollIndicators = (dependencies = []) => {
  // Horizontal scroll state
  const [showRightScrollIndicator, setShowRightScrollIndicator] = useState(false);
  const [showLeftScrollIndicator, setShowLeftScrollIndicator] = useState(false);
  const [indicatorRightOffset, setIndicatorRightOffset] = useState(16);
  const tableContainerRef = useRef(null);

  // Check for horizontal scrollbar
  const checkHorizontalScroll = useCallback(() => {
    if (tableContainerRef.current) {
      const { scrollWidth, clientWidth, scrollLeft, scrollHeight, clientHeight } = tableContainerRef.current;
      const hasHorizontalScroll = scrollWidth > clientWidth;
      const isAtEnd = scrollLeft + clientWidth >= scrollWidth - 1; // Account for floating point precision
      const isAtStart = scrollLeft <= 1; // Account for floating point precision
      const hasVerticalScroll = scrollHeight > clientHeight;

      // Adjust indicator position if there's a vertical scrollbar
      const rightOffset = hasVerticalScroll ? 32 : 16; // Account for vertical scrollbar width
      setIndicatorRightOffset(rightOffset);

      // Show right indicator when not at end and has horizontal scroll
      setShowRightScrollIndicator(hasHorizontalScroll && !isAtEnd);

      // Show left indicator when not at start and has horizontal scroll
      setShowLeftScrollIndicator(hasHorizontalScroll && !isAtStart);
    }
  }, []);

  // Handle horizontal scroll click - right direction
  const handleRightScrollClick = useCallback(() => {
    if (tableContainerRef.current) {
      const { clientWidth, scrollLeft, scrollWidth } = tableContainerRef.current;
      const scrollAmount = Math.min(300, clientWidth * 0.8); // Scroll by 300px or 80% of visible width, whichever is smaller
      const maxScrollLeft = scrollWidth - clientWidth;
      const newScrollLeft = Math.min(scrollLeft + scrollAmount, maxScrollLeft);

      tableContainerRef.current.scrollTo({
        left: newScrollLeft,
        behavior: 'smooth'
      });
    }
  }, []);

  // Handle horizontal scroll click - left direction
  const handleLeftScrollClick = useCallback(() => {
    if (tableContainerRef.current) {
      const { clientWidth, scrollLeft } = tableContainerRef.current;
      const scrollAmount = Math.min(300, clientWidth * 0.8); // Scroll by 300px or 80% of visible width, whichever is smaller
      const newScrollLeft = Math.max(scrollLeft - scrollAmount, 0);

      tableContainerRef.current.scrollTo({
        left: newScrollLeft,
        behavior: 'smooth'
      });
    }
  }, []);

  // Check scroll on mount and when dependencies change
  useEffect(() => {
    checkHorizontalScroll();
    // Add resize observer to check when table size changes
    const resizeObserver = new ResizeObserver(checkHorizontalScroll);
    if (tableContainerRef.current) {
      resizeObserver.observe(tableContainerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, [checkHorizontalScroll, ...dependencies]);

  return {
    // State
    showRightScrollIndicator,
    showLeftScrollIndicator,
    indicatorRightOffset,

    // Ref
    tableContainerRef,

    // Handlers
    handleRightScrollClick,
    handleLeftScrollClick,
    checkHorizontalScroll,
  };
};

export default useScrollIndicators; 