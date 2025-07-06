import React, { useState, useRef, useEffect } from 'react';
import { Typography, Box, ClickAwayListener, Tooltip, IconButton } from "@mui/material";
import { Menu, HelpOutline, ArrowDropDownSharp, ArrowDropUpSharp, ContentCopy, AddOutlined, RemoveOutlined } from "@mui/icons-material";
import { DATA_TYPES, MODES } from '../constants';
import { Icon } from './Icon';
import PropTypes from 'prop-types';
import classes from './HeaderField.module.css';
import { get } from 'lodash';
import { useTheme } from '@emotion/react';
import TreeExpansionControls from './trees/DataTree/TreeExpansionControls';


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

    /**
     * Helper function: Get the identifier value from the actual data
     * 
     * The identifier tells us which field in the data contains the meaningful value to display.
     * For example, if identifier is "broker", we look for data.broker
     * If identifier is "security.sec_id", we look for data.security.sec_id
     * 
     * @param {string} identifierPath - The path to the identifier field (like "broker" or "security.sec_id")
     * @param {object} nodeData - The tree node data containing paths and metadata
     * @param {object} updatedData - The actual data object containing values
     * @returns {string|number|null} - The identifier value or null if not found
     */
    const getIdentifierValue = (identifierPath, nodeData, updatedData) => {
        if (!identifierPath || !nodeData || !updatedData) return null;

        try {
            // Method 1: Get the value from the current node's data
            // The node has a "dataxpath" that tells us where its data is located
            const nodeDataPath = nodeData.dataxpath;
            if (nodeDataPath) {
                const nodeValue = get(updatedData, nodeDataPath);
                if (nodeValue && typeof nodeValue === 'object') {
                    // Look for the identifier field within this node's data
                    const identifierValue = get(nodeValue, identifierPath);
                    if (typeof identifierValue === 'string' || typeof identifierValue === 'number') {
                        return identifierValue;
                    }
                }
            }

            // Method 2: Fallback - try to get the value directly from the identifier path
            const value = get(updatedData, identifierPath);
            return (typeof value === 'string' || typeof value === 'number') ? value : null;
        } catch (error) {
            console.warn('Error getting identifier value:', error);
            return null;
        }
    };

    /**
     * Main function: Calculate the display title with identifier value
     * 
     * Here we check if this header has an identifier,
     * and if so, we add the actual value in parentheses next to the title.
     * 
     * Example: "Broker" becomes "Broker (ZERODHA)" if the broker field contains "ZERODHA"
     * 
     * @returns {string} - The display title with or without identifier value
     */
    const getDisplayTitle = () => {
        let displayTitle = title;
        // Check if this node has inherited array_obj_identifier from parent array , we have set this in complex props 
        if (props.data.array_obj_identifier) {
            const identifierValue = getIdentifierValue(
                props.data.array_obj_identifier,
                props.data,
                props.data.updatedDataForColor
            );
            if (identifierValue) {
                displayTitle = `${title} [${identifierValue}]`;
            }
        }
        return displayTitle;
    };

    let passToAddActiveContext = false;
    let passToRemoveActiveContext = false;

    // Check if this item is a child of a deleted container (cascaded deletion)
    // In this case, hide all options as the entire hierarchy is marked for deletion
    // Simple heuristic: if it's marked for removal but doesn't have canInitialize flag, 
    // it's likely a cascaded deletion from a container parent
    const isDirectlyDeleted = props.data['data-remove'] && (props.data.canInitialize || props.data.xpath?.endsWith(']'));
    const isCascadedDeletion = props.data['data-remove'] && !isDirectlyDeleted;

    if (props.data.mode === MODES.EDIT && !isCascadedDeletion) {
        const isArrayItem = props.data.xpath && props.data.xpath.endsWith(']');

        if (props.data.type === DATA_TYPES.ARRAY && !props.data['data-remove'] && !props.data.uiUpdateOnly) {
            passToAddActiveContext = true;
        } else if (props.data.type === DATA_TYPES.OBJECT) {
            // Check if orm_no_update is set
            const hasOrmNoUpdate = props.data.ormNoUpdate; // This comes from fieldProps mapping

            if (!hasOrmNoUpdate) {
                if (isArrayItem) {
                    // Array items can always be duplicated and removed (unless cascaded deletion)
                    passToAddActiveContext = true;
                    passToRemoveActiveContext = true;
                } else {
                    // Regular objects: use the flags set in treeHelper
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
    } else if (props.data['data-remove'] || props.visualState === 'removed') {
        bgColor = 'var(--red-error)'; // Light red for deleted
        textDecoration = 'line-through';
    }
    // No special styling for 'data-modified' in HeaderField as per requirement

    return (
        <Box className={classes.container} data-xpath={props.data.xpath} onClick={onClick}>
            <Box className={classes.header} data-xpath={props.data.xpath} bgcolor={bgColor} sx={{ color: 'white' }} >
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
                    {getDisplayTitle()}
                </Typography>

                {/* Add Expand/Collapse All controls for nodes with children */}
                <TreeExpansionControls
                    nodeXPath={props.data.xpath}
                    treeData={props.data.treeData || []}
                    onExpandAll={props.data.onExpandAll}
                    onCollapseAll={props.data.onCollapseAll}
                    onNodeToggle={props.data.onNodeToggle}
                    hasChildren={props.data.hasChildren}
                    expandedNodeXPaths={props.data.expandedNodeXPaths}
                // disabled={props.data.mode !== MODES.EDIT}
                />

                {
                    props.data.help && (
                        <Tooltip title={props.data.help} disableInteractive>
                            <HelpOutline fontSize='small' />
                        </Tooltip>
                    )
                }
            </Box>

            {/* Pagination Controls */}
            {props.data.pagination && (
                // Use displayPages when filtering is active, otherwise use totalPages
                (props.data.pagination.hasActiveFilters ?
                    props.data.pagination.displayPages > 1 :
                    props.data.pagination.totalPages > 1)
            ) && (
                <Box
                    className={`${classes.paginationControls} ${props.data.isContainer ? classes.containerPagination : classes.childPagination}`}
                    onClick={(e) => e.stopPropagation()}
                    sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'flex-end',
                        padding: '2px 8px',
                        borderTop: '1px solid rgba(0,0,0,0.1)',
                        backgroundColor: 'rgba(0,0,0,0.02)',
                        gap: 1
                    }}
                >
                    {/* Previous button */}
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
                    
                    {/* Page dropdown */}
                    <select
                        value={props.data.pagination.currentPage}
                        onChange={(e) => {
                            e.stopPropagation();
                            const page = Number(e.target.value);
                            props.data.pagination.onPageChange(page);
                        }}
                        style={{
                            height: '24px',
                            fontSize: '12px',
                            padding: '2px 4px',
                            border: `1px solid ${theme.palette.divider}`,
                            borderRadius: '4px',
                            backgroundColor: theme.palette.background.paper,
                            color: theme.palette.text.primary,
                            cursor: 'pointer'
                        }}
                    >
                        {Array.from({ 
                            length: props.data.pagination.hasActiveFilters ? 
                                props.data.pagination.displayPages : 
                                props.data.pagination.totalPages 
                        }, (_, i) => (
                            <option key={i} value={i}>
                                {`Page ${i + 1} of ${props.data.pagination.hasActiveFilters ? 
                                    props.data.pagination.displayPages : 
                                    props.data.pagination.totalPages}`}
                            </option>
                        ))}
                    </select>
                    
                    {/* Items count display */}
                    {!props.data.isContainer && (
                        <Typography variant="caption" sx={{
                            color: theme.palette.mode === 'light' ? theme.palette.text.default : theme.palette.text.primary,
                            fontSize: '11px'
                        }}>
                            ({props.data.pagination.hasActiveFilters ? 
                                props.data.pagination.displayItems : 
                                props.data.pagination.totalItems} items)
                        </Typography>
                    )}
                    
                    {/* Next button */}
                    <IconButton
                        size="small"
                        onClick={(e) => {
                            e.stopPropagation();
                            props.data.pagination.onPageChange('next');
                        }}
                        disabled={props.data.pagination.currentPage >= (
                            props.data.pagination.hasActiveFilters ? 
                            props.data.pagination.displayPages - 1 : 
                            props.data.pagination.totalPages - 1
                        )}
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
                isOpen={props.isOpen}
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
    const isRemoved = metadata['data-remove'] || metadata.visualState === 'removed';
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

    const showAdd = add && !isChildArrayItem && !isEffectivelyDeleted;
    const showCopy = add && isChildArrayItem && !isEffectivelyDeleted && !isRemoved;
    const showRemove = remove && !isEffectivelyDeleted && !isRemoved;

    if (showAdd || showCopy || showRemove) {
        if (show) {
            return (
                <ClickAwayListener onClickAway={() => onToggle(false)}>
                    <Box className={classes.menu} bgcolor={isAdded ? "var(--green-success)" : "background.secondary"}>
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
                    <Icon title="More Options" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
                        <Menu
                            sx={{ color: 'white !important' }} />
                    </Icon>
                </Box>
            );
        }
    }

    return null;
};

export default HeaderField;