# standard imports
import time
from threading import Thread

# project imports
from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_routes_msgspec_callback import (
    PerformanceBenchmarkServiceRoutesCallback)
from Flux.CodeGenProjects.performance_benchmark.app.performance_benchmark_helper import *
from FluxPythonUtils.scripts.utility_functions import except_n_log_alert, handle_refresh_configurable_data_members
from Flux.PyCodeGenEngine.FluxCodeGenCore.base_aggregate import get_raw_performance_data_from_callable_name_agg_pipeline


class PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride(PerformanceBenchmarkServiceRoutesCallback):
    underlying_read_raw_performance_data_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.performance_benchmark.generated.FastApi.performance_benchmark_service_http_msgspec_routes import underlying_read_raw_performance_data_http
        cls.underlying_read_raw_performance_data_http = underlying_read_raw_performance_data_http

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
                        # todo start RawPerformanceDataProcessor script once performance_benchmark service is up
                        self.service_ready = True
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
        self.initialize_underlying_http_callables()

        self.port = pb_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
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

    async def get_raw_performance_data_of_callable_query_pre(
            self, raw_performance_data_of_callable_class_type: Type[RawPerformanceDataOfCallable], callable_name: str):

        raw_performance_data_list = \
            await PerformanceBenchmarkServiceRoutesCallbackBaseNativeOverride.underlying_read_raw_performance_data_http(
                get_raw_performance_data_from_callable_name_agg_pipeline(callable_name), self.get_generic_read_route())

        raw_performance_data_of_callable = RawPerformanceDataOfCallable(raw_performance_data=raw_performance_data_list)

        return [raw_performance_data_of_callable]

