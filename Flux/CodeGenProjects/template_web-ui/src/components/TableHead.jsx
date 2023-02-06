import React from 'react';
import { Box, TableHead, TableSortLabel, TableRow, TableCell } from '@mui/material';
import PropTypes from 'prop-types';
import { visuallyHidden } from '@mui/utils';
import classes from './TableHead.module.css';

const CustomHeadCell = (props) => {
    const { order, orderBy, onRequestSort } = props;

    const createSortHandler = (property) => (event) => {
        onRequestSort(event, property);
    };

    return (
        <TableHead className={classes.head}>
            <TableRow>
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
                            sortDirection={orderBy === cell.key ? order : false}>
                            <TableSortLabel
                                active={orderBy === cell.tableTitle}
                                direction={orderBy === cell.tableTitle ? order : 'asc'}
                                onClick={createSortHandler(cell.tableTitle)}>

                                {cell.elaborateTitle ? cell.tableTitle : cell.title ? cell.title : cell.key}

                                {orderBy === cell.key ? (
                                    <Box component="span" sx={visuallyHidden}>
                                        {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
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
    order: PropTypes.oneOf(['asc', 'desc']).isRequired,
    orderBy: PropTypes.string.isRequired
};

export default CustomHeadCell;