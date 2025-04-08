import { useEffect, useRef, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { WEBSOCKET_CLOSE_CODES, WEBSOCKET_RETRY_CODES } from '../constants';
import { isWebSocketAlive } from '../utils';
import { clearWebSocketConnection, setWebSocketConnection } from '../cache/websocketConnectionCache';

/**
 * Hook for managing WebSocket connections with dedicated Web Workers.
 * Supports two modes:
 *  - Get-all mode: A single connection per dataSource.
 *  - By-id mode: Multiple connections per dataSource keyed by active IDs.
 *
 * The hook buffers messages received from each WebSocket and periodically posts
 * them to a Web Worker for processing. When processed, a Redux action is dispatched
 * to update the corresponding stored array.
 *
 * @param {Object} params - The hook parameters.
 * @param {Array} params.dataSources - Array of dataSource objects. Each should include:
 *   - {string} url - The WebSocket URL.
 *   - {string} name - Unique name for the connection.
 *   - {Object} actions - Object containing at least a `setStoredArray` action creator.
 * @param {boolean} params.isDisabled - If true, all connections are disabled.
 * @param {number} params.reconnectCounter - Changing this value triggers a reconnection.
 * @param {Function} params.onReconnect - Callback triggered when a reconnection is attempted.
 * @param {Object} params.storedArrayDict - Maps dataSource names to their stored arrays.
 * @param {Object} [params.dataSourcesCrudOverrideDict=null] - Optionally override endpoints per dataSource.
 * @param {Object} [params.dataSourcesParams=null] - Optional parameters per dataSource.
 * @param {boolean} [params.connectionByGetAll=false] - If true, use a single WebSocket per dataSource.
 * @param {Array} [params.activeIds=[]] - For by-id mode, an array of active IDs to maintain connections for.
 */
const useDataSourcesWebsocketWorker = ({
  dataSources,
  isDisabled,
  reconnectCounter,
  onReconnect,
  storedArrayDict,
  dataSourcesCrudOverrideDict = null,
  dataSourcesParams = null,
  connectionByGetAll = false,
  activeIds = []
}) => {
  const dispatch = useDispatch();

  // Constants for retry logic.
  const MAX_RETRY_COUNT = 10;
  const BASE_RETRY_DELAY = 10000; // milliseconds

  // Ref to store connection objects for each dataSource.
  const connectionsRef = useRef({});

  // Ref to maintain the latest stored arrays.
  const storedArrayDictRef = useRef(storedArrayDict);
  useEffect(() => {
    storedArrayDictRef.current = storedArrayDict;
  }, [storedArrayDict]);

  /**
   * Converts an HTTP/HTTPS URL to the corresponding WS/WSS URL.
   * @param {string} url - The original URL.
   * @returns {string} - The WebSocket URL.
   */
  const getWebSocketUrl = useCallback((url) => {
    try {
      const parsedUrl = new URL(url);
      parsedUrl.protocol = parsedUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      return parsedUrl.toString();
    } catch (error) {
      console.error('Invalid URL provided for WebSocket:', url);
      return url;
    }
  }, []);

  /**
   * Handles reconnection logic for a given connection.
   * Increases the retry count and calls the provided onReconnect callback after a delay.
   *
   * @param {Object} connection - The connection object.
   * @param {string} name - The dataSource name.
   * @param {string|number} [id] - Optional ID for by-id mode.
   */
  const handleReconnection = (connection, name, id = null) => {
    if (connection.retryCount < MAX_RETRY_COUNT) {
      connection.retryCount += 1;
      const delay = connection.lastCloseCode === WEBSOCKET_CLOSE_CODES.TRY_AGAIN_LATER
        ? connection.retryCount * BASE_RETRY_DELAY
        : BASE_RETRY_DELAY;
      setTimeout(() => {
        console.info(`Reconnecting WebSocket for ${name}${id ? ` id ${id}` : ''}, retryCount: ${connection.retryCount}`);
        onReconnect();
      }, delay);
    } else {
      console.error(`WebSocket closed for ${name}${id ? ` id ${id}` : ''} after maximum retry attempts`);
    }
  };

  // -----------------------------
  // Initialization: Create connection objects and start Web Workers.
  // -----------------------------
  useEffect(() => {
    dataSources.forEach(({ name }) => {
      if (!connectionsRef.current[name]) {
        const worker = new Worker(new URL('../workers/websocket-update.worker.js', import.meta.url));
        connectionsRef.current[name] = {
          worker,
          messageBuffer: [],
          isWorkerBusy: false,
          // For get-all mode: single WebSocket instance; for by-id mode: an object keyed by id.
          ws: connectionByGetAll ? null : {},
          messageHandler: null,
          retryCount: 0,
          lastCloseCode: null,
        };
      }
    });

    // Cleanup: Terminate workers on unmount.
    return () => {
      Object.values(connectionsRef.current).forEach((connection) => {
        if (connection.worker) {
          connection.worker.terminate();
        }
      });
    };
  }, []);

  // -----------------------------
  // GET-ALL MODE: Single WebSocket per dataSource
  // -----------------------------
  useEffect(() => {
    if (!connectionByGetAll) return;

    const currentConnectionDict = connectionsRef.current;
    dataSources.forEach(({ name, url }) => {
      if (!url || isDisabled) return;

      const wsUrl = getWebSocketUrl(url);
      let apiUrl = `${wsUrl}/get-all-${name}-ws`;
      const crudOverrideDict = dataSourcesCrudOverrideDict?.[name];
      const params = dataSourcesParams?.[name] ?? null;
      if (crudOverrideDict?.GET_ALL) {
        const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
        if (!params && Object.keys(paramDict).length > 0) return;
        apiUrl = `${wsUrl}/ws-${endpoint}`;
        if (params) {
          const paramsStr = '?' + Object.keys(params)
            .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
            .join('&');
          apiUrl += paramsStr;
        }
      }

      const connection = currentConnectionDict[name];
      const { messageBuffer } = connection;
      if (!connection.ws || connection.ws.readyState === WebSocket.CLOSED) {
        connection.retryCount = 0; // Reset retry count for a new connection.
        const ws = new WebSocket(apiUrl);
        connection.ws = ws;
        setWebSocketConnection(name, ws);

        ws.onopen = () => {
          connection.retryCount = 0;
        };

        ws.onmessage = (event) => {
          messageBuffer.push(event.data);
        };

        ws.onerror = (e) => {
          console.error(`WebSocket error for ${name}:`, e);
        };

        ws.onclose = (e) => {
          const { code, reason, wasClean } = e;
          connection.lastCloseCode = code;
          if (WEBSOCKET_RETRY_CODES.includes(code)) {
            handleReconnection(connection, name);
          }
          if (code !== WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE) {
            console.error(`WebSocket closed for ${name}, code: ${code}, reason: ${reason}, wasClean: ${wasClean}`);
          }
        };
      }
    });

    // Cleanup: Close all WebSocket connections on unmount or dependency change.
    return () => {
      if (!connectionByGetAll) return;
      Object.entries(connectionsRef.current).forEach(([name, connection]) => {
        if (connection.ws && connection.ws.readyState !== WebSocket.CLOSED) {
          connection.ws.close(WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE, 'Normal closure on cleanup');
          connection.ws = null;
          clearWebSocketConnection(name);
        }
      });
    };
  }, [
    dataSourcesParams,
    isDisabled,
    reconnectCounter
  ]);

  // -----------------------------
  // BY-ID MODE: Create or update connections for active IDs
  // -----------------------------
  useEffect(() => {
    if (connectionByGetAll) return;

    // If disabled, close all active connections.
    if (isDisabled) {
      dataSources.forEach(({ name }) => {
        const connection = connectionsRef.current[name];
        if (connection) {
          Object.keys(connection.ws).forEach((id) => {
            const socket = connection.ws[id];
            if (socket && socket.readyState !== WebSocket.CLOSED) {
              socket.close(WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE, 'Disabled: closing connection');
            }
            delete connection.ws[id];
          });
        }
      });
      return;
    }

    const currentConnectionDict = connectionsRef.current;
    dataSources.forEach(({ name, url }) => {
      if (!url) return;

      const wsUrl = getWebSocketUrl(url);
      let apiUrl = `${wsUrl}/get-${name}-ws`;
      const crudOverrideDict = dataSourcesCrudOverrideDict?.[name];
      const params = dataSourcesParams?.[name] ?? null;
      let paramsStr = '';
      if (crudOverrideDict?.GET_ALL) {
        const { endpoint, paramDict } = crudOverrideDict.GET_ALL;
        if (!params && Object.keys(paramDict).length > 0) return;
        apiUrl = `${wsUrl}/ws-${endpoint}`;
        if (params) {
          paramsStr = '?' + Object.keys(params)
            .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
            .join('&');
        }
      }

      const connection = currentConnectionDict[name];
      const { messageBuffer, ws } = connection;

      // For each active ID, create or update the corresponding WebSocket.
      activeIds.forEach((id) => {
        const normalizedId = String(id);
        let socket = ws[normalizedId];
        if (!socket || !isWebSocketAlive(socket)) {
          connection.retryCount = 0;
          socket = new WebSocket(`${apiUrl}/${id}${paramsStr}`);
          ws[normalizedId] = socket;
          setWebSocketConnection(name, socket);

          socket.onopen = () => {
            connection.retryCount = 0;
          };

          socket.onmessage = (event) => {
            messageBuffer.push(event.data);
          };

          socket.onerror = (e) => {
            console.error(`WebSocket error for ${name} id ${normalizedId}:`, e);
          };

          socket.onclose = (e) => {
            const { code, reason, wasClean } = e;
            connection.lastCloseCode = code;
            if (WEBSOCKET_RETRY_CODES.includes(code)) {
              handleReconnection(connection, name, normalizedId);
            }
            if (code !== WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE) {
              console.error(`WebSocket closed for ${name} id ${normalizedId}, code: ${code}, reason: ${reason}, wasClean: ${wasClean}`);
            }
          };
        }
      });

      // Close any connections that are no longer active.
      Object.keys(ws).forEach((id) => {
        if (!activeIds.map(String).includes(id)) {
          const socket = ws[id];
          if (socket && socket.readyState !== WebSocket.CLOSED) {
            socket.close(WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE, 'Closing inactive socket');
          }
          delete ws[id];
        }
      });
    });
  }, [
    activeIds,
    dataSourcesParams,
    isDisabled,
    reconnectCounter
  ]);

  // Cleanup for by-id mode on unmount: close all active connections.
  useEffect(() => {
    return () => {
      if (connectionByGetAll) return;
      Object.entries(connectionsRef.current).forEach(([name, connection]) => {
        Object.keys(connection.ws).forEach((id) => {
          const socket = connection.ws[id];
          if (socket && socket.readyState !== WebSocket.CLOSED) {
            socket.close(WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE, 'Normal closure on cleanup');
          }
          delete connection.ws[id];
        });
        clearWebSocketConnection(name);
      });
    };
  }, []);

  // -----------------------------
  // Periodically post buffered messages to the Web Worker.
  // -----------------------------
  useEffect(() => {
    const interval = setInterval(() => {
      dataSources.forEach(({ name }) => {
        const connection = connectionsRef.current[name];
        const { messageBuffer, isWorkerBusy } = connection;
        if (messageBuffer.length > 0 && !isWorkerBusy) {
          const messages = [...messageBuffer];
          connection.messageBuffer.length = 0;
          connection.isWorkerBusy = true;
          connection.worker.postMessage({
            messages,
            storedArray: storedArrayDictRef.current[name]
          });
        }
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [])

  // -----------------------------
  // Set up worker event listeners to handle responses.
  // -----------------------------
  useEffect(() => {
    dataSources.forEach(({ name, actions }) => {
      const connection = connectionsRef.current[name];
      const handleWorkerMessage = (e) => {
        dispatch(actions.setStoredArray(e.data));
        connection.isWorkerBusy = false;
      };
      connection.messageHandler = handleWorkerMessage;
      connection.worker.addEventListener('message', handleWorkerMessage);
    });
    return () => {
      dataSources.forEach(({ name }) => {
        const connection = connectionsRef.current[name];
        if (connection && connection.worker && connection.messageHandler) {
          connection.worker.removeEventListener('message', connection.messageHandler);
        }
      });
    };
  }, []);
};

export default useDataSourcesWebsocketWorker;