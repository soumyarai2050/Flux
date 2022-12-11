import React from 'react';
import { Box } from '@mui/material';
import { makeStyles } from '@mui/styles';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    widgetContainer: {
        padding: 5,
        display: 'flex',
        justifyContent: 'center',
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
    }
})

const CommonKeyWidget = React.forwardRef((props, ref) => {

    const classes = useStyles();

    return (
        <Box ref={ref} className={classes.widgetContainer}>
            {Object.entries(props.commonkeys).map(([k, v], i) => {
                return (
                    <Box key={i} className={classes.commonkey}>
                        <span className={classes.commonkeyTitle}>{k}:</span>
                        <span>{v}</span>
                    </Box>
                )
            })}
        </Box>
    )
})

CommonKeyWidget.propTypes = {
    commonkeys: PropTypes.object.isRequired
};

export default CommonKeyWidget;

