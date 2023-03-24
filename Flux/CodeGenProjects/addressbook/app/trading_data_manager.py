import logging
from threading import Thread
from typing import Callable

from FluxPythonUtils.scripts.utility_functions import get_host_port_from_env
from FluxPythonUtils.scripts.ws_reader import WSReader
from trading_cache import *
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import \
    is_ongoing_pair_strat
from Flux.CodeGenProjects.addressbook.app.trading_link import TradingLinkBase, get_trading_link

trading_link: TradingLinkBase = get_trading_link()

host, port = get_host_port_from_env()


class TradingDataManager:
    def __init__(self, executor_trigger_method: Callable):
        trading_base_url: str = f"ws://{host}:{port}/addressbook"
        market_data_base_url: str = f"ws://{host}:8040/market_data"
        cpp_ws_url: str = f"ws://{host}:8083/"
        self.trading_cache: TradingCache = TradingCache()

        self.top_of_book_ws_cont = WSReader(f"{market_data_base_url}/get-all-top_of_book-ws", TopOfBookBaseModel,
                                            TopOfBookBaseModelList, self.handle_top_of_book_ws)

        self.symbol_overview_ws_cont = WSReader(f"{market_data_base_url}/get-all-symbol_overview-ws",
                                                SymbolOverviewBaseModel,
                                                SymbolOverviewBaseModelList, self.handle_symbol_overview_ws)

        self.pair_strat_ws_cont = WSReader(f"{trading_base_url}/get-all-pair_strat-ws", PairStratBaseModel,
                                           PairStratBaseModelList, self.handle_pair_strat_ws, False)

        self.portfolio_status_ws_cont = WSReader(f"{trading_base_url}/get-all-portfolio_status-ws",
                                                 PortfolioStatusBaseModel,
                                                 PortfolioStatusBaseModelList, self.handle_portfolio_status_ws, False)

        self.portfolio_limits_ws_cont = WSReader(f"{trading_base_url}/get-all-portfolio_limits-ws",
                                                 PortfolioLimitsBaseModel,
                                                 PortfolioLimitsBaseModelList, self.handle_portfolio_limits_ws, False)
        self.order_limits_ws_cont = WSReader(f"{trading_base_url}/get-all-order_limits-ws", OrderLimitsBaseModel,
                                             OrderLimitsBaseModelList, self.handle_order_limits_ws, False)
        self.order_journal_ws_cont = WSReader(f"{trading_base_url}/get-all-order_journal-ws", OrderJournalBaseModel,
                                              OrderJournalBaseModelList, self.handle_order_journal_ws, False)
        self.fill_journal_ws_cont = WSReader(f"{trading_base_url}/get-all-fills_journal-ws", FillsJournalBaseModel,
                                             FillsJournalBaseModelList, self.handle_fill_journal_ws, False)
        self.strat_brief_ws_cont = WSReader(f"{trading_base_url}/get-all-strat_brief-ws", StratBriefBaseModel,
                                            StratBriefBaseModelList, self.handle_strat_brief_ws, False)
        self.cancel_order_ws_cont = WSReader(f"{trading_base_url}/get-all-cancel_order-ws", CancelOrderBaseModel,
                                             CancelOrderBaseModelList, self.handle_cancel_order_ws, True)
        self.new_order_ws_cont = WSReader(f"{trading_base_url}/get-all-new_order-ws", NewOrderBaseModel,
                                          NewOrderBaseModelList, self.handle_new_order_ws, True)
        # self.market_depth_ws_const = WSReader(cpp_ws_url, MarketDepthBaseModel, MarketDepthBaseModelList,
        #                                       self.handle_market_depth_ws, False)

        self.executor_trigger_method = executor_trigger_method
        self.strat_thread_dict: dict[str, Tuple['StratExecutor', Thread]] = dict()
        self.ws_thread = Thread(target=WSReader.start, daemon=True).start()

    def __del__(self):
        """
        ideally create join-able WS thread; set exit in WS static var & upon exit state detection, WS thread can
        cancel pending tasks, subsequently return to join. This helps terminate the program gracefully
        """

    # define callbacks for types you expect from ws as updates
    def handle_portfolio_status_ws(self, portfolio_status_: PortfolioStatusBaseModel):
        # handle kill switch here (in portfolio status handler directly)
        with self.portfolio_status_ws_cont.single_obj_lock:
            portfolio_status_tuple = self.trading_cache.get_portfolio_status()
            if portfolio_status_tuple is None or portfolio_status_tuple[0] is None:
                self.trading_cache.set_portfolio_status(portfolio_status_)
                if portfolio_status_.kill_switch:
                    trading_link.trigger_kill_switch()
                if self.portfolio_status_ws_cont.notify:
                    StratCache.notify_all()
                logging.info(f"Added portfolio status with id: {portfolio_status_.id}")
            else:
                portfolio_status, _ = portfolio_status_tuple
                if portfolio_status.id == portfolio_status_.id:
                    self.trading_cache.set_portfolio_status(portfolio_status_)
                    if self.portfolio_status_ws_cont.notify:
                        StratCache.notify_all()
                    logging.debug(f"updated portfolio status with id: {portfolio_status_.id}")
                else:
                    logging.error(f"received non unique portfolio_status, current id: "
                                  f"{portfolio_status.id} found: {portfolio_status_.id};;;"
                                  f"current portfolio_status: {portfolio_status}, "
                                  f"found portfolio_status: {portfolio_status_} ")

    def handle_portfolio_limits_ws(self, portfolio_limits_: PortfolioLimitsBaseModel):
        with self.portfolio_limits_ws_cont.single_obj_lock:
            portfolio_limits_tuple = self.trading_cache.get_portfolio_limits()
            if portfolio_limits_tuple is None or portfolio_limits_tuple[0] is None:
                self.trading_cache.set_portfolio_limits(portfolio_limits_)
                if self.portfolio_limits_ws_cont.notify:
                    StratCache.notify_all()
                logging.info(f"Added portfolio status with id: {portfolio_limits_.id}")
            else:
                portfolio_limits, _ = self.trading_cache.get_portfolio_limits()
                if portfolio_limits.id == portfolio_limits_.id:
                    self.trading_cache.set_portfolio_limits(portfolio_limits_)
                    if self.portfolio_limits_ws_cont.notify:
                        StratCache.notify_all()
                    logging.debug(f"updated portfolio limits with id: {portfolio_limits_.id}")
                else:
                    logging.error(f"received non unique portfolio_limits, current id: "
                                  f"{portfolio_limits.id} found: {portfolio_limits_.id};;;"
                                  f"current portfolio_limits: {portfolio_limits}, "
                                  f"found portfolio_limits: {portfolio_limits_} ")

    def handle_order_limits_ws(self, order_limits_: OrderLimitsBaseModel):
        with self.order_limits_ws_cont.single_obj_lock:
            order_limits_tuple = self.trading_cache.get_order_limits()
            if order_limits_tuple is None or order_limits_tuple[0] is None:
                self.trading_cache.set_order_limits(order_limits_)
                if self.order_limits_ws_cont.notify:
                    StratCache.notify_all()
                logging.info(f"Added order limits with id: {order_limits_.id}")
            else:
                order_limits, _ = self.trading_cache.get_order_limits()
                if order_limits.id == order_limits_.id:
                    self.trading_cache.set_order_limits(order_limits_)
                    if self.order_limits_ws_cont.notify:
                        StratCache.notify_all()
                    logging.debug(f"updated order limits with id: {order_limits_.id}")
                else:
                    logging.error(f"received non unique order_limits, current id: {order_limits.id} "
                                  f"found: {order_limits_.id};;;current order_limits: {order_limits}"
                                  f", found order_limits: {order_limits_} ")

    def handle_pair_strat_ws(self, pair_strat_: PairStratBaseModel):
        key_leg_1, key_leg_2 = StratCache.get_key_from_pair_strat(pair_strat_)
        if is_ongoing_pair_strat(pair_strat_):
            # only pair strat should use guaranteed_get_by_key as it is the only handler that removes the strat cache
            strat_cache: StratCache = StratCache.guaranteed_get_by_key(key_leg_1, key_leg_2)
            with strat_cache.re_ent_lock:
                pair_strat_tuple = strat_cache.get_pair_strat()
                cached_pair_strat = None
                if pair_strat_tuple is not None:
                    cached_pair_strat, _ = strat_cache.get_pair_strat()
                if cached_pair_strat is None:
                    # this is a new pair strat for processing, start its own thread with new strat executor object
                    strat_cache.set_pair_strat(pair_strat_)
                    strat_cache.stopped = False
                    strat_executor, strat_executor_thread = self.executor_trigger_method(self, strat_cache)
                    # update strat key to python processing thread
                    if key_leg_1 in self.strat_thread_dict:
                        logging.error(f"Unexpected: unable to proceed proceed with pair_strat key: {key_leg_1};;;"
                                      f"existing entry found in strat_thread_dict: "
                                      f"{self.strat_thread_dict[key_leg_1]}, new requested: {pair_strat_}")
                    self.strat_thread_dict[key_leg_1] = (strat_executor, strat_executor_thread)
                else:
                    strat_cache.set_pair_strat(pair_strat_)
            if self.strat_brief_ws_cont.notify:
                strat_cache.notify_semaphore.release()
            logging.debug(f"Updated strat_brief cache for key: {key_leg_1} ;;; strat_brief: {pair_strat_}")
        else:
            strat_cache: StratCache = StratCache.get(key_leg_1)
            if strat_cache is not None:
                # remove if this pair strat is in our cache - it's no more ongoing
                with strat_cache.re_ent_lock:
                    strat_cache.stopped = True  # demon thread will tear down itself
                    # strat_cache.set_pair_strat(None)  # avoids crash if strat thread is using strat_cache
                    # enables future re-activation, stops any processing until then
                    self.strat_thread_dict.pop(key_leg_1)
                    # don't join on trading thread - let the demon self shutdown
                    strat_cache.notify_semaphore.release()
                logging.warning(f"handle_pair_strat_ws: removed cache entry of non ongoing pair strat from trading:"
                                f" {pair_strat_}")
            # else not required - non-ongoing pair strat is not to exist in cache

    def handle_strat_brief_ws(self, strat_brief_: StratBriefBaseModel):
        if strat_brief_.pair_buy_side_trading_brief and strat_brief_.pair_sell_side_trading_brief:
            key1, key2 = StratCache.get_key_from_strat_brief(strat_brief_)
            strat_cache: StratCache = StratCache.get(key1, key2)
            if strat_cache is not None:
                with strat_cache.re_ent_lock:
                    strat_cache.set_strat_brief(strat_brief_)
                cached_pair_strat_tuple = strat_cache.get_pair_strat()
                if self.strat_brief_ws_cont.notify and cached_pair_strat_tuple is not None and \
                        cached_pair_strat_tuple[0] is not None:
                    cached_pair_strat, _ = cached_pair_strat_tuple
                    strat_cache.notify_semaphore.release()
                elif (cached_pair_strat_tuple is None) or (cached_pair_strat_tuple[0] is None):
                    logging.warning(f"ignoring: no ongoing pair strat matches this strat_brief: {strat_brief_}")
                # else not required - strat does not need this update notification
                logging.debug(f"Updated strat_brief cache for key: {key1} {key2} ;;; strat_brief: {strat_brief_}")
            else:
                logging.debug("either a non-ongoing strat-brief or one before corresponding active pair_strat: "
                              "we discard this and expect algo to get snapshot with explicit web query - maybe we wire "
                              f"explicit web query in ongoing pair-strat notification;;;strat_brief: {strat_brief_}")
        else:
            logging.error(f"ignoring strat brief update - missing required pair_buy_side_trading_brief or pair_sell_"
                          f"side_trading_brief;;;strat_brief: {strat_brief_}")

    def handle_fill_journal_ws(self, fill_journal_: FillsJournalBaseModel):
        key, symbol = StratCache.get_key_n_symbol_from_fill_journal(fill_journal_)
        if key is None or symbol is None:
            logging.error(f"error: no ongoing pair strat matches this fill_journal_: {fill_journal_}")
            return
        strat_cache: StratCache = StratCache.get(key)
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_fills_journal(fill_journal_)
            cached_pair_strat: PairStratBaseModel
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if symbol == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
                strat_cache.set_has_unack_leg1(False)
            elif symbol == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
                strat_cache.set_has_unack_leg2(False)
            else:
                logging.error(f"unexpected: fills general with non-matching symbol found in pre-matched strat-cache "
                              f"with key: {key}, fill journal symbol: {symbol}")
            if self.fill_journal_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.error(f"error: no ongoing pair strat matches this fill_journal_: {fill_journal_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated fill_journal cache for key: {key} ;;; fill_journal: {fill_journal_}")
        else:
            logging.error(f"error: no ongoing pair strat matches received fill journal: {fill_journal_}")

    def handle_order_journal_ws(self, order_journal_: OrderJournalBaseModel):
        key = StratCache.get_key_from_order_journal(order_journal_)
        strat_cache: StratCache = StratCache.get(key)
        is_unack: bool = False
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_order_journal(order_journal_)
                if order_journal_.order_event in [OrderEventType.OE_NEW, OrderEventType.OE_CXL]:
                    is_unack = True
                    if order_journal_.order_event == OrderEventType.OE_NEW:
                        StratCache.order_id_to_symbol_side_tuple_dict[order_journal_.order.order_id] = \
                            (order_journal_.order.security.sec_id, order_journal_.order.side)
            cached_pair_strat: PairStratBaseModel
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
                strat_cache.set_has_unack_leg1(is_unack)
            elif order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
                strat_cache.set_has_unack_leg2(is_unack)
            else:
                logging.error(f"unexpected: order general with non-matching symbol found in pre-matched strat-cache "
                              f"with key: {key}, order journal symbol: {order_journal_.order.security.sec_id}")
            if self.order_journal_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.error(f"error: no ongoing pair strat matches this order_journal_: {order_journal_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated order_journal cache for key: {key} ;;; order_journal: {order_journal_}")
        else:
            logging.error(f"error: no ongoing pair strat matches received order journal: {order_journal_}")

    def handle_cancel_order_ws(self, cancel_order_: CancelOrderBaseModel):
        key = StratCache.get_key_from_cancel_order(cancel_order_)
        strat_cache: StratCache = StratCache.get(key)
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_cancel_order(cancel_order_)
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if self.cancel_order_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.error(f"error: no ongoing pair strat matches this cancel_order: {cancel_order_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated cancel_order cache for key: {key} ;;; cancel_order: {cancel_order_}")
        else:
            logging.error(f"error: no ongoing pair strat matches this order_journal_: {cancel_order_}")

    def handle_new_order_ws(self, new_order_: NewOrderBaseModel):
        key = StratCache.get_key_from_new_order(new_order_)
        strat_cache: StratCache = StratCache.get(key)
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_new_order(new_order_)
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if self.new_order_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.error(f"error: no ongoing pair strat matches this order_journal_: {new_order_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated new_order cache for key: {key} ;;; order_journal: {new_order_}")
        else:
            logging.error(f"error: no ongoing pair strat matches this order_journal_: {new_order_}")

    def handle_symbol_overview_ws(self, symbol_overview_: SymbolOverviewBaseModel):
        key1, key2 = StratCache.get_key_from_symbol_overview(symbol_overview_)
        strat_cache1: StratCache = StratCache.get(key1)
        strat_cache2: StratCache = StratCache.get(key2)
        updated: bool = False
        if strat_cache1 is not None:
            with strat_cache1.re_ent_lock:
                strat_cache1.set_symbol_overview(symbol_overview_)
            if self.symbol_overview_ws_cont.notify:
                strat_cache1.notify_semaphore.release()
            updated = True
            # else not required - strat does not need this update notification
        if strat_cache2 is not None:
            with strat_cache2.re_ent_lock:
                strat_cache2.set_symbol_overview(symbol_overview_)
            if self.symbol_overview_ws_cont.notify:
                strat_cache2.notify_semaphore.release()
            updated = True
            # else not required - strat does not need this update notification
        if updated:
            logging.debug(f"Updated symbol_overview cache for keys: {key1}, {key2};;;detail: {symbol_overview_}")
        else:
            logging.debug(f"no matching strat: for symbol_overview keys: {key1}, {key2};;;detail: {symbol_overview_}")

    def handle_top_of_book_ws(self, top_of_book_: TopOfBookBaseModel):
        key1, key2 = StratCache.get_key_from_top_of_book(top_of_book_)
        strat_cache1: StratCache = StratCache.get(key1)
        strat_cache2: StratCache = StratCache.get(key2)
        updated: bool = False
        if strat_cache1 is not None:
            with strat_cache1.re_ent_lock:
                strat_cache1.set_top_of_book(top_of_book_)
            if self.top_of_book_ws_cont.notify:
                strat_cache1.notify_semaphore.release()
            updated = True
            # else not required - strat does not need this update notification
        if strat_cache2 is not None:
            with strat_cache2.re_ent_lock:
                strat_cache2.set_top_of_book(top_of_book_)
            if self.top_of_book_ws_cont.notify:
                strat_cache2.notify_semaphore.release()
            updated = True
            # else not required - strat does not need this update notification
        if updated:
            logging.debug(f"Updated top_of_book cache for keys: {key1}, {key2};;;TOB: {top_of_book_}")
        else:
            logging.debug(f"no matching strat: for TOB keys: {key1}, {key2};;;TOB: {top_of_book_}")

    def handle_market_depth_ws(self, market_depth_: MarketDepthBaseModel):
        print(market_depth_)
