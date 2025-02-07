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

# 3rd party modules
import pendulum
import setproctitle

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_routes_msgspec_callback import LogBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.phone_book_log_book import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import PlanViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import PlanState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    UpdateType, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.aggregate import *
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert, create_logger, submitted_task_result, handle_refresh_configurable_data_members,
    get_pid_from_port, is_process_running)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from FluxPythonUtils.log_book.log_book_shm import LogBookSHM

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


class LogBookServiceRoutesCallbackBaseNativeOverride(LogBookServiceRoutesCallback):
    debug_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DEBUG|INFO|DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    pair_plan_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    background_log_prefix_regex_pattern: str = (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : )?(.*"
                                                r"(?:Error|Exception|WARNING|ERROR|CRITICAL))(\s*:\s*)?")
    log_simulator_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                  r"INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
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
    underlying_log_book_force_kill_tail_executor_query_http: Callable[..., Any] | None = None
    underlying_filtered_plan_alert_by_plan_id_query_http: Callable[..., Any] | None = None
    underlying_delete_plan_alert_http: Callable[..., Any] | None = None
    underlying_delete_by_id_list_plan_alert_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.plan_alert_cache_dict_by_plan_id_dict: Dict[int, Dict[str, PlanAlert]] = {}     # updates in main thread only
        self.contact_alerts_cache_dict: Dict[str, ContactAlert] = {}    # updates in main thread only
        self.plan_alerts_cache_cont: AlertsCacheCont = AlertsCacheCont(name="plan")
        self.contact_alerts_cache_cont: AlertsCacheCont = AlertsCacheCont(name="contact")
        self.tail_file_multiprocess_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.clear_cache_file_path_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.file_path_to_log_detail_cache_mutex: threading.RLock = threading.RLock()
        self.file_path_to_log_detail_cache_dict: Dict[str, List[PlanLogDetail]] = {}
        self.active_plan_id_list_mutex: threading.Lock = threading.Lock()
        self.active_plan_id_list: List[int] = []
        self.file_path_to_log_book_shm_obj_dict: Dict[str, LogBookSHM] = {}
        self.file_watcher_process: multiprocessing.Process | None = None
        self.contact_alert_queue: Queue = Queue()
        self.plan_alert_queue: Queue = Queue()
        self.tail_executor_start_time_local: DateTime = DateTime.now(tz='local')
        self.tail_executor_start_time_local_fmt: str = (
            self.tail_executor_start_time_local.format("YYYY-MM-DD HH:mm:ss,SSS"))
        # timeout event
        self.plan_state_update_dict: Dict[int, Tuple[str, DateTime]] = {}
        self.pause_plan_trigger_dict: Dict[int, DateTime] = {}
        self.last_timeout_event_datetime: DateTime | None = None

        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.contact_alert_fail_logger = create_logger("contact_alert_fail_logger", logging.DEBUG,
                                                         str(CURRENT_PROJECT_LOG_DIR), contact_alert_fail_log)
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }

    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_msgspec_routes import (
            underlying_read_contact_alert_http, underlying_create_all_contact_alert_http,
            underlying_read_plan_alert_http, underlying_delete_by_id_list_plan_alert_http,
            underlying_update_all_contact_alert_http, underlying_create_all_plan_alert_http,
            underlying_update_all_plan_alert_http, underlying_log_book_force_kill_tail_executor_query_http,
            underlying_filtered_plan_alert_by_plan_id_query_http, underlying_delete_plan_alert_http)
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
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_log_book_force_kill_tail_executor_query_http = (
            underlying_log_book_force_kill_tail_executor_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_filtered_plan_alert_by_plan_id_query_http = (
            underlying_filtered_plan_alert_by_plan_id_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_alert_http = (
            underlying_delete_plan_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_by_id_list_plan_alert_http = (
            underlying_delete_by_id_list_plan_alert_http)

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"log_book_{la_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.run_queue_handler()

                        # creating tail_executor log dir if not exists
                        log_dir: PurePath = PurePath(__file__).parent.parent / "log" / "tail_executors"
                        if not os.path.exists(log_dir):
                            os.mkdir(log_dir)

                        simulation_mode: bool = config_yaml_dict.get("simulate_log_book", False)
                        # consumer thread for tail_file_multiprocess_queue
                        Thread(target=PhoneBookLogBook.dynamic_start_log_book_for_log_details,
                               args=(self.tail_file_multiprocess_queue,
                                     self.file_path_to_log_detail_cache_mutex,
                                     self.file_path_to_log_detail_cache_dict,
                                     spawn, self.tail_executor_start_time_local_fmt,
                                     self.file_path_to_log_book_shm_obj_dict,),
                               kwargs={"regex_file_dir_path": str(LOG_ANALYZER_DATA_DIR),
                                       "simulation_mode": simulation_mode},
                               daemon=True, name="tail_file_multiprocess_queue").start()

                        # running watcher process
                        process = (
                            multiprocessing.Process(
                                target=self.start_pair_plan_log_book_script,
                                args=(self.tail_file_multiprocess_queue,
                                      self.clear_cache_file_path_queue,),
                                daemon=True, name="file_watcher"))

                        process.start()
                        self.file_watcher_process = process

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

                    # checking all cached tail executor process - if crashed handles recovery
                    self.handle_crashed_tail_executors()

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

        # killing file watcher process
        self.file_watcher_process.kill()

        # Exiting all started threads
        self.tail_file_multiprocess_queue.put("EXIT")
        self.plan_alert_queue.put("EXIT")
        self.contact_alert_queue.put("EXIT")

        # deleting existing shm
        for file_name, log_book_shm in self.file_path_to_log_book_shm_obj_dict.items():
            log_book_shm.lock_shm.close()
            log_book_shm.lock_shm.unlink()
            logging.debug(f"Unlinked lock_shm for {log_book_shm.log_file_path} in graceful shutdown")

        # deleting lock file for suppress alert regex
        regex_lock_file_name = config_yaml_dict.get("regex_lock_file_name")
        if regex_lock_file_name is not None:
            regex_lock_file = LOG_ANALYZER_DATA_DIR / regex_lock_file_name
            if os.path.exists(regex_lock_file):
                os.remove(regex_lock_file)
        else:
            err_str_ = "Can't find key 'regex_lock_file_name' in config dict - can't delete regex pattern lock file"
            logging.error(err_str_)

    def handle_crashed_tail_executors(self):
        with self.file_path_to_log_detail_cache_mutex:
            for log_file_path, plan_log_detail_list in self.file_path_to_log_detail_cache_dict.items():
                for plan_log_detail in plan_log_detail_list:
                    pid = plan_log_detail.tail_executor_process.pid
                    if not is_process_running(pid):
                        # removing log detail from cached log details and sending it to queue for restart
                        plan_log_detail.tail_executor_process = None
                        plan_log_detail_list.remove(plan_log_detail)

                        log_book_shm = self.file_path_to_log_book_shm_obj_dict.get(plan_log_detail.log_file_path)
                        if log_book_shm is None:
                            logging.error("Can't find log_book_shm obj in file_path_to_log_book_shm_obj_dict for "
                                          f"{plan_log_detail.log_file_path=} - ignoring this tail executor recovery")
                            continue

                        last_processed_utc_datetime = log_book_shm.get()
                        restart_datetime: str | None = None
                        if last_processed_utc_datetime is not None:
                            restart_datetime = (
                                PhoneBookBaseLogBook._get_restart_datetime_from_log_detail(last_processed_utc_datetime))
                        self._handle_tail_file_multiprocess_queue_update_for_tail_executor_restart(
                            [plan_log_detail], restart_datetime)
                    # else not required: all good if tail executor is running

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
                self._force_trigger_plan_pause(plan_id, err_)
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
            plan_id: int, action: bool):
        with self.active_plan_id_list_mutex:
            if action:
                if plan_id not in self.active_plan_id_list:
                    self.active_plan_id_list.append(plan_id)
                else:
                    logging.warning(f"{plan_id=} already exists in active_plan_id_list - "
                                    f"enable_disable_plan_alert_create_query was called to enable plan_alerts for "
                                    f"this id - verify if happened due to some bug")
            else:
                if plan_id in self.active_plan_id_list:
                    self.active_plan_id_list.remove(plan_id)
                else:
                    logging.warning(f"{plan_id=} doesn't exist in active_plan_id_list - "
                                    f"enable_disable_plan_alert_create_query was called to disable plan_alerts for "
                                    f"this id - verify if happened due to some bug")
        return []

    def _force_trigger_plan_pause(self, pair_plan_id: int, error_event_msg: str):
        component_file_path: PurePath = PurePath(__file__)
        try:
            updated_pair_plan: PairPlanBaseModel = PairPlanBaseModel.from_kwargs(
                _id=pair_plan_id, plan_state=PlanState.PlanState_PAUSED)
            email_book_service_http_client.patch_pair_plan_client(
                updated_pair_plan.to_json_dict(exclude_none=True))
            err_ = f"Force paused {pair_plan_id=}, {error_event_msg}"
            logging.critical(err_)
            alert_meta = get_alert_meta_obj(str(component_file_path), component_file_path.name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow())
            self._send_plan_alerts(pair_plan_id, PhoneBookBaseLogBook.get_severity("critical"),
                                    err_, alert_meta)
        except Exception as e:
            alert_brief: str = f"force_trigger_plan_pause failed for {pair_plan_id=}, {error_event_msg=}"
            alert_details: str = f"exception: {e}"
            logging.critical(f"{alert_brief};;;{alert_details}")
            alert_meta = get_alert_meta_obj(str(component_file_path), component_file_path.name,
                                            inspect.currentframe().f_lineno, DateTime.utcnow(), alert_details)
            self.send_contact_alerts(severity=PhoneBookBaseLogBook.get_severity("critical"),
                                       alert_brief=alert_brief, alert_meta=alert_meta)

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
            self._send_plan_alerts(plan_id, PhoneBookBaseLogBook.get_severity("critical"), alert_brief,
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
                self.send_contact_alerts(model_obj.severity, model_obj.alert_brief, alert_meta)
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
                f"send_contact_alerts failed{PhoneBookBaseLogBook.log_seperator} exception: {e};;; "
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

    async def handle_plan_alerts_from_tail_executor_query_pre(
            self, handle_plan_alerts_from_tail_executor_class_type: Type[HandlePlanAlertsFromTailExecutor],
            payload_dict: Dict[str, Any]):
        plan_alert_data_list: List[Dict] = payload_dict.get("plan_alert_data_list")
        for plan_alert_data in plan_alert_data_list:
            plan_id = plan_alert_data.get("plan_id")
            severity = plan_alert_data.get("severity")
            alert_brief = plan_alert_data.get("alert_brief")
            alert_meta = plan_alert_data.get("alert_meta")
            if alert_meta:
                alert_meta = AlertMeta.from_dict(alert_meta)

            if plan_id is not None and severity is not None and alert_brief is not None:
                await async_update_plan_alert_cache(plan_id, self.plan_alert_cache_dict_by_plan_id_dict,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.
                                                     underlying_filtered_plan_alert_by_plan_id_query_http)
                self._send_plan_alerts(plan_id, severity, alert_brief, alert_meta)
            else:
                err_severity = PhoneBookBaseLogBook.get_severity("error")
                err_brief = ("handle_plan_alerts_from_tail_executor_query_pre failed - start_alert data found with "
                             "missing data, can't create plan alert")
                err_details = f"received: {plan_id=}, {severity=}, {alert_brief=}, {alert_meta=}"
                alert_meta = get_alert_meta_obj(alert_meta.component_file_path, alert_meta.source_file_name,
                                                alert_meta.line_num, alert_meta.alert_create_date_time,
                                                alert_meta.first_detail, err_details, alert_meta_type=AlertMeta)
                self.send_contact_alerts(err_severity, err_brief, alert_meta)
                raise HTTPException(detail=f"{err_severity};;;{err_details}", status_code=400)
        return []

    async def handle_contact_alerts_from_tail_executor_query_pre(
            self, handle_contact_alerts_from_tail_executor_class_type: Type[HandleContactAlertsFromTailExecutor],
            payload_dict: Dict[str, Any]):
        contact_alert_data_list: List[Dict] = payload_dict.get("contact_alert_data_list")
        for contact_alert_data in contact_alert_data_list:
            severity = contact_alert_data.get("severity")
            alert_brief = contact_alert_data.get("alert_brief")
            alert_meta = contact_alert_data.get("alert_meta")
            if alert_meta:
                alert_meta = AlertMeta.from_dict(alert_meta)

            if severity is not None and alert_brief is not None:
                self.send_contact_alerts(severity, alert_brief, alert_meta)
            else:
                err_str_ = ("handle_contact_alerts_from_tail_executor_query_pre failed - contact_alert data "
                            "found with missing data, can't create plan alert;;; "
                            f"received: {severity=}, {alert_brief=}, {alert_meta=}")
                self.contact_alert_fail_logger.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    def start_pair_plan_log_book_script(
            self, tail_multiprocess_queue: multiprocessing.Queue,
            clear_cache_file_path_queue: multiprocessing.Queue):
        # changing process name
        p_name = current_process().name
        setproctitle.setproctitle(p_name)

        # setting log file for current file watcher script
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        datetime_str = LogBookServiceRoutesCallbackBaseNativeOverride.datetime_str
        simulation_mode = config_yaml_dict.get("simulate_log_book", False)
        log_file_name = f"file_watcher_logs_{datetime_str}.log"
        configure_logger(logging.DEBUG, log_file_dir_path=str(log_dir),
                         log_file_name=log_file_name)
        if debug_mode:
            log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.debug_log_prefix_regex_pattern_to_callable_name_dict)
            log_prefix_regex_pattern_to_log_date_time_regex_pattern = (
                LogBookServiceRoutesCallbackBaseNativeOverride.debug_log_prefix_regex_pattern_to_log_date_time_regex_pattern
            )
            log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = (
                LogBookServiceRoutesCallbackBaseNativeOverride.debug_log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern
            )
        else:
            log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_callable_name_dict)
            log_prefix_regex_pattern_to_log_date_time_regex_pattern = (
                LogBookServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_log_date_time_regex_pattern
            )
            log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = (
                LogBookServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern
            )
        background_log_prefix_regex_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.
            background_log_prefix_regex_pattern_to_callable_name_dict)
        log_simulator_prefix_regex_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.log_simulator_prefix_regex_pattern_to_callable_name_dict
        )
        perf_benchmark_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.log_perf_benchmark_pattern_to_callable_name_dict)
        log_details: List[PlanLogDetail] = [
            PlanLogDetail(
                service="phone_book",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="phone_book_debug_background",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_logs_background.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict),
            PlanLogDetail(
                service="phone_book_background",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_logs_background_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict),
            PlanLogDetail(
                service="street_book",
                log_file_path=str(street_book_log_dir / f"street_book_*_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True,
                plan_id_find_callable=plan_id_from_executor_log_file),
            PlanLogDetail(
                service="post_book",
                log_file_path=str(post_barter_log_dir / f"post_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="post_book_background",
                log_file_path=str(
                    post_barter_log_dir / f"post_book_logs_background_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict),
            PlanLogDetail(
                service="post_book_debug_background",
                log_file_path=str(
                    post_barter_log_dir / f"post_book_logs_background.log"),
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict),
            PlanLogDetail(
                service="street_book_log_simulator",
                log_file_path=str(street_book_log_dir / f"log_simulator_*_{datetime_str}.log"),
                critical=True if simulation_mode else False,
                log_prefix_regex_pattern_to_callable_name_dict=
                log_simulator_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=True,
                plan_id_find_callable=plan_id_from_simulator_log_file),
            PlanLogDetail(
                service="log_book_perf_bench",
                log_file_path=str(
                    log_dir / f"log_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=perf_benchmark_pattern_to_callable_name_dict),
            PlanLogDetail(
                service="photo_book",
                log_file_path=str(
                    photo_book_log_dir / f"photo_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="photo_book_background",
                log_file_path=str(
                    photo_book_log_dir / f"photo_book_logs_background_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="photo_book_debug_background",
                log_file_path=str(
                    photo_book_log_dir / f"photo_book_logs_background.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="basket_book",
                log_file_path=str(
                    basket_book_log_dir / f"basket_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="basket_book_background",
                log_file_path=str(
                    basket_book_log_dir / f"basket_book_logs_background_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="basket_book_debug_background",
                log_file_path=str(
                    basket_book_log_dir / f"basket_book_logs_background.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern),
            PlanLogDetail(
                service="basket_book_log_simulator",
                log_file_path=str(basket_book_log_dir / f"log_simulator_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                log_simulator_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=True),
            PlanLogDetail(
                service="phone_book_unload_plan_event",
                log_file_path=str(
                    phone_book_log_dir / f"unload_plan_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True),
            PlanLogDetail(
                service="phone_book_recycle_plan_event",
                log_file_path=str(
                    phone_book_log_dir / f"recycle_plan_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True),
            PlanLogDetail(
                service="phone_book_pause_all_active_plan_event",
                log_file_path=str(
                    phone_book_log_dir / f"pause_all_active_plans_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            PlanLogDetail(
                # used for test to verify file_watcher's tail_executor start handler with full path
                # IMPO: Also configs in this are used in test - if changed needs changes in tests also
                service="test_street_book_with_full_path",
                log_file_path=str(
                    street_book_log_dir / f"sample_test.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            PlanLogDetail(
                # used for test to verify file_watcher's tail_executor start handler with pattern path
                # IMPO: Also configs in this are used in test - if changed needs changes in tests also
                service="test_street_book_with_pattern",
                log_file_path=str(
                    street_book_log_dir / f"sample_*_test.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True)
        ]
        PhoneBookLogBook.log_file_watcher(log_details, tail_multiprocess_queue, PlanLogDetail,
                                                    self.log_file_watcher_err_handler,
                                                    clear_cache_file_path_queue)

    def log_file_watcher_err_handler(self, alert_brief, **kwargs):

        alert_meta = get_alert_meta_obj(kwargs.get('component_path'), kwargs.get("source_file_name"),
                                        kwargs.get("line_num"), kwargs.get("alert_create_date_time"),
                                        kwargs.get("first_detail"), kwargs.get("latest_detail"),
                                        alert_meta_type=AlertMeta)
        self.send_contact_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                   alert_brief=alert_brief, alert_meta=alert_meta)

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

    def handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded(
            self, plan_alert_obj_list: List[PlanAlert]):
        alert_id_list = []
        with self.active_plan_id_list_mutex:
            for plan_alert_obj in plan_alert_obj_list:
                if plan_alert_obj.plan_id not in self.active_plan_id_list:
                    alert_id_list.append(plan_alert_obj.id)

        if alert_id_list:
            # using error pattern which is raised by update_fail so that in error handling of create_all_plan_alert
            # or update_all_plan_alert in handle_alert_create_n_update_using_async_submit diverts alerts of plan ids
            # of unloaded plans to contact alerts
            err_str_ = (f"Some plan alert objects with ids: {set(alert_id_list)} "
                        f"out of requested found having plan ids of unloaded plan")
            logging.warning(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

    async def update_all_plan_alert_pre(self, updated_plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        self.handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded(updated_plan_alert_obj_list)

        return updated_plan_alert_obj_list

    async def update_plan_alert_pre(self, updated_plan_alert_obj: PlanAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        self.handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded([updated_plan_alert_obj])

        return updated_plan_alert_obj

    async def partial_update_plan_alert_pre(self, stored_plan_alert_obj: PlanAlert,
                                             updated_plan_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        # passed obj is only used for extracting and checking plan_id - updated obj is not required
        self.handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded([stored_plan_alert_obj])

        return updated_plan_alert_obj_json

    async def partial_update_all_plan_alert_pre(self, stored_plan_alert_obj_list: List[PlanAlert],
                                                 updated_plan_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        # passed obj list is only used for extracting and checking plan_id - updated list is not required
        self.handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded(stored_plan_alert_obj_list)

        return updated_plan_alert_obj_json_list

    async def create_all_plan_alert_pre(self, plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_all_plan_alert_pre not ready - service is not initialized yet"
            self.contact_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        self.handle_diversion_of_plan_alerts_to_contact_alerts_if_plan_is_unloaded(plan_alert_obj_list)

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

                update_json = {"_id": updated_plan_id,
                               "plan_alert_aggregated_severity": plan_alert_aggregated_severity,
                               "plan_alert_count": plan_alert_count}
                payload_dict = {"update_json_list": [update_json], "update_type": UpdateType.SNAPSHOT_TYPE,
                                "basemodel_type_name": PlanViewBaseModel.__name__,
                                "method_name": "patch_all_plan_view_client"}
                photo_book_service_http_client.process_plan_view_updates_query_client(payload_dict)
            # else not required: if no data is in db - no handling

    async def update_all_plan_alert_post(self, updated_plan_alert_obj_list: List[PlanAlert]):
        await self.plan_view_update_handling(updated_plan_alert_obj_list)

    async def create_all_plan_alert_post(self, plan_alert_obj_list: List[PlanAlert]):
        await self.plan_view_update_handling(plan_alert_obj_list)

    def _handle_tail_file_multiprocess_queue_update_for_tail_executor_restart(
            self, plan_log_detail_list: List[PlanLogDetail], start_timestamp: str):
        for log_detail in plan_log_detail_list:
            # updating tail_details for this log_file to restart it from logged timestamp
            log_detail.processed_timestamp = start_timestamp
            log_detail.is_running = False

            # updating multiprocess queue to again start tail executor for log detail but from specific time
            logging.info(f"Putting log_detail in tail_file_multiprocess_queue for restart;;; {log_detail=}")
            self.tail_file_multiprocess_queue.put(log_detail)

    async def log_book_restart_tail_query_pre(
            self, log_book_restart_tail_class_type: Type[LogBookRestartTail], log_file_name: str,
            start_timestamp: str):
        try:
            pendulum.parse(start_timestamp)  # checking if passed value is parsable
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Couldn't parse start_datetime, exception: {e}")

        with self.file_path_to_log_detail_cache_mutex:
            plan_log_detail_list: List[PlanLogDetail] = self.file_path_to_log_detail_cache_dict.get(log_file_name)

            if plan_log_detail_list:
                # first terminating process - not unlinking shm for this tail executor, will be reused with new
                # tail executor
                self.terminate_tail_executor_process_from_plan_log_detail_list(log_file_name, plan_log_detail_list,
                                                                                unlink_shm=False)

                self._handle_tail_file_multiprocess_queue_update_for_tail_executor_restart(plan_log_detail_list,
                                                                                           start_timestamp)
            else:
                logging.warning("Can't find log_file_name in file_path_to_log_detail_cache_dict - ignoring restart, "
                                f"{log_file_name=}, {start_timestamp=}")
        return []

    def terminate_tail_executor_process_from_plan_log_detail_list(self,
                                                                   log_file_path: str,
                                                                   plan_log_detail_list: List[PlanLogDetail],
                                                                   unlink_shm: bool = True):
        plan_log_detail: PlanLogDetail
        for plan_log_detail in plan_log_detail_list:
            plan_log_detail.tail_executor_process.terminate()
            plan_log_detail.tail_executor_process.join()
            plan_log_detail.tail_executor_process = None

            if unlink_shm:
                # cleaning log analyzer shm
                log_book_shm = self.file_path_to_log_book_shm_obj_dict.get(plan_log_detail.log_file_path)
                if log_book_shm is None:
                    logging.error(f"Couldn't find log_book_shm for log file {plan_log_detail.log_file_path} in "
                                  f"file_path_to_log_book_shm_obj_dict - ignoring cleaning of this shm")
                    continue
                log_book_shm.last_processed_timestamp_shm.close()
                log_book_shm.last_processed_timestamp_shm.unlink()
                logging.debug(f"Unlinked last_processed_timestamp_shm for {log_book_shm.log_file_path}")
                log_book_shm.lock_shm.close()
                log_book_shm.lock_shm.unlink()
                logging.debug(f"Unlinked lock_shm for {log_book_shm.log_file_path}")
                del self.file_path_to_log_book_shm_obj_dict[plan_log_detail.log_file_path]
                logging.debug(f"removed entry for {log_book_shm.log_file_path} in "
                              f"file_path_to_log_book_shm_obj_dict")

        self.file_path_to_log_detail_cache_dict.pop(log_file_path)

    async def log_book_force_kill_tail_executor_query_pre(
            self, log_book_force_kill_tail_executor_class_type: Type[LogBookForceKillTailExecutor],
            log_file_path: str):
        """
        terminates all tail executors running for passed file_path - doesn't release cache for log file path
        since doing it will restart new tail executor - separate query must be called to release cache and restart
        tail executor for log_file_path
        """

        with self.file_path_to_log_detail_cache_mutex:  # mutex for file_path_to_log_detail_cache_dict
            plan_log_detail_list: List[PlanLogDetail] = (
                self.file_path_to_log_detail_cache_dict.get(log_file_path))

            if plan_log_detail_list:
                self.terminate_tail_executor_process_from_plan_log_detail_list(log_file_path, plan_log_detail_list)
            else:
                # keeping log as info since from tests this query is used in clean_n_set_limits - it's expected
                # to call this with no tail executor running with passed log_file_path
                logging.info(f"Ignoring Force Kill tail executor - Can't find any tail_executor for "
                             f"file: {log_file_path} in {self.file_path_to_log_detail_cache_dict=}")
            return []

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

    async def log_book_remove_file_from_created_cache_query_pre(
            self, log_book_remove_file_from_created_cache_class_type: Type[LogBookRemoveFileFromCreatedCache],
            log_file_path_list: List[str]):
        with self.file_path_to_log_detail_cache_mutex:
            for log_file_path in log_file_path_list:
                # consumer of this queue handles task to release cache for this file entry - logs error if file
                # not found in cache
                self.clear_cache_file_path_queue.put(log_file_path)
                logging.debug(f"requested cache clean-up for {log_file_path=}")

                # clearing file_path_to_log_detail_cache_dict so that if next tail_executor starts with same file_path
                # it doesn't already have entries for file_path
                self.file_path_to_log_detail_cache_dict.pop(log_file_path, None)

        return []

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
            self, remove_plan_alerts_for_plan_id_class_type: Type[RemovePlanAlertsForPlanId], plan_id: int):
        try:
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

            # releasing cache for plan id
            self.plan_alert_cache_dict_by_plan_id_dict.pop(plan_id, None)

            # updating plan_view fields
            # await self._plan_view_update_handling(plan_id)
            update_json = {"_id": plan_id,
                           "plan_alert_aggregated_severity": Severity.Severity_UNSPECIFIED,
                           "plan_alert_count": 0}
            payload_dict = {"update_json_list": [update_json], "update_type": UpdateType.SNAPSHOT_TYPE,
                            "basemodel_type_name": PlanViewBaseModel.__name__,
                            "method_name": "patch_all_plan_view_client"}
            photo_book_service_http_client.process_plan_view_updates_query_client(payload_dict)
        except Exception as e_:
            logging.exception(e_)
            raise HTTPException(detail=str(e_), status_code=500)

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


def filtered_plan_alert_by_plan_id_query_callable(plan_alert_obj_json_str: str, **kwargs):
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
