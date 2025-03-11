#!/usr/bin/env python
import os
from typing import List, Callable, Final
import time
from pathlib import PurePath
import logging

from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main
from FluxPythonUtils.scripts.general_utility_functions import capitalized_to_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class SelectorJsGenPlugin(BaseJSLayoutPlugin):
    indentation_space: Final[str] = "    "

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_const_selector_per_model(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.root_msg_list:
            message_name_camel_cased = capitalized_to_camel_case(message.proto.name)
            output_str += f"const {message_name_camel_cased}Selector = (state) => state.{message_name_camel_cased};\n"
        output_str += "\n"
        return output_str

    def handle_memoized_selector_per_model(self, file: protogen.File):
        output_str = ""
        for message in self.root_msg_list:
            message_name = message.proto.name
            message_name_camel_cased = capitalized_to_camel_case(message_name)
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            output_str += f"// Memoized selector for {message_name_camel_cased}\n"
            output_str += f"export const select{message_name} = createSelector(\n"
            output_str += SelectorJsGenPlugin.indentation_space + f"[{message_name_camel_cased}Selector],\n"
            output_str += (SelectorJsGenPlugin.indentation_space + f"({message_name_camel_cased}) => getDataSourceSelector("
                           f"'{message_name_snake_cased}', {message_name_camel_cased})\n")
            output_str += f");\n\n"
            # else not required: avoid duplicates
        return output_str

    def output_file_generate_handler(self, file: protogen.File | List[protogen.File]):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)

        output_file_name = "selectors.js"
        py_code_gen_engine_path = None
        if (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and len(template_file_name) and \
                (py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None and \
                len(py_code_gen_engine_path):
            template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.output_file_name_to_template_file_path_dict[output_file_name] = str(template_file_path)

        # sorting created message lists
        self.root_msg_list.sort(key=lambda message_: message_.proto.name)

        return {
            output_file_name: {
                "const_selector_per_model": self.handle_const_selector_per_model(file),
                "memoized_selector_per_model": self.handle_memoized_selector_per_model(file)
            }
        }


if __name__ == "__main__":
    main(SelectorJsGenPlugin)
