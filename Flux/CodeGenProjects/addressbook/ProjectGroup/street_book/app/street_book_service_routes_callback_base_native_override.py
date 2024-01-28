# standard imports
import logging
import threading
import time
import copy
import shutil
import sys
import stat
import subprocess
from typing import Set

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_routes_callback import (
    StreetBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_order_journal_log_key, get_symbol_side_key, get_order_snapshot_log_key,
    get_symbol_side_snapshot_log_key, all_service_up_check, host, EXECUTOR_PROJECT_DATA_DIR,
    strat_manager_service_http_client, get_consumable_participation_qty,
    get_strat_brief_log_key, get_fills_journal_log_key, get_new_strat_limits, get_new_strat_status,
    log_analyzer_service_http_client, executor_config_yaml_dict,
    EXECUTOR_PROJECT_SCRIPTS_DIR, post_trade_engine_service_http_client)
from FluxPythonUtils.scripts.utility_functions import (
    avg_of_new_val_sum_to_avg, find_free_port, except_n_log_alert, create_logger)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.app.pair_strat_engine_service_helper import (
    create_md_shell_script, MDShellEnvData, PairStratBaseModel, StratState, is_ongoing_strat,
    guaranteed_call_pair_strat_client, pair_strat_client_call_log_str, UpdateType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book import StreetBook, TradingDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.trade_simulator import TradeSimulator, TradingLinkBase
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_analyzer.generated.Pydentic.log_analyzer_service_model_imports import StratAlertBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.strat_cache import StratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.generated.StreetBook.strat_manager_service_key_handler import (
    StratManagerServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_order_total_sum_of_last_n_sec, get_symbol_side_snapshot_from_symbol_side, get_strat_brief_from_symbol,
    get_open_order_snapshots_for_symbol, get_symbol_side_underlying_account_cumulative_fill_qty,
    get_symbol_overview_from_symbol, get_last_n_sec_total_trade_qty, get_market_depths,
    get_last_n_order_journals_from_order_id)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_trade_engine.generated.Pydentic.post_trade_engine_service_model_imports import (
    PortfolioStatusUpdatesContainer)
from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import (
    StratLeg, FxSymbolOverviewBaseModel, StratViewBaseModel)

def get_pair_strat_id_from_cmd_argv():
    if len(sys.argv) > 2:
        pair_strat_id = sys.argv[1]
        is_crash_recovery: bool = False
        if len(sys.argv) == 4:
            try:
                is_crash_recovery = bool(parse_to_int(sys.argv[2]))
            except ValueError as e:
                err_str_ = (f"Provided cmd argument is_crash_recovery is not valid type, "
                            f"must be numeric, exception: {e}")
                logging.error(err_str_)
                raise Exception(err_str_)
        try:
            return parse_to_int(pair_strat_id), is_crash_recovery
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


class StreetBookServiceRoutesCallbackBaseNativeOverride(StreetBookServiceRoutesCallback):
    residual_compute_shared_lock: AsyncRLock | None = None
    journal_shared_lock: AsyncRLock | None = None
    underlying_read_strat_brief_http: Callable[..., Any] | None = None
    underlying_create_strat_limits_http: Callable[..., Any] | None = None
    underlying_delete_strat_limits_http: Callable[..., Any] | None = None
    underlying_create_strat_status_http: Callable[..., Any] | None = None
    underlying_update_strat_status_http: Callable[..., Any] | None = None
    underlying_get_executor_check_snapshot_query_http: Callable[..., Any] | None = None
    underlying_create_strat_brief_http: Callable[..., Any] | None = None
    underlying_read_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_create_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_overview_http: Callable[..., Any] | None = None
    underlying_read_strat_limits_by_id_http: Callable[..., Any] | None = None
    underlying_read_symbol_overview_http: Callable[..., Any] | None = None
    underlying_read_top_of_book_http: Callable[..., Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_read_order_snapshot_http: Callable[..., Any] | None = None
    underlying_read_order_journal_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_total_trade_qty_query_http: Callable[..., Any] | None = None
    get_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_create_order_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_order_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_cancel_order_http: Callable[..., Any] | None = None
    underlying_partial_update_strat_status_http: Callable[..., Any] | None = None
    underlying_get_open_order_count_query_http: Callable[..., Any] | None = None
    underlying_partial_update_strat_brief_http: Callable[..., Any] | None = None
    underlying_delete_symbol_side_snapshot_http: Callable[..., Any] | None = None
    get_symbol_side_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_read_fills_journal_http: Callable[..., Any] | None = None
    underlying_read_last_trade_http: Callable[..., Any] | None = None
    underlying_is_strat_ongoing_query_http: Callable[..., Any] | None = None
    underlying_delete_strat_brief_http: Callable[..., Any] | None = None
    underlying_create_cancel_order_http: Callable[..., Any] | None = None
    underlying_read_market_depth_http: Callable[..., Any] | None = None
    underlying_read_strat_status_http: Callable[..., Any] | None = None
    underlying_read_strat_status_by_id_http: Callable[..., Any] | None = None
    underlying_read_cancel_order_http: Callable[..., Any] | None = None
    underlying_read_strat_limits_http: Callable[..., Any] | None = None
    underlying_delete_strat_status_http: Callable[..., Any] | None = None
    underlying_trade_simulator_place_cxl_order_query_http: Callable[..., Any] | None = None
    underlying_read_strat_view_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes import (
            underlying_read_strat_brief_http, residual_compute_shared_lock, journal_shared_lock,
            underlying_create_strat_limits_http, underlying_delete_strat_limits_http,
            underlying_create_strat_status_http, underlying_update_strat_status_http,
            underlying_get_executor_check_snapshot_query_http, underlying_create_strat_brief_http,
            underlying_read_symbol_side_snapshot_http, underlying_create_symbol_side_snapshot_http,
            underlying_partial_update_symbol_overview_http, underlying_read_strat_limits_by_id_http,
            underlying_read_symbol_overview_http, underlying_create_cancel_order_http,
            underlying_read_top_of_book_http, underlying_get_top_of_book_from_symbol_query_http,
            underlying_read_order_snapshot_http, underlying_read_order_journal_http,
            underlying_get_last_n_sec_total_trade_qty_query_http, underlying_partial_update_cancel_order_http,
            get_underlying_account_cumulative_fill_qty_query_http, underlying_create_order_snapshot_http,
            underlying_partial_update_order_snapshot_http, underlying_partial_update_symbol_side_snapshot_http,
            underlying_partial_update_strat_status_http, underlying_get_open_order_count_query_http,
            underlying_partial_update_strat_brief_http, underlying_delete_symbol_side_snapshot_http,
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http, underlying_read_fills_journal_http,
            underlying_read_last_trade_http,
            underlying_delete_strat_brief_http, underlying_read_market_depth_http, underlying_read_strat_status_http,
            underlying_read_strat_status_by_id_http, underlying_read_cancel_order_http,
            underlying_read_strat_limits_http, underlying_delete_strat_status_http,
            underlying_trade_simulator_place_cxl_order_query_http)

        cls.residual_compute_shared_lock = residual_compute_shared_lock
        cls.journal_shared_lock = journal_shared_lock
        cls.underlying_read_strat_brief_http = underlying_read_strat_brief_http
        cls.underlying_create_strat_limits_http = underlying_create_strat_limits_http
        cls.underlying_delete_strat_limits_http = underlying_delete_strat_limits_http
        cls.underlying_create_strat_status_http = underlying_create_strat_status_http
        cls.underlying_update_strat_status_http = underlying_update_strat_status_http
        cls.underlying_get_executor_check_snapshot_query_http = underlying_get_executor_check_snapshot_query_http
        cls.underlying_create_strat_brief_http = underlying_create_strat_brief_http
        cls.underlying_read_symbol_side_snapshot_http = underlying_read_symbol_side_snapshot_http
        cls.underlying_create_symbol_side_snapshot_http = underlying_create_symbol_side_snapshot_http
        cls.underlying_partial_update_symbol_overview_http = underlying_partial_update_symbol_overview_http
        cls.underlying_read_strat_limits_by_id_http = underlying_read_strat_limits_by_id_http
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_read_order_snapshot_http = underlying_read_order_snapshot_http
        cls.underlying_read_order_journal_http = underlying_read_order_journal_http
        cls.underlying_get_last_n_sec_total_trade_qty_query_http = underlying_get_last_n_sec_total_trade_qty_query_http
        cls.get_underlying_account_cumulative_fill_qty_query_http = (
            get_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_create_order_snapshot_http = underlying_create_order_snapshot_http
        cls.underlying_partial_update_order_snapshot_http = underlying_partial_update_order_snapshot_http
        cls.underlying_partial_update_symbol_side_snapshot_http = underlying_partial_update_symbol_side_snapshot_http
        cls.underlying_partial_update_cancel_order_http = underlying_partial_update_cancel_order_http
        cls.underlying_partial_update_strat_status_http = underlying_partial_update_strat_status_http
        cls.underlying_get_open_order_count_query_http = underlying_get_open_order_count_query_http
        cls.underlying_partial_update_strat_brief_http = underlying_partial_update_strat_brief_http
        cls.underlying_delete_symbol_side_snapshot_http = underlying_delete_symbol_side_snapshot_http
        cls.get_symbol_side_underlying_account_cumulative_fill_qty_query_http = (
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_read_fills_journal_http = underlying_read_fills_journal_http
        cls.underlying_read_last_trade_http = underlying_read_last_trade_http
        cls.underlying_read_strat_brief_http = underlying_read_strat_brief_http
        cls.underlying_delete_strat_brief_http = underlying_delete_strat_brief_http
        cls.underlying_create_cancel_order_http = underlying_create_cancel_order_http
        cls.underlying_read_market_depth_http = underlying_read_market_depth_http
        cls.underlying_read_strat_status_http = underlying_read_strat_status_http
        cls.underlying_read_strat_status_by_id_http = underlying_read_strat_status_by_id_http
        cls.underlying_read_cancel_order_http = underlying_read_cancel_order_http
        cls.underlying_read_strat_limits_http = underlying_read_strat_limits_http
        cls.underlying_delete_strat_status_http = underlying_delete_strat_status_http
        cls.underlying_trade_simulator_place_cxl_order_query_http = (
            underlying_trade_simulator_place_cxl_order_query_http)

    def __init__(self):
        super().__init__()
        pair_strat_id, is_crash_recovery = get_pair_strat_id_from_cmd_argv()
        self.pair_strat_id = pair_strat_id
        self.is_crash_recovery = is_crash_recovery
        # since this init is called before db_init
        os.environ["DB_NAME"] = f"street_book_{self.pair_strat_id}"
        self.datetime_str: Final[str] = datetime.datetime.now().strftime("%Y%m%d")
        os.environ["LOG_FILE_NAME"] = f"street_book_{self.pair_strat_id}_logs_{self.datetime_str}.log"
        self.strat_leg_1: StratLeg | None = None  # will be set by once all_service_up test passes
        self.strat_leg_2: StratLeg | None = None  # will be set by once all_service_up test passes
        self.all_services_up: bool = False
        self.service_ready: bool = False
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.static_data: SecurityRecordManager | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {self.usd_fx_symbol: None}
        self.usd_fx = None
        self.port: int | None = None  # will be set by
        self.web_client = None
        self.strat_cache: StratCache | None = None

        self.min_refresh_interval: int = parse_to_int(executor_config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.trading_data_manager: TradingDataManager | None = None
        self.simulate_config_yaml_file_path = (
                EXECUTOR_PROJECT_DATA_DIR / f"executor_{self.pair_strat_id}_simulate_config.yaml")
        self.log_simulator_file_name = f"log_simulator_{self.pair_strat_id}_logs_{self.datetime_str}.log"
        self.log_simulator_file_path = (PurePath(__file__).parent.parent / "log" /
                                        f"log_simulator_{self.pair_strat_id}_logs_{self.datetime_str}.log")
        create_logger("log_simulator", logging.DEBUG, str(PurePath(__file__).parent.parent / "log"),
                      self.log_simulator_file_name)

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

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        symbol_overview_for_symbol_exists: bool = False
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"street_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                # static data and md service are considered essential
                if (self.all_services_up and static_data_service_state.ready and self.usd_fx is not None and
                        symbol_overview_for_symbol_exists and self.trading_data_manager is not None):
                    if not self.service_ready:
                        self.service_ready = True
                        # creating required models for this strat
                        if not self._check_n_create_related_models_for_strat():
                            self.service_ready = False
                        else:
                            logging.debug("Service Marked Ready")
                else:
                    logging.warning(f"service is not up yet;;; all_services_up: {self.all_services_up}, "
                                    f"static_data_service: {static_data_service_state.ready}, usd_fx: {self.usd_fx}, "
                                    f"symbol_overview_for_symbol_exists: {symbol_overview_for_symbol_exists}, "
                                    f"trading_data_manager: {self.trading_data_manager}")
                if not self.all_services_up:
                    try:
                        if all_service_up_check(self.web_client):
                            # starting trading_data_manager and street_book
                            try:
                                pair_strat = strat_manager_service_http_client.get_pair_strat_client(self.pair_strat_id)
                            except Exception as e:
                                logging.exception(f"get_pair_strat_client failed with exception: {e}")
                                continue

                            # self.strat_leg_1 = StratLeg(**pair_strat.pair_strat_params.strat_leg1.model_dump())
                            # self.strat_leg_2 = StratLeg(**pair_strat.pair_strat_params.strat_leg2.model_dump())
                            self.strat_leg_1 = pair_strat.pair_strat_params.strat_leg1
                            self.strat_leg_2 = pair_strat.pair_strat_params.strat_leg2

                            # creating config file for this server run if not exists
                            code_gen_projects_dir = PurePath(__file__).parent.parent.parent.parent
                            temp_config_file_path = (code_gen_projects_dir / "template_yaml_configs" /
                                                     "server_config.yaml")
                            dest_config_file_path = self.simulate_config_yaml_file_path
                            shutil.copy(temp_config_file_path, dest_config_file_path)

                            # setting simulate_config_file_name
                            TradingLinkBase.simulate_config_yaml_path = self.simulate_config_yaml_file_path
                            TradingLinkBase.executor_port = self.port
                            TradingLinkBase.reload_executor_configs()

                            # setting partial_run to True and assigning port to pair_strat
                            if not pair_strat.is_partially_running:
                                pair_strat.is_partially_running = True
                                pair_strat.port = self.port

                                try:
                                    updated_pair_strat = strat_manager_service_http_client.patch_pair_strat_client(
                                        jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                                except Exception as e:
                                    logging.exception(f"patch_pair_strat_client failed with exception: {e}")
                                    continue
                                else:
                                    self.strat_cache: StratCache = self.get_pair_strat_loaded_strat_cache(
                                        updated_pair_strat)
                                    # Setting asyncio_loop for StreetBook
                                    StreetBook.asyncio_loop = self.asyncio_loop
                                    # StreetBook.trading_link.asyncio_loop = self.asyncio_loop
                                    TradingDataManager.asyncio_loop = self.asyncio_loop
                                    self.trading_data_manager = TradingDataManager(StreetBook.executor_trigger,
                                                                                   self.strat_cache)
                                    logging.debug(f"Created trading_data_manager for pair_strat: {pair_strat}")
                            # else not required: not updating if already is_executor_running
                            logging.debug("Marked pair_strat.is_partially_running True")

                            self.all_services_up = True
                            logging.debug("Marked all_services_up True")
                            should_sleep = False
                        else:
                            should_sleep = True
                    except Exception as e:
                        logging.error("unexpected: all_service_up_check threw exception, "
                                      f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                      f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here
                    if self.usd_fx is None:
                        try:
                            if not self.update_fx_symbol_overview_dict_from_http():
                                logging.error(f"Can't find any symbol_overview with symbol {self.usd_fx_symbol} "
                                              f"in pair_strat_engine service, retrying in next periodic cycle",
                                              exc_info=True)
                        except Exception as e:
                            logging.exception(f"update_fx_symbol_overview_dict_from_http failed with exception: {e}")

                    if not symbol_overview_for_symbol_exists:
                        # updating symbol_overviews
                        symbol_overview_list = self.strat_cache.get_symbol_overviews
                        if None not in symbol_overview_list:
                            symbol_overview_for_symbol_exists = True
                        else:
                            run_coro = (
                                StreetBookServiceRoutesCallbackBaseNativeOverride.
                                underlying_read_symbol_overview_http())
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                            # block for task to finish
                            try:
                                symbol_overview_list = future.result()
                            except Exception as e:
                                logging.exception(f"underlying_read_symbol_overview_http "
                                                  f"failed with exception: {e}")
                            else:
                                for symbol_overview in symbol_overview_list:
                                    self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview)

                            symbol_overview_list = self.strat_cache.get_symbol_overviews
                            if None not in symbol_overview_list:
                                symbol_overview_for_symbol_exists = True
                            else:
                                symbol_overview_for_symbol_exists = False

                    # service loop: manage all sub-services within their private try-catch to allow high level
                    # service to remain partially operational even if some sub-service is not available for any reason
                    if not static_data_service_state.ready:
                        try:
                            self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                            if self.static_data is not None:
                                # creating and running so_shell script
                                pair_strat = self.strat_cache.get_pair_strat_obj()
                                self.create_n_run_so_shell_script(pair_strat)
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

                    # Reconnecting lost ws connections in WSReader
                    for ws_cont in WSReader.ws_cont_list:
                        if ws_cont.force_disconnected and not ws_cont.expired:
                            new_ws_cont = WSReader(ws_cont.uri, ws_cont.PydanticClassType,
                                                   ws_cont.PydanticClassTypeList, ws_cont.callback)
                            new_ws_cont.new_register_to_run()
                            ws_cont.expired = True

                    if self.service_ready:
                        try:
                            # Gets all open orders, updates residuals and raises pause to strat if req
                            run_coro = self.cxl_expired_open_orders()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                            # block for task to finish
                            try:
                                future.result()
                            except Exception as e:
                                logging.exception(f"cxl_expired_open_orders failed with exception: {e}")

                        except Exception as e:
                            logging.error("periodic open order check failed, periodic order state checks will "
                                          "not be honored and retried in next periodic cycle"
                                          f";;;exception: {e}", exc_info=True)
            else:
                should_sleep = True

    def app_launch_pre(self):
        StreetBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_routes()

        self.port = find_free_port()
        self.web_client = StreetBookServiceHttpClient.set_or_get_if_instance_exists(host, self.port)

        app_launch_pre_thread = threading.Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()
        logging.debug("Triggered server launch pre override")

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")
        # making pair_strat is_executor_running field to False
        try:
            # strat_manager_service_http_client.update_pair_strat_to_non_running_state_query_client(self.pair_strat_id)
            guaranteed_call_pair_strat_client(
                None, strat_manager_service_http_client.update_pair_strat_to_non_running_state_query_client,
                pair_strat_id=self.pair_strat_id)
        except Exception as e:
            if ('{"detail":"Id not Found: PairStrat ' + f'{self.pair_strat_id}' + '"}') in str(e):
                err_str_ = ("error occurred since pair_strat object got deleted, therefore can't update "
                            "is_running_state, symbol_side_key: "
                            f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
                logging.debug(err_str_)
            else:
                logging.error(f"Some error occurred while updating is_running state of pair_strat of id: "
                              f"{self.pair_strat_id} while shutting executor server, symbol_side_key: "
                              f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}, "
                              f"exception: {e}")
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

            # renaming simulator log file
            if os.path.exists(self.log_simulator_file_path):
                datetime_str = datetime.datetime.now().strftime("%Y%m%d.%H%M%S")
                os.rename(self.log_simulator_file_path, f"{self.log_simulator_file_path}.{datetime_str}")

    @staticmethod
    def create_n_run_so_shell_script(pair_strat):
        # creating run_symbol_overview.sh file
        run_symbol_overview_file_path = EXECUTOR_PROJECT_SCRIPTS_DIR / f"ps_id_{pair_strat.id}_so.sh"

        subscription_data = \
            [
                (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg1.sec.sec_type)),
                (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg2.sec.sec_type))
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = "SS" if pair_strat.pair_strat_params.strat_leg1.exch_id == "SSE" else "SZ"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_strat.host,
                           port=pair_strat.port, db_name=db_name, exch_code=exch_code,
                           project_name="street_book"))

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
        run_coro = (
            StreetBookServiceRoutesCallbackBaseNativeOverride.
            underlying_read_strat_limits_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            strat_limits_list = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_symbol_overview_http "
                              f"failed with exception: {e}")
        else:

            if not strat_limits_list:
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
                    err_str_ = (f"Exception occurred while fetching filtered broker from portfolio_status - "
                                f"will retry strat_limits create: exception: {e}")
                    logging.error(err_str_)
                    return

                # broker_list = []
                # for broker in eligible_brokers:
                #     broker_list.append(Broker(**broker.model_dump(by_alias=True)))
                strat_limits = get_new_strat_limits(eligible_brokers)
                strat_limits.id = self.pair_strat_id  # syncing id with pair_strat which triggered this server

                run_coro = StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_limits_http(
                    strat_limits)
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
                if len(strat_limits_list) > 1:
                    err_str_: str = ("Unexpected: Found multiple StratLimits in single executor - ignoring "
                                     "strat_cache update for strat_limits - symbol_side_key: "
                                     f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                                     f"strat_limits_list: {strat_limits_list}")
                    logging.error(err_str_)
                else:
                    self.trading_data_manager.handle_strat_limits_get_all_ws(strat_limits_list[0])
                return strat_limits_list[0]

    async def _check_n_remove_strat_limits(self):
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        if strat_limits_tuple is not None:
            strat_limits, _ = strat_limits_tuple
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_limits_http(
                strat_limits.id)
        # ignore if strat_limits doesn't exist - happens when strat is in SNOOZED at the time of this call

    def _check_n_create_or_update_strat_status(self, strat_limits: StratLimits):
        run_coro = (
            StreetBookServiceRoutesCallbackBaseNativeOverride.
            underlying_read_strat_status_http())
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

        # block for task to finish
        try:
            strat_status_list = future.result()
        except Exception as e:
            logging.exception(f"underlying_read_symbol_overview_http "
                              f"failed with exception: {e}")
        else:
            if not strat_status_list:      # When strat is newly created or reloaded after unloading from collection
                strat_status = get_new_strat_status(strat_limits)
                strat_status.id = self.pair_strat_id  # syncing id with pair_strat which triggered this server

                run_coro = (
                    StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_status_http(
                        strat_status))
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
            else:   # When strat is restarted
                if len(strat_status_list) > 1:
                    err_str_: str = (
                        "Unexpected: Found multiple StratStatus in single executor - ignoring strat_cache update"
                        f"for strat_status - symbol_side_key: "
                        f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                        f"strat_status_list: {strat_status_list}")
                    logging.error(err_str_)
                else:
                    self.trading_data_manager.handle_strat_status_get_all_ws(strat_status_list[0])
                return strat_status_list[0]

    async def _check_n_remove_strat_status(self):
        async with StratStatus.reentrant_lock:
            strat_status_tuple = self.strat_cache.get_strat_status()

            if strat_status_tuple:
                strat_status, _ = strat_status_tuple
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_status_http(
                    strat_status.id)
            # ignore if strat_limits doesn't exist - happens when strat is in SNOOZED at the time of this call

    def get_consumable_concentration_from_source(self, symbol: str, strat_limits: StratLimits):
        security_float: float | None = self.static_data.get_security_float_from_ticker(symbol)
        if security_float is None or security_float <= 0:
            logging.error(f"concentration check will fail for {symbol}, invalid security float found in static data: "
                          f"{security_float}")
            consumable_concentration = 0
        else:
            consumable_concentration = \
                (security_float / 100) * strat_limits.max_concentration
        return consumable_concentration

    async def _create_strat_brief_for_ready_to_active_pair_strat(self, strat_limits: StratLimits):
        symbol = self.strat_leg_1.sec.sec_id
        side = self.strat_leg_1.side
        strat_brief_tuple = self.strat_cache.get_strat_brief()

        if strat_brief_tuple is not None:
            err_str_ = (f"strat_brief must not exist in cache for this symbol while strat is converting "
                        f"from ready to active - ignoring strat_brief create, "
                        f"pair_strat_key: {get_symbol_side_key([(symbol, side)])};;; "
                        f"found strat_brief_tuple from cache: {strat_brief_tuple}")
            logging.error(err_str_)
            return
        else:
            # If no strat_brief exists for this symbol
            consumable_open_orders = strat_limits.max_open_orders_per_side
            consumable_notional = strat_limits.max_single_leg_notional
            consumable_open_notional = strat_limits.max_open_single_leg_notional

        residual_qty = 0
        all_bkr_cxlled_qty = 0
        open_notional = 0
        open_qty = 0

        buy_side_trading_brief: PairSideTradingBrief | None = None
        sell_side_trading_brief: PairSideTradingBrief | None = None

        for sec, side in [(self.strat_leg_1.sec, self.strat_leg_1.side), (self.strat_leg_2.sec, self.strat_leg_2.side)]:
            symbol = sec.sec_id
            consumable_concentration = self.get_consumable_concentration_from_source(symbol, strat_limits)

            participation_period_order_qty_sum = 0
            consumable_cxl_qty = 0
            applicable_period_second = strat_limits.market_trade_volume_participation.applicable_period_seconds
            executor_check_snapshot_list = \
                await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                         applicable_period_second))
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
            indicative_consumable_residual = strat_limits.residual_restriction.max_residual
            sec_pair_side_trading_brief_obj = \
                PairSideTradingBrief(security=sec,
                                     side=side,
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
            if Side.BUY == side:
                if buy_side_trading_brief is None:
                    buy_side_trading_brief = sec_pair_side_trading_brief_obj
                else:
                    logging.error(f"expected buy_side_trading_brief to be None, found: {buy_side_trading_brief}")
            elif Side.SELL == side:
                if sell_side_trading_brief is None:
                    sell_side_trading_brief = sec_pair_side_trading_brief_obj
                else:
                    logging.error(f"expected sell_side_trading_brief to be None, found: {sell_side_trading_brief}")

        strat_brief_obj: StratBrief = StratBrief(_id=strat_limits.id,
                                                 pair_buy_side_trading_brief=buy_side_trading_brief,
                                                 pair_sell_side_trading_brief=sell_side_trading_brief,
                                                 consumable_nett_filled_notional=strat_limits.max_net_filled_notional)
        created_underlying_strat_brief = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_brief_http(
                strat_brief_obj)
        logging.debug(f"Created strat brief in post call of update strat_status to active of "
                      f"key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                      f"strat_limits: {strat_limits}, "
                      f"created strat_brief: {created_underlying_strat_brief}")

    async def _create_symbol_snapshot_for_ready_to_active_pair_strat(self):
        # before running this server
        pair_symbol_side_list = [
            (self.strat_leg_1.sec, self.strat_leg_1.side),
            (self.strat_leg_2.sec, self.strat_leg_2.side)
        ]

        for security, side in pair_symbol_side_list:
            if security is not None and side is not None:

                symbol_side_snapshots_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(security.sec_id)

                if symbol_side_snapshots_tuple is None:
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
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj))
                    logging.debug(f"Created SymbolSideSnapshot with key: "
                                  f"{get_symbol_side_snapshot_log_key(created_symbol_side_snapshot)};;;"
                                  f"new SymbolSideSnapshot: {created_symbol_side_snapshot}")
                else:
                    err_str_ = (f"SymbolSideSnapshot must not be present in cache for this symbol and side "
                                f"when strat is converted from ready to active, symbol_side_key: "
                                f"{get_symbol_side_key([(security.sec_id, side)])}, "
                                f"symbol_side_snapshots_tuple {symbol_side_snapshots_tuple}")
                    logging.error(err_str_)
                    return
            else:
                # Ignore symbol side snapshot creation and logging if any of security and side is None
                logging.debug(f"Received either security or side as None from config of this start_executor for port "
                              f"{self.port}, likely populated by pair_strat_engine before launching this server, "
                              f"security: {security}, side: {side}")

    async def _force_publish_symbol_overview_for_ready_to_active_strat(self) -> None:

        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]

        async with SymbolOverview.reentrant_lock:
            for symbol in symbols_list:
                symbol_overview_obj_tuple = self.strat_cache.get_symbol_overview_from_symbol(symbol)

                if symbol_overview_obj_tuple is not None:
                    symbol_overview_obj, _ = symbol_overview_obj_tuple
                    updated_symbol_overview = FxSymbolOverviewBaseModel(_id=symbol_overview_obj.id,
                                                                        force_publish=True)
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_overview_http(
                            jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True)))
                else:
                    err_str_ = ("Found Strat_overview_tuple as None from strat_cache - ignoring symbol_overview "
                                "update, this must not happen unless manual deletion is done for these symbols from "
                                "symbol_overview because service_ready flag is only enabled after symbol_overviews "
                                "with these symbols are found")
                    logging.error(err_str_)

    def _check_n_create_strat_alert(self, strat_id: int) -> bool:
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
                return False
        return True

    def _check_n_create_related_models_for_strat(self) -> bool:
        strat_limits = self._check_n_create_default_strat_limits()
        if strat_limits is not None:
            strat_status = self._check_n_create_or_update_strat_status(strat_limits)
            if not self._check_n_create_strat_alert(self.pair_strat_id):
                return False

            if strat_status is not None:
                pair_strat_tuple = self.strat_cache.get_pair_strat()
                if pair_strat_tuple is not None:
                    pair_strat, _ = pair_strat_tuple
                    if not pair_strat.is_executor_running:
                        pair_strat.is_executor_running = True

                        strat_state = None
                        if pair_strat.strat_state == StratState.StratState_SNOOZED:
                            pair_strat.strat_state = StratState.StratState_READY
                            # strat_state = StratState.StratState_READY
                        # else not required: If it's not startup for reload or new strat creation then avoid

                        try:
                            strat_manager_service_http_client.patch_pair_strat_client(
                                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                            logging.debug(f"pair_strat's is_executor_running set to True, pair_strat: {pair_strat}")
                            return True
                        except Exception as e:
                            logging.exception("patch_pair_strat_client failed while setting is_executor_running "
                                              f"to true, retrying in next startup refresh: exception: {e}")
                    # else not required: not updating if already is_executor_running
                else:
                    err_str_ = ("Unexpected: Can't find pair_strat object in strat_cache - "
                                "retrying in next startup refresh")
                    logging.error(err_str_)
        return False

    async def load_strat_cache(self):
        # updating strat_brief
        strat_brief_list: List[StratBrief] = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http()
        for strat_brief in strat_brief_list:
            self.trading_data_manager.handle_strat_brief_get_all_ws(strat_brief)

        if self.is_crash_recovery:

            # updating order_journals
            order_journals: List[OrderJournal] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_order_journal_http()
            for order_journal in order_journals:
                self.trading_data_manager.handle_recovery_order_journal(order_journal)

            # updating order_snapshots
            order_snapshots: List[OrderSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http()
            for order_snapshot in order_snapshots:
                self.trading_data_manager.handle_order_snapshot_get_all_ws(order_snapshot)

            # updating symbol_side_snapshot
            symbol_side_snapshots: List[SymbolSideSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_side_snapshot_http()
            for symbol_side_snapshot in symbol_side_snapshots:
                self.trading_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot)

            # updating cancel_orders
            cancel_orders: List[CancelOrder] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_cancel_order_http()
            for cancel_order in cancel_orders:
                self.trading_data_manager.handle_recovery_cancel_order(cancel_order)

    async def _create_related_models_for_active_strat(self) -> None:
        # updating strat_cache
        await self.load_strat_cache()

        strat_limits_tuple = self.strat_cache.get_strat_limits()

        if strat_limits_tuple is not None:
            strat_limits, _ = strat_limits_tuple

            # creating strat_brief for both leg securities

            if not self.is_crash_recovery:
                await self._create_strat_brief_for_ready_to_active_pair_strat(strat_limits)
                # creating symbol_side_snapshot for both leg securities if not already exists
                await self._create_symbol_snapshot_for_ready_to_active_pair_strat()
                # changing symbol_overview force_publish to True if exists
                await self._force_publish_symbol_overview_for_ready_to_active_strat()
            # else not required: If it's crash recovery then these models must exist already
            # if before crash they existed
        else:
            err_str_ = (
                "Can't find any strat_limits in cache to create related models for active strat, "
                "ignoring model creations, symbol_side_key: "
                f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)

        logging.info(f"Updated Strat to active: "
                     f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")

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
        pause_strat: bool = False

        if (residual_notional := updated_strat_status.residual.residual_notional) is not None:
            if residual_notional > (max_residual := strat_limits.residual_restriction.max_residual):
                alert_brief: str = (f"residual notional: {residual_notional} > max residual: {max_residual} - "
                                    f"pausing this strat")
                alert_details: str = f"updated_strat_status: {updated_strat_status}, strat_limits: {strat_limits}"
                logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                 f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                pause_strat = True
            # else not required: if residual is in control then nothing to do

        if symbol_side_snapshot_.order_count > strat_limits.cancel_rate.waived_min_orders:
            if symbol_side_snapshot_.side == Side.BUY:
                if strat_brief_.pair_buy_side_trading_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_buy_side_trading_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, currently is {consumable_cxl_qty} " \
                                        f"for symbol {strat_brief_.pair_buy_side_trading_brief.security.sec_id} and " \
                                        f"side {Side.BUY} - pausing this strat"
                        alert_brief: str = err_str_
                        alert_details: str = (f"updated_strat_status: {updated_strat_status}, "
                                              f"strat_limits: {strat_limits}, "
                                              f"symbol_side_snapshot: {symbol_side_snapshot_}")
                        logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                         f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                        pause_strat = True
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
                        pause_strat = True
                        logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                         f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single sell order then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if sell side all_bkr_cxlled_qty is 0
            # else not required: if order count is less than waived_min_orders
        if pause_strat:
            self.set_strat_state_to_pause()

    ####################################
    # Get specific Data handling Methods
    ####################################

    def _get_top_of_book_from_symbol(self, symbol: str):
        tob_tuple: Tuple[List[TopOfBook], DateTime] = self.strat_cache.get_top_of_book()
        if tob_tuple is not None:
            tob_list, _ = tob_tuple
            if tob_list[0].symbol == symbol:
                return tob_list[0]
            elif tob_list[1].symbol == symbol:
                return tob_list[1]
            else:
                err_str_ = f"Can't find any tob with symbol {symbol} in strat_cache"
                logging.error(err_str_)
        else:
            err_str_ = f"Can't find tob list in strat_cache for symbol: {symbol}"
            logging.error(err_str_)

    def __get_residual_obj(self, side: Side, strat_brief: StratBrief) -> Residual | None:
        if side == Side.BUY:
            residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
        else:
            residual_qty = strat_brief.pair_sell_side_trading_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_buy_side_trading_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_trading_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_trading_brief.security.sec_id)

        if top_of_book_obj is None or other_leg_top_of_book is None:
            logging.error(f"Received both leg's TOBs as {top_of_book_obj} and {other_leg_top_of_book}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            return None

        residual_notional = abs((residual_qty * self.get_usd_px(top_of_book_obj.last_trade.px,
                                                                top_of_book_obj.symbol)) -
                                (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_trade.px,
                                                                          other_leg_top_of_book.symbol)))
        if side == Side.BUY:
            if (residual_qty * self.get_usd_px(top_of_book_obj.last_trade.px,
                                               top_of_book_obj.symbol)) > \
                    (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_trade.px,
                                                              other_leg_top_of_book.symbol)):
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

    async def get_last_n_sec_order_qty(self, symbol: str, side: Side, last_n_sec: int) -> int | None:
        last_n_sec_order_qty: int | None = None
        if last_n_sec == 0:
            symbol_side_snapshots_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(symbol)
            if symbol_side_snapshots_tuple is not None:
                symbol_side_snapshot, _ = symbol_side_snapshots_tuple
                last_n_sec_order_qty = symbol_side_snapshot.total_qty
            else:
                err_str_ = f"Received symbol_side_snapshots_tuple as None from strat_cache, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.exception(err_str_)
        else:
            agg_objs = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
                    get_order_total_sum_of_last_n_sec(symbol, last_n_sec), self.get_generic_read_route())

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
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        last_n_sec_trade_qty: int | None = None
        if strat_limits_tuple is not None:
            strat_limits, _ = strat_limits_tuple

            if strat_limits is not None:
                applicable_period_seconds = strat_limits.market_trade_volume_participation.applicable_period_seconds
                last_n_sec_market_trade_vol_obj_list = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_get_last_n_sec_total_trade_qty_query_http(symbol, applicable_period_seconds))
                if last_n_sec_market_trade_vol_obj_list:
                    last_n_sec_trade_qty = last_n_sec_market_trade_vol_obj_list[0].last_n_sec_trade_vol
                else:
                    logging.error(f"could not receive any last_n_sec_market_trade_vol_obj to get last_n_sec_trade_qty "
                                  f"for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, likely bug in "
                                  f"get_last_n_sec_total_trade_qty_query pre impl")
        else:
            err_str_ = (
                "Can't find any strat_limits in cache to get last_n_sec trade qty, "
                "ignoring model creations, symbol_side_key: "
                f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
        return last_n_sec_trade_qty

    async def get_list_of_underlying_account_n_cumulative_fill_qty(self, symbol: str, side: Side):
        underlying_account_cum_fill_qty_obj_list = \
            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                   get_underlying_account_cumulative_fill_qty_query_http(symbol, side))
        return underlying_account_cum_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty

    ######################################
    # Strat lvl models update pre handling
    ######################################

    async def create_admin_control_pre(self, admin_control_obj: AdminControl):
        match admin_control_obj.command_type:
            case CommandType.RESET_STATE:
                from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_beanie_database \
                    import document_models
                for document_model in document_models:
                    document_model._cache_obj_id_to_obj_dict = {}
            case other_:
                logging.error(f"create_admin_control_pre failed. unrecognized command_type: {other_}")

    async def _update_strat_limits_pre(self, stored_strat_limits_obj: StratLimits,
                                       updated_strat_limits_obj: StratLimits):
        pass

    async def update_strat_limits_pre(self, stored_strat_limits_obj: StratLimits,
                                      updated_strat_limits_obj: StratLimits):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "update_strat_limits_pre not ready - service is not initialized yet, " \
                       f"symbol_side_key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        await self._update_strat_limits_pre(stored_strat_limits_obj, updated_strat_limits_obj)
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

        original_eligible_brokers = []
        if (eligible_brokers := updated_strat_limits_obj_json.get("eligible_brokers")) is not None:
            original_eligible_brokers = copy.deepcopy(eligible_brokers)

        updated_pydantic_obj_dict = compare_n_patch_dict(
            copy.deepcopy(stored_strat_limits_obj.model_dump(by_alias=True)), updated_strat_limits_obj_json)
        updated_strat_limits_obj = StratLimitsOptional(**updated_pydantic_obj_dict)
        await self._update_strat_limits_pre(stored_strat_limits_obj, updated_strat_limits_obj)
        updated_strat_limits_obj_json = jsonable_encoder(updated_strat_limits_obj, by_alias=True, exclude_none=True)
        updated_strat_limits_obj_json["eligible_brokers"] = original_eligible_brokers

        if stored_strat_limits_obj.strat_limits_update_seq_num is None:
            stored_strat_limits_obj.strat_limits_update_seq_num = 0
        updated_strat_limits_obj_json[
            "strat_limits_update_seq_num"] = stored_strat_limits_obj.strat_limits_update_seq_num + 1
        return updated_strat_limits_obj_json

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

        return updated_strat_status_obj

    async def handle_strat_activate_query_pre(self, handle_strat_activate_class_type: Type[HandleStratActivate]):
        await self._create_related_models_for_active_strat()
        return []

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

        return updated_strat_status_obj_json

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
            top_of_book_obj = self._get_top_of_book_from_symbol(order_journal_obj.order.security.sec_id)
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

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock:
            res = await self._update_order_snapshot_from_order_journal(order_journal_obj)

            if res is not None:
                strat_id, order_snapshot, strat_brief, portfolio_status_updates = res

                # Updating and checking portfolio_limits in portfolio_manager
                post_trade_engine_service_http_client.check_portfolio_limits_query_client(
                    strat_id, order_journal_obj, order_snapshot, strat_brief, portfolio_status_updates)

            # else not required: if result returned from _update_order_snapshot_from_order_journal is None, that
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding portfolio_limit checks too

    async def create_order_snapshot_pre(self, order_snapshot_obj: OrderSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if order_snapshot_obj.order_brief.security.sec_type is None:
            order_snapshot_obj.order_brief.security.sec_type = SecurityType.TICKER

    async def create_symbol_side_snapshot_pre(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if symbol_side_snapshot_obj.security.sec_type is None:
            symbol_side_snapshot_obj.security.sec_type = SecurityType.TICKER

    @staticmethod
    def is_cxled_event(event: OrderEventType) -> bool:
        if event in [OrderEventType.OE_CXL_ACK, OrderEventType.OE_UNSOL_CXL]:
            return True
        return False

    async def _update_order_snapshot_from_order_journal(
            self, order_journal_obj: OrderJournal) -> Tuple[int, OrderSnapshot, StratBrief | None,
                                                            PortfolioStatusUpdatesContainer | None] | None:
        pair_strat = self.strat_cache.get_pair_strat_obj()

        if not is_ongoing_strat(pair_strat):
            # avoiding any update if strat is non-ongoing
            return None

        match order_journal_obj.order_event:
            case OrderEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'

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
                order_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                        underlying_create_order_snapshot_http(order_snapshot))
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                      order_snapshot)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_order_or_fill(order_journal_obj,
                                                                                            order_snapshot,
                                                                                            symbol_side_snapshot)
                    if updated_strat_brief is not None:
                        await self._update_strat_status_from_order_journal(order_journal_obj, order_snapshot,
                                                                           symbol_side_snapshot, updated_strat_brief)
                    # else not required: if updated_strat_brief is None then it means some error occurred in
                    # _update_strat_brief_from_order which would have got added to alert already
                    portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                        await self._update_portfolio_status_from_order_journal(
                            order_journal_obj, order_snapshot))

                    return pair_strat.id, order_snapshot, updated_strat_brief, portfolio_status_updates
                # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_order_journal
                # which would have got added to alert already

            case OrderEventType.OE_ACK:
                async with OrderSnapshot.reentrant_lock:
                    order_snapshot = \
                        await self._check_state_and_get_order_snapshot_obj(order_journal_obj,
                                                                           [OrderStatusType.OE_UNACK])
                    if order_snapshot is not None:
                        updated_order_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                            underlying_partial_update_order_snapshot_http(
                                json.loads(OrderSnapshotOptional(
                                    _id=order_snapshot.id,
                                    last_update_date_time=order_journal_obj.order_event_date_time,
                                    order_status=OrderStatusType.OE_ACKED).model_dump_json(by_alias=True,
                                                                                           exclude_none=True))))

                        return pair_strat.id, updated_order_snapshot, None, None

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL:
                async with OrderSnapshot.reentrant_lock:
                    order_snapshot = await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_UNACK, OrderStatusType.OE_ACKED])
                    if order_snapshot is not None:
                        updated_order_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                        underlying_partial_update_order_snapshot_http(
                            json.loads(OrderSnapshotOptional(
                                _id=order_snapshot.id, last_update_date_time=order_journal_obj.order_event_date_time,
                                order_status=OrderStatusType.OE_CXL_UNACK).model_dump_json(by_alias=True,
                                                                                           exclude_none=True))))

                        return pair_strat.id, updated_order_snapshot, None, None

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already
            case OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL:
                async with OrderSnapshot.reentrant_lock:
                    order_snapshot = \
                        await self._check_state_and_get_order_snapshot_obj(
                            order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_ACKED,
                                                OrderStatusType.OE_UNACK, OrderStatusType.OE_FILLED])
                    if order_snapshot is not None:
                        # When CXL_ACK arrived after order got fully filled, since nothing is left to cxl - ignoring
                        # this order_journal's order_snapshot update
                        if order_snapshot.order_status == OrderStatusType.OE_FILLED:
                            logging.info("Received order_journal with event CXL_ACK after OrderSnapshot is fully "
                                         f"filled - ignoring this CXL_ACK, order_journal_key: "
                                         f"{get_order_journal_log_key(order_journal_obj)};;; "
                                         f"order_journal: {order_journal_obj}, order_snapshot: {order_snapshot}")
                        else:
                            # If order_event is OE_UNSOL_CXL, that is treated as unsolicited cxl
                            # If CXL_ACK comes after OE_CXL_UNACK, that means cxl_ack came after cxl request
                            # order_brief = OrderBriefOptional(**order_snapshot.order_brief.model_dump())
                            order_brief = order_snapshot.order_brief
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
                            order_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                underlying_partial_update_order_snapshot_http(
                                    json.loads(OrderSnapshotOptional(_id=order_snapshot.id,
                                                                     order_brief=order_brief,
                                                                     cxled_qty=cxled_qty,
                                                                     cxled_notional=cxled_notional,
                                                                     avg_cxled_px=avg_cxled_px,
                                                                     last_update_date_time=
                                                                     order_journal_obj.order_event_date_time,
                                                                     order_status=
                                                                     OrderStatusType.OE_DOD).model_dump_json(
                                        by_alias=True, exclude_none=True))))

                        if order_snapshot.order_status != OrderStatusType.OE_FILLED:
                            symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_order_journal(
                                order_journal_obj, order_snapshot)
                            if symbol_side_snapshot is not None:
                                updated_strat_brief = (
                                    await self._update_strat_brief_from_order_or_fill(order_journal_obj, order_snapshot,
                                                                                      symbol_side_snapshot))
                                if updated_strat_brief is not None:
                                    await self._update_strat_status_from_order_journal(
                                        order_journal_obj, order_snapshot, symbol_side_snapshot, updated_strat_brief)
                                # else not required: if updated_strat_brief is None then it means some error occurred in
                                # _update_strat_brief_from_order which would have got added to alert already
                                portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                                    await self._update_portfolio_status_from_order_journal(
                                        order_journal_obj, order_snapshot))

                                return pair_strat.id, order_snapshot, updated_strat_brief, portfolio_status_updates

                            # else not required: if symbol_side_snapshot is None then it means some error occurred in
                            # _create_update_symbol_side_snapshot_from_order_journal which would have got added to
                            # alert already

                        # else not required: If CXL_ACK arrived after order is fully filled then since we ignore
                        # any update for this order journal object, returns None to not update post trade engine too

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_CXL_INT_REJ | OrderEventType.OE_CXL_BRK_REJ | OrderEventType.OE_CXL_EXH_REJ:
                # reverting the state of order_snapshot after receiving cxl reject

                async with OrderSnapshot.reentrant_lock:
                    order_snapshot = await self._check_state_and_get_order_snapshot_obj(
                        order_journal_obj, [OrderStatusType.OE_CXL_UNACK, OrderStatusType.OE_FILLED])
                    if order_snapshot is not None:
                        if order_snapshot.order_brief.qty > order_snapshot.filled_qty:
                            last_3_order_journals_from_order_id = \
                                await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                       underlying_read_order_journal_http(
                                        get_last_n_order_journals_from_order_id(
                                            order_journal_obj.order.order_id, 3),
                                        self.get_generic_read_route()))
                            if last_3_order_journals_from_order_id:
                                if (last_3_order_journals_from_order_id[0].order_event in
                                        [OrderEventType.OE_CXL_INT_REJ,
                                         OrderEventType.OE_CXL_BRK_REJ,
                                         OrderEventType.OE_CXL_EXH_REJ]):
                                    if last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_NEW:
                                        order_status = OrderStatusType.OE_UNACK
                                    elif last_3_order_journals_from_order_id[-1].order_event == OrderEventType.OE_ACK:
                                        order_status = OrderStatusType.OE_ACKED
                                    else:
                                        err_str_ = ("3rd order journal from order_journal of status OE_CXL_INT_REJ "
                                                    "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, must be"
                                                    "of status OE_ACK or OE_UNACK, received last 3 order_journals "
                                                    f"{last_3_order_journals_from_order_id}, "
                                                    f"order_journal_key: "
                                                    f"{get_order_journal_log_key(order_journal_obj)}")
                                        logging.error(err_str_)
                                        return None
                                else:
                                    err_str_ = ("Recent order journal must be of status OE_CXL_INT_REJ "
                                                "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, received last 3 "
                                                "order_journals {last_3_order_journals_from_order_id}, "
                                                f"order_journal_key: {get_order_journal_log_key(order_journal_obj)}")
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
                        updated_order_snapshot = \
                            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                   underlying_partial_update_order_snapshot_http(
                                    json.loads(OrderSnapshotOptional(
                                        _id=order_snapshot.id, last_update_date_time=
                                        order_journal_obj.order_event_date_time,
                                        order_status=order_status).model_dump_json(by_alias=True, exclude_none=True))))

                        return pair_strat.id, updated_order_snapshot, None, None
                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_order_snapshot_obj and hence would have been added to alert already

            case OrderEventType.OE_INT_REJ | OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ:
                async with OrderSnapshot.reentrant_lock:
                    order_snapshot = \
                        await self._check_state_and_get_order_snapshot_obj(
                            order_journal_obj, [OrderStatusType.OE_UNACK, OrderStatusType.OE_ACKED])
                    if order_snapshot is not None:
                        order_brief = order_snapshot.order_brief
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
                        order_snapshot = \
                            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                   underlying_partial_update_order_snapshot_http(
                                    json.loads(OrderSnapshotOptional(
                                        _id=order_snapshot.id,
                                        # order_brief=OrderBriefOptional(**order_brief.model_dump()),
                                        order_brief=order_brief,
                                        cxled_qty=cxled_qty,
                                        cxled_notional=cxled_notional,
                                        avg_cxled_px=avg_cxled_px,
                                        last_update_date_time=order_journal_obj.order_event_date_time,
                                        order_status=OrderStatusType.OE_DOD).model_dump_json(by_alias=True,
                                                                                             exclude_none=True))))
                        symbol_side_snapshot = \
                            await self._create_update_symbol_side_snapshot_from_order_journal(order_journal_obj,
                                                                                              order_snapshot)
                        if symbol_side_snapshot is not None:
                            updated_strat_brief = (
                                await self._update_strat_brief_from_order_or_fill(order_journal_obj, order_snapshot,
                                                                                  symbol_side_snapshot))
                            if updated_strat_brief is not None:
                                await self._update_strat_status_from_order_journal(
                                    order_journal_obj, order_snapshot, symbol_side_snapshot, updated_strat_brief)
                            # else not required: if updated_strat_brief is None then it means some error occurred in
                            # _update_strat_brief_from_order which would have got added to alert already
                            portfolio_status_updates: PortfolioStatusUpdatesContainer = (
                                await self._update_portfolio_status_from_order_journal(
                                    order_journal_obj, order_snapshot))

                            return pair_strat.id, order_snapshot, updated_strat_brief, portfolio_status_updates
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
                                                      order_count=1)
        symbol_side_snapshot_obj = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_symbol_side_snapshot_http(
                symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj

    async def _create_update_symbol_side_snapshot_from_order_journal(self, order_journal: OrderJournal,
                                                                     order_snapshot_obj: OrderSnapshot
                                                                     ) -> SymbolSideSnapshot | None:
        async with SymbolSideSnapshot.reentrant_lock:
            symbol_side_snapshot_objs = (
                self.strat_cache.get_symbol_side_snapshot_from_symbol(order_journal.order.security.sec_id))

            # If no symbol_side_snapshot for symbol-side of received order_journal
            if symbol_side_snapshot_objs is None:
                if order_journal.order_event == OrderEventType.OE_NEW:
                    created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_order(order_journal)
                    return created_symbol_side_snapshot
                else:
                    err_str_: str = (f"No OE_NEW detected for order_journal_key: "
                                     f"{get_order_journal_log_key(order_journal)} "
                                     f"failed to create symbol_side_snapshot "
                                     f";;; order_journal: {order_journal}")
                    logging.error(err_str_)
                    return
            # If symbol_side_snapshot exists for order_id from order_journal
            else:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_objs
                updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
                match order_journal.order_event:
                    case OrderEventType.OE_NEW:
                        updated_symbol_side_snapshot_obj.order_count = symbol_side_snapshot_obj.order_count + 1
                        updated_symbol_side_snapshot_obj.avg_px = \
                            avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                      order_journal.order.px,
                                                      updated_symbol_side_snapshot_obj.order_count
                                                      )
                        updated_symbol_side_snapshot_obj.total_qty = (
                                symbol_side_snapshot_obj.total_qty + order_journal.order.qty)
                        updated_symbol_side_snapshot_obj.last_update_date_time = order_journal.order_event_date_time
                    case (OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL | OrderEventType.OE_INT_REJ |
                          OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ):
                        updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                symbol_side_snapshot_obj.total_cxled_qty + order_snapshot_obj.cxled_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                symbol_side_snapshot_obj.total_cxled_notional + order_snapshot_obj.cxled_notional)
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
                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_side_snapshot_http(
                            json.loads(updated_symbol_side_snapshot_obj.model_dump_json(by_alias=True,
                                                                                        exclude_none=True))
                           ))
                return updated_symbol_side_snapshot_obj

    async def _check_state_and_get_order_snapshot_obj(self, order_journal_obj: OrderJournal,
                                                      expected_status_list: List[str]) -> OrderSnapshot | None:
        """
        Checks if order_snapshot holding order_id of passed order_journal has expected status
        from provided statuses list and then returns that order_snapshot
        """
        order_snapshot_obj = self.strat_cache.get_order_snapshot_from_order_id(order_journal_obj.order.order_id)

        if order_snapshot_obj is not None:
            if order_snapshot_obj.order_status in expected_status_list:
                return order_snapshot_obj
            else:
                ord_journal_key: str = get_order_journal_log_key(order_journal_obj)
                ord_snapshot_key: str = get_order_snapshot_log_key(order_snapshot_obj)
                err_str_: str = f"_check_state_and_get_order_snapshot_obj: order_journal of key: {ord_journal_key} " \
                                f"received with event: {order_journal_obj.order_event}, to update status of " \
                                f"order_snapshot: {ord_snapshot_key}, with status: " \
                                f"{order_snapshot_obj.order_status}, but order_snapshot doesn't contain any of " \
                                f"expected statuses: {expected_status_list}" \
                                f";;; order_journal: {order_journal_obj}, order_snapshot_obj: {order_snapshot_obj}"
                logging.error(err_str_)
        # else not required: error occurred in _get_order_snapshot_from_order_journal_order_id,
        # alert must have updated

    async def _update_strat_status_from_order_journal(self, order_journal_obj: OrderJournal,
                                                      order_snapshot: OrderSnapshot,
                                                      symbol_side_snapshot: SymbolSideSnapshot,
                                                      strat_brief: StratBrief, ):
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        async with StratStatus.reentrant_lock:
            strat_status_tuple = self.strat_cache.get_strat_status()

            if strat_limits_tuple is not None and strat_status_tuple is not None:
                strat_limits, _ = strat_limits_tuple
                update_strat_status_obj, _ = strat_status_tuple
                match order_journal_obj.order.side:
                    case Side.BUY:
                        match order_journal_obj.order_event:
                            case OrderEventType.OE_NEW:
                                update_strat_status_obj.total_buy_qty += order_journal_obj.order.qty
                                update_strat_status_obj.total_open_buy_qty += order_journal_obj.order.qty
                                update_strat_status_obj.total_open_buy_notional += \
                                    order_journal_obj.order.qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                                  order_snapshot.order_brief.security.sec_id)
                            case (OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL | OrderEventType.OE_INT_REJ |
                                  OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ):
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
                                (self.get_local_px_or_notional(update_strat_status_obj.total_open_buy_notional,
                                                              order_journal_obj.order.security.sec_id) /
                                 update_strat_status_obj.total_open_buy_qty)
                    case Side.SELL:
                        match order_journal_obj.order_event:
                            case OrderEventType.OE_NEW:
                                update_strat_status_obj.total_sell_qty += order_journal_obj.order.qty
                                update_strat_status_obj.total_open_sell_qty += order_journal_obj.order.qty
                                update_strat_status_obj.total_open_sell_notional += \
                                    order_journal_obj.order.qty * self.get_usd_px(order_journal_obj.order.px,
                                                                                  order_journal_obj.order.security.sec_id)
                            case (OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL | OrderEventType.OE_INT_REJ |
                                  OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ):
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
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_buy_notional
                else:
                    update_strat_status_obj.balance_notional = \
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_sell_notional

                updated_residual = self.__get_residual_obj(order_snapshot.order_brief.side, strat_brief)
                if updated_residual is not None:
                    update_strat_status_obj.residual = updated_residual

                # Updating strat_state as paused if limits get breached
                self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                     strat_brief, symbol_side_snapshot)

                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_strat_status_http(
                    json.loads(update_strat_status_obj.model_dump_json(by_alias=True, exclude_none=True)))
            else:
                logging.error(f"error: either tuple of strat_status or strat_limits received as None from cache;;; "
                              f"strat_status_tuple: {strat_status_tuple}, strat_limits_tuple: {strat_limits_tuple}")
                return

    async def _update_strat_brief_from_order_or_fill(self, order_journal_or_fills_journal: OrderJournal | FillsJournal,
                                                     order_snapshot: OrderSnapshot,
                                                     symbol_side_snapshot: SymbolSideSnapshot,
                                                     received_fill_after_dod: bool | None = None) -> StratBrief | None:

        security = symbol_side_snapshot.security
        side = symbol_side_snapshot.side
        symbol = security.sec_id

        async with StratBrief.reentrant_lock:
            strat_brief_tuple = self.strat_cache.get_strat_brief()

            strat_limits_tuple = self.strat_cache.get_strat_limits()

            if strat_brief_tuple is not None:
                strat_brief_obj, _ = strat_brief_tuple
                if strat_limits_tuple is not None:
                    strat_limits, _ = strat_limits_tuple

                    if side == Side.BUY:
                        fetched_open_qty = strat_brief_obj.pair_buy_side_trading_brief.open_qty
                        fetched_open_notional = strat_brief_obj.pair_buy_side_trading_brief.open_notional
                    else:
                        fetched_open_qty = strat_brief_obj.pair_sell_side_trading_brief.open_qty
                        fetched_open_notional = strat_brief_obj.pair_sell_side_trading_brief.open_notional

                    if isinstance(order_journal_or_fills_journal, OrderJournal):
                        order_journal: OrderJournal = order_journal_or_fills_journal
                        if order_journal.order_event == OrderEventType.OE_NEW:
                            # When order_event is OE_NEW then just adding current order's total qty to existing
                            # open_qty + total notional (total order Qty * order px) to exist open_notional
                            if fetched_open_qty is None:
                                fetched_open_qty = 0
                            if fetched_open_notional is None:
                                fetched_open_notional = 0
                            open_qty = fetched_open_qty + order_snapshot.order_brief.qty
                            open_notional = (
                                    fetched_open_notional + (
                                        order_snapshot.order_brief.qty *
                                        self.get_usd_px(order_snapshot.order_brief.px,
                                                        order_snapshot.order_brief.security.sec_id)))
                        elif order_journal.order_event in [OrderEventType.OE_INT_REJ, OrderEventType.OE_BRK_REJ,
                                                           OrderEventType.OE_EXH_REJ]:
                            # When order_event is OE_INT_REJ or OE_BRK_REJ or OE_EXH_REJ then just removing
                            # current order's total qty from existing open_qty + total notional
                            # (total order Qty * order px) from existing open_notional
                            open_qty = fetched_open_qty - order_snapshot.order_brief.qty
                            open_notional = (
                                    fetched_open_notional - (
                                        order_snapshot.order_brief.qty *
                                        self.get_usd_px(order_snapshot.order_brief.px,
                                                        order_snapshot.order_brief.security.sec_id)))
                        elif order_journal.order_event in [OrderEventType.OE_CXL_ACK, OrderEventType.OE_UNSOL_CXL]:
                            # When order_event is OE_CXL_ACK or OE_UNSOL_CXL then removing current order's
                            # unfilled qty from existing open_qty + unfilled notional
                            # (unfilled order Qty * order px) from existing open_notional
                            unfilled_qty = order_snapshot.order_brief.qty - order_snapshot.filled_qty
                            open_qty = fetched_open_qty - unfilled_qty
                            open_notional = (
                                    fetched_open_notional - (
                                        unfilled_qty * self.get_usd_px(order_snapshot.order_brief.px,
                                                                       order_snapshot.order_brief.security.sec_id)))
                        else:
                            err_str_: str = (f"Unsupported OrderEventType: Must be either of "
                                             f"[{OrderEventType.OE_NEW}, {OrderEventType.OE_INT_REJ}, "
                                             f"{OrderEventType.OE_BRK_REJ}, {OrderEventType.OE_EXH_REJ}"
                                             f"{OrderEventType.OE_CXL_ACK}, {OrderEventType.OE_UNSOL_CXL}], "
                                             f"Found: {order_journal_or_fills_journal.order_event} - ignoring "
                                             f"strat_brief update")
                            logging.error(err_str_)
                            return
                    elif isinstance(order_journal_or_fills_journal, FillsJournal):
                        # For fills, removing current fill's qty from existing
                        # open_qty + current fill's notional (fill_qty * order_px) from existing open_notional
                        if not received_fill_after_dod:
                            fills_journal: FillsJournal = order_journal_or_fills_journal
                            open_qty = fetched_open_qty - fills_journal.fill_qty
                            open_notional = (
                                    fetched_open_notional - (
                                        fills_journal.fill_qty *
                                        self.get_usd_px(order_snapshot.order_brief.px,
                                                        order_snapshot.order_brief.security.sec_id)))
                        else:
                            # if fills come after DOD, this order's open calculation must
                            # have already removed from overall open qty and notional - no need to remove fill qty from
                            # existing open
                            open_qty = fetched_open_qty
                            open_notional = fetched_open_notional
                    else:
                        err_str_: str = ("Unsupported Journal type: Must be either OrderJournal or FillsJournal, "
                                         f"Found type: {type(order_journal_or_fills_journal)} - ignoring "
                                         f"strat_brief update")
                        logging.error(err_str_)
                        return
                    consumable_notional = (strat_limits.max_single_leg_notional -
                                           symbol_side_snapshot.total_fill_notional - open_notional)
                    consumable_open_notional = strat_limits.max_open_single_leg_notional - open_notional
                    security_float = self.static_data.get_security_float_from_ticker(symbol)
                    if security_float is not None:
                        consumable_concentration = \
                            (security_float / 100) * strat_limits.max_concentration - \
                            (open_qty + symbol_side_snapshot.total_filled_qty)
                    else:
                        consumable_concentration = 0
                    open_orders_count = (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                                         underlying_get_open_order_count_query_http(symbol))
                    consumable_open_orders = strat_limits.max_open_orders_per_side - open_orders_count[
                        0].open_order_count
                    consumable_cxl_qty = ((((symbol_side_snapshot.total_filled_qty + open_qty +
                                             symbol_side_snapshot.total_cxled_qty) / 100) *
                                           strat_limits.cancel_rate.max_cancel_rate) -
                                          symbol_side_snapshot.total_cxled_qty)
                    applicable_period_second = strat_limits.market_trade_volume_participation.applicable_period_seconds
                    executor_check_snapshot_list = \
                        (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                         underlying_get_executor_check_snapshot_query_http(
                            symbol, side, applicable_period_second))
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
                        PairSideTradingBriefOptional(
                            # security=SecurityOptional(**security.model_dump()), side=side,
                            security=security, side=side,
                            last_update_date_time=order_snapshot.last_update_date_time,
                            consumable_open_orders=consumable_open_orders,
                            consumable_notional=consumable_notional,
                            consumable_open_notional=consumable_open_notional,
                            consumable_concentration=consumable_concentration,
                            participation_period_order_qty_sum=participation_period_order_qty_sum,
                            consumable_cxl_qty=consumable_cxl_qty,
                            indicative_consumable_participation_qty=
                            indicative_consumable_participation_qty,
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
                    top_of_book_obj = self._get_top_of_book_from_symbol(symbol)
                    other_leg_top_of_book = self._get_top_of_book_from_symbol(other_leg_symbol)
                    if top_of_book_obj is not None and other_leg_top_of_book is not None:
                        if order_snapshot.order_status == OrderStatusType.OE_DOD:
                            if received_fill_after_dod:
                                residual_qty = (stored_pair_strat_trading_brief.residual_qty -
                                                order_snapshot.last_update_fill_qty)
                            else:
                                residual_qty = stored_pair_strat_trading_brief.residual_qty + \
                                               (order_snapshot.order_brief.qty - order_snapshot.filled_qty)
                            # Updating residual_qty
                            updated_pair_side_brief_obj.residual_qty = residual_qty
                        else:
                            residual_qty = stored_pair_strat_trading_brief.residual_qty
                            updated_pair_side_brief_obj.residual_qty = residual_qty
                        updated_pair_side_brief_obj.indicative_consumable_residual = \
                            strat_limits.residual_restriction.max_residual - \
                            ((residual_qty * self.get_usd_px(top_of_book_obj.last_trade.px,
                                                             top_of_book_obj.symbol)) -
                             (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_trade.px,
                                                                       other_leg_top_of_book.symbol)))
                    else:
                        logging.error(f"received buy TOB as {top_of_book_obj} and sel TOB as {other_leg_top_of_book}, "
                                      f"order_snapshot_key: {order_snapshot}")
                        return

                    # Updating consumable_nett_filled_notional
                    if symbol_side_snapshot.security.sec_id == self.strat_leg_1.sec.sec_id:
                        other_sec_id = self.strat_leg_2.sec.sec_id
                    else:
                        other_sec_id = self.strat_leg_1.sec.sec_id

                    if symbol_side_snapshot.side == Side.BUY:
                        other_side = Side.SELL
                    else:
                        other_side = Side.BUY

                    other_symbol_side_snapshot_tuple = (
                        self.strat_cache.get_symbol_side_snapshot_from_symbol(other_sec_id))
                    consumable_nett_filled_notional: float | None = None
                    if other_symbol_side_snapshot_tuple is not None:
                        other_symbol_side_snapshot, _ = other_symbol_side_snapshot_tuple
                        consumable_nett_filled_notional = (
                                strat_limits.max_net_filled_notional - abs(
                                    symbol_side_snapshot.total_fill_notional -
                                    other_symbol_side_snapshot.total_fill_notional))
                    else:
                        err_str_ = ("Received symbol_side_snapshot_tuple as None from strat_cache, "
                                    f"symbol_side_key: {get_symbol_side_key([(other_sec_id, other_side)])}")
                        logging.error(err_str_)

                    if symbol == strat_brief_obj.pair_buy_side_trading_brief.security.sec_id:
                        updated_strat_brief = StratBriefOptional(
                            _id=strat_brief_obj.id, pair_buy_side_trading_brief=updated_pair_side_brief_obj,
                            consumable_nett_filled_notional=consumable_nett_filled_notional)
                    elif symbol == strat_brief_obj.pair_sell_side_trading_brief.security.sec_id:
                        updated_strat_brief = StratBriefOptional(
                            _id=strat_brief_obj.id, pair_sell_side_trading_brief=updated_pair_side_brief_obj,
                            consumable_nett_filled_notional=consumable_nett_filled_notional)
                    else:
                        err_str_ = f"error: None of the 2 pair_side_trading_brief(s) contain symbol: {symbol} in " \
                                   f"strat_brief of key: {get_strat_brief_log_key(strat_brief_obj)};;; strat_brief: " \
                                   f"{strat_brief_obj}"
                        logging.exception(err_str_)
                        return

                    updated_strat_brief = \
                        (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                         underlying_partial_update_strat_brief_http(
                            json.loads(updated_strat_brief.model_dump_json(by_alias=True, exclude_none=True))))
                    logging.debug(f"Updated strat_brief: order_id: {order_snapshot.order_brief.order_id}, "
                                  f"strat_brief: {updated_strat_brief}")
                    return updated_strat_brief
                else:
                    logging.error(f"error: no strat_limits found in strat_cache - ignoring update of strat_brief, "
                                  f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}")
                    return

            else:
                err_str_ = f"No strat brief found in strat_cache - ignoring update of strat_brief"
                logging.exception(err_str_)
                return

    async def _update_portfolio_status_from_order_journal(
            self, order_journal_obj: OrderJournal,
            order_snapshot_obj: OrderSnapshot) -> PortfolioStatusUpdatesContainer | None:
        match order_journal_obj.order.side:
            case Side.BUY:
                update_overall_buy_notional = 0
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        update_overall_buy_notional = \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case (OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL | OrderEventType.OE_INT_REJ |
                          OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ):
                        total_buy_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        update_overall_buy_notional = \
                            -(self.get_usd_px(order_snapshot_obj.order_brief.px,
                                              order_snapshot_obj.order_brief.security.sec_id) * total_buy_unfilled_qty)
                return PortfolioStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional)
            case Side.SELL:
                update_overall_sell_notional = 0
                match order_journal_obj.order_event:
                    case OrderEventType.OE_NEW:
                        update_overall_sell_notional = \
                            self.get_usd_px(order_journal_obj.order.px, order_journal_obj.order.security.sec_id) * \
                            order_journal_obj.order.qty
                    case (OrderEventType.OE_CXL_ACK | OrderEventType.OE_UNSOL_CXL | OrderEventType.OE_INT_REJ |
                          OrderEventType.OE_BRK_REJ | OrderEventType.OE_EXH_REJ):
                        total_sell_unfilled_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        update_overall_sell_notional = \
                            -(self.get_usd_px(order_snapshot_obj.order_brief.px,
                                              order_snapshot_obj.order_brief.security.sec_id) * total_sell_unfilled_qty)
                return PortfolioStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order_journal of key: " \
                           f"{get_order_journal_log_key(order_journal_obj)} while updating strat_status;;; " \
                           f"order_journal_obj: {order_journal_obj} "
                logging.error(err_str_)
                return None

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

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock:
            res = await self._apply_fill_update_in_order_snapshot(fills_journal_obj)

            if res is not None:
                strat_id, order_snapshot, strat_brief, portfolio_status_updates = res

                # Updating and checking portfolio_limits in portfolio_manager
                post_trade_engine_service_http_client.check_portfolio_limits_query_client(
                    strat_id, None, order_snapshot, strat_brief, portfolio_status_updates)

            # else not required: if result returned from _apply_fill_update_in_order_snapshot is None, that
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding portfolio_limit checks too

    async def _update_portfolio_status_from_fill_journal(
            self, order_snapshot_obj: OrderSnapshot, received_fill_after_dod: bool
            ) -> PortfolioStatusUpdatesContainer | None:

        match order_snapshot_obj.order_brief.side:
            case Side.BUY:
                if received_fill_after_dod:
                    update_overall_buy_notional = \
                        (order_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                         order_snapshot_obj.order_brief.security.sec_id))
                else:
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
                return PortfolioStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional,
                                                       buy_fill_notional_update=update_overall_buy_fill_notional)
            case Side.SELL:
                if received_fill_after_dod:
                    update_overall_sell_notional = \
                        (order_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                         order_snapshot_obj.order_brief.security.sec_id))
                else:
                    update_overall_sell_notional = \
                        (order_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                         order_snapshot_obj.order_brief.security.sec_id)) - \
                        (order_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(order_snapshot_obj.order_brief.px,
                                         order_snapshot_obj.order_brief.security.sec_id))
                update_overall_sell_fill_notional = \
                    self.get_usd_px(order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id) * \
                    order_snapshot_obj.last_update_fill_qty
                return PortfolioStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional,
                                                       sell_fill_notional_update=update_overall_sell_fill_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in order snapshot of key " \
                           f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                           f"order_snapshot: {order_snapshot_obj}"
                logging.error(err_str_)
                return None

    async def _update_symbol_side_snapshot_from_fill_applied_order_snapshot(
            self, order_snapshot_obj: OrderSnapshot, received_fill_after_dod: bool) -> SymbolSideSnapshot:
        async with SymbolSideSnapshot.reentrant_lock:
            symbol_side_snapshot_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(
                order_snapshot_obj.order_brief.security.sec_id)

            if symbol_side_snapshot_tuple is not None:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_tuple
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
                if received_fill_after_dod:
                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                        symbol_side_snapshot_obj.total_cxled_qty - order_snapshot_obj.last_update_fill_qty)
                    updated_symbol_side_snapshot_obj.total_cxled_notional = (
                        symbol_side_snapshot_obj.total_cxled_notional -
                        (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                     order_snapshot_obj.order_brief.security.sec_id)))

                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_side_snapshot_http(
                            json.loads(updated_symbol_side_snapshot_obj.model_dump_json(
                                by_alias=True, exclude_none=True))))
                return updated_symbol_side_snapshot_obj
            else:
                err_str_ = ("Received symbol_side_snapshot_tuple as None from strat_cache for symbol: "
                            f"{order_snapshot_obj.order_brief.security.sec_id}, "
                            f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)} - "
                            f"ignoring this symbol_side_snapshot update from fills")
                logging.error(err_str_)

    def set_strat_state_to_pause(self):
        pair_strat = PairStratBaseModel(_id=self.pair_strat_id,
                                        strat_state=StratState.StratState_PAUSED)
        # strat_manager_service_http_client.patch_pair_strat_client(jsonable_encoder(pair_strat, by_alias=True,
        #                                                                            exclude_none=True))
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, strat_manager_service_http_client.patch_pair_strat_client,
            _id=self.pair_strat_id, strat_state=StratState.StratState_PAUSED)

    async def _apply_fill_update_in_order_snapshot(
            self, fills_journal_obj: FillsJournal) -> Tuple[int, OrderSnapshot, StratBrief,
                                                            PortfolioStatusUpdatesContainer| None] | None:
        pair_strat = self.strat_cache.get_pair_strat_obj()

        if not is_ongoing_strat(pair_strat):
            # avoiding any update if strat is non-ongoing
            return

        async with (OrderSnapshot.reentrant_lock):    # for read-write atomicity
            order_snapshot_obj = self.strat_cache.get_order_snapshot_from_order_id(fills_journal_obj.order_id)

            if order_snapshot_obj is not None:
                if order_snapshot_obj.order_status in [OrderStatusType.OE_ACKED, OrderStatusType.OE_DOD,
                                                       OrderStatusType.OE_CXL_UNACK]:
                    received_fill_after_dod = False
                    if order_snapshot_obj.order_status == OrderStatusType.OE_DOD:
                        received_fill_after_dod = True

                    if (total_filled_qty := order_snapshot_obj.filled_qty) is not None:
                        updated_total_filled_qty = total_filled_qty + fills_journal_obj.fill_qty
                    else:
                        updated_total_filled_qty = fills_journal_obj.fill_qty
                    received_fill_notional = fills_journal_obj.fill_notional
                    last_update_fill_qty = fills_journal_obj.fill_qty
                    last_update_fill_px = fills_journal_obj.fill_px
                    updated_cxl_qty = None
                    updated_cxl_notional = None
                    order_status = None

                    pause_strat: bool = False

                    if order_snapshot_obj.order_brief.qty == updated_total_filled_qty:
                        pause_fulfill_post_order_dod: bool = (
                            executor_config_yaml_dict.get("pause_fulfill_post_order_dod"))
                        if received_fill_after_dod and pause_fulfill_post_order_dod:
                            logging.critical("Unexpected: Received fill that makes order_snapshot OE_FILLED which is "
                                             "already of state OE_DOD, ignoring this fill and putting this strat to "
                                             f"PAUSE, symbol_side_key: {get_order_snapshot_log_key(order_snapshot_obj)}"
                                             f";;; fills_journal {fills_journal_obj}, order_snapshot: "
                                             f"{order_snapshot_obj}")
                            pause_strat = True
                        else:
                            order_status = OrderStatusType.OE_FILLED
                            updated_cxl_qty = order_snapshot_obj.cxled_qty - fills_journal_obj.fill_qty
                            updated_cxl_notional = (
                                    updated_cxl_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                      order_snapshot_obj.order_brief.security.sec_id))
                    elif order_snapshot_obj.order_brief.qty < updated_total_filled_qty:
                        vacant_fill_qty = order_snapshot_obj.order_brief.qty - order_snapshot_obj.filled_qty
                        non_required_received_fill_qty = fills_journal_obj.fill_qty - vacant_fill_qty

                        if received_fill_after_dod:
                            logging.critical(
                                f"Unexpected: Received fill that will make order_snapshot OVER_FILLED which "
                                f"is already OE_DOD, vacant_fill_qty: {vacant_fill_qty}, received fill_qty: "
                                f"{fills_journal_obj.fill_qty}, extra_qty: {non_required_received_fill_qty} "
                                f"from fills_journal_key {get_fills_journal_log_key(fills_journal_obj)} - "
                                f"ignoring order_snapshot updates for this fill and putting strat to PAUSE"
                                f"symbol_side_key: {get_order_snapshot_log_key(order_snapshot_obj)}"
                                f";;; fills_journal {fills_journal_obj}, order_snapshot: "
                                f"{order_snapshot_obj}")
                        else:
                            logging.critical(
                                f"Unexpected: Received fill that will make order_snapshot OVER_FILLED, "
                                f"vacant_fill_qty: {vacant_fill_qty}, received fill_qty: "
                                f"{fills_journal_obj.fill_qty}, extra_qty: {non_required_received_fill_qty} "
                                f"from fills_journal_key {get_fills_journal_log_key(fills_journal_obj)} - "
                                f"ignoring order_snapshot updates for this fill and putting strat to PAUSE"
                                f"symbol_side_key: {get_order_snapshot_log_key(order_snapshot_obj)}"
                                f";;; fills_journal {fills_journal_obj}, order_snapshot: "
                                f"{order_snapshot_obj}")
                        pause_strat = True
                    else:
                        if received_fill_after_dod:
                            updated_cxl_qty = order_snapshot_obj.cxled_qty - fills_journal_obj.fill_qty
                            updated_cxl_notional = (
                                updated_cxl_qty * self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                                  order_snapshot_obj.order_brief.security.sec_id))

                    if pause_strat:
                        self.set_strat_state_to_pause()
                        return None
                    # else not required: If pause is not triggered, updating order_snapshot and other models

                    if (last_filled_notional := order_snapshot_obj.fill_notional) is not None:
                        updated_fill_notional = last_filled_notional + received_fill_notional
                    else:
                        updated_fill_notional = received_fill_notional
                    updated_avg_fill_px = \
                        self.get_local_px_or_notional(updated_fill_notional,
                                                      fills_journal_obj.fill_symbol) / updated_total_filled_qty

                    order_snapshot_obj = \
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_partial_update_order_snapshot_http(json.loads(OrderSnapshotOptional(
                                _id=order_snapshot_obj.id, filled_qty=updated_total_filled_qty,
                                avg_fill_px=updated_avg_fill_px, fill_notional=updated_fill_notional,
                                last_update_fill_qty=last_update_fill_qty, last_update_fill_px=last_update_fill_px,
                                cxled_qty=updated_cxl_qty, cxled_notional=updated_cxl_notional,
                                last_update_date_time=fills_journal_obj.fill_date_time,
                                order_status=order_status).model_dump_json(by_alias=True, exclude_none=True))))
                    symbol_side_snapshot = \
                        await self._update_symbol_side_snapshot_from_fill_applied_order_snapshot(
                            order_snapshot_obj, received_fill_after_dod=received_fill_after_dod)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_order_or_fill(
                            fills_journal_obj, order_snapshot_obj, symbol_side_snapshot,
                            received_fill_after_dod=received_fill_after_dod)
                        if updated_strat_brief is not None:
                            await self._update_strat_status_from_fill_journal(
                                order_snapshot_obj, symbol_side_snapshot, updated_strat_brief,
                                received_fill_after_dod=received_fill_after_dod)
                        # else not required: if updated_strat_brief is None then it means some error occurred in
                        # _update_strat_brief_from_order which would have got added to alert already
                        portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                            await self._update_portfolio_status_from_fill_journal(
                                order_snapshot_obj, received_fill_after_dod=received_fill_after_dod))

                        return pair_strat.id, order_snapshot_obj, updated_strat_brief, portfolio_status_updates

                    # else not require_create_update_symbol_side_snapshot_from_order_journald: if symbol_side_snapshot
                    # is None then it means error occurred in _create_update_symbol_side_snapshot_from_order_journal
                    # which would have got added to alert already
                elif order_snapshot_obj.order_status == OrderStatusType.OE_FILLED:
                    err_str_ = (f"Unsupported - Fill received for completely filled order_snapshot, "
                                f"order_snapshot_key: {get_order_snapshot_log_key(order_snapshot_obj)}, "
                                f"ignoring this fill journal - putting strat to PAUSE;;; "
                                f"fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}")
                    logging.critical(err_str_)
                    self.set_strat_state_to_pause()
                else:
                    err_str_ = f"Unsupported - Fill received for order_snapshot having status " \
                               f"{order_snapshot_obj.order_status}, order_snapshot_key: " \
                               f"{get_order_snapshot_log_key(order_snapshot_obj)};;; " \
                               f"fill_journal: {fills_journal_obj}, order_snapshot: {order_snapshot_obj}"
                    logging.error(err_str_)
            else:
                err_str_ = (f"Could not find any order snapshot with order-id {fills_journal_obj.order_id} in "
                            f"strat_cache, fill_journal_key: {get_fills_journal_log_key(fills_journal_obj)}")
                logging.error(err_str_)

    async def _update_strat_status_from_fill_journal(self, order_snapshot_obj: OrderSnapshot,
                                                     symbol_side_snapshot: SymbolSideSnapshot,
                                                     strat_brief_obj: StratBrief,
                                                     received_fill_after_dod: bool):
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        async with StratStatus.reentrant_lock:
            strat_status_tuple = self.strat_cache.get_strat_status()

            if strat_limits_tuple is not None and strat_status_tuple is not None:
                strat_limits, _ = strat_limits_tuple
                fetched_strat_status_obj, _ = strat_status_tuple

                update_strat_status_obj = StratStatusOptional(_id=fetched_strat_status_obj.id)
                match order_snapshot_obj.order_brief.side:
                    case Side.BUY:
                        if not received_fill_after_dod:
                            update_strat_status_obj.total_open_buy_qty = (fetched_strat_status_obj.total_open_buy_qty -
                                                                          order_snapshot_obj.last_update_fill_qty)
                            update_strat_status_obj.total_open_buy_notional = (
                                    fetched_strat_status_obj.total_open_buy_notional -
                                    (order_snapshot_obj.last_update_fill_qty *
                                     self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                     order_snapshot_obj.order_brief.security.sec_id)))
                            update_strat_status_obj.total_open_sell_notional = (
                                fetched_strat_status_obj.total_open_sell_notional)
                            if fetched_strat_status_obj.total_open_buy_qty == 0:
                                update_strat_status_obj.avg_open_buy_px = 0
                            else:
                                update_strat_status_obj.avg_open_buy_px = \
                                    self.get_local_px_or_notional(fetched_strat_status_obj.total_open_buy_notional,
                                                                  order_snapshot_obj.order_brief.security.sec_id) / \
                                    fetched_strat_status_obj.total_open_buy_qty
                        update_strat_status_obj.total_fill_buy_qty = (
                                fetched_strat_status_obj.total_fill_buy_qty + order_snapshot_obj.last_update_fill_qty)
                        update_strat_status_obj.total_fill_buy_notional = (
                                fetched_strat_status_obj.total_fill_buy_notional +
                                order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                    order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id))
                        update_strat_status_obj.avg_fill_buy_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_fill_buy_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            update_strat_status_obj.total_fill_buy_qty
                        update_strat_status_obj.total_fill_sell_notional = (
                            fetched_strat_status_obj.total_fill_sell_notional)
                        if received_fill_after_dod:
                            update_strat_status_obj.total_cxl_buy_qty = (
                                    fetched_strat_status_obj.total_cxl_buy_qty -
                                    order_snapshot_obj.last_update_fill_qty)
                            update_strat_status_obj.total_cxl_buy_notional = (
                                fetched_strat_status_obj.total_cxl_buy_notional -
                                (self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                 order_snapshot_obj.order_brief.security.sec_id) *
                                 order_snapshot_obj.last_update_fill_qty))
                            update_strat_status_obj.total_cxl_sell_notional = (
                                fetched_strat_status_obj.total_cxl_sell_notional)

                    case Side.SELL:
                        if not received_fill_after_dod:
                            update_strat_status_obj.total_open_sell_qty = (
                                    fetched_strat_status_obj.total_open_sell_qty -
                                    order_snapshot_obj.last_update_fill_qty)
                            update_strat_status_obj.total_open_sell_notional = (
                                    fetched_strat_status_obj.total_open_sell_notional -
                                    (order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                        order_snapshot_obj.order_brief.px,
                                        order_snapshot_obj.order_brief.security.sec_id)))
                            update_strat_status_obj.total_open_buy_notional = (
                                fetched_strat_status_obj.total_open_buy_notional)
                            if update_strat_status_obj.total_open_sell_qty == 0:
                                update_strat_status_obj.avg_open_sell_px = 0
                            else:
                                update_strat_status_obj.avg_open_sell_px = \
                                    self.get_local_px_or_notional(fetched_strat_status_obj.total_open_sell_notional,
                                                                  order_snapshot_obj.order_brief.security.sec_id) / \
                                    fetched_strat_status_obj.total_open_sell_qty
                        update_strat_status_obj.total_fill_sell_qty = (
                                fetched_strat_status_obj.total_fill_sell_qty + order_snapshot_obj.last_update_fill_qty)
                        update_strat_status_obj.total_fill_sell_notional = (
                                fetched_strat_status_obj.total_fill_sell_notional +
                                order_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                    order_snapshot_obj.last_update_fill_px,
                                    order_snapshot_obj.order_brief.security.sec_id))
                        update_strat_status_obj.avg_fill_sell_px = \
                            self.get_local_px_or_notional(update_strat_status_obj.total_fill_sell_notional,
                                                          order_snapshot_obj.order_brief.security.sec_id) / \
                            update_strat_status_obj.total_fill_sell_qty
                        update_strat_status_obj.total_fill_buy_notional = (
                            fetched_strat_status_obj.total_fill_buy_notional)

                        if received_fill_after_dod:
                            update_strat_status_obj.total_cxl_sell_qty = (
                                    fetched_strat_status_obj.total_cxl_sell_qty -
                                    order_snapshot_obj.last_update_fill_qty)
                            update_strat_status_obj.total_cxl_sell_notional = (
                                fetched_strat_status_obj.total_cxl_sell_notional -
                                (self.get_usd_px(order_snapshot_obj.order_brief.px,
                                                 order_snapshot_obj.order_brief.security.sec_id) *
                                 order_snapshot_obj.last_update_fill_qty))
                            update_strat_status_obj.total_cxl_buy_notional = (
                                fetched_strat_status_obj.total_cxl_buy_notional)
                    case other_:
                        err_str_ = f"Unsupported Side Type {other_} received for order_snapshot_key: " \
                                   f"{get_order_snapshot_log_key(order_snapshot_obj)} while updating strat_status;;; " \
                                   f"order_snapshot: {order_snapshot_obj}"
                        logging.error(err_str_)
                        return
                if not received_fill_after_dod:
                    update_strat_status_obj.total_open_exposure = (update_strat_status_obj.total_open_buy_notional -
                                                                   update_strat_status_obj.total_open_sell_notional)
                update_strat_status_obj.total_fill_exposure = (update_strat_status_obj.total_fill_buy_notional -
                                                               update_strat_status_obj.total_fill_sell_notional)
                if received_fill_after_dod:
                    update_strat_status_obj.total_cxl_exposure = (update_strat_status_obj.total_cxl_buy_notional -
                                                                  update_strat_status_obj.total_cxl_sell_notional)
                if update_strat_status_obj.total_fill_buy_notional < update_strat_status_obj.total_fill_sell_notional:
                    update_strat_status_obj.balance_notional = \
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_buy_notional
                else:
                    update_strat_status_obj.balance_notional = \
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_sell_notional

                updated_residual = self.__get_residual_obj(order_snapshot_obj.order_brief.side, strat_brief_obj)
                if updated_residual is not None:
                    update_strat_status_obj.residual = updated_residual

                # Updating strat_state as paused if limits get breached
                self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                     strat_brief_obj, symbol_side_snapshot)

                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_strat_status_http(
                    json.loads(update_strat_status_obj.model_dump_json(by_alias=True, exclude_none=True)))
            else:
                logging.error(f"error: either tuple of strat_status or strat_limits received as None from cache;;; "
                              f"strat_status_tuple: {strat_status_tuple}, strat_limits_tuple: {strat_limits_tuple}")
                return

    async def _check_n_delete_symbol_side_snapshot_from_unload_strat(self) -> bool:
        pair_symbol_side_list = [
            (self.strat_leg_1.sec, self.strat_leg_1.side),
            (self.strat_leg_2.sec, self.strat_leg_2.side)
        ]

        for security, side in pair_symbol_side_list:
            symbol_side_snapshots_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(security.sec_id)

            if symbol_side_snapshots_tuple is not None:
                symbol_side_snapshot, _ = symbol_side_snapshots_tuple
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_symbol_side_snapshot_http(
                    symbol_side_snapshot.id)
        return True

    async def _check_n_delete_strat_brief_for_unload_strat(self) -> bool:
        symbol = self.strat_leg_1.sec.sec_id
        strat_brief_obj_tuple = self.strat_cache.get_strat_brief()

        if strat_brief_obj_tuple is not None:
            strat_brief_obj, _ = strat_brief_obj_tuple
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_strat_brief_http(
                strat_brief_obj.id)
        return True

    async def _force_unpublish_symbol_overview_from_unload_strat(self) -> bool:
        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]

        async with SymbolOverview.reentrant_lock:
            for symbol in symbols_list:
                symbol_overview_tuple = self.strat_cache.get_symbol_overview_from_symbol(symbol)

                if symbol_overview_tuple is not None:
                    symbol_overview_obj, _ = symbol_overview_tuple
                    updated_symbol_overview = FxSymbolOverviewBaseModel(_id=symbol_overview_obj.id,
                                                                        force_publish=False)
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_overview_http(
                            jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True)))

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

    async def create_symbol_side_snapshot_post(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot_obj)

    async def update_symbol_side_snapshot_post(self, stored_symbol_side_snapshot_obj: SymbolSideSnapshot,
                                               updated_symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def partial_update_symbol_side_snapshot_post(self, stored_symbol_side_snapshot_obj: SymbolSideSnapshot,
                                                       updated_symbol_side_snapshot_obj: SymbolSideSnapshotOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                       updated_strat_status_obj: StratStatus):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_status_obj.id,
                                                 balance_notional=
                                                 updated_strat_status_obj.balance_notional)
        logging.info(log_str)

    async def partial_update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                               updated_strat_status_obj: StratStatus):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_status_obj.id,
                                                 balance_notional=
                                                 updated_strat_status_obj.balance_notional)
        logging.info(log_str)

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

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=strat_status_obj.id,
                                                 balance_notional=
                                                 strat_status_obj.balance_notional)
        logging.info(log_str)

    async def create_strat_limits_post(self, strat_limits_obj: StratLimits):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=strat_limits_obj.id,
                                                 max_single_leg_notional=
                                                 strat_limits_obj.max_single_leg_notional)
        logging.info(log_str)

    async def update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                       updated_strat_limits_obj: StratLimits):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_limits_obj.id,
                                                 max_single_leg_notional=
                                                 updated_strat_limits_obj.max_single_leg_notional)
        logging.info(log_str)

    async def partial_update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                               updated_strat_limits_obj: StratLimitsOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 strat_manager_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_limits_obj.id,
                                                 max_single_leg_notional=
                                                 updated_strat_limits_obj.max_single_leg_notional)
        logging.info(log_str)

    async def create_new_order_post(self, new_order_obj: NewOrder):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_new_order_get_all_ws(new_order_obj)

    async def create_cancel_order_post(self, cancel_order_obj: CancelOrder):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_cancel_order_get_all_ws(cancel_order_obj)

    async def partial_update_cancel_order_post(self, stored_cancel_order_obj: CancelOrder,
                                               updated_cancel_order_obj: CancelOrderOptional):
        # updating trading_data_manager's strat_cache
        self.trading_data_manager.handle_cancel_order_get_all_ws(updated_cancel_order_obj)

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
            symbol_overview_obj.force_publish = False  # setting it false if at create it is True
            if self.trading_data_manager:
                self.trading_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
            # else not required: since symbol overview is required to make executor service ready,
            #                    will add this to strat_cache explicitly using underlying http call

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
        symbol_side_snapshot_objs = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_side_snapshot_http(
                get_symbol_side_snapshot_from_symbol_side(security_id, side), self.get_generic_read_route())

        if len(symbol_side_snapshot_objs) > 1:
            err_str_ = f"Found multiple objects of symbol_side_snapshot for key: " \
                       f"{get_symbol_side_key([(security_id, side)])}"
            logging.error(err_str_)

        return symbol_side_snapshot_objs

    async def update_residuals_query_pre(self, pair_strat_class_type: Type[StratStatus], security_id: str, side: Side,
                                         residual_qty: int):
        async with (StreetBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock):
            strat_brief_tuple = self.strat_cache.get_strat_brief()

            if strat_brief_tuple is not None:
                strat_brief_obj, _ = strat_brief_tuple
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

                updated_strat_brief = (
                    await StreetBookServiceRoutesCallbackBaseNativeOverride.
                    underlying_partial_update_strat_brief_http(
                        json.loads(update_strat_brief.model_dump_json(by_alias=True, exclude_none=True))))
            else:
                err_str_ = (f"No strat_brief found from strat_cache for symbol_side_key: "
                            f"{get_symbol_side_key([(security_id, side)])}")
                logging.exception(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)

            # updating pair_strat's residual notional
            async with StratStatus.reentrant_lock:
                strat_status_tuple = self.strat_cache.get_strat_status()

                if strat_status_tuple is not None:
                    strat_status, _ = strat_status_tuple
                    updated_residual = self.__get_residual_obj(side, updated_strat_brief)
                    if updated_residual is not None:
                        strat_status = StratStatusOptional(_id=strat_status.id,
                                                           residual=updated_residual)
                                                           # residual=ResidualOptional(**updated_residual.model_dump()))
                        (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                         underlying_partial_update_strat_status_http(
                            jsonable_encoder(strat_status, by_alias=True, exclude_none=True)))
                    else:
                        err_str_ = f"Something went wrong while computing residual for security_side_key: " \
                                   f"{get_symbol_side_key([(security_id, side)])}"
                        logging.exception(err_str_)
                        raise HTTPException(status_code=500, detail=err_str_)
                else:
                    err_str_ = ("Received strat_status_tuple as None from strat_cache - ignoring strat_status update "
                                "for residual changes")
                    logging.exception(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)

            # nothing to send since this query updates residuals only
            return []

    async def get_open_order_count_query_pre(self, open_order_count_class_type: Type[OpenOrderCount], symbol: str):
        open_orders = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_order_snapshot_http(
                get_open_order_snapshots_for_symbol(symbol), self.get_generic_read_route())

        open_order_count = OpenOrderCount(open_order_count=len(open_orders))
        return [open_order_count]

    async def get_underlying_account_cumulative_fill_qty_query_pre(
            self, underlying_account_cum_fill_qty_class_type: Type[UnderlyingAccountCumFillQty],
            symbol: str, side: str):
        fill_journal_obj_list = \
            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                   get_symbol_side_underlying_account_cumulative_fill_qty_query_http(symbol, side))

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
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_fills_journal_http(
            get_symbol_side_underlying_account_cumulative_fill_qty(symbol, side), self.get_generic_read_route())

    async def cxl_expired_open_orders(self):
        open_order_snapshots_list: List[OrderSnapshot] = self.strat_cache.get_open_order_snapshots()

        for open_order_snapshot in open_order_snapshots_list:
            if (open_order_snapshot.order_status != OrderStatusType.OE_CXL_UNACK and
                    open_order_snapshot.order_status not in [OrderStatusType.OE_DOD, OrderStatusType.OE_FILLED]):
                strat_limits_tuple = self.strat_cache.get_strat_limits()
                time_delta = DateTime.utcnow() - open_order_snapshot.create_date_time

                if strat_limits_tuple is not None:
                    strat_limits, _ = strat_limits_tuple
                    if time_delta.total_seconds() > strat_limits.residual_restriction.residual_mark_seconds:
                        logging.info(f"Triggering cxl_expired_open_orders, order_id: "
                                     f"{open_order_snapshot.order_brief.order_id}")
                        await StreetBook.trading_link.place_cxl_order(
                            open_order_snapshot.order_brief.order_id, open_order_snapshot.order_brief.side,
                            open_order_snapshot.order_brief.security.sec_id,
                            open_order_snapshot.order_brief.security.sec_id,
                            open_order_snapshot.order_brief.underlying_account)
                    # else not required: If time-delta is still less than residual_mark_seconds then avoiding
                    # cancellation of order
                else:
                    logging.error("Received strat_limits_tuple as None from strat_cache, ignoring cxl expiring order "
                                  f"for this call, will retry again in {self.min_refresh_interval} secs")
            elif open_order_snapshot.order_status == OrderStatusType.OE_DOD:
                logging.error("Unexpected: Received open_order_snapshot with order_status OE_DOD, likely bug in "
                              "get_open_order_snapshots - list provided must not have any order_snapshot "
                              "that is non-open")
            elif open_order_snapshot.order_status == OrderStatusType.OE_FILLED:
                logging.error("Unexpected: Received open_order_snapshot with order_status OE_FILLED, likely bug in "
                              "get_open_order_snapshots - list provided must not have any order_snapshot "
                              "that is non-open")
            # else not required: avoiding cxl request if order_snapshot already got cxl request

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http(
            get_strat_brief_from_symbol(security_id), self.get_generic_read_route())

    async def get_executor_check_snapshot_query_pre(
            self, executor_check_snapshot_class_type: Type[ExecutorCheckSnapshot], symbol: str,
            side: Side, last_n_sec: int):

        last_n_sec_order_qty = await self.get_last_n_sec_order_qty(symbol, side, last_n_sec)
        logging.debug(f"Received last_n_sec_order_qty: {last_n_sec_order_qty}, symbol: {symbol}, side: {Side}")

        last_n_sec_trade_qty = await self.get_last_n_sec_trade_qty(symbol, side)
        logging.debug(f"Received last_n_sec_trade_qty: {last_n_sec_trade_qty}, symbol: {symbol}, side: {Side}")

        if last_n_sec_order_qty is not None and \
                last_n_sec_trade_qty is not None:
            # if no data is found by respective queries then all fields are set to 0 and every call returns
            # executor_check_snapshot object (except when exception occurs)
            executor_check_snapshot = \
                ExecutorCheckSnapshot(last_n_sec_trade_qty=last_n_sec_trade_qty,
                                      last_n_sec_order_qty=last_n_sec_order_qty)
            return [executor_check_snapshot]
        else:
            # will only return [] if some error occurred
            logging.error(f"no executor_check_snapshot for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, as"
                          f"Received last_n_sec_order_qty: {last_n_sec_order_qty}, last_n_sec_trade_qty: "
                          f"{last_n_sec_trade_qty} & last_n_sec: {last_n_sec}; returning empty list []")
            return []

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(
            get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import get_objs_from_symbol
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    async def get_last_n_sec_total_trade_qty_query_pre(
            self, last_sec_market_trade_vol_class_type: Type[LastNSecMarketTradeVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketTradeVol]:
        last_trade_obj_list = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_trade_http(
                get_last_n_sec_total_trade_qty(symbol, last_n_sec))
        last_n_sec_trade_vol = 0
        if last_trade_obj_list:
            last_n_sec_trade_vol = \
                last_trade_obj_list[-1].market_trade_volume.participation_period_last_trade_qty_sum

        return [LastNSecMarketTradeVol(last_n_sec_trade_vol=last_n_sec_trade_vol)]

    async def put_strat_to_snooze_query_pre(self, strat_status_class_type: Type[StratStatus]):
        # removing current strat_status
        await self._check_n_remove_strat_status()

        # removing current strat limits
        await self._check_n_remove_strat_limits()

        # If strat_cache stopped means strat is not ongoing anymore or was never ongoing
        # - removing related models that would have created if strat got activated
        if self.strat_cache.stopped:
            # deleting strat's both leg's symbol_side_snapshots
            await self._check_n_delete_symbol_side_snapshot_from_unload_strat()

            # deleting strat's strat_brief
            await self._check_n_delete_strat_brief_for_unload_strat()

            # making force publish flag back to false for current strat's symbol's symbol_overview
            await self._force_unpublish_symbol_overview_from_unload_strat()

        # removing strat_alert
        try:
            log_analyzer_service_http_client.delete_strat_alert_client(self.pair_strat_id)
        except Exception as e:
            if '{"detail":"Id not Found:' in str(e):
                logging.info(f"Strat Alert with id: {self.pair_strat_id} not found while deleting strat_alert")
            else:
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

    async def get_market_depths_query_pre(self, market_depth_class_type: Type[MarketDepth],
                                          payload_dict: Dict[str, Any]):
        symbol_side_tuple_list = payload_dict.get("symbol_side_tuple_list")
        if symbol_side_tuple_list is None:
            err_str_ = "Can't find symbol_side_tuple_list in payload from query"
            logging.error(err_str_)
            raise HTTPException(detail=err_str_, status_code=503)

        market_depth_list: List[MarketDepth] = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_market_depth_http(
            get_market_depths(symbol_side_tuple_list))
        return market_depth_list

    #########################
    # Trade Simulator Queries
    #########################

    async def trade_simulator_place_new_order_query_pre(
            self, trade_simulator_process_new_order_class_type: Type[TradeSimulatorProcessNewOrder],
            px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
            underlying_account: str, exchange: str | None = None):
        if TradeSimulator.symbol_configs is None:
            TradeSimulator.reload_symbol_configs()
        await TradeSimulator.place_new_order(px, qty, side, trading_sec_id, system_sec_id, underlying_account, exchange)
        return []

    async def trade_simulator_place_cxl_order_query_pre(
            self, trade_simulator_process_cxl_order_class_type: Type[TradeSimulatorProcessCxlOrder],
            order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
            system_sec_id: str | None = None, underlying_account: str | None = None):
        if TradeSimulator.symbol_configs is None:
            TradeSimulator.reload_symbol_configs()
        await TradeSimulator.place_cxl_order(order_id, side, trading_sec_id, system_sec_id, underlying_account)
        return []

    async def trade_simulator_process_order_ack_query_pre(
            self, trade_simulator_process_order_ack_class_type: Type[TradeSimulatorProcessOrderAck], order_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        if TradeSimulator.symbol_configs is None:
            TradeSimulator.reload_symbol_configs()
        await TradeSimulator.process_order_ack(order_id, px, qty, side, sec_id, underlying_account)
        return []

    async def trade_simulator_process_fill_query_pre(
            self, trade_simulator_process_fill_class_type: Type[TradeSimulatorProcessFill], order_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        if TradeSimulator.symbol_configs is None:
            TradeSimulator.reload_symbol_configs()
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
