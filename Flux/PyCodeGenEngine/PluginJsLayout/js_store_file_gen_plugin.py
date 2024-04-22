#!/usr/bin/env python
import os
from typing import List, Callable
import time
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.utility_functions import capitalized_to_camel_case


class JsSliceFileGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to generate jsx file for ORM root messages
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_import_output(self, ) -> str:
        output_str = "import { configureStore, getDefaultMiddleware } from '@reduxjs/toolkit';\n"
        for message in self.root_msg_list:
            message_name = message.proto.name
            message_name_camel_cased = capitalized_to_camel_case(message_name)
            output_str += f"import {message_name_camel_cased}Slice from './features/{message_name_camel_cased}Slice';\n"
        output_str += "import schemaSlice from './features/schemaSlice';\n\n"

        return output_str

    def handle_body(self) -> str:
        output_str = "export const store = configureStore({\n"
        output_str += "    reducer: {\n"
        output_str += "        schema: schemaSlice,\n"
        for message in self.root_msg_list:
            message_name = message.proto.name
            message_name_camel_cased = capitalized_to_camel_case(message_name)

            # If message is last in list
            if message == self.root_msg_list[-1]:
                output_str += f"        {message_name_camel_cased}: {message_name_camel_cased}Slice\n"
            else:
                output_str += f"        {message_name_camel_cased}: {message_name_camel_cased}Slice,\n"

        output_str += "    },\n"
        output_str += "    middleware: (getDefaultMiddleware) => getDefaultMiddleware({\n"
        output_str += "        serializableCheck: false,\n"
        output_str += "        immutableCheck: false\n"
        output_str += "    })\n"
        output_str += "});\n"

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
