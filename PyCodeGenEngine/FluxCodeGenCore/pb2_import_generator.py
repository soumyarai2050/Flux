#!/usr/bin/env python
import os
import protogen
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_proto_plugin import BaseProtoPlugin
from typing import List, Callable


class Pb2ImportGenerator(BaseProtoPlugin):
    """
    Plugin Script to add imports of pb2 files in insertion_imports.py
    """

    def __init__(self, base_dir_path: str, config_path: str | None = None):
        super().__init__(base_dir_path, config_path)
        # Overriding below all data-members for this script
        # Both template_file_path and output_file_name are same as this plugin adds import in same template file
        self.template_file_path = os.path.join(os.getenv("PLUGIN_DIR"),
                                               self.config_yaml["insertion_import_file_name"])
        self.output_file_name = self.config_yaml["insertion_import_file_name"]
        self.insertion_point_key_list: List[str] = [
            "import_pb2",
        ]
        self.insertion_point_key_to_callable_list: List[Callable] = [
            self.handle_import_pb2,
        ]

    def handle_import_pb2(self, file: protogen.File) -> str:
        proto_file_name = str(file.proto.name).split('/')[-1].split(".")[0]
        project_dir_import = ".".join(os.getenv("PROJECT_DIR").split("/")[-3:])
        import_str = f"import {project_dir_import}.output.{proto_file_name}_pb2"

        with open(self.template_file_path) as temp_file:
            temp_file_content = temp_file.read()

        # Returning empty string if import statement already present in template file
        for row in temp_file_content.split("\n"):
            if import_str == row:
                return ""

        return import_str


if __name__ == "__main__":
    def main():
        project_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        proto_to_db_plugin = Pb2ImportGenerator(project_dir_path)
        proto_to_db_plugin.process()

    main()
