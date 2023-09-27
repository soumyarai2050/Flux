import logging
from threading import Thread

from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.strat_executor.app.trading_cache import *
from Flux.CodeGenProjects.strat_executor.app.strat_cache import StratCache
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_models_log_keys import get_pair_strat_log_key
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import \
    get_consumable_participation_qty_http, create_alert, get_symbol_side_key, \
    get_strat_brief_log_key, get_fills_journal_log_key, get_order_journal_log_key, is_ongoing_strat
from Flux.CodeGenProjects.strat_executor.app.trading_link import TradingLinkBase, get_trading_link
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_ws_data_manager import \
    StratManagerServiceDataManager
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_ws_data_manager import (
    StratExecutorServiceDataManager)
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_key_handler import \
    StratManagerServiceKeyHandler
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_key_handler import (
    StratExecutorServiceKeyHandler)
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *

trading_link: TradingLinkBase = get_trading_link()


class TradingDataManager(StratManagerServiceDataManager, StratExecutorServiceDataManager):
    def __init__(self, executor_trigger_method: Callable, pair_strat_obj: PairStratBaseModel):
        StratManagerServiceDataManager.__init__(self, ps_host, ps_port, StratCache)
        StratExecutorServiceDataManager.__init__(self, host, port, StratCache)
        cpp_ws_url: str = f"ws://{host}:8083/"
        self.strat_cache_type: StratCache = StratCache()
        self.trading_cache: TradingCache = TradingCache()

        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # self.market_depth_ws_cont = WSReader(f"{market_data_base_url}/get-all-market_depth-ws", MarketDepthBaseModel,
        #                                     MarketDepthBaseModelList, self.handle_market_depth_ws)

        # self.market_depth_ws_const = WSReader(cpp_ws_url, MarketDepthBaseModel, MarketDepthBaseModelList,
        #                                       self.handle_market_depth_ws, False)

        # selecting which ws connections are required
        self.order_limits_ws_get_all_cont.register_to_run()
        self.portfolio_status_ws_get_all_cont.register_to_run()
        # overriding pair strat ws_get_all_const to filter by id
        self.pair_strat_ws_get_all_cont = self.pair_strat_ws_get_by_id_client(False, pair_strat_obj.id)
        self.pair_strat_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()
        self.portfolio_limits_ws_get_all_cont.register_to_run()

        self.executor_trigger_method = executor_trigger_method
        self.pair_strat_obj = pair_strat_obj
        self.strat_thread_dict: dict[str, Tuple['StratExecutor', Thread]] = dict()
        self.ws_thread = Thread(target=WSReader.start, daemon=True).start()

    # define callbacks for types you expect from ws as updates

    def underlying_handle_portfolio_status_ws(self, **kwargs):
        portfolio_status_ = kwargs.get("portfolio_status_")
        if portfolio_status_ is not None:
            # handle kill switch here (in portfolio status handler directly)
            if portfolio_status_.kill_switch:
                trading_link.trigger_kill_switch()
        else:
            err_str_ = "Received portfolio_status object from caller as None"
            logging.exception(err_str_)

    def handle_strat_status_get_all_ws(self, strat_status_: StratStatusBaseModel | StratStatus, **kwargs):
        logging.info("##### entered ss handler")
        key_leg_1, key_leg_2 = StratManagerServiceKeyHandler.get_key_from_pair_strat(self.pair_strat_obj)
        if is_ongoing_strat(strat_status_):
            # only pair strat should use guaranteed_get_by_key as it is the only handler that removes the strat cache
            strat_cache: StratCache = StratCache.guaranteed_get_by_key(key_leg_1, key_leg_2)

            # adding strat_cache using pair_strat_id since both strat_status and strat_limits will have same id and
            # also there keys are same
            # Note: other models have same key as pair_strat
            if StratCache.get(str(strat_status_.id)) is None:
                StratCache.add(str(strat_status_.id), strat_cache)

            logging.info(f"##### stratCache: {strat_cache}")
            with strat_cache.re_ent_lock:
                strat_status_tuple = strat_cache.get_strat_status()
                cached_strat_status = None
                if strat_status_tuple is not None:
                    cached_strat_status, _ = strat_status_tuple
                if cached_strat_status is None:
                    # this is a new pair strat for processing, start its own thread with new strat executor object
                    strat_cache.set_strat_status(strat_status_)
                    logging.info(f"##### setting pair_strat: {self.pair_strat_obj}")
                    strat_cache.set_pair_strat(self.pair_strat_obj)
                    strat_cache.stopped = False
                    strat_executor, strat_executor_thread = self.executor_trigger_method(self, strat_cache)
                    # update strat key to python processing thread
                    if key_leg_1 in self.strat_thread_dict:
                        logging.error(f"Unexpected: unable to proceed with pair_strat executor key: "
                                      f"{key_leg_1}, pair_strat_key: {get_pair_strat_log_key(self.pair_strat_obj)};;;"
                                      f"existing entry found in strat_thread_dict: "
                                      f"{self.strat_thread_dict[key_leg_1]}, new requested: {self.pair_strat_obj}")
                    else:
                        self.strat_thread_dict[key_leg_1] = (strat_executor, strat_executor_thread)
                else:
                    strat_cache.set_strat_status(strat_status_)
            if self.strat_status_ws_get_all_cont.notify:
                strat_cache.notify_semaphore.release()
            logging.debug(f"Updated strat_status cache for key: {key_leg_1}, pair_strat_key: "
                          f"{get_pair_strat_log_key(self.pair_strat_obj)} ;;; strat_status: {strat_status_}")
        else:
            logging.info("##### entered else of ss handler")
            strat_cache: StratCache = StratCache.get(key_leg_1)
            if strat_cache is not None:
                # remove if this pair strat is in our cache - it's no more ongoing
                with strat_cache.re_ent_lock:
                    # demon thread will tear down itself if strat_cache.stopped is True, it will also invoke
                    # set_pair_strat(None) on cache, enabling future reactivation + stops any processing until then
                    strat_cache.stopped = True
                    if key_leg_1 in self.strat_thread_dict:
                        self.strat_thread_dict.pop(key_leg_1)
                    # don't join on trading thread - let the demon self shutdown
                    strat_cache.notify_semaphore.release()
                logging.warning(f"handle_pair_strat_ws: removed cache entry of non ongoing pair strat from trading"
                                f"pair_strat_key: {get_pair_strat_log_key(self.pair_strat_obj)};;;"
                                f"strat_status: {strat_status_}")
            # else not required - non-ongoing pair strat is not to exist in cache

    def handle_strat_brief_get_all_ws(self, strat_brief_: StratBriefBaseModel | StratBrief, **kwargs):
        if strat_brief_.pair_buy_side_trading_brief and strat_brief_.pair_sell_side_trading_brief:
            key1, key2 = StratExecutorServiceKeyHandler.get_key_from_strat_brief(strat_brief_)
            strat_cache: StratCache = StratCache.get(key1, key2)
            if strat_cache is not None:
                with strat_cache.re_ent_lock:
                    strat_cache.set_strat_brief(strat_brief_)
                cached_pair_strat_tuple = strat_cache.get_pair_strat()
                if self.strat_brief_ws_get_all_cont.notify and cached_pair_strat_tuple is not None and \
                        cached_pair_strat_tuple[0] is not None:
                    cached_pair_strat, _ = cached_pair_strat_tuple
                    strat_cache.notify_semaphore.release()
                elif (cached_pair_strat_tuple is None) or (cached_pair_strat_tuple[0] is None):
                    logging.warning(f"ignoring: no ongoing pair strat matches this strat_brief_key: "
                                    f"{get_strat_brief_log_key(strat_brief_)};;; strat_brief: {strat_brief_}")
                # else not required - strat does not need this update notification
                logging.debug(f"Updated strat_brief cache for key: {key1} {key2}, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief_)};;; strat_brief: {strat_brief_}")
            else:
                logging.debug("either a non-ongoing strat-brief or one before corresponding active pair_strat: "
                              "we discard this and expect algo to get snapshot with explicit web query - maybe we wire "
                              f"explicit web query in ongoing pair-strat notification, strat_brief_key: "
                              f"{get_strat_brief_log_key(strat_brief_)};;;strat_brief: {strat_brief_}")
        else:
            logging.error(f"ignoring strat brief update - missing required pair_buy_side_trading_brief or pair_sell_"
                          f"side_trading_brief, strat_brief_key: "
                          f"{get_strat_brief_log_key(strat_brief_)};;;strat_brief: {strat_brief_}")

    def get_key_n_strat_cache_from_fills_journal(self, fills_journal_: FillsJournalBaseModel):
        key, symbol = StratCache.get_key_n_symbol_from_fills_journal(fills_journal_)
        if key is None or symbol is None:
            logging.error(f"error: no ongoing pair strat matches this fill_journal_key: "
                          f"{get_fills_journal_log_key(fills_journal_)};;; fill_journal_: {fills_journal_}")
            return None, None
        strat_cache: StratCache = StratCache.get(key)
        return key, strat_cache

    def underlying_handle_fills_journal_ws(self, **kwargs):
        fills_journal_ = kwargs.get("fills_journal_")
        strat_cache = kwargs.get("strat_cache")
        cached_pair_strat = kwargs.get("cached_pair_strat")
        key, symbol = StratCache.get_key_n_symbol_from_fills_journal(fills_journal_)
        if symbol == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            strat_cache.set_has_unack_leg1(False)
        elif symbol == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            strat_cache.set_has_unack_leg2(False)
        else:
            logging.error(f"unexpected: fills general with non-matching symbol found in pre-matched strat-cache "
                          f"with key: {key}, fill journal symbol: {symbol}, fill_journal_key: "
                          f"{get_fills_journal_log_key(fills_journal_)}")

    def handle_fills_journal_get_all_ws(self, fills_journal_: FillsJournalBaseModel | FillsJournal, **kwargs):
        cached_pair_strat_none_cmnt = f"error: no ongoing pair strat matches this fill_journal_key: " \
                                      f"{get_fills_journal_log_key(fills_journal_)};;; fill_journal_: {fills_journal_}"
        strat_cache_none_cmnt = f"error: no ongoing pair strat matches received fill journal: {fills_journal_}"
        super().handle_fills_journal_get_all_ws(fills_journal_, cached_pair_strat_none_cmnt=cached_pair_strat_none_cmnt,
                                                strat_cache_none_cmnt=strat_cache_none_cmnt)

    def underlying_handle_order_journal_ws(self, **kwargs):
        order_journal_ = kwargs.get("order_journal_")
        strat_cache = kwargs.get("strat_cache")
        cached_pair_strat = kwargs.get("cached_pair_strat")
        order_journal_key = kwargs.get("order_journal_key")
        if order_journal_ is None or strat_cache is None or cached_pair_strat is None or order_journal_key is None:
            err_str_ = f"received order_journal_ as {order_journal_}, strat_cache as {strat_cache}, " \
                       f"cached_pair_strat as {cached_pair_strat} and order_journal_key as {order_journal_key} " \
                       f"from caller of underlying_handle_order_journal_ws, ignored override task for this call"
            logging.exception(err_str_)
            return None
        with strat_cache.re_ent_lock:
            is_unack = False
            if order_journal_.order_event in [OrderEventType.OE_NEW, OrderEventType.OE_CXL]:
                is_unack = True
                if order_journal_.order_event == OrderEventType.OE_NEW:
                    StratCache.order_id_to_symbol_side_tuple_dict[order_journal_.order.order_id] = \
                        (order_journal_.order.security.sec_id, order_journal_.order.side)
        if order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            strat_cache.set_has_unack_leg1(is_unack)
        elif order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            strat_cache.set_has_unack_leg2(is_unack)
        else:
            logging.error(f"unexpected: order general with non-matching symbol found in pre-matched strat-cache "
                          f"with key: {order_journal_key}, order_journal_key: "
                          f"{get_order_journal_log_key(order_journal_)}")

    def handle_order_journal_get_all_ws(self, order_journal_: OrderJournalBaseModel | OrderJournal, **kwargs):
        key = StratExecutorServiceKeyHandler.get_key_from_order_journal(order_journal_)
        cached_pair_strat_none_cmnt = f"error: no ongoing pair strat matches this order_journal_key: " \
                                      f"{get_order_journal_log_key(order_journal_)};;; order_journal_: {order_journal_}"
        strat_cache_none_cmnt = f"error: no ongoing pair strat matches received order journal key: {key}, " \
                                f"order_journal_key: {get_order_journal_log_key(order_journal_)};;;" \
                                f"order_journal: {order_journal_}"
        super().handle_order_journal_get_all_ws(order_journal_, cached_pair_strat_none_cmnt=cached_pair_strat_none_cmnt,
                                                strat_cache_none_cmnt=strat_cache_none_cmnt)

    def handle_cancel_order_get_all_ws(self, cancel_order_: CancelOrderBaseModel | CancelOrder, **kwargs):
        key = StratExecutorServiceKeyHandler.get_key_from_cancel_order(cancel_order_)
        strat_cache: StratCache = StratCache.get(key)
        cached_pair_strat_none_cmnt = f"error: cancel_order key: {key} matched strat_cache with None pair_strat, " \
                                      f"symbol_side_key: " \
                                      f"{get_symbol_side_key([(cancel_order_.security.sec_id, cancel_order_.side)])} ;;;" \
                                      f"cancel_order: {cancel_order_}, strat_cache: {strat_cache}"
        strat_cache_none_cmnt = f"error: no ongoing pair strat matches this cancel_order key: {key} symbol_side_key: " \
                                f"{get_symbol_side_key([(cancel_order_.security.sec_id, cancel_order_.side)])};;; " \
                                f"cancel_order: {cancel_order_}"
        super().handle_cancel_order_get_all_ws(cancel_order_, cached_pair_strat_none_cmnt=cached_pair_strat_none_cmnt,
                                               strat_cache_none_cmnt=strat_cache_none_cmnt)

    def handle_new_order_get_all_ws(self, new_order_: NewOrderBaseModel | NewOrder, **kwargs):
        key = StratExecutorServiceKeyHandler.get_key_from_new_order(new_order_)
        strat_cache: StratCache = StratCache.get(key)
        cached_pair_strat_none_cmnt = f"error: new_order_ key: {key}matched strat_cache with None pair_strat, " \
                                      f"symbol_side_key: " \
                                      f"{get_symbol_side_key([(new_order_.security.sec_id, new_order_.side)])}" \
                                      f";;;new_order_: {new_order_}, strat_cache: {strat_cache}"
        strat_cache_none_cmnt = f"error: no ongoing pair strat matches this new_order_ key: {key}, " \
                                f"symbol_side_key: {get_symbol_side_key([(new_order_.security.sec_id, new_order_.side)])}" \
                                f";;;new_order_: {new_order_}, strat_cache: {strat_cache}"
        super().handle_new_order_get_all_ws(new_order_, cached_pair_strat_none_cmnt=cached_pair_strat_none_cmnt,
                                            strat_cache_none_cmnt=strat_cache_none_cmnt)

    def handle_fx_symbol_overview_get_all_ws(self, fx_symbol_overview_: FxSymbolOverviewBaseModel, **kwargs):
        if fx_symbol_overview_.symbol in StratCache.fx_symbol_overview_dict:
            # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
            StratCache.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
            StratCache.notify_all()
        super().handle_fx_symbol_overview_get_all_ws(fx_symbol_overview_)

    def handle_top_of_book_get_all_ws(self, top_of_book_: TopOfBookBaseModel | TopOfBook, **kwargs):
        if top_of_book_.symbol in StratCache.fx_symbol_overview_dict:
            # if we need fx TOB: StratCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx TOB at this time
        logging.info(f"##### tob handler override: {StratCache.fx_symbol_overview_dict}")
        super().handle_top_of_book_get_all_ws(top_of_book_)

    def handle_market_depth_get_all_ws(self, market_depth_: MarketDepthBaseModel, **kwargs):
        if market_depth_.symbol in StratCache.fx_symbol_overview_dict:
            # if we need fx Market Depth: StratCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx MarketDepth at this time
        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # super().handle_market_depth_get_all_ws(market_depth_)
