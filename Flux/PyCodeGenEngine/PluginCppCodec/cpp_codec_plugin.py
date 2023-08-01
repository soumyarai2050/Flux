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
    def header_generate_handler(file_name: str):
        output_content: str = ""
        output_content += f'#pragma once\n\n#include "quill/Quill.h"\n\n#include "../ProtoGenCc/{file_name}.pb.h"\n' \
                          f'#include <google/protobuf/util/json_util.h>\n\n'
        return output_content

    @staticmethod
    def encode_and_decode_options_generate_handler():
        output_content: str = ""
        output_content += "\t\tstatic inline void encode_options(google::protobuf::util::JsonPrintOptions" \
                          " &options,const bool whitespace = false) {\n\t\t" \
                          "\n\t\t\toptions.add_whitespace = whitespace;" \
                          "\n\t\t\toptions.always_print_primitive_fields = whitespace;\n\t\t" \
                          "options.preserve_proto_field_names = true;\n\n\t\t}\n\n\t\t"
        output_content += "static inline void decode_options(google::protobuf::util::JsonParseOptions " \
                          "&options) {\n\t\t\t" \
                          "\n\t\t\toptions.ignore_unknown_fields = " \
                          "true;\n\t\t}\n\n"

        return output_content

    @staticmethod
    def encode_generate_handler(message: protogen.Message, package_name: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        output_content: str = ""

        output_content += f"\t\t[[nodiscard]] static inline bool encode_{message_name_snake_cased} " \
                          f"(const {package_name}::{message_name} &{message_name_snake_cased}_obj, " \
                          f"std::string &{message_name_snake_cased}_json_out, const bool whitespace = false)"
        output_content += " {\n"
        output_content += "\t\t\tgoogle::protobuf::util::JsonPrintOptions options;\n"
        output_content += "\t\t\tencode_options(options, whitespace);\n"
        output_content += f"\t\t\tgoogle::protobuf::util::Status status = google::protobuf::util::MessageToJsonString(" \
                          f"{message_name_snake_cased}_obj, &{message_name_snake_cased}_json_out, options);\n\t\t\t"
        output_content += "if (status.code() == google::protobuf::util::StatusCode::kOk)\n"
        output_content += "\t\t\t\treturn true;\n"
        output_content += "\t\t\telse {\n"
        output_content += f'\t\t\t\tLOG_ERROR(logger_, "Failed Encoding {message_name}, error: {{}} ' \
                          f'{message_name_snake_cased}: {{}}", status.message().ToString(), ' \
                          f'{message_name_snake_cased}_obj.DebugString());\n'
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        output_content += f"\t\t[[nodiscard]] static inline bool encode_{message_name_snake_cased}_list " \
                          f"(const {package_name}::{message_name}List &{message_name_snake_cased}_list_obj, " \
                          f"std::string &{message_name_snake_cased}_list_json_out, const bool whitespace = false) "
        output_content += "{\n"
        output_content += "\t\t\tgoogle::protobuf::util::JsonPrintOptions options;\n"
        output_content += "\t\t\tencode_options(options, whitespace);\n"
        output_content += f"\t\t\tgoogle::protobuf::util::Status status = google::protobuf::util::MessageToJsonString(" \
                          f"{message_name_snake_cased}_list_obj, &{message_name_snake_cased}_list_json_out, options);\n"
        output_content += "\t\t\tif (status.code() == google::protobuf::util::StatusCode::kOk) {\n"
        output_content += f'\t\t\t\tsize_t pos = {message_name_snake_cased}_list_json_out.find(":[{{");\n'
        output_content += '\t\t\t\tif (pos != std::string::npos) {\n'
        output_content += '\t\t\t\t\t//refer to example_comments.txt for before substr and after substr\n'
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_list_json_out = {message_name_snake_cased}_list_' \
                          f'json_out.substr(pos + 1, {message_name_snake_cased}_list_json_out.size() - pos - 2);\n'
        output_content += "\t\t\t\t\treturn true;\n"
        output_content += "\t\t\t\t} // else not required: when we try to encode empty string we'll not find `:[{` as " \
                          "substr\n"
        output_content += "\t\t\t\treturn true;\n"
        output_content += "\t\t\t} else {\n"
        output_content += f'\t\t\t\tLOG_ERROR(logger_, "Failed Encoding {message_name} List, error: {{}} ' \
                          f'{message_name_snake_cased}_list: {{}}", status.message().ToString(), ' \
                          f'{message_name_snake_cased}_list_obj.DebugString());\n'
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        return output_content

    @staticmethod
    def decode_generate_handler(message: protogen.Message, package_name: str):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        output_content: str = ""

        output_content += f"\t\t[[nodiscard]] static inline bool decode_{message_name_snake_cased}({package_name}" \
                          f"::{message_name} &{message_name_snake_cased}_obj, const std::string " \
                          f"&{message_name_snake_cased}_json) {{\n"

        output_content += "\t\t\tgoogle::protobuf::util::JsonParseOptions options;\n"
        output_content += "\t\t\tdecode_options(options);\n"
        output_content += f"\t\t\tgoogle::protobuf::util::Status status = google::protobuf::util::JsonStringToMessage" \
                          f"({message_name_snake_cased}_json, &{message_name_snake_cased}_obj, options);\n\t\t\t"
        output_content += f"if (status.code() == google::protobuf::util::StatusCode::kOk) {{\n"
        output_content += "\t\t\t\treturn true;\n"
        output_content += "\t\t\t} else {\n"
        output_content += f'\t\t\t\tLOG_ERROR(logger_, "Failed Decoding {message_name}, error: {{}} ' \
                          f'{message_name_snake_cased}_json: {{}}", status.message().ToString(), ' \
                          f'{message_name_snake_cased}_json);\n'
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        output_content += f"\t\t// ideally {message_name_snake_cased}_list_json should have been a const - but we " \
                          f"intend to reuse the top_of_book_list_json to avoid creating new string\n"
        output_content += f"\t\t[[nodiscard]] static inline bool decode_{message_name_snake_cased}_list ({package_name}" \
                          f"::{message_name}List &{message_name_snake_cased}_list_obj, std::string " \
                          f"&{message_name_snake_cased}_list_json) "
        output_content += "{\n"
        output_content += "\t\t\tgoogle::protobuf::util::JsonParseOptions options;\n"
        output_content += "\t\t\tdecode_options(options);\n"
        output_content += f'\t\t\tsize_t pos = {message_name_snake_cased}_list_json.find(":[");\n'
        output_content += f"\t\t\tif (pos == std::string::npos && {message_name_snake_cased}_list_json.back() != ']')\n"
        output_content += f'\t\t\t\t{message_name_snake_cased}_list_json = "[" + {message_name_snake_cased}_list_json ' \
                          f'+ "]";\n'
        output_content += f'\t\t\t{message_name_snake_cased}_list_json = "{{\\"{message_name_snake_cased}\\":" + ' \
                          f'{message_name_snake_cased}_list_json + '
        output_content += "'}';\n"
        output_content += f"\t\t\tgoogle::protobuf::util::Status status = google::protobuf::util::JsonStringToMessage" \
                          f"({message_name_snake_cased}_list_json, &{message_name_snake_cased}_list_obj, options);\n"
        output_content += "\t\t\tif (status.code() == google::protobuf::util::StatusCode::kOk) {\n"
        output_content += "\t\t\t\treturn true;\n"
        output_content += "\t\t\t} else {\n"
        output_content += f'\t\t\t\tLOG_ERROR(logger_, "Failed Decoding {message_name}List, error: {{}} ' \
                          f'{message_name_snake_cased}_list_json: {{}}", status.message().ToString(),' \
                          f' {message_name_snake_cased}_list_json);\n'
        output_content += '\t\t\t\treturn false;\n'
        output_content += "\t\t\t}\n"
        output_content += "\n\t\t}\n\n"

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

        output_content += self.header_generate_handler(file_name)

        output_content += f"namespace {package_name}_handler {{\n\n"

        output_content += f"\tclass {class_name}JSONCodec {{\n\tpublic:\n\n"

        output_content += f"\t\t{class_name}JSONCodec() {{\n"
        output_content += "\t\t\tquill::start();\n"
        output_content += "\t\t\tlogger_ = quill::get_logger();\n"
        output_content += "\t\t}\n\n"

        output_content += self.encode_and_decode_options_generate_handler()

        output_content += "\t\t// All model encoders and decoders\n\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root) and \
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_executor_options):
                output_content += self.encode_generate_handler(message, package_name)
                output_content += self.decode_generate_handler(message, package_name)

        output_content += "\n\tprotected:\n"
        output_content += "\t\tstatic inline quill::Logger* logger_;\n"
        output_content += "\t};\n\n"

        output_content += "}\n\n"

        output_file_name = f"{class_name_snake_cased}_json_codec.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
