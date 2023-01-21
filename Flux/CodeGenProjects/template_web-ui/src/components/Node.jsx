import React from 'react';
import { makeStyles } from '@mui/styles';
import { Box } from '@mui/material';
import { capitalizeFirstLetter } from '../utils';
import { LiveHelp } from '@mui/icons-material';
import Icon from './Icon';
import NodeField from './NodeField';
import PropTypes from 'prop-types';
import { ColorTypes } from '../constants';

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
    },
    nodeTitleCritical: {
        color: '#9C0006 !important',
        animation: `$blink 0.5s step-start infinite`
    },
    nodeTitleError: {
        color: '#9C0006 !important'
    },
    nodeTitleInfo: {
        color: 'blue !important'
    },
    nodeTitleWarning: {
        color: '#9c6500 !important'
    },
    nodeTitleSuccess: {
        color: 'darkgreen !important'
    },
    nodeTitleDebug: {
        color: 'black !important'
    },
    "@keyframes blink": {
        "from": {
            opacity: 1
        },
        "50%": {
            opacity: 0.8
        },
        "to": {
            opacity: 1
        }
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

    let nodeTitleColorClass = '';
    if (props.data.nameColor) {
        let nameColor = props.data.nameColor.toLowerCase();
        if (nameColor === ColorTypes.CRITICAL) nodeTitleColorClass = classes.nodeTitleCritical;
        else if (nameColor === ColorTypes.ERROR) nodeTitleColorClass = classes.nodeTitleError;
        else if (nameColor === ColorTypes.WARNING) nodeTitleColorClass = classes.nodeTitleWarning;
        else if (nameColor === ColorTypes.INFO) nodeTitleColorClass = classes.nodeTitleInfo;
        else if (nameColor === ColorTypes.DEBUG) nodeTitleColorClass = classes.nodeTitleDebug;
        else if (nameColor === ColorTypes.SUCCESS) nodeTitleColorClass = classes.nodeTitleSuccess;
    }

    return (
        <Box className={classes.container}>
            <span className={classes.dash}>-</span>
            <Box className={classes.nodeContainer} data-xpath={props.data.xpath} data-dataxpath={props.data.dataxpath}>
                <div className={`${classes.node} ${nodeClass}`} onDoubleClick={() => props.data.onNodeDblClick(props.name)}>
                    <span className={nodeTitleColorClass}>{props.data.title ? props.data.title : props.data.name}</span>
                    {props.data.showDataType && <span className={classes.nodeType}>{capitalizeFirstLetter(props.data.type)}</span>}
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