/**
 * @class WebSocketManager
 * @description Manages a single WebSocket connection, including automatic reconnection with exponential backoff.
 */
export class WebSocketManager {
  /**
   * Creates an instance of WebSocketManager.
   * @param {string} url - The WebSocket URL to connect to.
   * @param {object} [options={}] - Configuration options for the WebSocket.
   * @param {number} [options.retryInterval=3000] - The base interval (in ms) before attempting a reconnect.
   * @param {number} [options.maxRetries=5] - The maximum number of reconnection attempts.
   */
  constructor(url, options = {}) {
    this.url = url;
    this.retryInterval = options.retryInterval || 3000;
    this.maxRetries = options.maxRetries || 5;
    this.currentRetries = 0;
    this.isTeardown = false; // Flag to indicate intentional closure
    this.ws = null;

    // Event listener callbacks
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
    this.onerror = null;

    this.connect();
  }

  /**
   * Establishes a WebSocket connection.
   * Handles initial connection and subsequent reconnections.
   */
  connect() {
    if (!this.url || this.isTeardown) return;

    this.ws = new WebSocket(this.url);

    // Transfer previously set listeners to the new WebSocket instance
    this.transferListeners();

    this.ws.onopen = (event) => {
      this.currentRetries = 0; // Reset retry count on successful connection
      if (this.onopen) this.onopen(event);
    };

    this.ws.onclose = (event) => {
      if (this.isTeardown) {
        if (this.onclose) this.onclose(event);
        return;
      }

      // Attempt reconnect with exponential backoff
      if (this.currentRetries < this.maxRetries) {
        const delay = this.retryInterval * Math.pow(2, this.currentRetries); // Exponential backoff
        console.warn(`WebSocket closed. Attempting reconnect ${this.currentRetries + 1}/${this.maxRetries} in ${delay}ms...`);
        setTimeout(() => {
          this.currentRetries++;
          this.connect();
        }, delay);
      } else {
        console.error(`WebSocket closed. Maximum retry attempts (${this.maxRetries}) reached.`);
        if (this.onclose) this.onclose(event);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      if (this.onerror) this.onerror(error);
    };
  }

  /**
   * Transfers the stored event listener callbacks to the current WebSocket instance.
   * This is crucial when a new WebSocket instance is created during reconnection.
   */
  transferListeners() {
    if (this.onmessage) this.ws.onmessage = this.onmessage;
    if (this.onopen) this.ws.onopen = this.onopen;
    if (this.onclose) this.ws.onclose = this.onclose;
    if (this.onerror) this.ws.onerror = this.onerror;
  }

  /**
   * Sends a message over the WebSocket connection.
   * @param {string|ArrayBufferLike|Blob|ArrayBufferView} message - The message to send.
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn("WebSocket is not open. Message not sent.");
    }
  }

  /**
   * Closes the WebSocket connection.
   * Sets `isTeardown` to true to prevent automatic reconnections.
   */
  close() {
    this.isTeardown = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Sets the callback for the 'open' event.
   * @param {function(Event): void} listener - The event listener for the 'open' event.
   */
  setOnOpen(listener) {
    this.onopen = listener;
    if (this.ws) this.ws.onopen = listener;
  }

  /**
   * Sets the callback for the 'close' event.
   * @param {function(CloseEvent): void} listener - The event listener for the 'close' event.
   */
  setOnClose(listener) {
    this.onclose = listener;
    if (this.ws) this.ws.onclose = listener;
  }

  /**
   * Sets the callback for the 'message' event.
   * @param {function(MessageEvent): void} listener - The event listener for the 'message' event.
   */
  setOnMessage(listener) {
    this.onmessage = listener;
    if (this.ws) this.ws.onmessage = listener;
  }

  /**
   * Sets the callback for the 'error' event.
   * @param {function(Event): void} listener - The event listener for the 'error' event.
   */
  setOnError(listener) {
    this.onerror = listener;
    if (this.ws) this.ws.onerror = listener;
  }
}
