from pendulum import DateTime
from typing import Final, Dict, Set

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_base_strat_cache import BasketBookServiceBaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_base_strat_cache import \
    EmailBookServiceBaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_strat_cache import BaseStratCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_key_handler import BasketBookServiceKeyHandler


class BasketCache(BaseStratCache, BasketBookServiceBaseStratCache, EmailBookServiceBaseStratCache):
    KeyHandler: Type[BasketBookServiceKeyHandler] = BasketBookServiceKeyHandler

    def __init__(self):
        BaseStratCache.__init__(self)
        BasketBookServiceBaseStratCache.__init__(self)
        EmailBookServiceBaseStratCache.__init__(self)
        self.unack_state_set: Set[str] = set()

    @staticmethod
    def get_symbol_side_cache_key(system_symbol: str, side: Side):
        return f"{system_symbol}-{side.value}"

    def check_unack(self, system_symbol: str, side: Side):
        symbol_side_key = BasketCache.get_symbol_side_cache_key(system_symbol, side)
        if symbol_side_key not in self.unack_state_set:
            return False
        return True

    def set_unack(self, has_unack: bool, system_symbol: str, side: Side):
        symbol_side_key = BasketCache.get_symbol_side_cache_key(system_symbol, side)
        if has_unack:
            self.unack_state_set.add(symbol_side_key)
        else:
            self.unack_state_set.discard(symbol_side_key)

    def set_chore_snapshot(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot) -> DateTime:
        """
        override to enrich _chore_id_to_open_chore_snapshot_dict [invoke base first and then act here]
        """
        _chore_snapshots_update_date_time = super().set_chore_snapshot(chore_snapshot)
        overfill_log_str = f"Chore found overfilled for symbol_side_key: ;;;{chore_snapshot=}"
        self.handle_set_chore_snapshot(chore_snapshot, overfill_log_str)
        return _chore_snapshots_update_date_time  # ignore - helps with debug

    def set_symbol_overview(self, symbol_overview_: SymbolOverviewBaseModel | SymbolOverview):
        symbol_overview = self.handle_set_symbol_overview_in_symbol_cache(symbol_overview_)
        return symbol_overview.last_update_date_time

    def set_top_of_book(self, top_of_book: TopOfBookBaseModel | TopOfBook) -> DateTime | None:
        tob = self.handle_set_top_of_book(top_of_book)
        return tob.last_update_date_time
