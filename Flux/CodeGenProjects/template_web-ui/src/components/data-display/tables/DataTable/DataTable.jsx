import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableContainer from '@mui/material/TableContainer';
import TableRow from '@mui/material/TableRow';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Box from '@mui/material/Box';
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
import TableHeader from '../TableHeader';
import Cell from '../Cell';
import styles from './DataTable.module.css';
import ClearAll from '@mui/icons-material/ClearAll';
import Save from '@mui/icons-material/Save';
import { getDataxpathV2, generateRowTrees, clearxpath } from '../../../../utils/core/dataAccess';
import { copyToClipboard } from '../../../../utils/core/stringUtils';
import { cloneDeep, get, set } from 'lodash';
import { DB_ID, MODES, DATA_TYPES, MODEL_TYPES, MIN_ROWS_FOR_PAGINATION } from '../../../../constants';
import { flux_toggle, flux_trigger_strat } from '../../../../projectSpecificUtils';
import FullScreenModal from '../../../ui/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../../utility/cards';
import DataTree from '../../trees/DataTree';
import Icon from '../../../ui/Icon';
import { useScrollIndicators, useKeyboardNavigation } from '../../../../hooks';
import TablePaginationControl from '../../../controls/table-controls/TablePaginationControl';
import ScrollIndicators from '../../../controls/table-controls/ScrollIndicators';
import { ContextMenu } from '../../../ui/ContextMenu';
import { hasButttonActions, aggregateButtonActionsByType } from '../../../../utils/bulkPatchUtils';
// import { useBoundaryScrollDetection } from '../../../hooks';

const DataTable = ({
  rows,
  activeRows,
  cells,
  mode,
  sortOrders,
  page,
  rowsPerPage,
  dataSourceColors,
  selectedId,
  modelType,
  storedData,
  updatedData,
  modelName,
  modelRootPath,
  fieldsMetadata,
  isReadOnly,
  onSortOrdersChange,
  onPageChange,
  onRowsPerPageChange,
  onUpdate,
  onUserChange,
  onRowSelect,
  onButtonToggle,
  onBulkPatch,
  onSelectiveButtonPatch,
  availableButtons = {},
  onModeToggle,
  onColumnOrdersChange,
  stickyHeader = true,
  frozenColumns,
  filters,
  onFiltersChange,
  uniqueValues,
  highlightDuration,
  maxRowSize,
  copyHeaders = true,
  selectedRows: externalSelectedRows,
  lastSelectedRowId: externalLastSelectedRowId,
  onSelectionChange: externalOnSelectionChange,
  totalCount,
  serverSideFilterSortEnabled,
}) => {

  const { schema: projectSchema } = useSelector((state) => state.schema);
  // Local state for immediate UI feedback
  const [localSelectedRows, setLocalSelectedRows] = useState([]);
  const [localLastSelectedRowId, setLocalLastSelectedRowId] = useState(null);
  const [contextMenuAnchorEl, setContextMenuAnchorEl] = useState(null);
  const [selectionAnchorId, setSelectionAnchorId] = useState(null);
  const [dataTree, setDataTree] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newlyAddedRowId, setNewlyAddedRowId] = useState(null);
  const [rowsBeforeUpdate, setRowsBeforeUpdate] = useState(null);
  const [columns, setColumns] = useState(cells);
  const [columnWidths, setColumnWidths] = useState({});
  const columnRefs = useRef({});
  const tableWrapperRef = useRef(null);

  // const { containerRef, isScrollable, enableScrolling, disableScrolling } = useBoundaryScrollDetection();

  useEffect(() => {
    setColumns(cells);
  }, [cells])

  // Ref to prevent infinite sync loops during internal updates
  const preventSyncRef = useRef(false);

  // Sync local state with external props when they change (from parent/chart)
  useEffect(() => {
    if (preventSyncRef.current) {
      return; // Skip sync if we're in the middle of internal selection changes
    }

    if (externalSelectedRows !== undefined) {
      setLocalSelectedRows(externalSelectedRows);
    }
    if (externalLastSelectedRowId !== undefined) {
      setLocalLastSelectedRowId(externalLastSelectedRowId);
    }
  }, [externalSelectedRows, externalLastSelectedRowId]);

  // Profile change detection - reset selections when layout profile changes
  const currentProfileId = useSelector(state => state.ui_layout?.storedUILayoutObj?.profile_id);
  const prevProfileIdRef = useRef(currentProfileId);
  
  //on profile change resetting all selection points
  useEffect(() => {
    if (prevProfileIdRef.current && prevProfileIdRef.current !== currentProfileId) {
      setLocalSelectedRows([]);
      setLocalLastSelectedRowId(null);
      setSelectionAnchorId(null);
      if (externalOnSelectionChange) {
        externalOnSelectionChange([], null);
      }
      prevProfileIdRef.current = currentProfileId;
    } else if (!prevProfileIdRef.current) {
      // Initialize ref on first render
      prevProfileIdRef.current = currentProfileId;
    }
  }, [currentProfileId, externalOnSelectionChange]);

  // Internal selection handler that provides immediate UI feedback
  const handleSelectionChange = (newSelectedRows, mostRecentId = null) => {
    // Prevent prop sync while we're updating selection internally
    preventSyncRef.current = true;

    // Update local state first for immediate UI feedback
    setLocalSelectedRows(newSelectedRows);
    setLocalLastSelectedRowId(mostRecentId || (newSelectedRows.length > 0 ? newSelectedRows[newSelectedRows.length - 1] : null));

    // Notify parent component asynchronously
    if (externalOnSelectionChange) {
      externalOnSelectionChange(newSelectedRows, mostRecentId);
    }

    // Allow prop sync again after a brief delay
    setTimeout(() => {
      preventSyncRef.current = false;
    }, 50);
  };

  // Sort sensors for drag-and-drop
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 10 } })
  );

  // Measure column widths after render
  useEffect(() => {
    const widths = {};
    cells.forEach(column => {
      if (columnRefs.current[column.tableTitle]) {
        widths[column.tableTitle] = columnRefs.current[column.tableTitle].getBoundingClientRect().width;
      }
    });
    setColumnWidths(widths);
  }, [columns]);

  const handleDragEnd = (event) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = cells.findIndex((col) => col.tableTitle === active.id);
      const newIndex = cells.findIndex((col) => col.tableTitle === over?.id);

      const reorderedColumns = arrayMove(cells, oldIndex, newIndex);
      const columnOrders = reorderedColumns.map(
        (column, index) => ({
          column_name: column.tableTitle,
          sequence: index
        })
      );
      setColumns(reorderedColumns);
      onColumnOrdersChange(columnOrders);
    }
  };

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
          const value = rowData?.[col.tableTitle];

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

  // Use the keyboard navigation hook
  const {
    handleKeyDown,
    handleRowClick,
    handleRowMouseDown,
    handleRowMouseEnter,
    handleRowMouseClick,
    isDragging,
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
    // DataTable specific state - using local state for immediate UI feedback
    selectedRows: localSelectedRows,
    lastSelectedRowId: localLastSelectedRowId,
    selectionAnchorId,
    setSelectedRows: setLocalSelectedRows,
    setLastSelectedRowId: setLocalLastSelectedRowId,
    setSelectionAnchorId,
    getRowRange,
    modelType,
    tableWrapperRef
  });


  const handleButtonClick = (e, action, xpath, value, dataSourceId, source = null, force = false) => {
    if (action === 'flux_toggle') {
      const updatedValue = flux_toggle(value);
      onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
    } else if (action === 'flux_trigger_strat') {
      const updatedValue = flux_trigger_strat(value);
      if (updatedValue) {
        onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
      }
    }
  }

  const handleFormUpdate = (xpath, dataxpath, value, dataSourceId, validationRes = null) => {
    let updatedObj;
    if (modelType === MODEL_TYPES.REPEATED_ROOT) {
      const objId = localSelectedRows[0] ?? selectedId;
      updatedObj = cloneDeep(updatedData.find((o) => o[DB_ID] === objId));
    } else {
      updatedObj = cloneDeep(updatedData);
    }
    set(updatedObj, dataxpath, value);
    if (onUpdate) {
      onUpdate(updatedObj);
    }
    const changeDict = {
      [DB_ID]: dataSourceId,
      [xpath]: value
    }
    if (onUserChange) {
      onUserChange(xpath, changeDict, validationRes, null);
    }
  }

  const handleTextChange = (e, type, xpath, value, dataxpath, validationRes, dataSourceId, source = null) => {
    if (value === '') {
      value = null;
    }
    if (type === DATA_TYPES.NUMBER) {
      if (value !== null) {
        value = value * 1;
      }
    }
    handleFormUpdate(xpath, dataxpath, value, dataSourceId, validationRes);
  }

  const handleSelectItemChange = (e, dataxpath, xpath, dataSourceId, source = null) => {
    const value = e.target.value;
    handleFormUpdate(xpath, dataxpath, value, dataSourceId);
  }

  const handleAutocompleteChange = (e, value, dataxpath, xpath, dataSourceId, source = null) => {
    handleFormUpdate(xpath, dataxpath, value, dataSourceId);
  }

  const handleCheckboxToggle = (e, dataxpath, xpath, dataSourceId, source = null) => {
    const value = e.target.checked;
    handleFormUpdate(xpath, dataxpath, value, dataSourceId);
  }

  const handleDateTimeChange = (dataxpath, xpath, value, dataSourceId, source = null) => {
    handleFormUpdate(xpath, dataxpath, value, dataSourceId);
  }

  const handleCellDoubleClick = (e, rowId, xpath) => {
    if (mode === MODES.EDIT) {
      setIsModalOpen(true);
      handleSelectionChange([rowId], rowId);

      if (modelType === MODEL_TYPES.REPEATED_ROOT) {
        const updatedTreeObj = updatedData.find((o) => o['data-id'] === rowId);
        setDataTree(updatedTreeObj ?? {});
        onRowSelect(rowId);
      } else {
        const updatedTrees = generateRowTrees(cloneDeep(updatedData), fieldsMetadata, modelRootPath);
        const updatedTreeObj = updatedTrees.find((o) => o['data-id'] === rowId);
        setDataTree(updatedTreeObj ?? {});
      }

      setTimeout(() => {
        const modalId = `${modelName}-modal`;
        const element = document.getElementById(modalId).querySelectorAll("[data-xpath='" + xpath + "']")[0];
        if (element) {
          element.classList.add(styles.highlight);
          element.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
          setTimeout(() => {
            element.classList.remove(styles.highlight);
          }, 2500);
        }
      }, 1200);
    }
  };

  const handleUpdate = (updatedObj, updateType) => {
    if (updateType === 'add' || updateType === 'remove') {
      setIsModalOpen(false);
    }

    // Capture current rows before update for comparison
    if (updateType === 'add') {
      setRowsBeforeUpdate([...rows]);
    }

    // Call parent update function first to trigger re-render
    if (onUpdate) {
      onUpdate(updatedObj);
    }
  }

  const handleUserChange = (xpath, changeDict, validationRes, source = null) => {
    if (onUserChange) {
      onUserChange(xpath, changeDict, validationRes, source);
    }
  }

  const handleRowSelect = (e, rowId) => {
    // This is called from Cell components for regular row selection (not drag)
    // Call the underlying row click handler directly
    handleRowClick(e, rowId);
  }

  const handleRowDoubleClick = (e) => {
    if (mode === MODES.READ && !isReadOnly) {
      if (localSelectedRows.length !== 1) {
        return;
      } // else - single selected row
      if (!e.target.closest('button')) {
        onModeToggle();
      }
    }
  }

  const handleContextMenu = (e) => {

    // // ALWAYS prevent default context menu and stop propagation immediately
    e.preventDefault();
    // e.stopPropagation();

    // Show context menu if 1+ rows are selected
    if (localSelectedRows.length >= 1) {
      // Store the cursor position for anchor positioning
      setContextMenuAnchorEl({
        clientX: e.clientX,
        clientY: e.clientY,
      });
    }
  }

  const handleContextMenuClose = () => {
    setContextMenuAnchorEl(null);
  }

 
  const handleRowsPerPageChange = (e) => {
    const updatedRowsPerPage = parseInt(e.target.value, 10);
    onRowsPerPageChange(updatedRowsPerPage);
  }

  const handlePageSelectChange = (e) => {
    const selectedPage = parseInt(e.target.value, 10);
    onPageChange(selectedPage);
  }

  const handleModalToggle = (e, reason) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
    setIsModalOpen((prev) => !prev);
  }

  // ADDED: Effect to compare rows before/after update to find new row
  useEffect(() => {
    if (rowsBeforeUpdate && rows.length > rowsBeforeUpdate.length) {

      // Find rows that exist in new but not in old
      const newRowIndices = [];
      rows.forEach((row, index) => {
        const existsInOld = rowsBeforeUpdate.some(oldRow =>
          JSON.stringify(oldRow) === JSON.stringify(row)
        );
        if (!existsInOld) {
          newRowIndices.push(index);
        }
      });

      if (newRowIndices.length > 0) {
        // Use the first new row found
        const newRowIndex = newRowIndices[0];
        setNewlyAddedRowId(newRowIndex);
      }

      // Clear the before update state
      setRowsBeforeUpdate(null);
    }
  }, [rows, rowsBeforeUpdate]);

  // ADDED: Effect to navigate to the correct page for a new row
  useEffect(() => {

    if (newlyAddedRowId !== null && rows.length > 0) {

      // Since we're using row index, we can directly calculate the page
      const rowIndex = typeof newlyAddedRowId === 'number' ? newlyAddedRowId : -1;

      if (rowIndex >= 0 && rowIndex < rows.length) {
        const targetPage = Math.floor(rowIndex / rowsPerPage);

        if (targetPage !== page) {
          onPageChange(targetPage);
        } else {
          console.log('Already on correct page');
        }
      } else {
        console.log('Invalid row index:', rowIndex);
      }
    }
  }, [rows, newlyAddedRowId, page, rowsPerPage, onPageChange]);

  // Effect to scroll to and highlight the new row once it's on the visible page
  useEffect(() => {
    if (newlyAddedRowId !== null && typeof newlyAddedRowId === 'number') {

      // Calculate which page the row should be on
      const targetPage = Math.floor(newlyAddedRowId / rowsPerPage);
      // Check if we're on the correct page for this row index
      const startRowIndex = page * rowsPerPage;
      const endRowIndex = startRowIndex + rowsPerPage - 1;
      const isRowOnCurrentPage = newlyAddedRowId >= startRowIndex && newlyAddedRowId <= endRowIndex;


      if (isRowOnCurrentPage) {
        setTimeout(() => {
          const tableContainer = tableContainerRef.current;
          if (tableContainer) {
            // Calculate the row index within the current page
            const rowIndexOnPage = newlyAddedRowId - startRowIndex;
            const newRowElement = tableContainer.querySelector(`tbody tr:nth-child(${rowIndexOnPage + 1})`);
            if (newRowElement) {
              newRowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

              newRowElement.classList.add(styles.highlight);
              setTimeout(() => {
                if (newRowElement) {
                  newRowElement.classList.remove(styles.highlight);
                }
              }, 3000);
            }
          }
          setNewlyAddedRowId(null);
        }, 150);
      }
    }
  }, [activeRows, newlyAddedRowId, page, rowsPerPage]);

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

  const handleClick = () => {
    // enableScrolling();
  }

  const handleDoubleClick = () => {
    // disableScrolling();
  }

  // Calculate available buttons from currently selected rows
  const calculatedAvailableButtons = React.useMemo(() => {
    if (!localSelectedRows || localSelectedRows.length === 0 || !rows || !cells) {
      return {};
    }

    // Find the actual row data for each selected row ID
    const selectedRowData = [];
    localSelectedRows.forEach(selectedId => {
      for (const groupedRow of rows) {
        for (const subRow of groupedRow) {
          if (subRow && subRow['data-id'] === selectedId) {
            selectedRowData.push(subRow);
            break;
          }
        }
      }
    });

    // Now aggregate button actions from the selected rows
    return aggregateButtonActionsByType(
      localSelectedRows,
      selectedRowData,
      cells,
      fieldsMetadata,
      modelType
    );
  }, [localSelectedRows, rows, cells, fieldsMetadata, modelType]);

  if (!activeRows || activeRows.length === 0) return null;

  // Calculate total pages for the select dropdown
  const totalPages = Math.ceil(rows.length / rowsPerPage);
  const pageOptions = Array.from({ length: totalPages }, (_, i) => i);


  let tableContainerClasses = `${styles.container} ${isDragging ? styles.isDragging : ''}`;
  // if (!isScrollable) {
  //   tableContainerClasses += ` ${styles.no_scroll}`;
  // }

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
        // ref={containerRef}
        // onDoubleClick={handleDoubleClick}
        onClick={handleClick}
      >
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <Table
            className={styles.table}
            size='medium'>
            <TableHeader
              columns={columns}
              uniqueValues={uniqueValues}
              filters={filters}
              sortOrders={sortOrders}
              onFiltersChange={onFiltersChange}
              onSortOrdersChange={onSortOrdersChange}
              columnRefs={columnRefs}
              stickyHeader={stickyHeader}
              getStickyPosition={getStickyPosition}
              groupedRows={rows}
              serverSideFilterSortEnabled={serverSideFilterSortEnabled}
            />
            <TableBody>
              {activeRows.map((groupedRow, idx) => {
                const rowKey = groupedRow[0]['data-id'] ?? idx;

                return (
                  <TableRow
                    key={rowKey}
                    data-row-id={rowKey}
                    className={styles.row}
                    onDoubleClick={handleRowDoubleClick}
                    onContextMenu={handleContextMenu}
                  >
                    {columns.map((cell) => {
                      // Get row data based on the cell's source index.
                      const row = groupedRow[cell.sourceIndex];
                      const isSelected = row && (
                        modelType === MODEL_TYPES.ROOT
                          ? localSelectedRows.includes(row['data-id'])
                          : localSelectedRows.includes(row['data-id']) || selectedId === row['data-id']);
                      const isMostRecent = row && localLastSelectedRowId === row['data-id'];
                      const isNullCell = !row || (row && Object.keys(row).length === 0 && !cell.commonGroupKey);

                      let xpath = row?.['xpath_' + cell.key];
                      if (row && cell.tableTitle && cell.tableTitle.indexOf('.') > -1) {
                        xpath = row[cell.tableTitle.substring(0, cell.tableTitle.lastIndexOf('.')) + '.xpath_' + cell.key];
                      }

                      let disabled = false;
                      if (row) {
                        if (row[cell.tableTitle] === undefined) {
                          disabled = true;
                        } else if (mode === MODES.EDIT) {
                          if (cell && cell.ormNoUpdate && !row['data-add']) {
                            disabled = true;
                          } else if (cell.uiUpdateOnly && row['data-add']) {
                            disabled = true;
                          } else if (row['data-remove']) {
                            disabled = true;
                          }
                        }
                      }

                      const dataxpath = getDataxpathV2(updatedData, xpath);
                      const dataAdd = row?.['data-add'] ?? false;
                      const dataRemove = row?.['data-remove'] ?? false;
                      let value = row?.[cell.tableTitle];
                      let storedValue;
                      if (modelType === MODEL_TYPES.REPEATED_ROOT) {
                        if (row && isSelected) {
                          const storedObj = storedData.find((o) => o[DB_ID] === row['data-id']);
                          if (storedObj) {
                            storedValue = get(storedObj, xpath);
                          }
                        } else {
                          storedValue = get(storedData, xpath);
                        }
                      } else {
                        storedValue = get(storedData, xpath);
                      }
                      if (cell.joinKey || cell.commonGroupKey) {
                        if (!value) {
                          const joinedKeyCellRow = groupedRow?.find(r => r?.[cell.tableTitle] !== null && r?.[cell.tableTitle] !== undefined);
                          if (joinedKeyCellRow) {
                            value = joinedKeyCellRow ? joinedKeyCellRow[cell.tableTitle] : undefined;
                          }
                        }
                      }
                      const isButtonUpdateDisabled = cell.serverPopulate || cell.ormNoUpdate;
                      const isButtonDisabled = isButtonUpdateDisabled || (modelType === MODEL_TYPES.REPEATED_ROOT && (!isSelected || (isSelected && xpath?.startsWith('['))));
                      const rowIdx = modelType === MODEL_TYPES.REPEATED_ROOT ? row?.['data-id'] : row?.['data-id'] || cell.tableTitle;
                      const cellKey = `${rowIdx}_${cell.tableTitle}`;
                      const stickyPosition = getStickyPosition(cell.tableTitle);

                      return (
                        <Cell
                          key={cellKey}
                          mode={mode}
                          selected={isSelected}
                          mostRecent={isMostRecent}
                          rowindex={rowIdx}
                          name={cell.key}
                          elaborateTitle={cell.tableTitle}
                          currentValue={value}
                          previousValue={storedValue}
                          collection={cell}
                          xpath={xpath}
                          dataxpath={dataxpath}
                          dataAdd={dataAdd}
                          dataRemove={dataRemove}
                          disabled={disabled}
                          buttonDisable={isButtonDisabled}
                          onButtonClick={handleButtonClick}
                          onTextChange={handleTextChange}
                          index={selectedId}
                          forceUpdate={isModalOpen}
                          modelType={modelType}
                          onForceSave={() => { }}
                          onRowSelect={handleRowSelect}
                          onCellMouseDown={handleRowMouseDown}
                          onCellMouseEnter={handleRowMouseEnter}
                          onCellMouseClick={handleRowMouseClick}
                          dataSourceId={modelType === MODEL_TYPES.ROOT ? selectedId : row?.['data-id']}
                          nullCell={isNullCell}
                          dataSourceColors={dataSourceColors}
                          onUpdate={handleUpdate}
                          onDoubleClick={handleCellDoubleClick}
                          onCheckboxChange={handleCheckboxToggle}
                          onSelectItemChange={handleSelectItemChange}
                          onAutocompleteOptionChange={handleAutocompleteChange}
                          onDateTimeChange={handleDateTimeChange}
                          stickyPosition={stickyPosition}
                          highlightDuration={highlightDuration}
                        />
                      );
                    })}
                  </TableRow>
                )
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
      {
        (totalCount ?? rows.length) > MIN_ROWS_FOR_PAGINATION && (
          <TablePaginationControl
            rowsLength={totalCount ?? rows.length}
            page={page}
            rowsPerPage={rowsPerPage}
            onPageChange={onPageChange}
            onRowsPerPageChange={handleRowsPerPageChange}
            rowsPerPageOptions={[25, 50, 100]} // Optional
          />
        )
      }
      <FullScreenModal
        id={`${modelName}-modal`}
        open={isModalOpen}
        onClose={handleModalToggle}
      >
        <ModelCard>
          <ModelCardHeader name={modelName}>
            <Icon name='save' title='save' onClick={handleModalToggle}><Save fontSize='small' color='white' /></Icon>
          </ModelCardHeader>
          <ModelCardContent>
            <DataTree
              projectSchema={projectSchema}
              modelName={modelName}
              updatedData={modelType === MODEL_TYPES.REPEATED_ROOT ? dataTree : updatedData}
              storedData={modelType === MODEL_TYPES.REPEATED_ROOT ? (storedData.find((o) => o[DB_ID] === localSelectedRows[0]) || {}) : storedData}
              subtree={modelType === MODEL_TYPES.REPEATED_ROOT ? null : dataTree}
              mode={mode}
              xpath={modelRootPath}
              onUpdate={handleUpdate}
              onUserChange={handleUserChange}
              selectedId={selectedId}
              treeLevel={10}
              disablePagination={true}
            />
          </ModelCardContent>
        </ModelCard>
      </FullScreenModal>

      {/* Bulk Patch Context Menu - Right-click menu */}
      {onSelectiveButtonPatch && (
        <ContextMenu
          selectedRows={localSelectedRows}
          availableButtons={calculatedAvailableButtons}
          onSelectiveButtonPatch={onSelectiveButtonPatch}
          onClearSelection={() => {
            handleSelectionChange([], null);
            // For RepeatedRootModels, also clear the single objId selection
            if (modelType === MODEL_TYPES.REPEATED_ROOT && onRowSelect) {
              onRowSelect(null);
            }
          }}
          anchorEl={contextMenuAnchorEl}
          open={Boolean(contextMenuAnchorEl)}
          onClose={handleContextMenuClose}
        />
      )}
    </div>
  )
}

export default DataTable;