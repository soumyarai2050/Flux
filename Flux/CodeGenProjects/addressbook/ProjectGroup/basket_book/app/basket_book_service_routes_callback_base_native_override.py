# standard imports
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
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert, handle_refresh_configurable_data_members)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase, market)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key, get_usd_px, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager, SecurityRecord)
from FluxPythonUtils.scripts.service import Service
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    MDShellEnvData, create_md_shell_script)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_symbol_overview_from_symbol, get_objs_from_symbol)


class MobileBookContainer(MsgspecBaseModel):
    tob: TopOfBook | TopOfBookBaseModel
    so: SymbolOverview | SymbolOverviewBaseModel


class BasketBookServiceRoutesCallbackBaseNativeOverride(BasketBookServiceRoutesCallback, Service):
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    symbol_side_key_cache: ClassVar[Dict[str, bool]] = {}

    # underlying callables
    underlying_read_symbol_overview_http: Callable[[...], Any] | None = None
    underlying_read_top_of_book_http: Callable[[...], Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_partial_update_basket_chore_http: Callable[Any, Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
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
        self.md_cache: Dict[str, MobileBookContainer] = {}
        self.basket_chore_queue: Queue[BasketChore | BasketChoreOptional] = Queue()
        # processed new chore cache dict
        self.new_chore_id_cache: Dict[int, NewChore] = {}

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
            underlying_read_symbol_overview_http, underlying_read_top_of_book_http,
            underlying_get_symbol_overview_from_symbol_query_http,
            underlying_get_top_of_book_from_symbol_query_http, underlying_partial_update_basket_chore_http)
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = underlying_get_symbol_overview_from_symbol_query_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_partial_update_basket_chore_http = underlying_partial_update_basket_chore_http

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
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"basket_book_{be_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up and self.static_data is not None and self.usd_fx is not None:
                    if not self.service_ready:
                        thread = threading.Thread(target=self.handle_basket_chores, daemon=True)
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
                                    f"self.static_data init to None, unexpected!!")
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
            else:
                should_sleep = True

    def app_launch_pre(self):
        BasketBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
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

    def handle_basket_chores(self):
        while True:
            basket_chore: BasketChore | BasketChoreOptional = self.basket_chore_queue.get()  # blocking call
            run_coro = self._handle_basket_chore(basket_chore)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_new_chores failed with exception: {e}")

    async def _handle_basket_chore(self, basket_chore: BasketChore | BasketChoreOptional):
        new_chore_list = basket_chore.new_chores
        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            await self.check_n_place_new_chore(new_chore_obj)
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
        meta_symbols_n_sec_id_source_dict: Dict[str, str] = {}  # stored symbol and symbol type [RIC, SEDOL, etc.]

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
        leg2_ticker: str = self.static_data.get_underlying_eqt_ticker_from_cb_ticker(leg1_ticker)

        subscription_data: List[Tuple[str, str]] = [
            (leg1_ticker, str(sec_id_source)),
            (leg2_ticker, str(sec_id_source))
        ]
        return subscription_data

    def create_so_shell_script(self, sec_id: str, sec_id_source: SecurityIdSource, exch_id: str) -> PurePath:
        # creating run_symbol_overview.sh file
        run_symbol_overview_file_path = CURRENT_PROJECT_DIR / "scripts" / f"new_ord_sec_id_{sec_id}_so.sh"

        # TODO: both leg is required in subscription data
        subscription_data = self.get_subscription_data(sec_id, sec_id_source)

        db_name = "basket_book"
        exch_code = "SS" if exch_id == "SSE" else "SZ"
        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=be_host, port=be_port, db_name=db_name,
                           exch_code=exch_code, project_name="basket_book"))
        create_md_shell_script(md_shell_env_data, run_symbol_overview_file_path, "SO")
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        return run_symbol_overview_file_path

    @staticmethod
    def run_so_shell_script(run_symbol_overview_file_path: PurePath):
        if not os.path.exists(run_symbol_overview_file_path):
            logging.error(f"run_so_shell_script failed, file not found;;;{run_symbol_overview_file_path=}")
            return
        # so file exists, run symbol overview file
        subprocess.Popen([f"{run_symbol_overview_file_path}"])

    async def loop_till_symbol_md_data_is_present(self, symbol: str, run_symbol_overview_file_path: PurePath,
                                                  last_md_trigger_time: DateTime):
        wait_sec = config_yaml_dict.get("fetch_md_data_wait_sec")
        if wait_sec is not None:
            wait_sec = int(wait_sec)

        if wait_sec is None or (60 <= wait_sec <= 0):  # wait_sec must be not None and positive less than a min
            wait_sec = 3

        md_trigger_wait_sec = config_yaml_dict.get("md_trigger_wait_sec")
        if md_trigger_wait_sec is not None:
            md_trigger_wait_sec = int(md_trigger_wait_sec)

        if md_trigger_wait_sec is None:
            md_trigger_wait_sec = 60  # default md trigger wait

        while True:
            symbol_overview_list: List[SymbolOverview] = \
                await (BasketBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_get_symbol_overview_from_symbol_query_http(symbol))
            top_of_book_list: List[TopOfBook] = await (BasketBookServiceRoutesCallbackBaseNativeOverride.
                                                       underlying_get_top_of_book_from_symbol_query_http(symbol))

            if symbol_overview_list and top_of_book_list:
                top_of_book = top_of_book_list[0]
                symbol_overview = symbol_overview_list[0]
                self.md_cache[symbol] = MobileBookContainer(tob=top_of_book, so=symbol_overview)
                break
            else:
                # if last md trigger time elapsed (in secs) is more than md_trigger_wait_sec, re-trigger so script
                if ((current_datetime := DateTime.utcnow()) - last_md_trigger_time).seconds >= md_trigger_wait_sec:
                    self.run_so_shell_script(run_symbol_overview_file_path)
                    last_md_trigger_time = current_datetime
                # else not needed - elapsed seconds since last run is less than md_trigger_wait_sec
                time.sleep(wait_sec)

    async def get_md_data_for_symbol(self, sec_id: str, sec_id_source: SecurityIdSource) -> MobileBookContainer:
        if sec_id not in self.md_cache:
            # create and run so shell script
            exch_id: str = self.static_data.get_exchange_from_ticker(sec_id)
            run_symbol_overview_file_path: PurePath = self.create_so_shell_script(sec_id, sec_id_source, exch_id)
            self.run_so_shell_script(run_symbol_overview_file_path)
            md_so_trigger_time: DateTime = DateTime.utcnow()

            # wait for md cache to be updated with tob and symbol_overview for this symbol
            await self.loop_till_symbol_md_data_is_present(sec_id, run_symbol_overview_file_path, md_so_trigger_time)
        # else not required: md cache already exists for this symbol

        # we expect md cache to be present if reached here
        return self.md_cache.get(sec_id)

    async def check_n_place_new_chore(self, new_chore_obj: NewChore) -> None:
        new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED  # only success overwrites
        px: float = new_chore_obj.px
        qty: int = new_chore_obj.qty
        side: Side = new_chore_obj.side
        system_symbol = new_chore_obj.security.sec_id
        err_str_: str | None = None

        # explicitly set sec_id_source if not set
        if new_chore_obj.security.sec_id_source == SecurityIdSource.SEC_ID_SOURCE_UNSPECIFIED:
            new_chore_obj.security.sec_id_source = SecurityIdSource.TICKER

        # if market.is_not_uat_nor_bartering_time():
        #     err_str_ = "Block place chore - strat outside market hours"
        #     logging.error(err_str_)
        #     raise HTTPException(detail=err_str_, status_code=400)

        # block new chore if any prior unack chore exist
        if BasketBookServiceRoutesCallbackBaseNativeOverride.check_unack(system_symbol, side):
            err_str_: str = (f"past chore on {system_symbol=} is in unack state, dropping chore with {px=}, {qty=}, "
                             f"{side=}, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            new_chore_obj.text = err_str_
            logging.error(err_str_)
            return

        md_cache: MobileBookContainer = await self.get_md_data_for_symbol(
            system_symbol, new_chore_obj.security.sec_id_source)

        # set usd_px and inst_type
        usd_px: float = get_usd_px(new_chore_obj.px, self.usd_fx)
        new_chore_obj.usd_px = usd_px
        inst_type: InstrumentType
        if self.static_data.is_cb_ticker(system_symbol):
            inst_type = InstrumentType.CB
        elif self.static_data.is_eqt_ticker(system_symbol):
            inst_type = InstrumentType.EQT
        else:
            err_str_ = f"check_n_place_new_chore failed, passed {system_symbol=} and not found in EQT/CB static data"
            new_chore_obj.text = err_str_
            return
        new_chore_obj.security.inst_type = inst_type

        usd_notional: float = new_chore_obj.usd_px * new_chore_obj.qty

        bartering_symbol: str = system_symbol
        symbol_type = "SEDOL"
        account: str = "TRADING_ACCOUNT"
        exchange: str
        if new_chore_obj.algo == "NONE":
            exchange = "TRADING_EXCHANGE"
        else:
            exchange = self.cb_algo_exchange  # this is a CB Algo Chore

        kwargs = {}
        if new_chore_obj.algo != "NONE":
            if new_chore_obj.algo:
                kwargs["algo"] = new_chore_obj.algo
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
        self.set_unack(system_symbol, side)
        res, ret_id_or_err_desc = await self.bartering_link_place_new_chore(
            px, qty, side, bartering_symbol, system_symbol, symbol_type, account, exchange, **kwargs)
        # reset unack for subsequent chores to go through - this chore did fail to go through
        BasketBookServiceRoutesCallbackBaseNativeOverride.clear_unack(system_symbol, side)

        if res:
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_DONE
        new_chore_obj.text = ret_id_or_err_desc
        # update processed new_chore cache dict
        self.new_chore_id_cache[new_chore_obj.id] = new_chore_obj

    def _handle_non_cached_new_chores(self, basket_chore_obj: BasketChore | BasketChoreOptional):
        non_cached_new_chore_list: List[NewChore] = []
        new_chore_obj: NewChore
        for new_chore_obj in basket_chore_obj.new_chores:
            if self.new_chore_id_cache.get(new_chore_obj.id) is None:
                non_cached_new_chore_list.append(new_chore_obj)
                self.new_chore_id_cache[new_chore_obj.id] = new_chore_obj

        if non_cached_new_chore_list:
            self.basket_chore_queue.put(BasketChore.from_kwargs(id=basket_chore_obj.id,
                                                                new_chores=non_cached_new_chore_list))

    async def create_basket_chore_pre(self, basket_chore_obj: BasketChore):
        new_chore_list: List[NewChore] = basket_chore_obj.new_chores
        if not new_chore_list:
            logging.warning("create_basket_chore_pre failed - no new chore found")
            return

        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            # setting state to pending
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING

    async def create_basket_chore_post(self, basket_chore_obj: BasketChore):
        self._handle_non_cached_new_chores(basket_chore_obj)

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
        updated_basket_chore_obj = BasketChore.from_dict(updated_basket_chore_obj_json)
        self._handle_non_cached_new_chores(updated_basket_chore_obj)
