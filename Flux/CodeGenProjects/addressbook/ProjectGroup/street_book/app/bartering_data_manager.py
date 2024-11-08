from threading import Thread

from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_cache import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.strat_cache import StratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    is_ongoing_strat, ps_host, ps_port)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_strat_log_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import market, get_bartering_link
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_ws_data_manager import (
    EmailBookServiceDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_ws_data_manager import (
    StreetBookServiceDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.Pydentic.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import (
    PairStrat, PairStratBaseModel, FxSymbolOverviewBaseModel)
from FluxPythonUtils.scripts.utility_functions import parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_data_manager import BaseBarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_strat_log_key, get_symbol_side_key)

port = os.environ.get("PORT")
if port is None or len(port) == 0:
    err_str = f"Env var 'PORT' received as {port}"
    logging.exception(err_str)
    raise Exception(err_str)
else:
    port = parse_to_int(port)


class BarteringDataManager(BaseBarteringDataManager, EmailBookServiceDataManager, StreetBookServiceDataManager):

    def __init__(self, executor_trigger_method: Callable,
                 strat_cache: StratCache):
        BaseBarteringDataManager.__init__(self)
        EmailBookServiceDataManager.__init__(self, ps_host, ps_port, strat_cache)
        StreetBookServiceDataManager.__init__(self, host, port, strat_cache)
        cpp_ws_url: str = f"ws://{host}:8083/"
        self.bartering_cache: BarteringCache = BarteringCache()
        self.strat_cache: StratCache = strat_cache

        raise_exception = False
        pair_strat: PairStrat | None = None
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
                "provided to object initialization - ignoring BarteringDataManager init")
            logging.error(err_str_)
            raise Exception(err_str)

        if market.is_test_run:
            err_str_: str = f"strat executor running in test mode, {market.is_test_run=}"
            print(f"CRITICAL: {err_str_}")
            logging.critical(err_str_)
        # else not required

        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # self.market_depth_ws_cont = WSReader(f"{mobile_book_base_url}/get-all-market_depth-ws", MarketDepthBaseModel,
        #                                     MarketDepthBaseModelList, self.handle_market_depth_ws)

        # self.market_depth_ws_const = WSReader(cpp_ws_url, MarketDepthBaseModel, MarketDepthBaseModelList,
        #                                       self.handle_market_depth_ws, False)

        # selecting which ws connections are required
        self.chore_limits_ws_get_all_cont.register_to_run()
        self.system_control_ws_get_all_cont.register_to_run()
        # overriding pair strat ws_get_all_const to filter by id
        # reached here only when pair_strat is not None
        self.pair_strat_ws_get_all_cont = self.pair_strat_ws_get_by_id_client(False, pair_strat.id)
        self.pair_strat_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()
        self.portfolio_limits_ws_get_all_cont.register_to_run()

        self.executor_trigger_method = executor_trigger_method
        self.ws_thread = Thread(target=WSReader.start, daemon=True).start()

    def ws_reader_handler(self):
        while 1:
            try:
                WSReader.start()
            except Exception as e:
                logging.error(f"WSReader failed - reconnecting ,exception: {e}")
                raise Exception(e)

    # define callbacks for types you expect from ws as updates
    # def underlying_handle_portfolio_status_ws(self, **kwargs):
    #     portfolio_status_ = kwargs.get("portfolio_status_")
    #     if portfolio_status_ is not None:
    #         # handle kill switch here (in portfolio status handler directly)
    #         if portfolio_status_.kill_switch:
    #             logging.critical("Triggering portfolio_status Kill_SWITCH")
    #             bartering_link.trigger_kill_switch()
    #     else:
    #         err_str_ = "Received portfolio_status object from caller as None"
    #         logging.exception(err_str_)

    def handle_pair_strat_get_by_id_ws(self, pair_strat_: PairStratBaseModel, **kwargs):
        if is_ongoing_strat(pair_strat_):
            with self.strat_cache.re_ent_lock:
                pair_strat_tuple = self.strat_cache.get_pair_strat()
                cached_pair_strat = None
                if pair_strat_tuple is not None:
                    cached_pair_strat, _ = pair_strat_tuple
                if cached_pair_strat is not None and cached_pair_strat.strat_state != pair_strat_.strat_state:
                    logging.warning(f"Strat state changed from {cached_pair_strat.strat_state.value} to "
                                    f"{pair_strat_.strat_state.value};;;pair_strat_log_key: "
                                    f"{get_pair_strat_log_key(pair_strat_)}")
                if self.street_book is None:
                    # this is a new pair strat for processing, start its own thread with new strat executor object
                    self.strat_cache.stopped = False
                    self.street_book, self.street_book_thread = self.executor_trigger_method(self,
                                                                                                   self.strat_cache)
                    # update strat key to python processing thread
                self.strat_cache.set_pair_strat(pair_strat_)
            if self.strat_status_ws_get_all_cont.notify:
                self.strat_cache.notify_semaphore.release()
            logging.debug(f"Updated pair_strat;;; {pair_strat_ = }")
        else:
            if not self.strat_cache.stopped:
                # strat_cache is not ongoing but is still running should be stopped
                with self.strat_cache.re_ent_lock:
                    # demon thread will tear down itself if strat_cache.stopped is True, it will also invoke
                    # set_pair_strat(None) on cache, enabling future reactivation + stops any processing until then
                    pair_strat_tuple = self.strat_cache.get_pair_strat()
                    cached_pair_strat = None
                    if pair_strat_tuple is not None:
                        cached_pair_strat, _ = pair_strat_tuple
                    if cached_pair_strat is not None and cached_pair_strat.strat_state != pair_strat_.strat_state:
                        logging.warning(f"Strat state changed from {cached_pair_strat.strat_state.value} to "
                                        f"{pair_strat_.strat_state.value};;;pair_strat_log_key: "
                                        f"{get_pair_strat_log_key(pair_strat_)}")
                    self.strat_cache.set_pair_strat(pair_strat_)
                    self.strat_cache.stopped = True
                    # @@@ trigger streaming unsubscribe
                    if bartering_link := get_bartering_link():
                        bartering_link.unsubscribe()
                        self.strat_cache.notify_semaphore.release()
                    else:
                        logging.error("Unexpected: get_bartering_link() returned None in handle_pair_strat_get_by_id_ws,"
                                      " bartering_link.unsubscribe not done for non ongoing pair-strat "
                                      f"{get_pair_strat_log_key(pair_strat_)}")

                logging.warning(f"handle_pair_strat_get_by_id_ws: removed cache entry of non ongoing strat;;;"
                                f"{pair_strat_ = }")
            # else not required: fine if strat cache is non-ongoing and is not running(stopped is True)

    def handle_strat_brief_get_all_ws(self, strat_brief_: StratBriefBaseModel | StratBrief, **kwargs):
        if strat_brief_.pair_buy_side_bartering_brief and strat_brief_.pair_sell_side_bartering_brief:
            super().handle_strat_brief_get_all_ws(strat_brief_, **kwargs)
        else:
            # don't log strat_brief_key here, it needs both legs (missing here): {get_strat_brief_log_key(strat_brief_)}
            logging.error(f"ignoring strat brief update - missing required pair_buy_side_bartering_brief or pair_sell_"
                          f"side_bartering_brief;;; {strat_brief_ = }")

    def underlying_handle_fills_journal_ws(self, **kwargs):
        # fills_journal_ = kwargs.get("fills_journal_")
        # key, symbol = StratCache.get_key_n_symbol_from_fills_journal(fills_journal_)
        # cached_pair_strat, _ = self.strat_cache.get_pair_strat()
        #
        # symbol_side_tuple = StratCache.chore_id_to_symbol_side_tuple_dict.get(fills_journal_.chore_id)
        # if not symbol_side_tuple:
        #     logging.error(f"Unknown chore id: {fills_journal_.chore_id} found for fill "
        #                   f"{get_fills_journal_log_key(fills_journal_)}, avoiding set_has_unack_leg update;;;"
        #                   f" {fills_journal_ = }")
        #     return
        # symbol, side = symbol_side_tuple
        #
        # if symbol == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
        #     self.strat_cache.set_has_unack_leg1(False)
        # elif symbol == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
        #     self.strat_cache.set_has_unack_leg2(False)
        # else:
        #     logging.error(f"unexpected: fills general with non-matching symbol found in pre-matched strat-cache "
        #                   f"with {key = }, fill journal {symbol = }, fill_journal_key: "
        #                   f"{get_fills_journal_log_key(fills_journal_)}")
        pass

    # disabled - we are using chore snapshot instead - if we enable this back, ensure to remove the unack logic
    # def underlying_handle_chore_journal_ws(self, **kwargs):
    #     chore_journal_ = kwargs.get("chore_journal_")
    #     with self.strat_cache.re_ent_lock:
    #         is_unack = False
    #         if chore_journal_.chore_event in [ChoreEventType.OE_NEW, ChoreEventType.OE_CXL]:
    #             is_unack = True
    #             if chore_journal_.chore_event == ChoreEventType.OE_NEW:
    #                 StratCache.chore_id_to_symbol_side_tuple_dict[chore_journal_.chore.chore_id] = \
    #                     (chore_journal_.chore.security.sec_id, chore_journal_.chore.side)
    #
    #     cached_pair_strat, _ = self.strat_cache.get_pair_strat()
    #     if chore_journal_.chore.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
    #         self.strat_cache.set_has_unack_leg1(is_unack)
    #     elif chore_journal_.chore.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
    #         self.strat_cache.set_has_unack_leg2(is_unack)
    #     else:
    #         logging.error(f"unexpected: chore journal with non-matching symbol found in pre-matched strat-cache, "
    #                       f"chore_journal_key: {get_chore_journal_log_key(chore_journal_)}")

    def handle_unack_state(self, is_unack: bool, chore_snapshot_: ChoreSnapshotBaseModel | ChoreSnapshot):
        cached_pair_strat, _ = self.strat_cache.get_pair_strat()
        if chore_snapshot_.chore_brief.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg1.sec.sec_id:
            if chore_snapshot_.chore_brief.user_data:
                self.strat_cache.set_has_unack_leg1(is_unack, chore_snapshot_.chore_brief.user_data)
            # else not required, external chore TODO: Add check for specific user data
        elif chore_snapshot_.chore_brief.security.sec_id == cached_pair_strat.pair_strat_params.strat_leg2.sec.sec_id:
            if chore_snapshot_.chore_brief.user_data:
                self.strat_cache.set_has_unack_leg2(is_unack, chore_snapshot_.chore_brief.user_data)
            # else not required, external chore TODO: Add check for specific user data
        else:
            chore_snapshot_key = get_symbol_side_key([(chore_snapshot_.chore_brief.security.sec_id,
                                                       chore_snapshot_.chore_brief.side)])
            logging.error(f"unexpected: chore snapshot with non-matching symbol found in pre-matched strat-cache, "
                          f"{chore_snapshot_key=};;;{chore_snapshot_=}")

    def underlying_handle_chore_snapshot_ws(self, **kwargs):
        self.underlying_handle_chore_snapshot_ws_(**kwargs)

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

    def handle_recovery_chore_journal(self, chore_journal_: ChoreJournal | ChoreJournalBaseModel):
        # interface to update chore_journal in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_chore_journal(chore_journal_)
        logging.debug(f"Updated chore_journal cache in recovery;;; {chore_journal_ = }")

    def handle_recovery_cancel_chore(self, cancel_chore_: CancelChore | CancelChoreBaseModel):
        # interface to update cancel_chore in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_cancel_chore(cancel_chore_)
        logging.debug(f"Updated cancel_chore cache in recovery;;; {cancel_chore_ = }")

    def handle_recovery_new_chore(self, new_chore_: NewChore | NewChoreBaseModel):
        # interface to update new_chore in crash recovery, Must be used only if required
        with self.strat_cache.re_ent_lock:
            self.strat_cache.set_new_chore(new_chore_)
        logging.debug(f"Updated new_chore cache in recovery;;; {new_chore_ = }")

    def handle_market_depth_get_all_ws(self, market_depth_: MarketDepthBaseModel | MarketDepth, **kwargs):
        if market_depth_.symbol in StratCache.fx_symbol_overview_dict:
            # if we need fx Market Depth: StratCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx MarketDepth at this time
        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # super().handle_market_depth_get_all_ws(market_depth_)
