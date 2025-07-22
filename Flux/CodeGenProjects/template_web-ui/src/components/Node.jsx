import React, { useRef, useEffect } from 'react';
import { Box, Tooltip } from '@mui/material';
import { capitalizeFirstLetter } from '../utils/core/stringUtils';
import { HelpOutline, HelpSharp, LiveHelp, RemoveCircle, PushPin, PushPinOutlined } from '@mui/icons-material';
import { Icon } from './Icon';
import NodeField from './NodeField';
import PropTypes from 'prop-types';
import classes from './Node.module.css';
import { MODES } from '../constants';
import { useTheme } from '@emotion/react';

// Helper function to determine if a field should show the quick filter icon based on metadata
const isFilterableField = (nodeData) => {
    if (!nodeData || !nodeData.key) return false;
    
    // Field is filterable if it has any of these characteristics from the payload:
    // 1. auto_complete (dropdown options) - shown in payload as 'autocomplete'
    // 2. filter_enable set to true - shown in payload as 'filterEnable'  
    // 3. is an enum type (has dropdown options) - shown as type: 'enum' or has 'options'/'dropdowndataset'
    // 4. is a boolean type (can be toggled) - shown as type: 'boolean'
    // 5. has underlying_type indicating it's configurable
    const hasAutoComplete = nodeData.autocomplete || nodeData.options || nodeData.dropdowndataset;
    const hasFilterEnable = nodeData.filterEnable === true;
    const isEnum = nodeData.type === 'enum' || nodeData.customComponentType === 'autocomplete';
    const isBoolean = nodeData.type === 'boolean';
    const isString = nodeData.type === 'string';
    const isNumber = nodeData.type === 'number';
    
    // Also check if it's a primitive type that can be easily modified
    const isSimpleEditableType = isBoolean || isString || isNumber || isEnum;
    
    return hasAutoComplete || hasFilterEnable || isSimpleEditableType;
};

const Node = (props) => {
    const theme = useTheme();
    const rootRef = useRef(null);
    const glowTimerIdRef = useRef(null);
    const { onClick, glow } = props;

    // Combine the data from props with the handler functions passed as separate props
    // This ensures NodeField receives everything it needs in its 'data' prop.
    const nodeFieldData = {
        ...props.data,
        onTextChange: props.onTextChange,
        onSelectItemChange: props.onSelectItemChange,
        onCheckboxChange: props.onCheckboxChange,
        onAutocompleteOptionChange: props.onAutocompleteChange, // Mapping to the name used in NodeField
        onDateTimeChange: props.onDateTimeChange,
        onQuickFilterPin: props.onQuickFilterPin,
        onQuickFilterUnpin: props.onQuickFilterUnpin,
        pinnedFilters: props.pinnedFilters,
        enableQuickFilterPin: props.enableQuickFilterPin,
    };

    let nodeClass = '';
    if (props.data['data-add']) {
        nodeClass = classes.add;
    } else if (props.data['data-remove']) {
        nodeClass = classes.remove;
    } else if (props.data['data-modified']) {
        nodeClass = classes.modified;
    }

    let nodeTitleColor = theme.palette.mode === "dark" ? theme.palette.common.white : theme.palette.common.black;
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

    let FilterIcon = PushPinOutlined;
    let filterColor = 'default';
    let isPinned = false;
    let isNewlyCreated = false;
    
    // Check if this field has an active filter
    const hasActiveFilter = props.data.quickFilter && props.data.quickFilter[props.data.key];
    
    // Check if this is a newly created node (green state) - should not allow pinning
    isNewlyCreated = props.data['data-add'] || props.data.isNewlyCreated || false;
    
    // Check if this field is currently pinned - use dataxpath or key as uniqueId
    const currentUniqueId = props.data.dataxpath || props.data.key;
    isPinned = props.data.pinnedFilters && props.data.pinnedFilters.some(pin => pin.uniqueId === currentUniqueId);
    
    if (hasActiveFilter || isPinned) {
        FilterIcon = PushPin;
        filterColor = 'info';
    }

    // Only show pin icon if enabled for this tree
    const showPinIcon = props.data.enableQuickFilterPin && isFilterableField(props.data);

    if (props.data.data_invisible) return;

    return (
        <Box className={classes.container} ref={rootRef} onClick={onClick}>
            {/* <span className={classes.dash}>-</span> */}
            <Box className={`${classes.node_container} ${glow ? classes.glowGreen : ''}`} data-xpath={props.data.xpath} data-dataxpath={props.data.dataxpath}>
                {props.data.key && (
                    <div className={`${classes.node} ${nodeClass}`}>
                        <span className={classes.node_title} style={{ color: nodeTitleColor }}>{props.data.title ? props.data.title : props.data.name}</span>
                        {props.data.showDataType && (
                            <span className={classes.type}>
                                {capitalizeFirstLetter(props.data.type)}
                            </span>
                        )}
                        <div style={{ minWidth: '20px', display: 'flex', alignItems: 'center', marginLeft: '10px' }}>
                            {props.data.help && <Tooltip title={props.data.help} disableInteractive><HelpOutline sx={{ cursor: 'pointer' }} fontSize='small' color='info' /></Tooltip>}
                        </div>
                        {showPinIcon && (
                            <Icon
                                title={
                                    isNewlyCreated 
                                        ? 'Save the node first to enable pinning' 
                                        : (isPinned ? 'unpin quick filter' : 'pin quick filter')
                                }
                                onClick={() => {
                                    if (isNewlyCreated) {
                                        // Do nothing for newly created nodes
                                        return;
                                    }
                                    
                                    if (isPinned) {
                                        // Unpin the filter - use uniqueId to match what's stored
                                        const uniqueIdToUnpin = props.data.dataxpath || props.data.key;
                                        props.data.onQuickFilterUnpin && props.data.onQuickFilterUnpin(uniqueIdToUnpin);
                                    } else {
                                        // Pin the filter
                                        props.data.onQuickFilterPin && props.data.onQuickFilterPin(
                                            props.data.key, 
                                            props.data.title || props.data.name, 
                                            props.data.value, // Use actual current value
                                            props.data // Pass the full node data for field type information
                                        );
                                    }
                                }}
                                style={{ 
                                    marginLeft: 'auto', 
                                    opacity: isNewlyCreated ? 0.3 : 1,
                                    cursor: isNewlyCreated ? 'not-allowed' : 'pointer'
                                }}
                            >
                                <FilterIcon 
                                    fontSize='small' 
                                    color={isNewlyCreated ? 'disabled' : filterColor} 
                                />
                            </Icon>
                        )}
                    </div>
                )}
                <NodeField data={nodeFieldData} />
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