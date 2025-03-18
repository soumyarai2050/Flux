from pendulum import DateTime
from threading import Thread
import time
import logging

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.ORMModel.dept_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_routes_callback_imports import (
    DeptBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.dept_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_new_contact_limits)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.app.aggregate import *
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState


class DeptBookServiceRoutesCallbackBaseNativeOverride(DeptBookServiceRoutesCallback):
    underlying_read_contact_limits_http_json_dict: Callable[..., Any] | None = None
    underlying_create_contact_limits_http: Callable[..., Any] | None = None
    underlying_read_dash_filters_collection_http_json_dict: Callable[..., Any] | None = None
    underlying_create_dash_filters_collection_http: Callable[..., Any] | None = None
    underlying_read_dash_collection_by_id_http: Callable[..., Any] | None = None
    underlying_create_dash_collection_http: Callable[..., Any] | None = None
    underlying_update_dash_collection_http: Callable[..., Any] | None = None
    underlying_read_bar_data_http: Callable[Any, Any] | None = None
    underlying_read_dash_filters_http: Callable[Any, Any] | None = None
    underlying_read_dash_http: Callable[Any, Any] | None = None
    underlying_filtered_dash_by_dash_filters_query_http: Callable[Any, Any] | None = None

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
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.dept_book.generated.FastApi.dept_book_service_http_msgspec_routes import (
            underlying_read_contact_limits_http_json_dict, underlying_create_contact_limits_http,
            underlying_read_dash_filters_collection_http_json_dict, underlying_create_dash_filters_collection_http,
            underlying_read_dash_collection_by_id_http, underlying_create_dash_collection_http,
            underlying_update_dash_collection_http, underlying_read_bar_data_http, underlying_read_dash_filters_http,
            underlying_read_dash_http, underlying_filtered_dash_by_dash_filters_query_http)
        cls.underlying_read_contact_limits_http_json_dict = underlying_read_contact_limits_http_json_dict
        cls.underlying_create_contact_limits_http = underlying_create_contact_limits_http
        cls.underlying_read_dash_filters_collection_http_json_dict = underlying_read_dash_filters_collection_http_json_dict
        cls.underlying_create_dash_filters_collection_http = underlying_create_dash_filters_collection_http
        cls.underlying_read_dash_collection_by_id_http = underlying_read_dash_collection_by_id_http
        cls.underlying_create_dash_collection_http = underlying_create_dash_collection_http
        cls.underlying_update_dash_collection_http = underlying_update_dash_collection_http
        cls.underlying_read_bar_data_http = underlying_read_bar_data_http
        cls.underlying_read_dash_filters_http = underlying_read_dash_filters_http
        cls.underlying_read_dash_http = underlying_read_dash_http
        cls.underlying_filtered_dash_by_dash_filters_query_http = underlying_filtered_dash_by_dash_filters_query_http

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
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
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: dept_book service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_all_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            run_coro = self._check_and_create_start_up_models()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                            try:
                                # block for task to finish
                                self.service_up = future.result()
                                should_sleep = False
                            except Exception as e:
                                err_str_ = (f"_check_and_create_contact_status_and_chore_n_contact_limits "
                                            f"failed with exception: {e}")
                                logging.exception(err_str_)
                                raise Exception(err_str_)
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

    @staticmethod
    async def _check_and_create_start_up_models() -> bool:
        try:
            await DeptBookServiceRoutesCallbackBaseNativeOverride._check_n_create_contact_limits()
            await DeptBookServiceRoutesCallbackBaseNativeOverride._check_n_create_dash_filters_collection()
        except Exception as e:
            logging.exception(f"_check_and_create_start_up_models failed, exception: {e}")
            return False
        else:
            return True

    @staticmethod
    async def _check_n_create_contact_limits():
        async with ContactLimits.reentrant_lock:
            contact_limits_list: List[Dict] = (
                await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_limits_http_json_dict())
            if 0 == len(contact_limits_list):  # no contact_limits set yet, create one
                contact_limits = get_new_contact_limits()
                await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_create_contact_limits_http(
                    contact_limits, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_dash_filters_collection():
        async with DashFiltersCollection.reentrant_lock:
            dash_filters_collection_list: List[Dict] = (
                await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_dash_filters_collection_http_json_dict())
            if len(dash_filters_collection_list) == 0:
                created_dash_filters_collection = DashFiltersCollection.from_kwargs(_id=1, loaded_dash_filters=[],
                                                                                    buffered_dash_filters=[])
                await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_create_dash_filters_collection_http(
                    created_dash_filters_collection, return_obj_copy=False)

    async def create_dash_filters_post(self, dash_filters_obj: DashFilters):
        try:
            dash_collection_obj: DashCollection = await (DeptBookServiceRoutesCallbackBaseNativeOverride.
                                                         underlying_read_dash_collection_by_id_http(dash_filters_obj.id))
            dash_collection_obj.dash_name = dash_filters_obj.dash_name
            dash_collection_obj.buffered_dashes = []
            await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_update_dash_collection_http(
                dash_collection_obj)
        except HTTPException as exp:  # does not exist - create new
            if exp.status_code == 404:
                dash_collection_obj: DashCollection = DashCollection.from_kwargs(
                    _id=dash_filters_obj.id, dash_name=dash_filters_obj.dash_name, buffered_dashes=[], loaded_dashes=[])
                await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_create_dash_collection_http(
                    dash_collection_obj)
            else:
                err_str_ = f"create_dash_collection failed in create_dash_filters_post, exception: {exp=}"
                logging.error(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)

    async def search_n_update_dash_query_pre(self, dash_class_type: Type[Dash], payload_dict: Dict[str, Any]):
        # To be implemented in main callback override file
        dash = payload_dict.get("dash")
        dash['rt_dash']["cb_leg"] = {"sec": {"sec_id": "check_cb_sec"}}
        dash['rt_dash']["eqt_leg"] = {"sec": {"sec_id": "check_eqt_sec"}}
        dash_obj = dash_class_type(**dash)
        return [dash_obj]

    async def get_vwap_projection_from_bar_data_query_pre(self, bar_data_class_type: Type[BarData], symbol: str,
                                                          exch_id: str, bar_type: BarType | None = None,
                                                          start_date_time: int | None = None,
                                                          end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwap)
        return bar_data_projection_list

    async def get_vwap_projection_from_bar_data_query_ws_pre(self):
        return get_vwap_projection_from_bar_data_filter_callable, get_vwap_projection_from_bar_data_agg_pipeline

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: BarType | None = None,
            start_date_time: int | None = None, end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, start_date_time,
                                                                         end_date_time), projection_read_http,
            projection_model=BarDataProjectionContainerForVwapNVwapChange)
        return bar_data_projection_list

    async def get_vwap_n_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_n_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_n_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_vwap_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: BarType | None = None,
            start_date_time: int | None = None, end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_vwap_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type,
                                                                  start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForVwapChange)
        return bar_data_projection_list

    async def get_vwap_change_projection_from_bar_data_query_ws_pre(self):
        return (get_vwap_change_projection_from_bar_data_filter_callable,
                get_vwap_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: BarType | None = None,
            start_date_time: int | None = None, end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type, start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremium)
        return bar_data_projection_list

    async def get_premium_projection_from_bar_data_query_ws_pre(self):
        return get_premium_projection_from_bar_data_filter_callable, get_premium_projection_from_bar_data_agg_pipeline

    async def get_premium_n_premium_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: BarType | None = None,
            start_date_time: int | None = None, end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_n_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type,
                                                                               start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremiumNPremiumChange)
        return bar_data_projection_list

    async def get_premium_n_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_n_premium_change_projection_from_bar_data_filter_callable,
                get_premium_n_premium_change_projection_from_bar_data_agg_pipeline)

    async def get_premium_change_projection_from_bar_data_query_pre(
            self, bar_data_class_type: Type[BarData], symbol: str, exch_id: str, bar_type: BarType | None = None,
            start_date_time: int | None = None, end_date_time: int | None = None):
        bar_data_projection_list = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_bar_data_http(
            get_premium_change_projection_from_bar_data_agg_pipeline(symbol, exch_id, bar_type,
                                                                     start_date_time, end_date_time),
            projection_read_http, projection_model=BarDataProjectionContainerForPremiumChange)
        return bar_data_projection_list

    async def get_premium_change_projection_from_bar_data_query_ws_pre(self):
        return (get_premium_change_projection_from_bar_data_filter_callable,
                get_premium_change_projection_from_bar_data_agg_pipeline)

    async def filtered_dash_by_dash_filters_query_pre(self, dash_class_type: Type[Dash], dash_name: str):
        dash_filters_list: List[DashFilters] = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_dash_filters_http(get_dash_filter_by_dash_name(dash_name))
        if dash_filters_list:
            dash_filters = dash_filters_list[0]

            dash_filter_agg_pipeline = filter_dash_from_dash_filters_agg(dash_filters)
            agg_pipeline = {"aggregate": dash_filter_agg_pipeline}
            filtered_dash_list = DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_dash_http(agg_pipeline)
            return filtered_dash_list

        return []

    async def filtered_dash_by_dash_filters_query_ws_pre(self, *args):
        dash_filters_list: List[DashFilters] = \
            await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_read_dash_filters_http(
                get_dash_filter_by_dash_name(args[0]))
        if dash_filters_list:
            dash_filters = dash_filters_list[0]

            dash_filter_agg_pipeline = filter_dash_from_dash_filters_agg(dash_filters)
        else:
            err_str_ = f"No dash_filter found with dash_name: {args[0]}"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=404)
        return self.filtered_dash_by_dash_filters_callable, dash_filter_agg_pipeline

    async def filtered_dash_by_dash_filters_callable(self, obj_json_str: str, **kwargs):
        data = await DeptBookServiceRoutesCallbackBaseNativeOverride.underlying_filtered_dash_by_dash_filters_query_http(kwargs.get("dash_name"))
        return_obj_bytes = msgspec.json.encode(data, enc_hook=Dash.enc_hook)
        return return_obj_bytes

async def get_vwap_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


async def get_vwap_n_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


async def get_vwap_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


async def get_premium_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


async def get_premium_n_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str


async def get_premium_change_projection_from_bar_data_filter_callable(bar_data_obj_json_str: str, **kwargs):
    return bar_data_obj_json_str

