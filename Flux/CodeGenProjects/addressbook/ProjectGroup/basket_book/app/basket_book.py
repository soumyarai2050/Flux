# standard imports
import asyncio
import logging
from threading import Thread, RLock
import time
import subprocess
import math
import copy
from typing import Set
from enum import auto

# 3rd party imports
from fastapi_restful.enums import StrEnum

# project imports
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase, market)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_bartering_data_manager import (
    BasketBarteringDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_cache import BasketCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key, get_usd_px, email_book_service_http_client, config_yaml_dict)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache, SecPosExtended
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    ChoreLimitsBaseModel, ChoreLimits)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import (
    ChoreControl)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    config_yaml_dict, be_host, be_port, CURRENT_PROJECT_DIR, capped_by_size_text)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecord)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book import BaseBook
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import (
    SymbolCache)
# below import is required to symbol_cache to work - SymbolCacheContainer must import from base_plan_cache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import SymbolCacheContainer
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.md_streaming_manager import MDStreamingManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


class CallerLoopReturns(StrEnum):  # used to manage loops in caller via called return's
    BREAK = auto()  # break caller loop
    CONTINUE = auto()  # continue caller loop to trigger next loop cycle
    REDO_CONTINUE = auto()  # reiterate caller loop with same data without any further processing within loop
    RESUME = auto()  # resume further processing after call as usual
    REDO_RESUME = auto()  # reiterate caller loop with same data after finishing any remaining processing within loop


class BasketBook(BaseBook):
    manage_chores_lock: RLock = RLock()
    algo_market_chore_suffix: Final[str] = "_MKT"
    symbol_side_key_cache: ClassVar[Dict[str, bool]] = {}
    symbol_has_md_data: ClassVar[Dict[str, bool]] = {}

    # Underlying Callables
    underlying_partial_update_basket_chore_http: Callable[..., Any] | None = None
    underlying_read_basket_chore_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_msgspec_routes import (
            underlying_read_basket_chore_http, underlying_partial_update_basket_chore_http)
        cls.underlying_partial_update_basket_chore_http = underlying_partial_update_basket_chore_http
        cls.underlying_read_basket_chore_http = underlying_read_basket_chore_http

    def __init__(self, basket_bartering_data_manager_: BasketBarteringDataManager, basket_cache: BasketCache):
        super().__init__(basket_bartering_data_manager_, basket_cache)
        self.max_post_cxl_chore_check_retry_count: Final[int] = 2
        self.retry_if_failed: bool = True  # TODO: override value from config if present, default True
        self.soft_amend: bool = False  # ideally read from config
        self.maintain_in_limit_price: bool = False  # ideally read from config
        self.epoch_time_by_symbol_dict: Dict[str, int] = {}
        # processed new chore cache dict
        self.id_to_sec_pos_extended_dict: Dict[int, SecPosExtended] = {}
        self.managed_chores_by_symbol: Dict[str, List[NewChore]] = {}
        self.system_symbol_type: str = "ticker"
        self.algo_exchange: str = "TRADING_EXCHANGE"
        self.usd_fx = None
        self.md_streaming_mgr: MDStreamingManager = MDStreamingManager(CURRENT_PROJECT_DIR, be_host, be_port,
                                                                       "basket_book")
        self.md_streaming_mgr.static_data = self.plan_cache.static_data
        self.sys_symbol_to_md_trigger_time_dict: Dict[str, DateTime] = {}
        self.sys_symbol_to_md_retry_count: Dict[str, int] = {}
        self.max_md_retry_count: int = 5
        self.md_trigger_wait_sec: int = parse_to_int(config_yaml_dict.get("md_trigger_wait_sec"))
        if self.md_trigger_wait_sec is None:
            self.md_trigger_wait_sec = 60
        thread: Thread = Thread(name="basket_chore_queue", target=self.handle_non_cached_basket_chore_from_queue,
                                daemon=True)
        thread.start()
        SymbolCacheContainer.release_semaphore()   # releasing it once so that if is recovery, data can be loaded
        BasketBook.initialize_underlying_http_callables()

    @property
    def derived_class_type(self):
        raise BasketBook

    @staticmethod
    def executor_trigger(basket_bartering_data_manager_: BasketBarteringDataManager, basket_cache: BasketCache):
        basket_book: BasketBook = BasketBook(basket_bartering_data_manager_, basket_cache)
        street_book_thread = Thread(target=basket_book.run, daemon=True).start()
        # block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]]
        # sedol_symbols, ric_symbols, block_bartering_symbol_side_events, mplan = basket_book.get_subscription_data()
        # listener_sedol_key = [f'{sedol_symbol}-' for sedol_symbol in sedol_symbols]
        # listener_ric_key = [f'{ric_symbol}-' for ric_symbol in ric_symbols]
        # listener_id = f"{listener_sedol_key}-{listener_ric_key}-{os.getpid()}"
        # basket_book.bartering_link.log_key = basket_cache.get_key()
        # basket_book.bartering_link.subscribe(listener_id, BasketBook.asyncio_loop, ric_filters=ric_symbols,
        #                                       sedol_filters=sedol_symbols,
        #                                       block_bartering_symbol_side_events=block_bartering_symbol_side_events,
        #                                       mplan=mplan)
        # trigger executor md start [ name to use tickers ]

        return basket_book, street_book_thread

    def get_subscription_data(self, sec_id: str, sec_id_source: SecurityIdSource):
        # currently only accepts CB ticker
        leg1_ticker: str = sec_id
        # leg2_ticker: str = self.static_data.get_underlying_eqt_ticker_from_cb_ticker(leg1_ticker)

        subscription_data: List[Tuple[str, str]] = [
            (leg1_ticker, str(sec_id_source)),
            # (leg2_ticker, str(sec_id_source))
        ]
        return subscription_data

    @staticmethod
    def check_algo_chore_limits(chore_limits: ChoreLimits | ChoreLimitsBaseModel, new_ord: NewChore | NewChoreBaseModel,
                                chore_usd_notional: float, symbol_cache: SymbolCache,
                                check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS):
        # no contact checks for algo chore
        sys_symbol = new_ord.ticker
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
        if ((InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED != new_ord.security.inst_type != InstrumentType.EQT) and
                chore_limits.max_contract_qty):
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

        # apply chore qty / chore contract qty check result
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        checks_passed_ = ChoreControl.check_px(symbol_cache.top_of_book, symbol_cache.get_so, chore_limits, new_ord.px,
                                               new_ord.usd_px, new_ord.qty, new_ord.side, sys_symbol,
                                               None, is_algo=True)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        return checks_passed

    def handle_non_cached_basket_chore_from_queue(self):
        while True:
            basket_chore: BasketChore = (
                self.plan_cache.non_cached_basket_chore_queue.get())  # blocking call
            self._handle_non_cached_basket_chore_from_queue(basket_chore)

    def _handle_non_cached_basket_chore_from_queue(self, basket_chore: BasketChore):
        new_chore_list: List[NewChore] = basket_chore.new_chores
        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            self.enrich_n_add_managed_new_chore(new_chore_obj)
        basket_chore.processing_level = 1
        run_coro = BasketBook.underlying_partial_update_basket_chore_http(
            basket_chore.to_json_dict(exclude_none=True))
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        try:
            # block for task to finish
            future.result()
        except Exception as e:
            logging.exception(f"_handle_non_cached_basket_chore_from_queue failed with exception: {e}")

    def enrich_n_add_managed_new_chore(self, new_chore_obj: NewChore) -> bool:
        """return True if enriched or False no enrichment needed"""
        is_enriched = False
        system_symbol: str = new_chore_obj.ticker
        bartering_symbol: str = new_chore_obj.security.sec_id

        if new_chore_obj.chore_submit_state is None or (
                new_chore_obj.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_DONE):
            # For recovery cases, chore state may be pending - we still change it to failed and mark pending post basic
            # validation
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_RETRY  # only success or cxl stops retry
            is_enriched = True
        px: float | None = new_chore_obj.px
        qty: int = new_chore_obj.qty
        side: Side = new_chore_obj.side
        err_str_: str | None = None
        max_error_len: Final[int] = 1024

        if new_chore_obj.security.sec_id_source not in [SecurityIdSource.RIC, SecurityIdSource.SEDOL]:
            err_str_ = (f"enrich_n_add_managed_new_chore failed! chore's {system_symbol=}, "
                        f"{bartering_symbol=} found with unsupported {new_chore_obj.security.sec_id_source=} for "
                        f"{new_chore_obj.chore_id}, expected RIC or SEDOL;;;{new_chore_obj=}")
            if len(err_str_) > max_error_len:
                err_str_ = f"Truncated err len from {len(err_str_)} to 2048: {err_str_[:max_error_len]=}"
            new_chore_obj.text = err_str_
            logging.error(err_str_)
            is_enriched = True
            return is_enriched  # chore text updated

        # block this new chore processing if any prior unack chore exist [user may resubmit another chore later]
        if self.plan_cache.check_unack(system_symbol, side):
            err_str_ = (f"past submit on symbol_side: {get_symbol_side_key([(bartering_symbol, side)])} is in unack state"
                        f", dropping chore request with {px=}, {qty=} for {new_chore_obj.chore_id};;;{new_chore_obj=}")
            err_str_ = capped_by_size_text(err_str_)
            new_chore_obj.text = err_str_
            logging.error(err_str_)
            is_enriched = True
            return is_enriched  # chore text updated

        if new_chore_obj.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_RETRY:
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING  # allow reprocessing of chore

        self.md_streaming_mgr.trigger_md_for_symbols([(system_symbol, self.system_symbol_type),])
        self.sys_symbol_to_md_trigger_time_dict[system_symbol] = DateTime.utcnow()
        # now add to managed_chores_by_symbol
        self.add_chore_to_managed_chores_by_symbol(system_symbol, new_chore_obj)
        # releasing semaphore to get added chores executed
        SymbolCacheContainer.release_semaphore()
        return is_enriched

    def add_chore_to_managed_chores_by_symbol(self, system_symbol: str, in_chore_obj: NewChore):
        with BasketBook.manage_chores_lock:
            if chore_list := self.managed_chores_by_symbol.get(system_symbol):
                chore_list.append(in_chore_obj)
            else:
                self.managed_chores_by_symbol[system_symbol] = [in_chore_obj]

    def get_symbol_cache_cont(self, system_symbol: str, side: Side | None = None) -> SymbolCache | None:
        # we expect md cache to be present if reached here
        symbol_cache: SymbolCache
        symbol_cache = SymbolCacheContainer.get_symbol_cache(system_symbol)
        if symbol_cache is None:
            warn_ = f"symbol_cache not found for symbol {system_symbol}"
            logging.warning(warn_)
            return None
        side_found: bool = False
        if side is None or Side.BUY == side:
            side_found = True
            if symbol_cache.buy_pos_cache is None:
                buy_pos_cache: PosCache = self.plan_cache.get_pos_cache(system_symbol, Side.BUY)
                symbol_cache.buy_pos_cache = buy_pos_cache
            # else not required, pos cache exist - likely for a prior chore
        if side is None or Side.SELL == side:
            side_found = True
            if symbol_cache.sell_pos_cache is None:
                sell_pos_cache: PosCache = self.plan_cache.get_pos_cache(system_symbol, Side.SELL)
                symbol_cache.sell_pos_cache = sell_pos_cache
            # else not required, pos cache exist - likely for a prior chore
        if not side_found:
            err_ = f"unsupported {side=} found for {system_symbol} in get_basket_book_cache_cont"
            logging.error(err_)
        if symbol_cache.top_of_book is None:
            logging.warning(f"symbol_cache is not ready yet, no TOB for: {system_symbol}")
            return None  # symbol_cache is not ready
        return symbol_cache

    def place_checked_new_chore(self, new_chore_obj: NewChore, sec_pos_extended: SecPosExtended) -> bool:
        """
        return True if successful, False if failed
        """
        bartering_symbol: str = sec_pos_extended.security.sec_id
        if sec_pos_extended.security.inst_type == InstrumentType.CB:
            symbol_type = "SEDOL"
        elif sec_pos_extended.security.inst_type == InstrumentType.EQT:
            symbol_type = "RIC"
        else:
            raise Exception(f"Unsupported {sec_pos_extended.security.inst_type} in {sec_pos_extended=} of "
                            f"{new_chore_obj=}")

        account: str = sec_pos_extended.bartering_account  # TRADING_ACCOUNT
        exchange: str
        if (new_chore_obj.algo is None or new_chore_obj.algo.lower() == "none" or
                sec_pos_extended.security.inst_type == InstrumentType.EQT):
            exchange = sec_pos_extended.bartering_route  # TRADING_EXCHANGE
        else:
            exchange = self.algo_exchange  # this is a CB Algo Chore

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
                if new_chore_obj.mplan is not None:
                    kwargs["mplan"] = new_chore_obj.mplan

        kwargs["sync_check"] = True

        client_ord_id: str = self.get_client_chore_id()
        # set unack for subsequent chores - this symbol to be blocked until this chore goes through
        self.plan_cache.set_unack(True, new_chore_obj.security.sec_id, new_chore_obj.side)
        res: bool
        res, ret_id_or_err_desc = BasketBook.bartering_link_place_new_chore(new_chore_obj.px, new_chore_obj.qty,
                                                                              new_chore_obj.side, bartering_symbol,
                                                                              new_chore_obj.security.sec_id, symbol_type,
                                                                              account, exchange, client_ord_id,
                                                                              **kwargs)
        # reset unack for subsequent chores to go through - this chore did fail to go through
        self.plan_cache.set_unack(False, new_chore_obj.security.sec_id, new_chore_obj.side)
        # failed or not - chore posting is done - we'll not support retry until after chore snapshot integration
        new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_DONE
        if res:
            err_, new_chore_obj.chore_id = self.get_chore_id_from_ret_id_or_err_desc(ret_id_or_err_desc)
            err_ = capped_by_size_text(err_)
            new_chore_obj.text = err_
            self.id_to_sec_pos_extended_dict[new_chore_obj.id] = sec_pos_extended
        else:
            ret_id_or_err_desc = capped_by_size_text(ret_id_or_err_desc)
            new_chore_obj.text = ret_id_or_err_desc

        if new_chore_obj.force_bkr is None:
            new_chore_obj.force_bkr = sec_pos_extended.broker
        return res

    def check_n_place_new_chore_(self, new_chore_obj: NewChore, chore_limits: ChoreLimits | ChoreLimitsBaseModel,
                                 symbol_cache: SymbolCache) -> None:
        if new_chore_obj.usd_px is None:
            new_chore_obj.usd_px = get_usd_px(new_chore_obj.px, self.usd_fx)
        usd_notional: float = new_chore_obj.usd_px * new_chore_obj.qty
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        if market.is_not_uat_nor_bartering_time():
            return
        else:
            # no contact checks
            checks_passed |= self.check_algo_chore_limits(chore_limits, new_chore_obj, usd_notional,
                                                          symbol_cache, checks_passed)

        if ChoreControl.ORDER_CONTROL_SUCCESS != checks_passed:
            # error message is already logged, update new chore text
            err_str_ = (f"internal check_algo_chore_limits failed, {checks_passed=}; "
                        f"{ChoreControl.chore_control_type_dict.get(checks_passed)};;;{new_chore_obj=}")
            err_str_ = capped_by_size_text(err_str_)
            new_chore_obj.text = err_str_
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_RETRY
            logging.error(err_str_)
            return
        # else - chore checks passed

        # we don't use extract availability list here - assumption 1 chore, maps to 1 position
        if new_chore_obj.side == Side.BUY:
            pos_cache = symbol_cache.buy_pos_cache
        elif new_chore_obj.side == Side.SELL:
            pos_cache = symbol_cache.sell_pos_cache
        else:
            err_ = (f"unsupported {new_chore_obj.side=} found for {new_chore_obj.ticker} in "
                    f"check_n_place_new_chore_;;;{new_chore_obj=}")
            logging.error(err_)
            raise Exception(err_)
        sec_pos_extended: SecPosExtended
        is_available, sec_pos_extended = pos_cache.extract_availability(new_chore_obj)
        if not is_available:
            # error logged in extract_availability
            err_str_ = "failed to extract position, retry in next iteration"
            new_chore_obj.text = err_str_
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_RETRY
            logging.error(err_str_)
            return
        else:
            logging.info(f"extracted position for {new_chore_obj=}, extracted {sec_pos_extended=}")

        res = self.place_checked_new_chore(new_chore_obj, sec_pos_extended)
        if not res:
            pos_cache.return_availability(new_chore_obj.ticker, sec_pos_extended)

    @staticmethod
    def get_chore_id_from_ret_id_or_err_desc(ret_id_or_err_desc) -> Tuple[str | None, any]:
        parts = ret_id_or_err_desc.split("---")
        match len(parts):
            case 2:
                err_ = parts[0]
                chore_id = parts[1]
            case _:
                err_ = ret_id_or_err_desc
                chore_id = None
        return err_, chore_id

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

    def bartering_link_check_is_chore_open_n_modifiable(self, chore: NewChore) -> \
            Tuple[bool, bool, str | None, int | None, float | None, int | None]:
        run_coro = self.bartering_link_check_is_chore_open_n_modifiable_(chore)
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        try:
            return future.result()
        except Exception as exp:
            logging.exception(f"bartering_link_check_is_chore_open_n_modifiable_ failed with exception: {exp}")

    @staticmethod
    async def bartering_link_check_is_chore_open_n_modifiable_(chore: NewChore) -> \
            Tuple[bool, bool, str | None, int | None, float | None, int | None]:
        """
        check and return is_open, is_unack, text, filled_qty, posted_px and posted_qty
        """
        is_open: bool
        is_unack: bool
        chore_status_type: ChoreStatusType

        # chore is not placed yet
        if chore.chore_id is None:
            if chore.chore_submit_state not in [ChoreSubmitType.ORDER_SUBMIT_RETRY,
                                                ChoreSubmitType.ORDER_SUBMIT_FAILED]:
                return True, True, None, None, None, None
            else:
                return False, False, None, None, None, None

        chore_status_tuple = await BasketBook.bartering_link.get_chore_status(chore.chore_id)
        if chore_status_tuple is None:
            return False, False, None, None, None, None
        chore_status_type, text, filled_qty, posted_px, posted_qty = chore_status_tuple

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
                raise Exception(err_)
        return is_open, is_unack, text, filled_qty, posted_px, posted_qty

    @staticmethod
    def is_market_algo_chore(chore: NewChore):
        return chore.algo and chore.algo.endswith(BasketBook.algo_market_chore_suffix)

    @classmethod
    def mark_algo_chore_market(cls, chore: NewChore):
        if not cls.is_market_algo_chore(chore):
            chore.algo += BasketBook.algo_market_chore_suffix

    def generate_algo_market_chore_price(self, chore: NewChore, chore_limits: ChoreLimits | ChoreLimitsBaseModel,
                                         symbol_cache: SymbolCache) -> float | None:
        tob = symbol_cache.top_of_book
        tick_size = symbol_cache.so.tick_size
        generated_px: float | None
        breach_px: float | None
        tick_size_distance_threshold: int = 100
        if tick_size is None:
            err_ = (f"unexpected {symbol_cache.so.tick_size=} found while processing {chore.chore_id=} for "
                    f"{chore.ticker};;;{chore=}; {symbol_cache=}")
            logging.error(err_)
            return None
        # else all good - continue with rest of flow
        tick_threshold = tick_size * tick_size_distance_threshold

        breach_px = ChoreControl.get_breach_threshold_px_ext(
            tob, symbol_cache.so, chore_limits, chore.side, chore.security.sec_id,
            None, is_algo=True)
        if breach_px is not None:
            if chore.side == Side.BUY:
                generated_px = breach_px - tick_threshold
            elif chore.side == Side.SELL:
                generated_px = breach_px + tick_threshold
            else:
                err_ = f"unexpected {chore.side=} found in {chore.chore_id=} for {chore.ticker};;;{chore=}"
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
            logging.debug(f"for {chore.ticker} {chore.side}, {chore.chore_id}: {generated_px_log}; "
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
                logging.error(f"for {chore.ticker} {chore.side}, {chore.chore_id} dropping {generated_px=:.3f}"
                              f" as {aggressive_passive_px_gap=:.3f} > {aggressive_px_1_percent=:.3f};;;{tob=}")
                generated_px = None
            elif chore_px_generated_px_gap < tick_threshold_25_percent:  # prevent too frequent post
                # if chore price is less than 25% tick_threshold apart
                # - ignore chore px amend [even if that means of chore goes passive]
                logging.info(f"for {chore.ticker} {chore.side}, {chore.chore_id} dropping {generated_px=:3f}"
                             f" as {chore_px_generated_px_gap=:.3f} < {tick_threshold_25_percent=:.3f};;;{tob=}")
                generated_px = None
        # generated_px is good to send to market [next periodic cycle may readjust px till chore done]
        if generated_px is not None:
            generated_px = round(generated_px, 3)
        return generated_px

    def update_chore_in_db_n_cache(self, chore: NewChore, processing_level: int = 1):
        run_coro = self.update_chore_in_db_n_cache_(chore, processing_level)
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        try:
            future.result()
        except Exception as exp:
            logging.exception(f"update_chore_in_db_n_cache_ failed with exception: {exp}")

    async def update_chore_in_db_n_cache_(self, chore: NewChore, processing_level: int = 1):
        # update processed new chore cache dict
        self.plan_cache.id_to_new_chore_dict[chore.id] = chore
        basket_chore: BasketChore = BasketChore(id=self.plan_cache.basket_id, new_chores=[chore],
                                                processing_level=processing_level)
        basket_chore_json = basket_chore.to_json_dict(exclude_none=True)
        await BasketBook.underlying_partial_update_basket_chore_http(basket_chore_json)

    def recover_n_reconcile(self) -> bool:
        run_coro = self.recover_n_reconcile_()
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        # block for task to finish [run as coroutine helps enable http call via asyncio, other threads use freed CPU]
        try:
            return future.result()
        except Exception as exp:
            logging.exception(f"recover_n_reconcile_ failed with exception: {exp}")
        return False

    async def recover_n_reconcile_(self) -> bool:
        # return True
        recovered_baskets: List[BasketChore] = await (
            BasketBook.underlying_read_basket_chore_http())
        if len(recovered_baskets) > 1:
            logging.error(f"invalid {len(recovered_baskets)=}, unable to process "
                          f"{len(self.managed_chores_by_symbol)=};;;{recovered_baskets=}")
            return False
        elif len(recovered_baskets) == 1:
            self.plan_cache.chores = recovered_baskets[0].new_chores
            if self.plan_cache.basket_id is None:
                self.plan_cache.basket_id = recovered_baskets[0].id
            else:
                logging.error(f"unsupported! Found basket_id: {recovered_baskets[0].id} in DB, whereas app "
                              f"{self.plan_cache.basket_id=}; recover_chores may not work as expected;;;"
                              f"{recovered_baskets[0]=}")
            if self.plan_cache.chores is not None:
                recovered_chores_symbol_n_type_list = set()
                updated_recovered_new_chores: List[NewChore] = []
                cancel_chore_list: List = []
                for recovered_chore in self.plan_cache.chores:
                    if recovered_chore.chore_submit_state in [ChoreSubmitType.ORDER_SUBMIT_FAILED,
                                                              ChoreSubmitType.ORDER_SUBMIT_NA]:
                        continue  # closed chores, no action
                    is_updated: bool = False
                    is_open, is_unack, text, filled_qty, posted_px, posted_qty = await (
                        self.bartering_link_check_is_chore_open_n_modifiable_(recovered_chore))
                    if recovered_chore.pending_cxl:
                        if is_open or is_unack:
                            cancel_chore_list.append(recovered_chore)
                        elif not is_open:
                            self.mark_chore_closed(recovered_chore)
                            is_updated = True
                        # else - chore is unack - dealt later
                    if posted_qty is not None and recovered_chore.qty != posted_qty:
                        recovered_chore.qty = posted_qty
                        is_updated = True
                    if (recovered_chore.pending_amd_qty is not None and
                            recovered_chore.pending_amd_qty == recovered_chore.qty):
                        recovered_chore.pending_amd_qty = None
                        is_updated = True

                    if posted_px is not None and not math.isclose(recovered_chore.px, posted_px):
                        recovered_chore.px = posted_px
                        is_updated = True

                    if recovered_chore.pending_amd_px is not None and math.isclose(recovered_chore.pending_amd_px,
                                                                                   recovered_chore.px):
                        recovered_chore.pending_amd_px = None
                        is_updated = True

                    if is_open or is_unack:
                        logging.info(f"added to recovered_chores_symbol_n_type_list: {recovered_chore}, {is_open}, "
                                     f"{is_unack}, {filled_qty}")
                        recovered_chores_symbol_n_type_list.add((recovered_chore.ticker, "ticker"))
                    else:
                        text = capped_by_size_text(text)
                        logging.warning(f"recovery ignoring chore {recovered_chore.ticker}, "
                                        f"{recovered_chore.security.sec_id} {recovered_chore.side} {recovered_chore.id}"
                                        f" {recovered_chore.chore_id} found not open on bartering link: {text=};;;"
                                        f"{recovered_chore=}")
                    if is_updated:
                        updated_recovered_new_chores.append(recovered_chore)
                if 0 != len(recovered_chores_symbol_n_type_list):
                    # stop MD for recovered chores, MD may still be running - step brings chores back to clean state
                    self.md_streaming_mgr.force_stop_md_for_symbols(list(recovered_chores_symbol_n_type_list))
                    for sys_symbol, _ in recovered_chores_symbol_n_type_list:
                        del self.sys_symbol_to_md_trigger_time_dict[sys_symbol]
                    # partial update forces recovery of chores from DB and applies any correction chores
                if len(updated_recovered_new_chores) == 0:
                    self.plan_cache.is_recovered_n_reconciled = True
                    partial_updated_basket_chore: BasketChore = BasketChore(
                        id=self.plan_cache.basket_id, update_id=recovered_baskets[0].update_id + 1)
                else:
                    # until self.is_recovered_n_reconciled == True, only update update_id=-1 is handled - rest
                    # throw exception in pre-call. update_id=-1 implies NO-OP in self._handle_basket_chore call.
                    # this allows for persist first as recovered / reconciled is persisted
                    partial_updated_basket_chore: BasketChore = BasketChore(
                        id=self.plan_cache.basket_id, processing_level=1, new_chores=updated_recovered_new_chores)
                    await BasketBook.underlying_partial_update_basket_chore_http(
                        partial_updated_basket_chore.to_json_dict(exclude_none=True))
                    # now allow standard basket chore processing recovered / reconciled [then process]
                    self.plan_cache.is_recovered_n_reconciled = True
                    # just new update_id is fine
                    partial_updated_basket_chore: BasketChore = BasketChore(
                        id=self.plan_cache.basket_id, processing_level=0)

                await BasketBook.underlying_partial_update_basket_chore_http(
                    partial_updated_basket_chore.to_json_dict(exclude_none=True))
                # else no change - nothing recovered has any change
        else:
            self.plan_cache.chores = []
        return True

    def check_n_place_cancel_chore(self, chore_list: List[NewChore]):
        run_coro = self.check_n_place_cancel_chore_(chore_list)
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        try:
            future.result()
        except Exception as exp:
            logging.exception(f"check_n_place_cancel_chore_ failed with exception: {exp}")

    async def check_n_place_cancel_chore_(self, chore_list: List[NewChore]):
        cancel_chore_list: List = []
        for chore in chore_list:
            if chore.pending_cxl and chore.chore_id is not None:
                cancel_chore_list.append(chore)
        if len(cancel_chore_list) > 0:
            await self.cancel_chores_on_bartering_link(cancel_chore_list)

    def check_if_amendable(self, chore, amend_chore, remove_chore_list, is_open, is_unack, text, filled_qty):
        run_coro = self.check_if_amendable_(chore, amend_chore, remove_chore_list, is_open, is_unack, text, filled_qty)
        future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
        try:
            return future.result()
        except Exception as exp:
            logging.exception(f"check_if_amendable_ failed with exception: {exp}")

    @staticmethod
    async def check_if_amendable_(chore, amend_chore, remove_chore_list, is_open, is_unack, text, filled_qty):
        if not is_open:
            chore.text = f"{chore.text}; {text}"
            chore.text = capped_by_size_text(chore.text)
            remove_chore_list.append(chore)
            err_ = (f"removing {chore.chore_id=} for {chore.ticker} {chore.security.sec_id} on {chore.algo=}; "
                    f"{filled_qty=} chore is not open anymore")
            if amend_chore is not None:
                logging.error(f"Error amend failed: {err_}, found amend chore: {amend_chore}")
            else:
                logging.info(err_)
            return False
        if is_unack:
            err_ = (f"ignoring {chore.chore_id=} for {chore.ticker} {chore.security.sec_id} on {chore.algo=}"
                    f"; {filled_qty=} chore is not in modifiable state")
            if amend_chore is not None:
                logging.warning(f"amend to be retried in next iteration: {err_}, found amend chore: {amend_chore}")
            else:
                logging.info(err_)
            return False
        return True

    @staticmethod
    def bartering_link_place_amend_chore(chore_id: str, px: float | None = None, qty: int | None = None,
                                       bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                       bartering_sec_type: str | None = None) -> bool:
        try:
            run_coro = BasketBook.bartering_link.place_amend_chore(chore_id, px=px, qty=qty,
                                                                     bartering_sec_id=bartering_sec_id,
                                                                     system_sec_id=system_sec_id,
                                                                     bartering_sec_type=bartering_sec_type)
            future = asyncio.run_coroutine_threadsafe(run_coro, BasketBook.asyncio_loop)
            # block for task to finish
            return future.result()
        except Exception as exp:
            logging.exception(f"bartering_link.place_amend_chore failed with exception: {exp}")
            return False

    def trigger_amend_chore(self, chore, amend_chore, remove_chore_list, processable_algo_market_chore,
                            symbol_cache: SymbolCache, sys_symbol_n_new_submit_chore_list, sys_symbol) -> bool:
        is_open, is_unack, text, filled_qty, posted_px, posted_qty = (
            self.bartering_link_check_is_chore_open_n_modifiable(chore))
        if not (self.check_if_amendable(chore, amend_chore, remove_chore_list, is_open, is_unack, text, filled_qty)):
            return False
        # else all good continue

        generated_px = None
        generated_qty = chore.qty
        # if we are here - chore is in modifiable state
        if amend_chore:
            if not math.isclose(amend_chore.px, chore.px):
                generated_px = amend_chore.px
            generated_qty = amend_chore.qty

        if processable_algo_market_chore:
            chore_limits_tuple = self.bartering_data_manager.bartering_cache.get_chore_limits()
            if chore_limits_tuple is not None:
                chore_limits, _ = chore_limits_tuple
                # we are to manage the price [market algo] - till chore remains open and modifiable
                generated_px = self.generate_algo_market_chore_price(chore, chore_limits, symbol_cache)
        # even if not an amend chore - if new price generated - we amend the chore
        if amend_chore or generated_px is not None:
            if self.soft_amend:
                res = self.bartering_link_place_cxl_chore(chore.chore_id, None, None, None, None)
                if res:
                    # get chore state again to get filled qty after chore is cancelled
                    for retry_count in range(self.max_post_cxl_chore_check_retry_count):
                        is_open, is_unack, text, filled_qty, posted_px, posted_qty = (
                            self.bartering_link_check_is_chore_open_n_modifiable_(chore))
                        if is_open:
                            time.sleep(1)
                            logging.warning(f"post place_cxl_chore: chore found in non-cancelled state,"
                                            f" {retry_count=}")
                        else:
                            break
                    if is_open:
                        logging.error(f"unexpected: post place_cxl_chore: chore found in non cancelled "
                                      f"state in spite exhausting retries, the chore will be dropped "
                                      f"from management")
                        return False
                    # else all good - compute remaining qty place new chore then add it for management
                    remaining_qty = generated_qty - filled_qty
                    if remaining_qty > 0:
                        px = generated_px if generated_px is not None else chore.px
                        usd_px = get_usd_px(px, self.usd_fx)
                        amend_as_new_ord = NewChore(
                            security=chore.security, side=chore.side, px=px, usd_px=usd_px,
                            qty=remaining_qty, lot_size=chore.lot_size, force_bkr=chore.force_bkr,
                            mplan=chore.mplan, chore_submit_state=ChoreSubmitType.ORDER_SUBMIT_RETRY,
                            algo=chore.algo, pov=chore.pov, activate_dt=chore.activate_dt,
                            deactivate_dt=chore.deactivate_dt,
                            ord_entry_time=pendulum.DateTime.utcnow())
                    else:
                        logging.error(f"unexpected: post place_cxl_chore: chore found {is_open=}"
                                      f" state but with invalid {remaining_qty=} computed by "
                                      f"{generated_qty=} - {filled_qty=}, the chore will be "
                                      f"dropped from management")
                        return False
                    sec_pos_extended = self.id_to_sec_pos_extended_dict[chore.id]
                    res = self.place_checked_new_chore(amend_as_new_ord, sec_pos_extended)
                    self.update_chore_in_db_n_cache(amend_as_new_ord)
                    if not res:
                        logging.error(f"failed to send {amend_as_new_ord=}")
                    else:
                        pass  # TODO AMEND Amend done
                    # amended or not: needed in managed, to be removed later after cyclic state-check
                    sys_symbol_n_new_submit_chore_list.append((sys_symbol, amend_as_new_ord))
                else:
                    text = capped_by_size_text(text)

                    logging.error(f"cancel for amend attempt failed! Basket {chore.chore_id=} from px: "
                                  f"{chore.px:.3f} to generated px: {generated_px:.3f} for {chore.ticker} "
                                  f"{chore.security.sec_id}, {chore.side}, {text=}, we'll retry in next"
                                  f" iteration")
                    return False
            else:
                res = self.bartering_link_place_amend_chore(chore_id=chore.chore_id, px=generated_px, qty=generated_qty,
                                                          bartering_sec_id=chore.security.sec_id,
                                                          system_sec_id=chore.ticker,
                                                          bartering_sec_type=chore.security.sec_id_source)
            if res:
                soft_amend_spaced_str = " " if not self.soft_amend else f" {self.soft_amend=} "
                px_amend_str = (f"from {chore.px:.3f} to new px: {generated_px:.3f}"
                                f"") if generated_px and not math.isclose(chore.px, generated_px) else ''
                qty_amend_str = (f"from {chore.qty} to new qty: {generated_qty}"
                                 f"") if generated_qty and chore.qty != generated_qty else ''
                logging.info(f"amended {soft_amend_spaced_str}{chore.chore_id=} {px_amend_str} {qty_amend_str} for "
                             f"{chore.ticker} {chore.security.sec_id}, {chore.side}, {text=}")
                if generated_px is not None:
                    chore.px = generated_px
                    if amend_chore and generated_px is not None:
                        amend_chore.px = generated_px
            else:
                logging.error(f"amend attempt failed - we'll retry! Basket {chore.chore_id=} from px: "
                              f"{chore.px:.3f} to generated px: {generated_px:.3f} for {chore.ticker} "
                              f"{chore.security.sec_id}, {chore.side}, {text=}")
                return False
        return True

    @staticmethod
    def extract_amend_chore(chore: NewChore) -> NewChore | None:
        amend_chore: NewChore | None = None
        if (chore.pending_amd_qty is not None and chore.pending_amd_qty != 0) or (
                chore.pending_amd_px is not None and not math.isclose(chore.pending_amd_px, 0)):
            amend_chore = copy.deepcopy(chore)
            if chore.pending_amd_qty is not None and chore.pending_amd_qty != 0:
                amend_chore.qty = amend_chore.pending_amd_qty
                amend_chore.pending_amd_qty = 0
            if chore.pending_amd_px is not None and not math.isclose(chore.pending_amd_px, 0):
                amend_chore.px = amend_chore.pending_amd_px
                amend_chore.pending_amd_px = 0
        return amend_chore

    @staticmethod
    def drop_dup_older_chores(chore_list):
        chore_by_id: Dict = {}
        del_chore_list: List[NewChore] = []
        for chore in chore_list:
            if chore.id in chore_by_id:
                del_chore = chore_by_id[chore.id]
                logging.warning(f"Found multiple entries of {chore.id} for {del_chore.ticker=}/"
                                f"{del_chore.security.sec_id=}, dropping older;;;"
                                f"retained {chore=}; removed {del_chore=}")
                del_chore_list.append(del_chore)
            # if or else - store the last found chore
            chore_by_id[chore.id] = chore

        for del_chore in del_chore_list:
            chore_list.remove(del_chore)

    @staticmethod
    def mark_chore_closed(chore: NewChore, posted_qty=None, filled_qty=None):
        # chore.pending_cxl = False
        if posted_qty is None and filled_qty is None:
            chore.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED
            chore.text = "internal chore cancel before sent to market"
        else:
            chore.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_NA
            chore.text = f"chore closed! {posted_qty=}, {filled_qty=}"

    @staticmethod
    async def cancel_chores_on_bartering_link(chores):
        if chores is None:
            return  # nothing to cancel
        symbol_to_cxl_chores: Set[str] = set()  # needed for stop_md_for_symbols call
        pending_cxl_tasks: List[Any] = []
        for chore in chores:
            if await BasketBook.update_bartering_link_submit_cxl_chore_task(chore, pending_cxl_tasks):
                symbol_to_cxl_chores.add(chore.ticker)
        # self.md_streaming_mgr.stop_md_for_symbols(list(symbol_to_cxl_chores))
        if 0 != len(pending_cxl_tasks):
            await BasketBook.bartering_link_submit_cxl_chore_tasks(pending_cxl_tasks, symbol_to_cxl_chores)

    @staticmethod
    async def update_bartering_link_submit_cxl_chore_task(chore, pending_cxl_tasks):
        status = False
        is_open, is_unack, text, filled_qty, posted_px, posted_qty = await (
            BasketBook.bartering_link_check_is_chore_open_n_modifiable_(chore))
        text = capped_by_size_text(text)

        if is_open or (is_unack and chore.chore_id is not None):
            logging.info(f"added chore for cancellation: {chore}")
            cxl_chore_task = asyncio.create_task(BasketBook.bartering_link.place_cxl_chore(chore.chore_id),
                                                 name=chore.chore_id)
            pending_cxl_tasks.append(cxl_chore_task)
            status = True
        elif not is_open:  # prior cancel, don't add in pending_cxl_tasks TODO: Add found_cancelled IN param & update ?
            logging.error(f"unable to cxl chore not open on bartering link: {chore.ticker} {chore.security.sec_id} "
                          f"{chore.side} {chore.id} {chore.chore_id} found unack on bartering link: {text=};;;{chore=}")
            status = True
            chore.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_NA
            chore.text = f"chore closed! {filled_qty=}"
        elif is_unack:
            logging.error(f"unable to cxl unack chore: {chore.ticker} {chore.security.sec_id} {chore.side} "
                          f"{chore.id} {chore.chore_id} found unack on bartering link: {text=};;;{chore=}")
        else:
            logging.warning(f"unable to cxl chore {chore.ticker} {chore.security.sec_id} {is_open=}, "
                            f"{is_unack=}, {chore.side}, {chore.chore_id} found not open on bartering "
                            f"link: {text=};;;{chore=}")
        return status

    @staticmethod
    async def bartering_link_submit_cxl_chore_tasks(pending_cxl_tasks, symbol_to_cxl_chores):  # : Set[str, NewChore]
        orig_pending_cxl_tasks_count = len(pending_cxl_tasks)
        timeout: float = 20.0
        while len(pending_cxl_tasks):
            try:
                # wait doesn't raise TimeoutError!
                # Futures that aren't done when timeout occurs are returned in 2nd set
                # 20 secs should be way more than enough for cancel tasks to complete
                completed_cxl_tasks, pending_cxl_tasks = \
                    await asyncio.wait(pending_cxl_tasks, return_when=asyncio.ALL_COMPLETED, timeout=timeout)
            except Exception as exp:
                logging.exception(f"dropping pending submit_cxl_chore_tasks: {len(pending_cxl_tasks)} of total: "
                                  f"{orig_pending_cxl_tasks_count} tasks; await asyncio.wait raised {exp=};;;"
                                  f"{pending_cxl_tasks}, {symbol_to_cxl_chores=}")
                break
            while completed_cxl_tasks and 0 != len(completed_cxl_tasks):
                cxl_done_task = None
                try:
                    cxl_done_task = completed_cxl_tasks.pop()
                    res = cxl_done_task.result()
                    logging.warning(f"cxl_done_task.result: {res=}")
                except Exception as exp:
                    task_name = cxl_done_task.get_name() if cxl_done_task else "cxl_done_task_is_None"
                    logging.exception('\n', f"cxl_task future returned exception within loop for: "
                                            f"{task_name=};;;{exp=}")
            if len(pending_cxl_tasks):
                logging.error(f"unexpected, submitted {orig_pending_cxl_tasks_count} cxl task, found "
                              f"{len(pending_cxl_tasks)=} post {timeout=:.1f}, going for retry")

    @staticmethod
    def handle_pending_amd_qty(chore) -> bool:
        if chore.pending_amd_qty is not None and chore.pending_amd_qty != 0:
            if chore.pending_amd_qty != chore.qty:
                logging.debug(f"internal qty amend accepted from: {chore.qty=} to {chore.pending_amd_qty=}")
                chore.qty = chore.pending_amd_qty
            chore.pending_amd_qty = 0
            return True  # DB update needed for qty [caller may set fast cycle with this indicator]
        return False  # no DB update required

    def manage_chore(self, chore, chore_limits, remove_chore_list, symbol_cache, sys_symbol_n_new_submit_chore_list,
                     sys_symbol, is_algo) -> CallerLoopReturns:
        if chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_RETRY:
            if self.retry_if_failed:
                chore.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING
        # above will allow for previous attempt failed chores to be retried
        if chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_DONE:
            is_open: bool
            is_unack: bool
            processable_algo_market_chore = self.maintain_in_limit_price and self.is_market_algo_chore(
                chore)
            amend_chore = self.extract_amend_chore(chore)
            if amend_chore is not None or processable_algo_market_chore:
                amended: bool = self.trigger_amend_chore(chore, amend_chore, remove_chore_list,
                                                         processable_algo_market_chore,
                                                         symbol_cache,
                                                         sys_symbol_n_new_submit_chore_list, sys_symbol)
                if not amended:
                    return CallerLoopReturns.CONTINUE  # no further processing for this chore, error logged in call
                else:  # amend successfully posted - reflect change in chore
                    if amend_chore:
                        chore.qty = amend_chore.qty
                        chore.px = amend_chore.px
                        chore.pending_amd_qty = 0
                        chore.pending_amd_px = 0
            else:
                # meaningful support logs
                is_open, is_unack, text, filled_qty, posted_px, posted_qty = (
                    self.bartering_link_check_is_chore_open_n_modifiable(chore))
                if is_unack:
                    logging.warning(f"found non-market unack {chore.chore_id} for {chore.ticker} "
                                    f"{chore.security.sec_id} on {chore.algo}; not managing this; monitor till "
                                    f"it remains unack, {text=}, {filled_qty=}")
                    return CallerLoopReturns.CONTINUE  # no further processing for this chore, error logged in call
                if not math.isclose(filled_qty, 0):
                    filled_qty_str = f"{filled_qty=}; "
                else:
                    filled_qty_str = ''
                # update text - chore is getting removed
                chore.text = f"{filled_qty_str}{text if text and text not in chore.text else ''} {chore.text};"
                if not is_open:
                    logging.info(f"removing non-market {chore.chore_id} for {chore.ticker} "
                                 f"{chore.security.sec_id} on {chore.algo}; chore not in open state "
                                 f"{chore.text=}")
                    if chore.chore_submit_state != ChoreSubmitType.ORDER_SUBMIT_NA:
                        self.mark_chore_closed(chore, posted_qty, filled_qty)
                        self.update_chore_in_db_n_cache(chore)
                    remove_chore_list.append(chore)
                elif not chore.pending_cxl:
                    remove_chore_list.append(chore)
                    logging.info(f"ignoring: {chore.chore_id} for {chore.ticker} {chore.security.sec_id}, "
                                 f"we don't manage/monitor non-market, non-pending[SUBMIT-DONE] or pending_cxl,"
                                 f" non-unack algo chores; removed from managed chore list, {chore.text=}")
        elif chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_PENDING:
            # chore is yet to go to the market
            if chore.pending_cxl:
                logging.info(f"removing market-unsent {chore.id} for {chore.ticker} "
                             f"{chore.security.sec_id} on {chore.algo}; chore has {chore.pending_cxl=} set;;;"
                             f"{chore.text=}")
                self.mark_chore_closed(chore)
                self.update_chore_in_db_n_cache(chore)
                remove_chore_list.append(chore)
                return CallerLoopReturns.CONTINUE  # no further processing for this chore, more info logged in call
            if self.is_market_algo_chore(
                    chore):  # was tried before, but it's a market chore, we reprice & send
                chore.usd_px = None
                chore.px = None
                # TODO : Market To Limit Conversion if User Set Explicit Price Found in pending_amd_px
            if chore.px is None:  # mark algo market since no price
                self.mark_algo_chore_market(chore)
                if chore.pending_amd_px is not None and not math.isclose(chore.pending_amd_px, 0):
                    logging.debug(
                        f"internal px amend accepted from: {chore.px=} to {chore.pending_amd_px=}")
                    chore.px = chore.pending_amd_px
                    chore.pending_amd_px = 0
                else:
                    chore.px = self.generate_algo_market_chore_price(chore, chore_limits, symbol_cache)
                if chore.px is not None:
                    _ = self.handle_pending_amd_qty(chore)
                    if chore.pending_amd_qty is not None and chore.pending_amd_qty != 0:
                        if chore.pending_amd_qty != chore.qty:
                            logging.debug(f"internal qty amend accepted from: {chore.qty=} to "
                                          f"{chore.pending_amd_qty=}")
                            chore.qty = chore.pending_amd_qty
                        chore.pending_amd_qty = 0
                    self.check_n_place_new_chore_(chore, chore_limits, symbol_cache)
                else:
                    logging.warning(f"generate_algo_market_chore_price returned invalid {chore.px=} for "
                                    f"{chore.ticker};;;{chore=}")
                if chore.text is not None:
                    self.update_chore_in_db_n_cache(chore)
            else:
                # chore has px, check if it is within the range and fire if so, otherwise re-evaluate in the
                # next cycle and retry [refer ORDER_SUBMIT_DONE handling]
                if self.handle_pending_amd_qty(chore):
                    self.update_chore_in_db_n_cache(chore)
                    # handle more in next cycle
                    # DO NOT ALTER any parameter besides chore to avoid side effect due to dup additions for REDO_CONTINUE return
                    return CallerLoopReturns.REDO_CONTINUE  # other parts of chore management in next cycle

                if chore.pending_amd_px is not None and not math.isclose(chore.pending_amd_px, 0):
                    if not math.isclose(chore.pending_amd_px, chore.px):
                        logging.debug(
                            f"internal px amend accepted from: {chore.px=} to {chore.pending_amd_px=}")
                        chore.px = chore.pending_amd_px
                    chore.pending_amd_px = 0
                    self.update_chore_in_db_n_cache(chore)
                    # handle more in next cycle
                    # DO NOT ALTER any parameter besides chore to avoid side effect due to dup additions for REDO_CONTINUE return
                    return CallerLoopReturns.REDO_CONTINUE  # other parts of chore management in next cycle
                tob = symbol_cache.top_of_book
                high_breach_px: float | None = ChoreControl.get_breach_threshold_px_ext(
                    tob, symbol_cache.so, chore_limits, Side.BUY, chore.ticker,
                    None, is_algo)
                if high_breach_px is None:
                    return CallerLoopReturns.CONTINUE  # no further processing for this chore, more info logged in call
                # else move forward - so far all good

                low_breach_px: float | None = ChoreControl.get_breach_threshold_px_ext(
                    tob, symbol_cache.so, chore_limits, Side.SELL, chore.ticker,
                    None, is_algo)
                if low_breach_px is None:
                    return CallerLoopReturns.CONTINUE  # no further processing for this chore, more info logged in call
                # else move forward - so far all good

                if high_breach_px > chore.px > low_breach_px:
                    self.check_n_place_new_chore_(chore, chore_limits, symbol_cache)
                    if chore.text is not None:
                        self.update_chore_in_db_n_cache(chore)
                else:
                    epoch_time_in_sec = int(time.time())
                    epoch_time_by_symbol: int = self.epoch_time_by_symbol_dict.get(chore.ticker, 0)
                    if epoch_time_in_sec > (epoch_time_by_symbol + 10):
                        self.epoch_time_by_symbol_dict[chore.ticker] = epoch_time_in_sec
                        logging.warning(f"Basket {chore.id=}, {chore.ticker}, {chore.side}, "
                                        f"{high_breach_px=:.3f} > {chore.px=:.3f} > {low_breach_px=:.3f} cond "
                                        f"not met - added to retry;;;{chore.chore_id=}")
                    # else not required - we'll retry in next attempt
        elif chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_NA:  # chore is closed
            remove_chore_list.append(chore)
        # else not required, chore.chore_submit_state == ChoreSubmitType.ORDER_SUBMIT_RETRY are to be retried

    def trigger_or_manage_algo_chores(self) -> bool:
        """
        Any chore that needs active management after posting stays in managed_chores_by_symbol, others are posted and
        removed called periodically to start with, later this can be moved to update via semaphore notification
        return True if we want next cycle to be normal - False if next cycle needs to be fast
        """
        next_cycle_not_fast: bool = True
        if self.plan_cache.chores is None:
            try:
                if not self.plan_cache.is_recovered_n_reconciled:  # recovery will be retried until its successful
                    self.plan_cache.is_recovered_n_reconciled = self.recover_n_reconcile()
                    return False  # next_cycle_not_fast False : next cycle be fast
            except Exception as exp:
                logging.exception(f"recover_n_reconcile failed with {exp=}")
                return next_cycle_not_fast

        # checking and setting usd_fx if not exists
        self.get_usd_fx()

        chore_limits: ChoreLimitsBaseModel
        chore_limits_tuple = self.bartering_data_manager.bartering_cache.get_chore_limits()
        if chore_limits_tuple:
            chore_limits, _ = chore_limits_tuple
            if chore_limits is None:
                logging.error(f"Can't proceed: chore_limits/plan_limit not found for bartering_cache: "
                              f"{self.bartering_data_manager.bartering_cache}; {self.plan_cache=}")
                return next_cycle_not_fast
        else:
            logging.error(f"chore_limits_tuple not found for plan: {self.plan_cache}, can't proceed")
            return next_cycle_not_fast

        is_algo: Final[bool] = True
        # used in Amend as New store system symbol and chore for at-end addition to managed chores
        sys_symbol_n_new_submit_chore_list: List[Tuple[str, NewChore]] = []
        # used to clear closed / unmanaged chore chores
        remove_sys_sym_n_type_list: List[Tuple[str, str]] = []
        restart_sys_sym_n_type_list: List[Tuple[str, str]] = []
        ord_delayed_compare_time = pendulum.DateTime.utcnow() - pendulum.duration(seconds=60)
        chore_list: List[NewChore]
        with BasketBook.manage_chores_lock:
            for sys_symbol, chore_list in self.managed_chores_by_symbol.items():
                if chore_list is None or len(chore_list) <= 0:
                    remove_sys_sym_n_type_list.append((sys_symbol, self.system_symbol_type))
                    continue  # nothing to do for this symbol
                self.drop_dup_older_chores(chore_list)  # retain the latest change - drop all else
                self.check_n_place_cancel_chore(chore_list)
                symbol_cache: SymbolCache | None
                symbol_cache = self.get_symbol_cache_cont(sys_symbol)
                if symbol_cache is None or symbol_cache.so is None:
                    delayed_chore_list = [chore for chore in chore_list if
                                          chore.ord_entry_time < ord_delayed_compare_time]
                    if delayed_chore_list is None or 0 == len(delayed_chore_list):
                        pass
                    else:
                        md_retry_count: int | None = self.sys_symbol_to_md_retry_count.get(sys_symbol)
                        if md_retry_count is None:
                            md_retry_count = 0
                            self.sys_symbol_to_md_retry_count[sys_symbol] = 0
                        if md_retry_count > self.max_md_retry_count:
                            logging.error(f"None or missing so in {symbol_cache=} for chores triggered over 120 sec ago"
                                          f" for {sys_symbol=} - re-trigger market data failed; "
                                          f"{self.max_md_retry_count=} exceeded")
                        else:
                            md_trigger_time: DateTime | None = self.sys_symbol_to_md_trigger_time_dict.get(sys_symbol)
                            md_elapsed_duration: int | None = None
                            if md_trigger_time is not None:
                                md_elapsed_duration = (DateTime.utcnow() - md_trigger_time).seconds
                            # else - md not running for symbol
                            if md_elapsed_duration is None or md_elapsed_duration > self.md_trigger_wait_sec:
                                md_retry_count += 1
                                self.sys_symbol_to_md_retry_count[sys_symbol] = md_retry_count
                                restart_sys_sym_n_type_list.append((sys_symbol, self.system_symbol_type))
                                logging.error(f"None or missing so in {symbol_cache=} for chores triggered over 120 "
                                              f"sec ago for {sys_symbol=} - adding for re-trigger market data; "
                                              f"{md_elapsed_duration=}, {md_retry_count=}")
                            else:
                                logging.debug(f"ignored re-trigger market data for {sys_symbol=}, "
                                              f"{md_elapsed_duration=} < {self.md_trigger_wait_sec=}")

                    if self.is_stabilization_period_past() and self.market.is_uat_or_bartering_time():
                        next_cycle_not_fast = False  # check again quicker - till the cache is ready
                    continue  # cache not ready for this symbol yet

                # if we are here - cache is ready
                chore: NewChore
                remove_chore_list: List[NewChore] = []
                # now chore list is clean to process
                for idx, chore in enumerate(chore_list):
                    ret = CallerLoopReturns.REDO_CONTINUE
                    while ret == CallerLoopReturns.REDO_CONTINUE:
                        ret = self.manage_chore(chore, chore_limits, remove_chore_list, symbol_cache,
                                                sys_symbol_n_new_submit_chore_list, sys_symbol, is_algo)

                for chore in remove_chore_list:
                    chore_list.remove(chore)  # chore list is from managed_chores_by_symbol: remove is impacting that
                    self.update_chore_in_db_n_cache(chore)
                    if len(chore_list) == 0:  # removing symbol itself from dict - no more chores in list
                        remove_sys_sym_n_type_list.append((sys_symbol, self.system_symbol_type))

            # dropping symbol altogether - stop corresponding market data and delete it from managed_chores_by_symbol
            if len(remove_sys_sym_n_type_list) > 0:
                self.md_streaming_mgr.force_stop_md_for_symbols(remove_sys_sym_n_type_list)
            if len(restart_sys_sym_n_type_list) > 0:
                self.md_streaming_mgr.restart_md_for_symbols(restart_sys_sym_n_type_list)
                for sys_symbol, _ in restart_sys_sym_n_type_list:
                    self.sys_symbol_to_md_trigger_time_dict[sys_symbol] = DateTime.utcnow()
            for sys_symbol, _ in remove_sys_sym_n_type_list:
                del self.managed_chores_by_symbol[sys_symbol]
                del self.sys_symbol_to_md_trigger_time_dict[sys_symbol]
            if len(remove_sys_sym_n_type_list) > 0:
                logging.warning(f"dropped symbols from management and stopped corresponding market data: "
                                f"{remove_sys_sym_n_type_list}")

            for sys_symbol, chore in sys_symbol_n_new_submit_chore_list:
                self.add_chore_to_managed_chores_by_symbol(sys_symbol, chore)

            return next_cycle_not_fast

    def run(self):
        while True:
            SymbolCacheContainer.semaphore.acquire()
            logging.debug("basket_book signaled")

            self.trigger_or_manage_algo_chores()
