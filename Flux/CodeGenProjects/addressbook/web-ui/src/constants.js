export const API_ROOT_URL = 'http://127.0.0.1:8000/addressbook';
export const API_PUBLIC_URL = 'http://127.0.0.1:3000';
export const DB_ID = '_id';
export const SCHEMA_DEFINITIONS_XPATH = 'definitions';
export const NEW_ITEM_ID = 999999;
export const COOKIE_NAME = 'addressbook';

export const Modes = {
    EDIT_MODE: 'edit',
    READ_MODE: 'read',
    DISABLED_MODE: 'disabled'
}

export const Layouts = {
    TREE_LAYOUT: 'Tree',
    TABLE_LAYOUT: 'Table',
    ABBREVIATED_FILTER_LAYOUT: 'AbbreviatedFilter',
    UNSPECIFIED: 'UNSPECIFIED'
}

export const ColorTypes = {
    CRITICAL: 'critical',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info',
    DEBUG: 'debug',
    SUCCESS: 'success',
    UNSPECIFIED: 'default'
}

export const ColorPriority = {
    [ColorTypes.CRITICAL]: 5,
    [ColorTypes.ERROR]: 4,
    [ColorTypes.WARNING]: 3,
    [ColorTypes.INFO]: 2,
    [ColorTypes.DEBUG]: 1,
    [ColorTypes.UNSPECIFIED]: 0
}

export const DataTypes = {
    STRING: 'string',
    NUMBER: 'number',
    BOOLEAN: 'boolean',
    ENUM: 'enum',
    OBJECT: 'object',
    ARRAY: 'array',
    INT32: 'int32',
    INT64: 'int64',
    FLOAT: 'float'
}

export const ComponentType = {
    BUTTON: 'button',
    PROGRESS_BAR: 'progressBar'
}

export const SizeType = {
    SMALL: 'small',
    MEDIUM: 'medium',
    LARGE: 'large',
    UNSPECIFIED: 'small'
}

export const ShapeType = {
    RECTANGLE: 'rectangle',
    ROUND: 'round',
    UNSPECIFIED: 'rectangle'
}