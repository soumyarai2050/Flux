import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import Popover from '@mui/material/Popover';
import Typography from '@mui/material/Typography';
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import FormControlLabel from '@mui/material/FormControlLabel';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import FormControl from '@mui/material/FormControl';
import Tooltip from '@mui/material/Tooltip';
import ArrowDropDown from '@mui/icons-material/ArrowDropDown';
import Search from '@mui/icons-material/Search';
import Clear from '@mui/icons-material/Clear';
import ContentCopy from '@mui/icons-material/ContentCopy';
import FilterAlt from '@mui/icons-material/FilterAlt';
import ArrowUpward from '@mui/icons-material/ArrowUpward';
import ArrowDownward from '@mui/icons-material/ArrowDownward';
import { debounce } from 'lodash';
import ClipboardCopier from '../../utility/ClipboardCopier';
import styles from './FilterSortPopup.module.css';

// Simple virtual scrolling component
const VirtualizedList = ({ items, height, itemHeight, renderItem, noItemsComponent }) => {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef();

  const visibleStart = Math.floor(scrollTop / itemHeight);
  const visibleEnd = Math.min(visibleStart + Math.ceil(height / itemHeight) + 1, items.length);

  const totalHeight = items.length * itemHeight;
  const offsetY = visibleStart * itemHeight;

  const handleScroll = (e) => {
    setScrollTop(e.target.scrollTop);
  };

  if (items.length === 0) {
    return noItemsComponent;
  }

  return (
    <div
      ref={containerRef}
      style={{ height, overflowY: 'auto' }}
      onScroll={handleScroll}
      className={styles.virtualizedContainer}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetY}px)` }}>
          {items.slice(visibleStart, visibleEnd).map((item, index) =>
            renderItem({ item, index: visibleStart + index })
          )}
        </div>
      </div>
    </div>
  );
};

// Extract constants
const TEXT_FILTER_TYPES = {
  EQUALS: 'equals',
  NOT_EQUAL: 'notEqual',
  CONTAINS: 'contains',
  NOT_CONTAINS: 'notContains',
  BEGINS_WITH: 'beginsWith',
  ENDS_WITH: 'endsWith'
};

const TEXT_FILTER_LABELS = {
  [TEXT_FILTER_TYPES.EQUALS]: 'Equals...',
  [TEXT_FILTER_TYPES.NOT_EQUAL]: 'Does not equal...',
  [TEXT_FILTER_TYPES.CONTAINS]: 'Contains...',
  [TEXT_FILTER_TYPES.NOT_CONTAINS]: 'Does not contain...',
  [TEXT_FILTER_TYPES.BEGINS_WITH]: 'Begins with...',
  [TEXT_FILTER_TYPES.ENDS_WITH]: 'Ends with...'
};

// Memoized sub-component for filter list items
const FilterListItem = React.memo(({ value, isChecked, count, onChange }) => {
  const handleChange = useCallback(() => onChange(value), [value, onChange]);

  return (
    <ListItem disablePadding className={styles.checkboxItem}>
      <FormControlLabel
        control={
          <Checkbox
            checked={isChecked}
            onChange={handleChange}
            className={styles.checkbox}
          />
        }
        label={
          <div className={styles.valueWithCount}>
            <span className={styles.checkboxLabel}>
              {value == null || value === undefined ? '(Blank)' : String(value)}
            </span>
            <span className={styles.valueCount}>
              {count}
            </span>
          </div>
        }
      />
    </ListItem>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for better memoization
  return prevProps.value === nextProps.value &&
    prevProps.isChecked === nextProps.isChecked &&
    prevProps.count === nextProps.count &&
    prevProps.onChange === nextProps.onChange;
});

FilterListItem.displayName = 'FilterListItem';

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
  clipboardText,
  serverSideFilterSortEnabled
}) => {
  // Use Set for O(1) lookups instead of array
  const [localSelectedFiltersSet, setLocalSelectedFiltersSet] = useState(new Set());
  const [originalSelectedFiltersSet, setOriginalSelectedFiltersSet] = useState(new Set());
  const [serverSideAppliedFilters, setServerSideAppliedFilters] = useState([]);
  const [localTextFilter, setLocalTextFilter] = useState('');
  const [localTextFilterType, setLocalTextFilterType] = useState(TEXT_FILTER_TYPES.CONTAINS);
  const [localSortDirection, setLocalSortDirection] = useState(null);
  const [localAbsoluteSort, setLocalAbsoluteSort] = useState(null);
  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearchValue, setDebouncedSearchValue] = useState('');
  const [showTextFilter, setShowTextFilter] = useState(false);
  const [addCurrentSelectionToFilter, setAddCurrentSelectionToFilter] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const multiSortRef = useRef(true);
  const isInitialized = useRef(false);
  // Internal state for popup open/close
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  // Use a ref to prevent re-creating debounce function on every render
  const debouncedSearchRef = useRef(
    debounce((value, currentSelectedSet, originalSet, addToFilter, uniqueValsSet) => {
      setDebouncedSearchValue(value);
      if (value) {
        const searchLower = value.toLowerCase();
        const newFilteredValues = [];
        for (const val of uniqueValsSet) {
          const stringValue = String(val ?? '').toLowerCase();
          if (stringValue.includes(searchLower)) {
            newFilteredValues.push(val);
          }
        }

        if (addToFilter) {
          const newSet = new Set(currentSelectedSet);
          newFilteredValues.forEach(v => newSet.add(v));
          setLocalSelectedFiltersSet(newSet);
        } else {
          setLocalSelectedFiltersSet(new Set(newFilteredValues));
        }
      } else {
        // Restore original when clearing search
        setLocalSelectedFiltersSet(new Set(originalSet));
      }
    }, 300)
  );

  // Memoize uniqueValues Set for faster lookups
  const uniqueValuesSet = useMemo(() => new Set(uniqueValues), [uniqueValues]);

  // Initialize local state when popup opens
  useEffect(() => {
    if (open) {
      if (isInitialized.current) return;

      // If no filters have been applied yet, select all values by default
      const initialFilters = selectedFilters.length > 0
        ? new Set(selectedFilters)
        : new Set(uniqueValuesSet);

      setLocalSelectedFiltersSet(initialFilters);
      setOriginalSelectedFiltersSet(new Set(initialFilters)); // Keep a copy of the initial state
      setServerSideAppliedFilters([...selectedFilters]);
      setLocalTextFilter(textFilter || '');
      setLocalTextFilterType(textFilterType || TEXT_FILTER_TYPES.CONTAINS);
      setLocalSortDirection(sortDirection);
      setLocalAbsoluteSort(absoluteSort);
      setSearchValue('');
      setDebouncedSearchValue('');
      setShowTextFilter(Boolean(textFilter));
      setAddCurrentSelectionToFilter(false);
      isInitialized.current = true;
    } else {
      isInitialized.current = false;

    }
  }, [open, JSON.stringify(selectedFilters), textFilter, textFilterType, sortDirection, absoluteSort, uniqueValuesSet]);


  // Handle icon click to open/close popup
  const handleIconClick = useCallback((event) => {
    event.stopPropagation();
    setAnchorEl(anchorEl ? null : event.currentTarget);
  }, [anchorEl]);

  // Memoized filter unique values based on search
  const filteredUniqueValues = useMemo(() => {
    if (!debouncedSearchValue) return Array.from(uniqueValuesSet);
    const searchLower = debouncedSearchValue.toLowerCase();
    const filtered = [];
    for (const value of uniqueValuesSet) {
      const stringValue = String(value ?? '').toLowerCase();
      if (stringValue.includes(searchLower)) {
        filtered.push(value);
      }
    }
    return filtered;
  }, [uniqueValuesSet, debouncedSearchValue]);

  // Memoize checkbox states
  const { allVisibleSelected, someVisibleSelected } = useMemo(() => {
    if (filteredUniqueValues.length === 0) {
      return { allVisibleSelected: false, someVisibleSelected: false };
    }

    let selectedCount = 0;
    for (const value of filteredUniqueValues) {
      if (localSelectedFiltersSet.has(value)) {
        selectedCount++;
      }
    }
    return {
      allVisibleSelected: selectedCount === filteredUniqueValues.length,
      someVisibleSelected: selectedCount > 0 && selectedCount < filteredUniqueValues.length
    };
  }, [filteredUniqueValues, localSelectedFiltersSet]);


  // Handle select/deselect all search results
  const handleSelectAllSearchResults = useCallback(() => {
    if (debouncedSearchValue) {
      // Search is active - handle filtered results
      if (addCurrentSelectionToFilter) {
        // Keep current selections and add search results
        const newSet = new Set(localSelectedFiltersSet);
        filteredUniqueValues.forEach(value => newSet.add(value));
        setLocalSelectedFiltersSet(newSet);
      } else {
        // Replace with only search results, but keep non-searched items that were selected
        const newSet = new Set();
        filteredUniqueValues.forEach(value => newSet.add(value));
        for (const value of uniqueValuesSet) {
          if (!filteredUniqueValues.includes(value) && localSelectedFiltersSet.has(value)) {
            newSet.add(value);
          }
        }
        setLocalSelectedFiltersSet(newSet);
      }
    } else {
      // No search active - select/deselect all unique values
      setLocalSelectedFiltersSet(new Set(uniqueValuesSet));
    }
  }, [debouncedSearchValue, addCurrentSelectionToFilter, filteredUniqueValues, uniqueValuesSet, localSelectedFiltersSet]);

  const handleDeselectAllSearchResults = useCallback(() => {
    if (debouncedSearchValue) {
      // Search is active - only deselect filtered results
      const newSet = new Set(localSelectedFiltersSet);
      filteredUniqueValues.forEach(value => newSet.delete(value));
      setLocalSelectedFiltersSet(newSet);
    } else {
      // No search - clear all selections
      setLocalSelectedFiltersSet(new Set());
    }
  }, [debouncedSearchValue, filteredUniqueValues, localSelectedFiltersSet]);


  // Handle "Add current selection to filter" toggle
  const handleAddCurrentSelectionChange = (e) => {
    setAddCurrentSelectionToFilter(e.target.checked);
  }

  // Handle individual filter selection change
  const handleFilterChange = useCallback((value) => {
    const newSet = new Set(localSelectedFiltersSet);
    if (newSet.has(value)) {
      newSet.delete(value);
    } else {
      newSet.add(value);
    }
    setLocalSelectedFiltersSet(newSet);
  }, [localSelectedFiltersSet]);

  // Handle search input for filtering the value list
  const handleSearchChange = useCallback((e) => {
    const value = e.target.value;
    setSearchValue(value);
    // Immediate UI update, then trigger debounced search
    debouncedSearchRef.current(
      value,
      localSelectedFiltersSet,
      originalSelectedFiltersSet,
      addCurrentSelectionToFilter,
      uniqueValuesSet
    );
  }, [localSelectedFiltersSet, originalSelectedFiltersSet, addCurrentSelectionToFilter, uniqueValuesSet]);


  // Clear search text
  const handleClearSearch = useCallback(() => {
    setSearchValue('');
    setDebouncedSearchValue('');
    // When clearing search, it restores the original selection
    setLocalSelectedFiltersSet(new Set(originalSelectedFiltersSet));
  }, [originalSelectedFiltersSet]);

  // Handle sorting
  const handleSortChange = useCallback((e, direction) => {
    multiSortRef.current = e.ctrlKey;
    setLocalSortDirection(localSortDirection === direction ? null : direction);
  }, [localSortDirection]);

  // Handle absolute sorting
  const handleAbsoluteSortToggle = useCallback(() => {
    setLocalAbsoluteSort(prev => !prev);
  }, []);

  // Handle text filter type change
  const handleTextFilterTypeChange = useCallback((e) => {
    setLocalTextFilterType(e.target.value);
  }, []);
  // Handle text filter input change
  const handleTextFilterChange = useCallback((e) => {
    setLocalTextFilter(e.target.value);
  }, []);

  // Handle key down events
  const handleKeyDown = (e) => {
    if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
      // Let Escape still close the popover/menu potentially? Maybe not stop propagation for Escape.
      if (e.key !== 'Escape') {
        e.stopPropagation();
      }
    }
  };

  // Handle popup close
  const handleClose = useCallback(() => {
    setAnchorEl(null);
  }, []);

  // Handle apply button click
  const handleApply = useCallback(() => {
    let finalFilterValues;

    // Scenario 1: No server-side filters + all visible values selected = no filtering
    if (serverSideAppliedFilters.length === 0 && localSelectedFiltersSet.size === uniqueValuesSet.size) {
      finalFilterValues = null;
    }
    // Scenario 2: Server-side filters exist + all visible values selected = preserve server filters
    else if (serverSideAppliedFilters.length > 0 && localSelectedFiltersSet.size === uniqueValuesSet.size) {
      finalFilterValues = serverSideAppliedFilters;
    }
    // Scenario 3: User made new selections
    else {
      let updatedFilters;
      if (addCurrentSelectionToFilter && originalSelectedFiltersSet.size > 0) {
        // Merge the sets and convert to array only when needed
        updatedFilters = Array.from(new Set([...originalSelectedFiltersSet, ...localSelectedFiltersSet]));
      } else {
        // Convert to array only here, at the last possible moment
        updatedFilters = Array.from(localSelectedFiltersSet);
      }

      finalFilterValues = updatedFilters.length !== uniqueValuesSet.size ? updatedFilters : null;
    }

    onApply?.(
      columnId,
      finalFilterValues,
      localTextFilter || null,
      localTextFilter ? localTextFilterType : null,
      localSortDirection,
      localAbsoluteSort,
      multiSortRef.current
    );
    handleClose();
  }, [
    columnId, localSelectedFiltersSet, originalSelectedFiltersSet,
    serverSideAppliedFilters, uniqueValuesSet, addCurrentSelectionToFilter,
    localTextFilter, localTextFilterType, localSortDirection,
    localAbsoluteSort, onApply, handleClose
  ]);


  // Handle cancel button click
  const handleCancel = useCallback(() => {
    // In Excel , Cancel just discards changes
    handleClose();
  }, [handleClose]);

  // Toggle text filter visibility
  const toggleTextFilter = () => {
    setShowTextFilter(!showTextFilter);
    if (!showTextFilter) {
      setLocalTextFilter('');
    }
  };

  // Clear all filters
  const clearAllFilters = useCallback(() => {
    setLocalSelectedFiltersSet(new Set(uniqueValuesSet));
    setServerSideAppliedFilters([]);
    setLocalTextFilter('');
    setLocalSortDirection(null);
    setLocalAbsoluteSort(false);
    setSearchValue('');
    setDebouncedSearchValue('');
  }, [uniqueValuesSet]);


  const handleCopy = useCallback(() => {
    setIsCopied(true);
    onCopy(columnId, columnName);
    setTimeout(() => setIsCopied(false), 2000)
  }, [columnId, columnName, onCopy]);


  // Memoize computed values - if any filter is actually applied
  const hasFilters = uniqueValuesSet.size > 1;
  const isFiltered = selectedFilters.length != 0 || textFilter;
  const hasActiveFilterOrSort = localSelectedFiltersSet.size != 0 && localSelectedFiltersSet.size < uniqueValuesSet.size || localTextFilter || localSortDirection || serverSideAppliedFilters.length > 0;
  const sortLevelClass = sortLevel && sortLevel > 2 ? styles.multiLevelSort :
    sortLevel > 1 ? styles.firstLevelSort :
      sortLevel == 2 ? styles.secondLevelSort : '';

  return (
    <>
      {/* Filter Icon */}
      <div className={`${styles.filterIconWrapper} ${open ? styles.popupOpen : ''}`}>
        <IconButton
          size="small"
          className={`${styles.filterButton} ${isFiltered ? styles.activeFilter : hasFilters ? styles.hasFilter : ''}`}
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
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        classes={{ paper: styles.popoverPaper }}
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
              <Typography>Copy</Typography>
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

            {(filterEnable || hasActiveFilterOrSort) && <Divider className={styles.menuDivider} />}

            {/* Text Filters */}
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
                        {Object.entries(TEXT_FILTER_TYPES).map(([key, value]) => (
                          <MenuItem key={key} value={value}>
                            {TEXT_FILTER_LABELS[value].replace('...', '')}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      placeholder={TEXT_FILTER_LABELS[localTextFilterType]}
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

                {hasActiveFilterOrSort && <Divider className={styles.menuDivider} />}
              </>
            )}

            {hasActiveFilterOrSort && (
              <div
                className={styles.clearFilterOption}
                onClick={clearAllFilters}
              >
                <div className={styles.sortIcon}></div>
                <div className={styles.sortIconPlaceholder}>
                  <FilterAlt fontSize="small" className={styles.menuIcon} />
                </div>
                <Typography>Clear Filter/Sort</Typography>
              </div>
            )}
          </div>

          <Divider />

          {/* Filter section */}
          {filterEnable && uniqueValuesSet.size > 1 && (
            <div className={styles.section}>
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

              {debouncedSearchValue && (
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
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {debouncedSearchValue ? "Select All Search Results" : "(Select All)"}
                        {serverSideFilterSortEnabled && (
                          <Tooltip title="Server-side filter is active. This list is a subset of all data.">
                            <div className={styles.serverFilterChipInSearch}>
                              Srv
                            </div>
                          </Tooltip>
                        )}
                      </Box>
                    }
                    className={styles.selectAllCheckbox}
                  />
                </div>

                <div className={styles.checkboxListContainer}>
                  <VirtualizedList
                    items={filteredUniqueValues}
                    height={200}
                    itemHeight={32}
                    renderItem={({ item: value, index }) => (
                      <FilterListItem
                        key={`${value}.${index}`}
                        value={value}
                        isChecked={localSelectedFiltersSet.has(value)}
                        count={valueCounts.get(value) ?? 0}
                        onChange={handleFilterChange}
                      />
                    )}
                    noItemsComponent={
                      <Typography variant="body2" className={styles.noResults}>
                        No matching values found
                      </Typography>
                    }
                  />
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
  selectedFilters: PropTypes.array,
  textFilter: PropTypes.string,
  textFilterType: PropTypes.oneOf(Object.values(TEXT_FILTER_TYPES)),
  sortDirection: PropTypes.oneOf(['asc', 'desc', null]),
  absoluteSort: PropTypes.bool,
  sortLevel: PropTypes.number,
  onApply: PropTypes.func.isRequired,
  onCopy: PropTypes.func.isRequired,
  filterEnable: PropTypes.bool,
  clipboardText: PropTypes.string,
  valueCounts: PropTypes.instanceOf(Map)
};

FilterSortPopup.defaultProps = {
  textFilter: '',
  textFilterType: TEXT_FILTER_TYPES.CONTAINS,
  sortDirection: null,
  absoluteSort: false,
  filterEnable: false,
  sortLevel: 0,
  uniqueValues: [],
  selectedFilters: [],
  valueCounts: new Map()
};

export default FilterSortPopup;
