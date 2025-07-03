import { DB_ID, MODES } from '../constants';
import {
    getRowsFromAbbreviation, applyFilter, getActiveRows, getGroupedTableRows, getMaxRowSize,
    getCommonKeyCollections, getGroupedTableColumns, getTableColumns,
    getFilteredCells
} from '../utils/index.js';
import { sortColumns, getActiveIds, applyRowIdsFilter, getSortOrdersWithAbs, getUniqueValues } from '../utils/index.js';

onmessage = (e) => {
    const {
        items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters,
        joinBy, joinSort, mode, enableOverride, disableOverride, showMore, showLess, showAll, moreAll, showHidden,
        columnOrders, frozenColumns, columnNameOverride, highlightUpdateOverride, noCommonKeyOverride,
        centerJoin, flip, rowIds
    } = e.data;
    const rows = getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps);  // not used externally
    const uniqueValues = getUniqueValues(rows, itemProps.filter((meta) => meta.filterEnable), true);
    const filteredRows = applyFilter(rows, filters);
    const rowIdsFilteredRows = applyRowIdsFilter(filteredRows, rowIds);
    const groupedRows = getGroupedTableRows(rowIdsFilteredRows, joinBy, joinSort);
    const { sortedRows, activeRows } = getActiveRows(groupedRows, page, pageSize, sortOrders, true);
    const modelItemIdField = itemProps.find(meta => meta.tableTitle === DB_ID)?.key;
    const activeIds = getActiveIds(activeRows, modelItemIdField);
    const maxRowSize = getMaxRowSize(activeRows);
    const updatedMode = mode === MODES.EDIT && !rowIds ? mode : MODES.READ;
    const columns = getTableColumns(itemProps, updatedMode, {
        enableOverride,
        disableOverride,
        showLess,
        frozenColumns,
        columnNameOverride,
        highlightUpdateOverride,
        noCommonKeyOverride,
    }, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, updatedMode, true);  // headCells
    if (updatedMode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, true, false, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll, true);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip, true);
    postMessage({ rows: filteredRows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, uniqueValues, sortedCells, activeIds });
}

export { };