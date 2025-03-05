#!/usr/bin/env python
import json
import logging
import os
from typing import List, Callable, Dict, Tuple
import time
import re

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class FilterProtoPlugin(BaseProtoPlugin):
    """
    Plugin script to convert proto schema to filter proto
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.proto_file_name: str = ""
        self.package_name: str = ""
        self.filter_field_msg_list: List[protogen.Message] = []
        self.dependency_msg_list: List[protogen.Message] = []
        self.dependency_enum_list: List[protogen.Enum] = []

    def is_field_having_filter_option(self, field: protogen.Field) -> bool:
        if self.is_option_enabled(field, FilterProtoPlugin.flux_fld_filter) and \
                "true" == self.get_simple_option_value_from_proto(field, FilterProtoPlugin.flux_fld_filter):
            return True
        else:
            return False

    def is_msg_having_filter_option_field(self, message: protogen.Message) -> bool:
        for field in message.fields:
            if self.is_field_having_filter_option(field):
                return True
        # else not required: returning False if no field of this msg is not having option FlxFldFilter
        return False

    def load_dependency_messages_and_enums_in_dicts(self, message: protogen.Message):
        if self.is_msg_having_filter_option_field(message) and message not in self.filter_field_msg_list:
            self.filter_field_msg_list.append(message)
        # else not required: Avoiding this msg if no field of it is having option FlxFldFilter
        for field in message.fields:
            if field.kind.name.lower() == "enum" and self.is_field_having_filter_option(field):
                if field.enum not in self.dependency_enum_list:
                    self.dependency_enum_list.append(field.enum)
                # else not required: avoiding repetition
            elif field.kind.name.lower() == "message":
                if self.is_field_having_filter_option(field) and field.message not in self.dependency_msg_list:
                    self.dependency_msg_list.append(field.message)
                # else not required: Avoiding this msg if no field of it is having option FlxFldFilter
                self.load_dependency_messages_and_enums_in_dicts(field.message)
            # else not required: avoiding other kinds than message or enum

    def load_root_and_non_root_messages_in_dicts(self, message_list: List[protogen.Message]):
        for message in message_list:
            self.load_dependency_messages_and_enums_in_dicts(message)

        for message in self.dependency_msg_list:
            for field in message.fields:
                if field.kind.name.lower() == "enum":
                    if field.enum not in self.dependency_enum_list:
                        self.dependency_enum_list.append(field.enum)
                    # else not required: avoiding repetition
                elif field.kind.name.lower() == "message":
                    if field.message not in self.dependency_msg_list:
                        self.dependency_msg_list.append(field.message)
                    # else not required: avoiding repetition
                # else not required: avoiding other kinds

    def handle_imports(self) -> str:
        output_str = 'syntax = "proto2";\n\n'
        output_str += 'import "flux_options.proto";\n'
        output_str += 'import "flux_utils.proto";\n'
        output_str += f'package {self.package_name}_filter;\n\n'
        return output_str

    def handle_enum_output(self, enum: protogen.Enum) -> str:
        output_str = f"enum {enum.proto.name}" + "{\n"
        for index, value in enumerate(enum.values):
            output_str += f"{value.proto.name} = {index+1};\n"
        output_str += "}\n"
        return output_str

    def __handle_filter_field_kind(self, field: protogen.Field) -> str:
        if field.kind.name.lower().startswith("uint"):
            return "FluxUIntRange"
        elif field.kind.name.lower().startswith("int"):
            return "FluxIntRange"
        elif field.enum is not None:
            return field.enum.proto.name
        elif field.message is not None:
            return field.message.proto.name
        else:
            return field.kind.name.lower()

    def __handle_field_kind(self, field: protogen.Field) -> str:
        if field.enum is not None:
            return field.enum.proto.name
        elif field.message is not None:
            return field.message.proto.name
        else:
            return field.kind.name.lower()

    def __handle_field_option_n_cmnt(self, field: protogen.Field) -> str:
        if field.kind.name.lower() == "string":
            return "; // one or more text or regex values to match against and filter data"
        elif field.enum is not None:
            return "; // one or more valid enum constants to compare and filter data"
        elif field.kind.name.lower() == "int32":
            return ' [(FluxFldValMin)="0.0", (FluxFldValMax)="4294967295"];'
        elif field.kind.name.lower() == "int64":
            return ' [(FluxFldValMin)="0.0", (FluxFldValMax)="9223372036854775807"];'
        elif field.kind.name.lower() == "uint32":
            return ' [(FluxFldValMin)="-2147483648", (FluxFldValMax)="2147483647"];'
        elif field.kind.name.lower() == "uint64":
            return ' [(FluxFldValMin)="-9223372036854775807", (FluxFldValMax)="9223372036854775807"];'
        else:
            return ";"

    def handle_message_output(self, message: protogen.Message, space_count: int = 2) -> str:
        if message in self.filter_field_msg_list:
            output_str = f"message {message.proto.name}" + "{\n"
            for index, field in enumerate(message.fields):
                if self.is_field_having_filter_option(field):
                    field_kind = self.__handle_filter_field_kind(field)
                    output_str += " "*space_count + f"repeated {field_kind} {field.proto.name} = {index+1}"
                    output_str += self.__handle_field_option_n_cmnt(field)
                    output_str += "\n"
                # else not required: avoiding fields not having filter option
            output_str += "}\n"
        elif message in self.dependency_msg_list:
            output_str = f"message {message.proto.name}" + "{\n"
            for index, field in enumerate(message.fields):
                field_kind = self.__handle_field_kind(field)
                output_str += " "*space_count + \
                              f"{field.cardinality.name.lower()} {field_kind} {field.proto.name} = {index+1};"
                output_str += "\n"
            output_str += "}\n"
        else:
            err_str = f"message {message.proto.name} not found in filter_field_msg_list and dependency_msg_list"
            logging.exception(err_str)
            raise Exception(err_str)
        return output_str

    def assign_required_data_members(self, file: protogen.File):
        self.proto_file_name = str(file.proto.name).split('.')[0]
        self.package_name = str(file.proto.package)

    def output_file_generate_handler(self, file: protogen.File):
        self.assign_required_data_members(file)
        self.load_root_and_non_root_messages_in_dicts(file.messages)
        # print("##enum##", [msg.proto.name for msg in self.dependency_enum_list])
        # print("##dmsg##", [msg.proto.name for msg in self.dependency_msg_list])
        # print("##fmsg##", [msg.proto.name for msg in self.filter_field_msg_list])

        output_str = self.handle_imports()
        for enum in self.dependency_enum_list:
            output_str += self.handle_enum_output(enum)
            output_str += "\n"

        for message in set(self.dependency_msg_list+self.filter_field_msg_list):
            output_str += self.handle_message_output(message)
            output_str += "\n"

        return_json = {f"{self.proto_file_name}_filter.proto": output_str}
        return return_json


if __name__ == "__main__":
    main(FilterProtoPlugin)
