import { DB_ID, MODES } from '../constants';
import {
    getRowsFromAbbreviation, getActiveRows, getCommonKeyCollections, getGroupedTableColumns,
    getTableColumns, getFilteredCells
} from '../utils/ui/tableUtils';
import { applyFilter } from '../utils/core/dataFiltering';
import { getGroupedTableRows, getMaxRowSize } from '../utils/core/dataGrouping';
import { sortColumns, getActiveIds, applyRowIdsFilter, getSortOrdersWithAbs, getUniqueValues } from '../utils/ui/uiUtils';

onmessage = (e) => {
    const {
        items, itemsDataDict, itemProps, abbreviation, loadedProps, page, pageSize, sortOrders, filters,
        joinBy, joinSort, mode, enableOverride, disableOverride, showMore, showLess, showAll, moreAll, showHidden,
        columnOrders, frozenColumns, columnNameOverride, highlightUpdateOverride, noCommonKeyOverride,
        centerJoin, flip, rowIds, serverSidePaginationEnabled
    } = e.data;
    const rows = getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps);  // not used externally
    const filterFieldsMetadata = itemProps.filter((meta) => meta.filterEnable);
    const filterAppliedFields = new Set(filters?.map((o) => o.column_name) ?? []);
    const uniqueValues = getUniqueValues(rows, filterFieldsMetadata, true);
    const filteredRows = applyFilter(rows, filters);
    const rowIdsFilteredRows = applyRowIdsFilter(filteredRows, rowIds);
    const groupedRows = getGroupedTableRows(rowIdsFilteredRows, joinBy, joinSort);

    // If server-side pagination is enabled, skip client-side pagination slice
    // The items already contain only the data for the current page
    const { sortedRows, activeRows } = serverSidePaginationEnabled
        ? getActiveRows(groupedRows, 0, pageSize, sortOrders, true)
        : getActiveRows(groupedRows, page, pageSize, sortOrders, true);
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
    let commonKeys;
    let nullColumns;
    if (updatedMode === MODES.EDIT) {
        commonKeys = [];
        nullColumns = [];
    } else {
        [commonKeys, nullColumns] = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, true, false, !showMore && !moreAll);
    }
    const updatedCommonKeys = commonKeys.filter((o) => !filterAppliedFields.has(o.key));
    const cells = getFilteredCells(groupedColumns, [...updatedCommonKeys, ...nullColumns], showHidden, showAll, showMore, moreAll, true);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip, true);
    postMessage({ rows: filteredRows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, columns, commonKeys: updatedCommonKeys, uniqueValues, sortedCells, activeIds });
}

export { };