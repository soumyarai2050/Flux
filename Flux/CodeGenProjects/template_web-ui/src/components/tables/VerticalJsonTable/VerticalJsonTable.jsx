import React, { useState, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Popover,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Paper,
  Box,
} from '@mui/material';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import styles from './VerticalJsonTable.module.css';
import { useTheme } from '@emotion/react';

/**
 * VerticalJsonTable - A component that displays JSON data in a vertical table format.
 * 
 * @component
 */
function VerticalJsonTable({
  data,
  isOpen = false,
  onClose = () => { },
  maxHeight = '80vh',
  anchorEl = null,
  usePopover = false,
}) {
  // State for managing nested data popups
  const [nestedPopups, setNestedPopups] = useState([]);
  const containerRef = useRef(null);
  const theme = useTheme();

  /**
   * Handles the opening of a nested popup for complex data types
   *
   * @param {Object|Array} nestedData - The nested data to display
   * @param {string} nestedKey - The key associated with the nested data
   * @param {HTMLElement} anchorElement - The element to anchor the popover to
   * @param {Event} event - The click event
   */
  const handleNestedOpen = (nestedData, nestedKey, anchorElement, event) => {
    // stop propagation to prevent immediate closing
    if (event) {
      event.stopPropagation();
    }

    setNestedPopups([...nestedPopups, {
      data: nestedData,
      key: nestedKey,
      anchorEl: anchorElement
    }]);
  };

  /**
   * Closes a nested popup at a specific index
   *
   * @param {number} index - The index of the nested popup to close
   */
  const handleNestedClose = (index) => {
    setNestedPopups(nestedPopups.filter((_, i) => i !== index));
  };

  /**
   * Checks if a value is a complex type (object or array) that should be expandable
   *
   * @param {any} value - The value to check
   * @returns {boolean} - Whether the value is complex and expandable
   */
  const isComplexType = (value) => {
    return (value !== null && typeof value === 'object') || Array.isArray(value);
  };

  /**
   * Determines if an array contains objects that should be displayed in columnar format
   *
   * @param {Array} arr - The array to check
   * @returns {boolean} - Whether the array contains objects
   */
  const isArrayOfObjects = (arr) => {
    return Array.isArray(arr) && arr.length > 0 && arr.some(item => item !== null && typeof item === 'object' && !Array.isArray(item));
  };

  /**
   * Extracts all unique keys from an array of objects
   *
   * @param {Array} arr - Array of objects
   * @returns {Array} - Array of unique keys
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
   * Renders a cell based on the data type of the value
   *
   * @param {any} value - The value to render
   * @param {string} key - The key associated with the value
   * @returns {React.ReactNode} - The rendered cell content
   */
  const renderCell = (value, key) => {
    if (value === null) return <span className={styles.nullValue}>null</span>;
    if (value === undefined) return <span className={styles.undefinedValue}>undefined</span>;

    if (isComplexType(value)) {
      // For objects and arrays, show expand button
      const displayTitle = Array.isArray(value)
        ? `Array (${value.length} items)`
        : `Object (${Object.keys(value).length} properties)`;

      return (
        <div className={styles.complexValueContainer}>
          <span className={styles.typeIndicator}>{displayTitle}</span>
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
    } else if (typeof value === 'boolean') {
      // For booleans, show true/false with styling
      return <span className={`${styles.booleanValue} ${value ? styles.trueValue : styles.falseValue}`}>{String(value)}</span >;
    } else if (typeof value === 'string') {
      // For strings, wrap in quotes to distinguish from other types
      return <span className={styles.stringValue}>{value}</span>;
    } else {
      // For numbers and other primitives
      return <span className={styles.primitiveValue}>{String(value)}</span>;
    }
  };

  /**
   * Renders table rows for a JSON object
   *
   * @param {Object} obj - The object to render as rows
   * @returns {Array<React.ReactNode>} - Array of rendered rows
   */
  const renderObjectRows = (obj) => {
    return Object.keys(obj).map((key) => (
      <TableRow key={key} hover>
        <TableCell
          component="th"
          scope="row"
          className={styles.headerCell}
          aria-label={`Property: ${key}`}
        >
          {key}
        </TableCell>
        <TableCell className={styles.dataCell}>{renderCell(obj[key], key)}</TableCell>
      </TableRow>
    ));
  };


  /**
   * Renders table for an array of objects
   *
   * @param {Array} arr - The array of objects to render
   * @returns {React.ReactNode} - The rendered table
   */
  const renderArrayOfObjectsTable = (arr) => {
    const allKeys = getAllKeysFromArrayOfObjects(arr);

    return (
      <TableContainer component={Paper} className={styles.tableContainer} style={{ maxHeight }}>
        <Table stickyHeader aria-label="array of objects table" className={styles.table}>
          <TableHead>
            <TableRow>
              {arr.map((_, index) => (
                <TableCell key={index} className={styles.tableHeaderCell}>{index}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {allKeys.map((key) => (
              <TableRow key={key} hover>
                <TableCell component="th" scope="row" className={styles.headerCell} aria-label={`Field: ${key}`}>
                  {key}
                </TableCell>
                {arr.map((item, index) => (
                  <TableCell key={index} className={styles.dataCell}>
                    {(item && typeof item === 'object' && !Array.isArray(item) && key in item)
                      ? renderCell(item[key], `${key}[${index}]`)
                      : <span className={styles.nullValue}>--</span>}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  /**
   * Renders table rows for a JSON array (for arrays not containing objects)
   *
   * @param {Array} arr - The array to render as rows
   * @returns {Array<React.ReactNode>} - Array of rendered rows
   */
  const renderArrayRows = (arr) => {
    return arr.map((item, index) => (
      <TableRow key={index} hover>
        <TableCell component="th" scope="row" className={styles.headerCell} aria-label={`Index: ${index}`}>
          {`[${index}]`}
        </TableCell>
        <TableCell className={styles.dataCell}>{renderCell(item, `[${index}]`)}</TableCell>
      </TableRow>
    ));
  };

  /**
   * Renders the content of the table based on the data type
   */
  const renderTableContent = (tableData) => {
    if (!tableData) return null;

    // Special handling for arrays of objects
    if (isArrayOfObjects(tableData)) {
      return renderArrayOfObjectsTable(tableData);
    }

    return (
      <TableContainer component={Paper} className={styles.tableContainer} style={{ maxHeight }}>
        <Table stickyHeader aria-label="vertical json data table" className={styles.table}>
          <TableHead>
            <TableRow>
              <TableCell className={styles.tableHeaderCell} sx={{ background: 'inherit' }}>Key</TableCell>
              <TableCell className={styles.tableHeaderCell} sx={{ background: 'inherit' }}>Value</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Array.isArray(tableData) ? renderArrayRows(tableData) : renderObjectRows(tableData)}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  /**
   * Safely handle popover close
   */
  const handlePopoverClose = (event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (isOpen) onClose();
  };

  /**
   * Renders a nested data popover
   */
  const renderNestedPopover = (popup, index) => {
    return (
      <Popover
        key={`popup-${index}`}
        open={Boolean(popup.anchorEl)}
        anchorEl={popup.anchorEl}
        onClose={(event) => {
          event.stopPropagation();
          handleNestedClose(index);
        }}
        anchorOrigin={{
          vertical: 'center',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'center',
          horizontal: 'left',
        }}
        className={styles.popover}
        slotProps={{
          paper: {
            className: styles.popoverPaper,
          }
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {renderTableContent(popup.data)}
      </Popover>
    );
  };

  // The table content to be rendered
  const tableContent = renderTableContent(data);

  // If usePopover is true AND isOpen is true, render the popover
  if (usePopover) {
    let popoverPosition = anchorEl
      ? {
        anchorEl: anchorEl,
        anchorOrigin: {
          vertical: 'bottom',
          horizontal: 'left',
        },
        transformOrigin: {
          vertical: 'top',
          horizontal: 'left',
        },
      }
      : { // If no anchorEl provided, center on screen
        anchorReference: "anchorPosition",
        anchorPosition: { top: window.innerHeight / 2, left: window.innerWidth / 2 },
        transformOrigin: {
          vertical: 'center',
          horizontal: 'center',
        },
      };

    // Only render the popover if isOpen is true
    if (usePopover) {
      return (
        <>
          <Popover
            open={isOpen} // We only render when it's open, so this is always true
            onClose={handlePopoverClose}
            {...popoverPosition}
            className={styles.popover}
            slotProps={{
              paper: {
                className: styles.mainPopoverPaper,
                onClick: (e) => e.stopPropagation() // Prevent clicks inside from bubbling
              }
            }}
            onClick={(e) => e.stopPropagation()} // Extra protection against click bubbling
          >
            <Box
              className={styles.popoverContent}
              onClick={(e) => e.stopPropagation()} // Even more protection
            >
              {tableContent}
            </Box>
          </Popover>

          {/* Render all nested popovers */}
          {nestedPopups.map((popup, index) => renderNestedPopover(popup, index))}
        </>
      );
    } else if (isOpen) {
      // Default rendering - direct table with no popover
      return (
        <div className={styles.directContainer}>
          {tableContent}
          {/* Nested popups are always in popovers */}
          {nestedPopups.map((popup, index) => renderNestedPopover(popup, index))}
        </div>
      );
    } else {
      // Don't render anything when closed
      return null;
    }
  }
};

VerticalJsonTable.propTypes = {
  /**
   * JSON data to display in the table
   */
  data: PropTypes.oneOfType([
    PropTypes.object,
    PropTypes.array
  ]).isRequired,

  /**
   * Controls whether the popup is open (only used when usePopover=true)
   */
  isOpen: PropTypes.bool,

  /**
   * Callback function for when the popup is closed (only used when usePopover=true)
   */
  onClose: PropTypes.func,

  /**
   * Maximum height for the table container
   */
  maxHeight: PropTypes.string,

  /**
   * Element to anchor the popover to (only used when usePopover=true)
   * If not provided, popover will be centered on screen
   */
  anchorEl: PropTypes.object,

  /**
   * Whether to display in a popover instead of directly
   */
  usePopover: PropTypes.bool,
};

export default VerticalJsonTable;