import React, { useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import { camelCase } from 'lodash';
import { MODES } from '../../../constants';
import styles from './PopoverWidgetWrapper.module.css';

// Map of Redux state keys to their selectors
// Used to fetch mode from Redux for each widget
// Redux state keys are snake_case (e.g., 'order_limits')
const getWidgetModeSelector = (widgetId) => (state) => {
  return state[widgetId]?.mode || null;
};

// Dispatch Redux actions for widget state management
// Redux action types are constructed with camelCase reducer names: camelCase(modelName)/actionName
const dispatchWidgetStateClear = (dispatch, widgetId) => {
  // Convert widgetId to camelCase for the action type (Redux slices are created with camelCase names)
  const reducerName = camelCase(widgetId);

  // Dispatch setMode action to widget's Redux slice
  dispatch({
    type: `${reducerName}/setMode`,
    payload: MODES.READ
  });
  // Dispatch setUpdatedObj action to clear widget's edited state
  dispatch({
    type: `${reducerName}/setUpdatedObj`,
    payload: null
  });
};

/**
 * PopoverWidgetWrapper Component
 * Wraps each widget in the floating popover and passes popover-specific props to the widget.
 * Handles maximize state and passes removal callback to the widget for header-integrated close button.
 * The widget component is responsible for rendering the close button in its header when isInPopover=true.
 */
const PopoverWidgetWrapper = ({
  widgetId,
  isMaximized,
  onRemove,
  onMaximizeToggle,
  children
}) => {
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
  const dispatch = useDispatch();

  // Fetch widget's mode directly from Redux using widgetId
  const widgetMode = useSelector(getWidgetModeSelector(widgetId));

  const handleRemove = useCallback((e) => {
    // e can be undefined if called directly (not from click event)
    if (e && e.stopPropagation) {
      e.stopPropagation();
    }

    console.log(`[handleRemove] widgetId: ${widgetId}, widgetMode: "${widgetMode}", MODES.EDIT: "${MODES.EDIT}", Equal? ${widgetMode === MODES.EDIT}`);

    // EDIT mode: Show confirmation dialog
    if (widgetMode === MODES.EDIT) {
      console.log(`[handleRemove] EDIT mode - showing dialog`);
      setShowRemoveConfirm(true);
    } else {
      // READ mode: Direct remove
      console.log(`[handleRemove] READ mode or null - direct remove`);
      onRemove(widgetId);
    }
  }, [widgetMode, widgetId, onRemove]);

  const handleConfirmRemove = useCallback(() => {
    // Clear widget's Redux state (mode → READ, updatedObj → null)
    dispatchWidgetStateClear(dispatch, widgetId);

    setShowRemoveConfirm(false);
    onRemove(widgetId);
  }, [widgetId, onRemove, dispatch]);

  const handleCancelRemove = useCallback(() => {
    setShowRemoveConfirm(false);
  }, []);

  const handleMaximizeToggleInPopover = () => {
    // Override the widget's maximize behavior to only work within popover
    onMaximizeToggle(widgetId);
  };

  const wrapperClass = isMaximized ? styles.wrapper_maximized : styles.wrapper;

  return (
    <>
      <div className={wrapperClass}>
        <div
          className={styles.widget_content}
          style={{
            height: '100%',
            position: isMaximized ? 'absolute' : 'relative',
            top: isMaximized ? 0 : 'auto',
            left: isMaximized ? 0 : 'auto',
            right: isMaximized ? 0 : 'auto',
            bottom: isMaximized ? 0 : 'auto',
            zIndex: isMaximized ? 10 : 1
          }}
        >
          {/* Pass popover-specific props to the widget component */}
          {React.cloneElement(children, {
            onMaximizeToggle: handleMaximizeToggleInPopover,
            isInPopover: true,
            onRemoveFromPopover: handleRemove,
            popoverWidgetId: widgetId
          })}
        </div>
      </div>

      {/* Remove confirmation dialog - shown only in EDIT mode */}
      <Dialog open={showRemoveConfirm} onClose={handleCancelRemove}>
        <DialogTitle>Remove Widget from Popover?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Changes to this widget will be lost if not saved. Continue?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelRemove} color="primary">
            Cancel
          </Button>
          <Button onClick={handleConfirmRemove} color="error" variant="contained">
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

PopoverWidgetWrapper.propTypes = {
  widgetId: PropTypes.string.isRequired,
  isMaximized: PropTypes.bool.isRequired,
  onRemove: PropTypes.func.isRequired,
  onMaximizeToggle: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
};

export default PopoverWidgetWrapper;