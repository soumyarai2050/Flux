from typing import List
import os
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript


class JsxPluginExecuteScript(PluginExecuteScript):
    def __init__(self, base_dir_path: str):
        super().__init__(base_dir_path)

    def get_required_param_values(self):
        # List of full paths of proto models in model directory
        all_proto_file_path_list = [os.path.join(self.base_dir_path, "model", proto_file)
                                    for proto_file in os.listdir(os.path.join(self.base_dir_path, "model"))]
        proto_file_path_list = [os.path.join(self.base_dir_path, "model", proto_file)
                                for proto_file in os.listdir(os.path.join(self.base_dir_path, "model"))
                                if "service" in proto_file]
        out_dir = os.path.join(os.getenv("PROJECT_DIR"), "output")
        proto_files_dir_paths_list: List[str] = [
            os.path.join(self.base_dir_path, "model"),
            os.path.abspath(os.path.join(self.base_dir_path, "..", ".."))
        ]
        insertion_imports_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        return all_proto_file_path_list, proto_file_path_list, out_dir, proto_files_dir_paths_list, \
               insertion_imports_dir_path

