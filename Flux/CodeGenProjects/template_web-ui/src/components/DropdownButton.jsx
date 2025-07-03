import React, { useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import Button from '@mui/material/Button';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import classes from './DropdownButton.module.css';

export default function DropdownButton({
  options,
  renderButtonContent,
  renderOption,
  onOptionSelect,
  initialSelectedIndex = 0,
  selectedIndex: controlledSelectedIndex,
  ...rest // Pass other ButtonProps like variant, color, sx, etc.
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [internalSelectedIndex, setInternalSelectedIndex] = useState(initialSelectedIndex);
  const open = Boolean(anchorEl);

  // Use controlled selectedIndex if provided, otherwise use internal state
  const selectedIndex = controlledSelectedIndex !== undefined ? controlledSelectedIndex : internalSelectedIndex;

  // Update internal state when controlledSelectedIndex changes
  useEffect(() => {
    if (controlledSelectedIndex !== undefined) {
      setInternalSelectedIndex(controlledSelectedIndex);
    }
  }, [controlledSelectedIndex]);

  // Memoize the selected option to avoid re-computation
  const selectedOption = useMemo(
    () => options[selectedIndex],
    [options, selectedIndex]
  );

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuItemClick = (event, index) => {
    // Only update internal state if not controlled
    if (controlledSelectedIndex === undefined) {
      setInternalSelectedIndex(index);
    }
    setAnchorEl(null);
    if (onOptionSelect) {
      onOptionSelect(options[index], index);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <div className={classes.dropdown_container}>
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
  /** Optional: Controlled selected index that can be changed externally. */
  selectedIndex: PropTypes.number,
};