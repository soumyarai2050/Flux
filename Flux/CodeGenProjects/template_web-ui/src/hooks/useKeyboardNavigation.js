import { useCallback, useState, useRef, useEffect, useMemo } from 'react';
import { MODES } from '../constants';

const SCROLL_DELAY = 50; // milliseconds

/**
 * @function useKeyboardNavigation
 * @description Custom hook for keyboard navigation in table components.
 * Provides functionalities like scrolling, single row selection, and range selection based on key presses.
 * @param {object} options - Configuration options for the hook.
 * @param {string} options.mode - Current mode of the component (e.g., MODES.READ, MODES.EDIT).
 * @param {Array<Array<object>>} options.activeRows - Array of active rows, typically grouped rows for display.
 * @param {Array<object>} [options.columns=[]] - Array of column definitions with sourceIndex for horizontal navigation.
 * @param {object} options.tableContainerRef - React ref to the HTML element that serves as the scrollable table container.
 * @param {object} [options.capabilities={}] - Object defining enabled navigation capabilities.
 * @param {boolean} [options.capabilities.editModeScrolling=true] - Enables Ctrl+Arrow scrolling in edit mode.
 * @param {boolean} [options.capabilities.readModeSelection=true] - Enables Ctrl+Up/Down selection in read mode.
 * @param {boolean} [options.capabilities.shiftSelection=false] - Enables Shift+Arrow range selection (typically for DataTable).
 * @param {boolean} [options.capabilities.ctrlShiftSelection=false] - Enables Ctrl+Shift+Arrow selection (typically for DataTable).
 * @param {boolean} [options.capabilities.dragSelection=false] - Enables mouse drag selection functionality.
 * @param {object} [options.callbacks={}] - Callback functions to be triggered by navigation events.
 * @param {function(string|number): void} [options.callbacks.onRowSelect] - Function to select a row by its ID.
 * @param {function(string|number, string|number): void} [options.callbacks.onRangeSelect] - Function for range selection.
 * @param {function(string|number, string|number): void} [options.callbacks.onExtendSelection] - Function for extending selection.
 * @param {function(Array<string|number>): void} [options.callbacks.onSelectionChange] - Function called with the full selected IDs after a click selection change.
 * @param {function(boolean): void} [options.callbacks.onDragStateChange] - Function called when drag state changes.
 * @param {Array<string|number>} [options.selectedRows=[]] - (DataTable specific) Array of currently selected row IDs.
 * @param {string|number|null} [options.lastSelectedRowId=null] - (DataTable specific) ID of the last selected row.
 * @param {string|number|null} [options.selectionAnchorId=null] - (DataTable specific) ID of the selection anchor row.
 * @param {function(Array<string|number>): void} [options.setSelectedRows=null] - (DataTable specific) Setter for selected rows state.
 * @param {function(string|number|null): void} [options.setLastSelectedRowId=null] - (DataTable specific) Setter for last selected row ID state.
 * @param {function(string|number|null): void} [options.setSelectionAnchorId=null] - (DataTable specific) Setter for selection anchor ID state.
 * @param {function(string|number, string|number): Array<string|number>} [options.getRowRange=null] - (DataTable specific) Function to get a range of row IDs.
 * @param {string|null} [options.modelType=null] - (DataTable specific) The type of the model.
 * @param {object} [options.dataSourcesModeDict={}] - Dictionary of data source modes to check for edit mode blocking.
 * @param {object} [options.tableWrapperRef=null] - React ref to table wrapper element for focus management during drag.
 * @param {number} [options.maxRowSize=1] - Maximum number of rows in a group (for join operations).
 * @returns {{handleKeyDown: function(KeyboardEvent): void, handleRowClick: function(MouseEvent, string|number): { nextSelected: Array<string|number>, mostRecentId: string|number }|undefined, handleRowMouseDown: function(MouseEvent, string|number): void, handleRowMouseEnter: function(MouseEvent, string|number): void, handleRowMouseClick: function(MouseEvent, string|number): void, isDragging: boolean}} An object containing handlers for keyboard and mouse selection.
 */
const useKeyboardNavigation = ({
  mode,
  activeRows,
  columns = [],
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
  dataSourcesModeDict = {},
  tableWrapperRef = null,
  maxRowSize = 1
}) => {
  const {
    editModeScrolling = true,
    readModeSelection = true,
    shiftSelection = false,
    ctrlShiftSelection = false,
    dragSelection = false,
    copySelection = false
  } = capabilities;

  const {
    onRowSelect,
    onRangeSelect,
    onExtendSelection,
    onSelectionChange,
    onDragStateChange,
    onCopySelection
  } = callbacks;

  // Drag selection state (only when enabled)
  const [isDragging, setIsDragging] = useState(false);
  const wasDraggedRef = useRef(false);

  // Track if we're in a "select all" state (for Ctrl+A specific anchor behavior)
  const [isSelectAllActive, setIsSelectAllActive] = useState(false);

  // Helper function to collect all row IDs based on maxRowSize
  const getAllRowIds = useCallback(() => {
    let allRowIds = [];
    if (maxRowSize > 1) {
      // Join operation: collect all subrow IDs from all groups
      for (const groupedRow of activeRows || []) {
        for (let i = 0; i < groupedRow.length; i++) {
          const subRow = groupedRow[i];
          if (subRow && subRow['data-id']) {
            allRowIds.push(subRow['data-id']);
          }
        }
      }
    } else {
      // Standard operation: only collect primary row IDs
      allRowIds = activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
    }
    return allRowIds;
  }, [activeRows, maxRowSize]);

  // Build columnGroups mapping: sourceIndex -> array of visible column indexes
  // This is used for horizontal navigation in join scenarios
  const columnGroups = useMemo(() => {
    if (maxRowSize <= 1 || !columns.length) return [];

    const groups = new Array(maxRowSize).fill(null).map(() => []);
    columns.forEach((column, columnIndex) => {
      const sourceIndex = column.sourceIndex ?? 0;
      if (sourceIndex < maxRowSize && !column.frozenColumn) {
        groups[sourceIndex].push(columnIndex);
      }
    });
    return groups;
  }, [columns, maxRowSize]);

  // Helper function to get current sub-row info from selected row ID
  const getSubRowInfo = useCallback((rowId) => {
    if (!rowId || !activeRows) return null;

    for (let visualIndex = 0; visualIndex < activeRows.length; visualIndex++) {
      const groupedRow = activeRows[visualIndex];
      for (let groupIndex = 0; groupIndex < groupedRow.length; groupIndex++) {
        const subRow = groupedRow[groupIndex];
        if (subRow && subRow['data-id'] === rowId) {
          return { visualIndex, groupIndex, subRow };
        }
      }
    }
    return null;
  }, [activeRows]);

  // Helper function to get neighboring sub-row in horizontal direction
  const getHorizontalNeighbor = useCallback((currentRowId, direction) => {
    const currentInfo = getSubRowInfo(currentRowId);
    if (!currentInfo || maxRowSize <= 1) return null;

    const { visualIndex, groupIndex } = currentInfo;
    const availableGroups = columnGroups.filter(group => group.length > 0);
    const currentGroupPosition = availableGroups.findIndex(group => group.length > 0 &&
      columnGroups[groupIndex] === group);

    if (currentGroupPosition === -1) return null;

    let nextGroupPosition;
    if (direction === 'left') {
      nextGroupPosition = currentGroupPosition - 1;
    } else {
      nextGroupPosition = currentGroupPosition + 1;
    }

    if (nextGroupPosition < 0 || nextGroupPosition >= availableGroups.length) {
      return null;
    }

    // Find the sourceIndex of the target group
    const targetGroupIndex = columnGroups.findIndex(group => group === availableGroups[nextGroupPosition]);

    const targetSubRow = activeRows[visualIndex]?.[targetGroupIndex];
    if (targetSubRow && targetSubRow['data-id']) {
      return targetSubRow['data-id'];
    }

    return null;
  }, [getSubRowInfo, maxRowSize, columnGroups, activeRows]);

  // Helper function to get main row IDs (one per visual row group)
  const getMainRowIds = useCallback(() => {
    if (maxRowSize <= 1) {
      // Non-join scenario: return all row IDs
      return activeRows?.map(groupedRow => groupedRow[0]['data-id']) || [];
    } else {
      // Join scenario: return first available sub-row ID from each main row
      return activeRows?.map(groupedRow => {
        // Find the first sub-row that exists in this group
        for (let i = 0; i < groupedRow.length; i++) {
          const subRow = groupedRow[i];
          if (subRow && subRow['data-id']) {
            return subRow['data-id'];
          }
        }
        return null;
      }).filter(id => id !== null) || [];
    }
  }, [activeRows, maxRowSize]);

  // Helper function to get neighboring main row in vertical direction
  const getVerticalNeighbor = useCallback((currentRowId, direction) => {
    if (maxRowSize <= 1) {
      // Non-join scenario: use existing logic
      const allRowIds = getAllRowIds();
      const currentIndex = allRowIds.indexOf(currentRowId);
      if (currentIndex === -1) return null;

      let nextIndex;
      if (direction === 'down') {
        nextIndex = currentIndex < allRowIds.length - 1 ? currentIndex + 1 : -1;
      } else {
        nextIndex = currentIndex > 0 ? currentIndex - 1 : -1;
      }

      return nextIndex >= 0 ? allRowIds[nextIndex] : null;
    } else {
      // Join scenario: navigate between main rows, preserving horizontal position
      const currentInfo = getSubRowInfo(currentRowId);
      if (!currentInfo) return null;

      const { visualIndex, groupIndex } = currentInfo;
      let targetVisualIndex;

      if (direction === 'down') {
        targetVisualIndex = visualIndex < activeRows.length - 1 ? visualIndex + 1 : -1;
      } else {
        targetVisualIndex = visualIndex > 0 ? visualIndex - 1 : -1;
      }

      if (targetVisualIndex < 0) return null;

      // Try to stay in the same sub-row position (groupIndex) if possible
      const targetGroup = activeRows[targetVisualIndex];
      if (targetGroup[groupIndex] && targetGroup[groupIndex]['data-id']) {
        return targetGroup[groupIndex]['data-id'];
      }

      // If the same position doesn't exist, find the first available sub-row
      for (let i = 0; i < targetGroup.length; i++) {
        const subRow = targetGroup[i];
        if (subRow && subRow['data-id']) {
          return subRow['data-id'];
        }
      }

      return null;
    }
  }, [maxRowSize, getAllRowIds, getSubRowInfo, activeRows]);

  // Effect to handle mouse up for drag selection cleanup
  useEffect(() => {
    if (!dragSelection) return;

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
      }
      if (wasDraggedRef.current) {
        wasDraggedRef.current = false;
      }
    };
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragSelection]);

  // Notify parent components when drag state changes
  useEffect(() => {
    if (dragSelection && onDragStateChange) {
      onDragStateChange(isDragging);
    }
  }, [isDragging, dragSelection, onDragStateChange]);

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

      const mainRowIds = getMainRowIds();
      if (mainRowIds.length === 0) return;

      const currentAnchorId = selectionAnchorId || (selectedRows.length > 0 ? selectedRows[0] : mainRowIds[0]);
      if (!selectionAnchorId && setSelectionAnchorId) {
        setSelectionAnchorId(currentAnchorId);
      }

      let targetRowId;
      if (event.key === 'ArrowDown') {
        targetRowId = mainRowIds[mainRowIds.length - 1];
      } else {
        targetRowId = mainRowIds[0];
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

      if (!selectedRows || selectedRows.length === 0) return;

      // Initialize anchor if not set
      if (!selectionAnchorId && setSelectionAnchorId) {
        const currentAnchor = selectedRows[0];
        setSelectionAnchorId(currentAnchor);
      }

      const currentAnchor = selectionAnchorId || selectedRows[0];

      if (maxRowSize <= 1) {
        // Non-join scenario: Use traditional Excel-like range selection logic
        const allRowIds = getAllRowIds();
        if (allRowIds.length === 0) return;

        const anchorIndex = allRowIds.indexOf(currentAnchor);
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
          const newSelectedRange = getRowRange(currentAnchor, nextRowId);
          setSelectedRows(newSelectedRange);
          // Keep lastSelectedRowId as the anchor for data binding (Excel behavior)
          setLastSelectedRowId(currentAnchor);

          // Notify callbacks about the selection change
          if (onSelectionChange) {
            onSelectionChange(newSelectedRange, currentAnchor);
          }
          if (onRowSelect) {
            // Data binding should use anchor row (Excel behavior)
            onRowSelect(currentAnchor);
          }
        }
      } else {
        // Join scenario: Excel-like rectangular selection with contraction
        const direction = event.key === 'ArrowDown' ? 'down' : 'up';

        const anchorInfo = getSubRowInfo(currentAnchor);
        if (!anchorInfo) return;

        // Find current selection boundaries
        const selectedRowsInfo = selectedRows.map(id => getSubRowInfo(id)).filter(info => info !== null);
        if (selectedRowsInfo.length === 0) return;

        const selectedVisualIndices = selectedRowsInfo.map(info => info.visualIndex);
        const selectedGroupIndices = selectedRowsInfo.map(info => info.groupIndex);

        const minVisualIndex = Math.min(...selectedVisualIndices);
        const maxVisualIndex = Math.max(...selectedVisualIndices);
        const minGroupIndex = Math.min(...selectedGroupIndices);
        const maxGroupIndex = Math.max(...selectedGroupIndices);

        // Determine new boundary based on direction
        let newVisualBoundary;
        if (direction === 'down') {
          // Check if we should contract or expand
          if (maxVisualIndex > anchorInfo.visualIndex) {
            // We have selection below anchor, try to expand further down
            newVisualBoundary = Math.min(maxVisualIndex + 1, activeRows.length - 1);
          } else if (minVisualIndex < anchorInfo.visualIndex) {
            // We have selection above anchor, contract upward (move min up toward anchor)
            newVisualBoundary = Math.min(minVisualIndex + 1, anchorInfo.visualIndex);
          } else {
            // Selection is at anchor, expand down
            newVisualBoundary = Math.min(anchorInfo.visualIndex + 1, activeRows.length - 1);
          }
        } else {
          // Moving up
          if (minVisualIndex < anchorInfo.visualIndex) {
            // We have selection above anchor, try to expand further up
            newVisualBoundary = Math.max(minVisualIndex - 1, 0);
          } else if (maxVisualIndex > anchorInfo.visualIndex) {
            // We have selection below anchor, contract downward (move max up toward anchor)
            newVisualBoundary = Math.max(maxVisualIndex - 1, anchorInfo.visualIndex);
          } else {
            // Selection is at anchor, expand up
            newVisualBoundary = Math.max(anchorInfo.visualIndex - 1, 0);
          }
        }

        // Calculate new rectangular selection from anchor to new boundary
        const newMinVisual = Math.min(anchorInfo.visualIndex, newVisualBoundary);
        const newMaxVisual = Math.max(anchorInfo.visualIndex, newVisualBoundary);

        const rectangularSelection = [];
        for (let vIndex = newMinVisual; vIndex <= newMaxVisual; vIndex++) {
          for (let gIndex = minGroupIndex; gIndex <= maxGroupIndex; gIndex++) {
            const subRow = activeRows[vIndex]?.[gIndex];
            if (subRow && subRow['data-id']) {
              rectangularSelection.push(subRow['data-id']);
            }
          }
        }

        if (setSelectedRows && setLastSelectedRowId) {
          setSelectedRows(rectangularSelection);
          setLastSelectedRowId(currentAnchor);

          // Notify callbacks about the selection change
          if (onSelectionChange) {
            onSelectionChange(rectangularSelection, currentAnchor);
          }
          if (onRowSelect) {
            onRowSelect(currentAnchor);
          }
        }
      }
    }
    // Shift+Arrow for horizontal range selection in join scenarios
    else if (
      shiftSelection &&
      event.shiftKey &&
      (event.key === 'ArrowLeft' || event.key === 'ArrowRight') &&
      maxRowSize > 1
    ) {
      if (mode !== MODES.READ) return;
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      if (!selectedRows || selectedRows.length === 0) return;

      // Initialize anchor if not set
      if (!selectionAnchorId && setSelectionAnchorId) {
        const currentAnchor = selectedRows[0];
        setSelectionAnchorId(currentAnchor);
      }

      const currentAnchor = selectionAnchorId || selectedRows[0];
      const direction = event.key === 'ArrowLeft' ? 'left' : 'right';

      const anchorInfo = getSubRowInfo(currentAnchor);
      if (!anchorInfo) return;

      // Find current selection boundaries
      const selectedRowsInfo = selectedRows.map(id => getSubRowInfo(id)).filter(info => info !== null);
      if (selectedRowsInfo.length === 0) return;

      const selectedVisualIndices = selectedRowsInfo.map(info => info.visualIndex);
      const selectedGroupIndices = selectedRowsInfo.map(info => info.groupIndex);

      const minVisualIndex = Math.min(...selectedVisualIndices);
      const maxVisualIndex = Math.max(...selectedVisualIndices);
      const minGroupIndex = Math.min(...selectedGroupIndices);
      const maxGroupIndex = Math.max(...selectedGroupIndices);

      // Find available groups (column positions)
      const availableGroups = columnGroups.map((group, index) => ({ index, hasColumns: group.length > 0 }))
        .filter(g => g.hasColumns)
        .map(g => g.index);

      if (availableGroups.length === 0) return;

      // Determine new boundary based on direction (Excel-like contraction/expansion)
      let newGroupBoundary;
      if (direction === 'right') {
        // Check if we should contract or expand
        if (maxGroupIndex > anchorInfo.groupIndex) {
          // We have selection to the right of anchor, try to expand further right
          const currentMaxPos = availableGroups.indexOf(maxGroupIndex);
          const nextPos = currentMaxPos + 1;
          newGroupBoundary = nextPos < availableGroups.length ? availableGroups[nextPos] : maxGroupIndex;
        } else if (minGroupIndex < anchorInfo.groupIndex) {
          // We have selection to the left of anchor, contract leftward (move min right toward anchor)
          const currentMinPos = availableGroups.indexOf(minGroupIndex);
          const nextPos = currentMinPos + 1;
          newGroupBoundary = nextPos < availableGroups.length ? availableGroups[nextPos] : minGroupIndex;
        } else {
          // Selection is at anchor, expand right
          const anchorPos = availableGroups.indexOf(anchorInfo.groupIndex);
          const nextPos = anchorPos + 1;
          newGroupBoundary = nextPos < availableGroups.length ? availableGroups[nextPos] : anchorInfo.groupIndex;
        }
      } else {
        // Moving left
        if (minGroupIndex < anchorInfo.groupIndex) {
          // We have selection to the left of anchor, try to expand further left
          const currentMinPos = availableGroups.indexOf(minGroupIndex);
          const nextPos = currentMinPos - 1;
          newGroupBoundary = nextPos >= 0 ? availableGroups[nextPos] : minGroupIndex;
        } else if (maxGroupIndex > anchorInfo.groupIndex) {
          // We have selection to the right of anchor, contract rightward (move max left toward anchor)
          const currentMaxPos = availableGroups.indexOf(maxGroupIndex);
          const nextPos = currentMaxPos - 1;
          newGroupBoundary = nextPos >= 0 ? availableGroups[nextPos] : maxGroupIndex;
        } else {
          // Selection is at anchor, expand left
          const anchorPos = availableGroups.indexOf(anchorInfo.groupIndex);
          const nextPos = anchorPos - 1;
          newGroupBoundary = nextPos >= 0 ? availableGroups[nextPos] : anchorInfo.groupIndex;
        }
      }

      // Calculate new rectangular selection from anchor to new boundary
      const newMinGroup = Math.min(anchorInfo.groupIndex, newGroupBoundary);
      const newMaxGroup = Math.max(anchorInfo.groupIndex, newGroupBoundary);

      const rectangularSelection = [];
      for (let vIndex = minVisualIndex; vIndex <= maxVisualIndex; vIndex++) {
        for (let gIndex = newMinGroup; gIndex <= newMaxGroup; gIndex++) {
          const subRow = activeRows[vIndex]?.[gIndex];
          if (subRow && subRow['data-id']) {
            rectangularSelection.push(subRow['data-id']);
          }
        }
      }

      if (setSelectedRows && setLastSelectedRowId) {
        setSelectedRows(rectangularSelection);
        setLastSelectedRowId(currentAnchor);

        // Notify callbacks about the selection change
        if (onSelectionChange) {
          onSelectionChange(rectangularSelection, currentAnchor);
        }
        if (onRowSelect) {
          onRowSelect(currentAnchor);
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

      if (!selectedRows || selectedRows.length === 0) return;

      const currentRowId = selectedRows[0];
      const direction = event.key === 'ArrowDown' ? 'down' : 'up';
      const nextRowId = getVerticalNeighbor(currentRowId, direction);

      if (!nextRowId) return;

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
    // Plain Left/Right arrow navigation in Read Mode (horizontal navigation in join scenarios)
    else if (
      mode === MODES.READ &&
      (event.key === 'ArrowLeft' || event.key === 'ArrowRight') &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey &&
      maxRowSize > 1
    ) {
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      if (!selectedRows || selectedRows.length === 0) return;

      const currentRowId = selectedRows[0];
      const direction = event.key === 'ArrowLeft' ? 'left' : 'right';
      const nextRowId = getHorizontalNeighbor(currentRowId, direction);

      if (!nextRowId) return;

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

      // // Scroll to the selected row and handle horizontal scrolling
      // setTimeout(() => {
      //   const tableContainer = tableContainerRef?.current;
      //   if (tableContainer) {
      //     let selectedRowElement = tableContainer.querySelector(`tr[data-row-id="${nextRowId}"]`);
      //     if (selectedRowElement) {
      //       // Vertical scrolling (keep row in view)
      //       selectedRowElement.scrollIntoView({
      //         behavior: 'smooth',
      //         block: 'center'
      //       });

      //       // Find the specific cell within the row for horizontal scrolling
      //       const targetInfo = getSubRowInfo(nextRowId);
      //       if (targetInfo) {
      //         // Find the cell at the target column position
      //         const cells = selectedRowElement.querySelectorAll('td');
      //         // Try to find the cell based on column position - this is approximate
      //         // since cell index might not directly map to groupIndex due to frozen columns
      //         const targetCell = cells[targetInfo.groupIndex];
      //         if (targetCell) {
      //           const containerRect = tableContainer.getBoundingClientRect();
      //           const cellRect = targetCell.getBoundingClientRect();

      //           // Check if cell is outside visible horizontal area
      //           if (cellRect.left < containerRect.left || cellRect.right > containerRect.right) {
      //             // Calculate scroll position to center the cell horizontally
      //             const scrollLeft = tableContainer.scrollLeft + 
      //               (cellRect.left + cellRect.width/2) - 
      //               (containerRect.left + containerRect.width/2);

      //             tableContainer.scrollTo({
      //               left: Math.max(0, scrollLeft),
      //               behavior: 'smooth'
      //             });
      //           }
      //         }
      //       }
      //     }
      //   }
      // }, SCROLL_DELAY);
    }
    else if (mode === MODES.READ && isCtrlPressed && event.key === 'c') {
      // Block if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault(); // Prevent default browser copy action
      event.stopPropagation();
      // Only proceed if there's a callback and rows are selected
      if (onCopySelection && selectedRows && selectedRows.length > 0) {
        onCopySelection(selectedRows);
      }
    }
    // Ctrl+A for select all functionality (Read mode only)
    else if (isCtrlPressed && event.key === 'a') {
      if (mode !== MODES.READ) return;
      // Block visual selection if any data source is in edit mode
      if (Object.values(dataSourcesModeDict).includes(MODES.EDIT)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();

      const allRowIds = getAllRowIds();
      if (allRowIds.length === 0) return;

      // Preserve current anchor if it exists, or set to first row
      const currentAnchor = selectionAnchorId || (selectedRows.length > 0 ? selectedRows[0] : allRowIds[0]);

      if (setSelectedRows && setLastSelectedRowId && setSelectionAnchorId) {
        // Select all rows
        setSelectedRows(allRowIds);
        // Keep the current anchor as the "most recent" for data binding (Excel behavior)
        setLastSelectedRowId(currentAnchor);
        // Preserve the anchor
        setSelectionAnchorId(currentAnchor);
        // Mark that we're in select-all mode for special anchor handling
        setIsSelectAllActive(true);

        // Notify callbacks about the selection change
        if (onSelectionChange) {
          onSelectionChange(allRowIds, currentAnchor);
        }
        if (onRowSelect) {
          // Data binding should use anchor row (Excel behavior)
          onRowSelect(currentAnchor);
        }
      }
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
    dataSourcesModeDict,
    dragSelection,
    setIsSelectAllActive,
    maxRowSize,
    getHorizontalNeighbor,
    getVerticalNeighbor,
    getMainRowIds
  ]);

  // Helper function to find the next adjacent anchor when current anchor is unselected
  const findNewAnchor = useCallback((originalAnchorId, remainingRowIds) => {
    const allRowIds = getAllRowIds();
    const anchorIndex = allRowIds.indexOf(originalAnchorId);
    const remainingIndices = remainingRowIds.map(id => allRowIds.indexOf(id)).filter(idx => idx !== -1);

    if (remainingIndices.length === 0) return null;

    const minIndex = Math.min(...remainingIndices);
    const maxIndex = Math.max(...remainingIndices);

    let newAnchorIndex;
    if (anchorIndex < minIndex) {
      // Anchor was at the beginning, next anchor should be minIndex (next adjacent row)
      newAnchorIndex = minIndex;
    } else if (anchorIndex > maxIndex) {
      // Anchor was at the end, next anchor should be maxIndex (next adjacent row)
      newAnchorIndex = maxIndex;
    } else {
      // Anchor was in the middle, find the closest adjacent row in the direction
      const lowerAdjacent = remainingIndices.filter(idx => idx < anchorIndex);
      const upperAdjacent = remainingIndices.filter(idx => idx > anchorIndex);

      // Prefer the next row in the same direction as the active row (from shift selection)
      if (upperAdjacent.length > 0) {
        newAnchorIndex = Math.min(...upperAdjacent);
      } else if (lowerAdjacent.length > 0) {
        newAnchorIndex = Math.max(...lowerAdjacent);
      } else {
        newAnchorIndex = remainingIndices[0];
      }
    }

    return allRowIds[newAnchorIndex];
  }, [getAllRowIds]);

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
    let newAnchor = selectionAnchorId;

    if (isShift && selectionAnchorId) {
      if (maxRowSize > 1) {
        // Join scenario: Select rectangular block
        const anchorInfo = getSubRowInfo(selectionAnchorId);
        const targetInfo = getSubRowInfo(rowId);

        if (anchorInfo && targetInfo) {
          const minVisualIndex = Math.min(anchorInfo.visualIndex, targetInfo.visualIndex);
          const maxVisualIndex = Math.max(anchorInfo.visualIndex, targetInfo.visualIndex);
          const minGroupIndex = Math.min(anchorInfo.groupIndex, targetInfo.groupIndex);
          const maxGroupIndex = Math.max(anchorInfo.groupIndex, targetInfo.groupIndex);

          const rectangularSelection = [];
          for (let vIndex = minVisualIndex; vIndex <= maxVisualIndex; vIndex++) {
            for (let gIndex = minGroupIndex; gIndex <= maxGroupIndex; gIndex++) {
              const subRow = activeRows[vIndex]?.[gIndex];
              if (subRow && subRow['data-id']) {
                rectangularSelection.push(subRow['data-id']);
              }
            }
          }

          if (isCtrl) {
            // Ctrl+Shift: extend selection by rectangular block
            nextSelected = Array.from(new Set([...(selectedRows || []), ...rectangularSelection]));
          } else {
            // Shift only: replace with rectangular block, keep original anchor fixed
            nextSelected = rectangularSelection;
          }
        }
      } else {
        // Non-join scenario: Use traditional range selection
        const range = getRowRange(selectionAnchorId, rowId);
        if (isCtrl) {
          // Ctrl+Shift: extend selection by range
          nextSelected = Array.from(new Set([...(selectedRows || []), ...range]));
        } else {
          // Shift only: replace with range, keep original anchor fixed
          nextSelected = range;
        }
      }
      // DON'T update anchor - keep original anchor for Excel-like behavior
      // The anchor should remain the same for visual distinction (dark vs light)
    } else if (isCtrl) {
      // Ctrl: toggle single
      const set = new Set(selectedRows || []);
      const wasSelected = set.has(rowId);

      if (wasSelected) {
        set.delete(rowId);
        // When unselecting the anchor, check if this was from a range selection
        if (set.size > 0 && rowId === selectionAnchorId) {
          const remainingRows = Array.from(set);
          const allRowIds = getAllRowIds();

          // Special case: If we're unselecting from a Ctrl+A state, use topmost element as new anchor
          if (isSelectAllActive) {
            const remainingIndices = remainingRows
              .map(id => ({ id, index: allRowIds.indexOf(id) }))
              .filter(item => item.index !== -1)
              .sort((a, b) => a.index - b.index);

            newAnchor = remainingIndices.length > 0 ? remainingIndices[0].id : null;
            setIsSelectAllActive(false); // Turn off the flag after first anchor change
          } else {
            // Existing logic for other cases
            const remainingIndices = remainingRows.map(id => allRowIds.indexOf(id)).filter(idx => idx !== -1).sort((a, b) => a - b);

            // Only use adjacent row logic for likely range selections (large, mostly contiguous selections)
            const isLikelyRangeSelection = remainingIndices.length >= 2 &&
              (remainingIndices[remainingIndices.length - 1] - remainingIndices[0]) <= remainingIndices.length + 1;

            if (isLikelyRangeSelection) {
              // Range selection: use adjacent row logic
              newAnchor = findNewAnchor(selectionAnchorId, remainingRows);
            } else {
              // Regular Ctrl+click selection: use selection order (last remaining)
              newAnchor = remainingRows[remainingRows.length - 1];
            }
          }
        } else if (set.size > 0) {
          // Non-anchor unselect: keep existing anchor or use last remaining
          if (!set.has(selectionAnchorId)) {
            const remainingRows = Array.from(set);
            newAnchor = remainingRows[remainingRows.length - 1];
          }
        } else {
          newAnchor = null;
        }
      } else {
        set.add(rowId);
        // When adding, the newly added row becomes the anchor
        newAnchor = rowId;
      }
      nextSelected = Array.from(set);
    } else {
      // Plain click: single select
      nextSelected = [rowId];
      newAnchor = rowId;
    }

    // Update state
    if (setSelectedRows) setSelectedRows(nextSelected);
    if (setSelectionAnchorId && newAnchor) setSelectionAnchorId(newAnchor);

    // Determine correct data binding row based on operation type
    let dataBindingRowId;
    if (isShift && selectionAnchorId) {
      // Shift+Click: use original anchor
      dataBindingRowId = selectionAnchorId;
    } else if (isCtrl) {
      const wasSelected = (selectedRows || []).includes(rowId);
      if (wasSelected && nextSelected.length > 0) {
        // Ctrl+Click unselect: use new anchor
        dataBindingRowId = newAnchor;
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
    if (onRowSelect) onRowSelect(dataBindingRowId);

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
    dataSourcesModeDict,
    findNewAnchor,
    isSelectAllActive,
    maxRowSize,
    getAllRowIds
  ]);

  // Drag selection handlers (only when enabled)
  const handleRowMouseDown = useCallback((e, rowId) => {
    if (!dragSelection || mode !== MODES.READ) return;

    // Only start drag if it's not a modifier click
    if (e.ctrlKey || e.metaKey || e.shiftKey) {
      return;
    }
    setIsDragging(true);
    wasDraggedRef.current = false;
    // For drag start, preserve the real event modifiers
    handleRowClick(e, rowId);
    tableWrapperRef?.current?.focus({ preventScroll: true });
  }, [dragSelection, mode, handleRowClick, tableWrapperRef]);

  const handleRowMouseEnter = useCallback((e, rowId) => {
    if (!dragSelection || !isDragging || mode !== MODES.READ) return;

    wasDraggedRef.current = true;
    // Treat mouse enter during drag as a shift-click to extend selection
    const mockEvent = { ctrlKey: false, metaKey: false, shiftKey: true };
    handleRowClick(mockEvent, rowId);
  }, [dragSelection, isDragging, mode, handleRowClick]);

  const handleRowMouseClick = useCallback((e, rowId) => {
    if (!dragSelection) {
      // If drag selection is disabled, just use the regular click handler
      return handleRowClick(e, rowId);
    }
    // If it was a genuine click (not a drag), let the hook handle it with real modifiers
    if (!wasDraggedRef.current) {
      handleRowClick(e, rowId);
    }
    // Always reset drag state after click
    wasDraggedRef.current = false;
  }, [dragSelection, handleRowClick]);

  return {
    handleKeyDown,
    handleRowClick,
    ...(dragSelection && {
      handleRowMouseDown,
      handleRowMouseEnter,
      handleRowMouseClick,
      isDragging
    })
  };
};

export default useKeyboardNavigation;