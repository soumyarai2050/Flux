import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import Button from '@mui/material/Button';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';

export default function DropdownButton({
  options,
  renderButtonContent,
  renderOption,
  onOptionSelect,
  initialSelectedIndex = 0,
  ...rest // Pass other ButtonProps like variant, color, sx, etc.
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(initialSelectedIndex);
  const open = Boolean(anchorEl);

  // Memoize the selected option to avoid re-computation
  const selectedOption = useMemo(
    () => options[selectedIndex],
    [options, selectedIndex]
  );

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuItemClick = (event, index) => {
    setSelectedIndex(index);
    setAnchorEl(null);
    if (onOptionSelect) {
      onOptionSelect(options[index], index);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <div>
      <Button
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={handleClick}
        endIcon={<ArrowDropDownIcon />}
        {...rest} // Spread the rest of the props here
      >
        {/* Use the render prop for the button's content */}
        {renderButtonContent(selectedOption)}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        {options.map((option, index) => (
          <MenuItem
            key={index} // Using index as key is acceptable if the list is static
            selected={index === selectedIndex}
            onClick={(event) => handleMenuItemClick(event, index)}
          >
            {/* Use the render prop for the menu item's content */}
            {renderOption(option, index, index === selectedIndex)}
          </MenuItem>
        ))}
      </Menu>
    </div>
  );
}

// --- PropTypes for runtime type checking and documentation ---
DropdownButton.propTypes = {
  /** The array of options to display in the dropdown. */
  options: PropTypes.array.isRequired,
  /** A function that renders the content of the button. */
  renderButtonContent: PropTypes.func.isRequired,
  /** A function that renders a single option in the menu list. */
  renderOption: PropTypes.func.isRequired,
  /** Optional: Callback function when an option is selected. */
  onOptionSelect: PropTypes.func,
  /** Optional: The initially selected index. Defaults to 0. */
  initialSelectedIndex: PropTypes.number,
};