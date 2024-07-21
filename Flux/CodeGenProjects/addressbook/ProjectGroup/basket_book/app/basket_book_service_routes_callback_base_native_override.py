# standard imports
import os
from typing import Dict, Final, List, Tuple, ClassVar
import time
import datetime
import logging
from threading import Thread
import asyncio

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_routes_callback import BasketBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    config_yaml_path, parse_to_int, config_yaml_dict, be_port, is_all_service_up)
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


class BasketBookServiceRoutesCallbackBaseNativeOverride(BasketBookServiceRoutesCallback):
    bartering_link: ClassVar[BarteringLinkBase] = get_bartering_link()
    symbol_side_key_cache: ClassVar[Dict[str, bool]] = {}

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

    @staticmethod
    def get_symbol_side_cache_key(system_symbol: str, side: Side):
        return f"{system_symbol}-{side}"

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
        pass

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

    async def create_basket_chore_pre(self, basket_chore_obj: BasketChore):
        new_chore_list = basket_chore_obj.new_chores

        if new_chore_list:
            for new_chore_obj in new_chore_list:
                px = new_chore_obj.px
                qty = new_chore_obj.qty
                side = new_chore_obj.side

                system_symbol = new_chore_obj.security.sec_id
                usd_px = self.get_usd_px(new_chore_obj.px, system_symbol)
                bartering_symbol, account, exchange = self.get_metadata(system_symbol)

                # block new chore if any prior unack chore exist
                if BasketBookServiceRoutesCallbackBaseNativeOverride.check_unack(system_symbol, side):
                    error_msg: str = f"past chore on {system_symbol=} is in unack state, dropping chore with " \
                                     f"{px=}, {qty=}, {side=}, symbol_side_key: " \
                                     f"{get_symbol_side_key([(system_symbol, side)])}"
                    logging.error(error_msg)
                    new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_FAILED
                    continue

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
