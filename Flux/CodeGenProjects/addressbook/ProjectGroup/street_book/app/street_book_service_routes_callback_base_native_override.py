# standard imports
import logging
import os
import threading
import time
import copy
import shutil
import sys
import stat
import subprocess
from typing import Set
import ctypes

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_routes_callback import (
    StreetBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_chore_journal_log_key, get_symbol_side_key, get_chore_snapshot_log_key,
    get_symbol_side_snapshot_log_key, all_service_up_check, host, EXECUTOR_PROJECT_DATA_DIR,
    email_book_service_http_client, get_consumable_participation_qty,
    get_strat_brief_log_key, get_fills_journal_log_key, get_new_strat_limits, get_new_strat_status,
    log_book_service_http_client, executor_config_yaml_dict,
    EXECUTOR_PROJECT_SCRIPTS_DIR, post_book_service_http_client, MobileBookMutexManager)
from FluxPythonUtils.scripts.utility_functions import (
    avg_of_new_val_sum_to_avg, find_free_port, except_n_log_alert, create_logger)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    create_md_shell_script, MDShellEnvData, PairStratBaseModel, StratState, is_ongoing_strat,
    guaranteed_call_pair_strat_client, pair_strat_client_call_log_str, UpdateType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.barter_simulator import BarterSimulator, BarteringLinkBase
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import is_test_run
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.generated.Pydentic.log_book_service_model_imports import StratAlertBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.strat_cache import StratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_key_handler import (
    EmailBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_client import (
    StreetBookServiceHttpClient)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_chore_total_sum_of_last_n_sec, get_symbol_side_snapshot_from_symbol_side, get_strat_brief_from_symbol,
    get_open_chore_snapshots_for_symbol, get_symbol_side_underlying_account_cumulative_fill_qty,
    get_symbol_overview_from_symbol, get_last_n_sec_total_barter_qty, get_market_depths,
    get_last_n_chore_journals_from_chore_id, get_last_n_sec_first_n_last_barter)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.Pydentic.post_book_service_model_imports import (
    PortfolioStatusUpdatesContainer)
from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import (
    StratLeg, FxSymbolOverviewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import StratViewBaseModel
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import photo_book_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book import (
    StreetBook, BarteringDataManager, TopOfBook, MarketDepth, MobileBookContainerCache,
    add_container_obj_for_symbol)


class FirstLastBarterCont(BaseModel):
    id: int | None = Field(None, alias="_id")
    first: LastBarterOptional | None = None
    last: LastBarterOptional | None = None
    model_config = ConfigDict(populate_by_name=True, extra='forbid')


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
    underlying_read_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_read_chore_journal_http: Callable[..., Any] | None = None
    underlying_get_last_n_sec_total_barter_qty_query_http: Callable[..., Any] | None = None
    get_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_create_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_update_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_side_snapshot_http: Callable[..., Any] | None = None
    underlying_partial_update_cancel_chore_http: Callable[..., Any] | None = None
    underlying_partial_update_strat_status_http: Callable[..., Any] | None = None
    underlying_get_open_chore_count_query_http: Callable[..., Any] | None = None
    underlying_partial_update_strat_brief_http: Callable[..., Any] | None = None
    underlying_delete_symbol_side_snapshot_http: Callable[..., Any] | None = None
    get_symbol_side_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_read_fills_journal_http: Callable[..., Any] | None = None
    underlying_read_last_barter_http: Callable[..., Any] | None = None
    underlying_is_strat_ongoing_query_http: Callable[..., Any] | None = None
    underlying_delete_strat_brief_http: Callable[..., Any] | None = None
    underlying_create_cancel_chore_http: Callable[..., Any] | None = None
    underlying_read_market_depth_http: Callable[..., Any] | None = None
    underlying_read_strat_status_http: Callable[..., Any] | None = None
    underlying_read_strat_status_by_id_http: Callable[..., Any] | None = None
    underlying_read_cancel_chore_http: Callable[..., Any] | None = None
    underlying_read_strat_limits_http: Callable[..., Any] | None = None
    underlying_delete_strat_status_http: Callable[..., Any] | None = None
    underlying_barter_simulator_place_cxl_chore_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes import (
            underlying_read_strat_brief_http, residual_compute_shared_lock, journal_shared_lock,
            underlying_create_strat_limits_http, underlying_delete_strat_limits_http,
            underlying_create_strat_status_http, underlying_update_strat_status_http,
            underlying_get_executor_check_snapshot_query_http, underlying_create_strat_brief_http,
            underlying_read_symbol_side_snapshot_http, underlying_create_symbol_side_snapshot_http,
            underlying_partial_update_symbol_overview_http, underlying_read_strat_limits_by_id_http,
            underlying_read_symbol_overview_http, underlying_create_cancel_chore_http,
            underlying_read_top_of_book_http, underlying_get_top_of_book_from_symbol_query_http,
            underlying_read_chore_snapshot_http, underlying_read_chore_journal_http,
            underlying_get_last_n_sec_total_barter_qty_query_http, underlying_partial_update_cancel_chore_http,
            get_underlying_account_cumulative_fill_qty_query_http, underlying_create_chore_snapshot_http,
            underlying_update_chore_snapshot_http, underlying_partial_update_symbol_side_snapshot_http,
            underlying_partial_update_strat_status_http, underlying_get_open_chore_count_query_http,
            underlying_partial_update_strat_brief_http, underlying_delete_symbol_side_snapshot_http,
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http, underlying_read_fills_journal_http,
            underlying_read_last_barter_http,
            underlying_delete_strat_brief_http, underlying_read_market_depth_http, underlying_read_strat_status_http,
            underlying_read_strat_status_by_id_http, underlying_read_cancel_chore_http,
            underlying_read_strat_limits_http, underlying_delete_strat_status_http,
            underlying_barter_simulator_place_cxl_chore_query_http)

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
        cls.underlying_read_chore_snapshot_http = underlying_read_chore_snapshot_http
        cls.underlying_read_chore_journal_http = underlying_read_chore_journal_http
        cls.underlying_get_last_n_sec_total_barter_qty_query_http = underlying_get_last_n_sec_total_barter_qty_query_http
        cls.get_underlying_account_cumulative_fill_qty_query_http = (
            get_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_create_chore_snapshot_http = underlying_create_chore_snapshot_http
        cls.underlying_update_chore_snapshot_http = underlying_update_chore_snapshot_http
        cls.underlying_partial_update_symbol_side_snapshot_http = underlying_partial_update_symbol_side_snapshot_http
        cls.underlying_partial_update_cancel_chore_http = underlying_partial_update_cancel_chore_http
        cls.underlying_partial_update_strat_status_http = underlying_partial_update_strat_status_http
        cls.underlying_get_open_chore_count_query_http = underlying_get_open_chore_count_query_http
        cls.underlying_partial_update_strat_brief_http = underlying_partial_update_strat_brief_http
        cls.underlying_delete_symbol_side_snapshot_http = underlying_delete_symbol_side_snapshot_http
        cls.get_symbol_side_underlying_account_cumulative_fill_qty_query_http = (
            get_symbol_side_underlying_account_cumulative_fill_qty_query_http)
        cls.underlying_read_fills_journal_http = underlying_read_fills_journal_http
        cls.underlying_read_last_barter_http = underlying_read_last_barter_http
        cls.underlying_read_strat_brief_http = underlying_read_strat_brief_http
        cls.underlying_delete_strat_brief_http = underlying_delete_strat_brief_http
        cls.underlying_create_cancel_chore_http = underlying_create_cancel_chore_http
        cls.underlying_read_market_depth_http = underlying_read_market_depth_http
        cls.underlying_read_strat_status_http = underlying_read_strat_status_http
        cls.underlying_read_strat_status_by_id_http = underlying_read_strat_status_by_id_http
        cls.underlying_read_cancel_chore_http = underlying_read_cancel_chore_http
        cls.underlying_read_strat_limits_http = underlying_read_strat_limits_http
        cls.underlying_delete_strat_status_http = underlying_delete_strat_status_http
        cls.underlying_barter_simulator_place_cxl_chore_query_http = (
            underlying_barter_simulator_place_cxl_chore_query_http)

    def __init__(self):
        super().__init__()
        pair_strat_id, is_crash_recovery = get_pair_strat_id_from_cmd_argv()
        self.pair_strat_id = pair_strat_id
        self.is_crash_recovery = is_crash_recovery
        # since this init is called before db_init
        self.db_name: str = f"street_book_{self.pair_strat_id}"
        os.environ["DB_NAME"] = self.db_name
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
        self.bartering_data_manager: BarteringDataManager | None = None
        self.simulate_config_yaml_file_path = (
                EXECUTOR_PROJECT_DATA_DIR / f"executor_{self.pair_strat_id}_simulate_config.yaml")
        self.log_simulator_file_name = f"log_simulator_{self.pair_strat_id}_logs_{self.datetime_str}.log"
        self.log_simulator_file_path = (PurePath(__file__).parent.parent / "log" /
                                        f"log_simulator_{self.pair_strat_id}_logs_{self.datetime_str}.log")
        create_logger("log_simulator", logging.DEBUG, str(PurePath(__file__).parent.parent / "log"),
                      self.log_simulator_file_name)
        self.is_test_run = is_test_run

        # to be populated in _app_launch_pre_thread_func
        self.mobile_book_container_cache: MobileBookContainerCache | None = None

        # Load the shared library
        so_module_dir = PurePath(__file__).parent
        so_module_file_name = BarteringLinkBase.pair_strat_config_dict.get("cpp_app_so_module_file_name")

        os.environ["LD_LIBRARY_PATH"] = f"{so_module_dir}:$LD_LIBRARY_PATH"
        self.mobile_book_provider = ctypes.CDLL(so_module_dir / so_module_file_name)
        self.mobile_book_provider.lock_mutex.argtypes = (ctypes.py_object,)
        self.mobile_book_provider.lock_mutex.restype = None
        self.mobile_book_provider.unlock_mutex.argtypes = (ctypes.py_object,)
        self.mobile_book_provider.unlock_mutex.restype = None
        self.mobile_book_provider.initialize_database.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.py_object
        ]
        self.mobile_book_provider.create_or_update_md_n_tob.argtypes = [
            ctypes.c_int32,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_int32,
            ctypes.c_float,
            ctypes.c_int64,
            ctypes.c_char_p,
            ctypes.c_bool,
            ctypes.c_float,
            ctypes.c_int64,
            ctypes.c_float
        ]
        self.mobile_book_provider.create_or_update_last_barter_n_tob.argtypes = [
            ctypes.c_int32,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_float,
            ctypes.c_int64,
            ctypes.c_float,
            ctypes.c_char_p,
            ctypes.c_int64,
            ctypes.c_int32
        ]
        self.mobile_book_provider.initialize_database.restype = None
        self.mobile_book_provider.create_or_update_md_n_tob.restype = None
        self.mobile_book_provider.create_or_update_last_barter_n_tob.restype = None

    def get_generic_read_route(self):
        return None

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat for now - may extend to accept symbol and send revised px according to
        underlying bartering currency
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
        key_leg_1, key_leg_2 = EmailBookServiceKeyHandler.get_key_from_pair_strat(pair_strat)
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
                        symbol_overview_for_symbol_exists and self.bartering_data_manager is not None):
                    if not self.service_ready:
                        self.service_ready = True
                        # creating required models for this strat
                        if not self._check_n_create_related_models_for_strat():
                            self.service_ready = False
                        else:
                            logging.debug("Service Marked Ready")
                else:
                    logging.warning(f"service is not up yet;;; {self.all_services_up = }, "
                                    f"{static_data_service_state.ready = }, {self.usd_fx = }, "
                                    f"{symbol_overview_for_symbol_exists = }, "
                                    f"{self.bartering_data_manager = }")
                if not self.all_services_up:
                    try:
                        if all_service_up_check(self.web_client):
                            # starting bartering_data_manager and street_book
                            try:
                                pair_strat = email_book_service_http_client.get_pair_strat_client(self.pair_strat_id)
                            except Exception as e:
                                logging.exception(f"get_pair_strat_client failed with exception: {e}")
                                continue

                            self.strat_leg_1 = pair_strat.pair_strat_params.strat_leg1
                            self.strat_leg_2 = pair_strat.pair_strat_params.strat_leg2

                            # creating config file for this server run if not exists
                            code_gen_projects_dir = PurePath(__file__).parent.parent.parent.parent
                            temp_config_file_path = (code_gen_projects_dir / "template_yaml_configs" /
                                                     "server_config.yaml")
                            dest_config_file_path = self.simulate_config_yaml_file_path
                            shutil.copy(temp_config_file_path, dest_config_file_path)

                            # setting simulate_config_file_name
                            BarteringLinkBase.simulate_config_yaml_path = self.simulate_config_yaml_file_path
                            BarteringLinkBase.executor_port = self.port
                            BarteringLinkBase.reload_executor_configs()

                            # setting partial_run to True and assigning port to pair_strat
                            if not pair_strat.is_partially_running:
                                pair_strat.is_partially_running = True
                                pair_strat.port = self.port

                                # Setting MobileBookCache instances for this symbol pair
                                md_port_dict: Dict = {}
                                mongo_server = executor_config_yaml_dict.get("mongo_server")
                                self.mobile_book_provider.initialize_database(
                                    ctypes.c_char_p(mongo_server.encode('utf-8')),
                                    ctypes.c_char_p(self.db_name.encode('utf-8')), md_port_dict)
                                pair_strat.top_of_book_port = md_port_dict.get("top_of_book_port")
                                pair_strat.market_depth_port = md_port_dict.get("market_depth_port")
                                pair_strat.last_barter_port = md_port_dict.get("last_barter_port")

                                try:
                                    updated_pair_strat = email_book_service_http_client.patch_pair_strat_client(
                                        jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                                except Exception as e:
                                    logging.exception(f"patch_pair_strat_client failed with exception: {e}")
                                    continue
                                else:

                                    leg_1_mobile_book_container = (
                                        add_container_obj_for_symbol(self.strat_leg_1.sec.sec_id))
                                    leg_2_mobile_book_container = (
                                        add_container_obj_for_symbol(self.strat_leg_2.sec.sec_id))
                                    self.mobile_book_container_cache = (
                                        MobileBookContainerCache(leg_1_mobile_book_container=leg_1_mobile_book_container,
                                                                 leg_2_mobile_book_container=leg_2_mobile_book_container))

                                    # Launching CppApp which internally creates and updates
                                    # MobileBookCache in real-time
                                    thread = threading.Thread(target=self.mobile_book_provider.cpp_app_launcher, daemon=True)
                                    thread.start()

                                    self.strat_cache: StratCache = self.get_pair_strat_loaded_strat_cache(
                                        updated_pair_strat)
                                    # Setting asyncio_loop for StreetBook
                                    StreetBook.asyncio_loop = self.asyncio_loop
                                    StreetBook.mobile_book_provider = self.mobile_book_provider
                                    # StreetBook.bartering_link.asyncio_loop = self.asyncio_loop
                                    BarteringDataManager.asyncio_loop = self.asyncio_loop
                                    self.bartering_data_manager = BarteringDataManager(StreetBook.executor_trigger,
                                                                                   self.strat_cache,
                                                                                   self.mobile_book_container_cache)
                                    logging.debug(f"Created bartering_data_manager for {pair_strat = }")
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
                                              f"in phone_book service, retrying in next periodic cycle",
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
                                    self.bartering_data_manager.handle_symbol_overview_get_all_ws(symbol_overview)

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
                            # Gets all open chores, updates residuals and raises pause to strat if req
                            run_coro = self.cxl_expired_open_chores()
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)

                            # block for task to finish
                            try:
                                future.result()
                            except Exception as e:
                                logging.exception(f"cxl_expired_open_chores failed with exception: {e}")

                        except Exception as e:
                            logging.error("periodic open chore check failed, periodic chore state checks will "
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
            # email_book_service_http_client.update_pair_strat_to_non_running_state_query_client(self.pair_strat_id)
            guaranteed_call_pair_strat_client(
                None, email_book_service_http_client.update_pair_strat_to_non_running_state_query_client,
                pair_strat_id=self.pair_strat_id)
        except Exception as e:
            if ('{"detail":"Id not Found: PairStrat ' + f'{self.pair_strat_id}' + '"}') in str(e):
                err_str_ = ("error occurred since pair_strat object got deleted, therefore can't update "
                            "is_running_state, symbol_side_key: "
                            f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
                logging.debug(err_str_)
            else:
                logging.error(f"Some error occurred while updating is_running state of "
                              f"{self.pair_strat_id = } while shutting executor server, symbol_side_key: "
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
            email_book_service_http_client.get_all_fx_symbol_overview_client()
        if fx_symbol_overviews:
            fx_symbol_overview_: FxSymbolOverviewBaseModel
            for fx_symbol_overview_ in fx_symbol_overviews:
                if fx_symbol_overview_.symbol in self.fx_symbol_overview_dict:
                    # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
                    self.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
                    self.usd_fx = fx_symbol_overview_.closing_px
                    logging.debug(f"Updated {self.usd_fx = }")
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
                        email_book_service_http_client.get_dismiss_filter_portfolio_limit_brokers_query_client(
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

                logging.debug(f"Created {strat_limits = }")

                return created_strat_limits
            else:
                if len(strat_limits_list) > 1:
                    err_str_: str = ("Unexpected: Found multiple StratLimits in single executor - ignoring "
                                     "strat_cache update for strat_limits - symbol_side_key: "
                                     f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                                     f"strat_limits_list: {strat_limits_list}")
                    logging.error(err_str_)
                else:
                    self.bartering_data_manager.handle_strat_limits_get_all_ws(strat_limits_list[0])
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

                logging.debug(f"Created {strat_status = }")
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
                    self.bartering_data_manager.handle_strat_status_get_all_ws(strat_status_list[0])
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
                int((security_float / 100) * strat_limits.max_concentration)
        return consumable_concentration

    async def _check_n_create_strat_brief_for_active_pair_strat(self, strat_limits: StratLimits):
        symbol = self.strat_leg_1.sec.sec_id
        side = self.strat_leg_1.side
        strat_brief_tuple = self.strat_cache.get_strat_brief()

        if strat_brief_tuple is not None:
            # all fine if strat_brief already exists: happens in some crash recovery
            return
        else:
            # If no strat_brief exists for this symbol
            consumable_open_chores = strat_limits.max_open_chores_per_side
            consumable_notional = strat_limits.max_single_leg_notional
            consumable_open_notional = strat_limits.max_open_single_leg_notional

        residual_qty = 0
        all_bkr_cxlled_qty = 0
        open_notional = 0
        open_qty = 0

        buy_side_bartering_brief: PairSideBarteringBrief | None = None
        sell_side_bartering_brief: PairSideBarteringBrief | None = None

        for sec, side in [(self.strat_leg_1.sec, self.strat_leg_1.side), (self.strat_leg_2.sec, self.strat_leg_2.side)]:
            symbol = sec.sec_id
            consumable_concentration = self.get_consumable_concentration_from_source(symbol, strat_limits)

            participation_period_chore_qty_sum = 0
            consumable_cxl_qty = 0
            applicable_period_second = strat_limits.market_barter_volume_participation.applicable_period_seconds
            executor_check_snapshot_list = \
                await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_get_executor_check_snapshot_query_http(symbol, side,
                                                                         applicable_period_second))
            if len(executor_check_snapshot_list) == 1:
                indicative_consumable_participation_qty = \
                    get_consumable_participation_qty(
                        executor_check_snapshot_list,
                        strat_limits.market_barter_volume_participation.max_participation_rate)
            else:
                logging.error("Received unexpected length of executor_check_snapshot_list from query "
                              f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                              f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                              f"get_executor_check_snapshot_query pre implementation")
                indicative_consumable_participation_qty = 0
            indicative_consumable_residual = strat_limits.residual_restriction.max_residual
            sec_pair_side_bartering_brief_obj = \
                PairSideBarteringBrief(security=sec,
                                     side=side,
                                     last_update_date_time=DateTime.utcnow(),
                                     consumable_open_chores=consumable_open_chores,
                                     consumable_notional=consumable_notional,
                                     consumable_open_notional=consumable_open_notional,
                                     consumable_concentration=consumable_concentration,
                                     participation_period_chore_qty_sum=participation_period_chore_qty_sum,
                                     consumable_cxl_qty=consumable_cxl_qty,
                                     indicative_consumable_participation_qty=indicative_consumable_participation_qty,
                                     residual_qty=residual_qty,
                                     indicative_consumable_residual=indicative_consumable_residual,
                                     all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                                     open_notional=open_notional, open_qty=open_qty)
            if Side.BUY == side:
                if buy_side_bartering_brief is None:
                    buy_side_bartering_brief = sec_pair_side_bartering_brief_obj
                else:
                    logging.error(f"expected buy_side_bartering_brief to be None, found: {buy_side_bartering_brief}")
            elif Side.SELL == side:
                if sell_side_bartering_brief is None:
                    sell_side_bartering_brief = sec_pair_side_bartering_brief_obj
                else:
                    logging.error(f"expected sell_side_bartering_brief to be None, found: {sell_side_bartering_brief}")

        strat_brief_obj: StratBrief = StratBrief(_id=strat_limits.id,
                                                 pair_buy_side_bartering_brief=buy_side_bartering_brief,
                                                 pair_sell_side_bartering_brief=sell_side_bartering_brief,
                                                 consumable_nett_filled_notional=strat_limits.max_net_filled_notional)
        created_strat_brief = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_strat_brief_http(
                strat_brief_obj)
        logging.debug(f"Created strat brief in post call of update strat_status to active of "
                      f"key: {get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])};;; "
                      f"{strat_limits = }, {created_strat_brief = }")

    async def _check_n_create_symbol_snapshot_for_active_pair_strat(self):
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
                                                                  chore_count=0)
                    created_symbol_side_snapshot: SymbolSideSnapshot = \
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_create_symbol_side_snapshot_http(symbol_side_snapshot_obj))
                    logging.debug(f"Created SymbolSideSnapshot with key: "
                                  f"{get_symbol_side_snapshot_log_key(created_symbol_side_snapshot)};;;"
                                  f"{created_symbol_side_snapshot = }")
                # else not required: all fine if symbol_side_snapshot already exists: happens in some crash recovery
            else:
                # Ignore symbol side snapshot creation and logging if any of security and side is None
                logging.debug(f"Received either security or side as None from config of this start_executor for "
                              f"{self.port = }, likely populated by phone_book before launching this server, "
                              f"{security = }, {side = }")

    async def _check_n_force_publish_symbol_overview_for_active_strat(self) -> None:

        symbols_list = [self.strat_leg_1.sec.sec_id, self.strat_leg_2.sec.sec_id]

        async with SymbolOverview.reentrant_lock:
            for symbol in symbols_list:
                symbol_overview_obj_tuple = self.strat_cache.get_symbol_overview_from_symbol(symbol)

                if symbol_overview_obj_tuple is not None:
                    symbol_overview_obj, _ = symbol_overview_obj_tuple
                    if not symbol_overview_obj.force_publish:
                        updated_symbol_overview = FxSymbolOverviewBaseModel(_id=symbol_overview_obj.id,
                                                                            force_publish=True)
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_partial_update_symbol_overview_http(
                                jsonable_encoder(updated_symbol_overview, by_alias=True, exclude_none=True)))
                    # else not required: happens in some crash recovery

    def _check_n_create_related_models_for_strat(self) -> bool:
        strat_limits = self._check_n_create_default_strat_limits()
        if strat_limits is not None:
            strat_status = self._check_n_create_or_update_strat_status(strat_limits)

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
                            email_book_service_http_client.patch_pair_strat_client(
                                jsonable_encoder(pair_strat, by_alias=True, exclude_none=True))
                            logging.debug(f"pair_strat's is_executor_running set to True, {pair_strat = }")
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
            self.bartering_data_manager.handle_strat_brief_get_all_ws(strat_brief)

        if self.is_crash_recovery:

            # updating chore_journals
            chore_journals: List[ChoreJournal] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_journal_http()
            for chore_journal in chore_journals:
                self.bartering_data_manager.handle_recovery_chore_journal(chore_journal)

            # updating chore_snapshots
            chore_snapshots: List[ChoreSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http()
            for chore_snapshot in chore_snapshots:
                self.bartering_data_manager.handle_chore_snapshot_get_all_ws(chore_snapshot)

            # updating symbol_side_snapshot
            symbol_side_snapshots: List[SymbolSideSnapshot] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_side_snapshot_http()
            for symbol_side_snapshot in symbol_side_snapshots:
                self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot)

            # updating cancel_chores
            cancel_chores: List[CancelChore] = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_cancel_chore_http()
            for cancel_chore in cancel_chores:
                self.bartering_data_manager.handle_recovery_cancel_chore(cancel_chore)

    async def _create_related_models_for_active_strat(self) -> None:
        # updating strat_cache
        await self.load_strat_cache()

        strat_limits_tuple = self.strat_cache.get_strat_limits()

        if strat_limits_tuple is not None:
            strat_limits, _ = strat_limits_tuple

            # creating strat_brief for both leg securities
            await self._check_n_create_strat_brief_for_active_pair_strat(strat_limits)
            # creating symbol_side_snapshot for both leg securities if not already exists
            await self._check_n_create_symbol_snapshot_for_active_pair_strat()
            # changing symbol_overview force_publish to True if exists
            await self._check_n_force_publish_symbol_overview_for_active_strat()
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
                alert_brief: str = (f"{residual_notional = } > {max_residual = } - "
                                    f"pausing this strat")
                alert_details: str = f"{updated_strat_status = }, {strat_limits = }"
                logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                 f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                pause_strat = True
            # else not required: if residual is in control then nothing to do

        if symbol_side_snapshot_.chore_count > strat_limits.cancel_rate.waived_min_chores:
            if symbol_side_snapshot_.side == Side.BUY:
                if strat_brief_.pair_buy_side_bartering_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_buy_side_bartering_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, current {consumable_cxl_qty = } " \
                                        f"for symbol {strat_brief_.pair_buy_side_bartering_brief.security.sec_id} and " \
                                        f"side {Side.BUY} - pausing this strat"
                        alert_brief: str = err_str_
                        alert_details: str = (f"{updated_strat_status = }, {strat_limits = }, "
                                              f"{symbol_side_snapshot_ = }")
                        logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                         f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; {alert_details}")
                        pause_strat = True
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single buy chore then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if buy side all_bkr_cxlled_qty is 0
            else:
                if strat_brief_.pair_sell_side_bartering_brief.all_bkr_cxlled_qty > 0:
                    if (consumable_cxl_qty := strat_brief_.pair_sell_side_bartering_brief.consumable_cxl_qty) < 0:
                        err_str_: str = f"Consumable cxl qty can't be < 0, current {consumable_cxl_qty = } " \
                                        f"for symbol {strat_brief_.pair_sell_side_bartering_brief.security.sec_id} and " \
                                        f"side {Side.SELL} - pausing this strat"
                        alert_brief: str = err_str_
                        alert_details: str = (f"{updated_strat_status = }, {strat_limits = }, "
                                              f"{symbol_side_snapshot_ = }")
                        pause_strat = True
                        logging.critical(f"{alert_brief}, symbol_side_snapshot_key: "
                                         f"{get_symbol_side_snapshot_log_key(symbol_side_snapshot_)};;; "
                                         f"{alert_details}")
                    # else not required: if consumable_cxl-qty is allowed then ignore
                # else not required: if there is not even a single sell chore then consumable_cxl-qty will
                # become 0 in that case too, so ignoring this case if sell side all_bkr_cxlled_qty is 0
            # else not required: if chore count is less than waived_min_chores
        if pause_strat:
            self.pause_strat()

    ####################################
    # Get specific Data handling Methods
    ####################################

    def _get_top_of_book_from_symbol(self, symbol: str) -> TopOfBook | None:
        if symbol == self.strat_leg_1.sec.sec_id:
            return self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book()
        elif symbol == self.strat_leg_2.sec.sec_id:
            return self.mobile_book_container_cache.leg_2_mobile_book_container.get_top_of_book()

    def _get_last_barter_px_n_symbol_tuples_from_tob(self, current_leg_tob_obj: TopOfBook,
                                                    other_leg_tob_obj: TopOfBook) -> Tuple[Tuple[float, str],
                                                                                    Tuple[float, str]]:
        with (MobileBookMutexManager(self.mobile_book_provider, current_leg_tob_obj, other_leg_tob_obj)):
            return ((current_leg_tob_obj.last_barter.px, current_leg_tob_obj.symbol),
                    (other_leg_tob_obj.last_barter.px, other_leg_tob_obj.symbol))

    def __get_residual_obj(self, side: Side, strat_brief: StratBrief) -> Residual | None:
        if side == Side.BUY:
            residual_qty = strat_brief.pair_buy_side_bartering_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_sell_side_bartering_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_bartering_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_bartering_brief.security.sec_id)
        else:
            residual_qty = strat_brief.pair_sell_side_bartering_brief.residual_qty
            other_leg_residual_qty = strat_brief.pair_buy_side_bartering_brief.residual_qty
            top_of_book_obj = \
                self._get_top_of_book_from_symbol(strat_brief.pair_sell_side_bartering_brief.security.sec_id)
            other_leg_top_of_book = \
                self._get_top_of_book_from_symbol(strat_brief.pair_buy_side_bartering_brief.security.sec_id)

        if top_of_book_obj is None or other_leg_top_of_book is None:
            logging.error(f"Received both leg's TOBs as {top_of_book_obj} and {other_leg_top_of_book}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            return None

        # since unit value is used make function
        current_leg_tob_data, other_leg_tob_data = (
            self._get_last_barter_px_n_symbol_tuples_from_tob(top_of_book_obj, other_leg_top_of_book))
        current_leg_last_barter_px, current_leg_tob_symbol = current_leg_tob_data
        other_leg_last_barter_px, other_leg_tob_symbol = other_leg_tob_data
        residual_notional = abs((residual_qty * self.get_usd_px(current_leg_last_barter_px,
                                                                current_leg_tob_symbol)) -
                                (other_leg_residual_qty * self.get_usd_px(other_leg_last_barter_px,
                                                                          other_leg_tob_symbol)))
        if side == Side.BUY:
            if (residual_qty * self.get_usd_px(top_of_book_obj.last_barter.px,
                                               top_of_book_obj.symbol)) > \
                    (other_leg_residual_qty * self.get_usd_px(other_leg_top_of_book.last_barter.px,
                                                              other_leg_top_of_book.symbol)):
                residual_security = strat_brief.pair_buy_side_bartering_brief.security
            else:
                residual_security = strat_brief.pair_sell_side_bartering_brief.security
        else:
            if (residual_qty * top_of_book_obj.last_barter.px) > \
                    (other_leg_residual_qty * other_leg_top_of_book.last_barter.px):
                residual_security = strat_brief.pair_sell_side_bartering_brief.security
            else:
                residual_security = strat_brief.pair_buy_side_bartering_brief.security

        if residual_notional > 0:
            updated_residual = Residual(security=residual_security, residual_notional=residual_notional)
            return updated_residual
        else:
            updated_residual = Residual(security=residual_security, residual_notional=0)
            return updated_residual

    async def get_last_n_sec_chore_qty(self, symbol: str, side: Side, last_n_sec: int) -> int | None:
        last_n_sec_chore_qty: int | None = None
        if last_n_sec == 0:
            symbol_side_snapshots_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(symbol)
            if symbol_side_snapshots_tuple is not None:
                symbol_side_snapshot, _ = symbol_side_snapshots_tuple
                last_n_sec_chore_qty = symbol_side_snapshot.total_qty
            else:
                err_str_ = f"Received symbol_side_snapshots_tuple as None from strat_cache, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.exception(err_str_)
        else:
            agg_objs = \
                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http(
                    get_chore_total_sum_of_last_n_sec(symbol, last_n_sec), self.get_generic_read_route())

            if len(agg_objs) > 0:
                last_n_sec_chore_qty = agg_objs[-1].last_n_sec_total_qty
            else:
                last_n_sec_chore_qty = 0
                err_str_ = "received empty list of aggregated objects from aggregation on ChoreSnapshot to " \
                           f"get {last_n_sec = } total chore sum, symbol_side_key: " \
                           f"{get_symbol_side_key([(symbol, side)])}"
                logging.debug(err_str_)
        logging.debug(f"Received {last_n_sec_chore_qty = }, {last_n_sec = }, {symbol = }, {Side = }")
        return last_n_sec_chore_qty

    async def get_last_n_sec_barter_qty(self, symbol: str, side: Side) -> int | None:
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        last_n_sec_barter_qty: int | None = None
        if strat_limits_tuple is not None:
            strat_limits, _ = strat_limits_tuple

            if strat_limits is not None:
                applicable_period_seconds = strat_limits.market_barter_volume_participation.applicable_period_seconds
                last_n_sec_market_barter_vol_obj_list = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_get_last_n_sec_total_barter_qty_query_http(symbol, applicable_period_seconds))
                if last_n_sec_market_barter_vol_obj_list:
                    last_n_sec_barter_qty = last_n_sec_market_barter_vol_obj_list[0].last_n_sec_barter_vol
                    logging.debug(
                        f"Received {last_n_sec_barter_qty = }, {applicable_period_seconds = }, {symbol = }, {Side = }")
                else:
                    logging.error(f"could not receive any last_n_sec_market_barter_vol_obj to get last_n_sec_barter_qty "
                                  f"for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, likely bug in "
                                  f"get_last_n_sec_total_barter_qty_query pre impl")
        else:
            err_str_ = (
                "Can't find any strat_limits in cache to get last_n_sec barter qty, "
                "ignoring model creations, symbol_side_key: "
                f"{get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])}")
            logging.error(err_str_)
        return last_n_sec_barter_qty

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
    # Chore Journal Update Methods
    ##############################

    async def create_chore_journal_pre(self, chore_journal_obj: ChoreJournal) -> None:
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = f"create_chore_journal_pre not ready - service is not initialized yet, " \
                       f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # updating chore notional in chore journal obj

        if chore_journal_obj.chore_event == ChoreEventType.OE_NEW and chore_journal_obj.chore.px == 0:
            top_of_book_obj = self._get_top_of_book_from_symbol(chore_journal_obj.chore.security.sec_id)
            if top_of_book_obj is not None:
                with MobileBookMutexManager(self.mobile_book_provider, top_of_book_obj):
                    chore_journal_obj.chore.px = top_of_book_obj.last_barter.px
            else:
                err_str_ = f"received chore journal px 0 and to update px, received {top_of_book_obj = }, " \
                           f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}"
                logging.error(err_str_)
                raise HTTPException(status_code=500, detail=err_str_)
        # If chore_journal is not new then we don't care about px, we care about event_type and if chore is new
        # and px is not 0 then using provided px

        if chore_journal_obj.chore.px is not None and chore_journal_obj.chore.qty is not None:
            chore_journal_obj.chore.chore_notional = \
                self.get_usd_px(chore_journal_obj.chore.px,
                                chore_journal_obj.chore.security.sec_id) * chore_journal_obj.chore.qty
        else:
            chore_journal_obj.chore.chore_notional = 0

    async def create_chore_journal_post(self, chore_journal_obj: ChoreJournal):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_chore_journal_get_all_ws(chore_journal_obj)

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock:
            res = await self._update_chore_snapshot_from_chore_journal(chore_journal_obj)

            if res is not None:
                strat_id, chore_snapshot, strat_brief, portfolio_status_updates = res

                # Updating and checking portfolio_limits in portfolio_manager
                post_book_service_http_client.check_portfolio_limits_query_client(
                    strat_id, chore_journal_obj, chore_snapshot, strat_brief, portfolio_status_updates)

            # else not required: if result returned from _update_chore_snapshot_from_chore_journal is None, that
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding portfolio_limit checks too

    async def create_chore_snapshot_pre(self, chore_snapshot_obj: ChoreSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if chore_snapshot_obj.chore_brief.security.sec_type is None:
            chore_snapshot_obj.chore_brief.security.sec_type = SecurityType.TICKER

    async def create_symbol_side_snapshot_pre(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating security's sec_type to default value if sec_type is None
        if symbol_side_snapshot_obj.security.sec_type is None:
            symbol_side_snapshot_obj.security.sec_type = SecurityType.TICKER

    @staticmethod
    def is_cxled_event(event: ChoreEventType) -> bool:
        if event in [ChoreEventType.OE_CXL_ACK, ChoreEventType.OE_UNSOL_CXL]:
            return True
        return False

    async def _update_chore_snapshot_from_chore_journal(
            self, chore_journal_obj: ChoreJournal) -> Tuple[int, ChoreSnapshot, StratBrief | None,
                                                            PortfolioStatusUpdatesContainer | None] | None:
        pair_strat = self.strat_cache.get_pair_strat_obj()

        if not is_ongoing_strat(pair_strat):
            # avoiding any update if strat is non-ongoing
            return None

        match chore_journal_obj.chore_event:
            case ChoreEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance called more than once in one session'

                chore_snapshot = ChoreSnapshot(_id=ChoreSnapshot.next_id(),
                                               chore_brief=chore_journal_obj.chore,
                                               filled_qty=0, avg_fill_px=0,
                                               fill_notional=0,
                                               cxled_qty=0,
                                               avg_cxled_px=0,
                                               cxled_notional=0,
                                               last_update_fill_qty=0,
                                               last_update_fill_px=0,
                                               total_amend_dn_qty=0,
                                               total_amend_up_qty=0,
                                               create_date_time=chore_journal_obj.chore_event_date_time,
                                               last_update_date_time=chore_journal_obj.chore_event_date_time,
                                               chore_status=ChoreStatusType.OE_UNACK)
                chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                        underlying_create_chore_snapshot_http(chore_snapshot))
                symbol_side_snapshot = \
                    await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                                      chore_snapshot)
                if symbol_side_snapshot is not None:
                    updated_strat_brief = await self._update_strat_brief_from_chore_or_fill(chore_journal_obj,
                                                                                            chore_snapshot,
                                                                                            symbol_side_snapshot)
                    if updated_strat_brief is not None:
                        await self._update_strat_status_from_chore_journal(chore_journal_obj, chore_snapshot,
                                                                           symbol_side_snapshot, updated_strat_brief)
                    # else not required: if updated_strat_brief is None then it means some error occurred in
                    # _update_strat_brief_from_chore which would have got added to alert already
                    portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                        await self._update_portfolio_status_from_chore_journal(
                            chore_journal_obj, chore_snapshot))

                    return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates
                # else not require_create_update_symbol_side_snapshot_from_chore_journald: if symbol_side_snapshot
                # is None then it means some error occurred in _create_update_symbol_side_snapshot_from_chore_journal
                # which would have got added to alert already

            case ChoreEventType.OE_ACK:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(chore_journal_obj,
                                                                           [ChoreStatusType.OE_UNACK])
                    if chore_snapshot is not None:
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.last_chore_status = chore_snapshot.chore_status
                        chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                        updated_chore_snapshot = (
                            await StreetBookServiceRoutesCallbackBaseNativeOverride.
                            underlying_update_chore_snapshot_http(chore_snapshot))

                        return pair_strat.id, updated_chore_snapshot, None, None

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already
            case ChoreEventType.OE_CXL:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = await self._check_state_and_get_chore_snapshot_obj(
                        chore_journal_obj, [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED,
                                                            ChoreStatusType.OE_AMD])
                    if chore_snapshot is not None:
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.last_chore_status = chore_snapshot.chore_status
                        chore_snapshot.chore_status = ChoreStatusType.OE_CXL_UNACK
                        updated_chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                        underlying_update_chore_snapshot_http(chore_snapshot))

                        return pair_strat.id, updated_chore_snapshot, None, None

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already
            case ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_ACKED,
                                                ChoreStatusType.OE_UNACK, ChoreStatusType.OE_FILLED,
                                                ChoreStatusType.OE_AMD])
                    if chore_snapshot is not None:
                        # When CXL_ACK arrived after chore got fully filled, since nothing is left to cxl - ignoring
                        # this chore_journal's chore_snapshot update
                        if chore_snapshot.chore_status == ChoreStatusType.OE_FILLED:
                            logging.info("Received chore_journal with event CXL_ACK after ChoreSnapshot is fully "
                                         f"filled - ignoring this CXL_ACK, chore_journal_key: "
                                         f"{get_chore_journal_log_key(chore_journal_obj)};;; "
                                         f"{chore_journal_obj=}, {chore_snapshot=}")
                        else:
                            # If chore_event is OE_UNSOL_CXL, that is treated as unsolicited cxl
                            # If CXL_ACK comes after OE_CXL_UNACK, that means cxl_ack came after cxl request
                            # chore_brief = ChoreBriefOptional(**chore_snapshot.chore_brief.model_dump())
                            chore_brief = chore_snapshot.chore_brief
                            if chore_journal_obj.chore.text:
                                if chore_brief.text:
                                    chore_brief.text.extend(chore_journal_obj.chore.text)
                                else:
                                    chore_brief.text = chore_journal_obj.chore.text
                            # else not required: If no text is present in chore_journal then updating
                            # chore snapshot with same obj

                            cxled_qty = int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                            chore_snapshot.total_amend_dn_qty)
                            cxled_notional = cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                         chore_snapshot.chore_brief.security.sec_id)
                            chore_snapshot.cxled_qty += cxled_qty
                            chore_snapshot.cxled_notional += cxled_notional
                            chore_snapshot.avg_cxled_px = \
                                (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                               chore_snapshot.chore_brief.security.sec_id) /
                                 chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0

                            chore_snapshot.chore_brief = chore_brief
                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_chore_status = chore_snapshot.chore_status
                            chore_snapshot.chore_status = ChoreStatusType.OE_DOD
                            chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                underlying_update_chore_snapshot_http(chore_snapshot))

                        if chore_snapshot.chore_status != ChoreStatusType.OE_FILLED:
                            symbol_side_snapshot = await self._create_update_symbol_side_snapshot_from_chore_journal(
                                chore_journal_obj, chore_snapshot)
                            if symbol_side_snapshot is not None:
                                updated_strat_brief = (
                                    await self._update_strat_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                                      symbol_side_snapshot))
                                if updated_strat_brief is not None:
                                    await self._update_strat_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_strat_brief)
                                # else not required: if updated_strat_brief is None then it means some error occurred in
                                # _update_strat_brief_from_chore which would have got added to alert already
                                portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                                    await self._update_portfolio_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot))

                                return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates

                            # else not required: if symbol_side_snapshot is None then it means some error occurred in
                            # _create_update_symbol_side_snapshot_from_chore_journal which would have got added to
                            # alert already

                        # else not required: If CXL_ACK arrived after chore is fully filled then since we ignore
                        # any update for this chore journal object, returns None to not update post barter engine too

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_CXL_INT_REJ | ChoreEventType.OE_CXL_BRK_REJ | ChoreEventType.OE_CXL_EXH_REJ:
                # reverting the state of chore_snapshot after receiving cxl reject

                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = await self._check_state_and_get_chore_snapshot_obj(
                        chore_journal_obj, [ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_FILLED])
                    if chore_snapshot is not None:
                        if chore_snapshot.chore_brief.qty > chore_snapshot.filled_qty:
                            last_3_chore_journals_from_chore_id = \
                                await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                       underlying_read_chore_journal_http(
                                        get_last_n_chore_journals_from_chore_id(
                                            chore_journal_obj.chore.chore_id, 3),
                                        self.get_generic_read_route()))
                            if last_3_chore_journals_from_chore_id:
                                if (last_3_chore_journals_from_chore_id[0].chore_event in
                                        [ChoreEventType.OE_CXL_INT_REJ,
                                         ChoreEventType.OE_CXL_BRK_REJ,
                                         ChoreEventType.OE_CXL_EXH_REJ]):
                                    if last_3_chore_journals_from_chore_id[-1].chore_event == ChoreEventType.OE_NEW:
                                        chore_status = ChoreStatusType.OE_UNACK
                                    elif last_3_chore_journals_from_chore_id[-1].chore_event == ChoreEventType.OE_ACK:
                                        chore_status = ChoreStatusType.OE_ACKED
                                    else:
                                        err_str_ = ("3rd chore journal from chore_journal of status OE_CXL_INT_REJ "
                                                    "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, must be"
                                                    "of status OE_ACK or OE_UNACK, received "
                                                    f"{last_3_chore_journals_from_chore_id = }, "
                                                    f"chore_journal_key: "
                                                    f"{get_chore_journal_log_key(chore_journal_obj)}")
                                        logging.error(err_str_)
                                        return None
                                else:
                                    err_str_ = ("Recent chore journal must be of status OE_CXL_INT_REJ "
                                                "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, received last 3 "
                                                "chore_journals {last_3_chore_journals_from_chore_id}, "
                                                f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}")
                                    logging.error(err_str_)
                                    return None
                            else:
                                err_str_ = f"Received empty list while fetching last 3 chore_journals for " \
                                           f"{chore_journal_obj.chore.chore_id = }, " \
                                           f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return None
                        elif chore_snapshot.chore_brief.qty < chore_snapshot.filled_qty:
                            chore_status = ChoreStatusType.OE_OVER_FILLED
                        else:
                            chore_status = ChoreStatusType.OE_FILLED

                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.last_chore_status = chore_snapshot.chore_status
                        chore_snapshot.chore_status = chore_status
                        updated_chore_snapshot = \
                            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                   underlying_update_chore_snapshot_http(chore_snapshot))

                        return pair_strat.id, updated_chore_snapshot, None, None
                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_INT_REJ | ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED])
                    if chore_snapshot is not None:
                        chore_brief = chore_snapshot.chore_brief
                        if chore_brief.text:
                            chore_brief.text.extend(chore_journal_obj.chore.text)
                        else:
                            chore_brief.text = chore_journal_obj.chore.text
                        cxled_qty = int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty)
                        cxled_notional = \
                            chore_snapshot.cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                       chore_snapshot.chore_brief.security.sec_id)
                        avg_cxled_px = \
                            (self.get_local_px_or_notional(cxled_notional, chore_snapshot.chore_brief.security.sec_id) /
                             cxled_qty) if cxled_qty != 0 else 0

                        chore_snapshot.chore_brief = chore_brief
                        chore_snapshot.cxled_qty = cxled_qty
                        chore_snapshot.cxled_notional = cxled_notional
                        chore_snapshot.avg_cxled_px = avg_cxled_px
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.last_chore_status = chore_snapshot.chore_status
                        chore_snapshot.chore_status = ChoreStatusType.OE_DOD
                        chore_snapshot = \
                            await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                   underlying_update_chore_snapshot_http(chore_snapshot))
                        symbol_side_snapshot = \
                            await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                                              chore_snapshot)
                        if symbol_side_snapshot is not None:
                            updated_strat_brief = (
                                await self._update_strat_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                                  symbol_side_snapshot))
                            if updated_strat_brief is not None:
                                await self._update_strat_status_from_chore_journal(
                                    chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_strat_brief)
                            # else not required: if updated_strat_brief is None then it means some error occurred in
                            # _update_strat_brief_from_chore which would have got added to alert already
                            portfolio_status_updates: PortfolioStatusUpdatesContainer = (
                                await self._update_portfolio_status_from_chore_journal(
                                    chore_journal_obj, chore_snapshot))

                            return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates
                        # else not require_create_update_symbol_side_snapshot_from_chore_journald:
                        # if symbol_side_snapshot is None then it means some error occurred in
                        # _create_update_symbol_side_snapshot_from_chore_journal which would have
                        # got added to alert already
                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already
            case ChoreEventType.OE_AMD_UNACK:

                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_ACKED])

                    if chore_snapshot is not None:
                        # checking if case is for qty amend down then amend qty must be greater than filled qty
                        if chore_snapshot.filled_qty is not None and chore_journal_obj.chore.qty is not None:
                            if chore_snapshot.filled_qty > chore_journal_obj.chore.qty:
                                logging.error("Unsupported: Amend qty is less than already filled qty - ignoring is "
                                              f"amend request, amend_qty: {chore_journal_obj.chore.qty}, "
                                              f"filled_qty: {chore_snapshot.filled_qty};;; "
                                              f"amend_unack chore_journal: {chore_journal_obj}, "
                                              f"chore_snapshot {chore_snapshot}")
                                return

                        # qty which is available to be used after amend downs
                        leaves_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty

                        # blocking same qty/px amends
                        if (leaves_qty == chore_journal_obj.chore.qty or
                                chore_snapshot.chore_brief.px == chore_journal_obj.chore.px):
                            err_str_ = (f"Found amend request for chore_id: {chore_snapshot.chore_brief.chore_id}, "
                                        f"with amend request for qty or px, same as existing qty or px - avoiding "
                                        f"amend request;;; requested amend {chore_journal_obj = }, {chore_snapshot = }")
                            logging.error(err_str_)
                            return

                        # we apply amend changes to chore if chore is risky
                        # For BUY: chore is risky if chore qty pr px is increased to higher value else it is non-risky
                        # For SELL: chore is risky if chore qty pr px is decreased to lower value else it is non-risky
                        if self.is_amend_risky(chore_journal_obj, chore_snapshot, leaves_qty):
                            last_original_px = chore_snapshot.chore_brief.px
                            last_original_qty = chore_snapshot.chore_brief.qty

                            # if amend px is requested
                            if chore_journal_obj.chore.px:
                                # applying px amend changes
                                chore_snapshot.chore_brief.px = chore_journal_obj.chore.px

                            # if amend qty is requested
                            if chore_journal_obj.chore.qty:
                                if chore_journal_obj.chore.qty < leaves_qty:
                                    # AMD: when qty is amended down then, qty that is amended dn gets
                                    # cxled - chore qty stays same and leaves qty is reduced for this chore
                                    removed_qty = leaves_qty - chore_journal_obj.chore.qty
                                    chore_snapshot.total_amend_dn_qty += removed_qty

                                    if chore_journal_obj.chore.px:
                                        # AMD: if px got amended then chore px is changed to amended value so
                                        # using last px, with which chore get cxled
                                        removed_notional = (removed_qty *
                                                            self.get_usd_px(last_original_px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                    else:
                                        removed_notional = (removed_qty *
                                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                    chore_snapshot.cxled_qty += removed_qty
                                    chore_snapshot.cxled_notional += removed_notional
                                    chore_snapshot.avg_cxled_px = (
                                        (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                       chore_snapshot.chore_brief.security.sec_id) /
                                         chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)
                                else:
                                    # AMD: when qty is amended up then, chore qty is updated to amended qty
                                    chore_snapshot.chore_brief.qty = chore_journal_obj.chore.qty
                                    chore_snapshot.total_amend_up_qty += chore_journal_obj.chore.qty - leaves_qty

                            chore_snapshot.chore_brief.chore_notional = (
                                    chore_snapshot.chore_brief.qty *
                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id))
                            last_chore_status = chore_snapshot.chore_status

                            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj.chore_event,
                                                                                    chore_snapshot, last_chore_status)
                            self.log_warning_based_on_amended_chore_status(chore_journal_obj.chore_event,
                                                                           chore_status, last_chore_status,
                                                                           chore_snapshot, chore_journal_obj,
                                                                           leaves_qty)
                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_amend_px = chore_journal_obj.chore.px
                            chore_snapshot.last_amend_qty = chore_journal_obj.chore.qty
                            chore_snapshot.last_leaves_qty = leaves_qty
                            chore_snapshot.last_original_qty = last_original_qty
                            chore_snapshot.last_original_px = last_original_px
                            chore_snapshot.last_chore_status = last_chore_status
                            chore_snapshot.chore_status = chore_status
                            chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                    underlying_update_chore_snapshot_http(chore_snapshot))
                            symbol_side_snapshot = \
                                await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                                                  chore_snapshot)
                            if symbol_side_snapshot is not None:
                                updated_strat_brief = (
                                    await self._update_strat_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                                      symbol_side_snapshot))
                                if updated_strat_brief is not None:
                                    await self._update_strat_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_strat_brief)
                                # else not required: if updated_strat_brief is None then it means some error occurred in
                                # _update_strat_brief_from_chore which would have got added to alert already
                                portfolio_status_updates: PortfolioStatusUpdatesContainer = (
                                    await self._update_portfolio_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot))
                                return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates
                            # else not require_create_update_symbol_side_snapshot_from_chore_journald:
                            # if symbol_side_snapshot is None then it means some error occurred in
                            # _create_update_symbol_side_snapshot_from_chore_journal which would have
                            # got added to alert already
                        else:
                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_amend_px = chore_journal_obj.chore.px
                            chore_snapshot.last_amend_qty = chore_journal_obj.chore.qty
                            chore_snapshot.last_chore_status = chore_snapshot.chore_status
                            chore_snapshot.chore_status = ChoreStatusType.OE_AMD
                            updated_chore_snapshot = (
                                await StreetBookServiceRoutesCallbackBaseNativeOverride.
                                underlying_update_chore_snapshot_http(chore_snapshot))
                            return pair_strat.id, updated_chore_snapshot, None, None
                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already
            case ChoreEventType.OE_AMD_ACK:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot: ChoreSnapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_AMD, ChoreStatusType.OE_FILLED,
                                                                ChoreStatusType.OE_OVER_FILLED,
                                                                ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_DOD])

                    if chore_snapshot is not None:
                        leaves_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty

                        # if not amended already that means it is non-risky amend - applying amend changes in AMD_ACK
                        if not self.is_already_amended(chore_snapshot):
                            last_original_px = chore_snapshot.chore_brief.px
                            last_original_qty = chore_snapshot.chore_brief.qty
                            if chore_snapshot.last_amend_px:
                                chore_snapshot.chore_brief.px = chore_snapshot.last_amend_px

                            if chore_snapshot.last_amend_qty:
                                if chore_snapshot.last_amend_qty < leaves_qty:
                                    chore_snapshot.total_amend_dn_qty += (
                                            leaves_qty - chore_snapshot.last_amend_qty)
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        removed_qty = leaves_qty - chore_snapshot.last_amend_qty
                                        if chore_snapshot.last_amend_px:
                                            # if px got amended then chore px is changes to amended value so using last
                                            # px, with which chore get cxled
                                            removed_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            removed_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        chore_snapshot.cxled_qty += removed_qty
                                        chore_snapshot.cxled_notional += removed_notional
                                        chore_snapshot.avg_cxled_px = (
                                            (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                           chore_snapshot.chore_brief.security.sec_id) /
                                             chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)
                                    else:
                                        logging.warning("Amending dn qty on chore which is already DOD - requested "
                                                        "qty will be shifted to amended dn qty from residual cxled_qty "
                                                        f";;; {chore_journal_obj = }, {chore_snapshot = }")

                                        removed_qty = leaves_qty - chore_snapshot.last_amend_qty
                                        if chore_snapshot.last_amend_px:
                                            # if px got amended then chore px is changed to amended value so removing
                                            # cxl_notional with ol px and updating new notional with amended px
                                            removed_old_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            removed_new_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))

                                            chore_snapshot.cxled_notional -= (
                                                                      removed_old_notional - removed_new_notional)
                                            chore_snapshot.avg_cxled_px = (
                                                (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                               chore_snapshot.chore_brief.security.sec_id) /
                                                 chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)
                                        # else not required: if chore is in DOD state and px is not amended in this
                                        # amend then amend dn notional is already in cxled notional
                                else:
                                    # AMD: when qty is amended up then, chore qty is updated to amended qty
                                    chore_snapshot.chore_brief.qty = chore_snapshot.last_amend_qty
                                    chore_snapshot.total_amend_up_qty += (
                                            chore_snapshot.last_amend_qty - leaves_qty)
                                    if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                        # AMD: if chore status is DOD that means amend is post DOD - adding amended up
                                        # qty to cxled_qty
                                        additional_qty = chore_snapshot.last_amend_qty - leaves_qty
                                        if chore_snapshot.last_amend_px:
                                            additional_new_notional = (
                                                    additional_qty *
                                                    self.get_usd_px(chore_snapshot.last_amend_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            additional_new_notional = (
                                                    additional_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        chore_snapshot.cxled_qty += additional_qty
                                        chore_snapshot.cxled_notional += additional_new_notional
                                        chore_snapshot.avg_cxled_px = (
                                            (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                           chore_snapshot.chore_brief.security.sec_id) /
                                             chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                            chore_snapshot.chore_brief.chore_notional = (
                                    chore_snapshot.chore_brief.qty *
                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id))
                            last_chore_status = chore_snapshot.chore_status

                            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj.chore_event,
                                                                                    chore_snapshot, last_chore_status)
                            self.log_warning_based_on_amended_chore_status(chore_journal_obj.chore_event,
                                                                           chore_status, last_chore_status,
                                                                           chore_snapshot, chore_journal_obj,
                                                                           leaves_qty)

                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_leaves_qty = leaves_qty
                            chore_snapshot.last_original_qty = last_original_qty
                            chore_snapshot.last_original_px = last_original_px
                            chore_snapshot.last_chore_status = last_chore_status
                            chore_snapshot.chore_status = chore_status
                            chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                    underlying_update_chore_snapshot_http(chore_snapshot))
                            symbol_side_snapshot = \
                                await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                                                  chore_snapshot)
                            if symbol_side_snapshot is not None:
                                updated_strat_brief = (
                                    await self._update_strat_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                                      symbol_side_snapshot))
                                if updated_strat_brief is not None:
                                    await self._update_strat_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_strat_brief)
                                # else not required: if updated_strat_brief is None then it means some error occurred in
                                # _update_strat_brief_from_chore which would have got added to alert already
                                portfolio_status_updates: PortfolioStatusUpdatesContainer = (
                                    await self._update_portfolio_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot))
                                return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates
                            # else not require_create_update_symbol_side_snapshot_from_chore_journald:
                            # if symbol_side_snapshot is None then it means some error occurred in
                            # _create_update_symbol_side_snapshot_from_chore_journal which would have
                            # got added to alert already
                        else:
                            last_chore_status = chore_snapshot.chore_status
                            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj.chore_event,
                                                                                    chore_snapshot, last_chore_status)

                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_chore_status = chore_snapshot.chore_status
                            chore_snapshot.chore_status = chore_status
                            updated_chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                            underlying_update_chore_snapshot_http(chore_snapshot))
                            return pair_strat.id, updated_chore_snapshot, None, None
                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already
            case ChoreEventType.OE_AMD_REJ:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot: ChoreSnapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_AMD, ChoreStatusType.OE_FILLED,
                                                ChoreStatusType.OE_OVER_FILLED,
                                                ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_DOD])
                    if chore_snapshot is not None:
                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                            logging.error(f"Received AMD_REJ post chore DOD on chore_id: "
                                          f"{chore_snapshot.chore_brief.chore_id} - ignoring this chore_journal and "
                                          f"chore will stay unchanged;;; amd_rej {chore_journal_obj = }, "
                                          f"{chore_snapshot = }")
                            return

                        leaves_qty = chore_snapshot.last_leaves_qty

                        if self.is_already_amended(chore_snapshot):
                            last_original_px = chore_snapshot.last_original_px
                            last_original_qty = chore_snapshot.last_original_qty
                            if chore_snapshot.last_amend_px:
                                # putting back last_original_px which got changed in risky AMD_UNACK
                                chore_snapshot.chore_brief.px = chore_snapshot.last_original_px

                            if chore_snapshot.last_amend_qty:
                                if chore_snapshot.last_amend_qty < leaves_qty:
                                    # reducing back amended_dn_qty which got increased in risky AMD_UNACK
                                    chore_snapshot.total_amend_dn_qty -= (
                                            leaves_qty - chore_snapshot.last_amend_qty)
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        removed_qty = leaves_qty - chore_snapshot.last_amend_qty
                                        if chore_snapshot.last_amend_px:
                                            # if px got amended then chore px is changes to amended value so using last
                                            # px, with which chore get cxled
                                            removed_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            removed_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))

                                        # reducing back amended_dn_qty which got added up in cxled_qty risky AMD_UNACK
                                        # also making corresponding cxled_notional and avg_cxled_px changes
                                        chore_snapshot.cxled_qty -= removed_qty
                                        chore_snapshot.cxled_notional -= removed_notional
                                        chore_snapshot.avg_cxled_px = (
                                            (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                           chore_snapshot.chore_brief.security.sec_id) /
                                             chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)
                                    else:
                                        logging.warning("Amending dn qty on chore which is already DOD - requested "
                                                        "qty will be shifted to amended dn qty from residual cxled_qty "
                                                        f";;; {chore_journal_obj = }, {chore_snapshot = }")

                                        removed_qty = leaves_qty - chore_snapshot.last_amend_qty
                                        if chore_snapshot.last_amend_px:
                                            # if px got amended then chore px is changed to amended value - removing
                                            # cxl_notional with amended px and putting notional with last original px
                                            removed_old_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            removed_new_notional = (
                                                    removed_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            chore_snapshot.cxled_notional += (
                                                    removed_old_notional - removed_new_notional)
                                            chore_snapshot.avg_cxled_px = (
                                                (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                               chore_snapshot.chore_brief.security.sec_id) /
                                                 chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)
                                        # else not required: if chore is in DOD state and px is not amended in this
                                        # amend then amend dn notional is already in cxled notional so no change
                                        # was made while amending
                                else:
                                    # AMD: when qty is amended up then, chore qty is updated to
                                    #      amended qty - reverting qty
                                    chore_snapshot.chore_brief.qty = chore_snapshot.last_original_qty
                                    chore_snapshot.total_amend_up_qty -= (
                                            chore_snapshot.last_amend_qty - last_original_qty)
                                    if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                        # AMD: if chore status is DOD that means amend is post DOD - adding amended up
                                        # qty to cxled_qty
                                        additional_qty = chore_snapshot.last_amend_qty - leaves_qty
                                        if chore_snapshot.last_amend_px:
                                            additional_new_notional = (
                                                    additional_qty *
                                                    self.get_usd_px(chore_snapshot.last_amend_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            additional_new_notional = (
                                                    additional_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        chore_snapshot.cxled_qty -= additional_qty
                                        chore_snapshot.cxled_notional -= additional_new_notional
                                        chore_snapshot.avg_cxled_px = (
                                            (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                           chore_snapshot.chore_brief.security.sec_id) /
                                             chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                            chore_snapshot.chore_brief.chore_notional = (
                                    chore_snapshot.chore_brief.qty *
                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                    chore_snapshot.chore_brief.security.sec_id))
                            last_chore_status = chore_snapshot.chore_status

                            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj.chore_event,
                                                                                    chore_snapshot, last_chore_status)
                            self.log_warning_amend_rej_reverted_chore_status(chore_status, last_chore_status,
                                                                             chore_snapshot, chore_journal_obj,
                                                                             leaves_qty)

                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_chore_status = last_chore_status
                            chore_snapshot.chore_status = chore_status
                            chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                    underlying_update_chore_snapshot_http(chore_snapshot))

                            symbol_side_snapshot = \
                                await self._create_update_symbol_side_snapshot_from_chore_journal(chore_journal_obj,
                                                                                                  chore_snapshot)
                            if symbol_side_snapshot is not None:
                                updated_strat_brief = (
                                    await self._update_strat_brief_from_chore_or_fill(chore_journal_obj, chore_snapshot,
                                                                                      symbol_side_snapshot))
                                if updated_strat_brief is not None:
                                    await self._update_strat_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot, symbol_side_snapshot, updated_strat_brief)
                                # else not required: if updated_strat_brief is None then it means some error occurred in
                                # _update_strat_brief_from_chore which would have got added to alert already
                                portfolio_status_updates: PortfolioStatusUpdatesContainer = (
                                    await self._update_portfolio_status_from_chore_journal(
                                        chore_journal_obj, chore_snapshot))
                                return pair_strat.id, chore_snapshot, updated_strat_brief, portfolio_status_updates
                            # else not require_create_update_symbol_side_snapshot_from_chore_journald:
                            # if symbol_side_snapshot is None then it means some error occurred in
                            # _create_update_symbol_side_snapshot_from_chore_journal which would have
                            # got added to alert already
                        else:
                            last_chore_status = chore_snapshot.chore_status
                            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj.chore_event,
                                                                                    chore_snapshot, last_chore_status)

                            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                            chore_snapshot.last_chore_status = last_chore_status
                            chore_snapshot.chore_status = chore_status
                            updated_chore_snapshot = await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                                                            underlying_update_chore_snapshot_http(chore_snapshot))
                            return pair_strat.id, updated_chore_snapshot, None, None
                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already
            case other_:
                err_str_ = f"Unsupported Chore event - {other_} in chore_journal_key: " \
                           f"{get_chore_journal_log_key(chore_journal_obj)}, {chore_journal_obj = }"
                logging.error(err_str_)

    def is_amend_risky(self, chore_journal_obj, chore_snapshot, leaves_qty):
        if chore_journal_obj.chore.side == Side.BUY:
            if chore_journal_obj.chore.px and chore_journal_obj.chore.px > chore_snapshot.chore_brief.px:
                return True
            elif chore_journal_obj.chore.qty and chore_journal_obj.chore.qty > leaves_qty:
                return True
            else:
                return False
        else:
            if chore_journal_obj.chore.px and chore_journal_obj.chore.px < chore_snapshot.chore_brief.px:
                return True
            elif chore_journal_obj.chore.qty and chore_journal_obj.chore.qty < leaves_qty:
                return True
            else:
                return False

    def is_already_amended(self, chore_snapshot: ChoreSnapshot):
        if chore_snapshot.chore_brief.side == Side.BUY:
            if chore_snapshot.last_amend_px and chore_snapshot.last_amend_px == chore_snapshot.chore_brief.px:
                return True
            elif chore_snapshot.last_amend_qty and chore_snapshot.last_amend_qty == chore_snapshot.chore_brief.qty:
                # amend_up is risky in buy so last_amend_qty has been applied to chore_snapshot chore qty
                # if last_amend_qty != chore qty that means it was amend_dn which is non-risky in buy so needs to be
                # handled now
                return True
            else:
                return False
        else:
            if chore_snapshot.last_amend_px and chore_snapshot.last_amend_px == chore_snapshot.chore_brief.px:
                return True
            elif chore_snapshot.last_amend_qty and chore_snapshot.last_amend_qty < chore_snapshot.chore_brief.qty:
                # in sell both risky and no-risky will have last_amend_qty != chore qty since chore doesn't get
                # affected with amend_dn which is risky in sell, but if
                # last_amend_qty > chore qty which is amend_up then it is non-risky and needs to be handled at AMD_ACK
                # hence when last_amend_qty < chore qty, then amend is already applied
                return True
            else:
                return False

    @staticmethod
    def get_chore_status_post_amend_applied(
            chore_event: ChoreEventType, chore_snapshot: ChoreSnapshot,
            last_chore_status: ChoreStatusType) -> ChoreStatusType:
        leaves_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty
        if leaves_qty == chore_snapshot.filled_qty:
            chore_status = ChoreStatusType.OE_FILLED
        elif leaves_qty < chore_snapshot.filled_qty:
            chore_status = ChoreStatusType.OE_OVER_FILLED
        else:
            if last_chore_status == ChoreStatusType.OE_DOD:
                chore_status = ChoreStatusType.OE_DOD
            else:
                if last_chore_status == ChoreStatusType.OE_CXL_UNACK:
                    chore_status = ChoreStatusType.OE_CXL_UNACK
                else:
                    if chore_event == ChoreEventType.OE_AMD_UNACK:
                        chore_status = ChoreStatusType.OE_AMD
                    else:
                        chore_status = ChoreStatusType.OE_ACKED
        return chore_status

    def log_warning_based_on_amended_chore_status(self, amend_event: ChoreEventType, amended_status: ChoreStatusType,
                                                  last_chore_status: ChoreStatusType, chore_snapshot: ChoreSnapshot,
                                                  chore_journal_obj: ChoreJournal, last_leaves_qty: int) -> None:
        if amend_event not in [ChoreEventType.OE_AMD_ACK, ChoreEventType.OE_AMD_UNACK]:
            logging.error("Unexpected: received amend_event param as non-amend chore event - ignoring logs related "
                          f"to amend, {amend_event = }, {amended_status = }, {last_chore_status = }, "
                          f"{last_leaves_qty = }, chore_journal_key: "
                          f"{get_chore_journal_log_key(chore_journal_obj)};;; "
                          f"{chore_snapshot = }, {chore_journal_obj = }")
            return

        if amended_status == ChoreStatusType.OE_OVER_FILLED:
            if last_chore_status != ChoreStatusType.OE_OVER_FILLED:
                logging.warning(f"Received {amend_event} for amend qty which makes chore OVER_FILLED, "
                                f"filled_qty: {chore_snapshot.filled_qty}, "
                                f"amend_qty: {chore_snapshot.last_amend_qty}, "
                                f"{last_leaves_qty = } - putting strat to PAUSE and "
                                f"applying amend, chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                                f"{chore_journal_obj = }, {chore_snapshot = }")
                self.pause_strat()
            else:
                logging.warning(f"Received {amend_event} for amend qty which makes chore OVER_FILLED to "
                                "chore which is already OVER_FILLED, "
                                f"filled_qty: {chore_snapshot.filled_qty}, "
                                f"amend_qty: {chore_snapshot.last_amend_qty}, "
                                f"{last_leaves_qty = } - strat must be at PAUSE and "
                                f"applying amend, chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                                f"{chore_journal_obj = }, {chore_snapshot = }")
        elif amended_status == ChoreStatusType.OE_FILLED:
            logging.warning(f"Received {amend_event} for amend qty which makes chore FILLED, "
                            f"filled_qty: {chore_snapshot.filled_qty}, "
                            f"amend_qty: {chore_snapshot.last_amend_qty}, "
                            f"{last_leaves_qty = } - applying amend and putting "
                            f"chore as FILLED, chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                            f"{chore_journal_obj = }, {chore_snapshot = }")
        elif amended_status == ChoreStatusType.OE_ACKED:
            if last_chore_status == ChoreStatusType.OE_FILLED:
                logging.warning(f"Received {amend_event} for amend qty which makes chore ACKED to "
                                "chore which was FILLED before amend, "
                                f"chore_id: {chore_snapshot.chore_brief.chore_id}, "
                                f"filled_qty: {chore_snapshot.filled_qty}, "
                                f"amend_qty: {chore_snapshot.last_amend_qty}, "
                                f"{last_leaves_qty = }, chore_journal_key: "
                                f"{get_chore_journal_log_key(chore_journal_obj)};;; {chore_journal_obj = }, "
                                f"{chore_snapshot = }")
            elif last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                logging.warning(f"Received {amend_event} for amend qty which makes chore ACKED to "
                                "chore which was OVER_FILLED before amend, "
                                f"chore_id: {chore_snapshot.chore_brief.chore_id}, "
                                f"filled_qty: {chore_snapshot.filled_qty}, "
                                f"amend_qty: {chore_snapshot.last_amend_qty}, "
                                f"{last_leaves_qty = } - setting strat back to ACTIVE"
                                f" and applying amend, also ignore OVERFILLED ALERT for this chore"
                                f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                                f"{chore_journal_obj = }, {chore_snapshot = }")
                self.unpause_strat()

    def log_warning_amend_rej_reverted_chore_status(self, reverted_status: ChoreStatusType,
                                                    last_chore_status: ChoreStatusType, chore_snapshot: ChoreSnapshot,
                                                    chore_journal_obj: ChoreJournal, last_leaves_qty: int) -> None:
        if reverted_status == ChoreStatusType.OE_OVER_FILLED:
            # chore status OVERFILLED is only possible if chore got risky amended before, chore status can't be
            # OVERFILLED without amend since that means amend req came when chore was OVERFILLED which is not supported
            log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                       f"{last_chore_status} before amend applied - reverted status: {reverted_status}, "
                       f"filled_qty: {chore_snapshot.filled_qty}, "
                       f"amend_qty: {chore_snapshot.last_amend_qty}, "
                       f"{last_leaves_qty = }")
            if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                log_str += (" - strat must be at PAUSE already and "
                            f"applying amend rollback, chore_journal_key: "
                            f"{get_chore_journal_log_key(chore_journal_obj)};;; "
                            f"{chore_journal_obj = }, {chore_snapshot = }")
                logging.warning(log_str)
            else:
                log_str += (" - putting strat to pause and applying amend rollback, chore_journal_key: "
                            f"{get_chore_journal_log_key(chore_journal_obj)};;; "
                            f"{chore_journal_obj = }, {chore_snapshot = }")
                logging.warning(log_str)
                self.pause_strat()
        else:
            log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                       f"{last_chore_status} before amend applied - reverted status: {reverted_status}, "
                       f"filled_qty: {chore_snapshot.filled_qty}, amend_qty: {chore_snapshot.last_amend_qty}, "
                       f"{last_leaves_qty = }")
            if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                log_str += (" - UNPAUSING strat and applying amend rollback, "
                            f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                            f"{chore_journal_obj = }, {chore_snapshot = }")
                logging.warning(log_str)
                self.unpause_strat()
            else:
                # strat can't be paused if last_chore_status is not OVERFILLED
                log_str += (f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)};;; "
                            f"{chore_journal_obj = }, {chore_snapshot = }")
                logging.warning(log_str)

    async def _create_symbol_side_snapshot_for_new_chore(self,
                                                         new_chore_journal_obj: ChoreJournal) -> SymbolSideSnapshot:
        security = new_chore_journal_obj.chore.security
        side = new_chore_journal_obj.chore.side
        symbol_side_snapshot_obj = SymbolSideSnapshot(_id=SymbolSideSnapshot.next_id(), security=security,
                                                      side=side,
                                                      avg_px=new_chore_journal_obj.chore.px,
                                                      total_qty=int(new_chore_journal_obj.chore.qty),
                                                      total_filled_qty=0, avg_fill_px=0,
                                                      total_fill_notional=0, last_update_fill_qty=0,
                                                      last_update_fill_px=0, total_cxled_qty=0,
                                                      avg_cxled_px=0, total_cxled_notional=0,
                                                      last_update_date_time=new_chore_journal_obj.chore_event_date_time,
                                                      chore_count=1)
        symbol_side_snapshot_obj = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_create_symbol_side_snapshot_http(
                symbol_side_snapshot_obj)
        return symbol_side_snapshot_obj

    async def _create_update_symbol_side_snapshot_from_chore_journal(
            self, chore_journal: ChoreJournal, chore_snapshot_obj: ChoreSnapshot) -> SymbolSideSnapshot | None:
        async with (SymbolSideSnapshot.reentrant_lock):
            symbol_side_snapshot_objs = (
                self.strat_cache.get_symbol_side_snapshot_from_symbol(chore_journal.chore.security.sec_id))

            # If no symbol_side_snapshot for symbol-side of received chore_journal
            if symbol_side_snapshot_objs is None:
                if chore_journal.chore_event == ChoreEventType.OE_NEW:
                    created_symbol_side_snapshot = await self._create_symbol_side_snapshot_for_new_chore(chore_journal)
                    return created_symbol_side_snapshot
                else:
                    err_str_: str = (f"No OE_NEW detected for chore_journal_key: "
                                     f"{get_chore_journal_log_key(chore_journal)} "
                                     f"failed to create symbol_side_snapshot "
                                     f";;; {chore_journal = }")
                    logging.error(err_str_)
                    return
            # If symbol_side_snapshot exists for chore_id from chore_journal
            else:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_objs
                updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
                match chore_journal.chore_event:
                    case ChoreEventType.OE_NEW:
                        updated_symbol_side_snapshot_obj.chore_count = symbol_side_snapshot_obj.chore_count + 1
                        updated_symbol_side_snapshot_obj.avg_px = \
                            avg_of_new_val_sum_to_avg(symbol_side_snapshot_obj.avg_px,
                                                      chore_journal.chore.px,
                                                      updated_symbol_side_snapshot_obj.chore_count)
                        updated_symbol_side_snapshot_obj.total_qty = int(
                                symbol_side_snapshot_obj.total_qty + chore_journal.chore.qty)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        unfilled_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                        chore_snapshot_obj.total_amend_dn_qty)
                        unfilled_notional = (
                                unfilled_qty *
                                self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                chore_snapshot_obj.chore_brief.security.sec_id))
                        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
                                symbol_side_snapshot_obj.total_cxled_qty + unfilled_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                symbol_side_snapshot_obj.total_cxled_notional + unfilled_notional)
                        updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                              symbol_side_snapshot_obj.security.sec_id) /
                                updated_symbol_side_snapshot_obj.total_cxled_qty) \
                            if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time
                    case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.last_amend_qty is None and chore_snapshot_obj.last_amend_px is None:
                            logging.error("Unexpected: received both amended px and qty as None while applying "
                                          "amend on symbol_side_snapshot - ignoring strat_brief update")
                            return

                        if chore_snapshot_obj.last_amend_qty:
                            # handling amend dn
                            if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                                    # putting amended dn qty to cxled_qty and updating notional and avg_cxled_px
                                    cxled_qty = chore_snapshot_obj.last_leaves_qty - chore_snapshot_obj.last_amend_qty
                                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                        symbol_side_snapshot_obj.total_cxled_qty + cxled_qty)
                                    updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                            symbol_side_snapshot_obj.total_cxled_notional +
                                            (cxled_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                        (self.get_local_px_or_notional(
                                            updated_symbol_side_snapshot_obj.total_cxled_notional,
                                            symbol_side_snapshot_obj.security.sec_id) /
                                            updated_symbol_side_snapshot_obj.total_cxled_qty)
                                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                                else:
                                    removed_qty = (chore_snapshot_obj.last_leaves_qty -
                                                   chore_snapshot_obj.last_amend_qty)
                                    if chore_snapshot_obj.last_amend_px:
                                        # if px got amended then chore px is changed to amended value so removing
                                        # cxl_notional with old px and updating new notional with amended px
                                        removed_old_notional = (
                                                removed_qty *
                                                self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                chore_snapshot_obj.chore_brief.security.sec_id))
                                        removed_new_notional = (
                                                removed_qty *
                                                self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                chore_snapshot_obj.chore_brief.security.sec_id))

                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                            (symbol_side_snapshot_obj.total_cxled_notional -
                                             removed_old_notional + removed_new_notional))
                                        updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                            (self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id) /
                                             symbol_side_snapshot_obj.total_cxled_qty)
                                            if symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                            else:
                                # adding amended up qty to total_qty
                                updated_symbol_side_snapshot_obj.total_qty = (
                                        symbol_side_snapshot_obj.total_qty - chore_snapshot_obj.last_original_qty +
                                        chore_snapshot_obj.last_amend_qty)
                                if chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
                                    # AMD: if chore status is DOD that means amend is post DOD - adding amended up
                                    # qty to cxled_qty
                                    additional_qty = (chore_snapshot_obj.last_amend_qty -
                                                      chore_snapshot_obj.last_leaves_qty)
                                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                            symbol_side_snapshot_obj.total_cxled_qty + additional_qty)
                                    if chore_snapshot_obj.last_amend_px:
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional +
                                                (additional_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                                  chore_snapshot_obj.chore_brief.
                                                                                  security.sec_id)))
                                    else:
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional +
                                                (additional_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                                  chore_snapshot_obj.chore_brief.
                                                                                  security.sec_id)))
                                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                        (self.get_local_px_or_notional(
                                            updated_symbol_side_snapshot_obj.total_cxled_notional,
                                            symbol_side_snapshot_obj.security.sec_id) /
                                         updated_symbol_side_snapshot_obj.total_cxled_qty)
                                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                                # else not required: no cxl handling is required in amend up if chore is not DOD
                        if chore_snapshot_obj.last_amend_px:
                            current_cumulative_notional = (symbol_side_snapshot_obj.avg_px *
                                                           symbol_side_snapshot_obj.total_qty)
                            # not calculating notional with usd px since avg_px is in local px
                            old_chore_notional = (chore_snapshot_obj.last_original_qty *
                                                  chore_snapshot_obj.last_original_px)
                            if chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.last_amend_qty > chore_snapshot_obj.last_leaves_qty:
                                    # chore qty is increased to amended qty if qty is amended up
                                    new_chore_notional = (chore_snapshot_obj.last_amend_qty *
                                                          chore_snapshot_obj.last_amend_px)
                                else:
                                    # chore qty stays unchanged if qty is amended dn
                                    new_chore_notional = (chore_snapshot_obj.last_original_qty *
                                                          chore_snapshot_obj.last_amend_px)
                            else:
                                new_chore_notional = (chore_snapshot_obj.chore_brief.qty *
                                                      chore_snapshot_obj.last_amend_px)
                            new_cumulative_notional = (
                                    current_cumulative_notional - old_chore_notional + new_chore_notional)
                            if chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.last_leaves_qty < chore_snapshot_obj.last_amend_qty:
                                    updated_symbol_side_snapshot_obj.avg_px = (
                                            new_cumulative_notional / updated_symbol_side_snapshot_obj.total_qty)
                                else:
                                    updated_symbol_side_snapshot_obj.avg_px = (
                                            new_cumulative_notional / symbol_side_snapshot_obj.total_qty)
                            else:
                                updated_symbol_side_snapshot_obj.avg_px = (
                                        new_cumulative_notional / symbol_side_snapshot_obj.total_qty)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time
                    case ChoreEventType.OE_AMD_REJ:
                        if chore_snapshot_obj.last_amend_qty is None and chore_snapshot_obj.last_amend_px is None:
                            logging.error("Unexpected: received both amended px and qty as None while applying "
                                          "amend rej rollback on symbol_side_snapshot - ignoring strat_brief update")
                            return

                        if chore_snapshot_obj.last_amend_qty:
                            if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                                    # removing amended dn qty from cxled_qty and updating notional and avg_cxled_px
                                    cxled_qty = chore_snapshot_obj.last_leaves_qty - chore_snapshot_obj.last_amend_qty
                                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                            symbol_side_snapshot_obj.total_cxled_qty - cxled_qty)
                                    updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                            symbol_side_snapshot_obj.total_cxled_notional -
                                            (cxled_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                        (self.get_local_px_or_notional(
                                            updated_symbol_side_snapshot_obj.total_cxled_notional,
                                            symbol_side_snapshot_obj.security.sec_id) /
                                         updated_symbol_side_snapshot_obj.total_cxled_qty)
                                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                                else:
                                    removed_qty = (chore_snapshot_obj.last_leaves_qty -
                                                   chore_snapshot_obj.last_amend_qty)
                                    if chore_snapshot_obj.last_amend_px:
                                        # if px got amended then chore px is changed to amended value so removing
                                        # cxl_notional with amended px and updating new notional with original px
                                        removed_old_notional = (
                                                removed_qty *
                                                self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                chore_snapshot_obj.chore_brief.security.sec_id))
                                        removed_amended_notional = (
                                                removed_qty *
                                                self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                chore_snapshot_obj.chore_brief.security.sec_id))

                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                            (symbol_side_snapshot_obj.total_cxled_notional +
                                             removed_old_notional - removed_amended_notional))
                                        updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                            (self.get_local_px_or_notional(
                                                updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                chore_snapshot_obj.chore_brief.security.sec_id) /
                                             symbol_side_snapshot_obj.total_cxled_qty)
                                            if symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                            else:
                                updated_symbol_side_snapshot_obj.total_qty = (
                                        symbol_side_snapshot_obj.total_qty + chore_snapshot_obj.last_original_qty -
                                        chore_snapshot_obj.last_amend_qty)
                                if chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
                                    # AMD: if chore status is DOD that means amend is post DOD - removing amended up
                                    # qty to cxled_qty
                                    additional_qty = (chore_snapshot_obj.last_amend_qty -
                                                      chore_snapshot_obj.last_leaves_qty)
                                    updated_symbol_side_snapshot_obj.total_cxled_qty = (
                                            symbol_side_snapshot_obj.total_cxled_qty - additional_qty)
                                    if chore_snapshot_obj.last_amend_px:
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional -
                                                (additional_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                                  chore_snapshot_obj.chore_brief.security.sec_id)))
                                    else:
                                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                                symbol_side_snapshot_obj.total_cxled_notional -
                                                (additional_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                                  chore_snapshot_obj.chore_brief.security.sec_id)))
                                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                                        (self.get_local_px_or_notional(
                                            updated_symbol_side_snapshot_obj.total_cxled_notional,
                                            symbol_side_snapshot_obj.security.sec_id) /
                                         updated_symbol_side_snapshot_obj.total_cxled_qty)
                                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0)
                                # else not required: no cxl handling is required in amend up if chore is not DOD
                        if chore_snapshot_obj.last_amend_px:
                            current_cumulative_notional = (symbol_side_snapshot_obj.avg_px *
                                                           symbol_side_snapshot_obj.total_qty)
                            # not calculating notional with usd px since avg_px is in local px
                            old_chore_notional = (chore_snapshot_obj.last_original_qty *
                                                  chore_snapshot_obj.last_original_px)
                            if chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.last_amend_qty > chore_snapshot_obj.last_leaves_qty:
                                    # chore qty is increased to amended qty if qty is amended up
                                    new_chore_notional = (chore_snapshot_obj.last_amend_qty *
                                                          chore_snapshot_obj.last_amend_px)
                                else:
                                    # chore qty stays unchanged if qty is amended dn
                                    new_chore_notional = (chore_snapshot_obj.last_original_qty *
                                                          chore_snapshot_obj.last_amend_px)
                            else:
                                new_chore_notional = (chore_snapshot_obj.chore_brief.qty *
                                                      chore_snapshot_obj.last_amend_px)
                            new_cumulative_notional = (
                                    current_cumulative_notional + old_chore_notional - new_chore_notional)
                            if chore_snapshot_obj.last_amend_qty:
                                if chore_snapshot_obj.last_leaves_qty < chore_snapshot_obj.last_amend_qty:
                                    updated_symbol_side_snapshot_obj.avg_px = (
                                            new_cumulative_notional / updated_symbol_side_snapshot_obj.total_qty)
                                else:
                                    updated_symbol_side_snapshot_obj.avg_px = (
                                            new_cumulative_notional / symbol_side_snapshot_obj.total_qty)
                            else:
                                updated_symbol_side_snapshot_obj.avg_px = (
                                        new_cumulative_notional / symbol_side_snapshot_obj.total_qty)
                        updated_symbol_side_snapshot_obj.last_update_date_time = chore_journal.chore_event_date_time
                    case other_:
                        err_str_ = f"Unsupported StratEventType for symbol_side_snapshot update {other_} " \
                                   f"{get_chore_journal_log_key(chore_journal)}"
                        logging.error(err_str_)
                        return
                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_side_snapshot_http(
                            json.loads(updated_symbol_side_snapshot_obj.model_dump_json(by_alias=True,
                                                                                        exclude_none=True))
                           ))
                return updated_symbol_side_snapshot_obj

    async def _check_state_and_get_chore_snapshot_obj(self, chore_journal_obj: ChoreJournal,
                                                      expected_status_list: List[str]) -> ChoreSnapshot | None:
        """
        Checks if chore_snapshot holding chore_id of passed chore_journal has expected status
        from provided statuses list and then returns that chore_snapshot
        """
        chore_snapshot_obj = self.strat_cache.get_chore_snapshot_from_chore_id(chore_journal_obj.chore.chore_id)

        if chore_snapshot_obj is not None:
            if chore_snapshot_obj.chore_status in expected_status_list:
                return chore_snapshot_obj
            else:
                ord_journal_key: str = get_chore_journal_log_key(chore_journal_obj)
                ord_snapshot_key: str = get_chore_snapshot_log_key(chore_snapshot_obj)
                err_str_: str = (f"Unexpected: Received chore_journal of event: {chore_journal_obj.chore_event} on "
                                 f"chore of chore_snapshot status: {chore_snapshot_obj.chore_status}, expected "
                                 f"chore_statuses for chore_journal event {chore_journal_obj.chore_event} is "
                                 f"{expected_status_list = }, {ord_journal_key = }, {ord_snapshot_key = };;; "
                                 f"{chore_journal_obj = }, {chore_snapshot_obj = }")
                logging.error(err_str_)
                return None
        # else not required: error occurred in _get_chore_snapshot_from_chore_journal_chore_id,
        # alert must have updated

    async def _update_strat_status_from_chore_journal(self, chore_journal_obj: ChoreJournal,
                                                      chore_snapshot: ChoreSnapshot,
                                                      symbol_side_snapshot: SymbolSideSnapshot,
                                                      strat_brief: StratBrief):
        strat_limits_tuple = self.strat_cache.get_strat_limits()

        async with StratStatus.reentrant_lock:
            strat_status_tuple = self.strat_cache.get_strat_status()

            if strat_limits_tuple is not None and strat_status_tuple is not None:
                strat_limits, _ = strat_limits_tuple
                update_strat_status_obj, _ = strat_status_tuple
                match chore_journal_obj.chore.side:
                    case Side.BUY:
                        match chore_journal_obj.chore_event:
                            case ChoreEventType.OE_NEW:
                                update_strat_status_obj.total_buy_qty += int(chore_journal_obj.chore.qty)
                                update_strat_status_obj.total_open_buy_qty += int(chore_journal_obj.chore.qty)
                                update_strat_status_obj.total_open_buy_notional += \
                                    chore_journal_obj.chore.qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                  chore_snapshot.chore_brief.security.sec_id)
                            case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                                  ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                                total_buy_unfilled_qty = \
                                    int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                        chore_snapshot.total_amend_dn_qty)
                                update_strat_status_obj.total_open_buy_qty -= total_buy_unfilled_qty
                                update_strat_status_obj.total_open_buy_notional -= \
                                    (total_buy_unfilled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                              chore_snapshot.chore_brief.security.sec_id))
                                update_strat_status_obj.total_cxl_buy_qty += int(total_buy_unfilled_qty)
                                update_strat_status_obj.total_cxl_buy_notional += \
                                    total_buy_unfilled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                             chore_snapshot.chore_brief.security.sec_id)
                                update_strat_status_obj.avg_cxl_buy_px = (
                                    (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_buy_notional,
                                                                   chore_journal_obj.chore.security.sec_id) / update_strat_status_obj.total_cxl_buy_qty)
                                    if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                                update_strat_status_obj.total_cxl_exposure = \
                                    update_strat_status_obj.total_cxl_buy_notional - \
                                    update_strat_status_obj.total_cxl_sell_notional
                            case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                                if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                    logging.error("Unexpected: received both amended px and qty as None while applying "
                                                  "amend on strat_brief - ignoring strat_brief update")
                                    return

                                if chore_snapshot.last_amend_qty:
                                    update_strat_status_obj.total_buy_qty = (
                                        update_strat_status_obj.total_buy_qty - chore_snapshot.last_original_qty +
                                        chore_snapshot.chore_brief.qty)
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                            amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                              chore_snapshot.last_amend_qty)

                                            # since chore qty doesn't get changed in amend dn on qty and cxled qty
                                            # is increased - removing newly added amend_dn qty from old cxled qty
                                            old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                            (chore_snapshot.cxled_qty - amended_dn_qty))
                                            new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                        else:
                                            old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                            new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)

                                        if old_open_qty < 0:
                                            # AMD: may happen when original qty < filled_qty, i.e., when some chore
                                            # was OVER_FILLED pre amend - no open exists in this case
                                            old_open_qty = 0
                                        if new_open_qty < 0:
                                            # AMD: may happen when amended qty < filled_qty, i.e., when some chore
                                            # becomes OVER_FILLED post amend - no open exists in this case
                                            new_open_qty = 0
                                        update_strat_status_obj.total_open_buy_qty = (
                                            update_strat_status_obj.total_open_buy_qty - old_open_qty + new_open_qty)

                                        if chore_snapshot.last_amend_px:
                                            old_open_notional = (
                                                    old_open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            old_open_notional = (
                                                    old_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                        update_strat_status_obj.total_open_buy_notional = (
                                            update_strat_status_obj.total_open_buy_notional - old_open_notional +
                                            new_open_notional)
                                    # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                                    # case of amend post DOD so open would already be removed while handling DOD

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                            cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                            update_strat_status_obj.total_cxl_buy_qty += cxled_qty

                                            update_strat_status_obj.total_cxl_buy_notional += \
                                                cxled_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                            chore_snapshot.chore_brief.security.sec_id)
                                            update_strat_status_obj.avg_cxl_buy_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_buy_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_buy_qty)
                                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                                        else:
                                            removed_qty = (chore_snapshot.last_leaves_qty -
                                                           chore_snapshot.last_amend_qty)
                                            if chore_snapshot.last_amend_px:
                                                # if px got amended then chore px is changed to amended value so
                                                # removing cxl_notional with ol px and updating new notional
                                                # with amended px
                                                removed_old_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                                removed_new_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                                update_strat_status_obj.total_cxl_buy_notional = (
                                                        update_strat_status_obj.total_cxl_buy_notional -
                                                        removed_old_notional + removed_new_notional)
                                                update_strat_status_obj.avg_cxl_buy_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_strat_status_obj.total_cxl_buy_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_strat_status_obj.total_cxl_buy_qty)
                                                    if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                                            # else not required: if chore is in DOD state and px is not amended in this
                                            # amend then amend dn notional is already in cxled notional
                                        update_strat_status_obj.total_cxl_exposure = \
                                            update_strat_status_obj.total_cxl_buy_notional - \
                                            update_strat_status_obj.total_cxl_sell_notional
                                    else:
                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                            additional_qty = (chore_snapshot.last_amend_qty -
                                                              chore_snapshot.last_leaves_qty)
                                            if chore_snapshot.last_amend_px:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            else:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            update_strat_status_obj.total_cxl_buy_qty += additional_qty
                                            update_strat_status_obj.total_cxl_buy_notional += additional_new_notional
                                            update_strat_status_obj.avg_cxl_buy_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_buy_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_buy_qty)
                                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)

                                            update_strat_status_obj.total_cxl_exposure = \
                                                update_strat_status_obj.total_cxl_buy_notional - \
                                                update_strat_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty
                                else:
                                    old_open_notional = (
                                            update_strat_status_obj.total_open_buy_qty *
                                            self.get_usd_px(chore_snapshot.last_original_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            update_strat_status_obj.total_open_buy_qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    update_strat_status_obj.total_open_buy_notional = (
                                            update_strat_status_obj.total_open_buy_notional - old_open_notional +
                                            new_open_notional)
                            case ChoreEventType.OE_AMD_REJ:
                                if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                    logging.error("Unexpected: received both amended px and qty as None while applying "
                                                  "amend on strat_brief - ignoring strat_brief update")
                                    return

                                if chore_snapshot.last_amend_qty:
                                    if chore_snapshot.last_amend_qty > chore_snapshot.last_leaves_qty:
                                        update_strat_status_obj.total_buy_qty = (
                                            update_strat_status_obj.total_buy_qty + chore_snapshot.last_original_qty -
                                            chore_snapshot.last_amend_qty)
                                    # else not required: qty stays unchanged in amended dn - no revert required
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                            amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                              chore_snapshot.last_amend_qty)

                                            # since chore qty doesn't get changed in amend dn on qty and
                                            # cxled qty is increased - removing added amend_dn qty from new_open_qty
                                            old_open_qty = (
                                                        chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                            new_open_qty = (
                                                        chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        (chore_snapshot.cxled_qty + amended_dn_qty))
                                        else:
                                            old_open_qty = (
                                                        chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                            new_open_qty = (chore_snapshot.last_amend_qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)

                                        if old_open_qty < 0:
                                            # AMD: may happen when original qty < filled_qty, i.e., when some chore
                                            # was OVER_FILLED pre amend - no open exists in this case
                                            old_open_qty = 0
                                        if new_open_qty < 0:
                                            # AMD: may happen when amended qty < filled_qty, i.e., when some chore
                                            # becomes OVER_FILLED post amend - no open exists in this case
                                            new_open_qty = 0

                                        # reverting open computes
                                        update_strat_status_obj.total_open_buy_qty = (
                                                update_strat_status_obj.total_open_buy_qty +
                                                old_open_qty - new_open_qty)

                                        if chore_snapshot.last_amend_px:
                                            old_open_notional = (
                                                    old_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_amend_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            old_open_notional = (
                                                    old_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        update_strat_status_obj.total_open_buy_notional = (
                                                update_strat_status_obj.total_open_buy_notional + old_open_notional -
                                                new_open_notional)
                                    # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                                    # case of amend post DOD so open would already be removed while handling DOD

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                            cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                            update_strat_status_obj.total_cxl_buy_qty -= cxled_qty

                                            update_strat_status_obj.total_cxl_buy_notional -= \
                                                cxled_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                            chore_snapshot.chore_brief.security.sec_id)
                                            update_strat_status_obj.avg_cxl_buy_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_buy_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_buy_qty)
                                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                                        else:
                                            removed_qty = (chore_snapshot.last_leaves_qty -
                                                           chore_snapshot.last_amend_qty)
                                            if chore_snapshot.last_amend_px:
                                                # if px got amended then chore px is changed to amended value so
                                                # removing cxl_notional with old px and updating new notional
                                                # with amended px
                                                removed_old_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                                removed_new_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                                update_strat_status_obj.total_cxl_buy_notional = (
                                                        update_strat_status_obj.total_cxl_buy_notional +
                                                        removed_old_notional - removed_new_notional)
                                                update_strat_status_obj.avg_cxl_buy_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_strat_status_obj.total_cxl_buy_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_strat_status_obj.total_cxl_buy_qty)
                                                    if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                                            # else not required: if chore is in DOD state and px is not amended in this
                                            # amend then amend dn notional is already in cxled notional
                                        update_strat_status_obj.total_cxl_exposure = \
                                            update_strat_status_obj.total_cxl_buy_notional - \
                                            update_strat_status_obj.total_cxl_sell_notional
                                    else:
                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                            additional_qty = (chore_snapshot.last_amend_qty -
                                                              chore_snapshot.last_leaves_qty)
                                            if chore_snapshot.last_amend_px:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_amend_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            else:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            update_strat_status_obj.total_cxl_buy_qty -= additional_qty
                                            update_strat_status_obj.total_cxl_buy_notional -= additional_new_notional
                                            update_strat_status_obj.avg_cxl_buy_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_buy_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_buy_qty)
                                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)

                                            update_strat_status_obj.total_cxl_exposure = \
                                                update_strat_status_obj.total_cxl_buy_notional - \
                                                update_strat_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty
                                else:
                                    old_open_notional = (
                                            update_strat_status_obj.total_open_buy_qty *
                                            self.get_usd_px(chore_snapshot.last_original_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            update_strat_status_obj.total_open_buy_qty *
                                            self.get_usd_px(chore_snapshot.last_amend_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    update_strat_status_obj.total_open_buy_notional = (
                                            update_strat_status_obj.total_open_buy_notional + old_open_notional -
                                            new_open_notional)
                            case other_:
                                err_str_ = f"Unsupported Chore Event type {other_}, " \
                                           f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return
                        if update_strat_status_obj.total_open_buy_qty == 0:
                            update_strat_status_obj.avg_open_buy_px = 0
                        else:
                            update_strat_status_obj.avg_open_buy_px = \
                                (self.get_local_px_or_notional(update_strat_status_obj.total_open_buy_notional,
                                                               chore_journal_obj.chore.security.sec_id) /
                                 update_strat_status_obj.total_open_buy_qty)
                    case Side.SELL:
                        match chore_journal_obj.chore_event:
                            case ChoreEventType.OE_NEW:
                                update_strat_status_obj.total_sell_qty += int(chore_journal_obj.chore.qty)
                                update_strat_status_obj.total_open_sell_qty += int(chore_journal_obj.chore.qty)
                                update_strat_status_obj.total_open_sell_notional += \
                                    chore_journal_obj.chore.qty * self.get_usd_px(chore_journal_obj.chore.px,
                                                                                  chore_journal_obj.chore.security.sec_id)
                            case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                                  ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                                total_sell_unfilled_qty = \
                                    int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                        chore_snapshot.total_amend_dn_qty)
                                update_strat_status_obj.total_open_sell_qty -= total_sell_unfilled_qty
                                update_strat_status_obj.total_open_sell_notional -= \
                                    (total_sell_unfilled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                               chore_snapshot.chore_brief.security.sec_id))
                                update_strat_status_obj.total_cxl_sell_qty += int(total_sell_unfilled_qty)
                                update_strat_status_obj.total_cxl_sell_notional += \
                                    total_sell_unfilled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                              chore_snapshot.chore_brief.security.sec_id)
                                update_strat_status_obj.avg_cxl_sell_px = (
                                    (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_sell_notional,
                                                                   chore_journal_obj.chore.security.sec_id) / update_strat_status_obj.total_cxl_sell_qty)
                                    if (update_strat_status_obj.total_cxl_sell_qty != 0) else 0)
                                update_strat_status_obj.total_cxl_exposure = \
                                    update_strat_status_obj.total_cxl_buy_notional - \
                                    update_strat_status_obj.total_cxl_sell_notional
                            case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                                if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                    logging.error("Unexpected: received both amended px and qty as None while applying "
                                                  "amend on strat_brief - ignoring strat_brief update")
                                    return

                                if chore_snapshot.last_amend_qty:
                                    update_strat_status_obj.total_sell_qty = (
                                        update_strat_status_obj.total_sell_qty - chore_snapshot.last_original_qty +
                                        chore_snapshot.chore_brief.qty)
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                            amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                              chore_snapshot.last_amend_qty)

                                            # since chore qty doesn't get changed in amend dn on qty and
                                            # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                            old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                            (chore_snapshot.cxled_qty - amended_dn_qty))
                                            new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                        else:
                                            old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                            new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                        if old_open_qty < 0:
                                            # may happen when original qty < filled_qty, i.e., when some chore
                                            # was OVER_FILLED pre amend - no open exists in this case
                                            old_open_qty = 0
                                        if new_open_qty < 0:
                                            # may happen when amended qty < filled_qty, i.e., when some chore
                                            # becomes OVER_FILLED post amend - no open exists in this case
                                            new_open_qty = 0
                                        update_strat_status_obj.total_open_sell_qty = (
                                            update_strat_status_obj.total_open_sell_qty - old_open_qty + new_open_qty)

                                        if chore_snapshot.last_amend_px:
                                            old_open_notional = (
                                                    old_open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            old_open_notional = (
                                                    old_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                                   chore_snapshot.chore_brief.security.sec_id))
                                        update_strat_status_obj.total_open_sell_notional = (
                                            update_strat_status_obj.total_open_sell_notional - old_open_notional +
                                            new_open_notional)
                                    else:
                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                            additional_qty = (chore_snapshot.last_amend_qty -
                                                              chore_snapshot.last_leaves_qty)
                                            if chore_snapshot.last_amend_px:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            else:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            update_strat_status_obj.total_cxl_sell_qty += additional_qty
                                            update_strat_status_obj.total_cxl_sell_notional += additional_new_notional
                                            update_strat_status_obj.avg_cxl_sell_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_sell_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_sell_qty)
                                                if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)

                                            update_strat_status_obj.total_cxl_exposure = \
                                                update_strat_status_obj.total_cxl_buy_notional - \
                                                update_strat_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                            cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                            update_strat_status_obj.total_cxl_sell_qty += cxled_qty

                                            update_strat_status_obj.total_cxl_sell_notional += \
                                                cxled_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                            chore_snapshot.chore_brief.security.sec_id)
                                            update_strat_status_obj.avg_cxl_sell_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_sell_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_sell_qty)
                                                if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)
                                            update_strat_status_obj.total_cxl_exposure = \
                                                update_strat_status_obj.total_cxl_buy_notional - \
                                                update_strat_status_obj.total_cxl_sell_notional
                                        else:
                                            removed_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                            if chore_snapshot.last_amend_px:
                                                # if px got amended then chore px is changed to amended value so
                                                # removing cxl_notional with ol px and updating new notional
                                                # with amended px
                                                removed_old_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                                removed_new_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                                update_strat_status_obj.total_cxl_sell_notional = (
                                                        update_strat_status_obj.total_cxl_sell_notional -
                                                        removed_old_notional + removed_new_notional)
                                                update_strat_status_obj.avg_cxl_sell_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_strat_status_obj.total_cxl_sell_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_strat_status_obj.total_cxl_sell_qty)
                                                    if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)
                                            # else not required: if chore is in DOD state and px is not amended in this
                                            # amend then amend dn notional is already in cxled notional
                                else:
                                    old_open_notional = (
                                            update_strat_status_obj.total_open_sell_qty *
                                            self.get_usd_px(chore_snapshot.last_original_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            update_strat_status_obj.total_open_sell_qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    update_strat_status_obj.total_open_sell_notional = (
                                            update_strat_status_obj.total_open_sell_notional - old_open_notional +
                                            new_open_notional)
                            case ChoreEventType.OE_AMD_REJ:
                                if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                    logging.error("Unexpected: received both amended px and qty as None while applying "
                                                  "amend on strat_brief - ignoring strat_brief update")
                                    return

                                if chore_snapshot.last_amend_qty:
                                    if chore_snapshot.last_amend_qty > chore_snapshot.last_leaves_qty:
                                        update_strat_status_obj.total_sell_qty = (
                                                update_strat_status_obj.total_sell_qty +
                                                chore_snapshot.last_original_qty -
                                                chore_snapshot.last_amend_qty)
                                    # else not required: qty stays unchanged in amended dn - no revert required
                                    if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                        if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                            amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                              chore_snapshot.last_amend_qty)

                                            # since chore qty doesn't get changed in amend dn on qty and
                                            # cxled qty is increased - removing added amend_dn qty from new_open_qty
                                            old_open_qty = (
                                                        chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                            new_open_qty = (
                                                        chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        (chore_snapshot.cxled_qty + amended_dn_qty))
                                        else:
                                            old_open_qty = (
                                                    chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                    chore_snapshot.cxled_qty)
                                            new_open_qty = (chore_snapshot.last_amend_qty - chore_snapshot.filled_qty -
                                                            chore_snapshot.cxled_qty)
                                        if old_open_qty < 0:
                                            # AMD: may happen when original qty < filled_qty, i.e., when some chore
                                            # was OVER_FILLED pre amend - no open exists in this case
                                            old_open_qty = 0
                                        if new_open_qty < 0:
                                            # AMD: may happen when amended qty < filled_qty, i.e., when some chore
                                            # becomes OVER_FILLED post amend - no open exists in this case
                                            new_open_qty = 0
                                        update_strat_status_obj.total_open_sell_qty = (
                                                update_strat_status_obj.total_open_sell_qty +
                                                old_open_qty - new_open_qty)

                                        if chore_snapshot.last_amend_px:
                                            old_open_notional = (
                                                    old_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_original_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty *
                                                    self.get_usd_px(chore_snapshot.last_amend_px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        else:
                                            old_open_notional = (
                                                    old_open_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                            new_open_notional = (
                                                    new_open_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                                        update_strat_status_obj.total_open_sell_notional = (
                                                update_strat_status_obj.total_open_sell_notional + old_open_notional -
                                                new_open_notional)
                                    # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                                    # case of amend post DOD so open would already be removed while handling DOD

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                            cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                            update_strat_status_obj.total_cxl_sell_qty -= cxled_qty

                                            update_strat_status_obj.total_cxl_sell_notional -= \
                                                cxled_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                            chore_snapshot.chore_brief.security.sec_id)
                                            update_strat_status_obj.avg_cxl_sell_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_sell_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_sell_qty)
                                                if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)
                                        else:
                                            removed_qty = (chore_snapshot.last_leaves_qty -
                                                           chore_snapshot.last_amend_qty)
                                            if chore_snapshot.last_amend_px:
                                                # if px got amended then chore px is changed to amended value so
                                                # removing cxl_notional with old px and updating new notional
                                                # with amended px
                                                removed_old_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                                removed_new_notional = (
                                                        removed_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                                update_strat_status_obj.total_cxl_sell_notional = (
                                                        update_strat_status_obj.total_cxl_sell_notional +
                                                        removed_old_notional - removed_new_notional)
                                                update_strat_status_obj.avg_cxl_sell_px = (
                                                    (self.get_local_px_or_notional(
                                                        update_strat_status_obj.total_cxl_sell_notional,
                                                        chore_journal_obj.chore.security.sec_id) /
                                                     update_strat_status_obj.total_cxl_sell_qty)
                                                    if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)
                                            # else not required: if chore is in DOD state and px is not amended in this
                                            # amend then amend dn notional is already in cxled notional
                                        update_strat_status_obj.total_cxl_exposure = \
                                            update_strat_status_obj.total_cxl_buy_notional - \
                                            update_strat_status_obj.total_cxl_sell_notional
                                    else:
                                        # if chore is amended post DOD then adding amended up qty to cxled qty
                                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                                            additional_qty = (chore_snapshot.last_amend_qty -
                                                              chore_snapshot.last_leaves_qty)
                                            if chore_snapshot.last_amend_px:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_amend_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            else:
                                                additional_new_notional = (
                                                        additional_qty *
                                                        self.get_usd_px(chore_snapshot.last_original_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))
                                            update_strat_status_obj.total_cxl_sell_qty -= additional_qty
                                            update_strat_status_obj.total_cxl_sell_notional -= additional_new_notional
                                            update_strat_status_obj.avg_cxl_sell_px = (
                                                (self.get_local_px_or_notional(
                                                    update_strat_status_obj.total_cxl_sell_notional,
                                                    chore_journal_obj.chore.security.sec_id) /
                                                 update_strat_status_obj.total_cxl_sell_qty)
                                                if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)

                                            update_strat_status_obj.total_cxl_exposure = \
                                                update_strat_status_obj.total_cxl_sell_notional - \
                                                update_strat_status_obj.total_cxl_sell_notional
                                        # AMD: else not required: if chore is not DOD then amend up has no handling
                                        # for cxled qty
                                else:
                                    old_open_notional = (
                                            update_strat_status_obj.total_open_sell_qty *
                                            self.get_usd_px(chore_snapshot.last_original_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            update_strat_status_obj.total_open_sell_qty *
                                            self.get_usd_px(chore_snapshot.last_amend_px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                    update_strat_status_obj.total_open_sell_notional = (
                                            update_strat_status_obj.total_open_sell_notional + old_open_notional -
                                            new_open_notional)
                            case other_:
                                err_str_ = f"Unsupported Chore Event type {other_} " \
                                           f"chore_journal_key: {get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return
                        if update_strat_status_obj.total_open_sell_qty == 0:
                            update_strat_status_obj.avg_open_sell_px = 0
                        else:
                            update_strat_status_obj.avg_open_sell_px = \
                                self.get_local_px_or_notional(update_strat_status_obj.total_open_sell_notional,
                                                              chore_journal_obj.chore.security.sec_id) / \
                                update_strat_status_obj.total_open_sell_qty
                    case other_:
                        err_str_ = f"Unsupported Side Type {other_} received in chore_journal_key: " \
                                   f"{get_chore_journal_log_key(chore_journal_obj)} while updating strat_status;;; " \
                                   f"{chore_journal_obj = }"
                        logging.error(err_str_)
                        return
                update_strat_status_obj.total_chore_qty = \
                    int(update_strat_status_obj.total_buy_qty + update_strat_status_obj.total_sell_qty)
                update_strat_status_obj.total_open_exposure = (update_strat_status_obj.total_open_buy_notional -
                                                               update_strat_status_obj.total_open_sell_notional)
                if update_strat_status_obj.total_fill_buy_notional < update_strat_status_obj.total_fill_sell_notional:
                    update_strat_status_obj.balance_notional = \
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_buy_notional
                else:
                    update_strat_status_obj.balance_notional = \
                        strat_limits.max_single_leg_notional - update_strat_status_obj.total_fill_sell_notional

                updated_residual = self.__get_residual_obj(chore_snapshot.chore_brief.side, strat_brief)
                if updated_residual is not None:
                    update_strat_status_obj.residual = updated_residual

                # Updating strat_state as paused if limits get breached
                self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                     strat_brief, symbol_side_snapshot)

                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_strat_status_http(
                    json.loads(update_strat_status_obj.model_dump_json(by_alias=True, exclude_none=True)))
            else:
                logging.error(f"error: either tuple of strat_status or strat_limits received as None from cache;;; "
                              f"{strat_status_tuple = }, {strat_limits_tuple = }")
                return

    async def _update_strat_brief_from_chore_or_fill(self, chore_journal_or_fills_journal: ChoreJournal | FillsJournal,
                                                     chore_snapshot: ChoreSnapshot,
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

                    all_bkr_cxlled_qty = None
                    if side == Side.BUY:
                        fetched_open_qty = strat_brief_obj.pair_buy_side_bartering_brief.open_qty
                        fetched_open_notional = strat_brief_obj.pair_buy_side_bartering_brief.open_notional
                        fetched_all_bkr_cxlled_qty = strat_brief_obj.pair_buy_side_bartering_brief.all_bkr_cxlled_qty
                    else:
                        fetched_open_qty = strat_brief_obj.pair_sell_side_bartering_brief.open_qty
                        fetched_open_notional = strat_brief_obj.pair_sell_side_bartering_brief.open_notional
                        fetched_all_bkr_cxlled_qty = strat_brief_obj.pair_sell_side_bartering_brief.all_bkr_cxlled_qty

                    if isinstance(chore_journal_or_fills_journal, ChoreJournal):
                        chore_journal: ChoreJournal = chore_journal_or_fills_journal
                        if chore_journal.chore_event == ChoreEventType.OE_NEW:
                            # When chore_event is OE_NEW then just adding current chore's total qty to existing
                            # open_qty + total notional (total chore Qty * chore px) to exist open_notional
                            if fetched_open_qty is None:
                                fetched_open_qty = 0
                            if fetched_open_notional is None:
                                fetched_open_notional = 0
                            open_qty = fetched_open_qty + chore_snapshot.chore_brief.qty
                            open_notional = (
                                    fetched_open_notional + (
                                        chore_snapshot.chore_brief.qty *
                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                        chore_snapshot.chore_brief.security.sec_id)))
                        elif chore_journal.chore_event in [ChoreEventType.OE_INT_REJ, ChoreEventType.OE_BRK_REJ,
                                                           ChoreEventType.OE_EXH_REJ]:
                            # When chore_event is OE_INT_REJ or OE_BRK_REJ or OE_EXH_REJ then just removing
                            # current chore's total qty from existing open_qty + total notional
                            # (total chore Qty * chore px) from existing open_notional
                            open_qty = fetched_open_qty - chore_snapshot.chore_brief.qty
                            open_notional = (
                                    fetched_open_notional - (
                                        chore_snapshot.chore_brief.qty *
                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                        chore_snapshot.chore_brief.security.sec_id)))
                        elif chore_journal.chore_event in [ChoreEventType.OE_CXL_ACK, ChoreEventType.OE_UNSOL_CXL]:
                            # When chore_event is OE_CXL_ACK or OE_UNSOL_CXL then removing current chore's
                            # unfilled qty from existing open_qty + unfilled notional
                            # (unfilled chore Qty * chore px) from existing open_notional
                            unfilled_qty = int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                               chore_snapshot.total_amend_dn_qty)
                            open_qty = int(fetched_open_qty - unfilled_qty)
                            open_notional = (
                                    fetched_open_notional - (
                                        unfilled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                       chore_snapshot.chore_brief.security.sec_id)))
                            if fetched_all_bkr_cxlled_qty is None:
                                all_bkr_cxlled_qty = int(unfilled_qty)
                            else:
                                all_bkr_cxlled_qty = int(fetched_all_bkr_cxlled_qty + unfilled_qty)
                        elif chore_journal.chore_event in [ChoreEventType.OE_AMD_UNACK, ChoreEventType.OE_AMD_ACK]:
                            if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                logging.error("Unexpected: received both amended px and qty as None while applying "
                                              "amend on strat_brief - ignoring strat_brief update")
                                return

                            if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                if chore_snapshot.last_amend_qty is not None:
                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                          chore_snapshot.last_amend_qty)

                                        # since chore qty doesn't get changed in amend dn on qty and
                                        # cxled qty is increased - removing newly added amend_dn qty from old cxl qty
                                        old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        (chore_snapshot.cxled_qty - amended_dn_qty))
                                        new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                    else:
                                        old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                        new_open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                    if old_open_qty < 0:
                                        # AMD: may happen when original qty < filled_qty, i.e., when some chore
                                        # was OVER_FILLED pre amend - no open exists in this case
                                        old_open_qty = 0
                                    if new_open_qty < 0:
                                        # AMD: may happen when amended qty < filled_qty, i.e., when some chore
                                        # becomes OVER_FILLED post amend - no open exists in this case
                                        new_open_qty = 0
                                    open_qty = fetched_open_qty - old_open_qty + new_open_qty

                                    if chore_snapshot.last_amend_px is not None:
                                        old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                    else:
                                        old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                    open_notional = fetched_open_notional - old_open_notional + new_open_notional

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                        all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty + cxled_qty
                                    # else not required: no cxl qty related values get updated when qty amends up
                                else:
                                    open_qty = fetched_open_qty
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                       chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                       chore_snapshot.chore_brief.security.sec_id))
                                    open_notional = fetched_open_notional - old_open_notional + new_open_notional
                            else:
                                # if chore is in DOD state then whole qty is already in
                                # cxled qty and no open chore exists to be updated
                                open_qty = fetched_open_qty
                                open_notional = fetched_open_notional

                                if chore_snapshot.last_leaves_qty < chore_snapshot.last_amend_qty:
                                    # AMD: if chore status is DOD that means amend is post DOD - adding amended up
                                    # qty to cxled_qty
                                    additional_qty = chore_snapshot.last_amend_qty - chore_snapshot.last_leaves_qty
                                    all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty + additional_qty
                                else:
                                    # AMD: if chore is in DOD state then whole qty is already in cxled qty
                                    all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty
                        elif chore_journal.chore_event == ChoreEventType.OE_AMD_REJ:
                            if chore_snapshot.last_amend_qty is None and chore_snapshot.last_amend_px is None:
                                logging.error("Unexpected: received both amended px and qty as None while applying "
                                              "amend on strat_brief - ignoring strat_brief update")
                                return

                            if chore_snapshot.chore_status != ChoreStatusType.OE_DOD:
                                if chore_snapshot.last_amend_qty is not None:
                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        amended_dn_qty = (chore_snapshot.last_leaves_qty -
                                                          chore_snapshot.last_amend_qty)

                                        # since chore qty doesn't get changed in amend dn on qty and
                                        # cxled qty is increased - removing added amend_dn qty from new_open_qty
                                        old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                        new_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        (chore_snapshot.cxled_qty + amended_dn_qty))
                                    else:
                                        old_open_qty = (chore_snapshot.last_original_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                        new_open_qty = (chore_snapshot.last_amend_qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.cxled_qty)
                                    if old_open_qty < 0:
                                        # AMD: may happen when original qty < filled_qty, i.e., when some chore
                                        # was OVER_FILLED pre amend - no open exists in this case
                                        old_open_qty = 0
                                    if new_open_qty < 0:
                                        # AMD: may happen when amended qty < filled_qty, i.e., when some chore
                                        # becomes OVER_FILLED post amend - no open exists in this case
                                        new_open_qty = 0
                                    open_qty = fetched_open_qty + old_open_qty - new_open_qty

                                    if chore_snapshot.last_amend_px is not None:
                                        old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot.last_amend_px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                    else:
                                        old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                        new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                           chore_snapshot.chore_brief.security.sec_id))
                                    open_notional = fetched_open_notional + old_open_notional - new_open_notional

                                    if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                        cxled_qty = chore_snapshot.last_leaves_qty - chore_snapshot.last_amend_qty
                                        all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty - cxled_qty
                                    # else not required: no cxl qty related values get updated when qty amends up
                                else:
                                    open_qty = fetched_open_qty
                                    old_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot.last_original_px,
                                                                       chore_snapshot.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            open_qty * self.get_usd_px(chore_snapshot.last_amend_px,
                                                                       chore_snapshot.chore_brief.security.sec_id))
                                    open_notional = fetched_open_notional + old_open_notional - new_open_notional
                            else:
                                # if chore is in DOD state then whole qty is already in
                                # cxled qty and no open chore exists to be updated
                                open_qty = fetched_open_qty
                                open_notional = fetched_open_notional

                                if chore_snapshot.last_leaves_qty < chore_snapshot.last_amend_qty:
                                    # AMD: if chore status is DOD that means amend is post DOD - removing added
                                    # amended up qty to cxled_qty
                                    additional_qty = chore_snapshot.last_amend_qty - chore_snapshot.last_leaves_qty
                                    all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty - additional_qty
                                else:
                                    # AMD: if chore is in DOD state then whole qty is already in cxled qty
                                    all_bkr_cxlled_qty = fetched_all_bkr_cxlled_qty
                        else:
                            err_str_: str = (f"Unsupported ChoreEventType: Must be either of "
                                             f"[{ChoreEventType.OE_NEW}, {ChoreEventType.OE_INT_REJ}, "
                                             f"{ChoreEventType.OE_BRK_REJ}, {ChoreEventType.OE_EXH_REJ}"
                                             f"{ChoreEventType.OE_CXL_ACK}, {ChoreEventType.OE_UNSOL_CXL}], "
                                             f"Found: {chore_journal_or_fills_journal.chore_event} - ignoring "
                                             f"strat_brief update")
                            logging.error(err_str_)
                            return
                    elif isinstance(chore_journal_or_fills_journal, FillsJournal):
                        # For fills, removing current fill's qty from existing
                        # open_qty + current fill's notional (fill_qty * chore_px) from existing open_notional
                        fills_journal: FillsJournal = chore_journal_or_fills_journal
                        if not received_fill_after_dod:
                            if not chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                open_qty = fetched_open_qty - fills_journal.fill_qty
                                open_notional = (
                                        fetched_open_notional - (
                                            fills_journal.fill_qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id)))
                            else:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                # removing only what was open originally
                                available_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty

                                open_qty = fetched_open_qty - acceptable_remaining_fill_qty
                                open_notional = fetched_open_notional - (
                                                    acceptable_remaining_fill_qty *
                                                    self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                    chore_snapshot.chore_brief.security.sec_id))
                        else:
                            # if fills come after DOD, this chore's open calculation must
                            # have already removed from overall open qty and notional - no need to remove fill qty from
                            # existing open
                            open_qty = fetched_open_qty
                            open_notional = fetched_open_notional

                            if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                available_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty
                                all_bkr_cxlled_qty = int(fetched_all_bkr_cxlled_qty - acceptable_remaining_fill_qty)
                            else:
                                all_bkr_cxlled_qty = int(fetched_all_bkr_cxlled_qty - chore_snapshot.last_update_fill_qty)
                    else:
                        err_str_: str = ("Unsupported Journal type: Must be either ChoreJournal or FillsJournal, "
                                         f"Found type: {type(chore_journal_or_fills_journal)} - ignoring "
                                         f"strat_brief update")
                        logging.error(err_str_)
                        return
                    consumable_notional = (strat_limits.max_single_leg_notional -
                                           symbol_side_snapshot.total_fill_notional - open_notional)
                    consumable_open_notional = strat_limits.max_open_single_leg_notional - open_notional
                    security_float = self.static_data.get_security_float_from_ticker(symbol)
                    if security_float is not None:
                        consumable_concentration = \
                            int((security_float / 100) * strat_limits.max_concentration -
                                (open_qty + symbol_side_snapshot.total_filled_qty))
                    else:
                        consumable_concentration = 0
                    open_chores_count = (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                                         underlying_get_open_chore_count_query_http(symbol))
                    consumable_open_chores = strat_limits.max_open_chores_per_side - open_chores_count[
                        0].open_chore_count
                    consumable_cxl_qty = ((((symbol_side_snapshot.total_filled_qty + open_qty +
                                             symbol_side_snapshot.total_cxled_qty) / 100) *
                                           strat_limits.cancel_rate.max_cancel_rate) -
                                          symbol_side_snapshot.total_cxled_qty)
                    applicable_period_second = strat_limits.market_barter_volume_participation.applicable_period_seconds
                    executor_check_snapshot_list = \
                        (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                         underlying_get_executor_check_snapshot_query_http(
                            symbol, side, applicable_period_second))
                    if len(executor_check_snapshot_list) == 1:
                        participation_period_chore_qty_sum = \
                            executor_check_snapshot_list[0].last_n_sec_chore_qty
                        indicative_consumable_participation_qty = \
                            get_consumable_participation_qty(
                                executor_check_snapshot_list,
                                strat_limits.market_barter_volume_participation.max_participation_rate)
                    else:
                        logging.error("Received unexpected length of executor_check_snapshot_list from query "
                                      f"{len(executor_check_snapshot_list)}, expected 1, symbol_side_key: "
                                      f"{get_symbol_side_key([(symbol, side)])}, likely bug in "
                                      f"get_executor_check_snapshot_query pre implementation")
                        indicative_consumable_participation_qty = 0
                        participation_period_chore_qty_sum = 0

                    updated_pair_side_brief_obj = \
                        PairSideBarteringBriefOptional(
                            security=security, side=side,
                            last_update_date_time=chore_snapshot.last_update_date_time,
                            consumable_open_chores=consumable_open_chores,
                            consumable_notional=consumable_notional,
                            consumable_open_notional=consumable_open_notional,
                            consumable_concentration=consumable_concentration,
                            participation_period_chore_qty_sum=participation_period_chore_qty_sum,
                            consumable_cxl_qty=consumable_cxl_qty,
                            indicative_consumable_participation_qty=
                            indicative_consumable_participation_qty,
                            all_bkr_cxlled_qty=all_bkr_cxlled_qty,
                            open_notional=open_notional,
                            open_qty=open_qty)

                    if side == Side.BUY:
                        other_leg_residual_qty = strat_brief_obj.pair_sell_side_bartering_brief.residual_qty
                        stored_pair_strat_bartering_brief = strat_brief_obj.pair_buy_side_bartering_brief
                        other_leg_symbol = strat_brief_obj.pair_sell_side_bartering_brief.security.sec_id
                    else:
                        other_leg_residual_qty = strat_brief_obj.pair_buy_side_bartering_brief.residual_qty
                        stored_pair_strat_bartering_brief = strat_brief_obj.pair_sell_side_bartering_brief
                        other_leg_symbol = strat_brief_obj.pair_buy_side_bartering_brief.security.sec_id
                    top_of_book_obj = self._get_top_of_book_from_symbol(symbol)
                    other_leg_top_of_book = self._get_top_of_book_from_symbol(other_leg_symbol)
                    if top_of_book_obj is not None and other_leg_top_of_book is not None:
                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                            if received_fill_after_dod:
                                residual_qty = int((stored_pair_strat_bartering_brief.residual_qty -
                                                    chore_snapshot.last_update_fill_qty))
                            else:
                                if chore_journal.chore_event == ChoreEventType.OE_AMD_ACK:
                                    # AMD post dod case: when OE_AMD_ACK comes with chore status DOD
                                    if chore_snapshot.last_amend_qty:
                                        if chore_snapshot.last_leaves_qty > chore_snapshot.last_amend_qty:
                                            # AMD: if chore qty is amended dn post DOD then whatever qty is put in
                                            # residual while handling DOD, removing amended dn qty from residual
                                            # which must already be added to total_amend_dn_qty
                                            residual_qty = int(stored_pair_strat_bartering_brief.residual_qty -
                                                               (chore_snapshot.last_leaves_qty -
                                                                chore_snapshot.last_amend_qty))
                                        else:
                                            # AMD: if chore qty is amended up post DOD then whatever qty is put in
                                            # residual while handling DOD, adding amended up qty to residual
                                            residual_qty = int(stored_pair_strat_bartering_brief.residual_qty +
                                                               (chore_snapshot.last_amend_qty -
                                                                chore_snapshot.last_leaves_qty))
                                    else:
                                        residual_qty = stored_pair_strat_bartering_brief.residual_qty
                                else:
                                    residual_qty = int(stored_pair_strat_bartering_brief.residual_qty +
                                                       (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty -
                                                        chore_snapshot.total_amend_dn_qty))
                                # else not required: If chore
                            # Updating residual_qty
                            updated_pair_side_brief_obj.residual_qty = residual_qty
                        else:
                            if received_fill_after_dod:
                                if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                    available_qty = chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty
                                    extra_fill_qty = chore_snapshot.filled_qty - available_qty
                                    acceptable_remaining_fill_qty = fills_journal.fill_qty - extra_fill_qty
                                    residual_qty = int((stored_pair_strat_bartering_brief.residual_qty -
                                                        acceptable_remaining_fill_qty))
                                else:
                                    residual_qty = int(stored_pair_strat_bartering_brief.residual_qty -
                                                       chore_snapshot.filled_qty)
                            else:
                                residual_qty = stored_pair_strat_bartering_brief.residual_qty
                            updated_pair_side_brief_obj.residual_qty = residual_qty

                        current_leg_tob_data, other_leg_tob_data = (
                            self._get_last_barter_px_n_symbol_tuples_from_tob(top_of_book_obj, other_leg_top_of_book))
                        current_leg_last_barter_px, current_leg_tob_symbol = current_leg_tob_data
                        other_leg_last_barter_px, other_leg_tob_symbol = other_leg_tob_data
                        updated_pair_side_brief_obj.indicative_consumable_residual = \
                            strat_limits.residual_restriction.max_residual - \
                            ((residual_qty * self.get_usd_px(current_leg_last_barter_px, current_leg_tob_symbol)) -
                             (other_leg_residual_qty * self.get_usd_px(other_leg_last_barter_px, other_leg_tob_symbol)))
                    else:
                        logging.error(f"received buy {top_of_book_obj = } and sell {other_leg_top_of_book = }, "
                                      f"chore_snapshot_key: {get_chore_snapshot_log_key(chore_snapshot)}")
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

                    if symbol == strat_brief_obj.pair_buy_side_bartering_brief.security.sec_id:
                        updated_strat_brief = StratBriefOptional(
                            _id=strat_brief_obj.id, pair_buy_side_bartering_brief=updated_pair_side_brief_obj,
                            consumable_nett_filled_notional=consumable_nett_filled_notional)
                    elif symbol == strat_brief_obj.pair_sell_side_bartering_brief.security.sec_id:
                        updated_strat_brief = StratBriefOptional(
                            _id=strat_brief_obj.id, pair_sell_side_bartering_brief=updated_pair_side_brief_obj,
                            consumable_nett_filled_notional=consumable_nett_filled_notional)
                    else:
                        err_str_ = f"error: None of the 2 pair_side_bartering_brief(s) contain {symbol = } in " \
                                   f"strat_brief of key: {get_strat_brief_log_key(strat_brief_obj)};;; " \
                                   f"{strat_brief_obj = }"
                        logging.exception(err_str_)
                        return

                    updated_strat_brief = \
                        (await StreetBookServiceRoutesCallbackBaseNativeOverride.
                         underlying_partial_update_strat_brief_http(
                            json.loads(updated_strat_brief.model_dump_json(by_alias=True, exclude_none=True))))
                    logging.debug(f"Updated strat_brief: {chore_snapshot.chore_brief.chore_id = }, "
                                  f"{updated_strat_brief = }")
                    return updated_strat_brief
                else:
                    logging.error(f"error: no strat_limits found in strat_cache - ignoring update of strat_brief, "
                                  f"symbol_side_key: {get_symbol_side_key([(symbol, side)])}")
                    return

            else:
                err_str_ = f"No strat brief found in strat_cache - ignoring update of strat_brief"
                logging.exception(err_str_)
                return

    async def _update_portfolio_status_from_chore_journal(
            self, chore_journal_obj: ChoreJournal,
            chore_snapshot_obj: ChoreSnapshot) -> PortfolioStatusUpdatesContainer | None:
        match chore_journal_obj.chore.side:
            case Side.BUY:
                update_overall_buy_notional = 0
                match chore_journal_obj.chore_event:
                    case ChoreEventType.OE_NEW:
                        update_overall_buy_notional = \
                            self.get_usd_px(chore_journal_obj.chore.px, chore_journal_obj.chore.security.sec_id) * \
                            chore_journal_obj.chore.qty
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        total_buy_unfilled_qty = int(chore_snapshot_obj.chore_brief.qty -
                                                     chore_snapshot_obj.filled_qty -
                                                     chore_snapshot_obj.total_amend_dn_qty)
                        update_overall_buy_notional = \
                            -(self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                              chore_snapshot_obj.chore_brief.security.sec_id) * total_buy_unfilled_qty)
                    case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                            if chore_snapshot_obj.last_amend_qty is not None:
                                if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                    amended_dn_qty = (chore_snapshot_obj.last_leaves_qty -
                                                      chore_snapshot_obj.last_amend_qty)

                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty = (chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                    (chore_snapshot_obj.cxled_qty - amended_dn_qty))
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                else:
                                    old_open_qty = (chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                if old_open_qty < 0:
                                    # may happen when original qty < filled_qty, i.e., when some chore
                                    # was OVER_FILLED pre amend - no open exists in this case
                                    old_open_qty = 0
                                if new_open_qty < 0:
                                    # may happen when amended qty < filled_qty, i.e., when some chore
                                    # becomes OVER_FILLED post amend - no open exists in this case
                                    new_open_qty = 0
                                if chore_snapshot_obj.last_amend_px is not None:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                else:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                old_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                                new_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))

                            update_overall_buy_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                    case ChoreEventType.OE_AMD_REJ:
                        if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                            if chore_snapshot_obj.last_amend_qty is not None:
                                if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                    amended_dn_qty = (chore_snapshot_obj.last_leaves_qty -
                                                      chore_snapshot_obj.last_amend_qty)

                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing added amend_dn qty from new_open_qty
                                    old_open_qty = (chore_snapshot_obj.last_original_qty -
                                                    chore_snapshot_obj.filled_qty - chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.last_original_qty -
                                                    chore_snapshot_obj.filled_qty -
                                                    (chore_snapshot_obj.cxled_qty + amended_dn_qty))
                                else:
                                    old_open_qty = (
                                                chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.last_amend_qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                if old_open_qty < 0:
                                    # may happen when original qty < filled_qty, i.e., when some chore
                                    # was OVER_FILLED pre amend - no open exists in this case
                                    old_open_qty = 0
                                if new_open_qty < 0:
                                    # may happen when amended qty < filled_qty, i.e., when some chore
                                    # becomes OVER_FILLED post amend - no open exists in this case
                                    new_open_qty = 0
                                if chore_snapshot_obj.last_amend_px is not None:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                else:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                old_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                                new_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))

                            update_overall_buy_notional = - new_open_notional + old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                return PortfolioStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional)
            case Side.SELL:
                update_overall_sell_notional = 0
                match chore_journal_obj.chore_event:
                    case ChoreEventType.OE_NEW:
                        update_overall_sell_notional = \
                            self.get_usd_px(chore_journal_obj.chore.px, chore_journal_obj.chore.security.sec_id) * \
                            chore_journal_obj.chore.qty
                    case (ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL | ChoreEventType.OE_INT_REJ |
                          ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ):
                        total_sell_unfilled_qty = int(chore_snapshot_obj.chore_brief.qty -
                                                     chore_snapshot_obj.filled_qty -
                                                     chore_snapshot_obj.total_amend_dn_qty)
                        update_overall_sell_notional = \
                            -(self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                              chore_snapshot_obj.chore_brief.security.sec_id) * total_sell_unfilled_qty)
                    case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                            if chore_snapshot_obj.last_amend_qty is not None:
                                if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                    amended_dn_qty = (chore_snapshot_obj.last_leaves_qty -
                                                      chore_snapshot_obj.last_amend_qty)

                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty = (chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                    (chore_snapshot_obj.cxled_qty - amended_dn_qty))
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                else:
                                    old_open_qty = (chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                if old_open_qty < 0:
                                    # may happen when original qty < filled_qty, i.e., when some chore
                                    # was OVER_FILLED pre amend - no open exists in this case
                                    old_open_qty = 0
                                if new_open_qty < 0:
                                    # may happen when amended qty < filled_qty, i.e., when some chore
                                    # becomes OVER_FILLED post amend - no open exists in this case
                                    new_open_qty = 0
                                if chore_snapshot_obj.last_amend_px is not None:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                else:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                old_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                                new_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                            update_overall_sell_notional = new_open_notional - old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                    case ChoreEventType.OE_AMD_UNACK | ChoreEventType.OE_AMD_ACK:
                        if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                            if chore_snapshot_obj.last_amend_qty is not None:
                                if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                    amended_dn_qty = (chore_snapshot_obj.last_leaves_qty -
                                                      chore_snapshot_obj.last_amend_qty)

                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing newly added amend_dn qty from old open qty
                                    old_open_qty = (
                                                chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                (chore_snapshot_obj.cxled_qty - amended_dn_qty))
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                else:
                                    old_open_qty = (
                                                chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                                chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                if old_open_qty < 0:
                                    # may happen when original qty < filled_qty, i.e., when some chore
                                    # was OVER_FILLED pre amend - no open exists in this case
                                    old_open_qty = 0
                                if new_open_qty < 0:
                                    # may happen when amended qty < filled_qty, i.e., when some chore
                                    # becomes OVER_FILLED post amend - no open exists in this case
                                    new_open_qty = 0
                                if chore_snapshot_obj.last_amend_px is not None:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                else:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                old_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                                new_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                            update_overall_sell_notional = - new_open_notional + old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                    case ChoreEventType.OE_AMD_REJ:
                        if chore_snapshot_obj.chore_status != ChoreStatusType.OE_DOD:
                            if chore_snapshot_obj.last_amend_qty is not None:
                                if chore_snapshot_obj.last_leaves_qty > chore_snapshot_obj.last_amend_qty:
                                    amended_dn_qty = (chore_snapshot_obj.last_leaves_qty -
                                                      chore_snapshot_obj.last_amend_qty)

                                    # since chore qty doesn't get changed in amend dn on qty and
                                    # cxled qty is increased - removing added amend_dn qty from new_open_qty
                                    old_open_qty = (chore_snapshot_obj.last_original_qty -
                                                    chore_snapshot_obj.filled_qty - chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.last_original_qty -
                                                    chore_snapshot_obj.filled_qty -
                                                    (chore_snapshot_obj.cxled_qty + amended_dn_qty))
                                else:
                                    old_open_qty = (
                                            chore_snapshot_obj.last_original_qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                    new_open_qty = (chore_snapshot_obj.last_amend_qty - chore_snapshot_obj.filled_qty -
                                                    chore_snapshot_obj.cxled_qty)
                                if old_open_qty < 0:
                                    # may happen when original qty < filled_qty, i.e., when some chore
                                    # was OVER_FILLED pre amend - no open exists in this case
                                    old_open_qty = 0
                                if new_open_qty < 0:
                                    # may happen when amended qty < filled_qty, i.e., when some chore
                                    # becomes OVER_FILLED post amend - no open exists in this case
                                    new_open_qty = 0
                                if chore_snapshot_obj.last_amend_px is not None:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                else:
                                    old_open_notional = (
                                            old_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                                    new_open_notional = (
                                            new_open_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                           chore_snapshot_obj.chore_brief.security.sec_id))
                            else:
                                open_qty = (chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.filled_qty -
                                            chore_snapshot_obj.cxled_qty)
                                old_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_original_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                                new_open_notional = (
                                        open_qty * self.get_usd_px(chore_snapshot_obj.last_amend_px,
                                                                   chore_snapshot_obj.chore_brief.security.sec_id))

                            update_overall_sell_notional = - new_open_notional + old_open_notional
                        # AMD: else not required: if chore status is DOD with AMD_ACK event then it is the
                        # case of amend post DOD so open would already be removed while handling DOD
                return PortfolioStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in chore_journal of key: " \
                           f"{get_chore_journal_log_key(chore_journal_obj)} while updating strat_status;;; " \
                           f"{chore_journal_obj = } "
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
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_fills_journal_get_all_ws(fills_journal_obj)

        async with StreetBookServiceRoutesCallbackBaseNativeOverride.residual_compute_shared_lock:
            res = await self._apply_fill_update_in_chore_snapshot(fills_journal_obj)

            if res is not None:
                strat_id, chore_snapshot, strat_brief, portfolio_status_updates = res

                # Updating and checking portfolio_limits in portfolio_manager
                post_book_service_http_client.check_portfolio_limits_query_client(
                    strat_id, None, chore_snapshot, strat_brief, portfolio_status_updates)

            # else not required: if result returned from _apply_fill_update_in_chore_snapshot is None, that
            # signifies some unexpected exception occurred so complete update was not done,
            # therefore avoiding portfolio_limit checks too

    async def _update_portfolio_status_from_fill_journal(
            self, chore_snapshot_obj: ChoreSnapshot, received_fill_after_dod: bool
            ) -> PortfolioStatusUpdatesContainer | None:

        match chore_snapshot_obj.chore_brief.side:
            case Side.BUY:
                if received_fill_after_dod:
                    update_overall_buy_notional = \
                        (chore_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                         chore_snapshot_obj.chore_brief.security.sec_id))
                else:
                    if not chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        update_overall_buy_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                    else:
                        # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                        # removing only what was open originally
                        available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        update_overall_buy_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (acceptable_remaining_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))

                update_overall_buy_fill_notional = \
                    (self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                     chore_snapshot_obj.last_update_fill_qty)
                return PortfolioStatusUpdatesContainer(buy_notional_update=update_overall_buy_notional,
                                                       buy_fill_notional_update=update_overall_buy_fill_notional)
            case Side.SELL:
                if received_fill_after_dod:
                    update_overall_sell_notional = \
                        (chore_snapshot_obj.last_update_fill_qty *
                         self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                         chore_snapshot_obj.chore_brief.security.sec_id))
                else:
                    if not chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        update_overall_sell_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                    else:
                        # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                        # removing only what was open originally
                        available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        update_overall_sell_notional = \
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)) - \
                            (acceptable_remaining_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id))
                update_overall_sell_fill_notional = \
                    self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                    chore_snapshot_obj.chore_brief.security.sec_id) * \
                    chore_snapshot_obj.last_update_fill_qty
                return PortfolioStatusUpdatesContainer(sell_notional_update=update_overall_sell_notional,
                                                       sell_fill_notional_update=update_overall_sell_fill_notional)
            case other_:
                err_str_ = f"Unsupported Side Type {other_} received in chore snapshot of key " \
                           f"{get_chore_snapshot_log_key(chore_snapshot_obj)} while updating strat_status;;; " \
                           f"{chore_snapshot_obj = }"
                logging.error(err_str_)
                return None

    async def _update_symbol_side_snapshot_from_fill_applied_chore_snapshot(
            self, chore_snapshot_obj: ChoreSnapshot, received_fill_after_dod: bool) -> SymbolSideSnapshot:
        async with SymbolSideSnapshot.reentrant_lock:
            symbol_side_snapshot_tuple = self.strat_cache.get_symbol_side_snapshot_from_symbol(
                chore_snapshot_obj.chore_brief.security.sec_id)

            if symbol_side_snapshot_tuple is not None:
                symbol_side_snapshot_obj, _ = symbol_side_snapshot_tuple
                updated_symbol_side_snapshot_obj = SymbolSideSnapshotOptional(_id=symbol_side_snapshot_obj.id)
                updated_symbol_side_snapshot_obj.total_filled_qty = int(
                    symbol_side_snapshot_obj.total_filled_qty + chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.total_fill_notional = \
                    symbol_side_snapshot_obj.total_fill_notional + \
                    (self.get_usd_px(chore_snapshot_obj.last_update_fill_px,
                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                     chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.avg_fill_px = \
                    (self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_fill_notional,
                                                   symbol_side_snapshot_obj.security.sec_id) /
                     updated_symbol_side_snapshot_obj.total_filled_qty
                     if updated_symbol_side_snapshot_obj.total_filled_qty != 0 else 0)
                updated_symbol_side_snapshot_obj.last_update_fill_px = chore_snapshot_obj.last_update_fill_px
                updated_symbol_side_snapshot_obj.last_update_fill_qty = int(chore_snapshot_obj.last_update_fill_qty)
                updated_symbol_side_snapshot_obj.last_update_date_time = chore_snapshot_obj.last_update_date_time
                if received_fill_after_dod:
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                        available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                        extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                        acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
                            symbol_side_snapshot_obj.total_cxled_qty - acceptable_remaining_fill_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                                (symbol_side_snapshot_obj.total_cxled_notional - acceptable_remaining_fill_qty *
                                 self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                 chore_snapshot_obj.chore_brief.security.sec_id)))
                    else:
                        updated_symbol_side_snapshot_obj.total_cxled_qty = int(
                            symbol_side_snapshot_obj.total_cxled_qty - chore_snapshot_obj.last_update_fill_qty)
                        updated_symbol_side_snapshot_obj.total_cxled_notional = (
                            symbol_side_snapshot_obj.total_cxled_notional -
                            (chore_snapshot_obj.last_update_fill_qty *
                             self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                             chore_snapshot_obj.chore_brief.security.sec_id)))
                    updated_symbol_side_snapshot_obj.avg_cxled_px = (
                            self.get_local_px_or_notional(updated_symbol_side_snapshot_obj.total_cxled_notional,
                                                          symbol_side_snapshot_obj.security.sec_id) /
                            updated_symbol_side_snapshot_obj.total_cxled_qty) \
                        if updated_symbol_side_snapshot_obj.total_cxled_qty != 0 else 0

                updated_symbol_side_snapshot_obj = \
                    await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                           underlying_partial_update_symbol_side_snapshot_http(
                            json.loads(updated_symbol_side_snapshot_obj.model_dump_json(
                                by_alias=True, exclude_none=True))))
                return updated_symbol_side_snapshot_obj
            else:
                err_str_ = ("Received symbol_side_snapshot_tuple as None from strat_cache for symbol: "
                            f"{chore_snapshot_obj.chore_brief.security.sec_id}, "
                            f"chore_snapshot_key: {get_chore_snapshot_log_key(chore_snapshot_obj)} - "
                            f"ignoring this symbol_side_snapshot update from fills")
                logging.error(err_str_)

    def pause_strat(self):
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=self.pair_strat_id, strat_state=StratState.StratState_PAUSED)

    def unpause_strat(self):
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=self.pair_strat_id, strat_state=StratState.StratState_ACTIVE)

    async def _apply_fill_update_in_chore_snapshot(
            self, fills_journal_obj: FillsJournal) -> Tuple[int, ChoreSnapshot, StratBrief,
                                                            PortfolioStatusUpdatesContainer| None] | None:
        pair_strat = self.strat_cache.get_pair_strat_obj()

        if not is_ongoing_strat(pair_strat):
            # avoiding any update if strat is non-ongoing
            return

        async with (ChoreSnapshot.reentrant_lock):    # for read-write atomicity
            chore_snapshot_obj = self.strat_cache.get_chore_snapshot_from_chore_id(fills_journal_obj.chore_id)

            if chore_snapshot_obj is not None:
                if chore_snapshot_obj.chore_status in [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED,
                                                       ChoreStatusType.OE_AMD,
                                                       ChoreStatusType.OE_DOD, ChoreStatusType.OE_CXL_UNACK]:
                    received_fill_after_dod = False
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
                        received_fill_after_dod = True

                    updated_total_filled_qty: int
                    if (total_filled_qty := chore_snapshot_obj.filled_qty) is not None:
                        updated_total_filled_qty = int(total_filled_qty + fills_journal_obj.fill_qty)
                    else:
                        updated_total_filled_qty = int(fills_journal_obj.fill_qty)
                    received_fill_notional = fills_journal_obj.fill_notional
                    fills_before_ack = False
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_UNACK:
                        fills_before_ack = True

                    available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                    if available_qty == updated_total_filled_qty:
                        pause_fulfill_post_chore_dod: bool = (
                            executor_config_yaml_dict.get("pause_fulfill_post_chore_dod"))
                        if received_fill_after_dod and pause_fulfill_post_chore_dod:
                            # @@@ below error log is used in specific test case for string matching - if changed here
                            # needs to be changed in test also
                            logging.critical("Unexpected: Received fill that makes chore_snapshot OE_FILLED which is "
                                             "already of state OE_DOD, ignoring this fill and putting this strat to "
                                             f"PAUSE, symbol_side_key: {get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                             f";;; {fills_journal_obj = }, {chore_snapshot_obj = }")
                            self.pause_strat()
                            return None
                            # pause_strat = True
                        else:
                            if received_fill_after_dod:
                                # @@@ below error log is used in specific test case for string matching - if changed
                                # here needs to be changed in test also
                                logging.warning(
                                    "Received fill that makes chore_snapshot OE_FILLED which is "
                                    "already of state OE_DOD, symbol_side_key: "
                                    f"{get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                    f";;; {fills_journal_obj = }, {chore_snapshot_obj = }")
                                chore_snapshot_obj.cxled_qty -= int(fills_journal_obj.fill_qty)
                                chore_snapshot_obj.cxled_notional = (
                                        chore_snapshot_obj.cxled_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                          chore_snapshot_obj.chore_brief.security.sec_id))
                                if chore_snapshot_obj.cxled_qty == 0:
                                    chore_snapshot_obj.avg_cxled_px = 0
                                else:
                                    logging.error("Unexpected: Received fill that makes chore FULFILL after DOD but "
                                                  "when fill_qty removed from cxl_qty, cxl_qty is not turning 0 ;;; "
                                                  f"fill_journal: {fills_journal_obj}, "
                                                  f"chore_journal: {chore_snapshot_obj}")

                            chore_snapshot_obj.last_chore_status = chore_snapshot_obj.chore_status
                            chore_snapshot_obj.chore_status = ChoreStatusType.OE_FILLED
                            if fills_before_ack:
                                logging.warning(f"Received fill for chore that has status: {ChoreStatusType.OE_UNACK} "
                                                f"that makes chore fulfilled, putting chore to "
                                                f"{chore_snapshot_obj.chore_status} status and applying fill")
                    elif available_qty < updated_total_filled_qty:     # OVER_FILLED
                        vacant_fill_qty = int(available_qty - chore_snapshot_obj.filled_qty)
                        non_required_received_fill_qty = fills_journal_obj.fill_qty - vacant_fill_qty

                        if received_fill_after_dod:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED which "
                                f"is already OE_DOD, {vacant_fill_qty = }, received "
                                f"{fills_journal_obj.fill_qty = }, {non_required_received_fill_qty = } "
                                f"from fills_journal_key of {fills_journal_obj.chore_id = } and "
                                f"{fills_journal_obj.id = } - putting strat to PAUSE and applying fill, "
                                f"symbol_side_key: {get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj = }, {chore_snapshot_obj = }")
                            chore_snapshot_obj.cxled_qty -= int(fills_journal_obj.fill_qty -
                                                                non_required_received_fill_qty)
                            chore_snapshot_obj.cxled_notional = (
                                    chore_snapshot_obj.cxled_qty *
                                    self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                    chore_snapshot_obj.chore_brief.security.sec_id))
                            if chore_snapshot_obj.cxled_qty == 0:
                                chore_snapshot_obj.avg_cxled_px = 0
                            else:
                                logging.error("Unexpected: Received fill that makes chore OVERFILL after DOD but "
                                              "when valid fill_qty (excluding extra fill) is removed from cxl_qty, "
                                              "cxl_qty is not turning 0 ;;; "
                                              f"fill_journal: {fills_journal_obj}, "
                                              f"chore_journal: {chore_snapshot_obj}")

                        elif fills_before_ack:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED to chore "
                                f"which is still OE_UNACK, "
                                f"{vacant_fill_qty = }, received {fills_journal_obj.fill_qty = }, "
                                f"{non_required_received_fill_qty = } "
                                f"from fills_journal_key of {fills_journal_obj.chore_id = } and "
                                f"{fills_journal_obj.id = } - putting strat to PAUSE and applying fill, "
                                f"symbol_side_key: {get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj = }, {chore_snapshot_obj = }")
                        else:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED, "
                                f"{vacant_fill_qty = }, received {fills_journal_obj.fill_qty = }, "
                                f"{non_required_received_fill_qty = } "
                                f"from fills_journal_key of {fills_journal_obj.chore_id = } and "
                                f"{fills_journal_obj.id = } - putting strat to PAUSE and applying fill, "
                                f"symbol_side_key: {get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj = }, {chore_snapshot_obj = }")
                        chore_snapshot_obj.last_chore_status = chore_snapshot_obj.chore_status
                        chore_snapshot_obj.chore_status = ChoreStatusType.OE_OVER_FILLED
                        self.pause_strat()
                        # pause_strat = True
                    else:
                        if received_fill_after_dod:
                            chore_snapshot_obj.cxled_qty = int(chore_snapshot_obj.cxled_qty -
                                                               fills_journal_obj.fill_qty)
                            chore_snapshot_obj.cxled_notional = (
                                chore_snapshot_obj.cxled_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                  chore_snapshot_obj.chore_brief.security.sec_id))
                            chore_snapshot_obj.avg_cxled_px = \
                                (self.get_local_px_or_notional(chore_snapshot_obj.cxled_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 chore_snapshot_obj.cxled_qty) if chore_snapshot_obj.cxled_qty != 0 else 0
                        elif fills_before_ack:
                            chore_snapshot_obj.last_chore_status = chore_snapshot_obj.chore_status
                            chore_snapshot_obj.chore_status = ChoreStatusType.OE_ACKED
                            logging.warning(f"Received fill for chore that has status: {ChoreStatusType.OE_UNACK}, "
                                            f"putting chore to {chore_snapshot_obj.chore_status} "
                                            f"status and applying fill")

                    if (last_filled_notional := chore_snapshot_obj.fill_notional) is not None:
                        updated_fill_notional = last_filled_notional + received_fill_notional
                    else:
                        updated_fill_notional = received_fill_notional
                    updated_avg_fill_px = \
                        (self.get_local_px_or_notional(updated_fill_notional,
                                                       fills_journal_obj.fill_symbol) / updated_total_filled_qty
                         if updated_total_filled_qty != 0 else 0)

                    chore_snapshot_obj.filled_qty = updated_total_filled_qty
                    chore_snapshot_obj.avg_fill_px = updated_avg_fill_px
                    chore_snapshot_obj.fill_notional = updated_fill_notional
                    chore_snapshot_obj.last_update_fill_qty = int(fills_journal_obj.fill_qty)
                    chore_snapshot_obj.last_update_fill_px = fills_journal_obj.fill_px
                    chore_snapshot_obj.last_update_date_time = fills_journal_obj.fill_date_time
                    chore_snapshot_obj = \
                        await (StreetBookServiceRoutesCallbackBaseNativeOverride.
                               underlying_update_chore_snapshot_http(chore_snapshot_obj))
                    symbol_side_snapshot = \
                        await self._update_symbol_side_snapshot_from_fill_applied_chore_snapshot(
                            chore_snapshot_obj, received_fill_after_dod=received_fill_after_dod)
                    if symbol_side_snapshot is not None:
                        updated_strat_brief = await self._update_strat_brief_from_chore_or_fill(
                            fills_journal_obj, chore_snapshot_obj, symbol_side_snapshot,
                            received_fill_after_dod=received_fill_after_dod)
                        if updated_strat_brief is not None:
                            await self._update_strat_status_from_fill_journal(
                                chore_snapshot_obj, symbol_side_snapshot, updated_strat_brief,
                                received_fill_after_dod=received_fill_after_dod)
                        # else not required: if updated_strat_brief is None then it means some error occurred in
                        # _update_strat_brief_from_chore which would have got added to alert already
                        portfolio_status_updates: PortfolioStatusUpdatesContainer | None = (
                            await self._update_portfolio_status_from_fill_journal(
                                chore_snapshot_obj, received_fill_after_dod=received_fill_after_dod))

                        return pair_strat.id, chore_snapshot_obj, updated_strat_brief, portfolio_status_updates

                    # else not require_create_update_symbol_side_snapshot_from_chore_journald: if symbol_side_snapshot
                    # is None then it means error occurred in _create_update_symbol_side_snapshot_from_chore_journal
                    # which would have got added to alert already
                elif chore_snapshot_obj.chore_status == ChoreStatusType.OE_FILLED:
                    err_str_ = (f"Unsupported - Fill received for completely filled chore_snapshot, "
                                f"chore_snapshot_key: {get_chore_snapshot_log_key(chore_snapshot_obj)}, "
                                f"ignoring this fill journal - putting strat to PAUSE;;; "
                                f"{fills_journal_obj = }, {chore_snapshot_obj = }")
                    logging.critical(err_str_)
                    self.pause_strat()
                else:
                    err_str_ = f"Unsupported - Fill received for chore_snapshot having status " \
                               f"{chore_snapshot_obj.chore_status}, chore_snapshot_key: " \
                               f"{get_chore_snapshot_log_key(chore_snapshot_obj)};;; " \
                               f"{fills_journal_obj = }, {chore_snapshot_obj = }"
                    logging.error(err_str_)
            else:
                err_str_ = (f"Could not find any chore snapshot with {fills_journal_obj.chore_id = } in "
                            f"strat_cache, fill_journal_key: {get_fills_journal_log_key(fills_journal_obj)}")
                logging.error(err_str_)

    async def _update_strat_status_from_fill_journal(self, chore_snapshot_obj: ChoreSnapshot,
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
                match chore_snapshot_obj.chore_brief.side:
                    case Side.BUY:
                        if not received_fill_after_dod:
                            if chore_snapshot_obj.chore_status != ChoreStatusType.OE_OVER_FILLED:
                                update_strat_status_obj.total_open_buy_qty = (
                                    int(fetched_strat_status_obj.total_open_buy_qty -
                                        chore_snapshot_obj.last_update_fill_qty))
                                update_strat_status_obj.total_open_buy_notional = (
                                        fetched_strat_status_obj.total_open_buy_notional -
                                        (chore_snapshot_obj.last_update_fill_qty *
                                         self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                            else:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                # removing only what was open originally
                                available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_strat_status_obj.total_open_buy_qty = int(
                                    fetched_strat_status_obj.total_open_buy_qty - acceptable_remaining_fill_qty)
                                update_strat_status_obj.total_open_buy_notional = (
                                        fetched_strat_status_obj.total_open_buy_notional -
                                        (acceptable_remaining_fill_qty *
                                         self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                            update_strat_status_obj.total_open_sell_notional = (
                                fetched_strat_status_obj.total_open_sell_notional)
                            if update_strat_status_obj.total_open_buy_qty == 0:
                                update_strat_status_obj.avg_open_buy_px = 0
                            else:
                                update_strat_status_obj.avg_open_buy_px = \
                                    self.get_local_px_or_notional(update_strat_status_obj.total_open_buy_notional,
                                                                  chore_snapshot_obj.chore_brief.security.sec_id) / \
                                    update_strat_status_obj.total_open_buy_qty

                        update_strat_status_obj.total_fill_buy_qty = int(
                                fetched_strat_status_obj.total_fill_buy_qty + chore_snapshot_obj.last_update_fill_qty)
                        update_strat_status_obj.total_fill_buy_notional = (
                                fetched_strat_status_obj.total_fill_buy_notional +
                                chore_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                    chore_snapshot_obj.last_update_fill_px,
                                    chore_snapshot_obj.chore_brief.security.sec_id))
                        update_strat_status_obj.avg_fill_buy_px = \
                            (self.get_local_px_or_notional(update_strat_status_obj.total_fill_buy_notional,
                                                          chore_snapshot_obj.chore_brief.security.sec_id) /
                             update_strat_status_obj.total_fill_buy_qty
                             if update_strat_status_obj.total_fill_buy_qty != 0 else 0)
                        update_strat_status_obj.total_fill_sell_notional = (
                            fetched_strat_status_obj.total_fill_sell_notional)
                        if received_fill_after_dod:
                            if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current cxl_qty
                                # removing only what was cxled qty originally
                                available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_strat_status_obj.total_cxl_buy_qty = int(
                                    fetched_strat_status_obj.total_cxl_buy_qty - acceptable_remaining_fill_qty)
                                update_strat_status_obj.total_cxl_buy_notional = (
                                        fetched_strat_status_obj.total_cxl_buy_notional -
                                        (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id) *
                                         acceptable_remaining_fill_qty))
                            else:
                                update_strat_status_obj.total_cxl_buy_qty = int(
                                        fetched_strat_status_obj.total_cxl_buy_qty -
                                        chore_snapshot_obj.last_update_fill_qty)
                                update_strat_status_obj.total_cxl_buy_notional = (
                                    fetched_strat_status_obj.total_cxl_buy_notional -
                                    (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                                     chore_snapshot_obj.last_update_fill_qty))
                            update_strat_status_obj.avg_cxl_buy_px = (
                                (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_buy_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 update_strat_status_obj.total_cxl_buy_qty)
                                if update_strat_status_obj.total_cxl_buy_qty != 0 else 0)
                            update_strat_status_obj.total_cxl_sell_notional = (
                                fetched_strat_status_obj.total_cxl_sell_notional)

                    case Side.SELL:
                        if not received_fill_after_dod:
                            if chore_snapshot_obj.chore_status != ChoreStatusType.OE_OVER_FILLED:
                                update_strat_status_obj.total_open_sell_qty = (
                                    int(fetched_strat_status_obj.total_open_sell_qty -
                                        chore_snapshot_obj.last_update_fill_qty))
                                update_strat_status_obj.total_open_sell_notional = (
                                        fetched_strat_status_obj.total_open_sell_notional -
                                        (chore_snapshot_obj.last_update_fill_qty *
                                         self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                            else:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current open
                                # removing only what was open originally
                                available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_strat_status_obj.total_open_sell_qty = int(
                                    fetched_strat_status_obj.total_open_sell_qty - acceptable_remaining_fill_qty)
                                update_strat_status_obj.total_open_sell_notional = (
                                        fetched_strat_status_obj.total_open_sell_notional -
                                        (acceptable_remaining_fill_qty *
                                         self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id)))
                            update_strat_status_obj.total_open_buy_notional = (
                                fetched_strat_status_obj.total_open_buy_notional)
                            if update_strat_status_obj.total_open_sell_qty == 0:
                                update_strat_status_obj.avg_open_sell_px = 0
                            else:
                                update_strat_status_obj.avg_open_sell_px = \
                                    self.get_local_px_or_notional(update_strat_status_obj.total_open_sell_notional,
                                                                  chore_snapshot_obj.chore_brief.security.sec_id) / \
                                    update_strat_status_obj.total_open_sell_qty

                        update_strat_status_obj.total_fill_sell_qty = int(
                                fetched_strat_status_obj.total_fill_sell_qty + chore_snapshot_obj.last_update_fill_qty)
                        update_strat_status_obj.total_fill_sell_notional = (
                                fetched_strat_status_obj.total_fill_sell_notional +
                                chore_snapshot_obj.last_update_fill_qty * self.get_usd_px(
                                    chore_snapshot_obj.last_update_fill_px,
                                    chore_snapshot_obj.chore_brief.security.sec_id))
                        if update_strat_status_obj.total_fill_sell_qty:
                            update_strat_status_obj.avg_fill_sell_px = \
                                self.get_local_px_or_notional(update_strat_status_obj.total_fill_sell_notional,
                                                              chore_snapshot_obj.chore_brief.security.sec_id) / \
                                update_strat_status_obj.total_fill_sell_qty
                        else:
                            update_strat_status_obj.avg_fill_sell_px = 0
                        update_strat_status_obj.total_fill_buy_notional = (
                            fetched_strat_status_obj.total_fill_buy_notional)

                        if received_fill_after_dod:
                            if chore_snapshot_obj.chore_status == ChoreStatusType.OE_OVER_FILLED:
                                # if fill made chore OVER_FILLED, then extra fill can't be removed from current cxl_qty
                                # removing only what was cxled qty originally
                                available_qty = chore_snapshot_obj.chore_brief.qty - chore_snapshot_obj.total_amend_dn_qty
                                extra_fill_qty = chore_snapshot_obj.filled_qty - available_qty
                                acceptable_remaining_fill_qty = chore_snapshot_obj.last_update_fill_qty - extra_fill_qty

                                update_strat_status_obj.total_cxl_sell_qty = int(
                                    fetched_strat_status_obj.total_cxl_sell_qty - acceptable_remaining_fill_qty)
                                update_strat_status_obj.total_cxl_sell_notional = (
                                        fetched_strat_status_obj.total_cxl_sell_notional -
                                        (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                         chore_snapshot_obj.chore_brief.security.sec_id) *
                                         acceptable_remaining_fill_qty))
                            else:
                                update_strat_status_obj.total_cxl_sell_qty = int(
                                        fetched_strat_status_obj.total_cxl_sell_qty -
                                        chore_snapshot_obj.last_update_fill_qty)
                                update_strat_status_obj.total_cxl_sell_notional = (
                                    fetched_strat_status_obj.total_cxl_sell_notional -
                                    (self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                     chore_snapshot_obj.chore_brief.security.sec_id) *
                                     chore_snapshot_obj.last_update_fill_qty))
                            update_strat_status_obj.avg_cxl_sell_px = (
                                (self.get_local_px_or_notional(update_strat_status_obj.total_cxl_sell_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 update_strat_status_obj.total_cxl_sell_qty)
                                if update_strat_status_obj.total_cxl_sell_qty != 0 else 0)
                            update_strat_status_obj.total_cxl_buy_notional = (
                                fetched_strat_status_obj.total_cxl_buy_notional)

                    case other_:
                        err_str_ = f"Unsupported Side Type {other_} received for chore_snapshot_key: " \
                                   f"{get_chore_snapshot_log_key(chore_snapshot_obj)} while updating strat_status;;; " \
                                   f"{chore_snapshot_obj = }"
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

                updated_residual = self.__get_residual_obj(chore_snapshot_obj.chore_brief.side, strat_brief_obj)
                if updated_residual is not None:
                    update_strat_status_obj.residual = updated_residual

                # Updating strat_state as paused if limits get breached
                self._pause_strat_if_limits_breached(update_strat_status_obj, strat_limits,
                                                     strat_brief_obj, symbol_side_snapshot)

                await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_strat_status_http(
                    json.loads(update_strat_status_obj.model_dump_json(by_alias=True, exclude_none=True)))
            else:
                logging.error(f"error: either tuple of strat_status or strat_limits received as None from cache;;; "
                              f"{strat_status_tuple = }, {strat_limits_tuple = }")
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
    # BarteringDataManager updates
    ############################

    async def partial_update_chore_journal_post(self, stored_chore_journal_obj: ChoreJournal,
                                                updated_chore_journal_obj: ChoreJournalOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_chore_journal_get_all_ws(updated_chore_journal_obj)

    async def create_chore_snapshot_post(self, chore_snapshot_obj: ChoreSnapshot):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(chore_snapshot_obj)

    async def update_chore_snapshot_post(self, stored_chore_snapshot_obj: ChoreSnapshot,
                                         updated_chore_snapshot_obj: ChoreSnapshot):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(updated_chore_snapshot_obj)

    async def partial_update_chore_snapshot_post(self, stored_chore_snapshot_obj: ChoreSnapshot,
                                                 updated_chore_snapshot_obj: ChoreSnapshotOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(updated_chore_snapshot_obj)

    async def create_symbol_side_snapshot_post(self, symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(symbol_side_snapshot_obj)

    async def update_symbol_side_snapshot_post(self, stored_symbol_side_snapshot_obj: SymbolSideSnapshot,
                                               updated_symbol_side_snapshot_obj: SymbolSideSnapshot):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def partial_update_symbol_side_snapshot_post(self, stored_symbol_side_snapshot_obj: SymbolSideSnapshot,
                                                       updated_symbol_side_snapshot_obj: SymbolSideSnapshotOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_side_snapshot_get_all_ws(updated_symbol_side_snapshot_obj)

    async def update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                       updated_strat_status_obj: StratStatus):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)

        # updating balance_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_status_obj.id,
                                                 balance_notional=
                                                 updated_strat_status_obj.balance_notional)
        logging.db(log_str)

    async def partial_update_strat_status_post(self, stored_strat_status_obj: StratStatus,
                                               updated_strat_status_obj: StratStatus):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_status_get_all_ws(updated_strat_status_obj)

        # updating balance_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_status_obj.id,
                                                 balance_notional=
                                                 updated_strat_status_obj.balance_notional)
        logging.db(log_str)

    def _call_cpp_mobile_book_updater_from_market_depth(self, market_depth: MarketDepth):
        # Convert string to bytes (for char* arguments)
        symbol = market_depth.symbol.encode('utf-8')
        market_maker = market_depth.market_maker.encode('utf-8') if market_depth.market_maker else ""
        # Convert to bytes (for char* arguments)
        exch_time_bytes = str(market_depth.exch_time).encode('utf-8')
        arrival_date_time = str(market_depth.arrival_time).encode('utf-8')
        side = 1 if market_depth.side == TickType.BID else 2
        is_smart_depth = ctypes.c_bool(market_depth.is_smart_depth) if market_depth.is_smart_depth is not None else False
        cumulative_notional = ctypes.c_float(market_depth.cumulative_notional) if market_depth.cumulative_notional else 0
        cumulative_qty = market_depth.cumulative_qty if market_depth.cumulative_qty else 0
        cumulative_avg_px = ctypes.c_float(market_depth.cumulative_avg_px) if market_depth.cumulative_avg_px else 0

        # Call the C++ function
        self.mobile_book_provider.create_or_update_md_n_tob(
            market_depth.id, symbol, exch_time_bytes, arrival_date_time, ctypes.c_int(side),
            market_depth.position,
            ctypes.c_float(market_depth.px), market_depth.qty,
            market_maker, is_smart_depth,
            cumulative_notional, cumulative_qty,
            cumulative_avg_px)

    def _call_cpp_mobile_book_updater_from_market_depth_json(self, market_depth_json: Dict):
        # Convert string to bytes (for char* arguments)
        symbol = market_depth_json.get("symbol").encode('utf-8')
        market_maker = market_depth_json.get("market_maker").encode('utf-8')
        # Convert to bytes (for char* arguments)
        exch_time_bytes = market_depth_json.get("exch_time").encode('utf-8')
        arrival_date_time = market_depth_json.get("arrival_time").encode('utf-8')
        side = 1 if market_depth_json.get("side") == "BID" else 2
        is_smart_depth = market_depth_json.get("is_smart_depth")
        is_smart_depth = ctypes.c_bool(is_smart_depth) if is_smart_depth is not None else False
        cumulative_notional = market_depth_json.get("cumulative_notional")
        cumulative_notional = ctypes.c_float(cumulative_notional) if cumulative_notional else 0
        cumulative_qty = market_depth_json.get("cumulative_qty")
        cumulative_qty = cumulative_qty if cumulative_qty else 0
        cumulative_avg_px = market_depth_json.get("cumulative_avg_px")
        cumulative_avg_px = ctypes.c_float(cumulative_avg_px) if cumulative_avg_px else 0

        # Call the C++ function
        self.mobile_book_provider.create_or_update_md_n_tob(
            market_depth_json.get("_id"), symbol, exch_time_bytes, arrival_date_time,
            ctypes.c_int(side),  market_depth_json.get("position"),
            ctypes.c_float(market_depth_json.get("px")), market_depth_json.get("qty"),
            market_maker, is_smart_depth,
            cumulative_notional, cumulative_qty, cumulative_avg_px)

    def _call_cpp_mobile_book_updater_from_last_barter(self, last_barter: LastBarter):
        # Convert string to bytes (for char* arguments)
        symbol = last_barter.symbol_n_exch_id.symbol.encode('utf-8')
        exch_id = last_barter.symbol_n_exch_id.exch_id.encode('utf-8')
        # Convert to bytes (for char* arguments)
        exch_time_bytes = str(last_barter.exch_time).encode('utf-8')
        arrival_date_time = str(last_barter.arrival_time).encode('utf-8')
        premium = ctypes.c_float(last_barter.premium) if last_barter.premium else 0
        market_barter_vol_id = last_barter.market_barter_volume.id.encode(
            'utf-8') if last_barter.market_barter_volume.id else ""
        participation_period_last_barter_qty_sum = last_barter.market_barter_volume.participation_period_last_barter_qty_sum if last_barter.market_barter_volume.participation_period_last_barter_qty_sum else 0
        applicable_period_seconds = last_barter.market_barter_volume.applicable_period_seconds if last_barter.market_barter_volume.applicable_period_seconds else 0

        # Call the C++ function
        self.mobile_book_provider.create_or_update_last_barter_n_tob(
            last_barter.id, symbol, exch_id, exch_time_bytes, arrival_date_time,
            ctypes.c_float(last_barter.px), last_barter.qty, premium,
            market_barter_vol_id, participation_period_last_barter_qty_sum,
            applicable_period_seconds)

    async def create_market_depth_pre(self, market_depth_obj: MarketDepth):
        self._call_cpp_mobile_book_updater_from_market_depth(market_depth_obj)

    async def create_all_market_depth_pre(self, market_depth_obj_list: List[MarketDepth]):
        for market_depth_obj in market_depth_obj_list:
            self._call_cpp_mobile_book_updater_from_market_depth(market_depth_obj)

    async def update_market_depth_pre(self, stored_market_depth_obj: MarketDepth,
                                      updated_market_depth_obj: MarketDepth):
        self._call_cpp_mobile_book_updater_from_market_depth(updated_market_depth_obj)
        return updated_market_depth_obj

    async def update_all_market_depth_pre(self, stored_market_depth_obj_list: List[MarketDepth],
                                          updated_market_depth_obj_list: List[MarketDepth]):
        for updated_market_depth_obj in updated_market_depth_obj_list:
            self._call_cpp_mobile_book_updater_from_market_depth(updated_market_depth_obj)
        return updated_market_depth_obj_list

    async def partial_update_market_depth_pre(self, stored_market_depth_obj: MarketDepth,
                                              updated_market_depth_obj_json: Dict):
        self._call_cpp_mobile_book_updater_from_market_depth_json(updated_market_depth_obj_json)
        return updated_market_depth_obj_json

    async def partial_update_all_market_depth_pre(self, stored_market_depth_obj_list: List[MarketDepth],
                                                  updated_market_depth_obj_json_list: List[Dict]):
        for updated_market_depth_obj_json in updated_market_depth_obj_json_list:
            self._call_cpp_mobile_book_updater_from_market_depth_json(updated_market_depth_obj_json)
        return updated_market_depth_obj_json_list

    async def create_last_barter_pre(self, last_barter_obj: LastBarter):
        self._call_cpp_mobile_book_updater_from_last_barter(last_barter_obj)

    async def create_all_last_barter_pre(self, last_barter_obj_list: List[LastBarter]):
        for last_barter_obj in last_barter_obj_list:
            self._call_cpp_mobile_book_updater_from_last_barter(last_barter_obj)

    async def partial_update_fills_journal_post(self, stored_fills_journal_obj: FillsJournal,
                                                updated_fills_journal_obj: FillsJournalOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_fills_journal_get_all_ws(updated_fills_journal_obj)

    async def create_strat_brief_post(self, strat_brief_obj: StratBrief):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_brief_get_all_ws(strat_brief_obj)

    async def update_strat_brief_post(self, stored_strat_brief_obj: StratBrief, updated_strat_brief_obj: StratBrief):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_brief_get_all_ws(updated_strat_brief_obj)

    async def partial_update_strat_brief_post(self, stored_strat_brief_obj: StratBrief,
                                              updated_strat_brief_obj: StratBriefOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_brief_get_all_ws(updated_strat_brief_obj)

    async def create_strat_status_post(self, strat_status_obj: StratStatus):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_status_get_all_ws(strat_status_obj)

        # updating balance_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=strat_status_obj.id,
                                                 balance_notional=
                                                 strat_status_obj.balance_notional)
        logging.db(log_str)

    async def create_strat_limits_post(self, strat_limits_obj: StratLimits):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_limits_get_all_ws(strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=strat_limits_obj.id,
                                                 max_single_leg_notional=strat_limits_obj.max_single_leg_notional)
        logging.db(log_str)

    async def update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                       updated_strat_limits_obj: StratLimits):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_limits_obj.id,
                                                 max_single_leg_notional=updated_strat_limits_obj.max_single_leg_notional)
        logging.db(log_str)

    async def partial_update_strat_limits_post(self, stored_strat_limits_obj: StratLimits,
                                               updated_strat_limits_obj: StratLimitsOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_strat_limits_get_all_ws(updated_strat_limits_obj)

        # updating max_single_leg_notional field in current pair_strat's StratView using log analyzer
        log_str = pair_strat_client_call_log_str(StratViewBaseModel,
                                                 photo_book_service_http_client.patch_all_strat_view_client,
                                                 UpdateType.SNAPSHOT_TYPE, _id=updated_strat_limits_obj.id,
                                                 max_single_leg_notional=updated_strat_limits_obj.max_single_leg_notional)
        logging.db(log_str)

    async def create_new_chore_post(self, new_chore_obj: NewChore):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_new_chore_get_all_ws(new_chore_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def create_cancel_chore_post(self, cancel_chore_obj: CancelChore):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_cancel_chore_get_all_ws(cancel_chore_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def partial_update_cancel_chore_post(self, stored_cancel_chore_obj: CancelChore,
                                               updated_cancel_chore_obj: CancelChoreOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_cancel_chore_get_all_ws(updated_cancel_chore_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        symbol_overview_obj.force_publish = False  # setting it false if at create is it True
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def update_symbol_overview_post(self, stored_symbol_overview_obj: SymbolOverview,
                                          updated_symbol_overview_obj: SymbolOverview):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_overview_get_all_ws(updated_symbol_overview_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def partial_update_symbol_overview_post(self, stored_symbol_overview_obj: SymbolOverview,
                                                  updated_symbol_overview_obj: SymbolOverviewOptional):
        # updating bartering_data_manager's strat_cache
        self.bartering_data_manager.handle_symbol_overview_get_all_ws(updated_symbol_overview_obj)
        self.mobile_book_provider.release_notify_semaphore()

    async def create_all_symbol_overview_post(self, symbol_overview_obj_list: List[SymbolOverview]):
        # updating bartering_data_manager's strat_cache
        for symbol_overview_obj in symbol_overview_obj_list:
            symbol_overview_obj.force_publish = False  # setting it false if at create it is True
            if self.bartering_data_manager:
                self.bartering_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
                self.mobile_book_provider.release_notify_semaphore()
            # else not required: since symbol overview is required to make executor service ready,
            #                    will add this to strat_cache explicitly using underlying http call

    async def update_all_symbol_overview_post(self, stored_symbol_overview_obj_list: List[SymbolOverview],
                                              updated_symbol_overview_obj_list: List[SymbolOverview]):
        # updating bartering_data_manager's strat_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            self.bartering_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
            self.mobile_book_provider.release_notify_semaphore()

    async def partial_update_all_symbol_overview_post(self, stored_symbol_overview_obj_list: List[SymbolOverview],
                                                      updated_symbol_overview_obj_list: List[SymbolOverviewOptional]):
        # updating bartering_data_manager's strat_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            self.bartering_data_manager.handle_symbol_overview_get_all_ws(symbol_overview_obj)
            self.mobile_book_provider.release_notify_semaphore()

    #####################
    # Query Pre/Post handling
    #####################

    async def get_symbol_side_snapshot_from_symbol_side_query_pre(
            self, symbol_side_snapshot_class_type: Type[SymbolSideSnapshot], security_id: str, side: str):
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
                    update_bartering_side_brief = \
                        PairSideBarteringBriefOptional(
                            residual_qty=int(strat_brief_obj.pair_buy_side_bartering_brief.residual_qty + residual_qty))
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_buy_side_bartering_brief=update_bartering_side_brief)

                else:
                    update_bartering_side_brief = \
                        PairSideBarteringBriefOptional(
                            residual_qty=int(strat_brief_obj.pair_sell_side_bartering_brief.residual_qty + residual_qty))
                    update_strat_brief = StratBriefOptional(_id=strat_brief_obj.id,
                                                            pair_sell_side_bartering_brief=update_bartering_side_brief)

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

    async def get_open_chore_count_query_pre(self, open_chore_count_class_type: Type[OpenChoreCount], symbol: str):
        open_chores = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_chore_snapshot_http(
                get_open_chore_snapshots_for_symbol(symbol), self.get_generic_read_route())

        open_chore_count = OpenChoreCount(open_chore_count=len(open_chores))
        return [open_chore_count]

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

    @staticmethod
    def is_chore_status_terminal(chore_status: ChoreStatusType) -> bool:
        return chore_status in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED,
                                               ChoreStatusType.OE_OVER_FILLED]

    @staticmethod
    def chore_has_terminal_state(chore_snapshot: ChoreSnapshot) -> bool:
        return chore_snapshot.chore_status in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED,
                                               ChoreStatusType.OE_OVER_FILLED]

    async def cxl_expired_open_chores(self):
        open_chore_snapshots_list: List[ChoreSnapshot] = self.strat_cache.get_open_chore_snapshots()

        for open_chore_snapshot in open_chore_snapshots_list:
            if (open_chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK and
                    not self.chore_has_terminal_state(open_chore_snapshot)):
                strat_limits_tuple = self.strat_cache.get_strat_limits()
                time_delta = DateTime.utcnow() - open_chore_snapshot.create_date_time

                if strat_limits_tuple is not None:
                    strat_limits, _ = strat_limits_tuple
                    if time_delta.total_seconds() > strat_limits.residual_restriction.residual_mark_seconds:
                        logging.info(f"Triggering cxl_expired_open_chores, chore_id: "
                                     f"{open_chore_snapshot.chore_brief.chore_id}")
                        await StreetBook.bartering_link.place_cxl_chore(
                            open_chore_snapshot.chore_brief.chore_id, open_chore_snapshot.chore_brief.side,
                            open_chore_snapshot.chore_brief.security.sec_id,
                            open_chore_snapshot.chore_brief.security.sec_id,
                            open_chore_snapshot.chore_brief.underlying_account)
                    # else not required: If time-delta is still less than residual_mark_seconds then avoiding
                    # cancellation of chore
                else:
                    logging.error("Received strat_limits_tuple as None from strat_cache, ignoring cxl expiring chore "
                                  f"for this call, will retry again in {self.min_refresh_interval} secs")
            elif open_chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                logging.error("Unexpected: Received open_chore_snapshot with chore_status OE_DOD, likely bug in "
                              "get_open_chore_snapshots - list provided must not have any chore_snapshot "
                              "that is non-open")
            elif open_chore_snapshot.chore_status == ChoreStatusType.OE_FILLED:
                logging.error("Unexpected: Received open_chore_snapshot with chore_status OE_FILLED, likely bug in "
                              "get_open_chore_snapshots - list provided must not have any chore_snapshot "
                              "that is non-open")
            # else not required: avoiding cxl request if chore_snapshot already got cxl request

    async def get_strat_brief_from_symbol_query_pre(self, strat_brief_class_type: Type[StratBrief], security_id: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_strat_brief_http(
            get_strat_brief_from_symbol(security_id), self.get_generic_read_route())

    async def get_executor_check_snapshot_query_pre(
            self, executor_check_snapshot_class_type: Type[ExecutorCheckSnapshot], symbol: str,
            side: Side, last_n_sec: int):

        last_n_sec_chore_qty = await self.get_last_n_sec_chore_qty(symbol, side, last_n_sec)
        last_n_sec_barter_qty = await self.get_last_n_sec_barter_qty(symbol, side)

        if last_n_sec_chore_qty is not None and \
                last_n_sec_barter_qty is not None:
            # if no data is found by respective queries then all fields are set to 0 and every call returns
            # executor_check_snapshot object (except when exception occurs)
            executor_check_snapshot = \
                ExecutorCheckSnapshot(last_n_sec_barter_qty=last_n_sec_barter_qty,
                                      last_n_sec_chore_qty=last_n_sec_chore_qty)
            return [executor_check_snapshot]
        else:
            # will only return [] if some error occurred
            logging.error(f"no executor_check_snapshot for symbol_side_key: {get_symbol_side_key([(symbol, side)])}, as"
                          f"Received {last_n_sec_chore_qty = }, {last_n_sec_barter_qty = } "
                          f"& {last_n_sec = }; returning empty list []")
            return []

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(
            get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import get_objs_from_symbol
        return await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    async def get_last_n_sec_total_barter_qty_by_aggressive_window_first_n_last_barters(
            self, last_sec_market_barter_vol_class_type: Type[LastNSecMarketBarterVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketBarterVol]:
        symbol_side_key = get_symbol_side_key([(self.strat_leg_1.sec.sec_id, self.strat_leg_1.side)])
        first_last_barter_cont: FirstLastBarterCont = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_barter_http(
                get_last_n_sec_first_n_last_barter(symbol, last_n_sec), projection_read_http, FirstLastBarterCont)
        if ((not first_last_barter_cont) or (not first_last_barter_cont.first) or (not first_last_barter_cont.last) or
                (not first_last_barter_cont.first.market_barter_volume) or
                (not first_last_barter_cont.last.market_barter_volume) or
                (not first_last_barter_cont.first.market_barter_volume.participation_period_last_barter_qty_sum) or
                (not first_last_barter_cont.last.market_barter_volume.participation_period_last_barter_qty_sum)):
            logging.error(f"not enough data to construct last_n_sec_barter_vol for: {symbol=}, returning 0;;;"
                          f"{first_last_barter_cont=}, {symbol_side_key=}")
            return [LastNSecMarketBarterVol(last_n_sec_barter_vol=0)]
        last_n_sec_trd_vol = (first_last_barter_cont.first.market_barter_volume.participation_period_last_barter_qty_sum -
                              first_last_barter_cont.last.market_barter_volume.participation_period_last_barter_qty_sum)
        if last_n_sec_trd_vol < 0:
            if first_last_barter_cont.first.exch_time == first_last_barter_cont.last.exch_time:
                last_n_sec_trd_vol = abs(last_n_sec_trd_vol)
                logging.debug(f"{first_last_barter_cont=}")
            else:
                first_mtv = first_last_barter_cont.first.market_barter_volume
                last_mtv = first_last_barter_cont.last.market_barter_volume
                logging.error(f"unexpected {last_n_sec_trd_vol=} found -ive for {symbol=}, "
                              f"{first_mtv.participation_period_last_barter_qty_sum=}, "
                              f"{last_mtv.participation_period_last_barter_qty_sum=};;;{first_mtv=}, {last_mtv=}, "
                              f"{symbol_side_key=}")
                last_n_sec_trd_vol = 0
            return [LastNSecMarketBarterVol(last_n_sec_barter_vol=last_n_sec_trd_vol)]


    async def get_last_n_sec_total_barter_qty_query_pre(
            self, last_sec_market_barter_vol_class_type: Type[LastNSecMarketBarterVol],
            symbol: str, last_n_sec: int) -> List[LastNSecMarketBarterVol]:
        last_barter_obj_list = \
            await StreetBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_barter_http(
                get_last_n_sec_total_barter_qty(symbol, last_n_sec))
        last_n_sec_barter_vol = 0
        if last_barter_obj_list:
            last_n_sec_barter_vol = \
                last_barter_obj_list[-1].market_barter_volume.participation_period_last_barter_qty_sum

        return [LastNSecMarketBarterVol(last_n_sec_barter_vol=last_n_sec_barter_vol)]

    async def delete_symbol_overview_pre(self, pydantic_obj_to_be_deleted: SymbolOverview):
        self.strat_cache.clear_symbol_overview(pydantic_obj_to_be_deleted.id)

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
            log_book_service_http_client.remove_strat_alerts_for_strat_id_query_client(self.pair_strat_id)
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

    async def get_strat_status_from_cache_query_pre(self, strat_status_class_type: Type[StratStatus]):
        cached_strat_status_tuple = self.strat_cache.get_strat_status()
        if cached_strat_status_tuple is not None:
            cached_strat_status, _ = cached_strat_status_tuple
            if cached_strat_status is not None:
                return [cached_strat_status]
        return []

    async def get_symbol_side_snapshots_from_cache_query_pre(self,
                                                             symbol_side_snapshot_class_type: Type[SymbolSideSnapshot]):
        cached_symbol_side_snapshot_tuple = self.strat_cache.get_symbol_side_snapshot()
        if cached_symbol_side_snapshot_tuple is not None:
            cached_symbol_side_snapshot, _ = cached_symbol_side_snapshot_tuple
            if cached_symbol_side_snapshot is not None:
                return cached_symbol_side_snapshot
        return []

    async def get_strat_brief_from_cache_query_pre(self, strat_brief_class_type: Type[StratBrief]):
        cached_strat_brief_tuple = self.strat_cache.get_strat_brief()
        if cached_strat_brief_tuple is not None:
            cached_strat_brief, _ = cached_strat_brief_tuple
            if cached_strat_brief is not None:
                return [cached_strat_brief]
        return []

    async def get_new_chore_from_cache_query_pre(self, new_chore_class_type: Type[NewChore]):
        cached_new_chore_tuple = self.strat_cache.get_new_chore()
        if cached_new_chore_tuple is not None:
            cached_new_chore, _ = cached_new_chore_tuple
            if cached_new_chore is not None:
                return cached_new_chore
        return []

    async def get_strat_limits_from_cache_query_pre(self, strat_limits_class_type: Type[StratLimits]):
        cached_strat_limits_tuple = self.strat_cache.get_strat_limits()
        if cached_strat_limits_tuple is not None:
            cached_strat_limits, _ = cached_strat_limits_tuple
            if cached_strat_limits is not None:
                return [cached_strat_limits]
        return []

    async def get_chore_journals_from_cache_query_pre(self, chore_journal_class_type: Type[ChoreJournal]):
        cached_chore_journal_tuple = self.strat_cache.get_chore_journal()
        if cached_chore_journal_tuple is not None:
            cached_chore_journal, _ = cached_chore_journal_tuple
            if cached_chore_journal is not None:
                return cached_chore_journal
        return []

    async def get_fills_journal_from_cache_query_pre(self, fills_journal_class_type: Type[FillsJournal]):
        cached_fills_journal_tuple = self.strat_cache.get_fills_journal()
        if cached_fills_journal_tuple is not None:
            cached_fills_journal, _ = cached_fills_journal_tuple
            if cached_fills_journal is not None:
                return cached_fills_journal
        return []

    async def get_chore_snapshots_from_cache_query_pre(self, chore_snapshot_class_type: Type[ChoreSnapshot]):
        cached_chore_snapshot_tuple = self.strat_cache.get_chore_snapshot()
        if cached_chore_snapshot_tuple is not None:
            cached_chore_snapshot, _ = cached_chore_snapshot_tuple
            if cached_chore_snapshot is not None:
                return cached_chore_snapshot
        return []

    async def get_tob_of_book_from_cache_query_pre(self, top_of_book_class_type: Type[TopOfBook]):
        # used in test case to verify cache after recovery
        tob_list = []

        leg_1_tob_of_book = self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book()
        leg_2_tob_of_book = self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book()

        if leg_1_tob_of_book is not None:
            with MobileBookMutexManager(self.mobile_book_provider, leg_1_tob_of_book):
                tob_list.append(leg_1_tob_of_book)

        if leg_2_tob_of_book is not None:
            with MobileBookMutexManager(self.mobile_book_provider, leg_2_tob_of_book):
                tob_list.append(leg_2_tob_of_book)
        return tob_list

    #########################
    # Barter Simulator Queries
    #########################

    async def barter_simulator_place_new_chore_query_pre(
            self, barter_simulator_process_new_chore_class_type: Type[BarterSimulatorProcessNewChore],
            px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
            underlying_account: str, exchange: str | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.place_new_chore(px, qty, side, bartering_sec_id, system_sec_id, underlying_account, exchange)
        return []

    async def barter_simulator_place_cxl_chore_query_pre(
            self, barter_simulator_process_cxl_chore_class_type: Type[BarterSimulatorProcessCxlChore],
            chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
            system_sec_id: str | None = None, underlying_account: str | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.place_cxl_chore(chore_id, side, bartering_sec_id, system_sec_id, underlying_account)
        return []

    async def barter_simulator_process_chore_ack_query_pre(
            self, barter_simulator_process_chore_ack_class_type: Type[BarterSimulatorProcessChoreAck], chore_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.process_chore_ack(chore_id, px, qty, side, sec_id, underlying_account)
        return []

    async def barter_simulator_process_fill_query_pre(
            self, barter_simulator_process_fill_class_type: Type[BarterSimulatorProcessFill], chore_id: str,
            px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
            use_exact_passed_qty: bool | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.process_fill(chore_id, px, qty, side, sec_id, underlying_account, use_exact_passed_qty)
        return []

    async def barter_simulator_reload_config_query_pre(
            self, barter_simulator_reload_config_class_type: Type[BarterSimulatorReloadConfig]):
        BarterSimulator.reload_symbol_configs()
        return []

    async def barter_simulator_process_amend_req_query_pre(
            self, barter_simulator_process_amend_req_class_type: Type[BarterSimulatorProcessAmendReq], chore_id: str,
            side: Side, sec_id: str, underlying_account: str, px: float | None = None, qty: int | None = None):
        if px is None and qty is None:
            logging.error("Both Px and Qty can't be None while placing amend chore - ignoring this "
                          "amend chore creation")
            return
        await BarterSimulator.place_amend_req_chore(chore_id, side, sec_id, sec_id, underlying_account, px=px, qty=qty)
        return []

    async def barter_simulator_process_amend_ack_query_pre(
            self, barter_simulator_process_amend_ack_class_type: Type[BarterSimulatorProcessAmendAck],
            chore_id: str, side: Side, sec_id: str, underlying_account: str):
        await BarterSimulator.place_amend_ack_chore(chore_id, side, sec_id, sec_id, underlying_account)
        return []

    async def barter_simulator_process_amend_rej_query_pre(
            self, barter_simulator_process_amend_ack_class_type: Type[BarterSimulatorProcessAmendAck],
            chore_id: str, side: Side, sec_id: str, underlying_account: str):
        await BarterSimulator.place_amend_rej_chore(chore_id, side, sec_id, sec_id, underlying_account)
        return []
