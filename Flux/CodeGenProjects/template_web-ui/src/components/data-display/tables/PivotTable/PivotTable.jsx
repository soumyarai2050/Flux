import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSelector } from 'react-redux';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import TableRenderers from 'react-pivottable/TableRenderers';
import Plot from 'react-plotly.js';
import createPlotlyRenderer from 'react-pivottable/PlotlyRenderers';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Add from '@mui/icons-material/Add';
import Close from '@mui/icons-material/Close';
import Delete from '@mui/icons-material/Delete';
import Done from '@mui/icons-material/Done';
import Save from '@mui/icons-material/Save';
import Icon from '../../../ui/Icon';
import ListPanel from '../../../ui/ListPanel/ListPanel';
import ContentCopier from '../../../ui/ContentCopier';
import 'react-pivottable/pivottable.css';
import styles from './PivotTable.module.css';
import { updatePivotSchema } from '../../../../utils/core/chartUtils';
import { addxpath, clearxpath } from '../../../../utils/core/dataAccess';
import { bindPlotlyClick } from '../../../../utils/core/plotlyClickMapper';
import { generateObjectFromSchema, getModelSchema } from '../../../../utils/core/schemaUtils';
import { MODES } from '../../../../constants';
import DataTree from '../../trees/DataTree';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../../utility/cards';
import FullScreenModal from '../../../ui/Modal';
import { cloneDeep } from 'lodash';
import Resizer from '../../../ui/Resizer/Resizer';

const PlotlyRenderers = createPlotlyRenderer(Plot);
const PIVOT_SCHEMA_NAME = 'pivot_data';

function PivotTable({
    pivotData,
    data,
    onPivotDataChange,
    selectedPivotName,
    mode,
    onModeToggle,
    onPivotSelect,
    pivotEnableOverride,
    onPivotCellSelect,
    children
}) {
    const containerRef = useRef(null);
    const { schema: projectSchema } = useSelector(state => state.schema);
    const [tableHeight, setTableHeight] = useState(300);
    const [schema, setSchema] = useState(updatePivotSchema(projectSchema));
    const [selectedIndex, setSelectedIndex] = useState(selectedPivotName ? pivotData.findIndex((o) => o.pivot_name === selectedPivotName) : null);
    const [storedPivotObj, setStoredPivotObj] = useState({});
    const [updatedPivotObj, setUpdatedPivotObj] = useState({});
    const [isPivotOptionOpen, setIsPivotOptionOpen] = useState(false);
    const [isCreate, setIsCreate] = useState(false);
    const [showColumnSelector, setShowColumnSelector] = useState(true);
    const [hasPvtUnused, setHasPvtUnused] = useState(false);

    const pivotObjRef = useRef();
    pivotObjRef.current = updatedPivotObj;
    const dataRef = useRef([]);
    dataRef.current = data;
    const onPivotCellSelectRef = useRef();
    onPivotCellSelectRef.current = onPivotCellSelect;

    const handleChartClick = useCallback((label, title) => {
        const labelSplit = label.split('-');
        let filterDict = {};
        filterDict = pivotObjRef.current?.rows.reduce((acc, item, index) => {
            acc[item] = labelSplit[index];
            return acc;
        }, filterDict);
        const titleSplit = title?.split('-');
        filterDict = pivotObjRef.current?.cols.reduce((acc, item, index) => {
            acc[item] = titleSplit[index];
            return acc;
        }, filterDict);
        const ids = dataRef.current
            .filter((row) => {
                // Check if the current row passes all column filters.
                return Object.keys(filterDict).every(columnId => {
                    const filterValue = filterDict[columnId];

                    // If there are no filter settings for this column, it passes by default.
                    if (!filterValue) return true;
                    return String(row[columnId]) === filterValue;
                });
            })
            .map((row) => row['data-id']);
        onPivotCellSelectRef.current(ids);
    }, [])

    // Attach single Plotly click event listener
    useEffect(() => {
        let unbindClick = null;
        let unbindAfterPlot = null;
        let attempts = 0;
        const maxAttempts = 20;

        const tryBind = () => {
            const plotlyDiv = document.querySelector('.js-plotly-plot');
            if (!plotlyDiv) {
                return false;
            }

            // Bind the click handler
            unbindClick = bindPlotlyClick(plotlyDiv, (mapped) => {
                handleChartClick(mapped.label, mapped.title);
            });

            // Also bind to plotly_afterplot to rebind after chart redraws
            if (plotlyDiv.on && typeof plotlyDiv.on === 'function') {
                const afterPlotHandler = () => {
                    // Rebind after plot updates
                    if (unbindClick) unbindClick();
                    unbindClick = bindPlotlyClick(plotlyDiv, (mapped) => {
                        handleChartClick(mapped.label, mapped.title);
                    });
                };
                plotlyDiv.on('plotly_afterplot', afterPlotHandler);
                unbindAfterPlot = () => {
                    if (plotlyDiv.removeListener) {
                        plotlyDiv.removeListener('plotly_afterplot', afterPlotHandler);
                    }
                };
            }

            return true;
        };

        // Try to bind immediately
        if (!tryBind()) {
            // If not ready, poll with short intervals
            const interval = setInterval(() => {
                attempts++;
                if (tryBind() || attempts >= maxAttempts) {
                    clearInterval(interval);
                }
            }, 100);

            return () => {
                clearInterval(interval);
                if (unbindClick) unbindClick();
                if (unbindAfterPlot) unbindAfterPlot();
            };
        }

        // Cleanup
        return () => {
            if (unbindClick) unbindClick();
            if (unbindAfterPlot) unbindAfterPlot();
        };
    }, [updatedPivotObj, handleChartClick]);

    const hideButtonRef = useRef(null);

    // Inject hide button into pvtUnused container
    useEffect(() => {
        // Only proceed if we have a valid pivot object
        if (!updatedPivotObj || Object.keys(updatedPivotObj).length === 0) {
            setHasPvtUnused(false);
            return;
        }

        const pvtUnused = document.querySelector('.pvtUnused');
        const button = hideButtonRef.current;

        if (pvtUnused && button && !pvtUnused.contains(button)) {
            setHasPvtUnused(true);
            // Insert button directly at the beginning of pvtUnused without li wrapper
            pvtUnused.insertBefore(button, pvtUnused.firstChild);
        }

        // Cleanup: move button back to original position when unmounting
        return () => {
            const button = hideButtonRef.current;
            if (button && button.parentElement) {
                // Check if parent still exists before removing
                button.parentElement.removeChild(button);
            }
        };
    }, [updatedPivotObj]); // Re-run when pivot config changes

    useEffect(() => {
        const updatedIndex = selectedPivotName ? pivotData.findIndex((o) => o.pivot_name === selectedPivotName) : null;
        setSelectedIndex(updatedIndex);
    }, [pivotEnableOverride, selectedPivotName])

    useEffect(() => {
        if (pivotData?.length > 0) {
            let updatedIndex = null;
            if ((selectedIndex || selectedIndex === 0) && pivotData[selectedIndex]) {
                updatedIndex = selectedIndex;
            } else {
                updatedIndex = 0;
            }
            if (updatedIndex !== selectedIndex) {
                setSelectedIndex(updatedIndex);
            }
        } else {
            // No pivots available, clear selection
            if (selectedIndex !== null) {
                setSelectedIndex(null);
            }
        }
    }, [pivotData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            const updatedObj = pivotData[selectedIndex];
            if (updatedObj) {
                setStoredPivotObj(updatedObj);
                setUpdatedPivotObj(addxpath(cloneDeep(updatedObj)));
                if (onPivotSelect) {
                    onPivotSelect(updatedObj.pivot_name);
                }
            } else {
                // Index is out of bounds, clear selection
                setStoredPivotObj({});
                setUpdatedPivotObj({});
                if (onPivotSelect) {
                    onPivotSelect(null);
                }
            }
        } else {
            setStoredPivotObj({});
            setUpdatedPivotObj({});
            if (onPivotSelect) {
                onPivotSelect(null);
            }
        }
        onPivotCellSelect(null);
        const prev = document.querySelector(`.${styles.selected}`);
        if (prev) {
            prev.classList.remove(styles.selected);
        }
    }, [selectedIndex])

    const handleTableResize = (newHeight) => {
        setTableHeight(newHeight);
    };

    const handlePivotTableChange = (updatedPivotProps) => {
        if (mode === MODES.READ) {
            onModeToggle();
        }
        const { rows, cols, vals, aggregatorName, rendererName, valueFilter } = updatedPivotProps;
        setUpdatedPivotObj((prev) => ({ ...prev, rows, cols, vals, aggregator_name: aggregatorName, renderer_name: rendererName, value_filter: JSON.stringify(valueFilter) }));
    }

    const handlePivotCreate = () => {
        const pivotSchema = getModelSchema(PIVOT_SCHEMA_NAME, schema);
        const updatedObj = addxpath(generateObjectFromSchema(schema, pivotSchema));
        updatedObj.rows = [];
        updatedObj.cols = [];
        updatedObj.vals = [];
        updatedObj.aggregator_name = 'Count';
        updatedObj.renderer_name = 'Table';
        updatedObj.value_filter = JSON.stringify({});
        setUpdatedPivotObj(updatedObj);
        setStoredPivotObj({});
        setIsCreate(true);
        onModeToggle();
        setIsPivotOptionOpen(true);
    }

    const handlePivotOptionClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        if (isCreate) {
            // If we cancel creation, restore the previously selected pivot
            if (selectedIndex !== null && pivotData[selectedIndex]) {
                const selectedPivotOption = pivotData[selectedIndex];
                setStoredPivotObj(selectedPivotOption);
                setUpdatedPivotObj(addxpath(cloneDeep(selectedPivotOption)));
            } else {
                // Or clear if nothing was selected
                setStoredPivotObj({});
                setUpdatedPivotObj({});
            }
        }
        setIsPivotOptionOpen(false);
        setIsCreate(false);
        onModeToggle();
    };

    const handleSave = () => {
        onModeToggle();
        setIsCreate(false);
        setIsPivotOptionOpen(false);
        const updatedObj = clearxpath(cloneDeep(updatedPivotObj));
        const idx = pivotData.findIndex((o) => o.pivot_name === updatedObj.pivot_name);
        const updatedPivotData = cloneDeep(pivotData);
        let newIndex = idx;
        if (idx !== -1) {
            updatedPivotData.splice(idx, 1, updatedObj);
        } else {
            updatedPivotData.push(updatedObj);
            newIndex = updatedPivotData.length - 1;
        }
        if (onPivotDataChange) {
            onPivotDataChange(updatedPivotData);
        }
        // Update selected index to the newly saved pivot
        setSelectedIndex(newIndex);
    }

    const handleUserChange = () => {

    }

    const handleUpdate = (updatedObj) => {
        setUpdatedPivotObj(updatedObj);
    }

    const handleSelect = (index) => {
        if (mode === MODES.READ) {
            if (index !== selectedIndex) {
                setSelectedIndex(index);
            }
        }
    }

    const handlePivotDelete = (pivotName, index) => {
        const updatedPivotData = pivotData.filter((o) => o.pivot_name !== pivotName);
        onPivotDataChange(updatedPivotData);

        if (index === selectedIndex) {
            setSelectedIndex(null);
            // Reset state if we're deleting the currently selected/edited pivot
            if (mode === MODES.EDIT) {
                setIsCreate(false);
                setIsPivotOptionOpen(false);
                onModeToggle();
            }
            // Clear the pivot objects to prevent stale data
            setStoredPivotObj({});
            setUpdatedPivotObj({});
        }
    }

    const handleDiscard = () => {
        setUpdatedPivotObj(addxpath(cloneDeep(storedPivotObj)));
        onModeToggle();
    }

    const clickCallback = function (e, _value, filters, pivotData) {
        const prev = document.querySelector(`.${styles.selected}`);
        if (prev) {
            prev.classList.remove(styles.selected);
        }

        // Add the module-scoped `selected` class to the clicked cell
        e.target.classList.add(styles.selected);
        const ids = [];
        pivotData.forEachMatchingRecord(filters, (record) => {
            ids.push(record['data-id']);
        });
        onPivotCellSelect(ids);
    };

    return (
        <>
            <Box className={styles.container} ref={containerRef}>
                <ListPanel
                    items={pivotData}
                    selectedIndex={selectedIndex}
                    onSelect={handleSelect}
                    onCreate={handlePivotCreate}
                    onDelete={(e, pivotName, index) => handlePivotDelete(pivotName, index)}
                    itemNameKey="pivot_name"
                    addButtonText="Add new pivot"
                    enableOverride={pivotEnableOverride}
                    collapse={true}
                    mode={mode}
                    additionalActions={(item, index, mode, selectedIndex) => (
                        <>
                            <ContentCopier text={item.pivot_name} />
                            {mode === MODES.EDIT && index === selectedIndex && (
                                <>
                                    <Icon title='Apply' onClick={handleSave}>
                                        <Done color='success' fontSize='small' />
                                    </Icon>
                                    <Icon title='Discard' onClick={handleDiscard}>
                                        <Close color='error' fontSize='small' />
                                    </Icon>
                                </>
                            )}
                            <Icon title='Delete' onClick={() => handlePivotDelete(item.pivot_name, index)}>
                                <Delete fontSize='small' />
                            </Icon>
                        </>
                    )}
                />
                <Divider orientation='vertical' flexItem />

                <Box className={styles.pivot_container}>
                    <Button
                        ref={hideButtonRef}
                        size="small"
                        variant="outlined"
                        onClick={() => setShowColumnSelector(s => !s)}
                        className={styles.columnToggleBtn}
                        style={{ display: hasPvtUnused ? 'inline-flex' : 'none', pointerEvents: 'auto' }}
                        draggable={false}
                        onDragStart={(e) => e.preventDefault()}
                    >
                        {showColumnSelector ? "Hide Columns" : "Show Columns"}
                    </Button>
                    {(updatedPivotObj && Object.keys(updatedPivotObj).length > 0) ? (
                        <Box
                            className={`${styles.pivot_table} ${!showColumnSelector ? styles.hideColumnSelector : ""}`}
                            style={{ height: `${tableHeight}px` }}
                        >
                            <PivotTableUI
                                {...updatedPivotObj}
                                data={data}
                                aggregatorName={updatedPivotObj.aggregator_name}
                                rendererName={updatedPivotObj.renderer_name}
                                valueFilter={updatedPivotObj.value_filter ? JSON.parse(updatedPivotObj.value_filter) : {}}
                                onChange={handlePivotTableChange}
                                renderers={Object.assign({}, TableRenderers, PlotlyRenderers)}
                                unusedOrientationCutoff={Infinity}
                                tableOptions={{
                                    clickCallback: clickCallback
                                }}
                                plotlyConfig={{
                                    staticPlot: false
                                }}
                            />
                        </Box>
                    ) : (
                        <Box className={styles.no_data_message} style={{ height: `${tableHeight}px` }}>
                            No Pivot Selected
                        </Box>
                    )}
                    <Resizer
                        direction="horizontal"
                        onResize={handleTableResize}
                        minSize={100}
                        maxSize={containerRef.current ? containerRef.current.clientHeight - 100 : 600}
                    />
                    <Box style={{ flex: 1, overflow: 'auto' }}>
                        {children}
                    </Box>
                </Box>
                <FullScreenModal
                    id={'pivot-option-modal'}
                    open={isPivotOptionOpen}
                    onClose={handlePivotOptionClose}
                >
                    <ModelCard>
                        <ModelCardHeader name={PIVOT_SCHEMA_NAME} >
                            <Icon name='save' title='save' onClick={handleSave}><Save fontSize='small' color='white' /></Icon>
                            <Icon name='close' title='close' onClick={handlePivotOptionClose}><Close fontSize='small' color='white' /></Icon>
                        </ModelCardHeader>
                        <ModelCardContent>
                            <DataTree
                                projectSchema={schema}
                                modelName={PIVOT_SCHEMA_NAME}
                                updatedData={updatedPivotObj}
                                storedData={storedPivotObj}
                                subtree={null}
                                mode={mode}
                                xpath={null}
                                onUpdate={handleUpdate}
                                onUserChange={handleUserChange}
                            />
                        </ModelCardContent>
                    </ModelCard>
                </FullScreenModal>
            </Box>
        </>
    )
}

export default PivotTable;