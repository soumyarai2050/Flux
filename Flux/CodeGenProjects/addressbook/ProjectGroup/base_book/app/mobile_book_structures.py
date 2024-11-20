# standard imports
from typing import Dict, Any, List, ClassVar, Tuple, Final
from ctypes import *

# 3rd party imports
import pendulum

# project imports
from FluxPythonUtils.scripts.pthread_shm_mutex import pthread_mutex_t, PThreadShmMutex
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import (
    TickType)

MAX_STRING_LENGTH: Final[int] = 128


class ShadowFields:
    def __init__(self):
        self._original_val: bytes | None = None
        self.manufactured_val: Any = None


class DTShadowFields(ShadowFields):

    @property
    def original_val(self) -> bytes:
        return self._original_val

    @original_val.setter
    def original_val(self, val: bytes):
        self._original_val = val
        self.manufactured_val = pendulum.parse(self._original_val.decode())


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


class SymbolNExchId(Structure):
    _fields_ = [
        ('symbol_', c_char * MAX_STRING_LENGTH), ('exch_id_', c_char * MAX_STRING_LENGTH)
    ]

    def __str__(self):
        return f"SymbolNExchId(symbol={self.symbol_}, exch_id={self.exch_id_})"

    @property
    def symbol(self):
        if not hasattr(self, "_symbol") or self._symbol is None:
            self._symbol = self.symbol_.decode()
        return self._symbol

    @property
    def exch_id(self):
        if not hasattr(self, "_exch_id") or self._exch_id is None:
            self._exch_id = self.exch_id_.decode()
        return self._exch_id


class LastBarter(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_n_exch_id', SymbolNExchId), ('exch_time_', c_char * MAX_STRING_LENGTH),
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
        if not hasattr(self, "_exch_time"):
            self._exch_time = DTShadowFields()

        if self.exch_time_ != self._exch_time.original_val:
            self._exch_time.original_val = self.exch_time_
        return self._exch_time.manufactured_val

    @property
    def arrival_time(self):
        if not hasattr(self, "_arrival_time"):
            self._arrival_time = DTShadowFields()

        if self.arrival_time_ != self._arrival_time.original_val:
            self._arrival_time.original_val = self.exch_time_
        return self._arrival_time.manufactured_val

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


class Quote(Structure):
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
            if not hasattr(self, "_last_update_date_time"):
                self._last_update_date_time = DTShadowFields()

            if self.last_update_date_time_ != self._last_update_date_time.original_val:
                self._last_update_date_time.original_val = self.last_update_date_time_
            return self._last_update_date_time.manufactured_val
        return None


class TopOfBook(Structure):
    _fields_ = [
        ("id", c_int32),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("bid_quote_", Quote),
        ("is_bid_quote_set_", c_bool),
        ("ask_quote_", Quote),
        ("is_ask_quote_set_", c_bool),
        ("last_barter_", Quote),
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
        if not hasattr(self, "_symbol") or self._symbol is None:
            self._symbol = self.symbol_.decode()
        return self._symbol

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
            if not hasattr(self, "_tob_last_update_date_time"):
                self._tob_last_update_date_time = DTShadowFields()

            if self.last_update_date_time_ != self._tob_last_update_date_time.original_val:
                self._tob_last_update_date_time.original_val = self.last_update_date_time_
            return self._tob_last_update_date_time.manufactured_val
        return None


class MarketDepth(Structure):
    _fields_ = (
        ("id", c_int32), ('symbol_', c_char * MAX_STRING_LENGTH),
        ('exch_time_', c_char * MAX_STRING_LENGTH),
        ('arrival_time_', c_char * MAX_STRING_LENGTH),
        ('side_', c_char),
        ('px_', c_double),
        ('is_px_set_', c_bool),
        ('qty_', c_int64), ('is_qty_set_', c_bool),
        ('position', c_int32),
        ('market_maker_', c_char * MAX_STRING_LENGTH), ('is_market_maker_set_', c_bool),
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
        if not hasattr(self, "_symbol") or self._symbol is None:
            self._symbol = self.symbol_.decode()
        return self._symbol

    @property
    def side(self):
        if self.side_ == b"B":
            return TickType.BID
        else:
            return TickType.ASK

    @property
    def exch_time(self):
        if not hasattr(self, "_exch_time"):
            self._exch_time = DTShadowFields()

        if self.exch_time_ != self._exch_time.original_val:
            self._exch_time.original_val = self.exch_time_
        return self._exch_time.manufactured_val

    @property
    def arrival_time(self):
        if not hasattr(self, "_arrival_time"):
            self._arrival_time = DTShadowFields()

        if self.arrival_time_ != self._arrival_time.original_val:
            self._arrival_time.original_val = self.exch_time_
        return self._arrival_time.manufactured_val


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
    def market_maker(self):
        if self.is_market_maker_set_:
            if not hasattr(self, "_market_maker") or self._market_maker is None:
                self._market_maker = self.market_maker_.decode()
            return self._market_maker
        return None

    @property
    def is_smart_depth(self):
        if self.is_is_smart_depth_set_:
            return self.is_smart_depth_
        return False

    @property
    def cumulative_notional(self):
        if self.is_cumulative_notional_set_:
            return self.cumulative_notional_
        return None

    @property
    def cumulative_qty(self):
        if self.is_cumulative_qty_set_:
            return self.cumulative_qty_
        return None

    @property
    def cumulative_avg_px(self):
        if self.is_cumulative_avg_px_set_:
            return self.cumulative_avg_px_
        return None


class MDContainer(Structure):
    _fields_ = [
        ("update_counter", c_int64),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("last_barter", LastBarter),
        ("top_of_book", TopOfBook),
        ("bid_market_depth_list", MarketDepth * 10),
        ("ask_market_depth_list", MarketDepth * 10)
    ]

    def __str__(self):
        return (f"{self.update_counter=} {self.symbol_=}, {str(self.last_barter)=}, {str(self.top_of_book)=}, "
                f"{[str(md) for md in self.bid_market_depth_list]}, {[str(md) for md in self.ask_market_depth_list]}")

    @property
    def symbol(self):
        if not hasattr(self, "_symbol") or self._symbol is None:
            self._symbol = self.symbol_.decode()
        return self._symbol


class BaseMDSharedMemoryContainer(Structure):
    _fields_ = [
        ("leg_1_md_shared_memory", MDContainer),
        ("leg_2_md_shared_memory", MDContainer)
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