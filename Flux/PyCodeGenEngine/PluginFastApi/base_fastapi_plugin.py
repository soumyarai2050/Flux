#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, ClassVar, Tuple
import time
from abc import abstractmethod

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen

# empty main import below is required for making main accessible to derived classes
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_to_camel_case


class BaseFastapiPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to json schema
    """
    query_name_key: ClassVar[str] = "query_name"
    query_aggregate_var_name_key: ClassVar[str] = "query_agg_var_name"
    query_params_key: ClassVar[str] = "query_params"
    query_params_data_types_key: ClassVar[str] = "query_params_data_types"
    query_type_key: ClassVar[str] = "query_type"
    query_route_type_key: ClassVar[str] = "query_route_type"

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
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
        self.model_dir_name: str = "Pydentic"
        self.fastapi_app_name: str = ""
        self.proto_file_name: str = ""
        self.proto_file_package: str = ""
        self.api_router_app_name: str = ""
        self.database_file_name: str = ""
        self.fastapi_file_name: str = ""
        self.model_file_name: str = ""
        self.routes_file_name: str = ""
        self.client_file_name: str = ""
        self.launch_file_name: str = ""
        self.routes_callback_class_name: str = ""
        self.base_native_override_routes_callback_class_name: str = ""
        self.beanie_native_override_routes_callback_class_name: str = ""
        self.beanie_bare_override_routes_callback_class_name: str = ""
        self.cache_native_override_routes_callback_class_name: str = ""
        self.cache_bare_override_routes_callback_class_name: str = ""
        self.routes_callback_class_name_capital_camel_cased: str = ""
        self.int_id_message_list: List[protogen.Message] = []
        self.callback_override_set_instance_file_name: str = ""
        self.reentrant_lock_non_required_msg: List[protogen.Message] = [
            # messages having SetReentrantLock field as True of FluxMsgJsonRoot option
        ]

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if (self.is_option_enabled(field.message, BaseFastapiPlugin.flux_msg_json_root) or
                        self.is_option_enabled(field.message, BaseFastapiPlugin.flux_msg_json_root_time_series)):
                    if field.message not in self.root_message_list:
                        self.root_message_list.append(field.message)
                    # else not required: avoiding repetition
                else:
                    if field.message not in self.non_root_message_list:
                        self.non_root_message_list.append(field.message)
                    # else not required: avoiding repetition
                self.load_dependency_messages_and_enums_in_dicts(field.message)

                if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_query):
                    if message not in self.message_to_query_option_list_dict:
                        self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
                    # else not required: avoiding repetition
                # else not required: avoiding list append if msg is not having option for query

            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
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

                if message not in self.root_message_list:
                    self.root_message_list.append(message)
                # else not required: avoiding repetition

                for field in message.fields:
                    if field.proto.name == BaseFastapiPlugin.default_id_field_name and \
                            "int" == self.proto_to_py_datatype(field):
                        self.int_id_message_list.append(message)
                    # else enot required: If field is not id or is not type int then avoiding append
                    # in int_id_message_list
            else:
                if message not in self.non_root_message_list:
                    self.non_root_message_list.append(message)
                # else not required: avoiding repetition

            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_query):
                if message not in self.message_to_query_option_list_dict:
                    self.message_to_query_option_list_dict[message] = self.get_query_option_message_values(message)
                # else not required: avoiding repetition
            # else not required: avoiding list append if msg is not having option for query

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
            if (query_params := option_dict.get(
                    BaseFastapiPlugin.flux_json_query_params_field)) is not None:
                query_params_data_types = \
                    option_dict.get(BaseFastapiPlugin.flux_json_query_params_data_type_field)
                # if only one element exists in query_params then it is received as single object so making it list
                # same for query_params_data_types
                query_params = query_params if isinstance(query_params, list) else [query_params]
                query_params_data_types = query_params_data_types \
                    if isinstance(query_params_data_types, list) else [query_params_data_types]
                if len(query_params) != len(query_params_data_types):
                    err_str = f"{BaseFastapiPlugin.flux_msg_json_query} option should have equal numbers of" \
                              f"{BaseFastapiPlugin.flux_json_query_params_field} and " \
                              f"{BaseFastapiPlugin.flux_json_query_params_data_type_field}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                else:
                    agg_value_dict[BaseFastapiPlugin.query_params_key] = query_params
                    agg_value_dict[BaseFastapiPlugin.query_params_data_types_key] = query_params_data_types
            else:
                agg_value_dict[BaseFastapiPlugin.query_params_key] = []
                agg_value_dict[BaseFastapiPlugin.query_params_data_types_key] = []

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

    def get_meta_data_field_name_to_field_proto_dict(self, message: protogen.Message
                                                     ) -> Dict[str, protogen.Field | Dict[str, protogen.Field]]:
        meta_data_field_name_to_field_proto_dict: Dict[str, (protogen.Field | Dict[str, protogen.Field])] = {}

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_val_meta_field):
                meta_field = field
                break
        else:
            err_str = (f"Could not find any time field in {message.proto.name} message having "
                       f"{BaseFastapiPlugin.flux_msg_json_root_time_series} option")
            logging.exception(err_str)
            raise Exception(err_str)

        if meta_field.message is not None:
            meta_data_field_name_to_field_proto_dict[meta_field.proto.name] = {}
            for nested_field in meta_field.message.fields:
                if nested_field.message is None:
                    meta_data_field_name_to_field_proto_dict[meta_field.proto.name][nested_field.proto.name] = (
                        nested_field)
                else:
                    err_str = ("Unsupported meta field type: meta field type must be either simple type or proto "
                               f"message type with only simple field, received another field: "
                               f"{nested_field.proto.name} of message type {nested_field.message.proto.name} "
                               f"in meta_field: {meta_field.proto.name} of message: {message.proto.name}")
                    logging.exception(err_str)
                    raise Exception(err_str)
        else:
            meta_data_field_name_to_field_proto_dict[meta_field.proto.name] = meta_field
        return meta_data_field_name_to_field_proto_dict


    @abstractmethod
    def handle_fastapi_initialize_file_gen(self):
        raise NotImplementedError

    @abstractmethod
    def set_req_data_members(self, file: protogen.File):
        """Pre Code generation initializations, must be called before code generation in `handle_fastapi_class_gen`"""
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.proto_file_package = str(file.proto.package)
        self.fastapi_app_name = f"{self.proto_file_name}_app"
        self.api_router_app_name = f"{self.proto_file_name}_API_router"
        self.client_file_name = f"{self.proto_file_name}_web_client"
        self.model_file_name = f'{self.proto_file_name}_model_imports'
        self.launch_file_name = self.proto_file_name + "_launch_server"
        self.routes_file_name = f'{self.proto_file_name}_routes'
        self.routes_callback_class_name = f"{self.proto_file_name}_routes_callback"
        routes_callback_class_name_camel_cased: str = convert_to_camel_case(self.routes_callback_class_name)
        self.routes_callback_class_name_capital_camel_cased: str = \
            routes_callback_class_name_camel_cased[0].upper() + routes_callback_class_name_camel_cased[1:]
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

