import { getAbbreviatedRows, applyFilter, getActiveRows } from "../workerUtils";

onmessage = (e) => {
    const { items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters } = e.data;
    const rows = getAbbreviatedRows(items, itemsDataDict, itemProps, abbreviation, loadedProps);
    const filteredRows = applyFilter(rows, filters);
    const activeRows = getActiveRows(filteredRows, page, pageSize, sortOrders);
    postMessage([filteredRows, activeRows]);
}

export { };