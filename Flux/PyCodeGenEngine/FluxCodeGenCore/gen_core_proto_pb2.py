import logging
import sys
from typing import List
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
flux_options_dir_path = code_gen_engine_env_manager.code_gen_root
flux_options_path = str(PurePath(flux_options_dir_path) / "flux_options.proto")
code_gen_core_path = code_gen_engine_env_manager.py_code_gen_core_path

flux_config_path = PurePath(__file__).parent.parent.parent / "flux_core.yaml"
flux_config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(flux_config_path))
flux_options_files = flux_config_yaml.get("options_files")
flux_core_or_util_files = flux_config_yaml.get("core_or_util_files")

proto_file_list: List[str] = []
if flux_options_files:
    proto_file_list.extend(flux_options_files)
if flux_core_or_util_files:
    proto_file_list.extend(flux_core_or_util_files)

if proto_file_list:
    for proto_file in proto_file_list:
        # python handling
        cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} {proto_file}"
        code_gen_engine_env_manager.execute_shell_command(cmd)

        # Cpp handling
        cmd = f"protoc --proto_path={flux_options_dir_path} --cpp_out={code_gen_core_path} {proto_file}"
        code_gen_engine_env_manager.execute_shell_command(cmd)
else:
    err_str = "Can't find any proto file to be used in protoc command for pb2 file generation"
    logging.exception(err_str)
    raise Exception(err_str)
