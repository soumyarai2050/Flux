import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
flux_options_dir_path = code_gen_engine_env_manager.code_gen_root
flux_options_path = str(PurePath(flux_options_dir_path) / "flux_options.proto")
code_gen_core_path = code_gen_engine_env_manager.py_code_gen_core_path

cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} flux_options.proto"
code_gen_engine_env_manager.execute_shell_command(cmd)

# For ui_core.proto
cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} ui_core.proto"
code_gen_engine_env_manager.execute_shell_command(cmd)

# For trade_core.proto
cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} trade_core.proto"
code_gen_engine_env_manager.execute_shell_command(cmd)

# For flux_utils.proto
cmd = f"protoc --proto_path={flux_options_dir_path} --python_out={code_gen_core_path} flux_utils.proto"
code_gen_engine_env_manager.execute_shell_command(cmd)

