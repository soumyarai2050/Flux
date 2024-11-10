import logging
from ctypes import *
import threading
from typing import Dict, Any, List, ClassVar, Tuple, Final
import pendulum
from pendulum import DateTime, parse

from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import (
    TickType, TopOfBookBaseModel)
from Flux.CodeGenProjects.AddressBook.Pydantic.barter_core_msgspec_model import QuoteBaseModel
from Flux.CodeGenProjects.AddressBook.Pydantic.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import (
    SymbolOverviewBaseModel, SymbolOverview)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from FluxPythonUtils.scripts.pthread_shm_mutex import pthread_mutex_t, PThreadShmMutex


def convert_str_to_datetime(date_str: str) -> DateTime:
    return parse(date_str)


MAX_STRING_LENGTH: Final[int] = 128


class SymbolCacheShadowFields:
    def __init__(self):
        self.original_val: bytes | None = None
        self.manufactured_val: Any = None


class SymbolCacheShadowClass:
    symbol1: ClassVar[str | None] = None
    exch_id1: ClassVar[str | None] = None
    leg1_bid_market_depth_list: ClassVar[List[Tuple[SymbolCacheShadowFields, SymbolCacheShadowFields]]] = [(SymbolCacheShadowFields(), SymbolCacheShadowFields())]*10
    leg1_ask_market_depth_list: ClassVar[List[Tuple[SymbolCacheShadowFields, SymbolCacheShadowFields]]] = [(SymbolCacheShadowFields(), SymbolCacheShadowFields())]*10
    leg1_tob_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg1_bid_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg1_ask_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg1_last_barter_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg1_last_barter_exch_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg1_last_barter_arrival_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()

    symbol2: ClassVar[str | None] = None
    exch_id2: ClassVar[str | None] = None
    leg2_bid_market_depth_list: ClassVar[List[Tuple[SymbolCacheShadowFields, SymbolCacheShadowFields]]] = [(
                                                                                                           SymbolCacheShadowFields(),
                                                                                                           SymbolCacheShadowFields())] * 10
    leg2_ask_market_depth_list: ClassVar[List[Tuple[SymbolCacheShadowFields, SymbolCacheShadowFields]]] = [(
                                                                                                           SymbolCacheShadowFields(),
                                                                                                           SymbolCacheShadowFields())] * 10
    leg2_tob_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg2_bid_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg2_ask_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg2_last_barter_quote_last_update_date_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg2_last_barter_exch_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()
    leg2_last_barter_arrival_time: ClassVar[SymbolCacheShadowFields] = SymbolCacheShadowFields()


class MarketBarterVolume(Structure):
    _fields_ = [
        ('id_', c_char * MAX_STRING_LENGTH), ('participation_period_last_barter_qty_sum_', c_int64),
        ('is_participation_period_last_barter_qty_sum_set_', c_bool),
        ('applicable_period_seconds_', c_int32),
        ('is_applicable_period_seconds_set_', c_bool)
    ]

    def __str__(self):
        return (f"MarketBarterVolume(id={self.id_.decode()}, participation_period_last_barter_qty_sum_="
                f"{self.participation_period_last_barter_qty_sum_}, applicable_period_seconds_="
                f"{self.applicable_period_seconds_})")

    def __repr__(self):
        return (f"MarketBarterVolume(id={self.id_.decode()}, participation_period_last_barter_qty_sum_="
                f"{self.participation_period_last_barter_qty_sum_}, applicable_period_seconds_="
                f"{self.applicable_period_seconds_})")

    @property
    def id(self):
        return self.id_.decode()

    @property
    def participation_period_last_barter_qty_sum(self):
        if self.is_participation_period_last_barter_qty_sum_set_:
            return self.participation_period_last_barter_qty_sum_
        return None

    @property
    def applicable_period_seconds_(self):
        if self.is_applicable_period_seconds_set_:
            return self.applicable_period_seconds_
        return None


############### LEG1 Structures ###############

class SymbolNExchId1(Structure):
    _fields_ = [
        ('symbol_', c_char * MAX_STRING_LENGTH), ('exch_id_', c_char * MAX_STRING_LENGTH)
    ]

    def __str__(self):
        return f"SymbolNExchId(symbol={self.symbol_}, exch_id={self.exch_id_})"

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol1 is None:
            SymbolCacheShadowClass.symbol1 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol1

    @property
    def exch_id(self):
        if SymbolCacheShadowClass.exch_id1 is None:
            SymbolCacheShadowClass.exch_id1 = self.exch_id_.decode()
        return SymbolCacheShadowClass.exch_id1


class LastBarter1(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_n_exch_id', SymbolNExchId1), ('exch_time_', c_char * MAX_STRING_LENGTH),
        ('arrival_time_',  c_char * MAX_STRING_LENGTH), ('px', c_double), ('qty', c_int64),
        ('premium_', c_double), ('is_premium_set_', c_bool),
        ('market_barter_volume_', MarketBarterVolume), ('is_market_barter_volume_set_', c_bool)
    )

    def __str__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px)}, qty_={str(self.qty)}, "
                f"premium_={str(self.premium)}, market_barter_volume_={str(self.market_barter_volume)})")

    def __repr__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px)}, qty_={str(self.qty)}, "
                f"premium_={str(self.premium)}, market_barter_volume_={str(self.market_barter_volume)})")

    @property
    def exch_time(self):
        if self.exch_time_ != SymbolCacheShadowClass.leg1_last_barter_exch_time.original_val:
            SymbolCacheShadowClass.leg1_last_barter_exch_time.original_val = self.exch_time_
            SymbolCacheShadowClass.leg1_last_barter_exch_time.manufactured_val = pendulum.parse(self.exch_time_.decode())
        return SymbolCacheShadowClass.leg1_last_barter_exch_time.manufactured_val

    @property
    def arrival_time(self):
        if self.arrival_time_ != SymbolCacheShadowClass.leg1_last_barter_arrival_time.original_val:
            SymbolCacheShadowClass.leg1_last_barter_arrival_time.original_val = self.arrival_time_
            SymbolCacheShadowClass.leg1_last_barter_arrival_time.manufactured_val = pendulum.parse(self.arrival_time_.decode())
        return SymbolCacheShadowClass.leg1_last_barter_arrival_time.manufactured_val

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def market_barter_volume(self):
        if self.is_market_barter_volume_set_:
            return self.market_barter_volume_
        return None


class BidQuote1(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg1_bid_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg1_bid_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg1_bid_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg1_bid_quote_last_update_date_time.manufactured_val
        return None


class AskQuote1(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg1_ask_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg1_ask_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg1_ask_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg1_ask_quote_last_update_date_time.manufactured_val
        return None


class LastBarterQuote1(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg1_last_barter_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg1_last_barter_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg1_last_barter_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg1_last_barter_quote_last_update_date_time.manufactured_val
        return None


class TopOfBook1(Structure):
    _fields_ = [
        ("id", c_int32),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("bid_quote_", BidQuote1),
        ("is_bid_quote_set_", c_bool),
        ("ask_quote_", AskQuote1),
        ("is_ask_quote_set_", c_bool),
        ("last_barter_", LastBarterQuote1),
        ("is_last_barter_set_", c_bool),
        ("total_bartering_security_size_", c_int64),
        ("is_total_bartering_security_size_set_", c_bool),
        ("market_barter_volume_", MarketBarterVolume),
        ("is_market_barter_volume_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"TOB: symbol={self.symbol_}, {str(self.bid_quote_)=}, {self.is_bid_quote_set_=}, "
                f"{str(self.ask_quote_)=}, {self.is_ask_quote_set_=}, "
                f"{str(self.last_barter_)=}, {self.is_last_barter_set_=}, "
                f"{self.total_bartering_security_size_=}, {self.last_update_date_time_=}, "
                f"{self.is_last_update_date_time_set_=}")

    def __repr__(self):
        return (f"TOB: symbol={self.symbol_}, {str(self.bid_quote_)=}, {self.is_bid_quote_set_=}, "
                f"{str(self.ask_quote_)=}, {self.is_ask_quote_set_=}, "
                f"{str(self.last_barter_)=}, {self.is_last_barter_set_=}, "
                f"{self.total_bartering_security_size_=}, {self.last_update_date_time_=}, "
                f"{self.is_last_update_date_time_set_=}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol1 is None:
            SymbolCacheShadowClass.symbol1 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol1

    @property
    def bid_quote(self):
        if self.is_bid_quote_set_:
            return self.bid_quote_
        return None

    @property
    def ask_quote(self):
        if self.is_ask_quote_set_:
            return self.ask_quote_
        return None

    @property
    def last_barter(self):
        if self.is_last_barter_set_:
            return self.last_barter_
        return None

    @property
    def total_bartering_security_size(self):
        if self.is_total_bartering_security_size_set_:
            return self.total_bartering_security_size_

    @property
    def market_barter_volume(self):
        if self.is_market_barter_volume_set_:
            return self.market_barter_volume_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg1_tob_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg1_tob_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg1_tob_last_update_date_time.manufactured_val = pendulum.parse(self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg1_tob_last_update_date_time.manufactured_val
        return None


class MarketDepth1(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_', c_char * MAX_STRING_LENGTH), ('exch_time_', c_char * MAX_STRING_LENGTH),
        ('arrival_time_', c_char * MAX_STRING_LENGTH), ('side_', c_char),
        ('px_', c_double), ('is_px_set_', c_bool), ('qty_', c_int64), ('is_qty_set_', c_bool),
        ('position', c_int32), ('market_maker_', c_char * MAX_STRING_LENGTH), ('is_market_maker_set_', c_bool),
        ('is_smart_depth_', c_bool), ('is_is_smart_depth_set_', c_bool),
        ('cumulative_notional_', c_double), ('is_cumulative_notional_set_', c_bool),
        ('cumulative_qty_', c_int64), ('is_cumulative_qty_set_', c_bool),
        ('cumulative_avg_px_', c_double), ('is_cumulative_avg_px_set_', c_bool)
    )

    def __str__(self):
        return (f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}, "
                f"position={self.position}")

    def __repr__(self):
        return (f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}, "
                f"position={self.position}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol1 is None:
            SymbolCacheShadowClass.symbol1 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol1

    @property
    def side(self):
        if self.side_ == b"B":
            return TickType.BID
        else:
            return TickType.ASK

    @property
    def exch_time(self):
        if self.side == TickType.BID:
            cached_exch_time = SymbolCacheShadowClass.leg1_bid_market_depth_list[self.position][0]
        else:
            cached_exch_time = SymbolCacheShadowClass.leg1_ask_market_depth_list[self.position][0]
        if cached_exch_time.original_val != self.exch_time_:
            cached_exch_time.original_val = self.exch_time_
            cached_exch_time.manufactured_val = pendulum.parse(self.exch_time_.decode())
        return cached_exch_time.manufactured_val

    @property
    def arrival_time(self):
        if self.side == TickType.BID:
            cached_arrival_time = SymbolCacheShadowClass.leg1_bid_market_depth_list[self.position][1]
        else:
            cached_arrival_time = SymbolCacheShadowClass.leg1_ask_market_depth_list[self.position][1]
        if cached_arrival_time.original_val != self.exch_time_:
            cached_arrival_time.original_val = self.exch_time_
            cached_arrival_time.manufactured_val = pendulum.parse(self.arrival_time_.decode())
        return cached_arrival_time.manufactured_val

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None


class MDSharedMemory1(Structure):
    _fields_ = [
        ("update_counter", c_int64),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("last_barter", LastBarter1),
        ("top_of_book", TopOfBook1),
        ("bid_market_depth_list", MarketDepth1 * 10),
        ("ask_market_depth_list", MarketDepth1 * 10)
    ]

    def __str__(self):
        return (f"{self.symbol_=}, {str(self.last_barter)=}, {str(self.top_of_book)=}, "
                f"{[str(md) for md in self.bid_market_depth_list]}, {[str(md) for md in self.ask_market_depth_list]}, "
                f"{str(self.last_barter_last_update_date_time)=}, {str(self.top_of_book_last_update_date_time)=}, "
                f"{[str(md) for md in self.bid_market_depth_last_update_date_times_list]}, "
                f"{[str(md) for md in self.bid_market_depth_last_update_date_times_list]}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol1 is None:
            SymbolCacheShadowClass.symbol1 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol1


############### LEG2 Structures ###############


class SymbolNExchId2(Structure):
    _fields_ = [
        ('symbol_', c_char * MAX_STRING_LENGTH), ('exch_id_', c_char * MAX_STRING_LENGTH)
    ]

    def __str__(self):
        return f"SymbolNExchId(symbol={self.symbol_}, exch_id={self.exch_id_})"

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol2 is None:
            SymbolCacheShadowClass.symbol2 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol2

    @property
    def exch_id(self):
        if SymbolCacheShadowClass.exch_id2 is None:
            SymbolCacheShadowClass.exch_id2 = self.exch_id_.decode()
        return SymbolCacheShadowClass.exch_id2


class LastBarter2(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_n_exch_id', SymbolNExchId2), ('exch_time_', c_char * MAX_STRING_LENGTH),
        ('arrival_time_',  c_char * MAX_STRING_LENGTH), ('px', c_double), ('qty', c_int64),
        ('premium_', c_double), ('is_premium_set_', c_bool),
        ('market_barter_volume_', MarketBarterVolume), ('is_market_barter_volume_set_', c_bool)
    )

    def __str__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px)}, qty_={str(self.qty)}, "
                f"premium_={str(self.premium)}, market_barter_volume_={str(self.market_barter_volume)})")

    def __repr__(self):
        return (f"LastBarter(symbol_n_exch_id={str(self.symbol_n_exch_id)}, exch_time_={str(self.exch_time_)}, "
                f"arrival_time_={str(self.arrival_time_)}, px_={str(self.px)}, qty_={str(self.qty)}, "
                f"premium_={str(self.premium)}, market_barter_volume_={str(self.market_barter_volume)})")

    @property
    def exch_time(self):
        if self.exch_time_ != SymbolCacheShadowClass.leg2_last_barter_exch_time.original_val:
            SymbolCacheShadowClass.leg2_last_barter_exch_time.original_val = self.exch_time_
            logging.info(f"!!!!!!!!!!!!! {self.exch_time_}")
            SymbolCacheShadowClass.leg2_last_barter_exch_time.manufactured_val = pendulum.parse(self.exch_time_.decode())
        return SymbolCacheShadowClass.leg2_last_barter_exch_time.manufactured_val

    @property
    def arrival_time(self):
        if self.arrival_time_ != SymbolCacheShadowClass.leg2_last_barter_arrival_time.original_val:
            SymbolCacheShadowClass.leg2_last_barter_arrival_time.original_val = self.arrival_time_
            SymbolCacheShadowClass.leg2_last_barter_arrival_time.manufactured_val = pendulum.parse(self.arrival_time_.decode())
        return SymbolCacheShadowClass.leg2_last_barter_arrival_time.manufactured_val

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def market_barter_volume(self):
        if self.is_market_barter_volume_set_:
            return self.market_barter_volume_
        return None


class BidQuote2(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg2_bid_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg2_bid_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg2_bid_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg2_bid_quote_last_update_date_time.manufactured_val
        return None


class AskQuote2(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg2_ask_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg2_ask_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg2_ask_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg2_ask_quote_last_update_date_time.manufactured_val
        return None


class LastBarterQuote2(Structure):
    _fields_ = [
        ("px_", c_double),
        ("is_px_set_", c_bool),
        ("qty_", c_int64),
        ("is_qty_set_", c_bool),
        ("premium_", c_double),
        ("is_premium_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"Quote: {self.px_=}, {self.is_px_set_=}, {self.qty_=}, {self.is_qty_set_=}, "
                f"{self.premium_=}, {self.is_premium_set_=},"
                f"{self.last_update_date_time_=}, {self.is_last_update_date_time_set_=}")

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None

    @property
    def premium(self):
        if self.is_premium_set_:
            return self.premium_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg2_last_barter_quote_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg2_last_barter_quote_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg2_last_barter_quote_last_update_date_time.manufactured_val = pendulum.parse(
                    self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg2_last_barter_quote_last_update_date_time.manufactured_val
        return None


class TopOfBook2(Structure):
    _fields_ = [
        ("id", c_int32),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("bid_quote_", BidQuote2),
        ("is_bid_quote_set_", c_bool),
        ("ask_quote_", AskQuote2),
        ("is_ask_quote_set_", c_bool),
        ("last_barter_", LastBarterQuote2),
        ("is_last_barter_set_", c_bool),
        ("total_bartering_security_size_", c_int64),
        ("is_total_bartering_security_size_set_", c_bool),
        ("market_barter_volume_", MarketBarterVolume),
        ("is_market_barter_volume_set_", c_bool),
        ("last_update_date_time_", c_char * MAX_STRING_LENGTH),
        ("is_last_update_date_time_set_", c_bool)
    ]

    def __str__(self):
        return (f"TOB: symbol={self.symbol_}, {str(self.bid_quote_)=}, {self.is_bid_quote_set_=}, "
                f"{str(self.ask_quote_)=}, {self.is_ask_quote_set_=}, "
                f"{str(self.last_barter_)=}, {self.is_last_barter_set_=}, "
                f"{self.total_bartering_security_size_=}, {self.last_update_date_time_=}, "
                f"{self.is_last_update_date_time_set_=}")

    def __repr__(self):
        return (f"TOB: symbol={self.symbol_}, {str(self.bid_quote_)=}, {self.is_bid_quote_set_=}, "
                f"{str(self.ask_quote_)=}, {self.is_ask_quote_set_=}, "
                f"{str(self.last_barter_)=}, {self.is_last_barter_set_=}, "
                f"{self.total_bartering_security_size_=}, {self.last_update_date_time_=}, "
                f"{self.is_last_update_date_time_set_=}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol2 is None:
            SymbolCacheShadowClass.symbol2 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol2

    @property
    def bid_quote(self):
        if self.is_bid_quote_set_:
            return self.bid_quote_
        return None

    @property
    def ask_quote(self):
        if self.is_ask_quote_set_:
            return self.ask_quote_
        return None

    @property
    def last_barter(self):
        if self.is_last_barter_set_:
            return self.last_barter_
        return None

    @property
    def total_bartering_security_size(self):
        if self.is_total_bartering_security_size_set_:
            return self.total_bartering_security_size_

    @property
    def market_barter_volume(self):
        if self.is_market_barter_volume_set_:
            return self.market_barter_volume_
        return None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if self.last_update_date_time_ != SymbolCacheShadowClass.leg2_tob_last_update_date_time.original_val:
                SymbolCacheShadowClass.leg2_tob_last_update_date_time.original_val = self.last_update_date_time_
                SymbolCacheShadowClass.leg2_tob_last_update_date_time.manufactured_val = pendulum.parse(self.last_update_date_time_.decode())
            return SymbolCacheShadowClass.leg2_tob_last_update_date_time.manufactured_val
        return None


class MarketDepth2(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_', c_char * MAX_STRING_LENGTH), ('exch_time_', c_char * MAX_STRING_LENGTH),
        ('arrival_time_', c_char * MAX_STRING_LENGTH), ('side_', c_char),
        ('px_', c_double), ('is_px_set_', c_bool), ('qty_', c_int64), ('is_qty_set_', c_bool),
        ('position', c_int32), ('market_maker_', c_char * MAX_STRING_LENGTH), ('is_market_maker_set_', c_bool),
        ('is_smart_depth_', c_bool), ('is_is_smart_depth_set_', c_bool),
        ('cumulative_notional_', c_double), ('is_cumulative_notional_set_', c_bool),
        ('cumulative_qty_', c_int64), ('is_cumulative_qty_set_', c_bool),
        ('cumulative_avg_px_', c_double), ('is_cumulative_avg_px_set_', c_bool)
    )

    def __str__(self):
        return (f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}, "
                f"position={self.position}")

    def __repr__(self):
        return (f"MD: symbol={self.symbol_}, px={self.px_}, qty={self.qty_}, side={self.side_}, "
                f"position={self.position}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol2 is None:
            SymbolCacheShadowClass.symbol2 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol2

    @property
    def side(self):
        if self.side_ == b"B":
            return TickType.BID
        else:
            return TickType.ASK

    @property
    def exch_time(self):
        if self.side == TickType.BID:
            cached_exch_time = SymbolCacheShadowClass.leg2_bid_market_depth_list[self.position][0]
        else:
            cached_exch_time = SymbolCacheShadowClass.leg2_ask_market_depth_list[self.position][0]
        if cached_exch_time.original_val != self.exch_time_:
            cached_exch_time.original_val = self.exch_time_
            cached_exch_time.manufactured_val = pendulum.parse(self.exch_time_.decode())
        return cached_exch_time.manufactured_val

    @property
    def arrival_time(self):
        if self.side == TickType.BID:
            cached_arrival_time = SymbolCacheShadowClass.leg2_bid_market_depth_list[self.position][1]
        else:
            cached_arrival_time = SymbolCacheShadowClass.leg2_ask_market_depth_list[self.position][1]
        if cached_arrival_time.original_val != self.exch_time_:
            cached_arrival_time.original_val = self.exch_time_
            cached_arrival_time.manufactured_val = pendulum.parse(self.arrival_time_.decode())
        return cached_arrival_time.manufactured_val

    @property
    def px(self):
        if self.is_px_set_:
            return self.px_
        return None

    @property
    def qty(self):
        if self.is_qty_set_:
            return self.qty_
        return None


class MDSharedMemory2(Structure):
    _fields_ = [
        ("update_counter", c_int64), ("symbol_", c_char * MAX_STRING_LENGTH),
        ("last_barter", LastBarter2), ("top_of_book", TopOfBook2),
        ("bid_market_depth_list", MarketDepth2 * 10),
        ("ask_market_depth_list", MarketDepth2 * 10)
    ]

    def __str__(self):
        return (f"{self.symbol_=}, {str(self.last_barter)=}, {str(self.top_of_book)=}, "
                f"{[str(md) for md in self.bid_market_depth_list]}, {[str(md) for md in self.ask_market_depth_list]}, "
                f"{str(self.last_barter_last_update_date_time)=}, {str(self.top_of_book_last_update_date_time)=}, "
                f"{[str(md) for md in self.bid_market_depth_last_update_date_times_list]}, "
                f"{[str(md) for md in self.bid_market_depth_last_update_date_times_list]}")

    @property
    def symbol(self):
        if SymbolCacheShadowClass.symbol2 is None:
            SymbolCacheShadowClass.symbol2 = self.symbol_.decode()
        return SymbolCacheShadowClass.symbol2


class BaseMDSharedMemoryContainer(Structure):
    _fields_ = [
        ("leg_1_md_shared_memory", MDSharedMemory1), ("leg_2_md_shared_memory", MDSharedMemory2)
    ]

    def __str__(self):
        return f"{str(self.leg_1_md_shared_memory)=}, {str(self.leg_2_md_shared_memory)=}"


class MDSharedMemoryContainer(Structure):
    _fields_ = [
        ("shm_update_signature", c_uint64),
        ("mutex", pthread_mutex_t),
        ("md_cache_container", BaseMDSharedMemoryContainer)
    ]

    def __str__(self):
        return f"{str(self.md_cache_container)=}"


class SymbolCache:
    def __init__(self):
        self.top_of_book: TopOfBook1 | TopOfBook2 | TopOfBookBaseModel | None = None
        self.last_barter: LastBarter1 | LastBarter2 | None = None
        self.bid_market_depth: List[MarketDepth1 | MarketDepth2] | None = None
        self.ask_market_depth: List[MarketDepth1 | MarketDepth2] | None = None
        self.so: SymbolOverview | SymbolOverviewBaseModel | None = None
        self.buy_pos_cache: PosCache | None = None
        self.sell_pos_cache: PosCache | None = None

    def __str__(self):
        return (f"MobileBookContainer({str(self.top_of_book)}, {str(self.bid_market_depth)}, "
                f"{str(self.ask_market_depth)}, {str(self.last_barter)})")

    def get_top_of_book_bid_quote(self) -> QuoteBaseModel | None:
        return self.top_of_book.bid_quote

    def get_top_of_book_ask_quote(self) -> QuoteBaseModel | None:
        return self.top_of_book.ask_quote

    def get_top_of_book_last_barter(self) -> QuoteBaseModel | None:
        return self.top_of_book.last_barter

    def get_top_of_book(self, date_time: DateTime | None = None) -> TopOfBook1 | TopOfBook2 | None:
        if date_time is None or date_time < self.top_of_book.last_update_date_time:
            return self.top_of_book
        return None

    def get_last_barter(self) -> LastBarter1 | LastBarter2 | None:
        return self.last_barter

    def remove_bid_market_depth_from_position(self, position: int) -> bool:
        self.bid_market_depth[position] = None
        return True

    def remove_ask_market_depth_from_position(self, position: int) -> bool:
        self.ask_market_depth[position] = None
        return True

    def get_bid_market_depths(self) -> List[MarketDepth1 | MarketDepth2]:
        return self.bid_market_depth

    def get_ask_market_depths(self) -> List[MarketDepth1 | MarketDepth2]:
        return self.ask_market_depth

    def get_bid_market_depth_from_depth(self, position: int) -> MarketDepth1 | MarketDepth2 | None:
        if position > 0 or position < 9:
            return self.bid_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_ask_market_depth_from_depth(self, position: int) -> MarketDepth1 | MarketDepth2 | None:
        if position > 0 or position < 9:
            return self.ask_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_so(self, symbol: str | None = None):  # so getter need to get breach_px
        return self.so


class SymbolCacheContainer:
    # below None data-members must be initialized at init time of executor process
    shared_memory = None
    shared_memory_semaphore = None
    is_shm_ready = False
    EXPECTED_SHM_SIGNATURE: hex = 0xFAFAFAFAFAFAFAFA    # hard-coded: cpp puts same value
    symbol_to_symbol_cache_dict: Dict[str, SymbolCache] = {}
    semaphore = threading.Semaphore(0)

    @staticmethod
    def release_notify_semaphore():
        if SymbolCacheContainer.shared_memory_semaphore is not None:
            SymbolCacheContainer.shared_memory_semaphore.release()
        else:
            SymbolCacheContainer.semaphore.release()

    @staticmethod
    def acquire_notify_semaphore():
        if SymbolCacheContainer.shared_memory_semaphore is not None:
            SymbolCacheContainer.shared_memory_semaphore.acquire()
        else:
            SymbolCacheContainer.semaphore.acquire()

    @staticmethod
    def update_md_cache_from_shared_memory() -> bool:
        md_shared_memory_container: MDSharedMemoryContainer = (
            MDSharedMemoryContainer.from_buffer(SymbolCacheContainer.shared_memory))
        if not SymbolCacheContainer.is_shm_ready:
            if md_shared_memory_container.shm_update_signature == SymbolCacheContainer.EXPECTED_SHM_SIGNATURE:
                SymbolCacheContainer.is_shm_ready = True
            else:
                logging.warning("Couldn't find matching shm signature, ignoring this internal run cycle - retrying "
                                f"on next semaphore release, {SymbolCacheContainer.EXPECTED_SHM_SIGNATURE=}, "
                                f"found {md_shared_memory_container.shm_update_signature}")
                return False
        # else not required: no need for reassigning is_shm_ready once expected signature matches

        pthread_shm_mutex: PThreadShmMutex = PThreadShmMutex(md_shared_memory_container.mutex)
        while True:
            lock_try_time = DateTime.utcnow()
            lock_res = pthread_shm_mutex.try_timedlock()
            if lock_res == 0:
                try:
                    md_shared_memory_container: MDSharedMemoryContainer = (
                        MDSharedMemoryContainer.from_buffer_copy(SymbolCacheContainer.shared_memory))
                    md_shared_memory_container_ = md_shared_memory_container.md_cache_container

                    # setting leg1 md data
                    leg_1_md_shared_memory = md_shared_memory_container_.leg_1_md_shared_memory
                    symbol = leg_1_md_shared_memory.symbol
                    symbol_cache = SymbolCacheContainer.symbol_to_symbol_cache_dict.get(symbol)
                    symbol_cache.top_of_book = leg_1_md_shared_memory.top_of_book
                    symbol_cache.last_barter = leg_1_md_shared_memory.last_barter
                    symbol_cache.bid_market_depth = leg_1_md_shared_memory.bid_market_depth_list
                    symbol_cache.ask_market_depth = leg_1_md_shared_memory.ask_market_depth_list

                    # setting leg2 md data
                    leg_2_md_shared_memory = md_shared_memory_container_.leg_2_md_shared_memory
                    symbol = leg_2_md_shared_memory.symbol
                    symbol_cache = SymbolCacheContainer.symbol_to_symbol_cache_dict.get(symbol)
                    symbol_cache.top_of_book = leg_2_md_shared_memory.top_of_book
                    symbol_cache.last_barter = leg_2_md_shared_memory.last_barter
                    symbol_cache.bid_market_depth = leg_2_md_shared_memory.bid_market_depth_list
                    symbol_cache.ask_market_depth = leg_2_md_shared_memory.ask_market_depth_list

                except Exception as e:
                    logging.exception(f"update_md_cache_from_shared_memory failed: exception {e}")
                    return False
                finally:
                    pthread_shm_mutex.unlock()
                    break
            else:
                lock_timed_out_time = DateTime.utcnow()
                logging.error(f"pthread lock tried to take lock at {lock_try_time}, but timed-out at "
                              f"{lock_timed_out_time}, taking total "
                              f"{(lock_timed_out_time - lock_try_time).total_seconds()} sec(s), {lock_res=}")
        return True


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