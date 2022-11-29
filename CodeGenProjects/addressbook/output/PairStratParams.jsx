import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import { Modes, Layouts, DB_ID, SCHEMA_DEFINITIONS_XPATH, DataTypes, NEW_ITEM_ID } from '../constants';
import {
    getAllPairStrat, getPairStrat, createPairStrat, updatePairStrat,
    resetPairStrat, setModifiedPairStrat, setSelectedPairStratId, resetSelectedPairStratId, resetError
} from '../features/pairStratSlice';
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

const PairStratParams = (props) => {

    const { pairStratArray, pairStrat, modifiedPairStrat, selectedPairStratId, loading, error, mode, createMode } = useSelector((state) => state.pairStrat);
    const { schema } = useSelector((state) => state.schema);
    const [layout, setLayout] = useState(Layouts.TABLE_LAYOUT);

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
        if (currentSchema) {
            setLayout(currentSchema.layout);
        }
    }, [schema])

    useEffect(() => {
        if (createMode) {
            let object = isJsonRoot ? generateObjectFromSchema(schema, currentSchema) : generateObjectFromSchema(schema, parentSchema);
            _.set(object, DB_ID, NEW_ITEM_ID);
            let updatedData = addxpath(object);
            dispatch(setModifiedPairStrat(updatedData));
        } else {
            let updatedData = addxpath(cloneDeep(pairStrat));
            dispatch(setModifiedPairStrat(updatedData));
        }
    }, [createMode, pairStrat])

    useEffect(() => {
        if (selectedPairStratId && selectedPairStratId !== NEW_ITEM_ID) {
            dispatch(getPairStrat(selectedPairStratId));
        }
    }, [selectedPairStratId])
    if (loading) {
        return (
            <SkeletonField title={title} />
        )
    }

    let collections = [];
    if (currentSchema) {
        collections = createCollections(schema, currentSchema, {mode: mode});
    }

    const onChangeLayout = () => {
        if (layout === Layouts.TABLE_LAYOUT) {
            setLayout(Layouts.TREE_LAYOUT);
        } else {
            setLayout(Layouts.TABLE_LAYOUT);
        }
    }

    const onResetError = () => {
        dispatch(resetError());
    }

    const onUpdate = (updatedData) => {
        dispatch(setModifiedPairStrat(updatedData));
    }
    const onSwitchToggle = (e, id, xpath) => {
        let updatedData = cloneDeep(modifiedPairStrat);
        _.set(updatedData, xpath, e.target.checked);
        dispatch(setModifiedPairStrat(updatedData));
    }

    if (layout === Layouts.TABLE_LAYOUT) {
        let menu = <DynamicMenu disabled={mode !== Modes.EDIT_MODE} collections={collections} data={_.get(modifiedPairStrat, currentSchemaXpath)} onSwitchToggle={onSwitchToggle} />;
        return (
            <TableWidget
                headerProps={{
                    title: title,
                    mode: mode,
                    layout: layout,
                    menu: menu,
                    onChangeLayout: onChangeLayout
                }}
                name={parentSchemaName}
                schema={schema}
                data={modifiedPairStrat}
                originalData={pairStrat}
                collections={collections}
                mode={mode}
                onUpdate={onUpdate}
                error={error}
                onResetError={onResetError}
                xpath={currentSchemaXpath}
            />
        )
    } else if (layout === Layouts.TREE_LAYOUT) {
        let menu = <DynamicMenu disabled={mode !== Modes.EDIT_MODE} collections={collections} data={_.get(modifiedPairStrat, currentSchemaXpath)} onSwitchToggle={onSwitchToggle} />;
        return (
            <TreeWidget
                headerProps={{
                    title: title,
                    mode: mode,
                    layout: layout,
                    menu: menu,
                    onChangeLayout: onChangeLayout,
                }}
                name={parentSchemaName}
                schema={schema}
                data={modifiedPairStrat}
                originalData={pairStrat}
                mode={mode}
                onUpdate={onUpdate}
                error={error}
                onResetError={onResetError}
                xpath={currentSchemaXpath}
            />
        )
    } else {
        return <h1>Unsupported Layout</h1>
    }
}
export default PairStratParams;

