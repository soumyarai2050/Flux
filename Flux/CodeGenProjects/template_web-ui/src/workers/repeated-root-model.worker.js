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
        centerJoin, flip, rowIds, serverSidePaginationEnabled
    } = e.data;
    const filterFieldsMetadata = fieldsMetadata.filter((meta) => meta.filterEnable);
    const filterAppliedFields = new Set(filters?.map((o) => o.column_name) ?? []);
    const uniqueValues = getUniqueValues(storedArray, filterFieldsMetadata);
    const filteredArray = applyFilter(storedArray, filters);
    const clonedArray = addxpath(cloneDeep(filteredArray));
    const updatedArray = clonedArray.map((o) => o[DB_ID] === updatedObj[DB_ID] ? updatedObj : o);
    const rows = getTableRows(fieldsMetadata, mode, filteredArray, updatedArray, null, true);
    const rowIdsFilteredRows = applyRowIdsFilter(rows, rowIds);
    const groupedRows = getGroupedTableRows(rowIdsFilteredRows, joinBy, joinSort);

    // If server-side pagination is enabled, skip client-side pagination slice
    //we have used serverSidePaginationEnabled here to skip client-side pagination
    // The storedArray already contains only the rows for the current page
    const { sortedRows, activeRows } = serverSidePaginationEnabled
        ? getActiveRows(groupedRows, 0, rowsPerPage, sortOrders, true)
        : getActiveRows(groupedRows, page, rowsPerPage, sortOrders, true);
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
    let commonKeys;
    let nullColumns;
    if (updatedMode === MODES.EDIT) {
        commonKeys = [];
        nullColumns = [];
    } else {
        [commonKeys, nullColumns] = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, true, !showMore && !moreAll);
    }
    const updatedCommonKeys = commonKeys.filter((o) => !filterAppliedFields.has(o.tableTitle));
    const cells = getFilteredCells(groupedColumns, [...updatedCommonKeys, ...nullColumns], showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip);
    postMessage({ rows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, columns, commonKeys: updatedCommonKeys, uniqueValues, sortedCells });
}

export { };