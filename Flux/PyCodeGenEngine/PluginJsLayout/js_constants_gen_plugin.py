#!/usr/bin/env python
import os
from typing import Dict, ClassVar, Final
import time
from pathlib import PurePath
import logging

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int, YAMLConfigurationManager

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginJsLayout.base_js_layout_plugin import BaseJSLayoutPlugin, main

ui_proxy_project_dir = PurePath(__file__).parent.parent.parent / "CodeGenProjects" / "ui_proxy"
ui_proxy_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(
    str(ui_proxy_project_dir / "data" / "config.yaml"))


class JsConstantsGenPlugin(BaseJSLayoutPlugin):
    """
    Plugin script to convert proto schema to required jsx layout script
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.output_file_name_to_template_file_path_dict: Dict[str, str] = {}
        self.proto_package_name: str | None = None
        self.host: str | None = None

    def get_option_values(self, file: protogen.File):
        self.proto_package_name = str(file.proto.package)
        host = os.environ.get("HOST")
        if host is None or len(host) == 0:
            err_str = (f"Env var 'HOST' found as '{host}', "
                       f"likely bug in setting env var from launch of this plugin")
            logging.error(err_str)
            raise Exception(err_str)
        self.host = host

    def handle_api_root_url(self, file: protogen.File) -> str:
        beanie_port = os.environ.get("BEANIE_PORT")
        proxy_server = os.environ.get("PROXY_SERVER")
        if beanie_port is None or len(beanie_port) == 0:
            err_str = (f"Env var 'BEANIE_PORT' found as '{beanie_port}', "
                       f"likely bug in setting env var from launch of this plugin")
            logging.error(err_str)
            raise Exception(err_str)
        output_str = f"export const PROXY_SERVER = {proxy_server.lower()};\n"
        ui_proxy_host: str = ui_proxy_config_yaml_dict.get("server_host")
        ui_proxy_port: str = ui_proxy_config_yaml_dict.get("server_port")
        if (ui_proxy_host is None or len(ui_proxy_host) == 0) or (ui_proxy_port is None or len(ui_proxy_port) == 0):
            err_str = "Couldn't find host or port for ui_proxy project from ui_proxy/data/config.yaml file"
            logging.error(err_str)
            raise Exception(err_str)
        output_str += f"export const PROXY_SERVER_URL = 'http://{ui_proxy_host}:{ui_proxy_port}/ui_proxy';\n"
        output_str += (f"export const API_ROOT_URL = PROXY_SERVER ? PROXY_SERVER_URL : "
                       f"'http://{self.host}:{beanie_port}/{self.proto_package_name}';\n")

        cache_port = os.environ.get("CACHE_PORT")
        if cache_port is None or len(cache_port) == 0:
            err_str = (f"Env var 'CACHE_PORT' found as '{cache_port}', "
                       f"likely bug in setting env var from launch of this plugin")
            logging.error(err_str)
            raise Exception(err_str)
        output_str += f"export const API_ROOT_CACHE_URL = 'http://{self.host}:{cache_port}/" \
                      f"{self.proto_package_name}';"
        return output_str

    def handle_api_public_url(self, file: protogen.File) -> str:
        ui_port = os.environ.get("UI_PORT")
        if ui_port is None or len(ui_port) == 0:
            err_str = (f"Env var 'UI_PORT' found as '{ui_port}', "
                       f"likely bug in setting env var from launch of this plugin")
            logging.error(err_str)
            raise Exception(err_str)
        output_str = f"export const API_PUBLIC_URL = 'http://{self.host}:{ui_port}';"
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
