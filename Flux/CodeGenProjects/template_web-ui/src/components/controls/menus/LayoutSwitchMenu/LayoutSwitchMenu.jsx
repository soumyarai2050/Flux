import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import Popover from '@mui/material/Popover';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';
import Tooltip from '@mui/material/Tooltip';
import AccountTree from '@mui/icons-material/AccountTree';
import BarChart from '@mui/icons-material/BarChart';
import FormatListNumberedSharp from '@mui/icons-material/FormatListNumberedSharp';
import PivotTableChartSharp from '@mui/icons-material/PivotTableChartSharp';
import TableChartSharp from '@mui/icons-material/TableChartSharp';
import PushPin from '@mui/icons-material/PushPin';
import PushPinOutlined from '@mui/icons-material/PushPinOutlined';
import Hub from '@mui/icons-material/Hub';
import Icon from '../../../ui/Icon';
import MenuItem from '../../../ui/MenuItem';
import { LAYOUT_TYPES } from '../../../../constants';

/**
 * LayoutSwitchMenu renders a menu for switching between different LAYOUT_TYPES.
 * It displays the current layout icon and, when clicked, opens a popover with toggle
 * buttons for each supported layout option.
 *
 * @component
 * @param {Object} props - Component props.
 * @param {string} props.layout - The current layout value.
 * @param {function} props.onLayoutSwitch - Callback invoked when a layout option is selected.
 * @param {string[]} props.supportedLayouts - Array of supported layout identifiers.
 * @returns {JSX.Element} The rendered LayoutSwitchMenu component.
 */
const LayoutSwitchMenu = ({
  layout,
  onLayoutSwitch,
  supportedLayouts,
  isPinned,
  onPinToggle,
  menuType,
  onMenuClose
}) => {
  const [anchorEl, setAnchorEl] = useState(null);

  // Map layout identifiers to corresponding icon components.
  const componentMap = useMemo(() => ({
    [LAYOUT_TYPES.TABLE]: TableChartSharp,
    [LAYOUT_TYPES.TREE]: AccountTree,
    [LAYOUT_TYPES.PIVOT_TABLE]: PivotTableChartSharp,
    [LAYOUT_TYPES.ABBREVIATION_MERGE]: FormatListNumberedSharp,
    [LAYOUT_TYPES.CHART]: BarChart,
    [LAYOUT_TYPES.GRAPH]: Hub,
  }), []);

  const layoutNameMap = useMemo(() => ({
    [LAYOUT_TYPES.TABLE]: 'table',
    [LAYOUT_TYPES.TREE]: 'tree',
    [LAYOUT_TYPES.PIVOT_TABLE]: 'pivot',
    [LAYOUT_TYPES.ABBREVIATION_MERGE]: 'list',
    [LAYOUT_TYPES.CHART]: 'chart',
    [LAYOUT_TYPES.GRAPH]: 'graph'
  }), [])

  const menuName = 'layout-switch';
  const IconComponent = componentMap[layout] || TableChartSharp; // Fallback to TableChartSharp if layout not found.
  const layoutTitle = `layout - ${layoutNameMap[layout] ?? layoutNameMap[LAYOUT_TYPES.TABLE]}`;
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

  const handleLayoutSwitch = (updatedLayoutType) => {
    handlePopoverClose();
    onLayoutSwitch(updatedLayoutType);
  }

  const renderMenu = () => {
    switch (menuType) {
      case 'item':
        const PinCompononent = isPinned ? PushPin : PushPinOutlined;
        return (
          <MenuItem name={menuName} onClick={handlePopoverOpen}>
            <span>
              <IconComponent sx={{ marginRight: '5px' }} fontSize='small' />
              {layoutTitle}
            </span>
            {<PinCompononent onClick={handlePinToggle} fontSize='small' />}
          </MenuItem>
        );
      case 'icon':
      default:
        return (
          <Icon name={menuName} title={menuName} onClick={handlePopoverOpen}>
            <IconComponent fontSize='small' color='white' />
          </Icon>
        );
    }
  }

  return (
    <>
      {renderMenu()}
      <Popover
        id={popoverId}
        open={isPopoverOpen}
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        onClose={handlePopoverClose}
      >
        <ToggleButtonGroup value={layout} size='small'>
          {supportedLayouts.map((layoutType) => {
            const LayoutComponent = componentMap[layoutType];
            const layoutTitle = layoutNameMap[layoutType];
            return (
              <ToggleButton
                key={layoutType}
                name={layoutType}
                value={layoutType}
                onClick={() => handleLayoutSwitch(layoutType)}
              >
                <Tooltip title={layoutTitle} disableInteractive>
                  <LayoutComponent fontSize='small' />
                </Tooltip>
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>
      </Popover>
    </>
  );
};

LayoutSwitchMenu.propTypes = {
  /** The current layout value. Should be one of the Layouts constants. */
  layout: PropTypes.string.isRequired,
  /** Callback invoked when a layout option is selected. */
  onLayoutSwitch: PropTypes.func.isRequired,
  /** Array of supported layout identifiers. */
  supportedLayouts: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default LayoutSwitchMenu;