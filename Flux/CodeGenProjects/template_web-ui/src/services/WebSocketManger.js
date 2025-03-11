export class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url;
    this.retryInterval = options.retryInterval || 3000;
    this.maxRetries = options.maxRetries || 5;
    this.currentRetries = 0;
    this.isTeardown = false;
    this.ws = null;

    // Event listeners
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
    this.onerror = null;

    this.connect();
  }

  connect() {
    if (!this.url) return;

    this.ws = new WebSocket(this.url);

    // Attach event listeners to the new WebSocket instance
    this.transferListeners();

    this.ws.onopen = (event) => {
      this.currentRetries = 0;
      if (this.onopen) this.onopen(event);
    };

    this.ws.onclose = () => {
      if (this.isTeardown) return;
      if (this.currentRetries < this.maxRetries) {
        setTimeout(() => {
          this.currentRetries++;
          this.connect(); // Retry connection
        }, this.retryInterval);
      } else if (this.onclose) {
        this.onclose();
      }
    };

    this.ws.onerror = (error) => {
      if (this.onerror) this.onerror(error);
    };
  }

  transferListeners() {
    if (this.onmessage) this.ws.onmessage = this.onmessage;
    if (this.onopen) this.ws.onopen = this.onopen;
    if (this.onclose) this.ws.onclose = this.onclose;
    if (this.onerror) this.ws.onerror = this.onerror;
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn("WebSocket is not open. Message not sent.");
    }
  }

  close() {
    this.isTeardown = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  setOnOpen(listener) {
    this.onopen = listener;
    if (this.ws) this.ws.onopen = listener;
  }

  setOnClose(listener) {
    this.onclose = listener;
    if (this.ws) this.ws.onclose = listener;
  }

  setOnMessage(listener) {
    this.onmessage = listener;
    if (this.ws) this.ws.onmessage = listener;
  }

  setOnError(listener) {
    this.onerror = listener;
    if (this.ws) this.ws.onerror = listener;
  }
}
