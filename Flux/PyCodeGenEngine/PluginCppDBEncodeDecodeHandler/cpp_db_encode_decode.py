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

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)
        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        output_content: str = ""
        class_name_list: List[str] = package_name.split("_")
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()

        output_content += "#pragma once\n\n"
        output_content += "#include <unordered_map>\n\n"
        output_content += f'#include "../CppDBHandler/{file_name}_db_handler.h"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'

        for message in self.root_message_list:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f"class {class_name}{message_name}Codec "
                output_content += "{\n\npublic:\n\t"
                output_content += f'explicit {class_name}{message_name}Codec({package_name}_handler::' \
                                  f'{class_name}_MongoDBHandler &mongo_db_) : mongo_db(std::move(mongo_db_))'
                output_content += "{}\n\n"

                output_content += f"\tstatic inline std::string get_key(const {package_name}::{message_name} " \
                                  f"&{message_name_snake_cased}_data) "
                output_content += "{\n\t\t"
                output_content += 'return "Not Implemented";\n\t}\n\n'

                output_content += f"\tvoid insert_or_update_{message_name_snake_cased}({package_name}::" \
                                  f"{message_name} &{message_name_snake_cased}_data) "
                output_content += "{\n\t\t"
                output_content += f"if (!{message_name_snake_cased}_data.IsInitialized() && has_required_fields" \
                                  f"({message_name_snake_cased}_data))\n\t\t\treturn;\n\t\t"
                output_content += f"bsoncxx::builder::basic::document {message_name_snake_cased}_document"
                output_content += "{};\n\t\t"
                output_content += f"\n\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_data, " \
                                  f"{message_name_snake_cased}_document);"
                output_content += f'\n\t\tauto found = {message_name_snake_cased}_key_to_db_id.find' \
                                  f'(get_key({message_name_snake_cased}_data));\n\t\t'
                output_content += f'if (found == {message_name_snake_cased}_key_to_db_id.end()) '
                output_content += '{\n\t\t\t'
                output_content += f'insert_{message_name_snake_cased}({message_name_snake_cased}_document, ' \
                                  f'get_key({message_name_snake_cased}_data));\n\t\t'
                output_content += '} else {\n\t\t\t'
                output_content += f"update_or_patch_{message_name_snake_cased}(found->second, " \
                                  f"{message_name_snake_cased}_document);\n\t\t"
                output_content += "}\n\t}\n"

                output_content += f"\tvoid patch_{message_name_snake_cased}({package_name}::{message_name} " \
                                  f"&{message_name_snake_cased}_data)"
                output_content += "{\n\t\t"
                output_content += f"if (!{message_name_snake_cased}_data.IsInitialized())\n\t\t\treturn;\n\t\t"
                output_content += f"bsoncxx::builder::basic::document {message_name_snake_cased}_document"
                output_content += "{};\n\t\t"
                output_content += f'\n\t\tauto found = {message_name_snake_cased}_key_to_db_id.find' \
                                  f'(get_key({message_name_snake_cased}_data));\n\t\t'
                output_content += f'if (found == {message_name_snake_cased}_key_to_db_id.end()) '
                output_content += '\n\t\t\tthrow '
                output_content += f'std::runtime_error("{message_name_snake_cased} not found");'
                output_content += f"\n\t\tprepare_{message_name_snake_cased}_doc({message_name_snake_cased}_data, " \
                                  f"{message_name_snake_cased}_document);"
                output_content += f"\n\t\tupdate_or_patch_{message_name_snake_cased}(found->second, " \
                                  f"{message_name_snake_cased}_document);\n\t"
                output_content += "}\n\n"

                output_content += f"\tvoid update_or_patch_{message_name_snake_cased}(bsoncxx::types::bson_value::view " \
                                  f"&{message_name_snake_cased}_id, bsoncxx::builder::basic::document " \
                                  f"&{message_name_snake_cased}_document)"
                output_content += "{\n\t\t"
                output_content += f'auto update_filter = {package_name}_handler::make_document({package_name}' \
                                  f'_handler::kvp("_id", {message_name_snake_cased}_id));\n\t\t'
                output_content += f'auto update_document = {package_name}_handler::make_document({package_name}' \
                                  f'_handler::kvp("$set", {message_name_snake_cased}_document.view()));\n\t\t'
                output_content += f'{message_name_snake_cased}_collection.update_one(update_filter.view(), ' \
                                  f'update_document.view());\n\t'
                output_content += "}\n\n"

                output_content += f"\tbool insert_{message_name_snake_cased} (bsoncxx::builder::basic::document " \
                                  f"&{message_name_snake_cased}_document, const std::string &{message_name_snake_cased}_key) "
                output_content += "{\n\t\t"
                output_content += f"auto {message_name_snake_cased}_insert_result = {message_name_snake_cased}" \
                                  f"_collection.insert_one({message_name_snake_cased}_document.view());\n\t\t"
                output_content += f"auto {message_name_snake_cased}_id = {message_name_snake_cased}" \
                                  f"_insert_result->inserted_id();\n\t\t{message_name_snake_cased}_key_to_db_id" \
                                  f"[{message_name_snake_cased}_key] = {message_name_snake_cased}_id;" \
                                  f"\n\t\treturn true;"
                output_content += "\n\t}\n\n"

                output_content += f"\tbool has_required_fields({package_name}::{message_name} " \
                                  f"&{message_name_snake_cased}_data) "
                output_content += "{\n\t\t"
                output_content += f"if ({message_name_snake_cased}_data.IsInitialized()) "
                output_content += "\n\t\t\treturn true;\n\t\treturn false;\n\t}"

                output_content += f"\n\nprivate:\n\n\t{package_name}_handler::{class_name}_MongoDBHandler mongo_db;\n"
                output_content += f"\tmongocxx::collection {message_name_snake_cased}_collection = " \
                                  f"mongo_db.{file_name}_db[{package_name}_handler::{message_name_snake_cased}];\n\n"

                output_content += f"\tstd::unordered_map <std::string, bsoncxx::types::bson_value::view> " \
                                  f"{message_name_snake_cased}_key_to_db_id;\n\n"

                output_content += "protected:\n\n"
                output_content += f"\tvoid prepare_{message_name_snake_cased}_doc({package_name}::{message_name} " \
                                  f"&{message_name_snake_cased}_data, bsoncxx::builder::basic::document " \
                                  f"&{message_name_snake_cased}_document)"
                output_content += "{\n\t\t"

                for field in message.fields:
                    field_name = field.proto.name
                    field_type = field.cardinality.name.lower()
                    field_type_message: protogen.Message | None = field.message
                    field_type_message_snake_case = convert_camel_case_to_specific_case(str(field_type_message))
                    if field_type_message is None:
                        if field_type != "repeated":
                            output_content += f"\n\t\tif ({message_name_snake_cased}_data.has_{field_name}())\n\t\t\t" \
                                              f"{message_name_snake_cased}_document.append({package_name}_handler::" \
                                              f"kvp({package_name}_handler::{field_name}_key, " \
                                              f"{message_name_snake_cased}_data.{field_name}()));"
                        else:
                            output_content += f"\n\t\tif ({message_name_snake_cased}_data.{field_name}_size() > 0) "
                            output_content += "{\n\t\t\tbsoncxx::builder::basic::array "
                            output_content += f"{field_name}_array"
                            output_content += "{};\n\t\t\t"
                            output_content += f"for (int i = 0; i < {message_name_snake_cased}_data.{field_name}_size(); ++i) "
                            output_content += "{\n\t\t\t\t"
                            output_content += f"{field_name}_array.append({message_name_snake_cased}_data." \
                                              f"{field_name}(i));"
                            output_content += "\n\t\t\t}\n\t\t"
                            output_content += f"{message_name_snake_cased}_document.append({package_name}_handler::kvp" \
                                              f"({package_name}_handler::{field_name}_key, " \
                                              f"{field_name}_array));"
                            output_content += "\n\t\t}"

                    # elif field_type_message is not None:
                    #     if field_type != "repeated":
                    #         output_content += f"\n\t\tbsoncxx::builder::basic::document {field_name};\n"
                    #         output_content += f"\t\tif ({message_name_snake_cased}_data.has_{field_name}()) "
                    #         output_content += "{\n\t\t\t"
                    #         for message_field in field_type_message.fields:
                    #             message_field_name = message_field.proto.name
                    #
                    #             output_content += f"if ({message_name_snake_cased}_data.{field_name}().has_{message_field_name}()) "
                    #             output_content += f'\n\t\t\t\t{field_name}.append({package_name}_handler'
                    #             output_content += f'::kvp("{message_field_name}", {message_name_snake_cased}_data.' \
                    #                               f'{field_name}().{message_field_name}()));\n\t\t\t'
                    #
                    #         output_content += f"{field_name}.append({package_name}_handler::kvp({package_name}_handler::{field_name}_key, {field_name}));"
                    #         output_content += "\n\t\t}"

                        # else:
                        #     output_content += f"\n\t\tif ({message_name_snake_cased}_data.{field_name}_size() > 0) "
                        #     output_content += "{\n\t\t\tfor (const auto& "
                        #     output_content += f"{field_name}_doc : {message_name_snake_cased}_data.{field_name}()) "
                        #     output_content += "{\n\t\t\t\t"
                        #     output_content += f"bsoncxx::builder::basic::document {field_name}_document"
                        #     output_content += "{};\n\n"
                        #     for message_field in field_type_message.fields:
                        #         message_field_name = message_field.proto.name
                        #         output_content += f"\t\t\t\tif ({field_name}_doc.has_{message_field_name}())\n\t\t\t\t\t"
                        #         output_content += f'{field_name}_document.append({package_name}_handler::kvp' \
                        #                           f'("{message_field_name}", {field_name}_doc.{message_field_name}()));\n'
                        #     output_content += "\t\t\t}\n\t\t}\n"

                output_content += "\n\n\t}\n\n"

                output_content += "\n};\n\n"

        output_content += "\n"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{proto_file_name}_db_encode_decode.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
