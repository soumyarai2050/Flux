import os.path
import sys
import signal
from pathlib import PurePath
from datetime import datetime
home_dir_path = PurePath(__file__).parent.parent.parent.parent.parent
sys.path.append(str(home_dir_path))
from Flux.code_gen_engine_env import CodeGenEngineEnvManager
from FluxPythonUtils.scripts.general_utility_functions import YAMLConfigurationManager, parse_to_int


if __name__ == "__main__":
    project_dir: PurePath = PurePath(__file__).parent.parent
    config_yaml_path = project_dir / "data" / "config.yaml"
    config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
    host = config_yaml_dict.get("server_host")
    if host is None or len(host) == 0:
        raise Exception("Couldn't find 'server_host' key in data/config.yaml file")
    model_type: str = "msgspec"

    port = config_yaml_dict.get(f"main_server_beanie_port")
    if port is None:
        raise Exception("couldn't find 'main_server_beanie_port' key in data.config.yaml of this project")
    code_gen_engine_env_manager = CodeGenEngineEnvManager.get_instance()

    env_dict = {
        "RELOAD": "false",
        "DEBUG_SLEEP_TIME": "0",
        "LOG_FILE_DIR_PATH": f"{project_dir / 'log'}",
        "FASTAPI_FILE_NAME": f"template_model_service_{model_type}_fastapi",
        "HOST": host,
        "ModelType": f"{model_type}"
    }

    code_gen_engine_env_manager.init_env_and_update_sys_path("template_project_name", "_", "_", env_dict)

    # creating static and templates dirs
    static_dir_path = project_dir / "scripts" / host / "static"
    if not os.path.exists(static_dir_path):
        os.makedirs(static_dir_path)

    templates_dir_path = project_dir / "scripts" / host / "templates"
    if not os.path.exists(templates_dir_path):
        os.mkdir(templates_dir_path)

    from Flux.CodeGenProjects.AddressBook.ProjectGroup.template_project_name.generated.FastApi.template_model_service_launch_msgspec_server import \
        template_model_service_launch_msgspec_server

    template_model_service_launch_msgspec_server()

    # killing current process

    # Get the current process ID
    pid = os.getpid()

    # Kill the process
    os.kill(pid, signal.SIGKILL)  # or signal.SIGKILL for immediate termination
