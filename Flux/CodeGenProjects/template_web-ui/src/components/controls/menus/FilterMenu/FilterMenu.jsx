import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import FilterAlt from '@mui/icons-material/FilterAlt';
import PushPin from '@mui/icons-material/PushPin';
import PushPinOutlined from '@mui/icons-material/PushPinOutlined';
import { MODEL_TYPES } from '../../../../constants';
import Icon from '../../../ui/Icon';
import MenuItem from '../../../ui/MenuItem';
import FilterDialog from './FilterDialog';
import styles from './FilterMenu.module.css';

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
 * @returns {JSX.Element} The rendered FilterMenu component.
 */
const FilterMenu = ({
  fieldsMetadata,
  isPinned,
  onPinToggle,
  menuType,
  modelType,
  filters,
  onFiltersChange,
  onMenuClose,
  uniqueValues,
  sortOrders,
  onSortOrdersChange,
  groupedRows,
  serverSideFilterSortEnabled
}) => {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const menuName = 'filter';

  // const filterFieldsMetadata = useMemo(() => fieldsMetadata.filter(meta => meta.filterEnable), []);

  // if (filterFieldsMetadata.length === 0) return null;

  const handlePopoverOpen = () => {
    setIsPopoverOpen(true);
  }

  const handlePopoverClose = () => {
    setIsPopoverOpen(false);
    onMenuClose();
  }

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinComponent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handlePopoverOpen}>
            <span>
              <FilterAlt sx={{ marginRight: '5px' }} fontSize='small' />
              {/* {menuName} */}
              filter/sort
            </span>
            {<PinComponent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={'filter/sort'} onClick={handlePopoverOpen}>
            <FilterAlt fontSize='small' color='white' />
          </Icon>
        );
    }
  }

  return (
    <>
      {renderMenu()}
      <FilterDialog
        isOpen={isPopoverOpen}
        filters={filters}
        fieldsMetadata={fieldsMetadata}
        uniqueValues={uniqueValues}
        isCollectionModel={modelType === MODEL_TYPES.ABBREVIATION_MERGE}
        onFiltersChange={onFiltersChange}
        onClose={handlePopoverClose}
        sortOrders={sortOrders}
        onSortOrdersChange={onSortOrdersChange}
        groupedRows={groupedRows}
        serverSideFilterSortEnabled={serverSideFilterSortEnabled}
      />
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
};

export default FilterMenu;