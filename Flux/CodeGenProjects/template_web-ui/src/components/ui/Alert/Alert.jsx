/**
 * @module Alert
 * @description This module provides components for displaying alerts and error messages.
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Snackbar from '@mui/material/Snackbar';
import AlertComponent from '@mui/material/Alert';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Close from '@mui/icons-material/Close';
import { isObject } from 'lodash';

import { DATA_TYPES } from '../../../constants';
import JsonView from '../../data-display/JsonView';
import classes from './Alert.module.css';

/**
 * @function Alert
 * @description A wrapper around the MUI Snackbar and Alert components to display messages.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the alert is open.
 * @param {function} props.onClose - The function to call when the alert is closed.
 * @param {string} [props.severity='success'] - The severity of the alert.
 * @param {React.ReactNode} props.children - The content of the alert.
 * @returns {React.ReactElement} The rendered Alert component.
 */
const Alert = ({ open, onClose, severity = 'success', children }) => (
    <Snackbar
        open={open}
        className={classes.snackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
    >
        <AlertComponent
            className={classes.alert}
            variant="filled"
            action={<IconButton onClick={onClose}><Close /></IconButton>}
            severity={severity}
        >
            {children}
        </AlertComponent>
    </Snackbar>
);

Alert.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    severity: PropTypes.string,
    children: PropTypes.node.isRequired,
};

/**
 * @function AlertErrorMessage
 * @description A component to display detailed error messages in an Alert.
 * @param {object} props - The properties for the component.
 * @param {object} props.error - The error object to display.
 * @param {string} props.error.code - The error code.
 * @param {string} props.error.status - The error status.
 * @param {string} props.error.message - The error message.
 * @param {string|object} [props.error.detail] - The error details.
 * @param {object} [props.error.payload] - The error payload.
 * @param {boolean} props.open - Whether the alert is open.
 * @param {function} props.onClose - The function to call when the alert is closed.
 * @param {string} [props.severity='error'] - The severity of the alert.
 * @returns {React.ReactElement} The rendered AlertErrorMessage component.
 */
export const AlertErrorMessage = ({ error, open, onClose, severity = 'error' }) => {
    const { code, status, message, detail, payload } = error;
    const [isDetailOpen, setDetailOpen] = useState(false);
    const [isPayloadOpen, setPayloadOpen] = useState(false);

    const renderJsonView = (src, isOpen, setOpen) => (
        <span className={classes.abbreviated_json} onClick={() => setOpen(true)}>
            {typeof src === 'object' ? JSON.stringify(src) : src}
            <JsonView open={isOpen} onClose={() => setOpen(false)} src={src} />
        </span>
    );

    return (
        <Alert open={open} onClose={onClose} severity={severity}>
            <Typography variant="body1" component="div">
                <strong>Status:</strong> {status}, <strong>Code:</strong> {code}, <strong>Message:</strong> {message}
                {detail && (
                    <>
                        , <strong>Detail:</strong> {isObject(detail) ? renderJsonView(detail, isDetailOpen, setDetailOpen) : detail}
                    </>
                )}
                {payload && (
                    <>
                        , <strong>Payload:</strong> {renderJsonView(payload, isPayloadOpen, setPayloadOpen)}
                    </>
                )}
            </Typography>
        </Alert>
    );
};

AlertErrorMessage.propTypes = {
    error: PropTypes.shape({
        code: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        message: PropTypes.string.isRequired,
        detail: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
        payload: PropTypes.object,
    }).isRequired,
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    severity: PropTypes.string,
};

export default Alert;