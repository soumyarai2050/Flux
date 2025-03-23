import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Box, TableHead, TableSortLabel, TableRow, TableCell, IconButton, Tooltip } from '@mui/material';
import { ContentCopy, LibraryAddCheckRounded } from '@mui/icons-material';
import { visuallyHidden } from '@mui/utils';
import { useTheme } from '@emotion/react';
import classes from './TableHead.module.css';

const CustomHeadCell = ({
    sortOrders,
    onRemoveSort,
    onRequestSort,
    headCells,
    copyColumnHandler,
    collectionView
}) => {
    const theme = useTheme();
    const [copiedCellId, setCopiedCellId] = useState(null);

    const createSortHandler = (property) => (event) => {
        let retainSortLevel = false;
        if (event.ctrlKey) {
            retainSortLevel = true;
        }
        onRequestSort(event, property, retainSortLevel);
    };

    const removeSortHandler = (property) => {
        onRemoveSort(property);
    }

    const handleColumnCopy = (cell) => {
        const cellKey = collectionView ? cell.key : cell.tableTitle;
        setCopiedCellId(cellKey);
        copyColumnHandler(cell);
        setTimeout(() => {
            setCopiedCellId((prev) => prev === cellKey ? null : prev);
        }, 5000)
    }

    return (
        <TableHead className={classes.head}>
            <TableRow>
                {headCells.map((cell) => {
                    // don't add cells which starts with xpath or cells that are hidden
                    // if (cell.key.startsWith('xpath_')) {
                    //     return;
                    // }
                    // if (cell.showLess) return;
                    let tableHeadColor = 'white';
                    if (cell.nameColor) {
                        const color = cell.nameColor.toLowerCase();
                        tableHeadColor = theme.palette.text[color];
                    }
                    const cellKey = collectionView ? cell.key : cell.tableTitle;
                    const sortOrder = sortOrders.find(o => o.order_by === cellKey);
                    const isSelected = copiedCellId === cellKey;
                    const iconText = isSelected ? 'Column copied!' : 'Click to copy column';
                    return (
                        <TableCell
                            key={cellKey}
                            className={`${classes.cell}`}
                            sx={{ color: `${tableHeadColor}` }}
                            align='center'
                            padding='normal'
                            sortDirection={sortOrder ? sortOrder.sort_type : false}>
                            {copyColumnHandler && (
                                <Tooltip title={iconText} disableInteractive>
                                    <IconButton className={classes.icon} size='small' sx={{ color: 'inherit' }} onClick={() => handleColumnCopy(cell)}>
                                        {isSelected ? <LibraryAddCheckRounded sx={{ color: 'success.main' }} fontSize='small' /> : <ContentCopy fontSize='small' />}
                                    </IconButton>
                                </Tooltip>
                            )}
                            <TableSortLabel
                                active={sortOrder !== undefined}
                                direction={sortOrder ? sortOrder.sort_type : 'asc'}
                                onClick={createSortHandler(cellKey)}
                                onDoubleClick={() => removeSortHandler(cellKey)}>
                                {cell.elaborateTitle ? cell.tableTitle : cell.title ? cell.title : cell.key}
                                {sortOrder && sortOrder.order_by === cellKey ? (
                                    <Box component='span' sx={visuallyHidden}>
                                        {sortOrder.sort_type === 'desc' ? 'sorted descending' : 'sorted ascending'}
                                    </Box>
                                ) : null}
                            </TableSortLabel>
                        </TableCell>
                    )
                })}
            </TableRow>
        </TableHead>
    );
}

CustomHeadCell.propTypes = {
    onRequestSort: PropTypes.func.isRequired,
};

export default CustomHeadCell;