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

    def get_client_url(self, message_name_snake_cased: str):

        output_content: str = ""

        output_content += f'\tconstexpr char get_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"get-all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_all_{message_name_snake_cased}' \
                          f'_client_url)> get_all_{message_name_snake_cased}_client_url_(get_all_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char get_{message_name_snake_cased}_client_url[] = ' \
                          f'"get-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_{message_name_snake_cased}_client_url)> ' \
                          f'get_{message_name_snake_cased}_client_url_(get_{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char create_{message_name_snake_cased}_client_url[] = ' \
                          f'"create-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(create_{message_name_snake_cased}' \
                          f'_client_url)> create_{message_name_snake_cased}_client_url_(create_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char create_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"create_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(create_all_{message_name_snake_cased}' \
                          f'_client_url)> create_all_{message_name_snake_cased}_client_url_(create_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char get_{message_name_snake_cased}_max_id_client_url[] = ' \
                          f'"query-get_{message_name_snake_cased}_max_id";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(get_{message_name_snake_cased}' \
                          f'_max_id_client_url)> get_{message_name_snake_cased}_max_id_client_url_(get_' \
                          f'{message_name_snake_cased}_max_id_client_url);\n'

        output_content += f'\tconstexpr char put_{message_name_snake_cased}_client_url[] = ' \
                          f'"put-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(put_{message_name_snake_cased}_client_url)> ' \
                          f'put_{message_name_snake_cased}_client_url_(put_{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char put_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"put_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(put_all_{message_name_snake_cased}_client_url)> ' \
                          f'put_all_{message_name_snake_cased}_client_url_(put_all_{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char patch_{message_name_snake_cased}_client_url[] = ' \
                          f'"patch-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(patch_{message_name_snake_cased}' \
                          f'_client_url)> patch_{message_name_snake_cased}_client_url_(patch_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char patch_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"patch_all-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(patch_all_{message_name_snake_cased}' \
                          f'_client_url)> patch_all_{message_name_snake_cased}_client_url_(patch_all_' \
                          f'{message_name_snake_cased}_client_url);\n'

        output_content += f'\tconstexpr char delete_{message_name_snake_cased}_client_url[] = ' \
                          f'"delete-{message_name_snake_cased}";\n'
        output_content += f'\tconstexpr FluxCppCore::StringLiteral<sizeof(delete_{message_name_snake_cased}' \
                          f'_client_url)> delete_{message_name_snake_cased}_client_url_(delete_' \
                          f'{message_name_snake_cased}_client_url);\n'
        output_content += f'\tconstexpr char delete_all_{message_name_snake_cased}_client_url[] = ' \
                          f'"delete_all-{message_name_snake_cased}";\n'
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
        output_content += '\tconst std::string host = getenv("HOST") ? getenv("HOST") : "127.0.0.1";\n'
        output_content += '\tconst std::string port = getenv("PORT") ? getenv("PORT") : "8040";\n\n'

        output_content += "\tconstexpr int min_pool_size_val = 2;\n"
        output_content += "\tconstexpr int max_pool_size_val = 2;\n"
        output_content += "\tconstexpr int connection_timeout = 3600;\n\n"
        file_name = str(file.proto.name).split(".")[0]
        output_content += (f'    const std::string {file_name}_db_name = getenv("DB_NAME") ? getenv("DB_NAME") : '
                           f'"{package_name}_8040";\n')

        output_content += "\n\t// key constants used across classes via constants for consistency\n"

        output_content += self.const_string_generate_handler(file)
        output_content += "\n"

        cache_msg_list: List[str] = ["market_depth", "top_of_book", "last_trade"]
        output_content += f"\n\n\t// keys for the {package_name} cython cache\n"
        output_content += f'\tconst std::string {package_name}_cache_module_name = "{package_name}_cache";\n'
        output_content += '\tconst std::string get_mutex_key = "get_mutex";\n'
        output_content += '\tconst std::string set_bid_market_depth_key = "set_bid_market_depth";\n'
        output_content += '\tconst std::string set_ask_market_depth_key = "set_ask_market_depth";\n'
        output_content += '\tconst std::string set_bid_market_depth_symbol_key = "set_bid_market_depth_symbol";\n'
        output_content += '\tconst std::string set_ask_market_depth_symbol_key = "set_ask_market_depth_symbol";\n'
        output_content += '\tconst std::string set_bid_market_depth_exch_time_key = "set_bid_market_depth_exch_time";\n'
        output_content += '\tconst std::string set_ask_market_depth_exch_time_key = "set_ask_market_depth_exch_time";\n'
        output_content += ('\tconst std::string set_bid_market_depth_arrival_time_key = '
                           '"set_bid_market_depth_arrival_time";\n')
        output_content += ('\tconst std::string set_ask_market_depth_arrival_time_key = '
                           '"set_ask_market_depth_arrival_time";\n')
        output_content += '\tconst std::string set_bid_market_depth_side_key = "set_bid_market_depth_side";\n'
        output_content += '\tconst std::string set_ask_market_depth_side_key = "set_ask_market_depth_side";\n'
        output_content += '\tconst std::string set_bid_market_depth_px_key = "set_bid_market_depth_px";\n'
        output_content += '\tconst std::string set_ask_market_depth_px_key = "set_ask_market_depth_px";\n'
        output_content += '\tconst std::string set_bid_market_depth_qty_key = "set_bid_market_depth_qty";\n'
        output_content += '\tconst std::string set_ask_market_depth_qty_key = "set_ask_market_depth_qty";\n'
        output_content += ('\tconst std::string set_bid_market_depth_market_maker_key = '
                           '"set_bid_market_depth_market_maker";\n')
        output_content += ('\tconst std::string set_ask_market_depth_market_maker_key = '
                           '"set_ask_market_depth_market_maker";\n')
        output_content += ('\tconst std::string set_bid_market_depth_is_smart_depth_key = '
                           '"set_bid_market_depth_is_smart_depth";\n')
        output_content += ('\tconst std::string set_ask_market_depth_is_smart_depth_key = '
                           '"set_ask_market_depth_is_smart_depth";\n')
        output_content += ('\tconst std::string set_bid_market_depth_cumulative_notional_key = '
                           '"set_bid_market_depth_cumulative_notional";\n')
        output_content += ('\tconst std::string set_ask_market_depth_cumulative_notional_key = '
                           '"set_ask_market_depth_cumulative_notional";\n')
        output_content += ('\tconst std::string set_bid_market_depth_cumulative_qty_key = '
                           '"set_bid_market_depth_cumulative_qty";\n')
        output_content += ('\tconst std::string set_ask_market_depth_cumulative_qty_key = '
                           '"set_ask_market_depth_cumulative_qty";\n')
        output_content += ('\tconst std::string set_bid_market_depth_cumulative_avg_px_key = '
                           '"set_bid_market_depth_cumulative_avg_px";\n')
        output_content += ('\tconst std::string set_ask_market_depth_cumulative_avg_px_key = '
                           '"set_ask_market_depth_cumulative_avg_px";\n')
        output_content += (f'\tconst std::string get_bid_market_depth_from_depth_key = '
                           f'"get_bid_market_depth_from_depth";\n')
        output_content += (f'\tconst std::string get_ask_market_depth_from_depth_key = '
                           f'"get_ask_market_depth_from_depth";\n')
        output_content += f'\tconst std::string get_last_trade_key = "get_last_trade";\n'
        output_content += f'\tconst std::string set_last_trade_key = "set_last_trade";\n'
        output_content += f'\tconst std::string set_last_trade_exch_id_key = "set_last_trade_exch_id";\n'
        output_content += f'\tconst std::string set_last_trade_exch_time_key = "set_last_trade_exch_time";\n'
        output_content += f'\tconst std::string set_last_trade_arrival_time_key = "set_last_trade_arrival_time";\n'
        output_content += f'\tconst std::string set_last_trade_px_key = "set_last_trade_px";\n'
        output_content += f'\tconst std::string set_last_trade_qty_key = "set_last_trade_qty";\n'
        output_content += f'\tconst std::string set_last_trade_premium_key = "set_last_trade_premium";\n'
        output_content += (f'\tconst std::string '
                           f'set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum_key = '
                           f'"set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum";\n')
        output_content += (f'\tconst std::string set_last_trade_market_trade_volume_applicable_period_seconds_key = '
                           f'"set_last_trade_market_trade_volume_applicable_period_seconds";\n')
        output_content += f'\tconst std::string get_top_of_book_key = "get_top_of_book";\n'
        output_content += f'\tconst std::string set_top_of_book_key = "set_top_of_book";\n'
        output_content += f'\tconst std::string get_top_of_book_bid_quote_key = "get_top_of_book_bid_quote";\n'
        output_content += f'\tconst std::string set_top_of_book_bid_quote_key = "set_top_of_book_bid_quote";\n'
        output_content += f'\tconst std::string set_top_of_book_bid_quote_px_key = "set_top_of_book_bid_quote_px";\n'
        output_content += f'\tconst std::string set_top_of_book_bid_quote_qty_key = "set_top_of_book_bid_quote_qty";\n'
        output_content += (f'\tconst std::string set_top_of_book_bid_quote_premium_key = '
                           f'"set_top_of_book_bid_quote_premium";\n')
        output_content += (f'\tconst std::string set_top_of_book_bid_quote_last_update_date_time_key = '
                           f'"set_top_of_book_bid_quote_last_update_date_time";\n')
        output_content += f'\tconst std::string get_top_of_book_ask_quote_key = "get_top_of_book_ask_quote";\n'
        output_content += f'\tconst std::string set_top_of_book_ask_quote_key = "set_top_of_book_ask_quote";\n'
        output_content += f'\tconst std::string set_top_of_book_ask_quote_px_key = "set_top_of_book_ask_quote_px";\n'
        output_content += f'\tconst std::string set_top_of_book_ask_quote_qty_key = "set_top_of_book_ask_quote_qty";\n'
        output_content += (f'\tconst std::string set_top_of_book_ask_quote_premium_key = '
                           f'"set_top_of_book_ask_quote_premium";\n')
        output_content += (f'\tconst std::string set_top_of_book_ask_quote_last_update_date_time_key = '
                           f'"set_top_of_book_ask_quote_last_update_date_time";\n')
        output_content += f'\tconst std::string get_top_of_book_last_trade_key = "get_top_of_book_last_trade";\n'
        output_content += f'\tconst std::string set_top_of_book_last_trade_key = "set_top_of_book_last_trade";\n'
        output_content += f'\tconst std::string set_top_of_book_last_trade_px_key = "set_top_of_book_last_trade_px";\n'
        output_content += f'\tconst std::string set_top_of_book_last_trade_qty_key = "set_top_of_book_last_trade_qty";\n'
        output_content += (f'\tconst std::string set_top_of_book_last_trade_premium_key = '
                           f'"set_top_of_book_last_trade_premium";\n')
        output_content += (f'\tconst std::string set_top_of_book_last_trade_last_update_date_time_key = '
                           f'"set_top_of_book_last_trade_last_update_date_time";\n')
        output_content += (f'\tconst std::string set_top_of_book_total_trading_security_size_key = '
                           f'"set_top_of_book_total_trading_security_size";\n')
        output_content += (f'\tconst std::string '
                           f'set_top_of_book_market_trade_volume_participation_period_last_trade_qty_sum_key = '
                           f'"set_top_of_book_market_trade_volume_participation_period_last_trade_qty_sum";\n')
        output_content += (f'\tconst std::string set_top_of_book_market_trade_volume_applicable_period_seconds_key = '
                           f'"set_top_of_book_market_trade_volume_applicable_period_seconds";\n')
        output_content += (f'\tconst std::string set_top_of_book_last_update_date_time_key = '
                           f'"set_top_of_book_last_update_date_time";\n')
        output_content += f'\tconst std::string market_data_cache_key = "market_data_cache";\n'
        output_content += f'\tconst std::string add_container_obj_for_symbol_key = "add_container_obj_for_symbol";\n'
        output_content += f'\tconst std::string get_market_data_container_key = "get_market_data_container";\n'
        # output_content += f'\tconst std::string last_trade_port_key = "last_trade_port";\n'
        output_content += (f'\tconst std::string set_top_of_book_market_trade_volume_key = '
                           f'"set_top_of_book_market_trade_volume";\n\n')

        for message in self.root_message_list:
            message_name = message.proto.name
            message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
            if message_name == cache_msg_list[0]:
                pass
            if CppConstantsHandlerPlugin.is_option_enabled(message, CppConstantsHandlerPlugin.flux_msg_json_root):
                output_content += f'\tconst std::string {message_name_snake_cased}_port_key = "{message_name_snake_cased}_port";\n'
                output_content += self.get_client_url(message_name_snake_cased)
                # output_content += self.generate_client_url(message_name_snake_cased, class_name_snake_cased)
            elif CppConstantsHandlerPlugin.is_option_enabled\
                (message, CppConstantsHandlerPlugin.flux_msg_json_root_time_series):
                output_content += f'\tconst std::string {message_name_snake_cased}_port_key = "{message_name_snake_cased}_port";\n'
                output_content += self.get_client_url(message_name_snake_cased)
                # output_content += self.generate_time_series_model_client_url(message_name_snake_cased, class_name_snake_cased)

        output_content += '\tconst std::string max_id_val_key = "max_id_val";\n'

        output_content += "\n}"

        output_file_name = f"{class_name_snake_cased}_constants.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppConstantsHandlerPlugin)
