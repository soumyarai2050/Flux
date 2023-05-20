#!/usr/bin/env python
import os
from typing import List, Callable
import time
from pathlib import PurePath
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main


class PackageJsonGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to convert proto schema to required jsx layout script
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_list: List[str] = [
            "tmp_project_name",
            "port_handling"
        ]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_temp_project_name,
            self.handle_port
        ]
        template_file_name = None
        py_code_gen_engine_path = None
        if (output_file_name := os.getenv("OUTPUT_FILE_NAME")) is not None and \
                (template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and \
                (py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None:
            self.output_file_name = output_file_name
            self.template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME', 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {output_file_name}, {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.proto_package_name: str | None = None
        self.port_offset = 0

    def get_option_values(self, file: protogen.File):
        self.proto_package_name = str(file.proto.package)
        if self.is_option_enabled(file, PackageJsonGenPlugin.flux_file_crud_port_offset):
            self.port_offset = \
                int(self.get_non_repeated_valued_custom_option_value(file,
                                                                     PackageJsonGenPlugin.flux_file_crud_port_offset))

    def handle_temp_project_name(self, file: protogen.File) -> str:
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
        self.get_option_values(file)
        output_str = f'"name": "{self.proto_package_name}",'
        return output_str

    def handle_port(self, file: protogen.File) -> str:
        port = 3000 + self.port_offset
        output_str = f'"start": "cross-env PORT={port} react-scripts start",'
        return output_str


if __name__ == "__main__":
    main(PackageJsonGenPlugin)
