import { get } from 'lodash';
import { toCamelCase, capitalizeCamelCase } from '../core/stringUtils';
import { hasxpath } from '../core/dataAccess';


/**
 * Retrieves a value from the Redux store using an XPath-like string.
 * This function parses the XPath to determine the slice name and property name within the store,
 * then uses `getValueFromReduxStore` to fetch the actual value.
 * @param {Object} state - The Redux store state object.
 * @param {string} xpath - The XPath-like string to the desired value (e.g., 'sliceName.propertyName.nestedField').
 * @returns {*} The value retrieved from the Redux store, or `null` if not found.
 */
export function getValueFromReduxStoreFromXpath(state, xpath) {
    // Extract the slice name from the first part of the XPath.
    let sliceName = toCamelCase(xpath.split('.')[0]);
    // Construct the property name, assuming a 'modified' prefix and capitalized slice name.
    let propertyName = 'modified' + capitalizeCamelCase(xpath.split('.')[0]);
    // Get the remaining part of the XPath for nested property access.
    let propxpath = xpath.substring(xpath.indexOf('.') + 1);
    return getValueFromReduxStore(state, sliceName, propertyName, propxpath);
}

/**
 * Retrieves a value from a specific slice and property within the Redux store.
 * It checks for the existence of the slice and property before attempting to retrieve the value.
 * @param {Object} state - The Redux store state object.
 * @param {string} sliceName - The name of the Redux slice (e.g., 'basketOrderSlice').
 * @param {string} propertyName - The name of the property within the slice (e.g., 'modifiedBasketOrder').
 * @param {string} xpath - The XPath-like string to the desired value within the property.
 * @returns {*} The value retrieved from the Redux store, or `null` if the slice, property, or value is not found.
 */
export function getValueFromReduxStore(state, sliceName, propertyName, xpath) {
    // Check if the state and the specified slice exist.
    if (state && state.hasOwnProperty(sliceName)) {
        let slice = state[sliceName];
        if (slice) {
            let object = slice[propertyName];
            // Check if the object and the specified XPath exist within the object.
            if (object && hasxpath(object, xpath)) {
                return get(object, xpath);
            }
        }
        return null;
    }
}