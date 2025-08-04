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
        enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll,
        columnOrders, frozenColumns, columnNameOverride, highlightUpdateOverride, noCommonKeyOverride
    } = e.data;
    const rows = getTableRows(fieldsMetadata, mode, storedObj, addxpath(cloneDeep(updatedObj)));
    const uniqueValues = getUniqueValues(rows, fieldsMetadata.filter((meta) => meta.filterEnable));
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, [], null);
    const { sortedRows, activeRows } = getActiveRows(groupedRows, page, rowsPerPage, sortOrders, true);
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
    const cells = getFilteredCells(groupedColumns, [...commonKeys, ...nullColumns], showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, false, false, false, false);
    postMessage({ rows: filteredRows, groupedRows: sortedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, uniqueValues, sortedCells });
}

export { };