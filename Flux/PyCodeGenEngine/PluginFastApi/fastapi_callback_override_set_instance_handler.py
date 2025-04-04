import os
import time
import logging
from abc import ABC
from pathlib import PurePath
from typing import List

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from FluxPythonUtils.scripts.general_utility_functions import convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiCallbackOverrideSetInstanceHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def _handle_callback_override_set_instance_file_gen(self, model_type_list: List[str]) -> str:
        output_str = "# File to contain injection of override callback instance using set instance\n\n"
        if not ((total_root_msg := len(self.root_message_list)) >= 4):
            err_str = f"Model file might have less then 4 root models, complete generation " \
                      f"requires at least 4 models, received {total_root_msg}, generating limited callback " \
                      f"override examples with available messages"
            logging.exception(err_str)
        output_str += "# standard imports\n"
        output_str += "import logging\n"
        output_str += "import os\n"
        output_str += "from pathlib import PurePath\n\n"

        output_str += "# project imports\n"
        callback_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", f"{self.routes_callback_file_name}")
        output_str += f"from {callback_file_path} import {self.routes_callback_class_name}\n"
        output_str += f"from FluxPythonUtils.scripts.general_utility_functions import YAMLConfigurationManager\n\n\n"
        output_str += 'config_yaml_path = PurePath(__file__).parent.parent.parent / "data" / f"config.yaml"\n'
        output_str += 'if os.path.exists(config_yaml_path):\n'
        output_str += '    config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))\n'
        output_str += '    host = config_yaml_dict.get("server_host")\n\n'
        output_str += '    if host is None:\n\n'
        output_str += '        err_str = "Can not find \'server_host\' key in data/config.yaml file loaded dict"\n'
        output_str += '        logging.exception(err_str)\n'
        output_str += '        raise Exception(err_str)\n'
        output_str += 'else:\n'
        output_str += '    err_str = f"'+f'data/config.yaml does not exist"\n'
        output_str += '    logging.exception(err_str)\n'
        output_str += '    raise Exception(err_str)\n\n'

        output_str += 'if (model_type := os.getenv("ModelType")) is None or len(model_type) == 0:\n'
        output_str += '\terr_str = f"env var ModelType must not be {model_type}"\n'
        output_str += '\tlogging.exception(err_str)\n'
        output_str += '\traise Exception(err_str)\n'
        output_str += 'else:\n'
        output_str += '\tmatch model_type.lower():\n'
        for model_type in model_type_list:
            output_str += f'\t\tcase "{model_type}":\n'
            if (project_dir := os.getenv("PROJECT_DIR")) is not None and len(project_dir):
                if model_type in ["beanie", "dataclass", "msgspec"]:
                    native_override_routes_callback_class_name = self.beanie_native_override_routes_callback_class_name
                    base_override_routes_callback_class_name = self.beanie_bare_override_routes_callback_class_name
                else:
                    native_override_routes_callback_class_name = self.cache_native_override_routes_callback_class_name
                    base_override_routes_callback_class_name = self.cache_bare_override_routes_callback_class_name
                for override_routes_callback_class_name in [native_override_routes_callback_class_name,
                                                            base_override_routes_callback_class_name]:
                    callback_override_path = \
                        self.import_path_from_os_path("PROJECT_DIR", f"app.{override_routes_callback_class_name}")
                    routes_callback_class_name_override_camel_cased = \
                        convert_to_capitalized_camel_case(override_routes_callback_class_name)
                    output_str += f"\t\t\tfrom {callback_override_path} import " \
                                  f"{routes_callback_class_name_override_camel_cased}\n"
                output_str += "\n"
            else:
                err_str = f"Env Var PROJECT_DIR received as {project_dir}"
                logging.exception(err_str)
                raise Exception(err_str)

            output_str += \
                f"\t\t\tif {self.routes_callback_class_name}." \
                f"{self.routes_callback_file_name}_instance is None:\n"
            output_str += f'\t\t\t\toverride_type = config_yaml_dict.get("{model_type}_override_type")\n'
            output_str += f'\t\t\t\tif override_type is None or override_type.lower() == "bare":\n'
            routes_callback_class_name_override_camel_cased = \
                convert_to_capitalized_camel_case(base_override_routes_callback_class_name)
            output_str += f'\t\t\t\t\tcallback_override = {routes_callback_class_name_override_camel_cased}()\n'
            output_str += f'\t\t\t\telif override_type.lower() == "native":\n'
            routes_callback_class_name_override_camel_cased = \
                convert_to_capitalized_camel_case(native_override_routes_callback_class_name)
            output_str += f'\t\t\t\t\tcallback_override = {routes_callback_class_name_override_camel_cased}()\n'
            output_str += f'\t\t\t\telse:\n'
            output_str += f'\t\t\t\t\terr_str = f"Unsupported config value of {model_type}_override_type: ' + \
                          '{override_type}"\n'
            output_str += '\t\t\t\t\tlogging.exception(err_str)\n'
            output_str += '\t\t\t\t\traise Exception(err_str)\n'
            output_str += f"\t\t\t\t{self.routes_callback_class_name}.set_instance(callback_override)\n"
            output_str += "\t\t\telse:\n"
            output_str += f'\t\t\t\terr_str = f"set instance for ModelType {model_type} called more than ' \
                          f'once in one session"\n'
            output_str += '\t\t\t\tlogging.exception(err_str)\n'
            output_str += '\t\t\t\traise Exception(err_str)\n'
        output_str += '\t\tcase other:\n'
        output_str += '\t\t\terr_str = f"unsupported db type {model_type}"\n'
        output_str += '\t\t\tlogging.exception(err_str)\n'
        output_str += '\t\t\traise Exception(err_str)\n'

        # generating override files if not exist already
        project_path = os.getenv("PROJECT_DIR")
        if project_path:
            # checking if app dir doesn't exist
            if not os.path.exists(PurePath(project_path) / "app"):
                # if not exists, creating
                os.mkdir(PurePath(project_path) / "app")

            base_native_callback_override_path = \
                PurePath(project_path) / "app" / self.base_native_override_routes_callback_class_name
            beanie_native_callback_override_path = \
                PurePath(project_path) / "app" / self.beanie_native_override_routes_callback_class_name
            beanie_bare_callback_override_path = \
                PurePath(project_path) / "app" / self.beanie_bare_override_routes_callback_class_name
            cache_native_callback_override_path = \
                PurePath(project_path) / "app" / self.cache_native_override_routes_callback_class_name
            cache_bare_callback_override_path = \
                PurePath(project_path) / "app" / self.cache_bare_override_routes_callback_class_name
            for file_path in [base_native_callback_override_path, beanie_native_callback_override_path,
                              beanie_bare_callback_override_path, cache_native_callback_override_path,
                              cache_bare_callback_override_path]:
                if not os.path.exists(f"{file_path}.py"):
                    with open(f"{file_path}.py", "w") as f:
                        base_native_override_class_name = \
                            convert_to_capitalized_camel_case(self.base_native_override_routes_callback_class_name)
                        if self.base_native_override_routes_callback_class_name == str(file_path).split(os.sep)[-1]:
                            callback_override_class_name = base_native_override_class_name
                            parent_callback_class_name = self.routes_callback_class_name
                            parent_callback_import_path = \
                                self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_callback_import_file_name)
                        elif self.beanie_native_override_routes_callback_class_name == str(file_path).split(os.sep)[-1]:
                            callback_override_class_name = \
                                convert_to_capitalized_camel_case(self.beanie_native_override_routes_callback_class_name)
                            parent_callback_class_name = base_native_override_class_name
                            parent_callback_import_path = \
                                self.import_path_from_os_path("PROJECT_DIR",
                                                              f"app.{self.base_native_override_routes_callback_class_name}")
                        elif self.beanie_bare_override_routes_callback_class_name == str(file_path).split(os.sep)[-1]:
                            callback_override_class_name = \
                                convert_to_capitalized_camel_case(self.beanie_bare_override_routes_callback_class_name)
                            parent_callback_class_name = self.routes_callback_class_name
                            parent_callback_import_path = \
                                self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_callback_import_file_name)
                        elif self.cache_native_override_routes_callback_class_name == str(file_path).split(os.sep)[-1]:
                            callback_override_class_name = \
                                convert_to_capitalized_camel_case(self.cache_native_override_routes_callback_class_name)
                            parent_callback_class_name = base_native_override_class_name
                            parent_callback_import_path = \
                                self.import_path_from_os_path("PROJECT_DIR",
                                                              f"app.{self.base_native_override_routes_callback_class_name}")
                        else:
                            callback_override_class_name = \
                                convert_to_capitalized_camel_case(self.cache_bare_override_routes_callback_class_name)
                            parent_callback_class_name = self.routes_callback_class_name
                            parent_callback_import_path = \
                                self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_callback_import_file_name)
                        content_str = "# project imports\n"
                        content_str += f"from {parent_callback_import_path} import {parent_callback_class_name}\n\n\n"
                        content_str += f"class {callback_override_class_name}({parent_callback_class_name}):\n"
                        content_str += f"    def __init__(self):\n"
                        content_str += f"        super().__init__()\n"
                        content_str += f"        pass\n"
                        f.write(content_str)
        else:
            err_str = "Received 'PROJECT_DIR' as None"
            logging.exception(err_str)
            raise Exception(err_str)

        return output_str

    def handle_callback_override_set_instance_file_gen(self) -> str:
        return self._handle_callback_override_set_instance_file_gen(["beanie", "cache"])

    def handle_dataclass_callback_override_set_instance_file_gen(self) -> str:
        return self._handle_callback_override_set_instance_file_gen(["dataclass"])

    def handle_msgspec_callback_override_set_instance_file_gen(self) -> str:
        return self._handle_callback_override_set_instance_file_gen(["msgspec"])
