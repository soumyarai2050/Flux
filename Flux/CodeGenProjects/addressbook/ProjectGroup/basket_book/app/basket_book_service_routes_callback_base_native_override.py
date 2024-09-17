# standard imports
import math
import os
import threading
from queue import Queue
from typing import Dict, Final, List, Tuple, ClassVar
import time
import datetime
import logging
from threading import Thread
import asyncio
import stat
import subprocess

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_routes_msgspec_callback import (
    BasketBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    config_yaml_path, parse_to_int, config_yaml_dict, be_host, be_port, is_all_service_up, CURRENT_PROJECT_DIR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import (
    ChoreControl, initialize_chore_control)
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_post_book_core_msgspec_model import \
    ChoreStatusType
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert, handle_refresh_configurable_data_members, set_package_logger_level)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase, market)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key, get_usd_px, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    create_symbol_overview_pre_helper, update_symbol_overview_pre_helper, partial_update_symbol_overview_pre_helper,
    create_stop_md_script)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache, SecPosExtended
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager, SecurityRecord)
from FluxPythonUtils.scripts.service import Service
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    MDShellEnvData, create_md_shell_script)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_symbol_overview_from_symbol, get_objs_from_symbol)


class BasketBookCacheContainer:
    def __init__(self, tob: TopOfBook | None = None, so: SymbolOverview | None = None,
                 buy_pos_cache: PosCache | None = None, sell_pos_cache: PosCache | None = None):
        self.tob: TopOfBook | TopOfBookBaseModel | None = tob
        self.so: SymbolOverview | SymbolOverviewBaseModel | None = so
        self.buy_pos_cache: PosCache | None = buy_pos_cache
        self.sell_pos_cache: PosCache | None = sell_pos_cache

    def has_tob_n_so(self):
        return (self.tob is not None) and (self.so is not None)

    def get_so(self, symbol: str | None = None):  # so getter need to get breach_px
        return self.so


class BasketBookServiceRoutesCallbackBaseNativeOverride(Service, BasketBookServiceRoutesCallback):
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    symbol_side_key_cache: ClassVar[Dict[str, bool]] = {}
    algo_market_chore_suffix: Final[str] = "_MKT"
    # underlying callables
    underlying_read_basket_chore_http: Callable[[...], Any] | None = None
    underlying_read_symbol_overview_http: Callable[[...], Any] | None = None
    underlying_read_top_of_book_http: Callable[[...], Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_partial_update_basket_chore_http: Callable[[...], Any] | None = None
    underlying_read_symbol_overview_by_id_http: Callable[[...], Any] | None = None

    def __init__(self):
        super().__init__()
        self.soft_amend: bool = True  # ideally read from config
        self.recovered_chores = None  # remains None until first init - which may make it empty list if no chores in DB
        self.basket_id = None
        self.epoch_time_by_symbol_dict: Dict[str, int] = {}
        self.port: int | None = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {self.usd_fx_symbol: None}
        self.usd_fx = None
        self.static_data: SecurityRecordManager | None = None
        self.cb_algo_exchange: str = "TRADING_EXCHANGE"
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        # cache for tob and symbol_overview by symbol
        self.basket_book_cache: Dict[str, BasketBookCacheContainer] = {}
        self.non_cached_basket_chore_queue: Queue[BasketChore | BasketChoreOptional] = Queue()
        # processed new chore cache dict
        self.id_to_new_chore_dict: Dict[int, NewChore] = {}
        self.id_to_sec_pos_extended_dict: Dict[int, SecPosExtended] = {}
        self.managed_chores_by_symbol: Dict[str, List[NewChore]] = {}
        self.chore_limits: ChoreLimits | ChoreLimitsBaseModel | None = None  # currently updated in Loop - Move to WS update
        # initialize ChoreControl class vars
        initialize_chore_control()

    @staticmethod
    def get_symbol_side_cache_key(system_symbol: str, side: Side):
        return f"{system_symbol}-{side.value}"

    @classmethod
    def check_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        if cls.symbol_side_key_cache.get(symbol_side_key) is None:
            return False
        return True

    @classmethod
    def set_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        if symbol_side_key not in cls.symbol_side_key_cache:
            cls.symbol_side_key_cache[symbol_side_key] = True
            return True
        else:
            # if key exists already
            return False

    @classmethod
    def clear_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        res = cls.symbol_side_key_cache.pop(symbol_side_key, None)
        if res is None:
            # if no key existed already
            logging.error(f'symbol-side key: {symbol_side_key} not found in cache to clear unack')
            return False
        else:
            return True

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_msgspec_routes import (
            underlying_read_basket_chore_http, underlying_read_symbol_overview_http, underlying_read_top_of_book_http,
            underlying_get_symbol_overview_from_symbol_query_http,
            underlying_get_top_of_book_from_symbol_query_http, underlying_partial_update_basket_chore_http,
            underlying_read_symbol_overview_by_id_http)
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = underlying_get_symbol_overview_from_symbol_query_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_partial_update_basket_chore_http = underlying_partial_update_basket_chore_http
        cls.underlying_read_basket_chore_http = underlying_read_basket_chore_http
        cls.underlying_read_symbol_overview_by_id_http = underlying_read_symbol_overview_by_id_http

    def static_data_periodic_refresh(self):
        # no action required if refreshed
        self.static_data.refresh()

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            try:
                if should_sleep:
                    time.sleep(self.min_refresh_interval)
                service_up_flag_env_var = os.environ.get(f"basket_book_{be_port}")

                if service_up_flag_env_var == "1":
                    # validate essential services are up, if so, set service ready state to true
                    if self.service_up and self.static_data is not None and self.usd_fx is not None:
                        if not self.service_ready:
                            thread: Thread = threading.Thread(target=self.handle_non_cached_basket_chore_from_queue,
                                                              daemon=True)
                            thread.start()
                            self.service_ready = True
                        print(f"INFO: basket executor service is ready: {datetime.datetime.now().time()}")

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

                        if self.usd_fx is None:
                            try:
                                if not self.update_fx_symbol_overview_dict_from_http():
                                    logging.error(f"Can't find any symbol_overview with symbol {self.usd_fx_symbol} "
                                                  f"in phone_book service, retrying in next periodic cycle",
                                                  exc_info=True)
                            except Exception as e:
                                logging.exception(f"update_fx_symbol_overview_dict_from_http failed with exception: {e}")

                        # service loop: manage all sub-services within their private try-catch to allow high level
                        # service to remain partially operational even if some sub-service is not available for any reason
                        if not static_data_service_state.ready:
                            try:
                                self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                                if self.static_data is not None:
                                    static_data_service_state.ready = True
                                    logging.debug("Marked static_data_service_state.ready True")
                                    # we just got static data - no need to sleep - force no sleep
                                    should_sleep = False
                                else:
                                    raise Exception(
                                        f"self.static_data did init to None, unexpected!!")
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                        else:
                            # refresh static data periodically (maybe more in future)
                            try:
                                self.static_data_periodic_refresh()
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                                static_data_service_state.ready = False  # forces re-init in next iteration

                        last_modified_timestamp = os.path.getmtime(config_yaml_path)
                        if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                            self.config_yaml_last_modified_timestamp = last_modified_timestamp

                            handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                     str(config_yaml_path))
                        if self.usd_fx and static_data_service_state.ready:
                            # add chore monitor / trigger logic here
                            chore_limits: ChoreLimitsBaseModel = (
                                email_book_service_http_client.get_chore_limits_client(1))
                            if chore_limits is not None:
                                self.chore_limits = chore_limits
                            # handle managed chores if found
                            try:
                                run_coro = self.trigger_or_manage_algo_chores()
                                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                                # block for task to finish
                                future.result()
                            except Exception as e:
                                logging.exception(f"trigger_or_manage_algo_chores failed with exception: {e}")
                else:
                    should_sleep = True
            except Exception as exp:
                err_ = f"exception caught in _app_launch_pre_thread_func, {exp=}, sending again"
                logging.exception(err_)

    def app_launch_pre(self):
        BasketBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        # to be called only after logger in initialized - to prevent getting overridden
        set_package_logger_level("filelock", logging.WARNING)
        logging.debug("Triggered server launch pre override")
        self.port = be_port
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

    def handle_non_cached_basket_chore_from_queue(self):
        while True:
            try:
                basket_chore: BasketChore | BasketChoreOptional = self.non_cached_basket_chore_queue.get()  # blocking call
                run_coro = self._handle_non_cached_basket_chore_from_queue(basket_chore)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                # block for task to finish
                future.result()
            except Exception as e:
                logging.exception(f"_handle_non_cached_basket_chore_from_queue failed with exception: {e}")

    async def _handle_non_cached_basket_chore_from_queue(self, basket_chore: BasketChore | BasketChoreOptional):
        new_chore_list: List[NewChore] = basket_chore.new_chores
        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            self.enrich_n_add_managed_new_chore(new_chore_obj)
        await (BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_basket_chore_http(
            basket_chore.to_dict(exclude_none=True)))

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
                    logging.debug(f"Updated {self.usd_fx=}")
                    return True
        # all else - return False
        return False

    def get_meta(self, ticker: str, side: Side) -> Tuple[Dict[str, Side], Dict[str, Side], Dict[str, str]]:
        # helps prevent reverse bartering on intraday positions where security level constraints exists
        meta_no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side] = {}
        # current strat bartering symbol and side dict - helps block intraday non recovery position updates
        meta_bartering_symbol_side_dict: Dict[str, Side] = {}
        meta_symbols_n_sec_id_source_dict: Dict[str, str] = {}  # stores symbol and symbol type [RIC, SEDOL, etc.]

        sec_rec: SecurityRecord = self.static_data.get_security_record_from_ticker(ticker)
        if self.static_data.is_cb_ticker(ticker):
            bartering_symbol: str = sec_rec.sedol
            meta_bartering_symbol_side_dict[bartering_symbol] = side
            if not sec_rec.executed_tradable:
                replenishing_side: Side = Side.SELL if side == Side.BUY else Side.BUY
                meta_no_executed_tradable_symbol_replenishing_side_dict[ticker] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[bartering_symbol] = replenishing_side
            meta_symbols_n_sec_id_source_dict[bartering_symbol] = SecurityIdSource.SEDOL

        elif self.static_data.is_eqt_ticker(ticker):
            qfii_ric, connect_ric = sec_rec.ric, sec_rec.secondary_ric
            if qfii_ric:
                meta_bartering_symbol_side_dict[qfii_ric] = side
                meta_symbols_n_sec_id_source_dict[qfii_ric] = SecurityIdSource.RIC
            if connect_ric:
                meta_bartering_symbol_side_dict[connect_ric] = side
                meta_symbols_n_sec_id_source_dict[connect_ric] = SecurityIdSource.RIC
            if not sec_rec.executed_tradable:
                replenishing_side: Side = Side.SELL if side == Side.BUY else Side.BUY
                meta_no_executed_tradable_symbol_replenishing_side_dict[ticker] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[qfii_ric] = replenishing_side
                meta_no_executed_tradable_symbol_replenishing_side_dict[connect_ric] = replenishing_side
        else:
            logging.error(f"Unsupported {ticker=}, neither cb or eqt")

        return (meta_no_executed_tradable_symbol_replenishing_side_dict, meta_bartering_symbol_side_dict,
                meta_symbols_n_sec_id_source_dict)

    async def bartering_link_place_new_chore(self, px: float, qty: int, side: Side, bartering_symbol: str,
                                           system_symbol: str, symbol_type: str, account: str, exchange: str,
                                           **kwargs) -> Tuple[bool, str]:
        """
        return bool indicating success/fail and unique-id-str/err-description in second param
        """
        chore_sent_status, ret_id_or_err_desc = await self.bartering_link.place_new_chore(
            px, qty, side, bartering_symbol, system_symbol, symbol_type, account, exchange, **kwargs)
        return chore_sent_status, ret_id_or_err_desc

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(
            get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    def get_subscription_data(self, sec_id: str, sec_id_source: SecurityIdSource):
        # currently only accepts CB ticker
        leg1_ticker: str = sec_id
        # leg2_ticker: str = self.static_data.get_underlying_eqt_ticker_from_cb_ticker(leg1_ticker)

        subscription_data: List[Tuple[str, str]] = [
            (leg1_ticker, str(sec_id_source)),
            # (leg2_ticker, str(sec_id_source))
        ]
        return subscription_data

    def create_so_shell_script(self, sec_id: str, sec_id_source: SecurityIdSource, exch_id: str,
                               continue_mode: bool = False) -> PurePath:
        # creating symbol_overview.sh file
        run_symbol_overview_file_path = CURRENT_PROJECT_DIR / "scripts" / f"new_ord_{sec_id}_so.sh"
        stop_symbol_overview_file_path = CURRENT_PROJECT_DIR / "scripts" / f"stop_new_ord_{sec_id}_so.sh"

        subscription_data = self.get_subscription_data(sec_id, sec_id_source)

        db_name: str = "basket_book"
        exch_code = "SS" if exch_id == "SSE" else "SZ"
        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=be_host, port=be_port, db_name=db_name,
                           exch_code=exch_code, project_name="basket_book"))
        mode = "SO_CONTINUE" if continue_mode else "SO"
        create_md_shell_script(md_shell_env_data, run_symbol_overview_file_path, mode, instance_id=sec_id)
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        create_stop_md_script(str(run_symbol_overview_file_path), str(stop_symbol_overview_file_path))
        os.chmod(stop_symbol_overview_file_path, stat.S_IRWXU)
        return run_symbol_overview_file_path

    @staticmethod
    def run_so_shell_script(run_symbol_overview_file_path: PurePath):
        if not os.path.exists(run_symbol_overview_file_path):
            logging.error(f"run_so_shell_script failed, file not found;;;{run_symbol_overview_file_path=}")
            return
        # so file exists, run symbol overview file
        subprocess.Popen([f"{run_symbol_overview_file_path}"])

    def loop_till_symbol_md_data_is_present(self, symbol: str,
                                            expire_wait_sec: int = 5) -> BasketBookCacheContainer | None:
        wait_sec = config_yaml_dict.get("fetch_md_data_wait_sec")
        if wait_sec is not None:
            wait_sec = int(wait_sec)

        if wait_sec is None or (60 <= wait_sec <= 0):  # wait_sec must be not None and positive less than a min
            wait_sec = 3
        total_wait: int = 0
        while True:
            cached_cont: BasketBookCacheContainer
            if (cached_cont := self.basket_book_cache.get(symbol)) and (cached_cont.tob is not None) and (
                    cached_cont.so is not None):
                return cached_cont
            elif total_wait <= expire_wait_sec:
                time.sleep(wait_sec)
                total_wait += wait_sec
            else:
                logging.error(f"loop_till_symbol_md_data_is_present failed for {symbol=}, no cached_cont in spite "
                              f"{total_wait=}")
                return None

    def get_basket_book_cache_cont(self, system_symbol: str,
                                       side: Side | None = None) -> BasketBookCacheContainer | None:
        # we expect md cache to be present if reached here
        cached_cont: BasketBookCacheContainer
        cached_cont = self.basket_book_cache.get(system_symbol)
        if cached_cont is None:
            warn_ = f"BasketBookCacheContainer not ready for {system_symbol}"
            logging.warning(warn_)
            return None
        if side is None or Side.BUY == side:
            if cached_cont.buy_pos_cache is None:
                buy_pos_cache: PosCache = self.get_pos_cache(system_symbol, Side.BUY)
                cached_cont.buy_pos_cache = buy_pos_cache
            # else not required, pos cache exist - likely for a prior chore
        elif side is None or Side.SELL == side:
            if cached_cont.sell_pos_cache is None:
                sell_pos_cache: PosCache = self.get_pos_cache(system_symbol, Side.SELL)
                cached_cont.sell_pos_cache = sell_pos_cache
            # else not required, pos cache exist - likely for a prior chore
        else:
            err_ = f"unsupported {side=} found for {system_symbol} in get_basket_book_cache_cont"
            logging.error(err_)
        if cached_cont.tob is None:
            logging.warning(f"cached_cont is not ready yet, no TOB for: {system_symbol}")
            return None  # cached_cont is not ready
        return cached_cont

    async def trigger_md_for_symbol(self, system_symbol: str, side: Side,
                                    sec_id_source: SecurityIdSource) -> bool:
        cached_cont: BasketBookCacheContainer | None
        if system_symbol not in self.basket_book_cache:
            # create and run so shell script
            exch_id: str = self.static_data.get_exchange_from_ticker(system_symbol)
            run_symbol_overview_file_path: PurePath = self.create_so_shell_script(system_symbol, sec_id_source, exch_id)
            self.run_so_shell_script(run_symbol_overview_file_path)
            md_so_trigger_time: DateTime = DateTime.utcnow()

            # wait for md cache to be updated with tob and symbol overview from this symbol
            if (cached_cont := self.loop_till_symbol_md_data_is_present(system_symbol)) is None:
                return False
        # else not required: md cache already exists for this symbol
        return True

    def get_pos_cache(self, system_symbol: str, side: Side) -> PosCache:
        (meta_no_executed_tradable_symbol_replenishing_side_dict, meta_bartering_symbol_side_dict,
         meta_symbols_n_sec_id_source_dict) = self.get_meta(system_symbol, side)

        dismiss_filter_portfolio_limit_broker_obj_list = (
            email_book_service_http_client.get_dismiss_filter_portfolio_limit_brokers_query_client(
                system_symbol, system_symbol))
        eligible_brokers: List[BrokerBaseModel] = []
        if dismiss_filter_portfolio_limit_broker_obj_list:
            eligible_brokers = dismiss_filter_portfolio_limit_broker_obj_list[0].brokers

        sod_n_intraday_pos_dict: Dict[str, Dict[str, List[Position]]] | None = None
        if hasattr(self.bartering_link, "load_positions_by_symbols_dict"):
            sod_n_intraday_pos_dict = (
                self.bartering_link.load_positions_by_symbols_dict(meta_symbols_n_sec_id_source_dict))

        pos_cache: PosCache = PosCache(self.static_data)
        pos_cache.start(eligible_brokers, sod_n_intraday_pos_dict, meta_bartering_symbol_side_dict,
                        meta_symbols_n_sec_id_source_dict, meta_no_executed_tradable_symbol_replenishing_side_dict,
                        config_dict={})
        return pos_cache

    @staticmethod
    def check_algo_chore_limits(chore_limits: ChoreLimits | ChoreLimitsBaseModel, new_ord: NewChore | NewChoreBaseModel,
                                chore_usd_notional: float, md_cache: BasketBookCacheContainer,
                                check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS):
        sys_symbol = new_ord.security.sec_id
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        is_algo: bool = True
        if new_ord.algo is None or new_ord.algo.lower() == "none":
            is_algo = False
        if check_mask == ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip other chore checks, they were conducted before, this is qty down adjusted chore

        checks_passed_ = ChoreControl.check_max_chore_notional(chore_limits, chore_usd_notional,
                                                               sys_symbol, new_ord.side, is_algo=is_algo)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        # chore qty / chore contract qty checks
        if (InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED != new_ord.security.inst_type != InstrumentType.EQT and
                chore_limits.max_chore_qty):
            checks_passed_ = ChoreControl.check_max_chore_contract_qty(chore_limits, new_ord.qty, sys_symbol,
                                                                       new_ord.side, is_algo=is_algo)
        else:
            checks_passed_ = ChoreControl.check_max_chore_qty(chore_limits, new_ord.qty, sys_symbol, new_ord.side,
                                                              is_algo=is_algo)

        if new_ord.security.inst_type == InstrumentType.EQT:
            checks_passed_ = ChoreControl.check_min_eqt_chore_qty(chore_limits, new_ord.qty, sys_symbol, new_ord.side)
            # apply min eqt chore qty check result
            if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
                checks_passed |= checks_passed_

        checks_passed_ = ChoreControl.check_px(md_cache.tob, md_cache.get_so, chore_limits, new_ord.px,
                                               new_ord.usd_px, new_ord.qty, new_ord.side, sys_symbol,
                                               None, is_algo=True)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        return checks_passed


    def enrich_n_add_managed_new_chore(self, new_chore_obj: NewChore) -> None:
        if new_chore_obj.chore_submit_state is None or (
                new_chore_obj.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_DONE):
            # For recovery cases, chore state may be pending - we still change it to failed and mark pending post basic
            # validation
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED  # only success overwrites
        px: float = new_chore_obj.px
        qty: int = new_chore_obj.qty
        side: Side = new_chore_obj.side
        system_symbol: str = new_chore_obj.security.sec_id
        err_str_: str | None = None

        # explicitly set sec_id_source if not set
        if new_chore_obj.security.sec_id_source == SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED:
            new_chore_obj.security.sec_id_source = SecurityIdSource.TICKER

        # block this new chore processing if any prior unack chore exist [user may resubmit another chore later]
        if BasketBookServiceRoutesCallbackBaseNativeOverride.check_unack(system_symbol, side):
            err_str_ = (f"past chore on smybol_side: {get_symbol_side_key([(system_symbol, side)])} is in unack state, "
                        f"dropping chore with {px=}, {qty=}, for {new_chore_obj.chore_id};;;{new_chore_obj=}")
            new_chore_obj.text = err_str_
            logging.error(err_str_)
            return

        # set inst_type if not set
        if new_chore_obj.security.inst_type is None or (
                new_chore_obj.security.inst_type == InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED):
            inst_type: InstrumentType
            if self.static_data.is_cb_ticker(system_symbol):
                inst_type = InstrumentType.CB
            elif self.static_data.is_eqt_ticker(system_symbol):  # ticker is EQT
                inst_type = InstrumentType.EQT
            else:
                err_str_ = (f"enrich_n_add_managed_new_chore failed! chore's {system_symbol=} and not found in EQT/CB "
                            f"static data for {new_chore_obj.chore_id};;;{new_chore_obj=}")
                new_chore_obj.text = err_str_
                logging.error(err_str_)
                return
            new_chore_obj.security.inst_type = inst_type

        if new_chore_obj.chore_submit_state is None or (
                new_chore_obj.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_DONE):
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING  # allow reprocessing of chore

        if not self.trigger_md_for_symbol(system_symbol, side, new_chore_obj.security.sec_id_source):
            warn_str_ = f"apply_to_basket_book_cache failed for {system_symbol=}, we'll retry in a bit"
            logging.warning(warn_str_)

        # now add manager_chores_by_symbol
        self.add_chore_to_managed_chores_by_symbol(system_symbol, new_chore_obj)

    def add_chore_to_managed_chores_by_symbol(self, system_symbol: str, chore_obj: NewChore):
        if chore_list := self.managed_chores_by_symbol.get(system_symbol):
            chore_list.append(chore_obj)
        else:
            self.managed_chores_by_symbol[system_symbol] = [chore_obj]

    async def place_checked_new_chore(self, new_chore_obj: NewChore, sec_pos_extended: SecPosExtended) -> bool:
        """
        return True if successful, False if failed
        """
        bartering_symbol: str = new_chore_obj.security.sec_id
        symbol_type = "SEDOL"
        account: str = "TRADING_ACCOUNT"
        exchange: str
        if new_chore_obj.algo.lower() == "none" or sec_pos_extended.security.inst_type == InstrumentType.EQT:
            exchange = "TRADING_EXCHANGE"
        else:
            exchange = self.cb_algo_exchange  # this is a CB Algo Chore

        kwargs = {}
        if new_chore_obj.algo != "NONE":
            if new_chore_obj.algo:
                kwargs["algo"] = new_chore_obj.algo.removesuffix(self.algo_market_chore_suffix)
                if new_chore_obj.activate_dt is not None:
                    kwargs["algo_start"] = new_chore_obj.activate_dt
                if new_chore_obj.deactivate_dt is not None:
                    kwargs["algo_expire"] = new_chore_obj.deactivate_dt
                if new_chore_obj.pov is not None:
                    kwargs["algo_mxpv"] = new_chore_obj.pov
                if new_chore_obj.mstrat is not None:
                    kwargs["mstrat"] = new_chore_obj.mstrat

        kwargs["sync_check"] = True

        # set unack for subsequent chores - this symbol to be blocked until this chore goes through
        self.set_unack(new_chore_obj.security.sec_id, new_chore_obj.side)
        res: bool
        res, ret_id_or_err_desc = await self.bartering_link_place_new_chore(new_chore_obj.px, new_chore_obj.qty,
                                                                          new_chore_obj.side, bartering_symbol,
                                                                          new_chore_obj.security.sec_id, symbol_type,
                                                                          account, exchange, **kwargs)
        # reset unack for subsequent chores to go through - this chore did fail to go through
        BasketBookServiceRoutesCallbackBaseNativeOverride.clear_unack(new_chore_obj.security.sec_id,
                                                                          new_chore_obj.side)

        if res:
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_DONE
            err_, new_chore_obj.chore_id = self.get_chore_id_from_ret_id_or_err_desc(ret_id_or_err_desc)
            new_chore_obj.text = err_
            self.id_to_new_chore_dict[new_chore_obj.id] = new_chore_obj
            self.id_to_sec_pos_extended_dict[new_chore_obj.id] = sec_pos_extended
        else:
            new_chore_obj.text = ret_id_or_err_desc

        if new_chore_obj.force_bkr is None:
            new_chore_obj.force_bkr = sec_pos_extended.broker
        # update processed new chore cache dict
        self.id_to_new_chore_dict[new_chore_obj.id] = new_chore_obj
        return res

    async def check_n_place_new_chore_(self, new_chore_obj: NewChore,
                                       md_cached_cont: BasketBookCacheContainer) -> None:
        if new_chore_obj.usd_px is None:
            new_chore_obj.usd_px = get_usd_px(new_chore_obj.px, self.usd_fx)
        usd_notional: float = new_chore_obj.usd_px * new_chore_obj.qty
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        if market.is_not_uat_nor_bartering_time():
            return
        else:
            checks_passed |= self.check_algo_chore_limits(self.chore_limits, new_chore_obj, usd_notional,
                                                          md_cached_cont, checks_passed)

        if ChoreControl.ORDER_CONTROL_SUCCESS != checks_passed:
            # error message is already logged, update new chore text
            err_str_ = (f"internal check_algo_chore_limits failed, {checks_passed=}; "
                        f"{ChoreControl.chore_control_type_dict.get(checks_passed)};;;{new_chore_obj=}")
            new_chore_obj.text = err_str_
            logging.error(err_str_)
            return
        # else - chore checks paseed

        # we don't use extract availability list here - assumption 1 chore, maps to 1 position
        if new_chore_obj.side == Side.BUY:
            pos_cache = md_cached_cont.buy_pos_cache
        elif new_chore_obj.side == Side.SELL:
            pos_cache = md_cached_cont.sell_pos_cache
        else:
            err_ = (f"unsupported {new_chore_obj.side=} found for {new_chore_obj.security.sec_id} in "
                    f"check_n_place_new_chore_;;;{new_chore_obj=}")
            logging.error(err_)
            raise Exception(err_)
        sec_pos_extended: SecPosExtended
        is_available, sec_pos_extended = pos_cache.extract_availability(new_chore_obj)
        if not is_available:
            err_str_ = (f"failed to extract position for algo chore id: {new_chore_obj.id}, "
                        f"{new_chore_obj.security.sec_id}, {new_chore_obj.side}, {new_chore_obj=};;;{sec_pos_extended=}"
                        f", retry in next iteration")
            new_chore_obj.text = err_str_
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED
            logging.error(err_str_)
            return
        else:
            logging.info(f"extracted position for {new_chore_obj=}, extracted {sec_pos_extended=}")

        res = await self.place_checked_new_chore(new_chore_obj, sec_pos_extended)
        if not res:
            pos_cache.return_availability(new_chore_obj.security.sec_id, sec_pos_extended)

    @staticmethod
    def get_chore_id_from_ret_id_or_err_desc(ret_id_or_err_desc) -> Tuple[str | None | any]:
        parts = ret_id_or_err_desc.split("---")
        match len(parts):
            case 2:
                err_ = parts[0]
                chore_id = parts[1]
            case _:
                err_ = ret_id_or_err_desc
                chore_id = None
        return err_, chore_id

    def _handle_basket_chore(self, basket_chore_obj: BasketChore | BasketChoreOptional):
        non_cached_new_chore_list: List[NewChore] = []
        new_chore_obj: NewChore
        for new_chore_obj in basket_chore_obj.new_chores:
            if self.id_to_new_chore_dict.get(new_chore_obj.id) is None:
                # this is new / recovered chore entry - add to non_cached_new_chore_list
                non_cached_new_chore_list.append(new_chore_obj)
                self.id_to_new_chore_dict[new_chore_obj.id] = new_chore_obj
                logging.info(f"Added to non_cached_new_chore_list chore: {new_chore_obj.security.sec_id} "
                             f"{new_chore_obj.side} {new_chore_obj.chore_id};;;{new_chore_obj}")

        if non_cached_new_chore_list:
            self.non_cached_basket_chore_queue.put(BasketChore.from_kwargs(id=basket_chore_obj.id,
                                                                           new_chores=non_cached_new_chore_list))

    async def create_basket_chore_pre(self, basket_chore_obj: BasketChore):
        if self.basket_id is None:
            self.basket_id = basket_chore_obj.id  # TODO: add recover from DB in init if basket chore exists
        else:
            err_: str = f"failed to create basket_chore_obj, {self.basket_id=} exists!;;;recvd: {basket_chore_obj}"
            logging.error(err_)
            raise HTTPException(detail=err_, status_code=500)
        new_chore_list: List[NewChore] = basket_chore_obj.new_chores
        if not new_chore_list:
            logging.warning("create_basket_chore_pre failed - no new chores found")
            return

        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            # to start with setting state to pending
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING

    async def create_basket_chore_post(self, basket_chore_obj: BasketChore):
        self._handle_basket_chore(basket_chore_obj)

    async def partial_update_basket_chore_pre(self, stored_basket_chore_obj_json: Dict[str, Any],
                                              updated_basket_chore_obj_json: Dict[str, Any]):
        new_chore_list: List[Dict] = updated_basket_chore_obj_json.get("new_chores")
        if new_chore_list:
            new_chore_dict: Dict
            for new_chore_dict in new_chore_list:
                if new_chore_dict.get("_id") is None:
                    # setting state to pending
                    new_chore_dict["chore_submit_state"] = ChoreSubmitType.ORDER_SUBMIT_PENDING
        return updated_basket_chore_obj_json

    async def partial_update_basket_chore_post(self, stored_basket_chore_obj_json: Dict[str, Any],
                                               updated_basket_chore_obj_json: Dict[str, Any]):
        updated_basket_chore_obj: BasketChore = BasketChore.from_dict(updated_basket_chore_obj_json)
        self._handle_basket_chore(updated_basket_chore_obj)

    def create_update_so_in_cache(self, sym_ovrw, is_create=False):
        if md_cached_cont := self.basket_book_cache.get(sym_ovrw.symbol):
            md_cached_cont.so = sym_ovrw
        else:
            if not is_create:
                logging.info(f"unexpected if not recovery/restart: create_update_so_in_cache called with {is_create=}, "
                             f"but md_cache has no SO for: {sym_ovrw.symbol=}, applying force update;;;{sym_ovrw=}")
            self.basket_book_cache[sym_ovrw.symbol] = BasketBookCacheContainer(tob=None, so=sym_ovrw)

    async def create_symbol_overview_pre(self, symbol_overview_obj: SymbolOverview):
        return create_symbol_overview_pre_helper(self.static_data, symbol_overview_obj)

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        self.create_update_so_in_cache(symbol_overview_obj, is_create=True)

    async def update_symbol_overview_pre(self, updated_symbol_overview_obj: SymbolOverview):
        stored_symbol_overview_obj = await (
            BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_by_id_http(
                updated_symbol_overview_obj.id))
        return update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj,
                                                 updated_symbol_overview_obj)

    async def update_symbol_overview_post(self, updated_symbol_overview_obj: SymbolOverview):
        self.create_update_so_in_cache(updated_symbol_overview_obj)

    async def partial_update_symbol_overview_pre(self, stored_symbol_overview_obj_json: Dict[str, Any],
                                                 updated_symbol_overview_obj_json: Dict[str, Any]):
        return partial_update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj_json,
                                                         updated_symbol_overview_obj_json)

    async def partial_update_symbol_overview_post(self, updated_symbol_overview_obj_json: Dict[str, Any]):
        updated_symbol_overview_obj: SymbolOverview = SymbolOverview.from_dict(updated_symbol_overview_obj_json)
        self.create_update_so_in_cache(updated_symbol_overview_obj)

    def create_update_tob_in_cache(self, tob, is_create=False):
        """
        return true if cache is complete, i.e. both tob and so are present
        """
        symbol = tob.symbol
        md_cache_cont: BasketBookCacheContainer
        if md_cache_cont := self.basket_book_cache.get(symbol):
            md_cache_cont.tob = tob
        else:
            if not is_create:
                logging.error(f"unexpected: create_update_tob_in_cache called with {is_create=}, but md_cache has no "
                              f"TOB for: {tob.symbol}, applying force update")
            self.basket_book_cache[tob.symbol] = BasketBookCacheContainer(tob=tob, so=None)

    async def create_top_of_book_pre(self, top_of_book_obj: TopOfBook):
        self.create_update_tob_in_cache(top_of_book_obj, is_create=True)

    async def update_top_of_book_post(self, updated_top_of_book_obj: TopOfBook):
        self.create_update_tob_in_cache(updated_top_of_book_obj)

    async def partial_update_top_of_book_post(self, updated_top_of_book_obj_json: Dict[str, Any]):
        updated_top_of_book_obj: TopOfBook = TopOfBook.from_dict(updated_top_of_book_obj_json)
        self.create_update_tob_in_cache(updated_top_of_book_obj)

    async def update_chore_in_db(self, chore: NewChore):
        basket_chore: BasketChore = BasketChore(id=self.basket_id, new_chores=[chore])
        basket_chore_json = basket_chore.to_dict(exclude_none=True)
        await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_basket_chore_http(
            basket_chore_json)

    @staticmethod
    def run_stop_md_for_recovered_chores(symbols: List[str]):
        symbol: str
        for symbol in symbols:
            stop_md_script_path: PurePath = CURRENT_PROJECT_DIR / "scripts" / f"stop_new_ord_{symbol}_so.sh"
            if os.path.exists(str(stop_md_script_path)):
                process: subprocess.Popen = subprocess.Popen([f"{stop_md_script_path}"])
                process.wait()
            else:
                logging.error(f"no stop_md_script found for {symbol=};;;{stop_md_script_path=}")

    async def recover_chores(self) -> bool:
        # return True
        recovered_baskets: List[BasketChore] = await (
            BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_basket_chore_http())
        if len(recovered_baskets) > 1:
            logging.error(f"invalid {len(recovered_baskets)=}, unable to process "
                          f"{len(self.managed_chores_by_symbol)=};;;{recovered_baskets=}")
            return False
        elif len(recovered_baskets) == 1:
            self.recovered_chores = recovered_baskets[0].new_chores
            if self.basket_id is None:
                self.basket_id = recovered_baskets[0].id
            else:
                logging.error(f"unsupported! Found basket_id: {recovered_baskets[0].id} in DB, whereas app "
                              f"{self.basket_id=};;;{recovered_baskets[0]=}")
            if self.recovered_chores is not None:
                recovered_chores_symbol_list = set()
                for recovered_chore in self.recovered_chores:
                    is_open, is_unack, text, filled_qty = await (
                        self.bartering_link_check_is_chore_open_n_modifiable(recovered_chore))
                    if is_open:
                        logging.info(f"added recovered chore for management: {recovered_chore}")
                        self.add_chore_to_managed_chores_by_symbol(recovered_chore.security.sec_id, recovered_chore)
                        recovered_chores_symbol_list.add(recovered_chore.security.sec_id)
                    else:
                        logging.warning(f"recovery ignoring chore {recovered_chore.security.sec_id} "
                                        f"{recovered_chore.side} {recovered_chore.chore_id} found not open on bartering "
                                        f"link: {text=};;;{recovered_chore=}")
                self.run_stop_md_for_recovered_chores(list(recovered_chores_symbol_list))
                updated_basket_chore: BasketChore = BasketChore(id=self.basket_id,
                                                                update_id=recovered_baskets[0].update_id + 1)
                await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_basket_chore_http(
                    updated_basket_chore.to_dict(exclude_none=True))
        else:
            self.recovered_chores = []
        return True

    async def trigger_or_manage_algo_chores(self):
        """
         Any chore that needs active management after posting stays in manager_chore_by_symbol, others are posted and removed
         called periodically to start with, later this can be moved to update via semaphore notification
        """
        if self.recovered_chores is None:
            try:
                is_recovered: bool = await self.recover_chores()
                if not is_recovered:
                    return  # error logged in call
            except Exception as exp:
                logging.exception(f"recover_chores failed with {exp=}")
                return

        if self.chore_limits is None:
            logging.error(f"invalid {self.chore_limits=}, unable to process {len(self.managed_chores_by_symbol)=}")
            return
        is_algo: Final[bool] = True

        # used in Amend as New store system symbol and chore for at-end addition to managed chores
        sys_symbol_n_new_submit_chore_list: List[Tuple[str, NewChore]] = []
        # used to clear closed / unmanaged chore chores
        remove_sys_symbol_list: List[str] = []

        chore_list: List[NewChore]
        for sys_symbol, chore_list in self.managed_chores_by_symbol.items():
            if chore_list is None or len(chore_list) <= 0:
                continue  # nothing to do for this symbol
            be_cached_cont: BasketBookCacheContainer | None
            be_cached_cont = self.basket_book_cache.get(sys_symbol)
            if not be_cached_cont:
                continue  # cache not ready for this symbol yet
            # if we are here - cache is ready
            tob = be_cached_cont.tob
            breach_px: float | None
            chore: NewChore
            remove_chore_list: List[NewChore] = []
            for idx, chore in enumerate(chore_list):
                if chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_DONE:
                    is_open: bool
                    is_unack: bool
                    text: str | None = None
                    if self.is_algo_market_chore(chore):
                        is_open, is_unack, text, filled_qty = await (
                            self.bartering_link_check_is_chore_open_n_modifiable(chore))
                        if not is_open:
                            chore.text = f"{chore.text}; {text}"
                            remove_chore_list.append(chore)
                            logging.info(f"removing algo market {chore.chore_id=} for {chore.security.sec_id} on "
                                         f"{chore.algo}; {filled_qty=} chore is not open anymore")
                            continue
                        if is_unack:
                            logging.info(f"ignoring algo market {chore.chore_id=} for {chore.security.sec_id} on "
                                         f"{chore.algo}; {filled_qty=} chore is not in modifiable state")
                            continue
                        # we are to manage the price [market algo] - till chore remains open and modifiable
                        if generated_px := self.generate_algo_market_chore_price(chore, be_cached_cont):
                            # if new price generated - we amend the chore
                            if self.soft_amend:
                                res = await self.bartering_link.place_cxl_chore(chore.chore_id)
                                if res:
                                    # get chore state again to get filled qty after chore is cancelled
                                    for retry_count in range(5):
                                        is_open, is_unack, text, filled_qty = await (
                                            self.bartering_link_check_is_chore_open_n_modifiable(chore))
                                        if is_open:
                                            await asyncio.sleep(1)
                                            logging.warning(f"post place_cxl_chore: chore found in non cancelled state,"
                                                            f" {retry_count=}")
                                        else:
                                            break
                                    if is_open:
                                        logging.error(f"unexpected: post place_cxl_chore: chore found in non cancelled "
                                                      f"state in spite exhausting retries, the chore will be dropped "
                                                      f"from management")
                                        continue
                                    # else all good - compute remaining qty place new chore then add it for management
                                    remaining_qty = chore.qty - filled_qty
                                    if remaining_qty > 0:
                                        usd_px = get_usd_px(generated_px, self.usd_fx)
                                        amend_as_new_ord = NewChore(
                                            security=chore.security, side=chore.side, px=generated_px, usd_px=usd_px,
                                            qty=remaining_qty, lot_size=chore.lot_size, force_bkr=chore.force_bkr,
                                            mstrat=chore.mstrat, chore_submit_state=ChoreSubmitType.ORDER_SUBMIT_FAILED,
                                            algo=chore.algo, pov=chore.pov, activate_dt=chore.activate_dt,
                                            deactivate_dt=chore.deactivate_dt,
                                            ord_entry_time=pendulum.DateTime.utcnow())
                                    else:
                                        logging.error(f"unexpected: post place_cxl_chore: chore found in {is_open=} "
                                                      f"state but with invalid {remaining_qty}, the chore will be "
                                                      f"dropped from management")
                                        continue
                                    sec_pos_extended = self.id_to_sec_pos_extended_dict[chore.id]
                                    res = await self.place_checked_new_chore(amend_as_new_ord, sec_pos_extended)
                                    await self.update_chore_in_db(amend_as_new_ord)
                                    if not res:
                                        logging.error(f"failed to send {amend_as_new_ord=}")
                                    sys_symbol_n_new_submit_chore_list.append((sys_symbol, amend_as_new_ord),)
                                else:
                                    logging.error(f"cancel for amend attempt failed! Basket {chore.chore_id=} from px: "
                                                  f"{chore.px:.3f} to generated px: {generated_px:.3f} for "
                                                  f"{chore.security.sec_id}, {chore.side}, {text=}, we'll retry in next"
                                                  f" iteration")
                                    continue
                            else:
                                res = await self.bartering_link.place_amend_chore(chore.chore_id, px=generated_px)
                            if res:
                                logging.info(f"amended {self.soft_amend=} {chore.chore_id=} from old px: {chore.px:.3f} to new px: "
                                             f"{generated_px:.3f} for {chore.security.sec_id}, {chore.side}, {text=}")
                                chore.px = generated_px if not self.soft_amend else chore.px
                            else:
                                logging.error(f"amend attempt failed! Basket {chore.chore_id=} from px: "
                                              f"{chore.px:.3f} to generated_px: {generated_px:.3f} for "
                                              f"{chore.security.sec_id}, {chore.side}, {text=}")
                                continue
                    else:
                        # meaningful support logs
                        is_open, is_unack, text, filled_qty = await (
                            self.bartering_link_check_is_chore_open_n_modifiable(chore))
                        if is_unack:
                            logging.warning(f"found non-market unack {chore.chore_id} for {chore.security.sec_id} on "
                                            f"{chore.algo}; not managing this - monitor till it remains unack, {text=},"
                                            f" {filled_qty=}")
                            continue
                        chore.text = f"{chore.text}; {text}; {filled_qty=}"  # update text - chore is getting removed
                        if not is_open:
                            logging.info(f"removing non-market {chore.chore_id} for {chore.security.sec_id} on "
                                         f"{chore.algo}; chore not in open state {chore.text=}")
                            remove_chore_list.append(chore)
                        else:
                            remove_chore_list.append(chore)
                            logging.info(f"ignoring: {chore.chore_id} for {chore.security.sec_id}, we don't "
                                         f"manager/monitor non-market, non-pending[SUBMIT-DONE], "
                                         f"non-unack algo chores - removed from manager chore list, {chore.text=}")
                elif chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_PENDING:
                    # chore is yet to go to the market
                    if chore.px is None:  # mark algo market since no price
                        self.mark_algo_chore_market(chore)
                        chore.px = self.generate_algo_market_chore_price(chore, be_cached_cont)
                        await self.check_n_place_new_chore_(chore, be_cached_cont)
                        if chore.text is not None:
                            await self.update_chore_in_db(chore)
                    else:
                        # chore has px, check if it is within the range and fire if so, otherwise re-evaluate in the
                        # next cycle and retry [refer ORDER_SUBMIT_DONE handling]
                        high_breach_px: float | None = ChoreControl.get_breach_threshold_px_ext(
                            tob, be_cached_cont.get_so, self.chore_limits, Side.BUY, chore.security.sec_id,
                            None, is_algo)
                        if high_breach_px is None:
                            continue  # error logged internally
                        # else move forward - so far all good

                        low_breach_px: float | None = ChoreControl.get_breach_threshold_px_ext(
                            tob, be_cached_cont.get_so, self.chore_limits, Side.SELL, chore.security.sec_id,
                            None, is_algo)
                        if low_breach_px is None:
                            continue  # error logged internally
                        # else move forward - so far all good

                        if high_breach_px > chore.px > low_breach_px:
                            await self.check_n_place_new_chore_(chore, be_cached_cont)
                            if chore.text is not None:
                                await self.update_chore_in_db(chore)
                        else:
                            epoch_time_in_sec = int(time.time())
                            epoch_time_by_symbol: int = self.epoch_time_by_symbol_dict.get(chore.security.sec_id, 0)
                            if epoch_time_in_sec > (epoch_time_by_symbol + 10):
                                self.epoch_time_by_symbol_dict[chore.security.sec_id] = epoch_time_in_sec
                                logging.warning(f"Basker {chore.id=}, {chore.security.sec_id}, {chore.side}, "
                                                f"{high_breach_px=:.3f} > {chore.px=:.3f} > {low_breach_px=:.3f} cond "
                                                f"not met - added to retry;;;{chore.chore_id=}")
                            # else not required - we'll retry in next attempt
                else:
                    # mark chore for removal: chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_FAILED
                    remove_chore_list.append(chore)
            for chore in remove_chore_list:
                chore_list.remove(chore)
                await self.update_chore_in_db(chore)
                if len(chore_list) == 0:  # removing symbol itself from dict - no more chores in list
                    remove_sys_symbol_list.append(sys_symbol)
        for sys_symbol in remove_sys_symbol_list:
            del self.managed_chores_by_symbol[sys_symbol]
        for sys_symbol, chore in sys_symbol_n_new_submit_chore_list:
            self.add_chore_to_managed_chores_by_symbol(sys_symbol, chore)

    async def bartering_link_check_is_chore_open_n_modifiable(self, chore: NewChore) -> \
            Tuple[bool, bool, str | None, int | None]:
        """
        check and return is_open and is_unack
        """
        is_open: bool
        is_unack: bool
        chore_status_type: ChoreStatusType
        chore_status_type, text, filled_qty = await self.bartering_link.get_chore_status(chore.chore_id)
        match chore_status_type:
            case ChoreStatusType.OE_UNACK:
                is_open = True
                is_unack = True
            case ChoreStatusType.OE_ACKED:
                is_open = True
                is_unack = False
            case ChoreStatusType.OE_DOD | ChoreStatusType.OE_FILLED:
                is_open = False
                is_unack = False
            case _:
                err_: str = (f"get_chore_status, unexpected {chore_status_type=} found for {chore.chore_id=};;;"
                             f"{chore=}")
                logging.error(err_)
                raise err_
        return is_open, is_unack, text, filled_qty

    @staticmethod
    def mark_algo_chore_market(chore: NewChore):
        if not chore.algo.endswith(BasketBookServiceRoutesCallbackBaseNativeOverride.algo_market_chore_suffix):
            chore.algo += BasketBookServiceRoutesCallbackBaseNativeOverride.algo_market_chore_suffix

    @staticmethod
    def is_algo_market_chore(chore: NewChore):
        return chore.algo and chore.algo.endswith(
            BasketBookServiceRoutesCallbackBaseNativeOverride.algo_market_chore_suffix)

    def generate_algo_market_chore_price(self, chore: NewChore,
                                         be_cache_cont: BasketBookCacheContainer) -> float | None:
        tob = be_cache_cont.tob
        tick_size = be_cache_cont.so.tick_size
        generated_px: float | None
        breach_px: float | None
        tick_size_distance_threshold: int = 100
        if tick_size is None:
            err_ = (f"unexpected {be_cache_cont.so.tick_size=} found while processing {chore.chore_id=} for "
                    f"{chore.security.sec_id};;;{chore=}; {be_cache_cont=}")
            logging.error(err_)
            return None
        # else all good - continue with rest of flow
        tick_threshold = tick_size * tick_size_distance_threshold

        breach_px = ChoreControl.get_breach_threshold_px_ext(
            tob, be_cache_cont.get_so, self.chore_limits, chore.side, chore.security.sec_id,
            None, is_algo=True)
        if breach_px is not None:
            if chore.side == Side.BUY:
                generated_px = breach_px - tick_threshold
            elif chore.side == Side.SELL:
                generated_px = breach_px + tick_threshold
            else:
                err_ = f"unexpected {chore.side=} found in {chore.chore_id=} for {chore.security.sec_id};;;{chore=}"
                logging.error(err_)
                raise Exception(err_)
        else:
            # error logged in get_breach_threshold_px_ext call
            return None
        aggressive_px = None
        passive_px = None
        generated_px_log = "Unknown"
        if chore.px is not None:
            if chore.side == Side.BUY:
                aggressive_px = tob.ask_quote.px
                passive_px = tob.bid_quote.px
                # minus of tick size (1 tick) helps prior run generated same price to fall in ignore category
                if chore.px > (aggressive_px + tick_threshold - tick_size):
                    generated_px = None
                    generated_px_str = f"{generated_px=}"
                else:
                    generated_px_str = f"{generated_px=:.3f}"
                generated_px_log = (f"{generated_px_str}, generate None cond: "
                                    f"{chore.px=:.3f} > ({aggressive_px=:.3f}[ask] + {tick_threshold=:.3f})")
            elif chore.side == Side.SELL:
                aggressive_px = tob.bid_quote.px
                passive_px = tob.ask_quote.px
                # plus of tick size (1 tick) helps prior run generated same price to fall in ignore category
                if chore.px < (aggressive_px - tick_threshold + tick_size):
                    generated_px = None
                    generated_px_str = f"{generated_px=}"
                else:
                    generated_px_str = f"{generated_px=:.3f}"
                generated_px_log = (f"{generated_px_str}, generate None cond: "
                                    f"{chore.px=:.3f} < ({aggressive_px=:.3f}[bid] - {tick_threshold=:.3f})")
            # else not required - generated_px generator block throws if any non BUY/SELL side detected
            logging.debug(f"for {chore.security.sec_id} {chore.side}, {chore.chore_id}: {generated_px_log}; "
                          f"{tick_size=:.3f}, {breach_px=:.3f};;;{chore.algo}")
        # else not required: no px: 1st handling of this chore, needs to get to market ASAP

        if (chore.px is not None) and (generated_px is not None):
            chore_px_generated_px_gap = abs(chore.px - generated_px)
            aggressive_passive_px_gap = abs(aggressive_px - passive_px)
            aggressive_px_1_percent = aggressive_px * .01
            tick_threshold_25_percent = tick_threshold / 4
            # If posted price & generated_px are more than hardcoded 1% apart:
            # - ignore chore px amend [even if that means of chore goes passive]
            # - the assumption here is MD is bad - we should have never been
            if aggressive_passive_px_gap > aggressive_px_1_percent:  # prevent bad MD
                logging.error(f"for {chore.security.sec_id} {chore.side}, {chore.chore_id} dropping {generated_px=:.3f}"
                              f" as {aggressive_passive_px_gap=:.3f} > {aggressive_px_1_percent=:.3f};;;{tob=}")
                generated_px = None
            elif chore_px_generated_px_gap < tick_threshold_25_percent:  # prevent too frequent post
                # if chore price is less than 25% tick_threshold apart
                # - ignore chore px amend [even if that means of chore goes passive]
                logging.info(f"for {chore.security.sec_id} {chore.side}, {chore.chore_id} dropping {generated_px=:3f}"
                             f" as {chore_px_generated_px_gap=:.3f} < {tick_threshold_25_percent=:.3f};;;{tob=}")
                generated_px = None
        # generated_px is good to sent to market [next periodic cycle may readjust px till chore done]
        if generated_px is not None:
            generated_px = round(generated_px, 3)
        return generated_px
