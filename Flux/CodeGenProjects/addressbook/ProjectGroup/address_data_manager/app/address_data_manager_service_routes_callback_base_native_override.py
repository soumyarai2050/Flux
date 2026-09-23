from pendulum import DateTime
from threading import Thread
import time
import logging
from typing import Callable, Any
import asyncio
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.generated.ORMModel.address_data_manager_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.app.address_data_manager_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_new_contact_limits)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.app.aggregate import *
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.generated.FastApi.address_data_manager_service_routes_callback_imports import AddressDataManagerServiceRoutesCallback
from Flux.PyCodeGenEngine.FluxCodeGenCore.generic_msgspec_routes import projection_read_http


class AddressDataManagerServiceRoutesCallbackBaseNativeOverride(AddressDataManagerServiceRoutesCallback):
    underlying_read_bar_data_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.address_data_manager.generated.FastApi.address_data_manager_service_http_routes_imports import (
            underlying_read_bar_data_http)
        cls.underlying_read_bar_data_http = underlying_read_bar_data_http

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI address_data_manager
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"address_data_manager_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: address_data_manager service is ready: {datetime.datetime.now().time()}")

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

    @except_n_log_alert()
    def _view_app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI address_data_manager
        should_sleep: bool = False
        mongo_stream_started = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"address_data_manager_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: address_data_manager view service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_all_view_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    if not mongo_stream_started:
                        Thread(target=self.start_mongo_streamer, daemon=True).start()
                        mongo_stream_started = True

            else:
                should_sleep = True

    def start_mongo_streamer(self):
        run_coro = self._start_mongo_streamer()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"start_mongo_streamer failed with exception: {e}")

    def app_launch_pre(self):
        AddressDataManagerServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = dsb_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def view_app_launch_pre(self):
        AddressDataManagerServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        self.port = dsb_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered view server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    def view_app_launch_post(self):
        logging.debug("Triggered view server launch post override")

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

    async def get_vwap_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: str | None = None,
            symbol_type: str | None = None, ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type, ticker,
                                                           start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwap)
        return bar_data_projection_list

    async def get_vwap_projection_from_bar_data_query_ws_pre(self):
        return get_vwap_projection_from_bar_data_filter_callable, get_vwap_projection_from_bar_data_agg_pipeline

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str,
            bar_type: str | None = None, symbol_type: str | None = None,
            ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type, ticker,
                                                                         start_date_time, end_date_time),
            projection_read_http,
            projection_model=BarDataProjectionContainerForVwapNVwapChange)
        return bar_data_projection_list

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_n_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_vwap_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: str | None = None,
            symbol_type: str | None = None, ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type, ticker,
                                                                  start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwapChange)
        return bar_data_projection_list

    async def get_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: str | None = None,
            symbol_type: str | None = None, ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type, ticker,
                                                              start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremium)
        return bar_data_projection_list

    async def get_premium_projection_from_bar_data_query_ws_pre(self):
        return get_premium_projection_from_bar_data_filter_callable, get_premium_projection_from_bar_data_agg_pipeline

    async def get_premium_n_premium_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: str | None = None,
            symbol_type: str | None = None, ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type,
                                                                               ticker, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremiumNPremiumChange)
        return bar_data_projection_list

    async def get_premium_n_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_n_premium_change_projection_from_bar_data_filter_callable,
                get_premium_n_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: str | None = None,
            symbol_type: str | None = None, ticker: str | None = None, start_date_time: DateTime | None = None,
            end_date_time: DateTime | None = None):
        bar_data_projection_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, symbol_type, ticker,
                                                                     start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremiumChange)
        return bar_data_projection_list

    async def get_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_change_projection_from_bar_data_filter_callable,
                get_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_latest_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], exch_id_list: List[str] | None = None,
            bar_type_list: List[str] | None = None, start_time: pendulum.DateTime | None = None,
            end_time: pendulum.DateTime | None = None):
        bar_data_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_latest_bar_data_agg(exch_id_list, bar_type_list, start_time, end_time))
        return bar_data_list

    async def get_aggregated_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], target_bar_type: str, end_time: pendulum.DateTime | None = None,
            start_time: pendulum.DateTime | None = None, target_bar_counts: int | None = None,
            exch_id_list: List[str] | None = None, symbol_list: List[str] | None = None):
        bar_data_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_bar_aggregation_pipeline(target_bar_type, end_time, start_time, target_bar_counts,
                                         exch_id_list, symbol_list))
        return bar_data_list

    async def filter_one_min_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], end_time: pendulum.DateTime | None = None,
            start_time: pendulum.DateTime | None = None, exch_id_list: List[str] | None = None,
            symbol_list: List[str] | None = None):
        bar_data_list = await AddressDataManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
                    filter_one_min_bar_data_agg(end_time, start_time, exch_id_list, symbol_list))
        return bar_data_list

    async def filter_one_min_bar_data_query_ws_pre(self, *args):
        pass

async def get_vwap_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")


async def get_vwap_n_vwap_change_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")


async def get_vwap_change_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")


async def get_premium_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")


async def get_premium_n_premium_change_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")


async def get_premium_change_projection_from_bar_data_filter_callable(**kwargs):
    return kwargs.get("json_obj_str")
