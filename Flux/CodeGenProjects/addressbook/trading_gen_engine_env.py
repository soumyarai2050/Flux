# standard imports
from pathlib import PurePath
from typing import Dict
import os
import sys

# project imports
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


class TradingGenEngineEnv(CodeGenEngineEnvManager):

    def __init__(self):
        super().__init__()
        self.project_group_root: PurePath = PurePath(__file__).parent

    def init_env_and_update_sys_path(self, project_name: str, config_file_name: str, plugin_name: str,
                                     custom_env_dict: Dict[str, str] | None = None,
                                     use_project_group_template_script: bool | None = None):
        super().init_env_and_update_sys_path(project_name, config_file_name, plugin_name, custom_env_dict)

        self.project_dir = self.project_group_root / "ProjectGroup" / project_name
        os.environ["PROJECT_DIR"] = str(self.project_dir)

        self.config_path_with_file_name = self.project_dir / "misc" / config_file_name
        os.environ["CONFIG_PATH"] = str(self.config_path_with_file_name)

        if use_project_group_template_script:
            self.plugin_dir = self.project_group_root / "ProjectGroupPlugins" / plugin_name
            os.environ["PLUGIN_DIR"] = str(self.plugin_dir)

        # update output dir to be within project output dir
        self.base_output_dir = self.project_dir / "generated"
        os.environ["OUTPUT_DIR"] = str(self.base_output_dir)

        # Adding output dir for proto generated classes and generated outputs
        self.plugin_output_dir = self.base_output_dir / plugin_name[len("PLUGIN"):]
        os.environ["PLUGIN_OUTPUT_DIR"] = str(self.plugin_output_dir)

        root_pb2_dir = PurePath(os.environ.get("FLUX_CODE_GEN_ENGINE_PATH")) / "PyCodeGenEngine" / "FluxCodeGenCore" / "ProtoGenPy"
        project_group_pb2_dir = PurePath(__file__).parent / "ProtoGenPy"

        # Add required path to sys.path & export them
        sys.path.append(str(self.py_code_gen_core_path))
        sys.path.append(str(self.base_output_dir))
        sys.path.append(str(self.plugin_output_dir))
        sys.path.append(str(self.plugin_dir))
        sys.path.append(str(self.code_gen_root.parent))
        sys.path.append(str(root_pb2_dir))
        sys.path.append(str(project_group_pb2_dir))

        # prepare & export PYTHONPATH
        self.python_path += (":" + str(self.py_code_gen_core_path) + ":" + str(self.base_output_dir) +
                             ":" + str(self.plugin_output_dir) + ":" + str(self.plugin_dir / "PluginFastApi") +
                             ":" + str(self.code_gen_root.parent) + ":" + str(root_pb2_dir) +
                             ":" + str(project_group_pb2_dir))
        os.environ["PYTHONPATH"] = str(self.python_path)
