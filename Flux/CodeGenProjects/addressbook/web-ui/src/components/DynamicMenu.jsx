import React from 'react';
import { Switch, FormControlLabel } from '@mui/material';
import { makeStyles } from '@mui/styles';
import { ColorTypes } from '../constants'
import _ from 'lodash';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    label: {
        textTransform: 'uppercase',
        '& .MuiFormControlLabel-label': {
            fontWeight: 'bold'
        }
    },
    labelCritical: {
        color: '#9C0006 !important',
        '& .Mui-disabled': {
            color: '#9C0006 !important'
        },
        '& .MuiSwitch-thumb': {
            color: '#9C0006 !important'
        }
    },
    labelError: {
        color: '#9C0006 !important',
        '& .Mui-disabled': {
            color: '#9C0006 !important'
        },
        '& .MuiSwitch-thumb': {
            color: '#9C0006 !important'
        }
    },
    labelWarning: {
        color: '#9c6500 !important',
        '& .Mui-disabled': {
            color: '#9c6500 !important'
        },
        '& .MuiSwitch-thumb': {
            color: '#9c6500 !important'
        }
    },
    labelInfo: {
        color: 'blue !important',
        '& .Mui-disabled': {
            color: 'blue !important'
        },
        '& .MuiSwitch-thumb': {
            color: 'blue !important'
        }
    },
    labelDebug: {
        color: 'black !important',
        '& .Mui-disabled': {
            color: 'black !important'
        },
        '& .MuiSwitch-thumb': {
            color: 'black !important'
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

                let labelClass = '';
                if (color === ColorTypes.CRITICAL) labelClass = classes.labelCritical;
                else if (color === ColorTypes.ERROR) labelClass = classes.labelError;
                else if (color === ColorTypes.WARNING) labelClass = classes.labelWarning;
                else if (color === ColorTypes.INFO) labelClass = classes.labelInfo;
                else if (color === ColorTypes.DEBUG) labelClass = classes.labelDebug;

                return (
                    <FormControlLabel
                        key={index}
                        className={`${classes.label} ${labelClass}`}
                        disabled={props.disabled}
                        control={<Switch checked={checked} color={color} onChange={(e) => props.onSwitchToggle(e, c.key, xpath)} />}
                        label={c.title}
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