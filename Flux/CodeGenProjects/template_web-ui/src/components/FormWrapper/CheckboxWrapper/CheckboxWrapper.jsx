import React from 'react';
import { Checkbox } from '@mui/material';

const CheckboxWrapper = ({ type, value, onChange, disabled, ...props }) => {
  return (
    <Checkbox
      checked={value || false}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      {...props}
    />
  );
};

export default CheckboxWrapper; 