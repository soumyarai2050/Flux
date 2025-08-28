import React from 'react';
import { Select, MenuItem } from '@mui/material';

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