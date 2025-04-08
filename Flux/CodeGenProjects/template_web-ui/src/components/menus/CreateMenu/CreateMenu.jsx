import React from 'react';
import PropTypes from 'prop-types';
import { Add, PushPin, PushPinOutlined } from '@mui/icons-material';
import { MODES } from '../../../constants';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';


/**
 * CreateMenu renders a clickable icon that triggers the creation action.
 * The menu is only visible when the application is in READ_MODE.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {string} props.mode - The current mode (should match MODES.READ to be visible).
 * @param {function} props.onCreate - Callback function invoked when the menu is clicked.
 * @returns {JSX.Element|null} The rendered CreateMenu component or null if not in READ_MODE.
 */
const CreateMenu = ({
  mode,
  onCreate,
  isPinned,
  onPinToggle,
  menuType,
  isAbbreviationSource,
  onMenuClose
}) => {
  if (mode !== MODES.READ || isAbbreviationSource) return null;

  const menuName = 'create';

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const handleCreate = () => {
    onMenuClose();
    onCreate();
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleCreate}>
            <span>
              <Add sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handleCreate}>
            <Add fontSize='small' />
          </Icon>
        );
    }
  }

  return renderMenu();
};

CreateMenu.propTypes = {
  /** The current mode. Component is rendered only if this equals MODES.READ. */
  mode: PropTypes.string.isRequired,
  /** Callback function triggered when the create icon is clicked. */
  onCreate: PropTypes.func.isRequired,
};

export default CreateMenu;