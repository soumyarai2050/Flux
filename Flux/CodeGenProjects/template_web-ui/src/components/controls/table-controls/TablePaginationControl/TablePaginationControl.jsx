import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import IconButton from '@mui/material/IconButton';
import KeyboardArrowLeft from '@mui/icons-material/KeyboardArrowLeft';
import KeyboardArrowRight from '@mui/icons-material/KeyboardArrowRight';

const TablePaginationControl = (
  { rowsLength,
    page,
    rowsPerPage,
    onPageChange,
    onRowsPerPageChange,
    rowsPerPageOptions = [25, 50, 100] }
) => {
  // Use totalCount if provided (server-side pagination), otherwise use rows.length (client-side)
  const totalPages = Math.ceil(rowsLength / rowsPerPage);
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1,
        paddingY: 0.25,
        paddingX: 1,
        justifyContent: 'flex-end',
        borderTop: '1px solid',
        borderColor: 'divider',
        position: 'sticky',
        bottom: 0,
        zIndex: 10,
        bgcolor: 'background.paper',
        minHeight: '32px',
      }}
    >
      {/* Rows per page section */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
          Rows per page:
        </Typography>
        <FormControl
          size="small"
          sx={{
            minWidth: 100,
            '& .MuiSelect-select': {
              fontSize: '0.75rem',
              padding: '4px 8px',
            },
            '& fieldset': {
              borderWidth: '1px !important',
            },
          }}
        >
          <Select value={rowsPerPage} onChange={onRowsPerPageChange} label="">
            {rowsPerPageOptions.map((opt) => (
              <MenuItem key={opt} value={opt}>
                {opt}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Page range and navigation buttons */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <FormControl
          size="small"
          sx={{
            minWidth: 100,
            '& .MuiSelect-select': {
              fontSize: '0.75rem',
              padding: '4px 8px',
            },
            '& .MuiOutlinedInput-root': {
              height: '28px',
            },
            '& fieldset': {
              borderWidth: '1px !important',
            },
          }}
        >
          <Select
            value={`${page * rowsPerPage + 1}-${Math.min((page + 1) * rowsPerPage, rowsLength)}`}
            onChange={(e) => {
              const selectedRange = e.target.value;
              const start = parseInt(selectedRange.split('-')[0], 10);
              const newPage = Math.floor((start - 1) / rowsPerPage);
              onPageChange(newPage);
            }}
          >
            {Array.from({ length: totalPages }, (_, i) => {
              const start = i * rowsPerPage + 1;
              const end = Math.min((i + 1) * rowsPerPage, rowsLength);
              return (
                <MenuItem key={i} value={`${start}-${end}`}>
                  {`${start}-${end} of ${rowsLength}`}
                </MenuItem>
              );
            })}
          </Select>
        </FormControl>

        {/* Navigation Arrows */}
        <IconButton onClick={() => onPageChange(page - 1)} disabled={page === 0}>
          <KeyboardArrowLeft />
        </IconButton>
        <IconButton onClick={() => onPageChange(page + 1)} disabled={page === totalPages - 1}>
          <KeyboardArrowRight />
        </IconButton>
      </Box>
    </Box>
  )
}

export default TablePaginationControl;