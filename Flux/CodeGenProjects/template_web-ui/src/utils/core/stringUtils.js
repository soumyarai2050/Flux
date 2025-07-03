import { DATA_TYPES } from '../../constants';


/**
 * Capitalizes the first letter of a given string.
 * If the input is null, undefined, or an empty string, it returns the input as is.
 * @param {string} text - The input string.
 * @returns {string} The string with its first letter capitalized, or the original input if invalid.
 */
export function capitalizeFirstLetter(text) {
    // Check if the text is valid (not null, undefined, or empty).
    if (text && text.length > 0) {
        // Capitalize the first character and concatenate with the rest of the string.
        return text.charAt(0).toUpperCase() + text.slice(1);
    }
    return text;
}

/**
 * Converts the first letter of a given string to lowercase.
 * If the input is null, undefined, or an empty string, it returns the input as is.
 * @param {string} text - The input string.
 * @returns {string} The string with its first letter in lowercase, or the original input if invalid.
 */
export function lowerFirstLetter(text) {
    // Check if the text is valid (not null, undefined, or empty).
    if (text && text.length > 0) {
        // Convert the first character to lowercase and concatenate with the rest of the string.
        return text.charAt(0).toLowerCase() + text.slice(1);
    }
    return text;
}

/**
 * Converts a snake_case string (e.g., 'some_text') to PascalCase (e.g., 'SomeText').
 * Each word separated by an underscore will have its first letter capitalized.
 * @param {string} text - The input string in snake_case.
 * @returns {string} The converted string in PascalCase, or the original input if invalid.
 */
export function capitalizeCamelCase(text) {
    if (text && text.length > 0) {
        // Split the string by underscore, capitalize the first letter of each word, and join them.
        let textSplit = text.split('_').map(t => t.charAt(0).toUpperCase() + t.slice(1));
        return textSplit.join('');
    }
    return text;
}

/**
 * Converts a snake_case string (e.g., 'some_text') to camelCase (e.g., 'someText').
 * The first word remains lowercase, and subsequent words separated by underscores are capitalized.
 * @param {string} text - The input string in snake_case.
 * @returns {string} The converted string in camelCase, or the original input if invalid.
 */
export function toCamelCase(text) {
    if (text && text.length > 0) {
        let textSplit = text.split('_');
        // Capitalize the first letter of each word from the second word onwards.
        for (let i = 1; i < textSplit.length; i++) {
            let value = textSplit[i];
            value = value.charAt(0).toUpperCase() + value.slice(1);
            textSplit[i] = value;
        }
        return textSplit.join('');
    }
    return text;
}

/**
 * Generates an icon text from a snake_case string by taking the first letter of each word and capitalizing it.
 * For example, 'some_text' would become 'ST'.
 * @param {string} text - The input string in snake_case.
 * @returns {string} The generated icon text.
 */
export function getIconText(text) {
    let textSplit = text.split('_');
    let iconText = '';
    // Iterate through each word and append its capitalized first letter to iconText.
    for (let i = 0; i < textSplit.length; i++) {
        iconText += textSplit[i][0].toUpperCase();
    }
    return iconText;
}

/**
 * Checks if a given string is a valid JSON string.
 * It attempts to parse the string after removing backslashes and returns true if successful, false otherwise.
 * @param {string} jsonString - The string to validate.
 * @returns {boolean} True if the string is a valid JSON string, false otherwise.
 */
export function isValidJsonString(jsonString) {
    if (typeof (jsonString) !== DATA_TYPES.STRING) return false;
    // Remove backslashes, as they can interfere with JSON parsing if not properly escaped.
    jsonString = jsonString.replace(/\\/g, '');
    try {
        JSON.parse(jsonString);
    } catch (e) {
        return false;
    }
    return true;
}

/**
 * Converts a snake_case string to PascalCase.
 * Special handling for 'ui' word, which will be converted to 'UI'.
 * @param {string} snakeStr - The snake_case string.
 * @returns {string} - The PascalCase string.
 */
export function snakeToPascal(snakeStr) {
    return snakeStr
        .split('_')
        .map(word => word === 'ui' ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1))
        .join('');
}
