import React from 'react';
import PropTypes from 'prop-types';
import { FileDownload, PushPin, PushPinOutlined } from '@mui/icons-material';
import Icon from '../../Icon';
import MenuItem from '../../MenuItem';

/**
 * DownloadMenu renders a clickable icon that triggers a download action.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {Function} props.onDownload - Callback function invoked when the download icon is clicked.
 * @returns {JSX.Element} The rendered DownloadMenu component.
 */
const DownloadMenu = ({
  onDownload,
  isPinned,
  onPinToggle,
  menuType
}) => {
  const menuName = 'download';

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={onDownload}>
            <span>
              <FileDownload sx={{ marginRight: '5px' }} fontSize='small' />
              {menuName}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={onDownload}>
            <FileDownload fontSize='small' />
          </Icon>
        );
    }
  }
  return renderMenu();
};

DownloadMenu.propTypes = {
  /** Callback invoked when the download icon is clicked. */
  onDownload: PropTypes.func.isRequired,
};

export default DownloadMenu;