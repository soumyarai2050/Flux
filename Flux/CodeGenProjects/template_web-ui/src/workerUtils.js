import _, { cloneDeep } from 'lodash';
import { COLOR_TYPES, DB_ID, DATA_TYPES, SEVERITY_TYPES, MODES } from './constants';
import { SortComparator, SortType } from './utility/sortComparator';

const FLOAT_POINT_PRECISION = 2;

export function applyFilter(arr, filters = []) {
    if (arr && arr.length > 0) {
        let updatedArr = cloneDeep(arr);
        const filterDict = getFilterDict(filters);
        Object.keys(filterDict).forEach(key => {
            let values = filterDict[key].split(',').map(val => val.trim()).filter(val => val !== '');
            updatedArr = updatedArr.filter(obj => {
                let objValue = _.get(obj, key);
                if (objValue === null || objValue === undefined || objValue === '') {
                    // obj key is unset, filter the obj
                    return false;
                }
                // filter is set
                objValue = String(objValue).toLowerCase();
                return values.some(value => objValue.includes(value.toLowerCase()));
            });
        })
        return updatedArr;
    }
    return [];
}

export function getFilterDict(filters) {
    const filterDict = {};
    if (filters) {
        filters.forEach(filter => {
            if (filter.fld_value) {
                filterDict[filter.fld_name] = filter.fld_value;
            }
        })
    }
    return filterDict;
}

export function stableSort(array, comparator) {
    const stabilizedThis = array.map((el, index) => [el, index]);
    stabilizedThis.sort((a, b) => {
        const order = comparator(a[0], b[0]);
        if (order !== 0) {
            return order;
        }
        return a[1] - b[1];
    });
    return stabilizedThis.map((el) => el[0]);
}

export function floatToInt(value) {
    /*
    Function to convert floating point numbers to integer.
    value: integer or floating point number
    */
    if (typeof value === DATA_TYPES.NUMBER) {
        if (Number.isInteger(value)) {
            return value;
        } else {
            // floating point number
            if (value > 0) {
                return Math.floor(value);
            } else {
                return Math.ceil(value);
            }
        }
    }
    return value;
}

export function getLocalizedValueAndSuffix(metadata, value) {
    /*
    Function to normalize numbers and return adornments if any
    metadata: contains all properties of the field
    value: field value
    */
    let adornment = '';

    if (typeof value !== DATA_TYPES.NUMBER) {
        return [adornment, value];
    }
    if (metadata.numberFormat) {
        if (metadata.numberFormat.includes('%')) {
            adornment = ' %';
        } else if (metadata.numberFormat.includes('bps')) {
            adornment = ' bps';
        } else if (metadata.numberFormat.includes('$')) {
            adornment = ' $';
        }
    }
    if (metadata.displayType === DATA_TYPES.INTEGER) {
        return [adornment, floatToInt(value)]
    }
    if (metadata.numberFormat && metadata.numberFormat.includes('.')) {
        let precision = metadata.numberFormat.split(".").pop();
        precision *= 1;
        value = roundNumber(value, precision);
    } else {
        value = roundNumber(value);
    }

    return [adornment, value];
}

export function roundNumber(value, precision = FLOAT_POINT_PRECISION) {
    /*
    Function to round floating point numbers.
    value: floating point number
    precision: decimal digits to round off to. default 2 (FLOAT_POINT_PRECISION)
    */
    if (typeof value === DATA_TYPES.NUMBER) {
        if (Number.isInteger(value) || precision === 0) {
            return value;
        } else {
            return +value.toFixed(precision);
        }
    }
    return value;
}

export function getRowsFromAbbreviation(items, itemsDataDict, itemProps, abbreviation, loadedProps) {
    /* 
        items: list of abbreviated keys built from it's abbreviated dependent fields
        itemsData: list of abbreviated dependent data for each abbreviated keys
        itemProps: list of abbreviated dependent fields and their attributes
        abbreviation: abbreviation syntax
    */
    let rows = [];
    if (items && items.length > 0) {
        items.map((item, i) => {
            let row = {};
            // integer id field of item
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            row['data-id'] = id;
            itemProps.forEach(c => {
                let value;
                let metadata = itemsDataDict[c.source].find(meta => _.get(meta, DB_ID) === id);
                if (c.type === 'alert_bubble') {
                    let color = COLOR_TYPES.DEFAULT;
                    if (c.colorSource) {
                        const severityType = _.get(metadata, c.colorSource);
                        color = getColorTypeFromValue(c.colorCollection, severityType);
                    }
                    value = [_.get(metadata, c.xpath), color];
                } else if (c.xpath === DB_ID) {
                    value = id;
                } else if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.find(col => col.tableTitle === xpath);
                        let val = _.get(metadata, xpath);
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
                    value = _.get(metadata, c.xpath);
                    let [, v] = getLocalizedValueAndSuffix(c, value);
                    value = v;
                }
                row[c.key] = value;
            })
            rows.push(row);
            return;
        })
    }
    // if (groupBy) {
    //     rows = Object.values(_.groupBy(rows, item => {
    //         const groupKeys = [];
    //         groupBy.forEach(groupingField => {
    //             groupKeys.push(_.get(item, groupingField));
    //         })
    //         return groupKeys.join('_');
    //     }));
    // } else {
    //     rows = rows.map(row => [row]);
    // }
    return rows;
}

export function getActiveRows(rows, page, pageSize, sortOrders, nestedArray = false) {
    return stableSort(rows, SortComparator.getInstance(sortOrders, nestedArray))
        .slice(page * pageSize, page * pageSize + pageSize);
}

export function getIdFromAbbreviatedKey(abbreviated, abbreviatedKey) {
    abbreviated = abbreviated.split('^')[0];
    let abbreviatedSplit = abbreviated.split('-');
    let idIndex = -1;
    abbreviatedSplit.map((text, index) => {
        if (text.indexOf(DB_ID) > 0) {
            idIndex = index;
        }
    })
    if (idIndex !== -1) {
        let abbreviatedKeySplit = abbreviatedKey.split('-');
        return parseInt(abbreviatedKeySplit[idIndex]);
    } else {
        // abbreviated key id not found. returning -1
        return idIndex;
    }
}

// export function applyGetAllWebsocketUpdate(arr, obj, uiLimit) {
//     const index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
//     // if index is not equal to -1, object already exists
//     if (index !== -1) {
//         if (Object.keys(obj).length === 1) {
//             // deleted object update. remove the object at the index
//             arr.splice(index, 1);
//         } else {
//             // replace the object with updated object at the index
//             arr.splice(index, 1, obj);
//         }
//     } else {
//         // add the new object to the array
//         arr.push(obj);
//     }
//     return arr;
// }

export function applyGetAllWebsocketUpdate(storedArray, updatedObj, uiLimit, isAlertModel = false) {
    const updatedArray = storedArray.filter(obj => obj[DB_ID] !== updatedObj[DB_ID]);
    // create or update case
    if (Object.keys(updatedObj).length !== 1) {
        const idx = storedArray.findIndex(obj => obj[DB_ID] === updatedObj[DB_ID]);
        // obj with DB_ID already exists. update obj case. update the existing obj at the index
        if (idx !== -1) {
            // ws update received for alert model. if alert is dismissed, return the filtered array
            if (isAlertModel && updatedObj.dismiss) {
                return updatedArray;
            } else {  // either not alert model or alert not dismissed or received ws update on existing obj. 
                updatedArray.splice(idx, 0, updatedObj);
            }
        } else {
            if (uiLimit) {
                // if uiLimit is positive, remove the top object and add the latest obj at the end
                // otherwise remove the last object and add the latest obj at the top
                if (uiLimit >= 0) {
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        updatedArray.shift();
                    }
                    updatedArray.push(updatedObj);
                } else {  // negative uiLimit
                    if (updatedArray.length >= Math.abs(uiLimit)) {
                        if (isAlertModel) {
                            if (SEVERITY_TYPES[updatedObj.severity] > SEVERITY_TYPES[updatedArray[updatedArray.length - 1].severity]) {
                                updatedArray.pop();
                                updatedArray.push(updatedObj);
                            }
                            sortAlertArray(updatedArray);
                            return updatedArray;
                        } else {
                            updatedArray.pop();
                        }
                    }
                    updatedArray.splice(0, 0, updatedObj);
                    return updatedArray;
                }
            } else {
                updatedArray.push(updatedObj);
            }
        }
    }  // else not required - obj is deleted. already filtered above
    return updatedArray;
}

export function sortAlertArray(alertArray) {
    alertArray.sort((a, b) => {
        const severityA = SEVERITY_TYPES[a.severity];
        const severityB = SEVERITY_TYPES[b.severity];
        if (severityA > severityB) {
            return -1;
        } else if (severityB > severityA) {
            return 1;
        } else {  // same severity
            if (a.last_update_analyzer_time > b.last_update_analyzer_time) {
                return -1;
            } else if (b.last_update_analyzer_time > a.last_update_analyzer_time) {
                return 1;
            } else {  // same last update date time
                if (a.alert_count >= b.alert_count) {
                    return -1;
                }
                return 1;
            }
        }
    })
    return alertArray;
}

export function getColorTypeFromValue(collection, value, separator = '-') {
    let color = COLOR_TYPES.DEFAULT;
    if (collection && collection.color) {
        const colorSplit = collection.color.split(',').map(valueColor => valueColor.trim());
        const valueColorMap = {};
        colorSplit.forEach(valueColor => {
            const [val, colorType] = valueColor.split('=');
            valueColorMap[val] = colorType;
        })
        let v = value;
        if (collection.xpath.split('-').length > 1) {
            for (let i = 0; i < collection.xpath.split('-').length; i++) {
                v = value.split(separator)[i];
                if (valueColorMap.hasOwnProperty(v)) {
                    const color = COLOR_TYPES[valueColorMap[v]];
                    return color;
                }
            }
        } else if (valueColorMap.hasOwnProperty(v)) {
            const color = COLOR_TYPES[valueColorMap[v]];
            return color;
        }
    }
    return color;
}

// Function to ensure each inner array is symmetric based on max counts of a specified field
function ensureSymmetry(arr, joinSort) {
    // Step 1: Calculate max counts for the specified field dynamically
    const field = joinSort.sort_order.order_by;
    const sortType = joinSort.sort_order.sort_type;
    const maxCounts = {};

    arr.forEach(innerArr => {
        let innerArrMaxCounts = {};
        innerArr.forEach(obj => {
            let fieldValue = obj[field];
            if (!innerArrMaxCounts.hasOwnProperty(fieldValue)) {
                innerArrMaxCounts[fieldValue] = 0;
            }
            innerArrMaxCounts[fieldValue]++;
        });
        if (maxCounts) {
            Object.keys(innerArrMaxCounts).forEach(key => {
                if (!maxCounts.hasOwnProperty(key) || maxCounts[key] < innerArrMaxCounts[key]) {
                    maxCounts[key] = innerArrMaxCounts[key];
                }
            })
        } else {
            maxCounts = { ...innerArrMaxCounts };
        }
    });
    if (joinSort.placeholders && joinSort.placeholders.length > 0) {
        joinSort.placeholders.forEach(key => {
            if (!maxCounts.hasOwnProperty(key)) {
                maxCounts[key] = 1;
            }
        })
    }

    // Step 2: Ensure symmetry based on max counts
    let grouped = arr.map(innerArr => {
        // Group objects by the specified field
        let groupedObj = {};
        if (sortType === SortType.DESCENDING) {
            Object.keys(maxCounts).sort().reverse().map(key => {
                groupedObj[key] = [];
            })
        } else {
            Object.keys(maxCounts).sort().map(key => {
                groupedObj[key] = [];
            })
        }
        let grouped = innerArr.reduce((acc, obj) => {
            let fieldValue = obj[field];
            if (!acc[fieldValue]) {
                acc[fieldValue] = [];
            }
            acc[fieldValue].push(obj);
            return acc;
        }, groupedObj);

        // Ensure each group has exactly maxCounts[field] objects
        Object.keys(grouped).forEach((key) => {
            let currentLength = grouped[key].length;
            if (currentLength < maxCounts[key]) {
                // Add empty objects to make it symmetric
                for (let i = currentLength; i < maxCounts[key]; i++) {
                    grouped[key].push({});
                }
            }
        });

        // Flatten the grouped objects back into an array
        let result = [];
        Object.keys(grouped).forEach((key) => {
            result.push(...grouped[key]);
        });

        return result;
    });

    return grouped;
}

export function getGroupedTableRows(tableRows, groupBy, joinSort = null) {
    if (groupBy && groupBy.length > 0) {
        // tableRows = Object.values(_.groupBy(tableRows, item => {
        //     const groupKeys = [];
        //     groupBy.forEach(groupingField => {
        //         groupKeys.push(_.get(item, groupingField));
        //     })
        //     return groupKeys.join('_');
        // }));
        const groupedRowsDict = _.groupBy(tableRows, item => {
            const groupKeys = [];
            groupBy.forEach(groupingField => {
                groupKeys.push(_.get(item, groupingField));
            })
            return groupKeys.join('_');
        });
        tableRows = Object.values(groupedRowsDict);

        if (joinSort) {
            tableRows = tableRows.map(rows => stableSort(rows, SortComparator.getInstance([joinSort.sort_order])));
            tableRows = ensureSymmetry(tableRows, joinSort);
        }
    } else {
        tableRows = tableRows.map(row => [row]);
    }
    return tableRows;
}

export function getMaxRowSize(rows) {
    let maxSize = 1;
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].length > maxSize) {
            maxSize = rows[i].length;
        }
    }
    return maxSize;
}

export function getCommonKeyCollections(rows, tableColumns, hide = true, collectionView = false, repeatedView = false, showLess = false) {
    if (rows.length > 1) {
        // exclude column with 'noCommonKey' as it cannot be added in common key
        tableColumns = tableColumns.map(column => Object.assign({}, column)).filter(column => !column.noCommonKey);
    }
    let commonKeyCollections = [];
    if (rows.length === 1 && (collectionView || repeatedView)) {
        const hasButtonType = tableColumns.find(obj => obj.type === 'button');
        if (hasButtonType) {
            tableColumns.forEach(column => {
                if (hide && column.hide) return;
                if (column.joinKey || column.commonGroupKey) return;
                if (showLess && column.showLess) return;
                let fieldName = column.tableTitle;
                if (collectionView) {
                    if (rows.length > 1 && (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
                        return;
                    }
                    fieldName = column.key;
                }
                const value = rows[0][column.sourceIndex]?.[fieldName];
                if (!column.noCommonKey) {
                    if (value === null || value === undefined) {
                        commonKeyCollections.push(column);
                    } else if (value === 0 && !column.displayZero) {
                        commonKeyCollections.push(column);
                    }
                }
            })
            return commonKeyCollections;
        }
    }
    if (rows.length > 0) {
        tableColumns.map((column) => {
            if (hide && column.hide) return;
            if (column.joinKey || column.commonGroupKey) return;
            if (showLess && column.showLess) return;
            let fieldName = column.tableTitle;
            if (collectionView) {
                if (rows.length > 1 && (column.type === 'button' || column.type === 'progressBar' || column.type === 'alert_bubble')) {
                    return;
                }
                fieldName = column.key;
            }
            let found = true;
            let firstValue = null;
            for (let i = 0; i < rows.length; i++) {
                const value = rows[i][column.sourceIndex]?.[fieldName];
                if (!(value === null || value === undefined || value === '')) {
                    firstValue = value;
                    break;
                }
            }
            // const value = rows[0][column.sourceIndex]?.[fieldName];
            // for (let i = 1; i < rows.length; i++) {
            for (let i = 0; i < rows.length; i++) {
                const value = rows[i][column.sourceIndex]?.[fieldName];
                if (value !== firstValue && firstValue !== null) {
                    if (column.type === DATA_TYPES.NUMBER && column.zeroAsNone && firstValue === 0 && value === null) {
                        continue;
                    } else {
                        found = false;
                        break;
                    }
                }
                // if (!(value === null || value === undefined || value === '')) {
                //     if (value !== firstValue) {
                //         found = false;
                //         break;
                //     }
                // }
                // if (rows[i][column.sourceIndex] && rows[i+1][column.sourceIndex]) {
                //     if (!_.isEqual(rows[i][column.sourceIndex][fieldName], rows[i + 1][column.sourceIndex][fieldName])) {
                //         const values = [rows[i][column.sourceIndex][fieldName], rows[i + 1][column.sourceIndex][fieldName]];
                //         for (let i = 0; i < values.length; i++) {
                //             let val = values[i];
                //             if (val) {
                //                 if (typeof val === DATA_TYPES.STRING) {
                //                     val = val.trim();
                //                 }
                //             }
                //             if (![null, undefined, ''].includes(val)) {
                //                 found = false;
                //                 break;
                //             }
                //         }
                //     }
                // }

                // if (rows[i][column.sourceIndex]?.[fieldName] !== value) {
                //     found = false;
                // }

                if (!found) {
                    break;
                }
            }
            if (found) {
                let collection = column;
                collection.value = firstValue;
                commonKeyCollections.push(collection);
            }
            return column;
        })
    }
    return commonKeyCollections;
}

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
            if (column.noCommonKey) {
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

export function getTableColumns(fieldsMetadata, mode, enableOverride = [], disableOverride = [], showLess = [], collectionView = false, repeatedView = false) {
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
            // if (mode === MODES.EDIT && collection.serverPopulate) {
            //     return false;
            // } else if (mode === MODES.EDIT && collection.type === 'button' && collection.button.read_only) {
            //     return false;
            // }

            // if (collection.serverPopulate && mode === MODES.EDIT) {
            //     return false;
            // } else if (primitiveDataTypes.includes(collection.type)) {
            //     return true;
            // } else if (collection.abbreviated && collection.abbreviated === "JSON") {
            //     return true;
            // } else if (collection.type === 'button' && !collection.rootLevel) {
            //     if (mode === MODES.EDIT && collection.button.read_only) {
            //         return false;
            //     }
            //     return true;
            // } else if (collection.type === 'progressBar') {
            //     return true;
            // } else if (collection.type === 'alert_bubble') {
            //     return true;
            // }
            // // TODO: what other cases are ignored?
            // return false;
        })

    return tableColumns;
}

const primitiveDataTypes = [
    DATA_TYPES.STRING,
    DATA_TYPES.BOOLEAN,
    DATA_TYPES.NUMBER,
    DATA_TYPES.ENUM,  // pre-defined set of values in schema.json file
    DATA_TYPES.DATE_TIME,
    DATA_TYPES.INT64,
    DATA_TYPES.FLOAT
];

export function getFilteredCells(headCells, commonKeys, showHidden, showAll, showMore, moreAll) {
    let updatedCells = cloneDeep(headCells);
    if (!showHidden && !showAll) {
        updatedCells = updatedCells.filter(cell => !cell.hide);
    }
    if (!showMore && !moreAll) {
        updatedCells = updatedCells.filter(cell => !cell.showLess);
    }
    updatedCells = updatedCells.filter(cell => commonKeys.filter(c => c.key === cell.key && c.sourceIndex === cell.sourceIndex).length === 0)
    return updatedCells;
}
