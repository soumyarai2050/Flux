# standard import
from pathlib import PurePath

# 3rd party imports
import polars as pl

# project imports
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.generated.ORMModel.address_data_manager_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.generated.FastApi.address_data_manager_service_http_client import AddressDataManagerServiceHttpClient


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_SCRIPTS_DIR = PurePath(__file__).parent.parent / 'scripts'

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))
dsb_host, dsb_port = (config_yaml_dict.get("server_host"),
                      parse_to_int(config_yaml_dict.get("main_server_beanie_port")))
dsb_view_port = parse_to_int(config_yaml_dict.get("view_port"))

address_data_manager_service_http_view_client = AddressDataManagerServiceHttpClient.set_or_get_if_instance_exists(dsb_host, dsb_port, view_port=dsb_view_port)
address_data_manager_service_http_main_client = AddressDataManagerServiceHttpClient.set_or_get_if_instance_exists(dsb_host, dsb_port)

if config_yaml_dict.get("use_view_clients"):
    address_data_manager_service_http_client = address_data_manager_service_http_view_client
else:
    address_data_manager_service_http_client = address_data_manager_service_http_main_client

def is_all_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            address_data_manager_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of address_data_manager project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def is_all_view_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            address_data_manager_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_all_service_up test failed - tried "
                              f"get_all_ui_layout_client of address_data_manager project;;; "
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is trues
        return False


def get_latest_bar_data_as_df(exch_id_list: List[str] | None = None, bar_type_list: List[BarType] | None = None,
                              start_time: DateTime | None = None, end_time: DateTime | None = None) -> pd.DataFrame:
    bar_data_list: List[BarDataBaseModel] = (
        address_data_manager_service_http_client.get_latest_bar_data_query_client(exch_id_list, bar_type_list, start_time, end_time))
    json_list = []
    for bar_data in bar_data_list:
        json_list.append(bar_data.to_json_dict())
    df = pl.DataFrame(json_list)
    return df
