# standard imports
import logging
from typing import Final, Set, Tuple
from threading import RLock

# Project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_phone_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import (
    SymbolCache, SymbolCacheContainer)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_models_log_keys import (
    get_symbol_side_key)
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState


class ChoreSnapshotContainer:
    def __init__(self, chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel, has_fill: bool):
        self.chore_snapshot: ChoreSnapshot | ChoreSnapshotBaseModel = chore_snapshot
        self.has_fill: bool = has_fill


class BaseStratCache:
    KeyHandler = None   # Must be set by derived impl
    usd_fx_symbol: Final[str] = "USD|SGD"
    fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {usd_fx_symbol: None}
    chore_id_to_symbol_side_tuple_dict: Dict[str | int, Tuple[str, Side]] = dict()

    error_prefix = "StratCache: "
    load_static_data_mutex: Lock = Lock()
    static_data_service_state: ClassVar[ServiceState] = ServiceState(
        error_prefix=error_prefix + "static_data_service failed, exception: ")
    static_data: SecurityRecordManager | None = None

    def __init__(self):
        self.usd_fx_symbol_overview: FxSymbolOverviewBaseModel | FxSymbolOverview | None = None
        if not BaseStratCache.static_data_service_state.ready:
            BaseStratCache.load_static_data()
        self.re_ent_lock: RLock = RLock()
        # chore-snapshot is also stored in here iff chore snapshot is open [and removed from here if otherwise]
        self._chore_id_to_open_chore_snapshot_cont_dict: Dict[Any, ChoreSnapshotContainer] = {}  # no open
        self._open_chore_snapshots_update_date_time: DateTime = DateTime.utcnow()
        # temp store for has_fill till chore snapshot is created / has fill updated
        self.open_chore_id_has_fill_set: Set = set()
        self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock: Lock = Lock()

    @staticmethod
    def get_pos_cache_from_symbol_side(symbol: str, side: Side) -> PosCache | None:
        symbol_cache: SymbolCache = SymbolCacheContainer.get_symbol_cache(symbol)
        if symbol_cache is not None:
            if side == Side.BUY:
                return symbol_cache.buy_pos_cache
            else:
                return symbol_cache.sell_pos_cache
        else:
            logging.error(f"Can't find any symbol_cache with {symbol=};;; "
                          f"{SymbolCacheContainer.symbol_to_symbol_cache_dict}")
            return None

    @staticmethod
    def get_close_px(system_symbol: str):
        symbol_cache: SymbolCache = SymbolCacheContainer.get_symbol_cache(system_symbol)
        symbol_overview = symbol_cache.so
        if symbol_overview is not None:
            return symbol_overview.closing_px

        # all else log error return None
        logging.error(f"_symbol_overviews.closing_px not found in get_close_px called for: {system_symbol}")
        return None

    @classmethod
    def get_key_n_symbol_from_fills_journal(
            cls, fills_journal: FillsJournalBaseModel | FillsJournal) -> Tuple[str | None, str | None]:
        symbol: str
        symbol_side_tuple = cls.chore_id_to_symbol_side_tuple_dict.get(fills_journal.chore_id)
        if not symbol_side_tuple:
            logging.error(f"Unknown {fills_journal.chore_id=} found for fill "
                          f"{get_symbol_side_key([(fills_journal.fill_symbol, fills_journal.fill_side)])};;; "
                          f"{fills_journal=}")
            return None, None
        symbol, side = symbol_side_tuple
        key: str | None = cls.KeyHandler.get_key_from_fills_journal(fills_journal)
        return key, symbol

    def handle_set_chore_snapshot(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot,
                                  overfill_log_str: str) -> DateTime:
        """
        override to enrich _chore_id_to_open_chore_snapshot_dict [invoke base first and then act here]
        """
        if not chore_snapshot.chore_brief.user_data:
            return DateTime.now()  # external chore - no need to further cache
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            has_fill: bool = False
            if chore_snapshot.chore_status not in [ChoreStatusType.OE_DOD, ChoreStatusType.OE_FILLED,
                                                   ChoreStatusType.OE_OVER_FILLED, ChoreStatusType.OE_OVER_CXLED]:
                if chore_snapshot.chore_brief.chore_id in self.open_chore_id_has_fill_set:
                    has_fill = True
                if not (chore_snapshot_container := self._chore_id_to_open_chore_snapshot_cont_dict.get(
                        chore_snapshot.chore_brief.chore_id)):
                    chore_snapshot_container = ChoreSnapshotContainer(chore_snapshot, has_fill)
                    self._chore_id_to_open_chore_snapshot_cont_dict[chore_snapshot.chore_brief.chore_id] = \
                        chore_snapshot_container
                else:
                    chore_snapshot_container.chore_snapshot = chore_snapshot
                    if not chore_snapshot_container.has_fill:
                        chore_snapshot_container.has_fill = has_fill
                    else:
                        # has existing fill
                        pass
            else:
                self._check_log_over_fill(chore_snapshot, overfill_log_str)
                # chore is not open anymore, remove from chore_id_has_fill_set [set used only on open chores]
                self.open_chore_id_has_fill_set.discard(chore_snapshot.chore_brief.chore_id)
                # Providing the second argument None prevents the KeyError exception
                self._chore_id_to_open_chore_snapshot_cont_dict.pop(chore_snapshot.chore_brief.chore_id, None)

    def get_open_chore_snapshots(self) -> List[ChoreSnapshot]:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            return [open_chore_snapshot_cont.chore_snapshot for open_chore_snapshot_cont in
                    self._chore_id_to_open_chore_snapshot_cont_dict.values()]

    def get_open_chore_count_from_cache(self) -> int:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        return len(self._chore_id_to_open_chore_snapshot_cont_dict)

    def check_has_open_chore_with_no_fill_from_cache(self) -> bool:
        """caller to ensure this call is made only after both _strat_limits and _strat_brief are initialized"""
        open_chore_snapshot_cont: ChoreSnapshotContainer
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            for open_chore_snapshot_cont in self._chore_id_to_open_chore_snapshot_cont_dict.values():
                if not open_chore_snapshot_cont.has_fill:
                    return True
        return False

    def update_has_fill_on_open_chore_snapshot(self, fills_journal: FillsJournal):
        if not fills_journal.user_data:
            return  # external chore, no processing needed
        with self._chore_id_to_open_chore_snapshot_cont_dict_n_chore_id_has_fill_set_lock:
            open_chore_snapshot_cont: ChoreSnapshotContainer
            if open_chore_snapshot_cont := self._chore_id_to_open_chore_snapshot_cont_dict.get(fills_journal.chore_id):
                open_chore_snapshot_cont.has_fill = True
            elif fills_journal.chore_id not in self.open_chore_id_has_fill_set:
                # TODO: this also adds fills that may arrive post DOD (non Open chores) and reenter the set - add
                #  periodic cleanup
                self.open_chore_id_has_fill_set.add(fills_journal.chore_id)

    def _check_log_over_fill(self, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot, overfill_log_str: str):
        if chore_snapshot.chore_status == ChoreStatusType.OE_OVER_FILLED:
            logging.critical(overfill_log_str)

    def get_metadata(self, system_symbol: str) -> Tuple[str, str, str]:
        """function to check system symbol's corresponding bartering_symbol, account, exchange (maybe fx in future ?)"""
        bartering_symbol: str = system_symbol
        account = "bartering_account"
        exchange = "bartering_exchange"
        return bartering_symbol, account, exchange

    def get_symbol_overview_from_symbol_obj(self, symbol: str) -> SymbolOverviewBaseModel | SymbolOverview | None:
        symbol_cache = SymbolCacheContainer.get_symbol_cache(symbol)
        if symbol_cache is not None and symbol_cache.so is not None:
            return symbol_cache.so
        # if no match - return None
        return None

    def get_symbol_overview_from_symbol(self, symbol: str, date_time: DateTime | None = None) -> \
            Tuple[SymbolOverviewBaseModel | SymbolOverview, DateTime] | None:
        symbol_overview = self.get_symbol_overview_from_symbol_obj(symbol)

        if symbol_overview is not None and (date_time is None or date_time < symbol_overview.last_update_date_time):
            return symbol_overview, symbol_overview.last_update_date_time
        # if no match - return None
        return None

    def handle_set_top_of_book(self, top_of_book: TopOfBookBaseModel | TopOfBook) -> TopOfBook | TopOfBookBaseModel:
        symbol_cache = SymbolCacheContainer.get_symbol_cache(top_of_book.symbol)
        if symbol_cache is None:
            symbol_cache = SymbolCacheContainer.add_symbol_cache_for_symbol(top_of_book.symbol)

        # if python side http client is used to update tob then overriding existing extended_top_of_book used by cpp
        # updates, useful when some project doesn't rely on cpp updates for tob cache updates
        symbol_cache.top_of_book = top_of_book
        return symbol_cache.top_of_book

    @classmethod
    def load_static_data(cls):
        with cls.load_static_data_mutex:
            try:
                cls.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                if cls.static_data is not None:
                    cls.static_data_service_state.ready = True
                else:
                    raise Exception(f"self.static_data init to None, unexpected!!")
            except Exception as e:
                cls.static_data_service_state.handle_exception(e)

    def handle_set_symbol_overview_in_symbol_cache(self, symbol_overview_: SymbolOverviewBaseModel | SymbolOverview):
        symbol_cache = SymbolCacheContainer.get_symbol_cache(symbol_overview_.symbol)
        if symbol_cache is None:
            symbol_cache = SymbolCacheContainer.add_symbol_cache_for_symbol(symbol_overview_.symbol)

        symbol_cache.so = symbol_overview_
        return symbol_cache.so

    def handle_set_tob_in_symbol_cache(self, top_of_book_: TopOfBookBaseModel | TopOfBook):
        symbol_cache = SymbolCacheContainer.get_symbol_cache(top_of_book_.symbol)
        if symbol_cache is None:
            symbol_cache = SymbolCacheContainer.add_symbol_cache_for_symbol(top_of_book_.symbol)

        symbol_cache.top_of_book = top_of_book_
        return symbol_cache.top_of_book
