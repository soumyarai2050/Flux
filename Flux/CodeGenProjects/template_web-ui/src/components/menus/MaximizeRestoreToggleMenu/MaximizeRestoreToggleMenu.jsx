import React from 'react';
import PropTypes from 'prop-types';
import { CloseFullscreen, Fullscreen, PushPin, PushPinOutlined } from '@mui/icons-material';
import MenuItem from '../../MenuItem';
import Icon from '../../Icon';

/**
 * MaximizeRestoreToggleMenu renders an icon that toggles between a maximized and restored state.
 * When `isMaximized` is true, it shows the restore icon, otherwise it shows the maximize icon.
 * Clicking the icon triggers the `onMaximizeToggle` callback.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {boolean} props.isMaximized - Indicates if the view is currently maximized.
 * @param {function} props.onMaximizeToggle - Callback function triggered when the toggle icon is clicked.
 * @returns {JSX.Element} The rendered MaximizeRestoreToggleMenu component.
 */
const MaximizeRestoreToggleMenu = ({
  isMaximized,
  onMaximizeToggle,
  isPinned,
  onPinToggle,
  menuType
}) => {
  const menuBaseName = 'maximize-restore';
  const menuName = isMaximized ? 'restore' : 'maximize';
  const IconComponent = isMaximized ? CloseFullscreen : Fullscreen;

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuBaseName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={onMaximizeToggle}>
            <span>
              <IconComponent sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={onMaximizeToggle}>
            <IconComponent fontSize='small' />
          </Icon>
        );
    }
  }

  return renderMenu();
};

MaximizeRestoreToggleMenu.propTypes = {
  /** Indicates if the view is currently maximized. */
  isMaximized: PropTypes.bool.isRequired,
  /** Callback triggered when the toggle icon is clicked. */
  onMaximizeToggle: PropTypes.func.isRequired,
};

export default MaximizeRestoreToggleMenu;