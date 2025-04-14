import logging
import time
from threading import Thread
import math
import subprocess
import stat
import random
import ctypes

from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecord, SecType

from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import (
    ChoreControl, initialize_chore_control)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_data_manager import BarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.plan_cache import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase, config_dict)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_pair_plan_log_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_consumable_participation_qty_http, get_new_chore_log_key,
    get_plan_brief_log_key, get_simulator_config_file_path)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import (
    executor_config_yaml_dict)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    create_md_shell_script, create_stop_md_script, MDShellEnvData, email_book_service_http_client,
    guaranteed_call_pair_plan_client, get_symbol_side_key, create_start_cpp_md_shell_script,
    create_stop_cpp_md_shell_script)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.model_extensions import SecPosExtended
from Flux.PyCodeGenEngine.FluxCodeGenCore.perf_benchmark_decorators import perf_benchmark_sync_callable
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.ORMModel.post_book_service_model_imports import (
    IsContactLimitsBreached)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import (
    post_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import (
    SymbolCache, MarketDepth, TopOfBook, LastBarter)
# below import is required to symbol_cache to work - SymbolCacheContainer must import from base_plan_cache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import SymbolCacheContainer
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book import BaseBook


def depths_str(depths: List[MarketDepth], notional_fx_rate: float | None = None) -> str:
    if not notional_fx_rate:
        notional_fx_rate = 1
    if depths:
        symbol: str = depths[0].symbol
        side = depths[0].side
        ret_str = f" Depths of {symbol}, {side}: ["
        depth: MarketDepth
        for depth in depths:
            if symbol != depth.symbol:
                logging.error(f"mismatched {depth.symbol=} found in {depth} expected {symbol};;;depths: "
                              f"{[str(d) for d in depths]}")
            if side != depth.side:
                logging.error(f"mismatched {depth.side=} found in {depth} expected {side};;;depths: "
                              f"{[str(d) for d in depths]}")
            exch_time_str = depth.exch_time.to_time_string()
            arrival_time_str = depth.arrival_time.to_time_string()
            ret_str += '\n\t' + (f"level={depth.position}, exch_time={exch_time_str}, arrival_time={arrival_time_str}, "
                                 f"px={depth.px:.3f}, qty={depth.qty}, cum_avg_px={depth.cumulative_avg_px:.3f}, "
                                 f"cum_qty={depth.cumulative_qty}, "
                                 f"cum_notional={depth.cumulative_notional/notional_fx_rate:.0f}")
        ret_str += '\n]\n'
        return ret_str
    else:
        return f"empty: depths_str called with {depths=}"


class StreetBook(BaseBook):
    # Query Callables
    underlying_handle_plan_activate_query_http: Callable[..., Any] | None = None
    underlying_update_residuals_query_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes_imports import (
            underlying_handle_plan_activate_query_http, underlying_update_residuals_query_http)
        cls.underlying_handle_plan_activate_query_http = underlying_handle_plan_activate_query_http
        cls.underlying_update_residuals_query_http = underlying_update_residuals_query_http

    def update_plan_leg_block(self, plan_leg: PlanLeg, sec_rec: SecurityRecord,
                               block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]]) -> bool:
        # ticker: str = plan_leg.sec.sec_id
        side: Side = plan_leg.side
        primary_bartering_symbol: str | None = None
        secondary_bartering_symbol: str | None = None
        if sec_rec.sec_type == SecType.CB:
            primary_bartering_symbol = sec_rec.sedol
        elif sec_rec.sec_type == SecType.EQT:
            primary_bartering_symbol = sec_rec.ric
            secondary_bartering_symbol = sec_rec.secondary_ric

        blocked_side = Side.SELL if side == Side.BUY or side == Side.BTC else Side.BUY
        if sec_rec.executed_tradable:
            # block_bartering_symbol_side_events[primary_bartering_symbol] = (blocked_side, "ALL_BUT_FILL")
            block_bartering_symbol_side_events[primary_bartering_symbol] = (blocked_side, "ALL")
            if secondary_bartering_symbol:
                # block_bartering_symbol_side_events[secondary_bartering_symbol] = (blocked_side, "ALL_BUT_FILL")
                block_bartering_symbol_side_events[secondary_bartering_symbol] = (blocked_side, "ALL")
        else:
            # sec_rec.settled_tradable is used to allow plan activation on opposite side
            # any plan activated on opposite side that is not executed_tradable is certainly settled_tradable
            # all plans start with executed_tradable if they are not settled_tradable - disallowing opposite side
            # plan parallel activation is prevented for plans that are neither settled_tradable nor executed_tradable
            block_bartering_symbol_side_events[primary_bartering_symbol] = (blocked_side, "ALL")
            if secondary_bartering_symbol:
                block_bartering_symbol_side_events[secondary_bartering_symbol] = (blocked_side, "ALL")
        return True  # block applied [blocked side either settled_tradable or fully not tradable]

    def get_subscription_data(self) -> Tuple[List[str], List[str], Dict[str, Tuple[Side, str]], str | None]:
        pair_plan_: PairPlan
        # store bartering symbol and side of sec that are not intraday true

        block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]] = {}
        pair_plan_, _ = self.plan_cache.get_pair_plan()
        plan_leg1 = pair_plan_.pair_plan_params.plan_leg1
        leg1_sec_rec: SecurityRecord = (
            self.plan_cache.static_data.get_security_record_from_ticker(plan_leg1.sec.sec_id))
        self.update_plan_leg_block(plan_leg1, leg1_sec_rec, block_bartering_symbol_side_events)

        plan_leg2 = pair_plan_.pair_plan_params.plan_leg2
        leg2_ticker: str = plan_leg2.sec.sec_id
        leg2_side: Side = plan_leg2.side
        secondary_symbols: List[str] = []
        leg2_sec_rec: SecurityRecord = self.plan_cache.static_data.get_security_record_from_ticker(leg2_ticker)
        self.update_plan_leg_block(plan_leg2, leg2_sec_rec, block_bartering_symbol_side_events)

        if self.plan_cache.static_data.is_cn_connect_restricted_(
                leg2_sec_rec, "B" if leg2_side == Side.BUY or leg2_side == Side.BTC else "S"):
            qfii_ric = leg2_sec_rec.ric
            secondary_symbols.append(qfii_ric)
        else:
            secondary_symbols.append(leg2_sec_rec.ric)
            secondary_symbols.append(leg2_sec_rec.secondary_ric)
        mplan: str | None = pair_plan_.pair_plan_params.mplan
        return [leg1_sec_rec.sedol], secondary_symbols, block_bartering_symbol_side_events, mplan

    @staticmethod
    def executor_trigger(bartering_data_manager_: BarteringDataManager, plan_cache: PlanCache):
        street_book: StreetBook = StreetBook(bartering_data_manager_, plan_cache)
        street_book_thread = Thread(target=street_book.run, daemon=True).start()
        block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]]
        sedol_symbols, ric_symbols, block_bartering_symbol_side_events, mplan = street_book.get_subscription_data()
        listener_sedol_key = [f'{sedol_symbol}-' for sedol_symbol in sedol_symbols]
        listener_ric_key = [f'{ric_symbol}-' for ric_symbol in ric_symbols]
        listener_id = f"{listener_sedol_key}-{listener_ric_key}-{os.getpid()}"
        street_book.bartering_link.log_key = plan_cache.get_key()
        street_book.bartering_link.subscribe(listener_id, StreetBook.asyncio_loop, ric_filters=ric_symbols,
                                              sedol_filters=sedol_symbols,
                                              block_bartering_symbol_side_events=block_bartering_symbol_side_events,
                                              mplan=mplan)
        # trigger executor md start [ name to use tickers ]

        return street_book, street_book_thread

    """ 1 instance = 1 thread = 1 pair plan"""

    def __init__(self, bartering_data_manager_: BarteringDataManager, plan_cache: PlanCache):
        super().__init__(bartering_data_manager_, plan_cache)
        # helps prevent reverse bartering on intraday positions where security level constraints exists
        self.meta_no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side] = {}
        # current plan bartering symbol and side dict - helps block intraday non recovery position updates
        self.meta_bartering_symbol_side_dict: Dict[str, Side] = {}
        self.meta_symbols_n_sec_id_source_dict: Dict[str, str] = {}  # stores symbol and symbol type [RIC, SEDOL, etc.]
        self.cn_eqt_min_qty: Final[int] = 100
        self.allow_multiple_unfilled_chore_pairs_per_plan: Final[bool] = allow_multiple_unfilled_chore_pairs_per_plan \
            if (allow_multiple_unfilled_chore_pairs_per_plan :=
                executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_plan")) is not None else False
        self.leg1_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg2_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg1_consumed_depth: MarketDepth | None = None
        self.leg2_consumed_depth: MarketDepth | None = None

        self.pair_street_book_id: str | None = None

        self.bartering_data_manager: BarteringDataManager = bartering_data_manager_
        self.plan_cache: PlanCache = plan_cache
        self.sym_ovrw_getter: Callable = self.plan_cache.get_symbol_overview_from_symbol_obj
        self.buy_leg_single_lot_usd_notional: int | None = None
        self.sell_leg_single_lot_usd_notional: int | None = None
        self.last_set_unack_call_date_time: DateTime | None = None

        self._system_control_update_date_time: DateTime | None = None
        self._plan_brief_update_date_time: DateTime | None = None
        self._chore_snapshots_update_date_time: DateTime | None = None
        self._chore_journals_update_date_time: DateTime | None = None
        self._fills_journals_update_date_time: DateTime | None = None
        self._chore_limits_update_date_time: DateTime | None = None
        self._new_chores_update_date_time: DateTime | None = None
        self._new_chores_processed_slice: int = 0
        self._top_of_books_update_date_time: DateTime | None = None
        self._tob_leg1_update_date_time: DateTime | None = None
        self._tob_leg2_update_date_time: DateTime | None = None
        self._processed_tob_date_time: DateTime | None = None

        self.plan_limit: PlanLimits | None = None
        self.last_chore_timestamp: DateTime | None = None

        self.leg1_notional: float = 0
        self.leg2_notional: float = 0

        self.chore_pase_seconds = 0
        # 1-time prepare param used by update_aggressive_market_depths_in_cache call for this plan [init on first use]
        self.aggressive_symbol_side_tuples_dict: Dict[str, List[Tuple[str, str]]] = {}
        StreetBook.initialize_underlying_http_routes()  # Calling underlying instances init

        # attributes to be set in run method
        self.leg_1_symbol: str | None = None
        self.leg_1_side: Side | None = None
        self.leg_1_symbol_cache: SymbolCache | None = None
        self.leg_2_symbol: str | None = None
        self.leg_2_side: Side | None = None
        self.leg_2_symbol_cache: SymbolCache | None = None

    @property
    def derived_class_type(self):
        raise StreetBook

    def check_chore_eligibility(self, side: Side, check_notional: float) -> bool:
        plan_brief, self._plan_brief_update_date_time = \
            self.plan_cache.get_plan_brief(self._plan_brief_update_date_time)
        if side == Side.BUY:
            if plan_brief.pair_buy_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False
        else:
            if plan_brief.pair_sell_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False

    def init_meta_dicts(self):
        pair_plan_: PairPlan
        pair_plan_, _ = self.plan_cache.get_pair_plan()
        plan_leg1 = pair_plan_.pair_plan_params.plan_leg1
        leg1_ticker: str = plan_leg1.sec.sec_id
        leg1_sec_rec: SecurityRecord = self.plan_cache.static_data.get_security_record_from_ticker(leg1_ticker)
        leg1_bartering_symbol: str = leg1_sec_rec.sedol
        self.meta_bartering_symbol_side_dict[leg1_bartering_symbol] = plan_leg1.side
        if not leg1_sec_rec.executed_tradable:
            replenishing_side = Side.SELL if plan_leg1.side == Side.BUY else Side.BUY
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg1_ticker] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg1_bartering_symbol] = replenishing_side
        self.meta_symbols_n_sec_id_source_dict[leg1_bartering_symbol] = SecurityIdSource.SEDOL

        # TODO Non CN Leg2 or Leg3 handling upgrades to be done here
        plan_leg2 = pair_plan_.pair_plan_params.plan_leg2
        leg2_ticker: str = plan_leg2.sec.sec_id
        leg2_sec_rec: SecurityRecord = self.plan_cache.static_data.get_security_record_from_ticker(leg2_ticker)
        qfii_ric, connect_ric = leg2_sec_rec.ric, leg2_sec_rec.secondary_ric
        if qfii_ric:
            self.meta_bartering_symbol_side_dict[qfii_ric] = plan_leg2.side
            self.meta_symbols_n_sec_id_source_dict[qfii_ric] = SecurityIdSource.RIC
        if connect_ric:
            self.meta_bartering_symbol_side_dict[connect_ric] = plan_leg2.side
            self.meta_symbols_n_sec_id_source_dict[connect_ric] = SecurityIdSource.RIC
        if not leg2_sec_rec.executed_tradable:
            replenishing_side = Side.SELL if plan_leg2.side == Side.BUY else Side.BUY
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg2_ticker] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[qfii_ric] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[connect_ric] = replenishing_side

    def start_pos_cache(self) -> bool:
        self.init_meta_dicts()

        with self.plan_cache.re_ent_lock:
            plan_limits: PlanLimitsBaseModel
            plan_limits_tuple = self.plan_cache.get_plan_limits()
            if plan_limits_tuple:
                plan_limits, _ = plan_limits_tuple
            else:
                err = (f"start_pos_cache failed get_plan_limits returned invalid plan_limits_tuple: "
                       f"{plan_limits_tuple}")
                logging.error(err)
                return False
            logging.info(f"{plan_limits.id=};;;{plan_limits=}")
            brokers: List[BrokerBaseModel] = plan_limits.eligible_brokers
            sod_n_intraday_pos_dict: Dict[str, Dict[str, List[Position]]] | None = None
            if hasattr(self.bartering_link, "load_positions_by_symbols_dict"):
                sod_n_intraday_pos_dict = self.bartering_link.load_positions_by_symbols_dict(
                    self.meta_symbols_n_sec_id_source_dict)

            return self.plan_cache.pos_cache.start(brokers, sod_n_intraday_pos_dict,
                                                    self.meta_bartering_symbol_side_dict,
                                                    self.meta_symbols_n_sec_id_source_dict,
                                                    self.meta_no_executed_tradable_symbol_replenishing_side_dict,
                                                    config_dict)
        return False  # NOQA - code should ideally never reach here [defensive]

    def init_aggressive_symbol_side_tuples_dict(self) -> bool:
        if self.aggressive_symbol_side_tuples_dict:
            logging.warning("init_aggressive_symbol_side_tuples_dict invoked on pre-initialized "
                            "aggressive_symbol_side_tuples_dict")
            return True  # its pre-initialized, not ideal, but not wrong either

        # 2. get pair-plan: no checking if it's updated since last checked (required for TOB extraction)
        pair_plan: PairPlan = self._get_latest_pair_plan()
        if pair_plan is None:
            logging.error("init_aggressive_symbol_side_tuples_dict invoked but no pair plan found in cache")
            return False

        leg1 = pair_plan.pair_plan_params.plan_leg1
        leg1_sec: str = leg1.sec.sec_id
        leg1_aggressive_side_str: str = "ASK" if leg1.side == Side.BUY else "BID"
        leg2 = pair_plan.pair_plan_params.plan_leg2
        leg2_sec: str = leg2.sec.sec_id
        leg2_aggressive_side_str: str = "ASK" if leg2.side == Side.BUY else "BID"

        self.aggressive_symbol_side_tuples_dict = {"symbol_side_tuple_list": [(leg1_sec, leg1_aggressive_side_str),
                                                                              (leg2_sec, leg2_aggressive_side_str)]}
        return True

    def extract_plan_specific_legs_from_tobs(self, pair_plan, top_of_books) -> Tuple[TopOfBook | None,
                                                                                       TopOfBook | None]:
        leg1_tob: TopOfBook | None
        leg2_tob: TopOfBook | None
        leg1_tob, leg2_tob = self.extract_legs_from_tobs(pair_plan, top_of_books)
        # Note: Not taking tob mutex since symbol never changes in tob
        if leg1_tob is not None and self.plan_cache.leg1_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg1_tob.symbol=} not found in plan_cache, "
                          f"pair_plan_key: {get_pair_plan_log_key(pair_plan)}")
            leg1_tob = None
        if leg2_tob is not None and self.plan_cache.leg2_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg2_tob.symbol=} not found in plan_cache, "
                          f"pair_plan_key: {get_pair_plan_log_key(pair_plan)}")
            leg2_tob = None
        return leg1_tob, leg2_tob

    @staticmethod
    def extract_legs_from_tobs(pair_plan, top_of_books) -> Tuple[TopOfBook | None, TopOfBook | None]:
        leg1_tob: TopOfBook | None = None
        leg2_tob: TopOfBook | None = None
        error = False
        # Note: Not taking tob mutex since symbol never changes in tob
        if pair_plan.pair_plan_params.plan_leg1.sec.sec_id == top_of_books[0].symbol:
            leg1_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_plan.pair_plan_params.plan_leg2.sec.sec_id == top_of_books[1].symbol:
                    leg2_tob = top_of_books[1]
                else:
                    tob_str = str(top_of_books[1])
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol=}, "
                                  f"expected: {pair_plan.pair_plan_params.plan_leg2.sec.sec_id}, pair_plan_key: "
                                  f" {get_pair_plan_log_key(pair_plan)};;; top_of_book: {tob_str}")
                    error = True
        elif pair_plan.pair_plan_params.plan_leg2.sec.sec_id == top_of_books[0].symbol:
            leg2_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_plan.pair_plan_params.plan_leg1.sec.sec_id == top_of_books[1].symbol:
                    leg1_tob = top_of_books[1]
                else:
                    tob_str = str(top_of_books[1])
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol=}, "
                                  f"expected: {pair_plan.pair_plan_params.plan_leg1.sec.sec_id} pair_plan_key: "
                                  f"{get_pair_plan_log_key(pair_plan)};;; top_of_book: {tob_str}")
                    error = True
        else:
            tob_str = str(top_of_books[1])
            logging.error(f"unexpected security found in top_of_books[0]: {top_of_books[0].symbol=}, "
                          f"expected either: {pair_plan.pair_plan_params.plan_leg1.sec.sec_id} or "
                          f"{pair_plan.pair_plan_params.plan_leg2.sec.sec_id} in pair_plan_key: "
                          f"{get_pair_plan_log_key(pair_plan)};;; top_of_book: {tob_str}")
            error = True
        if error:
            return None, None
        else:
            return leg1_tob, leg2_tob

    def set_unack(self, system_symbol: str, unack_state: bool, internal_ord_id: str):
        self.last_set_unack_call_date_time: DateTime = DateTime.utcnow()
        if self.plan_cache._pair_plan.pair_plan_params.plan_leg1.sec.sec_id == system_symbol:
            self.plan_cache.set_has_unack_leg1(unack_state, internal_ord_id)
        if self.plan_cache._pair_plan.pair_plan_params.plan_leg2.sec.sec_id == system_symbol:
            self.plan_cache.set_has_unack_leg2(unack_state, internal_ord_id)

    def check_unack(self, system_symbol: str):
        pair_plan, _ = self.plan_cache.get_pair_plan()
        if pair_plan.pair_plan_params.plan_leg1.sec.sec_id == system_symbol:
            if self.plan_cache.has_unack_leg1():
                return True
            # else not required, final return False covers this
        elif pair_plan.pair_plan_params.plan_leg2.sec.sec_id == system_symbol:
            if self.plan_cache.has_unack_leg2():
                return True
            # else not required, final return False covers this
        else:
            logging.error(f"check_unack: unknown {system_symbol=}, check force failed for plan_cache: "
                          f"{self.plan_cache.get_key()}, "
                          f"pair_plan_key_key: {get_pair_plan_log_key(pair_plan)}")
        return False

    def place_new_chore(self, top_of_book: TopOfBook, sym_overview: SymbolOverviewBaseModel | SymbolOverview,
                        plan_brief: PlanBriefBaseModel, chore_limits: ChoreLimitsBaseModel, pair_plan: PairPlan,
                        new_ord: NewChoreBaseModel, err_dict: Dict[str, any] | None = None,
                        check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        ret_val: int
        if err_dict is None:
            err_dict = dict()
        system_symbol = new_ord.security.sec_id
        sec_pos_extended_list: List[SecPosExtended]
        is_availability: bool
        # is_availability, sec_pos_extended = self.plan_cache.pos_cache.extract_availability(new_ord)
        is_availability, sec_pos_extended_list = self.plan_cache.pos_cache.extract_availability_list(new_ord)
        if not is_availability:
            logging.error(f"dropping opportunity, no sufficiently available SOD/PTH/Locate for {new_ord.px=}, "
                          f"{new_ord.qty=}, key: {get_symbol_side_key([(system_symbol, new_ord.side)])}")
            err_dict["extract_availability"] = f"{system_symbol}"
            return ChoreControl.ORDER_CONTROL_EXTRACT_AVAILABILITY_FAIL
        if new_ord.mplan is None:
            new_ord.mplan = pair_plan.pair_plan_params.mplan
        try:
            if not SecPosExtended.validate_all(system_symbol, new_ord.side, sec_pos_extended_list):
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL

            # block new chore if any prior unack chore exist
            if self.check_unack(system_symbol):
                error_msg: str = (f"past chore on {system_symbol=} is in unack state, dropping chore with "
                                  f"{new_ord.px=}, {new_ord.qty=}, key: {get_new_chore_log_key(new_ord)}")
                # if self.plan_cache.has_unack_leg():
                #     error_msg: str = (f"past chore on: {'leg1' if self.plan_cache.has_unack_leg1() else 'leg2'} is in "
                #                       f"unack state, dropping chore with symbol: {new_ord.security.sec_id} "
                #                       f"{new_ord.px=}, {new_ord.qty=}, key: {get_new_chore_log_key(new_ord)}")
                logging.warning(error_msg)
                return ChoreControl.ORDER_CONTROL_CHECK_UNACK_FAIL

            if ChoreControl.ORDER_CONTROL_SUCCESS == (ret_val := self.check_new_chore(top_of_book, plan_brief,
                                                                                      chore_limits, pair_plan, new_ord,
                                                                                      err_dict, check_mask)):
                # secondary bartering block
                # pair_plan not active: disallow chore from proceeding
                # system not in UAT & not bartering time: disallow chore from proceeding [UAT barters outside hours]
                pair_plan = self._get_latest_pair_plan()
                if pair_plan.plan_state != PlanState.PlanState_ACTIVE or self.market.is_not_uat_nor_bartering_time():
                    logging.error(f"Secondary Block place chore - plan in {pair_plan.plan_state} state (block as "
                                  f"plan either not active or outside market hours)")
                    return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                orig_new_chore_qty = new_ord.qty
                sec_pos_extended: SecPosExtended

                client_ord_id: str = self.get_client_chore_id()
                sec_pos_extended_list_len: int = len(sec_pos_extended_list)
                sent_qty: int = 0
                remaining_qty: int = new_ord.qty
                for idx, sec_pos_extended in enumerate(sec_pos_extended_list):
                    bartering_symbol = sec_pos_extended.security.sec_id
                    symbol_type = "SEDOL" if sec_pos_extended.security.inst_type == InstrumentType.CB else "RIC"
                    account = sec_pos_extended.bartering_account
                    exchange = sec_pos_extended.bartering_route
                    # create_date_time_gmt_epoch_micro_sec = int(DateTime.utcnow().timestamp() * 1_000_000)
                    suffix = "" if 1 == sec_pos_extended_list_len else f".{idx}"
                    client_ord_id += suffix

                    # set unack for subsequent chores - this symbol to be blocked until this chore goes through
                    self.set_unack(system_symbol, True, client_ord_id)
                    if len(sec_pos_extended.positions) < 2:  # 0 is valid in long buy cases
                        if sec_pos_extended_list_len > 1:
                            new_ord.qty = sec_pos_extended.get_extracted_size()
                            # extracted size is 0 if qty split between existing position and fallback broker
                            if new_ord.qty == 0:
                                new_ord.qty = remaining_qty
                            else:
                                remaining_qty -= new_ord.qty
                        else:
                            # else not needed - new_ord.qty is fully filled by single position
                            pass
                    else:
                        logging.error(f"Unexpected: extract_availability_list returned sec_pos_extended_list has "
                                      f"{len(sec_pos_extended.positions)=}, expected 0 or 1;;;{sec_pos_extended}; "
                                      f"{sec_pos_extended_list}")

                    kwargs = {}
                    if new_ord.mplan is not None:
                        kwargs["mplan"] = new_ord.mplan
                    res, ret_id_or_err_desc = (
                        StreetBook.bartering_link_place_new_chore(new_ord.px, new_ord.qty, new_ord.side, bartering_symbol,
                                                                   system_symbol, symbol_type, account, exchange,
                                                                   client_ord_id=client_ord_id, **kwargs))
                    if not res:
                        # reset unack for subsequent chores to go through - this chore did fail to go through
                        self.set_unack(system_symbol, False, client_ord_id)
                        if 0 != idx:
                            # handle partial fail
                            err_dict["FAILED_QTY"] = orig_new_chore_qty - sent_qty
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                    else:
                        sent_qty += new_ord.qty  # add just this new ord qty
                        sec_pos_extended.consumed = True
                else:  # loop completed - all chores sent successfully
                    return ChoreControl.ORDER_CONTROL_SUCCESS  # chore sent out successfully
            else:
                return ret_val
        except Exception as e:
            logging.exception(f"place_new_chore failed for: {system_symbol} px-qty-new_ord.side: "
                              f"{new_ord.px}-{new_ord.qty}-{new_ord.side}, with exception: {e}")
            return ChoreControl.ORDER_CONTROL_EXCEPTION_FAIL
        finally:
            for sec_pos_extended in sec_pos_extended_list:
                if not sec_pos_extended.consumed:
                    self.plan_cache.pos_cache.return_availability(system_symbol, sec_pos_extended)

    def check_consumable_concentration(self, plan_brief: PlanBrief | PlanBriefBaseModel,
                                       bartering_brief: PairSideBarteringBriefBaseModel, qty: int,
                                       side_str: str) -> bool:
        if bartering_brief.consumable_concentration - qty < 0:
            if bartering_brief.consumable_concentration == 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, unexpected: consumable_concentration found 0! "
                              f"for start_cache: {self.plan_cache.get_key()}, plan_brief_key: "
                              f"{get_plan_brief_log_key(plan_brief)}")
            else:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, not enough consumable_concentration: "
                              f"{plan_brief.pair_sell_side_bartering_brief.consumable_concentration} needed: {qty=}, "
                              f"for start_cache: {self.plan_cache.get_key()}, plan_brief_key: "
                              f"{get_plan_brief_log_key(plan_brief)}")
            return False
        else:
            return True

    def check_plan_limits(self, pair_plan: PairPlan, plan_brief: PlanBriefBaseModel,
                           top_of_book: TopOfBook, chore_limits: ChoreLimitsBaseModel,
                           new_ord: NewChoreBaseModel, chore_usd_notional: float, err_dict: Dict[str, any]):
        checks_passed = ChoreControl.ORDER_CONTROL_SUCCESS
        symbol_overview: SymbolOverviewBaseModel | None = None
        system_symbol = new_ord.security.sec_id

        symbol_overview_tuple = \
            self.plan_cache.get_symbol_overview_from_symbol(system_symbol)
        if symbol_overview_tuple:
            symbol_overview, _ = symbol_overview_tuple
            if not symbol_overview:
                logging.error(f"blocked generated chore, symbol_overview missing for: {new_ord}, "
                              f"plan_cache key: {self.plan_cache.get_key()}, limit up/down check needs "
                              f"symbol_overview, plan_brief_key: {get_plan_brief_log_key(plan_brief)}")
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            elif not symbol_overview.limit_dn_px or not symbol_overview.limit_up_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked chore, {get_new_chore_log_key(new_ord)} chore, limit up/down px not available "
                              f"limit-dn px: {symbol_overview.limit_dn_px}, limit-up px: {symbol_overview.limit_up_px=}"
                              f";;;{new_ord=}")
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            # else all good to continue limit checks
        bartering_brief = None
        if new_ord.side == Side.SELL:
            bartering_brief = plan_brief.pair_sell_side_bartering_brief
            # Sell - not allowed less than limit dn px
            # limit down - TODO : Important : Upgrade this to support bartering at Limit Dn within the limit Dn limit
            if new_ord.px < symbol_overview.limit_dn_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, px expected higher than limit-dn px: "
                              f"{symbol_overview.limit_dn_px}, found {new_ord.px} for "
                              f"plan_cache: {self.plan_cache.get_key()}, plan_brief_log_key: "
                              f"{get_plan_brief_log_key(plan_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_LIMIT_DOWN_FAIL
        elif new_ord.side == Side.BUY:
            bartering_brief = plan_brief.pair_buy_side_bartering_brief
            # Buy - not allowed more than limit up px
            # limit up - TODO : Important : Upgrade this to support bartering at Limit Up within the limit Up limit
            if new_ord.px > symbol_overview.limit_up_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, px expected lower than limit-up px: "
                              f"{symbol_overview.limit_up_px}, found {new_ord.px} for "
                              f"plan_cache: {self.plan_cache.get_key()}, plan_brief: "
                              f"{get_plan_brief_log_key(plan_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_LIMIT_UP_FAIL
        else:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            err_str_ = (f"blocked generated unsupported side: {new_ord.side} chore, symbol_side_key: "
                        f"{get_symbol_side_key([(system_symbol, new_ord.side)])}")
            logging.error(err_str_)
            raise Exception(err_str_)

        # max_open_chores_per_side check
        if bartering_brief.consumable_open_chores <= 0:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated {new_ord.side} chore, not enough consumable_open_chores: "
                          f"{bartering_brief.consumable_open_chores} for plan_cache: "
                          f"{self.plan_cache.get_key()}, plan_brief_key: {get_plan_brief_log_key(plan_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

        # max_open_single_leg_notional check
        if chore_usd_notional > bartering_brief.consumable_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked chore with symbol_side_key: {get_new_chore_log_key(new_ord)}, "
                          f"breaches available consumable open notional, expected less than: "
                          f"{plan_brief.pair_sell_side_bartering_brief.consumable_open_notional}, chore needs:"
                          f" {chore_usd_notional}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

        # Checking max_single_leg_notional
        if chore_usd_notional > bartering_brief.consumable_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated {new_ord.side} chore, breaches available consumable notional, "
                          f"expected less than: {bartering_brief.consumable_notional}, "
                          f"chore needs: {chore_usd_notional} for plan_cache: {self.plan_cache.get_key()}, "
                          f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL

        # checking max concentration
        if not self.check_consumable_concentration(plan_brief, bartering_brief, new_ord.qty,
                                                   "SELL" if new_ord.side == Side.SELL else "BUY"):
            checks_passed |= ChoreControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

        # checking max participation
        barterd_notional: float = (
                self.plan_limit.max_single_leg_notional - plan_brief.pair_sell_side_bartering_brief.consumable_notional)
        projected_notional = barterd_notional + chore_usd_notional
        min_allowed_notional = self.plan_limit.market_barter_volume_participation.min_allowed_notional
        # skip participation check if projected_notional is < min_allowed_notional
        if min_allowed_notional < projected_notional:
            if top_of_book.last_barter is None:
                # if no last barter implies auction/SOD, allow barters were upto min_allowed_notional, disallow
                warn_ = (f"blocked generated chore, participation check failed no barters in market yet, consumption: "
                         f"{barterd_notional} with chore_notional: {chore_usd_notional}, {projected_notional=} is higher"
                         f" than {min_allowed_notional=} for chore key: {get_new_chore_log_key(new_ord)}")
                logging.warning(f"{warn_}")
                checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL
            elif new_ord.security.inst_type != InstrumentType.EQT:
                consumable_participation_qty: int = get_consumable_participation_qty_http(
                    system_symbol, new_ord.side,
                    self.plan_limit.market_barter_volume_participation.applicable_period_seconds,
                    self.plan_limit.market_barter_volume_participation.max_participation_rate,
                    StreetBook.asyncio_loop)
                if consumable_participation_qty is not None and consumable_participation_qty != 0:
                    key = get_plan_brief_log_key(plan_brief)
                    if consumable_participation_qty - new_ord.qty < 0:
                        checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL
                        consumable_participation_notional: float = consumable_participation_qty * new_ord.usd_px
                        # @@@ below error log is used in specific test case for string matching - if changed here
                        # needs to be changed in test also
                        warn_ = (f"blocked generated chore, not enough consumable_participation_qty available, "
                                 f"expected higher than chore qty: {new_ord.qty}, found {consumable_participation_qty}"
                                 f" / notional: {consumable_participation_notional} for chore key: "
                                 f"{get_new_chore_log_key(new_ord)};;;plan_cache key: {self.plan_cache.get_key()}, "
                                 f"plan_brief key: {key}")
                        if not pair_plan.pair_plan_params or not pair_plan.pair_plan_params.hedge_ratio:
                            hedge_ratio = 1
                        else:
                            hedge_ratio = pair_plan.pair_plan_params.hedge_ratio
                        if (consumable_participation_notional * hedge_ratio) > self.plan_limit.min_chore_notional:
                            err_dict["consumable_participation_qty"] = f"{consumable_participation_qty}"
                            logging.warning(f"hedge_ratio adjusted retryable {warn_}")
                        else:
                            logging.warning(f"hedge_ratio adjusted non-retryable {warn_}")
                    else:  # check passed - no action
                        logging.debug(f"{consumable_participation_qty=}; {new_ord=}")

                else:
                    plan_brief_key: str = get_plan_brief_log_key(plan_brief)
                    # @@@ below error log is used in specific test case for string matching - if changed here
                    # needs to be changed in test also
                    logging.error(f"Received unusable {consumable_participation_qty=} from "
                                  f"get_consumable_participation_qty_http, {system_symbol=}, side: "
                                  f"{new_ord.side}, applicable_period_seconds: "
                                  f"{self.plan_limit.market_barter_volume_participation.applicable_period_seconds}, "
                                  f"plan_brief_key: {plan_brief_key}, check failed")
                    checks_passed |= ChoreControl.ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL
            # else not required, pass the check, EQT is barterd on SWAP, thus absolute participation capped by CB
            # participation instead. SWAP brokers have their participation checks built on top based their entire flow
        # else not required, all good check is passed, allow the chore through

        # checking max_net_filled_notional
        if chore_usd_notional > plan_brief.consumable_nett_filled_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked {new_ord.side} generated chore, not enough consumable_nett_filled_notional "
                          f"available, remaining {plan_brief.consumable_nett_filled_notional=}, "
                          f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL

        return checks_passed

    def check_chore_limits(self, top_of_book: TopOfBook, chore_limits: ChoreLimitsBaseModel,
                           pair_plan: PairPlan, new_ord: NewChoreBaseModel, chore_usd_notional: float,
                           check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS):
        sys_symbol = new_ord.security.sec_id
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        # TODO: min chore notional is to be a chore opportunity condition instead of chore check
        checks_passed_ = ChoreControl.check_min_chore_notional(pair_plan.pair_plan_params.plan_mode,
                                                               self.plan_limit, new_ord, chore_usd_notional)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        if check_mask == ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip other chore checks, they were conducted before, this is qty down adjusted chore

        checks_passed_ = ChoreControl.check_max_chore_notional(chore_limits, chore_usd_notional, sys_symbol,
                                                               new_ord.side)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        # chore qty / chore contract qty checks
        if (InstrumentType.INSTRUMENT_TYPE_UNSPECIFIED != new_ord.security.inst_type != InstrumentType.EQT and
                chore_limits.max_contract_qty):
            checks_passed_ = ChoreControl.check_max_chore_contract_qty(chore_limits, new_ord.qty, sys_symbol,
                                                                       new_ord.side)
        else:
            checks_passed_ = ChoreControl.check_max_chore_qty(chore_limits, new_ord.qty, sys_symbol, new_ord.side)
        # apply chore qty / chore contract qty check result
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        if new_ord.security.inst_type == InstrumentType.EQT:
            checks_passed_ = ChoreControl.check_min_eqt_chore_qty(chore_limits, new_ord.qty, sys_symbol, new_ord.side)
            # apply min eqt chore qty check result
            if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
                checks_passed |= checks_passed_

        if sys_symbol == self.leg_1_symbol:
            symbol_cache = self.leg_1_symbol_cache
        else:
            symbol_cache = self.leg_2_symbol_cache
        checks_passed_ = ChoreControl.check_px(top_of_book, self.sym_ovrw_getter, chore_limits, new_ord.px,
                                               new_ord.usd_px, new_ord.qty, new_ord.side,
                                               sys_symbol, symbol_cache)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        return checks_passed

    def check_new_chore(self, top_of_book: TopOfBook, plan_brief: PlanBriefBaseModel,
                        chore_limits: ChoreLimitsBaseModel, pair_plan: PairPlan, new_ord: NewChoreBaseModel,
                        err_dict: Dict[str, any], check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        chore_usd_notional = new_ord.usd_px * new_ord.qty

        checks_passed |= self.check_chore_limits(top_of_book, chore_limits, pair_plan, new_ord, chore_usd_notional,
                                                 check_mask)
        if check_mask == ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip plan checks, they were conducted before, this is qty down adjusted chore

        checks_passed |= self.check_plan_limits(pair_plan, plan_brief, top_of_book, chore_limits, new_ord,
                                                 chore_usd_notional, err_dict)

        # TODO LAZY Read config "chore_pace_seconds" to pace chores (needed for testing - not a limit)
        if self.chore_pase_seconds > 0:
            # allow chores only after chore_pase_seconds
            if self.last_chore_timestamp.add(seconds=self.chore_pase_seconds) < DateTime.now():
                checks_passed |= ChoreControl.ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL

        return checks_passed

    @staticmethod
    def create_n_run_md_shell_script(pair_plan, generation_start_file_path, generation_stop_file_path):
        exch_code = "SS" if pair_plan.pair_plan_params.plan_leg1.exch_id == "SSE" else "SZ"

        config_file_path = get_simulator_config_file_path(pair_plan.id)
        create_stop_cpp_md_shell_script(str(generation_start_file_path), str(generation_stop_file_path),
                                        config_file_path=str(config_file_path))
        os.chmod(generation_stop_file_path, stat.S_IRWXU)

        if os.path.exists(generation_start_file_path):
            # first stopping script if already exists
            process = subprocess.Popen([f"{generation_stop_file_path}"])
            # wait for scripts to complete execution and delete existing stop and start scripts
            process.wait()
            logging.debug("Called Stop script - found start script existing already")
            time.sleep(1)

        create_start_cpp_md_shell_script(str(generation_start_file_path), str(config_file_path),
                                         instance_id=str(pair_plan.id))
        os.chmod(generation_start_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{generation_start_file_path}"])
        time.sleep(3)

    def _mark_plan_state_as_error(self, pair_plan: PairPlanBaseModel):
        alert_str: str = \
            (f"Marking plan_state to ERROR for plan: {self.pair_street_book_id} "
             f"{get_pair_plan_log_key(pair_plan)};;; {pair_plan=}")
        logging.info(alert_str)
        guaranteed_call_pair_plan_client(
            PairPlanBaseModel, email_book_service_http_client.patch_all_pair_plan_client,
            _id=pair_plan.id, plan_state=PlanState.PlanState_ERROR.value)

    def _mark_plan_state_as_pause(self, pair_plan: PairPlanBaseModel):
        alert_str: str = \
            (f"graceful pause processing for plan: {self.pair_street_book_id} "
             f"{get_pair_plan_log_key(pair_plan)};;; {pair_plan=}")
        logging.info(alert_str)
        guaranteed_call_pair_plan_client(
            PairPlanBaseModel, email_book_service_http_client.patch_all_pair_plan_client,
            _id=pair_plan.id, plan_state=PlanState.PlanState_PAUSED.value)

    def _set_plan_pause_when_contact_limit_check_fails(self):
        pair_plan_tuple = self.plan_cache.get_pair_plan()
        if pair_plan_tuple is not None:
            pair_plan, _ = pair_plan_tuple
            logging.critical("Putting Activated Plan to PAUSE, found contact_limits breached already, "
                             f"pair_plan_key: {get_pair_plan_log_key(pair_plan)};;; {pair_plan=}")
            guaranteed_call_pair_plan_client(
                PairPlanBaseModel, email_book_service_http_client.patch_all_pair_plan_client,
                _id=pair_plan.id, plan_state=PlanState.PlanState_PAUSED.value)
        else:
            logging.error(f"Can't find pair_plan in plan_cache, found contact_limits "
                          f"breached but couldn't update plan_status: {str(self.plan_cache)=}")

    def check_n_pause_plan_before_run_if_contact_limit_breached(self):
        # Checking if contact_limits are still not breached
        is_contact_limits_breached_model_list: List[IsContactLimitsBreached] = (
            post_book_service_http_client.is_contact_limits_breached_query_client())

        if len(is_contact_limits_breached_model_list) == 1:
            is_contact_limits_breached: bool = (
                is_contact_limits_breached_model_list[0].is_contact_limits_breached)
            if is_contact_limits_breached:
                self._set_plan_pause_when_contact_limit_check_fails()
            # else not required: if contact_limits are fine then ignore
        elif len(is_contact_limits_breached_model_list) == 0:
            logging.critical("PairPlan service seems down, can't check contact_limits before current plan "
                             "activation - putting plan to pause")
            self._set_plan_pause_when_contact_limit_check_fails()
        else:
            err_str_ = ("is_contact_limits_breached_query_client must return list of exact one "
                        f"IsContactLimitsBreached model, but found "
                        f"{len(is_contact_limits_breached_model_list)=}, "
                        f"{is_contact_limits_breached_model_list=}")
            logging.error(err_str_)

    def run(self):
        db_name = os.environ["DB_NAME"]
        md_shared_memory_name = f"/dev/shm/{db_name}_shm"
        shared_memory_semaphore_name = f"{db_name}_sem"

        ret_val: int = -5000
        # Getting pre-requisites ready before plan active runs
        run_coro = StreetBook.underlying_handle_plan_activate_query_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e_:
            logging.exception(f"underlying_handle_plan_activate_query_http failed for pair_plan_id: "
                              f"{self.pair_street_book_id}; Exiting executor run();;;exception: {e_}")
            return -5001

        max_retry_count: Final[int] = 12
        retry_count: int = 0
        pair_plan_tuple: Tuple[PairPlanBaseModel, DateTime] | None = None
        pair_plan: PairPlanBaseModel | None = None
        lot_notional_ready: bool = False
        log_key: str | None = None
        while pair_plan_tuple is None or pair_plan is None:
            # getting pair_plan
            pair_plan_tuple = self.plan_cache.get_pair_plan()
            if pair_plan_tuple is None:
                logging.error("Can't find pair_plan_tuple even while entered executor's run method, likely bug "
                              "in loading plan_cache with pair_plan")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3000

            pair_plan, _ = pair_plan_tuple
            if pair_plan is None:
                logging.error("Can't find pair_plan from pair_plan_tuple even while entered "
                              "executor's run method, likely bug in loading plan_cache with pair_plan")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3001
            else:
                log_key = get_pair_plan_log_key(pair_plan)

        # setting index for leg1 and leg2 symbols
        self.leg_1_symbol = pair_plan.pair_plan_params.plan_leg1.sec.sec_id
        self.leg_1_side = pair_plan.pair_plan_params.plan_leg1.side
        self.leg_1_symbol_cache = SymbolCacheContainer.get_symbol_cache(self.leg_1_symbol)
        if self.leg_1_symbol_cache is None:
            logging.error(f"Can't find symbol_cache for {self.leg_1_symbol=} - must have been added before triggering "
                          f"StreetBook")
            return -3002

        self.leg_2_symbol = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        self.leg_2_side = pair_plan.pair_plan_params.plan_leg2.side
        self.leg_2_symbol_cache = SymbolCacheContainer.get_symbol_cache(self.leg_2_symbol)
        if self.leg_2_symbol_cache is None:
            logging.error(f"Can't find symbol_cache for {self.leg_2_symbol=} - must have been added before triggering "
                          f"StreetBook")
            return -3003

        scripts_dir = PurePath(__file__).parent.parent / "scripts"
        # start file generator
        start_sh_file_path = scripts_dir / f"start_ps_id_{pair_plan.id}_md.sh"
        stop_sh_file_path = scripts_dir / f"stop_ps_id_{pair_plan.id}_md.sh"

        try:
            StreetBook.create_n_run_md_shell_script(pair_plan, start_sh_file_path, stop_sh_file_path)
            if not self.start_pos_cache():
                return -6000
            self.check_n_pause_plan_before_run_if_contact_limit_breached()

            shared_memory_found = False
            while 1:
                if not shared_memory_found:
                    shared_memory_found = SymbolCacheContainer.check_if_shared_memory_exists(
                        md_shared_memory_name, f"/{shared_memory_semaphore_name}")
                    if not shared_memory_found:
                        time.sleep(1)
                        continue
                    # else not required: if shared_memory is found - all good, starting internal run

                # setting server_ready_state to 3 to notify ui that md server is up
                email_book_service_http_client.patch_pair_plan_client({"_id": pair_plan.id,
                                                                           "server_ready_state": 3})

                try:
                    ret_val = self.internal_run()
                except Exception as e:
                    logging.exception(f"internal_run returned with exception; sending again for pair_plan_id: "
                                      f"{self.pair_street_book_id}, pair_plan_key: {log_key};;;exception: {e}")
                finally:
                    if ret_val == 1:
                        logging.info(f"explicit plan shutdown requested for pair_plan_id: "
                                     f"{self.pair_street_book_id}, going down, pair_plan_key: {log_key}")
                        self.plan_cache.set_pair_plan(None)
                        break
                    elif ret_val != 0:
                        logging.error(f"Error: internal_run returned, code: {ret_val}; sending again for "
                                      f"pair_plan_id: {self.pair_street_book_id}, pair_plan_key: {log_key}")
                    else:
                        pair_plan, _ = self.plan_cache.get_pair_plan()
                        if pair_plan.plan_state != PlanState.PlanState_DONE:
                            # don't stop the plan with Done, just pause [later resume if inventory becomes available]
                            self._mark_plan_state_as_pause(pair_plan)
                            logging.debug(f"PlanStatus with pair_plan_id: {self.pair_street_book_id} marked Paused"
                                          f", pair_plan_key: {log_key}")
                            ret_val = 0
                        else:
                            logging.error(f"unexpected, pair_plan_id: {self.pair_street_book_id} was already marked"
                                          f" Done, pair_plan_key: {log_key}")
                            ret_val = -4000  # helps find the error location
                        break
        except Exception as e:
            logging.exception(f"exception occurred in run method of pair_plan_id: {self.pair_street_book_id}, "
                              f"pair_plan_key: {log_key};;;exception: {e}")
            ret_val = -4001
        finally:
            # running, stop md script
            logging.info(f"Executor: {self.pair_street_book_id} running, stop md script")
            process = subprocess.Popen([f"{stop_sh_file_path}"])
            process.wait()

            if ret_val != 0 and ret_val != 1:
                self._mark_plan_state_as_error(pair_plan)
                logging.critical(f"Executor: {self.pair_street_book_id} thread is going down due to unrecoverable "
                                 f"error - get tech to manually restart/recycle executor;;;{pair_plan=}")

            # removing created scripts
            try:
                if os.path.exists(start_sh_file_path):
                    os.remove(start_sh_file_path)
                if os.path.exists(stop_sh_file_path):
                    os.remove(stop_sh_file_path)
            except Exception as e:
                err_str_ = (f"exception occurred for pair_plan_key: {log_key} while deleting md scripts;;;"
                            f"exception: {e}")
                logging.exception(err_str_)

            # checking if shared_memory and semaphore are detached
            # checking shm first
            while True:
                result = subprocess.run(
                    ['ls', '-l', md_shared_memory_name],
                    text=True,  # Capture text output
                    stdout=subprocess.PIPE,  # Capture standard output
                    stderr=subprocess.PIPE  # Capture standard error
                )
                if not result.stdout:
                    # if no result found - shared memory is detached successfully
                    logging.info(f"Shared Memory: {md_shared_memory_name}, detached successfully")
                    break
                else:
                    time.sleep(0.1)
                    logging.warning(f"Shared Memory: {md_shared_memory_name} still exists post stop script call - "
                                    f"lopping till it is detached")

            # checking semaphore
            sem_loc_path = f"/dev/shm/sem.{shared_memory_semaphore_name}"
            while True:
                result = subprocess.run(
                    ['ls', '-l', sem_loc_path],
                    text=True,  # Capture text output
                    stdout=subprocess.PIPE,  # Capture standard output
                    stderr=subprocess.PIPE  # Capture standard error
                )
                if not result.stdout:
                    # if no result found - shared memory is detached successfully
                    logging.info(f"Posix semaphore: {sem_loc_path}, detached successfully")
                    break
                else:
                    time.sleep(0.1)
                    logging.warning(f"Posix semaphore: {sem_loc_path} still exists post stop script call - "
                                    f"lopping till it is detached")

        logging.info(f"Executor returning from run")
        return ret_val

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency plan - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.usd_fx

    @perf_benchmark_sync_callable
    def _check_tob_n_place_non_systematic_chore(self, new_chore: NewChoreBaseModel, pair_plan: PairPlan,
                                                plan_brief: PlanBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                                top_of_books: List[TopOfBook]) -> int:
        leg1_tob: TopOfBook | None
        leg2_tob: TopOfBook | None
        barter_tob: TopOfBook | None = None
        leg1_tob, leg2_tob = self.extract_plan_specific_legs_from_tobs(pair_plan, top_of_books)

        if leg1_tob is not None:
            if pair_plan.pair_plan_params.plan_leg1.sec.sec_id == new_chore.security.sec_id:
            # if self.plan_cache.leg1_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg1_tob

        if barter_tob is None and leg2_tob is not None:
            if pair_plan.pair_plan_params.plan_leg2.sec.sec_id == new_chore.security.sec_id:
            # if self.plan_cache.leg2_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg2_tob

        if barter_tob is None:
            err_str_ = f"unable to send new_chore: no matching leg in this plan: {new_chore} " \
                       f"pair_plan_key: {get_pair_plan_log_key(pair_plan)};;;" \
                       f"{self.plan_cache=}, {pair_plan=}"
            logging.error(err_str_)
            return False
        else:
            usd_px = self.get_usd_px(new_chore.px, new_chore.security.sec_id)
            ord_sym_ovrw = self.plan_cache.get_symbol_overview_from_symbol_obj(new_chore.security.sec_id)
            chore_placed: int = self.place_new_chore(barter_tob, ord_sym_ovrw, plan_brief, chore_limits, pair_plan,
                                                     new_chore)
            return chore_placed

    @staticmethod
    def get_leg1_leg2_ratio(leg1_px: float, leg2_px: float) -> float:
        if math.isclose(leg2_px, 0):
            return 0
        return leg1_px / leg2_px

    @staticmethod
    def get_cb_lot_size_from_cb_symbol_overview_(
            cb_symbol_overview: SymbolOverviewBaseModel | SymbolOverview) -> int | None:
        """
        Assumes non-none cb_symbol_overview passed
        """
        if cb_symbol_overview.lot_size:
            # CB lot size sent as FV, divide by 100 makes it true lot size
            cb_lot_size = int(cb_symbol_overview.lot_size / 100)
            return cb_lot_size
        else:
            return None

    @classmethod
    def get_cb_lot_size_from_cb_symbol_overview(cls,
            cb_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None) -> int | None:
        if cb_symbol_overview:
            return cls.get_cb_lot_size_from_cb_symbol_overview_(cb_symbol_overview)
        else:
            return None

    def _place_chore(self, pair_plan: PairPlanBaseModel, plan_brief: PlanBriefBaseModel,
                     chore_limits: ChoreLimitsBaseModel, quote: QuoteBaseModel, tob: TopOfBook, leg_sym_ovrw) -> float:
        """returns float posted notional of the chore sent"""
        # fail-safe
        pair_plan = self.plan_cache.get_pair_plan_obj()
        if pair_plan is not None:
            # If pair_plan not active, don't act, just return [check MD state and take action if required]
            if pair_plan.plan_state != PlanState.PlanState_ACTIVE or self.market.is_not_uat_nor_bartering_time():  # UAT barters outside bartering hours
                logging.error("Blocked place chore - plan not in activ state")
                return 0  # no chore sent = no posted notional
        if not (quote.qty == 0 or math.isclose(quote.px, 0)):
            ask_usd_px: float = self.get_usd_px(quote.px, tob.symbol)
            security = SecurityBaseModel(sec_id=tob.symbol)
            new_ord = NewChoreBaseModel(security=security, side=Side.BUY, px=quote.px, usd_px=ask_usd_px, qty=quote.qty)
            chore_placed = self.place_new_chore(tob, leg_sym_ovrw, plan_brief, chore_limits, pair_plan, new_ord)
            if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
                posted_notional = quote.px * quote.qty
                return posted_notional
            else:
                logging.error(f"0 value found in ask TOB - ignoring {quote.px=}, {quote.qty=}, pair_plan_key: "
                              f"{get_pair_plan_log_key(pair_plan)}")
            return 0  # no chore sent = no posted notional

    @perf_benchmark_sync_callable
    def _check_tob_and_place_chore(self, pair_plan: PairPlanBaseModel | PairPlan, plan_brief: PlanBriefBaseModel,
                                   chore_limits: ChoreLimitsBaseModel, top_of_books: List[TopOfBook]) -> int:
        posted_leg1_notional: float = 0
        posted_leg2_notional: float = 0
        leg1_tob: TopOfBook | None
        leg2_tob: TopOfBook | None
        barter_tob: TopOfBook
        leg1_tob, leg2_tob = self.extract_plan_specific_legs_from_tobs(pair_plan, top_of_books)
        leg1_sym_ovrw = self.leg_1_symbol_cache.so
        leg2_sym_ovrw = self.leg_2_symbol_cache.so

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
        if leg1_tob is not None and self.plan_cache.leg1_bartering_symbol is not None:
            if abs(self.leg1_notional) <= abs(self.leg2_notional):
                # process primary leg
                if pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:  # execute aggressive buy
                    posted_leg1_notional = self._place_chore(pair_plan, plan_brief, chore_limits, leg1_tob.ask_quote,
                                                             leg1_tob, leg1_sym_ovrw)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg1_notional = self._place_chore(pair_plan, plan_brief, chore_limits, leg1_tob.bid_quote,
                                                             leg1_tob, leg1_sym_ovrw)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if leg2_tob is not None and self.plan_cache.leg2_bartering_symbol is not None:
            if abs(self.leg2_notional) <= abs(self.leg1_notional):
                # process secondary leg
                if pair_plan.pair_plan_params.plan_leg2.side == Side.BUY:  # execute aggressive buy
                    posted_leg2_notional = self._place_chore(pair_plan, plan_brief, chore_limits, leg2_tob.ask_quote,
                                                             leg2_tob, leg2_sym_ovrw)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg2_notional = self._place_chore(pair_plan, plan_brief, chore_limits, leg2_tob.bid_quote,
                                                             leg2_tob, leg2_sym_ovrw)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
            self.last_chore_timestamp = DateTime.now()
            self.leg1_notional += posted_leg1_notional
            self.leg2_notional += posted_leg2_notional
            logging.debug(f"plan-matched ToB for pair_plan_key {get_pair_plan_log_key(pair_plan)}: "
                          f"{[str(tob) for tob in top_of_books]}")
        return chore_placed

    def _both_side_tob_has_data(self, leg_1_tob: TopOfBook, leg_2_tob: TopOfBook) -> bool:
        if leg_1_tob is not None and leg_2_tob is not None:
            if leg_1_tob.last_update_date_time is not None and leg_2_tob.last_update_date_time is not None:
                return True
        return False

    def _get_tob_bid_quote_px(self, tob: TopOfBook) -> float | None:
        if tob.bid_quote is not None:
            return tob.bid_quote.px
        else:
            logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
            return None

    def _get_tob_ask_quote_px(self, tob: TopOfBook) -> float | None:
        if tob.ask_quote is not None:
            return tob.ask_quote.px
        else:
            logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
            return None

    def _get_tob_bid_quote_last_update_date_time(self, tob: TopOfBook) -> DateTime | None:
        if tob.bid_quote is not None:
            return tob.bid_quote.last_update_date_time
        else:
            logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
            return None

    def _get_tob_ask_quote_last_update_date_time(self, tob: TopOfBook) -> DateTime | None:
        if tob.ask_quote is not None:
            return tob.ask_quote.last_update_date_time
        else:
            logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
            return None

    @perf_benchmark_sync_callable
    def _check_tob_and_place_chore_test(self, pair_plan: PairPlanBaseModel | PairPlan,
                                        plan_brief: PlanBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                        top_of_books: List[TopOfBook]) -> int:
        buy_top_of_book: TopOfBook | None = None
        sell_top_of_book: TopOfBook | None = None
        is_cb_buy: bool = True

        if pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:
            buy_symbol = pair_plan.pair_plan_params.plan_leg1.sec.sec_id
            sell_symbol = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
        else:
            is_cb_buy = False
            buy_symbol = pair_plan.pair_plan_params.plan_leg2.sec.sec_id
            sell_symbol = pair_plan.pair_plan_params.plan_leg1.sec.sec_id

        buy_sym_ovrw: SymbolOverviewBaseModel | SymbolOverview | None = (
            self.plan_cache.get_symbol_overview_from_symbol_obj(buy_symbol))
        sell_sym_ovrw: SymbolOverviewBaseModel | SymbolOverview | None = (
            self.plan_cache.get_symbol_overview_from_symbol_obj(sell_symbol))

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        leg_1_top_of_book: TopOfBook = (
            self.leg_1_symbol_cache.get_top_of_book(self._top_of_books_update_date_time))
        leg_2_top_of_book: TopOfBook = (
            self.leg_2_symbol_cache.get_top_of_book(self._top_of_books_update_date_time))

        if self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
            top_of_books = [leg_1_top_of_book, leg_2_top_of_book]
            latest_update_date_time: DateTime | None = None
            for top_of_book in top_of_books:
                if latest_update_date_time is None:
                    tob_symbol = top_of_book.symbol
                    if tob_symbol == buy_symbol:
                        buy_top_of_book = top_of_book
                        sell_top_of_book = None
                    elif tob_symbol == sell_symbol:
                        sell_top_of_book = top_of_book
                        buy_top_of_book = None
                    else:
                        err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                   f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}"
                        logging.error(err_str_)
                        raise Exception(err_str_)
                    latest_update_date_time = top_of_book.last_update_date_time
                else:
                    latest_update_date_time_ = top_of_book.last_update_date_time
                    if latest_update_date_time_ > latest_update_date_time:
                        tob_symbol = top_of_book.symbol
                        if tob_symbol == buy_symbol:
                            buy_top_of_book = top_of_book
                            sell_top_of_book = None
                        elif tob_symbol == sell_symbol:
                            sell_top_of_book = top_of_book
                            buy_top_of_book = None
                        else:
                            err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                       f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}"
                            logging.error(err_str_)
                            raise Exception(err_str_)
                        latest_update_date_time = latest_update_date_time_
            # tob tuple last_update_date_time is set to least of the 2 tobs update time
            # setting it to latest_update_date_time to allow chore to be placed
            self._top_of_books_update_date_time = latest_update_date_time

            if buy_top_of_book is not None:
                bid_quote_last_update_date_time = self._get_tob_bid_quote_last_update_date_time(buy_top_of_book)
                if bid_quote_last_update_date_time == self._top_of_books_update_date_time:
                    buy_tob_bid_px = self._get_tob_bid_quote_px(buy_top_of_book)
                    if buy_tob_bid_px == 100:
                        px = random.randint(95, 100)
                        qty = random.randint(85, 95)
                        usd_px: float = self.get_usd_px(px, buy_symbol)
                        inst_type: InstrumentType = InstrumentType.CB if is_cb_buy else InstrumentType.EQT
                        security = Security(sec_id=buy_symbol, sec_id_source=SecurityIdSource.TICKER,
                                            inst_type=inst_type)
                        new_ord = NewChoreBaseModel(security=security, side=Side.BUY, px=px, usd_px=usd_px, qty=qty)
                        chore_placed = self.place_new_chore(buy_top_of_book, buy_sym_ovrw, plan_brief, chore_limits,
                                                            pair_plan, new_ord)
            elif sell_top_of_book is not None:
                ask_quote_last_update_date_time = self._get_tob_ask_quote_last_update_date_time(sell_top_of_book)
                if ask_quote_last_update_date_time == self._top_of_books_update_date_time:
                    sell_tob_ask_px = self._get_tob_ask_quote_px(sell_top_of_book)
                    if sell_tob_ask_px == 120:
                        px = random.randint(100, 110)
                        qty = random.randint(95, 105)
                        usd_px: float = self.get_usd_px(px, sell_symbol)
                        inst_type: InstrumentType = InstrumentType.EQT if is_cb_buy else InstrumentType.CB
                        security = Security(sec_id=sell_symbol, sec_id_source=SecurityIdSource.TICKER,
                                            inst_type=inst_type)
                        new_ord = NewChoreBaseModel(security=security, side=Side.SELL, px=px, usd_px=usd_px, qty=qty)
                        chore_placed = self.place_new_chore(sell_top_of_book, sell_sym_ovrw, plan_brief, chore_limits,
                                                            pair_plan, new_ord)
            else:
                err_str_ = "TOB updates could not find any updated buy or sell tob, " \
                           f"plan_brief_key: {get_plan_brief_log_key(plan_brief)}"
                logging.debug(err_str_)
            return chore_placed
        return False

    def is_consumable_notional_tradable(self, plan_brief: PlanBriefBaseModel, ol: ChoreLimitsBaseModel):
        if (not self.buy_leg_single_lot_usd_notional) or (not self.sell_leg_single_lot_usd_notional):
            err: str = (f"unexpected {self.buy_leg_single_lot_usd_notional=} or "
                        f"{self.sell_leg_single_lot_usd_notional=}; is_consumable_notional_tradable will return false "
                        f"for {get_plan_brief_log_key(plan_brief)}")
            logging.error(err)
            return False
        min_tradable_notional = int(max(self.buy_leg_single_lot_usd_notional, self.sell_leg_single_lot_usd_notional))
        if plan_brief.pair_sell_side_bartering_brief.consumable_notional <= min_tradable_notional:
            # sell leg of plan is done - if either leg is done - plan is done
            logging.warning(f"sell-remaining-notional="
                            f"{int(plan_brief.pair_sell_side_bartering_brief.consumable_notional)} is <= "
                            f"{min_tradable_notional=}, no further chores possible; for "
                            f"{plan_brief.pair_sell_side_bartering_brief.security.sec_id}, "
                            f"{plan_brief.pair_sell_side_bartering_brief.side};;;{get_plan_brief_log_key(plan_brief)}")
            return True
        # else not required, more notional to consume on sell leg - plan done is set to 1 (no error, not done)
        if plan_brief.pair_buy_side_bartering_brief.consumable_notional <= min_tradable_notional:
            # buy leg of plan is done - if either leg is done - plan is done
            logging.warning(f"buy-remaining-notional="
                            f"{int(plan_brief.pair_buy_side_bartering_brief.consumable_notional)} is <= "
                            f"{min_tradable_notional=}, no further chores possible; for "
                            f"{plan_brief.pair_buy_side_bartering_brief.security.sec_id}, "
                            f"{plan_brief.pair_buy_side_bartering_brief.side};;;{get_plan_brief_log_key(plan_brief)}")
            return True
        return False

    def is_pair_plan_done(self, plan_brief: PlanBriefBaseModel, ol: ChoreLimitsBaseModel) -> int:
        """
        Args:
            plan_brief:
            ol: current chore limits as set by system / user
        Returns:
            0: indicates done; no notional to consume on at-least 1 leg & no-open chores for this plan in market
            -1: indicates needs-processing; plan has notional left to consume on both legs or has unack leg
            +number: TODO: indicates finishing; no notional to consume on at-least 1 leg but open chores found for plan
        """
        plan_done: bool = False
        if self.plan_cache.has_unack_leg():  # chore snapshot of immediate prior sent new-chore may not have arrived
            return -1
        open_chore_count: int = self.plan_cache.get_open_chore_count_from_cache()
        if 0 == open_chore_count:
            plan_done = self.is_consumable_notional_tradable(plan_brief, ol)
        # else not required, if plan has open chores, it's not done yet
        if plan_done:
            logging.warning(f"Plan is_consumable_notional_tradable returned done, plan will be closed / marked done "
                            f"for {get_plan_brief_log_key(plan_brief)}")
            time.sleep(5)  # allow for any pending post cancel ack race fills to arrive
            return 0
        else:
            return -1  # in progress

    def _get_latest_system_control(self) -> SystemControlBaseModel | None:
        system_control: SystemControlBaseModel | None = None
        system_control_tuple = self.bartering_data_manager.bartering_cache.get_system_control()
        if system_control_tuple is None:
            logging.warning("no kill_switch found yet - plan will not trigger until kill_switch arrives")
            return None
        else:
            system_control, self._system_control_update_date_time = system_control_tuple
        return system_control

    def is_plan_ready_for_next_opportunity(self, log_error: bool = False) -> bool:
        open_chore_count: int = self.plan_cache.get_open_chore_count_from_cache()
        has_unack_leg = self.plan_cache.has_unack_leg()
        if has_unack_leg:
            if log_error:  # [chore impact not applied yet]
                logging.debug(f"blocked opportunity search, has unack leg and {open_chore_count} open chore(s)")
            if open_chore_count == 0:
                secs_till_last_ser_unack_call = (DateTime.utcnow() - self.last_set_unack_call_date_time).total_seconds()
                acceptable_secs_btw_unack_and_chore_snapshot_open_count_update = 2  # secs
                if secs_till_last_ser_unack_call > acceptable_secs_btw_unack_and_chore_snapshot_open_count_update:
                    logging.exception(f"Found {open_chore_count=} but found some chore's either leg set as unack, "
                                      f"last unack was set {secs_till_last_ser_unack_call} secs ago, acceptable is <="
                                      f"{acceptable_secs_btw_unack_and_chore_snapshot_open_count_update} secs")
                else:
                    logging.info(f"Found {open_chore_count=} along with some chore's either leg set as unack but "
                                 f"last unack was set {secs_till_last_ser_unack_call} secs ago, which is <="
                                 f"expected {acceptable_secs_btw_unack_and_chore_snapshot_open_count_update} secs")
            return False
        if not self.plan_limit.max_open_chores_per_side:
            logging.debug(f"blocked opportunity search, {self.plan_limit.max_open_chores_per_side=} not set")
            return False
        else:
            if self.plan_limit.max_open_chores_per_side < open_chore_count:
                if log_error:
                    logging.debug(f"blocked opportunity search, has {open_chore_count} open chore(s), allowed: "
                                  f"{self.plan_limit.max_open_chores_per_side=}")
                return False
        if not self.allow_multiple_unfilled_chore_pairs_per_plan:
            if self.plan_cache.check_has_open_chore_with_no_fill_from_cache():
                if log_error:
                    logging.debug(f"blocked opportunity search, has open chore with no fill yet")
                return False
            # no else needed - no unfilled chores - default return true is good

        return True

    def _get_latest_pair_plan(self) -> PairPlan | None:
        pair_plan_tuple = self.plan_cache.get_pair_plan()
        if pair_plan_tuple is not None:
            pair_plan, _ = pair_plan_tuple
            if pair_plan:
                return pair_plan
            else:
                logging.error(f"pair_plan in pair_plan_tuple is None for: {self.plan_cache = }")
        else:
            logging.error(f"pair_plan_tuple is None for: {self.plan_cache = }")
        return None

    def _get_single_lot_usd_notional_for_symbol_overview(self,
                                                         symbol_overview: SymbolOverviewBaseModel | SymbolOverview):
        if self.plan_cache.static_data.is_cb_ticker(symbol_overview.symbol):
            lot_size = self.get_cb_lot_size_from_cb_symbol_overview(symbol_overview)
        else:
            lot_size = symbol_overview.lot_size
        return lot_size * symbol_overview.closing_px / self.usd_fx

    def _init_lot_notional(self, pair_plan: PairPlanBaseModel | PairPlan) -> bool:
        if self.buy_leg_single_lot_usd_notional and self.sell_leg_single_lot_usd_notional:
            return True  # happy path
        else:
            buy_leg: PlanLegBaseModel | PlanLeg | None = None
            sell_leg: PlanLegBaseModel | PlanLeg | None = None
            cb_side = Side.SIDE_UNSPECIFIED
            if pair_plan.pair_plan_params.plan_leg1.side == Side.BUY:
                cb_side = Side.BUY
                buy_leg = pair_plan.pair_plan_params.plan_leg1
                if pair_plan.pair_plan_params.plan_leg2.side == Side.SELL:
                    sell_leg = pair_plan.pair_plan_params.plan_leg2
                else:
                    logging.error(f"_init_lot_notional: pair plan has mismatching sell & buy legs, leg1 is "
                                  f"BUY & leg2 is not SELL: {pair_plan.pair_plan_params.plan_leg2.side};;;"
                                  f"{pair_plan=}")
            elif pair_plan.pair_plan_params.plan_leg1.side == Side.SELL:
                cb_side = Side.SELL
                sell_leg = pair_plan.pair_plan_params.plan_leg1
                if pair_plan.pair_plan_params.plan_leg2.side == Side.BUY:
                    buy_leg = pair_plan.pair_plan_params.plan_leg2
                else:
                    logging.error(f"_init_lot_notional: pair plan has mismatching sell & buy legs, leg1 is "
                                  f"SELL & leg2 is not BUY: {pair_plan.pair_plan_params.plan_leg2.side};;;"
                                  f"{pair_plan=}")
            else:
                logging.error(f"_init_lot_notional: unexpected side found in leg1 of pair_plan: "
                              f"{pair_plan.pair_plan_params.plan_leg1.side};;;{pair_plan=}")
            if buy_leg and sell_leg:
                buy_symbol_overview_tuple: Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None
                buy_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None
                if buy_symbol_overview_tuple := self.plan_cache.get_symbol_overview_from_symbol(buy_leg.sec.sec_id):
                    buy_symbol_overview, _ = buy_symbol_overview_tuple
                    if buy_symbol_overview.lot_size and buy_symbol_overview.closing_px:
                        self.buy_leg_single_lot_usd_notional = (
                            self._get_single_lot_usd_notional_for_symbol_overview(buy_symbol_overview))

                sell_symbol_overview_tuple: Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None
                sell_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None
                if sell_symbol_overview_tuple := self.plan_cache.get_symbol_overview_from_symbol(sell_leg.sec.sec_id):
                    sell_symbol_overview, _ = sell_symbol_overview_tuple
                    if sell_symbol_overview.lot_size and sell_symbol_overview.closing_px:
                        self.sell_leg_single_lot_usd_notional = (
                            self._get_single_lot_usd_notional_for_symbol_overview(sell_symbol_overview))
        if self.buy_leg_single_lot_usd_notional and self.sell_leg_single_lot_usd_notional:
            return True
        else:
            return False

    def internal_run(self):
        logging.info("Started street_book internal_run")
        pair_plan_id = None
        while 1:
            self.plan_limit = None
            try:
                logging.debug("street_book going to acquire semaphore")
                # self.plan_cache.notify_semaphore.acquire()
                SymbolCacheContainer.acquire_semaphore()
                # remove all unprocessed signals from semaphore, logic handles all new updates in single iteration
                # clear_semaphore(self.plan_cache.notify_semaphore)
                logging.debug("street_book signaled")

                # -1. refreshing shared memory obj
                update_success = SymbolCacheContainer.update_md_cache_from_shared_memory()
                if not update_success:
                    # cache didn't update for this semaphore release - ignoring this cycle
                    continue
                # else not required: all fine if cache updates as expected

                # 0. Checking if plan_cache stopped (happens most likely when plan is not ongoing anymore)
                if self.plan_cache.stopped:
                    # indicates explicit shutdown requested from server, set_pair_plan(None) called at return point
                    logging.debug(f"street_book {self.plan_cache.stopped=} indicates explicit shutdown requested")
                    return 1

                # 1. check if contact status has updated since we last checked
                system_control: SystemControlBaseModel | None = self._get_latest_system_control()
                if system_control is None:
                    logging.debug(f"{system_control=} going for retry")
                    continue

                # 2. get pair-plan: no checking if it's updated since last checked (required for TOB extraction)
                pair_plan: PairPlan = self._get_latest_pair_plan()
                if pair_plan is None:
                    return -1
                elif pair_plan_id is None:
                    pair_plan_id = pair_plan.id

                # primary bartering block
                # pair_plan not active: disallow proceeding
                # system not in UAT & not bartering time: disallow chore from proceeding [UAT barters outside hours]
                if pair_plan.plan_state != PlanState.PlanState_ACTIVE or self.market.is_not_uat_nor_bartering_time():
                    self.process_cxl_request(force_cxl_only=True)
                    continue
                else:
                    plan_limits_tuple = self.plan_cache.get_plan_limits()
                    self.plan_limit, plan_limits_update_date_time = plan_limits_tuple

                # uncomment below code to test stress perf
                # func_for_log_book_perf_check(pair_plan_id)

                # 3. check if any cxl chore is requested and send out [continue new loop after]
                if self.process_cxl_request():
                    continue

                plan_brief: PlanBriefBaseModel | None = None
                # plan doesn't need to check if plan_brief is updated or not
                # plan_brief_tuple = self.plan_cache.get_plan_brief(self._plan_brief_update_date_time)
                plan_brief_tuple = self.plan_cache.get_plan_brief()
                if plan_brief_tuple:
                    plan_brief, self._plan_brief_update_date_time = plan_brief_tuple
                    if plan_brief:
                        pass
                    else:
                        logging.error(f"can't proceed, plan_brief found None for plan-cache: "
                                      f"{self.plan_cache.get_key()};;; [{self.plan_cache=}]")
                        continue  # go next run - we don't stop processing for one faulty plan_cache
                else:
                    logging.error(f"can't proceed! plan_brief_tuple: {plan_brief_tuple} not found for plan-cache: "
                                  f"{self.plan_cache.get_key()};;; [{self.plan_cache=}]")
                    continue  # go next run - we don't stop processing for one faulty plan_cache

                chore_limits: ChoreLimitsBaseModel | None = None
                chore_limits_tuple = self.bartering_data_manager.bartering_cache.get_chore_limits()
                if chore_limits_tuple:
                    chore_limits, _ = chore_limits_tuple
                    if chore_limits and self.plan_limit:
                        plan_done_counter = self.is_pair_plan_done(plan_brief, chore_limits)
                        if 0 == plan_done_counter:
                            return 0  # triggers graceful shutdown
                        elif -1 != plan_done_counter:
                            # plan is finishing: waiting to close pending plan_done_counter number of open chores
                            continue
                        # else not needed - move forward, more processing needed to complete the plan
                    else:
                        logging.error(f"Can't proceed: chore_limits/plan_limit not found for bartering_cache: "
                                      f"{self.bartering_data_manager.bartering_cache}; {self.plan_cache=}")
                        continue  # go next run - we don't stop processing for one faulty plan_cache
                else:
                    logging.error(f"chore_limits_tuple not found for plan: {self.plan_cache}, can't proceed")
                    continue  # go next run - we don't stop processing for one faulty plan_cache

                # 4.1 check symbol overviews [if they don't exist - continue]
                leg1_symbol_overview = self.leg_1_symbol_cache.so
                leg2_symbol_overview = self.leg_2_symbol_cache.so
                if (leg1_symbol_overview is not None) and (leg2_symbol_overview is not None):
                    pass
                else:
                    logging.warning(f"found either leg1 or leg2 symbol overview as None;;;"
                                    f"{leg1_symbol_overview=}, {leg2_symbol_overview=}")
                    continue  # go next run - we don't stop processing - retry in next iteration

                # 4.2 get top_of_book (new or old to be checked by respective plan based on plan requirement)
                leg_1_top_of_book = self.leg_1_symbol_cache.get_top_of_book()
                leg_2_top_of_book = self.leg_2_symbol_cache.get_top_of_book()

                if not self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
                    logging.warning(f"plans need both sides of TOB to be present, found  only leg_1 or only leg_2 "
                                    f"or neither of them;;;tob found: {leg_1_top_of_book=}, {leg_2_top_of_book=}")
                    continue  # go next run - we don't stop processing for one faulty tob update

                tobs = [leg_1_top_of_book, leg_2_top_of_book]

                # 5. ensure usd_fx is present - otherwise don't proceed - retry later
                if not self.get_usd_fx():
                    logging.error(f"USD fx rate not found for plan: {self.plan_cache.get_key()}, unable to proceed, "
                                  f"fx symbol: {PlanCache.usd_fx_symbol}, we'll retry in next attempt")
                    continue

                # 5.1 init_lot_notionals
                else:
                    lot_notional_ready = self._init_lot_notional(pair_plan)  # error logged in call
                    if not lot_notional_ready:
                        logging.error(f"lot notional not ready for plan: {self.plan_cache.get_key()}, unable to "
                                      f"proceed, {self.buy_leg_single_lot_usd_notional=}, "
                                      f"{self.sell_leg_single_lot_usd_notional=}, we'll retry in next attempt")
                        continue

                # 6. If kill switch is enabled - don't act, just return
                if system_control.kill_switch:
                    logging.debug("not-progressing: kill switch enabled")
                    continue

                # 7. continue only if past-pair (iff triggered) has no open/unack chores
                if not self.is_plan_ready_for_next_opportunity(log_error=True):
                    continue

                # 8. If any manual new_chore requested: apply risk checks (maybe no plan param checks?) & send out
                new_chores_and_date_tuple = self.plan_cache.get_new_chore(self._new_chores_update_date_time)
                if new_chores_and_date_tuple is not None:
                    new_chores, self._new_chores_update_date_time = new_chores_and_date_tuple
                    if new_chores is not None:
                        final_slice = len(new_chores)
                        unprocessed_new_chores: List[NewChoreBaseModel] = (
                            new_chores[self._new_chores_processed_slice:final_slice])
                        self._new_chores_processed_slice = final_slice
                        for new_chore in unprocessed_new_chores:
                            if system_control and not system_control.kill_switch:
                                self._check_tob_n_place_non_systematic_chore(new_chore, pair_plan, plan_brief,
                                                                             chore_limits, tobs)
                                continue
                            else:
                                # kill switch in force - drop the chore
                                logging.error(f"kill switch is enabled, dropping non-systematic "
                                              f"new-chore request;;;{new_chore=} "
                                              "non-systematic new chore call")
                                continue
                # else no new_chore to process, ignore and move to next step

                if self.market.is_sanity_test_run:
                    self._check_tob_and_place_chore_test(pair_plan, plan_brief, chore_limits, tobs)
                else:
                    self._check_tob_and_place_chore(pair_plan, plan_brief, chore_limits, tobs)
                continue  # all good - go next run
            except Exception as e:
                logging.exception(f"Run for {pair_plan_id=} returned with exception: {e}")
                return -1
        logging.info(f"exiting internal_run of {pair_plan_id=}, graceful shutdown this plan")
        return 0


def func_for_log_book_perf_check(pair_plan_id: int):
    """
    This function is not a part of any code just kept for now temporarily for verifying perf of plan_view
    updates through log analyzer
    """
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import UpdateType
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import plan_view_client_call_log_str
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import \
        photo_book_service_http_client, PlanViewBaseModel
    date_time = DateTime.now()
    log_str = plan_view_client_call_log_str(
        PlanViewBaseModel, photo_book_service_http_client.patch_all_plan_view_client,
        UpdateType.SNAPSHOT_TYPE,
        _id=pair_plan_id, market_premium=float(f"{date_time.minute}.{date_time.second}"))
    logging.db(log_str)
