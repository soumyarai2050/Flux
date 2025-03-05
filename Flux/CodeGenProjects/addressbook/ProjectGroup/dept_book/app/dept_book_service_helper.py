# standard import
from pathlib import PurePath

# project imports
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_http_client import DeptBookServiceHttpClient


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
dsb_host, dsb_port = (config_yaml_dict.get("server_host"),
                      parse_to_int(config_yaml_dict.get("main_server_beanie_port")))
dashboard_service_http_client = DeptBookServiceHttpClient(dsb_host, dsb_port)


def is_all_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            dashboard_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of dashboard project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False
