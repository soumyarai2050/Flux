import { getWidgetOptionById } from '../utils';

export function rowsPerPageChangeHandler(config, updatedRowsPerPage) {
  const layoutDataUpdateDict = { rows_per_page: updatedRowsPerPage };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function columnOrdersChangeHandler(config, updatedColumnOrders) {
  const layoutDataUpdateDict = { column_orders: updatedColumnOrders };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function sortOrdersChangeHandler(config, updatedSortOrders) {
  const layoutDataUpdateDict = { sort_orders: updatedSortOrders };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function showLessChangeHandler(config, updatedShowLess) {
  const layoutDataUpdateDict = { show_less: updatedShowLess };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function pinnedChangeHandler(config, updatedPinned) {
  const layoutDataUpdateDict = { pinned: updatedPinned };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function dataSourceColorsChangeHandler(config, updatedDataSourceColors) {
  const layoutDataUpdateDict = { data_source_colors: updatedDataSourceColors };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function overrideChangeHandler(config, updatedEnableOverride, updatedDisableOverride) {
  const layoutDataUpdateDict = { enable_override: updatedEnableOverride, disable_override: updatedDisableOverride };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function joinByChangeHandler(config, updatedJoinBy) {
  const layoutDataUpdateDict = { join_by: updatedJoinBy };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function layoutTypeChangeHandler(config, updatedLayoutType, layoutTypeKey) {
  const layoutDataUpdateDict = { [layoutTypeKey]: updatedLayoutType };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function centerJoinToggleHandler(config, updatedCenterJoin) {
  const layoutDataUpdateDict = { joined_at_center: updatedCenterJoin };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

export function flipToggleHandler(config, updatedFlip) {
  const layoutDataUpdateDict = { flip: updatedFlip };
  layoutDataChangeHandler(config, layoutDataUpdateDict);
}

function layoutDataChangeHandler(config, layoutDataUpdateDict) {
  const { layoutOption, modelName, dispatch, objId, onLayoutChangeCallback } = config;
  const layoutData = getWidgetOptionById(layoutOption.widget_ui_data, objId, layoutOption.bind_id_fld);
  const updatedLayoutData = { ...layoutData, ...layoutDataUpdateDict };
  dispatch(onLayoutChangeCallback({ name: modelName, data: updatedLayoutData }));
}