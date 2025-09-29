import React, { useState, useRef, useEffect } from 'react';
import { Box, Button, List, ListItem, ListItemButton, ListItemText, Tooltip, ClickAwayListener } from '@mui/material';
import { Add, Menu, MenuOpen, BarChart, PivotTableChartSharp, Done, Close } from '@mui/icons-material';
import styles from './ListPanel.module.css';
import { MODES } from '../../../constants';

function ListPanel({
    items = [],
    selectedIndex,
    onSelect,
    onCreate,
    onDelete,
    itemNameKey = 'name',
    addButtonText = 'Add new item',
    enableOverride = [],
    collapse = false,
    mode,
    onDoubleClick,
    additionalActions,
    children
}) {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [showPivotDropdown, setShowPivotDropdown] = useState(false);
    const dropdownRef = useRef(null);

    const handleToggleCollapse = () => {
        setIsCollapsed(!isCollapsed);
    };

    const handleItemSelect = (index) => {
        if (onSelect) {
            onSelect(index);
        }
    };

    const handleItemDoubleClick = (index) => {
        if (onDoubleClick) {
            onDoubleClick(index);
        }
    };

    const handleCreate = () => {
        if (onCreate) {
            onCreate();
        }
    };

    const handleItemDelete = (e, item, index) => {
        e.stopPropagation();
        if (onDelete) {
            onDelete(e, item[itemNameKey], index);
        }
    };

    const handlePivotIconClick = (e) => {
        e.stopPropagation();
        const isPivotEditMode = mode === MODES.EDIT && itemNameKey.includes('pivot');
        if (isPivotEditMode) {
            setShowPivotDropdown(!showPivotDropdown);
        } else {
            handleToggleCollapse();
        }
    };

    const getPivotActionHandlers = () => {
        if (additionalActions && selectedIndex > -1) {
            const selectedItem = items[selectedIndex];
            const actionsComponent = additionalActions(selectedItem, selectedIndex, mode, selectedIndex);

            if (actionsComponent && actionsComponent.props && actionsComponent.props.children) {
                const children = Array.isArray(actionsComponent.props.children) ? actionsComponent.props.children : [actionsComponent.props.children];
                const allComponents = children.flat().filter(child => child && child.props);

                // Find the edit mode fragment (second fragment in the array)
                let editModeComponents = [];
                for (const component of allComponents) {
                    if (component.props && component.props.children && Array.isArray(component.props.children)) {
                        editModeComponents = component.props.children.filter(child => child && child.props && child.props.title);
                        break;
                    }
                }

                // Find Apply and Discard buttons by title
                const applyIcon = editModeComponents.find(icon => icon.props.title === 'Apply');
                const discardIcon = editModeComponents.find(icon => icon.props.title === 'Discard');

                return {
                    handleApply: applyIcon?.props?.onClick,
                    handleDiscard: discardIcon?.props?.onClick
                };
            }
        }
        return { handleApply: null, handleDiscard: null };
    };

    const handlePivotAction = (actionType, e) => {
        e.stopPropagation();
        setShowPivotDropdown(false);

        const { handleApply, handleDiscard } = getPivotActionHandlers();

        if (actionType === 'apply' && handleApply) {
            handleApply();
        } else if (actionType === 'discard' && handleDiscard) {
            handleDiscard();
        }
    };

    const handleClickAway = () => {
        setShowPivotDropdown(false);
    };

    const containerClass = `${styles.list_container} ${isCollapsed ? styles.collapsed : ''}`;

    return (
        <Box className={containerClass}>
            {collapse && (
                <Box className={styles.collapse_header}>
                    <Button
                        variant="text"
                        size="small"
                        onClick={handleToggleCollapse}
                        className={styles.collapse_button}
                        title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
                    >
                        {isCollapsed ? <Menu fontSize="small" /> : <MenuOpen fontSize="small" />}
                    </Button>
                </Box>
            )}

            {isCollapsed && onCreate && (
                <Box className={styles.add_button_collapsed_container}>
                    <Button
                        color='warning'
                        variant='contained'
                        onClick={handleCreate}
                        className={styles.add_button_collapsed}
                        title={addButtonText}
                    >
                        <Add fontSize='small' />
                    </Button>
                </Box>
            )}

            {isCollapsed && selectedIndex > -1 && items[selectedIndex] && (() => {
                const selectedItem = items[selectedIndex];
                let iconToShow = <BarChart fontSize="small" sx={{ color: 'var(--blue-info)' }} />;
                const isPivot = itemNameKey.includes('pivot');
                const isPivotEditMode = mode === MODES.EDIT && isPivot;

                if (isPivot) {
                    iconToShow = <PivotTableChartSharp fontSize="small" sx={{ color: 'var(--blue-info)' }} />;
                }

                return (
                    <ClickAwayListener onClickAway={handleClickAway}>
                        <Box className={`${styles.add_button_collapsed_container} ${isPivot ? styles.pivot_dropdown_container : ''}`} sx={{ mt: 1 }}>
                            <Tooltip title={selectedItem[itemNameKey]} placement="right">
                                <Button
                                    ref={dropdownRef}
                                    variant="text"
                                    color="primary"
                                    onClick={handlePivotIconClick}
                                    className={`${styles.add_button_collapsed} ${isPivotEditMode ? styles.pivot_edit_glow : ''}`}
                                >
                                    {iconToShow}
                                </Button>
                            </Tooltip>

                            {isPivot && showPivotDropdown && (
                                <div className={`${styles.pivot_dropdown} ${showPivotDropdown ? styles.show : ''}`}>
                                    <div
                                        className={`${styles.pivot_dropdown_item} ${styles.apply}`}
                                        onClick={(e) => handlePivotAction('apply', e)}
                                        title="Apply"
                                    >
                                        <Done color="success" fontSize="small" />
                                    </div>
                                    <div
                                        className={`${styles.pivot_dropdown_item} ${styles.discard}`}
                                        onClick={(e) => handlePivotAction('discard', e)}
                                        title="Discard"
                                    >
                                        <Close color="error" fontSize="small" />
                                    </div>
                                </div>
                            )}
                        </Box>
                    </ClickAwayListener>
                );
            })()}

            <Box className={`${styles.list_content} ${isCollapsed ? styles.content_hidden : ''}`}>
                <Button
                    color='warning'
                    variant='contained'
                    onClick={handleCreate}
                    className={styles.add_button}
                >
                    <Add fontSize='small' />
                    {addButtonText}
                </Button>

                <List className={styles.list}>
                    {items.map((item, index) => {
                        if (enableOverride.includes(item[itemNameKey])) return null;

                        return (
                            <ListItem
                                className={styles.list_item}
                                key={index}
                                disablePadding
                                onClick={() => handleItemSelect(index)}
                                onDoubleClick={() => handleItemDoubleClick(index)}
                                sx={{
                                    color: item.time_series ? 'var(--blue-info)' : undefined,
                                    backgroundColor: selectedIndex === index ? 'rgba(25, 118, 210, 0.08)' : undefined,
                                    '&:hover': {
                                        backgroundColor: selectedIndex === index ? 'rgba(25, 118, 210, 0.12)' : 'rgba(0, 0, 0, 0.04)'
                                    }
                                }}
                            >
                                <ListItemButton>
                                    <ListItemText>{item[itemNameKey]}</ListItemText>
                                </ListItemButton>

                                {/* Render additional actions if provided */}
                                {additionalActions && additionalActions(item, index, mode, selectedIndex)}
                            </ListItem>
                        );
                    })}
                </List>

                {/* Optional children content */}
                {children}
            </Box>
        </Box>
    );
}

export default ListPanel;