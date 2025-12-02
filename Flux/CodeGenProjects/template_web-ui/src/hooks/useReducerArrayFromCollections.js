import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { getReducerArrayFromCollections } from '../utils/ui/uiUtils';

/**
 * Custom hook to fetch Redux data needed for color source resolution
 *
 * This hook abstracts the pattern of:
 * 1. Determining which Redux reducers are needed based on color source properties
 * 2. Fetching those specific reducers from Redux state
 * 3. Memoizing to prevent unnecessary re-renders
 *
 * Used in conjunction with getColorFromMapping() to resolve colors based on
 * color sources (colorSrc, backgroundColorSrc, etc.)
 *
 * @param {Object|Object[]} collections - Single collection object or array of collection objects.
 *                                         Each collection may have colorSrc or backgroundColorSrc
 *                                         properties that reference other models.
 *
 * @returns {Object} reducerDict - Redux state slices keyed by reducer name.
 *                                  Format: { portfolio_limits: {...}, basket_order: {...}, ... }
 *                                  Each reducer contains stored*, modified*, and other state.
 *
 * @example
 * // In a component
 * const { collection } = props;
 * const reducerDict = useReducerArrayFromCollections(collection);
 *
 * const backgroundColor = getColorFromMapping(
 *   collection,
 *   currentValue,
 *   null,
 *   theme,
 *   null,
 *   false,
 *   reducerDict,        // ← Pass result of hook
 *   schemaCollections
 * );
 *
 * @example
 * // With multiple collections
 * const reducerDict = useReducerArrayFromCollections([collection1, collection2, collection3]);
 */
const useReducerArrayFromCollections = (collections) => {
  // Ensure collections is always an array
  const collectionsArray = useMemo(() => {
    if (!collections) return [];
    return Array.isArray(collections) ? collections : [collections];
  }, [collections]);

  // Step 1: Determine which Redux reducers we need based on color properties
  // This analyzes colorSrc and backgroundColorSrc in the collections and
  // extracts the model names they reference
  const reducerArray = useMemo(() => {
    return getReducerArrayFromCollections(collectionsArray);
  }, [collectionsArray]);

  // Step 2: Fetch those specific reducers from Redux state
  // Uses shallow reference equality check to prevent unnecessary re-renders
  // Only re-renders when reducer reference itself changes, not on every render
  const reducerDict = useSelector(
    (state) => {
      const selected = {};
      reducerArray.forEach((reducerName) => {
        selected[reducerName] = state[reducerName] || {};
      });
      return selected;
    },
    // Comparator: Use shallow reference equality check
    // Each reducer is only updated when its reference changes in Redux state
    // This is much faster than deep JSON stringification and sufficient for our use case
    // Redux ensures that unchanged reducer objects maintain reference identity
    (prev, curr) => {
      // Quick length check first
      if (Object.keys(prev).length !== Object.keys(curr).length) {
        return false;
      }
      // Shallow reference comparison - works because Redux maintains referential stability
      for (const key of Object.keys(curr)) {
        if (prev[key] !== curr[key]) {
          return false;
        }
      }
      return true;
    }
  );

  return reducerDict;
};

export default useReducerArrayFromCollections;
