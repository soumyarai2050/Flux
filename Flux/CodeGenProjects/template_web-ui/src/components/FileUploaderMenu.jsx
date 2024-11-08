import React, { useRef, useState } from "react";
// third-party library imports
import axios from 'axios';
import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';
import { Delete, FileUpload } from '@mui/icons-material';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
// project imports
import { Icon } from './Icon';
import { API_ROOT_URL } from '../constants';
import classes from './FileUploaderMenu.module.css';
import { computeFileChecksum, getErrorDetails } from "../utils";

// add utc support for datetime
dayjs.extend(utc);


const FileUploaderMenu = ({ disallowNonTodayFileUpload, fileUploadQuery, name, url }) => {
    // file uploader popup open indicator
    const [isFileUploaderOpen, setIsFileUploaderOpen] = useState(false);
    // ref to file input field
    const fileInputRef = useRef(null);

    const fileUploaderToggleHandler = () => {
        setIsFileUploaderOpen(prev => !prev);
    }

    const onUpload = async () => {
        // create form data for file upload
        const selectedFile = fileInputRef.current?.files?.[0];
        if (selectedFile) {
            const lastModified = dayjs.utc(selectedFile.lastModified);

            if (disallowNonTodayFileUpload) {
                const todayDate = dayjs.utc();
                const isToday = lastModified.isSame(todayDate, 'day');

                if (!isToday) {
                    const err_ = `ERROR: older file selected for upload, file: ${selectedFile.name}, lastModified: ${lastModified.toISOString()}`;
                    console.error(err_);
                    alert(err_);
                    setIsFileUploaderOpen(false);
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

            // create url for file upload
            url = url || API_ROOT_URL;
            const fileUploadUrl = `${url}/query-${fileUploadQuery}`;
            try {
                await axios.post(fileUploadUrl, formData);
                alert('SUCCESS: file uploaded successfully');
            } catch (err) {
                const { code, message, detail, status } = getErrorDetails(err);
                const err_ = `ERROR: file upload failed, ${JSON.stringify({ code, status, message, detail })}`;
                console.error(err_);
                alert(err_);
            } finally {
                setIsFileUploaderOpen(false);
            }
        } else {
            const err_ = 'ERROR: No file is selected for upload!';
            console.error(err_);
            alert(err_);
            setIsFileUploaderOpen(false);
        }
    }

    return (
        <React.Fragment>
            <Icon
                name='file upload'
                title='file upload'
                onClick={fileUploaderToggleHandler}>
                <FileUpload fontSize='small' />
            </Icon>
            <Dialog className={classes.backdrop} open={isFileUploaderOpen} onClose={fileUploaderToggleHandler}>
                <DialogTitle className={classes.dialog_title}>{name} File Upload</DialogTitle>
                <DialogContent className={classes.dialog_body}>
                    <DialogContentText className={classes.dialog_text}>Select file to upload</DialogContentText>
                    <input ref={fileInputRef} accept='.csv' type='file' />
                </DialogContent>
                <DialogActions>
                    <Button variant='contained' color='error' onClick={fileUploaderToggleHandler} startIcon={<Delete />}>Discard</Button>
                    <Button variant='contained' color='success' onClick={onUpload} startIcon={<FileUpload />}>Upload</Button>
                </DialogActions>
            </Dialog>
        </React.Fragment>
    )
}

export default FileUploaderMenu;