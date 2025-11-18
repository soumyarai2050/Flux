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
 * @param {boolean} [isBackgroundColor=false] - If true, returns backgroundColor style instead of text color.
 * @returns {string|Object|null} The resolved CSS color string, style object, or the default color.
 */
export const getResolvedColor = (colorIdentifier, theme, defaultColor = null, returnAsStyle = false, isBackgroundColor = false) => {
    if (!colorIdentifier) {
        return returnAsStyle ? (defaultColor ? { color: defaultColor } : {}) : defaultColor;
    }

    // Check for critical color BEFORE resolving to handle animation
    const isCritical = colorIdentifier === 'critical' || colorIdentifier?.toLowerCase?.() === 'critical';

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

    // For critical colors, return style object with blinking animation only when returnAsStyle=true
    if (isCritical && returnAsStyle) {
        if (isBackgroundColor) {
            // For critical chips, use backgroundColor with white text and blinking animation
            return {
                backgroundColor: resolvedColor,
                color: 'white',
                padding: '4px 12px',
                borderRadius: '16px',
                display: 'inline-block',
                width: 'fit-content',
                animation: 'blink 0.5s step-start infinite',
                '@keyframes blink': {
                    from: { opacity: 1 },
                    '50%': { opacity: 0.8 },
                    to: { opacity: 1 }
                }
            };
        }
        // For critical non-chip, use text color with blinking animation
        return {
            color: resolvedColor,
            animation: 'blink 0.5s step-start infinite',
            '@keyframes blink': {
                from: { opacity: 1 },
                '50%': { opacity: 0.8 },
                to: { opacity: 1 }
            }
        };
    }

    // Return as style object if requested, otherwise return color string
    if (returnAsStyle) {
        if (isBackgroundColor) {
            // For chip display, return backgroundColor style
            return { backgroundColor: resolvedColor };
        }
        return { color: resolvedColor };
    }

    return resolvedColor;
};

/**
 * COMPREHENSIVE RANGE SPECIFICATION GUIDE
 * ========================================
 *
 * FORMATS SUPPORTED:
 *
 * 1. EXACT MATCH (Highest Priority)
 *    "70=yellow"         → color is yellow only when value exactly equals 70
 *    "CRITICAL=critical" → enum exact match
 *
 * 2. RANGE OPERATORS (Lower Priority, First Match Wins)
 *    "70>=green"         → color is green when value >= 70
 *    "50>orange"         → color is orange when value > 50
 *    "30<=red"           → color is red when value <= 30
 *    "10<critical"       → color is critical when value < 10
 *
 * 3. MIXED OPERATORS (Exact match takes precedence)
 *    "70>=green, 70=yellow, 50>=orange"
 *    value=70   → yellow (exact match wins)
 *    value=60   → orange (first matching range)
 *    value=80   → green  (first matching range)
 *
 * 4. PERCENTAGE FORMAT (Same rules apply)
 *    "100%=success"      → exact percentage match
 *    "90%>=good"         → percentage >= 90
 *    "50%>okay"          → percentage > 50
 *    "0%=bad"            → exact percentage match for 0
 *
 * RESOLUTION PRIORITY (Highest to Lowest):
 * 1. Exact match (=) - always wins if matches
 * 2. First matching range operator (>=, >, <=, <)
 * 3. Default color
 */

/**
 * Parses a single range rule into structured format
 * @private
 * @param {string} rule - Single rule string (e.g., "70>=green", "50=yellow")
 * @param {boolean} isPercentage - Whether this is percentage-based
 * @returns {Object|null} Parsed rule with {threshold, operator, color, specificity} or null if invalid
 */
const parseRangeRule = (rule, isPercentage = false) => {
    if (!rule || typeof rule !== 'string') return null;

    // List of operators to check (order matters - check >= before >)
    const operators = ['>=', '<=', '=', '>', '<'];

    for (const operator of operators) {
        const index = rule.indexOf(operator);
        if (index > -1) {
            const thresholdPart = rule.substring(0, index).trim();
            const colorPart = rule.substring(index + operator.length).trim();

            if (!thresholdPart || !colorPart) continue;

            // Remove % if present
            const numStr = thresholdPart.replace('%', '').trim();
            const threshold = parseFloat(numStr);

            if (isNaN(threshold)) continue;

            return {
                threshold,
                operator,
                color: colorPart,
                specificity: getOperatorSpecificity(operator),
                isPercentage
            };
        }
    }

    return null;
};

/**
 * Gets specificity score for an operator (higher = higher priority)
 * @private
 * @param {string} operator - The operator (=, >=, >, <=, <)
 * @returns {number} Specificity score
 */
const getOperatorSpecificity = (operator) => {
    const specificity = {
        '=': 3,    // Highest - exact match always wins
        '>=': 2,   // Range operators
        '>': 2,
        '<=': 2,
        '<': 2
    };
    return specificity[operator] || 1;
};

/**
 * Evaluates if a rule matches the given value
 * @private
 * @param {Object} rule - Parsed rule object
 * @param {number} value - Value to test
 * @returns {boolean} True if rule matches
 */
const evaluateRule = (rule, value) => {
    const { threshold, operator } = rule;

    switch (operator) {
        case '=':
            return value === threshold;
        case '>=':
            return value >= threshold;
        case '>':
            return value > threshold;
        case '<=':
            return value <= threshold;
        case '<':
            return value < threshold;
        default:
            return false;
    }
};

/**
 * Unified color resolution system that auto-detects format and supports ALL color types.
 * Handles percentage ranges, numeric ranges, value mappings, and direct colors in a single function.
 * Uses specificity-based resolution: exact matches (=) have highest priority, then first matching range.
 *
 * @param {Object} collection - The collection object containing color configuration
 * @param {*} value - The value to evaluate against color rules
 * @param {number} [percentage=null] - Optional percentage value for percentage-based ranges
 * @param {Object} theme - The MUI theme object for color resolution (optional, for inline styles)
 * @param {string} [defaultColor=null] - Default color if no rules match
 * @param {boolean} [returnResolvedColor=false] - If true, returns resolved CSS color; if false, returns color identifier
 * @returns {string} The color identifier (e.g., 'CRITICAL', 'ERROR') or resolved CSS color if returnResolvedColor=true
 */
export const getColorFromMapping = (collection, value, percentage = null, theme, defaultColor = null, returnResolvedColor = false) => {
    if (!collection || !collection.color) {
        return defaultColor || COLOR_TYPES.DEFAULT;
    }

    const colorString = collection.color.trim();

    // Auto-detect format and parse accordingly
    const colorRules = colorString.split(',').map(rule => rule.trim());

    // Check if this is a percentage-based format (contains %)
    const isPercentageFormat = colorRules.some(rule => rule.includes('%'));

    // Check if this is a numeric range format (contains range operators with numbers)
    const isNumericRangeFormat = !isPercentageFormat && colorRules.some(rule => {
        const match = rule.match(/^(\d+(?:\.\d+)?)\s*(?:>=|>|<=|<|=)\s*(.+)$/);
        return match !== null;
    });

    let colorIdentifier;
    // Determine which parsing strategy to use
    if (isPercentageFormat && percentage !== null) {
        colorIdentifier = resolvePercentageColor(colorRules, percentage, defaultColor);
    } else if (isNumericRangeFormat && typeof value === 'number') {
        colorIdentifier = resolveNumericRangeColor(colorRules, value, defaultColor);
    } else {
        // Value mapping format (handles both enum/string values and direct colors)
        colorIdentifier = resolveValueMappingColor(collection, value, defaultColor);
    }

    // If theme is provided and returnResolvedColor is true, resolve to CSS color
    if (returnResolvedColor && theme) {
        return getResolvedColor(colorIdentifier, theme, defaultColor);
    }

    return colorIdentifier;
};

/**
 * Resolves color for percentage-based ranges using specificity rules
 * Priority: exact match (=) > first matching range (>=, >, <=, <)
 * @private
 * @returns {string} Color identifier (not resolved to CSS)
 */
const resolvePercentageColor = (colorRules, percentage, defaultColor) => {
    // Parse all rules
    const parsedRules = colorRules
        .map(rule => parseRangeRule(rule, true))
        .filter(rule => rule !== null);

    // Separate into exact matches and range matches
    const exactMatches = [];
    const rangeMatches = [];

    for (const rule of parsedRules) {
        if (evaluateRule(rule, percentage)) {
            if (rule.operator === '=') {
                exactMatches.push(rule);
            } else {
                rangeMatches.push(rule);
            }
        }
    }

    // Return first exact match if any exist (highest priority)
    if (exactMatches.length > 0) {
        return exactMatches[0].color;
    }

    // Return first range match (order preserved from original rules)
    if (rangeMatches.length > 0) {
        return rangeMatches[0].color;
    }

    return defaultColor || COLOR_TYPES.DEFAULT;
};

/**
 * Resolves color for numeric value ranges using specificity rules
 * Priority: exact match (=) > first matching range (>=, >, <=, <)
 * @private
 * @returns {string} Color identifier (not resolved to CSS)
 */
const resolveNumericRangeColor = (colorRules, value, defaultColor) => {
    // Parse all rules
    const parsedRules = colorRules
        .map(rule => parseRangeRule(rule, false))
        .filter(rule => rule !== null);

    // Separate into exact matches and range matches
    const exactMatches = [];
    const rangeMatches = [];

    for (const rule of parsedRules) {
        if (evaluateRule(rule, value)) {
            if (rule.operator === '=') {
                exactMatches.push(rule);
            } else {
                rangeMatches.push(rule);
            }
        }
    }

    // Return first exact match if any exist (highest priority)
    if (exactMatches.length > 0) {
        return exactMatches[0].color;
    }

    // Return first range match (order preserved from original rules)
    if (rangeMatches.length > 0) {
        return rangeMatches[0].color;
    }

    return defaultColor || COLOR_TYPES.DEFAULT;
};

/**
 * Resolves color for value-to-color mappings
 * Supports both enum/string values and direct colors
 * @private
 * @returns {string} Color identifier (not resolved to CSS)
 */
const resolveValueMappingColor = (collection, value, defaultColor) => {
    const colorString = collection.color.trim();
    const colorRules = colorString.split(',').map(rule => rule.trim());
    const valueColorMap = {};

    // Build the mapping
    colorRules.forEach(rule => {
        const [val, colorPart] = rule.split('=');
        if (val && colorPart) {
            valueColorMap[val.trim()] = colorPart.trim();
        }
    });

    // Convert value to string for matching (handles boolean, number, enum values)
    const stringValue = String(value);

    // Check for direct match
    let colorValue = valueColorMap[stringValue];
    if (colorValue) {
        return colorValue;
    }

    // Check for multi-part XPath values (e.g., "part1-part2")
    if (collection.xpath && collection.xpath.split('-').length > 1 && typeof stringValue === 'string') {
        const valueParts = stringValue.split('-');
        for (let i = 0; i < valueParts.length; i++) {
            const part = valueParts[i];
            if (valueColorMap[part]) {
                return valueColorMap[part];
            }
        }
    }

    // No match found, return default
    return defaultColor || COLOR_TYPES.DEFAULT;
};
