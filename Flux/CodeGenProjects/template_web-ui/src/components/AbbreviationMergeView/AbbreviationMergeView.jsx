import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { cloneDeep, get, set } from 'lodash';
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Divider,
  Table,
  TableBody,
  TableContainer,
  TableRow,
  TextField
} from '@mui/material';
import { Download } from '@mui/icons-material';
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
import { DB_ID, DATA_TYPES, MODES, MODEL_TYPES } from '../../constants';
import TableHeader from '../tables/TableHeader';
import Cell from '../../components/Cell';
import { getBufferAbbreviatedOptionLabel } from '../../utils/ui/uiUtils.js';
import styles from './AbbreviationMergeView.module.css';
import { flux_toggle, flux_trigger_strat } from '../../projectSpecificUtils';
import { useScrollIndicators, useKeyboardNavigation } from '../../hooks';
import TablePaginationControl from '../TableControls/TablePaginationControl';
import ScrollIndicators from '../TableControls/ScrollIndicators';

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
        value={searchQuery || null}
        onChange={onSearchQueryChange}
        renderInput={(params) => (
          <TextField {...params} label={bufferedFieldMetadata.title} />
        )}
      />
      <Button
        color="primary"
        className={styles.button}
        // Enable button only if searchQuery is truthy
        disabled={!searchQuery}
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
  stickyHeader = true,
  frozenColumns,
  filters,
  onFiltersChange,
  uniqueValues
}) => {
  const [columns, setColumns] = useState(cells);
  const [columnWidths, setColumnWidths] = useState({});
  const columnRefs = useRef({});
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

  // Use the keyboard navigation hook
  const { handleKeyDown } = useKeyboardNavigation({
    mode,
    activeRows,
    tableContainerRef,
    capabilities: {
      editModeScrolling: true,
      readModeSelection: true,
      shiftSelection: false,  // AbbreviationMergeView doesn't support multi-selection
      ctrlShiftSelection: false
    },
    callbacks: {
      onRowSelect: onRowSelect
    }
  });

  // const { containerRef, isScrollable, enableScrolling, disableScrolling } = useBoundaryScrollDetection();

  useEffect(() => {
    setColumns(cells);
  }, [cells])

  // Sort sensors for drag-and-drop
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 10 } })
  );

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

  const handleButtonClick = (e, action, xpath, value, dataSourceId, source, force = false) => {
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

  const handleRowSelect = (_, id) => {
    if (mode === MODES.READ) {
      onRowSelect(id);
    }
  };

  const handleRowDoubleClick = (e) => {
    if (mode === MODES.READ && !isReadOnly) {
      if (!e.target.closest('button')) {
        onModeToggle();
      }
    }
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

  const handleClick = () => {
    // enableScrolling();
  }

  const handleDoubleClick = () => {
    // disableScrolling();
  }

  if (!activeRows || activeRows.length === 0) return null;

  let tableContainerClasses = styles.container;
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
        onClick={handleClick}
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
                let rowKey = groupedRow[0]['data-id'];
                if (Number.isInteger(rowKey)) {
                  rowKey = rowIdx;
                }
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
                      const isSelected = row?.['data-id'] === selectedId;
                      const isButtonDisabled = !isSelected;
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
                          key={cellIndex}
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
                          truncateDateTime={false}
                          modelType={MODEL_TYPES.ABBREVIATION_MERGE}
                          onForceSave={onForceSave}
                          onRowSelect={handleRowSelect}
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
      {rows.length > 6 && (
        <TablePaginationControl
          rows={rows}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={onPageChange}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[25, 50]}
        />
      )}
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
  stickyHeader,
  frozenColumns,
  filters,
  onFiltersChange,
  uniqueValues
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
        stickyHeader={stickyHeader}
        frozenColumns={frozenColumns}
        filters={filters}
        onFiltersChange={onFiltersChange}
        uniqueValues={uniqueValues}
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
};

export default AbbreviationMergeView;