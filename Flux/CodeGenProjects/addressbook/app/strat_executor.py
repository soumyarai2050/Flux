import inspect
import os
import sys
import time
from pathlib import PurePath
from threading import Thread
import math

from FluxPythonUtils.scripts.utility_functions import configure_logger

os.environ["DBType"] = "beanie"

from Flux.CodeGenProjects.addressbook.app.trading_data_manager import TradingDataManager
from Flux.CodeGenProjects.addressbook.app.strat_cache import *
from Flux.CodeGenProjects.addressbook.app.trading_link import get_trading_link, TradingLinkBase, config_dict
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import \
    get_consumable_participation_qty_http, create_alert, get_pair_strat_key, get_portfolio_limits
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
        self.pair_strat_id: str | None = None
        self.is_test_run: bool = config_dict.get("is_test_run")

        self.trading_data_manager: TradingDataManager = trading_data_manager
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

        self.strat_limit: StratLimits | None = None
        self.last_order_timestamp: DateTime | None = None

        self.leg1_notional: float = 0
        self.leg2_notional: float = 0

        self.order_pase_seconds = 0
        # internal rejects to use:  -ive internal_reject_count + current date time as order id
        self.internal_reject_count = 0

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

    def update_market_depth_snapshot_from_http(self):
        market_depths: List[MarketDepthBaseModel] = \
            self.trading_link.market_data_service_web_client.get_all_market_depth_client()
        if market_depths:
            for market_depth in market_depths:
                self.strat_cache.set_market_depth(market_depth)

    def update_symbol_overviews_from_http(self):
        symbol_overviews: List[SymbolOverviewBaseModel] = \
            self.trading_link.market_data_service_web_client.get_all_symbol_overview_client()
        if symbol_overviews:
            for symbol_overview_ in symbol_overviews:
                self.trading_data_manager.handle_symbol_overview_ws(symbol_overview_)
            self.get_leg1_fx()  # internally looks up the updated fx symbol overview form above and updates it

    def update_tobs_from_http(self):
        tobs: List[TopOfBookBaseModel] = \
            self.trading_link.market_data_service_web_client.get_all_top_of_book_client()  # Never returns None
        if tobs:
            for tob in tobs:
                self.trading_data_manager.handle_top_of_book_ws(tob)
            # if we need fx TOB: self.strat_cache needs to collect reference here (like we do in symbol_overview)

    def update_strat_brief_from_http(self):
        strat_briefs: List[StratBriefBaseModel] | None = \
            self.trading_link.strat_manager_service_web_client.get_all_strat_brief_client()
        if strat_briefs:
            for strat_brief in strat_briefs:
                self.strat_cache.set_strat_brief(strat_brief)

    def update_portfolio_limits_from_http(self):
        portfolio_limits: PortfolioLimitsBaseModel | None = get_portfolio_limits()
        if portfolio_limits:
            self.trading_data_manager.trading_cache.set_portfolio_limits(portfolio_limits)

    def get_market_depths(self, symbol: str, side: Side) -> List[MarketDepthBaseModel]:
        market_depths = self.trading_link.market_data_service_web_client.get_market_depth_from_index_client(symbol)
        # store for subsequent reference
        if market_depths:
            for market_depth in market_depths:
                self.strat_cache.set_market_depth(market_depth)
        side = "BID" if side == Side.BUY else "ASK"
        filtered_market_depths: List[MarketDepthBaseModel] = []
        if market_depths:
            for market_depth in market_depths:
                if market_depth.side == side:
                    filtered_market_depths.append(market_depth)
        if not filtered_market_depths:
            logging.error(f"No market_depth object found for symbol: {symbol} side: {side}")
        else:
            # sort the smallest position to largest
            filtered_market_depths.sort(reverse=True, key=lambda x: x.position)
        return filtered_market_depths  # return empty if none found

    def extract_strat_specific_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[TopOfBook | None,
                                                                                       TopOfBook | None]:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        leg1_tob, leg2_tob = self.extract_legs_from_tobs(pair_strat, top_of_books)
        if leg1_tob is not None and self.strat_cache.leg1_trading_symbol is None:
            leg1_tob = None
            logging.debug(f"ignoring ticker: {leg1_tob} not found in strat_cache")
        if leg2_tob is not None and self.strat_cache.leg2_trading_symbol is None:
            leg2_tob = None
            logging.debug(f"ignoring ticker: {leg2_tob} not found in strat_cache")
        return leg1_tob, leg2_tob

    def extract_legs_from_tobs(self, pair_strat, top_of_books) -> Tuple[TopOfBook | None, TopOfBook | None]:
        leg1_tob: TopOfBook | None = None
        leg2_tob: TopOfBook | None = None
        error = False
        if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[0].symbol:
            leg1_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[1].symbol:
                    leg2_tob = top_of_books[1]
                else:
                    logging.error(f"unexpected security found in top_of_books[1]: {top_of_books[1]}, "
                                  f"expected: {pair_strat.pair_strat_params.strat_leg2.sec.sec_id}")
                    error = True
        elif pair_strat.pair_strat_params.strat_leg2.sec.sec_id == top_of_books[0].symbol:
            leg2_tob = top_of_books[0]
            if len(top_of_books) == 2:
                if pair_strat.pair_strat_params.strat_leg1.sec.sec_id == top_of_books[1].symbol:
                    leg1_tob = top_of_books[1]
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
            return leg1_tob, leg2_tob

    def internal_reject_new_order(self, new_order: NewOrderBaseModel, reject_msg: str):
        self.internal_reject_count += 1
        internal_reject_order_id: str = str(self.internal_reject_count * -1) + str(DateTime.utcnow())
        self.trading_link.internal_order_state_update(OrderEventType.OE_REJ, internal_reject_order_id, new_order.side,
                                                      new_order.security.sec_id, None, reject_msg)

    def set_unack(self, symbol: str, unack_state: bool):
        if self.strat_cache.leg1_trading_symbol == symbol:
            self.strat_cache.set_has_unack_leg1(unack_state)
        if self.strat_cache.leg2_trading_symbol == symbol:
            self.strat_cache.set_has_unack_leg2(unack_state)

    def check_unack(self, symbol: str):
        if self.strat_cache.leg1_trading_symbol == symbol:
            if self.strat_cache.has_unack_leg1():
                return True

        elif self.strat_cache.leg2_trading_symbol == symbol:
            if self.strat_cache.has_unack_leg2():
                return True

        return False

    def place_new_order(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        order_limits: OrderLimitsBaseModel, px: float, usd_px: float, qty: int,
                        side: Side, system_symbol: str) -> bool:
        trading_symbol, account, exchange = self.strat_cache.get_metadata(system_symbol)
        if trading_symbol is None or account is None or exchange is None:
            logging.error(f"unable to send order, couldn't find metadata for: symbol {system_symbol}, meta-data:"
                          f" trading_symbol: {trading_symbol}, account: {account}, exch: {exchange}")
            return False

        # block new order if any prior unack order exist
        if self.check_unack(system_symbol):
            error_msg: str = f"past order on symbol {system_symbol} is in unack state, dropping order with " \
                             f"px: {px}, qty: {qty}, side: {side}"
            logging.error(error_msg)
            return False

        if self.check_new_order(top_of_book, strat_brief, order_limits, px, usd_px, qty, side, system_symbol, account,
                                exchange):
            # set unack for subsequent orders this symbol to be blocked until this order goes through
            self.set_unack(system_symbol, True)
            if not self.trading_link.place_new_order(px, qty, side, trading_symbol, system_symbol, account, exchange):
                # reset unack for subsequent orders to go through - this order did fail to go through
                self.set_unack(system_symbol, False)
                return False
            else:
                return True  # order sent out successfully
        else:
            return False

    def check_strat_limits(self, strat_brief: StratBriefBaseModel, px: float, usd_px: float, qty: int, side: Side,
                           order_usd_notional: float, system_symbol: str):
        # max_open_orders_per_side check
        check_passed = True
        symbol_overview: SymbolOverviewBaseModel | None = None
        if side == Side.SELL:
            symbol_overview_tuple = \
                self.strat_cache.get_symbol_overview(strat_brief.pair_sell_side_trading_brief.security.sec_id)
            if symbol_overview_tuple:
                symbol_overview, _ = symbol_overview_tuple
                if not symbol_overview:
                    logging.error(f"blocked generated SELL order, symbol_overview missing: limit down check can't be "
                                  f"applied")
                    return False
            else:
                logging.error(f"blocked generated SELL order, symbol_overview_tuple missing: limit down check can't be "
                              f"applied")
                return False

            if strat_brief.pair_sell_side_trading_brief.consumable_open_orders < 0:
                logging.error(f"blocked generated SELL order, not enough consumable_open_orders: "
                              f"{strat_brief.pair_sell_side_trading_brief.consumable_open_orders} ")
                check_passed = False

            # covers: max cb notional, max open cb notional & max net filled notional (validate)
            if order_usd_notional > strat_brief.pair_sell_side_trading_brief.consumable_notional:
                logging.error(f"blocked generated SELL order, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_sell_side_trading_brief.consumable_notional}, order needs: "
                              f"{order_usd_notional} - the check covers: max cb notional, max open cb notional, "
                              f"max net filled notional, ")
                check_passed = False

            if strat_brief.pair_sell_side_trading_brief.consumable_concentration - qty < 0:
                logging.error(f"blocked generated SELL order, not enough consumable_concentration: "
                              f"{strat_brief.pair_sell_side_trading_brief.consumable_concentration}n needed: {qty} ")
                check_passed = False

            # limit down - TODO : Important : Upgrade this to support trading at Limit Dn within the limit Dn limit
            if px < symbol_overview.limit_dn_px:
                logging.error(f"blocked generated SELL order, limit down trading not allowed on day-1, px "
                              f"expected higher than limit-dn px: {symbol_overview.limit_dn_px}, found {px}")
                check_passed = False

        elif side == Side.BUY:
            symbol_overview_tuple = \
                self.strat_cache.get_symbol_overview(strat_brief.pair_buy_side_trading_brief.security.sec_id)
            if symbol_overview_tuple:
                symbol_overview, _ = symbol_overview_tuple
                if not symbol_overview:
                    logging.error(f"blocked generated BUY order, symbol_overview missing: limit down check can't be "
                                  f"applied")
                    return False
            else:
                logging.error(f"blocked generated BUY order, symbol_overview_tuple missing: limit down check can't be "
                              f"applied")
                return False

            if strat_brief.pair_buy_side_trading_brief.consumable_open_orders < 0:
                logging.error(f"blocked generated BUY order, not enough consumable_open_orders: "
                              f"{strat_brief.pair_buy_side_trading_brief.consumable_open_orders} ")
                check_passed = False
            if order_usd_notional > strat_brief.pair_buy_side_trading_brief.consumable_notional:
                logging.error(f"blocked generated BUY order, breaches available consumable notional, expected less "
                              f"than: {strat_brief.pair_buy_side_trading_brief.consumable_notional}, order needs: "
                              f"{order_usd_notional} ")
                check_passed = False
            # limit up - TODO : Important : Upgrade this to support trading at Limit Up within the limit Up limit
            if px > symbol_overview.limit_up_px:
                logging.error(f"blocked generated SELL order, limit down trading not allowed on day-1, px "
                              f"expected higher than limit-dn px: {symbol_overview.limit_dn_px}, found {px}")
                check_passed = False

        consumable_participation_qty: int = get_consumable_participation_qty_http \
            (system_symbol, side, self.strat_limit.market_trade_volume_participation.applicable_period_seconds,
             self.strat_limit.market_trade_volume_participation.max_participation_rate)

        if consumable_participation_qty - qty < 0:
            logging.error(f"blocked generated order, not enough consumable_participation_qty available, "
                          f"expected higher than order qty: {qty}, found {consumable_participation_qty}")
            check_passed = False

        return check_passed

    def check_portfolio_limits(self, symbol, side, pair_strat_: PairStratBaseModel) -> bool:
        applicable_period_seconds = pair_strat_.strat_limits.market_trade_volume_participation.applicable_period_seconds
        executor_check_snapshot_list: List[ExecutorCheckSnapshot] = \
            self.trading_link.strat_manager_service_web_client.get_executor_check_snapshot_query_client(
                [symbol, side, applicable_period_seconds])

        executor_check_snapshot = None
        if executor_check_snapshot_list:  # has at least 1 element
            if len(executor_check_snapshot_list) == 1:
                executor_check_snapshot = executor_check_snapshot_list[0]
        if executor_check_snapshot is None:
            logging.error(f"Could not get executor_check_snapshot for symbol {symbol} and side {side}")
            return False

        portfolio_limits: PortfolioLimitsBaseModel
        portfolio_limits_tuple = self.trading_data_manager.trading_cache.get_portfolio_limits()
        if portfolio_limits_tuple and portfolio_limits_tuple[0] is not None:
            portfolio_limits = portfolio_limits_tuple[0]
            return self._check_portfolio_limits(executor_check_snapshot, portfolio_limits)
        else:
            logging.error(f"check_portfolio_limits blocked generated order, portfolio limits not found!")
            return False  # unable to proceed - not enough data to continue further - return

    def _check_portfolio_limits(self, executor_check_snapshot: ExecutorCheckSnapshot,
                                portfolio_limits: PortfolioLimitsBaseModel) -> bool:
        checks_passed = True
        if executor_check_snapshot.rolling_new_order_count > \
                portfolio_limits.rolling_max_order_count.max_rolling_tx_count:
            logging.error(f"blocked generated order, breaches max_rolling_order_count limit, expected less than: "
                          f"{portfolio_limits.rolling_max_order_count.max_rolling_tx_count}, found: "
                          f"{executor_check_snapshot.rolling_new_order_count} ")
            checks_passed = False
        return checks_passed

    def get_breach_threshold_px(self, top_of_book: TopOfBookBaseModel, order_limits: OrderLimitsBaseModel,
                                side: Side, system_symbol: str) -> float:
        aggressive_quote: QuoteOptional | None = None
        # TODO important - check and change reference px in cases where last px is not available
        if top_of_book.last_trade is None or math.isclose(top_of_book.last_trade.px, 0):
            # symbol_overview_tuple =  self.strat_cache.get_symbol_overview(top_of_book.symbol)
            logging.error(f"blocked generated order, symbol: {top_of_book.symbol}, side: {side} as "
                          f"top_of_book.last_trade.px is none or 0")
            return 0

        if side != Side.BUY and side != Side.SELL:
            logging.error(f"blocked generated unsupported side order, symbol: {system_symbol}, side: {side}")
            return 0  # 0 return blocks the order from going further

        px_by_max_level: float = 0
        aggressive_side = Side.BUY if side == Side.SELL else Side.SELL
        market_depths: List[MarketDepthBaseModel] = self.get_market_depths(system_symbol, aggressive_side)
        for market_depth in market_depths:
            if market_depth.position <= order_limits.max_px_levels:
                px_by_max_level = market_depth.px
                break
        if math.isclose(px_by_max_level, 0):
            logging.error(f"blocked generated order, symbol: {system_symbol}, side: {side}, unable to find valid px"
                          f" based on max_px_levels: {order_limits.max_px_levels} limit from available depths;;;"
                          f"depths: {[str(market_depth) for market_depth in market_depths]}")
            return 0

        if side == Side.BUY:
            aggressive_quote = top_of_book.ask_quote
            if not aggressive_quote:
                logging.error(f"blocked generated BUY order, symbol: {system_symbol}, side: {side} as aggressive_quote"
                              f" is found None")
                return 0  # 0 return blocks the order from going further
            max_px_by_deviation: float = top_of_book.last_trade.px + (
                    top_of_book.last_trade.px / 100 * order_limits.max_px_deviation)
            max_px_by_basis_point: float = aggressive_quote.px + (aggressive_quote.px / 100 * (
                    order_limits.max_basis_points / 100))
            return min(max_px_by_basis_point, max_px_by_deviation, px_by_max_level)

        else:
            aggressive_quote = top_of_book.bid_quote
            if not aggressive_quote:
                logging.error(f"blocked generated SELL order, symbol: {system_symbol}, side: {side} as aggressive_quote"
                              f" is found None")
                return 0  # 0 return blocks the order from going further
            min_px_by_deviation: float = top_of_book.last_trade.px - (
                    top_of_book.last_trade.px / 100 * order_limits.max_px_deviation)
            min_px_by_basis_point: float = aggressive_quote.px - (aggressive_quote.px / 100 * (
                    order_limits.max_basis_points / 100))
            return max(min_px_by_deviation, min_px_by_basis_point, px_by_max_level)

    def check_new_order(self, top_of_book: TopOfBookBaseModel, strat_brief: StratBriefBaseModel,
                        order_limits: OrderLimitsBaseModel, px: float, usd_px: float,
                        qty: int, side: Side, system_symbol: str, account: str, exchange: str) -> bool:
        pair_strat_tuple = self.strat_cache.get_pair_strat()
        checks_passed: bool = True

        order_usd_notional = usd_px * qty
        if order_limits.min_order_notional > order_usd_notional:
            logging.warning(f"blocked order_opportunity < min_order_notional limit: "
                            f"{order_usd_notional} < {order_limits.min_order_notional}")
            checks_passed = False
        if order_limits.max_order_notional < order_usd_notional:
            logging.error(f"blocked generated order, breaches max_order_notional limit, expected less than: "
                          f"{order_limits.max_order_notional}, found: {order_usd_notional} ")
            checks_passed = False
        if order_limits.max_order_qty < qty:
            logging.error(f"blocked generated order, breaches max_order_qty limit, expected less than: "
                          f"{order_limits.max_order_qty}, found: {qty} ")
            checks_passed = False

        if top_of_book:
            breach_px: float = self.get_breach_threshold_px(top_of_book, order_limits, side, system_symbol)
            if side == Side.BUY:
                if px > breach_px:
                    logging.error(f"blocked generated BUY order, order px: {px} > allowed max_px {breach_px}")
                    checks_passed = False
            elif side == Side.SELL:
                if px < breach_px:
                    logging.error(f"blocked generated SELL order, order px: {px} < allowed min_px {breach_px}")
                    checks_passed = False
            else:
                logging.error(f"blocked generated unsupported Side: {side} order, order px: {px}, qty: {qty} ")
        else:
            logging.error(f"blocked generated order, unable to conduct px checks: top_of_book is sent None for strat: "
                          f"{self.strat_cache}")
            checks_passed = False

        if not self.check_strat_limits(strat_brief, px, usd_px, qty, side, order_usd_notional, system_symbol):
            checks_passed = False  # true only if no prior check failed

        if pair_strat_tuple:
            pair_strat_, _ = pair_strat_tuple
            if pair_strat_ is not None:
                if not self.check_portfolio_limits(system_symbol, side, pair_strat_):
                    checks_passed = False
            else:
                logging.error(f"pair_strat is None for: [ {self.strat_cache} ]")
                checks_passed = False
        else:
            logging.error(f"pair_strat_tuple is None for: [ {self.strat_cache} ]")
            checks_passed = False

        # TODO LAZY Read config "order_pace_seconds" to pace orders (needed for testing - not a limit)
        if self.order_pase_seconds > 0:
            if self.last_order_timestamp.add(
                    seconds=self.order_pase_seconds) < DateTime.now():  # allow orders only after 2 min
                checks_passed = False

        return checks_passed

    def retry_init_strat_cache(self):
        while True:
            done = True  # done is left unchanged (True) implies all required data checks succeeded
            try:
                if not self.pair_strat_id:
                    self.pair_strat_id = get_pair_strat_key(self.strat_cache.get_pair_strat_())
                    done = False
                if not self.strat_cache.symbol_overviews:
                    self.update_symbol_overviews_from_http()
                    done = False
                if not self.strat_cache.get_top_of_books():
                    self.update_tobs_from_http()
                    done = False
                if not self.leg1_fx:
                    self.update_symbol_overviews_from_http()  # internally updates fx if available
                    done = False
                if not self.strat_cache.get_strat_brief():
                    self.update_strat_brief_from_http()
                    done = False
                if not self.trading_data_manager.trading_cache.get_portfolio_limits():
                    self.update_portfolio_limits_from_http()
                    done = False
                if done:
                    return
            except Exception as e:
                logging.error(f"strat retry-init failed! unable to proceed with strat: {self.pair_strat_id}, retrying!"
                              f";;;exception: {e}, strat_cache: {self.strat_cache}")

    def run(self):
        ret_val: int = -5000
        self.retry_init_strat_cache()

        while 1:
            try:
                ret_val = self.internal_run()
            except Exception as e:
                logging.error(f"Run returned with exception - sending again, exception: {e}")
            finally:
                if ret_val != 0:
                    logging.error(f"Error: Run returned, code: {ret_val} - sending again")
                elif ret_val == 1:
                    logging.info(f"explicit strat shutdown requested for: {self.pair_strat_id}, going down")
                    break
                else:
                    pair_strat, _ = self.strat_cache.get_pair_strat()
                    alert_brief: str = f"graceful shut down processing for strat: {self.pair_strat_id}"
                    alert_details: str = f"strat details: {self.strat_cache.get_pair_strat()}"
                    alert: Alert = create_alert(alert_brief, alert_details, None, Severity.Severity_INFO)
                    if pair_strat.strat_status.strat_state != StratState.StratState_DONE:
                        pair_strat_basemodel = PairStratBaseModel(_id=pair_strat.id)
                        pair_strat_basemodel.strat_status = pair_strat.strat_status
                        pair_strat_basemodel.strat_status.strat_state = StratState.StratState_DONE
                        pair_strat_basemodel.strat_status.strat_alerts = [alert]
                        self.trading_link.strat_manager_service_web_client.patch_pair_strat_client(pair_strat_basemodel)
                        logging.debug(f"Pair Strat with id: {self.pair_strat_id} Marked Done")
                        ret_val = 0
                    else:
                        logging.error(f"unexpected, Pair Strat with id {self.pair_strat_id} was already Marked Done")
                        ret_val = -4000  # helps find the error location
                    break

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.leg1_fx

    def _check_tob_n_place_non_systematic_order(self, new_order: NewOrderBaseModel, pair_strat: PairStratBaseModel,
                                                strat_brief: StratBriefBaseModel, order_limits: OrderLimitsBaseModel,
                                                top_of_books: List[TopOfBookBaseModel]) -> bool:
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        trade_tob: TopOfBookBaseModel
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        if leg1_tob is not None and \
                (self.strat_cache.leg1_trading_symbol == new_order.security.sec_id or
                 self.strat_cache.leg2_trading_symbol == new_order.security.sec_id):
            trade_tob = leg1_tob
        elif leg2_tob is not None and \
                (self.strat_cache.leg1_trading_symbol == new_order.security.sec_id or
                 self.strat_cache.leg2_trading_symbol == new_order.security.sec_id):
            trade_tob = leg2_tob
        else:
            logging.error(f"unable to send new_order: no matching leg in this strat: {new_order};;;"
                          f"strat: {self.strat_cache}, pair_strat: {pair_strat}")
            return False

        usd_px = self.get_usd_px(new_order.px, new_order.security.sec_id)
        order_placed: bool = self.place_new_order(trade_tob, strat_brief, order_limits, new_order.px, usd_px,
                                                  new_order.qty, new_order.side,
                                                  system_symbol=new_order.security.sec_id)
        return order_placed

    def get_leg1_leg2_ratio(self, leg1_px: float, leg2_px: float):
        if math.isclose(leg2_px, 0):
            return 0
        return leg1_px / leg2_px

    def _check_tob_and_place_order(self, pair_strat: PairStratBaseModel, strat_brief: StratBriefBaseModel,
                                   order_limits: OrderLimitsBaseModel, top_of_books: List[TopOfBookBaseModel]) -> bool:
        posted_leg1_notional: float = 0
        posted_leg2_notional: float = 0
        leg1_tob: TopOfBookBaseModel | None
        leg2_tob: TopOfBookBaseModel | None
        trade_tob: TopOfBookBaseModel
        leg1_tob, leg2_tob = self.extract_strat_specific_legs_from_tobs(pair_strat, top_of_books)

        order_placed: bool = False
        if leg1_tob is not None and self.strat_cache.leg1_trading_symbol is not None:
            if abs(self.leg1_notional) <= abs(self.leg2_notional):
                # process primary leg
                if pair_strat.pair_strat_params.strat_leg1.side == Side.BUY:  # execute aggressive buy
                    if not (leg1_tob.ask_quote.qty == 0 or math.isclose(leg1_tob.ask_quote.px, 0)):
                        ask_usd_px: float = self.get_usd_px(leg1_tob.ask_quote.px, leg1_tob.symbol)
                        order_placed = self.place_new_order(leg1_tob, strat_brief, order_limits, leg1_tob.ask_quote.px,
                                                            ask_usd_px, leg1_tob.ask_quote.qty,
                                                            Side.BUY, leg1_tob.symbol)
                        if order_placed:
                            posted_leg1_notional = leg1_tob.ask_quote.px * leg1_tob.ask_quote.qty
                    else:
                        logging.error(
                            f"0 value found in ask TOB - ignoring: px{leg1_tob.ask_quote.px}, "
                            f"qty: {leg1_tob.ask_quote.qty}")
                        return False
                else:  # execute aggressive sell
                    if not (leg1_tob.bid_quote.qty == 0 or math.isclose(leg1_tob.bid_quote.px, 0)):
                        bid_usd_px: float = self.get_usd_px(leg1_tob.bid_quote.px, leg1_tob.symbol)
                        order_placed = self.place_new_order(leg1_tob, strat_brief, order_limits, leg1_tob.bid_quote.px,
                                                            bid_usd_px, leg1_tob.bid_quote.qty,
                                                            Side.SELL, leg1_tob.symbol)
                        if order_placed:
                            posted_leg1_notional = leg1_tob.bid_quote.px * leg1_tob.bid_quote.qty
                    else:
                        logging.error(f"0 value found in TOB - ignoring: px {leg1_tob.bid_quote.px}"
                                      f", qty: {leg1_tob.bid_quote.qty}")
                        return False

        if leg2_tob is not None and self.strat_cache.leg2_trading_symbol is not None:
            if abs(self.leg2_notional) <= abs(self.leg1_notional):
                # process secondary leg
                if pair_strat.pair_strat_params.strat_leg2.side == Side.BUY:  # execute aggressive buy
                    if not (leg2_tob.ask_quote.qty == 0 or math.isclose(leg2_tob.ask_quote.px, 0)):
                        ask_usd_px: float = self.get_usd_px(leg2_tob.ask_quote.px, leg2_tob.symbol)
                        order_placed = self.place_new_order(leg2_tob, strat_brief, order_limits, leg2_tob.ask_quote.px,
                                                            ask_usd_px, leg2_tob.ask_quote.qty, Side.BUY,
                                                            leg2_tob.symbol)
                        if order_placed:
                            posted_leg2_notional = leg2_tob.ask_quote.px * leg2_tob.ask_quote.qty
                    else:
                        logging.error(
                            f"0 value found in ask TOB - ignoring: px{leg2_tob.ask_quote.px}, "
                            f"qty: {leg2_tob.ask_quote.qty}")
                        return False
                else:  # execute aggressive sell
                    if not (leg2_tob.bid_quote.qty == 0 or math.isclose(leg2_tob.bid_quote.px, 0)):
                        bid_usd_px: float = self.get_usd_px(leg2_tob.bid_quote.px, leg2_tob.symbol)
                        order_placed = self.place_new_order(leg2_tob, strat_brief, order_limits, leg2_tob.bid_quote.px,
                                                            bid_usd_px, leg2_tob.bid_quote.qty, Side.SELL,
                                                            leg2_tob.symbol)
                        if order_placed:
                            posted_leg2_notional = leg2_tob.bid_quote.px * leg2_tob.bid_quote.qty
                    else:
                        logging.error(
                            f"0 value found in TOB - ignoring: px {leg2_tob.bid_quote.px}"
                            f", qty: {leg2_tob.bid_quote.qty}")
                        return False
        if order_placed:
            self.last_order_timestamp = DateTime.now()
            self.leg1_notional += posted_leg1_notional
            self.leg2_notional += posted_leg2_notional
            logging.debug(f"strat-matched ToB: {[str(tob) for tob in top_of_books]}")
        return order_placed

    def _check_tob_and_place_order_test(self, pair_strat: PairStratBaseModel, strat_brief: StratBriefBaseModel,
                                        order_limits: OrderLimitsBaseModel,
                                        top_of_books: List[TopOfBookBaseModel]) -> bool:
        buy_top_of_book: TopOfBookBaseModel | None = None
        sell_top_of_book: TopOfBookBaseModel | None = None
        buy_symbol_prefix = "CB_Sec"
        sell_symbol_prefix = "EQT_Sec"
        order_placed: bool = False

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
                    err_str_ = f"top_of_book with unsupported test symbol received, tob: {top_of_book}"
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
                        err_str_ = f"top_of_book with unsupported test symbol received, tob: {top_of_book}"
                        logging.error(err_str_)
                        raise Exception(err_str_)
                    latest_update_date_time = top_of_book.last_update_date_time

        if buy_top_of_book is not None:
            if buy_top_of_book.bid_quote.last_update_date_time == \
                    self._top_of_books_update_date_time:
                if buy_top_of_book.bid_quote.px == 110:
                    px = 100
                    usd_px: float = self.get_usd_px(px, buy_top_of_book.symbol)
                    order_placed = self.place_new_order(buy_top_of_book, strat_brief, order_limits, px, usd_px, 90,
                                                    Side.BUY, buy_top_of_book.symbol)
        elif sell_top_of_book is not None:
            if sell_top_of_book.ask_quote.last_update_date_time == \
                    self._top_of_books_update_date_time:
                if sell_top_of_book.ask_quote.px == 120:
                    px = 110
                    usd_px: float = self.get_usd_px(px, sell_top_of_book.symbol)
                    order_placed = self.place_new_order(sell_top_of_book, strat_brief, order_limits, px, usd_px, 70,
                                                        Side.SELL, sell_top_of_book.symbol)
        else:
            err_str_ = "TOB updates could not find any updated buy or sell tob"
            logging.error(err_str_)
            raise Exception(err_str_)
        return order_placed

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
                logging.error(f"unable to get fx_symbol_overview for leg1_fx_symbol: "
                              f"{self.strat_cache.leg1_fx_symbol};;;strat_cache: {self.strat_cache}")
                return None

    def process_cxl_request(self):
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
                if unprocessed_cancel_orders:
                    return True
        # all else return false - no cancel_order to process
        return False

    def internal_run(self):
        while 1:
            self.strat_limit = None
            try:
                if self.strat_cache.stopped:
                    self.strat_cache.set_pair_strat(None)
                    return 1  # indicates explicit shutdown requested from server
                self.strat_cache.notify_semaphore.acquire()

                # 1. check if portfolio status has updated since we last checked
                portfolio_status: PortfolioStatusBaseModel | None = None
                portfolio_status_tuple = self.trading_data_manager.trading_cache.get_portfolio_status()
                if portfolio_status_tuple is None:
                    logging.warning(
                        "no portfolio status found yet - strat will not trigger until portfolio status arrives")
                    continue
                if portfolio_status_tuple is not None:
                    portfolio_status, self._portfolio_status_update_date_time = portfolio_status_tuple
                # else no update - do we need this processed again ?

                # 2. get pair-strat: no checking if it's updated since last checked (required for TOB extraction)
                pair_strat_tuple = self.strat_cache.get_pair_strat()
                if pair_strat_tuple is not None:
                    pair_strat, pair_strat_update_date_time = pair_strat_tuple
                    # If strat status not active, don't act, just return
                    if pair_strat.strat_status.strat_state != StratState.StratState_ACTIVE:
                        continue
                    else:
                        self.strat_limit = pair_strat.strat_limits
                else:
                    logging.error(f"pair_strat_tuple is None for: {self.strat_cache}")
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
                    if order_limits:
                        if strat_brief.pair_sell_side_trading_brief.consumable_notional < order_limits.min_order_notional:
                            # this leg of strat is done
                            if strat_brief.pair_buy_side_trading_brief.consumable_notional < order_limits.min_order_notional:
                                # both sides are done - graceful shutdown the strat
                                return 0
                            # else not required, more notional to consume on buy leg
                        # else not required, more notional to consume on sell leg
                    else:
                        logging.error(f"order_limits not found for strat: {self.strat_cache}, can't proceed")
                        continue  # go next run - we don't stop processing for one faulty strat_cache
                else:
                    logging.error(f"order_limits_tuple not found for strat: {self.strat_cache}, can't proceed")
                    continue  # go next run - we don't stop processing for one faulty strat_cache

                # 4. get top_of_book (new or old to be checked by respective strat based on strat requirement)
                top_of_book_and_date_tuple = self.strat_cache.get_top_of_books()

                if top_of_book_and_date_tuple is not None:
                    top_of_books: List[TopOfBookBaseModel]
                    top_of_books, self._top_of_books_update_date_time = top_of_book_and_date_tuple
                    if top_of_books is not None and len(top_of_books) == 2:
                        if top_of_books[0] is not None and top_of_books[1] is not None:
                            pass
                        else:
                            logging.error(f"strats need both sides of TOB to be present, found  0 or 1 - triggering "
                                          f"force update;;;tob found: {top_of_books[0]}, {top_of_books[1]}")
                            self.update_tobs_from_http()
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
                    logging.error(f"unexpected top_of_book_and_date_tuple is None for strat: {self.strat_cache}")
                    continue  # go next run - we don't stop processing for one faulty tob update

                # 5. ensure leg1_fx is present - otherwise don't proceed - retry later
                if not self.get_leg1_fx():
                    logging.error(f"USD fx rate not found for strat, unable to proceed, fx symbol: "
                                  f"{self.strat_cache.leg1_fx_symbol}, we'll retry in next attempt")
                    continue

                # 6. If any manual new_order requested: apply risk checks (maybe no strat param checks?) & send out
                new_orders_and_date_tuple = self.strat_cache.get_new_orders(self._new_orders_update_date_time)
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

                # If kill switch is enabled - don't act, just return
                if portfolio_status.kill_switch:
                    continue

                if not self.is_test_run:
                    self._check_tob_and_place_order(pair_strat, strat_brief, order_limits, top_of_books)
                else:
                    self._check_tob_and_place_order_test(pair_strat, strat_brief, order_limits, top_of_books)
                continue  # all good - go next run
            except Exception as e:
                logging.error(f"Run returned with exception: {e};;;inspect.trace()[-1][3]: {inspect.trace()[-1][3]} "
                              f"sys.exc_info: {str(sys.exc_info())}")
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
