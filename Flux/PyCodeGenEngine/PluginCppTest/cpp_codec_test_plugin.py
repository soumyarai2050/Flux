#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

from FluxPythonUtils.scripts.utility_functions import parse_to_int, YAMLConfigurationManager

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = (
    YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path)))


class CppCodecTestPlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_web_client_test_plugin.py files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def dependency_message_proto_msg_handler(self, file: protogen.File):
        # Adding messages from core proto files having json_root option
        project_dir = os.getenv("PROJECT_DIR")
        if project_dir is None or not project_dir:
            err_str = f"env var DBType received as {project_dir}"
            logging.exception(err_str)
            raise Exception(err_str)

        core_or_util_files: List[str] = root_flux_core_config_yaml_dict.get("core_or_util_files")

        if "ProjectGroup" in project_dir:
            project_group_flux_core_config_yaml_path = PurePath(project_dir).parent.parent / "flux_core.yaml"
            project_group_flux_core_config_yaml_dict = (
                YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
            project_grp_core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
            if project_grp_core_or_util_files:
                core_or_util_files.extend(project_grp_core_or_util_files)

        if core_or_util_files is not None:
            for dependency_file in file.dependencies:
                dependency_file_name: str = dependency_file.proto.name
                if dependency_file_name in core_or_util_files:
                    if dependency_file_name.endswith("_core.proto"):
                        if self.is_option_enabled \
                                    (file, self.flux_file_import_dependency_model):
                            msg_list = []
                            import_data = (self.get_complex_option_value_from_proto
                                           (file, self.flux_file_import_dependency_model, True))
                            for item in import_data:
                                import_file_name = item['ImportFileName']
                                import_model_name = item['ImportModelName']

                                if import_file_name == dependency_file_name:
                                    for msg in dependency_file.messages:
                                        if msg.proto.name in import_model_name:
                                            if msg not in msg_list:
                                                msg_list.append(msg)
                            self.root_message_list.extend(msg_list)
                # else not required: if dependency file name not in core_or_util_files
                # config list, avoid messages from it
        # else not required: core_or_util_files key is not in yaml dict config

    @staticmethod
    def header_generate_handler(file_name: str, class_name: str):
        output: str = ""
        output += "#pragma once\n\n"
        output += '#include "gtest/gtest.h"\n\n'
        output += f'#include "{file_name}.pb.h"\n'
        output += f'#include "../../FluxCppCore/include/json_codec.h"\n'
        output += f'#include "../CppUtilGen/{class_name}_populate_random_values.h"\n\n'
        return output

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        1000. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        file_name = str(file.proto.name).split(".")[0]

        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)
        package_name = str(file.proto.package)

        class_name_list = package_name.split("_")
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)
        output_content += f"using FluxCppCore::RootModelJsonCodec;\n"
        output_content += f"using FluxCppCore::RootModelListJsonCodec;\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppCodecTestPlugin.is_option_enabled (message, CppCodecTestPlugin.flux_msg_json_root) or \
                    CppCodecTestPlugin.is_option_enabled(message, CppCodecTestPlugin.flux_msg_json_root_time_series):
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppCodecTestPlugin.is_option_enabled(field, CppCodecTestPlugin.flux_fld_PK):
                        output_content += f"TEST({message_name}, CppCodecTest) {{\n"
                        output_content += f'\t{class_name_snake_cased}::{message_name} {message_name_snake_cased};\n'
                        output_content += f'\t{class_name_snake_cased}::{message_name} {message_name_snake_cased}_decode;\n'
                        output_content += f'\t{class_name_snake_cased}::{message_name}List {message_name_snake_cased}_list;\n'
                        output_content += f'\t{class_name_snake_cased}::{message_name}List {message_name_snake_cased}_decode_' \
                                          f'list;\n'
                        output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                        output_content += f"\tRootModelJsonCodec<market_data::{message_name}> " \
                                          f"{class_name_snake_cased}_json_codec;\n"
                        output_content += f"\tRootModelListJsonCodec<market_data::{message_name}List> " \
                                          f"{class_name_snake_cased}_list_json_codec;\n"
                        output_content += (f'\t{package_name}_handler::{class_name}PopulateRandomValues::'
                                           f'{message_name_snake_cased}({message_name_snake_cased});\n')
                        output_content += f"\tASSERT_TRUE({class_name_snake_cased}_json_codec.encode_" \
                                          f"model({message_name_snake_cased}, " \
                                          f"{message_name_snake_cased}_json));\n"
                        output_content += f"\tASSERT_TRUE({class_name_snake_cased}_json_codec.decode_" \
                                          f"model({message_name_snake_cased}_decode, " \
                                          f"{message_name_snake_cased}_json));\n"
                        output_content += f"\tASSERT_EQ({message_name_snake_cased}.DebugString(), {message_name_snake_cased}" \
                                          f"_decode.DebugString());\n\n"

                        output_content += f"\t{message_name_snake_cased}_json.clear();\n"
                        output_content += f"\tfor (int i = 0; i < 1000; ++i) {{\n"
                        output_content += (f'\t{package_name}_handler::{class_name}PopulateRandomValues::'
                                           f'{message_name_snake_cased}({message_name_snake_cased});\n')
                        output_content += f'\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}()->CopyFrom(' \
                                          f'{message_name_snake_cased});\n'
                        output_content += "\t}\n\n"

                        output_content += f"\tASSERT_TRUE({class_name_snake_cased}_list_json_codec.encode_" \
                                          f"model_list({message_name_snake_cased}_list, " \
                                          f"{message_name_snake_cased}_json));\n"
                        output_content += f"\tASSERT_TRUE({class_name_snake_cased}_list_json_codec.decode_" \
                                          f"model_list({message_name_snake_cased}_decode_list, " \
                                          f"{message_name_snake_cased}_json));\n\n"
                        # output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                        #                   f"{message_name_snake_cased}_decode_list.DebugString());\n\n"
                        output_content += "}\n\n"
                        break

        output_file_name = f"{class_name_snake_cased}_codec_test.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppCodecTestPlugin)
