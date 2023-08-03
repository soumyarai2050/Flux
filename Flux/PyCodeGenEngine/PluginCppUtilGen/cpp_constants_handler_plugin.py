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
    Plugin to generate DB Handler
    """
    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: protogen.Message) -> None:
        field_names = []
        for field in messages.fields:
            field_name: str = field.proto.name
            field_type_message: protogen.Message | None = field.message
            if field_type_message is None:
                field_names.append(field_name)
            else:
                field_names.append(field_name)
                self.get_field_names(field_type_message)

        for field_name in field_names:
            if field_name not in self.field:
                self.field.append(field_name)

    def const_string_generate_handler(self, file: protogen.File):
        output_content: str = ""
        for message in file.messages:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            output_content += f'\tconst std::string {message_name_snake_cased}_msg_name = "{message_name}";\n'

        output_content += "\n\n"

        for field_name in self.field:
            output_content += f'\tconst std::string {field_name}_fld_name = "{field_name}";\n'
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)

        for message in self.root_message_list:
            self.get_field_names(message)
        package_name = str(file.proto.package)
        class_name_list = package_name.split("_")
        class_name: str = ""
        output_content: str = ""

        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += "#pragma once\n\n"

        output_content += f"namespace {package_name}_handler "
        output_content += "{\n\n"
        output_content += '    const std::string db_uri = getenv("MONGO_URI") ? getenv("MONGO_URI") : ' \
                          '"mongodb://localhost:27017";\n'
        file_name = str(file.proto.name).split(".")[0]
        output_content += f'    const std::string {file_name}_db_name = "{file_name}";\n'

        output_content += "\n\t// key constants used across classes via constants for consistency\n"

        output_content += self.const_string_generate_handler(file)

        output_content += "\n}"

        output_file_name = f"{class_name_snake_cased}_constants.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
