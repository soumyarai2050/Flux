import React, { useState } from 'react';
import { Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import PropTypes from 'prop-types';
import { clearxpath, getColorTypeFromValue } from '../utils';
import { ColorTypes } from '../constants';
import AbbreviatedJsonWidget from './AbbreviatedJsonWidget';
import { cloneDeep } from 'lodash';

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
        textDecoration: 'underline'
    }
})

const CommonKeyWidget = React.forwardRef((props, ref) => {
    const [showAbbreviatedJson, setShowAbbreviatedJson] = useState(false);
    const [abbreviatedJson, setAbbreviatedJson] = useState({});

    const classes = useStyles();

    const onAbbreviatedFieldOpen = (json) => {
        setAbbreviatedJson(clearxpath(cloneDeep(json)));
        setShowAbbreviatedJson(true);
    }

    const onAbbreviatedFieldClose = () => {
        setAbbreviatedJson({});
        setShowAbbreviatedJson(false);
    }

    let commonkeys = props.commonkeys.sort(function (a, b) {
        if (a.sequenceNumber < b.sequenceNumber) return -1;
        return 1;
    })

    return (
        <Box ref={ref} className={classes.widgetContainer}>
            {commonkeys.map((collection, i) => {
                if (collection.value === undefined) return;

                let abbreviatedJsonClass = '';
                if (collection.abbreviated && collection.abbreviated === "JSON") {
                    abbreviatedJsonClass = classes.abbreviatedJsonClass;
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
                    <Box key={i} className={classes.commonkey}>
                        <span className={classes.commonkeyTitle}>{collection.tableTitle}:</span>
                        {collection.abbreviated && collection.abbreviated === "JSON" ? (
                            <span className={abbreviatedJsonClass} onClick={() => onAbbreviatedFieldOpen(collection.value)}>
                                {JSON.stringify(collection.value)}
                            </span>
                        ) : (
                            <span className={commonkeyColorClass}>{String(collection.value)}</span>
                        )}
                    </Box>
                )
            })}
            <AbbreviatedJsonWidget open={showAbbreviatedJson} onClose={onAbbreviatedFieldClose} json={abbreviatedJson} />
        </Box>
    )
})

CommonKeyWidget.propTypes = {
    commonkeys: PropTypes.array.isRequired
};

export default CommonKeyWidget;

