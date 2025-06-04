# standard imports
import asyncio
import logging
import os
import time
from threading import Thread
import math

import pendulum
# 3rd party imports
import polars as pl
from fastapi import UploadFile

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_routes_msgspec_callback import (
    BasketBookServiceRoutesCallback)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book_helper import (
    config_yaml_path, parse_to_int, config_yaml_dict, be_host, be_port, is_all_service_up, CURRENT_PROJECT_DIR,
    CURRENT_PROJECT_DATA_DIR, get_new_chores_from_pl_df, get_figi_to_sec_rec_dict)
from FluxPythonUtils.scripts.general_utility_functions import (
    except_n_log_alert, handle_refresh_configurable_data_members, set_package_logger_level, create_logger)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.barter_simulator import (
    BarterSimulator, BarteringLinkBase)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.log_barter_simulator import LogBarterSimulator
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import (
     create_symbol_overview_pre_helper, update_symbol_overview_pre_helper,
     partial_update_symbol_overview_pre_helper)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.aggregate import (
    get_symbol_overview_from_symbol)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.aggregate import get_objs_from_symbol
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_book import BasketBook
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_cache import BasketCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.app.basket_bartering_data_manager import (
    BasketBarteringDataManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.markets.market import Market, MarketID
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_service_routes_callback_base_native_override import BaseBookServiceRoutesCallbackBaseNativeOverride
from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.StreetBook.basket_book_service_key_handler import BasketBookServiceKeyHandler

from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.ORMModel.basket_book_service_model_imports import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.phone_book_n_street_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.dept_book_n_mobile_book_n_street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import (
    SymbolCacheContainer, SymbolCache)

class BasketBookServiceRoutesCallbackBaseNativeOverride(BaseBookServiceRoutesCallbackBaseNativeOverride,
                                                            BasketBookServiceRoutesCallback):
    KeyHandler: Type[BasketBookServiceKeyHandler] = BasketBookServiceKeyHandler

    # underlying callables
    underlying_read_symbol_overview_http: Callable[..., Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_get_top_of_book_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_create_chore_journal_http: Callable[..., Any] | None = None
    underlying_create_fills_journal_http: Callable[..., Any] | None = None
    underlying_read_basket_chore_http: Callable[..., Any] | None = None
    underlying_create_basket_chore_http: Callable[..., Any] | None = None
    underlying_partial_update_basket_chore_http: Callable[..., Any] | None = None
    shared_md_lock: AsyncRLock = AsyncRLock()

    def __init__(self):
        super().__init__()
        self.port: int | None = None
        self.service_up: bool = False
        self.service_ready: bool = False
        self.market = Market(MarketID.IN)
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.project_config_yaml_path = config_yaml_path
        self.executor_config_yaml_dict = config_yaml_dict
        self.config_yaml_last_modified_timestamp = os.path.getmtime(self.project_config_yaml_path)
        # restricted variable: don't overuse this will be extended to multi-currency support
        self.usd_fx = None
        self.static_data: SecurityRecordManager | None = None
        # dict to hold realtime configurable data members and their respective keys in config_yaml_dict
        self.config_key_to_data_member_name_dict: Dict[str, str] = {
            "min_refresh_interval": "min_refresh_interval"
        }
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        self.bartering_data_manager: BasketBarteringDataManager | None = None

    @property
    def derived_class_type(self):
        return BasketBookServiceRoutesCallbackBaseNativeOverride

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.basket_book.generated.FastApi.basket_book_service_http_msgspec_routes import (
            underlying_read_symbol_overview_http, underlying_read_top_of_book_http,
            underlying_get_symbol_overview_from_symbol_query_http,
            underlying_get_top_of_book_from_symbol_query_http,
            underlying_create_fills_journal_http, underlying_create_chore_journal_http,
            residual_compute_shared_lock, journal_shared_lock, underlying_create_chore_snapshot_http,
            get_underlying_account_cumulative_fill_qty_query_http, underlying_update_chore_snapshot_http,
            underlying_read_chore_journal_http, underlying_read_symbol_overview_by_id_http,
            underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http,
            underlying_read_fills_journal_http,
            underlying_partial_update_basket_chore_http, underlying_read_basket_chore_http,
            underlying_create_basket_chore_http)
        cls.residual_compute_shared_lock = residual_compute_shared_lock
        cls.journal_shared_lock = journal_shared_lock
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = underlying_get_symbol_overview_from_symbol_query_http
        cls.underlying_get_top_of_book_from_symbol_query_http = underlying_get_top_of_book_from_symbol_query_http
        cls.underlying_read_symbol_overview_by_id_http = underlying_read_symbol_overview_by_id_http
        cls.underlying_create_chore_journal_http = underlying_create_chore_journal_http
        cls.underlying_create_chore_snapshot_http = underlying_create_chore_snapshot_http
        cls.get_underlying_account_cumulative_fill_qty_query_http = get_underlying_account_cumulative_fill_qty_query_http
        cls.underlying_update_chore_snapshot_http = underlying_update_chore_snapshot_http
        cls.underlying_read_chore_journal_http = underlying_read_chore_journal_http
        cls.underlying_read_symbol_overview_by_id_http = underlying_read_symbol_overview_by_id_http
        cls.underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http = underlying_get_symbol_side_underlying_account_cumulative_fill_qty_query_http
        cls.underlying_read_fills_journal_http = underlying_read_fills_journal_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_create_fills_journal_http = underlying_create_fills_journal_http
        cls.underlying_partial_update_basket_chore_http = underlying_partial_update_basket_chore_http
        cls.underlying_read_basket_chore_http = underlying_read_basket_chore_http
        cls.underlying_create_basket_chore_http = underlying_create_basket_chore_http

    def static_data_periodic_refresh(self):
        # no action required if refreshed
        self.static_data.refresh()

    @except_n_log_alert()
    def _app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        static_data_service_state: ServiceState = ServiceState(
            error_prefix=error_prefix + "static_data_service failed, exception: ")
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        while True:
            try:
                if should_sleep:
                    time.sleep(self.min_refresh_interval)
                service_up_flag_env_var = os.environ.get(f"basket_book_{be_port}")

                if service_up_flag_env_var == "1":
                    # validate essential services are up, if so, set service ready state to true
                    if (self.service_up and self.static_data is not None and self.usd_fx is not None and
                            self.bartering_data_manager is not None):
                        if not self.service_ready:
                            self.service_ready = True
                            run_coro = (BasketBookServiceRoutesCallbackBaseNativeOverride.
                                        underlying_read_basket_chore_http())
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                            try:
                                res = future.result()
                                if res:  # recovery case
                                    self.bartering_data_manager.handle_basket_chore_get_all_ws_(res[0])
                                else:  # no basket chore exists to recover
                                    self.bartering_data_manager.handle_basket_chore_get_all_ws_(None)
                            except Exception as exp:
                                logging.exception(f"underlying_read_basket_chore_http failed, exception: {exp}")
                                self.service_ready = False
                            # print is just to manually check if this server is ready - useful when we run
                            # multiple servers and before running any test we want to make sure servers are up
                            print(f"INFO: basket executor service is ready: {datetime.datetime.now().time()}")

                    if not self.service_up:
                        try:
                            if is_all_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                                self.plan_cache: BasketCache = BasketCache()

                                BarteringLinkBase.simulate_config_yaml_path = (
                                        CURRENT_PROJECT_DATA_DIR / "basket_simulate_config.yaml")

                                BasketBook.asyncio_loop = self.asyncio_loop
                                BasketBarteringDataManager.asyncio_loop = self.asyncio_loop
                                self.bartering_data_manager = (
                                    BasketBarteringDataManager(BasketBook.executor_trigger, self.plan_cache))
                                logging.debug(f"Created basket_bartering_data_manager")
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
                                    logging.error(f"Can't find any symbol_overview with symbol "
                                                  f"{BasketCache.usd_fx_symbol} "
                                                  f"in phone_book service, retrying in next periodic cycle",
                                                  exc_info=True)
                            except Exception as e:
                                logging.exception(f"update_fx_symbol_overview_dict_from_http failed with "
                                                  f"exception: {e}")

                        # service loop: manage all sub-services within their private try-catch to allow high level
                        # service to remain partially operational even if some sub-service is not available for any reason
                        if not static_data_service_state.ready:
                            try:
                                self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                                BasketCache.static_data = self.static_data
                                if self.static_data is not None:
                                    static_dir: PurePath = PurePath(
                                        __file__).parent.parent / "scripts" / be_host / "static"
                                    self.static_data.refresh_autocomplete_list(static_dir, "schema")
                                    self.plan_cache.figi_to_sec_rec_dict = get_figi_to_sec_rec_dict(self.static_data)
                                    static_data_service_state.ready = True
                                    logging.debug("Marked static_data_service_state.ready True")
                                    # we just got static data - no need to sleep - force no sleep
                                    should_sleep = False
                                else:
                                    raise Exception(
                                        f"self.static_data did init to None, unexpected!!")
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                        else:
                            # refresh static data periodically (maybe more in future)
                            try:
                                self.static_data_periodic_refresh()
                            except Exception as exp:
                                static_data_service_state.handle_exception(exp)
                                static_data_service_state.ready = False  # forces re-init in next iteration

                        if self.service_ready:
                            if self.bartering_data_manager and self.bartering_data_manager.street_book_thread and not \
                                    self.bartering_data_manager.street_book_thread.is_alive():
                                self.bartering_data_manager.street_book_thread.join(timeout=20)
                                logging.warning(f"street_book_thread is not alive anymore - returning from "
                                                f"_app_launch_pre_thread_func for executor {self.port=}")
                                return

                        last_modified_timestamp = os.path.getmtime(config_yaml_path)
                        if self.config_yaml_last_modified_timestamp != last_modified_timestamp:
                            self.config_yaml_last_modified_timestamp = last_modified_timestamp

                            handle_refresh_configurable_data_members(self, self.config_key_to_data_member_name_dict,
                                                                     str(config_yaml_path))
                else:
                    should_sleep = True
            except Exception as exp:
                err_ = f"exception caught in _app_launch_pre_thread_func, {exp=}, sending again"
                logging.exception(err_)

    def set_log_simulator_file_name_n_path(self):
        self.simulate_config_yaml_file_path = (
                CURRENT_PROJECT_DIR / "data" / f"basket_simulate_config.yaml")
        self.log_dir_path = PurePath(__file__).parent.parent / "log"
        self.log_simulator_file_name = f"log_simulator_basket_logs_{self.datetime_fmt_str}.log"
        self.log_simulator_file_path = (CURRENT_PROJECT_DIR / "log" /
                                        f"log_simulator_basket_logs_{self.datetime_fmt_str}.log")

    def app_launch_pre(self):
        BasketBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        # to be called only after logger in initialized - to prevent getting overridden
        set_package_logger_level("filelock", logging.WARNING)

        if self.market.is_test_run:
            LogBarterSimulator.chore_create_async_callable = (
                BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_create_chore_journal_http)
            LogBarterSimulator.fill_create_async_callable = (
                BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_create_fills_journal_http)
            LogBarterSimulator.executor_port = be_port
            BarterSimulator.chore_create_async_callable = (
                BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_create_chore_journal_http)
            BarterSimulator.fill_create_async_callable = (
                BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_create_fills_journal_http)

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

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview],
                                                        symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(
            get_symbol_overview_from_symbol(symbol))

    async def get_top_of_book_from_symbol_query_pre(self, top_of_book_class_type: Type[TopOfBook], symbol: str):
        return await BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http(
            get_objs_from_symbol(symbol))

    async def create_basket_chore_pre(self, basket_chore_obj: BasketChore):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "create_basket_chore_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        if self.plan_cache.basket_id is not None:
            err_: str = (f"failed to create basket_chore_obj, {self.plan_cache.basket_id=} "
                         f"exists!;;;received: {basket_chore_obj}")
            logging.error(err_)
            raise HTTPException(detail=err_, status_code=400)
        # else not required: if basket_cache.basket_id exists that means basket chore already exists
        # Also basket_cache.basket_id is set in handle_basket_chore_get_by_id_ws called in
        # create_basket_chore_post

        new_chore_list: List[NewChore] = basket_chore_obj.new_chores
        if not new_chore_list:
            err_: str = "create_basket_chore_pre failed - no new chores found"
            logging.error(err_)
            raise HTTPException(detail=err_, status_code=400)

        new_chore_obj: NewChore
        for new_chore_obj in new_chore_list:
            # to start with setting state to pending
            new_chore_obj.chore_submit_state = ChoreSubmitType.ORDER_SUBMIT_PENDING
            new_chore_obj.ord_entry_time = pendulum.DateTime.utcnow()

    async def create_basket_chore_post(self, basket_chore_obj: BasketChore):
        self.bartering_data_manager.handle_basket_chore_get_all_ws_(basket_chore_obj)

    async def partial_update_basket_chore_pre(self, stored_basket_chore_obj_json: Dict[str, Any],
                                              updated_basket_chore_obj_json: Dict[str, Any]):
        if not self.service_ready:
            # raise service unavailable 503 exception, let the caller retry
            err_str_ = "partial_update_basket_chore_pre not ready - service is not initialized yet"
            logging.error(err_str_)
            raise HTTPException(status_code=503, detail=err_str_)

        # recovery run;
        if updated_basket_chore_obj_json.get("processing_level") == 1:  # recovery run / internal handled update
            # no further processing needed - we just need persistence in DB - let it through
            updated_basket_chore_obj_json["processing_level"] = 3
            return updated_basket_chore_obj_json
        elif not self.plan_cache.is_recovered_n_reconciled:  # non-internal updates allowed only after is is_recovered_n_reconciled
            err_ = (f"partial_update_basket_chore_pre failed; waiting for state recovered_n_reconciled to be True, "
                    f"found: {self.plan_cache.is_recovered_n_reconciled}")
            raise HTTPException(detail=err_, status_code=400)
        # else continue as normal # TODO: Remove Mkt Suffix if sent from UI [processing_level == 0|3]
        # reverts any prior DB saved level 3 back to level 0 - helps post to continue as normal
        updated_basket_chore_obj_json["processing_level"] = 0
        new_chore_list: List[Dict] = updated_basket_chore_obj_json.get("new_chores")
        id_to_stored_new_chore_dicts: Dict[int, Dict] = {}
        if (stored_new_chore_dict_list := stored_basket_chore_obj_json.get("new_chores")) and len(
                stored_new_chore_dict_list) > 0:
            for stored_new_chore_dict in stored_new_chore_dict_list:
                id_to_stored_new_chore_dicts[stored_new_chore_dict.get("_id")] = stored_new_chore_dict
        if new_chore_list:
            new_chore_dict: Dict
            for idx, new_chore_dict in enumerate(new_chore_list):
                if id_ := new_chore_dict.get("_id"):
                    stored_chore_obj_json = id_to_stored_new_chore_dicts.get(id_)
                    if stored_chore_obj_json is not None and (amend_tuple := self.plan_cache.is_amend(
                            stored_chore_obj_json, new_chore_dict)):
                        err_: str | None = None
                        chore_submit_state = stored_chore_obj_json.get("chore_submit_state")
                        if chore_submit_state in ["ORDER_SUBMIT_NA", "ORDER_SUBMIT_FAILED"]:
                            err_ = (f"partial_update_basket_chore_pre failed; {amend_tuple=} found for chore with "
                                    f"{chore_submit_state=} indicating closed chore ")
                        stored_pending_amd_qty = stored_chore_obj_json.get("pending_amd_qty")
                        stored_pending_amd_px = stored_chore_obj_json.get("pending_amd_px")
                        if stored_pending_amd_qty is not None and stored_pending_amd_qty != 0 and \
                                stored_pending_amd_qty != new_chore_dict.get("qty"):
                            err_ = (err_ or "")
                            err_ += (f"system has pending Amend QTY on {id_=}, {new_chore_dict.get('chore_id')=}, amend"
                                     f" sent to this chore can't be handled;;;{amend_tuple=}; {new_chore_dict=}; "
                                     f"{stored_chore_obj_json} ")
                        if stored_pending_amd_px is not None and math.isclose(stored_pending_amd_px, 0) and not \
                                math.isclose(stored_pending_amd_qty, new_chore_dict.get("px")):
                            err_ = (err_ or "")
                            err_ += (f"system has pending Amend PX on {id_=}, {new_chore_dict.get('chore_id')=}, amend"
                                     f" sent to this chore can't be handled;;;{amend_tuple=}; {new_chore_dict=}; "
                                     f"{stored_chore_obj_json} ")

                        if err_ is not None:
                            logging.error(err_)
                            raise HTTPException(status_code=400, detail=err_)

                        # no existing amend - validate amend_tuple and disallow via throw if invalid
                        amd_qty, amd_px = amend_tuple
                        if (amd_qty is not None and 0 == amd_qty) or (amd_px is not None and math.isclose(0, amd_px)):
                            err_ = (f"amend sent to this chore can't be handled; invalid {amd_qty=} or {amd_px=} "
                                    f"for {id_=}, of {new_chore_dict.get('chore_id')=};;;{new_chore_dict=}")
                            logging.error(err_)
                            raise HTTPException(status_code=400, detail=err_)
                    else:  # either stored_chore_obj_json is None or amend is None
                        if stored_chore_obj_json is None:
                            if new_chore_dict.get("chore_submit_state") is None:
                                # setting state to pending
                                new_chore_dict["chore_submit_state"] = ChoreSubmitType.ORDER_SUBMIT_PENDING
                                new_chore_dict["ord_entry_time"] = pendulum.DateTime.utcnow()
                                new_chore_dict["pending_cxl"] = False
                        # else: update with no amend, let it through
                # else not required - _id is always present
        return updated_basket_chore_obj_json

    async def partial_update_basket_chore_post(self, stored_basket_chore_obj_json: Dict[str, Any],
                                               updated_basket_chore_obj_json: Dict[str, Any]):
        updated_basket_chore_obj: BasketChore = BasketChore.from_dict(updated_basket_chore_obj_json)
        self.bartering_data_manager.handle_basket_chore_get_all_ws_(updated_basket_chore_obj)

    async def create_symbol_overview_pre(self, symbol_overview_obj: SymbolOverview):
        return create_symbol_overview_pre_helper(self.static_data, symbol_overview_obj)

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_create_symbol_overview_post(symbol_overview_obj)

    async def update_symbol_overview_pre(self, updated_symbol_overview_obj: SymbolOverview):
        stored_symbol_overview_obj = await (
            BasketBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_by_id_http(
                updated_symbol_overview_obj.id))
        return update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj,
                                                 updated_symbol_overview_obj)

    async def update_symbol_overview_post(self, updated_symbol_overview_obj: SymbolOverview):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_update_symbol_overview_post(updated_symbol_overview_obj)

    async def partial_update_symbol_overview_pre(self, stored_symbol_overview_obj_json: Dict[str, Any],
                                                 updated_symbol_overview_obj_json: Dict[str, Any]):
        return partial_update_symbol_overview_pre_helper(self.static_data, stored_symbol_overview_obj_json,
                                                         updated_symbol_overview_obj_json)

    async def partial_update_symbol_overview_post(self, updated_symbol_overview_obj_json: Dict[str, Any]):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_partial_update_symbol_overview_post(updated_symbol_overview_obj_json)

    async def create_top_of_book_post(self, top_of_book_obj: TopOfBook):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_create_top_of_book_post(top_of_book_obj)

    async def update_top_of_book_post(self, updated_top_of_book_obj: TopOfBook):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_update_top_of_book_post(updated_top_of_book_obj)

    async def partial_update_top_of_book_post(self, updated_top_of_book_obj_json: Dict[str, Any]):
        async with BasketBookServiceRoutesCallbackBaseNativeOverride.shared_md_lock:
            await self.handle_partial_update_top_of_book_post(updated_top_of_book_obj_json)

    async def barter_simulator_place_new_chore_query_pre(
            self, barter_simulator_process_new_chore_class_type: Type[BarterSimulatorProcessNewChore],
            px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str, symbol_type: str,
            underlying_account: str, exchange: str | None = None, internal_ord_id: str | None = None):
        if BarterSimulator.symbol_configs is None:
            BarterSimulator.reload_symbol_configs()
        await BarterSimulator.place_new_chore(px, qty, side, bartering_sec_id, system_sec_id, symbol_type,
                                             underlying_account, exchange, client_ord_id=internal_ord_id)
        return []

    async def create_chore_journal_pre(self, chore_journal_obj: ChoreJournal) -> None:
        await self.handle_create_chore_journal_pre(chore_journal_obj)

    async def create_chore_journal_post(self, chore_journal_obj: ChoreJournal):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_chore_journal_get_all_ws(chore_journal_obj)

        async with BasketBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            _ = await self._update_chore_snapshot_from_chore_journal(chore_journal_obj)

    async def partial_update_chore_journal_post(self, updated_chore_journal_obj_json: Dict[str, Any]):
        await self.handle_partial_update_chore_journal_post(updated_chore_journal_obj_json)

    async def create_fills_journal_pre(self, fills_journal_obj: FillsJournal):
        await self.handle_create_fills_journal_pre(fills_journal_obj)

    async def create_fills_journal_post(self, fills_journal_obj: FillsJournal):
        # updating bartering_data_manager's plan_cache
        self.bartering_data_manager.handle_fills_journal_get_all_ws(fills_journal_obj)

        async with BasketBookServiceRoutesCallbackBaseNativeOverride.journal_shared_lock:
            await self._apply_fill_update_in_chore_snapshot(fills_journal_obj)

    async def partial_update_fills_journal_post(self, updated_fills_journal_obj_json: Dict[str, Any]):
        await self.handle_partial_update_fills_journal_post(updated_fills_journal_obj_json)

    async def create_chore_snapshot_pre(self, chore_snapshot_obj: ChoreSnapshot):
        await self.handle_create_chore_snapshot_pre(chore_snapshot_obj)

    async def create_chore_snapshot_post(self, chore_snapshot_obj: ChoreSnapshot):
        await self.handle_create_chore_snapshot_post(chore_snapshot_obj)

    async def update_chore_snapshot_post(self, updated_chore_snapshot_obj: ChoreSnapshot):
        await self.handle_update_chore_snapshot_post(updated_chore_snapshot_obj)

    async def partial_update_chore_snapshot_post(self, updated_chore_snapshot_obj_json: Dict[str, Any]):
        await self.handle_partial_update_chore_snapshot_post(updated_chore_snapshot_obj_json)

    async def cancel_all_basket_chores(self) -> bool:
        """
        check and cancel all open chores in the basket
        """
        pass

    async def cancel_all_basket_chores_query_pre(self, cancel_all_basket_chores_cls_type: Type[CancelAllBasketChores]):
        # resp: bool await self.cancel_all_basket_chores()
        # cxl_basket_chore: CancelAllBasketChores = CancelAllBasketChores.from_kwargs(resp=resp)
        # return [cxl_basket_chore]
        pass

    async def create_or_update_basket_chore(self, new_chores: List[NewChore]):
        pass

    async def basket_chore_file_upload_query_pre(self, upload_file: UploadFile,
                                                 disallow_duplicate_file_upload: bool = False):
        pass

    def get_residual_mark_secs(self):
        pass

    async def update_pos_cache_by_ticker_query_pre(self, update_pos_cache_class_type: Type[UpdatePosCache],
                                                   ticker: str):
        pass
