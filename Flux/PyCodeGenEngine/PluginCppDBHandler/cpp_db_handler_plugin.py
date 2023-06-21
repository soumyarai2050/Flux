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
    Plugin to generate DB Handler
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
    def header_generate_handler():
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += "#include <iostream>\n"
        output_content += "#include <sstream>\n"
        output_content += "#include <unordered_map>\n\n"
        output_content += "#include <bsoncxx/builder/stream/document.hpp>\n"
        output_content += "#include <bsoncxx/json.hpp>\n"
        output_content += "#include <mongocxx/client.hpp>\n"
        output_content += "#include <mongocxx/instance.hpp>\n"
        output_content += "#include <mongocxx/pool.hpp>\n\n"
        return output_content

    def const_string_generate_handler(self, file: protogen.File):
        output_content: str = ""
        for message in file.messages:
            if CppDbHandlerPlugin.is_option_enabled(message, CppDbHandlerPlugin.flux_msg_json_root):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f'\tconst std::string {message_name_snake_cased} = "{message_name}";\n'

        output_content += "\n\n"
        for field_name in self.field:
            output_content += f'\tconst std::string {field_name}_key = "{field_name}";\n'
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        # pre-requisite calls
        self.get_all_root_message(file.messages)
        self.get_field_names(self.root_message_list)
        package_name = str(file.proto.package)
        class_name_list = package_name.split("_")
        class_name: str = ""
        output_content: str = ""

        for i in class_name_list:
            class_name = class_name + i.capitalize()

        output_content += self.header_generate_handler()
        output_content += f"namespace {package_name}_handler "
        output_content += "{\n\n"
        output_content += "    using bsoncxx::builder::basic::make_array;\n"
        output_content += "    using bsoncxx::builder::basic::make_document;\n"
        output_content += "    using bsoncxx::builder::basic::kvp;\n\n"
        output_content += '    const std::string db_uri = getenv("MONGO_URI") ? getenv("MONGO_URI") : ' \
                          '"mongodb://localhost:27017";\n'
        file_name = str(file.proto.name).split(".")[0]
        output_content += f'    const std::string {file_name}_db_name = "{file_name}";\n'

        output_content += "\n\t// key constants used across classes via constants for consistency\n"

        output_content += self.const_string_generate_handler(file)

        output_content += "\n\n"
        output_content += "\tinline auto get_symbol_side_query(const std::string &symbol, const std::string &side){\n"
        output_content += '\t\tauto query = bsoncxx::builder::stream::document{}\n\t\t\t' \
                          '<< symbol_key << symbol << side_key << side\n\t\t\t<< bsoncxx::builder::stream::finalize;' \
                          '\n\t\treturn query;\n\t}\n\n'

        output_content += f"\tclass {class_name}_MongoDBHandler "
        output_content += "{\n\tpublic:\n\t\t"
        output_content += f'{class_name}_MongoDBHandler(): client(pool.acquire()), {file_name}_db((*client)[{file_name}_db_name])'
        output_content += "{\n\t\t\t"
        output_content += 'std::cout << "Mongo URI: " << str_uri << std::endl;\n\t\t}\n\n'

        output_content += "\t\tmongocxx::instance inst{};\n\t\tstd::string str_uri = "
        output_content += 'db_uri + "/?minPoolSize=2&maxPoolSize=2";'

        output_content += "\n\t\t" \
                          "mongocxx::uri uri{str_uri};\n\t\tmongocxx::pool pool{uri};\n\t\t" \
                          f"mongocxx::pool::entry client;\n\t\tmongocxx::database {file_name}_db;\n\t\t\n\t"
        output_content += "};\n}"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{proto_file_name}_db_handler.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppDbHandlerPlugin)
