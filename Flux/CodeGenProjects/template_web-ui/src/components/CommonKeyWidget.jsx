import React, { useState } from 'react';
import { Box, Tooltip, ClickAwayListener } from '@mui/material';
import { makeStyles } from '@mui/styles';
import PropTypes from 'prop-types';
import { clearxpath, getColorTypeFromValue, isValidJsonString } from '../utils';
import { ColorTypes, DataTypes } from '../constants';
import AbbreviatedJsonWidget, { AbbreviatedJsonTooltip } from './AbbreviatedJsonWidget';
import _, { cloneDeep } from 'lodash';

const useStyles = makeStyles({
    widgetContainer: {
        padding: '5px 10px',
        display: 'flex',
        justifyContent: 'flex-start',
        background: 'cadetblue',
        flexWrap: 'wrap'
    },
    commonkey: {
        marginRight: 10,
        color: 'white'
    },
    commonkeyTitle: {
        color: 'yellow',
        paddingRight: 5
    },
    commonkeyCritical: {
        color: '#9C0006 !important',
        animation: `$blink 0.5s step-start infinite`
    },
    commonkeyError: {
        color: '#9C0006 !important'
    },
    commonkeyWarning: {
        color: '#9c6500 !important'
    },
    commonkeyInfo: {
        color: 'blue !important'
    },
    commonkeyDebug: {
        color: 'black !important'
    },
    abbreviatedJsonClass: {
        maxWidth: 150,
        display: 'inline-flex',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        textDecoration: 'underline',
        color: 'blue',
        fontWeight: 'bold',
        cursor: 'pointer'
    },
    keyCritical: {
        color: '#9C0006 !important',
        animation: `$blink 0.5s step-start infinite`
    },
    keyError: {
        color: '#9C0006 !important'
    },
    keyInfo: {
        color: 'blue !important'
    },
    keyWarning: {
        color: '#9c6500 !important'
    },
    keySuccess: {
        color: 'darkgreen !important'
    },
    keyDebug: {
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

const CommonKeyWidget = React.forwardRef((props, ref) => {
    const classes = useStyles();

    let commonkeys = props.commonkeys.sort(function (a, b) {
        if (a.sequenceNumber < b.sequenceNumber) return -1;
        return 1;
    })

    return (
        <Box ref={ref} className={classes.widgetContainer}>
            {commonkeys.map((collection, i) => {
                if (collection.value === undefined || collection.value === null) return;
                if (collection.type === 'button') return;
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

    const classes = useStyles();

    const onOpenAbbreviatedField = () => {
        setOpen(true);
    }

    const onCloseAbbreviatedField = () => {
        setOpen(false);
    }

    let abbreviatedJsonClass = '';
    if (collection.abbreviated && collection.abbreviated === "JSON") {
        abbreviatedJsonClass = classes.abbreviatedJsonClass;
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
            abbreviatedField = (<AbbreviatedJsonTooltip open={open} onClose={onCloseAbbreviatedField} src={updatedData} />)
        } else if (collection.type === DataTypes.STRING && !isValidJsonString(updatedData)) {
            abbreviatedField = (
                <ClickAwayListener onClickAway={onCloseAbbreviatedField}>
                    <div className={classes.abbreviatedJsonClass}>
                        <Tooltip
                            title={updatedData}
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

    let value = collection.value;
    if (collection.type === DataTypes.STRING && isValidJsonString(value)) {
        value = value.replace(/\\/g, '');
        value = JSON.parse(value);
    }

    let color = '';
    let commonkeyColorClass = '';
    if (collection.color) {
        color = getColorTypeFromValue(collection, collection.value);
    }
    if (color === ColorTypes.CRITICAL) commonkeyColorClass = classes.commonkeyCritical;
    else if (color === ColorTypes.ERROR) commonkeyColorClass = classes.commonkeyError;
    else if (color === ColorTypes.WARNING) commonkeyColorClass = classes.commonkeyWarning;
    else if (color === ColorTypes.INFO) commonkeyColorClass = classes.commonkeyInfo;
    else if (color === ColorTypes.DEBUG) commonkeyColorClass = classes.commonkeyDebug;

    let commonkeyTitleColorClass = '';
    if (collection.nameColor) {
        let nameColor = collection.nameColor.toLowerCase();
        if (nameColor === ColorTypes.CRITICAL) commonkeyTitleColorClass = classes.keyCritical;
        else if (nameColor === ColorTypes.ERROR) commonkeyTitleColorClass = classes.keyError;
        else if (nameColor === ColorTypes.WARNING) commonkeyTitleColorClass = classes.keyWarning;
        else if (nameColor === ColorTypes.INFO) commonkeyTitleColorClass = classes.keyInfo;
        else if (nameColor === ColorTypes.DEBUG) commonkeyTitleColorClass = classes.keyDebug;
        else if (nameColor === ColorTypes.SUCCESS) commonkeyTitleColorClass = classes.keySuccess;
    }

    return (
        <Box className={classes.commonkey}>
            <span className={`${classes.commonkeyTitle} ${commonkeyTitleColorClass}`}>
                {collection.elaborateTitle ? collection.tableTitle : collection.title ? collection.title : collection.key}:
            </span>
            {collection.abbreviated && collection.abbreviated === "JSON" ? (
                <span className={abbreviatedJsonClass} onClick={onOpenAbbreviatedField}>
                    {abbreviatedField}
                </span>
            ) : (
                <span className={commonkeyColorClass}>
                    {collection.type === DataTypes.NUMBER && collection.value ? collection.value.toLocaleString() : String(collection.value)}
                </span>
            )}
        </Box>
    )
}

export default CommonKeyWidget;

