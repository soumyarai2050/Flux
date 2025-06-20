import React, { useMemo, useRef, useState } from 'react';
import axios from 'axios';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { API_ROOT_URL, API_ROOT_VIEW_URL } from '../constants';
import { PlayArrow, Delete } from '@mui/icons-material';
import Alert from './Alert';
import { getColorTypeFromValue, getSizeFromValue, getShapeFromValue, getErrorDetails, getAxiosMethod } from '../utils';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, DialogContentText } from '@mui/material';
import classes from './ButtonQuery.module.css';
import { computeFileChecksum } from '../utils/fileHelper';
// add utc support for datetime
dayjs.extend(utc);


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
            })
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
    }, [queryObj, value])

    const queryOptions = useMemo(() => {
        const { query_data } = queryObj;
        if (!query_data) {
            const err_ = `Unexpected! no query_data found in button query obj, ${JSON.stringify({ query_data })}`;
            console.error(err_);
            return null;
        }
        const { QueryType: queryType = 'HTTP' } = query_data;
        let { QueryRouteType: queryRouteType = 'GET' } = query_data;
        if (queryType === 'HTTP_FILE') {
            queryRouteType = 'POST';
        }
        const queryName = `query-${query_data.QueryName}`;
        return { queryName, queryType, queryRouteType };
    }, [queryObj])

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
    }, [queryObj])

    const baseUrl = useMemo(() => url || API_ROOT_URL, [url]);
    const baseViewUrl = useMemo(() => viewUrl || API_ROOT_VIEW_URL, [viewUrl]);

    const { caption, color, isDisabledValue, shape, size } = buttonOptions;
    const { allow_force_update, button_icon_name, hide_caption } = queryObj.ui_button;

    const handleButtonClick = (e) => {
        setIsOpen(true);
    }

    const handleClose = () => {
        setIsOpen(false);
    }

    const handleDiscard = () => {
        setIsOpen(false);
    }

    const handleExecute = async () => {
        const { queryName, queryType, queryRouteType } = queryOptions;
        setButtonValue(true);
        if (queryType === 'HTTP_FILE') {
            await handleHttpFileQuery(queryName, 'POST');
        } else if (queryType === 'HTTP') {
            await handleHttpQuery(queryName, queryRouteType);
        } else {
            const err_ = `queryType: ${queryType} is not supported`;
            console.error(err_);
            setAlert({ type: 'error', detail: err_ });
        }
        setIsOpen(false);
        setButtonValue(false);
    }

    const handleHttpFileQuery = async (queryName, queryRouteType) => {
        if (!fileUploadOptions) {
            const err_ = 'ERROR: No file upload options found';
            setAlert({ type: 'error', detail: err_ });
            return;
        }
        if (!fileUploadOptions.allowFileUpload) {
            const err_ = `ERROR: file upload failed, allowFileUpload: ${fileUploadOptions.allowFileUpload}`;
            setAlert({ type: 'error', detail: err_ });
            return;
        }
        // create form data for file upload
        const selectedFile = inputRef.current?.files?.[0];
        if (selectedFile) {
            const lastModified = dayjs.utc(selectedFile.lastModified);

            if (fileUploadOptions.disallowNonTodayFileUpload) {
                const todayDate = dayjs.utc();
                const isToday = lastModified.isSame(todayDate, 'day');

                if (!isToday) {
                    const err_ = `ERROR: older file selected for upload, file: ${selectedFile.name}, lastModified: ${lastModified.toISOString()}`;
                    console.error(err_);
                    setAlert({ type: 'error', detail: err_ });
                    return;
                }
            }
            const fileExt = selectedFile.name.split('.').pop();
            const checksum = await computeFileChecksum(selectedFile);
            const fileNameWithoutExt = selectedFile.name.replace(`.${fileExt}`, '');
            const lastModifiedStr = lastModified.toISOString();

            let newFileName;
            if (checksum) {
                newFileName = `${fileNameWithoutExt}~~${lastModifiedStr}~~${checksum}~~${selectedFile.size}.${fileExt}`;
            } else {
                newFileName = `${fileNameWithoutExt}~~${lastModifiedStr}~~${selectedFile.size}.${fileExt}`;
            }

            const renamedFile = new File([selectedFile], newFileName, { type: selectedFile.type, lastModified: selectedFile.lastModified });

            const formData = new FormData();
            formData.append('upload_file', renamedFile);

            try {
                await axios.post(`${baseUrl}/${queryName}`, formData);
                const text = `file uploaded successfully`;
                setAlert({ type: 'success', detail: text });
            } catch (err) {
                const { code, message, detail, status } = getErrorDetails(err);
                const err_ = `ERROR: file upload failed, ${JSON.stringify({ code, status, message, detail })}`;
                console.error(err_);
                setAlert({ type: 'error', detail: err_ });
            }
        } else {
            const err_ = 'ERROR: No file is selected for upload!';
            console.error(err_);
            setAlert({ type: 'error', detail: err_ });
        }
    }

    const handleHttpQuery = async (queryName, queryRouteType) => {
        try {
            const axiosFunc = getAxiosMethod(queryRouteType);
            await axiosFunc(`${queryRouteType === 'get' ? baseViewUrl : baseUrl}/${queryName}`);
            const text = `${queryName} successfully completed`;
            setAlert({ type: 'success', detail: text });
        } catch (err) {
            const { code, message, detail, status } = getErrorDetails(err);
            const err_ = `${queryName} failed, ${JSON.stringify({ code, status, message, detail })}`;
            console.error(err_);
            setAlert({ type: 'error', detail: err_ });
        }
    }

    const handleAlertClose = () => {
        setAlert(null);
    }

    return (
        <React.Fragment>
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
                <DialogTitle sx={{ width: 500 }} className={classes.dialog_title}>Execute Query</DialogTitle>
                <DialogContent className={classes.dialog_body}>
                    <DialogContentText className={classes.dialog_text}>QueryName: {queryOptions.queryName}</DialogContentText>
                    <DialogContentText className={classes.dialog_text}>QueryType: {queryOptions.queryType}</DialogContentText>
                    {/* <DialogContentText className={classes.dialog_text}>QueryRouteType: {queryOptions.queryRouteType}</DialogContentText> */}
                </DialogContent>
                {queryOptions.queryType === 'HTTP_FILE' && (
                    <DialogContent className={classes.dialog_body}>
                        <DialogContentText className={classes.dialog_text}>Select File to Upload:</DialogContentText>
                        <input ref={inputRef} accept='.csv' type='file' />
                    </DialogContent>
                )}
                <DialogActions>
                    <Button variant='contained' color='error' onClick={handleDiscard} startIcon={<Delete />}>DISCARD</Button>
                    <Button variant='contained' color='success' onClick={handleExecute} startIcon={<PlayArrow />}>RUN</Button>
                </DialogActions>
            </Dialog>
            <Alert
                open={alert !== null}
                onClose={handleAlertClose}
                severity={alert?.type}>
                {alert?.detail}
            </Alert>
        </React.Fragment>
    )
}

export default ButtonQuery;