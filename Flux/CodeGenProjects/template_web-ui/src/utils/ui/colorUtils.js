import { get } from 'lodash';
import { COLOR_TYPES, COLOR_PRIORITY, DATA_TYPES } from '../../constants';

/**
 * Calculates the count for an alert bubble based on the provided data and source path.
 * The count can be derived from a number or the length of an array.
 * @param {Object} data - The data object containing the alert bubble source.
 * @param {string} bubbleSourcePath - The path within the data object to the alert bubble source (e.g., 'alerts.critical').
 * @returns {number} The calculated alert bubble count. Returns 0 if the source is not found or is invalid.
 */
export function getAlertBubbleCount(data, bubbleSourcePath) {
    let bubbleCount = 0;
    const bubbleSource = get(data, bubbleSourcePath);
    if (bubbleSource) {
        // If the source is a number, use it directly as the count.
        if (typeof bubbleSource === DATA_TYPES.NUMBER) {
            bubbleCount = bubbleSource;
        } else if (Array.isArray(bubbleSource)) {
            // If the source is an array, use its length as the count.
            bubbleCount = bubbleSource.length;
        }
    }
    return bubbleCount;
}

/**
 * Determines the color type based on a percentage value and a collection's color configuration.
 * The collection's color configuration is expected to be a comma-separated string of rules,
 * where each rule can be `value=COLOR_TYPE` or `value>COLOR_TYPE`.
 * For example: "50%=RED, 75%>ORANGE".
 * @param {Object} collection - The collection object containing the color configuration.
 * @param {number} percentage - The percentage value to evaluate against the color rules.
 * @returns {string} The determined color type from `COLOR_TYPES`. Defaults to `COLOR_TYPES.DEFAULT` if no rule matches.
 */
export function getColorTypeFromPercentage(collection, percentage) {
    let color = COLOR_TYPES.DEFAULT;
    if (collection && collection.color) {
        let colorSplit = collection.color.split(',');
        for (let i = 0; i < colorSplit.length; i++) {
            let valueColorSet = colorSplit[i].trim();
            // Check for 'equals' rule (e.g., "50%=RED").
            if (valueColorSet.indexOf('=') !== -1) {
                let [val, colorType] = valueColorSet.split('=');
                val = val.replace('%', '');
                try {
                    val = parseInt(val);
                    if (val === percentage) {
                        color = COLOR_TYPES[colorType];
                        break;
                    }
                } catch (e) {
                    // If parsing fails, break the loop as the format is unexpected.
                    break;
                }
            } else if (valueColorSet.indexOf('>') !== -1) {
                // Check for 'greater than' rule (e.g., "75%>ORANGE").
                let [val, colorType] = valueColorSet.split('>');
                val = val.replace('%', '');
                try {
                    val = parseInt(val);
                    if (val < percentage) {
                        color = COLOR_TYPES[colorType];
                        break;
                    }
                } catch (e) {
                    // If parsing fails, break the loop as the format is unexpected.
                    break;
                }
            }
        }
    }
    return color;
}

/**
 * Retrieves the color type with the highest priority from a set of color types.
 * The priority is determined by the `COLOR_PRIORITY` constant.
 * @param {Set<string>} colorTypesSet - A Set of color type strings (e.g., 'RED', 'GREEN').
 * @returns {string} The color type with the highest priority. Defaults to `COLOR_TYPES.DEFAULT` if the set is empty.
 */
export function getPriorityColorType(colorTypesSet) {
    let colorTypesArray = Array.from(colorTypesSet);
    if (colorTypesArray.length > 0) {
        // Sort the array based on the predefined COLOR_PRIORITY. Higher priority values come first.
        colorTypesArray.sort(function (a, b) {
            if (COLOR_PRIORITY[a] > COLOR_PRIORITY[b]) {
                return -1;
            }
            return 1;
        });
        return colorTypesArray[0];
    } else {
        return COLOR_TYPES.DEFAULT;
    }
}

/**
 * Determines the alert bubble color based on data, collections, and specified source paths.
 * It finds the relevant collection and then uses `getColorTypeFromValue` to get the color.
 * @param {Object} data - The data object containing the values.
 * @param {Array<Object>} collections - An array of collection objects, each potentially containing color configurations.
 * @param {string} bubbleSourcePath - The path to the source of the bubble data (e.g., 'alerts.count'). This parameter is currently unused in the function logic but is retained for consistency with other bubble-related functions.
 * @param {string} bubbleColorSourcePath - The path within the data object that determines the color (e.g., 'status.severity').
 * @returns {string} The determined color type from `COLOR_TYPES`. Defaults to `COLOR_TYPES.DEFAULT` if no color can be determined.
 */
export function getAlertBubbleColor(data, collections, bubbleSourcePath, bubbleColorSourcePath) {
    // Find the collection that matches the bubbleColorSourcePath.
    const collection = collections.find(col => col.tableTitle === bubbleColorSourcePath);
    if (collection) {
        // Get the value from the data object using the bubbleColorSourcePath.
        const value = get(data, bubbleColorSourcePath);
        // Determine the color type based on the collection's color rules and the retrieved value.
        const colorType = getColorTypeFromValue(collection, value);
        return colorType;
    }
    return COLOR_TYPES.DEFAULT;
}

/**
 * Determines the color type based on a value and a collection's color configuration.
 * The collection's color configuration is expected to be a comma-separated string of `value=COLOR_TYPE` rules.
 * It can also handle values that are part of a hyphen-separated string, checking each segment.
 * @param {Object} collection - The collection object containing the color configuration and potentially an XPath.
 * @param {*} value - The value to evaluate against the color rules.
 * @param {string} [separator='-'] - The separator used if the value is a string that needs to be split (e.g., for XPath segments).
 * @returns {string} The determined color type from `COLOR_TYPES`. Defaults to `COLOR_TYPES.DEFAULT` if no rule matches.
 */
export function getColorTypeFromValue(collection, value, separator = '-') {
    let color = COLOR_TYPES.DEFAULT;
    if (collection && collection.color) {
        const colorSplit = collection.color.split(',').map(valueColor => valueColor.trim());
        const valueColorMap = {};
        // Populate a map for quick lookup of value to color type.
        colorSplit.forEach(valueColor => {
            const [val, colorType] = valueColor.split('=');
            valueColorMap[val] = colorType;
        });

        let v = value;
        // If the collection's XPath indicates a multi-part value (e.g., "part1-part2"),
        // iterate through the parts of the value to find a matching color rule.
        if (collection.xpath.split('-').length > 1) {
            for (let i = 0; i < collection.xpath.split('-').length; i++) {
                v = value.split(separator)[i];
                if (valueColorMap.hasOwnProperty(v)) {
                    const colorType = valueColorMap[v];
                    // Try to get from COLOR_TYPES first, fallback to the color value itself
                    const color = COLOR_TYPES[colorType] || colorType;
                    return color;
                }
            }
        } else if (valueColorMap.hasOwnProperty(v)) {
            // If it's a single value, check for a direct match.
            const colorType = valueColorMap[v];
            // Try to get from COLOR_TYPES first, fallback to the color value itself
            const color = COLOR_TYPES[colorType] || colorType;
            return color;
        }
    }
    return color;
}

/**
 * Parses a schema color string (e.g., "KEY1=VALUE1,KEY2=VALUE2") into a map.
 * @param {string} colorString - The color mapping string from the schema.
 * @returns {Object} A map of key-value pairs (e.g., { KEY1: 'VALUE1' }).
 */
export const createColorMapFromString = (colorString) => {
    if (!colorString || typeof colorString !== 'string') {
        return {};
    }
    const colorMap = {};
    colorString.split(',').forEach((pair) => {
        const [key, value] = pair.split('=');
        if (key && value) {
            colorMap[key.trim().toUpperCase()] = value.trim().toUpperCase();
        }
    });
    return colorMap;
};

export const getJoinColor = (joinType, colorMappingString, theme, isConfirmed = true) => {
    const colorMap = createColorMapFromString(colorMappingString);

    const joinKey = joinType?.toUpperCase();
    const schemaColorType = colorMap[joinKey]; // Will be undefined if not found

    // Use getResolvedColor to handle all color types (theme colors, CSS colors, etc.)
    const color = getResolvedColor(schemaColorType, theme, theme.palette.grey[500]);

    if (isConfirmed) {
        return color;
    } else {
        // Add opacity for unconfirmed suggestions
        if (color.startsWith('#')) {
            // Hex color - add opacity suffix
            return `${color}30`;  // 30 in hex = ~18% opacity
        } else if (color.startsWith('rgb(')) {
            // Convert rgb() to rgba() with opacity
            return color.replace('rgb(', 'rgba(').replace(')', ', 0.18)');
        } else if (color.startsWith('rgba(')) {
            // Already rgba, modify the alpha value
            return color.replace(/,\s*[\d.]+\)$/, ', 0.18)');
        } else {
            // For named colors, theme colors, etc., use CSS with opacity
            // Create a semi-transparent version by mixing with transparent
            // This preserves the color while adding opacity
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = color;
            const computedColor = ctx.fillStyle;

            // If we got a valid color, convert it to rgba
            if (computedColor.startsWith('#')) {
                return `${computedColor}30`;
            } else if (computedColor.startsWith('rgb(')) {
                return computedColor.replace('rgb(', 'rgba(').replace(')', ', 0.18)');
            } else {
                // Fallback: create a semi-transparent overlay effect
                return `rgba(0, 0, 0, 0.18)`;
            }
        }
    }
};

/**
 * Resolves a color identifier to a final CSS color value or style object with animation.
 * It first checks if the identifier is a key in the theme's text palette.
 * If not, it assumes the identifier is a valid CSS color itself.
 * For critical colors, it returns a style object with blinking animation when returnAsStyle=true.
 * @param {string} colorIdentifier - The color identifier to resolve (e.g., 'positive', 'red', '#FF5733', 'critical').
 * @param {Object} theme - The MUI theme object.
 * @param {string} [defaultColor=null] - The default color to return if the identifier is falsy.
 * @param {boolean} [returnAsStyle=false] - If true, returns a style object; if false, returns color string.
 * @returns {string|Object|null} The resolved CSS color string, style object, or the default color.
 */
export const getResolvedColor = (colorIdentifier, theme, defaultColor = null, returnAsStyle = false) => {
    if (!colorIdentifier) {
        return returnAsStyle ? (defaultColor ? { color: defaultColor } : {}) : defaultColor;
    }

    let resolvedColor;

    // 1. Check if the identifier is a key in the theme's text palette
    if (theme?.palette?.text?.[colorIdentifier]) {
        resolvedColor = theme.palette.text[colorIdentifier];
    }
    // 2. Check if the identifier is a semantic color (debug, info, error, etc.)
    // Try both the original case and lowercase for case-insensitive matching
    else if (theme?.palette?.[colorIdentifier]?.main) {
        resolvedColor = theme.palette[colorIdentifier].main;
    }
    else if (theme?.palette?.[colorIdentifier.toLowerCase()]?.main) {
        resolvedColor = theme.palette[colorIdentifier.toLowerCase()].main;
    }
    // 3. If not, assume it's a direct CSS color (e.g., 'red', '#FFF', 'rgb(0,0,0)')
    else {
        resolvedColor = colorIdentifier;
    }

    // 3. For critical colors, return style object with blinking animation only when returnAsStyle=true
    // Note: We only set backgroundColor for critical, not color (text color should remain readable)
    if (colorIdentifier === 'critical' && returnAsStyle) {
        return {
            backgroundColor: resolvedColor,
            color: 'white', // Ensure text is readable on critical background
            animation: 'blink 0.5s step-start infinite',
            '@keyframes blink': {
                from: { opacity: 1 },
                '50%': { opacity: 0.8 },
                to: { opacity: 1 }
            }
        };
    }

    // 4. Return as style object if requested, otherwise return color string
    if (returnAsStyle) {
        return { color: resolvedColor };
    }

    return resolvedColor;
};
