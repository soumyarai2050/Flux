#!/usr/bin/env python
import os
from typing import List, Callable, Final
import time
import logging

from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case
# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.general_utility_functions import capitalized_to_camel_case


class JsSliceFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    """
    indentation_space: Final[str] = "    "

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_import_output(self, ) -> str:
        output_str = "import { configureStore, getDefaultMiddleware, combineReducers } from '@reduxjs/toolkit';\n"
        for message in self.root_msg_list:
            message_name = message.proto.name
            message_name_camel_cased = capitalized_to_camel_case(message_name)
            output_str += f"import {message_name_camel_cased}Slice from './features/{message_name_camel_cased}Slice';\n"
        output_str += "import schemaSlice from './features/schemaSlice';\n\n"

        return output_str

    def handle_body(self) -> str:
        output_str = "// Store static reducers in a separate object for dynamic injection\n"
        output_str += "const staticReducers = {\n"
        output_str += JsSliceFileGenPlugin.indentation_space * 1 + "schema: schemaSlice,\n"
        for message in self.root_msg_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            message_name_camel_cased = capitalized_to_camel_case(message_name)

            # If message is last in list
            if message == self.root_msg_list[-1]:
                output_str += JsSliceFileGenPlugin.indentation_space*1 + f"{message_name_snake_cased}: {message_name_camel_cased}Slice\n"
            else:
                output_str += JsSliceFileGenPlugin.indentation_space*1 + f"{message_name_snake_cased}: {message_name_camel_cased}Slice,\n"
        output_str += "};\n\n"
        output_str += "export const store = configureStore({\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "reducer: staticReducers,\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "middleware: (getDefaultMiddleware) => getDefaultMiddleware({\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "serializableCheck: false,\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "immutableCheck: false\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "})\n"
        output_str += "});\n\n"

        # Add dynamic reducer injection functionality
        output_str += "// Dynamic reducer injection functionality\n"
        output_str += "store.dynamicReducers = {};\n\n"
        output_str += "store.injectReducer = (key, reducer) => {\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "if (!store.dynamicReducers[key]) {\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "console.log(`🔧 Injecting dynamic reducer: ${key}`);\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "store.dynamicReducers[key] = reducer;\n\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "// Replace the root reducer with the new combined reducer\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "const combinedReducer = combineReducers({\n"
        output_str += JsSliceFileGenPlugin.indentation_space*3 + "...staticReducers,\n"
        output_str += JsSliceFileGenPlugin.indentation_space*3 + "...store.dynamicReducers\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "});\n\n"
        output_str += JsSliceFileGenPlugin.indentation_space*2 + "store.replaceReducer(combinedReducer);\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "}\n"
        output_str += "};\n\n"

        # Make store globally available for dynamic slice creation
        output_str += "// Make store globally available for dynamic slice creation\n"
        output_str += "if (typeof window !== 'undefined') {\n"
        output_str += JsSliceFileGenPlugin.indentation_space + "window.store = store;\n"
        output_str += "}\n"

        return output_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        # sorting created message lists
        self.root_msg_list.sort(key=lambda message_: message_.proto.name)

        output_str = self.handle_import_output()
        output_str += self.handle_body()

        output_file_name = "store.js"
        return {output_file_name: output_str}


if __name__ == "__main__":
    main(JsSliceFileGenPlugin)
