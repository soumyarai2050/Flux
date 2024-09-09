# standard imports
import logging
from datetime import timedelta
from threading import RLock, Semaphore
from typing import Dict, Tuple, Optional, ClassVar, Set
import copy
import pytz
from pendulum import DateTime
import inspect

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_strat_log_key, get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_fills_journal_log_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_strat_cache import \
    EmailBookServiceBaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_strat_cache import (
    StreetBookServiceBaseStratCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import (
    StreetBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
# from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.ws_helper import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import config_dict
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.mobile_book_cache import SharedMarketDepth


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
            logging.error(f"get_market_depths: Unsupported {side = }, returning empty list")
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


class ChoreSnapshotContainer:
    def __init__(self, chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel, has_fill: bool):
        self.chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel = chore_snapshot
        self.has_fill: bool = has_fill


class StratCache(EmailBookServiceBaseStratCache, StreetBookServiceBaseStratCache):
    strat_cache_dict: Dict[str, 'StratCache'] = dict()  # symbol_side is the key
    add_to_strat_cache_rlock: RLock = RLock()
    chore_id_to_symbol_side_tuple_dict: Dict[str | int, Tuple[str, Side]] = dict()
    # fx_symbol_overview_dict must be preloaded with supported fx pairs for system to work
    fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | FxSymbolOverview | None] = {"USD|SGD": None}

    error_prefix = "StratCache"
    load_static_data_mutex: Lock = Lock()
    static_data_service_state: ClassVar[ServiceState] = ServiceState(
        error_prefix=error_prefix + "static_data_service failed, exception: ")
    static_data: SecurityRecordManager | None = None

    def __init__(self):
        EmailBookServiceBaseStratCache.__init__(self)
        StreetBookServiceBaseStratCache.__init__(self)
        self.market = Market(MarketID.IN)
        if not StratCache.static_data_service_state.ready:
            StratCache.load_static_data()
        self.re_ent_lock: RLock = RLock()
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

        # chore-snapshot is also stored in here iff chore snapshot is open [and removed from here if otherwise]
        self._chore_id_to_open_chore_snapshot_cont_dict: Dict[Any, ChoreSnapshotContainer] = {}  # no open
        self._open_chore_snapshots_update_date_time: DateTime = DateTime.utcnow()
        # temp store for has_fill till chore snapshot is created / has fill updated
        self.open_chore_id_has_fill_set: Set = set()
        self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock: Lock = Lock()

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

    def _check_log_over_fill(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot):
        if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
            # move strat to pause via log analyzer if we sees overfill: (logic handles corner cases)
            ord_brief = chore_snapshot.chore_brief
            logging.critical(f"Chore found overfilled for symbol_side_key: "
                             f"{get_symbol_side_key([(ord_brief.security.sec_id, ord_brief.side)])}; strat "
                             f"will be paused, {self.get_key()};;;{chore_snapshot=}")

    def set_chore_snapshot(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot) -> DateTime:
        """
        override to enrich _chore_id_to_open_chore_snapshot_dict [invoke base first and then act here]
        """
        _chore_snapshots_update_date_time = super().set_chore_snapshot(chore_snapshot)
        if not chore_snapshot.chore_brief.user_data:
            return DateTime.now()  # external chore - no need to further cache
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            has_fill: bool = False
            if chore_snapshot.chore_status not in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED,
                                                   ChoreStatusType.OE_OVER_FILLED, ChoreStatusType.OE_OVER_CXLED]:
                if chore_snapshot.chore_brief.chore_id in self.open_chore_id_has_fill_set:
                    has_fill = True
                if not (chore_snapshot_container := self._chore_id_to_open_chore_snapshot_cont_dict.get(
                        chore_snapshot.chore_brief.chore_id)):
                    chore_snapshot_container = ChoreSnapshotContainer(chore_snapshot, has_fill)
                    self._chore_id_to_open_chore_snapshot_cont_dict[chore_snapshot.chore_brief.chore_id] = \
                        chore_snapshot_container
                else:
                    chore_snapshot_container.chore_snapshot = chore_snapshot
                    if not chore_snapshot_container.has_fill:
                        chore_snapshot_container.has_fill = has_fill
                    else:
                        # has existing fill
                        pass
            else:
                self._check_log_over_fill(chore_snapshot)
                # chore is not open anymore, remove from chore_id_has_fill_set [set used only on open chores]
                self.open_chore_id_has_fill_set.discard(chore_snapshot.chore_brief.chore_id)
                # Providing the second argument None prevents the KeyError exception
                self._chore_id_to_open_chore_snapshot_cont_dict.pop(chore_snapshot.chore_brief.chore_id, None)
        return _chore_snapshots_update_date_time

    def get_open_chore_snapshots(self) -> List[ChoreSnapshot]:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            return [open_chore_snapshot_cont.chore_snapshot for open_chore_snapshot_cont in
                    self._chore_id_to_open_chore_snapshot_cont_dict.values()]

    def get_open_chore_count_from_cache(self) -> int:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        return len(self._chore_id_to_open_chore_snapshot_cont_dict)

    def check_has_open_chore_with_no_fill_from_cache(self) -> bool:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        open_chore_snapshot_cont: ChoreSnapshotContainer
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            for open_chore_snapshot_cont in self._chore_id_to_open_chore_snapshot_cont_dict.values():
                if not open_chore_snapshot_cont.has_fill:
                    return True
        return False

    def update_has_fill_on_open_chore_snapshot(self, fills_journal: FillsJournal):
        if not fills_journal.user_data:
            return  # external chore, no processing needed
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            open_chore_snapshot_cont: ChoreSnapshotContainer
            if open_chore_snapshot_cont := self._chore_id_to_open_chore_snapshot_cont_dict.get(fills_journal.chore_id):
                open_chore_snapshot_cont.has_fill = True
            elif fills_journal.chore_id not in self.open_chore_id_has_fill_set:
                # TODO: this also adds fills that may arrive post DOD (non Open chores) and reenter the set - add
                #  periodic cleanup
                self.open_chore_id_has_fill_set.add(fills_journal.chore_id)

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

    @staticmethod
    def get_key_n_symbol_from_fills_journal(
            fills_journal: FillsJournalBaseModel | FillsJournal) -> Tuple[str | None, str | None]:
        symbol: str
        symbol_side_tuple = StratCache.chore_id_to_symbol_side_tuple_dict.get(fills_journal.chore_id)
        if not symbol_side_tuple:
            logging.error(f"Unknown {fills_journal.chore_id = } found for fill "
                          f"{get_fills_journal_log_key(fills_journal)};;; {fills_journal = }")
            return None, None
        symbol, side = symbol_side_tuple
        key: str | None = StreetBookServiceKeyHandler.get_key_from_fills_journal(fills_journal)
        return key, symbol

    def get_metadata(self, system_symbol: str) -> Tuple[str, str, str]:
        """function to check system symbol's corresponding bartering_symbol, account, exchange (maybe fx in future ?)"""
        bartering_symbol: str = system_symbol
        account = "bartering_account"
        exchange = "bartering_exchange"
        return bartering_symbol, account, exchange

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
                    logging.debug(f"pos_cache updated from set_strat_limits for: "
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

    def get_symbol_overview_from_symbol_obj(self, symbol: str) -> SymbolOverviewBaseModel | SymbolOverview | None:
        symbol_overview_tuple = self.get_symbol_overview()
        if symbol_overview_tuple is not None:
            symbol_overview_list, _ = symbol_overview_tuple
            for symbol_overview in symbol_overview_list:
                if symbol_overview is not None and symbol_overview.symbol == symbol:
                    return symbol_overview
        # if no match - return None
        return None

    def get_symbol_overview_from_symbol(self, symbol: str, date_time: DateTime | None = None) -> \
            Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None:
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

    # override of street_book_service_base_strat_cache.py set_top_of_book
    def set_top_of_book(self, top_of_book: TopOfBookBaseModel | TopOfBook) -> DateTime | None:
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
                logging.debug(f"leg1 set_top_of_book called for: {top_of_book.symbol = } with update_date_time older "
                              f"by: {delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[0]}"
                              f" update received [discarded] {top_of_book = }")
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
                logging.debug(f"leg2 set_top_of_book called for: {top_of_book.symbol = } with update_date_time older "
                              f"by: {delta} period, ignoring this TOB;;;stored tob: {self._top_of_books[1]}"
                              f" update received [discarded] {top_of_book = }")
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
                                 sorted_market_depths: List[MarketDepthBaseModel | SharedMarketDepth]) -> DateTime:
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

    @classmethod
    def load_static_data(cls):
        with cls.load_static_data_mutex:
            try:
                cls.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                if cls.static_data is not None:
                    cls.static_data_service_state.ready = True
                else:
                    raise Exception(f"self.static_data init to None, unexpected!!")
            except Exception as e:
                cls.static_data_service_state.handle_exception(e)

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
