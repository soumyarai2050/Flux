/**
 * @module CONSTANTS
 * @description This module defines and exports production configuration constants and enumerations.
 */

import * as CONFIG from './config';

// Export API configuration values from config.
export const { API_PUBLIC_URL, API_ROOT_URL, COOKIE_NAME, PROJECT_NAME } = CONFIG;

/**
 * Unique identifier field for database objects.
 * @type {string}
 */
export const DB_ID = '_id';

/**
 * XPath used for schema definitions.
 * @type {string}
 */
export const SCHEMA_DEFINITIONS_XPATH = 'definitions';

/**
 * XPath used for schema autocomplete functionality.
 * @type {string}
 */
export const SCHEMA_AUTOCOMPLETE_XPATH = 'autocomplete';

/**
 * Default identifier for a new item.
 * @type {number}
 */
export const NEW_ITEM_ID = 999999;

/**
 * Application modes.
 * @readonly
 * @enum {string}
 */
export const MODES = Object.freeze({
  EDIT: 'edit',
  READ: 'read',
  DISABLED: 'disabled'
});

/**
 * Layout types for the user interface.
 * @readonly
 * @enum {string}
 */
export const LAYOUT_TYPES = Object.freeze({
  TREE: 'UI_TREE',
  TABLE: 'UI_TABLE',
  ABBREVIATION_MERGE: 'UI_ABBREVIATED_FILTER',
  PIVOT_TABLE: 'UI_PIVOT_TABLE',
  UNSPECIFIED: 'UNSPECIFIED',
  CHART: 'UI_CHART'
});

/**
 * Available color types.
 * @readonly
 * @enum {string}
 */
export const COLOR_TYPES = Object.freeze({
  CRITICAL: 'critical',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  DEBUG: 'debug',
  SUCCESS: 'success',
  DEFAULT: 'default'
});

/**
 * Mapping of color types to their priority levels.
 * @readonly
 * @type {Object<string, number>}
 */
export const COLOR_PRIORITY = Object.freeze({
  [COLOR_TYPES.CRITICAL]: 5,
  [COLOR_TYPES.ERROR]: 4,
  [COLOR_TYPES.WARNING]: 3,
  [COLOR_TYPES.INFO]: 2,
  [COLOR_TYPES.DEBUG]: 1,
  [COLOR_TYPES.DEFAULT]: 0
});

/**
 * Supported data types.
 * @readonly
 * @enum {string}
 */
export const DATA_TYPES = Object.freeze({
  STRING: 'string',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  ENUM: 'enum',
  OBJECT: 'object',
  ARRAY: 'array',
  INT32: 'int32',
  INT64: 'int64',
  FLOAT: 'float',
  DATE_TIME: 'date-time',
  INTEGER: 'int'
});

/**
 * Types of UI components.
 * @readonly
 * @enum {string}
 */
export const COMPONENT_TYPES = Object.freeze({
  BUTTON: 'button',
  PROGRESS_BAR: 'progressBar'
});

/**
 * Available size options.
 * @readonly
 * @enum {string}
 */
export const SIZE_TYPES = Object.freeze({
  SMALL: 'small',
  MEDIUM: 'medium',
  LARGE: 'large',
  UNSPECIFIED: 'small'
});

/**
 * Available shape options for UI elements.
 * @readonly
 * @enum {string}
 */
export const SHAPE_TYPES = Object.freeze({
  RECTANGLE: 'rectangle',
  ROUND: 'round',
  UNSPECIFIED: 'rectangle'
});

/**
 * Types for hover text display.
 * @readonly
 * @enum {string}
 */
export const HOVER_TEXT_TYPES = Object.freeze({
  NONE: 'none',
  VALUE: 'value',
  PERCENTAGE: 'percentage',
  VALUE_AND_PERCENTAGE: 'valueAndPercentage'
});

/**
 * Severity levels for logs or alerts.
 * @readonly
 * @enum {number}
 */
export const SEVERITY_TYPES = Object.freeze({
  Severity_CRITICAL: 5,
  Severity_ERROR: 4,
  Severity_WARNING: 3,
  Severity_INFO: 2,
  Severity_DEBUG: 1
})

/**
 * Model types used within the application.
 * @readonly
 * @enum {string}
 */
export const MODEL_TYPES = Object.freeze({
  ABBREVIATION_MERGE: 'abbreviation_merge',
  ROOT: 'root',
  REPEATED_ROOT: 'repeated_root',
  NON_ROOT: 'non_root'
});

export const WEBSOCKET_CLOSE_CODES = {
  NORMAL_CLOSURE: 1000,
  GOING_AWAY: 1001,
  PROTOCOL_ERROR: 1002,
  UNSUPPORTED_DATA: 1003,
  NO_STATUS_RECEIVED: 1005,
  ABNORMAL_CLOSURE: 1006,
  INVALID_PAYLOAD: 1007,
  POLICY_VIOLATION: 1008,
  MESSAGE_TOO_BIG: 1009,
  MANDATORY_EXTENSION: 1010,
  INTERNAL_ERROR: 1011,
  SERVICE_RESTART: 1012,
  TRY_AGAIN_LATER: 1013,
  BAD_GATEWAY: 1014,
  TLS_HANDSHAKE_FAILURE: 1015,
};

export const WEBSOCKET_RETRY_CODES = [
  WEBSOCKET_CLOSE_CODES.GOING_AWAY,
  WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE,
  WEBSOCKET_CLOSE_CODES.INTERNAL_ERROR,  // investigate
  WEBSOCKET_CLOSE_CODES.SERVICE_RESTART,
  WEBSOCKET_CLOSE_CODES.TRY_AGAIN_LATER,  // exponential backoff
  WEBSOCKET_CLOSE_CODES.BAD_GATEWAY
]