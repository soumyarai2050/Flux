# standard imports
from typing import Dict, Any, List, ClassVar, Tuple, Final
from ctypes import *
import os

# 3rd party imports
import pendulum

os.environ['ModelType'] = 'msgspec'
# project imports
from FluxPythonUtils.scripts.pthread_shm_mutex import pthread_mutex_t, PThreadShmMutex
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import (
    TickType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_ts_utils import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import get_pair_plan_id_from_cmd_argv
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import email_book_service_http_client
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import executor_config_yaml_dict

MAX_STRING_LENGTH: Final[int] = 128
pair_plan_id = get_pair_plan_id_from_cmd_argv(raise_exception=False)
if pair_plan_id is not None:
    pair_plan = email_book_service_http_client.get_pair_plan_client(pair_plan_id)
    exch_id = pair_plan.pair_plan_params.plan_leg1.exch_id
    exch_to_market_depth_lvl_dict = executor_config_yaml_dict.get("exch_to_market_depth_lvl", {})
    DEPTH_LVL: Final[int] = exch_to_market_depth_lvl_dict.get(exch_id, 10)
else:
    # when we reach here through basket executor flow
    DEPTH_LVL: Final[int] = 10


class ShadowFields:
    def __init__(self):
        self._original_val: Any = None
        self.manufactured_val: Any = None


class DTShadowFields(ShadowFields):

    @property
    def original_val(self) -> int:
        return self._original_val

    @original_val.setter
    def original_val(self, val: int):
        self._original_val = val
        self.manufactured_val = get_pendulum_dt_from_epoch(val)


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
    def applicable_period_seconds(self):
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
        ("id", c_int32), ('symbol_n_exch_id', SymbolNExchId), ('exch_time_', c_int64),
        ('arrival_time_',  c_int64), ('px', c_double), ('qty', c_int64),
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
        ("last_update_date_time_", c_int64),
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
        ("last_update_date_time_", c_int64),
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
        ('exch_time_', c_int64),
        ('arrival_time_', c_int64),
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


class SymbolOverview(Structure): # Renamed to avoid potential import conflicts
    _fields_ = [
        ('id_', c_int32),
        # is_id_set_ not strictly needed for required proto fields, but can be added for C struct consistency
        ('symbol_', c_char * MAX_STRING_LENGTH),
        # is_symbol_set_
        ('company_', c_char * MAX_STRING_LENGTH),
        ('is_company_set_', c_bool),
        ('exchange_code_', c_char * MAX_STRING_LENGTH),
        ('is_exchange_code_set_', c_bool),
        ('status_', c_char * MAX_STRING_LENGTH),
        ('is_status_set_', c_bool),
        ('lot_size_', c_int64),
        ('is_lot_size_set_', c_bool),
        ('limit_up_px_', c_double), # float in proto often maps to double (c_double) for precision
        ('is_limit_up_px_set_', c_bool),
        ('limit_dn_px_', c_double),
        ('is_limit_dn_px_set_', c_bool),
        ('conv_px_', c_double),
        ('is_conv_px_set_', c_bool),
        ('closing_px_', c_double),
        ('is_closing_px_set_', c_bool),
        ('open_px_', c_double),
        ('is_open_px_set_', c_bool),
        ('high_', c_double),
        ('is_high_set_', c_bool),
        ('low_', c_double),
        ('is_low_set_', c_bool),
        ('volume_', c_int64),
        ('is_volume_set_', c_bool),
        ('tick_size_', c_double),
        ('is_tick_size_set_', c_bool),
        ('last_update_date_time_', c_int64),
        ('is_last_update_date_time_set_', c_bool),
        ('force_publish_', c_bool),
        ('is_force_publish_set_', c_bool)
    ]

    def __str__(self):
        return (f"SymbolOverview(id={self.id_}, symbol={self.symbol}, company={self.company}, "
                f"exchange_code={self.exchange_code}, "
                f"status={self.status}, lot_size={self.lot_size}, limit_up_px={self.limit_up_px}, "
                f"limit_dn_px={self.limit_dn_px}, conv_px={self.conv_px}, closing_px={self.closing_px}, "
                f"open_px={self.open_px}, high={self.high}, low={self.low}, volume={self.volume}, "
                f"tick_size={self.tick_size}, last_update_date_time={self.last_update_date_time}, "
                f"force_publish={self.force_publish})")

    def __repr__(self):
        return self.__str__()

    # Properties for convenient access and handling optional fields / type conversions

    @property
    def id(self): # Assuming id is always set as per "required" in proto
        return self.id_

    @property
    def symbol(self): # Assuming symbol is always set
        # Decode c_char array to Python string, cache it
        if not hasattr(self, "_symbol_decoded") or self._symbol_decoded_val != self.symbol_:
            self._symbol_decoded = self.symbol_.decode().strip('\x00')
            self._symbol_decoded_val = self.symbol_ # Store original bytes to check for change
        return self._symbol_decoded

    @property
    def exchange_code(self):
        if self.is_exchange_code_set_:
            if not hasattr(self, "_exchange_code_decoded") or self._exchange_code_decoded_val != self.exchange_code_:
                self._exchange_code_decoded = self.exchange_code_.decode().strip('\x00')
                self._exchange_code_decoded_val = self.exchange_code_
            return self._exchange_code_decoded
        return None

    @property
    def company(self):
        if self.is_company_set_:
            if not hasattr(self, "_company_decoded") or self._company_decoded_val != self.company_:
                 self._company_decoded = self.company_.decode().strip('\x00')
                 self._company_decoded_val = self.company_
            return self._company_decoded
        return None

    @property
    def status(self):
        if self.is_status_set_:
            if not hasattr(self, "_status_decoded") or self._status_decoded_val != self.status_:
                self._status_decoded = self.status_.decode().strip('\x00')
                self._status_decoded_val = self.status_
            return self._status_decoded
        return None

    @property
    def lot_size(self):
        return self.lot_size_ if self.is_lot_size_set_ else None

    @property
    def limit_up_px(self):
        return self.limit_up_px_ if self.is_limit_up_px_set_ else None

    @property
    def limit_dn_px(self):
        return self.limit_dn_px_ if self.is_limit_dn_px_set_ else None

    @property
    def conv_px(self):
        return self.conv_px_ if self.is_conv_px_set_ else None

    @property
    def closing_px(self):
        return self.closing_px_ if self.is_closing_px_set_ else None

    @property
    def open_px(self):
        return self.open_px_ if self.is_open_px_set_ else None

    @property
    def high(self):
        return self.high_ if self.is_high_set_ else None

    @property
    def low(self):
        return self.low_ if self.is_low_set_ else None

    @property
    def volume(self):
        return self.volume_ if self.is_volume_set_ else None

    @property
    def tick_size(self):
        return self.tick_size_ if self.is_tick_size_set_ else None

    @property
    def last_update_date_time(self):
        if self.is_last_update_date_time_set_:
            if not hasattr(self, "_so_last_update_date_time_shadow"):
                self._so_last_update_date_time_shadow = DTShadowFields()
            # Check if the underlying c_int64 value has changed
            if self.last_update_date_time_ != self._so_last_update_date_time_shadow.original_val:
                self._so_last_update_date_time_shadow.original_val = self.last_update_date_time_
            return self._so_last_update_date_time_shadow.manufactured_val
        return None

    @property
    def force_publish(self):
        return self.force_publish_ if self.is_force_publish_set_ else None


class MDContainer(Structure):
    _fields_ = [
        ("update_counter", c_int64),
        ("symbol_", c_char * MAX_STRING_LENGTH),
        ("last_barter", LastBarter),
        ("top_of_book", TopOfBook),
        ("bid_market_depth_list", MarketDepth * DEPTH_LVL),
        ("ask_market_depth_list", MarketDepth * DEPTH_LVL),
        ("symbol_overview", SymbolOverview),  # ADDED FIELD
        ("is_symbol_overview_set", c_bool)  # ADDED FLAG
    ]

    def __str__(self):
        return (f"{self.update_counter=} {self.symbol_=}, {str(self.last_barter)=}, {str(self.top_of_book)=}, "
                f"{[str(md) for md in self.bid_market_depth_list]}, {[str(md) for md in self.ask_market_depth_list]}")

    @property
    def symbol(self):
        if not hasattr(self, "_symbol") or self._symbol is None:
            self._symbol = self.symbol_.decode()
        return self._symbol


class MDSharedMemoryContainer(Structure):
    """
    Top-level structure for shared memory, containing a single MDContainer,
    mutex, and signature.
    """
    _fields_ = [
        ("shm_update_signature", c_uint64),
        ("mutex", pthread_mutex_t),
        ("mobile_book_container", MDContainer)  # The existing MDContainer
    ]

    def __str__(self):
        return (f"MDSharedMemoryContainer(signature={hex(self.shm_update_signature)}, "
                f"mobile_book_container={str(self.mobile_book_container)})")
