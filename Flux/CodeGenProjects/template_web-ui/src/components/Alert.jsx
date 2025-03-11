import React, { useState } from 'react';
import _ from 'lodash';
import PropTypes from 'prop-types';
import { Snackbar, Alert as AlertComponent, IconButton } from '@mui/material';
import { Close } from '@mui/icons-material';
import { DATA_TYPES } from '../constants';
import JsonView from './JsonView';
import classes from './Alert.module.css';


const Alert = (props) => {
    return (
        <Snackbar
            open={props.open}
            className={classes.snackbar}
            anchorOrigin={{
                vertical: "top",
                horizontal: "left",
            }}>
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
    // children: PropTypes.any.isRequired
}

export const AlertErrorMessage = (props) => {
    const { code, status, message, detail, payload } = props.error;
    const [open, setOpen] = useState(false);

    const onOpenAbbreviatedField = () => {
        setOpen(true);
    }

    const onCloseAbbreviatedField = () => {
        setOpen(false);
    }

    return (
        <Alert open={props.open} onClose={props.onClose} severity={props.severity}>
            <span>error status: {status}, code: {code}, message: {message}, </span>
            {typeof (detail) === DATA_TYPES.STRING && <span>detail: {detail}</span>}
            {(Array.isArray(detail) || _.isObject(detail)) && <span>detail: {JSON.stringify(detail)}</span>}
            {payload && (
                <>
                    <span>, payload: </span>
                    <span className={classes.abbreviated_json} onClick={onOpenAbbreviatedField}>
                        <JsonView open={open} onClose={onCloseAbbreviatedField} src={payload} />
                    </span>
                </>
            )}
        </Alert>
    )
}

export default Alert;