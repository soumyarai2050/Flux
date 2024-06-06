import React from 'react';
import PropTypes from 'prop-types';
import { Box, TableHead, TableSortLabel, TableRow, TableCell, IconButton, Tooltip } from '@mui/material';
import { ContentCopy } from '@mui/icons-material';
import { visuallyHidden } from '@mui/utils';
import { useTheme } from '@emotion/react';
import classes from './TableHead.module.css';

const CustomHeadCell = (props) => {
    const { prefixCells, sortOrders, suffixCells, onRemoveSort, onRequestSort } = props;
    const theme = useTheme();

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

    let emptyPrefixCells;
    if (prefixCells && prefixCells > 0) {
        emptyPrefixCells = Array(prefixCells).fill().map((_, i) => {
            return (
                <TableCell key={i} />
            )
        })
    }

    let emptySuffixCells;
    if (suffixCells && suffixCells > 0) {
        emptySuffixCells = Array(suffixCells).fill().map((_, i) => {
            return (
                <TableCell key={i} />
            )
        })
    }

    return (
        <TableHead className={classes.head}>
            <TableRow>
                {emptyPrefixCells}
                {props.headCells.map((cell, index) => {
                    // don't add cells which starts with xpath or cells that are hidden
                    if (cell.key.startsWith('xpath_') || cell.hide) {
                        return;
                    }
                    let tableHeadColor = theme.palette.text.primary;
                    if (cell.nameColor) {
                        const color = cell.nameColor.toLowerCase();
                        tableHeadColor = theme.palette.text[color];
                    }
                    const cellKey = props.collectionView ? cell.key : cell.tableTitle;
                    const sortOrder = sortOrders.find(o => o.order_by === cellKey);
                    return (
                        <TableCell
                            key={index}
                            className={`${classes.cell}`}
                            sx={{ color: `${tableHeadColor} !important` }}
                            align='center'
                            padding='normal'
                            sortDirection={sortOrder ? sortOrder.sort_type : false}>
                            {props.copyColumnHandler && (
                                <Tooltip title="Click to copy column" disableInteractive>
                                    <IconButton className={classes.icon} size='small' onClick={() => props.copyColumnHandler(cellKey)}>
                                        <ContentCopy fontSize='small' />
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
                                    <Box component="span" sx={visuallyHidden}>
                                        {sortOrder.sort_type === 'desc' ? 'sorted descending' : 'sorted ascending'}
                                    </Box>
                                ) : null}
                            </TableSortLabel>
                        </TableCell>
                    )
                })}
                {emptySuffixCells}
            </TableRow>
        </TableHead>
    );
}

CustomHeadCell.propTypes = {
    onRequestSort: PropTypes.func.isRequired,
};

export default CustomHeadCell;