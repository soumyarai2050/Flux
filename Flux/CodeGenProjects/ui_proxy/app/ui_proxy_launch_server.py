import os
import uvicorn
import datetime
import logging
from pathlib import PurePath

# project imports
from Flux.CodeGenProjects.ui_proxy.app.ui_proxy_service_fastapi import *
from FluxPythonUtils.scripts.utility_functions import configure_logger, add_logging_levels, parse_to_int

project_data_dir = PurePath(__file__).parent.parent
config_yaml_path = project_data_dir / "data" / "config.yaml"
log_dir_path = project_data_dir / "log"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

custom_log_lvls = config_yaml_dict.get("custom_logger_lvls")
add_logging_levels([] if custom_log_lvls is None else custom_log_lvls)
log_lvl = config_yaml_dict.get("log_level")
datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
log_file_name = f"ui_proxy_logs_{datetime_str}.log"
configure_logger(log_lvl, log_file_dir_path=str(log_dir_path),
                 log_file_name=log_file_name)

host = config_yaml_dict.get("server_host")
port = config_yaml_dict.get("server_port")
if (host is None or len(host) < 1) or (port is None or len(port) < 1):
    err_str = "Either 'server_host' or 'server_host' not found in data/config.yaml file of ui_proxy_server project"
    logging.exception(err_str)
    raise Exception(err_str)


def ui_proxy_launch_server():
    os.environ["PORT"] = str(port)
    if reload_env := os.getenv("RELOAD"):
        reload_status: bool = True if reload_env.lower() == "true" else False
    else:
        reload_status: bool = False
    # Log Levels
    # NOTSET: 0
    # DEBUG: 10
    # INFO: 20
    # WARNING: 30
    # ERROR: 40
    # CRITICAL: 50
    uvicorn.run(reload=reload_status,
                host=host,
                port=parse_to_int(port),
                app=ui_proxy_service_app,
                log_level=20)


if __name__ == "__main__":
    ui_proxy_launch_server()
