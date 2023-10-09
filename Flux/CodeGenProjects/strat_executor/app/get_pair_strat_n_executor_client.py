# standard imports
from pathlib import PurePath
import logging
import os

# project imports
from Flux.CodeGenProjects.pair_strat_engine.generated.FastApi.strat_manager_service_http_client import (
    StratManagerServiceHttpClient)
from Flux.CodeGenProjects.log_analyzer.generated.FastApi.log_analyzer_service_http_client import (
    LogAnalyzerServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int

EXECUTOR_PROJECT_DIR = PurePath(__file__).parent.parent
EXECUTOR_PROJECT_DATA_DIR = EXECUTOR_PROJECT_DIR / 'data'
main_config_yaml_path: PurePath = EXECUTOR_PROJECT_DATA_DIR / "config.yaml"
try:
    main_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(main_config_yaml_path))
except FileNotFoundError as e:
    err_str = f"Can't find data/config.yaml"
    logging.exception(err_str)
    raise FileNotFoundError(err_str)

host = main_config_yaml_dict.get("server_host")

# pair_strat_engine client handling
pair_strat_config_yaml_path = PurePath(__file__).parent.parent.parent / "pair_strat_engine" / "data" / "config.yaml"
pair_strat_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(pair_strat_config_yaml_path))
pair_strat_port = pair_strat_config_yaml_dict.get("main_server_beanie_port")
ps_host, ps_port = pair_strat_config_yaml_dict.get("server_host"), parse_to_int(pair_strat_port)
strat_manager_service_http_client = \
    StratManagerServiceHttpClient.set_or_get_if_instance_exists(ps_host, ps_port)

# log_analyzer client handling
log_analyzer_config_yaml_path = PurePath(__file__).parent.parent.parent / "log_analyzer" / "data" / "config.yaml"
log_analyzer_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(log_analyzer_config_yaml_path))
log_analyzer_port = log_analyzer_config_yaml_dict.get("main_server_beanie_port")

la_host, la_port = log_analyzer_config_yaml_dict.get("server_host"), parse_to_int(log_analyzer_port)
log_analyzer_service_http_client = \
    LogAnalyzerServiceHttpClient.set_or_get_if_instance_exists(la_host, la_port)
