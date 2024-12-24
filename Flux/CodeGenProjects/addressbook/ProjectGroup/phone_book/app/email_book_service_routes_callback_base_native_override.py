# python imports
import copy
import glob
import logging
import signal
import subprocess
import stat
import time
from typing import Set
from datetime import datetime
import threading
import requests

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
    CURRENT_PROJECT_SCRIPTS_DIR, create_md_shell_script, MDShellEnvData, ps_host, get_new_portfolio_status,
    get_new_portfolio_limits, get_new_chore_limits, CURRENT_PROJECT_DATA_DIR, is_ongoing_strat,
    get_strat_key_from_pair_strat, get_id_from_strat_key, get_new_strat_view_obj,
    get_reset_log_book_cache_wrapper_pattern,
    pair_strat_client_call_log_str, UpdateType,
    get_matching_strat_from_symbol_n_side)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_pair_strat_log_key, get_pair_strat_dict_log_key, pair_strat_id_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.aggregate import (
    get_ongoing_pair_strat_filter, get_all_pair_strat_from_symbol_n_side, get_ongoing_or_all_pair_strats_by_sec_id)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.ORMModel.photo_book_service_model_imports import (
    StratViewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from FluxPythonUtils.scripts.service import Service
from FluxPythonUtils.scripts.utility_functions import (
    get_pid_from_port, except_n_log_alert, is_process_running, submit_task_with_first_completed_wait,
    handle_refresh_configurable_data_members, parse_to_int, set_package_logger_level)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import get_bartering_link
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager


class EmailBookServiceRoutesCallbackBaseNativeOverride(Service, EmailBookServiceRoutesCallback):
    underlying_read_portfolio_status_http: Callable[..., Any] | None = None
    underlying_read_portfolio_status_http_json_dict: Callable[..., Any] | None = None
    underlying_create_portfolio_status_http: Callable[..., Any] | None = None
    underlying_read_chore_limits_http: Callable[..., Any] | None = None
    underlying_read_chore_limits_http_json_dict: Callable[..., Any] | None = None
    underlying_create_chore_limits_http: Callable[..., Any] | None = None
    underlying_read_portfolio_limits_http_json_dict: Callable[..., Any] | None = None
    underlying_create_portfolio_limits_http: Callable[..., Any] | None = None
    underlying_read_pair_strat_http: Callable[..., Any] | None = None
    underlying_read_pair_strat_http_json_dict: Callable[..., Any] | None = None
    underlying_read_portfolio_status_by_id_http: Callable[..., Any] | None = None
    underlying_update_portfolio_status_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_http_json_dict: Callable[..., Any] | None = None
    underlying_create_strat_collection_http: Callable[..., Any] | None = None
    underlying_update_strat_collection_http: Callable[..., Any] | None = None
    underlying_partial_update_pair_strat_http: Callable[..., Any] | None = None
    underlying_partial_update_pair_strat_http_json_dict: Callable[..., Any] | None = None
    underlying_update_pair_strat_to_non_running_state_query_http: Callable[..., Any] | None = None
    underlying_read_pair_strat_by_id_http: Callable[..., Any] | None = None
    underlying_partial_update_all_pair_strat_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_by_id_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_by_id_http_json_dict: Callable[..., Any] | None = None
    underlying_read_system_control_by_id_http: Callable[..., Any] | None = None
    underlying_read_system_control_by_id_http_json_dict: Callable[..., Any] | None = None
    underlying_partial_update_system_control_http: Callable[..., Any] | None = None
    underlying_read_system_control_http: Callable[..., Any] | None = None
    underlying_read_system_control_http_json_dict: Callable[..., Any] | None = None
    underlying_create_system_control_http: Callable[..., Any] | None = None
    underlying_read_portfolio_limits_http: Callable[..., Any] | None = None
    underlying_read_portfolio_limits_by_id_http: Callable[..., Any] | None = None

    Fx_SO_FilePath = CURRENT_PROJECT_SCRIPTS_DIR / f"fx_so.sh"
    RecoveredKillSwitchUpdate: bool = False

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.FastApi.email_book_service_http_routes_imports import (
            underlying_read_portfolio_status_http, underlying_create_portfolio_status_http,
            underlying_read_chore_limits_http, underlying_create_chore_limits_http,
            underlying_create_portfolio_limits_http,
            underlying_read_pair_strat_http, underlying_read_portfolio_status_by_id_http,
            underlying_update_portfolio_status_http, underlying_read_strat_collection_http,
            underlying_create_strat_collection_http, underlying_update_strat_collection_http,
            underlying_partial_update_pair_strat_http, underlying_update_pair_strat_to_non_running_state_query_http,
            underlying_read_pair_strat_by_id_http, underlying_partial_update_all_pair_strat_http,
            underlying_read_strat_collection_by_id_http, underlying_read_portfolio_limits_http,
            underlying_read_system_control_by_id_http, underlying_partial_update_system_control_http,
            underlying_read_system_control_http, underlying_create_system_control_http,
            underlying_read_portfolio_status_http_json_dict, underlying_read_system_control_http_json_dict,
            underlying_read_chore_limits_http_json_dict, underlying_read_portfolio_limits_http_json_dict,
            underlying_read_strat_collection_http_json_dict, underlying_read_system_control_by_id_http_json_dict,
            underlying_read_pair_strat_http_json_dict, underlying_partial_update_pair_strat_http_json_dict,
            underlying_read_strat_collection_by_id_http_json_dict, underlying_read_portfolio_limits_by_id_http)
        cls.underlying_read_portfolio_status_http = underlying_read_portfolio_status_http
        cls.underlying_read_portfolio_status_http_json_dict = underlying_read_portfolio_status_http_json_dict
        cls.underlying_create_portfolio_status_http = underlying_create_portfolio_status_http
        cls.underlying_read_chore_limits_http = underlying_read_chore_limits_http
        cls.underlying_read_chore_limits_http_json_dict = underlying_read_chore_limits_http_json_dict
        cls.underlying_create_chore_limits_http = underlying_create_chore_limits_http
        cls.underlying_read_portfolio_limits_http_json_dict = underlying_read_portfolio_limits_http_json_dict
        cls.underlying_create_portfolio_limits_http = underlying_create_portfolio_limits_http
        cls.underlying_read_pair_strat_http = underlying_read_pair_strat_http
        cls.underlying_read_pair_strat_http_json_dict = underlying_read_pair_strat_http_json_dict
        cls.underlying_read_portfolio_status_by_id_http = underlying_read_portfolio_status_by_id_http
        cls.underlying_update_portfolio_status_http = underlying_update_portfolio_status_http
        cls.underlying_read_strat_collection_http = underlying_read_strat_collection_http
        cls.underlying_read_strat_collection_http_json_dict = underlying_read_strat_collection_http_json_dict
        cls.underlying_create_strat_collection_http = underlying_create_strat_collection_http
        cls.underlying_update_strat_collection_http = underlying_update_strat_collection_http
        cls.underlying_partial_update_pair_strat_http = underlying_partial_update_pair_strat_http
        cls.underlying_partial_update_pair_strat_http_json_dict = underlying_partial_update_pair_strat_http_json_dict
        cls.underlying_update_pair_strat_to_non_running_state_query_http = (
            underlying_update_pair_strat_to_non_running_state_query_http)
        cls.underlying_read_pair_strat_by_id_http = underlying_read_pair_strat_by_id_http
        cls.underlying_partial_update_all_pair_strat_http = underlying_partial_update_all_pair_strat_http
        cls.underlying_read_strat_collection_by_id_http = underlying_read_strat_collection_by_id_http
        cls.underlying_read_strat_collection_by_id_http_json_dict = underlying_read_strat_collection_by_id_http_json_dict
        cls.underlying_read_system_control_by_id_http = underlying_read_system_control_by_id_http
        cls.underlying_read_system_control_by_id_http_json_dict = underlying_read_system_control_by_id_http_json_dict
        cls.underlying_partial_update_system_control_http = underlying_partial_update_system_control_http
        cls.underlying_read_system_control_http = underlying_read_system_control_http
        cls.underlying_read_system_control_http_json_dict = underlying_read_system_control_http_json_dict
        cls.underlying_create_system_control_http = underlying_create_system_control_http
        cls.underlying_read_portfolio_limits_http = underlying_read_portfolio_limits_http
        cls.underlying_read_portfolio_limits_by_id_http = underlying_read_portfolio_limits_by_id_http

    def __init__(self):
        self.asyncio_loop = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.static_data: SecurityRecordManager | None = None
        # restricted variables: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {"USD|SGD": None}
        self.usd_fx: float | None = None
        self.pair_strat_id_to_executor_process_id_dict: Dict[int, int] = {}
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

        super().__init__()

    @staticmethod
    async def _check_n_create_portfolio_status():
        async with PortfolioStatus.reentrant_lock:
            portfolio_status_dict_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_portfolio_status_http_json_dict())
            if 0 == len(portfolio_status_dict_list):  # no portfolio status set yet, create one
                portfolio_status: PortfolioStatus = get_new_portfolio_status()
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_status_http(
                      portfolio_status, return_obj_copy=False)

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
    async def _check_n_create_portfolio_limits():
        async with PortfolioLimits.reentrant_lock:
            portfolio_limits_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_limits_http_json_dict())
            if 0 == len(portfolio_limits_list):  # no portfolio_limits set yet, create one
                portfolio_limits = get_new_portfolio_limits()
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_limits_http(
                    portfolio_limits, return_obj_copy=False)

    @staticmethod
    async def _check_n_create_strat_collection():
        async with StratCollection.reentrant_lock:
            strat_collection_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_strat_collection_http_json_dict())
            if len(strat_collection_list) == 0:
                created_strat_collection = StratCollection.from_kwargs(_id=1, loaded_strat_keys=[],
                                                                       buffered_strat_keys=[])
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_collection_http(
                    created_strat_collection, return_obj_copy=False)

    @staticmethod
    async def _check_and_create_start_up_models() -> bool:
        try:
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_portfolio_status()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_system_control()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_chore_limits()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_portfolio_limits()
            await EmailBookServiceRoutesCallbackBaseNativeOverride._check_n_create_strat_collection()
        except Exception as e:
            logging.exception(f"_check_and_create_start_up_models failed, exception: {e}")
            return False
        else:
            return True

    def _block_active_strat_with_restricted_security(self):
        pass

    def static_data_periodic_refresh(self):
        # for now only security restrictions are supported in refresh of static data
        # TODO LAZY: we may have to segregate static_data periodic_refresh and refresh when more is supported
        if self.static_data.refresh():
            self._block_active_strat_with_restricted_security()

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
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
                        self._block_active_strat_with_restricted_security()
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
                                err_str_ = (f"_check_and_create_portfolio_status_and_chore_n_portfolio_limits "
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
        pending_strats: List[PairStrat]
        pending_strats_id_list: List[int] = []

        if self.pair_strat_id_to_executor_process_id_dict:
            pending_strats = await self._async_check_running_executors(self.pair_strat_id_to_executor_process_id_dict)

            for strat in pending_strats:
                pending_strats_id_list.append(strat.id)

            for pair_strat_id in pending_strats_id_list:
                del self.pair_strat_id_to_executor_process_id_dict[pair_strat_id]

            if pending_strats:
                await self._async_start_executor_server_by_task_submit(pending_strats, is_crash_recovery=True)

    async def get_crashed_pair_strats(self, pair_strat_id, executor_process_id) -> PairStrat:
        pair_strat: PairStrat | None = None
        if not is_process_running(executor_process_id):
            logging.info(f"process for {pair_strat_id=} and {executor_process_id=} found killed, "
                         f"restarting again ...")

            pair_strat: PairStrat = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_pair_strat_by_id_http(pair_strat_id))

            # making strat state non-running - required for UI to know it is not running anymore and
            # avoid connections
            if pair_strat.is_executor_running or pair_strat.is_partially_running or pair_strat.port is not None:
                # If pair strat already exists and executor already have run before
                await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_update_pair_strat_to_non_running_state_query_http(pair_strat.id))
            # else not required: if it is newly created pair strat then already values are False

        return pair_strat

    async def _async_check_running_executors(self, pair_strat_id_to_executor_process_id_dict: Dict[int, int]) -> List[PairStrat]:
        tasks: List = []
        pair_strat_list: List[PairStrat] = []
        for pair_strat_id, executor_process_id in pair_strat_id_to_executor_process_id_dict.items():
            task = asyncio.create_task(self.get_crashed_pair_strats(pair_strat_id, executor_process_id), name=str(pair_strat_id))
            tasks.append(task)

        if tasks:
            pair_strat_list = await submit_task_with_first_completed_wait(tasks)
        return pair_strat_list

    async def _async_start_executor_server_by_task_submit(self, pending_strats: List[PairStrat],
                                                          is_crash_recovery: bool | None = False):
        tasks: List = []
        for idx, pending_strat in enumerate(pending_strats):
            task = asyncio.create_task(self._start_executor_server(pending_strat, is_crash_recovery), name=str(idx))
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
            MDShellEnvData(host=ps_host, port=ps_port, db_name=db_name, project_name="phone_book"))

        create_md_shell_script(md_shell_env_data, run_fx_symbol_overview_file_path, "SO")
        os.chmod(run_fx_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_fx_symbol_overview_file_path}"])

    async def async_recover_existing_executors(self) -> None:
        existing_pair_strats: List[PairStrat] = \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http()
        strat_collection_list: List[Dict] =  \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_collection_http_json_dict()

        if strat_collection_list:
            if len(strat_collection_list) == 1:
                strat_collection = strat_collection_list[0]
                loaded_strat_keys: List[str] = strat_collection.get("loaded_strat_keys")

                loaded_pair_strat_id_list: List[int] = []
                if loaded_strat_keys is not None:
                    for loaded_strat_key in loaded_strat_keys:
                        loaded_pair_strat_id_list.append(get_id_from_strat_key(loaded_strat_key))

                crashed_strats: List[PairStrat] = []
                for pair_strat in existing_pair_strats:
                    if pair_strat.id in loaded_pair_strat_id_list:
                        if pair_strat.port is not None:
                            # setting cache for executor client
                            self._update_port_to_executor_http_client_dict_from_updated_pair_strat(pair_strat.host,
                                                                                                   pair_strat.port)

                            street_book_http_client = self.port_to_executor_http_client_dict.get(pair_strat.port)
                            try:
                                # Checking if get-request works
                                street_book_http_client.get_all_ui_layout_client()
                            except requests.exceptions.Timeout:
                                # If timeout error occurs it is most probably that executor server got hung/stuck
                                # logging and killing this executor
                                logging.exception(f"Found executor with port: {pair_strat.port} in hung state, killing "
                                                  f"the executor process;;; pair_strat: {pair_strat}")
                                pid = get_pid_from_port(pair_strat.port)
                                os.kill(pid, signal.SIGKILL)

                                # Updating pair_strat
                                pair_strat_json = {
                                    "_id": pair_strat.id,
                                    "strat_state": StratState.StratState_ERROR,
                                    "is_partially_running": False,
                                    "is_executor_running": False,
                                    "port": None,
                                }

                                await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                       underlying_partial_update_pair_strat_http(pair_strat_json, return_obj_copy=False))

                            except Exception as e:
                                if "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
                                    logging.error(f"PairStrat found to have port set to {pair_strat.port} but executor "
                                                  f"server is down, recovering executor for "
                                                  f"{pair_strat.id=};;; {pair_strat=}")
                                    crashed_strats.append(pair_strat)
                                    await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                           underlying_update_pair_strat_to_non_running_state_query_http(pair_strat.id))
                                elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
                                      "it from responding to requests" in str(e) and "status_code: 503" in str(e)):
                                    pid = get_pid_from_port(pair_strat.port)
                                    if pid is not None:
                                        os.kill(pid, signal.SIGKILL)
                                    crashed_strats.append(pair_strat)
                                    await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                           underlying_update_pair_strat_to_non_running_state_query_http(pair_strat.id))
                                else:
                                    logging.exception("Something went wrong while checking is_service_up of executor "
                                                      f"with port: {pair_strat.port} in pair_strat strat_up recovery "
                                                      f"check - force kill this executor if is running, "
                                                      f"exception: {e};;; {pair_strat=}")
                            else:
                                # If executor server is still up and is in healthy state - Finding and adding
                                # process_id to pair_strat_id_to_executor_process_dicts
                                pid = get_pid_from_port(pair_strat.port)
                                self.pair_strat_id_to_executor_process_id_dict[pair_strat.id] = pid
                        else:
                            crashed_strats.append(pair_strat)
                    # else not required: avoiding if pair_strat is not in loaded_strats

                # Restart crashed executors
                if crashed_strats:
                    await self._async_start_executor_server_by_task_submit(crashed_strats, is_crash_recovery=True)
            else:
                err_str_ = "Unexpected: Found more than 1 strat_collection objects - Ignoring any executor recovery"
                logging.error(err_str_)
        else:
            err_str_ = "No strat_collection model exists yet - no executor to recover"
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

    async def update_portfolio_status_by_chore_or_fill_data_query_pre(
            self, portfolio_status_class_type: Type[PortfolioStatus], overall_buy_notional: float | None = None,
            overall_sell_notional: float | None = None, overall_buy_fill_notional: float | None = None,
            overall_sell_fill_notional: float | None = None, open_chore_count: int | None = None):
        async with PortfolioStatus.reentrant_lock:
            portfolio_status: PortfolioStatus = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_status_by_id_http(
                    1))

            if overall_buy_notional is not None:
                if portfolio_status.overall_buy_notional is None:
                    portfolio_status.overall_buy_notional = 0
                portfolio_status.overall_buy_notional += overall_buy_notional
            if overall_sell_notional is not None:
                if portfolio_status.overall_sell_notional is None:
                    portfolio_status.overall_sell_notional = 0
                portfolio_status.overall_sell_notional += overall_sell_notional
            if overall_buy_fill_notional is not None:
                if portfolio_status.overall_buy_fill_notional is None:
                    portfolio_status.overall_buy_fill_notional = 0
                portfolio_status.overall_buy_fill_notional += overall_buy_fill_notional
            if overall_sell_fill_notional is not None:
                if portfolio_status.overall_sell_fill_notional is None:
                    portfolio_status.overall_sell_fill_notional = 0
                portfolio_status.overall_sell_fill_notional += overall_sell_fill_notional
            if open_chore_count is not None:
                portfolio_status.open_chores = open_chore_count

            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_portfolio_status_http(
                portfolio_status, return_obj_copy=False)

        return []

    # Code-generated
    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        return await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http(
            get_ongoing_pair_strat_filter(security_id), self.get_generic_read_route())

    def _set_derived_side(self, pair_strat_obj: PairStrat):
        raise_error = False
        if pair_strat_obj.pair_strat_params.strat_leg2.side is None or \
                pair_strat_obj.pair_strat_params.strat_leg2.side == Side.SIDE_UNSPECIFIED:
            if pair_strat_obj.pair_strat_params.strat_leg1.side == Side.BUY:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.SELL
            elif pair_strat_obj.pair_strat_params.strat_leg1.side == Side.SELL:
                pair_strat_obj.pair_strat_params.strat_leg2.side = Side.BUY
            else:
                raise_error = True
        elif pair_strat_obj.pair_strat_params.strat_leg1.side is None:
            raise_error = True
        # else not required, all good
        if raise_error:
            # handles pair_strat_obj.pair_strat_params.strat_leg1.side == None and all other unsupported values
            raise Exception(f"error: _set_derived_side called with unsupported side combo on legs, leg1: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg1.side} leg2: "
                            f"{pair_strat_obj.pair_strat_params.strat_leg2.side} in pair strat: {pair_strat_obj}")

    def _set_derived_exchange(self, pair_strat_obj: PairStrat):
        unsupported_sec_id_source: bool = False
        strat_leg1: StratLeg = pair_strat_obj.pair_strat_params.strat_leg1
        strat_leg2: StratLeg = pair_strat_obj.pair_strat_params.strat_leg2
        if strat_leg1.sec.sec_id_source == SecurityIdSource.TICKER:
            strat_leg1.exch_id = self.static_data.get_exchange_from_ticker(strat_leg1.sec.sec_id)
        else:
            unsupported_sec_id_source = True
        if strat_leg2.sec.sec_id_source == SecurityIdSource.TICKER:
            strat_leg2.exch_id = self.static_data.get_exchange_from_ticker(strat_leg2.sec.sec_id)
        else:
            unsupported_sec_id_source = True
        if unsupported_sec_id_source:
            raise Exception(f"error: _set_derived_exchange called with unsupported sec_id_source param, supported: "
                            f"SecurityIdSource.TICKER, {strat_leg1.sec.sec_id_source=}, {strat_leg2.sec.sec_id_source=}"
                            f";;;{pair_strat_obj=}")

    async def get_dismiss_filter_portfolio_limit_brokers_query_pre(
            self, dismiss_filter_portfolio_limit_broker_class_type: Type[DismissFilterPortfolioLimitBroker],
            security_id1: str, security_id2: str):
        ric1, ric2 = self.static_data.get_connect_n_qfii_rics_from_ticker(security_id1)
        ric3, ric4 = self.static_data.get_connect_n_qfii_rics_from_ticker(security_id2)
        sedol = self.static_data.get_sedol_from_ticker(security_id1)
        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("security.sec_id", ric1, ric2, ric3, ric4, sedol)]}
        filtered_portfolio_limits: List[PortfolioLimits] = \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_limits_http(
                dismiss_filter_agg_pipeline, self.get_generic_read_route())
        if len(filtered_portfolio_limits) == 1:
            if filtered_portfolio_limits[0].eligible_brokers is not None:
                eligible_brokers = [eligible_broker for eligible_broker in
                                    filtered_portfolio_limits[0].eligible_brokers if
                                    eligible_broker.sec_positions]
                return_obj = DismissFilterPortfolioLimitBroker(brokers=eligible_brokers)
                return [return_obj]
        elif len(filtered_portfolio_limits) > 1:
            err_str_ = f"filtered_portfolio_limits expected: 1, found: " \
                       f"{str(len(filtered_portfolio_limits))}, for filter: " \
                       f"{dismiss_filter_agg_pipeline}, filtered_portfolio_limits: " \
                       f"{filtered_portfolio_limits}; use SWAGGER UI to check / fix and re-try "
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)
        else:
            err_str_ = (f"No filtered_portfolio_limits found for symbols of leg1 and leg2: {security_id1} and "
                        f"{security_id2}")
            logging.warning(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)

    def create_strat_view_for_strat(self, pair_strat: PairStrat):
        new_strat_view = get_new_strat_view_obj(pair_strat.id)
        photo_book_service_http_client.create_strat_view_client(new_strat_view)

    @except_n_log_alert()
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)};;; {pair_strat_obj=}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        if (pair_strat_obj.pair_strat_params.mstrat is None and
                pair_strat_obj.pair_strat_params.strat_type == StratType.Premium):
            pair_strat_obj.pair_strat_params.mstrat = "Mstrat_1"
        strat_leg1_sec_id: str = pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
        strat_leg2_sec_id: str | None = None
        # expectation: if strat leg2 is not provided, set it from static data
        if pair_strat_obj.pair_strat_params.strat_leg2 is None:
            strat_leg2_sec_id = self.static_data.get_underlying_eqt_ticker_from_cb_ticker(strat_leg1_sec_id)
            if strat_leg2_sec_id is None:
                raise Exception(f"error: underlying eqt ticker not found for cb_ticker: {strat_leg1_sec_id};;;"
                                f"{pair_strat_obj=}")
            strat_leg2_sec: Security = Security(sec_id=strat_leg2_sec_id, sec_id_source=SecurityIdSource.TICKER,
                                                inst_type=InstrumentType.EQT)
            pair_strat_obj.pair_strat_params.strat_leg2 = StratLeg(sec=strat_leg2_sec)
        else:
            strat_leg2_sec_id = pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id

        if (pair_strat_obj.pair_strat_params.strat_leg1.sec.inst_type is None or
                pair_strat_obj.pair_strat_params.strat_leg1.sec.inst_type == InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED):
            pair_strat_obj.pair_strat_params.strat_leg1.sec.inst_type = InstrumentType.CB
        if (pair_strat_obj.pair_strat_params.strat_leg2.sec.inst_type is None or
                pair_strat_obj.pair_strat_params.strat_leg2.sec.inst_type == InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED):
            pair_strat_obj.pair_strat_params.strat_leg2.sec.inst_type = InstrumentType.EQT

        self._set_derived_side(pair_strat_obj)
        self._set_derived_exchange(pair_strat_obj)
        pair_strat_obj.frequency = 1
        pair_strat_obj.pair_strat_params_update_seq_num = 0
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

        pair_strat_obj.host = street_book_config_yaml_dict.get("server_host")
        pair_strat_obj.is_executor_running = False
        pair_strat_obj.is_partially_running = False

        # creating strat_view object for this start
        self.create_strat_view_for_strat(pair_strat_obj)

        # @@@ Warning: Below handling of state collection is handled from ui also - see where can code be remove
        # to avoid duplicate
        async with StratCollection.reentrant_lock:
            strat_collection_obj: StratCollection = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.
                underlying_read_strat_collection_by_id_http(1))
            strat_key = get_strat_key_from_pair_strat(pair_strat_obj)
            strat_collection_obj.loaded_strat_keys.append(strat_key)
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                strat_collection_obj, return_obj_copy=False)

        # starting executor server for current pair strat
        await self._start_executor_server(pair_strat_obj)
        # if fail - log error is fine - strat not active
        self._apply_fallback_route_check(pair_strat_obj, raise_exception=False, update_fallback_route=True)
        self._apply_restricted_security_check(strat_leg1_sec_id, pair_strat_obj.pair_strat_params.strat_leg1.side,
                                              raise_exception=False)
        self._apply_restricted_security_check(strat_leg2_sec_id, pair_strat_obj.pair_strat_params.strat_leg2.side,
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

    def _create_fallback_routes(self, strat_collection_obj: StratCollection):
        pass

    def _apply_fallback_route_check(self, pair_strat: PairStrat, raise_exception: bool,
                                    update_fallback_route: bool = False):
        if pair_strat.pair_strat_params.strat_leg2.fallback_route != BrokerRoute.BR_CONNECT:
            return  # for now the check only applies if strat_leg2 fallback_route is BrokerRoute.BR_CONNECT
        sec_id: str = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        side: Side = pair_strat.pair_strat_params.strat_leg2.side
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
                pair_strat.pair_strat_params.strat_leg2.fallback_route = BrokerRoute.BR_QFII
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
    def are_similar_strats(strat1: PairStrat, strat2: PairStrat):
        strat1_leg1: StratLeg = strat1.pair_strat_params.strat_leg1
        strat1_leg2: StratLeg = strat1.pair_strat_params.strat_leg2
        strat2_leg1: StratLeg = strat2.pair_strat_params.strat_leg1
        strat2_leg2: StratLeg = strat2.pair_strat_params.strat_leg2

        if (strat1_leg1.sec.sec_id == strat2_leg1.sec.sec_id and strat1_leg1.side == strat2_leg1.side and
                strat1_leg2.sec.sec_id == strat2_leg2.sec.sec_id and strat1_leg2.side == strat2_leg2.side and
                strat1.id != strat2.id):
            return True
        return False

    async def _apply_activate_checks_n_log_error(self, pair_strat: PairStrat):
        """
        implement any strat management checks here (create / update strats)
        """
        leg1_side: Side
        leg2_side: Side
        leg1_symbol, leg1_side = (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                                  pair_strat.pair_strat_params.strat_leg1.side)
        leg2_symbol, leg2_side = (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                                  pair_strat.pair_strat_params.strat_leg2.side)
        self._apply_restricted_security_check(leg1_symbol, leg1_side)
        self._apply_restricted_security_check(leg2_symbol, leg2_side)

        ongoing_pair_strats: List[PairStrat] | None = await (
            get_matching_strat_from_symbol_n_side(leg1_symbol, leg1_side, no_ongoing_ok=True))
        # First Checking if any ongoing strat exists with same symbol_side pairs in same legs of param pair_strat,
        # that means if one strat is ongoing with s1-sd1 and s2-sd2 symbol-side pair legs then param pair_strat
        # must not have same symbol-side pair legs else HTTP exception is raised

        if ongoing_pair_strats:
            if len(ongoing_pair_strats) == 1:
                ongoing_pair_strat = ongoing_pair_strats[0]
                # raising exception only if ongoing pair_strat's leg1's symbol-side are same as
                # param pair_strat's leg1's symbol-side and same for leg2
                if self.are_similar_strats(ongoing_pair_strat, pair_strat):
                    err_str_ = (f"Ongoing strat already exists with same symbol-side pair legs - can't activate this "
                                f"strat till other strat is ongoing;;; {ongoing_pair_strat=}")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)
                # else not required, this is opposite side strat, let continue for further activation checks
            elif len(ongoing_pair_strats) == 2:
                ongoing_pair_strat1, ongoing_pair_strat2 = ongoing_pair_strats
                if not (self.are_similar_strats(ongoing_pair_strat1, pair_strat) or
                        self.are_similar_strats(ongoing_pair_strat2, pair_strat)):
                    err_str_ = (f"can't activate this strat, none of {len(ongoing_pair_strats)} more ongoing strats "
                                f"are similar;;;{ongoing_pair_strats=}")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)
                # else all good - let the activation through
            else:
                err_str_ = (f"can't activate this strat, {len(ongoing_pair_strats)} more ongoing strats found;;;"
                            f"{ongoing_pair_strats=}")
                logging.error(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
        # else not required, no ongoing pair strat - let the strat activation check pass

        # Checking if any strat exists with opp symbol and side of param pair_strat that activated today,
        # for instance if s1-sd1 and s2-sd2 are symbol-side pairs in param pair_strat's legs then checking there must
        # not be any strat activated today with s1-sd2 and s2-sd1 symbol-side pair legs, if it is found then this
        # strat can't be activated unless strat symbols are all opposite side tradable
        first_matched_strat_lock_file_path_list: List[str] = []
        if not self.static_data.is_opposite_side_tradable(leg1_symbol):
            first_matched_strat_lock_file_path_list = (
                glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                          f"{leg1_symbol}_{leg2_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        second_matched_strat_lock_file_path_list: List[str] = []
        if not self.static_data.is_opposite_side_tradable(leg2_symbol):
            second_matched_strat_lock_file_path_list = (
                glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                              f"{leg2_symbol}_{leg1_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        # checking both legs - If first_matched_strat_lock_file_path_list and second_matched_strat_lock_file_path_list
        # have file names having same pair_strat_id with today's date along with required symbol-side pair
        for matched_strat_file_path in first_matched_strat_lock_file_path_list:
            suffix_pattern = matched_strat_file_path[(matched_strat_file_path.index(leg2_side) + len(leg2_side)):]
            for sec_matched_strat_lock_file_path in second_matched_strat_lock_file_path_list:
                if sec_matched_strat_lock_file_path.endswith(suffix_pattern):
                    err_str_ = ("Found strat activated today with symbols of this strat being used in opposite sides"
                                " - can't activate this strat today")
                    logging.error(err_str_)
                    raise HTTPException(status_code=400, detail=err_str_)

    def get_lock_file_names_from_pair_strat(self, pair_strat: PairStrat) -> Tuple[PurePath | None, PurePath | None]:
        leg1_sec_id: str = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        leg1_lock_file_path: str | None = None
        if not self.static_data.is_opposite_side_tradable(leg1_sec_id):
            leg1_lock_file_path = (CURRENT_PROJECT_DATA_DIR / f"{leg1_sec_id}_"
                                                              f"{pair_strat.pair_strat_params.strat_leg1.side.value}_"
                                                              f"{pair_strat.id}_{DateTime.date(DateTime.utcnow())}"
                                                              f".json.lock")

        leg2_sec_id: str = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        leg2_lock_file_path: str | None = None
        if not self.static_data.is_opposite_side_tradable(leg2_sec_id):
            leg2_lock_file_path = (CURRENT_PROJECT_DATA_DIR / f"{leg2_sec_id}_"
                                                              f"{pair_strat.pair_strat_params.strat_leg2.side.value}_"
                                                              f"{pair_strat.id}_{DateTime.date(DateTime.utcnow())}"
                                                              f".json.lock")
        return leg1_lock_file_path, leg2_lock_file_path

    async def _update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat,
                                     updated_pair_strat_obj: PairStrat) -> bool | None:
        """
        Return true if check passed false otherwise
        """
        check_passed = True
        if stored_pair_strat_obj.strat_state != StratState.StratState_ACTIVE and \
                updated_pair_strat_obj.strat_state == StratState.StratState_ACTIVE:
            await self._apply_activate_checks_n_log_error(stored_pair_strat_obj)  # raises HTTPException internally
            if stored_pair_strat_obj.strat_state == StratState.StratState_READY:
                leg1_lock_file_path, leg2_lock_file_path = (
                    self.get_lock_file_names_from_pair_strat(updated_pair_strat_obj))
                if leg1_lock_file_path:
                    with open(leg1_lock_file_path, "w") as fl:  # creating empty file
                        pass
                if leg2_lock_file_path:
                    with open(leg2_lock_file_path, "w") as fl:  # creating empty file
                        pass
            # else not required: create strat lock file only if moving the strat state from
            # StratState_READY to StratState_ACTIVE
        if updated_pair_strat_obj.strat_state == StratState.StratState_DONE:
            # warning and above log level is required
            logging.warning(f"ResetLogBookCache;;;pair_strat_log_key: "
                            f"{get_reset_log_book_cache_wrapper_pattern()}"
                            f"{get_pair_strat_log_key(updated_pair_strat_obj)}"
                            f"{get_reset_log_book_cache_wrapper_pattern()}")
        if updated_pair_strat_obj.strat_state != StratState.StratState_ACTIVE:
            # if fail - log error is fine - strat not active - check does not fail due to this
            self._apply_fallback_route_check(updated_pair_strat_obj, raise_exception=False)
        else:
            # updated_pair_strat_obj.strat_state is StratState.StratState_ACTIVE, if fail - raise exception
            self._apply_fallback_route_check(updated_pair_strat_obj, raise_exception=True)
        return check_passed

    def _update_port_to_executor_http_client_dict_from_updated_pair_strat(self, host: str, port: int):
        if port is not None and port not in self.port_to_executor_http_client_dict:
            self.port_to_executor_http_client_dict[port] = (
                StreetBookServiceHttpClient.set_or_get_if_instance_exists(host, port))

    def _set_strat_company(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat | Dict) -> None:
        is_executor_running: bool
        if isinstance(updated_pair_strat_obj, dict):
            is_executor_running = updated_pair_strat_obj.get("is_executor_running")
        else:
            is_executor_running = updated_pair_strat_obj.is_executor_running

        if is_executor_running:
            # update only if strat company is not set for either leg1 or leg2
            if stored_pair_strat_obj.pair_strat_params.strat_leg1.company is None or (
                    stored_pair_strat_obj.pair_strat_params.strat_leg2.company is None):
                sec_id: str = stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
                side: Side = stored_pair_strat_obj.pair_strat_params.strat_leg1.side
                if stored_pair_strat_obj.port is not None:
                    strat_web_client: StreetBookServiceHttpClient = (
                        StreetBookServiceHttpClient.set_or_get_if_instance_exists(stored_pair_strat_obj.host,
                                                                                     stored_pair_strat_obj.port))
                    symbol_overview_list: List[SymbolOverviewBaseModel] = (
                        strat_web_client.get_all_symbol_overview_client())
                    strat_leg1_company: str | None = None
                    strat_leg2_company: str | None = None
                    for symbol_overview in symbol_overview_list:
                        if symbol_overview.symbol == stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id:
                            strat_leg1_company = symbol_overview.company
                        elif symbol_overview.symbol == stored_pair_strat_obj.pair_strat_params.strat_leg2.sec.sec_id:
                            strat_leg2_company = symbol_overview.company
                    if isinstance(updated_pair_strat_obj, dict):
                        updated_pair_strat_obj["pair_strat_params"]["strat_leg1"]["company"] = strat_leg1_company
                        updated_pair_strat_obj["pair_strat_params"]["strat_leg2"]["company"] = strat_leg2_company
                    else:
                        updated_pair_strat_obj.pair_strat_params.strat_leg1.company = strat_leg1_company
                        updated_pair_strat_obj.pair_strat_params.strat_leg2.company = strat_leg2_company
                else:
                    err_str_ = (f"_set_strat_company failed. no port found for pair_strat with symbol_side_key: "
                                f"{get_symbol_side_key([(sec_id, side)])}")
                    logging.error(err_str_)
            # else not required - company already set
        # else not required - pair strat executor is not running yet

    async def update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(updated_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        self._set_strat_company(stored_pair_strat_obj, updated_pair_strat_obj)
        if updated_pair_strat_obj.frequency is None:
            updated_pair_strat_obj.frequency = 0
        updated_pair_strat_obj.frequency += 1

        if updated_pair_strat_obj.pair_strat_params_update_seq_num is None:
            updated_pair_strat_obj.pair_strat_params_update_seq_num = 0
        updated_pair_strat_obj.pair_strat_params_update_seq_num += 1
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()

        res = await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        if not res:
            sec_id: str = stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
            side: Side = stored_pair_strat_obj.pair_strat_params.strat_leg1.side
            logging.debug(f"Alerts updated by _update_pair_strat_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(sec_id, side)])};;;{updated_pair_strat_obj=}")

        # updating port_to_executor_http_client_dict with this port if not present
        self._update_port_to_executor_http_client_dict_from_updated_pair_strat(updated_pair_strat_obj.host,
                                                                               updated_pair_strat_obj.port)

        return updated_pair_strat_obj

    async def _partial_update_pair_strat(self, stored_pair_strat_obj_dict: Dict, updated_pair_strat_obj_dict: Dict):
        stored_pair_strat_obj = PairStrat.from_dict(stored_pair_strat_obj_dict)

        self._set_strat_company(stored_pair_strat_obj, updated_pair_strat_obj_dict)
        updated_pair_strat_obj_dict["frequency"] = stored_pair_strat_obj.frequency + 1

        if updated_pair_strat_obj_dict.get("pair_strat_params") is not None:
            if stored_pair_strat_obj.pair_strat_params_update_seq_num is None:
                stored_pair_strat_obj.pair_strat_params_update_seq_num = 0
            updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = \
                stored_pair_strat_obj.pair_strat_params_update_seq_num + 1

        updated_pair_strat_obj_dict["last_active_date_time"] = DateTime.utcnow()

        updated_strat_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_pair_strat_obj.to_dict()),
                                                      updated_pair_strat_obj_dict)
        updated_pair_strat_obj = PairStrat.from_dict(updated_strat_obj_dict)
        res = await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        if not res:
            sec_id: str = stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id
            side: Side = stored_pair_strat_obj.pair_strat_params.strat_leg1.side
            logging.debug(f"Alerts updated by _update_pair_strat_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(sec_id, side)])};;;{updated_pair_strat_obj=}")
        updated_pair_strat_obj_dict = updated_pair_strat_obj.to_dict()

        # updating port_to_executor_http_client_dict with this port if not present
        host = updated_pair_strat_obj_dict.get("host")
        port = updated_pair_strat_obj_dict.get("port")
        self._update_port_to_executor_http_client_dict_from_updated_pair_strat(host, port)
        return updated_pair_strat_obj_dict

    async def partial_update_pair_strat_pre(self, stored_pair_strat_obj_json: Dict[str, Any],
                                            updated_pair_strat_obj_json: Dict[str, Any]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "partial_update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat: {stored_pair_strat_obj_json}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        updated_pair_strat_obj_dict = \
            await self._partial_update_pair_strat(stored_pair_strat_obj_json, updated_pair_strat_obj_json)
        return updated_pair_strat_obj_dict

    async def partial_update_all_pair_strat_pre(self, stored_pair_strat_dict_list: List[Dict[str, Any]],
                                                updated_pair_strat_dict_list: List[Dict[str, Any]]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "partial_update_pair_strat_pre not ready - service is not initialized yet, "
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        tasks: List = []
        for idx, updated_pair_strat_obj_json in enumerate(updated_pair_strat_dict_list):
            task = asyncio.create_task(self._partial_update_pair_strat(stored_pair_strat_dict_list[idx],
                                                                       updated_pair_strat_obj_json),
                                       name=str(f"{stored_pair_strat_dict_list[idx].get('_id')}"))
            tasks.append(task)
        updated_pair_strat_obj_json_list = await submit_task_with_first_completed_wait(tasks)
        return updated_pair_strat_obj_json_list

    def check_n_disable_non_mstrat_positions(self, stored_pair_strat_obj_or_dict: Dict | PairStrat,
                                             updated_pair_strat_obj_or_dict: Dict | PairStrat):
        pass

    def _update_pair_strat_post(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if stored_pair_strat_obj.strat_state != updated_pair_strat_obj.strat_state:
            logging.warning(f"Strat state changed from {stored_pair_strat_obj.strat_state.value} to "
                            f"{updated_pair_strat_obj.strat_state.value};;;pair_strat_log_key: "
                            f"{get_pair_strat_log_key(updated_pair_strat_obj)}")
        self.check_n_disable_non_mstrat_positions(stored_pair_strat_obj, updated_pair_strat_obj)

    def _partial_update_pair_strat_post(self, stored_pair_strat_obj_dict: Dict, updated_pair_strat_obj_dict: Dict):
        stored_strat_state = stored_pair_strat_obj_dict.get("strat_state")
        updated_strat_state = updated_pair_strat_obj_dict.get("strat_state")
        if stored_strat_state != updated_strat_state:
            logging.warning(f"Strat state changed from {stored_strat_state} to "
                            f"{updated_strat_state};;;pair_strat_log_key: "
                            f"{get_pair_strat_dict_log_key(updated_pair_strat_obj_dict)}")
        self.check_n_disable_non_mstrat_positions(stored_pair_strat_obj_dict, updated_pair_strat_obj_dict)

    async def update_pair_strat_post(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        self._update_pair_strat_post(stored_pair_strat_obj, updated_pair_strat_obj)

    async def partial_update_pair_strat_post(self, stored_pair_strat_obj_dict: Dict,
                                             updated_pair_strat_obj_dict: Dict):
        self._partial_update_pair_strat_post(stored_pair_strat_obj_dict, updated_pair_strat_obj_dict)

    async def partial_update_all_pair_strat_post(self, stored_pair_strat_obj_dict_list: List[Dict],
                                                 updated_pair_strat_obj_dict_list: List[Dict]):
        stored_pair_strat_obj_dict: Dict
        for idx, stored_pair_strat_obj_dict in enumerate(stored_pair_strat_obj_dict_list):
            updated_pair_strat_obj_dict: Dict[str, Any] = updated_pair_strat_obj_dict_list[idx]
            self._partial_update_pair_strat_post(stored_pair_strat_obj_dict, updated_pair_strat_obj_dict)

    async def pause_all_active_strats_query_pre(self, pair_strat_class_type: Type[PairStrat]):
        async with PairStrat.reentrant_lock:
            pair_strat_list: List[Dict] = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http_json_dict())

            updated_pair_strats_list: List[Dict] = []
            for pair_strat_ in pair_strat_list:

                # Putting strat to pause if strat is active
                strat_state = pair_strat_.get("strat_state")
                _id = pair_strat_.get("_id")
                if strat_state == StratState.StratState_ACTIVE:
                    update_pair_strat = {"_id": _id, "strat_state": StratState.StratState_PAUSED}
                    updated_pair_strats_list.append(update_pair_strat)

            if updated_pair_strats_list:
                logging.warning("Pausing all strats")
                (await EmailBookServiceRoutesCallbackBaseNativeOverride.
                 underlying_partial_update_all_pair_strat_http(updated_pair_strats_list, return_obj_copy=False))
        return []

    async def update_pair_strat_to_non_running_state_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                               pair_strat_id: int):
        pair_strat_json = {
            "_id": pair_strat_id,
            "is_partially_running": False,
            "is_executor_running": False,
            "port": None,
            "top_of_book_port": None,
            "market_depth_port": None,
            "last_barter_port": None
        }

        update_pair_strat = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_partial_update_pair_strat_http(pair_strat_json))
        return [update_pair_strat]

    async def _start_executor_server(self, pair_strat: PairStrat, is_crash_recovery: bool | None = None) -> None:
        code_gen_projects_dir = PurePath(__file__).parent.parent.parent
        # executor_path = code_gen_projects_dir / "street_book" / "scripts" / 'launch_beanie_fastapi.py'
        executor_path = code_gen_projects_dir / "street_book" / "scripts" / 'launch_msgspec_fastapi.py'
        if is_crash_recovery:
            # 1 is sent to indicate it is recovery restart
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_strat.id}', "1", '&'])
        else:
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_strat.id}', '&'])

        logging.info(f"Launched strat executor for {pair_strat.id=};;;{executor_path=}")
        self.pair_strat_id_to_executor_process_id_dict[pair_strat.id] = executor.pid

    def _close_executor_server(self, pair_strat_id: int) -> None:
        process_id = self.pair_strat_id_to_executor_process_id_dict.get(pair_strat_id)
        # process.terminate()
        os.kill(process_id, signal.SIGINT)

        del self.pair_strat_id_to_executor_process_id_dict[pair_strat_id]

    async def get_ongoing_strats_symbol_n_exch_query_pre(self,
                                                         ongoing_strat_symbols_class_type: Type[
                                                             OngoingStratsSymbolNExchange]):

        pair_strat_list: List[PairStrat] = \
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http(
                get_ongoing_pair_strat_filter(), self.get_generic_read_route())
        ongoing_symbol_n_exch_set: Set[str] = set()
        ongoing_strat_symbols_n_exchange = OngoingStratsSymbolNExchange(symbol_n_exchange=[])

        before_len: int = 0
        for pair_strat in pair_strat_list:
            leg1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            leg1_exch = pair_strat.pair_strat_params.strat_leg1.exch_id
            leg2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            leg2_exch = pair_strat.pair_strat_params.strat_leg2.exch_id
            leg1_symbol_n_exch = SymbolNExchange.from_kwargs(symbol=leg1_symbol, exchange=leg1_exch)
            leg2_symbol_n_exch = SymbolNExchange.from_kwargs(symbol=leg2_symbol, exchange=leg2_exch)

            ongoing_symbol_n_exch_set.add(f"{leg1_symbol}_{leg1_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg1_symbol_n_exch)
                before_len += 1

            ongoing_symbol_n_exch_set.add(f"{leg2_symbol}_{leg2_exch}")
            if len(ongoing_symbol_n_exch_set) == before_len + 1:
                ongoing_strat_symbols_n_exchange.symbol_n_exchange.append(leg2_symbol_n_exch)
                before_len += 1
        return [ongoing_strat_symbols_n_exchange]

    def _drop_executor_db_for_deleting_pair_strat(self, mongo_server_uri: str, pair_strat_id: int,
                                                  sec_id: str, side: Side):
        mongo_client = MongoClient(mongo_server_uri)
        db_name: str = f"street_book_{pair_strat_id}"

        if db_name in mongo_client.list_database_names():
            mongo_client.drop_database(db_name)
        else:
            err_str_ = (f"Unexpected: {db_name=} not found in mongo_client for uri: "
                        f"{mongo_server_uri} being used by current strat, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)

    async def delete_pair_strat_pre(self, pair_strat_id: int):
        pair_strat_to_be_deleted = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_read_pair_strat_by_id_http(pair_strat_id))

        port: int = pair_strat_to_be_deleted.port
        sec_id = pair_strat_to_be_deleted.pair_strat_params.strat_leg1.sec.sec_id
        side = pair_strat_to_be_deleted.pair_strat_params.strat_leg1.side

        strat_key = get_strat_key_from_pair_strat(pair_strat_to_be_deleted)
        strat_collection_dict: Dict = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                        underlying_read_strat_collection_by_id_http_json_dict(1))

        loaded_strat_keys = strat_collection_dict.get("loaded_strat_keys")
        buffered_strat_keys = strat_collection_dict.get("buffered_strat_keys")

        if loaded_strat_keys is not None and strat_key in loaded_strat_keys:
            if pair_strat_to_be_deleted.port is not None:
                strat_web_client: StreetBookServiceHttpClient = (
                    StreetBookServiceHttpClient.set_or_get_if_instance_exists(pair_strat_to_be_deleted.host,
                                                                                 pair_strat_to_be_deleted.port))
            else:
                err_str_ = f"pair_strat object has no port;;; {pair_strat_to_be_deleted=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=500)

            if strat_web_client is None:
                err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                            f"{port=}, ignoring this strat delete, likely bug in server cache dict handling, "
                            f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])};;; "
                            f"{pair_strat_to_be_deleted=}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            if is_ongoing_strat(pair_strat_to_be_deleted):
                err_str_ = ("This strat is ongoing: Deletion of ongoing strat is not supported, "
                            "ignoring this strat delete, try again once it is"
                            f"not ongoing, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # removing and updating relative models
            try:
                strat_web_client.put_strat_to_snooze_query_client()
            except Exception as e:
                err_str_ = ("Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                            f"delete of this strat, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}, "
                            f"exception: {e}, ;;; {pair_strat_to_be_deleted=}")
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
            self._close_executor_server(pair_strat_to_be_deleted.id)  # closing executor

            # Dropping database for this strat
            code_gen_projects_dir = PurePath(__file__).parent.parent.parent
            executor_config_file_path = (code_gen_projects_dir / "street_book" /
                                         "data" / f"config.yaml")
            if os.path.exists(executor_config_file_path):
                server_config_yaml_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(str(executor_config_file_path)))
                mongo_server_uri = server_config_yaml_dict.get("mongo_server")
                if mongo_server_uri is not None:
                    self._drop_executor_db_for_deleting_pair_strat(mongo_server_uri, pair_strat_to_be_deleted.id,
                                                                   sec_id, side)
                else:
                    err_str_ = (f"key 'mongo_server' missing in street_book/data/config.yaml, ignoring this"
                                f"strat delete, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                    logging.error(err_str_)
                    raise HTTPException(detail=err_str_, status_code=400)
            else:
                err_str_ = (f"Config file for {port=} missing, must exists since executor is running from this"
                            f"config, ignoring this strat delete, symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)

            # Removing strat_key from loaded strat keys
            async with StratCollection.reentrant_lock:
                strat_key = get_strat_key_from_pair_strat(pair_strat_to_be_deleted)
                obj_id = 1
                strat_collection: StratCollection = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_strat_collection_by_id_http(obj_id))

                loaded_strat_keys = strat_collection.loaded_strat_keys
                if loaded_strat_keys is not None:
                    try:
                        loaded_strat_keys.remove(strat_key)
                    except ValueError as val_err:
                        if "x not in list" in str(val_err):
                            logging.error(f"Unexpected: Can't find {strat_key=} in strat_collection's loaded"
                                          f"keys while deleting strat;;; {strat_collection=}")
                        else:
                            logging.error(f"Something unexpected happened while removing {strat_key=} from "
                                          f"loaded strat_keys in strat_collection - ignoring this strat_key removal;;; "
                                          f"{strat_collection=}")
                        return
                else:
                    logging.error(f"Unexpected: Can't find {strat_key=} in strat_collection's loaded"
                                  f"keys while deleting strat - loaded_strat_keys found None;;; {strat_collection}")
                    return

                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                    strat_collection, return_obj_copy=False)

            # Removing StratView for this strat
            photo_book_service_http_client.delete_strat_view_client(pair_strat_to_be_deleted.id)

            logging.warning(f"ResetLogBookCache;;;pair_strat_log_key: "
                            f"{get_reset_log_book_cache_wrapper_pattern()}"
                            f"{get_pair_strat_log_key(pair_strat_to_be_deleted)}"
                            f"{get_reset_log_book_cache_wrapper_pattern()}")
        elif buffered_strat_keys is not None and strat_key in buffered_strat_keys:
            # Removing strat_key from buffered strat keys
            async with StratCollection.reentrant_lock:
                strat_key = get_strat_key_from_pair_strat(pair_strat_to_be_deleted)
                obj_id = 1
                strat_collection: StratCollection = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_strat_collection_by_id_http(obj_id))

                try:
                    strat_collection.buffered_strat_keys.remove(strat_key)
                except ValueError as val_err:
                    if "x not in list" in str(val_err):
                        logging.error(f"Unexpected: Can't find {strat_key=} in strat_collection's buffered"
                                      f"keys while deleting strat;;; {strat_collection=}")
                    else:
                        logging.error(f"Something unexpected happened while removing {strat_key=} from "
                                      f"loaded strat_keys in strat_collection - ignoring this strat_key removal;;; "
                                      f"{strat_collection=}")
                    return

                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                    strat_collection, return_obj_copy=False)

            # Removing StratView for this strat
            photo_book_service_http_client.delete_strat_view_client(pair_strat_to_be_deleted)

            # removing log key cache value form pair_strat_id_key cache
            pair_strat_id_key.pop(pair_strat_to_be_deleted.id, None)

        else:
            err_str_ = ("Unexpected: Strat is not found in loaded or buffer list, ignoring this strat delete, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

    async def unload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        updated_strat_collection_loaded_strat_keys_frozenset = frozenset(updated_strat_collection_obj.loaded_strat_keys)
        stored_strat_collection_loaded_strat_keys_frozenset = frozenset(stored_strat_collection_obj.loaded_strat_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_strat_keys_frozenset = stored_strat_collection_loaded_strat_keys_frozenset.difference(
            updated_strat_collection_loaded_strat_keys_frozenset)
        if len(unloaded_strat_keys_frozenset) != 0:
            unloaded_strat_key: str
            for unloaded_strat_key in unloaded_strat_keys_frozenset:
                if unloaded_strat_key in updated_strat_collection_obj.buffered_strat_keys:  # unloaded not deleted
                    pair_strat_id: int = get_id_from_strat_key(unloaded_strat_key)
                    pair_strat = \
                        await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_read_pair_strat_by_id_http(pair_strat_id))
                    if pair_strat.port is not None:
                        street_book_web_client: StreetBookServiceHttpClient = (
                            self.port_to_executor_http_client_dict.get(pair_strat.port))
                    else:
                        err_str_ = (f"pair_strat object has no port while unloading - "
                                    f"ignoring this strat unload;;; {pair_strat=}")
                        logging.error(err_str_)
                        raise HTTPException(detail=err_str_, status_code=400)

                    if street_book_web_client is None:
                        err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                                    f"{pair_strat.port=}, ignoring this strat unload,"
                                    f"likely bug in server cache dict handling;;; {pair_strat=}")
                        logging.error(err_str_)
                        raise HTTPException(status_code=400, detail=err_str_)

                    if is_ongoing_strat(pair_strat):
                        error_str = f"unloading an ongoing pair strat key: {unloaded_strat_key} is not supported, " \
                                    f"current {pair_strat.strat_state=}, " \
                                    f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; {pair_strat=}"
                        logging.error(error_str)
                        raise HTTPException(status_code=400, detail=error_str)
                    elif pair_strat.strat_state in [StratState.StratState_DONE, StratState.StratState_READY,
                                                    StratState.StratState_SNOOZED]:
                        # removing and updating relative models
                        try:
                            street_book_web_client.put_strat_to_snooze_query_client()
                            logging.info(f"Strat set to Snooze state, {unloaded_strat_key=};;; {pair_strat=}")
                        except Exception as e:
                            err_str_ = (
                                "Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                                f"unload of this strat, pair_strat_key: {get_pair_strat_log_key(pair_strat)}, ;;;"
                                f"{pair_strat=}")
                            logging.error(err_str_)
                            raise HTTPException(status_code=500, detail=err_str_)
                        self._close_executor_server(pair_strat.id)    # closing executor
                    else:
                        err_str_ = (f"Unloading strat with strat_state: {pair_strat.strat_state} is not supported,"
                                    f"try unloading when start is READY or DONE, pair_strat_key: "
                                    f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat=}")
                        logging.error(err_str_)
                        raise Exception(err_str_)

                    pair_strat_json = {
                        "_id": pair_strat_id,
                        "strat_state": StratState.StratState_SNOOZED
                    }
                    pair_strat_obj = (
                        await EmailBookServiceRoutesCallbackBaseNativeOverride.
                        underlying_partial_update_pair_strat_http(pair_strat_json))

                    logging.warning(f"ResetLogBookCache;;;pair_strat_log_key: "
                                    f"{get_reset_log_book_cache_wrapper_pattern()}"
                                    f"{get_pair_strat_log_key(pair_strat_obj)}"
                                    f"{get_reset_log_book_cache_wrapper_pattern()}")
                    # clear strat view cache data for pair strat on unload
                    log_str = pair_strat_client_call_log_str(
                        StratViewBaseModel, photo_book_service_http_client.patch_all_strat_view_client,
                        UpdateType.SNAPSHOT_TYPE,
                        _id=pair_strat.id, average_premium=0, market_premium=0, strat_alert_count=0,
                        balance_notional=0, max_single_leg_notional=0,
                        total_fill_buy_notional=0, total_fill_sell_notional=0,
                        strat_alert_aggregated_severity=Severity.Severity_UNSPECIFIED.value)
                    logging.db(log_str)
                # else: deleted not unloaded - nothing to do , DB will remove entry

    async def reload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        updated_strat_collection_buffered_strat_keys_frozenset = frozenset(
            updated_strat_collection_obj.buffered_strat_keys)
        stored_strat_collection_buffered_strat_keys_frozenset = frozenset(
            stored_strat_collection_obj.buffered_strat_keys)
        # existing items in stored buffered frozenset but not in the updated stored frozen set need to
        # move to ready state
        reloaded_strat_keys_frozenset = stored_strat_collection_buffered_strat_keys_frozenset.difference(
            updated_strat_collection_buffered_strat_keys_frozenset)
        if len(reloaded_strat_keys_frozenset) != 0:
            logging.debug(f"found {len(reloaded_strat_keys_frozenset)} to load from buffered;;;"
                          f"{reloaded_strat_keys_frozenset=}")
            reloaded_strat_key: str
            for reloaded_strat_key in reloaded_strat_keys_frozenset:
                if reloaded_strat_key in updated_strat_collection_obj.loaded_strat_keys:  # loaded not deleted
                    pair_strat_id: int = get_id_from_strat_key(reloaded_strat_key)
                    pair_strat = \
                        await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_by_id_http(
                            pair_strat_id)

                    # unload_strat should be False if reached here (reload case)
                    log_str = pair_strat_client_call_log_str(
                        StratViewBaseModel, photo_book_service_http_client.patch_all_strat_view_client,
                        UpdateType.SNAPSHOT_TYPE, _id=pair_strat.id, unload_strat=False, recycle_strat=False)
                    logging.db(log_str)

                    # starting snoozed server
                    await self._start_executor_server(pair_strat)

                # else: deleted not loaded - nothing to do , DB will remove entry

    async def update_strat_collection_pre(self, updated_strat_collection_obj: StratCollection):
        stored_strat_collection_obj = \
            await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                   underlying_read_strat_collection_by_id_http(updated_strat_collection_obj.id))

        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_collection_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # handling unloading pair_strats
        await self.unload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        # handling reloading pair_strat
        await self.reload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        return updated_strat_collection_obj

    async def get_strat_collection(self) -> StratCollection:
        strat_collections = (
            await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_collection_http())

        if len(strat_collections) != 1:
            err_str_ = (f"Unexpected: multiple strat collection obj found, expected 1;;;"
                        f"{strat_collections=}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=400)

        strat_collection = strat_collections[0]
        return strat_collection

    async def unload_strat_from_strat_id_query_pre(
            self, strat_collection_class_type: Type[StratCollection], strat_id: int):
        async with StratCollection.reentrant_lock:

            pair_strat = await (
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_by_id_http(strat_id))
            strat_key = get_strat_key_from_pair_strat(pair_strat)

            strat_collection = await self.get_strat_collection()
            for loaded_strat_key in strat_collection.loaded_strat_keys:
                if loaded_strat_key == strat_key:
                    # strat found to unload
                    strat_collection.loaded_strat_keys.remove(strat_key)
                    strat_collection.buffered_strat_keys.insert(0, strat_key)
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                        strat_collection)
                    break
            else:
                err_str_ = f"No loaded strat found with {strat_id=} in strat_collection;;;{strat_collection=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    async def reload_strat_from_strat_id_query_pre(
            self, strat_collection_class_type: Type[StratCollection], strat_id: int):
        async with StratCollection.reentrant_lock:
            strat_collection = await self.get_strat_collection()
            pair_strat = await (
                EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_by_id_http(strat_id))
            strat_key = get_strat_key_from_pair_strat(pair_strat)

            for loaded_strat_key in strat_collection.buffered_strat_keys:
                if loaded_strat_key == strat_key:
                    # strat found to unload
                    strat_collection.buffered_strat_keys.remove(strat_key)
                    strat_collection.loaded_strat_keys.append(strat_key)
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                        strat_collection)
                    break
            else:
                err_str_ = f"No buffered strat found with {strat_id=} in strat_collection;;;{strat_collection=}"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)
        return []

    async def get_ongoing_or_single_exact_non_ongoing_pair_strat_from_symbol_side_query_pre(
            self, pair_strat_class_type: Type[PairStrat], sec_id: str, side: Side):
        """
        checks if ongoing strat is found with sec_id and side in any leg from all strats, else returns
        pair_strat if non-ongoing but single match is found with sec_id and side in any leg else returns None
        """
        read_pair_strat_filter = get_ongoing_or_all_pair_strats_by_sec_id(sec_id, side)
        pair_strats: List[Dict] = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                         underlying_read_pair_strat_http_json_dict(read_pair_strat_filter))
        if len(pair_strats) == 1:
            # if single match is found then either it is ongoing from multiple same matched strats or it is single
            # non-ongoing strat - both are accepted
            return pair_strats
        # else not required: returns None if found multiple matching symbol-side non-ongoing strats
        return []

    async def get_all_pair_strats_from_symbol_side_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                             sec_id: str, side: Side):
        return await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                      underlying_read_pair_strat_http(get_all_pair_strat_from_symbol_n_side(sec_id, side)))

    async def create_admin_control_pre(self, admin_control_obj: AdminControl):
        match admin_control_obj.command_type:
            case CommandType.CLEAR_STRAT:
                pair_strat_list: List[PairStrat] = (
                    await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http())
                for pair_strat_ in pair_strat_list:
                    leg1_lock_file_path, leg2_lock_file_path = (
                        self.get_lock_file_names_from_pair_strat(pair_strat_))
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

    async def create_portfolio_limits_pre(self, portfolio_limits_obj: PortfolioLimits):
        portfolio_limits_obj.eligible_brokers_update_count = 0

    async def update_portfolio_limits_pre(self, updated_portfolio_limits_obj: PortfolioLimits):
        if updated_portfolio_limits_obj.eligible_brokers:
            stored_portfolio_limits_obj = (
                await EmailBookServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_limits_by_id_http(
                    updated_portfolio_limits_obj.id))
            updated_portfolio_limits_obj.eligible_brokers_update_count = (
                    stored_portfolio_limits_obj.eligible_brokers_update_count + 1)
        return updated_portfolio_limits_obj

    async def partial_update_portfolio_limits_pre(self, stored_portfolio_limits_obj_json: Dict[str, Any],
                                                  updated_portfolio_limits_obj_json: Dict[str, Any]):
        if updated_portfolio_limits_obj_json.get("eligible_brokers") is not None:
            stored_eligible_brokers_update_count = stored_portfolio_limits_obj_json.get("eligible_brokers_update_count")
            if stored_eligible_brokers_update_count is None:
                stored_eligible_brokers_update_count = 0
            updated_portfolio_limits_obj_json["eligible_brokers_update_count"] = (
                    stored_eligible_brokers_update_count + 1)
        return updated_portfolio_limits_obj_json

    async def filtered_notify_pair_strat_update_query_ws_pre(self):
        return filter_ws_pair_strat

    async def _update_system_control_post(
            self, stored_system_control_json: Dict | SystemControl,
            updated_system_control_json_or_obj: Dict | SystemControl):
        if isinstance(stored_system_control_json, dict):
            stored_pause_all_strats = stored_system_control_json.get("pause_all_strats")
            stored_load_buffer_strats = stored_system_control_json.get("load_buffer_strats")
            stored_cxl_baskets = stored_system_control_json.get("cxl_baskets")
        else:
            stored_pause_all_strats = stored_system_control_json.pause_all_strats
            stored_load_buffer_strats = stored_system_control_json.load_buffer_strats
            stored_cxl_baskets = stored_system_control_json.cxl_baskets

        if isinstance(updated_system_control_json_or_obj, dict):
            updated_pause_all_strats = updated_system_control_json_or_obj.get("pause_all_strats")
            updated_load_buffer_strats = updated_system_control_json_or_obj.get("load_buffer_strats")
            updated_cxl_baskets = updated_system_control_json_or_obj.get("cxl_baskets")
        else:
            updated_pause_all_strats = updated_system_control_json_or_obj.pause_all_strats
            updated_load_buffer_strats = updated_system_control_json_or_obj.load_buffer_strats
            updated_cxl_baskets = updated_system_control_json_or_obj.cxl_baskets
        if not stored_pause_all_strats and updated_pause_all_strats:
            script_path: str = str(CURRENT_PROJECT_DIR / "pyscripts" / "pause_all_active_strats.py")
            cmd: List[str] = ["python", script_path, "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered pause_all_strat event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")
        if not stored_load_buffer_strats and updated_load_buffer_strats:
            script_path: str = str(CURRENT_PROJECT_DIR / "pyscripts" / "load_all_buffer_strats.py")
            cmd: List[str] = ["python", script_path, "&"]
            launcher: subprocess.Popen = subprocess.Popen(cmd)
            logging.warning(f"Triggered load_buffer_strats event at {DateTime.utcnow()};;;{cmd=}, {launcher=}")
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
        self.bartering_link.reload_portfolio_configs()
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

    async def register_pair_strat_for_recovery_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                         pair_strat_id: int):
        if not pair_strat_id:
            err_str_ = f"register_pair_strat_for_recovery failed, {pair_strat_id=} found None, expected int"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)
        # else not received - received pair_strat_id

        if self.pair_strat_id_to_executor_process_id_dict.get(pair_strat_id) is not None:
            err_str_ = f"register_pair_strat_for_recovery failed, {pair_strat_id=} already registered for recovery"
            logging.error(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)

        # check for valid pair_strat_id and register if present in loaded list
        try:
            pair_strat_obj: PairStrat = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                               underlying_read_pair_strat_by_id_http(pair_strat_id))
            strat_key: str = get_strat_key_from_pair_strat(pair_strat_obj)
            strat_collection_obj: StratCollection = await (EmailBookServiceRoutesCallbackBaseNativeOverride.
                                                           underlying_read_strat_collection_by_id_http(1))
            if strat_key not in strat_collection_obj.loaded_strat_keys:
                err_str_ = (f"register_pair_strat_for_recovery_failed, {pair_strat_id=} not found in loaded strats;;;"
                            f"{pair_strat_obj=}, {strat_collection_obj=}")
                logging.error(err_str_)
                raise HTTPException(status_code=400, detail=err_str_)
            # else - valid pair strat id and not monitored

            # register pair strat
            self.pair_strat_id_to_executor_process_id_dict[pair_strat_id] = None
            return [pair_strat_obj]
        except Exception as exp:
            err_str_ = f"register_pair_strat_for_recovery failed, exception: {exp}"
            logging.exception(err_str_)
            raise HTTPException(status_code=400, detail=err_str_)


def filter_ws_pair_strat(pair_strat_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    pair_strat_params = pair_strat_obj_json.get("pair_strat_params")
    if pair_strat_params is not None:
        strat_leg1 = pair_strat_params.get("strat_leg1")
        strat_leg2 = pair_strat_params.get("strat_leg2")
        if strat_leg1 is not None and strat_leg2 is not None:
            security1 = strat_leg1.get("sec")
            security2 = strat_leg2.get("sec")
            if security1 is not None and security2 is not None:
                sec1_id = security1.get("sec_id")
                sec2_id = security2.get("sec_id")
                if sec1_id in symbols or sec2_id in symbols:
                    return True
    return False
