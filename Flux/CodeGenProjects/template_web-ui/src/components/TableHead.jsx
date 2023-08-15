import React from 'react';
import { Box, TableHead, TableSortLabel, TableRow, TableCell, IconButton, Tooltip } from '@mui/material';
import { ContentCopy } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { visuallyHidden } from '@mui/utils';
import classes from './TableHead.module.css';

const CustomHeadCell = (props) => {
    const { order, orderBy, onRequestSort, prefixCells, suffixCells } = props;

    const createSortHandler = (property) => (event) => {
        onRequestSort(event, property);
    };

    const copyColumnHandler = (cell) => {
        if (props.collectionView) {
            props.copyColumnHandler(cell.key);
        } else {
            props.copyColumnHandler(cell.tableTitle);
        }
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
                    if (cell.key.startsWith('xpath_') || cell.hide) return;

                    let tableCellColorClass = '';
                    if (cell.nameColor) {
                        let color = cell.nameColor.toLowerCase();
                        tableCellColorClass = classes[color];
                    }

                    return (
                        <TableCell
                            key={index}
                            className={`${classes.cell} ${tableCellColorClass}`}
                            align='center'
                            padding='normal'
                            sortDirection={orderBy === cell.tableTitle ? order : false}>
                            {props.copyColumnHandler && (
                                <Tooltip title="Click to copy column">
                                    <IconButton className={classes.icon} size='small' onClick={() => copyColumnHandler(cell)}>
                                        <ContentCopy fontSize='small' />
                                    </IconButton>
                                </Tooltip>
                            )}
                            <TableSortLabel
                                active={orderBy === cell.tableTitle}
                                direction={orderBy === cell.tableTitle ? order : 'asc'}
                                onClick={createSortHandler(cell.tableTitle)}>
                                {cell.elaborateTitle ? cell.tableTitle : cell.title ? cell.title : cell.key}
                                {orderBy === cell.tableTitle ? (
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