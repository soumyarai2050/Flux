import { DATA_TYPES } from '../../constants';
import { Message } from '../core/errorUtils';


/**
 * Validates a given value against a set of constraints defined in metadata, including minimum, maximum, and required fields.
 * This function is used to check if a field's value adheres to the specified validation rules.
 *
 * @param {Object} metadata - Contains all properties (and constraints) of the field.
 * @param {*} value - The field value to validate.
 * @param {number} [min] - The minimum allowed value for the field.
 * @param {number} [max] - The maximum allowed value for the field.
 * @returns {string|null} A comma-separated string of error messages if constraints are violated, otherwise null.
 */
export function validateConstraints(metadata, value, min, max) {
    const errors = [];

    // disabled ignoring constraint checks on serverPopulate field
    // if (metadata.serverPopulate) {
    //     // if field is populated from server, ignore constaint checks
    //     return null;
    // }

    // Treat empty strings as null or unset for validation purposes.
    if (value === '') {
        value = null;
    }
    // Check if a required field is missing (null).
    if (metadata.required) {
        if (value === null) {
            errors.push(Message.REQUIRED_FIELD);
        }
        // else not required: value is set
    }
    // Check if an enum field has an "UNSPECIFIED" value when it's required.
    if (metadata.type === DATA_TYPES.ENUM && metadata.required) {
        if (value && value.includes('UNSPECIFIED')) {
            errors.push(Message.UNSPECIFIED_FIELD);
        }
        // else not required: value is set
    }
    // Check if the field violates the minimum requirement.
    if (typeof min === DATA_TYPES.NUMBER) {
        if (value !== undefined && value !== null && value < min) {
            errors.push(Message.MIN + ': ' + min);
        }
    }
    // Check if the field violates the maximum requirement.
    if (typeof max === DATA_TYPES.NUMBER) {
        if (value !== undefined && value !== null && value > max) {
            errors.push(Message.MAX + ': ' + max);
        }
    }

    // If no constraints are violated, return null; otherwise, return a comma-separated string of error messages.
    return errors.length ? errors.join(', ') : null;
}
