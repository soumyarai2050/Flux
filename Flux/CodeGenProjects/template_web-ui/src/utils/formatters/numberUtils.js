import { DATA_TYPES } from '../../constants';


/**
 * Normalizes a given value to a percentage within a specified range.
 * If the value, max, or min are not numbers, it returns 0.
 * The returned percentage is capped at 100.
 * @param {number} value - The value to normalize.
 * @param {number} max - The maximum value of the range.
 * @param {number} min - The minimum value of the range.
 * @returns {number} The normalized percentage (0-100), or 0 if inputs are invalid.
 */
export function normalise(value, max, min) {
    // Check if all inputs are numbers.
    if (typeof (value) === DATA_TYPES.NUMBER && typeof (min) === DATA_TYPES.NUMBER && typeof (max) === DATA_TYPES.NUMBER) {
        // Calculate the percentage.
        let percentage = ((value - min) * 100) / (max - min);
        // Cap the percentage at 100.
        return percentage > 100 ? 100 : percentage;
    }
    return 0;
}

/**
 * Checks if a numeric value falls within a specified minimum and/or maximum range.
 * @param {number} value - The numeric value to check.
 * @param {number} [min] - The minimum allowed value (inclusive). If undefined, no minimum check is performed.
 * @param {number} [max] - The maximum allowed value (inclusive). If undefined, no maximum check is performed.
 * @returns {boolean} True if the value is within the allowed range, false otherwise.
 */
export function isAllowedNumericValue(value, min, max) {
    // Check if both min and max are defined.
    if (min !== undefined && max !== undefined) {
        return min <= value && value <= max;
    } else if (min !== undefined) {
        // Check only if min is defined.
        return min <= value;
    } else if (max !== undefined) {
        // Check only if max is defined.
        return value <= max;
    }
    // If neither min nor max is defined, any value is allowed.
    return true;
}

/**
 * Default precision for floating-point numbers, typically used for rounding.
 * @type {number}
 */
export const FLOAT_POINT_PRECISION = 2;

/**
 * Converts a floating-point number to an integer by truncating the decimal part.
 * For positive numbers, it uses `Math.floor()`; for negative numbers, it uses `Math.ceil()`.
 * If the input is not a number, it returns the value as is.
 * @param {number} value - The number to convert.
 * @returns {number} The integer representation of the number.
 */
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
                return Math.floor(value); // For positive numbers, truncate towards zero.
            } else {
                return Math.ceil(value); // For negative numbers, truncate towards zero.
            }
        }
    }
    return value;
}

/**
 * Normalizes numbers and appends adornments (like %, bps, $) based on metadata.
 * It also handles rounding based on `numberFormat` and `displayType`.
 * @param {Object} metadata - Contains properties of the field, including `numberFormat` and `displayType`.
 * @param {*} value - The field value to normalize and format.
 * @returns {[string, *]} A tuple containing the adornment string and the formatted value.
 */
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
        return [adornment, floatToInt(value)];
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

/**
 * Rounds a floating-point number to a specified precision.
 * If the value is an integer or precision is 0, it returns the value as is.
 * @param {number} value - The floating-point number to round.
 * @param {number} [precision=FLOAT_POINT_PRECISION] - The number of decimal digits to round to. Defaults to `FLOAT_POINT_PRECISION` (2).
 * @returns {number} The rounded number.
 */
export function roundNumber(value, precision = FLOAT_POINT_PRECISION) {
    /*
    Function to round floating point numbers.
    value: floating point number
    precision: decimal digits to round off to. default 2 (FLOAT_POINT_PRECISION)
    */
    if (typeof value === DATA_TYPES.NUMBER) {
        // If the value is an integer or precision is 0, no rounding is needed.
        if (Number.isInteger(value) || precision === 0) {
            return value;
        } else {
            // Use toFixed to round and then convert back to a number.
            return +value.toFixed(precision);
        }
    }
    return value;
}