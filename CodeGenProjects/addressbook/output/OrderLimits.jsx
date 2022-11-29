import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import { Modes, Layouts, DB_ID, SCHEMA_DEFINITIONS_XPATH, DataTypes } from '../constants';
import {
    getAllOrderLimits, getOrderLimits, createOrderLimits, updateOrderLimits,
    resetOrderLimits, setModifiedOrderLimits, setSelectedOrderLimitsId, resetSelectedOrderLimitsId, resetError
} from '../features/orderLimitsSlice';
import { createCollections, generateObjectFromSchema, addxpath, clearxpath, lowerFirstLetter } from '../utils';
import SkeletonField from '../components/SkeletonField';
import TreeWidget from '../components/TreeWidget';
import TableWidget from '../components/TableWidget';
import Icon from '../components/Icon';
import { Add } from '@mui/icons-material';
import DynamicMenu from '../components/DynamicMenu';

const useStyles = makeStyles({
    icon: {
        backgroundColor: '#ccc !important',
        marginRight: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    }
})

const OrderLimits = (props) => {

    const { orderLimitsArray, orderLimits, modifiedOrderLimits, selectedOrderLimitsId, loading, error } = useSelector(state => state.orderLimits);
    const { schema } = useSelector(state => state.schema);
    const [mode, setMode] = useState(Modes.READ_MODE);
    const [layout, setLayout] = useState(Layouts.UNSPECIFIED);

    const dispatch = useDispatch();
    const classes = useStyles();

    let currentSchema = _.get(schema, props.name);
    let currentSchemaXpath = null;
    let title = currentSchema ? currentSchema.title : props.name;
    let isJsonRoot = _.keys(schema).length > 0 && currentSchema.json_root ? true : false;
    let parentSchema = null;
    let parentSchemaName = null;
    if (!isJsonRoot) {
        let currentSchemaPropname = lowerFirstLetter(props.name);
        _.keys(_.get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {
            let current = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);
            if (current.type === DataTypes.OBJECT && _.has(current.properties, currentSchemaPropname)) {
                parentSchema = current;
                parentSchemaName = SCHEMA_DEFINITIONS_XPATH + '.' + key;
                currentSchemaXpath = currentSchemaPropname;
            }
        })
    }
    
    useEffect(() => {
        dispatch(getAllOrderLimits());
    }, []);

    useEffect(() => {
        if (currentSchema) {
            setLayout(currentSchema.layout);
        }
    }, [schema])

    useEffect(() => {
        let updatedData = addxpath(cloneDeep(orderLimits));
        dispatch(setModifiedOrderLimits(updatedData));
    }, [orderLimits])

    if (loading) {
        return (
            <SkeletonField title={title} />
        )
    }

    let collections = [];
    if (currentSchema) {
        collections = createCollections(schema, currentSchema, {mode: mode});
    }

    const onChangeMode = () => {
        setMode(Modes.EDIT_MODE);
    }

    const onChangeLayout = () => {
        if (layout === Layouts.TABLE_LAYOUT) {
            setLayout(Layouts.TREE_LAYOUT);
        } else {
            setLayout(Layouts.TABLE_LAYOUT);
        }
    }

    const onReload = () => {
        dispatch(getAllOrderLimits());
    }

    const onResetError = () => {
        dispatch(resetError());
    }

    const onCreate = () => {
        let object = generateObjectFromSchema(schema, _.get(schema, props.name));
        let updatedData = addxpath(object);
        dispatch(setModifiedOrderLimits(updatedData));
    }

    const onUpdate = (updatedData) => {
        dispatch(setModifiedOrderLimits(updatedData));
    }

    const onSave = () => {
        let updatedData = clearxpath(cloneDeep(modifiedOrderLimits));
        if (!_.isEqual(orderLimits, updatedData)) {
            if (_.get(orderLimits, DB_ID)) {
                dispatch(updateOrderLimits(updatedData));
            } else {
                dispatch(createOrderLimits(updatedData));
            }
        }
        setMode(Modes.READ_MODE);
    }

    const onSwitchToggle = (e, id, xpath) => {
        let updatedData = cloneDeep(modifiedOrderLimits);
        _.set(updatedData, xpath, e.target.checked);
        dispatch(setModifiedOrderLimits(updatedData));
    }

    if (layout === Layouts.TABLE_LAYOUT) {
        let menu = <DynamicMenu collections={collections} data={modifiedOrderLimits} disabled={mode !== Modes.EDIT_MODE} onSwitchToggle={onSwitchToggle} />;
        return (
            <TableWidget
                headerProps={{
                    title: title,
                    mode: mode,
                    layout: layout,
                    menu: menu,
                    onChangeMode: onChangeMode,
                    onChangeLayout: onChangeLayout,
                    onSave: onSave,
                    onReload: onReload
                }}
                name={props.name}
                schema={schema}
                data={modifiedOrderLimits}
                originalData={orderLimits}
                collections={collections}
                mode={mode}
                onUpdate={onUpdate}
                error={error}
                onResetError={onResetError}
            />
        )
    } else if (layout === Layouts.TREE_LAYOUT) {
        let menu = <DynamicMenu collections={collections} data={modifiedOrderLimits} disabled={mode !== Modes.EDIT_MODE} onSwitchToggle={onSwitchToggle} />;
        if (isJsonRoot) {
            menu = (
                <DynamicMenu collections={collections} data={modifiedOrderLimits} disabled={mode !== Modes.EDIT_MODE} onSwitchToggle={onSwitchToggle}>
                    {mode === Modes.EDIT_MODE && _.keys(orderLimits).length === 0
                        && _.keys(modifiedOrderLimits).length === 0 && <Icon className={classes.icon} title="Create" onClick={onCreate}><Add fontSize="small" /></Icon>}
                </DynamicMenu>
            )
        }

        return (
            <TreeWidget
                headerProps={{
                    title: title,
                    mode: mode,
                    layout: layout,
                    menu: menu,
                    onChangeMode: onChangeMode,
                    onChangeLayout: onChangeLayout,
                    onSave: onSave,
                    onReload: onReload
                }}
                name={props.name}
                schema={schema}
                data={modifiedOrderLimits}
                originalData={orderLimits}
                mode={mode}
                onUpdate={onUpdate}
                error={error}
                onResetError={onResetError}
            />
        )
    } else {
        return <h1>Unsupported Layout</h1>
    }
}

export default OrderLimits;

