import React from 'react';
import PropTypes from 'prop-types';
import { Edit, Save, PushPin, PushPinOutlined } from '@mui/icons-material';
import { MODES } from '../../../constants';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';

/**
 * EditSaveToggleMenu renders an icon that toggles between edit and save modes.
 * It displays the edit icon when in READ_MODE, and the save icon otherwise.
 * Clicking the icon invokes the onModeToggle callback.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {string} props.mode - The current mode, expected to be one of the MODES constants.
 * @param {function} props.onModeToggle - Callback function triggered when the icon is clicked.
 * @returns {JSX.Element|null} The rendered component or null if onModeToggle is not provided.
 */
const EditSaveToggleMenu = ({
  mode,
  onModeToggle,
  onSave,
  isPinned,
  onPinToggle,
  menuType
}) => {
  if (!onModeToggle) return null;

  const menuBaseName = 'edit-save';
  const menuName = mode === MODES.READ ? 'edit' : 'save';
  const IconComponent = mode === MODES.READ ? Edit : Save;

  const handleClick = () => {
    if (mode === MODES.READ) {
      onModeToggle();
    } else {
      onSave();
    }
  }

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuBaseName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleClick}>
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
          <Icon name={menuName} title={menuName} onClick={handleClick}>
            <IconComponent fontSize='small' />
          </Icon>
        );
    }
  }

  return renderMenu();
};

EditSaveToggleMenu.propTypes = {
  /** The current mode; expected to match one of the MODES constants. */
  mode: PropTypes.string.isRequired,
  /** Callback function to toggle between edit and save modes. */
  onModeToggle: PropTypes.func.isRequired,
};

export default EditSaveToggleMenu;