import React from 'react';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';

const DropdownWrapper = ({ value, onChange, options = [], disabled, ...props }) => {
  return (
    <Select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      variant="outlined"
      size="small"
      {...props}
    >
      {options.map((option) => (
        <MenuItem key={option} value={option}>
          {option}
        </MenuItem>
      ))}
    </Select>
  );
};

export default DropdownWrapper; 