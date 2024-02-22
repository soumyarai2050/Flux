# python imports
import copy
import glob
import logging
import os
import signal
import subprocess
import stat
import time
import threading
import requests
from typing import Set

# third-party package imports
from pymongo import MongoClient

# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.FastApi.strat_manager_service_routes_callback import \
    StratManagerServiceRoutesCallback
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    is_service_up, get_single_exact_match_strat_from_symbol_n_side,
    get_symbol_side_key, get_ongoing_strats_from_symbol_n_side, config_yaml_dict,
    YAMLConfigurationManager, strat_executor_config_yaml_dict, ps_port,
    CURRENT_PROJECT_SCRIPTS_DIR, create_md_shell_script, MDShellEnvData, ps_host, get_new_portfolio_status,
    get_new_portfolio_limits, get_new_order_limits, CURRENT_PROJECT_DATA_DIR, is_ongoing_strat,
    get_strat_key_from_pair_strat, get_id_from_strat_key, get_new_strat_view_obj)
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.app.aggregate import (
    get_ongoing_pair_strat_filter, get_all_pair_strat_from_symbol_n_side)
from Flux.CodeGenProjects.addressbook.ProjectGroup.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_analyzer.app.log_analyzer_service_helper import log_pattern_to_restart_tail_process
from FluxPythonUtils.scripts.utility_functions import get_pid_from_port, is_process_running, except_n_log_alert
from Flux.CodeGenProjects.addressbook.ProjectGroup.strat_executor.app.trading_link import get_trading_link


class StratManagerServiceRoutesCallbackBaseNativeOverride(StratManagerServiceRoutesCallback):
    underlying_read_portfolio_status_http: Callable[..., Any] | None = None
    underlying_create_portfolio_status_http: Callable[..., Any] | None = None
    underlying_read_order_limits_http: Callable[..., Any] | None = None
    underlying_create_order_limits_http: Callable[..., Any] | None = None
    underlying_read_portfolio_limits_http: Callable[..., Any] | None = None
    underlying_create_portfolio_limits_http: Callable[..., Any] | None = None
    underlying_read_pair_strat_http: Callable[..., Any] | None = None
    underlying_read_portfolio_status_by_id_http: Callable[..., Any] | None = None
    underlying_partial_update_portfolio_status_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_http: Callable[..., Any] | None = None
    underlying_create_strat_collection_http: Callable[..., Any] | None = None
    underlying_update_strat_collection_http: Callable[..., Any] | None = None
    underlying_partial_update_pair_strat_http: Callable[..., Any] | None = None
    underlying_update_pair_strat_to_non_running_state_query_http: Callable[..., Any] | None = None
    underlying_read_pair_strat_by_id_http: Callable[..., Any] | None = None
    underlying_partial_update_all_pair_strat_http: Callable[..., Any] | None = None
    underlying_read_strat_collection_by_id_http: Callable[..., Any] | None = None
    underlying_get_pair_strat_from_symbol_side_query_http: Callable[..., Any] | None = None
    underlying_read_system_control_by_id_http: Callable[..., Any] | None = None
    underlying_partial_update_system_control_http: Callable[..., Any] | None = None
    underlying_read_system_control_http: Callable[..., Any] | None = None
    underlying_create_system_control_http: Callable[..., Any] | None = None
    underlying_create_strat_view_http: Callable[..., Any] | None = None
    underlying_delete_strat_view_http: Callable[..., Any] | None = None

    Fx_SO_FilePath = CURRENT_PROJECT_SCRIPTS_DIR / f"fx_so.sh"
    RecoveredKillSwitchUpdate: bool = False

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.FastApi.strat_manager_service_http_routes import (
            underlying_read_portfolio_status_http, underlying_create_portfolio_status_http,
            underlying_read_order_limits_http, underlying_create_order_limits_http,
            underlying_read_portfolio_limits_http, underlying_create_portfolio_limits_http,
            underlying_read_pair_strat_http, underlying_read_portfolio_status_by_id_http,
            underlying_partial_update_portfolio_status_http, underlying_read_strat_collection_http,
            underlying_create_strat_collection_http, underlying_update_strat_collection_http,
            underlying_partial_update_pair_strat_http, underlying_update_pair_strat_to_non_running_state_query_http,
            underlying_read_pair_strat_by_id_http, underlying_partial_update_all_pair_strat_http,
            underlying_read_strat_collection_by_id_http, underlying_get_pair_strat_from_symbol_side_query_http,
            underlying_read_system_control_by_id_http, underlying_partial_update_system_control_http,
            underlying_read_system_control_http, underlying_create_system_control_http,
            underlying_create_strat_view_http, underlying_delete_strat_view_http)
        cls.underlying_read_portfolio_status_http = underlying_read_portfolio_status_http
        cls.underlying_create_portfolio_status_http = underlying_create_portfolio_status_http
        cls.underlying_read_order_limits_http = underlying_read_order_limits_http
        cls.underlying_create_order_limits_http = underlying_create_order_limits_http
        cls.underlying_read_portfolio_limits_http = underlying_read_portfolio_limits_http
        cls.underlying_create_portfolio_limits_http = underlying_create_portfolio_limits_http
        cls.underlying_read_pair_strat_http = underlying_read_pair_strat_http
        cls.underlying_read_portfolio_status_by_id_http = underlying_read_portfolio_status_by_id_http
        cls.underlying_partial_update_portfolio_status_http = underlying_partial_update_portfolio_status_http
        cls.underlying_read_strat_collection_http = underlying_read_strat_collection_http
        cls.underlying_create_strat_collection_http = underlying_create_strat_collection_http
        cls.underlying_update_strat_collection_http = underlying_update_strat_collection_http
        cls.underlying_partial_update_pair_strat_http = underlying_partial_update_pair_strat_http
        cls.underlying_update_pair_strat_to_non_running_state_query_http = (
            underlying_update_pair_strat_to_non_running_state_query_http)
        cls.underlying_read_pair_strat_by_id_http = underlying_read_pair_strat_by_id_http
        cls.underlying_partial_update_all_pair_strat_http = underlying_partial_update_all_pair_strat_http
        cls.underlying_read_strat_collection_by_id_http = underlying_read_strat_collection_by_id_http
        cls.underlying_read_system_control_by_id_http = underlying_read_system_control_by_id_http
        cls.underlying_partial_update_system_control_http = underlying_partial_update_system_control_http
        cls.underlying_read_system_control_http = underlying_read_system_control_http
        cls.underlying_create_system_control_http = underlying_create_system_control_http
        cls.underlying_get_pair_strat_from_symbol_side_query_http = (
            underlying_get_pair_strat_from_symbol_side_query_http)
        cls.underlying_create_strat_view_http = underlying_create_strat_view_http
        cls.underlying_delete_strat_view_http = underlying_delete_strat_view_http

    def __init__(self):
        self.asyncio_loop = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.static_data: SecurityRecordManager | None = None
        self.pair_strat_id_to_executor_process_id_dict: Dict[int, int] = {}
        self.port_to_executor_http_client_dict: Dict[int, StratExecutorServiceHttpClient] = {}

        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 3mobile_book
        self.trading_link = get_trading_link()

        super().__init__()

    @staticmethod
    async def _check_n_create_portfolio_status():
        async with PortfolioStatus.reentrant_lock:
            portfolio_status_list: List[PortfolioStatus] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_status_http())
            if mobile_book == len(portfolio_status_list):  # no portfolio status set yet, create one
                portfolio_status: PortfolioStatus = get_new_portfolio_status()
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_status_http(
                    portfolio_status)

    @staticmethod
    async def _check_n_create_system_control():
        async with SystemControl.reentrant_lock:
            system_control_list: List[SystemControl] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_system_control_http())
            if mobile_book == len(system_control_list):  # no system_control set yet, create one
                system_control: SystemControl = SystemControl(_id=1, kill_switch=False)
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_system_control_http(
                    system_control)

    @staticmethod
    async def _check_n_create_order_limits():
        async with OrderLimits.reentrant_lock:
            order_limits_list: List[OrderLimits] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_order_limits_http())
            if mobile_book == len(order_limits_list):  # no order_limits set yet, create one
                order_limits: OrderLimits = get_new_order_limits()
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_order_limits_http(
                    order_limits)

    @staticmethod
    async def _check_n_create_portfolio_limits():
        async with PortfolioLimits.reentrant_lock:
            portfolio_limits_list: List[PortfolioLimits] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_limits_http())
            if mobile_book == len(portfolio_limits_list):  # no portfolio_limits set yet, create one
                portfolio_limits = get_new_portfolio_limits()
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_portfolio_limits_http(
                    portfolio_limits)

    @staticmethod
    async def _check_n_create_strat_collection():
        async with StratCollection.reentrant_lock:
            strat_collection_list: List[StratCollection] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_collection_http())
            if len(strat_collection_list) == mobile_book:
                created_strat_collection = StratCollection(_id=1, loaded_strat_keys=[], buffered_strat_keys=[])
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_collection_http(
                    created_strat_collection)

    @staticmethod
    async def _check_and_create_start_up_models() -> bool:
        try:
            await StratManagerServiceRoutesCallbackBaseNativeOverride._check_n_create_portfolio_status()
            await StratManagerServiceRoutesCallbackBaseNativeOverride._check_n_create_system_control()
            await StratManagerServiceRoutesCallbackBaseNativeOverride._check_n_create_order_limits()
            await StratManagerServiceRoutesCallbackBaseNativeOverride._check_n_create_portfolio_limits()
            await StratManagerServiceRoutesCallbackBaseNativeOverride._check_n_create_strat_collection()
        except Exception as e:
            logging.exception(f"_check_and_create_start_up_models failed, exception: {e}")
            return False
        else:
            return True

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
            service_up_flag_env_var = os.environ.get(f"phone_book_{ps_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        # running all existing executor
                        self.service_ready = True
                        self.recover_kill_switch_state()
                        self.recover_existing_executors()
                    self.service_ready = True
                    print(f"INFO: phone_book service is ready: {datetime.datetime.now().time()}")
                else:
                    logging.warning(f"_app_launch_pre_thread_func: service not ready yet;;; "
                                    f"{self.service_up = }")
                if not self.service_up:
                    try:
                        if is_service_up(ignore_error=(service_up_no_error_retry_count > mobile_book)):
                            run_coro = self._check_and_create_start_up_models()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                            try:
                                # block for task to finish
                                self.service_up = future.result()
                                should_sleep = False
                            except Exception as e:
                                err_str_ = (f"_check_and_create_portfolio_status_and_order_n_portfolio_limits "
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

                    # Checking and Restarting crashed executors
                    self.run_crashed_executors()
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
        pending_strats: List[PairStrat] = []
        pending_strats_id_list: List[int] = []
        for pair_strat_id, executor_process_id in self.pair_strat_id_to_executor_process_id_dict.items():
            if not is_process_running(executor_process_id):
                logging.info(f"process for {pair_strat_id = } and {executor_process_id = } found killed, "
                             f"restarting again ...")
                pending_strats_id_list.append(pair_strat_id)

                pair_strat: PairStrat = (
                    await StratManagerServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_pair_strat_by_id_http(pair_strat_id))
                pending_strats.append(pair_strat)

        for pair_strat_id in pending_strats_id_list:
            del self.pair_strat_id_to_executor_process_id_dict[pair_strat_id]

        if pending_strats:
            await self._async_start_executor_server_by_task_submit(pending_strats, is_crash_recovery=True)

    async def _async_start_executor_server_by_task_submit(self, pending_strats: List[PairStrat],
                                                          is_crash_recovery: bool | None = False):
        tasks: List = []
        for idx, pending_strat in enumerate(pending_strats):
            task = asyncio.create_task(self._start_executor_server(pending_strat, is_crash_recovery), name=str(idx))
            tasks.append(task)

        completed_tasks: Set | None = None
        pending_tasks: Set | None = None
        while True:
            try:
                completed_tasks, pending_tasks = \
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=6mobile_book)
            except Exception as e:
                logging.exception(f"start_executor_server asyncio.wait failed with exception: {e}")
            while completed_tasks:
                completed_task = None
                try:
                    completed_task = completed_tasks.pop()
                    completed_task.result()
                except Exception as e:
                    idx = int(completed_task.get_name())
                    logging.exception(f"start_executor_server failed for pair_strat_id: {pending_strats[idx]} - "
                                      f"can't recover executor server for it;;; exception: {e}, "
                                      f"pair_strat: {pending_strats[idx]}")
            if pending_tasks:
                tasks = [*pending_tasks, ]
            else:
                break

    def recover_kill_switch_state(self):
        # if db true and trading is false - trigger_kill_switch and not update db
        run_coro = self._recover_kill_switch_state()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            future.result()
        except Exception as e:
            err_str_ = f"_recover_kill_switch_state failed - check and handle kill state manually, exception: {e}"
            logging.exception(err_str_)
        finally:
            StratManagerServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate = False  # reverting state

    async def _recover_kill_switch_state(self) -> None:
        kill_switch_state = await self.trading_link.is_kill_switch_enabled()

        async with SystemControl.reentrant_lock:
            system_control_id = 1
            system_control: SystemControl = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.
                underlying_read_system_control_by_id_http(system_control_id))

            if not system_control.kill_switch and kill_switch_state:
                system_control.kill_switch = True
                StratManagerServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate = True
                await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                       underlying_partial_update_system_control_http(
                        jsonable_encoder(system_control, by_alias=True, exclude_none=True)))
            elif not kill_switch_state and system_control.kill_switch:
                logging.warning("Found kill switch in db as True but is_kill_switch_enabled returned False, "
                                "calling trading_link.trigger_kill_switch")
                await self.trading_link.trigger_kill_switch()
            # else not required: all okay

    @staticmethod
    def create_n_run_fx_so_shell_script():
        # creating run_symbol_overview.sh file
        run_fx_symbol_overview_file_path = StratManagerServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath

        db_name = os.environ.get("DB_NAME")
        if db_name is None:
            db_name = "phone_book"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(host=ps_host, port=ps_port, db_name=db_name, project_name="phone_book"))

        create_md_shell_script(md_shell_env_data, run_fx_symbol_overview_file_path, "SO")
        os.chmod(run_fx_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_fx_symbol_overview_file_path}"])

    async def async_recover_existing_executors(self) -> None:
        loaded_pair_strats: List[PairStrat] = \
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http()
        strat_collection_list: List[StratCollection] =  \
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_collection_http()

        if strat_collection_list:
            if len(strat_collection_list) == 1:
                strat_collection = strat_collection_list[mobile_book]
                loaded_strat_keys: List[str] = strat_collection.loaded_strat_keys

                loaded_pair_strat_id_list: List[int] = []
                for loaded_strat_key in loaded_strat_keys:
                    loaded_pair_strat_id_list.append(get_id_from_strat_key(loaded_strat_key))

                crashed_strats: List[PairStrat] = []
                for pair_strat in loaded_pair_strats:
                    if pair_strat.id in loaded_pair_strat_id_list:
                        if pair_strat.port is not None:
                            strat_executor_http_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(
                                pair_strat.host, pair_strat.port)
                            try:
                                # Checking if get-request works
                                strat_executor_http_client.get_all_ui_layout_client()
                            except requests.exceptions.Timeout:
                                # If timeout error occurs it is most probably that executor server got hung/stuck
                                # logging and killing this executor
                                logging.exception(f"Found executor with port: {pair_strat.port} in hung state, killing "
                                                  f"the executor process;;; pair_strat: {pair_strat}")
                                pid = get_pid_from_port(pair_strat.port)
                                os.kill(pid, signal.SIGKILL)

                                # Updating pair_strat
                                await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                                       underlying_partial_update_pair_strat_http(jsonable_encoder(
                                           PairStrat(_id=pair_strat.id, strat_state=StratState.StratState_ERROR,
                                                     port=None, is_partially_running=False,
                                                     is_executor_running=False), by_alias=True, exclude_none=True)))

                            except Exception as e:
                                if "Failed to establish a new connection: [Errno 111] Connection refused" in str(e):
                                    logging.error(f"PairStrat found to have port set to {pair_strat.port} but executor "
                                                  f"server is down, recovering executor for "
                                                  f"{pair_strat.id = };;; {pair_strat = }")
                                    crashed_strats.append(pair_strat)
                                elif ("The Web Server may be down, too busy, or experiencing other problems preventing "
                                      "it from responding to requests" in str(e) and "status_code: 5mobile_book3" in str(e)):
                                    pid = get_pid_from_port(pair_strat.port)
                                    if pid is not None:
                                        os.kill(pid, signal.SIGKILL)
                                    crashed_strats.append(pair_strat)
                                else:
                                    logging.exception("Something went wrong while checking is_service_up of executor "
                                                      f"with port: {pair_strat.port} in pair_strat strat_up recovery "
                                                      f"check - force kill this executor if is running, "
                                                      f"exception: {e};;; {pair_strat = }")
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
            raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)

    def app_launch_pre(self):
        StratManagerServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()

        self.port = ps_port
        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

        # removing md scripts
        try:
            if os.path.exists(StratManagerServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath):
                os.remove(StratManagerServiceRoutesCallbackBaseNativeOverride.Fx_SO_FilePath)
        except Exception as e:
            err_str_ = f"Something went wrong while deleting fx_so shell script, exception: {e}"
            logging.error(err_str_)

    def get_generic_read_route(self):
        return None

    # Example: Soft API Query Interfaces

    async def update_portfolio_status_by_order_or_fill_data_query_pre(
            self, portfolio_status_class_type: Type[PortfolioStatus], overall_buy_notional: float | None = None,
            overall_sell_notional: float | None = None, overall_buy_fill_notional: float | None = None,
            overall_sell_fill_notional: float | None = None):
        async with PortfolioStatus.reentrant_lock:
            updated_portfolio_status = PortfolioStatusOptional()
            portfolio_status: PortfolioStatus = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_status_by_id_http(1))

            updated_portfolio_status.id = portfolio_status.id
            if overall_buy_notional is not None:
                if portfolio_status.overall_buy_notional is None:
                    portfolio_status.overall_buy_notional = mobile_book
                updated_portfolio_status.overall_buy_notional = (portfolio_status.overall_buy_notional +
                                                                 overall_buy_notional)
            if overall_sell_notional is not None:
                if portfolio_status.overall_sell_notional is None:
                    portfolio_status.overall_sell_notional = mobile_book
                updated_portfolio_status.overall_sell_notional = (portfolio_status.overall_sell_notional +
                                                                  overall_sell_notional)
            if overall_buy_fill_notional is not None:
                if portfolio_status.overall_buy_fill_notional is None:
                    portfolio_status.overall_buy_fill_notional = mobile_book
                updated_portfolio_status.overall_buy_fill_notional = (portfolio_status.overall_buy_fill_notional +
                                                                      overall_buy_fill_notional)
            if overall_sell_fill_notional is not None:
                if portfolio_status.overall_sell_fill_notional is None:
                    portfolio_status.overall_sell_fill_notional = mobile_book
                updated_portfolio_status.overall_sell_fill_notional = (portfolio_status.overall_sell_fill_notional +
                                                                       overall_sell_fill_notional)
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_portfolio_status_http(
                json.loads(updated_portfolio_status.model_dump_json(by_alias=True, exclude_none=True)))
        return []

    # Code-generated
    async def get_pair_strat_sec_filter_json_query_pre(self, pair_strat_class_type: Type[PairStrat], security_id: str):
        return await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http(
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
        """
        update the exchange of derived (if we have one)
        """
        return

    async def get_dismiss_filter_portfolio_limit_brokers_query_pre(
            self, dismiss_filter_portfolio_limit_broker_class_type: Type[DismissFilterPortfolioLimitBroker],
            security_id1: str, security_id2: str):
        # get security name from : pair_strat_params.strat_legs and then redact pattern
        # security.sec_id (a pattern in positions) where there is a value match
        dismiss_filter_agg_pipeline = {'redact': [("security.sec_id",
                                                   security_id1,
                                                   security_id2)]}
        filtered_portfolio_limits: List[PortfolioLimits] = \
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_portfolio_limits_http(
                dismiss_filter_agg_pipeline, self.get_generic_read_route())
        if len(filtered_portfolio_limits) == 1:
            if filtered_portfolio_limits[mobile_book].eligible_brokers is not None:
                eligible_brokers = [eligible_broker for eligible_broker in
                                    filtered_portfolio_limits[mobile_book].eligible_brokers if
                                    eligible_broker.sec_positions]
                return_obj = DismissFilterPortfolioLimitBroker(brokers=eligible_brokers)
                return [return_obj]
        elif len(filtered_portfolio_limits) > 1:
            err_str_ = f"filtered_portfolio_limits expected: 1, found: " \
                       f"{str(len(filtered_portfolio_limits))}, for filter: " \
                       f"{dismiss_filter_agg_pipeline}, filtered_portfolio_limits: " \
                       f"{filtered_portfolio_limits}; use SWAGGER UI to check / fix and re-try "
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)
        else:
            err_str_ = (f"No filtered_portfolio_limits found for symbols of leg1 and leg2: {security_id1} and "
                        f"{security_id2}")
            logging.warning(err_str_)
            raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)

    async def create_strat_view_for_strat(self, pair_strat: PairStrat):
        new_strat_view = get_new_strat_view_obj(pair_strat.id)
        await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_view_http(new_strat_view)

    @except_n_log_alert()
    async def create_pair_strat_pre(self, pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 5mobile_book3 exception, let the caller retry
            err_str_ = f"create_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat_obj)};;; {pair_strat_obj = }"
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_book3, detail=err_str_)
        self._set_derived_side(pair_strat_obj)
        self._set_derived_exchange(pair_strat_obj)
        pair_strat_obj.frequency = 1
        pair_strat_obj.pair_strat_params_update_seq_num = mobile_book
        pair_strat_obj.last_active_date_time = DateTime.utcnow()

        pair_strat_obj.host = strat_executor_config_yaml_dict.get("server_host")
        pair_strat_obj.is_executor_running = False
        pair_strat_obj.is_partially_running = False

        # creating strat_view object for this start
        await self.create_strat_view_for_strat(pair_strat_obj)

        # @@@ Warning: Below handling of state collection is handled from ui also - see where can code be remove
        # to avoid duplicate
        async with StratCollection.reentrant_lock:
            strat_collection_obj: StratCollection = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.
                underlying_read_strat_collection_by_id_http(1))
            strat_key = get_strat_key_from_pair_strat(pair_strat_obj)
            strat_collection_obj.loaded_strat_keys.append(strat_key)
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                strat_collection_obj)

        # starting executor server for current pair strat
        await self._start_executor_server(pair_strat_obj)

    @staticmethod
    async def _apply_checks_n_log_error(pair_strat: PairStrat):
        """
        implement any strat management checks here (create / update strats)
        """
        # First Checking if any ongoing strat exists with same symbol_side pairs in same legs of param pair_strat,
        # that means if one strat is ongoing with s1-sd1 and s2-sd2 symbol-side pair legs then param pair_strat
        # must not have same symbol-side pair legs else HTTP exception is raised
        ongoing_pair_strats: List[PairStrat] = \
            await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                   underlying_get_pair_strat_from_symbol_side_query_http(
                    pair_strat.pair_strat_params.strat_leg1.sec.sec_id, pair_strat.pair_strat_params.strat_leg1.side))

        leg1_symbol, leg1_side = (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                                  pair_strat.pair_strat_params.strat_leg1.side)
        leg2_symbol, leg2_side = (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                                  pair_strat.pair_strat_params.strat_leg2.side)
        if ongoing_pair_strats:
            # raising exception only if ongoing pair_strat's leg1's symbol-side are same as
            # param pair_strat's leg1's symbol-side and same for leg2
            ongoing_pair_strat = ongoing_pair_strats[mobile_book]
            if (((leg1_symbol == ongoing_pair_strat.pair_strat_params.strat_leg1.sec.sec_id) and
                 (leg2_symbol == ongoing_pair_strat.pair_strat_params.strat_leg2.sec.sec_id)) and
                    (leg1_side == ongoing_pair_strat.pair_strat_params.strat_leg1.side) and
                    (leg2_side == ongoing_pair_strat.pair_strat_params.strat_leg2.side) and
                    (ongoing_pair_strat.id != pair_strat.id)):
                err_str_ = ("Ongoing strat already exists with same symbol-side pair legs - can't activate this "
                            f"strat till other strat is ongoing;;; {ongoing_pair_strat = }")
                logging.error(err_str_)
                raise HTTPException(status_code=4mobile_bookmobile_book, detail=err_str_)

        # Checking if any strat exists with opp symbol and side of param pair_strat that activated today,
        # for instance if s1-sd1 and s2-sd2 are symbol-side pairs in param pair_strat's legs then checking there must
        # not be any strat activated today with s1-sd2 and s2-sd1 symbol-side pair legs, if it is found then this
        # strat can't be activated

        first_matched_strat_lock_file_path_list: List[str] = (
            glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                          f"{leg1_symbol}_{leg2_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        sec_matched_strat_lock_file_path_list: List[str] = (
            glob.glob(str(CURRENT_PROJECT_DATA_DIR /
                          f"{leg2_symbol}_{leg1_side}_*_{DateTime.date(DateTime.utcnow())}.json.lock")))

        # checking both legs - If first_matched_strat_lock_file_path_list and sec_matched_strat_lock_file_path_list
        # have file names having same pair_strat_id with today's date along with required symbol-side pair
        for matched_strat_file_path in first_matched_strat_lock_file_path_list:
            suffix_pattern = matched_strat_file_path[(matched_strat_file_path.index(leg2_side) + len(leg2_side)):]
            for sec_matched_strat_lock_file_path in sec_matched_strat_lock_file_path_list:
                if sec_matched_strat_lock_file_path.endswith(suffix_pattern):
                    err_str_ = ("Found strat activated today with symbols of this strat being used in opposite sides"
                                " - can't activate this strat today")
                    logging.error(err_str_)
                    raise HTTPException(status_code=4mobile_bookmobile_book, detail=err_str_)

    @staticmethod
    def get_lock_file_names_from_pair_strat(pair_strat: PairStrat) -> Tuple[PurePath, PurePath]:
        return ((CURRENT_PROJECT_DATA_DIR / f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}_"
                                            f"{pair_strat.pair_strat_params.strat_leg1.side}_{pair_strat.id}_"
                                            f"{DateTime.date(DateTime.utcnow())}.json.lock"),
                (CURRENT_PROJECT_DATA_DIR / f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id}_"
                                            f"{pair_strat.pair_strat_params.strat_leg2.side}_{pair_strat.id}_"
                                            f"{DateTime.date(DateTime.utcnow())}.json.lock"))

    async def _update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat,
                                     updated_pair_strat_obj: PairStrat) -> bool | None:
        """
        Return true if check passed false otherwise
        """
        check_passed = True
        if stored_pair_strat_obj.strat_state != StratState.StratState_ACTIVE and \
                updated_pair_strat_obj.strat_state == StratState.StratState_ACTIVE:
            await self._apply_checks_n_log_error(stored_pair_strat_obj)  # raises HTTPException internally
            if stored_pair_strat_obj.strat_state == StratState.StratState_READY:
                leg1_lock_file_path, leg2_lock_file_path = (
                    self.get_lock_file_names_from_pair_strat(updated_pair_strat_obj))
                with open(leg1_lock_file_path, "w") as fl:  # creating empty file
                    pass
                with open(leg2_lock_file_path, "w") as fl:  # creating empty file
                    pass
            # else not required: create strat lock file only if moving the strat state from
            # StratState_READY to StratState_ACTIVE
        if updated_pair_strat_obj.strat_state == StratState.StratState_DONE:
            # warning and above log level is required
            logging.warning(f"ResetLogAnalyzerCache;;;pair_strat_log_key: "
                            f"{get_pair_strat_log_key(updated_pair_strat_obj)}")
        return check_passed

    def _update_port_to_executor_http_client_dict_from_updated_pair_strat(self, updated_pair_strat_obj: PairStrat):
        if (updated_pair_strat_obj.port is not None and
                updated_pair_strat_obj.port not in self.port_to_executor_http_client_dict):
            self.port_to_executor_http_client_dict[updated_pair_strat_obj.port] = (
                StratExecutorServiceHttpClient.set_or_get_if_instance_exists(updated_pair_strat_obj.host,
                                                                             updated_pair_strat_obj.port))

    async def update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj: PairStrat):
        if not self.service_ready:
            # raise service unavailable 5mobile_book3 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(updated_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_book3, detail=err_str_)

        if updated_pair_strat_obj.frequency is None:
            updated_pair_strat_obj.frequency = mobile_book
        updated_pair_strat_obj.frequency += 1

        if updated_pair_strat_obj.pair_strat_params_update_seq_num is None:
            updated_pair_strat_obj.pair_strat_params_update_seq_num = mobile_book
        updated_pair_strat_obj.pair_strat_params_update_seq_num += 1
        updated_pair_strat_obj.last_active_date_time = DateTime.utcnow()

        res = await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        if not res:
            logging.debug(f"Alerts updated by _update_strat_status_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id, stored_pair_strat_obj.pair_strat_params.strat_leg1.side)])};;; "
                          f"{updated_pair_strat_obj = }")

        # updating port_to_executor_http_client_dict with this port if not present
        self._update_port_to_executor_http_client_dict_from_updated_pair_strat(updated_pair_strat_obj)

        return updated_pair_strat_obj

    async def partial_update_pair_strat_pre(self, stored_pair_strat_obj: PairStrat, updated_pair_strat_obj_dict: Dict):
        if not self.service_ready:
            # raise service unavailable 5mobile_book3 exception, let the caller retry
            # @@@ IMPORTANT: below error string is used to catch this specific exception, please update
            # all catch handling too if error msg is changed
            err_str_ = "partial_update_pair_strat_pre not ready - service is not initialized yet, " \
                       f"pair_strat_key: {get_pair_strat_log_key(stored_pair_strat_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_book3, detail=err_str_)

        updated_pair_strat_obj_dict["frequency"] = stored_pair_strat_obj.frequency + 1

        if updated_pair_strat_obj_dict.get("pair_strat_params") is not None:
            if stored_pair_strat_obj.pair_strat_params_update_seq_num is None:
                stored_pair_strat_obj.pair_strat_params_update_seq_num = mobile_book
            updated_pair_strat_obj_dict["pair_strat_params_update_seq_num"] = \
                stored_pair_strat_obj.pair_strat_params_update_seq_num + 1

        updated_pair_strat_obj_dict["last_active_date_time"] = DateTime.utcnow()

        updated_pydantic_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_pair_strat_obj.model_dump(by_alias=True)),
                                                         updated_pair_strat_obj_dict)
        updated_pair_strat_obj = PairStratOptional(**updated_pydantic_obj_dict)
        res = await self._update_pair_strat_pre(stored_pair_strat_obj, updated_pair_strat_obj)
        if not res:
            logging.debug(f"Alerts updated by _update_strat_status_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(stored_pair_strat_obj.pair_strat_params.strat_leg1.sec.sec_id, stored_pair_strat_obj.pair_strat_params.strat_leg1.side)])};;; "
                          f"{updated_pair_strat_obj = }")
        updated_pair_strat_obj_dict = jsonable_encoder(updated_pair_strat_obj, by_alias=True, exclude_none=True)

        # updating port_to_executor_http_client_dict with this port if not present
        self._update_port_to_executor_http_client_dict_from_updated_pair_strat(updated_pair_strat_obj)

        return updated_pair_strat_obj_dict

    async def pause_all_active_strats_query_pre(self, pair_strat_class_type: Type[PairStrat]):
        async with PairStrat.reentrant_lock:
            pair_strat_list: List[PairStrat] = (
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http())

            updated_pair_strats_list: List[Dict] = []
            for pair_strat in pair_strat_list:
                # Putting strat to pause if strat is active
                if pair_strat.strat_state == StratState.StratState_ACTIVE:
                    update_pair_strat = PairStratBaseModel(_id=pair_strat.id, strat_state=StratState.StratState_PAUSED)
                    updated_pair_strats_list.append(
                        jsonable_encoder(update_pair_strat, by_alias=True, exclude_none=True))

            if updated_pair_strats_list:
                (await StratManagerServiceRoutesCallbackBaseNativeOverride.
                 underlying_partial_update_all_pair_strat_http(updated_pair_strats_list))
        return []

    async def update_pair_strat_to_non_running_state_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                               pair_strat_id: int):
        pair_strat = PairStratOptional(_id=pair_strat_id)
        pair_strat.port = None
        pair_strat.is_partially_running = False
        pair_strat.is_executor_running = False

        update_pair_strat = \
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_pair_strat_http(
                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
        return [update_pair_strat]

    async def _start_executor_server(self, pair_strat: PairStrat, is_crash_recovery: bool | None = None) -> None:
        if pair_strat.port is not None:
            # If pair strat already exists and executor already have run before

            await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                   underlying_update_pair_strat_to_non_running_state_query_http(pair_strat.id))
        # else not required: if it is newly created pair strat then already values are False

        code_gen_projects_dir = PurePath(__file__).parent.parent.parent
        executor_path = code_gen_projects_dir / "strat_executor" / "scripts" / 'launch_beanie_fastapi.py'
        if is_crash_recovery:
            # 1 is sent to indicate it is recovery restart
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_strat.id}', "1", '&'])
        else:
            executor = subprocess.Popen(['python', str(executor_path), f'{pair_strat.id}', '&'])

        logging.info(f"Launched {executor_path} ...")
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
            await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http(
                get_ongoing_pair_strat_filter(), self.get_generic_read_route())
        ongoing_symbol_n_exch_set: Set[str] = set()
        ongoing_strat_symbols_n_exchange = OngoingStratsSymbolNExchange(symbol_n_exchange=[])

        before_len: int = mobile_book
        for pair_strat in pair_strat_list:
            leg1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            leg1_exch = pair_strat.pair_strat_params.strat_leg1.exch_id
            leg2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            leg2_exch = pair_strat.pair_strat_params.strat_leg2.exch_id
            leg1_symbol_n_exch = SymbolNExchange(symbol=leg1_symbol, exchange=leg1_exch)
            leg2_symbol_n_exch = SymbolNExchange(symbol=leg2_symbol, exchange=leg2_exch)

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
        db_name: str = f"strat_executor_{pair_strat_id}"

        if db_name in mongo_client.list_database_names():
            mongo_client.drop_database(db_name)
        else:
            err_str_ = (f"Unexpected: {db_name = } not found in mongo_client for uri: "
                        f"{mongo_server_uri} being used by current strat, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)

    async def delete_pair_strat_pre(self, pair_strat_to_be_deleted: PairStrat):
        port: int = pair_strat_to_be_deleted.port
        sec_id = pair_strat_to_be_deleted.pair_strat_params.strat_leg1.sec.sec_id
        side = pair_strat_to_be_deleted.pair_strat_params.strat_leg1.side

        start_key = get_strat_key_from_pair_strat(pair_strat_to_be_deleted)
        strat_collection = await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                                  underlying_read_strat_collection_by_id_http(1))
        if start_key in strat_collection.loaded_strat_keys:
            if pair_strat_to_be_deleted.port is not None:
                strat_web_client: StratExecutorServiceHttpClient = (
                    StratExecutorServiceHttpClient.set_or_get_if_instance_exists(pair_strat_to_be_deleted.host,
                                                                                 pair_strat_to_be_deleted.port))
            else:
                err_str_ = f"pair_strat object has no port;;; {pair_strat_to_be_deleted = }"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)

            if strat_web_client is None:
                err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                            f"{port = }, ignoring this strat delete, likely bug in server cache dict handling, "
                            f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])};;; "
                            f"{pair_strat_to_be_deleted = }")
                logging.error(err_str_)
                raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)

            if is_ongoing_strat(pair_strat_to_be_deleted):
                err_str_ = ("This strat is ongoing: Deletion of ongoing strat is not supported, "
                            "ignoring this strat delete, try again once it is"
                            f"not ongoing, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)

            # removing and updating relative models
            try:
                strat_web_client.put_strat_to_snooze_query_client()
            except Exception as e:
                err_str_ = ("Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                            f"delete of this strat, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}, "
                            f"exception: {e}, ;;; {pair_strat_to_be_deleted = }")
                logging.error(err_str_)
                raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)
            self._close_executor_server(pair_strat_to_be_deleted.id)  # closing executor

            # Dropping database for this strat
            code_gen_projects_dir = PurePath(__file__).parent.parent.parent
            executor_config_file_path = (code_gen_projects_dir / "strat_executor" /
                                         "data" / f"config.yaml")
            if os.path.exists(executor_config_file_path):
                server_config_yaml_dict = (
                    YAMLConfigurationManager.load_yaml_configurations(str(executor_config_file_path)))
                mongo_server_uri = server_config_yaml_dict.get("mongo_server")
                if mongo_server_uri is not None:
                    self._drop_executor_db_for_deleting_pair_strat(mongo_server_uri, pair_strat_to_be_deleted.id,
                                                                   sec_id, side)
                else:
                    err_str_ = (f"key 'mongo_server' missing in strat_executor/data/config.yaml, ignoring this"
                                f"strat delete, symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
                    logging.error(err_str_)
                    raise HTTPException(detail=err_str_, status_code=4mobile_bookmobile_book)
            else:
                err_str_ = (f"Config file for {port = } missing, must exists since executor is running from this"
                            f"config, ignoring this strat delete, symbol_side_key: "
                            f"{get_symbol_side_key([(sec_id, side)])}")
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=4mobile_bookmobile_book)

            # Removing strat_key from loaded strat keys
            async with StratCollection.reentrant_lock:
                strat_key = get_strat_key_from_pair_strat(pair_strat_to_be_deleted)
                obj_id = 1
                strat_collection: StratCollection = (
                    await StratManagerServiceRoutesCallbackBaseNativeOverride.
                    underlying_read_strat_collection_by_id_http(obj_id))

                try:
                    strat_collection.loaded_strat_keys.remove(strat_key)
                except ValueError as val_err:
                    if "x not in list" in str(val_err):
                        logging.error(f"Unexpected: Can't find {strat_key = } in strat_collection's loaded"
                                      f"keys while deleting strat;;; {strat_collection = }")
                    else:
                        logging.error(f"Something unexpected happened while removing {strat_key = } from "
                                      f"loaded strat_keys in strat_collection - ignoring this strat_key removal;;; "
                                      f"{strat_collection = }")
                    return

                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_update_strat_collection_http(
                    strat_collection)

            # Removing StratView for this strat
            async with StratView.reentrant_lock:
                await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_view_http(
                    pair_strat_to_be_deleted.id)

        else:
            err_str_ = ("Strat is not loaded, Deletion of strat that is not in loaded collections is not supported, "
                        "please load strat and keep it not ongoing and then retry, ignoring this strat delete, "
                        f"symbol_side_key: {get_symbol_side_key([(sec_id, side)])}")
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=4mobile_bookmobile_book)

    async def unload_pair_strats(self, stored_strat_collection_obj: StratCollection,
                                 updated_strat_collection_obj: StratCollection) -> None:
        updated_strat_collection_loaded_strat_keys_frozenset = frozenset(updated_strat_collection_obj.loaded_strat_keys)
        stored_strat_collection_loaded_strat_keys_frozenset = frozenset(stored_strat_collection_obj.loaded_strat_keys)
        # existing items in stored loaded frozenset but not in the updated stored frozen set need to move to done state
        unloaded_strat_keys_frozenset = stored_strat_collection_loaded_strat_keys_frozenset.difference(
            updated_strat_collection_loaded_strat_keys_frozenset)
        if len(unloaded_strat_keys_frozenset) != mobile_book:
            unloaded_strat_key: str
            for unloaded_strat_key in unloaded_strat_keys_frozenset:
                if unloaded_strat_key in updated_strat_collection_obj.buffered_strat_keys:  # unloaded not deleted
                    pair_strat_id: int = get_id_from_strat_key(unloaded_strat_key)
                    pair_strat = \
                        await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                               underlying_read_pair_strat_by_id_http(pair_strat_id))
                    if pair_strat.port is not None:
                        strat_executor_web_client: StratExecutorServiceHttpClient = (
                            self.port_to_executor_http_client_dict.get(pair_strat.port))
                    else:
                        err_str_ = (f"pair_strat object has no port while unloading - "
                                    f"ignoring this strat unload;;; {pair_strat = }")
                        logging.error(err_str_)
                        raise HTTPException(detail=err_str_, status_code=4mobile_bookmobile_book)

                    if strat_executor_web_client is None:
                        err_str_ = ("Can't find any web_client present in server cache dict for ongoing strat of "
                                    f"{pair_strat.port = }, ignoring this strat unload,"
                                    f"likely bug in server cache dict handling;;; {pair_strat = }")
                        logging.error(err_str_)
                        raise HTTPException(status_code=4mobile_bookmobile_book, detail=err_str_)

                    if is_ongoing_strat(pair_strat):
                        error_str = f"unloading an ongoing pair strat key: {unloaded_strat_key} is not supported, " \
                                    f"current {pair_strat.strat_state = }, " \
                                    f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; {pair_strat = }"
                        logging.error(error_str)
                        raise HTTPException(status_code=4mobile_bookmobile_book, detail=error_str)
                    elif pair_strat.strat_state in [StratState.StratState_DONE, StratState.StratState_READY,
                                                    StratState.StratState_SNOOZED]:
                        # removing and updating relative models
                        try:
                            strat_executor_web_client.put_strat_to_snooze_query_client()
                        except Exception as e:
                            err_str_ = (
                                "Some error occurred in executor while setting strat to SNOOZED state, ignoring "
                                f"unload of this strat, pair_strat_key: {get_pair_strat_log_key(pair_strat)}, ;;;"
                                f"{pair_strat = }")
                            logging.error(err_str_)
                            raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)
                        self._close_executor_server(pair_strat.id)    # closing executor
                    else:
                        err_str_ = (f"Unloading strat with strat_state: {pair_strat.strat_state} is not supported,"
                                    f"try unloading when start is READY or DONE, pair_strat_key: "
                                    f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat = }")
                        logging.error(err_str_)
                        raise Exception(err_str_)

                    pair_strat = PairStratOptional(_id=pair_strat.id, strat_state=StratState.StratState_SNOOZED)
                    await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_pair_strat_http(
                        jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
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
        if len(reloaded_strat_keys_frozenset) != mobile_book:
            reloaded_strat_key: str
            for reloaded_strat_key in reloaded_strat_keys_frozenset:
                if reloaded_strat_key in updated_strat_collection_obj.loaded_strat_keys:  # loaded not deleted
                    pair_strat_id: int = get_id_from_strat_key(reloaded_strat_key)
                    pair_strat = \
                        await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_by_id_http(
                            pair_strat_id)

                    # starting snoozed server
                    await self._start_executor_server(pair_strat)

                # else: deleted not loaded - nothing to do , DB will remove entry

    async def update_strat_collection_pre(self, stored_strat_collection_obj: StratCollection,
                                          updated_strat_collection_obj: StratCollection):
        if not self.service_ready:
            # raise service unavailable 5mobile_book3 exception, let the caller retry
            err_str_ = "update_strat_collection_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=5mobile_book3, detail=err_str_)
        # handling unloading pair_strats
        await self.unload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        # handling reloading pair_strat
        await self.reload_pair_strats(stored_strat_collection_obj, updated_strat_collection_obj)

        return updated_strat_collection_obj

    async def get_pair_strat_from_symbol_side_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                        sec_id: str, side: Side):
        matched_strat = await get_single_exact_match_strat_from_symbol_n_side(sec_id, side)
        if matched_strat is None:
            # checking if no match found or if something unexpected happened
            match_level_1_pair_strats, match_level_2_pair_strats = \
                await get_ongoing_strats_from_symbol_n_side(sec_id, side)
            if len(match_level_1_pair_strats) == mobile_book and len(match_level_2_pair_strats) == mobile_book:
                return []
            else:
                err_str_ = (f"Something unexpected happened while fetching ongoing strats, please check logs for more "
                            f"details, symbol_side_snapshot: {get_symbol_side_key([(sec_id, side)])} "
                            f"{len(match_level_1_pair_strats) = };  ;;;"
                            f"{len(match_level_2_pair_strats) = };  ;;;"
                            f"{match_level_1_pair_strats = };  "
                            f"{match_level_2_pair_strats = } ")
                logging.error(err_str_)
                raise HTTPException(status_code=5mobile_bookmobile_book, detail=err_str_)
        return [matched_strat]

    async def get_all_pair_strats_from_symbol_side_query_pre(self, pair_strat_class_type: Type[PairStrat],
                                                             sec_id: str, side: Side):
        return await (StratManagerServiceRoutesCallbackBaseNativeOverride.
                      underlying_read_pair_strat_http(get_all_pair_strat_from_symbol_n_side(sec_id, side)))

    async def create_admin_control_pre(self, admin_control_obj: AdminControl):
        match admin_control_obj.command_type:
            case CommandType.CLEAR_STRAT:
                pair_strat_list: List[PairStrat] = (
                    await StratManagerServiceRoutesCallbackBaseNativeOverride.underlying_read_pair_strat_http())
                for pair_strat_ in pair_strat_list:
                    leg1_lock_file_path, leg2_lock_file_path = (
                        self.get_lock_file_names_from_pair_strat(pair_strat_))
                    if os.path.exists(leg1_lock_file_path):
                        os.remove(leg1_lock_file_path)
                    if os.path.exists(leg2_lock_file_path):
                        os.remove(leg2_lock_file_path)
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.addressbook.ProjectGroup.phone_book.generated.FastApi.strat_manager_service_beanie_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_admin_control_pre failed. unrecognized command_type: {other_}")

    async def filtered_notify_pair_strat_update_query_ws_pre(self):
        return filter_ws_pair_strat

    async def update_system_control_pre(self, stored_system_control_obj: SystemControl,
                                        updated_system_control_obj: SystemControl):
        if not stored_system_control_obj.kill_switch and updated_system_control_obj.kill_switch:
            if not StratManagerServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate:
                res = await self.trading_link.trigger_kill_switch()
                if not res:
                    err_str_ = "trading_link.trigger_kill_switch failed"
                    logging.critical(err_str_)
                    raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)
                # else not required: if res is fine make db update
            # else not required: avoid trading_link.trigger_kill_switch if RecoveredKillSwitchUpdate is True updated
            # from init check
        elif stored_system_control_obj.kill_switch and not updated_system_control_obj.kill_switch:
            res = await self.trading_link.revoke_kill_switch_n_resume_trading()
            if not res:
                err_str_ = "trading_link.revoke_kill_switch_n_resume_trading failed"
                logging.critical(err_str_)
                raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)
        # else not required: other case doesn't need trading link call

    async def log_simulator_reload_config_query_pre(
            self, log_simulator_reload_config_class_type: Type[LogSimulatorReloadConfig]):
        self.trading_link.reload_portfolio_configs()
        return []

    async def partial_update_system_control_pre(self, stored_system_control_obj: SystemControl,
                                                updated_system_control_obj_json: Dict):
        kill_switch_update = updated_system_control_obj_json.get("kill_switch")
        if kill_switch_update is not None:
            if not stored_system_control_obj.kill_switch and kill_switch_update:
                if not StratManagerServiceRoutesCallbackBaseNativeOverride.RecoveredKillSwitchUpdate:
                    res = await self.trading_link.trigger_kill_switch()
                    if not res:
                        err_str_ = "trading_link.trigger_kill_switch failed"
                        logging.critical(err_str_)
                        raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)
                    # else not required: if res is fine make db update
                # else not required: avoid trading_link.trigger_kill_switch if RecoveredKillSwitchUpdate is True
                # updated from init check
            elif stored_system_control_obj.kill_switch and not kill_switch_update:
                res = await self.trading_link.revoke_kill_switch_n_resume_trading()
                if not res:
                    err_str_ = "trading_link.revoke_kill_switch_n_resume_trading failed"
                    logging.critical(err_str_)
                    raise HTTPException(detail=err_str_, status_code=5mobile_bookmobile_book)
            # else not required: other case doesn't need trading link call
        return updated_system_control_obj_json


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
