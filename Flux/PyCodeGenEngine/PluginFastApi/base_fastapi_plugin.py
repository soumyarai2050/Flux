#!/usr/bin/env python
import logging
import os
from typing import List, Callable, Dict, ClassVar
import time
from abc import abstractmethod

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
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

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_fastapi_class_gen
        ]
        if (response_field_case_style := os.getenv("RESPONSE_FIELD_CASE_STYLE")) is not None:
            self.response_field_case_style: str = response_field_case_style
        else:
            err_str = f"Env var 'OUTPUT_FILE_NAME_SUFFIX' received as {response_field_case_style}"
            logging.exception(err_str)
            raise Exception(err_str)
        # Since output file name for this plugin will be created at runtime
        self.output_file_name_suffix = ""
        self.root_message_list: List[protogen.Message] = []
        self.message_to_query_option_list_dict: Dict[protogen.Message, List[Dict]] = {}
        self.non_root_message_list: List[protogen.Message] = []
        self.enum_list: List[protogen.Enum] = []
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
        self.routes_callback_class_name_override: str = ""
        self.routes_callback_class_name_capital_camel_cased: str = ""
        self.int_id_message_list: List[protogen.Message] = []
        self.callback_override_set_instance_file_name: str = ""
        self.reentrant_lock_non_required_msg: List[protogen.Message] = [
            # messages having SetReentrantLock field as True of FluxMsgJsonRoot option
        ]
        self.reentrant_lock_on_top_required_msg: List[protogen.Message] = [
            # messages having SetReentrantLockToTop field as True of FluxMsgJsonRoot option
        ]

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        for field in message.fields:
            if field.kind.name.lower() == "enum":
                if field.enum not in self.enum_list:
                    self.enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if self.is_option_enabled(field.message, BaseFastapiPlugin.flux_msg_json_root):
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
            if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
                json_root_msg_option_val_dict = \
                    self.get_complex_option_values_as_list_of_dict(message, BaseFastapiPlugin.flux_msg_json_root)
                # taking first obj since json root is of non-repeated option
                if (is_reentrant_required := json_root_msg_option_val_dict[0].get(
                        BaseFastapiPlugin.flux_json_root_set_reentrant_lock_field)) is not None:
                    if not is_reentrant_required:
                        self.reentrant_lock_non_required_msg.append(message)
                    # else not required: If reentrant field of json root has True then
                    # avoiding its append to reentrant lock non-required list
                # else not required: If json root option don't have reentrant field then considering it requires
                # reentrant lock as default and avoiding its append to reentrant lock non-required list

                if (is_reentrant_on_top := json_root_msg_option_val_dict[0].get(
                        BaseFastapiPlugin.flux_json_root_set_reentrant_lock_to_top_field)) is not None:
                    if not is_reentrant_required:
                        err_str = "Field SetReentrantLock is set to true, avoiding adding model's reentrant lock " \
                                  "to generated route for this model therefor no use can be made of " \
                                  "SetReentrantLockToTop field set to true, make changes to proto file for it"
                        logging.error(err_str)
                        raise Exception(err_str)
                    else:
                        if is_reentrant_on_top:
                            self.reentrant_lock_on_top_required_msg.append(message)
                        # else not required: if not set or is false then lock will be created on default position
                # else not required: If not set then avoiding any processing for it

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
            self.get_complex_option_values_as_list_of_dict(message, BaseFastapiPlugin.flux_msg_json_query)
        for option_dict in options_list_of_dict:
            agg_value_dict = {}
            agg_value_dict[BaseFastapiPlugin.query_name_key] = \
                option_dict[BaseFastapiPlugin.flux_json_query_name_field]
            agg_value_dict[BaseFastapiPlugin.query_aggregate_var_name_key] = \
                option_dict.get(BaseFastapiPlugin.flux_json_query_aggregate_var_name_field)
            if (aggregate_params := option_dict.get(
                    BaseFastapiPlugin.flux_json_query_params_field)) is not None:
                aggregate_params_data_types = \
                    option_dict.get(BaseFastapiPlugin.flux_json_query_params_data_type_field)
                # if only one element exists in aggregate_params then it is received as single object so making it list
                # same for aggregate_params_data_types
                aggregate_params = aggregate_params if isinstance(aggregate_params, list) else [aggregate_params]
                aggregate_params_data_types = aggregate_params_data_types \
                    if isinstance(aggregate_params_data_types, list) else [aggregate_params_data_types]
                if len(aggregate_params) != len(aggregate_params_data_types):
                    err_str = f"{BaseFastapiPlugin.flux_msg_json_query} option should have equal numbers of" \
                              f"{BaseFastapiPlugin.flux_json_query_params_field} and " \
                              f"{BaseFastapiPlugin.flux_json_query_params_data_type_field}"
                    logging.exception(err_str)
                    raise Exception(err_str)
                else:
                    agg_value_dict[BaseFastapiPlugin.query_params_key] = aggregate_params
                    agg_value_dict[BaseFastapiPlugin.query_params_data_types_key] = aggregate_params_data_types
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
                    else:
                        err_str = "id field other than int type not supported in fastapi impl"
                        logging.exception(err_str)
                        raise Exception(err_str)
                # else not required: Avoiding field if not id
        # else not required: Avoid if message does not have custom id field
        return id_field_type

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
        self.routes_callback_class_name_override = f"{self.proto_file_name}_routes_callback_override"
        self.callback_override_set_instance_file_name = f"{self.proto_file_name}_callback_override_set_instance"

    @abstractmethod
    def handle_fastapi_class_gen(self, file: protogen.File) -> Dict[str, str]:
        """Main method: returns dictionary of filename and file's content as key-value pair"""
        raise NotImplementedError
