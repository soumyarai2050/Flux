#!/usr/bin/env python
import logging
import os
import time
from typing import List

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppMaxIdHandler(BaseProtoPlugin):
    """
    Plugin to generate cpp_max_id_handler files
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
            if CppMaxIdHandler.is_option_enabled \
                        (message, CppMaxIdHandler.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    @staticmethod
    def header_generate_handler(file_name: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"

        output_content += f'#include "{class_name_snake_cased}_web_client.h"\n\n'

        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {package_name}_handler {{\n"

        output_content += f"\n\tclass {class_name}MaxIdHandler {{\n"
        output_content += "\tpublic:\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):
                        output_content += f"\t\tstatic int32_t get_{message_name_snake_cased}_max_id() {{\n"
                        output_content += f"\t\t\treturn {message_name_snake_cased}_max_id_;\n"
                        output_content += "\t\t}\n\n"

                        output_content += (f"\t\tstatic void update_{message_name_snake_cased}_max_id(const "
                                           f"{class_name}WebClient &{class_name_snake_cased}_web_client) {{\n")
                        output_content += (f"\t\t\t{message_name_snake_cased}_max_id_ = {class_name_snake_cased}"
                                           f"_web_client.get_{message_name_snake_cased}_max_id_client();\n")
                        output_content += "\t\t}\n\n"
                        break

        output_content += "\tprotected:\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):
                        output_content += f"\t\tstatic inline int32_t {message_name_snake_cased}_max_id_ = 0;\n"
                        break

        output_content += "\t};\n}\n"

        output_file_name = f"{class_name_snake_cased}_max_id_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppMaxIdHandler)
