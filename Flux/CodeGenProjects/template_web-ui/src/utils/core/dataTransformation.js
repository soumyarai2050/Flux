import { get } from 'lodash';
import { DB_ID, DATA_TYPES } from '../../constants';
import { getLocalizedValueAndSuffix } from '../formatters/numberUtils';
import { getIdFromAbbreviatedKey } from './dataUtils';


/**
 * Removes redundant fields (specifically those starting with 'xpath') from an array of row objects.
 * This function iterates through each row and deletes any property whose key includes the substring 'xpath'.
 * @param {Array<Object>} rows - An array of row objects to process.
 * @returns {Array<Object>} The array of row objects with redundant fields removed.
 */
export function removeRedundantFieldsFromRows(rows) {
    rows = rows.map(row => {
        Object.keys(row).forEach(key => {
            // If the key contains 'xpath', delete the property.
            if (key.includes('xpath')) {
                delete row[key];
            }
            // The commented-out section below was for removing 'data-id', but is currently inactive.
            // if (key === 'data-id') {
            //     delete row[key];
            // }
        });
        return row;
    });
    return rows;
}

/**
 * Transforms an array of abbreviated items into a structured array of rows.
 * This function is used to reconstruct full data rows from abbreviated representations,
 * enriching them with metadata and formatting values based on collection properties.
 * @param {Array<string>} items - An array of abbreviated item keys.
 * @param {Array<Object>} itemsData - An array of full item metadata objects.
 * @param {Array<Object>} itemFieldProperties - An array of objects describing the fields and their properties.
 * @param {string} abbreviation - The abbreviation string used to derive IDs from item keys.
 * @param {Object} loadedProps - Additional properties, including `microSeparator` for joining values.
 * @returns {Array<Object>} An array of structured row objects.
 */
export function getRowsFromAbbreviatedItems(items, itemsData, itemFieldProperties, abbreviation, loadedProps) {
    const rows = [];
    if (items) {
        items.map((item, i) => {
            let row = {};
            // Derive the full ID from the abbreviated item key.
            let id = getIdFromAbbreviatedKey(abbreviation, item);
            // Find the corresponding metadata for the item using its ID.
            let metadata = itemsData.find(metadata => get(metadata, DB_ID) === id);
            row['data-id'] = id;

            itemFieldProperties.forEach(c => {
                let value = null;
                // Handle fields with hyphenated xpaths, indicating multiple sub-collections.
                if (c.xpath.indexOf("-") !== -1) {
                    value = c.xpath.split("-").map(xpath => {
                        let collection = c.subCollections.find(col => col.tableTitle === xpath);
                        let val = get(metadata, xpath);
                        if (val === undefined || val === null) {
                            val = "";
                        }
                        // Get localized value and suffix for numbers.
                        let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, val);
                        if (typeof v === DATA_TYPES.NUMBER && collection.type === DATA_TYPES.NUMBER) {
                            v = v.toLocaleString();
                        }
                        val = v + numberSuffix;
                        return val;
                    });
                    // Join the values using microSeparator or a default hyphen.
                    if (loadedProps.microSeparator) {
                        value = value.join(loadedProps.microSeparator);
                    } else {
                        value = value.join("-");
                    }
                } else {
                    // Handle single-xpath fields.
                    value = get(metadata, c.xpath);
                    if (value === undefined || value === null) {
                        value = null;
                    }
                    // Get localized value and suffix for numbers.
                    let [, v] = getLocalizedValueAndSuffix(c, value);
                    value = v;
                }
                row[c.xpath] = value;
            });
            rows.push(row);
        });
    }
    return rows;
}
