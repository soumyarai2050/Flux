#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

import yaml

from FluxPythonUtils.scripts.utility_functions import parse_to_int, convert_camel_case_to_specific_case

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main

yaml_file_path: PurePath = PurePath(__file__).parent.parent.parent / "flux_core.yaml"


class CppProto2ModelPlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_proto2_market_data_service files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.root_message_name_list: List[str] = []
        self.core_or_util_files: List[str] = []
        self.options_files: List[str] = []
        self.dependency_file_list = []
        self.file_enum_list = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_all_root_message_name(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_name_list.append(message.proto.name)

    def get_all_enum_from_file(self, file: protogen.File) -> None:
        for enum in file.enums:
            self.file_enum_list.append(enum)

    def get_data_from_yaml(self):
        with open(yaml_file_path, "r") as yaml_file:
            parsed_yaml = yaml.safe_load(yaml_file)

        self.options_files = parsed_yaml.get('options_files', [])
        self.core_or_util_files = parsed_yaml.get('core_or_util_files', [])

    @staticmethod
    def generate_enum_value(enums: List[protogen.Enum]):
        output_content: str = ""
        for enum in enums:
            i: int = 1
            output_content += f"enum {enum.proto.name} {{\n"
            for enum_value in enum.values:
                output_content += f"\t{enum_value.proto.name} = {i};\n"
                i += 1

            output_content += "}\n\n"
        return output_content

    def generate_nested_fld(self, message_list: List[protogen.Message], message_name_list: List[str], enum_list):
        output_content: str = ""
        nested_msg_list: List[protogen.Message] = []

        nested_enum_list = []
        for message in message_list:
            i: int = 1
            message_name: str = message.proto.name
            output_content += f"message {message_name} {{\n"

            for field in message.fields:
                field_name: str = field.proto.name
                field_type: str = field.kind.name
                field_enum = field.enum
                field_type_message: protogen.Message | None = field.message
                field_cardinality: str = field.cardinality.name
                if field_enum is not None:
                    if field_enum not in enum_list:
                        enum_list.append(field_enum)
                        nested_enum_list.append(field_enum)

                if field_type_message is None:
                    if field_type.lower() != "enum":
                        output_content += f"\t{field_cardinality.lower()} {field_type.lower()} {field_name} = {i};\n"
                        i += 1
                    else:
                        output_content += f"\t{field_cardinality.lower()} {field_enum.proto.name} {field_name} = {i};\n"
                        i += 1
                else:
                    field_type_message_name: str = field_type_message.proto.name
                    if field_type_message_name not in message_name_list:
                        nested_msg_list.append(field_type_message)
                        message_name_list.append(field_type_message_name)
                    output_content += f"\t{field_cardinality.lower()} {field_type_message_name} {field_name} = {i};\n"
                    i += 1

            output_content += "}\n\n"
        output_content += self.generate_enum_value(nested_enum_list)

        return output_content, nested_msg_list, message_name_list, enum_list

    def get_dependency_message_proto(self, file: protogen.File):
        self.dependency_file_list = file.dependencies

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        self.get_all_root_message(file.messages)
        self.get_all_root_message_name(file.messages)
        self.get_data_from_yaml()
        self.get_dependency_message_proto(file)
        self.get_all_enum_from_file(file)

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += 'syntax = "proto2";\n\n'
        output_content += f'package {package_name};\n\n'

        dependency_list = []
        dependency_msg_list = []
        dependency_dict = {}
        dependency_enum_list = []
        dependency_enum_dict = {}
        message_list: List[protogen.Message] = []
        message_name_list: List[str] = []
        enum_list = []
        nested_enum_list = []

        file_msg_name_list = ["market_data_n_strat_executor_core.proto",
                              "dashboards_n_market_data_n_strat_executor_core.proto"]

        for dependency in self.dependency_file_list:
            dependency_name: str = dependency.proto.name
            if dependency_name not in self.core_or_util_files and dependency_name not in self.options_files:
                for dependency_msg in dependency.messages:
                    dependency_list.append(dependency_msg.proto.name)
                    dependency_msg_list.append(dependency_msg)
                    dependency_dict[dependency_msg.proto.name] = dependency_msg
                dependency_enum_list.append(dependency.enums)
                output_content += f'import "{dependency_name}";\n\n'

        dependency_file_msg_name_list = []

        for file in self.dependency_file_list:
            if file.proto.name in file_msg_name_list:
                for msg in file.messages:
                    num: int = 1
                    dependency_file_msg_name_list.append(msg.proto.name)
                    output_content += f"message {msg.proto.name} {{\n"
                    for fld in msg.fields:
                        if fld.enum is None:
                            if fld.message is None:
                                fld_name = fld.proto.name
                                fld_cardinality = fld.cardinality.name.lower()
                                fld_kind = fld.kind.name.lower()
                                output_content += f"\t{fld_cardinality} {fld_kind} {fld_name} = {num};\n"
                                num += 1
                            else:
                                if (fld.message.proto.name not in message_name_list and
                                        fld.message.proto.name not in dependency_file_msg_name_list):
                                    dependency_file_msg_name_list.append(fld.message.proto.name)
                                    message_name_list.append(fld.message.proto.name)
                                    message_list.append(fld.message)
                                fld_name = fld.proto.name
                                fld_cardinality = fld.cardinality.name.lower()
                                fld_msg = fld.message.proto.name
                                output_content += f"\t{fld_cardinality} {fld_msg} {fld_name} = {num};\n"
                                num += 1
                        else:
                            if fld.enum not in self.file_enum_list and fld.enum not in enum_list:
                                self.file_enum_list.append(fld.enum)
                            fld_name = fld.proto.name
                            fld_cardinality = fld.cardinality.name.lower()
                            fld_enum_name = fld.enum.proto.name
                            output_content += f"\t{fld_cardinality} {fld_enum_name} {fld_name} = {num};\n"
                            num += 1
                    output_content += "}\n\n"

        for enums in dependency_enum_list:
            for enum in enums:
                dependency_enum_dict[enum.proto.name] = enum

        for enums in dependency_enum_list:
            for enum in enums:
                enum_list.append(enum)

        for enum in self.file_enum_list:
            if enum not in enum_list:
                nested_enum_list.append(enum)
                enum_list.append(enum)

        for msg in dependency_msg_list:
            for fld in msg.fields:
                fld_enum = fld.enum
                fld_msg = fld.message
                if fld_enum is not None and fld_enum not in enum_list:
                    enum_list.append(fld_enum)
                if fld_msg is not None:
                    if fld_msg.proto.name not in message_name_list:
                        message_name_list.append(fld_msg.proto.name)

        for message_name in self.root_message_name_list:
            message_name_list.append(message_name)

        for msg_name in dependency_list:
            message_name_list.append(msg_name)

        for message in self.root_message_list:
            i: int = 1
            message_name: str = message.proto.name
            if message_name not in dependency_file_msg_name_list:
                output_content += f"\nmessage {message_name} {{\n"
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_type: str = field.kind.name
                    field_enum = field.enum
                    field_type_message: protogen.Message | None = field.message
                    field_cardinality: str = field.cardinality.name
                    field_enums = field.enum
                    if field_enums is not None:
                        if field_enums not in enum_list:
                            enum_list.append(field_enums)
                            nested_enum_list.append(field_enums)
                    if field_type_message is None:
                        if field_type.lower() != "enum":
                            output_content += f"\t{field_cardinality.lower()} {field_type.lower()} {field_name} = {i};\n"
                            i += 1
                        else:
                            output_content += f"\t{field_cardinality.lower()} {field_enum.proto.name} {field_name} = {i};\n"
                            i += 1
                    else:
                        field_type_message_name: str = field_type_message.proto.name
                        output_content += f"\t{field_cardinality.lower()} {field_type_message_name} {field_name} = {i};\n"
                        i += 1
                        if field_type_message_name not in message_name_list:
                            message_name_list.append(field_type_message_name)
                            message_list.append(field_type_message)

                output_content += "}\n\n"

        output_content += self.generate_enum_value(nested_enum_list)
        # for i in nested_enum_list:
        #     print(f"------------------------{i.proto.name}")

        output, nested_msg_list, nested_msg_name_list, nested_enum_list = self.generate_nested_fld \
            (message_list, message_name_list, enum_list)

        output_content += output
        size = len(nested_msg_list)
        while size != 0:
            output, nested_msg_list, nested_msg_name_list, nested_enum_list = self.generate_nested_fld \
                (nested_msg_list, nested_msg_name_list, nested_enum_list)
            output_content += output
            size = len(nested_msg_list)

        output_file_name = f"{file_name}.proto"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppProto2ModelPlugin)
