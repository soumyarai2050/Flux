# standard imports
import logging
import sys
from typing import List
from pathlib import PurePath

# project imports
home_dir_path = PurePath(__file__).parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager
from Flux.PyCodeGenEngine.FluxCodeGenCore.execute import Execute

code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
flux_import_dir_path_list = [code_gen_engine_env_manager.code_gen_root, str(PurePath(__file__).parent)]

flux_config_path = PurePath(__file__).parent / "flux_core.yaml"
flux_config_yaml = YAMLConfigurationManager.load_yaml_configurations(str(flux_config_path))
flux_options_files = flux_config_yaml.get("options_files")
flux_core_or_util_files = flux_config_yaml.get("core_or_util_files")

proto_file_list: List[str] = []
if flux_options_files:
    proto_file_list.extend(flux_options_files)
if flux_core_or_util_files:
    proto_file_list.extend(flux_core_or_util_files)

Execute.compile_proto_file(proto_file_list, flux_import_dir_path_list, str(PurePath(__file__).parent))

