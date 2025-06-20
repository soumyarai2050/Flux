import React, { useState } from 'react';
import {
    ChartSettingsMenu, ColumnSettingsMenu, CreateMenu, DataSourceColorMenu, DownloadMenu, DynamicMenu,
    EditSaveToggleMenu, FilterMenu, JoinMenu, LayoutSwitchMenu, MaximizeRestoreToggleMenu, PivotSettingsMenu, ReloadMenu, VisibilityMenu
} from './menus';
import { MODEL_TYPES } from '../constants';
import { cloneDeep } from 'lodash';
import { Menu } from '@mui/material';
import Icon from './Icon';
import { MenuOpen, Menu as MenuIcon } from '@mui/icons-material';
import ButtonQuery from './ButtonQuery';
import { FilterDialog } from './menus/FilterMenu';
import { DataSourceHexColorPopup } from './Popup';

const MenuGroup = ({
    columns,
    columnOrders,
    showAll,
    moreAll,
    mode,
    joinBy,
    maxRowSize,
    dataSourceColors,
    fieldsMetadata,
    filters,
    centerJoin,
    flip,
    layout,
    supportedLayouts,
    isMaximized,
    showMore,
    showHidden,
    modelType,
    enableOverride,
    disableOverride,
    showLess,
    commonKeys,
    modelSchema,
    url,
    viewUrl,
    onShowAllToggle,
    onMoreAllToggle,
    onColumnsChange,
    onColumnOrdersChange,
    onShowLessChange,
    onCreate,
    onDataSourceColorsChange,
    onDownload,
    onModeToggle,
    onFiltersChange,
    onJoinByChange,
    onCenterJoinToggle,
    onFlipToggle,
    onLayoutSwitch,
    onMaximizeToggle,
    onVisibilityMenuClick,
    onVisibilityMenuDoubleClick,
    onShowHiddenToggle,
    onShowMoreToggle,
    onSave,
    onButtonToggle,
    pinned,
    onPinToggle,
    isAbbreviationSource,
    isCreating,
    onReload,
    charts = [],
    onChartToggle,
    chartEnableOverride = [],
    pivots = [],
    onPivotToggle,
    pivotEnableOverride = [],
    absoluteSortOverride = [],
    onAbsoluteSortChange,
    disableCreate = false
}) => {
    const [anchorEl, setAnchorEl] = useState(null);

    const handleColumnToggle = (e, xpath, key, value, ...rest) => {
        const isHidden = value;
        const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
        const updatedColumns = columns.map((o) => o[fieldKey] === key ? { ...o, hide: isHidden } : o);
        const meta = fieldsMetadata.find((o) => o[fieldKey] === key);
        const updatedEnableOverride = cloneDeep(enableOverride);
        const updatedDisableOverride = cloneDeep(disableOverride);
        if (isHidden) {
            if (meta.hide !== isHidden) {
                if (!updatedEnableOverride.includes(key)) {
                    updatedEnableOverride.push(key);
                }
            }
            const idx = updatedDisableOverride.indexOf(key);
            if (idx !== -1) {
                updatedDisableOverride.splice(idx, 1);
            }
        } else {
            if (meta.hide !== undefined && meta.hide !== isHidden) {
                if (!updatedDisableOverride.includes(key)) {
                    updatedDisableOverride.push(key);
                }
            }
            const idx = updatedEnableOverride.indexOf(key);
            if (idx !== -1) {
                updatedEnableOverride.splice(idx, 1);
            }
        }
        if (onColumnsChange) {
            onColumnsChange(updatedEnableOverride, updatedDisableOverride, updatedColumns);
        }
    }

    const handleShowLessToggle = (e, xpath, key, value, ...rest) => {
        const isLess = value;
        const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
        const updatedColumns = columns.map((o) => o[fieldKey] === key ? { ...o, showLess: isLess } : o);
        const meta = fieldsMetadata.find((o) => o[fieldKey] === key);
        const updatedShowLess = cloneDeep(showLess);
        if (isLess) {
            if (meta.showLess !== isLess) {
                if (!updatedShowLess.includes(key)) {
                    updatedShowLess.push(key);
                }
            }
        } else {
            const idx = updatedShowLess.indexOf(key);
            if (idx !== -1) {
                updatedShowLess.splice(idx, 1);
            }
        }
        if (onShowLessChange) {
            onShowLessChange(updatedShowLess, updatedColumns);
        }
    }

    const handleColumnOrdersChange = (xpath, value) => {
        let updatedColumnOrders = cloneDeep(columnOrders || []);
        if (updatedColumnOrders) {
            const columnOrder = updatedColumnOrders.find((o) => o.column_name === xpath);
            if (columnOrder) {
                columnOrder.sequence = value;
            } else {
                updatedColumnOrders.push({ column_name: xpath, sequence: value });
            }
        }
        onColumnOrdersChange(updatedColumnOrders);
    }

    const handleJoinByChange = (e, column) => {
        let updatedJoinBy;
        if (e.target.checked) {
            updatedJoinBy = [...joinBy, column];
        } else {
            updatedJoinBy = joinBy.filter(joinColumn => joinColumn !== column);
        }
        onJoinByChange(updatedJoinBy);
    }

    const handleAbsoluteSortToggle = (e, xpath, key, value, ...rest) => {
        const isAbsoluteSort = !value;
        const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
        const updatedColumns = columns.map((o) => o[fieldKey] === key ? { ...o, absoluteSort: isAbsoluteSort } : o);
        const meta = fieldsMetadata.find((o) => o[fieldKey] === key);
        if (!meta) return;
        const updatedAbsoluteSortOverride = cloneDeep(absoluteSortOverride);
        if (isAbsoluteSort) {
            if (!updatedAbsoluteSortOverride.includes(key)) {
                updatedAbsoluteSortOverride.push(key);
            }
        } else {
            const idx = updatedAbsoluteSortOverride.indexOf(key);
            if (idx !== -1) {
                updatedAbsoluteSortOverride.splice(idx, 1);
            }
        }
        if (onAbsoluteSortChange) {
            onAbsoluteSortChange(updatedAbsoluteSortOverride, updatedColumns);
        }
    }

    const isMenuOpen = Boolean(anchorEl);
    const IconComponent = isMenuOpen ? MenuOpen : MenuIcon;

    const handleMenuOpen = (e) => {
        setAnchorEl(e.currentTarget);
    }

    const handleMenuClose = () => {
        setAnchorEl(null);
    }

    const handlePinToggle = (menuName, checked) => {
        const updatedPinned = cloneDeep(pinned.filter((o) => o !== menuName));
        if (checked) {
            updatedPinned.push(menuName);
        }
        onPinToggle(updatedPinned);
    }

    const menus = [
        'column-settings',
        'chart-settings',
        'pivot-settings',
        'filter',
        'visibility',
        'data-source-color',
        'join',
        'create',
        'download',
        'edit-save',
        'layout-switch',
        'maximize-restore',
        'reload',
    ]

    const renderMenu = (menuName, menuType = 'icon') => {
        const menuKey = `${menuName}_${menuType}`;
        switch (menuName) {
            case 'column-settings':
                return (
                    <ColumnSettingsMenu
                        key={menuKey}
                        columns={columns}
                        columnOrders={columnOrders}
                        // showAll={showAll}
                        // moreAll={moreAll}
                        // onShowAllToggle={onShowAllToggle}
                        // onMoreAllToggle={onMoreAllToggle}
                        onColumnToggle={handleColumnToggle}
                        onColumnOrdersChange={handleColumnOrdersChange}
                        onShowLessToggle={handleShowLessToggle}
                        modelType={modelType}
                        layout={layout}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        onAbsoluteSortToggle={handleAbsoluteSortToggle}
                    />
                );
            case 'filter':
                return (
                    <FilterMenu
                        key={menuKey}
                        filters={filters}
                        fieldsMetadata={fieldsMetadata}
                        menuType={menuType}
                        modelType={modelType}
                        isPinned={pinned.includes(menuName)}
                        onPinToggle={handlePinToggle}
                        onMenuClose={handleMenuClose}
                        onFiltersChange={onFiltersChange}
                    />
                );
            case 'visibility':
                return (
                    <VisibilityMenu
                        key={menuKey}
                        showMore={showMore}
                        showHidden={showHidden}
                        onVisibilityMenuClick={onVisibilityMenuClick}
                        onVisibilityMenuDoubleClick={onVisibilityMenuDoubleClick}
                        onShowHiddenToggle={onShowHiddenToggle}
                        onShowMoreToggle={onShowMoreToggle}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                    />
                );
            case 'data-source-color':
                return (
                    <DataSourceColorMenu
                        key={menuKey}
                        joinBy={joinBy}
                        menuType={menuType}
                        dataSourceColors={dataSourceColors}
                        maxRowSize={maxRowSize}
                        onDataSourceColorsChange={onDataSourceColorsChange}
                        isPinned={pinned.includes(menuName)}
                        onPinToggle={handlePinToggle}
                        onMenuClose={handleMenuClose}
                    />
                );
            case 'join':
                return (
                    <JoinMenu
                        key={menuKey}
                        joinBy={joinBy}
                        centerJoin={centerJoin}
                        flip={flip}
                        fieldsMetadata={fieldsMetadata}
                        onJoinByChange={handleJoinByChange}
                        onCenterJoinToggle={onCenterJoinToggle}
                        onFlipToggle={onFlipToggle}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        modelType={modelType}
                    />
                );
            case 'create':
                return (
                    <CreateMenu
                        key={menuKey}
                        mode={mode}
                        onCreate={onCreate}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        isAbbreviationSource={isAbbreviationSource}
                        disableCreate={disableCreate}
                    />
                );
            case 'download':
                return (
                    <DownloadMenu
                        key={menuKey}
                        onDownload={onDownload}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                    />
                );
            case 'edit-save':
                return (
                    <EditSaveToggleMenu
                        key={menuKey}
                        mode={mode}
                        onModeToggle={onModeToggle}
                        onSave={onSave}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        disabled={isAbbreviationSource && isCreating}
                    />
                );
            case 'layout-switch':
                return (
                    <LayoutSwitchMenu
                        key={menuKey}
                        layout={layout}
                        supportedLayouts={supportedLayouts}
                        onLayoutSwitch={onLayoutSwitch}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                    />
                );
            case 'maximize-restore':
                return (
                    <MaximizeRestoreToggleMenu
                        key={menuKey}
                        isMaximized={isMaximized}
                        onMaximizeToggle={onMaximizeToggle}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                    />
                );
            case 'reload':
                return (
                    <ReloadMenu
                        key={menuKey}
                        onReload={onReload}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                    />
                )
            case 'chart-settings':
                return (
                    <ChartSettingsMenu
                        key={menuKey}
                        charts={charts}
                        showAll={showAll}
                        onShowAllToggle={onShowAllToggle}
                        onChartToggle={onChartToggle}
                        layout={layout}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        chartEnableOverride={chartEnableOverride}
                    />
                );
            case 'pivot-settings':
                return (
                    <PivotSettingsMenu
                        key={menuKey}
                        pivots={pivots}
                        showAll={showAll}
                        onShowAllToggle={onShowAllToggle}
                        onPivotToggle={onPivotToggle}
                        layout={layout}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        pivotEnableOverride={pivotEnableOverride}
                    />
                );
        }
    }

    return (
        <>
            {modelType !== MODEL_TYPES.ABBREVIATION_MERGE && (
                <DynamicMenu
                    fieldsMetadata={fieldsMetadata}
                    commonKeys={commonKeys}
                    onButtonToggle={onButtonToggle}
                />
            )}
            {modelSchema?.button_query?.map((obj, idx) => (
                <ButtonQuery
                    key={idx}
                    url={url}
                    viewUrl={viewUrl}
                    queryObj={obj}
                />
            ))}
            {pinned && pinned.map((menuName) => renderMenu(menuName, 'icon'))}
            <Icon name={'show-all'} title={'show-all'} onClick={handleMenuOpen}>
                <IconComponent fontSize='small' />
            </Icon>
            <Menu
                anchorEl={anchorEl}
                open={isMenuOpen}
                onClose={handleMenuClose}
                disableRestoreFocus
            >
                {menus.map((menuName) => renderMenu(menuName, 'item'))}
            </Menu>
        </>
    )
}

export default MenuGroup;