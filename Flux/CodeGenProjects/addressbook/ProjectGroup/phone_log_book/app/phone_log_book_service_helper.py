# project imports
from typing import Type, Callable

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_log_book.generated.ORMModel.phone_log_book_service_model_imports import *
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int, is_first_param_list_type)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_log_book.generated.FastApi.phone_log_book_service_http_client import (
    PhoneLogBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_plan_log_book.app.base_plan_log_book_service_helper import *

# standard imports
import datetime
import logging
import time
import queue
from threading import Thread, current_thread
import re
import threading

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

psla_host, psla_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))
psla_view_port = parse_to_int(config_yaml_dict.get("view_port"))

phone_log_book_service_http_view_client = \
    PhoneLogBookServiceHttpClient.set_or_get_if_instance_exists(psla_host, psla_port, view_port=psla_view_port)
phone_log_book_service_http_main_client = \
    PhoneLogBookServiceHttpClient.set_or_get_if_instance_exists(psla_host, psla_port)

if config_yaml_dict.get("use_view_clients"):
    phone_log_book_service_http_client = phone_log_book_service_http_view_client
else:
    phone_log_book_service_http_client = phone_log_book_service_http_main_client

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
contact_alert_fail_log = f"contact_alert_fail_logs_{datetime_str}.log"
simulator_contact_alert_fail_log = f"simulator_contact_alert_fail_logs_{datetime_str}.log"

# pattern to find non-existing ids of objects which were not found while patch-all
non_existing_obj_read_fail_regex_pattern: Final[str] = r".*objects with ids: \{(.*?)\} out of requested .*"


def is_phone_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            phone_log_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def is_view_phone_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            phone_log_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def get_pattern_for_pair_plan_db_updates():
    pattern = config_yaml_dict.get("pattern_for_pair_plan_db_updates")
    if pattern is None:
        pattern = "^*^"
    return pattern


def get_pattern_for_log_simulator():
    pattern = config_yaml_dict.get("pattern_for_log_simulator")
    if pattern is None:
        pattern = "$$$"
    return pattern


def get_field_seperator_pattern():
    pattern = config_yaml_dict.get("field_seperator")
    if pattern is None:
        pattern = "~~"
    return pattern


def get_pattern_for_plan_view_db_updates():
    pattern = config_yaml_dict.get("pattern_for_plan_view_db_updates")
    if pattern is None:
        pattern = "^^^"
    return pattern


def get_key_val_seperator_pattern():
    pattern = config_yaml_dict.get("key_val_seperator")
    if pattern is None:
        pattern = "^^"
    return pattern


def get_pattern_to_remove_file_from_created_cache():
    pattern = config_yaml_dict.get("pattern_to_remove_file_from_created_cache")
    if pattern is None:
        pattern = "-*-"
    return pattern


def client_call_log_str(basemodel_type: Type | None, client_callable: Callable, db_pattern: str,
                        update_type: UpdateType | None = None, **kwargs):
    if update_type is None:
        update_type = UpdateType.JOURNAL_TYPE

    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_str = (f"{db_pattern}"
               f"{basemodel_type.__name__ if basemodel_type is not None else 'basemodel_type is None'}{fld_sep}{update_type.value}"
               f"{fld_sep}{client_callable.__name__}{fld_sep}")
    for k, v in kwargs.items():
        log_str += f"{k}{val_sep}{v}"
        if k != list(kwargs)[-1]:
            log_str += fld_sep

    return log_str


def plan_view_client_call_log_str(basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    plan_view_db_pattern: str = get_pattern_for_plan_view_db_updates()
    log_str = client_call_log_str(basemodel_type, client_callable, plan_view_db_pattern, update_type, **kwargs)
    return log_str


def pair_plan_client_call_log_str(basemodel_type: Type | None, client_callable: Callable,
                                   update_type: UpdateType | None = None, **kwargs) -> str:
    pair_plan_db_pattern: str = get_pattern_for_pair_plan_db_updates()
    log_str = client_call_log_str(basemodel_type, client_callable, pair_plan_db_pattern, update_type, **kwargs)
    return log_str


def enable_disable_plan_alerts_log_str(plan_id: int, symbol_side_key_list: List[str], action: bool):
    enable_disable_start_pattern = enable_disable_log_str_start_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_str = f"{enable_disable_start_pattern}{plan_id}{val_sep}{symbol_side_key_list}{val_sep}{action}"
    return log_str


def remove_plan_alert_by_start_id_log_str(plan_id: int) -> str:
    remove_plan_alert_by_start_id_pattern_str = remove_plan_alert_by_start_id_pattern()
    return f"{remove_plan_alert_by_start_id_pattern_str}{plan_id}"

