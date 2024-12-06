#!/usr/bin/env python
from pathlib import PurePath
from typing import List
import os
import time
import logging

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppKeyHandlerPlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to key generate from proto schema
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

    @staticmethod
    def header_generate_handler(file_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n\n"
        output_content += f'#include "../CppDataStructures/{file_name}.h"\n\n'
        return output_content

    @staticmethod
    def generate_get_key_list(package_name: str, message: protogen.Message):
        message_name = message.proto.name
        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

        output_content: str = ""

        output_content += f"\n\t\tstatic inline void get" \
                          f"_key_list(const {message_name}List &kr_{message_name_snake_cased}_list_obj, " \
                          f"std::vector< std::string > &r_{message_name_snake_cased}_key_list_out) {{\n"

        output_content += f'\t\t\tfor (size_t i = 0; i < kr_{message_name_snake_cased}_list_obj.{message_name_snake_cased}_.size(); ' \
                          f'++i) {{\n'
        output_content += f'\t\t\t\tstd::string key;\n'
        output_content += (f'\t\t\t\tget_key_out(kr_{message_name_snake_cased}_list_obj.{message_name_snake_cased}_.at(i), '
                           f'key);\n')
        output_content += f'\t\t\t\tr_{message_name_snake_cased}_key_list_out.emplace_back(std::move(key));\n'
        output_content += '\t\t\t}\n'

        return output_content

    @staticmethod
    def generate_get_key_handler(message: protogen.Message, message_name_snake_cased: str):
        output: str = ""

        for field in message.fields:
            field_name: str = field.proto.name
            field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
            field_type_message: protogen.Message | None = field.message
            if CppKeyHandlerPlugin.is_option_enabled(field, CppKeyHandlerPlugin.flux_fld_PK):
                if field_type_message is not None:
                    flux_fld_pk_value = (CppKeyHandlerPlugin.get_simple_option_value_from_proto
                                              (field, CppKeyHandlerPlugin.flux_fld_PK))
                    flux_fld_pk_value_list = flux_fld_pk_value.split(".")
                    output += (f"\t\t\tr_{message_name_snake_cased}_key_out = r_{message_name_snake_cased}_key_out + "
                               f"kr_{message_name_snake_cased}_obj.{field_name_snake_cased}_")
                    for flx_fld_val in flux_fld_pk_value_list:
                        clean_fld_val = flx_fld_val.strip('\'"')
                        output += f'.{clean_fld_val}_'
                    output += ";\n"
                    output += f'\t\t\tr_{message_name_snake_cased}_key_out += "_";\n'
                else:
                    if field.kind.name.lower() == "int32" or field.kind.name.lower() == "int64":
                        output += (f"\t\t\tr_{message_name_snake_cased}_key_out = r_{message_name_snake_cased}_key_out + "
                                   f"std::to_string(kr_{message_name_snake_cased}_obj.{field_name_snake_cased}_);\n")
                        output += f'\t\t\tr_{message_name_snake_cased}_key_out += "_";\n'
                    else:
                        output += (f"\t\t\tr_{message_name_snake_cased}_key_out = r_{message_name_snake_cased}_key_out + "
                                   f"kr_{message_name_snake_cased}_obj.{field_name_snake_cased}_;\n")
                        output += f'\t\t\tr_{message_name_snake_cased}_key_out += "_";\n'

        return output

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

    def output_file_generate_handler(self, file: protogen.File):
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

        output_content += self.header_generate_handler(file_name)

        output_content += f"namespace {package_name}_handler {{\n\n"

        output_content += f"\tclass {class_name}KeyHandler "
        output_content += "{\n\n"

        output_content += "\tpublic:\n\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_json_root) or \
                    CppKeyHandlerPlugin.is_option_enabled(message, CppKeyHandlerPlugin.flux_msg_json_root_time_series):
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppKeyHandlerPlugin.is_option_enabled(field, self.flux_fld_PK):
                        # message_name = message.proto.name
                        output_content += f"\n\t\tstatic inline void get_key_out(const " \
                                          f"{message_name} &kr_{message_name_snake_cased}_obj, std::string &" \
                                          f"r_{message_name_snake_cased}_key_out)"
                        output_content += "{\n"
                        output_content += self.generate_get_key_handler(message, message_name_snake_cased)
                        output_content += "\n\t\t}\n"

                        output_content += self.generate_get_key_list(package_name, message)
                        output_content += "\t\t}\n\n"
                        break

        output_content += "\t};\n\n"
        output_content += "}\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_key_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppKeyHandlerPlugin)
