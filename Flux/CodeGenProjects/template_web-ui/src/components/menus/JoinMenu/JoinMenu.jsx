import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Icon } from '../../Icon';
import { JoinInner, VerticalAlignCenter, SwapHoriz, PushPin, PushPinOutlined } from '@mui/icons-material';
import { Popover, FormControlLabel, Checkbox } from '@mui/material';
import MenuItem from '../../MenuItem';
import { MODEL_TYPES } from '../../../constants';

/**
 * JoinMenu provides an interface for selecting join fields and toggling join options.
 * It renders an icon that opens a popover containing a list of available fields,
 * each with a checkbox. Additionally, when at least one join field is selected,
 * it renders extra icons to toggle centering and flipping of join behavior.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {string[]} props.joinBy - Array of keys representing the currently selected join fields.
 * @param {function} props.onJoinByChange - Callback invoked when a join field is toggled.
 *   Receives the change event and the field key as arguments.
 * @param {Array<{ key: string }>} props.fieldsMetadata - Array of metadata objects for available fields.
 *   Each object must include a unique `key` string.
 * @param {boolean} props.centerJoin - Indicates whether the join should be centered.
 * @param {boolean} props.flip - Indicates whether the join should be flipped.
 * @param {function} props.onCenterJoinToggle - Callback to toggle the center join option.
 * @param {function} props.onFlipToggle - Callback to toggle the flip join option.
 * @returns {JSX.Element} The rendered JoinMenu component.
 */
const JoinMenu = ({
  joinBy,
  onJoinByChange,
  fieldsMetadata,
  centerJoin,
  flip,
  onCenterJoinToggle,
  onFlipToggle,
  isPinned,
  onPinToggle,
  menuType,
  onMenuClose,
  modelType
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

  const menuName = 'join';
  const centerJoinMenuName = 'center-join';
  const flipMenuName = 'flip';
  const isPopoverOpen = Boolean(anchorEl);
  const popoverId = isPopoverOpen ? `${menuName}-popover` : undefined;

  const handlePopoverOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    onMenuClose();
    setAnchorEl(null);
  };

  const handlePinToggle = (e) => {
    e.stopPropagation();
    onPinToggle(menuName, !isPinned);
  }

  if (![MODEL_TYPES.ABBREVIATION_MERGE, MODEL_TYPES.REPEATED_ROOT].includes(modelType)) return null;

  const renderMenu = (menuName) => {
    const PinCompononent = isPinned ? PushPin : PushPinOutlined;
    switch (menuName) {
      case 'join':
        if (menuType === 'item') {
          return (
            <MenuItem name={menuName} onClick={handlePopoverOpen}>
              <span>
                <JoinInner sx={{ marginRight: '5px' }} fontSize='small' />
                {menuName}
              </span>
              {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
            </MenuItem>
          )
        } else {
          return (
            <Icon name={menuName} title={menuName} onClick={handlePopoverOpen}>
              <JoinInner fontSize='small' />
            </Icon>
          )
        }
      case 'center-join':
        if (menuType === 'item') {
          return (
            <MenuItem name={centerJoinMenuName} onClick={onCenterJoinToggle}>
              <span>
                <VerticalAlignCenter sx={{ marginRight: '5px' }} fontSize='small' />
                {menuName}
              </span>
              {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
            </MenuItem>
          )
        } else {
          return (
            <Icon
              name={centerJoinMenuName}
              title={centerJoinMenuName}
              selected={centerJoin}
              onClick={onCenterJoinToggle}
            >
              <VerticalAlignCenter fontSize='small' />
            </Icon>
          )
        }
      case 'flip':
        if (menuType === 'item') {
          return (
            <MenuItem name={flipMenuName} onClick={onFlipToggle}>
              <span>
                <SwapHoriz sx={{ marginRight: '5px' }} fontSize='small' />
                {menuName}
              </span>
              {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
            </MenuItem>
          )
        } else {
          return (
            <Icon
              name={flipMenuName}
              title={flipMenuName}
              selected={flip}
              onClick={onFlipToggle}
            >
              <SwapHoriz fontSize='small' />
            </Icon>
          )
        }
    }
  }

  return (
    <>
      {renderMenu('join')}
      <Popover
        id={popoverId}
        open={isPopoverOpen}
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center'
        }}
        onClose={handlePopoverClose}
      >
        {fieldsMetadata.map((meta) => (
          <MenuItem key={meta.key} dense>
            <FormControlLabel
              sx={{ display: 'flex', flex: 1 }}
              size='small'
              label={meta.key}
              control={
                <Checkbox
                  size='small'
                  checked={joinBy.includes(meta.key)}
                  onChange={(e) => onJoinByChange(e, meta.key)}
                />
              }
            />
          </MenuItem>
        ))}
      </Popover>
      {joinBy && joinBy.length > 0 && ['center-join', 'flip'].map((menu) => renderMenu(menu))}
    </>
  );
};

JoinMenu.propTypes = {
  /** Array of keys representing the currently selected join fields. */
  joinBy: PropTypes.arrayOf(PropTypes.string).isRequired,
  /** Callback invoked when a join field is toggled.
   * Receives the event and the field key as arguments.
   */
  onJoinByChange: PropTypes.func.isRequired,
  /** Array of metadata objects for available fields.
   * Each object must include a unique `key` string.
   */
  fieldsMetadata: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
    })
  ).isRequired,
  /** Boolean indicating whether the join should be centered. */
  centerJoin: PropTypes.bool.isRequired,
  /** Boolean indicating whether the join should be flipped. */
  flip: PropTypes.bool.isRequired,
  /** Callback to toggle the center join option. */
  onCenterJoinToggle: PropTypes.func.isRequired,
  /** Callback to toggle the flip join option. */
  onFlipToggle: PropTypes.func.isRequired,
};

export default JoinMenu;