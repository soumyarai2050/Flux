import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import { Modes, Layouts, DB_ID, SCHEMA_DEFINITIONS_XPATH, DataTypes, NEW_ITEM_ID } from '../constants';
import {
    getAllStratCollection, getStratCollection, createStratCollection, updateStratCollection,
    resetStratCollection, setModifiedStratCollection, setSelectedStratCollectionId, resetSelectedStratCollectionId, resetError
} from '../features/stratCollectionSlice';
import {
    getAllPairStrat, getPairStrat, createPairStrat, updatePairStrat,
    resetPairStrat, setModifiedPairStrat, setSelectedPairStratId, resetSelectedPairStratId, setMode, setCreateMode
} from '../features/pairStratSlice';
import { createCollections, generateObjectFromSchema, addxpath, clearxpath, lowerFirstLetter, getNewItem } from '../utils';
import SkeletonField from '../components/SkeletonField';
import WidgetContainer from '../components/WidgetContainer';
import AbbreviatedFilterWidget from '../components/AbbreviatedFilterWidget';
import { Divider, List, ListItem, ListItemButton, ListItemText, Chip, Box } from '@mui/material';
import Icon from '../components/Icon';
import { Add, Delete } from '@mui/icons-material';

const useStyles = makeStyles({
    icon: {
        backgroundColor: '#ccc !important',
        marginRight: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    }
})

const StratCollection = (props) => {

    const { stratCollectionArray, stratCollection, modifiedStratCollection, selectedStratCollectionId, loading, error } = useSelector(state => state.stratCollection);
    const { pairStratArray, pairStrat, modifiedPairStrat, selectedPairStratId, mode, createMode } = useSelector(state => state.pairStrat);
    const { schema } = useSelector((state) => state.schema);
    const [layout, setLayout] = useState(Layouts.UNSPECIFIED);
    const [searchValue, setSearchValue] = useState('');

    const dispatch = useDispatch();
    const classes = useStyles();

    let currentSchema = _.get(schema, props.name);
    let currentSchemaXpath = null;
    let title = currentSchema ? currentSchema.title : props.name;
    let isJsonRoot = _.keys(schema).length > 0 && currentSchema.json_root ? true : false;
    let parentSchema = null;
    if (!isJsonRoot) {
        let currentSchemaPropname = lowerFirstLetter(props.name);
        _.keys(_.get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {
            let current = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);
            if (current.type === DataTypes.OBJECT && _.has(current.properties, currentSchemaPropname)) {
                parentSchema = current;
                currentSchemaXpath = currentSchemaPropname;
            }
        })
    }
    
    let collections = [];
    if (currentSchema) {
        collections = createCollections(schema, currentSchema, {mode: mode});
    }

    let bufferedKeyName = collections.filter(collection => collection.key.includes('buffer'))[0] ?
        collections.filter(collection => collection.key.includes('buffer'))[0].key : null;
    let loadedKeyName = collections.filter(collection => collection.key.includes('load'))[0] ?
        collections.filter(collection => collection.key.includes('load'))[0].key : null;
    let abbreviated = collections.filter(collection => collection.abbreviated && collection.abbreviated !== "JSON")[0] ?
        collections.filter(collection => collection.abbreviated && collection.abbreviated !== "JSON")[0].abbreviated : null;
    let dependentName = abbreviated ? abbreviated.split('.')[0] : null;

    useEffect(() => {
        dispatch(getAllStratCollection());
        dispatch(getAllPairStrat());
    }, []);

    useEffect(() => {
        if (currentSchema) {
            setLayout(currentSchema.layout);
        }
    }, [schema])

    useEffect(() => {
        if (_.get(stratCollection, loadedKeyName) && _.get(stratCollection, loadedKeyName).length > 0) {
            let id = getId(_.get(stratCollection, loadedKeyName)[0]) * 1;
            dispatch(setSelectedPairStratId(id));
        }
    }, [stratCollection])


    if (loading) {
        return (
            <SkeletonField title={title} />
        )
    }

    if (!bufferedKeyName || !loadedKeyName || !abbreviated) {
        return (
            <Box>{Layouts.ABBREVIATED_FILTER_LAYOUT} not supported. Required fields not found.</Box>
        )
    }

    const onChangeMode = () => {
        dispatch(setMode(Modes.EDIT_MODE));
    }

    const onReload = () => {
        dispatch(getAllStratCollection());
        dispatch(getAllPairStrat());
        dispatch(resetPairStrat());
        setSearchValue('');
    }

    const onResetError = () => {
        dispatch(resetError());
    }

    const onCreate = () => {
        if (!_.get(stratCollection, DB_ID)) {
            let object = generateObjectFromSchema(schema, currentSchema);
            dispatch(createStratCollection(object));
        } else {
            dispatch(setCreateMode(true));
            dispatch(setMode(Modes.EDIT_MODE));
            let newItem = getNewItem(abbreviated);
            let updatedData = cloneDeep(modifiedStratCollection);
            _.get(updatedData, loadedKeyName).push(newItem);
            dispatch(setModifiedStratCollection(updatedData));
            dispatch(setSelectedPairStratId(NEW_ITEM_ID));
            dispatch(resetPairStrat());
        }
    }

    const onSave = () => {
        if (createMode) {
            dispatch(setCreateMode(false));
            let updatedData = cloneDeep(modifiedStratCollection);
            let updatedLoaded = _.get(updatedData, loadedKeyName).filter((item) => {
                let id = getId(item) * 1;
                return id !== NEW_ITEM_ID;
            })
            _.set(updatedData, loadedKeyName, updatedLoaded);
            let values = abbreviated.split('-').map((field) => _.get(modifiedPairStrat, field.substring(field.indexOf('.') + 1)));
            let newItem = values.join('-');
            _.get(updatedData, loadedKeyName).push(newItem);
            dispatch(setModifiedStratCollection(updatedData));
            let updatedPairStrat = clearxpath(cloneDeep(modifiedPairStrat));
            delete updatedPairStrat[DB_ID];
            dispatch(createPairStrat(updatedPairStrat));
        } else {
            if (!_.isEqual(pairStrat, modifiedPairStrat)) {
                dispatch(updatePairStrat(modifiedPairStrat));
            }
        }
        dispatch(setMode(Modes.READ_MODE));
    }

    const onChange = (e, value) => {
        setSearchValue(value);
    }
    const onLoad = () => {
        let updatedData = cloneDeep(stratCollection);
        let index = _.get(stratCollection, bufferedKeyName).indexOf(searchValue);
        _.get(updatedData, bufferedKeyName).splice(index, 1);
        _.get(updatedData, loadedKeyName).push(searchValue);
        dispatch(updateStratCollection(updatedData));
        let id = getId(searchValue) * 1;
        setSelectedPairStratId(id);
        setSearchValue('');
    }
    const onUnload = (value) => {
        let updatedData = cloneDeep(stratCollection);
        let index = _.get(stratCollection, loadedKeyName).length - 1;
        _.get(updatedData, loadedKeyName).splice(index, 1);
        _.get(updatedData, bufferedKeyName).push(value);
        dispatch(updateStratCollection(updatedData));
        dispatch(resetPairStrat());
        dispatch(resetSelectedPairStratId());
    }

    const onDiscard = () => {
        dispatch(setCreateMode(false));
        dispatch(setModifiedStratCollection(stratCollection));
        dispatch(setMode(Modes.READ_MODE));
        // TODO: again select the first strat in the loaded keys if avialable
    }

    const onSelect = (id) => {
        id = id * 1;
        dispatch(setSelectedPairStratId(id));
    }

    const getId = (text) => {
        let index = abbreviated.split('-').length - 1;
        let id = text.split('-')[index] * 1;
        return id;
    }

    if (createMode) {
        return (
            <WidgetContainer
                title={title}
                mode={mode}
                onSave={onSave}>
                <Divider textAlign='left'><Chip label='Staging' /></Divider>
                <List>
                    {_.get(modifiedStratCollection, loadedKeyName) && _.get(modifiedStratCollection, loadedKeyName).map((item, index) => {
                        let id = getId(item) * 1;
                        if (id !== NEW_ITEM_ID) return;
                        return (
                            <ListItem key={index} className={classes.listItem} selected={selectedPairStratId === id} disablePadding>
                                <ListItemButton>
                                    <ListItemText>{item}</ListItemText>
                                </ListItemButton>
                                <Icon title='Discard' onClick={onDiscard}><Delete fontSize='small' /></Icon>
                            </ListItem>
                        )
                    })}
                </List>
            </WidgetContainer>
        )
    }

    let createMenu = '';
    if (mode === Modes.READ_MODE) {
        createMenu = <Icon className={classes.icon} title="Create" onClick={onCreate}><Add fontSize="small" /></Icon>;
    }

    let alertBubbleSource = null;
    let alertBubbleColorSource = null;
    if (collections.filter(col => col.hasOwnProperty('alertBubbleSource'))[0]) {
        alertBubbleSource = collections.filter(col => col.hasOwnProperty('alertBubbleSource'))[0].alertBubbleSource;
        alertBubbleColorSource = collections.filter(col => col.hasOwnProperty('alertBubbleSource'))[0].alertBubbleColor;
    }

    if (dependentName === alertBubbleSource.split('.')[0]) {
        alertBubbleSource = alertBubbleSource.substring(alertBubbleSource.indexOf('.') + 1);
        alertBubbleColorSource = alertBubbleColorSource.substring(alertBubbleColorSource.indexOf('.') + 1);
    }

    return (
        <AbbreviatedFilterWidget
            headerProps={{
                title: title,
                mode: mode,
                menu: createMenu,
                onChangeMode: onChangeMode,
                onSave: onSave,
                onReload: onReload
            }}
            name={props.name}
            schema={schema}
            bufferedKeyName={bufferedKeyName}
            bufferedLabel={collections.filter(col => col.key === bufferedKeyName)[0].title}
            searchValue={searchValue}
            options={_.get(stratCollection, bufferedKeyName) ? _.get(stratCollection, bufferedKeyName) : []}
            onChange={onChange}
            onLoad={onLoad}
            loadedKeyName={loadedKeyName}
            loadedLabel={collections.filter(col => col.key === loadedKeyName)[0].title}
            items={_.get(stratCollection, loadedKeyName) ? _.get(stratCollection, loadedKeyName) : []}
            selected={selectedPairStratId}
            onSelect={onSelect}
            onUnload={onUnload}
            abbreviated={abbreviated}
            itemsMetadata={pairStratArray}
            dependentName={dependentName}
            alertBubbleSource={alertBubbleSource}
            alertBubbleColorSource={alertBubbleColorSource}
            error={error}
            onResetError={onResetError}
        />
    )
}

export default StratCollection;

