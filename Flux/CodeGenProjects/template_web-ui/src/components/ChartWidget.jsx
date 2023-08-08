import React, { useEffect, useState } from 'react';
import { Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, List, ListItem, ListItemButton, ListItemText, } from '@mui/material';
import classes from './ChartWidget.module.css';
import FullScreenModal from './Modal';
import TreeWidget from './TreeWidget';
import { Button } from '@mui/base';
import { Modes, SCHEMA_DEFINITIONS_XPATH } from '../constants';
import { addxpath, clearxpath, generateObjectFromSchema, getChartOption, updateChartDataObj, updateChartSchema } from '../utils';
import _, { cloneDeep } from 'lodash';
import WidgetContainer from './WidgetContainer';
import { Icon } from './Icon';
import { Add } from '@mui/icons-material';
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

    const schema = updateChartSchema(props.schema, props.collections);

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
        let updatedObj = cloneDeep(data);
        updatedObj = updateChartDataObj(updatedObj, props.collections);
        setModifiedData(updatedObj);
        updatedObj = clearxpath(cloneDeep(updatedObj));
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

    let createMenu = '';
    if (mode === Modes.READ_MODE) {
        createMenu = <Icon title='Create' name='Create' onClick={onCreate}><Add fontSize='small' /></Icon>;
    }
    const menu = (
        <>  
            {createMenu}
            {props.menu}
        </>
    )

    const options = getChartOption(storedData);

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
                            theme='light'
                            option={{
                                legend: {},
                                tooltip: {},
                                dataset: [{
                                    dimensions: Object.keys(props.rows[0]),
                                    source: [...props.rows]
                                }],
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