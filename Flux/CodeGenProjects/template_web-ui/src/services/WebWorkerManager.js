/**
 * @class WebWorkerManager
 * @description Manages the lifecycle and communication with a Web Worker.
 * This class allows creating a Web Worker from a function, posting messages to it,
 * and handling its responses and errors.
 */
export class WebWorkerManager {
  /**
   * Creates an instance of WebWorkerManager.
   * @param {function} workerFn - The function to be executed as a Web Worker. This function will become the `onmessage` handler of the worker.
   */
  constructor(workerFn) {
    // Create a Blob from the worker function's string representation.
    // The worker function will be set as the `onmessage` handler inside the worker.
    const blob = new Blob([`onmessage = ${workerFn.toString()}`], {
      type: "text/javascript",
    });
    // Create a new Worker from the Blob URL.
    this.worker = new Worker(URL.createObjectURL(blob));
    /**
     * @property {boolean} isBusy - Indicates whether the worker is currently processing a task.
     */
    this.isBusy = false;
  }

  /**
   * Posts a message to the Web Worker to initiate a task.
   * If the worker is already busy, the message will not be sent.
   * @param {any} message - The data to send to the worker.
   * @param {function(any): void} onResult - Callback function to be executed when the worker sends a result.
   * @param {function(Error): void} onError - Callback function to be executed if an error occurs in the worker.
   * @returns {boolean} True if the message was successfully sent, false if the worker was busy.
   */
  postMessage(message, onResult, onError) {
    if (this.isBusy) {
      return false; // Worker is busy
    }

    this.isBusy = true;
    // Set up one-time message and error handlers for the current task.
    this.worker.onmessage = (e) => {
      this.isBusy = false;
      onResult(e.data);
    };

    this.worker.onerror = (e) => {
      this.isBusy = false;
      onError(e.message);
    };

    this.worker.postMessage(message);
    return true; // Successfully sent
  }

  /**
   * Terminates the Web Worker.
   * This method should be called to clean up the worker when it's no longer needed.
   */
  terminate() {
    this.worker.terminate();
  }
}
