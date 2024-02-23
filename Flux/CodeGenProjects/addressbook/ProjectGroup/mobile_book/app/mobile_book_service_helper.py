# standard import
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.utility_functions import (
    YAMLConfigurationManager, parse_to_int)


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
md_host, md_port = (config_yaml_dict.get("server_host"),
                    parse_to_int(config_yaml_dict.get("main_server_beanie_port")))
