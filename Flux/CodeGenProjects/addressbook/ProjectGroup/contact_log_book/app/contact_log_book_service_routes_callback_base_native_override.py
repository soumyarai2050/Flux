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
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_log_book.app.base_log_book_service_routes_callback_base_native_override import *
from FluxPythonUtils.scripts.general_utility_functions import (
    get_transaction_counts_n_timeout_from_config, create_logger, except_n_log_alert,
    handle_refresh_configurable_data_members)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.ORMModel.contact_log_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.app.contact_log_book_service_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.FastApi.contact_log_book_service_routes_callback_imports import ContactLogBookServiceRoutesCallback


# standard imports
from datetime import datetime

LOG_ANALYZER_DATA_DIR = (
    PurePath(__file__).parent.parent / "data"
)

contact_alert_bulk_update_counts_per_call, contact_alert_bulk_update_timeout = (
    get_transaction_counts_n_timeout_from_config(config_yaml_dict.get("contact_alert_configs")))


is_view_server = os.environ.get('IS_VIEW_SERVER', False)

class ContactLogBookServiceRoutesCallbackBaseNativeOverride(ContactLogBookServiceRoutesCallback,
                                                                  BaseLogBookServiceRoutesCallbackBaseNativeOverride):
    underlying_read_contact_alert_http: Callable[..., Any] | None = None
    underlying_create_all_contact_alert_http: Callable[..., Any] | None = None
    underlying_update_all_contact_alert_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.asyncio_loop = None
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.service_up: bool = False
        self.service_ready = False
        self.contact_alerts_service_ready = False
        self.contact_alerts_cache_dict_async_rlock: AsyncRLock = AsyncRLock()
        self.contact_alerts_id_to_obj_cache_dict: Dict[int, ContactAlert] = {}
        self.contact_alerts_cache_dict: Dict[str, ContactAlert] = {}
        self.contact_alert_queue: Queue = Queue()
        # timeout event
        self.last_timeout_event_datetime: DateTime | None = None
        self.no_activity_timeout_secs: int | None = config_yaml_dict.get("no_activity_timeout_secs")
        self.market: Market = Market([MarketID.IN])
        self.max_fetch_from_queue = config_yaml_dict.get("max_fetch_from_patch_queue_for_db_updates")
        if self.max_fetch_from_queue is None:
            self.max_fetch_from_queue = 10  # setting default value

        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        if not is_view_server:
            self.contact_alert_fail_logger = create_logger("contact_alert_fail_logger", logging.DEBUG,
                                                             str(CURRENT_PROJECT_LOG_DIR), contact_alert_fail_log)

        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }

    def initialize_underlying_http_callables(self):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.contact_log_book.generated.FastApi.contact_log_book_service_http_routes_imports import (
            underlying_read_contact_alert_http, underlying_create_all_contact_alert_http,
            underlying_update_all_contact_alert_http)
        ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http = (
            underlying_read_contact_alert_http)
        ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http = (
            underlying_create_all_contact_alert_http)
        ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http = (
            underlying_update_all_contact_alert_http)

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
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"contact_log_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.run_queue_handler()

                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: contact view log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_contact_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
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
            service_up_flag_env_var = os.environ.get(f"contact_log_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: contact view log analyzer service is ready: {datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_view_contact_log_book_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
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

        self.port = pla_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override")

    def view_app_launch_pre(self):
        self.initialize_underlying_http_callables()

        self.port = pla_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

        logging.debug("Triggered server launch pre override for view service")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override, killing file_watcher and tail executor processes")

        # Exiting all started threads
        self.contact_alert_queue.put("EXIT")

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

    def _handle_contact_alert_queue_err_handler(self, *args):
        err_str_ = f"_handle_contact_alert_queue_err_handler called, passed args: {args}"
        self.contact_alert_fail_logger.exception(err_str_)

    async def load_contact_alerts_n_update_cache(self):
        try:
            async with ContactAlert.reentrant_lock:
                contact_alerts: List[ContactAlert] = await ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http()
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

    def update_create_n_update_contact_alerts_list_for_payload(
            self, log_payload: Dict, create_contact_alert_list: List[ContactAlert],
            upload_contact_alert_list: List[ContactAlert]):
        message = log_payload.get("message")
        source_file = log_payload.get("source_file")
        line_num = log_payload.get("line")
        log_date_time = log_payload.get("timestamp")
        log_source_file_name = log_payload.get("file")
        level = log_payload.get("level")

        alert_brief_n_detail_lists: List[str] = (
            message.split(ContactLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator, 1))
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
        severity: Severity = ContactLogBookServiceRoutesCallbackBaseNativeOverride.severity_map.get(level.lower())

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
                create_contact_alert_list: List[ContactAlert] = []
                update_contact_alert_list: List[ContactAlert] = []
                for log_payload in log_payload_list:
                    self.update_create_n_update_contact_alerts_list_for_payload(
                        log_payload, create_contact_alert_list, update_contact_alert_list)

                if create_contact_alert_list:

                    # handling create list
                    try:
                        contact_alerts_list = await ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http(create_contact_alert_list)
                        for contact_alert in contact_alerts_list:
                            self.contact_alerts_id_to_obj_cache_dict[contact_alert.id] = contact_alert
                    except HTTPException as http_e:
                        alert_queue_handler_err_handler(http_e.detail, create_contact_alert_list, self.contact_alert_queue,
                                                         self._handle_contact_alert_queue_err_handler,
                                                         ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http)
                    except Exception as e:
                        alert_queue_handler_err_handler(e, create_contact_alert_list, self.contact_alert_queue, self._handle_contact_alert_queue_err_handler,
                                                         ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_contact_alert_http)
                    create_contact_alert_list.clear()  # cleaning dict to start fresh cycle

                if update_contact_alert_list:

                    # handling create list
                    try:
                        contact_alerts_list = await ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http(update_contact_alert_list)
                        for contact_alert in contact_alerts_list:
                            self.contact_alerts_id_to_obj_cache_dict[contact_alert.id] = contact_alert
                    except HTTPException as http_e:
                        alert_queue_handler_err_handler(http_e.detail, update_contact_alert_list, self.contact_alert_queue,
                                                         self._handle_contact_alert_queue_err_handler,
                                                         ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http)
                    except Exception as e:
                        alert_queue_handler_err_handler(e, update_contact_alert_list, self.contact_alert_queue, self._handle_contact_alert_queue_err_handler,
                                                         ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http)
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

    def run_queue_handler(self):
        contact_alert_handler_thread = Thread(target=self._handle_contact_alert_queue, daemon=True)
        contact_alert_handler_thread.start()

    def send_contact_alert(self, message: str, log_lvl: str, line_num: int, component_path: str,
                             source_file: str, time_stamp: DateTime):
        log_payload = {"message": message, "source_file":component_path, "line": line_num,
                       "level": log_lvl, "file": source_file, "timestamp": time_stamp}
        self.contact_alert_queue.put([log_payload])

    def update_create_n_update_contact_alert_list(
            self, create_contact_alert_list: List[ContactAlert],
            upload_contact_alert_list: List[ContactAlert], severity: str, alert_brief: str,
            alert_meta: AlertMeta | None = None) -> None:
        logging.debug(f"sending contact alert with {severity=}, {alert_brief=}, {alert_meta=}")
        try:
            severity: Severity = get_severity_type_from_severity_str(severity_str=severity)
            create_or_update_alert(create_contact_alert_list, upload_contact_alert_list,
                                   self.contact_alerts_cache_dict,
                                   ContactAlert, severity, alert_brief,
                                   alert_meta=alert_meta, create_alert_method=create_contact_alert)
        except Exception as e:
            self.contact_alert_fail_logger.exception(
                f"update_create_n_update_contact_alert_list failed{ContactLogBookServiceRoutesCallbackBaseNativeOverride.log_seperator} exception: {e};;; "
                f"received: {severity=}, {alert_brief=}, {alert_meta=}")

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

    async def delete_contact_alert_post(self, delete_web_response):
        async with self.contact_alerts_cache_dict_async_rlock:
            contact_alert = self.contact_alerts_id_to_obj_cache_dict.get(delete_web_response.id)
            component_file_path, source_file_name, line_num = get_key_meta_data_from_obj(contact_alert)
            alert_key = get_alert_cache_key(contact_alert.severity, contact_alert.alert_brief,
                                            component_file_path, source_file_name, line_num)
            self.contact_alerts_cache_dict.pop(alert_key, None)
            self.contact_alerts_id_to_obj_cache_dict.pop(delete_web_response.id)

    async def verify_contact_alert_id_in_get_contact_alert_id_to_obj_cache_dict_query_pre(
            self, contact_alert_id_to_obj_cache_class_type: Type[ContactAlertIdToObjCache], payload: Dict[str, Any]):
        # This query uses local cache so to avoid call from view server this query is kept as PATCH type
        async with self.contact_alerts_cache_dict_async_rlock:
            contact_alert_id = parse_to_int(payload.get("contact_alert_id"))
            is_id_present = contact_alert_id in self.contact_alerts_id_to_obj_cache_dict
            return [ContactAlertIdToObjCache(is_id_present=is_id_present)]

    async def verify_contact_alerts_cache_dict_query_pre(
            self, contact_alert_cache_dict_class_type: Type[ContactAlertCacheDict], payload: Dict[str, Any]):
        # This query uses local cache so to avoid call from view server this query is kept as PATCH type
        async with self.contact_alerts_cache_dict_async_rlock:
            plan_cache_key = payload.get("plan_cache_key")
            is_key_present = plan_cache_key in self.contact_alerts_cache_dict
            return [ContactAlertCacheDict(is_key_present=is_key_present)]

    async def contact_alert_fail_logger_query_pre(
            self, contact_alert_fail_logger_class_type: Type[ContactAlertFailLogger], payload: Dict[str, Any]):
        # Logger is initialized in main server so keeping this query PATCH type to avoid call from view client
        # logs msg to contact alert fail logs - listener mails if any log is found
        log_msg = payload.get("log_msg")
        self.contact_alert_fail_logger.error(log_msg)
        return []

    def trigger_self_terminate(self):
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

    async def dismiss_all_contact_alerts_query_pre(self, contact_alert_class_type: Type[ContactAlert]):
        async with ContactAlert.reentrant_lock:
            existing_contact_alerts: List[ContactAlert] = await (
                ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http())

            for existing_contact in existing_contact_alerts:
                existing_contact.dismiss = True

            await ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_contact_alert_http(
                existing_contact_alerts)

    async def handle_contact_alerts_query_pre(self, handle_contact_alerts_class_type: Type[HandleContactAlerts],
                                                payload: List[Dict[str, Any]]):
        self.contact_alert_queue.put(payload)
        return []

    async def get_filtered_contact_alert_count_query_pre(
            self, filtered_doc_count_class_type: Type[FilteredDocCount], filter_kwargs: Dict):
        agg_pipeline = get_cascading_multi_filter_count_pipeline(ContactAlert, filter_kwargs)

        filtered_doc_count_list: List[FilteredDocCount] | None = \
            await ContactLogBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_alert_http(
                agg_pipeline, projection_read_http, FilteredDocCount)
        if filtered_doc_count_list is None:
            return []
        return filtered_doc_count_list

    def get_cascading_multi_filter_count_contact_alert_pipeline(self, filter_kwargs):
        agg_pipeline = get_cascading_multi_filter_count_pipeline(ContactAlert, filter_kwargs)
        return agg_pipeline

    async def get_filtered_contact_alert_count_query_ws_pre(self, *args):
        return self.get_filtered_contact_alert_count_query_ws_callable, self.get_cascading_multi_filter_count_contact_alert_pipeline

    async def get_filtered_contact_alert_count_query_ws_callable(self, **kwargs):
        # no additional filter required
        return kwargs.get("json_obj_str")
