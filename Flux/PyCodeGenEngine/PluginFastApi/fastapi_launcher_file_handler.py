import os
import time
from abc import ABC

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from FluxPythonUtils.scripts.utility_functions import convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiLauncherFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def _handle_callback_override_set_instance_import(self) -> str:
        callback_override_set_instance_file_path = \
            self.import_path_from_os_path("OUTPUT_DIR", self.callback_override_set_instance_file_name)
        output_str = "# below import is to set derived callback's instance if implemented in the script\n"
        callback_override_set_instance_file_path = ".".join(callback_override_set_instance_file_path.split(".")[:-1])
        output_str += f"from {callback_override_set_instance_file_path} import " \
                      f"{self.callback_override_set_instance_file_name}\n"
        callback_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.routes_callback_class_name}")
        routes_callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from {callback_file_path} import {routes_callback_class_name_camel_cased}\n\n\n"

        return output_str

    def handle_launch_file_gen(self) -> str:
        output_str = "import os\n"
        output_str += "import uvicorn\n"
        output_str += "import logging\n"
        output_str += self._handle_callback_override_set_instance_import()
        routes_callback_class_name_camel_cased = convert_to_capitalized_camel_case(self.routes_callback_class_name)
        output_str += f"from FluxPythonUtils.scripts.utility_functions import configure_logger\n\n"
        output_str += f'configure_logger(os.getenv("LOG_LEVEL"), log_file_name=os.getenv("LOG_FILE_PATH"))\n'
        output_str += "\n\n"
        output_str += f'def {self.launch_file_name}():\n'
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
        output_str += f'    host = "127.0.0.1" if (env_host := os.getenv("HOST")) is None else env_host\n'
        output_str += f'    port = 8000 if (env_port := os.getenv("PORT")) is None else int(env_port)\n'
        output_str += f'    if (fastapi_file_name := os.getenv("FASTAPI_FILE_NAME")) is None:\n'
        output_str += f'        err_str = "Env Var FASTAPI_FILE_NAME received as None"\n'
        output_str += f'        logging.exception(err_str)\n'
        output_str += f'        raise Exception(err_str)\n'
        output_str += f'    # else not required: if fastapi file name received successfully then running server\n'
        output_str += f'    uvicorn.run(reload=reload_status, \n'
        output_str += f'                host=host, \n'
        output_str += f'                port=port, \n'
        output_str += '                app=f"{fastapi_file_name}'+f':{self.fastapi_app_name}", \n'
        output_str += f'                log_level=20)\n'
        output_str += f'    callback_instance.app_launch_post()\n'
        return output_str
