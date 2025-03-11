/**
 * Recursively generates all possible paths from the input JSON data.
 * For every property, a field `path_<key>` is added to represent the XPath-like
 * location of that property in the JSON hierarchy. When encountering an array,
 * the function generates separate paths for each array element.
 *
 * @param {*} data - The JSON data to be processed.
 * @param {string} [currentPath=""] - The current XPath-like path (used in recursion).
 * @returns {Array<Object>} An array of objects where each object represents one unique path.
 */
function generatePaths(data, currentPath = '') {
    // If data is an array, process each element separately.
    if (Array.isArray(data)) {
        let results = [];
        data.forEach((item, index) => {
            // Append array index to the current path.
            const arrayPath = currentPath ? `${currentPath}[${index}]` : `[${index}]`;
            const subPaths = generatePaths(item, arrayPath);
            results = results.concat(subPaths);
        });
        return results;
    }

    // If data is an object (but not null), process each key.
    if (data && typeof data === 'object') {
        let paths = [{}];
        Object.keys(data).forEach((key) => {
            const value = data[key];
            // Construct the new path for the current property.
            const newPath = currentPath ? `${currentPath}.${key}` : `${key}`;
            let newPaths = [];

            if (Array.isArray(value)) {
                // For array values, generate separate paths for each element.
                value.forEach((element, i) => {
                    // Include index in the path for clarity.
                    const elementPath = `${newPath}[${i}]`;
                    const subPaths = generatePaths(element, elementPath);
                    subPaths.forEach((sp) => {
                        paths.forEach((p) => {
                            newPaths.push({
                                ...p,
                                [key]: [sp],
                                // Add the path field without the index for the parent array.
                                [`path_${key}`]: newPath,
                                ['data-id']: newPath
                            });
                        });
                    });
                });
            } else if (value && typeof value === 'object') {
                // For nested objects, process recursively.
                const subPaths = generatePaths(value, newPath);
                subPaths.forEach((sp) => {
                    paths.forEach((p) => {
                        newPaths.push({
                            ...p,
                            [key]: sp,
                            [`path_${key}`]: newPath
                        });
                    });
                });
            } else {
                // For primitive values, assign the value and its path.
                paths.forEach((p) => {
                    newPaths.push({
                        ...p,
                        [key]: value,
                        [`path_${key}`]: newPath
                    });
                });
            }
            // Update paths for next iteration.
            paths = newPaths;
        });
        return paths;
    }

    // For primitive values, return an object containing the value and its path.
    return [{ value: data, path_value: currentPath }];
}