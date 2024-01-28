#!/usr/bin/env python
import logging
from pathlib import PurePath
from typing import List, Callable, Tuple, Dict
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case, YAMLConfigurationManager

root_flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
root_flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path))


class CppPopulateRandomValueHandlerPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                        (message, CppPopulateRandomValueHandlerPlugin.flux_msg_json_root):
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
        output_content += f'#include "../../../../../../FluxCppCore/include/RandomDataGen.h"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'

        return output_content

    def generate_nested_fields(self, field_type_message: protogen.Message, field_name,
                               message_name_snake_cased: str, package_name: str, field: protogen.Field, parent_field: str):
        output = ""
        initial_parent_field: str = field.proto.name

        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            enums = message_field.enum
            enum_value = ""
            if enums is not None:
                for x in enums.values:
                    enum_value = x.proto.name
            if message_field.message is None:
                if field_name != initial_parent_field:
                    if field_name != parent_field and initial_parent_field != parent_field:
                        if field_type != "repeated" and message_field.kind.name.lower() != "enum":
                            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                            (message_field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                                output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->" \
                                          f"mutable_{parent_field}()->mutable_{field_name}()->set_" \
                                          f"{message_field_name}(get_utc_time());\n"
                            else:
                                if message_field_name != "id":
                                    output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->" \
                                              f"mutable_{parent_field}()->mutable_{field_name}()->set_{message_field_name}" \
                                              f"(random_data_gen.get_random_{message_field.kind.name.lower()}());\n"
                                elif message_field_name == "id" and message_field.kind.name.lower() == "string":
                                    output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->" \
                                              f"mutable_{parent_field}()->mutable_{field_name}()->set_{message_field_name}" \
                                              f"(random_data_gen.get_random_string());\n"
                        elif message_field.kind.name.lower() != "enum":
                            output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{parent_field}()." \
                                      f"mutable_{field_name}()->add_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"
                        else:
                            output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{parent_field}()->" \
                                      f"mutable_{field_name}()->set_{message_field_name}({package_name}::" \
                                      f"{enums.proto.name}::{enum_value});\n"
                    elif message_field.kind.name.lower() != "enum":
                        if field_type != "repeated":
                            output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{field_name}()->" \
                                      f"set_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"
                        else:
                            output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{field_name}()->" \
                                      f"add_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"

                else:
                    if field_type != "repeated" and message_field.kind.name.lower() != "enum":
                        if CppPopulateRandomValueHandlerPlugin.is_option_enabled \
                                    (message_field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                            output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->set_" \
                                      f"{message_field_name}(get_utc_time());\n"
                        else:
                            if message_field_name != "id":
                                output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->set_" \
                                          f"{message_field_name}(random_data_gen.get_random_" \
                                          f"{message_field.kind.name.lower()}());\n"
                            else:
                                output += f"\t\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->set_" \
                                          f"{message_field_name}(random_data_gen.get_random_string());\n"
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field and message_field.kind.name.lower() != "enum":
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                else:
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_repeated_nested_fields(message_field.message, message_name_snake_cased,
                                                               initial_parent_field, message_field_name,
                                                               package_name)
        return output

    def generate_repeated_nested_fields(self, message: protogen.Message, message_name_snake_cased, initial_parent_field,
                                        message_field_name, package_name):
        output: str = ""
        if message_name_snake_cased != initial_parent_field:
            output += f"\t\t\tauto {message_field_name} = {message_name_snake_cased}.mutable_{initial_parent_field}" \
                      f"()->add_{message_field_name}();\n"
        elif message_name_snake_cased == initial_parent_field:
            output += f"\t\t\tauto {message_field_name} = {message_name_snake_cased}->add_{message_field_name}();\n"

        for fields in message.fields:
            field_name: str = fields.proto.name
            field_type_message: protogen.Message | None = fields.message
            field_type: str = fields.cardinality.name.lower()
            field_kind: str = fields.kind.name.lower()
            if field_type_message is None and field_type != "repeated" and field_kind != "enum":
                if field_name != "id":
                    if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                                (fields, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                        output += f"\t\t\t{message_field_name}->set_{field_name}(get_utc_time());\n"
                    else:
                        output += f"\t\t\t{message_field_name}->set_{field_name}(random_data_gen.get_random_{field_kind}());\n"
                else:
                    output += f"\t\t\t{message_field_name}->set_{field_name}(random_data_gen.get_random_string());\n"
            elif field_type_message is None and field_type != "repeated" and field_kind == "enum":
                enum_field_name_list: list = fields.enum.full_name.split(".")
                enum_field_list = fields.enum.values
                output += f"\t\t\t{message_field_name}->set_{field_name}({package_name}::{enum_field_list[-1].proto.name});\n"
            elif field_type_message is None and field_type == "repeated":
                output += f"\t\t\t{message_field_name}->add_{field_name}(random_data_gen.get_random_{field_kind}());\n"
            elif field_type_message is not None and field_type != "repeated":
                field_type_message_name = convert_camel_case_to_specific_case(field_type_message.proto.name)
                for nested_field in field_type_message.fields:
                    nested_field_name = convert_camel_case_to_specific_case(nested_field.proto.name)
                    nested_field_msg = nested_field.message
                    nested_field_kind = nested_field.kind.name.lower()
                    if nested_field_msg is None and nested_field.cardinality.name.lower() != "repeated" and \
                            nested_field_kind != "enum":
                        output += f"\t\t\t{message_field_name}->mutable_{field_type_message_name}()->" \
                                  f"set_{nested_field_name}(random_data_gen.get_random_{nested_field_kind}());\n"
                    elif nested_field_msg is None and nested_field.cardinality.name.lower() != "repeated" and \
                            nested_field_kind== "enum":
                        nested_enum_field_name_list: list = nested_field.enum.full_name.split(".")
                        nested_enum_field_list = nested_field.enum.values
                        output += f"\t\t\t{message_field_name}->mutable_{field_type_message_name}()->" \
                                  f"set_{nested_field_name}({package_name}::{nested_enum_field_list[-1].proto.name});\n"

            elif field_type_message is not None and field_type == "repeated":
                field_type_message_name = convert_camel_case_to_specific_case(field_type_message.proto.name)
                output += self.generate_repeated_nested_fields(field_type_message, message_field_name,
                                                               message_field_name, field_name, package_name)

        return output
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

        output_content += self.header_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {package_name}_handler {{\n\n"

        output_content += f"\tclass {class_name}PopulateRandomValues {{ \n\n"

        output_content += "\tpublic:\n\n"

        output_content += "\t\tstatic std::string get_utc_time() {\n"
        output_content += "\t\t\tstd::chrono::system_clock::time_point now = std::chrono::system_clock::now();\n"
        output_content += "\t\t\tstd::time_t now_t = std::chrono::system_clock::to_time_t(now);\n"
        output_content += "\t\t\tchar buffer[80];\n"
        output_content += '\t\t\tstd::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S+00:00", std::gmtime(&now_t));\n'
        output_content += '\t\t\treturn std::string(buffer);\n'
        output_content += "\t\t}\n\n"

        output_content += "\t\tstatic std::string get_repeated_id_field_string() {\n"
        output_content += "\t\t\tpid_t pid = getpid();\n"
        output_content += "\t\t\tstd::string id = std::to_string(pid);\n"
        output_content += '\t\t\tid += "-";\n'
        output_content += "\t\t\tid += get_utc_time();\n"
        output_content += "\t\t\treturn id;\n"
        output_content += "\t\t}\n\n"

        for message in self.root_message_list:
            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                        (message, CppPopulateRandomValueHandlerPlugin.flux_msg_json_root) or \
                    CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                                (message, CppPopulateRandomValueHandlerPlugin.flux_msg_json_root_time_series):

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppPopulateRandomValueHandlerPlugin.is_option_enabled(field, "FluxFldPk"):
                        message_name = message.proto.name
                        message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                        output_content += (f"\t\tstatic inline void {message_name_snake_cased} ({package_name}::"
                                           f"{message_name} &{message_name_snake_cased}) {{\n\t\t")
                        output_content += "\tRandomDataGen random_data_gen;\n\n"

                        for field in message.fields:
                            field_name: str = field.proto.name
                            field_type: str = field.kind.name.lower()
                            field_type_message: protogen.Message | None = field.message

                            if field_type_message is None:
                                if field.cardinality.name.lower() == "repeated" and field_type != "enum":
                                    output_content += f'\t\t\t{message_name_snake_cased}.add_{field_name}(random_data_gen.get_random_' \
                                                      f'{field_type}());\n'
                                else:
                                    if field_type != "enum":
                                        if field_name != "id":
                                            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                                                (field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                                                output_content += f'\t\t\t{message_name_snake_cased}.set_{field_name}' \
                                                                  f'(get_utc_time());\n'
                                            else:
                                                output_content += f'\t\t\t{message_name_snake_cased}.set_{field_name}(random_data_gen.get_random_' \
                                                                  f'{field_type}());\n'
                                        else:
                                            if field_type == "string":
                                                output_content += (f'\t\t\t{message_name_snake_cased}.set_{field_name}'
                                                                   f'(random_data_gen.get_random_{field_type}());\n')
                                            else:
                                                output_content += (f'\t\t\t{message_name_snake_cased}.set_{field_name}'
                                                                   f'(RandomDataGen::get_random_int32());\n')
                                    elif field.cardinality.name.lower() == "required":
                                        enum_field_list: list = field.enum.full_name.split(".")
                                        if enum_field_list[-1] != "Side":
                                            output_content += f"\t\t\t{message_name_snake_cased}.set_{field_name}" \
                                                              f"({package_name}::{enum_field_list[-1]}::ASK);\n"
                                        else:
                                            output_content += f"\t\t\t{message_name_snake_cased}.set_{field_name}" \
                                                              f"({field_name.capitalize()}::BUY);\n"

                            elif field_type_message is not None and field.cardinality.name.lower() != "repeated":
                                output_content += self.generate_nested_fields(field_type_message, field_name,
                                                                              message_name_snake_cased, package_name, field,
                                                                              field_name)
                            elif field_type_message is not None and field.cardinality.name.lower() == "repeated":
                                output_content += f"\t\t\tauto {field_name} = {message_name_snake_cased}." \
                                                  f"add_{field_name}();\n"
                                for nested_fields in field_type_message.fields:
                                    nested_fields_name = convert_camel_case_to_specific_case(nested_fields.proto.name)
                                    nested_fields_kind = nested_fields.kind.name.lower()
                                    if nested_fields_kind != "enum":
                                        if nested_fields_name != "id":
                                            output_content += f"\t\t\t{field_name}->set_{nested_fields_name}(" \
                                                              f"random_data_gen.get_random_" \
                                                              f"{nested_fields_kind}());\n"
                                        else:
                                            output_content += f"\t\t\t{field_name}->set_{nested_fields_name}" \
                                                              f"(random_data_gen.get_random_string());\n"


                        output_content += "\t\t}\n\n"
                        break

        output_content += "\t};\n}\n\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_populate_random_values.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppPopulateRandomValueHandlerPlugin)
