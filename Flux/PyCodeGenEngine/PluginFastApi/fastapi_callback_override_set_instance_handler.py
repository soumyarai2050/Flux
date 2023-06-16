import os
import time
import logging
from abc import ABC
from pathlib import PurePath

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from FluxPythonUtils.scripts.utility_functions import convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiCallbackOverrideSetInstanceHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_callback_override_set_instance_file_gen(self) -> str:
        output_str = "# File to contain injection of override callback instance using set instance\n\n"
        if not ((total_root_msg := len(self.root_message_list)) >= 4):
            err_str = f"Model file might have less then 4 root models, complete generation " \
                      f"requires at least 4 models, received {total_root_msg}, generating limited callback " \
                      f"override examples with available messages"
            logging.exception(err_str)
        output_str += "import logging\n"

        if (project_path := os.getenv("PROJECT_DIR")) is not None:
            routes_callback_override_file_path = \
                PurePath(project_path) / "app" / f"{self.routes_callback_class_name_override}.py"
            callback_override_path = \
                self.import_path_from_os_path("PROJECT_DIR", f"app.{self.routes_callback_class_name_override}")
            routes_callback_class_name_override_camel_cased = \
                convert_to_capitalized_camel_case(self.routes_callback_class_name_override)
        else:
            err_str = "Env Var PROJECT_DIR received as None"
            logging.exception(err_str)
            raise Exception(err_str)

        output_str += f"from {callback_override_path} import {routes_callback_class_name_override_camel_cased}\n\n\n"

        callback_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", f"{self.routes_callback_class_name}")
        routes_callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {callback_file_path} import {routes_callback_class_name_camel_cased}\n\n\n"

        output_str += \
            f"if {routes_callback_class_name_camel_cased}." \
            f"{self.routes_callback_class_name}_instance is None:\n"
        output_str += f"    callback_override = {routes_callback_class_name_override_camel_cased}()\n"
        output_str += f"    {routes_callback_class_name_camel_cased}.set_instance(callback_override)\n"
        output_str += "else:\n"
        output_str += '    err_str = f"set instance called more than once in one session"\n'
        output_str += '    logging.exception(err_str)\n'
        output_str += '    raise Exception(err_str)\n'
        return output_str
