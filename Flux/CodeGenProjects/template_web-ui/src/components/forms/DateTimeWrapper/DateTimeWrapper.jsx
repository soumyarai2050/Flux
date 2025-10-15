import React from 'react';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Clear from '@mui/icons-material/Clear';

const DateTimeWrapper = ({ type, value, onChange, disabled, ...props }) => {
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <DateTimePicker
        value={value || null}
        onChange={(newValue) => {
          if (newValue) {
            const newDate = new Date(newValue);
            newDate.setSeconds(0, 0);
            onChange(newDate.toISOString());
          } else {
            onChange(null);
          }
        }}
        disabled={disabled}
        inputFormat="YYYY-MM-DD HH:mm:ss"
        hideTabs={false}
        disablePast
        openTo="hours"
        renderInput={(params) => (
          <TextField
            {...params}
            variant="outlined"
            size="small"
            InputProps={{
              ...params.InputProps,
              readOnly: true,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={(e) => {
                      onChange(null);
                      e.stopPropagation();
                    }}
                    disabled={!value || disabled}
                    size="small"
                  >
                    <Clear fontSize="small" />
                  </IconButton>
                </InputAdornment>
              )
            }}
          />
        )}
        {...props}
      />
    </LocalizationProvider>
  );
};

export default DateTimeWrapper; 