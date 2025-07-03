import { useEffect, useRef } from "react";

/**
 * @function usePrevious
 * @description A custom React hook that returns the previous value of a given value (prop or state).
 * @param {any} value - The current value whose previous state is to be tracked.
 * @returns {any} The previous value of the input `value`.
 */
const usePrevious = (value) => {
    const ref = useRef();

    useEffect(() => {
        ref.current = value;
    }, [value]);

    return ref.current;
};

export default usePrevious;