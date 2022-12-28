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


class JsxFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    -- Types:
    ----- 1. Json Root and Layout type as table or tree
    ----- 2. Non-Root Type and Layout as table or tree
    ----- 3. Layout as Abbreviated Type
    """
    root_type: str = 'RootType'
    non_root_type: str = 'NonRootType'
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
        output_str = "import React, { Fragment, useEffect, useState } from 'react';\n"
        output_str += "import { useSelector, useDispatch } from 'react-redux';\n"
        output_str += "import _, { cloneDeep } from 'lodash';\n"
        output_str += "import { makeStyles } from '@mui/styles';\n"
        if layout_type == JsxFileGenPlugin.root_type:
            message_name = message.proto.name
            output_str += "import { Modes, Layouts, DB_ID, SCHEMA_DEFINITIONS_XPATH, DataTypes, API_ROOT_URL } " \
                          "from '../constants';\n"
        else:
            message_name = self.root_message.proto.name
            output_str += "import { Modes, Layouts, DB_ID, SCHEMA_DEFINITIONS_XPATH, DataTypes, " \
                          "API_ROOT_URL, NEW_ITEM_ID } from " \
                          "'../constants';\n"
        message_name_camel_cased = message_name[0].lower() + message_name[1:]
        if layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "import {\n"
            output_str += f"    getAll{message_name}, get{message_name}, create{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}, reset{message_name}, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetSelected{message_name}Id, resetError"
            output_str += ", setUserChanges, setDiscardedChanges\n"
        else:
            output_str += "import {\n"
            output_str += f"    getAll{message_name}, get{message_name}, create{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}Array, set{message_name}, reset{message_name}, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetSelected{message_name}Id, resetError"
            output_str += "\n"
        output_str += "}" + f" from '../features/{message_name_camel_cased}Slice';\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            dependent_message_name = self.abbreviated_dependent_message_name
            dependent_message_name_camel_cased = dependent_message_name[0].lower() + dependent_message_name[1:]
            output_str += "import {\n"
            output_str += f"    getAll{dependent_message_name}, get{dependent_message_name}, " \
                          f"create{dependent_message_name}, update{dependent_message_name},\n"
            output_str += f"    set{dependent_message_name}Array, reset{dependent_message_name}, " \
                          f"setModified{dependent_message_name}, setSelected{dependent_message_name}Id, " \
                          f"resetSelected{dependent_message_name}Id, setMode, setCreateMode, " \
                          f"setUserChanges, setDiscardedChanges\n"
            output_str += "}"+f" from '../features/{dependent_message_name_camel_cased}Slice';\n"
            output_str += "import { createCollections, generateObjectFromSchema, addxpath, clearxpath, " \
                          "lowerFirstLetter, getNewItem, compareObjects, getObjectWithLeastId, " \
                          "getIdFromAbbreviatedKey, hasxpath } from '../utils';\n"
            output_str += "import SkeletonField from '../components/SkeletonField';\n"
            output_str += "import WidgetContainer from '../components/WidgetContainer';\n"
            output_str += "import AbbreviatedFilterWidget from '../components/AbbreviatedFilterWidget';\n"
            output_str += "import { Divider, List, ListItem, ListItemButton, ListItemText, Chip, Box } from " \
                          "'@mui/material';\n"
            output_str += "import Icon from '../components/Icon';\n"
            output_str += "import { Add, Delete } from '@mui/icons-material';\n"
            output_str += "import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } " \
                          "from '@mui/material';\n"
            output_str += "\n"
        else:
            output_str += "import { \n"
            output_str += "    createCollections, generateObjectFromSchema, addxpath, clearxpath, lowerFirstLetter, \n"
            output_str += "    generateRowTrees, compareObjects, getObjectWithLeastId, hasxpath, " \
                          "getTableColumns, getTableRows, getCommonKeyCollections\n"
            output_str += "} from '../utils';\n"
            output_str += "import SkeletonField from '../components/SkeletonField';\n"
            output_str += "import TreeWidget from '../components/TreeWidget';\n"
            output_str += "import TableWidget from '../components/TableWidget';\n"
            output_str += "import Icon from '../components/Icon';\n"
            output_str += "import { Add } from '@mui/icons-material';\n"
            output_str += "import DynamicMenu from '../components/DynamicMenu';\n"
            output_str += "import { Button, Dialog, DialogActions, DialogContent, DialogContentText, " \
                          "DialogTitle } from '@mui/material';\n"
            output_str += "\n"

        return output_str

    def handle_non_abbreviated_return(self, message_name: str, message_name_camel_cased: str, layout_type: str) -> str:
        output_str = "    const onUserChange = (xpath, value) => {\n"
        if layout_type == self.root_type:
            output_str += "        setUserChanges({ ...userChanges, [xpath]: value });\n"
        else:
            output_str += "        dispatch(setUserChanges({ ...userChanges, [xpath]: value, [DB_ID]: " + \
                          f"selected{self.root_message.proto.name}Id "+"}));\n"
        output_str += "    }\n\n"
        output_str += "    const onClosePopup = (e, reason) => {\n"
        output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
        output_str += "        setOpenPopup(false);\n"
        if layout_type == self.root_type:
            output_str += f"        let trees = generateRowTrees(cloneDeep({message_name_camel_cased}), collections);\n"
            output_str += f"        let modifiedTrees = generateRowTrees(cloneDeep(modified{message_name})" \
                          f", collections);\n"
            output_str += "        if (trees.length !== modifiedTrees.length) {\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        } else {\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += "            _.keys(userChanges).map(xpath => {\n"
            output_str += "                _.set(updatedData, xpath, userChanges[xpath]);\n"
            output_str += "            })\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        }\n"
            output_str += "    }\n\n"
            output_str += "    let menu = <DynamicMenu collections={collections} commonKeyCollections=" \
                          "{commonKeyCollections} data=" \
                          "{modified"+f"{message_name}" + \
                          "} disabled={mode !== Modes.EDIT_MODE} onButtonToggle={onButtonToggle} />;\n"
            output_str += "    if (isJsonRoot) {\n"
            output_str += "        menu = (\n"
            output_str += "            <DynamicMenu collections={collections} " \
                          "commonKeyCollections={commonKeyCollections} data={modified"+f"{message_name}" \
                          "} disabled={mode !== Modes.EDIT_MODE} onButtonToggle={onButtonToggle}>\n"
            output_str += "                {mode === Modes.READ_MODE && _.keys("+f"{message_name_camel_cased})." \
                          f"length === 0 && _.keys(modified{message_name}).length === 0 &&\n"
            output_str += "                    <Icon className={classes.icon} title='Create' onClick={onCreate}" \
                          "><Add fontSize='small' /></Icon>}\n"
            output_str += "            </DynamicMenu>\n"
            output_str += "        )\n"
            output_str += "    }\n\n"

        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str += f"        let trees = generateRowTrees(cloneDeep({root_message_name_camel_cased}), " \
                          "collections, currentSchemaXpath);\n"
            output_str += f"        let modifiedTrees = generateRowTrees(" \
                          f"cloneDeep(modified{root_msg_name}), " \
                          f"collections, currentSchemaXpath);\n"
            output_str += "        if (trees.length !== modifiedTrees.length) {\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({root_message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{root_msg_name}(updatedData));\n"
            output_str += f"            clearUserChanges();\n"
            output_str += "        } else {\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({root_message_name_camel_cased}));\n"
            output_str += "            applyUserChanges(updatedData);\n"
            output_str += "            dispatch(setDiscardedChanges({}));\n"
            output_str += f"            dispatch(setModified{root_msg_name}(updatedData));\n"
            output_str += "        }\n"
            output_str += "    }\n\n"
            output_str += "    let menu = <DynamicMenu disabled={mode !== Modes.EDIT_MODE} collections=" \
                          "{collections} commonKeyCollections={commonKeyCollections}" \
                          " data={_.get(modified"+f"{root_msg_name}" + \
                          ", currentSchemaXpath)} onButtonToggle={onButtonToggle} />;\n"
        output_str += "    return (\n"
        output_str += "        <Fragment>\n"
        output_str += "            {layout === Layouts.TABLE_LAYOUT ? (\n"
        output_str += "                <TableWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        title: title,\n"
        output_str += "                        mode: mode,\n"
        output_str += "                        layout: layout,\n"
        output_str += "                        menu: menu,\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "                        onChangeMode: onChangeMode,\n"
            output_str += "                        onChangeLayout: onChangeLayout,\n"
            output_str += "                        onSave: onSave,\n"
            output_str += "                        onReload: onReload\n"
            output_str += "                    }}\n"
            output_str += "                    name={props.name}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified"+f"{message_name}"+"}\n"
            output_str += "                    originalData={"+f"{message_name_camel_cased}"+"}\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str += "                        onChangeLayout: onChangeLayout\n"
            output_str += "                    }}\n"
            output_str += "                    name={parentSchemaName}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified"+f"{root_msg_name}"+"}\n"
            output_str += "                    originalData={"+f"{root_message_name_camel_cased}"+"}\n"
        output_str += "                    collections={collections}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    onUpdate={onUpdate}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        if layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "                    xpath={currentSchemaXpath}\n"
        output_str += "                    onUserChange={onUserChange}\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                />\n"
        output_str += "            ) : layout === Layouts.TREE_LAYOUT ? (\n"
        output_str += "                <TreeWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        title: title,\n"
        output_str += "                        mode: mode,\n"
        output_str += "                        layout: layout,\n"
        output_str += "                        menu: menu,\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "                        onChangeMode: onChangeMode,\n"
            output_str += "                        onChangeLayout: onChangeLayout,\n"
            output_str += "                        onSave: onSave,\n"
            output_str += "                        onReload: onReload\n"
            output_str += "                    }}\n"
            output_str += "                    name={props.name}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified"+f"{message_name}"+"}\n"
            output_str += "                    originalData={"+f"{message_name_camel_cased}"+"}\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = root_msg_name[0].lower() + root_msg_name[1:]
            output_str += "                        onChangeLayout: onChangeLayout,\n"
            output_str += "                    }}\n"
            output_str += "                    name={parentSchemaName}\n"
            output_str += "                    schema={schema}\n"
            output_str += "                    data={modified"+f"{root_msg_name}"+"}\n"
            output_str += "                    originalData={"+f"{root_message_name_camel_cased}"+"}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    onUpdate={onUpdate}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        if layout_type == self.non_root_type:
            output_str += "                    xpath={currentSchemaXpath}\n"
        output_str += "                    onUserChange={onUserChange}\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                />\n"
        output_str += "            ) : (\n"
        output_str += "                <h1>Unsupported Layout</h1>\n"
        output_str += "            )}\n"
        output_str += "            <Dialog open={openPopup} onClose={onClosePopup}>\n"
        output_str += "                <DialogTitle>{title} Change Detected</DialogTitle>\n"
        output_str += "                <DialogContent>\n"
        output_str += "                    <DialogContentText>New change detected from server. Your changes " \
                      "may be lost. Following changes are discarded:</DialogContentText>\n"
        output_str += "                    {Object.keys(discardedChanges).map(xpath => (\n"
        output_str += "                        <DialogContentText>{xpath}: " \
                      "{discardedChanges[xpath]}</DialogContentText>\n"
        output_str += "                    ))}\n"
        output_str += "                </DialogContent>\n"
        output_str += "                <DialogActions>\n"
        output_str += "                    <Button onClick={onClosePopup} autoFocus>OK</Button>\n"
        output_str += "                </DialogActions>\n"
        output_str += "            </Dialog>\n"
        output_str += "        </Fragment>\n"
        output_str += "    )\n"
        output_str += "}\n"
        return output_str

    def __handle_const_on_layout(self, message_name: str, layout_type: str) -> str:
        message_name_camel_cased: str = message_name[0].lower() + message_name[1:]
        output_str = ""
        match layout_type:
            case JsxFileGenPlugin.root_type:
                output_str += "    const { "+f"{message_name_camel_cased}Array, {message_name_camel_cased}, modified{message_name}, selected{message_name}Id, loading, error "+"} = useSelector(state => "+f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema } = useSelector(state => state.schema);\n"
                output_str += "    const [mode, setMode] = useState(Modes.READ_MODE);\n"
                output_str += "    const [layout, setLayout] = useState(Layouts.UNSPECIFIED);\n"
                output_str += "    const [websocket, setWebsocket] = useState();\n"
                output_str += "    const [getAllWebsocket, setGetAllWebsocket] = useState();\n"
                output_str += "    const [userChanges, setUserChanges] = useState({});\n"
                output_str += "    const [discardedChanges, setDiscardedChanges] = useState({})\n"
                output_str += "    const [openPopup, setOpenPopup] = useState(false);\n"
            case JsxFileGenPlugin.non_root_type:
                message_name = self.root_message.proto.name
                message_name_camel_cased = message_name[0].lower() + message_name[1:]
                output_str += "    const { "+f"{message_name_camel_cased}Array, {message_name_camel_cased}, " \
                                             f"modified{message_name}, selected{message_name}Id, loading, error, " \
                                             f"mode, createMode, userChanges, discardedChanges " + \
                                             "}"+f" = useSelector((state) => " \
                                             f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema } = useSelector((state) => state.schema);\n"
                output_str += "    const [layout, setLayout] = useState(Layouts.TABLE_LAYOUT);\n"
                output_str += "    const [websocket, setWebsocket] = useState();\n"
                output_str += "    const [openPopup, setOpenPopup] = useState(false);\n\n"
            case JsxFileGenPlugin.abbreviated_type:
                output_str += "    const {"+f" {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                                            f"modified{message_name}, selected{message_name}Id, loading, error " + \
                              "}"+f" = useSelector(state => state.{message_name_camel_cased});\n"
                dependent_message = self.abbreviated_dependent_message_name
                dependent_mesaage_camel_cased = dependent_message[0].lower() + dependent_message[1:]
                output_str += "    const {"+f" {dependent_mesaage_camel_cased}Array, {dependent_mesaage_camel_cased}," \
                                            f" modified{dependent_message}, selected{dependent_message}Id, mode, " \
                                            f"createMode "+"}"+f" = useSelector(state => " \
                                                               f"state.{dependent_mesaage_camel_cased});\n"
                output_str += "    const { schema } = useSelector((state) => state.schema);\n"
                output_str += "    const [layout, setLayout] = useState(Layouts.UNSPECIFIED);\n"
                output_str += "    const [searchValue, setSearchValue] = useState('');\n"
                output_str += "    const [websocket, setWebsocket] = useState();\n"
                output_str += "    const [getAllWebsocket, setGetAllWebsocket] = useState();\n"
                output_str += f"    const [{dependent_mesaage_camel_cased}GetAllWebsocket, " \
                              f"set{dependent_message}GetAllWebsocket] = useState();\n"
                output_str += "    const [openPopup, setOpenPopup] = useState(false);\n\n"
        return output_str

    def handle_abbriviated_return(self, message_name: str, message_name_camel_cased: str) -> str:
        dependent_msg_name = self.abbreviated_dependent_message_name
        dependent_msg_name_camel_cased = dependent_msg_name[0].lower() + dependent_msg_name[1:]
        output_str = "    const onUnload = (value) => {\n"
        output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
        output_str += f"        let index = _.get({message_name_camel_cased}, loadedKeyName).indexOf(value);\n"
        output_str += f"        _.get(updatedData, loadedKeyName).splice(index, 1);\n"
        output_str += f"        _.get(updatedData, bufferedKeyName).push(value);\n"
        output_str += "        dispatch(update"+f"{message_name}(updatedData));\n"
        output_str += f"        dispatch(reset{dependent_msg_name}());\n"
        output_str += f"        dispatch(resetSelected{dependent_msg_name}Id());\n"
        output_str += "    }\n\n"
        output_str += "    const onDiscard = () => {\n"
        output_str += "        dispatch(setCreateMode(false));\n"
        output_str += f"        dispatch(setModified{message_name}({message_name_camel_cased}));\n"
        output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
        output_str += "        dispatch(setUserChanges({}));\n"
        output_str += "        dispatch(setDiscardedChanges({}));\n"
        output_str += "    }\n\n"
        output_str += "    const onSelect = (id) => {\n"
        output_str += "        id = id * 1;\n"
        output_str += f"        dispatch(setSelected{dependent_msg_name}Id(id));\n"
        output_str += "    }\n\n"
        output_str += "    const onClosePopup = (e, reason) => {\n"
        output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
        output_str += "        setOpenPopup(false);\n"
        output_str += "    }\n\n"
        output_str += "    const onButtonToggle = (e, xpath, value) => {\n"
        output_str += "        if (mode === Modes.READ_MODE) {\n"
        output_str += f"            let updatedData = cloneDeep({dependent_msg_name_camel_cased});\n"
        output_str += "            _.set(updatedData, xpath, value);\n"
        output_str += f"           dispatch(update{dependent_msg_name}(updatedData));\n"
        output_str += "        } else {\n"
        output_str += f"            let updatedData = cloneDeep({dependent_msg_name_camel_cased});\n"
        output_str += "            if (updatedData[DB_ID] && updatedData[DB_ID] !== NEW_ITEM_ID && " \
                      "hasxpath(updatedData, xpath)) {\n"
        output_str += "                _.set(updatedData, xpath, value);\n"
        output_str += f"                dispatch(update{dependent_msg_name}(updatedData));\n"
        output_str += "            } else {\n"
        output_str += f"                let updatedData = cloneDeep(modified{dependent_msg_name});\n"
        output_str += "                _.set(updatedData, xpath, value);\n"
        output_str += f"                dispatch(setModified{dependent_msg_name}(updatedData));\n"
        output_str += "            }\n"
        output_str += "        }\n"
        output_str += "    }\n\n"
        output_str += "    let createMenu = '';\n"
        output_str += "    if (mode === Modes.READ_MODE) {\n"
        output_str += "        createMenu = <Icon className={classes.icon} title='Create' " \
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
        output_str += "                        {_.get(modified"+f"{message_name}"+", loadedKeyName) && _.get(" \
                      "modified"+f"{message_name}"+", loadedKeyName).map((item, index) => {\n"
        output_str += "                            let id = getIdFromAbbreviatedKey(abbreviated, item);\n"
        output_str += "                            if (id !== NEW_ITEM_ID) return;\n"
        output_str += "                            return (\n"
        output_str += "                                <ListItem key={index} className={classes.listItem} " \
                      "selected={selected"+f"{dependent_msg_name}"+"Id === id} disablePadding>\n"
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
        output_str += "                    options={_.get("+f"{message_name_camel_cased}"+", bufferedKeyName) ? " \
                      "_.get("+f"{message_name_camel_cased}"+", bufferedKeyName) : []}\n"
        output_str += "                    onChange={onChange}\n"
        output_str += "                    onLoad={onLoad}\n"
        output_str += "                    loadedKeyName={loadedKeyName}\n"
        output_str += "                    loadedLabel={collections.filter(col => col.key === " \
                      "loadedKeyName)[0].title}\n"
        output_str += "                    items={_.get("+f"{message_name_camel_cased}"+", loadedKeyName) ? " \
                      "_.get("+f"{message_name_camel_cased}"+", loadedKeyName) : []}\n"
        output_str += "                    selected={selected"+f"{dependent_msg_name}"+"Id}\n"
        output_str += "                    onSelect={onSelect}\n"
        output_str += "                    onUnload={onUnload}\n"
        output_str += "                    abbreviated={abbreviated}\n"
        output_str += "                    itemsMetadata={"f"{dependent_msg_name_camel_cased}"+"Array}\n"
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
        output_str += "            <Dialog open={openPopup} onClose={onClosePopup}>\n"
        output_str += "                <DialogTitle>{title} Change Detected</DialogTitle>\n"
        output_str += "                <DialogContent>\n"
        output_str += "                    <DialogContentText>New change detected from server. Your " \
                      "changes may be lost.</DialogContentText>\n"
        output_str += "                </DialogContent>\n"
        output_str += "                <DialogActions>\n"
        output_str += "                    <Button onClick={onClosePopup} autoFocus>OK</Button>\n"
        output_str += "                </DialogActions>\n"
        output_str += "            </Dialog>\n"
        output_str += "        </Fragment>\n"
        output_str += "    )\n"
        output_str += "}\n\n"

        return output_str

    def handle_jsx_const(self, message: protogen.Message, layout_type: str) -> str:
        output_str = self.handle_import_output(message, layout_type)
        output_str += "const useStyles = makeStyles({\n"
        output_str += "    icon: {\n"
        output_str += "        backgroundColor: '#ccc !important',\n"
        output_str += "        marginRight: '5px !important',\n"
        output_str += "        '&:hover': {\n"
        output_str += "            backgroundColor: '#ddd !important'\n"
        output_str += "        }\n"
        output_str += "    }\n"
        output_str += "})\n\n"
        message_name = message.proto.name
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        message_name_camel_cased = message_name[0].lower() + message_name[1:]
        output_str += f"const {message_name} = (props) => " + "{\n\n"
        output_str += self.__handle_const_on_layout(message_name, layout_type)
        output_str += "    const dispatch = useDispatch();\n"
        output_str += "    const classes = useStyles();\n\n"
        output_str += "    let currentSchema = _.get(schema, props.name);\n"
        output_str += "    let currentSchemaXpath = null;\n"
        output_str += "    let title = currentSchema ? currentSchema.title : props.name;\n"
        json_root_case_styled = self.case_style_convert_method("json_root")
        output_str += f"    let isJsonRoot = _.keys(schema).length > 0 && currentSchema.{json_root_case_styled} ? true : false;\n"
        output_str += "    let parentSchema = null;\n"
        if layout_type != JsxFileGenPlugin.abbreviated_type:
            output_str += "    let parentSchemaName = null;\n"
        output_str += "    if (!isJsonRoot) {\n"
        output_str += "        let currentSchemaPropname = lowerFirstLetter(props.name);\n"
        output_str += "        _.keys(_.get(schema, SCHEMA_DEFINITIONS_XPATH)).map((key) => {\n"
        output_str += "            let current = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, key]);\n"
        output_str += "            if (current.type === DataTypes.OBJECT && _.has(current.properties, " \
                      "currentSchemaPropname)) {\n"
        output_str += "                parentSchema = current;\n"
        if layout_type != JsxFileGenPlugin.abbreviated_type:
            output_str += "                parentSchemaName = SCHEMA_DEFINITIONS_XPATH + '.' + key;\n"
        output_str += "                currentSchemaXpath = currentSchemaPropname;\n"
        output_str += "            }\n"
        output_str += "        })\n"
        output_str += "    }\n"
        output_str += "    \n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "    useEffect(() => {\n"
            output_str += f"        dispatch(getAll{message_name}());\n"
            output_str += "    }, []);\n\n"
        elif layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    let collections = [];\n"
            output_str += "    if (currentSchema) {\n"
            output_str += "        collections = createCollections(schema, currentSchema, { mode: mode });\n"
            output_str += "    }\n\n"
            output_str += "    let bufferedKeyName = collections.filter(collection => collection.key.includes" \
                          "('buffer'))[0] ?\n"
            output_str += "        collections.filter(collection => collection.key.includes('buffer'))[0].key : " \
                          "null;\n"
            output_str += "    let loadedKeyName = collections.filter(collection => collection.key.includes" \
                          "('load'))[0] ?\n"
            output_str += "        collections.filter(collection => collection.key.includes('load'))[0].key : " \
                          "null;\n"
            output_str += '    let abbreviated = collections.filter(collection => collection.abbreviated && ' \
                          'collection.abbreviated !== "JSON")[0] ?\n'
            output_str += '        collections.filter(collection => collection.abbreviated && collection.' \
                          'abbreviated !== "JSON")[0].abbreviated : null;\n'
            output_str += "    let dependentName = abbreviated ? abbreviated.split('.')[0] : null;\n"
            output_str += "    let dependentSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, dependentName]);\n\n"
            output_str += "    let dependentCollections = [];\n"
            output_str += "    if (dependentSchema) {\n"
            output_str += "        dependentCollections = createCollections(schema, dependentSchema, { mode: Modes.READ_MODE });\n"
            output_str += "    }\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        dispatch(getAll{message_name}());\n"
            output_str += f"        dispatch(getAll{self.abbreviated_dependent_message_name}());\n"
            output_str += "    }, []);\n\n"
        if layout_type != JsxFileGenPlugin.non_root_type:
            output_str += "    useEffect(() => {\n"
            output_str += f"        if ({message_name_camel_cased}Array.length > 0 && !selected{message_name}Id) "+"{\n"
            output_str += f"            let object = getObjectWithLeastId({message_name_camel_cased}Array);\n"
            output_str += f"            dispatch(setSelected{message_name}Id(object[DB_ID]));\n"
            output_str += "        }\n"
            output_str += "    }, "+f"[{message_name_camel_cased}Array])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        let socket = new WebSocket(`${API_ROOT_URL.replace('http', " \
                          "'ws')}/get-all-"+f"{message_name_snake_cased}"+"-ws/`);\n"
            output_str += "        setGetAllWebsocket(socket);\n"
            output_str += "        // close the websocket on re-render\n"
            output_str += "        return () => socket.close();\n"
            output_str += "    }, [])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        if (getAllWebsocket) {\n"
            output_str += "            getAllWebsocket.onmessage = (event) => {\n"
            output_str += "                let updatedData = JSON.parse(event.data);\n"
            output_str += "                if (Array.isArray(updatedData)) {\n"
            output_str += "                    if (updatedData.length === 0) {\n"
            output_str += f"                        dispatch(resetSelected{message_name}Id());\n"
            output_str += "                    }\n"
            output_str += f"                    dispatch(set{message_name}Array(updatedData));\n"
            output_str += "                } else if (_.isObject(updatedData)) {\n"
            output_str += f"                    let updatedArray = {message_name_camel_cased}Array.filter" \
                          f"(object => object[DB_ID] !== updatedData[DB_ID]);\n"
            output_str += "                    if (_.keys(updatedData).length !== 1) {\n"
            output_str += "                        updatedArray = [...updatedArray, updatedData];\n"
            output_str += "                    } else if (_.keys(updatedData).length === 1 && " \
                          f"selected{message_name}Id === updatedData[DB_ID]) "+"{\n"
            output_str += f"                        dispatch(resetSelected{message_name}Id());\n"
            output_str += f"                        dispatch(reset{message_name}());\n"
            output_str += "                    }\n"
            output_str += f"                    dispatch(set{message_name}Array(updatedArray));\n"
            output_str += "                }\n"
            output_str += "            }\n"
            output_str += "\n"
            output_str += "            getAllWebsocket.onclose = (event) => {\n"
            if layout_type == self.root_type:
                output_str += "                setMode(Modes.DISABLED_MODE);\n"
            else:
                output_str += "                dispatch(setMode(Modes.DISABLED_MODE));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }, [getAllWebsocket])\n\n"

        output_str += "    useEffect(() => {\n"
        output_str += "        if (currentSchema) {\n"
        output_str += "            setLayout(currentSchema.layout);\n"
        output_str += "        }\n"
        output_str += "    }, [schema])\n\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    useEffect(() => {\n"
            output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
            output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            output_str += f"        if (_.get({message_name_camel_cased}, loadedKeyName) && " \
                          f"_.get({message_name_camel_cased}, loadedKeyName).length > 0) "+"{\n"
            output_str += f"            let id = getIdFromAbbreviatedKey(abbreviated, _.get(" \
                          f"{message_name_camel_cased}, loadedKeyName)[0]);\n"
            output_str += f"            dispatch(setSelected{self.abbreviated_dependent_message_name}Id(id));\n"
            output_str += "        }\n"
            output_str += "    }"+f", [{message_name_camel_cased}])\n\n\n"
        else:
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "    useEffect(() => {\n"
                output_str += f"        let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
                output_str += f"        _.keys(userChanges).map(xpath => "+"{\n"
                output_str += f"            _.set(updatedData, xpath, userChanges[xpath]);\n"
                output_str += "        })\n"
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
                output_str += "    }, " + f"[{message_name_camel_cased}])\n\n"
                output_str += "    useEffect(() => {\n"
                output_str += "        if (selected"+f"{message_name}"+"Id) {\n"
                output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', " \
                              "'ws')}/get-"+f"{message_name_snake_cased}"+"-ws/${selected"+f"{message_name}"+"Id}`);\n"
                output_str += "            setWebsocket(socket);\n"
                output_str += "            // close the websocket on re-render\n"
                output_str += "            return () => socket.close();\n"
                output_str += "        }\n"
                output_str += "    }, [selected"+f"{message_name}"+"Id])\n\n"
            else:
                dependent_msg_name = self.root_message.proto.name
                dependent_msg_name_snake_cased = self.convert_camel_case_to_specific_case(dependent_msg_name)
                dependent_msg_name_camel_cased = dependent_msg_name[0].lower() + dependent_msg_name[1:]
                output_str += "    const applyUserChanges = (updatedData) => {\n"
                output_str += "        _.keys(userChanges).map(xpath => {\n"
                output_str += f"            if (userChanges[DB_ID] === selected{dependent_msg_name}Id) "+"{\n"
                output_str += f"                _.set(updatedData, xpath, userChanges[xpath]);\n"
                output_str += "            } else {\n"
                output_str += f"                clearUserChanges();\n"
                output_str += "            }\n"
                output_str += "        })\n"
                output_str += "    }\n\n"
                output_str += "    const clearUserChanges = () => {\n"
                output_str += "        dispatch(setUserChanges({}));\n"
                output_str += "        dispatch(setDiscardedChanges({}));\n"
                output_str += "    }\n\n"
                output_str += "    useEffect(() => {\n"
                output_str += "        if (!createMode) {\n"
                output_str += f"            let updatedData = addxpath(cloneDeep(" \
                              f"cloneDeep({dependent_msg_name_camel_cased})));\n"
                output_str += "            applyUserChanges(updatedData);\n"
                output_str += f"            dispatch(setModified{dependent_msg_name}(updatedData));\n"
                output_str += "        }\n"
                output_str += "    }"+f", [createMode, {dependent_msg_name_camel_cased}])\n\n"
                output_str += "    useEffect(() => {\n"
                output_str += f"        if (selected{dependent_msg_name}Id && selected{dependent_msg_name}Id " \
                              f"!== NEW_ITEM_ID) "+"{\n"
                output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}" \
                              f"/get-{dependent_msg_name_snake_cased}-ws/$"+"{" + f"selected{dependent_msg_name}Id" + \
                              "}`);\n"
                output_str += "            setWebsocket(socket);\n"
                output_str += "            // close the websocket on re-render\n"
                output_str += "            return () => socket.close();\n"
                output_str += "        }\n"
                output_str += "    }"+f", [selected{dependent_msg_name}Id])\n\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    useEffect(() => {\n"
            output_str += f"        if (selected{message_name}Id) "+"{\n"
            output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}/" \
                          f"get-{message_name_snake_cased}-ws/$"+"{"+f"selected{message_name}Id"+"}`);\n"
            output_str += f"            setWebsocket(socket);\n"
            output_str += f"            // close the websocket on re-render\n"
            output_str += f"            return () => socket.close();\n"
            output_str += "        }\n"
            output_str += "    }, [selected"+f"{message_name}Id])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        if (selected{message_name}Id) "+"{\n"
            abbreviated_dependent_msg_snake_cased = \
                self.convert_camel_case_to_specific_case(self.abbreviated_dependent_message_name)
            abbreviated_dependent_msg_camel_cased = self.abbreviated_dependent_message_name[0].lower() + \
                                                        self.abbreviated_dependent_message_name[1:]
            output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}/" \
                          f"get-all-{abbreviated_dependent_msg_snake_cased}-ws/`);\n"
            output_str += f"            set{self.abbreviated_dependent_message_name}GetAllWebsocket(socket);\n"
            output_str += f"            // close the websocket on re-render\n"
            output_str += "            return () => socket.close();\n"
            output_str += "        }\n"
            output_str += "    }, "+f"[selected{message_name}Id])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        if (websocket) {\n"
            output_str += "            websocket.onmessage = (event) => {\n"
            output_str += "                let updatedData = JSON.parse(event.data);\n"
            output_str += "                if (_.keys(updatedData).length === 1) {\n"
            output_str += f"                    dispatch(resetSelected{message_name}Id());\n"
            output_str += f"                    dispatch(reset{message_name}());\n"
            output_str += "                } else {\n"
            output_str += f"                    dispatch(set{message_name}(updatedData));\n"
            output_str += "                }\n"
            output_str += "                let diff = compareObjects(updatedData, " \
                          f"{message_name_camel_cased}, {message_name_camel_cased});\n"
            output_str += "                for (let i = 0; i < diff.length; i++) {\n"
            output_str += f"                    let id = getIdFromAbbreviatedKey(abbreviated, " \
                          f"_.get({message_name_camel_cased}, diff[i]));\n"
            output_str += f"                    if (id === selected{self.abbreviated_dependent_message_name}Id" \
                          " && mode === Modes.EDIT_MODE) {\n"
            output_str += "                        setOpenPopup(true);\n"
            output_str += "                    }\n"
            output_str += "                }\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }, [websocket, "+f"{message_name_camel_cased}, " \
                                                f"selected{self.abbreviated_dependent_message_name}Id, mode])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        if ({abbreviated_dependent_msg_camel_cased}GetAllWebsocket) "+"{\n"
            output_str += f"            {abbreviated_dependent_msg_camel_cased}GetAllWebsocket.onmessage = " \
                          f"(event) => "+"{\n"
            output_str += f"                let updatedData = JSON.parse(event.data);\n"
            output_str += f"                if (Array.isArray(updatedData)) "+"{\n"
            output_str += f"                    dispatch(set{self.abbreviated_dependent_message_name}" \
                          f"Array(updatedData));\n"
            output_str += "                } else {\n"
            output_str += "                    let id = updatedData[DB_ID];\n"
            output_str += f"                    let updatedArray = {abbreviated_dependent_msg_camel_cased}" \
                          f"Array.filter(strat => strat[DB_ID] !== id);\n"
            output_str += f"                    dispatch(set{self.abbreviated_dependent_message_name}Array(" \
                          f"[...updatedArray, updatedData]));\n"
            output_str += "                }\n"
            output_str += "            }\n\n"
            output_str += f"            {abbreviated_dependent_msg_camel_cased}GetAllWebsocket.onclose = (event) => " \
                          f"" + "{\n"
            output_str += "                dispatch(setMode(Modes.DISABLED_MODE));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }, " + \
                          f"[{abbreviated_dependent_msg_camel_cased}GetAllWebsocket, " \
                          f"{abbreviated_dependent_msg_camel_cased}Array])\n\n"
            output_str += "    if (loading) {\n"
            output_str += "        return (\n"
            output_str += "            <SkeletonField title={title} />\n"
            output_str += "        )\n"
            output_str += "    }\n\n"

            output_str += "    if (mode === Modes.DISABLED_MODE) {\n"
            output_str += "        return (\n"
            output_str += "            <h1>Connection lost. Please refresh...</h1>\n"
            output_str += "        )\n"
            output_str += "    }\n\n"
            output_str += "    if (!bufferedKeyName || !loadedKeyName || !abbreviated) {\n"
            output_str += "        return (\n"
            output_str += "            <Box>{Layouts.ABBREVIATED_FILTER_LAYOUT} not supported. Required " \
                          "fields not found.</Box>\n"
            output_str += "        )\n"
            output_str += "    }\n\n"
        else:
            output_str += f"    let collections = [];\n"
            output_str += f"    let rows = [];\n"
            output_str += f"    let tableColumns = [];\n"
            output_str += f"    let commonKeyCollections = [];\n"
            output_str += "    if (currentSchema) {\n"
            if layout_type == self.root_type:
                output_str += "        collections = createCollections(schema, currentSchema, { mode: mode });\n"
                output_str += "        tableColumns = getTableColumns(collections);\n"
                output_str += f"        rows = getTableRows(collections, {message_name_camel_cased}, " \
                              f"modified{message_name});\n"
                output_str += "        commonKeyCollections = getCommonKeyCollections(rows, tableColumns);\n"
            else:
                output_str += "        collections = createCollections(schema, currentSchema, { mode: mode, " \
                              "parentSchema: parentSchema, xpath: currentSchemaXpath }, undefined, undefined, currentSchemaXpath);\n"
                output_str += "        tableColumns = getTableColumns(collections);\n"
                dependent_msg_name = self.root_message.proto.name
                dependent_msg_name_camel_cased = self.convert_to_camel_case(dependent_msg_name)
                output_str += f"        rows = getTableRows(collections, {dependent_msg_name_camel_cased}, " \
                              f"modified{dependent_msg_name}, currentSchemaXpath);\n"
                output_str += "        commonKeyCollections = getCommonKeyCollections(rows, tableColumns);\n"
            output_str += "    }\n\n"
        if layout_type != JsxFileGenPlugin.abbreviated_type:
            output_str += "    useEffect(() => {\n"
            output_str += "        if (websocket) {\n"
            output_str += "            websocket.onmessage = (event) => {\n"
            output_str += "                let updatedData = JSON.parse(event.data);\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "                let diff = compareObjects(updatedData, " \
                              f"{message_name_camel_cased}, {message_name_camel_cased});\n"
                output_str += "                if (_.keys(updatedData).length === 1) {\n"
                output_str += f"                    dispatch(resetSelected{message_name}Id());\n"
                output_str += f"                    dispatch(reset{message_name}());\n"
                output_str += "                } else {\n"
                output_str += f"                    dispatch(set{message_name}(updatedData));\n"
                output_str += "                }\n"
                output_str += f"                let trees = generateRowTrees(cloneDeep(updatedData), collections);\n"
                output_str += f"                let modifiedTrees = generateRowTrees(cloneDeep" \
                              f"(modified{message_name}), collections);\n"
            else:
                dependent_msg_name = self.root_message.proto.name
                dependent_msg_name_camel_cased = dependent_msg_name[0].lower() + dependent_msg_name[1:]
                output_str += f"                let currentData = _.get({dependent_msg_name_camel_cased}, " \
                              f"currentSchemaXpath) ? _.get({dependent_msg_name_camel_cased}, " \
                              f"currentSchemaXpath) : {dependent_msg_name_camel_cased}\n"
                output_str += f"                let diff = compareObjects(updatedData, " \
                              f"{dependent_msg_name_camel_cased}, currentData, currentSchemaXpath);\n"
                output_str += f"                dispatch(set{dependent_msg_name}(updatedData));\n"
                output_str += f"                let trees = generateRowTrees(cloneDeep(updatedData), " \
                              f"collections, currentSchemaXpath);\n"
                output_str += f"                let modifiedTrees = generateRowTrees(cloneDeep" \
                              f"(modified{dependent_msg_name}), collections, currentSchemaXpath);\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "                if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                    if (mode === Modes.EDIT_MODE) {\n"
                output_str += "                        setOpenPopup(true);\n"
                output_str += "                    } else {\n"
                output_str += "                        updatedData = addxpath(cloneDeep(updatedData));\n"
                output_str += f"                        dispatch(setModified{message_name}(updatedData));\n"
            else:
                dependent_msg_name = self.root_message.proto.name
                output_str += "                if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                    if (mode === Modes.EDIT_MODE && _.keys(userChanges).length > 0) {\n"
                output_str += "                        setOpenPopup(true);\n"
                output_str += "                    } else {\n"
                output_str += "                        updatedData = addxpath(cloneDeep(updatedData));\n"
                output_str += f"                        dispatch(setModified{dependent_msg_name}(updatedData));\n"
            output_str += "                    }\n"
            output_str += "                } else {\n"
            output_str += "                    let found = false;\n"
            output_str += "                    let updatedUserChanges = cloneDeep(userChanges);\n"
            output_str += "                    let deletedChanges = {}\n"
            output_str += "                    _.keys(userChanges).map(xpath => {\n"
            output_str += "                        if (diff.includes(xpath)) {\n"
            output_str += "                            deletedChanges[xpath] = userChanges[xpath];\n"
            output_str += "                            delete updatedUserChanges[xpath];\n"
            output_str += "                            found = true;\n"
            output_str += "                        }\n"
            output_str += "                    })\n"
            output_str += "                    if (found) {\n"
            output_str += "                        setOpenPopup(true);\n"
            if layout_type == self.root_type:
                output_str += "                        setUserChanges(updatedUserChanges);\n"
                output_str += "                        setDiscardedChanges(deletedChanges);\n"
            else:
                output_str += "                        dispatch(setUserChanges(updatedUserChanges));\n"
                output_str += "                        dispatch(setDiscardedChanges(deletedChanges));\n"
            output_str += "                    }\n"
            output_str += "                }\n"
            output_str += "            }\n"
            output_str += "        }\n\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "    }, [websocket, "+f"{message_name_camel_cased}, " \
                                                    f"modified{message_name}, userChanges, mode])\n\n"
            else:
                dependent_msg_name = self.root_message.proto.name
                dependent_msg_name_camel_cased = dependent_msg_name[0].lower() + dependent_msg_name[1:]
                output_str += "    }, [websocket, " + f"{dependent_msg_name_camel_cased}, " \
                                                      f"modified{dependent_msg_name}, userChanges, mode])\n\n"
            output_str += "    if (loading) {\n"
            output_str += "        return (\n"
            output_str += "            <SkeletonField title={title} />\n"
            output_str += "        )\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const onChangeMode = () => {\n"
            output_str += "        dispatch(setMode(Modes.EDIT_MODE));\n"
            output_str += "    }\n\n"
            output_str += "    const onReload = () => {\n"
            output_str += f"        dispatch(getAll{message_name}());\n"
            abbreviated_dependent_msg_camel_cased = self.abbreviated_dependent_message_name[0].lower() + \
                                                    self.abbreviated_dependent_message_name[1:]
            output_str += f"        let updatedData = addxpath(cloneDeep(" \
                          f"{abbreviated_dependent_msg_camel_cased}));\n"
            output_str += f"        dispatch(setModified{self.abbreviated_dependent_message_name}(updatedData));\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        setSearchValue('');\n"
            output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "    }\n\n"
        else:
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "    if (mode === Modes.DISABLED_MODE) {\n"
                output_str += "        return (\n"
                output_str += "            <h1>Connection lost. Please refresh...</h1>\n"
                output_str += "        )\n"
                output_str += "    }\n\n"
                output_str += "    const onChangeMode = () => {\n"
                output_str += "        setMode(Modes.EDIT_MODE);\n"
                output_str += "    }\n\n"
            output_str += "    const onChangeLayout = () => {\n"
            output_str += "        if (layout === Layouts.TABLE_LAYOUT) {\n"
            output_str += "            setLayout(Layouts.TREE_LAYOUT);\n"
            output_str += "        } else {\n"
            output_str += "            setLayout(Layouts.TABLE_LAYOUT);\n"
            output_str += "        }\n"
            output_str += "    }\n\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "    const onReload = () => {\n"
            output_str += f"        if (selected{message_name}Id) "+"{\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        } else {\n"
            output_str += f"            dispatch(getAll{message_name}());\n"
            output_str += "        }\n"
            output_str += "        setUserChanges({});\n"
            output_str += "        setDiscardedChanges({});\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "    }\n\n"
        output_str += "    const onResetError = () => {\n"
        output_str += "        dispatch(resetError());\n"
        output_str += "    }\n\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const onCreate = () => {\n"
            output_str += f"        if (!_.get({message_name_camel_cased}, DB_ID)) "+"{\n"
            output_str += "            let object = generateObjectFromSchema(schema, currentSchema);\n"
            output_str += f"            dispatch(create{message_name}(object));\n"
            output_str += "        } else {\n"
            output_str += "            dispatch(setCreateMode(true));\n"
            output_str += "            dispatch(setMode(Modes.EDIT_MODE));\n"
            output_str += "            let newItem = getNewItem(dependentCollections, abbreviated);\n"
            output_str += f"            let updatedData = cloneDeep(modified{message_name});\n"
            output_str += "            _.get(updatedData, loadedKeyName).push(newItem);\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += f"            dispatch(setSelected{self.abbreviated_dependent_message_name}Id(NEW_ITEM_ID));\n"
            output_str += f"            dispatch(reset{self.abbreviated_dependent_message_name}());\n"
            output_str += f"            let object = generateObjectFromSchema(schema, dependentSchema);\n"
            output_str += "            _.set(object, DB_ID, NEW_ITEM_ID);\n"
            output_str += "            let modifiedData = addxpath(object);\n"
            output_str += f"            dispatch(setModified{self.abbreviated_dependent_message_name}(modifiedData));\n"
            output_str += "        }\n"
            output_str += "    }\n\n"
            output_str += "    const onSave = () => {\n"
            output_str += "        if (createMode) {\n"
            output_str += "            dispatch(setCreateMode(false));\n"
            output_str += f"            let updated{self.abbreviated_dependent_message_name} = clearxpath(cloneDeep" \
                          f"(modified{self.abbreviated_dependent_message_name}));\n"
            output_str += f"            delete updated{self.abbreviated_dependent_message_name}[DB_ID];\n"
            output_str += f"            dispatch(create{self.abbreviated_dependent_message_name}(" \
                          "{ data: " + f"updated{self.abbreviated_dependent_message_name}, abbreviated: " \
                          "abbreviated, loadedKeyName: loadedKeyName }));\n"
            output_str += "        } else {\n"
            output_str += f"            let updatedData = clearxpath(cloneDeep(modified" \
                          f"{self.abbreviated_dependent_message_name}));\n"
            dependent_msg_name_camel_cased = self.abbreviated_dependent_message_name[0].lower() + \
                                             self.abbreviated_dependent_message_name[1:]
            output_str += f"            if (!_.isEqual({dependent_msg_name_camel_cased}, updatedData"+")) {\n"
            output_str += f"                dispatch(update{self.abbreviated_dependent_message_name}(updatedData));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += f"        dispatch(setModified{message_name}({message_name_camel_cased}));\n"
            output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "    }\n\n"
            output_str += "    const onChange = (e, value) => {\n"
            output_str += "        setSearchValue(value);\n"
            output_str += "    }\n"
        else:
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "    const onCreate = () => {\n"
                output_str += "        let object = generateObjectFromSchema(schema, _.get(schema, props.name));\n"
                output_str += "        let updatedData = addxpath(object);\n"
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
                output_str += f"        setMode(Modes.EDIT_MODE);\n"
                output_str += "    }\n\n"
                output_str += "    const onUpdate = (updatedData) => {\n"
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
                output_str += "    }\n\n"
                output_str += "    const onSave = () => {\n"
                output_str += f"        let updatedData = clearxpath(cloneDeep(modified{message_name}));\n"
                output_str += f"        if (!_.isEqual({message_name_camel_cased}, updatedData)) " + "{\n"
                output_str += f"            if (_.get({message_name_camel_cased}, DB_ID)) "+"{\n"
                output_str += f"                dispatch(update{message_name}("+"updatedData));\n"
                output_str += "            } else {\n"
                output_str += f"                dispatch(create{message_name}(updatedData));\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "        setMode(Modes.READ_MODE);\n"
                output_str += "        setUserChanges({});\n"
                output_str += "        setDiscardedChanges({});\n"
                output_str += "    }\n\n"
            else:
                output_str += "    const onUpdate = (updatedData) => {\n"
                output_str += f"        dispatch(setModified{self.root_message.proto.name}(updatedData));\n"
                output_str += "    }\n"

        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += "    const onLoad = () => {\n"
            output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
            output_str += f"        let index = _.get({message_name_camel_cased}, bufferedKeyName).indexOf(" \
                          f"searchValue);\n"
            output_str += "        _.get(updatedData, bufferedKeyName).splice(index, 1);\n"
            output_str += "        _.get(updatedData, loadedKeyName).push(searchValue);\n"
            output_str += f"        dispatch(update{message_name}(updatedData));\n"
            output_str += "        let id = getIdFromAbbreviatedKey(abbreviated, searchValue);\n"
            output_str += f"        setSelected{self.abbreviated_dependent_message_name}Id(id);\n"
            output_str += "        setSearchValue('');\n"
            output_str += "    }\n"
        else:
            output_str += "\n"
            output_str += "    const onButtonToggle = (e, xpath, value) => {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        if (mode === Modes.READ_MODE) {\n"
                output_str += f"            let updatedData = cloneDeep({message_name_camel_cased});\n"
                output_str += f"            _.set(updatedData, xpath, value);\n"
                output_str += f"            dispatch(update{message_name}(updatedData));\n"
                output_str += "        } else {\n"
                output_str += f"            if ({message_name_camel_cased}[DB_ID] && hasxpath({message_name_camel_cased}, xpath)) "+"{\n"
                output_str += f"                let updatedData = cloneDeep({message_name_camel_cased});\n"
                output_str += f"                _.set(updatedData, xpath, value);\n"
                output_str += f"                dispatch(update{message_name}(updatedData));\n"
                output_str += "            } else {\n"
                output_str += f"                let updatedData = cloneDeep(modified{message_name});\n"
                output_str += f"                _.set(updatedData, xpath, value);\n"
                output_str += f"                dispatch(setModified{message_name}(updatedData));\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "    }\n\n"
            else:
                root_msg_name = self.root_message.proto.name
                root_msg_camel_cased = self.convert_to_camel_case(root_msg_name)
                output_str += "        if (mode === Modes.READ_MODE) {\n"
                output_str += "            let updatedData = cloneDeep("+f"{root_msg_camel_cased});\n"
                output_str += "            _.set(updatedData, xpath, value);\n"
                output_str += f"           dispatch(update{root_msg_name}(updatedData));\n"
                output_str += "        } else {\n"
                output_str += f"            let updatedData = cloneDeep({root_msg_camel_cased});\n"
                output_str += "            if (updatedData[DB_ID] && updatedData[DB_ID] !== NEW_ITEM_ID && " \
                              "hasxpath(updatedData, xpath)) {\n"
                output_str += f"                _.set(updatedData, xpath, value);\n"
                output_str += f"                dispatch(update{root_msg_name}(updatedData));\n"
                output_str += "            } else {\n"
                output_str += f"                let updatedData = cloneDeep(modified{root_msg_name});\n"
                output_str += f"                _.set(updatedData, xpath, value);\n"
                output_str += f"                dispatch(setModified{root_msg_name}(updatedData));\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "    }\n\n"
        if layout_type == JsxFileGenPlugin.abbreviated_type:
            output_str += self.handle_abbriviated_return(message_name, message_name_camel_cased)
        else:
            output_str += self.handle_non_abbreviated_return(message_name, message_name_camel_cased, layout_type)
        output_str += f"export default {message_name};\n\n"

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
                self.abbreviated_dependent_message_name = fld_abbreviated_option_value.split(".")[0]
                output_str = self.handle_jsx_const(message, JsxFileGenPlugin.abbreviated_type)
            else:
                # Root Type
                if message in self.root_msg_list:
                    self.root_message = message
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
                    output_str = self.handle_jsx_const(message, JsxFileGenPlugin.non_root_type)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsxFileGenPlugin)
