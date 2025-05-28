import React, { useState } from 'react';
import { Typography, Box, ClickAwayListener, Tooltip, IconButton } from "@mui/material";
import { Menu, HelpOutline, ArrowDropDownSharp, ArrowDropUpSharp, ContentCopy, AddOutlined, RemoveOutlined } from "@mui/icons-material";
import { DATA_TYPES, MODES } from '../constants';
import { Icon } from './Icon';
import PropTypes from 'prop-types';
import classes from './HeaderField.module.css';
import { get } from 'lodash';

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

    let bgColor = 'background.nodeHeader'; // Default
    const dataValue = get(props.updatedDataForColor, props.data.dataxpath);
    const storedDataValueForOriginalPath = get(props.storedDataForColor, props.data.xpath); // Use original xpath for stored data

    let isSelfEffectivelyDeleted = false;
    // Check if the item itself is marked for deletion or its data has vanished due to an ancestor deletion.
    if (props.data['data-remove'] && props.data.xpath.endsWith(']')) { // Array item explicitly marked for removal
        isSelfEffectivelyDeleted = true;
    } else if ((dataValue === null || dataValue === undefined) && 
               (storedDataValueForOriginalPath !== null && storedDataValueForOriginalPath !== undefined)) {
        // Data for this node is missing in updatedData but existed in storedData, implies ancestor deletion or self-deletion for objects.
        // This covers objects set to null, or any node (including containers like 'security') whose path leads to null/undefined data.
        if (props.data.type === DATA_TYPES.OBJECT && !passToRemoveActiveContext && props.data.required) {
            // If it's a required object that cannot be nulled out (no passToRemoveActiveContext), 
            // and it's missing, it must be due to an ancestor.
            isSelfEffectivelyDeleted = true;
        } else if (props.data.type === DATA_TYPES.OBJECT && passToRemoveActiveContext && props.data.mode === MODES.EDIT) {
            // Optional object explicitly set to null
            isSelfEffectivelyDeleted = true;
        } else if (props.data.type !== DATA_TYPES.OBJECT) {
            // For non-objects (arrays, primitives within objects that might become part of a deleted structure)
            isSelfEffectivelyDeleted = true;
        }
    }

    // Determine background color
    if (props.isParentMarkedForDeletion) { // If parent is deleted, this node also turns red (cascading)
        bgColor = 'var(--red-800)'; 
    } else if (isSelfEffectivelyDeleted) { // Else, if self is deleted
        bgColor = '#ffc7ce';
    } else if (props.visualState === 'added') { 
        bgColor = 'var(--green-400)'; 
    } else if (props.visualState === 'duplicated') { 
        bgColor = 'var(--green-400)'; 
    }

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
                <Typography variant="subtitle1" sx={{ display: 'flex', flex: '1' }} data-header-title="true"> {/* data-header-title is used by DataTree's handleClick */}
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
                        sx={{ padding: '2px' }}
                    >
                        <Typography variant="caption" sx={{ fontWeight: 'bold' }}>◄</Typography>
                    </IconButton>
                    <Typography variant="caption" sx={{ margin: '0 8px' }}>
                        {props.data.pagination.currentPage + 1}/{props.data.pagination.totalPages} 
                        {!props.data.isContainer && `(${props.data.pagination.totalItems} items)`}
                    </Typography>
                    <IconButton 
                        size="small" 
                        onClick={(e) => { 
                            e.stopPropagation(); 
                            props.data.pagination.onPageChange('next'); 
                        }} 
                        disabled={props.data.pagination.currentPage >= props.data.pagination.totalPages - 1}
                        sx={{ padding: '2px' }}
                    >
                        <Typography variant="caption" sx={{ fontWeight: 'bold' }}>►</Typography>
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
    onClick: PropTypes.func // Added onClick to propTypes
};

const HeaderOptions = ({ add, remove, show, metadata, onToggle, updatedData, storedData }) => {
    const { xpath, ref, type, dataxpath, mode, required } = metadata;
    const isChildArrayItem = xpath.endsWith(']');

    let isEffectivelyDeleted = false;
    const currentValue = get(updatedData, dataxpath);
    const originalValue = get(storedData, xpath);

    if (isChildArrayItem && metadata['data-remove']) {
        isEffectivelyDeleted = true;
    } else if ((currentValue === null || currentValue === undefined) && 
               (originalValue !== null && originalValue !== undefined)) {
        if (type === DATA_TYPES.OBJECT && metadata.passToRemoveActiveContext !== false && mode === MODES.EDIT && !required) {
             // Optional object explicitly set to null (passToRemoveActiveContext might not be on metadata directly, infer from 'remove' prop of HeaderOptions)
            isEffectivelyDeleted = true;
        } else if (type !== DATA_TYPES.OBJECT) {
            // For non-objects (arrays, primitives that became null/undefined due to ancestor)
            isEffectivelyDeleted = true;
        }
    }

    const showAdd = add && !isChildArrayItem && !isEffectivelyDeleted; // Hide Add if container is deleted
    const showCopy = add && isChildArrayItem && !isEffectivelyDeleted; 
    const showRemove = remove && ((isChildArrayItem && !isEffectivelyDeleted) || 
                                 (type === DATA_TYPES.OBJECT && !isChildArrayItem && metadata['object-remove'] && !isEffectivelyDeleted));

    if (showAdd || showCopy || showRemove) {
        if (show) {
            return (
                <ClickAwayListener onClickAway={() => onToggle(false)}>
                    <Box className={classes.menu} bgcolor='background.secondary'>
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
                <Box className={classes.option} bgcolor='background.secondary'
                >
                    <Icon title="More Options" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
                        <Menu />
                    </Icon>
                </Box>
            );
        }
    }

    return null; 
};

export default HeaderField;