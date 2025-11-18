import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import { cloneDeep, get, set } from 'lodash';
import Autocomplete from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableContainer from '@mui/material/TableContainer';
import TableRow from '@mui/material/TableRow';
import TextField from '@mui/material/TextField';
import Download from '@mui/icons-material/Download';
import { ContextMenu } from '../../ui/ContextMenu';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
} from '@dnd-kit/sortable';
import { DB_ID, DATA_TYPES, MODES, MODEL_TYPES, MIN_ROWS_FOR_PAGINATION } from '../../../constants';
import TableHeader from '../tables/TableHeader';
import Cell from '../tables/Cell';
import { getBufferAbbreviatedOptionLabel } from '../../../utils/ui/uiUtils';
import { aggregateButtonActionsByType, hasButttonActions } from '../../../utils/bulkPatchUtils';
import { copyToClipboard } from '../../../utils/core/stringUtils';
import { clearxpath } from '../../../utils/core/dataAccess';
import styles from './AbbreviationMergeView.module.css';
import { flux_toggle, flux_trigger_strat } from '../../../projectSpecificUtils';
import { useScrollIndicators, useKeyboardNavigation } from '../../../hooks';
import TablePaginationControl from '../../controls/table-controls/TablePaginationControl';
import ScrollIndicators from '../../controls/table-controls/ScrollIndicators';

// import { useBoundaryScrollDetection } from '../../hooks';

/**
 * BufferedView renders an autocomplete dropdown and a load button
 * for buffered items. It is hidden if the `bufferedFieldMetadata.hide` flag is true.
 *
 * @component
 * @param {Object} props
 * @param {Object} props.bufferedFieldMetadata - Metadata for the buffered field (should include `hide` and `title`).
 * @param {Object} props.loadedFieldMetadata - Metadata for the loaded fields.
 * @param {Array} props.dataSourceStoredArray - Array of stored data for the data source.
 * @param {Array} props.modelAbbreviatedBufferItems - Array of buffered options.
 * @param {*} props.searchQuery - Current search query (may be a string or other type).
 * @param {function} props.onSearchQueryChange - Callback when the search query changes.
 * @param {function} props.onLoad - Callback invoked when the load button is clicked.
 * @returns {JSX.Element|null}
 */
const BufferedView = ({
  bufferedFieldMetadata,
  loadedFieldMetadata,
  dataSourceStoredArray,
  modelAbbreviatedBufferItems,
  searchQuery,
  onSearchQueryChange,
  onLoad,
}) => {
  // Return null if the buffered container should be hidden.
  if (bufferedFieldMetadata.hide) return null;

  return (
    <Box className={styles.dropdown_container}>
      <Autocomplete
        className={styles.autocomplete_dropdown}
        disableClearable
        multiple={true}
        getOptionLabel={(option) =>
          getBufferAbbreviatedOptionLabel(
            option,
            bufferedFieldMetadata,
            loadedFieldMetadata,
            dataSourceStoredArray
          )
        }
        options={modelAbbreviatedBufferItems}
        size="small"
        variant="outlined"
        value={searchQuery || []}
        onChange={onSearchQueryChange}
        renderInput={(params) => (
          <TextField {...params} label={bufferedFieldMetadata.title} />
        )}
      />
      <Button
        color="primary"
        className={styles.button}
        // Enable button only if searchQuery is truthy
        disabled={!searchQuery || searchQuery.length === 0}
        disableElevation
        variant="contained"
        onClick={onLoad}
      >
        <Download fontSize="small" />
      </Button>
    </Box>
  );
};

BufferedView.propTypes = {
  bufferedFieldMetadata: PropTypes.shape({
    hide: PropTypes.bool,
    title: PropTypes.string,
  }).isRequired,
  loadedFieldMetadata: PropTypes.object.isRequired,
  dataSourceStoredArray: PropTypes.array.isRequired,
  modelAbbreviatedBufferItems: PropTypes.array.isRequired,
  searchQuery: PropTypes.any,
  onSearchQueryChange: PropTypes.func.isRequired,
  onLoad: PropTypes.func.isRequired,
};

/**
 * LoadedView renders a table with active rows, including sort headers,
 * inline cell display/editing, and pagination. It processes cell data for
 * special types (e.g. progressBar) and handles value derivation.
 *
 * @component
 * @param {Object} props
 * @param {string} props.mode - Current view mode.
 * @param {Array} props.rows - All rows of data.
 * @param {Array} props.activeRows - Filtered rows to display.
 * @param {Array} props.cells - Array of cell definitions.
 * @param {Array} [props.sortOrders] - Array of current sort orders.
 * @param {function} props.onSortOrdersChange - Callback to update sort orders.
 * @param {Object} props.dataSourcesStoredArrayDict - Dictionary of stored data arrays.
 * @param {Object} props.dataSourcesUpdatedArrayDict - Dictionary of updated data arrays.
 * @param {string|number} [props.selectedId] - ID of the selected row.
 * @param {function} props.onForceSave - Callback to force save changes.
 * @param {Array} props.dataSourceColors - Array of data source colors.
 * @param {number} props.page - Current page index.
 * @param {number} props.rowsPerPage - Number of rows per page.
 * @param {function} props.onPageChange - Callback when page changes.
 * @param {function} props.onRowsPerPageChange - Callback when rows per page change.
 * @returns {JSX.Element|null}
 */
const LoadedView = ({
  mode,
  rows,
  activeRows,
  cells,
  sortOrders,
  onSortOrdersChange,
  dataSourcesStoredArrayDict,
  dataSourcesUpdatedArrayDict,
  selectedId,
  onForceSave,
  dataSourceColors,
  page,
  rowsPerPage,
  isReadOnly,
  onPageChange,
  onRowsPerPageChange,
  onRowSelect,
  onModeToggle,
  onUpdate,
  onButtonToggle,
  onUserChange,
  onColumnOrdersChange,
  onBulkPatch,
  stickyHeader = true,
  frozenColumns,
  filters,
  onFiltersChange,
  uniqueValues,
  highlightDuration,
  selectedRows,
  lastSelectedRowId,
  onSelectionChange,
  dataSourcesModeDict,
  copyHeaders = true,
  maxRowSize,
}) => {
  const [columns, setColumns] = useState(cells);
  const [columnWidths, setColumnWidths] = useState({});
  const [localSelectedRows, setLocalSelectedRows] = useState([]);
  const [localLastSelectedRowId, setLocalLastSelectedRowId] = useState(null);
  const [isMultiSelectActive, setIsMultiSelectActive] = useState(false);
  const columnRefs = useRef({});
  const tableWrapperRef = useRef(null);
  const preventSyncRef = useRef(false);

  // Use the scroll indicators hook
  const {
    showRightScrollIndicator,
    showLeftScrollIndicator,
    indicatorRightOffset,
    tableContainerRef,
    handleRightScrollClick,
    handleLeftScrollClick,
    checkHorizontalScroll,
  } = useScrollIndicators([activeRows, cells]);

  // Define getRowRange function for shift selection
  const getRowRange = (startId, endId) => {
    const allRowIds = [];
    for (const group of activeRows) {
      for (const sub of group) {
        if (sub && sub['data-id']) allRowIds.push(sub['data-id']);
      }
    }

    const s = allRowIds.indexOf(startId);
    const e = allRowIds.indexOf(endId);
    if (s === -1 || e === -1) return [endId];

    const [lo, hi] = [Math.min(s, e), Math.max(s, e)];
    return allRowIds.slice(lo, hi + 1);
  };

  const [selectionAnchorId, setSelectionAnchorId] = useState(null);

  // Handle multiselect changes - update local state and track multiselect mode
  const handleSelectionChange = (newSelectedRows, mostRecentId = null) => {
    // Prevent prop sync while we're updating selection internally
    preventSyncRef.current = true;

    setLocalSelectedRows(newSelectedRows);
    // Update multiselect mode based on selection size
    const newIsMultiSelectActive = newSelectedRows.length > 1;
    setIsMultiSelectActive(newIsMultiSelectActive);

    // Use provided mostRecentId or fallback to last in array
    const finalMostRecentId = mostRecentId || (newSelectedRows.length > 0
      ? newSelectedRows[newSelectedRows.length - 1]
      : null);

    // If switching back to single select, ensure proper state sync
    if (!newIsMultiSelectActive && newSelectedRows.length === 1) {
      setLocalLastSelectedRowId(finalMostRecentId);
    } else if (newSelectedRows.length === 0) {
      setLocalLastSelectedRowId(null);
      setIsMultiSelectActive(false);
    } else {
      setLocalLastSelectedRowId(finalMostRecentId);
    }

    // Notify parent (this connects to chart!)
    if (onSelectionChange) {
      onSelectionChange(newSelectedRows, finalMostRecentId);
    }

    // Allow prop sync again after a brief delay
    setTimeout(() => {
      preventSyncRef.current = false;
    }, 50);
  };

  const handleCopySelection = useCallback((selectedRowIds) => {
    if (!selectedRowIds || selectedRowIds.length === 0) return;

    // Recreate the row structure, but only with the selected sub-rows.
    const processedRows = rows.map(groupedRow =>
      groupedRow.map(subRow =>
        subRow && selectedRowIds.includes(subRow['data-id']) ? subRow : null
      )
    );

    // Filter out any main rows that now contain no selected sub-rows at all.
    const selectedGroups = processedRows.filter(group => group.some(item => item !== null));

    // Generate headers
    const headers = copyHeaders ? columns.map(col => col.tableTitle).join('\t') : null;

    // Generate the TSV rows by mapping over our new 'selectedGroups'
    const tsvRows = selectedGroups.map(groupedRow => {
      return columns
        .map(col => {
          // Use the column's sourceIndex to get the correct sub-row data.
          const rowData = groupedRow[col.sourceIndex];
          const value = rowData?.[col.key];

          // If value is object/array → clean xpath fields and stringify, else normal string
          let cellValue;
          if (value !== null && typeof value === 'object') {
            // Clone the value to avoid modifying the original data
            const cleanValue = cloneDeep(value);
            // Remove xpath fields before stringifying
            clearxpath(cleanValue);
            cellValue = JSON.stringify(cleanValue);
          } else {
            cellValue = String(value ?? '');
          }

          // Replace newlines so it stays single-line in TSV
          return cellValue.replace(/\n/g, ' ');
        })
        .join('\t');
    });

    // Combine headers and rows into a single string.
    const tsvString = [headers, ...tsvRows].filter(Boolean).join('\n');

    copyToClipboard(tsvString).then(() => {
      console.log('Selected rows copied to clipboard in TSV format.');
    }).catch(err => {
      console.error('Failed to copy selected rows to clipboard:', err);
    });

  }, [rows, columns, copyHeaders]);


  const {
    handleKeyDown,
    handleRowClick,
    handleRowMouseDown,
    handleRowMouseEnter,
    handleRowMouseClick,
    isDragging
  } = useKeyboardNavigation({
    mode,
    activeRows,
    columns,
    maxRowSize,
    tableContainerRef,
    capabilities: {
      editModeScrolling: true,
      readModeSelection: true,
      shiftSelection: true,
      ctrlShiftSelection: true,
      dragSelection: true,
      copySelection: true,
    },
    callbacks: {
      onRowSelect: onRowSelect,
      onSelectionChange: handleSelectionChange,
      onCopySelection: handleCopySelection,
    },
    selectedRows: localSelectedRows,
    lastSelectedRowId: localLastSelectedRowId,
    selectionAnchorId,
    setSelectedRows: setLocalSelectedRows,
    setLastSelectedRowId: setLocalLastSelectedRowId,
    setSelectionAnchorId,
    getRowRange,
    dataSourcesModeDict,
    tableWrapperRef
  });

  useEffect(() => {
    setColumns(cells);
  }, [cells])

  // Sync local state with parent props (bidirectional sync)
  useEffect(() => {
    if (preventSyncRef.current) {
      return; // Skip sync if we're in the middle of internal selection changes
    }

    // Sync from parent multiselect props to local state
    if (selectedRows && selectedRows.length > 0) {
      setLocalSelectedRows(selectedRows);
      setIsMultiSelectActive(selectedRows.length > 1);
      if (lastSelectedRowId) {
        setLocalLastSelectedRowId(lastSelectedRowId);
      }
    } else if (selectedId !== null && selectedId !== undefined) {
      // Fallback to single selection from selectedId prop
      if (!isMultiSelectActive) {
        setLocalSelectedRows([selectedId]);
        setLocalLastSelectedRowId(selectedId);
      }
    } else if (!isMultiSelectActive) {
      // Clear selection if no parent selection
      setLocalSelectedRows([]);
      setLocalLastSelectedRowId(null);
    }
  }, [selectedRows, lastSelectedRowId, selectedId, isMultiSelectActive]);

  // Surgical fix: Only clear table selection when chart changes (not when other components change)
  const prevSelectedRowsRef = useRef(selectedRows);
  useEffect(() => {
    // Only clear if we had selections before and now we don't (chart switch scenario)
    const hadSelectionsBefore = prevSelectedRowsRef.current && prevSelectedRowsRef.current.length > 0;
    const hasNoSelectionsNow = !selectedRows || selectedRows.length === 0;

    if (hadSelectionsBefore && hasNoSelectionsNow) {
      console.log('🔄 Chart switch detected - clearing only this table\'s local state');
      setLocalSelectedRows([]);
      setLocalLastSelectedRowId(null);
      setIsMultiSelectActive(false);
      setSelectionAnchorId(null);
    }

    // Update our reference for next comparison
    prevSelectedRowsRef.current = selectedRows;
  }, [selectedRows]);

  // Profile change detection - reset selections when layout profile changes
  const currentProfileId = useSelector(state => state.ui_layout?.storedUILayoutObj?.profile_id);
  const prevProfileIdRef = useRef(currentProfileId);

  //on profile change resetting all selection points
  useEffect(() => {
    if (prevProfileIdRef.current && prevProfileIdRef.current !== currentProfileId) {
      setLocalSelectedRows([]);
      setLocalLastSelectedRowId(null);
      setIsMultiSelectActive(false);
      setSelectionAnchorId(null);
      if (onSelectionChange) {
        onSelectionChange([], null);
      }
      prevProfileIdRef.current = currentProfileId;
    } else if (!prevProfileIdRef.current) {
      // Initialize ref on first render
      prevProfileIdRef.current = currentProfileId;
    }
  }, [currentProfileId, onSelectionChange]);

  // Sort sensors for drag-and-drop
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 10 } })
  );

  // Context menu state for bulk patch
  const [contextMenuAnchor, setContextMenuAnchor] = useState(null);

  const handleContextMenu = (e) => {
    // Show context menu if 1+ rows are selected
    if (localSelectedRows.length > 1) {
      e.preventDefault();
      e.stopPropagation();
      // Use cursor position for anchor instead of element reference
      setContextMenuAnchor({
        clientX: e.clientX,
        clientY: e.clientY,
      });
    }
  };

  const handleContextMenuClose = () => {
    setContextMenuAnchor(null);
  };

  const handleSelectiveButtonPatchClick = async (selectedRows, selectedButtonType) => {
    if (onBulkPatch) {
      await onBulkPatch(selectedRows, selectedButtonType);
    }
  };

  const handleClearSelection = () => {
    handleSelectionChange([], null);
  };

  // Calculate available buttons for selective patching
  const availableButtons = React.useMemo(() => {
    if (!localSelectedRows || localSelectedRows.length === 0) return {};

    // For AbbreviationMergeView, rows is a grouped structure: [groupedRow1, groupedRow2, ...]
    // Each groupedRow is [row1, row2, row3, ...] (one per data source)
    // We need to flatten this and find the rows matching our selected IDs
    const selectedRowData = [];

    for (const groupedRow of rows) {
      if (!Array.isArray(groupedRow)) {
        // Fallback if not grouped (shouldn't happen, but safe)
        if (localSelectedRows.includes(groupedRow['data-id'])) {
          selectedRowData.push(groupedRow);
        }
      } else {
        // Grouped row - check each sub-row
        for (const subRow of groupedRow) {
          if (subRow && localSelectedRows.includes(subRow['data-id'])) {
            selectedRowData.push(subRow);
          }
        }
      }
    }

    return aggregateButtonActionsByType(
      localSelectedRows,
      selectedRowData,
      cells,
      {}, // mergedFieldsMetadata - empty for now, will be enhanced later if needed
      MODEL_TYPES.ABBREVIATION_MERGE
    );
  }, [localSelectedRows, rows, cells]);

  // Measure column widths after render
  useEffect(() => {
    const widths = {};
    cells.forEach(column => {
      if (columnRefs.current[column.key]) {
        widths[column.key] = columnRefs.current[column.key].getBoundingClientRect().width;
      }
    });
    setColumnWidths(widths);
  }, [columns]);

  const handleDragEnd = (event) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = cells.findIndex((col) => col.key === active.id);
      const newIndex = cells.findIndex((col) => col.key === over?.id);

      const reorderedColumns = arrayMove(cells, oldIndex, newIndex);
      const columnOrders = reorderedColumns.map(
        (column, index) => ({
          column_name: column.key,
          sequence: index
        })
      );
      setColumns(reorderedColumns);
      onColumnOrdersChange(columnOrders);
    }
  };

  const handleButtonClick = useCallback((e, action, xpath, value, dataSourceId, source, force = false) => {
    if (action === 'flux_toggle') {
      const updatedValue = flux_toggle(value);
      onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
    } else if (action === 'flux_trigger_strat') {
      const updatedValue = flux_trigger_strat(value);
      if (updatedValue) {
        onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
      }
    }
  }, [onButtonToggle])

  const handleFormUpdate = (xpath, dataxpath, value, dataSourceId, validationRes = null, source) => {
    const updatedObj = cloneDeep(dataSourcesUpdatedArrayDict[source].find(o => o[DB_ID] === selectedId));
    if (updatedObj) {
      set(updatedObj, dataxpath, value);
      if (onUpdate) {
        onUpdate(updatedObj, source);
      }
      const changeDict = {
        [DB_ID]: dataSourceId,
        [xpath]: value
      }
      if (onUserChange) {
        onUserChange(xpath, changeDict, validationRes, source);
      }
    }
  }

  const handleTextChange = (e, type, xpath, value, dataxpath, validationRes, dataSourceId, source) => {
    if (value === '') {
      value = null;
    }
    if (type === DATA_TYPES.NUMBER) {
      if (value !== null) {
        value = value * 1;
      }
    }
    handleFormUpdate(xpath, dataxpath, value, dataSourceId, validationRes, source)

  }

  const handleRowDoubleClick = (e) => {
    if (mode === MODES.READ && !isReadOnly) {
      if (!e.target.closest('button')) {
        onModeToggle();
      }
    }
  };

  const handleCellRowSelect = (e, rowId) => {
    // This function will be called by Cell components for regular row selection (not drag)
    // Call the underlying row click handler directly
    handleRowClick(e, rowId);
  };

  const handlePageChange = (_, updatedPage) => {
    onPageChange(updatedPage);
  }

  const handleRowsPerPageChange = (e) => {
    const updatedRowsPerPage = parseInt(e.target.value, 10);
    onRowsPerPageChange(updatedRowsPerPage);
  }

  // Function to calculate left position for sticky columns
  const getStickyPosition = (columnId) => {
    if (!frozenColumns.includes(columnId)) return null;

    let leftPosition = 0;
    for (const id of frozenColumns) {
      if (id === columnId) break;
      // Approximate width for each preceding sticky column (adjust as needed)
      leftPosition += columnWidths[id] || 0;
    }
    return `${leftPosition}px`;
  }



  if (!activeRows || activeRows.length === 0) return null;

  let tableContainerClasses = `${styles.container} ${isDragging ? styles.isDragging : ''}`;

  return (
    <div
      ref={tableWrapperRef}
      className={styles.dataTableWrapper}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <TableContainer
        ref={tableContainerRef}
        className={tableContainerClasses}
        onScroll={checkHorizontalScroll}
        onContextMenu={handleContextMenu}
      >
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <Table className={styles.table} size='medium'>
            <TableHeader
              columns={columns}
              uniqueValues={uniqueValues}
              filters={filters}
              sortOrders={sortOrders}
              onFiltersChange={onFiltersChange}
              onSortOrdersChange={onSortOrdersChange}
              collectionView={true}
              columnRefs={columnRefs}
              stickyHeader={stickyHeader}
              getStickyPosition={getStickyPosition}
              groupedRows={rows}
            />
            <TableBody>
              {activeRows.map((groupedRow, rowIdx) => {
                let rowKey = groupedRow[0]['data-id'] ?? rowIdx;
                const dataSourcesStoredObjDict = {};

                return (
                  <TableRow
                    key={rowKey}
                    data-row-id={rowKey}
                    className={styles.row}
                    onDoubleClick={handleRowDoubleClick}
                  >
                    {columns.map((cell, cellIndex) => {
                      // Get row data based on the cell's source index.
                      const row = groupedRow[cell.sourceIndex];
                      const isNullCell = !row || (row && Object.keys(row).length === 0 && !cell.commonGroupKey);

                      // Update stored objects for this row.
                      if (row) {
                        Object.keys(dataSourcesStoredArrayDict).forEach((source) => {
                          dataSourcesStoredObjDict[source] =
                            dataSourcesStoredArrayDict[source].find(
                              (o) => o[DB_ID] === row['data-id']
                            );
                        });
                      }

                      const isSelected = row && localSelectedRows.includes(row['data-id']);
                      const isMostRecent = row && localLastSelectedRowId === row['data-id'];
                      const isButtonDisabled = row ? row['data-id'] !== selectedId : true;
                      const rowIdx = row ? row['data-id'] : cellIndex;

                      // Process cells of type 'progressBar'
                      const cellCopy = cloneDeep(cell);
                      if (cell.type === 'progressBar') {
                        // Process the minimum value if it's a string.
                        if (typeof cellCopy.min === DATA_TYPES.STRING) {
                          const min = cellCopy.min;
                          const source = min.split('.')[0];
                          cellCopy.minFieldName = min.split('.').pop();
                          const updatedArray = dataSourcesUpdatedArrayDict[source];
                          if (updatedArray && row) {
                            const updatedObj = updatedArray.find(
                              (o) => o[DB_ID] === row['data-id']
                            );
                            if (updatedObj) {
                              cellCopy.min = get(
                                updatedObj,
                                min.substring(min.indexOf('.') + 1)
                              );
                            }
                          }
                        }
                        // Process the maximum value if it's a string.
                        if (typeof cellCopy.max === DATA_TYPES.STRING) {
                          const max = cellCopy.max;
                          const source = max.split('.')[0];
                          cellCopy.maxFieldName = max.split('.').pop();
                          const updatedArray = dataSourcesUpdatedArrayDict[source];
                          if (updatedArray && row) {
                            const updatedObj = updatedArray.find(
                              (o) => o[DB_ID] === row['data-id']
                            );
                            if (updatedObj) {
                              cellCopy.max = get(
                                updatedObj,
                                max.substring(max.indexOf('.') + 1)
                              );
                            }
                          }
                        }
                      }

                      // Determine the value and stored value using the cell's xpath.
                      const xpath = cellCopy.xpath;
                      let value = row?.[cellCopy.key] ?? undefined;
                      let storedValue;
                      if (xpath.indexOf('-') !== -1) {
                        const storedValueArray = xpath
                          .split('-')
                          .map((path) =>
                            get(dataSourcesStoredObjDict[cellCopy.source], path)
                          )
                          .filter((val) => val !== null && val !== undefined);
                        storedValue = storedValueArray.join('-');
                      } else {
                        storedValue = get(dataSourcesStoredObjDict[cellCopy.source], xpath);
                      }
                      // If the cell is part of a joined group, attempt to derive a value.
                      if (cellCopy.joinKey || cellCopy.commonGroupKey) {
                        if (!value) {
                          const joinedKeyCellRow = groupedRow.find(
                            (r) =>
                              r?.[cellCopy.key] !== null && r?.[cellCopy.key] !== undefined
                          );
                          if (joinedKeyCellRow) {
                            value = joinedKeyCellRow[cellCopy.key];
                          }
                        }
                      }

                      const stickyPosition = getStickyPosition(cell.key);

                      return (
                        <Cell
                          // key={cellIndex}
                          key={`${rowKey}-${cell.key}-${cellIndex}`}
                          mode={mode}
                          selected={isSelected}
                          rowindex={rowIdx}
                          name={cellCopy.key}
                          elaborateTitle={cellCopy.tableTitle}
                          currentValue={value}
                          previousValue={storedValue}
                          collection={cellCopy}
                          xpath={xpath}
                          dataxpath={xpath}
                          dataAdd={false}
                          dataRemove={false}
                          disabled={false}
                          buttonDisable={isButtonDisabled}
                          ignoreDisable={true}
                          onButtonClick={handleButtonClick}
                          onTextChange={handleTextChange}
                          forceUpdate={mode === MODES.READ}
                          modelType={MODEL_TYPES.ABBREVIATION_MERGE}
                          onForceSave={onForceSave}
                          onRowSelect={handleCellRowSelect}
                          onCellMouseDown={handleRowMouseDown}
                          onCellMouseEnter={handleRowMouseEnter}
                          onCellMouseClick={handleRowMouseClick}
                          dataSourceId={row?.['data-id'] || null}
                          nullCell={isNullCell}
                          dataSourceColors={dataSourceColors}
                          onUpdate={() => { }}
                          onDoubleClick={() => { }}
                          onCheckboxChange={() => { }}
                          onSelectItemChange={() => { }}
                          onAutocompleteOptionChange={() => { }}
                          onDateTimeChange={() => { }}
                          stickyPosition={stickyPosition}
                          highlightDuration={highlightDuration}
                          mostRecent={isMostRecent}
                        />
                      );
                    })}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </DndContext>
      </TableContainer>

      <ScrollIndicators
        showRightScrollIndicator={showRightScrollIndicator}
        showLeftScrollIndicator={showLeftScrollIndicator}
        indicatorRightOffset={indicatorRightOffset}
        onRightScrollClick={handleRightScrollClick}
        onLeftScrollClick={handleLeftScrollClick}
      />
      {rows.length > MIN_ROWS_FOR_PAGINATION && (
        <TablePaginationControl
          rowsLength={rows.length}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={onPageChange}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[25, 50]}
        />
      )}

      {/* Context Menu for selective bulk patch operations */}

      <ContextMenu
        selectedRows={localSelectedRows}
        availableButtons={availableButtons}
        onSelectiveButtonPatch={handleSelectiveButtonPatchClick}
        onClearSelection={handleClearSelection}
        anchorEl={contextMenuAnchor}
        open={Boolean(contextMenuAnchor)}
        onClose={handleContextMenuClose}
        isLoading={false}
      />
    </div>
  );
};

LoadedView.propTypes = {
  mode: PropTypes.string.isRequired,
  rows: PropTypes.array.isRequired,
  activeRows: PropTypes.array.isRequired,
  cells: PropTypes.array.isRequired,
  sortOrders: PropTypes.array,
  dataSourcesStoredArrayDict: PropTypes.object.isRequired,
  dataSourcesUpdatedArrayDict: PropTypes.object.isRequired,
  selectedId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onForceSave: PropTypes.func.isRequired,
  dataSourceColors: PropTypes.array.isRequired,
  page: PropTypes.number.isRequired,
  rowsPerPage: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
  onRowsPerPageChange: PropTypes.func.isRequired,
  onBulkPatch: PropTypes.func,
};

/**
 * AbbreviationMergeView is the main component that renders the buffered view (for selecting
 * buffered items) and the loaded view (table of active rows). It also displays a divider with
 * the loaded field metadata title.
 *
 * @component
 * @param {Object} props
 * @param {Object} props.bufferedFieldMetadata - Metadata for the buffered field.
 * @param {Object} props.loadedFieldMetadata - Metadata for the loaded field (should include `title`).
 * @param {Array} props.dataSourceStoredArray - Array of stored data for the data source.
 * @param {Array} props.modelAbbreviatedBufferItems - Options for the buffered view.
 * @param {*} props.searchQuery - Current search query.
 * @param {function} props.onSearchQueryChange - Callback when the search query changes.
 * @param {function} props.onLoad - Callback to trigger loading.
 * @param {string} props.mode - Current view mode.
 * @param {Array} props.rows - All rows of data.
 * @param {Array} props.activeRows - Filtered active rows to display.
 * @param {Array} props.cells - Array of cell definitions.
 * @param {Array} [props.sortOrders] - Current sort orders.
 * @param {function} props.onSortOrdersChange - Callback to update sort orders.
 * @param {Object} props.dataSourcesStoredArrayDict - Dictionary of stored data arrays.
 * @param {Object} props.dataSourcesUpdatedArrayDict - Dictionary of updated data arrays.
 * @param {string|number} [props.selectedId] - ID of the selected row.
 * @param {function} props.onForceSave - Callback to force save changes.
 * @param {Array} props.dataSourceColors - Array of data source colors.
 * @param {number} props.page - Current page index.
 * @param {number} props.rowsPerPage - Number of rows per page.
 * @param {function} props.onPageChange - Callback when the page changes.
 * @param {function} props.onRowsPerPageChange - Callback when rows per page change.
 * @returns {JSX.Element}
 */
const AbbreviationMergeView = ({
  bufferedFieldMetadata,
  loadedFieldMetadata,
  dataSourceStoredArray,
  modelAbbreviatedBufferItems,
  searchQuery,
  onSearchQueryChange,
  onLoad,
  mode,
  rows,
  activeRows,
  cells,
  sortOrders,
  onSortOrdersChange,
  dataSourcesStoredArrayDict,
  dataSourcesUpdatedArrayDict,
  selectedId,
  onForceSave,
  dataSourceColors,
  page,
  rowsPerPage,
  isReadOnly,
  onPageChange,
  onRowsPerPageChange,
  onRowSelect,
  onModeToggle,
  onUpdate,
  onUserChange,
  onButtonToggle,
  onColumnOrdersChange,
  onBulkPatch,
  stickyHeader,
  frozenColumns,
  filters,
  onFiltersChange,
  uniqueValues,
  highlightDuration,
  selectedRows,
  lastSelectedRowId,
  onSelectionChange,
  dataSourcesModeDict,
  copyHeaders = true,
  maxRowSize,
}) => {
  return (
    <>
      {!isReadOnly && (
        <>
          <BufferedView
            bufferedFieldMetadata={bufferedFieldMetadata}
            loadedFieldMetadata={loadedFieldMetadata}
            dataSourceStoredArray={dataSourceStoredArray}
            modelAbbreviatedBufferItems={modelAbbreviatedBufferItems}
            searchQuery={searchQuery}
            onSearchQueryChange={onSearchQueryChange}
            onLoad={onLoad}
          />
          {/* <Divider textAlign='left'>
            <Chip label={loadedFieldMetadata.title} />
          </Divider> */}
        </>
      )}
      <LoadedView
        mode={mode}
        rows={rows}
        activeRows={activeRows}
        cells={cells}
        sortOrders={sortOrders}
        onSortOrdersChange={onSortOrdersChange}
        dataSourcesStoredArrayDict={dataSourcesStoredArrayDict}
        dataSourcesUpdatedArrayDict={dataSourcesUpdatedArrayDict}
        selectedId={selectedId}
        onForceSave={onForceSave}
        dataSourceColors={dataSourceColors}
        page={page}
        rowsPerPage={rowsPerPage}
        isReadOnly={isReadOnly}
        onPageChange={onPageChange}
        onRowsPerPageChange={onRowsPerPageChange}
        onRowSelect={onRowSelect}
        onModeToggle={onModeToggle}
        onUpdate={onUpdate}
        onUserChange={onUserChange}
        onButtonToggle={onButtonToggle}
        onColumnOrdersChange={onColumnOrdersChange}
        onBulkPatch={onBulkPatch}
        stickyHeader={stickyHeader}
        frozenColumns={frozenColumns}
        filters={filters}
        onFiltersChange={onFiltersChange}
        uniqueValues={uniqueValues}
        highlightDuration={highlightDuration}
        selectedRows={selectedRows}
        lastSelectedRowId={lastSelectedRowId}
        onSelectionChange={onSelectionChange}
        dataSourcesModeDict={dataSourcesModeDict}
        copyHeaders={copyHeaders}
        maxRowSize={maxRowSize}
      />
    </>
  );
};

AbbreviationMergeView.propTypes = {
  bufferedFieldMetadata: PropTypes.object.isRequired,
  loadedFieldMetadata: PropTypes.object.isRequired,
  dataSourceStoredArray: PropTypes.array.isRequired,
  modelAbbreviatedBufferItems: PropTypes.array.isRequired,
  searchQuery: PropTypes.any,
  onSearchQueryChange: PropTypes.func.isRequired,
  onLoad: PropTypes.func.isRequired,
  mode: PropTypes.string.isRequired,
  rows: PropTypes.array.isRequired,
  activeRows: PropTypes.array.isRequired,
  cells: PropTypes.array.isRequired,
  sortOrders: PropTypes.array,
  onSortOrdersChange: PropTypes.func.isRequired,
  dataSourcesStoredArrayDict: PropTypes.object.isRequired,
  dataSourcesUpdatedArrayDict: PropTypes.object.isRequired,
  selectedId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onForceSave: PropTypes.func.isRequired,
  dataSourceColors: PropTypes.array.isRequired,
  page: PropTypes.number.isRequired,
  rowsPerPage: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
  onRowsPerPageChange: PropTypes.func.isRequired,
  onBulkPatch: PropTypes.func,
};

export default AbbreviationMergeView;