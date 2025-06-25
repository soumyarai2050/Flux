# standard imports
from datetime import timedelta
from threading import RLock, Semaphore
from typing import Set
import copy

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_plan_log_key, get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_plan_cache import \
    EmailBookServiceBasePlanCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_base_plan_cache import (
    StreetBookServiceBasePlanCache)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_key_handler import (
    StreetBookServiceKeyHandler)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import MarketDepth
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import BasePlanCache


class PlanCache(BasePlanCache, EmailBookServiceBasePlanCache, StreetBookServiceBasePlanCache):
    KeyHandler: Type[StreetBookServiceKeyHandler] = StreetBookServiceKeyHandler
    plan_cache_dict: Dict[str, 'PlanCache'] = dict()  # symbol_side is the key
    add_to_plan_cache_rlock: RLock = RLock()

    def __init__(self):
        BasePlanCache.__init__(self)
        EmailBookServiceBasePlanCache.__init__(self)
        StreetBookServiceBasePlanCache.__init__(self)
        self.market = Market([MarketID.IN])
        self.notify_semaphore = Semaphore()
        self.stopped = True  # used by consumer thread to stop processing
        self.leg1_bartering_symbol: str | None = None
        self.leg2_bartering_symbol: str | None = None
        self.unack_leg1_set: Set[str] = set()
        self.unack_leg2_set: Set[str] = set()
        self.pos_cache: PosCache = PosCache(PlanCache.static_data)

        # all fx always against usd - these are reused across plans
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
        # move plan to pause state via log analyzer if we sees overfill: (logic handles corner cases)
        overfill_log_str = (f"Chore found overfilled for symbol_side_key: "
                            f"{get_symbol_side_key([(ord_brief.security.sec_id, ord_brief.side)])}; plan "
                            f"will be paused, {self.get_key()};;;{chore_snapshot=}")
        self.handle_set_chore_snapshot(chore_snapshot, overfill_log_str)
        return _chore_snapshots_update_date_time  # ignore - helps with debug

    # not working with partially filled chores - check why
    def get_open_chore_count(self) -> int:
        """caller to ensure this call is made only after both _plan_limits and _plan_brief are initialized"""
        assert (self._plan_limits, self._plan_limits.max_open_chores_per_side, self._plan_brief,
                self._plan_brief.pair_sell_side_bartering_brief,
                self._plan_brief.pair_sell_side_bartering_brief.consumable_open_chores,
                self._plan_brief.pair_buy_side_bartering_brief.consumable_open_chores)
        max_open_chores_per_side = self._plan_limits.max_open_chores_per_side
        open_chore_count: int = int(
            max_open_chores_per_side - self._plan_brief.pair_sell_side_bartering_brief.consumable_open_chores +
            max_open_chores_per_side - self._plan_brief.pair_buy_side_bartering_brief.consumable_open_chores)
        return open_chore_count

    @property
    def get_symbol_side_snapshots(self) -> List[SymbolOverviewBaseModel | SymbolOverview | None]:
        return self._symbol_side_snapshots

    def get_bartering_symbols(self) -> Tuple[str | None, str | None]:
        if not self.static_data_service_state.ready:
            self.load_static_data()
        if self.static_data is not None:
            primary_ticker = self._pair_plan.pair_plan_params.plan_leg1.sec.sec_id
            primary_symbol_sedol = self.static_data.get_sedol_from_ticker(primary_ticker)
            secondary_ticker = self._pair_plan.pair_plan_params.plan_leg2.sec.sec_id
            secondary_symbol_ric = self.static_data.get_ric_from_ticker(secondary_ticker)
            if self.market.is_sanity_test_run:
                return primary_ticker, secondary_ticker
            return primary_symbol_sedol, secondary_symbol_ric
        else:
            return None, None

    # pass None to remove pair plan
    def set_pair_plan(self, pair_plan: PairPlanBaseModel | PairPlan | None) -> DateTime:
        self._pair_plan = pair_plan
        self._pair_plan_update_date_time = DateTime.utcnow()
        if self._pair_plan is not None:
            self.leg1_bartering_symbol, self.leg2_bartering_symbol = self.get_bartering_symbols()
            self.pos_cache.cb_fallback_broker = self._pair_plan.pair_plan_params.plan_leg1.fallback_broker.name
            self.pos_cache.cb_fallback_route = self._pair_plan.pair_plan_params.plan_leg1.fallback_route
            self.pos_cache.eqt_fallback_broker = self._pair_plan.pair_plan_params.plan_leg2.fallback_broker.name
            self.pos_cache.eqt_fallback_route = self._pair_plan.pair_plan_params.plan_leg2.fallback_route
        # else not required: passing None to clear pair_plan form cache is valid
        return self._pair_plan_update_date_time

    def get_pair_plan_obj(self) -> PairPlanBaseModel | PairPlan | None:
        return self._pair_plan

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
        if self._pair_plan is not None:
            if (symbol_side_snapshot.security.sec_id == self._pair_plan.pair_plan_params.plan_leg1.sec.sec_id and
                    symbol_side_snapshot.side == self._pair_plan.pair_plan_params.plan_leg1.side):
                self._symbol_side_snapshots[0] = symbol_side_snapshot
                self._symbol_side_snapshots_update_date_time = symbol_side_snapshot.last_update_date_time
                return symbol_side_snapshot.last_update_date_time
            elif (symbol_side_snapshot.security.sec_id == self._pair_plan.pair_plan_params.plan_leg2.sec.sec_id and
                  symbol_side_snapshot.side == self._pair_plan.pair_plan_params.plan_leg2.side):
                self._symbol_side_snapshots[1] = symbol_side_snapshot
                self._symbol_side_snapshots_update_date_time = symbol_side_snapshot.last_update_date_time
                return symbol_side_snapshot.last_update_date_time
            else:
                logging.error(f"set_symbol_side_snapshot called with non matching symbol: "
                              f"{symbol_side_snapshot.security.sec_id}, supported symbols: "
                              f"{self._pair_plan.pair_plan_params.plan_leg1.sec.sec_id}, "
                              f"{self._pair_plan.pair_plan_params.plan_leg2.sec.sec_id}")
        return None

    def set_plan_limits(self, plan_limits: PlanLimitsBaseModel | PlanLimits) -> DateTime:
        if self.pos_cache.started():
            if self._plan_limits is not None:
                if plan_limits.plan_limits_update_seq_num and (
                        self._plan_limits.plan_limits_update_seq_num is None or
                        plan_limits.plan_limits_update_seq_num > self._plan_limits.plan_limits_update_seq_num):
                    self.pos_cache.update_sec_limits(plan_limits.eligible_brokers)
                    logging.debug(f"pos_cache updated with update from set_plan_limits for: "
                                  f"{self.get_key() if self._pair_plan is not None else plan_limits.id}")
                # else not needed - old pos update is still valid
            else:
                logging.warning(f"unexpected: set_plan_limits invoked with: {plan_limits} for: "
                                f"{self.get_key() if self._pair_plan is not None else plan_limits.id} "
                                f"old plan_limits will be overwritten with: {plan_limits};;;"
                                f"old plan_limits: {self._plan_limits}")
        self._plan_limits = plan_limits
        self._plan_limits_update_date_time = DateTime.utcnow()
        return self._plan_limits_update_date_time


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
        if self._pair_plan:
            return f"{get_pair_plan_log_key(self._pair_plan)}-{self.stopped}"
        else:
            return None

    def __str__(self):
        return f"stopped: {self.stopped}, primary_leg_bartering_symbol: {self.leg1_bartering_symbol},  " \
               f"secondary_leg_bartering_symbol: {self.leg2_bartering_symbol}, pair_plan: {self._pair_plan}, " \
               f"unack_leg1 {self.unack_leg1_set}, unack_leg2 {self.unack_leg2_set}, " \
               f"plan_brief: {self._plan_brief}, cancel_chores: {self._chore_id_to_cancel_chore_dict}, " \
               f"new_chores: [{self._new_chores}], chore_snapshots: {self._chore_id_to_chore_snapshot_dict}, " \
               f"chore_ledgers: {self._chore_ledgers}, deals_ledgers: {self._deals_ledgers}"
