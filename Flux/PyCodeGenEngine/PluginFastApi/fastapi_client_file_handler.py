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
                     f"{message_name}BaseModel) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_post_client(self.create_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_GET_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_get_client(self.get_{message_name_snake_cased}_client_url, " \
                      f"{message_name_snake_cased}_id, {message_name}BaseModel)"
        return output_str

    def handle_PUT_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def put_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_put_client(self.put_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel)"
        return output_str

    def handle_PATCH_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_client(self, pydantic_obj: " \
                     f"{message_name}BaseModel) -> {message_name}:\n"
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
                             f"-> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_index_client(" \
                      f"self.get_{message_name_snake_cased}_from_index_fields_client_url, " \
                      f"[{', '.join([f'{field.proto.name}' for field in index_fields])}], {message_name}BaseModel)\n\n"
        return output_str

    def handle_get_all_message_http_client(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_all_{message_name_snake_cased}_client(self) -> List[{message_name}]:\n"
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

    def handle_POST_query_client_gen(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def create_{message_name_snake_cased}_query_client(self) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_post_client(self.create_{message_name_snake_cased}" \
                      f"_query_client_url, None, {message_name}BaseModel)"
        return output_str

    def handle_GET_query_client_gen(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def get_{message_name_snake_cased}_query_client(self) -> {message_name}:\n"
        output_str += " "*8 + f"return generic_http_get_client(self.get_{message_name_snake_cased}_query_" \
                      f"client_url, None, {message_name}BaseModel)"
        return output_str

    def handle_PUT_query_client_gen(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def put_{message_name_snake_cased}_query_client(self) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_put_client(self.put_{message_name_snake_cased}_query_" \
                      f"client_url, None, {message_name}BaseModel)"
        return output_str

    def handle_PATCH_query_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_query_client(self) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_patch_client(self.patch_{message_name_snake_cased}" \
                      f"_query_client_url, None, {message_name}BaseModel)"
        return output_str

    def handle_DELETE_query_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def delete_{message_name_snake_cased}_query_client(self) -> {message_name}:\n"
        output_str += " "*4 + f"    return generic_http_delete_client(self.delete_{message_name_snake_cased}" \
                      f"_query_client_url, None, {message_name}BaseModel)"
        return output_str

    def handle_read_by_id_WEBSOCKET_query_client_gen(self, message: protogen.Message, id_field_type):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"async def get_{message_name_snake_cased}_query_client_ws(self, " \
                     f"{message_name_snake_cased}_id: {id_field_type}, user_callable: Callable):\n"
        output_str += " "*4 + f"    await generic_ws_get_client(self.get_{message_name_snake_cased}_query_" \
                      f"client_ws_url, None, {message_name}BaseModel, user_callable)"
        return output_str

    def _import_model_in_client_file(self) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", self.model_file_name)
        output_str = f"from {model_file_path} import {BaseFastapiPlugin.default_id_type_var_name}, "
        for enum in self.enum_list:
            output_str += enum.proto.name
            output_str += ", "
        for message in self.root_message_list:
            output_str += message.proto.name
            output_str += ", "
            output_str += f"{message.proto.name}BaseModel"
            if message != self.root_message_list[-1]:
                output_str += ", "
        for message in self.query_message_list:
            output_str += ", "
            output_str += f"{message.proto.name}BaseModel"
        output_str += "\n"
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
                                                           f"create-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_read_field: f"self.get_{message_name_snake_cased}_client_url: str = "
                                                         "f'http://{self.host}:{self.port}/" +
                                                         f"{self.proto_file_package}/"
                                                         f"get-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_update_field: f"self.put_{message_name_snake_cased}_client_url: str = "
                                                           "f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"put-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_patch_field: f"self.patch_{message_name_snake_cased}_client_url: "
                                                          "str = f'http://{self.host}:{self.port}/" +
                                                          f"{self.proto_file_package}/"
                                                          f"patch-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_delete_field: f"self.delete_{message_name_snake_cased}_client_url: "
                                                           "str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"delete-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_read_websocket_field: f"self.get_{message_name_snake_cased}_"
                                                                   f"client_ws_url: "
                                                                   "str = f'ws://{self.host}:{self.port}/" +
                                                                   f"{self.proto_file_package}/get-"
                                                                   f"{message_name_snake_cased}-ws/'"
        }
        output_str += " " * 8 + "self.get_all_" + f"{message_name_snake_cased}" + \
                      "_client_url: str = f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/get-all-{message_name_snake_cased}/'\n"
        output_str += " " * 8 + "self.get_all_" + f"{message_name_snake_cased}" + \
                      "_client_ws_url: str = f'ws://{self.host}:{self.port}/" \
                      + f"{self.proto_file_package}/get-all-{message_name_snake_cased}-ws/'\n"

        for crud_option_field_name, url in crud_field_name_to_url_dict.items():
            if crud_option_field_name in option_dict:
                output_str += " " * 8 + f"{url}"
                output_str += "\n"
            # else not required: Avoiding method creation if desc not provided in option

        for field in message.fields:
            if self.is_bool_option_enabled(field, BaseFastapiPlugin.flux_fld_index):
                output_str += " " * 8 + f"self.get_{message_name_snake_cased}_from_index_fields_client_url: " \
                                        f"str = f'http://" + "{self.host}:{self.port}/" + \
                              f"{self.proto_file_package}/get-{message_name_snake_cased}-from-index-fields/'\n"
                break
            # else not required: Avoiding field if index option is not enabled

        return output_str

    def _handle_client_query_url(self, message: protogen.Message, message_name_snake_cased: str):
        output_str = ""
        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_json_query)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]
        crud_field_name_to_url_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: f"self.create_{message_name_snake_cased}_query_client"
                                                           "_url: str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"query-create-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_read_field: f"self.get_{message_name_snake_cased}_query_client"
                                                         "_url: str = f'http://{self.host}:{self.port}/" +
                                                         f"{self.proto_file_package}/"
                                                         f"query-get-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_update_field: f"self.put_{message_name_snake_cased}_query_client"
                                                           "_url: str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"query-put-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_patch_field: f"self.patch_{message_name_snake_cased}_query_client"
                                                          "_url: str = f'http://{self.host}:{self.port}/" +
                                                          f"{self.proto_file_package}/"
                                                          f"query-patch-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_delete_field: f"self.delete_{message_name_snake_cased}_query_client"
                                                           "_url: str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"query-delete-{message_name_snake_cased}/'",
            BaseFastapiPlugin.flux_json_root_read_websocket_field: f"self.get_{message_name_snake_cased}_"
                                                                   f"query_client_ws_url: "
                                                                   "str = f'ws://{self.host}:{self.port}/" +
                                                                   f"{self.proto_file_package}/query-get-"
                                                                   f"{message_name_snake_cased}-ws/'"
        }
        for crud_option_field_name, url in crud_field_name_to_url_dict.items():
            if crud_option_field_name in option_dict:
                output_str += " " * 8 + f"{url}"
                output_str += "\n"
            # else not required: Avoiding method creation if desc not provided in option
        return output_str

    def _handle_client_url_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = ""
        if message in self.root_message_list:
            output_str += self._handle_client_routes_url(message, message_name_snake_cased)

        if message in self.query_message_list:
            output_str += self._handle_client_query_url(message, message_name_snake_cased)

        return output_str

    def _handle_client_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        options_list_of_dict = \
            self.get_complex_option_values_as_list_of_dict(message,
                                                           BaseFastapiPlugin.flux_msg_json_query)

        # Since json_root option is of non-repeated type
        option_dict = options_list_of_dict[0]

        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_query_client_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_query_client_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_query_client_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_query_client_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_query_client_gen,
            BaseFastapiPlugin.flux_json_root_read_websocket_field: self.handle_read_by_id_WEBSOCKET_query_client_gen
        }

        for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
            if crud_option_field_name in option_dict:
                output_str += crud_operation_method(message)
                output_str += "\n\n"
            # else not required: Avoiding method creation if desc not provided in option
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

        if message in self.query_message_list:
            output_str += self._handle_client_query_methods(message)

        return output_str

    def handle_client_file_gen(self) -> str:
        output_str = f'from typing import Dict, List, Callable\n'
        generic_web_client_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_web_client")
        output_str += f'from {generic_web_client_path} import generic_http_get_all_client, ' + "\\\n" \
                      f'\tgeneric_http_post_client, generic_http_get_client, generic_http_put_client, ' \
                      f'generic_http_patch_client, generic_http_index_client,' \
                      f'\\\n\tgeneric_http_delete_client, generic_ws_get_client, ' \
                      f'generic_ws_get_all_client\n'
        output_str += self._import_model_in_client_file()
        output_str += "\n\n"
        output_str += f"class {convert_to_capitalized_camel_case(self.client_file_name)}:\n\n"
        output_str += "    def __init__(self, host: str | None = None, port: int | None = None):\n"
        output_str += " "*4 + "    # host and port\n"
        output_str += " "*4 + f'    self.host = "127.0.0.1" if host is None else host\n'
        output_str += " "*4 + f'    self.port = 8000 if port is None else port\n\n'
        output_str += " "*4 + f'    # urls\n'
        for message in self.root_message_list:
            output_str += self._handle_client_url_gen(message)
            output_str += "\n"
        output_str += f'    # interfaces\n'
        for message in self.root_message_list:
            output_str += self.handle_client_methods(message)
        return output_str
