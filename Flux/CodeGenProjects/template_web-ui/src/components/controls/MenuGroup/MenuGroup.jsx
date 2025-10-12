/**
 * @module MenuGroup
 * @description This module provides a comprehensive menu group component that dynamically renders various sub-menus and buttons based on provided configurations and data.
 */

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
    ChartSettingsMenu, TableSettingsMenu, CreateMenu, DataSourceColorMenu, DownloadMenu, DynamicMenu,
    EditSaveToggleMenu, FilterMenu, JoinMenu, LayoutSwitchMenu, MaximizeRestoreToggleMenu, PivotSettingsMenu, ReloadMenu, VisibilityMenu
} from '../menus';
import { MODEL_TYPES } from '../../../constants';
import { cloneDeep } from 'lodash';
import { Menu } from '@mui/material';
import Icon from '../../ui/Icon';
import { MenuOpen, Menu as MenuIcon } from '@mui/icons-material';
import ButtonQuery from '../../ui/ButtonQuery';

/**
 * @function MenuGroup
 * @description A component that groups and renders various interactive menus and buttons for data manipulation and display.
 * @param {object} props - The properties for the component.
 * @param {Array<object>} props.columns - Configuration for table columns.
 * @param {Array<object>} props.columnOrders - User-defined column order preferences.
 * @param {boolean} props.showAll - State for showing all columns.
 * @param {boolean} props.moreAll - State for showing more details.
 * @param {string} props.mode - Current application mode (e.g., 'read', 'edit').
 * @param {Array<string>} props.joinBy - Columns used for joining data.
 * @param {number} props.maxRowSize - Maximum number of rows to display.
 * @param {Array} props.dataSourceColors - Colors associated with different data sources.
 * @param {Array<object>} props.fieldsMetadata - Metadata for all fields.
 * @param {Array<object>} props.filters - Active filters.
 * @param {boolean} props.centerJoin - State for center join.
 * @param {boolean} props.flip - State for flipping data.
 * @param {string} props.layout - Current layout type.
 * @param {Array<string>} props.supportedLayouts - List of supported layouts.
 * @param {boolean} props.isMaximized - State for maximized view.
 * @param {boolean} props.showMore - State for showing more content.
 * @param {boolean} props.showHidden - State for showing hidden content.
 * @param {string} props.modelType - Type of the current model.
 * @param {Array<string>} props.enableOverride - List of columns to force enable.
 * @param {Array<string>} props.disableOverride - List of columns to force disable.
 * @param {Array<string>} props.showLess - List of columns to show less detail for.
 * @param {Array<object>} props.commonKeys - Common keys data.
 * @param {object} props.modelSchema - The schema for the current model.
 * @param {string} props.url - Base URL for API calls.
 * @param {string} props.viewUrl - Base URL for view-related API calls.
 * @param {function} props.onShowAllToggle - Callback for toggling show all.
 * @param {function} props.onMoreAllToggle - Callback for toggling more all.
 * @param {function} props.onColumnsChange - Callback for column visibility changes.
 * @param {function} props.onColumnOrdersChange - Callback for column order changes.
 * @param {function} props.onShowLessChange - Callback for show less changes.
 * @param {function} props.onCreate - Callback for create action.
 * @param {function} props.onDataSourceColorsChange - Callback for data source color changes.
 * @param {function} props.onDownload - Callback for download action.
 * @param {function} props.onModeToggle - Callback for mode toggle.
 * @param {function} props.onFiltersChange - Callback for filter changes.
 * @param {function} props.onJoinByChange - Callback for join by changes.
 * @param {function} props.onCenterJoinToggle - Callback for center join toggle.
 * @param {function} props.onFlipToggle - Callback for flip toggle.
 * @param {function} props.onLayoutSwitch - Callback for layout switch.
 * @param {function} props.onMaximizeToggle - Callback for maximize toggle.
 * @param {function} props.onVisibilityMenuClick - Callback for visibility menu click.
 * @param {function} props.onVisibilityMenuDoubleClick - Callback for visibility menu double click.
 * @param {function} props.onShowHiddenToggle - Callback for show hidden toggle.
 * @param {function} props.onShowMoreToggle - Callback for show more toggle.
 * @param {function} props.onSave - Callback for save action.
 * @param {function} props.onButtonToggle - Callback for button toggle.
 * @param {Array<string>} props.pinned - List of pinned menus.
 * @param {function} props.onPinToggle - Callback for pin toggle.
 * @param {boolean} props.isAbbreviationSource - Indicates if it's an abbreviation source.
 * @param {boolean} props.isCreating - Indicates if an item is being created.
 * @param {function} props.onReload - Callback for reload action.
 * @param {Array<object>} props.charts - Chart configurations.
 * @param {function} props.onChartToggle - Callback for chart toggle.
 * @param {Array<string>} props.chartEnableOverride - Chart enable override list.
 * @param {Array<object>} props.pivots - Pivot configurations.
 * @param {function} props.onPivotToggle - Callback for pivot toggle.
 * @param {Array<string>} props.pivotEnableOverride - Pivot enable override list.
 * @param {boolean} [props.disableCreate=false] - If true, disables the create menu.
 * @param {boolean} [props.commonKeyCollapse=false] - State for common key collapse.
 * @param {function} props.onCommonKeyCollapseToggle - Callback for common key collapse toggle.
 * @param {boolean} [props.stickyHeader=true] - State for sticky header.
 * @param {function} props.onStickyHeaderToggle - Callback for sticky header toggle.
 * @param {Array<string>} props.frozenColumns - List of frozen columns.
 * @param {function} props.onFrozenColumnsChange - Callback for frozen columns change.
 * @param {Array<object>} props.columnNameOverride - Column name override list.
 * @param {function} props.onColumnNameOverrideChange - Callback for column name override change.
 * @param {Array<object>} props.highlightUpdateOverride - Highlight update override list.
 * @param {function} props.onHighlightUpdateOverrideChange - Callback for highlight update override change.
 * @param {Array<object>} props.sortOrders - Sort orders.
 * @param {function} props.onSortOrdersChange - Callback for sort orders change.
 * @param {Array<object>} props.groupedRows - Grouped rows data.
 * @param {number} props.highlightDuration - Duration for highlight animation.
 * @param {function} props.onHighlightDurationChange - Callback for highlight duration change.
 * @param {Array<string>} props.noCommonKeyOverride - No common key override list.
 * @param {function} props.onNoCommonKeyOverrideChange - Callback for no common key override change.
 * @param {function} props.onDiscard - Callback for discard action.
 * @param {Object} [props.autoBoundParams={}] - Auto-bound query parameters from field values with FluxFldQueryParamBind.
 * @returns {React.ReactElement} The rendered MenuGroup component.
 */
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
    isAbbreviationSource = false,
    isCreating = false,
    onReload,
    onDiscard,
    charts = [],
    onChartToggle,
    chartEnableOverride = [],
    pivots = [],
    onPivotToggle,
    pivotEnableOverride = [],
    disableCreate = false,
    commonKeyCollapse = false,
    onCommonKeyCollapseToggle,
    stickyHeader = true,
    onStickyHeaderToggle,
    frozenColumns = [],
    onFrozenColumnsChange,
    uniqueValues = {},
    columnNameOverride = [],
    onColumnNameOverrideChange,
    highlightUpdateOverride = [],
    onHighlightUpdateOverrideChange,
    sortOrders = [],
    onSortOrdersChange,
    groupedRows = [],
    highlightDuration,
    onHighlightDurationChange,
    noCommonKeyOverride,
    onNoCommonKeyOverrideChange,
    autoBoundParams = {},
    isReadOnly = false
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
    };

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
    };

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
    };

    const handleJoinByChange = (e, column) => {
        let updatedJoinBy;
        if (e.target.checked) {
            updatedJoinBy = [...joinBy, column];
        } else {
            updatedJoinBy = joinBy.filter(joinColumn => joinColumn !== column);
        }
        onJoinByChange(updatedJoinBy);
    };

    const handleFrozenToggle = (e, xpath, key, value, ...rest) => {
        const isFrozen = !value;
        const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
        const updatedColumns = columns.map((o) => o[fieldKey] === key ? { ...o, frozenColumn: isFrozen } : o);
        const meta = fieldsMetadata.find((o) => o[fieldKey] === key);
        if (!meta) return;
        const updatedFrozenColumns = cloneDeep(frozenColumns);
        if (isFrozen) {
            if (!updatedFrozenColumns.includes(key)) {
                updatedFrozenColumns.push(key);
            }
        } else {
            const idx = updatedFrozenColumns.indexOf(key);
            if (idx !== -1) {
                updatedFrozenColumns.splice(idx, 1);
            }
        }
        if (onFrozenColumnsChange) {
            onFrozenColumnsChange(updatedFrozenColumns, updatedColumns);
        }
    };

    const handleNoCommonKeyToggle = (e, xpath, key, value, ...rest) => {
        const isNoCommonKey = !value;
        const fieldKey = modelType === MODEL_TYPES.ABBREVIATION_MERGE ? 'key' : 'tableTitle';
        const updatedColumns = columns.map((o) => o[fieldKey] === key ? { ...o, noCommonKeyDeduced: isNoCommonKey } : o);
        const meta = fieldsMetadata.find((o) => o[fieldKey] === key);
        if (!meta) return;
        const updatedNoCommonKeyOverride = cloneDeep(noCommonKeyOverride);
        const idx = updatedNoCommonKeyOverride.indexOf(key);
        if (idx !== -1) {
            updatedNoCommonKeyOverride.splice(idx, 1);
        } else {
            updatedNoCommonKeyOverride.push(key);
        }
        if (onNoCommonKeyOverrideChange) {
            onNoCommonKeyOverrideChange(updatedNoCommonKeyOverride, updatedColumns);
        }
    };

    const isMenuOpen = Boolean(anchorEl);
    const IconComponent = isMenuOpen ? MenuOpen : MenuIcon;

    const handleMenuOpen = (e) => {
        setAnchorEl(e.currentTarget);
    };

    const handleMenuClose = () => {
        setAnchorEl(null);
    };

    const handlePinToggle = (menuName, checked) => {
        const updatedPinned = cloneDeep(pinned.filter((o) => o !== menuName));
        if (checked) {
            updatedPinned.push(menuName);
        }
        onPinToggle(updatedPinned);
    };

    const menus = [
        'table-settings',
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
    ];

    const renderMenu = (menuName, menuType = 'icon') => {
        const menuKey = `${menuName}_${menuType}`;
        switch (menuName) {
            case 'table-settings':
                return (
                    <TableSettingsMenu
                        key={menuKey}
                        columns={columns}
                        columnOrders={columnOrders}
                        onColumnToggle={handleColumnToggle}
                        onColumnOrdersChange={handleColumnOrdersChange}
                        onShowLessToggle={handleShowLessToggle}
                        modelType={modelType}
                        layout={layout}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        commonKeyCollapse={commonKeyCollapse}
                        onCommonKeyCollapseToggle={onCommonKeyCollapseToggle}
                        stickyHeader={stickyHeader}
                        onStickyHeaderToggle={onStickyHeaderToggle}
                        onFrozenToggle={handleFrozenToggle}
                        columnNameOverride={columnNameOverride}
                        onColumnNameOverrideChange={onColumnNameOverrideChange}
                        highlightUpdateOverride={highlightUpdateOverride}
                        onHighlightUpdateOverrideChange={onHighlightUpdateOverrideChange}
                        highlightDuration={highlightDuration}
                        onHighlightDurationChange={onHighlightDurationChange}
                        onNoCommonKeyToggle={handleNoCommonKeyToggle}
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
                        uniqueValues={uniqueValues}
                        sortOrders={sortOrders}
                        onSortOrdersChange={onSortOrdersChange}
                        groupedRows={groupedRows}
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
                        disableCreate={isReadOnly || disableCreate}
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
                        onDiscard={onDiscard}
                        menuType={menuType}
                        isPinned={pinned.includes(menuName)}
                        onMenuClose={handleMenuClose}
                        onPinToggle={handlePinToggle}
                        disabled={isReadOnly || (isAbbreviationSource && isCreating)}
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
                );
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
            default:
                return null;
        }
    };

    return (
        <>
            <div aria-label='dynamic-n-button-query-menu' style={{ overflow: 'auto', whiteSpace: 'nowrap' }}>
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
                        autoBoundParams={autoBoundParams}
                    />
                ))}
            </div>
            {pinned && pinned.map((menuName) => renderMenu(menuName, 'icon'))}
            <Icon name={'show-all'} title={'show-all'} onClick={handleMenuOpen}>
                <IconComponent fontSize='small' color='white' />
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
    );
};

MenuGroup.propTypes = {
    columns: PropTypes.array.isRequired,
    columnOrders: PropTypes.array.isRequired,
    showAll: PropTypes.bool.isRequired,
    moreAll: PropTypes.bool.isRequired,
    mode: PropTypes.string.isRequired,
    joinBy: PropTypes.array.isRequired,
    maxRowSize: PropTypes.number.isRequired,
    dataSourceColors: PropTypes.array.isRequired,
    fieldsMetadata: PropTypes.array.isRequired,
    filters: PropTypes.array.isRequired,
    centerJoin: PropTypes.bool.isRequired,
    flip: PropTypes.bool.isRequired,
    layout: PropTypes.string.isRequired,
    supportedLayouts: PropTypes.array.isRequired,
    isMaximized: PropTypes.bool.isRequired,
    showMore: PropTypes.bool.isRequired,
    showHidden: PropTypes.bool.isRequired,
    modelType: PropTypes.string.isRequired,
    enableOverride: PropTypes.array.isRequired,
    disableOverride: PropTypes.array.isRequired,
    showLess: PropTypes.array.isRequired,
    commonKeys: PropTypes.array.isRequired,
    modelSchema: PropTypes.object,
    url: PropTypes.string,
    viewUrl: PropTypes.string,
    onShowAllToggle: PropTypes.func.isRequired,
    onMoreAllToggle: PropTypes.func.isRequired,
    onColumnsChange: PropTypes.func.isRequired,
    onColumnOrdersChange: PropTypes.func.isRequired,
    onShowLessChange: PropTypes.func.isRequired,
    onCreate: PropTypes.func.isRequired,
    onDataSourceColorsChange: PropTypes.func.isRequired,
    onDownload: PropTypes.func.isRequired,
    onModeToggle: PropTypes.func.isRequired,
    onFiltersChange: PropTypes.func.isRequired,
    onJoinByChange: PropTypes.func.isRequired,
    onCenterJoinToggle: PropTypes.func.isRequired,
    onFlipToggle: PropTypes.func.isRequired,
    onLayoutSwitch: PropTypes.func.isRequired,
    onMaximizeToggle: PropTypes.func.isRequired,
    onVisibilityMenuClick: PropTypes.func.isRequired,
    onVisibilityMenuDoubleClick: PropTypes.func.isRequired,
    onShowHiddenToggle: PropTypes.func.isRequired,
    onShowMoreToggle: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    onButtonToggle: PropTypes.func.isRequired,
    pinned: PropTypes.array.isRequired,
    onPinToggle: PropTypes.func.isRequired,
    isAbbreviationSource: PropTypes.bool,
    isCreating: PropTypes.bool,
    onReload: PropTypes.func.isRequired,
    onDiscard: PropTypes.func,
    charts: PropTypes.array,
    onChartToggle: PropTypes.func,
    chartEnableOverride: PropTypes.array,
    pivots: PropTypes.array,
    onPivotToggle: PropTypes.func,
    pivotEnableOverride: PropTypes.array,
    disableCreate: PropTypes.bool,
    commonKeyCollapse: PropTypes.bool,
    onCommonKeyCollapseToggle: PropTypes.func,
    stickyHeader: PropTypes.bool,
    onStickyHeaderToggle: PropTypes.func,
    frozenColumns: PropTypes.array,
    onFrozenColumnsChange: PropTypes.func,
    uniqueValues: PropTypes.object,
    columnNameOverride: PropTypes.array,
    onColumnNameOverrideChange: PropTypes.func,
    highlightUpdateOverride: PropTypes.array,
    onHighlightUpdateOverrideChange: PropTypes.func,
    sortOrders: PropTypes.array,
    onSortOrdersChange: PropTypes.func,
    groupedRows: PropTypes.array,
    highlightDuration: PropTypes.number,
    onHighlightDurationChange: PropTypes.func,
    noCommonKeyOverride: PropTypes.array,
    onNoCommonKeyOverrideChange: PropTypes.func,
    autoBoundParams: PropTypes.object,
    isReadOnly: PropTypes.bool,
};

export default MenuGroup;