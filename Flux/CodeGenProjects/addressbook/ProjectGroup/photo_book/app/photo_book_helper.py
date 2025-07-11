from pathlib import PurePath

from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import *
# from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_http_client import (
#     PhotoBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.FastApi.photo_book_service_http_client_async import (
    PhotoBookServiceHttpClient)
from FluxPythonUtils.scripts.general_utility_functions import YAMLConfigurationManager, parse_to_int


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

sv_host, sv_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))
sv_view_port = parse_to_int(config_yaml_dict.get("view_port"))

photo_book_service_http_view_client = \
    PhotoBookServiceHttpClient.set_or_get_if_instance_exists(sv_host, sv_port, view_port=sv_view_port)
photo_book_service_http_main_client = \
    PhotoBookServiceHttpClient.set_or_get_if_instance_exists(sv_host, sv_port)

if config_yaml_dict.get("use_view_clients"):
    photo_book_service_http_client = photo_book_service_http_view_client
else:
    photo_book_service_http_client = photo_book_service_http_main_client

def is_photo_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            photo_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_photo_book_service_up test failed - tried "
                              f"get_all_ui_layout_client;;; exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False

def is_photo_book_view_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            photo_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_photo_book_service_up test failed - tried "
                              f"get_all_ui_layout_client;;; exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False
