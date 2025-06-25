import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { cloneDeep, debounce } from 'lodash';
import { Box, Popover, TextField } from '@mui/material';
import { PushPin, PushPinOutlined, Settings } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
import ValueBasedToggleButton from '../../ValueBasedToggleButton';
import { LAYOUT_TYPES } from '../../../constants';
import styles from './PivotSettingsMenu.module.css';

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
  // showAll,
  // onShowAllToggle,
  onPivotToggle,
  menuType,
  isPinned,
  onMenuClose,
  onPinToggle,
  layout,
  pivotEnableOverride
}) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [searchValue, setSearchValue] = useState('');
  const [filteredPivots, setFilteredPivots] = useState(pivots);

  useEffect(() => {
    if (searchValue) {
      const lowerCasedValue = searchValue.toLowerCase();
      const updatedPivots = pivots.filter((pivot) => pivot.pivot_name.toLowerCase().includes(lowerCasedValue));
      setFilteredPivots(updatedPivots);
    } else {
      setFilteredPivots(pivots);
    }
  }, [pivots])

  const debouncedTransform = useRef(
    debounce((value) => {
      if (value) {
        const lowerCasedValue = value.toLowerCase();
        const updatedPivots = pivots.filter((pivot) => pivot.pivot_name.toLowerCase().includes(lowerCasedValue));
        setFilteredPivots(updatedPivots);
      } else {
        setFilteredPivots(pivots);
      }
    }, 300)
  ).current;

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
            <Settings fontSize='small' color='white' />
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
          {pivots.length > 5 && (
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
          {filteredPivots.map(({ pivot_name }) => {
            // Determine the toggle states and captions.
            const show = !pivotEnableOverride.includes(pivot_name);
            const showCaption = !show ? 'Show' : 'Hide';
            const showColor = show ? 'success' : 'debug';

            return (
              <Box key={pivot_name} className={styles.item}>
                <span className={styles.item_label}>{pivot_name}</span>
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
              </Box>
            )
          })}
        </Box>
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