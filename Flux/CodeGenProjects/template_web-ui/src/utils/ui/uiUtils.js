import { cloneDeep, get } from 'lodash';
import * as XLSX from 'xlsx';
import { DB_ID, DATA_TYPES, SHAPE_TYPES, SIZE_TYPES } from '../../constants';
import { addxpath } from '../core/dataAccess';
import { getIdFromAbbreviatedKey } from '../core/dataUtils';
import { toCamelCase } from '../core/stringUtils';
import { extractSourceModelName } from '../dynamicSchemaUtils/dataSourceUtils';


/**
 * Retrieves a widget option by its ID, handling cases where the ID is bound.
 * If an option with the given ID is found, a deep clone of it is returned. Otherwise,
 * a deep clone of the first widget option is returned with the ID bound to it.
 *
 * @param {Array<Object>} widgetOptions - An array of available widget options.
 * @param {string|number} id - The ID to search for.
 * @param {boolean} [isIdBound=false] - Indicates whether the ID is bound to a specific widget option.
 * @returns {Object} A cloned widget option object, potentially with a bound ID.
 */
export function getWidgetOptionById(widgetOptions, id, isIdBound = false) {
    let widgetOption = cloneDeep(widgetOptions[0]);
    if (isIdBound) {
        const dataElement = widgetOptions.find(data => data.hasOwnProperty('bind_id_val') && String(data.bind_id_val) === String(id));
        if (dataElement) {
            widgetOption = cloneDeep(dataElement);
        } else {
            widgetOption.bind_id_val = String(id);
        }
    }
    // widgetOption = cloneDeep(widgetOption);
    if (!widgetOption.enable_override) {
        widgetOption.enable_override = [];
    }
    if (!widgetOption.disable_override) {
        widgetOption.disable_override = [];
    }
    for (const key in widgetOption) {
        if (widgetOption[key] === null) {
            delete widgetOption[key];
        }
    }
    return widgetOption;
}


/**
 * Determines the title of a widget based on its schema, name, and dynamic data.
 * If a `dynamic_widget_title_fld` is specified in the widget schema and its value
 * can be retrieved from the data, that value is used as the title. Otherwise,
 * the title from the widget schema or the widget name itself is used.
 *
 * @param {Object} widgetOption - The widget option object.
 * @param {Object} widgetSchema - The schema definition for the widget.
 * @param {string} widgetName - The default name of the widget.
 * @param {Object} data - The data object from which to potentially extract a dynamic title.
 * @returns {string} The determined title for the widget.
 */
export function getWidgetTitle(widgetOption, widgetSchema, widgetName, data) {
    if (widgetSchema.widget_ui_data_element?.hasOwnProperty('dynamic_widget_title_fld')) {
        const dynamicWidgetTitleField = widgetSchema.widget_ui_data_element.dynamic_widget_title_fld;
        const name = dynamicWidgetTitleField.split('.')[0];
        if (name === widgetName) {
            const fieldxpath = dynamicWidgetTitleField.substring(dynamicWidgetTitleField.indexOf('.') + 1);
            const value = get(data, fieldxpath);
            if (value) {
                return value;
            }
        }
        // TODO: fetching dynamic name for other widget fields
    }
    return widgetSchema.hasOwnProperty('title') ? widgetSchema.title : widgetName;
}


/**
 * Generates a list of abbreviated collections based on widget collections dictionary and load list field attributes.
 * This function processes the `abbreviated` field from `loadListFieldAttrs` to construct
 * a structured array of collections, including special handling for alert bubbles.
 *
 * @param {Object} widgetCollectionsDict - A dictionary of widget collections, keyed by widget name.
 * @param {Object} loadListFieldAttrs - Attributes related to loading list fields, including abbreviation and alert bubble sources.
 * @returns {Array<Object>} An array of abbreviated collection objects.
 * @throws {Error} If a title is not found in an abbreviated split or if no collection is found for a field's XPath.
 */
export function getAbbreviatedCollections(widgetCollectionsDict, loadListFieldAttrs) {
    const abbreviated = loadListFieldAttrs.abbreviated;
    const abbreviatedCollections = [];
    let sequenceNumber = 1;
    // alert bubble is the first column always
    if (loadListFieldAttrs.alertBubbleSource) {
        let collection = {};
        collection.key = '';
        collection.title = '';
        collection.elaborateTitle = false;
        collection.sequenceNumber = sequenceNumber;
        collection.type = 'alert_bubble'
        // source to fetch value of bubble
        const bubbleSource = loadListFieldAttrs.alertBubbleSource;
        collection.alertBubbleSource = bubbleSource;
        collection.source = bubbleSource.split('.')[0];
        collection.xpath = bubbleSource.substring(bubbleSource.indexOf('.') + 1);
        // source to fetch color of bubble
        const bubbleColorSource = loadListFieldAttrs.alertBubbleColor;
        if (bubbleColorSource) {
            const colorSource = bubbleColorSource.substring(bubbleColorSource.indexOf('.') + 1);
            collection.colorSource = colorSource
            collection.colorCollection = widgetCollectionsDict[collection.source].find(col => col.tableTitle === colorSource);
        }
        abbreviatedCollections.push(collection);
        sequenceNumber += 1;
    }
    abbreviated.split('^').forEach((titlePathPair, index) => {
        let title;
        let source;
        // title in collection view is always expected to be present
        if (titlePathPair.indexOf(':') !== -1) {
            title = titlePathPair.split(':')[0];
            source = titlePathPair.split(':')[1];
        } else {
            throw new Error('no title found in abbreviated split. expected title followed by colon (:)')
        }
        // expected all the fields in abbreviated is from its abbreviated dependent source
        const widgetName = source.split('.')[0];
        let xpath = source.split('-').map(path => path = path.substring(path.indexOf('.') + 1));
        xpath = xpath.join('-');
        const subCollections = xpath.split('-').map(path => {
            return widgetCollectionsDict[widgetName].map(col => Object.assign({}, col))
                .find(col => col.tableTitle === path);
        })
        // if a single field has values from multiple source separated by hyphen, then
        // attributes of all fields are combined
        source = xpath.split('-')[0];
        const collectionsCopy = widgetCollectionsDict[widgetName].map(col => Object.assign({}, col));
        const collection = collectionsCopy.find(col => col.tableTitle === source);
        if (collection) {
            xpath.split('-').forEach(path => {
                const pathCollection = collectionsCopy.find(col => col.tableTitle === path);
                // additional handling to prevent override
                Object.keys(pathCollection).forEach(key => {
                    if (['serverPopulate', 'ormNoUpdate'].includes(key)) {
                        if (!(collection.hasOwnProperty(key) && collection[key]) && pathCollection.hasOwnProperty(key)) {
                            collection[key] = pathCollection[key];
                        }
                    } else {
                        collection[key] = pathCollection[key];
                    }
                })
            })
            if (xpath === DB_ID) {
                collection.noCommonKeyDeduced = true;
            }
            // create a custom collection object
            collection.sequenceNumber = sequenceNumber;
            collection.source = widgetName;
            collection.rootLevel = false;
            collection.key = title;
            collection.title = title;
            // TODO: check the scenario in which xpath and tableTitle are different
            collection.tableTitle = xpath;
            collection.xpath = xpath;
            // remove default properties set on the fields
            collection.elaborateTitle = false;
            collection.hide = false;
            collection.subCollections = subCollections;
            // if field has values from multiple source, it's data-type is considered STRING
            if (xpath.indexOf('-') !== -1) {
                collection.type = DATA_TYPES.STRING;
            }
            abbreviatedCollections.push(collection);
            sequenceNumber += 1;
        } else {
            throw new Error('no collection (field attributes) found for the field with xpath ' + source);
        }
    })
    return abbreviatedCollections;
}


/**
 * Identifies and returns a set of unique widget names that are dependent on the abbreviated fields.
 * This includes widgets referenced in the `abbreviated` field, as well as `alertBubbleSource`
 * and `alertBubbleColorSource`.
 *
 * @param {Object} loadListFieldAttrs - Attributes related to loading list fields, containing abbreviated field information.
 * @returns {Array<string>} An array of unique widget names that are abbreviated dependent.
 */
export function getAbbreviatedDependentWidgets(loadListFieldAttrs) {
    const widgetSet = new Set();
    loadListFieldAttrs.abbreviated.split('^').forEach((keyValuePair) => {
        const [, fieldxpath] = keyValuePair.split(':');
        const name = fieldxpath.split('.')[0];
        widgetSet.add(name);
    });
    const bubbleSource = loadListFieldAttrs.alertBubbleSource;
    if (bubbleSource) {
        const name = bubbleSource.split('.')[0];
        widgetSet.add(name);
    }
    const bubbleColorSource = loadListFieldAttrs.alertBubbleColorSource;
    if (bubbleColorSource) {
        const name = bubbleColorSource.split('.')[0];
        widgetSet.add(name);
    }
    return Array.from(widgetSet);
}


/**
 * Converts a snake_case string to camelCase.
 * @param {string} snakeCase - The snake_case string.
 * @returns {string} The camelCase string.
 */
export function snakeToCamel(snakeCase) {
    return snakeCase.replace(/_([a-z])/g, function (match, letter) {
        return letter.toUpperCase();
    });
}


/**
 * Converts a snake_case string to TitleCase.
 * @param {string} snakeStr - The snake_case string.
 * @returns {string} - The PascalCase string.
 */
export function snakeToTitle(snakeStr) {
    return snakeStr
        .split('_')
        .map(word => word === 'ui' ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}


/**
 * Sorts a collection of columns based on their sequence number, column orders, and grouping criteria.
 * This function provides complex sorting logic, including handling for grouped columns, centered columns,
 * and flipped order.
 *
 * @param {Array<Object>} collections - The array of column collection objects to be sorted.
 * @param {Array<Object>} columnOrders - An array of objects defining custom column orderings.
 * @param {boolean} [groupBy=false] - If true, applies grouping-specific sorting logic.
 * @param {boolean} [center=false] - If true, applies centering logic for grouped columns.
 * @param {boolean} [flip=false] - If true, reverses the order for certain grouped columns.
 * @param {boolean} [isCollectionType=false] - If true, uses 'key' for field name; otherwise, uses 'tableTitle'.
 * @returns {Array<Object>} The sorted array of column collection objects.
 */
export function sortColumns(collections, columnOrders, groupBy = false, center = false, flip = false, isCollectionType = false) {
    function handleEqualSequence(seqA, seqB, orderA, orderB, isReverse = false) {
        if (orderA && orderB) {
            if (orderA.sequence < orderB.sequence) {
                if (isReverse) return 1;
                return -1;
            }
            if (isReverse) return -1;
            return 1;
        } else if (orderA) {
            if (orderA.sequence <= seqB) {
                if (isReverse) return 1;
                return -1;
            }
            if (isReverse) return -1;
            return 1;
        } else if (orderB) {
            if (orderB.sequence <= seqA) {
                if (isReverse) return -1;
                return 1;
            }
            if (isReverse) return 1;
            return -1;
        }
    }
    collections.sort(function (a, b) {
        let seqA = a.sequenceNumber;
        let seqB = b.sequenceNumber;
        let orderA;
        let orderB;
        if (columnOrders) {
            let fieldName = 'tableTitle';
            if (isCollectionType) {
                fieldName = 'key';
            }
            orderA = columnOrders.find(order => order.column_name === a[fieldName]);
            orderB = columnOrders.find(order => order.column_name === b[fieldName]);
            if (orderA) {
                seqA = orderA.sequence;
            }
            if (orderB) {
                seqB = orderB.sequence;
            }
        }
        if (groupBy) {
            if (center && a.sourceIndex === 0 && b.sourceIndex === 0) {
                if (a.joinKey && b.joinKey) {
                    if (seqA < seqB) return -1;
                    else if (seqB < seqA) return 1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
                } else if (a.joinKey) {
                    return 1;
                } else if (b.joinKey) {
                    return -1
                } else if (a.commonGroupKey && b.commonGroupKey) {
                    if (seqA < seqB) return -1;
                    else if (seqB < seqA) return 1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
                } else if (a.commonGroupKey) {
                    return 1;
                } else if (b.commonGroupKey) {
                    return -1
                } else if (seqA < seqB) {
                    return -1;
                } else if (seqB < seqA) {
                    return 1
                } else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            }
            else if (a.joinKey && b.joinKey) {
                if (seqA < seqB) return -1;
                else if (seqB < seqA) return 1;
                else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            } else if (a.joinKey) {
                return -1;
            } else if (b.joinKey) {
                return 1;
            } else if (a.commonGroupKey && b.commonGroupKey) {
                if (seqA < seqB) return -1;
                else if (seqB < seqA) return 1;
                else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
            } else if (a.commonGroupKey) {
                return -1;
            } else if (b.commonGroupKey) {
                return 1;
            } else if (flip) {
                if (a.sourceIndex === b.sourceIndex && a.sourceIndex > 0) {
                    if (seqA < seqB) return 1;
                    else if (seqB < seqA) return -1;
                    else return handleEqualSequence(seqA, seqB, orderA, orderB, true);  // seqA === seqB with flip
                } else if (a.sourceIndex < b.sourceIndex) {
                    return -1;
                } else if (b.sourceIndex < a.sourceIndex) {
                    return 1;
                }
            } else if (a.sourceIndex < b.sourceIndex) {
                return -1;
            } else if (b.sourceIndex < a.sourceIndex) {
                return 1;
            }
        }
        if (seqA < seqB) return -1;
        else if (seqB < seqA) return 1;
        else return handleEqualSequence(seqA, seqB, orderA, orderB);  // seqA === seqB
    })
    return collections;
}


/**
 * Extracts reducer names from a collection of metadata objects.
 * It identifies properties like 'min', 'max', and 'autocomplete' that are strings
 * and derive reducer names from them, ensuring uniqueness.
 *
 * @param {Array<Object>} collections - An array of collection metadata objects.
 * @returns {Array<string>} An array of unique reducer names.
 */
export function getReducerArrayFromCollections(collections) {
    const reducerArray = [];
    collections
        .filter(col => typeof col.min === DATA_TYPES.STRING || typeof col.max === DATA_TYPES.STRING || col.dynamic_autocomplete)
        .map(col => {
            const dynamicListenProperties = ['min', 'max', 'autocomplete'];
            dynamicListenProperties.forEach(property => {
                if (col.hasOwnProperty(property) && typeof col[property] === DATA_TYPES.STRING) {
                    if (property === 'autocomplete' && !col.dynamic_autocomplete) {
                        return;
                    }
                    const reducerName = col[property].split('.')[0];
                    if (!reducerArray.includes(reducerName)) {
                        reducerArray.push(reducerName);
                    }
                }
            })
        });
    return reducerArray;

}


/**
 * Updates a stored array of repeated widgets with a modified object.
 * If a `selectedId` is provided and matches the `DB_ID` of the `updatedObj`,
 * the corresponding object in the `storedArray` is updated.
 *
 * @param {Array<Object>} storedArray - The array of stored widget objects.
 * @param {string|number} selectedId - The ID of the selected object to update.
 * @param {Object} updatedObj - The object with updated values.
 * @returns {Array<Object>} The updated array of widget objects.
 */
export function getRepeatedWidgetModifiedArray(storedArray, selectedId, updatedObj) {
    let updatedArray = addxpath(cloneDeep(storedArray));
    if (selectedId && updatedObj[DB_ID] === selectedId) {
        const idx = updatedArray.findIndex(obj => obj[DB_ID] === selectedId);
        if (idx !== -1) {
            updatedArray[idx] = updatedObj;
        }
    }
    return updatedArray;
}


/**
 * Generates an abbreviated option label for a buffer based on stored data.
 * If the `bufferListFieldAttrs` does not have an `abbreviated` field, the original `bufferOption` is returned.
 * Otherwise, it attempts to find the corresponding stored object and construct a label from its values.
 *
 * @param {string} bufferOption - The original buffer option string.
 * @param {Object} bufferListFieldAttrs - Attributes for the buffer list field, including abbreviation details.
 * @param {Object} loadListFieldAttrs - Attributes for loading list fields, used to get the ID from the abbreviated key.
 * @param {Array<Object>} storedArray - The array of stored objects to search within.
 * @returns {string} The abbreviated option label or the original buffer option if no abbreviation is defined or found.
 */
export function getBufferAbbreviatedOptionLabel(bufferOption, bufferListFieldAttrs, loadListFieldAttrs, storedArray) {
    if (!bufferListFieldAttrs.abbreviated) {
        return bufferOption;
    }
    if (bufferOption === '') return bufferOption;
    const id = getIdFromAbbreviatedKey(loadListFieldAttrs.abbreviated, bufferOption);
    const storedObj = storedArray.find(obj => obj[DB_ID] === id);
    if (storedObj) {
        let abbreviatedSplit = bufferListFieldAttrs.abbreviated.split('^')[0].split(':')[1].split('-');
        abbreviatedSplit = abbreviatedSplit.map(xpath => xpath.substring(xpath.indexOf('.') + 1));
        const values = [];
        abbreviatedSplit.forEach(xpath => {
            values.push(get(storedObj, xpath));
        })
        return values.join('-');
    }
    return bufferOption;
}


/**
 * Calculates the best contrasting color (black or white) for a given background color.
 * This function determines if the background color is light or dark and returns white or black respectively.
 *
 * @param {string} color - The input color in hex (e.g., '#RRGGBB') or RGB (e.g., 'rgb(R, G, B)') format.
 * @returns {string} The contrast color, either '#000000' (black) or '#FFFFFF' (white).
 * @throws {Error} If an unsupported color format is provided.
 */
export function getContrastColor(color) {
    // Function to convert hex to RGB
    function hexToRgb(hex) {
        hex = hex.replace(/^#/, '');
        if (hex.length === 3) {
            hex = hex.split('').map(function (hex) {
                return hex + hex;
            }).join('');
        }
        var bigint = parseInt(hex, 16);
        return [bigint >> 16 & 255, bigint >> 8 & 255, bigint & 255];
    }

    // Function to convert color to RGB
    function colorToRgb(color) {
        // Check if the color is in hex format
        if (color.startsWith('#')) {
            return hexToRgb(color);
        }
        // If it's already in rgb format
        if (color.startsWith('rgb')) {
            var match = color.match(/(\d+), (\d+), (\d+)/);
            if (match) {
                return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
            }
        }
        // Add other color formats if needed
        throw new Error('Unsupported color format');
    }

    // Get RGB components of the color
    const [r, g, b] = colorToRgb(color);

    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b);

    // Return black for light colors, white for dark colors
    return luminance > 186 ? '#000000' : '#FFFFFF';
}


/**
 * Measures the width of a given string of characters in pixels, considering a specified font size.
 * This function creates a temporary canvas element to accurately measure text dimensions.
 *
 * @param {string} characters - The string of characters to measure.
 * @param {number} [fontSize=14] - The font size in pixels to use for measurement.
 * @returns {number} The width of the text in pixels, adjusted for the device's pixel ratio.
 */
export function getTextWidthInPx(characters, fontSize = 14) {
    // Create a temporary canvas element
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');

    // Set the font size on the canvas context
    context.font = `${fontSize}px sans-serif`; // Using a default font (sans-serif)

    // Measure the text width
    const metrics = context.measureText(characters);

    // Calculate the zoom level
    const zoomLevel = window.devicePixelRatio;

    // Return the width adjusted for the zoom level
    return metrics.width * zoomLevel;
}


/**
 * Extracts unique IDs from an array of active rows.
 * This function iterates through grouped rows and collects all unique IDs associated with them.
 *
 * @param {Array<Array<Object>>} activeRows - An array of arrays, where each inner array represents a grouped row and contains row objects.
 * @param {string} idField - The name of the field in each row object that contains the ID.
 * @returns {Array<string|number>} An array of unique IDs.
 */
export function getActiveIds(activeRows, idField) {
    const activeObjIds = new Set();
    if (activeRows.length > 0) {
        activeRows.forEach((groupedRow) => {
            groupedRow.forEach((row) => {
                const id = row[idField];
                if (id) {
                    activeObjIds.add(id);
                }
            });
        });
    }
    return Array.from(activeObjIds);
}


/**
 * Generates an Excel or CSV file from a given array of rows.
 * This function uses the `xlsx` library to create a worksheet and then writes it to a file.
 *
 * @param {Array<Object>} rows - The data rows to be written to the file.
 * @param {string} fileName - The desired name of the output file.
 * @param {boolean} [csv=false] - If true, generates a CSV file; otherwise, generates an XLSX file.
 */
export function generateExcel(rows, fileName, csv = false) {
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Data');
    const bookType = csv ? 'csv' : 'xlsx'
    XLSX.writeFile(wb, fileName, { bookType: bookType });
}


/**
 * Generates a CSV file name based on the model name and current timestamp.
 *
 * @param {string} modelName - The name of the model.
 * @returns {string} The generated CSV file name.
 */
export function getCSVFileName(modelName) {
    return `${modelName}_${new Date().toISOString()}.csv`;
}


/**
 * Updates the form validation state for a specific XPath.
 * If a `validation` object is provided, it merges it into the current validation state.
 * If `validation` is null or undefined, it removes the validation for the given XPath.
 *
 * @param {Object} formValidationRef - A ref object pointing to the current form validation state.
 * @param {string} xpath - The XPath for which to update the validation.
 * @param {Object|null|undefined} validation - The validation object to apply or null/undefined to remove.
 */
export function updateFormValidation(formValidationRef, xpath, validation) {
    if (!formValidationRef?.current) {
        console.error('form validation ref found null');
        return;
    }

    if (validation) {
        formValidationRef.current = { ...formValidationRef.current, [xpath]: validation };
    } else {
        if (xpath in formValidationRef.current) {
            delete formValidationRef.current[xpath];
        }
    }
}



/**
 * Filters an array of rows based on a provided list of row IDs.
 * Only rows whose 'data-id' is present in the `rowIds` array will be returned.
 *
 * @param {Array<Object>} rows - The array of row objects to filter.
 * @param {Array<string|number>} rowIds - An array of IDs to filter the rows by.
 * @returns {Array<Object>} A new array containing only the rows whose IDs are in `rowIds`.
 */
export function applyRowIdsFilter(rows, rowIds) {
    if (rowIds && rowIds.length > 0 && rows.length > 0) {
        const updatedRows = rows.filter((row) => rowIds.includes(row['data-id']));
        return updatedRows;
    }
    return rows;
}


/**
 * Enriches sort orders with an `is_absolute_sort` flag for fields present in `absoluteSorts`.
 *
 * @param {Array<Object>} sortOrders - An array of sort order objects.
 * @param {Array<string>} absoluteSorts - An array of field names that should be treated as absolute sorts.
 * @returns {Array<Object>} The updated array of sort order objects.
 */
export function getSortOrdersWithAbs(sortOrders, absoluteSorts) {
    const sortOrdersWithAbs = sortOrders.map((sortOrder) => {
        if (absoluteSorts.includes(sortOrder.sort_by)) {
            sortOrder.is_absolute_sort = true;
        }
        return sortOrder;
    })
    return sortOrdersWithAbs;
}


/**
 * Calculates and returns unique values for specified filter fields from a given set of rows.
 * This function filters out object and array types, then counts occurrences of each unique value
 * for the remaining fields, and finally sorts these unique values.
 *
 * @param {Array<Object>} rows - The array of row objects to extract unique values from.
 * @param {Array<Object>} filterFieldsMetadata - An array of metadata objects for the filter fields.
 * @param {boolean} [isAbbreviationMerge=false] - If true, uses 'key' as the field for comparison; otherwise, uses 'tableTitle'.
 * @returns {Object} An object where keys are field names and values are Maps containing unique values and their counts.
 */
export function getUniqueValues(rows, filterFieldsMetadata, isAbbreviationMerge = false) {
    const uniqueValues = {};
    filterFieldsMetadata
        .filter((meta) => meta.type !== 'object' && meta.type !== 'array')
        .forEach((meta) => {
            const fieldKey = isAbbreviationMerge ? meta.key : meta.tableTitle;
            uniqueValues[fieldKey] = new Map();
            const counterMap = uniqueValues[fieldKey];
            rows.forEach((row) => {
                const value = row[fieldKey];
                if (counterMap.has(value)) {
                    const storedCount = counterMap.get(value);
                    counterMap.set(value, storedCount + 1);
                } else {
                    counterMap.set(value, 1);
                }
            });
            const sortedKeys = Array.from(counterMap.keys()).sort((a, b) => {
                // Both null/undefined - maintain order
                if ((a == null) && (b == null)) return 0;

                // Only 'a' is null/undefined - put it first
                if (a == null) return -1;

                // Only 'b' is null/undefined - put it second
                if (b == null) return 1;

                // Both have values - sort ascending
                if (a < b) return -1;
                if (a > b) return 1;
                return 0;
            });
            const sortedMap = new Map();
            for (const key of sortedKeys) {
                sortedMap.set(key, counterMap.get(key));
            }
            uniqueValues[fieldKey] = sortedMap;
        });
    return uniqueValues;
}


/**
 * Generates a CRUD override dictionary from a model schema.
 * This dictionary maps UI CRUD types to their corresponding query endpoints and parameters.
 *
 * @param {Object} modelSchema - The schema of the model, potentially containing `override_default_crud`.
 * @param {Array<string>} availableModelNames - Array of model names that exist in the schema.
 * @returns {Object|null} A dictionary of CRUD overrides or null if no overrides are defined.
 */
export function getCrudOverrideDict(modelSchema, availableModelNames = null) {
    return modelSchema.override_default_crud?.reduce((acc, { ui_crud_type, query_name, query_src_model_name, ui_query_params }) => {
        let paramDict = null;
        ui_query_params?.forEach(({ query_param_name, query_param_value_src }) => {
            // Extract model name using unified utility (checks query_src_model_name first, then extracts from value_src)
            const sourceModelName = extractSourceModelName(query_src_model_name, query_param_value_src);

            // Only include param if no validation needed OR source model exists in schema
            if (!availableModelNames || availableModelNames.includes(sourceModelName)) {
                const param_value_src = query_param_value_src.substring(query_param_value_src.indexOf('.') + 1);
                if (!paramDict) {
                    paramDict = {};
                }
                paramDict[query_param_name] = param_value_src;
            }
            // else: skip this param (source model doesn't exist in schema)
        })

        // Only add CRUD operation if it has valid params OR no params were defined
        // Skip if all params were filtered out (paramDict would be null but ui_query_params existed)
        if (paramDict !== null || !ui_query_params || ui_query_params.length === 0) {
            acc[ui_crud_type] = { endpoint: `query-${query_name}`, paramDict };
        }

        return acc;
    }, {}) || null;
}


/**
 * Extracts default filter parameters from the model schema.
 * Unlike `getCrudOverrideDict`, this does not replace the endpoint but appends filter parameters
 * to the standard GET_ALL endpoint.
 *
 * @param {Object} modelSchema - The schema of the model, potentially containing `default_filter_param`.
 * @param {Array<string>} availableModelNames - Array of model names that exist in the schema.
 * @returns {Object|null} A dictionary containing paramDict for default filtering, or null if not defined.
 */
export function getDefaultFilterParamDict(modelSchema, availableModelNames = null) {
    const defaultFilter = modelSchema.default_filter_param;

    // Check if default_filter_param exists and is an object (not array)
    if (!defaultFilter || typeof defaultFilter !== 'object' || Array.isArray(defaultFilter)) {
        return null;
    }

    // Check if ui_query_params exists
    if (!defaultFilter.ui_filter_params || !Array.isArray(defaultFilter.ui_filter_params)) {
        return null;
    }

    let paramDict = null;
    defaultFilter.ui_filter_params.forEach(({ param_name, param_value_src, param_value }) => {
        // Support both derived values (from other models) and direct values
        if (param_value_src) {
            // Extract model name using unified utility (checks param_src_model_name first, then extracts from value_src)
            const sourceModelName = extractSourceModelName(defaultFilter.param_src_model_name, param_value_src);

            // Only include param if no validation needed OR source model exists in schema
            if (!availableModelNames || availableModelNames.includes(sourceModelName)) {
                // Derived value - extract the path after the model name and store with type
                const extractedPath = param_value_src.substring(param_value_src.indexOf('.') + 1);
                if (!paramDict) {
                    paramDict = {};
                }
                paramDict[param_name] = { type: 'src', value: extractedPath };
            }
            // else: skip this param (source model doesn't exist in schema)
        } else if (param_value !== undefined && param_value !== null) {
            // Direct value - store as-is with type (always include - no dependency on source models)
            if (!paramDict) {
                paramDict = {};
            }
            paramDict[param_name] = { type: 'val', value: param_value };
        }
    });

    return paramDict && Object.keys(paramDict).length > 0 ? paramDict : null;
}


/**
 * Generates a dictionary of CRUD overrides for multiple data sources.
 * It iterates through the provided data sources and applies `getCrudOverrideDict` to each.
 *
 * @param {Array<Object>} dataSources - An array of data source objects, each containing a `name` and `schema`.
 * @param {Array<string>} availableModelNames - Array of model names that exist in the schema.
 * @returns {Object|null} A dictionary where keys are data source names and values are their CRUD override dictionaries, or null if no overrides are found.
 */
export function getDataSourcesCrudOverrideDict(dataSources, availableModelNames = null) {
    const dataSourcesCrudOverrideDict = {};
    dataSources.forEach(({ name, schema }) => {
        // Only process data source if no validation needed OR if the data source model exists in schema
        if (!availableModelNames || availableModelNames.includes(name)) {
            const crudOverrideDict = getCrudOverrideDict(schema, availableModelNames);
            if (crudOverrideDict) {
                dataSourcesCrudOverrideDict[name] = crudOverrideDict;
            }
        }
        // else: skip this data source (model doesn't exist in schema)
    });
    if (Object.keys(dataSourcesCrudOverrideDict).length === 0) {
        return null;
    }
    return dataSourcesCrudOverrideDict;
}


/**
 * Generates a dictionary of default filter parameters for multiple data sources.
 * It iterates through the provided data sources and applies `getDefaultFilterParamDict` to each.
 *
 * @param {Array<Object>} dataSources - An array of data source objects, each containing a `name` and `schema`.
 * @param {Array<string>} availableModelNames - Array of model names that exist in the schema.
 * @returns {Object|null} A dictionary where keys are data source names and values are their default filter param dictionaries, or null if no filters are found.
 */
export function getDataSourcesDefaultFilterParamDict(dataSources, availableModelNames = null) {
    const dataSourcesDefaultFilterParamDict = {};
    dataSources.forEach(({ name, schema }) => {
        // Only process data source if no validation needed OR if the data source model exists in schema
        if (!availableModelNames || availableModelNames.includes(name)) {
            const defaultFilterParamDict = getDefaultFilterParamDict(schema, availableModelNames);
            if (defaultFilterParamDict) {
                dataSourcesDefaultFilterParamDict[name] = defaultFilterParamDict;
            }
        }
        // else: skip this data source (model doesn't exist in schema)
    });
    if (Object.keys(dataSourcesDefaultFilterParamDict).length === 0) {
        return null;
    }
    return dataSourcesDefaultFilterParamDict;
}


/**
 * Retrieves a data source object by its name from a list of data sources.
 *
 * @param {Array<Object>} dataSources - An array of data source objects.
 * @param {string} sourceName - The name of the data source to retrieve.
 * @returns {Object} The data source object.
 * @throws {alert} If the data source is not found.
 */
export function getDataSourceObj(dataSources, sourceName) {
    const dataSource = dataSources.find(o => o.name === sourceName);
    if (!dataSource) {
        alert('error');
    }
    return dataSource;
}


/**
 * Extracts the size type from a given value string.
 * The size type is expected to be the last part of the string after an underscore.
 *
 * @param {string} value - The string value from which to extract the size.
 * @returns {string} The corresponding size type from `SIZE_TYPES` or `SIZE_TYPES.UNSPECIFIED` if not found.
 */
export function getSizeFromValue(value) {
    let size = value.split('_').pop();
    if (SIZE_TYPES.hasOwnProperty(size)) {
        return SIZE_TYPES[size];
    }
    return SIZE_TYPES.UNSPECIFIED;

}


/**
 * Extracts the shape type from a given value string.
 * The shape type is expected to be the last part of the string after an underscore.
 *
 * @param {string} value - The string value from which to extract the shape.
 * @returns {string} The corresponding shape type from `SHAPE_TYPES` or `SHAPE_TYPES.UNSPECIFIED` if not found.
 */
export function getShapeFromValue(value) {
    let shape = value.split('_').pop();
    if (SHAPE_TYPES.hasOwnProperty(shape)) {
        return SHAPE_TYPES[shape];
    }
    return SHAPE_TYPES.UNSPECIFIED;
}


/**
 * Retrieves the hover text type by trimming the input value.
 *
 * @param {string} value - The input string value.
 * @returns {string} The trimmed hover text type.
 */
export function getHoverTextType(value) {
    let hoverType = value.trim();
    return hoverType;
}