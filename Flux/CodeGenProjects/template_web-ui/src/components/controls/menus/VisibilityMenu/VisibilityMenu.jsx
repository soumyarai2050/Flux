import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Popover, FormControlLabel, Checkbox } from '@mui/material';
import { Visibility, PushPin, PushPinOutlined } from '@mui/icons-material';
import Icon from '../../../ui/Icon';
import MenuItem from '../../../ui/MenuItem';


/**
 * VisibilityMenu renders an icon that, when clicked, opens a popover allowing
 * users to toggle the visibility of additional fields via checkboxes.
 * The icon's color changes based on the current state of `showMore` and `showHidden`.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {boolean} props.showMore - Indicates whether the 'Show More' option is active.
 * @param {boolean} props.showHidden - Indicates whether the 'Show Hidden' option is active.
 * @param {function} props.onVisibilityMenuClick - Callback invoked on single click.
 *   Receives a boolean (result of `showMore || showHidden`) as an argument.
 * @param {function} props.onVisibilityMenuDoubleClick - Callback invoked on double click.
 *   Receives a boolean (result of `showMore || showHidden`) as an argument.
 * @param {function} props.onShowHiddenToggle - Callback invoked when the 'Show hidden fields' checkbox is toggled.
 * @param {function} props.onShowMoreToggle - Callback invoked when the 'Show More' checkbox is toggled.
 *
 * @returns {JSX.Element} The rendered VisibilityMenu component.
 */
const VisibilityMenu = ({
  showMore,
  showHidden,
  onVisibilityMenuClick,
  onVisibilityMenuDoubleClick,
  onShowHiddenToggle,
  onShowMoreToggle,
  isPinned,
  onPinToggle,
  menuType,
  onMenuClose
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

  const visibilityColor = showMore && showHidden ? 'success' : showMore ? 'warning' : 'inherit';
  const menuName = 'visibility';
  const isPopoverOpen = Boolean(anchorEl);
  const popoverId = isPopoverOpen ? `${menuName}-popover` : undefined;

  const handlePopoverOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    onMenuClose();
    setAnchorEl(null);
  };

  const handleClick = () => {
    if (onVisibilityMenuClick) {
      onVisibilityMenuClick(showMore || showHidden);
    }
  };

  const handleDoubleClick = () => {
    if (onVisibilityMenuDoubleClick) {
      onVisibilityMenuDoubleClick(showMore || showHidden);
    }
  };

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleClick} onDoubleClick={handleDoubleClick}>
            <span>
              <Visibility sx={{ marginRight: '5px' }} fontSize='small' color={visibilityColor} />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon
            name={menuName}
            title={menuName}
            onClick={handleClick}
            onDoubleClick={handleDoubleClick}
          >
            <Visibility fontSize='small' color={visibilityColor === 'inherit' ? 'white' : visibilityColor} />
          </Icon>
        );
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
            size='small'
            label='Show hidden fields'
            control={
              <Checkbox
                size='small'
                checked={showHidden}
                onChange={onShowHiddenToggle}
              />
            }
          />
        </MenuItem>
        <MenuItem dense>
          <FormControlLabel
            size='small'
            label='Show More'
            control={
              <Checkbox
                size='small'
                checked={showMore}
                onChange={onShowMoreToggle}
              />
            }
          />
        </MenuItem>
      </Popover>
    </>
  );
};

VisibilityMenu.propTypes = {
  /** Indicates whether the 'Show More' option is active. */
  showMore: PropTypes.bool.isRequired,
  /** Indicates whether the 'Show Hidden' option is active. */
  showHidden: PropTypes.bool.isRequired,
  /** Callback invoked on single click; receives (showMore || showHidden) as an argument. */
  onVisibilityMenuClick: PropTypes.func.isRequired,
  /** Callback invoked on double click; receives (showMore || showHidden) as an argument. */
  onVisibilityMenuDoubleClick: PropTypes.func.isRequired,
  /** Callback invoked when toggling the 'Show hidden fields' checkbox. */
  onShowHiddenToggle: PropTypes.func.isRequired,
  /** Callback invoked when toggling the 'Show More' checkbox. */
  onShowMoreToggle: PropTypes.func.isRequired,
};

export default VisibilityMenu;