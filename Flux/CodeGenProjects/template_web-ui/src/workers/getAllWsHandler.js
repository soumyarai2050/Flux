import { cloneDeep } from "lodash";
import { applyGetAllWebsocketUpdate, sortAlertArray } from "../workerUtils";

onmessage = (event) => {
    const { getAllDict, storedArray, uiLimit = null, isAlertModel = false } = event.data;
    let updatedArray = cloneDeep(storedArray);
    Object.values(getAllDict).forEach(obj => {
        updatedArray = applyGetAllWebsocketUpdate(updatedArray, obj, uiLimit, isAlertModel);
    })
    if (isAlertModel) {
        sortAlertArray(updatedArray);
    }
    postMessage([updatedArray]);
}

export { };