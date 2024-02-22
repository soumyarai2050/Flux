# standard imports
from pathlib import PurePath
import logging

# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.generated.FastApi.strat_manager_service_http_client import (
    StratManagerServiceHttpClient)
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_analyzer.generated.FastApi.log_analyzer_service_http_client import (
    LogAnalyzerServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_analyzer.app.log_analyzer_service_helper import log_analyzer_service_http_client
from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.app.pair_strat_engine_service_helper import (
    strat_manager_service_http_client, config_yaml_dict as pair_strat_config_yaml_dict, ps_host, ps_port)
from Flux.CodeGenProjects.addressbook.ProjectGroup.post_trade_engine.app.post_trade_engine_service_helper import (
    post_trade_engine_service_http_client)
EXECUTOR_PROJECT_DIR = PurePath(__file__).parent.parent
EXECUTOR_PROJECT_DATA_DIR = EXECUTOR_PROJECT_DIR / 'data'
EXECUTOR_PROJECT_SCRIPTS_DIR = EXECUTOR_PROJECT_DIR / 'scripts'
main_config_yaml_path: PurePath = EXECUTOR_PROJECT_DATA_DIR / "config.yaml"
try:
    executor_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(main_config_yaml_path))
except FileNotFoundError as e:
    err_str = f"Can't find data/config.yaml"
    logging.exception(err_str)
    raise FileNotFoundError(err_str)

host = executor_config_yaml_dict.get("server_host")

