from threading import Thread

from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_cache import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.plan_cache import PlanCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    is_ongoing_plan, ps_host, ps_port)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_plan_log_key)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import market, get_bartering_link
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_ws_data_manager import (
    EmailBookServiceDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.StreetBook.street_book_service_ws_data_manager import (
    StreetBookServiceDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.generated.ORMModel.street_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    PairPlan, PairPlanBaseModel, FxSymbolOverviewBaseModel)
from FluxPythonUtils.scripts.general_utility_functions import parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_data_manager import BaseBarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_pair_plan_log_key, get_symbol_side_key)

port = os.environ.get("PORT")
if port is None or len(port) == 0:
    err_str = f"Env var 'PORT' received as {port}"
    logging.exception(err_str)
    raise Exception(err_str)
else:
    port = parse_to_int(port)


class BarteringDataManager(BaseBarteringDataManager, EmailBookServiceDataManager, StreetBookServiceDataManager):

    def __init__(self, executor_trigger_method: Callable,
                 plan_cache: PlanCache):
        BaseBarteringDataManager.__init__(self)
        EmailBookServiceDataManager.__init__(self, ps_host, ps_port, plan_cache)
        StreetBookServiceDataManager.__init__(self, host, port, plan_cache)
        cpp_ws_url: str = f"ws://{host}:8083/"
        self.bartering_cache: BarteringCache = BarteringCache()
        self.plan_cache: PlanCache = plan_cache

        raise_exception = False
        pair_plan: PairPlan | None = None
        pair_plan_tuple: Tuple[PairPlan, DateTime] = self.plan_cache.get_pair_plan()
        if pair_plan_tuple is None:
            raise_exception = True
        else:
            pair_plan, _ = pair_plan_tuple
            if not pair_plan:
                raise_exception = True
        if raise_exception:
            err_str_ = (
                "Couldn't find any pair_plan in plan_cache, plan_cache must be loaded with pair_plan before"
                "provided to object initialization - ignoring BarteringDataManager init")
            logging.error(err_str_)
            raise Exception(err_str)

        if market.is_test_run:
            err_str_: str = f"plan executor running in test mode, {market.is_test_run=}"
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
        # overriding pair plan ws_get_all_const to filter by id
        # reached here only when pair_plan is not None
        self.pair_plan_ws_get_all_cont = self.pair_plan_ws_get_by_id_client(False, pair_plan.id)
        self.pair_plan_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()
        self.contact_limits_ws_get_all_cont.register_to_run()

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
    # def underlying_handle_contact_status_ws(self, **kwargs):
    #     contact_status_ = kwargs.get("contact_status_")
    #     if contact_status_ is not None:
    #         # handle kill switch here (in contact status handler directly)
    #         if contact_status_.kill_switch:
    #             logging.critical("Triggering contact_status Kill_SWITCH")
    #             bartering_link.trigger_kill_switch()
    #     else:
    #         err_str_ = "Received contact_status object from caller as None"
    #         logging.exception(err_str_)

    def handle_pair_plan_get_by_id_ws(self, pair_plan_: PairPlanBaseModel, **kwargs):
        if is_ongoing_plan(pair_plan_):
            with self.plan_cache.re_ent_lock:
                pair_plan_tuple = self.plan_cache.get_pair_plan()
                cached_pair_plan = None
                if pair_plan_tuple is not None:
                    cached_pair_plan, _ = pair_plan_tuple
                if cached_pair_plan is not None and cached_pair_plan.plan_state != pair_plan_.plan_state:
                    logging.warning(f"Plan state changed from {cached_pair_plan.plan_state.value} to "
                                    f"{pair_plan_.plan_state.value};;;pair_plan_log_key: "
                                    f"{get_pair_plan_log_key(pair_plan_)}")
                if self.street_book is None:
                    # this is a new pair plan for processing, start its own thread with new plan executor object
                    self.plan_cache.stopped = False
                    self.street_book, self.street_book_thread = self.executor_trigger_method(self,
                                                                                                   self.plan_cache)
                    # update plan key to python processing thread
                self.plan_cache.set_pair_plan(pair_plan_)
            if self.plan_status_ws_get_all_cont.notify:
                self.plan_cache.notify_semaphore.release()
            logging.debug(f"Updated pair_plan;;; {pair_plan_ = }")
        else:
            if not self.plan_cache.stopped:
                # plan_cache is not ongoing but is still running should be stopped
                with self.plan_cache.re_ent_lock:
                    # demon thread will tear down itself if plan_cache.stopped is True, it will also invoke
                    # set_pair_plan(None) on cache, enabling future reactivation + stops any processing until then
                    pair_plan_tuple = self.plan_cache.get_pair_plan()
                    cached_pair_plan = None
                    if pair_plan_tuple is not None:
                        cached_pair_plan, _ = pair_plan_tuple
                    if cached_pair_plan is not None and cached_pair_plan.plan_state != pair_plan_.plan_state:
                        logging.warning(f"Plan state changed from {cached_pair_plan.plan_state.value} to "
                                        f"{pair_plan_.plan_state.value};;;pair_plan_log_key: "
                                        f"{get_pair_plan_log_key(pair_plan_)}")
                    self.plan_cache.set_pair_plan(pair_plan_)
                    self.plan_cache.stopped = True
                    # @@@ trigger streaming unsubscribe
                    if bartering_link := get_bartering_link():
                        bartering_link.unsubscribe()
                        self.plan_cache.notify_semaphore.release()
                    else:
                        logging.error("Unexpected: get_bartering_link() returned None in handle_pair_plan_get_by_id_ws,"
                                      " bartering_link.unsubscribe not done for non ongoing pair-plan "
                                      f"{get_pair_plan_log_key(pair_plan_)}")

                logging.warning(f"handle_pair_plan_get_by_id_ws: removed cache entry of non ongoing plan;;;"
                                f"{pair_plan_ = }")
            # else not required: fine if plan cache is non-ongoing and is not running(stopped is True)

    def handle_plan_brief_get_all_ws(self, plan_brief_: PlanBriefBaseModel | PlanBrief, **kwargs):
        if plan_brief_.pair_buy_side_bartering_brief and plan_brief_.pair_sell_side_bartering_brief:
            super().handle_plan_brief_get_all_ws(plan_brief_, **kwargs)
        else:
            # don't log plan_brief_key here, it needs both legs (missing here): {get_plan_brief_log_key(plan_brief_)}
            logging.error(f"ignoring plan brief update - missing required pair_buy_side_bartering_brief or pair_sell_"
                          f"side_bartering_brief;;; {plan_brief_ = }")

    def underlying_handle_deals_ledger_ws(self, **kwargs):
        # deals_ledger_ = kwargs.get("deals_ledger_")
        # key, symbol = PlanCache.get_key_n_symbol_from_deals_ledger(deals_ledger_)
        # cached_pair_plan, _ = self.plan_cache.get_pair_plan()
        #
        # symbol_side_tuple = PlanCache.chore_id_to_symbol_side_tuple_dict.get(deals_ledger_.chore_id)
        # if not symbol_side_tuple:
        #     logging.error(f"Unknown chore id: {deals_ledger_.chore_id} found for fill "
        #                   f"{get_deals_ledger_log_key(deals_ledger_)}, avoiding set_has_unack_leg update;;;"
        #                   f" {deals_ledger_ = }")
        #     return
        # symbol, side = symbol_side_tuple
        #
        # if symbol == cached_pair_plan.pair_plan_params.plan_leg1.sec.sec_id:
        #     self.plan_cache.set_has_unack_leg1(False)
        # elif symbol == cached_pair_plan.pair_plan_params.plan_leg2.sec.sec_id:
        #     self.plan_cache.set_has_unack_leg2(False)
        # else:
        #     logging.error(f"unexpected: deals general with non-matching symbol found in pre-matched plan-cache "
        #                   f"with {key = }, fill ledger {symbol = }, fill_ledger_key: "
        #                   f"{get_deals_ledger_log_key(deals_ledger_)}")
        pass

    # disabled - we are using chore snapshot instead - if we enable this back, ensure to remove the unack logic
    # def underlying_handle_chore_ledger_ws(self, **kwargs):
    #     chore_ledger_ = kwargs.get("chore_ledger_")
    #     with self.plan_cache.re_ent_lock:
    #         is_unack = False
    #         if chore_ledger_.chore_event in [ChoreEventType.OE_NEW, ChoreEventType.OE_CXL]:
    #             is_unack = True
    #             if chore_ledger_.chore_event == ChoreEventType.OE_NEW:
    #                 PlanCache.chore_id_to_symbol_side_tuple_dict[chore_ledger_.chore.chore_id] = \
    #                     (chore_ledger_.chore.security.sec_id, chore_ledger_.chore.side)
    #
    #     cached_pair_plan, _ = self.plan_cache.get_pair_plan()
    #     if chore_ledger_.chore.security.sec_id == cached_pair_plan.pair_plan_params.plan_leg1.sec.sec_id:
    #         self.plan_cache.set_has_unack_leg1(is_unack)
    #     elif chore_ledger_.chore.security.sec_id == cached_pair_plan.pair_plan_params.plan_leg2.sec.sec_id:
    #         self.plan_cache.set_has_unack_leg2(is_unack)
    #     else:
    #         logging.error(f"unexpected: chore ledger with non-matching symbol found in pre-matched plan-cache, "
    #                       f"chore_ledger_key: {get_chore_ledger_log_key(chore_ledger_)}")

    def handle_unack_state(self, is_unack: bool, chore_snapshot_: ChoreSnapshotBaseModel | ChoreSnapshot):
        cached_pair_plan, _ = self.plan_cache.get_pair_plan()
        if chore_snapshot_.chore_brief.security.sec_id == cached_pair_plan.pair_plan_params.plan_leg1.sec.sec_id:
            if chore_snapshot_.chore_brief.user_data:
                self.plan_cache.set_has_unack_leg1(is_unack, chore_snapshot_.chore_brief.user_data)
            # else not required, external chore TODO: Add check for specific user data
        elif chore_snapshot_.chore_brief.security.sec_id == cached_pair_plan.pair_plan_params.plan_leg2.sec.sec_id:
            if chore_snapshot_.chore_brief.user_data:
                self.plan_cache.set_has_unack_leg2(is_unack, chore_snapshot_.chore_brief.user_data)
            # else not required, external chore TODO: Add check for specific user data
        else:
            chore_snapshot_key = get_symbol_side_key([(chore_snapshot_.chore_brief.security.sec_id,
                                                       chore_snapshot_.chore_brief.side)])
            logging.error(f"unexpected: chore snapshot with non-matching symbol found in pre-matched plan-cache, "
                          f"{chore_snapshot_key=};;;{chore_snapshot_=}")

    def underlying_handle_chore_snapshot_ws(self, **kwargs):
        self.underlying_handle_chore_snapshot_ws_(**kwargs)

    def handle_fx_symbol_overview_get_all_ws(self, fx_symbol_overview_: FxSymbolOverviewBaseModel, **kwargs):
        if fx_symbol_overview_.symbol in PlanCache.fx_symbol_overview_dict:
            # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
            PlanCache.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
            PlanCache.notify_all()
        super().handle_fx_symbol_overview_get_all_ws(fx_symbol_overview_)

    def handle_top_of_book_get_all_ws(self, top_of_book_: TopOfBookBaseModel | TopOfBook, **kwargs):
        if top_of_book_.symbol in PlanCache.fx_symbol_overview_dict:
            # if we need fx TOB: PlanCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx TOB at this time
        super().handle_top_of_book_get_all_ws(top_of_book_)

    def handle_recovery_chore_ledger(self, chore_ledger_: ChoreLedger | ChoreLedgerBaseModel):
        # interface to update chore_ledger in crash recovery, Must be used only if required
        with self.plan_cache.re_ent_lock:
            self.plan_cache.set_chore_ledger(chore_ledger_)
        logging.debug(f"Updated chore_ledger cache in recovery;;; {chore_ledger_ = }")

    def handle_recovery_cancel_chore(self, cancel_chore_: CancelChore | CancelChoreBaseModel):
        # interface to update cancel_chore in crash recovery, Must be used only if required
        with self.plan_cache.re_ent_lock:
            self.plan_cache.set_cancel_chore(cancel_chore_)
        logging.debug(f"Updated cancel_chore cache in recovery;;; {cancel_chore_ = }")

    def handle_recovery_new_chore(self, new_chore_: NewChore | NewChoreBaseModel):
        # interface to update new_chore in crash recovery, Must be used only if required
        with self.plan_cache.re_ent_lock:
            self.plan_cache.set_new_chore(new_chore_)
        logging.debug(f"Updated new_chore cache in recovery;;; {new_chore_ = }")

    def handle_market_depth_get_all_ws(self, market_depth_: MarketDepthBaseModel | MarketDepth, **kwargs):
        if market_depth_.symbol in PlanCache.fx_symbol_overview_dict:
            # if we need fx Market Depth: PlanCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx MarketDepth at this time
        # TODO IMPORTANT Enable this when we add formal ws support for market depth
        # super().handle_market_depth_get_all_ws(market_depth_)
