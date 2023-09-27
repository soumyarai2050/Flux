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
        output += f'#include "{class_name}_max_id_handler.h"\n'
        output += f'#include "../../cpp_app/include/RandomDataGen.h"\n'
        output += '#include "../../FluxCppCore/include/base_web_client.h"\n'
        output += '#include "../../FluxCppCore/include/json_codec.h"\n'
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

        output_content += f"using FluxCppCore::RootModelWebClient;\n"
        output_content += "using FluxCppCore::RootModelListWebClient;\n"
        output_content += "using FluxCppCore::RootModelJsonCodec;\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            num_of_doc: int = 1000
            if message_name == "Dash":
                num_of_doc = 100
            else:
                num_of_doc = 1000
            if CppWebClientTestPlugin.is_option_enabled (message, CppWebClientTestPlugin.flux_msg_json_root):
                flux_msg_root_values = CppWebClientTestPlugin.get_complex_option_value_from_proto\
                    (message, CppWebClientTestPlugin.flux_msg_json_root)
                if CppWebClientTestPlugin.flux_json_root_create_field in flux_msg_root_values \
                    and CppWebClientTestPlugin.flux_json_root_create_all_field in flux_msg_root_values:
                    for field1 in message.fields:
                        field_name1: str = field1.proto.name
                        field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name1)
                        if CppWebClientTestPlugin.is_option_enabled(field1, CppWebClientTestPlugin.flux_fld_PK):
                            if message_name == "MarketDepth":
                                output_content += f"// Helper function to generate random {message_name} data\n"
                                output_content += (f"void GenerateRandom{message_name}({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}_obj_out) {{\n")
                                output_content += (f"\t{class_name}PopulateRandomValues::{message_name_snake_cased}"
                                                   f"({message_name_snake_cased}_obj_out);\n")
                                output_content += "}\n\n"

                                output_content += "// Helper function to encode Dash data to JSON and compare\n"
                                output_content += (f"void EncodeAndCompareJson({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                                output_content += (f"\t{message_name_snake_cased}_from_server.CopyFrom("
                                                   f"{message_name_snake_cased});\n\n")
                                output_content += f'\tASSERT_TRUE(client.create_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_avg_px());\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test GET operation\n"
                                output_content += (f"void TestGetOperation(const {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                                output_content += (f'\tASSERT_TRUE(client.get_client({message_name_snake_cased}'
                                                   f'_from_server, {message_name_snake_cased}.id()));\n')
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model' \
                                                  f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += (f"\tASSERT_TRUE(RootModelJsonCodec<{package_name}::{message_name}>::"
                                                   f"encode_model({message_name_snake_cased}, {message_name_snake_cased}"
                                                   f"_json, true));\n")
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test PUT operation\n"
                                output_content += (f"void TestPutOperation({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{")
                                output_content += (f"\t{package_name}::{message_name} {message_name_snake_cased}"
                                                   f"_from_server;\n")
                                output_content += (f"\t{message_name_snake_cased}_from_server.CopyFrom("
                                                   f"{message_name_snake_cased});\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f'\tASSERT_TRUE(client.put_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_avg_px());\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test PATCH operation\n"
                                output_content += (f"void TestPatchOperation({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}_for_patch, "
                                                   f"RootModelWebClient<{package_name}::{message_name}, {package_name}"
                                                   f"_handler::create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, {package_name}_handler::"
                                                   f"patch_{message_name_snake_cased}_client_url, {package_name}"
                                                   f"_handler::delete_{message_name_snake_cased}_client_url> &client, "
                                                   f"RandomDataGen &random_data_gen) {{")

                                output_content += (f"\t{package_name}::{message_name} {message_name_snake_cased}"
                                                   f"_from_server;\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n\n"

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
                                output_content += f'\n\tASSERT_TRUE(client.patch_' \
                                                  f'client({message_name_snake_cased}_for_patch));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_for_patch.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_for_patch.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_for_patch.cumulative_avg_px());\n\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_for_patch, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += "}\n\n"

                                output_content += "// Helper function to test DELETE operation\n"
                                output_content += (f"void TestDeleteOperation(const int32_t "
                                                   f"{message_name_snake_cased}_id, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{\n")
                                output_content += '\tstd::string json = R"({"msg":"Deletion Successful","id":)";\n'
                                output_content += (f"\tjson += std::to_string({message_name_snake_cased}_id); // "
                                                   f"Convert int to string and append\n")
                                output_content += '\tjson += R"(})";\n'
                                output_content += (f"\tauto delete_response = client.delete_client("
                                                   f"{message_name_snake_cased}_id);\n")
                                output_content += "\tASSERT_EQ(delete_response, json);\n\n"
                                output_content += "}\n\n"

                                output_content += f'TEST({message_name}TestSuite, WebClient) {{\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}' \
                                                  f'_from_server;\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}' \
                                                  f'_list_from_server;\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_for_patch;\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}' \
                                                  f'_list_for_patch;\n'
                                output_content += f'\tRandomDataGen random_data_gen;\n'
                                # output_content += (f'\t{package_name}_handler::{class_name}WebClient '
                                #                    f'{class_name_snake_cased}_web_client(host, port);\n\n')
                                output_content += f"\tRootModelWebClient<{package_name}::{message_name}, " \
                                                  f"{package_name}_handler::create_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> {class_name_snake_cased}" \
                                                  f"_web_client(host, port);\n"

                                output_content += f"\tRootModelListWebClient<{package_name}::{message_name}List, " \
                                                  f"{package_name}_handler::create_all_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_all_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"all_{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"all_{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> " \
                                                  f"web_client(host, port);\n\n"

                                output_content += "\t// Test CREATE operation\n"
                                output_content += f"\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += (f"\tEncodeAndCompareJson({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test GET operation\n"
                                output_content += (f"\tTestGetOperation({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test PUT operation\n"
                                output_content += (f"\tTestPutOperation({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test PATCH operation\n"
                                output_content += (f"\tTestPatchOperation({message_name_snake_cased}, "
                                                   f"{message_name_snake_cased}_for_patch, "
                                                   f"{package_name}_web_client, random_data_gen);\n\n")
                                output_content += "\t// Test DELETE operation\n"
                                output_content += (f"\tTestDeleteOperation({message_name_snake_cased}.id(), "
                                                   f"{package_name}_web_client);\n\n")

                                output_content += "\t// Test CREATE operation for a list\n"
                                output_content += f"\tfor (int i = 1; i <= {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += f"\t\t{message_name_snake_cased}.set_id(i);\n"
                                output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}" \
                                                  f"()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n\n"
                                output_content += f"\t{message_name_snake_cased}_list_from_server.CopyFrom(" \
                                                  f"{message_name_snake_cased}_list);\n"
                                output_content += f"\tASSERT_TRUE(web_client.create_client({message_name_snake_cased}" \
                                                  f"_list_from_server));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_from_server.DebugString());\n\n"

                                output_content += f"\t{message_name_snake_cased}_list.Clear();\n"
                                output_content += f"\tfor (int i = 1; i <= {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += f"\t\t{message_name_snake_cased}.set_id(i);\n"
                                output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}" \
                                                  f"()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n\n"
                                output_content += f"\t{message_name_snake_cased}_list_from_server.CopyFrom" \
                                                  f"({message_name_snake_cased}_list);\n"
                                output_content += f"\tASSERT_TRUE(web_client.put_client({message_name_snake_cased}" \
                                                  f"_list_from_server));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_from_server.DebugString());\n\n"

                                output_content += f"\t{message_name_snake_cased}.Clear();\n"
                                output_content += f"\tfor (int i = 1; i <= {num_of_doc}; ++i) {{\n"
                                for field in message.fields:
                                    field_name: str = field.proto.name
                                    field_type_message: None | protogen.Message = field.message
                                    field_type: str = field.kind.name.lower()
                                    if field_type_message is None:
                                        if field_name != "id" and field.cardinality.name.lower() != "bool" and field_type != "enum":
                                            if not CppWebClientTestPlugin.is_option_enabled(field, CppWebClientTestPlugin.
                                                    flux_fld_val_is_datetime):
                                                output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(' \
                                                                  f'random_data_gen.get_random_{field_type}());\n'
                                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                                  f'{message_name_snake_cased}(i - 1)->set_{field_name}(' \
                                                                  f'{message_name_snake_cased}.{field_name}());\n'
                                        elif field.cardinality.name.lower() != "bool" and field_type != "enum":

                                            output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(i);\n'
                                output_content += f"\t\t{message_name_snake_cased}_list_for_patch.add_" \
                                                  f"{message_name_snake_cased}()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n"

                                output_content += f"\tASSERT_TRUE(web_client.patch_client({message_name_snake_cased}" \
                                                  f"_list_for_patch));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_for_patch.DebugString());\n\n"

                                output_content += f"\tfor (int i = 1; i < {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tTestDeleteOperation(i, {package_name}_web_client);\n"
                                output_content += "\t}\n\n"
                                output_content += "}\n\n"
                            else:
                                output_content += f"// Helper function to generate random {message_name} data\n"
                                output_content += (f"void GenerateRandom{message_name}({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}_obj_out) {{\n")
                                output_content += (f"\t{class_name}PopulateRandomValues::{message_name_snake_cased}"
                                                   f"({message_name_snake_cased}_obj_out);\n")
                                output_content += "}\n\n"

                                output_content += "// Helper function to encode Dash data to JSON and compare\n"
                                output_content += (f"void EncodeAndCompareJson(const {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                                output_content += (f"\t{message_name_snake_cased}_from_server.CopyFrom("
                                                   f"{message_name_snake_cased});\n\n")
                                output_content += f'\tASSERT_TRUE(client.create_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test GET operation\n"
                                output_content += (f"void TestGetOperation(const {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                                output_content += (f'\tASSERT_TRUE(client.get_client({message_name_snake_cased}'
                                                   f'_from_server, {message_name_snake_cased}.id()));\n')
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model' \
                                                  f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += (f"\tASSERT_TRUE(RootModelJsonCodec<{package_name}::{message_name}>::"
                                                   f"encode_model({message_name_snake_cased}, {message_name_snake_cased}"
                                                   f"_json, true));")
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test PUT operation\n"
                                output_content += (f"void TestPutOperation(const {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{")
                                output_content += (f"\t{package_name}::{message_name} {message_name_snake_cased}"
                                                   f"_from_server;\n")
                                output_content += (f"\t{message_name_snake_cased}_from_server.CopyFrom("
                                                   f"{message_name_snake_cased});\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                                output_content += f'\tASSERT_TRUE(client.put_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'
                                output_content += "}\n\n"

                                output_content += "// Helper function to test PATCH operation\n"
                                output_content += (f"void TestPatchOperation({package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}, {package_name}::{message_name} "
                                                   f"&{message_name_snake_cased}_for_patch, "
                                                   f"RootModelWebClient<{package_name}::{message_name}, {package_name}"
                                                   f"_handler::create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, {package_name}_handler::"
                                                   f"patch_{message_name_snake_cased}_client_url, {package_name}"
                                                   f"_handler::delete_{message_name_snake_cased}_client_url> &client, "
                                                   f"RandomDataGen &random_data_gen) {{")

                                output_content += (f"\t{package_name}::{message_name} {message_name_snake_cased}"
                                                   f"_from_server;\n")
                                output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                                output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n\n"
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

                                output_content += f'\tASSERT_TRUE(client.patch_' \
                                                  f'client({message_name_snake_cased}_for_patch));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_for_patch, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += "}\n\n"

                                output_content += "// Helper function to test DELETE operation\n"
                                output_content += (f"void TestDeleteOperation(const int32_t "
                                                   f"{message_name_snake_cased}_id, RootModelWebClient<"
                                                   f"{package_name}::{message_name}, {package_name}_handler::"
                                                   f"create_{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::get_{message_name_snake_cased}_client_url,"
                                                   f" {package_name}_handler::get_{message_name_snake_cased}"
                                                   f"_max_id_client_url, {package_name}_handler::put_"
                                                   f"{message_name_snake_cased}_client_url, "
                                                   f"{package_name}_handler::patch_{message_name_snake_cased}"
                                                   f"_client_url, {package_name}_handler::delete_"
                                                   f"{message_name_snake_cased}_client_url> &client) {{\n")
                                output_content += '\tstd::string json = R"({"msg":"Deletion Successful","id":)";\n'
                                output_content += (f"\tjson += std::to_string({message_name_snake_cased}_id); // "
                                                   f"Convert int to string and append\n")
                                output_content += '\tjson += R"(})";\n'
                                output_content += (f"\tauto delete_response = client.delete_client("
                                                   f"{message_name_snake_cased}_id);\n")
                                output_content += "\tASSERT_EQ(delete_response, json);\n\n"
                                output_content += "}\n\n"

                                output_content += f'TEST({message_name}TestSuite, WebClient) {{\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}' \
                                                  f'_from_server;\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}' \
                                                  f'_list_from_server;\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_for_patch;\n'
                                output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}' \
                                                  f'_list_for_patch;\n'
                                output_content += f'\tRandomDataGen random_data_gen;\n'
                                # output_content += (f'\t{package_name}_handler::{class_name}WebClient '
                                #                    f'{class_name_snake_cased}_web_client(host, port);\n\n')
                                output_content += f"\tRootModelWebClient<{package_name}::{message_name}, " \
                                                  f"{package_name}_handler::create_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> {class_name_snake_cased}" \
                                                  f"_web_client(host, port);\n"

                                output_content += f"\tRootModelListWebClient<{package_name}::{message_name}List, " \
                                                  f"{package_name}_handler::create_all_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_all_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"all_{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"all_{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> " \
                                                  f"web_client(host, port);\n\n"

                                output_content += "\t// Test CREATE operation\n"
                                output_content += f"\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += (f"\tEncodeAndCompareJson({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test GET operation\n"
                                output_content += (f"\tTestGetOperation({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test PUT operation\n"
                                output_content += (f"\tTestPutOperation({message_name_snake_cased}, {package_name}"
                                                   f"_web_client);\n\n")
                                output_content += "\t// Test PATCH operation\n"
                                output_content += (f"\tTestPatchOperation({message_name_snake_cased}, "
                                                   f"{message_name_snake_cased}_for_patch, "
                                                   f"{package_name}_web_client, random_data_gen);\n\n")
                                output_content += "\t// Test DELETE operation\n"
                                output_content += (f"\tTestDeleteOperation({message_name_snake_cased}.id(), "
                                                   f"{package_name}_web_client);\n\n")

                                output_content += "\t// Test CREATE operation for a list\n"
                                output_content += f"\tfor (int i = 1; i < {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += f"\t\t{message_name_snake_cased}.set_id(i);\n"
                                output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}" \
                                                  f"()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n\n"
                                output_content += f"\t{message_name_snake_cased}_list_from_server.CopyFrom(" \
                                                  f"{message_name_snake_cased}_list);\n"
                                output_content += f"\tASSERT_TRUE(web_client.create_client({message_name_snake_cased}" \
                                                  f"_list_from_server));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_from_server.DebugString());\n\n"

                                output_content += f"\t{message_name_snake_cased}_list.Clear();\n"
                                output_content += f"\tfor (int i = 1; i < {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tGenerateRandom{message_name}({message_name_snake_cased});\n"
                                output_content += f"\t\t{message_name_snake_cased}.set_id(i);\n"
                                output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}" \
                                                  f"()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n\n"
                                output_content += f"\t{message_name_snake_cased}_list_from_server.CopyFrom" \
                                                  f"({message_name_snake_cased}_list);\n"
                                output_content += f"\tASSERT_TRUE(web_client.put_client({message_name_snake_cased}" \
                                                  f"_list_from_server));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_from_server.DebugString());\n\n"

                                output_content += f"\t{message_name_snake_cased}.Clear();\n"
                                output_content += f"\tfor (int i = 1; i < {num_of_doc}; ++i) {{\n"
                                for field in message.fields:
                                    field_name: str = field.proto.name
                                    field_type_message: None | protogen.Message = field.message
                                    field_type: str = field.kind.name.lower()
                                    if field_type_message is None:
                                        if field_name != "id" and field.cardinality.name.lower() != "bool" and field_type != "enum":
                                            if not CppWebClientTestPlugin.is_option_enabled(field, CppWebClientTestPlugin.
                                                    flux_fld_val_is_datetime):
                                                output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(' \
                                                                  f'random_data_gen.get_random_{field_type}());\n'
                                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                                  f'{message_name_snake_cased}(i - 1)->set_{field_name}(' \
                                                                  f'{message_name_snake_cased}.{field_name}());\n'
                                        elif field.cardinality.name.lower() != "bool" and field_type != "enum":

                                            output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(i);\n'
                                output_content += f"\t\t{message_name_snake_cased}_list_for_patch.add_" \
                                                  f"{message_name_snake_cased}()->CopyFrom({message_name_snake_cased});\n"
                                output_content += "\t}\n"

                                output_content += f"\tASSERT_TRUE(web_client.patch_client({message_name_snake_cased}" \
                                                  f"_list_for_patch));\n"
                                output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                                  f"{message_name_snake_cased}_list_for_patch.DebugString());\n\n"
                                output_content += f"\tfor (int i = 1; i < {num_of_doc}; ++i) {{\n"
                                output_content += f"\t\tTestDeleteOperation(i, {package_name}_web_client);\n"
                                output_content += "\t}\n\n"

                                output_content += "}\n\n"
                            break
                elif CppWebClientTestPlugin.flux_json_root_create_field in flux_msg_root_values:
                    for field1 in message.fields:
                        field_name1: str = field1.proto.name
                        field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name1)
                        if CppWebClientTestPlugin.is_option_enabled(field1, CppWebClientTestPlugin.flux_fld_PK):
                            if message_name == "MarketDepth":
                                output_content += f'TEST({message_name}TestSuite, WebClient) {{\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n'
                                output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_for_patch;\n'
                                output_content += f'\tstd::string {message_name_snake_cased}_json;\n'
                                output_content += f'\tstd::string {message_name_snake_cased}_json_from_server;\n'
                                output_content += f'\tRandomDataGen random_data_gen;\n'
                                # output_content += (f'\t{package_name}_handler::{class_name}WebClient {class_name_snake_cased}'
                                #                    f'_web_client(host, port);\n\n')
                                output_content += f"\tRootModelWebClient<{package_name}::{message_name}, " \
                                                  f"{package_name}_handler::create_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> {class_name_snake_cased}" \
                                                  f"_web_client(host, port);\n\n"
                                output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}' \
                                                  f'({message_name_snake_cased});\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.create_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_avg_px());\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\tauto {message_name_snake_cased}_id = {message_name_snake_cased}.id();\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.get_' \
                                                  f'client({message_name_snake_cased}_from_server, {message_name_snake_cased}_id));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model' \
                                                  f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json.clear();\n\n'

                                # output_content += (f"\t{package_name}_handler::{class_name}MaxIdHandler::update_"
                                #                    f"{message_name_snake_cased}_max_id(market_data_web_client);\n")
                                output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}(' \
                                                  f'{message_name_snake_cased});\n'
                                output_content += f'\t{message_name_snake_cased}.set_id({message_name_snake_cased}_id);\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.put_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_avg_px());\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                for field in message.fields:
                                    field_name: str = field.proto.name
                                    field_type_message: None | protogen.Message = field.message
                                    field_type: str = field.kind.name.lower()
                                    if field_type_message is None:
                                        if field_name != "id" and field.cardinality.name.lower() != "bool":
                                            if not CppWebClientTestPlugin.is_option_enabled(field,
                                                                                            CppWebClientTestPlugin.
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
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_notional({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_notional());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_qty({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_qty());\n'
                                output_content += f'\t{message_name_snake_cased}.set_cumulative_avg_px({message_name_snake_cased}' \
                                                  f'_from_server.cumulative_avg_px());\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\tstd::string json = R"({{"msg":"Deletion Successful","id":)";\n'
                                output_content += (f'\tjson += std::to_string({message_name_snake_cased}.id()); // '
                                                   f'Convert int to string and append\n')
                                output_content += f'\tjson += R"(}})";\n\n'

                                output_content += f'\tauto delete_response = {class_name_snake_cased}_web_client.delete_' \
                                                  f'client({message_name_snake_cased}_id);\n'
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
                                # output_content += (f'\t{package_name}_handler::{class_name}WebClient '
                                #                    f'{class_name_snake_cased}_web_client(host, port);\n\n')
                                output_content += f"\tRootModelWebClient<{package_name}::{message_name}, " \
                                                  f"{package_name}_handler::create_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}_client_url, " \
                                                  f"{package_name}_handler::get_{message_name_snake_cased}" \
                                                  f"_max_id_client_url, {package_name}_handler::put_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                                  f"{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                                  f"delete_{message_name_snake_cased}_client_url> {class_name_snake_cased}" \
                                                  f"_web_client(host, port);\n\n"
                                output_content += f'\t{package_name}_handler::{class_name}PopulateRandomValues::{message_name_snake_cased}' \
                                                  f'({message_name_snake_cased});\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.create_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\tauto {message_name_snake_cased}_id = {message_name_snake_cased}.id();\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.get_' \
                                                  f'client({message_name_snake_cased}_from_server, {message_name_snake_cased}_id));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model' \
                                                  f'({message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\t{message_name_snake_cased}_from_server.Clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json_from_server.clear();\n'
                                output_content += f'\t{message_name_snake_cased}_json.clear();\n\n'

                                # output_content += (f"\t{package_name}_handler::{class_name}MaxIdHandler::update_"
                                #                    f"{message_name_snake_cased}_max_id({class_name_snake_cased}_web_client);\n")
                                output_content += (f'\t{package_name}_handler::{class_name}PopulateRandomValues::'
                                                   f'{message_name_snake_cased}({message_name_snake_cased});\n')
                                output_content += f'\t{message_name_snake_cased}.set_id({message_name_snake_cased}_id);\n'
                                output_content += f'\t{message_name_snake_cased}_from_server.CopyFrom({message_name_snake_cased});\n\n'
                                output_content += f'\tASSERT_TRUE({class_name_snake_cased}_web_client.put_' \
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                for field in message.fields:
                                    field_name: str = field.proto.name
                                    field_type_message: None | protogen.Message = field.message
                                    field_type: str = field.kind.name.lower()
                                    if field_type_message is None:
                                        if field_name != "id" and field.cardinality.name.lower() != "bool" and field_type != "enum":
                                            if not CppWebClientTestPlugin.is_option_enabled(field,
                                                                                            CppWebClientTestPlugin.
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
                                                  f'client({message_name_snake_cased}_from_server));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}_from_server, {message_name_snake_cased}' \
                                                  f'_json_from_server, true));\n'
                                output_content += f'\tASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::encode_model(' \
                                                  f'{message_name_snake_cased}, {message_name_snake_cased}_json, true));\n'
                                output_content += f'\tASSERT_EQ({message_name_snake_cased}_json_from_server, ' \
                                                  f'{message_name_snake_cased}_json);\n\n'

                                output_content += f'\tstd::string json = R"({{"msg":"Deletion Successful","id":)";\n'
                                output_content += (f'\tjson += std::to_string({message_name_snake_cased}.id()); // '
                                                   f'Convert int to string and append\n')
                                output_content += f'\tjson += R"(}})";\n\n'

                                output_content += f'\tauto delete_response = {class_name_snake_cased}_web_client.delete_' \
                                                  f'client({message_name_snake_cased}_id);\n'
                                output_content += "\tASSERT_EQ(delete_response, json);\n"
                                output_content += "}\n\n"
                            break

            elif CppWebClientTestPlugin.is_option_enabled\
                (message, CppWebClientTestPlugin.flux_msg_json_root_time_series):
                for field1 in message.fields:
                    field_name1: str = field1.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name1)
                    if CppWebClientTestPlugin.is_option_enabled(field1, CppWebClientTestPlugin.flux_fld_PK):
                        output_content += f"TEST({message_name}TestSuite, WebClient) {{\n"
                        output_content += f"\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output_content += f"\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n"
                        output_content += f"\t{package_name}::{message_name}List {message_name_snake_cased}" \
                                          f"_list_from_server;\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_json_from_server;\n"
                        output_content += f"\tRootModelListWebClient<{package_name}::{message_name}List, " \
                                          f"{package_name}_handler::create_all_{message_name_snake_cased}_client_url, " \
                                          f"{package_name}_handler::get_all_{message_name_snake_cased}_client_url, " \
                                          f"{package_name}_handler::get_{message_name_snake_cased}" \
                                          f"_max_id_client_url, {package_name}_handler::put_" \
                                          f"all_{message_name_snake_cased}_client_url, {package_name}_handler::patch_" \
                                          f"all_{message_name_snake_cased}_client_url, {package_name}_handler::" \
                                          f"delete_all_{message_name_snake_cased}_client_url> " \
                                          f"web_client(host, port);\n\n"

                        output_content += "\tfor (int i = 1; i < 1000; ++i) {\n"
                        output_content += f"\t\t{package_name}_handler::{class_name}PopulateRandomValues::" \
                                          f"{message_name_snake_cased}({message_name_snake_cased});\n"
                        output_content += f"\t\t{message_name_snake_cased}.set_id(i);\n"
                        output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}()" \
                                          f"->CopyFrom({message_name_snake_cased});\n"
                        output_content += "\t}\n\n"

                        output_content += f"\t{message_name_snake_cased}_list_from_server.CopyFrom" \
                                          f"({message_name_snake_cased}_list);\n"
                        output_content += f"\tASSERT_TRUE(web_client.create_client({message_name_snake_cased}" \
                                          f"_list_from_server));\n"
                        output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                          f"{message_name_snake_cased}_list_from_server.DebugString());\n"
                        output_content += '\tstd::string json = R"({"msg":"Deletion Successful","id":[)";\n\n'
                        output_content += f"\tfor (int i = 0; i < {message_name_snake_cased}_list." \
                                          f"{message_name_snake_cased}_size(); ++i) {{\n"
                        output_content += f"\t\tjson += std::to_string({message_name_snake_cased}_list." \
                                          f"{message_name_snake_cased}(i).id());\n"
                        output_content += '\t\tjson += ",";\n'
                        output_content += "\t}\n\n"

                        output_content += "\tjson.pop_back();\n"
                        output_content += '\tjson += R"(]})";\n\n'

                        output_content += "\tstd::string delete_response = web_client.delete_client();\n"
                        output_content += "\tASSERT_EQ(delete_response, json);\n"
                        output_content += "}\n\n"

        output_file_name = f"{class_name_snake_cased}_web_client_test.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebClientTestPlugin)
