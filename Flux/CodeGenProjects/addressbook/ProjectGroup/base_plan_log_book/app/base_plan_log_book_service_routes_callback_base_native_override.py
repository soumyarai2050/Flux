# standard imports
import asyncio
import json
import logging
import multiprocessing
import time
from multiprocessing import current_process
from queue import Queue
import sys
import signal
import threading
import inspect
import ast
from pathlib import PurePath
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Set

import msgspec
# 3rd party modules
import pendulum
import setproctitle
import pendulum.parsing.exceptions

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_routes_callback_base_native_override import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_plan_log_book.app.base_plan_log_book_service_helper import *
from FluxPythonUtils.scripts.general_utility_functions import (
    find_files_with_regex, is_file_modified, get_pid_from_port, execute_tasks_list_with_all_completed, create_logger)
from Flux.PyCodeGenEngine.FluxCodeGenCore.log_analyzer_utils import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.app.contact_log_book_service_helper import contact_log_book_service_http_client
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_msgspec_routes import projection_read_http


# standard imports
from datetime import datetime

class LogNoActivityData(MsgspecBaseModel, kw_only=True):
    source_file: str
    service_name: str
    critical_duration_list: List[Tuple[DateTime | None, DateTime | None]] = field(default_factory=list)
    last_modified_timestamp: float | None = None


class PlanAlertIDCont(MsgspecBaseModel):
    plan_alert_ids: List[int]

is_view_server = os.environ.get('IS_VIEW_SERVER', False)

class BasePlanLogBookServiceRoutesCallbackBaseNativeOverride(BaseLogBookServiceRoutesCallbackBaseNativeOverride):
    plan_id_to_start_alert_obj_list_dict: Dict[int, List[int]] = {}
    underlying_read_alert_http: Callable[..., Any]
    underlying_delete_by_id_list_alert_http: Callable[..., Any]
    underlying_create_all_alert_http: Callable[..., Any]
    underlying_update_all_alert_http: Callable[..., Any]
    underlying_handle_alerts_with_symbol_side_query_http: Callable[..., Any]
    underlying_handle_alerts_with_plan_id_query_http: Callable[..., Any]
    underlying_read_alert_http_json_dict: Callable[..., Any]

    def __init__(self, plan_alert_type, config_yaml_dict, symbol_side_pattern):
        super().__init__()
        self.asyncio_loop = None
        self.plan_lvl_alert_type = plan_alert_type
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.loaded_unload_plan_list_async_rlock: AsyncRLock = AsyncRLock()
        self.loaded_plan_id_list: List[int] = []
        self.loaded_plan_id_by_symbol_side_dict: Dict[str, int] = {}
        self.plan_alert_cache_dict_by_plan_id_dict: Dict[int, Dict[str, plan_alert_type]] = {}
        self.plan_alert_queue: Queue = Queue()
        # timeout event
        self.plan_state_update_dict: Dict[int, Tuple[str, DateTime]] = {}
        self.pause_plan_trigger_dict: Dict[int, DateTime] = {}
        self.last_timeout_event_datetime: DateTime | None = None
        self.log_file_no_activity_dict: Dict[str, LogNoActivityData] = {}
        self.no_activity_timeout_secs: int | None = config_yaml_dict.get("no_activity_timeout_secs")
        self.market: Market = Market([MarketID.IN])
        self.critical_log_regex_file_names: Dict = config_yaml_dict.get("critical_log_regex_file_names")
        self.key_val_sep = get_key_val_seperator_pattern()
        self.symbol_side_pattern = symbol_side_pattern

        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.no_activity_init_timeout = config_yaml_dict.get("no_activity_init_timeout")

        if not is_view_server:
            self.contact_alert_fail_logger = create_logger("contact_alert_fail_logger", logging.DEBUG,
                                                             str(CURRENT_PROJECT_LOG_DIR), contact_alert_fail_log)

        self.pos_disable_from_plan_id_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_plan_id_log_queue_timeout_sec: int = 2
        self.pos_disable_from_symbol_side_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_symbol_side_log_queue_timeout_sec: int = 2

    def log_analyzer_periodic_timeout_handler(self):
        while True:
            current_datetime: DateTime = DateTime.utcnow()
            timeout_event_threshold: int = 10
            seconds: int = 0
            should_sleep: bool = False
            if self.last_timeout_event_datetime is not None:
                seconds = timeout_event_threshold - (current_datetime - self.last_timeout_event_datetime).seconds
                if seconds > 0:
                    should_sleep = True
                # else - no sleep required
            if should_sleep:
                time.sleep(seconds)
                continue

            # perform all timeout event checks here
            try:
                self._handle_plan_state_mismatch_timeout_breach(current_datetime)
                self._handle_plan_pause_trigger_timeout_breach(current_datetime)
            except Exception as e:
                logging.exception(f"log_analyzer_periodic_timeout_handler failed, exception: {e}")
            finally:
                self.last_timeout_event_datetime = current_datetime

    def _handle_plan_state_mismatch_timeout_breach(self, current_datetime: DateTime):
        # check timeout breach for plan state updates
        pending_updates: List[int] = []
        for plan_id, plan_state_update_tuple in self.plan_state_update_dict.items():
            _, plan_update_datetime = plan_state_update_tuple
            if (current_datetime - plan_update_datetime).seconds > 10:  # 10 sec timeout
                pending_updates.append(plan_id)
            # else not required - timeout not breached yet
        if pending_updates:
            for plan_id in pending_updates:
                self.plan_state_update_dict.pop(plan_id, None)
                err_: str = "mismatch plan state in cache"
                component_file_path: PurePath = PurePath(__file__)
                self._force_trigger_plan_pause(plan_id, err_, str(component_file_path))
        # else - no updates

    def _handle_plan_pause_trigger_timeout_breach(self, current_datetime: DateTime):
        pending_updates: List[int] = []
        for plan_id, pause_trigger_datetime in self.pause_plan_trigger_dict.items():
            if (current_datetime - pause_trigger_datetime).seconds > 20:  # 20 sec timeout
                pending_updates.append(plan_id)
            # else not required - timeout not breached yet
        if pending_updates:
            for plan_id in pending_updates:
                self.pause_plan_trigger_dict.pop(plan_id, None)
                # force kill executor
                self._force_kill_executor(plan_id)
        # else - no updates

    async def _enable_disable_plan_alert_create_query_pre(
            self, payload: List[Dict[str, Any]]):
        # Note: Patch type query as internally doing delete calls - delete type query not supported yet
        try:
            async with self.loaded_unload_plan_list_async_rlock:
                async with self.plan_lvl_alert_type.reentrant_lock:
                    for log_data in payload:
                        message: str = log_data.get("message")
                        # cleaning enable_disable_pattern_str
                        message = message[len(enable_disable_log_str_start_pattern()):]
                        data_list = message.split(self.key_val_sep)
                        plan_id: int = parse_to_int(data_list.pop(0))
                        symbol_side_key_list: List[str] = ast.literal_eval(data_list.pop(0))        # todo: symbol_side_key_list must be generic name like plan_alert_key_list
                        action: bool = True if data_list.pop(0).lower() == "true" else False

                        if action:
                            # if action is True then enabling plan alert creation for this plan id
                            if plan_id not in self.loaded_plan_id_list:
                                self.loaded_plan_id_list.append(plan_id)
                                logging.debug(f"Added {plan_id=} in self.active_plan_id_list")

                                for symbol_side_key in symbol_side_key_list:
                                    self.loaded_plan_id_by_symbol_side_dict[symbol_side_key] = plan_id
                                    logging.debug(f"Added symbol_side: {symbol_side_key} to "
                                                  f"self.plan_id_by_symbol_side_dict with {plan_id=}")
                            else:
                                logging.warning(f"{plan_id=} already exists in active_plan_id_list - "
                                                f"enable_disable_plan_alert_create_query was called to enable plan_alerts for "
                                                f"this id - verify if happened due to some bug")

                            # adding dict for plan_id
                            self.plan_alert_cache_dict_by_plan_id_dict[plan_id] = {}

                        else:
                            # if action is False then disabling plan alert creation for this plan id
                            if plan_id in self.loaded_plan_id_list:
                                self.loaded_plan_id_list.remove(plan_id)
                                logging.debug(f"Removed {plan_id=} from self.active_plan_id_list")

                                for symbol_side_key in symbol_side_key_list:
                                    self.loaded_plan_id_by_symbol_side_dict.pop(symbol_side_key, None)
                                    logging.debug(f"Removed {symbol_side_key=} from "
                                                  f"self.plan_id_by_symbol_side_dict with {plan_id=}")
                            else:
                                logging.warning(f"{plan_id=} doesn't exist in active_plan_id_list - "
                                                f"enable_disable_plan_alert_create_query was called to disable plan_alerts for "
                                                f"this id - verify if happened due to some bug")

                            # getting projection model object having plan_ids as list, if no object is passed then empty
                            # list is passed
                            plan_alert_id_cont: PlanAlertIDCont | List = (
                                await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.
                                underlying_read_alert_http(get_projection_plan_alert_id_by_plan_id(plan_id),
                                                                 projection_read_http, PlanAlertIDCont))

                            if plan_alert_id_cont:
                                await (BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.
                                       underlying_delete_by_id_list_alert_http(plan_alert_id_cont.plan_alert_ids))

                            self.plan_alert_cache_dict_by_plan_id_dict.pop(plan_id, None)

                            self.handle_task_related_to_plan_lvl_alert_disable(plan_id=plan_id, )
        except Exception as e:
            logging.error(f"Error occurred while handling _enable_disable_plan_alert_create_query - {e}")

        return []

    def handle_task_related_to_plan_lvl_alert_disable(**kwargs):
        pass

    def init_no_activity_set_up(self):
        project_group_path = PurePath(__file__).parent.parent.parent
        for regex_log_file_name, regex_log_file_dict in self.critical_log_regex_file_names.items():
            if log_path:=regex_log_file_dict.get("path"):
                log_dir_path = f"{project_group_path}/{log_path}"
                matching_files = find_files_with_regex(log_dir_path, regex_log_file_name)
                for matching_file in matching_files:
                    if matching_file not in self.log_file_no_activity_dict:
                        self._update_no_activity_monitor_related_cache(matching_file, regex_log_file_dict)

    def notify_no_activity(self):
        delete_file_path_list = []
        for file_path, non_activity_data in self.log_file_no_activity_dict.items():
            if os.path.exists(file_path):
                _, last_modified_timestamp = is_file_modified(file_path, non_activity_data.last_modified_timestamp)
                non_activity_data.last_modified_timestamp = last_modified_timestamp

                current_datetime = DateTime.utcnow()

                # loops each critical range duration and if allows only if current time is found within duration
                for critical_duration in non_activity_data.critical_duration_list:
                    critical_start_time, critical_end_time = critical_duration
                    if critical_start_time is not None and critical_end_time is not None:
                        if critical_start_time < current_datetime < critical_end_time:
                            # allowing if time is between critical start and end time
                            break
                        else:
                            # avoiding if time is not between critical start and end time
                            pass
                    else:
                        if (critical_start_time is not None and
                                critical_end_time is None and
                                current_datetime < critical_start_time):
                            # avoiding if time is before critical start time and only start time is available
                            pass
                        elif (critical_end_time is not None and
                                  critical_start_time is None and
                                  current_datetime > critical_end_time):
                            # avoiding if time is after critical end time and only end time is available
                            pass
                        else:
                            # if both critical start and end times are not present then assuming
                            # everytime is critical
                            break
                else:
                    # ignoring no activity handling if out of critical time range
                    continue

                last_modified_date_time: DateTime = pendulum.from_timestamp(last_modified_timestamp, tz="UTC")
                non_activity_secs: int = int((current_datetime - last_modified_date_time).total_seconds())
                if non_activity_secs > self.no_activity_timeout_secs:
                    if non_activity_secs >= 60:
                        non_activity_mins = int(non_activity_secs / 60)
                        non_activity_period_description = f"almost {non_activity_mins} minute(s)"
                    else:
                        non_activity_period_description = f"{non_activity_secs} seconds"

                    source_file = file_path
                    service = non_activity_data.service_name

                    log_msg: str = (f"No new logs found for {service} for last "
                                    f"{non_activity_period_description} "
                                    f"{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
                                    f"{service} log file path: {source_file}")
                    log_lvl = "warning" if (self.market.is_bartering_session_not_started()) else "error"
                    self.send_contact_alert(log_msg, log_lvl, inspect.currentframe().f_lineno,
                                              source_file, PurePath(__file__).name, DateTime.now())
                # else not required: new logs are generated but filtered out
            else:
                delete_file_path_list.append(file_path)

        # deleting any case found in above iteration
        for file_path in delete_file_path_list:
            del self.log_file_no_activity_dict[file_path]

    def _force_trigger_plan_pause(self, plan_id, err_, component_file_path):
        raise NotImplementedError("_force_trigger_plan_pause must be implemented")

    def _force_kill_executor(self, plan_id: int):
        raise NotImplementedError("_force_kill_street_book must be implemented")

    def _handle_plan_state_update_mismatch(self, plan_id: int, message: str, log_file_path: str):
        plan_state_update_tuple = self.plan_state_update_dict.get(plan_id)
        if plan_state_update_tuple is None:  # new update
            logging.debug(f"received new plan state update for {plan_id=}, {message=};;;{log_file_path=}")
            self.plan_state_update_dict[plan_id] = (message, DateTime.utcnow())
            # clear force pause cache for plan if exists
            self.pause_plan_trigger_dict.pop(plan_id, None)
        else:  # update already exists
            cached_message, _ = plan_state_update_tuple
            logging.debug(f"received matched plan state update for {plan_id=}, {message=};;;{log_file_path=}")
            self.plan_state_update_dict.pop(plan_id, None)

    def update_loaded_plan_id_by_symbol_side_dict_with_loaded_plans(self):
        raise NotImplementedError("update_loaded_plan_id_by_symbol_side_dict_with_loaded_plans must be implemented")

    async def load_plan_alerts_n_update_cache(self):
        async with self.loaded_unload_plan_list_async_rlock:
            self.update_loaded_plan_id_by_symbol_side_dict_with_loaded_plans()

            plan_alerts = await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http()
            for plan_alert in plan_alerts:
                plan_alert_cache = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_alert.plan_id)
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(plan_alert)
                alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                if plan_alert_cache is None:
                    self.plan_alert_cache_dict_by_plan_id_dict[plan_alert.plan_id] = {alert_key: plan_alert}
                else:
                    plan_alert_cache[alert_key] = plan_alert

                plan_id_to_start_alert_obj_list = (
                    BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict.get(
                        plan_alert.plan_id))
                if plan_id_to_start_alert_obj_list is None:
                    BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict[
                        plan_alert.plan_id] = [plan_alert.id]
                else:
                    if plan_alert.id not in plan_id_to_start_alert_obj_list:
                        plan_id_to_start_alert_obj_list.append(plan_alert.id)
                    # else not required: avoiding duplicate entry

            # setting plan_alerts_service_ready since all cache is updated
            self.plan_alerts_service_ready = True

    def _handle_plan_alert_queue_err_handler(self, *args):
        model_obj_list = args[0]  # single unprocessed basemodel object is passed
        for model_obj in model_obj_list:
            component_file_path = None
            source_file_name = None
            line_num = None
            alert_create_date_time = None
            first_detail = None
            latest_detail = None
            if model_obj.alert_meta is not None:
                component_file_path = model_obj.alert_meta.component_file_path
                source_file_name = model_obj.alert_meta.source_file_name
                line_num = model_obj.alert_meta.line_num
                alert_create_date_time = model_obj.alert_meta.alert_create_date_time
                first_detail = model_obj.alert_meta.first_detail
                latest_detail = model_obj.alert_meta.latest_detail
            alert_detail = latest_detail if latest_detail else first_detail
            if alert_detail is None:
                alert_detail = ""

            log_msg = f"{model_obj.alert_brief};;;{alert_detail}"
            log_lvl = BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(model_obj.severity.value)
            self.send_contact_alert(log_msg, log_lvl, line_num, component_file_path, source_file_name, alert_create_date_time)

    def update_create_n_update_plan_alerts_list_for_start_id_payload(
            self, alert_class_type, log_payload: Dict, create_plan_alert_list: List,
            upload_plan_alert_list: List, plan_id_finder_method: Callable[[str, str], int]):
        message = log_payload.get("message")
        source_file = log_payload.get("source_file")
        line_num = log_payload.get("line")
        log_date_time = log_payload.get("timestamp")
        log_source_file_name = log_payload.get("file")
        level = log_payload.get("level")
        file_name_regex = log_payload.get("file_name_regex")

        # updating cache - used for no activity checks
        self.update_no_activity_monitor_related_cache(source_file)

        severity, alert_brief, alert_details = self._create_alert(message, level, source_file)
        alert_meta = get_alert_meta_obj(source_file, log_source_file_name,
                                        line_num, log_date_time, alert_details, alert_meta_type=AlertMeta)

        plan_id = plan_id_finder_method(file_name_regex, source_file)

        if self.plan_is_unloaded(plan_id, log_payload):  # sends contact alert internally
            return None

        self.create_n_update_plan_alerts_list_update(alert_class_type, plan_id, severity, alert_brief, alert_meta,
                                                      create_plan_alert_list, upload_plan_alert_list)

    def update_create_n_update_plan_alerts_list_for_symbol_side_payload(
            self, alert_class_type, log_payload: Dict, create_plan_alert_list,
            upload_plan_alert_list, get_symbol_side_set_method: Callable[[str], Set[str]]):
        message = log_payload.get("message")
        source_file = log_payload.get("source_file")
        line_num = log_payload.get("line")
        log_date_time = log_payload.get("timestamp")
        log_source_file_name = log_payload.get("file")
        level = log_payload.get("level")

        # updating cache - used for no activity checks
        self.update_no_activity_monitor_related_cache(source_file)

        log_message: str = message.replace(self.symbol_side_pattern, "")
        severity, alert_brief, alert_details = self._create_alert(log_message, level, source_file)

        alert_meta = get_alert_meta_obj(source_file, log_source_file_name,
                                        line_num, log_date_time, alert_details, alert_meta_type=AlertMeta)

        symbol_side_set = get_symbol_side_set_method(message)
        symbol_side: str = list(symbol_side_set)[0]
        plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)

        if plan_id is None:
            msg_ = (f"No plan_id found for symbol_side: {symbol_side} in loaded cache, "
                    f"sending plan alert to contact alert, orginial log msg: {message}")
            logging.error(msg_)
            self.send_contact_alert(msg_, level, line_num, source_file, log_source_file_name, log_date_time)
            return None

        if self.plan_is_unloaded(plan_id, log_payload):    # sends contact alert internally
            return None

        self.create_n_update_plan_alerts_list_update(alert_class_type, plan_id, severity, alert_brief, alert_meta,
                                                      create_plan_alert_list, upload_plan_alert_list)

    async def create_n_update_plan_alerts_from_payload_list(
            self, alert_class_type, log_payload_list: List[Dict], plan_id_finder_method: Callable[[str, str], int],
            get_symbol_side_set_method: Callable[[str], Set[str]]):
        async with self.loaded_unload_plan_list_async_rlock:
            create_plan_alert_list: List = []
            update_plan_alert_list: List = []
            for log_payload in log_payload_list:
                if "file_name_regex" in log_payload:
                    self.update_create_n_update_plan_alerts_list_for_start_id_payload(
                        alert_class_type, log_payload, create_plan_alert_list, update_plan_alert_list, plan_id_finder_method)
                else:
                    self.update_create_n_update_plan_alerts_list_for_symbol_side_payload(
                        alert_class_type, log_payload, create_plan_alert_list, update_plan_alert_list, get_symbol_side_set_method)

            if create_plan_alert_list:

                # handling create list
                try:
                    res = await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_alert_http(create_plan_alert_list)
                except HTTPException as http_e:
                    alert_queue_handler_err_handler(http_e.detail, create_plan_alert_list, self.plan_alert_queue,
                                                     self._handle_plan_alert_queue_err_handler,
                                                     BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_alert_http)
                except Exception as e:
                    alert_queue_handler_err_handler(e, create_plan_alert_list, self.plan_alert_queue, self._handle_plan_alert_queue_err_handler,
                                                     BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_alert_http)
                create_plan_alert_list.clear()  # cleaning dict to start fresh cycle

            if update_plan_alert_list:

                # handling create list
                try:
                    res = await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http(update_plan_alert_list)
                except HTTPException as http_e:
                    alert_queue_handler_err_handler(http_e.detail, update_plan_alert_list, self.plan_alert_queue,
                                                     self._handle_plan_alert_queue_err_handler,
                                                     BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http)
                except Exception as e:
                    alert_queue_handler_err_handler(e, update_plan_alert_list, self.plan_alert_queue, self._handle_plan_alert_queue_err_handler,
                                                     BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http)
                update_plan_alert_list.clear()  # cleaning dict to start fresh cycle

    def send_plan_alert(self, message: str, sev_lvl: str, line_num: int, component_path: str,
                         source_file: str, time_stamp: DateTime | None = None):
        if time_stamp is None:
            time_stamp = DateTime.now()
        log_payload = {"message": message, "source_file":component_path, "line": line_num,
                       "level": sev_lvl, "file": source_file, "timestamp": time_stamp}
        self.plan_alert_queue.put([log_payload])

    def _handle_plan_alert_queue(self, alert_class_type,
                                  plan_alert_bulk_update_timeout, plan_alert_bulk_update_counts_per_call,
                                  get_symbol_side_set_method: Callable[[str], Set[str]],
                                  plan_id_finder_method: Callable[[str, str], int]):
        oldest_entry_time: DateTime = DateTime.utcnow()
        log_payload_cache_list: List[Dict] = []
        while True:
            try:
                print(f"----- _handle_plan_alert_queue")

                remaining_timeout_secs = get_remaining_timeout_secs(log_payload_cache_list,
                                                                    plan_alert_bulk_update_timeout, oldest_entry_time)
                print(f"----- {remaining_timeout_secs=}")

                if not remaining_timeout_secs < 1:
                    try:
                        alert_payload = self.plan_alert_queue.get(timeout=remaining_timeout_secs)  # timeout based blocking call
                        print(f"----- {alert_payload=}, {self.plan_alerts_service_ready=}")

                        if alert_payload == "EXIT":
                            logging.info(f"Exiting alert_queue_handler")
                            return

                        if not self.plan_alerts_service_ready:
                            for alert_payload_item in alert_payload:
                                print("----------", alert_payload_item)
                                self.send_contact_alert(**alert_payload_item)
                        else:
                            # All good if plan_alerts_service_ready is set
                            log_payload_cache_list.extend(alert_payload)

                    except queue.Empty:
                        # since bulk update timeout limit has breached, will call update
                        pass
                    else:
                        if len(log_payload_cache_list) < plan_alert_bulk_update_counts_per_call:
                            continue
                        # else, since bulk update count limit has breached, will call update
                # since bulk update remaining timeout limit <= 0, will call update

                if not self.asyncio_loop:
                    # Exiting this function if self.asyncio_loop is removed
                    logging.info(f"Found {self.asyncio_loop=} in alert_queue_handler - Exiting while loop")
                    return

                if log_payload_cache_list:
                    run_coro = self.create_n_update_plan_alerts_from_payload_list(alert_class_type,
                                                                                   log_payload_cache_list,
                                                                                   plan_id_finder_method,
                                                                                   get_symbol_side_set_method)
                    future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                    # block for task to finish
                    try:
                        future.result()
                    except Exception as e_:
                        logging.exception(f"alert_create_n_update_using_async_submit_callable failed with exception: {e_}")
                        continue
                # else not required: avoid if timeout hits with empty queue data

                oldest_entry_time = DateTime.utcnow()
                log_payload_cache_list: List[Dict] = []
                # else not required since even after timeout no data found
            except Exception as e_:
                logging.exception(f"alert_queue_handler failed with exception: {e_}")

    def send_contact_alert(self, message: str, level: str, line: int, file: str,
                             source_file: str, timestamp: DateTime, **kwargs):
        log_payload = {"message": message, "source_file": file, "line": line,
                       "level": level, "file": source_file, "timestamp": timestamp}
        try:
            contact_log_book_service_http_client.handle_contact_alerts_query_client([log_payload])
        except Exception as e_:
            err_str = f"send_contact_alert failed with exception: {e_} ;;; {log_payload=}, {kwargs=}"
            logging.exception(err_str)


    def _create_n_update_plan_alerts_list_update(
            self, alert_class_type, create_plan_alert_list: List, upload_plan_alert_list: List,
            plan_id: int, severity_str: str, alert_brief: str, alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending plan alert with {plan_id=}, {severity_str=}, "
                      f"{alert_brief=}, {alert_meta=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity_str)
            plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
            if plan_alert_cache_dict is not None:
                create_or_update_alert(create_plan_alert_list, upload_plan_alert_list, plan_alert_cache_dict,
                                       alert_class_type, severity,
                                       alert_brief, alert_meta, plan_id=plan_id, create_alert_method=create_plan_lvl_alert)
            else:
                # happens when _send_plan_alerts is called post plan_id is cleaned from cache on delete for
                # this plan_id - expected when called from _force_trigger_plan_pause
                logging.info(f"Can't find {plan_id=} in plan_alert_cache_dict_by_plan_id_dict, likely "
                             f"_update_create_n_update_plan_alerts_list called later cache got removed for plan_id in delete operation;;; "
                             f"{self.plan_alert_cache_dict_by_plan_id_dict}")
                log_detail = alert_meta.latest_detail if alert_meta.latest_detail else alert_meta.first_detail
                log_msg = (f"{alert_brief}{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
                           f"{log_detail if log_detail else ''}")
                log_lvl = BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(Severity(severity_str))
                self.send_contact_alert(log_msg, log_lvl, alert_meta.line_num,
                                          alert_meta.component_file_path, alert_meta.source_file_name,
                                          alert_meta.alert_create_date_time)


        except Exception as e:
            err_msg: str = (f"_update_create_n_update_plan_alerts_list failed, exception: {e}, "
                            f"received {plan_id=}, {severity_str=}, {alert_brief=}")
            if alert_meta is not None:
                alert_detail = alert_meta.latest_detail if alert_meta.latest_detail else alert_meta.first_detail
                if alert_detail is not None:
                    err_msg += f"{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} original {alert_detail=}"
            logging.exception(err_msg)
            log_lvl = BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(Severity(severity_str))
            self.send_contact_alert(err_msg, log_lvl, alert_meta.line_num,
                                      alert_meta.component_file_path, alert_meta.source_file_name,
                                      alert_meta.alert_create_date_time)

    async def _dismiss_plan_alert_by_brief_str_query_pre(self, payload: Dict[str, Any]):
        plan_id: int = parse_to_int(payload.get("plan_id"))
        brief_str: str = payload.get("brief_str")

        plan_alerts: List = \
            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http(
                get_plan_alert_from_plan_id_n_alert_brief_regex(plan_id, brief_str))

        for plan_alert in plan_alerts:
            plan_alert.dismiss = True
        updated_plan_alerts = \
            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http(
                plan_alerts)
        return updated_plan_alerts

    async def _filtered_plan_alert_by_plan_id_query_pre(
            self, plan_alert_class_type, plan_id: int, limit_obj_count: int | None = None,
            filters: List[Dict[str, Any]] | None = None, sort_chore: List[Dict[str, Any]] | None = None,
            pagination: Dict[str, Any] | None = None):

        filter_sort_pagination_agg = create_cascading_multi_filter_pipeline(plan_alert_class_type, filters, sort_chore, pagination)

        sort_alerts_based_on_severity_n_last_update_analyzer_time_agg = sort_alerts_based_on_severity_n_last_update_analyzer_time(plan_id, limit_obj_count)

        agg_pipeline = {"agg": filter_sort_pagination_agg + sort_alerts_based_on_severity_n_last_update_analyzer_time_agg}
        filtered_plan_alerts = \
            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http(agg_pipeline)
        return filtered_plan_alerts

    async def _filtered_plan_alert_by_plan_id_query_ws_pre(self, alert_class_type, *args):
        if len(args) != 5:
            err_str_ = ("filtered_plan_alert_by_plan_id_query_ws_pre failed: received inappropriate *args to be "
                        f"used in agg pipeline to sort plan_alert based on severity and date_time with other args: "
                        f"filters, sort_chore and pagination - received {args=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=404)

        filter_sort_pagination_agg = create_cascading_multi_filter_pipeline(alert_class_type,
                                                                            args[2], args[3], args[4])

        sort_alerts_based_on_severity_n_last_update_analyzer_time_agg_pipeline = (
            sort_alerts_based_on_severity_n_last_update_analyzer_time(args[0], args[1]))

        final_agg_pipeline = (filter_sort_pagination_agg +
                              sort_alerts_based_on_severity_n_last_update_analyzer_time_agg_pipeline)

        return get_filtered_plan_alert_by_plan_id_query_callable(alert_class_type), final_agg_pipeline

    def trigger_self_terminate(self):
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

    async def _plan_state_update_matcher_for_symbol_side_log_query_pre(
            self, payload: List[Dict[str, Any]], get_symbol_side_set_method: Callable[[str], Set[str]]):
        for log_payload in payload:
            message = log_payload.get("message")
            source_file = log_payload.get("source_file")

            symbol_side_set = get_symbol_side_set_method(message)
            symbol_side: str = list(symbol_side_set)[0]
            plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)
            logging.info(f"found active to pause log line for {plan_id=}")

            self._handle_plan_state_update_mismatch(plan_id, message, source_file)
        return []

    async def _plan_state_update_matcher_for_plan_id_log_query_pre(
            self, payload: List[Dict[str, Any]], plan_id_finder_method: Callable[[str, str], int]):
        for log_payload in payload:
            message = log_payload.get("message")
            source_file = log_payload.get("source_file")
            file_name_regex = log_payload.get("file_name_regex")
            plan_id = plan_id_finder_method(file_name_regex, source_file)
            logging.info(f"found active to pause log line for {plan_id=}")

            self._handle_plan_state_update_mismatch(plan_id, message, source_file)
        return []

    def _update_no_activity_monitor_related_cache(self, source_file: str, file_regex_pattern_dict: Dict):
        critical_time_range_tuple_list: List[Tuple[DateTime | None, DateTime | None]] = []
        critical_time_ranges: List[Dict[str, str]] | None = file_regex_pattern_dict.get("critical_time_ranges")

        if critical_time_ranges is not None:
            for critical_time_range in critical_time_ranges:
                start_time_str = critical_time_range.get("start_time")
                critical_start_time = None
                if start_time_str and start_time_str != "None":
                    try:
                        critical_start_time = pendulum.parse(start_time_str)
                    except pendulum.parsing.exceptions.ParserError:
                        # keeping critical_start_time = None
                        pass

                end_time_str = critical_time_range.get("end_time")
                critical_end_time = None
                if end_time_str and end_time_str != "None":
                    try:
                        critical_end_time = pendulum.parse(end_time_str)
                    except pendulum.parsing.exceptions.ParserError:
                        # keeping critical_end_time = None
                        pass

                critical_time_range_tuple_list.append((critical_start_time, critical_end_time))

        service_name = get_service_name_from_component_path(source_file)
        self.log_file_no_activity_dict[source_file] = (
            LogNoActivityData.from_kwargs(source_file=source_file, service_name=service_name,
                                          critical_duration_list=critical_time_range_tuple_list))
        logging.info(f"Critical monitoring setup for {source_file=}, {service_name=}, "
                     f"{critical_time_range_tuple_list=}")

    def update_no_activity_monitor_related_cache(self, source_file: str):
        if source_file not in self.log_file_no_activity_dict:
            # verifying if this file is critical
            for file_regex_pattern, file_regex_pattern_dict in self.critical_log_regex_file_names.items():
                if re.search(file_regex_pattern, source_file):
                    self._update_no_activity_monitor_related_cache(source_file, file_regex_pattern_dict)
                    break
        # else not required: avoid no notify set-up if already got set-up

    def create_n_update_plan_alerts_list_update(
            self, alert_class_type, plan_id: int, severity: Severity, alert_brief: str, alert_meta: AlertMeta,
            create_plan_alert_list: List, upload_plan_alert_list: List):
        if plan_id is not None and severity is not None and alert_brief is not None:
            self._create_n_update_plan_alerts_list_update(alert_class_type, create_plan_alert_list, upload_plan_alert_list,
                                                           plan_id, severity, alert_brief, alert_meta)
        else:
            err_detail = alert_meta.latest_detail if alert_meta.latest_detail is not None else alert_meta.first_detail
            if err_detail is None:
                err_detail = ""
            err_msg = ("handle_plan_alerts_with_plan_id_query_pre failed - start_alert data found with "
                         f"missing data, can't create plan alert for {plan_id=}, original {alert_brief=}, "
                         f"{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
                         f"{err_detail}")
            self.send_contact_alert(err_msg, "error", alert_meta.line_num,
                                      alert_meta.component_file_path, alert_meta.source_file_name,
                                      alert_meta.alert_create_date_time)

    def plan_is_unloaded(self, plan_id: int, log_payload: Dict):
        if plan_id not in self.loaded_plan_id_list:
            # updating contact alert detail
            log_payload['message'] = (f"Plan with {plan_id=} was unloaded, sending as contact alert, "
                                      f"original log msg: {log_payload.get('message')}")
            self.send_contact_alert(**log_payload)

            return True
        return False

    def dynamic_queue_handler_err_handler(self, basemodel_type: str, update_type: UpdateType,
                                          err_obj: Exception, pending_updates):
        if isinstance(err_obj, HTTPException):
            non_existing_objs_id_list: List[str] = re.findall(non_existing_obj_read_fail_regex_pattern,
                                                              str(err_obj.detail))
            non_existing_pair_plan = []
            if non_existing_objs_id_list:

                for pending_pair_plan in pending_updates:
                    if pending_pair_plan.id in non_existing_objs_id_list:
                        non_existing_pair_plan.append(non_existing_pair_plan)
                        pending_updates.remove(pending_pair_plan)

                err_str_ = ("Found some pair_plan objects which didn't exist while patch-all was called - removing "
                            f"these objects from pending updates to ensure next updates don't fail;;; {non_existing_pair_plan=}")
                logging.warning(err_str_)
                return
            # else not required: handling this error as usual way if not of patch-all fail due to non-existing objs

        err_str_brief = (f"handle_dynamic_queue_for_patch running for basemodel_type: "
                         f"{basemodel_type} and update_type: {update_type} failed")
        err_str_detail = f"exception: {err_obj}, {pending_updates=}"
        logging.exception(f"{err_str_brief};;; {err_str_detail}")

    def _snapshot_type_callable_err_handler(self, basemodel_class_type: Type[MsgspecBaseModel], kwargs):
        err_str_brief = ("Can't find _id key in patch kwargs dict - ignoring this update in "
                         "get_update_obj_for_snapshot_type_update, "
                         f"basemodel_class_type: {basemodel_class_type.__name__}, "
                         f"{kwargs = }")
        logging.exception(f"{err_str_brief}")

    def handle_pos_disable_from_symbol_side_log_queue(self, get_symbol_side_set_method: Callable[[str], Set[str]]):
        while True:
            try:
                data_list = self.pos_disable_from_symbol_side_log_queue.get(timeout=self.pos_disable_from_symbol_side_log_queue_timeout_sec)      # event based block
            except queue.Empty:
                # Handle the empty queue condition
                continue

            # coro needs public method
            run_coro = self.handle_pos_disable_tasks_for_symbol_side_log(data_list, get_symbol_side_set_method)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_pos_disable_tasks_for_symbol_side_log failed with exception: {e}")

    async def _handle_pos_disable_from_symbol_side_log_query_pre(
            self, payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_symbol_side_query_http(payload)

        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            message_n_source_file_tuple_list.append((message, source_file))
        self.pos_disable_from_symbol_side_log_queue.put(message_n_source_file_tuple_list)
        return []

    async def dummy_pos_disable_check(self, plan_id: int):
        pass

    async def handle_pos_disable_task(self, plan_id, message):
        # Note: uncomment below function call to call dummy pos disable code - OS side not impl but used to verify impl
        await self.dummy_pos_disable_check(plan_id)
        pass

    async def handle_pos_disable_tasks_for_symbol_side_log(self, data_list: Tuple[str, str], get_symbol_side_set_method: Callable[[str], Set[str]]):

        task_list = []
        async with self.loaded_unload_plan_list_async_rlock:
            for data in data_list:
                message, source_file = data

                symbol_side_set = get_symbol_side_set_method(message)
                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")

                plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)

                if plan_id is None:
                    logging.error(f"No Loaded plan found for {symbol_side=}, can't fulfill pos disable request for "
                                  f"this symbol-side")
                    continue

                task = asyncio.create_task(self.handle_pos_disable_task(plan_id, message))
                task_list.append(task)

            await execute_tasks_list_with_all_completed(task_list)

    async def handle_pos_disable_tasks_for_plan_id_logs(self, data_list: Tuple[str, str, str], plan_id_finder_method: Callable[[str, str], int]):

        task_list = []
        for data in data_list:
            message, source_file, file_name_regex = data

            plan_id = plan_id_finder_method(file_name_regex, source_file)

            if plan_id is None:
                err_str_ = (f"Can't find plan id in {source_file=} from payload passed to "
                            f"handle_pos_disable_by_log_query - "
                            f"Can't disable positions intended to be disabled;;; "
                            f"log_message: {message}")
                logging.critical(err_str_)
                continue
            # else not required: using found plan_id

            task = asyncio.create_task(self.handle_pos_disable_task(plan_id, message))
            task_list.append(task)

        await execute_tasks_list_with_all_completed(task_list)

    def handle_pos_disable_from_plan_id_log_queue(self, plan_id_finder_method: Callable[[str, str], int]):
        while True:
            try:
                data_list = self.pos_disable_from_plan_id_log_queue.get(timeout=self.pos_disable_from_plan_id_log_queue_timeout_sec)      # event based block

            except queue.Empty:
                # Handle the empty queue condition
                continue

            # coro needs public method
            run_coro = self.handle_pos_disable_tasks_for_plan_id_logs(data_list, plan_id_finder_method)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_pos_disable_tasks failed with exception: {e}")


    async def _handle_pos_disable_from_plan_id_log_query_pre(
            self, payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_plan_id_query_http(payload)

        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            file_name_regex = log_data.get("file_name_regex")
            message_n_source_file_tuple_list.append((message, source_file, file_name_regex))
        self.pos_disable_from_plan_id_log_queue.put(message_n_source_file_tuple_list)
        return []

    async def _dismiss_all_plan_alert_by_plan_id_query_pre(self, plan_alert_class_type, plan_id: int):
        async with plan_alert_class_type.reentrant_lock:
            existing_plan_alerts: List = await (
                BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http(
                    filters=[{"column_name": "plan_id", "filtered_values": [plan_id]}]))

            for existing_plan_alert in existing_plan_alerts:
                existing_plan_alert.dismiss = True

            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http(
                existing_plan_alerts)

    async def _get_filtered_plan_alert_count_query_pre(self, plan_alert_class_type, filter_kwargs: List[Dict[str, Any]]):
        agg_pipeline = get_cascading_multi_filter_count_pipeline(plan_alert_class_type, filter_kwargs)

        filtered_doc_count_list: List[FilteredDocCount] | None = \
            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http(
                agg_pipeline, projection_read_http, FilteredDocCount)
        if filtered_doc_count_list is None:
            return []

        return filtered_doc_count_list

    def get_cascading_multi_filter_count_plan_alert_pipeline(self, plan_alert_class_type, filter_kwargs):
        agg_pipeline = get_cascading_multi_filter_count_pipeline(plan_alert_class_type, filter_kwargs)
        return agg_pipeline

    async def _get_filtered_plan_alert_count_query_ws_pre(self, *args):
        return self._get_filtered_plan_alert_count_query_ws_callable, self.get_cascading_multi_filter_count_plan_alert_pipeline

    async def _get_filtered_plan_alert_count_query_ws_callable(self, **kwargs):
        # no additional filter required
        return kwargs.get("json_obj_str")

def _handle_plan_alert_ids_list_update_for_start_id_in_filter_callable(
        plan_alert_obj_json: Dict, plan_id: int, plan_id_to_start_alert_obj_list_dict: Dict, res_json_list: List):
    if plan_alert_obj_json.get('plan_id') == plan_id:
        res_json_list.append(plan_alert_obj_json)

        # creating entry for start_alert id for this start_id if start_id matches - useful when delete is
        # called since delete only has _id in plan_alert_obj_json_str
        plan_alert_ids_list_for_start_id: List = plan_id_to_start_alert_obj_list_dict.get(plan_id)
        obj_id = plan_alert_obj_json.get('_id')
        if plan_alert_ids_list_for_start_id is None:
            plan_id_to_start_alert_obj_list_dict[plan_id] = [obj_id]
        else:
            if obj_id not in plan_alert_ids_list_for_start_id:
                plan_alert_ids_list_for_start_id.append(obj_id)
            # else not required: avoiding duplicate entry
    else:
        # checking if it is delete call and if _id obj this obj is present in
        # plan_alert_ids_list_for_start_id in kwargs registered at create publish_ws call
        if ['_id'] == list(plan_alert_obj_json.keys()):
            # delete case
            obj_id = plan_alert_obj_json.get('_id')
            plan_alert_ids_list_for_start_id = plan_id_to_start_alert_obj_list_dict.get(plan_id)
            if plan_alert_ids_list_for_start_id and obj_id in plan_alert_ids_list_for_start_id:
                plan_alert_ids_list_for_start_id.remove(obj_id)
                res_json_list.append(plan_alert_obj_json)
            # else not required: plan_obj is not of this plan_id
        # else not required: mismatched start_id case - not this ws' plan_id

def get_filtered_plan_alert_by_plan_id_query_callable(alert_class_type):
    async def filtered_plan_alert_by_plan_id_query_callable(**kwargs):
        plan_alert_obj_json_str = kwargs.get("json_obj_str")
        obj_id_or_list = kwargs.get("obj_id_or_list")

        plan_id: int = kwargs.get('plan_id')
        if plan_id is None:
            err_str_ = ("filtered_plan_alert_by_plan_id_query_callable failed: received inappropriate **kwargs to be "
                        f"used to compare plan_alert_json_obj in ws broadcast - received {plan_alert_obj_json_str=}, "
                        f"{kwargs=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=404)

        filters = kwargs.get('filters')
        sort_chore = kwargs.get('sort_chore')
        projection = kwargs.get('projection')
        filter_sort_pagination_agg_pipeline = create_cascading_multi_filter_pipeline(alert_class_type, filters, sort_chore, projection)

        # adding match for plan id to filter first
        filter_sort_pagination_agg_pipeline.insert(0, {"$match": {"plan_id": plan_id}})
        is_single_obj = False
        if isinstance(obj_id_or_list, int):
            is_single_obj = True
            obj_id_or_list = [obj_id_or_list]
        filter_sort_pagination_agg_pipeline.insert(0, get_match_layer_for_obj_id_list(obj_id_or_list))

        agg_pipeline = {"agg": filter_sort_pagination_agg_pipeline}
        filtered_plan_alert_obj_dict_list: List[Dict] = await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http_json_dict(agg_pipeline)

        res_json_list = []
        for plan_alert_obj_json in filtered_plan_alert_obj_dict_list:
            _handle_plan_alert_ids_list_update_for_start_id_in_filter_callable(
                plan_alert_obj_json, plan_id,
                BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict, res_json_list)
        if res_json_list:
            if is_single_obj:
                return orjson.dumps(res_json_list[0], default=non_jsonable_types_handler).decode("utf-8")
            else:
                return orjson.dumps(res_json_list, default=non_jsonable_types_handler).decode("utf-8")
        return None
    return filtered_plan_alert_by_plan_id_query_callable

