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


class CppKeyHandlerPlugin(BaseProtoPlugin):
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
            if CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()

        output_content: str = ""

        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n\n"
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'

        output_content += f"class {class_name}KeyHandler "
        output_content += "{\n\n"

        output_content += "public:\n\n"

        for message in self.root_message_list:
            if CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_executor_options):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                output_content += f"\n\tstatic inline std::string get_{message_name_snake_cased}_key(const {package_name}::" \
                                  f"{message_name} &{message_name_snake_cased}_data)"
                output_content += "{\n\t\t"
                key_list: List[List[str]] = StratExecutorPlugin.get_executor_key_sequence_list_of_model(message)
                output_content += "std::string key;\n"

                if key_list is not None and len(key_list) > 0:
                    for key in key_list[0]:
                        if key.count("'") > 0:
                            temp_str: str = key.replace("'", "")
                            output_content += f'\n\t\tkey = key + "{temp_str}";\n'
                        elif key.count(".") > 0:
                            temp_key_list = key.split(".")
                            # field_name = temp_key_list[-1]
                            # field_name_message = temp_key_list[-2]
                            # for msg in file.messages:
                            #     if msg.proto.name == field_name_message:
                            #         for fld in msg.fields:
                            #             # print(f"-------------------{msg.proto.name}")
                            #             if field_name == fld.proto.name:
                            #                 print(f"-------------------{field_name}")
                            #             else:
                            #                 pass
                            # "order.security.sec_id-order.side"
                            msg = None
                            for key_msg in temp_key_list:
                                if key_msg != temp_key_list[-1]:
                                    for field in message.fields:
                                        if field.proto.name == key_msg:
                                            msg = field.message
                                        else:
                                            err_str = ""
                                else:
                                    if msg is not None:
                                        for field in msg.fields:
                                            if field.proto.name == key_msg:
                                                if field.kind.name.lower() == "enum":
                                                    output_content += f"\n\t\tkey += std::to_string({message_name_snake_cased}_data"
                                                    for k in temp_key_list:
                                                        output_content += f".{k}()"
                                                    output_content += ");"
                                                else:
                                                    pass
                                            elif field.proto.name in temp_key_list:
                                                output_content += f"\n\t\tkey += {message_name_snake_cased}_data"
                                                for k in temp_key_list:
                                                    output_content += f".{k}()"
                                                output_content += ";"
                                    else:
                                        err_str = ""
                        else:
                            for field in message.fields:
                                if key == field.proto.name:
                                    if field.kind.name.lower() == "enum":
                                        output_content += f"\n\t\tkey += std::to_string({message_name_snake_cased}_data.{key}());"
                                    else:
                                        output_content += f"\n\t\tkey = key + {message_name_snake_cased}_data.{key}();"

                        output_content += '\n\t\tkey = key + "_";'

                output_content += "\n\t\treturn key;"
                output_content += "\n\t}\n"

        output_content += "};"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{proto_file_name}_key_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppKeyHandlerPlugin)
