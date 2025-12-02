import { useMemo } from 'react';

/**
 * Custom hook to mark columns and collections with shownByToggle flag based on visibility states
 * Returns marked versions of headCells, sortedCells, and commonKeys in one call
 *
 * @param {Array} headCells - Array of header cells to mark
 * @param {Array} sortedCells - Array of sorted cells to mark
 * @param {Array} commonKeys - Array of common key collections to mark
 * @param {boolean} showHidden - Whether to show hidden columns
 * @param {boolean} showMore - Whether to show "more" (less frequent) columns
 * @param {boolean} showAll - Whether to show all hidden columns
 * @param {boolean} moreAll - Whether to show all "more" columns
 * @returns {Object} Object with markedHeadCells, markedSortedCells, markedCommonKeys
 */
export const useMarkedColumns = (headCells, sortedCells, commonKeys, showHidden, showMore, showAll, moreAll) => {
    return useMemo(() => {
        const markItems = (items) => {
            if (!items || !Array.isArray(items)) {
                return items;
            }

            return items.map(item => {
                const wasHiddenByDefault = item.hide === true;
                const wasLessByDefault = item.showLess === true;

                const isShownViaHiddenToggle = wasHiddenByDefault && (showHidden || showAll);
                const isShownViaLessToggle = wasLessByDefault && (showMore || moreAll);

                const props = {};
                if (isShownViaHiddenToggle) {
                    props.shownByDoubleClick = true;
                }

                if (isShownViaLessToggle) {
                    props.shownByToggle = true;
                }

                if (Object.keys(props).length > 0) {
                    return {
                        ...item,
                        ...props
                    };
                }
                return item;
            });
        };

        return {
            markedHeadCells: markItems(headCells),
            markedSortedCells: markItems(sortedCells),
            markedCommonKeys: markItems(commonKeys)
        };
    }, [headCells, sortedCells, commonKeys, showHidden, showMore, showAll, moreAll]);
};
