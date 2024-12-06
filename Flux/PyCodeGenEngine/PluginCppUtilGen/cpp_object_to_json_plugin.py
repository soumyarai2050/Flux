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


class CppObjectToJsonPlugin(BaseProtoPlugin):
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
        output_file_name: str = package_name + "_object_to_json.h"
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
        output_content += '#include "../CppDataStructures/market_data_service.h"\n\n'
        output_content += "using namespace std;\n\n"

        class_name = ''.join(word.capitalize() for word in package_name.split('_'))
        output_content += f'class {class_name}ObjectToJson {{\n\n'
        output_content += "public:\n"

        struct_dict: Dict[str, protogen.Message] = {}
        struct_depend_dict: Dict[str, protogen.Message] = {}
        enum_dict: Dict[str, protogen.Enum] = {}

        for msg in file.messages:
            if (struct_depend_dict.get(msg.proto.name) is None and self.is_option_enabled(
                    msg, CppObjectToJsonPlugin.flux_msg_json_root) or
                    self.is_option_enabled(msg, CppObjectToJsonPlugin.flux_msg_json_root_time_series)):
                struct_dict[msg.proto.name] = msg
                for fld in msg.fields:
                    if fld.message is not None and struct_dict.get(fld.message.proto.name) is None:
                        if (self.is_option_enabled(fld.message, CppObjectToJsonPlugin.flux_msg_json_root) or
                            self.is_option_enabled(fld.message, CppObjectToJsonPlugin.flux_msg_json_root_time_series)):
                            struct_depend_dict[fld.message.proto.name] = fld.message
                    elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                        enum_dict[fld.enum.proto.name] = fld.enum

        for f in self.dependency_file_list:
            if f.proto.name in import_file_msg:
                for msg in f.messages:
                    if (msg.proto.name in import_msg_name_list and self.is_option_enabled(
                            msg, CppObjectToJsonPlugin.flux_msg_json_root) or
                            self.is_option_enabled(msg, CppObjectToJsonPlugin.flux_msg_json_root_time_series)
                            and struct_depend_dict.get(msg.proto.name) is None):
                        struct_dict[msg.proto.name] = msg
                        for fld in msg.fields:
                            if fld.message is not None and struct_dict.get(fld.message.proto.name) is None:
                                if (self.is_option_enabled(fld.message, CppObjectToJsonPlugin.flux_msg_json_root) or
                                        self.is_option_enabled(fld.message, CppObjectToJsonPlugin.flux_msg_json_root_time_series)):
                                    struct_depend_dict[fld.message.proto.name] = fld.message
                            elif fld.enum is not None and enum_dict.get(fld.enum.proto.name) is None:
                                enum_dict[fld.enum.proto.name] = fld.enum

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
                        output.append(f'{tab}if (kr_{name_lower}.is_{fld_name}_set_) {{')
                        output.append(f'{tab}\tr_{name_lower}_json_out["{fld_name}"] = kr_{name_lower}.{fld_name}_;')
                        output.append(f"{tab}}}")
                    else:
                        name = "_id" if fld_name == "id" else fld_name
                        output.append(f'{tab}r_{name_lower}_json_out["{name}"] = kr_{name_lower}.{fld_name}_;')
                else:
                    if fld_cardinality == "optional":
                        # Recursive case: Handle message fields
                        output.append(f'{tab}if (kr_{name_lower}.is_{fld_name}_set_) {{')
                        output.append(f'{tab}\tboost::json::object r_{fld_name}_json_out;')
                        output.append(f'{tab}\t{fld.message.proto.name} kr_{fld_name} = kr_{name_lower}.{fld_name}_;')
                        # Recursively process the nested message
                        nested_message_code = process_message(fld.proto.name, fld.message, indent + 1)
                        output.append(nested_message_code)
                        output.append(f'{tab}\tr_{name_lower}_json_out["{fld_name}"] = r_{fld_name}_json_out;\n')

                        output.append(f"{tab}}}\n")
                    elif fld_cardinality == "repeated":
                        output.append(f'{tab}if (kr_{name_lower}.is_{fld_name}_set_) {{')
                        output.append(f'{tab}\tboost::json::array r_{fld_name}_json_list;')
                        output.append(f'{tab}\tconst vector<{fld.message.proto.name}> kr_{fld_name}_list = '
                                      f'kr_{name_lower}.{fld_name}_;')
                        output.append(f'{tab}\tfor (size_t i = 0; i < kr_{fld_name}_list.size(); i++) {{\n')
                        output.append(f'{tab}\t\tboost::json::object r_{fld_name}_json_out;')
                        output.append(f'{tab}\t\tconst {fld.message.proto.name} kr_{fld_name} = kr_{fld_name}_list.at(i);')
                        nested_message_code = process_message(fld.proto.name, fld.message, indent + 2)
                        output.append(nested_message_code)
                        output.append(f'{tab}\t\tr_{fld_name}_json_list.push_back(std::move(r_{fld_name}_json_out));\n')
                        output.append(f"{tab}\t}}\n")
                        output.append(f'{tab}\tr_{name_lower}_json_out["{fld_name}"] = r_{fld_name}_json_list;')
                        output.append(f'{tab}}}')
                        # Recursively process the nested message
                    else:
                        # Recursive case: Handle message fields
                        # output.append(f'{tab}if ({name_lower}_json.if_contains("{fld_name}")) {{')
                        output.append(f'{tab}boost::json::object r_{fld_name}_json_out;')
                        output.append(f'{tab}{fld.message.proto.name} kr_{fld_name} = kr_{name_lower}.{fld_name}_;')
                        # Recursively process the nested message
                        nested_message_code = process_message(fld.proto.name, fld.message, indent)
                        output.append(nested_message_code)
                        output.append(f'{tab}r_{name_lower}_json_out["{fld_name}"] = r_{fld_name}_json_out;\n')
                        # output.append(f"{tab}}}\n")

                # output.append(f"{tab}}}\n")
            return "\n".join(output)

        for name, message in struct_dict.items():
            name_lower = convert_camel_case_to_specific_case(name)
            output_content += (f"static void object_to_json(const {name}& kr_{name_lower}, boost::json::object& "
                               f"r_{name_lower}_json_out) {{\n")
            output_content += process_message(name, message, 1)
            output_content += (f"\n}}\n\n")
            output_content += (f'static void object_to_json(const {name}List& kr_{name_lower}_list, '
                               f'boost::json::object& r_{name_lower}_json_out) {{\n')
            output_content += f'\tboost::json::array json_array;\n'
            output_content += f'\tfor (const auto& kr_{name_lower} : kr_{name_lower}_list.{name_lower}_) {{\n'
            output_content += f'\t\tboost::json::object json_obj;\n'
            output_content += f'\t\tobject_to_json(kr_{name_lower}, json_obj);\n'
            output_content += f'\t\tjson_array.push_back(json_obj);\n'
            output_content += f'\t}}\n'
            output_content += f'\tr_{name_lower}_json_out["{name_lower}"] = json_array;\n'
            output_content += f'}}\n\n'
        output_content += "};\n\n"

        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppObjectToJsonPlugin)
