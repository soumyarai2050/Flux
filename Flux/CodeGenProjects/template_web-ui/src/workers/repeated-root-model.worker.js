import { cloneDeep } from 'lodash';
import { DB_ID, MODES } from '../constants';
import {
    applyFilter, getActiveRows, getCommonKeyCollections, getFilteredCells,
    getGroupedTableColumns, getGroupedTableRows, getMaxRowSize,
    getTableColumns
} from '../workerUtils';
import { addxpath, getTableRows, sortColumns } from '../utils';

onmessage = (e) => {
    const { storedArray, updatedObj, fieldsMetadata, filters, mode, page, rowsPerPage, sortOrders,
        joinBy, joinSort, enableOverride, disableOverride, showLess, showHidden, showAll, showMore, moreAll,
        columnOrders, centerJoin, flip
    } = e.data;
    const filteredArray = applyFilter(storedArray, filters);
    const clonedArray = addxpath(cloneDeep(filteredArray));
    const updatedArray = clonedArray.map((o) => o[DB_ID] === updatedObj[DB_ID] ? updatedObj : o);
    const rows = getTableRows(fieldsMetadata, mode, filteredArray, updatedArray, null, true);
    const groupedRows = getGroupedTableRows(rows, joinBy, joinSort);
    const activeRows = getActiveRows(groupedRows, page, rowsPerPage, sortOrders, true);
    const maxRowSize = getMaxRowSize(activeRows);
    const columns = getTableColumns(fieldsMetadata, mode, enableOverride, disableOverride, showLess, false, true);  // not used externally
    const groupedColumns = getGroupedTableColumns(columns, maxRowSize, groupedRows, joinBy, mode, false);  // headCells
    if (mode === MODES.EDIT) {
        var commonKeys = [];
    } else {
        var commonKeys = getCommonKeyCollections(activeRows, groupedColumns, !showHidden && !showAll, false, true, !showMore && !moreAll);
    }
    const cells = getFilteredCells(groupedColumns, commonKeys, showHidden, showAll, showMore, moreAll);
    const sortedCells = sortColumns(cells, columnOrders, joinBy && joinBy.length > 0, centerJoin, flip);
    postMessage({ rows, groupedRows, activeRows, maxRowSize, headCells: groupedColumns, commonKeys, sortedCells });
}

export { };