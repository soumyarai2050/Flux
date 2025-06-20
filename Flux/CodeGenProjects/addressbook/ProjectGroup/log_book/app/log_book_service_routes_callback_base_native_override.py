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

# 3rd party modules
import pendulum
import setproctitle
import pendulum.parsing.exceptions

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_routes_msgspec_callback import LogBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import PlanViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import PlanState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.aggregate import *
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert, create_logger, is_file_modified, handle_refresh_configurable_data_members,
    get_pid_from_port, is_process_running, parse_to_float, get_symbol_side_pattern,
    get_transaction_counts_n_timeout_from_config, find_files_with_regex, ClientError)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_view_client, photo_book_service_http_main_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import StreetBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_plan_id_from_executor_log_file_name, get_symbol_n_side_from_log_line)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import symbol_side_key, get_symbol_side_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    be_port, basket_book_service_http_view_client, basket_book_service_http_main_client)
from Flux.PyCodeGenEngine.FluxCodeGenCore.log_book_utils import *
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_msgspec_routes import watch_specific_collection_with_stream


if config_yaml_dict.get("use_view_clients"):
    basket_book_service_http_client = basket_book_service_http_view_client
    photo_book_service_http_client = photo_book_service_http_view_client
else:
    basket_book_service_http_client = basket_book_service_http_main_client
    photo_book_service_http_client = photo_book_service_http_main_client

# standard imports
from datetime import datetime

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

project_group_path = PurePath(__file__).parent.parent.parent
phone_book_log_dir: PurePath = project_group_path / "phone_book" / "log"
mobile_book_log_dir: PurePath = project_group_path / "mobile_book" / "log"
street_book_log_dir: PurePath = project_group_path / "street_book" / "log"
post_barter_log_dir: PurePath = project_group_path / "post_book" / "log"
photo_book_log_dir: PurePath = project_group_path / "photo_book" / "log"
basket_book_log_dir: PurePath = project_group_path / "basket_book" / "log"

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

contact_alert_bulk_update_counts_per_call, contact_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("contact_alert_configs")))
plan_alert_bulk_update_counts_per_call, plan_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("plan_alert_config")))

# required to avoid problems like mentioned in this url
# https://pythonspeed.com/articles/python-multiprocessing/
spawn: multiprocessing.context.SpawnContext = multiprocessing.get_context("spawn")


class PlanViewUpdateCont(MsgspecBaseModel):
    total_objects: int | None = None
    highest_priority_severity: Severity | None = None

    @staticmethod
    def convert_ts_fields_in_db_fetched_dict(dict_obj: Dict):
        return dict_obj


class PlanAlertIDCont(MsgspecBaseModel):
    plan_alert_ids: List[int]


class LogNoActivityData(MsgspecBaseModel, kw_only=True):
    source_file: str
    service_name: str
    # critical_start_time: DateTime | None = None
    # critical_end_time: DateTime | None = None
    critical_duration_list: List[Tuple[DateTime | None, DateTime | None]] = field(default_factory=list)
    last_modified_timestamp: float | None = None


is_view_server = os.environ.get('IS_VIEW_SERVER', False)

class LogBookServiceRoutesCallbackBaseNativeOverride(LogBookServiceRoutesCallback):
    log_seperator: str = ';;;'
    max_str_size_in_bytes: int = 2048
    severity_map: Dict[str, Severity] = {
        "debug": Severity.Severity_DEBUG,
        "info": Severity.Severity_INFO,
        "error": Severity.Severity_ERROR,
        "critical": Severity.Severity_CRITICAL,
        "warning": Severity.Severity_WARNING,
        "exception": Severity.Severity_ERROR
    }
    severity_to_log_lvl_map: Dict[Severity, str] = {
        Severity.Severity_DEBUG: "debug",
        Severity.Severity_INFO: "info",
        Severity.Severity_ERROR: "error",
        Severity.Severity_CRITICAL: "critical",
        Severity.Severity_WARNING: "warning"
    }
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    plan_id_to_start_alert_obj_list_dict: Dict[int, List[int]] = {}
    underlying_read_contact_alert_http: Callable[..., Any] | None = None
    underlying_create_all_contact_alert_http: Callable[..., Any] | None = None
    underlying_update_all_contact_alert_http: Callable[..., Any] | None = None
    underlying_create_all_plan_alert_http: Callable[..., Any] | None = None
    underlying_update_all_plan_alert_http: Callable[..., Any] | None = None
    underlying_read_plan_alert_http: Callable[..., Any] | None = None
    underlying_filtered_plan_alert_by_plan_id_query_http: Callable[..., Any] | None = None
    underlying_delete_plan_alert_http: Callable[..., Any] | None = None
    underlying_delete_by_id_list_plan_alert_http: Callable[..., Any] | None = None
    underlying_handle_plan_alerts_with_symbol_side_query_http: Callable[..., Any] | None = None
    underlying_handle_plan_alerts_with_plan_id_query_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.contact_alerts_service_ready = False
        self.plan_alerts_service_ready = False
        self.loaded_unload_plan_list_async_rlock: AsyncRLock = AsyncRLock()
        self.loaded_plan_id_list: List[int] = []
        self.loaded_plan_id_by_symbol_side_dict: Dict[str, int] = {}
        self.plan_alert_cache_dict_by_plan_id_dict: Dict[int, Dict[str, PlanAlert]] = {}
        self.contact_alerts_cache_dict_async_rlock: AsyncRLock = AsyncRLock()
        self.contact_alerts_id_to_obj_cache_dict: Dict[int, ContactAlert] = {}
        self.contact_alerts_cache_dict: Dict[str, ContactAlert] = {}
        self.contact_alert_queue: Queue = Queue()
        self.plan_alert_queue: Queue = Queue()
        # timeout event
        self.plan_state_update_dict: Dict[int, Tuple[str, DateTime]] = {}
        self.pause_plan_trigger_dict: Dict[int, DateTime] = {}
        self.last_timeout_event_datetime: DateTime | None = None
        self.symbol_side_pattern: str = get_symbol_side_pattern()
        self.log_file_no_activity_dict: Dict[str, LogNoActivityData] = {}
        self.no_activity_timeout_secs: int | None = config_yaml_dict.get("no_activity_timeout_secs")
        self.market: Market = Market(MarketID.IN)
        self.model_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_db_updates")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value
        self.pattern_for_pair_plan_db_updates = get_pattern_for_pair_plan_db_updates()
        self.pattern_for_log_simulator = get_pattern_for_log_simulator()
        self.field_sep = get_field_seperator_pattern()
        self.key_val_sep = get_key_val_seperator_pattern()
        self.port_to_executor_web_client: Dict[int, StreetBookServiceHttpClient] = {}
        self.critical_log_regex_file_names: Dict = config_yaml_dict.get("critical_log_regex_file_names")

        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        if not is_view_server:
            self.contact_alert_fail_logger = create_logger("contact_alert_fail_logger", logging.DEBUG,
                                                             str(CURRENT_PROJECT_LOG_DIR), contact_alert_fail_log)
        # else not required: contact fail logger is only required when creating/updating contact alerts
        self.no_activity_init_timeout = config_yaml_dict.get("no_activity_init_timeout")

        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }

        self.pos_disable_from_plan_id_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_plan_id_log_queue_timeout_sec: int = 2
        threading.Thread(target=self.handle_pos_disable_from_plan_id_log_queue, daemon=True).start()
        self.pos_disable_from_symbol_side_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_symbol_side_log_queue_timeout_sec: int = 2
        threading.Thread(target=self.handle_pos_disable_from_symbol_side_log_queue, daemon=True).start()

    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_routes_imports import (
            underlying_read_contact_alert_http, underlying_create_all_contact_alert_http,
            underlying_read_plan_alert_http, underlying_delete_by_id_list_plan_alert_http,
            underlying_update_all_contact_alert_http, underlying_create_all_plan_alert_http,
            underlying_update_all_plan_alert_http,
            underlying_filtered_plan_alert_by_plan_id_query_http, underlying_delete_plan_alert_http,
            underlying_handle_plan_alerts_with_symbol_side_query_http,
            underlying_handle_plan_alerts_with_plan_id_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http = (
            underlying_read_contact_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http = (
            underlying_create_all_contact_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http = (
            underlying_update_all_contact_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_plan_alert_http = (
            underlying_create_all_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http = (
            underlying_update_all_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http = (
            underlying_read_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_filtered_plan_alert_by_plan_id_query_http = (
            underlying_filtered_plan_alert_by_plan_id_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_alert_http = (
            underlying_delete_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_by_id_list_plan_alert_http = (
            underlying_delete_by_id_list_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_symbol_side_query_http = (
            underlying_handle_plan_alerts_with_symbol_side_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_plan_id_query_http = (
            underlying_handle_plan_alerts_with_plan_id_query_http)

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        start_up_datetime = DateTime.utcnow()
        no_activity_setup_timeout = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"log_book_{self.port}")

            if not no_activity_setup_timeout:
                if (DateTime.utcnow() - start_up_datetime).total_seconds() > self.no_activity_init_timeout:
                    no_activity_setup_timeout = True
                    logging.info("No activity setup timed-out - Starting no activity notify monitoring")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.run_queue_handler()

                        # start periodic timeout event handler daemon thread
                        Thread(target=self.log_book_periodic_timeout_handler, daemon=True).start()

                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        self.contact_alert_fail_logger.exception(
                            "Unexpected: service startup threw exception, "
                            f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                            f";;;exception: {e}")
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    if not self.contact_alerts_service_ready:
                        # updating alert cache - updates self.contact_alerts_service_ready implicitly
                        run_coro = self.load_contact_alerts_n_update_cache()
                        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                        # block to finish task
                        try:
                            future.result()
                        except Exception as e:
                            logging.exception(f"load_contact_alerts_n_update_cache failed with exception: {e}")

                    if not self.plan_alerts_service_ready:
                        # updating alert cache - updates self.plan_alerts_service_ready implicitly
                        run_coro = self.load_plan_alerts_n_update_cache()
                        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                        # block to finish task
                        try:
                            future.result()
                        except Exception as e:
                            logging.exception(f"load_plan_alerts_n_update_cache failed with exception: {e}")


                    # sending no activity notifications for log files
                    if no_activity_setup_timeout:
                        self.notify_no_activity()
                    else:
                        self.init_no_activity_set_up()

                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    @except_n_log_alert()
    def _view_app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        mongo_streamer_started = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"log_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_view_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        self.contact_alert_fail_logger.exception(
                            "Unexpected: service startup threw exception, "
                            f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                            f";;;exception: {e}")
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    if not mongo_streamer_started:
                        threading.Thread(target=self.start_mongo_streamer, daemon=True).start()
                        mongo_streamer_started = True

                    # update latest config file if any modification is made
                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    def get_generic_read_route(self):
        pass

    def app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = la_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

    def view_app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = la_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override for view service")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # Exiting all started threads
        self.plan_alert_queue.put("EXIT")
        self.contact_alert_queue.put("EXIT")
        for _, queue_ in self.model_type_name_to_patch_queue_cache_dict.items():
            queue_.put("EXIT")

        # deleting lock file for suppress alert regex
        regex_lock_file_name = config_yaml_dict.get("regex_lock_file_name")
        if regex_lock_file_name is not None:
            regex_lock_file = LOG_ANALYZER_DATA_DIR / regex_lock_file_name
            if os.path.exists(regex_lock_file):
                os.remove(regex_lock_file)
        else:
            err_str_ = "Can't find key 'regex_lock_file_name' in config dict - can't delete regex pattern lock file"
            logging.error(err_str_)

    def view_app_launch_post(self):
        logging.debug("Triggered server launch post override for view service")

    def start_mongo_streamer(self):
        run_coro = self._start_mongo_streamer()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"start_mongo_streamer failed with exception: {e}")

    def log_book_periodic_timeout_handler(self):
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
                logging.exception(f"log_book_periodic_timeout_handler failed, exception: {e}")
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
                self._force_kill_street_book(plan_id)
        # else - no updates

    async def enable_disable_plan_alert_create_query_pre(
            self, enable_disable_plan_alert_create_class_type: Type[EnableDisablePlanAlertCreate],
            payload: List[Dict[str, Any]]):
        async with self.loaded_unload_plan_list_async_rlock:
            async with PlanAlert.reentrant_lock:
                for log_data in payload:
                    message: str = log_data.get("message")
                    # cleaning enable_disable_pattern_str
                    message = message[len(enable_disable_log_str_start_pattern()):]
                    data_list = message.split(self.key_val_sep)
                    plan_id: int = parse_to_int(data_list.pop(0))
                    symbol_side_key_list: List[str] = ast.literal_eval(data_list.pop(0))
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
                            await LogBookServiceRoutesCallbackBaseNativeOverride.
                            underlying_read_plan_alert_http(get_projection_plan_alert_id_by_plan_id(plan_id),
                                                             projection_read_http, PlanAlertIDCont))

                        if plan_alert_id_cont:
                            await (LogBookServiceRoutesCallbackBaseNativeOverride.
                                   underlying_delete_by_id_list_plan_alert_http(plan_alert_id_cont.plan_alert_ids))

                        self.plan_alert_cache_dict_by_plan_id_dict.pop(plan_id, None)

                        # updating plan_view fields
                        log_str = plan_view_client_call_log_str(
                            PlanViewBaseModel, photo_book_service_http_client.patch_all_plan_view_client,
                            UpdateType.SNAPSHOT_TYPE, _id=plan_id,
                            plan_alert_aggregated_severity=Severity.Severity_UNSPECIFIED.value,
                            plan_alert_count=0)
                        payload = [{"message": log_str}]
                        photo_book_service_http_client.handle_plan_view_updates_query_client(payload)

        return []

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
                                    f"{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
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

    def _force_kill_street_book(self, plan_id: int):
        pair_plan = email_book_service_http_client.get_pair_plan_client(plan_id)
        pid = get_pid_from_port(pair_plan.port)
        if pid is not None:
            symbol_side_key_ = get_symbol_side_key([(pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                    pair_plan.pair_plan_params.plan_leg1.side),
                                                   (pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                    pair_plan.pair_plan_params.plan_leg2.side)])
            log_msg: str = (f"Triggering force kill executor for {plan_id=}, killing {pid=}, {symbol_side_key_} "
                            f"{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}{pair_plan=}")
            logging.critical(log_msg)
            component_file_path = PurePath(__file__)
            self.send_plan_alert(log_msg, "critical", inspect.currentframe().f_lineno,
                                  str(component_file_path), component_file_path.name)

            os.kill(pid, signal.SIGKILL)
        else:
            logging.exception(f"_force_kill_street_book failed, no pid found for pair_plan with {plan_id=};;;"
                              f"{pair_plan=}")

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

    def _handle_contact_alert_queue_err_handler(self, *args):
        err_str_ = f"_handle_contact_alert_queue_err_handler called, passed args: {args}"
        self.contact_alert_fail_logger.exception(err_str_)

    async def load_contact_alerts_n_update_cache(self):
        try:
            async with ContactAlert.reentrant_lock:
                contact_alerts: List[ContactAlert] = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http()
                async with self.contact_alerts_cache_dict_async_rlock:
                    for contact_alert in contact_alerts:
                        component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
                        alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                                        component_file_path, source_file_name, line_num)
                        self.contact_alerts_cache_dict[alert_key] = contact_alert
                        self.contact_alerts_id_to_obj_cache_dict[contact_alert.id] = contact_alert

                    # setting contact_alerts_service_up
                    self.contact_alerts_service_ready = True

        except Exception as e:
            err_str_ = f"load_contact_alerts_n_update_cache failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    async def load_plan_alerts_n_update_cache(self):
        async with self.loaded_unload_plan_list_async_rlock:
            try:
                loaded_plans = email_book_service_http_client.get_loaded_plans_query_client()
            except ClientError as e:
                if "requests.exceptions.ConnectionError" in str(e):
                    # returning since cache can't be updated and leaving self.plan_alerts_service_ready
                    # as False - will be checked again in next loop cycle
                    return
                else:
                    raise e

            for plan in loaded_plans:
                self.loaded_plan_id_list.append(plan.id)

                symbol_side = symbol_side_key(plan.pair_plan_params.plan_leg1.sec.sec_id,
                                              plan.pair_plan_params.plan_leg1.side)
                self.loaded_plan_id_by_symbol_side_dict[symbol_side] = plan.id
                symbol_side = symbol_side_key(plan.pair_plan_params.plan_leg2.sec.sec_id,
                                              plan.pair_plan_params.plan_leg2.side)
                self.loaded_plan_id_by_symbol_side_dict[symbol_side] = plan.id

            plan_alerts: List[
                PlanAlert] = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http()
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
                    LogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict.get(
                        plan_alert.plan_id))
                if plan_id_to_start_alert_obj_list is None:
                    LogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict[
                        plan_alert.plan_id] = [plan_alert.id]
                else:
                    if plan_alert.id not in plan_id_to_start_alert_obj_list:
                        plan_id_to_start_alert_obj_list.append(plan_alert.id)
                    # else not required: avoiding duplicate entry

            # setting plan_alerts_service_ready since all cache is updated
            self.plan_alerts_service_ready = True

    def update_create_n_update_contact_alerts_list_for_payload(
            self, log_payload: Dict, create_contact_alert_list: List[PlanAlert],
            upload_contact_alert_list: List[PlanAlert]):
        message = log_payload.get("message")
        source_file = log_payload.get("source_file")
        line_num = log_payload.get("line")
        log_date_time = log_payload.get("timestamp")
        log_source_file_name = log_payload.get("file")
        level = log_payload.get("level")

        # updating cache - used for no activity checks
        self.update_no_activity_monitor_related_cache(source_file)

        alert_brief_n_detail_lists: List[str] = (
            message.split(LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator, 1))
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])

        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        alert_meta = get_alert_meta_obj(source_file, log_source_file_name,
                                        line_num, log_date_time, alert_details, alert_meta_type=AlertMeta)
        severity: Severity = LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get(level.lower())

        if severity is not None and alert_brief is not None:
            self.update_create_n_update_contact_alert_list(create_contact_alert_list,
                                                             upload_contact_alert_list,
                                                             severity, alert_brief, alert_meta)
        else:
            err_str_ = ("handle_contact_alerts_query_pre failed - contact_alert data "
                        "found with missing data, can't create plan alert;;; "
                        f"received: {severity=}, {alert_brief=}, {alert_meta=}")
            self.contact_alert_fail_logger.error(err_str_)

    async def create_n_update_contact_alerts_from_payload_list(
            self, log_payload_list: List[Dict]):
        async with ContactAlert.reentrant_lock:
            async with self.contact_alerts_cache_dict_async_rlock:
                create_contact_alert_list: List[PlanAlert] = []
                update_contact_alert_list: List[PlanAlert] = []
                for log_payload in log_payload_list:
                    self.update_create_n_update_contact_alerts_list_for_payload(
                        log_payload, create_contact_alert_list, update_contact_alert_list)

                if create_contact_alert_list:

                    # handling create list
                    try:
                        contact_alerts_list = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http(create_contact_alert_list)
                        for contact_alert in contact_alerts_list:
                            self.contact_alerts_id_to_obj_cache_dict[contact_alert.id] = contact_alert
                    except HTTPException as http_e:
                        alert_queue_handler_err_handler(http_e.detail, create_contact_alert_list, self.contact_alert_queue,
                                                         self._handle_contact_alert_queue_err_handler,
                                                         LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http)
                    except Exception as e:
                        alert_queue_handler_err_handler(e, create_contact_alert_list, self.contact_alert_queue, self._handle_contact_alert_queue_err_handler,
                                                         LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http)
                    create_contact_alert_list.clear()  # cleaning dict to start fresh cycle

                if update_contact_alert_list:

                    # handling create list
                    try:
                        contact_alerts_list = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http(update_contact_alert_list)
                        for contact_alert in contact_alerts_list:
                            self.contact_alerts_id_to_obj_cache_dict[contact_alert.id] = contact_alert
                    except HTTPException as http_e:
                        alert_queue_handler_err_handler(http_e.detail, update_contact_alert_list, self.contact_alert_queue,
                                                         self._handle_contact_alert_queue_err_handler,
                                                         LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http)
                    except Exception as e:
                        alert_queue_handler_err_handler(e, update_contact_alert_list, self.contact_alert_queue, self._handle_contact_alert_queue_err_handler,
                                                         LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http)
                    update_contact_alert_list.clear()  # cleaning dict to start fresh cycle

    def _handle_contact_alert_queue(self):
        oldest_entry_time: DateTime = DateTime.utcnow()
        log_payload_cache_list: List[Dict] = []
        while True:
            remaining_timeout_secs = get_remaining_timeout_secs(log_payload_cache_list,
                                                                contact_alert_bulk_update_timeout, oldest_entry_time)
            if not remaining_timeout_secs < 1:
                try:
                    alert_payload = self.contact_alert_queue.get(
                        timeout=remaining_timeout_secs)  # timeout based blocking call

                    if alert_payload == "EXIT":
                        logging.info(f"Exiting alert_queue_handler")
                        return

                    if not self.contact_alerts_service_ready:
                        err_str_ = (f"contact_alerts service is not initialized yet: {alert_payload=}")
                        self.contact_alert_fail_logger.error(err_str_)
                    else:
                        # All good if contact_alerts_service_ready is set
                        log_payload_cache_list.extend(alert_payload)

                except queue.Empty:
                    # since bulk update timeout limit has breached, will call update
                    pass
                else:
                    if len(log_payload_cache_list) < contact_alert_bulk_update_counts_per_call:
                        continue
                    # else, since bulk update count limit has breached, will call update
            # since bulk update remaining timeout limit <= 0, will call update

            if not self.asyncio_loop:
                # Exiting this function if self.asyncio_loop is removed
                logging.info(f"Found {self.asyncio_loop=} in alert_queue_handler - Exiting while loop")
                return

            if log_payload_cache_list:
                run_coro = self.create_n_update_contact_alerts_from_payload_list(log_payload_cache_list)
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

    def _handle_plan_alert_queue_err_handler(self, *args):
        try:
            model_obj_list: List[PlanAlert] = args[0]  # single unprocessed basemodel object is passed
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
                log_lvl = LogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(model_obj.severity.value)
                self.send_contact_alert(log_msg, log_lvl, line_num, component_file_path, source_file_name, alert_create_date_time)

        except Exception as e:
            err_str_ = f"_handle_plan_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            self.contact_alert_fail_logger.exception(err_str_)

    def update_create_n_update_plan_alerts_list_for_start_id_payload(
            self, log_payload: Dict, create_plan_alert_list: List[PlanAlert],
            upload_plan_alert_list: List[PlanAlert]):
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

        plan_id = get_plan_id_from_executor_log_file_name(file_name_regex, source_file)

        if self.plan_is_unloaded(plan_id, log_payload):  # sends contact alert internally
            return None

        self.create_n_update_plan_alerts_list_update(plan_id, severity, alert_brief, alert_meta,
                                                      create_plan_alert_list, upload_plan_alert_list)

    def update_create_n_update_plan_alerts_list_for_symbol_side_payload(
            self, log_payload: Dict, create_plan_alert_list: List[PlanAlert],
            upload_plan_alert_list: List[PlanAlert]):
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

        symbol_side_set = get_symbol_n_side_from_log_line(message)
        symbol_side: str = list(symbol_side_set)[0]
        plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)

        if plan_id is None:
            msg_ = (f"No plan_id found for symbol_side: {symbol_side} in loaded cache, "
                    f"sending plan alert to contact alert, orginial log msg: {message}")
            self.send_contact_alert(msg_, level, line_num, source_file, log_source_file_name, log_date_time)
            return None

        if self.plan_is_unloaded(plan_id, log_payload):    # sends contact alert internally
            return None

        self.create_n_update_plan_alerts_list_update(plan_id, severity, alert_brief, alert_meta,
                                                      create_plan_alert_list, upload_plan_alert_list)

    async def create_n_update_plan_alerts_from_payload_list(
            self, log_payload_list: List[Dict]):
        async with self.loaded_unload_plan_list_async_rlock:
            create_plan_alert_list: List[PlanAlert] = []
            update_plan_alert_list: List[PlanAlert] = []
            for log_payload in log_payload_list:
                if "file_name_regex" in log_payload:
                    self.update_create_n_update_plan_alerts_list_for_start_id_payload(
                        log_payload, create_plan_alert_list, update_plan_alert_list)
                else:
                    self.update_create_n_update_plan_alerts_list_for_symbol_side_payload(
                        log_payload, create_plan_alert_list, update_plan_alert_list)

            if create_plan_alert_list:

                # handling create list
                try:
                    res = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_plan_alert_http(create_plan_alert_list)
                except HTTPException as http_e:
                    alert_queue_handler_err_handler(http_e.detail, create_plan_alert_list, self.plan_alert_queue,
                                                     self._handle_plan_alert_queue_err_handler,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_plan_alert_http)
                except Exception as e:
                    alert_queue_handler_err_handler(e, create_plan_alert_list, self.plan_alert_queue, self._handle_plan_alert_queue_err_handler,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_plan_alert_http)
                create_plan_alert_list.clear()  # cleaning dict to start fresh cycle

            if update_plan_alert_list:

                # handling create list
                try:
                    res = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http(update_plan_alert_list)
                except HTTPException as http_e:
                    alert_queue_handler_err_handler(http_e.detail, update_plan_alert_list, self.plan_alert_queue,
                                                     self._handle_plan_alert_queue_err_handler,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http)
                except Exception as e:
                    alert_queue_handler_err_handler(e, update_plan_alert_list, self.plan_alert_queue, self._handle_plan_alert_queue_err_handler,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http)
                update_plan_alert_list.clear()  # cleaning dict to start fresh cycle

    def send_plan_alert(self, message: str, sev_lvl: str, line_num: int, component_path: str,
                         source_file: str, time_stamp: DateTime | None = None):
        if time_stamp is None:
            time_stamp = DateTime.now()
        log_payload = {"message": message, "source_file":component_path, "line": line_num,
                       "level": sev_lvl, "file": source_file, "timestamp": time_stamp}
        self.plan_alert_queue.put([log_payload])

    def _handle_plan_alert_queue(self):
        oldest_entry_time: DateTime = DateTime.utcnow()
        log_payload_cache_list: List[Dict] = []
        while True:
            remaining_timeout_secs = get_remaining_timeout_secs(log_payload_cache_list,
                                                                plan_alert_bulk_update_timeout, oldest_entry_time)

            if not remaining_timeout_secs < 1:
                try:
                    alert_payload = self.plan_alert_queue.get(timeout=remaining_timeout_secs)  # timeout based blocking call

                    if alert_payload == "EXIT":
                        logging.info(f"Exiting alert_queue_handler")
                        return

                    if not self.plan_alerts_service_ready:
                        if self.contact_alerts_service_ready:
                            # sending to contact alerts if plan alerts service is not up
                            self.contact_alert_queue.put(alert_payload)
                        else:
                            # raise service unavailable 503 exception, let the caller retry
                            err_str_ = (f"plan_alerts service is not initialized yet: {alert_payload=}")
                            self.contact_alert_fail_logger.error(err_str_)
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
                run_coro = self.create_n_update_plan_alerts_from_payload_list(log_payload_cache_list)
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

    def run_queue_handler(self):
        contact_alert_handler_thread = Thread(target=self._handle_contact_alert_queue, daemon=True)
        plan_alert_handler_thread = Thread(target=self._handle_plan_alert_queue, daemon=True)
        contact_alert_handler_thread.start()
        plan_alert_handler_thread.start()

    def send_contact_alert(self, message: str, log_lvl: str, line_num: int, component_path: str,
                             source_file: str, time_stamp: DateTime):
        log_payload = {"message": message, "source_file":component_path, "line": line_num,
                       "level": log_lvl, "file": source_file, "timestamp": time_stamp}
        self.contact_alert_queue.put([log_payload])

    def update_create_n_update_contact_alert_list(
            self, create_contact_alert_list: List[PlanAlert],
            upload_contact_alert_list: List[PlanAlert], severity: str, alert_brief: str,
            alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending contact alert with {severity=}, {alert_brief=}, {alert_meta=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            create_or_update_alert(create_contact_alert_list, upload_contact_alert_list,
                                   self.contact_alerts_cache_dict,
                                   PlanAlert, ContactAlert, severity, alert_brief,
                                   alert_meta=alert_meta)
        except Exception as e:
            self.contact_alert_fail_logger.exception(
                f"update_create_n_update_contact_alert_list failed{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} exception: {e};;; "
                f"received: {severity=}, {alert_brief=}, {alert_meta=}")

    def _create_n_update_plan_alerts_list_update(
            self, create_plan_alert_list: List[PlanAlert], upload_plan_alert_list: List[PlanAlert],
            plan_id: int, severity_str: str, alert_brief: str, alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending plan alert with {plan_id=}, {severity_str=}, "
                      f"{alert_brief=}, {alert_meta=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity_str)
            plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
            if plan_alert_cache_dict is not None:
                create_or_update_alert(create_plan_alert_list, upload_plan_alert_list, plan_alert_cache_dict,
                                       PlanAlert, ContactAlert, severity,
                                       alert_brief, plan_id, alert_meta)
            else:
                # happens when _send_plan_alerts is called post plan_id is cleaned from cache on delete for
                # this plan_id - expected when called from _force_trigger_plan_pause
                logging.info(f"Can't find {plan_id=} in plan_alert_cache_dict_by_plan_id_dict, likely "
                             f"_update_create_n_update_plan_alerts_list called later cache got removed for plan_id in delete operation;;; "
                             f"{self.plan_alert_cache_dict_by_plan_id_dict}")
                log_detail = alert_meta.latest_detail if alert_meta.latest_detail else alert_meta.first_detail
                log_msg = (f"{alert_brief}{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
                           f"{log_detail if log_detail else ''}")
                log_lvl = LogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(Severity(severity_str))
                self.send_contact_alert(log_msg, log_lvl, alert_meta.line_num,
                                          alert_meta.component_file_path, alert_meta.source_file_name,
                                          alert_meta.alert_create_date_time)


        except Exception as e:
            err_msg: str = (f"_update_create_n_update_plan_alerts_list failed, exception: {e}, "
                            f"received {plan_id=}, {severity_str=}, {alert_brief=}")
            if alert_meta is not None:
                alert_detail = alert_meta.latest_detail if alert_meta.latest_detail else alert_meta.first_detail
                if alert_detail is not None:
                    err_msg += f"{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} original {alert_detail=}"
            logging.exception(err_msg)
            log_lvl = LogBookServiceRoutesCallbackBaseNativeOverride.severity_to_log_lvl_map.get(Severity(severity_str))
            self.send_contact_alert(err_msg, log_lvl, alert_meta.line_num,
                                      alert_meta.component_file_path, alert_meta.source_file_name,
                                      alert_meta.alert_create_date_time)

    async def read_all_ui_layout_pre(self):
        # Setting asyncio_loop in ui_layout_pre since it called to check current service up
        attempt_counts = 3
        for _ in range(attempt_counts):
            if not self.asyncio_loop:
                self.asyncio_loop = asyncio.get_running_loop()
                time.sleep(1)
            else:
                break
        else:
            err_str_ = (f"self.asyncio_loop couldn't set as asyncio.get_running_loop() returned None for "
                        f"{attempt_counts} attempts")
            self.contact_alert_fail_logger.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def update_all_plan_alert_pre(self, updated_plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_list

    async def update_plan_alert_pre(self, updated_plan_alert_obj: PlanAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj

    async def partial_update_plan_alert_pre(self, stored_plan_alert_obj: PlanAlert,
                                             updated_plan_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_json

    async def partial_update_all_plan_alert_pre(self, stored_plan_alert_obj_list: List[PlanAlert],
                                                 updated_plan_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_json_list

    async def create_all_plan_alert_pre(self, plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def delete_contact_alert_post(self, delete_web_response):
        async with self.contact_alerts_cache_dict_async_rlock:
            contact_alert = self.contact_alerts_id_to_obj_cache_dict.get(delete_web_response.id)
            component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
            alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                            component_file_path, source_file_name, line_num)
            self.contact_alerts_cache_dict.pop(alert_key, None)
            self.contact_alerts_id_to_obj_cache_dict.pop(delete_web_response.id)

    async def delete_all_plan_alert_post(self, delete_web_response):
        # updating plan_view fields
        photo_book_service_http_client.reset_all_plan_view_count_n_severity_query_client()

    async def verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_pre(
            self, contact_alert_id_to_obj_cache_class_type: Type[ContactAlertIdToObjCache],
            contact_alert_id: int):
        async with self.contact_alerts_cache_dict_async_rlock:
            is_id_present = contact_alert_id in self.contact_alerts_id_to_obj_cache_dict
            return [ContactAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_pre(
            self, plan_alert_cache_dict_by_plan_id_dict_class_type: Type[PlanAlertCacheDictByPlanIdDict],
            plan_id: int, plan_cache_key: str):
        is_key_present = False
        async with self.loaded_unload_plan_list_async_rlock:
            plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
            if plan_alert_cache_dict is not None:
                is_key_present = plan_cache_key in plan_alert_cache_dict
            return [PlanAlertCacheDictByPlanIdDict(is_key_present=is_key_present)]

    async def verify_contact_alerts_cache_dict_query_pre(
            self, contact_alert_cache_dict_class_type: Type[ContactAlertCacheDict], plan_cache_key: str):
        async with self.contact_alerts_cache_dict_async_rlock:
            is_key_present = plan_cache_key in self.contact_alerts_cache_dict
            return [ContactAlertCacheDict(is_key_present=is_key_present)]

    async def plan_view_update_handling(self, plan_alert_obj_list: List[PlanAlert]):
        updated_plan_id_set = set()
        for updated_plan_alert_obj in plan_alert_obj_list:
            updated_plan_id_set.add(updated_plan_alert_obj.plan_id)

        for updated_plan_id in updated_plan_id_set:
            plan_view_update_cont: PlanViewUpdateCont = \
                await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http(
                    get_total_plan_alert_count_n_highest_severity(updated_plan_id),
                    projection_read_http, PlanViewUpdateCont)

            if plan_view_update_cont:
                plan_alert_aggregated_severity = plan_view_update_cont.highest_priority_severity
                plan_alert_count = plan_view_update_cont.total_objects

                log_str = plan_view_client_call_log_str(
                    PlanViewBaseModel, photo_book_service_http_client.patch_all_plan_view_client,
                    UpdateType.SNAPSHOT_TYPE, _id=updated_plan_id,
                    plan_alert_aggregated_severity=plan_alert_aggregated_severity.value if plan_alert_aggregated_severity is not None else plan_alert_aggregated_severity,
                    plan_alert_count=plan_alert_count)
                payload = [{"message": log_str}]
                photo_book_service_http_client.handle_plan_view_updates_query_client(payload)
            # else not required: if no data is in db - no handling

    async def update_all_plan_alert_post(self, updated_plan_alert_obj_list: List[PlanAlert]):
        await self.plan_view_update_handling(updated_plan_alert_obj_list)

    async def create_all_plan_alert_post(self, plan_alert_obj_list: List[PlanAlert]):
        await self.plan_view_update_handling(plan_alert_obj_list)

    async def dismiss_plan_alert_by_brief_str_query_pre(
            self, dismiss_plan_alert_by_brief_str_class_type: Type[DismissPlanAlertByBriefStr],
            plan_id: int, brief_str: str):
        plan_alerts: List[PlanAlert] = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http(
                get_plan_alert_from_plan_id_n_alert_brief_regex(plan_id, brief_str))

        for plan_alert in plan_alerts:
            plan_alert.dismiss = True
        updated_plan_alerts = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http(
                plan_alerts)
        return updated_plan_alerts

    async def filtered_plan_alert_by_plan_id_query_pre(
            self, plan_alert_class_type: Type[PlanAlert], plan_id: int, limit_obj_count: int | None = None):
        agg_pipeline = {"agg": sort_alerts_based_on_severity_n_last_update_analyzer_time(plan_id, limit_obj_count)}
        filtered_plan_alerts = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http(agg_pipeline)
        return filtered_plan_alerts

    async def filtered_plan_alert_by_plan_id_query_ws_pre(self, *args):
        if len(args) != 2:
            err_str_ = ("filtered_plan_alert_by_plan_id_query_ws_pre failed: received inappropriate *args to be "
                        f"used in agg pipeline to sort plan_alert based on severity and date_time - "
                        f"received {args=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=404)

        filter_agg_pipeline = sort_alerts_based_on_severity_n_last_update_analyzer_time(args[0], args[-1])
        return filtered_plan_alert_by_plan_id_query_callable, filter_agg_pipeline

    async def contact_alert_fail_logger_query_pre(
            self, contact_alert_fail_logger_class_type: Type[ContactAlertFailLogger], log_msg: str):
        # logs msg to contact alert fail logs - listener mails if any log is found
        self.contact_alert_fail_logger.error(log_msg)
        return []

    def trigger_self_terminate(self):
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

    async def shutdown_log_book_query_pre(self, shut_down_log_book_class_type: Type[ShutDownLogBook]):
        Thread(target=self.trigger_self_terminate, daemon=True).start()
        return []

    async def plan_state_update_matcher_for_symbol_side_log_query_pre(
            self,
            plan_state_update_matcher_for_symbol_side_log_class_type: Type[PlanStateUpdateMatcherForSymbolSideLog],
            payload: List[Dict[str, Any]]):
        for log_payload in payload:
            message = log_payload.get("message")
            source_file = log_payload.get("source_file")

            symbol_side_set = get_symbol_n_side_from_log_line(message)
            symbol_side: str = list(symbol_side_set)[0]
            plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)
            logging.info(f"found active to pause log line for {plan_id=}")

            self._handle_plan_state_update_mismatch(plan_id, message, source_file)
        return []

    async def plan_state_update_matcher_for_plan_id_log_query_pre(
            self,
            plan_state_update_matcher_for_plan_id_log_class_type: Type[PlanStateUpdateMatcherForPlanIdLog],
            payload: List[Dict[str, Any]]):
        for log_payload in payload:
            message = log_payload.get("message")
            source_file = log_payload.get("source_file")
            file_name_regex = log_payload.get("file_name_regex")
            plan_id = get_plan_id_from_executor_log_file_name(file_name_regex, source_file)
            logging.info(f"found active to pause log line for {plan_id=}")

            self._handle_plan_state_update_mismatch(plan_id, message, source_file)
        return []

    async def dismiss_all_contact_alerts_query_pre(self, contact_alert_class_type: Type[ContactAlert]):
        async with ContactAlert.reentrant_lock:
            existing_contact_alerts: List[ContactAlert] = await (
                LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http())

            for existing_contact in existing_contact_alerts:
                existing_contact.dismiss = True

            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http(
                existing_contact_alerts)

    def _get_executor_http_client_from_pair_plan(self, port_: int, host_: str) -> StreetBookServiceHttpClient:
        executor_web_client = self.port_to_executor_web_client.get(port_)
        if executor_web_client is None:
            executor_web_client = (
                StreetBookServiceHttpClient.set_or_get_if_instance_exists(host_, port_))
            self.port_to_executor_web_client[port_] = executor_web_client
        return executor_web_client

    async def handle_simulate_log_query_pre(self, handle_simulate_log_class_type: Type[HandleSimulateLog],
                                            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")

            # remove pattern_for_log_simulator from beginning of message
            message: str = message[len(self.pattern_for_log_simulator):]
            args: List[str] = message.split(self.field_sep)
            method_name: str = args.pop(0)
            host: str = args.pop(0)
            port: int = parse_to_int(args.pop(0))

            kwargs: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split(self.key_val_sep)
                kwargs[key] = value

            if port == be_port:
                executor_client = basket_book_service_http_client
            else:
                executor_client = self._get_executor_http_client_from_pair_plan(port, host)
            callback_method = getattr(executor_client, method_name)
            callback_method(**kwargs)
            logging.info(f"Called {method_name} with kwargs: {kwargs}")
        return []

    def _is_str_limit_breached(self, text: str) -> bool:
        if len(text.encode("utf-8")) > LogBookServiceRoutesCallbackBaseNativeOverride.max_str_size_in_bytes:
            return True
        return False

    def _truncate_str(self, text: str) -> str:
        if self._is_str_limit_breached(text):
            text = text.encode("utf-8")[:LogBookServiceRoutesCallbackBaseNativeOverride.max_str_size_in_bytes].decode()
            text += f"...check the component file to see the entire log"
        return text

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

    async def handle_contact_alerts_query_pre(self, handle_contact_alerts_class_type: Type[HandleContactAlerts],
                                                payload: List[Dict[str, Any]]):
        self.contact_alert_queue.put(payload)
        return []

    def _create_alert(self, message: str, level: str, source_file: str) -> Tuple[Severity, str, str]:
        alert_brief_n_detail_lists: List[str] = (
            message.split(LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator, 1))
        if len(alert_brief_n_detail_lists) == 2:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = alert_brief_n_detail_lists[1]
        else:
            alert_brief = alert_brief_n_detail_lists[0]
            alert_details = ". ".join(alert_brief_n_detail_lists[1:])

        alert_brief = self._truncate_str(alert_brief).strip()
        alert_details = self._truncate_str(alert_details).strip()
        severity: Severity = LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get(level.lower())
        return severity, alert_brief, alert_details

    def _force_trigger_plan_pause(self, pair_plan_id: int, error_event_msg: str,
                                   component_file_name: str):
        try:
            updated_pair_plan: PairPlanBaseModel = PairPlanBaseModel.from_kwargs(
                _id=pair_plan_id, plan_state=PlanState.PlanState_PAUSED)
            updated_pair_plan = email_book_service_http_client.patch_pair_plan_client(
                updated_pair_plan.to_json_dict(exclude_none=True))

            symbol_side_key_ = get_symbol_side_key([(updated_pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                     updated_pair_plan.pair_plan_params.plan_leg1.side),
                                                    (updated_pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                     updated_pair_plan.pair_plan_params.plan_leg2.side)])
            err_ = f"Force paused {pair_plan_id=}, {symbol_side_key_}, {error_event_msg}"
            logging.critical(err_)

            self.send_plan_alert(err_, "critical", inspect.currentframe().f_lineno,
                                  str(component_file_name), PurePath(__file__).name)
        except Exception as e:
            err_msg: str = (f"force_trigger_plan_pause failed for {pair_plan_id=}, {error_event_msg=}"
                            f"{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} exception: {e}")
            self.send_contact_alert(err_msg, "critical", inspect.currentframe().f_lineno,
                                      str(component_file_name), PurePath(__file__).name, DateTime.utcnow())

    def create_n_update_plan_alerts_list_update(
            self, plan_id: int, severity: Severity, alert_brief: str, alert_meta: AlertMeta,
            create_plan_alert_list: List[PlanAlert], upload_plan_alert_list: List[PlanAlert]):
        if plan_id is not None and severity is not None and alert_brief is not None:
            self._create_n_update_plan_alerts_list_update(create_plan_alert_list, upload_plan_alert_list,
                                                           plan_id, severity, alert_brief, alert_meta)
        else:
            err_detail = alert_meta.latest_detail if alert_meta.latest_detail is not None else alert_meta.first_detail
            if err_detail is None:
                err_detail = ""
            err_msg = ("handle_plan_alerts_with_plan_id_query_pre failed - start_alert data found with "
                         f"missing data, can't create plan alert for {plan_id=}, original {alert_brief=}, "
                         f"{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}"
                         f"{err_detail}")
            self.send_contact_alert(err_msg, "error", alert_meta.line_num,
                                      alert_meta.component_file_path, alert_meta.source_file_name,
                                      alert_meta.alert_create_date_time)

    def plan_is_unloaded(self, plan_id: int, log_payload: Dict):
        if plan_id not in self.loaded_plan_id_list:
            # updating contact alert detail
            log_payload['message'] = (f"Plan with {plan_id=} was unloaded, sending as contact alert, "
                                      f"original log msg: {log_payload.get('message')}")
            self.contact_alert_queue.put([log_payload])
            return True
        return False

    async def handle_plan_alerts_with_plan_id_query_pre(
            self, handle_plan_alerts_with_plan_id_class_type: Type[HandlePlanAlertsWithPlanId],
            payload: List[Dict[str, Any]]):
        self.plan_alert_queue.put(payload)
        return []

    async def handle_plan_alerts_with_symbol_side_query_pre(
            self, handle_plan_alerts_with_symbol_side_class_type: Type[HandlePlanAlertsWithSymbolSide],
            payload: List[Dict[str, Any]]):
        self.plan_alert_queue.put(payload)
        return []

    def dynamic_queue_handler_err_handler(self, basemodel_type: str, update_type: UpdateType,
                                          err_obj: Exception, pending_updates: List[PlanViewBaseModel]):
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

    async def handle_pair_plan_updates_from_logs_query_pre(
            self, handle_pair_plan_updates_from_logs_class_type: Type[HandlePairPlanUpdatesFromLogs],
            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")
            message: str = message[len(self.pattern_for_pair_plan_db_updates):]
            args: List[str] = message.split(self.field_sep)
            basemodel_type_name: str = args.pop(0)
            update_type: str = args.pop(0)
            method_name: str = args.pop(0)

            update_json: Dict[str, str] = dict()
            # get method kwargs separated by key_val_sep if any
            for arg in args:
                key, value = arg.split(self.key_val_sep)
                update_json[key] = value

            method_callable = getattr(email_book_service_http_client, method_name)
            handle_patch_db_queue_updater(update_type, self.model_type_name_to_patch_queue_cache_dict,
                                          basemodel_type_name, method_name, update_json,
                                          get_update_obj_list_for_ledger_type_update,
                                          get_update_obj_for_snapshot_type_update,
                                          method_callable, self.dynamic_queue_handler_err_handler,
                                          self.max_fetch_from_queue, self._snapshot_type_callable_err_handler,
                                          parse_to_model=True)
        return []

    def handle_pos_disable_from_symbol_side_log_queue(self):
        while True:
            try:
                data_list = self.pos_disable_from_symbol_side_log_queue.get(timeout=self.pos_disable_from_symbol_side_log_queue_timeout_sec)      # event based block
            except queue.Empty:
                # Handle the empty queue condition
                continue

            # coro needs public method
            run_coro = self.handle_pos_disable_tasks_for_symbol_side_log(data_list)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_pos_disable_tasks_for_symbol_side_log failed with exception: {e}")

    async def handle_pos_disable_from_symbol_side_log_query_pre(
            self, handle_pos_disable_from_symbol_side_log_class_type: Type[HandlePosDisableFromSymbolSideLog],
            payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_symbol_side_query_http(payload)

        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            message_n_source_file_tuple_list.append((message, source_file))
        self.pos_disable_from_symbol_side_log_queue.put(message_n_source_file_tuple_list)
        return []

    async def dummy_pos_disable_check(self, plan_id: int):
        pair_plan = email_book_service_http_client.get_pair_plan_client(plan_id)
        port = pair_plan.port
        host = pair_plan.host
        executor_client = self._get_executor_http_client_from_pair_plan(port, host)

        plan_limits = executor_client.get_plan_limits_client(pair_plan.id)
        logging.info(f"{plan_limits=}")
        updated_plan_limits = executor_client.patch_plan_limits_client({"_id": plan_id,
                                                                          "max_open_chores_per_side": plan_limits.max_open_chores_per_side+1})
        logging.info(f"{updated_plan_limits=}")

    async def handle_pos_disable_task(self, plan_id, message):
        # Note: uncomment below function call to call dummy pos disable code - OS side not impl but used to verify impl
        await self.dummy_pos_disable_check(plan_id)
        pass

    async def handle_pos_disable_tasks_for_symbol_side_log(self, data_list: Tuple[str, str]):

        task_list = []
        async with self.loaded_unload_plan_list_async_rlock:
            for data in data_list:
                message, source_file = data

                symbol_side_set = get_symbol_n_side_from_log_line(message)
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

    async def handle_pos_disable_tasks_for_plan_id_logs(self, data_list: Tuple[str, str, str]):

        task_list = []
        for data in data_list:
            message, source_file, file_name_regex = data

            plan_id = get_plan_id_from_executor_log_file_name(file_name_regex, source_file)

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

    def handle_pos_disable_from_plan_id_log_queue(self):
        while True:
            try:
                data_list = self.pos_disable_from_plan_id_log_queue.get(timeout=self.pos_disable_from_plan_id_log_queue_timeout_sec)      # event based block

            except queue.Empty:
                # Handle the empty queue condition
                continue

            # coro needs public method
            run_coro = self.handle_pos_disable_tasks_for_plan_id_logs(data_list)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_pos_disable_tasks failed with exception: {e}")


    async def handle_pos_disable_from_plan_id_log_query_pre(
            self, handle_pos_disable_from_plan_id_log_class_type: Type[HandlePosDisableFromPlanIdLog],
            payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_plan_id_query_http(payload)

        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            file_name_regex = log_data.get("file_name_regex")
            message_n_source_file_tuple_list.append((message, source_file, file_name_regex))
        self.pos_disable_from_plan_id_log_queue.put(message_n_source_file_tuple_list)
        return []

    async def handle_plan_pause_from_plan_id_log_query_pre(
            self, handle_plan_pause_from_plan_id_log_class_type: Type[HandlePlanPauseFromPlanIdLog],
            payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_plan_id_query_http(payload)

        update_pair_plan_json_list = []
        plan_id_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            file_name_regex = log_data.get("file_name_regex")

            plan_id = get_plan_id_from_executor_log_file_name(file_name_regex, source_file)

            if plan_id is None:
                err_str_ = (f"Can't find plan id in {source_file=} from payload passed to "
                            f"handle_plan_pause_from_log_query - Can't pause plan intended to be paused;;; "
                            f"payload: {log_data}")
                logging.critical(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
            # else not required: using found plan_id

            msg_brief: str = message.split(";;;")[0]
            err_: str = f"pausing pattern matched for plan with {plan_id=};;;{msg_brief=}"
            logging.critical(err_)

            update_pair_plan_json = {"_id": plan_id, "plan_state": PlanState.PlanState_PAUSED}
            update_pair_plan_json_list.append(update_pair_plan_json)
            plan_id_list.append(plan_id)
        email_book_service_http_client.patch_all_pair_plan_client(update_pair_plan_json_list)
        err_ = f"Force paused {plan_id_list=}"
        logging.critical(err_)
        return []

    async def handle_plan_pause_from_symbol_side_log_query_pre(
            self, handle_plan_pause_from_symbol_side_log_class_type: Type[HandlePlanPauseFromSymbolSideLog],
            payload: List[Dict[str, Any]]):
        async with self.loaded_unload_plan_list_async_rlock:

            # Adding alert for original payload
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_symbol_side_query_http(payload)

            update_pair_plan_json_list = []
            plan_id_list = []
            for log_data in payload:
                message = log_data.get("message")

                symbol_side_set = get_symbol_n_side_from_log_line(message)
                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")

                plan_id: int | None = self.loaded_plan_id_by_symbol_side_dict.get(symbol_side)

                if plan_id is None:
                    logging.error(f"No Loaded plan found for {symbol_side=}, can't fulfill pause plan request for "
                                  f"this symbol-side")
                    continue

                msg_brief: str = message.split(";;;")[0]
                err_: str = f"pausing pattern matched for plan with {plan_id=};;;{msg_brief=}"
                logging.critical(err_)

                update_pair_plan_json = {"_id": plan_id, "plan_state": PlanState.PlanState_PAUSED}
                update_pair_plan_json_list.append(update_pair_plan_json)
            email_book_service_http_client.patch_all_pair_plan_client(update_pair_plan_json_list)
            err_ = f"Force paused {plan_id_list=}"
            logging.critical(err_)
            return []

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


async def filtered_plan_alert_by_plan_id_query_callable(plan_alert_obj_json_str: str, obj_id_or_list: int | List[int], **kwargs):
    plan_id: int = kwargs.get('plan_id')
    if plan_id is None:
        err_str_ = ("filtered_plan_alert_by_plan_id_query_callable failed: received inappropriate **kwargs to be "
                    f"used to compare plan_alert_json_obj in ws broadcast - received {plan_alert_obj_json_str=}, "
                    f"{kwargs=}")
        logging.error(err_str_)
        raise HTTPException(detail=err_str_, status_code=404)

    plan_alert_obj_json_data = json.loads(plan_alert_obj_json_str)

    if isinstance(plan_alert_obj_json_data, list):
        res_json_list = []
        for plan_alert_obj_json in plan_alert_obj_json_data:
            _handle_plan_alert_ids_list_update_for_start_id_in_filter_callable(
                plan_alert_obj_json, plan_id,
                LogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict, res_json_list)
        if res_json_list:
            return json.dumps(res_json_list)
    elif isinstance(plan_alert_obj_json_data, dict):
        res_json_list = []
        _handle_plan_alert_ids_list_update_for_start_id_in_filter_callable(
            plan_alert_obj_json_data, plan_id,
            LogBookServiceRoutesCallbackBaseNativeOverride.plan_id_to_start_alert_obj_list_dict, res_json_list)
        if res_json_list:
            return json.dumps(res_json_list[0])
    else:
        logging.error("Unsupported DataType found in filtered_plan_alert_by_plan_id_query_callable: "
                      f"{plan_alert_obj_json_str=}")

    return None


def plan_id_from_executor_log_file(file_name: str) -> int | None:
    # Using regex to extract the number
    number_pattern = re.compile(r'street_book_(\d+)_logs_\d{8}\.log')

    match = number_pattern.search(file_name)

    if match:
        extracted_number = match.group(1)
        return parse_to_int(extracted_number)
    return None


def plan_id_from_simulator_log_file(file_name: str) -> int | None:
    # Using regex to extract the number
    number_pattern = re.compile(r'log_simulator_(\d+)_logs_\d{8}\.log')

    match = number_pattern.search(file_name)

    if match:
        extracted_number = match.group(1)
        return parse_to_int(extracted_number)
    return None
