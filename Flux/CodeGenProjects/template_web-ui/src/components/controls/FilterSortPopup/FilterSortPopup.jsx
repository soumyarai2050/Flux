import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Popover, Typography, Checkbox, TextField, Button,
  Divider, List, ListItem, FormControlLabel, Box,
  IconButton, InputAdornment, MenuItem, Select, FormControl
} from '@mui/material';
import {
  ArrowDropDown, Search, Clear, ContentCopy, FilterAlt,
  ArrowUpward, ArrowDownward
} from '@mui/icons-material';
import ClipboardCopier from '../../utility/ClipboardCopier';
import styles from './FilterSortPopup.module.css';

/**
 * Excel-style filter and sort popup component with integrated column header icon
 */
const FilterSortPopup = ({
  columnId,
  columnName,
  valueCounts,
  uniqueValues,
  selectedFilters,
  textFilter,
  textFilterType,
  sortDirection,
  absoluteSort,
  sortLevel,
  onApply,
  onCopy,
  filterEnable,
  clipboardText
}) => {
  // Local state for changes before applying
  const [localSelectedFilters, setLocalSelectedFilters] = useState([]);
  const [originalSelectedFilters, setOriginalSelectedFilters] = useState([]);
  const [serverSideAppliedFilters, setServerSideAppliedFilters] = useState([]);
  const [localTextFilter, setLocalTextFilter] = useState('');
  const [localTextFilterType, setLocalTextFilterType] = useState('contains');
  const [localSortDirection, setLocalSortDirection] = useState(null);
  const [localAbsoluteSort, setLocalAbsoluteSort] = useState(null);
  const [searchValue, setSearchValue] = useState('');
  const [showTextFilter, setShowTextFilter] = useState(false);
  const [addCurrentSelectionToFilter, setAddCurrentSelectionToFilter] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const multiSortRef = useRef(true);

  // Internal state for popup open/close
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  // Initialize local state when popup opens
  useEffect(() => {
    if (open) {
      // If no filters have been applied yet, select all values by default
      const initialFilters = selectedFilters.length > 0
        ? [...selectedFilters]
        : [...uniqueValues];

      setLocalSelectedFilters(initialFilters);
      setOriginalSelectedFilters(initialFilters);
      setServerSideAppliedFilters([...selectedFilters]);
      setLocalTextFilter(textFilter || '');
      setLocalTextFilterType(textFilterType || 'contains');
      setLocalSortDirection(sortDirection);
      setLocalAbsoluteSort(absoluteSort);
      setSearchValue('');
      setShowTextFilter(textFilter && textFilter.length > 0);
      setAddCurrentSelectionToFilter(false);
    }
  }, [open, JSON.stringify(selectedFilters), textFilter, textFilterType, sortDirection, JSON.stringify(uniqueValues)]);

  // Handle icon click to open/close popup
  const handleIconClick = (event) => {
    event.stopPropagation();
    setAnchorEl(anchorEl ? null : event.currentTarget);
  };

  // Filter unique values based on search
  const filteredUniqueValues = uniqueValues.filter(value => {
    if (!searchValue) return true;
    // Ensure value is a string for comparison, handle null/undefined
    const stringValue = String(value === null || value === undefined ? '' : value);
    return stringValue.toLowerCase().includes(searchValue.toLowerCase());
  });

  // Handle select/deselect all search results
  const handleSelectAllSearchResults = () => {
    if (searchValue) {
      if (addCurrentSelectionToFilter) {
        // Keep current selections and add search results
        const currentSelection = new Set(localSelectedFilters);
        filteredUniqueValues.forEach(value => currentSelection.add(value));
        setLocalSelectedFilters([...currentSelection]);
      } else {
        // Replace with only search results
        const nonSearchValues = uniqueValues.filter(item => !filteredUniqueValues.includes(item));
        setLocalSelectedFilters([...filteredUniqueValues, ...localSelectedFilters.filter(item => nonSearchValues.includes(item))]);
      }
    } else {
      // When no search is active, this behaves like regular select all
      setLocalSelectedFilters([...uniqueValues]);
    }
  };

  const handleDeselectAllSearchResults = () => {
    if (searchValue) {
      if (addCurrentSelectionToFilter) {
        // Keep selections that aren't in search results
        setLocalSelectedFilters(localSelectedFilters.filter(
          item => !filteredUniqueValues.includes(item)
        ));
      } else {
        // Remove all search results from selection
        setLocalSelectedFilters(localSelectedFilters.filter(item => !filteredUniqueValues.includes(item)));
      }
    } else {
      // When no search is active, this clears all selections
      setLocalSelectedFilters([]);
    }
  };

  // Handle "Add current selection to filter" toggle
  const handleAddCurrentSelectionChange = (e) => {
    setAddCurrentSelectionToFilter(e.target.checked);
  };

  // Normalize value for comparison (handle type mismatches between numbers and strings)
  const normalizeValue = (val) => {
    // Convert to string for consistent comparison
    return String(val === null || val === undefined ? '' : val);
  };

  // Check if a value is in the selected filters (type-safe comparison)
  const isValueSelected = (value) => {
    const normalizedValue = normalizeValue(value);
    return localSelectedFilters.some(filter => normalizeValue(filter) === normalizedValue);
  };

  // Handle individual filter selection
  const handleFilterChange = (value) => {
    const normalizedValue = normalizeValue(value);
    if (isValueSelected(value)) {
      setLocalSelectedFilters(localSelectedFilters.filter(item => normalizeValue(item) !== normalizedValue));
    } else {
      setLocalSelectedFilters([...localSelectedFilters, value]);
    }
  };

  // Handle sorting
  const handleSortChange = (e, direction) => {
    if (e.ctrlKey) {
      multiSortRef.current = true;
    } else {
      multiSortRef.current = false;
    }
    setLocalSortDirection(localSortDirection === direction ? null : direction);
  };

  // Handle absolute sorting
  const handleAbsoluteSortToggle = () => {
    setLocalAbsoluteSort(!localAbsoluteSort);
  }

  // Handle text filter type change
  const handleTextFilterTypeChange = (e) => {
    setLocalTextFilterType(e.target.value);
  };

  // Handle text filter change
  const handleTextFilterChange = (e) => {
    setLocalTextFilter(e.target.value);
  };

  // Handle search input for filtering the value list
  const handleSearchChange = (e) => {
    const newSearchValue = e.target.value;

    if (newSearchValue) {
      // When entering a search term, auto-select all search results by default
      // in Excel's behavior
      const newFilteredValues = uniqueValues.filter(value => {
        const stringValue = String(value === null || value === undefined ? '' : value);
        return stringValue.toLowerCase().includes(newSearchValue.toLowerCase());
      });

      setLocalSelectedFilters([
        ...newFilteredValues,
        // ...localSelectedFilters.filter(item => nonFilteredValues.includes(item))
      ]);

      // In Excel, when you type in search, it automatically selects all filtered items
      // but doesn't auto-check "Add current selection to filter"
      // if (!addCurrentSelectionToFilter) {
      //   const nonFilteredValues = uniqueValues.filter(value => !newFilteredValues.includes(value));
      //   setLocalSelectedFilters([
      //     ...newFilteredValues,
      //     // ...localSelectedFilters.filter(item => nonFilteredValues.includes(item))
      //   ]);
      // } else {
      //   // If "Add current selection" is checked, we merge the selections
      //   const currentSelection = new Set(localSelectedFilters);
      //   newFilteredValues.forEach(value => currentSelection.add(value));
      //   setLocalSelectedFilters([...currentSelection]);
      // }
    } else {
      // When clearing search, restore original selection that was applied before search
      setLocalSelectedFilters(originalSelectedFilters);
    }

    setSearchValue(newSearchValue);
  };

  // Handle key down events
  const handleKeyDown = (e) => {
    if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  };

  // Clear search text
  const handleClearSearch = () => {
    // When clearing search in Excel, it restores the original selection
    setLocalSelectedFilters(originalSelectedFilters);
    setSearchValue('');
  };

  // Handle popup close
  const handleClose = () => {
    setAnchorEl(null);
  };

  // Handle Apply button click
  const handleApply = () => {
    // Determine final filter values to send to TableHeader
    let finalFilterValues;

    if (serverSideAppliedFilters.length === 0 && localSelectedFilters.length === uniqueValues.length) {
      // No server-side filters and all local values selected = no filtering
      finalFilterValues = null;
    } else if (serverSideAppliedFilters.length === 0 && localSelectedFilters.length < uniqueValues.length) {
      // Cleared server-side filters, but user has local selections
      finalFilterValues = localSelectedFilters.length > 0 ? localSelectedFilters : null;
    } else if (serverSideAppliedFilters.length > 0 && localSelectedFilters.length === uniqueValues.length) {
      // Server-side filters exist, user selected all visible values - preserve server filters
      finalFilterValues = serverSideAppliedFilters;
    } else {
      // User made new selections or modified existing ones
      const updatedSelectedFilters = originalSelectedFilters && addCurrentSelectionToFilter
        ? [...originalSelectedFilters, ...localSelectedFilters]
        : [...localSelectedFilters];
      finalFilterValues = updatedSelectedFilters.length !== uniqueValues.length ? updatedSelectedFilters : null;
    }

    onApply && onApply(columnId, finalFilterValues, localTextFilter,
      localTextFilterType, localSortDirection, localAbsoluteSort, multiSortRef.current);
    handleClose();
  };

  // Handle Cancel button click
  const handleCancel = () => {
    // In Excel, Cancel just discards changes
    handleClose();
  };

  // Toggle text filter visibility
  const toggleTextFilter = () => {
    setShowTextFilter(!showTextFilter);
    if (!showTextFilter) {
      setLocalTextFilter('');
    }
  };

  // Clear all filters
  const clearAllFilters = () => {
    setLocalSelectedFilters([...uniqueValues]);
    setServerSideAppliedFilters([]);
    setLocalTextFilter('');
    setLocalSortDirection(null);
    setLocalAbsoluteSort(null);
    setSearchValue('');
  };

  const handleCopy = () => {
    setIsCopied(true);
    onCopy(columnId, columnName);
    setTimeout(() => {
      setIsCopied(false);
    }, 2000);
  };

  // Calculate checkbox states for visible items
  const allVisibleSelected = filteredUniqueValues.length > 0 &&
    filteredUniqueValues.every(value => isValueSelected(value));

  const someVisibleSelected = filteredUniqueValues.some(value =>
    isValueSelected(value)) && !allVisibleSelected;

  // Calculate if any filter is actually applied
  const hasFilters = uniqueValues.length > 1;
  // If selectedFilters has values, it means a filter is applied (active filtering)
  // This works because selectedFilters is only populated when user explicitly filters
  const isFiltered = (selectedFilters.length !== 0) || textFilter;
  const hasLocalFilterOrSort = localSelectedFilters.length !== 0 && localSelectedFilters.length < uniqueValues.length || localTextFilter || localSortDirection;

  // Count occurrences of each value
  // const valueCounts = {};
  // totalValues.forEach(value => {
  //   valueCounts[value] = (valueCounts[value] || 0) + 1;
  // });

  // Get text for filter operator
  const getTextFilterOperatorLabel = (type) => {
    switch (type) {
      case 'equals': return 'Equals...';
      case 'notEqual': return 'Does not equal...';
      case 'contains': return 'Contains...';
      case 'notContains': return 'Does not contain...';
      case 'beginsWith': return 'Begins with...';
      case 'endsWith': return 'Ends with...';
      default: return 'Contains...';
    }
  };

  // Check if search is active
  const hasActiveSearch = searchValue.length > 0;
  const sortLevelClass = sortLevel && sortLevel > 2 ? styles.multiLevelSort : sortLevel === 1 ? styles.firstLevelSort : sortLevel === 2 ? styles.secondLevelSort : '';

  return (
    <>
      {/* Filter Icon */}
      <div className={`${styles.filterIconWrapper} ${open ? styles.popupOpen : ''}`}>
        <IconButton
          size="small"
          className={`${styles.filterButton} ${(isFiltered) ? styles.activeFilter : hasFilters ? styles.hasFilter : ''}`}
          onClick={handleIconClick}
          aria-label="Filter and sort"
        >
          {sortDirection && (
            <>
              <div className={styles.sortIndicator}>
                {sortDirection === 'asc' && <div className={`${styles.sortArrow} ${sortLevelClass}`}>{'\u2191'}</div>}
                {sortDirection === 'desc' && <div className={`${styles.sortArrow} ${sortLevelClass}`}>{'\u2193'}</div>}
              </div>
              <div className={styles.absoluteSortIndicator}>
                {absoluteSort && <div className={sortLevelClass}>{'\u00B1'}</div>}
              </div>
            </>
          )}
          <ArrowDropDown />
        </IconButton>
      </div>

      {/* Filter Popup */}
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleCancel}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        classes={{
          paper: styles.popoverPaper,
        }}
      >
        <div className={styles.popupContainer}>
          {/* Copy section */}
          <div className={styles.section}>
            <div className={styles.copyOption} onClick={handleCopy}>
              <div className={styles.sortIcon}>
                {isCopied && <div className={styles.checkMark}>{'\u2713'}</div>}
              </div>
              <div className={styles.sortIconPlaceholder}>
                <ContentCopy fontSize="small" className={styles.menuIcon} />
              </div>
              <Typography>{`Copy`}</Typography>
            </div>
          </div>

          <Divider className={styles.menuDivider} />

          {/* Sort section */}
          <div className={styles.section}>
            <div className={styles.sortOption} onClick={(e) => handleSortChange(e, 'asc')}>
              <div className={styles.sortIcon}>
                {localSortDirection === 'asc' && <div className={styles.checkMark}>{'\u2713'}</div>}
              </div>
              <div className={styles.sortIconPlaceholder}>
                <ArrowUpward fontSize="small" className={styles.menuIcon} />
              </div>
              <Typography>Sort A to Z</Typography>
            </div>

            <div className={styles.sortOption} onClick={(e) => handleSortChange(e, 'desc')}>
              <div className={styles.sortIcon}>
                {localSortDirection === 'desc' && <div className={styles.checkMark}>{'\u2713'}</div>}
              </div>
              <div className={styles.sortIconPlaceholder}>
                <ArrowDownward fontSize="small" className={styles.menuIcon} />
              </div>
              <Typography>Sort Z to A</Typography>
            </div>

            <div className={styles.sortOption} onClick={handleAbsoluteSortToggle}>
              <div className={styles.sortIcon}>
                {localAbsoluteSort && <div className={styles.checkMark}>{'\u2713'}</div>}
              </div>
              <div className={styles.sortIconPlaceholder}>
                {'\u00B1'}
              </div>
              <Typography>Absolute Sort</Typography>
            </div>

            <Divider className={styles.menuDivider} />

            {/* Text Filters dropdown */}
            {filterEnable && (
              <>
                <div className={styles.textFiltersHeader} onClick={toggleTextFilter}>
                  <Typography>Text Filters</Typography>
                  <ArrowDropDown />
                </div>

                {showTextFilter && (
                  <div className={styles.textFilterSection}>
                    <FormControl fullWidth size="small" className={styles.filterTypeSelect}>
                      <Select
                        value={localTextFilterType}
                        onChange={handleTextFilterTypeChange}
                        displayEmpty
                        variant="outlined"
                      >
                        <MenuItem value="equals">Equals</MenuItem>
                        <MenuItem value="notEqual">Does not equal</MenuItem>
                        <MenuItem value="contains">Contains</MenuItem>
                        <MenuItem value="notContains">Does not contain</MenuItem>
                        <MenuItem value="beginsWith">Begins with</MenuItem>
                        <MenuItem value="endsWith">Ends with</MenuItem>
                      </Select>
                    </FormControl>
                    <TextField
                      placeholder={getTextFilterOperatorLabel(localTextFilterType)}
                      variant="outlined"
                      size="small"
                      fullWidth
                      value={localTextFilter}
                      onChange={handleTextFilterChange}
                      className={styles.textFilterField}
                      onKeyDown={handleKeyDown}
                    />
                  </div>
                )}

                <Divider className={styles.menuDivider} />
              </>
            )}
            {(hasLocalFilterOrSort || isFiltered) && (
              <div className={styles.clearFilterOption}
                onClick={(hasLocalFilterOrSort || isFiltered) ? clearAllFilters : undefined}
                style={{ opacity: (isFiltered || hasLocalFilterOrSort )? 1 : 0.5, pointerEvents: (isFiltered || hasLocalFilterOrSort ) ? 'auto' : 'none' }}
              >
                <div className={styles.sortIcon}></div>
                <div className={styles.sortIconPlaceholder}>
                  <FilterAlt fontSize="small" className={styles.menuIcon} />
                </div>
                <Typography>{`Clear Filter/Sort`}</Typography>
              </div>
            )}
          </div>

          <Divider />

          {/* Filter section */}
          {filterEnable && (
            <div className={styles.section}>
              {/* Show server-side applied filters when filters are active */}
              {/* {selectedFilters.length > 0 && uniqueValues.length >= 1 && (
                <div className={styles.serverFiltersSection}>
                  <Typography variant="caption" className={styles.serverFiltersTitle}>
                    Server Side Filters ({selectedFilters.length} applied):
                  </Typography>
                  <div className={styles.serverFiltersList}>
                    {selectedFilters.map((value, index) => (
                      <div key={index} className={styles.serverFilterItem}>
                        {value === null || value === undefined ? '(Blank)' : String(value)}
                      </div>
                    ))}
                  </div>
                  <Divider className={styles.menuDivider} />
                </div>
              )} */}

              <div className={styles.searchContainer}>
                <TextField
                  placeholder="Search"
                  variant="outlined"
                  size="small"
                  fullWidth
                  value={searchValue}
                  onChange={handleSearchChange}
                  onKeyDown={handleKeyDown}
                  className={styles.searchField}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search fontSize="small" className={styles.searchIcon} />
                      </InputAdornment>
                    ),
                    endAdornment: searchValue ? (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={handleClearSearch}>
                          <Clear fontSize="small" />
                        </IconButton>
                      </InputAdornment>
                    ) : null
                  }}
                />
              </div>

              {hasActiveSearch && (
                <div className={styles.addSelectionContainer}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={addCurrentSelectionToFilter}
                        onChange={handleAddCurrentSelectionChange}
                        className={styles.checkbox}
                      />
                    }
                    label="Add current selection to filter"
                    className={styles.addSelectionCheckbox}
                  />
                </div>
              )}

              <div className={styles.valuesList}>
                <div className={styles.selectAllContainer}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={allVisibleSelected}
                        indeterminate={someVisibleSelected}
                        onChange={allVisibleSelected ? handleDeselectAllSearchResults : handleSelectAllSearchResults}
                        disabled={filteredUniqueValues.length === 0}
                        className={styles.checkbox}
                      />
                    }
                    label={hasActiveSearch ? "Select All Search Results" : "(Select All)"}
                    className={styles.selectAllCheckbox}
                  />
                </div>

                <div className={styles.checkboxListContainer}>
                  <List className={styles.checkboxList} dense disablePadding>
                    {filteredUniqueValues.length > 0 ? (
                      filteredUniqueValues.map((value, index) => (
                        <ListItem key={index} dense disablePadding className={styles.checkboxItem}>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={isValueSelected(value)}
                                onChange={() => handleFilterChange(value)}
                                className={styles.checkbox}
                              />
                            }
                            label={
                              <div className={styles.valueWithCount}>
                                <span className={styles.checkboxLabel}>
                                  {value === null || value === undefined ? '(Blank)' : String(value)}
                                </span>
                                <span className={styles.valueCount}>
                                  ({valueCounts.get(value) ?? 0})
                                </span>
                              </div>
                            }
                          />
                        </ListItem>
                      ))
                    ) : (
                      <Typography variant="body2" className={styles.noResults}>
                        No matching values found
                      </Typography>
                    )}
                  </List>
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className={styles.actionButtons}>
            <Button
              variant="contained"
              onClick={handleApply}
              className={styles.okButton}
            >
              OK
            </Button>
            <Button
              variant="outlined"
              onClick={handleCancel}
              className={styles.cancelButton}
            >
              Cancel
            </Button>
          </div>
        </div>
        <ClipboardCopier text={clipboardText} />
      </Popover>
    </>
  );
};

FilterSortPopup.propTypes = {
  columnId: PropTypes.string.isRequired,
  columnName: PropTypes.string.isRequired,
  uniqueValues: PropTypes.array.isRequired,
  selectedFilters: PropTypes.array.isRequired,
  textFilter: PropTypes.string,
  textFilterType: PropTypes.oneOf(['equals', 'notEqual', 'contains', 'notContains', 'beginsWith', 'endsWith']),
  sortDirection: PropTypes.oneOf(['asc', 'desc', null]),
  onApply: PropTypes.func.isRequired,
  onCopy: PropTypes.func.isRequired,
  filterEnable: PropTypes.bool,
  clipboardText: PropTypes.string,
  valueCounts: PropTypes.instanceOf(Map)
};

FilterSortPopup.defaultProps = {
  textFilter: '',
  textFilterType: 'contains',
  sortDirection: null,
  filterEnable: false,
  uniqueValues: [],
  selectedFilters: [],
  valueCounts: new Map()
};

export default FilterSortPopup;