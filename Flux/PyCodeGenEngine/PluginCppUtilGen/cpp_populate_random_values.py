#!/usr/bin/env python
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

    @staticmethod
    def header_generate_handler(file_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += f'#include "../../cpp_app/include/RandomDataGen.h"\n'
        output_content += '#include "bsoncxx/oid.hpp"\n'
        output_content += f'#include "../ProtoGenCc/{file_name}.pb.h"\n\n'
        return output_content

    def generate_nested_fields(self, field_type_message: protogen.Message, field_name,
                               message_name_snake_cased: str, package_name: str, field: protogen.Field, parent_field: str):
        output = ""
        initial_parent_field: str = field.proto.name

        for message_field in field_type_message.fields:
            message_field_name = message_field.proto.name
            field_type = message_field.cardinality.name.lower()
            if message_field.message is None:
                if field_name != initial_parent_field:
                    if field_name != parent_field and initial_parent_field != parent_field and message_field.kind.\
                            name.lower() != "enum":
                        if field_type != "repeated":
                            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                            (message_field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                                output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->" \
                                          f"mutable_{parent_field}()->mutable_{field_name}()->set_" \
                                          f"{message_field_name}(get_utc_time());\n"
                            else:
                                output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->" \
                                          f"mutable_{parent_field}()->mutable_{field_name}()->set_{message_field_name}" \
                                          f"(random_data_gen.get_random_{message_field.kind.name.lower()}());\n"
                        else:
                            output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{parent_field}()." \
                                      f"mutable_{field_name}()->add_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"
                    elif message_field.kind.name.lower() != "enum":
                        if field_type != "repeated":
                            output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{field_name}()->" \
                                      f"set_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"
                        else:
                            output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->mutable_{field_name}()->" \
                                      f"add_{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"

                else:
                    if field_type != "repeated" and message_field.kind.name.lower() != "enum":
                        if CppPopulateRandomValueHandlerPlugin.is_option_enabled \
                                    (message_field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                            output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->set_" \
                                      f"{message_field_name}(get_utc_time());\n"
                        else:
                            output += f"\t\t{message_name_snake_cased}.mutable_{initial_parent_field}()->set_" \
                                      f"{message_field_name}(random_data_gen.get_random_" \
                                      f"{message_field.kind.name.lower()}());\n"
            elif message_field.message is not None and field_type != "repeated":
                if field_name != initial_parent_field and message_field.kind.name.lower() != "enum":
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
                else:
                    output += self.generate_nested_fields(message_field.message, message_field_name,
                                                          message_name_snake_cased, package_name, field, field_name)
        return output

    def output_file_generate_handler(self, file: protogen.File):
        self.get_all_root_message(file.messages)
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

        output_content += f"class {class_name}PopulateRandomValues {{ \n\n"

        output_content += "public:\n\n"

        output_content += "\tstatic std::string get_utc_time() {\n"
        output_content += "\t\tstd::chrono::system_clock::time_point now = std::chrono::system_clock::now();\n"
        output_content += "\t\tstd::time_t now_t = std::chrono::system_clock::to_time_t(now);\n"
        output_content += "\t\tchar buffer[80];\n"
        output_content += '\t\tstd::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S+00:00", std::gmtime(&now_t));\n'
        output_content += '\t\treturn std::string(buffer);\n'
        output_content += "\t}\n\n"

        for message in self.root_message_list:
            if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                        (message, CppPopulateRandomValueHandlerPlugin.flux_msg_json_root) and \
                    CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                                (message, CppPopulateRandomValueHandlerPlugin.flux_msg_executor_options):
                message_name = message.proto.name
                message_name_snake_cased = convert_camel_case_to_specific_case(message_name)
                output_content += f"\tstatic inline void {message_name_snake_cased} ({package_name}::{message_name} " \
                                  f"&{message_name_snake_cased}) {{\n\t\t"
                output_content += "RandomDataGen random_data_gen;\n\n"

                for field in message.fields:
                    field_name: str = field.proto.name
                    field_type: str = field.kind.name.lower()
                    field_type_message: protogen.Message | None = field.message

                    if field_type_message is None:
                        if field.cardinality.name.lower() == "repeated" and field_type != "enum":
                            output_content += f'\t\t{message_name_snake_cased}.add_{field_name}(random_data_gen.get_random_' \
                                              f'{field_type}());\n'
                        else:
                            if field_type != "enum":
                                if field_name != "id":
                                    if CppPopulateRandomValueHandlerPlugin.is_option_enabled\
                                        (field, CppPopulateRandomValueHandlerPlugin.flux_fld_val_is_datetime):
                                        output_content += f'\t\t{message_name_snake_cased}.set_{field_name}' \
                                                          f'(get_utc_time());\n'
                                    else:
                                        output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(random_data_gen.get_random_' \
                                                          f'{field_type}());\n'
                                else:
                                    output_content += "\t\tauto oid = bsoncxx::oid();\n"
                                    output_content += f'\t\t{message_name_snake_cased}.set_{field_name}(oid.to_string());\n'
                            elif field.cardinality.name.lower() == "required":
                                enum_field_list: list = field.enum.full_name.split(".")
                                if enum_field_list[-1] != "Side":
                                    output_content += f"\t\t{message_name_snake_cased}.set_{field_name}" \
                                                      f"({package_name}::{enum_field_list[-1]}::ASK);\n"
                                else:
                                    output_content += f"\t\t{message_name_snake_cased}.set_{field_name}" \
                                                      f"({field_name.capitalize()}::BUY);\n"

                    elif field_type_message is not None:
                        if field.cardinality.name.lower() != "repeated":
                            output_content += self.generate_nested_fields(field_type_message, field_name,
                                                                          message_name_snake_cased, package_name, field,
                                                                          field_name)

                output_content += "\t}\n\n"

        output_content += "};"

        proto_file_name = str(file.proto.name).split(".")[0]
        output_file_name = f"{class_name_snake_cased}_populate_random_values.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppPopulateRandomValueHandlerPlugin)

