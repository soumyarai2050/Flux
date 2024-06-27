import React, { useEffect, useState } from 'react';
import { Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button, Typography, Box, TextField } from '@mui/material';
import { Edit, Delete, ThumbUp, Save } from '@mui/icons-material';
import ReactJson from 'react-json-view';
import classes from './Popup.module.css';
import { useTheme } from '@mui/material/styles';
import { getDataSourceColor } from '../utils';
import { cloneDeep } from 'lodash';

export const ConfirmSavePopup = (props) => {
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText>Review changes:</DialogContentText>
                <ReactJson
                    theme={jsonViewTheme}
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
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';
    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText>New update detected from server. Your changes may be lost. Following unsaved changes are discarded:</DialogContentText>
                <ReactJson
                    theme={jsonViewTheme}
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
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText className={classes.dialog_text}>Form validation failed due to following errors:</DialogContentText>
                <ReactJson
                    theme={jsonViewTheme}
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

export const CollectionSwitchPopup = (props) => {

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText className={classes.dialog_text}>Collection switched while in EDIT mode. Your changes may be lost.</DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={props.onClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onContinue} startIcon={<Edit />} autoFocus>Continue Editing</Button>
            </DialogActions>
        </Dialog>
    )
}

export const DataSourceHexColorPopup = (props) => {
    const theme = useTheme();
    const [dataSourceColors, setDataSourceColors] = useState(props.dataSourceColors);

    useEffect(() => {
        setDataSourceColors(props.dataSourceColors);
    }, [props.dataSourceColors])

    const onTextChange = (e, idx) => {
        const updatedDataSourceColors = cloneDeep(dataSourceColors);
        for (let i=0; i<idx; i++) {
            if (updatedDataSourceColors[i] === undefined) {
                updatedDataSourceColors[i] = '';
            }
        }
        updatedDataSourceColors[idx] = e.target.value;
        setDataSourceColors(updatedDataSourceColors);
    }

    const onSave = () => {
        props.onSave(dataSourceColors);
        props.onClose();
    }

    return (
        <Dialog className={classes.backdrop} open={props.open} onClose={props.onClose}>
            <DialogTitle className={classes.dialog_title}>Data Source Hex Color</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                {props.maxRowSize && Array(props.maxRowSize).fill(0).map((item, index) => {
                    const defaultColor = getDataSourceColor(theme, index);
                    return (
                        <Box key={index} className={classes.field}>
                            <span className={classes.field_name}>Hex Color</span>
                            <TextField
                                className={classes.text_field}
                                id={`${index}`}
                                name={`${index}`}
                                size='small'
                                value={dataSourceColors?.[index] || ''}
                                onChange={(e) => onTextChange(e, index)}
                                variant='outlined'
                                placeholder={defaultColor}
                                inputProps={{
                                    style: { padding: '6px 10px' }
                                }}
                            />
                        </Box>
                    )
                })}
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={props.onClose} startIcon={<Delete />}>Cancel</Button>
                <Button variant='contained' color='success' onClick={onSave} startIcon={<ThumbUp />}>Save</Button>
            </DialogActions>
        </Dialog>
    )
}