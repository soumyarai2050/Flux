#!/usr/bin/env python
import json
import logging
from typing import List, Callable, Tuple, Dict
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppDbHandlerPlugin(BaseProtoPlugin):

    """
    Plugin to generate sample output to serialize and deserialize from proto schema
    """
    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    @staticmethod
    def generate_encode_list_comment(message: protogen.Message, message_name: str, message_name_snake_cased: str):
        output_content: str = ""
        output_content += f"{message_name}: \n\n"
        output_content += f"Encode {message_name}List:\n"
        output_content += f'Before substr: {{"{message_name_snake_cased}":[{{'

        for i in range(2):
            for field_id, fields in enumerate(message.fields):
                field_name: str = fields.proto.name
                field_type: str = fields.cardinality.name.lower()
                if field_type != "repeated":
                    if field_id == len(message.fields) - 1:
                        output_content += f'"{field_name}":""'
                    else:
                        output_content += f'"{field_name}":"",'
                else:
                    if field_id == len(message.fields) - 1:
                        output_content += f'"{field_name}":[]'
                    else:
                        output_content += f'"{field_name}":[],'
            if i != 1:
                output_content += f'}},{{'
            else:
                output_content += f'}}]}}\n'

        output_content += f'After substr: [{{'
        for i in range(2):
            for field_id, fields in enumerate(message.fields):
                field_name: str = fields.proto.name
                field_type: str = fields.cardinality.name.lower()
                if field_type != "repeated":
                    if field_id == len(message.fields) - 1:
                        output_content += f'"{field_name}":""'
                    else:
                        output_content += f'"{field_name}":"",'
                else:
                    if field_id == len(message.fields) - 1:
                        output_content += f'"{field_name}":[]'
                    else:
                        output_content += f'"{field_name}":[],'
            if i != 1:
                output_content += f'}},{{'
            else:
                output_content += f'}}]\n\n'

        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)

        class_name_list = package_name.split("_")
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root) and \
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_executor_options):

                output_content += self.generate_encode_list_comment(message, message_name, message_name_snake_cased)

                output_content += f"Decode {message_name}List:\n\n"
                output_content += "From Mongo: \n"
                output_content += f'Before adding string: {{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}\n'

                output_content += f'After adding string: {{"{message_name_snake_cased}":[{{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}]}}\n\n'

                output_content += "From Python: \n"
                output_content += f'Before adding string: [{{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}]\n'

                output_content += f'After adding string: {{"{message_name_snake_cased}":[{{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}]}}\n\n'

                output_content += "From Cpp: \n"
                output_content += f'Before adding string: [{{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}]\n'

                output_content += f'After adding string: {{"{message_name_snake_cased}":[{{'
                for i in range(2):
                    for field_id, fields in enumerate(message.fields):
                        field_name: str = fields.proto.name
                        field_type: str = fields.cardinality.name.lower()
                        if field_type != "repeated":
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":""'
                            else:
                                output_content += f'"{field_name}":"",'
                        else:
                            if field_id == len(message.fields) - 1:
                                output_content += f'"{field_name}":[]'
                            else:
                                output_content += f'"{field_name}":[],'
                    if i != 1:
                        output_content += f'}},{{'
                    else:
                        output_content += f'}}]}}\n\n\n'

        output_file_name = f"{class_name_snake_cased}_example_comments.txt"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
