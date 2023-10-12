# standard imports
import asyncio
import json
import logging
import os
from pathlib import PurePath
import threading
import time
import copy
import shutil
import sys
import stat
import datetime
import subprocess

# project imports
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_routes_callback import (
    StratExecutorServiceRoutesCallback)
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import (
    get_order_journal_log_key, get_symbol_side_key, get_order_snapshot_log_key,
    get_symbol_side_snapshot_log_key, all_service_up_check, host,
    strat_manager_service_http_client, get_consumable_participation_qty,
    get_strat_brief_log_key, get_fills_journal_log_key, get_new_strat_limits, get_new_strat_status,
    EXECUTOR_PROJECT_DATA_DIR, is_ongoing_strat, log_analyzer_service_http_client, main_config_yaml_dict,
    EXECUTOR_PROJECT_SCRIPTS_DIR)
from FluxPythonUtils.scripts.utility_functions import (
    avg_of_new_val_sum_to_avg, find_free_port, except_n_log_alert)
from Flux.CodeGenProjects.pair_strat_engine.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.pair_strat_engine.app.service_state import ServiceState
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import (
    PortfolioStatusOptional, PortfolioLimitsBaseModel, StratLeg, FxSymbolOverviewBaseModel)
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import (
    create_md_shell_script, MDShellEnvData)
from Flux.CodeGenProjects.strat_executor.app.strat_executor import StratExecutor, TradingDataManager
from Flux.CodeGenProjects.strat_executor.app.trade_simulator import TradeSimulator, TradingLinkBase
from Flux.CodeGenProjects.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import StratAlertBaseModel
from Flux.CodeGenProjects.strat_executor.app.strat_cache import StratCache
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_key_handler import (
    StratManagerServiceKeyHandler)
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import (
    StratExecutorServiceHttpClient)

def get_pair_strat_id_from_cmd_argv():
    if len(sys.argv) > 2:
        pair_strat_id = sys.argv[1]
        try:
            return parse_to_int(pair_strat_id)
        except ValueError as e:
            err_str_ = (f"Provided cmd argument pair_strat_id is not valid type, "
                        f"must be numeric, exception: {e}")
            logging.error(err_str_)
            raise Exception(err_str_)
    else:
        err_str_ = ("Can't find pair_strat_id as cmd argument, "
                    "Usage: python launch_beanie_fastapi.py <PAIR_STRAT_ID>, "
                    f"current args: {sys.argv}")
        logging.error(err_str_)
        raise Exception(err_str_)


class StratExecutorServiceRoutesCallbackBaseNativeOverride(StratExecutorServiceRoutesCallback):
    def __init__(self):
        super().__init__()
        self.pair_strat_id = get_pair_strat_id_from_cmd_argv()
        # since this init is called before db_init
        os.environ["DB_NAME"] = f"strat_executor_{self.pair_strat_id}"
        datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
        os.environ["LOG_FILE_NAME"] = f"strat_executor_{self.pair_strat_id}_logs_{datetime_str}.log"
        self.strat_leg_1: StratLeg | None = None    # will be set by once all_service_up test passes
        self.strat_leg_2: StratLeg | None = None    # will be set by once all_service_up test passes
        self.all_services_up: bool = False
        self.service_ready: bool = False
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.static_data: SecurityRecordManager | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {self.usd_fx_symbol: None}
        self.usd_fx = None
        self.port: int | None = None    # will be set by
        self.web_client = None

        self.min_refresh_interval: int = parse_to_int(main_config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.strat_leg_1 = None
        self.strat_leg_2 = None
        self.trading_data_manager: TradingDataManager | None = None
        self.simulate_config_yaml_file_path = (
                EXECUTOR_PROJECT_DATA_DIR / f"executor_{self.pair_strat_id}_simulate_config.yaml")

    def get_generic_read_route(self):
        return None

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat for now - may extend to accept symbol and send revised px according to
        underlying trading currency
        """
        return px / self.usd_fx

    def get_local_px_or_notional(self, px_or_notional: float, system_symbol: str):
        return px_or_notional * self.usd_fx

    ##################
    # Start-Up Methods
    ##################

    def _apply_checks_n_log_error(self, strat_status_obj: StratStatus, is_create: bool = False) -> List[Alert]:
        """
        implement any strat management checks here (create / update strats)
        """
        return []

    def static_data_periodic_refresh(self):
        pass

    def get_pair_strat_loaded_strat_cache(self, pair_strat):
        key_leg_1, key_leg_2 = StratManagerServiceKeyHandler.get_key_from_pair_strat(pair_strat)
        strat_cache: StratCache = StratCache.guaranteed_get_by_key(key_leg_1, key_leg_2)
        with strat_cache.re_ent_lock:
            strat_cache.set_pair_strat(pair_strat)
        return strat_cache

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up, then create portfolio limits if required
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_trigger_residual_check_query_http, underlying_get_symbol_overview_from_symbol_query_http)

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        symbol_overview_for_symbol_exists: bool = False
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"strat_executor_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                # static data and md service are considered essential
                if (self.all_services_up and static_data_service_state.ready and self.usd_fx is not None and
                        symbol_overview_for_symbol_exists and self.trading_data_manager is not None):
                    if not self.service_ready:
                        self.service_ready = True
                        logging.debug("Service Marked Ready")
                        # creating required models for this strat
                        self._check_n_create_related_models_for_strat()
                if not self.all_services_up:
                    try:
                        if all_service_up_check(self.web_client, ignore_error=(service_up_no_error_retry_count > 0)):
                            # starting trading_data_manager and strat_executor
                            pair_strat = strat_manager_service_http_client.get_pair_strat_client(self.pair_strat_id)
                            self.strat_leg_1 = pair_strat.pair_strat_params.strat_leg1
                            self.strat_leg_2 = pair_strat.pair_strat_params.strat_leg2
                            strat_cache: StratCache = self.get_pair_strat_loaded_strat_cache(pair_strat)

                            # creating config file for this server run if not exists
                            code_gen_projects_dir = PurePath(__file__).parent.parent.parent
                            temp_config_file_path = code_gen_projects_dir / "template_yaml_configs" / "server_config.yaml"
                            dest_config_file_path = self.simulate_config_yaml_file_path
                            shutil.copy(temp_config_file_path, dest_config_file_path)

                            # setting simulate_config_file_name
                            TradingLinkBase.simulate_config_yaml_path = self.simulate_config_yaml_file_path
                            TradingLinkBase.executor_port = self.port
                            TradingLinkBase.reload_executor_configs()

                            # Setting asyncio_loop for StratExecutor
                            StratExecutor.asyncio_loop = self.asyncio_loop
                            self.trading_data_manager = TradingDataManager(StratExecutor.executor_trigger,
                                                                           strat_cache)
                            logging.debug(f"Created trading_data_manager for pair_strat: {pair_strat}")

                            # setting partial_run to True and assigning port to pair_strat
                            if not pair_strat.is_partially_running:
                                pair_strat.is_partially_running = True
                                pair_strat.port = self.port
                                strat_manager_service_http_client.patch_pair_strat_client(
                                    jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                            # else not required: not updating if already is_executor_running
                            logging.debug("Marked pair_strat.is_partially_running True")

                            # creating and running so_shell script
                            self.create_n_run_so_shell_script(pair_strat)

                            self.all_services_up = True
                            logging.debug("Marked all_services_up True")
                            should_sleep = False
                        else:
                            should_sleep = True
                            service_up_no_error_retry_count -= 1
                    except Exception as e:
                        logging.error("unexpected: all_service_up_check threw exception, "
                                      f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                      f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
                    try:
                        # Gets all open orders, updates residuals and raises pause to strat if req
                        run_coro = underlying_trigger_residual_check_query_http(["OE_ACKED", "OE_UNACK"])
                        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                        # block for task to finish
                        try:
                            future.result()
                        except Exception as e:
                            logging.exception(f"underlying_trigger_residual_check_query_http "
                                              f"failed with exception: {e}")

                    except Exception as e:
                        logging.error("periodic open order check failed, periodic order state checks will "
                                      "not be honored and retried in next periodic cycle"
                                      f";;;exception: {e}", exc_info=True)

                    if self.usd_fx is None:
                        if not self.update_fx_symbol_overview_dict_from_http():
                            logging.error(f"Can't find any symbol_overview with symbol {self.usd_fx_symbol} "
                                          f"in pair_strat_engine service, retrying in next periodic cycle",
                                          exc_info=True)

                    if not symbol_overview_for_symbol_exists:
                        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]
                        for symbol in symbols_list:
                            run_coro = underlying_get_symbol_overview_from_symbol_query_http(symbol)
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                            # block for task to finish
                            try:
                                symbol_overview_list = future.result()
                                if symbol_overview_list:
                                    symbol_overview_for_symbol_exists = True
                                    logging.debug("Marked symbol_overview_for_symbol_exists True")
                                else:
                                    symbol_overview_for_symbol_exists = False
                                    break
                            except Exception as e:
                                logging.exception(f"underlying_get_symbol_overview_from_symbol_query_http "
                                                  f"failed with exception: {e}")

                    # service loop: manage all sub-services within their private try-catch to allow high level
                    # service to remain partially operational even if some sub-service is not available for any reason
                    if not static_data_service_state.ready:
                        try:
                            self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                            if self.static_data is not None:
                                static_data_service_state.ready = True
                                logging.debug("Marked static_data_service_state.ready True")
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
            else:
                should_sleep = True

    def app_launch_pre(self):
        self.port = find_free_port()
        self.web_client = StratExecutorServiceHttpClient.set_or_get_if_instance_exists(host, self.port)

        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")
        # making pair_strat is_executor_running field to False
        try:
            pair_strat = strat_manager_service_http_client.get_pair_strat_client(self.pair_strat_id)
            pair_strat.is_executor_running = False
            pair_strat.is_partially_running = False
            strat_manager_service_http_client.patch_pair_strat_client(
                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
        except Exception as e:
            if ('{"detail":"Id not Found: PairStrat '+f'{self.pair_strat_id}'+'"}') in str(e):
                err_str_ = ("error occurred since pair_strat object got deleted, therefore can't update "
                            "is_running_state, symbol_side_key: "
                            f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
                logging.debug(err_str_)
            else:
                logging.error(f"Some error occurred while updating is_running state of pair_strat of id: "
                              f"{self.pair_strat_id} while shutting executor server, symbol_side_key: "
                              f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
        finally:
            # removing md scripts
            try:
                so_file_path = EXECUTOR_PROJECT_SCRIPTS_DIR / f"ps_id_{self.pair_strat_id}_so.sh"
                if os.path.exists(so_file_path):
                    os.remove(so_file_path)
            except Exception as e:
                err_str_ = (f"Something went wrong while deleting so shell script, "
                            f"exception: {e}")
                logging.error(err_str_)

    @staticmethod
    def create_n_run_so_shell_script(pair_strat):
        # creating run_symbol_overview.sh file
        run_symbol_overview_file_path = EXECUTOR_PROJECT_SCRIPTS_DIR / f"ps_id_{pair_strat.id}_so.sh"

        subscription_data = \
            [
                (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                 pair_strat.pair_strat_params.strat_leg1.sec.sec_type.name),
                (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                 pair_strat.pair_strat_params.strat_leg2.sec.sec_type.name)
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = pair_strat.pair_strat_params.strat_leg1.exch_id  # ideally get from pair_strat

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_strat.host,
                           port=pair_strat.port, db_name=db_name, exch_code=exch_code,
                           project_name="strat_executor"))

        create_md_shell_script(md_shell_env_data, run_symbol_overview_file_path, "SO")
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_symbol_overview_file_path}"])

    def update_fx_symbol_overview_dict_from_http(self) -> bool:
        fx_symbol_overviews: List[FxSymbolOverviewBaseModel] = \
            strat_manager_service_http_client.get_all_fx_symbol_overview_client()
        if fx_symbol_overviews:
            fx_symbol_overview_: FxSymbolOverviewBaseModel
            for fx_symbol_overview_ in fx_symbol_overviews:
                if fx_symbol_overview_.symbol in self.fx_symbol_overview_dict:
                    # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
                    self.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
                    self.usd_fx = fx_symbol_overview_.closing_px
                    logging.debug(f"Updated self.usd_fx to {self.usd_fx}")
                    return True
        # all else - return False
        return False

    def _check_n_create_default_strat_limits(self):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_read_strat_limits_http, underlying_create_strat_limits_http)

        run_coro = underlying_read_strat_limits_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            existing_strat_limits_list: List[StratLimits] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_strat_limits_http failed, ignoring check or create strat_limits, "
                              f"exception: {e}")
            return

        if len(existing_strat_limits_list) > 1:
            err_str_ = (f"One Strat Must only contain one strat_limits obj, found: {len(existing_strat_limits_list)}, "
                        f";;;found strat_limits_list: {existing_strat_limits_list}")
            logging.error(err_str_)
            return None

        if len(existing_strat_limits_list) == 0:
            eligible_brokers: Broker | None = None
            try:
                dismiss_filter_portfolio_limit_broker_obj_list = (
                    strat_manager_service_http_client.get_dismiss_filter_portfolio_limit_brokers_query_client(
                        self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id))
                if dismiss_filter_portfolio_limit_broker_obj_list:
                    eligible_brokers = dismiss_filter_portfolio_limit_broker_obj_list[0].brokers
                else:
                    err_str_ = ("Http Query get_dismiss_filter_portfolio_limit_brokers_query returned empty list, "
                                "expected dismiss_filter_portfolio_limit_broker_obj_list obj with brokers list")
                    logging.error(err_str_)
            except Exception as e:
                err_str_ = (f"Exception occurred while fetching filtered broker from portfolio_status, "
                            f"creating strat_limits with no eligible_broker: exception: {e}")
                logging.error(err_str_)

            strat_limits = get_new_strat_limits(eligible_brokers)
            strat_limits.id = self.pair_strat_id     # syncing id with pair_strat which triggered this server

            run_coro = underlying_create_strat_limits_http(strat_limits)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                created_strat_limits: StratLimits = future.result()
            except Exception as e:
                logging.exception(f"underlying_create_strat_limits_http failed, ignoring create strat_limits, "
                                  f"exception: {e}")
                return

            logging.debug(f"Created strat_limits: {strat_limits}")
            return created_strat_limits
        else:
            return existing_strat_limits_list[0]

    async def _remove_strat_limits(self) -> bool:
        strat_limits = await self._get_strat_limits()

        if strat_limits is not None:
            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
                underlying_delete_strat_limits_http)
            await underlying_delete_strat_limits_http(strat_limits.id)
            return True
        else:
            err_str_ = ("Can't find any strat_limits to delete, ignoring delete call, "
                        f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
            return False

    def _check_n_create_or_update_strat_status(self, strat_limits: StratLimits):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_read_strat_status_http, underlying_create_strat_status_http,
            underlying_update_strat_status_http)

        run_coro = underlying_read_strat_status_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            existing_strat_status_list: List[StratStatus] = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_strat_status_http failed: ignoring check or create strat_status, "
                              f"exception: {e}")
            return

        if len(existing_strat_status_list) > 1:
            err_str_ = (
                f"One Strat Must only contain one strat_status obj, found: {len(existing_strat_status_list)}, ;;;"
                f"found strat_status_list: {existing_strat_status_list}")
            logging.error(err_str_)
            return None

        if len(existing_strat_status_list) == 0:
            strat_status = get_new_strat_status(strat_limits)
            strat_status.id = self.pair_strat_id     # syncing id with pair_strat which triggered this server

            run_coro = underlying_create_strat_status_http(strat_status)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

            # block for task to finish
            try:
                created_strat_status: StratStatus = future.result()
            except Exception as e:
                logging.exception(f"underlying_create_strat_status_http failed: ignoring create strat_status, "
                                  f"exception: {e}")
                return

            logging.debug(f"Created Strat_status: {strat_status}")
            return created_strat_status
        else:
            existing_strat_status: StratStatus = existing_strat_status_list[0]
            if existing_strat_status.strat_state == StratState.StratState_SNOOZED:
                strat_status = get_new_strat_status(strat_limits)
                strat_status.id = self.pair_strat_id  # syncing id with pair_strat which triggered this server

                run_coro = underlying_update_strat_status_http(strat_status)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                # block for task to finish
                try:
                    updated_strat_status: StratStatus = future.result()
                except Exception as e:
                    logging.exception(f"underlying_update_strat_status_http failed: ignoring update strat_status, "
                                      f"exception: {e}")
                    return

                logging.debug(f"Updated StratStatus to Snoozed State: {strat_status}")
                return updated_strat_status
            return existing_strat_status

    async def _snooze_strat_status(self) -> StratStatus | None:
        strat_status = await self._get_strat_status()
        if strat_status:
            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
                underlying_update_strat_status_http)
            updated_strat_status = StratStatus(id=strat_status.id,
                                               strat_state=StratState.StratState_SNOOZED)
            await underlying_update_strat_status_http(updated_strat_status)
            return strat_status
        else:
            err_str_ = ("Can't find any strat_status to update state to snoozed, ignoring snooze update, "
                        f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
            return None

    async def _create_strat_brief_for_ready_to_active_pair_strat(self, strat_limits: StratLimits):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_strat_brief_from_symbol
        symbol = self.strat_leg_1.sec.sec_id
        side = self.strat_leg_1.side
        # since strat_brief has both symbols as pair_strat has, so any symbol will give same strat_brief
        strat_brief_objs_list = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol))

        if len(strat_brief_objs_list) > 1:
            err_str_ = f"strat_brief must be only one per symbol received {strat_brief_objs_list} symbol_side_key: " \
                       f"{get_symbol_side_key([(symbol, side)])}"
            logging.error(err_str_)
            return
        elif len(strat_brief_objs_list) == 1:
            err_str_ = f"strat_brief must not exist for this symbol while strat is converting from ready to active, " \
                       f"pair_strat_key: {get_symbol_side_key([(symbol, side)])};;; " \
                       f"strat_brief_list: {strat_brief_objs_list}"
            logging.error(err_str_)
            return
        else:
            # If no strat_brief exists for this symbol
            consumable_open_orders = strat_limits.max_open_orders_per_side
            consumable_notional = strat_limits.max_cb_notional
            consumable_open_notional = strat_limits.max_open_cb_notional
            security_float = self.static_data.get_security_float_from_ticker(symbol)
            if security_float is not None:
                consumable_concentration = \
                    (security_float / 100) * strat_limits.max_concentration
            else:
                consumable_concentration = 0
            participation_period_order_qty_sum = 0
            consumable_cxl_qty = 0
            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                underlying_get_executor_check_snapshot_query_http
            applicable_period_second = strat_limits.market_trade_volume_participation.applicable_period_seconds
            executor_check_snapshot_list = \
                await underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                        applicable_period_second)
            if len(executor_check_snapshot_list) == 1:
                indicative_consumable_participation_qty = \
                    get_consumable_participation_qty(
                        executor_check_snapshot_list,
                        strat_limits.market_trade_volume_participation.max_participation_rate)
            else:
                logging.error("Received unexpected length of executor_check_snapshot_list from query "
                              f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_executor_check_snapshot_query pre implementation")
                indicative_consumable_participation_qty = 0
            residual_qty = 0
            indicative_consumable_residual = strat_limits.residual_restriction.max_residual
            all_bkr_cxlled_qty = 0
            open_notional = 0
            open_qty = 0

            sec2_pair_side_trading_brief_obj: PairSideTradingBrief | None = None
            sec1_pair_side_trading_brief_obj = \
                PairSideTradingBrief(security=self.strat_leg_1.sec,
                                     side=self.strat_leg_1.side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_orders=consumable_open_orders,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_order_qty_sum=participation_period_order_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)
            sec2_pair_side_trading_brief_obj = \
                PairSideTradingBrief(security=self.strat_leg_2.sec,
                                     side=self.strat_leg_2.side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_orders=consumable_open_orders,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_order_qty_sum=participation_period_order_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)

            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                underlying_create_strat_brief_http
            buy_side_trading_brief = sec1_pair_side_trading_brief_obj \
                if sec1_pair_side_trading_brief_obj.side == Side.BUY else sec2_pair_side_trading_brief_obj
            sell_side_trading_brief = sec1_pair_side_trading_brief_obj \
                if sec1_pair_side_trading_brief_obj.side == Side.SELL else sec2_pair_side_trading_brief_obj
            strat_brief_obj: StratBrief = StratBrief(_id=StratBrief.next_id(),
                                                     pair_buy_side_trading_brief=buy_side_trading_brief,
                                                     pair_sell_side_trading_brief=sell_side_trading_brief,
                                                     consumable_nett_filled_notional=0.0)
            created_underlying_strat_brief = await underlying_create_strat_brief_http(strat_brief_obj)
            logging.debug(f"Created strat brief in pre call of pair_strat of "
                          f"key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                          f"strat_limits: {strat_limits}, "
                          f"created strat_brief: {created_underlying_strat_brief}")

    async def _create_symbol_snapshot_for_ready_to_active_pair_strat(self):
        # before running this server
        pair_symbol_side_list = [
            (self.strat_leg_1.sec, self.strat_leg_1.side),
            (self.strat_leg_2.sec, self.strat_leg_2.side)
        ]

        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        for security, side in pair_symbol_side_list:
            if security is not None and side is not None:
                symbol_side_snapshots = await underlying_read_symbol_side_snapshot_http(
                    get_symbol_side_snapshot_from_symbol_side(security.sec_id, side), self.get_generic_read_route())

                if symbol_side_snapshots is not None:
                    if len(symbol_side_snapshots) == 1:
                        err_str_ = f"SymbolSideSnapshot must not be present for this symbol and side when strat is " \
                                   f"converted converted from ready to active, symbol_side_key: " \
                                   f"{get_symbol_side_key([(security.sec_id, side)])}, " \
                                   f"symbol_side_snapshot_list {symbol_side_snapshots}"
                        logging.error(err_str_)
                        return
                    elif len(symbol_side_snapshots) > 1:
                        err_str_ = f"SymbolSideSnapshot must be one per symbol and side, symbol_side_key: " \
                                   f"{get_symbol_side_key([(security.sec_id, side)])}, symbol_side_snapshot_list: " \
                                   f"{symbol_side_snapshots}"
                        logging.error(err_str_)
                        return
                    # else not required: good if no symbol_side_snapshot exists already (we create new)

                    from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes \
                        import underlying_create_symbol_side_snapshot_http
                    symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(),
                                                                  security=security,
                                                                  side=side, avg_px=0, total_qty=0,
                                                                  total_filled_qty=0, avg_fill_px=0.0,
                                                                  total_fill_notional=0.0, last_update_fill_qty=0,
                                                                  last_update_fill_px=0, total_cxled_qty=0,
                                                                  avg_cxled_px=0,
                                                                  total_cxled_notional=0,
                                                                  last_update_date_time=DateTime.utcnow(),
                                                                  order_count=0)
                    created_symbol_side_snapshot: SymbolSideSnapshot = \
                        await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
                    logging.debug(f"Created SymbolSideSnapshot with key: "
                                  f"{get_symbol_side_snapshot_log_key(created_symbol_side_snapshot)};;;"
                                  f"new SymbolSideSnapshot: {created_symbol_side_snapshot}")
                else:
                    logging.error("unexpected: None symbol_side_snapshots received - this is likely a bug, "
                                  f"symbol_side_key: {get_symbol_side_key([(security.sec_id, side)])}")
            else:
                # Ignore symbol side snapshot creation and logging if any of security and side is None
                logging.debug(f"Received either security or side as None from config of this start_executor for port "
                              f"{self.port}, likely populated by pair_strat_engine before launching this server, "
                              f"security: {security}, side: {side}")

    async def _force_publish_symbol_overview_for_ready_to_active_strat(self) -> None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_partial_update_symbol_overview_http, underlying_get_symbol_overview_from_symbol_query_http

        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]

        for symbol in symbols_list:
            symbol_overview_obj_list = await underlying_get_symbol_overview_from_symbol_query_http(symbol)
            if len(symbol_overview_obj_list) != 0:
                if len(symbol_overview_obj_list) == 1:
                    updated_symbol_overview = FxSymbolOverviewBaseModel(_id=symbol_overview_obj_list[0].id,
                                                                        force_publish=True)
                    await underlying_partial_update_symbol_overview_http(
                        jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True))
                else:
                    err_str_ = (f"symbol_overview must be one per symbol, symbol_side_key: "
                                f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                                f"symbol_overview_list: {symbol_overview_obj_list} ")
                    logging.error(err_str_)
            # else not required: this might not happen unless manual deletion is done for these symbols
            # from symbol_overview, since service_ready flag is only enabled unless symbol_overviews with
            # these symbols are found

    def _check_n_create_strat_alert(self, strat_id: int):
        try:
            strat_alert = log_analyzer_service_http_client.get_strat_alert_client(strat_id)
        except Exception as e:
            if "Id not Found: " in str(e):
                logging.info(f"get_strat_alert_client can't find strat_alert with id: {strat_id}, "
                              f"creating one, caught exception: {e}")

                # creating strat_alert for this strat in log_analyzer server
                strat_alert: StratAlertBaseModel = StratAlertBaseModel(_id=strat_id, alerts=[], alert_update_seq_num=0)
                log_analyzer_service_http_client.create_strat_alert_client(strat_alert)

            else:
                err_str_ = (f"Some Error Occurred while creating strat_alert for id: {strat_id}, "
                            f"exception: {e}")
                logging.error(err_str_)
                raise Exception(err_str_)

    def _check_n_create_related_models_for_strat(self) -> None:
        strat_limits = self._check_n_create_default_strat_limits()
        if strat_limits is not None:
            strat_status = self._check_n_create_or_update_strat_status(strat_limits)
            self._check_n_create_strat_alert(self.pair_strat_id)

            if strat_status is not None:
                pair_strat = strat_manager_service_http_client.get_pair_strat_client(self.pair_strat_id)
                if not pair_strat.is_executor_running:
                    pair_strat.is_executor_running = True
                    strat_manager_service_http_client.patch_pair_strat_client(
                        jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                    logging.debug(f"pair strat's is_executor_running set to True, pair_strat: {pair_strat}")
                # else not required: not updating if already is_executor_running
            # else not required: avoiding signalling executor completely running
        # else not required: avoiding strat_status check, strat_alert create and signalling executor completely running

    async def load_strat_cache(self):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_read_strat_limits_by_id_http, underlying_read_symbol_overview_http,
            underlying_read_top_of_book_http, underlying_read_strat_brief_http)

        # updating strat_limits
        strat_limits = await underlying_read_strat_limits_by_id_http(self.pair_strat_id)
        self.trading_data_manager.handle_strat_limits_get_all_ws(strat_limits)

        # updating symbol_overviews
        symbol_overview_list: List[SymbolOverview] = await underlying_read_symbol_overview_http()
        for symbol_overview in symbol_overview_list:
            self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview)

        # updating top of book
        tobs: List[TopOfBook] = await underlying_read_top_of_book_http()
        for tob in tobs:
            self.trading_data_manager.handle_top_of_book_get_all_ws(tob)

        # updating fx_symbol_overview
        fx_symbol_overview_list = strat_manager_service_http_client.get_all_fx_symbol_overview_client()
        for fx_symbol_overview in fx_symbol_overview_list:
            self.trading_data_manager.handle_fx_symbol_overview_get_all_ws(fx_symbol_overview)

        # updating strat_brief
        strat_brief_list: List[StratBrief] = await underlying_read_strat_brief_http()
        for strat_brief in strat_brief_list:
            self.trading_data_manager.handle_strat_brief_get_all_ws(strat_brief)

        # updating portfolio_limits
        portfolio_limits: PortfolioLimitsBaseModel = (
            strat_manager_service_http_client.get_portfolio_limits_client(1))
        self.trading_data_manager.handle_portfolio_limits_get_all_ws(portfolio_limits)

    async def _create_related_models_for_active_strat(self, stored_strat_status_obj: StratStatus,
                                                      updated_strat_status_obj: StratStatus) -> None:
        if stored_strat_status_obj.strat_state == StratState.StratState_READY:
            if updated_strat_status_obj.strat_state == StratState.StratState_ACTIVE:
                strat_limits = await self._get_strat_limits()
                # creating strat_brief for both leg securities
                await self._create_strat_brief_for_ready_to_active_pair_strat(strat_limits)
                # creating symbol_side_snapshot for both leg securities if not already exists
                await self._create_symbol_snapshot_for_ready_to_active_pair_strat()
                # changing symbol_overview force_publish to True if exists
                await self._force_publish_symbol_overview_for_ready_to_active_strat()

                # updating strat_cache
                await self.load_strat_cache()

            # else not required: if strat status is not active then avoiding creations
        # else not required: If stored strat is already active then related models would have been already created

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

    ############################
    # Limit Check update methods
    ############################

    def _pause_strat_if_limits_breached(self, updated_strat_status: StratStatus, strat_limits: StratLimits,
                                        strat_brief_: StratBrief,
                                        symbol_side_snapshot_: SymbolSideSnapshot):

        if (residual_notional := updated_strat_status.residual.residual_notional) is not None:
            if residual_notional > (max_residual := strat_limits.residual_restriction.max_residual):
                alert_brief: str = f"residual notional: {residual_notional} > max residual: {max_residual}"
                alert_details: str = f"updated_strat_status: {updated_strat_status}, strat_limits: {strat_limits}"
                logging.error(f"{alert_brief}, symbol_side_snapshot_key: "
                              f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                updated_strat_status.strat_state = StratState.StratState_PAUSED
            # else not required: if residual is in control then nothing to do

        if symbol_side_snapshot_.order_count > strat_limits.cancel_rate.waived_min_orders:
            if symbol_side_snapshot_.side == Side.BUY:
                if strat_brief_.pair_buy_side_trading_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_buy_side_trading_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} " \
                                        f"for symbol {strat_brief_.pair_buy_side_trading_brief.security.sec_id} and " \
                                        f"side {Side.BUY}"
                        alert_brief: str = err_str_
                        alert_details: str = (f"updated_strat_status: {updated_strat_status}, "
                                              f"strat_limits: {strat_limits}, "
                                              f"symbol_side_snapshot: {symbol_side_snapshot_}")
                        logging.error(f"{alert_brief}, symbol_side_snapshot_key: "
                                      f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                        updated_strat_status.strat_state = StratState.StratState_PAUSED
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single buy order then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if buy side all_bkr_cxlled_qty is 0
            else:
                if strat_brief_.pair_sell_side_trading_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_sell_side_trading_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} " \
                                        f"for symbol {strat_brief_.pair_sell_side_trading_brief.security.sec_id} and " \
                                        f"side {Side.SELL}"
                        alert_brief: str = err_str_
                        alert_details: str = (f"updated_strat_status: {updated_strat_status}, "
                                              f"strat_limits: {strat_limits}, "
                                              f"symbol_side_snapshot: {symbol_side_snapshot_}")
                        updated_strat_status.strat_state = StratState.StratState_PAUSED
                        logging.error(f"{alert_brief}, symbol_side_snapshot_key: "
                                      f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single sell order then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if sell side all_bkr_cxlled_qty is 0
            # else not required: if order count is less than waived_min_orders

    ####################################
    # Get specific Data handling Methods
    ####################################

    async def _get_symbol_side_snapshot_from_symbol_side(self, symbol: str,
                                                         side: Side) -> List[SymbolSideSnapshot] | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_side_snapshot_from_symbol_side

        symbol_side_snapshot_objs = \
            await underlying_read_symbol_side_snapshot_http(get_symbol_side_snapshot_from_symbol_side(symbol, side),
                                                            self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) > 1:
            err_str_ = f"Found multiple objects of symbol_side_snapshot for key: " \
                       f"{get_symbol_side_key([(symbol, side)])}"
            logging.error(err_str_)
            return None
        else:
            return symbol_side_snapshot_objs

    async def _get_strat_limits(self) -> StratLimits | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_read_strat_limits_http)
        strat_limits_list = await underlying_read_strat_limits_http()

        strat_limits: StratLimits | None = None
        if len(strat_limits_list) == 1:
            strat_limits = strat_limits_list[0]
        elif len(strat_limits_list) == 0:
            logging.error(f"Can't find any StartLimits obj: Current strat must have exactly 1 strat_limits obj, "
                          f"likely bug in server start_up handling")
        else:
            logging.error(f"StratLimits obj must be one per server, found length: {len(strat_limits_list)};;; "
                          f"strat_limits_list: {strat_limits_list}")
        return strat_limits

    async def _get_strat_status(self) -> StratStatus | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_read_strat_status_http)
        strat_status_list = await underlying_read_strat_status_http()

        strat_status: StratStatus | None = None
        if len(strat_status_list) == 1:
            strat_status = strat_status_list[0]
        elif len(strat_status_list) == 0:
            logging.error(f"Can't find any StratStatus obj: Current strat must have exactly 1 strat_status obj, "
                          f"likely bug in server start_up handling")
        else:
            logging.error(f"StratStatus obj must be one per server, found length: {len(strat_status_list)};;; "
                          f"strat_status_list: {strat_status_list}")
        return strat_status

    async def _get_top_of_book_from_symbol(self, symbol: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_get_top_of_book_from_symbol_query_http)
        top_of_book_list: List[TopOfBook] = await underlying_get_top_of_book_from_symbol_query_http(symbol)
        if len(top_of_book_list) != 1:
            err_str_ = f"TopOfBook should be one per symbol received {len(top_of_book_list)} for symbol {symbol} " \
                       f"- {top_of_book_list}"
            logging.error(err_str_)
            return None
        else:
            return top_of_book_list[0]

    async def _get_order_snapshot_from_order_journal_order_id(self,
                                                              order_journal_obj: OrderJournal) -> OrderSnapshot | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_snapshot_order_id_filter_json

        order_id = order_journal_obj.order.order_id
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(order_id),
                                                      self.get_generic_read_route())
        if len(order_snapshot_objs) == 1:
            return order_snapshot_objs[0]
        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order_id {order_id} to be updated for " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)};;; " \
                       f"order_journal: {order_journal_obj}"
            logging.error(err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj per order_id, " \
                       f"returned {order_snapshot_objs} to be updated for order_journal_key " \
                       f"{get_order_journal_log_key(order_journal_obj)};;; order_journal: {order_journal_obj}"
            logging.error(err_str_)

    async def __get_residual_obj(self, side: Side, strat_brief: StratBrief) -> Residual | None:
        if side == Side.BUY:
            residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            top_of_book_obj = \
                await self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                await self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
        else:
            residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            top_of_book_obj = \
                await self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                await self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)

        if top_of_book_obj is None or other_leg_top_of_book is None:
            logging.error(f"Received both leg's TOBs as {top_of_book_obj} and {other_leg_top_of_book}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            return None

        residual_notional = abs((residual_qty * self.get_usd_px(top_of_book_obj.last_trade.px,
                                                                top_of_book_obj.symbol)) -
                                (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_trade.px,
                                                                          other_leg_top_of_book.symbol)))
        if side == Side.BUY:
            if (residual_qty * top_of_book_obj.last_trade.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_trade.px):
                residual_security = strat_brief.pair_buy_side_trading_brief.security
            else:
                residual_security = strat_brief.pair_sell_side_trading_brief.security
        else:
            if (residual_qty * top_of_book_obj.last_trade.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_trade.px):
                residual_security = strat_brief.pair_sell_side_trading_brief.security
            else:
                residual_security = strat_brief.pair_buy_side_trading_brief.security

        if residual_notional > 0:
            updated_residual = Residual(security=residual_security, residual_notional=residual_notional)
            return updated_residual
        else:
            updated_residual = Residual(security=residual_security, residual_notional=0)
            return updated_residual

    async def get_last_order_journal_matching_suffix_order_id(self, order_id_suffix: str) -> OrderJournal | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_of_matching_suffix_order_id_filter

        stored_order_list: List[OrderJournal] = await underlying_read_order_journal_http(
            get_order_of_matching_suffix_order_id_filter(order_id_suffix, sort=-1, limit=1),
            self.get_generic_read_route())
        if len(stored_order_list) > 0:
            return stored_order_list[0]
        else:
            return None

    async def get_last_n_sec_order_qty(self, symbol: str, side: Side, last_n_sec: int) -> int | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_total_sum_of_last_n_sec

        last_n_sec_order_qty: int | None = None
        if last_n_sec == 0:
            symbol_side_snapshots = await self._get_symbol_side_snapshot_from_symbol_side(symbol, side)
            if symbol_side_snapshots is not None:
                if len(symbol_side_snapshots) == 1:
                    symbol_side_snapshot = symbol_side_snapshots[0]
                else:
                    err_str_ = f"Could not find symbol_side_snapshot, symbol_side_key: " \
                               f"{get_symbol_side_key([(symbol, side)])}"
                    logging.error(err_str_)
                    return None
                last_n_sec_order_qty = symbol_side_snapshot.total_qty
            else:
                err_str_ = f"Found multiple symbol_side_snapshot for symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}, must be only one"
                logging.exception(err_str_)
        else:
            agg_objs = \
                await underlying_read_order_snapshot_http(get_order_total_sum_of_last_n_sec(symbol, last_n_sec),
                                                          self.get_generic_read_route())

            if len(agg_objs) > 0:
                last_n_sec_order_qty = agg_objs[-1].last_n_sec_total_qty
            else:
                last_n_sec_order_qty = 0
                err_str_ = "received empty list of aggregated objects from aggregation on OrderSnapshot to " \
                           f"get last {last_n_sec} sec total order sum, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.debug(err_str_)
        return last_n_sec_order_qty

    async def get_last_n_sec_trade_qty(self, symbol: str, side: Side) -> int | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_get_last_n_sec_total_qty_query_http)

        strat_limits = await self._get_strat_limits()

        last_n_sec_trade_qty: int | None = None
        if strat_limits is not None:
            applicable_period_seconds = strat_limits.market_trade_volume_participation.applicable_period_seconds
            last_n_sec_market_trade_vol_obj_list = \
                await underlying_get_last_n_sec_total_qty_query_http(symbol, applicable_period_seconds)
            if last_n_sec_market_trade_vol_obj_list:
                last_n_sec_trade_qty = last_n_sec_market_trade_vol_obj_list[0].last_n_sec_trade_vol
            else:
                logging.error(f"could not receive any last_n_sec_market_trade_vol_obj to get last_n_sec_trade_qty "
                              f"for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_last_n_sec_total_qty_query pre impl")
        return last_n_sec_trade_qty

    async def get_rolling_new_order_count(self, symbol: str) -> int | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_get_last_n_sec_orders_by_event_query_http)
        portfolio_limits_obj = strat_manager_service_http_client.get_portfolio_limits_client(1)

        rolling_order_count_period_seconds = \
            portfolio_limits_obj.rolling_max_order_count.rolling_tx_count_period_seconds

        order_count_updated_order_journals = \
            await underlying_get_last_n_sec_orders_by_event_query_http(symbol,
                                                                       rolling_order_count_period_seconds,
                                                                       OrderEventType.OE_NEW)
        if len(order_count_updated_order_journals) == 1:
            rolling_new_order_count = order_count_updated_order_journals[-1].current_period_order_count
        elif len(order_count_updated_order_journals) > 1:
            err_str_ = "Must receive only one object by get_last_n_sec_orders_by_event_query, " \
                       f"received {order_count_updated_order_journals} for symbol {symbol}"
            logging.error(err_str_)
            return None
        else:
            rolling_new_order_count = 0
        return rolling_new_order_count

    async def get_list_of_underlying_account_n_cumulative_fill_qty(self, symbol: str, side: Side):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            get_underlying_account_cumulative_fill_qty_query_http
        underlying_account_cum_fill_qty_obj_list = \
            await get_underlying_account_cumulative_fill_qty_query_http(symbol, side)
        return underlying_account_cum_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty

    ######################################
    # Strat lvl models update pre handling
    ######################################

    async def create_command_n_control_pre(self, command_n_control_obj: CommandNControl):
        match command_n_control_obj.command_type:
            case CommandType.CLEAR_STRAT:
                for symbol, side in [(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side),
                                     (self.strat_leg_2.sec.sec_id, self.strat_leg_2.side)]:
                    file_path = EXECUTOR_PROJECT_DATA_DIR / f"{symbol}_{side}_{DateTime.date(DateTime.utcnow())}.json.lock"
                    if os.path.exists(file_path):
                        os.remove(file_path)
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_beanie_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_command_n_control_pre failed. unrecognized command_type: {other_}")

    async def update_strat_limits_pre(self, stored_strat_limits_obj: StratLimits,
                                      updated_strat_limits_obj: StratLimits):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_limits_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_strat_limits_obj.strat_limits_update_seq_num is None:
            updated_strat_limits_obj.strat_limits_update_seq_num = 0
        updated_strat_limits_obj.strat_limits_update_seq_num += 1
        return updated_strat_limits_obj

    async def partial_update_strat_limits_pre(self, stored_strat_limits_obj: StratLimits,
                                              updated_strat_limits_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_limits_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_strat_limits_obj.strat_limits_update_seq_num is None:
            stored_strat_limits_obj.strat_limits_update_seq_num = 0
        updated_strat_limits_obj_json[
            "strat_limits_update_seq_num"] = stored_strat_limits_obj.strat_limits_update_seq_num + 1
        return updated_strat_limits_obj_json

    async def _update_strat_status_pre(self, stored_strat_status_obj: StratStatus,
                                       updated_strat_status_obj: StratStatus) -> bool | None:
        """
        Return true if alert raised false otherwise
        """
        raised_alert = False
        if updated_strat_status_obj.strat_state == StratState.StratState_ACTIVE:
            raised_alert = self._apply_checks_n_log_error(updated_strat_status_obj)
            if raised_alert:
                # some check is violated, move strat to error
                updated_strat_status_obj.strat_state = StratState.StratState_ERROR
            # else not required - no alerts - all checks passed
            if stored_strat_status_obj.strat_state != StratState.StratState_ACTIVE:
                for symbol, side in [(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side),
                                     (self.strat_leg_2.sec.sec_id, self.strat_leg_2.side)]:
                    file_path = EXECUTOR_PROJECT_DATA_DIR / f"{symbol}_{side}_{DateTime.date(DateTime.utcnow())}.json.lock"
                    with open(file_path, "w") as fl:
                        pass

            # else not required: pair_strat_id_n_today_activated_tickers_dict is updated only if we activate a new strat
        return raised_alert

    async def update_strat_status_pre(self, stored_strat_status_obj: StratStatus,
                                      updated_strat_status_obj: StratStatus):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_status_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if updated_strat_status_obj.strat_status_update_seq_num is None:
            updated_strat_status_obj.strat_status_update_seq_num = 0
        updated_strat_status_obj.strat_status_update_seq_num += 1
        updated_strat_status_obj.last_update_date_time = DateTime.utcnow()

        res = await self._update_strat_status_pre(stored_strat_status_obj, updated_strat_status_obj)
        if res:
            logging.debug(f"Alerts updated by _update_strat_status_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                          f"strat_status: {updated_strat_status_obj}")
        return updated_strat_status_obj

    async def update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                       updated_strat_status_obj: StratStatus):
        await self._create_related_models_for_active_strat(stored_strat_status_obj, updated_strat_status_obj)

        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)


    async def partial_update_strat_status_pre(self, stored_strat_status_obj: StratStatus,
                                              updated_strat_status_obj_json: Dict):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_status_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if stored_strat_status_obj.strat_status_update_seq_num is None:
            stored_strat_status_obj.strat_status_update_seq_num = 0
        updated_strat_status_obj_json[
            "strat_status_update_seq_num"] = stored_strat_status_obj.strat_status_update_seq_num + 1
        updated_strat_status_obj_json["last_update_date_time"] = DateTime.utcnow()

        updated_pydantic_obj_dict = compare_n_patch_dict(copy.deepcopy(stored_strat_status_obj.dict(by_alias=True)),
                                                         updated_strat_status_obj_json)
        updated_strat_status_obj = StratStatusOptional(**updated_pydantic_obj_dict)
        res = await self._update_strat_status_pre(stored_strat_status_obj, updated_strat_status_obj)
        if res:
            logging.debug(f"Alerts updated by _update_strat_status_pre, symbol_side_key: "
                          f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                          f"strat_status: {updated_strat_status_obj} ")
        return updated_strat_status_obj_json

    async def partial_update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                               updated_strat_status_obj: StratStatus):
        await self._create_related_models_for_active_strat(stored_strat_status_obj, updated_strat_status_obj)

        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)

    ##############################
    # Order Journal Update Methods
    ##############################

    async def create_order_journal_pre(self, order_journal_obj: OrderJournal) -> None:
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_order_journal_pre not ready - service is not initialized yet, " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # updating order notional in order journal obj

        if order_journal_obj.order_event == OrderEventType.OE_NEW and order_journal_obj.order.px == 0:
            top_of_book_obj = await self._get_top_of_book_from_symbol(order_journal_obj.order.security.sec_id)
            if top_of_book_obj is not None:
                order_journal_obj.order.px = top_of_book_obj.last_trade.px
            else:
                err_str_ = f"received order journal px 0 and to update px, received TOB also as {top_of_book_obj}, " \
                           f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        # If order_journal is not new then we don't care about px, we care about event_type and if order is new
        # and px is not 0 then using provided px

        if order_journal_obj.order.px is not None and order_journal_obj.order.qty is not None:
            order_journal_obj.order.order_notional = \
                self.get_usd_px(order_journal_obj.order.px,
                                order_journal_obj.order.security.sec_id) * order_journal_obj.order.qty
        else:
            order_journal_obj.order.order_notional = 0

    async def create_order_journal_post(self, order_journal_obj: OrderJournal):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_order_journal_get_all_ws(order_journal_obj)

        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            residual_compute_shared_lock
        async with residual_compute_shared_lock:
            await self._update_order_snapshot_from_order_journal(order_journal_obj)

    async def create_order_snapshot_pre(self, order_snapshot_obj: OrderSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if order_snapshot_obj.order_brief.security.sec_type is None:
            order_snapshot_obj.order_brief.security.sec_type = SecurityType.TICKER

    async def create_symbol_side_snapshot_pre(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if symbol_side_snapshot_obj.security.sec_type is None:
            symbol_side_snapshot_obj.security.sec_type = SecurityType.TICKER

    async def _update_order_snapshot_from_order_journal(self, order_journal_obj: OrderJournal):
        strat_status = await self._get_strat_status()
        if not is_ongoing_strat(strat_status):
            # avoiding any update if strat is paused
            return

        match order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_create_order_snapshot_http

                order_snapshot = OrderSnapshot(_id=OrderSnapshot.next_id(),
                                               order_brief=order_journal_obj.order,
                                               filled_qty=0, avg_fill_px=0,
                                               fill_notional=0,
                                               cxled_qty=0,
                                               avg_cxled_px=0,
                                               cxled_notional=0,
                                               last_update_fill_qty=0,
                                               last_update_fill_px=0,
                                               create_date_time=order_journal_obj.order_event_date_time,
                                               last_update_date_time=order_journal_obj.order_event_date_time,
                                               order_status=OrderStatusType.OE_UNACK)
                order_snapshot = await underlying_create_order_snapshot_http(order_snapshot)
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                      order_snapshot)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                    symbol_side_snapshot)
                    await self._update_strat_status_from_order_journal(order_journal_obj, order_snapshot,
                                                                       symbol_side_snapshot, updated_strat_brief)
                    await self._update_portfolio_status_from_order_journal(
                        order_journal_obj, order_snapshot)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already

            case OrderEventType.OE_ACK:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(order_journal_obj,
                                                                       [OrderStatusType.OE_UNACK])
                if order_snapshot is not None:
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(
                            _id=order_snapshot.id, last_update_date_time=order_journal_obj.order_event_date_time,
                            order_status=OrderStatusType.OE_ACKED).json(by_alias=True, exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = await self._check_state_and_get_order_snapshot_obj(
                    order_journal_obj, [OrderStatusType.OE_UNACK, OrderStatusType.OE_ACKED])
                if order_snapshot is not None:
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(
                            _id=order_snapshot.id, last_update_date_time=order_journal_obj.order_event_date_time,
                            order_status=OrderStatusType.OE_CXL_UNACK).json(by_alias=True, exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL_ACK:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED,
                                            OrderStatusType.OE_UNACK])
                if order_snapshot is not None:
                    order_brief = OrderBrief(**order_snapshot.order_brief.dict())
                    if order_journal_obj.order.text:
                        if order_brief.text:
                            order_brief.text.extend(order_journal_obj.order.text)
                        else:
                            order_brief.text = order_journal_obj.order.text
                    # else not required: If no text is present in order_journal then updating
                    # order snapshot with same obj

                    cxled_qty = order_snapshot.order_brief.qty - order_snapshot.filled_qty
                    cxled_notional = cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                 order_snapshot.order_brief.security.sec_id)
                    avg_cxled_px = \
                        (self.get_local_px_or_notional(cxled_notional, order_snapshot.order_brief.security.sec_id) /
                         cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot = await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         order_brief=order_brief,
                                                         cxled_qty=cxled_qty,
                                                         cxled_notional=cxled_notional,
                                                         avg_cxled_px=avg_cxled_px,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=OrderStatusType.OE_DOD).json(by_alias=True,
                                                                                                   exclude_none=True)))

                    # updating cancel_order object for this id
                    cxl_marked_cxl_order = await self.update_cxl_order_for_order_cxl_ack(order_snapshot)
                    if cxl_marked_cxl_order is None:
                        return None

                    symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_order_journal(
                        order_journal_obj, order_snapshot)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                        symbol_side_snapshot)
                        await self._update_strat_status_from_order_journal(order_journal_obj, order_snapshot,
                                                                           symbol_side_snapshot, updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                    # is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have got added to alert already

                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_CXL_REJ:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = await self._check_state_and_get_order_snapshot_obj(
                    order_journal_obj, [OrderStatusType.OE_CXL_UNACK])
                if order_snapshot is not None:
                    if order_snapshot.order_brief.qty > order_snapshot.filled_qty:
                        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                            underlying_read_order_journal_http
                        from Flux.CodeGenProjects.strat_executor.app.aggregate import \
                            get_last_n_order_journals_from_order_id
                        last_3_order_journals_from_order_id = \
                            await underlying_read_order_journal_http(
                                get_last_n_order_journals_from_order_id(order_journal_obj.order.order_id, 3),
                                self.get_generic_read_route())
                        if last_3_order_journals_from_order_id:
                            if last_3_order_journals_from_order_id[0].order_event == OrderEventType.OE_CXL_REJ:
                                if last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_NEW:
                                    order_status = OrderStatusType.OE_UNACK
                                elif last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_ACK:
                                    order_status = OrderStatusType.OE_ACKED
                                else:
                                    err_str_ = "3rd order journal from order_journal of status OE_CXL_REJ, must be" \
                                               "of status OE_ACK and OE_UNACK, received last 3 order_journals " \
                                               f"{last_3_order_journals_from_order_id}, " \
                                               f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                                    logging.error(err_str_)
                                    return None
                            else:
                                err_str_ = "Recent order journal must be of status OE_CXL_REJ, " \
                                           f"received last 3 order_journals {last_3_order_journals_from_order_id}, " \
                                           f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                                logging.error(err_str_)
                                return None
                        else:
                            err_str_ = f"Received empty list while fetching last 3 order_journals for " \
                                       f"order_id {order_journal_obj.order.order_id}, " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return None
                    elif order_snapshot.order_brief.qty < order_snapshot.filled_qty:
                        order_status = OrderStatusType.OE_OVER_FILLED
                    else:
                        order_status = OrderStatusType.OE_FILLED
                    await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                         last_update_date_time=order_journal_obj.order_event_date_time,
                                                         order_status=order_status).json(by_alias=True,
                                                                                         exclude_none=True)))
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_REJ:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_partial_update_order_snapshot_http
                order_snapshot = \
                    await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_UNACK, OrderStatusType.OE_ACKED])
                if order_snapshot is not None:
                    order_brief = OrderBrief(**order_snapshot.order_brief.dict())
                    if order_brief.text:
                        order_brief.text.extend(order_journal_obj.order.text)
                    else:
                        order_brief.text = order_journal_obj.order.text
                    cxled_qty = order_snapshot.order_brief.qty - order_snapshot.filled_qty
                    cxled_notional = \
                        order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                   order_snapshot.order_brief.security.sec_id)
                    avg_cxled_px = \
                        (self.get_local_px_or_notional(cxled_notional, order_snapshot.order_brief.security.sec_id) /
                         cxled_qty) if cxled_qty != 0 else 0
                    order_snapshot = await underlying_partial_update_order_snapshot_http(
                        json.loads(OrderSnapshotOptional(
                            _id=order_snapshot.id,
                            order_brief=order_brief,
                            cxled_qty=cxled_qty,
                            cxled_notional=cxled_notional,
                            avg_cxled_px=avg_cxled_px,
                            last_update_date_time=order_journal_obj.order_event_date_time,
                            order_status=OrderStatusType.OE_DOD).json(by_alias=True, exclude_none=True)))
                    symbol_side_snapshot = \
                        await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                          order_snapshot)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot,
                                                                                        symbol_side_snapshot)
                        await self._update_strat_status_from_order_journal(order_journal_obj, order_snapshot,
                                                                           symbol_side_snapshot, updated_strat_brief)
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot)
                    # else not require_create_update_symbol_side_snapshot_from_order_journald:
                    # if symbol_side_snapshot is None then it means some error occurred in
                    # _create_update_symbol_side_snapshot_from_order_journal which would have
                    # got added to alert already
                # else not required: none returned object signifies there was something wrong in
                # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case other_:
                err_str_ = f"Unsupported Order event - {other_} in order_journal_key: " \
                           f"{get_order_journal_log_key(order_journal_obj)}, order_journal: {order_journal_obj}"
                logging.error(err_str_)

    async def _create_symbol_side_snapshot_for_new_order(self,
                                                         new_order_journal_obj: OrderJournal) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_create_symbol_side_snapshot_http
        security = new_order_journal_obj.order.security
        side = new_order_journal_obj.order.side
        symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(), security=security,
                                                      side=side,
                                                      avg_px=new_order_journal_obj.order.px,
                                                      total_qty=new_order_journal_obj.order.qty,
                                                      total_filled_qty=0, avg_fill_px=0,
                                                      total_fill_notional=0, last_update_fill_qty=0,
                                                      last_update_fill_px=0, total_cxled_qty=0,
                                                      avg_cxled_px=0, total_cxled_notional=0,
                                                      last_update_date_time=new_order_journal_obj.order_event_date_time,
                                                      order_count=1
                                                      )
        symbol_side_snapshot_obj = \
            await underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj

    async def _create_update_symbol_side_snapshot_from_order_journal(self, order_journal: OrderJournal,
                                                                     order_snapshot_obj: OrderSnapshot
                                                                     ) -> SymbolSideSnapshot | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_side_snapshot_http, underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        symbol_side_snapshot_objs = await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(order_journal.order.security.sec_id, order_journal.order.side),
            self.get_generic_read_route())

        # If no symbol_side_snapshot for symbol-side of received order_journal
        if len(symbol_side_snapshot_objs) == 0:
            if order_journal.order_event == OrderEventType.OE_NEW:
                created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_order(order_journal)
                return created_symbol_side_snapshot
            else:
                err_str_: str = (f"no OE_NEW detected for order_journal_key: "
                                 f"{get_order_journal_log_key(order_journal)} "
                                 f"failed to create symbol_side_snapshot "
                                 f";;; order_journal: {order_journal}")
                logging.error(err_str_)
                return
        # If symbol_side_snapshot exists for order_id from order_journal
        elif len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            match order_journal.order_event:
                case OrderEventType.OE_NEW:
                    updated_symbol_side_snapshot_obj.order_count = symbol_side_snapshot_obj.order_count + 1
                    updated_symbol_side_snapshot_obj.avg_px = \
                        avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                  order_journal.order.px,
                                                  updated_symbol_side_snapshot_obj.order_count
                                                  )
                    updated_symbol_side_snapshot_obj.total_qty = symbol_side_snapshot_obj.total_qty + order_journal.order.qty
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal.order_event_date_time
                case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                    updated_symbol_side_snapshot_obj.total_cxled_qty = symbol_side_snapshot_obj.total_cxled_qty + order_snapshot_obj.cxled_qty
                    updated_symbol_side_snapshot_obj.total_cxled_notional = symbol_side_snapshot_obj.total_cxled_notional + order_snapshot_obj.cxled_notional
                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                            self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                          symbol_side_snapshot_obj.security.sec_id) /
                            updated_symbol_side_snapshot_obj.total_cxled_qty) \
                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0
                    updated_symbol_side_snapshot_obj.last_update_date_time = order_journal.order_event_date_time
                case other_:
                    err_str_ = f"Unsupported StratEventType for symbol_side_snapshot update {other_} " \
                               f"{get_order_journal_log_key(order_journal)}"
                    logging.error(err_str_)
                    return
            updated_symbol_side_snapshot_obj = await underlying_partial_update_symbol_side_snapshot_http(
                json.loads(updated_symbol_side_snapshot_obj.json(by_alias=True, exclude_none=True))
            )
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = f"SymbolSideSnapshot can't be multiple for single symbol and side combination, " \
                       f"order_journal_key: {get_order_journal_log_key(order_journal)}, " \
                       f"received {len(symbol_side_snapshot_objs)} - {symbol_side_snapshot_objs}"
            logging.error(err_str_)
            return

    async def _check_state_and_get_order_snapshot_obj(self, order_journal_obj: OrderJournal,
                                                      expected_status_list: List[str]) -> OrderSnapshot | None:
        """
        Checks if order_snapshot holding order_id of passed order_journal has expected status
        from provided statuses list and then returns that order_snapshot
        """
        order_snapshot_obj = await self._get_order_snapshot_from_order_journal_order_id(order_journal_obj)
        if order_snapshot_obj is not None:
            if order_snapshot_obj.order_status in expected_status_list:
                return order_snapshot_obj
            else:
                ord_journal_key: str = get_order_journal_log_key(order_journal_obj)
                ord_snapshot_key: str = get_order_snapshot_log_key(order_snapshot_obj)
                err_str_: str = f"_check_state_and_get_order_snapshot_obj: order_journal: {ord_journal_key} " \
                                f"received with event: {order_journal_obj.order_event}, to update status of " \
                                f"order_snapshot: {ord_snapshot_key}, with status: " \
                                f"{order_snapshot_obj.order_status}, but order_snapshot doesn't contain any of " \
                                f"expected statuses: {expected_status_list}" \
                                f";;; order_journal: {order_journal_obj}, order_snapshot_obj: {order_snapshot_obj}"
                logging.error(err_str_)
        # else not required: error occurred in _get_order_snapshot_from_order_journal_order_id,
        # alert must have updated

    async def update_cxl_order_for_order_cxl_ack(self,
                                                 order_snapshot: OrderSnapshot) -> CancelOrder | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_cancel_order_http, underlying_partial_update_cancel_order_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_by_order_id_filter

        cxl_order_list: List[CancelOrder] | None = await underlying_read_cancel_order_http(
            get_order_by_order_id_filter(order_snapshot.order_brief.order_id), self.get_generic_read_route())

        if len(cxl_order_list) == 1:
            # if cxl-confirmed field is already True
            if cxl_order_list[0].cxl_confirmed:
                err_str_ = (f"received cxl_order obj for order_id {order_snapshot.order_brief.order_id} "
                            f"already having cxl_confirmed field True while updating cxl_order in between "
                            f"order_snapshot update order_snapshot: {get_order_snapshot_log_key(order_snapshot)};;; "
                            f"order_snapshot: {order_snapshot}")
                logging.error(err_str_)
                return None
        else:
            if len(cxl_order_list) > 1:
                err_str_ = f"There must be only one cancel_order obj per order_id, " \
                           f"received {len(cxl_order_list)} for order_id {order_snapshot.order_brief.order_id}" \
                           f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot)};;; " \
                           f"cxl_order_list {cxl_order_list} for order_snapshot {order_snapshot}"
                logging.error(err_str_)
                return None
            else:
                # unsolicited cxl case
                return CancelOrderOptional()
        updated_cxl_order = CancelOrderOptional(_id=cxl_order_list[0].id, cxl_confirmed=True)
        confirm_marked_cxl_oder = await underlying_partial_update_cancel_order_http(
            json.loads(updated_cxl_order.json(by_alias=True, exclude_none=True)))
        return confirm_marked_cxl_oder

    async def _update_strat_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                      order_snapshot: OrderSnapshot,
                                                      symbol_side_snapshot: SymbolSideSnapshot,
                                                      strat_brief: StratBrief, ):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'

        strat_limits: StratLimits | None = await self._get_strat_limits()
        update_strat_status_obj: StratStatus | None = await self._get_strat_status()

        if strat_limits is not None and update_strat_status_obj is not None:
            match order_journal_obj.order.side:
                case Side.BUY:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            update_strat_status_obj.total_buy_qty += order_journal_obj.order.qty
                            update_strat_status_obj.total_open_buy_qty += order_journal_obj.order.qty
                            update_strat_status_obj.total_open_buy_notional += \
                                order_journal_obj.order.qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                              order_snapshot.order_brief.security.sec_id)
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_buy_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            update_strat_status_obj.total_open_buy_qty -= total_buy_unfilled_qty
                            update_strat_status_obj.total_open_buy_notional -= \
                                (total_buy_unfilled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                          order_snapshot.order_brief.security.sec_id))
                            update_strat_status_obj.total_cxl_buy_qty += order_snapshot.cxled_qty
                            update_strat_status_obj.total_cxl_buy_notional += \
                                order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id)
                            update_strat_status_obj.avg_cxl_buy_px = (
                                (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_buy_notional,
                                 order_journal_obj.order.security.sec_id) / update_strat_status_obj.total_cxl_buy_qty)
                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                            update_strat_status_obj.total_cxl_exposure = \
                                update_strat_status_obj.total_cxl_buy_notional - \
                                update_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_}, " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return
                    if update_strat_status_obj.total_open_buy_qty == 0:
                        update_strat_status_obj.avg_open_buy_px = 0
                    else:
                        update_strat_status_obj.avg_open_buy_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_open_buy_notional,
                                                          order_journal_obj.order.security.sec_id) / \
                            update_strat_status_obj.total_open_buy_qty
                case Side.SELL:
                    match order_journal_obj.order_event:
                        case OrderEventType.OE_NEW:
                            update_strat_status_obj.total_sell_qty += order_journal_obj.order.qty
                            update_strat_status_obj.total_open_sell_qty += order_journal_obj.order.qty
                            update_strat_status_obj.total_open_sell_notional += \
                                order_journal_obj.order.qty * self.get_usd_px(order_journal_obj.order.px,
                                                                              order_journal_obj.order.security.sec_id)
                        case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                            total_sell_unfilled_qty = \
                                order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            update_strat_status_obj.total_open_sell_qty -= total_sell_unfilled_qty
                            update_strat_status_obj.total_open_sell_notional -= \
                                (total_sell_unfilled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id))
                            update_strat_status_obj.total_cxl_sell_qty += order_snapshot.cxled_qty
                            update_strat_status_obj.total_cxl_sell_notional += \
                                order_snapshot.cxled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                           order_snapshot.order_brief.security.sec_id)
                            update_strat_status_obj.avg_cxl_sell_px = (
                                (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_sell_notional,
                                 order_journal_obj.order.security.sec_id) / update_strat_status_obj.total_cxl_sell_qty)
                                if (update_strat_status_obj.total_cxl_sell_qty != 0) else 0)
                            update_strat_status_obj.total_cxl_exposure = \
                                update_strat_status_obj.total_cxl_buy_notional - \
                                update_strat_status_obj.total_cxl_sell_notional
                        case other_:
                            err_str_ = f"Unsupported Order Event type {other_} " \
                                       f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}"
                            logging.error(err_str_)
                            return
                    if update_strat_status_obj.total_open_sell_qty == 0:
                        update_strat_status_obj.avg_open_sell_px = 0
                    else:
                        update_strat_status_obj.avg_open_sell_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_open_sell_notional,
                                                          order_journal_obj.order.security.sec_id) / \
                            update_strat_status_obj.total_open_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received in order_journal_key: " \
                               f"{get_order_journal_log_key(order_journal_obj)} while updating strat_status;;; " \
                               f"order_journal {order_journal_obj}"
                    logging.error(err_str_)
                    return
            update_strat_status_obj.total_order_qty = \
                update_strat_status_obj.total_buy_qty + update_strat_status_obj.total_sell_qty
            update_strat_status_obj.total_open_exposure = (update_strat_status_obj.total_open_buy_notional -
                                                           update_strat_status_obj.total_open_sell_notional)
            if update_strat_status_obj.total_fill_buy_notional < update_strat_status_obj.total_fill_sell_notional:
                update_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - update_strat_status_obj.total_fill_buy_notional
            else:
                update_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - update_strat_status_obj.total_fill_sell_notional

            updated_residual = await self.__get_residual_obj(order_snapshot.order_brief.side, strat_brief)
            if updated_residual is not None:
                update_strat_status_obj.residual = updated_residual

            # Updating strat_state as paused if limits get breached
            self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                 strat_brief, symbol_side_snapshot)

            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
                underlying_partial_update_strat_status_http)

            await underlying_partial_update_strat_status_http(json.loads(
                update_strat_status_obj.json(by_alias=True, exclude_none=True)))
        else:
            logging.error(f"error: either strat_status or strat_limits received as None;;; "
                          f"strat_status: {update_strat_status_obj}, strat_limits: {strat_limits}")
            return

    async def _update_strat_brief_from_order(self, order_snapshot: OrderSnapshot,
                                             symbol_side_snapshot: SymbolSideSnapshot) -> StratBrief | None:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_strat_brief_http, underlying_partial_update_strat_brief_http, \
            underlying_get_executor_check_snapshot_query_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_strat_brief_from_symbol

        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id
        strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol),
                                                                  self.get_generic_read_route())

        strat_limits: StratLimits | None = await self._get_strat_limits()

        if len(strat_brief_objs) == 1:
            strat_brief_obj = strat_brief_objs[0]

            if strat_limits is not None:
                open_qty = (symbol_side_snapshot.total_qty -
                            (symbol_side_snapshot.total_filled_qty + symbol_side_snapshot.total_cxled_qty))
                open_notional = open_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                           order_snapshot.order_brief.security.sec_id)
                consumable_notional = (strat_limits.max_cb_notional - symbol_side_snapshot.total_fill_notional -
                                       open_notional)
                consumable_open_notional = strat_limits.max_open_cb_notional - open_notional
                security_float = self.static_data.get_security_float_from_ticker(symbol)
                if security_float is not None:
                    consumable_concentration = \
                        (security_float / 100) * strat_limits.max_concentration - \
                        (open_qty + symbol_side_snapshot.total_filled_qty)
                else:
                    consumable_concentration = 0
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_get_open_order_count_query_http
                open_orders_count = await underlying_get_open_order_count_query_http(symbol)
                consumable_open_orders = strat_limits.max_open_orders_per_side - open_orders_count[0].open_order_count
                consumable_cxl_qty = ((((symbol_side_snapshot.total_filled_qty + open_qty +
                                         symbol_side_snapshot.total_cxled_qty) / 100) *
                                       strat_limits.cancel_rate.max_cancel_rate) -
                                      symbol_side_snapshot.total_cxled_qty)
                applicable_period_second = strat_limits.market_trade_volume_participation.applicable_period_seconds
                executor_check_snapshot_list = \
                    await underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                            applicable_period_second)
                if len(executor_check_snapshot_list) == 1:
                    participation_period_order_qty_sum = \
                        executor_check_snapshot_list[0].last_n_sec_order_qty
                    indicative_consumable_participation_qty = \
                        get_consumable_participation_qty(
                            executor_check_snapshot_list,
                            strat_limits.market_trade_volume_participation.max_participation_rate)
                else:
                    logging.error("Received unexpected length of executor_check_snapshot_list from query "
                                  f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                                  f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                                  f"get_executor_check_snapshot_query pre implementation")
                    indicative_consumable_participation_qty = 0
                    participation_period_order_qty_sum = 0

                updated_pair_side_brief_obj = \
                    PairSideTradingBrief(security=security, side=side,
                                         last_update_date_time=order_snapshot.last_update_date_time,
                                         consumable_open_orders=consumable_open_orders,
                                         consumable_notional=consumable_notional,
                                         consumable_open_notional=consumable_open_notional,
                                         consumable_concentration=consumable_concentration,
                                         participation_period_order_qty_sum=participation_period_order_qty_sum,
                                         consumable_cxl_qty=consumable_cxl_qty,
                                         indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                         all_bkr_cxlled_qty=symbol_side_snapshot.total_cxled_qty,
                                         open_notional=open_notional,
                                         open_qty=open_qty)

                if side == Side.BUY:
                    other_leg_residual_qty = strat_brief_obj.pair_sell_side_trading_brief.residual_qty
                    stored_pair_strat_trading_brief = strat_brief_obj.pair_buy_side_trading_brief
                    other_leg_symbol = strat_brief_obj.pair_sell_side_trading_brief.security.sec_id
                else:
                    other_leg_residual_qty = strat_brief_obj.pair_buy_side_trading_brief.residual_qty
                    stored_pair_strat_trading_brief = strat_brief_obj.pair_sell_side_trading_brief
                    other_leg_symbol = strat_brief_obj.pair_buy_side_trading_brief.security.sec_id
                top_of_book_obj = await self._get_top_of_book_from_symbol(symbol)
                other_leg_top_of_book = await self._get_top_of_book_from_symbol(other_leg_symbol)
                if top_of_book_obj is not None and other_leg_top_of_book is not None:
                    if order_snapshot.order_status == OrderStatusType.OE_DOD:
                        residual_qty = stored_pair_strat_trading_brief.residual_qty + \
                                       (order_snapshot.order_brief.qty - order_snapshot.filled_qty)
                        # Updating residual_qty
                        updated_pair_side_brief_obj.residual_qty = residual_qty
                    else:
                        residual_qty = stored_pair_strat_trading_brief.residual_qty
                        updated_pair_side_brief_obj.residual_qty = residual_qty
                    updated_pair_side_brief_obj.indicative_consumable_residual = \
                        strat_limits.residual_restriction.max_residual - \
                        ((residual_qty * top_of_book_obj.last_trade.px) -
                         (other_leg_residual_qty * other_leg_top_of_book.last_trade.px))
                else:
                    logging.error(f"received buy TOB as {top_of_book_obj} and sel TOB as {other_leg_top_of_book}, "
                                  f"order_snapshot_key: {order_snapshot}")
                    return

                if symbol == strat_brief_obj.pair_buy_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_buy_side_trading_brief=updated_pair_side_brief_obj)
                elif symbol == strat_brief_obj.pair_sell_side_trading_brief.security.sec_id:
                    updated_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                             pair_sell_side_trading_brief=updated_pair_side_brief_obj)
                else:
                    err_str_ = f"error: None of the 2 pair_side_trading_brief(s) contain symbol: {symbol} in " \
                               f"strat_brief of key: {get_strat_brief_log_key(strat_brief_obj)};;; strat_brief: " \
                               f"{strat_brief_obj}"
                    logging.exception(err_str_)
                    return

                updated_strat_brief = \
                    await underlying_partial_update_strat_brief_http(
                        json.loads(updated_strat_brief.json(by_alias=True, exclude_none=True)))
                logging.debug(f"Updated strat_brief: order_id: {order_snapshot.order_brief.order_id}, "
                              f"strat_brief: {updated_strat_brief}")
                return updated_strat_brief
            else:
                logging.error(f"error: received strat_limits as None, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}")
                return

        else:
            err_str_ = f"StratBrief must be one per symbol, received {len(strat_brief_objs)} for symbol {symbol}, " \
                       f"order_snapshot_key: {order_snapshot};;;StratBriefs: {strat_brief_objs}"
            logging.exception(err_str_)
            return

    async def _update_portfolio_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                          order_snapshot_obj: OrderSnapshot):
        match order_journal_obj.order.side:
            case Side.BUY:
                update_overall_buy_notional = 0
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        update_overall_buy_notional = \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_buy_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        update_overall_buy_notional = \
                            -(self.get_usd_px(order_snapshot_obj.order_brief.px,
                                              order_snapshot_obj.order_brief.security.sec_id) * total_buy_unfilled_qty)

                strat_manager_service_http_client.update_portfolio_status_by_order_or_fill_data_query_client(
                    overall_buy_notional=update_overall_buy_notional)
            case Side.SELL:
                update_overall_sell_notional = 0
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        update_overall_sell_notional = \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case OrderEventType.OE_CXL_ACK | OrderEventType.OE_REJ:
                        total_sell_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        update_overall_sell_notional = \
                            -(self.get_usd_px(order_snapshot_obj.order_brief.px,
                                              order_snapshot_obj.order_brief.security.sec_id) * total_sell_unfilled_qty)

                strat_manager_service_http_client.update_portfolio_status_by_order_or_fill_data_query_client(
                    overall_sell_notional=update_overall_sell_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order_journal of key: " \
                           f"{get_order_journal_log_key(order_journal_obj)} while updating strat_status;;; " \
                           f"order_journal_obj: {order_journal_obj} "
                logging.error(err_str_)
                return

    ##############################
    # Fills Journal Update Methods
    ##############################

    async def create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_fills_journal_pre not ready - service is not initialized yet, " \
                       f"fills_journal_key: {get_fills_journal_log_key(fills_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # Updating notional field in fills journal
        fills_journal_obj.fill_notional = \
            self.get_usd_px(fills_journal_obj.fill_px, fills_journal_obj.fill_symbol) * fills_journal_obj.fill_qty

    async def create_fills_journal_post(self, fills_journal_obj: FillsJournal):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_fills_journal_get_all_ws(fills_journal_obj)

        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            residual_compute_shared_lock
        async with residual_compute_shared_lock:
            await self._apply_fill_update_in_order_snapshot(fills_journal_obj)

    async def _update_portfolio_status_from_fill_journal(self, order_snapshot_obj: OrderSnapshot):

        match order_snapshot_obj.order_brief.side:
            case Side.BUY:
                update_overall_buy_notional = \
                    (order_snapshot_obj.last_update_fill_qty *
                     self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                     order_snapshot_obj.order_brief.security.sec_id)) - \
                    (order_snapshot_obj.last_update_fill_qty *
                     self.get_usd_px(order_snapshot_obj.order_brief.px,
                                     order_snapshot_obj.order_brief.security.sec_id))
                update_overall_buy_fill_notional = \
                    (self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                     order_snapshot_obj.order_brief.security.sec_id) *
                     order_snapshot_obj.last_update_fill_qty)
                strat_manager_service_http_client.update_portfolio_status_by_order_or_fill_data_query_client(
                    overall_buy_notional=update_overall_buy_notional,
                    overall_buy_fill_notional=update_overall_buy_fill_notional)
            case Side.SELL:
                update_overall_sell_notional = \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                                                               order_snapshot_obj.order_brief.security.sec_id)) - \
                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                               order_snapshot_obj.order_brief.security.sec_id))
                update_overall_sell_fill_notional = \
                    self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id) * \
                    order_snapshot_obj.last_update_fill_qty
                strat_manager_service_http_client.update_portfolio_status_by_order_or_fill_data_query_client(
                    overall_sell_notional=update_overall_sell_notional,
                    overall_sell_fill_notional=update_overall_sell_fill_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order snapshot of key " \
                           f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                           f"order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)
                return

    async def _update_symbol_side_snapshot_from_fill_applied_order_snapshot(
            self, order_snapshot_obj: OrderSnapshot) -> SymbolSideSnapshot:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_side_snapshot_http, underlying_partial_update_symbol_side_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        symbol_side_snapshot_objs = await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(order_snapshot_obj.order_brief.security.sec_id,
                                                      order_snapshot_obj.order_brief.side),
            self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) == 1:
            symbol_side_snapshot_obj = symbol_side_snapshot_objs[0]
            updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
            updated_symbol_side_snapshot_obj.total_filled_qty = \
                symbol_side_snapshot_obj.total_filled_qty + order_snapshot_obj.last_update_fill_qty
            updated_symbol_side_snapshot_obj.total_fill_notional = \
                symbol_side_snapshot_obj.total_fill_notional + \
                (self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                 order_snapshot_obj.order_brief.security.sec_id) *
                 order_snapshot_obj.last_update_fill_qty)
            updated_symbol_side_snapshot_obj.avg_fill_px = \
                self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_fill_notional,
                                              symbol_side_snapshot_obj.security.sec_id) / \
                updated_symbol_side_snapshot_obj.total_filled_qty
            updated_symbol_side_snapshot_obj.last_update_fill_px = order_snapshot_obj.last_update_fill_px
            updated_symbol_side_snapshot_obj.last_update_fill_qty = order_snapshot_obj.last_update_fill_qty
            updated_symbol_side_snapshot_obj.last_update_date_time = order_snapshot_obj.last_update_date_time

            updated_symbol_side_snapshot_obj = await underlying_partial_update_symbol_side_snapshot_http(
                json.loads(updated_symbol_side_snapshot_obj.json(by_alias=True, exclude_none=True))
            )
            return updated_symbol_side_snapshot_obj
        else:
            err_str_ = f"SymbolSideSnapshot must be only one per symbol," \
                       f" order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)}, " \
                       f"received {len(symbol_side_snapshot_objs)}, - {symbol_side_snapshot_objs}"
            logging.error(err_str_)

    async def _apply_fill_update_in_order_snapshot(self, fills_journal_obj: FillsJournal) -> None:
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'

        strat_status = await self._get_strat_status()
        if not is_ongoing_strat(strat_status):
            # avoiding any update if strat is paused
            return

        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_snapshot_http, underlying_partial_update_order_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_snapshot_order_id_filter_json
        order_snapshot_objs = \
            await underlying_read_order_snapshot_http(get_order_snapshot_order_id_filter_json(
                fills_journal_obj.order_id), self.get_generic_read_route())
        if len(order_snapshot_objs) == 1:
            order_snapshot_obj = order_snapshot_objs[0]
            if order_snapshot_obj.order_status == OrderStatusType.OE_ACKED:
                if (total_filled_qty := order_snapshot_obj.filled_qty) is not None:
                    updated_total_filled_qty = total_filled_qty + fills_journal_obj.fill_qty
                else:
                    updated_total_filled_qty = fills_journal_obj.fill_qty
                received_fill_notional = fills_journal_obj.fill_notional
                last_update_fill_qty = fills_journal_obj.fill_qty
                last_update_fill_px = fills_journal_obj.fill_px

                if order_snapshot_obj.order_brief.qty == updated_total_filled_qty:
                    order_status = OrderStatusType.OE_FILLED
                elif order_snapshot_obj.order_brief.qty < updated_total_filled_qty:
                    vacant_fill_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                    non_required_received_fill_qty = fills_journal_obj.fill_qty - vacant_fill_qty
                    updated_total_filled_qty = order_snapshot_obj.order_brief.qty
                    order_status = OrderStatusType.OE_FILLED
                    received_fill_notional = self.get_usd_px(fills_journal_obj.fill_px,
                                                             fills_journal_obj.fill_symbol) * vacant_fill_qty
                    last_update_fill_qty = vacant_fill_qty

                    logging.warning(f"Unexpected: Received fill that makes order_snapshot OVER_FILLED, "
                                    f"vacant_fill_qty: {vacant_fill_qty}, received fill_qty "
                                    f"{fills_journal_obj.fill_qty}, taking only vacant_fill_qty for order_fill and "
                                    f"ignoring remaining {non_required_received_fill_qty} from fills_journal_key "
                                    f"{get_fills_journal_log_key(fills_journal_obj)};;; fills_journal {fills_journal_obj}")
                else:
                    order_status = order_snapshot_obj.order_status

                if (last_filled_notional := order_snapshot_obj.fill_notional) is not None:
                    updated_fill_notional = last_filled_notional + received_fill_notional
                else:
                    updated_fill_notional = received_fill_notional
                updated_avg_fill_px = \
                    self.get_local_px_or_notional(updated_fill_notional,
                                                  fills_journal_obj.fill_symbol) / updated_total_filled_qty

                order_snapshot_obj = \
                    await underlying_partial_update_order_snapshot_http(json.loads(OrderSnapshotOptional(
                        _id=order_snapshot_obj.id, filled_qty=updated_total_filled_qty, avg_fill_px=updated_avg_fill_px,
                        fill_notional=updated_fill_notional, last_update_fill_qty=last_update_fill_qty,
                        last_update_fill_px=last_update_fill_px,
                        last_update_date_time=fills_journal_obj.fill_date_time, order_status=order_status).json(
                        by_alias=True, exclude_none=True)))
                symbol_side_snapshot = \
                    await self._update_symbol_side_snapshot_from_fill_applied_order_snapshot(order_snapshot_obj)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order(order_snapshot_obj,
                                                                                    symbol_side_snapshot)
                    await self._update_strat_status_from_fill_journal(order_snapshot_obj, symbol_side_snapshot,
                                                                      updated_strat_brief)
                    await self._update_portfolio_status_from_fill_journal(order_snapshot_obj)
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already
            elif order_snapshot_obj.order_status == OrderStatusType.OE_FILLED:
                err_str_ = f"Unsupported - Fill received for completely filled order_snapshot, " \
                           f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)}, ignoring this " \
                           f"fill journal;;; fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)
            else:
                err_str_ = f"Unsupported - Fill received for order_snapshot having status " \
                           f"{order_snapshot_obj.order_status}, order_snapshot_key: " \
                           f"{get_order_snapshot_log_key(order_snapshot_obj)};;; " \
                           f"fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)

        elif len(order_snapshot_objs) == 0:
            err_str_ = f"Could not find any order snapshot with order-id {fills_journal_obj.order_id}, " \
                       f"fill_journal_key: {get_fills_journal_log_key(fills_journal_obj)};;; " \
                       f"order_snapshot_list: {order_snapshot_objs}"
            logging.error(err_str_)
        else:
            err_str_ = f"Match should return list of only one order_snapshot obj, " \
                       f"returned {len(order_snapshot_objs)}, fills_journal_key: " \
                       f"{get_fills_journal_log_key(fills_journal_obj)};;; order_snapshot_list: {order_snapshot_objs}"
            logging.error(err_str_)

    async def _update_strat_status_from_fill_journal(self, order_snapshot_obj: OrderSnapshot,
                                                     symbol_side_snapshot: SymbolSideSnapshot,
                                                     strat_brief_obj: StratBrief):
        # importing routes here otherwise at the time of launch callback's set instance is called by
        # routes call before set_instance file call and set_instance file throws error that
        # 'set instance called more than once in one session'

        strat_limits: StratLimits | None = await self._get_strat_limits()
        update_strat_status_obj: StratStatus | None = await self._get_strat_status()

        if strat_limits is not None and update_strat_status_obj is not None:
            match order_snapshot_obj.order_brief.side:
                case Side.BUY:
                    update_strat_status_obj.total_open_buy_qty -= order_snapshot_obj.last_update_fill_qty
                    update_strat_status_obj.total_open_buy_notional -= \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                                  order_snapshot_obj.order_brief.security.sec_id)
                    if update_strat_status_obj.total_open_buy_qty == 0:
                        update_strat_status_obj.avg_open_buy_px = 0
                    else:
                        update_strat_status_obj.avg_open_buy_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_open_buy_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            update_strat_status_obj.total_open_buy_qty
                    update_strat_status_obj.total_fill_buy_qty += order_snapshot_obj.last_update_fill_qty
                    update_strat_status_obj.total_fill_buy_notional += \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                            order_snapshot_obj.last_update_fill_px,
                            order_snapshot_obj.order_brief.security.sec_id)
                    update_strat_status_obj.avg_fill_buy_px = \
                        self.get_local_px_or_notional(update_strat_status_obj.total_fill_buy_notional,
                                                      order_snapshot_obj.order_brief.security.sec_id) / \
                        update_strat_status_obj.total_fill_buy_qty
                case Side.SELL:
                    update_strat_status_obj.total_open_sell_qty -= order_snapshot_obj.last_update_fill_qty
                    update_strat_status_obj.total_open_sell_notional -= \
                        (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                                   order_snapshot_obj.order_brief.security.sec_id))
                    if update_strat_status_obj.total_open_sell_qty == 0:
                        update_strat_status_obj.avg_open_sell_px = 0
                    else:
                        update_strat_status_obj.avg_open_sell_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_open_sell_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            update_strat_status_obj.total_open_sell_qty
                    update_strat_status_obj.total_fill_sell_qty += order_snapshot_obj.last_update_fill_qty
                    update_strat_status_obj.total_fill_sell_notional += \
                        order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                            order_snapshot_obj.last_update_fill_px,
                            order_snapshot_obj.order_brief.security.sec_id)
                    update_strat_status_obj.avg_fill_sell_px = \
                        self.get_local_px_or_notional(update_strat_status_obj.total_fill_sell_notional,
                                                      order_snapshot_obj.order_brief.security.sec_id) / \
                        update_strat_status_obj.total_fill_sell_qty
                case other_:
                    err_str_ = f"Unsupported Side Type {other_} received for order_snapshot_key: " \
                               f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                               f"order_snapshot: {order_snapshot_obj}"
                    logging.error(err_str_)
                    return
            update_strat_status_obj.total_open_exposure = (update_strat_status_obj.total_open_buy_notional -
                                                           update_strat_status_obj.total_open_sell_notional)
            update_strat_status_obj.total_fill_exposure = (update_strat_status_obj.total_fill_buy_notional -
                                                           update_strat_status_obj.total_fill_sell_notional)
            if update_strat_status_obj.total_fill_buy_notional < update_strat_status_obj.total_fill_sell_notional:
                update_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - update_strat_status_obj.total_fill_buy_notional
            else:
                update_strat_status_obj.balance_notional = \
                    strat_limits.max_cb_notional - update_strat_status_obj.total_fill_sell_notional

            updated_residual = await self.__get_residual_obj(order_snapshot_obj.order_brief.side, strat_brief_obj)
            if updated_residual is not None:
                update_strat_status_obj.residual = updated_residual

            # Updating strat_state as paused if limits get breached
            self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                 strat_brief_obj, symbol_side_snapshot)

            from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
                underlying_partial_update_strat_status_http)

            await underlying_partial_update_strat_status_http(json.loads(
                update_strat_status_obj.json(by_alias=True, exclude_none=True)))
        else:
            logging.error(f"error: either strat_status or strat_limits received as None;;; "
                          f"strat_status: {update_strat_status_obj}, strat_limits: {strat_limits}")
            return

    async def _delete_symbol_side_snapshot_from_unload_strat(self) -> bool:
        pair_symbol_side_list = [
            (self.strat_leg_1.sec, self.strat_leg_1.side),
            (self.strat_leg_2.sec, self.strat_leg_2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots = await self._get_symbol_side_snapshot_from_symbol_side(security.sec_id, side)

            if len(symbol_side_snapshots) == 1:
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_delete_symbol_side_snapshot_http
                symbol_side_snapshot = symbol_side_snapshots[0]
                await underlying_delete_symbol_side_snapshot_http(symbol_side_snapshot.id)
            elif len(symbol_side_snapshots) > 1:
                err_str_ = f"SymbolSideSnapshot must be one per symbol and side, symbol_side_key: " \
                           f"{get_symbol_side_key([(security.sec_id, side)])};;; symbol_side_snapshot: " \
                           f"{symbol_side_snapshots}"
                logging.error(err_str_)
                return False
            else:
                err_str_ = f"Could not find symbol_side_snapshot for symbol_side_key " \
                           f"{get_symbol_side_key([(security.sec_id, side)])}, " \
                           f"must be present already to be deleted while strat unload"
                logging.error(err_str_)
                return False
        return True

    async def _delete_strat_brief_for_unload_strat(self) -> bool:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_strat_brief_http, underlying_delete_strat_brief_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_strat_brief_from_symbol

        # since strat_brief has both symbols present in current strat,
        # so any symbol will give same strat_brief
        symbol = self.strat_leg_1.sec.sec_id
        strat_brief_objs_list = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(symbol),
                                                                       self.get_generic_read_route())

        if len(strat_brief_objs_list) > 1:
            err_str_ = (f"strat_brief must be only one per symbol, symbol_side_key: "
                        f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                        f"strat_brief_list: {strat_brief_objs_list}")
            logging.error(err_str_)
            return False
        elif len(strat_brief_objs_list) == 1:
            strat_brief_obj = strat_brief_objs_list[0]
            await underlying_delete_strat_brief_http(strat_brief_obj.id)
            return True
        else:
            err_str_ = (f"Could not find any strat_brief with symbol {symbol} already existing to be deleted "
                        f"while strat unload, symbol_side_key: "
                        f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
            return False

    async def _force_unpublish_symbol_overview_from_unload_strat(self) -> bool:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_partial_update_symbol_overview_http, underlying_get_symbol_overview_from_symbol_query_http

        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]

        for symbol in symbols_list:
            symbol_overview_obj_list = await underlying_get_symbol_overview_from_symbol_query_http(symbol)

            if len(symbol_overview_obj_list) != 0:
                if len(symbol_overview_obj_list) == 1:
                    updated_symbol_overview = FxSymbolOverviewBaseModel(_id=symbol_overview_obj_list[0].id,
                                                                        force_publish=False)
                    await underlying_partial_update_symbol_overview_http(
                        jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True))
                else:
                    err_str_ = (f"symbol_overview must be one per symbol, symbol_side_key: "
                                f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
                                f";;; symbol_overview_list: {symbol_overview_obj_list}")
                    logging.error(err_str_)
                    return False
            else:
                err_str_ = (f"Could not find symbol_overview for symbol {symbol} while unloading strat, "
                            f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
                logging.error(err_str_)
                return False
        return True

    ############################
    # TradingDataManager updates
    ############################

    async def partial_update_order_journal_post(self, stored_order_journal_obj: OrderJournal,
                                                updated_order_journal_obj: OrderJournalOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_order_journal_get_all_ws(updated_order_journal_obj)

    async def create_order_snapshot_post(self, order_snapshot_obj: OrderSnapshot):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_order_snapshot_get_all_ws(order_snapshot_obj)

    async def update_order_snapshot_post(self, stored_order_snapshot_obj: OrderSnapshot,
                                         updated_order_snapshot_obj: OrderSnapshot):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_order_snapshot_get_all_ws(updated_order_snapshot_obj)

    async def partial_update_order_snapshot_post(self, stored_order_snapshot_obj: OrderSnapshot,
                                                 updated_order_snapshot_obj: OrderSnapshotOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_order_snapshot_get_all_ws(updated_order_snapshot_obj)

    async def create_top_of_book_post(self, top_of_book_obj: TopOfBook):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_top_of_book_get_all_ws(top_of_book_obj)

    async def create_all_top_of_book_post(self, top_of_book_obj_list: List[TopOfBook]):
        # updating trading_data_manager's strat_cache
        for top_of_book_obj in top_of_book_obj_list:
            self.trading_data_manager.handle_top_of_book_get_all_ws(top_of_book_obj)

    async def update_top_of_book_post(self, stored_top_of_book_obj: TopOfBook, updated_top_of_book_obj: TopOfBook):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_top_of_book_get_all_ws(updated_top_of_book_obj)

    async def update_all_top_of_book_post(self, stored_top_of_book_obj_list: List[TopOfBook],
                                          updated_top_of_book_obj_list: List[TopOfBook]):
        # updating trading_data_manager's strat_cache
        for top_of_book_obj in updated_top_of_book_obj_list:
            self.trading_data_manager.handle_top_of_book_get_all_ws(top_of_book_obj)

    async def partial_update_top_of_book_post(self, stored_top_of_book_obj: TopOfBook,
                                              updated_top_of_book_obj: TopOfBookOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_top_of_book_get_all_ws(updated_top_of_book_obj)

    async def partial_update_all_top_of_book_post(self, stored_top_of_book_obj_list: List[TopOfBook],
                                                  updated_top_of_book_obj_list: List[TopOfBookOptional]):
        # updating trading_data_manager's strat_cache
        for top_of_book_obj in updated_top_of_book_obj_list:
            self.trading_data_manager.handle_top_of_book_get_all_ws(top_of_book_obj)

    async def partial_update_fills_journal_post(self, stored_fills_journal_obj: FillsJournal,
                                                updated_fills_journal_obj: FillsJournalOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_fills_journal_get_all_ws(updated_fills_journal_obj)

    async def create_strat_brief_post(self, strat_brief_obj: StratBrief):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_brief_get_all_ws(strat_brief_obj)

    async def update_strat_brief_post(self, stored_strat_brief_obj: StratBrief, updated_strat_brief_obj: StratBrief):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_brief_get_all_ws(updated_strat_brief_obj)

    async def partial_update_strat_brief_post(self, stored_strat_brief_obj: StratBrief,
                                              updated_strat_brief_obj: StratBriefOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_brief_get_all_ws(updated_strat_brief_obj)

    async def create_strat_status_post(self, strat_status_obj: StratStatus):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_status_get_all_ws(strat_status_obj)

    async def create_strat_limits_post(self, strat_limits_obj: StratLimits):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(strat_limits_obj)

    async def update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                       updated_strat_limits_obj: StratLimits):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

    async def partial_update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                               updated_strat_limits_obj: StratLimitsOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

    async def create_new_order_post(self, new_order_obj: NewOrder):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_new_order_get_all_ws(new_order_obj)

    async def create_cancel_order_post(self, cancel_order_obj: CancelOrder):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_cancel_order_get_all_ws(cancel_order_obj)

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        symbol_overview_obj.force_publish = False  # setting it false if at create is it True
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)

    async def update_symbol_overview_post(self, stored_symbol_overview_obj: SymbolOverview,
                                          updated_symbol_overview_obj: SymbolOverview):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_overview_get_all_ws(updated_symbol_overview_obj)

    async def partial_update_symbol_overview_post(self, stored_symbol_overview_obj: SymbolOverview,
                                                  updated_symbol_overview_obj: SymbolOverviewOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_overview_get_all_ws(updated_symbol_overview_obj)

    async def create_all_symbol_overview_post(self, symbol_overview_obj_list: List[SymbolOverview]):
        # updating trading_data_manager's strat_cache
        for symbol_overview_obj in symbol_overview_obj_list:
            symbol_overview_obj.force_publish = False   # setting it false if at create it is True
            if self.trading_data_manager:
                self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
            # else not required: since symbol overview is required to make executor service ready,
            #                    will add this to strat_cache explicitly using http call

    async def update_all_symbol_overview_post(self, stored_symbol_overview_obj_list: List[SymbolOverview],
                                              updated_symbol_overview_obj_list: List[SymbolOverview]):
        # updating trading_data_manager's strat_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)

    async def partial_update_all_symbol_overview_post(self, stored_symbol_overview_obj_list: List[SymbolOverview],
                                                      updated_symbol_overview_obj_list: List[SymbolOverviewOptional]):
        # updating trading_data_manager's strat_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)

    #####################
    # Query Pre/Post handling
    #####################

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(self, symbol_side_snapshot_class_type: Type[
        SymbolSideSnapshot], security_id: str, side: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_side_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_side_snapshot_from_symbol_side
        symbol_side_snapshot_objs = await underlying_read_symbol_side_snapshot_http(
            get_symbol_side_snapshot_from_symbol_side(security_id, side), self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) > 1:
            err_str_ = f"Found multiple objects of symbol_side_snapshot for key: " \
                       f"{get_symbol_side_key([(security_id, side)])}"
            logging.error(err_str_)

        return symbol_side_snapshot_objs

    async def update_residuals_query_pre(self, pair_strat_class_type: Type[StratStatus], security_id: str, side: Side,
                                         residual_qty: int):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            (journal_shared_lock, underlying_read_strat_brief_http, underlying_partial_update_strat_brief_http,
             underlying_partial_update_strat_status_http)
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_strat_brief_from_symbol

        async with (journal_shared_lock):
            # updating residual qty
            strat_brief_objs = await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id),
                                                                      self.get_generic_read_route())

            if len(strat_brief_objs) == 1:
                strat_brief_obj = strat_brief_objs[0]
                if side == Side.BUY:
                    update_trading_side_brief = \
                        PairSideTradingBriefOptional(
                            residual_qty=strat_brief_obj.pair_buy_side_trading_brief.residual_qty + residual_qty)
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_buy_side_trading_brief=update_trading_side_brief)

                else:
                    update_trading_side_brief = \
                        PairSideTradingBriefOptional(
                            residual_qty=strat_brief_obj.pair_sell_side_trading_brief.residual_qty + residual_qty)
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_sell_side_trading_brief=update_trading_side_brief)

                updated_strat_brief = await underlying_partial_update_strat_brief_http(
                    json.loads(update_strat_brief.json(by_alias=True, exclude_none=True)))
            else:
                err_str_ = f"StratBrief must be one per symbol, received {len(strat_brief_objs)} " \
                           f"for symbol_side_key: {get_symbol_side_key([(security_id, side)])};;;" \
                           f"StratBriefs: {strat_brief_objs}"
                logging.exception(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # updating pair_strat's residual notional
            strat_status = await self._get_strat_status()
            if strat_status is not None:
                updated_residual = await self.__get_residual_obj(side, updated_strat_brief)
                if updated_residual is not None:
                    strat_status = StratStatusOptional(_id=strat_status.id, residual=updated_residual)
                    await underlying_partial_update_strat_status_http(
                        jsonable_encoder(strat_status, by_alias=True, exclude_none=True)
                    )
                else:
                    err_str_ = f"Something went wrong while computing residual for security_side_key: " \
                               f"{get_symbol_side_key([(security_id, side)])}"
                    logging.exception(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)

            # nothing to send since this query updates residuals only
            return []

    async def get_open_order_count_query_pre(self, open_order_count_class_type: Type[OpenOrderCount], symbol: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_open_order_snapshots_for_symbol

        open_orders = await underlying_read_order_snapshot_http(get_open_order_snapshots_for_symbol(symbol),
                                                                self.get_generic_read_route())

        open_order_count = OpenOrderCount(open_order_count=len(open_orders))
        return [open_order_count]

    async def get_underlying_account_cumulative_fill_qty_query_pre(
            self, underlying_account_cum_fill_qty_class_type: Type[UnderlyingAccountCumFillQty],
            symbol: str, side: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http
        fill_journal_obj_list = await get_symbol_side_underlying_account_cumulative_fill_qty_query_http(symbol, side)

        underlying_accounts: Set[str] = set()
        underlying_accounts_cum_fill_qty_obj: UnderlyingAccountCumFillQty = UnderlyingAccountCumFillQty(
            underlying_account_n_cumulative_fill_qty=[]
        )
        for fill_journal_obj in fill_journal_obj_list:
            if (underlying_acc := fill_journal_obj.underlying_account) not in underlying_accounts:
                underlying_accounts.add(underlying_acc)
                underlying_accounts_cum_fill_qty_obj.underlying_account_n_cumulative_fill_qty.append(
                    UnderlyingAccountNCumFillQty(underlying_account=underlying_acc,
                                                 cumulative_qty=fill_journal_obj.underlying_account_cumulative_fill_qty)
                )
        return [underlying_accounts_cum_fill_qty_obj]

    async def get_symbol_side_underlying_account_cumulative_fill_qty_query_pre(
            self, fills_journal_class_type: Type[FillsJournal], symbol: str, side: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_fills_journal_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import \
            get_symbol_side_underlying_account_cumulative_fill_qty
        return await underlying_read_fills_journal_http(
            get_symbol_side_underlying_account_cumulative_fill_qty(symbol, side), self.get_generic_read_route())

    async def get_last_n_sec_orders_by_event_query_pre(self, order_journal_class_type: Type[OrderJournal],
                                                       symbol: str | None, last_n_sec: int, order_event: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_last_n_sec_orders_by_event
        return await underlying_read_order_journal_http(get_last_n_sec_orders_by_event(symbol, last_n_sec, order_event),
                                                        self.get_generic_read_route())

    async def trigger_residual_check_query_pre(self, order_snapshot_class_type: Type[OrderSnapshot],
                                               order_status: List[str]):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_snapshot_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_open_order_snapshots_by_order_status

        return await underlying_read_order_snapshot_http(get_open_order_snapshots_by_order_status(order_status),
                                                         self.get_generic_read_route())

    async def cxl_expired_open_orders(self, order_snapshot_obj_list: List[OrderSnapshot]):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_create_cancel_order_http
        for order_snapshot in order_snapshot_obj_list:

            strat_limits: StratLimits = await self._get_strat_limits()

            time_delta = DateTime.utcnow() - order_snapshot.create_date_time
            if strat_limits is not None and (time_delta.total_seconds() >
                                             strat_limits.residual_restriction.residual_mark_seconds):
                cancel_order: CancelOrder = CancelOrder(order_id=order_snapshot.order_brief.order_id,
                                                        security=order_snapshot.order_brief.security,
                                                        side=order_snapshot.order_brief.side,
                                                        cxl_confirmed=False)
                # trigger cancel if it does not already exist for this order id, otherwise log for alert
                from Flux.CodeGenProjects.strat_executor.app.aggregate import get_order_by_order_id_filter
                from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
                    underlying_read_cancel_order_http
                cxl_order_list: List[CancelOrder] | None = await underlying_read_cancel_order_http(
                    get_order_by_order_id_filter(cancel_order.order_id), self.get_generic_read_route())
                if not cxl_order_list:
                    await underlying_create_cancel_order_http(cancel_order)
                else:
                    if len(cxl_order_list) == 1:
                        if not cxl_order_list[0].cxl_confirmed:
                            logging.error(f"cxl_expired_open_orders failed: Prior cxl request found in DB for this "
                                          f"order-id: {cancel_order.order_id}, use swagger to delete this order-id "
                                          f"from DB to trigger cxl request again, order_snapshot_key: "
                                          f"{get_order_snapshot_log_key(order_snapshot)};;;order_snapshot: "
                                          f"{order_snapshot}")
                    else:
                        logging.error(f"There must be only one cancel_order obj per order_id, received "
                                      f"{cxl_order_list} for order_id {order_snapshot.order_brief.order_id}, "
                                      f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot)}")
            # else not required: If pair_strat_obj is None or If time-delta is still less than
            # residual_mark_seconds then avoiding cancellation of order

    async def trigger_residual_check_query_post(self, order_snapshot_obj_list_: List[OrderSnapshot]):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_order_journal_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_last_n_sec_orders_by_event

        # 1. cancel any expired from passed open orders
        await self.cxl_expired_open_orders(order_snapshot_obj_list_)

        # 2. If specified interval rejected orders count exceed threshold - trigger kill switch
        # get limit from portfolio limits
        portfolio_limits_obj: PortfolioLimitsBaseModel = (
            strat_manager_service_http_client.get_portfolio_limits_client(portfolio_limits_id=1))
        max_allowed_rejection_within_period = portfolio_limits_obj.rolling_max_reject_count.max_rolling_tx_count
        period_in_sec = portfolio_limits_obj.rolling_max_reject_count.rolling_tx_count_period_seconds
        order_count_updated_order_journals: List[OrderJournal] = \
            await underlying_read_order_journal_http(get_last_n_sec_orders_by_event(None, period_in_sec, "OE_REJ"),
                                                     self.get_generic_read_route())
        if len(order_count_updated_order_journals) == 1:
            if order_count_updated_order_journals[0].current_period_order_count > max_allowed_rejection_within_period:
                logging.debug(f"max_allowed_rejection_within_period breached found : "
                              f"{order_count_updated_order_journals[0].current_period_order_count} "
                              f"rejections in past period - initiating auto-kill switch")
                # single top level objects are hardcoded id=1 , saves the query portfolio status, if always id=1
                portfolio_status: PortfolioStatusOptional = PortfolioStatusOptional(id=1,
                                                                                    kill_switch=True)
                strat_manager_service_http_client.patch_portfolio_status_client(
                    json.loads(portfolio_status.json(by_alias=True, exclude_none=True)))
        elif len(order_count_updated_order_journals) != 0:
            err_str_ = "Must receive only one object from get_last_n_sec_orders_by_event_query, " \
                       f"received: {order_count_updated_order_journals}"
            logging.error(err_str_)
        # else not required - no rejects found - no action

        # 3. No one expects anything useful to be returned - just return empty list
        return []

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_strat_brief_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_strat_brief_from_symbol

        return await underlying_read_strat_brief_http(get_strat_brief_from_symbol(security_id),
                                                      self.get_generic_read_route())

    async def get_executor_check_snapshot_query_pre(
            self, executor_check_snapshot_class_type: Type[ExecutorCheckSnapshot], symbol: str,
            side: Side, last_n_sec: int):

        last_n_sec_order_qty = await self.get_last_n_sec_order_qty(symbol, side, last_n_sec)
        logging.debug(f"Received last_n_sec_order_qty: {last_n_sec_order_qty}, symbol: {symbol}, side: {Side}")

        last_n_sec_trade_qty = await self.get_last_n_sec_trade_qty(symbol, side)
        logging.debug(f"Received last_n_sec_trade_qty: {last_n_sec_trade_qty}, symbol: {symbol}, side: {Side}")

        rolling_new_order_count = await self.get_rolling_new_order_count(symbol)
        logging.debug(f"Received rolling_new_order_count: {rolling_new_order_count}, symbol: {symbol}, side: {Side}")

        if last_n_sec_order_qty is not None and \
                last_n_sec_trade_qty is not None and \
                rolling_new_order_count is not None:
            # if no data is found by respective queries then all fields are set to 0 and every call returns
            # executor_check_snapshot object (except when exception occurs)
            executor_check_snapshot = \
                ExecutorCheckSnapshot(last_n_sec_trade_qty=last_n_sec_trade_qty,
                                      last_n_sec_order_qty=last_n_sec_order_qty,
                                      rolling_new_order_count=rolling_new_order_count)
            return [executor_check_snapshot]
        else:
            # will only return [] if some error occurred
            logging.error(f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}, "
                          f"Received last_n_sec_order_qty - {last_n_sec_order_qty}, "
                          f"last_n_sec_trade_qty - {last_n_sec_trade_qty}, "
                          f"rolling_new_order_count - {rolling_new_order_count} and  last_n_sec - {last_n_sec}")
            return []

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_symbol_overview_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_symbol_overview_from_symbol
        return await underlying_read_symbol_overview_http(get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_top_of_book_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_objs_from_symbol
        return await underlying_read_top_of_book_http(get_objs_from_symbol(symbol))

    async def get_last_n_sec_total_qty_query_pre(self,
                                                 last_sec_market_trade_vol_class_type: Type[LastNSecMarketTradeVol],
                                                 symbol: str, last_n_sec: int) -> List[LastNSecMarketTradeVol]:
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import \
            underlying_read_last_trade_http
        from Flux.CodeGenProjects.strat_executor.app.aggregate import get_last_n_sec_total_qty
        last_trade_obj_list = await underlying_read_last_trade_http(get_last_n_sec_total_qty(symbol, last_n_sec))
        last_n_sec_trade_vol = 0
        if last_trade_obj_list:
            last_n_sec_trade_vol = \
                last_trade_obj_list[-1].market_trade_volume.participation_period_last_trade_qty_sum

        return [LastNSecMarketTradeVol(last_n_sec_trade_vol=last_n_sec_trade_vol)]

    async def is_strat_ongoing_query_pre(self, strat_details_class_type: Type[StratDetails]):
        strat_status = await self._get_strat_status()

        if strat_status:
            strat_details: StratDetails = StratDetails(is_ongoing=is_ongoing_strat(strat_status),
                                                       current_state=strat_status.strat_state)
            return [strat_details]
        return []

    async def put_strat_to_snooze_query_pre(self, strat_status_class_type: Type[StratStatus]):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_is_strat_ongoing_query_http)

        strat_details_list: List[StratDetails] = await underlying_is_strat_ongoing_query_http()
        if strat_details_list:
            strat_details = strat_details_list[0]
        else:
            err_str_ = ("Received empty strat_details list from underlying_is_strat_ongoing_query_http call "
                        f"of strat_executor for port {self.port}, ignoring setting this strat snooze process, "
                        f"symbol_side_key: "
                        f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
            raise HTTPException(status_code=500, detail=err_str_)

        # removing current strat limits
        res = await self._remove_strat_limits()
        if not res:
            err_str_ = "Some Error occurred while removing strat_limits in snoozing strat process"
            raise HTTPException(detail=err_str_, status_code=500)

        if strat_details.current_state == StratState.StratState_DONE:
            # deleting strat's both leg's symbol_side_snapshots
            res = await self._delete_symbol_side_snapshot_from_unload_strat()
            if not res:
                err_str_ = "Some Error occurred while removing symbol_side_snapshot in snoozing strat process"
                raise HTTPException(detail=err_str_, status_code=500)

            # deleting strat's strat_brief
            res = await self._delete_strat_brief_for_unload_strat()
            if not res:
                err_str_ = "Some Error occurred while removing strat_brief in snoozing strat process"
                raise HTTPException(detail=err_str_, status_code=500)

            # making force publish flag back to false for current strat's symbol's symbol_overview
            res = await self._force_unpublish_symbol_overview_from_unload_strat()
            if not res:
                err_str_ = "Some Error occurred while updating strat_overview in snoozing strat process"
                raise HTTPException(detail=err_str_, status_code=500)

        # Updating strat_state to SNOOZED and setting default values of strat_status
        snoozed_strat_status = await self._snooze_strat_status()
        if not snoozed_strat_status:
            err_str_ = "Some Error occurred while updating strat_status in snoozing strat process"
            raise HTTPException(detail=err_str_, status_code=500)

        # # taking time for strat_alert patch to publish last generated alerts
        # time.sleep(strat_alert_bulk_update_timeout*2)

        # removing strat_alert
        try:
            log_analyzer_service_http_client.delete_strat_alert_client(snoozed_strat_status.id)
        except Exception as e:
            err_str_ = f"Some Error occurred while removing strat_alerts in snoozing strat process, exception: {e}"
            raise HTTPException(detail=err_str_, status_code=500)

        # cleaning executor config.yaml file
        try:
            os.remove(self.simulate_config_yaml_file_path)
        except Exception as e:
            err_str_ = (f"Something went wrong while deleting executor_{self.pair_strat_id}_simulate_config.yaml, "
                        f"exception: {e}")
            logging.error(err_str_)

        return []

    #########################
    # Trade Simulator Queries
    #########################

    async def trade_simulator_place_new_order_query_pre(
            self, trade_simulator_process_new_order_class_type: Type[TradeSimulatorProcessNewOrder],
            px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
            underlying_account: str, exchange: str | None = None):
        await TradeSimulator.place_new_order(px, qty, side, trading_sec_id, system_sec_id, underlying_account, exchange)
        return []

    async def trade_simulator_place_cxl_order_query_pre(
            self, trade_simulator_process_cxl_order_class_type: Type[TradeSimulatorProcessCxlOrder],
            order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
            system_sec_id: str | None = None, underlying_account: str | None = None):
        await TradeSimulator.place_cxl_order(order_id, side, trading_sec_id, system_sec_id, underlying_account)
        return []

    async def trade_simulator_process_order_ack_query_pre(
            self, trade_simulator_process_order_ack_class_type: Type[TradeSimulatorProcessOrderAck], order_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        await TradeSimulator.process_order_ack(order_id, px, qty, side, sec_id, underlying_account)
        return []

    async def trade_simulator_process_fill_query_pre(
            self, trade_simulator_process_fill_class_type: Type[TradeSimulatorProcessFill], order_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        await TradeSimulator.process_fill(order_id, px, qty, side, sec_id, underlying_account)
        return []

    async def trade_simulator_reload_config_query_pre(
            self, trade_simulator_reload_config_class_type: Type[TradeSimulatorReloadConfig]):
        TradeSimulator.reload_symbol_configs()
        return []

    ###################
    # Filter WS queries
    ###################

    async def filtered_notify_tob_update_query_ws_pre(self):
        return tob_filter_callable

    async def filtered_notify_order_journal_update_query_ws_pre(self):
        return filter_ws_order_journal

    async def filtered_notify_order_snapshot_update_query_ws_pre(self):
        return filter_ws_order_snapshot

    async def filtered_notify_symbol_side_snapshot_update_query_ws_pre(self):
        return filter_ws_symbol_side_snapshot

    async def filtered_notify_fills_journal_update_query_ws_pre(self):
        return filter_ws_fills_journal

    async def filtered_notify_strat_brief_update_query_ws_pre(self):
        return filter_ws_strat_brief


def filter_ws_order_journal(order_journal_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    order = order_journal_obj_json.get("order")
    if order is not None:
        security = order.get("security")
        if security is not None:
            sec_id = security.get("sec_id")
            if sec_id is not None:
                if sec_id in symbols:
                    return True
    return False


def filter_ws_order_snapshot(order_snapshot_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    order = order_snapshot_obj_json.get("order")
    if order is not None:
        security = order.get("security")
        if security is not None:
            sec_id = security.get("sec_id")
            if sec_id is not None:
                if sec_id in symbols:
                    return True
    return False


def filter_ws_symbol_side_snapshot(symbol_side_snapshot_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    security = symbol_side_snapshot_obj_json.get("security")
    if security is not None:
        sec_id = security.get("sec_id")
        if sec_id is not None:
            if sec_id == symbols:
                return True
    return False


def filter_ws_fills_journal(fills_journal_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    fill_symbol = fills_journal_obj_json.get("fill_symbol")
    if fill_symbol is not None:
        if fill_symbol == symbols:
            return True
    return False


def filter_ws_strat_brief(strat_brief_obj_json: Dict, **kwargs):
    symbols = kwargs.get("symbols")
    pair_buy_side_trading_brief = strat_brief_obj_json.get("pair_buy_side_trading_brief")
    pair_sell_side_trading_brief = strat_brief_obj_json.get("pair_sell_side_trading_brief")
    if pair_buy_side_trading_brief is not None and pair_sell_side_trading_brief is not None:
        security_buy = pair_buy_side_trading_brief.get("security")
        security_sell = pair_sell_side_trading_brief.get("security")
        if security_buy is not None and security_sell is not None:
            sec1_id = security_buy.get("sec_id")
            sec2_id = security_sell.get("sec_id")
            if sec1_id in symbols or sec2_id in symbols:
                return True
    return False


def tob_filter_callable(tob_obj_json_str, **kwargs):
    symbols = kwargs.get("symbols")
    tob_obj_json = json.loads(tob_obj_json_str)
    tob_symbol = tob_obj_json.get("symbol")
    if tob_symbol in symbols:
        return True
    return False
