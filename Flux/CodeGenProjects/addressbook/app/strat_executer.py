import logging
import os
import time
from pathlib import PurePath
from threading import Thread

import pytz

os.environ["DBType"] = "beanie"
PROJECT_DATA_DIR = PurePath(__file__).parent.parent / 'data'

from FluxPythonUtils.scripts.utility_functions import load_yaml_configurations
from Flux.CodeGenProjects.addressbook.app.trading_data_manager import TradingDataManager
from Flux.CodeGenProjects.addressbook.app.strat_cache import *
from Flux.CodeGenProjects.addressbook.app.trade_simulator import TradeSimulator
from Flux.CodeGenProjects.market_data.generated.market_data_service_model_imports import *


class StratExecutor:
    @staticmethod
    def executor_trigger(trading_data_manager: TradingDataManager, strat_cache: StratCache):
        strat_executor: StratExecutor = StratExecutor(trading_data_manager, strat_cache)
        strat_executor_thread = Thread(target=strat_executor.run, daemon=True).start()
        return strat_executor, strat_executor_thread

    """ 1 instance = 1 thread = 1 pair strat"""

    def __init__(self, trading_data_manager: TradingDataManager, strat_cache: StratCache):
        config_file_path: PurePath = PROJECT_DATA_DIR / "config.yaml"
        config_dict = load_yaml_configurations(str(config_file_path))
        self.trading_data_manager: TradingDataManager = trading_data_manager
        self.strat_cache: StratCache = strat_cache

        self._portfolio_status_update_date_time: DateTime | None = None
        self._pair_strat_update_date_time: DateTime | None = None
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

        # TODO FIX THIS
        self.buy_sec_id: str = config_dict.get("buy_sec_id")
        self.sell_sec_id: str = config_dict.get("sell_sec_id")
        self.underlying_acc: str = config_dict.get("underlying_account")
        self.market_depth_lvl: int = config_dict.get("market_depth_lvl")

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
        market_depth_objs = TradeSimulator.market_data_service_web_client.get_market_depth_from_index_client(symbol)
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

    def check_new_order_limits(self, new_order) -> bool:
        return True

    def run(self):
        while 1:
            if self.strat_cache.stopped:
                break
            self.strat_cache.notify_semaphore.acquire()

            # 1. check if portfolio status has updated since we last checked
            portfolio_status_tuple = self.trading_data_manager.trading_cache.get_portfolio_status()
            if portfolio_status_tuple is not None:
                portfolio_status, self._portfolio_status_update_date_time = portfolio_status_tuple
                # If kill switch is enabled - don't act, just return
                if portfolio_status.kill_switch:
                    continue
            # else no update - do we need this processed again ?

            # 2. check if pair-strat has updated since we last checked
            pair_strat_tuple = self.strat_cache.get_pair_strat(self._pair_strat_update_date_time)
            if pair_strat_tuple is not None:
                pair_strat, self._pair_strat_update_date_time = pair_strat_tuple
                # If strat status not active, don't act, just return
                if pair_strat.strat_status.strat_state != StratState.StratState_ACTIVE:
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
                        TradeSimulator.place_cxl_order(cancel_order.order_id, cancel_order.side,
                                                       cancel_order.security.sec_id, "dummy_account")
            # else no cancel order to process

            # 4. check if any new order is requested: apply all risk checks, no strat param checks and send out
            new_orders_and_date_tuple = self.strat_cache.get_new_orders(self._new_orders_update_date_time)
            if new_orders_and_date_tuple is not None:
                new_orders, self._new_orders_update_date_time = new_orders_and_date_tuple
                if new_orders is not None:
                    final_slice = len(new_orders)
                    unprocessed_new_orders: List[NewOrderBaseModel] = new_orders[self._new_orders_processed_slice:final_slice]
                    self._new_orders_processed_slice = final_slice
                    for new_order in unprocessed_new_orders:
                        if self.check_new_order_limits(new_order):
                            TradeSimulator.place_new_order(new_order.px, new_order.qty, new_order.side,
                                                           new_order.security.sec_id, "dummy_account")
                        else:
                            logging.error(f"order check failed - unable to send new order: {new_order}")
            # else no new order to process

            # 5. check if top of book is updated
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
                    # TODO == won't work - there are 2 ToB objects - we may have processed the newer - older will be
                    #  different but less
                    if buy_top_of_book.bid_quote.last_update_date_time.replace(tzinfo=pytz.UTC) == \
                            self._top_of_books_update_date_time:
                        if buy_top_of_book.bid_quote.px == 25:
                            order_id = TradeSimulator.place_new_order(100, 90, Side.BUY, "CB_Sec_1", "Acc1")

                    if sell_top_of_book.ask_quote.last_update_date_time.replace(tzinfo=pytz.UTC) == \
                            self._top_of_books_update_date_time:
                        if sell_top_of_book.ask_quote.px == 25:
                            order_id = TradeSimulator.place_new_order(110, 70, Side.SELL, "EQT_Sec_1", "Acc1")

            else:
                continue  # no update to process
        # we are outside while 1 (strat processing loop) - shut down this strat processing
        pair_strat, _ = self.strat_cache.get_pair_strat()
        logging.critical(f"shutting down this strat processing for strat: "
                         f"{pair_strat.pair_strat_params.strat_leg1.sec.sec_id}_"
                         f"{pair_strat.pair_strat_params.strat_leg2.sec.sec_id}_"
                         f"{pair_strat.id};;;strat: {self.strat_cache.get_pair_strat()}")
        return
        # # TODO This moves to the trade notify receiver thread
        # if order_journal_.order_event == OrderEventType.OE_NEW:
        #     TradeSimulator.ack_order_n_fill(order_journal_.order.px, order_journal_.order.qty,
        #     order_journal_.order.order_id,
        #                                     order_journal_.order.side, order_journal_.order.security.sec_id,
        #                                     order_journal_.order.underlying_account)
        # elif order_journal_.order_event == OrderEventType.OE_CXL:
        #     TradeSimulator.place_cxl_order(order_journal_.order.px, order_journal_.order.qty,
        #     order_journal_.order.order_id,
        #                                    order_journal_.order.side, order_journal_.order.security.sec_id,
        #                                    order_journal_.order.underlying_account)

        # wait for websockets to set models in data-members
        # time.sleep(5)

        # order_count = 1
        # buying_stopped = False
        # selling_stopped = False
        # while True:
        #     # Buying if allowed
        #     market_depth_for_buy = self.get_px_qty_from_depth(2, self.buy_sec_id, Side.BUY)
        #     if order_count == 1:
        #         TradeSimulator.place_new_order(market_depth_for_buy.px, market_depth_for_buy.qty, f"O{order_count}",
        #                                        Side.BUY, self.buy_sec_id, self.underlying_acc)
        #         order_count += 1
        #     else:
        #         if not buying_stopped:
        #             if self.check_order_eligibility(Side.BUY, market_depth_for_buy.px * market_depth_for_buy.qty):
        #                 TradeSimulator.place_new_order(market_depth_for_buy.px, market_depth_for_buy.qty,
        #                                           f"O{order_count}", Side.BUY,
        #                                                self.buy_sec_id, self.underlying_acc)
        #                 order_count += 1
        #             else:
        #                 print("Stopping Buying, reached threshold")
        #                 buying_stopped = True
        #
        #     time.sleep(10)
        #
        #     # Selling if allowed
        #     market_depth_for_sell = self.get_px_qty_from_depth(2, self.sell_sec_id, Side.SELL)
        #     if order_count == 2:
        #         TradeSimulator.place_new_order(market_depth_for_sell.px, market_depth_for_sell.qty, f"O{order_count}",
        #                                        Side.SELL, self.sell_sec_id, self.underlying_acc)
        #         order_count += 1
        #     else:
        #         if not selling_stopped:
        #             if self.check_order_eligibility(Side.SELL, market_depth_for_sell.px * market_depth_for_sell.qty):
        #                 TradeSimulator.place_new_order(market_depth_for_sell.px, market_depth_for_sell.qty,
        #                                           f"O{order_count}", Side.SELL,
        #                                                self.sell_sec_id, self.underlying_acc)
        #                 order_count += 1
        #             else:
        #                 print("Stopping Selling, reached threshold")
        #                 selling_stopped = True
        #
        #     time.sleep(10)
        #
        #     if buying_stopped and selling_stopped:
        #         break


if __name__ == "__main__":
    trading_data_manager = TradingDataManager(StratExecutor.executor_trigger)
    while 1:
        time.sleep(10)
