# standard imports
from datetime import timedelta
from threading import RLock, Semaphore
from typing import Set
import copy

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_strat_log_key, get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_strat_cache import \
    EmailBookServiceBaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_strat_cache import (
    StreetBookServiceBaseStratCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import (
    StreetBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import MarketDepth
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_strat_cache import BaseStratCache


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
               f"chore_journals: {self._chore_journals}, fills_journals: {self._fills_journals}"
