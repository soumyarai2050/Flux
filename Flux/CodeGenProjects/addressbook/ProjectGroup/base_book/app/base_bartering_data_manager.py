# project imports
from typing import TypeVar
from threading import Thread

from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_cache import BaseBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_strat_cache import BaseStratCache
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *


BaseBarteringCacheType = TypeVar('BaseBarteringCacheType', bound=BaseBarteringCache)


class BaseBarteringDataManager:

    def __init__(self):
        self.bartering_cache: BaseBarteringCacheType | None = None  # must be set by derived impl
        self.strat_cache: BaseStratCache | None = None  # must be set by derived impl
        self.street_book = None
        self.street_book_thread: Thread | None = None

    def handle_unack_state(self, is_unack: bool, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot):
        raise NotImplementedError

    def underlying_handle_chore_snapshot_ws_(self, **kwargs):
        chore_snapshot_: ChoreSnapshotBaseModel | ChoreSnapshot = kwargs.get("chore_snapshot_")
        with self.strat_cache.re_ent_lock:
            is_unack: bool = False
            # ChoreStatusType.OE_CXL_UNACK not included here - this leads to seconds leg block cases - max open chore to
            # prevent more chores from going to market if / when too many cancel un-ack chores are pending
            if chore_snapshot_.chore_status == ChoreStatusType.OE_UNACK:
                is_unack = True
                BaseStratCache.chore_id_to_symbol_side_tuple_dict[chore_snapshot_.chore_brief.chore_id] = \
                    (chore_snapshot_.chore_brief.security.sec_id, chore_snapshot_.chore_brief.side)

        self.handle_unack_state(is_unack, chore_snapshot_)
