#!/usr/bin/env python
import os
from Flux.PyCodeGenEngine.FluxCodeGenCore.pb2_import_generator import Pb2ImportGenerator


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_DIR")
        json_proto_to_db_plugin = Pb2ImportGenerator(project_dir_path)
        json_proto_to_db_plugin.process()

    main()
