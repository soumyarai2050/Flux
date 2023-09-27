import os
import time
from abc import ABC

import protogen

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from FluxPythonUtils.scripts.utility_functions import convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiLauncherFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def _handle_callback_override_set_instance_import(self) -> str:
        callback_override_set_instance_file_path = \
            self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.callback_override_set_instance_file_name)
        output_str = "# below import is to set derived callback's instance if implemented in the script\n"
        callback_override_set_instance_file_path = ".".join(callback_override_set_instance_file_path.split("."))
        output_str += f"from {callback_override_set_instance_file_path} import port, config_yaml_dict\n"
        callback_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", f"{self.routes_callback_class_name}")
        routes_callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {callback_file_path} import {routes_callback_class_name_camel_cased}\n\n\n"

        return output_str

    def handle_launch_file_gen(self, file: protogen.File) -> str:
        if self.is_option_enabled(file, FastapiLauncherFileHandler.flux_file_crud_host):
            host = self.get_simple_option_value_from_proto(file,
                                                           FastapiLauncherFileHandler.flux_file_crud_host)
        else:
            host = '"127.0.0.1"'

        if self.is_option_enabled(file, FastapiLauncherFileHandler.flux_file_crud_port_offset):
            port_offset = \
                self.get_simple_option_value_from_proto(file,
                                                        FastapiLauncherFileHandler.flux_file_crud_port_offset)
            port = 8000 + int(port_offset)
        else:
            port = 8000

        output_str = "import os\n"
        output_str += "import uvicorn\n"
        output_str += "import logging\n"
        output_str += "from pathlib import PurePath\n"
        output_str += self._handle_callback_override_set_instance_import()
        routes_callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += (f"from FluxPythonUtils.scripts.utility_functions import configure_logger, add_logging_levels, "
                       f"parse_to_int\n\n")
        output_str += f'custom_log_lvls = config_yaml_dict.get("custom_logger_lvls") \n'
        output_str += f'add_logging_levels([] if custom_log_lvls is None else custom_log_lvls)\n'
        output_str += f'log_lvl = config_yaml_dict.get("log_level")\n'
        output_str += f'# if below env vars are not as expected internally in configure logger, it will handled\n'
        output_str += f'configure_logger(log_lvl, log_file_dir_path=os.getenv("LOG_FILE_DIR_PATH"), \n'
        output_str += f'                 log_file_name=os.getenv("LOG_FILE_NAME"))\n'
        output_str += "\n\n"
        output_str += f'def {self.launch_file_name}():\n'
        output_str += (f'    os.environ[f"{self.proto_file_package}_' + '{port}"] = "0"  # indicator flag to tell '
                      'callback override that service is not up yet\n')
        output_str += f'    callback_instance = {routes_callback_class_name_camel_cased}().get_instance()\n'
        output_str += f'    callback_instance.app_launch_pre()\n'
        output_str += f'    if reload_env := os.getenv("RELOAD"):\n'
        output_str += f'        reload_status: bool = True if reload_env.lower() == "true" else False\n'
        output_str += f'    else:\n'
        output_str += f'        reload_status: bool = False\n'
        output_str += f'    # Log Levels\n'
        output_str += f'    # NOTSET: 0\n'
        output_str += f'    # DEBUG: 10\n'
        output_str += f'    # INFO: 20\n'
        output_str += f'    # WARNING: 30\n'
        output_str += f'    # ERROR: 40\n'
        output_str += f'    # CRITICAL: 50\n'
        output_str += \
            f'    host = {host} if ((env_host := os.getenv("HOST")) is None or len(env_host) == 0) else env_host\n'
        output_str += f'    if (fastapi_file_name := os.getenv("FASTAPI_FILE_NAME")) is None or ' \
                      f'len(fastapi_file_name) == 0:\n'
        output_str += '        err_str = f"Env Var FASTAPI_FILE_NAME received as {fastapi_file_name}"\n'
        output_str += f'        logging.exception(err_str)\n'
        output_str += f'        raise Exception(err_str)\n'
        output_str += f'    # else not required: if fastapi file name received successfully then running server\n'
        output_str += f'    uvicorn.run(reload=reload_status, \n'
        output_str += f'                host=host, \n'
        output_str += f'                port=parse_to_int(port), \n'
        output_str += '                app=f"FastApi.{fastapi_file_name}'+f':{self.fastapi_app_name}", \n'
        output_str += f'                log_level=20)\n'
        output_str += f'    callback_instance.app_launch_post()\n'
        output_str += (f'    os.environ[f"{self.proto_file_package}_' + '{port}"] = "0"  # indicator flag to tell '
                       'callback override that service is not up now\n')
        return output_str
