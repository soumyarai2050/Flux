# standard imports
from datetime import timedelta
from threading import RLock, Semaphore
from typing import Set
import copy

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_strat_log_key, get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_strat_cache import \
    EmailBookServiceBaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_strat_cache import (
    StreetBookServiceBaseStratCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import (
    StreetBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import ExtendedMarketDepth
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_strat_cache import BaseStratCache


# deprecated - replaced by market_depth cython cache impl
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
            logging.error(f"get_market_depths: Unsupported {side=}, returning empty list")
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


class StratCache(BaseStratCache, EmailBookServiceBaseStratCache, StreetBookServiceBaseStratCache):
    KeyHandler: Type[StreetBookServiceKeyHandler] = StreetBookServiceKeyHandler
    strat_cache_dict: Dict[str, 'StratCache'] = dict()  # symbol_side is the key
    add_to_strat_cache_rlock: RLock = RLock()

    def __init__(self):
        BaseStratCache.__init__(self)
        EmailBookServiceBaseStratCache.__init__(self)
        StreetBookServiceBaseStratCache.__init__(self)
        self.market = Market(MarketID.IN)
        self.notify_semaphore = Semaphore()
        self.stopped = True  # used by consumer thread to stop processing
        self.leg1_bartering_symbol: str | None = None
        self.leg2_bartering_symbol: str | None = None
        self.unack_leg1_set: Set[str] = set()
        self.unack_leg2_set: Set[str] = set()
        self.pos_cache: PosCache = PosCache(StratCache.static_data)

        # all fx always against usd - these are reused across strats
        self.leg1_fx_symbol: str = "USD|SGD"  # get this from static data based on leg1 symbol
        self.leg1_fx_tob: TopOfBookBaseModel | TopOfBook | None = None

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

    def get_close_px(self, system_symbol: str):
        if system_symbol == self._symbol_overviews[0].symbol:
            if self._symbol_overviews[0].closing_px:
                return self._symbol_overviews[0].closing_px
        elif system_symbol == self._symbol_overviews[1].symbol:
            if self._symbol_overviews[1].closing_px:
                return self._symbol_overviews[1].closing_px
        # all else log error return None
        logging.error(f"_symbol_overviews.closing_px not found in get_close_px called for: {system_symbol}")
        return None

    def set_chore_snapshot(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot) -> DateTime:
        """
        override to enrich _chore_id_to_open_chore_snapshot_dict [invoke base first and then act here]
        """
        _chore_snapshots_update_date_time = super().set_chore_snapshot(chore_snapshot)
        ord_brief = chore_snapshot.chore_brief
        # move strat to pause state via log analyzer if we sees overfill: (logic handles corner cases)
        overfill_log_str = (f"Chore found overfilled for symbol_side_key: "
                            f"{get_symbol_side_key([(ord_brief.security.sec_id, ord_brief.side)])}; strat "
                            f"will be paused, {self.get_key()};;;{chore_snapshot=}")
        self.handle_set_chore_snapshot(chore_snapshot, overfill_log_str)
        return _chore_snapshots_update_date_time  # ignore - helps with debug

    # not working with partially filled chores - check why
    def get_open_chore_count(self) -> int:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        assert (self._strat_limits, self._strat_limits.max_open_chores_per_side, self._strat_brief,
                self._strat_brief.pair_sell_side_bartering_brief,
                self._strat_brief.pair_sell_side_bartering_brief.consumable_open_chores,
                self._strat_brief.pair_buy_side_bartering_brief.consumable_open_chores)
        max_open_chores_per_side = self._strat_limits.max_open_chores_per_side
        open_chore_count: int = int(
            max_open_chores_per_side - self._strat_brief.pair_sell_side_bartering_brief.consumable_open_chores +
            max_open_chores_per_side - self._strat_brief.pair_buy_side_bartering_brief.consumable_open_chores)
        return open_chore_count

    @property
    def get_symbol_side_snapshots(self) -> List[SymbolOverviewBaseModel | SymbolOverview | None]:
        return self._symbol_side_snapshots

    @property
    def symbol_overviews(self) -> List[SymbolOverviewBaseModel | SymbolOverview | None]:
        return self._symbol_overviews

    def clear_symbol_overview(self, symbol_overview_id: int) -> None:
        for symbol_overview in self._symbol_overviews:
            if symbol_overview and symbol_overview_id == symbol_overview.id:
                self._symbol_overviews.remove(symbol_overview)

    def get_bartering_symbols(self) -> Tuple[str | None, str | None]:
        if not self.static_data_service_state.ready:
            self.load_static_data()
        if self.static_data is not None:
            primary_ticker = self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            primary_symbol_sedol = self.static_data.get_sedol_from_ticker(primary_ticker)
            secondary_ticker = self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            secondary_symbol_ric = self.static_data.get_ric_from_ticker(secondary_ticker)
            if self.market.is_sanity_test_run:
                return primary_ticker, secondary_ticker
            return primary_symbol_sedol, secondary_symbol_ric
        else:
            return None, None

    # pass None to remove pair strat
    def set_pair_strat(self, pair_strat: PairStratBaseModel | PairStrat | None) -> DateTime:
        self._pair_strat = pair_strat
        self._pair_strat_update_date_time = DateTime.utcnow()
        if self._pair_strat is not None:
            self.leg1_bartering_symbol, self.leg2_bartering_symbol = self.get_bartering_symbols()
            self.pos_cache.cb_fallback_broker = self._pair_strat.pair_strat_params.strat_leg1.fallback_broker.name
            self.pos_cache.cb_fallback_route = self._pair_strat.pair_strat_params.strat_leg1.fallback_route
            self.pos_cache.eqt_fallback_broker = self._pair_strat.pair_strat_params.strat_leg2.fallback_broker.name
            self.pos_cache.eqt_fallback_route = self._pair_strat.pair_strat_params.strat_leg2.fallback_route
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

    def set_strat_limits(self, strat_limits: StratLimitsBaseModel | StratLimits) -> DateTime:
        if self.pos_cache.started():
            if self._strat_limits is not None:
                if strat_limits.strat_limits_update_seq_num and (
                        self._strat_limits.strat_limits_update_seq_num is None or
                        strat_limits.strat_limits_update_seq_num > self._strat_limits.strat_limits_update_seq_num):
                    self.pos_cache.update_sec_limits(strat_limits.eligible_brokers)
                    logging.debug(f"pos_cache updated with update from set_strat_limits for: "
                                  f"{self.get_key() if self._pair_strat is not None else strat_limits.id}")
                # else not needed - old pos update is still valid
            else:
                logging.warning(f"unexpected: set_strat_limits invoked with: {strat_limits} for: "
                                f"{self.get_key() if self._pair_strat is not None else strat_limits.id} "
                                f"old strat_limits will be overwritten with: {strat_limits};;;"
                                f"old strat_limits: {self._strat_limits}")
        self._strat_limits = strat_limits
        self._strat_limits_update_date_time = DateTime.utcnow()
        return self._strat_limits_update_date_time

    def set_symbol_overview(self, symbol_overview_: SymbolOverviewBaseModel | SymbolOverview):
        self.handle_set_symbol_overview_in_symbol_cache(symbol_overview_)
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

    # override of street_book_service_base_strat_cache.py set_top_of_book
    def set_top_of_book(self, top_of_book: TopOfBookBaseModel | TopOfBook) -> DateTime | None:
        self.handle_set_top_of_book(top_of_book)
        if self._pair_strat is None:
            if not self.stopped:
                logging.error(f"Unexpected: strat_cache has no pair strat for tob update of: {top_of_book.symbol}")
            else:
                logging.debug(f"set_top_of_book ignored - strat cache is stopped: {self.stopped}")
            return None
        if top_of_book.symbol == self._pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            if self._top_of_books[0] is None or top_of_book.last_update_date_time > self._tob_leg1_update_date_time:
                self._top_of_books[0] = top_of_book
                self._tob_leg1_update_date_time = top_of_book.last_update_date_time
                return top_of_book.last_update_date_time
            elif top_of_book.last_barter and (self._top_of_books[0].last_barter is None or (
                    top_of_book.last_barter.last_update_date_time >
                    self._top_of_books[0].last_barter.last_update_date_time)):
                self._top_of_books[0].last_barter = top_of_book.last_barter
                # artificially update TOB datetime for next pickup by app
                self._tob_leg1_update_date_time += timedelta(milliseconds=1)
                return self._tob_leg1_update_date_time
            else:
                delta = self._tob_leg1_update_date_time - top_of_book.last_update_date_time
                logging.debug(f"leg1 set_top_of_book called for: {top_of_book.symbol=} with update_date_time older "
                              f"by: {delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[0]}"
                              f" update received [discarded] {top_of_book=}")
                return None
            # else not needed - common log outside handles this
        elif top_of_book.symbol == self._pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            # TOB sometimes is with same time-stamp, could be due to time granularity, don't block, so: >= not >
            if self._top_of_books[1] is None or top_of_book.last_update_date_time >= self._tob_leg2_update_date_time:
                self._top_of_books[1] = top_of_book
                self._tob_leg2_update_date_time = top_of_book.last_update_date_time
                return top_of_book.last_update_date_time
            elif top_of_book.last_barter and (self._top_of_books[1].last_barter is None or (
                    top_of_book.last_barter.last_update_date_time >
                    self._top_of_books[1].last_barter.last_update_date_time)):
                self._top_of_books[1].last_barter = top_of_book.last_barter
                # artificially update TOB datetime for next pickup by app
                self._tob_leg2_update_date_time += timedelta(milliseconds=1)
                return self._tob_leg2_update_date_time
            else:
                delta = self._tob_leg2_update_date_time - top_of_book.last_update_date_time
                logging.debug(f"leg2 set_top_of_book called for: {top_of_book.symbol=} with update_date_time older "
                              f"by: {delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[1]}"
                              f" update received [discarded] {top_of_book=}")
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
                                 sorted_market_depths: List[MarketDepthBaseModel | ExtendedMarketDepth]) -> DateTime:
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
        unack_leg1 = self.has_unack_leg1()
        unack_leg2 = self.has_unack_leg2()
        return unack_leg1 or unack_leg2

    def set_has_unack_leg1(self, has_unack: bool, internal_ord_id: str):
        if has_unack:
            self.unack_leg1_set.add(internal_ord_id)
        else:  # remove from
            self.unack_leg1_set.discard(internal_ord_id)

    def has_unack_leg1(self) -> bool:
        return len(self.unack_leg1_set) > 0

    def set_has_unack_leg2(self, has_unack: bool, internal_ord_id: str):
        if has_unack:
            self.unack_leg2_set.add(internal_ord_id)
        else:  # remove from
            self.unack_leg2_set.discard(internal_ord_id)

    def has_unack_leg2(self) -> bool:
        return len(self.unack_leg2_set) > 0

    def get_key(self):
        if self._pair_strat:
            return f"{get_pair_strat_log_key(self._pair_strat)}-{self.stopped}"
        else:
            return None

    def __str__(self):
        return f"stopped: {self.stopped}, primary_leg_bartering_symbol: {self.leg1_bartering_symbol},  " \
               f"secondary_leg_bartering_symbol: {self.leg2_bartering_symbol}, pair_strat: {self._pair_strat}, " \
               f"unack_leg1 {self.unack_leg1_set}, unack_leg2 {self.unack_leg2_set}, " \
               f"strat_brief: {self._strat_brief}, cancel_chores: {self._chore_id_to_cancel_chore_dict}, " \
               f"new_chores: [{self._new_chores}], chore_snapshots: {self._chore_id_to_chore_snapshot_dict}, " \
               f"chore_journals: {self._chore_journals}, fills_journals: {self._fills_journals}, " \
               f"_symbol_overview: {[str(symbol_overview) for symbol_overview in self._symbol_overviews] if self._symbol_overviews else str(None)}, " \
               f"top of books: {[str(top_of_book) for top_of_book in self._top_of_books] if self._top_of_books else str(None)}, " \
               f"market_depth: {[str(market_depth) for market_depth in self._market_depths_conts] if self._market_depths_conts else str(None)}"
