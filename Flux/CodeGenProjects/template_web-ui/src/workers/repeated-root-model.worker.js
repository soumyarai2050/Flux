import { cloneDeep } from 'lodash';
import { DB_ID, MODES } from '../constants';
import {
    applyFilter, getActiveRows, getCommonKeyCollections, getFilteredCells,
    getGroupedTableColumns, getGroupedTableRows, getMaxRowSize,
    getTableColumns
} from '../workerUtils';
import { addxpath, getTableRows, sortColumns, applyRowIdsFilter, getSortOrdersWithAbs } from '../utils';

onmessage = (e) => {
    const { storedArray, updatedObj, fieldsMetadata, filters, mode, page, rowsPerPage, sortOrders,
        joinBy, joinSort, enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll,
        columnOrders, absoluteSortOverride, centerJoin, flip, rowIds
    } = e.data;
    const filteredArray = applyFilter(storedArray, filters);
    const rowIdsFilteredRows = applyRowIdsFilter(filteredArray, rowIds);
    const clonedArray = addxpath(cloneDeep(rowIdsFilteredRows));
    const updatedArray = clonedArray.map((o) => o[DB_ID] === updatedObj[DB_ID] ? updatedObj : o);
    const rows = getTableRows(fieldsMetadata, mode, filteredArray, updatedArray, null, true);
    const groupedRows = getGroupedTableRows(rows, joinBy, joinSort);
    const sortOrdersWithAbs = getSortOrdersWithAbs(sortOrders, absoluteSortOverride);
    const activeRows = getActiveRows(groupedRows, page, rowsPerPage, sortOrdersWithAbs, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const updatedMode = mode === MODES.EDIT && !rowIds ? mode : MODES.READ;
    const columns = getTableColumns(fieldsMetadata, updatedMode, enableOverride, disableOverride, showLess, absoluteSortOverride, false, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, updatedMode, false);  // headCells
    if (updatedMode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, true, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip);
    postMessage({ rows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, sortedCells });
}

export { };