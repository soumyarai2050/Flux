import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
env_dict = {
    "DEBUG_SLEEP_TIME": "0"
}
code_gen_engine_env_manager.init_env_and_update_sys_path("sample_project", "hybrid_beanie_fastapi_gen_config.yaml",
                                                         "PluginFastApi", env_dict)

params_list = [
    str(code_gen_engine_env_manager.project_dir),
    str(code_gen_engine_env_manager.config_path_with_file_name)
]

code_gen_engine_env_manager.execute_python_script(str(code_gen_engine_env_manager.plugin_dir / "trigger_script.py"), params_list)
