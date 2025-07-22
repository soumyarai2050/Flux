import React, { useState, useEffect, useRef } from 'react';
import { TextField } from '@mui/material';
import { NumericFormat } from 'react-number-format';
import { debounce } from 'lodash';
import { DATA_TYPES } from '../../constants';

const TextFieldWrapper = ({ type, value, onChange, disabled, placeholder, decimalScale, ...props }) => {
  const [inputValue, setInputValue] = useState(value);
  const inputRef = useRef(null);
  const cursorPos = useRef(null);
  const debouncedOnChange = useRef(debounce((newValue) => {
    onChange(newValue);
  }, 800)).current;

  useEffect(() => {
    setInputValue(value);
  }, [value]);

  useEffect(() => {
    if (inputRef.current && cursorPos.current !== null) {
      if (inputRef.current.selectionStart !== cursorPos.current) {
        inputRef.current.setSelectionRange(cursorPos.current, cursorPos.current);
      }
    }
  }, [inputValue]);

  const handleChange = (newValue, event) => {
    cursorPos.current = event?.target.selectionStart ?? null;
    setInputValue(newValue);
    debouncedOnChange(newValue);
  };

  const handleBlur = () => {
    debouncedOnChange.flush();
  };

  return (
    <TextField
      value={inputValue || ''}
      onChange={(e) => handleChange(e.target.value, e)}
      disabled={disabled}
      placeholder={placeholder}
      variant="outlined"
      size="small"
      sx={{ minWidth: '100px !important' }}
      onBlur={handleBlur}
      inputProps={{
        ref: inputRef,
        style: { padding: '6px 10px' },
        onKeyDown: (e) => {
          if (!['Tab', 'Enter', 'Escape', 'Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) {
            e.stopPropagation();
          }
        }
      }}
      {...props}
    />
  );
}

export default TextFieldWrapper; 