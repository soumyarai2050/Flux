import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager

project_dir: PurePath = PurePath(__file__).parent.parent
code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
env_dict = {
    "RELOAD": "false",
    "DEBUG_SLEEP_TIME": "0",
    "LOG_FILE_PATH": f"{project_dir / 'generated' / 'cache_logs.log'}",
    "LOG_LEVEL": "debug",
    "FASTAPI_FILE_NAME": "strat_manager_service_cache_fastapi"
}
code_gen_engine_env_manager.init_env_and_update_sys_path("addressbook", "_", "_", env_dict)

# Importing here to get LOG_FILE_PATH and LOG_LEVEL set before getting logging config triggered in
# strat_manager_service_cache_fastapi file
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_launch_server import \
    strat_manager_service_launch_server

strat_manager_service_launch_server()
