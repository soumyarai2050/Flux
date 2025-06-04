# standard imports
import logging
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
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *


class BasketBarteringDataManager(BaseBarteringDataManager, BasketBookServiceDataManager, EmailBookServiceDataManager):

    def __init__(self, executor_trigger_method: Callable, plan_cache: BasketCache):
        BaseBarteringDataManager.__init__(self)
        BasketBookServiceDataManager.__init__(self, be_host, be_port, plan_cache)
        EmailBookServiceDataManager.__init__(self, ps_host, ps_port, plan_cache)
        self.bartering_cache: BasketBarteringCache = BasketBarteringCache()
        self.plan_cache: BasketCache = plan_cache

        if market.is_test_run:
            err_str_: str = f"basket executor running in test mode, {market.is_test_run=}"
            print(f"CRITICAL: {err_str_}")
            logging.critical(err_str_)

        self.chore_limits_ws_get_all_cont.register_to_run()
        self.system_control_ws_get_all_cont.register_to_run()
        self.fx_symbol_overview_ws_get_all_cont.register_to_run()

        self.executor_trigger_method = executor_trigger_method
        self.ws_thread = Thread(target=WSReader.start, daemon=True).start()

    def handle_basket_chore_get_all_ws_(self, basket_chore_: BasketChoreBaseModel | BasketChore | None, **kwargs):
        if self.street_book is None:
            # Triggering executor when basket_chore is created
            self.street_book, self.street_book_thread = (
                self.executor_trigger_method(self, self.plan_cache))
        if basket_chore_ is None:  # startup case - no basket chore is present
            return
        self.plan_cache.set_basket_chore(basket_chore_)
        logging.debug(f"Updated basket_chore;;; {basket_chore_=}")

    def handle_unack_state(self, is_unack: bool, chore_snapshot: ChoreSnapshotBaseModel | ChoreSnapshot):
        self.plan_cache.set_unack(is_unack, chore_snapshot.chore_brief.security.sec_id,
                                   chore_snapshot.chore_brief.side)

    def handle_fx_symbol_overview_get_all_ws(self, fx_symbol_overview_: FxSymbolOverviewBaseModel, **kwargs):
        if fx_symbol_overview_.symbol in BasketCache.fx_symbol_overview_dict:
            # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
            BasketCache.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
            BasketCache.notify_all()
        super().handle_fx_symbol_overview_get_all_ws(fx_symbol_overview_)
