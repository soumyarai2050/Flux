import React, { useState } from 'react';
import { Typography, Box, ClickAwayListener, Tooltip } from "@mui/material";
import { IndeterminateCheckBox, AddBox, AddCircle, RemoveCircle, Menu, LiveHelp } from "@mui/icons-material";
import { DataTypes, Modes } from '../constants';
import { Icon } from './Icon';
import PropTypes from 'prop-types';
import classes from './HeaderField.module.css';

const HeaderField = (props) => {
    const [showOptions, setShowOptions] = useState(false);

    const onClick = (e) => {
        setShowOptions(false);
        props.onClick(e);
    }

    const onToggle = (val) => {
        if (val) {
            setShowOptions(val);
        } else {
            setShowOptions((show) => !show);
        }
    }

    const title = props.data.title ? props.data.title : props.name;

    let add = false;
    let remove = false;
    if (props.data.mode === Modes.EDIT_MODE && !props.data.uiUpdateOnly) {
        if (props.data.type === DataTypes.ARRAY && !props.data['data-remove']) {
            add = true;
            remove = true;
        }
        if (props.data.type === DataTypes.OBJECT && !props.data.required) {
            if (props.data['object-add']) {
                add = true;
            }
            if (props.data['object-remove']) {
                remove = true;
            }
        }
    }

    return (
        <Box className={classes.container} data-xpath={props.data.xpath}>
            <Box className={classes.header} data-xpath={props.data.xpath}>
                <span className={classes.icon}>
                    {props.isOpen ? (
                        <IndeterminateCheckBox fontSize='small' data-close={props.data.xpath} onClick={props.onClick} />
                    ) : (
                        <AddBox data-open={props.data.xpath} onClick={props.onClick} />
                    )}
                </span>
                <Typography variant="subtitle1" >
                    {title}
                </Typography>
            </Box>

            <HeaderOptions
                add={add}
                remove={remove}
                show={showOptions}
                metadata={props.data}
                onClick={onClick}
                onToggle={onToggle}
            />
            {
                props.data.help && (
                    <Box className={classes.option}>
                        <Icon title={props.data.help}>
                            <LiveHelp color='primary' />
                        </Icon>
                    </Box>
                )
            }
        </Box >
    )
}

HeaderField.propTypes = {
    data: PropTypes.object
}

const HeaderOptions = ({ add, remove, show, metadata, onClick, onToggle }) => {
    const { xpath, ref } = metadata;

    if (add || remove) {
        if (show) {
            return (
                <ClickAwayListener onClickAway={() => onToggle(false)}>
                    <Box className={classes.menu}>
                        {add && (
                            <AddCircle
                                data-add={xpath}
                                data-ref={ref}
                                data-prop={JSON.stringify(metadata)}
                                onClick={onClick}
                            />
                        )}
                        {remove && (
                            <RemoveCircle
                                data-remove={xpath}
                                onClick={onClick}
                            />
                        )}
                    </Box>
                </ClickAwayListener>
            )
        } else {
            return (
                <Box className={classes.option}>
                    <Icon title="options" onClick={onToggle}>
                        <Menu />
                    </Icon>
                </Box>
            )
        }
    }
}

export default HeaderField;