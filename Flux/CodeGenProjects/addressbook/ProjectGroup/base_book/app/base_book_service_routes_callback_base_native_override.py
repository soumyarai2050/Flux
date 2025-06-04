# standard imports
import time
from typing import Set, final
import ctypes
from abc import abstractmethod

# project imports
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import (
    chore_has_terminal_state, create_symbol_overview_pre_helper, update_symbol_overview_pre_helper,
    get_bkr_from_underlying_account, partial_update_symbol_overview_pre_helper)
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert, create_logger)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    is_ongoing_plan, email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.barter_simulator import (
    BarterSimulator, BarteringLinkBase)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.aggregate import (
    get_symbol_side_underlying_account_cumulative_fill_qty,
    get_last_n_chore_journals_from_chore_id, get_objs_from_symbol)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book import (
    BaseBook)
from FluxPythonUtils.scripts.service import Service
# below import is required to symbol_cache to work - SymbolCacheContainer must import from base_plan_cache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_plan_cache import BasePlanCache, SymbolCacheContainer, SymbolCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_data_manager import (
    BaseBarteringDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import get_symbol_side_key

BasePlanCacheType = TypeVar('BasePlanCacheType', bound=BasePlanCache)
BaseBarteringDataManagerType = TypeVar('BaseBarteringDataManagerType', bound=BaseBarteringDataManager)


class BaseBookServiceRoutesCallbackBaseNativeOverride(Service):
    KeyHandler = None   # must be set by derived class
    residual_compute_shared_lock: AsyncRLock | None = None
    journal_shared_lock: AsyncRLock | None = None
    get_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_update_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_create_chore_snapshot_http: Callable[..., Any] | None = None
    underlying_read_chore_journal_http: Callable[..., Any] | None = None
    underlying_read_symbol_overview_by_id_http: Callable[..., Any] | None = None
    underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http: Callable[..., Any] | None = None
    underlying_read_fills_journal_http: Callable[..., Any] | None = None
    underlying_read_top_of_book_http: Callable[..., Any] | None = None

    @classmethod
    def initialize_underlying_http_routes(cls):
        raise NotImplementedError

    def __init__(self):
        super().__init__()
        self.market = Market(MarketID.IN)
        self.datetime_fmt_str: Final[str] = datetime.datetime.now().strftime("%Y%m%d")
        self.all_services_up: bool = False
        self.service_ready: bool = False
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.static_data: SecurityRecordManager | None = None
        self.usd_fx = None
        self.plan_cache: BasePlanCacheType | None = None
        self.min_refresh_interval = 30  # default - override in derived with configured value
        self.executor_config_yaml_dict: Dict | None = None  # override in derived with configured value
        self.project_config_yaml_dict: Dict | None = None  # override in derived with configured value
        self.project_config_yaml_path: str | None = None  # override in derived with configured value
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.bartering_data_manager: BaseBarteringDataManagerType | None = None
        self.executor_inst_id = None

        # below data members must be updated by derived class in set_log_simulator_file_name_n_path abstract method,
        # which is called in initialize_log_simulator_logger
        self.simulate_config_yaml_file_path = None
        self.log_dir_path = None
        self.log_simulator_file_name = None
        self.log_simulator_file_path = None
        self.initialize_log_simulator_logger()

        self.is_test_run = self.market.is_test_run

    @property
    def derived_class_type(self):
        raise NotImplementedError

    def get_generic_read_route(self):
        return None

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency plan for now - may extend to accept symbol and send revised px according to
        underlying bartering currency
        """
        return px / self.usd_fx

    def get_local_px_or_notional(self, px_or_notional: float, system_symbol: str):
        return px_or_notional * self.usd_fx

    @abstractmethod
    def set_log_simulator_file_name_n_path(self):
        raise NotImplementedError

    @final
    def initialize_log_simulator_logger(self):
        self.set_log_simulator_file_name_n_path()
        create_logger("log_simulator", logging.DEBUG, str(self.log_dir_path),
                      self.log_simulator_file_name)

    @classmethod
    def get_chore_journal_log_key(cls, chore_journal: ChoreJournal | ChoreJournalBaseModel | ChoreJournalOptional):
        sec_id = chore_journal.chore.security.sec_id
        side = chore_journal.chore.side
        symbol_side_key = get_symbol_side_key([(sec_id, side)])
        base_chore_journal_key = cls.KeyHandler.get_log_key_from_chore_journal(chore_journal)
        return f"{symbol_side_key}-{base_chore_journal_key}"

    @classmethod
    def get_fills_journal_log_key(cls, fills_journal: FillsJournal | FillsJournalBaseModel | FillsJournalOptional):
        sec_id = fills_journal.fill_symbol
        side = fills_journal.fill_side
        symbol_side_key = get_symbol_side_key([(sec_id, side)])
        base_fill_journal_key = cls.KeyHandler.get_log_key_from_fills_journal(fills_journal)
        return f"{symbol_side_key}-{base_fill_journal_key}"

    @classmethod
    def get_chore_snapshot_log_key(cls, chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel | ChoreSnapshotOptional):
        sec_id = chore_snapshot.chore_brief.security.sec_id
        side = chore_snapshot.chore_brief.side
        symbol_side_key = get_symbol_side_key([(sec_id, side)])
        base_chore_snapshot_key = cls.KeyHandler.get_log_key_from_chore_snapshot(chore_snapshot)
        return f"{symbol_side_key}-{base_chore_snapshot_key}"

    ##################
    # Start-Up Methods
    ##################

    def static_data_periodic_refresh(self):
        # no action required if refreshed
        self.static_data.refresh()

    @abstractmethod
    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        raise NotImplementedError

    def app_launch_pre(self):
        raise NotImplementedError

    def app_launch_post(self):
        logging.debug(f"Triggered server launch post override")

    def update_fx_symbol_overview_dict_from_http(self) -> bool:
        fx_symbol_overviews: List[FxSymbolOverviewBaseModel] = \
            email_book_service_http_client.get_all_fx_symbol_overview_client()
        if fx_symbol_overviews:
            fx_symbol_overview_: FxSymbolOverviewBaseModel
            for fx_symbol_overview_ in fx_symbol_overviews:
                if fx_symbol_overview_.symbol in BasePlanCache.fx_symbol_overview_dict:
                    # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
                    BasePlanCache.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
                    self.usd_fx = fx_symbol_overview_.closing_px
                    logging.debug(f"Updated {self.usd_fx=}")
                    return True
        # all else - return False
        return False

    async def read_all_ui_layout_pre_handler(self):
        # Setting asyncio_loop in ui_layout_pre since it called to check current service up
        attempt_counts = 3
        for _ in range(attempt_counts):
            if not self.asyncio_loop:
                self.asyncio_loop = asyncio.get_running_loop()
                time.sleep(1)
            else:
                break
        else:
            err_str_ = (f"self.asyncio_loop couldn't set as asyncio.get_running_loop() returned None for "
                        f"{attempt_counts} attempts")
            logging.critical(err_str_)
            raise HTTPException(detail=err_str_, status_code=500)

    ####################################
    # Get specific Data handling Methods
    ####################################

    async def get_list_of_underlying_account_n_cumulative_fill_qty(self, symbol: str, side: Side):
        underlying_account_cum_fill_qty_obj_list = \
            await (self.derived_class_type.
                   get_underlying_account_cumulative_fill_qty_query_http(symbol, side))
        return underlying_account_cum_fill_qty_obj_list[0].underlying_account_n_cumulative_fill_qty

    ##############################
    # Chore Journal Update Methods
    ##############################

    @staticmethod
    def get_cached_top_of_book_from_symbol(symbol: str) -> TopOfBookBaseModel | None:
        symbol_cache: SymbolCache = SymbolCacheContainer.get_symbol_cache(symbol)
        if symbol_cache is not None:
            return symbol_cache.top_of_book
        else:
            logging.error(f"Can't find any symbol_cache with {symbol=};;; "
                          f"{SymbolCacheContainer.symbol_to_symbol_cache_dict}")
            return None

    async def handle_create_chore_journal_pre(self, chore_journal_obj: ChoreJournal) -> None:
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = (f"create_chore_journal_pre not ready - service is not initialized yet, chore_journal_key: "
                        f"{self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}")
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # updating chore notional in chore journal obj
        if chore_journal_obj.chore_event == ChoreEventType.OE_NEW:
            if chore_journal_obj.chore.px == 0:
                top_of_book_obj = self.get_cached_top_of_book_from_symbol(chore_journal_obj.chore.security.sec_id)
                if top_of_book_obj is not None:
                    chore_journal_obj.chore.px = top_of_book_obj.last_barter.px
                else:
                    err_str_ = (f"received chore journal px 0 and to update px, received TOB also as {top_of_book_obj}"
                                f", chore_journal_key: "
                                f"{self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}")
                    logging.error(err_str_)
                    raise HTTPException(status_code=500, detail=err_str_)
            # extract availability if this chore is not from this executor
            if not self.executor_inst_id:
                self.executor_inst_id = BaseBook.bartering_link.inst_id
            if (not chore_journal_obj.chore.user_data) or (
                    not chore_journal_obj.chore.user_data.startswith(self.executor_inst_id)):
                # this chore is not from executor
                chore = chore_journal_obj.chore
                if not chore.security.inst_type:
                    logging.error(f"unexpected chore_journal_obj with no chore.security.inst_type, assumed EQT chore "
                                  f"for sec_id: {chore_journal_obj.chore.security.sec_id} ord_id: "
                                  f"{chore_journal_obj.chore.chore_id};;;{chore_journal_obj=}")

                # prepare new chore to extract availability
                force_bkr: str = get_bkr_from_underlying_account(chore.underlying_account, chore.security.inst_type)
                new_ord: NewChoreBaseModel = NewChoreBaseModel(security=chore.bartering_security, side=chore.side,
                                                               px=chore.px, qty=chore.qty, force_bkr=force_bkr)
                # now extract availability and log for disable broker-position if extract availability fails
                # TODO: allow extract from disabled position (explicit param), external chores may use disabled positions
                # we don't use extract availability list here - assumption 1 chore, maps to 1 position + this blocks
                # non replenishing enabled intraday positions from flowing in

                pos_cache = BasePlanCache.get_pos_cache_from_symbol_side(chore.security.sec_id, chore.side)
                is_available, sec_pos_extended = pos_cache.extract_availability(new_ord)
                if not is_available:
                    pos_disable_payload = {"symbol": chore_journal_obj.chore.bartering_security.sec_id,
                                           "symbol_type": chore_journal_obj.chore.bartering_security.sec_id_source,
                                           "account": chore_journal_obj.chore.underlying_account}
                    logging.error(f"EXT: failed to extract position for external chore: {chore_journal_obj};;;"
                                  f"sec_pos_extended: {sec_pos_extended}, pos_disable_payload: {pos_disable_payload}")
                else:
                    logging.info(f"extracted position for external chore: {chore_journal_obj}, extracted "
                                 f"sec_pos_extended: {sec_pos_extended}")
        # else If chore_journal is not new then we don't care about px, we care about event_type and if chore is new
        # and px is not 0 then using provided px
        if chore_journal_obj.chore.px is not None and chore_journal_obj.chore.qty is not None:
            chore_journal_obj.chore.chore_notional = \
                self.get_usd_px(chore_journal_obj.chore.px,
                                chore_journal_obj.chore.security.sec_id) * chore_journal_obj.chore.qty
        else:
            chore_journal_obj.chore.chore_notional = 0

    async def handle_create_chore_snapshot_pre(self, chore_snapshot_obj: ChoreSnapshot):
        # updating security's sec_id_source to default value if sec_id_source is None
        if chore_snapshot_obj.chore_brief.security.sec_id_source is None:
            chore_snapshot_obj.chore_brief.security.sec_id_source = SecurityIdSource.TICKER

    @staticmethod
    def is_cxled_event(event: ChoreEventType) -> bool:
        if event in [ChoreEventType.OE_CXL_ACK, ChoreEventType.OE_UNSOL_CXL]:
            return True
        return False

    async def _handle_chore_snapshot_update_in_chore_dod(self, chore_journal_obj: ChoreJournal,
                                                         chore_snapshot: ChoreSnapshot,
                                                         is_lapse_call: bool) -> Tuple[ChoreSnapshot, bool]:
        prior_chore_status = chore_snapshot.chore_status
        # When CXL_ACK arrived after chore got fully filled, since nothing is left to cxl - ignoring
        # this chore_journal's chore_snapshot update
        if chore_snapshot.chore_status == ChoreStatusType.OE_FILLED:
            logging.info("Received chore_journal with event CXL_ACK after ChoreSnapshot is fully "
                         f"filled - ignoring this CXL_ACK, chore_journal_key: "
                         f"{self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)};;; "
                         f"{chore_journal_obj=}, {chore_snapshot=}")
        else:
            # If chore_event is OE_UNSOL_CXL, that is treated as unsolicited cxl
            # If CXL_ACK comes after OE_CXL_UNACK, that means cxl_ack came after cxl request
            chore_brief = chore_snapshot.chore_brief
            if chore_journal_obj.chore.text:  # put update
                if chore_brief.text is None:
                    chore_brief.text = []
                # else not required: text is already set
                chore_brief.text.extend(chore_journal_obj.chore.text)
            # else not required: If no text is present in chore_journal then updating
            # chore snapshot with same obj

            if ChoreStatusType.OE_DOD == prior_chore_status:
                # CXL after CXL: no further processing needed
                chore_snapshot = await (self.derived_class_type.
                                        underlying_update_chore_snapshot_http(chore_snapshot))
                return chore_snapshot, True

            unfilled_qty = self.get_open_qty(chore_snapshot)
            if is_lapse_call:
                chore_snapshot.last_lapsed_qty = unfilled_qty
                chore_snapshot.total_lapsed_qty += unfilled_qty

            cxled_qty = unfilled_qty
            cxled_notional = cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                         chore_snapshot.chore_brief.security.sec_id)
            chore_snapshot.cxled_qty += cxled_qty
            chore_snapshot.cxled_notional += cxled_notional
            chore_snapshot.avg_cxled_px = \
                (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                               chore_snapshot.chore_brief.security.sec_id) /
                 chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0

            chore_snapshot.chore_brief = chore_brief
            chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
            chore_snapshot.chore_status = ChoreStatusType.OE_DOD
            chore_snapshot = await (self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
        return chore_snapshot, False

    async def _handle_post_chore_snapshot_update_tasks_in_chore_dod(self, chore_journal: ChoreJournal,
                                                                    chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def _handle_chore_dod(self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot,
                                is_lapse_call: bool = False):

        chore_snapshot, cxl_after_cxl = await self._handle_chore_snapshot_update_in_chore_dod(
            chore_journal_obj, chore_snapshot, is_lapse_call)
        if not cxl_after_cxl:
            return await self._handle_post_chore_snapshot_update_tasks_in_chore_dod(chore_journal_obj, chore_snapshot)
        else:
            return (True,)

    @staticmethod
    def get_valid_available_fill_qty(chore_snapshot: ChoreSnapshot) -> int:
        """
        qty which is available to be filled after amend downs and qty lapses in chore
        :param chore_snapshot:
        :return: int qty
        """
        valid_available_fill_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.total_amend_dn_qty -
                                    chore_snapshot.total_lapsed_qty)
        return valid_available_fill_qty

    @staticmethod
    def get_residual_qty_post_chore_dod(chore_snapshot: ChoreSnapshot) -> int:
        open_qty = (chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty - chore_snapshot.total_amend_dn_qty -
                    chore_snapshot.total_lapsed_qty)
        return open_qty

    @staticmethod
    def get_open_qty(chore_snapshot: ChoreSnapshot) -> int:
        open_qty = chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty - chore_snapshot.cxled_qty
        return open_qty

    async def _handle_chore_snapshot_update_after_chore_journal_amend_applied(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot, amend_direction: ChoreEventType,
            is_amend_rej_call: bool):
        last_chore_status = chore_snapshot.chore_status
        if is_amend_rej_call:
            chore_status = self.get_chore_status_post_amend_rej(chore_journal_obj,
                                                                chore_snapshot, amend_direction,
                                                                last_chore_status)
        else:
            chore_status = self.get_chore_status_post_amend_applied(chore_journal_obj,
                                                                    chore_snapshot, amend_direction,
                                                                    last_chore_status)
        if chore_status is not None:
            chore_snapshot.chore_status = chore_status
        # else not required: if something went wrong then not updating status and issue must be logged already

        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
        chore_snapshot = await (self.derived_class_type.
                                underlying_update_chore_snapshot_http(chore_snapshot))
        return chore_snapshot

    async def _handle_post_chore_snapshot_update_tasks_after_chore_journal_amend_applied(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_model_updates_post_chore_journal_amend_applied(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot, amend_direction: ChoreEventType,
            is_amend_rej_call: bool = False):
        chore_snapshot = await self._handle_chore_snapshot_update_after_chore_journal_amend_applied(
            chore_journal_obj, chore_snapshot, amend_direction, is_amend_rej_call)

        return await self._handle_post_chore_snapshot_update_tasks_after_chore_journal_amend_applied(chore_journal_obj,
                                                                                                     chore_snapshot)

    def set_default_values_to_pend_amend_fields(self, chore_snapshot: ChoreSnapshot):
        chore_snapshot.pending_amend_dn_qty = 0
        chore_snapshot.pending_amend_up_qty = 0
        chore_snapshot.pending_amend_dn_px = 0
        chore_snapshot.pending_amend_up_px = 0

    def update_chore_snapshot_pre_checks(self) -> bool:
        return True

    async def handle_post_chore_snapshot_update_tasks_for_new_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_ack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_cxl_unack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_cxl_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_int_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_lapse_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_non_risky_amend_unack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_risky_amend_ack_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def handle_post_chore_snapshot_update_tasks_for_non_risky_amend_rej_chore_journal(
            self, chore_journal_obj: ChoreJournal, chore_snapshot: ChoreSnapshot):
        return chore_snapshot

    async def _update_chore_snapshot_from_chore_journal(
            self, chore_journal_obj: ChoreJournal):
        res = self.update_chore_snapshot_pre_checks()
        if not res:     # returning None if some check fails
            return None

        match chore_journal_obj.chore_event:
            case ChoreEventType.OE_NEW:
                # importing routes here otherwise at the time of launch callback's set instance is called by
                # routes call before set_instance file call and set_instance file throws error that
                # 'set instance is called more than once in one session'
                if not chore_journal_obj.chore.px:  # market chore
                    chore_journal_obj.chore.px = BasePlanCache.get_close_px(chore_journal_obj.chore.security.sec_id)
                    if not chore_journal_obj.chore.px:
                        logging.error("ChoreEventType.OE_NEW came with no px, get_close_px failed unable to apply px")
                chore_snapshot = ChoreSnapshot(id=ChoreSnapshot.next_id(),
                                               chore_brief=chore_journal_obj.chore,
                                               filled_qty=0, avg_fill_px=0,
                                               fill_notional=0,
                                               cxled_qty=0,
                                               avg_cxled_px=0,
                                               cxled_notional=0,
                                               pending_amend_dn_px=0,
                                               pending_amend_dn_qty=0,
                                               pending_amend_up_px=0,
                                               pending_amend_up_qty=0,
                                               last_update_fill_qty=0,
                                               last_update_fill_px=0,
                                               total_amend_dn_qty=0,
                                               total_amend_up_qty=0,
                                               last_lapsed_qty=0,
                                               total_lapsed_qty=0,
                                               create_date_time=chore_journal_obj.chore_event_date_time,
                                               last_update_date_time=chore_journal_obj.chore_event_date_time,
                                               chore_status=ChoreStatusType.OE_UNACK)
                chore_snapshot = await (self.derived_class_type.
                                        underlying_create_chore_snapshot_http(chore_snapshot))
                return await self.handle_post_chore_snapshot_update_tasks_for_new_chore_journal(chore_journal_obj,
                                                                                                chore_snapshot)

            case ChoreEventType.OE_ACK:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(chore_journal_obj,
                                                                           [ChoreStatusType.OE_UNACK])
                    if chore_snapshot is not None:
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                        updated_chore_snapshot = (
                            await self.derived_class_type.underlying_update_chore_snapshot_http(chore_snapshot))

                        return await self.handle_post_chore_snapshot_update_tasks_for_ack_chore_journal(
                            chore_journal_obj, updated_chore_snapshot)

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already
            case ChoreEventType.OE_CXL:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = await self._check_state_and_get_chore_snapshot_obj(
                        chore_journal_obj, [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED,
                                            ChoreStatusType.OE_AMD_DN_UNACKED,
                                            ChoreStatusType.OE_AMD_UP_UNACKED, ChoreStatusType.OE_AMD_UP_UNACKED,
                                            ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_DOD])
                    if chore_snapshot is not None and chore_snapshot.chore_status in [ChoreStatusType.OE_CXL_UNACK,
                                                                                      ChoreStatusType.OE_DOD]:
                        return (True,)  # CXL detected after CXL/CXL-ACK, no further processing needed
                    if chore_snapshot is not None:
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.chore_status = ChoreStatusType.OE_CXL_UNACK
                        updated_chore_snapshot = await (
                            self.derived_class_type.underlying_update_chore_snapshot_http(chore_snapshot))

                        return await self.handle_post_chore_snapshot_update_tasks_for_cxl_unack_chore_journal(
                            chore_journal_obj, chore_snapshot)

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already
            case ChoreEventType.OE_CXL_ACK | ChoreEventType.OE_UNSOL_CXL:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_ACKED,
                                                ChoreStatusType.OE_UNACK, ChoreStatusType.OE_FILLED,
                                                ChoreStatusType.OE_AMD_DN_UNACKED,
                                                ChoreStatusType.OE_AMD_UP_UNACKED, ChoreStatusType.DOD])
                    if chore_snapshot is not None and chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                        return (True,)  # CXL Ack detected after CXL-ACK - no further processing needed
                    if chore_snapshot is not None:
                        return await self._handle_chore_dod(chore_journal_obj, chore_snapshot)

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_CXL_INT_REJ | ChoreEventType.OE_CXL_BRK_REJ | ChoreEventType.OE_CXL_EXH_REJ:
                # reverting the state of chore_snapshot after receiving cxl reject

                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = await self._check_state_and_get_chore_snapshot_obj(
                        chore_journal_obj, [ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_FILLED])
                    if chore_snapshot is not None:
                        if chore_snapshot.chore_brief.qty > chore_snapshot.filled_qty:
                            last_3_chore_journals_from_chore_id = \
                                await (self.derived_class_type.underlying_read_chore_journal_http(
                                    get_last_n_chore_journals_from_chore_id(
                                        chore_journal_obj.chore.chore_id, 3),
                                    self.get_generic_read_route()))
                            if last_3_chore_journals_from_chore_id:
                                if (last_3_chore_journals_from_chore_id[0].chore_event in
                                        [ChoreEventType.OE_CXL_INT_REJ,
                                         ChoreEventType.OE_CXL_BRK_REJ,
                                         ChoreEventType.OE_CXL_EXH_REJ]):
                                    if last_3_chore_journals_from_chore_id[-1].chore_event == ChoreEventType.OE_NEW:
                                        chore_status = ChoreStatusType.OE_UNACK
                                    elif last_3_chore_journals_from_chore_id[-1].chore_event == ChoreEventType.OE_ACK:
                                        chore_status = ChoreStatusType.OE_ACKED
                                    else:
                                        err_str_ = ("3rd chore journal from chore_journal of status OE_CXL_INT_REJ "
                                                    "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, must be"
                                                    "of status OE_ACK or OE_UNACK, received last 3 chore_journals "
                                                    f"{last_3_chore_journals_from_chore_id = }, "
                                                    f"chore_journal_key: "
                                                    f"{self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}")
                                        logging.error(err_str_)
                                        return None
                                else:
                                    err_str_ = ("Recent chore journal must be of status OE_CXL_INT_REJ "
                                                "or OE_CXL_BRK_REJ or OE_CXL_EXH_REJ, received last 3 "
                                                "chore_journals {last_3_chore_journals_from_chore_id}, "
                                                f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}")
                                    logging.error(err_str_)
                                    return None
                            else:
                                err_str_ = f"Received empty list while fetching last 3 chore_journals for " \
                                           f"{chore_journal_obj.chore.chore_id = }, " \
                                           f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}"
                                logging.error(err_str_)
                                return None
                        elif chore_snapshot.chore_brief.qty < chore_snapshot.filled_qty:
                            chore_status = ChoreStatusType.OE_OVER_FILLED
                        else:
                            chore_status = ChoreStatusType.OE_FILLED

                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.chore_status = chore_status
                        updated_chore_snapshot = \
                            await (self.derived_class_type.
                                   underlying_update_chore_snapshot_http(chore_snapshot))

                        return await self.handle_post_chore_snapshot_update_tasks_for_cxl_rej_chore_journal(
                            chore_journal_obj, updated_chore_snapshot)
                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_INT_REJ | ChoreEventType.OE_BRK_REJ | ChoreEventType.OE_EXH_REJ:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED])
                    if chore_snapshot is not None:
                        chore_brief = chore_snapshot.chore_brief
                        if chore_brief.text:
                            chore_brief.text.extend(chore_journal_obj.chore.text)
                        else:
                            chore_brief.text = chore_journal_obj.chore.text
                        cxled_qty = int(chore_snapshot.chore_brief.qty - chore_snapshot.filled_qty)
                        cxled_notional = \
                            chore_snapshot.cxled_qty * self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                       chore_snapshot.chore_brief.security.sec_id)
                        avg_cxled_px = \
                            (self.get_local_px_or_notional(cxled_notional, chore_snapshot.chore_brief.security.sec_id) /
                             cxled_qty) if cxled_qty != 0 else 0

                        chore_snapshot.chore_brief = chore_brief
                        chore_snapshot.cxled_qty = cxled_qty
                        chore_snapshot.cxled_notional = cxled_notional
                        chore_snapshot.avg_cxled_px = avg_cxled_px
                        chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                        chore_snapshot.chore_status = ChoreStatusType.OE_DOD
                        chore_snapshot = \
                            await (self.derived_class_type.
                                   underlying_update_chore_snapshot_http(chore_snapshot))
                        return await self.handle_post_chore_snapshot_update_tasks_for_int_rej_chore_journal(
                            chore_journal_obj, chore_snapshot)
                        # else not require_create_update_symbol_side_snapshot_from_chore_journald:
                        # if symbol_side_snapshot is None then it means some error occurred in
                        # _create_update_symbol_side_snapshot_from_chore_journal which would have
                        # got added to alert already
                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_LAPSE:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = await self._check_state_and_get_chore_snapshot_obj(
                        chore_journal_obj, [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED,
                                            ChoreStatusType.OE_AMD_DN_UNACKED,
                                            ChoreStatusType.OE_AMD_UP_UNACKED, ChoreStatusType.OE_CXL_UNACK])
                    if chore_snapshot is not None:
                        lapsed_qty = chore_journal_obj.chore.qty
                        # if no qty is specified then canceling remaining complete qty for chore
                        if not lapsed_qty:
                            return await self._handle_chore_dod(chore_journal_obj, chore_snapshot, is_lapse_call=True)
                        else:
                            # avoiding any lapse qty greater than chore qty
                            if lapsed_qty > chore_snapshot.chore_brief.qty:
                                logging.critical(f"Unexpected: Lapse qty can't be greater than chore_qty - putting "
                                                 f"plan to DOD state, {chore_journal_obj.chore.chore_id=}, "
                                                 f"lapse_qty: {chore_journal_obj.chore.qty}, "
                                                 f"chore_qty: {chore_snapshot.chore_brief.qty}")
                                # Passing chore_journal with passing OE_CXL_ACK as event so that all models
                                # later are handled as DOD handling
                                chore_journal_obj.chore_event = ChoreEventType.OE_CXL_ACK
                                return await self._handle_chore_dod(chore_journal_obj, chore_snapshot)

                            # avoiding any lapse qty greater than unfilled qty
                            unfilled_qty = self.get_open_qty(chore_snapshot)
                            if lapsed_qty > unfilled_qty:
                                logging.critical("Unexpected: Lapse qty can't be greater than unfilled qty - putting "
                                                 f"plan to DOD state, {chore_journal_obj.chore.chore_id=}, "
                                                 f"lapse_qty: {chore_journal_obj.chore.qty}, "
                                                 f"unfilled_qty: {unfilled_qty}")
                                # Passing chore_journal with passing OE_CXL_ACK as event so that all models
                                # later are handled as DOD handling
                                chore_journal_obj.chore_event = ChoreEventType.OE_CXL_ACK
                                return await self._handle_chore_dod(chore_journal_obj, chore_snapshot)

                            # handling partial cxl that got lapsed
                            if chore_snapshot.total_lapsed_qty is None:
                                chore_snapshot.total_lapsed_qty = 0
                            chore_snapshot.total_lapsed_qty += lapsed_qty
                            chore_snapshot.last_lapsed_qty = lapsed_qty

                            chore_snapshot.cxled_qty += lapsed_qty
                            removed_notional = (lapsed_qty *
                                                self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                chore_snapshot.chore_brief.security.sec_id))
                            chore_snapshot.cxled_notional += removed_notional
                            chore_snapshot.avg_cxled_px = (
                                (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                               chore_snapshot.chore_brief.security.sec_id) /
                                 chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                            # computing unfilled_qty post chore_snapshot obj values update to find status
                            unfilled_qty = self.get_open_qty(chore_snapshot)
                            if unfilled_qty == 0:
                                chore_snapshot.chore_status = ChoreStatusType.OE_DOD
                            # else not required: keeping same status

                            chore_snapshot.last_update_date_time = DateTime.utcnow()
                            chore_snapshot = await (self.derived_class_type.
                                                    underlying_update_chore_snapshot_http(chore_snapshot))
                            return await self.handle_post_chore_snapshot_update_tasks_for_lapse_chore_journal(
                                chore_journal_obj, chore_snapshot)

                    # else not required: none returned object signifies there was something wrong in
                    # _check_state_and_get_chore_snapshot_obj and hence would have been added to alert already

            case ChoreEventType.OE_AMD_DN_UNACK | ChoreEventType.OE_AMD_UP_UNACK:
                if not chore_journal_obj.chore.qty and not chore_journal_obj.chore.px:
                    logging.error("Unexpected: no amend qty or px found in requested amend chore_journal - "
                                  f"ignoring this amend request, amend_qty: {chore_journal_obj.chore.qty}, "
                                  f"amend_px: {chore_journal_obj.chore.px};;; {chore_journal_obj=}")
                    return

                # amend changes are applied to chore in unack state immediately if chore is risky and if chore
                # is non-risky then changes are applied on amend_ack
                # For BUY: chore is risky if chore qty or px is increased to higher value else it is non-risky
                # For SELL: chore is risky if chore qty or px is decreased to lower value else it is non-risky
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_ACKED])

                    if chore_snapshot is not None:
                        if chore_journal_obj.chore_event == ChoreEventType.OE_AMD_DN_UNACK:
                            amend_dn_qty = chore_journal_obj.chore.qty
                            amend_dn_px = chore_journal_obj.chore.px

                            open_qty = self.get_open_qty(chore_snapshot)
                            if amend_dn_qty is not None:
                                if open_qty < amend_dn_qty:
                                    logging.error("Unexpected: Amend qty is higher than open qty - ignoring is "
                                                  f"amend request, amend_qty: {chore_journal_obj.chore.qty}, "
                                                  f"open_qty: {open_qty};;; "
                                                  f"amend_dn_unack chore_journal: {chore_journal_obj}, "
                                                  f"chore_snapshot {chore_snapshot}")
                                    return None

                            # amend dn is risky in SELL side and non-risky in BUY
                            # Risky side will be amended right away and non-risky side will be amended on AMD_ACK
                            if chore_snapshot.chore_brief.side == Side.SELL:
                                # AMD: when qty is amended down then, qty that is amended dn gets cxled and
                                # chore qty stays same
                                if amend_dn_qty:
                                    chore_snapshot.total_amend_dn_qty += amend_dn_qty

                                    removed_notional = (amend_dn_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                    chore_snapshot.cxled_qty += amend_dn_qty
                                    chore_snapshot.cxled_notional += removed_notional
                                    chore_snapshot.avg_cxled_px = (
                                        (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                       chore_snapshot.chore_brief.security.sec_id) /
                                         chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                                if amend_dn_px:
                                    chore_snapshot.chore_brief.px -= amend_dn_px

                                    chore_snapshot.chore_brief.chore_notional = (
                                            chore_snapshot.chore_brief.qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id))

                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                # updating fields required to other models to be updated once chore_snapshot is updated
                                if amend_dn_px:
                                    chore_snapshot.pending_amend_dn_px = amend_dn_px
                                if amend_dn_qty:
                                    chore_snapshot.pending_amend_dn_qty = amend_dn_qty

                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                        chore_journal_obj, chore_snapshot, chore_journal_obj.chore_event)

                            else:
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                # updating fields required to other models to be updated once chore_snapshot is updated
                                if amend_dn_px:
                                    chore_snapshot.pending_amend_dn_px = amend_dn_px
                                if amend_dn_qty:
                                    chore_snapshot.pending_amend_dn_qty = amend_dn_qty
                                chore_snapshot.chore_status = ChoreStatusType.OE_AMD_DN_UNACKED
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_non_risky_amend_unack_chore_journal(chore_journal_obj, updated_chore_snapshot)

                        else:
                            amend_up_qty = chore_journal_obj.chore.qty
                            amend_up_px = chore_journal_obj.chore.px

                            # amend up is risky in BUY side and non-risky in SELL
                            # Risky side will be amended right away and non-risky side will be amended on AMD_ACK
                            if chore_snapshot.chore_brief.side == Side.BUY:
                                # AMD: when qty is amended up then, amend_qty is increased to chore qty
                                if amend_up_qty:
                                    chore_snapshot.chore_brief.qty += amend_up_qty
                                    chore_snapshot.total_amend_up_qty += amend_up_qty
                                if amend_up_px:
                                    chore_snapshot.chore_brief.px += amend_up_px

                                chore_snapshot.chore_brief.chore_notional = (
                                        chore_snapshot.chore_brief.qty *
                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                        chore_snapshot.chore_brief.security.sec_id))

                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                # updating fields required to other models to be updated once chore_snapshot is updated
                                if amend_up_px:
                                    chore_snapshot.pending_amend_up_px = amend_up_px
                                if amend_up_qty:
                                    chore_snapshot.pending_amend_up_qty = amend_up_qty

                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                    chore_journal_obj, chore_snapshot, chore_journal_obj.chore_event)

                            else:
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                # updating fields required to other models to be updated once chore_snapshot is updated
                                if amend_up_px:
                                    chore_snapshot.pending_amend_up_px = amend_up_px
                                if amend_up_qty:
                                    chore_snapshot.pending_amend_up_qty = amend_up_qty
                                chore_snapshot.chore_status = ChoreStatusType.OE_AMD_UP_UNACKED
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_non_risky_amend_unack_chore_journal(chore_journal_obj, updated_chore_snapshot)
                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already

            case ChoreEventType.OE_AMD_ACK:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot: ChoreSnapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_AMD_DN_UNACKED,
                                                ChoreStatusType.OE_AMD_UP_UNACKED,
                                                ChoreStatusType.OE_FILLED,
                                                ChoreStatusType.OE_OVER_FILLED,
                                                ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_DOD])

                    # Non-risky amend cases will be updated in AMD_ACK
                    # Risky cases already get updated at amend unack event only
                    if chore_snapshot is not None:
                        pending_amend_event = self.pending_amend_type(chore_journal_obj, chore_snapshot)
                        if pending_amend_event == ChoreEventType.OE_AMD_DN_UNACK:
                            amend_dn_qty = chore_snapshot.pending_amend_dn_qty
                            amend_dn_px = chore_snapshot.pending_amend_dn_px

                            # amend dn is risky in SELL side and non-risky in BUY
                            if chore_snapshot.chore_brief.side == Side.BUY:
                                # AMD: when qty is amended down then, qty that is amended dn gets cxled and
                                # chore qty stays same
                                if amend_dn_qty:
                                    chore_snapshot.total_amend_dn_qty += amend_dn_qty

                                    removed_notional = (amend_dn_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                    chore_snapshot.cxled_qty += amend_dn_qty
                                    chore_snapshot.cxled_notional += removed_notional
                                    chore_snapshot.avg_cxled_px = (
                                        (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                       chore_snapshot.chore_brief.security.sec_id) /
                                         chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                                if amend_dn_px:
                                    chore_snapshot.chore_brief.px -= amend_dn_px

                                    chore_snapshot.chore_brief.chore_notional = (
                                            chore_snapshot.chore_brief.qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id))
                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                        chore_journal_obj, chore_snapshot, pending_amend_event)

                            else:
                                # since if amend was already applied in amend unack event only for risky case - no
                                # further compute updates are required
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                if (not chore_has_terminal_state(chore_snapshot) and
                                        chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK):
                                    chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                                # else not required: if chore has terminal state or has cxl_unack state then
                                # keeping same state
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_risky_amend_ack_chore_journal(chore_journal_obj, updated_chore_snapshot)

                        else:
                            amend_up_qty = chore_snapshot.pending_amend_up_qty
                            amend_up_px = chore_snapshot.pending_amend_up_px

                            # amend up is risky in BUY side and non-risky in SELL
                            if chore_snapshot.chore_brief.side == Side.SELL:
                                # AMD: when qty is amended up then, amend_qty is increased to chore qty
                                if amend_up_qty:
                                    chore_snapshot.chore_brief.qty += amend_up_qty
                                    chore_snapshot.total_amend_up_qty += amend_up_qty

                                    # If chore is already DOD or OVER_CXLED at the time of AMD_ACK event - chore
                                    # cannot be reverted to non-terminal state so putting any amended up qty which
                                    # is added to chore_qty to cxled_qty
                                    if chore_snapshot.chore_status in [ChoreStatusType.OE_DOD,
                                                                       ChoreStatusType.OE_OVER_CXLED]:
                                        # putting any qty amended up post terminal state to over_cxled
                                        chore_snapshot.cxled_qty += amend_up_qty
                                        removed_notional = (amend_up_qty *
                                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                                            chore_snapshot.chore_brief.security.sec_id))
                                        chore_snapshot.cxled_notional += removed_notional
                                        chore_snapshot.avg_cxled_px = (
                                            (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                           chore_snapshot.chore_brief.security.sec_id) /
                                             chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                                if amend_up_px:
                                    chore_snapshot.chore_brief.px += amend_up_px

                                chore_snapshot.chore_brief.chore_notional = (
                                        chore_snapshot.chore_brief.qty *
                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                        chore_snapshot.chore_brief.security.sec_id))

                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                        chore_journal_obj, chore_snapshot, pending_amend_event)

                            else:
                                # since if amend was already applied in amend unack event only for risky case - no
                                # further compute updates are required
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                if (not chore_has_terminal_state(chore_snapshot) and
                                        chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK):
                                    chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                                # else not required: if chore has terminal state or has cxl_unack state then
                                # keeping same state
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_risky_amend_ack_chore_journal(chore_journal_obj, updated_chore_snapshot)
                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already

            case ChoreEventType.OE_AMD_REJ:
                async with ChoreSnapshot.reentrant_lock:
                    chore_snapshot: ChoreSnapshot = \
                        await self._check_state_and_get_chore_snapshot_obj(
                            chore_journal_obj, [ChoreStatusType.OE_AMD_DN_UNACKED,
                                                ChoreStatusType.OE_AMD_UP_UNACKED, ChoreStatusType.OE_FILLED,
                                                ChoreStatusType.OE_OVER_FILLED,
                                                ChoreStatusType.OE_CXL_UNACK, ChoreStatusType.OE_DOD])
                    if chore_snapshot is not None:
                        if chore_snapshot.chore_status == ChoreStatusType.OE_DOD:
                            logging.error(f"Received AMD_REJ post chore DOD on chore_id: "
                                          f"{chore_snapshot.chore_brief.chore_id} - ignoring this amend chore_journal "
                                          f"and chore will stay unchanged;;; amd_rej {chore_journal_obj=}, "
                                          f"{chore_snapshot=}")
                            return None

                        pending_amend_event = self.pending_amend_type(chore_journal_obj, chore_snapshot)
                        if pending_amend_event == ChoreEventType.OE_AMD_DN_UNACK:
                            amend_dn_qty = chore_snapshot.pending_amend_dn_qty
                            amend_dn_px = chore_snapshot.pending_amend_dn_px

                            # amend dn is risky in SELL side and non-risky in BUY
                            if chore_snapshot.chore_brief.side == Side.SELL:

                                # AMD: when qty is amended down then, qty that is amended dn gets cxled and
                                # chore qty stays same

                                if amend_dn_qty:
                                    chore_snapshot.total_amend_dn_qty -= amend_dn_qty

                                    removed_notional = (amend_dn_qty *
                                                        self.get_usd_px(chore_snapshot.chore_brief.px+amend_dn_px,
                                                                        chore_snapshot.chore_brief.security.sec_id))

                                    chore_snapshot.cxled_qty -= amend_dn_qty
                                    chore_snapshot.cxled_notional -= removed_notional
                                    chore_snapshot.avg_cxled_px = (
                                        (self.get_local_px_or_notional(chore_snapshot.cxled_notional,
                                                                       chore_snapshot.chore_brief.security.sec_id) /
                                         chore_snapshot.cxled_qty) if chore_snapshot.cxled_qty != 0 else 0)

                                if amend_dn_px:
                                    chore_snapshot.chore_brief.px += amend_dn_px

                                    chore_snapshot.chore_brief.chore_notional = (
                                            chore_snapshot.chore_brief.qty *
                                            self.get_usd_px(chore_snapshot.chore_brief.px,
                                                            chore_snapshot.chore_brief.security.sec_id))

                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                        chore_journal_obj, chore_snapshot, pending_amend_event,
                                        is_amend_rej_call=True)

                            else:
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                if (not chore_has_terminal_state(chore_snapshot) and
                                        chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK):
                                    chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                                # else not required: if chore has terminal state or has cxl_unack state then
                                # keeping same state
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_non_risky_amend_rej_chore_journal(chore_journal_obj, updated_chore_snapshot)

                        else:
                            amend_up_qty = chore_snapshot.pending_amend_up_qty
                            amend_up_px = chore_snapshot.pending_amend_up_px

                            # amend up is risky in BUY side and non-risky in SELL
                            if chore_snapshot.chore_brief.side == Side.BUY:

                                # AMD: when qty is amended up then, chore qty is updated to amended qty
                                if amend_up_qty:
                                    chore_snapshot.chore_brief.qty -= amend_up_qty
                                    chore_snapshot.total_amend_up_qty -= amend_up_qty

                                if amend_up_px:
                                    chore_snapshot.chore_brief.px -= amend_up_px

                                chore_snapshot.chore_brief.chore_notional = (
                                        chore_snapshot.chore_brief.qty *
                                        self.get_usd_px(chore_snapshot.chore_brief.px,
                                                        chore_snapshot.chore_brief.security.sec_id))

                                return await self.handle_model_updates_post_chore_journal_amend_applied(
                                        chore_journal_obj, chore_snapshot, pending_amend_event,
                                        is_amend_rej_call=True)

                            else:
                                chore_snapshot.last_update_date_time = chore_journal_obj.chore_event_date_time
                                # updating all pending amend fields to 0
                                self.set_default_values_to_pend_amend_fields(chore_snapshot)
                                if (not chore_has_terminal_state(chore_snapshot) and
                                        chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK):
                                    chore_snapshot.chore_status = ChoreStatusType.OE_ACKED
                                # else not required: if chore has terminal state or has cxl_unack state then
                                # keeping same state
                                updated_chore_snapshot = (
                                    await self.derived_class_type.
                                    underlying_update_chore_snapshot_http(chore_snapshot))
                                return await self.handle_post_chore_snapshot_update_tasks_for_non_risky_amend_rej_chore_journal(chore_journal_obj, updated_chore_snapshot)

                    # else not required: Ignoring this update since none returned object signifies
                    # there was something wrong in _check_state_and_get_chore_snapshot_obj and
                    # hence would have been added to alert already
            case other_:
                chore_jpurnal_key = self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)
                err_str_ = f"Unsupported Chore event - {other_} in {chore_jpurnal_key=};;;{chore_journal_obj=}"
                logging.error(err_str_)
        # avoiding any update for all cases that end up here
        return None

    def get_chore_status_post_amend_applied(
            self, chore_journal: ChoreJournal, chore_snapshot: ChoreSnapshot, amend_direction: ChoreEventType,
            last_chore_status: ChoreStatusType) -> ChoreStatusType | None:
        # risky
        # * dn
        # - open > 0 -> OE_AMD_DN_UNACKED
        # - open = 0 -> DOD
        # - open < 0 -> not possible
        # * up
        # - open > 0 -> OE_AMD_UP_UNACKED
        # - open = 0 -> not possible
        # - open < 0 -> not possible
        # non-risky
        # * dn
        # - open > 0 -> ACK
        # - open = 0 -> DOD
        # - open < 0 -> OVER_CXL
        # * up
        # - open > 0 -> ACK
        # - open = 0 -> DOD
        # - open < 0 -> if over-filled then ovr-filled else over-cxl

        chore_event = chore_journal.chore_event
        open_qty = self.derived_class_type.get_open_qty(chore_snapshot)
        if chore_event != ChoreEventType.OE_AMD_ACK:
            # risky case
            if amend_direction == ChoreEventType.OE_AMD_DN_UNACK:
                # Amend DN
                if open_qty > 0:
                    return ChoreStatusType.OE_AMD_DN_UNACKED
                elif open_qty == 0:
                    # If chore qty becomes zero post amend dn then chore is considered DOD
                    logging.warning(
                        f"Received {chore_event} for amend qty which makes chore DOD, before status was "
                        f"{last_chore_status} - applying amend and putting "
                        f"chore as DOD, chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                        f"{chore_journal=}, {chore_snapshot=}")
                    return ChoreStatusType.OE_DOD
                else:
                    logging.error("Can't find chore_status, keeping last status - open_qty can't be negative post "
                                  "risky amend dn since we don't amend dn any qty lower than available, likely bug "
                                  f"in blocking logic;;; {chore_snapshot=}")
                    return None
            else:
                # Amend UP
                if open_qty > 0:
                    return ChoreStatusType.OE_AMD_UP_UNACKED
                elif open_qty == 0:
                    logging.error("Can't find chore_status, keeping last status - open_qty can't be zero post risky "
                                  "amend up since chore status must always be ACK before risky amend up and open_qty "
                                  f"can never be zero by adding any qty;;; {chore_snapshot=}")
                    return None
                else:
                    logging.error("Can't find chore_status, keeping last status - open_qty can't be negative post "
                                  "risky amend up since chore status must always be ACK before risky amend up and "
                                  f"open_qty can never be negative by adding any qty;;; {chore_snapshot=}")
                    return None
        else:
            # non risky case
            if amend_direction == ChoreEventType.OE_AMD_DN_UNACK:
                # Amend DN
                if open_qty > 0:
                    if last_chore_status == ChoreStatusType.OE_CXL_UNACK:
                        return ChoreStatusType.OE_CXL_UNACK
                    else:
                        return ChoreStatusType.OE_ACKED
                elif open_qty == 0:
                    # If chore qty becomes zero post amend dn then chore is considered DOD
                    logging.warning(
                        f"Received {chore_event} for amend qty which makes chore DOD, before status was "
                        f"{last_chore_status} - applying amend and putting "
                        f"chore as DOD, chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                        f"{chore_journal=}, {chore_snapshot=}")
                    return ChoreStatusType.OE_DOD
                else:
                    # If chore qty becomes negative post amend dn then chore must be in terminal state already before
                    # non-risky amend dn - any further amend dn will be added to extra cxled
                    logging.warning(f"Received {chore_event} for amend qty which makes chore OVER_CXLED to "
                                    f"chore which was {last_chore_status} before - amend applied and "
                                    f"putting plan to PAUSE , chore_journal_key: "
                                    f"{self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                    f"{chore_journal=}, {chore_snapshot=}")
                    self.pause_plan()
                    return ChoreStatusType.OE_OVER_CXLED
            else:
                # Amend UP
                if open_qty > 0:
                    if last_chore_status == ChoreStatusType.OE_CXL_UNACK:
                        return ChoreStatusType.OE_CXL_UNACK
                    else:
                        if last_chore_status == ChoreStatusType.OE_FILLED:
                            logging.warning(f"Received {chore_event} for amend qty which makes chore back to ACKED "
                                            f"which was FILLED before amend, "
                                            f"chore_id: {chore_snapshot.chore_brief.chore_id}, "
                                            f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                            f"{chore_journal=}, {chore_snapshot=}")
                        elif last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                            logging.warning(f"Received {chore_event} for amend qty which makes chore back to ACKED "
                                            f"which was OVER_FILLED before amend, chore_id: "
                                            f"{chore_snapshot.chore_brief.chore_id} - setting plan back to ACTIVE"
                                            f" and applying amend, also ignore OVERFILLED ALERT for this chore"
                                            f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                            f"{chore_journal=}, {chore_snapshot=}")
                            self.unpause_plan()
                        return ChoreStatusType.OE_ACKED
                elif open_qty == 0:
                    # chore qty can be zero in below chore status cases
                    # if status was DOD - whatever qty is amended up is also put in cxled qty so overall no impact
                    # if status was OVER_CXLED - whatever qty was over-cxled got
                    #                            compensated by amending up chore qty so chore became DOD
                    # if status was OVER_FILLED - whatever qty was over-filled got
                    #                             compensated by amending up chore qty so chore became FILLED
                    if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                        logging.warning(f"Received {chore_event} for amend qty which makes chore FILLED "
                                        f"which was OVER_FILLED before amend, chore_id: "
                                        f"{chore_snapshot.chore_brief.chore_id} - setting plan back to ACTIVE"
                                        f" and applying amend, also ignore OVERFILLED ALERT for this chore"
                                        f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                        f"{chore_journal=}, {chore_snapshot=}")
                        self.unpause_plan()
                        return ChoreStatusType.OE_FILLED
                    else:
                        logging.warning(
                            f"Received {chore_event} for amend qty which makes chore DOD, before status was "
                            f"{last_chore_status} - applying amend and putting "
                            f"chore as DOD, chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                            f"{chore_journal=}, {chore_snapshot=}")
                        return ChoreStatusType.OE_DOD
                else:
                    # amend up also couldn't make open_qty non-negative so keeping same status on chore
                    return last_chore_status


    def pause_plan(self):
        pass

    def unpause_plan(self):
        pass

    def get_chore_status_post_amend_rej(
            self, chore_journal: ChoreJournal, chore_snapshot: ChoreSnapshot, amend_direction: ChoreEventType,
            last_chore_status: ChoreStatusType) -> ChoreStatusType:
        # * dn
        # - open > 0 -> ACK
        # - open = 0 -> if dod: dod else filled
        # - open < 0 -> OVER_FILLED
        # * up
        # - open > 0 -> ACK
        # - open = 0 -> if dod: dod else filled
        # - open < 0 -> OVER_FILLED

        open_qty = self.derived_class_type.get_open_qty(chore_snapshot)
        if amend_direction == ChoreEventType.OE_AMD_DN_UNACK:
            # Amend DN
            if open_qty > 0:
                if last_chore_status == ChoreStatusType.OE_CXL_UNACK:
                    return ChoreStatusType.OE_CXL_UNACK
                else:
                    log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                               f"{last_chore_status} before amend applied - status post amd_rej applied: "
                               f"{ChoreStatusType.OE_ACKED}")
                    if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                        log_str += (" - UNPAUSING plan and applying amend rollback, "
                                    f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                    f"{chore_journal=}, {chore_snapshot=}")
                        logging.warning(log_str)
                        self.unpause_plan()
                    elif last_chore_status == ChoreStatusType.OE_FILLED:
                        log_str += (f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                    f"{chore_journal=}, {chore_snapshot=}")
                        logging.warning(log_str)
                    # else not required: if chore was already acked then no need to notify as alert

                    return ChoreStatusType.OE_ACKED
            elif open_qty == 0:
                if last_chore_status == ChoreStatusType.OE_DOD:
                    return ChoreStatusType.OE_DOD
                else:
                    if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                        log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                                   f"{last_chore_status} before amend applied - status post amd_rej applied: "
                                   f"{ChoreStatusType.OE_ACKED}")
                        log_str += (" - UNPAUSING plan and applying amend rollback, "
                                    f"chore_journal_key: {self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                    f"{chore_journal=}, {chore_snapshot=}")
                        logging.warning(log_str)
                        self.unpause_plan()
                    else:
                        log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                                   f"{last_chore_status} before amend applied - status post amd_rej applied: "
                                   f"{ChoreStatusType.OE_FILLED}, chore_journal_key: "
                                   f"{self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; {chore_journal=}, {chore_snapshot=}")
                        logging.warning(log_str)
                    return ChoreStatusType.OE_FILLED
            else:
                return last_chore_status
        else:
            # Amend UP
            if open_qty > 0:
                if last_chore_status == ChoreStatusType.OE_CXL_UNACK:
                    return ChoreStatusType.OE_CXL_UNACK
                else:
                    return ChoreStatusType.OE_ACKED
            elif open_qty == 0:
                if last_chore_status == ChoreStatusType.OE_DOD:
                    return ChoreStatusType.OE_DOD
                else:
                    log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                               f"{last_chore_status} before amend applied - status post amd_rej applied: "
                               f"{ChoreStatusType.OE_FILLED}, chore_journal_key: "
                               f"{self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; {chore_journal=}, {chore_snapshot=}")
                    logging.warning(log_str)
                    return ChoreStatusType.OE_FILLED
            else:
                log_str = (f"Reverted amend changes post receiving OE_AMD_REJ on chore that had status "
                           f"{last_chore_status} before amend applied - status post amd_rej applied: "
                           f"{ChoreStatusType.OE_OVER_FILLED}")
                if last_chore_status == ChoreStatusType.OE_OVER_FILLED:
                    log_str += (" - plan must be at PAUSE already and "
                                f"applying amend rollback, chore_journal_key: "
                                f"{self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                f"{chore_journal=}, {chore_snapshot=}")
                    logging.warning(log_str)
                else:
                    log_str += (" - putting plan to pause and applying amend rollback, chore_journal_key: "
                                f"{self.derived_class_type.get_chore_journal_log_key(chore_journal)};;; "
                                f"{chore_journal=}, {chore_snapshot=}")
                    logging.warning(log_str)
                    self.pause_plan()
                return ChoreStatusType.OE_OVER_FILLED

    def pending_amend_type(self, chore_journal: ChoreJournal, chore_snapshot: ChoreSnapshot) -> ChoreEventType | None:
        if chore_journal.chore_event == ChoreEventType.OE_AMD_DN_UNACK:
            chore_event = ChoreEventType.OE_AMD_DN_UNACK
        elif chore_journal.chore_event == ChoreEventType.OE_AMD_UP_UNACK:
            chore_event = ChoreEventType.OE_AMD_UP_UNACK
        else:
            # if event is AMD_ACK then checking what all fields are updated by amend unack event - for
            # amend dn only fields related to amend_dn will be updated rest will stay 0 by default and same goes
            # for amend up case
            if ((chore_snapshot.pending_amend_dn_qty or chore_snapshot.pending_amend_dn_px) and
                    not chore_snapshot.pending_amend_up_qty and not chore_snapshot.pending_amend_up_px):
                return ChoreEventType.OE_AMD_DN_UNACK
            elif (not chore_snapshot.pending_amend_dn_qty and not chore_snapshot.pending_amend_dn_px and
                  (chore_snapshot.pending_amend_up_qty or chore_snapshot.pending_amend_up_px)):
                return ChoreEventType.OE_AMD_UP_UNACK
            else:
                logging.error("Unexpected: Found both dn and up pending amend fields in chore_snapshot having values, "
                              "ideally either dn is updated or up is updated - can't find which type of amend is it, "
                              f"ignoring all computes post chore_snapshot update;;; {chore_snapshot=}")
                return None
        return chore_event

    async def _check_state_and_get_chore_snapshot_obj(self, chore_journal_obj: ChoreJournal,
                                                      expected_status_list: List[str]) -> ChoreSnapshot | None:
        """
        Checks if chore_snapshot holding chore_id of passed chore_journal has expected status
        from provided statuses list and then returns that chore_snapshot
        """
        chore_snapshot_obj = self.plan_cache.get_chore_snapshot_from_chore_id(chore_journal_obj.chore.chore_id)

        if chore_snapshot_obj is not None:
            if chore_snapshot_obj.chore_status in expected_status_list:
                return chore_snapshot_obj
            else:
                ord_journal_key: str = self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)
                ord_snapshot_key: str = self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)
                err_str_: str = (f"Unexpected: Received chore_journal of event: {chore_journal_obj.chore_event} on "
                                 f"chore of chore_snapshot status: {chore_snapshot_obj.chore_status}, expected "
                                 f"chore_statuses for chore_journal event {chore_journal_obj.chore_event} is "
                                 f"{expected_status_list=}, {ord_journal_key=}, {ord_snapshot_key=};;; "
                                 f"{chore_journal_obj=}, {chore_snapshot_obj=}")
                logging.error(err_str_)
                return None
        else:
            logging.error(f"unexpected: _check_state_and_get_chore_snapshot_obj got chore_snapshot_obj as None;;;"
                          f"{self.derived_class_type.get_chore_journal_log_key(chore_journal_obj)}; {chore_journal_obj=}")
            return None

    ##############################
    # Fills Journal Update Methods
    ##############################

    async def handle_create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_fills_journal_pre not ready - service is not initialized yet, " \
                       f"fills_journal_key: " \
                       f"{self.derived_class_type.get_fills_journal_log_key(fills_journal_obj)}"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)
        # Updating notional field in fills journal
        fills_journal_obj.fill_notional = \
            self.get_usd_px(fills_journal_obj.fill_px, fills_journal_obj.fill_symbol) * fills_journal_obj.fill_qty

    async def handle_post_chore_snapshot_tasks_for_fills(
            self, fills_journal_obj: FillsJournal, chore_snapshot_obj: ChoreSnapshot,
            received_fill_after_dod: bool):
        return chore_snapshot_obj

    async def _apply_fill_update_in_chore_snapshot(
            self, fills_journal_obj: FillsJournal):
        res = self.update_chore_snapshot_pre_checks()
        if not res:  # returning None if some check fails
            return None

        async with (ChoreSnapshot.reentrant_lock):  # for read-write atomicity
            chore_snapshot_obj = self.plan_cache.get_chore_snapshot_from_chore_id(fills_journal_obj.chore_id)

            if chore_snapshot_obj is not None:
                if chore_snapshot_obj.chore_status in [ChoreStatusType.OE_UNACK, ChoreStatusType.OE_ACKED,
                                                       ChoreStatusType.OE_AMD_DN_UNACKED,
                                                       ChoreStatusType.OE_AMD_UP_UNACKED,
                                                       ChoreStatusType.OE_DOD, ChoreStatusType.OE_CXL_UNACK]:
                    received_fill_after_dod = False
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_DOD:
                        received_fill_after_dod = True

                    updated_total_filled_qty: int
                    if (total_filled_qty := chore_snapshot_obj.filled_qty) is not None:
                        updated_total_filled_qty = int(total_filled_qty + fills_journal_obj.fill_qty)
                    else:
                        updated_total_filled_qty = int(fills_journal_obj.fill_qty)
                    received_fill_notional = fills_journal_obj.fill_notional
                    fills_before_ack = False
                    if chore_snapshot_obj.chore_status == ChoreStatusType.OE_UNACK:
                        fills_before_ack = True

                    available_qty = self.get_valid_available_fill_qty(chore_snapshot_obj)
                    if available_qty == updated_total_filled_qty:
                        pause_fulfill_post_chore_dod: bool = (
                            self.executor_config_yaml_dict.get("pause_fulfill_post_chore_dod"))
                        if received_fill_after_dod and pause_fulfill_post_chore_dod:
                            # @@@ below error log is used in specific test case for string matching - if changed here
                            # needs to be changed in test also
                            logging.critical("Unexpected: Received fill that makes chore_snapshot OE_FILLED which is "
                                             "already of state OE_DOD, ignoring this fill and putting this plan to "
                                             f"PAUSE, symbol_side_key: "
                                             f"{self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                             f";;; {fills_journal_obj=}, {chore_snapshot_obj=}")
                            self.pause_plan()
                            return None
                            # pause_plan = True
                        else:
                            if received_fill_after_dod:
                                # @@@ below error log is used in specific test case for string matching - if changed
                                # here needs to be changed in test also
                                logging.warning(
                                    "Received fill that makes chore_snapshot OE_FILLED which is "
                                    "already of state OE_DOD, symbol_side_key: "
                                    f"{self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                    f";;; {fills_journal_obj=}, {chore_snapshot_obj=}")
                                chore_snapshot_obj.cxled_qty -= int(fills_journal_obj.fill_qty)
                                chore_snapshot_obj.cxled_notional = (
                                        chore_snapshot_obj.cxled_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                                       chore_snapshot_obj.chore_brief.security.sec_id))
                                if chore_snapshot_obj.cxled_qty == 0:
                                    chore_snapshot_obj.avg_cxled_px = 0
                                else:
                                    logging.error("Unexpected: Received fill that makes chore FULFILL after DOD but "
                                                  "when fill_qty removed from cxl_qty, cxl_qty is not turning 0 ;;; "
                                                  f"fill_journal: {fills_journal_obj}, "
                                                  f"chore_journal: {chore_snapshot_obj}")

                            chore_snapshot_obj.chore_status = ChoreStatusType.OE_FILLED
                            if fills_before_ack:
                                logging.warning(f"Received fill for chore that has status: {ChoreStatusType.OE_UNACK} "
                                                f"that makes chore fulfilled, putting chore to "
                                                f"{chore_snapshot_obj.chore_status} status and applying fill")
                    elif available_qty < updated_total_filled_qty:  # OVER_FILLED
                        vacant_fill_qty = int(available_qty - chore_snapshot_obj.filled_qty)
                        non_required_received_fill_qty = fills_journal_obj.fill_qty - vacant_fill_qty

                        if received_fill_after_dod:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED which "
                                f"is already OE_DOD, {vacant_fill_qty=}, received "
                                f"{fills_journal_obj.fill_qty=}, {non_required_received_fill_qty=} "
                                f"from fills_journal_key of {fills_journal_obj.chore_id=} and "
                                f"{fills_journal_obj.id=} - putting plan to PAUSE and applying fill, "
                                f"symbol_side_key: {self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj=}, {chore_snapshot_obj=}")
                            chore_snapshot_obj.cxled_qty -= int(fills_journal_obj.fill_qty -
                                                                non_required_received_fill_qty)
                            chore_snapshot_obj.cxled_notional = (
                                    chore_snapshot_obj.cxled_qty *
                                    self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                    chore_snapshot_obj.chore_brief.security.sec_id))
                            if chore_snapshot_obj.cxled_qty == 0:
                                chore_snapshot_obj.avg_cxled_px = 0
                            else:
                                logging.error("Unexpected: Received fill that makes chore OVERFILL after DOD but "
                                              "when valid fill_qty (excluding extra fill) is removed from cxl_qty, "
                                              "cxl_qty is not turning 0 ;;; "
                                              f"fill_journal: {fills_journal_obj}, "
                                              f"chore_journal: {chore_snapshot_obj}")

                        elif fills_before_ack:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED to chore "
                                f"which is still OE_UNACK, "
                                f"{vacant_fill_qty=}, received {fills_journal_obj.fill_qty=}, "
                                f"{non_required_received_fill_qty=} "
                                f"from fills_journal_key of {fills_journal_obj.chore_id=} and "
                                f"{fills_journal_obj.id=} - putting plan to PAUSE and applying fill, "
                                f"symbol_side_key: {self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj=}, {chore_snapshot_obj=}")
                        else:
                            # @@@ below error log is used in specific test case for string matching - if changed
                            # here needs to be changed in test also
                            logging.critical(
                                f"Unexpected: Received fill that will make chore_snapshot OVER_FILLED, "
                                f"{vacant_fill_qty=}, received {fills_journal_obj.fill_qty=}, "
                                f"{non_required_received_fill_qty=} "
                                f"from fills_journal_key of {fills_journal_obj.chore_id=} and "
                                f"{fills_journal_obj.id=} - putting plan to PAUSE and applying fill, "
                                f"symbol_side_key: {self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}"
                                f";;; {fills_journal_obj=}, {chore_snapshot_obj=}")
                        chore_snapshot_obj.chore_status = ChoreStatusType.OE_OVER_FILLED
                        self.pause_plan()
                        # pause_plan = True
                    else:
                        if received_fill_after_dod:
                            chore_snapshot_obj.cxled_qty = int(chore_snapshot_obj.cxled_qty -
                                                               fills_journal_obj.fill_qty)
                            chore_snapshot_obj.cxled_notional = (
                                    chore_snapshot_obj.cxled_qty * self.get_usd_px(chore_snapshot_obj.chore_brief.px,
                                                                                   chore_snapshot_obj.chore_brief.security.sec_id))
                            chore_snapshot_obj.avg_cxled_px = \
                                (self.get_local_px_or_notional(chore_snapshot_obj.cxled_notional,
                                                               chore_snapshot_obj.chore_brief.security.sec_id) /
                                 chore_snapshot_obj.cxled_qty) if chore_snapshot_obj.cxled_qty != 0 else 0
                        elif fills_before_ack:
                            chore_snapshot_obj.chore_status = ChoreStatusType.OE_ACKED
                            logging.warning(f"Received fill for chore that has status: {ChoreStatusType.OE_UNACK}, "
                                            f"putting chore to {chore_snapshot_obj.chore_status} "
                                            f"status and applying fill")

                    if (last_filled_notional := chore_snapshot_obj.fill_notional) is not None:
                        updated_fill_notional = last_filled_notional + received_fill_notional
                    else:
                        updated_fill_notional = received_fill_notional
                    updated_avg_fill_px = \
                        (self.get_local_px_or_notional(updated_fill_notional,
                                                       fills_journal_obj.fill_symbol) / updated_total_filled_qty
                         if updated_total_filled_qty != 0 else 0)

                    chore_snapshot_obj.filled_qty = updated_total_filled_qty
                    chore_snapshot_obj.avg_fill_px = updated_avg_fill_px
                    chore_snapshot_obj.fill_notional = updated_fill_notional
                    chore_snapshot_obj.last_update_fill_qty = int(fills_journal_obj.fill_qty)
                    chore_snapshot_obj.last_update_fill_px = fills_journal_obj.fill_px
                    chore_snapshot_obj.last_update_date_time = fills_journal_obj.fill_date_time
                    chore_snapshot_obj = \
                        await (self.derived_class_type.
                               underlying_update_chore_snapshot_http(chore_snapshot_obj))
                    return await self.handle_post_chore_snapshot_tasks_for_fills(
                        fills_journal_obj, chore_snapshot_obj, received_fill_after_dod)

                    # else not require_create_update_symbol_side_snapshot_from_chore_journald: if symbol_side_snapshot
                    # is None then it means error occurred in _create_update_symbol_side_snapshot_from_chore_journal
                    # which would have got added to alert already
                elif chore_snapshot_obj.chore_status == ChoreStatusType.OE_FILLED:
                    err_str_ = (f"Unsupported - Fill received for completely filled chore_snapshot, "
                                f"chore_snapshot_key: {self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)}, "
                                f"ignoring this fill journal - putting plan to PAUSE;;; "
                                f"{fills_journal_obj=}, {chore_snapshot_obj=}")
                    logging.critical(err_str_)
                    self.pause_plan()
                else:
                    err_str_ = f"Unsupported - Fill received for chore_snapshot having status " \
                               f"{chore_snapshot_obj.chore_status}, chore_snapshot_key: " \
                               f"{self.derived_class_type.get_chore_snapshot_log_key(chore_snapshot_obj)};;; " \
                               f"{fills_journal_obj=}, {chore_snapshot_obj=}"
                    logging.error(err_str_)
            else:
                err_str_ = (f"Could not find any chore snapshot with {fills_journal_obj.chore_id=} in "
                            f"plan_cache, fill_journal_key: "
                            f"{self.derived_class_type.get_fills_journal_log_key(fills_journal_obj)}")
                logging.error(err_str_)

    ############################
    # BarteringDataManager updates
    # Note: Obj passed to bartering_data_manager gte_all_ws methods is also that which is returned by underlying call
    #       so be careful, if in get_all_ws handling it is updated it would impact obj received by caller of
    #       underlying or client
    ############################

    async def handle_partial_update_chore_journal_post(self, updated_chore_journal_obj_json: Dict[str, Any]):
        updated_chore_journal_obj = ChoreJournal.from_dict(updated_chore_journal_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_journal_get_all_ws(updated_chore_journal_obj)

    async def handle_create_chore_snapshot_post(self, chore_snapshot_obj: ChoreSnapshot):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(chore_snapshot_obj)

    async def handle_update_chore_snapshot_post(self, updated_chore_snapshot_obj: ChoreSnapshot):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(updated_chore_snapshot_obj)

    async def handle_partial_update_chore_snapshot_post(self, updated_chore_snapshot_obj_json: Dict[str, Any]):
        updated_chore_snapshot_obj = ChoreSnapshot.from_dict(updated_chore_snapshot_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_snapshot_get_all_ws(updated_chore_snapshot_obj)

    async def handle_partial_update_fills_journal_post(self, updated_fills_journal_obj_json: Dict[str, Any]):
        updated_fills_journal_obj = FillsJournal.from_dict(updated_fills_journal_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_fills_journal_get_all_ws(updated_fills_journal_obj)

    async def handle_create_new_chore_post(self, new_chore_obj: NewChore):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_new_chore_get_all_ws(deepcopy(new_chore_obj))
        SymbolCacheContainer.release_semaphore()

    async def handle_create_cancel_chore_post(self, cancel_chore_obj: CancelChore):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_cancel_chore_get_all_ws(cancel_chore_obj)
        SymbolCacheContainer.release_semaphore()

    async def handle_partial_update_cancel_chore_post(self, updated_cancel_chore_obj_json: Dict[str, Any]):
        updated_cancel_chore_obj = CancelChore.from_dict(updated_cancel_chore_obj_json)
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_cancel_chore_get_all_ws(updated_cancel_chore_obj)
        SymbolCacheContainer.release_semaphore()

    async def handle_create_symbol_overview_pre(self, symbol_overview_obj: SymbolOverview):
        return create_symbol_overview_pre_helper(self.static_data, symbol_overview_obj)

    async def handle_update_symbol_overview_pre(self, updated_symbol_overview_obj: SymbolOverview):
        stored_symbol_overview_obj = await (self.derived_class_type.
                                            underlying_read_symbol_overview_by_id_http(updated_symbol_overview_obj.id))
        return update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj,
                                                 updated_symbol_overview_obj)

    async def handle_partial_update_symbol_overview_pre(self, stored_symbol_overview_obj_json: Dict[str, Any],
                                                        updated_symbol_overview_obj_json: Dict[str, Any]):
        return partial_update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj_json,
                                                         updated_symbol_overview_obj_json)

    async def handle_create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        symbol_overview_obj.force_publish = False  # setting it false if at create is it True
        # updating symbol_cache
        self.plan_cache.handle_set_symbol_overview_in_symbol_cache(symbol_overview_obj)

        SymbolCacheContainer.release_semaphore()

    async def handle_update_symbol_overview_post(self, updated_symbol_overview_obj: SymbolOverview):
        # updating symbol_cache
        self.plan_cache.handle_set_symbol_overview_in_symbol_cache(updated_symbol_overview_obj)
        SymbolCacheContainer.release_semaphore()

    async def handle_partial_update_symbol_overview_post(self, updated_symbol_overview_obj_json: Dict[str, Any]):
        updated_symbol_overview_obj = SymbolOverview.from_dict(updated_symbol_overview_obj_json)
        # updating symbol_cache
        self.plan_cache.handle_set_symbol_overview_in_symbol_cache(updated_symbol_overview_obj)
        SymbolCacheContainer.release_semaphore()

    async def handle_create_all_symbol_overview_post(self, symbol_overview_obj_list: List[SymbolOverview]):
        # updating bartering_data_manager's plan_cache
        for symbol_overview_obj in symbol_overview_obj_list:
            symbol_overview_obj.force_publish = False  # setting it false if at create it is True
            # updating symbol_cache
            self.plan_cache.handle_set_symbol_overview_in_symbol_cache(symbol_overview_obj)
            SymbolCacheContainer.release_semaphore()
            # else not required: since symbol overview is required to make executor service ready,
            #                    will add this to plan_cache explicitly using underlying http call

    async def handle_update_all_symbol_overview_post(self, updated_symbol_overview_obj_list: List[SymbolOverview]):
        # updating bartering_data_manager's plan_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            # updating symbol_cache
            self.plan_cache.handle_set_symbol_overview_in_symbol_cache(symbol_overview_obj)
            SymbolCacheContainer.release_semaphore()

    async def handle_partial_update_all_symbol_overview_post(self, updated_symbol_overview_dict_list: List[Dict[str, Any]]):
        updated_symbol_overview_obj_list = SymbolOverview.from_dict_list(updated_symbol_overview_dict_list)
        # updating bartering_data_manager's plan_cache
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            # updating symbol_cache
            self.plan_cache.handle_set_symbol_overview_in_symbol_cache(symbol_overview_obj)
            SymbolCacheContainer.release_semaphore()

    async def handle_create_top_of_book_post(self, top_of_book_obj: TopOfBook):
        self.plan_cache.handle_set_tob_in_symbol_cache(top_of_book_obj)
        # used for basket executor - plan executor releases semaphore from cpp app
        SymbolCacheContainer.release_semaphore()

    async def handle_update_top_of_book_post(self, updated_top_of_book_obj: TopOfBook):
        self.plan_cache.handle_set_tob_in_symbol_cache(updated_top_of_book_obj)
        # used for basket executor - plan executor releases semaphore from cpp app
        SymbolCacheContainer.release_semaphore()

    async def handle_partial_update_top_of_book_post(self, updated_top_of_book_obj_json: Dict[str, Any]):
        updated_top_of_book_obj: TopOfBook = TopOfBook.from_dict(updated_top_of_book_obj_json)
        self.plan_cache.handle_set_tob_in_symbol_cache(updated_top_of_book_obj)
        # used for basket executor - plan executor releases semaphore from cpp app
        SymbolCacheContainer.release_semaphore()

    #####################
    # Query Pre/Post handling
    #####################

    async def handle_get_underlying_account_cumulative_fill_qty_query_pre(
            self, symbol: str, side: str):
        fill_journal_obj_list = \
            await (self.derived_class_type.
                   underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http(symbol, side))

        underlying_accounts: Set[str] = set()
        underlying_accounts_cum_fill_qty_obj: UnderlyingAccountCumFillQty = UnderlyingAccountCumFillQty(
            underlying_account_n_cumulative_fill_qty=[]
        )
        for fill_journal_obj in fill_journal_obj_list:
            if (underlying_acc := fill_journal_obj.underlying_account) not in underlying_accounts:
                underlying_accounts.add(underlying_acc)
                underlying_accounts_cum_fill_qty_obj.underlying_account_n_cumulative_fill_qty.append(
                    UnderlyingAccountNCumFillQty(underlying_account=underlying_acc,
                                                 cumulative_qty=fill_journal_obj.underlying_account_cumulative_fill_qty)
                )
        return [underlying_accounts_cum_fill_qty_obj]

    async def handle_get_symbol_side_underlying_account_cumulative_fill_qty_query_pre(self, symbol: str, side: str):
        return await self.derived_class_type.underlying_read_fills_journal_http(
            get_symbol_side_underlying_account_cumulative_fill_qty(symbol, side), self.get_generic_read_route())

    @abstractmethod
    def get_residual_mark_secs(self):
        raise NotImplementedError

    async def cxl_expired_open_chores(self):
        residual_mark_secs = self.get_residual_mark_secs()

        open_chore_snapshots_list: List[ChoreSnapshot] = self.plan_cache.get_open_chore_snapshots()

        for open_chore_snapshot in open_chore_snapshots_list:
            if not self.executor_inst_id:
                self.executor_inst_id = BaseBook.bartering_link.inst_id
            if (not open_chore_snapshot.chore_brief.user_data) or (
                    not open_chore_snapshot.chore_brief.user_data.startswith(self.executor_inst_id)):
                logging.info(f"cancel ext chore ignored: {open_chore_snapshot.chore_brief.chore_id} found in "
                             f"expired open chores for {self.derived_class_type.get_chore_snapshot_log_key(open_chore_snapshot)}")
                continue
            if (open_chore_snapshot.chore_status != ChoreStatusType.OE_CXL_UNACK and
                    not chore_has_terminal_state(open_chore_snapshot)):
                open_chore_interval = DateTime.utcnow() - open_chore_snapshot.create_date_time
                open_chore_interval_secs = open_chore_interval.total_seconds()
                if residual_mark_secs != 0 and open_chore_interval_secs > residual_mark_secs:
                    logging.info(f"Triggering place_cxl_chore for expired_open_chore:  "
                                 f"{open_chore_snapshot.chore_brief.chore_id}, {open_chore_interval_secs=};;;"
                                 f"{residual_mark_secs=}; {open_chore_snapshot.chore_status=}")
                    await BaseBook.bartering_link.place_cxl_chore(
                        open_chore_snapshot.chore_brief.chore_id, open_chore_snapshot.chore_brief.side,
                        open_chore_snapshot.chore_brief.security.sec_id,
                        open_chore_snapshot.chore_brief.security.sec_id,
                        open_chore_snapshot.chore_brief.underlying_account)
                # else not required: If time-delta is still less than residual_mark_seconds then avoiding
                # cancellation of chore
            elif chore_has_terminal_state(open_chore_snapshot):
                logging.warning(f"Unexpected or Rare: Received {open_chore_snapshot.chore_status=}, bug or race in "
                                f"get_open_chore_snapshots, results should not have any non-open chore_snapshot, unless"
                                f" under ignorable race condition [i.e. chore went DOD/Fully-Filled after queried DB "
                                f"via get_open_chore_snapshots] for "
                                f"{self.derived_class_type.get_chore_snapshot_log_key(open_chore_snapshot)}")
            # else not required: avoiding cxl request if chore_snapshot already got cxl request

    async def handle_get_top_of_book_from_symbol_query_pre(self, symbol: str):
        return await self.derived_class_type.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    async def handle_delete_symbol_overview_pre(self, obj_id: int):
        symbol_overview: SymbolOverview = \
            await self.derived_class_type.underlying_read_symbol_overview_by_id_http(obj_id)
        symbol_cache = SymbolCacheContainer.get_symbol_cache(symbol_overview.symbol)
        symbol_cache.so = None

    #########################
    # Barter Simulator Queries
    #########################

    async def handle_barter_simulator_place_new_chore_query_pre(
            self, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str, symbol_type: str,
            underlying_account: str, exchange: str | None = None, internal_ord_id: str | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.place_new_chore(px, qty, side, bartering_sec_id, system_sec_id, symbol_type,
                                             underlying_account, exchange, client_ord_id=internal_ord_id)
        return []

    async def handle_barter_simulator_place_cxl_chore_query_pre(
            self, chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
            system_sec_id: str | None = None, underlying_account: str | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.place_cxl_chore(chore_id, side, bartering_sec_id, system_sec_id, underlying_account)
        return []

    async def handle_barter_simulator_process_chore_ack_query_pre(
            self, chore_id: str, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.process_chore_ack(chore_id, px, qty, side, sec_id, underlying_account)
        return []

    async def handle_barter_simulator_process_fill_query_pre(
            self, chore_id: str, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
            use_exact_passed_qty: bool | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.process_fill(chore_id, px, qty, side, sec_id, underlying_account, use_exact_passed_qty)
        return []

    async def handle_barter_simulator_reload_config_query_pre(self):
        BarterSimulator.reload_symbol_configs()
        return []

    async def handle_barter_simulator_process_amend_req_query_pre(
            self, chore_id: str, side: Side, sec_id: str, underlying_account: str, chore_event: ChoreEventType,
            px: float | None = None, qty: int | None = None):
        if px is None and qty is None:
            logging.error("Both Px and Qty can't be None while placing amend chore - ignoring this "
                          "amend chore creation")
            return
        await BarterSimulator.place_amend_req_chore(chore_id, side, sec_id, sec_id, chore_event,
                                                   underlying_account, px=px, qty=qty)
        return []

    async def handle_barter_simulator_process_amend_ack_query_pre(
            self, chore_id: str, side: Side, sec_id: str, underlying_account: str):
        await BarterSimulator.place_amend_ack_chore(chore_id, side, sec_id, sec_id, underlying_account)
        return []

    async def handle_barter_simulator_process_amend_rej_query_pre(
            self, chore_id: str, side: Side, sec_id: str, underlying_account: str):
        await BarterSimulator.place_amend_rej_chore(chore_id, side, sec_id, sec_id, underlying_account)
        return []

    async def handle_barter_simulator_process_lapse_query_pre(
            self, chore_id: str, side: Side, sec_id: str, underlying_account: str, qty: int | None = None):
        await BarterSimulator.place_lapse_chore(chore_id, side, sec_id, sec_id, underlying_account, qty)
        return []
