#!/usr/bin/env python
from pathlib import PurePath
from typing import List
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.file_n_general_utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppWebsocketTestPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

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
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += f'#include "gtest/gtest.h"\n\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n'
        output_content += f'#include "../../FluxCppCore/include/web_socket_client.h"\n'
        output_content += f'#include "../CppUtilGen/{class_name}_web_socket_server.h"\n'
        output_content += f'#include "../CppUtilGen/{class_name}_populate_random_values.h"\n\n'
        return output_content

    def generate_multiple_model_handler(self, package_name: str, class_name: str):
        output: str = ""
        output += "TEST(MultipleModel, WebSocket) {\n"
        output += '\tconst std::string host = "127.0.0.1";\n'
        i: int = 0
        port: int = 8083
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                        output += f"\t{package_name}_handler::{class_name}PopulateRandomValues::" \
                                  f"{message_name_snake_cased}({message_name_snake_cased});\n"
                        output += f"\t{package_name}_handler::{class_name}{message_name}WebSocketServer" \
                                  f"<{package_name}::{message_name}> {message_name_snake_cased}_web_socket_server" \
                                  f"({message_name_snake_cased}, host, {port});\n"
                        port += 1
                        break

        output += "\n"
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\tstd::thread {message_name_snake_cased}_server_thread([&](){{\n"
                        output += f"\t\t{message_name_snake_cased}_web_socket_server.run();\n"
                        output += "\t});\n"
                        break
        output += "\n\t// Sleep to allow the server to start before running the tests\n"
        output += "\tstd::this_thread::sleep_for(std::chrono::seconds(1));\n"

        port = 8083
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\tWebSocketClient<{package_name}::{message_name}> {message_name_snake_cased}" \
                                  f"_web_socket_client({message_name_snake_cased}_from_server, host, {port});\n"
                        port += 1
                        break

        output += "\n"
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\tstd::thread {message_name_snake_cased}_client_thread([&](){{\n"
                        output += f"\t\t{message_name_snake_cased}_web_socket_client.run();\n"
                        output += "\t});\n\n"
                        break

        output += "\n"
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\tif ({message_name_snake_cased}_server_thread.joinable() and " \
                                  f"{message_name_snake_cased}_server_thread.joinable()) {{\n"
                        output += f"\t\t{message_name_snake_cased}_server_thread.join();\n"
                        output += f"\t\t{message_name_snake_cased}_client_thread.join();\n"
                        output += "\t}\n\n"
                        break

        output += "\n"
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\t{message_name_snake_cased}_web_socket_client.get_received_data" \
                                  f"({message_name_snake_cased}_from_server);\n"
                        break

        output += "\n"
        for message in self.root_message_list:
            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output += f"\tASSERT_EQ({message_name_snake_cased}.DebugString(), " \
                                  f"{message_name_snake_cased}_from_server.DebugString());\n"
                        break

        output += "}\n\n"
        return output

    def output_file_generate_handler(self, file: protogen.File):

        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)
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

        for message in self.root_message_list:

            if CppWebsocketTestPlugin.is_option_enabled(message, CppWebsocketTestPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebsocketTestPlugin.is_option_enabled(field, CppWebsocketTestPlugin.flux_fld_PK):
                        output_content += f"TEST({message_name}, WebSocket) {{\n"
                        output_content += f"\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output_content += f"\t{package_name}::{message_name} {message_name_snake_cased}_from_server;\n"
                        output_content += f"\t{package_name}_handler::{class_name}PopulateRandomValues::" \
                                          f"{message_name_snake_cased}({message_name_snake_cased});\n"
                        output_content += f"\t{package_name}_handler::{class_name}{message_name}WebSocketServer" \
                                          f"<{package_name}::{message_name}> {class_name_snake_cased}" \
                                          f"_web_socket_server({message_name_snake_cased});\n"
                        output_content += "\tstd::thread server_thread([&](){\n"
                        output_content += f"\t\t{class_name_snake_cased}_web_socket_server.run();\n"
                        output_content += "\t});\n\n"
                        output_content += "\t// Sleep to allow the server to start before running the tests\n"
                        output_content += "\tstd::this_thread::sleep_for(std::chrono::seconds(1));\n"
                        output_content += f"\tWebSocketClient<{package_name}::{message_name}> " \
                                          f"{class_name_snake_cased}_web_socket_client({message_name_snake_cased}" \
                                          f"_from_server);\n\n"
                        output_content += f"\tstd::thread client_thread([&](){{\n"
                        output_content += f"\t\t{class_name_snake_cased}_web_socket_client.run();\n"
                        output_content += "\t});\n\n"

                        output_content += "\tif (server_thread.joinable() and client_thread.joinable()) {\n"
                        output_content += "\t\tserver_thread.join();\n"
                        output_content += "\t\tclient_thread.join();\n"
                        output_content += "\t}\n\n"
                        output_content += f"\t{class_name_snake_cased}_web_socket_client.get_received_data" \
                                          f"({message_name_snake_cased}_from_server);\n\n"
                        output_content += f"\tASSERT_EQ({message_name_snake_cased}.DebugString(), " \
                                          f"{message_name_snake_cased}_from_server.DebugString());\n"
                        output_content += "}\n\n"

                        output_content += f"TEST({message_name}List, WebSocket) {{\n"
                        output_content += f"\t{package_name}::{message_name} {message_name_snake_cased};\n"
                        output_content += f"\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n"
                        output_content += f"\t{package_name}::{message_name}List {message_name_snake_cased}" \
                                          f"_list_from_server;\n"
                        output_content += "\tfor (int i = 0; i <= 100; ++i) {\n"
                        output_content += f"\t\t{package_name}_handler::{class_name}PopulateRandomValues::" \
                                          f"{message_name_snake_cased}({message_name_snake_cased});\n"
                        output_content += f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}()" \
                                          f"->CopyFrom({message_name_snake_cased});\n"
                        output_content += "\t}\n\n"
                        output_content += f"\t{package_name}_handler::{class_name}{message_name}ListWebSocketServer" \
                                          f"<{package_name}::{message_name}List> {class_name_snake_cased}" \
                                          f"_web_socket_server({message_name_snake_cased}_list);\n"
                        output_content += "\tstd::thread server_thread([&](){\n"
                        output_content += f"\t\t{class_name_snake_cased}_web_socket_server.run();\n"
                        output_content += "\t});\n\n"
                        output_content += "\t// Sleep to allow the server to start before running the tests\n"
                        output_content += "\tstd::this_thread::sleep_for(std::chrono::seconds(1));\n"
                        output_content += f"\tWebSocketClient<{package_name}::{message_name}List> " \
                                          f"{class_name_snake_cased}_web_socket_client({message_name_snake_cased}_list" \
                                          f"_from_server);\n\n"
                        output_content += f"\tstd::thread client_thread([&](){{\n"
                        output_content += f"\t\t{class_name_snake_cased}_web_socket_client.run();\n"
                        output_content += "\t});\n\n"

                        output_content += "\tif (server_thread.joinable() and client_thread.joinable()) {\n"
                        output_content += "\t\tserver_thread.join();\n"
                        output_content += "\t\tclient_thread.join();\n"
                        output_content += "\t}\n\n"
                        output_content += f"\t{class_name_snake_cased}_web_socket_client.get_received_data" \
                                          f"({message_name_snake_cased}_list_from_server);\n\n"
                        output_content += f"\tASSERT_EQ({message_name_snake_cased}_list.DebugString(), " \
                                          f"{message_name_snake_cased}_list_from_server.DebugString());\n"
                        output_content += "}\n\n"
                        break

        output_content += self.generate_multiple_model_handler(package_name, class_name)
        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_web_socket_test.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebsocketTestPlugin)

