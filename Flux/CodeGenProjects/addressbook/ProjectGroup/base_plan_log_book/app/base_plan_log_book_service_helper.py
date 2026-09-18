# standard imports
import datetime
import logging
import time
import queue
from threading import Thread, current_thread
import re
import threading
from pathlib import PurePath

# project imports
from typing import Type, Callable

from FluxPythonUtils.scripts.general_utility_functions import (
    YAMLConfigurationManager, parse_to_int, is_first_param_list_type)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_msgspec_model import *


CURRENT_PROJECT_DIR = PurePath(__file__).parent.parent
CURRENT_PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'
CURRENT_PROJECT_LOG_DIR = PurePath(__file__).parent.parent / "log"

datetime_str = datetime.datetime.now().strftime("%Y%m%d")
contact_alert_fail_log = f"contact_alert_fail_logs_{datetime_str}.log"

base_plan_log_config_yaml_path: PurePath = CURRENT_PROJECT_DATA_DIR / f"config.yaml"
base_plan_log_config_yaml_dict = YAMLConfigurationManager.load_yaml_configurations(str(base_plan_log_config_yaml_path))


def create_plan_lvl_alert(
        alert_type, alert_brief: str, severity: Severity = Severity.Severity_ERROR, plan_id: int | None = None,
        alert_meta: AlertMeta | None = None, **kwargs):
    """
    Handles plan alerts if plan id is passed else handles contact alerts
    """
    alert_kwargs = {}
    alert_kwargs.update(severity=severity, alert_brief=alert_brief, dismiss=False,
                  last_update_analyzer_time=DateTime.utcnow(), alert_count=1)
    if alert_meta:
        alert_kwargs['alert_meta'] = alert_meta
    alert_kwargs["plan_id"] = plan_id
    print(f"create_plan_lvl_alert -- {alert_kwargs=}")
    start_alert = alert_type.from_dict(alert_kwargs)
    if hasattr(alert_type, "next_id"):
        # used in server process since db is initialized in that process -
        # putting id so that object can be cached with id - to avoid put http with cached obj without id
        start_alert.id = alert_type.next_id()
    return start_alert


def get_key_val_seperator_pattern():
    pattern = base_plan_log_config_yaml_dict.get("key_val_seperator")
    if pattern is None:
        pattern = "^^"
    return pattern

def update_plan_alert_cache(
        plan_id: int, plan_alert_cache_by_plan_id_dict,
        filter_query_callable: Callable[..., Any]) -> None:
    if plan_id not in plan_alert_cache_by_plan_id_dict:
        try:
            # block for task to finish
            plan_alert_list = filter_query_callable(plan_id)
        except Exception as e:
            err_str_ = f"{filter_query_callable.__name__} failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            plan_alert_cache_by_plan_id_dict[plan_id] = {}
            for plan_alert in plan_alert_list:
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(plan_alert)
                alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                plan_alert_cache_by_plan_id_dict[plan_id][alert_key] = plan_alert


def handle_patch_db_queue_updater(
        update_type: str, model_type_name_to_patch_queue_cache_dict: Dict[str, queue.Queue],
        basemodel_type_name: str, method_name: str, update_data,
        ledger_type_handler_callable: Callable, snapshot_type_handler_callable: Callable,
        update_handler_callable: Callable, error_handler_callable: Callable,
        max_fetch_from_queue: int, snapshot_type_callable_err_handler: Callable,
        parse_to_model: bool | None = None):
    if update_type in UpdateType.__members__:
        update_type: UpdateType = UpdateType(update_type)

        update_cache_dict = model_type_name_to_patch_queue_cache_dict

        patch_queue = update_cache_dict.get(basemodel_type_name)

        if patch_queue is None:
            patch_queue = queue.Queue()

            Thread(target=handle_dynamic_queue_for_patch_n_patch_all,
                   args=(basemodel_type_name, method_name, update_type,
                         patch_queue, ledger_type_handler_callable, snapshot_type_handler_callable,
                         update_handler_callable, error_handler_callable, max_fetch_from_queue,
                         snapshot_type_callable_err_handler, parse_to_model,),
                   name=f"{basemodel_type_name}_handler").start()
            logging.info(f"Thread Started: {basemodel_type_name}_handler")

            update_cache_dict[basemodel_type_name] = patch_queue

        patch_queue.put(update_data)
    else:
        raise Exception(f"Unsupported {update_type=} in handle_dynamic_queue_updater")


def handle_dynamic_queue_for_patch_n_patch_all(basemodel_type: str, method_name: str,
                                               update_type: UpdateType, patch_queue: queue.Queue,
                                               ledger_type_handler_callable: Callable,
                                               snapshot_type_handler_callable: Callable,
                                               update_handler_callable: Callable, error_handler_callable: Callable,
                                               max_fetch_from_queue: int,
                                               snapshot_type_callable_err_handler: Callable,
                                               parse_to_model: bool | None = None):
    try:
        basemodel_class_type: Type[MsgspecBaseModel] = eval(basemodel_type)

        is_param_list_type = is_first_param_list_type(update_handler_callable)

        pending_updates = []
        while 1:
            try:
                if update_type == UpdateType.JOURNAL_TYPE:
                    # blocking call
                    pending_updates: List[Any] | Any = (
                        ledger_type_handler_callable(basemodel_class_type, update_type, method_name, patch_queue,
                                                      max_fetch_from_queue, pending_updates, parse_to_model))

                else:  # if update_type is UpdateType.SNAPSHOT_TYPE
                    # blocking call
                    pending_updates: List[Any] | Any = (
                        snapshot_type_handler_callable(basemodel_class_type, update_type, method_name, patch_queue,
                                                       max_fetch_from_queue, snapshot_type_callable_err_handler,
                                                       pending_updates, parse_to_model))

                if pending_updates == "EXIT":
                    return

                while 1:
                    try:
                        if is_param_list_type:
                            update_handler_callable(pending_updates)
                            logging.info(f"called {update_handler_callable.__name__} with {pending_updates=} in "
                                         f"handle_dynamic_queue_for_patch_n_patch_all")
                        else:
                            for pending_update in pending_updates:
                                update_handler_callable(pending_update)
                                logging.info(f"called {update_handler_callable.__name__} with {pending_update=} in "
                                             f"handle_dynamic_queue_for_patch_n_patch_all")
                                pending_updates.remove(pending_update)     # cleaning all updates that went fine
                        # only gets cleared if client call was successful else keeps data for further updates
                        pending_updates = []
                        break
                    except Exception as e:
                        if not should_retry_due_to_server_down(e):  # stays within loop if server is down
                            logging.exception(e)
                            raise e
            except Exception as e:
                error_handler_callable(basemodel_type, update_type, e, pending_updates)
    except Exception as e:
        logging.exception(e)
        raise Exception(e)


def enable_disable_log_str_start_pattern() -> str:
    return "*^*"

def enable_disable_plan_alerts_log_str(plan_id: int, symbol_side_key_list: List[str], action: bool):
    enable_disable_start_pattern = enable_disable_log_str_start_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_str = f"{enable_disable_start_pattern}{plan_id}{val_sep}{symbol_side_key_list}{val_sep}{action}"
    return log_str


def remove_plan_alert_by_start_id_pattern() -> str:
    return "-***-"


def remove_plan_alert_by_start_id_log_str(plan_id: int) -> str:
    remove_plan_alert_by_start_id_pattern_str = remove_plan_alert_by_start_id_pattern()
    return f"{remove_plan_alert_by_start_id_pattern_str}{plan_id}"
