import asyncio
import datetime
import inspect
import logging
import os
import sys
import threading
import time
from pathlib import PurePath
from threading import Thread
import math
import traceback
from fastapi.encoders import jsonable_encoder
from typing import Callable, Final
import subprocess
import stat
import random
import ctypes

from FluxPythonUtils.scripts.service import Service
from FluxPythonUtils.scripts.utility_functions import clear_semaphore
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecord, SecType

from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import (
    ChoreControl, initialize_chore_control)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_data_manager import BarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.strat_cache import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase, market, config_dict)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    get_consumable_participation_qty_http, get_new_chore_log_key,
    get_strat_brief_log_key, create_stop_md_script, executor_config_yaml_dict, MobileBookMutexManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    create_md_shell_script, MDShellEnvData, email_book_service_http_client, guaranteed_call_pair_strat_client,
    get_premium, pair_strat_client_call_log_str, UpdateType, get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.model_extensions import SecPosExtended
from Flux.PyCodeGenEngine.FluxCodeGenCore.perf_benchmark_decorators import perf_benchmark_sync_callable
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.generated.Pydentic.post_book_service_model_imports import (
    IsPortfolioLimitsBreached)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.post_book.app.post_book_service_helper import (
    post_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.generated.Pydentic.photo_book_service_model_imports import (
    StratViewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.photo_book.app.photo_book_helper import (
    photo_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.mobile_book_cache import (
    MobileBookContainer, ExtendedTopOfBook, ExtendedMarketDepth, LastBarter, MarketBarterVolume, add_container_obj_for_symbol,
    get_mobile_book_container, acquire_notify_semaphore)


def depths_str(depths: List[ExtendedMarketDepth], notional_fx_rate: float | None = None) -> str:
    if not notional_fx_rate:
        notional_fx_rate = 1
    if depths:
        symbol: str = depths[0].symbol
        side = depths[0].side
        ret_str = f" Depths of {symbol}, {side}: ["
        depth: ExtendedMarketDepth
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


class MobileBookContainerCache(BaseModel):
    leg_1_mobile_book_container: MobileBookContainer
    leg_2_mobile_book_container: MobileBookContainer
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class StreetBook(Service):
    # Query Callables
    underlying_get_aggressive_market_depths_query_http: Callable[..., Any] | None = None
    underlying_handle_strat_activate_query_http: Callable[..., Any] | None = None
    underlying_update_residuals_query_http: Callable[..., Any] | None = None

    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    asyncio_loop: asyncio.AbstractEventLoop
    mobile_book_provider: ctypes.CDLL

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.FastApi.street_book_service_http_routes_imports import (
            underlying_get_market_depths_query_http, underlying_handle_strat_activate_query_http,
            underlying_update_residuals_query_http)
        cls.underlying_get_aggressive_market_depths_query_http = underlying_get_market_depths_query_http
        cls.underlying_handle_strat_activate_query_http = underlying_handle_strat_activate_query_http
        cls.underlying_update_residuals_query_http = underlying_update_residuals_query_http

    def update_strat_leg_block(self, strat_leg: StratLeg, sec_rec: SecurityRecord,
                               block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]]) -> bool:
        # ticker: str = strat_leg.sec.sec_id
        side: Side = strat_leg.side
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
            # sec_rec.settled_tradable is used to allow strat activation on opposite side
            # any strat activated on opposite side that is not executed_tradable is certainly settled_tradable
            # all strats start with executed_tradable if they are not settled_tradable - disallowing opposite side
            # strat parallel activation is prevented for strats that are neither settled_tradable nor executed_tradable
            block_bartering_symbol_side_events[primary_bartering_symbol] = (blocked_side, "ALL")
            if secondary_bartering_symbol:
                block_bartering_symbol_side_events[secondary_bartering_symbol] = (blocked_side, "ALL")
        return True  # block applied [blocked side either settled_tradable or fully not tradable]

    def get_subscription_data(self) -> Tuple[List[str], List[str], Dict[str, Tuple[Side, str]], str | None]:
        pair_strat_: PairStrat
        # store bartering symbol and side of sec that are not intraday true

        block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]] = {}
        pair_strat_, _ = self.strat_cache.get_pair_strat()
        strat_leg1 = pair_strat_.pair_strat_params.strat_leg1
        leg1_sec_rec: SecurityRecord = (
            self.strat_cache.static_data.get_security_record_from_ticker(strat_leg1.sec.sec_id))
        self.update_strat_leg_block(strat_leg1, leg1_sec_rec, block_bartering_symbol_side_events)

        strat_leg2 = pair_strat_.pair_strat_params.strat_leg2
        leg2_ticker: str = strat_leg2.sec.sec_id
        leg2_side: Side = strat_leg2.side
        secondary_symbols: List[str] = []
        leg2_sec_rec: SecurityRecord = self.strat_cache.static_data.get_security_record_from_ticker(leg2_ticker)
        self.update_strat_leg_block(strat_leg2, leg2_sec_rec, block_bartering_symbol_side_events)

        if self.strat_cache.static_data.is_cn_connect_restricted_(
                leg2_sec_rec, "B" if leg2_side == Side.BUY or leg2_side == Side.BTC else "S"):
            qfii_ric = leg2_sec_rec.ric
            secondary_symbols.append(qfii_ric)
        else:
            secondary_symbols.append(leg2_sec_rec.ric)
            secondary_symbols.append(leg2_sec_rec.secondary_ric)
        mstrat: str | None = pair_strat_.pair_strat_params.mstrat
        return [leg1_sec_rec.sedol], secondary_symbols, block_bartering_symbol_side_events, mstrat

    @staticmethod
    def executor_trigger(bartering_data_manager_: BarteringDataManager, strat_cache: StratCache,
                         mobile_book_container_cache: MobileBookContainerCache):
        street_book: StreetBook = StreetBook(bartering_data_manager_, strat_cache, mobile_book_container_cache)
        street_book_thread = Thread(target=street_book.run, daemon=True).start()
        block_bartering_symbol_side_events: Dict[str, Tuple[Side, str]]
        sedol_symbols, ric_symbols, block_bartering_symbol_side_events, mstrat = street_book.get_subscription_data()
        listener_sedol_key = [f'{sedol_symbol}-' for sedol_symbol in sedol_symbols]
        listener_ric_key = [f'{ric_symbol}-' for ric_symbol in ric_symbols]
        listener_id = f"{listener_sedol_key}-{listener_ric_key}-{os.getpid()}"
        street_book.bartering_link.log_key = strat_cache.get_key()
        street_book.bartering_link.subscribe(listener_id, StreetBook.asyncio_loop, ric_filters=ric_symbols,
                                              sedol_filters=sedol_symbols,
                                              block_bartering_symbol_side_events=block_bartering_symbol_side_events,
                                              mstrat=mstrat)
        # trigger executor md start [ name to use tickers ]

        return street_book, street_book_thread

    """ 1 instance = 1 thread = 1 pair strat"""

    def __init__(self, bartering_data_manager_: BarteringDataManager, strat_cache: StratCache,
                 mobile_book_container_cache: MobileBookContainerCache):
        super().__init__()
        # helps prevent reverse bartering on intraday positions where security level constraints exists
        self.meta_no_executed_tradable_symbol_replenishing_side_dict: Dict[str, Side] = {}
        # current strat bartering symbol and side dict - helps block intraday non recovery position updates
        self.meta_bartering_symbol_side_dict: Dict[str, Side] = {}
        self.meta_symbols_n_sec_id_source_dict: Dict[str, str] = {}  # stores symbol and symbol type [RIC, SEDOL, etc.]
        self.market = Market(MarketID.IN)
        self.cn_eqt_min_qty: Final[int] = 100
        self.allow_multiple_unfilled_chore_pairs_per_strat: Final[bool] = allow_multiple_unfilled_chore_pairs_per_strat \
            if (allow_multiple_unfilled_chore_pairs_per_strat :=
                executor_config_yaml_dict.get("allow_multiple_unfilled_chore_pairs_per_strat")) is not None else False
        self.leg1_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg2_consumed_depth_time: DateTime = DateTime.utcnow()
        self.leg1_consumed_depth: ExtendedMarketDepth | None = None
        self.leg2_consumed_depth: ExtendedMarketDepth | None = None

        self.pair_street_book_id: str | None = None
        self.internal_new_chore_count: int = 0

        self.bartering_data_manager: BarteringDataManager = bartering_data_manager_
        self.strat_cache: StratCache = strat_cache
        self.sym_ovrw_getter: Callable = self.strat_cache.get_symbol_overview_from_symbol_obj
        self.mobile_book_container_cache: MobileBookContainerCache = mobile_book_container_cache
        self.leg1_fx: float | None = None
        self.buy_leg_single_lot_usd_notional: int | None = None
        self.sell_leg_single_lot_usd_notional: int | None = None

        self._system_control_update_date_time: DateTime | None = None
        self._strat_brief_update_date_time: DateTime | None = None
        self._chore_snapshots_update_date_time: DateTime | None = None
        self._chore_journals_update_date_time: DateTime | None = None
        self._fills_journals_update_date_time: DateTime | None = None
        self._chore_limits_update_date_time: DateTime | None = None
        self._new_chores_update_date_time: DateTime | None = None
        self._new_chores_processed_slice: int = 0
        self._cancel_chores_update_date_time: DateTime | None = None
        self._cancel_chores_processed_slice: int = 0
        self._top_of_books_update_date_time: DateTime | None = None
        self._tob_leg1_update_date_time: DateTime | None = None
        self._tob_leg2_update_date_time: DateTime | None = None
        self._processed_tob_date_time: DateTime | None = None

        self.strat_limit: StratLimits | None = None
        self.last_chore_timestamp: DateTime | None = None

        self.leg1_notional: float = 0
        self.leg2_notional: float = 0

        self.chore_pase_seconds = 0
        # internal rejects to use:  -ive internal_reject_count + current date time as chore id
        self.internal_reject_count = 0
        # 1-time prepare param used by update_aggressive_market_depths_in_cache call for this strat [init on first use]
        self.aggressive_symbol_side_tuples_dict: Dict[str, List[Tuple[str, str]]] = {}
        StreetBook.initialize_underlying_http_routes()  # Calling underlying instances init
        # initialize ChoreControl class vars
        initialize_chore_control()

        # attributes to be set in run method
        self.leg_1_symbol: str | None = None
        self.leg_1_side: Side | None = None
        self.leg_2_symbol: str | None = None
        self.leg_2_side: Side | None = None

    def check_chore_eligibility(self, side: Side, check_notional: float) -> bool:
        strat_brief, self._strat_brief_update_date_time = \
            self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
        if side == Side.BUY:
            if strat_brief.pair_buy_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False
        else:
            if strat_brief.pair_sell_side_bartering_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False

    def init_meta_dicts(self):
        pair_strat_: PairStrat
        pair_strat_, _ = self.strat_cache.get_pair_strat()
        strat_leg1 = pair_strat_.pair_strat_params.strat_leg1
        leg1_ticker: str = strat_leg1.sec.sec_id
        leg1_sec_rec: SecurityRecord = self.strat_cache.static_data.get_security_record_from_ticker(leg1_ticker)
        leg1_bartering_symbol: str = leg1_sec_rec.sedol
        self.meta_bartering_symbol_side_dict[leg1_bartering_symbol] = strat_leg1.side
        if not leg1_sec_rec.executed_tradable:
            replenishing_side = Side.SELL if strat_leg1.side == Side.BUY else Side.BUY
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg1_ticker] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg1_bartering_symbol] = replenishing_side
        self.meta_symbols_n_sec_id_source_dict[leg1_bartering_symbol] = SecurityIdSource.SEDOL

        # TODO Non CN Leg2 or Leg3 handling upgrades to be done here
        strat_leg2 = pair_strat_.pair_strat_params.strat_leg2
        leg2_ticker: str = strat_leg2.sec.sec_id
        leg2_sec_rec: SecurityRecord = self.strat_cache.static_data.get_security_record_from_ticker(leg2_ticker)
        qfii_ric, connect_ric = leg2_sec_rec.ric, leg2_sec_rec.secondary_ric
        if qfii_ric:
            self.meta_bartering_symbol_side_dict[qfii_ric] = strat_leg2.side
            self.meta_symbols_n_sec_id_source_dict[qfii_ric] = SecurityIdSource.RIC
        if connect_ric:
            self.meta_bartering_symbol_side_dict[connect_ric] = strat_leg2.side
            self.meta_symbols_n_sec_id_source_dict[connect_ric] = SecurityIdSource.RIC
        if not leg2_sec_rec.executed_tradable:
            replenishing_side = Side.SELL if strat_leg2.side == Side.BUY else Side.BUY
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[leg2_ticker] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[qfii_ric] = replenishing_side
            self.meta_no_executed_tradable_symbol_replenishing_side_dict[connect_ric] = replenishing_side

    def start_pos_cache(self) -> bool:
        self.init_meta_dicts()

        with self.strat_cache.re_ent_lock:
            strat_limits: StratLimitsBaseModel
            strat_limits_tuple = self.strat_cache.get_strat_limits()
            if strat_limits_tuple:
                strat_limits, _ = strat_limits_tuple
            else:
                err = (f"start_pos_cache failed get_strat_limits returned invalid strat_limits_tuple: "
                       f"{strat_limits_tuple}")
                logging.error(err)
                return False
            logging.info(f"{strat_limits.id=};;;{strat_limits=}")
            brokers: List[BrokerBaseModel] = strat_limits.eligible_brokers
            sod_n_intraday_pos_dict: Dict[str, Dict[str, List[Position]]] | None = None
            if hasattr(self.bartering_link, "load_positions_by_symbols_dict"):
                sod_n_intraday_pos_dict = self.bartering_link.load_positions_by_symbols_dict(
                    self.meta_symbols_n_sec_id_source_dict)

            return self.strat_cache.pos_cache.start(brokers, sod_n_intraday_pos_dict,
                                                    self.meta_bartering_symbol_side_dict,
                                                    self.meta_symbols_n_sec_id_source_dict,
                                                    self.meta_no_executed_tradable_symbol_replenishing_side_dict,
                                                    config_dict)
        return False  # NOQA - code should ideally never reach here [defensive]

    def update_aggressive_market_depths_in_cache(self) -> Tuple[List[ExtendedMarketDepth], List[ExtendedMarketDepth]]:
        if not self.aggressive_symbol_side_tuples_dict:
            if not self.init_aggressive_symbol_side_tuples_dict():
                return [], []  # error logged internally

        # coro needs public method
        run_coro = StreetBook.underlying_get_aggressive_market_depths_query_http(
            self.aggressive_symbol_side_tuples_dict)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        try:
            symbol_side_tuple_list: List = list(self.aggressive_symbol_side_tuples_dict.values())[0]
            sym1, sym1_aggressive_side = symbol_side_tuple_list[0]
            sym2, sym2_aggressive_side = symbol_side_tuple_list[1]
            sym1_filtered_market_depths: List[ExtendedMarketDepth] = []  # sym1 may not be same as strat leg1
            sym2_filtered_market_depths: List[ExtendedMarketDepth] = []  # sym2 may not be same as strat leg2
            sym1_newest_exch_time = None
            sym2_newest_exch_time = None
            md: ExtendedMarketDepth

            # now block for task to finish
            market_depths = future.result()
            # store for subsequent reference
            if market_depths:
                for md in market_depths:
                    if md.qty != 0 and (not math.isclose(md.px, 0)):
                        if md.symbol == sym1:
                            sym1_filtered_market_depths.append(md)
                            if not sym1_newest_exch_time:
                                sym1_newest_exch_time = md.exch_time
                            if md.exch_time > sym1_newest_exch_time:
                                sym1_newest_exch_time = md.exch_time

                        elif md.symbol == sym2:
                            sym2_filtered_market_depths.append(md)
                            if not sym2_newest_exch_time:
                                sym2_newest_exch_time = md.exch_time
                            if not md.exch_time > sym2_newest_exch_time:
                                sym2_newest_exch_time = md.exch_time

                        else:
                            logging.error(f"update_aggressive_market_depths_in_cache failed, expected: {sym1} or "
                                          f"{sym2} found for symbol: {md.symbol}, ignoring depth;;;{md}")
                    else:
                        logging.error(f"update_aggressive_market_depths_in_cache failed, invalid px or qty: {md.px}, "
                                      f"{md.qty} found for symbol: {md.symbol}, ignoring depth;;;{md}")

                # sort by px - most aggressive to passive (reverse sorts big to small)
                sym1_filtered_market_depths.sort(reverse=(sym1_aggressive_side == "ASK"), key=lambda x: x.px)
                sym2_filtered_market_depths.sort(reverse=(sym2_aggressive_side == "ASK"), key=lambda x: x.px)

            if not sym1_filtered_market_depths:
                sym1_side = Side.BUY if sym1_aggressive_side == "ASK" else Side.SELL
                logging.error(f"update_aggressive_market_depths_in_cache failed, no market_depth object found "
                              f"symbol_side_key: {get_symbol_side_key([(sym1, sym1_side)])}")
            if not sym2_filtered_market_depths:
                sym2_side = Side.BUY if sym2_aggressive_side == "ASK" else Side.SELL
                logging.error(f"update_aggressive_market_depths_in_cache failed, no market_depth object found "
                              f"symbol_side_key: {get_symbol_side_key([(sym2, sym2_side)])}")
            self.strat_cache.set_sorted_market_depths(sym1, sym1_aggressive_side, sym1_newest_exch_time,
                                                      sym1_filtered_market_depths)
            self.strat_cache.set_sorted_market_depths(sym2, sym2_aggressive_side, sym2_newest_exch_time,
                                                      sym2_filtered_market_depths)
            return sym1_filtered_market_depths, sym2_filtered_market_depths
        except Exception as e:
            logging.exception(f"update_aggressive_market_depths_in_cache failed for: "
                              f"{str(self.aggressive_symbol_side_tuples_dict)} with exception: {e}")
            return [], []

    def init_aggressive_symbol_side_tuples_dict(self) -> bool:
        if self.aggressive_symbol_side_tuples_dict:
            logging.warning("init_aggressive_symbol_side_tuples_dict invoked on pre-initialized "
                            "aggressive_symbol_side_tuples_dict")
            return True  # its pre-initialized, not ideal, but not wrong either

        # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
        pair_strat: PairStrat = self._get_latest_pair_strat()
        if pair_strat is None:
            logging.error("init_aggressive_symbol_side_tuples_dict invoked but no pair strat found in cache")
            return False

        leg1 = pair_strat.pair_strat_params.strat_leg1
        leg1_sec: str = leg1.sec.sec_id
        leg1_aggressive_side_str: str = "ASK" if leg1.side == Side.BUY else "BID"
        leg2 = pair_strat.pair_strat_params.strat_leg2
        leg2_sec: str = leg2.sec.sec_id
        leg2_aggressive_side_str: str = "ASK" if leg2.side == Side.BUY else "BID"

        self.aggressive_symbol_side_tuples_dict = {"symbol_side_tuple_list": [(leg1_sec, leg1_aggressive_side_str),
                                                                              (leg2_sec, leg2_aggressive_side_str)]}
        return True

    def extract_strat_specific_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[ExtendedTopOfBook | None,
                                                                                       ExtendedTopOfBook | None]:
        leg1_tob: ExtendedTopOfBook | None
        leg2_tob: ExtendedTopOfBook | None
        leg1_tob, leg2_tob = self.extract_legs_from_tobs(pair_strat, top_of_books)
        # Note: Not taking tob mutex since symbol never changes in tob
        if leg1_tob is not None and self.strat_cache.leg1_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg1_tob.symbol=} not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg1_tob = None
        if leg2_tob is not None and self.strat_cache.leg2_bartering_symbol is None:
            logging.debug(f"ignoring ticker: {leg2_tob.symbol=} not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg2_tob = None
        return leg1_tob, leg2_tob

    @staticmethod
    def _get_tob_str(tob: ExtendedTopOfBook) -> str:
        with MobileBookMutexManager(tob):
            return str(tob)

    @staticmethod
    def extract_legs_from_tobs(pair_strat, top_of_books) -> Tuple[ExtendedTopOfBook | None, ExtendedTopOfBook | None]:
        leg1_tob: ExtendedTopOfBook | None = None
        leg2_tob: ExtendedTopOfBook | None = None
        error = False
        # Note: Not taking tob mutex since symbol never changes in tob
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[0].symbol:
            leg1_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[1].symbol:
                    leg2_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol=}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg2.sec.sec_id}, pair_strat_key: "
                                  f" {get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                                  f"{StreetBook._get_tob_str(top_of_books[1])}")
                    error = True
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[0].symbol:
            leg2_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[1].symbol:
                    leg1_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol=}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id} pair_strat_key: "
                                  f"{get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                                  f"{StreetBook._get_tob_str(top_of_books[1])}")
                    error = True
        else:
            logging.error(f"unexpected security found in top_of_books[0]: {top_of_books[0].symbol=}, "
                          f"expected either: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id} or "
                          f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id} in pair_strat_key: "
                          f"{get_pair_strat_log_key(pair_strat)};;; top_of_book: "
                          f"{StreetBook._get_tob_str(top_of_books[1])}")
            error = True
        if error:
            return None, None
        else:
            return leg1_tob, leg2_tob

    def bartering_link_internal_chore_state_update(
            self, chore_event: ChoreEventType, chore_id: str, side: Side | None = None,
            bartering_sec_id: str | None = None, system_sec_id: str | None = None,
            underlying_account: str | None = None, msg: str | None = None):
        # coro needs public method
        run_coro = self.bartering_link.internal_chore_state_update(chore_event, chore_id, side, bartering_sec_id,
                                                                 system_sec_id, underlying_account, msg)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)
        # block for start_executor_server task to finish
        try:
            return future.result()
        except Exception as e:
            logging.exception(f"_internal_reject_new_chore failed with exception: {e}")

    def internal_reject_new_chore(self, new_chore: NewChoreBaseModel, reject_msg: str):
        self.internal_reject_count += 1
        internal_reject_chore_id: str = str(self.internal_reject_count * -1) + str(DateTime.utcnow())
        self.bartering_link_internal_chore_state_update(
            ChoreEventType.OE_INT_REJ, internal_reject_chore_id, new_chore.side, None,
            new_chore.security.sec_id, None, reject_msg)

    def set_unack(self, system_symbol: str, unack_state: bool, internal_ord_id: str):
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg1.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg1(unack_state, internal_ord_id)
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg2.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg2(unack_state, internal_ord_id)

    def check_unack(self, system_symbol: str):
        pair_strat, _ = self.strat_cache.get_pair_strat()
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == system_symbol:
            if self.strat_cache.has_unack_leg1():
                return True
            # else not required, final return False covers this
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == system_symbol:
            if self.strat_cache.has_unack_leg2():
                return True
            # else not required, final return False covers this
        else:
            logging.error(f"check_unack: unknown {system_symbol=}, check force failed for strat_cache: "
                          f"{self.strat_cache.get_key()}, "
                          f"pair_strat_key_key: {get_pair_strat_log_key(pair_strat)}")
        return False

    def place_new_chore(self, top_of_book: ExtendedTopOfBook, sym_overview: SymbolOverviewBaseModel | SymbolOverview,
                        strat_brief: StratBriefBaseModel, chore_limits: ChoreLimitsBaseModel, pair_strat: PairStrat,
                        new_ord: NewChoreBaseModel, err_dict: Dict[str, any] | None = None,
                        check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        ret_val: int
        if err_dict is None:
            err_dict = dict()
        system_symbol = new_ord.security.sec_id
        sec_pos_extended_list: List[SecPosExtended]
        is_availability: bool
        # is_availability, sec_pos_extended = self.strat_cache.pos_cache.extract_availability(new_ord)
        is_availability, sec_pos_extended_list = self.strat_cache.pos_cache.extract_availability_list(new_ord)
        if not is_availability:
            logging.error(f"dropping opportunity, no sufficiently available SOD/PTH/Locate for {new_ord.px=}, "
                          f"{new_ord.qty=}, key: {get_symbol_side_key([(system_symbol, new_ord.side)])}")
            err_dict["extract_availability"] = f"{system_symbol}"
            return ChoreControl.ORDER_CONTROL_EXTRACT_AVAILABILITY_FAIL
        if new_ord.mstrat is None:
            new_ord.mstrat = pair_strat.pair_strat_params.mstrat
        try:
            if not SecPosExtended.validate_all(system_symbol, new_ord.side, sec_pos_extended_list):
                return ChoreControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL

            # block new chore if any prior unack chore exist
            if self.check_unack(system_symbol):
                error_msg: str = (f"past chore on {system_symbol=} is in unack state, dropping chore with "
                                  f"{new_ord.px=}, {new_ord.qty=}, key: {get_new_chore_log_key(new_ord)}")
                # if self.strat_cache.has_unack_leg():
                #     error_msg: str = (f"past chore on: {'leg1' if self.strat_cache.has_unack_leg1() else 'leg2'} is in "
                #                       f"unack state, dropping chore with symbol: {new_ord.security.sec_id} "
                #                       f"{new_ord.px=}, {new_ord.qty=}, key: {get_new_chore_log_key(new_ord)}")
                logging.warning(error_msg)
                return ChoreControl.ORDER_CONTROL_CHECK_UNACK_FAIL

            if ChoreControl.ORDER_CONTROL_SUCCESS == (ret_val := self.check_new_chore(top_of_book, strat_brief,
                                                                                      chore_limits, pair_strat, new_ord,
                                                                                      err_dict, check_mask)):
                # secondary bartering block
                # pair_strat not active: disallow chore from proceeding
                # system not in UAT & not bartering time: disallow chore from proceeding [UAT barters outside hours]
                pair_strat = self._get_latest_pair_strat()
                if pair_strat.strat_state != StratState.StratState_ACTIVE or self.market.is_not_uat_nor_bartering_time():
                    logging.error(f"Secondary Block place chore - strat in {pair_strat.strat_state} state (block as "
                                  f"strat either not active or outside market hours)")
                    return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                orig_new_chore_qty = new_ord.qty
                sec_pos_extended: SecPosExtended
                self.internal_new_chore_count += 1
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
                    internal_ord_id: str = f"{self.bartering_link.inst_id}-{self.internal_new_chore_count}{suffix}"

                    # set unack for subsequent chores - this symbol to be blocked until this chore goes through
                    self.set_unack(system_symbol, True, internal_ord_id)
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
                    if not self.bartering_link_place_new_chore(new_ord.px, new_ord.qty, new_ord.side, bartering_symbol,
                                                             system_symbol, symbol_type, account, exchange,
                                                             internal_ord_id=internal_ord_id, mstrat=new_ord.mstrat):
                        # reset unack for subsequent chores to go through - this chore did fail to go through
                        self.set_unack(system_symbol, False, internal_ord_id)
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
                    self.strat_cache.pos_cache.return_availability(system_symbol, sec_pos_extended)

    def bartering_link_place_new_chore(self, px: float, qty: int, side: Side, bartering_symbol: str, system_symbol: str,
                                     symbol_type: str, account: str, exchange: str,
                                     internal_ord_id: str | None = None, mstrat: str | None = None):
        kwargs = {}
        if mstrat is not None:
            kwargs["mstrat"] = mstrat
        run_coro = self.bartering_link.place_new_chore(px, qty, side, bartering_symbol, system_symbol, symbol_type,
                                                     account, exchange, internal_ord_id=internal_ord_id, **kwargs)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for task to finish [run as coroutine helps enable http call via asyncio, other threads use freed CPU]
        try:
            # ignore 2nd param: _id_or_err_str - logged in call and not used in strat executor yet
            chore_sent_status, _id_or_err_str = future.result()
            return chore_sent_status
        except Exception as e:
            logging.exception(f"bartering_link_place_new_chore failed for {system_symbol=} px-qty-side: {px}-{qty}-{side}"
                              f" with exception;;;{e}")
            return False

    def check_consumable_concentration(self, strat_brief: StratBrief | StratBriefBaseModel,
                                       bartering_brief: PairSideBarteringBriefBaseModel, qty: int,
                                       side_str: str) -> bool:
        if bartering_brief.consumable_concentration - qty < 0:
            if bartering_brief.consumable_concentration == 0:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, unexpected: consumable_concentration found 0! "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            else:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated {side_str} chore, not enough consumable_concentration: "
                              f"{strat_brief.pair_sell_side_bartering_brief.consumable_concentration} needed: {qty=}, "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            return False
        else:
            return True

    def check_strat_limits(self, pair_strat: PairStrat, strat_brief: StratBriefBaseModel,
                           top_of_book: ExtendedTopOfBook, chore_limits: ChoreLimitsBaseModel,
                           new_ord: NewChoreBaseModel, chore_usd_notional: float, err_dict: Dict[str, any]):
        checks_passed = ChoreControl.ORDER_CONTROL_SUCCESS
        symbol_overview: SymbolOverviewBaseModel | None = None
        system_symbol = new_ord.security.sec_id

        symbol_overview_tuple = \
            self.strat_cache.get_symbol_overview_from_symbol(system_symbol)
        if symbol_overview_tuple:
            symbol_overview, _ = symbol_overview_tuple
            if not symbol_overview:
                logging.error(f"blocked generated chore, symbol_overview missing for: {new_ord}, "
                              f"strat_cache key: {self.strat_cache.get_key()}, limit up/down check needs "
                              f"symbol_overview, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
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
            bartering_brief = strat_brief.pair_sell_side_bartering_brief
            # Sell - not allowed less than limit dn px
            # limit down - TODO : Important : Upgrade this to support bartering at Limit Dn within the limit Dn limit
            if new_ord.px <= symbol_overview.limit_dn_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated SELL chore, limit down bartering not allowed on day-1, px "
                              f"expected higher than limit-dn px: {symbol_overview.limit_dn_px}, found {new_ord.px} for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief_log_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= ChoreControl.ORDER_CONTROL_LIMIT_DOWN_FAIL
        elif new_ord.side == Side.BUY:
            bartering_brief = strat_brief.pair_buy_side_bartering_brief
            # Buy - not allowed more than limit up px
            # limit up - TODO : Important : Upgrade this to support bartering at Limit Up within the limit Up limit
            if new_ord.px >= symbol_overview.limit_up_px:
                # @@@ below error log is used in specific test case for string matching - if changed here
                # needs to be changed in test also
                logging.error(f"blocked generated BUY chore, limit up bartering not allowed on day-1, px "
                              f"expected lower than limit-up px: {symbol_overview.limit_up_px}, found {new_ord.px} for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
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
                          f"{bartering_brief.consumable_open_chores} for strat_cache: "
                          f"{self.strat_cache.get_key()}, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

        # max_open_single_leg_notional check
        if chore_usd_notional > bartering_brief.consumable_open_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked chore with symbol_side_key: {get_new_chore_log_key(new_ord)}, "
                          f"breaches available consumable open notional, expected less than: "
                          f"{strat_brief.pair_sell_side_bartering_brief.consumable_open_notional}, chore needs:"
                          f" {chore_usd_notional}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

        # Checking max_single_leg_notional
        if chore_usd_notional > bartering_brief.consumable_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked generated {new_ord.side} chore, breaches available consumable notional, "
                          f"expected less than: {bartering_brief.consumable_notional}, "
                          f"chore needs: {chore_usd_notional} for strat_cache: {self.strat_cache.get_key()}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL

        # checking max concentration
        if not self.check_consumable_concentration(strat_brief, bartering_brief, new_ord.qty,
                                                   "SELL" if new_ord.side == Side.SELL else "BUY"):
            checks_passed |= ChoreControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

        # checking max participation
        barterd_notional: float = (
                self.strat_limit.max_single_leg_notional - strat_brief.pair_sell_side_bartering_brief.consumable_notional)
        projected_notional = barterd_notional + chore_usd_notional
        min_allowed_notional = self.strat_limit.market_barter_volume_participation.min_allowed_notional
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
                    self.strat_limit.market_barter_volume_participation.applicable_period_seconds,
                    self.strat_limit.market_barter_volume_participation.max_participation_rate,
                    StreetBook.asyncio_loop)
                if consumable_participation_qty is not None and consumable_participation_qty != 0:
                    key = get_strat_brief_log_key(strat_brief)
                    if consumable_participation_qty - new_ord.qty < 0:
                        checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL
                        consumable_participation_notional: float = consumable_participation_qty * new_ord.usd_px
                        # @@@ below error log is used in specific test case for string matching - if changed here
                        # needs to be changed in test also
                        warn_ = (f"blocked generated chore, not enough consumable_participation_qty available, "
                                 f"expected higher than chore qty: {new_ord.qty}, found {consumable_participation_qty}"
                                 f" / notional: {consumable_participation_notional} for chore key: "
                                 f"{get_new_chore_log_key(new_ord)};;;strat_cache key: {self.strat_cache.get_key()}, "
                                 f"strat_brief key: {key}")
                        if not pair_strat.pair_strat_params or not pair_strat.pair_strat_params.hedge_ratio:
                            hedge_ratio = 1
                        else:
                            hedge_ratio = pair_strat.pair_strat_params.hedge_ratio
                        if (consumable_participation_notional * hedge_ratio) > self.strat_limit.min_chore_notional:
                            err_dict["consumable_participation_qty"] = f"{consumable_participation_qty}"
                            logging.warning(f"hedge_ratio adjusted retryable {warn_}")
                        else:
                            logging.warning(f"hedge_ratio adjusted non-retryable {warn_}")
                    else:  # check passed - no action
                        logging.debug(f"{consumable_participation_qty=}; {new_ord=}")

                else:
                    strat_brief_key: str = get_strat_brief_log_key(strat_brief)
                    # @@@ below error log is used in specific test case for string matching - if changed here
                    # needs to be changed in test also
                    logging.error(f"Received unusable {consumable_participation_qty=} from "
                                  f"get_consumable_participation_qty_http, {system_symbol=}, side: "
                                  f"{new_ord.side}, applicable_period_seconds: "
                                  f"{self.strat_limit.market_barter_volume_participation.applicable_period_seconds}, "
                                  f"strat_brief_key: {strat_brief_key}, check failed")
                    checks_passed |= ChoreControl.ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL
            # else not required, pass the check, EQT is barterd on SWAP, thus absolute participation capped by CB
            # participation instead. SWAP brokers have their participation checks built on top based their entire flow
        # else not required, all good check is passed, allow the chore through

        # checking max_net_filled_notional
        if chore_usd_notional > strat_brief.consumable_nett_filled_notional:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            logging.error(f"blocked {new_ord.side} generated chore, not enough consumable_nett_filled_notional "
                          f"available, remaining {strat_brief.consumable_nett_filled_notional=}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            checks_passed |= ChoreControl.ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL

        return checks_passed

    def check_chore_limits(self, top_of_book: ExtendedTopOfBook, chore_limits: ChoreLimitsBaseModel,
                           pair_strat: PairStrat, new_ord: NewChoreBaseModel, chore_usd_notional: float,
                           check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS):
        sys_symbol = new_ord.security.sec_id
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        # TODO: min chore notional is to be a chore opportunity condition instead of chore check
        checks_passed_ = ChoreControl.check_min_chore_notional(pair_strat, self.strat_limit, new_ord,
                                                               chore_usd_notional)
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
            mobile_book_container = self.mobile_book_container_cache.leg_1_mobile_book_container
        else:
            mobile_book_container = self.mobile_book_container_cache.leg_2_mobile_book_container
        checks_passed_ = ChoreControl.check_px(top_of_book, self.sym_ovrw_getter, chore_limits, new_ord.px,
                                               new_ord.usd_px, new_ord.qty, new_ord.side,
                                               sys_symbol, mobile_book_container)
        if checks_passed_ != ChoreControl.ORDER_CONTROL_SUCCESS:
            checks_passed |= checks_passed_

        return checks_passed

    def check_new_chore(self, top_of_book: ExtendedTopOfBook, strat_brief: StratBriefBaseModel,
                        chore_limits: ChoreLimitsBaseModel, pair_strat: PairStrat, new_ord: NewChoreBaseModel,
                        err_dict: Dict[str, any], check_mask: int = ChoreControl.ORDER_CONTROL_SUCCESS) -> int:
        checks_passed: int = ChoreControl.ORDER_CONTROL_SUCCESS
        chore_usd_notional = new_ord.usd_px * new_ord.qty

        checks_passed |= self.check_chore_limits(top_of_book, chore_limits, pair_strat, new_ord, chore_usd_notional,
                                                 check_mask)
        if check_mask == ChoreControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip strat checks, they were conducted before, this is qty down adjusted chore

        checks_passed |= self.check_strat_limits(pair_strat, strat_brief, top_of_book, chore_limits, new_ord,
                                                 chore_usd_notional, err_dict)

        # TODO LAZY Read config "chore_pace_seconds" to pace chores (needed for testing - not a limit)
        if self.chore_pase_seconds > 0:
            # allow chores only after chore_pase_seconds
            if self.last_chore_timestamp.add(seconds=self.chore_pase_seconds) < DateTime.now():
                checks_passed |= ChoreControl.ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL

        return checks_passed

    @staticmethod
    def create_n_run_md_shell_script(pair_strat, generation_start_file_path, generation_stop_file_path):
        subscription_data = \
            [
                (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg1.sec.sec_id_source)),
                (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg2.sec.sec_id_source))
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = "SS" if pair_strat.pair_strat_params.strat_leg1.exch_id == "SSE" else "SZ"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_strat.host,
                           port=pair_strat.port, db_name=db_name, exch_code=exch_code,
                           project_name="street_book"))

        create_stop_md_script(str(generation_start_file_path), str(generation_stop_file_path))
        os.chmod(generation_stop_file_path, stat.S_IRWXU)

        if os.path.exists(generation_start_file_path):
            # first stopping script if already exists
            process = subprocess.Popen([f"{generation_stop_file_path}"])
            # wait for scripts to complete execution and delete existing stop and start scripts
            process.wait()

        create_md_shell_script(md_shell_env_data, str(generation_start_file_path), mode="MD",
                               instance_id=str(pair_strat.id))
        os.chmod(generation_start_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{generation_start_file_path}"])

    def _mark_strat_state_as_error(self, pair_strat: PairStratBaseModel):
        alert_str: str = \
            (f"Marking strat_state to ERROR for strat: {self.pair_street_book_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat=}")
        logging.info(alert_str)
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=pair_strat.id, strat_state=StratState.StratState_ERROR.value)

    def _mark_strat_state_as_pause(self, pair_strat: PairStratBaseModel):
        alert_str: str = \
            (f"graceful pause processing for strat: {self.pair_street_book_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; {pair_strat=}")
        logging.info(alert_str)
        guaranteed_call_pair_strat_client(
            PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
            _id=pair_strat.id, strat_state=StratState.StratState_PAUSED.value)

    def _set_strat_pause_when_portfolio_limit_check_fails(self):
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is not None:
            pair_strat, _ = pair_strat_tuple
            logging.critical("Putting Activated Strat to PAUSE, found portfolio_limits breached already, "
                             f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;; {pair_strat=}")
            guaranteed_call_pair_strat_client(
                PairStratBaseModel, email_book_service_http_client.patch_pair_strat_client,
                _id=pair_strat.id, strat_state=StratState.StratState_PAUSED.value)
        else:
            logging.error(f"Can't find pair_strat in strat_cache, found portfolio_limits "
                          f"breached but couldn't update strat_status: {str(self.strat_cache)=}")

    def check_n_pause_strat_before_run_if_portfolio_limit_breached(self):
        # Checking if portfolio_limits are still not breached
        is_portfolio_limits_breached_model_list: List[IsPortfolioLimitsBreached] = (
            post_book_service_http_client.is_portfolio_limits_breached_query_client())

        if len(is_portfolio_limits_breached_model_list) == 1:
            is_portfolio_limits_breached: bool = (
                is_portfolio_limits_breached_model_list[0].is_portfolio_limits_breached)
            if is_portfolio_limits_breached:
                self._set_strat_pause_when_portfolio_limit_check_fails()
            # else not required: if portfolio_limits are fine then ignore
        elif len(is_portfolio_limits_breached_model_list) == 0:
            logging.critical("PairStrat service seems down, can't check portfolio_limits before current strat "
                             "activation - putting strat to pause")
            self._set_strat_pause_when_portfolio_limit_check_fails()
        else:
            err_str_ = ("is_portfolio_limits_breached_query_client must return list of exact one "
                        f"IsPortfolioLimitsBreached model, but found "
                        f"{len(is_portfolio_limits_breached_model_list)=}, "
                        f"{is_portfolio_limits_breached_model_list=}")
            logging.error(err_str_)

    def run(self):
        ret_val: int = -5000
        # Getting pre-requisites ready before strat active runs
        run_coro = StreetBook.underlying_handle_strat_activate_query_http()
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e_:
            logging.exception(f"underlying_handle_strat_activate_query_http failed for pair_strat_id: "
                              f"{self.pair_street_book_id}; Exiting executor run();;;exception: {e_}")
            return -5001

        max_retry_count: Final[int] = 12
        retry_count: int = 0
        pair_strat_tuple: Tuple[PairStratBaseModel, DateTime] | None = None
        pair_strat: PairStratBaseModel | None = None
        lot_notional_ready: bool = False
        log_key: str | None = None
        while pair_strat_tuple is None or pair_strat is None:
            # getting pair_strat
            pair_strat_tuple = self.strat_cache.get_pair_strat()
            if pair_strat_tuple is None:
                logging.error("Can't find pair_strat_tuple even while entered executor's run method, likely bug "
                              "in loading strat_cache with pair_strat")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3000

            pair_strat, _ = pair_strat_tuple
            if pair_strat is None:
                logging.error("Can't find pair_strat from pair_strat_tuple even while entered "
                              "executor's run method, likely bug in loading strat_cache with pair_strat")
                if retry_count < max_retry_count:
                    retry_count += 1
                    continue
                else:
                    return -3001
            else:
                log_key = get_pair_strat_log_key(pair_strat)

        # setting index for leg1 and leg2 symbols
        self.leg_1_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
        self.leg_1_side = pair_strat.pair_strat_params.strat_leg1.side
        self.leg_2_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        self.leg_2_side = pair_strat.pair_strat_params.strat_leg2.side

        scripts_dir = PurePath(__file__).parent.parent / "scripts"
        # start file generator
        start_sh_file_path = scripts_dir / f"start_ps_id_{pair_strat.id}_md.sh"
        stop_sh_file_path = scripts_dir / f"stop_ps_id_{pair_strat.id}_md.sh"

        try:
            StreetBook.create_n_run_md_shell_script(pair_strat, start_sh_file_path, stop_sh_file_path)
            if not self.start_pos_cache():
                return -6000
            self.check_n_pause_strat_before_run_if_portfolio_limit_breached()

            while 1:
                try:
                    ret_val = self.internal_run()
                except Exception as e:
                    logging.exception(f"internal_run returned with exception; sending again for pair_strat_id: "
                                      f"{self.pair_street_book_id}, pair_strat_key: {log_key};;;exception: {e}")
                finally:
                    if ret_val == 1:
                        logging.info(f"explicit strat shutdown requested for pair_strat_id: "
                                     f"{self.pair_street_book_id}, going down, pair_strat_key: {log_key}")
                        self.strat_cache.set_pair_strat(None)
                        break
                    elif ret_val != 0:
                        logging.error(f"Error: internal_run returned, code: {ret_val}; sending again for "
                                      f"pair_strat_id: {self.pair_street_book_id}, pair_strat_key: {log_key}")
                    else:
                        pair_strat, _ = self.strat_cache.get_pair_strat()
                        if pair_strat.strat_state != StratState.StratState_DONE:
                            # don't stop the strat with Done, just pause [later resume if inventory becomes available]
                            self._mark_strat_state_as_pause(pair_strat)
                            logging.debug(f"StratStatus with pair_strat_id: {self.pair_street_book_id} marked Paused"
                                          f", pair_strat_key: {log_key}")
                            ret_val = 0
                        else:
                            logging.error(f"unexpected, pair_strat_id: {self.pair_street_book_id} was already marked"
                                          f" Done, pair_strat_key: {log_key}")
                            ret_val = -4000  # helps find the error location
                        break
        except Exception as e:
            logging.exception(f"exception occurred in run method of pair_strat_id: {self.pair_street_book_id}, "
                              f"pair_strat_key: {log_key};;;exception: {e}")
            ret_val = -4001
        finally:
            # running, stop md script
            logging.info(f"Executor: {self.pair_street_book_id} running, stop md script")
            process = subprocess.Popen([f"{stop_sh_file_path}"])
            process.wait()

            if ret_val != 0 and ret_val != 1:
                self._mark_strat_state_as_error(pair_strat)
                logging.critical(f"Executor: {self.pair_street_book_id} thread is going down due to unrecoverable "
                                 f"error - get tech to manually restart/recycle executor;;;{pair_strat=}")

            # removing created scripts
            try:
                if os.path.exists(start_sh_file_path):
                    os.remove(start_sh_file_path)
                if os.path.exists(stop_sh_file_path):
                    os.remove(stop_sh_file_path)
            except Exception as e:
                err_str_ = (f"exception occurred for pair_strat_key: {log_key} while deleting md scripts;;;"
                            f"exception: {e}")
                logging.exception(err_str_)
        logging.info(f"Executor returning from run")
        return ret_val

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.leg1_fx

    @perf_benchmark_sync_callable
    def _check_tob_n_place_non_systematic_chore(self, new_chore: NewChoreBaseModel, pair_strat: PairStrat,
                                                strat_brief: StratBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                                top_of_books: List[ExtendedTopOfBook]) -> int:
        leg1_tob: ExtendedTopOfBook | None
        leg2_tob: ExtendedTopOfBook | None
        barter_tob: ExtendedTopOfBook | None = None
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        if leg1_tob is not None:
            if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == new_chore.security.sec_id:
            # if self.strat_cache.leg1_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg1_tob

        if barter_tob is None and leg2_tob is not None:
            if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == new_chore.security.sec_id:
            # if self.strat_cache.leg2_bartering_symbol == new_chore.security.sec_id:
                barter_tob = leg2_tob

        if barter_tob is None:
            err_str_ = f"unable to send new_chore: no matching leg in this strat: {new_chore} " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;;" \
                       f"{self.strat_cache=}, {pair_strat=}"
            logging.error(err_str_)
            return False
        else:
            usd_px = self.get_usd_px(new_chore.px, new_chore.security.sec_id)
            ord_sym_ovrw = self.strat_cache.get_symbol_overview_from_symbol_obj(new_chore.security.sec_id)
            chore_placed: int = self.place_new_chore(barter_tob, ord_sym_ovrw, strat_brief, chore_limits, pair_strat,
                                                     new_chore)
            return chore_placed

    @staticmethod
    def get_leg1_leg2_ratio(leg1_px: float, leg2_px: float) -> float:
        if math.isclose(leg2_px, 0):
            return 0
        return leg1_px / leg2_px

    def _get_bid_tob_px_qty(self, tob: ExtendedTopOfBook) -> Tuple[float | None, int | None]:
        with MobileBookMutexManager(tob):
            if tob.bid_quote is not None:
                has_valid_px_qty = True
                if not tob.bid_quote.qty:
                    logging.error(f"Invalid {tob.bid_quote.qty = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                elif math.isclose(tob.bid_quote.px, 0):
                    logging.error(f"Invalid {tob.bid_quote.px = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                if has_valid_px_qty:
                    return tob.bid_quote.px, tob.bid_quote.qty
            else:
                logging.error(f"Can't find bid_quote in top of book, {tob.symbol = };;; {tob = }")
        return None, None

    def _get_ask_tob_px_qty(self, tob: ExtendedTopOfBook) -> Tuple[float | None, int | None]:
        with MobileBookMutexManager(tob):
            if tob.ask_quote is not None:
                has_valid_px_qty = True
                if not tob.ask_quote.qty:
                    logging.error(f"Invalid {tob.ask_quote.qty = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                elif math.isclose(tob.ask_quote.px, 0):
                    logging.error(f"Invalid {tob.ask_quote.px = } found in tob of {tob.symbol = };;; {tob = }")
                    has_valid_px_qty = False
                if has_valid_px_qty:
                    return tob.ask_quote.px, tob.ask_quote.qty
            else:
                logging.error(f"Can't find ask_quote in top of book, {tob.symbol = };;; {tob = }")
        return None, None

    @staticmethod
    def get_cb_lot_size_from_cb_symbol_overview_(
            cb_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None) -> int | None:
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
            cb_symbol_overview: SymbolOverviewBaseModel | SymbolOverview) -> int | None:
        if cb_symbol_overview:
            return cls.get_cb_lot_size_from_cb_symbol_overview_(cb_symbol_overview)
        else:
            return None

    def _place_chore(self, pair_strat: PairStratBaseModel, strat_brief: StratBriefBaseModel,
                     chore_limits: ChoreLimitsBaseModel, quote: QuoteBaseModel, tob: ExtendedTopOfBook, leg_sym_ovrw) -> float:
        """returns float posted notional of the chore sent"""
        # fail-safe
        pair_strat = self.strat_cache.get_pair_strat_obj()
        if pair_strat is not None:
            # If pair_strat not active, don't act, just return [check MD state and take action if required]
            if pair_strat.strat_state != StratState.StratState_ACTIVE or self.market.is_not_uat_nor_bartering_time():  # UAT barters outside bartering hours
                logging.error("Blocked place chore - strat not in activ state")
                return 0  # no chore sent = no posted notional
        if not (quote.qty == 0 or math.isclose(quote.px, 0)):
            ask_usd_px: float = self.get_usd_px(quote.px, tob.symbol)
            security = SecurityBaseModel(sec_id=tob.symbol)
            new_ord = NewChoreBaseModel(security=security, side=Side.BUY, px=quote.px, usd_px=ask_usd_px, qty=quote.qty)
            chore_placed = self.place_new_chore(tob, leg_sym_ovrw, strat_brief, chore_limits, pair_strat, new_ord)
            if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
                posted_notional = quote.px * quote.qty
                return posted_notional
            else:
                logging.error(f"0 value found in ask TOB - ignoring {quote.px=}, {quote.qty=}, pair_strat_key: "
                              f"{get_pair_strat_log_key(pair_strat)}")
            return 0  # no chore sent = no posted notional

    @perf_benchmark_sync_callable
    def _check_tob_and_place_chore(self, pair_strat: PairStratBaseModel | PairStrat, strat_brief: StratBriefBaseModel,
                                   chore_limits: ChoreLimitsBaseModel, top_of_books: List[ExtendedTopOfBook]) -> int:
        posted_leg1_notional: float = 0
        posted_leg2_notional: float = 0
        leg1_tob: ExtendedTopOfBook | None
        leg2_tob: ExtendedTopOfBook | None
        barter_tob: ExtendedTopOfBook
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)
        leg1_sym_ovrw = self.strat_cache.symbol_overviews[0]
        leg2_sym_ovrw = self.strat_cache.symbol_overviews[1]

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
        if leg1_tob is not None and self.strat_cache.leg1_bartering_symbol is not None:
            if abs(self.leg1_notional) <= abs(self.leg2_notional):
                # process primary leg
                if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:  # execute aggressive buy
                    posted_leg1_notional = self._place_chore(pair_strat, strat_brief, chore_limits, leg1_tob.ask_quote,
                                                             leg1_tob, leg1_sym_ovrw)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg1_notional = self._place_chore(pair_strat, strat_brief, chore_limits, leg1_tob.bid_quote,
                                                             leg1_tob, leg1_sym_ovrw)
                    if math.isclose(posted_leg1_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if leg2_tob is not None and self.strat_cache.leg2_bartering_symbol is not None:
            if abs(self.leg2_notional) <= abs(self.leg1_notional):
                # process secondary leg
                if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:  # execute aggressive buy
                    posted_leg2_notional = self._place_chore(pair_strat, strat_brief, chore_limits, leg2_tob.ask_quote,
                                                             leg2_tob, leg2_sym_ovrw)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg2_notional = self._place_chore(pair_strat, strat_brief, chore_limits, leg2_tob.bid_quote,
                                                             leg2_tob, leg2_sym_ovrw)
                    if math.isclose(posted_leg2_notional, 0):
                        return ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if chore_placed == ChoreControl.ORDER_CONTROL_SUCCESS:
            self.last_chore_timestamp = DateTime.now()
            self.leg1_notional += posted_leg1_notional
            self.leg2_notional += posted_leg2_notional
            logging.debug(f"strat-matched ToB for pair_strat_key {get_pair_strat_log_key(pair_strat)}: "
                          f"{[str(tob) for tob in top_of_books]}")
        return chore_placed

    def _both_side_tob_has_data(self, leg_1_tob: ExtendedTopOfBook, leg_2_tob: ExtendedTopOfBook) -> bool:
        if leg_1_tob is not None and leg_2_tob is not None:
            with (MobileBookMutexManager(leg_1_tob, leg_2_tob)):
                if leg_1_tob.last_update_date_time is not None and leg_2_tob.last_update_date_time is not None:
                    return True
        return False

    def _get_tob_symbol(self, tob: ExtendedTopOfBook) -> str:
        with MobileBookMutexManager(tob):
            return tob.symbol

    def _get_tob_last_update_date_time(self, tob: ExtendedTopOfBook) -> DateTime:
        with MobileBookMutexManager(tob):
            return tob.last_update_date_time

    def _get_tob_bid_quote_px(self, tob: ExtendedTopOfBook) -> float | None:
        with MobileBookMutexManager(tob):
            if tob.bid_quote is not None:
                return tob.bid_quote.px
            else:
                logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_ask_quote_px(self, tob: ExtendedTopOfBook) -> float | None:
        with MobileBookMutexManager(tob):
            if tob.ask_quote is not None:
                return tob.ask_quote.px
            else:
                logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_bid_quote_last_update_date_time(self, tob: ExtendedTopOfBook) -> DateTime | None:
        with MobileBookMutexManager(tob):
            if tob.bid_quote is not None:
                return tob.bid_quote.last_update_date_time
            else:
                logging.info(f"Can't find bid_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    def _get_tob_ask_quote_last_update_date_time(self, tob: ExtendedTopOfBook) -> DateTime | None:
        with MobileBookMutexManager(tob):
            if tob.ask_quote is not None:
                return tob.ask_quote.last_update_date_time
            else:
                logging.info(f"Can't find ask_quote in tob of symbol: {tob.symbol};;; tob: {tob}")
                return None

    @perf_benchmark_sync_callable
    def _check_tob_and_place_chore_test(self, pair_strat: PairStratBaseModel | PairStrat,
                                        strat_brief: StratBriefBaseModel, chore_limits: ChoreLimitsBaseModel,
                                        top_of_books: List[ExtendedTopOfBook]) -> int:
        buy_top_of_book: ExtendedTopOfBook | None = None
        sell_top_of_book: ExtendedTopOfBook | None = None
        is_cb_buy: bool = True

        if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
            buy_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
            sell_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
        else:
            is_cb_buy = False
            buy_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
            sell_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id

        buy_sym_ovrw: SymbolOverviewBaseModel | SymbolOverview | None = (
            self.strat_cache.get_symbol_overview_from_symbol_obj(buy_symbol))
        sell_sym_ovrw: SymbolOverviewBaseModel | SymbolOverview | None = (
            self.strat_cache.get_symbol_overview_from_symbol_obj(sell_symbol))

        chore_placed: int = ChoreControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        leg_1_top_of_book: ExtendedTopOfBook = (
            self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book(
                self._top_of_books_update_date_time))
        leg_2_top_of_book = (
            self.mobile_book_container_cache.leg_2_mobile_book_container.get_top_of_book(
                self._top_of_books_update_date_time))

        if self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
            top_of_books = [leg_1_top_of_book, leg_2_top_of_book]
            self.update_aggressive_market_depths_in_cache()
            latest_update_date_time: DateTime | None = None
            for top_of_book in top_of_books:
                if latest_update_date_time is None:
                    tob_symbol = self._get_tob_symbol(top_of_book)
                    if tob_symbol == buy_symbol:
                        buy_top_of_book = top_of_book
                        sell_top_of_book = None
                    elif tob_symbol == sell_symbol:
                        sell_top_of_book = top_of_book
                        buy_top_of_book = None
                    else:
                        err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                   f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                        logging.error(err_str_)
                        raise Exception(err_str_)
                    latest_update_date_time = self._get_tob_last_update_date_time(top_of_book)
                else:
                    latest_update_date_time_ = self._get_tob_last_update_date_time(top_of_book)
                    if latest_update_date_time_ > latest_update_date_time:
                        tob_symbol = self._get_tob_symbol(top_of_book)
                        if tob_symbol == buy_symbol:
                            buy_top_of_book = top_of_book
                            sell_top_of_book = None
                        elif tob_symbol == sell_symbol:
                            sell_top_of_book = top_of_book
                            buy_top_of_book = None
                        else:
                            err_str_ = f"top_of_book with unsupported test symbol received, {top_of_book = }, " \
                                       f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
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
                        chore_placed = self.place_new_chore(buy_top_of_book, buy_sym_ovrw, strat_brief, chore_limits,
                                                            pair_strat, new_ord)
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
                        chore_placed = self.place_new_chore(sell_top_of_book, sell_sym_ovrw, strat_brief, chore_limits,
                                                            pair_strat, new_ord)
            else:
                err_str_ = "TOB updates could not find any updated buy or sell tob, " \
                           f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                logging.debug(err_str_)
            return chore_placed
        return False

    def get_leg1_fx(self):
        if self.leg1_fx:
            return self.leg1_fx
        else:
            if not self.strat_cache.leg1_fx_symbol_overview:
                self.strat_cache.leg1_fx_symbol_overview = \
                    StratCache.fx_symbol_overview_dict[self.strat_cache.leg1_fx_symbol]
            if self.strat_cache.leg1_fx_symbol_overview and self.strat_cache.leg1_fx_symbol_overview.closing_px and \
                    (not math.isclose(self.strat_cache.leg1_fx_symbol_overview.closing_px, 0)):
                self.leg1_fx = self.strat_cache.leg1_fx_symbol_overview.closing_px
                return self.leg1_fx
            else:
                logging.error(f"unable to find fx_symbol_overview for "
                              f"{self.strat_cache.leg1_fx_symbol = };;; {self.strat_cache = }")
                return None

    def process_cxl_request(self, force_cxl_only: bool = False):
        cancel_chores_and_date_tuple = self.strat_cache.get_cancel_chore(self._cancel_chores_update_date_time)
        if cancel_chores_and_date_tuple is not None:
            cancel_chores, self._cancel_chores_update_date_time = cancel_chores_and_date_tuple
            if cancel_chores is not None:
                final_slice = len(cancel_chores)
                unprocessed_cancel_chores: List[CancelChoreBaseModel] = \
                    cancel_chores[self._cancel_chores_processed_slice:final_slice]
                self._cancel_chores_processed_slice = final_slice
                cancel_chore: CancelChoreBaseModel
                for cancel_chore in unprocessed_cancel_chores:
                    if not cancel_chore.cxl_confirmed:
                        res: bool = True
                        if (not force_cxl_only) or cancel_chore.force_cancel:
                            res = self.bartering_link_place_cxl_chore(cancel_chore.chore_id, cancel_chore.side,
                                                                    bartering_sec_id=None,
                                                                    system_sec_id=cancel_chore.security.sec_id,
                                                                    underlying_account="NA")
                        else:
                            logging.warning(f"{force_cxl_only=} and {cancel_chore.force_cancel=} leaving unprocessed "
                                            f"{cancel_chore=}")
                        if not res:
                            # check in DB if this chore needs cancellation, otherwise set cancel_chore.cxl_confirmed to
                            # true and stop processing it
                            pass

                # if some update was on existing cancel_chores then this semaphore release was for that update only,
                # therefore returning True to continue and wait for next semaphore release
                return True
        # all else return false - no cancel_chore to process
        return False

    def bartering_link_place_cxl_chore(self, chore_id, side, bartering_sec_id, system_sec_id, underlying_account) -> bool:
        # coro needs public method
        run_coro = self.bartering_link.place_cxl_chore(chore_id, side, bartering_sec_id, system_sec_id, underlying_account)
        future = asyncio.run_coroutine_threadsafe(run_coro, StreetBook.asyncio_loop)

        # block for start_executor_server task to finish
        try:
            # ignore return chore_journal: don't generate cxl chores in system, just treat cancel acks as unsol cxls
            res: bool = future.result()
            if not res:
                logging.error(f"bartering_link_place_cxl_chore failed, {res=} returned")
                return False
            else:
                return True
        except Exception as e:
            key = get_symbol_side_key([(system_sec_id, side)])
            logging.exception(f"bartering_link_place_cxl_chore failed for: {key} with exception: {e}")

    def is_consumable_notional_tradable(self, strat_brief: StratBriefBaseModel, ol: ChoreLimitsBaseModel):
        if (not self.buy_leg_single_lot_usd_notional) or (not self.sell_leg_single_lot_usd_notional):
            err: str = (f"unexpected {self.buy_leg_single_lot_usd_notional=} or "
                        f"{self.sell_leg_single_lot_usd_notional=}; is_consumable_notional_tradable will return false "
                        f"for {get_strat_brief_log_key(strat_brief)}")
            logging.error(err)
            return False
        min_tradable_notional = int(max(self.buy_leg_single_lot_usd_notional, self.sell_leg_single_lot_usd_notional))
        if strat_brief.pair_sell_side_bartering_brief.consumable_notional <= min_tradable_notional:
            # sell leg of strat is done - if either leg is done - strat is done
            logging.warning(f"sell-remaining-notional="
                            f"{int(strat_brief.pair_sell_side_bartering_brief.consumable_notional)} is <= "
                            f"{min_tradable_notional=}, no further chores possible; for "
                            f"{strat_brief.pair_sell_side_bartering_brief.security.sec_id}, "
                            f"{strat_brief.pair_sell_side_bartering_brief.side};;;{get_strat_brief_log_key(strat_brief)}")
            return True
        # else not required, more notional to consume on sell leg - strat done is set to 1 (no error, not done)
        if strat_brief.pair_buy_side_bartering_brief.consumable_notional <= min_tradable_notional:
            # buy leg of strat is done - if either leg is done - strat is done
            logging.warning(f"buy-remaining-notional="
                            f"{int(strat_brief.pair_buy_side_bartering_brief.consumable_notional)} is <= "
                            f"{min_tradable_notional=}, no further chores possible; for "
                            f"{strat_brief.pair_buy_side_bartering_brief.security.sec_id}, "
                            f"{strat_brief.pair_buy_side_bartering_brief.side};;;{get_strat_brief_log_key(strat_brief)}")
            return True
        return False

    def is_pair_strat_done(self, strat_brief: StratBriefBaseModel, ol: ChoreLimitsBaseModel) -> int:
        """
        Args:
            strat_brief:
            ol: current chore limits as set by system / user
        Returns:
            0: indicates done; no notional to consume on at-least 1 leg & no-open chores for this strat in market
            -1: indicates needs-processing; strat has notional left to consume on both legs or has unack leg
            +number: TODO: indicates finishing; no notional to consume on at-least 1 leg but open chores found for strat
        """
        strat_done: bool = False
        if self.strat_cache.has_unack_leg():  # chore snapshot of immediate prior sent new-chore may not have arrived
            return -1
        open_chore_count: int = self.strat_cache.get_open_chore_count_from_cache()
        if 0 == open_chore_count:
            strat_done = self.is_consumable_notional_tradable(strat_brief, ol)
        # else not required, if strat has open chores, it's not done yet
        if strat_done:
            logging.warning(f"Strat is_consumable_notional_tradable returned done, strat will be closed / marked done "
                            f"for {get_strat_brief_log_key(strat_brief)}")
            time.sleep(5)  # allow for any pending post cancel ack race fills to arrive
            return 0
        else:
            return -1  # in progress

    def _get_latest_system_control(self) -> SystemControlBaseModel | None:
        system_control: SystemControlBaseModel | None = None
        system_control_tuple = self.bartering_data_manager.bartering_cache.get_system_control()
        if system_control_tuple is None:
            logging.warning("no kill_switch found yet - strat will not trigger until kill_switch arrives")
            return None
        else:
            system_control, self._system_control_update_date_time = system_control_tuple
        return system_control

    def is_strat_ready_for_next_opportunity(self, log_error: bool = False) -> bool:
        open_chore_count: int = self.strat_cache.get_open_chore_count_from_cache()
        has_unack_leg = self.strat_cache.has_unack_leg()
        if has_unack_leg:
            if log_error:  # [chore impact not applied yet]
                logging.debug(f"blocked opportunity search, has unack leg and {open_chore_count} open chore(s)")
            return False
        if not self.strat_limit.max_open_chores_per_side:
            logging.debug(f"blocked opportunity search, {self.strat_limit.max_open_chores_per_side=} not set")
            return False
        else:
            if self.strat_limit.max_open_chores_per_side < open_chore_count:
                if log_error:
                    logging.debug(f"blocked opportunity search, has {open_chore_count} open chore(s), allowed: "
                                  f"{self.strat_limit.max_open_chores_per_side=}")
                return False
        if not self.allow_multiple_unfilled_chore_pairs_per_strat:
            if self.strat_cache.check_has_open_chore_with_no_fill_from_cache():
                if log_error:
                    logging.debug(f"blocked opportunity search, has open chore with no fill yet")
                return False
            # no else needed - no unfilled chores - default return true is good

        return True

    def _get_latest_pair_strat(self) -> PairStrat | None:
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is not None:
            pair_strat, _ = pair_strat_tuple
            if pair_strat:
                return pair_strat
            else:
                logging.error(f"pair_strat in pair_strat_tuple is None for: {self.strat_cache = }")
        else:
            logging.error(f"pair_strat_tuple is None for: {self.strat_cache = }")
        return None

    def _get_single_lot_usd_notional_for_symbol_overview(self,
                                                         symbol_overview: SymbolOverviewBaseModel | SymbolOverview):
        if self.strat_cache.static_data.is_cb_ticker(symbol_overview.symbol):
            lot_size = self.get_cb_lot_size_from_cb_symbol_overview(symbol_overview)
        else:
            lot_size = symbol_overview.lot_size
        return lot_size * symbol_overview.closing_px / self.leg1_fx

    def _init_lot_notional(self, pair_strat: PairStratBaseModel | PairStrat) -> bool:
        if self.buy_leg_single_lot_usd_notional and self.sell_leg_single_lot_usd_notional:
            return True  # happy path
        else:
            buy_leg: StratLegBaseModel | StratLeg | None = None
            sell_leg: StratLegBaseModel | StratLeg | None = None
            cb_side = Side.SIDE_UNSPECIFIED
            if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:
                cb_side = Side.BUY
                buy_leg = pair_strat.pair_strat_params.strat_leg1
                if pair_strat.pair_strat_params.strat_leg2.side == Side.SELL:
                    sell_leg = pair_strat.pair_strat_params.strat_leg2
                else:
                    logging.error(f"_init_lot_notional: pair strat has mismatching sell & buy legs, leg1 is "
                                  f"BUY & leg2 is not SELL: {pair_strat.pair_strat_params.strat_leg2.side};;;"
                                  f"{pair_strat=}")
            elif pair_strat.pair_strat_params.strat_leg1.side == Side.SELL:
                cb_side = Side.SELL
                sell_leg = pair_strat.pair_strat_params.strat_leg1
                if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:
                    buy_leg = pair_strat.pair_strat_params.strat_leg2
                else:
                    logging.error(f"_init_lot_notional: pair strat has mismatching sell & buy legs, leg1 is "
                                  f"SELL & leg2 is not BUY: {pair_strat.pair_strat_params.strat_leg2.side};;;"
                                  f"{pair_strat=}")
            else:
                logging.error(f"_init_lot_notional: unexpected side found in leg1 of pair_strat: "
                              f"{pair_strat.pair_strat_params.strat_leg1.side};;;{pair_strat=}")
            if buy_leg and sell_leg:
                buy_symbol_overview_tuple: Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None
                buy_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None
                if buy_symbol_overview_tuple := self.strat_cache.get_symbol_overview_from_symbol(buy_leg.sec.sec_id):
                    buy_symbol_overview, _ = buy_symbol_overview_tuple
                    if buy_symbol_overview.lot_size and buy_symbol_overview.closing_px:
                        self.buy_leg_single_lot_usd_notional = (
                            self._get_single_lot_usd_notional_for_symbol_overview(buy_symbol_overview))

                sell_symbol_overview_tuple: Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None
                sell_symbol_overview: SymbolOverviewBaseModel | SymbolOverview | None
                if sell_symbol_overview_tuple := self.strat_cache.get_symbol_overview_from_symbol(sell_leg.sec.sec_id):
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
        pair_strat_id = None
        while 1:
            self.strat_limit = None
            try:
                logging.debug("street_book going to acquire semaphore")
                # self.strat_cache.notify_semaphore.acquire()
                acquire_notify_semaphore()
                # remove all unprocessed signals from semaphore, logic handles all new updates in single iteration
                # clear_semaphore(self.strat_cache.notify_semaphore)
                logging.debug("street_book signaled")

                # 0. Checking if strat_cache stopped (happens most likely when strat is not ongoing anymore)
                if self.strat_cache.stopped:
                    # indicates explicit shutdown requested from server, set_pair_strat(None) called at return point
                    logging.debug(f"street_book {self.strat_cache.stopped=} indicates explicit shutdown requested")
                    return 1

                # 1. check if portfolio status has updated since we last checked
                system_control: SystemControlBaseModel | None = self._get_latest_system_control()
                if system_control is None:
                    logging.debug(f"{system_control=} going for retry")
                    continue

                # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
                pair_strat: PairStrat = self._get_latest_pair_strat()
                if pair_strat is None:
                    return -1
                elif pair_strat_id is None:
                    pair_strat_id = pair_strat.id

                # primary bartering block
                # pair_strat not active: disallow proceeding
                # system not in UAT & not bartering time: disallow chore from proceeding [UAT barters outside hours]
                if pair_strat.strat_state != StratState.StratState_ACTIVE or self.market.is_not_uat_nor_bartering_time():
                    self.process_cxl_request(force_cxl_only=True)
                    continue
                else:
                    strat_limits_tuple = self.strat_cache.get_strat_limits()
                    self.strat_limit, strat_limits_update_date_time = strat_limits_tuple

                # 3. check if any cxl chore is requested and send out [continue new loop after]
                if self.process_cxl_request():
                    continue

                strat_brief: StratBriefBaseModel | None = None
                # strat doesn't need to check if strat_brief is updated or not
                # strat_brief_tuple = self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
                strat_brief_tuple = self.strat_cache.get_strat_brief()
                if strat_brief_tuple:
                    strat_brief, self._strat_brief_update_date_time = strat_brief_tuple
                    if strat_brief:
                        pass
                    else:
                        logging.error(f"can't proceed, strat_brief found None for strat-cache: "
                                      f"{self.strat_cache.get_key()};;; [{self.strat_cache=}]")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"can't proceed! strat_brief_tuple: {strat_brief_tuple} not found for strat-cache: "
                                  f"{self.strat_cache.get_key()};;; [{self.strat_cache=}]")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                chore_limits: ChoreLimitsBaseModel | None = None
                chore_limits_tuple = self.bartering_data_manager.bartering_cache.get_chore_limits()
                if chore_limits_tuple:
                    chore_limits, _ = chore_limits_tuple
                    if chore_limits and self.strat_limit:
                        strat_done_counter = self.is_pair_strat_done(strat_brief, chore_limits)
                        if 0 == strat_done_counter:
                            return 0  # triggers graceful shutdown
                        elif -1 != strat_done_counter:
                            # strat is finishing: waiting to close pending strat_done_counter number of open chores
                            continue
                        # else not needed - move forward, more processing needed to complete the strat
                    else:
                        logging.error(f"Can't proceed: chore_limits/strat_limit not found for bartering_cache: "
                                      f"{self.bartering_data_manager.bartering_cache}; {self.strat_cache=}")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"chore_limits_tuple not found for strat: {self.strat_cache}, can't proceed")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                # 4.1 check symbol overviews [if they don't exist - continue]
                symbol_overviews: List[SymbolOverviewBaseModel | SymbolOverview | None]
                symbol_overviews = self.strat_cache.symbol_overviews
                if symbol_overviews and len(symbol_overviews) == 2 and (symbol_overviews[0] is not None) and (
                        symbol_overviews[1] is not None):
                    pass
                else:
                    logging.warning(f"found: {len(symbol_overviews)=} expected 2 for {self};;;received-SOs: "
                                    f"{[str(so) for so in symbol_overviews]}!")
                    continue  # go next run - we don't stop processing - retry in next iteration

                # 4.2 get top_of_book (new or old to be checked by respective strat based on strat requirement)
                leg_1_top_of_book = (
                    self.mobile_book_container_cache.leg_1_mobile_book_container.get_top_of_book())
                leg_2_top_of_book = (
                    self.mobile_book_container_cache.leg_2_mobile_book_container.get_top_of_book())

                if not self._both_side_tob_has_data(leg_1_top_of_book, leg_2_top_of_book):
                    logging.warning(f"strats need both sides of TOB to be present, found  only leg_1 or only leg_2 "
                                    f"or neither of them;;;tob found: {leg_1_top_of_book=}, {leg_2_top_of_book=}")
                    continue  # go next run - we don't stop processing for one faulty tob update

                tobs = [leg_1_top_of_book, leg_2_top_of_book]

                # 5. ensure leg1_fx is present - otherwise don't proceed - retry later
                if not self.get_leg1_fx():
                    logging.error(f"USD fx rate not found for strat: {self.strat_cache.get_key()}, unable to proceed, "
                                  f"fx symbol: {self.strat_cache.leg1_fx_symbol}, we'll retry in next attempt")
                    continue

                # 5.1 init_lot_notionals
                else:
                    lot_notional_ready = self._init_lot_notional(pair_strat)  # error logged in call
                    if not lot_notional_ready:
                        logging.error(f"lot notional not ready for strat: {self.strat_cache.get_key()}, unable to "
                                      f"proceed, {self.buy_leg_single_lot_usd_notional=}, "
                                      f"{self.sell_leg_single_lot_usd_notional=}, we'll retry in next attempt")
                        continue

                # 6. If kill switch is enabled - don't act, just return
                if system_control.kill_switch:
                    logging.debug("not-progressing: kill switch enabled")
                    continue

                # 7. continue only if past-pair (iff triggered) has no open/unack chores
                if not self.is_strat_ready_for_next_opportunity(log_error=True):
                    continue

                # 8. If any manual new_chore requested: apply risk checks (maybe no strat param checks?) & send out
                new_chores_and_date_tuple = self.strat_cache.get_new_chore(self._new_chores_update_date_time)
                if new_chores_and_date_tuple is not None:
                    new_chores, self._new_chores_update_date_time = new_chores_and_date_tuple
                    if new_chores is not None:
                        self.update_aggressive_market_depths_in_cache()
                        final_slice = len(new_chores)
                        unprocessed_new_chores: List[NewChoreBaseModel] = (
                            new_chores[self._new_chores_processed_slice:final_slice])
                        self._new_chores_processed_slice = final_slice
                        for new_chore in unprocessed_new_chores:
                            if system_control and not system_control.kill_switch:
                                self._check_tob_n_place_non_systematic_chore(new_chore, pair_strat, strat_brief,
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
                    self._check_tob_and_place_chore_test(pair_strat, strat_brief, chore_limits, tobs)
                else:
                    self._check_tob_and_place_chore(pair_strat, strat_brief, chore_limits, tobs)
                continue  # all good - go next run
            except Exception as e:
                logging.exception(f"Run for {pair_strat_id=} returned with exception: {e}")
                return -1
        logging.info(f"exiting internal_run of {pair_strat_id=}, graceful shutdown this strat")
        return 0
