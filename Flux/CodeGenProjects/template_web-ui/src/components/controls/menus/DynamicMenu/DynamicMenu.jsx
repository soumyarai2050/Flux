import React, { useMemo } from 'react';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import Box from '@mui/material/Box';
import { DATA_TYPES } from '../../../../constants';
import { getColorTypeFromValue } from '../../../../utils/ui/colorUtils';
import { getShapeFromValue, getSizeFromValue, getHoverTextType, getReducerArrayFromCollections } from '../../../../utils/ui/uiUtils';
import { capitalizeCamelCase } from '../../../../utils/core/stringUtils';
import { getValueFromReduxStoreFromXpath } from '../../../../utils/redux/reduxUtils';
import { flux_toggle, flux_trigger_strat } from '../../../../projectSpecificUtils';
import ValueBasedToggleButton from '../../../ui/ValueBasedToggleButton';
import { ValueBasedProgressBarWithHover } from '../../../ui/ValueBasedProgressBar';


const DynamicMenu = ({
    fieldsMetadata,
    commonKeys,
    onButtonToggle
}) => {
    const reducerArray = useMemo(() => getReducerArrayFromCollections(fieldsMetadata), [fieldsMetadata]);
    const reducerDict = useSelector(state => {
        const selected = {};
        reducerArray.forEach(reducerName => {
            const fieldName = 'modified' + capitalizeCamelCase(reducerName);
            selected[reducerName] = {
                [fieldName]: state[reducerName]?.[fieldName],
            }
        })
        return selected;
    }, (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    })

    const onClick = (e, action, xpath, value, dataSourceId, source = null, force = false) => {
        if (action === 'flux_toggle') {
            const updatedValue = flux_toggle(value);
            onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
        } else if (action === 'flux_trigger_strat') {
            const updatedValue = flux_trigger_strat(value);
            if (updatedValue) {
                onButtonToggle(e, xpath, updatedValue, dataSourceId, source, force);
            }
        }
    }

    // let alertBubble = <></>;
    // if (props.currentSchema) {
    //     let alertBubbleSourceXpath = props.currentSchema.widget_ui_data_element ? props.currentSchema.widget_ui_data_element.alert_bubble_source : undefined;
    //     let alertBubbleColorXpath = props.currentSchema.widget_ui_data_element ? props.currentSchema.widget_ui_data_element.alert_bubble_color : undefined;
    //     if (props.data && alertBubbleSourceXpath && alertBubbleColorXpath) {
    //         alertBubbleSourceXpath = alertBubbleSourceXpath.substring(alertBubbleSourceXpath.indexOf('.') + 1);
    //         alertBubbleColorXpath = alertBubbleColorXpath.substring(alertBubbleColorXpath.indexOf('.') + 1);
    //         if (props.xpath) {
    //             alertBubbleSourceXpath = alertBubbleSourceXpath.replace(`${props.xpath}.`, '');
    //             alertBubbleColorXpath = alertBubbleColorXpath.replace(`${props.xpath}.`, '');
    //         }

    //         let count = getAlertBubbleCount(props.data, alertBubbleSourceXpath);
    //         let color = getAlertBubbleColor(props.data, fieldsMetadata, alertBubbleSourceXpath, alertBubbleColorXpath);

    //         if (count > 0) {
    //             alertBubble = (
    //                 <AlertBubble content={count} color={color} />
    //             )
    //         }
    //     }
    // }

    return (
        <>
            {/* {alertBubble} */}
            {commonKeys && commonKeys.filter((collection) => ['button', 'progressBar'].includes(collection.type)).map((collection, index) => {
                if (collection.value === undefined || collection.value === null) return;

                if (collection.type === 'progressBar') {
                    let value = collection.value;

                    let maxFieldName = collection.maxFieldName;
                    let valueFieldName = collection.key;
                    let min = collection.min;
                    if (typeof (min) === DATA_TYPES.STRING) {
                        min = getValueFromReduxStoreFromXpath(reducerDict, min);
                    }
                    let max = collection.max;
                    if (typeof (max) === DATA_TYPES.STRING) {
                        maxFieldName = max.substring(max.lastIndexOf(".") + 1);
                        max = getValueFromReduxStoreFromXpath(reducerDict, max);
                    }
                    let hoverType = getHoverTextType(collection.progressBar.hover_text_type);

                    return (
                        <Box key={collection.tableTitle} sx={{ minWidth: 150, margin: '0 10px' }}>
                            <ValueBasedProgressBarWithHover
                                collection={collection}
                                value={value}
                                min={min}
                                max={max}
                                valueFieldName={valueFieldName}
                                maxFieldName={maxFieldName}
                                hoverType={hoverType}
                            />
                        </Box>
                    )
                } else if (collection.type === 'button') {
                    let value = collection.value;
                    let disabledCaptions = {};
                    if (collection.button.disabled_captions) {
                        collection.button.disabled_captions.split(',').forEach(valueCaptionPair => {
                            let [buttonValue, caption] = valueCaptionPair.split('=');
                            disabledCaptions[buttonValue] = caption;
                        })
                    }
                    let isDisabledValue = Object.keys(disabledCaptions).includes(String(value)) ? true : false;
                    let disabledCaption = isDisabledValue ? disabledCaptions[String(value)] : '';
                    let checked = String(collection.value) === collection.button.pressed_value_as_text;
                    let xpath = collection.xpath;
                    let color = getColorTypeFromValue(collection, String(collection.value));
                    let size = getSizeFromValue(collection.button.button_size);
                    let shape = getShapeFromValue(collection.button.button_type);
                    let caption = String(collection.value);

                    if (isDisabledValue) {
                        caption = disabledCaption;
                    } else if (checked && collection.button.pressed_caption) {
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
                            disabled={isDisabledValue}
                            xpath={xpath}
                            allowForceUpdate={collection.button.allow_force_update}
                            action={collection.button.action}
                            source={collection.source}
                            onClick={onClick}
                            iconName={collection.button.button_icon_name}
                            hideCaption={collection.button.hide_caption}
                        />
                    )
                }
            })}
        </ >
    )
}

export default DynamicMenu;