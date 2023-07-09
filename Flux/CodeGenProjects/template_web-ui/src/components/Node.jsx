import React from 'react';
import { Box } from '@mui/material';
import { capitalizeFirstLetter } from '../utils';
import { LiveHelp, RemoveCircle } from '@mui/icons-material';
import { Icon } from './Icon';
import NodeField from './NodeField';
import PropTypes from 'prop-types';
import classes from './Node.module.css';
import { Modes } from '../constants';

const Node = (props) => {

    let nodeClass = '';
    if (props.data['data-add']) {
        nodeClass = classes.add;
    } else if (props.data['data-remove']) {
        nodeClass = classes.remove;
    } else if (props.data['data-modified']) {
        nodeClass = classes.modified;
    }

    let nodeTitleColorClass = '';
    if (props.data.nameColor) {
        let nameColor = props.data.nameColor.toLowerCase();
        nodeTitleColorClass = classes[nameColor];
    }

    return (
        <Box className={classes.container}>
            <span className={classes.dash}>-</span>
            <Box className={classes.node_container} data-xpath={props.data.xpath} data-dataxpath={props.data.dataxpath}>
                {props.data.key && (
                    <div className={`${classes.node} ${nodeClass}`}>
                        <span className={nodeTitleColorClass}>{props.data.title ? props.data.title : props.data.name}</span>
                        {props.data.showDataType && <span className={classes.type}>{capitalizeFirstLetter(props.data.type)}</span>}
                    </div>
                )}
                <NodeField data={props.data} />
            </Box>
            {props.data.mode === Modes.EDIT_MODE && props.data.key == undefined && !props.data['data-remove'] &&  (
                <Box className={classes.menu}>
                    <RemoveCircle
                        data-remove={props.data.xpath}
                        onClick={props.onClick}
                    />
                </Box>
            )}
            {props.data.help &&
                <Icon title={props.data.help}>
                    <LiveHelp color='primary' />
                </Icon>
            }
        </Box>
    )
}

Node.propTypes = {
    data: PropTypes.object
}

export default Node;