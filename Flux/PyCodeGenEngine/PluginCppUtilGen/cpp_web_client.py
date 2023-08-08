#!/usr/bin/env python
import logging
import os
import time
from typing import List

from FluxPythonUtils.scripts.utility_functions import parse_to_int

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and len(debug_sleep_time):
    time.sleep(parse_to_int(debug_sleep_time))
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppWebClient(BaseProtoPlugin):
    """
    Plugin to generate cpp_web_client files
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def output_file_generate_handler(self, file: protogen.File):
        """
        Abstract method which is responsible for generating outputs from derived plugin class.
        Must return dict having:
        1. output_file_name to output_content key-value pair - for non-insertion point based template output
        2. output_file_name to output_content_dict key-value pair, where output_content_dict must have
        insertion_point to replacing_content key-value pair - for non-insertion point based template output
        """
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += f'#include "{class_name_snake_cased}_web_client.h"\n\n'
        output_content += f"boost::asio::io_context {package_name}_handler::MarketDataWebClient::io_context_;\n"
        output_content += (f"boost::asio::ip::tcp::resolver {package_name}_handler::MarketDataWebClient::resolver_"
                           f"(io_context_);\n")
        output_content += (f"boost::asio::ip::tcp::socket {package_name}_handler::MarketDataWebClient::socket_"
                           f"(io_context_);\n")
        output_content += (f"boost::asio::ip::tcp::resolver::results_type {package_name}_handler::"
                           f"MarketDataWebClient::result_;\n")
        output_file_name = f"{class_name_snake_cased}_web_client.cpp"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppWebClient)

