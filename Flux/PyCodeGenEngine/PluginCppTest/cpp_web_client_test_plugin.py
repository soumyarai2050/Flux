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


class CppWebClientTestPlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_web_client_test_plugin.py files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    @staticmethod
    def header_generate_handler(file_name: str, class_name: str):
        output: str = ""
        output += "#pragma once\n\n"
        output += '#include "gtest/gtest.h"\n\n'
        output += f'#include "{file_name}.pb.h"\n'
        output += f'#include "{class_name}_web_client.h"\n'
        output += f'#include "{class_name}_max_id_handler.h"\n'
        output += f'#include "../../cpp_app/include/RandomDataGen.h"\n'
        output += f'#include "../CppUtilGen/{class_name}_populate_random_values.h"\n\n'
        return output

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        file_name = str(file.proto.name).split(".")[0]

        self.get_all_root_message(file.messages)
        package_name = str(file.proto.package)

        class_name_list = package_name.split("_")
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)
        output_content += 'const std::string host = "127.0.0.1";\n'
        output_content += 'const std::string port = "8040";\n'

        output_content += f"using {package_name}_handler::{class_name}JSONCodec;\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppWebClientTestPlugin.is_option_enabled (message, CppWebClientTestPlugin.flux_msg_json_root):
                for field1 in message.fields:
                    field_name1: str = field1.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name1)
                    if CppWebClientTestPlugin.is_option_enabled(field1, "FluxFldPk"):
                        if message_name == "MarketDepth":
                            output_content += f'TEST({message_name}TestSuite, WebClient) {{\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_for_patch;\n'
                            output_content += f'\tstd::string {message_name_snake_cased}_json;\n'
                            output_content += f'\tstd::string {message_name_snake_cased}_json_from_server;\n'
                            output_content += f'\tRandomDataGen random_data_gen;\n'
                            output_content += (f'\t{package_name}_handler::{class_name}WebClient {class_name_snake_cased}'
                                               f'_web_client(host, port);\n\n')
                            output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}' \
                                              f'({message_name_snake_cased});\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.create_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                              f'_from_server.cumulative_notional());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                              f'_from_server.cumulative_qty());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                              f'_from_server.cumulative_avg_px());\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\tauto {message_name_snake_cased}_id = {message_name_snake_cased}.id();\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.get_{message_name_snake_cased}' \
                                              f'_client({message_name_snake_cased}_from_server, {message_name_snake_cased}_id));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}' \
                                              f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json.clear();\n\n'

                            output_content += (f"\t{package_name}_handler::{class_name}MaxIdHandler::update_"
                                               f"{message_name_snake_cased}_max_id(market_data_web_client);\n")
                            output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased});\n'
                            output_content += f'\t{message_name_snake_cased}.set_id({message_name_snake_cased}_id);\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.put_{message_name_snake_cased}' \
                                              f'_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                              f'_from_server.cumulative_notional());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                              f'_from_server.cumulative_qty());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                              f'_from_server.cumulative_avg_px());\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            for field in message.fields:
                                field_name: str = field.proto.name
                                field_type_message: None | protogen.Message = field.message
                                field_type: str = field.kind.name.lower()
                                if field_type_message is None:
                                    if field_name != "id" and field.cardinality.name.lower() != "bool":
                                        if not CppWebClientTestPlugin.is_option_enabled(field, CppWebClientTestPlugin.
                                                                                        flux_fld_val_is_datetime):
                                            if field_type != "enum":
                                                output_content += f'\t{message_name_snake_cased}_for_patch.set_{field_name}(' \
                                                                  f'random_data_gen.get_random_{field_type}());\n'
                                                output_content += f'\t{message_name_snake_cased}.set_{field_name}(' \
                                                                  f'{message_name_snake_cased}_for_patch.{field_name}());\n'
                                    else:

                                        output_content += f'\t{message_name_snake_cased}_for_patch.set_{field_name}(' \
                                                          f'{message_name_snake_cased}.{field_name}());\n'

                            output_content += f'\n\t{message_name_snake_cased}_from_server.CopyFrom(' \
                                              f'{message_name_snake_cased}_for_patch);\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.patch_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                              f'_from_server.cumulative_notional());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                              f'_from_server.cumulative_qty());\n'
                            output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                              f'_from_server.cumulative_avg_px());\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\tstd::string json = R"({{"msg":"Deletion Successful","id":)";\n'
                            output_content += (f'\tjson += std::to_string({message_name_snake_cased}.id()); // '
                                               f'Convert int to string and append\n')
                            output_content += f'\tjson += R"(}})";\n\n'

                            output_content += f'\tauto delete_response = {class_name_snake_cased}_web_client.delete_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_id);\n'
                            output_content += "\tASSERT_EQ(delete_response, json);\n"
                            output_content += "}\n\n"
                        else:
                            output_content += f'TEST({message_name}TestSuite, WebClient) {{\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n'
                            output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_for_patch;\n'
                            output_content += f'\tstd::string {message_name_snake_cased}_json;\n'
                            output_content += f'\tstd::string {message_name_snake_cased}_json_from_server;\n'
                            output_content += f'\tRandomDataGen random_data_gen;\n'
                            output_content += (f'\t{package_name}_handler::{class_name}WebClient '
                                               f'{class_name_snake_cased}_web_client(host, port);\n\n')
                            output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}' \
                                              f'({message_name_snake_cased});\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.create_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\tauto {message_name_snake_cased}_id = {message_name_snake_cased}.id();\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.get_{message_name_snake_cased}' \
                                              f'_client({message_name_snake_cased}_from_server, {message_name_snake_cased}_id));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}' \
                                              f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                            output_content += f'\t{message_name_snake_cased}_json.clear();\n\n'

                            output_content += (f"\t{package_name}_handler::{class_name}MaxIdHandler::update_"
                                               f"{message_name_snake_cased}_max_id({class_name_snake_cased}_web_client);\n")
                            output_content += (f'\t{package_name}_handler::{class_name}PopulateRandomValues::'
                                               f'{message_name_snake_cased}({message_name_snake_cased});\n')
                            output_content += f'\t{message_name_snake_cased}.set_id({message_name_snake_cased}_id);\n'
                            output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.put_{message_name_snake_cased}' \
                                              f'_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            for field in message.fields:
                                field_name: str = field.proto.name
                                field_type_message: None | protogen.Message = field.message
                                field_type: str = field.kind.name.lower()
                                if field_type_message is None:
                                    if field_name != "id" and field.cardinality.name.lower() != "bool" and field_type != "enum":
                                        if not CppWebClientTestPlugin.is_option_enabled(field, CppWebClientTestPlugin.
                                                                                        flux_fld_val_is_datetime):
                                            output_content += f'\t{message_name_snake_cased}_for_patch.set_{field_name}(' \
                                                              f'random_data_gen.get_random_{field_type}());\n'
                                            output_content += f'\t{message_name_snake_cased}.set_{field_name}(' \
                                                              f'{message_name_snake_cased}_for_patch.{field_name}());\n'
                                    else:

                                        output_content += f'\t{message_name_snake_cased}_for_patch.set_{field_name}(' \
                                                          f'{message_name_snake_cased}.{field_name}());\n'

                            output_content += f'\n\t{message_name_snake_cased}_from_server.CopyFrom(' \
                                              f'{message_name_snake_cased}_for_patch);\n'
                            output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.patch_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_from_server));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                              f'_json_from_server, true));\n'
                            output_content += f'\tASSERT_TRUE({class_name}JSONCodec::encode_{message_name_snake_cased}(' \
                                              f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                            output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                              f'{message_name_snake_cased}_json);\n\n'

                            output_content += f'\tstd::string json = R"({{"msg":"Deletion Successful","id":)";\n'
                            output_content += (f'\tjson += std::to_string({message_name_snake_cased}.id()); // '
                                               f'Convert int to string and append\n')
                            output_content += f'\tjson += R"(}})";\n\n'

                            output_content += f'\tauto delete_response = {class_name_snake_cased}_web_client.delete_' \
                                              f'{message_name_snake_cased}_client({message_name_snake_cased}_id);\n'
                            output_content += "\tASSERT_EQ(delete_response, json);\n"
                            output_content += "}\n\n"
                        break

        output_file_name = f"{class_name_snake_cased}_web_client_test.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebClientTestPlugin)
