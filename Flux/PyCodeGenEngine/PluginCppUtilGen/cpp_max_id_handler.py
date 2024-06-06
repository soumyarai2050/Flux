#!/usr/bin/env python
import logging
import os
import time
from pathlib import PurePath
from typing import List

from FluxPythonUtils.scripts.utility_functions import parse_to_int, YAMLConfigurationManager

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppMaxIdHandler(BaseProtoPlugin):
    """
    Plugin to generate cpp_max_id_handler files
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
            if CppMaxIdHandler.is_option_enabled \
                        (message, CppMaxIdHandler.flux_msg_json_root):
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
    def header_generate_handler(file_name: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n"
        output_content += f'#include <mutex>"\n\n'

        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
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

        output_content += f"namespace {package_name}_handler {{\n"

        output_content += f"\n\tclass {class_name}MaxIdHandler;\n\n"

        output_content += "\tclass MaxIdHandler {\n"
        output_content += "\tpublic:\n\n"
        output_content += "\t\tint32_t get_next_id() {\n"
        output_content += "\t\t\tstd::lock_guard lg(max_id_mutex);\n"
        output_content += "\t\t\tmax_used_id++;\n"
        output_content += "\t\t\treturn max_used_id;\n"
        output_content += "\t\t}\n\n"

        output_content += "\tprotected:\n\n"
        output_content += "\t\tvoid update_max_id(const int32_t max_used_id_) {\n"
        output_content += "\t\t\tmax_used_id = max_used_id_;\n"
        output_content += "\t\t}\n\n"

        output_content += f"\t\tfriend {class_name}MaxIdHandler;\n"
        output_content += "\t\tint32_t max_used_id = 0;\n"
        output_content += "\t\tstd::mutex max_id_mutex{};\n"
        output_content += "\t};\n\n"

        output_content += f"\tclass {class_name}MaxIdHandler {{\n\n"
        output_content += "\tpublic:\n\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if (CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root) or
                    CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root_time_series)):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):

                        output_content += (f"\t\tstatic void update_{message_name_snake_cased}_max_id(const "
                                           f"int32_t k_max_id) {{\n")
                        output_content += (f"\t\t\tc_{message_name_snake_cased}_max_id_handler.update_max_id("
                                           f"k_max_id);\n")
                        output_content += "\t\t}\n\n"
                        break

        output_content += "\tpublic:\n"

        for message in self.root_message_list:
            message_name: str = message.proto.name
            message_name_snake_cased: str = convert_camel_case_to_specific_case(message_name)
            if CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root) or \
                    CppMaxIdHandler.is_option_enabled(message, CppMaxIdHandler.flux_msg_json_root_time_series):
                for field in message.fields:
                    if CppMaxIdHandler.is_option_enabled(field, CppMaxIdHandler.flux_fld_PK):
                        output_content += f"\t\tstatic inline MaxIdHandler c_{message_name_snake_cased}_max_id_handler{{}};\n"
                        break

        output_content += "\t};\n}\n"

        output_file_name = f"{class_name_snake_cased}_max_id_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppMaxIdHandler)
