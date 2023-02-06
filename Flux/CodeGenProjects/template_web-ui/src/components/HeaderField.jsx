import React, { useState } from 'react';
import { Typography, Box, ClickAwayListener } from "@mui/material";
import { IndeterminateCheckBox, AddBox, AddCircle, RemoveCircle, Menu, LiveHelp } from "@mui/icons-material";
import { DataTypes, Modes } from '../constants';
import {Icon} from './Icon';
import PropTypes from 'prop-types';
import classes from './HeaderField.module.css';

const HeaderField = (props) => {
    const [showOptions, setShowOptions] = useState(false);

    const onClick = (e) => {
        setShowOptions(false);
        props.onClick(e);
    }

    let allowCreate = false;
    if (props.data.mode === Modes.EDIT_MODE) {
        if (props.data.type === DataTypes.ARRAY && !props.data['data-remove'] && !props.data.uiUpdateOnly) {
            allowCreate = true;
        }
    }

    return (
        <Box className={classes.container} data-xpath={props.data.xpath}>
            <Typography variant="subtitle1" >
                <div className={classes.header} data-xpath={props.data.xpath} onDoubleClick={() => props.data.onNodeDblClick(props.name)} >
                    <span className={classes.icon}>
                        {props.isOpen ? <IndeterminateCheckBox data-close={props.data.xpath} onClick={props.onClick} /> :
                            <AddBox data-open={props.data.xpath} onClick={props.onClick} />}
                    </span>
                    <span>{props.data.title ? props.data.title : props.name}</span>
                </div>
            </Typography>
            {allowCreate ? showOptions ? (
                <ClickAwayListener onClickAway={() => setShowOptions(false)}>
                    <div className={classes.menu}>
                        <AddCircle data-add={props.data.xpath} data-ref={props.data.ref} onClick={onClick} />
                        <RemoveCircle data-remove={props.data.xpath} onClick={onClick} />
                    </div>
                </ClickAwayListener>
            ) : (
                <Icon title="More Options" onClick={() => setShowOptions(!showOptions)}>
                    <Menu />
                </Icon>
            ) : null}
            {props.data.help &&
                <Icon title={props.data.help}>
                    <LiveHelp color='primary' />
                </Icon>
            }
        </Box>
    )
}

HeaderField.propTypes = {
    data: PropTypes.object
}

export default HeaderField;