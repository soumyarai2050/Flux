# standard imports
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
    get_transaction_counts_n_timeout_from_config, find_files_with_regex)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import performance_benchmark_service_http_client, RawPerformanceDataBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import StreetBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_plan_id_from_executor_log_file_name, get_symbol_n_side_from_log_line)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import symbol_side_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import be_port, basket_book_service_http_client
from Flux.PyCodeGenEngine.FluxCodeGenCore.log_book_utils import *

# standard imports
from datetime import datetime

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import get_plan_key_from_pair_plan
from ProjectGroup.phone_book.generated.FastApi.email_book_service_http_msgspec_routes import \
    underlying_read_pair_plan_http

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
    critical_start_time: DateTime | None = None
    critical_end_time: DateTime | None = None
    last_modified_timestamp: float | None = None


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
    debug_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DEBUG|INFO|DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    pair_plan_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    background_log_prefix_regex_pattern: str = (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : )?(.*(?:Error|Exception|WARNING|ERROR|CRITICAL))(\s*:\s*)?")
    log_simulator_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
    perf_benchmark_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                   r"TIMING) : \[[a-zA-Z._]* : \d*] : "
    log_prefix_regex_pattern_to_callable_name_dict = {
        pair_plan_log_prefix_regex_pattern: "handle_pair_plan_matched_log_message",
        perf_benchmark_log_prefix_regex_pattern: "handle_perf_benchmark_matched_log_message"
    }
    log_prefix_regex_pattern_to_log_date_time_regex_pattern = {
        pair_plan_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})',
        perf_benchmark_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        pair_plan_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]',
        perf_benchmark_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
    }
    debug_log_prefix_regex_pattern_to_callable_name_dict = {
        debug_prefix_regex_pattern: "handle_pair_plan_matched_log_message",
        perf_benchmark_log_prefix_regex_pattern: "handle_perf_benchmark_matched_log_message"
    }
    debug_log_prefix_regex_pattern_to_log_date_time_regex_pattern = {
        debug_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})',
        perf_benchmark_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    debug_log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        debug_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]',
        perf_benchmark_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
    }
    log_perf_benchmark_pattern_to_callable_name_dict = {
        perf_benchmark_log_prefix_regex_pattern: "handle_perf_benchmark_matched_log_message"
    }
    log_perf_benchmark_pattern_to_log_date_time_regex_pattern = {
        perf_benchmark_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    log_perf_benchmark_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        perf_benchmark_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
    }
    log_simulator_prefix_regex_pattern_to_callable_name_dict = {
        log_simulator_log_prefix_regex_pattern: "handle_log_simulator_matched_log_message"
    }
    log_simulator_prefix_regex_pattern_to_log_date_time_regex_pattern = {
        log_simulator_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    log_simulator_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        log_simulator_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
    }
    background_log_prefix_regex_pattern_to_callable_name_dict = {
        background_log_prefix_regex_pattern: "handle_pair_plan_matched_log_message"
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
    underlying_plan_state_update_matcher_query_http: Callable[..., Any] | None = None
    underlying_handle_plan_alerts_with_symbol_side_query_http: Callable[..., Any] | None = None
    underlying_handle_plan_alerts_with_plan_id_query_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.plan_alert_cache_dict_by_plan_id_dict: Dict[int, Dict[str, PlanAlert]] = {}     # updates in main thread only
        self.plan_id_by_symbol_side_dict: Dict[str, int] = {}
        self.contact_alerts_cache_dict: Dict[str, ContactAlert] = {}    # updates in main thread only
        self.plan_alerts_cache_cont: AlertsCacheCont = AlertsCacheCont(name="plan")
        self.contact_alerts_cache_cont: AlertsCacheCont = AlertsCacheCont(name="contact")
        self.active_plan_id_list_mutex: threading.Lock = threading.Lock()
        self.active_plan_id_list: List[int] = []
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
        self.contact_alert_fail_logger = create_logger("contact_alert_fail_logger", logging.DEBUG,
                                                         str(CURRENT_PROJECT_LOG_DIR), contact_alert_fail_log)
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
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_msgspec_routes import (
            underlying_read_contact_alert_http, underlying_create_all_contact_alert_http,
            underlying_read_plan_alert_http, underlying_delete_by_id_list_plan_alert_http,
            underlying_update_all_contact_alert_http, underlying_create_all_plan_alert_http,
            underlying_update_all_plan_alert_http,
            underlying_filtered_plan_alert_by_plan_id_query_http, underlying_delete_plan_alert_http,
            underlying_plan_state_update_matcher_query_http,
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
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_plan_state_update_matcher_query_http = (
            underlying_plan_state_update_matcher_query_http)
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
            service_up_flag_env_var = os.environ.get(f"log_book_{la_port}")

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

                            # updating alert cache
                            run_coro = self.load_alerts_n_update_cache()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                            # block to finish task
                            try:
                                future.result()
                            except Exception as e:
                                logging.exception(f"load_alerts_n_update_cache failed with exception: {e}")

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

    async def load_alerts_n_update_cache(self):
        # updating contact alert cache
        await self.load_contact_alerts_n_update_cache()
        # updating plan alert cache
        await self.load_plan_alerts_n_update_cache()
        # loading ongoing plan's cache data
        self.load_loaded_plans_cache_data()

    def get_generic_read_route(self):
        pass

    def app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = la_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

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
        with self.active_plan_id_list_mutex:
            if action:
                if plan_id not in self.active_plan_id_list:
                    self.active_plan_id_list.append(plan_id)
                    logging.debug(f"Added {plan_id=} in self.active_plan_id_list")
            for log_data in payload:
                message: str = log_data.get("message")
                # cleaning enable_disable_pattern_str
                message = message[len(enable_disable_log_str_start_pattern()):]
                data_list = message.split(self.key_val_sep)
                plan_id: int = parse_to_int(data_list.pop(0))
                symbol_side_key_list: List[str] = ast.literal_eval(data_list.pop(0))
                action: bool = bool(data_list.pop(0))

                if action:
                    if plan_id not in self.active_plan_id_list:
                        self.active_plan_id_list.append(plan_id)
                        logging.debug(f"Added {plan_id=} in self.active_plan_id_list")

                        for symbol_side_key in symbol_side_key_list:
                            self.plan_id_by_symbol_side_dict[symbol_side_key] = plan_id
                            logging.debug(f"Added symbol_side: {symbol_side_key} to "
                                          f"self.plan_id_by_symbol_side_dict with {plan_id=}")
                    else:
                        logging.warning(f"{plan_id=} already exists in active_plan_id_list - "
                                        f"enable_disable_plan_alert_create_query was called to enable plan_alerts for "
                                        f"this id - verify if happened due to some bug")
                else:
                    if plan_id in self.active_plan_id_list:
                        self.active_plan_id_list.remove(plan_id)
                        logging.debug(f"Removed {plan_id=} from self.active_plan_id_list")

                        for symbol_side_key in symbol_side_key_list:
                            self.plan_id_by_symbol_side_dict.pop(symbol_side_key, None)
                            logging.debug(f"Removed {symbol_side_key=} from "
                                          f"self.plan_id_by_symbol_side_dict with {plan_id=}")
                    else:
                        logging.warning(f"{plan_id=} doesn't exist in active_plan_id_list - "
                                        f"enable_disable_plan_alert_create_query was called to disable plan_alerts for "
                                        f"this id - verify if happened due to some bug")
        return []

    def init_no_activity_set_up(self):
        project_group_path = PurePath(__file__).parent.parent.parent
        for regex_log_file_name, regex_log_file_dict in self.critical_log_regex_file_names.items():
            if log_path:=regex_log_file_dict.get("path"):
                log_dir_path = f"{project_group_path}/{log_path}"
                matching_files = find_files_with_regex(log_dir_path, regex_log_file_name)
                for matching_file in matching_files:
                    self._update_no_activity_monitor_related_cache(matching_file, regex_log_file_dict)


    def notify_no_activity(self):
        delete_file_path_list = []
        for file_path, non_activity_data in self.log_file_no_activity_dict.items():
            if os.path.exists(file_path):
                _, last_modified_timestamp = is_file_modified(file_path, non_activity_data.last_modified_timestamp)
                non_activity_data.last_modified_timestamp = last_modified_timestamp

                current_datetime = DateTime.utcnow()
                if non_activity_data.critical_start_time is not None and non_activity_data.critical_end_time is not None:
                    if non_activity_data.critical_start_time < current_datetime < non_activity_data.critical_end_time:
                        # allowing if time is between critical start and end time
                        pass
                    else:
                        # avoiding if time is not between critical start and end time
                        continue
                else:
                    if (non_activity_data.critical_start_time is not None and
                            non_activity_data.critical_end_time is None and
                            current_datetime < non_activity_data.critical_start_time):
                        # avoiding if time is before critical start time
                        continue
                    elif (non_activity_data.critical_end_time is not None and
                              non_activity_data.critical_start_time is None and
                              current_datetime > non_activity_data.critical_end_time):
                        # avoiding if time is after critical end time
                        continue
                    # else not required: if both critical start and end times are not present then assuming
                    # everytime is critical

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

                    alert_brief: str = (f"No new logs found for {service} for last "
                                        f"{non_activity_period_description}")
                    alert_details: str = f"{service} log file path: {source_file}"
                    alert_meta = get_alert_meta_obj(source_file, PurePath(__file__).name,
                                                    inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
                    severity = LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("warning") if (
                        self.market.is_bartering_session_not_started()) else (
                        LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("error"))
                    self.send_contact_alerts(severity, alert_brief, alert_meta)
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
            alert_brief: str = f"Triggering force kill executor for {plan_id=}, killing {pid=}"
            alert_details: str = f"{pair_plan=}"
            logging.critical(f"{alert_brief};;;{alert_details}")
            component_file_path = PurePath(__file__)
            alert_meta = get_alert_meta_obj(str(component_file_path), component_file_path.name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
            self._send_plan_alerts(
                plan_id, LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("critical"), alert_brief,
                alert_meta)
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
            contact_alerts: List[ContactAlert] = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http()
            async with self.contact_alerts_cache_cont.re_mutex:
                for contact_alert in contact_alerts:
                    component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
                    alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                                    component_file_path, source_file_name, line_num)
                    self.contact_alerts_cache_dict[alert_key] = contact_alert
                    self.contact_alerts_cache_cont.alert_id_to_obj_dict[contact_alert.id] = contact_alert

        except Exception as e:
            err_str_ = f"load_contact_alerts_n_update_cache failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    async def load_plan_alerts_n_update_cache(self):
        plan_alerts: List[PlanAlert] = await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_alert_http()
        async with self.plan_alerts_cache_cont.re_mutex:
            for plan_alert in plan_alerts:
                plan_alert_cache = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_alert.plan_id)
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(plan_alert)
                alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                if plan_alert_cache is None:
                    self.plan_alert_cache_dict_by_plan_id_dict[plan_alert.plan_id] = {alert_key: plan_alert}
                else:
                    plan_alert_cache[alert_key] = plan_alert
                self.plan_alerts_cache_cont.alert_id_to_obj_dict[plan_alert.id] = plan_alert

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

    def load_loaded_plans_cache_data(self):
        loaded_plans = email_book_service_http_client.get_loaded_plans_query_client()
        for plan in loaded_plans:
            self.active_plan_id_list.append(plan.id)

            symbol_side = symbol_side_key(plan.pair_plan_params.plan_leg1.sec.sec_id,
                                          plan.pair_plan_params.plan_leg1.side)
            self.plan_id_by_symbol_side_dict[symbol_side] = plan.id
            symbol_side = symbol_side_key(plan.pair_plan_params.plan_leg2.sec.sec_id,
                                          plan.pair_plan_params.plan_leg2.side)
            self.plan_id_by_symbol_side_dict[symbol_side] = plan.id

    async def plan_alert_create_n_update_using_async_submit_callable(
            self, alerts_cache_cont, queue_obj, err_handling_callable,
            client_connection_fail_retry_secs):
        await handle_alert_create_n_update_using_async_submit(
            alerts_cache_cont,
            LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_plan_alert_http,
            LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_plan_alert_http,
            queue_obj, err_handling_callable, PlanAlert, client_connection_fail_retry_secs)

    async def contact_alert_create_n_update_using_async_submit_callable(
            self, alerts_cache_cont, queue_obj, err_handling_callable,
            client_connection_fail_retry_secs):
        await handle_alert_create_n_update_using_async_submit(
            alerts_cache_cont,
            LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http,
            LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http,
            queue_obj, err_handling_callable, ContactAlert, client_connection_fail_retry_secs)

    def _handle_contact_alert_queue(self):
        alert_queue_handler_for_create_n_update(
            self.asyncio_loop, self.contact_alert_queue, contact_alert_bulk_update_counts_per_call,
            contact_alert_bulk_update_timeout,
            self.contact_alert_create_n_update_using_async_submit_callable,
            self._handle_contact_alert_queue_err_handler,
            self.contact_alerts_cache_cont, asyncio_loop=self.asyncio_loop)

    def _handle_plan_alert_queue_err_handler(self, *args):
        try:
            model_obj_list: List[PlanAlertBaseModel] = args[0]  # single unprocessed basemodel object is passed
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
                alert_meta = get_alert_meta_obj(component_file_path, source_file_name, line_num,
                                                alert_create_date_time, first_detail, latest_detail,
                                                alert_meta_type=AlertMeta)
                self.send_contact_alerts(model_obj.severity.value, model_obj.alert_brief, alert_meta)
        except Exception as e:
            err_str_ = f"_handle_plan_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            self.contact_alert_fail_logger.exception(err_str_)

    def _handle_plan_alert_queue(self):
        alert_queue_handler_for_create_n_update(
            self.asyncio_loop, self.plan_alert_queue, plan_alert_bulk_update_counts_per_call,
            plan_alert_bulk_update_timeout,
            self.plan_alert_create_n_update_using_async_submit_callable,
            self._handle_plan_alert_queue_err_handler,
            self.plan_alerts_cache_cont, asyncio_loop=self.asyncio_loop)

    def run_queue_handler(self):
        contact_alert_handler_thread = Thread(target=self._handle_contact_alert_queue, daemon=True)
        plan_alert_handler_thread = Thread(target=self._handle_plan_alert_queue, daemon=True)
        contact_alert_handler_thread.start()
        plan_alert_handler_thread.start()

    def send_contact_alerts(self, severity: str, alert_brief: str,
                              alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending contact alert with {severity=}, {alert_brief=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            create_or_update_alert(self.contact_alerts_cache_dict, self.contact_alert_queue,
                                   PlanAlert, ContactAlert, severity, alert_brief,
                                   alert_meta=alert_meta)
        except Exception as e:
            self.contact_alert_fail_logger.exception(
                f"send_contact_alerts failed{LogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} exception: {e};;; "
                f"received: {severity=}, {alert_brief=}, {alert_meta=}")

    def _send_plan_alerts(self, plan_id: int, severity_str: str, alert_brief: str,
                           alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending plan alert with {plan_id=}, {severity_str=}, "
                      f"{alert_brief=}, {alert_meta=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity_str)
            plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
            if plan_alert_cache_dict is not None:
                create_or_update_alert(plan_alert_cache_dict,
                                       self.plan_alert_queue, PlanAlert, ContactAlert, severity,
                                       alert_brief, plan_id, alert_meta)
            else:
                # happens when _send_plan_alerts is called post plan_id is cleaned from cache on delete for
                # this plan_id - expected when called from _force_trigger_plan_pause
                logging.info(f"Can't find {plan_id=} in plan_alert_cache_dict_by_plan_id_dict, likely "
                             f"_send_plan_alerts called later cache got removed for plan_id in delete operation;;; "
                             f"{self.plan_alert_cache_dict_by_plan_id_dict}")
                self.send_contact_alerts(severity=severity_str, alert_brief=alert_brief, alert_meta=alert_meta)

        except Exception as e:
            err_msg: str = (f"_send_plan_alerts failed, exception: {e}, "
                            f"received {plan_id=}, {severity_str=}, {alert_brief=}")
            if alert_meta is not None:
                err_msg += f", {alert_meta=}"
                alert_meta = get_alert_meta_obj(alert_meta.component_file_path, alert_meta.source_file_name,
                                                alert_meta.line_num, alert_meta.alert_create_date_time,
                                                alert_meta.first_detail, err_msg, alert_meta_type=AlertMeta)

            logging.exception(err_msg)
            self.send_contact_alerts(severity=severity_str, alert_brief=alert_brief, alert_meta=alert_meta)

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
        async with self.contact_alerts_cache_cont.re_mutex:
            contact_alert = self.contact_alerts_cache_cont.alert_id_to_obj_dict.get(delete_web_response.id)
            component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
            alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                            component_file_path, source_file_name, line_num)
            self.contact_alerts_cache_dict.pop(alert_key, None)
            self.contact_alerts_cache_cont.alert_id_to_obj_dict.pop(delete_web_response.id, None)

            # Below pops are required to avoid race_condition with alert_queue_handler_for_create_n_update
            # running for contact_alerts in separate thread
            self.contact_alerts_cache_cont.update_alert_obj_dict.pop(delete_web_response.id, None)
            self.contact_alerts_cache_cont.create_alert_obj_dict.pop(delete_web_response.id, None)

    def handle_cache_clean_up_for_plan_alert_id(self, plan_alert_id: int):
        """
        Important: caller must take self.plan_alerts_cache_cont.re_mutex lock before calling this function
        """
        plan_alert = self.plan_alerts_cache_cont.alert_id_to_obj_dict.get(plan_alert_id)
        plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_alert.plan_id)
        component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(plan_alert)
        alert_key = get_alert_cache_key(plan_alert.severity, plan_alert.alert_brief,
                                        component_file_path, source_file_name, line_num)
        if plan_alert_cache_dict:
            plan_alert_cache_dict.pop(alert_key, None)
        self.plan_alerts_cache_cont.alert_id_to_obj_dict.pop(plan_alert_id, None)

        # Below pops are required to avoid race_condition with alert_queue_handler_for_create_n_update
        # running for plan_alerts in separate thread
        self.plan_alerts_cache_cont.update_alert_obj_dict.pop(plan_alert_id, None)
        self.plan_alerts_cache_cont.create_alert_obj_dict.pop(plan_alert_id, None)

    async def delete_plan_alert_post(self, delete_web_response):
        async with self.plan_alerts_cache_cont.re_mutex:
            self.handle_cache_clean_up_for_plan_alert_id(delete_web_response.id)

    async def delete_by_id_list_plan_alert_post(self, delete_web_response):
        async with self.plan_alerts_cache_cont.re_mutex:
            for plan_alert_id in delete_web_response.id:
                self.handle_cache_clean_up_for_plan_alert_id(plan_alert_id)

    async def delete_all_plan_alert_post(self, delete_web_response):
        self.plan_alert_cache_dict_by_plan_id_dict.clear()
        async with self.plan_alerts_cache_cont.re_mutex:
            self.plan_alerts_cache_cont.alert_id_to_obj_dict.clear()

            # Below pops are required to avoid race_condition with alert_queue_handler_for_create_n_update
            # running for plan_alerts in separate thread
            self.plan_alerts_cache_cont.update_alert_obj_dict.clear()
            self.plan_alerts_cache_cont.create_alert_obj_dict.clear()

        # updating plan_view fields
        photo_book_service_http_client.reset_all_plan_view_count_n_severity_query_client()

    async def verify_plan_alert_id_in_plan_alert_id_to_obj_cache_dict_query_pre(
            self, plan_alert_id_to_obj_cache_class_type: Type[PlanAlertIdToObjCache], plan_alert_id: int):
        async with self.plan_alerts_cache_cont.re_mutex:
            is_id_present = plan_alert_id in self.plan_alerts_cache_cont.alert_id_to_obj_dict
            return [PlanAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_pre(
            self, contact_alert_id_to_obj_cache_class_type: Type[ContactAlertIdToObjCache],
            contact_alert_id: int):
        async with self.contact_alerts_cache_cont.re_mutex:
            is_id_present = contact_alert_id in self.contact_alerts_cache_cont.alert_id_to_obj_dict
            return [ContactAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_plan_id_in_plan_alert_cache_dict_by_plan_id_dict_query_pre(
            self, _: Type[PlanIdInPlanAlertCacheDictByPlanIdDict], plan_id: int):
        is_id_present = plan_id in self.plan_alert_cache_dict_by_plan_id_dict
        return [PlanIdInPlanAlertCacheDictByPlanIdDict(is_id_present=is_id_present)]

    async def verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_pre(
            self, plan_alert_cache_dict_by_plan_id_dict_class_type: Type[PlanAlertCacheDictByPlanIdDict],
            plan_id: int, plan_cache_key: str):
        is_key_present = False
        plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
        if plan_alert_cache_dict is not None:
            is_key_present = plan_cache_key in plan_alert_cache_dict
        return [PlanAlertCacheDictByPlanIdDict(is_key_present=is_key_present)]

    async def verify_contact_alerts_cache_dict_query_pre(
            self, contact_alert_cache_dict_class_type: Type[ContactAlertCacheDict], plan_cache_key: str):
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

    async def remove_plan_alerts_for_plan_id_query_pre(
            self, remove_plan_alerts_for_plan_id_class_type: Type[RemovePlanAlertsForPlanId],
            payload: List[Dict[str, Any]]):
        for payload_dict in payload:

            message = payload_dict.get("message")
            # removing the starting pattern
            message = message[len(remove_plan_alert_by_start_id_pattern()):]
            # remaining is plan_id
            plan_id: int = parse_to_int(message)

            try:
                # releasing cache for plan id
                self.plan_alert_cache_dict_by_plan_id_dict.pop(plan_id, None)

                async with PlanAlert.reentrant_lock:
                    # getting projection model object having plan_ids as list, if no object is passed then empty
                    # list is passed
                    plan_alert_id_cont: PlanAlertIDCont | List = (
                        await LogBookServiceRoutesCallbackBaseNativeOverride.
                        underlying_read_plan_alert_http(get_projection_plan_alert_id_by_plan_id(plan_id),
                                                         projection_read_http, PlanAlertIDCont))

                    if plan_alert_id_cont:
                        await (LogBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_delete_by_id_list_plan_alert_http(plan_alert_id_cont.plan_alert_ids))

                # updating plan_view fields
                log_str = plan_view_client_call_log_str(
                    PlanViewBaseModel, photo_book_service_http_client.patch_all_plan_view_client,
                    UpdateType.SNAPSHOT_TYPE, _id=plan_id,
                    plan_alert_aggregated_severity=Severity.Severity_UNSPECIFIED.value,
                    plan_alert_count=0)
                payload = [{"message": log_str}]
                photo_book_service_http_client.handle_plan_view_updates_query_client(payload)
            except Exception as e_:
                logging.exception(e_)

        return []

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

    async def plan_state_update_matcher_query_pre(
            self, plan_state_update_matcher_class_type: Type[PlanStateUpdateMatcher], plan_id: int,
            message: str, log_file_path: str):
        self._handle_plan_state_update_mismatch(plan_id, message, log_file_path)
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
        if source_file not in self.log_file_no_activity_dict:
            critical_start_time_str: str | None = file_regex_pattern_dict.get("start_time")
            critical_start_time = None
            if critical_start_time_str and critical_start_time_str != "None":
                try:
                    critical_start_time = pendulum.parse(critical_start_time_str)
                except pendulum.parsing.exceptions.ParserError:
                    # keeping critical_start_time = None
                    pass

            critical_end_time_str = file_regex_pattern_dict.get("end_time")
            critical_end_time = None
            if critical_end_time_str and critical_end_time_str != "None":
                try:
                    critical_end_time = pendulum.parse(critical_end_time_str)
                except pendulum.parsing.exceptions.ParserError:
                    # keeping critical_end_time = None
                    pass

            service_name = get_service_name_from_component_path(source_file)
            self.log_file_no_activity_dict[source_file] = (
                LogNoActivityData.from_kwargs(source_file=source_file, service_name=service_name,
                                              critical_start_time=critical_start_time,
                                              critical_end_time=critical_end_time))
            logging.info(f"Critical monitoring setup for {source_file=}, {service_name=}, "
                         f"{critical_start_time=}, {critical_end_time=}")

    def update_no_activity_monitor_related_cache(self, source_file: str):
        # verifying if this file is critical
        for file_regex_pattern, file_regex_pattern_dict in self.critical_log_regex_file_names.items():
            if re.search(file_regex_pattern, source_file):
                self._update_no_activity_monitor_related_cache(source_file, file_regex_pattern_dict)
                break

    async def handle_contact_alerts_query_pre(self, handle_contact_alerts_class_type: Type[HandleContactAlerts],
                                                payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            line_num = log_data.get("line")
            log_date_time = log_data.get("timestamp")
            log_source_file_name = log_data.get("file")
            level = log_data.get("level")

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
                self.send_contact_alerts(severity, alert_brief, alert_meta)
            else:
                err_str_ = ("handle_contact_alerts_query_pre failed - contact_alert data "
                            "found with missing data, can't create plan alert;;; "
                            f"received: {severity=}, {alert_brief=}, {alert_meta=}")
                self.contact_alert_fail_logger.error(err_str_)
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
            email_book_service_http_client.patch_pair_plan_client(
                updated_pair_plan.to_json_dict(exclude_none=True))
            err_ = f"Force paused {pair_plan_id=}, {error_event_msg}"
            logging.critical(err_)
            alert_meta = get_alert_meta_obj(component_file_name, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow())
            self._send_plan_alerts(pair_plan_id, LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("critical"),
                                    err_, alert_meta)
        except Exception as e:
            alert_brief: str = f"force_trigger_plan_pause failed for {pair_plan_id=}, {error_event_msg=}"
            alert_details: str = f"exception: {e}"
            logging.critical(f"{alert_brief};;;{alert_details}")
            alert_meta = get_alert_meta_obj(component_file_name, PurePath(__file__).name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
            self.send_contact_alerts(severity=LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("critical"),
                                       alert_brief=alert_brief, alert_meta=alert_meta)

    async def handle_msg_pattern_checks(self, message: str, plan_id: int, component_file_name: str):
        # handle plan_state update mismatch
        if "Plan state changed from PlanState_ACTIVE to PlanState_PAUSED" in message:
            logging.info(f"found active to pause log line for {plan_id=}")
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_plan_state_update_matcher_query_http(
                plan_id, message, component_file_name)

    async def _handle_plan_alerts_using_data_from_log_line(self, plan_id: int, severity: Severity,
                                                            alert_brief: str, alert_meta: AlertMeta):
        if plan_id is not None and severity is not None and alert_brief is not None:
            if plan_id not in self.plan_alert_cache_dict_by_plan_id_dict:
                # verifying if plan exists
                try:
                    pair_plan: PairPlanBaseModel = email_book_service_http_client.get_pair_plan_client(plan_id)
                except Exception as e:
                    logging.exception(f"get_pair_plan_client failed: Can't find pair_start "
                                      f"with id: {plan_id}, exception={e}")
                    self.send_contact_alerts(severity, alert_brief, alert_meta)
                else:
                    # checking if plan is not unloaded
                    plan_key = get_plan_key_from_pair_plan(pair_plan)
                    plan_collections = email_book_service_http_client.get_all_plan_collection_client()
                    plan_collection = plan_collections[0]
                    if plan_key in plan_collection.buffered_plan_keys:
                        logging.exception(f"pair_plan with {pair_plan.id=} found to be unloaded - sending alert"
                                          f"for this plan as contact alert")
                        self.send_contact_alerts(severity, alert_brief, alert_meta)
                        if pair_plan.id in self.active_plan_id_list:
                            # precautionary step: removing plan from active if not active and not removed yet
                            self.active_plan_id_list.remove(pair_plan.id)
                        # else not required: good if not already present

            await async_update_plan_alert_cache(plan_id, self.plan_alert_cache_dict_by_plan_id_dict,
                                                 LogBookServiceRoutesCallbackBaseNativeOverride.
                                                 underlying_filtered_plan_alert_by_plan_id_query_http)
            self._send_plan_alerts(plan_id, severity, alert_brief, alert_meta)
        else:
            err_severity = LogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get("error")
            err_brief = ("handle_plan_alerts_with_plan_id_query_pre failed - start_alert data found with "
                         "missing data, can't create plan alert")
            err_details = f"received: {plan_id=}, {severity=}, {alert_brief=}, {alert_meta=}"
            alert_meta = get_alert_meta_obj(alert_meta.component_file_path, alert_meta.source_file_name,
                                            alert_meta.line_num, alert_meta.alert_create_date_time,
                                            alert_meta.first_detail, err_details, alert_meta_type=AlertMeta)
            self.send_contact_alerts(err_severity, err_brief, alert_meta)

    def plan_is_unloaded(self, plan_id: int, severity: Severity, alert_brief: str, alert_meta: AlertMeta):
        if plan_id not in self.active_plan_id_list:
            logging.error(f"No plan_id found for active pair_plan {plan_id=}, "
                          f"sending plan alert to contact alert;;; {severity=}, {alert_brief=}, {alert_meta=}")
            self.send_contact_alerts(severity, alert_brief, alert_meta)
            return True
        return False

    async def handle_plan_alerts_with_plan_id_query_pre(
            self, handle_plan_alerts_with_plan_id_class_type: Type[HandlePlanAlertsWithPlanId],
            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            line_num = log_data.get("line")
            log_date_time = log_data.get("timestamp")
            log_source_file_name = log_data.get("file")
            level = log_data.get("level")
            file_name_regex = log_data.get("file_name_regex")

            # updating cache - used for no activity checks
            self.update_no_activity_monitor_related_cache(source_file)

            severity, alert_brief, alert_details = self._create_alert(message, level, source_file)
            alert_meta = get_alert_meta_obj(source_file, log_source_file_name,
                                            line_num, log_date_time, alert_details, alert_meta_type=AlertMeta)

            plan_id = get_plan_id_from_executor_log_file_name(file_name_regex, source_file)
            if self.plan_is_unloaded(plan_id, severity, alert_brief, alert_meta):    # sends contact alert internally
                continue

            # handling pause and pos_disable
            await self.handle_msg_pattern_checks(message, plan_id, source_file)

            await self._handle_plan_alerts_using_data_from_log_line(plan_id, severity, alert_brief, alert_meta)
        return []

    def _get_pair_plan_obj_from_symbol_side(self, symbol: str, side: Side) -> PairPlanBaseModel | None:
        pair_plan_list: List[PairPlanBaseModel] = \
            (email_book_service_http_client.
             get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_client(
                sec_id=symbol, side=side))

        if len(pair_plan_list) == 0:
            return None
        elif len(pair_plan_list) == 1:
            pair_plan_obj: PairPlanBaseModel = pair_plan_list[0]
            return pair_plan_obj

    async def handle_plan_alerts_with_symbol_side_query_pre(
            self, handle_plan_alerts_with_symbol_side_class_type: Type[HandlePlanAlertsWithSymbolSide],
            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            line_num = log_data.get("line")
            log_date_time = log_data.get("timestamp")
            log_source_file_name = log_data.get("file")
            level = log_data.get("level")

            # updating cache - used for no activity checks
            self.update_no_activity_monitor_related_cache(source_file)

            log_message: str = message.replace(self.symbol_side_pattern, "")
            severity, alert_brief, alert_details = self._create_alert(log_message, level, source_file)

            alert_meta = get_alert_meta_obj(source_file, log_source_file_name,
                                            line_num, log_date_time, alert_details, alert_meta_type=AlertMeta)

            symbol_side_set = get_symbol_n_side_from_log_line(message)
            symbol_side: str = list(symbol_side_set)[0]
            plan_id: int | None = self.plan_id_by_symbol_side_dict.get(symbol_side)

            if plan_id is None:
                logging.error(f"No plan_id found for symbol_side: {symbol_side} in self.plan_id_by_symbol_side_dict, "
                              f"sending plan alert to contact alert;;; {severity=}, {alert_brief=}, {alert_meta=}")
                self.send_contact_alerts(severity, alert_brief, alert_meta)
                continue

            if self.plan_is_unloaded(plan_id, severity, alert_brief, alert_meta):    # sends contact alert internally
                continue

            # handling pause and pos_disable
            await self.handle_msg_pattern_checks(message, plan_id, source_file)

            await self._handle_plan_alerts_using_data_from_log_line(plan_id, severity, alert_brief, alert_meta)
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
                                          get_update_obj_list_for_journal_type_update,
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
            plan_id_n_msg_tuple_list: List[Tuple[int, str]] = []
            for data in data_list:
                message, source_file = data

                symbol_side_set = get_symbol_n_side_from_log_line(message)
                symbol_side: str = list(symbol_side_set)[0]
                symbol, side = symbol_side.split("-")

                plan_id: int | None = self.plan_id_by_symbol_side_dict.get(symbol_side)

                if plan_id is None:
                    pair_plan_obj: PairPlanBaseModel = self._get_pair_plan_obj_from_symbol_side(symbol, Side(side))
                    if pair_plan_obj is None:
                        raise HTTPException(detail=f"No Ongoing pair plan found for symbol_side: {symbol_side}",
                                            status_code=400)

                    plan_id = pair_plan_obj.id
                    for symbol_side in symbol_side_set:
                        self.plan_id_by_symbol_side_dict[symbol_side] = plan_id

                plan_id_n_msg_tuple_list.append((plan_id, message))

            if plan_id_n_msg_tuple_list:
                # coro needs public method
                run_coro = self.handle_pos_disable_tasks(plan_id_n_msg_tuple_list)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                # block for task to finish
                try:
                    future.result()
                except Exception as e:
                    logging.exception(f"handle_pos_disable_tasks failed with exception: {e}")

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

    async def handle_pos_disable_tasks(self, plan_id_n_msg_tuple_list: List[Tuple[int, str]]):
        task_list = []
        for plan_id_n_msg_tuple in plan_id_n_msg_tuple_list:
            plan_id, msg = plan_id_n_msg_tuple

            task = asyncio.create_task(self.handle_pos_disable_task(plan_id, msg))
            task_list.append(task)

        await execute_tasks_list_with_all_completed(task_list)

    def handle_pos_disable_from_plan_id_log_queue(self):
        while True:
            try:
                data_list = self.pos_disable_from_plan_id_log_queue.get(timeout=self.pos_disable_from_plan_id_log_queue_timeout_sec)      # event based block

            except queue.Empty:
                # Handle the empty queue condition
                continue

            plan_id_n_msg_tuple_list: List[Tuple[int, str]] = []
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

                plan_id_n_msg_tuple_list.append((plan_id, message))

            if plan_id_n_msg_tuple_list:
                # coro needs public method
                run_coro = self.handle_pos_disable_tasks(plan_id_n_msg_tuple_list)
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
        # Adding alert for original payload
        await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_plan_alerts_with_symbol_side_query_http(payload)

        update_pair_plan_json_list = []
        plan_id_list = []
        for log_data in payload:
            message = log_data.get("message")

            symbol_side_set = get_symbol_n_side_from_log_line(message)
            symbol_side: str = list(symbol_side_set)[0]
            symbol, side = symbol_side.split("-")

            plan_id: int | None = self.plan_id_by_symbol_side_dict.get(symbol_side)

            if plan_id is None:
                pair_plan_obj: PairPlanBaseModel = self._get_pair_plan_obj_from_symbol_side(symbol, Side(side))
                if pair_plan_obj is None:
                    raise HTTPException(detail=f"No Ongoing pair plan found for symbol_side: {symbol_side}",
                                        status_code=400)

                plan_id = pair_plan_obj.id
                for symbol_side in symbol_side_set:
                    self.plan_id_by_symbol_side_dict[symbol_side] = plan_id

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
