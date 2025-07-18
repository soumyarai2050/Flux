import React, { useEffect, useState, useMemo } from 'react';
import { Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button, Typography, Box, TextField, Autocomplete } from '@mui/material';
import { Edit, Delete, ThumbUp, Save } from '@mui/icons-material';
import ReactJson from 'react-json-view';
import classes from './Popup.module.css';
import { useTheme } from '@mui/material/styles';
import { getDataSourceColor } from '../utils/ui/themeUtils';
import { cloneDeep } from 'lodash';
import VerticalDataTable from './tables/VerticalDataTable';
import PropTypes from 'prop-types';

/**
 * @function ConfirmSavePopup
 * @description A popup component to confirm and review changes before saving.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onSave - Callback function to save the changes.
 * @param {string} props.title - The title of the popup.
 * @param {object} props.src - The data object containing changes to be reviewed.
 * @returns {React.ReactElement} The rendered ConfirmSavePopup component.
 */
export const ConfirmSavePopup = (props) => {
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        props.onClose();
    };

    return (
        <Dialog aria-label='confirm-save-popup' className={classes.backdrop} open={props.open} onClose={handleClose}>
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
                <Button variant='contained' color='error' onClick={handleClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onSave} startIcon={<Save />} autoFocus>Confirm Save</Button>
            </DialogActions>
        </Dialog>
    );
};

ConfirmSavePopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    title: PropTypes.string.isRequired,
    src: PropTypes.object.isRequired,
};

/**
 * @function WebsocketUpdatePopup
 * @description A popup component to inform the user about websocket updates that might discard unsaved changes.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {string} props.title - The title of the popup.
 * @param {object} props.src - The data object containing discarded changes.
 * @returns {React.ReactElement} The rendered WebsocketUpdatePopup component.
 */
export const WebsocketUpdatePopup = (props) => {
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        props.onClose();
    };

    return (
        <Dialog aria-label='ws-update-popup' className={classes.backdrop} open={props.open} onClose={handleClose}>
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
                <Button variant='contained' color='success' onClick={handleClose} startIcon={<ThumbUp />} autoFocus>Okay</Button>
            </DialogActions>
        </Dialog>
    );
};

WebsocketUpdatePopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    title: PropTypes.string.isRequired,
    src: PropTypes.object.isRequired,
};

/**
 * @function FormValidation
 * @description A popup component to display form validation errors.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onContinue - Callback function to continue editing.
 * @param {string} props.title - The title of the popup.
 * @param {object} props.src - The data object containing validation errors.
 * @returns {React.ReactElement} The rendered FormValidation component.
 */
export const FormValidation = (props) => {
    const theme = useTheme();
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        props.onClose();
    };

    return (
        <Dialog aria-label='form-val-popup' className={classes.backdrop} open={props.open} onClose={handleClose}>
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
                <Button variant='contained' color='error' onClick={handleClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onContinue} startIcon={<Edit />} autoFocus>Continue Editing</Button>
            </DialogActions>
        </Dialog>
    );
};

FormValidation.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onContinue: PropTypes.func.isRequired,
    title: PropTypes.string.isRequired,
    src: PropTypes.object.isRequired,
};

/**
 * @function CollectionSwitchPopup
 * @description A popup component to warn the user about switching collections while in edit mode.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onContinue - Callback function to continue with the collection switch.
 * @param {string} props.title - The title of the popup.
 * @returns {React.ReactElement} The rendered CollectionSwitchPopup component.
 */
export const CollectionSwitchPopup = (props) => {
    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        props.onClose();
    };

    return (
        <Dialog aria-label='collection-switch-popup' className={classes.backdrop} open={props.open} onClose={handleClose}>
            <DialogTitle className={classes.dialog_title}>{props.title}</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                <DialogContentText className={classes.dialog_text}>Collection switched while in EDIT mode. Your changes may be lost.</DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={handleClose} startIcon={<Delete />}>Discard Changes</Button>
                <Button variant='contained' color='success' onClick={props.onContinue} startIcon={<Edit />} autoFocus>Continue Editing</Button>
            </DialogActions>
        </Dialog>
    );
};

CollectionSwitchPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onContinue: PropTypes.func.isRequired,
    title: PropTypes.string.isRequired,
};

/**
 * @function DataSourceHexColorPopup
 * @description A popup component for configuring data source hex colors.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onSave - Callback function to save the data source colors.
 * @param {Array<string>} props.dataSourceColors - An array of hex color strings for data sources.
 * @param {number} props.maxRowSize - The maximum number of rows/data sources.
 * @returns {React.ReactElement} The rendered DataSourceHexColorPopup component.
 */
export const DataSourceHexColorPopup = (props) => {
    const theme = useTheme();
    const [dataSourceColors, setDataSourceColors] = useState(props.dataSourceColors);

    useEffect(() => {
        setDataSourceColors(props.dataSourceColors);
    }, [props.dataSourceColors]);

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        props.onClose();
    };

    const onTextChange = (e, idx) => {
        const updatedDataSourceColors = cloneDeep(dataSourceColors);
        // Ensure array has enough elements up to the current index
        for (let i = 0; i < idx; i++) {
            if (updatedDataSourceColors[i] === undefined) {
                updatedDataSourceColors[i] = '';
            }
        }
        updatedDataSourceColors[idx] = e.target.value;
        setDataSourceColors(updatedDataSourceColors);
    };

    const onSave = () => {
        props.onSave(dataSourceColors);
        props.onClose();
    };

    const handleKeyDown = (e) => {
        if (e.key.length === 1 || e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === 'Escape') {
            if (e.key !== 'Escape') {
                e.stopPropagation();
            }
        }
    };

    return (
        <Dialog aria-label='data-source-popup' className={classes.backdrop} open={props.open} onClose={handleClose}>
            <DialogTitle className={classes.dialog_title}>Data Source Hex Color</DialogTitle>
            <DialogContent className={classes.dialog_body}>
                {props.maxRowSize && Array(props.maxRowSize).fill(0).map((_, index) => {
                    const defaultColor = getDataSourceColor(theme, index);
                    return (
                        <Box key={index} className={classes.field}>
                            <span className={classes.field_name}>Hex Color</span>
                            <TextField
                                key={`color-input-${index}`} // Added key to TextField
                                className={classes.text_field}
                                id={`color-input-${index}`}
                                name={`color-input-${index}`}
                                size='small'
                                value={dataSourceColors?.[index] || ''}
                                onChange={(e) => onTextChange(e, index)}
                                variant='outlined'
                                placeholder={defaultColor}
                                inputProps={{
                                    style: { padding: '6px 10px' }
                                }}
                                onKeyDown={handleKeyDown}
                            />
                        </Box>
                    );
                })}
            </DialogContent>
            <DialogActions>
                <Button variant='contained' color='error' onClick={handleClose} startIcon={<Delete />}>Cancel</Button>
                <Button variant='contained' color='success' onClick={onSave} startIcon={<ThumbUp />}>Save</Button>
            </DialogActions>
        </Dialog>
    );
};

DataSourceHexColorPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    dataSourceColors: PropTypes.array.isRequired,
    maxRowSize: PropTypes.number.isRequired,
};

/**
 * @function SaveLayoutPopup
 * @description A popup component for saving the current layout with a profile ID.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onSave - Callback function to save the layout.
 * @param {Array<object>} props.storedArray - An array of stored layouts.
 * @param {string} props.profileId - The current profile ID.
 * @param {function} props.onProfileIdChange - Callback function for profile ID changes.
 * @returns {React.ReactElement} The rendered SaveLayoutPopup component.
 */
export const SaveLayoutPopup = ({
    open,
    onClose,
    storedArray,
    profileId,
    onProfileIdChange,
    onSave
}) => {

    const profileExists = useMemo(() => storedArray.some((o) => o.profile_id === profileId), [storedArray, profileId]);

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        onClose();
    };

    return (
        <Dialog
            aria-label='save-layout-popup'
            open={open}
            onClose={handleClose}>
            <DialogTitle>Save Layout</DialogTitle>
            <DialogContent>
                <DialogContentText className={classes.dialog_text}>
                    To save the layout, please enter profile id. If profile id already exists, layout will be overwritten.
                </DialogContentText>
                <TextField
                    label="Profile Id"
                    variant="standard"
                    error={profileExists}
                    helperText={profileExists ? 'Profile Id already exists. Click on Save to overwrite.' : ''}
                    value={profileId}
                    onChange={onProfileIdChange}
                />
            </DialogContent>
            <DialogActions>
                <Button color='error' variant='contained' onClick={handleClose} autoFocus>Discard</Button>
                <Button color='success' variant='contained' onClick={onSave} autoFocus>Save</Button>
            </DialogActions>
        </Dialog>
    );
};

SaveLayoutPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    storedArray: PropTypes.array.isRequired,
    profileId: PropTypes.string.isRequired,
    onProfileIdChange: PropTypes.func.isRequired,
};

/**
 * @function LoadLayoutPopup
 * @description A popup component for loading a previously saved layout.
 * @param {object} props - The properties for the component.
 * @param {boolean} props.open - Whether the popup is open.
 * @param {function} props.onClose - Callback function to close the popup.
 * @param {function} props.onReset - Callback function to reset the layout.
 * @param {Array<object>} props.storedArray - An array of stored layouts to choose from.
 * @param {object} props.value - The currently selected layout profile.
 * @param {function} props.onSearchValueChange - Callback function for search value changes.
 * @param {function} props.onLoad - Callback function to load the selected layout.
 * @returns {React.ReactElement} The rendered LoadLayoutPopup component.
 */
export const LoadLayoutPopup = ({
    open,
    onClose,
    onReset,
    storedArray,
    value,
    onSearchValueChange,
    onLoad
}) => {

    const handleClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        onClose();
    };

    return (
        <Dialog
            aria-label='load-layout-popup'
            open={open}
            onClose={handleClose}>
            <DialogTitle>Load Layout</DialogTitle>
            <DialogContent>
                <DialogContentText className={classes.dialog_text}>
                    To load the layout, select the profile id, or <Button color='error' onClick={onReset}>Reset Layout</Button>
                </DialogContentText>
                <Autocomplete
                    options={storedArray}
                    getOptionLabel={(option) => option.profile_id ?? ''}
                    disableClearable
                    variant='outlined'
                    size='small'
                    value={value ?? null}
                    onChange={onSearchValueChange}
                    renderInput={(params) => <TextField {...params} label="Profile id" />}
                />
            </DialogContent>
            <DialogActions>
                <Button color='error' variant='contained' onClick={handleClose} autoFocus>Discard</Button>
                <Button color='success' variant='contained' disabled={value ? false : true} onClick={onLoad} autoFocus>Load</Button>
            </DialogActions>
        </Dialog>
    );
};

LoadLayoutPopup.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onReset: PropTypes.func.isRequired,
    storedArray: PropTypes.array.isRequired,
    value: PropTypes.object,
    onSearchValueChange: PropTypes.func.isRequired,
    onLoad: PropTypes.func.isRequired,
};
