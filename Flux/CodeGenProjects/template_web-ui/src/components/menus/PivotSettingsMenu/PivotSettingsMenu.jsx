import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { cloneDeep } from 'lodash';
import { Popover, FormControlLabel } from '@mui/material';
import { PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';
import { LAYOUT_TYPES } from '../../../constants';

/**
 * PivotSettingsMenu provides a popover menu for toggling pivot visibility,
 * ordering, and additional "more/less" options.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Array} props.pivots - Array of pivot objects. Each should include:
 *   - pivot_name: string (unique identifier)
 * @param {boolean} props.showAll - Flag indicating if all pivots are shown.
 * @param {function} props.onShowAllToggle - Callback when the showAll toggle is clicked.
 * @param {function} props.onPivotToggle - Callback when an individual pivot's visibility is toggled.
 *
 * @returns {JSX.Element} The rendered component.
 */
const PivotSettingsMenu = ({
  pivots,
  showAll,
  onShowAllToggle,
  onPivotToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  layout,
  pivotEnableOverride
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

  const menuName = 'pivot-settings';
  const isPopoverOpen = Boolean(anchorEl);
  const popoverId = isPopoverOpen ? `${menuName}-popover` : undefined;

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

  const handlePivotToggle = (e, xpath, key, value, ...rest) => {
    const isHidden = value;
    const updatedPivotEnableOverride = cloneDeep(pivotEnableOverride);
    if (isHidden) {
      if (!updatedPivotEnableOverride.includes(key)) {
        updatedPivotEnableOverride.push(key);
      }
    } else {
      const idx = updatedPivotEnableOverride.indexOf(key);
      if (idx !== -1) {
        updatedPivotEnableOverride.splice(idx, 1);
      }
    }
    if (onPivotToggle) {
      onPivotToggle(updatedPivotEnableOverride);
    }
  }

  if (layout !== LAYOUT_TYPES.PIVOT_TABLE) return null;

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
            label={'Show/Hide All'}
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
        </MenuItem>
        {pivots.map(({ pivot_name }) => {
          // Determine the toggle states and captions.
          const show = !pivotEnableOverride.includes(pivot_name);
          const showCaption = !show ? 'Show' : 'Hide';
          const showColor = show ? 'success' : 'debug';

          return (
            <MenuItem key={pivot_name} dense>
              <FormControlLabel
                sx={{ display: 'flex', flex: 1 }}
                size='small'
                label={pivot_name}
                control={
                  <ValueBasedToggleButton
                    name={pivot_name}
                    size='small'
                    selected={show}
                    disabled={false}
                    value={show}
                    caption={showCaption}
                    xpath={pivot_name}
                    color={showColor}
                    onClick={handlePivotToggle}
                  />
                }
              />
            </MenuItem>
          );
        })}
      </Popover>
    </>
  );
};

PivotSettingsMenu.propTypes = {
  /** Array of pivot objects. Each pivot should include:
   * - pivot_name: string (unique identifier)
   */
  pivots: PropTypes.arrayOf(
    PropTypes.shape({
      pivot_name: PropTypes.string.isRequired,
    })
  ).isRequired,
  /** Flag indicating if all pivots are shown */
  showAll: PropTypes.bool.isRequired,
  /** Callback to toggle the showAll state */
  onShowAllToggle: PropTypes.func.isRequired,
  /** Callback to toggle an individual pivot's visibility */
  onPivotToggle: PropTypes.func,
};

export default PivotSettingsMenu;