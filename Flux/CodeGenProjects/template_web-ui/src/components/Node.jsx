import React, { useRef, useEffect } from 'react';
import { Box, Tooltip } from '@mui/material';
import { capitalizeFirstLetter } from '../utils';
import { HelpOutline, HelpSharp, LiveHelp, NotListedLocationOutlined, RemoveCircle } from '@mui/icons-material';
import { Icon } from './Icon';
import NodeField from './NodeField';
import PropTypes from 'prop-types';
import classes from './Node.module.css';
import { MODES } from '../constants';
import { useTheme } from '@emotion/react';

const Node = (props) => {
    const theme = useTheme(); 
    const rootRef = useRef(null);
    const glowTimerIdRef = useRef(null);

    let nodeClass = '';
    if (props.data['data-add']) {
        nodeClass = classes.add;
    } else if (props.data['data-remove']) {
        nodeClass = classes.remove;
    } else if (props.data['data-modified']) {
        nodeClass = classes.modified;
    }

    let nodeTitleColor = theme.palette.mode === "dark" ? theme.palette.common.white:theme.palette.common.black;
    if (props.data.nameColor) {
        let nameColor = props.data.nameColor.toLowerCase();
        nodeTitleColor = theme.palette.text[nameColor];
    }

    useEffect(() => {
        const currentRootEl = rootRef.current;
        const shouldGlow = props.triggerGlowForXPath && props.data && props.triggerGlowForXPath === props.data.xpath;

        if (glowTimerIdRef.current) {
            clearTimeout(glowTimerIdRef.current);
            glowTimerIdRef.current = null;
        }
        if (currentRootEl) {
            currentRootEl.classList.remove(classes.newlyAddedGlow);
        }

        if (shouldGlow && currentRootEl) {
            currentRootEl.classList.add(classes.newlyAddedGlow);
            glowTimerIdRef.current = setTimeout(() => {
                if (rootRef.current) {
                    rootRef.current.classList.remove(classes.newlyAddedGlow);
                }
                glowTimerIdRef.current = null;
            }, 5000);
        }

        return () => {
            if (glowTimerIdRef.current) {
                clearTimeout(glowTimerIdRef.current);
                glowTimerIdRef.current = null;
            }
        };
    }, [props.triggerGlowForXPath, props.data, classes.newlyAddedGlow]);

    return (
        <Box className={classes.container} ref={rootRef}>
            {/* <span className={classes.dash}>-</span> */}
            <Box className={classes.node_container} data-xpath={props.data.xpath} data-dataxpath={props.data.dataxpath}>
                {props.data.key && (
                    <div className={`${classes.node} ${nodeClass}`}>
                        <span className={classes.node_title} style={{color: nodeTitleColor}}>{props.data.title ? props.data.title : props.data.name}</span>
                        {props.data.showDataType && <span className={classes.type}>{capitalizeFirstLetter(props.data.type)}</span>}
                        <div style={{ minWidth: '20px', display: 'flex', alignItems: 'center', marginLeft: '10px' }}>
                            {props.data.help && <Tooltip title={props.data.help} disableInteractive><HelpOutline sx={{cursor: 'pointer'}} fontSize='small' /></Tooltip>}
                        </div>
                    </div>
                )}
                <NodeField data={props.data} />
            </Box>
            {props.data.mode === MODES.EDIT && props.data.key == undefined && !props.data['data-remove'] && (
                <Box className={classes.menu}>
                    <RemoveCircle
                        data-remove={props.data.xpath}
                        onClick={props.onClick}
                    />
                </Box>
            )}
        </Box>
    )
}

Node.propTypes = {
    data: PropTypes.object,
    visualState: PropTypes.string,
    triggerGlowForXPath: PropTypes.string
}

export default Node;