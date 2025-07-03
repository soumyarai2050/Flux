import { useEffect, useRef } from 'react';

/**
 * @function useDebugger
 * @description A custom React hook for debugging state changes.
 * It logs changes in a provided dictionary of states by comparing current values with their previous values.
 * @param {object} statesDict - A dictionary where keys are state names and values are the corresponding state values to be tracked.
 */
const useDebugger = (statesDict) => {
    const prevStateRef = useRef(statesDict);

    useEffect(() => {
        let logStr = '';
        Object.entries(statesDict).forEach(([key, currentValue]) => {
            const prevValue = prevStateRef.current[key];

            if (!(JSON.stringify(prevValue) === JSON.stringify(currentValue))) {
                logStr += `${key} changed, prev: ${prevValue}, cur: ${currentValue}`;
            }
        })
        if (logStr.length > 0) {
            console.log('State changes detected:\n' + logStr);
        } else {
            console.log('No state changes detected.');
        }
        prevStateRef.current = JSON.parse(JSON.stringify(statesDict));
    }, [JSON.stringify(statesDict)])
}

export default useDebugger;