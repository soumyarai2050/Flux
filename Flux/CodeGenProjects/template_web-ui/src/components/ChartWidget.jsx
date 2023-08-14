import React, { useEffect, useRef, useState } from 'react';
import { Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText, Button, RadioGroup, Radio, FormControlLabel, Popover } from '@mui/material';
import classes from './ChartWidget.module.css';
import FullScreenModal from './Modal';
import TreeWidget from './TreeWidget';
import { DataTypes, Modes, SCHEMA_DEFINITIONS_XPATH } from '../constants';
import { addxpath, clearxpath, generateObjectFromSchema, getChartDatasets, getChartOption, updateChartDataObj, updateChartSchema } from '../utils';
import _, { cloneDeep } from 'lodash';
import WidgetContainer from './WidgetContainer';
import { Icon } from './Icon';
import { Add, AltRoute } from '@mui/icons-material';
import EChart from './EChart';

const name = 'chart_data';

function ChartWidget(props) {
    const [storedData, setStoredData] = useState({});
    const [modifiedData, setModifiedData] = useState({});
    const [selectedIndex, setSelectedIndex] = useState();
    const [open, setOpen] = useState(false);
    const [openModalPopup, setOpenModalPopup] = useState(false);
    const [mode, setMode] = useState(Modes.READ_MODE);
    const [data, setData] = useState({});
    const [openPartition, setOpenPartition] = useState(false);
    const [anchorEl, setAnchorEl] = useState(null);
    const [chartObj, setChartObj] = useState({});
    const [theme, setTheme] = useState('light');

    const schema = updateChartSchema(props.schema, props.collections, props.collectionView);
    const datasets = getChartDatasets(props.rows, props.partitionFld, chartObj);

    useEffect(() => {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setTheme('dark');
        }
    }, [])

    useEffect(() => {
        if (Object.keys(storedData).length > 0) {
            const updatedObj = addxpath(cloneDeep(storedData));
            setChartObj(updateChartDataObj(updatedObj, props.collections, props.rows, datasets, props.partitionFld, props.collectionView));
        }
    }, [storedData, props.filters, props.partitionFld])

    useEffect(() => {
        if (props.chartData && props.chartData.length > 0) {
            if (!((selectedIndex || selectedIndex === 0) && props.chartData[selectedIndex]) || !selectedIndex) {
                setSelectedIndex(0);
                setStoredData(props.chartData[0]);
                setModifiedData(addxpath(cloneDeep(props.chartData[0])));
            } else {
                setStoredData(props.chartData[selectedIndex]);
                setModifiedData(addxpath(cloneDeep(props.chartData[selectedIndex])));
            }
        }
    }, [props.chartData])

    useEffect(() => {
        if (selectedIndex || selectedIndex === 0) {
            setStoredData(props.chartData[selectedIndex]);
            setModifiedData(addxpath(cloneDeep(props.chartData[selectedIndex])));
        } else {
            setStoredData({});
            setModifiedData({});
        }
    }, [selectedIndex])

    useEffect(() => {
        setData(modifiedData);
    }, [modifiedData])

    // on closing of modal, open a pop up to confirm/discard changes
    const onClose = (e) => {
        if (!_.isEqual(modifiedData, data)) {
            setOpenModalPopup(true);
        } else {
            setOpen(false);
            setMode(Modes.READ_MODE);
        }
    }

    const onSave = () => {
        setMode(Modes.READ_MODE);
        setOpen(false);
        setOpenModalPopup(false);
        const updatedObj = clearxpath(cloneDeep(data));
        props.onChartDataChange(props.name, updatedObj);
    }

    // on closing of modal popup (discard), revert back the changes
    const onConfirmClose = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        else {
            setData(modifiedData);
            setOpen(false);
            setOpenModalPopup(false);
            setMode(Modes.READ_MODE);
        }
    }

    const onChangeMode = () => {
        setMode(Modes.EDIT_MODE);
        setOpen(true);
    }

    const onReload = () => {
        setMode(Modes.READ_MODE);
        props.onReload();
    }

    const onCreate = () => {
        let updatedObj = generateObjectFromSchema(schema, _.get(schema, [SCHEMA_DEFINITIONS_XPATH, name]));
        updatedObj = addxpath(updatedObj);
        setModifiedData(updatedObj);
        setData(updatedObj);
        setStoredData({});
        setMode(Modes.EDIT_MODE);
        setOpen(true);
    }

    const onUserChange = () => {

    }

    const onUpdate = (updatedData) => {
        setData(updatedData);
    }

    const onSelect = (index) => {
        setSelectedIndex(index);
    }

    const onPartitionOpen = (e) => {
        setOpenPartition(true);
        setAnchorEl(e.currentTarget);
    }

    const onPartitionClose = () => {
        setOpenPartition(false);
        setAnchorEl(null);
    }

    const onPartitionFldChange = (e, value) => {
        if (value === '') {
            value = null;
        }
        props.onPartitionFldChange(props.name, value);
        onPartitionClose();
    }

    let createMenu = '';
    if (mode === Modes.READ_MODE) {
        createMenu = <Icon title='Create' name='Create' onClick={onCreate}><Add fontSize='small' /></Icon>;
    }
    const partitionMenu = (
        <>
            <Icon className={classes.icon} name="Partition" title={"Partition: " + props.partitionFld} onClick={onPartitionOpen}><AltRoute fontSize='small' /></Icon>
            <Popover
                id={props.name + '_partitionFld'}
                open={openPartition}
                anchorEl={anchorEl}
                anchorOrigin={{
                    vertical: "bottom",
                    horizontal: "center"
                }}
                onClose={onPartitionClose}>
                <RadioGroup
                    defaultValue=''
                    name="partition_fld"
                    value={props.partitionFld ? props.partitionFld : ''}
                    onChange={onPartitionFldChange}>
                    <FormControlLabel size='small'
                        sx={{ paddingLeft: 1 }}
                        label='None'
                        value=''
                        control={
                            <Radio checked={!props.partitionFld} size='small' />
                        }
                    />
                    {props.collections.map(collection => {
                        if (collection.type === DataTypes.STRING) {
                            return (
                                <FormControlLabel size='small' key={collection.tableTitle}
                                    sx={{ paddingLeft: 1 }}
                                    label={collection.elaborateTitle ? collection.tableTitle : collection.key}
                                    value={collection.tableTitle}
                                    control={
                                        <Radio checked={props.partitionFld === collection.tableTitle} size='small' />
                                    }
                                />
                            )
                        }
                    })}
                </RadioGroup>
            </Popover>
        </>
    )
    const menu = (
        <>
            {createMenu}
            {partitionMenu}
            {props.menu}
        </>
    )

    const options = getChartOption(clearxpath(cloneDeep(chartObj)));

    return (
        <WidgetContainer
            name={props.name}
            title={props.title}
            onReload={onReload}
            layout={props.layout}
            supportedLayouts={props.supportedLayouts}
            onChangeLayout={props.onChangeLayout}
            mode={mode}
            onSave={onSave}
            menu={menu}
            onChangeMode={onChangeMode}>
            <Box className={classes.container}>
                <Box className={classes.list_container}>
                    <List>
                        {props.chartData && props.chartData.map((item, index) => (
                            <ListItem className={classes.list_item} key={index} selected={selectedIndex === index} disablePadding onClick={() => onSelect(index)}>
                                <ListItemButton>
                                    <ListItemText>{item.chart_name}</ListItemText>
                                </ListItemButton>
                            </ListItem>
                        ))}
                    </List>
                </Box>
                <Divider orientation="vertical" flexItem />
                <Box className={classes.chart_container}>
                    {props.rows.length > 0 &&
                        <EChart
                            loading={false}
                            theme={theme}
                            option={{
                                legend: {},
                                tooltip: { trigger: 'axis' },
                                dataset: datasets,
                                ...options
                            }}
                        />
                    }
                </Box>
            </Box>
            <FullScreenModal
                id={selectedIndex}
                open={open}
                onClose={onClose}
                onSave={onSave}
                popup={openModalPopup}
                onConfirmClose={onConfirmClose}>
                <TreeWidget
                    headerProps={{
                        title: props.title,
                        mode: mode,
                        // menuRight: modalCloseMenu,
                        onSave: onSave
                    }}
                    name='chart_data'
                    schema={schema}
                    data={data}
                    originalData={storedData}
                    mode={mode}
                    onUpdate={onUpdate}
                    onUserChange={onUserChange}
                    topLevel={false}
                />
                <Dialog
                    open={openModalPopup}
                    onClose={onConfirmClose}>
                    <DialogTitle>Save Changes</DialogTitle>
                    <DialogContent>
                        <DialogContentText>Do you want to save changes?</DialogContentText>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={onConfirmClose} autoFocus>Discard</Button>
                        <Button onClick={onSave} autoFocus>Save</Button>
                    </DialogActions>
                </Dialog>
            </FullScreenModal>
        </WidgetContainer>
    )
}

export default ChartWidget;