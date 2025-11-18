import React, { useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import Popover from '@mui/material/Popover';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import TablePagination from '@mui/material/TablePagination';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import ContentCopy from '@mui/icons-material/ContentCopy';
import Check from '@mui/icons-material/Check';
import styles from './VerticalDataTable.module.css';
import ClipboardCopier from '../../../utility/ClipboardCopier';
import ValueBasedToggleButton from '../../../ui/ValueBasedToggleButton';
import { getColorFromMapping, getResolvedColor } from '../../../../utils/ui/colorUtils';
import { getSizeFromValue, getShapeFromValue } from '../../../../utils/ui/uiUtils';
import { useTheme } from '@mui/material/styles';

// ============================================================================
// Constants
// ============================================================================

const COPY_TIMEOUT_MS = 2000;
const DEFAULT_PAGINATION_KEY = 'main';

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Flattens a nested object into dot-notation keys.
 * @param {Object} obj - The object to flatten
 * @param {string} prefix - Current prefix for nested keys
 * @returns {Object} Flattened object with dot-notation keys
 * @example flattenObject({ user: { name: "Alice" } }) => { "user.name": "Alice" }
 */
const flattenObject = (obj, prefix = '') => {
  const flattened = {};
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      const value = obj[key];
      const newKey = prefix ? `${prefix}.${key}` : key;
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        Object.assign(flattened, flattenObject(value, newKey));
      } else {
        flattened[newKey] = value;
      }
    }
  }
  return flattened;
};

/**
 * Checks if a value should be treated as expandable.
 * @param {*} value - The value to check
 * @param {boolean} flattenObjects - Whether objects should be flattened
 * @returns {boolean} True if value is expandable
 */
const isComplexType = (value, flattenObjects) => {
  if (flattenObjects) return Array.isArray(value);
  return (value !== null && typeof value === 'object') || Array.isArray(value);
};

/**
 * Checks if an array contains objects.
 * @param {Array} arr - The array to check
 * @returns {boolean} True if array contains at least one object
 */
const isArrayOfObjects = (arr) => {
  return Array.isArray(arr) && arr.length > 0 && arr.some(item =>
    item !== null && typeof item === 'object' && !Array.isArray(item)
  );
};

/**
 * Extracts all unique keys from an array of objects.
 * @param {Array} arr - Array of objects
 * @returns {string[]} Array of unique keys
 */
const getAllKeysFromArrayOfObjects = (arr) => {
  const keys = new Set();
  arr.forEach(obj => {
    if (obj !== null && typeof obj === 'object' && !Array.isArray(obj)) {
      Object.keys(obj).forEach(key => keys.add(key));
    }
  });
  return Array.from(keys);
};

/**
 * Calculates paginated array slice.
 * @param {Array} arr - Array to paginate
 * @param {Object} paginationState - Current pagination state
 * @param {string} paginationKey - Key for this pagination instance
 * @param {number} itemsPerPage - Items per page
 * @param {boolean} enablePagination - Whether pagination is enabled
 * @returns {Object} Pagination data and sliced array
 */
const getPaginatedData = (arr, paginationState, paginationKey, itemsPerPage, enablePagination) => {
  const currentPage = paginationState[paginationKey] || 0;
  const startIdx = currentPage * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const paginatedArr = enablePagination ? arr.slice(startIdx, endIdx) : arr;
  return { paginatedArr, currentPage, startIdx, endIdx };
};

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Copy button with visual feedback.
 */
const CopyButton = ({ copyKey, isCopied, onCopy, title = "Copy row data" }) => (
  <IconButton
    size="small"
    onClick={(e) => {
      e.stopPropagation();
      onCopy(copyKey);
    }}
    title={title}
    className={styles.iconButton}
  >
    {isCopied ? (
      <Check fontSize="small" className={styles.checkIcon} />
    ) : (
      <ContentCopy fontSize="small" />
    )}
  </IconButton>
);

CopyButton.propTypes = {
  copyKey: PropTypes.string.isRequired,
  isCopied: PropTypes.bool.isRequired,
  onCopy: PropTypes.func.isRequired,
  title: PropTypes.string
};

/**
 * Reusable table wrapper with common structure.
 */
const TableWrapper = ({
  children,
  maxHeight,
  ariaLabel,
  clipboardText,
  showPagination,
  paginationProps
}) => (
  <TableContainer component={Paper} className={styles.tableContainer} style={{ maxHeight }}>
    <Table stickyHeader aria-label={ariaLabel} className={styles.table}>
      {children}
    </Table>
    <ClipboardCopier text={clipboardText} />
    {showPagination && <TablePagination {...paginationProps} />}
  </TableContainer>
);

TableWrapper.propTypes = {
  children: PropTypes.node.isRequired,
  maxHeight: PropTypes.string,
  ariaLabel: PropTypes.string.isRequired,
  clipboardText: PropTypes.string,
  showPagination: PropTypes.bool.isRequired,
  paginationProps: PropTypes.object
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * VerticalDataTable - Displays JSON data in a vertical table format with expandable nested data.
 *
 * Key Features:
 * - Displays objects with keys as rows and values as columns
 * - Supports nested data exploration via expandable popups
 * - Optional object flattening into dot-notation (e.g., user.name)
 * - Copy functionality for individual rows or entire table
 * - Pagination support for arrays with independent state per popup
 * - Can render standalone or within a popover
 * - Supports button fields with metadata-driven rendering
 *
 * @component
 * @example
 * // Standalone usage
 * <VerticalDataTable
 *   data={{ name: "John", age: 30 }}
 *   isOpen={true}
 * />
 *
 * @example
 * // Popover usage
 * <VerticalDataTable
 *   data={userData}
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   usePopover={true}
 *   anchorEl={buttonRef.current}
 * />
 *
 * @example
 * // With button fields
 * <VerticalDataTable
 *   data={{ status: "active", value: 42 }}
 *   isOpen={true}
 *   fieldsMetadata={[
 *     {
 *       key: "status",
 *       type: "button",
 *       button: {
 *         pressed_value_as_text: "active",
 *         unpressed_caption: "Inactive",
 *         pressed_caption: "Active",
 *         value_color_map: { active: "success", inactive: "error" }
 *       }
 *     }
 *   ]}
 * />
 */
function VerticalDataTable({
  data,
  isOpen = false,
  onClose = () => { },
  maxHeight = '80vh',
  anchorEl = null,
  usePopover = false,
  flattenObjects = true,
  itemsPerPage = 10,
  enablePagination = true,
  fieldsMetadata = [],
}) {
  // ============================================================================
  // Hooks
  // ============================================================================

  const theme = useTheme();

  // ============================================================================
  // State Management
  // ============================================================================

  const [nestedPopups, setNestedPopups] = useState([]);
  const [clipboardText, setClipboardText] = useState(null);
  const [copiedKey, setCopiedKey] = useState(null);
  const [paginationState, setPaginationState] = useState({ main: 0 });

  // ============================================================================
  // Helper Functions
  // ============================================================================

  /**
   * Finds field metadata by key from fieldsMetadata array.
   * Strips array indices [n] and uses base key for lookup.
   */
  const getFieldMetadata = useCallback((key) => {
    if (!fieldsMetadata || fieldsMetadata.length === 0) return null;

    // Strip array index suffix like [0], [1], etc.
    // Also handle nested paths by taking the last segment after dot
    let baseKey = key.replace(/\[\d+\]$/, ''); // Remove [n] suffix

    // For flattened objects with dot notation (e.g., "parent.child"), use the last part
    if (baseKey.includes('.')) {
      const parts = baseKey.split('.');
      baseKey = parts[parts.length - 1];
    }

    return fieldsMetadata.find(field =>
      field.key === baseKey ||
      field.xpath === baseKey ||
      field.key === key ||
      field.xpath === key
    );
  }, [fieldsMetadata]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handles pagination page change.
   */
  const handlePageChange = useCallback((paginationKey) => (event, newPage) => {
    setPaginationState(prev => ({
      ...prev,
      [paginationKey]: newPage
    }));
  }, []);

  /**
   * Converts value to string for clipboard.
   */
  const valueToString = useCallback((value) => {
    if (value === null || value === undefined) return '--';
    if (typeof value === 'object' && !Array.isArray(value)) {
      return `Object (${Object.keys(value).length} properties)`;
    }
    if (Array.isArray(value)) return `Array (${value.length} items)`;
    return String(value);
  }, []);

  /**
   * Handles copying data to clipboard with visual feedback.
   */
  const handleCopy = useCallback((key, values) => {
    const text = key === 'copy-all'
      ? JSON.stringify(data ?? '')
      : [key, ...values.map(valueToString)].join('\n');

    setClipboardText(text);
    setCopiedKey(key);

    setTimeout(() => {
      setClipboardText(null);
      setCopiedKey(null);
    }, COPY_TIMEOUT_MS);
  }, [data, valueToString]);

  /**
   * Opens a nested popup for complex data types.
   */
  const handleNestedOpen = useCallback((nestedData, nestedKey, anchorElement, event) => {
    if (event) event.stopPropagation();

    const popupId = `popup-${nestedPopups.length}`;

    setNestedPopups([...nestedPopups, {
      data: nestedData,
      key: nestedKey,
      anchorEl: anchorElement,
      paginationKey: popupId
    }]);

    setPaginationState(prev => ({ ...prev, [popupId]: 0 }));
  }, [nestedPopups]);

  /**
   * Closes a nested popup and cleans up its state.
   */
  const handleNestedClose = useCallback((index) => {
    const closedPopup = nestedPopups[index];

    setNestedPopups(nestedPopups.filter((_, i) => i !== index));

    if (closedPopup?.paginationKey) {
      setPaginationState(prev => {
        const newState = { ...prev };
        delete newState[closedPopup.paginationKey];
        return newState;
      });
    }
  }, [nestedPopups]);

  /**
   * Handles popover close with event safety.
   */
  const handlePopoverClose = useCallback((event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (isOpen) onClose();
  }, [isOpen, onClose]);

  // ============================================================================
  // Rendering Functions
  // ============================================================================

  /**
   * Gets display text for complex types.
   */
  const getComplexTypeDisplay = useCallback((value) => {
    return Array.isArray(value)
      ? `Array (${value.length} items)`
      : `Object (${Object.keys(value).length} properties)`;
  }, []);

  /**
   * Renders a button field using ValueBasedToggleButton.
   */
  const renderButtonField = useCallback((value, key, collection) => {
    // If value not set, show null placeholder
    if (value === undefined || value === null) {
      return <span className={styles.nullValue}>--</span>;
    }

    const buttonConfig = collection.button;
    if (!buttonConfig) {
      return <span className={styles.primitiveValue}>{String(value)}</span>;
    }

    // Parse disabled captions if present
    const disabledValueCaptionDict = {};
    if (buttonConfig.disabled_captions) {
      buttonConfig.disabled_captions.split(',').forEach(valueCaptionPair => {
        const [val, caption] = valueCaptionPair.split('=');
        disabledValueCaptionDict[val] = caption;
      });
    }

    const isDisabledValue = disabledValueCaptionDict.hasOwnProperty(String(value));
    const disabledCaption = isDisabledValue ? disabledValueCaptionDict[String(value)] : '';
    const checked = String(value) === buttonConfig.pressed_value_as_text;
    const colorIdentifier = getColorFromMapping(collection, String(value), null, theme, null, false);
    const color = getResolvedColor(colorIdentifier, theme, null, true);
    const size = getSizeFromValue(buttonConfig.button_size);
    const shape = getShapeFromValue(buttonConfig.button_type);

    let caption = String(value);
    if (isDisabledValue) {
      caption = disabledCaption;
    } else if (checked && buttonConfig.pressed_caption) {
      caption = buttonConfig.pressed_caption;
    } else if (!checked && buttonConfig.unpressed_caption) {
      caption = buttonConfig.unpressed_caption;
    }

    return (
      <ValueBasedToggleButton
        size={size}
        shape={shape}
        color={color}
        value={value}
        caption={caption}
        xpath={null}
        disabled={isDisabledValue}
        action={buttonConfig.action}
        allowForceUpdate={buttonConfig.allow_force_update}
        dataSourceId={null}
        source={null}
        onClick={null}
        iconName={buttonConfig.button_icon_name}
        hideCaption={buttonConfig.hide_caption}
      />
    );
  }, []);

  /**
   * Renders a cell based on value type.
   */
  const renderCell = useCallback((value, key) => {
    if (value === null) return <span className={styles.nullValue}>null</span>;
    if (value === undefined) return <span className={styles.undefinedValue}>undefined</span>;

    // Check if field has button metadata (identified by presence of button attribute)
    const fieldMeta = getFieldMetadata(key);
    if (fieldMeta && fieldMeta.button) {
      return renderButtonField(value, key, fieldMeta);
    }

    if (isComplexType(value, flattenObjects)) {
      return (
        <div className={styles.complexValueContainer}>
          <span className={styles.typeIndicator}>{getComplexTypeDisplay(value)}</span>
          <IconButton
            onClick={(event) => handleNestedOpen(value, key, event.currentTarget, event)}
            size="small"
            aria-label={`Expand ${key}`}
            className={styles.expandButton}
          >
            <MoreHorizIcon fontSize="small" />
          </IconButton>
        </div>
      );
    }

    if (typeof value === 'boolean') {
      return <span className={`${styles.booleanValue} ${value ? styles.trueValue : styles.falseValue}`}>{String(value)}</span>;
    }

    if (typeof value === 'string') {
      return <span className={styles.stringValue}>{value}</span>;
    }

    return <span className={styles.primitiveValue}>{String(value)}</span>;
  }, [flattenObjects, getComplexTypeDisplay, handleNestedOpen, getFieldMetadata, renderButtonField]);

  /**
   * Renders table rows for an object.
   */
  const renderObjectRows = useCallback((obj) => {
    const dataToRender = flattenObjects ? flattenObject(obj) : obj;

    return Object.entries(dataToRender).map(([key, value]) => (
      <TableRow key={key} hover>
        <TableCell component="th" scope="row" className={styles.headerCell} aria-label={`Property: ${key}`}>
          <div className={styles.flexContainer}>
            <span>{key}</span>
            <CopyButton copyKey={key} isCopied={copiedKey === key} onCopy={(k) => handleCopy(k, [value])} />
          </div>
        </TableCell>
        <TableCell className={styles.dataCell}>{renderCell(value, key)}</TableCell>
      </TableRow>
    ));
  }, [flattenObjects, copiedKey, handleCopy, renderCell]);

  /**
   * Renders table for array of objects.
   */
  const renderArrayOfObjectsTable = useCallback((arr, paginationKey = DEFAULT_PAGINATION_KEY) => {
    const { paginatedArr, currentPage, startIdx } = getPaginatedData(
      arr, paginationState, paginationKey, itemsPerPage, enablePagination
    );

    const processedArr = flattenObjects
      ? paginatedArr.map(item => (item && typeof item === 'object' && !Array.isArray(item) ? flattenObject(item) : item))
      : paginatedArr;

    const allKeys = getAllKeysFromArrayOfObjects(processedArr);

    return (
      <TableWrapper
        maxHeight={maxHeight}
        ariaLabel="array of objects table"
        clipboardText={clipboardText}
        showPagination={enablePagination && arr.length > itemsPerPage}
        paginationProps={{
          component: "div",
          count: arr.length,
          page: currentPage,
          onPageChange: handlePageChange(paginationKey),
          rowsPerPage: itemsPerPage,
          rowsPerPageOptions: [itemsPerPage],
          labelDisplayedRows: ({ from, to, count }) => `${from}-${to} of ${count} items`
        }}
      >
        <TableHead>
          <TableRow>
            <TableCell className={styles.tableHeaderCell}>
              <span>Field</span>
              <CopyButton
                copyKey="copy-all"
                isCopied={copiedKey === 'copy-all'}
                onCopy={() => handleCopy('copy-all', null)}
                title="Copy table"
              />
            </TableCell>
            {processedArr.map((_, index) => (
              <TableCell key={index} className={styles.tableHeaderCell}>{startIdx + index}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {allKeys.map((key) => {
            const values = processedArr.map((item) => {
              if (item && typeof item === 'object' && !Array.isArray(item) && key in item) {
                return item[key];
              }
              return null;
            });

            return (
              <TableRow key={key} hover>
                <TableCell component="th" scope="row" className={styles.headerCell} aria-label={`Field: ${key}`}>
                  <div className={styles.flexContainer}>
                    <span>{key}</span>
                    <CopyButton
                      copyKey={key}
                      isCopied={copiedKey === key}
                      onCopy={(k) => handleCopy(k, values)}
                    />
                  </div>
                </TableCell>
                {processedArr.map((item, index) => (
                  <TableCell key={index} className={styles.dataCell}>
                    {(item && typeof item === 'object' && !Array.isArray(item) && key in item)
                      ? renderCell(item[key], `${key}[${index}]`)
                      : <span className={styles.nullValue}>--</span>}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}
        </TableBody>
      </TableWrapper>
    );
  }, [paginationState, flattenObjects, itemsPerPage, enablePagination, maxHeight, clipboardText, copiedKey, handleCopy, handlePageChange, renderCell]);

  /**
   * Renders table rows for simple arrays.
   */
  const renderArrayRows = useCallback((arr, paginationKey = DEFAULT_PAGINATION_KEY) => {
    const { paginatedArr, startIdx } = getPaginatedData(
      arr, paginationState, paginationKey, itemsPerPage, enablePagination
    );

    return paginatedArr.map((item, index) => {
      const actualIndex = startIdx + index;
      return (
        <TableRow key={actualIndex} hover>
          <TableCell component="th" scope="row" className={styles.headerCell} aria-label={`Index: ${actualIndex}`}>
            <div className={styles.flexContainer}>
              <span>{`[${actualIndex}]`}</span>
              <CopyButton
                copyKey={`[${actualIndex}]`}
                isCopied={copiedKey === `[${actualIndex}]`}
                onCopy={(k) => handleCopy(k, [item])}
              />
            </div>
          </TableCell>
          <TableCell className={styles.dataCell}>{renderCell(item, `[${actualIndex}]`)}</TableCell>
        </TableRow>
      );
    });
  }, [paginationState, itemsPerPage, enablePagination, copiedKey, handleCopy, renderCell]);

  /**
   * Renders table content based on data type.
   */
  const renderTableContent = useCallback((tableData, paginationKey = DEFAULT_PAGINATION_KEY) => {
    if (!tableData) return null;

    // Array of objects - special columnar layout
    if (isArrayOfObjects(tableData)) {
      return renderArrayOfObjectsTable(tableData, paginationKey);
    }

    // Simple array - indexed rows
    if (Array.isArray(tableData)) {
      const { currentPage } = getPaginatedData(
        tableData, paginationState, paginationKey, itemsPerPage, enablePagination
      );

      return (
        <TableWrapper
          maxHeight={maxHeight}
          ariaLabel="vertical json data table"
          clipboardText={clipboardText}
          showPagination={enablePagination && tableData.length > itemsPerPage}
          paginationProps={{
            component: "div",
            count: tableData.length,
            page: currentPage,
            onPageChange: handlePageChange(paginationKey),
            rowsPerPage: itemsPerPage,
            rowsPerPageOptions: [itemsPerPage],
            labelDisplayedRows: ({ from, to, count }) => `${from}-${to} of ${count} items`
          }}
        >
          <TableHead>
            <TableRow>
              <TableCell className={styles.tableHeaderCell}>
                <span>Key</span>
                <CopyButton
                  copyKey="copy-all"
                  isCopied={copiedKey === 'copy-all'}
                  onCopy={() => handleCopy('copy-all', null)}
                  title="Copy table"
                />
              </TableCell>
              <TableCell className={styles.tableHeaderCell}>Value</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {renderArrayRows(tableData, paginationKey)}
          </TableBody>
        </TableWrapper>
      );
    }

    // Object - key-value pairs
    return (
      <TableWrapper
        maxHeight={maxHeight}
        ariaLabel="vertical json data table"
        clipboardText={clipboardText}
        showPagination={false}
      >
        <TableHead>
          <TableRow>
            <TableCell className={styles.tableHeaderCell}>
              <span>Key</span>
              <CopyButton
                copyKey="copy-all"
                isCopied={copiedKey === 'copy-all'}
                onCopy={() => handleCopy('copy-all', null)}
                title="Copy table"
              />
            </TableCell>
            <TableCell className={styles.tableHeaderCell}>Value</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {renderObjectRows(tableData)}
        </TableBody>
      </TableWrapper>
    );
  }, [paginationState, itemsPerPage, enablePagination, maxHeight, clipboardText, copiedKey, handleCopy, handlePageChange, renderArrayOfObjectsTable, renderArrayRows, renderObjectRows]);

  /**
   * Renders a nested data popover.
   */
  const renderNestedPopover = useCallback((popup, index) => (
    <Popover
      key={`popup-${index}`}
      open={Boolean(popup.anchorEl)}
      anchorEl={popup.anchorEl}
      onClose={(event) => {
        event.stopPropagation();
        handleNestedClose(index);
      }}
      anchorOrigin={{ vertical: 'center', horizontal: 'right' }}
      transformOrigin={{ vertical: 'center', horizontal: 'left' }}
      className={styles.popover}
      slotProps={{ paper: { className: styles.popoverPaper } }}
      onClick={(e) => e.stopPropagation()}
    >
      {renderTableContent(popup.data, popup.paginationKey)}
    </Popover>
  ), [handleNestedClose, renderTableContent]);

  // ============================================================================
  // Memoized Content
  // ============================================================================

  const tableContent = useMemo(() => renderTableContent(data), [data, renderTableContent]);

  // ============================================================================
  // Render Logic
  // ============================================================================

  if (!isOpen) return null;

  // Popover mode
  if (usePopover) {
    const popoverPosition = anchorEl
      ? {
        anchorEl: anchorEl,
        anchorOrigin: { vertical: 'bottom', horizontal: 'left' },
        transformOrigin: { vertical: 'top', horizontal: 'left' },
      }
      : {
        anchorReference: "anchorPosition",
        anchorPosition: { top: window.innerHeight / 2, left: window.innerWidth / 2 },
        transformOrigin: { vertical: 'center', horizontal: 'center' },
      };

    return (
      <>
        <Popover
          open={isOpen}
          onClose={handlePopoverClose}
          {...popoverPosition}
          className={styles.popover}
          slotProps={{
            paper: {
              className: styles.mainPopoverPaper,
              onClick: (e) => e.stopPropagation()
            }
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Box className={styles.popoverContent} onClick={(e) => e.stopPropagation()}>
            {tableContent}
          </Box>
        </Popover>
        {nestedPopups.map((popup, index) => renderNestedPopover(popup, index))}
      </>
    );
  }

  // Direct rendering mode
  return (
    <>
      <div className={styles.directContainer}>{tableContent}</div>
      {nestedPopups.map((popup, index) => renderNestedPopover(popup, index))}
    </>
  );
}

// ============================================================================
// PropTypes
// ============================================================================

VerticalDataTable.propTypes = {
  /** JSON data to display (object or array) */
  data: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array
  ]).isRequired,

  /** Controls component visibility */
  isOpen: PropTypes.bool,

  /** Callback when popover closes */
  onClose: PropTypes.func,

  /** Maximum height for table container */
  maxHeight: PropTypes.string,

  /** Anchor element for popover positioning */
  anchorEl: PropTypes.object,

  /** Display as popover instead of inline */
  usePopover: PropTypes.bool,

  /** Flatten nested objects to dot-notation (e.g., user.name) */
  flattenObjects: PropTypes.bool,

  /** Number of items per page for arrays */
  itemsPerPage: PropTypes.number,

  /** Enable pagination for arrays */
  enablePagination: PropTypes.bool,

  /** Array of field metadata objects for special rendering (buttons, etc.) */
  fieldsMetadata: PropTypes.arrayOf(PropTypes.shape({
    key: PropTypes.string,
    xpath: PropTypes.string,
    type: PropTypes.string,
    button: PropTypes.object,
  })),
};

export default VerticalDataTable;
