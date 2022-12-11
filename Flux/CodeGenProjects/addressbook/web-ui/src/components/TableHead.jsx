import React from 'react';
import { Box, TableHead, TableSortLabel, TableRow, TableCell } from '@mui/material';
import PropTypes from 'prop-types';
import { visuallyHidden } from '@mui/utils';
import { makeStyles } from '@mui/styles';

const useStyles = makeStyles({
    tableHead: {
        background: '#0097a7',
        color: 'white !important',
        whiteSpace: 'nowrap'
    },
    tableCell: {
        color: 'white !important',
        padding: '12px !important'
    }
})

const CustomHeadCell = (props) => {

    const classes = useStyles();
    const { order, orderBy, onRequestSort } = props;

    const createSortHandler = (property) => (event) => {
        onRequestSort(event, property);
    };

    return (
        <TableHead className={classes.tableHead}>
            <TableRow>
                {/* {props.mode === 'edit' && <TableCell />} */}
                {props.headCells.map((cell, index) => {
                    if (cell.key.startsWith('xpath_') || cell.hide) return;
                    return (
                        <TableCell
                            key={index}
                            className={classes.tableCell}
                            align='center'
                            padding='normal'
                            sortDirection={orderBy === cell.key ? order : false}>
                            <TableSortLabel
                                active={orderBy === cell.tableTitle}
                                direction={orderBy === cell.tableTitle ? order : 'asc'}
                                onClick={createSortHandler(cell.tableTitle)}>

                                {cell.tableTitle ? cell.tableTitle : cell.key}
                                
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