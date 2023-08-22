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
from Flux.PyCodeGenEngine.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin


class CppWebSocketServerPlugin(BaseProtoPlugin):
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
        output_content += f'#include "../../FluxCppCore/include/web_socket_server.h"\n'
        output_content += f'#include "../../FluxCppCore/include/json_codec.h"\n'
        output_content += f'#include "../../generated/ProtoGenCc/market_data_service.pb.h"\n\n'
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
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
            if CppWebSocketServerPlugin.is_option_enabled(message, CppWebSocketServerPlugin.flux_msg_json_root):
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppWebSocketServerPlugin.is_option_enabled(field, CppWebSocketServerPlugin.flux_fld_PK):
                        output_content += "\ttemplate <typename UserDataType>\n"
                        output_content += f"\tclass {class_name}{message_name}WebSocketServer : public " \
                                          f"FluxCppCore::WebSocketServer<{package_name}::{message_name}, " \
                                          f"{package_name}::{message_name}List, UserDataType> {{\n"
                        output_content += f"\t\tusing BaseClass = FluxCppCore::WebSocketServer<{package_name}::{message_name}, " \
                                          f"{package_name}::{message_name}List, UserDataType>;\n"
                        output_content += "\tpublic:\n"
                        output_content += f'\t\texplicit {class_name}{message_name}WebSocketServer(UserDataType ' \
                                          f'&user_data, const std::string k_host = "127.0.0.1", const ' \
                                          f'int32_t k_web_socket_server_port = 8083, const int32_t k_read_timeout = ' \
                                          f'60, quill::Logger *p_logger = quill::get_logger()) : ' \
                                          f'BaseClass(user_data, k_host, k_web_socket_server_port, ' \
                                          f'k_read_timeout, p_logger) {{}}\n\n'

                        output_content += "\t\tbool NewClientCallBack(UserDataType &user_data, int16_t " \
                                          "new_client_web_socket_id) override {\n"
                        output_content += f"\t\t\t{package_name}::{message_name} root_model_obj = user_data;\n\n"
                        output_content += "\t\t\t// Use the publish function with RootModelType\n"
                        output_content += "\t\t\treturn this->publish(root_model_obj, new_client_web_socket_id);\n"
                        output_content += "\t\t}\n\t};\n\n"

                        output_content += "\ttemplate <typename UserDataType>\n"
                        output_content += f"\tclass {class_name}{message_name}ListWebSocketServer : public " \
                                          f"FluxCppCore::WebSocketServer<{package_name}::{message_name}, " \
                                          f"{package_name}::{message_name}List, UserDataType> {{\n"
                        output_content += f"\t\tusing BaseClass = FluxCppCore::WebSocketServer<{package_name}::{message_name}, " \
                                          f"{package_name}::{message_name}List, UserDataType>;\n"
                        output_content += "\tpublic:\n"
                        output_content += f'\t\texplicit {class_name}{message_name}ListWebSocketServer(UserDataType ' \
                                          f'&user_data, const std::string k_host = "127.0.0.1", const ' \
                                          f'int32_t k_web_socket_server_port = 8083, const int32_t k_read_timeout = ' \
                                          f'60, quill::Logger *p_logger = quill::get_logger()) : ' \
                                          f'BaseClass(user_data, k_host, k_web_socket_server_port, ' \
                                          f'k_read_timeout, p_logger) {{}}\n\n'

                        output_content += "\t\tbool NewClientCallBack(UserDataType &user_data, int16_t " \
                                          "new_client_web_socket_id) override {\n"
                        output_content += f"\t\t\t{package_name}::{message_name}List root_model_list_obj = user_data;\n\n"
                        output_content += "\t\t\t// Use the publish function with RootModelListType\n"
                        output_content += "\t\t\treturn this->publish(root_model_list_obj, new_client_web_socket_id);\n"
                        output_content += "\t\t}\n\t};\n\n"
                        break

        output_content += "}\n\n"
        output_file_name = f"{package_name}_web_socket_server.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebSocketServerPlugin)
