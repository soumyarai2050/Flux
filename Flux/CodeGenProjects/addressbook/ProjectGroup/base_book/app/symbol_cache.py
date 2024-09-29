import logging
from ctypes import *
import traceback
import threading
from typing import Dict, Any, List
import msgspec
from pendulum import DateTime, parse

from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import (
    TickType, MarketDepthBaseModel, SymbolNExchIdBaseModel, MarketBarterVolumeBaseModel, LastBarterBaseModel, TopOfBookBaseModel)
from Flux.CodeGenProjects.AddressBook.Pydantic.barter_core_msgspec_model import QuoteBaseModel
from Flux.CodeGenProjects.AddressBook.Pydantic.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import (
    SymbolOverviewBaseModel, SymbolOverview)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache


def convert_str_to_datetime(date_str: str) -> DateTime:
    return parse(date_str)


class ExtendedLastBarter(LastBarterBaseModel, kw_only=True):
    lock: threading.Lock = msgspec.field(default_factory=threading.Lock)

    def get_lock(self) -> threading.Lock:
        return self.lock


class ExtendedMarketDepth(MarketDepthBaseModel, kw_only=True):
    lock: threading.Lock = msgspec.field(default_factory=threading.Lock)

    def get_lock(self) -> threading.Lock:
        return self.lock


class ExtendedTopOfBook(TopOfBookBaseModel, kw_only=True):
    lock: threading.Lock = msgspec.field(default_factory=threading.Lock)

    def get_lock(self) -> threading.Lock:
        return self.lock


class SymbolCache:
    def __init__(self):
        self.top_of_book: ExtendedTopOfBook = ExtendedTopOfBook(
            id=None, symbol=None, bid_quote=QuoteBaseModel(), ask_quote=QuoteBaseModel(), last_barter=QuoteBaseModel(),
            total_bartering_security_size=None, last_update_date_time=None
        )
        self.last_barter: ExtendedLastBarter = ExtendedLastBarter(
            id=None, symbol_n_exch_id=SymbolNExchIdBaseModel(), exch_time=None, arrival_time=None,
            px=None, qty=None, premium=None, market_barter_volume=MarketBarterVolumeBaseModel()
        )
        # todo: add dynamic length of market depth list based on config
        self.bid_market_depth: List[ExtendedMarketDepth] = [] * 10
        self.ask_market_depth: List[ExtendedMarketDepth] = [] * 10
        self.so: SymbolOverview | SymbolOverviewBaseModel | None = None
        self.buy_pos_cache: PosCache | None = None
        self.sell_pos_cache: PosCache | None = None

        for i in range(10):
            self.bid_market_depth.append(ExtendedMarketDepth(id=None, px=0.0, qty=0, position=i))
            self.ask_market_depth.append(ExtendedMarketDepth(id=None, px=0.0, qty=0, position=i))

    def __str__(self):
        return (f"MobileBookContainer({str(self.top_of_book)}, {str(self.bid_market_depth)}, "
                f"{str(self.ask_market_depth)}, {str(self.last_barter)})")

    def get_top_of_book_bid_quote(self) -> QuoteBaseModel | None:
        return self.top_of_book.bid_quote

    def get_top_of_book_ask_quote(self) -> QuoteBaseModel | None:
        return self.top_of_book.ask_quote

    def get_top_of_book_last_barter(self) -> QuoteBaseModel | None:
        return self.top_of_book.last_barter

    def get_top_of_book(self, date_time: DateTime | None = None) -> ExtendedTopOfBook | None:
        if date_time is None or date_time < self.top_of_book.last_update_date_time:
            return self.top_of_book
        return None

    def get_last_barter(self) -> ExtendedLastBarter | None:
        return self.last_barter

    def remove_bid_market_depth_from_position(self, position: int) -> bool:
        self.bid_market_depth[position] = None
        return True

    def remove_ask_market_depth_from_position(self, position: int) -> bool:
        self.ask_market_depth[position] = None
        return True

    def get_bid_market_depths(self) -> List[ExtendedMarketDepth]:
        return self.bid_market_depth

    def get_ask_market_depths(self) -> List[ExtendedMarketDepth]:
        return self.ask_market_depth

    def get_bid_market_depth_from_depth(self, position: int) -> ExtendedMarketDepth | None:
        if position > 0 or position < 9:
            return self.bid_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_ask_market_depth_from_depth(self, position: int) -> ExtendedMarketDepth | None:
        if position > 0 or position < 9:
            return self.ask_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_so(self, symbol: str | None = None):  # so getter need to get breach_px
        return self.so


class SymbolNExchId(Structure):
    _fields_ = [
        ('symbol_', c_char_p), ('exch_id_', c_char_p)
    ]

    def __str__(self):
        return f"SymbolNExchId(symbol={self.symbol_}, exch_id={self.exch_id_})"


class MarketBarterVolume(Structure):
    _fields_ = [
        ('id_', c_char_p), ('participation_period_last_barter_qty_sum_', c_int64),
        ('is_participation_period_last_barter_qty_sum_set_', c_bool),
        ('applicable_period_seconds_', c_int32),
        ('is_applicable_period_seconds_set_', c_bool)
    ]

    def __str__(self):
        return (f"MarketBarterVolume(id={self.id_.decode()}, participation_period_last_barter_qty_sum_="
                f"{self.participation_period_last_barter_qty_sum_}, applicable_period_seconds_="
                f"{self.applicable_period_seconds_})")


class LastBarter(Structure):
    _fields_ = (
        ('symbol_n_exch_id_', SymbolNExchId), ('exch_time_', c_char_p),
        ('arrival_time_',  c_char_p), ('px_', c_double), ('qty_', c_int64),
        ('premium_', c_double), ('is_premium_set_', c_bool),
        ('market_barter_volume_', MarketBarterVolume), ('is_market_barter_volume_set_', c_bool)
    )

    def __str__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id_)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px_)}, qty_={str(self.qty_)}, "
                f"premium_={str(self.premium_)}, market_barter_volume_={str(self.market_barter_volume_)})")


class MarketDepth(Structure):
    _fields_ = (
        ('symbol_', c_char_p), ('exch_time_', c_char_p), ('arrival_time_', c_char_p), ('side_', c_char),
        ('px_', c_double), ('is_px_set_', c_bool), ('qty_', c_int64), ('is_qty_set_', c_bool),
        ('position_', c_int32), ('market_maker_', c_char_p), ('is_market_maker_set_', c_bool),
        ('is_smart_depth_', c_bool), ('is_is_smart_depth_set_', c_bool),
        ('cumulative_notional_', c_double), ('is_cumulative_notional_set_', c_bool),
        ('cumulative_qty_', c_int64), ('is_cumulative_qty_set_', c_bool),
        ('cumulative_avg_px_', c_double), ('is_cumulative_avg_px_set_', c_bool)
    )

    def __str__(self):
        return f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}"


last_barter_callback_type = CFUNCTYPE(c_int, POINTER(LastBarter))
market_depth_callback_type = CFUNCTYPE(c_int, POINTER(MarketDepth))


class SymbolCacheContainer:
    symbol_to_symbol_cache_dict: Dict[str, SymbolCache] = {}
    semaphore = threading.Semaphore(0)

    @staticmethod
    def release_notify_semaphore():
        SymbolCacheContainer.semaphore.release()

    @staticmethod
    def acquire_notify_semaphore():
        SymbolCacheContainer.semaphore.acquire()

    @staticmethod
    def market_depth_consumer():
        while True:
            try:
                SymbolCacheContainer.semaphore.acquire()
                for symbol_cache in SymbolCacheContainer.symbol_to_symbol_cache_dict.values():
                    for md in symbol_cache.bid_market_depth:
                        if md.lock.acquire(blocking=False):
                            try:
                                pass
                            finally:
                                md.lock.release()
                    for md in symbol_cache.ask_market_depth:
                        if md.lock.acquire(blocking=False):
                            try:
                                logging.debug(f"Consumed {md.symbol}: {md}")
                            finally:
                                md.lock.release()
            except Exception as e:
                logging.exception(f"md_consumer failed: {e}")

    @staticmethod
    def last_barter_consumer():
        while True:
            SymbolCacheContainer.semaphore.acquire()
            for symbol_cache in SymbolCacheContainer.symbol_to_symbol_cache_dict.values():
                with symbol_cache.last_barter.lock:
                    print(str(symbol_cache.last_barter))

    @staticmethod
    def market_depth_callback(mes_p):
        try:
            md = mes_p[0]
            symbol_cache: SymbolCache = SymbolCacheContainer.get_symbol_cache(md.symbol_.decode())
            mkt_depths: List[
                ExtendedMarketDepth] = symbol_cache.bid_market_depth if 'B' == md.side_.decode() else symbol_cache.ask_market_depth
            mkt_depth: ExtendedMarketDepth = mkt_depths[md.position_]
            if mkt_depth.lock.acquire(blocking=False):
                try:
                    mkt_depth.symbol = md.symbol_.decode()
                    mkt_depth.arrival_time = convert_str_to_datetime(md.arrival_time_.decode())
                    mkt_depth.exch_time = convert_str_to_datetime(md.exch_time_.decode())
                    mkt_depth.side = TickType.BID if md.side_.decode() == 'B' else TickType.ASK
                    mkt_depth.px = md.px_ if md.is_px_set_ else 0.0
                    mkt_depth.qty = md.qty_ if md.is_qty_set_ else 0
                    mkt_depth.position = md.position_
                    mkt_depth.market_maker = md.market_maker_.decode() if md.market_maker_ else ''
                    mkt_depth.is_smart_depth = md.is_smart_depth_ if md.is_is_smart_depth_set_ else False
                    mkt_depth.cumulative_notional = md.cumulative_notional_ if md.is_cumulative_notional_set_ else 0.0
                    mkt_depth.cumulative_qty = md.cumulative_qty_ = md.cumulative_qty_ if md.is_cumulative_qty_set_ else 0
                    mkt_depth.cumulative_avg_px = md.cumulative_avg_px_ if md.is_cumulative_avg_px_set_ else 0.0
                finally:
                    mkt_depth.lock.release()
                if md.position_ == 0:
                    tob: ExtendedTopOfBook = symbol_cache.top_of_book
                    tob.symbol = md.symbol_.decode()
                    if tob is not None:
                        if tob.lock.acquire(blocking=False):
                            try:
                                if md.side_.decode() == "B":
                                    if tob.bid_quote == None:
                                        tob.bid_quote = QuoteBaseModel()
                                    tob.bid_quote.px = mkt_depth.px
                                    tob.bid_quote.qty = mkt_depth.qty
                                    tob.bid_quote.last_update_date_time = mkt_depth.exch_time
                                    tob.last_update_date_time = mkt_depth.arrival_time
                                else:
                                    if tob.ask_quote == None:
                                        tob.ask_quote = QuoteBaseModel()
                                    tob.ask_quote.px = mkt_depth.px
                                    tob.ask_quote.qty = mkt_depth.qty
                                    tob.ask_quote.last_update_date_time = mkt_depth.exch_time
                                    tob.last_update_date_time = mkt_depth.arrival_time
                            except Exception as e:
                                logging.exception(f"market_depth_callback failed: {e}")
                            finally:
                                tob.lock.release()
                    else:
                        err_str: str = f"TopOfBook not found in the python cache for symbol: {md.symbol_.decode()}"
                        raise Exception(err_str)

                    SymbolCacheContainer.semaphore.release()
            else:
                logging.info(f'MD lock is busy for {md.symbol_.decode()}. level{md.position} skipping...')
        except Exception as e:
            logging.exception(f"market_depth_callback failed, {e}")

        return 0

    @staticmethod
    def last_barter_callback(mes_p):
        try:
            lt = mes_p[0]
            symbol = lt.symbol_n_exch_id_.symbol_.decode()
            symbol_cache: SymbolCache = SymbolCacheContainer.get_symbol_cache(symbol)
            last_barter: ExtendedLastBarter = symbol_cache.last_barter
            if last_barter.lock.acquire(blocking=False):
                try:
                    last_barter.symbol_n_exch_id.symbol = symbol
                    last_barter.symbol_n_exch_id.exch_id = lt.symbol_n_exch_id_.exch_id_.decode()
                    last_barter.exch_time = convert_str_to_datetime(lt.exch_time_.decode())
                    last_barter.arrival_time = convert_str_to_datetime(lt.arrival_time_.decode())
                    last_barter.px = lt.px_
                    last_barter.qty = lt.qty_
                    last_barter.premium = lt.premium_ if lt.is_premium_set_ else 0.0
                    if lt.is_market_barter_volume_set_:
                        last_barter.market_barter_volume.id = lt.market_barter_volume_.id_.decode()
                        last_barter.market_barter_volume.participation_period_last_barter_qty_sum = lt.market_barter_volume_.participation_period_last_barter_qty_sum_
                        last_barter.market_barter_volume.applicable_period_seconds = lt.market_barter_volume_.applicable_period_seconds_
                    tob: ExtendedTopOfBook = SymbolCacheContainer.get_symbol_cache(symbol).top_of_book
                    if tob is not None:
                        if tob.lock.acquire(blocking=False):
                            try:
                                tob.symbol = last_barter.symbol_n_exch_id.symbol
                                tob.last_barter.px = last_barter.px
                                tob.last_barter.qty = last_barter.qty
                                tob.last_barter.last_update_date_time = last_barter.exch_time
                                tob.last_update_date_time = last_barter.exch_time
                                if tob.market_barter_volume is None:
                                    tob.market_barter_volume = []
                                if lt.is_market_barter_volume_set_:
                                    tob.market_barter_volume.append(last_barter.market_barter_volume)
                            except Exception as e:
                                logging.exception(f"update of top of book failed in last_barter_callback: {e}")
                            finally:
                                tob.lock.release()
                    else:
                        err_str: str = f"TopOfBook not found in the python cache for symbol: {symbol}"
                        raise Exception(err_str)
                except Exception as e:
                    logging.exception(f"update of last barter failed in last_barter_callback: {e}")
                finally:
                    last_barter.lock.release()
            else:
                logging.debug("lock not found:")
            SymbolCacheContainer.semaphore.release()
        except Exception as e:
            traceback.format_exc()
        return 0

    @classmethod
    def get_symbol_cache(cls, symbol: str) -> SymbolCache | None:
        symbol_cache = cls.symbol_to_symbol_cache_dict.get(symbol)
        return symbol_cache

    @classmethod
    def add_symbol_cache_for_symbol(cls, symbol: str) -> SymbolCache:
        symbol_cache = cls.symbol_to_symbol_cache_dict.get(symbol)
        if symbol_cache is None:
            symbol_cache = SymbolCache()
            cls.symbol_to_symbol_cache_dict[symbol] = symbol_cache
            logging.debug(f'Added Container Obj for symbol: {symbol}')
            return symbol_cache
        else:
            logging.warning(f"SymbolCache for {symbol=} already exists - passing existing object to caller of "
                            "add_symbol_cache_for_symbol")
            return symbol_cache
