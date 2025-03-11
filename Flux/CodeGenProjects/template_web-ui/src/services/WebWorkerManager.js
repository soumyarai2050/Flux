export class WebWorkerManager {
  constructor(workerFn) {
    const blob = new Blob([`onmessage = ${workerFn.toString()}`], {
      type: "text/javascript",
    });
    this.worker = new Worker(URL.createObjectURL(blob));
    this.isBusy = false;
  }

  postMessage(message, onResult, onError) {
    if (this.isBusy) {
      return false; // Worker is busy
    }

    this.isBusy = true;
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

  terminate() {
    this.worker.terminate();
  }
}
