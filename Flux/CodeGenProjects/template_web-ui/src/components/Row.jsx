import React, { useMemo } from 'react';
import { TableRow } from '@mui/material';
import PropTypes from 'prop-types';
import _ from 'lodash';
import { getDataxpath } from '../utils';
import { Modes } from '../constants';
import Cell from './Cell';
import classes from './Row.module.css';

const Row = (props) => {
    const {
        className,
        row,
        cells,
        selected,
        mode,
        onRowSelect,
        onRowDisselect,
        data,
        originalData,
        collections,
        onUpdate,
        onRowClick,
        onButtonClick,
        onCheckboxChange,
        onTextChange,
        onSelectItemChange,
        onAutocompleteOptionChange,
        onDateTimeChange,
    } = props

    let rowClass = `${classes.row} ${className}`
    let rowindex = row['data-id'];

    return useMemo(() => (
        <TableRow
            className={rowClass}
            hover
            selected={selected}
            onDoubleClick={(e) => onRowDisselect(e, rowindex)}
            onClick={(e) => onRowSelect(e, rowindex)}>

            {cells.map((cell, i) => {
                let collection = collections.filter(c => c.tableTitle === cell.tableTitle)[0];
                let xpath = row['xpath_' + cell.key];
                if (cell.tableTitle && cell.tableTitle.indexOf('.') > -1) {
                    xpath = row[cell.tableTitle.substring(0, cell.tableTitle.lastIndexOf('.')) + '.xpath_' + cell.key]
                }

                let disabled = false;
                if (row[cell.tableTitle] === undefined) {
                    disabled = true;
                } else if (mode === Modes.EDIT_MODE) {
                    if (collection && collection.ormNoUpdate && !row['data-add']) {
                        disabled = true;
                    } else if (collection.uiUpdateOnly && row['data-add']) {
                        disabled = true;
                    } else if (row['data-remove']) {
                        disabled = true;
                    }
                }

                let dataxpath = getDataxpath(data, xpath);
                let dataAdd = row['data-add'] ? row['data-add'] : false;
                let dataRemove = row['data-remove'] ? row['data-remove'] : false;
                let value = row[cell.tableTitle];
                let previousValue = _.get(originalData, xpath);

                if (cell.hide) return;

                return (
                    <Cell
                        key={i}
                        mode={mode}
                        rowindex={rowindex}
                        name={cell.key}
                        elaborateTitle={cell.tableTitle}
                        currentValue={value}
                        previousValue={previousValue}
                        collection={collection}
                        xpath={xpath}
                        dataxpath={dataxpath}
                        dataAdd={dataAdd}
                        dataRemove={dataRemove}
                        disabled={disabled}
                        onUpdate={onUpdate}
                        onDoubleClick={onRowClick}
                        onButtonClick={onButtonClick}
                        onCheckboxChange={onCheckboxChange}
                        onTextChange={onTextChange}
                        onSelectItemChange={onSelectItemChange}
                        onAutocompleteOptionChange={onAutocompleteOptionChange}
                        onDateTimeChange={onDateTimeChange}
                        onFormUpdate={props.onFormUpdate}
                    />
                )
            })}
        </TableRow>
    ), [
        className,
        row,
        selected,
        mode,
        onRowSelect,
        onRowDisselect,
        data,
        originalData,
        collections,
        onUpdate,
        onRowClick,
        onButtonClick,
        onCheckboxChange,
        onTextChange,
        onSelectItemChange,
        onAutocompleteOptionChange,
        onDateTimeChange,
    ])
}

Row.propTypes = {
    className: PropTypes.string,
    row: PropTypes.object.isRequired,
    cells: PropTypes.array.isRequired,
    selected: PropTypes.bool.isRequired,
    mode: PropTypes.oneOf([Modes.READ_MODE, Modes.EDIT_MODE]).isRequired,
    data: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    originalData: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    collections: PropTypes.array.isRequired,
    onUpdate: PropTypes.func.isRequired,
    onRowSelect: PropTypes.func.isRequired,
    onRowDisselect: PropTypes.func.isRequired,
    onRowClick: PropTypes.func.isRequired,
    onButtonClick: PropTypes.func.isRequired,
    onCheckboxChange: PropTypes.func.isRequired,
    onTextChange: PropTypes.func.isRequired,
    onSelectItemChange: PropTypes.func.isRequired,
    onAutocompleteOptionChange: PropTypes.func.isRequired,
    onDateTimeChange: PropTypes.func.isRequired
}

export default Row;