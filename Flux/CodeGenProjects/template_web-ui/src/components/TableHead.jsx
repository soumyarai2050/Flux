import React from 'react';
import { Box, TableHead, TableSortLabel, TableRow, TableCell } from '@mui/material';
import PropTypes from 'prop-types';
import { visuallyHidden } from '@mui/utils';
import { makeStyles } from '@mui/styles';
import { ColorTypes } from '../constants';

const useStyles = makeStyles({
    tableHead: {
        background: '#0097a7',
        color: 'white !important',
        whiteSpace: 'nowrap'
    },
    tableCell: {
        color: 'white !important',
        padding: '12px !important'
    },
    cellCritical: {
        color: '#9C0006 !important',
        animation: `$blink 0.5s step-start infinite`
    },
    cellError: {
        color: '#9C0006 !important'
    },
    cellInfo: {
        color: 'blue !important'
    },
    cellWarning: {
        color: '#9c6500 !important'
    },
    cellSuccess: {
        color: 'darkgreen !important'
    },
    cellDebug: {
        color: 'black !important'
    },
    "@keyframes blink": {
        "from": {
            opacity: 1
        },
        "50%": {
            opacity: 0.8
        },
        "to": {
            opacity: 1
        }
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

                    let tableCellColorClass = '';
                    if (cell.nameColor) {
                        let color = cell.nameColor.toLowerCase();
                        if (color === ColorTypes.CRITICAL) tableCellColorClass = classes.cellCritical;
                        else if (color === ColorTypes.ERROR) tableCellColorClass = classes.cellError;
                        else if (color === ColorTypes.WARNING) tableCellColorClass = classes.cellWarning;
                        else if (color === ColorTypes.INFO) tableCellColorClass = classes.cellInfo;
                        else if (color === ColorTypes.SUCCESS) tableCellColorClass = classes.cellSuccess;
                        else if (color === ColorTypes.DEBUG) tableCellColorClass = classes.cellDebug;
                    }

                    return (
                        <TableCell
                            key={index}
                            className={`${classes.tableCell} ${tableCellColorClass}`}
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