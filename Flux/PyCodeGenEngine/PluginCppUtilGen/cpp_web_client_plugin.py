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


class CppWebCLientPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppWebCLientPlugin.is_option_enabled\
                        (message, CppWebCLientPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    @staticmethod
    def header_generate_handler(file_name: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += '#include <boost/beast.hpp>\n'
        output_content += '#include <boost/asio/ip/tcp.hpp>\n\n'

        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n'
        output_content += f'#include "../CppCodec/{class_name_snake_cased}_json_codec.h"\n'
        output_content += f'#include "market_data_constants.h"\n\n'

        return output_content

    @staticmethod
    def generate_get_max_id_handler(message_name_snake_cased: str):
        output_content: str = ""

        output_content += f"\t\t[[nodiscard]] auto get_{message_name_snake_cased}_max_id_client() const {{\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_json_out;\n"
        output_content += "\t\t\tint32_t new_max_id = 0;\n"
        output_content += (f"\t\t\tbool status = send_get_request(get_{message_name_snake_cased}_max_id_client_url, "
                           f"{message_name_snake_cased}_json_out);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += "\t\t\t\t// Find the starting position of the `max_id_val` within the JSON string " \
                          "and calculate the position\n"
        output_content += "\t\t\t\t// where the value associated with it begins. We add the length of " \
                          "`max_id_val_key` and 2 to skip dual-quote\n"
        output_content += "\t\t\t\t// and the colon character in the string.\n"
        output_content += (f"\t\t\t\tsize_t start_pos = {message_name_snake_cased}_json_out.find(max_id_val_key) + "
                           f"max_id_val_key.length() + 2;\n")
        output_content += (f'\t\t\t\tsize_t end_pos = {message_name_snake_cased}_json_out.find_first_of("}}",'
                           f' start_pos);\n')
        output_content += "\t\t\t\tif (start_pos != std::string::npos && end_pos != std::string::npos) {\n"
        output_content += (f"\t\t\t\t\tstd::string max_id_str = {message_name_snake_cased}_json_out.substr("
                           f"start_pos, end_pos - start_pos);\n")
        output_content += "\t\t\t\t\ttry {\n"
        output_content += "\t\t\t\t\t\tnew_max_id = std::stoi(max_id_str);\n"
        output_content += "\t\t\t\t\t} catch (const std::exception& e) {\n"
        output_content += '\t\t\t\t\t\tLOG_ERROR(logger_, "Error parsing max_id_val: {}", e.what());\n'
        output_content += "\t\t\t\t\t}\n\t\t\t\t}\n"
        output_content += "\t\t\t\treturn new_max_id;\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while performing get max_id_val request: {{}}, url:'
                           f' {{}}", {message_name_snake_cased}_json_out, get_{message_name_snake_cased}'
                           f'_max_id_client_url);\n')
        output_content += "\t\t\t\treturn new_max_id;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_get_all_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):
        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool get_all_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name}List &{message_name_snake_cased}_list_obj_out) const {{\n'
        output_content += "\t\t\tbool status = false;\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_list_json_out;\n"
        output_content += (f"\t\t\tstatus = send_get_request(get_all_{message_name_snake_cased}_client_url,"
                           f" {message_name_snake_cased}_list_json_out);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += f"\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_json_out.size(); ++i) {{\n'
        output_content += (f"\t\t\t\t\tif ({message_name_snake_cased}_list_json_out[i] == '_' && (i + 1 < "
                           f"{message_name_snake_cased}_list_json_out.size()) && {message_name_snake_cased}"
                           f"_list_json_out[i + 1] == 'i' && {message_name_snake_cased}_list_json_out[i + 2] == 'd'"
                           f" && ( i > 0 && !std::isalnum({message_name_snake_cased}_list_json_out[i - 1]))) {{\n")
        output_content += "\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += (f"\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}"
                           f"_list_json_out[i];\n")
        output_content += "\t\t\t\t\t}\n\t\t\t\t}\n\n"
        output_content += f"\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}_list(" \
                          f"{message_name_snake_cased}_list_obj_out, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t\t} else {\n"
        output_content += "\t\t\t\treturn status;\n"
        output_content += "\t\t\t}\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_get_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):
        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool get_{message_name_snake_cased}_client({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}_obj_out, const int32_t ' \
                          f'&{message_name_snake_cased}_id) const {{\n'
        output_content += "\t\t\tbool status = false;\n"
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_json_out;\n"
        output_content += (f"\t\t\tstatus = send_get_request(get_{message_name_snake_cased}_client_url, "
                           f"{message_name_snake_cased}_id, {message_name_snake_cased}_json_out);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += f"\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_json_out.size(); ++i) {{\n'
        output_content += f"\t\t\t\t\tif ({message_name_snake_cased}_json_out[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_json_out.size()) && {message_name_snake_cased}_json_out[i + 1] == " \
                          f"'i' && {message_name_snake_cased}_json_out[i + 2] == 'd' && ( i > 0 && !std::isalnum" \
                          f"({message_name_snake_cased}_json_out[i - 1]))) {{\n"
        output_content += "\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += (f"\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}"
                           f"_json_out[i];\n")
        output_content += "\t\t\t\t\t}\n\t\t\t\t}\n\n"
        output_content += f"\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}_obj_out, modified_{message_name_snake_cased}_json);\n"
        output_content += f"\t\t\t\treturn status;\n"
        output_content += "\t\t\t} else {\n"
        output_content += "\t\t\t\treturn status;\n"
        output_content += "\t\t\t}\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_create_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool create_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}_obj_in_n_out) const {{\n'
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += f"\t\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}" \
                          f"({message_name_snake_cased}_obj_in_n_out, {message_name_snake_cased}_json, true);\n"
        output_content += f"\t\t\tif (status) {{\n"
        output_content += f"\t\t\t\tstd::string {message_name_snake_cased}_json_out;\n"
        output_content += (f"\t\t\t\tstatus = send_post_request(create_{message_name_snake_cased}_client_url, "
                           f"{message_name_snake_cased}_json, {message_name_snake_cased}_json_out);\n")
        output_content += "\t\t\t\tif (status) {\n"
        output_content += f"\t\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_json_out.size(); ++i) {{\n'
        output_content += f"\t\t\t\t\t\tif ({message_name_snake_cased}_json_out[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_json_out.size()) && {message_name_snake_cased}" \
                          f"_json_out[i + 1] == 'i' && {message_name_snake_cased}_json_out[i + 2] == 'd' " \
                          f"&& ( i > 0 && !std::isalnum({message_name_snake_cased}_json_out[i - 1]))) {{\n"
        output_content += "\t\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += (f"\t\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}"
                           f"_json_out[i];\n")
        output_content += "\t\t\t\t\t\t}\n\t\t\t\t\t}\n"
        output_content += f"\t\t\t\t\t{message_name_snake_cased}_obj_in_n_out.Clear();\n"
        output_content += f"\t\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}_obj_in_n_out, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t\t\t\treturn status;\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += (f'\t\t\t\t\tLOG_ERROR(logger_, "Error while creating {message_name_snake_cased}: {{}} url: '
                           f'{{}}", {message_name_snake_cased}_json, create_{message_name_snake_cased}_client_url);\n')
        output_content += f"\t\t\t\t\treturn false;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while encoding {message_name_snake_cased}: {{}}", '
                           f'{message_name_snake_cased}_obj_in_n_out.DebugString());\n')
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_create_all_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool create_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name}List &{message_name_snake_cased}_list_obj_in_n_out) const {{\n'
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_list_json;\n"
        output_content += (f"\t\t\tbool status = {class_name}JSONCodec::encode_{message_name_snake_cased}_list" 
                          f"({message_name_snake_cased}_list_obj_in_n_out, {message_name_snake_cased}_list_json,"
                           f" true);\n")
        output_content += f"\t\t\tif (status) {{\n"
        output_content += f"\t\t\t\tstd::string {message_name_snake_cased}_list_json_out;\n"
        output_content += (f"\t\t\t\tstatus = send_post_request(create_all_{message_name_snake_cased}_client_url,"
                           f" {message_name_snake_cased}_list_json, {message_name_snake_cased}_list_json_out);\n")
        output_content += "\t\t\t\tif (status) {\n"
        output_content += f"\t\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_json_out.size(); ++i) {{\n'
        output_content += f"\t\t\t\t\t\tif ({message_name_snake_cased}_list_json_out[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_list_json_out.size()) && {message_name_snake_cased}" \
                          f"_list_json_out[i + 1] == 'i' && {message_name_snake_cased}_list_json_out[i + 2] == 'd' " \
                          f"&& ( i > 0 && !std::isalnum({message_name_snake_cased}_list_json_out[i - 1]))) {{\n"
        output_content += "\t\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += (f"\t\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}"
                           f"_list_json_out[i];\n")
        output_content += "\t\t\t\t\t\t}\n\t\t\t\t\t}\n"
        output_content += f"\t\t\t\t\t{message_name_snake_cased}_list_obj_in_n_out.Clear();\n"
        output_content += f"\t\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}_list(" \
                          f"{message_name_snake_cased}_list_obj_in_n_out, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t\t\t\treturn status;\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += (f'\t\t\t\t\tLOG_ERROR(logger_, "Error while creating {message_name_snake_cased}List: {{}}",'
                           f' {message_name_snake_cased}_list_json);\n')
        output_content += f"\t\t\t\t\treturn false;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while encoding {message_name_snake_cased}List: {{}} '
                           f'url: {{}}", {message_name_snake_cased}_list_obj_in_n_out.DebugString(), create_all_'
                           f'{message_name_snake_cased}_client_url);\n')
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_delete_client(message_name_snake_cased: str):

        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] std::string delete_{message_name_snake_cased}_client (const ' \
                          f'int32_t &{message_name_snake_cased}_id) const {{\n'
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_delete_response_json;\n"
        output_content += (f"\t\t\tbool status = send_delete_request(delete_{message_name_snake_cased}_client_url, "
                           f"{message_name_snake_cased}_id, {message_name_snake_cased}_delete_response_json);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += f"\t\t\t\treturn {message_name_snake_cased}_delete_response_json;\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while delete dash: {{}}, dash_id: {{}}, url: {{}}", '
                           f'{message_name_snake_cased}_delete_response_json, {message_name_snake_cased}_id, delete_'
                           f'{message_name_snake_cased}_client_url);\n')
        output_content += f"\t\t\t\treturn {message_name_snake_cased}_delete_response_json;\n"
        output_content += "\t\t\t}\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_put_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool put_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}_obj_in_n_out) const {{\n'
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += (f"\t\t\tbool status = MarketDataJSONCodec::encode_{message_name_snake_cased}("
                           f"{message_name_snake_cased}_obj_in_n_out, {message_name_snake_cased}_json, true);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += f'\t\t\t\tsize_t pos = {message_name_snake_cased}_json.find("id");\n'
        output_content += "\t\t\t\twhile (pos != std::string::npos) {\n"
        output_content += "\t\t\t\t\t// Check if there's no underscore before `id`\n"
        output_content += (f"\t\t\t\t\tif (pos == 0 || {message_name_snake_cased}_json[pos - 1] != '_' && "
                           f"(!std::isalpha({message_name_snake_cased}_json[pos - 1]))) {{\n")
        output_content += "\t\t\t\t\t\t// Insert the underscore before `id`\n"
        output_content += f'\t\t\t\t\t\t{message_name_snake_cased}_json.insert(pos, "_");\n'
        output_content += "\t\t\t\t\t\t// Move the search position to the end of the inserted underscore\n"
        output_content += "\t\t\t\t\t\tpos += 1;\n"
        output_content += "\t\t\t\t\t}\n"
        output_content += "\t\t\t\t\t// Find the next occurrence of `id`\n"
        output_content += f'\t\t\t\t\tpos = {message_name_snake_cased}_json.find("id", pos + 1);\n'
        output_content += "\t\t\t\t}\n"
        output_content += f"\t\t\t\tstd::string {message_name_snake_cased}_json_out;\n"
        output_content += (f"\t\t\t\tstatus = send_put_request(put_{message_name_snake_cased}_client_url, "
                           f"{message_name_snake_cased}_json, {message_name_snake_cased}_json_out);\n\n")
        output_content += "\t\t\t\tif (status) {\n"
        output_content += f"\t\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f"\t\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_json_out.size(); ++i) {{\n"
        output_content += (f"\t\t\t\t\t\tif ({message_name_snake_cased}_json_out[i] == '_' && (i + 1 < "
                           f"{message_name_snake_cased}_json_out.size()) && {message_name_snake_cased}"
                           f"_json_out[i + 1] == 'i' && {message_name_snake_cased}_json_out[i + 2] == "
                           f"'d' && ( i > 0 && !std::isalnum({message_name_snake_cased}_json_out[i - 1]))) {{\n")
        output_content += "\t\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += (f"\t\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}"
                           f"_json_out[i];\n")
        output_content += "\t\t\t\t\t\t}\n"
        output_content += "\t\t\t\t\t}\n"
        output_content += (f"\t\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}("
                           f"{message_name_snake_cased}_obj_in_n_out, modified_{message_name_snake_cased}_json);\n")
        output_content += "\t\t\t\t} else {\n"
        output_content += (f'\t\t\t\t\tLOG_ERROR(logger_, "Error while put {message_name}: {{}} url: {{}}", '
                           f'{message_name_snake_cased}_json, put_{message_name_snake_cased}_client_url);\n')
        output_content += "\t\t\t\t\treturn false;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while encoding {message_name_snake_cased}: '
                           f'{{}}", {message_name_snake_cased}_obj_in_n_out.DebugString());\n')
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n"
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_patch_client(package_name: str, message_name: str, message_name_snake_cased: str, class_name: str):

        output_content: str = ""

        output_content += f'\t\t[[nodiscard]] bool patch_{message_name_snake_cased}_client ({package_name}::' \
                          f'{message_name} &{message_name_snake_cased}_obj_in_n_out) const {{\n'
        output_content += f"\t\t\tstd::string {message_name_snake_cased}_json;\n"
        output_content += (f"\t\t\tbool status = MarketDataJSONCodec::encode_{message_name_snake_cased}"
                           f"({message_name_snake_cased}_obj_in_n_out, {message_name_snake_cased}_json);\n")
        output_content += f"\t\t\tif (status) {{\n"
        output_content += f'\t\t\t\tsize_t pos = {message_name_snake_cased}_json.find("id");\n'
        output_content += f'\t\t\t\twhile (pos != std::string::npos) {{\n'
        output_content += f"\t\t\t\t\t// Check if there's no underscore before `id`\n"
        output_content += f"\t\t\t\t\tif (pos == 0 || {message_name_snake_cased}_json[pos - 1] != '_' && (!std::isalpha" \
                          f"({message_name_snake_cased}_json[pos - 1]))) {{\n"
        output_content += f"\t\t\t\t\t\t// Insert the underscore before `id`\n"
        output_content += f'\t\t\t\t\t\t{message_name_snake_cased}_json.insert(pos, "_");\n'
        output_content += f"\t\t\t\t\t\t// Move the search position to the end of the inserted underscore\n"
        output_content += f"\t\t\t\t\t\tpos += 1;\n"
        output_content += "\t\t\t\t\t}\n"
        output_content += "\t\t\t\t\t// Find the next occurrence of `id`\n"
        output_content += f'\t\t\t\t\tpos = {message_name_snake_cased}_json.find("id", pos + 1);\n'
        output_content += "\t\t\t\t}\n\n"

        output_content += f"\t\t\t\tstd::string {message_name_snake_cased}_json_out;\n"
        output_content += (f"\t\t\t\tstatus = send_patch_request(patch_{message_name_snake_cased}_client_url, "
                           f"{message_name_snake_cased}_json, {message_name_snake_cased}_json_out);\n")
        output_content += "\t\t\t\tif (status) {\n"
        output_content += f"\t\t\t\t\tstd::string modified_{message_name_snake_cased}_json;\n"
        output_content += f'\t\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_json_out.size(); ++i) {{\n'
        output_content += f"\t\t\t\t\t\tif ({message_name_snake_cased}_json_out[i] == '_' && (i + 1 < " \
                          f"{message_name_snake_cased}_json_out.size()) && {message_name_snake_cased}" \
                          f"_json_out[i + 1] == 'i' && {message_name_snake_cased}_json_out[i + 2] == 'd'" \
                           f" && ( i > 0 && !std::isalnum({message_name_snake_cased}_json_out[i - 1]))) {{\n"
        output_content += "\t\t\t\t\t\t\t// Skip the underscore if `_id` is detected\n"
        output_content += "\t\t\t\t\t\t\t// Do nothing, and let the loop increment i automatically\n"
        output_content += "\t\t\t\t\t\t} else {\n"
        output_content += "\t\t\t\t\t\t\t// Copy the character to the modified json\n"
        output_content += f"\t\t\t\t\t\t\tmodified_{message_name_snake_cased}_json += {message_name_snake_cased}" \
                          f"_json_out[i];\n"
        output_content += "\t\t\t\t\t\t}\n\t\t\t\t\t}\n"
        output_content += f"\t\t\t\t\t{message_name_snake_cased}_obj_in_n_out.Clear();\n"
        output_content += f"\t\t\t\t\tstatus =  MarketDataJSONCodec::decode_{message_name_snake_cased}(" \
                          f"{message_name_snake_cased}_obj_in_n_out, modified_{message_name_snake_cased}_json);\n"
        output_content += "\t\t\t\t\treturn status;\n"
        output_content += "\t\t\t\t} else {\n"
        output_content += (f'\t\t\t\t\tLOG_ERROR(logger_, "Error while patch {message_name}: {{}} url: {{}}", '
                           f'{message_name_snake_cased}_json, patch_{message_name_snake_cased}_client_url);\n')
        output_content += "\t\t\t\t\treturn false;\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t} else {\n"
        output_content += (f'\t\t\t\tLOG_ERROR(logger_, "Error while encoding {message_name}: {{}}", '
                           f'{message_name_snake_cased}_obj_in_n_out.DebugString());\n')
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n"
        output_content += f"\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_protected_method_handler():
        output_content: str = ""

        output_content += "\tprotected:\n"
        output_content += "\t\tconst std::string host_;\n"
        output_content += "\t\tconst std::string port_;\n"
        output_content += "\t\tstatic boost::asio::io_context io_context_;\n"
        output_content += "\t\tstatic boost::asio::ip::tcp::resolver resolver_;\n"
        output_content += "\t\tstatic boost::asio::ip::tcp::socket socket_;\n"
        output_content += "\t\tstatic boost::asio::ip::tcp::resolver::results_type result_;\n"
        output_content += "\t\tstatic inline bool static_members_initialized_ = false;\n"
        output_content += "\t\tquill::Logger* logger_ = quill::get_logger();\n\n"

        output_content += "\t\tstatic void static_init(const std::string &host, const std::string &port) {\n"
        output_content += "\t\t\tstatic std::mutex m_market_data_web_client_mutex;\n"
        output_content += "\t\t\tconst std::lock_guard<std::mutex> lock(m_market_data_web_client_mutex);\n"
        output_content += "\t\t\tif (!static_members_initialized_) {\n"
        output_content += "\t\t\t\tif (!io_context_.stopped()) {\n"
        output_content += "\t\t\t\t\t// Initialize socket and connect using the resolved results\n"
        output_content += "\t\t\t\t\tresult_ = resolver_.resolve(host, port);\n"
        output_content += "\t\t\t\t\tsocket_ = boost::asio::ip::tcp::socket(io_context_);\n"
        output_content += "\t\t\t\t\tboost::asio::connect(socket_, result_);\n"
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t\tstatic_members_initialized_ = true;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_http_request(const boost::beast::http::verb &method, const"
                           " std::string &url, const std::string &request_json, std::string &response_json_out) const {\n")
        output_content += "\t\t\t// Construct an HTTP request object with the specified HTTP method, URL, and version\n"
        output_content += ("\t\t\tboost::beast::http::request<boost::beast::http::string_body> request{method, url, 11"
                           "};\n")
        output_content += "\t\t\t// Set the host and user agent fields in the HTTP request headers\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::host, host_);\n"
        output_content += "\t\t\trequest.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);\n\n"
        output_content += "\t\t\tif (!request_json.empty()) {\n"
        output_content += '\t\t\t\trequest.set(boost::beast::http::field::content_type, "application/json");\n'
        output_content += '\t\t\t\trequest.body() = request_json;\n'
        output_content += ("\t\t\t\trequest.set(boost::beast::http::field::content_length, std::to_string("
                           "request_json.size()));\n")
        output_content += "\t\t\t\trequest.prepare_payload();\n"
        output_content += ("\t\t\t} // else not required: If there's request JSON data, set the content type, "
                           "body, and content length in the request headers\n\n")
        output_content += "\t\t\tboost::asio::ip::tcp::socket synchronous_socket(socket_.get_executor());\n"
        output_content += "\t\t\tboost::asio::connect(synchronous_socket, result_);\n"
        output_content += "\t\t\tboost::beast::http::write(synchronous_socket, request);\n\n"
        output_content += "\t\t\tboost::beast::flat_buffer buffer;\n"
        output_content += "\t\t\tboost::beast::http::response<boost::beast::http::dynamic_body> response;\n"
        output_content += "\t\t\tboost::beast::http::read(synchronous_socket, buffer, response);\n"
        output_content += "\t\t\tresponse_json_out = boost::beast::buffers_to_string(response.body().data());\n\n"

        output_content += "\t\t\tif (!response_json_out.empty()) {\n"
        output_content += "\t\t\t\treturn true;\n"
        output_content += "\t\t\t} else {\n"
        output_content += "\t\t\t\treturn false;\n"
        output_content += "\t\t\t}\n\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_get_request(const std::string &url, std::string "
                           "&response_json_out) const {\n")
        output_content += '\t\t\treturn send_http_request(boost::beast::http::verb::get, url, "", response_json_out);\n'
        output_content += "\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_get_request(const std::string &get_url, const int32_t &id, "
                           "std::string &response_json_out) const {\n")
        output_content += ('\t\t\treturn send_http_request(boost::beast::http::verb::get, get_url + "/" +'
                           ' std::to_string(id), "", response_json_out);\n')
        output_content += "\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_post_request(const std::string &post_url, const "
                           "std::string &post_json, std::string &response_json_out) const {\n")
        output_content += ("\t\t\treturn send_http_request(boost::beast::http::verb::post, post_url, post_json,"
                           " response_json_out);\n")
        output_content += "\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_patch_request(const std::string &patch_url, const std::"
                           "string &patch_json, std::string &response_json_out) const {\n")
        output_content += ("\t\t\treturn send_http_request(boost::beast::http::verb::patch, patch_url, "
                           "patch_json, response_json_out);\n")
        output_content += "\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_put_request(const std::string &put_url, const "
                           "std::string &put_json, std::string &response_json_out) const {\n")
        output_content += ("\t\t\treturn send_http_request(boost::beast::http::verb::put, put_url, put_json,"
                           " response_json_out);\n")
        output_content += "\t\t}\n\n"

        output_content += ("\t\t[[nodiscard]] bool send_delete_request(const std::string &delete_url, "
                           "const int32_t &id, std::string &response_json_out) const {\n")
        output_content += ('\t\t\treturn send_http_request(boost::beast::http::verb::delete_, delete_url + "/" + '
                           'std::to_string(id), "", response_json_out);\n')
        output_content += "\t\t}\n"
        output_content += "\t};\n\n"

        return output_content

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

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {package_name}_handler {{\n"

        output_content += f"\n\tclass {class_name}WebClient {{\n"
        output_content += "\tpublic:\n"
        output_content += f'\t\t{class_name}WebClient(const std::string &host, const std::string &port) : host_(host), ' \
                          f'port_(port) {{\n'
        output_content += "\t\t\tstatic_init(host_, port_);\n"
        output_content += "\t\t}\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppWebCLientPlugin.is_option_enabled(message, CppWebCLientPlugin.flux_msg_json_root):

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebCLientPlugin.is_option_enabled(field, "FluxFldPk"):
                        output_content += self.generate_get_max_id_handler(message_name_snake_cased)

                        output_content += self.generate_get_client(package_name, message_name, message_name_snake_cased,
                                                                   class_name)
                        output_content += self.generate_get_all_client(package_name, message_name, message_name_snake_cased,
                                                                       class_name)
                        output_content += self.generate_create_client(package_name, message_name, message_name_snake_cased,
                                                                      class_name)
                        output_content += self.generate_create_all_client(package_name, message_name, message_name_snake_cased,
                                                                          class_name)
                        output_content += self.generate_patch_client(package_name, message_name, message_name_snake_cased,
                                                                     class_name)
                        output_content += self.generate_put_client(package_name, message_name, message_name_snake_cased,
                                                                   class_name)
                        output_content += self.generate_delete_client(message_name_snake_cased)
                        break
        output_content += self.generate_protected_method_handler()

        output_content += "}\n"

        output_file_name = f"{class_name_snake_cased}_web_client.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebCLientPlugin)