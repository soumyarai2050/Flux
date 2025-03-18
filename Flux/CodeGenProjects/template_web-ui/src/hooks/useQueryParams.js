import { useEffect, useState } from "react";

function useQueryParams() {
  const [params, setParams] = useState({});

  useEffect(() => {
    // Parse query parameters from URL
    const queryParams = new URLSearchParams(window.location.search);
    const paramsObj = {};
    for (const [key, value] of queryParams.entries()) {
      paramsObj[key] = value;
    }
    setParams(paramsObj);

    // Update params whenever the URL changes
    const handlePopState = () => {
      const newQueryParams = new URLSearchParams(window.location.search);
      const newParamsObj = {};
      for (const [key, value] of newQueryParams.entries()) {
        newParamsObj[key] = value;
      }
      setParams(newParamsObj);
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  return params;
}

export default useQueryParams;