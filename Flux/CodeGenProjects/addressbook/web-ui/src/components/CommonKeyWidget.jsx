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
        color: '#9C0006 !important'
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
                if (collection.value === undefined) return;
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

    return (
        <Box className={classes.commonkey}>
            <span className={classes.commonkeyTitle}>{collection.tableTitle}:</span>
            {collection.abbreviated && collection.abbreviated === "JSON" ? (
                <span className={abbreviatedJsonClass} onClick={onOpenAbbreviatedField}>
                    {abbreviatedField}
                </span>
            ) : (
                <span className={commonkeyColorClass}>{String(collection.value)}</span>
            )}
        </Box>
    )
}

export default CommonKeyWidget;

