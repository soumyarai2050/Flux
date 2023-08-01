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

    @staticmethod
    def headers_generate_handler(file_name: str, class_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <unordered_map>\n\n"
        output_content += f'#include "../../cpp_app/include/{class_name}_mongo_db_handler.h"\n'
        output_content += f'#include "../CppUtilGen/{class_name}_key_handler.h"\n'
        output_content += f'#include "../CppCodec/{class_name}_json_codec.h"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'
        return output_content

    @staticmethod
    def generate_class_handler(class_name: str, message_name: str, package_name: str, message_name_snake_cased: str,
                               file_name: str):
        output_content: str = ""
        output_content += f"\tclass {class_name}MongoDB{message_name}Codec "
        output_content += "{\n\n\tpublic:\n\t\t"
        output_content += (f'explicit {class_name}MongoDB{message_name}Codec(std::shared_ptr<{package_name}_handler::'
                           f'{class_name}_MongoDBHandler> mongo_db_, quill::Logger* logger) : mongo_db(mongo_db_), '
                           f'logger_(logger)')
        output_content += " {\n"
        output_content += (f'\t\t\t{message_name_snake_cased}_collection = mongo_db->{file_name}_db[{package_name}'
                           f'_handler::{message_name_snake_cased}_msg_name];\n')
        output_content += "\t\t}\n\n"
        return output_content

    @staticmethod
    def generate_insert_handler(class_name: str, message_name: str, package_name: str,
                                        message_name_snake_cased: str, file_name: str):
        output_content: str = ""

        output_content += f"\t\t/**\n\t\t * Insert or update the {message_name_snake_cased} data\n\t\t*/\n"
        output_content += f"\t\tbool insert_or_update_{message_name_snake_cased}(const {package_name}::" \
                          f"{message_name} &{message_name_snake_cased}_obj) "
        output_content += "{\n\t\t\t"
        output_content += (f'if (!{message_name_snake_cased}_obj.IsInitialized()) {{\n\t\t\t\tLOG_ERROR(logger_, '
                           f'"Reuired fields is not initialized in TopOfBook obj: {{}}", {message_name_snake_cased}_obj.'
                           f'DebugString());\n\t\t\t}} // else not required: code continues here for'
                           f' cases where the {message_name_snake_cased}_obj is initialized and has all the required'
                           f' fields\n\t\t\t')
        output_content += f"std::string {message_name_snake_cased}_key;\n"
        output_content += (f"\t\t\t{class_name}KeyHandler::get_{message_name_snake_cased}_key("
                           f"{message_name_snake_cased}_obj, {message_name_snake_cased}_key);\n")
        output_content += (f"\t\t\tbool status = insert_or_update_{message_name_snake_cased}("
                           f"{message_name_snake_cased}_obj, {message_name_snake_cased}_key);\n")
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        output_content += (f"\t\tbool insert_or_update_{message_name_snake_cased}(const {package_name}::" \
                          f"{message_name} &{message_name_snake_cased}_obj, std::string &{message_name_snake_cased}"
                           f"_key_in_n_out) {{\n")
        output_content += f"\t\t\tbool status = false;\n\t\t\t"
        output_content += f"bsoncxx::builder::basic::document {message_name_snake_cased}_document"
        output_content += "{};\n\t\t\t"

        output_content += f'\n\t\t\tauto found = {message_name_snake_cased}_key_to_db_id.find' \
                          f'({message_name_snake_cased}_key_in_n_out);\n\t\t\t'
        output_content += f'if (found == {message_name_snake_cased}_key_to_db_id.end()) '
        output_content += "{\n\t\t\t\t// Key does not exist, so it's a new object. Insert it into the database"
        output_content += f"\n\t\t\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_document, IsUpdateOrPatch::DB_FALSE);\n"
        output_content += f'\t\t\t\tstatus = insert_{message_name_snake_cased}({message_name_snake_cased}_document, ' \
                          f'{message_name_snake_cased}_key_in_n_out);\n\t\t\t'
        output_content += '} else {\n\t\t\t\t// Key already exists, so update the existing object in the database'
        output_content += f"\n\t\t\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_obj, " \
                          f"{message_name_snake_cased}_document, IsUpdateOrPatch::DB_TRUE);\n"
        output_content += f"\t\t\t\tstatus = update_or_patch_{message_name_snake_cased}(found->second, " \
                          f"{message_name_snake_cased}_document);\n\t\t\t"
        output_content += "}\n\t\t}\n\n"
        return output_content

    @staticmethod
    def generate_patch_handler(class_name: str, message_name: str, package_name: str,
                                        message_name_snake_cased: str, file_name: str):
        output_content: str = ""
        output_content += (f"\t\t/**\n\t\t * Patch the {message_name_snake_cased} data (update specific document)"
                           f"\n\t\t*/\n")
        output_content += f"\t\tbool patch_{message_name_snake_cased}(const {package_name}::{message_name} " \
                          f"&{message_name_snake_cased}_obj)"
        output_content += "{\n\t\t\t"
        output_content += "// Check if the object is initialized and has all the required fields\n\t\t\t"
        output_content += (f'if (!{message_name_snake_cased}_obj.IsInitialized()) {{\n\t\t\t\tLOG_ERROR(logger_, '
                           f'"Required fields is not initialized in TopOfBook obj: {{}}", {message_name_snake_cased}_obj.'
                           f'DebugString());\n\t\t\t\treturn false;\n\t\t\t}} // else not required: code continues here for'
                           f' cases where the {message_name_snake_cased}_obj is initialized and has all the required'
                           f' fields\n\t\t\t')
        output_content += f"std::string {message_name_snake_cased}_key;\n"
        output_content += (f"\t\t\t{class_name}KeyHandler::get_{message_name_snake_cased}_key("
                           f"{message_name_snake_cased}_obj, {message_name_snake_cased}_key);\n")
        output_content += (f"\t\t\tbool status = patch_{message_name_snake_cased}({message_name_snake_cased}_obj, "
                           f"{message_name_snake_cased}_key);\n")
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        output_content += f"\t\tbool patch_{message_name_snake_cased}(const {package_name}::{message_name} " \
                          f"&{message_name_snake_cased}_obj, std::string {message_name_snake_cased}_key_in_n_out)"
        output_content += "{\n\t\t\t"
        output_content += "bool status = false;\n"
        output_content += f"\t\t\tbsoncxx::builder::basic::document {message_name_snake_cased}_document{{}};\n"
        output_content += f"\t\t\tif (!{message_name_snake_cased}_key_in_n_out.empty()) {{\n"
        output_content += (f"\t\t\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_obj, "
                           f"{message_name_snake_cased}_document, IsUpdateOrPatch::DB_TRUE);\n")
        output_content += (f"\t\t\t\tstatus = update_or_patch_{message_name_snake_cased}({message_name_snake_cased}"
                           f"_key_to_db_id.at({message_name_snake_cased}_key_in_n_out), "
                           f"{message_name_snake_cased}_document);\n")
        output_content += f"\t\t\t}} else {{\n"
        output_content += (f"\t\t\t\t{class_name}KeyHandler::get_{message_name_snake_cased}_key("
                           f"{message_name_snake_cased}_obj, {message_name_snake_cased}_key_in_n_out);\n")
        output_content += (f"\t\t\t\tauto found = {message_name_snake_cased}_key_to_db_id.find("
                           f"{message_name_snake_cased}_key_in_n_out);\n")
        output_content += f"\t\t\t\tif (found != {message_name_snake_cased}_key_to_db_id.end()) {{\n"
        output_content += (f"\t\t\t\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_obj,"
                           f" {message_name_snake_cased}_document, IsUpdateOrPatch::DB_TRUE);\n")
        output_content += (f"\t\t\t\t\tstatus = update_or_patch_{message_name_snake_cased}(found->second, "
                           f"{message_name_snake_cased}_document);\n")
        output_content += "\t\t\t\t} else {\n"
        output_content += (f'\t\t\t\t\tLOG_ERROR(logger_, "patch_{message_name_snake_cased} failed - '
                           f'{message_name_snake_cased} key not found in {message_name_snake_cased}_key_to_db_id map;;; '
                           f'{message_name_snake_cased}: {{}} map: {{}}", {message_name_snake_cased}_obj.DebugString'
                           f'(), {message_name}KeyToDbIdAsString());\n')
        output_content += "\t\t\t\t}\n\t\t\t}\n\t\t\treturn status;\n\t\t}\n\n"

        output_content += (f"\t\t/**\n\t\t * Patch the {message_name_snake_cased} data (update specific document)"
                           f" and retrieve the updated object\n\t\t*/\n")
        output_content += (f"\t\tbool patch_{message_name_snake_cased}(const {package_name}::{message_name} "
                           f"&{message_name_snake_cased}_obj, {package_name}::{message_name} "
                           f"&{message_name_snake_cased}_obj_out)")
        output_content += "{\n\t\t\t"
        output_content += "// Check if the object is initialized and has all the required fields\n\t\t\t"
        output_content += (f'if (!{message_name_snake_cased}_obj.IsInitialized()) {{\n\t\t\t\tLOG_ERROR(logger_, '
                           f'"Required fields is not initialized in TopOfBook obj: {{}}", {message_name_snake_cased}_obj.'
                           f'DebugString());\n\t\t\t\treturn false;\n\t\t\t}} // else not required: code continues here for'
                           f' cases where the {message_name_snake_cased}_obj is initialized and has all the required'
                           f' fields\n\t\t\t')
        output_content += f"std::string {message_name_snake_cased}_key;\n"
        output_content += (f"\t\t\t{class_name}KeyHandler::get_{message_name_snake_cased}_key("
                           f"{message_name_snake_cased}_obj, {message_name_snake_cased}_key);\n")
        output_content += (f"\t\t\tbool status = patch_{message_name_snake_cased}({message_name_snake_cased}_obj, "
                           f"{message_name_snake_cased}_obj_out, {message_name_snake_cased}_key);\n")
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        output_content += (f"\t\tbool patch_{message_name_snake_cased}(const {package_name}::{message_name} "
                           f"&{message_name_snake_cased}_obj, {package_name}::{message_name} "
                           f"&{message_name_snake_cased}_obj_out, std::string &{message_name_snake_cased}"
                           f"_key_in_n_out)")
        output_content += " {\n"
        output_content += (f"\t\t\tbool status = patch_{message_name_snake_cased}({message_name_snake_cased}"
                           f"_obj, {message_name_snake_cased}_key_in_n_out);\n")
        output_content += "\t\t\tif (status) {\n"
        output_content += (f"\t\t\t\tauto {message_name_snake_cased}_id = {message_name_snake_cased}_key_to_db_id"
                           f".at({message_name_snake_cased}_key_in_n_out);\n")
        output_content += (f"\t\t\t\tstatus = get_data_by_id_from_{message_name_snake_cased}_collection("
                           f"{message_name_snake_cased}_obj_out, {message_name_snake_cased}_id);\n")
        output_content += "\t\t\t}\n"
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_public_members_handler(class_name: str, message_name: str, package_name: str,
                                        message_name_snake_cased: str, file_name: str):
        output_content: str = ""

        output_content += f"\t\tbool update_or_patch_{message_name_snake_cased}(const std::string " \
                          f"&{message_name_snake_cased}_id, const bsoncxx::builder::basic::document " \
                          f"&{message_name_snake_cased}_document)"
        output_content += "{\n\t\t\t"
        output_content += f'auto update_filter = {package_name}_handler::make_document({package_name}' \
                          f'_handler::kvp("_id", {message_name_snake_cased}_id));\n\t\t\t'
        output_content += f'auto update_document = {package_name}_handler::make_document({package_name}' \
                          f'_handler::kvp("$set", {message_name_snake_cased}_document.view()));\n\t\t\t'
        output_content += f'auto result = {message_name_snake_cased}_collection.update_one(update_filter.view(), ' \
                          f'update_document.view());\n\t\t'
        output_content += "\tif (result->modified_count() > 0) {\n"
        output_content += "\t\t\t\treturn true;\n\t\t\t}"
        output_content += " else {\n"
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t}\n\n"

        output_content += f"\t\tbool insert_{message_name_snake_cased} (const bsoncxx::builder::basic::document " \
                          f"&{message_name_snake_cased}_document, const std::string &{message_name_snake_cased}_key) "
        output_content += "{\n\t\t\t"
        output_content += f"auto {message_name_snake_cased}_insert_result = {message_name_snake_cased}" \
                          f"_collection.insert_one({message_name_snake_cased}_document.view());\n\t\t\t"
        output_content += f"auto {message_name_snake_cased}_inserted_id = {message_name_snake_cased}" \
                          f"_insert_result->inserted_id().get_string().value.to_string();\n\n"

        output_content += f"\t\t\tif (!{message_name_snake_cased}_inserted_id.empty()) {{"
        output_content += f"\n\t\t\t\t{message_name_snake_cased}_key_to_db_id" \
                          f"[{message_name_snake_cased}_key] = {message_name_snake_cased}_inserted_id;" \
                          f"\n\t\t\t\treturn true;\n\t\t\t}} else {{\n"
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\n\t\t}"

        return output_content

    @staticmethod
    def generate_private_members_handler(class_name: str, package_name: str, message_name_snake_cased: str, file_name: str):
        output_content: str = ""
        output_content += f"\t\tstd::unordered_map <std::string, std::string> {message_name_snake_cased}_key_to_db_id;\n\n"
        output_content += "\tprotected:"
        output_content += f"\n\n\t\tstd::shared_ptr<{package_name}_handler::{class_name}_MongoDBHandler> mongo_db;\n"
        output_content += f"\t\tquill::Logger* logger_;"
        output_content += f"\t\tmongocxx::collection {message_name_snake_cased}_collection;\n\n"

        return output_content

    @staticmethod
    def generate_get_data_from_db(message_name: str, package_name: str, message_name_snake_cased: str, class_name: str):
        output_content: str = ""

        output_content += f"\n\t\tbool get_all_data_from_{message_name_snake_cased}_collection({package_name}::" \
                          f"{message_name}List &{message_name_snake_cased}_list_obj) {{\n"
        output_content += "\t\t\tbool status = false;\n"
        output_content += f'\t\t\tstd::string all_{message_name_snake_cased}_data_from_db_json_string;\n'
        output_content += f'\t\t\tauto cursor = {message_name_snake_cased}_collection.find({{}});\n\n'
        output_content += f'\t\t\tfor (const auto& {message_name_snake_cased}_doc : cursor) {{\n'
        output_content += f'\t\t\t\tstd::string {message_name_snake_cased}_view = bsoncxx::to_json' \
                          f'({message_name_snake_cased}_doc);\n'
        output_content += f'\t\t\t\tsize_t pos = {message_name_snake_cased}_view.find("_id");\n'
        output_content += f'\t\t\t\tif (pos != std::string::npos)\n'
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_view.erase(pos, 1);\n'
        output_content += f'\t\t\t\tall_{message_name_snake_cased}_data_from_db_json_string += ' \
                          f'{message_name_snake_cased}_view;\n'
        output_content += f'\t\t\t\tall_{message_name_snake_cased}_data_from_db_json_string += ",";'
        output_content += f'\n\t\t\t}}\n'
        output_content += f"\t\t\tif (all_{message_name_snake_cased}_data_from_db_json_string.back() == ',') {{\n"
        output_content += f'\t\t\t\tall_{message_name_snake_cased}_data_from_db_json_string.pop_back();\n'
        output_content += f'\t\t\t}} // else not required: all_{message_name_snake_cased}_data_from_db_json_string is ' \
                          f'empty so need to perform any operation\n'
        output_content += f"\t\t\tif (!all_{message_name_snake_cased}_data_from_db_json_string.empty()) \n"
        output_content += f"\t\t\t\tstatus = {class_name}JSONCodec::decode_{message_name_snake_cased}_list" \
                          f"({message_name_snake_cased}_list_obj, all_{message_name_snake_cased}_data_from" \
                          f"_db_json_string);\n"

        output_content += f"\t\t\treturn status;\n"
        output_content += "\t\t}\n"

        output_content += f"\n\t\tbool get_data_by_id_from_{message_name_snake_cased}_collection ({package_name}" \
                          f"::{message_name} &{message_name_snake_cased}obj, const std::string " \
                          f"&{message_name_snake_cased}_id) {{\n"
        output_content += "\t\t\tbool status = false;\n"

        output_content += f'\t\t\tauto cursor = {message_name_snake_cased}_collection.find' \
                          f'(bsoncxx::builder::stream::document{{}} << "_id" << {message_name_snake_cased}_id ' \
                          f'<< bsoncxx::builder::stream::finalize );\n'
        output_content += "\t\t\tif (cursor.begin() != cursor.end()) {\n"
        output_content += f'\t\t\t\tauto&& doc = *cursor.begin();\n'
        output_content += f'\t\t\t\tstd::string {message_name_snake_cased}_doc = bsoncxx::to_json(doc);\n'
        output_content += f'\t\t\t\tsize_t pos = {message_name_snake_cased}_doc.find("_id");\n'
        output_content += "\t\t\t\tif (pos != std::string::npos)\n"
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_doc.erase(pos, 1);\n'
        output_content += f'\t\t\t\tstatus = {class_name}JSONCodec::decode_{message_name_snake_cased}(' \
                          f'{message_name_snake_cased}obj, {message_name_snake_cased}_doc);\n'
        output_content += f"\t\t\t\treturn status;\n"
        output_content += "\t\t\t} else {\n"
        output_content += f"\t\t\t\treturn status;\n\t\t\t}}\n\t\t}}\n\n"

        return output_content

    @staticmethod
    def generate_delete_from_db_handler(message_name_snake_cased: str):
        output_content: str = ""
        output_content += f"\n\t\tbool delete_all_data_from_{message_name_snake_cased}_collection() {{\n"
        output_content += f"\t\t\tauto result = {message_name_snake_cased}_collection.delete_many({{}});\n"
        output_content += "\t\t\tif (result) {\n\t\t\t\treturn true;\n\t\t\t} "
        output_content += "else {\n\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += '\t\t}\n'

        output_content += f"\n\t\tbool delete_data_by_id_from_{message_name_snake_cased}_collection (const " \
                          f"std::string &{message_name_snake_cased}_id) {{\n"
        output_content += f'\t\t\tauto result = {message_name_snake_cased}_collection.delete_one(bsoncxx::builder::' \
                          f'stream::document{{}} << "_id" << {message_name_snake_cased}_id << ' \
                          f'bsoncxx::builder::stream::finalize);\n'
        output_content += "\t\t\tif (result) {\n"
        output_content += "\t\t\t\treturn true;\n\t\t\t} "
        output_content += "else {\n"
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t}\n\n"

        return output_content

    @staticmethod
    def generate_bulk_insert_and_update(message_name_snake_cased: str, message_name: str, package_name: str):
        output_content: str = ""

        output_content += f"\n\n\t\tbool bulk_insert_{message_name_snake_cased} (const {package_name}::" \
                          f"{message_name}List &{message_name_snake_cased}_list_obj, const std::vector <std::string>" \
                          f" &{message_name_snake_cased}_key_list) {{\n"

        output_content += f"\t\t\tstd::vector<bsoncxx::builder::basic::document> {message_name_snake_cased}_document_list;\n"

        output_content += f"\t\t\tprepare_{message_name_snake_cased}_list_doc({message_name_snake_cased}_list_obj, " \
                          f"{message_name_snake_cased}_document_list, IsUpdateOrPatch::DB_FALSE);\n"

        output_content += f"\t\t\tauto {message_name_snake_cased}_insert_results = {message_name_snake_cased}_" \
                          f"collection.insert_many({message_name_snake_cased}_document_list);\n"

        output_content += f"\t\t\tfor (int i = 0; i < {message_name_snake_cased}_document_list.size(); ++i) {{\n"
        output_content += f'\t\t\t\t{message_name_snake_cased}_key_to_db_id[{message_name_snake_cased}_key_list[i]] ' \
                          f'= {message_name_snake_cased}_insert_results->inserted_ids().at(i).get_value().' \
                          f'get_string().value.to_string();\n'
        output_content += f'\t\t\t}}\n\n'

        output_content += (f"\t\t\tif ({message_name_snake_cased}_insert_results->inserted_count() == "
                           f"{message_name_snake_cased}_document_list.size()) {{\n")
        output_content += "\t\t\t\treturn true;\n\t\t\t} else {\n"
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t}\n\n"

        output_content += (f"\t\t/**\n\t\t * Bulk patch the {message_name_snake_cased} data (update specific document)"
                           f"\n\t\t*/\n")
        output_content += f"\t\tbool bulk_patch_{message_name_snake_cased}(const {package_name}::{message_name}List " \
                          f"&{message_name_snake_cased}_list_obj){{\n"
        output_content += f'\t\t\tstd::vector< bsoncxx::builder::basic::document > {message_name_snake_cased}' \
                          f'_document_list;\n'
        output_content += f"\t\t\tstd::vector< std::string > {message_name_snake_cased}_key_list;\n"
        output_content += f'\t\t\tMarketDataKeyHandler::get_{message_name_snake_cased}_key_list(' \
                          f'{message_name_snake_cased}_list_obj, {message_name_snake_cased}_key_list);\n'
        output_content += f'\t\t\tstd::vector<std::string> {message_name_snake_cased}_ids;\n\n'
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_obj.{message_name_snake_cased}' \
                          f'_size(); ++i) {{\n'
        output_content += f'\t\t\t\tif (!{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).' \
                          f'IsInitialized()) {{\n'
        output_content += (f'\t\t\t\t\tcontinue;\n\t\t\t\t}} // else not required: code continues here for cases where '
                           f'the {message_name_snake_cased}_obj is initialized and has all the required fields\n\n')
        output_content += f'\t\t\t\tauto found = {message_name_snake_cased}_key_to_db_id.find(' \
                          f'{message_name_snake_cased}_key_list[i]);\n'
        output_content += f'\t\t\t\tif (found == {message_name_snake_cased}_key_to_db_id.end()) {{\n'
        output_content += (f'\t\t\t\t\tconst std::string error = "bulk_patch_{message_name_snake_cased} failed - '
                           f'{message_name_snake_cased} key not found in {message_name_snake_cased}_key_to_db_id '
                           f'map;;; {message_name_snake_cased}_list_obj: " + {message_name_snake_cased}_list_obj'
                           f'.DebugString() + "map: " + {message_name}KeyToDbIdAsString();\n')
        output_content += f'\t\t\t\t\tthrow std::runtime_error(error);\n'
        output_content += f'\t\t\t\t}} else {{\n'
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_ids.push_back({message_name_snake_cased}_key_to_db_id' \
                          f'.at({message_name_snake_cased}_key_list[i]));\n'
        output_content += "\t\t\t\t}\n"
        output_content += "\t\t\t}\n"
        output_content += f'\t\t\tprepare_{message_name_snake_cased}_list_doc({message_name_snake_cased}_list_obj,' \
                          f' {message_name_snake_cased}_document_list, IsUpdateOrPatch::DB_TRUE);\n'
        output_content += f"\t\t\tbool status = bulk_update_or_patch_{message_name_snake_cased}_collection(" \
                          f"{message_name_snake_cased}_ids, {message_name_snake_cased}_document_list);\n"
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        output_content += (f"\t\t/**\n\t\t * Bulk patch the {message_name_snake_cased} data (update specific document)"
                           f" and retrieve the updated object\n\t\t*/\n")
        output_content += f"\t\tbool bulk_patch_{message_name_snake_cased}(const {package_name}::{message_name}List " \
                          f"&{message_name_snake_cased}_list_obj, {package_name}::{message_name}List " \
                          f"&{message_name_snake_cased}_list_out){{\n"
        output_content += f'\t\t\tstd::vector< bsoncxx::builder::basic::document > {message_name_snake_cased}' \
                          f'_document_list;\n'
        output_content += f"\t\t\tstd::vector< std::string > {message_name_snake_cased}_key_list;\n"
        output_content += f'\t\t\tMarketDataKeyHandler::get_{message_name_snake_cased}_key_list(' \
                          f'{message_name_snake_cased}_list_obj, {message_name_snake_cased}_key_list);\n'
        output_content += f'\t\t\tstd::vector<std::string> {message_name_snake_cased}_ids;\n\n'
        output_content += f'\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_obj.{message_name_snake_cased}' \
                          f'_size(); ++i) {{\n'
        output_content += f'\t\t\t\tif (!{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).' \
                          f'IsInitialized()) \n'
        output_content += f'\t\t\t\t\tcontinue;\n\n'
        output_content += f'\t\t\t\tauto found = {message_name_snake_cased}_key_to_db_id.find(' \
                          f'{message_name_snake_cased}_key_list[i]);\n'
        output_content += f'\t\t\t\tif (found == {message_name_snake_cased}_key_to_db_id.end()) {{\n'
        output_content += (f'\t\t\t\t\tconst std::string error = "bulk_patch_{message_name_snake_cased} failed -'
                           f' {message_name_snake_cased} key not found in {message_name_snake_cased}_key_to_db_id '
                           f'map;;; {message_name_snake_cased}_list_obj: " + {message_name_snake_cased}_list_obj.'
                           f'DebugString() + "map: " + {message_name}KeyToDbIdAsString();\n')
        output_content += f'\t\t\t\t\tthrow std::runtime_error(error);\n'
        output_content += f'\t\t\t\t}} else {{\n'
        output_content += f'\t\t\t\t\t{message_name_snake_cased}_ids.push_back({message_name_snake_cased}_key_to_db_id' \
                          f'.at({message_name_snake_cased}_key_list[i]));\n'
        output_content += "\t\t\t\t}"
        output_content += "\n\t\t\t}\n"
        output_content += f'\t\t\tprepare_{message_name_snake_cased}_list_doc({message_name_snake_cased}_list_obj,' \
                          f' {message_name_snake_cased}_document_list, IsUpdateOrPatch::DB_TRUE);\n'
        output_content += f"\t\t\tbool status = bulk_update_or_patch_{message_name_snake_cased}_collection(" \
                          f"{message_name_snake_cased}_ids, {message_name_snake_cased}_document_list);\n"
        output_content += f"\t\t\tif (status) {{\n"
        output_content += (f"\t\t\t\tget_all_data_from_{message_name_snake_cased}_collection(" \
                          f"{message_name_snake_cased}_list_out);\n\t\t\t}} // else not required: Retrieve updated data"
                          f" if the update or patch was successful\n")
        output_content += "\t\t\treturn status;\n"
        output_content += "\t\t}\n\n"

        output_content += f"\t\tbool bulk_update_or_patch_{message_name_snake_cased}_collection " \
                          f"(const std::vector<std::string> &{message_name_snake_cased}_ids," \
                          f" const std::vector<bsoncxx::builder::basic::document> &{message_name_snake_cased}" \
                          f"_document_list) {{\n"
        output_content += f"\t\t\tauto bulk_write = {message_name_snake_cased}_collection.create_bulk_write();\n"
        output_content += f"\t\t\tfor (int i = 0; i < {message_name_snake_cased}_ids.size(); ++i) {{\n"
        output_content += f'\t\t\t\tauto update_filter = {package_name}_handler::make_document({package_name}' \
                          f'_handler::kvp("_id", {message_name_snake_cased}_ids[i]));\n'
        output_content += f'\t\t\t\tauto update_document = {package_name}_handler::make_document({package_name}' \
                          f'_handler::kvp("$set", {message_name_snake_cased}_document_list[i]));\n'
        output_content += '\t\t\t\tmongocxx::model::update_one updateOne(update_filter.view(), ' \
                          'update_document.view());\n'
        output_content += "\t\t\t\tupdateOne.upsert(false);\n"
        output_content += "\t\t\t\tbulk_write.append(updateOne);\n"
        output_content += "\t\t\t}\n"
        output_content += "\t\t\tauto result = bulk_write.execute();\n\n"

        output_content += "\t\t\tif (result) {\n"
        output_content += "\t\t\t\tauto modified_count = result->modified_count();\n"
        output_content += "\t\t\t\tauto matched_count = result->matched_count();\n"
        output_content += "\t\t\t\treturn (modified_count == matched_count); // Return true only if " \
                          "all updates were successful\n"
        output_content += "\t\t\t} else {\n"
        output_content += '\t\t\t\tstd::cerr << "Bulk update failed" << std::endl;\n'
        output_content += "\t\t\t\treturn false;\n\t\t\t}\n"
        output_content += "\t\t}\n\n"

        return output_content

    def generate_repeated_nested_fields(self, message: protogen.Message, field_name, package_name,
                                        message_name_snake_cased, field, initial_parent, num_of_tabs: int | None = None):
        if num_of_tabs is None:
            num_of_tabs = 6

        output = ""
        parent_field = field.proto.name

        if parent_field != field_name:
            output += f'\t\t\t\tif ({message_name_snake_cased}_obj.{parent_field}().{field_name}_size() > 0) {{\n'
            output += f'\t\t\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n'
            output += f'\t\t\t\t\tfor (const auto& {field_name}_doc : {message_name_snake_cased}_obj.{parent_field}().' \
                      f'{field_name}()) {{\n'
            output += f'\t\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\tif ({message_name_snake_cased}_obj.{parent_field}_size() > 0) {{\n'
                output += f'\t\t\t\tbsoncxx::builder::basic::array {parent_field}_list;\n'
                output += f'\t\t\t\tfor (const auto& {field_name}_doc : {message_name_snake_cased}_obj.{parent_field}()) {{\n'
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
                            output += f'\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                            output += f'\t\t\t\t\t\t\t{field_name}_document.append({package_name}_handler::kvp("' \
                                      f'_id", {field_name}_doc_doc.{message_field_name}()));\n'
                        else:
                            output += f'\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                            output += f'\t\t\t\t\t\t\t{field_name}_document.append({package_name}_handler::kvp(' \
                                      f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc_doc' \
                                      f'.{message_field_name}()));\n'
                    else:
                        if initial_parent == parent_field and parent_field == field_name:
                            if message_field_name == "id":
                                output += f'\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp("' \
                                          f'_id", {parent_field}_doc.{message_field_name}()));\n'
                            else:
                                output += f'\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp(' \
                                          f'{package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                          f'{message_field_name}()));\n'
                        else:
                            if message_field_name == "id":
                                output += "\t" * local_num_of_tabs + f'if ({parent_field}_doc.has_' \
                                                                     f'{message_field_name}())\n'
                                local_num_of_tabs += 1
                                output += "\t" * local_num_of_tabs + f'{parent_field}_document.append({package_name}' \
                                                                     f'_handler::kvp("_id", {parent_field}' \
                                                                     f'_doc.{message_field_name}()));\n'
                            else:
                                output += "\t"*local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                local_num_of_tabs += 1
                                output += "\t"*local_num_of_tabs + f'{parent_field}_document.append({package_name}' \
                                                                   f'_handler::kvp({package_name}_handler::' \
                                                                   f'{message_field_name}_fld_name, ' \
                                                                   f'{parent_field}_doc.{message_field_name}()));\n'
                else:
                    output += f'\t\t\t\t\tif ({parent_field}_doc.{message_field_name}_size() > 0) {{\n'
                    output += f'\t\t\t\t\t\tbsoncxx::builder::basic::array {message_field_name}_array;\n'
                    output += f'\t\t\t\t\t\tfor (const auto& {message_field_name}_doc : {parent_field}_doc.' \
                              f'{message_field_name}()){{\n'
                    output += f'\t\t\t\t\t\t\t{message_field_name}_array.append({message_field_name}_doc);\n'
                    output += "\t\t\t\t\t\t}\n"
                    output += f'\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp' \
                              f'({package_name}_handler::{message_field_name}_fld_name, {message_field_name}_array));\n'

                    output += "\t\t\t\t\t}\n"

            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_repeated_nested_fields(message_field.message, message_field_name,
                                                               package_name,
                                                               message_name_snake_cased, message_field, field_name,
                                                               num_of_tabs)

        if parent_field != field_name:
            output += f'\t\t\t\t\t\t{field_name}_list.append({field_name}_document);\n'
            output += "\t\t\t\t\t}\n"
            output += f"\t\t\t\t\t{parent_field}.append({package_name}_handler::kvp({package_name}_handler::{field_name}_fld_name," \
                      f" {field_name}_list));\n"
            output += "\n\t\t\t\t}\n"
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\t\t\t{parent_field}_list.append({parent_field}_document);\n'
                output += f'\t\t\t\t}}\n\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp' \
                          f'({package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                output += "\t\t\t}\n"
            else:
                output += "\t"*num_of_tabs + f'{parent_field}_list.append({parent_field}_document);\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"
                output += "\t"*num_of_tabs + f'{initial_parent}_document.append({package_name}_handler::kvp(' \
                                             f'{package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"

        return output

    def generate_msg_repeated_nested_fields(self, message: protogen.Message, field_name, package_name,
                                            message_name_snake_cased, field, initial_parent,
                                            num_of_tabs: int | None = None):
        if num_of_tabs is None:
            num_of_tabs = 6

        output = ""
        parent_field = field.proto.name

        if parent_field != field_name:
            output += f'\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{parent_field}' \
                      f'().{field_name}_size() > 0) {{\n'
            output += f'\t\t\t\t\t\tbsoncxx::builder::basic::array {field_name}_list;\n'
            output += f'\t\t\t\t\t\tfor (const auto& {field_name}_doc : {message_name_snake_cased}_list_obj.' \
                      f'{message_name_snake_cased}(i).{parent_field}().{field_name}()) {{\n'
            output += f'\t\t\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{parent_field}' \
                          f'_size() > 0) {{\n'
                output += f'\t\t\t\t\tbsoncxx::builder::basic::array {parent_field}_list;\n'
                output += f'\t\t\t\t\tfor (const auto& {field_name}_doc : {message_name_snake_cased}_list_obj.' \
                          f'{message_name_snake_cased}(i).{parent_field}()) {{\n'
                output += f'\t\t\t\t\t\tbsoncxx::builder::basic::document {field_name}_document;\n'
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
                            output += f'\t\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                            output += f'\t\t\t\t\t\t\t\t{field_name}_document.append({package_name}_handler::kvp("' \
                                      f'_id", {field_name}_doc_doc.{message_field_name}()));\n'
                        else:
                            output += f'\t\t\t\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n'
                            output += f'\t\t\t\t\t\t\t{field_name}_document.append({package_name}_handler::kvp(' \
                                      f'{package_name}_handler::{message_field_name}_fld_name, {field_name}_doc_doc.' \
                                      f'{message_field_name}()));\n'
                    else:
                        if initial_parent == parent_field and parent_field == field_name:
                            if message_field_name == "id":
                                output += f'\t\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp("' \
                                          f'_id", {parent_field}_doc.{message_field_name}()));\n'
                            else:
                                output += f'\t\t\t\t\t\tif ({parent_field}_doc.has_{message_field_name}())\n'
                                output += f'\t\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp' \
                                          f'({package_name}_handler::{message_field_name}_fld_name, {parent_field}_doc.' \
                                          f'{message_field_name}()));\n'
                        else:
                            if message_field_name == "_id":
                                output += "\t"*local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                local_num_of_tabs += 1
                                output += "\t"*local_num_of_tabs + f'{parent_field}_document.append({package_name}' \
                                                                   f'_handler::kvp("_id", {parent_field}_doc.' \
                                                                   f'{message_field_name}()));\n'
                            else:
                                output += "\t" * local_num_of_tabs + f'if ({parent_field}_doc.has_{message_field_name}())\n'
                                local_num_of_tabs += 1
                                output += "\t" * local_num_of_tabs + f'{parent_field}_document.append({package_name}' \
                                                                     f'_handler::kvp({package_name}_handler::' \
                                                                     f'{message_field_name}_fld_name, {parent_field}_doc' \
                                                                     f'.{message_field_name}()));\n'
                else:
                    output += f'\t\t\t\t\t\tif ({parent_field}_doc.{message_field_name}_size() > 0) {{\n'
                    output += f'\t\t\t\t\t\t\tbsoncxx::builder::basic::array {message_field_name}_array;\n'
                    output += f'\t\t\t\t\t\t\tfor (const auto& {message_field_name}_doc : {parent_field}_doc.' \
                              f'{message_field_name}()){{\n'
                    output += f'\t\t\t\t\t\t\t\t{message_field_name}_array.append({message_field_name}_doc);\n'
                    output += "\t\t\t\t\t\t\t}\n"
                    output += f'\t\t\t\t\t\t\t{parent_field}_document.append({package_name}_handler::kvp' \
                              f'({package_name}_handler::{message_field_name}_fld_name, {message_field_name}_array));\n'

                    output += "\t\t\t\t\t\t}\n"

            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_msg_repeated_nested_fields(message_field.message, message_field_name,
                                                                   package_name, message_name_snake_cased,
                                                                   message_field, field_name, num_of_tabs)

        if parent_field != field_name:
            output += f'\t\t\t\t\t\t\t{field_name}_list.append({field_name}_document);\n'
            output += "\t\t\t\t\t\t}\n"
            output += f"\t\t\t\t\t\t{parent_field}.append({package_name}_handler::kvp({package_name}_handler::" \
                      f"{field_name}_fld_name, {field_name}_doc_list));\n"
            output += "\n\t\t\t\t}\n"
        else:
            if initial_parent == parent_field and parent_field == field_name:
                output += f'\t\t\t\t\t\t{parent_field}_list.append({parent_field}_document);\n'
                output += f'\t\t\t\t\t}}\n\t\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp' \
                          f'({package_name}_handler::{parent_field}_fld_name, {parent_field}_list));\n'
                output += "\t\t\t\t}\n"
            else:
                output += "\t"*num_of_tabs + f'{parent_field}_list.append({parent_field}_document);\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"
                output += "\t"*num_of_tabs + f'{initial_parent}_document.append({package_name}_handler::kvp("{parent_field}",' \
                          f' {parent_field}_list));\n'
                num_of_tabs -= 1
                output += "\t"*num_of_tabs + "}\n"

        return output

    def generate_nested_fields(self, field_type_message: protogen.Message, field_name,
                               message_name_snake_cased: str, package_name: str, field: protogen.Field, parent_feild: str):
        output = ""
        initial_parent_field: str = field.proto.name
        # field_name: str = field.proto.name
        # print(f".............{field.parent.proto.name}...............")
        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            if message_field.message is None and field_type != "repeated":
                if field_name != initial_parent_field:
                    if field_name != parent_feild and initial_parent_field != parent_feild:
                        output += f"\t\t\t\t\tif ({message_name_snake_cased}_obj.{initial_parent_field}()." \
                                  f"{parent_feild}().{field_name}().has_{message_field_name}())\n"
                        output += f'\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}' \
                                  f'_handler::{message_field_name}_fld_name, {message_name_snake_cased}_obj.' \
                                  f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                    else:
                        output += f"\t\t\t\t\tif ({message_name_snake_cased}_obj.{initial_parent_field}()." \
                                  f"{field_name}().has_{message_field_name}())\n"
                        output += f'\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}' \
                                  f'_handler::{message_field_name}_fld_name, {message_name_snake_cased}_obj.' \
                                  f'{initial_parent_field}().{field_name}().{message_field_name}()));\n'
                else:
                    output += f"\t\t\t\tif ({message_name_snake_cased}_obj.{field_name}().has_{message_field_name}())\n"
                    output += f'\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}' \
                              f'_handler::{message_field_name}_fld_name, {message_name_snake_cased}_obj.{field_name}' \
                              f'().{message_field_name}()));\n'
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field:
                    output += f"\t\t\t\tbsoncxx::builder::basic::document {message_field_name};\n"
                    output += f"\t\t\t\tif ({message_name_snake_cased}_obj.{initial_parent_field}()." \
                              f"{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                else:
                    output += f"\t\t\t\tbsoncxx::builder::basic::document {message_field_name};\n"
                    output += f"\t\t\t\tif ({message_name_snake_cased}_obj.{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                output += f'\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}_handler::' \
                          f'{message_field_name}_fld_name, {message_field_name}));\n'
                output += f"\t\t\t\t}}\n"
            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_repeated_nested_fields(message_field.message, message_field_name, package_name,
                                                               message_name_snake_cased, field, field_name, 5)
        return output

    def generate_msg_nested_fields(self, field_type_message: protogen.Message, field_name,
                                   message_name_snake_cased: str, package_name: str, field: protogen.Field,
                                   parent_feild: str):
        output = ""
        initial_parent_field: str = field.proto.name
        # field_name: str = field.proto.name
        # print(f".............{field.parent.proto.name}...............")
        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            if message_field.message is None and field_type != "repeated":
                if field_name != initial_parent_field:
                    if field_name != parent_feild and initial_parent_field != parent_feild:
                        output += f"\t\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                  f"{initial_parent_field}().{parent_feild}().{field_name}()." \
                                  f"has_{message_field_name}())\n"
                        output += f'\t\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}' \
                                  f'_handler::{message_field_name}_fld_name, {message_name_snake_cased}_list_obj.' \
                                  f'{message_name_snake_cased}(i).' \
                                  f'{initial_parent_field}().{parent_feild}().{field_name}().{message_field_name}()));\n'
                    else:
                        output += f"\t\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                  f"{initial_parent_field}().{field_name}().has_{message_field_name}())\n"
                        output += f'\t\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}' \
                                  f'_handler::{message_field_name}_fld_name, {message_name_snake_cased}_list_obj.' \
                                  f'{message_name_snake_cased}(i).{initial_parent_field}().{field_name}().' \
                                  f'{message_field_name}()));\n'
                else:
                    output += f"\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                              f"{field_name}().has_{message_field_name}())\n"
                    output += f'\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}_handler' \
                              f'::{message_field_name}_fld_name, {message_name_snake_cased}_list_obj.{message_name_snake_cased}' \
                              f'(i).{field_name}().{message_field_name}()));\n'
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field:
                    output += f"\t\t\t\t\tbsoncxx::builder::basic::document {message_field_name};\n"
                    output += f"\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                              f"{initial_parent_field}().{field_name}().has_{message_field_name}()) "
                    output += f"{{\n"
                    output += self.generate_msg_nested_fields(message_field.message, message_field_name,
                                                              message_name_snake_cased, package_name, field, field_name)
                else:
                    output += f"\t\t\t\t\tbsoncxx::builder::basic::document {message_field_name};\n"
                    output += f"\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i).{field_name}()" \
                              f".has_{message_field_name}()) "
                    output += f"{{\n"
                    output += self.generate_msg_nested_fields(message_field.message, message_field_name,
                                                              message_name_snake_cased, package_name, field, field_name)
                output += f"\t\t\t\t\t\t{field_name}_doc.append({package_name}_handler::kvp({package_name}_handler::" \
                          f"{message_field_name}_fld_name, {message_field_name}));\n"
                output += f"\t\t\t\t\t}}\n"
            elif message_field.message is not None and field_type == "repeated":
                output += self.generate_msg_repeated_nested_fields(message_field.message, message_field_name, package_name,
                                                                   message_name_snake_cased, field, field_name)
        return output

    def generate_prepare_doc(self, message: protogen.Message, message_name_snake_cased: str,
                             package_name: str, message_name: str):
        output_content: str = ""
        # output_content += f"\tprotected:\n\n"
        output_content += f"\t\tvoid prepare_{message_name_snake_cased}_doc(const {package_name}::{message_name} " \
                          f"&{message_name_snake_cased}_obj, bsoncxx::builder::basic::document " \
                          f"&{message_name_snake_cased}_document, const IsUpdateOrPatch is_update_or_patch) const"
        output_content += " {\n"

        for field in message.fields:
            field_name = field.proto.name
            field_kind = field.kind.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message

            if field_type_message is None:
                if field_type != "repeated":
                    if field_name != "id":
                        if field_type == "required":
                            output_content += (f"\t\t\t{message_name_snake_cased}_document.append({package_name}"
                                               f"_handler::kvp({package_name}_handler::{field_name}_fld_name, "
                                               f"{message_name_snake_cased}_obj.{field_name}()));\n")
                        else:
                            output_content += f"\t\t\tif ({message_name_snake_cased}_obj.has_{field_name}())\n"
                            output_content += f"\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::" \
                                              f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                              f"{message_name_snake_cased}_obj.{field_name}()));\n"
                    else:
                        if field_type == "required":
                            output_content += "\t\t\tif (IsUpdateOrPatch::DB_FALSE == is_update_or_patch) {\n"
                            output_content += f'\t\t\t\t{message_name_snake_cased}_document.append(' \
                                              f'{package_name}_handler::kvp("_id", {message_name_snake_cased}' \
                                              f'_obj.{field_name}()));\n'
                        else:
                            output_content += "\t\t\tif (IsUpdateOrPatch::DB_FALSE == update_or_patch) {\n"
                            output_content += f"\t\t\t\tif ({message_name_snake_cased}_obj.has_{field_name}())\n"
                            output_content += f'\t\t\t\t\t{message_name_snake_cased}_document.append(' \
                                              f'{package_name}_handler::kvp("_id", {message_name_snake_cased}' \
                                              f'_obj.{field_name}()));\n'
                        output_content += "\t\t\t}\n"
                else:
                    output_content += f"\t\t\tif ({message_name_snake_cased}_obj.{field_name}_size() > 0)\n"
                    output_content += f"\t\t\t{{\n"
                    output_content += f"\t\t\t\tbsoncxx::builder::basic::array {field_name}_array;\n"
                    output_content += f"\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_obj.{field_name}_size(); ++i)\n"
                    output_content += f"\t\t\t\t\t{field_name}_array.append({message_name_snake_cased}_obj.{field_name}(i));\n"
                    output_content += f"\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp" \
                                      f"({package_name}_handler::{field_name}_fld_name, {field_name}_doc_array));\n"
                    output_content += f"\t\t\t}}\n"

            else:
                if field_type != "repeated":
                    output_content += f"\t\t\tif ({message_name_snake_cased}_obj.has_{field_name}())"
                    output_content += f" {{\n"
                    output_content += f"\t\t\t\tbsoncxx::builder::basic::document {field_name}_doc;\n"
                    # print(f".............{field.proto.name}...............")
                    output_content += self.generate_nested_fields(field_type_message, field_name,
                                                                  message_name_snake_cased, package_name, field,
                                                                  field_name)
                    output_content += f"\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp(" \
                                      f"{package_name}_handler::{field_name}_fld_name, {field_name}_doc));\n"
                    output_content += f"\t\t\t}}\n"

                else:
                    output_content += self.generate_repeated_nested_fields(field_type_message, field_name,
                                                                           package_name, message_name_snake_cased,
                                                                           field, field_name)
        return output_content

    def generate_prepare_docs(self, message: protogen.Message, message_name_snake_cased: str,
                              package_name: str, message_name: str):

        output_content: str = ""
        output_content += f"\t\tvoid prepare_{message_name_snake_cased}_list_doc(const {package_name}::{message_name}List " \
                          f"&{message_name_snake_cased}_list_obj, std::vector<bsoncxx::builder::basic::document> " \
                          f"&{message_name_snake_cased}_document_list, const IsUpdateOrPatch is_update_or_patch) const"
        output_content += " {\n"
        output_content += f"\t\t\tfor (int i =0; i < {message_name_snake_cased}_list_obj.{message_name_snake_cased}_size(); " \
                          f"++i) {{\n"
        output_content += f"\t\t\t\tbsoncxx::builder::basic::document {message_name_snake_cased}_document;\n"

        for field in message.fields:
            field_name = field.proto.name
            field_type = field.cardinality.name.lower()
            field_type_message = field.message

            if field_type_message is None:
                if field_type != "repeated":
                    if field_name != "id":
                        if field_type == "required":
                            output_content += f"\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::" \
                                              f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                              f"{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"{field_name}()));\n"
                        else:
                            output_content += f"\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"has_{field_name}())\n"
                            output_content += f"\t\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::" \
                                              f"kvp({package_name}_handler::{field_name}_fld_name, " \
                                              f"{message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"{field_name}()));\n"
                    else:
                        if field_type == "required":
                            output_content += "\t\t\t\tif (IsUpdateOrPatch::DB_FALSE == is_update_or_patch) {\n"
                            output_content += f'\t\t\t\t\t{message_name_snake_cased}_document.append(' \
                                              f'{package_name}_handler::kvp("_id", {message_name_snake_cased}_list_obj.' \
                                              f'{message_name_snake_cased}(i).{field_name}()));\n'
                        else:
                            output_content += "\t\t\t\tif (IsUpdateOrPatch::DB_FALSE == update_or_patch) {\n"
                            output_content += f"\t\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                              f"has_{field_name}())\n"
                            output_content += f'\t\t\t\t\t{message_name_snake_cased}_document.append(' \
                                              f'{package_name}_handler::kvp("_id", {message_name_snake_cased}_list_obj.' \
                                              f'{message_name_snake_cased}(i).{field_name}()));\n'
                        output_content += "\t\t\t\t}\n"
                else:
                    output_content += f"\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"{field_name}_size() > 0)\n"
                    output_content += f"\t\t\t\t{{\n"
                    output_content += f"\t\t\t\t\tbsoncxx::builder::basic::array {field_name}_array;\n"
                    output_content += f"\t\t\t\t\tfor (int i = 0; i < {message_name_snake_cased}_list_obj." \
                                      f"{message_name_snake_cased}(i).{field_name}_size(); ++i)\n"
                    output_content += f"\t\t\t\t\t\t{field_name}_array.append({message_name_snake_cased}_list_obj." \
                                      f"{message_name_snake_cased}(i).{field_name}(i));\n"
                    output_content += f"\t\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp" \
                                      f"({package_name}_handler::{field_name}_fld_name, {field_name}_doc_array));\n"
                    output_content += f"\t\t\t\t}}\n"

            else:
                if field_type != "repeated":
                    output_content += f"\t\t\t\tbsoncxx::builder::basic::document {field_name}_doc;\n"
                    output_content += f"\t\t\t\tif ({message_name_snake_cased}_list_obj.{message_name_snake_cased}(i)." \
                                      f"has_{field_name}())"
                    output_content += f" {{\n"
                    # print(f".............{field.proto.name}...............")
                    output_content += self.generate_msg_nested_fields(field_type_message, field_name,
                                                                      message_name_snake_cased, package_name, field,
                                                                      field_name)
                    output_content += f"\t\t\t\t\t{message_name_snake_cased}_document.append({package_name}_handler::kvp(" \
                                      f"{package_name}_handler::{field_name}_fld_name, {field_name}_doc));\n"
                    output_content += f"\t\t\t\t}}\n"

                else:
                    output_content += self.generate_msg_repeated_nested_fields(field_type_message, field_name,
                                                                               package_name, message_name_snake_cased,
                                                                               field, field_name)
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)
        file_name = str(file.proto.name).split(".")[0]
        package_name = str(file.proto.package)
        output_content = ""

        class_name_list = package_name.split("_")
        class_name = ''.join(word.capitalize() for word in class_name_list)
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content += self.headers_generate_handler(file_name, class_name_snake_cased)

        output_content += f"namespace {class_name_snake_cased}_handler {{\n"

        output_content += "\n\tenum class IsUpdateOrPatch {\n"
        output_content += "\t\tDB_TRUE = true,\n"
        output_content += "\t\tDB_FALSE = false\n\t};\n\n"

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root) and \
                    CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_executor_options):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)

                output_content += self.generate_class_handler(class_name, message_name, package_name,
                                                              message_name_snake_cased, file_name)

                output_content += self.generate_insert_handler(class_name, message_name, package_name,
                                                               message_name_snake_cased, file_name)

                output_content += self.generate_patch_handler(class_name, message_name, package_name,
                                                              message_name_snake_cased, file_name)

                output_content += self.generate_public_members_handler(class_name, message_name, package_name,
                                                                       message_name_snake_cased, file_name)

                output_content += self.generate_bulk_insert_and_update(message_name_snake_cased, message_name,
                                                                       package_name)
                output_content += self.generate_get_data_from_db(message_name, package_name,
                                                                 message_name_snake_cased, class_name)
                output_content += self.generate_delete_from_db_handler(message_name_snake_cased)

                output_content += f"\t\tstd::string {message_name}KeyToDbIdAsString() {{\n"
                output_content += f'\t\t\tstd::string result = "{message_name_snake_cased}_key_to_db_id: ";\n'
                output_content += '\t\t\tint index = 1;\n'
                output_content += f'\t\t\tfor (const auto& entry : {message_name_snake_cased}_key_to_db_id) {{\n'
                output_content += (f'\t\t\t\tresult += "key " + std::to_string(index) + ":" + entry.first + " ; value " '
                                   f'+ std::to_string(index) + ":" + entry.second;\n')
                output_content += "\t\t\t\t++index;\n"
                output_content += "\t\t\t}\n"
                output_content += "\t\t\treturn result;\n\t\t}\n\n"

                output_content += self.generate_private_members_handler(class_name, package_name,
                                                                        message_name_snake_cased, file_name)
                output_content += self.generate_prepare_doc(message, message_name_snake_cased, package_name,
                                                            message_name)
                output_content += "\t\t}\n\n"
                output_content += self.generate_prepare_docs(message, message_name_snake_cased, package_name,
                                                             message_name)
                output_content += f"\t\t\t\t{message_name_snake_cased}_document_list.push_back(std::move(" \
                                  f"{message_name_snake_cased}_document));\n"
                output_content += "\t\t\t}\n\t\t}\n\n"

                output_content += "\t};\n\n"

        output_content += "}\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_mongo_db_codec.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
