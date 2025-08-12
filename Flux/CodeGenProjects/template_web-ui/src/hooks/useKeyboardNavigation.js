import { useCallback } from 'react';
import { MODES } from '../constants';

const SCROLL_DELAY = 50; // milliseconds

/**
 * @function useKeyboardNavigation
 * @description Custom hook for keyboard navigation in table components.
 * Provides functionalities like scrolling, single row selection, and range selection based on key presses.
 * @param {object} options - Configuration options for the hook.
 * @param {string} options.mode - Current mode of the component (e.g., MODES.READ, MODES.EDIT).
 * @param {Array<Array<object>>} options.activeRows - Array of active rows, typically grouped rows for display.
 * @param {object} options.tableContainerRef - React ref to the HTML element that serves as the scrollable table container.
 * @param {object} [options.capabilities={}] - Object defining enabled navigation capabilities.
 * @param {boolean} [options.capabilities.editModeScrolling=true] - Enables Ctrl+Arrow scrolling in edit mode.
 * @param {boolean} [options.capabilities.readModeSelection=true] - Enables Ctrl+Up/Down selection in read mode.
 * @param {boolean} [options.capabilities.shiftSelection=false] - Enables Shift+Arrow range selection (typically for DataTable).
 * @param {boolean} [options.capabilities.ctrlShiftSelection=false] - Enables Ctrl+Shift+Arrow selection (typically for DataTable).
 * @param {object} [options.callbacks={}] - Callback functions to be triggered by navigation events.
 * @param {function(string|number): void} [options.callbacks.onRowSelect] - Function to select a row by its ID.
 * @param {function(string|number, string|number): void} [options.callbacks.onRangeSelect] - Function for range selection.
 * @param {function(string|number, string|number): void} [options.callbacks.onExtendSelection] - Function for extending selection.
 * @param {function(Array<string|number>): void} [options.callbacks.onSelectionChange] - Function called with the full selected IDs after a click selection change.
 * @param {Array<string|number>} [options.selectedRows=[]] - (DataTable specific) Array of currently selected row IDs.
 * @param {string|number|null} [options.lastSelectedRowId=null] - (DataTable specific) ID of the last selected row.
 * @param {string|number|null} [options.selectionAnchorId=null] - (DataTable specific) ID of the selection anchor row.
 * @param {function(Array<string|number>): void} [options.setSelectedRows=null] - (DataTable specific) Setter for selected rows state.
 * @param {function(string|number|null): void} [options.setLastSelectedRowId=null] - (DataTable specific) Setter for last selected row ID state.
 * @param {function(string|number|null): void} [options.setSelectionAnchorId=null] - (DataTable specific) Setter for selection anchor ID state.
 * @param {function(string|number, string|number): Array<string|number>} [options.getRowRange=null] - (DataTable specific) Function to get a range of row IDs.
 * @param {string|null} [options.modelType=null] - (DataTable specific) The type of the model.
 * @param {object} [options.dataSourcesModeDict={}] - Dictionary of data source modes to check for edit mode blocking.
 * @returns {{handleKeyDown: function(KeyboardEvent): void, handleRowClick: function(MouseEvent, string|number): { nextSelected: Array<string|number>, mostRecentId: string|number }|undefined}} An object containing handlers for keyboard and mouse selection.
 */
const useKeyboardNavigation = ({
  mode,
  activeRows,
  tableContainerRef,
  capabilities = {},
  callbacks = {},
  selectedRows = [],
  lastSelectedRowId = null,
  selectionAnchorId = null,
  setSelectedRows = null,
  setLastSelectedRowId = null,
  setSelectionAnchorId = null,
  getRowRange = null,
  modelType = null,
  dataSourcesModeDict = {}
}) => {
  const {
    editModeScrolling = true,
    readModeSelection = true,
    shiftSelection = false,
    ctrlShiftSelection = false
  } = capabilities;

  const {
    onRowSelect,
    onRangeSelect,
    onExtendSelection,
    onSelectionChange
  } = callbacks;

  const handleKeyDown = useCallback((event) => {
    const isCtrlPressed = event.ctrlKey || event.metaKey;

    // Ctrl+Shift+Up/Down for range selection (DataTable only)
    if (ctrlShiftSelection && isCtrlPressed && event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const allRowIdsOnPage = activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
      if (allRowIdsOnPage.length === 0) return;

      const currentAnchorId = selectionAnchorId || (selectedRows.length > 0 ? selectedRows[0] : allRowIdsOnPage[0]);
      if (!selectionAnchorId && setSelectionAnchorId) {
        setSelectionAnchorId(currentAnchorId);
      }

      let targetRowId;
      if (event.key === 'ArrowDown') {
        targetRowId = allRowIdsOnPage[allRowIdsOnPage.length - 1];
      } else {
        targetRowId = allRowIdsOnPage[0];
      }

      if (getRowRange && setSelectedRows && setLastSelectedRowId) {
        const newSelectedRange = getRowRange(currentAnchorId, targetRowId);
        setSelectedRows(newSelectedRange);
        setLastSelectedRowId(currentAnchorId);
        // Notify callbacks about the selection change
        if (onSelectionChange) {
          onSelectionChange(newSelectedRange, currentAnchorId);
        }
        if (onRowSelect) {
          onRowSelect(currentAnchorId);
        }
      }
    }
    // Shift+Arrow for extending selection (DataTable only)
    else if (shiftSelection && event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const allRowIds = activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
      if (allRowIds.length === 0) return;

      // Initialize selection if no anchor or last selected exists
      if (!lastSelectedRowId || !selectionAnchorId) {
        const firstRowId = allRowIds[0];
        if (setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
          setSelectedRows([firstRowId]);
          setLastSelectedRowId(firstRowId);
          setSelectionAnchorId(firstRowId);
        }
        return;
      }

      // Excel-like behavior: Keep anchor fixed, handle contraction then extension
      const anchorIndex = allRowIds.indexOf(selectionAnchorId);
      if (anchorIndex === -1) return;

      // Find current selection boundaries
      const selectedIndices = selectedRows.map(id => allRowIds.indexOf(id)).filter(idx => idx !== -1);
      if (selectedIndices.length === 0) return;

      const minSelectedIndex = Math.min(...selectedIndices);
      const maxSelectedIndex = Math.max(...selectedIndices);

      let nextBoundaryIndex;

      if (event.key === 'ArrowDown') {
        // Moving down: First contract upward selection, then extend downward
        if (minSelectedIndex < anchorIndex) {
          // Contract upward selection by moving min boundary toward anchor
          nextBoundaryIndex = minSelectedIndex + 1;
        } else {
          // No upward selection to contract, extend downward from max boundary
          nextBoundaryIndex = Math.min(maxSelectedIndex + 1, allRowIds.length - 1);
        }
      } else {
        // Moving up: First contract downward selection, then extend upward
        if (maxSelectedIndex > anchorIndex) {
          // Contract downward selection by moving max boundary toward anchor
          nextBoundaryIndex = maxSelectedIndex - 1;
        } else {
          // No downward selection to contract, extend upward from min boundary
          nextBoundaryIndex = Math.max(minSelectedIndex - 1, 0);
        }
      }

      // Don't proceed if we can't move
      const currentBoundaryIndex = event.key === 'ArrowDown' ?
        (minSelectedIndex < anchorIndex ? minSelectedIndex : maxSelectedIndex) :
        (maxSelectedIndex > anchorIndex ? maxSelectedIndex : minSelectedIndex);

      if (nextBoundaryIndex === currentBoundaryIndex) return;

      const nextRowId = allRowIds[nextBoundaryIndex];
      if (getRowRange && setSelectedRows && setLastSelectedRowId) {
        // Always calculate range from FIXED anchor to new boundary
        const newSelectedRange = getRowRange(selectionAnchorId, nextRowId);
        setSelectedRows(newSelectedRange);
        // Keep lastSelectedRowId as the anchor for data binding (Excel behavior)
        setLastSelectedRowId(selectionAnchorId);

        // Notify callbacks about the selection change
        if (onSelectionChange) {
          onSelectionChange(newSelectedRange, selectionAnchorId);
        }
        if (onRowSelect) {
          // Data binding should use anchor row (Excel behavior)
          onRowSelect(selectionAnchorId);
        }
      }
    }
    // Ctrl+Arrow navigation
    else if (isCtrlPressed && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      event.stopPropagation();

      if (mode === MODES.EDIT && editModeScrolling) {
        // Edit mode: vertical and horizontal scrolling
        if (!tableContainerRef?.current) return;
        const container = tableContainerRef.current;

        switch (event.key) {
          case 'ArrowUp':
            container.scrollTo({ top: 0, behavior: 'smooth' });
            break;
          case 'ArrowDown':
            container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
            break;
          case 'ArrowLeft':
            container.scrollTo({ left: 0, behavior: 'smooth' });
            break;
          case 'ArrowRight':
            container.scrollTo({ left: container.scrollWidth, behavior: 'smooth' });
            break;
          default:
            break;
        }
      }
      else if (mode === MODES.READ && readModeSelection) {
        // Read mode: select top/bottom items
        if (!activeRows || activeRows.length === 0) return;
        // Block visual selection if any data source is in edit mode
        if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
          return;
        }

        let targetRowId = null;

        if (event.key === 'ArrowUp') {
          const firstRow = activeRows[0];
          if (firstRow && firstRow[0] && firstRow[0]['data-id']) {
            targetRowId = firstRow[0]['data-id'];
          }
        } else if (event.key === 'ArrowDown') {
          const lastRowIndex = activeRows.length - 1;
          const lastRow = activeRows[lastRowIndex];
          if (lastRow && lastRow[0] && lastRow[0]['data-id']) {
            targetRowId = lastRow[0]['data-id'];
          }
        }

        if (targetRowId) {
          // Handle different selection patterns
          if (shiftSelection && setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
            // DataTable: multi-selection
            setSelectedRows([targetRowId]);
            setLastSelectedRowId(targetRowId);
            setSelectionAnchorId(targetRowId);
            // Notify about selection change for visual updates
            if (onSelectionChange) {
              onSelectionChange([targetRowId], targetRowId);
            }
          }

          // Always notify parent about the selection for data binding
          if (onRowSelect) {
            onRowSelect(targetRowId);
          }

          // Scroll to selected row
          setTimeout(() => {
            const tableContainer = tableContainerRef?.current;
            if (tableContainer) {
              let selectedRowElement = tableContainer.querySelector(`tr[data-row-id="${targetRowId}"]`);

              if (!selectedRowElement) {
                const tbody = tableContainer.querySelector('tbody');
                if (tbody) {
                  const rows = tbody.querySelectorAll('tr');
                  if (event.key === 'ArrowUp' && rows.length > 0) {
                    selectedRowElement = rows[0];
                  } else if (event.key === 'ArrowDown' && rows.length > 0) {
                    selectedRowElement = rows[rows.length - 1];
                  }
                }
              }

              if (selectedRowElement) {
                selectedRowElement.scrollIntoView({
                  behavior: 'smooth',
                  block: 'center'
                });
              } else {
                if (event.key === 'ArrowUp') {
                  tableContainer.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                  tableContainer.scrollTo({ top: tableContainer.scrollHeight, behavior: 'smooth' });
                }
              }
            }
          }, SCROLL_DELAY);
        }
      }
    }
    // Plain Up/Down arrow navigation in Read Mode (single selection)
    else if (
      mode === MODES.READ &&
      (event.key === 'ArrowUp' || event.key === 'ArrowDown') &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey
    ) {
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const allRowIds = activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
      if (allRowIds.length === 0) return;

      let currentIndex = -1;
      if (selectedRows && selectedRows.length > 0) {
        currentIndex = allRowIds.indexOf(selectedRows[0]);
      }

      let nextIndex;
      if (event.key === 'ArrowDown') {
        nextIndex = currentIndex < allRowIds.length - 1 ? currentIndex + 1 : currentIndex;
      } else {
        nextIndex = currentIndex > 0 ? currentIndex - 1 : currentIndex;
      }

      // Don't proceed if we're at the boundary and can't move further
      if (nextIndex === currentIndex) return;

      const nextRowId = allRowIds[nextIndex];

      if (setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
        setSelectedRows([nextRowId]);
        setLastSelectedRowId(nextRowId);
        setSelectionAnchorId(nextRowId);
        // Notify about selection change for visual updates
        if (onSelectionChange) {
          onSelectionChange([nextRowId], nextRowId);
        }
      }
      if (onRowSelect) {
        onRowSelect(nextRowId);
      }

      // Scroll to the selected row
      setTimeout(() => {
        const tableContainer = tableContainerRef?.current;
        if (tableContainer) {
          let selectedRowElement = tableContainer.querySelector(`tr[data-row-id="${nextRowId}"]`);
          if (selectedRowElement) {
            selectedRowElement.scrollIntoView({
              behavior: 'smooth',
              block: 'center'
            });
          }
        }
      }, SCROLL_DELAY);
    }
  }, [
    mode,
    activeRows,
    tableContainerRef,
    editModeScrolling,
    readModeSelection,
    shiftSelection,
    ctrlShiftSelection,
    onRowSelect,
    selectedRows,
    lastSelectedRowId,
    selectionAnchorId,
    setSelectedRows,
    setLastSelectedRowId,
    setSelectionAnchorId,
    getRowRange,
    modelType,
    dataSourcesModeDict
  ]);

  // New: mouse click selection that supports Ctrl/Shift toggling and tracks most recent
  const handleRowClick = useCallback((e, rowId) => {
    if (mode !== MODES.READ) return;

    // Block visual selection if any data source is in edit mode
    if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
      return;
    }

    const isCtrl = e?.ctrlKey || e?.metaKey;
    const isShift = e?.shiftKey;

    let nextSelected = [];

    if (isShift && selectionAnchorId && getRowRange) {
      const range = getRowRange(selectionAnchorId, rowId);
      if (isCtrl) {
        // Ctrl+Shift: extend selection by range
        nextSelected = Array.from(new Set([...(selectedRows || []), ...range]));
      } else {
        // Shift only: replace with range, keep original anchor fixed
        nextSelected = range;
      }
      // DON'T update anchor - keep original anchor for Excel-like behavior
      // The anchor should remain the same for visual distinction (dark vs light)
    } else if (isCtrl) {
      // Ctrl: toggle single
      const set = new Set(selectedRows || []);
      const wasSelected = set.has(rowId);
      
      if (wasSelected) {
        set.delete(rowId);
        // When unselecting, find the previous most recent from remaining selection
        if (set.size > 0 && setSelectionAnchorId) {
          // Use the last item in the remaining selection as new anchor (Excel-like)
          const remainingRows = Array.from(set);
          const newAnchor = remainingRows[remainingRows.length - 1];
          setSelectionAnchorId(newAnchor);
        }
      } else {
        set.add(rowId);
        // When adding, the newly added row becomes the anchor
        if (setSelectionAnchorId) setSelectionAnchorId(rowId);
      }
      nextSelected = Array.from(set);
    } else {
      // Plain click: single select
      nextSelected = [rowId];
      if (setSelectionAnchorId) setSelectionAnchorId(rowId);
    }

    if (setSelectedRows) setSelectedRows(nextSelected);

    // Determine correct data binding row based on operation type
    let dataBindingRowId;
    if (isShift && selectionAnchorId) {
      // Shift+Click: use original anchor
      dataBindingRowId = selectionAnchorId;
    } else if (isCtrl) {
      const wasSelected = (selectedRows || []).includes(rowId);
      if (wasSelected && nextSelected.length > 0) {
        // Ctrl+Click unselect: use new anchor (last remaining row)
        dataBindingRowId = nextSelected[nextSelected.length - 1];
      } else if (!wasSelected) {
        // Ctrl+Click select: use clicked row (new anchor)
        dataBindingRowId = rowId;
      } else {
        // Unselected everything
        dataBindingRowId = null;
      }
    } else {
      // Plain click: use clicked row
      dataBindingRowId = rowId;
    }
    
    if (setLastSelectedRowId) setLastSelectedRowId(dataBindingRowId);
    if (onSelectionChange) onSelectionChange(nextSelected, dataBindingRowId);
    if (onRowSelect && dataBindingRowId) onRowSelect(dataBindingRowId);

    return { nextSelected, mostRecentId: dataBindingRowId };
  }, [
    mode,
    selectedRows,
    selectionAnchorId,
    setSelectedRows,
    setLastSelectedRowId,
    setSelectionAnchorId,
    getRowRange,
    onSelectionChange,
    onRowSelect,
    dataSourcesModeDict
  ]);

  return {
    handleKeyDown,
    handleRowClick
  };
};

export default useKeyboardNavigation;