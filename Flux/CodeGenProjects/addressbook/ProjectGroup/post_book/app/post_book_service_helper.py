from pathlib import PurePath

from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.ORMModel.post_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.FastApi.post_book_service_http_client import (
    PostBookServiceHttpClient)
from FluxPythonUtils.scripts.utility_functions import YAMLConfigurationManager, parse_to_int


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

pt_host, pt_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))

post_book_service_http_client = \
    PostBookServiceHttpClient.set_or_get_if_instance_exists(pt_host, pt_port)


def is_post_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            post_book_service_http_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_contact_manager_service_up test failed - tried "
                              f"get_all_ui_layout_client;;; exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False
