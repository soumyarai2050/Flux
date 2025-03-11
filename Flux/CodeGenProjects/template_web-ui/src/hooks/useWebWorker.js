import { useEffect, useRef, useState } from "react";
import { WebWorkerManager } from "../services/WebWorkerManager";

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
    if (!managerRef.current) return;

    const manager = managerRef.current;

    if (manager.isBusy) {
      setError("Worker is busy");
      return;
    }

    setIsBusy(true);
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
