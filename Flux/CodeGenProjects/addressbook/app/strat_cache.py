import logging
from threading import RLock, Lock, Semaphore
from typing import Dict, Tuple, Optional, ClassVar
import copy

import pytz
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.app.service_state import ServiceState
from Flux.CodeGenProjects.addressbook.app.ws_helper import *


class MarketDepthsCont:
    def __init__(self, symbol: str):
        self.symbol: str = symbol
        self.bid_market_depths: List[MarketDepthBaseModel] = []
        self.ask_market_depths: List[MarketDepthBaseModel] = []

    def get_market_depths(self, side: Side):
        if side == Side.BUY:
            return self.bid_market_depths
        elif side == Side.SELL:
            return self.ask_market_depths
        else:
            logging.error(f"get_market_depths: Unsupported Side requested: {side}, returning empty list")
            return []

    def set_market_depth(self, market_depth: MarketDepthBaseModel):
        if market_depth.side == TickTypeEnum.BID:
            for bid_market_depth in self.bid_market_depths:
                if bid_market_depth.position == market_depth.position:
                    bid_market_depth = market_depth
            else:
                self.bid_market_depths.append(market_depth)
        elif market_depth.side == TickTypeEnum.ASK:
            for ask_market_depth in self.ask_market_depths:
                if ask_market_depth.position == market_depth.position:
                    ask_market_depth = market_depth
            else:
                self.ask_market_depths.append(market_depth)


class StratCache:
    add_to_strat_cache_rlock: RLock = RLock()

    @staticmethod
    def get_key_from_order_snapshot(order_snapshot: OrderSnapshotBaseModel):
        key: str | None = None
        if order_snapshot.order_brief.security.sec_id is not None and \
                order_snapshot.order_brief.side == Side.BUY:
            key = order_snapshot.order_brief.security.sec_id + "_BID"
        elif order_snapshot.order_brief.security.sec_id is not None and \
                order_snapshot.order_brief.side == Side.SELL:
            key = order_snapshot.order_brief.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_cancel_order(cancel_order: CancelOrderBaseModel):
        key: str | None = None
        if cancel_order.security.sec_id is not None and \
                cancel_order.side == Side.BUY:
            key = cancel_order.security.sec_id + "_BID"
        elif cancel_order.security.sec_id is not None and \
                cancel_order.side == Side.SELL:
            key = cancel_order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_new_order(new_order: NewOrderBaseModel):
        key: str | None = None
        if new_order.security.sec_id is not None and \
                new_order.side == Side.BUY:
            key = new_order.security.sec_id + "_BID"
        elif new_order.security.sec_id is not None and \
                new_order.side == Side.SELL:
            key = new_order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_order_journal(order_journal: OrderJournalBaseModel):
        key: str | None = None
        if order_journal.order.security.sec_id is not None and \
                order_journal.order.side == Side.BUY:
            key = order_journal.order.security.sec_id + "_BID"
        elif order_journal.order.security.sec_id is not None and \
                order_journal.order.side == Side.SELL:
            key = order_journal.order.security.sec_id + "_ASK"
        # else not required - returning None (default value of key)
        return key

    @staticmethod
    def get_key_from_strat_brief(strat_brief: StratBriefBaseModel):
        key1: str | None = None
        if strat_brief.pair_buy_side_trading_brief.security.sec_id is not None:
            key1 = strat_brief.pair_buy_side_trading_brief.security.sec_id + "_BID"
        else:
            raise Exception(f"get_key_from_strat_brief: did not find buy sec id;;; strat_brief: {strat_brief}")
        # else not required - returning None (default value of key)
        key2: str | None = None
        if strat_brief.pair_sell_side_trading_brief.security.sec_id is not None:
            key2 = strat_brief.pair_sell_side_trading_brief.security.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_strat_brief: did not find sell sec id;;; strat_brief: {strat_brief}")
        # else not required - returning None (default value of key)
        return key1, key2

    @staticmethod
    def get_key_from_pair_strat(pair_strat: PairStratBaseModel):
        key1: str | None = None
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id is not None:
            if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
                key1 = pair_strat.pair_strat_params.strat_leg1.sec.sec_id + "_BID"
            elif pair_strat.pair_strat_params.strat_leg1.side == Side.SELL:
                key1 = pair_strat.pair_strat_params.strat_leg1.sec.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_pair_strat: did not find leg1 sec id;;; pair_strat: {pair_strat}")
        key2: str | None = None
        if pair_strat.pair_strat_params.strat_leg2.sec.sec_id is not None:
            if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:
                key2 = pair_strat.pair_strat_params.strat_leg2.sec.sec_id + "_BID"
            elif pair_strat.pair_strat_params.strat_leg2.side == Side.SELL:
                key2 = pair_strat.pair_strat_params.strat_leg2.sec.sec_id + "_ASK"
        else:
            raise Exception(f"get_key_from_pair_strat: did not find leg2 sec id;;; pair_strat: {pair_strat}")
        return key1, key2

    @staticmethod
    def get_key_from_symbol_overview(symbol_overview_: SymbolOverviewBaseModel):
        return (symbol_overview_.symbol + "_BID"), (symbol_overview_.symbol + "_ASK")

    @staticmethod
    def get_key_from_top_of_book(top_of_book: TopOfBookBaseModel) -> Tuple[str, str]:
        return (top_of_book.symbol + "_BID"), (top_of_book.symbol + "_ASK")

    def get_pair_strat(self, date_time: DateTime | None = None) -> Tuple[PairStratBaseModel, DateTime] | None:
        if date_time is None or date_time < self._pair_strat_update_date_time:
            if self._pair_strat is not None:
                return self._pair_strat, self._pair_strat_update_date_time
            else:
                return None
        else:
            return None

    def get_trading_symbols(self):
        primary_ticker = self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        secondary_ticker = self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        return primary_ticker, secondary_ticker

    # pass None to remove pair strat
    def set_pair_strat(self, pair_strat: PairStratBaseModel | None) -> DateTime:
        self._pair_strat = pair_strat
        self._pair_strat_update_date_time = DateTime.utcnow()
        if self._pair_strat is not None:
            self.leg1_trading_symbol, self.leg2_trading_symbol = self.get_trading_symbols()
        # else not required: passing None to clear pair_strat form cache is valid
        return self._pair_strat_update_date_time

    def get_strat_brief(self, date_time: DateTime | None = None) -> Tuple[StratBriefBaseModel, DateTime] | None:
        if date_time is None or date_time < self._strat_brief_update_date_time:
            if self._strat_brief is not None:
                return self._strat_brief, self._strat_brief_update_date_time
            else:
                return None
        else:
            return None

    def set_strat_brief(self, strat_brief: StratBriefBaseModel) -> DateTime:
        self._strat_brief = strat_brief
        self._strat_brief_update_date_time = DateTime.utcnow()
        return self._strat_brief_update_date_time

    def get_order_snapshots(self, date_time: DateTime | None = None) -> \
            Tuple[List[OrderSnapshotBaseModel], DateTime] | None:
        if date_time is None or date_time < self._order_snapshots_update_date_time:
            if self._order_snapshots is not None:
                return self._order_snapshots, self._order_snapshots_update_date_time
            else:
                return None
        else:
            return None

    def set_order_snapshot(self, order_snapshot: OrderSnapshotBaseModel) -> DateTime:
        if self._order_snapshots is None:
            self._order_snapshots = list()
        self._order_snapshots.append(order_snapshot)
        self._order_snapshots_update_date_time = DateTime.utcnow()
        return self._order_snapshots_update_date_time

    def get_order_journals(self, date_time: DateTime | None = None) -> \
            Tuple[List[OrderJournalBaseModel], DateTime] | None:
        if date_time is None or date_time < self._order_journals_update_date_time:
            if self._order_journals is not None:
                return self._order_journals, self._order_journals_update_date_time
            else:
                return None
        else:
            return None

    def set_order_journal(self, order_journal: OrderJournalBaseModel) -> DateTime:
        if self._order_journals is None:
            self._order_journals = list()
        self._order_journals.append(order_journal)
        self._order_journals_update_date_time = DateTime.utcnow()
        return self._order_journals_update_date_time

    def get_fills_journals(self, date_time: DateTime | None = None) -> \
            Tuple[List[FillsJournalBaseModel], DateTime] | None:
        if date_time is None or date_time < self._fills_journals_update_date_time:
            if self._fills_journals is not None:
                return self._fills_journals, self._fills_journals_update_date_time
            else:
                return None
        else:
            return None

    def set_fills_journal(self, fills_journal: FillsJournalBaseModel) -> DateTime:
        if self._fills_journals is None:
            self._fills_journals = list()
        self._fills_journals.append(fills_journal)
        self._fills_journals_update_date_time = DateTime.utcnow()
        return self._fills_journals_update_date_time

    def get_cancel_orders(self, date_time: DateTime | None = None) -> \
            Tuple[List[CancelOrderBaseModel], DateTime] | None:
        if date_time is None or date_time < self._cancel_orders_update_date_time:
            if self._cancel_orders is not None:
                return self._cancel_orders, self._cancel_orders_update_date_time
            else:
                return None
        else:
            return None

    def set_cancel_order(self, cancel_order: CancelOrderBaseModel) -> DateTime:
        if self._cancel_orders is None:
            self._cancel_orders = list()
        self._cancel_orders.append(cancel_order)
        self._cancel_orders_update_date_time = DateTime.utcnow()
        return self._cancel_orders_update_date_time

    def get_new_orders(self, date_time: DateTime | None = None) -> Tuple[List[NewOrderBaseModel], DateTime] | None:
        if date_time is None or date_time < self._new_orders_update_date_time:
            if self._new_orders is not None:
                return self._new_orders, self._new_orders_update_date_time
            else:
                return None
        else:
            return None

    def set_new_order(self, new_order: NewOrderBaseModel) -> DateTime:
        if self._new_orders is None:
            self._new_orders = list()
        self._new_orders.append(new_order)
        self._new_orders_update_date_time = DateTime.utcnow()
        return self._new_orders_update_date_time

    def get_symbol_overview(self, date_time: DateTime | None = None) -> Tuple[SymbolOverviewBaseModel, DateTime] | None:
        if date_time is None or date_time < self._symbol_overview_update_date_time:
            if self._symbol_overview is not None:
                return self._symbol_overview, self._symbol_overview_update_date_time
            else:
                return None
        else:
            return None

    def set_symbol_overview(self, symbol_overview_: SymbolOverviewBaseModel):
        self._symbol_overview = symbol_overview_
        self._symbol_overview_update_date_time = symbol_overview_.last_update_date_time
        return self._symbol_overview_update_date_time

    def get_top_of_books(self, date_time: DateTime | None = None) -> Tuple[List[TopOfBookBaseModel], DateTime] | None:
        if date_time is None or date_time < self._top_of_books_update_date_time:
            with self.re_ent_lock:
                if self._top_of_books is not None:
                    _top_of_books_update_date_time = copy.deepcopy(self._top_of_books_update_date_time)
                    _top_of_books = copy.deepcopy(self._top_of_books)
                    return _top_of_books, _top_of_books_update_date_time
                else:
                    return None
        else:
            return None

    def set_top_of_book(self, top_of_book: TopOfBookBaseModel) -> DateTime:
        if self._top_of_books is None:
            self._top_of_books = list()

        match len(self._top_of_books):
            case 0:
                self._top_of_books.append(top_of_book)
            case 1:
                if self._top_of_books[0].symbol != top_of_book.symbol:
                    self._top_of_books.append(top_of_book)
                else:
                    self._top_of_books[0] = top_of_book
            case 2:
                if self._top_of_books[0].symbol == top_of_book.symbol:
                    self._top_of_books[0] = top_of_book
                elif self._top_of_books[1].symbol == top_of_book.symbol:
                    self._top_of_books[1] = top_of_book
                else:
                    logging.error(f"Unexpected: ToB symbol: {top_of_book.symbol} not in strat symbols: "
                                  f"{self._top_of_books[0].symbol} {self._top_of_books[1].symbol};;; ToB: {top_of_book}, "
                                  f"pair_strat: {self.get_pair_strat()}")
            case unexpected_len_ToB:
                logging.error(f"Unexpected: expected <= 2 ToB, found: {unexpected_len_ToB} in strat TOB symbols: "
                              f"{[tob.symbol for tob in self._top_of_books]};;; ToB passed: {top_of_book}, ToB stored:"
                              f" {[str(tob) for tob in self._top_of_books]}, pair_strat: {self.get_pair_strat()}")
        # Adding tz awareness to make stored object's timezone comparable with initialized datetime in
        # get_top_of_books, else throws errors
        self._top_of_books_update_date_time = top_of_book.last_update_date_time
        return self._top_of_books_update_date_time

    def get_market_depths(self, symbol: str, side: Side, sorted_reverse: bool = False,
                          date_time: DateTime | None = None) -> Tuple[List[MarketDepthBaseModel], DateTime] | None:
        if date_time is None or date_time < self._market_depths_update_date_time:
            with self.re_ent_lock:
                if self._market_depths_conts is not None:
                    _market_depths_by_symbol: MarketDepthsCont
                    for stored_symbol, _market_depths_by_symbol in self._market_depths_conts:
                        if stored_symbol == symbol:
                            _market_depths_update_date_time = copy.deepcopy(self._market_depths_update_date_time)
                            filtered_market_depths: List[MarketDepthBaseModel] = copy.deepcopy(
                                _market_depths_by_symbol.get_market_depths(side))
                            if sorted_reverse:
                                filtered_market_depths.sort(reverse=True, key=lambda x: x.position)
                            return filtered_market_depths, _market_depths_update_date_time
        # if no match - return None
        return None

    def set_market_depth(self, market_depth: MarketDepthBaseModel) -> DateTime:
        if self._market_depths_conts is None:
            _market_depths_cont = MarketDepthsCont(market_depth.symbol)
            _market_depths_cont.set_market_depth(market_depth)
            self._market_depths_conts = [_market_depths_cont]
        else:
            _market_depths_cont: MarketDepthsCont
            for _market_depths_cont in self._market_depths_conts:
                if _market_depths_cont.symbol == market_depth.symbol:
                    _market_depths_cont.set_market_depth(market_depth)
            else:
                _market_depths_cont = MarketDepthsCont(market_depth.symbol)
                _market_depths_cont.set_market_depth(market_depth)
                self._market_depths_conts.append(_market_depths_cont)
        self._market_depths_update_date_time = market_depth.time
        return self._market_depths_update_date_time

    @classmethod
    def notify_all(cls):
        for strat_cache in cls.strat_cache_dict.values():
            strat_cache.notify_semaphore.release()

    @classmethod
    def add(cls, key: str, strat_cache_: 'StratCache'):
        with cls.add_to_strat_cache_rlock:
            strat_cache: StratCache | None = cls.strat_cache_dict.get(key)
            if strat_cache is None:
                cls.strat_cache_dict[key] = strat_cache_
            else:
                error_str: str = f"Existing StratCache found for add StratCache request, key: {key};;; " \
                                 f"existing_cache: {strat_cache}, strat_cache send to add: {strat_cache_}"
                logging.error(error_str)
                raise Exception(error_str)

    @classmethod
    def pop(cls, key1: str, key2: str):
        with cls.add_to_strat_cache_rlock:
            cls.strat_cache_dict.pop(key1)
            cls.strat_cache_dict.pop(key2)

    @classmethod
    def get(cls, key1: str, key2: str | None = None) -> Optional['StratCache']:
        strat_cache: StratCache = cls.strat_cache_dict.get(key1)
        if strat_cache is None and key2 is not None:
            strat_cache: StratCache = cls.strat_cache_dict.get(key2)
        return strat_cache

    @classmethod
    def guaranteed_get_by_key(cls, key1, key2) -> 'StratCache':
        strat_cache: StratCache = cls.get(key1)
        if strat_cache is None:
            with cls.add_to_strat_cache_rlock:
                strat_cache2: StratCache = cls.get(key2)
                if strat_cache2 is None:  # key2 is guaranteed None, key1 maybe None
                    strat_cache1: StratCache = cls.get(key1)
                    if strat_cache1 is None:  # DCLP (maybe apply SM-DCLP)  # both key-1 and key-1 are none - add
                        strat_cache = StratCache()
                        cls.add(key1, strat_cache)
                        cls.add(key2, strat_cache)
                        logging.info(f"Created strat_cache for key: {key1} {key2}")
                    else:
                        cls.add(key2, strat_cache1)  # add key1 found cache to key2
                        strat_cache = strat_cache1
                else:  # key2 is has cache, key1 maybe None
                    strat_cache1: StratCache = cls.get(key1)
                    if strat_cache1 is None:
                        cls.add(key1, strat_cache2) # add key2 found cache to key1
                        strat_cache = strat_cache2
        return strat_cache

    strat_cache_dict: Dict[str, 'StratCache'] = dict()

    def set_has_unack_leg1(self, has_unack: bool):
        self.unack_leg1 = has_unack

    def has_unack_leg1(self) -> bool:
        return self.unack_leg1

    def set_has_unack_leg2(self, has_unack: bool):
        self.unack_leg1 = has_unack

    def has_unack_leg2(self) -> bool:
        return self.unack_leg2

    def __init__(self):
        self.re_ent_lock: RLock = RLock()
        self.notify_semaphore = Semaphore()
        self.stopped = True  # used by consumer thread to stop processing
        self.leg1_trading_symbol: str | None = None
        self.leg2_trading_symbol: str | None = None
        self.unack_leg1: bool = False
        self.unack_leg2: bool = False

        self._cancel_orders: List[CancelOrderBaseModel] | None = None
        self._cancel_orders_update_date_time: DateTime = DateTime.utcnow()

        self._new_orders: List[NewOrderBaseModel] | None = None
        self._new_orders_update_date_time: DateTime = DateTime.utcnow()

        self._pair_strat: PairStratBaseModel | None = None
        self._pair_strat_update_date_time: DateTime = DateTime.utcnow()

        self._strat_brief: StratBriefBaseModel | None = None
        self._strat_brief_update_date_time: DateTime = DateTime.utcnow()

        self._order_snapshots: List[OrderSnapshotBaseModel] | None = None
        self._order_snapshots_update_date_time: DateTime = DateTime.utcnow()

        self._order_journals: List[OrderJournalBaseModel] | None = None
        self._order_journals_update_date_time: DateTime = DateTime.utcnow()

        self._fills_journals: List[FillsJournalBaseModel] | None = None
        self._fills_journals_update_date_time: DateTime = DateTime.utcnow()

        self._symbol_overview: SymbolOverviewBaseModel | None = None
        self._symbol_overview_update_date_time: DateTime = DateTime.utcnow()

        self._top_of_books: List[TopOfBookBaseModel] | None = None
        self._top_of_books_update_date_time: DateTime = DateTime.utcnow()

        self._market_depths_conts: List[MarketDepthsCont] | None = None
        self._market_depths_update_date_time: DateTime = DateTime.utcnow()


    def __str__(self):
        return f"stopped: {self.stopped}, primary_leg_trading_symbol: {self.leg1_trading_symbol},  " \
               f"secondary_leg_trading_symbol: {self.leg2_trading_symbol}, pair_strat: {self._pair_strat}, " \
               f"unack_leg1 {self.unack_leg1}, unack_leg2 {self.unack_leg2}" \
               f"strat_brief: {self._strat_brief}, cancel_orders: [{self._cancel_orders}], " \
               f"new_orders: [{self._new_orders}], order_snapshots: {self._order_snapshots}, " \
               f"order_journals: {self._order_journals}, fills_journals: {self._fills_journals}, " \
               f"_symbol_overview: {self._symbol_overview}, top of books: {self._top_of_books}"
