import React from 'react';
import { Box, TableHead, TableSortLabel, TableRow, TableCell, IconButton, Tooltip } from '@mui/material';
import { ContentCopy } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { visuallyHidden } from '@mui/utils';
import classes from './TableHead.module.css';
import { useTheme } from '@emotion/react';

const CustomHeadCell = (props) => {
    const { order, orderBy, onRequestSort, prefixCells, suffixCells } = props;
    const theme = useTheme();

    const createSortHandler = (property) => (event) => {
        onRequestSort(event, property);
    };

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
                    if (cell.key.startsWith('xpath_') || cell.hide) return;

                    let tableHeadColor = theme.palette.text.primary;
                    if (cell.nameColor) {
                        const color = cell.nameColor.toLowerCase();
                        tableHeadColor = theme.palette.text[color];
                        console.log(tableHeadColor);
                    }
                    const cellKey = props.collectionView ? cell.key : cell.tableTitle;
                    return (
                        <TableCell
                            key={index}
                            className={`${classes.cell}`}
                            sx={{color: `${tableHeadColor} !important`}}
                            align='center'
                            padding='normal'
                            sortDirection={orderBy === cellKey ? order : false}>
                            {props.copyColumnHandler && (
                                <Tooltip title="Click to copy column">
                                    <IconButton className={classes.icon} size='small' onClick={() => props.copyColumnHandler(cellKey)}>
                                        <ContentCopy fontSize='small' />
                                    </IconButton>
                                </Tooltip>
                            )}
                            <TableSortLabel
                                active={orderBy === cellKey}
                                direction={orderBy === cellKey ? order : 'asc'}
                                onClick={createSortHandler(cellKey)}>
                                {cell.elaborateTitle ? cell.tableTitle : cell.title ? cell.title : cell.key}
                                {orderBy === cellKey ? (
                                    <Box component="span" sx={visuallyHidden}>
                                        {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
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
    order: PropTypes.oneOf(['asc', 'desc']).isRequired,
    orderBy: PropTypes.string.isRequired
};

export default CustomHeadCell;