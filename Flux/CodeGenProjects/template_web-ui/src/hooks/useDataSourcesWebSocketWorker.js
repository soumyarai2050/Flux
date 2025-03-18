import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import * as Selectors from '../selectors';
import { WEBSOCKET_CLOSE_CODES, WEBSOCKET_RETRY_CODES } from '../constants';

/**
 * Custom hook to handle multiple WebSocket connections with dedicated Web Workers.
 *
 * @param {Array} dataSources - An array of dataSource objects.
 * Each dataSource should have:
 *   - url: The WebSocket URL.
 *   - name: Unique name for the connection.
 *   - actions: An object containing at least an `update` action creator.
 *   - selector: A function that accepts the Redux state and returns the current stored array.
 */
const useDataSourcesWebsocketWorker = ({
  dataSources,
  isDisabled,
  reconnectCounter,
  onReconnect,
  activeItemIdMap
}) => {
  const dispatch = useDispatch();

  // Access the Redux state with a custom selector.
  const storedArrayDict = useSelector(
    (state) => Selectors.selectDataSourcesStoredArray(state, dataSources), (prev, curr) => {
      return JSON.stringify(prev) === JSON.stringify(curr);
    }
  );

  // Initialize the connectionsRef as an empty object.
  const connectionsRef = useRef({});

  const activeItemIdMapRef = useRef(activeItemIdMap);

  // Create connections (worker, message buffer, WebSocket, etc.) for each dataSource.
  useEffect(() => {
    dataSources.forEach(ds => {
      if (!connectionsRef.current[ds.name]) {
        // Create the Web Worker. Adjust the worker import as needed for your bundler.
        const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url));
        connectionsRef.current[ds.name] = {
          worker,
          messageBuffer: [],
          isWorkerBusy: false,
          ws: null,
          // We'll store the event listener so we can remove it later.
          messageHandler: null,
          retryCount: 0
        };
      }
    });
  }, []);

  // Keep a ref of the latest storedArray for use in worker postMessage.
  const storedArrayDictRef = useRef({});
  useEffect(() => {
    storedArrayDictRef.current = storedArrayDict;
  }, [storedArrayDict]);

  useEffect(() => {
    activeItemIdMapRef.current = activeItemIdMap;
  }, [activeItemIdMap])

  // Set up WebSocket connections.
  useEffect(() => {
    const currentConnectionDict = connectionsRef.current;
    dataSources.forEach(ds => {
      if (!ds.url || isDisabled) return;

      const connection = currentConnectionDict[ds.name];
      const { messageBuffer, retryCount } = connection;
      // Only create a new connection if one doesn't already exist.
      if (!connection.ws) {
        const ws = new WebSocket(`${ds.url.replace('http', 'ws')}/get-all-${ds.name}-ws`);
        connection.ws = ws;

        ws.onmessage = (event) => {
          // Add incoming messages to the buffer.
          messageBuffer.push(event.data);
        };

        ws.onerror = (e) => {
          console.error(`WebSocket error for ${ds.name}:`, e);
        };

        ws.onclose = (e) => {
          const { code, reason, wasClean } = e;
          if (WEBSOCKET_RETRY_CODES.includes(code)) {
            if (retryCount <= 10) {
              connection.retryCount += 1;
              setTimeout(() => {
                console.log(`reconnecting ws for ${ds.name}, retryCount: ${retryCount}`);
                onReconnect();
              },
                code === WEBSOCKET_CLOSE_CODES.TRY_AGAIN_LATER
                  ? connection.retryCount * 10000
                  : 10000);
            }
          }
          if (code !== WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE) {
            console.error(`ws closed for ${ds.name}, code: ${code}, reason: ${reason}, wasClean: ${wasClean}`);
          }
        };
      }
    });

    // Cleanup: close all WebSocket connections and terminate workers.
    return () => {
      Object.values(currentConnectionDict).forEach(connection => {
        if (connection.ws) {
          connection.ws.close();
          connection.ws = null;
        }
      });
    };
  }, [isDisabled, reconnectCounter]);

  // Periodically post messages to workers.
  useEffect(() => {
    const interval = setInterval(() => {
      dataSources.forEach(ds => {
        const connection = connectionsRef.current[ds.name];
        const { messageBuffer, isWorkerBusy } = connection;
        // Check if there are messages and the worker is free.
        if (messageBuffer.length > 0 && !isWorkerBusy) {
          const messages = [...messageBuffer];
          connection.messageBuffer.length = 0;
          connection.isWorkerBusy = true;
          connection.worker.postMessage({
            messages,
            storedArray: storedArrayDictRef.current[ds.name],
            activeItemIdMap: activeItemIdMapRef.current
          });
        }
      });
    }, 1000); // Dispatch every 1 sec

    return () => clearInterval(interval);
  }, [])

  // Set up worker event listeners to handle responses.
  useEffect(() => {
    const currentConnectionDict = connectionsRef.current;
    dataSources.forEach(ds => {
      const connection = currentConnectionDict[ds.name];
      // Define the event handler.
      const handleWorkerMessage = (e) => {
        dispatch(ds.actions.setStoredArray(e.data));
        connection.isWorkerBusy = false;
      };
      // Save the handler reference for later removal.
      connection.messageHandler = handleWorkerMessage;
      connection.worker.addEventListener('message', handleWorkerMessage);
    });

    // Cleanup: remove event listeners.
    return () => {
      dataSources.forEach(ds => {
        const connection = currentConnectionDict[ds.name];
        if (connection && connection.worker && connection.messageHandler) {
          connection.worker.removeEventListener('message', connection.messageHandler);
        }
      });
    };
  }, [dataSources, dispatch]);
};

export default useDataSourcesWebsocketWorker;