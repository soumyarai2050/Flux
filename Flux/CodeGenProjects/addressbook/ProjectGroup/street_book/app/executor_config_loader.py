# standard imports
from pathlib import PurePath
import logging

# project imports
from FluxPythonUtils.scripts.file_n_general_utility_functions import YAMLConfigurationManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    config_yaml_dict as pair_plan_config_yaml_dict)

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

