import { useEffect, useRef, useState } from "react";
import { WebWorkerManager } from "../services/WebWorkerManager";

/**
 * @function useWebWorker
 * @description A custom React hook for managing a Web Worker's lifecycle and communication.
 * It provides a simplified interface to run tasks in a Web Worker and handle its results or errors.
 * @param {function} workerFn - The function that will be executed as a Web Worker.
 * @returns {object} An object containing Web Worker control functions and status.
 * @property {function(any): void} runTask - Function to send a message to the Web Worker to run a task.
 * @property {boolean} isBusy - True if the Web Worker is currently busy processing a task.
 * @property {any} result - The last result received from the Web Worker.
 * @property {Error|null} error - Any error encountered by the Web Worker.
 */
const useWebWorker = (workerFn) => {
  const managerRef = useRef(null);
  const [isBusy, setIsBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    managerRef.current = new WebWorkerManager(workerFn);
    return () => {
      managerRef.current.terminate();
    };
  }, [workerFn]);

  const runTask = (message) => {
    if (!managerRef.current) {
      setError("Web Worker manager not initialized.");
      return;
    }

    const manager = managerRef.current;

    if (manager.isBusy) {
      setError("Worker is busy");
      return;
    }

    setIsBusy(true);
    setError(null); // Clear previous errors
    setResult(null); // Clear previous results

    manager.postMessage(
      message,
      (res) => {
        setResult(res);
        setIsBusy(false);
      },
      (err) => {
        setError(err);
        setIsBusy(false);
      }
    );
  };

  return { runTask, isBusy, result, error };
};

export default useWebWorker;
