import React, { useState, useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import TableRenderers from 'react-pivottable/TableRenderers';
import Plot from 'react-plotly.js';
import createPlotlyRenderer from 'react-pivottable/PlotlyRenderers';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
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
    const [isCellActive, setIsCellActive] = useState(false);

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
        }
    }, [pivotData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            const updatedObj = pivotData[selectedIndex];
            setStoredPivotObj(updatedObj);
            setUpdatedPivotObj(addxpath(cloneDeep(updatedObj)));
            if (onPivotSelect) {
                onPivotSelect(updatedObj.pivot_name);
            }
        } else {
            setStoredPivotObj({});
            setUpdatedPivotObj({});
            if (onPivotSelect) {
                onPivotSelect(null);
            }
        }
        onPivotCellSelect(null);
        setIsCellActive(false);
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
        onModeToggle();
        setIsPivotOptionOpen(true);
    }

    const handlePivotOptionClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        setIsPivotOptionOpen(false);
        onModeToggle();
    }

    const handleSave = () => {
        onModeToggle();
        setIsPivotOptionOpen(false);
        const updatedObj = clearxpath(cloneDeep(updatedPivotObj));
        const idx = pivotData.findIndex((o) => o.pivot_name === updatedObj.pivot_name);
        const updatedPivotData = cloneDeep(pivotData);
        if (idx !== -1) {
            updatedPivotData.splice(idx, 1, updatedObj);
        } else {
            updatedPivotData.push(updatedObj);
        }
        if (onPivotDataChange) {
            onPivotDataChange(updatedPivotData);
        }
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
        }
    }

    const handleDiscard = () => {
        setUpdatedPivotObj(addxpath(cloneDeep(storedPivotObj)));
        onModeToggle();
    }

    const clickCallback = function (e, value, filters, pivotData) {
        const prev = document.querySelector(`.${styles.selected}`);
        if (prev) {
            prev.classList.remove(styles.selected);
        }

        // 2. Add the module-scoped `selected` class to the clicked cell
        e.target.classList.add(styles.selected);
        const ids = [];
        pivotData.forEachMatchingRecord(filters, (record) => {
            ids.push(record['data-id']);
        });
        onPivotCellSelect(ids);
        setIsCellActive(true);
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
                    {updatedPivotObj && Object.keys(updatedPivotObj).length > 0 && (
                        <>
                            <Box className={styles.pivot_table} style={{ height: `${tableHeight}px` }}>
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
                                />
                            </Box>
                            {isCellActive && (
                                <>
                                    <Resizer
                                        direction="horizontal"
                                        onResize={handleTableResize}
                                        minSize={100}
                                        maxSize={containerRef.current ? containerRef.current.clientHeight - 100 : 600}
                                    />
                                    <Box style={{ flex: 1, overflow: 'auto' }}>
                                        {children}
                                    </Box>
                                </>
                            )}
                        </>
                    )}
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