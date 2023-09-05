#!/usr/bin/env python
import json
import logging
from typing import List, Callable, Tuple, Dict
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


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
        output_content += '#include "../../FluxCppCore/include/TemplateUtils.h"\n\n'

        output_content += f"namespace {package_name}_handler "
        output_content += "{\n\n"
        output_content += '    const std::string db_uri = getenv("MONGO_URI") ? getenv("MONGO_URI") : ' \
                          '"mongodb://localhost:27017";\n'
        file_name = str(file.proto.name).split(".")[0]
        output_content += f'    const std::string {file_name}_db_name = "{package_name}";\n'

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
