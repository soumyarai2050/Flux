import React from 'react';
import PropTypes from 'prop-types';
import { Edit, Save, Close, PushPin, PushPinOutlined } from '@mui/icons-material';
import { MODES } from '../../../constants';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';

/**
 * EditSaveToggleMenu renders an icon that toggles between edit and save modes.
 * In READ mode, it displays the edit icon.
 * In EDIT mode, it displays both save and discard (red cross) icons.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {string} props.mode - The current mode, expected to be one of the MODES constants.
 * @param {function} props.onModeToggle - Callback function triggered when edit icon is clicked.
 * @param {function} props.onSave - Callback function triggered when save icon is clicked.
 * @param {function} props.onDiscard - Callback function triggered when discard icon is clicked.
 * @returns {JSX.Element|null} The rendered component or null if onModeToggle is not provided.
 */
const EditSaveToggleMenu = ({
  mode,
  onModeToggle,
  onSave,
  onDiscard,
  isPinned,
  onPinToggle,
  menuType,
  disabled,
  onMenuClose
}) => {
  if (!onModeToggle || disabled) return null;

  const menuBaseName = 'edit-save';

  const handleEditClick = () => {
    onMenuClose();
    onModeToggle();
  }

  const handleSaveClick = () => {
    onMenuClose();
    onSave();
  }

  const handleDiscardClick = () => {
    onMenuClose();
    onDiscard();
  }

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuBaseName, !isPinned);
  }

  const renderMenu = () => {
    if (mode === MODES.READ) {
      // Show only edit icon in read mode
      switch (menuType) {
        case 'item':
          const PinComponent = isPinned ? PushPin : PushPinOutlined;
          return (
            <MenuItem name="edit" onClick={handleEditClick}>
              <span>
                <Edit sx={{ marginRight: '5px' }} fontSize='small' />
                edit
              </span>
              {<PinComponent onClick={handlePinToggle} fontSize='small' />}
            </MenuItem>
          );
        case 'icon':
        default:
          return (
            <Icon name="edit" title="edit" onClick={handleEditClick}>
              <Edit fontSize='small' color='white' />
            </Icon>
          );
      }
    } else {
      // Show both save (green tick) and discard (red cross) icons in edit mode
      switch (menuType) {
        case 'item':
          const PinComponent = isPinned ? PushPin : PushPinOutlined;
          return (
            <>
              <MenuItem name="save" onClick={handleSaveClick}>
                <span>
                  <Save sx={{ marginRight: '5px' }} fontSize='small' color='success' />
                  save
                </span>
                {/* {<PinComponent onClick={handlePinToggle} fontSize='small' />} */}
              </MenuItem>
              <MenuItem name="discard" onClick={handleDiscardClick}>
                <span>
                  <Close sx={{ marginRight: '5px' }} fontSize='small' color='error' />
                  discard
                </span>
              </MenuItem>
            </>
          );
        case 'icon':
        default:
          return (
            <>
              <Icon name="save" title="save" onClick={handleSaveClick}>
                <Save fontSize='small' color='success' />
              </Icon>
              <Icon name="discard" title="discard" onClick={handleDiscardClick}>
                <Close fontSize='small' color='error' />
              </Icon>
            </>
          );
      }
    }
  }

  return renderMenu();
};

EditSaveToggleMenu.propTypes = {
  /** The current mode; expected to match one of the MODES constants. */
  mode: PropTypes.string.isRequired,
  /** Callback function to toggle between edit and save modes. */
  onModeToggle: PropTypes.func.isRequired,
  /** Callback function to save changes. */
  onSave: PropTypes.func.isRequired,
  /** Callback function to discard changes. */
  onDiscard: PropTypes.func,
};

export default EditSaveToggleMenu;