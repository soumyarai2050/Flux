import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { FilterAlt, PushPin, PushPinOutlined } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';
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
 * @param {function} props.onOpen - Callback function.
 * @returns {JSX.Element} The rendered FilterMenu component.
 */
const FilterMenu = ({
  fieldsMetadata,
  isPinned,
  onPinToggle,
  menuType,
  onOpen
}) => {
  const menuName = 'filter';

  const filterFieldsMetadata = useMemo(() => fieldsMetadata.filter(meta => meta.filterEnable), []);

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
          <MenuItem name={menuName} onClick={onOpen}>
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
          <Icon name={menuName} title={menuName} onClick={onOpen}>
            <FilterAlt fontSize='small' />
          </Icon>
        );
    }
  }

  return (
    <>
      {renderMenu()}
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
  onOpen: PropTypes.func.isRequired
};

export default FilterMenu;