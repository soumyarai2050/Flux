import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ColorLens, PushPin, PushPinOutlined } from '@mui/icons-material';
import { DataSourceHexColorPopup } from '../../Popup';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';

/**
 * DataSourceColorMenu renders an icon that opens a popup for managing data source colors.
 * The menu is only displayed when the `joinBy` prop is provided and non-empty.
 *
 * @component
 * @param {Object} props - Component properties.
 * @param {string|string[]} props.joinBy - Value(s) used to determine data source grouping; if empty, the menu is not rendered.
 * @param {number} props.maxRowSize - Maximum number of rows to display in the popup.
 * @param {Array} props.dataSourceColors - An array mapping data source identifiers to their hex color codes.
 * @param {Function} props.onDataSourceColorsChange - Callback function invoked when the data source colors are updated.
 * @returns {JSX.Element|null} The rendered DataSourceColorMenu component, or null if `joinBy` is empty.
 */
const DataSourceColorMenu = ({
  joinBy,
  maxRowSize,
  dataSourceColors,
  onDataSourceColorsChange,
  isPinned,
  onPinToggle,
  menuType
}) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  const handleDataSourcePopupOpen = () => {
    setIsPopupOpen(true);
  };

  const handleDataSourcePopupClose = () => {
    setIsPopupOpen(false);
  };

  // Render nothing if joinBy is not provided or is empty.
  if (!joinBy || joinBy.length === 0) return null;

  const menuName = 'data-source-color';

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handleDataSourcePopupOpen}>
            <span>
              <ColorLens sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon
            name={menuName}
            title={menuName}
            selected={isPopupOpen}
            onClick={handleDataSourcePopupOpen}
          >
            <ColorLens fontSize='small' />
          </Icon>
        );
    }
  }

  return (
    <>
      {renderMenu()}
      <DataSourceHexColorPopup
        open={isPopupOpen}
        onClose={handleDataSourcePopupClose}
        maxRowSize={maxRowSize}
        dataSourceColors={dataSourceColors}
        onSave={onDataSourceColorsChange}
      />
    </>
  );
};

DataSourceColorMenu.propTypes = {
  /** Value(s) used for grouping data sources; menu is rendered only if provided and non-empty. */
  joinBy: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.arrayOf(PropTypes.string),
  ]).isRequired,
  /** Maximum number of rows to display in the color popup. */
  maxRowSize: PropTypes.number.isRequired,
  /** Mapping of data source identifiers to their respective hex color codes. */
  dataSourceColors: PropTypes.arrayOf(PropTypes.string).isRequired,
  /** Callback function triggered when the data source colors are updated. */
  onDataSourceColorsChange: PropTypes.func.isRequired,
};

export default DataSourceColorMenu;