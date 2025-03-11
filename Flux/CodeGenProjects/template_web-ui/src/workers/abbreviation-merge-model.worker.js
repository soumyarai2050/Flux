import { MODES } from '../constants';
import {
    getRowsFromAbbreviation, applyFilter, getActiveRows, getGroupedTableRows, getMaxRowSize,
    getCommonKeyCollections, getGroupedTableColumns, getTableColumns,
    getFilteredCells
} from '../workerUtils';

onmessage = (e) => {
    const {
        items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters,
        joinBy, joinSort, mode, enableOverride, disableOverride, showMore, showLess, showAll, moreAll, showHidden
    } = e.data;
    const start = Date.now();
    const rows = getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps);  // not used externally
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, joinBy, joinSort);
    const activeRows = getActiveRows(groupedRows, page, pageSize, sortOrders, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const columns = getTableColumns(itemProps, MODES.READ, enableOverride, disableOverride, showLess, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, mode, true);  // headCells
    if (mode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, true, false, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    // console.log(Date.now() - start);
    postMessage({ rows: filteredRows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, filteredCells: cells });
}

export { };