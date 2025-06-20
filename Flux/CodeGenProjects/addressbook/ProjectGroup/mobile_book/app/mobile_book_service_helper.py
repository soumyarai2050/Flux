# standard import
from pathlib import PurePath
from typing import List
import logging

# project imports
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_msgspec_model import UILayoutBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_client import MobileBookServiceHttpClient


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
md_host, md_port = (config_yaml_dict.get("server_host"),
                    parse_to_int(config_yaml_dict.get("main_server_beanie_port")))
md_view_port = parse_to_int(config_yaml_dict.get("view_port"))

mobile_book_service_http_view_client = MobileBookServiceHttpClient.set_or_get_if_instance_exists(md_host, md_port,
                                                                                            view_port=md_view_port)
mobile_book_service_http_main_client = MobileBookServiceHttpClient.set_or_get_if_instance_exists(md_host, md_port)

if config_yaml_dict.get("use_view_clients"):
    mobile_book_service_http_client = mobile_book_service_http_view_client
else:
    mobile_book_service_http_client = mobile_book_service_http_main_client

def is_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            mobile_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of dashboard project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def is_view_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            mobile_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of dashboard project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False
