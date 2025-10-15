import React from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';

const AutocompleteWrapper = ({ value, onChange, options = [], disabled, ...props }) => {
  return (
    <Autocomplete
      options={options}
      getOptionLabel={(option) => option?.toString() || ''}
      isOptionEqualToValue={(option, value) => option === value || (option === 0 && value === 0)}
      value={value}
      onChange={(e, newValue) => onChange(newValue)}
      disabled={disabled}
      renderInput={(params) => (
        <TextField {...params} variant="outlined" size="small" />
      )}
      disableClearable
      forcePopupIcon={false}
      {...props}
    />
  );
};

export default AutocompleteWrapper; 