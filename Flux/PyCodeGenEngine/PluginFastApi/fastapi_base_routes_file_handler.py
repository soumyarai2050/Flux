import os
import time
from abc import ABC
from typing import List, Dict, Tuple, Set
import logging

# 3rd party imports
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    parse_string_to_original_types, convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin, ModelType
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import (
    root_core_proto_files, project_grp_core_proto_files, project_dir)


class FastapiBaseRoutesFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.shared_lock_name_to_model_class_dict: Dict[str, List[protogen.Message]] = {}
        self.shared_lock_name_message_list: List[protogen.Message] = []
        self.message_to_link_messages_dict: Dict[protogen.Message, List[protogen.Message]] = {}

    def _handle_routes_callback_import(self) -> str:
        routes_callback_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_callback_file_name)
        output_str = f"from {routes_callback_path} import {self.routes_callback_class_name}\n"
        return output_str

    def _handle_routes_callback_instantiate(self):
        output_str = f"callback_class = {self.routes_callback_class_name}.get_instance()\n\n\n"
        return output_str

    def _set_shared_lock_name_to_model_class_dict(self):
        for message in self.root_message_list:
            # Setting lock for shared_lock option
            if self.is_option_enabled(message, FastapiBaseRoutesFileHandler.flux_msg_crud_shared_lock):
                shared_lock_name = \
                    self.get_simple_option_value_from_proto(message,
                                                            FastapiBaseRoutesFileHandler.flux_msg_crud_shared_lock)
                if shared_lock_name not in self.shared_lock_name_to_model_class_dict:
                    self.shared_lock_name_to_model_class_dict[shared_lock_name] = [message]
                else:
                    self.shared_lock_name_to_model_class_dict[shared_lock_name].append(message)

                if message not in self.shared_lock_name_message_list:
                    self.shared_lock_name_message_list.append(message)
                # else not required: avoiding repetition
            # else not required: avoiding precess if message doesn't have shared_lock option set

            # setting shared lock for link messages
            linked_messages: List[protogen.Message] = self.message_to_link_messages_dict.get(message)
            if linked_messages is not None:
                linked_lock_name = f"{message.proto.name}_link_lock"
                self.shared_lock_name_to_model_class_dict[linked_lock_name] = [message] + linked_messages

    def _get_messages_having_links(self) -> None:
        for message in self.root_message_list:
            linked_messages: Set = set()
            for field in message.fields:
                if self.is_option_enabled(field, FastapiBaseRoutesFileHandler.flux_fld_collection_link):
                    if field.message is not None:
                        linked_messages.add(field.message)
                    else:
                        err_str = f"Message can't be linked to non-root message, " \
                                  f"currently {message} is linked to {field.message}"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else not required: avoid if option not set

            if linked_messages:
                self.message_to_link_messages_dict[message] = list(linked_messages)

    def _handle_model_imports(self, file: protogen.File | None = None, model_file_suffix: str | None = None) -> str:
        # model imports
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str = f"from {model_file_path} import *\n"

        if file and model_file_suffix:
            project_grp_root_dir = PurePath(project_dir).parent.parent / "ORMModel"
            dependency_file_path_list = self.get_dependency_file_path_list(
                file, root_core_proto_files, project_grp_core_proto_files,
                model_file_suffix, str(project_grp_root_dir))

            project_name = file.proto.package
            for dependency_file_path in dependency_file_path_list:
                if f"_n_{project_name}" in dependency_file_path or f"{project_name}_n_" in dependency_file_path:
                    output_str += f'from {dependency_file_path} import *\n'
        output_str += "\n\n"
        return output_str

    def _get_filter_agg_projection_model(self, message: protogen.Message) -> str | None:
        additional_agg_option_val_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     BaseFastapiPlugin.flux_msg_main_crud_operations_agg)
        return additional_agg_option_val_dict.get("projection_model_name")

    def _get_filter_configs_var_name(self, message: protogen.Message, param_name: str | None = None,
                                     put_param: bool | None = True, put_limit: bool | None = None) -> str:
        filter_option_val_list_of_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     BaseFastapiPlugin.flux_msg_nested_fld_val_filter_param,
                                                     is_option_repeated=True)
        field_name_list = []
        for filter_option_dict in filter_option_val_list_of_dict:
            if "field_name" in filter_option_dict:
                field_name = filter_option_dict["field_name"]
                field_name_list.append(field_name)
        if field_name_list:
            return_str = "_n_".join(field_name_list)
            override_default_get_all_limit = False
            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_main_crud_operations_agg):
                additional_agg_option_val_dict = \
                    self.get_complex_option_value_from_proto(message,
                                                             BaseFastapiPlugin.flux_msg_main_crud_operations_agg)
                additional_agg_name = additional_agg_option_val_dict["agg_var_name"]
                override_default_get_all_limit = additional_agg_option_val_dict.get("override_get_all_limit_handling")
                return_str += f"_n_{additional_agg_name}"
            return_str += "_filter_config"
            if put_param:
                if param_name is not None:
                    if override_default_get_all_limit and put_limit:
                        return_str += f"({param_name}, limit_obj_count)"
                    else:
                        return_str += f"({param_name})"
                else:
                    if override_default_get_all_limit and put_limit:
                        return_str += f"(None, limit_obj_count)"
                    else:
                        return_str += f"(None)"

            return return_str
        elif self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_main_crud_operations_agg):
            additional_agg_option_val_dict = \
                self.get_complex_option_value_from_proto(message,
                                                         BaseFastapiPlugin.flux_msg_main_crud_operations_agg)

            override_default_get_all_limit = additional_agg_option_val_dict.get("override_get_all_limit_handling")
            return_str = f"{message.proto.name}_limit_filter_config"
            if put_param:
                if param_name is not None:
                    if override_default_get_all_limit and put_limit:
                        return_str += f"({param_name}, limit_obj_count)"
                    else:
                        return_str += f"({param_name})"
                else:
                    if override_default_get_all_limit and put_limit:
                        return_str += f"(None, limit_obj_count)"
                    else:
                        return_str += f"(None)"
            return return_str
        else:
            return ""

    def _set_filter_config_vars(self, message: protogen.Message) -> str:
        filter_list = []
        filter_option_val_list_of_dict = \
            self.get_complex_option_value_from_proto(message,
                                                     BaseFastapiPlugin.flux_msg_nested_fld_val_filter_param,
                                                     is_option_repeated=True)
        for filter_option_dict in filter_option_val_list_of_dict:
            temp_list = []
            if "field_name" in filter_option_dict:
                field_name = filter_option_dict["field_name"]
                temp_list.append(field_name)
                if "bool_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["bool_val_filters"], list):
                        filter_option_dict["bool_val_filters"] = [filter_option_dict["bool_val_filters"]]
                    # else not required: if filter_option_dict["bool_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["bool_val_filters"])
                elif "string_val_filters" in filter_option_dict:
                    if not isinstance(filter_option_dict["string_val_filters"], list):
                        filter_option_dict["string_val_filters"] = [filter_option_dict["string_val_filters"]]
                    # else not required: if filter_option_dict["string_val_filters"] already os list type then
                    # avoiding type-casting
                    temp_list.extend(filter_option_dict["string_val_filters"])
                else:
                    err_str = f"No valid val_filter option field found in filter option for filter field: {field_name}"
                    logging.exception(err_str)
                    raise Exception(err_str)

                filter_list.append(tuple(temp_list))

            else:
                err_str = f"No filter field_name key found in filter option: {filter_option_val_list_of_dict}"
                logging.exception(err_str)
                raise Exception(err_str)

        additional_agg_str = ""
        override_default_get_all_limit: bool = False
        if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_main_crud_operations_agg):
            additional_agg_option_val_dict = \
                self.get_complex_option_value_from_proto(message,
                                                         BaseFastapiPlugin.flux_msg_main_crud_operations_agg)

            override_default_get_all_limit = additional_agg_option_val_dict.get("override_get_all_limit_handling")
            agg_params = additional_agg_option_val_dict.get("agg_params")
            additional_agg_str = f"{additional_agg_option_val_dict['agg_var_name']}(model_obj"

            if override_default_get_all_limit:
                additional_agg_str += ", limit"

            if agg_params is not None:
                if isinstance(agg_params, list):
                    type_casted_agg_params = [str(parse_string_to_original_types(param)) for param in agg_params]
                    agg_params = ", ".join(type_casted_agg_params)
                else:
                    agg_params = parse_string_to_original_types(agg_params)

                additional_agg_str += f", {agg_params}"
            additional_agg_str += ")"

        # else not required: by-passing if option not used

        if filter_list:
            var_name = self._get_filter_configs_var_name(message, put_param=False)
            return_str = f"{var_name} = lambda model_obj : " + "{'redact': " + f"{filter_list}"
            if additional_agg_str:
                return_str += f", 'agg': {additional_agg_str}"
            return_str += "}\n"
            return return_str
        elif additional_agg_str:
            var_name = self._get_filter_configs_var_name(message, put_param=False)
            if override_default_get_all_limit:
                return_str = f"{var_name} = lambda model_obj, limit = None: " + "{'agg': " + f"{additional_agg_str}" + "}\n"
            else:
                return_str = f"{var_name} = lambda model_obj : " + "{'agg': " + f"{additional_agg_str}" + "}\n"
            return return_str
        else:
            return ""

    def _handle_CRUD_shared_locks_declaration(self):
        output_str = ""
        for lock_name in self.shared_lock_name_to_model_class_dict:
            output_str += f"{lock_name} = AsyncRLock()\n"
        return output_str

    def handle_base_routes_file_gen(self, file: protogen.File | None = None, model_suffix: str | None = None) -> str:
        # running pre-requisite method to set shared lock option info
        self._get_messages_having_links()
        self._set_shared_lock_name_to_model_class_dict()

        output_str = ("# Imports in this file are used by importing files so should not be removed "
                      "for being unused in current file\n")
        output_str += "\n"
        output_str += "# python standard modules\n"
        output_str += "from typing import List, Any, Dict, Final, Callable\n"
        output_str += "import copy\n"
        output_str += "\n"
        output_str += "# third-party modules\n"
        output_str += "from fastapi import APIRouter, Request, Query, UploadFile\n"
        output_str += "from fastapi.templating import Jinja2Templates\n"
        output_str += "\n"
        output_str += "# project imports\n"
        output_str += self._handle_routes_callback_import()
        output_str += self._handle_model_imports(file, model_suffix)
        if self.response_field_case_style.lower() == "camel":
            output_str += f"from FluxPythonUtils.scripts.model_base_utils import to_camel\n"
        output_str += f"from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager\n"
        # else not required: if response type is not camel type then avoid import
        default_web_response_file_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "default_web_response")
        output_str += f'from {default_web_response_file_path} import *\n'
        perf_benchmark_decorators_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH",
                                                                      "perf_benchmark_decorators")
        output_str += f"from {perf_benchmark_decorators_path} import perf_benchmark\n"
        output_str += f"from FluxPythonUtils.scripts.async_rlock import AsyncRLock\n"
        aggregate_file_path = self.import_path_from_os_path("PROJECT_DIR", "app.aggregate")
        output_str += f'from {aggregate_file_path} import *'

        output_str += f"\n\n"
        output_str += 'config_path = PurePath(__file__).parent.parent.parent / "data" / "config.yaml"\n'
        output_str += 'config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_path))\n'
        temp_list = []  # used to prevent code repetition
        for message in self.root_message_list:
            filter_config_var_declaration = self._set_filter_config_vars(message)
            if filter_config_var_declaration not in temp_list:
                output_str += filter_config_var_declaration
                temp_list.append(filter_config_var_declaration)
            # else not required: preventing if declaration already added
        output_str += self._handle_CRUD_shared_locks_declaration()
        output_str += f"{self.api_router_app_name} = APIRouter()\n"
        output_str += self._handle_routes_callback_instantiate()
        return output_str

    def _unpack_kwargs_with_id_field_type(self, **kwargs) -> Tuple[protogen.Message, str, str, List[str], bool]:
        message: protogen.Message | None = kwargs.get("message")
        aggregation_type: str | None = kwargs.get("aggregation_type")
        id_field_type: str | None = kwargs.get("id_field_type")
        shared_lock_list: List[str] | None = kwargs.get("shared_lock_list")
        model_type: bool | None = kwargs.get("model_type")

        if message is None or aggregation_type is None or id_field_type is None:
            err_str = (f"Received kwargs having some None values out of message: "
                       f"{message.proto.name if message is not None else message}, "
                       f"aggregation_type: {aggregation_type}, id_field_type: {id_field_type}")
            logging.exception(err_str)
            raise Exception(err_str)
        return message, aggregation_type, id_field_type, shared_lock_list, model_type

    def _unpack_kwargs_without_id_field_type(self, **kwargs):
        message: protogen.Message | None = kwargs.get("message")
        aggregation_type: str | None = kwargs.get("aggregation_type")
        shared_lock_list: List[str] | None = kwargs.get("shared_lock_list")
        model_type: ModelType | None = kwargs.get("model_type")
        if message is None or aggregation_type is None:
            err_str = (f"Received kwargs having some None values out of message: "
                       f"{message.proto.name if message is not None else message}, "
                       f"aggregation_type: {aggregation_type}")
            logging.exception(err_str)
            raise Exception(err_str)
        return message, aggregation_type, shared_lock_list, model_type
