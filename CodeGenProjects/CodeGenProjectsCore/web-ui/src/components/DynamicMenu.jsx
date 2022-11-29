import React from 'react';
import { Switch, FormControlLabel } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { ColorTypes } from '../constants'
import _ from 'lodash';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    label: {
        '& .Mui-disabled': {
            color: 'white !important'
        }
    }
})

const DynamicMenu = (props) => {
    const classes = useStyles();

    return (
        <>
            {props.collections.filter(c => c.type === 'switch').map((c, index) => {
                let checked = _.get(props.data, c.key) ? _.get(props.data, c.key) : false;
                let xpath = _.get(props.data, `xpath_${c.key}`) ? _.get(props.data, `xpath_${c.key}`) : false;
                let color = c.color ? ColorTypes[c.color.split(',')[0].split('=')[1]] : ColorTypes.UNSPECIFIED;
                return (
                    <FormControlLabel
                        key={index}
                        className={classes.label}
                        disabled={props.disabled}
                        control={<Switch checked={checked} color={color} onChange={(e) => props.onSwitchToggle(e, c.key, xpath)} />}
                        label={c.key}
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