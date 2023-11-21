#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, Final, ClassVar
import time

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
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
    ----- 5. Layout as Simple Abbreviated Type
    ----- 6. Layout as Parent Abbreviated Type (for nested abbreviated types)
    ----- 7. Abbreviated dependent type
    """
    root_type: str = 'RootType'
    repeated_root_type: str = 'RepeatedRootType'
    non_root_type: str = 'NonRootType'
    repeated_non_root_type: str = 'RepeatedNonRootType'
    simple_abbreviated_type: str = 'SimpleAbbreviatedType'
    parent_abbreviated_type: str = 'ParentAbbreviatedType'
    abbreviated_dependent_type: str = 'AbbreviatedDependentType'

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message: protogen.Message | None = None
        self.abbreviated_dependent_message_name: str | None = None

    def handle_import_output(self, message: protogen.Message, layout_type: str) -> str:
        output_str = "/* react and third-party library imports */\n"
        if layout_type == JsxFileGenPlugin.non_root_type or layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
            output_str += "import React, { Fragment, memo, useEffect } from 'react';\n"
        else:
            output_str += "import React, { Fragment, useState, useEffect, useCallback, useRef, memo, useMemo } " \
                          "from 'react';\n"
        output_str += "import { useSelector, useDispatch } from 'react-redux';\n"
        output_str += "import _, { cloneDeep, isEqual } from 'lodash';\n"
        if layout_type == JsxFileGenPlugin.root_type:
            output_str += "import { Add } from '@mui/icons-material';\n"
        elif layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "import { Add, Delete } from '@mui/icons-material';\n"
            output_str += "import { Divider, List, ListItem, ListItemButton, ListItemText, Chip, Box } " \
                          "from '@mui/material';\n"
        output_str += "/* redux CRUD and additional helper actions */\n"
        output_str += "import {\n"
        message_name = message.proto.name
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += f"    getAll{message_name},\n"
            output_str += f"    set{message_name}Ws, resetError"
            widget_ui_option_value = JsxFileGenPlugin.get_complex_option_value_from_proto(
                message, JsxFileGenPlugin.flux_msg_widget_ui_data_element)
            if widget_ui_option_value.get(JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field):
                output_str += ", setUrl"
            output_str += "\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += f"    getAll{message_name}, create{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}ArrayWs, set{message_name}Ws, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetError,\n"
            output_str += "    setUserChanges, setDiscardedChanges, setActiveChanges, setOpenWsPopup, setForceUpdate"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message):
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += ", setOpenConfirmSavePopup, setUrl"
            output_str += "\n"
        elif layout_type == JsxFileGenPlugin.non_root_type or \
                layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
            message_name = self.root_message.proto.name
            output_str += f"    setModified{message_name}, resetError,\n"
            output_str += ("    setUserChanges, setActiveChanges, setOpenConfirmSavePopup, "
                           "setFormValidationWithCallback, setOpenFormValidationPopup\n")
        else:
            output_str += f"    getAll{message_name}, update{message_name},\n"
            output_str += f"    set{message_name}ArrayWs, set{message_name}Ws, setModified{message_name}, " \
                          f"setSelected{message_name}Id, resetError\n"
        message_name_camel_cased = convert_to_camel_case(message_name)
        output_str += "}" + f" from '../features/{message_name_camel_cased}Slice';\n"
        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            dependent_message_name = self.abbreviated_dependent_message_name
            dependent_message_name_camel_cased = convert_to_camel_case(dependent_message_name)
            output_str += "import {\n"
            output_str += f"    getAll{dependent_message_name}, create{dependent_message_name}, " \
                          f"update{dependent_message_name},\n"
            if message_name in self.parent_abb_msg_name_to_linked_abb_msg_name_dict.values():
                output_str += f"    querySearchNUpdate{dependent_message_name},\n"
            output_str += f"    set{dependent_message_name}Array, set{dependent_message_name}ArrayWs, " \
                          f"setModified{dependent_message_name}, setSelected{dependent_message_name}Id,\n"
            output_str += ("    setUserChanges, setDiscardedChanges, setActiveChanges, setOpenWsPopup, "
                           "setForceUpdate, \n")
            output_str += (f"    setMode, setCreateMode, setOpenConfirmSavePopup, set{dependent_message_name}, "
                           f"reset{dependent_message_name}, resetSelected{dependent_message_name}Id, "
                           f"setFormValidation, setOpenFormValidationPopup")
            if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                output_str += f", getAll{dependent_message_name}Background"
            output_str += "\n"
            output_str += "}" + f" from '../features/{dependent_message_name_camel_cased}Slice';\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        additional_data = (f", setActiveChanges as set{dep_msg_name}ActiveChanges, "
                                           "setOpenConfirmSavePopup as "
                                           f"set{dep_msg_name}OpenConfirmSavePopup")
                        output_str += ("import { setSelected"+f"{dep_msg_name}"+f"Id, set{dep_msg_name}ArrayWs, set{dep_msg_name}Array" +
                                       additional_data + " } " + f"from '../features/{dep_msg_camel_cased}Slice';\n")
                    for msg in self.root_msg_list:
                        if msg in self.repeated_tree_layout_msg_list or msg in self.repeated_table_layout_msg_list:
                            # taking all repeated root types
                            widget_ui_option_value = JsxFileGenPlugin.get_complex_option_value_from_proto(
                                msg, JsxFileGenPlugin.flux_msg_widget_ui_data_element)
                            if (widget_ui_option_value.get(
                                        JsxFileGenPlugin.widget_ui_option_depending_proto_file_name_field) ==
                                    self.current_proto_file_name):
                                msg_name_camel_cased = convert_to_camel_case(msg.proto.name)
                                output_str += ("import { reset" + f"{msg.proto.name}" + " } from '../features/" +
                                               f"{msg_name_camel_cased}Slice';\n")

        if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
            output_str += "import {\n"
            dependent_abb_msg = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
            dependent_abb_msg_camel_cased = convert_to_camel_case(dependent_abb_msg)
            output_str += f"    setSelected{dependent_abb_msg}Id\n"
            output_str += "}"+f" from '../features/{dependent_abb_msg_camel_cased}Slice';\n"
            dependent_to_linked_abb_msg = self.abbreviated_msg_name_to_dependent_msg_name_dict[dependent_abb_msg]
            dependent_to_linked_abb_msg_camel_cased = convert_to_camel_case(dependent_to_linked_abb_msg)
            output_str += "import {\n"
            output_str += "    setMode as setLinkedMode\n"
            output_str += "}" + f" from '../features/{dependent_to_linked_abb_msg_camel_cased}Slice';\n"
        output_str += "/* project constants */\n"
        output_str += "import { Modes, Layouts, DB_ID"
        if layout_type != JsxFileGenPlugin.abbreviated_dependent_type:
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
            output_str += "    addxpath, getTableColumns, getTableRows, getCommonKeyCollections, applyFilter, " \
                          "removeRedundantFieldsFromRows, getWidgetOptionById, getWidgetTitle, getServerUrl\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += "    generateObjectFromSchema, addxpath, clearxpath, getObjectWithLeastId,\n"
            output_str += "    getTableColumns, getTableRows, getCommonKeyCollections, compareJSONObjects, " \
                          "getWidgetOptionById, getWidgetTitle, getServerUrl\n"
        elif layout_type == JsxFileGenPlugin.non_root_type or \
                layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
            output_str += "    getTableColumns, getTableRows, getCommonKeyCollections, lowerFirstLetter, clearxpath, " \
                          "compareJSONObjects, getWidgetOptionById, getWidgetTitle\n"
        else:
            output_str += "    generateObjectFromSchema, addxpath, clearxpath, getObjectWithLeastId, " \
                          "compareJSONObjects,\n"
            output_str += "    getNewItem, getIdFromAbbreviatedKey, getAbbreviatedKeyFromId, createCollections, " \
                          "getWidgetOptionById, getWidgetTitle,\n"
            output_str += ("    getAbbreviatedCollections, getServerUrl, getAbbreviatedDependentWidgets, "
                           "isWebSocketAlive\n")
        output_str += "} from '../utils';\n"
        output_str += "/* custom components */\n"
        output_str += "import WidgetContainer from '../components/WidgetContainer';\n"
        output_str += "import SkeletonField from '../components/SkeletonField';\n"
        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "import AbbreviatedFilterWidget from '../components/AbbreviatedFilterWidget';\n"
        else:
            output_str += "import TableWidget from '../components/TableWidget';\n"
            output_str += "import DynamicMenu from '../components/DynamicMenu';\n"
            if layout_type == JsxFileGenPlugin.repeated_root_type:
                output_str += "import PivotTable from '../components/PivotTable';\n"
                output_str += "import ChartWidget from '../components/ChartWidget';\n"
            else:
                output_str += "import TreeWidget from '../components/TreeWidget';\n"
        if layout_type == JsxFileGenPlugin.root_type or \
                layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "import { Icon } from '../components/Icon';\n"
        if layout_type != JsxFileGenPlugin.non_root_type and layout_type != JsxFileGenPlugin.abbreviated_dependent_type:
            if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                output_str += "import { ConfirmSavePopup, WebsocketUpdatePopup, FormValidation, " \
                              "CollectionSwitchPopup } from '../components/Popup';\n\n"
            else:
                output_str += "import { ConfirmSavePopup, WebsocketUpdatePopup, FormValidation } " \
                              "from '../components/Popup';\n\n"
        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "const getAllWsWorker = new Worker(new URL('../workers/getAllWsHandler.js', " \
                          "import.meta.url));\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        output_str += (f"const getAll{dep_msg_name}WsWorker = new Worker("
                                       "new URL('../workers/getAllWsHandler.js', import.meta.url));\n")
            output_str += "\n"
        else:
            output_str += "\n\n"
        return output_str

    def handle_non_abbreviated_return(self, message_name: str, message_name_camel_cased: str, layout_type: str) -> str:
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str = '    let menu = (\n'
            output_str += '        <DynamicMenu\n'
            output_str += '            name={props.name}\n'
            output_str += '            collections={collections}\n'
            output_str += '            currentSchema={currentSchema}\n'
            output_str += '            commonKeyCollections={commonKeyCollections}\n'
            output_str += '            data={modifiedData}\n'
            output_str += '            disabled={mode !== Modes.EDIT_MODE}\n'
            output_str += '            filters={props.filters}\n'
            output_str += '            onFiltersChange={props.onFiltersChange}\n'
            output_str += '            onButtonToggle={onButtonToggle}\n'
            output_str += '        />\n'
            output_str += '    )\n\n'
            output_str += "    let cleanedRows = [];\n"
            output_str += "    if ([Layouts.PIVOT_TABLE, Layouts.CHART].includes(widgetOption.view_layout)) {\n"
            output_str += "        cleanedRows = removeRedundantFieldsFromRows(rows);\n"
            output_str += "    }\n"
            output_str += "    const pivotTable = (\n"
            output_str += "        <WidgetContainer\n"
            output_str += "            name={props.name}\n"
            output_str += "            title={title}\n"
            output_str += "            menu={menu}\n"
            output_str += "            layout={widgetOption.view_layout}\n"
            output_str += "            onReload={onReload}\n"
            output_str += "            onChangeLayout={onChangeLayout}\n"
            output_str += "            supportedLayouts={[Layouts.TABLE_LAYOUT, Layouts.PIVOT_TABLE, Layouts.CHART]}>\n"
            output_str += "            {cleanedRows.length > 0 && <PivotTable pivotData={cleanedRows} />}\n"
            output_str += "        </WidgetContainer>\n"
            output_str += "    )\n\n"
            output_str += "    const chart = (\n"
            output_str += "        <ChartWidget\n"
            output_str += "            name={props.name}\n"
            output_str += "            title={title}\n"
            output_str += "            layout={widgetOption.view_layout}\n"
            output_str += "            onReload={onReload}\n"
            output_str += "            onChangeLayout={onChangeLayout}\n"
            output_str += "            supportedLayouts={[Layouts.TABLE_LAYOUT, Layouts.PIVOT_TABLE, Layouts.CHART]}\n"
            output_str += "            schema={schema}\n"
            output_str += "            mode={mode}\n"
            output_str += "            menu={menu}\n"
            output_str += "            onChangeMode={onChangeMode}\n"
            output_str += "            rows={cleanedRows}\n"
            output_str += "            chartData={props.chartData}\n"
            output_str += "            onChartDataChange={props.onChartDataChange}\n"
            output_str += "            onChartDelete={props.onChartDelete}\n"
            output_str += "            collections={collections}\n"
            output_str += "            filters={props.filters}\n"
            output_str += "        />\n"
            output_str += "    )\n\n"
        elif layout_type == JsxFileGenPlugin.root_type:
            output_str = "    let menu = (\n"
            output_str += "        <DynamicMenu name={props.name} collections={collections} currentSchema={currentSchema} " \
                          "commonKeyCollections={commonKeyCollections} data={modified" + f"{message_name}" \
                                                                                         "} disabled={mode !== Modes.EDIT_MODE} onButtonToggle={onButtonToggle}>\n"
            output_str += "            {mode === Modes.READ_MODE && _.keys(" + f"{message_name_camel_cased})." \
                                                                               f"length === 0 && _.keys(modified{message_name}).length === 0 &&\n"
            output_str += "                <Icon name='Create' title='Create' " \
                          "onClick={onCreate}><Add fontSize='small' /></Icon>}\n"
            output_str += "        </DynamicMenu>\n"
            output_str += "    )\n\n"
        elif layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
            output_str = "    let menu = <DynamicMenu name={props.name} disabled={mode !== Modes.EDIT_MODE} " \
                         "currentSchema={currentSchema} collections=" \
                         "{collections} commonKeyCollections={commonKeyCollections} data={" \
                         f"modified{message_name}" \
                         "} onButtonToggle={onButtonToggle} />;\n"
        else:
            root_msg_name = self.root_message.proto.name
            output_str = "    let menu = <DynamicMenu name={props.name} disabled={mode !== Modes.EDIT_MODE} " \
                         "currentSchema={currentSchema} xpath={currentSchemaXpath} collections=" \
                         "{collections} commonKeyCollections={commonKeyCollections}" \
                         " data={_.get(modified" + f"{root_msg_name}" + \
                         ", currentSchemaXpath)} onButtonToggle={onButtonToggle} />;\n"
        output_str += "    return (\n"
        output_str += "        <Fragment>\n"
        output_str += "            {widgetOption.view_layout === Layouts.TABLE_LAYOUT ? (\n"
        output_str += "                <TableWidget\n"
        output_str += "                    headerProps={{\n"
        output_str += "                        name: props.name,\n"
        output_str += "                        title: title,\n"
        output_str += "                        layout: widgetOption.view_layout,\n"
        output_str += "                        menu: menu,\n"
        output_str += "                        onChangeLayout: onChangeLayout,\n"
        if layout_type != JsxFileGenPlugin.repeated_root_type:
            output_str += "                        mode: mode,\n"
            output_str += "                        supportedLayouts: [Layouts.TABLE_LAYOUT, Layouts.TREE_LAYOUT],\n"
        else:
            output_str += "                        supportedLayouts: [Layouts.TABLE_LAYOUT, Layouts.PIVOT_TABLE, Layouts.CHART],\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.repeated_root_type:
            if layout_type != JsxFileGenPlugin.repeated_root_type:
                output_str += "                        onChangeMode: onChangeMode,\n"
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
                output_str += "                    index={selected" + f"{message_name}Id" + "}\n"
        else:
            root_msg_name = self.root_message.proto.name
            root_message_name_camel_cased = convert_to_camel_case(root_msg_name)
            output_str += "                    }}\n"
            if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += "                    name={props.name}\n"
            else:
                output_str += "                    name={parentSchemaName}\n"
            output_str += "                    schema={schema}\n"
            if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += "                    data={modified" + f"{message_name}" + "}\n"
                output_str += "                    originalData={" + f"{message_name_camel_cased}" + "}\n"
                output_str += "                    index={selected" + f"{message_name}Id" + "}\n"
            else:
                output_str += "                    data={modified" + f"{root_msg_name}" + "}\n"
                output_str += "                    originalData={" + f"{root_message_name_camel_cased}" + "}\n"
                output_str += "                    index={selected" + f"{root_msg_name}Id" + "}\n"
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
        output_str += "                    enableOverride={widgetOption.enable_override}\n"
        output_str += "                    disableOverride={widgetOption.disable_override}\n"
        output_str += "                    onOverrideChange={onOverrideChange}\n"
        output_str += "                    onFormUpdate={onFormUpdate}\n"
        output_str += "                    formValidation={formValidation}\n"
        output_str += "                    truncateDateTime={truncateDateTime}\n"
        output_str += "                    columnOrders={columnOrders}\n"
        output_str += "                    onColumnOrdersChange={onColumnOrdersChange}\n"
        if layout_type != JsxFileGenPlugin.repeated_root_type:
            output_str += "                    forceUpdate={forceUpdate}\n"
        output_str += "                />\n"
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "            ) : widgetOption.view_layout === Layouts.PIVOT_TABLE ? (\n"
            output_str += "                pivotTable\n"
            output_str += "            ) : widgetOption.view_layout === Layouts.CHART ? (\n"
            output_str += "                chart\n"
        else:
            output_str += "            ) : widgetOption.view_layout === Layouts.TREE_LAYOUT ? (\n"
            output_str += "                <TreeWidget\n"
            output_str += "                    headerProps={{\n"
            output_str += "                        name: props.name,\n"
            output_str += "                        title: title,\n"
            output_str += "                        mode: mode,\n"
            output_str += "                        layout: widgetOption.view_layout,\n"
            output_str += "                        menu: menu,\n"
            output_str += "                        onChangeLayout: onChangeLayout,\n"
            output_str += "                        supportedLayouts: [Layouts.TABLE_LAYOUT, Layouts.TREE_LAYOUT],\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "                        onChangeMode: onChangeMode,\n"
                output_str += "                        onSave: onSave,\n"
                output_str += "                        onReload: onReload,\n"
                output_str += "                    }}\n"
                output_str += "                    name={props.name}\n"
                output_str += "                    schema={schema}\n"
                output_str += "                    data={modified" + f"{message_name}" + "}\n"
                output_str += "                    originalData={" + f"{message_name_camel_cased}" + "}\n"
                output_str += "                    index={selected" + f"{message_name}Id" + "}\n"
            else:
                root_msg_name = self.root_message.proto.name
                root_message_name_camel_cased = convert_to_camel_case(root_msg_name)
                output_str += "                    }}\n"
                if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                    output_str += "                    name={props.name}\n"
                else:
                    output_str += "                    name={parentSchemaName}\n"
                output_str += "                    schema={schema}\n"
                if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                    output_str += "                    data={modified" + f"{message_name}" + "}\n"
                    output_str += "                    originalData={" + f"{message_name_camel_cased}" + "}\n"
                    output_str += "                    index={selected" + f"{message_name}Id" + "}\n"
                else:
                    output_str += "                    data={modified" + f"{root_msg_name}" + "}\n"
                    output_str += "                    originalData={" + f"{root_message_name_camel_cased}" + "}\n"
                    output_str += "                    index={selected" + f"{root_msg_name}Id" + "}\n"
            output_str += "                    mode={mode}\n"
            output_str += "                    onUpdate={onUpdate}\n"
            output_str += "                    error={error}\n"
            output_str += "                    onResetError={onResetError}\n"
            if layout_type == self.non_root_type:
                output_str += "                    xpath={currentSchemaXpath}\n"
            output_str += "                    onUserChange={onUserChange}\n"
            output_str += "                    onButtonToggle={onButtonToggle}\n"
            output_str += "                    onFormUpdate={onFormUpdate}\n"
            output_str += "                    forceUpdate={forceUpdate}\n"
            output_str += "                />\n"
        output_str += "            ) : (\n"
        output_str += "                <h1>Unsupported Layout</h1>\n"
        output_str += "            )}\n"
        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.repeated_root_type or \
                layout_type == JsxFileGenPlugin.repeated_non_root_type:
            output_str += "            <FormValidation\n"
            output_str += "                title={title}\n"
            output_str += "                open={openFormValidationPopup}\n"
            output_str += "                onClose={onCloseFormValidationPopup}\n"
            output_str += "                onContinue={onContinueFormEdit}\n"
            output_str += "                src={formValidation}\n"
            output_str += "            />\n"
            output_str += "            <ConfirmSavePopup\n"
            output_str += "                title={title}\n"
            output_str += "                open={openConfirmSavePopup}\n"
            output_str += "                onClose={onCloseConfirmPopup}\n"
            output_str += "                onSave={onConfirmSave}\n"
            output_str += "                src={activeChanges}\n"
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

    def __handle_const_on_layout(self, message: protogen.Message, layout_type: str) -> str:
        message_name = message.proto.name
        message_name_camel_cased: str = convert_to_camel_case(message_name)
        output_str = ""
        match layout_type:
            case JsxFileGenPlugin.repeated_root_type:
                output_str += "    /* states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}, activeChanges, discardedChanges, openWsPopup," \
                              " loading, error"
                widget_ui_option_value = JsxFileGenPlugin.get_complex_option_value_from_proto(
                    message, JsxFileGenPlugin.flux_msg_widget_ui_data_element)
                if widget_ui_option_value.get(JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field):
                    output_str += ", url"
                output_str += "\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
                if other_file_dependent_msg_name:
                    other_file_dependent_msg_name_camel_cased = convert_to_camel_case(other_file_dependent_msg_name)
                    output_str += "    const {\n"
                    output_str += f"        {other_file_dependent_msg_name_camel_cased}\n"
                    output_str += ("    }" +
                                   f" = useSelector(state => state.{other_file_dependent_msg_name_camel_cased});\n")
                    output_str += f"    const {other_file_dependent_msg_name_camel_cased}Mode = " \
                                  f"useSelector(state => state.{other_file_dependent_msg_name_camel_cased}.mode);\n"
                output_str += "    const { schema, schemaCollections } = useSelector(state => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [mode, setMode] = useState(Modes.READ_MODE);\n"
                output_str += "    const [formValidation, setFormValidation] = useState({});\n"
                output_str += "    const [openConfirmSavePopup, setOpenConfirmSavePopup] = useState(false);\n"
                output_str += "    const [openFormValidationPopup, setOpenFormValidationPopup] = useState(false);\n"
                output_str += "    const [disableWs, setDisableWs] = useState(false);\n"
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                other_proto_file = option_dict.get(JsxFileGenPlugin.widget_ui_option_depending_proto_file_name_field)
                other_proto_mode_name = option_dict.get(
                    JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field)
                if other_proto_file is not None and other_proto_mode_name is None:
                    output_str += "    const [url, setUrl] = useState();\n"
                output_str += "    const getAllWsDict = useRef({});\n"
            case JsxFileGenPlugin.root_type:
                output_str += "    /* states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                              f"modified{message_name}, selected{message_name}Id,\n"
                output_str += ("        userChanges, discardedChanges, activeChanges, openWsPopup, loading, "
                               "error, forceUpdate")
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += ", openConfirmSavePopup, url"
                output_str += "\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
                if other_file_dependent_msg_name is not None and other_file_dependent_msg_name:
                    # if other_file_dependent_msg_name is not None and also not empty str
                    other_file_dependent_msg_name_camel_cased = convert_to_camel_case(other_file_dependent_msg_name)
                    output_str += "    const {\n"
                    output_str += f"        {other_file_dependent_msg_name_camel_cased}\n"
                    output_str += ("    }" +
                                   f" = useSelector(state => state.{other_file_dependent_msg_name_camel_cased});\n")
                    output_str += f"    const {other_file_dependent_msg_name_camel_cased}Mode = " \
                                  f"useSelector(state => state.{other_file_dependent_msg_name_camel_cased}.mode);\n"
                output_str += "    const { schema, schemaCollections } = useSelector(state => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [mode, setMode] = useState(Modes.READ_MODE);\n"
                output_str += "    const [formValidation, setFormValidation] = useState({});\n"
                if not option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "    const [openConfirmSavePopup, setOpenConfirmSavePopup] = useState(false);\n"
                output_str += "    const [openFormValidationPopup, setOpenFormValidationPopup] = useState(false);\n"
                output_str += "    const [disableWs, setDisableWs] = useState(false);\n"
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                other_proto_file = option_dict.get(JsxFileGenPlugin.widget_ui_option_depending_proto_file_name_field)
                # is_id_based = option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field)
                other_proto_mode_name = option_dict.get(
                    JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field)
                if other_proto_file is not None and other_proto_mode_name is None:
                    output_str += "    const [url, setUrl] = useState();\n"
                output_str += "    const getAllWsDict = useRef({});\n"
                output_str += "    const getWsDict = useRef({});\n"
            case JsxFileGenPlugin.non_root_type | JsxFileGenPlugin.abbreviated_dependent_type:
                message_name = self.root_message.proto.name
                message_name_camel_cased = convert_to_camel_case(message_name)
                output_str += "    /* states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}, modified{message_name}, selected{message_name}Id,\n"
                output_str += "        userChanges, loading, error, mode, formValidation, forceUpdate\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                output_str += "    const { schema, schemaCollections } = useSelector(state => state.schema);\n"
            case JsxFileGenPlugin.simple_abbreviated_type | JsxFileGenPlugin.parent_abbreviated_type:
                output_str += "    /* states from redux store */\n"
                output_str += "    const {\n"
                output_str += f"        {message_name_camel_cased}Array, {message_name_camel_cased}, " \
                              f"modified{message_name}, selected{message_name}Id,\n"
                output_str += "        loading, error\n"
                output_str += "    } = useSelector(state => " + f"state.{message_name_camel_cased});\n"
                dependent_message = self.abbreviated_dependent_message_name
                dependent_message_camel_cased = convert_to_camel_case(dependent_message)
                output_str += "    const {\n"
                output_str += f"        {dependent_message_camel_cased}Array, {dependent_message_camel_cased}, " \
                              f"modified{dependent_message}, selected{dependent_message}Id,\n"
                output_str += "        userChanges, discardedChanges, activeChanges, openWsPopup, mode, createMode, " \
                              "openConfirmSavePopup, formValidation, openFormValidationPopup, forceUpdate\n"
                output_str += "    } = useSelector(state => " + f"state.{dependent_message_camel_cased});\n"
                output_str += f"    const dependentLoading = useSelector(state => " \
                              f"state.{dependent_message_camel_cased}.loading);\n"
                if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                    dependent_msg_list_from_another_proto = (
                        self._get_abbreviated_msg_dependent_msg_from_other_proto_file())
                    if dependent_msg_list_from_another_proto:
                        for dep_msg_name in dependent_msg_list_from_another_proto:
                            dep_msg_name_camel_cased = convert_to_camel_case(dep_msg_name)
                            additional_data = f", {dep_msg_name_camel_cased}, modified{dep_msg_name}"
                            output_str += ("    const { "+f"{dep_msg_name_camel_cased}Array"+additional_data+" }" +
                                           f" = useSelector(state => state.{dep_msg_name_camel_cased});\n")
                if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                    dependent_abb_msg = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
                    dependent_abb_msg_camel_cased = convert_to_camel_case(dependent_abb_msg)
                    output_str += "    const { " + f"{dependent_abb_msg_camel_cased}Array" + " } = useSelector(" + \
                                  "state => " + f"state.{dependent_abb_msg_camel_cased});\n"
                    dependent_to_linked_abb_msg = self.abbreviated_msg_name_to_dependent_msg_name_dict[
                        dependent_abb_msg]
                    dependent_to_linked_abb_msg_camel_cased = convert_to_camel_case(dependent_to_linked_abb_msg)
                    output_str += f"    const linkedMode = useSelector(state => " \
                                  f"state.{dependent_to_linked_abb_msg_camel_cased}.mode);\n"
                output_str += "    const { schema, schemaCollections } = useSelector((state) => state.schema);\n"
                output_str += "    /* local react states */\n"
                output_str += "    const [searchValue, setSearchValue] = useState('');\n"
                if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                    output_str += "    const [openCollectionSwitchPopup, setOpenCollectionSwitchPopup] = " \
                                  "useState(false);\n"
                output_str += f"    const [active{dependent_message}List, setActive{dependent_message}List] = " \
                              f"useState([]);\n"
                output_str += f"    const [oldActive{dependent_message}List, setOldActive{dependent_message}List] = " \
                              f"useState(active{dependent_message}List);\n"
                output_str += f"    const prevActive{dependent_message}List = useRef([]);\n"
                output_str += f"    const prevOldActive{dependent_message}List = useRef([]);\n"
                output_str += "    const [disableWs, setDisableWs] = useState(false);\n"
                output_str += "    const getAllWsDict = useRef({});\n"
                output_str += "    const getWsDict = useRef({});\n"
                output_str += "    const socketDict = useRef({});\n"
                output_str += f"    const getAll{dependent_message}Dict = useRef(" + "{});\n"
                if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                    dependent_msg_list_from_another_proto = (
                        self._get_abbreviated_msg_dependent_msg_from_other_proto_file())
                    if dependent_msg_list_from_another_proto:
                        for dep_msg_name in dependent_msg_list_from_another_proto:
                            dep_msg_name_camel_cased = convert_to_camel_case(dep_msg_name)
                            output_str += f"    const getAll{dep_msg_name}Dict = "+"useRef({});\n"
                            output_str += f"    const {dep_msg_name_camel_cased}SocketDict = "+"useRef({});\n"
                            output_str += f"    const {dep_msg_name_camel_cased}ArrayRef = "+"useRef([]);\n"

                output_str += f"    const {dependent_message_camel_cased}ArrayRef = useRef([]);\n"
                output_str += f"    const runFlush = useRef(false);\n"
        return output_str

    def handle_abbreviated_return(self, message: protogen.Message, message_name_camel_cased: str,
                                  layout_type: str) -> str:
        message_name = message.proto.name
        dependent_msg_name = self.abbreviated_dependent_message_name
        dependent_msg_name_camel_cased = convert_to_camel_case(dependent_msg_name)
        output_str = "    let createMenu = '';\n"
        output_str += "    if (mode === Modes.READ_MODE) {\n"
        output_str += "        createMenu = <Icon title='Create' name='Create' " \
                      "onClick={onCreate}><Add fontSize='small' /></Icon>;\n"
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
        output_str += "                        {_.get(modified" + f"{message_name}" + ", loadListFieldAttrs.key) && _.get(" \
                                                                                      "modified" + f"{message_name}" + ", loadListFieldAttrs.key).map((item, index) => {\n"
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
        output_str += "                        name: props.name,\n"
        output_str += "                        mode: mode,\n"
        output_str += "                        menu: createMenu,\n"
        output_str += "                        onChangeMode: onChangeMode,\n"
        output_str += "                        onSave: onSave,\n"
        output_str += "                        onReload: onReload,\n"
        output_str += "                        layout: widgetOption.view_layout,\n"
        output_str += "                        onChangeLayout: onChangeLayout,\n"
        output_str += "                        supportedLayouts: [Layouts.ABBREVIATED_FILTER_LAYOUT, Layouts.PIVOT_TABLE, Layouts.CHART]\n"
        output_str += "                    }}\n"
        output_str += "                    name={props.name}\n"
        output_str += "                    mode={mode}\n"
        output_str += "                    schema={schema}\n"
        output_str += "                    collections={itemCollections}\n"
        output_str += "                    bufferListFieldAttrs={bufferListFieldAttrs}\n"
        output_str += "                    searchValue={searchValue}\n"
        output_str += "                    options={_.get(" + f"{message_name_camel_cased}" + ", bufferListFieldAttrs.key) ? " \
                                                                                              "_.get(" + f"{message_name_camel_cased}" + ", bufferListFieldAttrs.key) : []}\n"
        output_str += "                    onChange={onChange}\n"
        output_str += "                    onLoad={onLoad}\n"
        output_str += "                    loadListFieldAttrs={loadListFieldAttrs}\n"
        output_str += "                    items={_.get(" + f"{message_name_camel_cased}" + ", loadListFieldAttrs.key) ? " \
                                                                                            "_.get(" + f"{message_name_camel_cased}" + ", loadListFieldAttrs.key) : []}\n"
        output_str += "                    activeItems={active" + f"{dependent_msg_name}List" + "}\n"
        output_str += "                    setActiveItems={setActive" + f"{dependent_msg_name}List" + "}\n"
        output_str += "                    setOldActiveItems={setOldActive" + f"{dependent_msg_name}List" + "}\n"
        output_str += "                    selected={selected" + f"{dependent_msg_name}" + "Id}\n"
        output_str += "                    setSelectedItem={setSelectedItem}\n"
        output_str += "                    onSelect={onSelect}\n"
        output_str += "                    onUnload={onUnload}\n"
        output_str += "                    abbreviated={abbreviated}\n"
        output_str += "                    enableOverride={widgetOption.enable_override}\n"
        output_str += "                    disableOverride={widgetOption.disable_override}\n"
        output_str += "                    onOverrideChange={onOverrideChange}\n"
        output_str += "                    itemsMetadata={"f"{dependent_msg_name_camel_cased}" + "Array}\n"
        abb_dependent_message_name = self.abbreviated_dependent_message_name
        abb_dependent_message_name_snake_cased = convert_camel_case_to_specific_case(abb_dependent_message_name)
        abb_dependent_message_name_camel_cased = convert_to_camel_case(abb_dependent_message_name)
        output_str += "                    itemsMetadataDict={{\n"
        output_str += (f"                        '{abb_dependent_message_name_snake_cased}': "
                       f"{dependent_msg_name_camel_cased}Array,\n")
        if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
            dependent_msg_list_from_another_proto = (
                self._get_abbreviated_msg_dependent_msg_from_other_proto_file())
            if dependent_msg_list_from_another_proto:
                for dep_msg in dependent_msg_list_from_another_proto:
                    dep_msg_camel_cased = convert_to_camel_case(dep_msg)
                    dep_msg_snake_cased = convert_camel_case_to_specific_case(dep_msg)
                    output_str += (f"                        '{dep_msg_snake_cased}': "
                                   f"{dep_msg_camel_cased}Array,\n")
        output_str += "                    }}\n"
        output_str += "                    itemSchema={dependentWidgetSchema}\n"
        output_str += "                    itemCollectionsDict={dependentWidgetCollectionsDict}\n"
        if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
            dependent_msg_name = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
            dependent_msg_name_camel_cased = convert_to_camel_case(dependent_msg_name)
            output_str += "                    linkedItemsMetadata={" + f"{dependent_msg_name_camel_cased}Array" + "}\n"
        output_str += "                    alertBubbleSource={loadListFieldAttrs.alertBubbleSource}\n"
        output_str += "                    alertBubbleColorSource={loadListFieldAttrs.alertBubbleColor}\n"
        output_str += "                    error={error}\n"
        output_str += "                    onResetError={onResetError}\n"
        output_str += "                    onButtonToggle={onButtonToggle}\n"
        output_str += "                    collectionIndex={" + f"selected{message_name}Id" + "}\n"
        output_str += "                    truncateDateTime={truncateDateTime}\n"
        output_str += "                    onRefreshItems={onRefreshItems}\n"
        output_str += "                    chartData={props.chartData}\n"
        output_str += "                    onChartDataChange={props.onChartDataChange}\n"
        output_str += "                    onChartDelete={props.onChartDelete}\n"
        output_str += "                    filters={props.filters}\n"
        output_str += "                    onFiltersChange={props.onFiltersChange}\n"
        output_str += "                    dependentLoading={dependentLoading}\n"
        output_str += "                    columnOrders={columnOrders}\n"
        output_str += "                    onColumnOrdersChange={onColumnOrdersChange}\n"
        output_str += "                />\n"
        output_str += "            )}\n"
        output_str += "            <FormValidation\n"
        output_str += "                title={dependentWidgetSchema.title}\n"
        output_str += "                open={openFormValidationPopup}\n"
        output_str += "                onClose={onCloseFormValidationPopup}\n"
        output_str += "                onContinue={onContinueFormEdit}\n"
        output_str += "                src={formValidation}\n"
        output_str += "            />\n"
        output_str += "            <ConfirmSavePopup\n"
        output_str += "                title={dependentWidgetSchema.title}\n"
        output_str += "                open={openConfirmSavePopup}\n"
        output_str += "                onClose={onCloseConfirmPopup}\n"
        output_str += "                onSave={onConfirmSave}\n"
        output_str += "                src={activeChanges}\n"
        output_str += "            />\n"
        output_str += "            <WebsocketUpdatePopup\n"
        output_str += "                title={dependentWidgetSchema.title}\n"
        output_str += "                open={openWsPopup}\n"
        output_str += "                onClose={onClosePopup}\n"
        output_str += "                src={discardedChanges}\n"
        output_str += "            />\n"
        if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
            output_str += "            <CollectionSwitchPopup\n"
            output_str += "                title={title}\n"
            output_str += "                open={openCollectionSwitchPopup}\n"
            output_str += "                onClose={onCloseCollectionSwitchPopup}\n"
            output_str += "                onContinue={onContinueCollectionEdit}\n"
            output_str += "            />\n"
        output_str += "        </Fragment>\n"
        output_str += "    )\n"
        output_str += "}\n\n"

        return output_str

    def _get_abbreviated_msg_dependent_msg_from_other_proto_file(self) -> List[str]:
        abbreviated_other_project_dependent_msg_name_list: List[str] = []
        if self.proto_file_name_to_message_list_dict:
            dependent_message = self.abbreviated_dependent_message_name
            for file_name, message_list in self.proto_file_name_to_message_list_dict.items():
                if file_name != self.current_proto_file_name:
                    for msg in message_list:
                        if JsxFileGenPlugin.is_option_enabled(msg, JsxFileGenPlugin.flux_msg_widget_ui_data_element):
                            option_dict = JsxFileGenPlugin.get_complex_option_value_from_proto(
                                msg, JsxFileGenPlugin.flux_msg_widget_ui_data_element)
                            depending_proto_file_name = option_dict.get(
                                JsxFileGenPlugin.widget_ui_option_depending_proto_file_name_field)
                            depending_proto_model_name = option_dict.get(
                                JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field)
                            is_dependent_for_id = option_dict.get(
                                JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field)
                            if (self.current_proto_file_name == depending_proto_file_name and
                                    dependent_message == depending_proto_model_name and is_dependent_for_id):
                                abbreviated_other_project_dependent_msg_name_list.append(msg.proto.name)
        return abbreviated_other_project_dependent_msg_name_list

    def __get_abb_option_vals_cleaned_message_n_field_list(self, field: protogen.Field) -> List[str]:
        abbreviated_option_val = (
            JsxFileGenPlugin.get_simple_option_value_from_proto(field,
                                                                JsxFileGenPlugin.flux_fld_abbreviated))
        abbreviated_option_val_check_str_list: List[str] = []
        if "^" in abbreviated_option_val:
            abbreviated_option_val_caret_sep = abbreviated_option_val.split("^")
            for abbreviated_option_val_caret_sep_line in abbreviated_option_val_caret_sep:
                if "-" in abbreviated_option_val_caret_sep:
                    abbreviated_option_val_caret_sep_hyphen_sep = (
                        abbreviated_option_val_caret_sep_line.split("-"))
                    for abbreviated_option_val_caret_sep_hyphen_sep_line in (
                            abbreviated_option_val_caret_sep_hyphen_sep):
                        if ":" in abbreviated_option_val_caret_sep_hyphen_sep_line:
                            mapping_key, mapping_value = (
                                abbreviated_option_val_caret_sep_hyphen_sep_line.split(":"))
                            abbreviated_option_val_check_str_list.append(mapping_value)
                        else:
                            abbreviated_option_val_check_str_list.append(
                                abbreviated_option_val_caret_sep_hyphen_sep_line)
                else:
                    if ":" in abbreviated_option_val_caret_sep_line:
                        mapping_key, mapping_value = abbreviated_option_val_caret_sep_line.split(":")
                        abbreviated_option_val_check_str_list.append(mapping_value)
                    else:
                        abbreviated_option_val_check_str_list.append(
                            abbreviated_option_val_caret_sep_line)
        return abbreviated_option_val_check_str_list

    def _is_dependent_msg_from_other_proto_present_in_abb_n_bubble_option(self, abb_message: protogen.Message,
                                                                          dep_message_name: str):
        # First checking in flux_fld_abbreviated
        for field in abb_message.fields:
            if JsxFileGenPlugin.is_option_enabled(field, JsxFileGenPlugin.flux_fld_abbreviated):
                abbreviated_option_val = (
                    JsxFileGenPlugin.get_simple_option_value_from_proto(field,
                                                                        JsxFileGenPlugin.flux_fld_abbreviated))
                abbreviated_option_val_check_str_list: List[str] = (
                    self.__get_abb_option_vals_cleaned_message_n_field_list(field))

                for abbreviated_option_val_check_str in abbreviated_option_val_check_str_list:
                    if abbreviated_option_val_check_str.startswith(dep_message_name):
                        return True

            # Checking in flux_fld_alert_bubble_source
            if JsxFileGenPlugin.is_option_enabled(field, JsxFileGenPlugin.flux_fld_alert_bubble_source):
                alert_bubble_source_option_val = (
                    JsxFileGenPlugin.get_simple_option_value_from_proto(field,
                                                                        JsxFileGenPlugin.flux_fld_alert_bubble_source))
                if alert_bubble_source_option_val.startswith(dep_message_name):
                    return True

            # Checking in flux_fld_alert_bubble_color
            if JsxFileGenPlugin.is_option_enabled(field, JsxFileGenPlugin.flux_fld_alert_bubble_color):
                alert_bubble_color_option_val = (
                    JsxFileGenPlugin.get_simple_option_value_from_proto(field,
                                                                        JsxFileGenPlugin.flux_fld_alert_bubble_color))
                if alert_bubble_color_option_val.startswith(dep_message_name):
                    return True
        return False

    def _if_any_field_mentioned_in_abb_option_has_button_option(self, abb_message: protogen.Message,
                                                                dep_message_name: str) -> bool:
        # First checking in flux_fld_abbreviated
        for field in abb_message.fields:
            if JsxFileGenPlugin.is_option_enabled(field, JsxFileGenPlugin.flux_fld_abbreviated):
                abbreviated_option_val_check_str_list: List[str] = (
                    self.__get_abb_option_vals_cleaned_message_n_field_list(field))

                for abbreviated_option_val_check_str in abbreviated_option_val_check_str_list:
                    if abbreviated_option_val_check_str.startswith(dep_message_name):
                        abbreviated_option_val_check_str_dot_sep = abbreviated_option_val_check_str.split(".")
                        abb_option_val_fld_name = abbreviated_option_val_check_str_dot_sep[1]
                        for msg in self.layout_msg_list:
                            if msg.proto.name == dep_message_name:
                                break
                        else:
                            err_str = f"Couldn't find {dep_message_name} in list of all messaged loaded by base class"
                            logging.error(err_str)
                            raise Exception(err_str)

                        for fld in msg.fields:
                            if fld.proto.name == abb_option_val_fld_name:
                                if JsxFileGenPlugin.is_option_enabled(fld, JsxFileGenPlugin.flux_fld_button):
                                    return True

        return False

    def handle_jsx_const(self, message: protogen.Message, layout_type: str) -> str:
        output_str = self.handle_import_output(message, layout_type)
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        message_name_camel_cased = convert_to_camel_case(message_name)
        root_message_name = ""
        root_message_name_camel_cased = ""
        dependent_message = ""
        dependent_message_camel_cased = ""
        output_str += f"function {message_name}(props) " + "{\n"
        output_str += self.__handle_const_on_layout(message, layout_type)
        output_str += "    /* dispatch to trigger redux actions */\n"
        output_str += "    const dispatch = useDispatch();\n\n"
        output_str += "    const currentSchema = schema[props.name];\n"
        output_str += "    const collections = schemaCollections[props.name];\n"

        match layout_type:
            case JsxFileGenPlugin.repeated_root_type:
                output_str += "    const widgetOption = getWidgetOptionById(props.options, null);\n"
                output_str += "    const title = getWidgetTitle(widgetOption, currentSchema, props.name, null);\n"
                output_str += "    let uiLimit = currentSchema.ui_get_all_limit;\n"
                output_str += f"    let originalData = applyFilter({message_name_camel_cased}, props.filters);\n"
                output_str += "    let modifiedData = addxpath(cloneDeep(originalData));\n"
                output_str += "    let rows = getTableRows(collections, mode, originalData, modifiedData);\n"
            case JsxFileGenPlugin.root_type | JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += f"    const widgetOption = getWidgetOptionById(props.options, selected{message_name}Id, " \
                              f"currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld'));\n"
                output_str += f"    const title = getWidgetTitle(widgetOption, currentSchema, props.name, " \
                              f"{message_name_camel_cased});\n"
                output_str += f"    let rows = getTableRows(collections, mode, {message_name_camel_cased}, " \
                              f"modified{message_name});\n"
            case JsxFileGenPlugin.non_root_type:
                root_message_name = self.root_message.proto.name
                root_message_name_camel_cased = convert_to_camel_case(root_message_name)
                output_str += f"    const widgetOption = getWidgetOptionById(props.options, selected{root_message_name}Id, " \
                              f"currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld'));\n"
                output_str += f"    const title = getWidgetTitle(widgetOption, currentSchema, props.name, " \
                              f"{root_message_name_camel_cased});\n"
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
                output_str += f"    let rows = getTableRows(collections, mode, {root_message_name_camel_cased}, " \
                              f"modified{root_message_name}, currentSchemaXpath);\n"
            case JsxFileGenPlugin.simple_abbreviated_type | JsxFileGenPlugin.parent_abbreviated_type:
                output_str += "    const widgetOption = useMemo(() => {\n"
                output_str += f"        return getWidgetOptionById(props.options, selected{message_name}Id,\n"
                output_str += "            currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld'));\n"
                output_str += "    }, " + f"[selected{message_name}Id, props.options])\n"
                output_str += "    const title = useMemo(() => {\n"
                output_str += "        return getWidgetTitle(widgetOption, currentSchema, props.name, " \
                              f"{message_name_camel_cased});\n"
                output_str += "    }, " + f"[widgetOption, {message_name_camel_cased}])\n"
                output_str += "    const bufferListFieldAttrs = useMemo(() => collections.find(col => " \
                              "col.key.includes('buffer')), []);\n"
                output_str += "    const loadListFieldAttrs = useMemo(() => collections.find(col => " \
                              "col.key.includes('load')), []);\n"
                output_str += "    const abbreviated = loadListFieldAttrs.abbreviated;\n"
                output_str += "    const dependentWidgets = useMemo(() => {\n"
                output_str += "        return getAbbreviatedDependentWidgets(loadListFieldAttrs);\n"
                output_str += "    }, [])\n"
                output_str += "    const dependentWidgetCollectionsDict = useMemo(() => {\n"
                output_str += "        const widgetCollectionsDict = {};\n"
                output_str += "        dependentWidgets.forEach(widgetName => {\n"
                output_str += "            widgetCollectionsDict[widgetName] = schemaCollections[widgetName];\n"
                output_str += "        })\n"
                output_str += "        return widgetCollectionsDict;\n"
                output_str += "    }, [schemaCollections])\n"
                output_str += "    let dependentWidgetSchema = _.get(schema, dependentWidgets[0]);\n"
                output_str += "    if (!dependentWidgetSchema) {\n"
                output_str += "        dependentWidgetSchema = _.get(schema, [SCHEMA_DEFINITIONS_XPATH, " \
                              "dependentWidgets[0]]);\n"
                output_str += "    }\n"
                output_str += "    const itemCollections = useMemo(() => {\n"
                output_str += "        return getAbbreviatedCollections(dependentWidgetCollectionsDict, abbreviated);\n"
                output_str += "    }, [dependentWidgetCollectionsDict])\n"
        output_str += "    const columnOrders = widgetOption.column_orders;\n"
        output_str += "    const truncateDateTime = widgetOption.hasOwnProperty('truncate_date_time') ? " \
                      "widgetOption.truncate_date_time : false;\n\n"
        if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
            dependent_message = self.abbreviated_dependent_message_name
            dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
            if dependent_msg_list_from_another_proto:
                output_str += "    useEffect(() => {\n"
                output_str += f"        prevActive{dependent_message}List.current = active{dependent_message}List;\n"
                output_str += "    }, " + f"[active{dependent_message}List])\n\n"
                output_str += "    useEffect(() => {\n"
                output_str += f"        prevOldActive{dependent_message}List.current = oldActive{dependent_message}List;\n"
                output_str += "    }, " + f"[oldActive{dependent_message}List])\n\n"

                output_str += "    useEffect(() => {\n"
                for dep_msg_name in dependent_msg_list_from_another_proto:
                    output_str += f"        dispatch(setSelected{dep_msg_name}Id(selected{dependent_message}Id));\n"
                for msg in self.root_msg_list:
                    if msg in self.repeated_tree_layout_msg_list or msg in self.repeated_table_layout_msg_list:
                        # taking all repeated root types
                        widget_ui_option_value = JsxFileGenPlugin.get_complex_option_value_from_proto(
                            msg, JsxFileGenPlugin.flux_msg_widget_ui_data_element)
                        if widget_ui_option_value.get(
                                JsxFileGenPlugin.widget_ui_option_depending_proto_file_name_field) == \
                                self.current_proto_file_name and \
                                widget_ui_option_value.get(
                                    JsxFileGenPlugin.widget_ui_option_depending_proto_model_name_field) is not None:
                            output_str += f"        dispatch(reset{msg.proto.name}());\n"
                output_str += "    }, " + f"[selected{dependent_message}Id])\n\n"

        if layout_type not in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "    const tableColumns = getTableColumns(collections, mode, widgetOption.enable_override, " \
                          "widgetOption.disable_override);\n"
            output_str += "    const commonKeyCollections = getCommonKeyCollections(rows, tableColumns);\n\n"

        if layout_type == JsxFileGenPlugin.repeated_root_type or layout_type == JsxFileGenPlugin.root_type:
            other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
            if other_file_dependent_msg_name is not None:
                if other_file_dependent_msg_name:
                    other_file_dependent_msg_name_camel_cased = convert_to_camel_case(other_file_dependent_msg_name)
                    other_file_dependent_msg_name_snake_cased = (
                        convert_camel_case_to_specific_case(other_file_dependent_msg_name))
                    output_str += "    useEffect(() => {\n"
                    output_str += ("        if (currentSchema.connection_details && (currentSchema."
                                   "connection_details.dynamic_url || currentSchema.widget_ui_data_element."
                                   "depends_on_other_model_for_id)) {\n")
                    option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                                        message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                    if (option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field) or
                        option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_dynamic_url_field)):
                        output_str += (f"            const {other_file_dependent_msg_name_camel_cased}Collections = "
                                       f"schemaCollections['{other_file_dependent_msg_name_snake_cased}'];\n")
                        output_str += (f"            const isRunningCheckField = "
                                       f"{other_file_dependent_msg_name_camel_cased}Collections.find("
                                       "col => col.hasOwnProperty('server_running_status')).key;\n")
                        output_str += ("            const serverUrl = getServerUrl(currentSchema, "
                                       f"{other_file_dependent_msg_name_camel_cased}, isRunningCheckField);\n")
                        output_str += "            dispatch(setUrl(serverUrl));\n"
                    else:
                        output_str += f"            const serverUrl = getServerUrl(currentSchema, " \
                                      f"{other_file_dependent_msg_name_camel_cased});\n"
                        output_str += "            setUrl(serverUrl);\n"
                    output_str += "        }\n"
                    output_str += "    },"+f" [{other_file_dependent_msg_name_camel_cased}])\n\n"
                else:
                    output_str += "    useEffect(() => {\n"
                    output_str += "        if (currentSchema.connection_details) {\n"
                    output_str += f"            let serverUrl = getServerUrl(currentSchema);\n"
                    output_str += "            setUrl(serverUrl);\n"
                    output_str += "        }\n"
                    output_str += "    },"+f" [])\n\n"

        output_str += "    useEffect(() => {\n"
        output_str += "        if (mode === Modes.EDIT_MODE) {\n"
        output_str += "            if (widgetOption.hasOwnProperty('edit_layout') && " \
                      "widgetOption.view_layout !== widgetOption.edit_layout) {\n"
        output_str += "                if (currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld')) {\n"
        output_str += "                    props.onChangeLayout(props.name, widgetOption.edit_layout, "
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "null);\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += f"selected{root_message_name}Id);\n"
        else:
            output_str += f"selected{message_name}Id);\n"
        output_str += "                } else {\n"
        output_str += "                    props.onChangeLayout(props.name, widgetOption.edit_layout);\n"
        output_str += "                }\n"
        output_str += "            }\n"
        if layout_type not in [JsxFileGenPlugin.non_root_type, JsxFileGenPlugin.abbreviated_dependent_type]:
            output_str += "            if (currentSchema.widget_ui_data_element.disable_ws_on_edit) {\n"
            output_str += "                setDisableWs(true);\n"
            output_str += "            }\n"
        output_str += "        } else if (mode === Modes.READ_MODE) {\n"
        output_str += "            if (widgetOption.view_layout !== currentSchema.widget_ui_data_element.widget_ui_data[0].view_layout) {\n"
        output_str += "                if (currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld')) {\n"
        output_str += "                    props.onChangeLayout(props.name, currentSchema.widget_ui_data_element.widget_ui_data[0].view_layout, "
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "null);\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += f"selected{root_message_name}Id);\n"
        else:
            output_str += f"selected{message_name}Id);\n"
        output_str += "                } else {\n"
        output_str += "                    props.onChangeLayout(props.name, currentSchema.widget_ui_data_element.widget_ui_data[0].view_layout);\n"
        output_str += "                }\n"
        output_str += "            }\n"
        if layout_type not in [JsxFileGenPlugin.non_root_type, JsxFileGenPlugin.abbreviated_dependent_type]:
            output_str += "            if (currentSchema.widget_ui_data_element.disable_ws_on_edit) {\n"
            output_str += "                setDisableWs(false);\n"
            output_str += "            }\n"
        output_str += "        }\n"
        output_str += "    }, [mode])\n\n"


        if layout_type != JsxFileGenPlugin.non_root_type and layout_type != JsxFileGenPlugin.abbreviated_dependent_type:
            output_str += "    useEffect(() => {\n"
            output_str += "        /* fetch all objects. to be triggered only once when the component loads */\n"
            if layout_type == JsxFileGenPlugin.repeated_root_type or layout_type == JsxFileGenPlugin.root_type:
                other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
                if other_file_dependent_msg_name is not None:
                    output_str += "        if (url) {\n"
                    output_str += f"            dispatch(getAll{message_name}("+"{ url }));\n"
                    output_str += "        }\n"
                    output_str += "    }, [url]);\n\n"
                else:
                    output_str += f"        dispatch(getAll{message_name}());\n"
                    output_str += "    }, []);\n\n"
                    if layout_type == JsxFileGenPlugin.root_type:
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
            else:
                output_str += f"        dispatch(getAll{message_name}());\n"
                if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                    dependent_message = self.abbreviated_dependent_message_name
                    output_str += f"        dispatch(getAll{dependent_message}());\n"
                output_str += "    }, []);\n\n"

        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
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
            dependent_message = self.abbreviated_dependent_message_name
            output_str += f"            setActive{dependent_message}List([]);\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{message_name_camel_cased}Array])\n\n"

        if layout_type in [JsxFileGenPlugin.root_type,
                           JsxFileGenPlugin.simple_abbreviated_type,
                           JsxFileGenPlugin.parent_abbreviated_type]:
            other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
            if other_file_dependent_msg_name is not None and len(other_file_dependent_msg_name) == 0:
                output_str += "    useEffect(() => {\n"
                output_str += ("        /* handles listening for new object. listens to creation of new "
                               "objects added to array.\n")
                output_str += ("         * if selectedId is not set, automatically listens to new object "
                               "created. if multiple object are available,\n")
                output_str += "         * listens to the object with least id\n"
                output_str += "        */\n"
                output_str += (f"        if ({message_name_camel_cased}Array.length > 0 && !selected{message_name}Id"
                               f")") + " {\n"
                output_str += f"            let object = getObjectWithLeastId({message_name_camel_cased}Array);\n"
                output_str += f"            dispatch(setSelected{message_name}Id(object[DB_ID]));\n"
                output_str += "        }\n"
                output_str += "    }, "+f"[{message_name_camel_cased}Array])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        /* on new update on original object from websocket/server, " \
                          "update the modified object\n"
            output_str += "         * from original object by adding xpath and applying any local " \
                          "pending changes if any\n"
            output_str += "        */\n"
            output_str += f"        let modifiedObj = addxpath(cloneDeep({message_name_camel_cased}));\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        _.keys(userChanges).forEach(xpath => {\n"
                output_str += "            let key = xpath.split('.').pop();\n"
                output_str += "            let collection = collections.filter(c => c.key === key)[0];\n"
                output_str += "            if (collection.type !== 'button') {\n"
                output_str += "                _.set(modifiedObj, xpath, userChanges[xpath]);\n"
                output_str += "            }\n"
                output_str += "        })\n"
            output_str += f"        dispatch(setModified{message_name}(modifiedObj));\n"
            if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                dependent_message = self.abbreviated_dependent_message_name
                dependent_message_camel_cased = convert_to_camel_case(dependent_message)
                output_str += f"        let loadedKeys = _.get({message_name_camel_cased}, loadListFieldAttrs.key);\n"
                output_str += "        if (loadedKeys) {\n"
                output_str += f"            if (loadedKeys.length > 0 && !selected{dependent_message}Id) " + "{\n"
                output_str += "                let id = getIdFromAbbreviatedKey(abbreviated, loadedKeys[0]);\n"
                output_str += f"                dispatch(setSelected{dependent_message}Id(id));\n"
                if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                    dependent_abb_msg_name = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
                    output_str += f"                dispatch(setSelected{dependent_abb_msg_name}Id(id));\n"
                output_str += "            }\n"
                output_str += "        }\n"
                if self.is_bool_option_enabled(message, JsxFileGenPlugin.flux_msg_small_sized_collection):
                    output_str += f"        dispatch(getAll{dependent_message}Background());\n"
            output_str += "    }" + f", [{message_name_camel_cased}])\n\n"

        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            abbreviated_dependent_msg_snake_cased = \
                convert_camel_case_to_specific_case(self.abbreviated_dependent_message_name)
            output_str += "    useEffect(() => {\n"
            output_str += f"        {dependent_message_camel_cased}ArrayRef.current = " \
                          f"{dependent_message_camel_cased}Array;\n"
            output_str += "    }, " + f"[{dependent_message_camel_cased}Array])\n\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += "    useEffect(() => {\n"
                        output_str += (f"        {dep_msg_camel_cased}ArrayRef.current = "
                                       f"{dep_msg_camel_cased}Array;\n")
                        output_str += "    }, "+f"[{dep_msg_camel_cased}Array])\n\n"

            output_str += "    useEffect(() => {\n"
            output_str += f"        let loadedKeys = _.get(modified{message_name}, loadListFieldAttrs.key);\n"
            output_str += "        if (loadedKeys && loadedKeys.length === 0) {\n"
            output_str += f"            if (selected{dependent_message}Id) " + "{\n"
            output_str += "                if (mode === Modes.EDIT_MODE) {\n"
            output_str += "                    dispatch(setOpenWsPopup(true));\n"
            output_str += "                }\n"
            output_str += f"                dispatch(reset{dependent_message}());\n"
            output_str += f"                dispatch(resetSelected{dependent_message}Id());\n"
            output_str += f"                dispatch(setModified{dependent_message}(" + "{}));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }" f", [modified{message_name}, mode])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        if (!createMode && selected{dependent_message}Id) " + "{\n"
            output_str += f"            let updatedObj = {dependent_message_camel_cased}Array.filter(strat => " \
                          f"strat[DB_ID] === selected{dependent_message}Id)[0];\n"
            output_str += "            if (updatedObj) {\n"
            output_str += f"                dispatch(set{dependent_message}(updatedObj));\n"
            output_str += "                let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
            output_str += "                _.keys(userChanges).forEach(xpath => {\n"
            output_str += f"                    if (userChanges[DB_ID] === selected{dependent_message}Id) " + "{\n"
            output_str += "                        let key = xpath.split('.').pop();\n"
            output_str += "                        let collection = dependentWidgetCollectionsDict" \
                          f"['{abbreviated_dependent_msg_snake_cased}'].filter(c => c.key === key)[0];\n"
            output_str += "                        if (collection.type !== 'button') {\n"
            output_str += "                            _.set(modifiedObj, xpath, userChanges[xpath]);\n"
            output_str += "                        }\n"
            output_str += "                    } else {\n"
            output_str += "                        dispatch(setUserChanges({}));\n"
            output_str += "                        dispatch(setDiscardedChanges({}));\n"
            output_str += "                    }\n"
            output_str += "                })\n"
            output_str += f"                dispatch(setModified{dependent_message}(modifiedObj));\n"
            output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }" + f", [{dependent_message_camel_cased}Array, selected{dependent_message}Id, " \
                                    "createMode])\n\n"

        if layout_type != JsxFileGenPlugin.non_root_type and layout_type != JsxFileGenPlugin.abbreviated_dependent_type:
            option_dict = {}
            if layout_type == JsxFileGenPlugin.root_type:
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
            if not option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
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
                if (layout_type in [JsxFileGenPlugin.repeated_root_type, JsxFileGenPlugin.root_type] and
                        self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
                    output_str += "        let socket;\n"
                    output_str += "        if (url) {\n"
                    output_str += ("            socket = new WebSocket(`${url.replace('http', 'ws')}/get-all-" +
                                   f"{message_name_snake_cased}"+"-ws`);\n")
                    output_str += "            socket.onmessage = (event) => {\n"
                    output_str += "                let updatedData = JSON.parse(event.data);\n"
                    output_str += "                if (Array.isArray(updatedData)) {\n"
                    output_str += "                    updatedData.forEach(o => {\n"
                    output_str += "                        getAllWsDict.current[o[DB_ID]] = o;\n"
                    output_str += "                    })\n"
                    output_str += "                } else if (_.isObject(updatedData)) {\n"
                    output_str += "                    getAllWsDict.current[updatedData[DB_ID]] = updatedData;\n"
                    output_str += "                }\n"
                    output_str += "            }\n"
                    if layout_type == JsxFileGenPlugin.root_type:
                        output_str += "            socket.onclose = () => {\n"
                        output_str += "                setMode(Modes.DISABLED_MODE);\n"
                        output_str += "            }\n"
                    output_str += "        }\n"
                    output_str += "        /* close the websocket on cleanup */\n"
                    output_str += "        return () => {\n"
                    output_str += "            if (socket) {\n"
                    output_str += "                socket.close();\n"
                    output_str += "            }\n"
                    output_str += "        }\n"
                    output_str += "    }, [url])\n\n"
                else:
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
                    output_str += "        }\n"
                    output_str += "        socket.onclose = () => {\n"
                    if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                        output_str += "            dispatch(setMode(Modes.DISABLED_MODE));\n"
                    else:
                        output_str += "            setMode(Modes.DISABLED_MODE);\n"
                    output_str += "        }\n"
                    output_str += "        /* close the websocket on cleanup */\n"
                    output_str += "        return () => socket.close();\n"
                    output_str += "    }, [])\n\n"
                output_str += "    useEffect(() => {\n"
                output_str += "        const intervalId = setInterval(flushGetAllWs, 250);\n"
                output_str += "        return () => {\n"
                output_str += "            clearInterval(intervalId);\n"
                output_str += "        }\n"
                output_str += "    }, [])\n\n"

        if layout_type == JsxFileGenPlugin.root_type or \
                layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "    const flushGetWs = useCallback(() => {\n"
            output_str += "        /* apply get websocket changes */\n"
            output_str += "        if (_.keys(getWsDict.current).length > 0) {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "            dispatch(setForceUpdate(true));\n"
            output_str += f"            dispatch(set{message_name}Ws(" + "{ dict: cloneDeep(getWsDict.current)" \
                                                                         ", mode, collections }));\n"
            output_str += "            getWsDict.current = {};\n"
            output_str += "        }\n"
            output_str += "    }, [mode])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        /* get websocket. create a websocket client to listen to selected obj interface */\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += f"        if (selected{message_name}Id && !disableWs && url) " + "{\n"
                output_str += "            let socket = new WebSocket(`${url.replace('http', 'ws')}" \
                              f"/get-{message_name_snake_cased}-ws/$" + "{selected" + f"{message_name}" + "Id}`);\n"
            else:
                output_str += f"        if (selected{message_name}Id && !disableWs) " + "{\n"
                output_str += "            let socket = new WebSocket(`${API_ROOT_URL.replace('http', 'ws')}" \
                              f"/get-{message_name_snake_cased}-ws/$" + "{selected" + f"{message_name}" + "Id}`);\n"
            output_str += "            socket.onmessage = (event) => {\n"
            output_str += "                let updatedObj = JSON.parse(event.data);\n"
            output_str += "                getWsDict.current[updatedObj[DB_ID]] = updatedObj;\n"
            output_str += "            }\n"
            output_str += "            /* close the websocket on cleanup */\n"
            output_str += "            return () => socket.close();\n"
            output_str += "        }\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += "    }" + f", [selected{message_name}Id, disableWs, url])\n\n"
            else:
                output_str += "    }" + f", [selected{message_name}Id, disableWs])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        const intervalId = setInterval(flushGetWs, 250);\n"
            output_str += "        return () => {\n"
            output_str += "            clearInterval(intervalId);\n"
            output_str += "        }\n"
            output_str += "    }, [])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        if (forceUpdate) {\n"
            output_str += "            setTimeout(() => dispatch(setForceUpdate(false)), 100);\n"
            output_str += "        }\n"
            output_str += "    }, [forceUpdate])\n\n"

        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            abbreviated_dependent_msg_name = self.abbreviated_dependent_message_name
            abbreviated_dependent_msg_snake_cased = convert_camel_case_to_specific_case(abbreviated_dependent_msg_name)
            abbreviated_dependent_msg_camel_cased = convert_to_camel_case(abbreviated_dependent_msg_name)
            output_str += f"    const flush{dependent_message}GetAllWs = useCallback(() => " + "{\n"
            output_str += "        /* apply get-all websocket changes */\n"
            output_str += "        if (window.Worker && runFlush.current === true) {\n"
            output_str += f"            if (Object.keys(getAll{dependent_message}Dict.current).length > 0) " + "{\n"
            output_str += "                getAllWsWorker.postMessage({ getAllDict: " + \
                          f"cloneDeep(getAll{dependent_message}Dict.current), storedArray: " \
                          f"{abbreviated_dependent_msg_camel_cased}ArrayRef.current" + " });\n"
            output_str += f"                getAll{dependent_message}Dict.current = " + "{};\n"
            output_str += "            }\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += f"            if (Object.keys(getAll{dep_msg_name}Dict.current).length > 0) "+"{\n"
                        output_str += (f"                getAll{dep_msg_name}"+"WsWorker.postMessage({ getAllDict: "
                                       f"cloneDeep(getAll{dep_msg_name}Dict.current), storedArray: "
                                       f"{dep_msg_camel_cased}ArrayRef.current"+" });\n")
                        output_str += f"                getAll{dep_msg_name}Dict.current ="+" {};\n"
                        output_str += "            }\n"
            output_str += "        }\n"
            output_str += "    }, " + f"[])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        if (window.Worker) {\n"
            output_str += "            getAllWsWorker.onmessage = (e) => {\n"
            output_str += "                const [updatedArray] = e.data;\n"
            output_str += "                dispatch(setForceUpdate(true));\n"
            output_str += f"                dispatch(set{dependent_message}" + \
                          "ArrayWs({ data: updatedArray, collections: " \
                          f"dependentWidgetCollectionsDict['{abbreviated_dependent_msg_snake_cased}']" + " }));\n"
            output_str += "            }\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_snake_cased = convert_camel_case_to_specific_case(dep_msg_name)
                        output_str += f"            getAll{dep_msg_name}"+"WsWorker.onmessage = (e) => {\n"
                        output_str += "                const [updatedArray] = e.data;\n"
                        output_str += (f"                dispatch(set{dep_msg_name}"+"ArrayWs({ data: updatedArray, "
                                       f"collections: dependentWidgetCollectionsDict['{dep_msg_snake_cased}']" +
                                       " }));\n")
                        output_str += "            }\n"
            output_str += "        }\n"
            output_str += "        return () => {\n"
            output_str += "            getAllWsWorker.terminate();\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        output_str += f"            getAll{dep_msg_name}WsWorker.terminate();\n"
            output_str += "        }\n"
            output_str += "    }, [getAllWsWorker])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += "        if (disableWs) {\n"
            output_str += "            // close all websockets if disableWs is set to true\n"
            output_str += "            for (let id in socketDict.current) {\n"
            output_str += "                id *= 1;\n"
            output_str += "                let socket = socketDict.current[id];\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                output_str += "                if (isWebSocketAlive(socket)) socket.close();\n"
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                let {dep_msg_camel_cased}Socket = "
                                       f"{dep_msg_camel_cased}SocketDict.current[id];\n")
                    # output_str += "                if (socket) socket.close();\n"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                if (isWebSocketAlive({dep_msg_camel_cased}Socket)) "
                                       f"{dep_msg_camel_cased}Socket.close();\n")
                    output_str += "                delete socketDict.current[id];\n"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += f"                delete {dep_msg_camel_cased}SocketDict.current[id];\n"

                else:
                    output_str += "                if (socket) socket.close();\n"
                    output_str += "                delete socketDict.current[socketId];\n"
            else:
                output_str += "                if (socket) socket.close();\n"
                output_str += "                delete socketDict.current[socketId];\n"
            output_str += "            }\n"
            output_str += "        }" + f" else if (active{dependent_message}List && !_.isEqual(active{dependent_message}List, " \
                          f"oldActive{dependent_message}List)) " + "{\n"
            output_str += f"            runFlush.current = false;\n"
            output_str += f"            const updated{dependent_message}List = " \
                          f"active{dependent_message}List.filter(key => key !== undefined);\n"
            output_str += f"            const loadedIds = updated{dependent_message}List.map(key => " \
                          f"getIdFromAbbreviatedKey(abbreviated, key));\n"
            output_str += "            const createSocket = async (id) => {\n"
            output_str += "                return new Promise((resolve, reject) => {\n"
            output_str += "                    let socket = socketDict.current.hasOwnProperty(id) ? " \
                          "socketDict.current[id] : null;\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                    let {dep_msg_camel_cased}Socket = "
                                       f"{dep_msg_camel_cased}SocketDict.current.hasOwnProperty(id) ? "
                                       f"{dep_msg_camel_cased}SocketDict.current[id] : null;\n")
                    output_str += f"                    if (isWebSocketAlive(socket)"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += f" && isWebSocketAlive({dep_msg_camel_cased}Socket)"
                    output_str += ") {\n"
            output_str += "                        resolve();\n"
            output_str += "                    } else {\n"
            output_str += "                        socket = new WebSocket(`${API_ROOT_URL.replace('http', " \
                          "'ws')}/get-"+f"{abbreviated_dependent_msg_snake_cased}"+"-ws/${id}`);\n"
            output_str += "                        socketDict.current = { ...socketDict.current, [id]: socket };\n"
            output_str += "                        socket.onmessage = (event) => {\n"
            output_str += "                            let updatedObj = JSON.parse(event.data);\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    output_str += (f"                            const "
                                   f"{abbreviated_dependent_msg_camel_cased}Collections = "
                                   f"dependentWidgetCollectionsDict['{abbreviated_dependent_msg_snake_cased}'];\n")
                    output_str += (f"                            const isRunningCheckField = "
                                   f"{abbreviated_dependent_msg_camel_cased}Collections."
                                   "find(col => col.hasOwnProperty('server_running_status')).key;\n")
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        dep_msg_snake_cased = convert_camel_case_to_specific_case(dep_msg_name)
                        output_str += (f"                            const {dep_msg_camel_cased}Schema "
                                       f"= schema['{dep_msg_snake_cased}'];\n")
                        output_str += (f"                            const {dep_msg_camel_cased}Url = "
                                       f"getServerUrl({dep_msg_camel_cased}Schema, updatedObj, "
                                       f"isRunningCheckField);\n")
                        output_str += f"                            if ({dep_msg_camel_cased}Url)"+" {\n"
                        output_str += (f"                                if (!isWebSocketAlive("
                                       f"{dep_msg_camel_cased}Socket))")+" {\n"
                        output_str += (f"                                    {dep_msg_camel_cased}Socket = " +
                                       "new WebSocket(`${" + f"{dep_msg_camel_cased}Url.replace('http', 'ws')"+
                                       "}/get"+f"-{dep_msg_snake_cased}-ws/$"+"{id}`);\n")
                        output_str += (f"                                    {dep_msg_camel_cased}SocketDict."
                                       f"current[id] = {dep_msg_camel_cased}Socket;\n")
                        output_str += (f"                                    {dep_msg_camel_cased}Socket"
                                       ".onmessage = (event) => {\n")
                        output_str += ("                                        let updatedObj = "
                                       "JSON.parse(event.data);\n")
                        output_str += (f"                                        getAll{dep_msg_name}Dict"
                                       ".current[updatedObj[DB_ID]] = updatedObj;\n")
                        output_str += "                                    }\n"
                        output_str += "                                }\n"
                        output_str += "                            }\n"
            output_str += f"                            getAll{dependent_message}Dict.current[updatedObj[DB_ID]] " \
                          f"= updatedObj;\n"
            output_str += "                            resolve();\n"
            output_str += "                        }\n"
            output_str += "                    }\n"
            output_str += "                })\n"
            output_str += "            }\n\n"
            output_str += "            const createAllSockets = async () => {\n"
            output_str += "                Object.keys(socketDict.current).forEach(id => {\n"
            output_str += "                    id *= 1;\n"
            output_str += "                    if (!loadedIds.includes(id)) {\n"
            output_str += "                        let socket = socketDict.current[id];\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                        let {dep_msg_camel_cased}Socket = "
                                       f"{dep_msg_camel_cased}SocketDict.current[id];\n")
                    output_str += "                        if (isWebSocketAlive(socket)) socket.close();\n"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                        if (isWebSocketAlive({dep_msg_camel_cased}Socket)) "
                                       f"{dep_msg_camel_cased}Socket.close();\n")
                    output_str += "                        delete socketDict.current[id];\n"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                        delete {dep_msg_camel_cased}SocketDict."
                                       f"current[id];\n")
                    output_str += "                    }\n"
                    output_str += "                })\n"
                    output_str += "                const socketPromises = loadedIds.map(id => createSocket(id));\n"
                    output_str += "                await Promise.all(socketPromises);\n"
                    output_str += "                runFlush.current = true;\n"
                    output_str += "            }\n"
                    output_str += "            createAllSockets();\n"
                    output_str += "        }\n"
                    output_str += "        return () => {\n"
                    output_str += (f"            if (_.isEqual(active{dependent_message}List, "
                                   f"prevActive{dependent_message}List.current) "
                                   f"&& _.isEqual(oldActive{dependent_message}List, "
                                   f"prevOldActive{dependent_message}List)) "+"{\n")
                    output_str += ("                // no dependency change (except disableWs which is acceptable case "
                                   "for all sockets close)\n")
                    output_str += "                Object.keys(socketDict.current).forEach(id => {\n"
                    output_str += "                    let socket = socketDict.current[id];\n"
                    output_str += "                    if (isWebSocketAlive(socket)) socket.close();\n"
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        output_str += (f"                    let {dep_msg_camel_cased}Socket = "
                                       f"{dep_msg_camel_cased}SocketDict.current[id];\n")
                        output_str += (f"                    if (isWebSocketAlive({dep_msg_camel_cased}Socket)) "
                                       f"{dep_msg_camel_cased}Socket.close();\n")
                    output_str += "                })\n"
                    output_str += "            }\n"
                    output_str += "        }\n"
                    output_str += "    },"+(f" [active{dependent_message}List, oldActive{dependent_message}List, "
                                            f"disableWs])\n\n")
                else:
                    output_str += "                            /* close the websocket on cleanup */\n"
                    output_str += "                            if (socket) socket.close();\n"
                    output_str += "                            delete socketDict.current[id];\n"
                    output_str += "                        }\n"
                    output_str += "                    })\n"
                    output_str += "                    runFlush.current = true;\n"
                    output_str += "                }\n"
                    output_str += "                createAllSockets();\n"
                    output_str += "            }\n"
                    output_str += "        }\n"
                    output_str += "    }" + f", [active{dependent_message}List, oldActive{dependent_message}List, disableWs])\n\n"
            else:
                output_str += "                            /* close the websocket on cleanup */\n"
                output_str += "                            if (socket) socket.close();\n"
                output_str += "                            delete socketDict.current[id];\n"
                output_str += "                        }\n"
                output_str += "                    })\n"
                output_str += "                    runFlush.current = true;\n"
                output_str += "                }\n"
                output_str += "                createAllSockets();\n"
                output_str += "            }\n"
                output_str += "        }\n"
                output_str += "    }" + f", [active{dependent_message}List, oldActive{dependent_message}List, disableWs])\n\n"
            output_str += "    useEffect(() => {\n"
            output_str += f"        const intervalId = setInterval(flush{dependent_message}GetAllWs, 250);\n"
            output_str += "        return () => {\n"
            output_str += "            clearInterval(intervalId);\n"
            output_str += "        }\n"
            output_str += "    }, [])\n\n"

        output_str += "    /* if loading, render the skeleton view */\n"
        output_str += "    if (loading) {\n"
        output_str += "        return (\n"
        output_str += "            <SkeletonField title={title} />\n"
        output_str += "        )\n"
        output_str += "    }\n\n"
        output_str += "    /* if get-all websocket is disconnected, render connection lost view */\n"
        output_str += "    if (mode === Modes.DISABLED_MODE"
        other_file_dependent_msg_name = self._get_ui_msg_dependent_msg_name_from_another_proto(message)
        if other_file_dependent_msg_name:
            other_file_dependent_msg_name_camel_cased = convert_to_camel_case(other_file_dependent_msg_name)
            output_str += f" || {other_file_dependent_msg_name_camel_cased}Mode === Modes.DISABLED_MODE"
        output_str += ") {\n"
        output_str += "        return (\n"
        output_str += "            <WidgetContainer title={title}>\n"
        output_str += "                <h1>Connection lost. Please refresh...</h1>\n"
        output_str += "            </WidgetContainer>\n"
        output_str += "        )\n"
        output_str += "    }\n\n"

        output_str += "    const onChangeLayout = (layoutType) => {\n"
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "        if ([Layouts.PIVOT_TABLE, Layouts.CHART, Layouts.TABLE].includes(layoutType)) {\n"
            output_str += "            setMode(Modes.READ_MODE);\n"
            output_str += "        }\n"
        elif layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "        if ([Layouts.PIVOT_TABLE, Layouts.CHART].includes(layoutType)) {\n"
            output_str += "            dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "        }\n"
        output_str += "        if (currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld')) {\n"
        output_str += "            props.onChangeLayout(props.name, layoutType, "
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "null);\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += f"selected{root_message_name}Id);\n"
        else:
            output_str += f"selected{message_name}Id);\n"
        output_str += "        } else {\n"
        output_str += "            props.onChangeLayout(props.name, layoutType);\n"
        output_str += "        }\n"
        output_str += "    }\n\n"

        output_str += "    const onOverrideChange = (enableOverride, disableOverride) => {\n"
        output_str += "        if (currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld')) {\n"
        output_str += "            props.onOverrideChange(props.name, enableOverride, disableOverride, "
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "null);\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += f"selected{root_message_name}Id);\n"
        else:
            output_str += f"selected{message_name}Id);\n"
        output_str += "        } else {\n"
        output_str += "            props.onOverrideChange(props.name, enableOverride, disableOverride);\n"
        output_str += "        }\n"
        output_str += "    }\n\n"

        output_str += "    const onColumnOrdersChange = (orders) => {\n"
        output_str += "        if (currentSchema.widget_ui_data_element.hasOwnProperty('bind_id_fld')) {\n"
        output_str += "            props.onColumnOrdersChange(props.name, orders, "
        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "null);\n"
        elif layout_type == JsxFileGenPlugin.non_root_type:
            output_str += f"selected{root_message_name}Id);\n"
        else:
            output_str += f"selected{message_name}Id);\n"
        output_str += "        } else {\n"
        output_str += "            props.onColumnOrdersChange(props.name, orders);\n"
        output_str += "        }\n"
        output_str += "    }\n\n"

        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "    /* required fields (loaded & buffered) not found. render error view */\n"
            output_str += "    if (!bufferListFieldAttrs.key || !loadListFieldAttrs.key || !abbreviated) {\n"
            output_str += "        return (\n"
            output_str += "            <Box>{Layouts.ABBREVIATED_FILTER_LAYOUT} not supported. " \
                          "Required fields not found.</Box>\n"
            output_str += "        )\n"
            output_str += "    }\n\n"

        output_str += "    const onResetError = () => {\n"
        output_str += "        dispatch(resetError());\n"
        output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or \
                layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
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
            output_str += "        if (_.keys(formValidation).length > 0) {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "            setOpenFormValidationPopup(true);\n"
            else:
                output_str += "            dispatch(setOpenFormValidationPopup(true));\n"
            output_str += "            return;\n"
            output_str += "        }\n"
            if layout_type == JsxFileGenPlugin.root_type or \
                    layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                output_str += "        let differences = {};\n"
                output_str += "        if (e) {\n"
                if layout_type == JsxFileGenPlugin.root_type:
                    output_str += f"            let modifiedObj = clearxpath(cloneDeep(modified{message_name}));\n"
                    output_str += f"            differences = compareJSONObjects({message_name_camel_cased}, " \
                                  f"modifiedObj);\n"
                else:
                    output_str += f"            let modifiedObj = clearxpath(cloneDeep(modified{dependent_message}));\n"
                    output_str += "            if (createMode) {\n"
                    output_str += "                delete modifiedObj[DB_ID];\n"
                    output_str += "            }\n"
                    output_str += f"            differences = compareJSONObjects({dependent_message_camel_cased}, " \
                                  f"modifiedObj);\n"
                output_str += "            dispatch(setActiveChanges(differences));\n"
                output_str += "        }\n"
            output_str += "        if (e === null && openPopup) {\n"
            if layout_type == JsxFileGenPlugin.root_type or \
                    layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                option_dict = {}
                if layout_type == JsxFileGenPlugin.root_type:
                    option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                        message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
                else:
                    output_str += "            setOpenConfirmSavePopup(true);\n"
            else:
                output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
            output_str += "            return;\n"
            output_str += "        }\n"
            if layout_type == JsxFileGenPlugin.root_type or \
                    layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:

                output_str += "        if (_.keys(differences).length > 0) {\n"
                if layout_type == JsxFileGenPlugin.root_type:
                    option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                        message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                    if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                        output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
                    else:
                        output_str += "            setOpenConfirmSavePopup(true);\n"
                else:
                    output_str += "            dispatch(setOpenConfirmSavePopup(true));\n"
                output_str += "        } else {\n"
                output_str += "            onConfirmSave();\n"
                output_str += "        }\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.non_root_type:
            output_str += "    const onUpdate = (updatedData) => {\n"
            if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            else:
                output_str += f"        dispatch(setModified{root_message_name}(updatedData));\n"
            output_str += "    }\n\n"

        if layout_type != JsxFileGenPlugin.repeated_root_type:
            if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += "    const onUpdate = (updatedData) => {\n"
                output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
                output_str += "    }\n\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                output_str += "    const onButtonToggle = (e, xpath, value, source) => {\n"
            else:
                output_str += "    const onButtonToggle = (e, xpath, value) => {\n"
            output_str += "        let xpathDict = {\n"
            if layout_type == JsxFileGenPlugin.non_root_type:
                output_str += f"            [DB_ID]: selected{root_message_name}Id,\n"
            elif layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                output_str += f"            [DB_ID]: selected{dependent_message}Id,\n"
            elif layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += f"            [DB_ID]: selected{message_name}Id,\n"
            output_str += "            [xpath]: value\n"
            output_str += "        };\n"

            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
                abbreviated_dependent_msg_name = self.abbreviated_dependent_message_name
                abbreviated_dependent_msg_camel_cased = convert_to_camel_case(abbreviated_dependent_msg_name)
                output_str += f"        let originalObj = {abbreviated_dependent_msg_camel_cased};\n"
                output_str += f"        let modifiedObj = modified{abbreviated_dependent_msg_name};\n"
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                        dep_msg_snake_cased = convert_camel_case_to_specific_case(dep_msg_name)
                        if self._if_any_field_mentioned_in_abb_option_has_button_option(message, dep_msg_name):
                            output_str += f"        if (source === '{dep_msg_snake_cased}') "+"{\n"
                            output_str += f"            originalObj = {dep_msg_camel_cased};\n"
                            output_str += f"            modifiedObj = modified{dep_msg_name};\n"
                            output_str += "        }\n"
                output_str += "        modifiedObj = clearxpath(cloneDeep(modifiedObj));\n"
                output_str += "        _.keys(xpathDict).forEach(xpath => {\n"
                output_str += "            _.set(modifiedObj, xpath, xpathDict[xpath]);\n"
                output_str += "        })\n"
                output_str += "        let differences = compareJSONObjects(originalObj, modifiedObj);\n"
                if dependent_msg_list_from_another_proto:
                    for dep_msg_name in dependent_msg_list_from_another_proto:
                        dep_msg_snake_cased = convert_camel_case_to_specific_case(dep_msg_name)
                        if self._if_any_field_mentioned_in_abb_option_has_button_option(message, dep_msg_name):
                            output_str += f"        if (source === '{dep_msg_snake_cased}') "+"{\n"
                            output_str += f"            dispatch(set{dep_msg_name}ActiveChanges(differences));\n"
                            output_str += f"            dispatch(set{dep_msg_name}OpenConfirmSavePopup(true));\n"
                            output_str += f"            return;\n"
                            output_str += "        }\n"
            else:
                if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                    output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{message_name}));\n"
                elif layout_type == JsxFileGenPlugin.non_root_type:
                    output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{root_message_name}));\n"
                else:
                    output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{dependent_message}));\n"
                output_str += "        _.keys(xpathDict).forEach(xpath => {\n"
                output_str += "            _.set(modifiedObj, xpath, xpathDict[xpath]);\n"
                output_str += "        })\n"
                if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                    output_str += f"        let differences = compareJSONObjects({message_name_camel_cased}, modifiedObj);\n"
                elif layout_type == JsxFileGenPlugin.non_root_type:
                    output_str += f"        let differences = compareJSONObjects({root_message_name_camel_cased}, modifiedObj);\n"
                else:
                    output_str += f"        let differences = compareJSONObjects({dependent_message_camel_cased}, modifiedObj);\n"
            output_str += "        dispatch(setActiveChanges(differences));\n"
            if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += f"        if ({message_name_camel_cased}[DB_ID]) " + "{\n"
            elif layout_type == JsxFileGenPlugin.non_root_type:
                output_str += f"        if ({root_message_name_camel_cased}[DB_ID]) " + "{\n"
            else:
                output_str += f"        if ({dependent_message_camel_cased}[DB_ID]) " + "{\n"
            output_str += "            onSave(null, true);\n"
            output_str += "        }\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or \
                layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += "    const onClosePopup = (e, reason) => {\n"
            output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
            output_str += "        dispatch(setOpenWsPopup(false));\n"
            if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
                output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "    }\n\n"
            output_str += "    const onCloseConfirmPopup = (e, reason) => {\n"
            output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
            output_str += "        onReload();\n"
            if layout_type == JsxFileGenPlugin.root_type:
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "        dispatch(setOpenConfirmSavePopup(false));\n"
                else:
                    output_str += "        setOpenConfirmSavePopup(false);\n"
            else:
                output_str += "        dispatch(setOpenConfirmSavePopup(false));\n"
            output_str += "    }\n\n"
            output_str += "    const onCloseFormValidationPopup = (e, reason) => {\n"
            output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
            output_str += "        onReload();\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        setOpenFormValidationPopup(false);\n"
            else:
                output_str += "        dispatch(setOpenFormValidationPopup(false));\n"
            output_str += "    }\n\n"
            output_str += "    const onContinueFormEdit = () => {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        setOpenFormValidationPopup(false);\n"
            else:
                output_str += "        dispatch(setOpenFormValidationPopup(false));\n"
            output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.repeated_root_type:
            output_str += "    const onSave = () => { }\n\n"
            output_str += "    const onUpdate = () => { }\n\n"
            output_str += "    const onButtonToggle = () => { }\n\n"
            output_str += "    const onReload = () => {\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += f"        dispatch(getAll{message_name}("+"{ url }));\n"
            else:
                output_str += f"        dispatch(getAll{message_name}());\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => { }\n\n"
            output_str += "    const onClosePopup = () => { }\n\n"
            output_str += "    const onCloseConfirmPopup = () => { }\n\n"
            output_str += "    const onUserChange = () => { }\n\n"
            output_str += "    const onCloseFormValidationPopup = () => { }\n\n"
            output_str += "    const onContinueFormEdit = () => { }\n\n"
            output_str += "    const onFormUpdate = () => { }\n\n"
            output_str += "    const onChangeMode = () => {\n"
            output_str += "        setMode(Modes.EDIT_MODE);\n"
            output_str += "    }\n\n"

        elif layout_type == JsxFileGenPlugin.root_type:
            output_str += "    const onReload = () => {\n"
            output_str += f"        if (selected{message_name}Id) " + "{\n"
            output_str += f"            let updatedData = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        } else {\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += f"            dispatch(getAll{message_name}("+"{ url }));\n"
            else:
                output_str += f"            dispatch(getAll{message_name}());\n"
            output_str += "        }\n"
            output_str += "        dispatch(setActiveChanges({}));\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onCreate = () => {\n"
            output_str += "        let updatedObj = generateObjectFromSchema(schema, _.get(schema, props.name));\n"
            output_str += "        updatedObj = addxpath(updatedObj);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedObj));\n"
            output_str += "        setMode(Modes.EDIT_MODE);\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => {\n"
            output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{message_name}));\n"
            output_str += f"        if (!_.isEqual({message_name_camel_cased}, modifiedObj)) " + "{\n"
            output_str += f"            if (_.get({message_name_camel_cased}, DB_ID)) " + "{\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += f"                dispatch(update{message_name}("+"{ url, data: activeChanges }));\n"
                output_str += "            } else {\n"
                output_str += f"                dispatch(create{message_name}("+"{ url, data: activeChanges }));\n"
                output_str += "            }\n"
                output_str += "        } else if (_.keys(activeChanges).length > 0) {\n"
                output_str += f"            dispatch(update{message_name}("+"{ url, data: activeChanges }));\n"
            else:
                output_str += f"                dispatch(update{message_name}(activeChanges));\n"
                output_str += "            } else {\n"
                output_str += f"                dispatch(create{message_name}(activeChanges));\n"
                output_str += "            }\n"
                output_str += "        } else if (_.keys(activeChanges).length > 0) {\n"
                output_str += f"            dispatch(update{message_name}(activeChanges));\n"
            output_str += "        }\n"
            output_str += "        /* reset states */\n"
            output_str += "        dispatch(setActiveChanges({}));\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        setMode(Modes.READ_MODE);\n"
            option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
            if option_dict.get(JsxFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                output_str += "        dispatch(setOpenConfirmSavePopup(false));\n"
            else:
                output_str += "        setOpenConfirmSavePopup(false);\n"
            output_str += "    }\n\n"
        elif layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            abbreviated_dependent_msg_camel_cased = convert_to_camel_case(self.abbreviated_dependent_message_name)
            abbreviated_dependent_msg_snake_cased = \
                convert_camel_case_to_specific_case(self.abbreviated_dependent_message_name)
            output_str += "    const onReload = () => {\n"
            output_str += f"        dispatch(getAll{self.abbreviated_dependent_message_name}());\n"
            output_str += f"        if (selected{message_name}Id) " + "{\n"
            output_str += f"            let modifiedObj = addxpath(cloneDeep({message_name_camel_cased}));\n"
            output_str += f"            dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += "        } else {\n"
            output_str += f"            dispatch(getAll{message_name}());\n"
            output_str += "        }\n"
            output_str += f"        if (selected{dependent_message}Id) " + "{\n"
            output_str += f"            let modifiedObj = addxpath(cloneDeep({abbreviated_dependent_msg_camel_cased}))"\
                          ";\n"
            output_str += f"            dispatch(setModified{self.abbreviated_dependent_message_name}(modifiedObj));\n"
            output_str += "        }\n"
            output_str += "        dispatch(setActiveChanges({}));\n"
            output_str += "        dispatch(setUserChanges({}));\n"
            output_str += "        dispatch(setDiscardedChanges({}));\n"
            output_str += "        dispatch(setMode(Modes.READ_MODE));\n"
            output_str += "        dispatch(setCreateMode(false));\n"
            output_str += "        setSearchValue('');\n"
            output_str += "    }\n\n"
            output_str += "    const onCreate = () => {\n"
            output_str += f"        let updatedObj = generateObjectFromSchema(schema, dependentWidgetSchema);\n"
            output_str += "        _.set(updatedObj, DB_ID, NEW_ITEM_ID);\n"
            output_str += "        updatedObj = addxpath(updatedObj);\n"
            output_str += f"        dispatch(setModified{self.abbreviated_dependent_message_name}(updatedObj));\n"
            output_str += f"        dispatch(reset{self.abbreviated_dependent_message_name}());\n"
            output_str += "        dispatch(setCreateMode(true));\n"
            output_str += "        dispatch(setMode(Modes.EDIT_MODE));\n"
            output_str += f"        dispatch(setSelected{self.abbreviated_dependent_message_name}Id(NEW_ITEM_ID));\n"
            output_str += "        let newItem = getNewItem(dependentWidgetCollectionsDict['" \
                          f"{abbreviated_dependent_msg_snake_cased}'], abbreviated);\n"
            output_str += f"        let modifiedObj = cloneDeep(modified{message_name});\n"
            output_str += "        _.get(modifiedObj, loadListFieldAttrs.key).push(newItem);\n"
            output_str += f"        dispatch(setModified{message_name}(modifiedObj));\n"
            output_str += "    }\n\n"
            output_str += "    const onConfirmSave = () => {\n"
            output_str += f"        let modifiedObj = clearxpath(cloneDeep(modified{dependent_message}));\n"
            output_str += "        if (createMode) {\n"
            output_str += "            dispatch(setCreateMode(false));\n"
            output_str += "        }\n"
            output_str += f"        if (!_.isEqual({dependent_message_camel_cased}, modifiedObj)) " + "{\n"
            output_str += f"            if (_.get({dependent_message_camel_cased}, DB_ID)) " + "{\n"
            output_str += f"                dispatch(update{dependent_message}(activeChanges));\n"
            output_str += "            } else {\n"
            if message_name in self.parent_abb_msg_name_to_linked_abb_msg_name_dict.values():
                output_str += f"                dispatch(querySearchNUpdate{dependent_message}(activeChanges));\n"
                output_str += f"                dispatch(setModified{message_name}({message_name_camel_cased}));\n"
            else:
                output_str += f"                dispatch(create{dependent_message}(" \
                              "{ data: activeChanges, abbreviated, loadedKeyName: loadListFieldAttrs.key }));\n"
            output_str += "            }\n"
            output_str += "        } else if (_.keys(activeChanges).length > 0) {\n"
            output_str += f"            dispatch(update{dependent_message}(activeChanges));\n"
            output_str += "        }\n"
            output_str += "        /* reset states */\n"
            output_str += "        dispatch(setActiveChanges({}));\n"
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
            output_str += f"        let index = _.get({message_name_camel_cased}, bufferListFieldAttrs.key).indexOf(" \
                          f"searchValue);\n"
            output_str += "        _.get(updatedData, bufferListFieldAttrs.key).splice(index, 1);\n"
            output_str += "        _.get(updatedData, loadListFieldAttrs.key).push(searchValue);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            output_str += f"        dispatch(update{message_name}(updatedData));\n"
            output_str += "        let id = getIdFromAbbreviatedKey(abbreviated, searchValue);\n"
            output_str += f"        setSelected{self.abbreviated_dependent_message_name}Id(id);\n"
            output_str += "        setSearchValue('');\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                output_str += f"        dispatch(getAll{self.abbreviated_dependent_message_name}Background())\n"
            output_str += "    }\n\n"
            output_str += "    const onUnload = (id) => {\n"
            output_str += f"        let updatedData = cloneDeep({message_name_camel_cased});\n"
            output_str += f"        let abbreviatedKey = getAbbreviatedKeyFromId(_.get({message_name_camel_cased}, " \
                          f"loadListFieldAttrs.key), abbreviated, id);\n"
            output_str += f"        let index = _.get({message_name_camel_cased}, " \
                          "loadListFieldAttrs.key).indexOf(abbreviatedKey);\n"
            output_str += f"        let socket = socketDict.current[id];\n"
            output_str += "        if (socket) {\n"
            output_str += f"            socket.close();\n"
            output_str += "        }\n"
            output_str += f"        _.get(updatedData, loadListFieldAttrs.key).splice(index, 1);\n"
            output_str += f"        _.get(updatedData, bufferListFieldAttrs.key).push(abbreviatedKey);\n"
            output_str += f"        dispatch(setModified{message_name}(updatedData));\n"
            output_str += "        dispatch(update" + f"{message_name}(updatedData));\n"
            output_str += (f"        const updatedArray = {abbreviated_dependent_msg_camel_cased}Array.filter(obj "
                           f"=> obj[DB_ID] !== id);\n")
            output_str += f"        dispatch(set{self.abbreviated_dependent_message_name}Array(updatedArray));\n"
            dependent_msg_list_from_another_proto = self._get_abbreviated_msg_dependent_msg_from_other_proto_file()
            if dependent_msg_list_from_another_proto:
                for dep_msg_name in dependent_msg_list_from_another_proto:
                    dep_msg_camel_cased = convert_to_camel_case(dep_msg_name)
                    output_str += f"        const updated{dep_msg_name}Array = {dep_msg_camel_cased}Array.filter(" \
                                  "obj => obj[DB_ID] !== id);\n"
                    output_str += f"        dispatch(set{dep_msg_name}Array(updated{dep_msg_name}Array));\n"
            output_str += "    }\n\n"
            output_str += "    const onDiscard = () => {\n"
            output_str += "        onReload();\n"
            output_str += "    }\n\n"
            output_str += "    const onSelect = (id) => {\n"
            if layout_type == JsxFileGenPlugin.simple_abbreviated_type:
                output_str += "        id = id * 1;\n"
                output_str += f"        dispatch(setSelected{dependent_message}Id(id));\n"
            elif layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                output_str += "        if (linkedMode === Modes.EDIT_MODE) {\n"
                output_str += "            setOpenCollectionSwitchPopup(true);\n"
                output_str += "        } else {\n"
                output_str += "            id = id * 1;\n"
                output_str += f"            dispatch(setSelected{dependent_message}Id(id));\n"
                dependent_abb_msg = self.parent_abb_msg_name_to_linked_abb_msg_name_dict[message_name]
                output_str += f"            dispatch(setSelected{dependent_abb_msg}Id(id));\n"
                output_str += "        }\n"
            output_str += "    }\n\n"
            output_str += "    const setSelectedItem = (id) => {\n"
            output_str += "        if (id === null) {\n"
            output_str += f"            dispatch(resetSelected{dependent_message}Id());\n"
            output_str += "        } else {\n"
            output_str += f"            dispatch(setSelected{dependent_message}Id(id));\n"
            output_str += "        }\n"
            output_str += "    }\n\n"
            output_str += "    const onRefreshItems = () => {\n"
            output_str += f"        dispatch(getAll{dependent_message}Background());\n"
            output_str += "    }\n\n"
            if layout_type == JsxFileGenPlugin.parent_abbreviated_type:
                output_str += "    const onCloseCollectionSwitchPopup = (e, reason) => {\n"
                output_str += "        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;\n"
                output_str += "        dispatch(setLinkedMode(Modes.READ_MODE));\n"
                output_str += "        setOpenCollectionSwitchPopup(false);\n"
                output_str += "    }\n\n"
                output_str += "    const onContinueCollectionEdit = () => {\n"
                output_str += "        setOpenCollectionSwitchPopup(false);\n"
                output_str += "    }\n\n"

        if layout_type == JsxFileGenPlugin.root_type or layout_type == JsxFileGenPlugin.non_root_type or \
                layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
            output_str += "    const onUserChange = (xpath, value, dict = null) => {\n"
            output_str += "        let updatedData = cloneDeep(userChanges);\n"
            output_str += "        if (dict) {\n"
            if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                output_str += f"            dict[DB_ID] = selected{message_name}Id;\n"
            elif layout_type == JsxFileGenPlugin.non_root_type:
                output_str += f"            dict[DB_ID] = selected{root_message_name}Id;\n"
            output_str += "            updatedData = { ...updatedData, ...dict };\n"
            output_str += "        } else {\n"
            if layout_type == self.root_type:
                output_str += "            updatedData = { ...updatedData, [xpath]: value };\n"
            else:
                if layout_type == JsxFileGenPlugin.abbreviated_dependent_type:
                    output_str += "            updatedData = { ...updatedData, [xpath]: value, [DB_ID]: " \
                                  f"selected{message_name}Id " + "};\n"
                else:
                    output_str += "            updatedData = { ...updatedData, [xpath]: value, [DB_ID]: " \
                                  f"selected{root_message_name}Id " + "};\n"
            output_str += "        }\n"
            output_str += "        dispatch(setUserChanges(updatedData));\n"
            output_str += "    }\n\n"
            output_str += "    const onFormUpdate = (xpath, value) => {\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        setFormValidation((prevState) => {\n"
            else:
                output_str += "        dispatch(setFormValidationWithCallback((prevState) => {\n"
            output_str += "            let updatedData = cloneDeep(prevState);\n"
            output_str += "            if (value) {\n"
            output_str += "                updatedData = { ...updatedData, [xpath]: value };\n"
            output_str += "            } else {\n"
            output_str += "                if (xpath in updatedData) {\n"
            output_str += "                    delete updatedData[xpath];\n"
            output_str += "                }\n"
            output_str += "            }\n"
            output_str += "            return updatedData;\n"
            if layout_type == JsxFileGenPlugin.root_type:
                output_str += "        });\n"
            else:
                output_str += "        }));\n"
            output_str += "    }\n\n"

        if layout_type in [JsxFileGenPlugin.simple_abbreviated_type, JsxFileGenPlugin.parent_abbreviated_type]:
            output_str += self.handle_abbreviated_return(message, message_name_camel_cased, layout_type)
        else:
            output_str += self.handle_non_abbreviated_return(message_name, message_name_camel_cased, layout_type)
        output_str += f"export default React.memo({message_name});\n\n"

        return output_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
        output_dict: Dict[str, str] = {}

        for message in self.layout_msg_list:
            self.root_message = None
            message_name = message.proto.name
            output_dict_key = f"{message_name}.jsx"
            # Abbreviated Case
            if message in self.simple_abbreviated_filter_layout_msg_list:
                self.root_message = message
                for field in message.fields:
                    # It's assumed that abbreviated layout type will also have  some field having flux_fld_abbreviated
                    # set to get abbreviated dependent message name
                    if self.is_option_enabled(field, JsxFileGenPlugin.flux_fld_abbreviated):
                        fld_abbreviated_option_value = \
                            self.get_simple_option_value_from_proto(field,
                                                                    JsxFileGenPlugin.flux_fld_abbreviated)[1:]
                        break
                else:
                    err_str = f"Could not find any field having {JsxFileGenPlugin.flux_fld_abbreviated} option set in " \
                              f"message {message_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                self.abbreviated_dependent_message_name = \
                    self.abbreviated_msg_name_to_dependent_msg_name_dict.get(message.proto.name)
                output_str = self.handle_jsx_const(message, JsxFileGenPlugin.simple_abbreviated_type)
            elif message in self.parent_abbreviated_filter_layout_msg_list:
                self.root_message = message
                self.abbreviated_dependent_message_name = \
                    self.abbreviated_msg_name_to_dependent_msg_name_dict.get(message.proto.name)
                output_str = self.handle_jsx_const(message, JsxFileGenPlugin.parent_abbreviated_type)
            elif message.proto.name in self.abbreviated_msg_name_to_dependent_msg_name_dict.values():
                self.root_message = message
                output_str = self.handle_jsx_const(message, JsxFileGenPlugin.abbreviated_dependent_type)
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
