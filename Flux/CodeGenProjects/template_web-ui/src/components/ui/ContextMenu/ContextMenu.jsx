import React, { useState } from 'react';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import EditIcon from '@mui/icons-material/Edit';
import ClearAll from '@mui/icons-material/ClearAll';

/**
 * ContextMenu Component - Right-click context menu for selective bulk patching
 *
 * Props:
 * - selectedRows: Array of selected row IDs
 * - availableButtons: Object mapping button names to their data:
 *    {
 *      buttonName: {
 *        count: number,
 *        action: string,
 *        isDisabled: boolean,
 *        cellMetadata: object,
 *        affectedRowIds: array
 *      }
 *    }
 * - onSelectiveButtonPatch: Callback function when a button patch is clicked
 *    Called with: (selectedRows, buttonType)
 * - onClearSelection: Callback function when "Clear Selection" is clicked
 * - anchorEl: Object with {clientX, clientY} for positioning
 * - open: Whether the menu is open
 * - onClose: Callback when menu closes
 * - isLoading: Boolean indicating if table is loading
 */
const ContextMenu = ({
  selectedRows = [],
  availableButtons = {},
  onSelectiveButtonPatch,
  onClearSelection,
  anchorEl,
  open,
  onClose,
  isLoading = false
}) => {
  const [isPatching, setIsPatching] = useState(false);

  const handleButtonPatchClick = async (buttonType) => {
    if (!onSelectiveButtonPatch || isPatching) return;

    try {
      setIsPatching(true);
      onClose();
      await onSelectiveButtonPatch(selectedRows, buttonType);
    } catch (error) {
      console.error(`Error during button patch for ${buttonType}:`, error);
    } finally {
      setIsPatching(false);
    }
  };

  const handleClearSelectionClick = () => {
    onClose();
    if (onClearSelection) {
      onClearSelection();
    }
  };

  const buttonCount = Object.keys(availableButtons).length;
  const hasButtons = buttonCount > 0;

  // Determine if we should show the menu (1+ rows selected and has buttons)
  const shouldShow = open && selectedRows.length >= 1;

  // Build menu items as array to avoid Fragment issues with MUI Menu
  const menuItems = [];

  if (hasButtons) {
    // Add dynamic button items
    Object.entries(availableButtons).forEach(([buttonType, buttonData]) => {
      menuItems.push(
        <MenuItem
          key={buttonType}
          onClick={() => handleButtonPatchClick(buttonData.tableTitle)}
          disabled={
            isPatching ||
            isLoading ||
            buttonData.isDisabled === true
          }
          title={buttonData.isDisabled ? 'This button is disabled in the schema' : ''}
        >
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            {buttonData.displayName || buttonType} ({buttonData.count})
          </ListItemText>
        </MenuItem>
      );
    });

    // Add divider before clear selection
    menuItems.push(<Divider key="divider" sx={{ my: 0.5 }} />);
  } else {
    // No buttons available message
    menuItems.push(
      <MenuItem key="no-buttons" disabled>
        <ListItemText>
          No button actions available
        </ListItemText>
      </MenuItem>
    );
  }

  // Always add clear selection option
  menuItems.push(
    <MenuItem
      key="clear-selection"
      onClick={handleClearSelectionClick}
      disabled={isPatching || isLoading}
    >
      <ListItemIcon>
        <ClearAll fontSize="small" />
      </ListItemIcon>
      <ListItemText>
        Clear Selection
      </ListItemText>
    </MenuItem>
  );

  return (
    <Menu
      anchorEl={null}
      anchorPosition={
        anchorEl && shouldShow
          ? { top: anchorEl.clientY, left: anchorEl.clientX }
          : undefined
      }
      anchorReference={anchorEl && shouldShow ? 'anchorPosition' : 'anchorEl'}
      open={shouldShow}
      onClose={onClose}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'left',
      }}
    >
      {menuItems}
    </Menu>
  );
};

export default ContextMenu;