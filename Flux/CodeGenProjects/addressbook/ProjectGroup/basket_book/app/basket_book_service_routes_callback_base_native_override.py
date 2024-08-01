# standard imports
import os
import threading
from queue import Queue
from typing import Dict, Final, List, Tuple, ClassVar
import time
import datetime
import logging
from threading import Thread
import asyncio
import stat
import subprocess

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_routes_callback import BasketBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    config_yaml_path, parse_to_int, config_yaml_dict, be_host, be_port, is_all_service_up, CURRENT_PROJECT_DIR)
from FluxPythonUtils.scripts.utility_functions import (
    except_n_log_alert, handle_refresh_configurable_data_members)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.Pydentic.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import (
    StratLeg, FxSymbolOverviewBaseModel)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import (
    email_book_service_http_client)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link import get_bartering_link, BarteringLinkBase, is_test_run
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.street_book_service_helper import \
    get_symbol_side_key
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import MDShellEnvData, create_md_shell_script
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_symbol_overview_from_symbol, get_objs_from_symbol)


class MobileBookContainer(BaseModel):
    tob: TopOfBook | TopOfBookBaseModel
    so: SymbolOverview | SymbolOverviewBaseModel


class BasketBookServiceRoutesCallbackBaseNativeOverride(BasketBookServiceRoutesCallback):
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    symbol_side_key_cache: ClassVar[Dict[str, bool]] = {}

    # underlying callables
    underlying_read_symbol_overview_http: Callable[[...], Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[[...], Any] | None = None
    underlying_partial_update_basket_chore_http: Callable[Any, Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.is_sanity_test_run: bool = config_yaml_dict.get("is_sanity_test_run")
        self.is_dev_env = True
        self.is_test_run = is_test_run
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx_symbol: Final[str] = "USD|SGD"
        self.fx_symbol_overview_dict: Dict[str, FxSymbolOverviewBaseModel | None] = {self.usd_fx_symbol: None}
        self.usd_fx = None
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        # cache for tob and symbol_overview for each new_chore
        self.md_cache: Dict[str, MobileBookContainer] = {}
        self.basket_chore_queue: Queue[BasketChore | BasketChoreOptional] = Queue()
        self.new_chore_id_cache: Dict[int, NewChore] = {}

    @staticmethod
    def get_symbol_side_cache_key(system_symbol: str, side: Side):
        return f"{system_symbol}-{side.value}"

    @classmethod
    def check_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        if cls.symbol_side_key_cache.get(symbol_side_key) is None:
            return False
        return True

    @classmethod
    def set_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        if symbol_side_key not in cls.symbol_side_key_cache:
            cls.symbol_side_key_cache[symbol_side_key] = True
            return True
        else:
            # if key exists already
            return False

    @classmethod
    def clear_unack(cls, system_symbol: str, side: Side):
        symbol_side_key = cls.get_symbol_side_cache_key(system_symbol, side)
        res = cls.symbol_side_key_cache.pop(symbol_side_key, None)
        if res is None:
            # if no key existed already
            logging.error(f'symbol-side key: {symbol_side_key} not found in cache to clear unack')
            return False
        else:
            return True

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_routes import (
            underlying_read_symbol_overview_http, underlying_read_top_of_book_http,
            underlying_get_symbol_overview_from_symbol_query_http,
            underlying_get_top_of_book_from_symbol_query_http, underlying_partial_update_basket_chore_http)
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = underlying_get_symbol_overview_from_symbol_query_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_partial_update_basket_chore_http = underlying_partial_update_basket_chore_http

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair strats at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"basket_book_{be_port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up and self.usd_fx is not None:
                    if not self.service_ready:
                        self.service_ready = True
                        print(f"INFO: service is ready: {datetime.datetime.now().time()}")
                        thread = threading.Thread(target=self.handle_basket_chores, daemon=True)
                        thread.start()

                if not self.service_up:
                    try:
                        if is_all_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    if self.usd_fx is None:
                        try:
                            if not self.update_fx_symbol_overview_dict_from_http():
                                logging.error(f"Can't find any symbol_overview with symbol {self.usd_fx_symbol} "
                                              f"in phone_book service, retrying in next periodic cycle",
                                              exc_info=True)
                        except Exception as e:
                            logging.exception(f"update_fx_symbol_overview_dict_from_http failed with exception: {e}")

                    last_modified_timestamp = os.path.getmtime(config_yaml_path)
                    if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                        self.config_yaml_last_modified_timestamp = last_modified_timestamp

                        handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                 str(config_yaml_path))
            else:
                should_sleep = True

    def app_launch_pre(self):
        BasketBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = be_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

    async def read_all_ui_layout_pre(self):
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

    def handle_basket_chores(self):
        while True:
            basket_chore: BasketChore | BasketChoreOptional = self.basket_chore_queue.get()      # blocking call
            run_coro = self._handle_basket_chore(basket_chore)
            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
            # block for task to finish
            try:
                future.result()
            except Exception as e:
                logging.exception(f"handle_new_chores failed with exception: {e}")

    async def _handle_basket_chore(self, basket_chore: BasketChore | BasketChoreOptional):
        new_chore_list = basket_chore.new_chores
        for new_chore_obj in new_chore_list:
            system_symbol = new_chore_obj.security.sec_id
            sec_id_source = new_chore_obj.security.sec_id_source
            await self._verify_mobile_book_for_symbol(system_symbol, sec_id_source)

            px = new_chore_obj.px
            qty = new_chore_obj.qty
            side = new_chore_obj.side

            usd_px = self.get_usd_px(new_chore_obj.px, system_symbol)
            bartering_symbol, account, exchange = self.get_metadata(system_symbol)

            # block new chore if any prior unack chore exist
            if BasketBookServiceRoutesCallbackBaseNativeOverride.check_unack(system_symbol, side):
                error_msg: str = f"past chore on {system_symbol=} is in unack state, dropping chore with " \
                                 f"{px=}, {qty=}, {side=}, symbol_side_key: " \
                                 f"{get_symbol_side_key([(system_symbol, side)])}"
                logging.error(error_msg)
                new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED
                return None

            if self._is_outside_bartering_hours():
                err_str_ = "Secondary Block place chore - strat outside market hours"
                logging.error(err_str_)
                raise HTTPException(detail=err_str_, status_code=400)

            # set unack for subsequent chores - this symbol to be blocked until this chore goes through
            self.set_unack(system_symbol, side)
            res = await self.bartering_link_place_new_chore(px, qty, side, bartering_symbol, system_symbol,
                                                          account, exchange)
            # reset unack for subsequent chores to go through - this chore did fail to go through
            BasketBookServiceRoutesCallbackBaseNativeOverride.clear_unack(system_symbol, side)

            if res:
                new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_DONE
            else:
                new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED

            self.new_chore_id_cache[new_chore_obj.id] = new_chore_obj   # updating new_chore cache

        await (BasketBookServiceRoutesCallbackBaseNativeOverride.
               underlying_partial_update_basket_chore_http(
                    basket_chore.model_dump(by_alias=True, exclude_none=True)))

    def update_fx_symbol_overview_dict_from_http(self) -> bool:
        fx_symbol_overviews: List[FxSymbolOverviewBaseModel] = \
            email_book_service_http_client.get_all_fx_symbol_overview_client()
        if fx_symbol_overviews:
            fx_symbol_overview_: FxSymbolOverviewBaseModel
            for fx_symbol_overview_ in fx_symbol_overviews:
                if fx_symbol_overview_.symbol in self.fx_symbol_overview_dict:
                    # fx_symbol_overview_dict is pre initialized with supported fx pair symbols and None objects
                    self.fx_symbol_overview_dict[fx_symbol_overview_.symbol] = fx_symbol_overview_
                    self.usd_fx = fx_symbol_overview_.closing_px
                    logging.debug(f"Updated {self.usd_fx=}")
                    return True
        # all else - return False
        return False

    def get_usd_px(self, px: float, system_symbol: str):
        """
        assumes single currency strat - may extend to accept symbol and send revised px according to underlying currency
        """
        return px / self.usd_fx

    def get_metadata(self, system_symbol: str) -> Tuple[str, str, str]:
        """function to check system symbol's corresponding bartering_symbol, account, exchange (maybe fx in future ?)"""
        bartering_symbol: str = system_symbol
        account = "bartering_account"
        exchange = "bartering_exchange"
        return bartering_symbol, account, exchange

    def _is_outside_bartering_hours(self):
        if self.is_sanity_test_run or self.is_test_run or self.is_dev_env: return False
        return False

    async def bartering_link_place_new_chore(self, px, qty, side, bartering_symbol, system_symbol, account, exchange):
        chore_sent_status = await self.bartering_link.place_new_chore(px, qty, side, bartering_symbol, system_symbol,
                                                                    account, exchange)
        return chore_sent_status

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(
            get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    @staticmethod
    def create_n_run_so_shell_script(sec_id: str, sec_id_source: str):
        # creating run_symbol_overview.sh file
        run_symbol_overview_file_path = CURRENT_PROJECT_DIR / "scripts" / f"new_ord_sec_id_{sec_id}_so.sh"

        subscription_data = \
            [
                (sec_id, str(sec_id_source))
            ]
        db_name = "basket_book"

        md_shell_env_data: MDShellEnvData = (
            MDShellEnvData(subscription_data=subscription_data, host=be_host,
                           port=be_port, db_name=db_name, project_name="basket_book"))

        create_md_shell_script(md_shell_env_data, run_symbol_overview_file_path, "SO")
        os.chmod(run_symbol_overview_file_path, stat.S_IRWXU)
        subprocess.Popen([f"{run_symbol_overview_file_path}"])

    async def loop_till_symbol_md_data_is_present(self, symbol: str):
        wait_sec = config_yaml_dict.get("fetch_md_data_wait_sec")
        while True:

            symbol_overview_list: List[SymbolOverview] = \
                await (BasketBookServiceRoutesCallbackBaseNativeOverride.
                       underlying_get_symbol_overview_from_symbol_query_http(symbol))
            top_of_book_list: List[TopOfBook] = await (BasketBookServiceRoutesCallbackBaseNativeOverride.
                                                       underlying_get_top_of_book_from_symbol_query_http(symbol))

            if symbol_overview_list and top_of_book_list:
                top_of_book = top_of_book_list[0]
                symbol_overview = symbol_overview_list[0]
                self.md_cache[symbol] = MobileBookContainer(tob=top_of_book, so=symbol_overview)
                break
            else:
                time.sleep(wait_sec)

    async def _verify_mobile_book_for_symbol(self, sec_id: str, sec_id_source: str) -> bool:
        if sec_id not in self.md_cache:
            # creating script and running md cpp handling
            self.create_n_run_so_shell_script(sec_id, sec_id_source)

            # updating cache for tob and symbol_overview for this symbol
            await self.loop_till_symbol_md_data_is_present(sec_id)
            return False
        # else not required: if data already exists then will be using cached data
        return True

    def _handle_non_cached_new_chores(self, basket_chore_obj: BasketChore | BasketChoreOptional):
        non_cached_new_chore_list = []
        for new_chore_obj in basket_chore_obj.new_chores:
            if self.new_chore_id_cache.get(new_chore_obj.id) is None:
                non_cached_new_chore_list.append(new_chore_obj)

        if non_cached_new_chore_list:
            self.basket_chore_queue.put(BasketChore(id=basket_chore_obj.id,
                                                    new_chores=non_cached_new_chore_list))

    async def create_basket_chore_pre(self, basket_chore_obj: BasketChore):
        new_chore_list = basket_chore_obj.new_chores

        if new_chore_list:
            for new_chore_obj in new_chore_list:
                # setting state to pending
                new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING

    async def create_basket_chore_post(self, basket_chore_obj: BasketChore):
        self._handle_non_cached_new_chores(basket_chore_obj)

    async def partial_update_basket_chore_pre(self, stored_basket_chore_obj: BasketChore,
                                              updated_basket_chore_obj_json: Dict):

        new_chore_list = updated_basket_chore_obj_json.get("new_chores")

        if new_chore_list:
            for new_chore_dict in new_chore_list:
                if new_chore_dict.get("_id") is None:
                    # setting state to pending
                    new_chore_dict["chore_submit_state"] = ChoreSubmitType.ORDER_SUBMIT_PENDING
        return updated_basket_chore_obj_json

    async def partial_update_basket_chore_post(self, stored_basket_chore_obj: BasketChore,
                                               updated_basket_chore_obj: BasketChore):
        self._handle_non_cached_new_chores(updated_basket_chore_obj)

