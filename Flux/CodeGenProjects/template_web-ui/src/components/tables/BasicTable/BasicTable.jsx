import React from 'react';
import { Table, TableHead, TableBody, TableCell, TableRow } from '@mui/material';

const BasicTable = ({
    rows,
    columns,
    onSelect
}) => {

    return (
        <Table size='small'>
            <TableHead>
                <TableRow>
                    {columns.map((column) => (
                        <TableCell key={column.key}>{column.key}</TableCell>
                    ))}
                </TableRow>
            </TableHead>
            <TableBody>
                {rows.map((row) => (
                    <TableRow key={row['data-id']} onClick={() => onSelect(row['data-id'])}>
                        {columns.map((column) => (
                            <TableCell key={row['data-id'] + column.key}>{row[column.key]}</TableCell>
                        ))}
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    )
}

export default BasicTable;