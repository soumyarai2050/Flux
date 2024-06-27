import React, { useMemo } from 'react';
import { TableRow } from '@mui/material';
import PropTypes from 'prop-types';
import _ from 'lodash';
import { getDataxpath } from '../utils';
import { DB_ID, Modes } from '../constants';
import Cell from './Cell';
import classes from './Row.module.css';

const Row = (props) => {
    const {
        // className,
        row,
        cells,
        // selected,
        mode,
        onRowSelect,
        onRowDoubleClick,
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

    let rowClass = classes.row;
    let rowindex = row[0]['data-id'];

    return useMemo(() => (
        <TableRow
            className={rowClass}
            hover
            // selected={selected}
            // onClick={(e) => onRowSelect(e, rowindex)}
            onDoubleClick={onRowDoubleClick}>
            {cells.map((cell, i) => {
                const cellRow = row[cell.sourceIndex];
                let selected = cellRow ? props.selectedRows.includes(cellRow['data-id']) : false;
                let collection = collections.filter(c => c.tableTitle === cell.tableTitle)[0];
                let xpath = cellRow?.['xpath_' + cell.key];
                if (cellRow && cell.tableTitle && cell.tableTitle.indexOf('.') > -1) {
                    xpath = cellRow[cell.tableTitle.substring(0, cell.tableTitle.lastIndexOf('.')) + '.xpath_' + cell.key]
                }

                let disabled = false;
                if (cellRow) {
                    if (cellRow[cell.tableTitle] === undefined) {
                        disabled = true;
                    } else if (mode === Modes.EDIT_MODE) {
                        if (collection && collection.ormNoUpdate && !cellRow['data-add']) {
                            disabled = true;
                        } else if (collection.uiUpdateOnly && cellRow['data-add']) {
                            disabled = true;
                        } else if (cellRow['data-remove']) {
                            disabled = true;
                        }
                    }
                }

                let dataxpath = getDataxpath(data, xpath);
                let dataAdd = cellRow && cellRow['data-add'] ? cellRow['data-add'] : false;
                let dataRemove = cellRow && cellRow['data-remove'] ? cellRow['data-remove'] : false;
                let value = cellRow?.[cell.tableTitle];
                let previousValue;
                if (props.widgetType === 'repeatedRoot') {
                    if (cellRow && selected) {
                        const storedObj = originalData.find(obj => obj[DB_ID] === cellRow['data-id']);
                        if (storedObj) {
                            previousValue = _.get(storedObj, xpath);
                        }
                    } else {
                        previousValue = _.get(originalData, xpath);
                    }
                } else {
                    previousValue = _.get(originalData, xpath);
                }
                // let previousValue = _.get(originalData, xpath);
                if (cell.joinKey || cell.commonGroupKey) {
                    if (!value) {
                        const joinedKeyCellRow = row.find(r => r?.[cell.tableTitle] !== null && r?.[cell.tableTitle] !== undefined);
                        if (joinedKeyCellRow) {
                            value = joinedKeyCellRow ? joinedKeyCellRow[cell.tableTitle] : undefined;
                        }
                    }
                }

                if (cell.hide) return;
                let buttonDisable = false;
                if (props.widgetType === 'repeatedRoot' && !selected) {
                    buttonDisable = true;
                }

                return (
                    <Cell
                        key={i}
                        mode={mode}
                        rowindex={rowindex}
                        name={cell.key}
                        elaborateTitle={cell.tableTitle}
                        currentValue={value}
                        previousValue={previousValue}
                        collection={cell}
                        xpath={xpath}
                        dataxpath={dataxpath}
                        dataAdd={dataAdd}
                        dataRemove={dataRemove}
                        disabled={disabled}
                        buttonDisable={buttonDisable}
                        onUpdate={onUpdate}
                        onDoubleClick={onRowClick}
                        onButtonClick={onButtonClick}
                        onCheckboxChange={onCheckboxChange}
                        onTextChange={onTextChange}
                        onSelectItemChange={onSelectItemChange}
                        onAutocompleteOptionChange={onAutocompleteOptionChange}
                        onDateTimeChange={onDateTimeChange}
                        onFormUpdate={props.onFormUpdate}
                        index={props.index}
                        forceUpdate={props.forceUpdate}
                        truncateDateTime={props.truncateDateTime}
                        widgetType={props.widgetType}
                        selected={selected}
                        onForceSave={props.onForceSave}
                        dataSourceId={cellRow ? props.widgetType === 'root' ? props.index : cellRow['data-id'] : null}
                        onRowSelect={onRowSelect}
                        nullCell={cellRow ? false : true}
                        dataSourceColors={props.dataSourceColors}
                    />
                )
            })}
        </TableRow>
    ), [
        // className,
        row,
        // selected,
        mode,
        onRowSelect,
        onRowDoubleClick,
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
    // className: PropTypes.string,
    // row: PropTypes.object.isRequired,
    cells: PropTypes.array.isRequired,
    // selected: PropTypes.bool.isRequired,
    mode: PropTypes.oneOf([Modes.READ_MODE, Modes.EDIT_MODE]).isRequired,
    data: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    originalData: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
    collections: PropTypes.array.isRequired,
    onUpdate: PropTypes.func.isRequired,
    onRowSelect: PropTypes.func.isRequired,
    onRowDoubleClick: PropTypes.func.isRequired,
    onRowClick: PropTypes.func.isRequired,
    onButtonClick: PropTypes.func.isRequired,
    onCheckboxChange: PropTypes.func.isRequired,
    onTextChange: PropTypes.func.isRequired,
    onSelectItemChange: PropTypes.func.isRequired,
    onAutocompleteOptionChange: PropTypes.func.isRequired,
    onDateTimeChange: PropTypes.func.isRequired
}

export default Row;