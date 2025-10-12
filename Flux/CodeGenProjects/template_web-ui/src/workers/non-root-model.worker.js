import { cloneDeep } from 'lodash';
import { MODES } from '../constants';
import { applyFilter } from '../utils/core/dataFiltering';
import {
    getActiveRows, getCommonKeyCollections, getFilteredCells, getGroupedTableColumns,
    getTableColumns, getTableRows
} from '../utils/ui/tableUtils';
import { getGroupedTableRows, getMaxRowSize } from '../utils/core/dataGrouping';
import { addxpath } from '../utils/core/dataAccess';
import { sortColumns, getSortOrdersWithAbs, getUniqueValues } from '../utils/ui/uiUtils';

onmessage = (e) => {
    const { storedObj, updatedObj, fieldsMetadata, filters, mode, page, rowsPerPage, sortOrders,
        enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll, xpath,
        columnOrders, frozenColumns, columnNameOverride, highlightUpdateOverride, noCommonKeyOverride,serverSidePaginationEnabled
    } = e.data;
    const rows = getTableRows(fieldsMetadata, mode, storedObj, addxpath(cloneDeep(updatedObj)), xpath);
    const filterFieldsMetadata = fieldsMetadata.filter((meta) => meta.filterEnable);
    const filterAppliedFields = new Set(filters?.map((o) => o.column_name) ?? []);
    const uniqueValues = getUniqueValues(rows, filterFieldsMetadata);
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, [], null);

    // If server-side pagination is enabled, skip client-side pagination slice
    // The storedObj already contains only the data for the current page
    const { sortedRows, activeRows } = serverSidePaginationEnabled
        ? getActiveRows(groupedRows, 0, rowsPerPage, sortOrders, true)
        : getActiveRows(groupedRows, page, rowsPerPage, sortOrders, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const columns = getTableColumns(fieldsMetadata, mode, {
        enableOverride,
        disableOverride,
        showLess,
        frozenColumns,
        columnNameOverride,
        highlightUpdateOverride,
        noCommonKeyOverride,
    });  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, [], mode, false);  // headCells
    let commonKeys;
    let nullColumns;
    if (mode === MODES.EDIT) {
        commonKeys = [];
        nullColumns = [];
    } else {
        [commonKeys, nullColumns] = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, false, !showMore && !moreAll);
    }
    const updatedCommonKeys = commonKeys.filter((o) => !filterAppliedFields.has(o.tableTitle));
    const cells = getFilteredCells(groupedColumns, [...updatedCommonKeys, ...nullColumns], showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, false, false, false, false);
    postMessage({ rows: filteredRows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys: updatedCommonKeys, uniqueValues, sortedCells });
}

export { };