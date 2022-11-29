import React, { useState } from 'react';
import { MenuItem, TableCell, Select, TextField, Checkbox } from '@mui/material';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import { clearxpath, getDataxpath } from '../utils';
import { ColorTypes, DataTypes, Modes } from '../constants';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    previousValue: {
        color: 'red',
        textDecoration: 'line-through',
        marginRight: 10
    },
    modifiedValue: {
        color: 'green'
    },
    abbreviatedJsonCell: {
        maxWidth: 150,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
    },
    tableCellCritical: {
        color: '#9C0006 !important',
        background: '#ffc7ce'
    },
    tableCellError: {
        color: '#9C0006 !important',
        background: '#ffc7ce'
    },
    tableCellWarning: {
        color: '#9c6500 !important',
        background: '#ffeb9c'
    },
    tableCellInfo: {
        color: 'blue !important',
        background: '#c2d1ff'
    },
    tableCellDebug: {
        color: 'black !important',
        background: '#ccc'
    },
    tableCellRemove: {
        textDecoration: 'line-through'
    },
    select: {
        background: 'white',
        '& .MuiSelect-outlined': {
            padding: '6px 10px'
        }
    },
    checkbox: {
        padding: '6px !important'
    },
    textField: {
        background: 'white',
        minWidth: '50px !important'
    }
})

const Cell = (props) => {
    const [active, setActive] = useState(false);
    const { data, originalData, row, propname, proptitle, mode, collections } = props;
    const classes = useStyles();

    const onFocusIn = () => {
        setActive(true);
    }

    const onFocusOut = () => {
        setActive(false);
    }

    const onTextChange = (e, type) => {
        let value = e.target.value;
        if(type === 'number') {
            value = value * 1;
        }
        let xpath = e.target.getAttribute('xpath');
        let updatedData = cloneDeep(data);
        _.set(updatedData, xpath, value);
        props.onUpdate(updatedData);
    }

    const onSelectItemChange = (e, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, xpath, e.target.value);
        props.onUpdate(updatedData);
    }

    const onCheckboxChange = (e, xpath) => {
        let updatedData = cloneDeep(data);
        _.set(updatedData, xpath, e.target.checked);
        props.onUpdate(updatedData);
    }

    let collection = collections.filter(col => col.tableTitle === proptitle)[0];
    let type = DataTypes.STRING;
    let enumValues = [];
    let xpath = proptitle ? proptitle.indexOf('.') > 0 ? row[proptitle.split('.')[0] + '.xpath_' + propname] : row['xpath_' + propname] : row['xpath_' + propname];
    let dataxpath = getDataxpath(data, xpath)
    let disabled = row['data-remove'] || (!row[proptitle] && row[proptitle] !== 0 && row[proptitle] !== '' && row[proptitle] !== false)

    if (collection) {
        type = collection.type;
        enumValues = collection.autocomplete_list;
    }

    if (mode === Modes.EDIT_MODE && active && !collection.ormNoUpdate && !collection.serverPopulate && !row['data-remove']) {
        if (type === DataTypes.ENUM) {
            return (
                <TableCell align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Select
                        className={classes.select}
                        size='small'
                        open={active}
                        disabled={disabled}
                        onOpen={onFocusIn}
                        onClose={onFocusOut}
                        value={row[proptitle]}
                        onChange={(e) => onSelectItemChange(e, dataxpath)}>

                        {enumValues.map((val) => {
                            return (
                                <MenuItem key={val} value={val}>
                                    {val}
                                </MenuItem>
                            )
                        })}
                    </Select>
                </TableCell >
            )
        } else if (type === DataTypes.BOOLEAN) {
            return (
                <TableCell align='center' size='small' onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <Checkbox
                        className={classes.checkbox}
                        defaultValue={false}
                        checked={row[proptitle]}
                        disabled={disabled}
                        onChange={(e) => onCheckboxChange(e, dataxpath)}
                    />
                </TableCell >
            )
        } else {
            return (
                <TableCell align='center' size='small' onBlur={onFocusOut} onDoubleClick={(e) => props.onDoubleClick(e, props.rowindex, xpath)}>
                    <TextField
                        className={classes.textField}
                        autoFocus
                        size='small'
                        disabled={disabled}
                        onChange={(e) => onTextChange(e, type)}
                        inputProps={{ style: { padding: '6px 10px' }, xpath: dataxpath }}
                        value={row[proptitle]}
                        type={type}
                    />
                </TableCell>
            )
        }
    }

    if (type === DataTypes.BOOLEAN) {
        return (
            <TableCell align='center' size='small' onClick={onFocusIn}>
                <Checkbox
                    className={classes.checkbox}
                    disabled
                    defaultValue={false}
                    checked={row[proptitle]}
                />
            </TableCell >
        )
    }

    if (type === DataTypes.OBJECT || type === DataTypes.ARRAY) {
        let updatedData = proptitle ? clearxpath(cloneDeep(row[proptitle])) : {};
        let text = JSON.stringify(updatedData)
        return (
            <TableCell className={classes.abbreviatedJsonCell} align='center' size='medium' onClick={() => props.onAbbreviatedFieldOpen(updatedData)}>
                <span>{text}</span>
            </TableCell >
        )
    }

    let color = ColorTypes.UNSPECIFIED;
    if (collection) {
        if (collection.color) {
            collection.color.split(',').map((colorSet) => {
                colorSet = colorSet.trim();
                let [key, value] = colorSet.split('=');
                if (key === row[proptitle]) {
                    color = ColorTypes[value];
                }
            });
        }
    }

    let tableCellColorClass = '';
    if (color === ColorTypes.CRITICAL) tableCellColorClass = classes.tableCellCritical;
    else if (color === ColorTypes.ERROR) tableCellColorClass = classes.tableCellError;
    else if (color === ColorTypes.WARNING) tableCellColorClass = classes.tableCellWarning;
    else if (color === ColorTypes.INFO) tableCellColorClass = classes.tableCellInfo;
    else if (color === ColorTypes.DEBUG) tableCellColorClass = classes.tableCellDebug;

    let dataModified = _.get(originalData, xpath) !== row[proptitle];
    let tableCellRemove = row['data-remove'] ? classes.tableCellRemove : '';
    if (dataModified) {
        return (
            <TableCell className={`${classes.td} ${tableCellColorClass}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span className={classes.previousValue}>{_.get(originalData, xpath)}</span>
                <span className={classes.modifiedValue}>{row[proptitle]}</span>
            </TableCell>
        )
    } else {
        return (
            <TableCell className={`${classes.td} ${tableCellColorClass} ${tableCellRemove}`} align='center' size='medium' onClick={onFocusIn} data-xpath={xpath} data-dataxpath={dataxpath}>
                <span>{row[proptitle]}</span>
            </TableCell>
        )
    }
}

Cell.propTypes = {
    data: PropTypes.object.isRequired,
    originalData: PropTypes.object.isRequired,
    row: PropTypes.object.isRequired,
    propname: PropTypes.string.isRequired,
    proptitle: PropTypes.string,
    mode: PropTypes.string.isRequired,
    collections: PropTypes.array.isRequired
}

export default Cell;