#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List, Set, Dict

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class CppSharedDataStructure(BaseProtoPlugin):
    """
    Plugin to generate cpp_shared_data_structure files
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
        self.get_all_root_message(file.messages)
        self.get_all_root_message_name(file.messages)
        self.get_dependency_message_proto(file)

        output_content: str = ""
        proto_file_name: str = str(file.proto.name).split(".")[0]

        flux_import_models: list = self.get_complex_option_value_from_proto(
            file, self.flux_file_import_dependency_model, True)
        import_file_msg: List[str] = []
        import_msg_name_list: List[str] = []
        cache_model_name_list: List[str] = ["LastTrade", "MarketDepth"]
        for _ in flux_import_models:
            import_file_msg.append(_.get("ImportFileName"))
            msg_list = _.get("ImportModelName")
            for i in msg_list:
                if not i.endswith("List"):
                    import_msg_name_list.append(i)
                # output_content += i
                # print(__)
                # if __ in flux_import_models:
                #     outpt_content += str(__)

        output_content += "#pragma once\n\n"
        # output_content += "#include <string>\n\n"
        output_content += "using namespace std;\n\n"

        # char_size = CppSharedDataStructure.is_option_enabled(file, CppSharedDataStructure.flux_)
        struct_dict: Dict[str, protogen.Message] = {}
        struct_depend_dict: Dict[str, protogen.Message] = {}

        for msg in file.messages:
            if not msg.proto.name.endswith("List") and struct_depend_dict.get(msg.proto.name) is None:
                struct_dict[msg.proto.name] = msg
                for fld in msg.fields:
                    if (fld.message is not None and not fld.message.proto.name.endswith("List") and
                            struct_dict.get(fld.message.proto.name) is None):
                        struct_depend_dict[fld.message.proto.name] = fld.message

        for f in self.dependency_file_list:
            if f.proto.name in import_file_msg:
                for msg in f.messages:
                    if (not msg.proto.name.endswith("List") and msg.proto.name in import_msg_name_list
                            and struct_depend_dict.get(msg.proto.name) is None):
                        struct_dict[msg.proto.name] = msg
                        for fld in msg.fields:
                            if (fld.message is not None and not fld.message.proto.name.endswith("List")
                                    and struct_dict.get(fld.message.proto.name) is None):
                                struct_depend_dict[fld.message.proto.name] = fld.message

        # Output the struct definitions
        for name, message in struct_dict.items():
            output_content += f"struct {name}QueueElement;\n\n"

        for i in struct_depend_dict.values():
            str_val = CppSharedDataStructure.get_simple_option_value_from_proto(i, CppSharedDataStructure.flux_msg_string_length)
            char_size = str_val if str_val is not None else 64
            output_content += "struct " + i.proto.name + "QueueElement {\n"
            for fld in i.fields:
                if fld.proto.name.lower().endswith("time"):
                    output_content += "\tchar " + fld.proto.name + f"_[{char_size}];\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "float":
                    output_content += "\tdouble " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "int64" or fld.kind.name.lower() == "int32":
                    output_content += "\t" + fld.kind.name.lower() + "_t" + " " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "enum":
                    output_content += "\t" + "char " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "message":
                    output_content += "\t" + fld.message.proto.name + "QueueElement " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "string":
                    output_content += "\tchar " + fld.proto.name + f"_[{char_size}];\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                else:
                    output_content += "\t" + fld.kind.name.lower() + " " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
            output_content += "};\n\n"

        for i in struct_dict.values():
            str_val = CppSharedDataStructure.get_simple_option_value_from_proto(
                i, CppSharedDataStructure.flux_msg_string_length)
            char_size = str_val if str_val is not None else 64
            output_content += "struct " + i.proto.name + "QueueElement {\n"
            for fld in i.fields:
                if fld.proto.name.lower().endswith("time"):
                    output_content += "\tchar " + fld.proto.name + f"_[{char_size}];\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "float":
                    output_content += "\tdouble " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "int64" or fld.kind.name.lower() == "int32":
                    output_content += "\t" + fld.kind.name.lower() + "_t" + " " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "enum":
                    output_content += "\t" + "char " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "message":
                    output_content += "\t" + fld.message.proto.name + "QueueElement " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                elif fld.kind.name.lower() == "string":
                    output_content += "\tchar " + fld.proto.name + f"_[{char_size}];\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
                else:
                    output_content += "\t" + fld.kind.name.lower() + " " + fld.proto.name + "_;\n"
                    if fld.cardinality.name.lower() == "optional" or fld.cardinality.name.lower() == "repeated":
                        output_content += "\tbool is_" + fld.proto.name + "_set_ = false;\n"
            output_content += "};\n\n"

        output_file_name = f"{proto_file_name}_shared_data_structure.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppSharedDataStructure)
