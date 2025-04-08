import { useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { WEBSOCKET_CLOSE_CODES, WEBSOCKET_RETRY_CODES } from '../constants';
import { clearWebSocketConnection, setWebSocketConnection } from '../cache/websocketConnectionCache';

function useWebSocketWorker({
  url,
  modelName,
  isDisabled,
  reconnectCounter,
  isAbbreviationSource,
  selector,
  onWorkerUpdate,
  onReconnect,
  uiLimit = null,
  isAlertModel = false,
  crudOverrideDict = null,
  params = null
}) {
  // Get the current stored array from Redux (slice can be dynamic)
  const { storedArray } = useSelector(selector);
  const connectionRef = useRef(null);
  const storedArrayRef = useRef(storedArray);

  // State to notify UI about connection status changes
  const [, setIsConnected] = useState(false);

  if (!connectionRef.current) {
    const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url));
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
    let apiUrl = `${wsUrl}/get-all-${modelName}-ws`;
    if (crudOverrideDict?.GET_ALL) {
      const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
      if (!params && Object.keys(paramDict).length > 0) return;
      apiUrl = `${wsUrl}/ws-${endpoint}`;
      if (params) {
        const paramsStr = '?' + Object.keys(params).map((k) => `${k}=${params[k]}`).join('&');
        apiUrl += paramsStr;
      }
    }

    const connection = connectionRef.current;
    const { messageBuffer } = connection;
    const ws = new WebSocket(apiUrl);
    connection.ws = ws;
    setWebSocketConnection(modelName, ws);

    // Update state when connection opens
    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      messageBuffer.push(event.data);
    };

    ws.onerror = (e) => {
      console.error(`WebSocket error for ${modelName}:`, e);
    };

    ws.onclose = (e) => {
      const { code, reason, wasClean } = e;
      // Notify UI that the connection is closed
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
        clearWebSocketConnection(modelName);
        // Update state to notify UI
        setIsConnected(false);
      }
    };
  }, [url, isDisabled, params, reconnectCounter]);

  // Periodically send accumulated messages and the current storedArray to the worker
  useEffect(() => {
    const interval = setInterval(() => {
      const connection = connectionRef.current;
      const { messageBuffer, isWorkerBusy, worker } = connection;
      if (messageBuffer.length > 0 && !isWorkerBusy) {
        const messages = [...messageBuffer];
        connection.messageBuffer.length = 0;
        connection.isWorkerBusy = true;
        worker.postMessage({ messages, storedArray: storedArrayRef.current, uiLimit, isAlertModel });
      }
    }, 1000); // Dispatch every 1 sec

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
