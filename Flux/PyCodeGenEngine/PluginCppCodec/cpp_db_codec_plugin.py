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

flux_core_config_yaml_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
flux_core_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(flux_core_config_yaml_path))


class CppDbHandlerPlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to serialize and deserialize from proto schema
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
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                field_names = [field.proto.name for field in message.fields]

                for field_name in field_names:
                    if field_name not in self.field:
                        self.field.append(field_name)

    def dependency_message_proto_msg_handler(self, file: protogen.File):
        # Adding messages from core proto files having json_root option
        core_or_util_files = flux_core_config_yaml_dict.get("core_or_util_files")
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
    def headers_generate_handler(file_name: str, class_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        # j+Csh04P15QLolwboE9xsA001fPuo8VAE-pb1OOU0+4M4M0jE-mPfDCQZ
        # output_content += "#include <mutex>\n"
        # output_content += "#include <unordered_map>\n\n"
        # output_content += f'#include "../../cpp_app/include/{class_name}_mongo_db_handler.h"\n'
        # output_content += f'#include "../CppUtilGen/{class_name}_key_handler.h"\n'
        # output_content += f'#include "../../FluxCppCore/include/market_data_json_codec.h"\n'
        # output_content += f'#include "../CppUtilGen/{class_name}_max_id_handler.h"\n'
        output_content += f'#include "../../FluxCppCore/include/json_codec.h"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'
        return output_content

    def generate_repeated_nested_fields(self, message: protogen.Message, field_name, package_name,
                                        message_name_snake_cased, field, initial_parent, num_of_tabs: int | None = None):
        if num_of_tabs is None:
            num_of_tabs = 5

        output = ""
        parent_field = field.proto.name

        if parent_field != field_name:
            output += f'\t\t\tif (kr_{message_name_snake_cased}_obj.{parent_field}().{field_name}_size() > 0) {{\n'
            output += f'\t\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n'
            output += f'\t\t\t\tfor (const auto& {field_name}_doc : kr_{message_name_snake_cased}_obj.{parent_field}().' \
                      f'{field_name}()) {{\n'
            output += f'\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\tif (kr_{message_name_snake_cased}_obj.{parent_field}_size() > 0) {{\n'
                output += f'\t\t\tbsoncxx::builder::basic::array {parent_field}_list;\n'
                output += f'\t\t\tfor (const auto& {field_name}_doc : kr_{message_name_snake_cased}_obj.{parent_field}()) {{\n'
                output += f'\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
            else:
                output += "\t"*num_of_tabs + f'if ({initial_parent}_doc.{parent_field}_size() > 0) {{\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'bsoncxx::builder::basic::array {parent_field}_list;\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'for (const auto& {parent_field}_doc : {initial_parent}_doc.{parent_field}()) {{\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'bsoncxx::builder::basic::document {parent_field}_document;\n'

        for message_field in message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            local_num_of_tabs = num_of_tabs
            if message_field.message is None:
                if field_type != "repeated":
                    if parent_field != field_name:
                        if message_field_name == "id":
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp("' \
                                          f'_id", {field_name}_doc.{message_field_name}()));\n'
                            else:
                                output += f'\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp("' \
                                          f'_id", {field_name}_doc.{message_field_name}()));\n'
                        else:
                            if not CppDbHandlerPlugin.is_option_enabled(message_field,
                                                                        CppDbHandlerPlugin.flux_fld_val_time_field):
                                if field_type == "required":
                                    output += f'\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                              f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc' \
                                              f'.{message_field_name}()));\n'
                                else:
                                    output += f'\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                                    output += f'\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                              f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc' \
                                              f'.{message_field_name}()));\n'
                            else:
                                if field_type == "required":
                                    output += f'\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                              f'{package_name}_handler::{message_field_name}_fld_name, FluxCppCore'\
                                               f'::StringUtil::convert_utc_string_to_b_date({field_name}_doc' \
                                              f'.{message_field_name}())));\n'
                                else:
                                    output += f'\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                                    output += f'\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                              f'{package_name}_handler::{message_field_name}_fld_name, FluxCppCore'\
                                               f'::StringUtil::convert_utc_string_to_b_date({field_name}_doc' \
                                              f'.{message_field_name}())));\n'
                    else:
                        if initial_parent == parent_field and parent_field == field_name:
                            if message_field_name == "id":
                                if field_type == "required":
                                    output += f'\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp("' \
                                              f'_id", {parent_field}_doc.{message_field_name}()));\n'
                                else:
                                    output += f'\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                    output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp("' \
                                              f'_id", {parent_field}_doc.{message_field_name}()));\n'
                            else:
                                if not CppDbHandlerPlugin.is_option_enabled(message_field,
                                                                            CppDbHandlerPlugin.flux_fld_val_time_field):
                                    if field_type == "required":
                                        output += f'\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp(' \
                                                  f'{package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                                  f'{message_field_name}()));\n'
                                    else:
                                        output += f'\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                        output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp(' \
                                                  f'{package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                                  f'{message_field_name}()));\n'
                                else:
                                    if field_type == "required":
                                        output += f'\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp(' \
                                                  f'{package_name}_handler::{message_field_name}_fld_name, '\
                                                   f'FluxCppCore::StringUtil::convert_utc_string_to_b_date('\
                                                    f'{parent_field}_doc.{message_field_name}())));\n'
                                    else:
                                        output += f'\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                        output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp(' \
                                                  f'{package_name}_handler::{message_field_name}_fld_name, '\
                                                   f'FluxCppCore::StringUtil::convert_utc_string_to_b_date('\
                                                    f'{parent_field}_doc.{message_field_name}())));\n'
                        else:
                            if message_field_name == "id":
                                if field_type == "required":
                                    output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore'\
                                                                          f'::kvp("_id", {parent_field}' \
                                                                         f'_doc.{message_field_name}()));\n'
                                else:
                                    output += "\t" * local_num_of_tabs + f'if ({parent_field}_doc.has_' \
                                                                         f'{message_field_name}())\n'
                                    local_num_of_tabs += 1
                                    output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                         f'::kvp("_id", {parent_field}' \
                                                                         f'_doc.{message_field_name}()));\n'
                            else:
                                if not CppDbHandlerPlugin.is_option_enabled(message_field,
                                                                            CppDbHandlerPlugin.flux_fld_val_time_field):
                                    if field_type == "required":
                                        output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                             f'::kvp({package_name}_handler::' \
                                                                             f'{message_field_name}_fld_name, ' \
                                                                             f'{parent_field}_doc.{message_field_name}()));\n'
                                    else:
                                        output += "\t"*local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                        local_num_of_tabs += 1
                                        output += "\t"*local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                           f'::kvp({package_name}_handler::' \
                                                                           f'{message_field_name}_fld_name, ' \
                                                                           f'{parent_field}_doc.{message_field_name}()));\n'
                                else:
                                    if field_type == "required":
                                        output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                             f'::kvp({package_name}_handler::' \
                                                                             f'{message_field_name}_fld_name, ' \
                                                                             f'FluxCppCore::StringUtil::'\
                                                                              f'convert_utc_string_to_b_date('\
                                                                              f'{parent_field}_doc.'\
                                                                              f'{message_field_name}())));\n'
                                    else:
                                        output += "\t"*local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                        local_num_of_tabs += 1
                                        output += "\t"*local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                           f'::kvp({package_name}_handler::' \
                                                                           f'{message_field_name}_fld_name, ' \
                                                                           f'FluxCppCore::StringUtil::'\
                                                                            f'convert_utc_string_to_b_date('\
                                                                            f'{parent_field}_doc.'\
                                                                            f'{message_field_name}())));\n'
                else:
                    output += f'\t\t\t\tif ({parent_field}_doc.{message_field_name}_size() > 0) {{\n'
                    output += f'\t\t\t\t\tbsoncxx::builder::basic::array {message_field_name}_list;\n'
                    output += f'\t\t\t\t\tfor (const auto& {message_field_name}_doc : {parent_field}_doc.' \
                              f'{message_field_name}()){{\n'
                    output += f'\t\t\t\t\t\t{message_field_name}_list.append({message_field_name}_doc);\n'
                    output += "\t\t\t\t\t}\n"
                    output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp' \
                              f'({package_name}_handler::{message_field_name}_fld_name, {message_field_name}_list));\n'

                    output += "\t\t\t\t}\n"

            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_repeated_nested_fields(message_field.message, message_field_name,
                                                               package_name,
                                                               message_name_snake_cased, message_field, field_name,
                                                               num_of_tabs)
            elif message_field.message is not None and field_type != "repeated":
                message_field_name1 = convert_camel_case_to_specific_case(message_field.message.proto.name)
                output += "\t" * num_of_tabs + f"bsoncxx::builder::basic::document {message_field_name}_document;\n"
                for field in message_field.message.fields:
                    field_name1 = convert_camel_case_to_specific_case(field.proto.name)
                    field_cardinality = field.cardinality.name.lower()
                    # LZUWDOV6ISYpiG-S7CaGYUN3assS9xeUkqPD7elDTEv9GLG1yPWcYd
                    # if field_cardinality == "required":
                    output += "\t" * num_of_tabs + f"{message_field_name}_document.append(FluxCppCore::kvp({field_name1}_fld_name, " \
                                                   f"{parent_field}_doc.{message_field_name}().{field_name1}()));\n"
                output += "\t" * num_of_tabs + f"{parent_field}_document.append(FluxCppCore::kvp({message_field_name}_fld_name, " \
                                               f"{message_field_name}_document));\n"

        if parent_field != field_name:
            output += f'\t\t\t\t\t{field_name}_list.append({field_name}_document);\n'
            output += "\t\t\t\t}\n"
            output += f"\t\t\t\t{parent_field}_doc.append(FluxCppCore::kvp({package_name}_handler::{field_name}_fld_name," \
                      f" {field_name}_list));\n"
            output += "\n\t\t\t}\n"
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\t\t{parent_field}_list.append({parent_field}_document);\n'
                output += f'\t\t\t}}\n\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp' \
                          f'({package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                output += "\t\t}\n"
            else:
                output += "\t"*num_of_tabs + f'{parent_field}_list.append({parent_field}_document);\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"
                output += "\t"*num_of_tabs + f'{initial_parent}_document.append(FluxCppCore::kvp(' \
                                             f'{package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"

        return output

    def generate_msg_repeated_nested_fields(self, message: protogen.Message, field_name, package_name,
                                            message_name_snake_cased, field, initial_parent,
                                            num_of_tabs: int | None = None):
        if num_of_tabs is None:
            num_of_tabs = 5

        output = ""
        parent_field = field.proto.name

        if parent_field != field_name:
            output += f'\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{parent_field}' \
                      f'().{field_name}_size() > 0) {{\n'
            output += f'\t\t\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n'
            output += f'\t\t\t\t\tfor (const auto& {field_name}_doc : r_{message_name_snake_cased}_list_obj.' \
                      f'{message_name_snake_cased}(i).{parent_field}().{field_name}()) {{\n'
            output += f'\t\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{parent_field}' \
                          f'_size() > 0) {{\n'
                output += f'\t\t\t\tbsoncxx::builder::basic::array {parent_field}_list;\n'
                output += f'\t\t\t\tfor (const auto& {field_name}_doc : r_{message_name_snake_cased}_list_obj.' \
                          f'{message_name_snake_cased}(i).{parent_field}()) {{\n'
                output += f'\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
            else:
                output += "\t"*num_of_tabs + f'if ({initial_parent}_doc.{parent_field}_size() > 0) {{\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'bsoncxx::builder::basic::array {parent_field}_list;\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'for (const auto& {parent_field}_doc : {initial_parent}_doc.{parent_field}()) {{\n'
                num_of_tabs += 1
                output += "\t"*num_of_tabs + f'bsoncxx::builder::basic::document {parent_field}_document;\n'

        for message_field in message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            local_num_of_tabs = num_of_tabs
            if message_field.message is None:
                if field_type != "repeated":
                    if parent_field != field_name:
                        if message_field_name == "id":
                            if field_type == "required":
                                output += f'\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp("' \
                                          f'_id", {field_name}_doc.{message_field_name}()));\n'
                            else:
                                output += f'\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp("' \
                                          f'_id", {field_name}_doc.{message_field_name}()));\n'
                        else:
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                          f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc.' \
                                          f'{message_field_name}()));\n'
                            else:
                                output += f'\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t\t{field_name}_document.append(FluxCppCore::kvp(' \
                                          f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc.' \
                                          f'{message_field_name}()));\n'
                    else:
                        if initial_parent == parent_field and parent_field == field_name:
                            if message_field_name == "id":
                                if field_type == "required":
                                    output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp("' \
                                              f'_id", {parent_field}_doc.{message_field_name}()));\n'
                                else:
                                    output += f'\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                    output += f'\t\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp("' \
                                              f'_id", {parent_field}_doc.{message_field_name}()));\n'
                            else:
                                if field_type == "required":
                                    output += f'\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp' \
                                              f'({package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                              f'{message_field_name}()));\n'
                                else:
                                    output += f'\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                    output += f'\t\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp' \
                                              f'({package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                              f'{message_field_name}()));\n'
                        else:
                            if message_field_name == "_id":
                                if field_type == "required":
                                    output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                         f'::kvp("_id", {parent_field}_doc.' \
                                                                         f'{message_field_name}()));\n'
                                else:
                                    output += "\t"*local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                    local_num_of_tabs += 1
                                    output += "\t"*local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                       f'::kvp("_id", {parent_field}_doc.' \
                                                                       f'{message_field_name}()));\n'
                            else:
                                if field_type == "required":
                                    output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                         f'::kvp({package_name}_handler::' \
                                                                         f'{message_field_name}_fld_name, {parent_field}_doc' \
                                                                         f'.{message_field_name}()));\n'
                                else:
                                    output += "\t" * local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                    local_num_of_tabs += 1
                                    output += "\t" * local_num_of_tabs + f'{parent_field}_document.append(FluxCppCore' \
                                                                         f'::kvp({package_name}_handler::' \
                                                                         f'{message_field_name}_fld_name, {parent_field}_doc' \
                                                                         f'.{message_field_name}()));\n'
                else:
                    output += f'\t\t\t\t\tif ({parent_field}_doc.{message_field_name}_size() > 0) {{\n'
                    output += f'\t\t\t\t\t\tbsoncxx::builder::basic::array {message_field_name}_list;\n'
                    output += f'\t\t\t\t\t\tfor (const auto& {message_field_name}_doc : {parent_field}_doc.' \
                              f'{message_field_name}()){{\n'
                    output += f'\t\t\t\t\t\t\t{message_field_name}_list.append({message_field_name}_doc);\n'
                    output += "\t\t\t\t\t\t}\n"
                    output += f'\t\t\t\t\t\t{parent_field}_document.append(FluxCppCore::kvp' \
                              f'({package_name}_handler::{message_field_name}_fld_name, {message_field_name}_list));\n'

                    output += "\t\t\t\t\t}\n"

            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_msg_repeated_nested_fields(message_field.message, message_field_name,
                                                                   package_name, message_name_snake_cased,
                                                                   message_field, field_name, num_of_tabs)
            elif message_field.message is not None and field_type != "repeated":
                message_field_name1 = convert_camel_case_to_specific_case(message_field.message.proto.name)
                output += "\t" * num_of_tabs + f"bsoncxx::builder::basic::document {message_field_name}_document;\n"
                for field in message_field.message.fields:
                    field_name1 = convert_camel_case_to_specific_case(field.proto.name)
                    field_cardinality = field.cardinality.name.lower()
                    # Q7ecC-x-dVXLcorn+fPIfrXqkidxMHUvJJINGCAd8tfLhiRUfqCoi6x+
                    # if field_cardinality == "required":
                    output += "\t" * num_of_tabs + f"{message_field_name}_document.append(FluxCppCore::kvp({field_name1}_fld_name, " \
                                                   f"{parent_field}_doc.{message_field_name}().{field_name1}()));\n"
                output += "\t" * num_of_tabs + f"{parent_field}_document.append(FluxCppCore::kvp({message_field_name}_fld_name, " \
                                               f"{message_field_name}_document));\n"


        if parent_field != field_name:
            output += f'\t\t\t\t\t\t{field_name}_list.append({field_name}_document);\n'
            output += "\t\t\t\t\t}\n"
            output += f"\t\t\t\t\t{parent_field}_doc.append(FluxCppCore::kvp({package_name}_handler::" \
                      f"{field_name}_fld_name, {field_name}_list));\n"
            output += "\n\t\t\t}\n"
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\t\t\t{parent_field}_list.append({parent_field}_document);\n'
                output += f'\t\t\t\t}}\n\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp' \
                          f'({package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                output += "\t\t\t}\n"
            else:
                output += "\t"*num_of_tabs + f'{parent_field}_list.append({parent_field}_document);\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"
                output += "\t"*num_of_tabs + f'{initial_parent}_document.append(FluxCppCore::kvp(' \
                                            f'{package_name}_handler::{parent_field}_fld_name,' \
                                            f' {parent_field}_list));\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"

        return output

    def generate_nested_fields(self, field_type_message: protogen.Message, field_name,
                               message_name_snake_cased: str, package_name: str, field: protogen.Field, parent_feild: str):
        output = ""
        initial_parent_field: str = field.proto.name
        # WnrLdfWAHxtyihghkeS5yCmY6LyqnBMbcf5lfceLsHazdjnZNCbPrCvZc
        # field_name: str = field.proto.name
        # print(f".............{field.parent.proto.name}...............")
        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            if message_field.message is None and field_type != "repeated":
                if field_name != initial_parent_field:
                    if field_name != parent_feild and initial_parent_field != parent_feild:
                        if not CppDbHandlerPlugin.is_option_enabled(message_field, CppDbHandlerPlugin.flux_fld_val_time_field):
                            if field_type == "required":
                                output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                            else:
                                output += f"\t\t\t\tif (kr_{message_name_snake_cased}_obj.{initial_parent_field}()." \
                                          f"{parent_feild}().{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                        else:
                            if field_type == "required":
                                output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}())));\n'
                            else:
                                output += f"\t\t\t\tif (kr_{message_name_snake_cased}_obj.{initial_parent_field}()." \
                                          f"{parent_feild}().{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}())));\n'
                    else:
                        if not CppDbHandlerPlugin.is_option_enabled(message_field, CppDbHandlerPlugin.flux_fld_val_time_field):
                            if field_type == "required":
                                output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{field_name}().{message_field_name}()));\n'
                            else:
                                output += f"\t\t\t\tif (kr_{message_name_snake_cased}_obj.{initial_parent_field}()." \
                                          f"{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{field_name}().{message_field_name}()));\n'
                        else:
                            if field_type == "required":
                                output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{field_name}().{message_field_name}())));\n'
                            else:
                                output += f"\t\t\t\tif (kr_{message_name_snake_cased}_obj.{initial_parent_field}()." \
                                          f"{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.' \
                                          f'{initial_parent_field}().{field_name}().{message_field_name}())));\n'
                else:
                    if not CppDbHandlerPlugin.is_option_enabled(message_field, CppDbHandlerPlugin.flux_fld_val_time_field):
                        if field_type == "required":
                            output += f'\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                      f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.{field_name}' \
                                      f'().{message_field_name}()));\n'
                        else:
                            output += f"\t\t\tif (kr_{message_name_snake_cased}_obj.{field_name}().has_{message_field_name}())\n"
                            output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                      f'_handler::{message_field_name}_fld_name, kr_{message_name_snake_cased}_obj.{field_name}' \
                                      f'().{message_field_name}()));\n'
                    else:
                        if field_type == "required":
                            output += f'\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                      f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                       f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.{field_name}' \
                                      f'().{message_field_name}())));\n'
                        else:
                            output += f"\t\t\tif (kr_{message_name_snake_cased}_obj.{field_name}().has_{message_field_name}())\n"
                            output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                      f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                       f'convert_utc_string_to_b_date(kr_{message_name_snake_cased}_obj.{field_name}' \
                                      f'().{message_field_name}()));\n'
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field:
                    output += f"\t\t\tif (kr_{message_name_snake_cased}_obj.{initial_parent_field}()." \
                              f"{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += f"\t\t\t\tbsoncxx::builder::basic::document {message_field_name}_doc;\n"
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                else:
                    output += f"\t\t\tif (kr_{message_name_snake_cased}_obj.{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += f"\t\t\t\tbsoncxx::builder::basic::document {message_field_name}_doc;\n"
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler::' \
                          f'{message_field_name}_fld_name, {message_field_name}_doc));\n'
                output += f"\t\t\t}}\n"
            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_repeated_nested_fields(message_field.message, message_field_name, package_name,
                                                               message_name_snake_cased, field, field_name, 5)
        return output

    def generate_msg_nested_fields(self, field_type_message: protogen.Message, field_name,
                                   message_name_snake_cased: str, package_name: str, field: protogen.Field,
                                   parent_feild: str):
        output = ""
        initial_parent_field: str = field.proto.name
        # 5Coy]3IhZJl-ULje+D8c4Q53WXUYAKw8YdODGUu0VCpcC7RfSB0GUd1uA
        # field_name: str = field.proto.name
        # print(f".............{field.parent.proto.name}...............")
        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            if message_field.message is None and field_type != "repeated":
                if field_name != initial_parent_field:
                    if field_name != parent_feild and initial_parent_field != parent_feild:
                        if not CppDbHandlerPlugin.is_option_enabled(message_field,
                                                                    CppDbHandlerPlugin.flux_fld_val_time_field):
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                            else:
                                output += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                          f"{initial_parent_field}().{parent_feild}().{field_name}()." \
                                          f"has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                        else:
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}())));\n'
                            else:
                                output += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                          f"{initial_parent_field}().{parent_feild}().{field_name}()." \
                                          f"has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).' \
                                          f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}())));\n'
                    else:
                        if not CppDbHandlerPlugin.is_option_enabled(message_field,
                                                                    CppDbHandlerPlugin.flux_fld_val_time_field):
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).{initial_parent_field}().{field_name}().' \
                                          f'{message_field_name}()));\n'
                            else:
                                output += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                          f"{initial_parent_field}().{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).{initial_parent_field}().{field_name}().' \
                                          f'{message_field_name}()));\n'
                        else:
                            if field_type == "required":
                                output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).{initial_parent_field}().{field_name}().' \
                                          f'{message_field_name}())));\n'
                            else:
                                output += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                          f"{initial_parent_field}().{field_name}().has_{message_field_name}())\n"
                                output += f'\t\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}' \
                                          f'_handler::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                           f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.' \
                                          f'{message_name_snake_cased}(i).{initial_parent_field}().{field_name}().' \
                                          f'{message_field_name}())));\n'
                else:
                    if not CppDbHandlerPlugin.is_option_enabled(message_field, CppDbHandlerPlugin.flux_fld_val_time_field):
                        if field_type == "required":
                            output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler' \
                                      f'::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}' \
                                      f'(i).{field_name}().{message_field_name}()));\n'
                        else:
                            output += f"\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"{field_name}().has_{message_field_name}())\n"
                            output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler' \
                                      f'::{message_field_name}_fld_name, r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}' \
                                      f'(i).{field_name}().{message_field_name}()));\n'
                    else:
                        if field_type == "required":
                            output += f'\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler' \
                                      f'::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                       f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.'\
                                        f'{message_name_snake_cased}(i).{field_name}().{message_field_name}())));\n'
                        else:
                            output += f"\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"{field_name}().has_{message_field_name}())\n"
                            output += f'\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler' \
                                      f'::{message_field_name}_fld_name, FluxCppCore::StringUtil::'\
                                       f'convert_utc_string_to_b_date(r_{message_name_snake_cased}_list_obj.'\
                                       f'{message_name_snake_cased}(i).{field_name}().{message_field_name}())));\n'
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field:
                    output += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                              f"{initial_parent_field}().{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += f"\t\t\t\t\tbsoncxx::builder::basic::document {message_field_name}_doc;\n"
                    output += self.generate_msg_nested_fields(message_field.message, message_field_name,
                                                              message_name_snake_cased, package_name, field, field_name)
                else:
                    output += f"\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{field_name}()" \
                              f".has_{message_field_name}()) "
                    output += f"{{\n"
                    output += f"\t\t\t\t\tbsoncxx::builder::basic::document {message_field_name}_doc;\n"
                    output += self.generate_msg_nested_fields(message_field.message, message_field_name,
                                                              message_name_snake_cased, package_name, field, field_name)
                output += f"\t\t\t\t\t{field_name}_doc.append(FluxCppCore::kvp({package_name}_handler::" \
                          f"{message_field_name}_fld_name, {message_field_name}_doc));\n"
                output += f"\t\t\t\t}}\n"
            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_msg_repeated_nested_fields(message_field.message, message_field_name, package_name,
                                                                   message_name_snake_cased, field, field_name)
        return output

    def generate_prepare_doc(self, message: protogen.Message, message_name_snake_cased: str,
                             package_name: str, message_name: str):
        output_content: str = ""
        # output_content += f"\tprotected:\n\n"
        output_content += f"\tvoid prepare_doc(const {package_name}::{message_name} " \
                          f"&kr_{message_name_snake_cased}_obj, bsoncxx::builder::basic::document " \
                          f"&r_{message_name_snake_cased}_document) "
        output_content += " {\n"

        for field in message.fields:
            field_name = field.proto.name
            field_kind = field.kind.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message

            if field_type_message is None:
                if field_type != "repeated":
                    if field_name != "id":
                        if not CppDbHandlerPlugin.is_option_enabled(field, CppDbHandlerPlugin.flux_fld_val_time_field):
                            if field_type == "required":
                                output_content += (f"\t\tr_{message_name_snake_cased}_document.append(FluxCppCore"
                                                   f"::kvp({package_name}_handler::{field_name}_fld_name, "
                                                   f"kr_{message_name_snake_cased}_obj.{field_name}()));\n")
                            else:
                                output_content += f"\t\tif (kr_{message_name_snake_cased}_obj.has_{field_name}())\n"
                                output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                                  f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                                  f"kr_{message_name_snake_cased}_obj.{field_name}()));\n"
                        else:
                            if field_type == "required":
                                output_content += (f"\t\tr_{message_name_snake_cased}_document.append(FluxCppCore"
                                                   f"::kvp({package_name}_handler::{field_name}_fld_name, "
                                                   f"FluxCppCore::StringUtil::convert_utc_string_to_b_date("
                                                   f"kr_{message_name_snake_cased}_obj.{field_name}())));\n")
                            else:
                                output_content += f"\t\tif (kr_{message_name_snake_cased}_obj.has_{field_name}())\n"
                                output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                                  f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                                  f"FluxCppCore::StringUtil::convert_utc_string_to_b_date("\
                                                  f"kr_{message_name_snake_cased}_obj.{field_name}())));\n"

                else:
                    output_content += f"\t\tif (kr_{message_name_snake_cased}_obj.{field_name}_size() > 0)\n"
                    output_content += f"\t\t{{\n"
                    output_content += f"\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n"
                    output_content += f"\t\t\tfor (int i = 0; i < kr_{message_name_snake_cased}_obj.{field_name}_size(); ++i)\n"
                    output_content += f"\t\t\t\t{field_name}_list.append(kr_{message_name_snake_cased}_obj.{field_name}(i));\n"
                    output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp" \
                                      f"({package_name}_handler::{field_name}_fld_name, {field_name}_list));\n"
                    output_content += f"\t\t}}\n"

            else:
                if field_type != "repeated":
                    output_content += f"\t\tif (kr_{message_name_snake_cased}_obj.has_{field_name}())"
                    output_content += f" {{\n"
                    output_content += f"\t\t\tbsoncxx::builder::basic::document {field_name}_doc;\n"
                    # print(f".............{field.proto.name}...............")
                    output_content += self.generate_nested_fields(field_type_message, field_name,
                                                                  message_name_snake_cased, package_name, field,
                                                                  field_name)
                    output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp(" \
                                      f"{package_name}_handler::{field_name}_fld_name, {field_name}_doc));\n"
                    output_content += f"\t\t}}\n"

                else:
                    output_content += self.generate_repeated_nested_fields(field_type_message, field_name,
                                                                           package_name, message_name_snake_cased,
                                                                           field, field_name)
        return output_content

    def generate_prepare_docs(self, message: protogen.Message, message_name_snake_cased: str,
                              package_name: str, message_name: str):

        output_content: str = ""
        output_content += f"\tvoid prepare_list_doc(const {package_name}::{message_name}List " \
                          f"&r_{message_name_snake_cased}_list_obj, std::vector<bsoncxx::builder::basic::document> " \
                          f"&r_{message_name_snake_cased}_document_list) "
        output_content += " {\n"
        output_content += f"\t\tfor (int i =0; i < r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}_size(); " \
                          f"++i) {{\n"
        output_content += f"\t\t\tbsoncxx::builder::basic::document r_{message_name_snake_cased}_document;\n"

        for field in message.fields:
            field_name = field.proto.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message

            if field_type_message is None:
                if field_type != "repeated":
                    if not CppDbHandlerPlugin.is_option_enabled(field, CppDbHandlerPlugin.flux_fld_val_time_field):
                        if field_name != "id":
                            if field_type == "required":
                                output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                                  f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                                  f"r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                                  f"{field_name}()));\n"
                            else:
                                output_content += f"\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                                  f"has_{field_name}())\n"
                                output_content += f"\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                                  f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                                  f"r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                                  f"{field_name}()));\n"
                    else:
                        if field_type == "required":
                            output_content += f"\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                              f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                              f"FluxCppCore::StringUtil::convert_utc_string_to_b_date("\
                                               f"r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"{field_name}())));\n"
                        else:
                            output_content += f"\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"has_{field_name}())\n"
                            output_content += f"\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::" \
                                              f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                              f"FluxCppCore::StringUtil::convert_utc_string_to_b_date("\
                                               f"r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"{field_name}())));\n"
                    # at+4iH1j6iJECmU1wU7uY7Jt5Exr7M7foYXMuJVBZX3yc32W8vIdoFO4+
                    # else:
                    #     if field_type == "required":
                    #         output_content += "\t\t\t\tif (IsUpdateOrPatch::DB_FALSE == is_update_or_patch) {\n"
                    #         output_content += f'\t\t\t\t\tr_{message_name_snake_cased}_document.append(' \
                    #                           f'FluxCppCore::kvp("_id", r_{message_name_snake_cased}_list_obj.' \
                    #                           f'{message_name_snake_cased}(i).{field_name}()));\n'
                    #     else:
                    #         output_content += "\t\t\t\tif (IsUpdateOrPatch::DB_FALSE == update_or_patch) {\n"
                    #         output_content += f"\t\t\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                    #                           f"has_{field_name}())\n"
                    #         output_content += f'\t\t\t\t\tr_{message_name_snake_cased}_document.append(' \
                    #                           f'FluxCppCore::kvp("_id", r_{message_name_snake_cased}_list_obj.' \
                    #                           f'{message_name_snake_cased}(i).{field_name}()));\n'
                    #     output_content += "\t\t\t\t}\n"
                else:
                    output_content += f"\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"{field_name}_size() > 0)\n"
                    output_content += f"\t\t\t{{\n"
                    output_content += f"\t\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n"
                    output_content += f"\t\t\t\tfor (int i = 0; i < r_{message_name_snake_cased}_list_obj." \
                                      f"{message_name_snake_cased}(i).{field_name}_size(); ++i)\n"
                    output_content += f"\t\t\t\t\t{field_name}_list.append(r_{message_name_snake_cased}_list_obj." \
                                      f"{message_name_snake_cased}(i).{field_name}(i));\n"
                    output_content += f"\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp" \
                                      f"({package_name}_handler::{field_name}_fld_name, {field_name}_list));\n"
                    output_content += f"\t\t\t}}\n"

            else:
                if field_type != "repeated":
                    output_content += f"\t\t\tif (r_{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"has_{field_name}())"
                    output_content += f" {{\n"
                    output_content += f"\t\t\t\tbsoncxx::builder::basic::document {field_name}_doc;\n"
                    # print(f".............{field.proto.name}...............")
                    output_content += self.generate_msg_nested_fields(field_type_message, field_name,
                                                                      message_name_snake_cased, package_name, field,
                                                                      field_name)
                    output_content += f"\t\t\t\tr_{message_name_snake_cased}_document.append(FluxCppCore::kvp(" \
                                      f"{package_name}_handler::{field_name}_fld_name, {field_name}_doc));\n"
                    output_content += f"\t\t\t}}\n"

                else:
                    output_content += self.generate_msg_repeated_nested_fields(field_type_message, field_name,
                                                                               package_name, message_name_snake_cased,
                                                                               field, field_name)
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.dependency_message_proto_msg_handler(file)
        self.get_field_names(self.root_message_list)
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)
        output_content = ""

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += self.headers_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {class_name_snake_cased}_handler {{\n\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root) or \
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root_time_series):
                for field in message.fields:
                    field_name: str = field.proto.name
                    field_name_snake_cased: str = convert_camel_case_to_specific_case(field_name)
                    # if CppDbHandlerPlugin.is_option_enabled(field, "FluxFldPk"):
                    message_name = message.proto.name
                    message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                    output_content += self.generate_prepare_doc(message, message_name_snake_cased, package_name,
                                                                message_name)
                    output_content += "\t}\n\n"
                    output_content += self.generate_prepare_docs(message, message_name_snake_cased, package_name,
                                                                 message_name)
                    output_content += f"\t\t\tr_{message_name_snake_cased}_document_list.emplace_back(std::move(" \
                                      f"r_{message_name_snake_cased}_document));\n"
                    output_content += "\t\t}\n\t}\n\n"

                    # output_content += "\t};\n\n"
                    break

        output_content += "}\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_mongo_db_codec.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
