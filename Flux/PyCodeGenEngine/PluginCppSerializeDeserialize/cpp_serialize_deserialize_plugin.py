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

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)
        output_content = ""

        output_content += f'#pragma once\n\n#include <iostream>\n\n#include "../ProtoGenCc/{file_name}.pb.h"\n' \
                          f'#include <google/protobuf/util/json_util.h>\n\n'

        output_content += "class JSONCodec {\npublic:\n\n"

        output_content += "\tinline auto encode_options(bool whitespace = false) {\n\t\t" \
                          "google::protobuf::util::JsonPrintOptions options;\n\t\toptions.add_whitespace = whitespace;" \
                          "\n\t\toptions.always_print_primitive_fields = true;\n\t\t" \
                          "options.preserve_proto_field_names = true;\n\t\treturn options;\n\t}\n\n\t"

        output_content += "// All model encoders\n\n"

        output_content += "\tinline auto decode_options() {\n\t\t" \
                          "google::protobuf::util::JsonParseOptions options;\n\t\toptions.ignore_unknown_fields = " \
                          "true;\n\t\treturn options;\n\t}\n\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f"\tinline std::string encode_{message_name_snake_cased} " \
                                  f"({package_name}::{message_name} &{message_name_snake_cased}, bool whitespace = false)"
                output_content += " {\n\t\t"
                output_content += "\n\t\tstd::string json_string;\n\t\t"
                output_content += f"google::protobuf::util::MessageToJsonString(" \
                                  f"{message_name_snake_cased}, &json_string, encode_options(whitespace));\n\t\t"
                output_content += "return json_string;\n\t}\n\n"

        output_content += "\n\t// All model list encoders\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f"\tinline std::vector<std::string> encode_" \
                                  f"{message_name_snake_cased}_list (std::vector<{package_name}::{message_name}>" \
                                  f" &{message_name_snake_cased}_list, bool whitespace = false)"
                output_content += "{\n\t\t"
                output_content += f'std::vector<std::string> {message_name_snake_cased}_json_list;\n\t\t'
                output_content += f"for (auto& {message_name_snake_cased} : {message_name_snake_cased}_list) "
                output_content += "{\n\t\t\tstd::string json_string;\n\t\t\t"
                output_content += f"google::protobuf::util::MessageToJsonString(" \
                                  f"{message_name_snake_cased}, &json_string, encode_options(whitespace));\n\t\t\t"
                output_content += f"{message_name_snake_cased}_json_list.push_back(json_string);\n\t\t"
                output_content += "}"
                output_content += f"\n\t\treturn {message_name_snake_cased}_json_list;\n\t"
                output_content += "}\n\n"

        output_content += "\n\t// All model decoders\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                output_content += f"\tinline {package_name}::{message_name} decode_" \
                                  f"{message_name_snake_cased}(const std::string &{message_name_snake_cased}" \
                                  f"_json_string)"

                output_content += "{\n\t\t"
                output_content += f"{package_name}::{message_name} {message_name_snake_cased};\n\t\t"
                output_content += f"google::protobuf::util::JsonStringToMessage({message_name_snake_cased}" \
                                  f"_json_string, &{message_name_snake_cased}, decode_options());\n\t\t"
                output_content += f"return {message_name_snake_cased};"
                output_content += "\n\t}\n\n"

        output_content += "\n\t// All model list decoders\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f"\tinline std::vector <{package_name}::{message_name}> decode_" \
                                  f"{message_name_snake_cased}_list(std::vector <std::string> &{message_name_snake_cased}" \
                                  f"_json_list)"

                output_content += "{\n\t\t"
                output_content += f"std::vector <{package_name}::{message_name}> {message_name_snake_cased}_list;\n\t\t"
                output_content += f"for (auto& {message_name_snake_cased}_data: {message_name_snake_cased}_json_list) "
                output_content += "{\n\t\t\t"
                output_content += f"{package_name}::{message_name} {message_name_snake_cased};\n\t\t\t"
                output_content += f"google::protobuf::util::JsonStringToMessage({message_name_snake_cased}_data, " \
                                  f"&{message_name_snake_cased}, decode_options());\n\t\t\t"
                output_content += f'{message_name_snake_cased}_list.push_back({message_name_snake_cased});\n\t\t'
                output_content += "}\n\t\t"
                output_content += f"return {message_name_snake_cased}_list;"
                output_content += "\n\t}\n\n"

        output_content += "};\n\n"

        output_content += "\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{proto_file_name}_handle_serialize_deserialize.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
