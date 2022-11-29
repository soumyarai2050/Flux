import React from 'react';
import { makeStyles } from '@mui/styles';
import { Box } from '@mui/material';
import { capitalizeFirstLetter } from '../utils';
import { LiveHelp } from '@mui/icons-material';
import Icon from './Icon';
import NodeField from './NodeField';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    container: {
        display: 'flex',
        alignItems: 'center'
    },
    dash: {
        borderLeft: '1px solid #444',
        padding: '5px 0'
    },
    nodeContainer: {
        display: 'flex',
        alignItems: 'center',
        padding: '0 5px',
        paddingLeft: 0,
        width: 'max-content',
        borderRadius: '5px',
        "&:hover": {
            background: '#618685'
        }
    },
    node: {
        marginRight: 5,
        padding: '5px 14px',
        background: '#fefbd8',
        borderRadius: 5,
        boxShadow: '0 0 1px 0 #999'
    },
    nodeDataAdd: {
        background: '#b3e0e5'
    },
    nodeDataRemove: {
        background: '#f27981',
        textDecoration: 'line-through'
    },
    nodeDataModified: {
        background: '#ccc',
    },
    nodeType: {
        fontWeight: 'bold',
        marginLeft: 20
    }
})

const Node = (props) => {

    const classes = useStyles();

    let nodeClass = '';
    if (props.data['data-add']) {
        nodeClass = classes.nodeDataAdd;
    } else if (props.data['data-remove']) {
        nodeClass = classes.nodeDataRemove;
    } else if (props.data['data-modified']) {
        nodeClass = classes.nodeDataModified;
    }

    return (
        <Box className={classes.container}>
            <span className={classes.dash}>-</span>
            <Box className={classes.nodeContainer} data-xpath={props.data.xpath} data-dataxpath={props.data.dataxpath}>
                <div className={`${classes.node} ${nodeClass}`} onDoubleClick={() => props.data.onNodeDblClick(props.name)}>
                    <span>{props.data.title ? props.data.title : props.data.name}</span>
                    <span className={classes.nodeType}>{capitalizeFirstLetter(props.data.type)}</span>
                </div>
                <NodeField data={props.data} />
            </Box>
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