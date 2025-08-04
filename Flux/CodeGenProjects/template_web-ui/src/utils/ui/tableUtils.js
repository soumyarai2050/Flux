import { get, cloneDeep } from 'lodash';
import { COLOR_TYPES, DB_ID, DATA_TYPES, MODES } from '../../constants';
import { SortComparator } from '../core/sortUtils';
import { stableSort } from '../core/dataSorting';
import { getLocalizedValueAndSuffix } from '../formatters/numberUtils';
import { getIdFromAbbreviatedKey } from '../core/dataUtils';
import { getColorTypeFromValue } from './colorUtils';
import { generateRowTrees, generateRowsFromTree, addxpath } from '../core/dataAccess';


/**
 * Generates table rows from abbreviated data, enriching them with metadata and localized values.
 * This function processes a list of abbreviated keys and their corresponding data to construct
 * a structured array of rows suitable for display in a table.
 *
 * @param {Array<string>} items - A list of abbreviated keys, each representing a unique item.
 * @param {Object} itemsDataDict - A dictionary where keys are source identifiers and values are arrays of metadata objects.
 * @param {Array<Object>} itemProps - An array of objects describing the properties of each item, including their source and display type.
 * @param {string} abbreviation - The abbreviation syntax used to derive item IDs.
 * @param {Object} loadedProps - Additional properties that might influence how values are processed or displayed, e.g., `microSeparator`.
 * @returns {Array<Object>} An array of row objects, each containing `data-id` and other processed fields.
 */
export function getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps) {
    let rows = [];
    if (items && items.length > 0) {
        items.map((item, i) => {
            let row = {};
            // integer id field of item
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            row['data-id'] = id;
            itemProps.forEach(c => {
                let value;
                let metadata = itemsDataDict[c.source].find(meta => get(meta, DB_ID) === id);
                if (c.type === 'alert_bubble') {
                    let color = COLOR_TYPES.DEFAULT;
                    if (c.colorSource) {
                        const severityType = get(metadata, c.colorSource);
                        color = getColorTypeFromValue(c.colorCollection, severityType);
                    }
                    let fldValue = get(metadata, c.xpath);
                    if (Array.isArray(fldValue)) {
                        fldValue = fldValue.length;
                    }
                    value = [fldValue, color];
                } else if (c.xpath === DB_ID) {
                    value = id;
                } else if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.find(col => col.tableTitle === xpath);
                        let val = get(metadata, xpath);
                        if (val === undefined || val === null) {
                            val = "";
                        }
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                        if (typeof v === DATA_TYPES.NUMBER && collection.type === DATA_TYPES.NUMBER) {
                            v = v.toLocaleString();
                        }
                        if (v === '') {
                            val = undefined;
                        } else {
                            val = v + numberSuffix;
                        }
                        return val;
                    })
                    value = value.filter(x => typeof x === DATA_TYPES.STRING && x.length > 0);
                    if (loadedProps.microSeparator) {
                        value = value.join(loadedProps.microSeparator);
                    } else {
                        value = value.join("-");
                    }
                    if (value === '') {
                        value = undefined;
                    }
                } else {
                    value = get(metadata, c.xpath);
                    let [, v] = getLocalizedValueAndSuffix(c, value);
                    value = v;
                }
                row[c.key] = value;
            })
            rows.push(row);
            return;
        })
    }
    return rows;
}


/**
 * Retrieves a subset of rows for display based on pagination and sorting parameters.
 * This function sorts the provided rows and then slices them to return only the active (visible) rows
 * for the current page, along with the fully sorted set of rows.
 *
 * @param {Array<Object>} rows - The array of row objects to be sorted and paginated.
 * @param {number} page - The current page number (0-indexed).
 * @param {number} pageSize - The number of rows to display per page.
 * @param {Array<Object>} sortOrders - An array of objects defining the sorting criteria (e.g., field, direction).
 * @param {boolean} [nestedArray=false] - Indicates whether the rows contain nested arrays that require special sorting.
 * @returns {{sortedRows: Array<Object>, activeRows: Array<Object>}} An object containing the full sorted rows and the active rows for the current page.
 */
export function getActiveRows(rows, page, pageSize, sortOrders, nestedArray = false) {
    const sortedRows = stableSort(rows, SortComparator.getInstance(sortOrders, nestedArray));
    const activeRows = sortedRows.slice(page * pageSize, page * pageSize + pageSize);
    return { sortedRows, activeRows };
}


/**
 * Generates table rows from raw data based on a collection of metadata and a specified XPath.
 * This function first generates row trees from the data and then flattens them into a list of rows.
 *
 * @param {Array<Object>} collections - An array of collection metadata objects, defining the structure and types of data.
 * @param {Object} data - The raw data object from which to generate table rows.
 * @param {string} xpath - The XPath expression used to navigate and extract data from the `data` object.
 * @returns {Array<Object>} An array of table row objects.
 */
export function getTableRowsFromData(collections, data, xpath) {
    let trees = generateRowTrees(cloneDeep(data), collections, xpath);
    let rows = generateRowsFromTree(trees, collections, xpath);
    return rows;
}


/**
 * Retrieves table rows based on the current mode (read or edit) and data. This function handles
 * combining original and modified data rows for edit mode to show additions and removals.
 *
 * @param {Array<Object>} collections - An array of collection metadata objects.
 * @param {string} mode - The current mode, either `MODES.READ` or `MODES.EDIT`.
 * @param {Object} originalData - The original, unmodified data object.
 * @param {Object} data - The current (potentially modified) data object.
 * @param {string} xpath - The XPath expression for data extraction.
 * @param {boolean} [repeatedView=false] - Indicates if the view is a repeated view.
 * @returns {Array<Object>} An array of table row objects, potentially including `data-remove` or `data-add` flags.
 */
export function getTableRows(collections, mode, originalData, data, xpath, repeatedView = false) {
    let tableRows = [];
    if (mode === MODES.READ) {
        if (repeatedView) {
            tableRows = getTableRowsFromData(collections, data, xpath);
        } else {
            tableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
        }
    } else {
        let originalDataTableRows = getTableRowsFromData(collections, addxpath(cloneDeep(originalData)), xpath);
        tableRows = getTableRowsFromData(collections, data, xpath);

        // combine the original and modified data rows
        for (let i = 0; i < originalDataTableRows.length; i++) {
            if (i < tableRows.length) {
                if (originalDataTableRows[i]['data-id'] !== tableRows[i]['data-id']) {
                    if (!tableRows.find(row => row['data-id'] === originalDataTableRows[i]['data-id'])) {
                        let row = originalDataTableRows[i];
                        row['data-remove'] = true;
                        tableRows.splice(i, 0, row);
                    }
                }
            } else {
                let row = originalDataTableRows[i];
                row['data-remove'] = true;
                tableRows.splice(i, 0, row);
            }
        }
        for (let i = 0; i < tableRows.length; i++) {
            if (!originalDataTableRows.find(row => row['data-id'] === tableRows[i]['data-id'])) {
                tableRows[i]['data-add'] = true;
            }
        }
    }
    return tableRows;
}


/**
 * Identifies and returns common key collections from a set of rows and table columns.
 * This function is used to determine which columns have common values across multiple rows,
 * which can be useful for displaying aggregated or summarized information.
 *
 * @param {Array<Object>} rows - An array of row objects from which to find common keys.
 * @param {Array<Object>} tableColumns - An array of column definition objects.
 * @param {boolean} [hide=true] - If true, columns marked as `hide` will be excluded.
 * @param {boolean} [collectionView=false] - If true, adjusts behavior for collection views.
 * @param {boolean} [repeatedView=false] - If true, adjusts behavior for repeated views.
 * @param {boolean} [showLess=false] - If true, columns marked as `showLess` will be excluded.
 * @returns {Array<Object>} An array of column definition objects that have common keys across the rows.
 */
export function getCommonKeyCollections(rows, tableColumns, hide = true, collectionView = false, repeatedView = false, showLess = false) {
    const filteredColumns = tableColumns
        .filter((column) => {
            // if (column.noCommonKeyDeduced) return false;
            if (hide && column.hide) return false;
            if (showLess && column.showLess) return false;
            if (column.joinKey || column.commonGroupKey) return false;
            return true;
        })
        .map((column) => Object.assign({}, column));

    const commonKeyColumns = [];
    const nullColumns = [];

    if (!rows || rows.length === 0) return [commonKeyColumns, nullColumns];

    filteredColumns.forEach((column) => {
        const keyField = collectionView ? column.key : column.tableTitle;
        if (rows.length === 1) {
            if (['button', 'progressBar', 'alert_bubble'].includes(column.type) && collectionView) return false;

            const value = rows[0][column.sourceIndex]?.[keyField];
            column.value = value;
            commonKeyColumns.push(column);
        } else {
            if (['button', 'progressBar', 'alert_bubble'].includes(column.type) && !column.rootLevel) return;

            const valueSet = new Set();
            for (let i = 0; i < rows.length; i++) {
                const value = rows[i][column.sourceIndex]?.[keyField];
                if (value == null || value === '') {
                    valueSet.add(null);
                } else {
                    // non-null value found
                    if (value === 0 && column.zeroAsNone) {
                        valueSet.add(null);
                    } else {
                        valueSet.add(value);
                    }
                }
                if (valueSet.size > 1) {
                    break;
                }
            }
            if (valueSet.size > 1) return;

            const value = valueSet.size === 1 ? [...valueSet][0] : null;
            column.value = value;
            if (value === null || value === undefined) {
                nullColumns.push(column);
            } else {
                if (!column.noCommonKeyDeduced) {
                    commonKeyColumns.push(column);
                }
            }
        }
    })
    return [commonKeyColumns, nullColumns];

    // if (rows.length > 1 || (rows.length === 1 && (collectionView || repeatedView))) {
    //     // exclude column with 'noCommonKey' as it cannot be added in common key
    //     tableColumns = tableColumns.map(column => Object.assign({}, column)).filter(column => !column.noCommonKeyDeduced);
    // }
    // let commonKeyCollections = [];
    // if (rows.length === 1 && (collectionView || repeatedView)) {
    //     const hasButtonType = tableColumns.find(obj => obj.type === 'button');
    //     if (hasButtonType) {
    //         tableColumns.forEach((column) => {
    //             if (hide && column.hide) return;
    //             if (column.joinKey || column.commonGroupKey) return;
    //             if (showLess && column.showLess) return;
    //             let fieldName = column.tableTitle;
    //             if (collectionView) {
    //                 if ((column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
    //                     return;
    //                 }
    //                 fieldName = column.key;
    //             }
    //             const value = rows[0][column.sourceIndex]?.[fieldName];
    //             if (!column.noCommonKeyDeduced) {
    //                 if (value === null || value === undefined) {
    //                     commonKeyCollections.push(column);
    //                 } else if (value === 0 && !column.displayZero) {
    //                     commonKeyCollections.push(column);
    //                 }
    //             }
    //         })
    //         return commonKeyCollections;
    //     }
    // }
    // if (rows.length > 0) {
    //     tableColumns.map((column) => {
    //         if (hide && column.hide) return;
    //         if (column.joinKey || column.commonGroupKey) return;
    //         if (showLess && column.showLess) return;
    //         let fieldName = column.tableTitle;
    //         if (collectionView) {
    //             if (rows.length > 1 && (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
    //                 return;
    //             }
    //             fieldName = column.key;
    //         }
    //         let found = true;
    //         let firstValue = null;
    //         for (let i = 0; i < rows.length; i++) {
    //             const value = rows[i][column.sourceIndex]?.[fieldName];
    //             if (!(value === null || value === undefined || value === '')) {
    //                 firstValue = value;
    //                 break;
    //             }
    //         }
    //         for (let i = 0; i < rows.length; i++) {
    //             const value = rows[i][column.sourceIndex]?.[fieldName];
    //             if (value !== firstValue && firstValue !== null) {
    //                 if (column.type === DATA_TYPES.NUMBER && column.zeroAsNone && firstValue === 0 && value === null) {
    //                     continue;
    //                 } else {
    //                     found = false;
    //                     break;
    //                 }
    //             }
    //             if (!found) {
    //                 break;
    //             }
    //         }
    //         if (found) {
    //             let collection = column;
    //             collection.value = firstValue;
    //             commonKeyCollections.push(collection);
    //         }
    //         return column;
    //     })
    // }
    // return commonKeyCollections;
}


/**
 * Groups table columns based on specified criteria, primarily for read mode with grouping enabled.
 * This function duplicates columns for each row in a grouped view and then filters them
 * to show common columns only once.
 *
 * @param {Array<Object>} columns - An array of column definition objects.
 * @param {number} maxRowSize - The maximum number of rows in a group.
 * @param {Array<Object>} rows - The data rows, potentially grouped.
 * @param {Array<string>} [groupBy=[]] - An array of field names to group by.
 * @param {string} mode - The current mode, e.g., `MODES.READ`.
 * @param {boolean} [collectionView=false] - Indicates if the view is a collection view.
 * @returns {Array<Object>} An array of grouped table column objects.
 */
export function getGroupedTableColumns(columns, maxRowSize, rows, groupBy = [], mode, collectionView = false) {
    let tableColumns = []
    let maxSequence = 0;
    columns.forEach(column => {
        if (column.sequenceNumber > maxSequence) {
            maxSequence = column.sequenceNumber;
        }
    })
    for (let i = 0; i < maxRowSize; i++) {
        const updatedColumns = columns.map(column => {
            column = Object.assign({}, column);
            column.sourceIndex = i;
            column.sequenceNumber = column.sequenceNumber + i * maxSequence;
            return column;
        })
        tableColumns = [...tableColumns, ...updatedColumns];
    }
    if (mode === MODES.READ && groupBy && groupBy.length > 0) {
        const commonColumns = [];
        columns.forEach(column => {
            if (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble') {
                return;
            }
            if (column.noCommonKeyDeduced) {
                return;
            }
            let fieldName = column.tableTitle;
            if (collectionView) {
                fieldName = column.key;
            }
            let found = true;
            for (let i = 0; i < rows.length; i++) {
                const groupedRow = rows[i];
                let firstValue = null;
                for (let j = 0; j < maxRowSize; j++) {
                    const value = groupedRow?.[j]?.[fieldName];
                    if (!(value === null || value === undefined || value === '')) {
                        firstValue = value;
                        break;
                    }
                }
                let matched = true;
                for (let j = 0; j < groupedRow.length; j++) {
                    const value = groupedRow[j][fieldName];
                    if (!(value === null || value === undefined || value === '')) {
                        if (value !== firstValue) {
                            matched = false;
                            break;
                        }
                    }
                }
                if (!matched) {
                    found = false;
                    break;
                }
            }
            if (found) {
                commonColumns.push(fieldName);
            }
        })
        tableColumns = tableColumns.filter(column => {
            let fieldName = column.tableTitle;
            if (collectionView) {
                fieldName = column.key;
            }
            if (commonColumns.includes(fieldName) && column.sourceIndex !== 0) {
                // exclude all common columns from non-zeroth source index
                return false;
            }
            return true;
        })
        tableColumns = tableColumns.map(column => {
            let fieldName = column.tableTitle;
            if (collectionView) {
                fieldName = column.key;
            }
            if (commonColumns.includes(fieldName)) {
                column.commonGroupKey = true;
            }
            if (groupBy.includes(fieldName)) {
                column.joinKey = true;
            }
            return column;
        })
    }
    return tableColumns;
}


/**
 * Processes and returns a list of table column definitions based on metadata and override properties.
 * This function applies various overrides such as enabling/disabling columns, setting display names,
 * and handling frozen columns, ensuring the columns are configured correctly for the UI.
 *
 * @param {Array<Object>} fieldsMetadata - An array of metadata objects for the fields.
 * @param {string} mode - The current mode, e.g., `MODES.EDIT`.
 * @param {Object} [overrideProps={}] - An object containing various override properties for columns.
 * @param {Array<string>} [overrideProps.enableOverride=[]] - List of field names to enable (show).
 * @param {Array<string>} [overrideProps.disableOverride=[]] - List of field names to disable (hide).
 * @param {Array<string>} [overrideProps.showLess=[]] - List of field names to mark as 'show less'.
 * @param {Array<string>} [overrideProps.frozenColumns=[]] - List of field names for frozen columns.
 * @param {Array<string>} [overrideProps.columnNameOverride=[]] - List of 'name:override' strings for column name overrides.
 * @param {Array<string>} [overrideProps.highlightUpdateOverride=[]] - List of 'name:override' strings for highlight update overrides.
 * @param {Array<string>} [overrideProps.noCommonKeyOverride=[]] - List of field names for no common key overrides.
 * @param {boolean} [collectionView=false] - Indicates if the view is a collection view.
 * @param {boolean} [repeatedView=false] - Indicates if the view is a repeated view.
 * @returns {Array<Object>} An array of processed table column objects.
 */
export function getTableColumns(fieldsMetadata, mode, overrideProps = {}, collectionView = false, repeatedView = false) {
    const {
        enableOverride = [],
        disableOverride = [],
        showLess = [],
        frozenColumns = [],
        columnNameOverride = [],
        highlightUpdateOverride = [],
        noCommonKeyOverride = []
    } = overrideProps;
    const columnNameOverrideDict = columnNameOverride.reduce((acc, item) => {
        const [name, override] = item.split(':');
        acc[name] = override;
        return acc;
    }, {});
    const highlightUpdateOverrideDict = highlightUpdateOverride.reduce((acc, item) => {
        const [name, override] = item.split(':');
        acc[name] = override;
        return acc;
    }, {});
    let tableColumns = fieldsMetadata
        .map(collection => Object.assign({}, collection))
        .map(collection => {
            let fieldName = collection.tableTitle;
            if (collectionView) {
                fieldName = collection.key;
            }
            if (enableOverride.includes(fieldName)) {
                collection.hide = true;
            }
            if (disableOverride.includes(fieldName)) {
                collection.hide = false;
            }
            if (showLess.includes(fieldName)) {
                collection.showLess = true;
            }
            if (frozenColumns.includes(fieldName)) {
                collection.frozenColumn = true;
            } else {
                delete collection.frozenColumn;
            }
            if (columnNameOverrideDict[fieldName]) {
                collection.displayName = columnNameOverrideDict[fieldName];
            }
            if (highlightUpdateOverrideDict[fieldName]) {
                collection.highlightUpdate = highlightUpdateOverrideDict[fieldName];
            }
            if (collection.noCommonKey) {
                collection.noCommonKeyDeduced = true;
            }
            if (noCommonKeyOverride.includes(fieldName)) {
                if (collection.noCommonKey) {
                    collection.noCommonKeyDeduced = false;
                } else {
                    collection.noCommonKeyDeduced = true;
                }
            }
            if (repeatedView) {
                collection.rootLevel = false;
            }
            return collection;
        })
        .filter(collection => {
            // add all exclusion cases
            if (mode === MODES.EDIT) {
                if (collection.serverPopulate) return false;
                if (collection.type === 'button' && !collection.rootLevel && collection.button.read_only) return false;
            }
            if ((collection.type === 'object' || collection.type === 'array') && collection.abbreviated !== 'JSON') return false;
            return true;
        })

    return tableColumns;
}


/**
 * Filters a list of head cells based on visibility flags and common keys.
 * This function is used to dynamically show or hide columns in a table based on user preferences
 * or application logic, such as showing only non-hidden cells or excluding common keys.
 *
 * @param {Array<Object>} headCells - An array of head cell objects, each representing a column header.
 * @param {Array<Object>} commonKeys - An array of common key objects, used to filter out cells that are considered common.
 * @param {boolean} showHidden - If true, hidden cells will be shown.
 * @param {boolean} showAll - If true, all cells will be shown, overriding `showHidden`.
 * @param {boolean} showMore - If true, cells marked as 'show less' will be shown.
 * @param {boolean} moreAll - If true, all cells will be shown, overriding `showMore`.
 * @param {boolean} [isAbbreviationMerge=false] - If true, uses 'key' as the field for comparison; otherwise, uses 'tableTitle'.
 * @returns {Array<Object>} An array of filtered head cell objects.
 */
export function getFilteredCells(headCells, commonKeys, showHidden, showAll, showMore, moreAll, isAbbreviationMerge = false) {
    let updatedCells = cloneDeep(headCells);
    if (!showHidden && !showAll) {
        updatedCells = updatedCells.filter(cell => !cell.hide);
    }
    if (!showMore && !moreAll) {
        updatedCells = updatedCells.filter(cell => !cell.showLess);
    }
    const fieldKey = isAbbreviationMerge ? 'key' : 'tableTitle';
    updatedCells = updatedCells.filter(cell => commonKeys.filter(c => c[fieldKey] === cell[fieldKey] && c.sourceIndex === cell.sourceIndex).length === 0)
    return updatedCells;
}