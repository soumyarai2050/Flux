import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import TableRenderers from 'react-pivottable/TableRenderers';
import Plot from 'react-plotly.js';
import createPlotlyRenderer from 'react-pivottable/PlotlyRenderers';
import { Box, Button, Divider, List, ListItem, ListItemButton, ListItemText } from '@mui/material';
import { Add, Close, Delete, Save } from '@mui/icons-material';
import Icon from '../../Icon';
import 'react-pivottable/pivottable.css';
import styles from './PivotTable.module.css';
import { updatePivotSchema, addxpath, clearxpath, generateObjectFromSchema, getModelSchema } from '../../../utils';
import { MODES } from '../../../constants';
import DataTree from '../../trees/DataTree/DataTree';
import { ModelCard, ModelCardContent, ModelCardHeader } from '../../cards';
import FullScreenModal from '../../Modal';
import { cloneDeep } from 'lodash';

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
    pivotEnableOverride
}) {
    const { schema: projectSchema } = useSelector(state => state.schema);

    const [schema, setSchema] = useState(updatePivotSchema(projectSchema));
    const [selectedIndex, setSelectedIndex] = useState(selectedPivotName ? pivotData.findIndex((o) => o.pivot_name === selectedPivotName) : null);
    const [storedPivotObj, setStoredPivotObj] = useState({});
    const [updatedPivotObj, setUpdatedPivotObj] = useState({});
    const [isPivotOptionOpen, setIsPivotOptionOpen] = useState(false);

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
    }, [selectedIndex, pivotData])

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
        const updatedPivotData = pivotData.filter((o) => o.pivot_data !== pivotName);
        if (onPivotDataChange) {
            onPivotDataChange(updatedPivotData);
        }
        if (index === selectedIndex) {
            setSelectedIndex(null);
        }
    }

    return (
        <Box className={styles.container}>
            <Box className={styles.list_container}>
                <Button color='warning' variant='contained' onClick={handlePivotCreate}>
                    <Add fontSize='small' />
                    Add new pivot
                </Button>
                <List>
                    {pivotData.map((item, index) => {
                        if (pivotEnableOverride.includes(item.pivot_name)) return;
                        return (
                            <ListItem className={styles.list_item} key={index} selected={selectedIndex === index} disablePadding onClick={() => handleSelect(index)}>
                                <ListItemButton>
                                    <ListItemText>{item.pivot_name}</ListItemText>
                                </ListItemButton>
                                {mode === MODES.EDIT && index === selectedIndex && (
                                    <Icon title='Save' onClick={handleSave}>
                                        <Save fontSize='small' />
                                    </Icon>
                                )}
                                <Icon title='Delete' onClick={() => handlePivotDelete(item.pivot_name, index)}>
                                    <Delete fontSize='small' />
                                </Icon>
                            </ListItem>
                        )
                    })}
                </List>
            </Box>
            <Divider orientation='vertical' flexItem />
            <Box className={styles.pivot_container}>
                {updatedPivotObj && Object.keys(updatedPivotObj).length > 0 && (
                    <PivotTableUI
                        {...updatedPivotObj}
                        data={data}
                        aggregatorName={updatedPivotObj.aggregator_name}
                        rendererName={updatedPivotObj.renderer_name}
                        valueFilter={updatedPivotObj.value_filter ? JSON.parse(updatedPivotObj.value_filter) : {}}
                        onChange={handlePivotTableChange}
                        renderers={Object.assign({}, TableRenderers, PlotlyRenderers)}
                        unusedOrientationCutoff={Infinity}
                    />
                )}
            </Box>
            <FullScreenModal
                id={'pivot-option-modal'}
                open={isPivotOptionOpen}
                onClose={handlePivotOptionClose}
            >
                <ModelCard>
                    <ModelCardHeader name={PIVOT_SCHEMA_NAME} >
                        <Icon name='save' title='save' onClick={handleSave}><Save fontSize='small' /></Icon>
                        <Icon name='close' title='close' onClick={handlePivotOptionClose}><Close fontSize='small' /></Icon>
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
    )
}

export default PivotTable;