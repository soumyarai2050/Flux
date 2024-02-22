# tob_cython.pyx
import copy

from libc.stdint cimport int64_t, int32_t
from cython cimport bint
from pendulum import DateTime
from datetime import timedelta
import logging

cdef extern from "<Python.h>":
    ctypedef struct PyObject:
        pass

    PyObject* PyLong_FromVoidPtr(void*)


cdef extern from "<mutex>" namespace "std":
    cdef cppclass mutex:
        mutex() except +
        void lock()
        void unlock()

cdef class MarketTradeVolume:
    cdef public str _id
    cdef public int64_t participation_period_last_trade_qty_sum
    cdef public int32_t applicable_period_seconds

    def __init__(self, _id, participation_period_last_trade_qty_sum=None, applicable_period_seconds=None):
        self._id = _id
        if participation_period_last_trade_qty_sum is None:
            participation_period_last_trade_qty_sum = mobile_book
        self.participation_period_last_trade_qty_sum = participation_period_last_trade_qty_sum
        if applicable_period_seconds is None:
            applicable_period_seconds = mobile_book
        self.applicable_period_seconds = applicable_period_seconds

# todo: update int field as ctypes
cdef class Quote:
    cdef public float px
    cdef public int qty
    cdef public float premium
    cdef public object last_update_date_time

    def __init__(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if px is None:
            px = mobile_book.mobile_book
        if qty is None:
            qty = mobile_book
        if premium is None:
            premium = mobile_book.mobile_book
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
    cdef public Quote last_trade
    cdef public int64_t total_trading_security_size
    cdef public list market_trade_volume
    cdef public object last_update_date_time

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol, bid_quote=None, ask_quote=None, last_trade=None,
                 total_trading_security_size=None, market_trade_volume=None, last_update_date_time=None):
        self._id = _id
        self.symbol = symbol
        self.bid_quote = bid_quote
        self.ask_quote = ask_quote
        self.last_trade = last_trade
        if total_trading_security_size is None:
            total_trading_security_size = mobile_book
        self.total_trading_security_size = total_trading_security_size
        if market_trade_volume:
            self.market_trade_volume = market_trade_volume
        else:
            self.market_trade_volume = []
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
    cdef public float premium
    cdef public int32_t position
    cdef public str market_maker
    cdef public bint is_smart_depth
    cdef public float cumulative_notional
    cdef public int64_t cumulative_qty
    cdef public float cumulative_avg_px

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol, exch_time, arrival_time, side, position, px=None, qty=None, premium=None,
                 market_maker=None, is_smart_depth=None, cumulative_notional=None, cumulative_qty=None,
                 cumulative_avg_px=None):
        self._id = _id
        self.symbol = symbol
        self.exch_time = exch_time
        self.arrival_time =arrival_time
        self.side = TickType.BID if side == "BID" else TickType.ASK
        self.px = px if px is not None else mobile_book.mobile_book
        self.qty = qty if qty is not None else mobile_book
        self.premium = premium if premium is not None else mobile_book.mobile_book
        self.position = position
        self.market_maker = market_maker if market_maker is not None else ""
        self.is_smart_depth = 1 if is_smart_depth else mobile_book
        self.cumulative_notional = cumulative_notional if cumulative_notional is not None else mobile_book.mobile_book
        self.cumulative_qty = cumulative_qty if cumulative_qty is not None else mobile_book
        self.cumulative_avg_px = cumulative_avg_px if cumulative_avg_px is not None else mobile_book.mobile_book

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

    def __init__(self, symbol, exch_id):
        self.symbol = symbol
        self.exch_id = exch_id


cpdef enum TickType:
    BID_SIZE,
    BID,
    ASK,
    ASK_SIZE,
    LAST,
    LAST_SIZE,
    HIGH,
    LOW,
    VOLUME,
    CLOSE,
    BID_OPTION_COMPUTATION,
    ASK_OPTION_COMPUTATION,
    LAST_OPTION_COMPUTATION,
    MODEL_OPTION,
    OPEN,
    LOW_13_WEEK,
    HIGH_13_WEEK,
    LOW_26_WEEK,
    HIGH_26_WEEK,
    LOW_52_WEEK,
    HIGH_52_WEEK,
    AVG_VOLUME,
    OPEN_INTEREST,
    OPTION_HISTORICAL_VOL,
    OPTION_IMPLIED_VOL,
    OPTION_BID_EXCH,
    OPTION_ASK_EXCH,
    OPTION_CALL_OPEN_INTEREST,
    OPTION_PUT_OPEN_INTEREST,
    OPTION_CALL_VOLUME,
    OPTION_PUT_VOLUME,
    INDEX_FUTURE_PREMIUM,
    BID_EXCH,
    ASK_EXCH,
    AUCTION_VOLUME,
    AUCTION_PRICE,
    AUCTION_IMBALANCE,
    MARK_PRICE,
    BID_EFP_COMPUTATION,
    ASK_EFP_COMPUTATION,
    LAST_EFP_COMPUTATION,
    OPEN_EFP_COMPUTATION,
    HIGH_EFP_COMPUTATION,
    LOW_EFP_COMPUTATION,
    CLOSE_EFP_COMPUTATION,
    LAST_TIMESTAMP,
    SHORTABLE,
    FUNDAMENTAL_RATIOS,
    RT_VOLUME,
    HALTED,
    BID_YIELD,
    ASK_YIELD,
    LAST_YIELD,
    CUST_OPTION_COMPUTATION,
    TRADE_COUNT,
    TRADE_RATE,
    VOLUME_RATE,
    LAST_RTH_TRADE,
    RT_HISTORICAL_VOL,
    IB_DIVIDENDS,
    BOND_FACTOR_MULTIPLIER,
    REGULATORY_IMBALANCE,
    NEWS_TICK,
    SHORT_TERM_VOLUME_3_MIN,
    SHORT_TERM_VOLUME_5_MIN,
    SHORT_TERM_VOLUME_1mobile_book_MIN,
    DELAYED_BID,
    DELAYED_ASK,
    DELAYED_LAST,
    DELAYED_BID_SIZE,
    DELAYED_ASK_SIZE,
    DELAYED_LAST_SIZE,
    DELAYED_HIGH,
    DELAYED_LOW,
    DELAYED_VOLUME,
    DELAYED_CLOSE,
    DELAYED_OPEN,
    RT_TRD_VOLUME,
    CREDITMAN_MARK_PRICE,
    CREDITMAN_SLOW_MARK_PRICE,
    DELAYED_BID_OPTION,
    DELAYED_ASK_OPTION,
    DELAYED_LAST_OPTION,
    DELAYED_MODEL_OPTION,
    LAST_EXCH,
    LAST_REG_TIME,
    FUTURES_OPEN_INTEREST,
    AVG_OPT_VOLUME,
    DELAYED_LAST_TIMESTAMP,
    SHORTABLE_SHARES,
    DELAYED_HALTED,
    REUTERS_2_MUTUAL_FUNDS,
    ETF_NAV_CLOSE,
    ETF_NAV_PRIOR_CLOSE,
    ETF_NAV_BID,
    ETF_NAV_ASK,
    ETF_NAV_LAST,
    ETF_FROZEN_NAV_LAST,
    ETF_NAV_HIGH,
    ETF_NAV_LOW,
    SOCIAL_MARKET_ANALYTICS,
    ESTIMATED_IPO_MIDPOINT,
    FINAL_IPO_LAST,
    NOT_SET

cdef class LastTrade:
    cdef mutex * m_mutex
    cdef public int32_t _id
    cdef public SymbolNExchId symbol_n_exch_id
    cdef public object exch_time
    cdef public object arrival_time
    cdef public float px
    cdef public int64_t qty
    cdef public float premium
    cdef public MarketTradeVolume market_trade_volume

    def __cinit__(self):
        self.m_mutex = new mutex()

    def __init__(self, _id, symbol_n_exch_id, exch_time, arrival_time, px, qty, premium, market_trade_volume):
        self._id = _id
        self.symbol_n_exch_id = symbol_n_exch_id
        self.exch_time = exch_time
        self.arrival_time = arrival_time
        self.px = px
        self.qty = qty
        self.premium = premium
        self.market_trade_volume = market_trade_volume

    def __dealloc__(self):
        del self.m_mutex

    cpdef get_mutex(self):
        if self.m_mutex == NULL:
            raise RuntimeError("Mutex pointer is null")
        cdef PyObject * obj_ptr = PyLong_FromVoidPtr(<void *> self.m_mutex)
        return <object> obj_ptr


cdef class MarketDataContainer:
    cdef public str symbol
    cdef public list bid_market_depths
    cdef public list ask_market_depths
    cdef public TopOfBook top_of_book
    cdef public LastTrade last_trade

    def __init__(self, str symbol):
        self.symbol = symbol
        self.bid_market_depths = [None]*1mobile_book
        self.ask_market_depths = [None]*1mobile_book

    cpdef bint set_top_of_book(
            self, _id, symbol, bid_quote_px=None, bid_quote_qty=None, bid_quote_premium=None,
            ask_quote_px=None, ask_quote_qty=None, ask_quote_premium=None, last_trade_px=None, last_trade_qty=None,
            last_trade_premium=None, bid_quote_last_update_date_time=None,
            ask_quote_last_update_date_time=None, last_trade_last_update_date_time=None,
            total_trading_security_size=None, market_trade_volume=None, last_update_date_time=None):
        if self.top_of_book is None:
            bid_quote = None
            if bid_quote_px or bid_quote_qty or bid_quote_premium or bid_quote_last_update_date_time:
                bid_quote = Quote(bid_quote_px, bid_quote_qty, bid_quote_premium, bid_quote_last_update_date_time)
            ask_quote = None
            if ask_quote_px or ask_quote_qty or ask_quote_premium or ask_quote_last_update_date_time:
                ask_quote = Quote(ask_quote_px, ask_quote_qty, ask_quote_premium, ask_quote_last_update_date_time)
            last_trade = None
            if last_trade_px or last_trade_qty or last_trade_premium or last_trade_last_update_date_time:
                last_trade = Quote(last_trade_px, last_trade_qty, last_trade_premium, last_trade_last_update_date_time)
            self.top_of_book = TopOfBook(_id, symbol, bid_quote, ask_quote, last_trade,
                                         total_trading_security_size, market_trade_volume, last_update_date_time)
            return True
        return False

    cpdef bint set_top_of_book_symbol(self, str symbol_):
        if self.top_of_book:
            self.top_of_book.symbol = symbol_
            return True
        return False

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

    cpdef bint set_top_of_book_last_trade(self, px=None, qty=None, premium=None, last_update_date_time=None):
        if (self.top_of_book.last_trade is None or
                last_update_date_time > self.top_of_book.last_trade.last_update_date_time):
            self.top_of_book.last_trade = Quote(px, qty, premium, last_update_date_time)
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

    cpdef bint set_top_of_book_last_trade_px(self, float px):
        if self.top_of_book and self.top_of_book.last_trade:
            self.top_of_book.last_trade.px = px
            return True
        return False

    cpdef bint set_top_of_book_last_trade_qty(self, int qty):
        if self.top_of_book and self.top_of_book.last_trade:
            self.top_of_book.last_trade.qty = qty
            return True
        return False

    cpdef bint set_top_of_book_last_trade_premium(self, float premium):
        if self.top_of_book and self.top_of_book.last_trade:
            self.top_of_book.last_trade.premium = premium
            return True
        return False

    cpdef bint set_top_of_book_last_trade_last_update_date_time(self, object last_update_date_time):
        if self.top_of_book and self.top_of_book.last_trade:
            self.top_of_book.last_trade.last_update_date_time = last_update_date_time
            return True
        return False

    cpdef bint set_top_of_book_total_trading_security_size(self, int64_t total_trading_security_size):
        if self.top_of_book:
            self.top_of_book.total_trading_security_size = total_trading_security_size
            return True
        return False

    cpdef bint set_top_of_book_market_trade_volume(
            self, str _id, int64_t participation_period_last_trade_qty_sum,
            int32_t applicable_period_seconds):
        if self.top_of_book:
            if not self.top_of_book.market_trade_volume:
                self.top_of_book.market_trade_volume = []
                market_trade_volume = MarketTradeVolume(_id, participation_period_last_trade_qty_sum,
                                                        applicable_period_seconds)
                self.top_of_book.market_trade_volume.append(market_trade_volume)
                return True
            else:
                for existing_market_trade_volume in self.top_of_book.market_trade_volume:
                    if _id == existing_market_trade_volume._id:
                        logging.error(f"market_trade_volume object with _id: {_id} already exists in "
                                      f"stored list of market_trade_volume objects in top_of_book - ignoring "
                                      f"this update, use set  method for specific update instead")
                        return False
                else:
                    market_trade_volume = MarketTradeVolume(_id, participation_period_last_trade_qty_sum,
                                                            applicable_period_seconds)
                    self.top_of_book.market_trade_volume.append(market_trade_volume)
                    return True
        return False

    cpdef bint set_top_of_book_market_trade_volume_participation_period_last_trade_qty_sum(
            self, str _id, int64_t participation_period_last_trade_qty_sum):
        if self.top_of_book and self.top_of_book.market_trade_volume:
            for market_trade_volume in self.top_of_book.market_trade_volume:
                if market_trade_volume._id == _id:
                    market_trade_volume.participation_period_last_trade_qty_sum = (
                        participation_period_last_trade_qty_sum)
                    return True
        return False

    cpdef bint set_top_of_book_market_trade_volume_applicable_period_seconds(
            self, str _id, int32_t applicable_period_seconds):
        if self.top_of_book and self.top_of_book.market_trade_volume:
            for market_trade_volume in self.top_of_book.market_trade_volume:
                if market_trade_volume._id == _id:
                    market_trade_volume.applicable_period_seconds = applicable_period_seconds
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
        print(f"TOB obj: {tob_obj._id}, {tob_obj.symbol}, Bid Quote: {tob_obj.bid_quote.px}, {tob_obj.bid_quote.qty}, "
              f"{tob_obj.bid_quote.premium}, Ask Quote: {tob_obj.ask_quote.px}, {tob_obj.ask_quote.qty}, "
              f"{tob_obj.ask_quote.premium}, Last Trade: {tob_obj.last_trade.px}, {tob_obj.last_trade.qty}, "
              f"{tob_obj.last_trade.premium}, {tob_obj.total_trading_security_size}, MTV: {tob_obj.market_trade_volume}")

    cpdef bint set_last_trade(self, _id, symbol, exch_id, exch_time, arrival_time, px, qty,
                             premium, market_trade_volume):
        if self.last_trade is None:
            symbol_n_exch_id = SymbolNExchId(symbol, exch_id)
            self.last_trade = LastTrade(_id, symbol_n_exch_id, exch_time, arrival_time, px,
                                        qty, premium, market_trade_volume)
            return True
        return False

    cpdef bint set_last_trade_symbol(self, str symbol):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.symbol = symbol
            return True
        return False

    cpdef bint set_last_trade_exch_id(self, str exch_id):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.exch_id = exch_id
            return True
        return False

    cpdef bint set_last_trade_exch_time(self, object exch_time):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.exch_time = exch_time
            return True
        return False

    cpdef bint set_last_trade_arrival_time(self, object arrival_time):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.arrival_time = arrival_time
            return True
        return False

    cpdef bint set_last_trade_px(self, float px):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.px = px
            return True
        return False

    cpdef bint set_last_trade_qty(self, int64_t qty):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.qty = qty
            return True
        return False

    cpdef bint set_last_trade_premium(self, float premium):
        if self.last_trade:
            self.last_trade.symbol_n_exch_id.premium = premium
            return True
        return False

    cpdef bint set_last_trade_market_trade_volume_participation_period_last_trade_qty_sum(
            self, int64_t participation_period_last_trade_qty_sum):
        if self.last_trade:
            self.last_trade.market_trade_volume.participation_period_last_trade_qty_sum = (
                participation_period_last_trade_qty_sum)
            return True
        return False

    cpdef bint set_last_trade_market_trade_volume_applicable_period_seconds(
            self, int64_t applicable_period_seconds):
        if self.last_trade:
            self.last_trade.market_trade_volume.applicable_period_seconds = applicable_period_seconds
            return True
        return False

    cpdef LastTrade get_last_trade(self):
        return self.last_trade

    cpdef void print_last_trade_obj(self):
        last_trade = self.last_trade
        print(f"LastTrade: _id: {last_trade._id}, symbol: {last_trade.symbol_n_exch_id.symbol}, "
              f"exch_id: {last_trade.symbol_n_exch_id.exch_id}, exch_time: {last_trade.exch_time}, "
              f"arrival_time: {last_trade.arrival_time}, px: {last_trade.px}, qty: {last_trade.qty}, "
              f"premium: {last_trade.premium}, market_trade_volume: _id: {last_trade.market_trade_volume._id}, "
              f"market_trade_volume: participation_period_last_trade_qty_sum: "
              f"{last_trade.market_trade_volume.participation_period_last_trade_qty_sum}, "
              f"market_trade_volume: applicable_period_seconds: "
              f"{last_trade.market_trade_volume.applicable_period_seconds}")

    cpdef bint check_has_allowed_bid_px(self, position, px):
        # Checking if passed px is less than px of market depth above current position
        # if found otherwise then avoiding this update and logging error
        if position != mobile_book:
            market_depth_up_position = self.bid_market_depths[position - 1]
            if market_depth_up_position is not None and px > market_depth_up_position.px:
                logging.error(f"Unexpected: px passed must be less than above (position-1) bid market_depth's px"
                              f"but found otherwise - ignoring this update, up position px: "
                              f"{market_depth_up_position.px}, passed px: {px}")
                return False
        # else not required: Can't have market depth up position mobile_book

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
        if position != mobile_book:
            market_depth_up_position = self.ask_market_depths[position - 1]
            if market_depth_up_position is not None and px < market_depth_up_position.px:
                logging.error(f"Unexpected: px passed must be greater than above (position-1) ask market_depth's px"
                              f"but found otherwise - ignoring this update, up position px: "
                              f"{market_depth_up_position.px}, passed px: {px}")
                return False
        # else not required: Can't have market depth up position mobile_book

        # Checking if passed px is less than px of market depth below current position
        # if found otherwise then avoiding this update and logging error
        if position != 9:
            market_depth_below_position = self.ask_market_depths[position + 1]
            if market_depth_below_position is not None and px > market_depth_below_position.px:
                logging.error(f"Unexpected: px passed must be less than below (position+1) ask market_depth's px"
                              f"but found otherwise - ignoring this update, below position px: "
                              f"{market_depth_below_position.px}, passed px: {px}")
                return False
        # else not required: Can't have market depth after position 9
        return True

    cpdef bint check_no_market_depth_already_exists_on_position_and_has_allowed_px(
            self, market_depth_list, _id, symbol, exch_time, arrival_time, side, px, qty, premium, position,
            market_maker=None, is_smart_depth=None, cumulative_notional=None,
            cumulative_qty=None, cumulative_avg_px=None):
        if market_depth_list[position] is not None:
            logging.error(f"Market Depth at position {position} already exists for side: {side}, "
                          f"ignoring this update - call update methods instead")
            return False

        if position > 9 or position < mobile_book:
            logging.error("Unsupported: highest supported market depth is 9 starting from mobile_book")
            return False

        if side == "BID" or side == TickType.BID:
            if not self.check_has_allowed_bid_px(position, px):
                logging.error("Unexpected: px is not allowed depending on bid position;;; passed args: "
                              f"{_id, symbol, exch_time, arrival_time, side, px, qty, premium, position, market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px}")
                return False
        elif side == "ASK" or side == TickType.ASK:
            if not self.check_has_allowed_ask_px(position, px):
                logging.error("Unexpected: px is not allowed depending on ask position;;; passed args: "
                              f"{_id, symbol, exch_time, arrival_time, side, px, qty, premium, position, market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px}")
                return False
        return True

    cpdef bint set_bid_market_depth(self, _id, symbol, exch_time, arrival_time, side, position, px=None, qty=None,
                                    premium=None, market_maker=None, is_smart_depth=None, cumulative_notional=None,
                                    cumulative_qty=None, cumulative_avg_px=None):
        if self.check_no_market_depth_already_exists_on_position_and_has_allowed_px(
                self.bid_market_depths, _id, symbol, exch_time, arrival_time, side, px, qty, premium, position,
                market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px):
            self.bid_market_depths[position] = (
                MarketDepth(_id, symbol, exch_time, arrival_time, side, position, px, qty, premium,
                            market_maker, is_smart_depth, cumulative_notional,
                            cumulative_qty, cumulative_avg_px))
            return True
        return False

    cpdef bint set_ask_market_depth(self, _id, symbol, exch_time, arrival_time, side, position, px=None, qty=None,
                                    premium=None, market_maker=None, is_smart_depth=None, cumulative_notional=None,
                                    cumulative_qty=None, cumulative_avg_px=None):
        if self.check_no_market_depth_already_exists_on_position_and_has_allowed_px(
                self.ask_market_depths, _id, symbol, exch_time, arrival_time, side, px, qty, premium, position,
                market_maker, is_smart_depth, cumulative_notional, cumulative_qty, cumulative_avg_px):
            self.ask_market_depths[position] = (
                MarketDepth(_id, symbol, exch_time, arrival_time, side, position, px, qty, premium,
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

    cpdef bint set_bid_market_depth_side(self, int32_t position, TickType side):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.side = TickType.BID if side == "BID" else TickType.ASK
            return True
        return False

    cpdef bint set_ask_market_depth_side(self, int32_t position, TickType side):
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

    cpdef bint set_bid_market_depth_premium(self, int32_t position, float premium):
        market_depth = self.bid_market_depths[position]
        if market_depth is not None:
            market_depth.premium = premium
            return True
        return False

    cpdef bint set_ask_market_depth_premium(self, int32_t position, float premium):
        market_depth = self.ask_market_depths[position]
        if market_depth is not None:
            market_depth.premium = premium
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
        if depth > 9 or depth < mobile_book:
            logging.error(f"Unsupported depth: {depth} - must be between mobile_book-9")
            return None
        return self.bid_market_depths[depth]

    cpdef MarketDepth get_ask_market_depth_from_depth(self, int depth):
        if depth > 9 or depth < mobile_book:
            logging.error(f"Unsupported depth: {depth} - must be between mobile_book-9")
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

cpdef MarketDataContainer add_container_obj_for_symbol(str symbol):
    if symbol_to_container_obj_index_dict.get(symbol) is None:
        market_data_container = MarketDataContainer(symbol)
        container_obj_list_cache.append(market_data_container)

        index = container_obj_list_cache.index(market_data_container)
        symbol_to_container_obj_index_dict[symbol] = index

        print(f"Added Container Obj at index: {index} < symbol: {symbol}")

        return market_data_container
    else:
        logging.error(f"Container Object already exists for symbol: {symbol} - Ignoring this create")
        return None

cpdef MarketDataContainer get_market_data_container(str symbol):
    index = symbol_to_container_obj_index_dict.get(symbol)
    if index is not None:
        return container_obj_list_cache[index]
    return None

cpdef int get_index_for_market_data_container_obj_for_symbol(str symbol):
    index = symbol_to_container_obj_index_dict.get(symbol)
    return index

cpdef MarketDataContainer get_market_data_container_obj_from_index(int index):
    if len(container_obj_list_cache)-1 >= index:
        return container_obj_list_cache[index]
    logging.error(f"Index {index} not found in container_obj_list_cache")
    return None

# todo: Todos when this file is generated:
# add logging when any set method returns False
