import { cloneDeep, values } from "lodash";
import { applyGetAllWebsocketUpdate } from "../workerUtils";

onmessage = (e) => {
    const { getAllDict, storedArray } = e.data;
    const updatedArray = cloneDeep(storedArray);
    values(getAllDict).forEach(obj => {
        applyGetAllWebsocketUpdate(updatedArray, obj);
    })
    postMessage([updatedArray]);
}

export { };