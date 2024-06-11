import { getAbbreviatedRows, applyFilter, getActiveRows, getGroupedTableRows } from "../workerUtils";

onmessage = (e) => {
    const { items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters, joinBy } = e.data;
    const rows = getAbbreviatedRows(items, itemsDataDict, itemProps, abbreviation, loadedProps);
    const groupedRows = getGroupedTableRows(rows, joinBy, sortOrders);
    const filteredRows = applyFilter(rows, filters);
    const filteredGroupedRows = applyFilter(groupedRows, filters, true);
    const activeRows = getActiveRows(filteredGroupedRows, page, pageSize, sortOrders);
    postMessage([filteredRows, filteredGroupedRows, activeRows]);
}

export { };