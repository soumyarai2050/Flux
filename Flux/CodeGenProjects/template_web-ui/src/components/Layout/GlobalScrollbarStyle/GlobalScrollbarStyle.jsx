import React from 'react';
import GlobalStyles from '@mui/material/GlobalStyles';
import { useTheme } from '@mui/material/styles';
import { cssVar, baseColorPalettes, BaseColor } from '../../../theme'; // Assuming theme utilities are here

const GlobalScrollbarStyle = ({ selectedBaseColorName }) => {
  const theme = useTheme(); // MUI theme, not your custom Theme object
  const selectedPalette = baseColorPalettes[selectedBaseColorName] || baseColorPalettes[BaseColor.GREEN];

  // Use the dark variant of the selected base color for the scrollbar thumb
  // And a slightly lighter or neutral color for the track, can be from grey palette or a lighter base color variant
  const scrollbarThumbColor = cssVar(selectedPalette.dark);
  const scrollbarTrackColor = theme.palette.mode === 'dark' ? cssVar('--dark-primary-main') : cssVar('--light-primary-main'); // Example track colors

  return (
    <GlobalStyles
      styles={{
        '*::-webkit-scrollbar': {
          width: '10px',
          height: '10px'
        },
        '*::-webkit-scrollbar-track': {
          background: scrollbarTrackColor,
        },
        '*::-webkit-scrollbar-thumb': {
          background: scrollbarThumbColor,
          borderRadius: '5px',
        },
        '*::-webkit-scrollbar-thumb:hover': {
          background: cssVar(selectedPalette.medium), // Example hover: medium variant
        },
        '*': {
          scrollbarWidth: 'thin',
          scrollbarColor: `${scrollbarThumbColor} ${scrollbarTrackColor}`,
        },
      }}
    />
  );
};

export default GlobalScrollbarStyle; 