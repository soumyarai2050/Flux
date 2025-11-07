import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { WEBSOCKET_CLOSE_CODES, WEBSOCKET_RETRY_CODES } from '../constants';
import { clearWebSocketConnection, setWebSocketConnection } from '../cache/websocketConnectionCache';
import { buildWebSocketQueryParams, createWebSocketPaginatedEndpoint } from '../utils/core/paginationUtils';

function useWebSocketWorker({
  url,
  modelName,
  isDisabled,
  reconnectCounter,
  isAbbreviationSource,
  selector,
  onWorkerUpdate,
  onReconnect,
  isAlertModel = false,
  crudOverrideDict = null,
  defaultFilterParamDict = null,
  params = null,
  isCppModel = false,
  // Parameters for unified endpoint with dynamic parameter inclusion
  filters = null,
  sortOrders = null,
  pagination = null,
  uiLimit = null  // Client-side limit (null when server-side pagination is enabled)
}) {
  // Get the current stored array from Redux (slice can be dynamic)
  const { storedArray } = useSelector(selector);
  const connectionRef = useRef(null);
  const storedArrayRef = useRef(storedArray);

  // New refs for snapshot logic
  const snapshotRef = useRef(null);
  const isNewlyConnectedRef = useRef(false);

  // Refs to track latest values for worker messages
  const sortOrdersRef = useRef(sortOrders);
  const uiLimitRef = useRef(uiLimit);
  const isAlertModelRef = useRef(isAlertModel);

  // Update refs directly (no useEffect needed)
  sortOrdersRef.current = sortOrders;
  uiLimitRef.current = uiLimit;
  isAlertModelRef.current = isAlertModel;

  // State to notify UI about connection status changes
  const [, setIsConnected] = useState(false);

  if (!connectionRef.current) {
    const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url), { type: 'module' });
    connectionRef.current = {
      worker,
      messageBuffer: [],
      isWorkerBusy: false,
      ws: null,
      retryCount: 0
    };
  }

  useEffect(() => {
    storedArrayRef.current = storedArray;
  }, [storedArray]);

  // Create and manage the WebSocket connection only if url exists and is not disabled
  useEffect(() => {
    if (isAbbreviationSource) return;
    if (!url || isDisabled) return;

    const wsUrl = url.replace('http', 'ws');
    let apiUrl;

    // Always use unified endpoint with dynamic parameter inclusion
    let queryParams;
    let baseEndpoint;

    // Priority 1: CRUD override (custom endpoint)
    if (crudOverrideDict?.GET_ALL) {
      // Handle CRUD override case - uses custom endpoint with query params
      const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
      if (!params && paramDict && Object.keys(paramDict).length > 0) return;

      baseEndpoint = `${wsUrl}/ws-${endpoint}`;
      queryParams = buildWebSocketQueryParams(filters || [], sortOrders || [], pagination, uiLimit, isCppModel);

      // Add custom params as query params for CRUD override
      if (params) {
        Object.keys(params).forEach(key => {
          queryParams.append(key, params[key]);
        });
      }
    }
    // Priority 2: Standard endpoint (defaultFilterParamDict or no params)
    else {
      // Use standard paginated endpoint
      // defaultFilterParamDict params are now included in filters array
      baseEndpoint = createWebSocketPaginatedEndpoint(wsUrl, modelName);
      queryParams = buildWebSocketQueryParams(filters || [], sortOrders || [], pagination, uiLimit, isCppModel);
    }

    apiUrl = queryParams.toString() ? `${baseEndpoint}?${queryParams.toString()}` : baseEndpoint;

    const connection = connectionRef.current;
    const { messageBuffer } = connection;
    const ws = new WebSocket(apiUrl);
    connection.ws = ws;
    setWebSocketConnection(modelName, ws);

    // Update state when connection opens
    ws.onopen = () => {
      // Clear previous snapshot on new connection
      snapshotRef.current = null;
      // Clear message buffer on new connection
      messageBuffer.length = 0;
      setIsConnected(true);
      isNewlyConnectedRef.current = true;
    };

    ws.onmessage = (event) => {
      if (isNewlyConnectedRef.current && !snapshotRef.current) {
        // First message after connection - save as snapshot
        snapshotRef.current = event.data;
        isNewlyConnectedRef.current = false;
      } else {
        // Subsequent messages go to buffer
        messageBuffer.push(event.data);
      }
    };

    ws.onerror = (e) => {
      console.error(`WebSocket error for ${modelName}:`, e);
    };

    ws.onclose = (e) => {
      const { code, reason, wasClean } = e;
      // Clear messageBuffer on disconnection
      connection.messageBuffer.length = 0;
      setIsConnected(false);

      if (WEBSOCKET_RETRY_CODES.includes(code)) {
        if (connection.retryCount <= 10) {
          connection.retryCount += 1;
          setTimeout(() => {
            console.info(`Reconnecting WebSocket for ${modelName}, retryCount: ${connection.retryCount}`);
            onReconnect();
          }, code === WEBSOCKET_CLOSE_CODES.TRY_AGAIN_LATER ? connection.retryCount * 10000 : 10000);
        } else {
          console.error(`WebSocket closed for ${modelName}, retryCount exhausted`);
        }
      }
      if (code !== WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE) {
        console.error(`WebSocket closed for ${modelName}, code: ${code}, reason: ${reason}, wasClean: ${wasClean}`);
      }
    };

    return () => {
      if (connectionRef.current.ws) {
        connectionRef.current.ws.close(1000, 'Normal closure on useEffect cleanup');
        connectionRef.current.ws = null;
        // Clear messageBuffer and reset connection state on cleanup
        connectionRef.current.messageBuffer.length = 0;
        snapshotRef.current = null;
        isNewlyConnectedRef.current = false;
        clearWebSocketConnection(modelName);
        // Update state to notify UI
        setIsConnected(false);
      }
    };
  }, [url, isDisabled, params, reconnectCounter, modelName, JSON.stringify(filters), JSON.stringify(sortOrders), JSON.stringify(pagination), uiLimit, isCppModel, crudOverrideDict, defaultFilterParamDict]);

  // Periodically send snapshot or accumulated messages to the worker
  useEffect(() => {
    const interval = setInterval(() => {
      const connection = connectionRef.current;
      const { messageBuffer, isWorkerBusy, worker } = connection;

      if (!isWorkerBusy) {
        // Send snapshot if available, otherwise send messageBuffer
        if (snapshotRef.current) {
          const snapshot = snapshotRef.current;
          snapshotRef.current = null;
          connection.isWorkerBusy = true;
          worker.postMessage({
            snapshot,
            storedArray: storedArrayRef.current,
            uiLimit: uiLimitRef.current,
            sortOrders: sortOrdersRef.current,
            isAlertModel: isAlertModelRef.current
          });
        } else if (messageBuffer.length > 0) {
          const messages = [...messageBuffer];
          connection.messageBuffer.length = 0;
          connection.isWorkerBusy = true;
          worker.postMessage({
            messages,
            storedArray: storedArrayRef.current,
            uiLimit: uiLimitRef.current,
            sortOrders: sortOrdersRef.current,
            isAlertModel: isAlertModelRef.current
          });
        }
      }
    }, 1000); // Check every 1 sec

    return () => clearInterval(interval);
  }, []);

  // Listen for updates from the worker and call the update callback
  useEffect(() => {
    const connection = connectionRef.current;
    const handleWorkerMessage = (event) => {
      connection.isWorkerBusy = false;
      onWorkerUpdate(event.data);
    };

    connection.worker.addEventListener('message', handleWorkerMessage);
    return () => {
      connection.worker.removeEventListener('message', handleWorkerMessage);
    };
  }, [onWorkerUpdate]);

  // Return the WebSocket from the ref.
  return connectionRef.current?.ws;
}

export default useWebSocketWorker;
