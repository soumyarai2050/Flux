import { cloneDeep } from 'lodash';
import { DB_ID, MODES } from '../constants';
import { applyFilter } from '../utils/core/dataFiltering';
import {
    getActiveRows, getCommonKeyCollections, getFilteredCells, getGroupedTableColumns,
    getTableColumns, getTableRows
} from '../utils/ui/tableUtils';
import { getGroupedTableRows, getMaxRowSize } from '../utils/core/dataGrouping';
import { addxpath } from '../utils/core/dataAccess';
import { sortColumns, applyRowIdsFilter, getSortOrdersWithAbs, getUniqueValues } from '../utils/ui/uiUtils';

onmessage = (e) => {
    const { storedArray, updatedObj, fieldsMetadata, filters, mode, page, rowsPerPage, sortOrders,
        joinBy, joinSort, enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll,
        columnOrders, frozenColumns, columnNameOverride, highlightUpdateOverride, noCommonKeyOverride,
        centerJoin, flip, rowIds
    } = e.data;
    const uniqueValues = getUniqueValues(storedArray, fieldsMetadata.filter((meta) => meta.filterEnable));
    const filteredArray = applyFilter(storedArray, filters);
    const rowIdsFilteredRows = applyRowIdsFilter(filteredArray, rowIds);
    const clonedArray = addxpath(cloneDeep(rowIdsFilteredRows));
    const updatedArray = clonedArray.map((o) => o[DB_ID] === updatedObj[DB_ID] ? updatedObj : o);
    const rows = getTableRows(fieldsMetadata, mode, filteredArray, updatedArray, null, true);
    const groupedRows = getGroupedTableRows(rows, joinBy, joinSort);
    const { sortedRows, activeRows } = getActiveRows(groupedRows, page, rowsPerPage, sortOrders, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const updatedMode = mode === MODES.EDIT && !rowIds ? mode : MODES.READ;
    const columns = getTableColumns(fieldsMetadata, updatedMode, {
        enableOverride,
        disableOverride,
        showLess,
        frozenColumns,
        columnNameOverride,
        highlightUpdateOverride,
        noCommonKeyOverride,
    }, false, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, updatedMode, false);  // headCells
    if (updatedMode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, true, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip);
    postMessage({ rows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, uniqueValues, sortedCells });
}

export { };