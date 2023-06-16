import logging
import os
import time
from abc import ABC
from typing import List

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin


class FastapiClientFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_POST_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def create_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}BaseModel:\n"
        output_str += " "*8 + f"return generic_http_post_client(self.create_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_GET_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}) -> {message_name}BaseModel:\n"
        output_str += " "*8 + f"return generic_http_get_client(self.get_{message_name_snake_cased}_client_url, " \
                      f"{message_name_snake_cased}_id, {message_name}BaseModel)"
        return output_str

    def handle_PUT_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def put_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}BaseModel:\n"
        output_str += " "*4 + f"    return generic_http_put_client(self.put_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_PATCH_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_client(self, pydantic_obj_json: " \
                     f"Dict) -> {message_name}BaseModel:\n"
        output_str += " "*4 + f"    return generic_http_patch_client(self.patch_{message_name_snake_cased}" \
                      f"_client_url, pydantic_obj_json, {message_name}BaseModel)"
        return output_str

    def handle_DELETE_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def delete_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}) -> Dict:\n"
        output_str += " "*4 + f"    return generic_http_delete_client(self.delete_{message_name_snake_cased}" \
                      f"_client_url, {message_name_snake_cased}_id)"
        return output_str

    def handle_index_client_gen(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        index_fields: List[protogen.Field] = [field for field in message.fields
                                              if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index)]
        field_params = ", ".join([f"{field.proto.name}: {self.proto_to_py_datatype(field)}" for field in index_fields])
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_from_index_client(self, {field_params}) " \
                             f"-> List[{message_name}BaseModel]:\n"
        output_str += " "*4 + f"    return generic_http_index_client(" \
                      f"self.get_{message_name_snake_cased}_from_index_fields_client_url, " \
                      f"[{', '.join([f'{field.proto.name}' for field in index_fields])}], {message_name}BaseModel)\n\n"
        return output_str

    def handle_get_all_message_http_client(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_all_{message_name_snake_cased}_client(self) -> List[{message_name}BaseModel]:\n"
        output_str += " "*4 + f"    return generic_http_get_all_client(self.get_all_" \
                      f"{message_name_snake_cased}_client_url, {message_name}BaseModel)\n\n"
        return output_str

    def handle_get_all_message_ws_client(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"async def get_all_{message_name_snake_cased}_client_ws(self, user_callable: Callable):\n"
        output_str += " "*4 + f"    await generic_ws_get_all_client(self.get_all_{message_name_snake_cased}" \
                      f"_client_ws_url, {message_name}BaseModel, user_callable)\n\n"
        return output_str

    def handle_read_by_id_WEBSOCKET_client_gen(self, message: protogen.Message, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"async def get_{message_name_snake_cased}_client_ws(self, " \
                     f"{message_name_snake_cased}_id: {id_field_type}, user_callable: Callable):\n"
        output_str += " "*4 + f"    await generic_ws_get_client(self.get_{message_name_snake_cased}_client_ws_url, " \
                      f"{message_name_snake_cased}_id, {message_name}BaseModel, user_callable)"
        return output_str

    def _import_model_in_client_file(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str = f"from {model_file_path} import *\n"
        return output_str

    def _handle_client_routes_url(self, message: protogen.Message, message_name_snake_cased: str) -> str:
        output_str = ""
        option_value_dict = \
            self.get_complex_option_set_values(message,
                                               BaseFastapiPlugin.flux_msg_json_root)

        crud_field_name_to_url_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: f"self.create_{message_name_snake_cased}_client_url: "
                                                           "str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"create-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_read_field: f"self.get_{message_name_snake_cased}_client_url: str = "
                                                         "f'http://{self.host}:{self.port}/" +
                                                         f"{self.proto_file_package}/"
                                                         f"get-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_update_field: f"self.put_{message_name_snake_cased}_client_url: str = "
                                                           "f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"put-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_patch_field: f"self.patch_{message_name_snake_cased}_client_url: "
                                                          "str = f'http://{self.host}:{self.port}/" +
                                                          f"{self.proto_file_package}/"
                                                          f"patch-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_delete_field: f"self.delete_{message_name_snake_cased}_client_url: "
                                                           "str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"delete-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_read_websocket_field: f"self.get_{message_name_snake_cased}_"
                                                                   f"client_ws_url: "
                                                                   "str = f'ws://{self.host}:{self.port}/" +
                                                                   f"{self.proto_file_package}/get-"
                                                                   f"{message_name_snake_cased}-ws'"
        }
        output_str += " " * 8 + "self.get_all_" + f"{message_name_snake_cased}" + \
                      "_client_url: str = f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/get-all-{message_name_snake_cased}'\n"
        output_str += " " * 8 + "self.get_all_" + f"{message_name_snake_cased}" + \
                      "_client_ws_url: str = f'ws://{self.host}:{self.port}/" \
                      + f"{self.proto_file_package}/get-all-{message_name_snake_cased}-ws'\n"

        for crud_option_field_name, url in crud_field_name_to_url_dict.items():
            if crud_option_field_name in option_value_dict:
                output_str += " " * 8 + f"{url}"
                output_str += "\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index):
                output_str += " " * 8 + f"self.get_{message_name_snake_cased}_from_index_fields_client_url: " \
                                        f"str = f'http://" + "{self.host}:{self.port}/" + \
                              f"{self.proto_file_package}/get-{message_name_snake_cased}-from-index-fields'\n"
                break
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_client_query_url(self, message: protogen.Message):
        output_str = ""

        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiClientFileHandler.query_name_key]
            query_type = str(aggregate_value[FastapiClientFileHandler.query_type_key]).lower()[1:] \
                if aggregate_value[FastapiClientFileHandler.query_type_key] is not None else None

            if query_type is None or query_type == "http":
                url = f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/" + f"query-{query_name}'"
            elif query_type == "ws":
                url = f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/" + f"ws-query-{query_name}'"
            elif query_type == "both":
                url = f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/" + f"query-{query_name}'\n"
                url += f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                       f"{self.proto_file_package}/" + f"ws-query-{query_name}'"
            else:
                err_str = f"Unexpected query type {query_type} for web client code generation"
                logging.exception(err_str)
                raise Exception(err_str)
            output_str += " " * 8 + f"{url}\n"
        return output_str

    def _handle_client_url_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = ""
        if message in self.root_message_list:
            output_str += self._handle_client_routes_url(message, message_name_snake_cased)

        if message in self.message_to_query_option_list_dict:
            output_str += self._handle_client_query_url(message)

        return output_str

    def _handle_client_http_query_output(self, message: protogen.Message, query_name: str, query_params: List[str],
                                         params_str: str):
        message_name = message.proto.name
        if query_params:
            output_str = " " * 4 + f"def {query_name}_query_client(self, {params_str}) -> " \
                                    f"List[{message_name}]:\n"
            params_dict_str = \
                ', '.join([f'"{aggregate_param}": {aggregate_param}' for aggregate_param in query_params])
            output_str += " " * 4 + "    query_params_dict = {" + f"{params_dict_str}" + "}\n"
            output_str += " " * 4 + f"    return generic_http_query_client(self.query_{query_name}_url, " \
                                    f"query_params_dict, {message_name}BaseModel)\n\n"
        else:
            output_str = " " * 4 + f"def {query_name}_query_client(self) -> " \
                                    f"List[{message_name}]:\n"
            output_str += " " * 4 + f"    return generic_http_query_client(self.query_{query_name}_url, " \
                                    "{}, " + f"{message_name}BaseModel)\n\n"
        return output_str

    def _handle_client_ws_query_output(self, message: protogen.Message, query_name: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " " * 4 + f"async def {query_name}_ws_query_client(self, user_callable: Callable):\n"
        output_str += " " * 4 + f"    await generic_ws_get_all_client(self.get_all_{message_name_snake_cased}" \
                                f"_client_ws_url, {message_name}BaseModel, user_callable)\n\n"
        return output_str

    def _handle_client_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]
        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiClientFileHandler.query_name_key]
            query_params = aggregate_value[FastapiClientFileHandler.query_params_key]
            query_params_types = aggregate_value[FastapiClientFileHandler.query_params_data_types_key]
            query_type = str(aggregate_value[FastapiClientFileHandler.query_type_key]).lower()[1:] \
                if aggregate_value[FastapiClientFileHandler.query_type_key] is not None else None

            params_str = ", ".join([f"{aggregate_param}: {aggregate_params_type}"
                                    for aggregate_param, aggregate_params_type in zip(query_params,
                                                                                      query_params_types)])

            if query_type is None or query_type == "http":
                output_str += self._handle_client_http_query_output(message, query_name, query_params, params_str)
            elif query_type == "ws":
                output_str += self._handle_client_ws_query_output(message, query_name)
            elif query_type == "both":
                output_str += self._handle_client_http_query_output(message, query_name, query_params, params_str)
                output_str += self._handle_client_ws_query_output(message, query_name)
            else:
                err_str = f"Unsupported Query type for query web client code generation {query_type}"
                logging.exception(err_str)
                raise Exception(err_str)

        return output_str

    def _handle_client_route_methods(self, message: protogen.Message) -> str:
        output_str = ""
        option_value_dict = \
            self.get_complex_option_set_values(message,
                                               BaseFastapiPlugin.flux_msg_json_root)

        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_client_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_client_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_client_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_client_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_client_gen,
            BaseFastapiPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_client_gen
        }

        output_str += self.handle_get_all_message_http_client(message)
        output_str += self.handle_get_all_message_ws_client(message)

        id_field_type: str = self._get_msg_id_field_type(message)

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_value_dict:
                output_str += crud_operation_method(message, id_field_type)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index):
                output_str += self.handle_index_client_gen(message)
                break
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def handle_client_methods(self, message: protogen.Message) -> str:
        output_str = ""
        if message in self.root_message_list:
            output_str += self._handle_client_route_methods(message)

        if message in self.message_to_query_option_list_dict:
            output_str += self._handle_client_query_methods(message)

        return output_str

    def handle_client_file_gen(self, file) -> str:
        if self.is_option_enabled(file, FastapiClientFileHandler.flux_file_crud_host):
            host = self.get_non_repeated_valued_custom_option_value(file, FastapiClientFileHandler.flux_file_crud_host)
        else:
            host = '"127.0.0.1"'

        if self.is_option_enabled(file, FastapiClientFileHandler.flux_file_crud_port_offset):
            port_offset = \
                self.get_non_repeated_valued_custom_option_value(file,
                                                                 FastapiClientFileHandler.flux_file_crud_port_offset)
            port = 8000 + int(port_offset)
        else:
            port = 8000

        output_str = f'from typing import Dict, List, Callable, Any\n'
        generic_web_client_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_web_client")
        output_str += f'from {generic_web_client_path} import *\n'
        output_str += self._import_model_in_client_file()
        output_str += "\n\n"
        output_str += f"class {convert_to_capitalized_camel_case(self.client_file_name)}:\n\n"
        output_str += "    def __init__(self, host: str | None = None, port: int | None = None):\n"
        output_str += " "*4 + "    # host and port\n"
        output_str += " "*4 + f'    self.host = {host} if host is None else host\n'
        output_str += " "*4 + f'    self.port = {port} if port is None else port\n\n'
        output_str += " "*4 + f'    # urls\n'
        for message in set(self.root_message_list+list(self.message_to_query_option_list_dict)):
            output_str += self._handle_client_url_gen(message)
            output_str += "\n"
        output_str += f'    # interfaces\n'
        for message in self.root_message_list:
            output_str += self.handle_client_methods(message)

        for message in list(self.message_to_query_option_list_dict):
            if message not in self.root_message_list:
                output_str += self.handle_client_methods(message)
            # else not required: root lvl message with query already executed in last loop

        return output_str
