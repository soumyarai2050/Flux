#!/usr/bin/env python
import os
from typing import Dict
import time
from pathlib import PurePath
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main


class JsConstantsGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to convert proto schema to required jsx layout script
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.output_file_name_to_template_file_path_dict: Dict[str, str] = {}
        self.proto_package_name: str | None = None
        self.host = "127.0.0.1"
        self.port_offset = 0

    def get_option_values(self, file: protogen.File):
        self.proto_package_name = str(file.proto.package)
        if self.is_option_enabled(file, JsConstantsGenPlugin.flux_file_crud_host):
            self.host = self.get_simple_option_value_from_proto(file,
                                                                JsConstantsGenPlugin.flux_file_crud_host)
        if self.is_option_enabled(file, JsConstantsGenPlugin.flux_file_crud_port_offset):
            self.port_offset = \
                int(self.get_simple_option_value_from_proto(file,
                                                            JsConstantsGenPlugin.flux_file_crud_port_offset))

    def handle_api_root_url(self, file: protogen.File) -> str:
        port = 8000 + self.port_offset
        cache_offset = 10
        output_str = f"export const API_ROOT_URL = 'http://{self.host}:{port}/{self.proto_package_name}';\n"
        output_str += f"export const API_ROOT_CACHE_URL = 'http://{self.host}:{port + cache_offset}/" \
                      f"{self.proto_package_name}';"
        return output_str

    def handle_api_public_url(self, file: protogen.File) -> str:
        port = 3000 + self.port_offset
        output_str = f"export const API_PUBLIC_URL = 'http://{self.host}:{port}';"
        return output_str

    def handle_cookie_name(self, file: protogen.File) -> str:
        output_str = f"export const COOKIE_NAME = '{self.proto_package_name}';"
        return output_str

    def output_file_generate_handler(self, file: protogen.File):
        # Loading root messages to data member
        self.load_root_message_to_data_member(file)
        self.get_option_values(file)

        output_file_name = "constants.js"
        py_code_gen_engine_path = None
        if ((template_file_name := os.getenv("TEMPLATE_FILE_NAME")) is not None and len(template_file_name)) and \
                ((py_code_gen_engine_path := os.getenv("PY_CODE_GEN_ENGINE_PATH")) is not None and \
                 len(py_code_gen_engine_path)):
            template_file_path = PurePath(py_code_gen_engine_path) / PurePath(__file__).parent / template_file_name
        else:
            err_str = f"Env var 'TEMPLATE_FILE_NAME' and 'PY_CODE_GEN_ENGINE_PATH'" \
                      f"received as {template_file_name} and {py_code_gen_engine_path}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.output_file_name_to_template_file_path_dict[output_file_name] = str(template_file_path)
        return {
            output_file_name: {
                "api_root_url": self.handle_api_root_url(file),
                "api_public_url": self.handle_api_public_url(file),
                "cookie_name": self.handle_cookie_name(file)
            }
        }


if __name__ == "__main__":
    main(JsConstantsGenPlugin)
