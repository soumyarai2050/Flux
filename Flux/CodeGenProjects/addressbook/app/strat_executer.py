import logging
import os
import time
from pathlib import PurePath
from threading import Thread
import math

os.environ["DBType"] = "beanie"
PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

from FluxPythonUtils.scripts.utility_functions import configure_logger
from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations
from Flux.CodeGenProjects.addressbook.app.trading_data_manager import TradingDataManager
from Flux.CodeGenProjects.addressbook.app.strat_cache import *
from Flux.CodeGenProjects.addressbook.app.trading_link import get_trading_link, TradingLinkBase
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import *


class StratExecutor:
    trading_link: ClassVar[TradingLinkBase] = get_trading_link()

    @staticmethod
    def executor_trigger(trading_data_manager: TradingDataManager, strat_cache: StratCache):
        strat_executor: StratExecutor = StratExecutor(trading_data_manager, strat_cache)
        strat_executor_thread = Thread(target=strat_executor.run, daemon=True).start()
        return strat_executor, strat_executor_thread

    """ 1 instance = 1 thread = 1 pair strat"""

    def __init__(self, trading_data_manager: TradingDataManager, strat_cache: StratCache):
        config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"
        config_dict = load_yaml_configurations(str(config_file_path))
        self.is_test_run: bool = config_dict.get("is_test_run")
        self.trading_data_manager: TradingDataManager = trading_data_manager
        self.strat_cache: StratCache = strat_cache

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

        self.primary_leg_notional: float = 0
        self.secondary_leg_notional: float = 0

    def check_order_eligibility(self, side: Side, check_notional: float) -> bool:
        strat_brief, self._strat_brief_update_date_time = \
            self.strat_cache.get_strat_brief(self._strat_brief_update_date_time)
        portfolio_status, self._portfolio_status_update_date_time = \
            self.trading_data_manager.trading_cache.get_portfolio_status(self._portfolio_status_update_date_time)
        if side == Side.BUY:
            if strat_brief.pair_buy_side_trading_brief.consumable_notional - check_notional > 0:
                if portfolio_status.current_period_available_buy_order_count > 0:
                    return True
                else:
                    return False
            else:
                return False
        else:
            if strat_brief.pair_sell_side_trading_brief.consumable_notional - check_notional > 0:
                if portfolio_status.current_period_available_sell_order_count > 0:
                    return True
                else:
                    return False
            else:
                return False

    def get_px_qty_from_depth(self, depth: int, symbol: str, side: Side) -> MarketDepthBaseModel:  # NOQA
        market_depth_objs = self.trading_link.market_data_service_web_client.get_market_depth_from_index_client(symbol)
        side = "BID" if side == Side.BUY else "ASK"

        if len(market_depth_objs) > 0:
            for market_depth_obj in market_depth_objs:
                if market_depth_obj.side == side and market_depth_obj.position == depth - 1:
                    return market_depth_obj
            else:
                raise Exception(f"Couldn't find market_depth obj with depth: {depth} and side {side} "
                                f"for symbol {symbol}")
        else:
            raise Exception(f"Can't find market_depth objects for symbol {symbol}")

    def extract_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[TopOfBook | None, TopOfBook | None]:
        primary_leg: TopOfBook | None = None
        secondary_leg: TopOfBook | None = None
        error = False
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[0].symbol:
            primary_leg = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[1].symbol:
                    secondary_leg = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1]}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
                    error = True
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[0].symbol:
            secondary_leg = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[1].symbol:
                    primary_leg = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1]}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg1.sec.sec_id}")
                    error = True
        else:
            logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1]}, expected either of: "
                          f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id} or "
                          f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
            error = True
        if error:
            return None, None
        else:
            return primary_leg, secondary_leg

    def place_new_order(self, px: float, qty, side: Side, trading_symbol: str, system_symbol: str, account, exchange) \
            -> bool:
        if self.check_new_order_limits(px, qty, side, trading_symbol, account, exchange):
            return get_trading_link().place_new_order(px, qty, side, trading_symbol, system_symbol, account, exchange)
        else:
            return False

    def check_new_order_limits(self, px, qty, side, trading_symbol, account, exchange) -> bool:
        checks_passed: bool = True
        order_limits: OrderLimitsBaseModel
        order_limits, _ = self.trading_data_manager.trading_cache.get_order_limits()
        order_notional = px * qty
        if order_limits.max_order_notional < order_notional:
            logging.error(f"blocked generated order, breaches max_order_notional limit, expected less than: "
                          f"{order_limits.max_order_notional}, found: {order_notional} ")
            checks_passed = False
        if order_limits.min_order_notional > order_notional:
            logging.error(f"blocked generated order, breaches min_order_notional limit, expected more than: "
                          f"{order_limits.min_order_notional}, found: {order_notional} ")
            checks_passed = False
        if order_limits.max_order_qty < qty:
            logging.error(f"blocked generated order, breaches max_order_qty limit, expected less than: "
                          f"{order_limits.max_order_qty}, found: {qty} ")
            checks_passed = False
        return checks_passed

    def run(self):
        ret_val: int = -5000
        while 1:
            try:
                ret_val = self.internal_run()
            except Exception as e:
                logging.error(f"Run returned with exception - sending again, exception: {e}")
            finally:
                if ret_val != 0:
                    logging.error(f"Error: Run returned, code: {ret_val} - sending again")
                else:
                    pair_strat, _ = self.strat_cache.get_pair_strat()
                    logging.warning(f"graceful shut down this strat processing for strat: "
                                    f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}_"
                                    f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id}_"
                                    f"{pair_strat.id};;;strat details: {self.strat_cache.get_pair_strat()}")
                    break

    def _check_tob_and_place_order(self, pair_strat: PairStratBaseModel) -> bool:
        posted_primary_notional: float = 0
        posted_secondary_notional: float = 0
        top_of_book_and_date_tuple = self.strat_cache.get_top_of_books(self._top_of_books_update_date_time)
        if top_of_book_and_date_tuple is not None:
            top_of_books, self._top_of_books_update_date_time = top_of_book_and_date_tuple
            if top_of_books is not None and len(top_of_books) <= 2:
                primary_leg, secondary_leg = self.extract_legs_from_tobs(pair_strat, top_of_books)
                if primary_leg is not None and self.strat_cache.primary_leg_trading_symbol is None:
                    primary_leg = None
                    logging.error(f"Unable to proceed with this ticker: {primary_leg} no static data")
                if secondary_leg is not None and self.strat_cache.secondary_leg_trading_symbol is None:
                    secondary_leg = None
                    logging.error(f"Unable to proceed with this ticker: {primary_leg} no static data")
                if primary_leg is not None and self.strat_cache.primary_leg_trading_symbol is not None:
                    if abs(self.primary_leg_notional) <= abs(self.secondary_leg_notional):
                        # process primary leg
                        if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:  # execute aggressive buy
                            if not (primary_leg.ask_quote.qty == 0 or math.isclose(primary_leg.ask_quote.px,
                                                                                   0)):
                                self.place_new_order(primary_leg.ask_quote.px, primary_leg.ask_quote.qty,
                                                     Side.BUY,
                                                     self.strat_cache.primary_leg_trading_symbol,
                                                     primary_leg.symbol,
                                                     "trading-account", "exchange-name")
                                posted_primary_notional = primary_leg.ask_quote.px * primary_leg.ask_quote.qty
                                return True
                            else:
                                logging.error(
                                    f"0 value found in ask TOB - ignoring: px{primary_leg.ask_quote.px}, "
                                    f"qty: {primary_leg.ask_quote.qty}")
                                return False
                        else:  # execute aggressive sell
                            if not (primary_leg.bid_quote.qty == 0 or math.isclose(primary_leg.bid_quote.px,
                                                                                   0)):
                                self.place_new_order(primary_leg.bid_quote.px, primary_leg.bid_quote.qty,
                                                     Side.SELL, self.strat_cache.primary_leg_trading_symbol,
                                                     primary_leg.symbol,
                                                     "trading-account", "exchange-name")
                                posted_primary_notional = primary_leg.bid_quote.px * primary_leg.bid_quote.qty
                                return True
                            else:
                                logging.error(f"0 value found in TOB - ignoring: px {primary_leg.bid_quote.px}"
                                              f", qty: {primary_leg.bid_quote.qty}")
                                return False
                if secondary_leg is not None and self.strat_cache.secondary_leg_trading_symbol is not None:
                    if abs(self.secondary_leg_notional) <= abs(self.primary_leg_notional):
                        # process secondary leg
                        if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:  # execute aggressive buy
                            if not (secondary_leg.ask_quote.qty == 0 or
                                    math.isclose(secondary_leg.ask_quote.px, 0)):
                                self.place_new_order(secondary_leg.ask_quote.px, secondary_leg.ask_quote.qty,
                                                     Side.BUY, self.strat_cache.secondary_leg_trading_symbol,
                                                     secondary_leg.symbol,
                                                     "trading-account", "exchange-name")
                                posted_secondary_notional = \
                                    secondary_leg.ask_quote.px * secondary_leg.ask_quote.qty
                                return True
                            else:
                                logging.error(
                                    f"0 value found in ask TOB - ignoring: px{secondary_leg.ask_quote.px}, "
                                    f"qty: {secondary_leg.ask_quote.qty}")
                                return False
                        else:  # execute aggressive sell
                            if not (secondary_leg.bid_quote.qty == 0 or
                                    math.isclose(secondary_leg.bid_quote.px, 0)):
                                self.place_new_order(secondary_leg.bid_quote.px, secondary_leg.bid_quote.qty,
                                                     Side.SELL, self.strat_cache.secondary_leg_trading_symbol,
                                                     secondary_leg.symbol,
                                                     "trading-account", "exchange-name")
                                posted_secondary_notional = \
                                    secondary_leg.bid_quote.px * secondary_leg.bid_quote.qty
                                return True
                            else:
                                logging.error(
                                    f"0 value found in TOB - ignoring: px {secondary_leg.bid_quote.px}"
                                    f", qty: {secondary_leg.bid_quote.qty}")
                                return False
                self.primary_leg_notional += posted_primary_notional
                self.secondary_leg_notional += posted_secondary_notional
                logging.debug(f"strat-matched ToB: {[str(tob) for tob in top_of_books]}")
            else:
                logging.error(f"expected 1 / 2 TOB , received: "
                              f"{len(top_of_books) if top_of_books is not None else 0} in tob update!;;;"
                              f"received-TOBs: "
                              f"{[str(tob) for tob in top_of_books] if top_of_books is not None else None}!")
                return False
        else:
            return False  # no update to process

    def _check_tob_and_place_order_test(self, pair_strat: PairStratBaseModel) -> bool:
        from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator

        top_of_book_and_date_tuple = self.strat_cache.get_top_of_books(self._top_of_books_update_date_time)
        if top_of_book_and_date_tuple is not None:
            top_of_books, self._top_of_books_update_date_time = top_of_book_and_date_tuple
            if top_of_books is not None:
                if top_of_books[0].symbol == "CB_Sec_1":
                    buy_top_of_book = top_of_books[0]
                    sell_top_of_book = top_of_books[1]
                else:
                    buy_top_of_book = top_of_books[1]
                    sell_top_of_book = top_of_books[0]

                if buy_top_of_book.bid_quote.last_update_date_time.replace(tzinfo=pytz.UTC) == \
                        self._top_of_books_update_date_time:
                    if buy_top_of_book.bid_quote.px == 25:
                        order_id = TradeSimulator.place_new_order(100, 90, Side.BUY, "CB_Sec_1", "", "Acc1")

                if sell_top_of_book.ask_quote.last_update_date_time.replace(tzinfo=pytz.UTC) == \
                        self._top_of_books_update_date_time:
                    if sell_top_of_book.ask_quote.px == 25:
                        order_id = TradeSimulator.place_new_order(110, 70, Side.SELL, "EQT_Sec_1", "", "Acc1")
                return True
        else:
            return False  # no update to process

    def internal_run(self):
        while 1:
            try:
                if self.strat_cache.stopped:
                    break
                self.strat_cache.notify_semaphore.acquire()

                # 0. get pair-strat: no checking if it's updated since last checked (required for TOB extraction &
                # get consumable_allowed_participation_volume
                consumable_allowed_participation_volume: int | None = None
                pair_strat_tuple = self.strat_cache.get_pair_strat()
                if pair_strat_tuple is not None:
                    pair_strat, pair_strat_update_date_time = pair_strat_tuple
                    # If strat status not active, don't act, just return
                    if pair_strat.strat_status.strat_state != StratState.StratState_ACTIVE:
                        continue
                else:
                    logging.error(f"pair_strat_tuple is None for: {self.strat_cache}")
                    return -1

                # 1. computing consumable_allowed_participation_volume
                buy_consumable_allowed_participation_volume: int
                sell_consumable_allowed_participation_volume: int
                buy_symbol = pair_strat.pair_strat_params.strat_leg1.sec.sec_id
                sell_symbol = pair_strat.pair_strat_params.strat_leg2.sec.sec_id
                applicable_period_seconds = \
                    pair_strat.strat_limits.market_trade_volume_participation.applicable_period_seconds
                last_sec_market_trade_vol_obj = \
                    StratExecutor.trading_link.market_data_service_web_client.get_last_n_sec_total_qty_query_client(
                        [buy_symbol, sell_symbol, applicable_period_seconds])[0]
                buy_consumable_allowed_participation_volume = \
                    last_sec_market_trade_vol_obj.buy_side_last_sec_trade_vol
                sell_consumable_allowed_participation_volume = \
                    last_sec_market_trade_vol_obj.sell_side_last_sec_trade_vol

                # 1. check if portfolio status has updated since we last checked
                portfolio_status_tuple = self.trading_data_manager.trading_cache.get_portfolio_status()
                if portfolio_status_tuple is None:
                    logging.warning(
                        "no portfolio status found yet - strat will not trigger until portfolio status arrives")
                    continue
                if portfolio_status_tuple is not None:
                    portfolio_status, self._portfolio_status_update_date_time = portfolio_status_tuple
                    # If kill switch is enabled - don't act, just return
                    if portfolio_status.kill_switch:
                        continue
                # else no update - do we need this processed again ?

                # 3. check if any cxl order is requested and send out
                cancel_orders_and_date_tuple = self.strat_cache.get_cancel_orders(self._cancel_orders_update_date_time)
                if cancel_orders_and_date_tuple is not None:
                    cancel_orders, self._cancel_orders_update_date_time = cancel_orders_and_date_tuple
                    if cancel_orders is not None:
                        final_slice = len(cancel_orders)
                        unprocessed_cancel_orders: List[CancelOrderBaseModel] = \
                            cancel_orders[self._cancel_orders_processed_slice:final_slice]
                        self._cancel_orders_processed_slice = final_slice
                        for cancel_order in unprocessed_cancel_orders:
                            self.trading_link.place_cxl_order(cancel_order.order_id, cancel_order.side,
                                                              cancel_order.security.sec_id)
                # else no cancel_order to process

                # 4. check if any new_order is requested: apply all risk checks, no strat param checks and send out
                new_orders_and_date_tuple = self.strat_cache.get_new_orders(self._new_orders_update_date_time)
                if new_orders_and_date_tuple is not None:
                    new_orders, self._new_orders_update_date_time = new_orders_and_date_tuple
                    if new_orders is not None:
                        final_slice = len(new_orders)
                        unprocessed_new_orders: List[NewOrderBaseModel] = new_orders[
                                                                          self._new_orders_processed_slice:final_slice]
                        self._new_orders_processed_slice = final_slice
                        for new_order in unprocessed_new_orders:
                            if self.check_new_order_limits(new_order.px, new_order.qty, new_order.side,
                                                           new_order.security.sec_id, "trading-symbol",
                                                           "trading-account"):
                                self.trading_link.place_new_order(new_order.px, new_order.qty, new_order.side,
                                                                  new_order.security.sec_id, "trading-symbol",
                                                                  "trading-account")
                            else:
                                logging.error(f"order check failed - unable to send new_order: {new_order}")
                # else no new_order to process

                # 5. check if top_of_book is updated
                if not self.is_test_run:
                    if not self._check_tob_and_place_order(pair_strat):
                        continue
                else:
                    if not self._check_tob_and_place_order_test(pair_strat):
                        continue

            except Exception as e:
                logging.error(f"Run returned with exception - sending again, exception: {e}")
                return -1
        # we are outside while 1 (strat processing loop) - graceful shut down this strat processing
        return 0


if __name__ == "__main__":
    from datetime import datetime

    log_dir: PurePath = PurePath(__file__).parent.parent / "log"
    datetime_str: str = datetime.now().strftime("%Y%m%d")
    configure_logger('debug', str(log_dir), f'strat_executor_{datetime_str}.log')

    trading_data_manager = TradingDataManager(StratExecutor.executor_trigger)
    while 1:
        time.sleep(10)
