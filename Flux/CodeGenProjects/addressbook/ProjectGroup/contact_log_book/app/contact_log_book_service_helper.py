# project imports
from typing import Type, Callable

from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.ORMModel.contact_log_book_service_model_imports import *
from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.FastApi.contact_log_book_service_http_client import (
    ContactLogBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_helper import *

# standard imports
import datetime
import logging

CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(config_yaml_path))

pla_host, pla_port = config_yaml_dict.get("server_host"), parse_to_int(config_yaml_dict.get("main_server_beanie_port"))
pla_view_port = parse_to_int(config_yaml_dict.get("view_port"))

contact_log_book_service_http_view_client = \
    ContactLogBookServiceHttpClient.set_or_get_if_instance_exists(pla_host, pla_port, view_port=pla_view_port)
contact_log_book_service_http_main_client = \
    ContactLogBookServiceHttpClient.set_or_get_if_instance_exists(pla_host, pla_port)

if config_yaml_dict.get("use_view_clients"):
    contact_log_book_service_http_client = contact_log_book_service_http_view_client
else:
    contact_log_book_service_http_client = contact_log_book_service_http_main_client

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
contact_alert_fail_log = f"contact_alert_fail_logs_{datetime_str}.log"
simulator_contact_alert_fail_log = f"simulator_contact_alert_fail_logs_{datetime_str}.log"


def create_contact_alert(
        alert_type: Type[ContactAlert],
        alert_brief: str, severity: Severity = Severity.Severity_ERROR,
        alert_meta: AlertMeta | None = None, **kwargs) -> ContactAlert:
    """
    Handles plan alerts if plan id is passed else handles contact alerts
    """
    alert_kwargs = {}
    alert_kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False,
                  last_update_analyzer_time=DateTime.utcnow(), alert_count=1)
    if alert_meta:
        alert_kwargs['alert_meta'] = alert_meta

    contact_alert = alert_type.from_dict(alert_kwargs)
    if hasattr(alert_type, "next_id"):
        # used in server process since db is initialized in that process -
        # putting id so that object can be cached with id - to avoid put http with cached obj without id
        contact_alert.id = alert_type.next_id()
    return contact_alert


def is_contact_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            contact_log_book_service_http_main_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def is_view_contact_log_book_service_up(ignore_error: bool = False) -> bool:
    try:
        ui_layout_list: List[UILayoutBaseModel] = (
            contact_log_book_service_http_view_client.get_all_ui_layout_client())

        return True
    except Exception as _e:
        if not ignore_error:
            logging.exception("is_executor_service_up test failed - tried "
                              "get_all_ui_layout_client ;;;"
                              f"exception: {_e}", exc_info=True)
        # else not required - silently ignore error is true
        return False


def init_service(contact_alerts_cache: Dict[str, ContactAlertBaseModel]) -> bool:
    if is_contact_log_book_service_up(ignore_error=True):
        try:
            # block for task to finish
            contact_alert_list: List[ContactAlertBaseModel] = (
                contact_log_book_service_http_client.get_all_contact_alert_client())  # returns list - empty or with objs

        except Exception as e:
            err_str_ = f"get_all_contact_alert_client failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

        for contact_alert in contact_alert_list:
            component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
            alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                            component_file_path, source_file_name, line_num)
            contact_alerts_cache[alert_key] = contact_alert
        return True
    return False
