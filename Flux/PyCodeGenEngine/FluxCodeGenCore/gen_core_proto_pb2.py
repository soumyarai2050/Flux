import sys
from typing import List
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
flux_options_dir_path = code_gen_engine_env_manager.code_gen_root
flux_options_path = str(PurePath(flux_options_dir_path) / "flux_options.proto")
code_gen_core_path = code_gen_engine_env_manager.py_code_gen_core_path

util_proto_file_list: List[str] = ["flux_options.proto", "ui_core.proto", "trade_core.proto", "flux_utils.proto"]

for proto_file in util_proto_file_list:
    # python handling
    cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} {proto_file}"
    code_gen_engine_env_manager.execute_shell_command(cmd)

    # Cpp handling
    cmd = f"protoc --proto_path={flux_options_dir_path} --cpp_out={code_gen_core_path} {proto_file}"
    code_gen_engine_env_manager.execute_shell_command(cmd)
