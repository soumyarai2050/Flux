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


class CppDbTestPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def get_all_root_message(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            self.root_message_list.append(message)

    def get_field_names(self, messages: List[protogen.Message]) -> None:
        for message in messages:
            if CppDbTestPlugin.is_option_enabled(message, CppDbTestPlugin.flux_msg_json_root):
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
    def header_generate_handler(file_name: str, class_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += f'#include "gtest/gtest.h"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n'
        output_content += f'#include "../../FluxCppCore/include/mongo_db_handler.h"\n'
        output_content += f'#include "../../FluxCppCore/include/mongo_db_codec.h"\n'
        output_content += f'#include "../../FluxCppCore/include/json_codec.h"\n'
        output_content += f'#include "../CppUtilGen/{class_name}_key_handler.h"\n'
        output_content += f'#include "../CppUtilGen/{class_name}_populate_random_values.h"\n\n'
        return output_content

    @staticmethod
    def generate_bulk_patch_for_test(message: protogen.Message, message_name, message_name_snake_cased: str, package_name: str,
                                     class_name: str, flux_fld_pk_value):

        output_content: str = ""

        output_content += f"\tfor (int i = 0; i < {message_name_snake_cased}_list.{message_name_snake_cased}" \
                          f"_size(); ++i) {{\n"

        key_list: List[List[str]] = StratExecutorPlugin.get_executor_key_sequence_list_of_model(message)
        for field in message.fields:
            field_name = field.proto.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message

            if not CppDbTestPlugin.is_option_enabled(field, "FluxFldPk"):

                if field_type_message is not None and field_type != "repeated":
                    for f in field_type_message.fields:
                        field_variable_type: str = f.kind.name.lower()
                        if f.message is None and f.proto.name:
                            if CppDbTestPlugin.is_option_enabled(f, CppDbTestPlugin.flux_fld_val_is_datetime):
                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                  f'{message_name_snake_cased}(i)->mutable_{field_name}()->set_' \
                                                  f'{f.proto.name}({class_name}PopulateRandomValues::get_utc_time());\n'
                            elif f.proto.name != "id":
                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                  f'{message_name_snake_cased}(i)->mutable_{field_name}()->set_' \
                                                  f'{f.proto.name}(random_data_gen.get_random_{field_variable_type}());\n'
                elif field_type_message is None and field_type != "repeated":
                    if field.kind.name.lower() != "enum" and field_name != "id":
                        if CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_val_is_datetime):
                            output_content += f'\t\t{message_name_snake_cased}_list.mutable_{message_name_snake_cased}' \
                                              f'(i)->set_{field_name}({class_name}PopulateRandomValues::get_utc_time());\n'
                        else:
                            output_content += f'\t\t{message_name_snake_cased}_list.mutable_{message_name_snake_cased}' \
                                              f'(i)->set_{field_name}(random_data_gen.get_random_' \
                                              f'{field.kind.name.lower()}());\n'
            else:
                if field_type_message is not None and field_type != "repeated":
                    for f in field_type_message.fields:
                        field_variable_type: str = f.kind.name.lower()
                        if f.message is None and f.proto.name not in flux_fld_pk_value:
                            if CppDbTestPlugin.is_option_enabled(f, CppDbTestPlugin.flux_fld_val_is_datetime):
                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                  f'{message_name_snake_cased}(i)->mutable_{field_name}()->set_' \
                                                  f'{f.proto.name}({class_name}PopulateRandomValues::get_utc_time());\n'
                            elif f.proto.name != "id":
                                output_content += f'\t\t{message_name_snake_cased}_list.mutable_' \
                                                  f'{message_name_snake_cased}(i)->mutable_{field_name}()->set_' \
                                                  f'{f.proto.name}(random_data_gen.get_random_{field_variable_type}());\n'
                elif field_type_message is None and field_type != "repeated":
                    if field.kind.name.lower() != "enum" and field_name != "id":
                        if CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_val_is_datetime):
                            output_content += f'\t\t{message_name_snake_cased}_list.mutable_{message_name_snake_cased}' \
                                              f'(i)->set_{field_name}({class_name}PopulateRandomValues::get_utc_time());\n'


        output_content += "\t}\n"
        output_content += f"\t{message_name_snake_cased}_json.clear();\n\t{message_name_snake_cased}_json_from_db" \
                          f".clear();\n\t{message_name_snake_cased}_list_from_db.Clear();\n\n"

        output_content += f'\tASSERT_TRUE({message_name_snake_cased}_codec.bulk_patch' \
                          f'({message_name_snake_cased}_list));\n'
        output_content += f'\tASSERT_TRUE({message_name_snake_cased}_codec.get_all_data_from' \
                          f'_collection({message_name_snake_cased}_list_from_db));\n\n'

        output_content += f'\tASSERT_TRUE(RootModelListJsonCodec<market_data::{message_name}List>::encode_model_list' \
                          f'({message_name_snake_cased}_list_from_db, {message_name_snake_cased}_json_from_db));\n'
        output_content += f'\tASSERT_TRUE(RootModelListJsonCodec<market_data::{message_name}List>::encode_model_list(' \
                          f'{message_name_snake_cased}_list, {message_name_snake_cased}_json));\n'
        output_content += f"\tASSERT_EQ({message_name_snake_cased}_json_from_db, {message_name_snake_cased}_json);\n"

        return output_content

    def generate_patch_for_test(self, message: protogen.Message, message_name: str,
                                message_name_snake_cased: str, class_name: str, flux_fld_pk_value):
        output_content: str = ""

        key_list: List[List[str]] = StratExecutorPlugin.get_executor_key_sequence_list_of_model(message)
        for field in message.fields:
            field_name = field.proto.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message
            if not CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_PK):
                if field_type_message is not None and field_type != "repeated":
                    for f in field_type_message.fields:
                        field_variable_type: str = f.kind.name.lower()
                        if f.message is None:
                            if CppDbTestPlugin.is_option_enabled(f, CppDbTestPlugin.flux_fld_val_is_datetime):
                                output_content += f'\t{message_name_snake_cased}.mutable_{field_name}()->set_{f.proto.name}' \
                                                  f'({class_name}PopulateRandomValues::get_utc_time());\n'
                            elif f.proto.name != "id":
                                output_content += f'\t{message_name_snake_cased}.mutable_{field_name}()->set_{f.proto.name}' \
                                                  f'(random_data_gen.get_random_{field_variable_type}());\n'
                elif field_type_message is None and field_type != "repeated":
                    if field.kind.name.lower() != "enum" and field_name != "id":
                        if CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_val_is_datetime):
                            output_content += f'\t{message_name_snake_cased}.set_{field_name}({class_name}' \
                                              f'PopulateRandomValues::get_utc_time());\n'
                        else:
                            output_content += f'\t{message_name_snake_cased}.set_{field_name}(random_data_gen.get_random_' \
                                              f'{field.kind.name.lower()}());\n'
            else:
                if field_type_message is not None and field_type != "repeated":
                    for f in field_type_message.fields:
                        field_variable_type: str = f.kind.name.lower()
                        if f.message is None and f.proto.name not in flux_fld_pk_value:
                            if CppDbTestPlugin.is_option_enabled(f, CppDbTestPlugin.flux_fld_val_is_datetime):
                                output_content += f'\t{message_name_snake_cased}.mutable_{field_name}()->set_{f.proto.name}' \
                                                  f'({class_name}PopulateRandomValues::get_utc_time());\n'
                            elif f.proto.name != "id":
                                output_content += f'\t{message_name_snake_cased}.mutable_{field_name}()->set_{f.proto.name}' \
                                                  f'(random_data_gen.get_random_{field_variable_type}());\n'
                elif field_type_message is None and field_type != "repeated":
                    if field.kind.name.lower() != "enum" and field_name != "id":
                        if CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_val_is_datetime):
                            output_content += f'\t{message_name_snake_cased}.set_{field_name}({class_name}' \
                                              f'PopulateRandomValues::get_utc_time());\n'

        output_content += f"\t{message_name_snake_cased}_from_db.Clear();\n"
        output_content += f'\n\tASSERT_TRUE({message_name_snake_cased}_codec.patch' \
                          f'({message_name_snake_cased}));\n\n'
        output_content += self.generate_assert(message_name, message_name_snake_cased, class_name, 1)

        return output_content

    @staticmethod
    def generate_assert(message_name: str, message_name_snake_cased: str, class_name: str, num_of_tabs: int):
        output_content: str = ""

        output_content += "\t"*num_of_tabs + f'ASSERT_TRUE({message_name_snake_cased}_codec.get_data_by_id_from_' \
                                             f'collection({message_name_snake_cased}' \
                                             f'_from_db, found->second));\n'
        output_content += "\t"*num_of_tabs + f"ASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::" \
                                             f"encode_model({message_name_snake_cased}_from_db, " \
                                             f"{message_name_snake_cased}_json_from_db));\n"
        output_content += "\t"*num_of_tabs + f"ASSERT_TRUE(RootModelJsonCodec<market_data::{message_name}>::" \
                                             f"encode_model({message_name_snake_cased}, " \
                                             f"{message_name_snake_cased}_json));\n"

        output_content += "\t"*num_of_tabs + f'ASSERT_EQ({message_name_snake_cased}_json_from_db, ' \
                                             f'{message_name_snake_cased}_json);\n\n'
        num_of_tabs -= 1
        # output_content += "\t"*num_of_tabs + f"}}\n"

        return output_content

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

        output_content += "quill::Logger* logger = quill::get_logger();\n"

        output_content += (f'std::shared_ptr<FluxCppCore::MongoDBHandler> sp_mongo_db = std::'
                           f'make_shared<FluxCppCore::MongoDBHandler>(logger);\n\n')

        output_content += f"using FluxCppCore::RootModelJsonCodec;\n"
        output_content += "using FluxCppCore::RootModelListJsonCodec;\n"
        output_content += "using FluxCppCore::MongoDBCodec;\n"
        output_content += f"using {package_name}_handler::{class_name}KeyHandler;\n"
        output_content += f"using {package_name}_handler::{class_name}PopulateRandomValues;\n"
        # for message in self.root_message_list:
        #
        #     if CppDbTestPlugin.is_option_enabled(message, CppDbTestPlugin.flux_msg_json_root):
        #         for field in message.fields:
        #             field_name: str = field.proto.name
        #             field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
        #             if CppDbTestPlugin.is_option_enabled(field, "FluxFldPk"):
        #                 message_name = message.proto.name
        #                 message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
        #                 output_content += f"using {class_name_snake_cased}_handler::{class_name}MongoDB{message_name}Codec;\n"

        for message in self.root_message_list:

            if CppDbTestPlugin.is_option_enabled(message, CppDbTestPlugin.flux_msg_json_root) or \
                    CppDbTestPlugin.is_option_enabled(message, CppDbTestPlugin.flux_msg_json_root_time_series):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    if CppDbTestPlugin.is_option_enabled(field, CppDbTestPlugin.flux_fld_PK):
                        flux_fld_pk_value = (CppDbTestPlugin.get_simple_option_value_from_proto
                                            (field, CppDbTestPlugin.flux_fld_PK))

                        output_content += f"\n// Helper function to generate random {message_name_snake_cased} data\n"
                        output_content += (f"void GenerateRandomData({package_name}::{message_name} "
                                           f"&{message_name_snake_cased}_obj_out) {{\n")
                        output_content += (f"\t{class_name}PopulateRandomValues::{message_name_snake_cased}"
                                           f"({message_name_snake_cased}_obj_out);\n")
                        output_content += "}\n\n"

                        output_content += f"// Helper function to perform CRUD operations on {message_name_snake_cased} objects\n"
                        output_content += (f"void PerformCRUDOperationsOn{message_name}(MongoDBCodec<{package_name}::"
                                           f"{message_name}, {package_name}::{message_name}List> "
                                           f"&{message_name_snake_cased}_codec, {package_name}::{message_name} "
                                           f"&{message_name_snake_cased}, {package_name}::{message_name} "
                                           f"&{message_name_snake_cased}_from_db, std::string "
                                           f"&{message_name_snake_cased}_json, std::string "
                                           f"&{message_name_snake_cased}_json_from_db, int32_t &new_generated_id, "
                                           f"RandomDataGen &random_data_gen) {{\n")
                        output_content += f"\tGenerateRandomData({message_name_snake_cased});\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_key;\n"
                        output_content += f"\t// Insert or update {message_name}\n"
                        output_content += (f"\tMarketDataKeyHandler::get_key_out({message_name_snake_cased}, "
                                           f"{message_name_snake_cased}_key);\n")
                        output_content += (f"\t{message_name_snake_cased}_codec.insert_or_update("
                                           f"{message_name_snake_cased}, new_generated_id);\n")
                        output_content += f"\t{message_name_snake_cased}.set_id(new_generated_id);\n"
                        output_content += (f"\tauto found = {message_name_snake_cased}_codec.m_root_model_key_to_db_id."
                                           f"find({message_name_snake_cased}_key);\n")
                        output_content += (f"\tif (found != {message_name_snake_cased}_codec."
                                           f"m_root_model_key_to_db_id.end()) {{\n")
                        output_content += f"\t\t// Retrieve {message_name_snake_cased} from the database and compare JSON\n"
                        output_content += (f"\t\tASSERT_TRUE({message_name_snake_cased}_codec."
                                           f"get_data_by_id_from_collection({message_name_snake_cased}"
                                           f"_from_db, found->second));\n")
                        output_content += (f"\t\tASSERT_TRUE(RootModelJsonCodec<{package_name}::{message_name}>::"
                                           f"encode_model({message_name_snake_cased}_from_db, "
                                           f"{message_name_snake_cased}_json_from_db));\n")
                        output_content += (f"\t\tASSERT_TRUE(RootModelJsonCodec<{package_name}::{message_name}>::"
                                           f"encode_model({message_name_snake_cased}, "
                                           f"{message_name_snake_cased}_json));\n")
                        output_content += (f"\t\tASSERT_EQ({message_name_snake_cased}_json_from_db, "
                                           f"{message_name_snake_cased}_json);\n")
                        output_content += "\t}\n\n"

                        output_content += "\t// Clear variables for the next operation\n"
                        output_content += f"\t{message_name_snake_cased}_json_from_db.clear();\n"
                        output_content += f"\t{message_name_snake_cased}_json.clear();\n\n"
                        output_content += self.generate_patch_for_test(message, message_name,
                                                                       message_name_snake_cased, class_name,
                                                                       flux_fld_pk_value)
                        output_content += f"\t{message_name_snake_cased}_json.clear();\n"
                        output_content += f"\t{message_name_snake_cased}_json_from_db.clear();\n"
                        output_content += f'\t{message_name_snake_cased}.Clear();\n'
                        output_content += f"\t{message_name_snake_cased}_from_db.Clear();\n\n"

                        output_content += f"\tASSERT_TRUE({message_name_snake_cased}_codec.delete_data_by_id_from_" \
                                          f"collection(found->second));\n"
                        output_content += f"\tASSERT_FALSE({message_name_snake_cased}_codec.get_data_by_id_from_" \
                                          f"collection({message_name_snake_cased}_from_db," \
                                          f" found->second));\n\n"
                        output_content += "}\n\n"

                        output_content += (f"// Helper function to update {message_name_snake_cased} objects and "
                                           f"perform bulk operations\n")
                        output_content += (f"void UpdateAndPerformBulkOperations(MongoDBCodec<{package_name}::"
                                           f"{message_name}, {package_name}::{message_name}List> "
                                           f"&{message_name_snake_cased}_codec, {package_name}::{message_name}List "
                                           f"&{message_name_snake_cased}_list, {package_name}::{message_name} "
                                           f"&{message_name_snake_cased}, std::vector<int32_t>& new_generated_id_list,"
                                           f"RandomDataGen &random_data_gen) {{\n")
                        output_content += (f"\t{package_name}::{message_name}List {message_name_snake_cased}"
                                           f"_list_from_db;\n")
                        output_content += f"\tstd::string {message_name_snake_cased}_json_from_db;\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                        output_content += f"\tstd::vector < std::string > {message_name_snake_cased}_key_list;\n"
                        output_content += f"\t// Update {message_name_snake_cased} objects in the list\n"
                        output_content += "\tfor (int i = 0; i <= 1000; ++i) {\n"
                        output_content += (f"\t\t{class_name}PopulateRandomValues::{message_name_snake_cased}("
                                           f"{message_name_snake_cased});\n")
                        output_content += (f"\t\t{message_name_snake_cased}_list.add_{message_name_snake_cased}()->"
                                           f"CopyFrom({message_name_snake_cased});\n")
                        output_content += "\t}\n\n"
                        output_content += f"\t// Bulk insert {message_name_snake_cased} objects\n"
                        output_content += (f"\t{class_name}KeyHandler::get_key_list({message_name_snake_cased}_list, "
                                           f"{message_name_snake_cased}_key_list);\n")
                        output_content += (f"\tASSERT_TRUE({message_name_snake_cased}_codec.bulk_insert("
                                           f"{message_name_snake_cased}_list, {message_name_snake_cased}_key_list,"
                                           f" new_generated_id_list));\n\n")
                        output_content += "\tfor (int i = 0; i <= 1000; ++i) {\n"
                        output_content += (f"\t\t{message_name_snake_cased}_list.mutable_{message_name_snake_cased}"
                                           f"(i)->set_id(new_generated_id_list[i]);\n")
                        output_content += "\t}\n\n"
                        output_content += f"\tASSERT_TRUE({message_name_snake_cased}_codec.get_all_data_from_" \
                                          f"collection({message_name_snake_cased}_list_from_db));\n"
                        output_content += f"\t{message_name_snake_cased}_json_from_db.clear();\n"
                        output_content += f"\t{message_name_snake_cased}_json.clear();\n\n"

                        output_content += f"\tASSERT_TRUE(RootModelListJsonCodec<market_data::{message_name}List>::" \
                                          f"encode_model_list({message_name_snake_cased}_list_from_db, " \
                                          f"{message_name_snake_cased}_json_from_db));\n"

                        output_content += f"\tASSERT_TRUE(RootModelListJsonCodec<market_data::{message_name}List>" \
                                          f"::encode_model_list({message_name_snake_cased}_list, " \
                                          f"{message_name_snake_cased}_json));\n"
                        output_content += f"\tASSERT_EQ({message_name_snake_cased}_json_from_db, {message_name_snake_cased}" \
                                          f"_json);\n\n"

                        output_content += self.generate_bulk_patch_for_test(message, message_name,
                                                                            message_name_snake_cased, package_name,
                                                                            class_name, flux_fld_pk_value)
                        output_content += f"\n\tASSERT_TRUE({message_name_snake_cased}_codec.delete_all_data_from_" \
                                          f"collection());\n"
                        output_content += f"\t{message_name_snake_cased}_json_from_db.clear();\n"
                        output_content += f"\t{message_name_snake_cased}_json.clear();\n"
                        output_content += f"\t{message_name_snake_cased}_list.Clear();\n"
                        output_content += f'\t{message_name_snake_cased}_list_from_db.Clear();\n\n'

                        output_content += f'\tASSERT_FALSE({message_name_snake_cased}_codec.get_all_data_from_' \
                                          f'collection({message_name_snake_cased}_list_from_db));\n'

                        output_content += "}\n"

                        output_content += f"\nTEST({class_name}{message_name}TestSuite, DBTest) {{\n\t"
                        # output_content += (f"{class_name}MongoDB{message_name}Codec {message_name_snake_cased}_codec("
                        #                    f"mongo_db, logger);\n")
                        output_content += f"MongoDBCodec<{package_name}::{message_name}, {package_name}::" \
                                          f"{message_name}List> {message_name_snake_cased}_codec(sp_mongo_db, logger);\n"
                        output_content += f'\t{package_name}::{message_name} {message_name_snake_cased};\n'
                        output_content += f'\t{package_name}::{message_name} {message_name_snake_cased}_from_db;\n'
                        output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}_list;\n'
                        output_content += f'\t{package_name}::{message_name}List {message_name_snake_cased}_list_from_db;\n'
                        output_content += f"\tstd::string {message_name_snake_cased}_json;\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_json_from_db;\n"
                        output_content += f"\tstd::string {message_name_snake_cased}_key;\n"
                        output_content += f"\tstd::vector < std::string > {message_name_snake_cased}_key_list;\n"
                        output_content += "\tRandomDataGen random_data_gen;\n"
                        output_content += "\tint32_t new_generated_id;\n"
                        output_content += "\tstd::vector < int32_t > new_generated_id_list;\n\n"

                        output_content += f"\t// Perform CRUD operations on {message_name_snake_cased} objects\n"
                        output_content += (f"\tPerformCRUDOperationsOn{message_name}({message_name_snake_cased}_codec, "
                                           f"{message_name_snake_cased}, {message_name_snake_cased}_from_db, "
                                           f"{message_name_snake_cased}_json, {message_name_snake_cased}_json_from_db,"
                                           f" new_generated_id, random_data_gen);\n\n")
                        output_content += f"\t// Update {message_name_snake_cased} objects and perform bulk operations\n"
                        output_content += (f"\tUpdateAndPerformBulkOperations({message_name_snake_cased}_codec, "
                                           f"{message_name_snake_cased}_list, {message_name_snake_cased}, "
                                           f"new_generated_id_list, random_data_gen);\n")

                        output_content += "}\n"
                        break

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_mongo_db_test.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbTestPlugin)

