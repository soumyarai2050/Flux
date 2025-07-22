import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import * as Selectors from '../selectors';
import { getWidgetOptionById } from '../utils/ui/uiUtils';
import { actions as LayoutActions } from '../features/uiLayoutSlice';
import {
    sortOrdersChangeHandler,
    rowsPerPageChangeHandler,
    layoutTypeChangeHandler,
    columnOrdersChangeHandler,
    showLessChangeHandler,
    overrideChangeHandler,
    pinnedChangeHandler,
    filtersChangeHandler,
    stickyHeaderToggleHandler,
    commonKeyCollapseToggleHandler,
    frozenColumnsChangeHandler,
    columnNameOverrideHandler,
    highlightUpdateOverrideHandler,
    highlightDurationChangeHandler,
    noCommonKeyOverrideChangeHandler,
    dataSourceColorsChangeHandler,
    joinByChangeHandler,
    centerJoinToggleHandler,
    flipToggleHandler,
    chartDataChangeHandler,
    selectedChartNameChangeHandler,
    chartEnableOverrideChangeHandler,
    selectedPivotNameChangeHandler,
    pivotEnableOverrideChangeHandler,
    pivotDataChangeHandler,
    quickFiltersChangeHandler
} from '../utils/redux/modelHandlers';
import { LAYOUT_TYPES, MODEL_TYPES, MODES } from '../constants';

function getDefaultViewLayout(layoutData, modelType) {
    return layoutData.view_layout ?? (
        modelType === MODEL_TYPES.ABBREVIATION_MERGE
            ? LAYOUT_TYPES.ABBREVIATION_MERGE
            : LAYOUT_TYPES.TABLE
    );
}

const useModelLayout = (modelName, objId, modelType, onColumnsChange, mode) => {
    const dispatch = useDispatch();

    const modelLayoutOption = useSelector((state) => Selectors.selectModelLayout(state, modelName), (prev, curr) => {
        return JSON.stringify(prev) === JSON.stringify(curr);
    });

    const modelLayoutData = useMemo(() => getWidgetOptionById(modelLayoutOption.widget_ui_data, objId, modelLayoutOption.bind_id_fld), [modelLayoutOption, objId]);

    const [isMaximized, setIsMaximized] = useState(false);
    const [page, setPage] = useState(0);
    const [showHidden, setShowHidden] = useState(false);
    const [showMore, setShowMore] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const [moreAll, setMoreAll] = useState(false);
    const [layoutType, setLayoutType] = useState(getDefaultViewLayout(modelLayoutData, modelType));
    const modelHandlerConfigRef = useRef();
    modelHandlerConfigRef.current = {
        modelName,
        modelType,
        dispatch,
        objId,
        layoutOption: modelLayoutOption,
        onLayoutChangeCallback: LayoutActions.setStoredObjByName,
        layoutData: modelLayoutData,
        mode
    }

    useEffect(() => {
        const viewLayout = getDefaultViewLayout(modelLayoutData, modelType);
        const editLayout = modelLayoutData.edit_layout ?? viewLayout;
        setLayoutType(mode === MODES.READ ? viewLayout : editLayout);
    }, [mode, modelLayoutData.view_layout, modelLayoutData.edit_layout])

    const handleFullScreenToggle = useCallback(() => {
        setIsMaximized((prev) => !prev);
    }, []);

    const handlePageChange = useCallback((updatedPage) => {
        setPage(updatedPage);
    }, []);

    const handleRowsPerPageChange = useCallback((updatedRowsPerPage) => {
        rowsPerPageChangeHandler(modelHandlerConfigRef.current, updatedRowsPerPage);
    }, []);

    const handleColumnOrdersChange = useCallback((updatedColumnOrders) => {
        columnOrdersChangeHandler(modelHandlerConfigRef.current, updatedColumnOrders);
    }, []);

    const handleSortOrdersChange = useCallback((updatedSortOrders) => {
        setPage(0);
        sortOrdersChangeHandler(modelHandlerConfigRef.current, updatedSortOrders);
    }, []);

    const handleShowLessChange = useCallback((updatedShowLess, updatedColumns) => {
        onColumnsChange(updatedColumns);
        showLessChangeHandler(modelHandlerConfigRef.current, updatedShowLess);
    }, []);

    const handlePinnedChange = useCallback((updatedPinned) => {
        pinnedChangeHandler(modelHandlerConfigRef.current, updatedPinned);
    }, []);

    const handleOverrideChange = useCallback((updatedEnableOverride, updatedDisableOverride, updatedColumns) => {
        onColumnsChange(updatedColumns);
        overrideChangeHandler(modelHandlerConfigRef.current, updatedEnableOverride, updatedDisableOverride);
    }, []);

    const handleLayoutTypeChange = useCallback((updatedLayoutType, mode = null) => {
        if (!mode) {
            mode = modelHandlerConfigRef.current.mode;
        }
        const layoutTypeKey = mode === MODES.READ ? 'view_layout' : 'edit_layout';
        layoutTypeChangeHandler(modelHandlerConfigRef.current, updatedLayoutType, layoutTypeKey);
        setLayoutType(updatedLayoutType);
    }, []);

    const handleFiltersChange = useCallback((updatedFilters) => {
        filtersChangeHandler(modelHandlerConfigRef.current, updatedFilters);
    }, []);

    const handleStickyHeaderToggle = useCallback(() => {
        stickyHeaderToggleHandler(modelHandlerConfigRef.current, !modelHandlerConfigRef.current.layoutData.sticky_header);
    }, []);

    const handleCommonKeyCollapseToggle = useCallback(() => {
        commonKeyCollapseToggleHandler(modelHandlerConfigRef.current, !modelHandlerConfigRef.current.layoutData.common_key_collapse);
    }, []);

    const handleFrozenColumnsChange = useCallback((updatedFrozenColumns, updatedColumns) => {
        onColumnsChange(updatedColumns);
        frozenColumnsChangeHandler(modelHandlerConfigRef.current, updatedFrozenColumns);
    }, []);

    const handleColumnNameOverrideChange = useCallback((updatedColumnNameOverride) => {
        columnNameOverrideHandler(modelHandlerConfigRef.current, updatedColumnNameOverride);
    }, []);

    const handleHighlightUpdateOverrideChange = useCallback((updatedHighlightUpdateOverride) => {
        highlightUpdateOverrideHandler(modelHandlerConfigRef.current, updatedHighlightUpdateOverride);
    }, []);

    const handleHighlightDurationChange = useCallback((updatedHighlightDuration) => {
        highlightDurationChangeHandler(modelHandlerConfigRef.current, updatedHighlightDuration);
    }, []);

    const handleNoCommonKeyOverrideChange = useCallback((updatedNoCommonKeyOverride, updatedColumns) => {
        onColumnsChange(updatedColumns);
        noCommonKeyOverrideChangeHandler(modelHandlerConfigRef.current, updatedNoCommonKeyOverride);
    }, []);

    const handleDataSourceColorsChange = useCallback((updatedDataSourceColors) => {
        dataSourceColorsChangeHandler(modelHandlerConfigRef.current, updatedDataSourceColors);
    }, []);

    const handleJoinByChange = useCallback((updatedJoinBy) => {
        joinByChangeHandler(modelHandlerConfigRef.current, updatedJoinBy);
    }, []);

    const handleCenterJoinToggle = useCallback(() => {
        centerJoinToggleHandler(modelHandlerConfigRef.current, !modelHandlerConfigRef.current.layoutData.joined_at_center);
    }, []);

    const handleFlipToggle = useCallback(() => {
        flipToggleHandler(modelHandlerConfigRef.current, !modelHandlerConfigRef.current.layoutData.flip);
    }, []);

    const handleSelectedChartNameChange = useCallback((updatedChartName) => {
        selectedChartNameChangeHandler(modelHandlerConfigRef.current, updatedChartName);
    }, []);

    const handleChartEnableOverrideChange = useCallback((updatedChartEnableOverride) => {
        chartEnableOverrideChangeHandler(modelHandlerConfigRef.current, updatedChartEnableOverride);
    }, []);

    const handleChartDataChange = useCallback((updatedChartData) => {
        chartDataChangeHandler(modelHandlerConfigRef.current, updatedChartData);
    }, []);

    const handleSelectedPivotNameChange = useCallback((updatedPivotName) => {
        selectedPivotNameChangeHandler(modelHandlerConfigRef.current, updatedPivotName);
    }, []);

    const handlePivotEnableOverrideChange = useCallback((updatedPivotEnableOverride) => {
        pivotEnableOverrideChangeHandler(modelHandlerConfigRef.current, updatedPivotEnableOverride);
    }, []);

    const handlePivotDataChange = useCallback((updatedPivotData) => {
        pivotDataChangeHandler(modelHandlerConfigRef.current, updatedPivotData);
    }, []);

    const handleQuickFiltersChange = useCallback((updatedQuickFilters) => {
        quickFiltersChangeHandler(modelHandlerConfigRef.current, updatedQuickFilters);
    }, []);

    const handleVisibilityMenuClick = useCallback((isChecked) => {
        if (isChecked) {
            setShowHidden(false);
            setShowMore(false);
        } else {
            setShowMore(true);
            setShowHidden(false);
        }
    }, []);

    const handleVisibilityMenuDoubleClick = useCallback((isChecked) => {
        if (isChecked) {
            setShowHidden(false);
            setShowMore(false);
        } else {
            setShowHidden(true);
            setShowMore(true);
        }
    }, []);

    const handleShowAllToggle = useCallback(() => {
        setShowAll((prev) => !prev);
    }, []);

    const handleMoreAllToggle = useCallback(() => {
        setMoreAll((prev) => !prev);
    }, []);

    const handleShowHiddenToggle = useCallback(() => {
        setShowHidden((prev) => !prev);
    }, []);

    const handleShowMoreToggle = useCallback(() => {
        setShowMore((prev) => !prev);
    }, []);

    return {
        modelLayoutOption,
        modelLayoutData,
        isMaximized,
        page,
        showHidden,
        showMore,
        showAll,
        moreAll,
        layoutType,
        // modelHandlerConfig: modelHandlerConfigRef.current,
        // setIsMaximized,
        // setPage,
        // setShowHidden,
        // setShowMore,
        // setShowAll,
        // setMoreAll,
        setLayoutType,
        handleFullScreenToggle,
        handlePageChange,
        handleRowsPerPageChange,
        handleColumnOrdersChange,
        handleSortOrdersChange,
        handleShowLessChange,
        handlePinnedChange,
        handleOverrideChange,
        handleLayoutTypeChange,
        handleFiltersChange,
        handleStickyHeaderToggle,
        handleCommonKeyCollapseToggle,
        handleFrozenColumnsChange,
        handleColumnNameOverrideChange,
        handleHighlightUpdateOverrideChange,
        handleHighlightDurationChange,
        handleNoCommonKeyOverrideChange,
        handleDataSourceColorsChange,
        handleJoinByChange,
        handleCenterJoinToggle,
        handleFlipToggle,
        handleSelectedChartNameChange,
        handleChartEnableOverrideChange,
        handleChartDataChange,
        handleSelectedPivotNameChange,
        handlePivotEnableOverrideChange,
        handlePivotDataChange,
        handleQuickFiltersChange,
        handleVisibilityMenuClick,
        handleVisibilityMenuDoubleClick,
        handleShowAllToggle,
        handleMoreAllToggle,
        handleShowHiddenToggle,
        handleShowMoreToggle,
    };
};

export default useModelLayout;
