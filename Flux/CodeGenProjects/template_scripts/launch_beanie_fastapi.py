import os.path
import sys
from pathlib import PurePath
from datetime import datetime
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int


if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        port = parse_to_int(args[1])
    else:
        project_dir: PurePath = PurePath(__file__).parent.parent
        config_yaml_path = project_dir / "data" / "config.yaml"
        db_type: str = "beanie"
        config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
        port = 8000 if ((config_port := config_yaml_dict.get(f"main_server_beanie_port")) is None or
                        len(config_port) == 0) else parse_to_int(config_port)
    project_dir: PurePath = PurePath(__file__).parent.parent
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()
    db_type: str = "beanie"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log'}",
        "LOG_FILE_NAME": f"template_project_name_{db_type}_{port}_logs_{datetime_str}.log",
        "FASTAPI_FILE_NAME": f"template_model_service_{db_type}_fastapi",
        "PORT": f"{port}",
        "DBType": f"{db_type}",
        "DB_NAME": f"template_project_name_{port}"
    }

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "_", env_dict)

    # creating config file for this server run if not exists
    config_file_path = project_dir / "data" / f"template_project_name_{port}_config.yaml"
    if not os.path.exists(config_file_path):
        temp_config_file_path = project_dir.parent / "template_yaml_configs" / "server_config.yaml"
        with open(temp_config_file_path, "r") as temp_config:
            config_lines = temp_config.readlines()

        with open(config_file_path, "w") as new_config_file:
            for config_line in config_lines:
                if "beanie_port:" in config_line:
                    config_line = f"beanie_port: '{port}'\n"
                new_config_file.write(config_line)

    from Flux.CodeGenProjects.template_project_name.generated.FastApi.template_model_service_launch_server import \
        template_model_service_launch_server

    template_model_service_launch_server()
