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
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}BaseModel:\n"
        output_str += " "*4 + f"    return generic_http_patch_client(self.patch_{message_name_snake_cased}" \
                      f"_client_url, pydantic_obj, {message_name}BaseModel)"
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
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import *\n"
        return output_str

    def _handle_client_routes_url(self, message: protogen.Message, message_name_snake_cased: str) -> str:
        output_str = ""
        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

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
            if crud_option_field_name in option_dict:
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
            aggregate_var_name = aggregate_value[FastapiClientFileHandler.aggregate_var_name_key]
            url = f"self.query_{aggregate_var_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                  f"{self.proto_file_package}/" + f"query-{aggregate_var_name}'"
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

    def _handle_client_query_methods(self, message: protogen.Message) -> str:
        message_name = message.proto.name

        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]
        for aggregate_value in aggregate_value_list:
            aggregate_var_name = aggregate_value[FastapiClientFileHandler.aggregate_var_name_key]
            aggregate_params = aggregate_value[FastapiClientFileHandler.aggregate_params_key]
            aggregate_params_types = aggregate_value[FastapiClientFileHandler.aggregate_params_data_types_key]

            params_str = ", ".join([f"{aggregate_param}: {aggregate_params_type}"
                                    for aggregate_param, aggregate_params_type in zip(aggregate_params,
                                                                                      aggregate_params_types)])

            if aggregate_params:
                output_str += " " * 4 + f"def {aggregate_var_name}_query_client(self, {params_str}) -> " \
                                        f"List[{message_name}]:\n"
                params_dict_str = \
                    ', '.join([f'"{aggregate_param}": {aggregate_param}' for aggregate_param in aggregate_params])
                output_str += " " * 4 + "    query_params_dict = {"+f"{params_dict_str}"+"}\n"
                output_str += " " * 4 + f"    return generic_http_query_client(self.query_{aggregate_var_name}_url, " \
                                        f"query_params_dict, {message_name}BaseModel)\n\n"
            else:
                output_str += " " * 4 + f"def {aggregate_var_name}_query_client(self) -> " \
                                        f"List[{message_name}]:\n"
                output_str += " " * 4 + f"    return generic_http_query_client(self.query_{aggregate_var_name}_url, " \
                                        "{}, "+f"{message_name}BaseModel)\n\n"

        return output_str

    def _handle_client_route_methods(self, message: protogen.Message) -> str:
        output_str = ""
        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_json_root)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

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
            if crud_option_field_name in option_dict:
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
        if FastapiClientFileHandler.flux_file_crud_host in str(file.proto.options):
            host = self.get_non_repeated_valued_custom_option_value(file.proto.options,
                                                                    FastapiClientFileHandler.flux_file_crud_host)
        else:
            host = '"127.0.0.1"'

        if FastapiClientFileHandler.flux_file_crud_port_offset in str(file.proto.options):
            port_offset = \
                self.get_non_repeated_valued_custom_option_value(file.proto.options,
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
        for message in self.root_message_list+list(self.message_to_query_option_list_dict):
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
