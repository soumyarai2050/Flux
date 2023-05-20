import React, { Fragment, useState } from 'react';
import { Box, Tooltip, ClickAwayListener } from '@mui/material';
import PropTypes from 'prop-types';
import { clearxpath, getColorTypeFromValue, isValidJsonString, floatToInt, groupCommonKeys } from '../utils';
import { DataTypes } from '../constants';
import AbbreviatedJson from './AbbreviatedJson';
import _, { cloneDeep } from 'lodash';
import classes from './CommonKeyWidget.module.css';

const CommonKeyWidget = React.forwardRef((props, ref) => {
    // filter unset or null values from common keys
    let commonkeys = props.commonkeys.filter(commonKeyObj => {
        if (commonKeyObj.value === undefined || commonKeyObj.value === null ||
            (Array.isArray(commonKeyObj.value) && commonKeyObj.value.length === 0) ||
            (_.isObject(commonKeyObj.value) && _.keys(commonKeyObj.value).length === 0)) {
                return false;
        }
        return true;
    })

    // sort the common keys based on sequence in ascending order
    commonkeys = commonkeys.sort(function (a, b) {
        if (a.sequenceNumber < b.sequenceNumber) return -1;
        return 1;
    })

    // group the common keys with same parent
    commonkeys = groupCommonKeys(commonkeys);

    return (
        <Box ref={ref} className={classes.container}>
            {commonkeys.map((collection, i) => {
                return (
                    <Fragment key={i}>
                        {props.lineBreakStart && collection.groupStart && <div className={classes.break_line} />}
                        <CommonKey collection={collection} />
                        {props.lineBreakEnd && collection.groupEnd && <div className={classes.break_line} />}
                    </Fragment>
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
            let tooltipText = "";
            if (updatedData !== null && updatedData !== undefined) {
                let lines = updatedData.split("\n");
                tooltipText = (
                    <>
                        {lines.map((line, idx) => (
                            <p key={idx}>{line}</p>
                        ))}
                    </>
                )
            }
            abbreviatedField = (
                <ClickAwayListener onClickAway={onCloseAbbreviatedField}>
                    <div className={classes.abbreviated_json}>
                        <Tooltip
                            title={tooltipText}
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
        if (collection.displayType === DataTypes.INTEGER) {
            value = floatToInt(value);
        }
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
            {collection.groupStart && <span className={classes.group_indicator}>{collection.parentxpath}: [ </span>}
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
            {collection.groupEnd && <span className={classes.group_indicator}> ]</span>}
        </Box>
    )
}

export default CommonKeyWidget;

