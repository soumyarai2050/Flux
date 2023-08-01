#!/usr/bin/env python
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
from Flux.PyCodeGenEngine.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin


class CppKeyHandlerPlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to key generate from proto schema
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
            if CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    @staticmethod
    def header_generate_handler(file_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n\n"
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'
        return output_content

    @staticmethod
    def generate_get_key_list(package_name: str, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        output_content: str = ""

        output_content += f"\n\t\tstatic inline void get_{message_name_snake_cased}" \
                          f"_key_list(const {package_name}::{message_name}List &{message_name_snake_cased}_list_obj, " \
                          f"std::vector< std::string > &{message_name_snake_cased}_key_list) {{\n"

        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_obj.{message_name_snake_cased}_size(); ' \
                          f'++i) {{\n'
        output_content += f'\t\t\t\tstd::string key;\n'
        output_content += (f'\t\t\t\tget_{message_name_snake_cased}_key({message_name_snake_cased}_list_obj.'
                           f'{message_name_snake_cased}(i), key);\n')
        output_content += f'\t\t\t\t{message_name_snake_cased}_key_list.push_back(key);\n'
        output_content += '\t\t\t}\n'

        return output_content

    @staticmethod
    def generate_get_key_handler(message: protogen.Message, message_name_snake_cased: str):
        output: str = ""

        for field in message.fields:
            field_name: str = field.proto.name
            field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
            if CppKeyHandlerPlugin.is_option_enabled(field, "FluxFldPk"):
                if field.kind.name.lower() == "int32":
                    output += (f"\t\t\t{message_name_snake_cased}_key = {message_name_snake_cased}_key + "
                               f"std::to_string({message_name_snake_cased}_obj.{field_name_snake_cased}());\n")
                    output += f'\t\t\t{message_name_snake_cased}_key += "_";\n'
                else:
                    output += (f"\t\t\t{message_name_snake_cased}_key = {message_name_snake_cased}_key + "
                               f"{message_name_snake_cased}_obj.{field_name_snake_cased}();\n")
                    output += f'\t\t\t{message_name_snake_cased}_key += "_";\n'

        return output

    def output_file_generate_handler(self, file: protogen.File):
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

        output_content += self.header_generate_handler(file_name)

        output_content += f"namespace {package_name}_handler {{\n\n"

        output_content += f"\tclass {class_name}KeyHandler "
        output_content += "{\n\n"

        output_content += "\tpublic:\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_executor_options):
                # message_name = message.proto.name
                output_content += f"\n\t\tstatic inline void get_{message_name_snake_cased}_key(const {package_name}::" \
                                  f"{message_name} &{message_name_snake_cased}_obj, std::string &" \
                                  f"{message_name_snake_cased}_key)"
                output_content += "{\n"
                output_content += self.generate_get_key_handler(message, message_name_snake_cased)
                output_content += "\n\t\t}\n"

                output_content += self.generate_get_key_list(package_name, message)
                output_content += "\t\t}\n\n"

        output_content += "\t};\n\n"
        output_content += "}\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_key_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppKeyHandlerPlugin)
