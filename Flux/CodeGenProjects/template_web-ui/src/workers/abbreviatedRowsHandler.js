import { getAbbreviatedRows, applyFilter, getActiveRows } from "../workerUtils";

onmessage = (e) => {
    const { items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, order, orderBy, filters } = e.data;
    const rows = getAbbreviatedRows(items, itemsDataDict, itemProps, abbreviation, loadedProps);
    const filteredRows = applyFilter(rows, filters);
    const activeRows = getActiveRows(filteredRows, page, pageSize, order, orderBy);
    postMessage([filteredRows, activeRows]);
}

export { };