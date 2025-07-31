import React, { useState, useEffect, useCallback, useRef } from 'react';
import { debounce } from 'lodash';
import PropTypes from 'prop-types';
import { Box, Dialog, DialogTitle, DialogContent, TextField } from '@mui/material';
import styles from './FilterDialog.module.css';
import FilterSortPopup from '../../FilterSortPopup/FilterSortPopup';
import LinkText from '../../LinkText';
import { getFilterDict } from '../../../utils/core/dataFiltering';
import { getSortOrderDict } from '../../../utils/core/dataSorting';
import { FilterAlt } from '@mui/icons-material';

/**
 * FilterMenu renders a dialog that allows users to apply filters on a data set.
 * When the filter icon is clicked, a dialog opens with text fields for each field that
 * supports filtering (as defined by `fieldsMetadata`). The current filter values are
 * initialized from the `filters` prop.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Array<Object>} props.fieldsMetadata - Array of metadata objects for each field.
 *        Each object should include:
 *          - key: {string} Unique identifier for the field.
 *          - filterEnable: {boolean} (Optional) Indicates if filtering is enabled for the field.
 *          - elaborateTitle: {boolean} (Optional) If true, use tableTitle as the display name.
 *          - tableTitle: {string} Display name when elaborateTitle is true.
 *          - title: {string} Display name when elaborateTitle is false.
 * @param {Array<Object>} props.filters - Array of filter objects.
 *        Each filter object should have:
 *          - fld_name: {string} The field identifier.
 *          - fld_value: {string} The filter value.
 * @param {function} props.onFiltersChange - Callback function invoked with the updated filters when applied.
 * @param {boolean} props.isCollectionModel - Flag indicating if the model is a collection model.
 * @returns {JSX.Element} The rendered FilterDialog component.
 */

const FilterDialog = ({
  isOpen,
  onClose,
  filters,
  onFiltersChange,
  fieldsMetadata,
  isCollectionModel,
  uniqueValues,
  sortOrders,
  onSortOrdersChange,
  groupedRows
}) => {
  const [filteredColumns, setFilteredColumns] = useState(fieldsMetadata);
  const [searchValue, setSearchValue] = useState('');
  // Lazy initializer for filterDict to avoid recomputation on every render.
  const [filterDict, setFilterDict] = useState(getFilterDict(filters));
  const [sortOrderDict, setSortOrderDict] = useState(getSortOrderDict(sortOrders));
  const [clipboardText, setClipboardText] = useState(null);

  // Update filterDict whenever the filters prop changes.
  useEffect(() => {
    const updatedFilterDict = getFilterDict(filters);
    setFilterDict(updatedFilterDict);
  }, [filters]);

  useEffect(() => {
    const updatedSortOrderDict = getSortOrderDict(sortOrders);
    setSortOrderDict(updatedSortOrderDict);
  }, [sortOrders]);

  const debouncedTransform = useRef(
    debounce((value) => {
      if (value) {
        const lowerCasedValue = value.toLowerCase();
        const updatedColumns = fieldsMetadata.filter((column) => column[fieldKey]?.toLowerCase().includes(lowerCasedValue));
        setFilteredColumns(updatedColumns);
      } else {
        setFilteredColumns(fieldsMetadata);
      }
    }, 300)
  ).current;

  const handleSearchValueChange = (e) => {
    const { value } = e.target;
    setSearchValue(value);
    debouncedTransform(value);
  };

  const handleKeyDown = (e) => {
    if (e.key.length === 1 || ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  };

  const handlePopupClose = (e, reason) => {
    // if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
    onClose();
  };

  const handleApply = useCallback((filterName, values, textFilter, textFilterType, sortDirection, isAbsoluteSort, multiSort = false) => {
    let updatedFilterDict = {};
    let updatedSortOrderDict = {};

    setFilterDict((prev) => {
      updatedFilterDict = {
        ...prev,
        [filterName]: {
          ...prev[filterName],
          column_name: filterName,
          filtered_values: values,
          text_filter: textFilter,
          text_filter_type: textFilterType
        }
      };
      return updatedFilterDict;
    });

    setSortOrderDict((prev) => {
      updatedSortOrderDict = multiSort ? {
        ...prev,
        [filterName]: {
          ...prev[filterName],
          sort_direction: sortDirection,
          is_absolute_sort: isAbsoluteSort
        }
      } : {
        [filterName]: {
          ...prev[filterName],
          sort_direction: sortDirection,
          is_absolute_sort: isAbsoluteSort
        }
      };
      if (!sortDirection) {
        delete updatedSortOrderDict[filterName];
      }

      const updatedFilters = Object.keys(updatedFilterDict).map((filterName) => ({
        ...updatedFilterDict[filterName],
        filtered_values: updatedFilterDict[filterName].filtered_values?.join(',') ?? null,
      }));
      const updatedSortOrders = Object.keys(updatedSortOrderDict).map((sortBy) => ({
        sort_by: sortBy,
        sort_direction: updatedSortOrderDict[sortBy].sort_direction,
        is_absolute_sort: updatedSortOrderDict[sortBy].is_absolute_sort
      }));
      onFiltersChange(updatedFilters);
      onSortOrdersChange(updatedSortOrders);

      return updatedSortOrderDict;
    });
    onClose();
  }, [onFiltersChange, onSortOrdersChange, onClose]);

  const handleCopy = (columnId, columnName) => {
    const fieldKey = isCollectionModel ? 'key' : 'tableTitle';
    const column = fieldsMetadata.find((meta) => meta[fieldKey] === columnId);
    if (!column) {
      console.error(`handleCopy failed, no column found with columnId: ${columnId}`);
      return;
    }

    let sourceIndex = column.sourceIndex;
    if (sourceIndex == null) {
      sourceIndex = 0;
    }
    const values = [columnName];
    groupedRows.forEach((groupedRow) => {
      const row = groupedRow[sourceIndex];
      values.push(row[columnId]);
    });

    const text = values.join('\n');
    setClipboardText(text);
    setTimeout(() => {
      // to allow same column to be copied again even if there is no text change
      setClipboardText(null);
    }, 2000);
  };

  // const handleKeyDown = (e) => {
  //   if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
  //     // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
  //     if (e.key !== 'Escape') {
  //       e.stopPropagation();
  //     }
  //   }
  // }

  const fieldKey = isCollectionModel ? 'key' : 'tableTitle';

  return (
    <Dialog open={isOpen} onClose={handlePopupClose}>
      <DialogTitle>
        <span style={{ display: 'flex', alignItems: 'center' }}>
          <FilterAlt fontSize='large' color='info' />
          Filter & Sort
        </span>
      </DialogTitle>
      <DialogContent style={{ minWidth: '350px', padding: 10 }}>
        {fieldsMetadata.length > 5 && (
          <TextField
            sx={{ width: '100%', marginBottom: '10px' }}
            size="small"
            label="Field Name"
            placeholder='Search a field'
            value={searchValue}
            onChange={handleSearchValueChange}
            onKeyDown={handleKeyDown}
            // InputProps={{
            //   style: {},
            // }}
            autoFocus
          />
        )}
        {filteredColumns
          .filter((meta) => meta.type !== 'object' && meta.type !== 'array')
          .map((meta) => {
            // Determine display name and a unique field key for the filter.
            const displayName = isCollectionModel
              ? meta.key
              : meta.elaborateTitle
                ? meta.tableTitle
                : meta.title;
            const fieldName = meta[fieldKey];
            return (
              <Box key={displayName} className={styles.filter} mb={2}>
                <span className={styles.filter_name}>{displayName}</span>
                {/* <TextField
                  id={meta[fieldKey]}
                  className={styles.text_field}
                  name={meta[fieldKey]}
                  size='small'
                  value={filterDict[meta[fieldKey]] || ''}
                  onChange={(e) => handleTextChange(e, meta[fieldKey])}
                  variant='outlined'
                  placeholder='Comma separated values'
                  inputProps={{
                    style: { padding: '6px 10px' },
                  }}
                  fullWidth
                  margin='dense'
                  onKeyDown={handleKeyDown}
                /> */}
                <FilterSortPopup
                  columnId={fieldName}
                  columnName={meta.title}
                  valueCounts={uniqueValues[fieldName] ?? new Map()}
                  uniqueValues={Array.from(uniqueValues[fieldName]?.keys() ?? [])}
                  selectedFilters={filterDict[fieldName]?.filtered_values ?? []}
                  textFilter={filterDict[fieldName]?.text_filter ?? null}
                  textFilterType={filterDict[fieldName]?.text_filter_type ?? null}
                  sortDirection={sortOrderDict[fieldName]?.sort_direction ?? null}
                  absoluteSort={sortOrderDict[fieldName]?.is_absolute_sort ?? null}
                  sortLevel={sortOrderDict[fieldName]?.sort_level ?? null}
                  onApply={handleApply}
                  onCopy={handleCopy}
                  filterEnable={meta.filterEnable ?? false}
                  clipboardText={clipboardText}
                />
                {filterDict[fieldName]?.filtered_values && (
                  <LinkText
                    text={JSON.stringify(filterDict[fieldName]?.filtered_values)}
                  />
                )}
              </Box>
            );
          })}
      </DialogContent>
      {/* <DialogActions>
        <Button color='error' variant='contained' onClick={handleFilterClear}>
          Clear
        </Button>
        <Button color='success' variant='contained' onClick={handleFilterApply}>
          Apply
        </Button>
      </DialogActions> */}
    </Dialog>
  );
};

FilterDialog.propTypes = {
  /** Array of metadata objects for each field to be filtered. */
  fieldsMetadata: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      filterEnable: PropTypes.bool,
      elaborateTitle: PropTypes.bool,
      tableTitle: PropTypes.string,
      title: PropTypes.string,
    })
  ).isRequired,
  /** Array of filter objects with field name and value. */
  filters: PropTypes.arrayOf(
    PropTypes.shape({
      column_name: PropTypes.string.isRequired,
      filtered_values: PropTypes.string,
      text_filter: PropTypes.string,
      text_filter_type: PropTypes.string
    })
  ).isRequired,
  /** Callback function invoked with updated filters when the user applies changes. */
  onFiltersChange: PropTypes.func.isRequired,
  /** Flag indicating whether the model is a collection model. */
  isCollectionModel: PropTypes.bool.isRequired,
};

export default FilterDialog;
