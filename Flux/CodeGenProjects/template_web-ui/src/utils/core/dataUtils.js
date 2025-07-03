import { DB_ID, NEW_ITEM_ID } from '../../constants';


/**
 * Generates a new item key based on the provided collections and abbreviation.
 * This function constructs a unique key for a new item, incorporating default values or placeholders
 * from the collection definitions, and a special `NEW_ITEM_ID` for the database ID field.
 * @param {Array<Object>} collections - An array of collection objects, each defining properties like `key`, `placeholder`, and `default`.
 * @param {string} abbreviated - The abbreviated key format string (e.g., "field1:field2-DB_ID").
 * @returns {string} The newly generated item key.
 */
export function getNewItem(collections, abbreviated) {
    // Extract the relevant part of the abbreviated key path (before '^' and after the last ':').
    const abbreviatedKeyPath = abbreviated.split('^')[0].split(':').pop();
    const fields = abbreviatedKeyPath.split('-');
    let newItem = '';

    fields.forEach(field => {
        let key = field.split('.').pop();
        // DB_ID must be the last field in abbreviated key
        if (key === DB_ID) {
            newItem += NEW_ITEM_ID;
        } else {
            let defaultValue = 'XXXX'; // Default placeholder if no specific one is found.
            let collection = collections.find(c => c.key === key);
            // Use placeholder or default value from the collection if available.
            if (collection) {
                if (collection.placeholder) {
                    defaultValue = collection.placeholder;
                } else if (collection.default) {
                    defaultValue = collection.default;
                }
            }
            newItem += defaultValue + '-';
        }
    });
    return newItem;
}


/**
 * Retrieves the abbreviated key from an array of keys that matches a given ID.
 * This function is useful for mapping a database ID back to its abbreviated key representation.
 * @param {Array<string>} keyArray - An array of abbreviated keys to search through.
 * @param {string} abbreviated - The abbreviated key format string, used by `getIdFromAbbreviatedKey`.
 * @param {number} id - The database ID to match.
 * @returns {string|undefined} The matching abbreviated key, or `undefined` if no match is found.
 */
export function getAbbreviatedKeyFromId(keyArray, abbreviated, id) {
    let abbreviatedKey; // Variable to store the found abbreviated key.
    keyArray.forEach(key => {
        let keyId = getIdFromAbbreviatedKey(abbreviated, key);
        if (keyId === id) {
            abbreviatedKey = key;
        }
    });
    return abbreviatedKey;
}

/**
 * Extracts the numerical ID from an abbreviated key string.
 * The ID is expected to be associated with the `DB_ID` field within the abbreviated key format.
 * @param {string} abbreviated - The abbreviated key format string (e.g., "field1:field2-DB_ID").
 * @param {string} abbreviatedKey - The actual abbreviated key string (e.g., "value1-value2-123").
 * @returns {number} The extracted numerical ID, or -1 if the ID is not found or cannot be parsed.
 */
export function getIdFromAbbreviatedKey(abbreviated, abbreviatedKey) {
    // Clean the abbreviated format string by removing any part after '^'.
    abbreviated = abbreviated.split('^')[0];
    let abbreviatedSplit = abbreviated.split('-');
    let idIndex = -1;

    // Find the index of the DB_ID field in the abbreviated format.
    abbreviatedSplit.map((text, index) => {
        if (text.indexOf(DB_ID) > 0) {
            idIndex = index;
        }
    });

    if (idIndex !== -1) {
        let abbreviatedKeySplit = abbreviatedKey.split('-');
        // Parse the ID as an integer.
        return parseInt(abbreviatedKeySplit[idIndex]);
    } else {
        // If DB_ID is not found, return -1.
        return idIndex;
    }
}

/**
 * Performs a fast deep clone of an object using JSON serialization and deserialization.
 * This method is quick but has limitations: it cannot clone functions, Dates, RegExps, Maps, Sets, or undefined values.
 * @param {Object} obj - The object to clone.
 * @returns {Object} A deep clone of the input object.
 */
export function fastClone(obj) {
    // Handle undefined or null input by returning it directly.
    if (obj === undefined || obj === null) return obj;
    // Serialize the object to a JSON string and then parse it back to a new object.
    return JSON.parse(JSON.stringify(obj));
}

/**
 * Retrieves a collection object by its name (either `key` or `tableTitle`).
 * This function is crucial for accessing collection-specific metadata and attributes.
 * @param {Array<Object>} collections - A list of dictionaries, where each dictionary represents a widget field and its attributes.
 * @param {string} name - The name (field name or XPath) of the collection to retrieve.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type (uses `key` for lookup), false otherwise (uses `tableTitle`).
 * @returns {Object} The found collection object.
 * @throws {Error} If the `collections` list is null or undefined, or if no collection is found for the given name.
 */
export function getCollectionByName(collections, name, isCollectionType = false) {
    if (!collections) {
        throw new Error(`getCollectionByName failed: 'collections' list is null or undefined. Received: ${collections}`);
    }
    let collection;
    if (isCollectionType) {
        // Find collection by 'key' if it's a collection type.
        collection = collections.find(collection => collection.key === name);
    } else {
        // Find collection by 'tableTitle' otherwise.
        collection = collections.find(collection => collection.tableTitle === name);
    }
    if (!collection) {
        throw new Error(`getCollectionByName failed: no collection object found for name: ${name}`);
    }
    return collection;
}