import React, { useEffect, useMemo, useRef, useState } from 'react';
import { debounce } from 'lodash';
import PropTypes from 'prop-types';
import { Popover, Select, Box, Tabs, Tab, TextField } from '@mui/material';
import { PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';
import { LAYOUT_TYPES, MODEL_TYPES } from '../../../constants';
import styles from './ColumnSettingsMenu.module.css';

/**
 * ColumnSettingsMenu provides a popover menu for toggling column visibility,
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
 * @param {boolean} props.showAll - Flag indicating if all columns are shown.
 * @param {boolean} props.moreAll - Flag indicating if the "more" option is active for all columns.
 * @param {function} props.onShowAllToggle - Callback when the showAll toggle is clicked.
 * @param {function} props.onMoreAllToggle - Callback when the moreAll toggle is clicked.
 * @param {function} props.onColumnToggle - Callback when an individual column's visibility is toggled.
 * @param {function} props.onColumnOrdersChange - Callback when an individual column's order is changed.
 *   Receives the new sequence (number) and the column key (string) as arguments.
 * @param {function} props.onShowLessToggle - Callback when an individual column's "show less" toggle is clicked.
 *
 * @returns {JSX.Element} The rendered component.
 */
const ColumnSettingsMenu = ({
  columns,
  columnOrders,
  // showAll,
  // moreAll,
  // onShowAllToggle,
  // onMoreAllToggle,
  onColumnToggle,
  onColumnOrdersChange,
  onShowLessToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  modelType,
  layout,
  onAbsoluteSortToggle
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [tabIndex, setTabIndex] = useState(0);
  const [searchValue, setSearchValue] = useState('');
  const [filteredColumns, setFilteredColumns] = useState(columns);

  const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';

  useEffect(() => {
    if (searchValue) {
      const lowerCasedValue = searchValue.toLowerCase();
      const updatedColumns = columns.filter((column) => column[fieldKey].toLowerCase().includes(lowerCasedValue));
      setFilteredColumns(updatedColumns);
    } else {
      setFilteredColumns(columns);
    }
  }, [columns])

  const debouncedTransform = useRef(
    debounce((value) => {
      if (value) {
        const lowerCasedValue = value.toLowerCase();
        const updatedColumns = columns.filter((column) => column[fieldKey].toLowerCase().includes(lowerCasedValue));
        setFilteredColumns(updatedColumns);
      } else {
        setFilteredColumns(columns);
      }
    }, 300)
  ).current;

  const menuName = 'column-settings';
  const isPopoverOpen = Boolean(anchorEl);
  const popoverId = isPopoverOpen ? `${menuName}-popover` : undefined;

  // Determine the maximum sequence number among columns for ordering purposes.
  const maxSequence = useMemo(
    () => Math.max(...columns.map((column) => column.sequenceNumber)),
    [columns]
  );

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
  }

  const handleSearchValueChange = (e) => {
    setSearchValue(e.target.value);
    debouncedTransform(e.target.value);
  }

  const handleKeyDown = (e) => {
    if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  }

  if (![LAYOUT_TYPES.TABLE, LAYOUT_TYPES.ABBREVIATION_MERGE, LAYOUT_TYPES.PIVOT_TABLE].includes(layout)) return null;

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handlePopoverOpen}>
            <span>
              <Settings sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        )
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handlePopoverOpen}>
            <Settings fontSize='small' />
          </Icon>
        )
    }
  }

  return (
    <>
      {renderMenu()}
      <Popover
        id={popoverId}
        open={isPopoverOpen}
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center'
        }}
        onClose={handlePopoverClose}
      >
        <Box sx={{ display: 'flex', width: 400, maxHeight: 600 }}>
          <Tabs
            orientation='vertical'
            value={tabIndex}
            onChange={(e, newValue) => setTabIndex(newValue)}
            sx={{ borderRight: 1, borderColor: 'divider', minWidth: 100 }}
          >
            <Tab label='Show/More' />
            <Tab label='Sequence' />
            <Tab label='Absolute Sort' />
          </Tabs>
          {/* Tab Content */}
          <Box className={styles.content}>
            {columns.length > 5 && (
              <TextField
                size='small'
                label='Column Name'
                value={searchValue}
                onChange={handleSearchValueChange}
                onKeyDown={handleKeyDown}
                autoFocus
                inputProps={{
                  style: { padding: '6px 10px' }
                }}
              />
            )}
            {tabIndex === 0 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;

                  // Determine the toggle states and captions.
                  const show = !column.hide;
                  const showCaption = column.hide ? 'Show' : 'Hide';
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
                        size='small'
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
                        size='small'
                        selected={more}
                        disabled={moreDisabled}
                        value={more}
                        caption={moreCaption}
                        xpath={column[fieldKey]}
                        color={moreColor}
                        onClick={onShowLessToggle}
                      />
                    </Box>
                  )
                })}
              </>
            )}
            {tabIndex === 1 && (
              <>
                {filteredColumns.map((column) => {
                  // Only render columns with a sourceIndex of 0.
                  if (column.sourceIndex !== 0) return null;

                  // Determine the column's order.
                  let sequence = column.sequenceNumber;
                  const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
                  if (columnOrders) {
                    const columnOrder = columnOrders.find(
                      (o) => o.column_name === column[fieldKey]
                    );
                    if (columnOrder) {
                      sequence = columnOrder.sequence;
                    }
                  }

                  return (
                    <Box key={column[fieldKey]} className={styles.item}>
                      <span className={styles.item_label}>{columnLabel}</span>
                      <Select
                        size='small'
                        value={sequence}
                        onChange={(e) =>
                          onColumnOrdersChange(column[fieldKey], parseInt(e.target.value, 10))
                        }
                      >
                        {[...Array(maxSequence).keys()].map((_, index) => (
                          <MenuItem key={index} value={index + 1} dense>
                            {index + 1}
                          </MenuItem>
                        ))}
                      </Select>
                    </Box>
                  )
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
                        size='small'
                        selected={absoluteSort}
                        disabled={false}
                        value={absoluteSort}
                        caption={showCaption}
                        xpath={column[fieldKey]}
                        color={showColor}
                        onClick={onAbsoluteSortToggle}
                      />
                    </Box>
                  )
                })}
              </>
            )}
          </Box>
        </Box>
      </Popover>
    </>
  );
};

ColumnSettingsMenu.propTypes = {
  /** Array of column objects. Each column should include:
   * - key: string (unique identifier)
   * - sequenceNumber: number (default order)
   * - sourceIndex: number (used for filtering)
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
  /** Flag indicating if all columns are shown */
  showAll: PropTypes.bool.isRequired,
  /** Flag indicating if the "more" option is active for all columns */
  moreAll: PropTypes.bool.isRequired,
  /** Callback to toggle the showAll state */
  onShowAllToggle: PropTypes.func.isRequired,
  /** Callback to toggle the moreAll state */
  onMoreAllToggle: PropTypes.func.isRequired,
  /** Callback to toggle an individual column's visibility */
  onColumnToggle: PropTypes.func.isRequired,
  /** Callback to change an individual column's order.
   * Receives the new sequence (number) and the column key (string) as arguments.
   */
  onColumnOrdersChange: PropTypes.func.isRequired,
  /** Callback to toggle an individual column's "show less" state */
  onShowLessToggle: PropTypes.func.isRequired,
};

export default ColumnSettingsMenu;