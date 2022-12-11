import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
env_dict = {
    "RELOAD": "false",
    "DEBUG_SLEEP_TIME": "0"
}
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_", "_", env_dict)

project_dir: PurePath = PurePath(__file__).parent.parent
script_path = project_dir / "output" / "strat_manager_service_cached_beanie_fastapi.py"
code_gen_engine_env_manager.execute_python_script(str(script_path))
