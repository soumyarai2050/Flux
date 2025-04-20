import { cloneDeep } from 'lodash';
import { MODES } from '../constants';
import {
    applyFilter, getActiveRows, getCommonKeyCollections, getFilteredCells,
    getGroupedTableColumns, getGroupedTableRows, getMaxRowSize,
    getTableColumns
} from '../workerUtils';
import { addxpath, getTableRows, sortColumns, getSortOrdersWithAbs } from '../utils';

onmessage = (e) => {
    const { storedObj, updatedObj, fieldsMetadata, filters, mode, page, rowsPerPage, sortOrders,
        enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll, xpath, columnOrders, absoluteSortOverride
    } = e.data;
    const rows = getTableRows(fieldsMetadata, mode, storedObj, addxpath(cloneDeep(updatedObj)), xpath);
    const filteredRows = applyFilter(rows, filters);
    const groupedRows = getGroupedTableRows(filteredRows, [], null);
    const sortOrdersWithAbs = getSortOrdersWithAbs(sortOrders, absoluteSortOverride);
    const activeRows = getActiveRows(groupedRows, page, rowsPerPage, sortOrdersWithAbs, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const columns = getTableColumns(fieldsMetadata, mode, enableOverride, disableOverride, showLess, absoluteSortOverride);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, [], mode, false);  // headCells
    let commonKeys;
    if (mode === MODES.EDIT) {
        commonKeys = [];
    } else {
        commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, false, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, false, false, false, false);
    postMessage({ rows: filteredRows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, sortedCells });
}

export { };