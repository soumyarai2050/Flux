#!/usr/bin/env python
import logging
import os
import re
from typing import List, Callable, Dict
import time
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, capitalized_to_camel_case, \
    convert_to_camel_case, convert_to_capitalized_camel_case, YAMLConfigurationManager

if (project_dir := os.getenv("PROJECT_DIR")) is not None and len(project_dir):
    project_dir_path = PurePath(project_dir)
else:
    err_str = f"Couldn't find 'PROJECT_DIR' env var, value is {project_dir}"
    logging.exception(err_str)
    raise Exception(err_str)
config_yaml_path = project_dir_path / "data" / "config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

def get_native_url_js_layout_var_name():
    cache_override_type = config_yaml_dict.get("cache_override_type")
    if cache_override_type is not None and cache_override_type.lower() == "native":
        return "API_ROOT_CACHE_URL"
    else:
        return "API_ROOT_URL"


class JsSliceFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    -- Generated for all Json Root messages
    ----- 1. Independent Case - Json Root message (some special treatment for uiLayout message and
                                                   dependent widget message of abbreviated widget message)
    ----- 2. Dependent Case - Json Root message and layout as option set to any of the field type of it
    ----- 3. Abbreviated Case - Json Root message and having relationship as field contains abbreviated option
                                having message name which is dependent on current message
                                - dependent_to_abbreviated_relation_msg_name_dict is used to differ between
                                abbreviated type message and msg depending on it
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        # key message name is dependent on value message value name
        self.dependent_to_abbreviated_relation_msg_name_dict: Dict[str, str] = {}
        self.dependent_message_list: List[protogen.Message] = []
        self.independent_message_list: List[protogen.Message] = []
        self.repeated_layout_msg_name_list: List[str] = []
        self.abbreviated_message_list: List[protogen.Message] = []
        self.current_message_is_dependent: bool | None = None  # True if dependent else false
        if (ui_layout_msg_name := os.getenv("UILAYOUT_MESSAGE_NAME")) is not None and len(ui_layout_msg_name):
            self.__ui_layout_msg_name = ui_layout_msg_name
        else:
            err_str = f"Env var 'UILAYOUT_MESSAGE_NAME' received as {ui_layout_msg_name}"
            logging.exception(err_str)
            raise Exception(err_str)

    def load_root_message_to_data_member(self, file: protogen.File):
        """
        Adds root messages to class's data member
        """
        super().load_root_message_to_data_member(file)

        for message in self.root_msg_list:
            if self.is_option_enabled(message, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element):
                widget_ui_data_option_value_dict = \
                    self.get_complex_option_value_from_proto(message, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element)
                message_layout_is_repeated = widget_ui_data_option_value_dict.get("is_repeated")
                if message_layout_is_repeated is not None and message_layout_is_repeated:
                    self.repeated_layout_msg_name_list.append(message.proto.name)

            for field in message.fields:
                if field.message is not None and \
                        self.is_option_enabled(field.message, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element):
                    # If field of message datatype of this message is found having widget_ui_data option
                    # with layout field then collecting those messages in dependent_message_list
                    widget_ui_data_option_value_dict = \
                        self.get_complex_option_value_from_proto(field.message,
                                                                 JsSliceFileGenPlugin.flux_msg_widget_ui_data_element)
                    widget_ui_data_list = (
                        widget_ui_data_option_value_dict.get(
                            BaseJSLayoutPlugin.flux_msg_widget_ui_data_element_widget_ui_data_field))
                    if widget_ui_data_list is not None and widget_ui_data_list:
                        widget_ui_data_dict = widget_ui_data_list[0]
                        if "view_layout" in widget_ui_data_dict:
                            self.dependent_message_list.append(message)
                            break
                        # else not required: Avoid if any field of message type doesn't contain view_layout options
                    # else not required: Avoid if any field of message type doesn't contain widget_ui_data field
                    # in option which internally has view_layout field
                # else not required: If it couldn't find any field of message type with view_layout option
                # then avoiding addition of message in dependent_message_list

                # Checking abbreviated dependent relation
                if self.is_option_enabled(field, JsSliceFileGenPlugin.flux_fld_abbreviated):
                    abbreviated_option_value = \
                        self.get_simple_option_value_from_proto(field,
                                                                JsSliceFileGenPlugin.flux_fld_abbreviated)
                    if any(special_char in abbreviated_option_value for special_char in [":", ".", "-"]):
                        dependent_message_name = abbreviated_option_value.split(".")[0][1:]
                        if ":" in dependent_message_name:
                            dependent_message_name = dependent_message_name.split(":")[-1]
                        self.dependent_to_abbreviated_relation_msg_name_dict[dependent_message_name] = message.proto.name
                        self.abbreviated_message_list.append(message)
                        break
                # else not required: Avoid if field doesn't contain abbreviated option
            else:
                self.independent_message_list.append(message)

        # handling for abbreviated message's dependent message is done specifically in dependent case
        # removing abbreviated message's dependent message if present in independent_message_list and shifting to
        # dependent_message_list
        for abb_dependent_message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
            for message in self.independent_message_list:
                if message.proto.name == abb_dependent_message_name:
                    abb_dependent_message = message
                    self.independent_message_list.remove(abb_dependent_message)
                    self.dependent_message_list.append(abb_dependent_message)

        # checking if any field of abb_dependent_message is not of type of message having
        # widget_ui_data option enabled, raises exception if is found
        for dependent_message in self.dependent_message_list:
            if dependent_message.proto.name in self.dependent_to_abbreviated_relation_msg_name_dict:
                if self.is_option_enabled(dependent_message, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element):
                    for field in dependent_message.fields:
                        if field.message is not None:
                            if self.is_option_enabled(field, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element):
                                err_str_ = ("Dependent message of Abbreviated widget type message if is having "
                                            "widget_ui_data option enabled then none of the fields of this message "
                                            "can be of message type that also has widget_ui_data option enabled, "
                                            "currently message {dependent_message.proto.name} which is dependent "
                                            "message of abbreviated type"
                                            f"{self.dependent_to_abbreviated_relation_msg_name_dict.get(dependent_message.proto.name)}"
                                            f" has field {field.proto.name} of message type "
                                            f"{field.message.proto.name} having widget_ui_data option enabled; "
                                            f"please carefully check for remaining fields of "
                                            f"this message for same issue")
                                logging.exception(err_str_)
                                raise Exception(err_str_)
                # else not required: if abbreviated message's dependent message is not having widget_ui_data option
                # then it is allowed to have fields of message type having widget_ui_data

    def handle_import_output(self, message: protogen.Message) -> str:
        output_str = "/* redux and third-party library imports */\n"
        output_str += "import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';\n"
        output_str += "import axios from 'axios';\n"
        output_str += "import _, { cloneDeep } from 'lodash';\n"
        output_str += "/* project constants */\n"
        output_str += "import { DB_ID, API_ROOT_URL, API_ROOT_CACHE_URL, Modes, PROXY_SERVER } from '../constants';\n"
        output_str += "/* common util imports */\n"
        if not self.current_message_is_dependent:
            if message.proto.name not in self.dependent_to_abbreviated_relation_msg_name_dict.values():
                if message.proto.name in self.repeated_layout_msg_name_list:
                    # Repeated case
                    output_str += ("import { getErrorDetails, applyWebSocketUpdate, clearxpath, addxpath")
                    output_str += " } from '../utils';\n\n"
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
            if message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
                dependent_message_name = self.dependent_to_abbreviated_relation_msg_name_dict[message_name]
            output_str += "import {\n"
            output_str += "    addxpath, clearxpath, getErrorDetails, applyGetAllWebsocketUpdate,\n"
            output_str += "    compareObjects, generateRowTrees\n"
            output_str += "} from '../utils';\n"
            if dependent_message_name is not None:
                output_str += "/* dependent actions imports */\n"
                output_str += "import { update" + f"{dependent_message_name}" + " } from " \
                              f"'./{capitalized_to_camel_case(dependent_message_name)}Slice';\n\n"
        return output_str

    def handle_get_all_export_out_str(self, message: protogen.Message, message_name_camel_cased: str) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = "/* CRUD async actions */\n"
        output_str += f"export const getAll{message_name} = createAsyncThunk('{message_name_camel_cased}/getAll'," \
                      " async (payload, { rejectWithValue }) => " + "{\n"

        if (not self.current_message_is_dependent and
                self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
            widget_ui_option_value = JsSliceFileGenPlugin.get_complex_option_value_from_proto(
                message, JsSliceFileGenPlugin.flux_msg_widget_ui_data_element)
            get_all_override_default_crud = self._get_override_default_get_all_crud(widget_ui_option_value)
            if (message_name in self.repeated_layout_msg_name_list and
                    JsSliceFileGenPlugin.is_option_enabled(message, JsSliceFileGenPlugin.flux_msg_ui_get_all_limit)):
                if get_all_override_default_crud:
                    output_str += "    const { url, uiLimit, endpoint, param } = payload;\n"
                    output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                    output_str += ("    return axios.get(`${serverUrl}/${endpoint}?"
                                   "limit_obj_count=${uiLimit}&${param}`)\n")
                else:
                    output_str += "    const { url, uiLimit } = payload;\n"
                    output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                    output_str += ("    return axios.get(`${serverUrl}/" +
                                   f"get-all-{message_name_snake_cased}?limit_obj_count="
                                   "${uiLimit}`)\n")
            else:
                if get_all_override_default_crud:
                    output_str += "    const { endpoint, param } = payload;\n"
                    output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                    output_str += "    return axios.get(`${serverUrl}/${endpoint}?${param}`)\n"
                else:
                    output_str += "    const { url } = payload;\n"
                    output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                    output_str += "    return axios.get(`${serverUrl}/" + (
                        f"get-all-{message_name_snake_cased}`)\n")
        else:
            if (message_name in self.repeated_layout_msg_name_list and
                    JsSliceFileGenPlugin.is_option_enabled(message, JsSliceFileGenPlugin.flux_msg_ui_get_all_limit)):
                output_str += "    const { uiLimit } = payload;\n"
                output_str += "    return axios.get(`${API_ROOT_URL}/" + (f"get-all-{message_name_snake_cased}?limit_obj_count="
                                                                          "${uiLimit}`)\n")
            else:
                output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-all-{message_name_snake_cased}`)\n"
        output_str += "        .then(res => res.data)\n"
        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
        output_str += "})\n\n"
        if message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
            output_str += (f"export const getAll{message_name}Background = createAsyncThunk("
                           f"'{message_name_camel_cased}/getAllBackground', async (payload, "
                           "{ rejectWithValue }) => {\n")
            output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-all-{message_name_snake_cased}`)\n"
            output_str += "        .then(res => res.data)\n"
            output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
            output_str += "})\n\n"
        return output_str

    def handle_get_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f"export const get{message_name} = createAsyncThunk('{message_name_camel_cased}/get', " \
                     "async (payload, { rejectWithValue }) => " + "{\n"
        output_str += "    const { url, id } = payload;\n"
        output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
        output_str += "    return axios.get(`${serverUrl}/" + f"get-{message_name_snake_cased}"+"/${id}`)\n"
        output_str += "        .then(res => res.data)\n"
        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
        output_str += "})\n\n"
        return output_str

    def handle_create_export_out_str(self, message: protogen.Message, message_name_camel_cased: str) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if not self.current_message_is_dependent:
            output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/create', " \
                         "async (payload, { rejectWithValue }) => " + "{\n"
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                output_str += "    const { url, data } = payload;\n"
                output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                output_str += "    return axios.post(`${serverUrl}/create-" + f"{message_name_snake_cased}" + \
                              "`, data)\n"
            else:
                native_url = get_native_url_js_layout_var_name()
                output_str += "    return axios.post(`${"+f"{native_url}"+"}/create-" + f"{message_name_snake_cased}" + \
                              "`, payload)\n"
            output_str += "        .then(res => res.data)\n"
            output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
            output_str += "})\n\n"
            return output_str
        else:
            if message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
                dependent_message_name = self.dependent_to_abbreviated_relation_msg_name_dict[message_name]
                dependent_message_name_camel_cased = capitalized_to_camel_case(dependent_message_name)
                output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/" \
                             f"create', async (payload, "+"{ dispatch, getState, rejectWithValue }) => " + "{\n"
                output_str += "    let { data, abbreviated, loadedKeyName } = payload;\n"
                output_str += "    abbreviated = abbreviated.split('^')[0].split(':').pop();\n"
                native_url = get_native_url_js_layout_var_name()
                output_str += "    return axios.post(`${"+f"{native_url}"+"}/create-" + f"{message_name_snake_cased}" + \
                              "`, data)\n"
                output_str += "        .then(res => {\n"
                output_str += "            let state = getState();\n"
                output_str += f"            let updatedData = cloneDeep(state.{dependent_message_name_camel_cased}" \
                              f".{dependent_message_name_camel_cased});\n"
                output_str += f"            let newObject = res.data;\n"
                output_str += "            let newObjectKey = abbreviated.split('-').map(xpath => _.get(newObject, " \
                              "xpath.substring(xpath.indexOf('.') + 1)));\n"
                output_str += "            newObjectKey = newObjectKey.join('-');\n"
                output_str += "            if (!_.get(updatedData, loadedKeyName).includes(newObjectKey)) {\n"
                output_str += "                _.get(updatedData, loadedKeyName).push(newObjectKey);\n"
                output_str += f"                dispatch(update{dependent_message_name}("+"updatedData));\n"
                output_str += "            }\n"
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
                     "async (payload, { rejectWithValue }) => "+"{\n"
        option_val_dict = self.get_complex_option_value_from_proto(message, JsSliceFileGenPlugin.flux_msg_json_root)
        if JsSliceFileGenPlugin.flux_json_root_patch_field in option_val_dict:
            if (not self.current_message_is_dependent and
                    self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
                output_str += "    const { url, data } = payload;\n"
                output_str += "    const serverUrl = PROXY_SERVER ? API_ROOT_URL : url;\n"
                output_str += ("    return axios.patch(`${serverUrl}/patch-" +
                               f"{message_name_snake_cased}"+"`, data)\n")
            else:
                native_url = get_native_url_js_layout_var_name()
                output_str += ("    return axios.patch(`${"+f"{native_url}"+"}/patch-" +
                               f"{message_name_snake_cased}"+"`, payload)\n")
        else:
            if (not self.current_message_is_dependent and
                    self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
                output_str += "    const { url, data } = payload;\n"
                output_str += ("    return axios.put(`${url}/put-" +
                               f"{message_name_snake_cased}"+"`, data)\n")
            else:
                native_url = get_native_url_js_layout_var_name()
                output_str += ("    return axios.put(`${"+f"{native_url}"+"}/put-" +
                               f"{message_name_snake_cased}"+"`, payload)\n")
        output_str += "        .then(res => res.data)\n"
        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
        output_str += "})\n\n"
        return output_str

    def handle_get_all_out_str(self, message: protogen.Message, message_name_camel_cased: str) -> str:
        message_name = message.proto.name
        output_str = f"        [getAll{message_name}.pending]: (state) => "+"{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
            message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
        if (not self.current_message_is_dependent and (message_name not in self.repeated_layout_msg_name_list) and
                not option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field)
                and not self.if_msg_used_in_abb_option_value(message)):
            output_str += f"            state.selected{message_name}Id = null;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.fulfilled]: (state, action) => " + "{\n"
        if not self.current_message_is_dependent and message_name not in self.repeated_layout_msg_name_list:
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                if (option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field) and
                        option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_dynamic_url_field)):
                    output_str += (f"            const updatedArray = state.{message_name_camel_cased}Array.filter(obj => "
                                   "action.payload[0][DB_ID] !== obj[DB_ID]);\n")
                    output_str += (f"            state.{message_name_camel_cased}Array = [...updatedArray, "
                                   f"...action.payload];\n")
                else:
                    output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
            else:
                output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
            if message_name != self.__ui_layout_msg_name:
                if (not option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field) and
                        not self.if_msg_used_in_abb_option_value(message)):
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
        elif self.current_message_is_dependent:
            output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
        elif message_name in self.repeated_layout_msg_name_list:
            output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += "            let { code, message, detail, status } = action.payload;\n"
        output_str += "            state.error = { code, message, detail, status };\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        if message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
            output_str += (f"        [getAll{message_name}Background"
                           ".fulfilled]: (state, action) => {\n")
            output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
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
        if message_name in self.repeated_layout_msg_name_list:
            output_str += (f"            state.{message_name_camel_cased}Array = "
                           f"[...state.{message_name_camel_cased}Array, action.payload];\n")
            output_str += f"            state.{message_name_camel_cased} = " + "{};\n"
            output_str += f"            state.modified{message_name} = " + "{};\n"
            output_str += f"            state.selected{message_name}Id = null;\n"
        else:
            output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
            output_str += f"            state.modified{message_name} = action.payload;\n"
            if message_name in self.dependent_to_abbreviated_relation_msg_name_dict.values():
                output_str += f"            state.selected{message_name}Id = action.payload[DB_ID];\n"
            elif self.current_message_is_dependent:
                output_str += f"            state.{message_name_camel_cased}Array = " \
                              f"[...state.{message_name_camel_cased}Array, action.payload];\n"
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

    def handle_update_out_str(self, message: protogen.Message, message_name: str,
                              message_name_camel_cased: str) -> str:
        output_str = f"        [update{message_name}.pending]: (state) => " + "{\n"
        # output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        output_str += "        },\n"
        output_str += f"        [update{message_name}.fulfilled]: (state, action) => " + "{\n"
        if message_name in self.repeated_layout_msg_name_list:
            output_str += f"            const idx = state.{message_name_camel_cased}Array.findIndex(obj => obj[DB_ID] === action.payload[DB_ID]);\n"
            output_str += "            if (idx !== -1) {\n"
            output_str += f"                state.{message_name_camel_cased}Array[idx] = action.payload;\n"
            output_str += "            }\n"
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
        option_value_dict_list = \
            JsSliceFileGenPlugin.get_complex_option_value_from_proto(message, JsSliceFileGenPlugin.flux_msg_json_query,
                                                                     is_option_repeated=True)
        if option_value_dict_list:
            for option_value_dict in option_value_dict_list:
                if option_value_dict.get(JsSliceFileGenPlugin.flux_json_query_require_js_slice_changes_field):
                    query_name = option_value_dict.get(JsSliceFileGenPlugin.flux_json_query_name_field)
                    query_name_capitalized_camel_cased = convert_to_capitalized_camel_case(query_name)
                    output_str += "        },\n"
                    output_str += f"        [query{query_name_capitalized_camel_cased}.pending]: (state) => "+"{\n"
                    output_str += f"            state.error = null;\n"
                    output_str += "        },\n"
                    output_str += f"        [query{query_name_capitalized_camel_cased}.fulfilled]: (state, action) => "+"{\n"
                    output_str += f"            const index = state.{message_name_camel_cased}Array.findIndex(obj => " \
                                  f"obj[DB_ID] === action.payload[DB_ID]);\n"
                    output_str += f"            state.{message_name_camel_cased}Array[index] = action.payload;\n"
                    output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
                    output_str += f"            state.modified{message_name} = action.payload;\n"
                    output_str += f"            state.selected{message_name}Id = action.payload[DB_ID];\n"
                    output_str += "        },\n"
                    output_str += f"        [query{query_name_capitalized_camel_cased}.rejected]: (state, action) => "+"{\n"
                    output_str += f"            let updatedData = clearxpath(cloneDeep(state.modified{message_name}));\n"
                    output_str += "            let { code, message, detail, status } = action.payload;\n"
                    output_str += "            state.error = { code, message, detail, status, payload: updatedData };\n"
                    output_str += f"            state.modified{message_name} = addxpath(cloneDeep(" \
                                  f"state.{message_name_camel_cased}));\n"
        output_str += "        }\n"
        return output_str

    def handle_additional_async_helper_actions(self, message: protogen.Message) -> str:
        output_str = ""
        message_name = message.proto.name
        message_name_camel_cased = capitalized_to_camel_case(message_name)
        if message_name not in self.repeated_layout_msg_name_list:
            option_value_dict_list = \
                JsSliceFileGenPlugin.get_complex_option_value_from_proto(message, JsSliceFileGenPlugin.flux_msg_json_query,
                                                                         is_option_repeated=True)
            if option_value_dict_list:
                for option_value_dict in option_value_dict_list:
                    if option_value_dict.get(JsSliceFileGenPlugin.flux_json_query_require_js_slice_changes_field):
                        query_name = option_value_dict.get(JsSliceFileGenPlugin.flux_json_query_name_field)
                        query_name_capitalized_camel_cased = convert_to_capitalized_camel_case(query_name)
                        output_str += f"/* additional queries actions */\n"
                        output_str += f"export const query{query_name_capitalized_camel_cased} = createAsyncThunk(" \
                                      f"'{message_name_camel_cased}/query{query_name_capitalized_camel_cased}', " \
                                      "async (payload, {rejectWithValue}) => {\n"
                        native_url = get_native_url_js_layout_var_name()
                        output_str += "    return axios.patch(`${"+f"{native_url}"+"}/query-"+f"{query_name}`, payload)\n"
                        output_str += "        .then(res => res.data[0])\n"
                        output_str += "        .catch(err => rejectWithValue(getErrorDetails(err)));\n"
                        output_str += "})\n\n"
            output_str += "/* additional async helper actions with callback to support frequent " \
                          "state updates using redux-toolkit */\n"
            output_str += f"export const set{message_name}ArrayWithCallback = createAsyncThunk('" \
                          f"{message_name_camel_cased}/set{message_name}WithCallback', async (callback, " + \
                          "{ getState, dispatch }) => {\n"
            output_str += "\tconst { "+f"{message_name_camel_cased}"+"Array } = getState()." + \
                          f"{message_name_camel_cased}"+";\n"
            output_str += f"\tconst updatedData = callback({message_name_camel_cased}Array);\n"
            output_str += f"\tdispatch(set{message_name}Array(updatedData));\n"
            output_str += "})\n\n"
            output_str += f"export const set{message_name}WithCallback = createAsyncThunk('" \
                          f"{message_name_camel_cased}/set{message_name}WithCallback', async (callback," + \
                          " { getState, dispatch }) => {\n"
            output_str += "\tconst { "+f"{message_name_camel_cased}"+" } = getState()." + \
                          f"{message_name_camel_cased}"+";\n"
            output_str += f"\tconst updatedData = callback({message_name_camel_cased});\n"
            output_str += f"\tdispatch(set{message_name}(updatedData));\n"
            output_str += "})\n\n"
            output_str += f"export const setModified{message_name}WithCallback = createAsyncThunk('" \
                          f"{message_name_camel_cased}/setModified{message_name}WithCallback', async (callback, " + \
                          "{ getState, dispatch }) => {\n"
            output_str += "\tconst { modified"+f"{message_name}"+" } = getState()." + \
                          f"{message_name_camel_cased}"+";\n"
            output_str += f"\tconst updatedData = callback(modified{message_name});\n"
            output_str += f"\tdispatch(setModified{message_name}(updatedData));\n"
            output_str += "})\n\n"
        output_str += "export const setUserChangesWithCallback = createAsyncThunk(" \
                      f"'{message_name_camel_cased}/setUserChangesWithCallback', async (callback, " + \
                      "{ getState, dispatch }" + ") => {\n"
        output_str += "\tconst { userChanges } = getState()." + f"{message_name_camel_cased};\n"
        output_str += "\tconst updatedData = callback(userChanges);\n"
        output_str += "\tdispatch(setUserChanges(updatedData));\n"
        output_str += "})\n\n"
        output_str += "export const setDiscardedChangesWithCallback = createAsyncThunk(" \
                      f"'{message_name_camel_cased}/setDiscardedChangesWithCallback', " \
                      f"async (callback, " + "{ getState, dispatch }) => {\n"
        output_str += "\tconst { discardedChanges } = getState()." + f"{message_name_camel_cased};\n"
        output_str += "\tconst updatedData = callback(discardedChanges);\n"
        output_str += "\tdispatch(setDiscardedChanges(updatedData));\n"
        output_str += "})\n\n"
        output_str += "export const setActiveChangesWithCallback = createAsyncThunk('" \
                      f"{message_name_camel_cased}/setActiveChangesWithCallback', async (callback, " + \
                      "{ getState, dispatch }) => {\n"
        output_str += "\tconst { activeChanges } = getState()." + f"{message_name_camel_cased};\n"
        output_str += "\tconst updatedData = callback(activeChanges);\n"
        output_str += "\tdispatch(setActiveChanges(updatedData));\n"
        output_str += "})\n\n"
        if message_name in self.dependent_to_abbreviated_relation_msg_name_dict:
            output_str += "export const setFormValidationWithCallback = createAsyncThunk('" \
                          f"{message_name_camel_cased}/setFormValidationWithCallback', async (callback," + \
                          " { getState, dispatch }) => {\n"
            output_str += "\tconst { formValidation } = getState()." + f"{message_name_camel_cased};\n"
            output_str += "\tconst updatedData = callback(formValidation);\n"
            output_str += "\tdispatch(setFormValidation(updatedData));\n"
            output_str += "})\n\n"
        output_str += "/* redux-toolkit slice */\n"
        return output_str

    def handle_slice_content(self, message: protogen.Message) -> str:
        output_str = self.handle_import_output(message)
        message_name = message.proto.name
        message_name_camel_cased = capitalized_to_camel_case(message_name)
        output_str += "/* initial redux state */\n"
        output_str += f"const initialState = " + "{\n"
        output_str += f"    {message_name_camel_cased}Array: [],\n"
        output_str += f"    {message_name_camel_cased}: " + "{},\n"
        output_str += f"    modified{message_name}: " + "{},\n"
        output_str += f"    selected{message_name}Id: null,\n"
        if message_name == self.__ui_layout_msg_name:
            output_str += "    loading: true,\n"
        else:
            output_str += "    loading: false,\n"
        output_str += "    error: null,\n"
        output_str += "    userChanges: {},\n"
        output_str += "    discardedChanges: {},\n"
        output_str += "    activeChanges: {},\n"
        output_str += "    openWsPopup: false,\n"
        output_str += "    forceUpdate: false,\n"
        if (message_name in self.repeated_layout_msg_name_list and
                self._get_ui_msg_dependent_msg_name_from_another_proto(message)):
            output_str += "    url: null,\n"
        if self.current_message_is_dependent:
            output_str += "    mode: Modes.READ_MODE,\n"
            output_str += "    createMode: false,\n"
            output_str += "    formValidation: {},\n"
            output_str += "    openConfirmSavePopup: false,\n"
            output_str += "    openFormValidationPopup: false\n"
        else:
            if (not self.current_message_is_dependent and
                    self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "    openConfirmSavePopup: false,\n"
                    output_str += "    url: null\n"
        output_str += "}\n\n"
        output_str += self.handle_get_all_export_out_str(message, message_name_camel_cased)
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += self.handle_get_export_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_create_export_out_str(message, message_name_camel_cased)
        output_str += self.handle_update_export_out_str(message, message_name, message_name_camel_cased)
        output_str += self.handle_additional_async_helper_actions(message)
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
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)

                if (option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field) or
                        self.if_msg_used_in_abb_option_value(message)):
                    output_str += "            const { data } = action.payload;\n"
                    output_str += "            // deleted objects are already filtered in the array received\n"
                    output_str += f"            state.{message_name_camel_cased}Array = data;\n"
                else:
                    output_str += f"            const dict = action.payload;\n"
                    output_str += f"            const updatedArray = state.{message_name_camel_cased}Array;\n"
                    output_str += "            _.values(dict).forEach(v => {\n"
                    output_str += "                applyGetAllWebsocketUpdate(updatedArray, v);\n"
                    output_str += "            })\n"
                    output_str += f"            state.{message_name_camel_cased}Array = updatedArray;\n"
                output_str += f"            if (state.selected{message_name}Id) " + "{\n"
                output_str += f"                const storedObj = state.{message_name_camel_cased}Array.find(o => " \
                              f"o[DB_ID] === state.selected{message_name}Id);\n"
                output_str += "                if (storedObj) {\n"
                if self.if_msg_used_in_abb_option_value(message):
                    output_str += f"                    state.{message_name_camel_cased} = storedObj;\n"
                    output_str += f"                    state.modified{message_name} = storedObj;\n"
                output_str += "                } else {\n"
                output_str += "                    // active obj is deleted, reset the states to their initial values\n"
                output_str += f"                    state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                    state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += f"                    state.modified{message_name} = " \
                              f"initialState.modified{message_name};\n"
                output_str += "                }\n"
                output_str += "            }  // else not required, no active obj\n"
                output_str += "        },\n"
            else:
                output_str += f"        set{message_name}ArrayWs: (state, action) => " + "{\n"
                output_str += "            const { data, collections } = action.payload;\n"
                output_str += f"            state.{message_name_camel_cased}Array = data;\n"
                output_str += f"            const updatedObj = data.find(o => o[DB_ID] === " \
                              f"state.selected{message_name}Id);\n"
                output_str += "            if (updatedObj) {\n"
                output_str += "                let diff = compareObjects(updatedObj, " \
                              f"state.{message_name_camel_cased}, state.{message_name_camel_cased});\n"
                output_str += "                if (_.keys(updatedObj).length === 1) {\n"
                output_str += f"                    state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                    state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "                } else {\n"
                output_str += f"                    state.{message_name_camel_cased} = updatedObj;\n"
                output_str += "                }\n"
                output_str += "                let trees = generateRowTrees(cloneDeep(updatedObj), collections);\n"
                output_str += "                let modifiedTrees = generateRowTrees(cloneDeep(" \
                              f"state.modified{message_name}), collections);\n"
                output_str += "                if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                    if (state.mode === Modes.EDIT_MODE) {\n"
                output_str += "                        state.openWsPopup = true;\n"
                output_str += "                    } else {\n"
                output_str += "                        let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
                output_str += f"                        state.modified{message_name} = modifiedObj;\n"
                output_str += "                    }\n"
                output_str += "                } else {\n"
                output_str += "                    _.keys(state.userChanges).map(xpath => {\n"
                output_str += "                        if (diff.includes(xpath) && !diff.includes(DB_ID)) {\n"
                output_str += "                            state.discardedChanges[xpath] = " \
                              "state.userChanges[xpath];\n"
                output_str += "                            delete state.userChanges[xpath];\n"
                output_str += "                            state.openWsPopup = true;\n"
                output_str += "                        }\n"
                output_str += "                        return;\n"
                output_str += "                    })\n"
                output_str += "                }\n"
                output_str += "            }\n"
                output_str += "        },\n"

            output_str += f"        set{message_name}: (state, action) => " + "{\n"
            output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
            output_str += "        },\n"

            if not self.current_message_is_dependent and message_name not in self.dependent_to_abbreviated_relation_msg_name_dict.values():
                output_str += f"        set{message_name}Ws: (state, action) => " + "{\n"
                output_str += "            const { dict, mode, collections } = action.payload;\n"
                output_str += f"            let updatedObj = dict[state.selected{message_name}Id];\n"
                output_str += "            if (updatedObj) {\n"
                output_str += f"                let diff = compareObjects(updatedObj, state.{message_name_camel_cased}, " \
                              f"state.{message_name_camel_cased});\n"
                output_str += "                if (_.keys(updatedObj).length === 1) {\n"
                output_str += f"                    state.selected{message_name}Id = " \
                              f"initialState.selected{message_name}Id;\n"
                output_str += f"                    state.{message_name_camel_cased} = " \
                              f"initialState.{message_name_camel_cased};\n"
                output_str += "                } else {\n"
                output_str += f"                    state.{message_name_camel_cased} = updatedObj;\n"
                output_str += "                }\n"
                output_str += "                let trees = generateRowTrees(cloneDeep(updatedObj), collections);\n"
                output_str += f"                let modifiedTrees = generateRowTrees(cloneDeep(" \
                              f"state.modified{message_name}), collections);\n"
                output_str += "                if (trees.length !== modifiedTrees.length) {\n"
                output_str += "                    if (mode === Modes.EDIT_MODE) {\n"
                output_str += "                        state.openWsPopup = true;\n"
                output_str += "                    } else {\n"
                output_str += "                        let modifiedObj = addxpath(cloneDeep(updatedObj));\n"
                output_str += f"                        state.modified{message_name} = modifiedObj;\n"
                output_str += "                    }\n"
                output_str += "                } else {\n"
                output_str += "                    _.keys(state.userChanges).map(xpath => {\n"
                output_str += "                        if (diff.includes(xpath)) {\n"
                output_str += "                            state.discardedChanges[xpath] = state.userChanges[xpath];\n"
                output_str += "                            delete state.userChanges[xpath];\n"
                output_str += "                            state.openWsPopup = true;\n"
                output_str += "                        }\n"
                output_str += "                        return;\n"
                output_str += "                    })\n"
                output_str += "                }\n"
                output_str += "            }\n"
                output_str += "        },\n"
            elif message_name in self.dependent_to_abbreviated_relation_msg_name_dict.values():
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
            if (not self.current_message_is_dependent and
                    self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None):
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "            state.url = null;\n"
                    output_str += f"            state.{message_name_camel_cased} = " \
                                  f"initialState.{message_name_camel_cased};\n"
                    output_str += f"            state.modified{message_name} = initialState.modified{message_name};\n"
            output_str += "        },\n"
            output_str += f"        resetSelected{message_name}Id: (state) => "+"{\n"
            output_str += f"            state.selected{message_name}Id = initialState.selected{message_name}Id;\n"
            if self.current_message_is_dependent:
                output_str += f"            state.{message_name_camel_cased} = initialState.{message_name_camel_cased};\n"
                output_str += f"            state.modified{message_name} = initialState.modified{message_name};\n"
            output_str += "        },\n"
        else:
            output_str += f"        set{message_name}ArrayWs: (state, action) => "+"{\n"
            output_str += "            const { data } = action.payload;\n"
            output_str += f"            state.{message_name_camel_cased}Array = data;\n"
            output_str += "        },\n"
            output_str += f"        set{message_name}: (state, action) => " + "{\n"
            output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
            output_str += "        },\n"
            output_str += f"        setModified{message_name}: (state, action) => " + "{\n"
            output_str += f"            state.modified{message_name} = action.payload;\n"
            output_str += "        },\n"
            output_str += f"        setSelected{message_name}Id: (state, action) => " + "{\n"
            output_str += f"            state.selected{message_name}Id = action.payload;\n"
            output_str += "        },\n"
            # if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
            output_str += (f"        reset{message_name}: (state, action) => "
                           "{\n")
            output_str += (f"            state.{message_name_camel_cased}Array = "
                           f"initialState.{message_name_camel_cased}Array;\n")
            output_str += (f"            state.{message_name_camel_cased} = "
                           f"initialState.{message_name_camel_cased};\n")
            output_str += (f"            state.modified{message_name} = "
                           f"initialState.modified{message_name};\n")
            output_str += (f"            state.selected{message_name}Id = "
                           f"initialState.selected{message_name}Id;\n")
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message):
                output_str += "            state.url = null;\n"
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
        output_str += "        setActiveChanges: (state, action) => {\n"
        output_str += "            state.activeChanges = action.payload;\n"
        output_str += "        },\n"
        output_str += "        setOpenWsPopup: (state, action) => {\n"
        output_str += "            state.openWsPopup = action.payload;\n"
        output_str += "        },\n"
        output_str += "        setForceUpdate: (state, action) => {\n"
        output_str += "            state.forceUpdate = action.payload;\n"
        output_str += "        },\n"
        if (message_name in self.repeated_layout_msg_name_list and
                self._get_ui_msg_dependent_msg_name_from_another_proto(message)):
            output_str += "        setUrl: (state, action) => {\n"
            output_str += "            state.url = action.payload;\n"
            output_str += "        }\n"
        if self.current_message_is_dependent:
            output_str += "        setMode: (state, action) => {\n"
            output_str += "            state.mode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setCreateMode: (state, action) => {\n"
            output_str += "            state.createMode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setFormValidation: (state, action) => {\n"
            output_str += "            state.formValidation = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setOpenConfirmSavePopup: (state, action) => {\n"
            output_str += "            state.openConfirmSavePopup = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setOpenFormValidationPopup: (state, action) => {\n"
            output_str += "            state.openFormValidationPopup = action.payload;\n"
            output_str += "        },\n"
        else:
            if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                    message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                if option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                    output_str += "        setOpenConfirmSavePopup: (state, action) => {\n"
                    output_str += "            state.openConfirmSavePopup = action.payload;\n"
                    output_str += "        },\n"
                    output_str += "        setUrl: (state, action) => {\n"
                    output_str += "            state.url = action.payload;\n"
                    output_str += "        }\n"
        output_str += "    },\n"
        output_str += "    extraReducers: {\n"
        output_str += self.handle_get_all_out_str(message, message_name_camel_cased)
        if message_name not in self.repeated_layout_msg_name_list:
            output_str += self.handle_get_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_create_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_update_out_str(message, message_name, message_name_camel_cased)
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
            output_str += "    setUserChanges, setDiscardedChanges, setActiveChanges, setOpenWsPopup, setForceUpdate"
            if self.current_message_is_dependent:
                output_str += (", setMode, setCreateMode, setFormValidation, setOpenConfirmSavePopup, "
                               "setOpenFormValidationPopup")
            else:
                if self._get_ui_msg_dependent_msg_name_from_another_proto(message) is not None:
                    option_dict = BaseJSLayoutPlugin.get_complex_option_value_from_proto(
                        message, BaseJSLayoutPlugin.flux_msg_widget_ui_data_element)
                    if option_dict.get(JsSliceFileGenPlugin.widget_ui_option_depends_on_other_model_for_id_field):
                        output_str += ", setOpenConfirmSavePopup, setUrl"
            output_str += "\n"
            output_str += "} = " + f"{message_name_camel_cased}Slice.actions;\n"
        else:
            output_str += "export const {\n"
            output_str += (f"    set{message_name}ArrayWs, set{message_name}, setModified{message_name}, "
                           f"setSelected{message_name}Id,\n")
            output_str += "    resetError, setUserChanges, setDiscardedChanges, setActiveChanges, setOpenWsPopup\n"
            if (message_name in self.repeated_layout_msg_name_list and
                    self._get_ui_msg_dependent_msg_name_from_another_proto(message)):
                output_str += f", setUrl"
            output_str += f", reset{message_name}"+"}" + f" = {message_name_camel_cased}Slice.actions;\n"

        return output_str

    def if_msg_used_in_abb_option_value(self, message: protogen.Message):
        for abb_message in self.abbreviated_message_list:
            msg_used_in_abb_option_list: List[str] = self._get_msg_names_list_used_in_abb_option_val(abb_message)
            for msg_name in msg_used_in_abb_option_list:
                if (msg_name == message.proto.name and
                        msg_name not in self.dependent_to_abbreviated_relation_msg_name_dict.keys()):
                    return True
        return False

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_dict = {}

        # sorting created message lists
        self.root_msg_list.sort(key=lambda message_: message_.proto.name)
        self.independent_message_list.sort(key=lambda message_: message_.proto.name)
        self.dependent_message_list.sort(key=lambda message_: message_.proto.name)

        for message in self.root_msg_list:
            if message in self.independent_message_list:
                self.current_message_is_dependent = False
            elif message in self.dependent_message_list:
                self.current_message_is_dependent = True
            elif message.proto.name in self.dependent_to_abbreviated_relation_msg_name_dict.values():
                self.current_message_is_dependent = False
            else:
                independent_msg_names = [msg.proto.name for msg in self.independent_message_list]
                dependent_msg_names = [msg.proto.name for msg in self.dependent_message_list]
                abb_msg_names_to_dep_msg_names_dict = \
                    {abb_msg: dep_msg for dep_msg, abb_msg in
                     self.dependent_to_abbreviated_relation_msg_name_dict.items()}
                err_str_ = (f"message {message.proto.name} not found neither in dependent_list or in independent_list, "
                            f"nor in abbreviated message dict, independent_msg_list: {independent_msg_names}, "
                            f"dependent_msg_list: {dependent_msg_names} and Abbreviated_to_dependent_msg_dict: "
                            f"{abb_msg_names_to_dep_msg_names_dict}")
                logging.exception(err_str_)
                raise Exception(err_str_)
            message_name_camel_cased = capitalized_to_camel_case(message.proto.name)
            output_dict_key = f"{message_name_camel_cased}Slice.js"
            output_str = self.handle_slice_content(message)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsSliceFileGenPlugin)
