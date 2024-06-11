# mobile_book_cache.pyx

# standard imports
import copy
from libc.stdint cimport int64_t, int32_t
from cython cimport bint
from pendulum import DateTime
from datetime import timedelta
import logging
from pathlib import PurePath

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    executor_config_yaml_dict)


market_depth_levels = executor_config_yaml_dict.get("market_depth_levels")
if market_depth_levels is None:
    market_depth_levels = 10    # default value


cdef extern from "<Python.h>":
    ctypedef struct PyObject:
        pass

    PyObject* PyLong_FromVoidPtr(void*)


cdef extern from "<mutex>" namespace "std":
    cdef cppclass mutex:
        mutex() except +
        void lock()
        void unlock()

cdef class MarketBarterVolume:
    cdef public str _id
    cdef public int64_t participation_period_last_barter_qty_sum
    cdef public int32_t applicable_period_seconds

    def __init__(self, _id=None, participation_period_last_barter_qty_sum=None, applicable_period_seconds=None):
        self._id = _id if _id is not None else ""
        if participation_period_last_barter_qty_sum is None:
            participation_period_last_barter_qty_sum = 0
        self.participation_period_last_barter_qty_sum = participation_period_last_barter_qty_sum
        if applicable_period_seconds is None:
            applicable_period_seconds = 0
        self.applicable_period_seconds = applicable_period_seconds

# todo: update int field as ctypes
cdef class Quote:
    cdef public float px
    cdef public int qty
    cdef public float premium
    cdef public object last_update_date_time

    def __init__(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if px is None:
            px = 0.0
        if qty is None:
            qty = 0
        if premium is None:
            premium = 0.0
        self.px = px
        self.qty = qty
        self.premium = premium
        self.last_update_date_time = last_update_date_time

cdef class TopOfBook:
    cdef mutex * m_mutex
    cdef public int32_t _id
    cdef public str symbol
    cdef public Quote bid_quote
    cdef public Quote ask_quote
    cdef public Quote last_barter
    cdef public int64_t total_bartering_security_size
    cdef public list market_barter_volume
    cdef public object last_update_date_time

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol, bid_quote=None, ask_quote=None, last_barter=None,
                 total_bartering_security_size=None, market_barter_volume=None, last_update_date_time=None):
        self._id = _id
        self.symbol = symbol
        self.bid_quote = bid_quote
        self.ask_quote = ask_quote
        self.last_barter = last_barter
        if total_bartering_security_size is None:
            total_bartering_security_size = 0
        self.total_bartering_security_size = total_bartering_security_size
        if market_barter_volume:
            self.market_barter_volume = market_barter_volume
        else:
            self.market_barter_volume = []
        self.last_update_date_time = last_update_date_time

    def __dealloc__(self):
        del self.m_mutex

    cpdef get_mutex(self):
        if self.m_mutex == NULL:
            raise RuntimeError("Mutex pointer is null")
        cdef PyObject * obj_ptr = PyLong_FromVoidPtr(<void *> self.m_mutex)
        return <object> obj_ptr


cdef class MarketDepth:
    cdef mutex * m_mutex
    cdef public int32_t _id
    cdef public str symbol
    cdef public object exch_time
    cdef public object arrival_time
    cdef public TickType side
    cdef public float px
    cdef public int64_t qty
    cdef public int32_t position
    cdef public str market_maker
    cdef public bint is_smart_depth
    cdef public float cumulative_notional
    cdef public int64_t cumulative_qty
    cdef public float cumulative_avg_px

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol, exch_time=None, arrival_time=None, side=None, position=None, px=None, qty=None,
                 market_maker=None, is_smart_depth=None, cumulative_notional=None,
                 cumulative_qty=None, cumulative_avg_px=None):
        self._id = _id
        self.symbol = symbol
        self.exch_time = exch_time
        self.arrival_time =arrival_time
        self.side = TickType.BID if side == "BID" else TickType.ASK
        self.px = px if px is not None else 0.0
        self.qty = qty if qty is not None else 0
        self.position = position
        self.market_maker = market_maker if market_maker is not None else ""
        self.is_smart_depth = is_smart_depth if is_smart_depth else 0
        self.cumulative_notional = cumulative_notional if cumulative_notional is not None else 0.0
        self.cumulative_qty = cumulative_qty if cumulative_qty is not None else 0
        self.cumulative_avg_px = cumulative_avg_px if cumulative_avg_px is not None else 0.0

    def __dealloc__(self):
        del self.m_mutex

    cpdef get_mutex(self):
        if self.m_mutex == NULL:
            raise RuntimeError("Mutex pointer is null")
        cdef PyObject * obj_ptr = PyLong_FromVoidPtr(<void *> self.m_mutex)
        return <object> obj_ptr


cdef class SymbolNExchId:
    cdef public str symbol
    cdef public str exch_id

    def __init__(self, symbol=None, exch_id=None):
        self.symbol = symbol if symbol is not None else ""
        self.exch_id = exch_id if exch_id is not None else ""


cpdef enum TickType:
    BID_SIZE = 1,
    BID = 2,
    ASK = 3,
    ASK_SIZE = 4,
    LAST = 5,
    LAST_SIZE = 6,
    HIGH = 7,
    LOW = 8,
    VOLUME = 9,
    CLOSE = 10,
    BID_OPTION_COMPUTATION = 11,
    ASK_OPTION_COMPUTATION = 12,
    LAST_OPTION_COMPUTATION = 13,
    MODEL_OPTION = 14,
    OPEN = 15,
    LOW_13_WEEK = 16,
    HIGH_13_WEEK = 17,
    LOW_26_WEEK = 18,
    HIGH_26_WEEK = 19,
    LOW_52_WEEK = 20,
    HIGH_52_WEEK = 21,
    AVG_VOLUME = 22,
    OPEN_INTEREST = 23,
    OPTION_HISTORICAL_VOL = 24,
    OPTION_IMPLIED_VOL = 25,
    OPTION_BID_EXCH = 26,
    OPTION_ASK_EXCH = 27,
    OPTION_CALL_OPEN_INTEREST = 28,
    OPTION_PUT_OPEN_INTEREST = 29,
    OPTION_CALL_VOLUME = 30,
    OPTION_PUT_VOLUME = 31,
    INDEX_FUTURE_PREMIUM = 32,
    BID_EXCH = 33,
    ASK_EXCH = 34,
    AUCTION_VOLUME = 35,
    AUCTION_PRICE = 36,
    AUCTION_IMBALANCE = 37,
    MARK_PRICE = 38,
    BID_EFP_COMPUTATION = 39,
    ASK_EFP_COMPUTATION = 40,
    LAST_EFP_COMPUTATION = 41,
    OPEN_EFP_COMPUTATION = 42,
    HIGH_EFP_COMPUTATION = 43,
    LOW_EFP_COMPUTATION = 44,
    CLOSE_EFP_COMPUTATION = 45,
    LAST_TIMESTAMP = 46,
    SHORTABLE = 47,
    FUNDAMENTAL_RATIOS = 48,
    RT_VOLUME = 49,
    HALTED = 50,
    BID_YIELD = 51,
    ASK_YIELD = 52,
    LAST_YIELD = 53,
    CUST_OPTION_COMPUTATION = 54,
    TRADE_COUNT = 55,
    TRADE_RATE = 56,
    VOLUME_RATE = 57,
    LAST_RTH_TRADE = 58,
    RT_HISTORICAL_VOL = 59,
    IB_DIVIDENDS = 60,
    BOND_FACTOR_MULTIPLIER = 61,
    REGULATORY_IMBALANCE = 62,
    NEWS_TICK = 63,
    SHORT_TERM_VOLUME_3_MIN = 64,
    SHORT_TERM_VOLUME_5_MIN = 65,
    SHORT_TERM_VOLUME_10_MIN = 66,
    DELAYED_BID = 67,
    DELAYED_ASK = 68,
    DELAYED_LAST = 69,
    DELAYED_BID_SIZE = 70,
    DELAYED_ASK_SIZE = 71,
    DELAYED_LAST_SIZE = 72,
    DELAYED_HIGH = 73,
    DELAYED_LOW = 74,
    DELAYED_VOLUME = 75,
    DELAYED_CLOSE = 76,
    DELAYED_OPEN = 77,
    RT_TRD_VOLUME = 78,
    CREDITMAN_MARK_PRICE = 79,
    CREDITMAN_SLOW_MARK_PRICE = 80,
    DELAYED_BID_OPTION = 81,
    DELAYED_ASK_OPTION = 82,
    DELAYED_LAST_OPTION = 83,
    DELAYED_MODEL_OPTION = 84,
    LAST_EXCH = 85,
    LAST_REG_TIME = 86,
    FUTURES_OPEN_INTEREST = 87,
    AVG_OPT_VOLUME = 88,
    DELAYED_LAST_TIMESTAMP = 89,
    SHORTABLE_SHARES = 90,
    DELAYED_HALTED = 91,
    REUTERS_2_MUTUAL_FUNDS = 92,
    ETF_NAV_CLOSE = 93,
    ETF_NAV_PRIOR_CLOSE = 94,
    ETF_NAV_BID =  95,
    ETF_NAV_ASK = 96,
    ETF_NAV_LAST = 97,
    ETF_FROZEN_NAV_LAST = 98,
    ETF_NAV_HIGH = 99,
    ETF_NAV_LOW = 100,
    SOCIAL_MARKET_ANALYTICS = 101,
    ESTIMATED_IPO_MIDPOINT = 102,
    FINAL_IPO_LAST = 103,
    NOT_SET = 104

cdef class LastBarter:
    cdef mutex * m_mutex
    cdef public int32_t _id
    cdef public SymbolNExchId symbol_n_exch_id
    cdef public object exch_time
    cdef public object arrival_time
    cdef public float px
    cdef public int64_t qty
    cdef public float premium
    cdef public MarketBarterVolume market_barter_volume

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol_n_exch_id=None, exch_time=None, arrival_time=None, px=None, qty=None,
                 premium=None, market_barter_volume=None):
        self._id = _id
        self.symbol_n_exch_id = symbol_n_exch_id
        self.exch_time = exch_time
        self.arrival_time = arrival_time
        print("PY: After arrival in lastBarter constructor")
        self.px = px if px is not None else 0.0
        self.qty = qty if qty is not None else 0
        self.premium = premium if premium is not None else 0
        print("PY: After premium in lastBarter constructor")
        self.market_barter_volume = market_barter_volume
        print("PY:  ======================  returning from lastBarter constructor")

    def __dealloc__(self):
        del self.m_mutex

    cpdef get_mutex(self):
        if self.m_mutex == NULL:
            raise RuntimeError("Mutex pointer is null")
        cdef PyObject * obj_ptr = PyLong_FromVoidPtr(<void *> self.m_mutex)
        return <object> obj_ptr


cdef class MobileBookContainer:
    cdef public str symbol
    cdef public list bid_market_depths
    cdef public list ask_market_depths
    cdef public TopOfBook top_of_book
    cdef public LastBarter last_barter

    def __init__(self, str symbol):
        self.symbol = symbol
        self.bid_market_depths = [None]*market_depth_levels
        self.ask_market_depths = [None]*market_depth_levels

    cpdef bint set_top_of_book(
            self, _id, symbol, bid_quote_px=None, bid_quote_qty=None, bid_quote_premium=None,
            ask_quote_px=None, ask_quote_qty=None, ask_quote_premium=None, last_barter_px=None, last_barter_qty=None,
            last_barter_premium=None, bid_quote_last_update_date_time=None,
            ask_quote_last_update_date_time=None, last_barter_last_update_date_time=None,
            total_bartering_security_size=None, market_barter_volume=None, last_update_date_time=None):
        if self.top_of_book is None:
            bid_quote = None
            if bid_quote_px or bid_quote_qty or bid_quote_premium or bid_quote_last_update_date_time:
                bid_quote = Quote(bid_quote_px, bid_quote_qty, bid_quote_premium, bid_quote_last_update_date_time)
            ask_quote = None
            if ask_quote_px or ask_quote_qty or ask_quote_premium or ask_quote_last_update_date_time:
                ask_quote = Quote(ask_quote_px, ask_quote_qty, ask_quote_premium, ask_quote_last_update_date_time)
            last_barter = None
            if last_barter_px or last_barter_qty or last_barter_premium or last_barter_last_update_date_time:
                last_barter = Quote(last_barter_px, last_barter_qty, last_barter_premium, last_barter_last_update_date_time)
            self.top_of_book = TopOfBook(_id, symbol, bid_quote, ask_quote, last_barter,
                                         total_bartering_security_size, market_barter_volume, last_update_date_time)
            return True
        return False

    cpdef bint set_top_of_book_symbol(self, str symbol_):
        if self.top_of_book:
            self.top_of_book.symbol = symbol_
            return True
        return False

    cpdef Quote get_top_of_book_bid_quote(self):
        return self.top_of_book.bid_quote

    cpdef bint set_top_of_book_bid_quote(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if (self.top_of_book.bid_quote is None or
                last_update_date_time > self.top_of_book.bid_quote.last_update_date_time):
            self.top_of_book.bid_quote = Quote(px, qty, premium, last_update_date_time)
            return True
        return False

    cpdef bint set_top_of_book_ask_quote(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if (self.top_of_book.ask_quote is None or
                last_update_date_time > self.top_of_book.ask_quote.last_update_date_time):
            self.top_of_book.ask_quote = Quote(px, qty, premium, last_update_date_time)
            return True
        return False

    cpdef bint set_top_of_book_last_barter(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if (self.top_of_book.last_barter is None or
                last_update_date_time > self.top_of_book.last_barter.last_update_date_time):
            self.top_of_book.last_barter = Quote(px, qty, premium, last_update_date_time)
            return True
        return False

    cpdef bint set_top_of_book_bid_quote_px(self, float px):
        if self.top_of_book and self.top_of_book.bid_quote:
            self.top_of_book.bid_quote.px = px
            return True
        return False

    cpdef bint set_top_of_book_bid_quote_qty(self, int qty):
        if self.top_of_book and self.top_of_book.bid_quote:
            self.top_of_book.bid_quote.qty = qty
            return True
        return False

    cpdef bint set_top_of_book_bid_quote_premium(self, float premium):
        if self.top_of_book and self.top_of_book.bid_quote:
            self.top_of_book.bid_quote.premium = premium
            return True
        return False

    cpdef bint set_top_of_book_bid_quote_last_update_date_time(self, object last_update_date_time):
        if self.top_of_book and self.top_of_book.bid_quote:
            self.top_of_book.bid_quote.last_update_date_time = last_update_date_time
            return True
        return False

    cpdef Quote get_top_of_book_ask_quote(self):
        return self.top_of_book.ask_quote

    cpdef bint set_top_of_book_ask_quote_px(self, float px):
        if self.top_of_book and self.top_of_book.ask_quote:
            self.top_of_book.ask_quote.px = px
            return True
        return False

    cpdef bint set_top_of_book_ask_quote_qty(self, int qty):
        if self.top_of_book and self.top_of_book.ask_quote:
            self.top_of_book.ask_quote.qty = qty
            return True
        return False

    cpdef bint set_top_of_book_ask_quote_premium(self, float premium):
        if self.top_of_book and self.top_of_book.ask_quote:
            self.top_of_book.ask_quote.premium = premium
            return True
        return False

    cpdef bint set_top_of_book_ask_quote_last_update_date_time(self, object last_update_date_time):
        if self.top_of_book and self.top_of_book.ask_quote:
            self.top_of_book.ask_quote.last_update_date_time = last_update_date_time
            return True
        return False

    cpdef Quote get_top_of_book_last_barter(self):
        return self.top_of_book.last_barter

    cpdef bint set_top_of_book_last_barter_px(self, float px):
        if self.top_of_book and self.top_of_book.last_barter:
            self.top_of_book.last_barter.px = px
            return True
        return False

    cpdef bint set_top_of_book_last_barter_qty(self, int qty):
        if self.top_of_book and self.top_of_book.last_barter:
            self.top_of_book.last_barter.qty = qty
            return True
        return False

    cpdef bint set_top_of_book_last_barter_premium(self, float premium):
        if self.top_of_book and self.top_of_book.last_barter:
            self.top_of_book.last_barter.premium = premium
            return True
        return False

    cpdef bint set_top_of_book_last_barter_last_update_date_time(self, object last_update_date_time):
        if self.top_of_book and self.top_of_book.last_barter:
            self.top_of_book.last_barter.last_update_date_time = last_update_date_time
            return True
        return False

    cpdef bint set_top_of_book_total_bartering_security_size(self, int64_t total_bartering_security_size):
        if self.top_of_book:
            self.top_of_book.total_bartering_security_size = total_bartering_security_size
            return True
        return False

    cpdef bint set_top_of_book_market_barter_volume(
            self, str _id, int64_t participation_period_last_barter_qty_sum,
            int32_t applicable_period_seconds):
        if self.top_of_book:
            if not self.top_of_book.market_barter_volume:
                self.top_of_book.market_barter_volume = []
                market_barter_volume = MarketBarterVolume(_id, participation_period_last_barter_qty_sum,
                                                        applicable_period_seconds)
                self.top_of_book.market_barter_volume.append(market_barter_volume)
                return True
            else:
                for existing_market_barter_volume in self.top_of_book.market_barter_volume:
                    if _id == existing_market_barter_volume._id:
                        logging.error(f"market_barter_volume object with _id: {_id} already exists in "
                                      f"stored list of market_barter_volume objects in top_of_book - ignoring "
                                      f"this update, use set  method for specific update instead")
                        return False
                else:
                    market_barter_volume = MarketBarterVolume(_id, participation_period_last_barter_qty_sum,
                                                            applicable_period_seconds)
                    self.top_of_book.market_barter_volume.append(market_barter_volume)
                    return True
        return False

    cpdef bint set_top_of_book_market_barter_volume_participation_period_last_barter_qty_sum(
            self, str _id, int64_t participation_period_last_barter_qty_sum):
        if self.top_of_book and self.top_of_book.market_barter_volume:
            for market_barter_volume in self.top_of_book.market_barter_volume:
                if market_barter_volume._id == _id:
                    market_barter_volume.participation_period_last_barter_qty_sum = (
                        participation_period_last_barter_qty_sum)
                    return True
        return False

    cpdef bint set_top_of_book_market_barter_volume_applicable_period_seconds(
            self, str _id, int32_t applicable_period_seconds):
        if self.top_of_book and self.top_of_book.market_barter_volume:
            for market_barter_volume in self.top_of_book.market_barter_volume:
                if market_barter_volume._id == _id:
                    market_barter_volume.applicable_period_seconds = applicable_period_seconds
                    return True
        return False

    cpdef bint set_top_of_book_last_update_date_time(self, object last_update_date_time):
        if self.top_of_book:
            self.top_of_book.last_update_date_time = last_update_date_time
            return True
        return False

    cpdef TopOfBook get_top_of_book(self, object date_time=None):
        if date_time is None or date_time < self.top_of_book.last_update_date_time:
            return self.top_of_book
        return None

    cpdef void print_tob_obj(self):
        tob_obj = self.top_of_book
        print_str = ""
        if tob_obj:
            print_str += f"TOB obj: {tob_obj._id}, symbol: {tob_obj.symbol}"
        if tob_obj.bid_quote:
            print_str += (f", Bid Quote: {tob_obj.bid_quote.px}, {tob_obj.bid_quote.qty}, "
                          f"{tob_obj.bid_quote.premium}, {tob_obj.bid_quote.last_update_date_time}")
        if tob_obj.ask_quote:
            print_str += (f", ASK Quote: {tob_obj.ask_quote.px}, {tob_obj.ask_quote.qty}, "
                          f"{tob_obj.ask_quote.premium}, {tob_obj.ask_quote.last_update_date_time}")
        if tob_obj.last_barter:
            print_str += (f", LastBarter Quote: {tob_obj.last_barter.px}, {tob_obj.last_barter.qty}, "
                          f"{tob_obj.last_barter.premium}, {tob_obj.last_barter.last_update_date_time}")
        print_str += f", total_bartering_security_size: {tob_obj.total_bartering_security_size}"
        if tob_obj.market_barter_volume:
            print_str += f", MarketBarterVolume: "
            for market_barter_vol in tob_obj.market_barter_volume:
                print_str += (f"id: {market_barter_vol._id}, participation_period_last_barter_qty_sum: "
                              f"{market_barter_vol.participation_period_last_barter_qty_sum}, applicable_period_seconds: "
                              f"{market_barter_vol.applicable_period_seconds}")
                if market_barter_vol != tob_obj.market_barter_volume[-1]:
                    print_str += ", "
        print_str += f", last_update_date_time: {tob_obj.last_update_date_time}"
        print(print_str)
        logging.info(print_str)

    cpdef bint set_last_barter(self, _id, str symbol, exch_id=None, exch_time=None, arrival_time=None, px=None, qty=None,
                             premium=None, MarketBarterVolume market_barter_volume=None):
        if self.last_barter is None:
            print(f"PY: id: {_id}, symbol: {symbol}")
            symbol_n_exch_id = SymbolNExchId(symbol, exch_id)
            self.last_barter = LastBarter(_id, symbol_n_exch_id, exch_time, arrival_time, px,
                                        qty, premium, market_barter_volume)
            print(f"self.last_barter [{self.last_barter}]")
            # print(f"PY: Created LastBarter with market_barter_vol: {market_barter_volume._id, market_barter_volume.participation_period_last_barter_qty_sum, market_barter_volume.applicable_period_seconds}")
            return True
        print(f"PY: LastBarter is already present in the container with symbol: {symbol}")
        return False

    cpdef bint set_last_barter_symbol(self, str symbol):
        if self.last_barter:
            self.last_barter.symbol_n_exch_id.symbol = symbol
            return True
        return False

    cpdef bint set_last_barter_exch_id(self, str exch_id):
        if self.last_barter:
            self.last_barter.symbol_n_exch_id.exch_id = exch_id
            return True
        return False

    cpdef bint set_last_barter_exch_time(self, object exch_time):
        if self.last_barter:
            self.last_barter.exch_time = exch_time
            return True
        return False

    cpdef bint set_last_barter_arrival_time(self, object arrival_time):
        if self.last_barter:
            self.last_barter.arrival_time = arrival_time
            return True
        return False

    cpdef bint set_last_barter_px(self, float px):
        if self.last_barter:
            self.last_barter.px = px
            return True
        return False

    cpdef bint set_last_barter_qty(self, int64_t qty):
        if self.last_barter:
            self.last_barter.qty = qty
            return True
        return False

    cpdef bint set_last_barter_premium(self, float premium):
        if self.last_barter:
            self.last_barter.premium = premium
            return True
        return False

    cpdef bint set_last_barter_market_barter_volume_participation_period_last_barter_qty_sum(
            self, int64_t participation_period_last_barter_qty_sum):
        if self.last_barter:
            self.last_barter.market_barter_volume.participation_period_last_barter_qty_sum = (
                participation_period_last_barter_qty_sum)
            return True
        return False

    cpdef bint set_last_barter_market_barter_volume_applicable_period_seconds(
            self, int64_t applicable_period_seconds):
        if self.last_barter:
            self.last_barter.market_barter_volume.applicable_period_seconds = applicable_period_seconds
            return True
        return False

    cpdef LastBarter get_last_barter(self):
        return self.last_barter

    cpdef void print_last_barter_obj(self):
        last_barter = self.last_barter
        print(f"LastBarter: _id: {last_barter._id}, symbol: {last_barter.symbol_n_exch_id.symbol}, "
              f"exch_id: {last_barter.symbol_n_exch_id.exch_id}, exch_time: {last_barter.exch_time}, "
              f"arrival_time: {last_barter.arrival_time}, px: {last_barter.px}, qty: {last_barter.qty}, "
              f"premium: {last_barter.premium}, market_barter_volume: _id: {last_barter.market_barter_volume._id}, "
              f"market_barter_volume: participation_period_last_barter_qty_sum: "
              f"{last_barter.market_barter_volume.participation_period_last_barter_qty_sum}, "
              f"market_barter_volume: applicable_period_seconds: "
              f"{last_barter.market_barter_volume.applicable_period_seconds}")

    cpdef bint check_has_allowed_bid_px(self, position, px):
        # Checking if passed px is less than px of market depth above current position
        # if found otherwise then avoiding this update and logging error
        if position != 0:
            market_depth_up_position = self.bid_market_depths[position - 1]
            if market_depth_up_position is not None and px > market_depth_up_position.px:
                logging.error(f"Unexpected: px passed must be less than above (position-1) bid market_depth's px"
                              f"but found otherwise - ignoring this update, up position px: "
                              f"{market_depth_up_position.px}, passed px: {px}")
                return False
        # else not required: Can't have market depth up position 0

        # Checking if passed px is greater than px of market depth below current position
        # if found otherwise then avoiding this update and logging error
        if position != 9:
            market_depth_below_position = self.bid_market_depths[position + 1]
            if market_depth_below_position is not None and px < market_depth_below_position.px:
                logging.error(f"Unexpected: px passed must be greater than below (position+1) bid market_depth's px"
                              f"but found otherwise - ignoring this update, below position px: "
                              f"{market_depth_below_position.px}, passed px: {px}")
                return False
        # else not required: Can't have market depth after position 9
        return True

    cpdef bint check_has_allowed_ask_px(self, position, px):
        # Checking if passed px is greater than px of market depth above current position
        # if found otherwise then avoiding this update and logging error
        if position != 0:
            market_depth_up_position = self.ask_market_depths[position - 1]
            if market_depth_up_position.px != 0.0:
                if market_depth_up_position is not None and px < market_depth_up_position.px:
                    logging.error(f"Unexpected: px passed must be greater than above (position-1) ask market_depth's px"
                                  f"but found otherwise - ignoring this update, up position px: "
                                  f"{market_depth_up_position.px}, passed px: {px}")
                    return False
        # else not required: Can't have market depth up position 0

        # Checking if passed px is less than px of market depth below current position
        # if found otherwise then avoiding this update and logging error
        if position != 9:
            market_depth_below_position = self.ask_market_depths[position + 1]
            if market_depth_below_position.px != 0.0:
                if market_depth_below_position is not None and px > market_depth_below_position.px:
                    logging.error(f"Unexpected: px passed must be less than below (position+1) ask market_depth's px"
                                  f"but found otherwise - ignoring this update, below position px: "
                                  f"{market_depth_below_position.px}, passed px: {px}")
                    return False
        # else not required: Can't have market depth after position 9
        return True

    cpdef bint check_no_market_depth_already_exists_on_position_and_has_allowed_px(
            self, market_depth_list, _id, symbol, exch_time, arrival_time, side, px, qty, position,
            market_maker=None, is_smart_depth=None, cumulative_notional=None,
            cumulative_qty=None, cumulative_avg_px=None):
        if market_depth_list[position] is not None:
            logging.error(f"Market Depth at position {position} already exists for side: {side}, "
                          f"ignoring this update - call update methods instead")
            return False

        if position > 9 or position < 0:
            logging.error("Unsupported: highest supported market depth is 9 starting from 0")
            return False

        if side == "BID" or side == TickType.BID:
            if not self.check_has_allowed_bid_px(position, px):
                logging.error("Unexpected: px is not allowed depending on bid position;;; passed args: "
                              f"{_id, symbol, exch_time, arrival_time, side, px, qty, position, market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px}")
                return False
        elif side == "ASK" or side == TickType.ASK:
            if not self.check_has_allowed_ask_px(position, px):
                logging.error("Unexpected: px is not allowed depending on ask position;;; passed args: "
                              f"{_id, symbol, exch_time, arrival_time, side, px, qty, position, market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px}")
                return False
        return True

    cpdef bint set_bid_market_depth(self, _id, symbol, exch_time=None, arrival_time=None, side=None, position=None,
                                    px=None, qty=None, market_maker=None, is_smart_depth=None,
                                    cumulative_notional=None, cumulative_qty=None, cumulative_avg_px=None):
        if self.check_no_market_depth_already_exists_on_position_and_has_allowed_px(
                self.bid_market_depths, _id, symbol, exch_time, arrival_time, side, px, qty, position,
                market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px):
            if side is None:
                side="BID"
            self.bid_market_depths[position] = (
                MarketDepth(_id, symbol, exch_time, arrival_time, side, position, px, qty,
                            market_maker, is_smart_depth, cumulative_notional,
                            cumulative_qty, cumulative_avg_px))
            return True
        return False

    cpdef bint set_ask_market_depth(self, _id, symbol, exch_time=None, arrival_time=None, side=None, position=None,
                                    px=None, qty=None, market_maker=None, is_smart_depth=None,
                                    cumulative_notional=None, cumulative_qty=None, cumulative_avg_px=None):
        if self.check_no_market_depth_already_exists_on_position_and_has_allowed_px(
                self.ask_market_depths, _id, symbol, exch_time, arrival_time, side, px, qty, position,
                market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px):
            if side is None:
                side="ASK"
            self.ask_market_depths[position] = (
                MarketDepth(_id, symbol, exch_time, arrival_time, side, position, px, qty,
                            market_maker, is_smart_depth, cumulative_notional,
                            cumulative_qty, cumulative_avg_px))
            return True
        return False

    cpdef bint remove_bid_market_depth_from_position(self, int position):
        self.bid_market_depths[position] = None
        return True

    cpdef bint remove_ask_market_depth_from_position(self, int position):
        self.ask_market_depths[position] = None
        return True

    cpdef bint set_bid_market_depth_symbol(self, int32_t position, str symbol):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.symbol = symbol
            return True
        return False

    cpdef bint set_ask_market_depth_symbol(self, int32_t position, str symbol):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.symbol = symbol
            return True
        return False

    cpdef bint set_bid_market_depth_exch_time(self, int32_t position, object exch_time):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.exch_time = exch_time
            return True
        return False

    cpdef bint set_ask_market_depth_exch_time(self, int32_t position, object exch_time):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.exch_time = exch_time
            return True
        return False

    cpdef bint set_bid_market_depth_arrival_time(self, int32_t position, object arrival_time):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.arrival_time = arrival_time
            return True
        return False

    cpdef bint set_ask_market_depth_arrival_time(self, int32_t position, object arrival_time):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.arrival_time = arrival_time
            return True
        return False

    cpdef bint set_bid_market_depth_side(self, int32_t position, str side):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            print(f"PY: side: - {side}")
            market_depth.side = TickType.BID if side == "BID" else TickType.ASK
            return True
        return False

    cpdef bint set_ask_market_depth_side(self, int32_t position, str side):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.side = TickType.BID if side == "BID" else TickType.ASK
            return True
        return False

    cpdef bint set_bid_market_depth_qty(self, int32_t position, int32_t qty):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.qty = qty
            return True
        return False

    cpdef bint set_ask_market_depth_qty(self, int32_t position, int32_t qty):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.qty = qty
            return True
        return False

    cpdef bint set_bid_market_depth_px(self, int32_t position, float px):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            if self.check_has_allowed_bid_px(position, px):
                market_depth.px = px
                return True
        return False

    cpdef bint set_ask_market_depth_px(self, int32_t position, float px):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            if self.check_has_allowed_ask_px(position, px):
                market_depth.px = px
                return True
        return False

    cpdef bint set_bid_market_depth_market_maker(self, int32_t position, str market_maker):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.market_maker = market_maker
            return True
        return False

    cpdef bint set_ask_market_depth_market_maker(self, int32_t position, str market_maker):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.market_maker = market_maker
            return True
        return False

    cpdef bint set_bid_market_depth_is_smart_depth(self, int32_t position, bint is_smart_depth):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.is_smart_depth = is_smart_depth
            return True
        return False

    cpdef bint set_ask_market_depth_is_smart_depth(self, int32_t position, bint is_smart_depth):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.is_smart_depth = is_smart_depth
            return True
        return False

    cpdef bint set_bid_market_depth_cumulative_notional(self, int32_t position, float cumulative_notional):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_notional = cumulative_notional
            return True
        return False

    cpdef bint set_ask_market_depth_cumulative_notional(self, int32_t position, float cumulative_notional):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_notional = cumulative_notional
            return True
        return False

    cpdef bint set_bid_market_depth_cumulative_qty(self, int32_t position, int64_t cumulative_qty):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_qty = cumulative_qty
            return True
        return False

    cpdef bint set_ask_market_depth_cumulative_qty(self, int32_t position, int64_t cumulative_qty):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_qty = cumulative_qty
            return True
        return False

    cpdef bint set_bid_market_depth_cumulative_avg_px(self, int32_t position, float cumulative_avg_px):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_avg_px = cumulative_avg_px
            return True
        return False

    cpdef bint set_ask_market_depth_cumulative_avg_px(self, int32_t position, float cumulative_avg_px):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.cumulative_avg_px = cumulative_avg_px
            return True
        return False

    cpdef list get_bid_market_depths(self):
        return self.bid_market_depths

    cpdef list get_ask_market_depths(self):
        return self.ask_market_depths

    cpdef MarketDepth get_bid_market_depth_from_depth(self, int depth):
        if depth > 9 or depth < 0:
            logging.error(f"Unsupported depth: {depth} - must be between 0-9")
            return None
        return self.bid_market_depths[depth]

    cpdef MarketDepth get_ask_market_depth_from_depth(self, int depth):
        if depth > 9 or depth < 0:
            logging.error(f"Unsupported depth: {depth} - must be between 0-9")
            return None
        return self.ask_market_depths[depth]

    cpdef void print_bid_market_depth_obj(self):
        print("BID MarketDepth:")
        for market_depth in self.bid_market_depths:
            if market_depth is not None:
                print(f"_id: {market_depth._id}, symbol: {market_depth.symbol}, exch_time: {market_depth.exch_time}, "
                      f"arrival_time: {market_depth.arrival_time}, side: {market_depth.side}, px: {market_depth.px}, "
                      f"qty: {market_depth.qty}, position: {market_depth.position}")

    cpdef void print_ask_market_depth_obj(self):
        print("ASK MarketDepth:")
        for market_depth in self.ask_market_depths:
            if market_depth is not None:
                print(f"_id: {market_depth._id}, symbol: {market_depth.symbol}, exch_time: {market_depth.exch_time}, "
                      f"arrival_time: {market_depth.arrival_time}, side: {market_depth.side}, px: {market_depth.px}, "
                      f"qty: {market_depth.qty}, position: {market_depth.position}")

cdef list container_obj_list_cache = []
cdef dict symbol_to_container_obj_index_dict = {}

cpdef MobileBookContainer add_container_obj_for_symbol(str symbol):
    mobile_book_container = symbol_to_container_obj_index_dict.get(symbol)
    if  mobile_book_container is None:
        mobile_book_container = MobileBookContainer(symbol)
        container_obj_list_cache.append(mobile_book_container)

        index = container_obj_list_cache.index(mobile_book_container)
        symbol_to_container_obj_index_dict[symbol] = index

        print(f"Added Container Obj at index: {index} < symbol: {symbol}")

        return mobile_book_container
    else:
        return mobile_book_container



cpdef MobileBookContainer get_mobile_book_container(str symbol):
    index = symbol_to_container_obj_index_dict.get(symbol)
    if index is not None:
        return container_obj_list_cache[index]
    return None

cpdef int get_index_for_mobile_book_container_obj_for_symbol(str symbol):
    index = symbol_to_container_obj_index_dict.get(symbol)
    return index

cpdef MobileBookContainer get_mobile_book_container_obj_from_index(int index):
    if len(container_obj_list_cache)-1 >= index:
        return container_obj_list_cache[index]
    logging.error(f"Index {index} not found in container_obj_list_cache")
    return None

# todo: Todos when this file is generated:
# add logging when any set method returns False
