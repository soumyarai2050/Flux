import _, { cloneDeep } from "lodash";
import { DB_ID } from "../constants";

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

export function applyGetAllWebsocketUpdate(arr, obj, uiLimit) {
    const index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
    let updatedArr = arr.filter(o => o[DB_ID] !== obj[DB_ID]);
    // if obj is not deleted object
    if (Object.keys(obj) !== 1) {
        // if index is not equal to -1, it is updated obj. If updated, replace the obj at the index
        if (index !== -1) {
            updatedArr.splice(index, 0, obj);
        } else {
            updatedArr.push(obj);
        }
    }
    return updatedArr;
}

export {};