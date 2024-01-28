import sys
from pathlib import PurePath
from datetime import datetime
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager


if __name__ == "__main__":

    project_dir: PurePath = PurePath(__file__).parent.parent
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    db_type: str = "bare"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log' }",
        "LOG_FILE_NAME": f"template_project_name_{db_type}_logs_{datetime_str}.log",
        "LOG_LEVEL": "debug",
        "FASTAPI_FILE_NAME": f"template_model_service_{db_type}_fastapi",
        "DBType": f"{db_type}"
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "_", env_dict)

    # Importing here to get LOG_FILE_NAME and LOG_LEVEL set before getting logging config triggered in
    # template_model_service_cache_fastapi file
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.template_project_name.generated.FastApi.template_model_service_launch_server import \
        template_model_service_launch_server

    template_model_service_launch_server()
