import React, { useState, useRef, useEffect } from 'react';
import { Typography, Box, ClickAwayListener, Tooltip, IconButton } from "@mui/material";
import { Menu, HelpOutline, ArrowDropDownSharp, ArrowDropUpSharp, ContentCopy, AddOutlined, RemoveOutlined } from "@mui/icons-material";
import { DATA_TYPES, MODES } from '../constants';
import { Icon } from './Icon';
import PropTypes from 'prop-types';
import classes from './HeaderField.module.css';
import { get } from 'lodash';
import { useTheme } from '@emotion/react';


const HeaderField = (props) => {
    const [showOptions, setShowOptions] = useState(false);

    // onClick is now passed from DataTree's nodeRenderer
    const { onClick } = props;

    const onToggle = (val) => {
        if (val) {
            setShowOptions(val);
        } else {
            setShowOptions((show) => !show);
        }
    }
    const theme = useTheme();

    const title = props.data.title ? props.data.title : props.name;

    let passToAddActiveContext = false;
    let passToRemoveActiveContext = false;

    if (props.data.mode === MODES.EDIT) {
        const isArrayItem = props.data.xpath && props.data.xpath.endsWith(']');

        if (props.data.type === DATA_TYPES.ARRAY && !props.data['data-remove'] && !props.data.uiUpdateOnly) {
            passToAddActiveContext = true; 
        } else if (props.data.type === DATA_TYPES.OBJECT) {
            if (isArrayItem) {
                passToAddActiveContext = true;   
                passToRemoveActiveContext = true; 
            } else {
                if (!props.data.required) {
                    if (props.data['object-add']) { 
                        passToAddActiveContext = true;
                    }
                    if (props.data['object-remove']) { 
                        passToRemoveActiveContext = true;
                    }
                }
            }
        }
    }

    let bgColor = theme.palette.primary.dark; // Default
    let textDecoration = 'none';

    // Determine background color and text decoration based on data flags and visualState
    if (props.data['data-add'] || props.visualState === 'added' || props.visualState === 'duplicated') {
        bgColor = 'var(--green-success)'; // Changed from '--green-accent-400:' to 'var(--green-dark)'
    } else if (props.data['data-remove']) {
        bgColor = 'var(--red-error)'; // Light red for deleted
        textDecoration = 'line-through';
    }
    // No special styling for 'data-modified' in HeaderField as per requirement

    return (
        <Box className={classes.container} data-xpath={props.data.xpath} onClick={onClick}>
            <Box className={classes.header} data-xpath={props.data.xpath} bgcolor={bgColor} sx={{color: 'white'}} >
            <span className={classes.icon}>
    {props.isOpen ? (
        <ArrowDropUpSharp 
            fontSize='small' 
            data-close={props.data.xpath} 
            // The main onClick handler in DataTree now manages arrow clicks via data-attributes
        />
    ) : (
        <ArrowDropDownSharp 
            data-open={props.data.xpath} 
            // The main onClick handler in DataTree now manages arrow clicks via data-attributes
        />
    )}
</span>
                <Typography variant="subtitle1" sx={{ display: 'flex', flex: '1', textDecoration: textDecoration }} data-header-title="true"> {/* data-header-title is used by DataTree's handleClick */}
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

            {/* Pagination Controls */}
            {props.data.pagination && props.data.pagination.totalPages > 1 && (
                <Box 
                    className={`${classes.paginationControls} ${props.data.isContainer ? classes.containerPagination : classes.childPagination}`}
                    onClick={(e) => e.stopPropagation()}
                    sx={{ 
                        display: 'flex',
                        alignItems: 'center', 
                        justifyContent: 'flex-end', 
                        padding: '2px 8px', 
                        borderTop: '1px solid rgba(0,0,0,0.1)',
                        backgroundColor: 'rgba(0,0,0,0.02)'
                    }}
                >
                    <IconButton 
                        size="small" 
                        onClick={(e) => { 
                            e.stopPropagation(); 
                            props.data.pagination.onPageChange('prev'); 
                        }} 
                        disabled={props.data.pagination.currentPage === 0}
                        sx={{ 
                            padding: '2px',
                            '&.Mui-disabled': {
                                '& .MuiTypography-root': {
                                    color: theme.palette.text.disabled
                                }
                            }
                        }}
                    >
                        <Typography variant="caption" sx={{ 
                            fontWeight: 'bold', 
                            color: theme.palette.mode === 'light' ? theme.palette.text.default : theme.palette.text.primary 
                        }}>◄</Typography>
                    </IconButton>
                    <Typography variant="caption" sx={{ 
                        margin: '0 8px', 
                        color: theme.palette.mode === 'light' ? theme.palette.text.default : theme.palette.text.primary 
                    }}>
                        Page: {props.data.pagination.currentPage + 1}/{props.data.pagination.totalPages}
                        {!props.data.isContainer && `(${props.data.pagination.totalItems} items)`}
                    </Typography>
                    <IconButton 
                        size="small" 
                        onClick={(e) => { 
                            e.stopPropagation(); 
                            props.data.pagination.onPageChange('next'); 
                        }} 
                        disabled={props.data.pagination.currentPage >= props.data.pagination.totalPages - 1}
                        sx={{ 
                            padding: '2px',
                            '&.Mui-disabled': {
                                '& .MuiTypography-root': {
                                    color: theme.palette.text.disabled
                                }
                            }
                        }}
                    >
                        <Typography variant="caption" sx={{ 
                            fontWeight: 'bold', 
                            color: theme.palette.mode === 'light' ? theme.palette.text.default : theme.palette.text.primary 
                        }}>►</Typography>
                    </IconButton>
                </Box>
            )}

            <HeaderOptions
                add={passToAddActiveContext}
                remove={passToRemoveActiveContext}
                show={showOptions}
                metadata={props.data}
                onToggle={onToggle}
                updatedData={props.updatedDataForColor}
                storedData={props.storedDataForColor}
                isOpen = {props.isOpen}
                bgColor={bgColor}
            />
        </Box>
    )
}

HeaderField.propTypes = {
    data: PropTypes.object,
    isOpen: PropTypes.bool,
    updatedDataForColor: PropTypes.object,
    storedDataForColor: PropTypes.object,
    visualState: PropTypes.string,
    isParentMarkedForDeletion: PropTypes.bool,
    onClick: PropTypes.func,
};

const HeaderOptions = ({ add, remove, show, metadata, onToggle, updatedData, storedData, bgColor }) => {
    const { xpath, ref, type, dataxpath, mode, required, dataStatus } = metadata; 
    const isChildArrayItem = xpath.endsWith(']');

    let isEffectivelyDeleted = false;
    const currentValue = get(updatedData, dataxpath);
    const originalValue = get(storedData, xpath);

    // Use direct data flags from metadata for showing/hiding options
    const isAdded = metadata['data-add'] || metadata.visualState === 'added' || metadata.visualState === 'duplicated';
    const isRemoved = metadata['data-remove'];
    // const isModified = metadata['data-modified']; // Not used for option visibility

    // Logic to determine if an item is considered "effectively deleted" for UI options, based on its current data or explicit flags.
    if (isChildArrayItem && isRemoved) { // Array item marked for removal
        isEffectivelyDeleted = true;
    } else if ((currentValue === null || currentValue === undefined) && 
               (originalValue !== null && originalValue !== undefined)) {
        // Data for this node is missing in updatedData but existed in storedData.
        // This covers objects set to null or any node whose path leads to null/undefined data.
        if (type === DATA_TYPES.OBJECT && metadata['object-remove'] && mode === MODES.EDIT && !required) {
            // Optional object explicitly set to null. 'object-remove' indicates it has a remove control.
            isEffectivelyDeleted = true;
        } else if (type !== DATA_TYPES.OBJECT && !isAdded) {
            // For non-objects (like array containers or primitive wrappers that became null/undefined).
            // If it's not marked as new/added, and its data is gone, it's effectively deleted.
            isEffectivelyDeleted = true;
        }
    }
    
    const showAdd = add && !isChildArrayItem && !isEffectivelyDeleted && !isRemoved;
    const showCopy = add && isChildArrayItem && !isEffectivelyDeleted && !isRemoved;
    const showRemove = remove && !isEffectivelyDeleted && !isRemoved; 

    if (showAdd || showCopy || showRemove) {
        if (show) {
            return (
                <ClickAwayListener onClickAway={() => onToggle(false)}>
                    <Box className={classes.menu} bgcolor={isAdded?"var(--green-success)": "background.secondary"}>
                        {showAdd && (
                            <IconButton
                                size='small'
                                title='Add'
                                data-add={xpath}
                                data-ref={ref}
                                data-prop={JSON.stringify(metadata)}
                                // onClick={(e) => e.stopPropagation()} // Stop propagation
                            >
                                <AddOutlined fontSize='small' />
                            </IconButton>
                        )}
                        {showCopy && (
                            <IconButton
                                size='small'
                                title='Duplicate'
                                data-duplicate={xpath}
                                data-ref={ref}
                                data-prop={JSON.stringify(metadata)}
                                // onClick={(e) => e.stopPropagation()} // Stop propagation
                            >
                                <ContentCopy fontSize='small' />
                            </IconButton>
                        )}
                        {showRemove && (
                            <IconButton
                                size='small'
                                title='Remove'
                                data-remove={xpath}
                                // onClick={(e) => e.stopPropagation()} // Stop propagation
                            >
                                <RemoveOutlined fontSize='small' />
                            </IconButton>
                        )}
                    </Box>
                </ClickAwayListener>
            );
        } else {
            return (
                <Box className={classes.option} bgcolor={bgColor}
                >
                    <Icon title="More Options" onClick={(e) => { e.stopPropagation(); onToggle(); }}
                        
                        >
                        <Menu 
                        sx={{ color: 'white !important' }}/>
                    </Icon>
                </Box>
            );
        }
    }

    return null; 
};

export default HeaderField;