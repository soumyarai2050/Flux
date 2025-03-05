#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case


class CppDbTestCppPlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_db_test.cpp file
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    @staticmethod
    def headers_generate_handler(class_name: str):
        output_content: str = ""
        output_content += f'#include "{class_name}_mongo_db_codec.h"\n\n'
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
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)
        output_content = ""

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += self.headers_generate_handler(class_name_snake_cased)

        # for message in self.root_message_list:
        #     if CppDbTestCppPlugin.is_option_enabled(message, CppDbTestCppPlugin.flux_msg_json_root):
        #         for field in message.fields:
        #             field_name: str = field.proto.name
        #             field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
        #             if CppDbTestCppPlugin.is_option_enabled(field, CppDbTestCppPlugin.flux_fld_PK):
        #                 message_name = message.proto.name
        #                 message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        #                 output_content += f"std::unordered_map < std::string, int32_t > {package_name}_handler::" \
        #                                   f"{class_name}MongoDB{message_name}Codec::{message_name_snake_cased}" \
        #                                   f"_key_to_db_id;\n"
        #                 output_content += f"std::mutex {package_name}_handler::{class_name}MongoDB" \
        #                                   f"{message_name}Codec::max_id_mutex;\n"
        #                 output_content += f"int32_t {package_name}_handler::" \
        #                                   f"{class_name}MongoDB{message_name}Codec::cur_unused_max_id;\n\n"
        #                 break

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_mongo_db_codec.cpp"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbTestCppPlugin)
