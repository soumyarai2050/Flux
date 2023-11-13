import datetime
import inspect
import logging
import os
import sys
import threading
from pathlib import PurePath
import time
from threading import Thread
import math
import traceback
from fastapi.encoders import jsonable_encoder
from typing import Callable
import subprocess
import stat

os.environ["DBType"] = "beanie"

from Flux.CodeGenProjects.strat_executor.app.order_check import OrderControl
from Flux.CodeGenProjects.strat_executor.app.trading_data_manager import TradingDataManager
from Flux.CodeGenProjects.strat_executor.app.strat_cache import *
from Flux.CodeGenProjects.strat_executor.app.trading_link import get_trading_link, TradingLinkBase, is_test_run, \
    config_dict
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import \
    get_consumable_participation_qty_http, get_symbol_side_key, \
    get_strat_brief_log_key, create_stop_md_script
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import *
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import (
    create_md_shell_script, MDShellEnvData)
from FluxPythonUtils.scripts.utility_functions import clear_semaphore


class StratExecutor:
    # Query Callables
    underlying_get_aggressive_market_depths_query_http: Callable[..., Any] | None = None
    underlying_get_market_depth_from_index_fields_http: Callable[..., Any] | None = None
    underlying_partial_update_strat_status_http: Callable[..., Any] | None = None
    underlying_update_residuals_query_http: Callable[..., Any] | None = None

    trading_link: ClassVar[TradingLinkBase] = get_trading_link()
    asyncio_loop: asyncio.AbstractEventLoop

    @classmethod
    def initialize_underlying_http_routes(cls):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_get_market_depth_from_index_fields_http, underlying_partial_update_strat_status_http,
            underlying_update_residuals_query_http, underlying_get_aggressive_market_depths_query_http)
        cls.underlying_get_aggressive_market_depths_query_http = underlying_get_aggressive_market_depths_query_http
        cls.underlying_get_market_depth_from_index_fields_http = underlying_get_market_depth_from_index_fields_http
        cls.underlying_partial_update_strat_status_http = underlying_partial_update_strat_status_http
        cls.underlying_update_residuals_query_http = underlying_update_residuals_query_http

    @staticmethod
    def executor_trigger(trading_data_manager_: TradingDataManager, strat_cache: StratCache):
        strat_executor: StratExecutor = StratExecutor(trading_data_manager_, strat_cache)
        strat_executor_thread = Thread(target=strat_executor.run, daemon=True).start()
        return strat_executor, strat_executor_thread

    """ 1 instance = 1 thread = 1 pair strat"""

    def __init__(self, trading_data_manager_: TradingDataManager, strat_cache: StratCache):
        # prevents consuming any market data older than current time
        self.is_dev_env = True

        self.leg1_consumed_depth_time: DateTime = DateTime.now()
        self.leg2_consumed_depth_time: DateTime = DateTime.now()
        self.leg1_consumed_depth: MarketDepth | None = None
        self.leg2_consumed_depth: MarketDepth | None = None

        self.pair_strat_executor_id: str | None = None
        self.is_test_run: bool = is_test_run
        self.is_sanity_test_run: bool = config_dict.get("is_sanity_test_run")

        self.trading_data_manager: TradingDataManager = trading_data_manager_
        self.strat_cache: StratCache = strat_cache
        self.leg1_fx: float | None = None

        self._portfolio_status_update_date_time: DateTime | None = None
        self._strat_brief_update_date_time: DateTime | None = None
        self._order_snapshots_update_date_time: DateTime | None = None
        self._order_journals_update_date_time: DateTime | None = None
        self._fills_journals_update_date_time: DateTime | None = None
        self._order_limits_update_date_time: DateTime | None = None
        self._new_orders_update_date_time: DateTime | None = None
        self._new_orders_processed_slice: int = 0
        self._cancel_orders_update_date_time: DateTime | None = None
        self._cancel_orders_processed_slice: int = 0
        self._top_of_books_update_date_time: DateTime | None = None
        self._tob_leg1_update_date_time: DateTime | None = None
        self._tob_leg2_update_date_time: DateTime | None = None
        self._processed_tob_date_time: DateTime | None = None

        self.strat_limit: StratLimits | None = None
        self.last_order_timestamp: DateTime | None = None

        self.leg1_notional: float = 0
        self.leg2_notional: float = 0

        self.order_pase_seconds = 0
        # internal rejects to use:  -ive internal_reject_count + current date time as order id
        self.internal_reject_count = 0
        # 1-time prepare param used by update_aggresive_market_depths_in_cache call for this strat [init on first use]
        self.aggresive_symbol_side_tuples_dict: Dict[str, List[Tuple[str, str]]] = {}
        StratExecutor.initialize_underlying_http_routes()  # Calling underlying instances init

    def check_order_eligibility(self, side: Side, check_notional: float) -> bool:
        strat_brief, self._strat_brief_update_date_time = \
            self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
        portfolio_status, self._portfolio_status_update_date_time = \
            self.trading_data_manager.trading_cache.get_portfolio_status(self._portfolio_status_update_date_time)
        if side == Side.BUY:
            if strat_brief.pair_buy_side_trading_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False
        else:
            if strat_brief.pair_sell_side_trading_brief.consumable_notional - check_notional > 0:
                return True
            else:
                return False

    def init_aggresive_symbol_side_tuples_dict(self) -> bool:
        if self.aggresive_symbol_side_tuples_dict:
            logging.warning("init_aggresive_symbol_side_tuples_dict invoked in pre-initialized "
                            "aggressive_symbol_side_tuples_dict")
            return True  # its pre-initialized, not ideal, but not wrong either

        # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
        pair_strat: PairStrat = self._get_latest_pair_strat()
        if pair_strat is None:
            logging.error("init_aggresive_symbol_side_tuples_dict invoked but no pair strat found in cache")
            return False

        leg1 = pair_strat.pair_strat_params.strat_leg1
        leg1_sec: str = leg1.sec.sec_id
        leg1_aggressive_side_str: str = "ASK" if leg1.side == Side.BUY else "BID"
        leg2 = pair_strat.pair_strat_params.strat_leg2
        leg2_sec: str = leg2.sec.sec_id
        leg2_aggressive_side_str: str = "ASK" if leg2.side == Side.BUY else "BID"

        self.aggresive_symbol_side_tuples_dict = {"symbol_side_tuples_list": [(leg1_sec, leg1_aggressive_side_str),
                                                                              (leg2_sec, leg2_aggressive_side_str)]}
        return True

    def update_aggressive_market_depths_in_cache(self) -> Tuple[List[MarketDepth], List[MarketDepth]]:
        if not self.aggresive_symbol_side_tuples_dict:
            if not self.init_aggresive_symbol_side_tuples_dict():
                return [], []   # error logged internally

        # coro needs public method
        run_coro = \
            StratExecutor.underlying_get_aggressive_market_depths_query_http(self.aggresive_symbol_side_tuples_dict)
        future = asyncio.run_coroutine_threadsafe(run_coro, StratExecutor.asyncio_loop)

        try:
            symbol_side_tuple_list: List = list(self.aggresive_symbol_side_tuples_dict.values())[0]
            sym1, sym1_aggressive_side = symbol_side_tuple_list[0]
            sym2, sym2_aggressive_side = symbol_side_tuple_list[1]
            sym1_filtered_market_depths: List[MarketDepth] = []  # sym1 may not be same as strat leg1
            sym2_filtered_market_depths: List[MarketDepth] = []  # sym2 may not be same as strat leg1
            sym1_newest_exch_time = None
            sym2_newest_exch_time = None
            md: MarketDepth

            # now block for task to finish
            market_depths = future.result()
            # store for subsequent reference
            if market_depths:
                for md in market_depths:
                    if md.qty != 0 and md.px and (not math.isclose(md.px, 0)):
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
                            if md.exch_time > sym2_newest_exch_time:
                                sym2_newest_exch_time = md.exch_time

                        else:
                            logging.error(f"update_aggressive_market_depths_in_cache, expected: {sym1} or {sym2} found "
                                          f"for symbol: {md.symbol}, ignoring depth;;; {md}")
                    else:
                        logging.error(f"update_aggressive_market_depths_in_cache, invalid px or qty: {md.px}, {md.qty} "
                                      f"found for symbol: {md.symbol}, ignoring depth;;; {md}")

                # sort by px - most aggresive to passive (reverse sorts big to small)
                sym1_filtered_market_depths.sort(reverse=(sym1_aggressive_side == "ASK"), key=lambda x: x.px)
                sym2_filtered_market_depths.sort(reverse=(sym2_aggressive_side == "ASK"), key=lambda x: x.px)

            if not sym1_filtered_market_depths:
                sym1_side = Side.BUY if sym1_aggressive_side == "ASK" else Side.SELL
                logging.error(f"update_aggressive_market_depths_in_cache, no market_depth object found symbol_side_key:"
                              f" {get_symbol_side_key([(sym1, sym1_side)])}")
            if not sym2_filtered_market_depths:
                sym2_side = Side.BUY if sym2_aggressive_side == "ASK" else Side.SELL
                logging.error(f"update_aggressive_market_depths_in_cache, no market_depth object found symbol_side_key:"
                              f" {get_symbol_side_key([(sym2, sym2_side)])}")
            self.strat_cache.set_sorted_market_depths(sym1, sym1_aggressive_side, sym1_newest_exch_time,
                                                      sym1_filtered_market_depths)
            self.strat_cache.set_sorted_market_depths(sym2, sym2_aggressive_side, sym2_newest_exch_time,
                                                      sym2_filtered_market_depths)
            return sym1_filtered_market_depths, sym2_filtered_market_depths
        except Exception as e:
            logging.exception(f"update_aggressive_market_depths_in_cache failed with exception: {e}")

    def extract_strat_specific_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[TopOfBook | None,
                                                                                       TopOfBook | None]:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        leg1_tob, leg2_tob = self.extract_legs_from_tobs(pair_strat, top_of_books)
        if leg1_tob is not None and self.strat_cache.leg1_trading_symbol is None:
            logging.debug(f"ignoring ticker: {leg1_tob.symbol} not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg1_tob = None
        if leg2_tob is not None and self.strat_cache.leg2_trading_symbol is None:
            logging.debug(f"ignoring ticker: {leg2_tob.symbol} not found in strat_cache, "
                          f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
            leg2_tob = None
        return leg1_tob, leg2_tob

    @staticmethod
    def extract_legs_from_tobs(pair_strat, top_of_books) -> Tuple[TopOfBook | None, TopOfBook | None]:
        leg1_tob: TopOfBook | None = None
        leg2_tob: TopOfBook | None = None
        error = False
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[0].symbol:
            leg1_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[1].symbol:
                    leg2_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg2.sec.sec_id}, pair_strat_key: "
                                  f" {get_pair_strat_log_key(pair_strat)};;;top_of_books[1]: {top_of_books[1]}")
                    error = True
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[0].symbol:
            leg2_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[1].symbol:
                    leg1_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1].symbol}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id} pair_strat_key: "
                                  f"{get_pair_strat_log_key(pair_strat)};;;top_of_books[1]: {top_of_books[1]}")
                    error = True
        else:
            logging.error(f"unexpected security found in top_of_books[0]: {top_of_books[0].symbol}, expected either: "
                          f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id} or "
                          f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id} in pair_strat_key: "
                          f"{get_pair_strat_log_key(pair_strat)};;;top_of_books[1]: {top_of_books[1]}")
            error = True
        if error:
            return None, None
        else:
            return leg1_tob, leg2_tob

    def trading_link_internal_order_state_update(
            self, order_event: OrderEventType, order_id: str, side: Side | None = None,
            trading_sec_id: str | None = None, system_sec_id: str | None = None,
            underlying_account: str | None = None, msg: str | None = None):
        # coro needs public method
        run_coro = self.trading_link.internal_order_state_update(order_event, order_id, side, trading_sec_id,
                                                                 system_sec_id, underlying_account, msg)
        future = asyncio.run_coroutine_threadsafe(run_coro, StratExecutor.asyncio_loop)
        # block for start_executor_server task to finish
        try:
            return future.result()
        except Exception as e:
            logging.exception(f"_internal_reject_new_order failed with exception: {e}")

    def internal_reject_new_order(self, new_order: NewOrderBaseModel, reject_msg: str):
        self.internal_reject_count += 1
        internal_reject_order_id: str = str(self.internal_reject_count * -1) + str(DateTime.utcnow())
        self.trading_link_internal_order_state_update(
            OrderEventType.OE_REJ, internal_reject_order_id, new_order.side, None,
            new_order.security.sec_id, None, reject_msg)

    def set_unack(self, system_symbol: str, unack_state: bool):
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg1.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg1(unack_state)
        if self.strat_cache._pair_strat.pair_strat_params.strat_leg2.sec.sec_id == system_symbol:
            self.strat_cache.set_has_unack_leg2(unack_state)

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
            logging.error(f"check_unack: unknown system_symbol: {system_symbol}, check force failed for strat_cache: "
                          f"{self.strat_cache.get_key()}, "
                          f"pair_strat_key_key: {get_pair_strat_log_key(pair_strat)}")
        return False

    def place_new_order(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        order_limits: OrderLimitsBaseModel, px: float, usd_px: float, qty: int,
                        side: Side, system_symbol: str, err_dict: Dict[str, any] | None = None,
                        is_eqt: bool | None = None, check_mask: int = OrderControl.ORDER_CONTROL_SUCCESS) -> int:

        if err_dict is None:
            err_dict = dict()
        try:
            trading_symbol, account, exchange = self.strat_cache.get_metadata(system_symbol)
            if trading_symbol is None or account is None or exchange is None:
                logging.error(f"unable to send order, couldn't find metadata for: symbol {system_symbol}, meta-data:"
                              f" trading_symbol: {trading_symbol}, account: {account}, exch: {exchange} "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                return OrderControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL

            # block new order if any prior unack order exist
            if self.check_unack(system_symbol):
                error_msg: str = f"past order on symbol {system_symbol} is in unack state, dropping order with " \
                                 f"px: {px}, qty: {qty}, side: {side}, symbol_side_key: " \
                                 f"{get_symbol_side_key([(system_symbol, side)])}"
                logging.error(error_msg)
                return OrderControl.ORDER_CONTROL_CHECK_UNACK_FAIL

            if OrderControl.ORDER_CONTROL_SUCCESS == (ret_val := self.check_new_order(top_of_book, strat_brief,
                                                                                      order_limits, px, usd_px,
                                                                                      qty, side, system_symbol,
                                                                                      account, exchange, err_dict,
                                                                                      check_mask)):
                # check and block order if strat not in activ state [second fail-safe-check]
                strat_status_tuple = self.strat_cache.get_strat_status()
                if strat_status_tuple is not None:
                    strat_status, strat_status_update_date_time = strat_status_tuple
                    # If strat status not active, don't act, just return [check MD state and take action if required]
                    if strat_status.strat_state != StratState.StratState_ACTIVE or self._is_outside_trading_hours():
                        logging.error("Secondary Block place order - strat not in activ state or outside market hours")
                        return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                # set unack for subsequent orders this symbol to be blocked until this order goes through
                self.set_unack(system_symbol, True)
                if not self.trading_link_place_new_order(px, qty, side, trading_symbol, system_symbol, account, exchange):
                    # reset unack for subsequent orders to go through - this order did fail to go through
                    self.set_unack(system_symbol, False)
                    return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:
                    return OrderControl.ORDER_CONTROL_SUCCESS  # order sent out successfully
            else:
                return ret_val
        except Exception as e:
            logging.exception(f"place_new_order failed for: {system_symbol} px-qty-side: {px}-{qty}-{side}, with "
                              f"exception: {e}")
            return OrderControl.ORDER_CONTROL_EXCEPTION_FAIL
        finally:
            pass

    def trading_link_place_new_order(self, px, qty, side, trading_symbol, system_symbol, account, exchange):
        run_coro = self.trading_link.place_new_order(px, qty, side, trading_symbol, system_symbol,
                                                     account, exchange)
        future = asyncio.run_coroutine_threadsafe(run_coro, StratExecutor.asyncio_loop)

        # block for task to finish
        try:
            order_sent_status = future.result()
            return order_sent_status
        except Exception as e_:
            logging.exception(f"trading_link_place_new_order failed for {system_symbol} px-qty-side: {px}-{qty}-{side}"
                              f" with exception: {e_}")
            return False

    def check_consumable_concentration(self, strat_brief: StratBrief | StratBriefBaseModel,
                                       trading_brief: PairSideTradingBrief, qty: int,
                                       side_str: str) -> bool:
        if trading_brief.consumable_concentration - qty < 0:
            if trading_brief.consumable_concentration == 0:
                logging.error(f"blocked generated {side_str} order, unexpected: consumable_concentration found 0! "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            else:
                logging.error(f"blocked generated {side_str} order, not enough consumable_concentration: "
                              f"{strat_brief.pair_sell_side_trading_brief.consumable_concentration} needed: {qty}, "
                              f"for start_cache: {self.strat_cache.get_key()}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief)}")
            return False
        else:
            return True

    def check_strat_limits(self, strat_brief: StratBriefBaseModel, order_limits: OrderLimitsBaseModel,
                           px: float, usd_px: float, qty: int, side: Side,
                           order_usd_notional: float, system_symbol: str, err_dict: Dict[str, any]):
        checks_passed = OrderControl.ORDER_CONTROL_SUCCESS
        symbol_overview: SymbolOverviewBaseModel | None = None
        symbol_overview_tuple = \
            self.strat_cache.get_symbol_overview_from_symbol(system_symbol)
        if symbol_overview_tuple:
            symbol_overview, _ = symbol_overview_tuple
            if not symbol_overview:
                logging.error(f"block generated {side} order, symbol_overview missing for symbol: {system_symbol}, "
                              f"for strat_cache: {self.strat_cache.get_key()}, limit up/down needs "
                              f"symbol overview, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                return OrderControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            elif symbol_overview.limit_dn_px or not symbol_overview.limit_up_px:
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])} order, "
                              f"limit up/down px not available limit-dn px: {symbol_overview.limit_dn_px}, found {px}"
                              f", limit-up px: {symbol_overview.limit_up_px}")
                return OrderControl.ORDER_CONTROL_REQUIRED_DATA_MISSING_FAIL
            # else all good to continue limit checks

        if side == Side.SELL:
            # max_open_orders_per_side check
            if strat_brief.pair_sell_side_trading_brief.consumable_open_orders < 0:
                logging.error(f"blocked generated SELL order, not enough consumable_open_orders: "
                              f"{strat_brief.pair_sell_side_trading_brief.consumable_open_orders} for strat_cache: "
                              f"{self.strat_cache.get_key()}, strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

            # max_open_cb_notional check
            if order_usd_notional > strat_brief.pair_sell_side_trading_brief.consumable_open_notional:
                logging.error(f"blocked generated SELL order, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_sell_side_trading_brief.consumable_open_notional}, order needs:"
                              f" {order_usd_notional}, for symbol_side_key: "
                              f"{get_symbol_side_key([(system_symbol, side)])}")
                checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

            # covers: max cb notional, max open cb notional & max net filled notional
            # ( TODO Urgent: validate and add this description to log detail section ;;;)
            # Checking max_cb_notional
            if order_usd_notional > strat_brief.pair_sell_side_trading_brief.consumable_notional:
                logging.error(f"blocked generated SELL order, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_sell_side_trading_brief.consumable_notional}, order needs: "
                              f"{order_usd_notional} - the check covers: max cb notional, max open cb notional, "
                              f"max net filled notional, for start_cache: {self.strat_cache.get_key()}, "
                              f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL

            # Checking max_concentration
            if not self.check_consumable_concentration(strat_brief, strat_brief.pair_sell_side_trading_brief, qty,
                                                       "SELL"):
                checks_passed |= OrderControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

            # limit down - TODO : Important : Upgrade this to support trading at Limit Dn within the limit Dn limit
            if px < symbol_overview.limit_dn_px:
                logging.error(f"blocked generated SELL order, limit down trading not allowed on day-1, px "
                              f"expected higher than limit-dn px: {symbol_overview.limit_dn_px}, found {px} for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_LIMIT_DOWN_FAIL

        elif side == Side.BUY:
            # max_open_orders_per_side check
            if strat_brief.pair_buy_side_trading_brief.consumable_open_orders < 0:
                logging.error(f"blocked generated BUY order, not enough consumable_open_orders: "
                              f"{strat_brief.pair_buy_side_trading_brief.consumable_open_orders} for strat_cache: "
                              f"{self.strat_cache.get_key()}, strat_brief: {get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_MAX_OPEN_ORDERS_FAIL

            # max_open_cb_notional check
            if order_usd_notional > strat_brief.pair_buy_side_trading_brief.consumable_open_notional:
                logging.error(f"blocked symbol_side_key: {get_symbol_side_key([(system_symbol, side)])} order, "
                              f"breaches available consumable notional, order needs: "
                              f"{strat_brief.pair_buy_side_trading_brief.consumable_open_notional}, expected less than:"
                              f" {order_usd_notional}")
                checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_OPEN_NOTIONAL_FAIL

            if order_usd_notional > strat_brief.pair_buy_side_trading_brief.consumable_notional:
                logging.error(f"blocked generated BUY order, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_buy_side_trading_brief.consumable_notional}, order needs: "
                              f"{order_usd_notional} for strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_NOTIONAL_FAIL
            # Checking max_concentration
            if not self.check_consumable_concentration(strat_brief, strat_brief.pair_buy_side_trading_brief, qty,
                                                       "BUY"):
                checks_passed |= OrderControl.ORDER_CONTROL_MAX_CONCENTRATION_FAIL

            # Buy - not allowed more than limit up px
            # limit up - TODO : Important : Upgrade this to support trading at Limit Up within the limit Up limit
            if px > symbol_overview.limit_up_px:
                logging.error(f"blocked generated BUY order, limit up trading not allowed on day-1, px "
                              f"expected lower than limit-up px: {symbol_overview.limit_up_px}, found {px} for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}")
                checks_passed |= OrderControl.ORDER_CONTROL_LIMIT_UP_FAIL

        consumable_participation_qty: int = get_consumable_participation_qty_http(
            system_symbol, side, self.strat_limit.market_trade_volume_participation.applicable_period_seconds,
            self.strat_limit.market_trade_volume_participation.max_participation_rate, StratExecutor.asyncio_loop)
        if consumable_participation_qty is not None and consumable_participation_qty != 0:
            if consumable_participation_qty - qty < 0:
                logging.error(f"blocked generated order, not enough consumable_participation_qty available, "
                              f"expected higher than order qty: {qty}, found {consumable_participation_qty} for "
                              f"strat_cache: {self.strat_cache.get_key()}, strat_brief: "
                              f"{get_strat_brief_log_key(strat_brief)}, system_symbol: {system_symbol}, side: {side}, "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL
                if (consumable_participation_qty * usd_px) > order_limits.min_order_notional:
                    err_dict["consumable_participation_qty"] = f"{consumable_participation_qty}"
            # else check passed - no action
        else:
            strat_brief_key: str = get_strat_brief_log_key(strat_brief)
            logging.error(f"Received unusable consumable_participation_qty: {consumable_participation_qty} from "
                          f"get_consumable_participation_qty_http, system_symbol: {system_symbol}, side: {side}, "
                          f"applicable_period_seconds: "
                          f"{self.strat_limit.market_trade_volume_participation.applicable_period_seconds}, "
                          f"strat_brief_key: {strat_brief_key}, check failed")
            checks_passed |= OrderControl.ORDER_CONTROL_UNUSABLE_CONSUMABLE_PARTICIPATION_QTY_FAIL

        # checking max_net_filled_notional
        if order_usd_notional > strat_brief.consumable_nett_filled_notional:
            logging.error(f"blocked generated order, not enough consumable_nett_filled_notional available, "
                          f"remaining consumable_nett_filled_notional: {strat_brief.consumable_nett_filled_notional}, "
                          f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}")
            checks_passed |= OrderControl.ORDER_CONTROL_CONSUMABLE_NETT_FILLED_NOTIONAL_FAIL

        return checks_passed

    def get_breach_threshold_px(self, top_of_book: TopOfBookBaseModel, order_limits: OrderLimitsBaseModel,
                                side: Side, system_symbol: str) -> float | None:
        # TODO important - check and change reference px in cases where last px is not available
        if top_of_book.last_trade is None or math.isclose(top_of_book.last_trade.px, 0):
            # symbol_overview_tuple =  self.strat_cache.get_symbol_overview(top_of_book.symbol)
            logging.error(f"blocked generated order, symbol: {top_of_book.symbol}, side: {side} as "
                          f"top_of_book.last_trade.px is none or 0, symbol_side_key: "
                          f" {get_symbol_side_key([(top_of_book.symbol, side)])}")
            return None

        if side != Side.BUY and side != Side.SELL:
            logging.error(f"blocked generated unsupported side order, symbol_side_key: "
                          f"{get_symbol_side_key([(system_symbol, side)])}")
            return None  # None return blocks the order from going further

        aggressive_side = Side.BUY if side == Side.SELL else Side.SELL
        market_depths_tuple: Tuple[List[MarketDepthBaseModel | MarketDepth], DateTime] | None
        market_depths_tuple = self.strat_cache.get_market_depth(system_symbol, aggressive_side)
        market_depths: List[MarketDepthBaseModel | MarketDepth] | None = None
        if market_depths_tuple is not None:
            market_depths, _ = market_depths_tuple
        return self._get_breach_threshold_px(top_of_book, order_limits, side, system_symbol, market_depths)

    def _get_breach_threshold_px(self, top_of_book: TopOfBookBaseModel, order_limits: OrderLimitsBaseModel,
                                 side: Side, system_symbol: str, market_depths: List[MarketDepth]) -> float | None:
        px_by_max_level: float = 0
        for market_depth in market_depths:
            if market_depth.position <= order_limits.max_px_levels:
                px_by_max_level = market_depth.px
                break
        if math.isclose(px_by_max_level, 0):
            logging.error(f"blocked generated order, symbol: {system_symbol}, side: {side}, unable to find valid px"
                          f" based on max_px_levels: {order_limits.max_px_levels} limit from available depths, "
                          f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])};;;"
                          f"depths: {[str(market_depth) for market_depth in market_depths]}")
            return None
        if not top_of_book.last_trade:
            logging.error(f"block generated BUY order, symbol: {system_symbol}, side: {side}; top_of_book.last_trade"
                          f" is found None, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])};;;"
                          f"tob: {top_of_book}")
            return None  # None return blocks the order going further
        aggressive_quote: QuoteOptional | None = None
        if side == Side.BUY:
            aggressive_quote = top_of_book.ask_quote
            if not aggressive_quote:
                logging.error(f"blocked generated BUY order, symbol: {system_symbol}, side: {side} as aggressive_quote"
                              f" is not found or has no px, symbol_side_key: "
                              f"{get_symbol_side_key([(system_symbol, side)])};;;aggressive_quote: {aggressive_quote}")
                return None  # None return blocks the order from going further
            max_px_by_deviation: float = top_of_book.last_trade.px + (
                    top_of_book.last_trade.px / 100 * order_limits.max_px_deviation)
            max_px_by_basis_point: float = aggressive_quote.px + (aggressive_quote.px / 100 * (
                    order_limits.max_basis_points / 100))
            return min(max_px_by_basis_point, max_px_by_deviation, px_by_max_level)

        else:
            aggressive_quote = top_of_book.bid_quote
            if not aggressive_quote or not aggressive_quote.px:
                logging.error(f"blocked generated SELL order, symbol: {system_symbol}, side: {side} as aggressive_quote"
                              f" is found None, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                return None  # 0 return blocks the order from going further
            min_px_by_deviation: float = top_of_book.last_trade.px - (
                    top_of_book.last_trade.px / 100 * order_limits.max_px_deviation)
            min_px_by_basis_point: float = aggressive_quote.px - (aggressive_quote.px / 100 * (
                    order_limits.max_basis_points / 100))
            return max(min_px_by_deviation, min_px_by_basis_point, px_by_max_level)

    def check_new_order(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        order_limits: OrderLimitsBaseModel, px: float, usd_px: float,
                        qty: int, side: Side, system_symbol: str, account: str, exchange: str,
                        err_dict: Dict[str, any], check_mask: int = OrderControl.ORDER_CONTROL_SUCCESS) -> int:
        checks_passed: int = OrderControl.ORDER_CONTROL_SUCCESS

        order_usd_notional = usd_px * qty
        # min order notional is to be a order opportunity condition instead of order check
        checks_passed_ = OrderControl.check_min_order_notional(order_limits, order_usd_notional, system_symbol, side)

        if checks_passed_ != OrderControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        if check_mask == OrderControl.ORDER_CONTROL_CONSUMABLE_PARTICIPATION_QTY_FAIL:
            return checks_passed  # skip other checks - they were conducted before, this is adjusted order

        checks_passed_ = OrderControl.check_max_order_notional(order_limits, order_usd_notional, system_symbol, side)

        if checks_passed_ != OrderControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        checks_passed_ = OrderControl.check_max_order_qty(order_limits, qty, system_symbol, side)

        if checks_passed_ != OrderControl.ORDER_CONTROL_SUCCESS: checks_passed |= checks_passed_

        if top_of_book:
            breach_px: float = self.get_breach_threshold_px(top_of_book, order_limits, side, system_symbol)
            if breach_px is not None:
                if side == Side.BUY:
                    if px > breach_px:
                        logging.error(f"blocked generated BUY order, order px: {px} > allowed max_px {breach_px}, "
                                      f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                        checks_passed |= OrderControl.ORDER_CONTROL_BUY_ORDER_MAX_PX_FAIL
                elif side == Side.SELL:
                    if px < breach_px:
                        logging.error(f"blocked generated SELL order, order px: {px} < allowed min_px {breach_px}, "
                                      f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                        checks_passed |= OrderControl.ORDER_CONTROL_SELL_ORDER_MIN_PX_FAIL
                else:
                    logging.error(f"blocked generated unsupported Side: {side} order, order px: {px}, qty: {qty}, "
                                  f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
                    checks_passed |= OrderControl.ORDER_CONTROL_UNSUPPORTED_SIDE_FAIL
            else:
                logging.error(f"blocked generated order, breach_px returned None from get_breach_threshold_px for "
                              f"symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}, "
                              f"px: {px}, usd_px: {usd_px}")
                checks_passed |= OrderControl.ORDER_CONTROL_NO_BREACH_PX_FAIL
        else:
            logging.error(f"blocked generated order, unable to conduct px checks: top_of_book is sent None for strat: "
                          f"{self.strat_cache}, symbol_side_key: {get_symbol_side_key([(system_symbol, side)])}")
            checks_passed |= OrderControl.ORDER_CONTROL_NO_TOB_FAIL

        checks_passed |= self.check_strat_limits(strat_brief, order_limits, px, usd_px, qty, side, order_usd_notional,
                                                 system_symbol, err_dict)

        # TODO LAZY Read config "order_pace_seconds" to pace orders (needed for testing - not a limit)
        if self.order_pase_seconds > 0:
            # allow orders only after order_pase_seconds
            if self.last_order_timestamp.add(seconds=self.order_pase_seconds) < DateTime.now():
                checks_passed |= OrderControl.ORDER_CONTROL_ORDER_PASE_SECONDS_FAIL

        return checks_passed

    @staticmethod
    def create_n_run_md_shell_script(pair_strat, generation_start_file_path, generation_stop_file_path):
        subscription_data = \
            [
                (pair_strat.pair_strat_params.strat_leg1.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg1.sec.sec_type)),
                (pair_strat.pair_strat_params.strat_leg2.sec.sec_id,
                 str(pair_strat.pair_strat_params.strat_leg2.sec.sec_type.name))
            ]
        db_name = os.environ["DB_NAME"]
        exch_code = "SS" if pair_strat.pair_strat_params.strat_leg1.exch_id == "SSE" else "SZ"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=pair_strat.host,
                           port=pair_strat.port, db_name=db_name, exch_code=exch_code,
                           project_name="strat_executor"))

        create_stop_md_script(str(generation_start_file_path), str(generation_stop_file_path))
        os.chmod(generation_stop_file_path, stat.S_IRWXU)

        if os.path.exists(generation_start_file_path):
            # first stopping script if already exists
            subprocess.Popen([f"{generation_stop_file_path}"])
        create_md_shell_script(md_shell_env_data, str(generation_start_file_path), mode="MD")
        os.chmod(generation_start_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{generation_start_file_path}"])

    def _update_strat_state(self, strat_status_basemodel: StratStatusBaseModel):
        # coro needs public method
        run_coro = StratExecutor.underlying_partial_update_strat_status_http(
            jsonable_encoder(strat_status_basemodel, by_alias=True, exclude_none=True))
        future = asyncio.run_coroutine_threadsafe(run_coro, StratExecutor.asyncio_loop)

        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"underlying_partial_update_strat_status_http failed "
                              f"with exception: {e}")

    def _mark_strat_state_as_error(self, pair_strat: PairStratBaseModel):
        strat_status_basemodel = StratStatusBaseModel(_id=pair_strat.id)
        strat_status_basemodel.strat_state = StratState.StratState_ERROR
        alert_str: str = \
            (f"Marking strat_state to ERROR for strat: {self.pair_strat_executor_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}")
        logging.info(alert_str)

        self._update_strat_state(strat_status_basemodel)

    def _mark_strat_state_as_done(self, pair_strat: PairStratBaseModel):
        strat_status_basemodel = StratStatusBaseModel(_id=pair_strat.id)
        strat_status_basemodel.strat_state = StratState.StratState_DONE
        alert_str: str = \
            (f"graceful shut down processing for strat: {self.pair_strat_executor_id} "
             f"{get_pair_strat_log_key(pair_strat)};;; pair_strat: {pair_strat}")
        logging.info(alert_str)

        self._update_strat_state(strat_status_basemodel)

    def run(self):
        ret_val: int = -5000
        max_retry_count: Final[int] = 10
        retry_count: int = 0
        pair_strat_tuple: Tuple[PairStratBaseModel, DateTime] | None = None
        pair_strat: PairStratBaseModel | None = None
        while pair_strat_tuple is None or pair_strat is None:
            # getting pair_strat
            pair_strat_tuple: Tuple[PairStratBaseModel, DateTime] = self.strat_cache.get_pair_strat()
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

        scripts_dir = PurePath(__file__).parent.parent / "scripts"
        # start file generator
        start_sh_file_path = scripts_dir / f"start_ps_id_{pair_strat.id}_md.sh"
        stop_sh_file_path = scripts_dir / f"stop_ps_id_{pair_strat.id}_md.sh"

        try:
            StratExecutor.create_n_run_md_shell_script(pair_strat, start_sh_file_path, stop_sh_file_path)

            while 1:
                try:
                    ret_val = self.internal_run()
                except Exception as e:
                    logging.exception(f"Run returned with exception - sending again, exception: {e}")
                finally:
                    if ret_val == 1:
                        logging.info(f"explicit strat shutdown requested for: {self.pair_strat_executor_id}, "
                                     f"going down")
                        break
                    elif ret_val != 0:
                        logging.error(f"Error: Run returned, code: {ret_val} - sending again")
                    else:
                        pair_strat, _ = self.strat_cache.get_pair_strat()
                        strat_status_tuple = self.strat_cache.get_strat_status()
                        if strat_status_tuple is not None:
                            strat_status_, strat_status_update_date_time = strat_status_tuple
                            if strat_status_.strat_state != StratState.StratState_DONE:
                                self._mark_strat_state_as_done(pair_strat)
                                logging.debug(f"StratStatus with id: {self.pair_strat_executor_id} Marked Done, "
                                              f"pair_strat_key: {get_pair_strat_log_key(pair_strat)}")
                                ret_val = 0
                            else:
                                logging.error(f"unexpected, pair_strat: {self.pair_strat_executor_id} "
                                              f"was already Marked Done, pair_strat_key: "
                                              f"{get_pair_strat_log_key(pair_strat)}")
                                ret_val = -4000  # helps find the error location
                            break
                        else:
                            logging.error(f"strat_limits_tuple is None for: [ {self.strat_cache} ], "
                                          f"symbol_side_key: {get_pair_strat_log_key(pair_strat)}")
        except Exception as e:
            logging.exception(f"Some Error occurred in run method of executor, exception: {e}")
            ret_val = -4001
        finally:
            # running, stop md script
            subprocess.Popen([f"{stop_sh_file_path}"])

            if ret_val != 0 and ret_val != 1:
                self._mark_strat_state_as_error(pair_strat)

            # removing created scripts
            try:
                if os.path.exists(start_sh_file_path):
                    os.remove(start_sh_file_path)
                if os.path.exists(stop_sh_file_path):
                    os.remove(stop_sh_file_path)
            except Exception as e:
                err_str_ = (f"Something went wrong while deleting md scripts, "
                            f"exception: {e}")
                logging.error(err_str_)

        return ret_val

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.leg1_fx

    def _check_tob_n_place_non_systematic_order(self, new_order: NewOrderBaseModel, pair_strat: PairStrat,
                                                strat_brief: StratBriefBaseModel, order_limits: OrderLimitsBaseModel,
                                                top_of_books: List[TopOfBookBaseModel]) -> int:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        trade_tob: TopOfBookBaseModel | None = None
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        if leg1_tob is not None:
            if self.strat_cache.leg1_trading_symbol == new_order.security.sec_id:
                trade_tob = leg1_tob

        if trade_tob is None and leg2_tob is not None:
            if self.strat_cache.leg2_trading_symbol == new_order.security.sec_id:
                trade_tob = leg2_tob

        if trade_tob is None:
            err_str_ = f"unable to send new_order: no matching leg in this strat: {new_order} " \
                       f"pair_strat_key: {get_pair_strat_log_key(pair_strat)};;;" \
                       f"strat: {self.strat_cache}, pair_strat: {pair_strat}"
            logging.error(err_str_)
            return False
        else:
            usd_px = self.get_usd_px(new_order.px, new_order.security.sec_id)
            order_placed: int = self.place_new_order(trade_tob, strat_brief, order_limits, new_order.px, usd_px,
                                                     new_order.qty, new_order.side,
                                                     system_symbol=new_order.security.sec_id)
            return order_placed

    @staticmethod
    def get_leg1_leg2_ratio(leg1_px: float, leg2_px: float):
        if math.isclose(leg2_px, 0):
            return 0
        return leg1_px / leg2_px

    def _place_order(self, pair_strat: PairStratBaseModel, strat_brief: StratBriefBaseModel,
                     order_limits: OrderLimitsBaseModel, quote: QuoteOptional, tob: TopOfBookBaseModel):
        """returns float posted notional of the order sent"""
        # fail-safe
        strat_status_tuple = self.strat_cache.get_strat_status()
        if strat_status_tuple is not None:
            strat_status, strat_status_update_date_time = self.strat_cache.get_strat_status()
            # If strat status not active, don't act, just return [check MD state and take action if required]
            if strat_status.strat_state != StratState.StratState_ACTIVE or self._is_outside_trading_hours():
                logging.error("Blocked place order - strat not in activ state")
                return 0  # no order sent = no posted notional
        if not (quote.qty == 0 or math.isclose(quote.px, 0)):
            ask_usd_px: float = self.get_usd_px(quote.px, tob.symbol)
            order_placed = self.place_new_order(tob, strat_brief, order_limits, quote.px,
                                                ask_usd_px, quote.qty,
                                                Side.BUY, tob.symbol)
            if order_placed == OrderControl.ORDER_CONTROL_SUCCESS:
                posted_notional = quote.px * quote.qty
                return posted_notional
        else:
            logging.error(f"0 value found in ask TOB - ignoring px: {quote.px}, qty: {quote.qty}, pair_strat_key: "
                          f"{get_pair_strat_log_key(pair_strat)}")
            return 0  # no order sent = 0 posted notional

    def _check_tob_and_place_order(self, pair_strat: PairStratBaseModel | PairStrat, strat_brief: StratBriefBaseModel,
                                   order_limits: OrderLimitsBaseModel, top_of_books: List[TopOfBookBaseModel]) -> int:
        posted_leg1_notional: float = 0
        posted_leg2_notional: float = 0
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        trade_tob: TopOfBookBaseModel
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        order_placed: int = OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
        if leg1_tob is not None and self.strat_cache.leg1_trading_symbol is not None:
            if abs(self.leg1_notional) <= abs(self.leg2_notional):
                # process primary leg
                if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:  # execute aggressive buy
                    posted_leg1_notional = self._place_order(pair_strat, strat_brief, order_limits, leg1_tob.ask_quote,
                                                             leg1_tob)
                    if math.isclose(posted_leg1_notional, 0):
                        return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg1_notional = self._place_order(pair_strat, strat_brief, order_limits, leg1_tob.bid_quote,
                                                             leg1_tob)
                    if math.isclose(posted_leg1_notional, 0):
                        return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if leg2_tob is not None and self.strat_cache.leg2_trading_symbol is not None:
            if abs(self.leg2_notional) <= abs(self.leg1_notional):
                # process secondary leg
                if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:  # execute aggressive buy
                    posted_leg2_notional = self._place_order(pair_strat, strat_brief, order_limits, leg2_tob.ask_quote,
                                                             leg2_tob)
                    if math.isclose(posted_leg2_notional, 0):
                        return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL
                else:  # execute aggressive sell
                    posted_leg2_notional = self._place_order(pair_strat, strat_brief, order_limits, leg2_tob.bid_quote,
                                                             leg2_tob)
                    if math.isclose(posted_leg2_notional, 0):
                        return OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        if order_placed == OrderControl.ORDER_CONTROL_SUCCESS:
            self.last_order_timestamp = DateTime.now()
            self.leg1_notional += posted_leg1_notional
            self.leg2_notional += posted_leg2_notional
            logging.debug(f"strat-matched ToB for pair_strat_key {get_pair_strat_log_key(pair_strat)}: "
                          f"{[str(tob) for tob in top_of_books]}")
        return order_placed

    def _check_tob_and_place_order_test(self, pair_strat: PairStratBaseModel | PairStrat, strat_brief: StratBriefBaseModel,
                                        order_limits: OrderLimitsBaseModel,
                                        top_of_books: List[TopOfBookBaseModel]) -> int:
        buy_top_of_book: TopOfBookBaseModel | None = None
        sell_top_of_book: TopOfBookBaseModel | None = None
        buy_symbol_prefix = "CB_Sec"
        sell_symbol_prefix = "EQT_Sec"
        order_placed: int = OrderControl.ORDER_CONTROL_PLACE_NEW_ORDER_FAIL

        top_of_book_and_date_tuple = self.strat_cache.get_top_of_book(self._top_of_books_update_date_time)

        if top_of_book_and_date_tuple is not None:
            top_of_books, self._top_of_books_update_date_time = top_of_book_and_date_tuple
            if top_of_books is not None and len(top_of_books) == 2:
                if top_of_books[0] is not None and top_of_books[1] is not None:
                    latest_update_date_time: DateTime | None = None
                    for top_of_book in top_of_books:
                        if latest_update_date_time is None:
                            if top_of_book.symbol.startswith(buy_symbol_prefix):
                                buy_top_of_book = top_of_book
                                sell_top_of_book = None
                            elif top_of_book.symbol.startswith(sell_symbol_prefix):
                                sell_top_of_book = top_of_book
                                buy_top_of_book = None
                            else:
                                err_str_ = f"top_of_book with unsupported test symbol received, tob: {top_of_book}, " \
                                           f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                                logging.error(err_str_)
                                raise Exception(err_str_)
                            latest_update_date_time = top_of_book.last_update_date_time
                        else:
                            if top_of_book.last_update_date_time > latest_update_date_time:
                                if top_of_book.symbol.startswith(buy_symbol_prefix):
                                    buy_top_of_book = top_of_book
                                    sell_top_of_book = None
                                elif top_of_book.symbol.startswith(sell_symbol_prefix):
                                    sell_top_of_book = top_of_book
                                    buy_top_of_book = None
                                else:
                                    err_str_ = f"top_of_book with unsupported test symbol received, tob: {top_of_book}, " \
                                               f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                                    logging.error(err_str_)
                                    raise Exception(err_str_)
                                latest_update_date_time = top_of_book.last_update_date_time

                    if buy_top_of_book is not None:
                        if buy_top_of_book.bid_quote.last_update_date_time == \
                                self._top_of_books_update_date_time:
                            if buy_top_of_book.bid_quote.px == 110:
                                px = 100
                                usd_px: float = self.get_usd_px(px, buy_top_of_book.symbol)
                                order_placed = self.place_new_order(buy_top_of_book, strat_brief, order_limits, px,
                                                                    usd_px, 90,
                                                                    Side.BUY, buy_top_of_book.symbol)
                    elif sell_top_of_book is not None:
                        if sell_top_of_book.ask_quote.last_update_date_time == \
                                self._top_of_books_update_date_time:
                            if sell_top_of_book.ask_quote.px == 120:
                                px = 110
                                usd_px: float = self.get_usd_px(px, sell_top_of_book.symbol)
                                order_placed = self.place_new_order(sell_top_of_book, strat_brief, order_limits, px,
                                                                    usd_px, 70,
                                                                    Side.SELL, sell_top_of_book.symbol)
                    else:
                        err_str_ = "TOB updates could not find any updated buy or sell tob, " \
                                   f"strat_brief_key: {get_strat_brief_log_key(strat_brief)}"
                        logging.debug(err_str_)
                    return order_placed
                else:
                    logging.error(f"strats need both sides of TOB to be present, found  0 or 1"
                                  f", strat_brief_key: {get_strat_brief_log_key(strat_brief)};;;"
                                  f"tob found: {top_of_books[0]}, {top_of_books[1]}")
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
                logging.error(f"unable to find fx_symbol_overview for leg1_fx_symbol: "
                              f"{self.strat_cache.leg1_fx_symbol};;;strat_cache: {self.strat_cache}")
                return None

    def process_cxl_request(self):
        cancel_orders_and_date_tuple = self.strat_cache.get_cancel_order(self._cancel_orders_update_date_time)
        if cancel_orders_and_date_tuple is not None:
            cancel_orders, self._cancel_orders_update_date_time = cancel_orders_and_date_tuple
            if cancel_orders is not None:
                final_slice = len(cancel_orders)
                unprocessed_cancel_orders: List[CancelOrderBaseModel] = \
                    cancel_orders[self._cancel_orders_processed_slice:final_slice]
                self._cancel_orders_processed_slice = final_slice
                for cancel_order in unprocessed_cancel_orders:
                    if not cancel_order.cxl_confirmed:
                        self.trading_link_place_cxl_order(
                            cancel_order.order_id, cancel_order.side, None, cancel_order.security.sec_id,
                            underlying_account="NA")

                # if some update was on existing cancel_orders then this semaphore release was for this update only,
                # therefore returning True to continue and wait for next semaphore release
                return True
        # all else return false - no cancel_order to process
        return False

    def trading_link_place_cxl_order(self, order_id, side, trading_sec_id, system_sec_id, underlying_account):
        # coro needs public method
        run_coro = self.trading_link.place_cxl_order(order_id, side, trading_sec_id, system_sec_id, underlying_account)
        future = asyncio.run_coroutine_threadsafe(run_coro, StratExecutor.asyncio_loop)

        # block for start_executor_server task to finish
        try:
            # ignore return order_journal: don't generate cxl orders in system, just treat cancel acks as unsol cxls
            if not (res := future.result()):
                logging.error(f"trading_link_place_cxl_order failed, res: {res} returned")
        except Exception as e:
            logging.exception(f"trading_link_place_cxl_order failed with exception: {e}")

    def is_pair_strat_done(self, strat_brief: StratBriefBaseModel, ol: OrderLimitsBaseModel) -> int:
        """
        Args:
            strat_brief:
            ol: current order limits as set by system / user
        Returns:
            0: indicated done; no notional to consume on at-least 1 leg & no-open orders for this strat in market
            -1: indicates needs-processing; strat has notional left to consume on either of the legs
            + number: indicates finishing: no notional to consume on at-least 1 leg but open orders for strat in market
        """
        strat_done: bool = False
        open_order_count: int = self.strat_cache.get_open_order_count_from_cache()

        if 0 == open_order_count and (
                strat_brief.pair_sell_side_trading_brief.consumable_notional < ol.min_order_notional):
            # sell leg of strat is done - if either leg is done - strat is done
            logging.info(f"Sell Side Leg is done, no open orders remaining + sell-remainder: "
                         f"{strat_brief.pair_sell_side_trading_brief.consumable_notional} is less than"
                         f" min_order_notional: {ol.min_order_notional}, no further orders possible")
            strat_done = True
        # else not required, more notional to consume on sell leg - strat done is set to 1 (no error, not done)
        if 0 == open_order_count and (
                strat_brief.pair_buy_side_trading_brief.consumable_notional < ol.min_order_notional):
            # buy leg of strat is done - if either leg is done - strat is done
            logging.info(f"Buy Side Leg is done, no open orders remaining + buy-remainder: "
                         f"{strat_brief.pair_buy_side_trading_brief.consumable_notional} is less than"
                         f" min_order_notional: {ol.min_order_notional}, no further orders possible")
            strat_done = True
        # else not required, more notional to consume on buy leg - strat done is set to 1 (no error, not done)
        if strat_done:
            if 0 == open_order_count:
                logging.info(f"Strat is done")
            else:
                logging.warning(f"Strat is finishing [if / after strat open orders: {open_order_count} are filled]")
        else:
            return -1  # in progress

    def _get_latest_portfolio_status(self) -> PortfolioStatusBaseModel | None:
        portfolio_status: PortfolioStatusBaseModel | None = None
        portfolio_status_tuple = self.trading_data_manager.trading_cache.get_portfolio_status()
        if portfolio_status_tuple is None:
            logging.warning("no portfolio status found yet - strat will not trigger until portfolio status arrives")
            return None
        else:
            portfolio_status, self._portfolio_status_update_date_time = portfolio_status_tuple
        return portfolio_status


    def _get_latest_pair_strat(self) -> PairStrat | None:
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is not None:
            pair_strat, _ = pair_strat_tuple
            if pair_strat:
                return pair_strat
            else:
                logging.error(f"pair_strat in pair_strat_tuple is None for: {self.strat_cache}")
        else:
            logging.error(f"pair_strat_tuple is None for: {self.strat_cache}")
        return None

    def _is_outside_trading_hours(self):
        if self.is_sanity_test_run or self.is_test_run or self.is_dev_env: return False
        return False

    def internal_run(self):
        logging.debug("Started strat_executor run")
        while 1:
            self.strat_limit = None
            try:
                if self.strat_cache.stopped:
                    self.strat_cache.set_pair_strat(None)
                    return 1  # indicates explicit shutdown requested from server
                self.strat_cache.notify_semaphore.acquire()
                # remove all unprocessed signals from semaphore, logic handles all new updates in single iteration
                clear_semaphore(self.strat_cache.notify_semaphore)

                # 1. check if portfolio status has updated since we last checked
                portfolio_status: PortfolioStatusBaseModel | None = self._get_latest_portfolio_status()
                if portfolio_status is None: continue

                # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
                pair_strat: PairStrat = self._get_latest_pair_strat()
                if pair_strat is None: return -1

                strat_status_tuple = self.strat_cache.get_strat_status()
                if strat_status_tuple is not None:
                    strat_status, strat_status_update_date_time = strat_status_tuple
                    # If strat status not active, don't act, just return [check MD state and take action if required]
                    if strat_status.strat_state != StratState.StratState_ACTIVE or self._is_outside_trading_hours():
                        continue
                    else:
                        strat_limits_tuple = self.strat_cache.get_strat_limits()
                        self.strat_limit, strat_limits_update_date_time = strat_limits_tuple
                else:
                    logging.error(f"strat_status_tuple is None for: {self.strat_cache}")
                    return -1

                # 3. check if any cxl order is requested and send out
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
                                      f"{self.strat_cache.get_key()};;;strat_cache: [ {self.strat_cache} ]")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"can't proceed! strat_brief_tuple: {strat_brief_tuple} not found for strat-cache: "
                                  f"{self.strat_cache.get_key()};;;strat_cache: [ {self.strat_cache} ]")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                order_limits: OrderLimitsBaseModel | None = None
                order_limits_tuple = self.trading_data_manager.trading_cache.get_order_limits()
                if order_limits_tuple:
                    order_limits, _ = order_limits_tuple
                    if order_limits and self.strat_limit:
                        strat_done_counter = self.is_pair_strat_done(strat_brief, order_limits)
                        if 0 == strat_done_counter:
                            return 0  # triggers graceful shutdown
                        elif -1 != strat_done_counter:
                            # strat is finishing: waiting to close pending strat_done_counter number of open orders
                            continue
                        # else not needed - move forward, more processing needed to complete the strat
                    else:
                        logging.error(f"order_limits not found for strat: {self.strat_cache}, can't proceed")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"Can't proceed: order_limits/strat_limit not found for trading_cache: "
                                  f"{self.trading_data_manager.trading_cache}; strat_cache: {self.strat_cache}")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                # 4. get top_of_book (new or old to be checked by respective strat based on strat requirement)
                top_of_book_and_date_tuple = self.strat_cache.get_top_of_book()

                if top_of_book_and_date_tuple is not None:
                    top_of_books: List[TopOfBookBaseModel]
                    top_of_books, _ = top_of_book_and_date_tuple
                    if top_of_books is not None and len(top_of_books) == 2:
                        if top_of_books[0] is not None and top_of_books[1] is not None:
                            pass
                        else:
                            logging.warning(f"strats need both sides of TOB to be present, found  0 or 1"
                                            f";;;tob found: {top_of_books[0]}, {top_of_books[1]}")
                            continue
                    elif top_of_books is not None and len(top_of_books) == 1:
                        logging.error(f"Unexpected! found one tob, this should never happen - likely bug"
                                      f"{[str(tob) for tob in top_of_books]}, ignoring this round")
                        continue
                    else:
                        logging.error(f"unexpected , received: "
                                      f"{len(top_of_books) if top_of_books is not None else 0} in tob update!;;;"
                                      f"received-TOBs: "
                                      f"{[str(tob) for tob in top_of_books] if top_of_books is not None else None}!")
                        continue  # go next run - we don't stop processing for one faulty tob update
                else:
                    logging.error(f"No TOB exists yet, top_of_book_and_date_tuple is None for strat: "
                                  f"{self.strat_cache.get_key()};;;strat_cache: {self.strat_cache}")
                    continue  # go next run - we don't stop processing for one faulty tob update

                # 5. ensure leg1_fx is present - otherwise don't proceed - retry later
                if not self.get_leg1_fx():
                    logging.error(f"USD fx rate not found for strat: {self.strat_cache.get_key()}, unable to proceed, "
                                  f"fx symbol: {self.strat_cache.leg1_fx_symbol}, we'll retry in next attempt")
                    continue

                # 6. If kill switch is enabled - don't act, just return
                if portfolio_status.kill_switch:
                    logging.debug("not-progressing: kill switch enabled")
                    continue

                # 7. continue only if past-pair (iff triggered) has no open/unack orders
                open_orders_count: int = self.strat_cache.get_open_order_count_from_cache()
                if self.strat_cache.has_unack_leg() or 0 != open_orders_count:
                    logging.debug(f"blocked processing - part pair is still has {open_orders_count} open order(s)")
                    continue

                # 8. If any manual new_order requested: apply risk checks (maybe no strat param checks?) & send out
                new_orders_and_date_tuple = self.strat_cache.get_new_order(self._new_orders_update_date_time)
                if new_orders_and_date_tuple is not None:
                    new_orders, self._new_orders_update_date_time = new_orders_and_date_tuple
                    if new_orders is not None:
                        final_slice = len(new_orders)
                        unprocessed_new_orders: List[NewOrderBaseModel] = new_orders[
                                                                          self._new_orders_processed_slice:final_slice]
                        self._new_orders_processed_slice = final_slice
                        for new_order in unprocessed_new_orders:
                            if portfolio_status and not portfolio_status.kill_switch:
                                self._check_tob_n_place_non_systematic_order(new_order, pair_strat, strat_brief,
                                                                             order_limits, top_of_books)
                                continue
                            else:
                                # kill switch in force - drop the order
                                logging.error(f"Portfolio_status kill switch's is enabled, dropping non-systematic "
                                              f"new-order request;;;new order: {new_order} "
                                              "non-systematic new order call")
                                continue
                # else no new_order to process, ignore and move to next step

                if self.is_sanity_test_run:
                    self._check_tob_and_place_order_test(pair_strat, strat_brief, order_limits, top_of_books)
                else:
                    self._check_tob_and_place_order(pair_strat, strat_brief, order_limits, top_of_books)
                continue  # all good - go next run
            except Exception as e:
                logging.exception(f"Run returned with exception: {e}")
                return -1
        # we are outside while 1 (strat processing loop) - graceful shut down this strat processing
        return 0
