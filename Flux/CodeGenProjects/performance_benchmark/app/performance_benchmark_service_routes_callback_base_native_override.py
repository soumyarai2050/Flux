# standard imports
import logging
import queue
import time
from threading import Thread
import re

# project imports
from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_routes_msgspec_callback import (
    PerformanceBenchmarkServiceRoutesCallback)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import *
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert, handle_refresh_configurable_data_members, parse_to_float,
    get_transaction_counts_n_timeout_from_config)
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import get_raw_performance_data_from_callable_name_agg_pipeline
from Flux.PyCodeGenEngine.FluxCodeGenCore.perf_benchmark_decorators import (get_timeit_pattern,
                                                                            get_timeit_field_separator)
from Flux.CodeGenProjects.TradeEngine.ProjectGroup.log_analyzer.app.log_analyzer_service_helper import (
    alert_queue_handler_for_create_only)

class PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride(PerformanceBenchmarkServiceRoutesCallback):
    underlying_read_raw_performance_data_http: Callable[..., Any] | None = None
    underlying_create_all_raw_performance_data_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_http_msgspec_routes import (
            underlying_read_raw_performance_data_http, underlying_create_all_raw_performance_data_http)
        cls.underlying_read_raw_performance_data_http = underlying_read_raw_performance_data_http
        cls.underlying_create_all_raw_performance_data_http = underlying_create_all_raw_performance_data_http

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.timeit_pattern: str = get_timeit_pattern()
        self.timeit_field_separator: str = get_timeit_field_separator()
        self.raw_performance_data_queue: queue.Queue = queue.Queue()
        self.perf_benchmark_queue_handler_running_state: bool = True

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
            service_up_flag_env_var = os.environ.get(f"performance_benchmark_{pb_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        # running raw_performance thread
                        raw_performance_handler_thread = Thread(target=self._handle_raw_performance_data_queue,
                                                                daemon=True,
                                                                name="raw_performance_handler")
                        raw_performance_handler_thread.start()
                        logging.info(f"Thread Started: _handle_raw_performance_data_queue")

                        # todo start RawPerformanceDataProcessor script once performance_benchmark service is up
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: perf benchmark service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_performance_benchmark_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    def app_launch_pre(self):
        PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()

        self.port = pb_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        self.perf_benchmark_queue_handler_running_state: bool = True
        logging.debug("Triggered server launch post override")

    def get_generic_read_route(self):
        pass

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
            logging.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    async def create_raw_performance_data_pre(self, raw_performance_data_obj: RawPerformanceData):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_raw_performance_data_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def create_all_raw_performance_data_pre(self, raw_performance_data_obj_list: List[RawPerformanceData]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_all_raw_performance_data_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

    async def get_raw_performance_data_of_callable_query_pre(
            self, raw_performance_data_of_callable_class_type: Type[RawPerformanceDataOfCallable], callable_name: str):

        raw_performance_data_list = \
            await PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride.underlying_read_raw_performance_data_http(
                get_raw_performance_data_from_callable_name_agg_pipeline(callable_name), self.get_generic_read_route())

        raw_performance_data_of_callable = RawPerformanceDataOfCallable(raw_performance_data=raw_performance_data_list)

        return [raw_performance_data_of_callable]

    def create_all_raw_performance_data_async(self, obj_list):
        # updating alert cache
        run_coro = (PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride.
                    underlying_create_all_raw_performance_data_http(obj_list))
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block to finish task
        try:
            future.result()
        except Exception as e:
            logging.exception(f"load_alerts_n_update_cache failed with exception: {e}")
            raise e

    def _handle_raw_performance_data_queue(self):
        raw_performance_data_bulk_create_counts_per_call, raw_perf_data_bulk_create_timeout = (
            get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("raw_perf_data_config")))
        client_connection_fail_retry_secs = config_yaml_dict.get("perf_bench_client_connection_fail_retry_secs")
        if client_connection_fail_retry_secs:
            client_connection_fail_retry_secs = parse_to_int(client_connection_fail_retry_secs)
        alert_queue_handler_for_create_only(
            self.perf_benchmark_queue_handler_running_state, self.raw_performance_data_queue, raw_performance_data_bulk_create_counts_per_call,
            raw_perf_data_bulk_create_timeout,
            self.create_all_raw_performance_data_async,
            self.handle_raw_performance_data_queue_err_handler,
            client_connection_fail_retry_secs=client_connection_fail_retry_secs)

    def handle_raw_performance_data_queue_err_handler(self, *args):
        err_str_ = f"perf benchmark's create_all_raw_performance_data_client failed, {args=}"
        logging.error(err_str_)

    async def handle_perf_benchmark_query_pre(
            self, handle_perf_benchmark_class_type: Type[HandlePerfBenchmark], payload: List[Dict[str, Any]]):
        for log_data in payload:
            log_message = log_data.get("message")
            service = log_data.get("component_name")

            pattern = re.compile(f"{self.timeit_pattern}.*{self.timeit_pattern}")
            if search_obj := re.search(pattern, log_message):
                found_pattern = search_obj.group()
                found_pattern = found_pattern[8:-8]  # removing beginning and ending _timeit_
                found_pattern_list = found_pattern.split(self.timeit_field_separator)  # splitting pattern values
                if len(found_pattern_list) == 3:
                    callable_name, start_time, delta = found_pattern_list
                    if callable_name != "underlying_create_raw_performance_data_http":
                        raw_performance_data_obj = RawPerformanceDataBaseModel()
                        raw_performance_data_obj.callable_name = callable_name
                        raw_performance_data_obj.start_time = pendulum.parse(start_time)
                        raw_performance_data_obj.delta = parse_to_float(delta)
                        raw_performance_data_obj.project_name = service

                        self.raw_performance_data_queue.put(raw_performance_data_obj)
                        logging.debug(f"Created raw_performance_data entry in queue for callable {callable_name} "
                                      f"with start_datetime {start_time}")
                    # else not required: avoiding callable underlying_create_raw_performance_data to avoid infinite loop
                else:
                    err_str_: str = f"Found timeit pattern but internally only contains {found_pattern_list}, " \
                                    f"ideally must contain callable_name, start_time & delta " \
                                    f"seperated by '{self.timeit_field_separator}'"
                    logging.error(err_str_)
            else:
                err_str_ = f"Can't find perf benchmark related data in log data provided by caller;;; {payload=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []
