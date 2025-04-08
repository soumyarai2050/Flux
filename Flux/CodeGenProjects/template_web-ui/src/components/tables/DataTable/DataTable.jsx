import React, { useState } from 'react';
import { ListItemIcon, ListItemText, Menu, MenuItem, Table, TableBody, TableContainer, TableRow, TablePagination } from '@mui/material';
import TableHead from '../../TableHead';
import Cell from '../../Cell';
import styles from './DataTable.module.css';
import { ClearAll } from '@mui/icons-material';
import { getDataxpath, generateRowTrees } from '../../../utils';
import { cloneDeep, get, set } from 'lodash';
import { DB_ID, MODES, DATA_TYPES, MODEL_TYPES } from '../../../constants';
import { flux_toggle, flux_trigger_strat } from '../../../projectSpecificUtils';
import FullScreenModal from '../../Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../cards';
import { useSelector } from 'react-redux';
import DataTree from '../../trees/DataTree/DataTree';
import ClipboardCopier from '../../ClipboardCopier';

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
  onModeToggle
}) => {
  const { schema: projectSchema } = useSelector((state) => state.schema);
  const [clipboardText, setClipboardText] = useState(null);
  const [selectedRows, setSelectedRows] = useState([]);
  // const [contextMenuAnchorEl, setContextMenuAnchorEl] = useState(null);
  const [dataTree, setDataTree] = useState({});
  const [isModalOpen, setIsModalOpen] = useState(false);

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
    // row select only allowed in READ mode
    if (mode !== MODES.READ) {
      return;
    }
    let updatedSelectedRows;
    if (e.ctrlKey) {
      if (selectedRows.find(row => row === rowId)) {
        // rowId already selected. unselect the row
        updatedSelectedRows = selectedRows.filter(row => row !== rowId);
      } else {
        // new selected row. add it to selected array
        updatedSelectedRows = [...selectedRows, rowId];
      }
    } else {
      updatedSelectedRows = [rowId];
    }
    setSelectedRows(updatedSelectedRows);
    if (modelType === MODEL_TYPES.REPEATED_ROOT) {
      if (updatedSelectedRows.length === 1) {
        onRowSelect(rowId);
      } else {
        onRowSelect(null);
      }
    }
  }

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

  const handleSave = () => {

  }

  const handlePageChange = (_, updatedPage) => {
    onPageChange(updatedPage);
  }

  const handleRowsPerPageChange = (e) => {
    const updatedRowsPerPage = parseInt(e.target.value, 10);
    onRowsPerPageChange(updatedRowsPerPage);
  }

  const handleModalToggle = () => {
    setIsModalOpen((prev) => !prev);
  }

  if (!activeRows || activeRows.length === 0) return null;

  // const isContextMenuOpen = Boolean(contextMenuAnchorEl);

  return (
    <TableContainer className={styles.container}>
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
                  const isNullCell = row && Object.keys(row).length === 0 && !cell.commonGroupKey;

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
                      forceUpdate={mode === MODES.READ}
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
      {rows.length > 6 &&
        <TablePagination
          rowsPerPageOptions={[25, 50, 100]}
          component='div'
          count={rows.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handlePageChange}
          onRowsPerPageChange={handleRowsPerPageChange}
        />
      }
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

          </ModelCardHeader>
          <ModelCardContent>
            <DataTree
              projectSchema={projectSchema}
              modelName={modelName}
              updatedData={modelType === MODEL_TYPES.REPEATED_ROOT ? dataTree : updatedData}
              storedData={modelType === MODEL_TYPES.REPEATED_ROOT ? storedData[selectedRows[0]] || {} : storedData}
              subtree={modelType === MODEL_TYPES.REPEATED_ROOT ? null : dataTree}
              mode={mode}
              xpath={modelRootPath}
              onUpdate={handleUpdate}
              onUserChange={handleUserChange}
              selectedId={selectedId}
            />
          </ModelCardContent>
        </ModelCard>
      </FullScreenModal>
    </TableContainer>
  )
}

export default DataTable;