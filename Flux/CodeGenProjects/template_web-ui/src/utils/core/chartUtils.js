import { cloneDeep, get } from 'lodash';
import { DB_ID, DATA_TYPES, SCHEMA_DEFINITIONS_XPATH, primitiveDataTypes } from '../../constants';
import { getCollectionByName } from './dataUtils';
import { roundNumber } from '../formatters/numberUtils';

/**
 * Defines the types of axes used in charts.
 * @enum {string}
 */
const ChartAxisType = {
    /** For string data types, typically used for categorical data. */
    CATEGORY: 'category',
    /** For time-series data. */
    TIME: 'time',
    /** For numeric data types. */
    VALUE: 'value'
};

/**
 * Determines the appropriate chart axis type and name based on the collection's data type.
 * @param {Array<Object>} collections - List of widget fields and their attributes.
 * @param {string} axisField - The field name or XPath for the axis.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type, false otherwise.
 * @returns {[string, string]} A tuple containing the axis type and axis name.
 * @throws {Error} If the collections list is null or undefined.
 */
function getChartAxisTypeAndName(collections, axisField, isCollectionType = false) {
    if (!collections) {
        throw new Error('getChartAxisTypeAndName failed. collections list is null or undefined, collections: ' + collections);
    }
    const collection = getCollectionByName(collections, axisField, isCollectionType);
    let axisName = collection.title;
    let axisType = ChartAxisType.VALUE;
    if (collection.type === DATA_TYPES.STRING) {
        axisType = ChartAxisType.CATEGORY;
    } else if (collection.type === DATA_TYPES.NUMBER) {
        axisType = ChartAxisType.VALUE;
    } else if (collection.type === DATA_TYPES.DATE_TIME) {
        axisType = ChartAxisType.TIME;
    }
    return [axisType, axisName];
}

/**
 * Calculates the maximum value for a given field across a dataset of rows.
 * @param {Array<Object>} rows - List of dictionaries representing table rows.
 * @param {string} field - The field name to find the maximum value for.
 * @param {number} [index=0] - Index of the axis (default 0). This parameter is currently unused in the calculation but is retained for potential future use or consistency with other functions.
 * @returns {number} The maximum value found, or 0 if no valid maximum is determined.
 * @throws {Error} If the rows list is null or undefined.
 */
function getAxisMax(rows, field, index = 0) {
    if (!rows) {
        throw new Error('getAxisMax failed. rows list is null or undefined, rows: ' + rows);
    }
    let max;
    rows.forEach(row => {
        if (row.hasOwnProperty(field)) {
            const value = row[field];
            if (max === undefined || max === null) {
                if (value !== undefined && value !== null) {
                    max = value;
                }
            } else if (value > max) {
                max = value;
            }
        }
    });
    // The commented-out scaling logic below was part of previous iterations
    // and is kept for historical context, but is not currently active.
    // max = Math.ceil(max);
    // const scale = 1.5 - 0.25 * index;
    // const scale = 1.25;
    // return max * scale;
    if (!max) return 0;
    return max;
}

/**
 * Calculates the minimum value for a given field across a dataset of rows.
 * @param {Array<Object>} rows - List of dictionaries representing table rows.
 * @param {string} field - The field name to find the minimum value for.
 * @param {number} [index=0] - Index of the axis (default 0). This parameter is currently unused in the calculation but is retained for potential future use or consistency with other functions.
 * @returns {number} The minimum value found, or 0 if no valid minimum is determined.
 * @throws {Error} If the rows list is null or undefined.
 */
function getAxisMin(rows, field, index = 0) {
    if (!rows) {
        throw new Error('getAxisMax failed. rows list is null or undefined, rows: ' + rows);
    }
    let min;
    rows.forEach(row => {
        if (row.hasOwnProperty(field)) {
            const value = row[field];
            if (min === undefined || min === null) {
                if (value !== undefined && value !== null) {
                    min = value;
                }
            } else if (value < min) {
                min = value;
            }
        }
    });
    // The commented-out scaling logic below was part of previous iterations
    // and is kept for historical context, but is not currently active.
    // min = Math.floor(min);
    // const scale = 1.5 - 0.25 * index;
    // const scale = 1.25;
    // return min / scale;
    if (!min) return 0;
    return min;
}

/**
 * Updates chart series options based on the chart type.
 * For 'line' charts, it hides symbols if the dataset source is large and sets a default symbol size.
 * For 'scatter' charts, it sets a default symbol size.
 * @param {Object} chartSeries - The chart series object to update.
 * @param {Object} dataset - The dataset associated with the chart series.
 */
function updateChartTypeSpecificOptions(chartSeries, dataset) {
    if (chartSeries.type === 'line') {
        // If the dataset has more than 100 data points, hide symbols for cleaner lines.
        if (dataset.source.length > 100) {
            chartSeries.showSymbol = false;
        }
        // Set a default symbol size for line charts.
        chartSeries.symbolSize = 5;
    } else if (chartSeries.type === 'scatter') {
        // Set a default symbol size for scatter charts.
        chartSeries.symbolSize = 5;
    }
}

/**
 * Determines the Y-axis index for a given Y-axis encoding.
 * If the encoding is already present, its index is returned. Otherwise, a new index is provided.
 * @param {Array<Object>} [encodes=[]] - An array of existing axis encodings.
 * @param {string} yEncode - The Y-axis encoding to find or assign an index for.
 * @param {boolean} [isStack=false] - Indicates if the series is stacked (currently unused in logic but retained for context).
 * @returns {number} The determined Y-axis index.
 */
function getYAxisIndex(encodes = [], yEncode, isStack = false) {
    if (encodes.length === 0) {
        return 0;
    } else {
        let index = -1;
        encodes.forEach((encode, i) => {
            if (encode.encode === yEncode) {
                index = i;
            }
        });
        // If the yEncode is not found in existing encodes, return the next available index.
        if (index === -1) return encodes.length;
        return index;
    }
}

/**
 * Updates the chart data object with series, axes, and dataset information.
 * This function processes raw data and chart configurations to produce a complete chart option object
 * suitable for rendering. It handles time-series data, partitioning, and dynamic axis scaling.
 * @param {Object} chartDataObj - The base chart data object to be updated.
 * @param {Array<Object>} collections - List of widget fields and their attributes.
 * @param {Array<Object>} rows - The main dataset rows.
 * @param {Array<Object>} datasets - Pre-generated datasets for the chart.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type, false otherwise.
 * @param {Object} schemaCollections - Schema definitions for various collections.
 * @param {Object} queryDict - Dictionary of queries used for time-series data.
 * @returns {Object} The updated chart data object with configured series and axes.
 */
export function updateChartDataObj(chartDataObj, collections, rows, datasets, isCollectionType = false, schemaCollections, queryDict) {
    // Create a deep clone to avoid modifying the original chartDataObj directly.
    chartDataObj = cloneDeep(chartDataObj);
    const xEndodes = [];
    const yEncodes = [];
    const xAxis = [];
    const yAxis = [];
    const seriesList = [];
    let prevYEncode;
    let prevYEncodeIndex = 0;

    // Iterate over each series defined in the chart configuration.
    chartDataObj.series.forEach((series, seriesIndex) => {
        let xEncode = series.encode.x;
        let yEncode = series.encode.y;
        let yMax = 0;
        let yMin = 0;
        let forceMin = false;
        let forceMax = false;
        let chartSeriesCollections = collections;
        let updatedSeries;

        // Handle time-series charts.
        if (chartDataObj.time_series) {
            const collection = getCollectionByName(collections, series.encode.y, isCollectionType);
            if (collection.hasOwnProperty('mapping_src')) {
                const [seriesWidgetName, ...mappingSrcField] = collection.mapping_src.split('.');
                const srcField = mappingSrcField.join('.');
                const seriesCollections = schemaCollections[seriesWidgetName];
                const query = queryDict[seriesIndex];
                if (query) {
                    const xCollection = seriesCollections.find(col => col.val_time_field === true);
                    xEncode = xCollection.tableTitle;
                    const yCollection = seriesCollections.find(col => col.tableTitle === srcField);
                    yEncode = yCollection.tableTitle;
                    // The lines below are commented out as series.encode.x and series.encode.y are already set above.
                    // series.encode.x = xEncode;
                    // series.encode.y = yEncode;
                    const tsRows = [];
                    datasets.forEach((dataset, index) => {
                        if (dataset.type === 'time_series' && dataset.query === query.name && dataset.series_type === series.type) {
                            updatedSeries = cloneDeep(series);
                            updatedSeries.datasetIndex = index;
                            updatedSeries.name = dataset.name + ' ' + series.encode.y + ' ' + series.type;
                            updatedSeries.animation = false;
                            updateChartTypeSpecificOptions(updatedSeries, dataset);
                            updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                            if (updatedSeries.yAxisIndex < 2) {
                                seriesList.push(updatedSeries);
                                tsRows.push(...dataset.source);
                            }
                        }
                    });
                    // Determine y-axis min/max, respecting forced values if present.
                    if (series.y_min || series.y_min === 0) {
                        yMin = series.y_min;
                        forceMin = true;
                    }
                    if (series.y_max || series.y_max === 0) {
                        yMax = series.y_max;
                        forceMax = true;
                    }
                    if (!forceMin) {
                        yMin = getAxisMin(tsRows, yEncode, yEncodes.length);
                    }
                    if (!forceMax) {
                        yMax = getAxisMax(tsRows, yEncode, yEncodes.length);
                    }
                    chartSeriesCollections = seriesCollections;
                }
            }
        } else {
            // Handle non-time-series charts, potentially with partitioning.
            if (chartDataObj.partition_fld) {
                const partitionRows = [];
                datasets.forEach((dataset, index) => {
                    if (dataset.type === 'partition' && dataset.series_type === series.type) {
                        updatedSeries = cloneDeep(series);
                        updatedSeries.datasetIndex = index;
                        updatedSeries.name = dataset.name + ' ' + series.encode.y + ' ' + series.type;
                        updatedSeries.animation = false;
                        updateChartTypeSpecificOptions(updatedSeries, dataset);
                        updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                        if (updatedSeries.yAxisIndex < 2) {
                            seriesList.push(updatedSeries);
                            partitionRows.push(...dataset.source);
                        }
                    }
                });
                // Determine y-axis min/max for partitioned data.
                if (series.y_min || series.y_min === 0) {
                    yMin = series.y_min;
                    forceMin = true;
                }
                if (series.y_max || series.y_max === 0) {
                    yMax = series.y_max;
                    forceMax = true;
                }
                if (!forceMin) {
                    yMin = getAxisMin(partitionRows, yEncode, yEncodes.length);
                }
                if (!forceMax) {
                    yMax = getAxisMax(partitionRows, yEncode, yEncodes.length);
                }
            } else {
                // Handle default (non-partitioned, non-time-series) charts.
                const dataset = datasets.find(dataset => dataset.type === 'default');
                if (dataset) {
                    updatedSeries = cloneDeep(series);
                    updatedSeries.datasetIndex = datasets.indexOf(dataset);
                    updatedSeries.name = series.encode.y + ' ' + series.type;
                    updatedSeries.animation = false;
                    updateChartTypeSpecificOptions(updatedSeries, dataset);
                    updatedSeries.yAxisIndex = getYAxisIndex(yEncodes, yEncode);
                    if (updatedSeries.yAxisIndex < 2) {
                        seriesList.push(updatedSeries);
                    }
                    // Determine y-axis min/max for default data.
                    if (series.y_min || series.y_min === 0) {
                        yMin = series.y_min;
                        forceMin = true;
                    }
                    if (series.y_max || series.y_max === 0) {
                        yMax = series.y_max;
                        forceMax = true;
                    }
                    if (!forceMin) {
                        yMin = getAxisMin(rows, yEncode, yEncodes.length);
                    }
                    if (!forceMax) {
                        yMax = getAxisMax(rows, yEncode, yEncodes.length);
                    }
                }
            }
        }

        // Update series encoding and axis information.
        if (updatedSeries) {
            if (xEncode && yEncode) {
                // The commented-out block below was for tracking previous Y-axis encodes,
                // but the current logic for `prevYEncodeIndex` handles this implicitly.
                // if (!prevYEncode) {
                //     prevYEncode = yEncode;
                // } else if (prevYEncode !== yEncode) {
                //     prevYEncodeIndex += 1;
                // }

                // Add x-axis encode if not already present.
                if (!xEndodes.find(encode => encode.encode === xEncode)) {
                    xEndodes.push({ encode: xEncode, seriesCollections: chartSeriesCollections, isCollectionType });
                }

                // Handle stacked series.
                if (series.stack) {
                    // If a stack is already present, do not add a new encode for it.
                    if (!yEncodes.find((encode) => encode.stack)) {
                        yEncodes.push({ encode: yEncode, seriesCollections: chartSeriesCollections, isCollectionType, max: yMax, min: yMin, forceMin, forceMax, stack: series.stack });
                        prevYEncodeIndex += 1;
                    }
                } else if (!yEncodes.find(encode => encode.encode === yEncode && !encode.stack)) {
                    // Add y-axis encode if not stacked and not already present.
                    yEncodes.push({ encode: yEncode, seriesCollections: chartSeriesCollections, isCollectionType, max: yMax, min: yMin, forceMin, forceMax });
                    prevYEncodeIndex += 1;
                }
                updatedSeries.yAxisIndex = prevYEncodeIndex - 1;

                // Configure stacked series properties.
                if (updatedSeries.stack) {
                    updatedSeries.stack = 'total'; // ECharts specific for stacked charts.
                    if (updatedSeries.type === 'line') {
                        updatedSeries.areaStyle = {}; // Fill area for stacked line charts.
                        updatedSeries.emphasis = {
                            focus: 'series' // Highlight the entire series on hover.
                        };
                    }
                }
            }
        }
    });

    // Configure X-axis.
    xEndodes.forEach(({ encode, seriesCollections, isCollectionType }) => {
        const [xAxisType, xAxisName] = getChartAxisTypeAndName(seriesCollections, encode, isCollectionType);
        // Only one x-axis is allowed per chart. If more than one x-axis is present,
        // only the first one is considered to avoid unsupported configurations.
        if (xAxis.length === 0) {
            const axis = {
                type: xAxisType,
                name: xAxisName,
                encode: encode
            };
            // Configure value-type x-axis with dynamic min/max and formatter.
            if (axis.type === ChartAxisType.VALUE) {
                const max = getAxisMax(rows, encode, 0);
                const min = getAxisMin(rows, encode, 0);
                axis.max = max + (max - min);
                axis.min = min >= 0 && min - (max - min) < 0 ? 0 : min - (max - min);
                axis.onZero = false; // Do not force axis to include zero.
                axis.axisLabel = {
                    formatter: (val) => tooltipFormatter(val) // Format axis labels.
                };
                axis.axisPointer = {
                    label: {
                        formatter: (param) => tooltipFormatter(param.value) // Format axis pointer labels.
                    }
                };
            }
            xAxis.push(axis);
        }
    });

    // Configure Y-axes.
    yEncodes.forEach(({ encode, seriesCollections, isCollectionType, max, min, forceMin, forceMax, stack = false }) => {
        const [yAxisType, yAxisName] = getChartAxisTypeAndName(seriesCollections, encode, isCollectionType);
        // Only two y-axes are allowed per chart. If more than two y-axes are present,
        // only the first two are considered to avoid unsupported configurations.
        const axisMax = forceMax ? max : max + (max - min);
        const axisMin = forceMin ? min : min >= 0 && min - (max - min) < 0 ? 0 : min - (max - min);
        if (yAxis.length < 2) {
            let axis = {
                type: yAxisType,
                name: yAxisName,
                encode: encode,
                splitNumber: 5, // Number of segments for the axis.
                // The commented-out properties below are dynamically set based on 'stack' property.
                // max: axisMax,
                // interval: (axisMax - axisMin) / 5,
                // min: axisMin,
                // onZero: false,
                axisLabel: {
                    formatter: (val) => tooltipFormatter(val) // Format axis labels.
                },
                axisPointer: {
                    label: {
                        formatter: (param) => tooltipFormatter(param.value) // Format axis pointer labels.
                    }
                }
            };
            // Apply non-stack specific properties if the series is not stacked.
            if (!stack) {
                const nonStackProps = {
                    max: axisMax,
                    interval: (axisMax - axisMin) / 5,
                    min: axisMin,
                    onZero: false, // Do not force axis to include zero.
                    axisLabel: {
                        formatter: (val) => tooltipFormatter(val)
                    },
                    axisPointer: {
                        label: {
                            formatter: (param) => tooltipFormatter(param.value)
                        }
                    }
                };
                axis = { ...axis, ...nonStackProps };
            }
            yAxis.push(axis);
        }
    });

    // Assign the constructed axes and series to the chart data object.
    chartDataObj.xAxis = xAxis;
    chartDataObj.yAxis = yAxis;
    chartDataObj.series = seriesList;
    return chartDataObj;
}

/**
 * Recursively updates chart-related attributes within a given schema.
 * This function modifies properties like `server_populate`, `hide`, and `orm_no_update`
 * for specific keys such as `DB_ID`, `chart_name`, `y_min`, and `y_max`.
 * It traverses nested schemas for objects and arrays.
 * @param {Object} schema - The complete schema object.
 * @param {Object} currentSchema - The current schema (or sub-schema) being processed.
 */
function updateChartAttributesInSchema(schema, currentSchema) {
    if (currentSchema.hasOwnProperty('properties')) {
        for (const key in currentSchema.properties) {
            const attributes = currentSchema.properties[key];
            // Handle primitive data types.
            if (primitiveDataTypes.includes(attributes.type)) {
                if (key === DB_ID) {
                    attributes.server_populate = true;
                    attributes.hide = true;
                    attributes.orm_no_update = true;
                } else if (key === 'chart_name') {
                    attributes.orm_no_update = true;
                } else if (['y_min', 'y_max'].includes(key)) {
                    attributes.hide = true;
                } else if (key === 'fld_value') {
                    attributes.placeholder = 'comma separated values';
                }
            } else if ([DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(attributes.type)) {
                // Recursively call for nested objects or arrays.
                const ref = attributes.items.$ref.split('/');
                const nestedSchema = ref.length === 2 ? schema[ref[1]] : schema[ref[1]][ref[2]];
                updateChartAttributesInSchema(schema, nestedSchema);
            }
        }
    }
}

/**
 * Updates the chart schema with autocomplete suggestions and visibility rules.
 * This function customizes the schema for chart-related fields, including
 * `partition_fld`, `x`, `y`, and filter fields, based on available collections.
 * @param {Object} schema - The original schema object.
 * @param {Array<Object>} collections - List of widget fields and their attributes.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type, false otherwise.
 * @returns {Object} The updated schema object.
 */
export function updateChartSchema(schema, collections, isCollectionType = false) {
    // Create a deep clone to avoid modifying the original schema directly.
    schema = cloneDeep(schema);

    // Update chart_data schema properties.
    const chartDataSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_data']);
    updateChartAttributesInSchema(schema, chartDataSchema);
    chartDataSchema.auto_complete = 'partition_fld:StrFldList';
    chartDataSchema.properties.partition_fld.visible_if = 'chart_data.time_series=false';

    // Update chart_encode schema properties.
    const chartEncodeSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'chart_encode']);
    chartEncodeSchema.auto_complete = 'x:FldList,y:FldList';
    chartEncodeSchema.properties.x.visible_if = 'chart_data.time_series=false';

    // Update ui_filter schema properties.
    const filterSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'ui_filter']);
    filterSchema.auto_complete = 'fld_name:FldList';

    let fldList;
    let strFldList;
    let metaFldList;
    let projectionFldList;
    let fieldKey;

    // Determine the key to use for field identification based on collection type.
    if (isCollectionType) {
        fieldKey = 'key';
    } else {
        fieldKey = 'tableTitle';
    }

    // Populate autocomplete lists based on collections.
    fldList = collections.map(collection => collection[fieldKey]);
    strFldList = collections.filter(collection => collection.type === DATA_TYPES.STRING).map(collection => collection[fieldKey]);
    metaFldList = collections.filter(collection => collection.hasOwnProperty('mapping_underlying_meta_field')).map(collection => collection[fieldKey]);
    projectionFldList = collections.filter(col => col.hasOwnProperty('mapping_src')).map(col => col[fieldKey]);

    // Assign the generated lists to the schema's autocomplete definitions.
    schema.autocomplete['FldList'] = fldList;
    schema.autocomplete['StrFldList'] = strFldList;
    schema.autocomplete['MetaFldList'] = metaFldList;
    schema.autocomplete['ProjFldList'] = projectionFldList;

    return schema;
}

/**
 * Converts a dictionary of filters into an array of filter objects.
 * Each filter object will have `fld_name` and `fld_value` properties.
 * @param {Object} filterDict - A dictionary where keys are field names and values are filter values.
 * @returns {Array<Object>} An array of filter objects.
 */
export function getFiltersFromDict(filterDict) {
    const filters = [];
    Object.keys(filterDict).forEach(key => {
        filters.push({
            fld_name: key,
            fld_value: filterDict[key]
        });
    });
    return filters;
}

/**
 * Generates a list of datasets for charting by grouping rows based on a partition field.
 * If no partition field is provided, all rows are treated as a single dataset.
 * Datasets are sorted by the x-axis encode if specified in the chart object.
 * @param {Array<Object>} rows - List of dictionaries representing table rows.
 * @param {string} partitionFld - The field name or XPath to group the rows on.
 * @param {Object} chartObj - The chart configuration/option object.
 * @returns {Array<Object>} A list of dataset objects, each containing `dimensions` and `source`.
 * @throws {Error} If the rows list is null or undefined.
 */
export function getChartDatasets(rows, partitionFld, chartObj) {
    if (rows.length === 0) {
        return [];
    } else {
        const datasets = [];
        // Get dimensions from the first row, assuming all rows have the same structure.
        const dimensions = Object.keys(rows[0]);
        let groups;

        // Group rows if a partition field is provided.
        if (partitionFld) {
            const groupsDict = rows.reduce((acc, cur) => {
                acc[cur[partitionFld]] = [...(acc[cur[partitionFld]] || []), cur];
                return acc;
            }, {});
            groups = [];
            for (const key in groupsDict) {
                groups.push(groupsDict[key]);
            }
        } else {
            // If no partition field, all rows form a single group.
            groups = [rows];
        }

        // Sort each group by the x-axis encode if defined in the chart object.
        if (chartObj.xAxis) {
            const axis = chartObj.xAxis[0];
            groups.forEach(group => {
                group.sort((a, b) => get(a, axis.encode) > get(b, axis.encode) ? 1 : get(a, axis.encode) < get(b, axis.encode) ? -1 : 0);
            });
        }

        // Create dataset objects for each group.
        groups.forEach(group => {
            const dataset = {
                dimensions: dimensions,
                source: group
            };
            datasets.push(dataset);
        });
        return datasets;
    }
}

/**
 * Generates chart datasets from raw rows and time-series data based on chart configuration.
 * This function handles both time-series and non-time-series data, including partitioning.
 * @param {Array<Object>} [rows=[]] - The main dataset rows.
 * @param {Object} tsData - Time-series data, typically indexed by query name.
 * @param {Object} chartObj - The chart configuration object.
 * @param {Object} queryDict - Dictionary of queries used for time-series data.
 * @param {Array<Object>} collections - List of widget fields and their attributes.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type, false otherwise.
 * @returns {Array<Object>} An array of generated dataset objects.
 */
export function genChartDatasets(rows = [], tsData, chartObj, queryDict, collections, isCollectionType = false) {
    const datasets = [];

    if (chartObj.series) {
        chartObj.series.forEach((series, index) => {
            // Handle time-series data.
            if (chartObj.time_series) {
                const collection = getCollectionByName(collections, series.encode.y, isCollectionType);
                if (collection.hasOwnProperty('mapping_src')) {
                    const query = queryDict[index];
                    if (query) {
                        const seriesTsData = tsData[query.name];
                        if (seriesTsData) {
                            seriesTsData.forEach(ts => {
                                if (ts.projection_models && ts.projection_models.length > 0) {
                                    // Generate a name for the series based on query parameters.
                                    let name = query.params.map(param => get(ts, param)).join(' ');
                                    const { projection_models, ...meta } = ts;
                                    const metaFieldName = Object.keys(meta)[0];

                                    // Add meta field and series index to each projection model.
                                    ts.projection_models.map(projection => {
                                        projection[metaFieldName] = meta[metaFieldName];
                                        projection['seriesIndex'] = index;
                                        return projection;
                                    });

                                    datasets.push({
                                        dimensions: Object.keys(ts.projection_models[0]),
                                        source: ts.projection_models,
                                        name: name,
                                        type: 'time_series',
                                        query: query.name,
                                        series_type: series.type
                                    });
                                }
                            });
                        }
                    }
                }
            } else if (rows.length > 0) {
                // Handle non-time-series data with or without partitioning.
                if (chartObj.partition_fld) {
                    // Group rows by the partition field.
                    const groupsDict = rows.reduce((acc, cur) => {
                        acc[cur[chartObj.partition_fld]] = [...(acc[cur[chartObj.partition_fld]] || []), cur];
                        return acc;
                    }, {});
                    const sortAxis = series.encode.x;
                    for (const groupName in groupsDict) {
                        const group = groupsDict[groupName];
                        // Sort the group by the x-axis encode if specified.
                        if (sortAxis) {
                            group.sort((a, b) => get(a, sortAxis) > get(b, sortAxis) ? 1 : get(a, sortAxis) < get(b, sortAxis) ? -1 : 0);
                        }
                        datasets.push({
                            dimensions: Object.keys(rows[0]),
                            source: group,
                            name: groupName,
                            type: 'partition',
                            series_type: series.type
                        });
                    }
                } else {
                    // If no partition field, treat all rows as a single default dataset.
                    const sortAxis = series.encode.x;
                    // Sort the rows by the x-axis encode if specified.
                    if (sortAxis) {
                        rows.sort((a, b) => get(a, sortAxis) > get(b, sortAxis) ? 1 : get(a, sortAxis) < get(b, sortAxis) ? -1 : 0);
                    }
                    datasets.push({
                        dimensions: Object.keys(rows[0]),
                        source: rows,
                        name: 'default',
                        type: 'default'
                    });
                }
            }
        });
    }
    return datasets;
}

/**
 * Merges updated time-series data into existing time-series data.
 * This function iterates through updated data, finds corresponding time series
 * in the existing data based on query parameters, and appends or adds new data.
 * @param {Object} tsData - The existing time-series data object.
 * @param {Object} updatedData - The new time-series data to merge.
 * @param {Object} queryDict - Dictionary of queries, used to identify time series.
 * @returns {Object} The merged time-series data object.
 */
export function mergeTsData(tsData, updatedData, queryDict) {
    for (const queryName in updatedData) {
        const dataList = updatedData[queryName];
        let query;
        // Find the corresponding query in queryDict.
        Object.entries(queryDict).forEach(([index, queryProps]) => {
            if (query) return; // Stop if query is already found.
            if (queryProps.name === queryName) {
                query = queryProps;
            }
        });

        if (query) {
            // Initialize tsData entry if it doesn't exist.
            if (!tsData.hasOwnProperty(queryName)) {
                tsData[queryName] = [];
            }
            dataList.forEach(data => {
                // Find existing time series based on query parameters.
                const timeSeries = tsData[queryName].find(ts => {
                    let found = true;
                    query.params.forEach(param => {
                        if (get(ts, param) !== get(data, param)) {
                            found = false;
                        }
                    });
                    return found;
                });
                // Merge or add new time series data.
                if (timeSeries) {
                    timeSeries.projection_models.push(...data.projection_models);
                } else {
                    tsData[queryName].push(data);
                }
            });
        }
    }
    return tsData;
}

/**
 * Generates meta filters based on a given array, collections, filter dictionary, and filter field.
 * This function maps filter values from the `filterDict` to corresponding meta fields
 * defined in the `collections` to create a list of filter objects.
 * @param {Array<Object>} arr - The array of data rows to filter.
 * @param {Array<Object>} collections - List of widget fields and their attributes, including meta field mappings.
 * @param {Object} filterDict - A dictionary of filter field names to their values (e.g., { "metaField": "value1,value2" }).
 * @param {string} filterFld - The field name in `filterDict` that contains the values to filter by.
 * @param {boolean} [isCollectionType=false] - True if the widget is of collection type, false otherwise.
 * @returns {Array<Object>} An array of filter objects, where each object maps meta field names to their values.
 */
export function genMetaFilters(arr, collections, filterDict, filterFld, isCollectionType = false) {
    const filters = [];
    const fldMappingDict = {};

    // Find the meta collection based on filterFld.
    const metaCollection = collections.find(col => {
        if (isCollectionType) {
            return col.key === filterFld;
        } else {
            return col.tableTitle === filterFld;
        }
    });

    // If no metaCollection is found, return empty filters.
    if (!metaCollection) {
        return filters;
    }

    const metaId = metaCollection.metaFieldId;

    // Build a mapping from collection key/tableTitle to underlying meta field name.
    collections.forEach(col => {
        if (col.hasOwnProperty('mapping_underlying_meta_field') && col.metaFieldId === metaId) {
            const metaField = col.mapping_underlying_meta_field.split('.').pop();
            if (isCollectionType) {
                fldMappingDict[col.key] = metaField;
            } else {
                fldMappingDict[col.tableTitle] = metaField;
            }
        }
    });

    // Parse filter values from the filter dictionary.
    let values = filterDict[filterFld].split(",").map(val => val.trim()).filter(val => val !== "");

    // For each filter value, create a meta filter
    values.forEach(value => {
        // Try to find a matching row in the data to get meta field mappings
        const matchingRow = arr.find(row => get(row, filterFld) === value);

        if (matchingRow) {
            // If we found a matching row, use its data for meta fields
            const filter = {};
            for (const key in fldMappingDict) {
                filter[fldMappingDict[key]] = get(matchingRow, key);
            }
            filters.push(filter);
        } else {
            // If no matching row exists, create a filter with the value directly mapped
            // This ensures we create WebSocket connections for all filter values
            const filter = {};

            // For time-series, we need to map the filter field to its underlying meta field
            if (fldMappingDict[filterFld]) {
                filter[fldMappingDict[filterFld]] = value;
            } else {
                // Fallback: use the field name directly as the meta field
                filter[filterFld] = value;
            }

            // Add any other meta fields we can derive (like exch_id if it's consistent)
            for (const key in fldMappingDict) {
                if (key !== filterFld && arr.length > 0) {
                    // Use the value from the first available row for other meta fields
                    filter[fldMappingDict[key]] = get(arr[0], key);
                }
            }

            filters.push(filter);
        }
    });

    return filters;
}

/**
 * Formats a given value for display in tooltips, primarily for numbers.
 * Numbers are formatted with `toLocaleString()`, and floating-point numbers are rounded to 2 decimal places.
 * Other types of values are returned as is.
 * @param {*} value - The value to format.
 * @returns {*} The formatted value.
 */
export function tooltipFormatter(value) {
    if (typeof value === DATA_TYPES.NUMBER) {
        if (Number.isInteger(value)) {
            return value.toLocaleString();
        } else {
            return roundNumber(value, 2).toLocaleString();
        }
    }
    return value;
}
// export function tooltipFormatter(value, fractionDigits = 2) {
//     const n = Number(value);
//     if (Number.isFinite(n)) {
//         if (Number.isInteger(n)) {
//             return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
//         }
//         // always show the same precision for floats
//         return n.toLocaleString(undefined, {
//             minimumFractionDigits: fractionDigits,
//             maximumFractionDigits: fractionDigits
//         });
//     }
//     return value;
// }

/**
 * Updates the schema for the `partition_fld` property based on whether the chart is a time-series chart.
 * If the chart is a time-series chart, the `partition_fld` property is hidden. Otherwise, it is shown.
 * @param {Object} schema - The original schema object.
 * @param {Object} chartObj - The chart object containing `time_series` property.
 * @returns {Object} The updated schema object.
 */
export function updatePartitionFldSchema(schema, chartObj) {
    const updatedSchema = cloneDeep(schema);
    const chartSchema = get(updatedSchema, [SCHEMA_DEFINITIONS_XPATH, 'chart_data']);
    if (chartObj.time_series) {
        chartSchema.properties.partition_fld.hide = true;
    } else {
        chartSchema.properties.partition_fld.hide = false;
    }
    return updatedSchema;
}

/**
 * Recursively updates pivot-related attributes within a given schema.
 * This function modifies properties like `server_populate`, `hide`, and `orm_no_update`
 * for specific keys such as `DB_ID` and `pivot_name`, and handles nested schemas.
 * @param {Object} schema - The complete schema object.
 * @param {Object} currentSchema - The current schema (or sub-schema) being processed.
 */
export function updatePivotAttributesInSchema(schema, currentSchema) {
    if (currentSchema.hasOwnProperty('properties')) {
        for (const key in currentSchema.properties) {
            const attributes = currentSchema.properties[key];
            // Handle primitive data types.
            if (primitiveDataTypes.includes(attributes.type)) {
                if (key === DB_ID) {
                    attributes.server_populate = true;
                    attributes.hide = true;
                    attributes.orm_no_update = true;
                } else if (key === 'pivot_name') {
                    attributes.orm_no_update = true;
                } else {
                    attributes.server_populate = true;
                }
            } else if ([DATA_TYPES.OBJECT, DATA_TYPES.ARRAY].includes(attributes.type)) {
                // For objects and arrays, set server_populate and hide.
                attributes.server_populate = true;
                attributes.hide = true;
            }
        }
    }
}

/**
 * Updates the pivot schema by applying specific attribute modifications.
 * This function clones the schema and then calls `updatePivotAttributesInSchema`
 * to modify the `pivot_data` section of the schema.
 * @param {Object} schema - The original schema object.
 * @returns {Object} The updated schema object for pivot data.
 */
export function updatePivotSchema(schema) {
    schema = cloneDeep(schema);
    const pivotDataSchema = get(schema, [SCHEMA_DEFINITIONS_XPATH, 'pivot_data']);
    updatePivotAttributesInSchema(schema, pivotDataSchema);
    return schema;
}

/**
 * Retrieves a clean chart option object by removing internal `DB_ID` properties.
 * This function ensures that the returned chart option is suitable for external use
 * or rendering by stripping internal database identifiers from axes and series.
 * @param {Object} chartDataObj - The chart data object potentially containing `DB_ID`s.
 * @returns {Object} A cleaned chart option object, or an empty object if `chartDataObj` is invalid.
 */
export function getChartOption(chartDataObj) {
    // Create a deep clone to avoid modifying the original chartDataObj directly.
    chartDataObj = cloneDeep(chartDataObj);
    if (chartDataObj && Object.keys(chartDataObj).length > 0) {
        // Remove DB_ID from xAxis, yAxis, and series to clean the object for external use.
        chartDataObj.xAxis.forEach(axis => {
            delete axis[DB_ID];
        });
        chartDataObj.yAxis.forEach(axis => {
            delete axis[DB_ID];
        });
        chartDataObj.series.forEach(series => {
            delete series[DB_ID];
        });
        return chartDataObj;
    } else {
        // Return an empty chart option object if the input is invalid.
        return { xAxis: [], yAxis: [], series: [] };
    }
}
