import React from 'react';
import { Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import PropTypes from 'prop-types';
import { getColorTypeFromValue } from '../utils';
import { ColorTypes } from '../constants';

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
})

const CommonKeyWidget = React.forwardRef((props, ref) => {

    const classes = useStyles();

    return (
        <Box ref={ref} className={classes.widgetContainer}>
            {props.commonkeys.map((commonkey, i) => {
                let color = getColorTypeFromValue(commonkey, commonkey.value);
                let commonkeyColorClass = '';
                if (color === ColorTypes.CRITICAL) commonkeyColorClass = classes.commonkeyCritical;
                else if (color === ColorTypes.ERROR) commonkeyColorClass = classes.commonkeyError;
                else if (color === ColorTypes.WARNING) commonkeyColorClass = classes.commonkeyWarning;
                else if (color === ColorTypes.INFO) commonkeyColorClass = classes.commonkeyInfo;
                else if (color === ColorTypes.DEBUG) commonkeyColorClass = classes.commonkeyDebug;

                return (
                    <Box key={i} className={classes.commonkey}>
                        <span className={classes.commonkeyTitle}>{commonkey.tableTitle}:</span>
                        <span className={commonkeyColorClass}>{commonkey.value}</span>
                    </Box>
                )
            })}
        </Box>
    )
})

CommonKeyWidget.propTypes = {
    commonkeys: PropTypes.array.isRequired
};

export default CommonKeyWidget;

