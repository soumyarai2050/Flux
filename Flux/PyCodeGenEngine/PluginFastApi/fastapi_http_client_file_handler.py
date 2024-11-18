# standard imports
import logging
import os
import time
from abc import ABC
from typing import List, Dict

# 3rd party imports
import protogen
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, \
    convert_to_capitalized_camel_case
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import (
    project_dir, root_core_proto_files, project_grp_core_proto_files)


class FastapiHttpClientFileHandler(BaseFastapiPlugin, ABC):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def handle_POST_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = (" "*4 + f"def create_{message_name_snake_cased}_client(self, pydantic_obj: "
                      f"{message_name}BaseModel, return_obj_copy: bool | None = True) -> "
                      f"{message_name}BaseModel | bool:\n")
        output_str += " "*8 + f"return generic_http_post_client(self.create_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel, return_obj_copy)"
        return output_str

    def handle_POST_all_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = (" "*4 + f"def create_all_{message_name_snake_cased}_client(self, pydantic_obj_list: "
                      f"List[{message_name}BaseModel], return_obj_copy: bool | None = True"
                      f") -> List[{message_name}BaseModel] | bool:\n")
        output_str += " "*8 + f"return generic_http_post_all_client(self.create_all_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj_list, {message_name}BaseModel, return_obj_copy)"
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
        output_str = (" "*4 + f"def put_{message_name_snake_cased}_client(self, pydantic_obj: "
                      f"{message_name}BaseModel, return_obj_copy: bool | None = True"
                      f") -> {message_name}BaseModel | bool:\n")
        output_str += " "*4 + f"    return generic_http_put_client(self.put_{message_name_snake_cased}_client_url, " \
                      f"pydantic_obj, {message_name}BaseModel, return_obj_copy)"
        return output_str

    def handle_PUT_all_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = (" "*4 + f"def put_all_{message_name_snake_cased}_client(self, pydantic_obj: "
                      f"List[{message_name}BaseModel], return_obj_copy: bool | None = True"
                      f") -> List[{message_name}BaseModel] | bool:\n")
        output_str += " "*4 + f"    return generic_http_put_all_client(self.put_all_{message_name_snake_cased}_client_url," \
                      f" pydantic_obj, {message_name}BaseModel, return_obj_copy)"
        return output_str

    def handle_PATCH_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_{message_name_snake_cased}_client(self, pydantic_obj_json: " \
                     f"Dict, return_obj_copy: bool | None = True) -> {message_name}BaseModel | bool:\n"
        output_str += " "*4 + f"    return generic_http_patch_client(self.patch_{message_name_snake_cased}" \
                      f"_client_url, pydantic_obj_json, {message_name}BaseModel, return_obj_copy)"
        return output_str

    def handle_PATCH_all_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def patch_all_{message_name_snake_cased}_client(self, pydantic_obj_json_list: " \
                     f"List[Dict], return_obj_copy: bool | None = True) -> List[{message_name}BaseModel] | bool:\n"
        output_str += " "*4 + f"    return generic_http_patch_all_client(self.patch_all_{message_name_snake_cased}" \
                      f"_client_url, pydantic_obj_json_list, {message_name}BaseModel, return_obj_copy)"
        return output_str

    def handle_DELETE_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + f"def delete_{message_name_snake_cased}_client(self, {message_name_snake_cased}_id: " \
                     f"{field_type}, return_obj_copy: bool | None = True) -> Dict | bool:\n"
        output_str += " "*4 + f"    return generic_http_delete_client(self.delete_{message_name_snake_cased}" \
                      f"_client_url, {message_name_snake_cased}_id, return_obj_copy)"
        return output_str

    def handle_DELETE_all_client_gen(self, message: protogen.Message, field_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " "*4 + (f"def delete_all_{message_name_snake_cased}_client(self, "
                              f"return_obj_copy: bool | None = True) -> Dict | bool:\n")
        output_str += " "*4 + f"    return generic_http_delete_all_client(self.delete_all_{message_name_snake_cased}" \
                      f"_client_url, return_obj_copy)"
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
        output_str = " "*4 + (f"def get_all_{message_name_snake_cased}_client(self, limit_obj_count: int | None = None"
                              f") -> List[{message_name}BaseModel]:\n")
        output_str += " "*4 + f"    return generic_http_get_all_client(self.get_all_" \
                      f"{message_name_snake_cased}_client_url, {message_name}BaseModel, limit_obj_count)\n\n"
        return output_str

    def _import_model_in_client_file(self, file: protogen.File | None = None, model_file_suffix: str | None = None) -> str:
        model_file_path = self.import_path_from_os_path("OUTPUT_DIR", f"{self.model_dir_name}.{self.model_file_name}")
        output_str = f"from {model_file_path} import *\n"

        if file is not None and model_file_suffix is not None:
            project_grp_root_dir = PurePath(project_dir).parent.parent / "Pydantic"
            dependency_file_path_list = self.get_dependency_file_path_list(
                file, root_core_proto_files, project_grp_core_proto_files,
                model_file_suffix, str(project_grp_root_dir))

            project_name = file.proto.package
            for dependency_file_path in dependency_file_path_list:
                if f"_n_{project_name}" in dependency_file_path or f"{project_name}_n_" in dependency_file_path:
                    output_str += f'from {dependency_file_path} import *\n'
        output_str += "\n\n"

        return output_str

    def _handle_client_routes_url(self, message: protogen.Message, message_name_snake_cased: str) -> str:
        output_str = ""
        if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
            option_value_dict = self.get_complex_option_value_from_proto(message, FastapiHttpClientFileHandler.flux_msg_json_root)
        else:
            option_value_dict = (
                self.get_complex_option_value_from_proto(message, FastapiHttpClientFileHandler.flux_msg_json_root_time_series))

        crud_field_name_to_url_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: f"self.create_{message_name_snake_cased}_client_url: "
                                                           "str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"create-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_create_all_field: f"self.create_all_{message_name_snake_cased}_client_"
                                                               "url: str = f'http://{self.host}:{self.port}/" +
                                                               f"{self.proto_file_package}/create_all-" +
                                                               f"{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_read_field: f"self.get_{message_name_snake_cased}_client_url: str = "
                                                         "f'http://{self.host}:{self.port}/" +
                                                         f"{self.proto_file_package}/"
                                                         f"get-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_update_field: f"self.put_{message_name_snake_cased}_client_url: str = "
                                                           "f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"put-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_update_all_field: f"self.put_all_{message_name_snake_cased}_client_url: str = "
                                                           "f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"put_all-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_patch_field: f"self.patch_{message_name_snake_cased}_client_url: "
                                                          "str = f'http://{self.host}:{self.port}/" +
                                                          f"{self.proto_file_package}/"
                                                          f"patch-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_patch_all_field: f"self.patch_all_{message_name_snake_cased}_client_url: "
                                                          "str = f'http://{self.host}:{self.port}/" +
                                                          f"{self.proto_file_package}/"
                                                          f"patch_all-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_delete_field: f"self.delete_{message_name_snake_cased}_client_url: "
                                                           "str = f'http://{self.host}:{self.port}/" +
                                                           f"{self.proto_file_package}/"
                                                           f"delete-{message_name_snake_cased}'",
            BaseFastapiPlugin.flux_json_root_delete_all_field: f"self.delete_all_{message_name_snake_cased}_client_url: "
                                                               "str = f'http://{self.host}:{self.port}/" +
                                                               f"{self.proto_file_package}/"
                                                               f"delete_all-{message_name_snake_cased}'"
        }
        output_str += " " * 8 + "self.get_all_" + f"{message_name_snake_cased}" + \
                      "_client_url: str = f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/get-all-{message_name_snake_cased}'\n"

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

        id_field_type: str = self._get_msg_id_field_type(message)
        if id_field_type == "int":
            output_str += " " * 8 + "self.get_" + f"{message_name_snake_cased}_" + \
                          "max_id_client_url: str = f'http://{self.host}:{self.port}/" + \
                          f"{self.proto_file_package}/query-get_{message_name_snake_cased}_max_id'\n"
        return output_str

    def _handle_client_projection_query_url(self, message: protogen.Message) -> str:
        output_str = ""
        if FastapiHttpClientFileHandler.is_option_enabled(message,
                                                          FastapiHttpClientFileHandler.flux_msg_json_root_time_series):
            for field in message.fields:
                if FastapiHttpClientFileHandler.is_option_enabled(
                        field, FastapiHttpClientFileHandler.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            projection_val_to_query_name_dict = (
                FastapiHttpClientFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
            for temp_query_name, query_name in projection_val_to_query_name_dict.items():
                url = f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
                      f"{self.proto_file_package}/" + f"query-{query_name}'"
                output_str += " " * 8 + f"{url}\n"

        return output_str

    def _handle_client_query_url(self, message: protogen.Message):
        output_str = ""

        aggregate_value_list = self.message_to_query_option_list_dict[message]

        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiHttpClientFileHandler.query_name_key]
            query_type = str(aggregate_value[FastapiHttpClientFileHandler.query_type_key]).lower() \
                if aggregate_value[FastapiHttpClientFileHandler.query_type_key] is not None else None

            if query_type is None or query_type == "http" or query_type == "both" or query_type == "http_file":
                output_str += self._get_url_set_str_for_output(query_name)
            # else not required: ws handling is done by ws client plugin

        return output_str

    def _get_url_set_str_for_output(self, query_name: str):
        output_str = ""
        url = f"self.query_{query_name}_url: str = " + "f'http://{self.host}:{self.port}/" + \
              f"{self.proto_file_package}/" + f"query-{query_name}'"
        output_str += " " * 8 + f"{url}\n"

        return output_str

    def _handle_client_url_gen(self, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = ""
        if message in self.root_message_list:
            output_str += self._handle_client_routes_url(message, message_name_snake_cased)
            output_str += self._handle_client_projection_query_url(message)

        if message in self.message_to_query_option_list_dict:
            output_str += self._handle_client_query_url(message)

        query_data_dict_list = self.message_to_button_query_data_dict.get(message)
        if query_data_dict_list is not None:
            for query_data_dict in query_data_dict_list:
                query_data = query_data_dict.get("query_data")
                query_name = query_data.get(FastapiHttpClientFileHandler.flux_json_query_name_field)
                output_str += self._get_url_set_str_for_output(query_name)

        return output_str

    def _handle_client_http_query_output(self, message_name: str, query_name: str, query_params: List[str],
                                         params_str: str, route_type: str | None = None,
                                         is_projection_query: bool | None = None):
        if is_projection_query:
            container_model_name = message_name
        else:
            container_model_name = message_name + "BaseModel"

        if query_params:
            output_str = " " * 4 + f"def {query_name}_query_client(self, {params_str}) -> " \
                                    f"List[{container_model_name}]:\n"
            params_dict_str = \
                ', '.join([f'"{aggregate_param}": {aggregate_param}' for aggregate_param in query_params])
            if route_type is None or route_type == FastapiHttpClientFileHandler.flux_json_query_route_get_type_field_val:
                output_str += " " * 4 + "    query_params_dict = {" + f"{params_dict_str}" + "}\n"
                output_str += " " * 4 + ("    query_params_data = generic_encoder(query_params_dict, "
                                         "exclude_none=True)   # removes none values from dict\n")
                output_str += " " * 4 + f"    return generic_http_get_query_client(self.query_{query_name}_url, " \
                                        f"query_params_data, {container_model_name})\n\n"
            else:
                output_str += " " * 4 + "    query_params_dict = {" + f"{params_dict_str}" + "}\n"
                output_str += " " * 4 + ("    query_params_data = generic_encoder(query_params_dict, "
                                         "exclude_none=True)   # removes none values from dict\n")
                if route_type == FastapiHttpClientFileHandler.flux_json_query_route_patch_type_field_val:
                    output_str += " " * 4 + (f"    return generic_http_patch_query_client(self.query_{query_name}"
                                             f"_url, query_params_data, {container_model_name})\n\n")
                else:
                    output_str += " " * 4 + (f"    return generic_http_post_query_client(self.query_{query_name}"
                                             f"_url, query_params_data, {container_model_name})\n\n")
        else:
            if route_type == FastapiHttpClientFileHandler.flux_json_query_route_patch_type_field_val:
                err_str = f"Patch web client can't be generated without payload parameters, query_name: {query_name} " \
                          f"in message {message_name} has no query_params"
                logging.exception(err_str)
                raise Exception(err_str)
            output_str = " " * 4 + f"def {query_name}_query_client(self) -> " \
                                   f"List[{message_name}]:\n"
            output_str += " " * 4 + f"    return generic_http_get_query_client(self.query_{query_name}_url, " \
                                    "{}, " + f"{container_model_name})\n\n"
        return output_str

    def _handle_client_http_file_query_output(self, message_name: str, query_name: str,
                                              query_params: List[str] | None = None,
                                              params_str: str | None = None):
        container_model_name = message_name + "BaseModel"
        if query_params:
            output_str = " " * 4 + (f"def {query_name}_query_client(self, file_path: str | PurePath, {params_str}) "
                                    f"-> List[{container_model_name}]:\n")
            params_dict_str = \
                ', '.join([f'"{aggregate_param}": {aggregate_param}' for aggregate_param in query_params])
            output_str += " " * 4 + "    query_params_dict = {" + f"{params_dict_str}" + "}\n"
            output_str += " " * 4 + ("    query_params_data = generic_encoder(query_params_dict, "
                                     "exclude_none=True)   # removes none values from dict\n")
            output_str += " " * 4 + f"    return generic_http_file_query_client(self.query_{query_name}_url, " \
                                    f"file_path, query_params_data, {container_model_name})\n\n"
        else:
            output_str = " " * 4 + f"def {query_name}_query_client(self, file_path: str | PurePath) -> " \
                                   f"List[{message_name}]:\n"
            output_str += " " * 4 + f"    return generic_http_file_query_client(self.query_{query_name}_url, " \
                                    "file_path, {}, " + f"{container_model_name})\n\n"
        return output_str

    def _handle_client_query_methods(self, message: protogen.Message) -> str:
        output_str = ""
        aggregate_value_list = self.message_to_query_option_list_dict[message]
        for aggregate_value in aggregate_value_list:
            query_name = aggregate_value[FastapiHttpClientFileHandler.query_name_key]
            query_params = aggregate_value[FastapiHttpClientFileHandler.query_params_key]
            query_type_value = aggregate_value[FastapiHttpClientFileHandler.query_type_key]
            query_type = str(query_type_value).lower() if query_type_value is not None else None
            query_route_type_value = aggregate_value[FastapiHttpClientFileHandler.query_route_type_key]
            query_route_type = str(query_route_type_value) if query_route_type_value is not None else \
                FastapiHttpClientFileHandler.flux_json_query_route_get_type_field_val

            query_params_name_list = []
            if query_params:
                for query_param_name, param_type in query_params:
                    query_params_name_list.append(query_param_name)

            params_str = ", ".join([f"{aggregate_param}: {aggregate_params_type}"
                                    for aggregate_param, aggregate_params_type in query_params])
            message_name = message.proto.name

            if query_type is None or query_type == "http" or query_type == "both":
                output_str += self._handle_client_http_query_output(message_name, query_name, query_params_name_list,
                                                                    params_str, query_route_type)
            elif query_type == "http_file":
                output_str += self._handle_client_http_file_query_output(message_name, query_name, query_params_name_list, params_str)
            # else not required: ws handling is done by ws client plugin
        return output_str

    def _handle_client_button_query_method(self, message: protogen.Message, query_data_dict: Dict) -> str:
        output_str = ""
        message_name = message.proto.name
        query_data = query_data_dict.get("query_data")
        query_name = query_data.get(FastapiHttpClientFileHandler.flux_json_query_name_field)
        query_type_value = query_data.get(FastapiHttpClientFileHandler.flux_json_query_type_field)
        query_type = str(query_type_value).lower() if query_type_value is not None else None
        query_params = query_data.get(FastapiHttpClientFileHandler.flux_json_query_params_field)
        query_route_type_value = query_data.get(FastapiHttpClientFileHandler.flux_json_query_route_type_field)
        query_route_type = str(query_route_type_value) if query_route_type_value is not None else \
            FastapiHttpClientFileHandler.flux_json_query_route_get_type_field_val

        params_str = ""
        query_params_name_list = []
        if query_params:
            query_param_name_n_param_type_list = []
            for query_param in query_params:
                query_param_name = query_param.get(BaseFastapiPlugin.flux_json_query_params_name_field)
                query_param_type = query_param.get(BaseFastapiPlugin.flux_json_query_params_data_type_field)
                query_param_name_n_param_type_list.append((query_param_name, query_param_type))
                query_params_name_list.append(query_param_name)
            params_str = ", ".join([f"{aggregate_param}: {aggregate_params_type}"
                                    for aggregate_param, aggregate_params_type in query_param_name_n_param_type_list])

        if query_type is None or query_type == "http" or query_type == "both":
            output_str += self._handle_client_http_query_output(message_name, query_name, query_params_name_list,
                                                                params_str, query_route_type)
        elif query_type == "http_file":
            file_upload_data = query_data_dict.get(
                FastapiHttpClientFileHandler.button_query_file_upload_options_key)
            disallow_duplicate_file_upload = False
            if file_upload_data:
                disallow_duplicate_file_upload = file_upload_data.get("disallow_duplicate_file_upload")

            query_params_name_list.append("disallow_duplicate_file_upload")

            if params_str:
                if disallow_duplicate_file_upload:
                    params_str += ", disallow_duplicate_file_upload: bool = True"
                else:
                    params_str += ", disallow_duplicate_file_upload: bool = False"
            else:
                if disallow_duplicate_file_upload:
                    params_str = "disallow_duplicate_file_upload: bool = True"
                else:
                    params_str = "disallow_duplicate_file_upload: bool = False"
            output_str += self._handle_client_http_file_query_output(message_name, query_name, query_params_name_list, params_str)
        return output_str

    def _handle_client_projection_query_methods(self, message: protogen.Message):
        output_str = ""
        if FastapiHttpClientFileHandler.is_option_enabled(message,
                                                          FastapiHttpClientFileHandler.flux_msg_json_root_time_series):
            for field in message.fields:
                if FastapiHttpClientFileHandler.is_option_enabled(
                        field, FastapiHttpClientFileHandler.flux_fld_projections):
                    break
            else:
                # If no field is found having projection enabled
                return output_str

            projection_val_to_query_name_dict = (
                FastapiHttpClientFileHandler.get_projection_temp_query_name_to_generated_query_name_dict(message))
            meta_data_field_name_to_field_proto_dict: Dict[str, (protogen.Field | Dict[str, protogen.Field])] = (
                self.get_meta_data_field_name_to_field_proto_dict(message))

            query_params_list = []
            query_params_str = ""
            for meta_field_name, meta_field_value in meta_data_field_name_to_field_proto_dict.items():
                if isinstance(meta_field_value, dict):
                    for nested_meta_field_name, nested_meta_field in meta_field_value.items():
                        query_params_list.append(nested_meta_field_name)
                        query_params_str += (f"{nested_meta_field_name}: "
                                             f"{self.proto_to_py_datatype(nested_meta_field)}, ")
                else:
                    query_params_list.append(meta_field_name)
                    query_params_str += f"{meta_field_name}: {self.proto_to_py_datatype(meta_field_value)}, "
            query_params_list += ["start_date_time", "end_date_time"]
            query_params_str += "start_date_time: DateTime | None = None, end_date_time: DateTime | None = None"
            for temp_query_name, query_name in projection_val_to_query_name_dict.items():
                projection_val_to_fields_dict = (
                    FastapiHttpClientFileHandler.get_projection_option_value_to_fields(message))

                field_name_list: List[str] = []
                field_name_set = projection_val_to_fields_dict[temp_query_name]
                for field_name in field_name_set:
                    if "." in field_name:
                        field_name_list.append("_".join(field_name.split(".")))
                    else:
                        field_name_list.append(field_name)
                field_names_str = "_n_".join(field_name_list)
                field_names_str_camel_cased = convert_to_capitalized_camel_case(field_names_str)

                container_model_name = f"{message.proto.name}ProjectionContainerFor{field_names_str_camel_cased}"
                # http query
                output_str += self._handle_client_http_query_output(container_model_name, query_name, query_params_list,
                                                                    query_params_str, is_projection_query=True)

        return output_str

    def _handle_get_max_id_client_generation(self, message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = " " * 4 + f"def get_{message_name_snake_cased}_max_id_client(self) -> MaxId:\n"
        output_str += " " * 4 + f"    return generic_http_get_client(self.get_" \
                                f"{message_name_snake_cased}_max_id_client_url, None, MaxId)\n\n"
        return output_str

    def _handle_client_route_methods(self, message: protogen.Message) -> str:
        output_str = ""
        if self.is_option_enabled(message, BaseFastapiPlugin.flux_msg_json_root):
            option_value_dict = self.get_complex_option_value_from_proto(message, FastapiHttpClientFileHandler.flux_msg_json_root)
        else:
            option_value_dict = (
                self.get_complex_option_value_from_proto(message, FastapiHttpClientFileHandler.flux_msg_json_root_time_series))

        crud_field_name_to_method_call_dict = {
            BaseFastapiPlugin.flux_json_root_create_field: self.handle_POST_client_gen,
            BaseFastapiPlugin.flux_json_root_create_all_field: self.handle_POST_all_client_gen,
            BaseFastapiPlugin.flux_json_root_read_field: self.handle_GET_client_gen,
            BaseFastapiPlugin.flux_json_root_update_field: self.handle_PUT_client_gen,
            BaseFastapiPlugin.flux_json_root_update_all_field: self.handle_PUT_all_client_gen,
            BaseFastapiPlugin.flux_json_root_patch_field: self.handle_PATCH_client_gen,
            BaseFastapiPlugin.flux_json_root_patch_all_field: self.handle_PATCH_all_client_gen,
            BaseFastapiPlugin.flux_json_root_delete_field: self.handle_DELETE_client_gen,
            BaseFastapiPlugin.flux_json_root_delete_all_field: self.handle_DELETE_all_client_gen
        }

        output_str += self.handle_get_all_message_http_client(message)

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

        if id_field_type == "int":
            output_str += self._handle_get_max_id_client_generation(message)

        return output_str

    def handle_client_methods(self, message: protogen.Message) -> str:
        output_str = ""
        if message in self.root_message_list:
            output_str += self._handle_client_route_methods(message)

        if message in self.message_to_query_option_list_dict:
            output_str += self._handle_client_query_methods(message)

        query_data_dict_list = self.message_to_button_query_data_dict.get(message)
        if query_data_dict_list is not None:
            for query_data_dict in query_data_dict_list:
                output_str += self._handle_client_button_query_method(message, query_data_dict)

        return output_str

    def handle_client_file_gen(self, file: protogen.File, model_file_suffix: str) -> str:
        if self.is_option_enabled(file, FastapiHttpClientFileHandler.flux_file_crud_host):
            host = self.get_simple_option_value_from_proto(file, FastapiHttpClientFileHandler.flux_file_crud_host)
        else:
            host = '"127.0.0.1"'

        if self.is_option_enabled(file, FastapiHttpClientFileHandler.flux_file_crud_port_offset):
            port_offset = \
                self.get_simple_option_value_from_proto(file,
                                                        FastapiHttpClientFileHandler.flux_file_crud_port_offset)
            port = 8000 + parse_to_int(port_offset)
        else:
            port = 8000

        output_str = f'# standard imports\n'
        output_str += f'from typing import Dict, List, Callable, Any\n'
        output_str += f'from fastapi import UploadFile\n'
        output_str += f'import threading\n\n'
        output_str += f'# 3rd party imports\n\n'
        output_str += f'# project imports\n'
        generic_web_client_path = self.import_path_from_os_path("PY_CODE_GEN_CORE_PATH", "generic_web_client")
        output_str += f'from {generic_web_client_path} import *\n'
        output_str += self._import_model_in_client_file(file, model_file_suffix)
        output_str += "\n\n"
        class_name = convert_to_capitalized_camel_case(self.client_file_name)
        output_str += f"class {class_name}:\n"
        output_str += f"    get_instance_mutex: threading.Lock = threading.Lock()\n"
        output_str += f"    host_port_key_to_instance_dict: Dict[str, '{class_name}'] = "+"{}\n\n"
        output_str += f"    @classmethod\n"
        output_str += f"    def set_or_get_if_instance_exists(cls, host: str | None = None, port: int | None = None):\n"
        output_str += f"        with cls.get_instance_mutex:\n"
        output_str += f'            host = {host} if host is None else host\n'
        output_str += f'            port = {port} if port is None else port\n'
        output_str += '            key = f"{host}_{port}"\n'
        output_str += '            if key in cls.host_port_key_to_instance_dict:\n'
        output_str += '                return cls.host_port_key_to_instance_dict.get(key)\n'
        output_str += '            else:\n'
        output_str += f'                cls.host_port_key_to_instance_dict[key] = {class_name}(host, port)\n'
        output_str += '                return cls.host_port_key_to_instance_dict[key]\n\n'
        output_str += "    def __init__(self, host: str, port: int):\n"
        output_str += " "*4 + "    # host and port\n"
        output_str += " "*4 + f'    self.host = host\n'
        output_str += " "*4 + f'    self.port = port\n\n'
        output_str += " "*4 + f'    # urls\n'
        for message in set(self.root_message_list+list(self.message_to_query_option_list_dict)):
            output_str += self._handle_client_url_gen(message)
            output_str += "\n"
        output_str += f'    # interfaces\n'
        for message in self.root_message_list:
            output_str += self.handle_client_methods(message)
            output_str += self._handle_client_projection_query_methods(message)

        for message in list(self.message_to_query_option_list_dict):
            if message not in self.root_message_list:
                output_str += self.handle_client_methods(message)
            # else not required: root lvl message with query already executed in last loop

        return output_str
