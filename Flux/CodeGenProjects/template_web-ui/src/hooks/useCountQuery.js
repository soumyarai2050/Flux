import { useState, useEffect, useCallback, useRef } from 'react';
import { createCountEndpoint, createCountWebSocketEndpoint, buildCountQueryParams } from '../utils/core/paginationUtils';
import { WebSocketManager } from '../services/WebSocketManager';

/**
 * Unified custom hook for fetching filtered count from the server
 * Supports both HTTP and WebSocket transports based on model configuration
 *
 * @param {string} apiRoot - API root URL
 * @param {string} modelName - Model name for the count query
 * @param {Array} filters - Array of processed filter objects
 * @param {boolean} enabled - Whether the query should be enabled (server-side pagination)
 * @param {boolean} hasReadByIdWsProperty - Model's ws allowed operation 
 * @returns {Object} Count query state and utilities: { count, isLoading, isSynced }
 */
function useCountQuery(apiRoot, modelName, filters = [], enabled = false, hasReadByIdWsProperty = false) {
  const [count, setCount] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetchedFilters, setLastFetchedFilters] = useState(null);
  
  // Track the current HTTP request to avoid race conditions
  const currentRequestRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Track WebSocket connection for WebSocket-based queries
  const wsManagerRef = useRef(null);

  /**
   * HTTP Transport: Fetches count via REST API
   */
  const fetchCountViaHTTP = useCallback(async (filtersToFetch) => {
    // Cancel any previous HTTP request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Create unique request identifier to handle race conditions
    const requestId = Date.now() + Math.random();
    currentRequestRef.current = requestId;

    setIsLoading(true);
    setError(null);

    try {
      const endpoint = createCountEndpoint(apiRoot, modelName);
      const queryParams = buildCountQueryParams(filtersToFetch || []);
      const url = queryParams.toString() ? `${endpoint}?${queryParams.toString()}` : endpoint;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal
      });

      // Check if this request is still the current one
      if (currentRequestRef.current !== requestId) {
        return; // Another request has been initiated, ignore this response
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      const countValue = result.filtered_count;
      setCount(countValue);
      setLastFetchedFilters(JSON.stringify(filtersToFetch));
      setError(null);

    } catch (err) {
      // Only set error if this request is still current and wasn't aborted
      if (currentRequestRef.current === requestId && !signal.aborted) {
        console.error('HTTP count query failed:', err);
        setError(err.message);
        setCount(null);
      }
    } finally {
      // Only update loading state if this request is still current
      if (currentRequestRef.current === requestId) {
        setIsLoading(false);
      }
    }
  }, [apiRoot, modelName]);

  /**
   * WebSocket Transport: Fetches count via WebSocket connection
   */
  const fetchCountViaWebSocket = useCallback((filtersToFetch) => {
    // Close any previous WebSocket connection
    if (wsManagerRef.current) {
      wsManagerRef.current.close();
      wsManagerRef.current = null;
    }

    setIsLoading(true);
    setError(null);

    // Convert HTTP URL to WebSocket URL
    const wsRoot = apiRoot.replace('http', 'ws');
    const endpoint = createCountWebSocketEndpoint(wsRoot, modelName);

    // Use the unified query parameter builder for consistency
    const queryParams = buildCountQueryParams(filtersToFetch || []);
    const url = queryParams.toString() ? `${endpoint}?${queryParams.toString()}` : endpoint;

    // Create WebSocket connection
    wsManagerRef.current = new WebSocketManager(url, {
      retryInterval: 3000,
      maxRetries: 3
    });

    // Set up message handler - receives count data
    wsManagerRef.current.setOnMessage((event) => {
      try {
        const result = JSON.parse(event.data);

        // Handle both snapshot (array) and update (object) formats
        // First message: [{"filtered_count": 31}] (snapshot)
        // Subsequent messages: {"filtered_count": 32} (updates)
        let countValue;
        if (Array.isArray(result)) {
          // Snapshot format - extract from first element
          countValue = result[0]?.filtered_count;
        } else {
          // Update format - extract directly
          countValue = result?.filtered_count;
        }

        setCount(countValue);
        setLastFetchedFilters(JSON.stringify(filtersToFetch));
        setError(null);
        setIsLoading(false);
      } catch (parseErr) {
        console.error('Failed to parse WebSocket count response:', parseErr);
        setError(parseErr.message);
        setCount(null);
        setIsLoading(false);
      }
    });

    // Set up error handler
    wsManagerRef.current.setOnError((err) => {
      console.error('WebSocket count query error:', err);
      setError('WebSocket connection error');
      setCount(null);
      setIsLoading(false);
    });

    // Set up close handler
    wsManagerRef.current.setOnClose((event) => {
      // Connection closed before receiving data
      if (!event.wasClean) {
        setError('WebSocket connection closed unexpectedly');
        setCount(null);
      }
      setIsLoading(false);
    });
  }, [apiRoot, modelName]);

  /**
   * Main fetch function - delegates to appropriate transport
   */
  const fetchCount = useCallback((filtersToFetch) => {
    // Early return if server-side pagination is not enabled
    // When disabled, no count query should run at all (neither HTTP nor WebSocket)
    if (!enabled || !apiRoot || !modelName) {
      return;
    }

    // Delegate to appropriate transport based on model configuration
    if (hasReadByIdWsProperty) {
      fetchCountViaWebSocket(filtersToFetch);
    } else {
      fetchCountViaHTTP(filtersToFetch);
    }
  }, [enabled, apiRoot, modelName, hasReadByIdWsProperty, fetchCountViaHTTP, fetchCountViaWebSocket]);

  // Effect to trigger count fetch when filters change
  useEffect(() => {
    const filtersString = JSON.stringify(filters);

    // Only fetch if filters have actually changed
    if (enabled && filtersString !== lastFetchedFilters) {
      fetchCount(filters);
    }
  }, [filters, enabled, lastFetchedFilters, fetchCount]);

  // Cleanup on unmount - handle both transport types
  useEffect(() => {
    return () => {
      // Cleanup HTTP resources
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      // Cleanup WebSocket resources
      if (wsManagerRef.current) {
        wsManagerRef.current.close();
        wsManagerRef.current = null;
      }
    };
  }, []);

  // Derive whether count is synced with current filters
  const isSynced = lastFetchedFilters === JSON.stringify(filters);

  // If not enabled, return early with default values (after all hooks have been called)
  if (!enabled) {
    return {
      count: null,
      isLoading: false,
      error: null,
      isSynced: true
    };
  }

  return {
    count,
    isLoading,
    error,
    isSynced
  };
}

export default useCountQuery;