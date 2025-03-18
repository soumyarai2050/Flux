import { useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import { WEBSOCKET_CLOSE_CODES, WEBSOCKET_RETRY_CODES } from '../constants';

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
  crudOverrideDict = {},
  params = null
}) {
  // Get the current stored array from Redux (slice can be dynamic)
  const { storedArray } = useSelector(selector);
  const connectionRef = useRef(null);

  const storedArrayRef = useRef(storedArray);

  if (!connectionRef.current) {
    const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url));
    connectionRef.current = {
      worker,
      messageBuffer: [],
      isWorkerBusy: false,
      ws: null,
      retryCount: 0
    }
  }

  useEffect(() => {
    storedArrayRef.current = storedArray;
  }, [storedArray])

  // Create and manage the WebSocket connection only if url exists and is not disabled
  useEffect(() => {
    if (isAbbreviationSource) return;

    if (!url || isDisabled) {
      return;
    }
    const wsUrl = url.replace('http', 'ws');
    let apiUrl = `${wsUrl}/get-all-${modelName}-ws`;
    if (crudOverrideDict.GET_ALL) {
      const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
      if (!params && Object.keys(paramDict).length > 0) {
        return;
      }
      apiUrl = `${wsUrl}/ws-${endpoint}`;
      if (params) {
        const paramsStr = '?' + Object.keys(params).map((k) => `${k}=${params[k]}`).join('&');
        apiUrl += paramsStr;
      }
    }

    const connection = connectionRef.current;
    const { messageBuffer, retryCount } = connection;
    const ws = new WebSocket(apiUrl);
    connection.ws = ws;

    ws.onmessage = (event) => {
      messageBuffer.push(event.data);
    };

    ws.onerror = (e) => {
      console.error(`ws closed on error for ${modelName}. ${e}`)
    }
    ws.onclose = (e) => {
      const { code, reason, wasClean } = e;
      if (WEBSOCKET_RETRY_CODES.includes(code)) {
        if (retryCount <= 10) {
          connection.retryCount += 1;
          setTimeout(() => {
            console.log(`reconnecting ws for ${modelName}, retryCount: ${retryCount}`);
            onReconnect();
          }, code === WEBSOCKET_CLOSE_CODES.TRY_AGAIN_LATER ? connection.retryCount * 10000 : 10000);
        }
      }
      if (code !== WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE) {
        console.error(`ws closed for ${modelName}, code: ${code}, reason: ${reason}, wasClean: ${wasClean}`);
      }
    }

    return () => {
      if (connectionRef.current.ws) {
        connectionRef.current.ws.close();
        connectionRef.current.ws = null;
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

  return connectionRef.current?.ws;
}

export default useWebSocketWorker;

