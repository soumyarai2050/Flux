import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from '@mui/material';
import { FilterAlt, PushPin, PushPinOutlined } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';

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
 *          - filter_enable: {boolean} (Optional) Indicates if filtering is enabled for the field.
 *          - elaborateTitle: {boolean} (Optional) If true, use tableTitle as the display name.
 *          - tableTitle: {string} Display name when elaborateTitle is true.
 *          - title: {string} Display name when elaborateTitle is false.
 * @param {Array<Object>} props.filters - Array of filter objects.
 *        Each filter object should have:
 *          - fld_name: {string} The field identifier.
 *          - fld_value: {string} The filter value.
 * @param {function} props.onFiltersChange - Callback function invoked with the updated filters when applied.
 * @param {boolean} props.isCollectionModel - Flag indicating if the model is a collection model.
 * @returns {JSX.Element} The rendered FilterMenu component.
 */
const FilterMenu = ({
  fieldsMetadata,
  filters,
  onFiltersChange,
  isCollectionModel,
  isPinned,
  onPinToggle,
  menuType
}) => {
  // Lazy initializer for filterDict to avoid recomputation on every render.
  const [filterDict, setFilterDict] = useState(() =>
    filters.reduce((acc, { fld_name, fld_value }) => {
      acc[fld_name] = fld_value;
      return acc;
    }, {})
  );
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  // Update filterDict whenever the filters prop changes.
  useEffect(() => {
    const updatedFilterDict = filters.reduce((acc, { fld_name, fld_value }) => {
      acc[fld_name] = fld_value;
      return acc;
    }, {});
    setFilterDict(updatedFilterDict);
  }, [filters]);

  const menuName = 'filter';

  const handlePopupOpen = () => {
    setIsPopupOpen(true);
  };

  const handlePopupClose = (e, reason) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
    setIsPopupOpen(false);
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
    setIsPopupOpen(false);
  };

  const handleFilterClear = () => {
    setFilterDict({});
    onFiltersChange([]);
    setIsPopupOpen(false);
  };

  const filterFieldsMetadata = useMemo(() => fieldsMetadata.filter(meta => meta.filter_enable), []);

  if (filterFieldsMetadata.length === 0) return null;

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handlePopupOpen}>
            <span>
              <FilterAlt sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handlePopupOpen}>
            <FilterAlt fontSize='small' />
          </Icon>
        );
    }
  }

  return (
    <>
      {renderMenu()}
      <Dialog open={isPopupOpen} onClose={handlePopupClose}>
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
              const fieldKey = isCollectionModel ? 'key' : 'path';
              return (
                <Box key={displayName} mb={2}>
                  <span>{displayName}</span>
                  <TextField
                    id={meta.tableTitle}
                    name={meta.tableTitle}
                    size='small'
                    value={filterDict[fieldKey] || ''}
                    onChange={(e) => handleTextChange(e, fieldKey)}
                    variant='outlined'
                    placeholder='Comma separated values'
                    inputProps={{
                      style: { padding: '6px 10px' },
                    }}
                    fullWidth
                    margin='dense'
                  />
                </Box>
              );
            })}
        </DialogContent>
        <DialogActions>
          <Button color='error' onClick={handleFilterClear} autoFocus>
            Clear
          </Button>
          <Button onClick={handleFilterApply} autoFocus>
            Apply
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

FilterMenu.propTypes = {
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

export default FilterMenu;