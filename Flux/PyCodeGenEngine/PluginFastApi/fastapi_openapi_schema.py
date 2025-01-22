# standard imports
from abc import ABC
from typing import List, Dict, Tuple
import logging

import protogen

# project imports
from Flux.PyCodeGenEngine.PluginFastApi.base_fastapi_plugin import BaseFastapiPlugin
from FluxPythonUtils.scripts.utility_functions import (convert_camel_case_to_specific_case,
                                                       convert_to_capitalized_camel_case)


class FastapiOpenapiSchema(BaseFastapiPlugin, ABC):
    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.cache_schema_message_name_to_res_type_list_dict: Dict[str, List[str]] = {}
        self.message_schema_cache_list: List[protogen.Message] = []
        
    def _get_schema_type_from_field(self, field: protogen.Field) -> str:
        match field.kind.name.lower():
            case "int32" | "int64":
                return f"integer"
            case "string" | "enum":
                return f'string'
            case "float":
                return f'number'
            case "bool":
                return f"boolean"

    def _get_openapi_schema_for_field(self, field: protogen.Field, indent_count: int) -> str:
        output_str = " "*indent_count + f'"type": "{self._get_schema_type_from_field(field)}"'
        if self.is_option_enabled(field, FastapiOpenapiSchema.flux_fld_help):
            output_str += ',\n'
            help_str = FastapiOpenapiSchema.get_simple_option_value_from_proto(field, FastapiOpenapiSchema.flux_fld_help)
            output_str += " "*indent_count + f'"description": "{help_str}"'
        # else not required: no format required if field is standard string

        if field.enum is not None:
            output_str += ',\n'
            output_str += (" " * indent_count + f'"enum": {[enum_.proto.name for enum_ in field.enum.values]}')
        return output_str

    def _get_openapi_schema_for_message(self, message: protogen.Message, indent_count: int | None = None) -> str:
        if indent_count is None:
            indent_count = 4
        output_str = " " * indent_count + f'"type": "object",\n'
        output_str += " " * indent_count + '"properties": {\n'
        indent_count += 4
        for field in message.fields:
            if field.proto.name == "id":
                output_str += " " * indent_count + f'"_{field.proto.name}": ' + "{\n"
            else:
                output_str += " " * indent_count + f'"{field.proto.name}": ' + "{\n"

            if field.message is not None:
                output_str += self._get_openapi_schema_for_message(field.message, indent_count + 4)
            else:
                output_str += self._get_openapi_schema_for_field(field, indent_count + 4)
            output_str += "\n"
            if field != message.fields[-1]:
                output_str += " " * indent_count + "},\n"
            else:
                output_str += " " * indent_count + "}\n"
        indent_count -= 4
        output_str += " " * indent_count + "}\n"

        return output_str

    def handle_status_404_response(self, indent_count: int = 0) -> str:
        output_str = " "*indent_count + '    "404": {\n'
        output_str += " "*indent_count + '        "description": "Something went wrong",\n'
        output_str += " "*indent_count + '        "content": {\n'
        output_str += " "*indent_count + '            "application/json": {\n'
        output_str += " "*indent_count + '                "schema": {\n'
        output_str += " "*indent_count + '                    "type": "object",\n'
        output_str += " "*indent_count + '                    "properties": {\n'
        output_str += " "*indent_count + '                        "detail": {"type": "string"}\n'
        output_str += " "*indent_count + '                    }\n'
        output_str += " "*indent_count + '                }\n'
        output_str += " "*indent_count + '            }\n'
        output_str += " "*indent_count + '        }\n'
        output_str += " "*indent_count + '    }\n'
        return output_str

    def _handle_get_response(self, message_name_snake_cased: str) -> str:
        cache_response_type_list = self.cache_schema_message_name_to_res_type_list_dict.get(message_name_snake_cased)
        output_str = ""
        if "get_response" not in cache_response_type_list:
            output_str += f"{message_name_snake_cased}_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "found",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += f'                "schema": {message_name_snake_cased}_schema\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    },\n'
            output_str += self.handle_status_404_response()
            output_str += '}\n\n'
            cache_response_type_list.append("get_response")
        # else not required: avoiding duplicate response
        return output_str

    def _handle_get_all_response(self, message_name_snake_cased: str) -> str:
        cache_response_type_list = self.cache_schema_message_name_to_res_type_list_dict.get(message_name_snake_cased)
        output_str = ""
        if "get_all_response" not in cache_response_type_list:
            # get-all request response
            output_str += f"{message_name_snake_cased}_list_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "found-all",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "array",\n'
            output_str += f'                    "items": {message_name_snake_cased}_schema\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    }\n'
            output_str += '}\n\n'
            cache_response_type_list.append("get_all_response")
        # else not required: avoiding duplicate response
        return output_str

    def _handle_create_all_response(self, message_name_snake_cased: str) -> str:
        cache_response_type_list = self.cache_schema_message_name_to_res_type_list_dict.get(message_name_snake_cased)
        output_str = ""
        if "create_all_response" not in cache_response_type_list:
            output_str += f"{message_name_snake_cased}_create_list_response = " + "{\n"
            output_str += '    "201": {\n'
            output_str += '        "description": "Created List",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "array",\n'
            output_str += f'                    "items": {message_name_snake_cased}_schema\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    }\n'
            output_str += '}\n\n'
            cache_response_type_list.append("create_all_response")
        # else not required: avoiding duplicate response
        return output_str

    def _handle_update_all_response(self, message_name_snake_cased: str) -> str:
        cache_response_type_list = self.cache_schema_message_name_to_res_type_list_dict.get(message_name_snake_cased)
        output_str = ""
        if "update_all_response" not in cache_response_type_list:
            output_str += f"{message_name_snake_cased}_update_list_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "Updated List",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "array",\n'
            output_str += f'                    "items": {message_name_snake_cased}_schema\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    },\n'
            output_str += self.handle_status_404_response()
            output_str += '}\n\n'
            cache_response_type_list.append("update_all_response")
        # else not required: avoiding duplicate response
        return output_str

    def _handle_msg_schema(self, message: protogen.Message, message_name_snake_cased: str) -> str:
        output_str = ""
        if message_name_snake_cased not in self.cache_schema_message_name_to_res_type_list_dict:
            output_str = f"{message_name_snake_cased}_schema = " + "{\n"
            output_str += self._get_openapi_schema_for_message(message)
            output_str += "}\n\n"
            output_str += f"{message_name_snake_cased}_list_schema = " + "{\n"
            output_str += f'    "type": "array",\n'
            output_str += f'    "items": {message_name_snake_cased}_schema\n'
            output_str += "}\n\n"
            self.cache_schema_message_name_to_res_type_list_dict[message_name_snake_cased] = []
            self.message_schema_cache_list.append(message)
        # else not required: avoiding duplicate schema
        return output_str

    def _get_root_msg_openapi_schemas_str(
            self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        # handling schema
        output_str = ""
        output_str += self._handle_msg_schema(message, message_name_snake_cased)

        # handling response
        if self.is_option_enabled(message, FastapiOpenapiSchema.flux_msg_json_root):
            option_val_dict = self.get_complex_option_value_from_proto(message, FastapiOpenapiSchema.flux_msg_json_root)
        else:
            option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                       FastapiOpenapiSchema.flux_msg_json_root_time_series)

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_read_field) is not None:
            # get and get-all request response
            output_str += self._handle_get_response(message_name_snake_cased)
            output_str += self._handle_get_all_response(message_name_snake_cased)

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_create_field) is not None:
            # create request response
            output_str += f"{message_name_snake_cased}_create_response = " + "{\n"
            output_str += '    "201": {\n'
            output_str += '        "description": "Created",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += f'                "schema": {message_name_snake_cased}_schema\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    },\n'
            output_str += self.handle_status_404_response()
            output_str += '}\n\n'

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_create_all_field) is not None:
            # create-all request response
            output_str += self._handle_create_all_response(message_name_snake_cased)

        if (option_val_dict.get(FastapiOpenapiSchema.flux_json_root_update_all_field) is not None or
                option_val_dict.get(FastapiOpenapiSchema.flux_json_root_patch_all_field) is not None):
            # update-all request response
            output_str += self._handle_update_all_response(message_name_snake_cased)

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_delete_field) is not None:
            # delete request response
            output_str += f"{message_name_snake_cased}_delete_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "Deleted",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "object",\n'
            output_str += '                    "properties": {\n'
            output_str += '                        "id": {\n'
            output_str += '                            "type": "integer"\n'
            output_str += '                        },\n'
            output_str += '                        "msg": {\n'
            output_str += '                            "type": "string"\n'
            output_str += '                        }\n'
            output_str += '                    }\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    },\n'
            output_str += self.handle_status_404_response()
            output_str += '}\n\n'

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_delete_all_field) is not None:
            # delete-all request response
            output_str += f"{message_name_snake_cased}_delete_list_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "Deleted all",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "object",\n'
            output_str += '                    "properties": {\n'
            output_str += '                        "id": {\n'
            output_str += '                            "type": "array",\n'
            output_str += '                            "items": {\n'
            output_str += '                                "type": "integer"\n'
            output_str += '                            }\n'
            output_str += '                        },\n'
            output_str += '                        "msg": {\n'
            output_str += '                            "type": "string"\n'
            output_str += '                        }\n'
            output_str += '                    }\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    }\n'
            output_str += '}\n\n'

        if option_val_dict.get(FastapiOpenapiSchema.flux_json_root_delete_by_id_list_field) is not None:
            # delete-all request response
            output_str += f"{message_name_snake_cased}_delete_by_id_list_response = " + "{\n"
            output_str += '    "200": {\n'
            output_str += '        "description": "Deleted all",\n'
            output_str += '        "content": {\n'
            output_str += '            "application/json": {\n'
            output_str += '                "schema": {\n'
            output_str += '                    "type": "object",\n'
            output_str += '                    "properties": {\n'
            output_str += '                        "id": {\n'
            output_str += '                            "type": "array",\n'
            output_str += '                            "items": {\n'
            output_str += '                                "type": "integer"\n'
            output_str += '                            }\n'
            output_str += '                        },\n'
            output_str += '                        "msg": {\n'
            output_str += '                            "type": "string"\n'
            output_str += '                        }\n'
            output_str += '                    }\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }\n'
            output_str += '    },\n'
            output_str += self.handle_status_404_response()
            output_str += '}\n\n'

        return output_str

    def _get_query_msg_openapi_schemas_str(
            self, message: protogen.Message, query_route_type: str | None = None) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        output_str = ''
        # handling query msg schema
        output_str += self._handle_msg_schema(message, message_name_snake_cased)

        # handling query msg response
        if (query_route_type is None or
                query_route_type == FastapiOpenapiSchema.flux_json_query_route_get_type_field_val):
            output_str += self._handle_get_response(message_name_snake_cased)
            output_str += self._handle_get_all_response(message_name_snake_cased)
        elif query_route_type == FastapiOpenapiSchema.flux_json_query_route_patch_type_field_val:
            output_str += self._handle_get_response(message_name_snake_cased)
            output_str += self._handle_update_all_response(message_name_snake_cased)
        elif query_route_type == FastapiOpenapiSchema.flux_json_query_route_post_type_field_val:
            output_str += self._handle_get_response(message_name_snake_cased)
            output_str += self._handle_create_all_response(message_name_snake_cased)
        return output_str

    def _return_obj_copy_paramter_req_body(self) -> str:
        output_str = '                "parameters": [\n'
        output_str += '                    {\n'
        output_str += '                        "name": "return_obj_copy",\n'
        output_str += '                        "in": "path",\n'
        output_str += '                        "required": False,\n'
        output_str += '                        "schema": {\n'
        output_str += '                            "type": "boolean",\n'
        output_str += '                            "default": True,\n'
        output_str += '                        },\n'
        output_str += ('                        "description": "response will be object after operation if true else '
                       'will be success bool"\n')
        output_str += '                    }\n'
        output_str += '                ],\n'
        return output_str

    def _obj_id_paramter_req_body(self, message_name_snake_cased: str) -> str:
        output_str = '                "parameters": [\n'
        output_str += '                    {\n'
        output_str += f'                        "name": "{message_name_snake_cased}_id",\n'
        output_str += '                        "in": "path",\n'
        output_str += '                        "required": True,\n'
        output_str += '                        "schema": {\n'
        output_str += '                            "type": "integer",\n'
        output_str += '                        },\n'
        output_str += f'                        "description": "ID of {message_name_snake_cased} obj"\n'
        output_str += '                    }\n'
        output_str += '                ],\n'
        return output_str

    def _get_query_param_schema(self, option_type_value: str) -> str:
        # option_type_value is python type passed by user in model option
        # since this is get query schema only simple types are supported, e.g., str, bool | None,
        # int | None = None, List[float]

        is_repeated: bool = False
        if "List" in option_type_value:
            option_type_value = option_type_value.replace("List[", "")
            option_type_value = option_type_value.replace("]", "")
            is_repeated = True
        # cleaning None from type
        option_type_value = option_type_value.replace(" ", "")

        eq_idx = option_type_value.find("=")
        default_val = None
        if eq_idx != -1:
            default_val = option_type_value[eq_idx + 1:]
            option_type_value = option_type_value[:eq_idx]  # removing any value from '=' till end

        option_type_value = option_type_value.replace("|None", "")

        match option_type_value:
            case "int":
                schema_type = "integer"
            case "float":
                schema_type = "number"
            case "bool":
                schema_type = "boolean"
            case other:     # handling enums also as str
                schema_type = "string"

        output_str = '                        "schema": {\n'
        if is_repeated:
            output_str += '                            "type": "array",\n'
            output_str += '                            "items": {\n'
            output_str += f'                                "type": "{schema_type}"\n'
            output_str += '                            },\n'
        else:
            output_str += f'                            "type": "{schema_type}",\n'
        output_str += '                        }'
        if default_val:
            output_str += f',\n'
            output_str += f'                        "default": {default_val}'
        output_str += f'\n'
        return output_str

    def _handle_query_parameter_req_body(self, query_params_name_n_param_type_tuple_list: List[Tuple[str, str]]) -> str:
        output_str = '                "parameters": [\n'
        for query_param_name_n_param_type in query_params_name_n_param_type_tuple_list:
            query_param_name, param_type = query_param_name_n_param_type
            output_str += '                    {\n'
            output_str += f'                        "name": "{query_param_name}",\n'
            output_str += '                        "in": "query",\n'
            if 'None' in param_type:
                output_str += '                        "required": False,\n'
            else:
                output_str += '                        "required": True,\n'
            output_str += self._get_query_param_schema(param_type)

            if query_param_name_n_param_type != query_params_name_n_param_type_tuple_list[-1]:
                output_str += '                    },\n'
            else:
                output_str += '                    }\n'
        output_str += '                ],\n'
        return output_str

    def handle_POST_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/create-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "post": {\n'
        output_str += f'                "summary": "POST api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_create_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_POST_all_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/create-all-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "post": {\n'
        output_str += f'                "summary": "POST-ALL api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_list_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_create_list_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_PUT_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/put-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "put": {\n'
        output_str += f'                "summary": "PUT api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_PUT_all_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/put-all-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "put": {\n'
        output_str += f'                "summary": "PUT-ALL api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_list_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_update_list_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_PATCH_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/patch-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "patch": {\n'
        output_str += f'                "summary": "PATCH api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_PATCH_all_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/patch-all-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "patch": {\n'
        output_str += f'                "summary": "PATCH-ALL api for {message_name}",\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": {message_name_snake_cased}_list_schema\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._return_obj_copy_paramter_req_body()
        output_str += f'                "responses": {message_name_snake_cased}_update_list_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_GET_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/get-{message_name_snake_cased}/'+'{' + f'{message_name_snake_cased}_id' + '}": ' + '{\n'
        output_str += '            "get": {\n'
        output_str += f'                "summary": "GET api for {message_name}",\n'
        output_str += f'                "responses": {message_name_snake_cased}_response,\n'
        output_str += self._obj_id_paramter_req_body(message_name_snake_cased)
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_GET_all_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/get-all-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "get": {\n'
        output_str += f'                "summary": "GET-ALL api for {message_name}",\n'
        output_str += f'                "responses": {message_name_snake_cased}_list_response,\n'
        output_str += f'                "parameters": [\n'
        output_str += '                    {\n'
        output_str += '                        "name": "limit_obj_count",\n'
        output_str += '                        "in": "query",\n'
        output_str += '                        "required": False,\n'
        output_str += '                        "schema": {\n'
        output_str += '                            "type": "integer"\n'
        output_str += '                        },\n'
        output_str += '                        "description": "int value to limit response list length"\n'
        output_str += '                    }\n'
        output_str += f'                ]\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_DELETE_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/delete-{message_name_snake_cased}/'+'{' + f'{message_name_snake_cased}_id' + '}": ' + '{\n'
        output_str += '            "delete": {\n'
        output_str += f'                "summary": "DELETE api for {message_name}",\n'
        output_str += f'                "responses": {message_name_snake_cased}_delete_response,\n'
        output_str += self._obj_id_paramter_req_body(message_name_snake_cased)
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_DELETE_by_id_list_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/delete-by-id-list-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "delete": {\n'
        output_str += f'                "summary": "DELETE by id list api for {message_name}",\n'
        output_str += f'                "responses": {message_name_snake_cased}_delete_by_id_list_response,\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "application/json": {\n'
        output_str += f'                            "schema": '+'{\n'
        output_str += '                                "type": "array",\n'
        output_str += '                                "items": {\n'
        output_str += f'                                    "type": "integer"\n'
        output_str += '                                },\n'
        output_str += '                            },\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                }\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_DELETE_all_req_body(self, message: protogen.Message) -> str:
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/delete-all-{message_name_snake_cased}": ' + '{\n'
        output_str += '            "delete": {\n'
        output_str += f'                "summary": "DELETE-ALL api for {message_name}",\n'
        output_str += f'                "responses": {message_name_snake_cased}_delete_list_response\n'
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_query_req_body(self, message: protogen.Message, query_name: str,
                              query_params_name_n_param_type_tuple_list: List[Tuple[str, str]],
                              query_route_type: str | None = None):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        if (query_route_type is None or
                query_route_type == FastapiOpenapiSchema.flux_json_query_route_get_type_field_val):
            output_str = f'        "/{self.proto_file_package}/query-{query_name}": ' + '{\n'
            output_str += '            "get": {\n'
            output_str += f'                "summary": "Get query api for {query_name} query",\n'
            output_str += f'                "responses": {message_name_snake_cased}_list_response,\n'
            output_str += self._handle_query_parameter_req_body(query_params_name_n_param_type_tuple_list)
            output_str += '            }\n'
            output_str += '        }'
            return output_str
        elif query_route_type in [FastapiOpenapiSchema.flux_json_query_route_patch_type_field_val,
                            FastapiOpenapiSchema.flux_json_query_route_post_type_field_val]:
            output_str = f'        "/{self.proto_file_package}/query-{query_name}": ' + '{\n'
            output_str += f'            "{query_route_type.lower()}": '+'{\n'
            output_str += f'                "summary": "{query_route_type} query api for {query_name} query",\n'
            if query_route_type == FastapiOpenapiSchema.flux_json_query_route_post_type_field_val:
                output_str += f'                "responses": {message_name_snake_cased}_create_list_response,\n'
            else:
                output_str += f'                "responses": {message_name_snake_cased}_update_list_response,\n'
            output_str += '                "requestBody": {\n'
            output_str += '                    "content": {\n'
            output_str += '                        "application/json": {\n'
            output_str += '                            "schema": {"type": "object"}\n'
            output_str += '                        }\n'
            output_str += '                    },\n'
            output_str += '                    "required": True\n'
            output_str += '                }\n'
            output_str += '            }\n'
            output_str += '        }'
            return output_str
        else:
            err_str = f"Unexpected routes_type: {query_route_type}, type {type(query_route_type)}"
            logging.exception(err_str)
            raise Exception(err_str)

    def handle_file_query_req_body(self, message: protogen.Message, query_name: str,
                                   query_params_name_n_param_type_tuple_list: List[Tuple[str, str]]):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        output_str = f'        "/{self.proto_file_package}/query-{query_name}": ' + '{\n'
        output_str += '            "post": {\n'
        output_str += f'                "summary": "File upload query api for {query_name} query",\n'
        output_str += f'                "responses": {message_name_snake_cased}_create_list_response,\n'
        output_str += '                "requestBody": {\n'
        output_str += '                    "content": {\n'
        output_str += '                        "multipart/form-data": {\n'
        output_str += '                            "schema": {\n'
        output_str += '                                "type": "object",\n'
        output_str += '                                "properties": {\n'
        output_str += '                                    "upload_file": {\n'
        output_str += '                                        "type": "string",\n'
        output_str += '                                        "format": "binary",\n'
        output_str += '                                        "description": "File to upload",\n'
        output_str += '                                    }\n'
        output_str += '                                }\n'
        output_str += '                            }\n'
        output_str += '                        }\n'
        output_str += '                    },\n'
        output_str += '                    "required": True\n'
        output_str += '                },\n'
        output_str += self._handle_query_parameter_req_body(query_params_name_n_param_type_tuple_list)
        output_str += '            }\n'
        output_str += '        }'
        return output_str

    def handle_button_query_req_body(self, message: protogen.Message, query_data_dict: Dict):
        query_data = query_data_dict.get("query_data")
        query_name = query_data.get(FastapiOpenapiSchema.flux_json_query_name_field)
        query_type_value = query_data.get(FastapiOpenapiSchema.flux_json_query_type_field)
        query_type = str(query_type_value).lower() if query_type_value is not None else None
        query_params = query_data.get(FastapiOpenapiSchema.flux_json_query_params_field)

        query_param_name_n_param_type_list = []
        if query_params:
            for query_param in query_params:
                query_param_name = query_param.get(FastapiOpenapiSchema.flux_json_query_params_name_field)
                query_param_type = query_param.get(FastapiOpenapiSchema.flux_json_query_params_data_type_field)
                query_param_name_n_param_type_list.append((query_param_name, query_param_type))

        output_str = ""
        if query_type is None or query_type == "http" or query_type == "both":
            query_route_value = query_data.get(FastapiOpenapiSchema.flux_json_query_route_type_field)
            query_route_type = query_route_value if query_route_value is not None else None

            output_str += self.handle_query_req_body(message, query_name,
                                                     query_param_name_n_param_type_list,
                                                     query_route_type)
            output_str += ",\n"
        elif query_type == "http_file":
            file_upload_data = query_data_dict.get(
                FastapiOpenapiSchema.button_query_file_upload_options_key)
            disallow_duplicate_file_upload = False
            if file_upload_data:
                disallow_duplicate_file_upload = file_upload_data.get("disallow_duplicate_file_upload")
            if disallow_duplicate_file_upload:
                query_param_name_n_param_type_list.append(("disallow_duplicate_file_upload", "bool = True"))
            else:
                query_param_name_n_param_type_list.append(("disallow_duplicate_file_upload", "bool = False"))

            output_str += self.handle_file_query_req_body(message, query_name,
                                                          query_param_name_n_param_type_list)
            output_str += ",\n"
        return output_str

    def handle_projection_query_req_body(self, message):
        output_str = ""
        for field in message.fields:
            if FastapiOpenapiSchema.is_option_enabled(field, FastapiOpenapiSchema.flux_fld_projections):
                break
        else:
            # If no field is found having projection enabled
            return output_str

        meta_data_field_name_to_field_proto_dict: Dict[str, (protogen.Field | Dict[str, protogen.Field])] = (
            self.get_meta_data_field_name_to_field_proto_dict(message))
        projection_val_to_query_name_dict = (
            FastapiOpenapiSchema.get_projection_temp_query_name_to_generated_query_name_dict(message))
        for projection_option_val, query_name in projection_val_to_query_name_dict.items():
            query_params_name_n_param_type_tuple_list: List[Tuple[str, str]] = []
            for meta_field_name, meta_field_value in meta_data_field_name_to_field_proto_dict.items():
                if isinstance(meta_field_value, dict):
                    for nested_meta_field_name, nested_meta_field in meta_field_value.items():
                        query_params_name_n_param_type_tuple_list.append((nested_meta_field_name,
                                                                          self.proto_to_py_datatype(nested_meta_field)))
                else:
                    query_params_name_n_param_type_tuple_list.append((meta_field_name,
                                                                      self.proto_to_py_datatype(meta_field_value)))
            query_params_name_n_param_type_tuple_list.append(("start_date_time", "int | None = None"))
            query_params_name_n_param_type_tuple_list.append(("end_date_time", "int | None = None"))

            # Http Filter Call
            output_str += f'        "/{self.proto_file_package}/query-{query_name}": ' + '{\n'
            output_str += '            "get": {\n'
            output_str += f'                "summary": "Get projection query api for {query_name} query",\n'
            output_str += '                "responses": {\n'
            output_str += '                    "200": {\n'
            output_str += '                        "description": "found",\n'
            output_str += '                        "content": {\n'
            output_str += '                            "application/json": {\n'
            output_str += '                                "schema": {"type": "object"}\n'
            output_str += '                            }\n'
            output_str += '                        }\n'
            output_str += '                    },\n'
            output_str += self.handle_status_404_response(indent_count=16)
            output_str += '                },\n'
            output_str += self._handle_query_parameter_req_body(query_params_name_n_param_type_tuple_list)
            output_str += '            }\n'
            output_str += '        },\n'
        return output_str

    def handle_openapi_schema_gen(self, file: protogen.File) -> str:
        output_str = ""
        for message in self.root_message_list:
            output_str += self._get_root_msg_openapi_schemas_str(message)
        for message in self.message_to_query_option_list_dict:
            aggregate_value_list = self.message_to_query_option_list_dict[message]

            # query takes query_params and returns list of message as response so just creating single list type
            # response to be used in multiple queries of same message
            for aggregate_value in aggregate_value_list:
                query_type_value = aggregate_value[FastapiOpenapiSchema.query_type_key]
                query_type = str(query_type_value).lower() if query_type_value is not None else None

                # If any of the query require schema for this message - that is enough for all queries
                if query_type is None or query_type == "http" or query_type == "both" or query_type == "http_file":
                    query_route_value = aggregate_value[FastapiOpenapiSchema.query_route_type_key]
                    query_route_type = query_route_value if query_route_value is not None else None
                    if query_type == "http_file":   # http_file query type is POST type query
                        query_route_type = FastapiOpenapiSchema.flux_json_query_route_post_type_field_val
                    output_str += self._get_query_msg_openapi_schemas_str(message, query_route_type)
                    break

        # ui button query schema and response handling
        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                query_data = query_data_dict.get("query_data")
                query_type_value = query_data.get(FastapiOpenapiSchema.flux_json_query_type_field)
                query_route_value = query_data.get(FastapiOpenapiSchema.flux_json_query_route_type_field)
                query_route_type = query_route_value if query_route_value is not None else None
                query_type = str(query_type_value).lower() if query_type_value is not None else None
                if query_type == "http_file":   # http_file query type is POST type query
                    query_route_type = FastapiOpenapiSchema.flux_json_query_route_post_type_field_val
                output_str += self._get_query_msg_openapi_schemas_str(message, query_route_type)

        output_str += "# openapi schema\n"
        output_str += "openapi_schema = {\n"
        output_str += '    "openapi": "3.0.2",\n'
        output_str += '    "info": {\n'
        output_str += f'        "title": "{file.proto.package} API Docs",\n'
        output_str += f'        "version": "1.0.0",\n'
        output_str += f'            "description": "CRUD API(s) for {file.proto.package}"\n'
        output_str += '    },\n'
        output_str += '    "paths": {\n'

        crud_field_name_to_method_call_dict = {
            FastapiOpenapiSchema.flux_json_root_read_field: self.handle_GET_req_body,
            FastapiOpenapiSchema.flux_json_root_create_field: self.handle_POST_req_body,
            FastapiOpenapiSchema.flux_json_root_create_all_field: self.handle_POST_all_req_body,
            FastapiOpenapiSchema.flux_json_root_update_field: self.handle_PUT_req_body,
            FastapiOpenapiSchema.flux_json_root_update_all_field: self.handle_PUT_all_req_body,
            FastapiOpenapiSchema.flux_json_root_patch_field: self.handle_PATCH_req_body,
            FastapiOpenapiSchema.flux_json_root_patch_all_field: self.handle_PATCH_all_req_body,
            FastapiOpenapiSchema.flux_json_root_delete_field: self.handle_DELETE_req_body,
            FastapiOpenapiSchema.flux_json_root_delete_by_id_list_field: self.handle_DELETE_by_id_list_req_body,
            FastapiOpenapiSchema.flux_json_root_delete_all_field: self.handle_DELETE_all_req_body
        }

        for message in self.root_message_list:
            if self.is_option_enabled(message, FastapiOpenapiSchema.flux_msg_json_root):
                option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                           FastapiOpenapiSchema.flux_msg_json_root)
            else:
                option_val_dict = self.get_complex_option_value_from_proto(message,
                                                                           FastapiOpenapiSchema.flux_msg_json_root_time_series)

            for crud_option_field_name, crud_operation_method in crud_field_name_to_method_call_dict.items():
                if crud_option_field_name in option_val_dict:
                    output_str += crud_operation_method(message)

                    if crud_option_field_name == FastapiOpenapiSchema.flux_json_root_read_field:
                        # adding get all handling also
                        output_str += ",\n"
                        output_str += self.handle_GET_all_req_body(message)

                    output_str += ",\n"

        # query req_body and response
        for message in self.message_to_query_option_list_dict:
            aggregate_value_list = self.message_to_query_option_list_dict[message]

            for aggregate_value in aggregate_value_list:
                query_name = aggregate_value[FastapiOpenapiSchema.query_name_key]
                query_params_name_n_param_type_tuple_list = aggregate_value[FastapiOpenapiSchema.query_params_key]
                query_type_value = aggregate_value[FastapiOpenapiSchema.query_type_key]
                query_type = str(query_type_value).lower() if query_type_value is not None else None
                query_route_value = aggregate_value[FastapiOpenapiSchema.query_route_type_key]
                query_route_type = query_route_value if query_route_value is not None else None

                if query_type is None or query_type == "http" or query_type == "both":
                    output_str += self.handle_query_req_body(message, query_name,
                                                             query_params_name_n_param_type_tuple_list, query_route_type)
                    output_str += ",\n"
                elif query_type == "http_file":
                    output_str += self.handle_file_query_req_body(message, query_name,
                                                                  query_params_name_n_param_type_tuple_list)
                    output_str += ",\n"

        # ui button query req body
        query_data_dict_list: List[Dict]
        for message, query_data_dict_list in self.message_to_button_query_data_dict.items():
            for query_data_dict in query_data_dict_list:
                output_str += self.handle_button_query_req_body(message, query_data_dict)

        for message in self.root_message_list:
            if FastapiOpenapiSchema.is_option_enabled(message, FastapiOpenapiSchema.flux_msg_json_root_time_series):
                # returns empty str if message has no field suggesting projection query option set
                output_str += self.handle_projection_query_req_body(message)

        output_str += '    },\n'
        output_str += '    "components": {\n'
        output_str += '        "schemas": {\n'
        for message in self.message_schema_cache_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            output_str += f'            "{message_name}": {message_name_snake_cased}_schema,\n'
        output_str += '        }\n'
        output_str += '    }\n'
        output_str += '}\n'
        return output_str
