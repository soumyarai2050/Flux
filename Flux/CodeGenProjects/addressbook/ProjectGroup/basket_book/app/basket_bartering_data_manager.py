# standard imports
from threading import Thread
from queue import Queue

# 3rd party imports

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_ws_data_manager import BasketBookServiceDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.StreetBook.email_book_service_ws_data_manager import (
    EmailBookServiceDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import (
    ps_host, ps_port)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import be_host, be_port
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_cache import BasketCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_bartering_cache import BasketBarteringCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link import market
from FluxPythonUtils.scripts.ws_reader import WSReader
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_bartering_data_manager import BaseBarteringDataManager
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import *

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.Pydantic.mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


class BasketBarteringDataManager(BaseBarteringDataManager, BasketBookServiceDataManager, EmailBookServiceDataManager):

    def __init__(self, executor_trigger_method: Callable, strat_cache: BasketCache):
        BaseBarteringDataManager.__init__(self)
        BasketBookServiceDataManager.__init__(self, be_host, be_port, strat_cache)
        EmailBookServiceDataManager.__init__(self, ps_host, ps_port, strat_cache)
        self.bartering_cache: BasketBarteringCache = BasketBarteringCache()
        self.strat_cache: BasketCache = strat_cache
        self.id_to_new_chore_dict: Dict[int, NewChore] = {}
        self.non_cached_basket_chore_queue: Queue[BasketChore | BasketChoreOptional] = Queue()

        if market.is_test_run:
            err_str_: str = f"basket executor running in test mode, {market.is_test_run=}"
            print(f"CRITICAL: {err_str_}")
            logging.critical(err_str_)

        self.chore_limits_ws_get_all_cont.register_to_run()
        self.system_control_ws_get_all_cont.register_to_run()
        self.basket_chore_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()

        self.executor_trigger_method = executor_trigger_method
        self.ws_thread = Thread(target=WSReader.start, daemon=True).start()
        self.basket_id: int | None = None

    def handle_basket_chore_get_all_ws_(self, basket_chore_: BasketChoreBaseModel | BasketChore, **kwargs):
        # setting basket_chore_exists to True when basket_chore exists
        if self.basket_id is None:
            self.basket_id = basket_chore_.id
            # Triggering executor when basket_chore is created
            self.street_book, self.street_book_thread = (
                self.executor_trigger_method(self, self.strat_cache))

        self.strat_cache.set_basket_chore(basket_chore_)
        non_cached_new_chore_list: List[NewChore] = []
        new_chore_obj: NewChore
        for new_chore_obj in basket_chore_.new_chores:
            if self.id_to_new_chore_dict.get(new_chore_obj.id) is None:
                # this is new / recovered chore entry - add to non_cached_new_chore_list
                non_cached_new_chore_list.append(new_chore_obj)
                self.id_to_new_chore_dict[new_chore_obj.id] = new_chore_obj
                logging.info(f"Added to non_cached_new_chore_list chore: {new_chore_obj.security.sec_id} "
                             f"{new_chore_obj.side} {new_chore_obj.chore_id};;;{new_chore_obj}")

        if non_cached_new_chore_list:
            basket_chore_ = BasketChore.from_kwargs(_id=basket_chore_.id,
                                                    new_chores=non_cached_new_chore_list)
            self.non_cached_basket_chore_queue.put(basket_chore_)

    def handle_unack_state(self, is_unack: bool, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot):
        self.strat_cache.set_unack(is_unack, chore_snapshot.chore_brief.security.sec_id,
                                   chore_snapshot.chore_brief.side)

    def handle_fx_symbol_overview_get_all_ws(self, fx_symbol_overview_: FxSymbolOverviewBaseModel, **kwargs):
        if fx_symbol_overview_.symbol in BasketCache.fx_symbol_overview_dict:
            # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
            BasketCache.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
            BasketCache.notify_all()
        super().handle_fx_symbol_overview_get_all_ws(fx_symbol_overview_)

    def handle_top_of_book_get_all_ws(self, top_of_book_: TopOfBookBaseModel | TopOfBook, **kwargs):
        if top_of_book_.symbol in BasketCache.fx_symbol_overview_dict:
            # if we need fx TOB: StratCache needs to collect reference here (like we do in symbol_overview)
            return  # No use-case for fx TOB at this time
        super().handle_top_of_book_get_all_ws(top_of_book_)
