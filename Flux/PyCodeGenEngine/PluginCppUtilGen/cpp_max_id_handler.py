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

        output_content += f'#include "../../FluxCppCore/include/base_web_client.h"\n\n'

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

        output_content += f"\n\tclass {class_name}MaxIdHandler;\n\n"

        output_content += "\tclass MaxIdHandler {\n"
        output_content += "\tpublic:\n\n"
        output_content += "\t\tint32_t get_next_id() {\n"
        output_content += "\t\t\tstd::lock_guard lg(max_id_mutex);\n"
        output_content += "\t\t\tmax_used_id++;\n"
        output_content += "\t\t\treturn max_used_id;\n"
        output_content += "\t\t}\n\n"

        output_content += "\tprotected:\n\n"
        output_content += "\t\tvoid update_max_id(const int32_t max_used_id_) {\n"
        output_content += "\t\t\tmax_used_id = max_used_id_;\n"
        output_content += "\t\t}\n\n"

        output_content += f"\t\tfriend {class_name}MaxIdHandler;\n"
        output_content += "\t\tint32_t max_used_id = 0;\n"
        output_content += "\t\tstd::mutex max_id_mutex{};\n"
        output_content += "\t};\n\n"

        output_content += f"\tclass {class_name}MaxIdHandler {{\n\n"
        output_content += "\tpublic:\n\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):

                        output_content += (f"\t\tstatic void update_{message_name_snake_cased}_max_id(const "
                                           f"FluxCppCore::RootModelWebClient <{package_name}::{message_name}, "
                                           f"create_{message_name_snake_cased}_client_url, get_"
                                           f"{message_name_snake_cased}_client_url, get_{message_name_snake_cased}"
                                           f"_max_id_client_url, put_{message_name_snake_cased}_client_url, patch_"
                                           f"{message_name_snake_cased}_client_url, delete_{message_name_snake_cased}"
                                           f"_client_url> &kr_{class_name_snake_cased}_web_client) {{\n")
                        output_content += (f"\t\t\tc_{message_name_snake_cased}_max_id_handler.update_max_id("
                                           f"kr_{class_name_snake_cased}_web_client.get_max_id_client());\n")
                        output_content += "\t\t}\n\n"
                        break

        output_content += "\tpublic:\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):
                        output_content += f"\t\tstatic inline MaxIdHandler c_{message_name_snake_cased}_max_id_handler{{}};\n"
                        break

        output_content += "\t};\n}\n"

        output_file_name = f"{class_name_snake_cased}_max_id_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppMaxIdHandler)
