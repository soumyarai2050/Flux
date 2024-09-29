import ctypes
import math

from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import (
    get_bartering_link, BarteringLinkBase)
from FluxPythonUtils.scripts.service import Service
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_data_manager import BaseBarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_strat_cache import BaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.chore_check import (
    ChoreControl, initialize_chore_control)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_basket_book_core_msgspec_model import *


BaseStratCacheType = TypeVar('BaseStratCacheType', bound=BaseStratCache)
BaseBarteringDataManagerType = TypeVar('BaseBarteringDataManagerType', bound=BaseBarteringDataManager)


class BaseBook(Service):
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    asyncio_loop: asyncio.AbstractEventLoop

    def __init__(self, bartering_data_manager_: BaseBarteringDataManagerType, strat_cache: BaseStratCacheType):
        super().__init__()
        self.bartering_data_manager = bartering_data_manager_
        self.strat_cache = strat_cache
        self.market = Market(MarketID.IN)
        self.usd_fx = None
        self.internal_new_chore_count: int = 0
        # internal rejects to use:  -ive internal_reject_count + current date time as chore id
        self.internal_reject_count = 0
        self._cancel_chores_update_date_time: DateTime | None = None
        self._cancel_chores_processed_slice: int = 0
        # initialize ChoreControl class vars
        initialize_chore_control()

    @property
    def derived_class_type(self):
        raise NotImplementedError

    def get_usd_fx(self):
        if self.usd_fx:
            return self.usd_fx
        else:
            if not self.strat_cache.usd_fx_symbol_overview:
                self.strat_cache.usd_fx_symbol_overview = \
                    BaseStratCache.fx_symbol_overview_dict[BaseStratCache.usd_fx_symbol]
            if self.strat_cache.usd_fx_symbol_overview and self.strat_cache.usd_fx_symbol_overview.closing_px and \
                    (not math.isclose(self.strat_cache.usd_fx_symbol_overview.closing_px, 0)):
                self.usd_fx = self.strat_cache.usd_fx_symbol_overview.closing_px
                return self.usd_fx
            else:
                logging.error(f"unable to find fx_symbol_overview for "
                              f"{BaseStratCache.usd_fx_symbol=};;; {self.strat_cache=}")
                return None

    @classmethod
    def bartering_link_internal_chore_state_update(
            cls, chore_event: ChoreEventType, chore_id: str, side: Side | None = None,
            bartering_sec_id: str | None = None, system_sec_id: str | None = None,
            underlying_account: str | None = None, msg: str | None = None):
        # coro needs public method
        run_coro = cls.bartering_link.internal_chore_state_update(chore_event, chore_id, side, bartering_sec_id,
                                                                         system_sec_id, underlying_account, msg)
        future = asyncio.run_coroutine_threadsafe(run_coro, cls.asyncio_loop)
        # block for start_executor_server task to finish
        try:
            return future.result()
        except Exception as e:
            logging.exception(f"_internal_reject_new_chore failed with exception: {e}")

    def internal_reject_new_chore(self, new_chore: NewChoreBaseModel, reject_msg: str):
        self.internal_reject_count += 1
        internal_reject_chore_id: str = str(self.internal_reject_count * -1) + str(DateTime.utcnow())
        self.bartering_link_internal_chore_state_update(
            ChoreEventType.OE_INT_REJ, internal_reject_chore_id, new_chore.side, None,
            new_chore.security.sec_id, None, reject_msg)

    def get_client_chore_id(self):
        self.internal_new_chore_count += 1
        client_ord_id: str = f"{BaseBook.bartering_link.inst_id}-{self.internal_new_chore_count}"
        return client_ord_id

    @classmethod
    def bartering_link_place_new_chore(cls, px: float, qty: int, side: Side, bartering_symbol: str, system_symbol: str,
                                     symbol_type: str, account: str, exchange: str,
                                     client_ord_id: str | None = None, **kwargs):
        run_coro = cls.bartering_link.place_new_chore(px, qty, side, bartering_symbol, system_symbol, symbol_type,
                                                    account, exchange, client_ord_id=client_ord_id, **kwargs)
        future = asyncio.run_coroutine_threadsafe(run_coro, cls.asyncio_loop)

        # block for task to finish [run as coroutine helps enable http call via asyncio, other threads use freed CPU]
        try:
            # ignore 2nd param: _id_or_err_str - logged in call and not used in strat executor yet
            chore_sent_status, _id_or_err_str = future.result()
            return chore_sent_status, _id_or_err_str
        except Exception as e:
            logging.exception(f"bartering_link_place_new_chore failed for {system_symbol=} px-qty-side: {px}-{qty}-{side}"
                              f" with exception;;;{e}")
            return False

    def process_cxl_request(self, force_cxl_only: bool = False):
        cancel_chores_and_date_tuple = self.strat_cache.get_cancel_chore(self._cancel_chores_update_date_time)
        if cancel_chores_and_date_tuple is not None:
            cancel_chores, self._cancel_chores_update_date_time = cancel_chores_and_date_tuple
            if cancel_chores is not None:
                final_slice = len(cancel_chores)
                unprocessed_cancel_chores: List[CancelChoreBaseModel] = \
                    cancel_chores[self._cancel_chores_processed_slice:final_slice]
                self._cancel_chores_processed_slice = final_slice
                cancel_chore: CancelChoreBaseModel
                for cancel_chore in unprocessed_cancel_chores:
                    if not cancel_chore.cxl_confirmed:
                        res: bool = True
                        if (not force_cxl_only) or cancel_chore.force_cancel:
                            res = self.bartering_link_place_cxl_chore(cancel_chore.chore_id, cancel_chore.side,
                                                                    bartering_sec_id=None,
                                                                    system_sec_id=cancel_chore.security.sec_id,
                                                                    underlying_account="NA")
                        else:
                            logging.warning(f"{force_cxl_only=} and {cancel_chore.force_cancel=} leaving unprocessed "
                                            f"{cancel_chore=}")
                        if not res:
                            # check in DB if this chore needs cancellation, otherwise set cancel_chore.cxl_confirmed to
                            # true and stop processing it
                            pass

                # if some update was on existing cancel_chores then this semaphore release was for that update only,
                # therefore returning True to continue and wait for next semaphore release
                return True
        # all else return false - no cancel_chore to process
        return False

    @classmethod
    def bartering_link_place_cxl_chore(cls, chore_id, side, bartering_sec_id, system_sec_id, underlying_account) -> bool:
        # coro needs public method
        run_coro = cls.bartering_link.place_cxl_chore(chore_id, side, bartering_sec_id, system_sec_id, underlying_account)
        future = asyncio.run_coroutine_threadsafe(run_coro, cls.asyncio_loop)

        # block for start_executor_server task to finish
        try:
            # ignore return chore_journal: don't generate cxl chores in system, just treat cancel acks as unsol cxls
            res: bool = future.result()
            if not res:
                logging.error(f"bartering_link_place_cxl_chore failed, {res=} returned")
                return False
            else:
                return True
        except Exception as e:
            key = get_symbol_side_key([(system_sec_id, side)])
            logging.exception(f"bartering_link_place_cxl_chore failed for: {key} with exception: {e}")
