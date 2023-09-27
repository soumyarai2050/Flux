# standard imports
from pathlib import PurePath
import logging
import os

# project imports
from Flux.CodeGenProjects.pair_strat_engine.generated.FastApi.strat_manager_service_http_client import (
    StratManagerServiceHttpClient)
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, \
    get_native_host_n_port_from_config_dict

# Current server client handling
server_port = os.environ.get("PORT")
if server_port is None or len(server_port) == 0:
    err_str = f"Env var 'PORT' received as {server_port}"
    logging.exception(err_str)
    raise Exception(err_str)

EXECUTOR_PROJECT_DIR = PurePath(__file__).parent.parent
EXECUTOR_PROJECT_DATA_DIR = EXECUTOR_PROJECT_DIR / 'data'
executor_config_yaml_path: PurePath = EXECUTOR_PROJECT_DATA_DIR / f"strat_executor_{server_port}_config.yaml"
try:
    executor_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(executor_config_yaml_path))
except FileNotFoundError as e:
    err_str = f"Can't find config file for executor with port {server_port} in data dir"
    logging.exception(err_str)
    raise FileNotFoundError(err_str)

host, port = get_native_host_n_port_from_config_dict(executor_config_yaml_dict)

strat_executor_http_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(host, port)

# pair_strat_engine client handling
pair_strat_config_yaml_path = PurePath(__file__).parent.parent.parent / "pair_strat_engine" / "data" / "config.yaml"
pair_strat_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(pair_strat_config_yaml_path))
pair_strat_port = pair_strat_config_yaml_dict.get("main_server_beanie_port")

if pair_strat_port is not None:
    pair_strat_port_config_yaml_path = (PurePath(__file__).parent.parent.parent / "pair_strat_engine" / "data" /
                                        f"pair_strat_engine_{pair_strat_port}_config.yaml")
    pair_strat_port_config_yaml_dict = (
        YAMLConfigurationManager.load_yaml_configurations(str(pair_strat_port_config_yaml_path)))
else:
    err_str = "'main_server_beanie_port' attribute not found in data/config.yaml file of pair_strat_engine"
    logging.exception(err_str)
    raise Exception(err_str)

ps_host, ps_port = get_native_host_n_port_from_config_dict(pair_strat_port_config_yaml_dict)
strat_manager_service_http_client = \
    StratManagerServiceHttpClient.set_or_get_if_instance_exists(ps_host, ps_port)