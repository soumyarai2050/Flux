import React from 'react';
import { Snackbar, Alert as AlertComponent, IconButton } from '@mui/material';
import { Close } from '@mui/icons-material';
import PropTypes from 'prop-types';
import { makeStyles } from '@mui/styles';

const useStyles = makeStyles({
    alert: {
        alignItems: 'center'
    }
})

const Alert = (props) => {
    const classes = useStyles();

    return (
        <Snackbar open={props.open} autoHideDuration={4000} onClose={props.onClose}>
            <AlertComponent
                className={classes.alert}
                variant='filled'
                action={<IconButton onClick={props.onClose}><Close /></IconButton>}
                severity={props.severity ? props.severity : 'success'}>
                {props.children}
            </AlertComponent>
        </Snackbar>
    )
}

Alert.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    severity: PropTypes.string,
    children: PropTypes.any.isRequired
}

export default Alert;