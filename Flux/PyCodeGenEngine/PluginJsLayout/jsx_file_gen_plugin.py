#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, convert_to_camel_case


class JsxFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    -- Types:
    ----- 1. Json Root and Layout type as table or tree
    ----- 2. Json Root and Layout type as table or tree in repeated view
    ----- 3. Non-Root Type and Layout as table or tree
    ----- 4. Non-Root Type and Layout as table or tree in repeated view
    ----- 5. Layout as Abbreviated Type
    """
    root_type: str = 'RootType'
    repeated_root_type: str = 'RepeatedRootType'
    non_root_type: str = 'NonRootType'
    repeated_non_root_type: str = 'RepeatedNonRootType'
    abbreviated_type: str = 'AbbreviatedType'

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_jsx_file_convert
        ]
        self.root_message: protogen.Message | None = None
        self.abbreviated_dependent_message_name: str | None = None
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix: str = ""

    def handle_import_output(self, message: protogen.Message, layout_type: str) -> str:
        output_str = "/* react and third-party library imports */\n"
        if layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "import React, { Fragment, useEffect, memo } from 'react';\n"
        else:
            output_str += "import React, { Fragment, useState, useEffect, useCallback, useRef, memo } from 'react';\n"
        output_str += "import { useSelector, useDispatch } from 'react-redux';\n"
        output_str += "import _, { cloneDeep, isEqual } from 'lodash';\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "import { Add } from '@mui/icons-material';\n"
        elif layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "import { Add, Delete } from '@mui/icons-material';\n"
            output_str += "import { Divider, List, ListItem, ListItemButton, ListItemText, Chip, Box } " \
                          "from '@mui/material';\n"
        output_str += "/* redux CRUD and additional helper actions */\n"
        output_str += "import {\n"
        message_name = message.proto.name
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += f"    getAll{message_name},\n"
            output_str += f"    set{message_name}Ws, resetError\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += f"    getAll{message_name}, create{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}ArrayWs, set{message_name}Ws, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetError,\n"
            output_str += "    setUserChanges, setDiscardedChanges, setOpenWsPopup\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            message_name = self.root_message.proto.name
            output_str += f"    setModified{message_name}, resetError,\n"
            output_str += "    setUserChanges, setDiscardedChanges,\n"
            output_str += f"    setOpenConfirmSavePopup, set{message_name}\n"
        else:
            output_str += f"    getAll{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}ArrayWs, set{message_name}Ws, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetError\n"
        message_name_camel_cased = message_name[0].lower() + message_name[1:]
        output_str += "}" + f" from '../features/{message_name_camel_cased}Slice';\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            dependent_message_name = self.abbreviated_dependent_message_name
            dependent_message_name_camel_cased = dependent_message_name[0].lower() + dependent_message_name[1:]
            output_str += "import {\n"
            output_str += f"    create{dependent_message_name}, update{dependent_message_name},\n"
            output_str += f"    set{dependent_message_name}Array, set{dependent_message_name}ArrayWs," \
                          f"setModified{dependent_message_name}, setSelected{dependent_message_name}Id,\n"
            output_str += "    setUserChanges, setDiscardedChanges, setOpenWsPopup,\n"
            output_str += f"    setMode, setCreateMode, setOpenConfirmSavePopup, reset{dependent_message_name}, " \
                          f"resetSelected{dependent_message_name}Id\n"
            output_str += "}" + f" from '../features/{dependent_message_name_camel_cased}Slice';\n"
        output_str += "/* project constants */\n"
        output_str += "import { Modes, Layouts, DB_ID"
        if layout_type == JsxFileGenPlugin.repeated_root_type or layout_type == JsxFileGenPlugin.root_type:
            output_str += ", API_ROOT_URL"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += ", SCHEMA_DEFINITIONS_XPATH, DataTypes"
        else:
            output_str += ", API_ROOT_URL, SCHEMA_DEFINITIONS_XPATH, NEW_ITEM_ID"
        output_str += " } from '../constants';\n"
        output_str += "/* common util imports */\n"
        output_str += "import {\n"
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "    addxpath, getTableColumns, getTableRows, getCommonKeyCollections, applyFilter\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += "    generateObjectFromSchema, addxpath, clearxpath, getObjectWithLeastId, " \
                          "generateRowTrees, createObjectFromDict,\n"
            output_str += "    getTableColumns, getTableRows, getCommonKeyCollections, getXpathKeyValuePairFromObject\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "    addxpath, getTableColumns, getTableRows, getCommonKeyCollections, lowerFirstLetter\n"
        else:
            output_str += "    generateObjectFromSchema, addxpath, clearxpath, getObjectWithLeastId, " \
                          "createObjectFromDict,\n"
            output_str += "    getNewItem, getIdFromAbbreviatedKey, getAbbreviatedKeyFromId, createCollections\n"
        output_str += "} from '../utils';\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "import { usePrevious } from '../hooks';\n"
        output_str += "/* custom components */\n"
        output_str += "import WidgetContainer from '../components/WidgetContainer';\n"
        output_str += "import SkeletonField from '../components/SkeletonField';\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "import AbbreviatedFilterWidget from '../components/AbbreviatedFilterWidget';\n"
        else:
            output_str += "import TreeWidget from '../components/TreeWidget';\n"
            output_str += "import TableWidget from '../components/TableWidget';\n"
            output_str += "import DynamicMenu from '../components/DynamicMenu';\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "import { Icon } from '../components/Icon';\n"
        if layout_type != JsxFileGenPlugin.non_root_type:
            output_str += "import { ConfirmSavePopup, WebsocketUpdatePopup } from '../components/Popup';\n"
        output_str += "\n\n"
        return output_str

    def handle_non_abbreviated_return(self, message_name: str, message_name_camel_cased: str, layout_type: str) -> str:
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str = '    let menu = (\n'
            output_str += '        <DynamicMenu\n'
            output_str += '            collections={collections}\n'
            output_str += '            currentSchema={currentSchema}\n'
            output_str += '            commonKeyCollections={commonKeyCollections}\n'
            output_str += '            data={modifiedData}\n'
            output_str += '            disabled={mode !== Modes.EDIT_MODE}\n'
            output_str += '            filter={filter}\n'
            output_str += '            onFilterChange={setFilter}\n'
            output_str += '            onButtonToggle={onButtonToggle}\n'
            output_str += '        />\n'
            output_str += '    )\n\n'
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str = "    let menu = (\n"
            output_str += "        <DynamicMenu collections={collections} currentSchema={currentSchema} " \
                          "commonKeyCollections={commonKeyCollections} data={modified" + f"{message_name}" \
                                                                                         "} disabled={mode !== Modes.EDIT_MODE} onButtonToggle={onButtonToggle}>\n"
            output_str += "            {mode === Modes.READ_MODE && _.keys(" + f"{message_name_camel_cased})." \
                                                                               f"length === 0 && _.keys(modified{message_name}).length === 0 &&\n"
            output_str += "                <Icon name='Create' title='Create' " \
                          "onClick={onCreate}><Add fontSize='small' /></Icon>}\n"
            output_str += "        </DynamicMenu>\n"
            output_str += "    )\n\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str = "    let menu = <DynamicMenu disabled={mode !== Modes.EDIT_MODE} " \
                         "currentSchema={currentSchema} collections=" \
                         "{collections} commonKeyCollections={commonKeyCollections}" \
                         " data={_.get(modified" + f"{root_msg_name}" + \
                         ", currentSchemaXpath)} onButtonToggle={onButtonToggle} />;\n"
        output_str += "    return (\n"
        output_str += "        <Fragment>\n"
        output_str += "            {props.layout === Layouts.TABLE_LAYOUT ? (\n"
        output_str += "                <TableWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        name: props.name,\n"
        output_str += "                        title: title,\n"
        if layout_type != JsxFileGenPlugin.repeated_root_type:
            output_str += "                        mode: mode,\n"
            output_str += "                        layout: props.layout,\n"
        output_str += "                        menu: menu,\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.repeated_root_type:
            if layout_type != JsxFileGenPlugin.repeated_root_type:
                output_str += "                        onChangeMode: onChangeMode,\n"
                output_str += "                        onChangeLayout: props.onChangeLayout,\n"
            output_str += "                        onSave: onSave,\n"
            output_str += "                        onReload: onReload\n"
            output_str += "                    }}\n"
            output_str += "                    name={props.name}\n"
            output_str += "                    schema={schema}\n"
            if layout_type == JsxFileGenPlugin.repeated_root_type:
                output_str += "                    data={modifiedData}\n"
                output_str += "                    originalData={originalData}\n"
            else:
                output_str += "                    data={modified" + f"{message_name}" + "}\n"
                output_str += "                    originalData={" + f"{message_name_camel_cased}" + "}\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str += "                        onChangeLayout: props.onChangeLayout\n"
            output_str += "                    }}\n"
            output_str += "                    name={parentSchemaName}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified" + f"{root_msg_name}" + "}\n"
            output_str += "                    originalData={" + f"{root_message_name_camel_cased}" + "}\n"
        output_str += "                    collections={collections}\n"
        output_str += "                    rows={rows}\n"
        output_str += "                    tableColumns={tableColumns}\n"
        output_str += "                    commonKeyCollections={commonKeyCollections}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    onUpdate={onUpdate}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        if layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "                    xpath={currentSchemaXpath}\n"
        output_str += "                    onUserChange={onUserChange}\n"
        output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                    enableOverride={props.enableOverride}\n"
        output_str += "                    disableOverride={props.disableOverride}\n"
        output_str += "                    onOverrideChange={props.onOverrideChange}\n"
        output_str += "                />\n"
        output_str += "            ) : props.layout === Layouts.TREE_LAYOUT ? (\n"
        output_str += "                <TreeWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        name: props.name,\n"
        output_str += "                        title: title,\n"
        if layout_type != JsxFileGenPlugin.repeated_root_type and layout_type != JsxFileGenPlugin.repeated_non_root_type:
            output_str += "                        mode: mode,\n"
        output_str += "                        layout: props.layout,\n"
        output_str += "                        menu: menu,\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.repeated_root_type:
            if layout_type != JsxFileGenPlugin.repeated_root_type:
                output_str += "                        onChangeMode: onChangeMode,\n"
            output_str += "                        onChangeLayout: props.onChangeLayout,\n"
            output_str += "                        onSave: onSave,\n"
            output_str += "                        onReload: onReload\n"
            output_str += "                    }}\n"
            output_str += "                    name={props.name}\n"
            output_str += "                    schema={schema}\n"
            if layout_type == JsxFileGenPlugin.repeated_root_type:
                output_str += "                    data={modifiedData}\n"
                output_str += "                    originalData={originalData}\n"
            else:
                output_str += "                    data={modified" + f"{message_name}" + "}\n"
                output_str += "                    originalData={" + f"{message_name_camel_cased}" + "}\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str += "                        onChangeLayout: props.onChangeLayout,\n"
            output_str += "                    }}\n"
            output_str += "                    name={parentSchemaName}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified" + f"{root_msg_name}" + "}\n"
            output_str += "                    originalData={" + f"{root_message_name_camel_cased}" + "}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    onUpdate={onUpdate}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        if layout_type == self.non_root_type:
            output_str += "                    xpath={currentSchemaXpath}\n"
        output_str += "                    onUserChange={onUserChange}\n"
        output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                />\n"
        output_str += "            ) : (\n"
        output_str += "                <h1>Unsupported Layout</h1>\n"
        output_str += "            )}\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.repeated_root_type or \
                layout_type == JsxFileGenPlugin.repeated_non_root_type:
            output_str += "            <ConfirmSavePopup\n"
            output_str += "                open={openConfirmSavePopup}\n"
            output_str += "                onClose={onCloseConfirmPopup}\n"
            output_str += "                onSave={onConfirmSave}\n"
            output_str += "                src={userChanges}\n"
            output_str += "            />\n"
            output_str += "            <WebsocketUpdatePopup\n"
            output_str += "                title={title}\n"
            output_str += "                open={openWsPopup}\n"
            output_str += "                onClose={onClosePopup}\n"
            output_str += "                src={discardedChanges}\n"
            output_str += "            />\n"
        output_str += "        </Fragment>\n"
        output_str += "    )\n"
        output_str += "}\n"
        return output_str

    def __handle_const_on_layout(self, message_name: str, layout_type: str) -> str:
        message_name_camel_cased: str = message_name[0].lower() + message_name[1:]
        output_str = ""
        match layout_type:
            case JsxFileGenPlugin.repeated_root_type:
                output_str += "    /* global states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}, userChanges, discardedChanges, openWsPopup," \
                              " loading, error\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema, schemaCollections } = useSelector(state => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [mode, setMode] = useState(Modes.READ_MODE);\n"
                output_str += "    const [openConfirmSavePopup,] = useState(false);\n"
                output_str += "    const [filter, setFilter] = useState({});\n"
                output_str += "    const getAllWsDict = useRef({});\n"
            case JsxFileGenPlugin.root_type:
                output_str += "    /* global states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                              f"modified{message_name}, selected{message_name}Id,\n"
                output_str += "        userChanges, discardedChanges, openWsPopup, loading, error\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema, schemaCollections } = useSelector(state => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [mode, setMode] = useState(Modes.READ_MODE);\n"
                output_str += "    const [openConfirmSavePopup, setOpenConfirmSavePopup] = useState(false);\n"
                output_str += "    const getAllWsDict = useRef({});\n"
                output_str += "    const getWsDict = useRef({});\n"
            case JsxFileGenPlugin.non_root_type:
                message_name = self.root_message.proto.name
                message_name_camel_cased = message_name[0].lower() + message_name[1:]
                output_str += "    /* global states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                              f"modified{message_name}, selected{message_name}Id,\n"
                output_str += "        userChanges, loading, error, mode, createMode\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema, schemaCollections } = useSelector((state) => state.schema);\n"
            case JsxFileGenPlugin.abbreviated_type:
                output_str += "    /* global states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                              f"modified{message_name}, selected{message_name}Id,\n"
                output_str += "        loading, error\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                dependent_message = self.abbreviated_dependent_message_name
                dependent_message_camel_cased = dependent_message[0].lower() + dependent_message[1:]
                output_str += "    const {\n"
                output_str += f"        {dependent_message_camel_cased}Array, {dependent_message_camel_cased}, " \
                              f"modified{dependent_message}, selected{dependent_message}Id,\n"
                output_str += "        userChanges, discardedChanges, openWsPopup, mode, createMode, " \
                              "openConfirmSavePopup\n"
                output_str += "    } = useSelector(state => " + f"state.{dependent_message_camel_cased});\n"
                output_str += "    const { schema, schemaCollections } = useSelector((state) => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [searchValue, setSearchValue] = useState('');\n"
                output_str += f"    const previous{message_name} = usePrevious({message_name_camel_cased});\n"
                output_str += "    const getAllWsDict = useRef({});\n"
                output_str += "    const getWsDict = useRef({});\n"
                output_str += "    const socketDict = useRef({});\n"
                output_str += f"    const getAll{dependent_message}Dict = useRef(" + "{});\n"
        return output_str

    def handle_abbreviated_return(self, message_name: str, message_name_camel_cased: str) -> str:
        dependent_msg_name = self.abbreviated_dependent_message_name
        dependent_msg_name_camel_cased = dependent_msg_name[0].lower() + dependent_msg_name[1:]
        output_str = "    let createMenu = '';\n"
        output_str += "    if (mode === Modes.READ_MODE) {\n"
        output_str += "        createMenu = <Icon title='Create' name='Create' " \
                      "onClick={onCreate}><Add fontSize='small' /></Icon>;\n"
        output_str += "    }\n\n"
        output_str += "    let alertBubbleSource = null;\n"
        output_str += "    let alertBubbleColorSource = null;\n"
        output_str += "    if (collections.filter(col => col.hasOwnProperty('alertBubbleSource'))[0]) {\n"
        output_str += "        alertBubbleSource = collections.filter(col => col.hasOwnProperty(" \
                      "'alertBubbleSource'))[0].alertBubbleSource;\n"
        output_str += "        alertBubbleColorSource = collections.filter(col => col.hasOwnProperty(" \
                      "'alertBubbleSource'))[0].alertBubbleColor;\n"
        output_str += "    }\n\n"
        output_str += "    if (dependentName === alertBubbleSource.split('.')[0]) {\n"
        output_str += "        alertBubbleSource = alertBubbleSource.substring(alertBubbleSource.indexOf('.') + 1);\n"
        output_str += "        alertBubbleColorSource = alertBubbleColorSource.substring(" \
                      "alertBubbleColorSource.indexOf('.') + 1);\n"
        output_str += "    }\n\n"
        output_str += "    return (\n"
        output_str += "        <Fragment>\n"
        output_str += "            {createMode ? (\n"
        output_str += "                <WidgetContainer\n"
        output_str += "                    title={title}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    onSave={onSave}>\n"
        output_str += "                    <Divider textAlign='left'><Chip label='Staging' /></Divider>\n"
        output_str += "                    <List>\n"
        output_str += "                        {_.get(modified" + f"{message_name}" + ", loadedKeyName) && _.get(" \
                                                                                      "modified" + f"{message_name}" + ", loadedKeyName).map((item, index) => {\n"
        output_str += "                            let id = getIdFromAbbreviatedKey(abbreviated, item);\n"
        output_str += "                            if (id !== NEW_ITEM_ID) return;\n"
        output_str += "                            return (\n"
        output_str += "                                <ListItem key={index} " \
                      "selected={selected" + f"{dependent_msg_name}" + "Id === id} disablePadding>\n"
        output_str += "                                    <ListItemButton>\n"
        output_str += "                                        <ListItemText>{item}</ListItemText>\n"
        output_str += "                                    </ListItemButton>\n"
        output_str += "                                    <Icon title='Discard' onClick={onDiscard}><Delete " \
                      "fontSize='small' /></Icon>\n"
        output_str += "                                </ListItem>\n"
        output_str += "                            )\n"
        output_str += "                        })}\n"
        output_str += "                    </List>\n"
        output_str += "                </WidgetContainer>\n"
        output_str += "            ) : (\n"
        output_str += "                <AbbreviatedFilterWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        title: title,\n"
        output_str += "                        mode: mode,\n"
        output_str += "                        menu: createMenu,\n"
        output_str += "                        onChangeMode: onChangeMode,\n"
        output_str += "                        onSave: onSave,\n"
        output_str += "                        onReload: onReload\n"
        output_str += "                    }}\n"
        output_str += "                    name={props.name}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    schema={schema}\n"
        output_str += "                    bufferedKeyName={bufferedKeyName}\n"
        output_str += "                    bufferedLabel={collections.filter(col => " \
                      "col.key === bufferedKeyName)[0].title}\n"
        output_str += "                    searchValue={searchValue}\n"
        output_str += "                    options={_.get(" + f"{message_name_camel_cased}" + ", bufferedKeyName) ? " \
                                                                                              "_.get(" + f"{message_name_camel_cased}" + ", bufferedKeyName) : []}\n"
        output_str += "                    onChange={onChange}\n"
        output_str += "                    onLoad={onLoad}\n"
        output_str += "                    loadedKeyName={loadedKeyName}\n"
        output_str += "                    loadedLabel={collections.filter(col => col.key === " \
                      "loadedKeyName)[0].title}\n"
        output_str += "                    items={_.get(" + f"{message_name_camel_cased}" + ", loadedKeyName) ? " \
                                                                                            "_.get(" + f"{message_name_camel_cased}" + ", loadedKeyName) : []}\n"
        output_str += "                    selected={selected" + f"{dependent_msg_name}" + "Id}\n"
        output_str += "                    onSelect={onSelect}\n"
        output_str += "                    onUnload={onUnload}\n"
        output_str += "                    abbreviated={abbreviated}\n"
        output_str += "                    itemsMetadata={"f"{dependent_msg_name_camel_cased}" + "Array}\n"
        output_str += "                    itemSchema={dependentSchema}\n"
        output_str += "                    itemCollections={dependentCollections}\n"
        output_str += "                    dependentName={dependentName}\n"
        output_str += "                    alertBubbleSource={alertBubbleSource}\n"
        output_str += "                    alertBubbleColorSource={alertBubbleColorSource}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                />\n"
        output_str += "            )}\n"
        output_str += "            <ConfirmSavePopup\n"
        output_str += "                open={openConfirmSavePopup}\n"
        output_str += "                onClose={onCloseConfirmPopup}\n"
        output_str += "                onSave={onConfirmSave}\n"
        output_str += "                src={userChanges}\n"
        output_str += "            />\n"
        output_str += "            <WebsocketUpdatePopup\n"
        output_str += "                title={title}\n"
        output_str += "                open={openWsPopup}\n"
        output_str += "                onClose={onClosePopup}\n"
        output_str += "                src={discardedChanges}\n"
        output_str += "            />\n"
        output_str += "        </Fragment>\n"
        output_str += "    )\n"
        output_str += "}\n\n"

        return output_str

    def handle_jsx_const(self, message: protogen.Message, layout_type: str) -> str:
        output_str = self.handle_import_output(message, layout_type)
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        message_name_camel_cased = message_name[0].lower() + message_name[1:]
        root_message_name = ""
        root_message_name_camel_cased = ""
        dependent_message = ""
        dependent_message_camel_cased = ""
        output_str += f"const {message_name} = (props) => " + "{\n"
        output_str += self.__handle_const_on_layout(message_name, layout_type)
        output_str += "    /* dispatch to trigger redux actions */\n"
        output_str += "    const dispatch = useDispatch();\n\n"
        output_str += "    let currentSchema = _.get(schema, props.name);\n"
        output_str += "    let title = currentSchema ? currentSchema.title : props.name;\n"
        output_str += "    let collections = schemaCollections[props.name];\n"
        match layout_type:
            case JsxFileGenPlugin.repeated_root_type:
                output_str += "    let uiLimit = currentSchema.ui_get_all_limit;\n"
                output_str += f"    let originalData = applyFilter({message_name_camel_cased}, filter);\n"
                output_str += "    let modifiedData = addxpath(cloneDeep(originalData));\n"
                output_str += "    let rows = getTableRows(collections, originalData, modifiedData);\n"
            case JsxFileGenPlugin.root_type:
                output_str += f"    let rows = getTableRows(collections, {message_name_camel_cased}, " \
                              f"modified{message_name});\n"
            case JsxFileGenPlugin.non_root_type:
                root_message_name = self.root_message.proto.name
                root_message_name_camel_cased = root_message_name[0].lower() + root_message_name[1:]
                output_str += "    let currentSchemaXpath = null;\n"
                output_str += "    let isJsonRoot = _.keys(schema).length > 0 && currentSchema.json_root ? true : " \
                              "false;\n"
                output_str += "    /* not json root. load parent schema info */\n"
                output_str += "    let parentSchemaName = null;\n"
                output_str += "    if (!isJsonRoot) {\n"
                output_str += "        let currentSchemaPropname = lowerFirstLetter(props.name);\n"
                output_str += "        _.keys(_.get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {\n"
                output_str += "            let current = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);\n"
                output_str += "            if (current.type === DataTypes.OBJECT && _.has(current.properties, " \
                              "currentSchemaPropname)) {\n"
                output_str += "                parentSchemaName = SCHEMA_DEFINITIONS_XPATH + '.' + key;\n"
                output_str += "                currentSchemaXpath = currentSchemaPropname;\n"
                output_str += "            }\n"
                output_str += "            return;\n"
                output_str += "        })\n"
                output_str += "    }\n"
                output_str += f"    let rows = getTableRows(collections, {root_message_name_camel_cased}, " \
                              f"modified{root_message_name}, currentSchemaXpath);\n"
            case JsxFileGenPlugin.abbreviated_type:
                output_str += "    let bufferedKeyName = collections.filter(collection => " \
                              "collection.key.includes('buffer'))[0] ?\n"
                output_str += "        collections.filter(collection => collection.key.includes('buffer'))[0].key " \
                              ": null;\n"
                output_str += "    let loadedKeyName = collections.filter(collection => " \
                              "collection.key.includes('load'))[0] ?\n"
                output_str += "        collections.filter(collection => collection.key.includes('load'))[0].key " \
                              ": null;\n"
                output_str += '    let abbreviated = collections.filter(collection => collection.abbreviated && ' \
                              'collection.abbreviated !== "JSON")[0] ?\n'
                output_str += '        collections.filter(collection => collection.abbreviated && collection.' \
                              'abbreviated !== "JSON")[0].abbreviated : null;\n'
                output_str += '    let dependentName = abbreviated ? abbreviated.substring' \
                              '(abbreviated.indexOf(":") + 1).split(".")[0] : null;\n'
                output_str += "    let dependentSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, dependentName]);\n"
                output_str += "    let dependentCollections = " \
                              "createCollections(schema, dependentSchema, { mode: Modes.READ_MODE });\n\n"
        if layout_type != JsxFileGenPlugin.abbreviated_type:
            output_str += "    let tableColumns = getTableColumns(collections, mode, props.enableOverride, " \
                          "props.disableOverride);\n"
            output_str += "    let commonKeyCollections = getCommonKeyCollections(rows, tableColumns);\n\n"

        if layout_type != JsxFileGenPlugin.non_root_type:
            output_str += "    useEffect(() => {\n"
            output_str += "        /* fetch all objects. to be triggered only once when the component loads */\n"
            output_str += f"        dispatch(getAll{message_name}());\n"
            output_str += "    }, []);\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    useEffect(() => {\n"
            output_str += "        /* handles listening for new object. listens to creation of new objects added " \
                          "to array.\n"
            output_str += "         * if selectedId is not set, automatically listens to new object created. " \
                          "if multiple object are available,\n"
            output_str += "         * listens to the object with least id\n"
            output_str += "        */\n"
            output_str += f"        if ({message_name_camel_cased}Array.length > 0 && !selected{message_name}Id) " + \
                          "{\n"
            output_str += f"            let object = getObjectWithLeastId({message_name_camel_cased}Array);\n"
            output_str += f"            dispatch(setSelected{message_name}Id(object[DB_ID]));\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{message_name_camel_cased}Array])\n\n"

        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "    useEffect(() => {\n"
            output_str += "        /* on new update on original object from websocket/server, " \
                          "update the modified object\n"
            output_str += "         * from original object by adding xpath and applying any local " \
                          "pending changes if any\n"
            output_str += "        */\n"
            output_str += f"        let modifiedObj = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += "        _.keys(userChanges).map(xpath => {\n"
            output_str += "            _.set(modifiedObj, xpath, userChanges[xpath]);\n"
            output_str += "            return;\n"
            output_str += "        })\n"
            output_str += f"        dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += "    }" + f", [{message_name_camel_cased}])\n\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "    const applyUserChanges = (updatedData) => {\n"
            output_str += "        _.keys(userChanges).map(xpath => {\n"
            output_str += f"            if (userChanges[DB_ID] === selected{root_message_name}Id) " + "{\n"
            output_str += "                _.set(updatedData, xpath, userChanges[xpath]);\n"
            output_str += "            } else {\n"
            output_str += "                clearUserChanges();\n"
            output_str += "            }\n"
            output_str += "            return;\n"
            output_str += "        })\n"
            output_str += "    }\n\n"
            output_str += "    const clearUserChanges = () => {\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "    }\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        if (!createMode && selected{root_message_name}Id) " + "{\n"
            output_str += f"            let updatedObj = {root_message_name_camel_cased}Array.filter(strat => " \
                          f"strat[DB_ID] === selected{root_message_name}Id)[0];\n"
            output_str += "            if (updatedObj) {\n"
            output_str += f"                dispatch(set{root_message_name}(updatedObj));\n"
            output_str += "                let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
            output_str += "                applyUserChanges(modifiedObj);\n"
            output_str += f"                dispatch(setModified{root_message_name}(modifiedObj));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }" + f", [createMode, {root_message_name_camel_cased}Array, " \
                                    f"selected{root_message_name}Id])\n\n"
        elif layout_type == JsxFileGenPlugin.abbreviated_type:
            dependent_message = self.abbreviated_dependent_message_name
            dependent_message_camel_cased = dependent_message[0].lower() + dependent_message[1:]
            output_str += "    useEffect(() => {\n"
            output_str += "        /* on new update on original object from websocket/server, update the " \
                          "modified object\n"
            output_str += "         * from original object by adding xpath and applying any local " \
                          "pending changes if any\n"
            output_str += "        */\n"
            output_str += f"        let modifiedObj = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"        dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += f"        if (_.get({message_name_camel_cased}, loadedKeyName)) " + "{\n"
            output_str += f"            let loadedIds = _.get({message_name_camel_cased}, loadedKeyName).map(key => " \
                          "getIdFromAbbreviatedKey(abbreviated, key));\n"
            output_str += f"            let updatedArray = {dependent_message_camel_cased}Array.filter(strat => " \
                          "loadedIds.includes(strat[DB_ID]));\n"
            output_str += f"            dispatch(set{dependent_message}Array(updatedArray));\n"
            output_str += f"            if (_.get({message_name_camel_cased}, loadedKeyName).length > 0) " + "{\n"
            output_str += f"                let id = getIdFromAbbreviatedKey(abbreviated, " \
                          f"_.get({message_name_camel_cased}, loadedKeyName)[0]);\n"
            output_str += f"                dispatch(setSelected{dependent_message}Id(id));\n"
            output_str += "                return;\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{message_name_camel_cased}])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        if (!createMode && selected{dependent_message}Id) " + "{\n"
            output_str += f"            let modifiedObj = addxpath(cloneDeep({dependent_message_camel_cased}));\n"
            output_str += f"            dispatch(setModified{dependent_message}(modifiedObj));\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{dependent_message_camel_cased}, selected{dependent_message}Id, " \
                                    "createMode])\n\n"

        if layout_type != JsxFileGenPlugin.non_root_type:
            output_str += "    const flushGetAllWs = useCallback(() => {\n"
            output_str += "        /* apply get-all websocket changes */\n"
            output_str += "        if (_.keys(getAllWsDict.current).length > 0) {\n"
            if layout_type == JsxFileGenPlugin.repeated_root_type:
                output_str += f"            dispatch(set{message_name}Ws(" + \
                              "{ dict: cloneDeep(getAllWsDict.current), uiLimit }));\n"
            else:
                output_str += f"            dispatch(set{message_name}ArrayWs(cloneDeep(getAllWsDict.current)));\n"
            output_str += "            getAllWsDict.current = {};\n"
            output_str += "        }\n"
            output_str += "    }, [])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        /* get-all websocket. create a websocket client to listen to get-all interface */\n"
            output_str += "        let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}" \
                          f"/get-all-{message_name_snake_cased}-ws`);\n"
            output_str += "        socket.onmessage = (event) => {\n"
            output_str += "            let updatedData = JSON.parse(event.data);\n"
            output_str += "            if (Array.isArray(updatedData)) {\n"
            output_str += "                updatedData.forEach(o => {\n"
            output_str += "                    getAllWsDict.current[o[DB_ID]] = o;\n"
            output_str += "                })\n"
            output_str += "            } else if (_.isObject(updatedData)) {\n"
            output_str += "                getAllWsDict.current[updatedData[DB_ID]] = updatedData;\n"
            output_str += "            }\n"
            output_str += "            setTimeout(flushGetAllWs, 100);\n"
            output_str += "        }\n"
            output_str += "        socket.onclose = () => {\n"
            if layout_type == JsxFileGenPlugin.abbreviated_type:
                output_str += "            dispatch(setMode(Modes.DISABLED_MODE));\n"
            else:
                output_str += "            setMode(Modes.DISABLED_MODE);\n"
            output_str += "        }\n"
            output_str += "        /* close the websocket on cleanup */\n"
            output_str += "        return () => socket.close();\n"
            output_str += "    }, [])\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const flushGetWs = useCallback(() => {\n"
            output_str += "        /* apply get websocket changes */\n"
            output_str += "        if (_.keys(getWsDict.current).length > 0) {\n"
            output_str += f"            dispatch(set{message_name}Ws(" + "{ dict: cloneDeep(getWsDict.current)" \
                                                                         ", mode, collections }));\n"
            output_str += "            getWsDict.current = {};\n"
            output_str += "        }\n"
            output_str += "    }, [mode, collections])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        /* get websocket. create a websocket client to listen to selected obj interface */\n"
            output_str += f"        if (selected{message_name}Id) " + "{\n"
            output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}" \
                          f"/get-{message_name_snake_cased}-ws/$" + "{selected" + f"{message_name}" + "Id}`);\n"
            output_str += "            socket.onmessage = (event) => {\n"
            output_str += "                let updatedObj = JSON.parse(event.data);\n"
            output_str += "                getWsDict.current[updatedObj[DB_ID]] = updatedObj;\n"
            output_str += "                setTimeout(flushGetWs, 100);\n"
            output_str += "            }\n"
            output_str += "            /* close the websocket on cleanup */\n"
            output_str += "            return () => socket.close();\n"
            output_str += "        }\n"
            output_str += "    }" + f", [selected{message_name}Id])\n\n"

        if layout_type == JsxFileGenPlugin.abbreviated_type:
            abbreviated_dependent_msg_snake_cased = \
                convert_camel_case_to_specific_case(self.abbreviated_dependent_message_name)
            output_str += f"    const flush{dependent_message}GetAllWs = useCallback(() => " + "{\n"
            output_str += "        /* apply get-all websocket changes */\n"
            output_str += f"        if (_.keys(getAll{dependent_message}Dict.current).length > 0) " + "{\n"
            output_str += f"            dispatch(set{dependent_message}ArrayWs("
            output_str += "{" + f" dict: cloneDeep(getAll{dependent_message}Dict.current), mode, collections: " \
                                "dependentCollections }));\n"
            output_str += f"            getAll{dependent_message}Dict.current = " + "{};\n"
            output_str += "        }\n"
            output_str += "    }, [mode, dependentCollections])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        let loadedKeys = _.get({message_name_camel_cased}, loadedKeyName);\n"
            output_str += f"        if (loadedKeys && !_.isEqual({message_name_camel_cased}, " \
                          f"previous{message_name})) " + "{\n"
            output_str += "            loadedKeys.forEach(key => {\n"
            output_str += "                let id = getIdFromAbbreviatedKey(abbreviated, key);\n"
            output_str += "                let socket = socketDict.current.hasOwnProperty(id) ? " \
                          "socketDict.current[id] : null;\n"
            output_str += "                if (!socket || (socket.readyState === WebSocket.CLOSING || " \
                          "socket.readyState === WebSocket.CLOSED)) {\n"
            output_str += "                    if (socket) socket.close();\n"
            output_str += "                    socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}" \
                          f"/get-{abbreviated_dependent_msg_snake_cased}-ws/$" + "{id}`);\n"
            output_str += "                    socket.onmessage = (event) => {\n"
            output_str += "                        let updatedObj = JSON.parse(event.data);\n"
            output_str += f"                        getAll{dependent_message}Dict.current[updatedObj[DB_ID]] = " \
                          f"updatedObj;\n"
            output_str += f"                        setTimeout(flush{dependent_message}GetAllWs, 100);\n"
            output_str += "                    }\n"
            output_str += "                    socket.onclose = () => {\n"
            output_str += "                        delete socketDict.current[id];\n"
            output_str += "                    }\n"
            output_str += "                    socketDict.current = { ...socketDict.current, [id]: socket };\n"
            output_str += "                }\n"
            output_str += "                /* close the websocket on cleanup */\n"
            output_str += "                return () => socket.close();\n"
            output_str += "            })\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{message_name_camel_cased}])\n\n"

        output_str += "    /* if loading, render the skeleton view */\n"
        output_str += "    if (loading) {\n"
        output_str += "        return (\n"
        output_str += "            <SkeletonField title={title} />\n"
        output_str += "        )\n"
        output_str += "    }\n\n"
        output_str += "    /* if get-all websocket is disconnected, render connection lost view */\n"
        output_str += "    if (mode === Modes.DISABLED_MODE) {\n"
        output_str += "        return (\n"
        output_str += "            <WidgetContainer title={title}>\n"
        output_str += "                <h1>Connection lost. Please refresh...</h1>\n"
        output_str += "            </WidgetContainer>\n"
        output_str += "        )\n"
        output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    /* required fields (loaded & buffered) not found. render error view */\n"
            output_str += "    if (!bufferedKeyName || !loadedKeyName || !abbreviated) {\n"
            output_str += "        return (\n"
            output_str += "            <Box>{Layouts.ABBREVIATED_FILTER_LAYOUT} not supported. " \
                          "Required fields not found.</Box>\n"
            output_str += "        )\n"
            output_str += "    }\n\n"

        output_str += "    const onResetError = () => {\n"
        output_str += "        dispatch(resetError());\n"
        output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const onChangeMode = () => {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        setMode(Modes.EDIT_MODE);\n"
            else:
                output_str += "        dispatch(setMode(Modes.EDIT_MODE));\n"
            output_str += "    }\n\n"

        if layout_type != JsxFileGenPlugin.repeated_root_type:
            output_str += "    const onSave = (e, openPopup = false) => {\n"
            output_str += "        /* if save event is triggered from button (openPopup is true), " \
                          "open the confirm save dialog.\n"
            output_str += "         * if user local changes is present, open confirm save dialog for confirmation,\n"
            output_str += "         * otherwise call confirmSave to reset states\n"
            output_str += "        */\n"
            output_str += "        if (e === null && openPopup) {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "            setOpenConfirmSavePopup(true);\n"
            else:
                output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
            output_str += "            return;\n"
            output_str += "        }\n"
            if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:

                output_str += "        if (_.keys(userChanges).length > 0) {\n"
                if layout_type == JsxFileGenPlugin.root_type:
                    output_str += "            setOpenConfirmSavePopup(true);\n"
                else:
                    output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
                output_str += "        } else {\n"
                output_str += "            onConfirmSave();\n"
                output_str += "        }\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "    const onUpdate = (updatedData) => {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            else:
                output_str += f"        dispatch(setModified{root_message_name}(updatedData));\n"
            output_str += "    }\n\n"

        if layout_type != JsxFileGenPlugin.repeated_root_type:
            output_str += "    const onButtonToggle = (e, xpath, value) => {\n"
            output_str += "        dispatch(setUserChanges({\n"
            output_str += "            ...userChanges,\n"
            output_str += "            [xpath]: value\n"
            output_str += "        }));\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += f"        if ({message_name_camel_cased}[DB_ID]) " + "{\n"
            elif layout_type == JsxFileGenPlugin.non_root_type:
                output_str += f"        if ({root_message_name_camel_cased}[DB_ID]) " + "{\n"
            else:
                output_str += f"        if ({dependent_message_camel_cased}[DB_ID]) " + "{\n"
            output_str += "            onSave(null, true);\n"
            output_str += "        }\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const onClosePopup = (e, reason) => {\n"
            output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
            output_str += "        dispatch(setOpenWsPopup(false));\n"
            output_str += "    }\n\n"
            output_str += "    const onCloseConfirmPopup = (e, reason) => {\n"
            output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
            output_str += "        onReload();\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        setOpenConfirmSavePopup(false);\n"
            else:
                output_str += "        dispatch(setOpenConfirmSavePopup(false));\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "    const onSave = () => { }\n\n"
            output_str += "    const onUpdate = () => { }\n\n"
            output_str += "    const onButtonToggle = () => { }\n\n"
            output_str += "    const onReload = () => {\n"
            output_str += f"        dispatch(getAll{message_name}());\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => { }\n\n"
            output_str += "    const onClosePopup = () => { }\n\n"
            output_str += "    const onCloseConfirmPopup = () => { }\n\n"
            output_str += "    const onUserChange = () => { }\n\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += "    const onReload = () => {\n"
            output_str += f"        if (selected{message_name}Id) " + "{\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        } else {\n"
            output_str += f"            dispatch(getAll{message_name}());\n"
            output_str += "        }\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onCreate = () => {\n"
            output_str += "        let updatedObj = generateObjectFromSchema(schema, _.get(schema, props.name));\n"
            output_str += "        updatedObj = addxpath(updatedObj);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedObj));\n"
            output_str += "        let changesDict = getXpathKeyValuePairFromObject(updatedObj);\n"
            output_str += "        dispatch(setUserChanges(changesDict));\n"
            output_str += "        setMode(Modes.EDIT_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => {\n"
            output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{message_name}));\n"
            output_str += f"        if (!_.isEqual({message_name_camel_cased}, modifiedObj)) " + "{\n"
            output_str += f"            if (_.get({message_name_camel_cased}, DB_ID)) " + "{\n"
            output_str += f"                let updatedObj = createObjectFromDict({message_name_camel_cased}, " \
                          "userChanges);\n"
            output_str += f"                dispatch(update{message_name}(updatedObj));\n"
            output_str += "            } else {\n"
            output_str += f"                dispatch(create{message_name}(modifiedObj));\n"
            output_str += "            }\n"
            output_str += "        } else if (_.keys(userChanges).length === 1) {\n"
            output_str += f"            let updatedObj = createObjectFromDict({message_name_camel_cased}, " \
                          "userChanges);\n"
            output_str += f"            dispatch(update{message_name}(updatedObj));\n"
            output_str += "        }\n"
            output_str += "        /* reset states */\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "        setOpenConfirmSavePopup(false);\n"
            output_str += "    }\n\n"
        elif layout_type == JsxFileGenPlugin.abbreviated_type:
            abbreviated_dependent_msg_camel_cased = self.abbreviated_dependent_message_name[0].lower() + \
                                                    self.abbreviated_dependent_message_name[1:]
            output_str += "    const onReload = () => {\n"
            output_str += f"        if (selected{message_name}Id) " + "{\n"
            output_str += f"            let modifiedObj = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += "        } else {\n"
            output_str += f"            dispatch(getAll{message_name}());\n"
            output_str += "        }\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += f"        if (selected{dependent_message}Id) " + "{\n"
            output_str += f"            let modifiedObj = addxpath(cloneDeep({abbreviated_dependent_msg_camel_cased}))"\
                          ";\n"
            output_str += f"            dispatch(setModified{self.abbreviated_dependent_message_name}(modifiedObj));\n"
            output_str += "        }\n"
            output_str += "        dispatch(setCreateMode(false));\n"
            output_str += "        setSearchValue('');\n"
            output_str += "    }\n\n"
            output_str += "    const onCreate = () => {\n"
            output_str += f"        let updatedObj = generateObjectFromSchema(schema, dependentSchema);\n"
            output_str += "        _.set(updatedObj, DB_ID, NEW_ITEM_ID);\n"
            output_str += "        updatedObj = addxpath(updatedObj);\n"
            output_str += f"        dispatch(setModified{self.abbreviated_dependent_message_name}(updatedObj));\n"
            output_str += f"        dispatch(reset{self.abbreviated_dependent_message_name}());\n"
            output_str += "        dispatch(setCreateMode(true));\n"
            output_str += "        dispatch(setMode(Modes.EDIT_MODE));\n"
            output_str += f"        dispatch(setSelected{self.abbreviated_dependent_message_name}Id(NEW_ITEM_ID));\n"
            output_str += "        let newItem = getNewItem(dependentCollections, abbreviated);\n"
            output_str += f"        let modifiedObj = cloneDeep(modified{message_name});\n"
            output_str += "        _.get(modifiedObj, loadedKeyName).push(newItem);\n"
            output_str += f"        dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => {\n"
            output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{dependent_message}));\n"
            output_str += "        if (createMode) {\n"
            output_str += "            dispatch(setCreateMode(false));\n"
            output_str += "            delete modifiedObj[DB_ID];\n"
            output_str += "        }\n"
            output_str += f"        if (!_.isEqual({dependent_message_camel_cased}, modifiedObj)) " + "{\n"
            output_str += f"            if (_.get({dependent_message_camel_cased}, DB_ID)) " + "{\n"
            output_str += f"                let updatedObj = createObjectFromDict({dependent_message_camel_cased}, " \
                          "userChanges);\n"
            output_str += f"                dispatch(update{dependent_message}(updatedObj));\n"
            output_str += "            } else {\n"
            output_str += f"                dispatch(create{dependent_message}(" \
                          "{ data: modifiedObj, abbreviated, loadedKeyName }));\n"
            output_str += "            }\n"
            output_str += "        } else if (_.keys(userChanges).length === 1) {\n"
            output_str += f"            let updatedObj = createObjectFromDict({dependent_message_camel_cased}, " \
                          "userChanges);\n"
            output_str += f"            dispatch(update{dependent_message}(updatedObj));\n"
            output_str += "        }\n"
            output_str += "        /* reset states */\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "        dispatch(setOpenConfirmSavePopup(false));\n"
            output_str += "    }\n\n"
            output_str += "    const onChange = (e, value) => {\n"
            output_str += "        setSearchValue(value);\n"
            output_str += "    }\n\n"
            output_str += "    const onLoad = () => {\n"
            output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
            output_str += f"        let index = _.get({message_name_camel_cased}, bufferedKeyName).indexOf(" \
                          f"searchValue);\n"
            output_str += "        _.get(updatedData, bufferedKeyName).splice(index, 1);\n"
            output_str += "        _.get(updatedData, loadedKeyName).push(searchValue);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            output_str += f"        dispatch(update{message_name}(updatedData));\n"
            output_str += "        let id = getIdFromAbbreviatedKey(abbreviated, searchValue);\n"
            output_str += f"        setSelected{self.abbreviated_dependent_message_name}Id(id);\n"
            output_str += "        setSearchValue('');\n"
            output_str += "    }\n\n"
            output_str += "    const onUnload = (id) => {\n"
            output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
            output_str += f"        let abbreviatedKey = getAbbreviatedKeyFromId(_.get({message_name_camel_cased}, " \
                          f"loadedKeyName), abbreviated, id);\n"
            output_str += f"        let index = _.get({message_name_camel_cased}, " \
                          "loadedKeyName).indexOf(abbreviatedKey);\n"
            output_str += f"        let socket = socketDict.current[id];\n"
            output_str += "        if (socket) {\n"
            output_str += f"            socket.close();\n"
            output_str += "        }\n"
            output_str += f"        _.get(updatedData, loadedKeyName).splice(index, 1);\n"
            output_str += f"        _.get(updatedData, bufferedKeyName).push(abbreviatedKey);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        dispatch(update" + f"{message_name}(updatedData));\n"
            output_str += "    }\n\n"
            output_str += "    const onDiscard = () => {\n"
            output_str += "        onReload();\n"
            output_str += "    }\n\n"
            output_str += "    const onSelect = (id) => {\n"
            output_str += "        id = id * 1;\n"
            output_str += f"        dispatch(setSelected{dependent_message}Id(id));\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "    const onUserChange = (xpath, value, deleted = false, keyValueDict) => {\n"
            output_str += "        let updatedData = cloneDeep(userChanges);\n"
            output_str += "        if (deleted && keyValueDict) {\n"
            if layout_type == self.non_root_type:
                output_str += f"            updatedData[DB_ID] = selected{root_message_name}Id;\n"
            output_str += "            if (updatedData.deleted) {\n"
            output_str += "                updatedData.deleted = { ...updatedData.deleted, ...keyValueDict };\n"
            output_str += "            } else {\n"
            output_str += "                updatedData.deleted = keyValueDict;\n"
            output_str += "            }\n"
            output_str += "        } else {\n"
            output_str += "            if (keyValueDict) {\n"
            if layout_type == self.root_type:
                output_str += "                updatedData = { ...updatedData, ...keyValueDict };\n"
            else:
                output_str += "                updatedData = { ...updatedData, ...keyValueDict, [DB_ID]: " \
                              f"selected{root_message_name}Id " + "};\n"
            output_str += "            } else {\n"
            if layout_type == self.root_type:
                output_str += "                updatedData = { ...updatedData, [xpath]: value };\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "        dispatch(setUserChanges(updatedData));\n"
            else:
                output_str += "                updatedData = { ...updatedData, [xpath]: value, [DB_ID]: " \
                              f"selected{root_message_name}Id " + "};\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "        dispatch(setUserChanges(updatedData));\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += self.handle_abbreviated_return(message_name, message_name_camel_cased)
        else:
            output_str += self.handle_non_abbreviated_return(message_name, message_name_camel_cased, layout_type)
        output_str += f"export default memo({message_name}, isEqual);\n\n"

        return output_str

    def handle_jsx_file_convert(self, file: protogen.File) -> Dict[str, str]:
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
        output_dict: Dict[str, str] = {}

        for message in self.layout_msg_list:
            self.root_message = None
            message_name = message.proto.name
            output_dict_key = f"{message_name}.jsx"
            # Abbreviated Case
            if message in self.abbreviated_filter_layout_msg_list:
                self.root_message = message
                for field in message.fields:
                    # It's assumed that abbreviated layout type will also have  some field having flux_fld_abbreviated
                    # set to get abbreviated dependent message name
                    if JsxFileGenPlugin.flux_fld_abbreviated in str(field.proto.options):
                        fld_abbreviated_option_value = \
                            self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                             JsxFileGenPlugin.flux_fld_abbreviated)[1:]
                        break
                else:
                    err_str = f"Could not find any field having {JsxFileGenPlugin.flux_fld_abbreviated} option set in " \
                              f"message {message_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                abb_dependent_msg_name = fld_abbreviated_option_value.split(".")[0]
                if ":" in abb_dependent_msg_name:
                    abb_dependent_msg_name = abb_dependent_msg_name.split(":")[-1]
                self.abbreviated_dependent_message_name = abb_dependent_msg_name
                output_str = self.handle_jsx_const(message, JsxFileGenPlugin.abbreviated_type)
            else:
                # Root Type
                if message in self.root_msg_list:
                    self.root_message = message
                    if message in self.repeated_tree_layout_msg_list or message in self.repeated_table_layout_msg_list:
                        output_str = self.handle_jsx_const(message, JsxFileGenPlugin.repeated_root_type)
                    else:
                        output_str = self.handle_jsx_const(message, JsxFileGenPlugin.root_type)
                # Non Root Type
                else:
                    for msg in self.root_msg_list:
                        if message.proto.name in [fld.message.proto.name for fld in msg.fields if
                                                  fld.message is not None]:
                            self.root_message = msg
                            break
                        # else not required: Avoiding msg not having any field of type message
                    else:
                        err_str = f"Could not find {message.proto.name} as datatype of field in any root " \
                                  f"message in proto"
                        logging.exception(err_str)
                        raise Exception(err_str)
                    if message in self.repeated_table_layout_msg_list or message in self.repeated_tree_layout_msg_list:
                        output_str = self.handle_jsx_const(message, JsxFileGenPlugin.repeated_non_root_type)
                    else:
                        output_str = self.handle_jsx_const(message, JsxFileGenPlugin.non_root_type)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsxFileGenPlugin)
