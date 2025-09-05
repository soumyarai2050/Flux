// TODO: generalise supported flux options by project
/**
 * @constant {Array<Object>} fluxOptions - Placeholder for project-specific Flux options.
 * Currently empty, but intended to be extended with general Flux-related configurations.
 */
export const fluxOptions = [];

/**
 * @constant {Object} FileOptions - Placeholder for file-related options.
 * Currently empty, but intended to be extended with configurations for file handling.
 */
export const FileOptions = {};

// complex (object and array) field properties. applies/passed to child components also
/**
 * @constant {Array<Object>} complexFieldProps - Defines properties applicable to complex fields (objects and arrays).
 * These properties are typically passed down to child components for rendering and behavior customization.
 */
export const complexFieldProps = [
    /**
     * If set to true, the field is populated by the server and not shown in edit mode.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "server_populate", usageName: "serverPopulate" },
    /**
     * If set to true, the field is not shown during creation but can be subsequently modified.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "ui_update_only", usageName: "uiUpdateOnly" },
    /**
     * If set to true, the field cannot be modified once created. It is shown in edit mode but is not editable.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "orm_no_update", usageName: "ormNoUpdate" },
    /**
     * Provides a set of options allowed on the field (':'), and/or assigns a default value to the field (=),
     * and/or sets server population on the field (server_populate).
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "auto_complete", usageName: "autocomplete" },
    /**
     * If set to true, overrides the default title of the field with its XPath for more detailed display.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    /**
     * If set to true, allows a filter to be applied on the field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "filter_enable", usageName: "filterEnable" },
    /**
     * Chart projections related option: maps to an underlying meta field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "mapping_underlying_meta_field", usageName: "mapping_underlying_meta_field" },
    /**
     * Chart projections related option: defines the mapping source.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "mapping_src", usageName: "mapping_src" },
    /**
     * Chart projections related option: defines the value meta field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "val_meta_field", usageName: "val_meta_field" },
    /**
     * If set to true, the field is hidden by default in the UI.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "hide", usageName: "hide" },

    { propertyName: "array_obj_identifier", usageName: "array_obj_identifier" },
]


// simple field flux properties supported by project
/**
 * @constant {Array<Object>} fieldProps - Defines properties applicable to simple fields.
 * These properties control various aspects of field behavior, display, and validation.
 */
export const fieldProps = [
    /**
     * Sets the data type of the field (e.g., 'string', 'number', 'boolean').
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "type", usageName: "type" },
    /**
     * Sets the display title of the field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "title", usageName: "title" },
    /**
     * If set to true, the field is hidden by default in the UI.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "hide", usageName: "hide" },
    /**
     * Sets the help text for the field, typically displayed as a tooltip or hint.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "help", usageName: "help" },
    // TODO: not supported
    { propertyName: "cmnt", usageName: "description" },
    /**
     * Sets the default value of the field, assigned when the field is created.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "default", usageName: "default" },
    /**
     * Sets the sub-data type of the field, providing more specific type information.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "underlying_type", usageName: "underlyingtype" },
    /**
     * Sets the placeholder text for the field, displayed when the field is unset or empty.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "ui_placeholder", usageName: "placeholder" },
    /**
     * Sets the associated value color map for the field, used for visual representation.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "color", usageName: "color" },
    /**
     * Displays the field as a button in the UI.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "button", usageName: "button" },
    /**
     * If set to "JSON", the field is displayed as JSON. Otherwise, it holds metadata for the field
     * in collection (abbreviated filter) view.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "abbreviated", usageName: "abbreviated" },
    /**
     * Sets the maximum constraint on the field's value.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "val_max", usageName: "max" },
    /**
     * Sets the minimum constraint on the field's value.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "val_min", usageName: "min" },
    // TODO: not supported
    { propertyName: "default_value_placeholder_string", usageName: "defaultValuePlaceholderString" },
    // TODO: not supported
    { propertyName: "val_sort_weight", usageName: "sortWeight" },
    /**
     * Sets the field as a datetime field, enabling date and time formatting and parsing.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "val_is_date_time", usageName: "dateTime" },
    // TODO: not supported
    { propertyName: "index", usageName: "index" },
    // TODO: not supported
    { propertyName: "sticky", usageName: "sticky" },
    // TODO: not supported
    { propertyName: "size_max", usageName: "sizeMax" },
    /**
     * Displays the field as a progress bar in the UI.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "progress_bar", usageName: "progressBar" },
    /**
     * If set to True, overrides the default title of the field with its XPath for more detailed display.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "elaborate_title", usageName: "elaborateTitle" },
    /**
     * Sets the color of the field key (label).
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "name_color", usageName: "nameColor" },
    /**
     * Sets the number formatting (floating point precision, prefix, suffix) on the field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "number_format", usageName: "numberFormat" },
    /**
     * If set to True, the field is not added to the common key.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "no_common_key", usageName: "noCommonKey" },
    /**
     * Sets the field value display type (e.g., 'float' to display as 'int').
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "display_type", usageName: "displayType" },
    /**
     * Sets the alignment of text in a table column for this field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "text_align", usageName: "textAlign" },
    /**
     * If set to True, fields with zero values are displayed.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "display_zero", usageName: "displayZero" },
    /**
     * Sets the separator for multi-value fields defined in abbreviated form.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "micro_separator", usageName: "microSeparator" },
    /**
     * Chart projection related field: indicates if it's a time field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "val_time_field", usageName: "val_time_field" },
    /**
     * Chart projection related field: defines projections.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "projections", usageName: "projections" },
    /**
     * Chart projection related field: maps to a projection query field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "mapping_projection_query_field", usageName: "mapping_projection_query_field" },
    /**
     * Chart projection related field: maps to an underlying meta field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "mapping_underlying_meta_field", usageName: "mapping_underlying_meta_field" },
    /**
     * Chart projection related field: defines the mapping source.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "mapping_src", usageName: "mapping_src" },
    /**
     * Indicates that the underlying server ready status is derived from this field.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "server_ready_status", usageName: "server_ready_status" },
    /**
     * Sets the column size of the field in a table.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "column_size", usageName: "columnSize" },
    /**
     * Sets the column (text) direction of the field in a table.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "column_direction", usageName: "columnDirection" },
    /**
     * Sets the allowed difference percentage on a field which is saved without confirmation.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "diff_threshold", usageName: "diffThreshold" },
    /**
     * If set to true, zero values are treated as none or empty.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "zero_as_none", usageName: "zeroAsNone" },
    /**
     * Defines a condition under which the field is visible.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "visible_if", usageName: "visible_if" },
    { propertyName: "text_area", usageName: "text_area" },
    { propertyName: "chat_context", usageName: "chat_context" },
    { propertyName: "chat_conversation", usageName: "chat_conversation" },
    { propertyName: "user_message", usageName: "user_message" },
    { propertyName: "bot_message", usageName: "bot_message" },
    { propertyName: "bot_reasoning", usageName: "bot_reasoning" },
    { propertyName: "default_array_create", usageName: "default_array_create" },
    { propertyName: "graph", usageName: "graph" },
    { propertyName: "node", usageName: "node" },
    { propertyName: "edge", usageName: "edge" },
    { propertyName: "node_name", usageName: "node_name" },
    { propertyName: "node_type", usageName: "node_type" },
    { propertyName: "node_access", usageName: "node_access" },
    { propertyName: "node_url", usageName: "node_url" },
]


// additional properties supported only on array fields
/**
 * @constant {Array<Object>} arrayFieldProps - Defines additional properties specifically supported on array fields.
 * These properties are used to configure features like alert bubbles for array elements.
 */
export const arrayFieldProps = [
    /**
     * Sets the source field to fetch the bubble count for array elements.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "alert_bubble_source", usageName: "alertBubbleSource" },
    /**
     * Sets the source field to fetch the bubble color for array elements.
     * @property {string} propertyName - The original property name from the schema.
     * @property {string} usageName - The standardized name used in the UI code.
     */
    { propertyName: "alert_bubble_color", usageName: "alertBubbleColor" }
]
