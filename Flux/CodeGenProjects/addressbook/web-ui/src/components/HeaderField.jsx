import React, { useState } from 'react';
import { makeStyles } from "@mui/styles";
import { Typography, Box } from "@mui/material";
import { IndeterminateCheckBox, AddBox, AddCircle, RemoveCircle, Menu, LiveHelp } from "@mui/icons-material";
import { DataTypes, Modes } from '../constants';
import Icon from './Icon';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    headerContainer: {
        display: 'flex'
    },
    header: {
        background: '#0097a7',
        color: 'white',
        padding: 5,
        borderRadius: 5,
        width: '250px',
        display: 'flex',
        alignItems: 'center',
        margin: '1px 0',
        boxShadow: '0 0 1px 0 #999'
    },
    icon: {
        marginRight: 10,
        display: 'inline-flex'
    },
    options: {
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0 3px',
        borderRadius: 5,
        background: '#ccc',
        boxShadow: '0 0 1px 0 black',
        margin: '2px 0',
        marginLeft: 1
    }
})

const HeaderField = (props) => {

    const classes = useStyles();
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
        <Box className={classes.headerContainer} data-xpath={props.data.xpath}>
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
                <div className={classes.options}>
                    <AddCircle data-add={props.data.xpath} data-ref={props.data.ref} onClick={onClick} />
                    <RemoveCircle data-remove={props.data.xpath} onClick={onClick} />
                </div>
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