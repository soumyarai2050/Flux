import React, { useState } from 'react';
import { Typography, Box, ClickAwayListener, Tooltip, IconButton } from "@mui/material";
import { IndeterminateCheckBox, AddBox, AddCircle, RemoveCircle, Menu, LiveHelp, ArrowDropDownSharp, ArrowDropUpSharp, HelpSharp, HelpOutline, Copyright, ContentCopy, AddOutlined, RemoveOutlined, CopyAllOutlined } from "@mui/icons-material";
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
    if (props.data.mode === Modes.EDIT_MODE) {
        if (props.data.type === DataTypes.ARRAY && !props.data['data-remove'] && !props.data.uiUpdateOnly) {
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
            <Box className={classes.header} data-xpath={props.data.xpath} bgcolor='background.nodeHeader'>
                <span className={classes.icon}>
                    {props.isOpen ? (
                        <ArrowDropUpSharp fontSize='small' data-close={props.data.xpath} onClick={props.onClick} />
                    ) : (
                        <ArrowDropDownSharp data-open={props.data.xpath} onClick={props.onClick} />
                    )}
                </span>
                <Typography variant="subtitle1" sx={{ display: 'flex', flex: '1' }} >
                    {title}
                </Typography>
                {
                    props.data.help && (
                        <Tooltip title={props.data.help} disableInteractive>
                            <HelpOutline fontSize='small' />
                        </Tooltip>
                    )
                }
            </Box>

            <HeaderOptions
                add={add}
                remove={remove}
                show={showOptions}
                metadata={props.data}
                onClick={onClick}
                onToggle={onToggle}
            />
        </Box>
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
                    <Box className={classes.menu} bgcolor='background.secondary'>
                        {add && (
                            <>
                                <IconButton
                                    size='small'
                                    title='Add'
                                    data-add={xpath}
                                    data-ref={ref}
                                    data-prop={JSON.stringify(metadata)}
                                    onClick={onClick}>
                                    <AddOutlined fontSize='small' />
                                </IconButton>
                                <IconButton
                                    size='small'
                                    title='Copy'
                                    data-addcopy={xpath}
                                    data-ref={ref}
                                    data-prop={JSON.stringify(metadata)}
                                    onClick={onClick}>
                                    <ContentCopy fontSize='small' />
                                </IconButton>
                            </>
                        )}
                        {remove && (
                            <IconButton
                                size='small'
                                title='Remove'
                                data-remove={xpath}
                                onClick={onClick}>
                                <RemoveOutlined fontSize='small' />
                            </IconButton>
                        )}
                    </Box>
                </ClickAwayListener>
            )
        } else {
            return (
                <Box className={classes.option} bgcolor='background.secondary'>
                    <Icon title="More Options" onClick={onToggle}>
                        <Menu />
                    </Icon>
                </Box>
            )
        }
    }
}

export default HeaderField;