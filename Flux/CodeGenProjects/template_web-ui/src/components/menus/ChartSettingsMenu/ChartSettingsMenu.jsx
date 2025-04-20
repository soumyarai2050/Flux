import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { cloneDeep, debounce } from 'lodash';
import { Box, Popover, TextField } from '@mui/material';
import { PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';
import { LAYOUT_TYPES } from '../../../constants';
import styles from './ChartSettingsMenu.module.css';

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
  // showAll,
  // onShowAllToggle,
  onChartToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  layout,
  chartEnableOverride
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [searchValue, setSearchValue] = useState('');
  const [filteredCharts, setFilteredCharts] = useState(charts);

  useEffect(() => {
    if (searchValue) {
      const lowerCasedValue = searchValue.toLowerCase();
      const updatedCharts = charts.filter((chart) => chart.chart_name.toLowerCase().includes(lowerCasedValue));
      setFilteredCharts(updatedCharts);
    } else {
      setFilteredCharts(charts);
    }
  }, [charts])

  const debouncedTransform = useRef(
    debounce((value) => {
      if (value) {
        const lowerCasedValue = value.toLowerCase();
        const updatedCharts = charts.filter((chart) => chart.chart_name.toLowerCase().includes(lowerCasedValue));
        setFilteredCharts(updatedCharts);
      } else {
        setFilteredCharts(charts);
      }
    }, 300)
  ).current;

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
        <Box className={styles.content}>
          {charts.length > 5 && (
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
          {filteredCharts.map(({ chart_name }) => {
            // Determine the toggle states and captions.
            const show = !chartEnableOverride.includes(chart_name);
            const showCaption = !show ? 'Show' : 'Hide';
            const showColor = show ? 'success' : 'debug';

            return (
              <Box key={chart_name} className={styles.item}>
                <span className={styles.item_label}>{chart_name}</span>
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
              </Box>
            )
          })}
        </Box>
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
  onChartToggle: PropTypes.func,
};

export default ChartSettingsMenu;