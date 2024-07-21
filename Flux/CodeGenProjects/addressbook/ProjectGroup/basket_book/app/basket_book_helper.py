from pathlib import PurePath

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_client import (
    BasketBookServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

be_host, be_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

basket_book_service_http_client = \
    BasketBookServiceHttpClient.set_or_get_if_instance_exists(be_host, be_port)


def is_all_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            email_book_service_http_client.get_all_ui_layout_client())

        ui_layout_list: List[UILayoutBaseModel] = (
            basket_book_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of phone_book and basket executor;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False
