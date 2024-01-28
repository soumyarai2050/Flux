#!/usr/bin/env python
from pathlib import PurePath
from typing import List
import os
import time
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppWebSocketServerUtilPlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to project include generate from proto schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    @staticmethod
    def header_generate_handler(package_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += f'#include "{package_name}_web_socket_server.h"\n'
        output_content += f'#include "../CppUtilGen/{package_name}_populate_random_values.h"\n\n'
        return output_content

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

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)
        output_content: str = ""
        package_name = str(file.proto.package)
        output_content += self.header_generate_handler(package_name)

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += f"namespace {package_name}_handler{{\n\n"
        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppWebSocketServerUtilPlugin.is_option_enabled(message, CppWebSocketServerUtilPlugin.flux_msg_json_root):

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebSocketServerUtilPlugin.is_option_enabled(field, CppWebSocketServerUtilPlugin.flux_fld_PK):
                        output_content += f"\tvoid prepare_{message_name_snake_cased}_list_obj({package_name}::{message_name}List " \
                                          f"&r_{message_name_snake_cased}_list_obj_in_n_out, const int32_t size = 5) {{\n"
                        output_content += f"\t\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output_content += "\t\tfor (int i = 0; i < size; ++i) {\n"
                        output_content += f"\t\t\t{class_name}PopulateRandomValues::{message_name_snake_cased}" \
                                          f"({message_name_snake_cased});\n"
                        output_content += f"\t\t\tr_{message_name_snake_cased}_list_obj_in_n_out.add_" \
                                          f"{message_name_snake_cased}()->CopyFrom({message_name_snake_cased});\n"
                        output_content += "\t\t}\n\t}\n\n"

                        output_content += f"\tvoid send_{message_name_snake_cased}_to_web_client() {{\n"
                        output_content += f"\t\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output_content += f"\t\t{class_name}PopulateRandomValues::{message_name_snake_cased}" \
                                          f"({message_name_snake_cased});\n"
                        output_content += f"\t\t{class_name}{message_name}WebSocketServer<{package_name}::{message_name}>" \
                                          f" {package_name}_web_socket_server({message_name_snake_cased});\n"
                        output_content += f"\t\t{package_name}_web_socket_server.run();\n"
                        output_content += f"\t\t{class_name}PopulateRandomValues::{message_name_snake_cased}" \
                                          f"({message_name_snake_cased});\n"
                        output_content += f"\t\t{package_name}_web_socket_server.NewClientCallBack(" \
                                          f"{message_name_snake_cased}, -1);\n"
                        output_content += "\t}\n\n"

                        output_content += f"\tvoid send_{message_name_snake_cased}_list_to_web_client() {{\n"
                        output_content += f"\t\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n"
                        output_content += f"\t\tprepare_{message_name_snake_cased}_list_obj({message_name_snake_cased}_list);\n"
                        output_content += f"\t\t{class_name}{message_name}ListWebSocketServer<{package_name}::{message_name}List>" \
                                          f" {package_name}_web_socket_server({message_name_snake_cased}_list);\n"
                        output_content += f"\t\t{package_name}_web_socket_server.run();\n"
                        output_content += f"\t\tprepare_{message_name_snake_cased}_list_obj({message_name_snake_cased}_list);\n"
                        output_content += f"\t\t{package_name}_web_socket_server.NewClientCallBack(" \
                                          f"{message_name_snake_cased}_list, -1);\n"
                        output_content += "\t}\n\n"
                        break

        output_content += "}\n\n"
        output_file_name = f"{package_name}_web_socket_server_util.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebSocketServerUtilPlugin)
