import { useEffect, useState } from "react";

/**
 * @function useURLParams
 * @description A custom React hook that parses and provides access to URL query parameters.
 * It updates the parameters whenever the URL changes (e.g., via browser navigation).
 * @returns {object} An object containing the current URL query parameters as key-value pairs.
 */
function useURLParams() {
  const [params, setParams] = useState({});

  useEffect(() => {
    // Parse query parameters from URL on initial load
    const queryParams = new URLSearchParams(window.location.search);
    const paramsObj = {};
    for (const [key, value] of queryParams.entries()) {
      paramsObj[key] = value;
    }
    setParams(paramsObj);

    // Update params whenever the URL changes (e.g., back/forward button clicks)
    const handlePopState = () => {
      const newQueryParams = new URLSearchParams(window.location.search);
      const newParamsObj = {};
      for (const [key, value] of newQueryParams.entries()) {
        newParamsObj[key] = value;
      }
      setParams(newParamsObj);
    };

    window.addEventListener('popstate', handlePopState);

    // Cleanup: remove the event listener when the component unmounts
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []); // Empty dependency array ensures this effect runs only once on mount

  return params;
}

export default useURLParams;