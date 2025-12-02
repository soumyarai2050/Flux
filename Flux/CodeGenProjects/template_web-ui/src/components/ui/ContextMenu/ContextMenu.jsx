import { useState } from 'react';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import ClearAll from '@mui/icons-material/ClearAll';
import ArrowRight from '@mui/icons-material/ArrowRight';
import { useTheme } from '@mui/material/styles';
import { Box, Button } from '@mui/material';
import { getResolvedColor } from '../../../utils/ui/colorUtils';

/**
 * ContextMenu Component - Right-click context menu for selective bulk patching with sub-actions
 *
 * Props:
 * - selectedRows: Array of selected row IDs
 * - availableButtons: Object mapping button names to their data:
 *    {
 *      displayName: {
 *        tableTitle: string,
 *        displayName: string,
 *        totalCount: number,
 *        isDisabled: boolean,
 *        cellMetadata: object,
 *        subActions: {
 *          caption: { caption, count, affectedRowIds, expectedCurrentState, color: string }
 *        }
 *      }
 *    }
 * - onSelectiveButtonPatch: Callback function when a sub-action is clicked
 *    Called with: (selectedRows, buttonType, actionCaption, expectedCurrentState)
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
  const [anchorElSubMenu, setAnchorElSubMenu] = useState(null);
  const [activeSubMenuButton, setActiveSubMenuButton] = useState(null);
  const theme = useTheme();

  const handleButtonClick = (event, buttonName) => {
    const subActions = availableButtons[buttonName]?.subActions;
    setAnchorElSubMenu(event.currentTarget);
    setActiveSubMenuButton(buttonName);
  };

  const handleSubMenuClose = () => {
    setAnchorElSubMenu(null);
    setActiveSubMenuButton(null);
  };

  const handleMainMenuClose = () => {
    handleSubMenuClose();
    onClose();
  };

  const handleSubActionClick = async (buttonType, actionCaption, expectedCurrentState) => {
    if (!onSelectiveButtonPatch || isPatching) return;

    try {
      setIsPatching(true);
      onClose();
      handleSubMenuClose();
      await onSelectiveButtonPatch(selectedRows, buttonType, actionCaption, expectedCurrentState);
    } catch (error) {
      console.error(`Error during button patch for ${buttonType} / ${actionCaption}:`, error);
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
  const shouldShow = open && selectedRows.length > 1;

  // Build menu items as array to avoid Fragment issues with MUI Menu
  const menuItems = [];

  if (hasButtons) {
    // Add dynamic button items with sub-actions
    Object.entries(availableButtons).forEach(([displayName, buttonData]) => {
      const subActionKeys = Object.keys(buttonData.subActions || {});
      const hasSubActions = subActionKeys.length > 0;

      // Main menu item for the button field
      menuItems.push(
        <MenuItem
          key={displayName}
          onClick={(e) => hasSubActions && handleButtonClick(e, displayName)}
          disabled={
            isPatching ||
            isLoading ||
            buttonData.isDisabled === true ||
            !hasSubActions
          }
          title={buttonData.isDisabled ? 'This button is disabled in the schema' : ''}
          sx={{
            cursor: hasSubActions ? 'pointer' : 'default',
            backgroundColor: activeSubMenuButton === displayName ? 'action.hover' : 'inherit'
          }}
        >
          <ListItemIcon >
            <TouchAppIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            {buttonData.displayName} ({buttonData.totalCount})
          </ListItemText>
          {hasSubActions && (
            <ArrowRight fontSize="small" sx={{ ml: 1 }} />
          )}
        </MenuItem>
      );
    });

    // Add divider before other options
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
    // Add divider even if no buttons
    menuItems.push(<Divider key="divider" sx={{ my: 0.5 }} />);
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

  // Get the currently active button data for sub-menu rendering
  const activeButtonData = activeSubMenuButton && availableButtons[activeSubMenuButton];
  const subMenuItems = [];

  if (activeButtonData && activeButtonData.subActions) {
    Object.entries(activeButtonData.subActions).forEach(([actionKey, subAction]) => {
      // Use getResolvedColor to get the actual color from the theme
      const resolvedColor = getResolvedColor(subAction.color, theme);

      subMenuItems.push(
        <Box
          key={`${activeSubMenuButton}-${actionKey}`}
          sx={{
            px: 0.5,
            py: 0.25,
          }}
        >
          <Button
            variant="contained"
            fullWidth
            size="small"
            onClick={() => handleSubActionClick(
              activeButtonData.tableTitle,
              subAction.caption,
              subAction.expectedCurrentState
            )}
            disabled={isPatching || isLoading}
            sx={{
              textTransform: 'none',
              justifyContent: 'flex-start',
              fontSize: '0.75rem',
              padding: '4px 8px',
              minHeight: '28px',
              backgroundColor: resolvedColor,
              '&:hover': {
                backgroundColor: resolvedColor,
                opacity: 0.8,
              },
              '&.Mui-disabled': {
                backgroundColor: resolvedColor,
                opacity: 0.6,
                color: '#fff',
              }
            }}
          >
            {subAction.caption} ({subAction.count})
          </Button>
        </Box>
      );
    });
  }

  return (
    <>
      <Menu
        anchorEl={null}
        anchorPosition={
          anchorEl && shouldShow
            ? { top: anchorEl.clientY, left: anchorEl.clientX }
            : undefined
        }
        anchorReference={anchorEl && shouldShow ? 'anchorPosition' : 'anchorEl'}
        open={shouldShow}
        onClose={handleMainMenuClose}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
      >
        {menuItems}
      </Menu>

      {/* Sub-menu for actions */}
      {activeSubMenuButton && anchorElSubMenu && (
        <Menu
          anchorEl={anchorElSubMenu}
          open={true}
          onClose={handleSubMenuClose}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'left',
          }}
          MenuListProps={{
            onMouseLeave: handleSubMenuClose,
            sx: { py: 0 }
          }}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, p: 0.5, minWidth: '100px', maxWidth:'150px' }}>
            {subMenuItems}
          </Box>
        </Menu>
      )}
    </>
  );
};

export default ContextMenu;