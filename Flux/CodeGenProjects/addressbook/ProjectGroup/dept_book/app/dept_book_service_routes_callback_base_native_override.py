from pendulum import DateTime
from threading import Thread
import time

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.Pydentic.dept_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_routes_callback_imports import \
    DeptBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.dept_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.aggregate import \
      (get_vwap_projection_from_bar_data_agg_pipeline, get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline,
       get_vwap_change_projection_from_bar_data_agg_pipeline, get_premium_projection_from_bar_data_agg_pipeline,
       get_premium_n_premium_change_projection_from_bar_data_agg_pipeline,
       get_premium_change_projection_from_bar_data_agg_pipeline)
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState


class DeptBookServiceRoutesCallbackBaseNativeOverride(DeptBookServiceRoutesCallback):

    underlying_read_bar_data_http: Callable[Any, Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_http_msgspec_routes import underlying_read_bar_data_http
        cls.underlying_read_bar_data_http = underlying_read_bar_data_http

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"dept_book_{dsb_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                    print(f"INFO: dept_book service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_all_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

            else:
                should_sleep = True

    def app_launch_pre(self):
        DeptBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = dsb_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

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

    async def search_n_update_dash_query_pre(self, dash_class_type: Type[Dash], payload_dict: Dict[str, Any]):
        # To be implemented in main callback override file
        dash = payload_dict.get("dash")
        dash['rt_dash']["cb_leg"] = {"sec": {"sec_id": "check_cb_sec"}}
        dash['rt_dash']["eqt_leg"] = {"sec": {"sec_id": "check_eqt_sec"}}
        dash_obj = dash_class_type(**dash)
        return [dash_obj]

    async def get_vwap_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                          exch_id: str, start_date_time: DateTime | None = None,
                                                          end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwap)
        return bar_data_projection_list

    async def get_vwap_projection_from_bar_data_query_ws_pre(self):
        return get_vwap_projection_from_bar_data_filter_callable, get_vwap_projection_from_bar_data_agg_pipeline

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                        symbol: str, exch_id: str,
                                                                        start_date_time: DateTime | None = None,
                                                                        end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                         end_date_time), projection_read_http,
            projection_model=BarDataProjectionContainerForVwapNVwapChange)
        return bar_data_projection_list

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_n_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_vwap_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                                 exch_id: str, start_date_time: DateTime | None = None,
                                                                 end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwapChange)
        return bar_data_projection_list

    async def get_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                             exch_id: str, start_date_time: DateTime | None = None,
                                                             end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremium)
        return bar_data_projection_list

    async def get_premium_projection_from_bar_data_query_ws_pre(self):
        return get_premium_projection_from_bar_data_filter_callable, get_premium_projection_from_bar_data_agg_pipeline

    async def get_premium_n_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                              symbol: str, exch_id: str,
                                                                              start_date_time: DateTime | None = None,
                                                                              end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time,
                                                                               end_date_time), projection_read_http,
            projection_model=BarDataProjectionContainerForPremiumNPremiumChange)
        return bar_data_projection_list

    async def get_premium_n_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_n_premium_change_projection_from_bar_data_filter_callable,
                get_premium_n_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_change_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData],
                                                                    symbol: str, exch_id: str,
                                                                    start_date_time: DateTime | None = None,
                                                                    end_date_time: DateTime | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremiumChange)
        return bar_data_projection_list

    async def get_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_change_projection_from_bar_data_filter_callable,
                get_premium_change_projection_from_bar_data_agg_pipeline)


def get_vwap_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


def get_vwap_n_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


def get_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


def get_premium_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


def get_premium_n_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


def get_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str

