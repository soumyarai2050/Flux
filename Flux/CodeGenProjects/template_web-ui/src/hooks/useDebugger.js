import { useEffect, useRef } from 'react';

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
            console.log(logStr);
        } else {
            console.log('no change detected');
        }
        prevStateRef.current = JSON.parse(JSON.stringify(statesDict));
    }, [JSON.stringify(statesDict)])
}

export default useDebugger;