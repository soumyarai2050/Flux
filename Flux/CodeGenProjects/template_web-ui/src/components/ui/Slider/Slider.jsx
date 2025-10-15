import React, { useState, useEffect, useRef } from 'react';
import MuiSlider from '@mui/material/Slider';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { debounce } from 'lodash';
import PropTypes from 'prop-types';
import styles from './Slider.module.css';

const Slider = ({ 
  value, 
  onChange, 
  disabled = false, 
  min = 0, 
  max = 100, 
  step = 1,
  marks = false,
  showValue = true,
  showTooltip = true,
  orientation = 'horizontal',
  color = 'primary',
  size = 'small',
  valueLabelFormat,
  track = 'normal',
  ...props 
}) => {
  const [internalValue, setInternalValue] = useState(value || min);
  const debouncedOnChange = useRef(debounce((newValue) => {
    onChange?.(newValue);
  }, 300)).current;

  useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value);
    }
  }, [value]);

  const handleChange = (event, newValue) => {
    setInternalValue(newValue);
    debouncedOnChange(newValue);
  };

  const handleChangeCommitted = (event, newValue) => {
    debouncedOnChange.flush();
  };

  const formatValueLabel = (val) => {
    if (valueLabelFormat) {
      return typeof valueLabelFormat === 'function' ? valueLabelFormat(val) : val;
    }
    return val;
  };

  return (
    <Box className={styles.container}>
      <Box className={styles.sliderWrapper}>
        <MuiSlider
          value={internalValue}
          onChange={handleChange}
          onChangeCommitted={handleChangeCommitted}
          disabled={disabled}
          min={min}
          max={max}
          step={step}
          marks={marks}
          orientation={orientation}
          color={color}
          size={size}
          track={track}
          valueLabelDisplay={showTooltip ? 'auto' : 'off'}
          valueLabelFormat={formatValueLabel}
          className={`${styles.slider} ${disabled ? styles.disabled : ''}`}
          {...props}
        />
        {showValue && (
          <Typography 
            variant="body2" 
            className={styles.valueDisplay}
            color={disabled ? 'text.disabled' : 'text.secondary'}
          >
            {formatValueLabel(internalValue)}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

Slider.propTypes = {
  value: PropTypes.number,
  onChange: PropTypes.func,
  disabled: PropTypes.bool,
  min: PropTypes.number,
  max: PropTypes.number,
  step: PropTypes.number,
  marks: PropTypes.oneOfType([PropTypes.bool, PropTypes.array]),
  showValue: PropTypes.bool,
  showTooltip: PropTypes.bool,
  orientation: PropTypes.oneOf(['horizontal', 'vertical']),
  color: PropTypes.oneOf(['primary', 'secondary']),
  size: PropTypes.oneOf(['small', 'medium']),
  valueLabelFormat: PropTypes.oneOfType([PropTypes.func, PropTypes.string]),
  track: PropTypes.oneOf(['normal', 'inverted', false])
};

export default Slider;