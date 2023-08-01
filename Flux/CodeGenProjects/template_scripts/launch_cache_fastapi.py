import sys
from pathlib import PurePath
from datetime import datetime
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int


if __name__ == "__main__":

    project_dir: PurePath = PurePath(__file__).parent.parent
    config_yaml_path = project_dir / "data" / "config.yaml"
    config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    db_type: str = "cache"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    port = 8000 if ((config_port := config_yaml_dict.get(f"{db_type}_port")) is None or
                    len(config_port) == 0) else parse_to_int(config_port)
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log' }",
        "LOG_FILE_NAME": f"template_project_name_{db_type}_logs_{datetime_str}.log",
        "FASTAPI_FILE_NAME": f"template_model_service_{db_type}_fastapi",
        "DBType": f"{db_type}",
        "PORT": f"{port}",
    }
    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "_", env_dict)

    # Importing here to get LOG_FILE_NAME and LOG_LEVEL set before getting logging config triggered in
    # template_model_service_cache_fastapi file
    from Flux.CodeGenProjects.template_project_name.generated.FastApi.template_model_service_launch_server import \
        template_model_service_launch_server

    template_model_service_launch_server()
