import _, { cloneDeep } from "lodash";
import { applyGetAllWebsocketUpdate } from "../workerUtils";

onmessage = (e) => {
    const { getAllDict, storedArray } = e.data;
    let updatedArray = cloneDeep(storedArray);
    _.entries(getAllDict).map(([k, v]) => {
        k *= 1;
        updatedArray = applyGetAllWebsocketUpdate(updatedArray, v);
        return;
    })
    postMessage([updatedArray]);
}

export { };