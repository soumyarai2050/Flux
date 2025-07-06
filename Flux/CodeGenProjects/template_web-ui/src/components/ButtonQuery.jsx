/**
 * @module ButtonQuery
 * @description This module provides a component for a button that executes a query.
 */

import React, { useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, DialogContentText } from '@mui/material';
import { PlayArrow, Delete } from '@mui/icons-material';

import ValueBasedToggleButton from './ValueBasedToggleButton';
import { API_ROOT_URL, API_ROOT_VIEW_URL } from '../constants';
import Alert, { AlertErrorMessage } from './Alert';
import { getColorTypeFromValue } from '../utils/ui/colorUtils';
import { getSizeFromValue, getShapeFromValue } from '../utils/ui/uiUtils';
import { getErrorDetails } from '../utils/core/errorUtils';
import { getAxiosMethod } from '../utils/network/networkUtils';
import classes from './ButtonQuery.module.css';
import { computeFileChecksum } from '../utils/file/fileUtils';

// Add UTC support for datetime
dayjs.extend(utc);

const DIALOG_TITLE = 'Execute Query';
const DISCARD_BUTTON_TEXT = 'DISCARD';
const RUN_BUTTON_TEXT = 'RUN';

/**
 * @function ButtonQuery
 * @description A button component that triggers a query execution flow.
 * @param {object} props - The properties for the component.
 * @param {object} props.queryObj - The query object from the schema.
 * @param {string} [props.url] - The base URL for the query.
 * @param {string} [props.viewUrl] - The base URL for view queries.
 * @returns {React.ReactElement} The rendered ButtonQuery component.
 */
const ButtonQuery = ({ queryObj, url, viewUrl }) => {
    const [value, setButtonValue] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [alert, setAlert] = useState(null);
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
        const { QueryType: queryType = 'HTTP', QueryRouteType: queryRouteType = 'GET' } = query_data;
        const finalQueryRouteType = queryType === 'HTTP_FILE' ? 'POST' : queryRouteType;
        const queryName = `query-${query_data.QueryName}`;
        return { queryName, queryType, queryRouteType: finalQueryRouteType };
    }, [queryObj]);

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

    const handleButtonClick = () => setIsOpen(true);

    const handleClose = () => setIsOpen(false);

    const handleDiscard = () => setIsOpen(false);

    const handleExecute = async () => {
        const { queryName, queryType, queryRouteType } = queryOptions;
        setButtonValue(true);
        try {
            if (queryType === 'HTTP_FILE') {
                await handleHttpFileQuery(queryName, 'POST');
            } else if (queryType === 'HTTP') {
                await handleHttpQuery(queryName, queryRouteType);
            } else {
                throw new Error(`QueryType: ${queryType} is not supported`);
            }
        } catch (error) {
            setAlert(getErrorDetails(error));
        }
        setIsOpen(false);
        setButtonValue(false);
    };

    const handleHttpFileQuery = async (queryName, queryRouteType) => {
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

        await axios.post(`${baseUrl}/${queryName}`, formData);
        setAlert({ type: 'success', detail: 'File uploaded successfully' });
    };

    const handleHttpQuery = async (queryName, queryRouteType) => {
        const axiosFunc = getAxiosMethod(queryRouteType);
        const url = queryRouteType === 'get' ? baseViewUrl : baseUrl;
        await axiosFunc(`${url}/${queryName}`);
        setAlert({ type: 'success', detail: `${queryName} successfully completed` });
    };

    const handleAlertClose = () => setAlert(null);

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
                </DialogContent>
                {queryOptions.queryType === 'HTTP_FILE' && (
                    <DialogContent className={classes.dialog_body}>
                        <DialogContentText className={classes.dialog_text}>Select File to Upload:</DialogContentText>
                        <input ref={inputRef} accept='.csv' type='file' className={classes.fileInput} />
                    </DialogContent>
                )}
                <DialogActions>
                    <Button variant='contained' color='error' onClick={handleDiscard} startIcon={<Delete />}>{DISCARD_BUTTON_TEXT}</Button>
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
};

export default ButtonQuery;