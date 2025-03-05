#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

from FluxPythonUtils.scripts.general_utility_functions import parse_to_int
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class CppSwaggerUiJson(BaseProtoPlugin):
    """
    Plugin to generate cpp_swagger_ui_json files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_name_list: List[protogen.Message] = []
        self.root_message_list: List[protogen.Message] = []
        self.kind_dict = {"bool": "boolean", "int32": "integer", "int64": "integer", "float": "number",
                     "double": "number", "string": "string", "enum": "string"}
        self.generated_schemas: List[str] = []

    def generate_schema(self, message: protogen.Message, field_name: str, num_of_tabs: int):
        msg_name = message.proto.name
        msg_name_snake_cased = convert_camel_case_to_specific_case(msg_name)
        output_content: str = ""

        output_content += num_of_tabs*"\t" + f'"{field_name}": {{\n'
        num_of_tabs+=1
        output_content += num_of_tabs*"\t" + f'"type": "object",\n'
        output_content += num_of_tabs*"\t" + f'"properties": {{\n'
        num_of_tabs+=1
        for fld in message.fields:
            fld_name = fld.proto.name
            if fld.message is None:
                if fld_name == "id":
                    output_content += num_of_tabs*"\t" + f'"_{fld_name}": {{\n'
                    num_of_tabs+=1
                    fld_type = self.kind_dict.get(fld.kind.name.lower())
                    output_content += num_of_tabs*"\t" + f'"type": "{fld_type}"'
                    if fld_type is not None and fld_type == "number":
                        output_content += ",\n" + num_of_tabs*"\t" + '"format": "double"\n'
                    num_of_tabs-=1
                    output_content += "\n" + num_of_tabs*"\t" + f'}},\n'
                else:
                    output_content += num_of_tabs * "\t" + f'"{fld_name}": {{\n'
                    num_of_tabs += 1
                    fld_type = self.kind_dict.get(fld.kind.name.lower())
                    output_content += num_of_tabs * "\t" + f'"type": "{fld_type}"'
                    if fld_type is not None and fld_type == "number":
                        output_content += ",\n" + num_of_tabs * "\t" + '"format": "double"\n'
                    num_of_tabs -= 1
                    output_content += "\n" + num_of_tabs * "\t" + f'}},\n'
            else:
                if fld.message.proto.name not in self.generated_schemas:
                    self.generated_schemas.append(message.proto.name)
                    output_content += self.generate_schema(fld.message, fld_name, 5)
        output_content = output_content[:-2]
        num_of_tabs-=1
        output_content += "\n" + num_of_tabs* "\t" + f'}}\n'
        num_of_tabs-=1
        output_content += "\t" * num_of_tabs + f'}},\n'
        return output_content

    @staticmethod
    def generate_get_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        output_content += f'\t\t"/get-{msg_name_snake_cased}/{{{msg_name_snake_cased}_id}}": {{\n'
        output_content += f'\t\t\t"get": {{\n'
        output_content += f'\t\t\t\t"summary": "GET api to get {msg_name}",\n'
        output_content += f'\t\t\t\t"parameters": [\n\n'
        output_content += f'\t\t\t\t\t{{\n'
        output_content += f'\t\t\t\t\t\t"name": "{msg_name_snake_cased}_id",\n'
        output_content += f'\t\t\t\t\t\t"in": "path",\n'
        output_content += f'\t\t\t\t\t\t"required": true,\n'
        output_content += f'\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t"type": "integer"\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t],\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "found",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'

        return output_content

    @staticmethod
    def generate_get_all_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        # Get All interface
        output_content += f'\t\t"/get-all-{msg_name_snake_cased}": {{\n'
        output_content += f'\t\t\t"get": {{\n'
        output_content += f'\t\t\t\t"summary": "GET api to get all {msg_name}",\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "found",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'
        return output_content

    @staticmethod
    def generate_create_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        # create api
        output_content += f'\t\t"/create-{msg_name_snake_cased}": {{\n'
        output_content += f'\t\t\t"post": {{\n'
        output_content += f'\t\t\t\t"summary": "POST api to create {msg_name}",\n'
        output_content += f'\t\t\t\t"requestBody": {{\n'
        output_content += f'\t\t\t\t\t"description": "response",\n\n'
        output_content += f'\t\t\t\t\t"required": true,\n'
        output_content += f'\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}},\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "found",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'

        return output_content

    @staticmethod
    def generate_put_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        # PUT api
        output_content += f'\t\t"/put-{msg_name_snake_cased}": {{\n'
        output_content += f'\t\t\t"put": {{\n'
        output_content += f'\t\t\t\t"summary": "PUT api to update {msg_name}",\n'
        output_content += f'\t\t\t\t"requestBody": {{\n'
        output_content += f'\t\t\t\t\t"description": "response",\n\n'
        output_content += f'\t\t\t\t\t"required": true,\n'
        output_content += f'\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}},\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "found",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'
        return output_content

    @staticmethod
    def generate_patch_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        # PATCH api
        output_content += f'\t\t"/patch-{msg_name_snake_cased}": {{\n'
        output_content += f'\t\t\t"patch": {{\n'
        output_content += f'\t\t\t\t"summary": "PATCH api to partially update {msg_name}",\n'
        output_content += f'\t\t\t\t"requestBody": {{\n'
        output_content += f'\t\t\t\t\t"description": "response",\n\n'
        output_content += f'\t\t\t\t\t"required": true,\n'
        output_content += f'\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}},\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "found",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/{msg_name_snake_cased}"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'

        return output_content

    @staticmethod
    def generate_delete_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        # delete api
        output_content += f'\t\t"/delete-{msg_name_snake_cased}/{{{msg_name_snake_cased}_id}}": {{\n'
        output_content += f'\t\t\t"delete": {{\n'
        output_content += f'\t\t\t\t"summary": "DELETE api to delete {msg_name}",\n'
        output_content += f'\t\t\t\t"parameters": [\n\n'
        output_content += f'\t\t\t\t\t{{\n'
        output_content += f'\t\t\t\t\t\t"name": "{msg_name_snake_cased}_id",\n'
        output_content += f'\t\t\t\t\t\t"in": "path",\n'
        output_content += f'\t\t\t\t\t\t"required": true,\n'
        output_content += f'\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t"type": "integer"\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t],\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "deleted",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'
        return output_content

    @staticmethod
    def generate_delete_all_schema(msg_name: str, msg_name_snake_cased: str):
        output_content = ""
        output_content += f'\t\t"/delete-all-{msg_name_snake_cased}": {{\n'
        output_content += f'\t\t\t"delete": {{\n'
        output_content += f'\t\t\t\t"summary": "DELETE api to delete all {msg_name}",\n'
        output_content += f'\t\t\t\t"responses": {{\n'
        output_content += f'\t\t\t\t\t"200": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "deleted",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}},\n'
        output_content += f'\t\t\t\t\t"400": {{\n'
        output_content += f'\t\t\t\t\t\t"description": "Bad Request",\n'
        output_content += f'\t\t\t\t\t\t"content": {{\n'
        output_content += f'\t\t\t\t\t\t\t"application/json": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t"schema": {{\n'
        output_content += f'\t\t\t\t\t\t\t\t\t"$ref": "#/components/schemas/ErrorResponse"\n'
        output_content += f'\t\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t\t}}\n'
        output_content += f'\t\t\t\t}}\n'
        output_content += f'\t\t\t}}\n'
        output_content += f'\t\t}},\n'
        return output_content

    def output_file_generate_handler(self, file: protogen.File):

        proto_file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        # print(package_name)
        output_content: str = f""

        output_content += '{\n'
        output_content += f'\t"openapi": "3.0.2",\n'
        output_content += f'\t"info": {{\n'
        output_content += f'\t\t"title": "{package_name} API Docs",\n'
        output_content += f'\t\t"version": "1.0.0"\n'
        output_content += f'\t}},\n'
        output_content += f'\t"paths": {{\n'

        flux_import_models = self.get_complex_option_value_from_proto(file, self.flux_file_import_dependency_model, True)
        import_file_name_list: List[str] = []
        for i in flux_import_models:
            import_file_name_list.append(i.get("ImportFileName"))
            for msg in i.get("ImportModelName"):
                self.root_message_name_list.append(msg)

        for dependency_file in file.dependencies:
            dependency_name = dependency_file.proto.name
            if dependency_name in import_file_name_list:
                for msg in dependency_file.messages:
                    if msg.proto.name in self.root_message_name_list:
                        if (self.is_option_enabled(msg, self.flux_msg_json_root) or
                                self.is_option_enabled(msg, self.flux_msg_json_root_time_series)):
                            self.root_message_list.append(msg)

        for msg in file.messages:
            if self.is_option_enabled(msg, self.flux_msg_cpp_json_root):
                self.root_message_list.append(msg)

        for message in self.root_message_list:
            msg_name = message.proto.name
            msg_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            if self.is_option_enabled(message, self.flux_msg_cpp_json_root):
                # if self.is_option_enabled(message, self.flux_msg_json_root):
                cpp_server_operations = self.get_complex_option_value_from_proto(
                    message, self.flux_msg_cpp_json_root, False)

                for key, val in cpp_server_operations.items():
                    if key == self.flux_json_root_read_field:
                        output_content += self.generate_get_schema(msg_name, msg_name_snake_cased)
                        output_content+= self.generate_get_all_schema(msg_name, msg_name_snake_cased)
                    elif key == self.flux_json_root_create_field:
                        output_content += self.generate_create_schema(msg_name, msg_name_snake_cased)
                    elif key == self.flux_json_root_update_field:
                        output_content += self.generate_put_schema(msg_name, msg_name_snake_cased)
                    elif key == self.flux_json_root_patch_field:
                        output_content += self.generate_patch_schema(msg_name, msg_name_snake_cased)
                    elif key == self.flux_json_root_delete_field:
                        output_content += self.generate_delete_schema(msg_name, msg_name_snake_cased)
                    elif key == self.flux_json_root_delete_all_field:
                        output_content += self.generate_delete_all_schema(msg_name, msg_name_snake_cased)

        output_content = output_content[:-2]
        output_content += "\n\t},\n"
        output_content += f'\t"components": {{\n'
        output_content += f'\t\t"schemas": {{\n'
        for message in self.root_message_list:
            msg_name = message.proto.name
            msg_name_snake_cased: str = convert_camel_case_to_specific_case(msg_name)
            if self.is_option_enabled(message, self.flux_msg_cpp_json_root):
                if self.is_option_enabled(message, self.flux_msg_json_root):
                    if message.proto.name not in self.generated_schemas:
                        self.generated_schemas.append(message.proto.name)
                        output_content += self.generate_schema(message, msg_name_snake_cased, 3)
                else:
                    if message.proto.name not in self.generated_schemas:
                        self.generated_schemas.append(message.proto.name)
                        output_content += self.generate_schema(message, msg_name_snake_cased, 3)

        output_content = output_content[:-2]
        output_content += ",\n"
        output_content += '\t\t\t"ErrorResponse": {\n'
        output_content += '\t\t\t\t"type": "object",\n'
        output_content += '\t\t\t\t"properties": {\n'
        output_content += '\t\t\t\t\t"error": {\n'
        output_content += '\t\t\t\t\t\t"type": "string"\n'
        output_content += '\t\t\t\t\t}\n'
        output_content += '\t\t\t\t}\n'
        output_content += '\t\t\t}\n'
        output_content += f'\n\t\t}}\n'
        output_content += "\t}\n"
        output_content += '}\n'

        output_file_name: str = f'{package_name}_swagger.json'
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppSwaggerUiJson)
