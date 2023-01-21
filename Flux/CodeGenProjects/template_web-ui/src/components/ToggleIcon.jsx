import React from 'react';
import { makeStyles } from '@mui/styles';
import { Tooltip, ToggleButton, Avatar, IconButton } from '@mui/material';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    toggleIcon: {
        // margin: '4px !important',
        padding: '2px !important',
        borderRadius: '50%',
        color: '444 !important',
        '&.Mui-selected': {
            color: 'blue !important',
            // backgroundColor: '#999 !important'
        },
        '&.Mui-selected>.MuiAvatar-root': {
            color: 'white !important',
            backgroundColor: 'blue !important'
        }
    },
    avatar: {
        color: 'inherit !important',
        height: '30px! important',
        width: '30px !important',
        '&:hover': {
            background: 'white'
        },
        '&.Mui-selected': {
            color: 'white',
            backgroundColor: 'blue !important'
        }
    }
})

const ToggleIcon = (props) => {

    const classes = useStyles();

    return (
        <Tooltip title={props.title}>
            <ToggleButton size='small' className={classes.toggleIcon} name={props.name} selected={props.selected} onClick={() => props.onClick(props.name)} value={props.name}>
                <Avatar className={classes.avatar}>{props.children}</Avatar>
            </ToggleButton>
        </Tooltip>
    )
}

ToggleIcon.propTypes = {
    title: PropTypes.string,
    name: PropTypes.string.isRequired,
    children: PropTypes.any.isRequired,
    onClick: PropTypes.func.isRequired
}

export default ToggleIcon;