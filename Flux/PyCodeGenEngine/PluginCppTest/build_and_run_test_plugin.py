#!/usr/bin/env python
from typing import List
import os
import time

if (debug_sleep_time := os.getenv("DEBUG_SLEEP_TIME")) is not None and \
        isinstance(debug_sleep_time := int(debug_sleep_time), int):
    time.sleep(debug_sleep_time)
# else not required: Avoid if env var is not set or if value cant be type-cased to int

import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main
from FluxPythonUtils.scripts.utility_functions import convert_camel_case_to_specific_case


class CppBuildAndRunTestPlugin(BaseProtoPlugin):

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)
        self.root_message_list: List[protogen.Message] = []
        self.field = []

    def output_file_generate_handler(self, file: protogen.File):

        file_name: str = str(file.proto.name).split(".")[0]
        package_name: str = str(file.proto.package)
        class_name_list: List[str] = package_name.split('_')
        class_name: str = ""
        for i in class_name_list:
            class_name = class_name + i.capitalize()
        class_name_snake_cased: str = convert_camel_case_to_specific_case(class_name)

        output_content: str = ""

        output_content += "#!/bin/bash\n\n"

        output_content += "# source directory where your CMakeLists.txt file is located\n"
        output_content += 'SOURCE_DIR="../../../../../tests/CodeGenProjects/market_data/cpp_app/"\n\n'
        # output_content += "# Change the file mode to executable mode\n"
        # output_content += "chmod +x build_and_run_test.sh\n\n"
        #
        # output_content += "# Create a build directory\n"
        # output_content += f"chmod +x {class_name_snake_cased}_build_and_run_test.sh\n\n"

        output_content += "# Create a build directory\n"
        output_content += 'mkdir -p "${SOURCE_DIR}/build"\n\n'

        output_content += "# Change dir to build\n"
        output_content += 'cd "${SOURCE_DIR}/build"\n\n'

        output_content += "# Run CMake to generate build files\n"
        output_content += 'cmake "${SOURCE_DIR}"\n\n'

        output_content += "# build process\n"
        output_content += "make\n\n"

        output_content += 'cd "${SOURCE_DIR}/build/Google_tests"\n\n'

        output_content += "./Google_Tests_run\n\n"

        output_content += '# Clean up build files\n'
        output_content += 'cd ../..\n'
        output_content += 'rm -rf build'

        output_file_name = f"run.sh"
        return {output_file_name: output_content}


if __name__ == "__main__":
    main(CppBuildAndRunTestPlugin)

