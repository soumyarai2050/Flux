import { useEffect, useRef, useState, useCallback } from "react";
import WebSocketManager from "../services/WebSocketManger";

export const useWebSocket = (url, options = {}) => {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Initialize or cleanup WebSocket connection
  useEffect(() => {
    if (!url) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    setIsRetrying(false);
    wsRef.current = new WebSocketManager(url, options);

    // Default WebSocket event handlers
    wsRef.current.setOnOpen(() => {
      setIsConnected(true);
      setIsRetrying(false);
      console.log("WebSocket connected.");
    });

    wsRef.current.setOnClose(() => {
      setIsConnected(false);
      if (!wsRef.current?.isTeardown) {
        setIsRetrying(true);
        console.log("WebSocket retrying...");
      } else {
        setIsRetrying(false);
        console.log("WebSocket closed.");
      }
    });

    wsRef.current.setOnError((error) => {
      console.error("WebSocket error:", error);
    });

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url, options]);

  // Send message callback
  const sendMessage = useCallback((message) => {
    if (wsRef.current) {
      wsRef.current.send(message);
    } else {
      console.warn("WebSocket is not connected.");
    }
  }, []);

  // Close WebSocket explicitly
  const closeWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
      setIsRetrying(false);
    }
  }, []);

  // Custom message handler
  const setOnMessage = useCallback((listener) => {
    if (wsRef.current) {
      wsRef.current.setOnMessage(listener);
    }
  }, []);

  return {
    sendMessage,
    closeWebSocket,
    isConnected,
    isRetrying,
    setOnMessage, // Expose only this for customization
  };
};

export default useWebSocket;
