

/**
 * Filters a given data array based on a list of filter configurations.
 * Each filter configuration can specify `filtered_values` (for exact matches) and `text_filter` (for string-based comparisons).
 * If no filters are provided or the data is empty, the original data is returned.
 * @param {Array<Object>} data - The original array of data objects to be filtered.
 * @param {Array<Object>} [filters=[]] - An array of filter objects. Each object should have at least `column_name`,
 *   and optionally `filtered_values` (comma-separated string) and `text_filter`, `text_filter_type`.
 * @returns {Array<Object>} The filtered data array.
 */
export function applyFilter(data, filters = []) {
    // If data is empty or no filters are provided, return the original data without filtering.
    if (!data || !data.length || !filters || !filters.length) return data;

    // Convert the array of filter objects into a dictionary for easier lookup by column name.
    const filterDict = getFilterDict(filters);

    // Filter the data array, keeping only rows that pass all active filters.
    return data.filter(row => {
        // Check if the current row passes all column filters.
        return Object.keys(filterDict).every(columnId => {
            const filterObj = filterDict[columnId];

            // If there are no filter settings for this column, it passes by default.
            if (!filterObj) return true;

            // Get the value of the column from the current row.
            const value = row[columnId];
            // Convert the value to a string for consistent comparison, handling null/undefined.
            const strValue = String((value === null || value === undefined) ? '' : value);

            // Check if the string value is included in the `filtered_values` list (if provided).
            // If `filtered_values` is null or undefined, this check always passes.
            const passesValueFilter = filterObj.filtered_values?.includes(strValue) ?? true;

            // Check if the value passes the text filter (if `text_filter` is present).
            const passesTextFilter = filterByText(value, filterObj.text_filter, filterObj.text_filter_type);

            // A row passes the filter for a column only if it passes both value and text filters.
            return passesValueFilter && passesTextFilter;
        });
    });
}

/**
 * Filters a single value based on a text filter and a specified filter type.
 * This function supports various text comparison types like 'equals', 'contains', 'startsWith', etc.
 * @param {*} value - The cell value to check. Can be of any type, but will be converted to string for comparison.
 * @param {string} textFilter - The text string to filter against.
 * @param {string} textFilterType - The type of text filter to apply. Supported types include:
 *   - 'equals': Value must be exactly equal to the text filter (case-insensitive).
 *   - 'notEqual': Value must not be exactly equal to the text filter (case-insensitive).
 *   - 'contains': Value must contain the text filter (case-insensitive).
 *   - 'notContains': Value must not contain the text filter (case-insensitive).
 *   - 'beginsWith': Value must start with the text filter (case-insensitive).
 *   - 'endsWith': Value must end with the text filter (case-insensitive).
 *   If `textFilterType` is not recognized, it defaults to 'contains'.
 * @returns {boolean} True if the value passes the text filter, false otherwise.
 */
export function filterByText(value, textFilter, textFilterType) {
    // If no text filter is provided, the value always passes.
    if (!textFilter) return true;

    // Convert the value to a string, handling null or undefined values by treating them as empty strings.
    const stringValue = String(value === null || value === undefined ? '' : value);

    // Perform case-insensitive comparison by converting both the filter and the value to lowercase.
    const filterLower = textFilter.toLowerCase();
    const valueLower = stringValue.toLowerCase();

    switch (textFilterType) {
        case 'equals':
            return valueLower === filterLower;

        case 'notEqual':
            return valueLower !== filterLower;

        case 'contains':
            return valueLower.includes(filterLower);

        case 'notContains':
            return !valueLower.includes(filterLower);

        case 'beginsWith':
            return valueLower.startsWith(filterLower);

        case 'endsWith':
            return valueLower.endsWith(filterLower);

        default:
            // Default behavior: if the filter type is not recognized, perform a 'contains' check.
            return valueLower.includes(filterLower);
    }
}

/**
 * Transforms an array of filter objects into a dictionary, keyed by `column_name`.
 * It also processes the `filtered_values` string in each filter object,
 * splitting it into an array of strings if it exists, otherwise setting it to `null`.
 * @param {Array<Object>} filters - An array of filter objects. Each object is expected to have a `column_name` property and optionally a `filtered_values` string.
 * @returns {Object<string, Object>} A dictionary where keys are `column_name` and values are the processed filter objects.
 */
export function getFilterDict(filters) {
    return filters.reduce((acc, item) => {
        acc[item.column_name] = {
            ...item,
            // Split the comma-separated `filtered_values` string into an array.
            // If `filtered_values` is null or undefined, set it to null.
            filtered_values: item.filtered_values?.split(',') ?? null
        };
        return acc;
    }, {});
}

export function getChartFilterDict(filters) {

    const result = filters.reduce((acc, { fld_name, fld_value }) => {
        const toList = (v) =>
            Array.isArray(v)
                ? v
                : String(v ?? '')
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean);

        const merged = acc[fld_name]
            ? Array.from(new Set([...toList(acc[fld_name]), ...toList(fld_value)]))
            : toList(fld_value);

        acc[fld_name] = merged.join(',');
        return acc;
    }, {});

    return result;
}