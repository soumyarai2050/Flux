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
 * @param {Array<string|number>} [options.selectedRows=[]] - (DataTable specific) Array of currently selected row IDs.
 * @param {string|number|null} [options.lastSelectedRowId=null] - (DataTable specific) ID of the last selected row.
 * @param {string|number|null} [options.selectionAnchorId=null] - (DataTable specific) ID of the selection anchor row.
 * @param {function(Array<string|number>): void} [options.setSelectedRows=null] - (DataTable specific) Setter for selected rows state.
 * @param {function(string|number|null): void} [options.setLastSelectedRowId=null] - (DataTable specific) Setter for last selected row ID state.
 * @param {function(string|number|null): void} [options.setSelectionAnchorId=null] - (DataTable specific) Setter for selection anchor ID state.
 * @param {function(string|number, string|number): Array<string|number>} [options.getRowRange=null] - (DataTable specific) Function to get a range of row IDs.
 * @param {string|null} [options.modelType=null] - (DataTable specific) The type of the model.
 * @returns {{handleKeyDown: function(KeyboardEvent): void}} An object containing the `handleKeyDown` function to be attached to a DOM element.
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
  modelType = null
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
    onExtendSelection
  } = callbacks;

  const handleKeyDown = useCallback((event) => {
    const isCtrlPressed = event.ctrlKey || event.metaKey;

    // Ctrl+Shift+Up/Down for range selection (DataTable only)
    if (ctrlShiftSelection && isCtrlPressed && event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;
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
        setLastSelectedRowId(targetRowId);
      }
    }
    // Shift+Arrow for extending selection (DataTable only)
    else if (shiftSelection && event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;
      event.preventDefault();
      event.stopPropagation();

      const allRowIds = activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
      if (allRowIds.length === 0) return;

      if (!lastSelectedRowId || !selectionAnchorId) {
        const firstRowId = allRowIds[0];
        if (setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
          setSelectedRows([firstRowId]);
          setLastSelectedRowId(firstRowId);
          setSelectionAnchorId(firstRowId);
        }
        return;
      }

      const currentIndex = allRowIds.indexOf(lastSelectedRowId);
      if (currentIndex === -1) return;

      let nextIndex = event.key === 'ArrowDown'
        ? Math.min(currentIndex + 1, allRowIds.length - 1)
        : Math.max(currentIndex - 1, 0);

      if (nextIndex === currentIndex) return;

      const nextRowId = allRowIds[nextIndex];
      if (getRowRange && setSelectedRows && setLastSelectedRowId) {
        const newSelectedRange = getRowRange(selectionAnchorId, nextRowId);
        setSelectedRows(newSelectedRange);
        setLastSelectedRowId(nextRowId);
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
            if (modelType && onRowSelect) {
              onRowSelect(targetRowId);
            }
          } else if (onRowSelect) {
            // AbbreviationMergeView: single selection
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
        nextIndex = currentIndex < allRowIds.length - 1 ? currentIndex + 1 : 0;
      } else {
        nextIndex = currentIndex > 0 ? currentIndex - 1 : allRowIds.length - 1;
      }

      const nextRowId = allRowIds[nextIndex];

      if (setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
        setSelectedRows([nextRowId]);
        setLastSelectedRowId(nextRowId);
        setSelectionAnchorId(nextRowId);
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
    modelType
  ]);

  return {
    handleKeyDown
  };
};

export default useKeyboardNavigation;