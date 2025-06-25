import React, { useEffect, useMemo, useState, useRef } from 'react';
import { debounce } from 'lodash';
import PropTypes from 'prop-types';
import { Popover, Select, Box, Tabs, Tab, TextField, Tooltip } from '@mui/material';
import { Help, PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';

import { LAYOUT_TYPES, MODEL_TYPES, HIGHLIGHT_STATES } from '../../../constants';
import styles from './TableSettingsMenu.module.css';

/**
 * TableSettingsMenu provides a popover menu for toggling column visibility,
 * ordering, and additional "more/less" options.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Array} props.columns - Array of column objects. Each should include:
 *   - key: string (unique identifier)
 *   - sequenceNumber: number (default order)
 *   - sourceIndex: number (used for filtering columns)
 *   - hide: boolean (visibility toggle)
 *   - showLess: boolean (toggle for less/more display)
 * @param {Array} [props.columnOrders] - Array of column order objects. Each should include:
 *   - column_name: string
 *   - sequence: number
 * @param {function} props.onColumnToggle - Callback when an individual column's visibility is toggled.
 * @param {function} props.onColumnOrdersChange - Callback when an individual column's order is changed.
 *   Receives the new sequence (number) and the column key (string) as arguments.
 * @param {function} props.onShowLessToggle - Callback when an individual column's "show less" toggle is clicked.
 *
 *
 * @returns {JSX.Element} The rendered component.
 */
const TableSettingsMenu = ({
  columns,
  columnOrders,
  onColumnToggle,
  onColumnOrdersChange,
  onShowLessToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  modelType,
  layout,
  onAbsoluteSortToggle,
  commonKeyCollapse,
  onCommonKeyCollapseToggle,
  stickyHeader,
  onStickyHeaderToggle,
  onFrozenToggle,
  columnNameOverride = [],
  onColumnNameOverrideChange,
  highlightUpdateOverride = [],
  onHighlightUpdateOverrideChange
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [tabIndex, setTabIndex] = useState(0);
  const [searchValue, setSearchValue] = useState('');
  const [filteredColumns, setFilteredColumns] = useState(columns);
  const [columnNameOverrideDict, setColumnNameOverrideDict] = useState(() =>
    columnNameOverride.reduce((acc, item) => {
      const [name, override] = item.split(':');
      acc[name] = override;
      return acc;
    }, {})
  );
  const [highlightUpdateOverrideDict, setHighlightUpdateOverrideDict] = useState(() =>
    highlightUpdateOverride.reduce((acc, item) => {
      const [name, override] = item.split(':');
      acc[name] = override;
      return acc;
    }, {})
  );

  const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';

  useEffect(() => {
    if (searchValue) {
      const lowerCasedValue = searchValue.toLowerCase();
      const updatedColumns = columns.filter((column) => column[fieldKey]?.toLowerCase().includes(lowerCasedValue));
      setFilteredColumns(updatedColumns);
    } else {
      setFilteredColumns(columns);
    }
  }, [columns]);

  const debouncedTransform = useRef(
    debounce((value) => {
      if (value) {
        const lowerCasedValue = value.toLowerCase();
        const updatedColumns = columns.filter((column) => column[fieldKey]?.toLowerCase().includes(lowerCasedValue));
        setFilteredColumns(updatedColumns);
      } else {
        setFilteredColumns(columns);
      }
    }, 300)
  ).current;

  const menuName = 'table-settings';
  const isPopoverOpen = Boolean(anchorEl);
  const popoverId = isPopoverOpen ? `${menuName}-popover` : undefined;

  // Determine the maximum sequence number among columns for ordering purposes.
  // const maxSequence = useMemo(() => {
  //   if (!columns || columns.length === 0) return 0;
  //   return Math.max(...columns.map((column) => column.sequenceNumber));
  // }, [columns]);

  const handlePopoverOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    onMenuClose();
    setAnchorEl(null);
  };

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  };

  const handleSearchValueChange = (e) => {
    setSearchValue(e.target.value);
    debouncedTransform(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key.length === 1 || ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  };

  const handleTextChange = (e, fieldKey) => {
    setColumnNameOverrideDict((prev) => ({
      ...prev,
      [fieldKey]: e.target.value,
    }));
  };

  const handleBlur = () => {
    // Construct the array of strings for columnNameOverride
    const updatedColumnNameOverride = Object.keys(columnNameOverrideDict).map(
      (name) => `${name}:${columnNameOverrideDict[name]}`
    );
    onColumnNameOverrideChange(updatedColumnNameOverride);
  };

  const handleHighlightUpdateChange = (fieldKey, value) => {
    let updatedDict;
    setHighlightUpdateOverrideDict((prev) => {
      updatedDict = {
        ...prev,
        [fieldKey]: value,
      };
      return updatedDict;
    });
    const updatedHighlightUpdateOverride = Object.keys(updatedDict).map(
      (name) => `${name}:${updatedDict[name]}`
    );
    onHighlightUpdateOverrideChange(updatedHighlightUpdateOverride);
  };

  if (![LAYOUT_TYPES.TABLE, LAYOUT_TYPES.ABBREVIATION_MERGE, LAYOUT_TYPES.PIVOT_TABLE, LAYOUT_TYPES.CHART].includes(layout)) return null;

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinComponent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handlePopoverOpen}>
            <span>
              <Settings sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinComponent onClick={handlePinToggle} fontSize="small" />}
          </MenuItem>
        )
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handlePopoverOpen}>
            <Settings fontSize="small" color="white" />
          </Icon>
        )
    }
  };

  return (
    <>
      {renderMenu()}
      <Popover
        id={popoverId}
        open={isPopoverOpen}
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        onClose={handlePopoverClose}
      >
        <Box sx={{ display: 'flex', width: 400, maxHeight: 600 }}>
          <Tabs
            orientation="vertical"
            value={tabIndex}
            onChange={(e, newValue) => setTabIndex(newValue)}
            sx={{ borderRight: 1, borderColor: 'divider', minWidth: 100 }}
          >
            <Tab label="Settings" />
            <Tab label="Show/More" />
            <Tab label="Absolute Sort" />
            <Tab label="Freeze" />
            <Tab label="Column Name/Help" />
            <Tab label="Highlight" />
            {/* <Tab label="Sequence" /> */}
          </Tabs>
          {/* Tab Content */}
          <Box className={styles.content}>
            <TextField
              size="small"
              label="Column Name"
              value={searchValue}
              onChange={handleSearchValueChange}
              onKeyDown={handleKeyDown}
              autoFocus
              InputProps={{
                style: { padding: '6px 10px' },
              }}
            />
            {tabIndex === 0 && (
              <>
                <Box className={styles.item}>
                  <span className={styles.item_label}>Common Key</span>
                  <ValueBasedToggleButton
                    name="common_key_collapse"
                    size="small"
                    selected={commonKeyCollapse}
                    disabled={false}
                    value={commonKeyCollapse}
                    captions={commonKeyCollapse ? 'Expand' : 'Collapse'}
                    xpath="common_key_collapse"
                    color={commonKeyCollapse ? 'debug' : 'info'}
                    onClick={onCommonKeyCollapseToggle}
                  />
                </Box>
                <Box className={styles.item}>
                  <span className={styles.item_label}>Sticky Header</span>
                  <ValueBasedToggleButton
                    name="sticky_header"
                    size="small"
                    selected={stickyHeader}
                    disabled={false}
                    value={stickyHeader}
                    captions={stickyHeader ? 'Disable' : 'Enable'}
                    xpath="sticky_header"
                    color={stickyHeader ? 'info' : 'debug'}
                    onClick={onStickyHeaderToggle}
                  />
                </Box>
              </>
            )}
            {tabIndex === 1 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;

                  // Determine the toggle states and captions.
                  const show = !column.hide;
                  const showCaption = show ? 'Hide' : 'Show';
                  const showColor = show ? 'success' : 'debug';
                  const more = !column.showLess;
                  const moreDisabled = column.hide;
                  const moreCaption = more ? 'Less' : 'More';
                  const moreColor = more ? 'info' : 'debug';

                  return (
                    <Box key={column[fieldKey]} className={styles.item}>
                      <span className={styles.item_label}>{columnLabel}</span>
                      <ValueBasedToggleButton
                        name={column[fieldKey]}
                        size="small"
                        selected={show}
                        disabled={false}
                        value={show}
                        caption={showCaption}
                        xpath={column[fieldKey]}
                        color={showColor}
                        onClick={onColumnToggle}
                      />
                      <ValueBasedToggleButton
                        name={column[fieldKey]}
                        size="small"
                        selected={more}
                        disabled={moreDisabled}
                        value={more}
                        caption={moreCaption}
                        xpath={column[fieldKey]}
                        color={moreColor}
                        onClick={onShowLessToggle}
                      />
                    </Box>
                  );
                })}
              </>
            )}
            {tabIndex === 2 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
                  // Determine the toggle states and captions.
                  const absoluteSort = column.absoluteSort ?? false;
                  const showCaption = absoluteSort ? 'Disable' : 'Enable';
                  const showColor = absoluteSort ? 'success' : 'debug';

                  return (
                    <Box key={column[fieldKey]} className={styles.item}>
                      <span className={styles.item_label}>{columnLabel}</span>
                      <ValueBasedToggleButton
                        name={column[fieldKey]}
                        size="small"
                        selected={absoluteSort}
                        disabled={false}
                        value={absoluteSort}
                        caption={showCaption}
                        xpath={column[fieldKey]}
                        color={showColor}
                        onClick={onAbsoluteSortToggle}
                      />
                    </Box>
                  );
                })}
              </>
            )}
            {tabIndex === 3 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
                  // Determine the toggle states and captions.
                  const frozen = column.frozenColumn ?? false;
                  const showCaption = frozen ? 'Unfreeze' : 'Freeze';
                  const showColor = frozen ? 'info' : 'debug';

                  return (
                    <Box key={column[fieldKey]} className={styles.item}>
                      <span className={styles.item_label}>{columnLabel}</span>
                      <ValueBasedToggleButton
                        name={column[fieldKey]}
                        size="small"
                        selected={frozen}
                        disabled={false}
                        value={frozen}
                        caption={showCaption}
                        xpath={column[fieldKey]}
                        color={showColor}
                        onClick={onFrozenToggle}
                      />
                    </Box>
                  );
                })}
              </>
            )}
            {tabIndex === 4 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
                  let helpText = column.help;
                  if (modelType === MODEL_TYPES.ABBREVIATION_MERGE) {
                    if (!helpText) {
                      helpText = '';
                    }
                    helpText += `${column.tableTitle} - ${helpText}`;
                  }

                  return (
                    <Box key={column[fieldKey]} className={styles.item_large}>
                      <span className={styles.item_label}>
                        {columnLabel}
                        <span style={{ margin: '0 10px' }}>
                          {helpText && (
                            <Tooltip title={helpText} disableInteractive>
                              <Help name="help" sx={{ cursor: 'pointer' }} color="info" fontSize="small" />
                            </Tooltip>
                          )}
                        </span>
                      </span>
                      <TextField
                        id={column[fieldKey]}
                        className={styles.text_field}
                        name={column[fieldKey]}
                        size="small"
                        value={columnNameOverrideDict[column[fieldKey]] || ''}
                        onChange={(e) => handleTextChange(e, column[fieldKey])}
                        onKeyDown={handleKeyDown}
                        onBlur={handleBlur}
                        variant="outlined"
                        inputProps={{
                          style: { padding: '6px 10px' },
                        }}
                        fullWidth
                        margin="dense"
                      />
                    </Box>
                  );
                })}
              </>
            )}
            {tabIndex === 5 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
                  const highlightState = highlightUpdateOverrideDict[column[fieldKey]] ?? HIGHLIGHT_STATES.NONE;

                  return (
                    <Box key={column[fieldKey]} className={styles.item_large}>
                      <span className={styles.item_label}>
                        {columnLabel}
                      </span>
                      <Select
                        size="small"
                        value={highlightState}
                        onChange={(e) => handleHighlightUpdateChange(column[fieldKey], e.target.value)}
                      >
                        {Object.keys(HIGHLIGHT_STATES).map((item, index) => (
                          <MenuItem key={index} value={HIGHLIGHT_STATES[item]} dense>
                            {HIGHLIGHT_STATES[item] === HIGHLIGHT_STATES.NONE &&
                              <span>{HIGHLIGHT_STATES.NONE}</span>}
                            {HIGHLIGHT_STATES[item] === HIGHLIGHT_STATES.CHANGE &&
                              <span style={{ color: 'var(--blue-info)' }}>{HIGHLIGHT_STATES.CHANGE}</span>}
                            {HIGHLIGHT_STATES[item] === HIGHLIGHT_STATES.HIGH_LOW && (
                              <>
                                <span style={{ color: 'var(--green-success)' }}>HIGH</span>
                                <span>/</span>
                                <span style={{ color: 'var(--red-error)' }}>LOW</span>
                              </>
                            )}
                          </MenuItem>
                        ))}
                      </Select>
                    </Box>
                  );
                })}
              </>
            )}
          </Box>
        </Box>
      </Popover>
    </>
  );
};

TableSettingsMenu.propTypes = {
  /** Array of column objects. Each column should include:
   * - key: string (unique identifier)
   * - sequenceNumber: number (default order)
   * - sourceIndex: number (used for filtering columns)
   * - hide: boolean (visibility flag)
   * - showLess: boolean (toggle for less/more display)
   */
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      sequenceNumber: PropTypes.number.isRequired,
      sourceIndex: PropTypes.number,
      hide: PropTypes.bool,
      showLess: PropTypes.bool,
      elaborateTitle: PropTypes.bool, // Added from usage
      tableTitle: PropTypes.string, // Added from usage (part of fieldKey logic)
      help: PropTypes.string, // Added from usage
      absoluteSort: PropTypes.bool, // Added from usage
      frozen: PropTypes.bool, // Added from usage
    })
  ).isRequired,
  /** Array of column order objects. Each should include:
   * - column_name: string
   * - sequence: number
   */
  columnOrders: PropTypes.arrayOf(
    PropTypes.shape({
      column_name: PropTypes.string.isRequired,
      sequence: PropTypes.number.isRequired,
    })
  ),
  /** Callback to toggle an individual column's visibility */
  onColumnToggle: PropTypes.func.isRequired,
  /** Callback to change an individual column's order.
   * Receives the new sequence (number) and the column key (string) as arguments.
   */
  onColumnOrdersChange: PropTypes.func.isRequired,
  /** Callback to toggle an individual column's "show less" state */
  onShowLessToggle: PropTypes.func.isRequired,
};

export default TableSettingsMenu;