import { DB_ID, MODES } from '../constants';
import {
    getRowsFromAbbreviation, applyFilter, getActiveRows, getGroupedTableRows, getMaxRowSize,
    getCommonKeyCollections, getGroupedTableColumns, getTableColumns,
    getFilteredCells
} from '../workerUtils';
import { sortColumns, getActiveIds } from '../utils';

onmessage = (e) => {
    const {
        items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters,
        joinBy, joinSort, mode, enableOverride, disableOverride, showMore, showLess, showAll, moreAll, showHidden, columnOrders,
        centerJoin, flip
    } = e.data;
    const rows = getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps);  // not used externally
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, joinBy, joinSort);
    const activeRows = getActiveRows(groupedRows, page, pageSize, sortOrders, true);
    const modelItemIdField = itemProps.find(meta => meta.tableTitle === DB_ID)?.key;
    const activeIds = getActiveIds(activeRows, modelItemIdField);
    const maxRowSize = getMaxRowSize(activeRows);
    const columns = getTableColumns(itemProps, MODES.READ, enableOverride, disableOverride, showLess, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, mode, true);  // headCells
    if (mode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, true, false, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip, true);
    postMessage({ rows: filteredRows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, sortedCells, activeIds });
}

export { };