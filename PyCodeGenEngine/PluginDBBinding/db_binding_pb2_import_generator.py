#!/usr/bin/env python
import os
from FluxCodeGenEngine.PyCodeGenEngine.FluxCodeGenCore.pb2_import_generator import Pb2ImportGenerator


if __name__ == "__main__":
    def main():
        project_dir_path = os.getenv("PROJECT_DIR")
        config_path = os.getenv("CONFIG_PATH")
        pb2_import_generator = Pb2ImportGenerator(project_dir_path, config_path)
        pb2_import_generator.process()

    main()
