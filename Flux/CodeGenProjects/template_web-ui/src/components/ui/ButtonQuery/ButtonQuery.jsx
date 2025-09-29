/**
 * @module ButtonQuery
 * @description This module provides a component for a button that executes a query.
 * It supports user-editable query parameters for GET, POST, and file upload requests.
 */

import React, { useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button,
    DialogContentText, TextField, Box, FormControlLabel, Switch
} from '@mui/material';
import { PlayArrow, Delete } from '@mui/icons-material';
import ValueBasedToggleButton from '../ValueBasedToggleButton';
import { API_ROOT_URL, API_ROOT_VIEW_URL } from '../../../constants';
import { AlertErrorMessage } from '../Alert';
import { getColorTypeFromValue } from '../../../utils/ui/colorUtils';
import { getSizeFromValue, getShapeFromValue } from '../../../utils/ui/uiUtils';
import { getErrorDetails } from '../../../utils/core/errorUtils';
import { getAxiosMethod } from '../../../utils/network/networkUtils';
import { getEditableParams, mergeQueryParams } from '../../../utils/core/parameterBindingUtils';
import classes from './ButtonQuery.module.css';
import { computeFileChecksum } from '../../../utils/file/fileUtils';

// Add UTC support for datetime
dayjs.extend(utc);

const DIALOG_TITLE = 'Execute Query';
const DISCARD_BUTTON_TEXT = 'DISCARD';
const RUN_BUTTON_TEXT = 'RUN';

/**
 * @function ButtonQuery
 * @description A button component that triggers a query execution flow, with support for user-editable query parameters.
 * @param {Object} props - The properties for the component.
 * @param {Object} props.queryObj - The query object from the schema.
 * @param {string} [props.url] - The base URL for the query.
 * @param {string} [props.viewUrl] - The base URL for view queries.
 * @param {Object} [props.autoBoundParams={}] - Auto-bound query parameters from field values with FluxFldQueryParamBind.
 * @returns {React.ReactElement} The rendered ButtonQuery component.
 */
const ButtonQuery = ({ queryObj, url, viewUrl, autoBoundParams = {} }) => {
    const [value, setButtonValue] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [alert, setAlert] = useState(null);
    const [queryParamsState, setQueryParamsState] = useState({});
    const inputRef = useRef();

    const buttonOptions = useMemo(() => {
        const disabledValueCaptionDict = {};
        const { ui_button } = queryObj;
        if (ui_button.disabled_captions) {
            ui_button.disabled_captions.split(',').forEach(valueCaptionPair => {
                const [buttonValue, caption] = valueCaptionPair.split('=');
                disabledValueCaptionDict[buttonValue] = caption;
            });
        }
        const isDisabledValue = disabledValueCaptionDict.hasOwnProperty(String(value));
        const disabledCaption = isDisabledValue ? disabledValueCaptionDict[String(value)] : '';
        const checked = String(value) === ui_button.pressed_value_as_text;
        const collection = {
            color: ui_button.value_color_map,
            xpath: 'null'
        };
        const color = getColorTypeFromValue(collection, String(value));
        const size = getSizeFromValue(ui_button.button_size);
        const shape = getShapeFromValue(ui_button.button_type);
        let caption = String(value);

        if (isDisabledValue) {
            caption = disabledCaption;
        } else if (checked && ui_button.pressed_caption) {
            caption = ui_button.pressed_caption;
        } else if (!checked && ui_button.unpressed_caption) {
            caption = ui_button.unpressed_caption;
        }
        return { size, shape, color, caption, isDisabledValue };
    }, [queryObj, value]);

    const queryOptions = useMemo(() => {
        const { query_data } = queryObj;
        if (!query_data) {
            console.error(`Unexpected! no query_data found in button query obj, ${JSON.stringify({ query_data })}`);
            return null;
        }
        const {
            QueryType: queryType = 'HTTP',
            QueryRouteType: queryRouteType = 'GET',
            QueryParams: queryParamsArray = []
        } = query_data;

        // Filter out auto-bound parameters from user-editable parameters
        const editableParams = getEditableParams(queryParamsArray, autoBoundParams);

        // Keep all parameters for reference (used in coercion and final execution)
        const allParams = queryParamsArray.reduce((acc, param) => {
            acc[param.QueryParamName] = { type: param.QueryParamDataType || 'str' };
            return acc;
        }, {});

        const finalQueryRouteType = queryType === 'HTTP_FILE' ? 'POST' : queryRouteType;
        const queryName = `query-${query_data.QueryName}`;
        return {
            queryName,
            queryType,
            queryRouteType: finalQueryRouteType,
            queryParams: editableParams,  // Only user-editable parameters
            allParams  // All parameters for type coercion
        };
    }, [queryObj, autoBoundParams]);

    const fileUploadOptions = useMemo(() => {
        const { file_upload_options } = queryObj;
        if (!file_upload_options) {
            return null;
        }
        const {
            AllowFileUpload: allowFileUpload,
            DisallowNonTodayFileUpload: disallowNonTodayFileUpload,
            DisallowDuplicateFileUpload: disallowDuplicateFileUpload
        } = file_upload_options;
        return { allowFileUpload, disallowNonTodayFileUpload, disallowDuplicateFileUpload };
    }, [queryObj]);

    const baseUrl = useMemo(() => url || API_ROOT_URL, [url]);
    const baseViewUrl = useMemo(() => viewUrl || API_ROOT_VIEW_URL, [viewUrl]);

    const { caption, color, isDisabledValue, shape, size } = buttonOptions;
    const { allow_force_update, button_icon_name, hide_caption } = queryObj.ui_button;

    const handleButtonClick = () => {
        const initialParams = {};
        Object.keys(queryOptions.queryParams).forEach(key => {
            const paramInfo = queryOptions.queryParams[key];
            initialParams[key] = paramInfo.type === 'boolean' ? false : '';
        });
        setQueryParamsState(initialParams);
        setIsOpen(true);
    };

    const handleClose = () => {
        setIsOpen(false);
        setQueryParamsState({}); // Clear state on close
    };

    const handleParamChange = (key, val) => {
        setQueryParamsState(prevState => ({ ...prevState, [key]: val }));
    };

    /**
     * Coerces and validates parameters from their string/UI state to their target data types.
     * @param {object} paramsToCoerce - The state object with user inputs.
     * @returns {object} A new object with correctly typed values.
     * @throws {Error} If a numeric conversion fails.
     */
    const coerceParams = (paramsToCoerce) => {
        const coerced = {};
        for (const key in paramsToCoerce) {
            const paramInfo = queryOptions.queryParams[key];
            if (!paramInfo) continue;

            const { type } = paramInfo;
            const value = paramsToCoerce[key];

            if (value === '' && type !== 'str') {
                // Treat empty non-string fields as null or skip them
                coerced[key] = null;
                continue;
            }

            switch (type) {
                case 'int':
                    const intVal = parseInt(value, 10);
                    if (isNaN(intVal)) {
                        throw new Error(`Invalid integer value for parameter "${key}": ${value}`);
                    }
                    coerced[key] = intVal;
                    break;
                case 'float':
                    const floatVal = parseFloat(value);
                    if (isNaN(floatVal)) {
                        throw new Error(`Invalid float value for parameter "${key}": ${value}`);
                    }
                    coerced[key] = floatVal;
                    break;
                case 'boolean':
                    coerced[key] = !!value; // Ensures it's a strict boolean
                    break;
                case 'str':
                default:
                    coerced[key] = value;
                    break;
            }
        }
        return coerced;
    };

    const handleExecute = async () => {
        setButtonValue(true);
        try {
            const { queryName, queryType, queryRouteType } = queryOptions;
            const coercedUserParams = coerceParams(queryParamsState);

            // Merge auto-bound parameters with user-provided parameters
            const finalParams = mergeQueryParams(autoBoundParams, coercedUserParams);

            if (queryType === 'HTTP_FILE') {
                await handleHttpFileQuery(queryName, 'POST', finalParams);
            } else if (queryType === 'HTTP') {
                await handleHttpQuery(queryName, queryRouteType, finalParams);
            } else {
                throw new Error(`QueryType: ${queryType} is not supported`);
            }
        } catch (error) {
            setAlert(getErrorDetails(error));
        }
        handleClose(); // Close dialog and clear state
        setButtonValue(false);
    };

    const handleHttpFileQuery = async (queryName, queryRouteType, params) => {
        if (!fileUploadOptions?.allowFileUpload) {
            throw new Error(`File upload not allowed`);
        }

        const selectedFile = inputRef.current?.files?.[0];
        if (!selectedFile) {
            throw new Error('No file selected for upload');
        }

        const lastModified = dayjs.utc(selectedFile.lastModified);
        if (fileUploadOptions.disallowNonTodayFileUpload && !lastModified.isSame(dayjs.utc(), 'day')) {
            throw new Error(`Older file selected for upload, file: ${selectedFile.name}, lastModified: ${lastModified.toISOString()}`);
        }

        const fileExt = selectedFile.name.split('.').pop();
        const checksum = await computeFileChecksum(selectedFile);
        const fileNameWithoutExt = selectedFile.name.replace(`.${fileExt}`, '');
        const lastModifiedStr = lastModified.toISOString();
        const newFileName = checksum ?
            `${fileNameWithoutExt}~~${lastModifiedStr}~~${checksum}~~${selectedFile.size}.${fileExt}` :
            `${fileNameWithoutExt}~~${lastModifiedStr}~~${selectedFile.size}.${fileExt}`;

        const renamedFile = new File([selectedFile], newFileName, { type: selectedFile.type, lastModified: selectedFile.lastModified });
        const formData = new FormData();
        formData.append('upload_file', renamedFile);

        // Append other coerced parameters to the form data
        // if (params) {
        //     Object.entries(params).forEach(([key, paramValue]) => {
        //         if (paramValue !== null) {
        //             formData.append(key, paramValue);
        //         }
        //     });
        // }

        await axios.post(`${baseUrl}/${queryName}`, formData);
        setAlert({ type: 'success', detail: 'File uploaded successfully' });
    };

    const handleHttpQuery = async (queryName, queryRouteType, params) => {
        const axiosFunc = getAxiosMethod(queryRouteType);
        const isGetRequest = queryRouteType.toLowerCase() === 'get';
        const urlRoot = isGetRequest ? baseViewUrl : baseUrl;
        let finalUrl = `${urlRoot}/${queryName}`;
        let requestData = null;

        // Filter out null/undefined params before sending
        const finalParams = Object.entries(params)
            .filter(([, value]) => value !== null && value !== undefined)
            .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});

        if (isGetRequest) {
            // For GET requests, append params to URL
            if (Object.keys(finalParams).length > 0) {
                const searchParams = new URLSearchParams(finalParams);
                finalUrl += `?${searchParams.toString()}`;
            }
        } else {
            // For POST, PUT, etc., send params as request body
            requestData = finalParams;
        }

        // The second argument to axiosFunc will be data for POST/PUT, and undefined for GET
        await axiosFunc(finalUrl, requestData);
        setAlert({ type: 'success', detail: `${queryName} successfully completed` });
    };

    const handleAlertClose = () => setAlert(null);

    const renderParamInput = (key, paramInfo) => {
        const { type } = paramInfo;
        switch (type) {
            case 'boolean':
                return (
                    <FormControlLabel
                        key={key}
                        sx={{ display: 'block', mt: 1 }}
                        control={
                            <Switch
                                checked={!!queryParamsState[key]}
                                onChange={(e) => handleParamChange(key, e.target.checked)}
                                name={key}
                            />
                        }
                        label={key}
                    />
                );
            case 'int':
            case 'float':
                return (
                    <TextField
                        key={key}
                        margin="dense"
                        label={key}
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={queryParamsState[key] || ''}
                        onChange={(e) => handleParamChange(key, e.target.value)}
                        inputProps={{ step: type === 'float' ? 'any' : '1' }}
                    />
                );
            case 'str':
            default:
                return (
                    <TextField
                        key={key}
                        margin="dense"
                        label={key}
                        type="text"
                        fullWidth
                        variant="outlined"
                        value={queryParamsState[key] || ''}
                        onChange={(e) => handleParamChange(key, e.target.value)}
                    />
                );
        }
    };

    return (
        <>
            <ValueBasedToggleButton
                size={size}
                shape={shape}
                color={color}
                value={value}
                caption={caption}
                disabled={isDisabledValue}
                allowForceUpdate={allow_force_update}
                iconName={button_icon_name}
                hideCaption={hide_caption}
                onClick={handleButtonClick}
                xpath={null}
                action={null}
                dataSourceId={null}
                source={null}
            />
            <Dialog className={classes.backdrop} open={isOpen} onClose={handleClose}>
                <DialogTitle sx={{ width: 500 }} className={classes.dialog_title}>{DIALOG_TITLE}</DialogTitle>
                <DialogContent className={classes.dialog_body}>
                    <DialogContentText className={classes.dialog_text}>QueryName: {queryOptions.queryName}</DialogContentText>
                    <DialogContentText className={classes.dialog_text}>QueryType: {queryOptions.queryType}</DialogContentText>

                    {Object.keys(queryOptions.queryParams).length > 0 && (
                        <Box sx={{ mt: 2 }}>
                            <DialogContentText className={classes.dialog_text} sx={{ fontWeight: 'bold', mb: 1 }}>
                                Query Parameters:
                            </DialogContentText>
                            {Object.entries(queryOptions.queryParams).map(([key, paramInfo]) =>
                                renderParamInput(key, paramInfo)
                            )}
                        </Box>
                    )}
                </DialogContent>

                {queryOptions.queryType === 'HTTP_FILE' && (
                    <DialogContent className={classes.dialog_body}>
                        <DialogContentText className={classes.dialog_text}>Select File to Upload:</DialogContentText>
                        <input ref={inputRef} accept='.csv' type='file' className={classes.fileInput} />
                    </DialogContent>
                )}
                <DialogActions>
                    <Button variant='contained' color='error' onClick={handleClose} startIcon={<Delete />}>{DISCARD_BUTTON_TEXT}</Button>
                    <Button variant='contained' color='success' onClick={handleExecute} startIcon={<PlayArrow />}>{RUN_BUTTON_TEXT}</Button>
                </DialogActions>
            </Dialog>
            {alert && (
                <AlertErrorMessage
                    open={alert !== null}
                    onClose={handleAlertClose}
                    severity={alert.type || 'info'}
                    error={alert}
                />
            )}
        </>
    );
};

ButtonQuery.propTypes = {
    queryObj: PropTypes.object.isRequired,
    url: PropTypes.string,
    viewUrl: PropTypes.string,
    autoBoundParams: PropTypes.object,
};

export default ButtonQuery;