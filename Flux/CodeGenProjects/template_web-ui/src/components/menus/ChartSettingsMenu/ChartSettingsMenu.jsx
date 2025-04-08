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
 * ChartSettingsMenu provides a popover menu for toggling chart visibility,
 * ordering, and additional "more/less" options.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Array} props.charts - Array of chart objects. Each should include:
 *   - chart_name: string (unique identifier)
 * @param {boolean} props.showAll - Flag indicating if all charts are shown.
 * @param {function} props.onShowAllToggle - Callback when the showAll toggle is clicked.
 * @param {function} props.onChartToggle - Callback when an individual chart's visibility is toggled.
 *
 * @returns {JSX.Element} The rendered component.
 */
const ChartSettingsMenu = ({
  charts,
  showAll,
  onShowAllToggle,
  onChartToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  layout,
  chartEnableOverride
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

  const menuName = 'chart-settings';
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

  const handleChartToggle = (e, xpath, key, value, ...rest) => {
    const isHidden = value;
    const updatedChartEnableOverride = cloneDeep(chartEnableOverride);
    if (isHidden) {
      if (!updatedChartEnableOverride.includes(key)) {
        updatedChartEnableOverride.push(key);
      }
    } else {
      const idx = updatedChartEnableOverride.indexOf(key);
      if (idx !== -1) {
        updatedChartEnableOverride.splice(idx, 1);
      }
    }
    if (onChartToggle) {
      onChartToggle(updatedChartEnableOverride);
    }
  }

  if (layout !== LAYOUT_TYPES.CHART) return null;

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
        {charts.map(({ chart_name }) => {
          // Determine the toggle states and captions.
          const show = !chartEnableOverride.includes(chart_name);
          const showCaption = !show ? 'Show' : 'Hide';
          const showColor = show ? 'success' : 'debug';

          return (
            <MenuItem key={chart_name} dense>
              <FormControlLabel
                sx={{ display: 'flex', flex: 1 }}
                size='small'
                label={chart_name}
                control={
                  <ValueBasedToggleButton
                    name={chart_name}
                    size='small'
                    selected={show}
                    disabled={false}
                    value={show}
                    caption={showCaption}
                    xpath={chart_name}
                    color={showColor}
                    onClick={handleChartToggle}
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

ChartSettingsMenu.propTypes = {
  /** Array of chart objects. Each chart should include:
   * - chart_name: string (unique identifier)
   */
  charts: PropTypes.arrayOf(
    PropTypes.shape({
      chart_name: PropTypes.string.isRequired,
    })
  ).isRequired,
  /** Flag indicating if all charts are shown */
  showAll: PropTypes.bool.isRequired,
  /** Callback to toggle the showAll state */
  onShowAllToggle: PropTypes.func.isRequired,
  /** Callback to toggle an individual chart's visibility */
  onChartToggle: PropTypes.func.isRequired,
};

export default ChartSettingsMenu;