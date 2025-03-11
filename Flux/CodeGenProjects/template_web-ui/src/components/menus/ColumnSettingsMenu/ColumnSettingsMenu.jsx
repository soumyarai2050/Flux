import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Popover, FormControlLabel, Select } from '@mui/material';
import { PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';
import { LAYOUT_TYPES, MODEL_TYPES } from '../../../constants';
// import styles from './ColumnSettingsMenu.module.css'; // Uncomment if you plan to use the styles

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
  showAll,
  moreAll,
  onShowAllToggle,
  onMoreAllToggle,
  onColumnToggle,
  onColumnOrdersChange,
  onShowLessToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  modelType,
  layout
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

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
    setAnchorEl(null);
    onMenuClose();
  };

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  if (![LAYOUT_TYPES.TABLE, LAYOUT_TYPES.ABBREVIATION_MERGE].includes(layout)) return null;

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
        <MenuItem dense>
          <FormControlLabel
            sx={{ display: 'flex', flex: 1 }}
            size='small'
            control={
              <ValueBasedToggleButton
                name='HideShowAll'
                size='small'
                selected={showAll}
                value={showAll}
                caption={showAll ? 'Show Default' : 'Show All'}
                xpath='HideShowAll'
                color={showAll ? 'debug' : 'success'}
                onClick={onShowAllToggle}
              />
            }
          />
          <ValueBasedToggleButton
            name='MoreLessAll'
            size='small'
            selected={moreAll}
            value={moreAll}
            caption={moreAll ? 'More Default' : 'More All'}
            xpath='MoreLessAll'
            color={moreAll ? 'debug' : 'info'}
            onClick={onMoreAllToggle}
          />
        </MenuItem>
        {columns.map((column) => {
          // Only render columns with a sourceIndex of 0.
          if (column.sourceIndex !== 0) return null;

          // Determine the column's order.
          let sequence = column.sequenceNumber;
          const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
          const columnLabel = column.elaborateTitle ? column[fieldKey] : column.key;
          if (columnOrders) {
            const columnOrder = columnOrders.find(
              (o) => o.column_name === column[fieldKey]
            );
            if (columnOrder) {
              sequence = columnOrder.sequence;
            }
          }

          // Determine the toggle states and captions.
          const show = !column.hide;
          const showCaption = column.hide ? 'Show' : 'Hide';
          const showColor = show ? 'success' : 'debug';
          const more = !column.showLess;
          const moreDisabled = column.hide;
          const moreCaption = more ? 'Less' : 'More';
          const moreColor = more ? 'info' : 'debug';

          return (
            <MenuItem key={column[fieldKey]} dense>
              <FormControlLabel
                sx={{ display: 'flex', flex: 1 }}
                size='small'
                label={columnLabel}
                control={
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
                }
              />
              <Select
                size='small'
                value={sequence}
                onChange={(e) =>
                  onColumnOrdersChange(column[fieldKey], parseInt(e.target.value, 10))
                }
              >
                {[...Array(maxSequence).keys()].map((_, index) => (
                  <MenuItem key={index} value={index + 1}>
                    {index + 1}
                  </MenuItem>
                ))}
              </Select>
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
            </MenuItem>
          );
        })}
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