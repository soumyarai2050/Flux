#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List, Dict

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class CppDataStructurePlugin(BaseProtoPlugin):
    """
    Plugin to generate cpp_data_structure_plugin.py files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.root_message_name_list: List[str] = []
        self.dependency_file_list = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_all_root_message_name(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_name_list.append(message.proto.name)

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
        proto_file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        output_file_name: str = proto_file_name + ".h"
        output_content: str = ""
        self.get_all_root_message(file.messages)
        self.get_all_root_message_name(file.messages)
        self.get_dependency_message_proto(file)

        output_content: str = ""
        proto_file_name: str = str(file.proto.name).split(".")[0]

        flux_import_models: list = self.get_complex_option_value_from_proto(
            file, self.flux_file_import_dependency_model, True)
        import_file_msg: List[str] = []
        import_msg_name_list: List[str] = []
        for _ in flux_import_models:
            import_file_msg.append(_.get("ImportFileName"))
            msg_list = _.get("ImportModelName")
            for i in msg_list:
                # if not i.endswith("List"):
                import_msg_name_list.append(i)
                # output_content += i
                # print(__)
                # if __ in flux_import_models:
                #     outpt_content += str(__)

        output_content += "#pragma once\n\n"
        output_content += "#include <vector>\n"
        output_content += "#include <string>\n\n"
        output_content += "using namespace std;\n\n"

        struct_dict: Dict[str, protogen.Message] = {}
        struct_depend_dict: Dict[str, protogen.Message] = {}
        enum_dict: Dict[str, protogen.Enum] = {}

        for msg in file.messages:
            if struct_depend_dict.get(msg.proto.name) is None:
                struct_dict[msg.proto.name] = msg
                for fld in msg.fields:
                    if (fld.message is not None and
                            struct_dict.get(fld.message.proto.name) is None):
                        struct_depend_dict[fld.message.proto.name] = fld.message
                    elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                        enum_dict[fld.enum.proto.name] = fld.enum

        for f in self.dependency_file_list:
            if f.proto.name in import_file_msg:
                for msg in f.messages:
                    if (msg.proto.name in import_msg_name_list
                            and struct_depend_dict.get(msg.proto.name) is None):
                        struct_dict[msg.proto.name] = msg
                        for fld in msg.fields:
                            if fld.message is not None and struct_dict.get(fld.message.proto.name) is None:
                                struct_depend_dict[fld.message.proto.name] = fld.message
                            elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                                enum_dict[fld.enum.proto.name] = fld.enum

        # Output the struct definitions
        for name, message in struct_depend_dict.items():
            output_content += f"struct {name};\n\n"
        for name, message in struct_dict.items():
            output_content += f"struct {name};\n\n"

        for name, message in struct_depend_dict.items():
            output_content += f"struct {name} {{\n"
            if not name.endswith("List"):
                for fld in message.fields:
                    fld_kind = fld.kind.name.lower()
                    # if self.is_option_enabled(fld, self.flux_fld_val_is_datetime):
                    #     if fld_kind == "int64":
                    #         output_content += f"\tint64_t {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    #     elif fld_kind == "int32":
                    #         output_content += f"\tint32_t {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    #     else:
                    #         output_content += f"\t{fld_kind} {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    # else:
                    if fld_kind == "enum":
                        output_content += f"\tstring {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "int64":
                        output_content += f"\tint64_t {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "int32":
                        output_content += f"\tint32_t {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "message":
                        if fld.cardinality.name.lower() == "optional":
                            output_content += f"\t{fld.message.proto.name} {fld.proto.name}_;\n"
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                        elif fld.cardinality.name.lower() == "repeated":
                            output_content += f"\tvector<{fld.message.proto.name}> {fld.proto.name}_;\n"
                            output_content += f"\tbool is_{fld.message.proto.name}_set_ is_{fld.proto.name}_set_;\n"
                        else:
                            output_content += f"\t{fld.message.proto.name} {fld.proto.name}_;\n"
                    elif fld_kind == "float":
                        output_content += f"\tdouble {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    else:
                        output_content += f"\t{fld_kind} {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
            else:
                for fld in message.fields:
                    if fld.kind.name.lower() == "message":
                        output_content += f"\tvector<{fld.message.proto.name}> {fld.proto.name}_;\n"
            output_content += "};\n\n"

        for name, message in struct_dict.items():
            output_content += f"struct {name} {{\n"
            if not name.endswith("List"):
                for fld in message.fields:
                    fld_kind = fld.kind.name.lower()
                    # if self.is_option_enabled(fld, self.flux_fld_val_is_datetime):
                    #     if fld_kind == "int64":
                    #         output_content += f"\tint64_t {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    #     elif fld_kind == "int32":
                    #         output_content += f"\tint32_t {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    #     else:
                    #         output_content += f"\t{fld_kind} {fld.proto.name}_;\n"
                    #         # if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                    #         output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    # else:
                    if fld_kind == "enum":
                        output_content += f"\tstring {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "int64":
                        output_content += f"\tint64_t {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "int32":
                        output_content += f"\tint32_t {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    elif fld_kind == "message":
                        if fld.cardinality.name.lower() == "optional":
                            output_content += f"\t{fld.message.proto.name} {fld.proto.name}_;\n"
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                        elif fld.cardinality.name.lower() == "repeated":
                            output_content += f"\tvector<{fld.message.proto.name}> {fld.proto.name}_;\n"
                            output_content += f"\tbool is_{fld.proto.name}_set_ = false;\n"
                        else:
                            output_content += f"\t{fld.message.proto.name} {fld.proto.name}_;\n"
                    elif fld_kind == "float":
                        output_content += f"\tdouble {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                    else:
                        output_content += f"\t{fld_kind} {fld.proto.name}_;\n"
                        if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                            output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
            else:
                for fld in message.fields:
                    if fld.kind.name.lower() == "message":
                        output_content += f"\tvector<{fld.message.proto.name}> {fld.proto.name}_;\n"
            output_content += "\n\tauto get_name() const {\n"
            output_content += f'\t\treturn "{name}";\n'
            output_content += '\t}\n'
            output_content += "};\n\n"


        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDataStructurePlugin)
