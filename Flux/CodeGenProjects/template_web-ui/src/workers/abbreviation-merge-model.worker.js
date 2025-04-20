import { DB_ID, MODES } from '../constants';
import {
    getRowsFromAbbreviation, applyFilter, getActiveRows, getGroupedTableRows, getMaxRowSize,
    getCommonKeyCollections, getGroupedTableColumns, getTableColumns,
    getFilteredCells
} from '../workerUtils';
import { sortColumns, getActiveIds, applyRowIdsFilter, getSortOrdersWithAbs } from '../utils';

onmessage = (e) => {
    const {
        items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters,
        joinBy, joinSort, mode, enableOverride, disableOverride, showMore, showLess, showAll, moreAll, showHidden, columnOrders, absoluteSortOverride,
        centerJoin, flip, rowIds
    } = e.data;
    const rows = getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps);  // not used externally
    const filteredRows = applyFilter(rows, filters);
    const rowIdsFilteredRows = applyRowIdsFilter(filteredRows, rowIds);
    const groupedRows = getGroupedTableRows(rowIdsFilteredRows, joinBy, joinSort);
    const sortOrdersWithAbs = getSortOrdersWithAbs(sortOrders, absoluteSortOverride);
    const activeRows = getActiveRows(groupedRows, page, pageSize, sortOrdersWithAbs, true);
    const modelItemIdField = itemProps.find(meta => meta.tableTitle === DB_ID)?.key;
    const activeIds = getActiveIds(activeRows, modelItemIdField);
    const maxRowSize = getMaxRowSize(activeRows);
    const updatedMode = mode === MODES.EDIT && !rowIds ? mode : MODES.READ;
    const columns = getTableColumns(itemProps, updatedMode, enableOverride, disableOverride, showLess, absoluteSortOverride, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, updatedMode, true);  // headCells
    if (updatedMode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, true, false, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll, true);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip, true);
    postMessage({ rows: filteredRows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, sortedCells, activeIds });
}

export { };