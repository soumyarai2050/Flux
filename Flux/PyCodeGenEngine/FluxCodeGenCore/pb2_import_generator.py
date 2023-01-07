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
        # Overriding below all data-members for this script
        # Both template_file_path and output_file_name are same as this plugin adds import in same template file
        if (py_code_gen_core_path := os.getenv("PY_CODE_GEN_CORE_PATH")) is not None:
            self.template_file_path = os.path.join(py_code_gen_core_path, Pb2ImportGenerator.insertion_import_file_name)
            self.output_file_name = Pb2ImportGenerator.insertion_import_file_name
        else:
            err_str = f"Env var 'PY_CODE_GEN_CORE_PATH' received as None"
            logging.exception(err_str)
            raise Exception(err_str)
        self.insertion_point_key_list: List[str] = [
            "import_pb2",
        ]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_import_pb2,
        ]

    def handle_import_pb2(self, file: protogen.File) -> str:
        proto_file_name = str(file.proto.name).split('/')[-1].split(".")[0]
        if (project_dir := os.getenv("PROJECT_DIR")) is not None:
            project_dir_import = ".".join(project_dir.split("/")[-3:])
        else:
            err_str = "Env var 'PROJECT_DIR' received as None"
            logging.exception(err_str)
            raise Exception(err_str)
        import_str = f"import {project_dir_import}.generated.{proto_file_name}_pb2"

        with open(self.template_file_path) as temp_file:
            temp_file_content = temp_file.read()

        # Returning empty string if import statement already present in template file
        for row in temp_file_content.split("\n"):
            if import_str == row:
                return ""

        return import_str


if __name__ == "__main__":
    main(Pb2ImportGenerator)
