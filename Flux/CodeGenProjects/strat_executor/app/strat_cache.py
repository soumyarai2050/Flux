# standard imports
import logging
from datetime import timedelta
from threading import RLock, Semaphore
from typing import Dict, Tuple, Optional, ClassVar
import copy
import pytz
from pendulum import DateTime

# project imports
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import get_fills_journal_log_key
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_base_strat_cache import \
    StratManagerServiceBaseStratCache
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_base_strat_cache import (
    StratExecutorServiceBaseStratCache)
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_key_handler import (
    StratExecutorServiceKeyHandler)


class MarketDepthsCont:
    def __init__(self, symbol: str):
        self.symbol: str = symbol
        self.bid_market_depths: List[MarketDepthBaseModel | MarketDepth] = []
        self.ask_market_depths: List[MarketDepthBaseModel | MarketDepth] = []

    def __str__(self):
        return f"{self.symbol} " \
               f"bid_market_depths: {[str(bid_market_depth) for bid_market_depth in self.bid_market_depths] if self.bid_market_depths else str(None)} " \
               f"ask_market_depths: {[str(ask_market_depth) for ask_market_depth in self.ask_market_depths] if self.ask_market_depths else str(None)}"

    def get_market_depths(self, side: Side):
        if side == Side.BUY:
            return self.bid_market_depths
        elif side == Side.SELL:
            return self.ask_market_depths
        else:
            logging.error(f"get_market_depths: Unsupported Side requested: {side}, returning empty list")
            return []

    def set_market_depths(self, side: str, market_depths: List[MarketDepthBaseModel] | List[MarketDepth]):
        if side == "BID":
            self.bid_market_depths = market_depths
        elif side == "ASK":
            self.ask_market_depths = market_depths

    def set_market_depth(self, market_depth: MarketDepthBaseModel | MarketDepth):
        if market_depth.side == TickType.BID:
            for bid_market_depth in self.bid_market_depths:
                if bid_market_depth.position == market_depth.position:
                    bid_market_depth = market_depth
            else:
                self.bid_market_depths.append(market_depth)
        elif market_depth.side == TickType.ASK:
            for ask_market_depth in self.ask_market_depths:
                if ask_market_depth.position == market_depth.position:
                    ask_market_depth = market_depth
            else:
                self.ask_market_depths.append(market_depth)


class StratCache(StratManagerServiceBaseStratCache, StratExecutorServiceBaseStratCache):
    strat_cache_dict: Dict[str, 'StratCache'] = dict()  # symbol_side is the key
    add_to_strat_cache_rlock: RLock = RLock()
    order_id_to_symbol_side_tuple_dict: Dict[str | int, Tuple[str, Side]] = dict()
    # fx_symbol_overview_dict must be preloaded with supported fx pairs for system to work
    fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | FxSymbolOverview | None] = {"USD|SGD": None}

    def __init__(self):
        StratManagerServiceBaseStratCache.__init__(self)
        StratExecutorServiceBaseStratCache.__init__(self)
        self.re_ent_lock: RLock = RLock()
        self.notify_semaphore = Semaphore()
        self.stopped = True  # used by consumer thread to stop processing
        self.leg1_trading_symbol: str | None = None
        self.leg2_trading_symbol: str | None = None
        self.unack_leg1: bool = False
        self.unack_leg2: bool = False

        # all fx always against usd - these are reused across strats
        self.leg1_fx_symbol: str = "USD|SGD"  # get this from static data based on leg1 symbol
        self.leg1_fx_tob: TopOfBookBaseModel | TopOfBook | None = None
        self.leg1_fx_symbol_overview: FxSymbolOverviewBaseModel | FxSymbolOverview | None = None

        self._symbol_side_snapshots: List[SymbolSideSnapshotBaseModel |
                                          SymbolSideSnapshot | None] = [None, None]  # pre-create space for 2 legs
        self._symbol_side_snapshots_update_date_time: DateTime = DateTime.utcnow()

        self._symbol_overviews: List[SymbolOverviewBaseModel |
                                     SymbolOverview | None] = [None, None]  # pre-create space for 2 legs
        self._symbol_overviews_update_date_time: DateTime = DateTime.utcnow()

        self._top_of_books: List[TopOfBookBaseModel | TopOfBook | None] = [None, None]  # pre-create space for 2 legs
        self._tob_leg1_update_date_time: DateTime = DateTime.utcnow()
        self._tob_leg2_update_date_time: DateTime = DateTime.utcnow()

        self._market_depths_conts: List[MarketDepthsCont] | None = None
        self._market_depths_update_date_time: DateTime = DateTime.utcnow()

        # order-snapshot is also stored in here iff order snapshot is open [and removed from here if otherwise]
        self._order_id_to_open_order_snapshot_dict: Dict[Any, OrderSnapshotBaseModel | OrderSnapshot] = {}  # no open
        self._open_order_snapshots_update_date_time: DateTime = DateTime.utcnow()

    def set_order_snapshot(self, order_snapshot: OrderSnapshotBaseModel | OrderSnapshot) -> DateTime:
        """
        override to enrich _order_id_to_open_order_snapshot_dict [invoke base first and then act here]
        """
        _order_snapshots_update_date_time = super().set_order_snapshot(order_snapshot)
        if order_snapshot.order_status not in [OrderStatusType.OE_DOD, OrderStatusType.OE_FILLED]:
            self._order_id_to_open_order_snapshot_dict[order_snapshot.order_brief.order_id] = order_snapshot
        elif order_snapshot.order_status == OrderStatusType.OE_OVER_FILLED:
            # ideally code would move the strat to pause state when it sees overfill - this only handles corner cases
            logging.error("Unexpected: Order found overfilled - strat will block [has open order will force fail]")
        else:
            # Providing the second argument None prevents the KeyError exception
            self._order_id_to_open_order_snapshot_dict.pop(order_snapshot.order_brief.order_id, None)
        pass  # ignore - helps with debug

    def get_open_order_count_from_cache(self) -> int:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        return len(self._order_id_to_open_order_snapshot_dict)

    # not working with partially filled orders - check why
    def get_open_order_count(self) -> int:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        assert (self._strat_limits, self._strat_limits.max_open_orders_per_side, self._strat_brief,
               self._strat_brief.pair_sell_side_trading_brief,
               self._strat_brief.pair_sell_side_trading_brief.consumable_open_orders,
               self._strat_brief.pair_buy_side_trading_brief.consumable_open_orders)
        max_open_orders_per_side = self._strat_limits.max_open_orders_per_side
        open_order_count: int = int(
            max_open_orders_per_side - self._strat_brief.pair_sell_side_trading_brief.consumable_open_orders +
            max_open_orders_per_side - self._strat_brief.pair_buy_side_trading_brief.consumable_open_orders)
        return open_order_count

    @property
    def get_symbol_side_snapshots(self) -> List[SymbolOverviewBaseModel | SymbolOverview | None]:
        return self._symbol_side_snapshots

    @property
    def get_symbol_overviews(self) -> List[SymbolOverviewBaseModel | SymbolOverview | None]:
        return self._symbol_overviews

    @staticmethod
    def get_key_n_symbol_from_fills_journal(
            fills_journal: FillsJournalBaseModel | FillsJournal) -> Tuple[str | None, str | None]:
        symbol: str
        symbol_side_tuple = StratCache.order_id_to_symbol_side_tuple_dict.get(fills_journal.order_id)
        if not symbol_side_tuple:
            logging.error(f"Unknown order id: {fills_journal.order_id} found for fill "
                          f"{get_fills_journal_log_key(fills_journal)};;;fill_journal: {fills_journal}")
            return None, None
        symbol, side = symbol_side_tuple
        key: str | None = StratExecutorServiceKeyHandler.get_key_from_fills_journal(fills_journal)
        return key, symbol

    def get_metadata(self, system_symbol: str) -> Tuple[str, str, str]:
        """function to check system symbol's corresponding trading_symbol, account, exchange (maybe fx in future ?)"""
        trading_symbol: str = system_symbol
        account = "trading_account"
        exchange = "trading_exchange"
        return trading_symbol, account, exchange

    def get_trading_symbols(self):
        primary_ticker = self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        secondary_ticker = self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        return primary_ticker, secondary_ticker

    # pass None to remove pair strat
    def set_pair_strat(self, pair_strat: PairStratBaseModel | PairStrat | None) -> DateTime:
        self._pair_strat = pair_strat
        self._pair_strat_update_date_time = DateTime.utcnow()
        if self._pair_strat is not None:
            self.leg1_trading_symbol, self.leg2_trading_symbol = self.get_trading_symbols()
        # else not required: passing None to clear pair_strat form cache is valid
        return self._pair_strat_update_date_time

    def get_pair_strat_obj(self) -> PairStratBaseModel | PairStrat | None:
        return self._pair_strat

    def get_symbol_side_snapshot_from_symbol(self, symbol: str, date_time: DateTime | None = None) -> \
            Tuple[SymbolSideSnapshot, DateTime] | None:
        symbol_side_snapshot_tuple = self.get_symbol_side_snapshot(date_time)
        if symbol_side_snapshot_tuple is not None:
            symbol_side_snapshot_list, _ = symbol_side_snapshot_tuple
            for symbol_side_snapshot in symbol_side_snapshot_list:
                if symbol_side_snapshot is not None and symbol_side_snapshot.security.sec_id == symbol:
                    if date_time is None or date_time < symbol_side_snapshot.last_update_date_time:
                        return symbol_side_snapshot, symbol_side_snapshot.last_update_date_time
        return None

    def set_symbol_side_snapshot(self, symbol_side_snapshot: SymbolSideSnapshotBaseModel | SymbolSideSnapshot
                                 ) -> DateTime | None:
        if self._pair_strat is not None:
            if (symbol_side_snapshot.security.sec_id == self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id and
                    symbol_side_snapshot.side == self._pair_strat.pair_strat_params.strat_leg1.side):
                self._symbol_side_snapshots[0] = symbol_side_snapshot
                self._symbol_side_snapshots_update_date_time = symbol_side_snapshot.last_update_date_time
                return symbol_side_snapshot.last_update_date_time
            elif (symbol_side_snapshot.security.sec_id == self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id and
                  symbol_side_snapshot.side == self._pair_strat.pair_strat_params.strat_leg2.side):
                self._symbol_side_snapshots[1] = symbol_side_snapshot
                self._symbol_side_snapshots_update_date_time = symbol_side_snapshot.last_update_date_time
                return symbol_side_snapshot.last_update_date_time
            else:
                logging.error(f"set_symbol_side_snapshot called with non matching symbol: "
                              f"{symbol_side_snapshot.security.sec_id}, supported symbols: "
                              f"{self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id}, "
                              f"{self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
        return None

    def get_symbol_overview_from_symbol(
            self, symbol: str, date_time: DateTime | None = None) -> Tuple[SymbolOverviewBaseModel | SymbolOverview,
                                                                           DateTime] | None:
        symbol_overview_tuple = self.get_symbol_overview(date_time)

        if symbol_overview_tuple is not None:
            symbol_overview_list, _ = symbol_overview_tuple
            for symbol_overview in symbol_overview_list:
                if symbol_overview is not None and symbol_overview.symbol == symbol:
                    if date_time is None or date_time < symbol_overview.last_update_date_time:
                        return symbol_overview, symbol_overview.last_update_date_time
        # if no match - return None
        return None

    def set_symbol_overview(self, symbol_overview_: SymbolOverviewBaseModel | SymbolOverview):
        if self._pair_strat is not None:
            if symbol_overview_.symbol == self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
                self._symbol_overviews[0] = symbol_overview_
                self._symbol_overviews_update_date_time = symbol_overview_.last_update_date_time
                return symbol_overview_.last_update_date_time
            elif symbol_overview_.symbol == self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
                self._symbol_overviews[1] = symbol_overview_
                self._symbol_overviews_update_date_time = symbol_overview_.last_update_date_time
                return symbol_overview_.last_update_date_time
            else:
                logging.error(f"set_symbol_overview called with non matching symbol: {symbol_overview_.symbol}, "
                              f"supported symbols: {self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id}, "
                              f"{self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
        return None

    def get_top_of_book(self, date_time: DateTime | None = None) -> \
            Tuple[List[TopOfBookBaseModel | TopOfBook], DateTime] | None:
        if date_time is None or (
                date_time < self._tob_leg1_update_date_time and date_time < self._tob_leg2_update_date_time):
            with self.re_ent_lock:
                if self._top_of_books[0] is not None and self._top_of_books[1] is not None:
                    _top_of_books_update_date_time = copy.deepcopy(
                        self._tob_leg1_update_date_time if self._tob_leg1_update_date_time < self._tob_leg2_update_date_time else self._tob_leg2_update_date_time)
                    _top_of_books = copy.deepcopy(self._top_of_books)
                    return _top_of_books, _top_of_books_update_date_time
        # all else's return None
        return None

    def set_top_of_book(self, top_of_book: TopOfBookBaseModel | TopOfBook) -> DateTime | None:
        if top_of_book.symbol == self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            if top_of_book.last_update_date_time > self._tob_leg1_update_date_time:
                self._top_of_books[0] = top_of_book
                self._tob_leg1_update_date_time = top_of_book.last_update_date_time
                return top_of_book.last_update_date_time
            elif top_of_book.last_trade and (self._top_of_books[0].last_trade is None or (
                    top_of_book.last_trade.last_update_date_time >
                    self._top_of_books[0].last_trade.last_update_date_time)):
                self._top_of_books[0].last_trade = top_of_book.last_trade
                # artificially update TOB datetime for next pickup by app
                self._tob_leg1_update_date_time += timedelta(milliseconds=1)
            else:
                delta = self._tob_leg1_update_date_time - top_of_book.last_update_date_time
                logging.debug(f"leg1 set_top_of_book called for: {top_of_book.symbol} with update_date_time older by: "
                              f"{delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[0]}"
                              f" update received [discarded] TOB: {top_of_book}")
                return None
            # else not needed - common log outside handles this
        elif top_of_book.symbol == self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            if top_of_book.last_update_date_time > self._tob_leg2_update_date_time:
                self._top_of_books[1] = top_of_book
                self._tob_leg2_update_date_time = top_of_book.last_update_date_time
                return top_of_book.last_update_date_time
            elif top_of_book.last_trade and (self._top_of_books[1].last_trade is None or (
                    top_of_book.last_trade.last_update_date_time >
                    self._top_of_books[1].last_trade.last_update_date_time)):
                self._top_of_books[1].last_trade = top_of_book.last_trade
                # artificially update TOB datetime for next pickup by app
                self._tob_leg2_update_date_time += timedelta(milliseconds=1)
            else:
                delta = self._tob_leg2_update_date_time - top_of_book.last_update_date_time
                logging.debug(f"leg2 set_top_of_book called for: {top_of_book.symbol} with update_date_time older by: "
                              f"{delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[1]}"
                              f" update received [discarded] TOB: {top_of_book}")
                return None
        else:
            logging.error(f"set_top_of_book called with non matching symbol: {top_of_book.symbol}, "
                          f"supported symbols: {self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id}, "
                          f"{self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
            return None

    def get_market_depth(self, symbol: str, side: Side, sorted_reverse: bool = False,
                         date_time: DateTime | None = None) -> \
            Tuple[List[MarketDepthBaseModel | MarketDepth], DateTime] | None:
        if date_time is None or date_time < self._market_depths_update_date_time:
            with self.re_ent_lock:
                if self._market_depths_conts is not None:
                    _market_depth_cont: MarketDepthsCont
                    for _market_depth_cont in self._market_depths_conts:
                        if _market_depth_cont.symbol == symbol:
                            # deep copy not needed as new updates overwrite the entire container [only
                            # set_sorted_market_depths interface available for update]
                            _market_depths_update_date_time = self._market_depths_update_date_time
                            # _market_depths_update_date_time = copy.deepcopy(self._market_depths_update_date_time)
                            # filtered_market_depths: List[MarketDepthBaseModel | MarketDepth] = copy.deepcopy(
                            filtered_market_depths: List[MarketDepthBaseModel | MarketDepth] = \
                                _market_depth_cont.get_market_depths(side)
                            if sorted_reverse:
                                filtered_market_depths.sort(reverse=True, key=lambda x: x.position)
                            return filtered_market_depths, _market_depths_update_date_time
        # if no match - return None
        return None

    def set_market_depth(self, market_depth: MarketDepthBaseModel | MarketDepth) -> DateTime:
        """
        # old code - now disabled [ At this time we expect only set_sorted_market_depths to be called ]
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
        self._market_depths_update_date_time = market_depth.exch_time
        return self._market_depths_update_date_time
        """
        raise NotImplementedError

    def set_sorted_market_depths(self, system_symbol: str, side: str, newest_exch_time: datetime,
                                 sorted_market_depths: List[MarketDepthBaseModel | MarketDepth]) -> DateTime:
        if self._market_depths_conts is None:
            self._market_depths_conts = []
            _market_depths_cont = MarketDepthsCont(system_symbol)
            _market_depths_cont.set_market_depths(side, sorted_market_depths)
            self._market_depths_conts.append(_market_depths_cont)
        else:
            _market_depths_cont: MarketDepthsCont
            for _market_depths_cont in self._market_depths_conts:
                if _market_depths_cont.symbol == system_symbol:
                    _market_depths_cont.set_market_depths(side, sorted_market_depths)
            else:
                _market_depths_cont = MarketDepthsCont(system_symbol)
                _market_depths_cont.set_market_depths(side, sorted_market_depths)
                self._market_depths_conts.append(_market_depths_cont)
        self._market_depths_update_date_time = newest_exch_time
        return self._market_depths_update_date_time

    def has_unack_leg(self) -> bool:
        return self.has_unack_leg1() or self.has_unack_leg2()

    def set_has_unack_leg1(self, has_unack: bool):
        self.unack_leg1 = has_unack

    def has_unack_leg1(self) -> bool:
        return self.unack_leg1

    def set_has_unack_leg2(self, has_unack: bool):
        self.unack_leg2 = has_unack

    def has_unack_leg2(self) -> bool:
        return self.unack_leg2

    def get_key(self):
        return f"{get_pair_strat_log_key(self._pair_strat)}-{self.stopped}"

    def __str__(self):
        return f"stopped: {self.stopped}, primary_leg_trading_symbol: {self.leg1_trading_symbol},  " \
               f"secondary_leg_trading_symbol: {self.leg2_trading_symbol}, pair_strat: {self._pair_strat}, " \
               f"unack_leg1 {self.unack_leg1}, unack_leg2 {self.unack_leg2}, " \
               f"strat_brief: {self._strat_brief}, cancel_orders: {self._order_id_to_cancel_order_dict}, " \
               f"new_orders: [{self._new_orders}], order_snapshots: {self._order_id_to_order_snapshot_dict}, " \
               f"order_journals: {self._order_journals}, fills_journals: {self._fills_journals}, " \
               f"_symbol_overview: {[str(symbol_overview) for symbol_overview in self._symbol_overviews] if self._symbol_overviews else str(None)}, " \
               f"top of books: {[str(top_of_book) for top_of_book in self._top_of_books] if self._top_of_books else str(None)}, " \
               f"market_depth: {[str(market_depth) for market_depth in self._market_depths_conts] if self._market_depths_conts else str(None)}"
