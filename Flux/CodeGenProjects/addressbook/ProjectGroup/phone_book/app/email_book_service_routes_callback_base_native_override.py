# python imports
import asyncio
import copy
import glob
import logging
import signal
import subprocess
import stat
import time
import queue
from typing import Set
from datetime import datetime
import threading
import requests
import re

# third-party package imports
from fastapi import UploadFile
from pymongo import MongoClient

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    SymbolOverviewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_routes_msgspec_callback import (
    EmailBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    is_service_up, get_symbol_side_key, config_yaml_dict, config_yaml_path,
    YAMLConfigurationManager, street_book_config_yaml_dict, ps_port, CURRENT_PROJECT_DIR,
    CURRENT_PROJECT_SCRIPTS_DIR, create_md_shell_script, MDShellEnvData, ps_host, get_new_contact_status,
    get_new_contact_limits, get_new_chore_limits, CURRENT_PROJECT_DATA_DIR, is_ongoing_plan,
    get_plan_key_from_pair_plan, get_id_from_plan_key, get_new_plan_view_obj,
    get_matching_plan_from_symbol_n_side, get_dismiss_filter_brokers, handle_shadow_broker_updates,
    handle_shadow_broker_creates)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import plan_view_client_call_log_str
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_plan_log_key, get_pair_plan_dict_log_key, pair_plan_id_key, symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.aggregate import (
    get_ongoing_pair_plan_filter, get_all_pair_plan_from_symbol_n_side, get_ongoing_or_all_pair_plans_by_sec_id)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import (
    PlanViewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_plan_id_from_executor_log_file_name, get_symbol_n_side_from_log_line)
from FluxPythonUtils.scripts.service import Service
from FluxPythonUtils.scripts.general_utility_functions import (
    get_pid_from_port, except_n_log_alert, is_process_running, submit_task_with_first_completed_wait,
    handle_refresh_configurable_data_members, parse_to_int, set_package_logger_level)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import get_bartering_link
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    log_book_service_http_client, UpdateType, get_pattern_for_pair_plan_db_updates,
    get_field_seperator_pattern, get_key_val_seperator_pattern)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager


class EmailBookServiceRoutesCallbackBaseNativeOverride(Service, EmailBookServiceRoutesCallback):
    underlying_read_contact_status_http: Callable[..., Any] | None = None
    underlying_read_contact_status_http_json_dict: Callable[..., Any] | None = None
    underlying_create_contact_status_http: Callable[..., Any] | None = None
    underlying_read_chore_limits_http: Callable[..., Any] | None = None
    underlying_read_chore_limits_http_json_dict: Callable[..., Any] | None = None
    underlying_create_chore_limits_http: Callable[..., Any] | None = None
    underlying_read_contact_limits_http_json_dict: Callable[..., Any] | None = None
    underlying_create_contact_limits_http: Callable[..., Any] | None = None
    underlying_read_pair_plan_http: Callable[..., Any] | None = None
    underlying_read_pair_plan_http_json_dict: Callable[..., Any] | None = None
    underlying_read_contact_status_by_id_http: Callable[..., Any] | None = None
    underlying_update_contact_status_http: Callable[..., Any] | None = None
    underlying_read_plan_collection_http: Callable[..., Any] | None = None
    underlying_read_plan_collection_http_json_dict: Callable[..., Any] | None = None
    underlying_create_plan_collection_http: Callable[..., Any] | None = None
    underlying_update_plan_collection_http: Callable[..., Any] | None = None
    underlying_partial_update_pair_plan_http: Callable[..., Any] | None = None
    underlying_partial_update_pair_plan_http_json_dict: Callable[..., Any] | None = None
    underlying_update_pair_plan_to_non_running_state_query_http: Callable[..., Any] | None = None
    underlying_read_pair_plan_by_id_http: Callable[..., Any] | None = None
    underlying_partial_update_all_pair_plan_http: Callable[..., Any] | None = None
    underlying_read_plan_collection_by_id_http: Callable[..., Any] | None = None
    underlying_read_plan_collection_by_id_http_json_dict: Callable[..., Any] | None = None
    underlying_read_system_control_by_id_http: Callable[..., Any] | None = None
    underlying_read_system_control_by_id_http_json_dict: Callable[..., Any] | None = None
    underlying_partial_update_system_control_http: Callable[..., Any] | None = None
    underlying_read_system_control_http: Callable[..., Any] | None = None
    underlying_read_system_control_http_json_dict: Callable[..., Any] | None = None
    underlying_create_system_control_http: Callable[..., Any] | None = None
    underlying_read_contact_limits_http: Callable[..., Any] | None = None
    underlying_read_contact_limits_by_id_http: Callable[..., Any] | None = None
    underlying_read_shadow_brokers_http: Callable[..., Any] | None = None
    underlying_create_all_shadow_brokers_http: Callable[..., Any] | None = None
    underlying_update_all_shadow_brokers_http: Callable[..., Any] | None = None
    underlying_delete_by_id_list_shadow_brokers_http: Callable[..., Any] | None = None
    underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http: Callable[..., Any] | None = None

    Fx_SO_FilePath = CURRENT_PROJECT_SCRIPTS_DIR / f"fx_so.sh"
    RecoveredKillSwitchUpdate: bool = False

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_routes_imports import (
            underlying_read_contact_status_http, underlying_create_contact_status_http,
            underlying_read_chore_limits_http, underlying_create_chore_limits_http,
            underlying_create_contact_limits_http,
            underlying_read_pair_plan_http, underlying_read_contact_status_by_id_http,
            underlying_update_contact_status_http, underlying_read_plan_collection_http,
            underlying_create_plan_collection_http, underlying_update_plan_collection_http,
            underlying_partial_update_pair_plan_http, underlying_update_pair_plan_to_non_running_state_query_http,
            underlying_read_pair_plan_by_id_http, underlying_partial_update_all_pair_plan_http,
            underlying_read_plan_collection_by_id_http, underlying_read_contact_limits_http,
            underlying_read_system_control_by_id_http, underlying_partial_update_system_control_http,
            underlying_read_system_control_http, underlying_create_system_control_http,
            underlying_read_contact_status_http_json_dict, underlying_read_system_control_http_json_dict,
            underlying_read_chore_limits_http_json_dict, underlying_read_contact_limits_http_json_dict,
            underlying_read_plan_collection_http_json_dict, underlying_read_system_control_by_id_http_json_dict,
            underlying_read_pair_plan_http_json_dict, underlying_partial_update_pair_plan_http_json_dict,
            underlying_read_plan_collection_by_id_http_json_dict, underlying_read_contact_limits_by_id_http,
            underlying_read_shadow_brokers_http, underlying_create_all_shadow_brokers_http,
            underlying_update_all_shadow_brokers_http, underlying_delete_by_id_list_shadow_brokers_http,
            underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http)
        cls.underlying_read_contact_status_http = underlying_read_contact_status_http
        cls.underlying_read_contact_status_http_json_dict = underlying_read_contact_status_http_json_dict
        cls.underlying_create_contact_status_http = underlying_create_contact_status_http
        cls.underlying_read_chore_limits_http = underlying_read_chore_limits_http
        cls.underlying_read_chore_limits_http_json_dict = underlying_read_chore_limits_http_json_dict
        cls.underlying_create_chore_limits_http = underlying_create_chore_limits_http
        cls.underlying_read_contact_limits_http_json_dict = underlying_read_contact_limits_http_json_dict
        cls.underlying_create_contact_limits_http = underlying_create_contact_limits_http
        cls.underlying_read_pair_plan_http = underlying_read_pair_plan_http
        cls.underlying_read_pair_plan_http_json_dict = underlying_read_pair_plan_http_json_dict
        cls.underlying_read_contact_status_by_id_http = underlying_read_contact_status_by_id_http
        cls.underlying_update_contact_status_http = underlying_update_contact_status_http
        cls.underlying_read_plan_collection_http = underlying_read_plan_collection_http
        cls.underlying_read_plan_collection_http_json_dict = underlying_read_plan_collection_http_json_dict
        cls.underlying_create_plan_collection_http = underlying_create_plan_collection_http
        cls.underlying_update_plan_collection_http = underlying_update_plan_collection_http
        cls.underlying_partial_update_pair_plan_http = underlying_partial_update_pair_plan_http
        cls.underlying_partial_update_pair_plan_http_json_dict = underlying_partial_update_pair_plan_http_json_dict
        cls.underlying_update_pair_plan_to_non_running_state_query_http = (
            underlying_update_pair_plan_to_non_running_state_query_http)
        cls.underlying_read_pair_plan_by_id_http = underlying_read_pair_plan_by_id_http
        cls.underlying_partial_update_all_pair_plan_http = underlying_partial_update_all_pair_plan_http
        cls.underlying_read_plan_collection_by_id_http = underlying_read_plan_collection_by_id_http
        cls.underlying_read_plan_collection_by_id_http_json_dict = underlying_read_plan_collection_by_id_http_json_dict
        cls.underlying_read_system_control_by_id_http = underlying_read_system_control_by_id_http
        cls.underlying_read_system_control_by_id_http_json_dict = underlying_read_system_control_by_id_http_json_dict
        cls.underlying_partial_update_system_control_http = underlying_partial_update_system_control_http
        cls.underlying_read_system_control_http = underlying_read_system_control_http
        cls.underlying_read_system_control_http_json_dict = underlying_read_system_control_http_json_dict
        cls.underlying_create_system_control_http = underlying_create_system_control_http
        cls.underlying_read_contact_limits_http = underlying_read_contact_limits_http
        cls.underlying_read_shadow_brokers_http = underlying_read_shadow_brokers_http
        cls.underlying_read_contact_limits_by_id_http = underlying_read_contact_limits_by_id_http
        cls.underlying_create_all_shadow_brokers_http = underlying_create_all_shadow_brokers_http
        cls.underlying_update_all_shadow_brokers_http = underlying_update_all_shadow_brokers_http
        cls.underlying_delete_by_id_list_shadow_brokers_http = underlying_delete_by_id_list_shadow_brokers_http
        cls.underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http = (
            underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http)


    def __init__(self):
        self.asyncio_loop = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.static_data: SecurityRecordManager | None = None
        # restricted variables: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {"USD|SGD": None}
        self.usd_fx: float | None = None
        self.pair_plan_id_to_executor_process_id_dict: Dict[int, int] = {}
        self.port_to_executor_http_client_dict: Dict[int, StreetBookServiceHttpClient] = {}

        self.config_yaml_dict = config_yaml_dict
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(self.config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.pos_standby: bool = self.config_yaml_dict.get("pos_standby", False)
        self.bartering_link = get_bartering_link()
        self.pos_disable_from_plan_id_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_plan_id_log_queue_timeout_sec: int = 2
        threading.Thread(target=self.handle_pos_disable_from_plan_id_log_queue, daemon=True).start()
        self.plan_id_by_symbol_side_dict: Dict[str, int] = {}
        self.pos_disable_from_symbol_side_log_queue: queue.Queue = queue.Queue()
        self.pos_disable_from_symbol_side_log_queue_timeout_sec: int = 2
        threading.Thread(target=self.handle_pos_disable_from_symbol_side_log_queue, daemon=True).start()

        super().__init__()

    @staticmethod
    async def _check_n_create_contact_status():
        async with ContactStatus.reentrant_lock:
            contact_status_dict_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_contact_status_http_json_dict())
            if 0 == len(contact_status_dict_list):  # no contact status set yet, create one
                contact_status: ContactStatus = get_new_contact_status()
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_contact_status_http(
                      contact_status, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_system_control():
        async with SystemControl.reentrant_lock:
            system_control_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_system_control_http_json_dict())
            if 0 == len(system_control_list):  # no system_control set yet, create one
                system_control: SystemControl = SystemControl.from_kwargs(_id=1, kill_switch=False)
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_system_control_http(
                    system_control, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_chore_limits():
        async with ChoreLimits.reentrant_lock:
            chore_limits_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_limits_http_json_dict())
            if 0 == len(chore_limits_list):  # no chore_limits set yet, create one
                chore_limits: ChoreLimits = get_new_chore_limits()
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_chore_limits_http(
                    chore_limits, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_contact_limits():
        async with ContactLimits.reentrant_lock:
            contact_limits_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_limits_http_json_dict())
            if 0 == len(contact_limits_list):  # no contact_limits set yet, create one
                contact_limits = get_new_contact_limits()
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_contact_limits_http(
                    contact_limits, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_plan_collection():
        async with PlanCollection.reentrant_lock:
            plan_collection_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_plan_collection_http_json_dict())
            if len(plan_collection_list) == 0:
                created_plan_collection = PlanCollection.from_kwargs(_id=1, loaded_plan_keys=[],
                                                                       buffered_plan_keys=[])
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_plan_collection_http(
                    created_plan_collection, return_obj_copy=False)

    @staticmethod
    async def _check_and_create_start_up_models() -> bool:
        try:
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_contact_status()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_system_control()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_chore_limits()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_contact_limits()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_plan_collection()
        except Exception as e:
            logging.exception(f"_check_and_create_start_up_models failed, exception: {e}")
            return False
        else:
            return True

    def _block_active_plan_with_restricted_security(self):
        pass

    def static_data_periodic_refresh(self):
        # for now only security restrictions are supported in refresh of static data
        # TODO LAZY: we may have to segregate static_data periodic_refresh and refresh when more is supported
        if self.static_data.refresh():
            self._block_active_plan_with_restricted_security()

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create contact limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        static_data_service_state: ServiceState = ServiceState(error_prefix=error_prefix + "static_data_service")
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"phone_book_{ps_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                # static data are considered essential
                if self.service_up and static_data_service_state.ready:
                    if not self.service_ready:
                        # running all existing executor
                        self.service_ready = True
                        self.recover_kill_switch_state()
                        self.recover_existing_executors()
                        self._block_active_plan_with_restricted_security()
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: phone_book service is ready: {datetime.datetime.now().time()}")
                else:
                    warn: str = (f"_app_launch_pre_thread_func: service not ready yet;;;{self.service_up=}, "
                                 f"{static_data_service_state.ready=}")
                    if self.is_stabilization_period_past():
                        logging.warning(warn)
                    else:
                        logging.info(warn)
                if not self.service_up:
                    try:
                        if is_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
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

                            # creating and running fx_so.sh
                            self.create_n_run_fx_so_shell_script()
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

                    # service loop: manage all sub-services within their private try-catch to allow high level service
                    # to remain partially operational even if some sub-service is not available for any reason
                    if not static_data_service_state.ready:
                        try:
                            self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                            if self.static_data is not None:
                                static_data_service_state.ready = True
                                logging.debug("Marked static_data_service_state.ready True")
                                # we just got static data - no need to sleep - force no sleep
                                should_sleep = False
                            else:
                                raise Exception("self.static_data init to None, unexpected!!")
                        except Exception as e:
                            static_data_service_state.handle_exception(e)
                    else:
                        # refresh static data periodically (maybe more in future)
                        try:
                            self.static_data_periodic_refresh()
                        except Exception as e:
                            static_data_service_state.handle_exception(e)
                            static_data_service_state.ready = False  # forces re-init in next iteration

                    # Checking and Restarting crashed executors
                    self.run_crashed_executors()

                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    def run_crashed_executors(self) -> None:
        # coro needs public method
        run_coro = self.async_run_crashed_executors()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"async_run_crashed_executors failed with exception: {e}")

    async def async_run_crashed_executors(self) -> None:
        pending_plans: List[PairPlan]
        pending_plans_id_list: List[int] = []

        if self.pair_plan_id_to_executor_process_id_dict:
            pending_plans = await self._async_check_running_executors(self.pair_plan_id_to_executor_process_id_dict)

            for plan in pending_plans:
                pending_plans_id_list.append(plan.id)

            for pair_plan_id in pending_plans_id_list:
                del self.pair_plan_id_to_executor_process_id_dict[pair_plan_id]

            if pending_plans:
                await self._async_start_executor_server_by_task_submit(pending_plans, is_crash_recovery=True)

    async def get_crashed_pair_plans(self, pair_plan_id, executor_process_id) -> PairPlan:
        pair_plan: PairPlan | None = None
        if not is_process_running(executor_process_id):
            logging.info(f"process for {pair_plan_id=} and {executor_process_id=} found killed, "
                         f"restarting again ...")

            pair_plan: PairPlan = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_pair_plan_by_id_http(pair_plan_id))

            # making plan state non-running - required for UI to know it is not running anymore and
            # avoid connections
            if pair_plan.server_ready_state > 0 or pair_plan.port is not None:
                # If pair plan already exists and executor already have run before
                await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_update_pair_plan_to_non_running_state_query_http(pair_plan.id))
            # else not required: if it is newly created pair plan then already values are False

        return pair_plan

    async def _async_check_running_executors(self, pair_plan_id_to_executor_process_id_dict: Dict[int, int]) -> List[PairPlan]:
        tasks: List = []
        pair_plan_list: List[PairPlan] = []
        for pair_plan_id, executor_process_id in pair_plan_id_to_executor_process_id_dict.items():
            task = asyncio.create_task(self.get_crashed_pair_plans(pair_plan_id, executor_process_id), name=str(pair_plan_id))
            tasks.append(task)

        if tasks:
            pair_plan_list = await submit_task_with_first_completed_wait(tasks)
        return pair_plan_list

    async def _async_start_executor_server_by_task_submit(self, pending_plans: List[PairPlan],
                                                          is_crash_recovery: bool | None = False):
        tasks: List = []
        for idx, pending_plan in enumerate(pending_plans):
            task = asyncio.create_task(self._start_executor_server(pending_plan, is_crash_recovery), name=str(idx))
            tasks.append(task)

        await submit_task_with_first_completed_wait(tasks)

    def recover_kill_switch_state(self):
        # if db true and bartering is false - trigger_kill_switch and not update db
        run_coro = self._recover_kill_switch_state()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            future.result()
        except Exception as e:
            err_str_ = f"_recover_kill_switch_state failed - check and handle kill state manually, exception: {e}"
            logging.exception(err_str_)
        finally:
            EmailBookServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate = False  # reverting state

    async def _recover_kill_switch_state(self) -> None:
        kill_switch_state = await self.bartering_link.is_kill_switch_enabled()

        async with SystemControl.reentrant_lock:
            system_control_id = 1
            system_control: Dict = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_system_control_by_id_http_json_dict(system_control_id))

            kill_switch = system_control.get('kill_switch')
            if not kill_switch and kill_switch_state:
                system_control["kill_switch"] = True
                EmailBookServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate = True
                await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_partial_update_system_control_http(system_control, return_obj_copy=False))
            elif not kill_switch_state and kill_switch:
                logging.warning("Found kill switch in db as True but is_kill_switch_enabled returned False, "
                                "calling bartering_link.trigger_kill_switch")
                await self.bartering_link.trigger_kill_switch()
            # else not required: all okay

    @staticmethod
    def create_n_run_fx_so_shell_script():
        # creating run_symbol_overview.sh file
        run_fx_symbol_overview_file_path = EmailBookServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath

        db_name = os.environ.get("DB_NAME")
        if db_name is None:
            db_name = "phone_book"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData.from_kwargs(host=ps_host, port=ps_port, db_name=db_name, project_name="phone_book"))

        create_md_shell_script(md_shell_env_data, run_fx_symbol_overview_file_path, "SO")
        os.chmod(run_fx_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_fx_symbol_overview_file_path}"])

    async def async_recover_existing_executors(self) -> None:
        existing_pair_plans: List[PairPlan] = \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_http()
        plan_collection_list: List[Dict] =  \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_collection_http_json_dict()

        if plan_collection_list:
            if len(plan_collection_list) == 1:
                plan_collection = plan_collection_list[0]
                loaded_plan_keys: List[str] = plan_collection.get("loaded_plan_keys")

                loaded_pair_plan_id_list: List[int] = []
                if loaded_plan_keys is not None:
                    for loaded_plan_key in loaded_plan_keys:
                        loaded_pair_plan_id_list.append(get_id_from_plan_key(loaded_plan_key))

                crashed_plans: List[PairPlan] = []
                for pair_plan in existing_pair_plans:
                    if pair_plan.id in loaded_pair_plan_id_list:
                        if pair_plan.port is not None:
                            # setting cache for executor client
                            self._update_port_to_executor_http_client_dict_from_updated_pair_plan(pair_plan.host,
                                                                                                   pair_plan.port)

                            street_book_http_client = self.port_to_executor_http_client_dict.get(pair_plan.port)
                            try:
                                # Checking if get-request works
                                street_book_http_client.get_all_ui_layout_client()
                            except requests.exceptions.Timeout:
                                # If timeout error occurs it is most probably that executor server got hung/stuck
                                # logging and killing this executor
                                logging.exception(f"Found executor with port: {pair_plan.port} in hung state, killing "
                                                  f"the executor process;;; pair_plan: {pair_plan}")
                                pid = get_pid_from_port(pair_plan.port)
                                os.kill(pid, signal.SIGKILL)

                                # Updating pair_plan
                                pair_plan_json = {
                                    "_id": pair_plan.id,
                                    "plan_state": PlanState.PlanState_ERROR,
                                    "server_ready_state": 0,
                                    "port": None,
                                    "cpp_port": None,
                                    "cpp_ws_port": None
                                }

                                await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                       underlying_partial_update_pair_plan_http(pair_plan_json, return_obj_copy=False))

                            except Exception as e:
                                if "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
                                    logging.error(f"PairPlan found to have port set to {pair_plan.port} but executor "
                                                  f"server is down, recovering executor for "
                                                  f"{pair_plan.id=};;; {pair_plan=}")
                                    crashed_plans.append(pair_plan)
                                    await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                           underlying_update_pair_plan_to_non_running_state_query_http(pair_plan.id))
                                elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
                                      "it from responding to requests" in str(e) and "status_code: 503" in str(e)):
                                    pid = get_pid_from_port(pair_plan.port)
                                    if pid is not None:
                                        os.kill(pid, signal.SIGKILL)
                                    crashed_plans.append(pair_plan)
                                    await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                           underlying_update_pair_plan_to_non_running_state_query_http(pair_plan.id))
                                else:
                                    logging.exception("Something went wrong while checking is_service_up of executor "
                                                      f"with port: {pair_plan.port} in pair_plan plan_up recovery "
                                                      f"check - force kill this executor if is running, "
                                                      f"exception: {e};;; {pair_plan=}")
                            else:
                                # If executor server is still up and is in healthy state - Finding and adding
                                # process_id to pair_plan_id_to_executor_process_dicts
                                pid = get_pid_from_port(pair_plan.port)
                                self.pair_plan_id_to_executor_process_id_dict[pair_plan.id] = pid
                        else:
                            crashed_plans.append(pair_plan)
                    # else not required: avoiding if pair_plan is not in loaded_plans

                # Restart crashed executors
                if crashed_plans:
                    await self._async_start_executor_server_by_task_submit(crashed_plans, is_crash_recovery=True)
            else:
                err_str_ = "Unexpected: Found more than 1 plan_collection objects - Ignoring any executor recovery"
                logging.error(err_str_)
        else:
            err_str_ = "No plan_collection model exists yet - no executor to recover"
            logging.debug(err_str_)

    def recover_existing_executors(self) -> None:
        if self.asyncio_loop:
            # coro needs public method
            run_existing_executors_coro = self.async_recover_existing_executors()
            future = asyncio.run_coroutine_threadsafe(run_existing_executors_coro, self.asyncio_loop)
        else:
            raise Exception("run_existing_executors failed - self.asyncio_loop found None")
        # block for start_executor_server task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"start executor server failed with exception: {e}")

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

    def get_local_px_or_notional(self, px_or_notional: float, system_symbol: str):
        return px_or_notional * self.usd_fx

    def app_launch_pre(self):
        EmailBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()
        # to be called only after logger is initialized - to prevent getting overridden
        set_package_logger_level("filelock", logging.WARNING)

        self.port = ps_port
        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

        # removing md scripts
        try:
            if os.path.exists(EmailBookServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath):
                os.remove(EmailBookServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath)
        except Exception as e:
            err_str_ = f"Something went wrong while deleting fx_so shell script, exception: {e}"
            logging.error(err_str_)

    def get_generic_read_route(self):
        return None

    # Example: Soft API Query Interfaces

    async def update_contact_status_by_chore_or_fill_data_query_pre(
            self, contact_status_class_type: Type[ContactStatus], overall_buy_notional: float | None = None,
            overall_sell_notional: float | None = None, overall_buy_fill_notional: float | None = None,
            overall_sell_fill_notional: float | None = None, open_chore_count: int | None = None):
        async with ContactStatus.reentrant_lock:
            contact_status: ContactStatus = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_status_by_id_http(
                    1))

            if overall_buy_notional is not None:
                if contact_status.overall_buy_notional is None:
                    contact_status.overall_buy_notional = 0
                contact_status.overall_buy_notional += overall_buy_notional
            if overall_sell_notional is not None:
                if contact_status.overall_sell_notional is None:
                    contact_status.overall_sell_notional = 0
                contact_status.overall_sell_notional += overall_sell_notional
            if overall_buy_fill_notional is not None:
                if contact_status.overall_buy_fill_notional is None:
                    contact_status.overall_buy_fill_notional = 0
                contact_status.overall_buy_fill_notional += overall_buy_fill_notional
            if overall_sell_fill_notional is not None:
                if contact_status.overall_sell_fill_notional is None:
                    contact_status.overall_sell_fill_notional = 0
                contact_status.overall_sell_fill_notional += overall_sell_fill_notional
            if open_chore_count is not None:
                contact_status.open_chores = open_chore_count

            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_contact_status_http(
                contact_status, return_obj_copy=False)

        return []

    # Code-generated
    async def get_pair_plan_sec_filter_json_query_pre(self, pair_plan_class_type: Type[PairPlan], security_id: str):
        return await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_http(
            get_ongoing_pair_plan_filter(security_id), self.get_generic_read_route())

    def _set_derived_side(self, pair_plan_obj: PairPlan):
        raise_error = False
        if pair_plan_obj.pair_plan_params.plan_leg2.side is None or \
                pair_plan_obj.pair_plan_params.plan_leg2.side == Side.SIDE_UNSPECIFIED:
            if pair_plan_obj.pair_plan_params.plan_leg1.side == Side.BUY:
                pair_plan_obj.pair_plan_params.plan_leg2.side = Side.SELL
            elif pair_plan_obj.pair_plan_params.plan_leg1.side == Side.SELL:
                pair_plan_obj.pair_plan_params.plan_leg2.side = Side.BUY
            else:
                raise_error = True
        elif pair_plan_obj.pair_plan_params.plan_leg1.side is None:
            raise_error = True
        # else not required, all good
        if raise_error:
            # handles pair_plan_obj.pair_plan_params.plan_leg1.side == None and all other unsupported values
            raise Exception(f"error: _set_derived_side called with unsupported side combo on legs, leg1: "
                            f"{pair_plan_obj.pair_plan_params.plan_leg1.side} leg2: "
                            f"{pair_plan_obj.pair_plan_params.plan_leg2.side} in pair plan: {pair_plan_obj}")

    def _set_derived_exchange(self, pair_plan_obj: PairPlan):
        unsupported_sec_id_source: bool = False
        plan_leg1: PlanLeg = pair_plan_obj.pair_plan_params.plan_leg1
        plan_leg2: PlanLeg = pair_plan_obj.pair_plan_params.plan_leg2
        if plan_leg1.sec.sec_id_source == SecurityIdSource.TICKER:
            plan_leg1.exch_id = self.static_data.get_exchange_from_ticker(plan_leg1.sec.sec_id)
        else:
            unsupported_sec_id_source = True
        if plan_leg2.sec.sec_id_source == SecurityIdSource.TICKER:
            plan_leg2.exch_id = self.static_data.get_exchange_from_ticker(plan_leg2.sec.sec_id)
        else:
            unsupported_sec_id_source = True
        if unsupported_sec_id_source:
            raise Exception(f"error: _set_derived_exchange called with unsupported sec_id_source param, supported: "
                            f"SecurityIdSource.TICKER, {plan_leg1.sec.sec_id_source=}, {plan_leg2.sec.sec_id_source=}"
                            f";;;{pair_plan_obj=}")

    async def get_dismiss_filter_contact_limit_brokers_query_pre(
            self, shadow_brokers_class_type: Type[ShadowBrokers], security_id1: str, security_id2: str):
        return await get_dismiss_filter_brokers(
            EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_shadow_brokers_http,
            self.static_data, security_id1, security_id2)

    def create_plan_view_for_plan(self, pair_plan: PairPlan):
        new_plan_view = get_new_plan_view_obj(pair_plan.id)
        photo_book_service_http_client.create_plan_view_client(new_plan_view)

    @except_n_log_alert()
    async def create_pair_plan_pre(self, pair_plan_obj: PairPlan):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_pair_plan_pre not ready - service is not initialized yet, " \
                       f"pair_plan_key: {get_pair_plan_log_key(pair_plan_obj)};;; {pair_plan_obj=}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        if (pair_plan_obj.pair_plan_params.mplan is None and
                pair_plan_obj.pair_plan_params.plan_type == PlanType.Premium):
            pair_plan_obj.pair_plan_params.mplan = "Mplan_1"
        plan_leg1_sec_id: str = pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id
        plan_leg2_sec_id: str | None = None
        # expectation: if plan leg2 is not provided, set it from static data
        if pair_plan_obj.pair_plan_params.plan_leg2 is None:
            plan_leg2_sec_id = self.static_data.get_underlying_eqt_ticker_from_cb_ticker(plan_leg1_sec_id)
            if plan_leg2_sec_id is None:
                raise Exception(f"error: underlying eqt ticker not found for cb_ticker: {plan_leg1_sec_id};;;"
                                f"{pair_plan_obj=}")
            plan_leg2_sec: Security = Security(sec_id=plan_leg2_sec_id, sec_id_source=SecurityIdSource.TICKER,
                                                inst_type=InstrumentType.EQT)
            pair_plan_obj.pair_plan_params.plan_leg2 = PlanLeg(sec=plan_leg2_sec)
        else:
            plan_leg2_sec_id = pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id

        if (pair_plan_obj.pair_plan_params.plan_leg1.sec.inst_type is None or
                pair_plan_obj.pair_plan_params.plan_leg1.sec.inst_type == InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED):
            pair_plan_obj.pair_plan_params.plan_leg1.sec.inst_type = InstrumentType.CB
        if (pair_plan_obj.pair_plan_params.plan_leg2.sec.inst_type is None or
                pair_plan_obj.pair_plan_params.plan_leg2.sec.inst_type == InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED):
            pair_plan_obj.pair_plan_params.plan_leg2.sec.inst_type = InstrumentType.EQT

        self._set_derived_side(pair_plan_obj)
        self._set_derived_exchange(pair_plan_obj)
        pair_plan_obj.frequency = 1
        pair_plan_obj.pair_plan_params_update_seq_num = 0
        pair_plan_obj.last_active_date_time = DateTime.utcnow()

        pair_plan_obj.host = street_book_config_yaml_dict.get("server_host")
        pair_plan_obj.server_ready_state = 0

        # creating plan_view object for this start
        self.create_plan_view_for_plan(pair_plan_obj)

        # @@@ Warning: Below handling of state collection is handled from ui also - see where can code be remove
        # to avoid duplicate
        async with PlanCollection.reentrant_lock:
            plan_collection_obj: PlanCollection = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_plan_collection_by_id_http(1))
            plan_key = get_plan_key_from_pair_plan(pair_plan_obj)
            plan_collection_obj.loaded_plan_keys.append(plan_key)
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_collection_http(
                plan_collection_obj, return_obj_copy=False)

        # setting plan alert state to False for this plan_id
        symbol_side1 = symbol_side_key(pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id,
                                       pair_plan_obj.pair_plan_params.plan_leg1.side)
        symbol_side2 = symbol_side_key(pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id,
                                       pair_plan_obj.pair_plan_params.plan_leg2.side)
        log_book_service_http_client.enable_disable_plan_alert_create_query_client(pair_plan_obj.id,
                                                                                        [symbol_side1,
                                                                                         symbol_side2],
                                                                                        True)

        # starting executor server for current pair plan
        await self._start_executor_server(pair_plan_obj)
        # if fail - log error is fine - plan not active
        self._apply_fallback_route_check(pair_plan_obj, raise_exception=False, update_fallback_route=True)
        self._apply_restricted_security_check(plan_leg1_sec_id, pair_plan_obj.pair_plan_params.plan_leg1.side,
                                              raise_exception=False)
        self._apply_restricted_security_check(plan_leg2_sec_id, pair_plan_obj.pair_plan_params.plan_leg2.side,
                                              raise_exception=False)

    def _apply_restricted_security_check(self, sec_id: str, side: Side, raise_exception: bool = True):
        # restricted security check
        if self.static_data is None:
            err_str_ = (f"unable to conduct restricted security check static data is not available yet, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            if raise_exception:
                raise HTTPException(status_code=503, detail=err_str_)
            else:
                logging.error(err_str_)
        elif self.static_data.get_security_record_from_ticker(sec_id) is None:
            err_str_ = f"Security record found None {sec_id=}, security not present in barter ready list"
            if raise_exception:
                raise HTTPException(status_code=400, detail=err_str_)
            else:
                logging.error(err_str_)
        elif self.static_data.is_restricted(sec_id):
            err_str_ = (f"restricted security check failed: {sec_id=}, symbol_side_key: "
                        f"{get_symbol_side_key([(sec_id, side)])}")
            if raise_exception:
                raise HTTPException(status_code=400, detail=err_str_)
            else:
                logging.error(err_str_)

    def _create_fallback_routes(self, plan_collection_obj: PlanCollection):
        pass

    def _apply_fallback_route_check(self, pair_plan: PairPlan, raise_exception: bool,
                                    update_fallback_route: bool = False):
        if pair_plan.pair_plan_params.plan_leg2.fallback_route != BrokerRoute.BR_CONNECT:
            return  # for now the check only applies if plan_leg2 fallback_route is BrokerRoute.BR_CONNECT
        sec_id: str = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        side: Side = pair_plan.pair_plan_params.plan_leg2.side
        if self.static_data is None:
            err_str_ = (f"unable to conduct connect security check static data not available yet, symbol_side_key: "
                        f"{get_symbol_side_key([(sec_id, side)])}")
            if raise_exception:
                raise HTTPException(status_code=503, detail=err_str_)
            else:
                logging.error(err_str_)
        elif self.static_data.is_cn_connect_restricted(sec_id, "B" if side == Side.BUY or side == Side.BTC else "S"):
            # connect security check is the only fallback_route check for now
            if update_fallback_route:
                pair_plan.pair_plan_params.plan_leg2.fallback_route = BrokerRoute.BR_QFII
                logging.warning(f"fallback route updated from BR_CONNECT to BR_QFII for {sec_id=};;;symbol_side_key: "
                                f"{get_symbol_side_key([(sec_id, side)])}")
            else:
                err_str_ = (f"on CN connect, {sec_id=} found restricted for {side=};;;symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])}")
                if raise_exception:
                    raise HTTPException(status_code=400, detail=err_str_)
                else:
                    logging.error(err_str_)

    @staticmethod
    def are_similar_plans(plan1: PairPlan, plan2: PairPlan):
        plan1_leg1: PlanLeg = plan1.pair_plan_params.plan_leg1
        plan1_leg2: PlanLeg = plan1.pair_plan_params.plan_leg2
        plan2_leg1: PlanLeg = plan2.pair_plan_params.plan_leg1
        plan2_leg2: PlanLeg = plan2.pair_plan_params.plan_leg2

        if (plan1_leg1.sec.sec_id == plan2_leg1.sec.sec_id and plan1_leg1.side == plan2_leg1.side and
                plan1_leg2.sec.sec_id == plan2_leg2.sec.sec_id and plan1_leg2.side == plan2_leg2.side and
                plan1.id != plan2.id):
            return True
        return False

    async def _apply_activate_checks_n_log_error(self, pair_plan: PairPlan):
        """
        implement any plan management checks here (create / update plans)
        """
        leg1_side: Side
        leg2_side: Side
        leg1_symbol, leg1_side = (pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                  pair_plan.pair_plan_params.plan_leg1.side)
        leg2_symbol, leg2_side = (pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                  pair_plan.pair_plan_params.plan_leg2.side)
        self._apply_restricted_security_check(leg1_symbol, leg1_side)
        self._apply_restricted_security_check(leg2_symbol, leg2_side)

        ongoing_pair_plans: List[PairPlan] | None = await (
            get_matching_plan_from_symbol_n_side(leg1_symbol, leg1_side, no_ongoing_ok=True))
        # First Checking if any ongoing plan exists with same symbol_side pairs in same legs of param pair_plan,
        # that means if one plan is ongoing with s1-sd1 and s2-sd2 symbol-side pair legs then param pair_plan
        # must not have same symbol-side pair legs else HTTP exception is raised

        if ongoing_pair_plans:
            if len(ongoing_pair_plans) == 1:
                ongoing_pair_plan = ongoing_pair_plans[0]
                # raising exception only if ongoing pair_plan's leg1's symbol-side are same as
                # param pair_plan's leg1's symbol-side and same for leg2
                if self.are_similar_plans(ongoing_pair_plan, pair_plan):
                    err_str_ = (f"Ongoing plan already exists with same symbol-side pair legs - can't activate this "
                                f"plan till other plan is ongoing;;; {ongoing_pair_plan=}")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)
                # else not required, this is opposite side plan, let continue for further activation checks
            elif len(ongoing_pair_plans) == 2:
                ongoing_pair_plan1, ongoing_pair_plan2 = ongoing_pair_plans
                if not (self.are_similar_plans(ongoing_pair_plan1, pair_plan) or
                        self.are_similar_plans(ongoing_pair_plan2, pair_plan)):
                    err_str_ = (f"can't activate this plan, none of {len(ongoing_pair_plans)} more ongoing plans "
                                f"are similar;;;{ongoing_pair_plans=}")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)
                # else all good - let the activation through
            else:
                err_str_ = (f"can't activate this plan, {len(ongoing_pair_plans)} more ongoing plans found;;;"
                            f"{ongoing_pair_plans=}")
                logging.error(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
        # else not required, no ongoing pair plan - let the plan activation check pass

        # Checking if any plan exists with opp symbol and side of param pair_plan that activated today,
        # for instance if s1-sd1 and s2-sd2 are symbol-side pairs in param pair_plan's legs then checking there must
        # not be any plan activated today with s1-sd2 and s2-sd1 symbol-side pair legs, if it is found then this
        # plan can't be activated unless plan symbols are all opposite side tradable
        first_matched_plan_lock_file_path_list: List[str] = []
        if not self.static_data.is_opposite_side_tradable(leg1_symbol):
            first_matched_plan_lock_file_path_list = (
                glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                          f"{leg1_symbol}_{leg2_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        second_matched_plan_lock_file_path_list: List[str] = []
        if not self.static_data.is_opposite_side_tradable(leg2_symbol):
            second_matched_plan_lock_file_path_list = (
                glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                              f"{leg2_symbol}_{leg1_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        # checking both legs - If first_matched_plan_lock_file_path_list and second_matched_plan_lock_file_path_list
        # have file names having same pair_plan_id with today's date along with required symbol-side pair
        for matched_plan_file_path in first_matched_plan_lock_file_path_list:
            suffix_pattern = matched_plan_file_path[(matched_plan_file_path.index(leg2_side) + len(leg2_side)):]
            for sec_matched_plan_lock_file_path in second_matched_plan_lock_file_path_list:
                if sec_matched_plan_lock_file_path.endswith(suffix_pattern):
                    err_str_ = ("Found plan activated today with symbols of this plan being used in opposite sides"
                                " - can't activate this plan today")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)

    def get_lock_file_names_from_pair_plan(self, pair_plan: PairPlan) -> Tuple[PurePath | None, PurePath | None]:
        leg1_sec_id: str = pair_plan.pair_plan_params.plan_leg1.sec.sec_id
        leg1_lock_file_path: str | None = None
        if not self.static_data.is_opposite_side_tradable(leg1_sec_id):
            leg1_lock_file_path = (CURRENT_PROJECT_DATA_DIR / f"{leg1_sec_id}_"
                                                              f"{pair_plan.pair_plan_params.plan_leg1.side.value}_"
                                                              f"{pair_plan.id}_{DateTime.date(DateTime.utcnow())}"
                                                              f".json.lock")

        leg2_sec_id: str = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        leg2_lock_file_path: str | None = None
        if not self.static_data.is_opposite_side_tradable(leg2_sec_id):
            leg2_lock_file_path = (CURRENT_PROJECT_DATA_DIR / f"{leg2_sec_id}_"
                                                              f"{pair_plan.pair_plan_params.plan_leg2.side.value}_"
                                                              f"{pair_plan.id}_{DateTime.date(DateTime.utcnow())}"
                                                              f".json.lock")
        return leg1_lock_file_path, leg2_lock_file_path

    async def _update_pair_plan_pre(self, stored_pair_plan_obj: PairPlan,
                                     updated_pair_plan_obj: PairPlan) -> bool | None:
        """
        Return true if check passed false otherwise
        """
        check_passed = True
        if stored_pair_plan_obj.plan_state != PlanState.PlanState_ACTIVE and \
                updated_pair_plan_obj.plan_state == PlanState.PlanState_ACTIVE:
            await self._apply_activate_checks_n_log_error(stored_pair_plan_obj)  # raises HTTPException internally
            if stored_pair_plan_obj.plan_state == PlanState.PlanState_READY:
                leg1_lock_file_path, leg2_lock_file_path = (
                    self.get_lock_file_names_from_pair_plan(updated_pair_plan_obj))
                if leg1_lock_file_path:
                    with open(leg1_lock_file_path, "w") as fl:  # creating empty file
                        pass
                if leg2_lock_file_path:
                    with open(leg2_lock_file_path, "w") as fl:  # creating empty file
                        pass
            # else not required: create plan lock file only if moving the plan state from
            # PlanState_READY to PlanState_ACTIVE
        if updated_pair_plan_obj.plan_state == PlanState.PlanState_DONE:
            # warning and above log level is required
            # setting plan alert state to False for this plan_id
            symbol_side1 = symbol_side_key(stored_pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id,
                                           stored_pair_plan_obj.pair_plan_params.plan_leg1.side)
            symbol_side2 = symbol_side_key(stored_pair_plan_obj.pair_plan_params.plan_leg2.sec.sec_id,
                                           stored_pair_plan_obj.pair_plan_params.plan_leg2.side)
            log_book_service_http_client.enable_disable_plan_alert_create_query_client(stored_pair_plan_obj.id,
                                                                                            [symbol_side1,
                                                                                             symbol_side2],
                                                                                            False)

        if updated_pair_plan_obj.plan_state != PlanState.PlanState_ACTIVE:
            # if fail - log error is fine - plan not active - check does not fail due to this
            self._apply_fallback_route_check(updated_pair_plan_obj, raise_exception=False)
        else:
            # updated_pair_plan_obj.plan_state is PlanState.PlanState_ACTIVE, if fail - raise exception
            self._apply_fallback_route_check(updated_pair_plan_obj, raise_exception=True)
        return check_passed

    def _update_port_to_executor_http_client_dict_from_updated_pair_plan(self, host: str, port: int):
        if port is not None and port not in self.port_to_executor_http_client_dict:
            self.port_to_executor_http_client_dict[port] = (
                StreetBookServiceHttpClient.set_or_get_if_instance_exists(host, port))

    async def update_pair_plan_pre(self, stored_pair_plan_obj: PairPlan, updated_pair_plan_obj: PairPlan):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "update_pair_plan_pre not ready - service is not initialized yet, " \
                       f"pair_plan_key: {get_pair_plan_log_key(updated_pair_plan_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_pair_plan_obj.frequency is None:
            updated_pair_plan_obj.frequency = 0
        updated_pair_plan_obj.frequency += 1

        if updated_pair_plan_obj.pair_plan_params_update_seq_num is None:
            updated_pair_plan_obj.pair_plan_params_update_seq_num = 0
        updated_pair_plan_obj.pair_plan_params_update_seq_num += 1
        updated_pair_plan_obj.last_active_date_time = DateTime.utcnow()

        res = await self._update_pair_plan_pre(stored_pair_plan_obj, updated_pair_plan_obj)
        if not res:
            sec_id: str = stored_pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id
            side: Side = stored_pair_plan_obj.pair_plan_params.plan_leg1.side
            logging.debug(f"Alerts updated by _update_pair_plan_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(sec_id, side)])};;;{updated_pair_plan_obj=}")

        # updating port_to_executor_http_client_dict with this port if not present
        self._update_port_to_executor_http_client_dict_from_updated_pair_plan(updated_pair_plan_obj.host,
                                                                               updated_pair_plan_obj.port)

        return updated_pair_plan_obj

    async def _partial_update_pair_plan(self, stored_pair_plan_obj_dict: Dict, updated_pair_plan_obj_dict: Dict):
        stored_pair_plan_obj = PairPlan.from_dict(stored_pair_plan_obj_dict)
        updated_pair_plan_obj_dict["frequency"] = stored_pair_plan_obj.frequency + 1

        if updated_pair_plan_obj_dict.get("pair_plan_params") is not None:
            if stored_pair_plan_obj.pair_plan_params_update_seq_num is None:
                stored_pair_plan_obj.pair_plan_params_update_seq_num = 0
            updated_pair_plan_obj_dict["pair_plan_params_update_seq_num"] = \
                stored_pair_plan_obj.pair_plan_params_update_seq_num + 1

        updated_pair_plan_obj_dict["last_active_date_time"] = DateTime.utcnow()

        updated_plan_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_pair_plan_obj.to_dict()),
                                                      updated_pair_plan_obj_dict)
        updated_pair_plan_obj = PairPlan.from_dict(updated_plan_obj_dict)
        res = await self._update_pair_plan_pre(stored_pair_plan_obj, updated_pair_plan_obj)
        if not res:
            sec_id: str = stored_pair_plan_obj.pair_plan_params.plan_leg1.sec.sec_id
            side: Side = stored_pair_plan_obj.pair_plan_params.plan_leg1.side
            logging.debug(f"Alerts updated by _update_pair_plan_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(sec_id, side)])};;;{updated_pair_plan_obj=}")
        updated_pair_plan_obj_dict = updated_pair_plan_obj.to_dict()

        # updating port_to_executor_http_client_dict with this port if not present
        host = updated_pair_plan_obj_dict.get("host")
        port = updated_pair_plan_obj_dict.get("port")
        self._update_port_to_executor_http_client_dict_from_updated_pair_plan(host, port)
        return updated_pair_plan_obj_dict

    async def partial_update_pair_plan_pre(self, stored_pair_plan_obj_json: Dict[str, Any],
                                            updated_pair_plan_obj_json: Dict[str, Any]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "partial_update_pair_plan_pre not ready - service is not initialized yet, " \
                       f"pair_plan: {stored_pair_plan_obj_json}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        updated_pair_plan_obj_dict = \
            await self._partial_update_pair_plan(stored_pair_plan_obj_json, updated_pair_plan_obj_json)
        return updated_pair_plan_obj_dict

    async def partial_update_all_pair_plan_pre(self, stored_pair_plan_dict_list: List[Dict[str, Any]],
                                                updated_pair_plan_dict_list: List[Dict[str, Any]]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "partial_update_pair_plan_pre not ready - service is not initialized yet, "
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        tasks: List = []
        for idx, updated_pair_plan_obj_json in enumerate(updated_pair_plan_dict_list):
            task = asyncio.create_task(self._partial_update_pair_plan(stored_pair_plan_dict_list[idx],
                                                                       updated_pair_plan_obj_json),
                                       name=str(f"{stored_pair_plan_dict_list[idx].get('_id')}"))
            tasks.append(task)
        updated_pair_plan_obj_json_list = await submit_task_with_first_completed_wait(tasks)
        return updated_pair_plan_obj_json_list

    def check_n_disable_non_mplan_positions(self, stored_pair_plan_obj_or_dict: Dict | PairPlan,
                                             updated_pair_plan_obj_or_dict: Dict | PairPlan):
        pass

    def _update_pair_plan_post(self, stored_pair_plan_obj: PairPlan, updated_pair_plan_obj: PairPlan):
        if stored_pair_plan_obj.plan_state != updated_pair_plan_obj.plan_state:
            logging.warning(f"Plan state changed from {stored_pair_plan_obj.plan_state.value} to "
                            f"{updated_pair_plan_obj.plan_state.value};;;pair_plan_log_key: "
                            f"{get_pair_plan_log_key(updated_pair_plan_obj)}")
        self.check_n_disable_non_mplan_positions(stored_pair_plan_obj, updated_pair_plan_obj)

    def _partial_update_pair_plan_post(self, stored_pair_plan_obj_dict: Dict, updated_pair_plan_obj_dict: Dict):
        stored_plan_state = stored_pair_plan_obj_dict.get("plan_state")
        updated_plan_state = updated_pair_plan_obj_dict.get("plan_state")
        if stored_plan_state != updated_plan_state:
            logging.warning(f"Plan state changed from {stored_plan_state} to "
                            f"{updated_plan_state};;;pair_plan_log_key: "
                            f"{get_pair_plan_dict_log_key(updated_pair_plan_obj_dict)}")
        self.check_n_disable_non_mplan_positions(stored_pair_plan_obj_dict, updated_pair_plan_obj_dict)

    async def update_pair_plan_post(self, stored_pair_plan_obj: PairPlan, updated_pair_plan_obj: PairPlan):
        self._update_pair_plan_post(stored_pair_plan_obj, updated_pair_plan_obj)

    async def partial_update_pair_plan_post(self, stored_pair_plan_obj_dict: Dict,
                                             updated_pair_plan_obj_dict: Dict):
        self._partial_update_pair_plan_post(stored_pair_plan_obj_dict, updated_pair_plan_obj_dict)

    async def partial_update_all_pair_plan_post(self, stored_pair_plan_obj_dict_list: List[Dict],
                                                 updated_pair_plan_obj_dict_list: List[Dict]):
        stored_pair_plan_obj_dict: Dict
        for idx, stored_pair_plan_obj_dict in enumerate(stored_pair_plan_obj_dict_list):
            updated_pair_plan_obj_dict: Dict[str, Any] = updated_pair_plan_obj_dict_list[idx]
            self._partial_update_pair_plan_post(stored_pair_plan_obj_dict, updated_pair_plan_obj_dict)

    async def pause_all_active_plans_query_pre(self, pair_plan_class_type: Type[PairPlan]):
        async with PairPlan.reentrant_lock:
            pair_plan_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_http_json_dict())

            updated_pair_plans_list: List[Dict] = []
            for pair_plan_ in pair_plan_list:

                # Putting plan to pause if plan is active
                plan_state = pair_plan_.get("plan_state")
                _id = pair_plan_.get("_id")
                if plan_state == PlanState.PlanState_ACTIVE:
                    update_pair_plan = {"_id": _id, "plan_state": PlanState.PlanState_PAUSED}
                    updated_pair_plans_list.append(update_pair_plan)

            if updated_pair_plans_list:
                logging.warning("Pausing all plans")
                (await EmailBookServiceRoutesCallbackBaseNativeOverride.
                 underlying_partial_update_all_pair_plan_http(updated_pair_plans_list, return_obj_copy=False))
        return []

    async def update_pair_plan_to_non_running_state_query_pre(self, pair_plan_class_type: Type[PairPlan],
                                                               pair_plan_id: int):
        pair_plan_json = {
            "_id": pair_plan_id,
            "server_ready_state": 0,
            "port": None,
            "cpp_port": None,
            "cpp_ws_port": None
        }

        update_pair_plan = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_partial_update_pair_plan_http(pair_plan_json))
        return [update_pair_plan]

    async def _start_executor_server(self, pair_plan: PairPlan, is_crash_recovery: bool | None = None) -> None:
        code_gen_projects_dir = PurePath(__file__).parent.parent.parent
        # executor_path = code_gen_projects_dir / "street_book" / "scripts" / 'launch_beanie_fastapi.py'
        executor_path = code_gen_projects_dir / "street_book" / "scripts" / 'launch_msgspec_fastapi.py'
        if is_crash_recovery:
            # 1 is sent to indicate it is recovery restart
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_plan.id}', "1", '&'])
        else:
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_plan.id}', '&'])

        logging.info(f"Launched plan executor for {pair_plan.id=};;;{executor_path=}")
        self.pair_plan_id_to_executor_process_id_dict[pair_plan.id] = executor.pid

    def _close_executor_server(self, pair_plan_id: int) -> None:
        process_id = self.pair_plan_id_to_executor_process_id_dict.get(pair_plan_id)
        # process.terminate()
        os.kill(process_id, signal.SIGINT)

        del self.pair_plan_id_to_executor_process_id_dict[pair_plan_id]

    async def get_ongoing_plans_symbol_n_exch_query_pre(self,
                                                         ongoing_plan_symbols_class_type: Type[
                                                             OngoingPlansSymbolNExchange]):

        pair_plan_list: List[PairPlan] = \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_http(
                get_ongoing_pair_plan_filter(), self.get_generic_read_route())
        ongoing_symbol_n_exch_set: Set[str] = set()
        ongoing_plan_symbols_n_exchange = OngoingPlansSymbolNExchange(symbol_n_exchange=[])

        before_len: int = 0
        for pair_plan in pair_plan_list:
            leg1_symbol = pair_plan.pair_plan_params.plan_leg1.sec.sec_id
            leg1_exch = pair_plan.pair_plan_params.plan_leg1.exch_id
            leg2_symbol = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
            leg2_exch = pair_plan.pair_plan_params.plan_leg2.exch_id
            leg1_symbol_n_exch = SymbolNExchange.from_kwargs(symbol=leg1_symbol, exchange=leg1_exch)
            leg2_symbol_n_exch = SymbolNExchange.from_kwargs(symbol=leg2_symbol, exchange=leg2_exch)

            ongoing_symbol_n_exch_set.add(f"{leg1_symbol}_{leg1_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_plan_symbols_n_exchange.symbol_n_exchange.append(leg1_symbol_n_exch)
                before_len += 1

            ongoing_symbol_n_exch_set.add(f"{leg2_symbol}_{leg2_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_plan_symbols_n_exchange.symbol_n_exchange.append(leg2_symbol_n_exch)
                before_len += 1
        return [ongoing_plan_symbols_n_exchange]

    def _drop_executor_db_for_deleting_pair_plan(self, mongo_server_uri: str, pair_plan_id: int,
                                                  sec_id: str, side: Side):
        mongo_client = MongoClient(mongo_server_uri)
        db_name: str = f"street_book_{pair_plan_id}"

        if db_name in mongo_client.list_database_names():
            mongo_client.drop_database(db_name)
        else:
            err_str_ = (f"Unexpected: {db_name=} not found in mongo_client for uri: "
                        f"{mongo_server_uri} being used by current plan, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)

    async def delete_pair_plan_pre(self, pair_plan_id: int):
        pair_plan_to_be_deleted = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_read_pair_plan_by_id_http(pair_plan_id))

        port: int = pair_plan_to_be_deleted.port
        sec_id = pair_plan_to_be_deleted.pair_plan_params.plan_leg1.sec.sec_id
        side = pair_plan_to_be_deleted.pair_plan_params.plan_leg1.side

        plan_key = get_plan_key_from_pair_plan(pair_plan_to_be_deleted)
        plan_collection_dict: Dict = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                        underlying_read_plan_collection_by_id_http_json_dict(1))

        loaded_plan_keys = plan_collection_dict.get("loaded_plan_keys")
        buffered_plan_keys = plan_collection_dict.get("buffered_plan_keys")

        if loaded_plan_keys is not None and plan_key in loaded_plan_keys:
            if pair_plan_to_be_deleted.port is not None:
                plan_web_client: StreetBookServiceHttpClient = (
                    StreetBookServiceHttpClient.set_or_get_if_instance_exists(pair_plan_to_be_deleted.host,
                                                                                 pair_plan_to_be_deleted.port))
            else:
                err_str_ = f"pair_plan object has no port;;; {pair_plan_to_be_deleted=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=500)

            if plan_web_client is None:
                err_str_ = ("Can't find any web_client present in server cache dict for ongoing plan of "
                            f"{port=}, ignoring this plan delete, likely bug in server cache dict handling, "
                            f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])};;; "
                            f"{pair_plan_to_be_deleted=}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            if is_ongoing_plan(pair_plan_to_be_deleted):
                err_str_ = ("This plan is ongoing: Deletion of ongoing plan is not supported, "
                            "ignoring this plan delete, try again once it is"
                            f"not ongoing, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # removing and updating relative models
            try:
                plan_web_client.put_plan_to_snooze_query_client()
            except Exception as e:
                err_str_ = ("Some error occurred in executor while setting plan to SNOOZED state, ignoring "
                            f"delete of this plan, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}, "
                            f"exception: {e}, ;;; {pair_plan_to_be_deleted=}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
            self._close_executor_server(pair_plan_to_be_deleted.id)  # closing executor

            # Dropping database for this plan
            code_gen_projects_dir = PurePath(__file__).parent.parent.parent
            executor_config_file_path = (code_gen_projects_dir / "street_book" /
                                         "data" / f"config.yaml")
            if os.path.exists(executor_config_file_path):
                server_config_yaml_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(str(executor_config_file_path)))
                mongo_server_uri = server_config_yaml_dict.get("mongo_server")
                if mongo_server_uri is not None:
                    self._drop_executor_db_for_deleting_pair_plan(mongo_server_uri, pair_plan_to_be_deleted.id,
                                                                   sec_id, side)
                else:
                    err_str_ = (f"key 'mongo_server' missing in street_book/data/config.yaml, ignoring this"
                                f"plan delete, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                    logging.error(err_str_)
                    raise HTTPException(detail=err_str_, status_code=400)
            else:
                err_str_ = (f"Config file for {port=} missing, must exists since executor is running from this"
                            f"config, ignoring this plan delete, symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)

            # Removing plan_key from loaded plan keys
            async with PlanCollection.reentrant_lock:
                plan_key = get_plan_key_from_pair_plan(pair_plan_to_be_deleted)
                obj_id = 1
                plan_collection: PlanCollection = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_plan_collection_by_id_http(obj_id))

                loaded_plan_keys = plan_collection.loaded_plan_keys
                if loaded_plan_keys is not None:
                    try:
                        loaded_plan_keys.remove(plan_key)
                    except ValueError as val_err:
                        if "x not in list" in str(val_err):
                            logging.error(f"Unexpected: Can't find {plan_key=} in plan_collection's loaded"
                                          f"keys while deleting plan;;; {plan_collection=}")
                        else:
                            logging.error(f"Something unexpected happened while removing {plan_key=} from "
                                          f"loaded plan_keys in plan_collection - ignoring this plan_key removal;;; "
                                          f"{plan_collection=}")
                        return
                else:
                    logging.error(f"Unexpected: Can't find {plan_key=} in plan_collection's loaded"
                                  f"keys while deleting plan - loaded_plan_keys found None;;; {plan_collection}")
                    return

                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_collection_http(
                    plan_collection, return_obj_copy=False)

            # Removing PlanView for this plan
            photo_book_service_http_client.delete_plan_view_client(pair_plan_to_be_deleted.id)

            # setting plan alert state to False for this plan_id
            symbol_side1 = symbol_side_key(pair_plan_to_be_deleted.pair_plan_params.plan_leg1.sec.sec_id,
                                           pair_plan_to_be_deleted.pair_plan_params.plan_leg1.side)
            symbol_side2 = symbol_side_key(pair_plan_to_be_deleted.pair_plan_params.plan_leg2.sec.sec_id,
                                           pair_plan_to_be_deleted.pair_plan_params.plan_leg2.side)
            log_book_service_http_client.enable_disable_plan_alert_create_query_client(pair_plan_to_be_deleted.id,
                                                                                            [symbol_side1,
                                                                                             symbol_side2],
                                                                                            False)
        elif buffered_plan_keys is not None and plan_key in buffered_plan_keys:
            # Removing plan_key from buffered plan keys
            async with PlanCollection.reentrant_lock:
                plan_key = get_plan_key_from_pair_plan(pair_plan_to_be_deleted)
                obj_id = 1
                plan_collection: PlanCollection = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_plan_collection_by_id_http(obj_id))

                try:
                    plan_collection.buffered_plan_keys.remove(plan_key)
                except ValueError as val_err:
                    if "x not in list" in str(val_err):
                        logging.error(f"Unexpected: Can't find {plan_key=} in plan_collection's buffered"
                                      f"keys while deleting plan;;; {plan_collection=}")
                    else:
                        logging.error(f"Something unexpected happened while removing {plan_key=} from "
                                      f"loaded plan_keys in plan_collection - ignoring this plan_key removal;;; "
                                      f"{plan_collection=}")
                    return

                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_collection_http(
                    plan_collection, return_obj_copy=False)

            # Removing PlanView for this plan
            photo_book_service_http_client.delete_plan_view_client(pair_plan_to_be_deleted.id)

            # removing log key cache value form pair_plan_id_key cache
            pair_plan_id_key.pop(pair_plan_to_be_deleted.id, None)

        else:
            err_str_ = ("Unexpected: Plan is not found in loaded or buffer list, ignoring this plan delete, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

    async def unload_pair_plans(self, stored_plan_collection_obj: PlanCollection,
                                 updated_plan_collection_obj: PlanCollection) -> None:
        updated_plan_collection_loaded_plan_keys_frozenset = frozenset(updated_plan_collection_obj.loaded_plan_keys)
        stored_plan_collection_loaded_plan_keys_frozenset = frozenset(stored_plan_collection_obj.loaded_plan_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_plan_keys_frozenset = stored_plan_collection_loaded_plan_keys_frozenset.difference(
            updated_plan_collection_loaded_plan_keys_frozenset)
        if len(unloaded_plan_keys_frozenset) != 0:
            unloaded_plan_key: str
            for unloaded_plan_key in unloaded_plan_keys_frozenset:
                if unloaded_plan_key in updated_plan_collection_obj.buffered_plan_keys:  # unloaded not deleted
                    pair_plan_id: int = get_id_from_plan_key(unloaded_plan_key)
                    pair_plan = \
                        await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_read_pair_plan_by_id_http(pair_plan_id))
                    if pair_plan.port is not None:
                        street_book_web_client: StreetBookServiceHttpClient = (
                            self.port_to_executor_http_client_dict.get(pair_plan.port))
                    else:
                        err_str_ = (f"pair_plan object has no port while unloading - "
                                    f"ignoring this plan unload;;; {pair_plan=}")
                        logging.error(err_str_)
                        raise HTTPException(detail=err_str_, status_code=400)

                    if street_book_web_client is None:
                        err_str_ = ("Can't find any web_client present in server cache dict for ongoing plan of "
                                    f"{pair_plan.port=}, ignoring this plan unload,"
                                    f"likely bug in server cache dict handling;;; {pair_plan=}")
                        logging.error(err_str_)
                        raise HTTPException(status_code=400, detail=err_str_)

                    if is_ongoing_plan(pair_plan):
                        error_str = f"unloading an ongoing pair plan key: {unloaded_plan_key} is not supported, " \
                                    f"current {pair_plan.plan_state=}, " \
                                    f"pair_plan_key: {get_pair_plan_log_key(pair_plan)};;; {pair_plan=}"
                        logging.error(error_str)
                        raise HTTPException(status_code=400, detail=error_str)
                    elif pair_plan.plan_state in [PlanState.PlanState_DONE, PlanState.PlanState_READY,
                                                    PlanState.PlanState_SNOOZED]:
                        # removing and updating relative models
                        try:
                            street_book_web_client.put_plan_to_snooze_query_client()
                            logging.info(f"Plan set to Snooze state, {unloaded_plan_key=};;; {pair_plan=}")
                        except Exception as e:
                            err_str_ = (
                                "Some error occurred in executor while setting plan to SNOOZED state, ignoring "
                                f"unload of this plan, pair_plan_key: {get_pair_plan_log_key(pair_plan)}, ;;;"
                                f"{pair_plan=}")
                            logging.error(err_str_)
                            raise HTTPException(status_code=500, detail=err_str_)

                        pair_plan_json = {
                            "_id": pair_plan_id,
                            "plan_state": PlanState.PlanState_SNOOZED
                        }
                        pair_plan_obj = (
                            await EmailBookServiceRoutesCallbackBaseNativeOverride.
                            underlying_partial_update_pair_plan_http(pair_plan_json))

                        self._close_executor_server(pair_plan.id)    # closing executor
                    else:
                        err_str_ = (f"Unloading plan with plan_state: {pair_plan.plan_state} is not supported,"
                                    f"try unloading when start is READY or DONE, pair_plan_key: "
                                    f"{get_pair_plan_log_key(pair_plan)};;; {pair_plan=}")
                        logging.error(err_str_)
                        raise Exception(err_str_)

                    # setting plan alert state to False for this plan_id
                    symbol_side1 = symbol_side_key(pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                   pair_plan.pair_plan_params.plan_leg1.side)
                    symbol_side2 = symbol_side_key(pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                   pair_plan.pair_plan_params.plan_leg2.side)
                    log_book_service_http_client.enable_disable_plan_alert_create_query_client(
                        pair_plan.id, [symbol_side1, symbol_side2], False)
                # else: deleted not unloaded - nothing to do , DB will remove entry

    async def reload_pair_plans(self, stored_plan_collection_obj: PlanCollection,
                                 updated_plan_collection_obj: PlanCollection) -> None:
        updated_plan_collection_buffered_plan_keys_frozenset = frozenset(
            updated_plan_collection_obj.buffered_plan_keys)
        stored_plan_collection_buffered_plan_keys_frozenset = frozenset(
            stored_plan_collection_obj.buffered_plan_keys)
        # existing items in stored buffered frozenset but not in the updated stored frozen set need to
        # move to ready state
        reloaded_plan_keys_frozenset = stored_plan_collection_buffered_plan_keys_frozenset.difference(
            updated_plan_collection_buffered_plan_keys_frozenset)
        if len(reloaded_plan_keys_frozenset) != 0:
            logging.debug(f"found {len(reloaded_plan_keys_frozenset)} to load from buffered;;;"
                          f"{reloaded_plan_keys_frozenset=}")
            reloaded_plan_key: str
            for reloaded_plan_key in reloaded_plan_keys_frozenset:
                if reloaded_plan_key in updated_plan_collection_obj.loaded_plan_keys:  # loaded not deleted
                    pair_plan_id: int = get_id_from_plan_key(reloaded_plan_key)
                    pair_plan = \
                        await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_by_id_http(
                            pair_plan_id)

                    # clear plan view cache data for pair plan on unload
                    # unload_plan should be False if reached here (reload case)
                    log_str = plan_view_client_call_log_str(
                        PlanViewBaseModel, photo_book_service_http_client.patch_all_plan_view_client,
                        UpdateType.SNAPSHOT_TYPE,
                        _id=pair_plan.id, average_premium=0, market_premium=0, plan_alert_count=0,
                        balance_notional=0, max_single_leg_notional=0,
                        total_fill_buy_notional=0, total_fill_sell_notional=0,
                        plan_alert_aggregated_severity=Severity.Severity_UNSPECIFIED.value,
                        unload_plan=False, recycle_plan=False)
                    logging.db(log_str)

                    # setting plan alert state to True for this plan_id
                    symbol_side1 = symbol_side_key(pair_plan.pair_plan_params.plan_leg1.sec.sec_id,
                                                   pair_plan.pair_plan_params.plan_leg1.side)
                    symbol_side2 = symbol_side_key(pair_plan.pair_plan_params.plan_leg2.sec.sec_id,
                                                   pair_plan.pair_plan_params.plan_leg2.side)
                    log_book_service_http_client.enable_disable_plan_alert_create_query_client(pair_plan_id,
                                                                                                    [symbol_side1,
                                                                                                     symbol_side2],
                                                                                                    True)

                    # starting snoozed server
                    await self._start_executor_server(pair_plan)

                # else: deleted not loaded - nothing to do , DB will remove entry

    async def update_plan_collection_pre(self, updated_plan_collection_obj: PlanCollection):
        stored_plan_collection_obj = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_read_plan_collection_by_id_http(updated_plan_collection_obj.id))

        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_plan_collection_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # handling unloading pair_plans
        await self.unload_pair_plans(stored_plan_collection_obj, updated_plan_collection_obj)

        # handling reloading pair_plan
        await self.reload_pair_plans(stored_plan_collection_obj, updated_plan_collection_obj)

        return updated_plan_collection_obj

    async def get_plan_collection(self) -> PlanCollection:
        plan_collections = (
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_collection_http())

        if len(plan_collections) != 1:
            err_str_ = (f"Unexpected: multiple plan collection obj found, expected 1;;;"
                        f"{plan_collections=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

        plan_collection = plan_collections[0]
        return plan_collection

    async def unload_plan_from_plan_id_query_pre(
            self, plan_collection_class_type: Type[PlanCollection], plan_id: int):
        async with PlanCollection.reentrant_lock:

            pair_plan = await (
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_by_id_http(plan_id))
            plan_key = get_plan_key_from_pair_plan(pair_plan)

            plan_collection = await self.get_plan_collection()
            for loaded_plan_key in plan_collection.loaded_plan_keys:
                if loaded_plan_key == plan_key:
                    # plan found to unload
                    plan_collection.loaded_plan_keys.remove(plan_key)
                    plan_collection.buffered_plan_keys.insert(0, plan_key)
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_collection_http(
                        plan_collection)
                    break
            else:
                err_str_ = f"No loaded plan found with {plan_id=} in plan_collection;;;{plan_collection=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    async def reload_plan_from_plan_id_query_pre(
            self, plan_collection_class_type: Type[PlanCollection], plan_id: int):
        async with PlanCollection.reentrant_lock:
            plan_collection = await self.get_plan_collection()
            pair_plan = await (
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_by_id_http(plan_id))
            plan_key = get_plan_key_from_pair_plan(pair_plan)

            for loaded_plan_key in plan_collection.buffered_plan_keys:
                if loaded_plan_key == plan_key:
                    # plan found to unload
                    plan_collection.buffered_plan_keys.remove(plan_key)
                    plan_collection.loaded_plan_keys.append(plan_key)
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_plan_collection_http(
                        plan_collection)
                    break
            else:
                err_str_ = f"No buffered plan found with {plan_id=} in plan_collection;;;{plan_collection=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    async def get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_pre(
            self, pair_plan_class_type: Type[PairPlan], sec_id: str, side: Side):
        """
        checks if ongoing plan is found with sec_id and side in any leg from all plans, else returns
        pair_plan if non-ongoing but single match is found with sec_id and side in any leg else returns None
        """
        read_pair_plan_filter = get_ongoing_or_all_pair_plans_by_sec_id(sec_id, side)
        pair_plans: List[PairPlan] = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                         underlying_read_pair_plan_http(read_pair_plan_filter))
        if len(pair_plans) == 1:
            # if single match is found then either it is ongoing from multiple same matched plans or it is single
            # non-ongoing plan - both are accepted
            return pair_plans
        # else not required: returns None if found multiple matching symbol-side non-ongoing plans
        return []

    async def get_all_pair_plans_from_symbol_side_query_pre(self, pair_plan_class_type: Type[PairPlan],
                                                             sec_id: str, side: Side):
        return await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                      underlying_read_pair_plan_http(get_all_pair_plan_from_symbol_n_side(sec_id, side)))

    async def create_admin_control_pre(self, admin_control_obj: AdminControl):
        match admin_control_obj.command_type:
            case CommandType.CLEAR_STRAT:
                pair_plan_list: List[PairPlan] = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_http())
                for pair_plan_ in pair_plan_list:
                    leg1_lock_file_path, leg2_lock_file_path = (
                        self.get_lock_file_names_from_pair_plan(pair_plan_))
                    if leg1_lock_file_path and os.path.exists(leg1_lock_file_path):
                        os.remove(leg1_lock_file_path)
                    if leg2_lock_file_path and os.path.exists(leg2_lock_file_path):
                        os.remove(leg2_lock_file_path)
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_msgspec_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_admin_control_pre failed. unrecognized command_type: {other_}")

    async def create_contact_limits_pre(self, contact_limits_obj: ContactLimits):
        contact_limits_obj.eligible_brokers_update_count = 0

    async def create_contact_limits_post(self, contact_limits_objs: ContactLimits):
        async with ShadowBrokers.reentrant_lock:
            await handle_shadow_broker_creates(
                contact_limits_objs,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_shadow_brokers_http)

    async def update_contact_limits_pre(self, updated_contact_limits_obj: ContactLimits):
        if updated_contact_limits_obj.eligible_brokers:
            stored_contact_limits_obj = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_contact_limits_by_id_http(
                    updated_contact_limits_obj.id))
            updated_contact_limits_obj.eligible_brokers_update_count = (
                    stored_contact_limits_obj.eligible_brokers_update_count + 1)
        return updated_contact_limits_obj

    async def update_contact_limits_post(self, updated_contact_limits_obj: ContactLimits):
        async with ShadowBrokers.reentrant_lock:
            await handle_shadow_broker_updates(
                updated_contact_limits_obj,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_by_id_list_shadow_brokers_http)

    async def partial_update_contact_limits_pre(self, stored_contact_limits_obj_json: Dict[str, Any],
                                                  updated_contact_limits_obj_json: Dict[str, Any]):
        if updated_contact_limits_obj_json.get("eligible_brokers") is not None:
            stored_eligible_brokers_update_count = stored_contact_limits_obj_json.get("eligible_brokers_update_count")
            if stored_eligible_brokers_update_count is None:
                stored_eligible_brokers_update_count = 0
            updated_contact_limits_obj_json["eligible_brokers_update_count"] = (
                    stored_eligible_brokers_update_count + 1)
        return updated_contact_limits_obj_json

    async def partial_update_contact_limits_post(self, updated_contact_limits_obj_json: Dict[str, Any]):
        async with ShadowBrokers.reentrant_lock:
            await handle_shadow_broker_updates(
                updated_contact_limits_obj_json,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_all_shadow_brokers_http,
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_by_id_list_shadow_brokers_http)

    async def filtered_notify_pair_plan_update_query_ws_pre(self):
        return filter_ws_pair_plan

    async def _update_system_control_post(
            self, stored_system_control_json: Dict | SystemControl,
            updated_system_control_json_or_obj: Dict | SystemControl):
        if isinstance(stored_system_control_json, dict):
            stored_pause_all_plans = stored_system_control_json.get("pause_all_plans")
            stored_load_buffer_plans = stored_system_control_json.get("load_buffer_plans")
            stored_cxl_baskets = stored_system_control_json.get("cxl_baskets")
        else:
            stored_pause_all_plans = stored_system_control_json.pause_all_plans
            stored_load_buffer_plans = stored_system_control_json.load_buffer_plans
            stored_cxl_baskets = stored_system_control_json.cxl_baskets

        if isinstance(updated_system_control_json_or_obj, dict):
            updated_pause_all_plans = updated_system_control_json_or_obj.get("pause_all_plans")
            updated_load_buffer_plans = updated_system_control_json_or_obj.get("load_buffer_plans")
            updated_cxl_baskets = updated_system_control_json_or_obj.get("cxl_baskets")
        else:
            updated_pause_all_plans = updated_system_control_json_or_obj.pause_all_plans
            updated_load_buffer_plans = updated_system_control_json_or_obj.load_buffer_plans
            updated_cxl_baskets = updated_system_control_json_or_obj.cxl_baskets
        if not stored_pause_all_plans and updated_pause_all_plans:
            script_path: str = str(CURRENT_PROJECT_DIR / "pyscripts" / "pause_all_active_plans.py")
            cmd: List[str] = ["python", script_path, "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered pause_all_plan event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")
        if not stored_load_buffer_plans and updated_load_buffer_plans:
            script_path: str = str(CURRENT_PROJECT_DIR / "pyscripts" / "load_all_buffer_plans.py")
            cmd: List[str] = ["python", script_path, "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered load_buffer_plans event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")
        if not stored_cxl_baskets and updated_cxl_baskets:
            script_path: str = str(CURRENT_PROJECT_DIR / "pyscripts" / "cancel_all_basket_chores.py")
            cmd: List[str] = ["python", script_path, "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered cxl_baskets event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")

    async def update_system_control_pre(self, stored_system_control_obj: SystemControl,
                                        updated_system_control_obj: SystemControl):

        stored_kill_switch = stored_system_control_obj.kill_switch
        updated_kill_switch = updated_system_control_obj.kill_switch
        if not stored_kill_switch and updated_kill_switch:
            if not EmailBookServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate:
                res = await self.bartering_link.trigger_kill_switch()
                if not res:
                    err_str_ = "bartering_link.trigger_kill_switch failed"
                    logging.critical(err_str_)
                    raise HTTPException(detail=err_str_, status_code=500)
                # else not required: if res is fine make db update
            # else not required: avoid bartering_link.trigger_kill_switch if RecoveredKillSwitchUpdate is True updated
            # from init check
        elif stored_kill_switch and not updated_kill_switch:
            res = await self.bartering_link.revoke_kill_switch_n_resume_bartering()
            if not res:
                err_str_ = "bartering_link.revoke_kill_switch_n_resume_bartering failed"
                logging.critical(err_str_)
                raise HTTPException(detail=err_str_, status_code=500)
        # else not required: other case doesn't need bartering link call
        return updated_system_control_obj

    async def update_system_control_post(self, stored_system_control_obj: SystemControl,
                                         updated_system_control_obj: SystemControl):
        await self._update_system_control_post(stored_system_control_obj, updated_system_control_obj)

    async def log_simulator_reload_config_query_pre(
            self, log_simulator_reload_config_class_type: Type[LogSimulatorReloadConfig]):
        self.bartering_link.reload_contact_configs()
        return []

    async def partial_update_system_control_pre(self, stored_system_control_obj_json: Dict[str, Any],
                                                updated_system_control_obj_json: Dict[str, Any]):
        kill_switch_update = updated_system_control_obj_json.get("kill_switch")
        if kill_switch_update is not None:
            stored_kill_switch = stored_system_control_obj_json.get("kill_switch")
            if not stored_kill_switch and kill_switch_update:
                if not EmailBookServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate:
                    res = await self.bartering_link.trigger_kill_switch()
                    if not res:
                        err_str_ = "bartering_link.trigger_kill_switch failed"
                        logging.critical(err_str_)
                        raise HTTPException(detail=err_str_, status_code=500)
                    logging.critical("Invoked kill switch")
                    # else not required: if res is fine make db update
                # else not required: avoid bartering_link.trigger_kill_switch if RecoveredKillSwitchUpdate is True
                # updated from init check
            elif stored_kill_switch and not kill_switch_update:
                res = await self.bartering_link.revoke_kill_switch_n_resume_bartering()
                if not res:
                    err_str_ = "bartering_link.revoke_kill_switch_n_resume_bartering failed"
                    logging.critical(err_str_)
                    raise HTTPException(detail=err_str_, status_code=500)
                logging.critical("Removed kill switch. Bartering resumed")
            # else not required: other case doesn't need bartering link call
        return updated_system_control_obj_json

    async def partial_update_system_control_post(self, stored_system_control_obj_json: Dict[str, Any],
                                                 updated_system_control_obj_json: Dict[str, Any]):
        await self._update_system_control_post(stored_system_control_obj_json, updated_system_control_obj_json)

    async def reload_bartering_data_query_pre(self, reload_bartering_data_class_type: Type[ReloadBarteringData]):
        if self.static_data is not None:
            self.static_data_periodic_refresh()
        else:
            logging.error("reload_bartering_data_query called when static_data is not initialized or "
                          "is None due to some other reason")
        return []

    async def sample_file_upload_query_pre(self, upload_file: UploadFile, save_file_destination: str):
        """
        Used in verifying file upload functionality with http client in test
        :param upload_file:
        :param save_file_destination:
        :return:
        """
        content = await upload_file.read()
        with open(save_file_destination, "wb") as file:
            file.write(content)
        return []

    async def sample_file_upload_button_query_pre(self, upload_file: UploadFile, sample_param: str,
                                                  disallow_duplicate_file_upload: bool = False):
        """
        Used in verifying file upload functionality with http client for SampleModel based query in test
        :param upload_file:
        :return:
        """
        save_file_destination = PurePath(__file__).parent.parent / "generated" / "sample_file.txt"
        content = await upload_file.read()
        with open(save_file_destination, "wb") as file:
            file.write(content)
        return []

    async def partial_update_sample_model_post(self, stored_sample_model_obj_json: Dict[str, Any],
                                               updated_sample_model_obj_json: Dict[str, Any]):
        # @@@ Used in test to verify patch's post call doesn't get stored == updated obj after generic call
        if stored_sample_model_obj_json == updated_sample_model_obj_json:
            raise HTTPException(status_code=400,
                                detail="Unexpected: Found stored_sample_model_obj_json == "
                                       "updated_sample_model_obj_json, must be different;;; "
                                       f"{stored_sample_model_obj_json=}, {updated_sample_model_obj_json=}")

    async def partial_update_all_sample_model_post(self, stored_sample_model_dict_list: List[Dict[str, Any]],
                                                   updated_sample_model_dict_list: List[Dict[str, Any]]):
        # @@@ Used in test to verify patch_all's post call doesn't get stored == updated obj list after generic call
        if stored_sample_model_dict_list == updated_sample_model_dict_list:
            raise HTTPException(status_code=400,
                                detail="Unexpected: Found stored_sample_model_dict_list == "
                                       "updated_sample_model_dict_list, must be different;;; "
                                       f"{stored_sample_model_dict_list=}, {updated_sample_model_dict_list=}")

    async def register_pair_plan_for_recovery_query_pre(self, pair_plan_class_type: Type[PairPlan],
                                                         pair_plan_id: int):
        if not pair_plan_id:
            err_str_ = f"register_pair_plan_for_recovery failed, {pair_plan_id=} found None, expected int"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)
        # else not received - received pair_plan_id

        if self.pair_plan_id_to_executor_process_id_dict.get(pair_plan_id) is not None:
            err_str_ = f"register_pair_plan_for_recovery failed, {pair_plan_id=} already registered for recovery"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)

        # check for valid pair_plan_id and register if present in loaded list
        try:
            pair_plan_obj: PairPlan = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                               underlying_read_pair_plan_by_id_http(pair_plan_id))
            plan_key: str = get_plan_key_from_pair_plan(pair_plan_obj)
            plan_collection_obj: PlanCollection = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                                           underlying_read_plan_collection_by_id_http(1))
            if plan_key not in plan_collection_obj.loaded_plan_keys:
                err_str_ = (f"register_pair_plan_for_recovery_failed, {pair_plan_id=} not found in loaded plans;;;"
                            f"{pair_plan_obj=}, {plan_collection_obj=}")
                logging.error(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
            # else - valid pair plan id and not monitored

            # register pair plan
            self.pair_plan_id_to_executor_process_id_dict[pair_plan_id] = None
            return [pair_plan_obj]
        except Exception as exp:
            err_str_ = f"register_pair_plan_for_recovery failed, exception: {exp}"
            logging.exception(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)

    async def get_loaded_plans_query_pre(self, pair_plan_class_type: Type[PairPlan]):
        pair_plan_list = []
        async with PlanCollection.reentrant_lock:
            async with PairPlan.reentrant_lock:
                plan_collection_list: List[PlanCollection] = \
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_plan_collection_http()
                if plan_collection_list:
                    plan_collection = plan_collection_list[0]
                    for plan_key in plan_collection.loaded_plan_keys:
                        pair_plan_id = get_id_from_plan_key(plan_key)
                        pair_plan = await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_plan_by_id_http(pair_plan_id)
                        pair_plan_list.append(pair_plan)
        return pair_plan_list

    async def handle_plan_pause_from_plan_id_log_query_pre(
            self, handle_plan_pause_from_plan_id_log_class_type: Type[HandlePlanPauseFromPlanIdLog],
            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")

            plan_id = get_plan_id_from_executor_log_file_name(source_file)

            if plan_id is None:
                err_str_ = (f"Can't find plan id in {source_file=} from payload passed to "
                            f"handle_plan_pause_from_log_query - Can't pause plan intended to be paused;;; "
                            f"payload: {log_data}")
                logging.critical(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
            # else not required: using found plan_id

            msg_brief: str = message.split(";;;")[0]
            err_: str = f"pausing pattern matched for plan with {plan_id=};;;{msg_brief=}"

            update_pair_plan_json = {"_id": plan_id, "plan_state": PlanState.PlanState_PAUSED}
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_pair_plan_http(
                update_pair_plan_json)
            err_ = f"Force paused {plan_id=}, {err_}"
            logging.critical(err_)
        return []

    async def handle_plan_pause_from_symbol_side_log_query_pre(
            self, handle_plan_pause_from_symbol_side_log_class_type: Type[HandlePlanPauseFromSymbolSideLog],
            payload: List[Dict[str, Any]]):
        for log_data in payload:
            message = log_data.get("message")

            symbol_side_set = get_symbol_n_side_from_log_line(message)
            symbol_side: str = list(symbol_side_set)[0]
            symbol, side = symbol_side.split("-")

            plan_id: int | None = self.plan_id_by_symbol_side_dict.get(symbol_side)

            if plan_id is None:
                pair_plan_obj: PairPlan = await self._get_pair_plan_obj_from_symbol_side_async(symbol, Side(side))
                if pair_plan_obj is None:
                    raise HTTPException(detail=f"No Ongoing pair plan found for symbol_side: {symbol_side}",
                                        status_code=400)

                plan_id = pair_plan_obj.id
                for symbol_side in symbol_side_set:
                    self.plan_id_by_symbol_side_dict[symbol_side] = plan_id

            msg_brief: str = message.split(";;;")[0]
            err_: str = f"pausing pattern matched for plan with {plan_id=};;;{msg_brief=}"

            update_pair_plan_json = {"_id": plan_id, "plan_state": PlanState.PlanState_PAUSED}
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_pair_plan_http(
                update_pair_plan_json)
            err_ = f"Force paused {plan_id=}, {err_}"
            logging.critical(err_)
        return []

    async def handle_pos_disable_task(self, plan_id, message):
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
                message, source_file = data

                plan_id = get_plan_id_from_executor_log_file_name(source_file)

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
        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            message_n_source_file_tuple_list.append((message, source_file))
        self.pos_disable_from_plan_id_log_queue.put(message_n_source_file_tuple_list)
        return []

    async def _get_pair_plan_obj_from_symbol_side_async(self, symbol: str, side: Side) -> PairPlan | None:
        pair_plan_list: List[PairPlan] = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http(
                        sec_id=symbol, side=side))
        if len(pair_plan_list) == 0:
            return None
        elif len(pair_plan_list) == 1:
            pair_plan_obj: PairPlan = pair_plan_list[0]
            return pair_plan_obj

    def _get_pair_plan_obj_from_symbol_side(self, symbol: str, side: Side) -> PairPlan | None:
        # coro needs public method
        run_coro = (EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http(
                        sec_id=symbol, side=side))
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            pair_plan_list: List[PairPlan] = future.result()
        except Exception as e:
            logging.exception(
                f"underlying_get_ongoing_or_single_exact_non_ongoing_pair_plan_from_symbol_side_query_http "
                f"failed with exception: {e}")
            return None
        else:
            if len(pair_plan_list) == 0:
                return None
            elif len(pair_plan_list) == 1:
                pair_plan_obj: PairPlan = pair_plan_list[0]
                return pair_plan_obj

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
                    pair_plan_obj: PairPlan = self._get_pair_plan_obj_from_symbol_side(symbol, Side(side))
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
        message_n_source_file_tuple_list = []
        for log_data in payload:
            message = log_data.get("message")
            source_file = log_data.get("source_file")
            message_n_source_file_tuple_list.append((message, source_file))
        self.pos_disable_from_symbol_side_log_queue.put(message_n_source_file_tuple_list)
        return []


async def filter_ws_pair_plan(pair_plan_obj_json: Dict, obj_id_or_list: int | List[int], **kwargs):
    symbols = kwargs.get("symbols")
    pair_plan_params = pair_plan_obj_json.get("pair_plan_params")
    if pair_plan_params is not None:
        plan_leg1 = pair_plan_params.get("plan_leg1")
        plan_leg2 = pair_plan_params.get("plan_leg2")
        if plan_leg1 is not None and plan_leg2 is not None:
            security1 = plan_leg1.get("sec")
            security2 = plan_leg2.get("sec")
            if security1 is not None and security2 is not None:
                sec1_id = security1.get("sec_id")
                sec2_id = security2.get("sec_id")
                if sec1_id in symbols or sec2_id in symbols:
                    return True
    return False
