from threading import Thread

from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.strat_executor.app.trading_cache import *
from Flux.CodeGenProjects.strat_executor.app.strat_cache import StratCache
from Flux.CodeGenProjects.strat_executor.app.strat_executor_service_helper import (
    get_symbol_side_key, get_fills_journal_log_key, get_order_journal_log_key)
from Flux.CodeGenProjects.pair_strat_engine.app.pair_strat_engine_service_helper import is_ongoing_strat
from Flux.CodeGenProjects.strat_executor.app.trading_link import TradingLinkBase, get_trading_link, is_test_run
from Flux.CodeGenProjects.pair_strat_engine.generated.StratExecutor.strat_manager_service_ws_data_manager import \
    StratManagerServiceDataManager
from Flux.CodeGenProjects.strat_executor.generated.StratExecutor.strat_executor_service_ws_data_manager import (
    StratExecutorServiceDataManager)
from Flux.CodeGenProjects.strat_executor.app.get_pair_strat_n_executor_client import *
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import *
from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_client import StratExecutorServiceHttpClient

trading_link: TradingLinkBase = get_trading_link()
port = os.environ.get("PORT")
if port is None or len(port) == 0:
    err_str = f"Env var 'PORT' received as {port}"
    logging.exception(err_str)
    raise Exception(err_str)
else:
    port = parse_to_int(port)


class TradingDataManager(StratManagerServiceDataManager, StratExecutorServiceDataManager):

    def __init__(self, executor_trigger_method: Callable,
                 strat_cache: StratCache, ):
        StratManagerServiceDataManager.__init__(self, ps_host, ps_port, strat_cache)
        StratExecutorServiceDataManager.__init__(self, host, port, strat_cache)
        cpp_ws_url: str = f"ws://{host}:8083/"
        self.trading_cache: TradingCache = TradingCache()
        self.strat_cache: StratCache = strat_cache
        self.strat_executor = None
        self.strat_executor_thread: Thread | None = None

        raise_exception = False
        pair_strat_tuple: Tuple[PairStrat, DateTime] = self.strat_cache.get_pair_strat()
        if pair_strat_tuple is None:
            raise_exception = True
        else:
            pair_strat, _ = pair_strat_tuple
            if not pair_strat:
                raise_exception = True
        if raise_exception:
            err_str_ = (
                "Couldn't find any pair_strat in strat_cache, strat_cache must be loaded with pair_strat before"
                "provided to object initialization - ignoring TradingDataManager init")
            logging.error(err_str_)
            raise Exception(err_str)

        if is_test_run:
            err_str_: str = f"strat executor running in test mode, is_test_run: {is_test_run}"
            print(f"CRITICAL: {err_str_}")
            logging.critical(err_str_)
        # else not required


        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # self.market_depth_ws_cont = WSReader(f"{market_data_base_url}/get-all-market_depth-ws", MarketDepthBaseModel,
        #                                     MarketDepthBaseModelList, self.handle_market_depth_ws)

        # self.market_depth_ws_const = WSReader(cpp_ws_url, MarketDepthBaseModel, MarketDepthBaseModelList,
        #                                       self.handle_market_depth_ws, False)

        # selecting which ws connections are required
        self.order_limits_ws_get_all_cont.register_to_run()
        self.portfolio_status_ws_get_all_cont.register_to_run()
        # overriding pair strat ws_get_all_const to filter by id
        pair_strat_obj = self.strat_cache.get_pair_strat()[0]
        self.pair_strat_ws_get_all_cont = self.pair_strat_ws_get_by_id_client(False, pair_strat_obj.id)
        self.pair_strat_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()
        self.portfolio_limits_ws_get_all_cont.register_to_run()

        self.executor_trigger_method = executor_trigger_method
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

    def handle_pair_strat_get_by_id_ws(self, pair_strat_: PairStratBaseModel, **kwargs):
        if is_ongoing_strat(pair_strat_):
            with self.strat_cache.re_ent_lock:
                pair_strat_tuple = self.strat_cache.get_pair_strat()
                cached_pair_strat = None
                if pair_strat_tuple is not None:
                    cached_pair_strat, _ = pair_strat_tuple
                if self.strat_executor is None:
                    # this is a new pair strat for processing, start its own thread with new strat executor object
                    self.strat_cache.stopped = False
                    self.strat_executor, self.strat_executor_thread = (
                        self.executor_trigger_method(self, self.strat_cache))
                    # update strat key to python processing thread
                self.strat_cache.set_pair_strat(pair_strat_)
            if self.strat_status_ws_get_all_cont.notify:
                self.strat_cache.notify_semaphore.release()
            logging.debug(f"Updated pair_strat;;; pair_strat: {pair_strat_}")
        else:
            if not self.strat_cache.stopped:
                # strat_cache is not ongoing but is still running should be stopped
                with self.strat_cache.re_ent_lock:
                    # demon thread will tear down itself if strat_cache.stopped is True, it will also invoke
                    # set_pair_strat(None) on cache, enabling future reactivation + stops any processing until then
                    self.strat_cache.set_pair_strat(pair_strat_)
                    self.strat_cache.stopped = True
                    self.strat_cache.notify_semaphore.release()
                logging.warning(f"handle_pair_strat_get_by_id_ws: removed cache entry of non ongoing strat;;;"
                                f"pair_strat: {pair_strat_}")
            # else not required: fine if strat cache is non-ongoing and is not running(stopped is True)

    def handle_strat_brief_get_all_ws(self, strat_brief_: StratBriefBaseModel | StratBrief, **kwargs):
        if strat_brief_.pair_buy_side_trading_brief and strat_brief_.pair_sell_side_trading_brief:
            super().handle_strat_brief_get_all_ws(strat_brief_, **kwargs)
        else:
            # don't log strat_brief_key here, it needs both legs (missing here): {get_strat_brief_log_key(strat_brief_)}
            logging.error(f"ignoring strat brief update - missing required pair_buy_side_trading_brief or pair_sell_"
                          f"side_trading_brief;;;strat_brief: {strat_brief_}")

    def underlying_handle_fills_journal_ws(self, **kwargs):
        fills_journal_ = kwargs.get("fills_journal_")
        key, symbol = StratCache.get_key_n_symbol_from_fills_journal(fills_journal_)
        cached_pair_strat, _ = self.strat_cache.get_pair_strat()

        symbol_side_tuple = StratCache.order_id_to_symbol_side_tuple_dict.get(fills_journal_.order_id)
        if not symbol_side_tuple:
            logging.error(f"Unknown order id: {fills_journal_.order_id} found for fill "
                          f"{get_fills_journal_log_key(fills_journal_)}, avoiding set_has_unack_leg update;;;"
                          f"fill_journal: {fills_journal_}")
            return
        symbol, side = symbol_side_tuple

        if symbol == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            self.strat_cache.set_has_unack_leg1(False)
        elif symbol == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            self.strat_cache.set_has_unack_leg2(False)
        else:
            logging.error(f"unexpected: fills general with non-matching symbol found in pre-matched strat-cache "
                          f"with key: {key}, fill journal symbol: {symbol}, fill_journal_key: "
                          f"{get_fills_journal_log_key(fills_journal_)}")

    def underlying_handle_order_journal_ws(self, **kwargs):
        order_journal_ = kwargs.get("order_journal_")
        with self.strat_cache.re_ent_lock:
            is_unack = False
            if order_journal_.order_event in [OrderEventType.OE_NEW, OrderEventType.OE_CXL]:
                is_unack = True
                if order_journal_.order_event == OrderEventType.OE_NEW:
                    StratCache.order_id_to_symbol_side_tuple_dict[order_journal_.order.order_id] = \
                        (order_journal_.order.security.sec_id, order_journal_.order.side)

        cached_pair_strat, _ = self.strat_cache.get_pair_strat()
        if order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            self.strat_cache.set_has_unack_leg1(is_unack)
        elif order_journal_.order.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            self.strat_cache.set_has_unack_leg2(is_unack)
        else:
            logging.error(f"unexpected: order general with non-matching symbol found in pre-matched strat-cache, "
                          f"order_journal_key: {get_order_journal_log_key(order_journal_)}")

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
        super().handle_top_of_book_get_all_ws(top_of_book_)

    def handle_recovery_order_journal(self, order_journal_: OrderJournal | OrderJournalBaseModel):
        # interface to update order_journal in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_order_journal(order_journal_)
        logging.debug(f"Updated order_journal cache in recovery;;; order_journal: {order_journal_}")

    def handle_recovery_cancel_order(self, cancel_order_: CancelOrder | CancelOrderBaseModel):
        # interface to update cancel_order in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_cancel_order(cancel_order_)
        logging.debug(f"Updated cancel_order cache in recovery;;; cancel_order: {cancel_order_}")

    def handle_recovery_new_order(self, new_order_: NewOrder | NewOrderBaseModel):
        # interface to update new_order in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_new_order(new_order_)
        logging.debug(f"Updated new_order cache in recovery;;; new_order: {new_order_}")

    def handle_market_depth_get_all_ws(self, market_depth_: MarketDepthBaseModel | MarketDepth, **kwargs):
        if market_depth_.symbol in StratCache.fx_symbol_overview_dict:
            # if we need fx Market Depth: StratCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx MarketDepth at this time
        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # super().handle_market_depth_get_all_ws(market_depth_)
