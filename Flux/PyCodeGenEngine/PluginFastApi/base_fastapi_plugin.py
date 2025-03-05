#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, ClassVar, Tuple, Final
import time
from abc import abstractmethod
from enum import auto
import copy

# 3rd party imports
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int
from fastapi_restful.enums import StrEnum

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen

# empty main import below is required for making main accessible to derived classes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.general_utility_functions import convert_to_capitalized_camel_case
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class ModelType(StrEnum):
    Beanie = auto()
    Dataclass = auto()
    Msgspec = auto()


class BaseFastapiPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    query_name_key: ClassVar[str] = "query_name"
    query_aggregate_var_name_key: ClassVar[str] = "query_agg_var_name"
    query_params_key: ClassVar[str] = "query_params"
    query_type_key: ClassVar[str] = "query_type"
    query_route_type_key: ClassVar[str] = "query_route_type"
    button_query_data_key: ClassVar[str] = "query_data"
    button_query_file_upload_options_key: ClassVar[str] = "file_upload_options"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None and \
                len(response_field_case_style):
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'RESPONSE_FIELD_CASE_STYLE' received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        self.root_message_list: List[protogen.Message] = []
        self.message_to_query_option_list_dict: Dict[protogen.Message, List[Dict]] = {}
        self.message_to_button_query_data_dict: Dict[protogen.Message, Dict] = {}
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.model_dir_name: str = "ORMModel"
        self.fastapi_app_name: str = ""
        self.proto_file_name: str = ""
        self.proto_file_package: str = ""
        self.api_router_app_name: str = ""
        self.database_file_name: str = ""
        self.fastapi_file_name: str = ""
        self.model_file_name: str = ""
        self.base_routes_file_name: str = ""
        self.http_routes_file_name: str = ""
        self.ws_routes_file_name: str = ""
        self.client_file_name: str = ""
        self.ws_client_file_name: str = ""
        self.ws_ui_proxy_config_file_name: Final[str] = "ui_uri_to_server_uri_config.yaml"
        self.launch_file_name: str = ""
        self.routes_callback_file_name: str = ""
        self.routes_callback_class_name: str = ""
        self.routes_callback_import_file_name: str = ""
        self.http_routes_import_file_name: str = ""
        self.base_native_override_routes_callback_class_name: str = ""
        self.beanie_native_override_routes_callback_class_name: str = ""
        self.beanie_bare_override_routes_callback_class_name: str = ""
        self.cache_native_override_routes_callback_class_name: str = ""
        self.cache_bare_override_routes_callback_class_name: str = ""
        self.int_id_message_list: List[protogen.Message] = []
        self.callback_override_set_instance_file_name: str = ""
        self.reentrant_lock_non_required_msg: List[protogen.Message] = [
            # messages having SetReentrantLock field as True of FluxMsgJsonRoot option
        ]

    def update_root_msg_list(self, message: protogen.Message) -> None:
        if message not in self.root_message_list:
            self.root_message_list.append(message)
        # else not required: avoiding repetition

    def update_non_root_msg_list(self, message: protogen.Message) -> None:
        if message not in self.non_root_message_list:
            self.non_root_message_list.append(message)
        # else not required: avoiding repetition

    def update_query_data_members(self, message: protogen.Message) -> None:
        if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_query):
            if message not in self.message_to_query_option_list_dict:
                self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
            # else not required: avoiding repetition
        # else not required: avoiding list append if msg is not having option for query

        if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_button_query):
            if message not in self.message_to_button_query_data_dict:
                option_val_list = self.get_complex_option_value_from_proto(message, BaseFastapiPlugin.flux_msg_button_query, is_option_repeated=True)
                self.message_to_button_query_data_dict[message] = option_val_list
            # else not required: avoiding repetition
        # else not required: avoiding list append if msg is not having option for file query

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if (self.is_option_enabled(field.message, BaseFastapiPlugin.flux_msg_json_root) or
                        self.is_option_enabled(field.message, BaseFastapiPlugin.flux_msg_json_root_time_series)):
                    self.update_root_msg_list(field.message)
                else:
                    self.update_non_root_msg_list(field.message)

                self.load_dependency_messages_and_enums_in_dicts(field.message)

                self.update_query_data_members(message)

            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        message_list.sort(key=lambda message_: message_.proto.name)     # sorting by name

        for message in message_list:
            if ((is_json_root := self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root)) or
                    self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root_time_series)):
                if is_json_root:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, BaseFastapiPlugin.flux_msg_json_root)
                else:
                    json_root_msg_option_val_dict = \
                        self.get_complex_option_value_from_proto(message, BaseFastapiPlugin.flux_msg_json_root_time_series)
                if (is_reentrant_required := json_root_msg_option_val_dict.get(
                        BaseFastapiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                self.update_root_msg_list(message)

                for field in message.fields:
                    if field.proto.name == BaseFastapiPlugin.default_id_field_name and \
                            "int" == self.proto_to_py_datatype(field):
                        self.int_id_message_list.append(message)
                    # else enot required: If field is not id or is not type int then avoiding append
                    # in int_id_message_list
            else:
                self.update_non_root_msg_list(message)

            self.update_query_data_members(message)

            self.load_dependency_messages_and_enums_in_dicts(message)

    def get_query_option_message_values(self, message: protogen.Message) -> List[Dict]:
        list_of_agg_value_dict = []
        options_list_of_dict = \
            self.get_complex_option_value_from_proto(message, BaseFastapiPlugin.flux_msg_json_query, is_option_repeated=True)
        for option_dict in options_list_of_dict:
            agg_value_dict = {}
            agg_value_dict[BaseFastapiPlugin.query_name_key] = \
                option_dict[BaseFastapiPlugin.flux_json_query_name_field]
            agg_value_dict[BaseFastapiPlugin.query_aggregate_var_name_key] = \
                option_dict.get(BaseFastapiPlugin.flux_json_query_aggregate_var_name_field)
            agg_value_dict[BaseFastapiPlugin.query_type_key] = \
                option_dict.get(BaseFastapiPlugin.flux_json_query_type_field)
            agg_value_dict[BaseFastapiPlugin.query_route_type_key] = \
                option_dict.get(BaseFastapiPlugin.flux_json_query_route_type_field)
            agg_value_dict[BaseFastapiPlugin.query_params_key] = []
            if (query_params := option_dict.get(
                    BaseFastapiPlugin.flux_json_query_params_field)) is not None:
                # time.sleep(10)
                for query_param in query_params:
                    query_param_name = query_param.get(BaseFastapiPlugin.flux_json_query_params_name_field)
                    query_param_type = query_param.get(BaseFastapiPlugin.flux_json_query_params_data_type_field)
                    agg_value_dict[BaseFastapiPlugin.query_params_key].append((query_param_name, query_param_type))
            list_of_agg_value_dict.append(agg_value_dict)
        return list_of_agg_value_dict

    def proto_to_py_datatype(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "message":
                return field.message.proto.name
            case "enum":
                return field.enum.proto.name
            case other:
                return BaseFastapiPlugin.proto_type_to_py_type_dict[field.kind.name.lower()]

    def _get_msg_id_field_type(self, message: protogen.Message) -> str:
        id_field_type: str = BaseFastapiPlugin.default_id_type_var_name
        if message in self.int_id_message_list:
            for field in message.fields:
                if field.proto.name == BaseFastapiPlugin.default_id_field_name:
                    if "int" == (field_type := self.proto_to_py_datatype(field)):
                        id_field_type = field_type
                        break
                    elif "str" == (field_type := self.proto_to_py_datatype(field)):
                        id_field_type = field_type
                        break
                    else:
                        err_str = "id field other than int type not supported in fastapi impl"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

    def get_meta_data_field_name_to_type_str_dict(
            self, message: protogen.Message) -> Dict[str, Tuple[str, protogen.Field] |
                                                          Dict[str, Tuple[str, protogen.Field]]]:
        meta_data_field_name_to_field_tuple_dict: Dict[str, Tuple[str, protogen.Field] |
                                                         Dict[str, Tuple[str, protogen.Field]]] = {}

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_val_meta_field):
                meta_field = field
                is_required = field.cardinality.name.lower() == "required"
                break
        else:
            err_str = (f"Could not find any time field in {message.proto.name} message having "
                       f"{BaseFastapiPlugin.flux_msg_json_root_time_series} option")
            logging.exception(err_str)
            raise Exception(err_str)

        if meta_field.message is not None:
            meta_data_field_name_to_field_tuple_dict[meta_field.proto.name] = {}
            for nested_field in meta_field.message.fields:
                if nested_field.message is None:
                    is_required = nested_field.cardinality.name.lower() == "required"
                    field_type = self.proto_to_py_datatype(nested_field)
                    if is_required:
                        meta_data_field_name_to_field_tuple_dict[meta_field.proto.name][nested_field.proto.name] = (
                            field_type, nested_field)
                    else:
                        meta_data_field_name_to_field_tuple_dict[meta_field.proto.name][nested_field.proto.name] = (
                            f"{field_type} | None = None", nested_field)
                else:
                    err_str = ("Unsupported meta field type: meta field type must be either simple type or proto "
                               f"message type with only simple fields, received another field: "
                               f"{nested_field.proto.name} of message type {nested_field.message.proto.name} "
                               f"in meta_field: {meta_field.proto.name} of message: {message.proto.name}")
                    logging.exception(err_str)
                    raise Exception(err_str)
        else:
            field_type = self.proto_to_py_datatype(field)
            if is_required:
                meta_data_field_name_to_field_tuple_dict[meta_field.proto.name] = (field_type, field)
            else:
                meta_data_field_name_to_field_tuple_dict[meta_field.proto.name] = (f"{field_type} | None = None", field)
        return meta_data_field_name_to_field_tuple_dict

    def _import_current_routes_callback(self) -> List[str]:
        import_statements: List[str] = []
        model_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.routes_callback_file_name)
        import_statements.append(f"            from {model_file_path} import {self.routes_callback_class_name}\n")
        return import_statements

    def handle_routes_callback_import_file_gen(self) -> str:
        model_import_file_name = self.routes_callback_import_file_name + ".py"
        return self.handle_import_file_gen(model_import_file_name, self._import_current_routes_callback)

    def _import_current_http_routes(self) -> List[str]:
        import_statements: List[str] = []
        model_file_path = self.import_path_from_os_path("PLUGIN_OUTPUT_DIR", self.http_routes_file_name)
        import_statements.append(f"            from {model_file_path} import *\n")
        return import_statements

    def handle_http_routes_import_file_gen(self) -> str:
        model_import_file_name = self.http_routes_import_file_name + ".py"
        return self.handle_import_file_gen(model_import_file_name, self._import_current_http_routes)

    @abstractmethod
    def handle_fastapi_initialize_file_gen(self, **args):
        raise NotImplementedError

    def _get_if_pass_stored_obj_to_pre_post_callback(
            self, pass_stored_obj_pre_post_callback_field_name: str, **kwargs) -> bool:
        json_root_option_val = kwargs.get("json_root_option_val")
        if json_root_option_val is not None:
            pass_stored_obj_to_pre_post_callback: bool | None = (
                json_root_option_val.get(pass_stored_obj_pre_post_callback_field_name))

            if pass_stored_obj_to_pre_post_callback is not None:
                return pass_stored_obj_to_pre_post_callback
            else:
                return False
        else:
            err_str_ = "json_root_option_val not found in passed kwarg to put route generation"
            logging.error(err_str_)
            raise Exception(err_str_)

    @abstractmethod
    def set_req_data_members(self, file: protogen.File):
        """Pre Code generation initializations, must be called before code generation in `handle_fastapi_class_gen`"""
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.client_file_name = f"{self.proto_file_name}_http_client"
        self.ws_client_file_name = f"{self.proto_file_name}_ws_client"
        self.model_file_name = f'{self.proto_file_name}_model_imports'
        self.launch_file_name = self.proto_file_name + "_launch_server"
        self.base_routes_file_name = f'{self.proto_file_name}_base_routes'
        self.http_routes_file_name = f'{self.proto_file_name}_http_routes'
        self.ws_routes_file_name = f'{self.proto_file_name}_ws_routes'
        self.routes_callback_class_name = f"{convert_to_capitalized_camel_case(self.proto_file_name)}RoutesCallback"
        self.routes_callback_file_name = f"{self.proto_file_name}_routes_callback"
        self.routes_callback_import_file_name = f"{self.proto_file_name}_routes_callback_imports"
        self.http_routes_import_file_name = f"{self.proto_file_name}_http_routes_imports"
        self.base_native_override_routes_callback_class_name: str = \
            f"{self.proto_file_name}_routes_callback_base_native_override"
        self.beanie_native_override_routes_callback_class_name = \
            f"{self.proto_file_name}_routes_callback_beanie_native_override"
        self.beanie_bare_override_routes_callback_class_name = \
            f"{self.proto_file_name}_routes_callback_beanie_bare_override"
        self.cache_native_override_routes_callback_class_name = \
            f"{self.proto_file_name}_routes_callback_cache_native_override"
        self.cache_bare_override_routes_callback_class_name = \
            f"{self.proto_file_name}_routes_callback_cache_bare_override"
        self.callback_override_set_instance_file_name = f"{self.proto_file_name}_callback_override_set_instance"

