import React from 'react';
import { Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button } from '@mui/material';
import ReactJson from 'react-json-view';

export const ConfirmSavePopup = (props) => {

    return (
        <Dialog open={props.open} onClose={props.onClose}>
            <DialogTitle>Save Changes</DialogTitle>
            <DialogContent>
                <ReactJson
                    displayDataTypes={false}
                    displayObjectSize={false}
                    indentWidth={6}
                    enableClipboard={false}
                    name={false}
                    iconStyle='square'
                    src={props.src}
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={props.onClose} autoFocus>Discard Changes</Button>
                <Button onClick={props.onSave} autoFocus>Save</Button>
            </DialogActions>
        </Dialog>
    )
}

export const WebsocketUpdatePopup = (props) => {
    return (
        <Dialog open={props.open} onClose={props.onClose}>
            <DialogTitle>{props.title} Change Detected</DialogTitle>
            <DialogContent>
                <DialogContentText>New change detected from server. Your changes may be lost. Following changes are discarded:</DialogContentText>
                <ReactJson
                    displayDataTypes={false}
                    displayObjectSize={false}
                    indentWidth={6}
                    enableClipboard={false}
                    name={false}
                    iconStyle='square'
                    src={props.src}
                />
                {/* {Object.keys(discardedChanges).map(xpath => (
                    <DialogContentText>{xpath}: {discardedChanges[xpath]}</DialogContentText>
                ))} */}
            </DialogContent>
            <DialogActions>
                <Button onClick={props.onClose} autoFocus>OK</Button>
            </DialogActions>
        </Dialog>
    )
}