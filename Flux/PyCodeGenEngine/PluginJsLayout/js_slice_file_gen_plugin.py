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
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, capitalized_to_camel_case


class JsSliceFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    -- Generated for all Json Root messages
    ----- 1. Independent Case - Json Root message (some special treatment for uiLayout message)
    ----- 2. Dependent Case - Json Root message and layout as option set to any of the field type of it
    ----- 3. Abbreviated Case - Json Root message and having relationship as field contains abbreviated option
                                having message name which is dependent on current message
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_jsx_file_convert
        ]
        # key message name is dependent on value message value name
        self.dependent_to_abbreviated_message_relation_dict: Dict[str, str] = {}
        self.dependent_message_list: List[protogen.Message] = []
        self.independent_message_list: List[protogen.Message] = []
        self.repeated_layout_msg_name_list: List[str] = []
        self.current_message_is_dependent: bool | None = None  # True if dependent else false
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix: str = ""
        if (ui_layout_msg_name := os.getenv("UILAYOUT_MESSAGE_NAME")) is not None:
            self.__ui_layout_msg_name = ui_layout_msg_name
        else:
            err_str = f"Env var 'UILAYOUT_MESSAGE_NAME' received as None"
            logging.exception(err_str)
            raise Exception(err_str)

    def load_root_message_to_data_member(self, file: protogen.File):
        """
        Adds root messages to class's data member
        """
        super().load_root_message_to_data_member(file)

        for message in self.root_msg_list:
            if JsSliceFileGenPlugin.flux_msg_widget_ui_data in str(message.proto.options):
                widget_ui_data_option_list_of_dict = \
                    self.get_complex_option_values_as_list_of_dict(message,
                                                                   JsSliceFileGenPlugin.flux_msg_widget_ui_data)[0]
                message_layout_is_repeated = widget_ui_data_option_list_of_dict.get("is_repeated")
                if message_layout_is_repeated is not None and message_layout_is_repeated:
                    self.repeated_layout_msg_name_list.append(message.proto.name)

            for field in message.fields:
                if field.message is not None and \
                        JsSliceFileGenPlugin.flux_msg_widget_ui_data in str(field.message.proto.options):
                    # If field of message datatype of this message is found having widget_ui_data option
                    # with layout field then collecting those messages in dependent_message_list
                    widget_ui_data_option_list_of_dict = \
                        self.get_complex_option_values_as_list_of_dict(field.message,
                                                                       JsSliceFileGenPlugin.flux_msg_widget_ui_data)[0]
                    if "layout" in widget_ui_data_option_list_of_dict:
                        self.dependent_message_list.append(message)
                        break
                    # else not required: Avoid if any field of message type doesn't contain layout options
                # else not required: If couldn't find any field of message type with layout option then avoiding
                # addition of message in dependent_message_list

                # Checking abbreviated dependent relation
                if JsSliceFileGenPlugin.flux_fld_abbreviated in str(field.proto.options):
                    abbreviated_option_value = \
                        self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                         JsSliceFileGenPlugin.flux_fld_abbreviated)
                    dependent_message_name = abbreviated_option_value.split(".")[0][1:]
                    if ":" in dependent_message_name:
                        dependent_message_name = dependent_message_name.split(":")[-1]
                    self.dependent_to_abbreviated_message_relation_dict[dependent_message_name] = message.proto.name
                # else not required: Avoid if field doesn't contain abbreviated option
            else:
                self.independent_message_list.append(message)

    def handle_import_output(self, message: protogen.Message) -> str:
        output_str = "/* redux and third-party library imports */\n"
        output_str += "import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';\n"
        output_str += "import axios from 'axios';\n"
        output_str += "import _, { cloneDeep } from 'lodash';\n"
        output_str += "/* project constants */\n"
        output_str += "import { DB_ID, API_ROOT_URL, Modes } from '../constants';\n"
        output_str += "/* common util imports */\n"
        if not self.current_message_is_dependent:
            if message.proto.name not in self.dependent_to_abbreviated_message_relation_dict.values():
                if message.proto.name in self.repeated_layout_msg_name_list:
                    # Repeated case
                    output_str += "import { getErrorDetails, applyWebSocketUpdate } from '../utils';\n\n"
                else:
                    # Independent case
                    output_str += "import {\n"
                    output_str += "    addxpath, clearxpath, getErrorDetails, applyGetAllWebsocketUpdate, " \
                                  "getObjectWithLeastId,\n"
                    output_str += "    compareObjects, generateRowTrees\n"
                    output_str += "} from '../utils';\n\n"
            else:
                # abbreviated case
                output_str += "import {\n"
                output_str += "    addxpath, clearxpath, getErrorDetails, getObjectWithLeastId, " \
                              "applyGetAllWebsocketUpdate,\n"
                output_str += "    generateObjectFromSchema\n"
                output_str += "} from '../utils';\n\n"
        else:
            dependent_message_name: str | None = None
            message_name = message.proto.name
            if message_name in self.dependent_to_abbreviated_message_relation_dict:
                dependent_message_name = self.dependent_to_abbreviated_message_relation_dict[message_name]
            output_str += "import {\n"
            output_str += "    addxpath, clearxpath, getErrorDetails, applyGetAllWebsocketUpdate,\n"
            output_str += "    compareObjects, generateRowTrees\n"
            output_str += "} from '../utils';\n"
            if dependent_message_name is not None:
                output_str += "/* dependent actions imports */\n"
                output_str += "import { update" + f"{dependent_message_name}" + " } from " \
                              f"'./{capitalized_to_camel_case(dependent_message_name)}Slice';\n\n"
        return output_str

    def handle_get_all_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if message_name not in self.dependent_to_abbreviated_message_relation_dict.values():
            output_str = f"export const getAll{message_name} = createAsyncThunk('{message_name_camel_cased}/getAll'," \
                         " (payload, { rejectWithValue }) => " + "{\n"
            output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-all-{message_name_snake_cased}`)\n"
            output_str += "        .then(res => res.data)\n"
            output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
            output_str += "})\n\n"
        else:
            output_str = f"export const getAll{message_name} = createAsyncThunk('{message_name_camel_cased}/" \
                         "getAll', (payload, { dispatch, getState, rejectWithValue }) => " + "{\n"
            output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-all-{message_name_snake_cased}`)\n"
            output_str += "        .then(res => {\n"
            output_str += "            if (res.data.length === 0) {\n"
            output_str += "                let state = getState();\n"
            output_str += "                let schema = state.schema.schema;\n"
            output_str += f"                let currentSchema = _.get(schema, '{message_name_snake_cased}');\n"
            output_str += f"                let updatedData = generateObjectFromSchema(schema, currentSchema);\n"
            output_str += f"                dispatch(create{message_name}(updatedData));\n"
            output_str += "            }\n"
            output_str += "            return res.data;\n"
            output_str += "        })\n"
            output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)))\n"
            output_str += "})\n\n"
        return output_str

    def handle_get_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f"export const get{message_name} = createAsyncThunk('{message_name_camel_cased}/get', " \
                     "(id, { rejectWithValue }) => " + "{\n"
        output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-{message_name_snake_cased}"+"/${id}`)\n"
        output_str += "        .then(res => res.data)\n"
        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
        output_str += "})\n\n"
        return output_str

    def handle_create_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if not self.current_message_is_dependent:
            output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/create', " \
                         "(payload, { rejectWithValue }) => " + "{\n"
            output_str += "    return axios.post(`${API_ROOT_URL}/create-" + f"{message_name_snake_cased}" + \
                          "`, payload)\n"
            output_str += "        .then(res => res.data)\n"
            output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
            output_str += "})\n\n"
            return output_str
        else:
            if message_name in self.dependent_to_abbreviated_message_relation_dict:
                dependent_message_name = self.dependent_to_abbreviated_message_relation_dict[message_name]
                dependent_message_name_camel_cased = capitalized_to_camel_case(dependent_message_name)
                output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/" \
                             f"create', (payload, "+"{ dispatch, getState, rejectWithValue }) => " + "{\n"
                output_str += "    let { data, abbreviated, loadedKeyName } = payload;\n"
                output_str += "    abbreviated = abbreviated.substring(0, abbreviated.indexOf('$'));\n"
                output_str += "    return axios.post(`${API_ROOT_URL}/create-" + f"{message_name_snake_cased}" + \
                              "`, data)\n"
                output_str += "        .then(res => {\n"
                output_str += "            let state = getState();\n"
                output_str += f"            let updatedData = cloneDeep(state.{dependent_message_name_camel_cased}" \
                              f".{dependent_message_name_camel_cased});\n"
                output_str += f"            let newStrat = res.data;\n"
                output_str += "            let newStratKey = abbreviated.split('-').map(xpath => _.get(newStrat, " \
                              "xpath.substring(xpath.indexOf('.') + 1)));\n"
                output_str += "            newStratKey = newStratKey.join('-');\n"
                output_str += "            _.get(updatedData, loadedKeyName).push(newStratKey);\n"
                output_str += f"            dispatch(update{dependent_message_name}("+"updatedData));\n"
                output_str += "            return res.data;\n"
                output_str += "        })\n"
                output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
                output_str += "})\n\n"
                return output_str
        return ""

    def handle_update_export_out_str(self, message: protogen.Message, message_name: str,
                                     message_name_camel_cased: str) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f"export const update{message_name} = createAsyncThunk('{message_name_camel_cased}/update', " \
                     "(payload, { rejectWithValue }) => "+"{\n"
        option_val_dict = self.get_complex_option_values_as_list_of_dict(message, JsSliceFileGenPlugin.flux_msg_json_root)[0]

        if JsSliceFileGenPlugin.flux_json_root_patch_field in option_val_dict:
            output_str += "    return axios.patch(`${API_ROOT_URL}/patch-"+f"{message_name_snake_cased}"+"`, payload)\n"
        else:
            output_str += "    return axios.put(`${API_ROOT_URL}/put-"+f"{message_name_snake_cased}"+"`, payload)\n"
        output_str += "        .then(res => res.data)\n"
        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
        output_str += "})\n\n"
        return output_str

    def handle_get_all_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        output_str = f"        [getAll{message_name}.pending]: (state) => "+"{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        if not self.current_message_is_dependent and (message_name not in self.repeated_layout_msg_name_list):
            output_str += f"            state.selected{message_name}Id = null;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.fulfilled]: (state, action) => " + "{\n"
        if not self.current_message_is_dependent and message_name not in self.repeated_layout_msg_name_list:
            output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
            if message_name != self.__ui_layout_msg_name:
                output_str += "            if (action.payload.length === 0) {\n"
                output_str += f"                state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += f"                state.modified{message_name} = " \
                              f"initialState.modified{message_name};\n"
                output_str += f"                state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += "            } else if (action.payload.length > 0) {\n"
                output_str += f"                let object = getObjectWithLeastId(action.payload);\n"
                output_str += f"                state.selected{message_name}Id = object[DB_ID];\n"
                output_str += "            }\n"
        else:
            output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
            if message_name not in self.repeated_layout_msg_name_list:
                output_str += f"            state.modified{message_name} = action.payload;\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += "            let { code, message, detail, status } = action.payload;\n"
        output_str += "            state.error = { code, message, detail, status };\n"
        output_str += f"            state.loading = false;\n"
        if message_name in self.repeated_layout_msg_name_list:
            output_str += "        }\n"
        else:
            output_str += "        },\n"
        return output_str

    def handle_get_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        output_str = f"        [get{message_name}.pending]: (state) => " + "{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        output_str += "        },\n"
        output_str += f"        [get{message_name}.fulfilled]: (state, action) => " + "{\n"
        output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
        output_str += f"            state.modified{message_name} = action.payload;\n"
        output_str += f"            state.selected{message_name}Id = state.{message_name_camel_cased}[DB_ID];\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [get{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += "            let { code, message, detail, status } = action.payload;\n"
        output_str += "            state.error = { code, message, detail, status };\n"
        output_str += "            state.loading = false;\n"
        output_str += "        },\n"
        return output_str

    def handle_create_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        output_str = f"        [create{message_name}.pending]: (state) => " + "{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        output_str += "        },\n"
        output_str += f"        [create{message_name}.fulfilled]: (state, action) => " + "{\n"
        output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
        output_str += f"            state.modified{message_name} = action.payload;\n"
        if message_name in self.dependent_to_abbreviated_message_relation_dict.values():
            output_str += f"            state.selected{message_name}Id = action.payload[DB_ID];\n"
        elif not self.current_message_is_dependent and message_name != self.__ui_layout_msg_name:
            output_str += f"            state.selected{message_name}Id = action.payload[DB_ID];\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [create{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += f"            let updatedData = clearxpath(cloneDeep(state.modified{message_name}));\n"
        output_str += "            let { code, message, detail, status } = action.payload;\n"
        output_str += "            state.error = { code, message, detail, status, payload: updatedData };\n"
        output_str += "            state.loading = false;\n"
        output_str += f"            state.modified{message_name} = " \
                      f"addxpath(cloneDeep(state.{message_name_camel_cased}));\n"
        output_str += "        },\n"
        return output_str

    def handle_update_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        output_str = f"        [update{message_name}.pending]: (state) => " + "{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        output_str += "        },\n"
        output_str += f"        [update{message_name}.fulfilled]: (state, action) => " + "{\n"
        output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
        output_str += f"            state.modified{message_name} = action.payload;\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [update{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += f"            let updatedData = clearxpath(cloneDeep(state.modified{message_name}));\n"
        output_str += "            let { code, message, detail, status } = action.payload;\n"
        output_str += "            state.error = { code, message, detail, status, payload: updatedData };\n"
        output_str += f"            state.loading = false;\n"
        output_str += f"            state.modified{message_name} = " \
                      f"addxpath(cloneDeep(state.{message_name_camel_cased}));\n"
        output_str += "        }\n"
        return output_str

    def handle_slice_content(self, message: protogen.Message) -> str:
        output_str = self.handle_import_output(message)
        message_name = message.proto.name
        message_name_camel_cased = capitalized_to_camel_case(message_name)
        output_str += "/* initial redux state */\n"
        output_str += f"const initialState = " + "{\n"
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += f"    {message_name_camel_cased}Array: [],\n"
            output_str += f"    {message_name_camel_cased}: " + "{},\n"
            output_str += f"    modified{message_name}: " + "{},\n"
            output_str += f"    selected{message_name}Id: null,\n"
        else:
            output_str += f"    {message_name_camel_cased}: " + "[],\n"
        output_str += "    loading: false,\n"
        output_str += "    error: null,\n"
        output_str += "    userChanges: {},\n"
        output_str += "    discardedChanges: {},\n"
        output_str += "    openWsPopup: false,\n"
        if self.current_message_is_dependent:
            output_str += "    mode: Modes.READ_MODE,\n"
            output_str += "    createMode: false,\n"
            output_str += "    openConfirmSavePopup: false\n"
        output_str += "}\n\n"
        output_str += self.handle_get_all_export_out_str(message_name, message_name_camel_cased)
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += self.handle_get_export_out_str(message_name, message_name_camel_cased)
            output_str += self.handle_create_export_out_str(message_name, message_name_camel_cased)
            output_str += self.handle_update_export_out_str(message, message_name, message_name_camel_cased)
        output_str += f"const {message_name_camel_cased}Slice = createSlice(" + "{\n"
        output_str += f"    name: '{message_name_camel_cased}',\n"
        output_str += "    initialState: initialState,\n"
        output_str += "    reducers: {\n"
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += f"        set{message_name}Array: (state, action) => "+"{\n"
            output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
            output_str += "        },\n"
            if not self.current_message_is_dependent:
                output_str += f"        set{message_name}ArrayWs: (state, action) => " + "{\n"
                output_str += f"            const dict = action.payload;\n"
                output_str += f"            let updatedArray = state.{message_name_camel_cased}Array;\n"
                output_str += "            _.values(dict).forEach(v => {\n"
                output_str += "                updatedArray = applyGetAllWebsocketUpdate(updatedArray, v);\n"
                output_str += "            })\n"
                output_str += f"            state.{message_name_camel_cased}Array = updatedArray;\n"
                output_str += "            let isDeleted = false;\n"
                output_str += f"            if (state.selected{message_name}Id) " + "{\n"
                output_str += "                isDeleted = true;\n"
                output_str += f"                state.{message_name_camel_cased}Array.forEach(o => " + "{\n"
                output_str += f"                    if (_.get(o, DB_ID) === state.selected{message_name}Id) " + "{\n"
                output_str += "                        isDeleted = false;\n"
                output_str += "                    }\n"
                output_str += "                })\n"
                output_str += "            }\n"
                output_str += "            if (isDeleted) {\n"
                output_str += f"                state.selected{message_name}Id = initialState.selected{message_name}Id;\n"
                output_str += f"                state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "            }\n"
                output_str += "        },\n"
            else:
                output_str += f"        set{message_name}ArrayWs: (state, action) => " + "{\n"
                output_str += "            const { dict, mode, collections } = action.payload;\n"
                output_str += f"            let updatedArray = state.{message_name_camel_cased}Array;\n"
                output_str += "            _.entries(dict).map(([k, v]) => {\n"
                output_str += "                k *= 1;\n"
                output_str += "                let updatedObj = v;\n"
                output_str += "                updatedArray = applyGetAllWebsocketUpdate(updatedArray, updatedObj);\n"
                output_str += f"                state.{message_name_camel_cased}Array = updatedArray;\n"
                output_str += f"                if (k === state.selected{message_name}Id) " + "{\n"
                output_str += "                    let diff = compareObjects(updatedObj, " \
                              f"state.{message_name_camel_cased}, state.{message_name_camel_cased});\n"
                output_str += "                    if (_.keys(updatedObj).length === 1) {\n"
                output_str += f"                        state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                        state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "                    } else {\n"
                output_str += f"                        state.{message_name_camel_cased} = updatedObj;\n"
                output_str += "                    }\n"
                output_str += "                    let trees = generateRowTrees(cloneDeep(updatedObj), collections);\n"
                output_str += "                    let modifiedTrees = generateRowTrees(cloneDeep(" \
                              f"state.modified{message_name}), collections);\n"
                output_str += "                    if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                        if (mode === Modes.EDIT_MODE) {\n"
                output_str += "                            state.openWsPopup = true;\n"
                output_str += "                        } else {\n"
                output_str += "                            let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
                output_str += f"                            state.modified{message_name} = modifiedObj;\n"
                output_str += "                        }\n"
                output_str += "                    } else {\n"
                output_str += "                        _.keys(state.userChanges).map(xpath => {\n"
                output_str += "                            if (diff.includes(xpath) && ! diff.includes(DB_ID)) {\n"
                output_str += "                                state.discardedChanges[xpath] = " \
                              "state.userChanges[xpath];\n"
                output_str += "                                delete state.userChanges[xpath];\n"
                output_str += "                                state.openWsPopup = true;\n"
                output_str += "                            }\n"
                output_str += "                            return;\n"
                output_str += "                        })\n"
                output_str += "                    }\n"
                output_str += "                }\n"
                output_str += "                return;\n"
                output_str += "            })\n"
                output_str += "        },\n"

            output_str += f"        set{message_name}: (state, action) => " + "{\n"
            output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
            output_str += "        },\n"

            if not self.current_message_is_dependent and message_name not in self.dependent_to_abbreviated_message_relation_dict.values():
                output_str += f"        set{message_name}Ws: (state, action) => " + "{\n"
                output_str += "            const { dict, mode, collections } = action.payload;\n"
                output_str += f"            let updatedObj = dict[state.selected{message_name}Id];\n"
                output_str += f"            let diff = compareObjects(updatedObj, state.{message_name_camel_cased}, " \
                              f"state.{message_name_camel_cased});\n"
                output_str += "            if (_.keys(updatedObj).length === 1) {\n"
                output_str += f"                state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "            } else {\n"
                output_str += f"                state.{message_name_camel_cased} = updatedObj;\n"
                output_str += "            }\n"
                output_str += "            let trees = generateRowTrees(cloneDeep(updatedObj), collections);\n"
                output_str += f"            let modifiedTrees = generateRowTrees(cloneDeep(" \
                              f"state.modified{message_name}), collections);\n"
                output_str += "            if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                if (mode === Modes.EDIT_MODE) {\n"
                output_str += "                    state.openWsPopup = true;\n"
                output_str += "                } else {\n"
                output_str += "                    let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
                output_str += f"                    state.modified{message_name} = modifiedObj;\n"
                output_str += "                 }\n"
                output_str += "            } else {\n"
                output_str += "                _.keys(state.userChanges).map(xpath => {\n"
                output_str += "                    if (diff.includes(xpath)) {\n"
                output_str += "                        state.discardedChanges[xpath] = state.userChanges[xpath];\n"
                output_str += "                        delete state.userChanges[xpath];\n"
                output_str += "                        state.openWsPopup = true;\n"
                output_str += "                    }\n"
                output_str += "                    return;\n"
                output_str += "                })\n"
                output_str += "            }\n"
                output_str += "        },\n"
            elif message_name in self.dependent_to_abbreviated_message_relation_dict.values():
                output_str += f"        set{message_name}Ws: (state, action) => " + "{\n"
                output_str += "            const { dict } = action.payload;\n"
                output_str += f"            let updatedObj = dict[state.selected{message_name}Id];\n"
                output_str += "            if (_.keys(updatedObj).length === 1) {\n"
                output_str += f"                state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "            } else {\n"
                output_str += f"                state.{message_name_camel_cased} = updatedObj;\n"
                output_str += "            }\n"
                output_str += "        },\n"

            output_str += f"        reset{message_name}: (state) => " + "{\n"
            output_str += f"            state.{message_name_camel_cased} = initialState.{message_name_camel_cased};\n"
            output_str += "        },\n"
            output_str += f"        setModified{message_name}: (state, action) => " + "{\n"
            output_str += f"            state.modified{message_name} = action.payload;\n"
            output_str += "        },\n"
            output_str += f"        setSelected{message_name}Id: (state, action) => "+"{\n"
            output_str += f"            state.selected{message_name}Id = action.payload;\n"
            output_str += "        },\n"
            output_str += f"        resetSelected{message_name}Id: (state) => "+"{\n"
            output_str += f"            state.selected{message_name}Id = initialState.selected{message_name}Id;\n"
            output_str += "        },\n"
        else:
            output_str += f"        set{message_name}Ws: (state, action) => "+"{\n"
            output_str += "            const { dict, uiLimit } = action.payload;\n"
            output_str += f"            let updated{message_name} = state.{message_name_camel_cased};\n"
            output_str += "            _.values(dict).forEach(v => {\n"
            output_str += f"                updated{message_name} = applyWebSocketUpdate(updated{message_name}, " \
                          f"v, uiLimit);\n"
            output_str += "            })\n"
            output_str += f"            state.{message_name_camel_cased} = updated{message_name};\n"
            output_str += "        },\n"
        output_str += "        resetError: (state) => {\n"
        output_str += "            state.error = initialState.error;\n"
        output_str += "        },\n"
        output_str += "        setUserChanges: (state, action) => {\n"
        output_str += "            state.userChanges = action.payload;\n"
        output_str += "        },\n"
        output_str += "        setDiscardedChanges: (state, action) => {\n"
        output_str += "            state.discardedChanges = action.payload;\n"
        output_str += "        },\n"
        output_str += "        setOpenWsPopup: (state, action) => {\n"
        output_str += "            state.openWsPopup = action.payload;\n"
        output_str += "        },\n"
        if self.current_message_is_dependent:
            output_str += "        setMode: (state, action) => {\n"
            output_str += "            state.mode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setCreateMode: (state, action) => {\n"
            output_str += "            state.createMode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setOpenConfirmSavePopup: (state, action) => {\n"
            output_str += "            state.openConfirmSavePopup = action.payload;\n"
            output_str += "        },\n"
        # output_str += "        }\n"
        output_str += "    },\n"
        output_str += "    extraReducers: {\n"
        output_str += self.handle_get_all_out_str(message_name, message_name_camel_cased)
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += self.handle_get_out_str(message_name, message_name_camel_cased)
            output_str += self.handle_create_out_str(message_name, message_name_camel_cased)
            output_str += self.handle_update_out_str(message_name, message_name_camel_cased)
        output_str += "    }\n"
        output_str += "})\n\n"
        output_str += f"export default {message_name_camel_cased}Slice.reducer;\n\n"
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += "export const {\n"
            output_str += f"    set{message_name}Array, set{message_name}ArrayWs, set{message_name}, "
            if not self.current_message_is_dependent:
                output_str += f"set{message_name}Ws,"
            output_str += "\n"
            output_str += f"    reset{message_name}, setModified{message_name}, setSelected{message_name}Id, " \
                          f"resetSelected{message_name}Id, resetError,\n"
            output_str += "    setUserChanges, setDiscardedChanges, setOpenWsPopup"
            if self.current_message_is_dependent:
                output_str += ", setMode, setCreateMode,  setOpenConfirmSavePopup"
            output_str += "\n"
            output_str += "} = " + f"{message_name_camel_cased}Slice.actions;\n"
        else:
            output_str += "export const { " + f"set{message_name}Ws, resetError"
            output_str += " }" + f" = {message_name_camel_cased}Slice.actions;\n"
        # if message.proto.name == self.__ui_layout_msg_name:

        return output_str

    def handle_jsx_file_convert(self, file: protogen.File) -> Dict[str, str]:
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_dict = {}

        for message in self.root_msg_list:
            if message in self.independent_message_list:
                self.current_message_is_dependent = False
            elif message in self.dependent_message_list:
                self.current_message_is_dependent = True
            else:
                err_str = f"message {message.proto.name} not found neither in dependent_list nor in independent_list"
                logging.exception(err_str)
                raise Exception(err_str)
            message_name_camel_cased = capitalized_to_camel_case(message.proto.name)
            output_dict_key = f"{message_name_camel_cased}Slice.js"
            output_str = self.handle_slice_content(message)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsSliceFileGenPlugin)
