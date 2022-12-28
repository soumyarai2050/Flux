import React, { Fragment } from 'react';
import { useSelector } from 'react-redux';
import { makeStyles } from '@mui/styles';
import _ from 'lodash';
import PropTypes from 'prop-types';
import { DataTypes } from '../constants';
import { getColorTypeFromValue, getShapeFromValue, getSizeFromValue, toCamelCase, capitalizeCamelCase, getColorTypeFromPercentage, getValueFromReduxStore, normalise } from '../utils';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { ValueBasedProgressBar } from './ValueBasedProgressBar';
import { Box } from '@mui/material';

const useStyles = makeStyles({})

const DynamicMenu = (props) => {
    const state = useSelector(state => state);
    const classes = useStyles();

    const onClick = (e, action, xpath, value) => {
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
        <Fragment>
            {props.commonKeyCollections && props.commonKeyCollections.filter(collection => ['button', 'progressBar'].includes(collection.type)).map((collection, index) => {
                if (collection.value === undefined) return;

                if (collection.type === 'progressBar') {
                    let value = collection.value;
                    if (value === undefined) return;

                    let min = collection.min;
                    if (typeof (min) === DataTypes.STRING) {
                        let sliceName = toCamelCase(min.split('.')[0]);
                        let propertyName = 'modified' + capitalizeCamelCase(min.split('.')[0]);
                        let minxpath = min.substring(min.indexOf('.') + 1);
                        min = getValueFromReduxStore(state, sliceName, propertyName, minxpath);
                    }
                    let max = collection.max;
                    if (typeof (max) === DataTypes.STRING) {
                        let sliceName = toCamelCase(max.split('.')[0]);
                        let propertyName = 'modified' + capitalizeCamelCase(max.split('.')[0]);
                        let maxxpath = max.substring(max.indexOf('.') + 1);
                        max = getValueFromReduxStore(state, sliceName, propertyName, maxxpath);
                    }

                    let percentage = normalise(value, max, min);
                    let color = getColorTypeFromPercentage(collection, percentage);

                    return (
                        <Box key={collection.key} sx={{minWidth: 150, margin: '0 10px'}}>
                            <ValueBasedProgressBar percentage={percentage} value={value} min={min} max={max} color={color} />
                        </Box>
                    )
                } else if (collection.type === 'button') {
                    let checked = String(collection.value) === collection.button.pressed_value_as_text;
                    let xpath = collection.xpath;
                    let color = getColorTypeFromValue(collection, String(collection.value));
                    let size = getSizeFromValue(collection.button.button_size);
                    let shape = getShapeFromValue(collection.button.button_type);
                    let caption = String(collection.value);

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
                            value={collection.value}
                            caption={caption}
                            xpath={xpath}
                            action={collection.button.action}
                            onClick={onClick}
                        />
                    )
                }
            })}

            {
                props.collections.filter(collection => collection.type === 'button' && collection.rootLevel).map((collection, index) => {
                    if (_.get(props.data, collection.key) === undefined) return;
                    let checked = String(_.get(props.data, collection.key)) === collection.button.pressed_value_as_text;
                    let xpath = _.get(props.data, `xpath_${collection.key}`) ? _.get(props.data, `xpath_${collection.key}`) : '';
                    let color = getColorTypeFromValue(collection, String(_.get(props.data, collection.key)));
                    let size = getSizeFromValue(collection.button.button_size);
                    let shape = getShapeFromValue(collection.button.button_type);
                    let caption = String(_.get(props.data, collection.key));

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
                            value={_.get(props.data, collection.key)}
                            caption={caption}
                            xpath={xpath}
                            action={collection.button.action}
                            onClick={onClick}
                        />
                    )
                })
            }


            {props.children}
        </Fragment >
    )
}

DynamicMenu.propTypes = {
    data: PropTypes.object,
    collections: PropTypes.array,
    disabled: PropTypes.bool,
    onSwitchToggle: PropTypes.func
}

export default DynamicMenu;