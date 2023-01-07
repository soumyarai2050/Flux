import React from 'react';
import { useSelector } from 'react-redux';
import { Autocomplete, Box, TextField, Button, Divider, List, ListItem, ListItemButton, ListItemText, Chip, Badge } from '@mui/material';
import { makeStyles } from '@mui/styles';
import WidgetContainer from './WidgetContainer';
import { Download, Delete } from '@mui/icons-material';
import PropTypes from 'prop-types';
import Icon from './Icon';
import _ from 'lodash';
import { DB_ID, Modes, DataTypes } from '../constants';
import Alert from './Alert';
import AlertBubble from './AlertBubble';
import {
    getAlertBubbleColor, getAlertBubbleCount, getIdFromAbbreviatedKey, getColorTypeFromValue,
    getSizeFromValue, getShapeFromValue, normalise, toCamelCase, capitalizeCamelCase, getColorTypeFromPercentage, getValueFromReduxStore, getHoverTextType, getValueFromReduxStoreFromXpath
} from '../utils';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';

const useStyles = makeStyles({
    autocompleteDropdownContainer: {
        display: 'flex',
        margin: '10px 0'
    },
    autocomplete: {
        flex: 1,
        background: 'white'
    },
    button: {
        margin: '0 5px !important'
    },
    listItem: {
        padding: '0px 10px 10px'
    },
    badge: {
        margin: '0 10px'
    },
    listItemSelected: {
        background: 'rgba(25, 118, 210, 0.2) !important'
    }
})

const AbbreviatedFilterWidget = (props) => {
    const state = useSelector(state => state);
    const classes = useStyles();

    const onButtonClick = (e, action, xpath, value) => {
        if (action === 'flux_toggle') {
            let updatedData = flux_toggle(value);
            props.onButtonToggle(e, xpath, updatedData);
        } else if (action === 'flux_trigger_strat') {
            let updatedData = flux_trigger_strat(value);
            if (updatedData) {
                props.onButtonToggle(e, xpath, updatedData);
            }
        }
    }

    return (
        <WidgetContainer
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            menu={props.headerProps.menu}
            onChangeMode={props.headerProps.onChangeMode}
            onSave={props.headerProps.onSave}
            onReload={props.headerProps.onReload}
        >
            <Box className={classes.autocompleteDropdownContainer}>
                <Autocomplete
                    className={classes.autocomplete}
                    options={props.options}
                    getOptionLabel={(option) => option}
                    disableClearable
                    variant='outlined'
                    size='small'
                    value={props.searchValue ? props.searchValue : null}
                    onChange={props.onChange}
                    renderInput={(params) => <TextField {...params} label={props.bufferedLabel} />}
                />
                <Button className={classes.button} variant='contained' disableElevation disabled={props.searchValue ? false : true} onClick={props.onLoad}>
                    <Download fontSize='small' />
                </Button>
            </Box>
            <Divider textAlign='left'><Chip label={props.loadedLabel} /></Divider>
            <List className={classes.list}>
                {props.items && props.items.map((item, i) => {
                    let id = getIdFromAbbreviatedKey(props.abbreviated, item);
                    let disabled = props.mode === Modes.EDIT_MODE && props.selected !== id ? true : false;
                    let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === id)[0];
                    let alertBubbleCount = getAlertBubbleCount(metadata, props.alertBubbleSource);
                    let alertBubbleColor = getAlertBubbleColor(metadata, props.itemCollections, props.alertBubbleSource, props.alertBubbleColorSource);
                    let selectedClass = props.selected === id ? classes.listItemSelected : '';

                    let extraProps = [];
                    if (props.abbreviated.indexOf('$') !== -1) {
                        props.abbreviated.substring(props.abbreviated.indexOf('$') + 1).split('$').forEach(source => {
                            let object = {};
                            object.key = source.split('.').pop();
                            object.collection = props.itemCollections.filter(col => col.key === object.key)[0];
                            object.value = _.get(metadata, object.collection.xpath);
                            extraProps.push(object);
                        })
                    }

                    return (
                        <ListItem key={i} className={`${classes.listItem} ${selectedClass}`} selected={props.selected === id} disablePadding >
                            {alertBubbleCount > 0 && <AlertBubble content={alertBubbleCount} color={alertBubbleColor} />}
                            <ListItemButton disabled={disabled} onClick={() => props.onSelect(id)}>
                                <ListItemText>
                                    {item}
                                </ListItemText>
                            </ListItemButton>
                            {extraProps.map(extraProp => {
                                let collection = extraProp.collection;
                                if (extraProp.value === undefined || extraProp.value === null) return;

                                if (collection.type === 'button') {
                                    let checked = String(extraProp.value) === collection.button.pressed_value_as_text;
                                    let xpath = collection.xpath;
                                    let color = getColorTypeFromValue(collection, String(extraProp.value));
                                    let size = getSizeFromValue(collection.button.button_size);
                                    let shape = getShapeFromValue(collection.button.button_type);
                                    let caption = String(extraProp.value);

                                    if (checked && collection.button.pressed_caption) {
                                        caption = collection.button.pressed_caption;
                                    } else if (!checked && collection.button.unpressed_caption) {
                                        caption = collection.button.unpressed_caption;
                                    }

                                    return (
                                        <ValueBasedToggleButton
                                            key={collection.key}
                                            size={size}
                                            shape={shape}
                                            color={color}
                                            disabled={props.selected !== id ? true : false}
                                            value={extraProp.value}
                                            caption={caption}
                                            xpath={xpath}
                                            action={collection.button.action}
                                            onClick={onButtonClick}
                                        />
                                    )
                                } else if (collection.type === 'progressBar') {
                                    let value = extraProp.value;

                                    let min = collection.min;
                                    if (typeof (min) === DataTypes.STRING) {
                                        min = getValueFromReduxStoreFromXpath(state, min)
                                    }
                                    let max = collection.max;
                                    if (typeof (max) === DataTypes.STRING) {
                                        max = getValueFromReduxStoreFromXpath(state, max);
                                    }
                                    let hoverType = getHoverTextType(collection.progressBar.hover_text_type);

                                    return (
                                        <Box key={collection.key} sx={{ minWidth: '95%', position: 'absolute', bottom: 0 }}>
                                            <ValueBasedProgressBarWithHover
                                                collection={collection}
                                                value={value}
                                                min={min}
                                                max={max}
                                                hoverType={hoverType}
                                            />
                                        </Box>
                                    )
                                }
                            })}
                            <Icon title='Unload' disabled={disabled} onClick={() => props.onUnload(item)}>
                                <Delete fontSize='small' />
                            </Icon>
                        </ListItem>
                    )
                })}
            </List>
            {props.error && <Alert open={props.error ? true : false} onClose={props.onResetError} severity='error'>{props.error}</Alert>}
        </WidgetContainer>
    )
}

AbbreviatedFilterWidget.propTypes = {
    headerProps: PropTypes.object.isRequired,
    options: PropTypes.array,
    searchValue: PropTypes.string,
    onChange: PropTypes.func,
    bufferedLabel: PropTypes.string,
    onLoad: PropTypes.func,
    loadedLabel: PropTypes.string,
    selected: PropTypes.number,
    onSelect: PropTypes.func,
    onUnload: PropTypes.func
}

export default AbbreviatedFilterWidget;