# standard imports
from pathlib import PurePath
import logging

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_client import (
    EmailBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_client import (
    LogBookServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import log_book_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client, config_yaml_dict as pair_strat_config_yaml_dict, ps_host, ps_port)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_barter_engine.app.post_barter_engine_service_helper import (
    post_barter_engine_service_http_client)
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

