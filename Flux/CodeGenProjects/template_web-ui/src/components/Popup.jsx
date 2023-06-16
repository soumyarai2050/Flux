import React from 'react';
import { Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button, Typography } from '@mui/material';
import { Edit, Delete, ThumbUp, Save } from '@mui/icons-material';
import ReactJson from 'react-json-view';
import classes from './Popup.module.css';

export const ConfirmSavePopup = (props) => {

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText>Review changes:</DialogContentText>
                <ReactJson
                    displayDataTypes={false}
                    displayObjectSize={false}
                    indentWidth={6}
                    enableClipboard={true}
                    name={false}
                    iconStyle='square'
                    src={props.src}
                    collapsed={1}
                />
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={props.onClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onSave} startIcon={<Save />} autoFocus>Confirm Save</Button>
            </DialogActions>
        </Dialog>
    )
}

export const WebsocketUpdatePopup = (props) => {
    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText>New update detected from server. Your changes may be lost. Following unsaved changes are discarded:</DialogContentText>
                <ReactJson
                    displayDataTypes={false}
                    displayObjectSize={false}
                    indentWidth={6}
                    enableClipboard={true}
                    name={false}
                    iconStyle='square'
                    src={props.src}
                    collapsed={1}
                />
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='success' onClick={props.onClose} startIcon={<ThumbUp />} autoFocus>Okay</Button>
            </DialogActions>
        </Dialog>
    )
}

export const FormValidation = (props) => {

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText className={classes.dialog_text}>Form validation failed due to following errors:</DialogContentText>
                <ReactJson
                    displayDataTypes={false}
                    displayObjectSize={false}
                    indentWidth={6}
                    enableClipboard={true}
                    name={false}
                    iconStyle='square'
                    src={props.src}
                    collapsed={1}
                />
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={props.onClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onContinue} startIcon={<Edit />} autoFocus>Continue Editing</Button>
            </DialogActions>
        </Dialog>
    )
}