import React, { Fragment } from 'react';
import { useSelector } from 'react-redux';
import _ from 'lodash';
import PropTypes from 'prop-types';
import { DataTypes } from '../constants';
import { getColorTypeFromValue, getShapeFromValue, getSizeFromValue, toCamelCase, capitalizeCamelCase, getColorTypeFromPercentage, getValueFromReduxStore, normalise, getHoverTextType, getValueFromReduxStoreFromXpath, getAlertBubbleCount, getAlertBubbleColor } from '../utils';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';
import { ValueBasedProgressBarWithHover } from './ValueBasedProgressBar';
import { Box } from '@mui/material';
import AlertBubble from './AlertBubble';

const DynamicMenu = (props) => {
    const state = useSelector(state => state);

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

    let alertBubble = <></>;
    let alertBubbleSourceXpath = props.currentSchema.widget_ui_data.alert_bubble_source;
    let alertBubbleColorXpath = props.currentSchema.widget_ui_data.alert_bubble_color;
    if (alertBubbleSourceXpath && alertBubbleColorXpath) {
        alertBubbleSourceXpath = alertBubbleSourceXpath.substring(alertBubbleSourceXpath.indexOf('.') + 1);
        alertBubbleColorXpath = alertBubbleColorXpath.substring(alertBubbleColorXpath.indexOf('.') + 1);

        let count = getAlertBubbleCount(props.data, alertBubbleSourceXpath);
        let color = getAlertBubbleColor(props.data, props.collections, alertBubbleSourceXpath, alertBubbleColorXpath);

        if (count > 0) {
            alertBubble = (
                <AlertBubble content={count} color={color} />
            )
        }
    }

    return (
        <Fragment>
            {alertBubble}
            {props.commonKeyCollections && props.commonKeyCollections.filter(collection => ['button', 'progressBar'].includes(collection.type)).map((collection, index) => {
                if (collection.value === undefined || collection.value === null) return;

                if (collection.type === 'progressBar') {
                    let value = collection.value;

                    let min = collection.min;
                    if (typeof (min) === DataTypes.STRING) {
                        min = getValueFromReduxStoreFromXpath(state, min);
                    }
                    let max = collection.max;
                    if (typeof (max) === DataTypes.STRING) {
                        max = getValueFromReduxStoreFromXpath(state, max);
                    }
                    let hoverType = getHoverTextType(collection.progressBar.hover_text_type);

                    return (
                        <Box key={collection.tableTitle} sx={{ minWidth: 150, margin: '0 10px' }}>
                            <ValueBasedProgressBarWithHover
                                collection={collection}
                                value={value}
                                min={min}
                                max={max}
                                hoverType={hoverType}
                            />
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
                            key={collection.tableTitle}
                            name={collection.tableTitle}
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
                    let value = _.get(props.data, collection.key);
                    if (value === undefined || value === null) return;

                    let checked = String(value) === collection.button.pressed_value_as_text;
                    let xpath = _.get(props.data, `xpath_${collection.key}`) ? _.get(props.data, `xpath_${collection.key}`) : '';
                    let color = getColorTypeFromValue(collection, String(value));
                    let size = getSizeFromValue(collection.button.button_size);
                    let shape = getShapeFromValue(collection.button.button_type);
                    let caption = String(value);

                    if (checked && collection.button.pressed_caption) {
                        caption = collection.button.pressed_caption;
                    } else if (!checked && collection.button.unpressed_caption) {
                        caption = collection.button.unpressed_caption;
                    }

                    return (
                        <ValueBasedToggleButton
                            key={collection.tableTitle}
                            name={collection.tableTitle}
                            size={size}
                            shape={shape}
                            color={color}
                            value={value}
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