import os
import sys
import shutil
from typing import List
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.PyCodeGenEngine.FluxCodeGenCore.plugin_execute_script import PluginExecuteScript
from Flux.CodeGenProjects.AddressBook.bartering_gen_engine_env import BarteringGenEngineEnv
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager


if __name__ == "__main__":
    code_gen_engine_env_manager = BarteringGenEngineEnv.get_instance()
    env_var_dict = BarteringGenEngineEnv.default_gen_env_var_dict
    env_var_dict["PLUGIN_FILE_NAME"] = "msgspec_model_plugin.py"
    env_var_dict["ModelType"] = "msgspec"

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "PluginORMModel", env_var_dict)

    plugin_execute_script = PluginExecuteScript(str(code_gen_engine_env_manager.project_dir), "service.proto")
    plugin_execute_script.execute()

    # moving generated core ORMModel files to their locations
    root_flux_core_config_yaml_path = code_gen_engine_env_manager.code_gen_root / "flux_core.yaml"
    root_flux_core_config_yaml_dict = (
        YAMLConfigurationManager.load_yaml_configurations(str(root_flux_core_config_yaml_path)))
    root_core_proto_files: List[str] = []
    option_files = root_flux_core_config_yaml_dict.get("options_files")
    core_or_util_files = root_flux_core_config_yaml_dict.get("core_or_util_files")
    if option_files is not None and option_files:
        root_core_proto_files.extend(option_files)
    if core_or_util_files is not None and core_or_util_files:
        root_core_proto_files.extend(core_or_util_files)
    # removing .proto from file_names
    root_core_proto_files = [proto_file.removesuffix(".proto") for proto_file in root_core_proto_files]

    project_group_flux_core_config_yaml_path = code_gen_engine_env_manager.project_dir.parent.parent / "flux_core.yaml"
    project_group_flux_core_config_yaml_dict = (
        YAMLConfigurationManager.load_yaml_configurations(str(project_group_flux_core_config_yaml_path)))
    project_grp_core_proto_files = []
    option_files = project_group_flux_core_config_yaml_dict.get("options_files")
    core_or_util_files = project_group_flux_core_config_yaml_dict.get("core_or_util_files")
    if option_files is not None and option_files:
        project_grp_core_proto_files.extend(option_files)
    if core_or_util_files is not None and core_or_util_files:
        project_grp_core_proto_files.extend(core_or_util_files)
    # removing .proto from file_names
    project_grp_core_proto_files = [proto_file.removesuffix(".proto") for proto_file in project_grp_core_proto_files]

    if not os.path.exists(code_gen_engine_env_manager.py_code_gen_core_path / "ORMModel"):
        os.mkdir(code_gen_engine_env_manager.py_code_gen_core_path / "ORMModel")
    if not os.path.exists(code_gen_engine_env_manager.project_dir.parent.parent / "ORMModel"):
        os.mkdir(code_gen_engine_env_manager.project_dir.parent.parent / "ORMModel")

    gen_suffix = "_msgspec_model.py"
    for model_file in os.listdir(code_gen_engine_env_manager.plugin_output_dir):
        if model_file.removesuffix(gen_suffix) in root_core_proto_files:
            shutil.move(code_gen_engine_env_manager.plugin_output_dir / model_file,
                        code_gen_engine_env_manager.py_code_gen_core_path / "ORMModel" / model_file)
        elif model_file.removesuffix(gen_suffix) in project_grp_core_proto_files:
            shutil.move(code_gen_engine_env_manager.plugin_output_dir / model_file,
                        code_gen_engine_env_manager.project_dir.parent.parent / "ORMModel" / model_file)
