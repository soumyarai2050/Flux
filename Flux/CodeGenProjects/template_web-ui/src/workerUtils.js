import _, { cloneDeep } from 'lodash';
import { ColorTypes, DB_ID, DataTypes, SeverityType } from './constants';
import { SortComparator } from './utility/sortComparator';

const FLOAT_POINT_PRECISION = 2;

export function applyFilter(arr, filters = [], grouped = false) {
    if (arr && arr.length > 0) {
        let updatedArr = cloneDeep(arr);
        const filterDict = getFilterDict(filters);
        Object.keys(filterDict).forEach(key => {
            let values = filterDict[key].split(',').map(val => val.trim()).filter(val => val !== '');
            if (grouped) {
                updatedArr = updatedArr.filter(a => {
                    a = a.filter(obj => values.includes(String(_.get(obj, key))));
                    return a.length === 0;
                })
            } else {
                updatedArr = updatedArr.filter(data => values.includes(String(_.get(data, key))));
            }
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
    if (typeof value === DataTypes.NUMBER) {
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

    if (typeof value !== DataTypes.NUMBER) {
        return [adornment, value];
    }
    if (metadata.numberFormat) {
        if (metadata.numberFormat.includes('%')) {
            adornment = ' %';
        } else if (metadata.numberFormat.includes('bps')) {
            adornment = ' bps';
        }
    }
    if (metadata.displayType === DataTypes.INTEGER) {
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
    if (typeof value === DataTypes.NUMBER) {
        if (Number.isInteger(value) || precision === 0) {
            return value;
        } else {
            return +value.toFixed(precision);
        }
    }
    return value;
}

export function getAbbreviatedRows(items, itemsDataDict, itemProps, abbreviation, loadedProps) {
    /* 
        items: list of abbreviated keys built from it's abbreviated dependent fields
        itemsData: list of abbreviated dependent data for each abbreviated keys
        itemProps: list of abbreviated dependent fields and their attributes
        abbreviation: abbreviation syntax
    */
    let rows = [];
    if (items) {
        items.map((item, i) => {
            let row = {};
            // integer id field of item
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            row['data-id'] = id;
            itemProps.forEach(c => {
                let value;
                let metadata = itemsDataDict[c.source].find(meta => _.get(meta, DB_ID) === id);
                if (c.type === 'alert_bubble') {
                    let color = ColorTypes.DEFAULT;
                    if (c.colorSource) {
                        const severityType = _.get(metadata, c.colorSource);
                        color = getColorTypeFromValue(c.colorCollection, severityType);
                    }
                    value = [_.get(metadata, c.xpath), color];
                } else if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.filter(col => col.tableTitle === xpath)[0];
                        let val = _.get(metadata, xpath);
                        if (val === undefined || val === null) {
                            val = "";
                        }
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                        if (typeof v === DataTypes.NUMBER && collection.type === DataTypes.NUMBER) {
                            v = v.toLocaleString();
                        }
                        if (v === '') {
                            val = undefined;
                        } else {
                            val = v + numberSuffix;
                        }
                        return val;
                    })
                    value = value.filter(x => typeof x === DataTypes.STRING && x.length > 0);
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

export function getActiveRows(rows, page, pageSize, sortOrders) {
    return stableSort(rows, SortComparator.getInstance(sortOrders))
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
                            if (SeverityType[updatedObj.severity] > SeverityType[updatedArray[updatedArray.length - 1].severity]) {
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
        const severityA = SeverityType[a.severity];
        const severityB = SeverityType[b.severity];
        if (severityA > severityB) {
            return -1;
        } else if (severityB > severityA) {
            return 1;
        } else {  // same severity
            if (a.last_update_analyzer_time >= b.last_update_analyzer_time) {
                return -1;
            } else {
                return 1;
            }
        }
    })
    return alertArray;
}

export function getColorTypeFromValue(collection, value, separator = '-') {
    let color = ColorTypes.DEFAULT;
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
                    const color = ColorTypes[valueColorMap[v]];
                    return color;
                }
            }
        } else if (valueColorMap.hasOwnProperty(v)) {
            const color = ColorTypes[valueColorMap[v]];
            return color;
        }
    }
    return color;
}

export function getGroupedTableRows(tableRows, groupBy, joinSortOrders = null) {
    if (groupBy && groupBy.length > 0) {
        tableRows = Object.values(_.groupBy(tableRows, item => {
            const groupKeys = [];
            groupBy.forEach(groupingField => {
                groupKeys.push(_.get(item, groupingField));
            })
            return groupKeys.join('_');
        }));
        if (joinSortOrders && joinSortOrders.length > 0) {
            tableRows = tableRows.map(rows => stableSort(rows, SortComparator.getInstance(joinSortOrders)));
        }
    } else {
        tableRows = tableRows.map(row => [row]);
    }
    return tableRows;
}