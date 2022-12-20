import React from 'react';
import { makeStyles } from '@mui/styles';
import _ from 'lodash';
import PropTypes from 'prop-types';
import { getColorTypeFromValue, getShapeFromValue, getSizeFromValue } from '../utils';
import ValueBasedToggleButton from './ValueBasedToggleButton';
import { flux_toggle, flux_trigger_strat } from '../projectSpecificUtils';

const useStyles = makeStyles({})

const DynamicMenu = (props) => {
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
        <>
            {props.collections.filter(collection => collection.type === 'button').map((collection, index) => {
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
            })}
            {props.children}
        </>
    )
}

DynamicMenu.propTypes = {
    data: PropTypes.object,
    collections: PropTypes.array,
    disabled: PropTypes.bool,
    onSwitchToggle: PropTypes.func
}

export default DynamicMenu;