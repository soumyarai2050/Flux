#!/usr/bin/env python
import json
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


class CppConstantsHandlerPlugin(BaseProtoPlugin):

    """
    Plugin to generate DB Handler
    """
    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: protogen.Message) -> None:
        field_names = []
        for field in messages.fields:
            field_name: str = field.proto.name
            field_type_message: protogen.Message | None = field.message
            if field_type_message is None:
                field_names.append(field_name)
            else:
                field_names.append(field_name)
                self.get_field_names(field_type_message)

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

    def const_string_generate_handler(self, file: protogen.File):
        output_content: str = ""
        for message in file.messages:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            output_content += f'\tconst std::string {message_name_snake_cased}_msg_name = "{message_name}";\n'

        output_content += "\n\n"

        for field_name in self.field:
            output_content += f'\tconst std::string {field_name}_fld_name = "{field_name}";\n'
        return output_content

    @staticmethod
    def generate_client_url(message_name_snake_cased: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += f'\tconstexpr char get_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/get-all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_all_{message_name_snake_cased}' \
                          f'_client_url)> get_all_{message_name_snake_cased}_client_url_(get_all_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char get_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/get-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_{message_name_snake_cased}_client_url)> ' \
                          f'get_{message_name_snake_cased}_client_url_(get_{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char create_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/create-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(create_{message_name_snake_cased}' \
                          f'_client_url)> create_{message_name_snake_cased}_client_url_(create_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char create_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/create_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(create_all_{message_name_snake_cased}' \
                          f'_client_url)> create_all_{message_name_snake_cased}_client_url_(create_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char get_{message_name_snake_cased}_max_id_client_url[] = ' \
                          f'"/{class_name_snake_cased}/query-get_{message_name_snake_cased}_max_id";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_{message_name_snake_cased}' \
                          f'_max_id_client_url)> get_{message_name_snake_cased}_max_id_client_url_(get_' \
                          f'{message_name_snake_cased}_max_id_client_url);\n'

        output_content += f'\tconstexpr char put_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/put-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(put_{message_name_snake_cased}_client_url)> ' \
                          f'put_{message_name_snake_cased}_client_url_(put_{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char put_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/put_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(put_all_{message_name_snake_cased}_client_url)> ' \
                          f'put_all_{message_name_snake_cased}_client_url_(put_all_{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char patch_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/patch-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(patch_{message_name_snake_cased}' \
                          f'_client_url)> patch_{message_name_snake_cased}_client_url_(patch_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char patch_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/patch_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(patch_all_{message_name_snake_cased}' \
                          f'_client_url)> patch_all_{message_name_snake_cased}_client_url_(patch_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char delete_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/delete-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(delete_{message_name_snake_cased}' \
                          f'_client_url)> delete_{message_name_snake_cased}_client_url_(delete_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char delete_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/delete_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(delete_all_{message_name_snake_cased}' \
                          f'_client_url)> delete_all_{message_name_snake_cased}_client_url_(delete_all_' \
                          f'{message_name_snake_cased}_client_url);\n\n'

        return output_content

    @staticmethod
    def generate_time_series_model_client_url(message_name_snake_cased: str, class_name_snake_cased: str):
        output_content: str = ""
        output_content += f'\tconstexpr char get_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/get-all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_all_{message_name_snake_cased}' \
                          f'_client_url)> get_all_{message_name_snake_cased}_client_url_(get_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char create_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/create_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(create_all_{message_name_snake_cased}' \
                          f'_client_url)> create_all_{message_name_snake_cased}_client_url_(create_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char get_{message_name_snake_cased}_max_id_client_url[] = ' \
                          f'"/{class_name_snake_cased}/query-get_{message_name_snake_cased}_max_id";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_{message_name_snake_cased}' \
                          f'_max_id_client_url)> get_{message_name_snake_cased}_max_id_client_url_(get_' \
                          f'{message_name_snake_cased}_max_id_client_url);\n'

        output_content += f'\tconstexpr char put_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/put_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(put_all_{message_name_snake_cased}_client_url)> ' \
                          f'put_all_{message_name_snake_cased}_client_url_(put_all_{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char patch_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/patch_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(patch_all_{message_name_snake_cased}' \
                          f'_client_url)> patch_all_{message_name_snake_cased}_client_url_(patch_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char delete_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"/{class_name_snake_cased}/delete_all-{message_name_snake_cased}/";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(delete_all_{message_name_snake_cased}' \
                          f'_client_url)> delete_all_{message_name_snake_cased}_client_url_(delete_all_' \
                          f'{message_name_snake_cased}_client_url);\n\n'

        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)

        for message in self.root_message_list:
            self.get_field_names(message)
        package_name = str(file.proto.package)
        class_name_list = package_name.split("_")
        class_name: str = ""
        output_content: str = ""

        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += "#pragma once\n\n"
        output_content += '#include "../../../../../../FluxCppCore/include/TemplateUtils.h"\n\n'

        output_content += f"namespace {package_name}_handler "
        output_content += "{\n\n"
        output_content += '    const std::string db_uri = getenv("MONGO_URI") ? getenv("MONGO_URI") : ' \
                          '"mongodb://localhost:27017";\n'
        output_content += 'const std::string host = getenv("HOST") ? getenv("HOST") : "127.0.0.1";\n'
        output_content += 'const std::string port = getenv("PORT") ? getenv("PORT") : "8040";\n'

        file_name = str(file.proto.name).split(".")[0]
        output_content += (f'    const std::string {file_name}_db_name = getenv("DB_NAME") ? getenv("DB_NAME") : '
                           f'"{package_name}_8040";\n')

        output_content += "\n\t// key constants used across classes via constants for consistency\n"

        output_content += self.const_string_generate_handler(file)
        output_content += "\n"

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if CppConstantsHandlerPlugin.is_option_enabled(message, CppConstantsHandlerPlugin.flux_msg_json_root):
                output_content += self.generate_client_url(message_name_snake_cased, class_name_snake_cased)
            elif CppConstantsHandlerPlugin.is_option_enabled\
                (message, CppConstantsHandlerPlugin.flux_msg_json_root_time_series):
                output_content += self.generate_time_series_model_client_url(message_name_snake_cased, class_name_snake_cased)

        output_content += '\tconst std::string max_id_val_key = "max_id_val";\n'

        output_content += "\n}"

        output_file_name = f"{class_name_snake_cased}_constants.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppConstantsHandlerPlugin)
