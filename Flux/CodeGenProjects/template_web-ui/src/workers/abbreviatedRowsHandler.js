import { getAbbreviatedRows, applyFilter, getActiveRows, getGroupedTableRows } from "../workerUtils";

onmessage = (e) => {
    const { items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters, joinBy, joinSort } = e.data;
    const rows = getAbbreviatedRows(items, itemsDataDict, itemProps, abbreviation, loadedProps);
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, joinBy, joinSort);
    const activeRows = getActiveRows(groupedRows, page, pageSize, sortOrders, true);
    postMessage([filteredRows, groupedRows, activeRows]);
}

export { };