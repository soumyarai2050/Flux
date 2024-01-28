#!/usr/bin/env python
import logging
from typing import List
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin


class Proto2ToProto3(BaseProtoPlugin):
    """
    Plugin to generate sample output to key generate from proto schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.dependencies: List[str] = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_all_dependencies(self, file: protogen.File):
        for dependencies in file.dependencies:
            self.dependencies.append(dependencies.proto.name)

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
        self.get_all_dependencies(file)

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += 'syntax = "proto3";\n\n'

        for dependency in self.dependencies:
            output_content += f'import "{dependency}";\n'

        output_content += f'\npackage {package_name};\n\n'

        for message in self.root_message_list:
            i: int = 1
            message_name: str = message.proto.name
            output_content += f"message {message_name} {{\n"

            for field in message.fields:
                field_name: str = field.proto.name
                field_type: str = field.kind.name
                field_enum = field.enum
                field_type_message: protogen.Message | None = field.message
                field_cardinality: str = field.cardinality.name
                if field_type_message is None:
                    if field_type.lower() != "enum":
                        if field_cardinality.lower() != "required":
                            output_content += f"\t{field_cardinality.lower()} {field_type.lower()} {field_name} = {i};\n"
                            i += 1
                        else:
                            output_content += f"\t{field_type.lower()} {field_name} = {i};\n"
                            i += 1
                    else:
                        if field_cardinality.lower() != "required":
                            output_content += f"\t{field_cardinality.lower()} {field_enum.proto.name} {field_name} = {i};\n"
                            i += 1
                        else:
                            output_content += f"\t{field_enum.proto.name} {field_name} = {i};\n"
                            i += 1
                else:
                    field_type_message_name: str = field_type_message.proto.name
                    if field_cardinality.lower() != "required":
                        output_content += f"\t{field_cardinality.lower()} {field_type_message_name} {field_name} = {i};\n"
                        i += 1
                    else:
                        output_content += f"\t{field_type_message_name} {field_name} = {i};\n"
                        i += 1

            output_content += "}\n\n"

        output_file_name = f"{class_name_snake_cased}.proto"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(Proto2ToProto3)
