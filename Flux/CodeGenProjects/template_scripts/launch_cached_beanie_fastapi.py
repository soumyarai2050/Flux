import sys
from pathlib import PurePath
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager

# Todo: Might be broken due to changes made in cache and beanie fastapi

if __name__ == "__main__":

    project_dir: PurePath = PurePath(__file__).parent.parent
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_PATH": f"{project_dir / 'generated' / 'logs.log'}",
        "LOG_LEVEL": "debug"
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "_", env_dict)

    # Importing here to get LOG_FILE_PATH and LOG_LEVEL set before getting logging config triggered in
    # template_model_service_cached_beanie_fastapi file
    from Flux.CodeGenProjects.template_project_name.generated.template_model_service_cached_beanie_fastapi import \
        launch_template_model_service_cached_beanie_fastapi

    launch_template_model_service_cached_beanie_fastapi()

