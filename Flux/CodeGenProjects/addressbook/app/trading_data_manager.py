from threading import Thread
from typing import Callable

from FluxPythonUtils.scripts.ws_reader import WSReader
from trading_cache import *
from Flux.CodeGenProjects.addressbook.app.addressbook_service_helper import \
    is_ongoing_pair_strat
from Flux.CodeGenProjects.addressbook.app.trading_link import TradingLinkBase, get_trading_link
trading_link: TradingLinkBase = get_trading_link()


class TradingDataManager:
    def __init__(self, executor_trigger_method: Callable):
        trading_base_url: str = "ws://127.0.0.1:8020/addressbook"
        market_data_base_url: str = "ws://127.0.0.1:8040/market_data"
        cpp_ws_url: str = "ws://127.0.0.1:8083/"
        self.trading_cache: TradingCache = TradingCache()

        self.top_of_book_ws_cont = WSReader(f"{market_data_base_url}/get-all-top_of_book-ws", TopOfBookBaseModel,
                                            TopOfBookBaseModelList, self.handle_top_of_book_ws)

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
        self.strat_brief_ws_cont = WSReader(f"{trading_base_url}/get-all-strat_brief-ws", StratBriefBaseModel,
                                            StratBriefBaseModelList, self.handle_strat_brief_ws, False)
        self.cancel_order_ws_cont = WSReader(f"{trading_base_url}/get-all-cancel_order-ws", CancelOrderBaseModel,
                                             CancelOrderBaseModelList, self.handle_cancel_order_ws, True)
        self.new_order_ws_cont = WSReader(f"{trading_base_url}/get-all-new_order-ws", NewOrderBaseModel,
                                          NewOrderBaseModelList, self.handle_new_order_ws, True)
        self.market_depth_ws_const = WSReader(cpp_ws_url, MarketDepthBaseModel, MarketDepthBaseModelList,
                                              self.handle_market_depth_ws, False)

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
        # handle kill switch in portfolio status handler directly
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
                portfolio_status, _ = self.trading_cache.get_portfolio_status()
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
        # handle kill switch in portfolio limits handler directly
        with self.portfolio_limits_ws_cont.single_obj_lock:
            portfolio_limits_tuple = self.trading_cache.get_portfolio_limits()
            if portfolio_limits_tuple is None or portfolio_limits_tuple[0] is None:
                self.trading_cache.set_portfolio_limits(portfolio_limits_)
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

    def handle_strat_brief_ws(self, strat_brief_: StratBriefBaseModel):
        key1, key2 = StratCache.get_key_from_strat_brief(strat_brief_)
        strat_cache: StratCache = StratCache.get(key1, key2)
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_strat_brief(strat_brief_)
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if self.strat_brief_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.warning(f"ignoring: no ongoing pair strat matches this strat_brief: {strat_brief_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated strat_brief cache for key: {key1} {key2} ;;; strat_brief: {strat_brief_}")
        else:
            logging.debug("either a non-ongoing strat-brief or one before corresponding active pair_strat: "
                          "we discard this and expect algo to get snapshot with explicit web query - maybe we wire "
                          f"explicit web query in ongoing pair-strat notification;;;strat_brief: {strat_brief_}")

    def handle_order_limits_ws(self, order_limits_: OrderLimitsBaseModel):
        with self.order_limits_ws_cont.single_obj_lock:
            order_limits_tuple = self.trading_cache.get_order_limits()
            if order_limits_tuple is None or order_limits_tuple[0] is None:
                self.trading_cache.set_order_limits(order_limits_)
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

    def handle_order_journal_ws(self, order_journal_: OrderJournalBaseModel):  # NOQA
        key = StratCache.get_key_from_order_journal(order_journal_)
        strat_cache: StratCache = StratCache.get(key)
        if strat_cache is not None:
            with strat_cache.re_ent_lock:
                strat_cache.set_order_journal(order_journal_)
            cached_pair_strat, _ = strat_cache.get_pair_strat()
            if self.order_journal_ws_cont.notify and cached_pair_strat is not None:
                strat_cache.notify_semaphore.release()
            elif cached_pair_strat is None:
                logging.error(f"error: no ongoing pair strat matches this order_journal_: {order_journal_}")
            # else not required - strat does not need this update notification
            logging.debug(f"Updated order_journal cache for key: {key} ;;; order_journal: {order_journal_}")
        else:
            logging.error(f"error: no ongoing pair strat matches received order journal: {order_journal_}")
    def handle_cancel_order_ws(self, cancel_order_: CancelOrderBaseModel):  # NOQA
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

    def handle_new_order_ws(self, new_order_: NewOrderBaseModel):  # NOQA
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
            logging.debug(f"Updated top_of_book cache for keys: {key1}, {key2} ;;; top_of_book: {top_of_book_}")
        else:
            logging.debug(f"no matching strat - ignoring TOB for keys: {key1}, {key2} ;;; top_of_book: {top_of_book_}")

    def handle_market_depth_ws(self, market_depth_: MarketDepthBaseModel):      # NOQA
        print(market_depth_)
