# standard imports
import json
import logging
import multiprocessing
import time
from multiprocessing import current_process
from queue import Queue
import sys
import signal

# 3rd party modules
import pendulum
import setproctitle

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_routes_callback import LogBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.phone_book_log_book import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import StratViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    pair_strat_client_call_log_str, UpdateType, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.aggregate import *
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert, create_logger, submitted_task_result)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)

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

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

portfolio_alert_bulk_update_counts_per_call, portfolio_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("portfolio_alert_configs")))
strat_alert_bulk_update_counts_per_call, strat_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("strat_alert_config")))

# required to avoid problems like mentioned in this url
# https://pythonspeed.com/articles/python-multiprocessing/
spawn = multiprocessing.get_context("spawn")

class StratViewUpdateCont(BaseModel):
    total_objects: int | None = None
    highest_priority_severity: Severity | None = None
    model_config = ConfigDict(populate_by_name=True, extra='forbid')


class LogBookServiceRoutesCallbackBaseNativeOverride(LogBookServiceRoutesCallback):
    debug_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DEBUG|INFO|DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    pair_strat_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                               r"DB|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*\] : "
    background_log_prefix_regex_pattern: str = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : )?(" \
                                               r"WARNING|ERROR|CRITICAL):"
    log_simulator_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                  r"INFO|WARNING|ERROR|CRITICAL) : \[[a-zA-Z._]* : \d*] : "
    perf_benchmark_log_prefix_regex_pattern: str = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} : (" \
                                                   r"TIMING) : \[[a-zA-Z._]* : \d*] : "
    log_prefix_regex_pattern_to_callable_name_dict = {
        pair_strat_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    log_prefix_regex_pattern_to_log_date_time_regex_pattern = {
        pair_strat_log_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        pair_strat_log_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
    }
    debug_log_prefix_regex_pattern_to_callable_name_dict = {
        debug_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    debug_log_prefix_regex_pattern_to_log_date_time_regex_pattern = {
        debug_prefix_regex_pattern: r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    }
    debug_log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern = {
        debug_prefix_regex_pattern: r'\[([^:]+)\s*:\s*(\d+)\]'
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
        background_log_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    debug_background_log_prefix_regex_pattern_to_callable_name_dict = {
        debug_prefix_regex_pattern: "handle_pair_strat_matched_log_message"
    }
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    underlying_read_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_create_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_update_all_portfolio_alert_http: Callable[..., Any] | None = None
    underlying_create_all_strat_alert_http: Callable[..., Any] | None = None
    underlying_update_all_strat_alert_http: Callable[..., Any] | None = None
    underlying_read_strat_alert_http: Callable[..., Any] | None = None
    underlying_log_book_force_kill_tail_executor_query_http: Callable[..., Any] | None = None
    underlying_filtered_strat_alert_by_strat_id_query_http: Callable[..., Any] | None = None
    underlying_delete_strat_alert_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.strat_alert_cache_dict_by_strat_id_dict: Dict[int, Dict[str, StratAlert]] = {}
        self.portfolio_alerts_cache_dict: Dict[str, PortfolioAlert] = {}
        self.strat_alert_id_to_obj_dict: Dict[int, StratAlert] = {}
        self.portfolio_alert_id_to_obj_dict: Dict[int, PortfolioAlert] = {}
        self.pydantic_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.tail_file_multiprocess_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.clear_cache_file_path_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.file_path_to_tail_executor_process_cache_dict: Dict[str, List[multiprocessing.Process]] = {}
        self.file_path_to_log_detail_cache_dict: Dict[str, List[StratLogDetail]] = {}
        self.file_watcher_process: multiprocessing.Process | None = None
        self.portfolio_alert_queue: Queue = Queue()
        self.strat_alert_queue: Queue = Queue()
        self.tail_executor_start_time_local: DateTime = DateTime.now(tz='local')
        self.tail_executor_start_time_local_fmt: str = (
            self.tail_executor_start_time_local.format("YYYY-MM-DD HH:mm:ss,SSS"))

        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.portfolio_alert_fail_logger = create_logger("portfolio_alert_fail_logger", logging.DEBUG,
                                                         str(CURRENT_PROJECT_LOG_DIR), portfolio_alert_fail_log)

    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.FastApi.log_book_service_http_routes import (
            underlying_read_portfolio_alert_http, underlying_create_all_portfolio_alert_http,
            underlying_read_strat_alert_http,
            underlying_update_all_portfolio_alert_http, underlying_create_all_strat_alert_http,
            underlying_update_all_strat_alert_http, underlying_log_book_force_kill_tail_executor_query_http,
            underlying_filtered_strat_alert_by_strat_id_query_http, underlying_delete_strat_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_alert_http = (
            underlying_read_portfolio_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_portfolio_alert_http = (
            underlying_create_all_portfolio_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_portfolio_alert_http = (
            underlying_update_all_portfolio_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_strat_alert_http = (
            underlying_create_all_strat_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_strat_alert_http = (
            underlying_update_all_strat_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_alert_http = (
            underlying_read_strat_alert_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_log_book_force_kill_tail_executor_query_http = (
            underlying_log_book_force_kill_tail_executor_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_filtered_strat_alert_by_strat_id_query_http = (
            underlying_filtered_strat_alert_by_strat_id_query_http)
        LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_alert_http = (
            underlying_delete_strat_alert_http)

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
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
                        # updating portfolio alert cache
                        self.load_portfolio_alerts_n_update_cache()
                        # updating strat alert cache
                        self.load_strat_alerts_n_update_cache()

                        self.run_queue_handler()

                        # creating tail_executor log dir if not exists
                        log_dir: PurePath = PurePath(__file__).parent.parent / "log" / "tail_executors"
                        if not os.path.exists(log_dir):
                            os.mkdir(log_dir)

                        simulation_mode: bool = config_yaml_dict.get("simulate_log_book", False)
                        Thread(target=PhoneBookLogBook.dynamic_start_log_book_for_log_details,
                               args=(self.tail_file_multiprocess_queue,
                                     self.file_path_to_tail_executor_process_cache_dict,
                                     self.file_path_to_log_detail_cache_dict,
                                     spawn, self.tail_executor_start_time_local_fmt,),
                               kwargs={"regex_file_dir_path": str(LOG_ANALYZER_DATA_DIR),
                                       "simulation_mode": simulation_mode},
                               daemon=True).start()

                        # running watcher process
                        process = (
                            multiprocessing.Process(
                                target=self.start_pair_strat_log_book_script,
                                args=(self.tail_file_multiprocess_queue,
                                      self.clear_cache_file_path_queue,),
                                daemon=True, name="file_watcher"))

                        process.start()
                        self.file_watcher_process = process

                        self.service_ready = True
                        print(f"INFO: service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        self.portfolio_alert_fail_logger.exception(
                            "Unexpected: service startup threw exception, "
                            f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                            f";;;exception: {e}")
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
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

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # killing file watcher process
        self.file_watcher_process.kill()

        # Exiting all started threads
        self.tail_file_multiprocess_queue.put("EXIT")
        self.strat_alert_queue.put("EXIT")
        self.portfolio_alert_queue.put("EXIT")

        # deleting lock file for suppress alert regex
        regex_lock_file_name = config_yaml_dict.get("regex_lock_file_name")
        if regex_lock_file_name is not None:
            regex_lock_file = LOG_ANALYZER_DATA_DIR / regex_lock_file_name
            if os.path.exists(regex_lock_file):
                os.remove(regex_lock_file)
        else:
            err_str_ = "Can't find key 'regex_lock_file_name' in config dict - can't delete regex pattern lock file"
            logging.error(err_str_)

    def _handle_portfolio_alert_queue_err_handler(self, *args):
        err_str_ = f"_handle_portfolio_alert_queue_err_handler called, passed args: {args}"
        self.portfolio_alert_fail_logger.exception(err_str_)

    def load_portfolio_alerts_n_update_cache(self):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_alert_http()
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_read_portfolio_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            portfolio_alerts: List[PortfolioAlert] = submitted_task_result(future)
            for portfolio_alert in portfolio_alerts:
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(portfolio_alert)
                alert_key = get_alert_cache_key(portfolio_alert.severity, portfolio_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                self.portfolio_alerts_cache_dict[alert_key] = portfolio_alert
                self.portfolio_alert_id_to_obj_dict[portfolio_alert.id] = portfolio_alert

        except Exception as e:
            err_str_ = f"load_portfolio_alerts_n_update_cache failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def load_strat_alerts_n_update_cache(self):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_alert_http()
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_read_strat_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            strat_alerts: List[StratAlert] = submitted_task_result(future)
        except Exception as e:
            err_str_ = f"load_portfolio_alerts_n_update_cache failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)
        else:
            for strat_alert in strat_alerts:
                strat_alert_cache = self.strat_alert_cache_dict_by_strat_id_dict.get(strat_alert.strat_id)
                component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(strat_alert)
                alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                                component_file_path, source_file_name, line_num)
                if strat_alert_cache is None:
                    self.strat_alert_cache_dict_by_strat_id_dict[strat_alert.strat_id] = {alert_key: strat_alert}
                else:
                    strat_alert_cache[alert_key] = strat_alert
                self.strat_alert_id_to_obj_dict[strat_alert.id] = strat_alert

    def put_all_portfolio_alert_client_with_asyncio_loop(self, portfolio_alerts: List[PortfolioAlert]):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_portfolio_alert_http(
                    portfolio_alerts)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_update_all_portfolio_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            return submitted_task_result(future)
        except Exception as e:
            err_str_ = f"put_all_portfolio_alert_client_with_asyncio_loop failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def create_all_portfolio_alert_client_with_asyncio_loop(self, portfolio_alerts: List[PortfolioAlert]):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_portfolio_alert_http(
                    portfolio_alerts)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_create_all_portfolio_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            return submitted_task_result(future)
        except Exception as e:
            err_str_ = f"create_all_portfolio_alert_client_with_asyncio_loop failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def put_all_strat_alert_client_with_asyncio_loop(self, strat_alerts: List[StratAlert]):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_strat_alert_http(
                    strat_alerts)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_create_all_portfolio_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            return submitted_task_result(future)
        except Exception as e:
            err_str_ = f"put_all_strat_alert_client_with_asyncio_loop failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def create_all_strat_alert_client_with_asyncio_loop(self, strat_alerts: List[StratAlert]):
        try:
            if self.asyncio_loop is not None:
                run_coro = LogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_strat_alert_http(
                    strat_alerts)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            else:
                err_str_ = f"cant find asyncio_loop, cant submit task of underlying_create_all_portfolio_alert_http"
                logging.error(err_str_)
                raise Exception(err_str_)

            return submitted_task_result(future)
        except Exception as e:
            err_str_ = f"create_all_strat_alert_client_with_asyncio_loop failed with exception: {e}"
            logging.error(err_str_)
            raise Exception(err_str_)

    def _handle_portfolio_alert_queue(self):
        alert_queue_handler(
            self.asyncio_loop, self.portfolio_alert_queue, portfolio_alert_bulk_update_counts_per_call,
            portfolio_alert_bulk_update_timeout,
            self.create_all_portfolio_alert_client_with_asyncio_loop,
            self._handle_portfolio_alert_queue_err_handler,
            self.put_all_portfolio_alert_client_with_asyncio_loop,
            self.portfolio_alert_id_to_obj_dict)

    def _handle_strat_alert_queue_err_handler(self, *args):
        try:
            pydantic_obj_list: List[StratAlertBaseModel] = args[0]     # single unprocessed pydantic object is passed
            for pydantic_obj in pydantic_obj_list:
                self.send_portfolio_alerts(pydantic_obj.severity, pydantic_obj.alert_brief, pydantic_obj.alert_details,
                                           pydantic_obj.component_file_path, pydantic_obj.source_file_name,
                                           pydantic_obj.line_num, pydantic_obj.alert_create_date_time)
        except Exception as e:
            err_str_ = f"_handle_strat_alert_queue_err_handler failed, passed args: {args};;; exception: {e}"
            self.portfolio_alert_fail_logger.exception(err_str_)

    def _handle_strat_alert_queue(self):
        alert_queue_handler(
            self.asyncio_loop, self.strat_alert_queue, strat_alert_bulk_update_counts_per_call,
            strat_alert_bulk_update_timeout,
            self.create_all_strat_alert_client_with_asyncio_loop,
            self._handle_strat_alert_queue_err_handler,
            self.put_all_strat_alert_client_with_asyncio_loop,
            self.strat_alert_id_to_obj_dict)

    def run_queue_handler(self):
        portfolio_alert_handler_thread = Thread(target=self._handle_portfolio_alert_queue, daemon=True)
        strat_alert_handler_thread = Thread(target=self._handle_strat_alert_queue, daemon=True)
        portfolio_alert_handler_thread.start()
        strat_alert_handler_thread.start()

    def send_portfolio_alerts(self, severity: str, alert_brief: str,
                              alert_details: AlertDetailOptional | str | None = None,
                              component_path: str | None = None,
                              source_file_name: str | None = None, line_num: int | None = None,
                              alert_create_date_time: DateTime | None = None) -> None:
        logging.debug(f"sending alert with {severity=}, {alert_brief=}, "
                      f"{alert_details=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            alert_meta = get_alert_meta_obj(component_path, source_file_name,
                                            line_num, alert_create_date_time)
            create_or_update_alert(self.portfolio_alerts_cache_dict, self.portfolio_alert_queue,
                                   StratAlert, PortfolioAlert, severity, alert_brief, alert_details,
                                   alert_meta=alert_meta)
        except Exception as e:
            self.portfolio_alert_fail_logger.exception(
                f"send_portfolio_alerts failed{PhoneBookBaseLogBook.log_seperator} exception: {e};;; "
                f"received: {severity=}, {alert_brief=}, {alert_details=}")

    def _send_strat_alerts(self, strat_id: int, severity: str, alert_brief: str,
                           alert_details: AlertDetailOptional | None = None, component_path: str | None = None,
                           source_file_name: str | None = None, line_num: int | None = None,
                           alert_create_date_time: DateTime | None = None) -> None:
        logging.debug(f"sending strat alert with {strat_id=}, {severity=}, "
                      f"{alert_brief=}, {alert_details=}")
        try:
            if not alert_details:
                alert_details = None

            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            alert_meta = get_alert_meta_obj(component_path, source_file_name,
                                            line_num, alert_create_date_time)
            create_or_update_alert(self.strat_alert_cache_dict_by_strat_id_dict[strat_id],
                                   self.strat_alert_queue, StratAlert, PortfolioAlert, severity,
                                   alert_brief, alert_details, strat_id, alert_meta)
        except Exception as e:
            err_msg: str = (f"_send_strat_alerts failed, exception: {e}, "
                            f"received {strat_id=}, {severity=}, {alert_brief=}, {alert_details=}")
            logging.exception(err_msg)
            self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                       alert_brief=alert_brief, alert_details=err_msg,
                                       component_path=component_path, source_file_name=source_file_name,
                                       line_num=line_num, alert_create_date_time=alert_create_date_time)

    async def handle_strat_alerts_from_tail_executor_query_pre(
            self, handle_strat_alerts_from_tail_executor_class_type: Type[HandleStratAlertsFromTailExecutor],
            payload_dict: Dict[str, Any]):
        strat_alert_data_list: List[Dict] = payload_dict.get("strat_alert_data_list")
        for strat_alert_data in strat_alert_data_list:
            strat_id = strat_alert_data.get("strat_id")
            severity = strat_alert_data.get("severity")
            alert_brief = strat_alert_data.get("alert_brief")
            alert_details = strat_alert_data.get("alert_details")
            if alert_details:
                alert_details = AlertDetailOptional(**alert_details)
            alert_meta = strat_alert_data.get("alert_meta")
            if alert_meta:
                alert_meta = AlertMeta(**alert_meta)
            else:
                alert_meta = AlertMeta()

            if strat_id is not None and severity is not None and alert_brief is not None:
                await async_update_strat_alert_cache(strat_id, self.strat_alert_cache_dict_by_strat_id_dict,
                                                     LogBookServiceRoutesCallbackBaseNativeOverride.
                                                     underlying_filtered_strat_alert_by_strat_id_query_http)
                self._send_strat_alerts(strat_id, severity, alert_brief, alert_details,
                                        alert_meta.component_file_path, alert_meta.source_file_name,
                                        alert_meta.line_num, alert_meta.alert_create_date_time)
            else:
                err_severity = PhoneBookBaseLogBook.get_severity("error")
                err_brief = ("handle_strat_alerts_from_tail_executor_query_pre failed - start_alert data found with "
                             "missing data, can't create strat alert")
                err_details = f"received: {strat_id=}, {severity=}, {alert_brief=}, {alert_details=}"
                self.send_portfolio_alerts(err_severity, err_brief, err_details,
                                           alert_meta.component_file_path, alert_meta.source_file_name,
                                           alert_meta.line_num, alert_meta.alert_create_date_time)
                raise HTTPException(detail=f"{err_severity};;;{err_details}", status_code=400)
        return []

    async def handle_portfolio_alerts_from_tail_executor_query_pre(
            self, handle_portfolio_alerts_from_tail_executor_class_type: Type[HandlePortfolioAlertsFromTailExecutor],
            payload_dict: Dict[str, Any]):
        portfolio_alert_data_list: List[Dict] = payload_dict.get("portfolio_alert_data_list")
        for portfolio_alert_data in portfolio_alert_data_list:
            severity = portfolio_alert_data.get("severity")
            alert_brief = portfolio_alert_data.get("alert_brief")
            alert_details = portfolio_alert_data.get("alert_details")
            if alert_details:
                alert_details = AlertDetailOptional(**alert_details)
            alert_meta = portfolio_alert_data.get("alert_meta")
            if alert_meta:
                alert_meta = AlertMeta(**alert_meta)
            else:
                alert_meta = AlertMeta()

            if severity is not None and alert_brief is not None:
                self.send_portfolio_alerts(severity, alert_brief, alert_details,
                                           alert_meta.component_file_path, alert_meta.source_file_name,
                                           alert_meta.line_num, alert_meta.alert_create_date_time)
            else:
                err_str_ = ("handle_portfolio_alerts_from_tail_executor_query_pre failed - portfolio_alert data "
                            "found with missing data, can't create strat alert;;; "
                            f"received: {severity=}, {alert_brief=}, {alert_details=}")
                self.portfolio_alert_fail_logger.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    def start_pair_strat_log_book_script(
            self, tail_multiprocess_queue: multiprocessing.Queue,
            clear_cache_file_path_queue: multiprocessing.Queue):
        # changing process name
        p_name = current_process().name
        setproctitle.setproctitle(p_name)

        # setting log file for current file watcher script
        log_dir: PurePath = PurePath(__file__).parent.parent / "log"
        datetime_str = LogBookServiceRoutesCallbackBaseNativeOverride.datetime_str
        log_file_name = f"file_watcher_logs_{datetime_str}.log"
        configure_logger(logging.DEBUG, log_file_dir_path=str(log_dir),
                         log_file_name=log_file_name)
        if debug_mode:
            log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.debug_log_prefix_regex_pattern_to_callable_name_dict)
            background_log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.
                debug_background_log_prefix_regex_pattern_to_callable_name_dict)
        else:
            log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.log_prefix_regex_pattern_to_callable_name_dict)
            background_log_prefix_regex_pattern_to_callable_name_dict = (
                LogBookServiceRoutesCallbackBaseNativeOverride.
                background_log_prefix_regex_pattern_to_callable_name_dict)
        log_simulator_prefix_regex_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.log_simulator_prefix_regex_pattern_to_callable_name_dict
        )
        perf_benchmark_pattern_to_callable_name_dict = (
            LogBookServiceRoutesCallbackBaseNativeOverride.log_perf_benchmark_pattern_to_callable_name_dict)
        log_details: List[StratLogDetail] = [
            StratLogDetail(
                service="phone_book_beanie_fastapi",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_background_debug",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_background_logs.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                background_log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_background",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_background_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=background_log_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_perf_bench",
                log_file_path=str(
                    phone_book_log_dir / f"phone_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=perf_benchmark_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="street_book",
                log_file_path=str(street_book_log_dir / f"street_book_*_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True,
                strat_id_find_callable=strat_id_from_executor_log_file),
            StratLogDetail(
                service="street_book_perf_bench",
                log_file_path=str(
                    street_book_log_dir / f"street_book_*_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=perf_benchmark_pattern_to_callable_name_dict,
                log_file_path_is_regex=True),
            StratLogDetail(
                service="post_book",
                log_file_path=str(post_barter_log_dir / f"post_book_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True),
            StratLogDetail(
                service="post_book_perf_bench",
                log_file_path=str(
                    post_barter_log_dir / f"post_book_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=perf_benchmark_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="log_simulator",
                log_file_path=str(street_book_log_dir / f"log_simulator_*_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=
                log_simulator_prefix_regex_pattern_to_callable_name_dict,
                log_file_path_is_regex=True),
            StratLogDetail(
                service="log_book_perf_bench",
                log_file_path=str(
                    log_dir / f"log_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=perf_benchmark_pattern_to_callable_name_dict,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="photo_book",
                log_file_path=str(
                    photo_book_log_dir / f"photo_book_logs_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_unload_strat_event",
                log_file_path=str(
                    phone_book_log_dir / f"unload_strat_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_recycle_strat_event",
                log_file_path=str(
                    phone_book_log_dir / f"recycle_strat_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                service="phone_book_pause_all_active_strat_event",
                log_file_path=str(
                    phone_book_log_dir / f"pause_all_active_strats_{datetime_str}.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                # used for test to verify file_watcher's tail_executor start handler with full path
                # IMPO: Also configs in this are used in test - if changed needs changes in tests also
                service="test_street_book_with_full_path",
                log_file_path=str(
                    street_book_log_dir / f"sample_test.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=False),
            StratLogDetail(
                # used for test to verify file_watcher's tail_executor start handler with pattern path
                # IMPO: Also configs in this are used in test - if changed needs changes in tests also
                service="test_street_book_with_pattern",
                log_file_path=str(
                    street_book_log_dir / f"sample_*_test.log"),
                critical=True,
                log_prefix_regex_pattern_to_callable_name_dict=log_prefix_regex_pattern_to_callable_name_dict,
                log_prefix_regex_pattern_to_log_date_time_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_date_time_regex_pattern,
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern=
                LogBookServiceRoutesCallbackBaseNativeOverride.
                log_prefix_regex_pattern_to_log_source_patter_n_line_num_regex_pattern,
                log_file_path_is_regex=True)
        ]
        PhoneBookLogBook.log_file_watcher(log_details, tail_multiprocess_queue, StratLogDetail,
                                                    self.log_file_watcher_err_handler,
                                                    clear_cache_file_path_queue)

    def log_file_watcher_err_handler(self, alert_brief, **kwargs):
        self.send_portfolio_alerts(severity=PhoneBookBaseLogBook.get_severity("error"),
                                   alert_brief=alert_brief, alert_details=kwargs.get("alert_details"),
                                   component_path=kwargs.get("component_path"),
                                   source_file_name=kwargs.get("source_file_name"),
                                   line_num=kwargs.get("line_num"),
                                   alert_create_date_time=kwargs.get("alert_create_date_time"))

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
            self.portfolio_alert_fail_logger.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def update_all_strat_alert_pre(self, stored_strat_alert_obj_list: List[StratAlert],
                                         updated_strat_alert_obj_list: List[StratAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_all_strat_alert_pre not ready - service is not initialized yet"
            self.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        return updated_strat_alert_obj_list

    async def update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert, updated_strat_alert_obj: StratAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_strat_alert_pre not ready - service is not initialized yet"
            self.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        return updated_strat_alert_obj

    async def partial_update_strat_alert_pre(self, stored_strat_alert_obj: StratAlert,
                                             updated_strat_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_strat_alert_pre not ready - service is not initialized yet"
            self.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        return updated_strat_alert_obj_json

    async def partial_update_all_strat_alert_pre(self, stored_strat_alert_obj_list: List[StratAlert],
                                                 updated_strat_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_strat_alert_pre not ready - service is not initialized yet"
            self.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        return updated_strat_alert_obj_json_list

    async def create_all_strat_alert_pre(self, strat_alert_obj_list: List[StratAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_all_strat_alert_pre not ready - service is not initialized yet"
            self.portfolio_alert_fail_logger.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def delete_portfolio_alert_post(self, delete_web_response):
        portfolio_alert = self.portfolio_alert_id_to_obj_dict.get(delete_web_response.id)
        component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(portfolio_alert)
        alert_key = get_alert_cache_key(portfolio_alert.severity, portfolio_alert.alert_brief,
                                        component_file_path, source_file_name, line_num)
        self.portfolio_alerts_cache_dict.pop(alert_key, None)
        self.portfolio_alert_id_to_obj_dict.pop(delete_web_response.id, None)

    async def delete_strat_alert_post(self, delete_web_response):
        strat_alert = self.strat_alert_id_to_obj_dict.get(delete_web_response.id)
        strat_alert_cache_dict = self.strat_alert_cache_dict_by_strat_id_dict.get(strat_alert.strat_id)
        component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(strat_alert)
        alert_key = get_alert_cache_key(strat_alert.severity, strat_alert.alert_brief,
                                        component_file_path, source_file_name, line_num)
        strat_alert_cache_dict.pop(alert_key, None)
        self.strat_alert_id_to_obj_dict.pop(delete_web_response.id, None)

    async def delete_all_strat_alert_post(self, delete_web_response):
        self.strat_alert_cache_dict_by_strat_id_dict.clear()
        self.strat_alert_id_to_obj_dict.clear()
        # updating strat_view fields
        photo_book_service_http_client.reset_all_strat_view_count_n_severity_query_client()

    async def verify_strat_alert_id_in_strat_alert_id_to_obj_cache_dict_query_pre(
            self, strat_alert_id_to_obj_cache_class_type: Type[StratAlertIdToObjCache], strat_alert_id: int):
        is_id_present = strat_alert_id in self.strat_alert_id_to_obj_dict
        return [StratAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_portfolio_alert_id_in_get_portfolio_alert_id_to_obj_cache_dict_query_pre(
            self, portfolio_alert_id_to_obj_cache_class_type: Type[PortfolioAlertIdToObjCache],
            portfolio_alert_id: int):
        is_id_present = portfolio_alert_id in self.portfolio_alert_id_to_obj_dict
        return [PortfolioAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_strat_id_in_strat_alert_cache_dict_by_strat_id_dict_query_pre(
            self, _: Type[StratIdInStratAlertCacheDictByStratIdDict], strat_id: int):
        is_id_present = strat_id in self.strat_alert_cache_dict_by_strat_id_dict
        return [StratIdInStratAlertCacheDictByStratIdDict(is_id_present=is_id_present)]

    async def verify_strat_alert_id_in_strat_alert_cache_dict_by_strat_id_dict_query_pre(
            self, strat_alert_cache_dict_by_strat_id_dict_class_type: Type[StratAlertCacheDictByStratIdDict],
            strat_id: int, strat_cache_key: str):
        is_key_present = False
        strat_alert_cache_dict = self.strat_alert_cache_dict_by_strat_id_dict.get(strat_id)
        if strat_alert_cache_dict is not None:
            is_key_present = strat_cache_key in strat_alert_cache_dict
        return [StratAlertCacheDictByStratIdDict(is_key_present=is_key_present)]

    async def verify_portfolio_alerts_cache_dict_query_pre(
            self, portfolio_alert_cache_dict_class_type: Type[PortfolioAlertCacheDict], strat_cache_key: str):
        is_key_present = strat_cache_key in self.portfolio_alerts_cache_dict
        return [PortfolioAlertCacheDict(is_key_present=is_key_present)]

    async def strat_view_update_handling(self, strat_alert_obj_list: List[StratAlert]):
        updated_strat_id_set = set()
        for updated_strat_alert_obj in strat_alert_obj_list:
            updated_strat_id_set.add(updated_strat_alert_obj.strat_id)

        for updated_strat_id in updated_strat_id_set:
            strat_view_update_cont: StratViewUpdateCont = \
                await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_alert_http(
                    get_total_strat_alert_count_n_highest_severity(updated_strat_id),
                    projection_read_http, StratViewUpdateCont)

            if strat_view_update_cont is not None:
                strat_alert_aggregated_severity = strat_view_update_cont.highest_priority_severity
                strat_alert_count = strat_view_update_cont.total_objects

                update_json = {"_id": updated_strat_id,
                               "strat_alert_aggregated_severity": strat_alert_aggregated_severity,
                               "strat_alert_count": strat_alert_count}
                payload_dict = {"update_json_list": [update_json], "update_type": UpdateType.SNAPSHOT_TYPE,
                                "pydantic_basemodel_type_name": StratViewBaseModel.__name__,
                                "method_name": "patch_all_strat_view_client"}
                photo_book_service_http_client.process_strat_view_updates_query_client(payload_dict)
            # else not required: if no data is in db - no handling

    async def update_all_strat_alert_post(self, stored_strat_alert_obj_list: List[StratAlert],
                                          updated_strat_alert_obj_list: List[StratAlert]):
        await self.strat_view_update_handling(updated_strat_alert_obj_list)

    async def create_all_strat_alert_post(self, strat_alert_obj_list: List[StratAlert]):
        await self.strat_view_update_handling(strat_alert_obj_list)

    async def log_book_restart_tail_query_pre(
            self, log_book_restart_tail_class_type: Type[LogBookRestartTail], log_file_name: str,
            start_timestamp: str):
        try:
            pendulum.parse(start_timestamp)     # checking if passed value is parsable
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Couldn't parse start_datetime, exception: {e}")

        # first killing process
        await (LogBookServiceRoutesCallbackBaseNativeOverride.
               underlying_log_book_force_kill_tail_executor_query_http(
                log_file_name))

        # updating multiprocess queue to again start tail executor for log detail but from specific time
        log_details: List[StratLogDetail] = self.file_path_to_log_detail_cache_dict.get(log_file_name)

        if log_details:
            self.file_path_to_log_detail_cache_dict.pop(log_file_name)

            for log_detail in log_details:
                # updating tail_details for this log_file to restart it from logged timestamp
                log_detail.processed_timestamp = start_timestamp
                log_detail.is_running = False

                self.tail_file_multiprocess_queue.put(log_detail)
        else:
            logging.warning("Can't find log_file_name in file_path_to_log_detail_cache_dict - ignoring restart, "
                            f"{log_file_name=}, {start_timestamp=}")
        return []

    async def log_book_force_kill_tail_executor_query_pre(
            self, log_book_force_kill_tail_executor_class_type: Type[LogBookForceKillTailExecutor],
            log_file_path: str):
        """terminates all tail executors running for passed file_path"""

        tail_executor_process_list: List[multiprocessing.Process] = (
            self.file_path_to_tail_executor_process_cache_dict.get(log_file_path))

        if tail_executor_process_list:
            for tail_executor_process in tail_executor_process_list:
                tail_executor_process.terminate()
                tail_executor_process.join()
            self.file_path_to_tail_executor_process_cache_dict.pop(log_file_path)
        else:
            # keeping log as info since from tests this query is used in clean_n_set_limits - it's expected
            # to call this with no tail executor running with passed log_file_path
            logging.info(f"Ignoring Force Kill tail executor - Can't find any tail_executor proces for "
                         f"file: {log_file_path} in {self.file_path_to_tail_executor_process_cache_dict=}")
        return []

    async def dismiss_strat_alert_by_brief_str_query_pre(
            self, dismiss_strat_alert_by_brief_str_class_type: Type[DismissStratAlertByBriefStr],
            strat_id: int, brief_str: str):
        strat_alerts: List[StratAlert] = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_alert_http(
                get_strat_alert_from_strat_id_n_alert_brief_regex(strat_id, brief_str))

        for strat_alert in strat_alerts:
            strat_alert.dismiss = True
        updated_strat_alerts = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_strat_alert_http(
                strat_alerts)
        return updated_strat_alerts

    async def log_book_remove_file_from_created_cache_query_pre(
            self, log_book_remove_file_from_created_cache_class_type: Type[LogBookRemoveFileFromCreatedCache],
            log_file_path_list: List[str]):
        for log_file_path in log_file_path_list:
            # consumer of this queue handles task to release cache for this file entry - logs error if file
            # not found in cache
            self.clear_cache_file_path_queue.put(log_file_path)

            # clearing file_path_to_log_detail_cache_dict so that if next tail_executor starts with same file_path
            # it doesn't already have entries for file_path
            self.file_path_to_log_detail_cache_dict.pop(log_file_path, None)

        return []

    async def filtered_strat_alert_by_strat_id_query_pre(
            self, strat_alert_class_type: Type[StratAlert], strat_id: int, limit_obj_count: int | None = None):
        agg_pipeline = {"agg": sort_alerts_based_on_severity_n_last_update_analyzer_time(strat_id, limit_obj_count)}
        filtered_strat_alerts = \
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_alert_http(agg_pipeline)
        return filtered_strat_alerts

    async def filtered_strat_alert_by_strat_id_query_ws_pre(self, *args):
        if len(args) != 2:
            err_str_ = ("filtered_strat_alert_by_strat_id_query_ws_pre failed: received inappropriate *args to be "
                        f"used in agg pipeline to sort strat_alert based on severity and date_time - "
                        f"received {args=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=404)

        filter_agg_pipeline = sort_alerts_based_on_severity_n_last_update_analyzer_time(args[0], args[-1])
        return filtered_strat_alert_by_strat_id_query_callable, filter_agg_pipeline

    async def remove_strat_alerts_for_strat_id_query_pre(
            self, remove_strat_alerts_for_strat_id_class_type: Type[RemoveStratAlertsForStratId], strat_id: int):
        strat_alerts = \
            await (LogBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_filtered_strat_alert_by_strat_id_query_http(strat_id))

        # todo: introduce bulk delete with id list and replace looped deletion here
        strat_alert: StratAlert
        for strat_alert in strat_alerts:
            await LogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_alert_http(strat_alert.id)
            self.strat_alert_id_to_obj_dict.pop(strat_alert.id, None)

        # releasing cache for strat id
        self.strat_alert_cache_dict_by_strat_id_dict.pop(strat_id, None)

        # updating strat_view fields
        # await self._strat_view_update_handling(strat_id)
        update_json = {"_id": strat_id,
                       "strat_alert_aggregated_severity": Severity.Severity_UNSPECIFIED,
                       "strat_alert_count": 0}
        payload_dict = {"update_json_list": [update_json], "update_type": UpdateType.SNAPSHOT_TYPE,
                        "pydantic_basemodel_type_name": StratViewBaseModel.__name__,
                        "method_name": "patch_all_strat_view_client"}
        photo_book_service_http_client.process_strat_view_updates_query_client(payload_dict)

        return []

    async def portfolio_alert_fail_logger_query_pre(
            self, portfolio_alert_fail_logger_class_type: Type[PortfolioAlertFailLogger], log_msg: str):
        # logs msg to portfolio alert fail logs - listener mails if any log is found
        self.portfolio_alert_fail_logger.error(log_msg)
        return []

    def trigger_self_terminate(self):
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

    async def shutdown_log_book_query_pre(self, shut_down_log_book_class_type: Type[ShutDownLogBook]):
        Thread(target=self.trigger_self_terminate, daemon=True).start()
        return []


def filtered_strat_alert_by_strat_id_query_callable(strat_alert_obj_json_str: str, **kwargs):
    strat_id: int = kwargs.get('strat_id')
    if strat_id is None:
        err_str_ = ("filtered_strat_alert_by_strat_id_query_callable failed: received inappropriate **kwargs to be "
                    f"used to compare strat_alert_json_obj in ws broadcast - received {strat_alert_obj_json_str=}, "
                    f"{kwargs=}")
        logging.error(err_str_)
        raise HTTPException(detail=err_str_, status_code=404)

    strat_alert_obj_json_data = json.loads(strat_alert_obj_json_str)

    if isinstance(strat_alert_obj_json_data, list):
        res_json_list = []
        for strat_alert_obj_json in strat_alert_obj_json_data:
            if strat_alert_obj_json.get('strat_id') == strat_id:
                res_json_list.append(strat_alert_obj_json)
        if res_json_list:
            return json.dumps(res_json_list)
    elif isinstance(strat_alert_obj_json_data, dict):
        if strat_alert_obj_json_data.get('strat_id') == strat_id:
            return json.dumps(strat_alert_obj_json_data)
    else:
        logging.error("Unsupported DataType found in filtered_strat_alert_by_strat_id_query_callable: "
                      f"{strat_alert_obj_json_str=}")

    return None


def strat_id_from_executor_log_file(file_name: str) -> int | None:
    # Using regex to extract the number
    number_pattern = re.compile(r'street_book_(\d+)_logs_\d{8}\.log')

    match = number_pattern.search(file_name)

    if match:
        extracted_number = match.group(1)
        return parse_to_int(extracted_number)
    return None