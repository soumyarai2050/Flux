import _, { cloneDeep } from 'lodash';
import { DB_ID, DataTypes } from './constants';

const FLOAT_POINT_PRECISION = 2;

export function applyFilter(arr, filters = []) {
    if (arr && arr.length > 0) {
        let updatedArr = cloneDeep(arr);
        const filterDict = getFilterDict(filters);
        Object.keys(filterDict).forEach(key => {
            let values = filterDict[key].split(',').map(val => val.trim()).filter(val => val !== '');
            updatedArr = updatedArr.filter(data => values.includes(String(_.get(data, key))));
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
    const rows = [];
    if (items) {
        items.map((item, i) => {
            let row = {};
            // integer id field of item
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            row['data-id'] = id;
            itemProps.forEach(c => {
                let value;
                let metadata = itemsDataDict[c.source].find(meta => _.get(meta, DB_ID) === id);
                if (c.xpath.indexOf("-") !== -1) {
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
        })
    }
    return rows;
}

export function getActiveRows(rows, page, pageSize, order, orderBy) {
    return stableSort(rows, getComparator(order, orderBy))
        .slice(page * pageSize, page * pageSize + pageSize);
}

export function getComparator(order, orderBy) {
    return order === 'desc'
        ? (a, b) => descendingComparator(a, b, orderBy)
        : (a, b) => -descendingComparator(a, b, orderBy);
}

export function descendingComparator(a, b, orderBy) {
    if (a[orderBy] === undefined || a[orderBy] === null) {
        return -1;
    }
    if (b[orderBy] === undefined || b[orderBy] === null) {
        return 1;
    }
    if (b[orderBy] < a[orderBy]) {
        return -1;
    }
    if (b[orderBy] > a[orderBy]) {
        return 1;
    }
    return 0;
}

export function getIdFromAbbreviatedKey(abbreviated, abbreviatedKey) {
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

export function applyGetAllWebsocketUpdate(arr, obj, uiLimit) {
    const index = arr.findIndex(o => o[DB_ID] === obj[DB_ID]);
    let updatedArr = arr.filter(o => o[DB_ID] !== obj[DB_ID]);
    // if obj is not deleted object
    if (Object.keys(obj) !== 1) {
        // if index is not equal to -1, it is updated obj. If updated, replace the obj at the index
        if (index !== -1) {
            updatedArr.splice(index, 0, obj);
        } else {
            updatedArr.push(obj);
        }
    }
    return updatedArr;
}