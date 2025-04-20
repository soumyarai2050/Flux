import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Box, Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField } from '@mui/material';
import styles from './FilterDialog.module.css';

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
  isCollectionModel
}) => {
  // Lazy initializer for filterDict to avoid recomputation on every render.
  const [filterDict, setFilterDict] = useState(() =>
    filters.reduce((acc, { fld_name, fld_value }) => {
      acc[fld_name] = fld_value;
      return acc;
    }, {})
  );

  // Update filterDict whenever the filters prop changes.
  useEffect(() => {
    const updatedFilterDict = filters.reduce((acc, { fld_name, fld_value }) => {
      acc[fld_name] = fld_value;
      return acc;
    }, {});
    setFilterDict(updatedFilterDict);
  }, [filters]);

  const handlePopupClose = (e, reason) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
    onClose();
  };

  const handleTextChange = (e, fieldKey) => {
    setFilterDict((prev) => ({
      ...prev,
      [fieldKey]: e.target.value,
    }));
  };

  const handleFilterApply = () => {
    const updatedFilters = Object.keys(filterDict).map((filterField) => ({
      fld_name: filterField,
      fld_value: filterDict[filterField],
    }));
    onFiltersChange(updatedFilters);
    onClose();
  };

  const handleFilterClear = () => {
    setFilterDict({});
    onFiltersChange([]);
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  }

  const filterFieldsMetadata = useMemo(() => fieldsMetadata.filter(meta => meta.filterEnable), []);
  const fieldKey = isCollectionModel ? 'key' : 'path';

  return (
    <Dialog open={isOpen} onClose={handlePopupClose}>
      <DialogTitle>Filters</DialogTitle>
      <DialogContent>
        {filterFieldsMetadata
          .map((meta) => {
            // Determine display name and a unique field key for the filter.
            const displayName = isCollectionModel
              ? meta.key
              : meta.elaborateTitle
                ? meta.tableTitle
                : meta.title;
            return (
              <Box key={displayName} className={styles.filter} mb={2}>
                <span className={styles.filter_name}>{displayName}</span>
                <TextField
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
                />
              </Box>
            );
          })}
      </DialogContent>
      <DialogActions>
        <Button color='error' variant='contained' onClick={handleFilterClear}>
          Clear
        </Button>
        <Button color='success' variant='contained' onClick={handleFilterApply}>
          Apply
        </Button>
      </DialogActions>
    </Dialog>
  );
};

FilterDialog.propTypes = {
  /** Array of metadata objects for each field to be filtered. */
  fieldsMetadata: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      filter_enable: PropTypes.bool,
      elaborateTitle: PropTypes.bool,
      tableTitle: PropTypes.string,
      title: PropTypes.string,
    })
  ).isRequired,
  /** Array of filter objects with field name and value. */
  filters: PropTypes.arrayOf(
    PropTypes.shape({
      fld_name: PropTypes.string.isRequired,
      fld_value: PropTypes.string,
    })
  ).isRequired,
  /** Callback function invoked with updated filters when the user applies changes. */
  onFiltersChange: PropTypes.func.isRequired,
  /** Flag indicating whether the model is a collection model. */
  isCollectionModel: PropTypes.bool.isRequired,
};

export default FilterDialog;
