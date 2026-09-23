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

import msgspec
# 3rd party modules
import pendulum
import setproctitle
import pendulum.parsing.exceptions

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_plan_log_book.app.base_plan_log_book_service_routes_callback_base_native_override import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_log_book.generated.FastApi.phone_log_book_service_routes_callback_imports import PhoneLogBookServiceRoutesCallback
from FluxPythonUtils.scripts.general_utility_functions import (
    get_transaction_counts_n_timeout_from_config, get_symbol_side_pattern, except_n_log_alert,
    handle_refresh_configurable_data_members, ClientError)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_log_book.app.phone_log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import email_book_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import symbol_side_key, get_symbol_side_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import photo_book_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import StreetBookServiceHttpClient
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_plan_id_from_executor_log_file_name, get_symbol_n_side_from_log_line)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_msgspec_model import *

# standard imports
from datetime import datetime

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

debug_mode: bool = False if ((debug_env := os.getenv("PS_LOG_ANALYZER_DEBUG")) is None or
                             len(debug_env) == 0 or debug_env == "0") else True

plan_alert_bulk_update_counts_per_call, plan_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("plan_alert_config")))


class PlanViewUpdateCont(MsgspecBaseModel):
    total_objects: int | None = None
    highest_priority_severity: Severity | None = None

    @staticmethod
    def convert_ts_fields_in_db_fetched_dict(dict_obj: Dict):
        return dict_obj


is_view_server = os.environ.get('IS_VIEW_SERVER', False)

class PhoneLogBookServiceRoutesCallbackBaseNativeOverride(PhoneLogBookServiceRoutesCallback,
                                                                  BasePlanLogBookServiceRoutesCallbackBaseNativeOverride):
    underlying_delete_plan_alert_http: Callable[..., Any]


    def __init__(self):
        PhoneLogBookServiceRoutesCallback.__init__(self)
        self.symbol_side_pattern: str = get_symbol_side_pattern()
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.__init__(self, PlanAlert, config_yaml_dict, self.symbol_side_pattern)
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.service_up: bool = False
        self.service_ready = False
        self.plan_alerts_service_ready = False
        # timeout event
        self.model_type_name_to_patch_queue_cache_dict: Dict[str, Queue] = {}
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_db_updates")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value
        self.pattern_for_pair_plan_db_updates = get_pattern_for_pair_plan_db_updates()
        self.pattern_for_log_simulator = get_pattern_for_log_simulator()
        self.field_sep = get_field_seperator_pattern()
        self.key_val_sep = get_key_val_seperator_pattern()
        self.port_to_executor_web_client: Dict[int, StreetBookServiceHttpClient] = {}

        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        threading.Thread(target=self.handle_pos_disable_from_plan_id_log_queue, args=(get_plan_id_from_executor_log_file_name,), daemon=True).start()
        threading.Thread(target=self.handle_pos_disable_from_symbol_side_log_queue, args=(get_symbol_n_side_from_log_line,), daemon=True).start()


    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_log_book.generated.FastApi.phone_log_book_service_http_routes_imports import (
            underlying_read_plan_alert_http, underlying_delete_by_id_list_plan_alert_http,
            underlying_create_all_plan_alert_http,
            underlying_update_all_plan_alert_http, underlying_delete_plan_alert_http,
            underlying_handle_plan_alerts_with_symbol_side_query_http,
            underlying_handle_plan_alerts_with_plan_id_query_http,
            underlying_read_plan_alert_http_json_dict)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_alert_http = (
            underlying_create_all_plan_alert_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_alert_http = (
            underlying_update_all_plan_alert_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http = (
            underlying_read_plan_alert_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http_json_dict = (
            underlying_read_plan_alert_http_json_dict)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_plan_alert_http = (
            underlying_delete_plan_alert_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_by_id_list_alert_http = (
            underlying_delete_by_id_list_plan_alert_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_symbol_side_query_http = (
            underlying_handle_plan_alerts_with_symbol_side_query_http)
        BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_plan_id_query_http = (
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
            service_up_flag_env_var = os.environ.get(f"phone_log_book_{self.port}")

            if not no_activity_setup_timeout:
                if (DateTime.utcnow() - start_up_datetime).total_seconds() > self.no_activity_init_timeout:
                    no_activity_setup_timeout = True
                    logging.info("No activity setup timed-out - Starting no activity notify monitoring")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.run_queue_handler()

                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: pair_plan log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_phone_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        err_msg = ("Unexpected: service startup threw exception, "
                                   f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                   f";;;exception: {e}")
                        component_file_path = PurePath(__file__)
                        self.send_contact_alert(err_msg, "error", inspect.currentframe().f_lineno,
                                                  str(component_file_path), component_file_path.name, DateTime.now())
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

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
            service_up_flag_env_var = os.environ.get(f"phone_log_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: pair_plan log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_view_phone_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        err_str_ = (
                            "Unexpected: service startup threw exception, "
                            f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                            f";;;exception: {e}")
                        self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                                  str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
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

        self.port = psla_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

    def view_app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = psla_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override for view service")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # Exiting all started threads
        self.plan_alert_queue.put("EXIT")
        for _, queue_ in self.model_type_name_to_patch_queue_cache_dict.items():
            queue_.put("EXIT")

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

    async def enable_disable_plan_alert_create_query_pre(
            self, enable_disable_plan_alert_create_class_type: Type[EnableDisablePlanAlertCreate],
            payload: List[Dict[str, Any]]):
        return await self._enable_disable_plan_alert_create_query_pre(payload)

    def _force_kill_executor(self, plan_id: int):
        pair_plan = email_book_service_http_client.get_pair_plan_client(plan_id)
        pid = get_pid_from_port(pair_plan.port)
        if pid is not None:
            symbol_side_key_ = get_symbol_side_key([(pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                     pair_plan.pair_plan_params.plan_leg1.side),
                                                    (pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                     pair_plan.pair_plan_params.plan_leg2.side)])
            log_msg: str = (f"Triggering force kill executor for {plan_id=}, killing {pid=}, {symbol_side_key_} "
                            f"{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator}{pair_plan=}")
            logging.critical(log_msg)
            component_file_path = PurePath(__file__)
            self.send_plan_alert(log_msg, "critical", inspect.currentframe().f_lineno,
                                  str(component_file_path), component_file_path.name)

            os.kill(pid, signal.SIGKILL)
        else:
            logging.exception(f"_force_kill_street_book failed, no pid found for pair_plan with {plan_id=};;;"
                              f"{pair_plan=}")

    def update_loaded_plan_id_by_symbol_side_dict_with_loaded_plans(self):
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

    def run_queue_handler(self):
        plan_alert_handler_thread = Thread(target=self._handle_plan_alert_queue,
                                            args=(PlanAlert, AlertMeta, plan_alert_bulk_update_timeout,
                                                  plan_alert_bulk_update_counts_per_call,
                                                  get_symbol_n_side_from_log_line,
                                                  get_plan_id_from_executor_log_file_name), daemon=True)
        plan_alert_handler_thread.start()

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
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(detail=err_str_, status_code=500)

    async def update_all_plan_alert_pre(self, updated_plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_all_plan_alert_pre not ready - service is not initialized yet"
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_list

    async def update_plan_alert_pre(self, updated_plan_alert_obj: PlanAlert):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"update_plan_alert_pre not ready - service is not initialized yet"
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj

    async def partial_update_plan_alert_pre(self, stored_plan_alert_obj: PlanAlert,
                                             updated_plan_alert_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_plan_alert_pre not ready - service is not initialized yet"
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_json

    async def partial_update_all_plan_alert_pre(self, stored_plan_alert_obj_list: List[PlanAlert],
                                                 updated_plan_alert_obj_json_list: List[Dict]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"partial_update_all_plan_alert_pre not ready - service is not initialized yet"
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(status_code=503, detail=err_str_)

        return updated_plan_alert_obj_json_list

    async def create_all_plan_alert_pre(self, plan_alert_obj_list: List[PlanAlert]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_all_plan_alert_pre not ready - service is not initialized yet"
            self.send_contact_alert(err_str_, "error", inspect.currentframe().f_lineno,
                                      str(PurePath(__file__)), PurePath(__file__).name, DateTime.utcnow())
            raise HTTPException(status_code=503, detail=err_str_)

    async def delete_all_plan_alert_post(self, delete_web_response):
        # updating plan_view fields
        photo_book_service_http_client.reset_all_plan_view_count_n_severity_query_client()

    async def verify_plan_alert_id_in_plan_alert_cache_dict_by_plan_id_dict_query_pre(
            self, plan_alert_cache_dict_by_plan_id_dict_class_type: Type[PlanAlertCacheDictByPlanIdDict],
            payload: Dict[str, Any]):
        # This query uses local cache so to avoid call from view server this query is kept as PATCH type
        is_key_present = False
        async with self.loaded_unload_plan_list_async_rlock:
            plan_id = parse_to_int(payload.get("plan_id"))
            plan_cache_key = payload.get("plan_cache_key")
            plan_alert_cache_dict = self.plan_alert_cache_dict_by_plan_id_dict.get(plan_id)
            if plan_alert_cache_dict is not None:
                is_key_present = plan_cache_key in plan_alert_cache_dict
            return [PlanAlertCacheDictByPlanIdDict(is_key_present=is_key_present)]

    async def plan_view_update_handling(self, plan_alert_obj_list: List[PlanAlert]):
        updated_plan_id_set = set()
        for updated_plan_alert_obj in plan_alert_obj_list:
            updated_plan_id_set.add(updated_plan_alert_obj.plan_id)

        for updated_plan_id in updated_plan_id_set:
            plan_view_update_cont: PlanViewUpdateCont = \
                await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_alert_http(
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
            payload: Dict[str, Any]):
        return await self._dismiss_plan_alert_by_brief_str_query_pre(payload)

    async def filtered_plan_alert_by_plan_id_query_pre(
            self, plan_alert_class_type: Type[PlanAlert], plan_id: int, limit_obj_count: int | None = None,
            filters: List[Dict[str, Any]] | None = None, sort_chore: List[Dict[str, Any]] | None = None,
            pagination: Dict[str, Any] | None = None):
        return await self._filtered_plan_alert_by_plan_id_query_pre(
            PlanAlert, plan_id, limit_obj_count, filters, sort_chore, pagination)

    async def filtered_plan_alert_by_plan_id_query_ws_pre(self, *args):
        return await self._filtered_plan_alert_by_plan_id_query_ws_pre(PlanAlert, *args)

    async def read_all_ws_plan_alert_pre(self):
        pass

    async def shutdown_log_analyzer_query_pre(self, shut_down_log_analyzer_class_type: Type[ShutDownLogAnalyzer]):
        Thread(target=self.trigger_self_terminate, daemon=True).start()
        return []

    async def plan_state_update_matcher_for_symbol_side_log_query_pre(
            self,
            plan_state_update_matcher_for_symbol_side_log_class_type: Type[PlanStateUpdateMatcherForSymbolSideLog],
            payload: List[Dict[str, Any]]):
        return await self._plan_state_update_matcher_for_symbol_side_log_query_pre(payload, get_symbol_n_side_from_log_line)

    async def plan_state_update_matcher_for_plan_id_log_query_pre(
            self,
            plan_state_update_matcher_for_plan_id_log_class_type: Type[PlanStateUpdateMatcherForPlanIdLog],
            payload: List[Dict[str, Any]]):
        return await self._plan_state_update_matcher_for_plan_id_log_query_pre(payload, get_plan_id_from_executor_log_file_name)

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

            executor_client = self._get_executor_http_client_from_pair_plan(port, host)
            callback_method = getattr(executor_client, method_name)
            callback_method(**kwargs)
            logging.info(f"Called {method_name} with kwargs: {kwargs}")
        return []

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
                            f"{BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} exception: {e}")
            self.send_contact_alert(err_msg, "critical", inspect.currentframe().f_lineno,
                                      str(component_file_name), PurePath(__file__).name, DateTime.utcnow())

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

    async def handle_pos_disable_from_symbol_side_log_query_pre(
            self, handle_pos_disable_from_symbol_side_log_class_type: Type[HandlePosDisableFromSymbolSideLog],
            payload: List[Dict[str, Any]]):
        return self._handle_pos_disable_from_symbol_side_log_query_pre(payload)

    async def dummy_pos_disable_check(self, plan_id: int):
        pair_plan = email_book_service_http_client.get_pair_plan_client(plan_id)
        port = pair_plan.port
        host = pair_plan.host
        executor_client = self._get_executor_http_client_from_pair_plan(port, host)

        plan_limits = executor_client.get_plan_limits_client(pair_plan.id)
        logging.info(f"{plan_limits=}")
        updated_plan_limits = executor_client.patch_plan_limits_client({"_id": plan_id,
                                                                          "max_open_chores_per_side": plan_limits.max_open_chores_per_side + 1})
        logging.info(f"{updated_plan_limits=}")

    async def handle_pos_disable_from_plan_id_log_query_pre(
            self, handle_pos_disable_from_plan_id_log_class_type: Type[HandlePosDisableFromPlanIdLog],
            payload: List[Dict[str, Any]]):
        return self._handle_pos_disable_from_plan_id_log_query_pre(payload)

    async def handle_plan_pause_from_plan_id_log_query_pre(
            self, handle_plan_pause_from_plan_id_log_class_type: Type[HandlePlanPauseFromPlanIdLog],
            payload: List[Dict[str, Any]]):
        # Adding alert for original payload
        await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_plan_id_query_http(
            payload)

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

    async def dismiss_all_plan_alert_by_plan_id_query_pre(self, plan_alert_class_type: Type[PlanAlert],
                                                            plan_id: int):
        await self._dismiss_all_plan_alert_by_plan_id_query_pre(plan_alert_class_type, plan_id)

    async def handle_plan_pause_from_symbol_side_log_query_pre(
            self, handle_plan_pause_from_symbol_side_log_class_type: Type[HandlePlanPauseFromSymbolSideLog],
            payload: List[Dict[str, Any]]):
        async with self.loaded_unload_plan_list_async_rlock:

            # Adding alert for original payload
            await BasePlanLogBookServiceRoutesCallbackBaseNativeOverride.underlying_handle_alerts_with_symbol_side_query_http(
                payload)

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

    async def get_filtered_plan_alert_count_query_pre(self, plan_alert_class_type: Type[PlanAlert],
                                                       filter_kwargs: List[Dict[str, Any]]):
        return await self._get_filtered_plan_alert_count_query_pre(plan_alert_class_type, filter_kwargs)

    async def get_filtered_plan_alert_count_query_ws_pre(self, *args):
        return self._get_filtered_plan_alert_count_query_ws_pre()

    async def get_filtered_plan_alert_count_query_ws_callable(self, **kwargs):
        return self._get_filtered_plan_alert_count_query_ws_callable()


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
