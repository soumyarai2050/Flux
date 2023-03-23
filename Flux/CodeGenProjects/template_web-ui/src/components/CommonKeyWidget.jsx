import React, { useState } from 'react';
import { Box, Tooltip, ClickAwayListener } from '@mui/material';
import PropTypes from 'prop-types';
import { clearxpath, getColorTypeFromValue, isValidJsonString } from '../utils';
import { DataTypes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import _, { cloneDeep } from 'lodash';
import classes from './CommonKeyWidget.module.css';

const CommonKeyWidget = React.forwardRef((props, ref) => {

    let commonkeys = props.commonkeys.sort(function (a, b) {
        if (a.sequenceNumber < b.sequenceNumber) return -1;
        return 1;
    })

    return (
        <Box ref={ref} className={classes.container}>
            {commonkeys.map((collection, i) => {
                if (collection.value === undefined || collection.value === null) return;
                // if (collection.type === 'button') return;
                if (Array.isArray(collection.value) && collection.value.length === 0) return;
                if (_.isObject(collection.value) && _.keys(collection.value).length === 0) return;

                return (
                    <CommonKey key={i} collection={collection} />
                )
            })}
        </Box>
    )
})

CommonKeyWidget.propTypes = {
    commonkeys: PropTypes.array.isRequired
};

const CommonKey = (props) => {
    const [open, setOpen] = useState(false);
    const { collection } = props;

    const onOpenAbbreviatedField = () => {
        setOpen(true);
    }

    const onCloseAbbreviatedField = () => {
        setOpen(false);
    }

    let abbreviatedJsonClass = '';
    if (collection.abbreviated && collection.abbreviated === "JSON") {
        abbreviatedJsonClass = classes.abbreviated_json;
    }

    let abbreviatedField;
    if (collection.abbreviated && collection.abbreviated === "JSON") {
        let updatedData = collection.value;
        if (collection.type === DataTypes.OBJECT || collection.type === DataTypes.ARRAY || (collection.type === DataTypes.STRING && isValidJsonString(updatedData))) {
            if (collection.type === DataTypes.OBJECT || collection.type === DataTypes.ARRAY) {
                updatedData = clearxpath(cloneDeep(updatedData));
            } else {
                updatedData = updatedData.replace(/\\/g, '');
                updatedData = JSON.parse(updatedData);
            }
            abbreviatedField = (<AbbreviatedJson open={open} onClose={onCloseAbbreviatedField} src={updatedData} />)
        } else if (collection.type === DataTypes.STRING && !isValidJsonString(updatedData)) {
            abbreviatedField = (
                <ClickAwayListener onClickAway={onCloseAbbreviatedField}>
                    <div className={classes.abbreviated_json}>
                        <Tooltip
                            title={updatedData}
                            placement="bottom-start"
                            open={open}
                            onClose={onCloseAbbreviatedField}
                            disableFocusListener
                            disableHoverListener
                            disableTouchListener>
                            <span>{updatedData}</span>
                        </Tooltip >
                    </div>
                </ClickAwayListener>
            )
        }
    }

    let color;
    if (collection.color) {
        color = getColorTypeFromValue(collection, collection.value);
    }
    let commonkeyColorClass = classes[color];

    let commonkeyTitleColorClass = '';
    if (collection.nameColor) {
        let nameColor = collection.nameColor.toLowerCase();
        commonkeyTitleColorClass = classes[nameColor];
    }

    let value = collection.value;
    if (value && (collection.type === DataTypes.NUMBER || typeof (value) === DataTypes.NUMBER)) {
        value = value.toLocaleString()
    } else {
        value = String(value);
    }

    let numberSuffix = ""
    if (collection.numberFormat) {
        if (collection.numberFormat === "%") {
            numberSuffix = " %"
        }
    }

    return (
        <Box className={classes.item}>
            <span className={`${classes.key} ${commonkeyTitleColorClass}`}>
                {collection.elaborateTitle ? collection.tableTitle : collection.title ? collection.title : collection.key}:
            </span>
            {collection.abbreviated && collection.abbreviated === "JSON" ? (
                <span className={abbreviatedJsonClass} onClick={onOpenAbbreviatedField}>
                    {abbreviatedField}
                </span>
            ) : (
                <span className={commonkeyColorClass}>
                    {value}{numberSuffix}
                </span>
            )}
        </Box>
    )
}

export default CommonKeyWidget;

