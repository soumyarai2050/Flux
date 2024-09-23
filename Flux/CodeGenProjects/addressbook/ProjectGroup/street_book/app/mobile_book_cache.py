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


class MobileBookContainer:
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

        for i in range(10):
            self.bid_market_depth.append(ExtendedMarketDepth())
            self.ask_market_depth.append(ExtendedMarketDepth())

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


symbol_to_container_obj_index_dict: Dict[str, int] = {}
container_obj_list_cache: List[MobileBookContainer] = []

semaphore = threading.Semaphore(0)


def release_notify_semaphore():
    semaphore.release()


def acquire_notify_semaphore():
    semaphore.acquire()


class SymbolNExchId(Structure):
    _fields_ = [
        ('symbol_', c_char_p), ('exch_id_', c_char_p)
    ]

    def __str__(self):
        return f"SymbolNExchId(symbol={self.symbol_}, exch_id={self.exch_id_})"


class MarketBarterVolume(Structure):
    _fields_ = [
        ('id_', c_char_p), ('participation_period_last_barter_qty_sum_', c_int64),
        ('applicable_period_seconds_', c_int32)
    ]

    def __str__(self):
        return (f"MarketBarterVolume(id={self.id_.decode()}, participation_period_last_barter_qty_sum_="
                f"{self.participation_period_last_barter_qty_sum_}, applicable_period_seconds_="
                f"{self.applicable_period_seconds_})")


class LastBarter(Structure):
    _fields_ = (
        ('symbol_n_exch_id_', SymbolNExchId), ('exch_time_', c_char_p),
        ('arrival_time_',  c_char_p), ('px_', c_double), ('qty_', c_int64),
        ('premium_', c_double), ('market_barter_volume_', MarketBarterVolume)
    )

    def __str__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id_)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px_)}, qty_={str(self.qty_)}, "
                f"premium_={str(self.premium_)}, market_barter_volume_={str(self.market_barter_volume_)})")


class MarketDepth(Structure):
    _fields_ = (
        ('symbol_', c_char_p), ('exch_time_', c_char_p), ('arrival_time_', c_char_p),
        ('side_', c_char), ('position_', c_int32), ('px_', c_double), ('qty_', c_int64),
        ('market_maker_', c_char_p), ('is_smart_depth_', c_bool), ('cumulative_notional_', c_double),
        ('cumulative_qty_', c_int64), ('cumulative_avg_px_', c_double)
    )

    def __str__(self):
        return f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}"


last_barter_callback_type = CFUNCTYPE(c_int, POINTER(LastBarter))
market_depth_callback_type = CFUNCTYPE(c_int, POINTER(MarketDepth))


def market_depth_consumer():
    while True:
        try:
            semaphore.acquire()
            for provider in container_obj_list_cache:
                for md in provider.bid_market_depth:
                    if md.lock.acquire(blocking=False):
                        try:
                            pass
                        finally:
                            md.lock.release()
                for md in provider.ask_market_depth:
                    if md.lock.acquire(blocking=False):
                        try:
                            logging.debug(f"Consumed {md.symbol}: {md}")
                        finally:
                            md.lock.release()
        except Exception as e:
            logging.exception(f"md_consumer failed: {e}")


def last_barter_consumer():
    while True:
        semaphore.acquire()
        for provider in list(container_obj_list_cache):
            with provider.last_barter.lock:
                print(str(provider.last_barter))


def market_depth_callback(mes_p):
    try:
        md = mes_p[0]
        md_provider: MobileBookContainer = get_mobile_book_container(md.symbol_.decode())
        mkt_depths: List[ExtendedMarketDepth] = md_provider.bid_market_depth if 'B' == md.side_.decode() else md_provider.ask_market_depth
        mkt_depth: ExtendedMarketDepth = mkt_depths[md.position_]
        if mkt_depth.lock.acquire(blocking=False):
            try:
                mkt_depth.symbol = md.symbol_.decode()
                mkt_depth.side = TickType.BID if md.side_.decode() == 'B' else TickType.ASK
                mkt_depth.exch_time = convert_str_to_datetime(md.exch_time_.decode())
                mkt_depth.arrival_time = convert_str_to_datetime(md.arrival_time_.decode())
                mkt_depth.position = md.position_
                mkt_depth.px = md.px_
                mkt_depth.qty = md.qty_
                mkt_depth.market_maker = md.market_maker_.decode()
                mkt_depth.cumulative_notional = md.cumulative_notional_
                mkt_depth.cumulative_qty = md.cumulative_qty_
                mkt_depth.is_smart_depth = md.is_smart_depth_
                mkt_depth.cumulative_avg_px = md.cumulative_avg_px_
            finally:
                mkt_depth.lock.release()
            if md.position_ == 0:
                tob: ExtendedTopOfBook = md_provider.top_of_book
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

                semaphore.release()
        else:
            logging.info(f'MD lock is busy for {md.symbol_.decode()}. level{md.position} skipping...')
    except Exception as e:
        logging.exception(f"market_depth_callback failed, {e}")

    return 0


def last_barter_callback(mes_p):
    try:
        lt = mes_p[0]
        symbol = lt.symbol_n_exch_id_.symbol_.decode()
        mobile_book_container: MobileBookContainer = get_mobile_book_container(symbol)
        last_barter: ExtendedLastBarter = mobile_book_container.last_barter
        if last_barter.lock.acquire(blocking=False):
            try:
                last_barter.symbol_n_exch_id.symbol = symbol
                last_barter.symbol_n_exch_id.exch_id = lt.symbol_n_exch_id_.exch_id_.decode()
                last_barter.exch_time = convert_str_to_datetime(lt.exch_time_.decode())
                last_barter.arrival_time = convert_str_to_datetime(lt.arrival_time_.decode())
                last_barter.px = lt.px_
                last_barter.qty = lt.qty_
                last_barter.premium = lt.premium_
                last_barter.market_barter_volume.id = lt.market_barter_volume_.id_.decode()
                last_barter.market_barter_volume.participation_period_last_barter_qty_sum = lt.market_barter_volume_.participation_period_last_barter_qty_sum_
                last_barter.market_barter_volume.applicable_period_seconds = lt.market_barter_volume_.applicable_period_seconds_
                tob: ExtendedTopOfBook = get_mobile_book_container(symbol).top_of_book
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
        semaphore.release()
    except Exception as e:
        traceback.format_exc()
    return 0


def get_mobile_book_container(symbol: str) -> MobileBookContainer | None:
    index = symbol_to_container_obj_index_dict.get(symbol)
    if index is None:
        return None
    else:
        return container_obj_list_cache[index]


def add_container_obj_for_symbol(symbol: str):
    mobile_book_container_index = symbol_to_container_obj_index_dict.get(symbol)
    if mobile_book_container_index is None:
        mobile_book_container = MobileBookContainer()
        container_obj_list_cache.append(mobile_book_container)
        index = container_obj_list_cache.index(mobile_book_container)
        symbol_to_container_obj_index_dict[symbol] = index
        logging.debug(f'Added Container Obj at index: {index} < symbol: {symbol}')
        return mobile_book_container

