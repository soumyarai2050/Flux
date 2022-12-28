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
        self.dependent_message_relation_dict: Dict[str, str] = {}
        self.dependent_message_list: List[protogen.Message] = []
        self.independent_message_list: List[protogen.Message] = []
        self.current_message_is_dependent: bool | None = None  # True if dependent else false
        self.output_file_name_suffix: str = ""
        if (ui_layout_msg_name := os.getenv("UILAYOUT_MESSAGE_NAME")) is not None:
            self.__ui_layout_msg_name = ui_layout_msg_name
        else:
            err_str = f"Env var 'UILAYOUT_MESSAGE_NAME' received as None"
            logging.exception(err_str)
            raise Exception(err_str)

    def load_root_message_to_data_member(self, file: protogen.File):
        super().load_root_message_to_data_member(file)

        for message in self.root_msg_list:
            for field in message.fields:
                if field.message is not None and \
                        JsSliceFileGenPlugin.flux_msg_layout in str(field.message.proto.options):
                    self.dependent_message_list.append(message)
                    break
                # else not required: Avoid if any field of message type doesn't contain layout options

                # Checking abbreviated dependent relation
                if JsSliceFileGenPlugin.flux_fld_abbreviated in str(field.proto.options):
                    abbreviated_option_value = \
                        self.get_non_repeated_valued_custom_option_value(field.proto.options,
                                                                         JsSliceFileGenPlugin.flux_fld_abbreviated)
                    abbreviated_message_name = abbreviated_option_value.split(".")[0][1:]
                    self.dependent_message_relation_dict[abbreviated_message_name] = message.proto.name
                # else not required: Avoid if field doesn't contain abbreviated option
            else:
                self.independent_message_list.append(message)

    def handle_import_output(self, message: protogen.Message) -> str:
        if not self.current_message_is_dependent:
            output_str = "import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';\n"
            output_str += "import axios from 'axios';\n"
            output_str += "import { API_ROOT_URL, DB_ID } from '../constants';\n"
            if message.proto.name != self.__ui_layout_msg_name:
                output_str += "import { getObjectWithLeastId } from '../utils';\n"
            output_str += "\n"
        else:
            dependent_message_name: str | None = None
            message_name = message.proto.name
            if message_name in self.dependent_message_relation_dict:
                dependent_message_name = self.dependent_message_relation_dict[message_name]
            output_str = "import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';\n"
            output_str += "import axios from 'axios';\n"
            output_str += "import _, { cloneDeep } from 'lodash';\n"
            output_str += "import { API_ROOT_URL, DB_ID, Modes, NEW_ITEM_ID } from '../constants';\n"
            output_str += "import { addxpath } from '../utils';\n"
            if dependent_message_name is not None:
                output_str += "import { setModified"+f"{dependent_message_name}, "+"update"+f"{dependent_message_name}"+" } from './"+\
                              f"{self.capitalized_to_camel_case(dependent_message_name)}Slice';\n"
            output_str += "\n"

        return output_str

    def handle_get_all_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f"export const getAll{message_name} = createAsyncThunk('{message_name_camel_cased}/getAll', () => " + "{\n"
        output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-all-{message_name_snake_cased}`)\n"
        output_str += "        .then(res => res.data);\n"
        output_str += "})\n\n"
        return output_str

    def handle_get_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f"export const get{message_name} = createAsyncThunk('{message_name_camel_cased}/get', (id) => " + "{\n"
        output_str += "    return axios.get(`${API_ROOT_URL}/" + f"get-{message_name_snake_cased}"+"/${id}`)\n"
        output_str += "        .then(res => res.data);\n"
        output_str += "})\n\n"
        return output_str

    def handle_create_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        if not self.current_message_is_dependent:
            output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/create', (payload) => " + "{\n"
            output_str += "    return axios.post(`${API_ROOT_URL}/create-" + f"{message_name_snake_cased}" + "`, payload)\n"
            output_str += "        .then(res => res.data);\n"
            output_str += "})\n\n"
            return output_str
        else:
            if message_name in self.dependent_message_relation_dict:
                dependent_message_name = self.dependent_message_relation_dict[message_name]
                dependent_message_name_camel_cased = self.capitalized_to_camel_case(dependent_message_name)
                output_str = f"export const create{message_name} = createAsyncThunk('{message_name_camel_cased}/create', (payload, "+"{ dispatch, getState }) => " + "{\n"
                output_str += "    const { data, abbreviated, loadedKeyName } = payload;\n"
                output_str += "    return axios.post(`${API_ROOT_URL}/create-" + f"{message_name_snake_cased}" + "`, data)\n"
                output_str += "        .then(res => {\n"
                output_str += "            let state = getState();\n"
                output_str += f"            let updatedData = cloneDeep(state.{dependent_message_name_camel_cased}" \
                              f".{dependent_message_name_camel_cased});\n"
                loaded_strat_keys_style_cased = self.case_style_convert_method("loaded_strat_keys")
                output_str += f"            let newStrat = res.data;\n"
                output_str += "            let newStratKey = abbreviated.split('-').map(xpath => _.get(newStrat, " \
                              "xpath.substring(xpath.indexOf('.') + 1)));\n"
                output_str += "            newStratKey = newStratKey.join('-');\n"
                output_str += "            _.get(updatedData, loadedKeyName).push(newStratKey);\n"
                output_str += f"            dispatch(update{dependent_message_name}("+"updatedData));\n"
                output_str += "            return res.data;\n"
                output_str += "        });\n"
                output_str += "})\n\n"
                return output_str

    def handle_update_export_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        message_name_snake_cased = self.convert_camel_case_to_specific_case(message_name)
        output_str = f"export const update{message_name} = createAsyncThunk('{message_name_camel_cased}/update', (payload) => "+"{\n"
        output_str += "    return axios.put(`${API_ROOT_URL}/put-"+f"{message_name_snake_cased}"+"`, payload)\n"
        output_str += "        .then(res => res.data);\n"
        output_str += "})\n\n"
        return output_str

    def handle_get_all_out_str(self, message_name: str, message_name_camel_cased: str) -> str:
        output_str = f"        [getAll{message_name}.pending]: (state) => "+"{\n"
        output_str += f"            state.loading = true;\n"
        output_str += f"            state.error = null;\n"
        if not self.current_message_is_dependent:
            output_str += f"            state.selected{message_name}Id = null;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.fulfilled]: (state, action) => " + "{\n"
        output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
        if not self.current_message_is_dependent:
            if message_name != self.__ui_layout_msg_name:
                output_str += "            if (action.payload.length === 0) {\n"
                output_str += f"                state.{message_name_camel_cased} = initialState.{message_name_camel_cased};\n"
                output_str += f"                state.modified{message_name} = initialState.modified{message_name};\n"
                output_str += f"                state.selected{message_name}Id = initialState.selected{message_name}Id;\n"
                output_str += "            } else if (action.payload.length > 0) {\n"
                output_str += f"                let object = getObjectWithLeastId(action.payload);\n"
                output_str += f"                state.selected{message_name}Id = object[DB_ID];\n"
                output_str += "            }\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [getAll{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += f"            state.error = action.error.code + ': ' + action.error.message;\n"
        output_str += f"            state.loading = false;\n"
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
        output_str += f"            state.error = action.error.code + ': ' + action.error.message;\n"
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
        if message_name in self.dependent_message_relation_dict.values():
            output_str += f"            state.setSelected{message_name}Id = action.payload[DB_ID];\n"
        elif not self.current_message_is_dependent and message_name != self.__ui_layout_msg_name:
            output_str += f"            state.selected{message_name}Id = action.payload[DB_ID];\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        },\n"
        output_str += f"        [create{message_name}.rejected]: (state, action) => " + "{\n"
        output_str += f"            state.error = action.error.code + ': ' + action.error.message;\n"
        output_str += "            state.loading = false;\n"
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
        output_str += f"            state.error = action.error.code + ': ' + action.error.message;\n"
        output_str += f"            state.loading = false;\n"
        output_str += "        }\n"
        return output_str

    def handle_slice_content(self, message: protogen.Message) -> str:
        output_str = self.handle_import_output(message)
        message_name = message.proto.name
        message_name_camel_cased = self.capitalized_to_camel_case(message_name)
        output_str += f"const initialState = " + "{\n"
        output_str += f"    {message_name_camel_cased}Array: [],\n"
        output_str += f"    {message_name_camel_cased}: " + "{},\n"
        output_str += f"    modified{message_name}: " + "{},\n"
        output_str += f"    selected{message_name}Id: null,\n"
        output_str += "    loading: true,\n"
        if self.current_message_is_dependent:
            output_str += "    error: null,\n"
            output_str += "    mode: Modes.READ_MODE,\n"
            output_str += "    createMode: false,\n"
            output_str += "    userChanges: {},\n"
            output_str += "    discardedChanges: {}\n"
        else:
            output_str += "    error: null\n"
        output_str += "}\n\n"
        output_str += self.handle_get_all_export_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_get_export_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_create_export_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_update_export_out_str(message_name, message_name_camel_cased)
        output_str += f"const {message_name_camel_cased}Slice = createSlice(" + "{\n"
        output_str += f"    name: '{message_name_camel_cased}',\n"
        output_str += "    initialState: initialState,\n"
        output_str += "    reducers: {\n"
        output_str += f"        set{message_name}Array: (state, action) => "+"{\n"
        output_str += f"            state.{message_name_camel_cased}Array = action.payload;\n"
        output_str += "        },\n"
        output_str += f"        set{message_name}: (state, action) => " + "{\n"
        output_str += f"            state.{message_name_camel_cased} = action.payload;\n"
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
        output_str += "        resetError: (state) => {\n"
        if not self.current_message_is_dependent:
            output_str += "            state.error = initialState.error;\n"
        else:
            output_str += "            state.error = null;\n"
            output_str += "        },\n"
            output_str += "        setMode: (state, action) => {\n"
            output_str += "            state.mode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setCreateMode: (state, action) => {\n"
            output_str += "            state.createMode = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setUserChanges: (state, action) => {\n"
            output_str += "            state.userChanges = action.payload;\n"
            output_str += "        },\n"
            output_str += "        setDiscardedChanges: (state, action) => {\n"
            output_str += "            state.discardedChanges = action.payload;\n"
        output_str += "        }\n"
        output_str += "    },\n"
        output_str += "    extraReducers: {\n"
        output_str += self.handle_get_all_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_get_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_create_out_str(message_name, message_name_camel_cased)
        output_str += self.handle_update_out_str(message_name, message_name_camel_cased)
        output_str += "    }\n"
        output_str += "})\n\n"
        output_str += f"export default {message_name_camel_cased}Slice.reducer;\n\n"
        output_str += "export const { " + f"set{message_name}Array, set{message_name}, reset{message_name}, " \
                                          f"setModified{message_name}, setSelected{message_name}Id, " \
                                          f"resetSelected{message_name}Id, resetError"
        if message.proto.name == self.__ui_layout_msg_name:
            output_str += " }" + f" = {message_name_camel_cased}Slice.actions;\n"
        else:
            if not self.current_message_is_dependent:
                output_str += " }" + f" = {message_name_camel_cased}Slice.actions;\n"
            else:
                output_str += f", setMode, setCreateMode" + \
                              ", setUserChanges, setDiscardedChanges }" + \
                              f" = {message_name_camel_cased}Slice.actions;\n"
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
            message_name_camel_cased = self.capitalized_to_camel_case(message.proto.name)
            output_dict_key = f"{message_name_camel_cased}Slice.js"
            output_str = self.handle_slice_content(message)

            output_dict[output_dict_key] = output_str

        return output_dict


if __name__ == "__main__":
    main(JsSliceFileGenPlugin)
