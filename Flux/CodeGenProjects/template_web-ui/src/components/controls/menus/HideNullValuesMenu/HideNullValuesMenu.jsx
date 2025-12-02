import React from 'react';
import PropTypes from 'prop-types';
import EyeOff from '@mui/icons-material/VisibilityOff';
import Eye from '@mui/icons-material/Visibility';
import PushPin from '@mui/icons-material/PushPin';
import PushPinOutlined from '@mui/icons-material/PushPinOutlined';
import MenuItem from '../../../ui/MenuItem';
import Icon from '../../../ui/Icon';

/**
 * HideNullValuesMenu renders a toggle to hide/show null and unset values in tree layout.
 * When `hideNullValues` is true, it shows the eye-off icon, otherwise it shows the eye icon.
 * Clicking the icon triggers the `onHideNullValuesToggle` callback.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {boolean} props.hideNullValues - Indicates if null/unset values are currently hidden.
 * @param {function} props.onHideNullValuesToggle - Callback function triggered when the toggle icon is clicked.
 * @param {boolean} props.isPinned - Indicates if the menu is pinned.
 * @param {function} props.onPinToggle - Callback function for pin toggle.
 * @param {string} props.menuType - Type of menu rendering ('item' or 'icon').
 * @param {function} props.onMenuClose - Callback function to close the menu.
 * @returns {JSX.Element} The rendered HideNullValuesMenu component.
 */
const HideNullValuesMenu = ({
  hideNullValues,
  onHideNullValuesToggle,
  isPinned,
  onPinToggle,
  menuType,
  onMenuClose
}) => {
  const menuBaseName = 'hide-nulls';
  const menuName = hideNullValues ? 'show-nulls' : 'hide-nulls';
  const IconComponent = hideNullValues ? Eye : EyeOff;

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuBaseName, !isPinned);
  }

  const handleToggle = () => {
    onMenuClose();
    onHideNullValuesToggle(!hideNullValues);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinComponent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleToggle}>
            <span>
              <IconComponent sx={{ marginRight: '5px' }} fontSize='small' />
              {hideNullValues ? 'Show Nulls ' : 'Hide Nulls'}
            </span>
            {<PinComponent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handleToggle}>
            <IconComponent fontSize='small' color='white' />
          </Icon>
        );
    }
  }

  return renderMenu();
};

HideNullValuesMenu.propTypes = {
  /** Indicates if null/unset values are currently hidden. */
  hideNullValues: PropTypes.bool.isRequired,
  /** Callback triggered when the toggle icon is clicked. */
  onHideNullValuesToggle: PropTypes.func.isRequired,
  /** Indicates if the menu is pinned. */
  isPinned: PropTypes.bool.isRequired,
  /** Callback for pin toggle. */
  onPinToggle: PropTypes.func.isRequired,
  /** Type of menu rendering. */
  menuType: PropTypes.string.isRequired,
  /** Callback to close the menu. */
  onMenuClose: PropTypes.func.isRequired,
};

export default HideNullValuesMenu;