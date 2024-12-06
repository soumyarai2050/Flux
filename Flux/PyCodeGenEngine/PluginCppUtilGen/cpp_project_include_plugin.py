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
from Flux.CodeGenProjects.TradeEngine.ProjectGroupPlugins.PluginStratExecutor.strat_executor_plugin import StratExecutorPlugin


class CppProjectIncludePlugin(BaseProtoPlugin):
    """
    Plugin to generate sample output to project include generate from proto schema
    """

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    @staticmethod
    def header_generate_handler(package_name: str):
        output_content: str = ""
        output_content += "#pragma once\n\n"
        output_content += f'#include "../../../{package_name}/generated/CppUtilGen/{package_name}_object_to_json.h"\n'
        output_content += f'#include "../../../{package_name}/generated/CppCodec/{package_name}_mongo_db_codec.h"\n'
        output_content += f'#include "../../../{package_name}/generated/CppUtilGen/{package_name}_key_handler.h"\n'
        output_content += f'#include "../../../{package_name}/generated/CppUtilGen/{package_name}_json_to_object.h"\n'
        output_content += f'#include "../../../{package_name}/generated/CppUtilGen' \
                          f'/{package_name}_constants.h"\n\n'
        return output_content

    def output_file_generate_handler(self, file: protogen.File):
        output_content: str = ""
        package_name = str(file.proto.package)
        output_content += self.header_generate_handler(package_name)
        output_content += f"using namespace {package_name}_handler;\n\n"

        output_file_name = f"project_includes.h"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppProjectIncludePlugin)
