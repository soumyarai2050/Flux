#!/usr/bin/env python
import os
import protogen
from typing import List, Callable, ClassVar
import logging
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin, main


class Pb2ImportGenerator(BaseProtoPlugin):
    """
    Plugin Script to add imports of pb2 files in insertion_imports.py
    """
    insertion_import_file_name: ClassVar[str] = "insertion_imports.py"

    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def output_file_generate_handler(self, file: protogen.File):
        proto_file_name = str(file.proto.name).split('/')[-1].split(".")[0]
        if (py_code_gen_core_path := os.getenv("PY_CODE_GEN_CORE_PATH")) is not None and len(py_code_gen_core_path):
            template_file_path = os.path.join(py_code_gen_core_path, Pb2ImportGenerator.insertion_import_file_name)
            output_file_name = Pb2ImportGenerator.insertion_import_file_name
        else:
            err_str = f"Env var 'PY_CODE_GEN_CORE_PATH' received as {py_code_gen_core_path}"
            logging.exception(err_str)
            raise Exception(err_str)

        import_path = self.import_path_from_os_path("OUTPUT_DIR", f"ProtoGenPy.{proto_file_name}_pb2")
        import_str = f"import {import_path}"

        with open(template_file_path) as temp_file:
            temp_file_content = temp_file.read()

        # Returning empty string if import statement already present in template file
        for row in temp_file_content.split("\n"):
            if import_str == row:
                import_str = ""

        self.output_file_name_to_template_file_path_dict[output_file_name] = template_file_path
        return {
            output_file_name: {
                "import_pb2": import_str
            }
        }


if __name__ == "__main__":
    main(Pb2ImportGenerator)
