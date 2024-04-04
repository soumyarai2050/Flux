#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppGetStrFromEnumPlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_get_str_from_enum_plugin files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.root_enum_list: List[protogen.Enum] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_all_enum_list(self, enums: List[protogen.Enum]):
        for enum in enums:
            self.root_enum_list.append(enum)

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        proto_file_name: str = str(file.proto.name).split(".")[0]
        self.get_all_root_message(file.messages)
        self.get_all_enum_list(file.enums)
        dependency_file_list: List[file] = file.dependencies
        # for dependency_file in dependency_file_list:
        #     self.get_all_root_message(file.messages)
        #     self.get_all_enum_list(file.enums)
        package_name = str(file.proto.package)
        output_content = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n\n"
        output_content += f'#include "../ProtoGenCc/{proto_file_name}.pb.h"\n\n'

        output_content += f"namespace {package_name}_handler {{\n\n"


        for message in self.root_message_list:
            for field in message.fields:
                # print(field.kind.name)
                if field.kind.name == "ENUM":
                    if field.enum not in self.root_enum_list:
                        self.root_enum_list.append(field.enum)

        for enum in self.root_enum_list:
            enum_name: str = enum.proto.name
            enum_name_snake_cased: str = convert_camel_case_to_specific_case(enum_name)
            output_content += (f"\tstd::string get_str_from_enum(const {package_name}::{enum_name} "
                               f"&kr_{enum_name_snake_cased}) {{\n")
            output_content += f"\t\tswitch (kr_{enum_name_snake_cased}) {{\n"
            for enum_val in enum.values:
                output_content += f"\t\t\tcase {package_name}::{enum_name}::{enum_val.proto.name}:\n"
                output_content += f'\t\t\t\treturn "{enum_val.proto.name}";\n'

            output_content += "\t\t\tdefault:\n"
            output_content += '\t\t\t\treturn "UNKNOWN";\n'
            output_content += "\t\t}\n\t}\n\n"

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += "}\n"

        output_file_name = f"{class_name_snake_cased}_get_str_from_enum.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppGetStrFromEnumPlugin)
