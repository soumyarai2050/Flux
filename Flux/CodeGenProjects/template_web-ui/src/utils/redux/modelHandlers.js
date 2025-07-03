import { getWidgetOptionById } from '../ui/uiUtils';

/**
 * @function rowsPerPageChangeHandler
 * @description Handles changes to the 'rows per page' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {number} updatedRowsPerPage - The new value for rows per page.
 */
export function rowsPerPageChangeHandler(config, updatedRowsPerPage) {
  const layoutDataUpdateDict = { rows_per_page: updatedRowsPerPage };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function columnOrdersChangeHandler
 * @description Handles changes to the 'column orders' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedColumnOrders - The new array of column order objects.
 */
export function columnOrdersChangeHandler(config, updatedColumnOrders) {
  const layoutDataUpdateDict = { column_orders: updatedColumnOrders };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function sortOrdersChangeHandler
 * @description Handles changes to the 'sort orders' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedSortOrders - The new array of sort order objects.
 */
export function sortOrdersChangeHandler(config, updatedSortOrders) {
  const layoutDataUpdateDict = { sort_orders: updatedSortOrders };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function showLessChangeHandler
 * @description Handles changes to the 'show less' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedShowLess - The new array of fields to show less for.
 */
export function showLessChangeHandler(config, updatedShowLess) {
  const layoutDataUpdateDict = { show_less: updatedShowLess };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function pinnedChangeHandler
 * @description Handles changes to the 'pinned' menus setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedPinned - The new array of pinned menu names.
 */
export function pinnedChangeHandler(config, updatedPinned) {
  const layoutDataUpdateDict = { pinned: updatedPinned };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function dataSourceColorsChangeHandler
 * @description Handles changes to the 'data source colors' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedDataSourceColors - The new array of data source color strings.
 */
export function dataSourceColorsChangeHandler(config, updatedDataSourceColors) {
  const layoutDataUpdateDict = { data_source_colors: updatedDataSourceColors };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function overrideChangeHandler
 * @description Handles changes to the 'enable/disable override' settings for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedEnableOverride - The new array of enabled override fields.
 * @param {Array<string>} updatedDisableOverride - The new array of disabled override fields.
 */
export function overrideChangeHandler(config, updatedEnableOverride, updatedDisableOverride) {
  const layoutDataUpdateDict = { enable_override: updatedEnableOverride, disable_override: updatedDisableOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function joinByChangeHandler
 * @description Handles changes to the 'join by' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedJoinBy - The new array of fields to join by.
 */
export function joinByChangeHandler(config, updatedJoinBy) {
  const layoutDataUpdateDict = { join_by: updatedJoinBy };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function layoutTypeChangeHandler
 * @description Handles changes to the 'layout type' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {string} updatedLayoutType - The new layout type.
 * @param {string} layoutTypeKey - The key for the layout type (e.g., 'view_layout' or 'edit_layout').
 */
export function layoutTypeChangeHandler(config, updatedLayoutType, layoutTypeKey) {
  const layoutDataUpdateDict = { [layoutTypeKey]: updatedLayoutType };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function centerJoinToggleHandler
 * @description Handles toggling the 'joined at center' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {boolean} updatedCenterJoin - The new boolean value for 'joined at center'.
 */
export function centerJoinToggleHandler(config, updatedCenterJoin) {
  const layoutDataUpdateDict = { joined_at_center: updatedCenterJoin };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function flipToggleHandler
 * @description Handles toggling the 'flip' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {boolean} updatedFlip - The new boolean value for 'flip'.
 */
export function flipToggleHandler(config, updatedFlip) {
  const layoutDataUpdateDict = { flip: updatedFlip };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function selectedChartNameChangeHandler
 * @description Handles changes to the 'selected chart name' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {string} updatedChartName - The new selected chart name.
 */
export function selectedChartNameChangeHandler(config, updatedChartName) {
  const layoutDataUpdateDict = { selected_chart_name: updatedChartName };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function chartEnableOverrideChangeHandler
 * @description Handles changes to the 'chart enable override' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedChartEnableOverride - The new array of chart enable override fields.
 */
export function chartEnableOverrideChangeHandler(config, updatedChartEnableOverride) {
  const layoutDataUpdateDict = { chart_enable_override: updatedChartEnableOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function selectedPivotNameChangeHandler
 * @description Handles changes to the 'selected pivot name' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {string} updatedPivotName - The new selected pivot name.
 */
export function selectedPivotNameChangeHandler(config, updatedPivotName) {
  const layoutDataUpdateDict = { selected_pivot_name: updatedPivotName };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function pivotEnableOverrideChangeHandler
 * @description Handles changes to the 'pivot enable override' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedPivotEnableOverride - The new array of pivot enable override fields.
 */
export function pivotEnableOverrideChangeHandler(config, updatedPivotEnableOverride) {
  const layoutDataUpdateDict = { pivot_enable_override: updatedPivotEnableOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function quickFiltersChangeHandler
 * @description Handles changes to the 'quick filters' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedQuickFilters - The new array of quick filter objects.
 */
export function quickFiltersChangeHandler(config, updatedQuickFilters) {
  const layoutDataUpdateDict = { quick_filters: updatedQuickFilters };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function stickyHeaderToggleHandler
 * @description Handles toggling the 'sticky header' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {boolean} updatedStickyHeader - The new boolean value for 'sticky header'.
 */
export function stickyHeaderToggleHandler(config, updatedStickyHeader) {
  const layoutDataUpdateDict = { sticky_header: updatedStickyHeader };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function commonKeyCollapseToggleHandler
 * @description Handles toggling the 'common key collapse' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {boolean} updatedCollapse - The new boolean value for 'common key collapse'.
 */
export function commonKeyCollapseToggleHandler(config, updatedCollapse) {
  const layoutDataUpdateDict = { common_key_collapse: updatedCollapse };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function frozenColumnsChangeHandler
 * @description Handles changes to the 'frozen columns' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedFrozenColumns - The new array of frozen column names.
 */
export function frozenColumnsChangeHandler(config, updatedFrozenColumns) {
  const layoutDataUpdateDict = { frozen_columns: updatedFrozenColumns };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function columnNameOverrideHandler
 * @description Handles changes to the 'column name override' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedColumnNameOverride - The new array of column name override strings.
 */
export function columnNameOverrideHandler(config, updatedColumnNameOverride) {
  const layoutDataUpdateDict = { column_name_override: updatedColumnNameOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function highlightUpdateOverrideHandler
 * @description Handles changes to the 'highlight update override' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedHighlightUpdateOverride - The new array of highlight update override strings.
 */
export function highlightUpdateOverrideHandler(config, updatedHighlightUpdateOverride) {
  const layoutDataUpdateDict = { highlight_update_override: updatedHighlightUpdateOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function highlightDurationChangeHandler
 * @description Handles changes to the 'highlight duration' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {number} updatedHighlightDuration - The new highlight duration in milliseconds.
 */
export function highlightDurationChangeHandler(config, updatedHighlightDuration) {
  const layoutDataUpdateDict = { highlight_duration: updatedHighlightDuration };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function noCommonKeyOverrideChangeHandler
 * @description Handles changes to the 'no common key override' setting for a model's layout.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<string>} updatedNoCommonKeyOverride - The new array of no common key override strings.
 */
export function noCommonKeyOverrideChangeHandler(config, updatedNoCommonKeyOverride) {
  const layoutDataUpdateDict = { no_common_key_override: updatedNoCommonKeyOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

/**
 * @function joinSortChangeHandler
 * @description Handles changes to the 'join sort' setting for a model's layout option.
 * @param {object} config - The configuration object for the model handler.
 * @param {object} updatedJoinSort - The new join sort object.
 */
export function joinSortChangeHandler(config, updatedJoinSort) {
  const layoutOptionUpdateDict = { join_sort: updatedJoinSort };
  layoutOptionChangeHandler(config, layoutOptionUpdateDict);
}

/**
 * @function filtersChangeHandler
 * @description Handles changes to the 'filters' setting for a model's layout option.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedFilters - The new array of filter objects.
 */
export function filtersChangeHandler(config, updatedFilters) {
  const layoutOptionUpdateDict = { filters: updatedFilters };
  layoutOptionChangeHandler(config, layoutOptionUpdateDict);
}

/**
 * @function chartDataChangeHandler
 * @description Handles changes to the 'chart data' setting for a model's layout option.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedChartData - The new array of chart data objects.
 */
export function chartDataChangeHandler(config, updatedChartData) {
  const layoutOptionUpdateDict = { chart_data: updatedChartData };
  layoutOptionChangeHandler(config, layoutOptionUpdateDict);
}

/**
 * @function pivotDataChangeHandler
 * @description Handles changes to the 'pivot data' setting for a model's layout option.
 * @param {object} config - The configuration object for the model handler.
 * @param {Array<object>} updatedPivotData - The new array of pivot data objects.
 */
export function pivotDataChangeHandler(config, updatedPivotData) {
  const layoutOptionUpdateDict = { pivot_data: updatedPivotData };
  layoutOptionChangeHandler(config, layoutOptionUpdateDict);
}

/**
 * @function layoutDataChangeHandler
 * @description Dispatches an action to update the layout data for a specific model.
 * @param {object} config - The configuration object for the model handler.
 * @param {object} layoutDataUpdateDict - A dictionary containing the layout data properties to update.
 */
function layoutDataChangeHandler(config, layoutDataUpdateDict) {
  const { layoutOption, modelName, dispatch, objId, onLayoutChangeCallback } = config;
  const layoutData = getWidgetOptionById(layoutOption.widget_ui_data, objId, layoutOption.bind_id_fld);
  const updatedLayoutData = { ...layoutData, ...layoutDataUpdateDict };
  dispatch(onLayoutChangeCallback({ name: modelName, data: updatedLayoutData, type: 'data' }));
}

/**
 * @function layoutOptionChangeHandler
 * @description Dispatches an action to update the layout option for a specific model.
 * @param {object} config - The configuration object for the model handler.
 * @param {object} layoutOptionUpdateDict - A dictionary containing the layout option properties to update.
 */
function layoutOptionChangeHandler(config, layoutOptionUpdateDict) {
  const { layoutOption, modelName, dispatch, onLayoutChangeCallback } = config;
  const updatedLayoutOption = { ...layoutOption, ...layoutOptionUpdateDict };
  dispatch(onLayoutChangeCallback({ name: modelName, data: updatedLayoutOption, type: 'option' }));
}