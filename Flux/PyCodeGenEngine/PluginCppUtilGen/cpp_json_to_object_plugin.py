#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List, Dict

from FluxPythonUtils.scripts.utility_functions import parse_to_int, convert_camel_case_to_specific_case

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class CppJsonToObjectPlugin(BaseProtoPlugin):
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
        output_file_name: str = package_name + "_json_to_object.h"
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
        output_content += "#include <iostream>\n"
        output_content += "#include <string>\n\n"
        output_content += "#include <boost/json.hpp>\n\n"
        output_content += '#include "cpp_app_logger.h"\n'
        output_content += f'#include "../CppDataStructures/{proto_file_name}.h"\n\n'
        output_content += "using namespace std;\n\n"
        class_name = ''.join(word.capitalize() for word in package_name.split('_'))
        output_content += f'class {class_name}JsonToObject {{\n\n'
        output_content += "public:\n"

        struct_dict: Dict[str, protogen.Message] = {}
        struct_depend_dict: Dict[str, protogen.Message] = {}
        enum_dict: Dict[str, protogen.Enum] = {}

        for msg in file.messages:
            if (struct_depend_dict.get(msg.proto.name) is None and self.is_option_enabled(
                    msg, CppJsonToObjectPlugin.flux_msg_json_root) or
                    self.is_option_enabled(msg, CppJsonToObjectPlugin.flux_msg_json_root_time_series)):
                struct_dict[msg.proto.name] = msg
                for fld in msg.fields:
                    if fld.message is not None and struct_dict.get(fld.message.proto.name) is None:
                        if (self.is_option_enabled(fld.message, CppJsonToObjectPlugin.flux_msg_json_root) or
                            self.is_option_enabled(fld.message, CppJsonToObjectPlugin.flux_msg_json_root_time_series)):
                            struct_depend_dict[fld.message.proto.name] = fld.message
                    elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                        enum_dict[fld.enum.proto.name] = fld.enum

        for f in self.dependency_file_list:
            if f.proto.name in import_file_msg:
                for msg in f.messages:
                    if (msg.proto.name in import_msg_name_list and self.is_option_enabled(
                            msg, CppJsonToObjectPlugin.flux_msg_json_root) or
                            self.is_option_enabled(msg, CppJsonToObjectPlugin.flux_msg_json_root_time_series)
                            and struct_depend_dict.get(msg.proto.name) is None):
                        struct_dict[msg.proto.name] = msg
                        for fld in msg.fields:
                            if fld.message is not None and struct_dict.get(fld.message.proto.name) is None:
                                if (self.is_option_enabled(fld.message, CppJsonToObjectPlugin.flux_msg_json_root) or
                                        self.is_option_enabled(fld.message, CppJsonToObjectPlugin.flux_msg_json_root_time_series)):
                                    struct_depend_dict[fld.message.proto.name] = fld.message
                            elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                                enum_dict[fld.enum.proto.name] = fld.enum

        output_content += "\tstatic void parse_string_to_json(const std::string& kr_str, boost::json::object& r_json_out) {\n"
        output_content += "\t\ttry{\n"
        output_content += '\t\tboost::json::value parsed_value = boost::json::parse(kr_str);\n'
        output_content += '\t\tif (parsed_value.is_object()) {\n'
        output_content += '\t\t\tr_json_out = parsed_value.as_object();\n'
        output_content += '\t\t}\n'
        output_content += "\t\t} catch (const boost::json::system_error& e) {\n"
        output_content += '\t\t\tLOG_ERROR_IMPL(GetCppAppLogger(), "Error parsing JSON: {}", e.what());\n\t\t}\n\t}\n\n'

        def process_message(name, message, indent=1):
            """Recursively processes a message to generate the JSON to object conversion code."""
            name_lower = convert_camel_case_to_specific_case(name)
            output = []
            tab = "\t" * indent

            for fld in message.fields:
                fld_cardinality = fld.cardinality.name.lower()
                fld_name = fld.proto.name
                fld_kind = fld.kind.name.lower()
                kind = {
                    "float": "double",
                    "int32": "int64",
                    "int64": "int64",
                    "string": "string",
                    "bool": "bool",
                    "enum": "string",
                    "message": "object"
                }.get(fld_kind, "")

                if fld_kind != "message":
                    # Non-message types (handle optional/repeated cases)
                    if fld_cardinality in {"optional", "repeated"}:
                        val = f'{name_lower}_json["{fld_name}"].as_{kind}();' if fld_kind == "int32" else f'{name_lower}_json["{fld_name}"].as_{kind}();'
                        output.append(f'{tab}if ({name_lower}_json.if_contains("{fld_name}")) {{')
                        output.append(f'{tab}\tr_{name_lower}.{fld_name}_ = {val};')
                        output.append(f'{tab}\tr_{name_lower}.is_{fld_name}_set_ = true;')
                        output.append(f"{tab}}}")
                    else:
                        if fld_name == "id":
                            val = f'{name_lower}_json["_{fld_name}"].as_{kind}();' if fld_kind == "int32" and fld_name == "id" else f'{name_lower}_json["_{fld_name}"].as_{kind}();'
                            output.append(f'{tab}r_{name_lower}.{fld_name}_ = {val};')
                        else:
                            val = f'{name_lower}_json["_{fld_name}"].as_{kind}();' if fld_kind == "int32" and fld_name == "id" else f'{name_lower}_json["{fld_name}"].as_{kind}();'
                            output.append(f'{tab}r_{name_lower}.{fld_name}_ = {val};')
                else:
                    if fld_cardinality == "optional":
                        # Recursive case: Handle message fields
                        output.append(f'{tab}if ({name_lower}_json.if_contains("{fld_name}")) {{')
                        output.append(f'{tab}\tauto {fld_name}_json = {name_lower}_json["{fld_name}"].as_object();')
                        output.append(f'{tab}\t{fld.message.proto.name} r_{fld_name}{{}};')
                        # Recursively process the nested message
                        nested_message_code = process_message(fld.proto.name, fld.message, indent + 1)
                        output.append(nested_message_code)
                        output.append(f'{tab}\tr_{name_lower}.{fld_name}_ = r_{fld_name};\n')
                        output.append(f'{tab}\tr_{name_lower}.is_{fld_name}_set_ = true;\n')

                        output.append(f"{tab}}}\n")
                    elif fld_cardinality == "repeated":
                        output.append(f'{tab}if ({name_lower}_json.if_contains("{fld_name}")) {{')
                        output.append(f'{tab}\tboost::json::array {fld_name}_array = {name_lower}_json["{fld_name}"].as_array();')
                        output.append(f'{tab}\tfor (const auto& {fld_name}_val : {fld_name}_array) {{')
                        output.append(f'{tab}\t\tauto {fld_name}_json = {fld_name}_val.as_object();')
                        output.append(f'{tab}\t\t{fld.message.proto.name} r_{fld_name}{{}};')
                        # Recursively process the nested message
                        nested_message_code = process_message(fld.proto.name, fld.message, indent + 2)
                        output.append(nested_message_code)
                        output.append(f'{tab}\t\tr_{name_lower}.{fld_name}_.push_back(r_{fld_name});')
                        output.append(f'{tab}\t}}')
                        output.append(f'{tab}\tr_{name_lower}.is_{fld_name}_set_ = true;')

                        output.append(f"{tab}}}\n")
                    else:
                        # Recursive case: Handle message fields
                        output.append(f'{tab}if ({name_lower}_json.if_contains("{fld_name}")) {{')
                        output.append(f'{tab}\tauto {fld_name}_json = {name_lower}_json["{fld_name}"].as_object();')
                        output.append(f'{tab}\t{fld.message.proto.name} r_{fld_name}{{}};')
                        # Recursively process the nested message
                        nested_message_code = process_message(fld.proto.name, fld.message, indent + 1)
                        output.append(nested_message_code)
                        output.append(f'{tab}\tr_{name_lower}.{fld_name}_ = r_{fld_name};\n')
                        output.append(f"{tab}}}\n")

                # output.append(f"{tab}}}\n")
            return "\n".join(output)

        for name, message in struct_dict.items():
            name_lower = convert_camel_case_to_specific_case(name)
            output_content += (f"\tstatic void json_to_object(const std::string& kr_json_str, "
                               f"{name}& r_{name_lower}) {{\n")
            output_content += (f"\t\tboost::json::object {name_lower}_json;\n")
            output_content += (f"\t\tparse_string_to_json(kr_json_str, {name_lower}_json);\n")
            output_content += process_message(name, message, 2)
            output_content += (f"\n\t}}\n\n")

            output_content += (f"\tstatic void json_to_object(const std::string& kr_json_str, "
                               f"{name}List& r_{name_lower}_list) {{\n")
            output_content += f'\t\tconst auto& {name_lower}_parse = boost::json::parse(kr_json_str);\n'
            output_content += f'\t\tif ({name_lower}_parse.is_array()) {{\n'
            output_content += f'\t\t\tconst auto& {name_lower}_list_json = {name_lower}_parse.get_array();\n'
            output_content += f'\t\t\tr_{name_lower}_list.{name_lower}_.reserve({name_lower}_list_json.size());\n'
            output_content += f'\t\t\tfor (const auto& {name_lower}_json : {name_lower}_list_json) {{\n'
            output_content += f'\t\t\t\t{name} r_{name_lower}{{}};\n'
            output_content += f'\t\t\t\tjson_to_object(boost::json::serialize({name_lower}_json), r_{name_lower});\n'
            output_content += f'\t\t\t\tr_{name_lower}_list.{name_lower}_.emplace_back(std::move(r_{name_lower}));\n'
            output_content += f'\t\t\t}}\n'
            output_content += f'\t\t}}\n'
            output_content += f'\t}}\n\n'
        output_content += "};\n\n"

        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppJsonToObjectPlugin)
