import React from 'react';
import PropTypes from 'prop-types';
import { Refresh, PushPin, PushPinOutlined } from '@mui/icons-material';
import Icon from '../../../ui/Icon';
import MenuItem from '../../../ui/MenuItem';

/**
 * ReloadMenu renders a clickable icon that triggers a reload action.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Function} props.onReload - Callback function invoked when the reload icon is clicked.
 * @returns {JSX.Element} The rendered ReloadMenu component.
 */
const ReloadMenu = ({
  onReload,
  isPinned,
  onPinToggle,
  menuType,
  onMenuClose
}) => {
  const menuName = 'reload';

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const handleReload = () => {
    onMenuClose();
    onReload();
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleReload}>
            <span>
              <Refresh sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handleReload}>
            <Refresh fontSize='small' color='white' />
          </Icon>
        );
    }
  }
  return renderMenu();
};

ReloadMenu.propTypes = {
  /** Callback invoked when the reload icon is clicked. */
  onReload: PropTypes.func.isRequired,
};

export default ReloadMenu;