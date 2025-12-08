import { get } from 'lodash';
import { COLOR_TYPES, COLOR_PRIORITY, DATA_TYPES } from '../../constants';
import { capitalizeCamelCase } from '../core/stringUtils';

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

/**
 * Resolves the actual color value/rules from a source field path.
 * Handles two formats:
 * 1. Simple: "model.field"
 * 2. Custom rule: "model.field|5>ERROR"
 *
 * Looks up source field in Redux and applies color rules. For REPEATED_ROOT models,
 * uses current row data (same-row optimization) when available.
 *
 * NOTE: Percentage format (3-part pipe-delimited) is NO LONGER supported.
 * Use the dedicated color_percentage and background_color_percentage properties instead.
 *
 * @param {string} colorSourcePath - Color source path (e.g., "status_field" or "model.field|5>ERROR")
 * @param {Object} fullData - Redux reducer dict (e.g., { portfolio_limits: { stored..., selected..., etc } })
 * @param {number|string} sourceValue - Current field's value (for direct evaluation, ignored for colorSrc)
 * @param {number} [percentage=null] - Not used (deprecated)
 * @param {Object} allCollections - schemaCollections from Redux
 * @param {Object} theme - MUI theme object
 * @param {string} [colorType='foreground'] - 'foreground' or 'background' (for source field rule selection)
 * @param {string} [currentModelName=null] - Current field's model name (for same-row optimization)
 * @param {Object} [currentRowData=null] - Current row's data (for same-row optimization in REPEATED_ROOT models)
 * @param {string} [currentXpath=null] - Current field's xpath (for array index extraction in REPEATED_ROOT)
 * @returns {string|null} The color identifier from source field's color rules, or null if not found
 */
export const resolveColorFromSource = (colorSourcePath, fullData, sourceValue, percentage = null, allCollections = null, theme = null, colorType = 'foreground', currentModelName = null, currentRowData = null, currentXpath = null) => {
    if (!colorSourcePath || !fullData) {
        return null;
    }

    // Parse pipe-delimited format: strict validation (0 or 1 pipes only)
    // Valid: "model.field" (simple) or "model.field|5>ERROR" (custom rule)
    // Invalid: 2+ pipes (e.g., old 3-pipe percentage format) → reject
    const parsed = parseColorSourceFormat(colorSourcePath);

    if (parsed.format === 'invalid') {
        console.warn(
            `Invalid color_src/background_color_src format: "${colorSourcePath}"\n` +
            `Expected: "source_field" or "source_field|rule"\n` +
            `For percentage-based coloring, use "color_percentage" or "background_color_percentage" property instead.`
        );
        return null;
    }

    // Validate custom rule format if present
    if (parsed.format === 'custom' && parsed.customRule) {
        const isValidCustomRule = isValidColorRule(parsed.customRule);
        if (!isValidCustomRule) {
            console.warn(
                `Invalid custom rule in color_src/background_color_src: "${parsed.customRule}"\n` +
                `Expected format: "[number][operator][color]"\n` +
                `Examples: "5>ERROR", "10>=WARNING", "-100<orange"\n` +
                `Operators: >= > <= < =`
            );
            return null;
        }
    }

    let actualPath = parsed.sourcePath || colorSourcePath;
    let customRule = parsed.customRule || null;

    try {
        let sourceCollection = null;
        let sourceFieldValue = sourceValue;

        // If fullData is an array (array of collections from CommonKey), find the source field in it
        if (Array.isArray(fullData)) {
            const sourceCollObj = fullData.find(col =>
                col.key === actualPath || col.identifier === actualPath
            );
            if (sourceCollObj) {
                sourceCollection = sourceCollObj;
                sourceFieldValue = sourceCollObj.value;
            }
        } else {
            // If fullData is an object, navigate using XPath with lodash get
            sourceFieldValue = get(fullData, actualPath);

            // SAME-ROW OPTIMIZATION: For REPEATED_ROOT models, prefer current row data over Redux
            if (sourceFieldValue === undefined && actualPath.includes('.')) {
                const parts = actualPath.split('.');
                const sourceModelName = parts[0];
                const sourceFieldPath = parts.slice(1).join('.');  // Supports nested paths like "rt_dash.leg1.exch_id"

                // Check if source model matches current model (same-row optimization)
                if (sourceModelName === currentModelName && currentRowData) {
                    // Try both the field path directly and the full "model.field" format
                    // (in case extractCellDataDependencies stored it with full path key)
                    sourceFieldValue = get(currentRowData, sourceFieldPath) || get(currentRowData, actualPath);
                }
            }

            // If still not found with direct path, try searching inside stored data objects (for Redux reducer structure)
            // Supports both simple paths (model.field) and nested paths (model.nested.field.subfield)
            if (sourceFieldValue === undefined && actualPath.includes('.')) {
                const parts = actualPath.split('.');
                const sourceModelName = parts[0];
                const sourceFieldPath = parts.slice(1).join('.');  // Supports nested paths like "rt_dash.leg1.exch_id"

                const modelData = fullData[sourceModelName];
                if (modelData) {
                    // Convert snake_case model name to PascalCase for key construction
                    // e.g., "portfolio_limits" → "PortfolioLimits" → "storedPortfolioLimitsObj"
                    const modelNamePascalCase = capitalizeCamelCase(sourceModelName);

                    // Try storedObj first (e.g., storedPortfolioLimitsObj)
                    // Use lodash get to support nested paths
                    const storedObjKey = 'stored' + modelNamePascalCase + 'Obj';
                    if (modelData[storedObjKey]) {
                        sourceFieldValue = get(modelData[storedObjKey], sourceFieldPath);
                    }
                    // If still not found, try storedArray (use first element)
                    if (sourceFieldValue === undefined) {
                        const storedArrayKey = 'stored' + modelNamePascalCase + 'Array';
                        if (Array.isArray(modelData[storedArrayKey]) && modelData[storedArrayKey].length > 0) {
                            sourceFieldValue = get(modelData[storedArrayKey][0], sourceFieldPath);
                        }
                    }
                }
            }

            // Look up the source field's collection from allCollections map
            const sourceFieldKey = actualPath.split('.').pop();
            // allCollections can be either:
            // 1. A flat object with field keys (legacy): { fieldName: collection, ... }
            // 2. A nested object with model keys (current): { modelName: [collections], ... }
            if (allCollections) {
                // Try direct lookup first (legacy format)
                sourceCollection = allCollections[sourceFieldKey];

                // If not found, try to find in nested model collections (current format)
                if (!sourceCollection && actualPath.includes('.')) {
                    const sourceModelName = actualPath.split('.')[0];
                    const modelCollections = allCollections[sourceModelName];
                    if (Array.isArray(modelCollections)) {
                        sourceCollection = modelCollections.find(col => col.key === sourceFieldKey || col.identifier === sourceFieldKey);
                    }
                }
            }
        }

        // If source field value doesn't exist, return null
        if (sourceFieldValue === undefined || sourceFieldValue === null) {
            return null;
        }

        // If we found the source field's collection and it has color rules, apply them
        if (sourceCollection) {
            // Priority: customRule > source field's appropriate color property
            let colorRules = customRule;
            if (!colorRules) {
                // Select only the appropriate property based on colorType (don't cross-fallback)
                if (colorType === 'background') {
                    colorRules = sourceCollection.backgroundColor;
                } else {
                    colorRules = sourceCollection.color;
                }
            }

            if (colorRules) {
                const rules = colorRules.trim().split(',').map(rule => rule.trim());
                const isPercentageFormat = rules.some(rule => rule.includes('%'));
                const isNumericRangeFormat = !isPercentageFormat && rules.some(rule => {
                    const match = rule.match(/^([+\-]?\d+(?:\.\d+)?)\s*(?:>=|>|<=|<|=)\s*(.+)$/);
                    return match !== null;
                });

                let colorIdentifier;
                if (isPercentageFormat && percentage !== null) {
                    colorIdentifier = resolvePercentageColor(rules, percentage, null);
                } else if (isNumericRangeFormat && typeof sourceFieldValue === 'number') {
                    colorIdentifier = resolveNumericRangeColor(rules, sourceFieldValue, null);
                } else {
                    colorIdentifier = resolveValueMappingColor(sourceCollection, sourceFieldValue, null);
                }

                return colorIdentifier;
            }
        }

        // If no collection found but source value is a string, return it as-is (might be a color identifier)
        if (typeof sourceFieldValue === 'string') {
            return sourceFieldValue;
        }

        return null;
    } catch (error) {
        console.warn(`Failed to resolve color from source path "${actualPath}":`, error);
        return null;
    }
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
 * 5. SIGNED PERCENTAGE FORMAT (For Deviation Mode)
 *    "+20%>=critical"    → positive deviation >= 20% (also: 20%>=critical without +)
 *    "+10%>=warning"     → positive deviation >= 10%
 *    "-10%<=warning"     → negative deviation <= -10%
 *    "-20%<=critical"    → negative deviation <= -20%
 *    Note: Numbers without sign prefix (e.g., "20%") are treated as positive
 *
 * RESOLUTION PRIORITY (Highest to Lowest):
 * 1. Exact match (=) - always wins if matches
 * 2. First matching range operator (>=, >, <=, <)
 * 3. Default color
 */

/**
 * Parses a single range rule into structured format
 * Supports signed numbers for deviation mode (e.g., "+10%>=warning", "-10%<=error")
 * @private
 * @param {string} rule - Single rule string (e.g., "70>=green", "+10%>=warning", "-10%<=error")
 * @param {boolean} isPercentage - Whether this is percentage-based
 * @returns {Object|null} Parsed rule with {threshold, operator, color, specificity, isSigned} or null if invalid
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

            // Remove % if present and parse signed number
            const numStr = thresholdPart.replace('%', '').trim();

            // IMPORTANT: parseFloat preserves the sign, so +25 becomes 25 and -25 becomes -25
            // Don't use Math.abs() - we need to keep the signed value!
            const threshold = parseFloat(numStr);

            if (isNaN(threshold)) continue;

            // Determine if this rule has an explicit sign (+/-)
            const hasPlusSign = numStr.startsWith('+');
            const hasMinusSign = numStr.startsWith('-');
            const isSigned = hasPlusSign || hasMinusSign;

            const parsed = {
                threshold,  // This preserves sign: +25 → 25, -25 → -25
                operator,
                color: colorPart,
                specificity: getOperatorSpecificity(operator),
                isPercentage,
                isSigned
            };

            return parsed;
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
 * Supports color inheritance via color_src: if color_src is defined and color is not,
 * the function will resolve the color from the source field's rules.
 *
 * @param {Object} collection - The collection object containing color configuration
 * @param {*} value - The value to evaluate against color rules
 * @param {number} [percentage=null] - Optional percentage value for percentage-based ranges
 * @param {Object} theme - The MUI theme object for color resolution (optional, for inline styles)
 * @param {string} [defaultColor=null] - Default color if no rules match
 * @param {boolean} [returnResolvedColor=false] - If true, returns resolved CSS color; if false, returns color identifier
 * @param {Object} [colorSourceData=null] - The complete data object for resolving color_src dependencies
 * @param {Object} [allCollections=null] - All field collections from schema (for resolving source field's color rules)
 * @param {string} [colorType='foreground'] - 'foreground' for text color, 'background' for background color (affects which source property is used)
 * @returns {string} The color identifier (e.g., 'CRITICAL', 'ERROR') or resolved CSS color if returnResolvedColor=true
 */
export const getColorFromMapping = (collection, value, percentage = null, theme, defaultColor = null, returnResolvedColor = false, colorSourceData = null, allCollections = null, colorType = 'foreground') => {
    if (!collection) {
        return defaultColor || COLOR_TYPES.DEFAULT;
    }

    let colorString;

    // Priority 1: Use direct color property
    if (collection.color) {
        colorString = collection.color.trim();
    }
    // Priority 2: Resolve from color_src dependency
    else if (collection.colorSrc && colorSourceData) {
        // Pass colorSrc (may be pipe-delimited with rule) to resolveColorFromSource
        // Rule parsing happens inside resolveColorFromSource
        // Also pass colorType to ensure we only use the appropriate property from the source field
        const sourceColorId = resolveColorFromSource(collection.colorSrc, colorSourceData, value, percentage, allCollections, theme, colorType);
        if (sourceColorId) {
            // resolveColorFromSource already returns the final color identifier (e.g., 'ERROR', 'SUCCESS')
            // Return it directly without re-parsing
            if (returnResolvedColor && theme) {
                return getResolvedColor(sourceColorId, theme, defaultColor);
            }
            return sourceColorId;
        } else {
            // If colorSrc was set but no matching rule found, return null (not defaultColor)
            // This ensures the field has no color, rather than showing an unwanted default color
            return null;
        }
    }
    // Priority 3: No color defined
    else {
        return defaultColor || COLOR_TYPES.DEFAULT;
    }

    // Auto-detect format and parse accordingly
    const colorRules = colorString.split(',').map(rule => rule.trim());

    // Check if this is a percentage-based format (contains %)
    const isPercentageFormat = colorRules.some(rule => rule.includes('%'));

    // Check if this is a numeric range format (contains range operators with numbers)
    // Also supports signed numbers like +10 or -10 for deviation mode
    const isNumericRangeFormat = !isPercentageFormat && colorRules.some(rule => {
        const match = rule.match(/^([+\-]?\d+(?:\.\d+)?)\s*(?:>=|>|<=|<|=)\s*(.+)$/);
        return match !== null;
    });

    let colorIdentifier;
    // Determine which parsing strategy to use
    // NOTE: Pass null for defaultColor to the resolution functions so they return null when no rule matches
    // This ensures consistent behavior: if a color/backgroundColor rule is set but doesn't match, return null (not a default color)
    if (isPercentageFormat && percentage !== null) {
        colorIdentifier = resolvePercentageColor(colorRules, percentage, null);
    } else if (isNumericRangeFormat && typeof value === 'number') {
        colorIdentifier = resolveNumericRangeColor(colorRules, value, null);
    } else {
        // Value mapping format (handles both enum/string values and direct colors)
        colorIdentifier = resolveValueMappingColor(collection, value, null);
    }

    // If no rule matched and we have a colorString, return null (not defaultColor)
    // This ensures that if color/backgroundColor is explicitly set but no rule matches, no color is applied
    if (!colorIdentifier) {
        return null;
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
 * Used for both single-field percentage rules and two-field percentage coloring
 *
 * @param {Array<string>} colorRules - Array of rule strings (e.g., ["85%>=critical", "50%>warning"])
 * @param {number} percentage - Calculated percentage value (0-100)
 * @param {string} [defaultColor=null] - Default color if no rules match
 * @returns {string|null} Color identifier (not resolved to CSS) or null if no match
 */
export const resolvePercentageColor = (colorRules, percentage, defaultColor) => {
    // Parse all rules
    const parsedRules = colorRules
        .map(rule => parseRangeRule(rule, true))
        .filter(rule => rule !== null);

    // Separate into exact matches and range matches
    const exactMatches = [];
    const rangeMatches = [];

    for (const rule of parsedRules) {
        const ruleMatches = evaluateRule(rule, percentage);

        if (ruleMatches) {
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

    // Return range match with highest absolute threshold (most extreme/specific condition)
    // For example: if both -15%<=warning and -25%<=critical match,
    // return -25%<=critical because it's more specific (further from 0)
    if (rangeMatches.length > 0) {
        let bestMatch = rangeMatches[0];
        for (const match of rangeMatches) {
            if (Math.abs(match.threshold) > Math.abs(bestMatch.threshold)) {
                bestMatch = match;
            }
        }
        return bestMatch.color;
    }

    // Return null if defaultColor is null (indicates "no color" behavior)
    // Otherwise return defaultColor
    return defaultColor === null ? null : (defaultColor || COLOR_TYPES.DEFAULT);
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

    // Return null if defaultColor is null (indicates "no color" behavior)
    // Otherwise return defaultColor
    return defaultColor === null ? null : (defaultColor || COLOR_TYPES.DEFAULT);
};

/**
 * Resolves color for value-to-color mappings
 * Supports both enum/string values and direct colors
 * @private
 * @returns {string} Color identifier (not resolved to CSS)
 */
const resolveValueMappingColor = (collection, value, defaultColor) => {
    if (!collection.color) {
        return defaultColor || COLOR_TYPES.DEFAULT;
    }

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
    // Return null if defaultColor is null (indicates "no color" behavior)
    // Otherwise return defaultColor
    return defaultColor === null ? null : (defaultColor || COLOR_TYPES.DEFAULT);
};

/**
 * Applies color rules from a collection to a source field value.
 * This is used for color source inheritance (color_src, background_color_src).
 * Custom rules can be passed as a parameter (extracted from pipe-delimited colorSrc in component).
 *
 * @param {Object} sourceCollection - The source field's collection with color rules
 * @param {*} sourceValue - The value to apply color rules to
 * @param {number} percentage - Optional percentage value for percentage-based rules
 * @param {*} defaultColor - Default color if no rules match
 * @param {string} colorType - 'foreground' for text color, 'background' for background color
 * @param {string} [customRule=null] - Custom rule to use instead of source field's rule (extracted from pipe-delimited colorSrc)
 * @returns {string|null} The color identifier (e.g., 'SUCCESS', 'ERROR')
 */
export const applyColorRules = (sourceCollection, sourceValue, percentage = null, defaultColor = null, colorType = 'background', customRule = null) => {
    if (!sourceCollection) {
        return defaultColor === null ? null : (defaultColor || COLOR_TYPES.DEFAULT);
    }

    // Determine which rule to use
    // Priority: customRule > source field's property
    let colorRules = customRule;

    if (!colorRules) {
        // Fall back to source field's color property based on colorType
        colorRules = colorType === 'foreground' ? sourceCollection.color : sourceCollection.backgroundColor;
    }

    if (!colorRules) {
        // No color rules found - if defaultColor is null, return null (no color)
        // Otherwise return defaultColor or system default
        return defaultColor === null ? null : (defaultColor || COLOR_TYPES.DEFAULT);
    }

    const rules = colorRules.trim().split(',').map(rule => rule.trim());
    const isPercentageFormat = rules.some(rule => rule.includes('%'));
    const isNumericRangeFormat = !isPercentageFormat && rules.some(rule => {
        const match = rule.match(/^([+\-]?\d+(?:\.\d+)?)\s*(?:>=|>|<=|<|=)\s*(.+)$/);
        return match !== null;
    });

    let colorIdentifier;
    if (isPercentageFormat && percentage !== null) {
        colorIdentifier = resolvePercentageColor(rules, percentage, defaultColor);
    } else if (isNumericRangeFormat && typeof sourceValue === 'number') {
        colorIdentifier = resolveNumericRangeColor(rules, sourceValue, defaultColor);
    } else {
        colorIdentifier = resolveValueMappingColor(sourceCollection, sourceValue, defaultColor);
    }

    return colorIdentifier;
};

/**
 * Constructs the XPath for a source field based on current field's XPath.
 * For example: "[1].limit_up_px" → "[1].limit_dn_px"
 * @param {string} currentXpath - The XPath of the current field
 * @param {string} sourceFieldKey - The key of the source field
 * @returns {string} The XPath for the source field
 */
export const constructSourceFieldXpath = (currentXpath, sourceFieldKey) => {
    if (!currentXpath || !currentXpath.includes('.')) {
        return sourceFieldKey;
    }

    const lastDotIndex = currentXpath.lastIndexOf('.');
    return currentXpath.substring(0, lastDotIndex) + '.' + sourceFieldKey;
};

/**
 * Validates color rule format (both numeric and percentage-based)
 * Supports multiple comma-separated rules within a single rule string
 *
 * Valid numeric rules: "50>blue", "-10>=red", "100<green"
 * Valid percentage rules: "75%>pink", "50%<green", "0%=yellow"
 * Multiple rules: "50>blue,100>=red" or "75%>pink,50%<green"
 *
 * @param {string} rule - Color rule string to validate (may contain multiple rules separated by commas)
 * @returns {boolean} True if rule matches numeric or percentage comparison format
 */
export function isValidColorRule(rule) {
    if (!rule || typeof rule !== 'string') {
        return false;
    }

    // Split by comma to handle multiple rules
    const rules = rule.split(',').map(r => r.trim());

    return rules.every(singleRule => {
        if (!singleRule) {
            return false;
        }

        // Numeric rule: 50>blue, -10>=red, etc.
        const numericRuleRegex = /^([+\-]?\d+(?:\.\d+)?)\s*(?:>=|>|<=|<|=)\s*(.+)$/;

        // Percentage rule: 75%>pink, 50%<green, 0%=yellow, etc.
        const percentageRuleRegex = /^([+\-]?\d+(?:\.\d+)?)%\s*(?:>=|>|<=|<|=)\s*(.+)$/;

        // Value-based color map: Severity_CRITICAL=CRITICAL, status_ACTIVE=green, etc.
        // Matches: [key]=[value] where key can be alphanumeric/underscore, value can be alphanumeric/underscore or hex color
        const valueMapRuleRegex = /^([a-zA-Z0-9_]+)\s*=\s*([a-zA-Z0-9_#]+)$/;

        return numericRuleRegex.test(singleRule) || percentageRuleRegex.test(singleRule) || valueMapRuleRegex.test(singleRule);
    });
}

/**
 * Parses color source format and detects which type it is
 * Strictly validates format - only 0 or 1 pipes allowed
 *
 * Valid formats for color_src/background_color_src:
 * 1. Simple: "model.field" (0 pipes)
 * 2. Custom rule: "model.field|5>ERROR" (1 pipe)
 *
 * INVALID: 2+ pipes (e.g., 3-pipe percentage format) → returns format='invalid'
 * Use dedicated color_percentage and background_color_percentage properties for percentage-based coloring.
 *
 * @param {string} sourceXpath - Color source path (may contain pipe delimiters)
 * @returns {Object} Parsed format with detection results
 *   format: 'simple'|'custom'|'invalid'
 *   sourcePath: string (for simple/custom)
 *   customRule: string (for custom)
 */
export function parseColorSourceFormat(sourceXpath) {
    if (!sourceXpath || !sourceXpath.includes('|')) {
        // Simple format: no pipes
        return {
            format: 'simple',
            sourcePath: sourceXpath
        };
    }

    const parts = sourceXpath.split('|').map(p => p.trim());

    // Strict validation: only 1 pipe allowed (custom rule format: field|rule)
    if (parts.length === 2) {
        return {
            format: 'custom',
            sourcePath: parts[0],
            customRule: parts[1]
        };
    }

    // Invalid: 2+ pipes detected - reject the entire format
    // This includes old 3-pipe percentage format like "field|field|%rule"
    return {
        format: 'invalid',
        sourceXpath: sourceXpath
    };
}

/**
 * Validates that min/max paths are from the same model (same-row constraint)
 * Required for percentage-based coloring to work with row data
 *
 * @param {string} minPath - Min field path (e.g., "portfolio_limits.min_px")
 * @param {string} maxPath - Max field path (e.g., "portfolio_limits.max_px")
 * @param {string} currentModelName - Current field's model name
 * @returns {boolean} True if valid (all from same model)
 */
export function validatePercentageFormat(minPath, maxPath, currentModelName) {
    if (!minPath || !maxPath || !currentModelName) {
        return false;
    }

    const minModelName = minPath.split('.')[0];
    const maxModelName = maxPath.split('.')[0];

    return (
        minModelName === currentModelName &&
        maxModelName === currentModelName
    );
}

/**
 * Extracts field key from a path
 * Handles both simple paths and nested paths with array notation
 * Examples:
 *   "field" → "field"
 *   "nested.field" → "field"
 *   "array[0].nested.field" → "field"
 *
 * @param {string} path - Field path
 * @returns {string} Field key (last part)
 */
export function extractFieldKey(path) {
    if (!path || typeof path !== 'string') {
        return null;
    }

    // Split by dots and get last part
    const parts = path.split('.');
    const lastPart = parts[parts.length - 1];

    // Remove array notation if present: "field[0]" → "field"
    return lastPart.split('[')[0];
}

/**
 * Calculates color based on percentage within min-max range
 * Formula: percentage = ((value - min) / (max - min)) * 100
 *
 * Edge cases handled:
 * - Non-numeric values → return null
 * - min >= max (range <= 0) → return null
 * - Value outside range → negative/>100% percentage (may not match any rule)
 *
 * @param {number} minValue - Minimum value of range
 * @param {number} maxValue - Maximum value of range
 * @param {number} currentValue - Value to calculate percentage for
 * @param {string} rules - Percentage rules string (e.g., "85%>=critical,50%>warning")
 * @returns {string|null} Color identifier or null if invalid/no match
 */
export function calculatePercentageColor(minValue, maxValue, currentValue, rules) {
    // Validate all values are numeric
    if (typeof minValue !== 'number' || typeof maxValue !== 'number' || typeof currentValue !== 'number') {
        return null;
    }

    // Calculate range
    const range = maxValue - minValue;
    if (range <= 0) {
        return null;
    }

    // Calculate percentage
    const percentage = ((currentValue - minValue) / range) * 100;

    // Parse rules and evaluate
    const rulesList = rules.split(',').map(r => r.trim()).filter(r => r);
    return resolvePercentageColor(rulesList, percentage, null);
}

/**
 * Extracts array index for REPEATED_ROOT models
 * Uses three strategies in order:
 * 1. Selected object ID (if available)
 * 2. Array index from xpath pattern
 * 3. Default to index 0
 *
 * @param {string} xpath - XPath of current field (e.g., "[1].field.name")
 * @param {string} selectedId - Selected object ID from Redux
 * @param {Object} reducerData - Redux data for the model
 * @param {string} sourceModelName - Name of source model
 * @returns {number} Array index to use
 */
export function extractArrayIndex(xpath, selectedId, reducerData, sourceModelName) {
    if (!reducerData || !sourceModelName) {
        return 0;
    }

    // Strategy 1: Check for selected object ID
    const storedArrayKey = 'stored' + capitalizeCamelCase(sourceModelName) + 'Array';

    if (selectedId && Array.isArray(reducerData[storedArrayKey])) {
        const matchingIndex = reducerData[storedArrayKey].findIndex(item =>
            item?._id === selectedId || item?.id_val === selectedId
        );
        if (matchingIndex !== -1) {
            return matchingIndex;
        }
    }

    // Strategy 2: Extract array index from xpath pattern
    if (xpath) {
        const arrayIndexMatch = xpath.match(/^\[(\d+)\]/);
        if (arrayIndexMatch) {
            return parseInt(arrayIndexMatch[1], 10);
        }
    }

    // Strategy 3: Default to index 0
    return 0;
}

/**
 * Resolves color from percentage-based property (color_percentage or background_color_percentage)
 * Strictly validates 3-pipe percentage format: "min_field|max_field|90%>=critical,50%>warning"
 *
 * STRICT VALIDATION:
 * - Must have exactly 3 pipes (2 separators between 3 parts)
 * - Third part must contain '%' character
 * - Returns null if format doesn't match
 *
 * @param {string} percentageString - Format: "min_field|max_field|90%>=critical,50%>warning"
 * @param {number} currentValue - Current field value
 * @param {string} currentModelName - Current model name (for validation)
 * @param {object} currentRowData - Current row data (for extracting min/max values)
 * @returns {string|null} Color identifier or null
 */
export function resolveColorFromPercentage(
    percentageString,
    currentValue,
    currentModelName,
    currentRowData
) {
    if (!percentageString || !currentRowData) {
        return null;
    }

    // Strict validation: exactly 3 pipes (2 separators → 3 parts)
    const parts = percentageString.split('|').map(p => p.trim());

    if (parts.length !== 3) {
        console.warn(
            `Invalid color_percentage format: "${percentageString}"\n` +
            `Expected: "min_field|max_field|percentage_rules"\n` +
            `Example: "model.min_px|model.max_px|90%>=critical,50%>warning"`
        );
        return null;
    }

    // Validate third part contains percentage rules (must have '%')
    if (!parts[2].includes('%')) {
        console.warn(
            `Invalid color_percentage rules: "${parts[2]}"\n` +
            `Rules must contain percentage operators (%). Example: "90%>=critical,50%>warning"`
        );
        return null;
    }

    const [minPath, maxPath, rules] = parts;

    // Validate same-row constraint (all fields must be from same model)
    if (!validatePercentageFormat(minPath, maxPath, currentModelName)) {
        console.warn(`color_percentage: min and max fields must be from same model as current field`);
        return null;
    }

    // Extract field keys from paths
    const minFieldKey = extractFieldKey(minPath);
    const maxFieldKey = extractFieldKey(maxPath);

    // Get min/max values from current row data
    // Try full path first (for optimized row data), then try just field key
    let minValue = get(currentRowData, minPath);
    if (minValue === undefined) {
        minValue = get(currentRowData, minFieldKey);
    }

    let maxValue = get(currentRowData, maxPath);
    if (maxValue === undefined) {
        maxValue = get(currentRowData, maxFieldKey);
    }


    // Calculate and return percentage color
    const result = calculatePercentageColor(minValue, maxValue, currentValue, rules);
    return result;
}

/**
 * Centralized color resolution utility for both foreground and background colors
 * Handles color, colorSrc, and colorPercentage properties independently for each color type.
 *
 * Resolves colors using the following priority:
 * 1. Direct color property (color or backgroundColor)
 * 2. Source-based property (color_src or background_color_src)
 * 3. Percentage-based property (color_percentage or background_color_percentage)
 *
 * Returns an object containing:
 * - colorIdentifiers: { foreground, background } - raw color identifiers
 * - resolvedColors: { foreground, background } - CSS color values
 * - styles: { foreground, background } - MUI style objects (with animations for critical colors)
 * - colorSx: MUI sx object for use in component styling
 *
 * @param {Object} data - The data object (collection or props.data) with color properties
 * @param {number|string} fieldValue - The field's current value
 * @param {string} modelName - The model name (for percentage validation)
 * @param {Object} theme - MUI theme object
 * @param {Object} reducerDict - Redux reducer data for color_src resolution
 * @param {Object} schemaCollections - All schema collections
 * @returns {Object} Color resolution results with identifiers, resolved colors, and styles
 */
export function resolveFieldColors(
    data,
    fieldValue,
    modelName,
    theme,
    reducerDict,
    schemaCollections,
    colorRules = [],
    fieldName = null,
    currentRowData = null
) {
    const result = {
        colorIdentifiers: { foreground: null, background: null },
        resolvedColors: { foreground: null, background: null },
        styles: { foreground: null, background: null },
        colorSx: {}
    };

    if (!data || !theme) {
        return result;
    }

    // === PRIORITY 0: CHECK USER OVERRIDES FIRST (HIGHEST PRIORITY) ===
    // Override replaces the rule part of the existing schema rule with highest precedence
    // Strategy: Find override, identify which schema rule exists, replace its rule part with override
    if (fieldName && colorRules && colorRules.length > 0) {
        const override = colorRules.find(rule => rule.field_name === fieldName);
        if (override && (override.color_rule || override.background_color_rule)) {
            // Make a copy of data to avoid mutating original
            let modifiedData = { ...data };

            // Handle foreground override
            if (override.color_rule) {
                // Priority: direct color > colorSrc > colorPercentage
                if (data.color) {
                    // Case 1: Direct rule exists - replace it
                    modifiedData.color = override.color_rule;
                } else if (data.colorSrc) {
                    // Case 2: Source rule exists - replace the rule part
                    const parsed = parseColorSourceFormat(data.colorSrc);
                    if (parsed.format === 'simple') {
                        // No rule in colorSrc, add override rule: "sourcePath|overrideRule"
                        modifiedData.colorSrc = `${parsed.sourcePath}|${override.color_rule}`;
                    } else if (parsed.format === 'custom') {
                        // Replace existing rule: "sourcePath|overrideRule"
                        modifiedData.colorSrc = `${parsed.sourcePath}|${override.color_rule}`;
                    }
                } else if (data.colorPercentage) {
                    // Case 3: Percentage rule exists - replace only the rule part (keep min/max fields)
                    const percentageParts = data.colorPercentage.split('|');
                    if (percentageParts.length === 3) {
                        // Keep min and max fields, replace only the rule part
                        modifiedData.colorPercentage = `${percentageParts[0]}|${percentageParts[1]}|${override.color_rule}`;
                    } else {
                        // Invalid format, just set the override
                        modifiedData.colorPercentage = override.color_rule;
                    }
                } else {
                    // Case 4: No schema rule - apply override as direct rule
                    modifiedData.color = override.color_rule;
                }
            }

            // Handle background override (same logic)
            if (override.background_color_rule) {
                if (data.backgroundColor) {
                    modifiedData.backgroundColor = override.background_color_rule;
                } else if (data.backgroundColorSrc) {
                    const parsed = parseColorSourceFormat(data.backgroundColorSrc);
                    if (parsed.format === 'simple') {
                        modifiedData.backgroundColorSrc = `${parsed.sourcePath}|${override.background_color_rule}`;
                    } else if (parsed.format === 'custom') {
                        modifiedData.backgroundColorSrc = `${parsed.sourcePath}|${override.background_color_rule}`;
                    }
                } else if (data.backgroundColorPercentage) {
                    // Replace only the rule part (keep min/max fields)
                    const percentageParts = data.backgroundColorPercentage.split('|');
                    if (percentageParts.length === 3) {
                        // Keep min and max fields, replace only the rule part
                        modifiedData.backgroundColorPercentage = `${percentageParts[0]}|${percentageParts[1]}|${override.background_color_rule}`;
                    } else {
                        // Invalid format, just set the override
                        modifiedData.backgroundColorPercentage = override.background_color_rule;
                    }
                } else {
                    modifiedData.backgroundColor = override.background_color_rule;
                }
            }

            // Replace data with modified version for resolution
            data = modifiedData;
        }
    }

    // === FOREGROUND COLOR RESOLUTION ===
    if (data.color || data.colorSrc || data.colorPercentage) {
        let foregroundColor = '';

        if (data.color) {
            // Priority 1: Use direct color property
            foregroundColor = getColorFromMapping(
                data,
                fieldValue,
                null,
                theme,
                null,
                false,
                reducerDict,
                schemaCollections,
                'foreground'
            );
        } else if (data.colorSrc) {
            // Priority 2: Resolve from source field
            foregroundColor = resolveColorFromSource(
                data.colorSrc,
                reducerDict,
                fieldValue,
                null,
                schemaCollections,
                theme,
                'foreground',
                modelName,
                currentRowData,
                data.xpath
            );
        } else if (data.colorPercentage) {
            // Priority 3: Use dedicated percentage property
            foregroundColor = resolveColorFromPercentage(
                data.colorPercentage,
                fieldValue,
                modelName,
                currentRowData
            );
        }

        if (foregroundColor) {
            result.colorIdentifiers.foreground = foregroundColor;
            const foregroundStyle = getResolvedColor(foregroundColor, theme, null, true, false);
            result.styles.foreground = foregroundStyle;

            // Extract actual color value
            if (typeof foregroundStyle === 'object') {
                result.resolvedColors.foreground = foregroundStyle.color || null;
            } else {
                result.resolvedColors.foreground = foregroundStyle;
            }
        }
    }

    // === BACKGROUND COLOR RESOLUTION ===
    if (data.backgroundColor || data.backgroundColorSrc || data.backgroundColorPercentage) {
        let backgroundColor = '';

        if (data.backgroundColor) {
            // Priority 1: Use direct backgroundColor property
            // Create temporary data object with backgroundColor as color property for getColorFromMapping
            const bgColorData = {
                ...data,
                color: data.backgroundColor,
                colorSrc: data.backgroundColorSrc
            };
            backgroundColor = getColorFromMapping(
                bgColorData,
                fieldValue,
                null,
                theme,
                null,
                false,
                reducerDict,
                schemaCollections,
                'background'
            );
        } else if (data.backgroundColorSrc) {
            // Priority 2: Resolve from source field
            backgroundColor = resolveColorFromSource(
                data.backgroundColorSrc,
                reducerDict,
                fieldValue,
                null,
                schemaCollections,
                theme,
                'background',
                modelName,
                currentRowData,
                data.xpath
            );
        } else if (data.backgroundColorPercentage) {
            // Priority 3: Use dedicated background percentage property
            backgroundColor = resolveColorFromPercentage(
                data.backgroundColorPercentage,
                fieldValue,
                modelName,
                currentRowData
            );
        }

        if (backgroundColor) {
            result.colorIdentifiers.background = backgroundColor;
            const backgroundStyle = getResolvedColor(backgroundColor, theme, null, true, true);
            result.styles.background = backgroundStyle;

            // Extract actual color value
            if (typeof backgroundStyle === 'object') {
                result.resolvedColors.background = backgroundStyle.backgroundColor || null;
            } else {
                result.resolvedColors.background = backgroundStyle;
            }
        }
    }

    // === BUILD SX STYLES FOR MUI COMPONENTS ===
    const { foreground: resolvedForegroundColor, background: resolvedBackgroundColor } = result.resolvedColors;

    if (resolvedForegroundColor || resolvedBackgroundColor) {
        // Merge critical animation styles if present
        const animationStyles = {};
        if (result.styles.foreground && typeof result.styles.foreground === 'object' && result.styles.foreground.animation) {
            animationStyles.animation = result.styles.foreground.animation;
            animationStyles['@keyframes blink'] = result.styles.foreground['@keyframes blink'];
        } else if (result.styles.background && typeof result.styles.background === 'object' && result.styles.background.animation) {
            animationStyles.animation = result.styles.background.animation;
            animationStyles['@keyframes blink'] = result.styles.background['@keyframes blink'];
        }

        result.colorSx = {
            ...animationStyles,
            // Rules for Select (dropdowns and button-like fields)
            '& .MuiSelect-select': {
                '&.Mui-disabled': {
                    color: resolvedForegroundColor || 'inherit',
                    backgroundColor: resolvedBackgroundColor || 'inherit'
                }
            },
            // Rules for Input/TextField (text inputs)
            '& .MuiInputBase-input': {
                color: resolvedForegroundColor || 'inherit',
                backgroundColor: resolvedBackgroundColor || 'inherit',
                WebkitTextFillColor: resolvedForegroundColor || 'inherit',
                '&.Mui-disabled': {
                    WebkitTextFillColor: resolvedForegroundColor || 'inherit',
                }
            },
            // Rules for Checkbox
            '& .MuiCheckbox-root': {
                color: resolvedForegroundColor || 'inherit',
                '&.Mui-disabled': {
                    color: resolvedForegroundColor || 'inherit',
                }
            }
        };
    }

    return result;
}
