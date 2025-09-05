#!/usr/bin/env python
import logging
import os
from typing import List, Dict
import time
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import main
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_file_handler import FastapiCallbackFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_http_client_file_handler import FastapiHttpClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_ws_client_file_handler import FastapiWSClientFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_launcher_file_handler import FastapiLauncherFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_http_routes_file_handler import FastapiHttpRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_ws_routes_file_handler import FastapiWsRoutesFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_file_handler import FastapiCallbackOverrideFileHandler
from Flux.PyCodeGenEngine.PluginFastApi.fastapi_callback_override_set_instance_handler import \
    FastapiCallbackOverrideSetInstanceHandler
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager


root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CacheFastApiPlugin(FastapiCallbackFileHandler,
                         FastapiCallbackOverrideSetInstanceHandler,
                         FastapiHttpClientFileHandler,
                         FastapiWSClientFileHandler,
                         FastapiHttpRoutesFileHandler,
                         FastapiWsRoutesFileHandler,
                         FastapiLauncherFileHandler,
                         FastapiCallbackOverrideFileHandler):
    """
    Plugin script to generate
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message],
                                                 avoid_non_roots: bool | None = None):
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name

        for message in message_list:
            if ((is_json_root := self.is_option_enabled(message, CacheFastApiPlugin.flux_msg_json_root)) or
                    self.is_option_enabled(message, CacheFastApiPlugin.flux_msg_json_root_time_series)):
                if is_json_root:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, CacheFastApiPlugin.flux_msg_json_root)
                else:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, CacheFastApiPlugin.flux_msg_json_root_time_series)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict.get(
                        CacheFastApiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == CacheFastApiPlugin.default_id_field_name:
                        if "int" == self.proto_to_py_datatype(field):
                            self.int_id_message_list.append(message)
                            break
                        elif "str" == self.proto_to_py_datatype(field):
                            break
                        else:
                            err_str = "Id field other than int or str are not supported for cached pydantic model"
                            logging.exception(err_str)
                            raise Exception(err_str)
                # else not required : If no id field exists then adding id field using int
                # auto-increment in next for loop
                else:
                    self.int_id_message_list.append(message)
            else:
                if not avoid_non_roots:
                    if message not in self.non_root_message_list:
                        self.non_root_message_list.append(message)
                    # else not required: avoiding repetition

            if self.is_option_enabled(message, CacheFastApiPlugin.flux_msg_json_query):
                if message not in self.message_to_query_option_list_dict:
                    self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
                # else not required: avoiding repetition
            # else not required: avoiding list append if msg is not having option for query

            self.load_dependency_messages_and_enums_in_dicts(message)

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                return CacheFastApiPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def handle_fastapi_initialize_file_gen(self):
        output_str = "import os\n"
        output_str += "from fastapi import FastAPI\n"
        routes_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.http_routes_file_name)
        output_str += f"from {routes_file_path} import {self.api_router_app_name}\n"
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str += f"from {model_file_path} import *\n"
        # else not required: if no message with custom id is found then avoiding import statement
        database_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.database_file_name)
        output_str += f"from {database_file_path} import init_db\n\n\n"
        output_str += f"{self.fastapi_app_name} = FastAPI(title='CRUD API of {self.proto_file_name}')\n\n\n"
        output_str += f"async def init_max_id_handler(document):\n"
        output_str += '    max_val = await document.find_all().max("_id")\n'
        output_str += '    document.init_max_id(int(max_val) if max_val is not None else 0)\n'
        output_str += '    document_list = await document.find_all().to_list()\n'
        output_str += '    document._cache_obj_id_to_obj_dict = {document_obj.id: document_obj for document_obj in document_list}\n\n\n'
        output_str += f'@{self.fastapi_app_name}.on_event("startup")\n'
        output_str += f'async def connect():\n'
        output_str += f'    await init_db()\n'
        for message in self.int_id_message_list:
            message_name = message.proto.name
            output_str += f"    await init_max_id_handler({message_name})\n"
        output_str += "\n\n"
        output_str += "if os.getenv('DEBUG'):\n"
        output_str += "    from fastapi.middleware.cors import CORSMiddleware\n\n"
        output_str += "    origins = ['*']\n"
        output_str += f"    {self.fastapi_app_name}.add_middleware(\n"
        output_str += f"        CORSMiddleware,\n"
        output_str += f"        allow_origins=origins,\n"
        output_str += f"        allow_credentials=True,\n"
        output_str += f"        allow_methods=['*'],\n"
        output_str += f"        allow_headers=['*'],\n"
        output_str += f"    )\n\n"
        output_str += f'{self.fastapi_app_name}.include_router({self.api_router_app_name}, ' \
                      f'prefix="/{self.proto_file_package}")\n'
        output_str += f"from fastapi.staticfiles import StaticFiles\n\n"
        output_str += f"{self.fastapi_app_name}.mount('/static', StaticFiles(directory='static'), name='static')\n\n"
        return output_str


    def set_req_data_members(self, file: protogen.File):
        super().set_req_data_members(file)
        self.fastapi_file_name = f"{self.proto_file_name}_cache_fastapi"
        self.database_file_name = f"{self.proto_file_name}_beanie_database"

    def output_file_generate_handler(self, file: protogen.File):
        # Pre-code generation initializations
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        self.set_req_data_members(file)

        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var PROJECT_DIR received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        core_or_util_files: List[str] = root_flux_core_config_yaml_dict.get("core_or_util_files")

        if "ProjectGroup" in project_dir:
            project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
            project_group_flux_core_config_yaml_dict = (
                YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
            project_grp_core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
            if project_grp_core_or_util_files:
                core_or_util_files.extend(project_grp_core_or_util_files)

        dependency_file_list = self._get_core_dependency_file_list(file)

        for dependency_file in dependency_file_list:
            self.load_root_and_non_root_messages_in_dicts(dependency_file.messages, avoid_non_roots=True)

        output_dict: Dict[str, str] = {
            # Adding project´s main.py
            self.fastapi_file_name + ".py": self.handle_fastapi_initialize_file_gen(),

            # Adding route's callback class
            self.routes_callback_class_name + ".py": self.handle_callback_class_file_gen(),

            # Adding callback override set_instance file
            self.callback_override_set_instance_file_name + ".py":
                self.handle_callback_override_set_instance_file_gen(),

            # Adding callback import file
            self.routes_callback_import_file_name + ".py": self.handle_routes_callback_import_file_gen(),

            # Adding dummy callback override class file
            "dummy_" + self.beanie_native_override_routes_callback_class_name + ".py": self.handle_callback_override_file_gen(),

            # Adding base routes.py
            self.base_routes_file_name + ".py": self.handle_base_routes_file_gen(),

            # Adding project's http routes.py
            self.http_routes_file_name + ".py": self.handle_http_pydantic_routes_file_gen(),

            # adding http routes import file
            self.http_routes_import_file_name + ".py": self.handle_http_routes_import_file_gen(),

            # Adding project's ws routes.py
            self.ws_routes_file_name + ".py": self.handle_ws_routes_file_gen(),

            # Adding project's run file
            self.launch_file_name + ".py": self.handle_launch_file_gen(file),

            # Adding client file
            self.client_file_name + ".py": self.handle_client_file_gen(file),

            # Adding WS client file
            self.ws_client_file_name + ".py": self.handle_ws_client_file_gen(file)
        }

        return output_dict


if __name__ == "__main__":
    main(CacheFastApiPlugin)
