import React, { useState, useEffect, useRef } from 'react';
import { ListItemIcon, ListItemText, Menu, MenuItem, Table, TableBody, TableContainer, TableRow, FormControl, InputLabel, Box } from '@mui/material';
import TableHead from '../../TableHead';
import Cell from '../../Cell';
import styles from './DataTable.module.css';
import { ClearAll, Save } from '@mui/icons-material';
import { getDataxpath, generateRowTrees } from '../../../utils';
import { cloneDeep, get, set } from 'lodash';
import { DB_ID, MODES, DATA_TYPES, MODEL_TYPES } from '../../../constants';
import { flux_toggle, flux_trigger_strat } from '../../../projectSpecificUtils';
import FullScreenModal from '../../Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../cards';
import { useSelector } from 'react-redux';
import DataTree from '../../trees/DataTree/DataTree';
import ClipboardCopier from '../../ClipboardCopier';
import Icon from '../../Icon';
import { useScrollIndicators } from '../../../hooks';
import TablePaginationControl from '../../TableControls/TablePaginationControl'
import ScrollIndicators from '../../TableControls/ScrollIndicators'

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
  onModeToggle,
}) => {
  const { schema: projectSchema } = useSelector((state) => state.schema);
  const [clipboardText, setClipboardText] = useState(null);
  const [selectedRows, setSelectedRows] = useState([]);
  const [lastSelectedRowId, setLastSelectedRowId] = useState(null);
  // const [contextMenuAnchorEl, setContextMenuAnchorEl] = useState(null);
  const [selectionAnchorId, setSelectionAnchorId] = useState(null);
  const [dataTree, setDataTree] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newlyAddedRowId, setNewlyAddedRowId] = useState(null);
  const [rowsBeforeUpdate, setRowsBeforeUpdate] = useState(null);
  const tableWrapperRef = useRef(null);

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

  const handleSortRequest = (e, property, retainSortLevel = false) => {
    let updatedSortOrders = cloneDeep(sortOrders);
    if (!retainSortLevel) {
      updatedSortOrders = updatedSortOrders.filter(o => o.order_by === property);
    }
    const sortOrder = updatedSortOrders.find(o => o.order_by === property);
    if (sortOrder) {
      // sort level already exists for this property
      sortOrder.sort_type = sortOrder.sort_type === 'asc' ? 'desc' : 'asc';
    } else {
      // add a new sort level
      updatedSortOrders.push({ order_by: property, sort_type: 'asc' });
    }
    onSortOrdersChange(updatedSortOrders);
  }

  const handleSortRemove = (property) => {
    const updatedSortOrders = sortOrders.filter(o => o.order_by !== property);
    onSortOrdersChange(updatedSortOrders);
  }

  const handleCopy = (column) => {
    const columnName = column.key;
    let sourceIndex = column.sourceIndex;
    if (sourceIndex === null || sourceIndex === undefined) {
      sourceIndex = 0;
    }
    const values = [columnName];
    rows.forEach((groupedRow) => {
      const row = groupedRow[sourceIndex];
      values.push(row[column.tableTitle]);
    })
    const text = values.join('\n');
    setClipboardText(text);
  }

  // const handleContextMenuOpen = (e) => {
  //     setContextMenuAnchorEl(e.currentTarget);
  // }

  // const handleContextMenuClose = () => {
  //     setContextMenuAnchorEl(null);
  // }

  // const handleClearAll = () => {
  //     setSelectedRows([]);
  //     handleContextMenuClose();
  // }

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
      const objId = selectedRows[0] ?? selectedId;
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
      setSelectedRows([rowId]);
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
          }, 3000);
        }
      }, 500)
    }
  }

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

  const getRowRange = (startRowId, endRowId) => {
    // Get all row IDs from activeRows
    const allRowIds = activeRows.map(groupedRow => groupedRow[0]['data-id']);
    const startIndex = allRowIds.indexOf(startRowId);
    const endIndex = allRowIds.indexOf(endRowId);
    if (startIndex === -1 || endIndex === -1) {
      return [endRowId];
    }
    const minIndex = Math.min(startIndex, endIndex);
    const maxIndex = Math.max(startIndex, endIndex);
    return allRowIds.slice(minIndex, maxIndex + 1);
  }

  const handleRowSelect = (e, rowId) => {
    // row select only allowed in READ mode
    if (mode !== MODES.READ) {
      return;
    }
    let updatedSelectedRows;

    if (e.shiftKey && e.ctrlKey && selectionAnchorId) {
      // Ctrl+Shift+Click: Add range to existing selection (Excel behavior)
      const range = getRowRange(selectionAnchorId, rowId);
      updatedSelectedRows = [...new Set([...selectedRows, ...range])];
    } else if (e.shiftKey && selectionAnchorId) {
      // Shift+Click: Select range from anchor, replacing previous selection (Excel behavior)
      updatedSelectedRows = getRowRange(selectionAnchorId, rowId);
    } else if (e.ctrlKey) {
      // Ctrl+Click: Toggle individual row selection
      if (selectedRows.find(row => row === rowId)) {
        updatedSelectedRows = selectedRows.filter(row => row !== rowId);
      } else {
        updatedSelectedRows = [...selectedRows, rowId];
      }
      setSelectionAnchorId(rowId);
    } else {
      // Regular click: Select single row and set as anchor
      updatedSelectedRows = [rowId];
      setSelectionAnchorId(rowId);
    }

    setSelectedRows(updatedSelectedRows);
    setLastSelectedRowId(rowId);

    if (modelType === MODEL_TYPES.REPEATED_ROOT) {
      if (updatedSelectedRows.length === 1) {
        onRowSelect(rowId);
      } else {
        onRowSelect(null);
      }
    }
  }

  const handleKeyDown = (event) => {
    const isCtrlPressed = event.ctrlKey || event.metaKey;

    // Ctrl+Shift+Up/Down to select to page start/end
    if (isCtrlPressed && event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;
      event.preventDefault();

      const allRowIdsOnPage = activeRows.map(groupedRow => groupedRow[0]['data-id']);
      if (allRowIdsOnPage.length === 0) return;

      // The anchor is the fixed point of the selection. If not set, use the first selected row or the top of the page.
      const currentAnchorId = selectionAnchorId || (selectedRows.length > 0 ? selectedRows[0] : allRowIdsOnPage[0]);
      if (!selectionAnchorId) {
        setSelectionAnchorId(currentAnchorId);
      }

      let targetRowId;
      if (event.key === 'ArrowDown') {
        // Select to the last row on the current page
        targetRowId = allRowIdsOnPage[allRowIdsOnPage.length - 1];
      } else { // ArrowUp
        // Select to the first row on the current page
        targetRowId = allRowIdsOnPage[0];
      }

      const newSelectedRange = getRowRange(currentAnchorId, targetRowId);
      setSelectedRows(newSelectedRange);
      setLastSelectedRowId(targetRowId); // The new "last selected" is the target at the page boundary
    }
    // Original Shift+Arrow logic, now in an else-if block
    else if (event.shiftKey && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      if (mode !== MODES.READ) return;

      event.preventDefault();
      const allRowIds = activeRows.map(groupedRow => groupedRow[0]['data-id']);
      if (allRowIds.length === 0) return;

      if (!lastSelectedRowId || !selectionAnchorId) {
        const firstRowId = allRowIds[0];
        setSelectedRows([firstRowId]);
        setLastSelectedRowId(firstRowId);
        setSelectionAnchorId(firstRowId);
        return;
      }

      const currentIndex = allRowIds.indexOf(lastSelectedRowId);
      if (currentIndex === -1) return;

      let nextIndex = event.key === 'ArrowDown'
        ? Math.min(currentIndex + 1, allRowIds.length - 1)
        : Math.max(currentIndex - 1, 0);

      if (nextIndex === currentIndex) return;

      const nextRowId = allRowIds[nextIndex];
      const newSelectedRange = getRowRange(selectionAnchorId, nextRowId);
      setSelectedRows(newSelectedRange);
      setLastSelectedRowId(nextRowId);
    }
    // MODIFIED: Original Ctrl+Arrow logic, now in an else-if block
    else if (isCtrlPressed && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();

      if (mode === MODES.EDIT) {
        if (!tableContainerRef.current) return;
        const container = tableContainerRef.current;
        switch (event.key) {
          case 'ArrowUp':
            const tbody = container.querySelector('tbody');
            if (tbody) {
              const firstRow = tbody.querySelector('tr:first-child');
              if (firstRow) {
                firstRow.scrollIntoView({ behavior: 'smooth', block: 'start' });
              } else {
                container.scrollTo({ top: 0, behavior: 'smooth' });
              }
            } else {
              container.scrollTo({ top: 0, behavior: 'smooth' });
            }
            break;
          case 'ArrowDown':
            const tbodyDown = container.querySelector('tbody');
            if (tbodyDown) {
              const lastRow = tbodyDown.querySelector('tr:last-child');
              if (lastRow) {
                lastRow.scrollIntoView({ behavior: 'smooth', block: 'end' });
              } else {
                container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
              }
            } else {
              container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
            }
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
      else if (mode === MODES.READ) {
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
          setSelectedRows([targetRowId]);
          setLastSelectedRowId(targetRowId);
          setSelectionAnchorId(targetRowId);
          if (modelType === MODEL_TYPES.REPEATED_ROOT) {
            onRowSelect(targetRowId);
          }

          setTimeout(() => {
            const tableContainer = tableContainerRef.current;
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
          }, 50);
        }
      }
    }
  };

  const handleRowDoubleClick = (e) => {
    if (mode === MODES.READ && !isReadOnly) {
      if (selectedRows.length !== 1) {
        return;
      } // else - single selected row
      if (!e.target.closest('button')) {
        onModeToggle();
      }
    }
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

  if (!activeRows || activeRows.length === 0) return null;

  // Calculate total pages for the select dropdown
  const totalPages = Math.ceil(rows.length / rowsPerPage);
  const pageOptions = Array.from({ length: totalPages }, (_, i) => i);

  // const isContextMenuOpen = Boolean(contextMenuAnchorEl);

  return (
    <div
      ref={tableWrapperRef}
      className={styles.dataTableWrapper}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div className={styles.tableContainerWrapper}>
        <TableContainer
          ref={tableContainerRef}
          className={styles.scrollableTableContainer}
          onScroll={checkHorizontalScroll}
        >
          <Table
            className={styles.table}
            size='medium'>
            <TableHead
              headCells={cells}
              mode={mode}
              sortOrders={sortOrders}
              onRequestSort={handleSortRequest}
              onRemoveSort={handleSortRemove}
              copyColumnHandler={handleCopy}
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
                  >
                    {cells.map((cell) => {
                      // Get row data based on the cell's source index.
                      const row = groupedRow[cell.sourceIndex];
                      const isSelected = row && (
                        modelType === MODEL_TYPES.ROOT
                          ? selectedRows.includes(row['data-id'])
                          : selectedRows.includes(row['data-id']) || selectedId === row['data-id']);
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

                      const dataxpath = getDataxpath(updatedData, xpath);
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
                          const joinedKeyCellRow = row.find(r => r?.[cell.tableTitle] !== null && r?.[cell.tableTitle] !== undefined);
                          if (joinedKeyCellRow) {
                            value = joinedKeyCellRow ? joinedKeyCellRow[cell.tableTitle] : undefined;
                          }
                        }
                      }

                      const isButtonDisabled = modelType === MODEL_TYPES.REPEATED_ROOT && (!isSelected || (isSelected && xpath?.startsWith('[')));
                      const rowIdx = modelType === MODEL_TYPES.REPEATED_ROOT ? row?.['data-id'] : row?.['data-id'] || cell.tableTitle;
                      const cellKey = `${rowIdx}_${cell.tableTitle}`

                      return (
                        <Cell
                          key={cellKey}
                          mode={mode}
                          selected={isSelected}
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
                          truncateDateTime={false}
                          modelType={modelType}
                          onForceSave={() => { }}
                          onRowSelect={handleRowSelect}
                          dataSourceId={modelType === MODEL_TYPES.ROOT ? selectedId : row?.['data-id']}
                          nullCell={isNullCell}
                          dataSourceColors={dataSourceColors}
                          onUpdate={handleUpdate}
                          onDoubleClick={handleCellDoubleClick}
                          onCheckboxChange={handleCheckboxToggle}
                          onSelectItemChange={handleSelectItemChange}
                          onAutocompleteOptionChange={handleAutocompleteChange}
                          onDateTimeChange={handleDateTimeChange}
                        />
                      );
                    })}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <ScrollIndicators
          showRightScrollIndicator={showRightScrollIndicator}
          showLeftScrollIndicator={showLeftScrollIndicator}
          indicatorRightOffset={indicatorRightOffset}
          onRightScrollClick={handleRightScrollClick}
          onLeftScrollClick={handleLeftScrollClick}
        />
      </div>

      {rows.length > 6 && (
        <TablePaginationControl
          rows={rows}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={onPageChange}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[25, 50, 100]} // Optional
        />
      )}
      <ClipboardCopier text={clipboardText} />
      {/* <Menu
                open={isContextMenuOpen}
                onClose={handleContextMenuClose}
            >
                <MenuItem dense onClick={handleClearAll}>
                    <ListItemIcon>
                        <ClearAll fontSize='small' />
                    </ListItemIcon>
                    <ListItemText>Clear All</ListItemText>
                </MenuItem>
            </Menu> */}
      <FullScreenModal
        id={`${modelName}-modal`}
        open={isModalOpen}
        onClose={handleModalToggle}
      >
        <ModelCard>
          <ModelCardHeader name={modelName}>
            <Icon name='save' title='save' onClick={handleModalToggle}><Save fontSize='small' /></Icon>
          </ModelCardHeader>
          <ModelCardContent>
            <DataTree
              projectSchema={projectSchema}
              modelName={modelName}
              updatedData={modelType === MODEL_TYPES.REPEATED_ROOT ? dataTree : updatedData}
              storedData={modelType === MODEL_TYPES.REPEATED_ROOT ? (storedData.find((o) => o[DB_ID] === selectedRows[0]) || {}) : storedData}
              subtree={modelType === MODEL_TYPES.REPEATED_ROOT ? null : dataTree}
              mode={mode}
              xpath={modelRootPath}
              onUpdate={handleUpdate}
              onUserChange={handleUserChange}
              selectedId={selectedId}
              treeLevel={10}
            />
          </ModelCardContent>
        </ModelCard>
      </FullScreenModal>
    </div>
  )
}

export default DataTable;