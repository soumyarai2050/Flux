# standard imports
import asyncio
import os
import logging
from threading import Thread
from queue import Queue
import time
import datetime
from typing import Dict, Any, List, Callable, Tuple
import posix_ipc
from ib_insync import IB, Stock, Ticker
import pendulum
import math

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_routes_callback_imports import MobileBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_service_helper import (
    md_port, config_yaml_dict, config_yaml_path, is_service_up, is_view_service_up, get_realtime_price_limits)
from FluxPythonUtils.scripts.general_utility_functions import except_n_log_alert, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_shared_memory_producer import MobileBookSharedMemoryProducer
from ProjectGroup.mobile_book.app.mobile_book_service_helper import md_view_port
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.aggregate import (
    get_symbol_interest_from_symbol, get_symbol_overview_from_symbol)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import (
    SecurityRecordManager)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.service_state import ServiceState
from scripts.general_utility_functions import compare_n_patch_dict


class SemaphoreNSHMProducerContainer:
    def __init__(self, semaphore_list, shm_producer_obj):
        self.semaphore_list = semaphore_list
        self.shm_producer_obj = shm_producer_obj

class ReceivedQtyFoundDecimalValError(Exception):
    def __init__(self, message="Unsupported: Received float quantity that has a decimal value"):
        super().__init__(message)

class MobileBookServiceRoutesCallbackBaseNativeOverride(MobileBookServiceRoutesCallback):
    underlying_read_symbol_interests_by_id_http: Callable[..., Any] | None = None
    underlying_read_symbol_interests_http: Callable[..., Any] | None = None
    underlying_delete_symbol_interests_http: Callable[..., Any] | None = None
    underlying_remove_symbol_interest_by_symbol_query_http: Callable[..., Any] | None = None
    underlying_create_all_market_depth_http: Callable[..., Any] | None = None
    underlying_partial_update_all_market_depth_http: Callable[..., Any] | None = None
    underlying_create_last_barter_http: Callable[..., Any] | None = None
    underlying_get_symbol_overview_from_symbol_query_http: Callable[..., Any] | None = None
    underlying_create_top_of_book_http: Callable[..., Any] | None = None
    underlying_partial_update_top_of_book_http: Callable[..., Any] | None = None
    underlying_read_top_of_book_http: Callable[..., Any] | None = None
    underlying_read_market_depth_http: Callable[..., Any] | None = None
    underlying_read_symbol_overview_http: Callable[..., Any] | None = None
    underlying_create_all_symbol_overview_http: Callable[..., Any] | None = None
    underlying_read_last_barter_http: Callable[..., Any] | None = None
    underlying_update_symbol_overview_http: Callable[..., Any] | None = None
    underlying_partial_update_symbol_overview_http: Callable[..., Any] | None = None
    underlying_partial_update_all_symbol_overview_http: Callable[..., Any] | None = None

    def __init__(self):
        super().__init__()
        self.port = None
        self.service_up = False
        self.service_ready = False
        self.config_yaml_last_modified_timestamp = os.path.getmtime(config_yaml_path)
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.min_refresh_interval: int = parse_to_int(config_yaml_dict.get("min_refresh_interval"))
        if self.min_refresh_interval is None:
            self.min_refresh_interval = 30
        self.depth_count = config_yaml_dict.get("market_depth_count", 10)        # default length 10
        self.symbol_to_mobile_book_db_id_dict: Dict[str, Dict[str, List[int | None], int]] = {}
        self.symbol_to_mobile_book_db_id_dict_async_lock: AsyncRLock = AsyncRLock()
        self.id_to_symbol_overview_cache_dict: Dict[int, SymbolOverview] = {}
        self.id_to_tob_cache_dict: Dict[int, TopOfBook] = {}
        self.id_to_last_barter_cache_dict: Dict[int, LastBarter] = {}
        self.id_to_md_cache_dict: Dict[int, MarketDepth] = {}
        self.ticker_update_queue: Queue[Any] = Queue()
        self.symbol_to_sem_n_producer_container_dict: Dict[str, SemaphoreNSHMProducerContainer] = {}
        self.symbol_to_sem_n_producer_container_dict_async_lock: AsyncRLock = AsyncRLock()
        self.static_data: SecurityRecordManager | None = None
        self.ib = IB()
        self.ib_tickers: Dict[str, Tuple[Ticker, Ticker]] = {}
        self.is_ib_connected = None

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_msgspec_routes import (
            underlying_read_symbol_interests_by_id_http, underlying_read_symbol_interests_http,
            underlying_delete_symbol_interests_http, underlying_remove_symbol_interest_by_symbol_query_http,
            underlying_create_all_market_depth_http, underlying_partial_update_all_market_depth_http,
            underlying_create_last_barter_http, underlying_get_symbol_overview_from_symbol_query_http,
            underlying_create_top_of_book_http, underlying_partial_update_top_of_book_http,
            underlying_read_top_of_book_http, underlying_read_market_depth_http,
            underlying_read_symbol_overview_http, underlying_create_all_symbol_overview_http,
            underlying_update_symbol_overview_http, underlying_read_last_barter_http,
            underlying_partial_update_all_symbol_overview_http, underlying_partial_update_symbol_overview_http)
        cls.underlying_read_symbol_interests_by_id_http = underlying_read_symbol_interests_by_id_http
        cls.underlying_read_symbol_interests_http = underlying_read_symbol_interests_http
        cls.underlying_delete_symbol_interests_http = underlying_delete_symbol_interests_http
        cls.underlying_remove_symbol_interest_by_symbol_query_http = underlying_remove_symbol_interest_by_symbol_query_http
        cls.underlying_create_all_market_depth_http = underlying_create_all_market_depth_http
        cls.underlying_partial_update_all_market_depth_http = underlying_partial_update_all_market_depth_http
        cls.underlying_create_last_barter_http = underlying_create_last_barter_http
        cls.underlying_get_symbol_overview_from_symbol_query_http = underlying_get_symbol_overview_from_symbol_query_http
        cls.underlying_create_top_of_book_http = underlying_create_top_of_book_http
        cls.underlying_partial_update_top_of_book_http = underlying_partial_update_top_of_book_http
        cls.underlying_read_top_of_book_http = underlying_read_top_of_book_http
        cls.underlying_read_market_depth_http = underlying_read_market_depth_http
        cls.underlying_read_symbol_overview_http = underlying_read_symbol_overview_http
        cls.underlying_create_all_symbol_overview_http = underlying_create_all_symbol_overview_http
        cls.underlying_read_last_barter_http = underlying_read_last_barter_http
        cls.underlying_update_symbol_overview_http = underlying_update_symbol_overview_http
        cls.underlying_partial_update_all_symbol_overview_http = underlying_partial_update_all_symbol_overview_http
        cls.underlying_partial_update_symbol_overview_http = underlying_partial_update_symbol_overview_http

    def app_launch_pre(self):
        MobileBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = md_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def connect_ibkr_async(self):
        run_coro = self._connect_ibkr_async()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            future.result()
            return True
        except Exception as e:
            err_str_ = (f"_connect_ibkr_async failed with exception: {e}")
            logging.exception(err_str_)
            return False

    async def _connect_ibkr_async(self):
        try:
            logging.info("Connecting to IBKR...")
            await self.ib.connectAsync('127.0.0.1', 7497, clientId=1)
            logging.info("Successfully connected to IBKR.")
            # Set to live data
            self.ib.reqMobileBookType(1)
            logging.info("Requested live market data.")
            self.ib.pendingTickersEvent += self.on_pending_tickers_update
            logging.info("Registered pending tickers event handler.")
        except Exception as e:
            logging.error(f"Error connecting to IBKR: {e}", exc_info=True)

    def view_app_launch_pre(self):
        MobileBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = md_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

        # closing all cached shared memory producers - not taking lock since async loop is closed by this point
        # and no subsiquent read to this dict can be done in async loop
        for symbol, sem_n_shm_producer_container_obj in self.symbol_to_sem_n_producer_container_dict.items():
            for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
                try:
                    semaphore.close()
                    logging.debug(f"SEM for {symbol} closed.")
                except Exception as e:
                    logging.error(f"Error closing SEM for {symbol}: {e}", exc_info=True)
            sem_n_shm_producer_container_obj.shm_producer_obj.close()

        if self.ib.isConnected():
            self.ib.disconnect()
            logging.info("Disconnected from IBKR.")

    def view_app_launch_post(self):
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
        recovered_cache = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"mobile_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up and recovered_cache:
                    if not self.service_ready:
                        try:
                            self.load_symbol_overview_from_static_data()
                        except Exception:
                            logging.exception("Something went wrong while loading symbol overview from static data - "
                                              "will retry in next loop")
                        else:
                            Thread(target=self.pending_tickers_update_listener, daemon=True).start()

                            self.service_ready = True
                            # print is just to manually check if this server is ready - useful when we run
                            # multiple servers and before running any test we want to make sure servers are up
                            print(f"INFO: Market data service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    # service loop: manage all sub-services within their private try-catch to allow high level
                    # service to remain partially operational even if some sub-service is not available for any reason
                    if not static_data_service_state.ready:
                        try:
                            self.static_data = SecurityRecordManager.get_loaded_instance(from_cache=True)
                            if self.static_data is not None:
                                static_data_service_state.ready = True
                                logging.debug(
                                    f"Marked static_data_service_state.ready True")
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

                    if not self.is_ib_connected:
                        if not config_yaml_dict.get("ibkr_connection_enabled", True):
                            logging.info("IBKR connection is disabled in config. Skipping connection.")
                            self.is_ib_connected = True
                        else:
                            logging.info("Creating IBKR connection task.")
                            self.is_ib_connected = self.connect_ibkr_async()

                    if not recovered_cache:
                        self.recover_cache()
                        recovered_cache = True
            else:
                should_sleep = True

    def load_symbol_overview_from_static_data(self):
        run_coro = self._load_symbol_overview_from_static_data()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"_load_symbol_overview_from_static_data failed with exception: {e}")
            raise e

    async def _load_symbol_overview_from_static_data(self):
        symbol_overview_list: List[SymbolOverview] = \
            await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http()
        existing_ticker_list = [symbol_overview.symbol for symbol_overview in symbol_overview_list]

        create_symbol_overview_list: List[SymbolOverview] = []
        for ticker, sec_record in self.static_data.barter_ready_records_by_ticker.items():
            if ticker not in existing_ticker_list:
                symbol_overview = SymbolOverview.from_kwargs(symbol=ticker,
                                                             exchange_code=sec_record.exchange_code)
                create_symbol_overview_list.append(symbol_overview)
        if create_symbol_overview_list:
            await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_symbol_overview_http(
                create_symbol_overview_list)

    def static_data_periodic_refresh(self):
        # no action required if refreshed
        self.static_data.refresh()

    @except_n_log_alert()
    def _view_app_launch_pre_thread_func(self):
        """
        sleep wait till engine is up
        TODO LAZY: we should invoke _apply_checks_n_alert on all active pair plans at startup/re-start
        """

        error_prefix = "_app_launch_pre_thread_func: "
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        mongo_stream_started = False
        while True:
            if should_sleep:
                time.sleep(self.min_refresh_interval)
            service_up_flag_env_var = os.environ.get(f"mobile_book_{self.port}")

            if service_up_flag_env_var == "1":
                # validate essential services are up, if so, set service ready state to true
                if self.service_up:
                    if not self.service_ready:
                        self.service_ready = True
                        # print is just to manually check if this server is ready - useful when we run
                        # multiple servers and before running any test we want to make sure servers are up
                        print(f"INFO: Market data service is ready: {datetime.datetime.now().time()}")

                if not self.service_up:
                    try:
                        if is_view_service_up(ignore_error=(service_up_no_error_retry_count > 0)):
                            self.service_up = True
                            should_sleep = False
                    except Exception as e:
                        logging.exception("unexpected: service startup threw exception, "
                                          f"we'll retry periodically in: {self.min_refresh_interval} seconds"
                                          f";;;exception: {e}", exc_info=True)
                else:
                    should_sleep = True
                    # any periodic refresh code goes here

                    if not mongo_stream_started:
                        self.start_mongo_streamer()
                        self.mongo_stream_started = True
            else:
                should_sleep = True

    def start_mongo_streamer(self):
        run_coro = self._start_mongo_streamer()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        # block for task to finish
        try:
            future.result()
        except Exception as e:
            logging.exception(f"start_mongo_streamer failed with exception: {e}")

    async def _recover_cache(self):
        async with SymbolInterests.reentrant_lock:
            symbol_interests_obj_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_interests_http()

            non_existing_symbol_interests_obj_list = []
            for symbol_interests_obj in symbol_interests_obj_list:
                try:
                    await self.register_symbol_n_sem(symbol_interests_obj)
                except posix_ipc.ExistentialError as e_:
                    # shared memory doesn't exist yet
                    err_str = (f"Can't find semaphore with name {symbol_interests_obj.semaphore_full_path} "
                               f"for symbol: {symbol_interests_obj.symbol_name} while recovery - removing this "
                               f"entry;;; error: {e_}")
                    logging.error(err_str)
                    non_existing_symbol_interests_obj_list.append(symbol_interests_obj)

            for symbol_interests_obj in non_existing_symbol_interests_obj_list:
                await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_remove_symbol_interest_by_symbol_query_http(
                    symbol_interests_obj.symbol_name)
                logging.info(f"removed non-existing symbol interests entry: {symbol_interests_obj} "
                             f"found while recovery")

        async with SymbolOverview.reentrant_lock:
            symbol_overview_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http()
            for symbol_overview in symbol_overview_list:
                self.id_to_symbol_overview_cache_dict[symbol_overview.id] = symbol_overview

        async with TopOfBook.reentrant_lock:
            async with self.symbol_to_mobile_book_db_id_dict_async_lock:
                if not config_yaml_dict.get("avoid_top_of_book_db_n_ws_update"):
                    top_of_book_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_top_of_book_http()
                    for top_of_book in top_of_book_list:
                        self.id_to_tob_cache_dict[top_of_book.id] = top_of_book
                        self.symbol_to_mobile_book_db_id_dict[top_of_book.symbol] = {"tob": top_of_book.id,
                                                                                     TickType.ASK: [None] * self.depth_count,
                                                                                     TickType.BID: [None] * self.depth_count}

        async with MarketDepth.reentrant_lock:
            async with self.symbol_to_mobile_book_db_id_dict_async_lock:
                if not config_yaml_dict.get("avoid_market_depth_db_n_ws_update"):
                    market_depth_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_market_depth_http()
                    for market_depth in market_depth_list:
                        self.id_to_md_cache_dict[market_depth.id] = market_depth
                        self.symbol_to_mobile_book_db_id_dict[market_depth.symbol][market_depth.side][market_depth.position-1] = market_depth.id

        async with LastBarter.reentrant_lock:
            if not config_yaml_dict.get("avoid_last_barter_db_n_ws_update"):
                last_barter_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_last_barter_http()
                for last_barter in last_barter_list:
                    self.id_to_last_barter_cache_dict[last_barter.id] = last_barter


    def recover_cache(self):
        run_coro = self._recover_cache()
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            future.result()
        except Exception as e:
            err_str_ = (f"_recover_cache failed with exception: {e}")
            logging.exception(err_str_)
            raise Exception(err_str_)

    async def get_sem_n_shm_producer_cont_obj(
            self, symbol: str) -> SemaphoreNSHMProducerContainer:
        async with self.symbol_to_sem_n_producer_container_dict_async_lock:
            sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = (
                self.symbol_to_sem_n_producer_container_dict.get(symbol))
            if sem_n_shm_producer_container_obj is not None:
                return sem_n_shm_producer_container_obj
            else:
                raise HTTPException(
                    status_code=400, detail=f"Can't find sem_n_shm_producer_container_obj for symbol: {symbol}")

    async def _update_last_barter_cache_n_shm(self, last_barter_obj: LastBarter):
        # updating cache for last barter
        self.id_to_last_barter_cache_dict[last_barter_obj.id] = last_barter_obj

        sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
            await self.get_sem_n_shm_producer_cont_obj(last_barter_obj.symbol_n_exch_id.symbol)
        shm_producer = sem_n_shm_producer_container_obj.shm_producer_obj
        shm_producer.update_last_barter_shm_from_msgspec_obj(last_barter_obj)

        async with self.symbol_to_mobile_book_db_id_dict_async_lock:
            # Update Top of Book
            tob_update_data = {
                "_id": self.symbol_to_mobile_book_db_id_dict[last_barter_obj.symbol_n_exch_id.symbol]["tob"],
                "symbol": last_barter_obj.symbol_n_exch_id.symbol,
                "last_update_date_time": last_barter_obj.exch_time,
                "last_barter": {
                    "px": last_barter_obj.px,
                    "qty": last_barter_obj.qty,
                    "last_update_date_time": last_barter_obj.exch_time
                }
            }
        await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_top_of_book_http(
            tob_update_data)

        for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
            semaphore.release()

    async def create_last_barter_pre(self, last_barter_obj: LastBarter):
        await self._update_last_barter_cache_n_shm(last_barter_obj)

    async def create_all_last_barter_pre(self, last_barter_obj_list: List[LastBarter]):
        for last_barter_obj in last_barter_obj_list:
            await self._update_last_barter_cache_n_shm(last_barter_obj)

    async def _update_market_depth_shm(self, market_depth_obj: MarketDepth):
        sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
            await self.get_sem_n_shm_producer_cont_obj(market_depth_obj.symbol)
        shm_producer: MobileBookSharedMemoryProducer = sem_n_shm_producer_container_obj.shm_producer_obj
        shm_producer.update_market_depth_shm_from_msgspec_obj(market_depth_obj)

        if market_depth_obj.position == 0:
            async with self.symbol_to_mobile_book_db_id_dict_async_lock:
                tob_update_data: Dict[str, Any] = {
                    "_id": self.symbol_to_mobile_book_db_id_dict[market_depth_obj.symbol]["tob"],
                    "symbol": market_depth_obj.symbol,
                    "last_update_date_time": market_depth_obj.exch_time
                }
            quote = {"px": market_depth_obj.px, "qty": market_depth_obj.qty,
                     "last_update_date_time": market_depth_obj.exch_time}
            if market_depth_obj.side == TickType.BID:
                tob_update_data["bid_quote"] = quote
            else:
                tob_update_data["ask_quote"] = quote

            await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_top_of_book_http(
                tob_update_data)

        for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
            semaphore.release()

    async def _update_market_depth_cache_n_shm(self, market_depth_obj: MarketDepth):
        # updating cache
        self.id_to_md_cache_dict[market_depth_obj.id] = market_depth_obj

        # updating shm
        await self._update_market_depth_shm(market_depth_obj)

    async def _partial_update_market_depth_cache_n_shm(self, market_depth_patch_dict: Dict):
        # updating cache
        market_depth_obj = self.id_to_md_cache_dict.get(market_depth_patch_dict.get("_id"))
        patched_dict = compare_n_patch_dict(market_depth_obj.to_dict(), market_depth_patch_dict)
        market_depth_obj = MarketDepth.from_dict(patched_dict)
        self.id_to_md_cache_dict[market_depth_obj.id] = market_depth_obj

        # updating shm
        await self._update_market_depth_shm(market_depth_obj)
        return patched_dict

    async def create_market_depth_pre(self, market_depth_obj: MarketDepth):
        await self._update_market_depth_cache_n_shm(market_depth_obj)

    async def create_all_market_depth_pre(self, market_depth_obj_list: List[MarketDepth]):
        for market_depth_obj in market_depth_obj_list:
            await self._update_market_depth_cache_n_shm(market_depth_obj)

    async def update_market_depth_pre(self, updated_market_depth_obj: MarketDepth):
        await self._update_market_depth_cache_n_shm(updated_market_depth_obj)
        return updated_market_depth_obj

    async def update_all_market_depth_pre(self, updated_market_depth_obj_list: List[MarketDepth]):
        for market_depth_obj in updated_market_depth_obj_list:
            await self._update_market_depth_cache_n_shm(market_depth_obj)
        return updated_market_depth_obj_list

    async def partial_update_market_depth_pre(self, stored_market_depth_obj_json: Dict[str, Any],
                                              updated_market_depth_obj_json: Dict[str, Any]):
        return await self._partial_update_market_depth_cache_n_shm(updated_market_depth_obj_json)

    async def partial_update_all_market_depth_pre(self, stored_market_depth_dict_list: List[Dict[str, Any]],
                                                  updated_market_depth_dict_list: List[Dict[str, Any]]):
        market_depth_patched_dict_list: List[Dict] = []
        for market_depth_obj_dict in updated_market_depth_dict_list:
            market_depth_patched_dict = await self._partial_update_market_depth_cache_n_shm(market_depth_obj_dict)
            market_depth_patched_dict_list.append(market_depth_patched_dict)
        return market_depth_patched_dict_list

    async def _update_top_of_book_shm(self, top_of_book_obj: TopOfBook):
        sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
            await self.get_sem_n_shm_producer_cont_obj(top_of_book_obj.symbol)
        shm_producer: MobileBookSharedMemoryProducer = sem_n_shm_producer_container_obj.shm_producer_obj
        shm_producer.update_top_of_book_shm_from_msgspec_obj(top_of_book_obj)

        for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
            semaphore.release()

    async def _update_tob_cache_n_shm(self, top_of_book_obj: TopOfBook):
        # updating cache
        self.id_to_tob_cache_dict[top_of_book_obj.id] = top_of_book_obj

        # updating shm
        await self._update_top_of_book_shm(top_of_book_obj)

    async def _partial_update_tob_cache_n_shm(self, top_of_book_patch_dict: Dict):
        # updating cache
        top_of_book_obj = self.id_to_tob_cache_dict.get(top_of_book_patch_dict.get("_id"))
        patched_dict = compare_n_patch_dict(top_of_book_obj.to_dict(), top_of_book_patch_dict)
        top_of_book_obj = TopOfBook.from_dict(patched_dict)
        self.id_to_tob_cache_dict[top_of_book_obj.id] = top_of_book_obj

        # updating shm
        await self._update_top_of_book_shm(top_of_book_obj)
        return patched_dict

    async def create_top_of_book_pre(self, top_of_book_obj: TopOfBook):
        await self._update_tob_cache_n_shm(top_of_book_obj)

    async def create_all_top_of_book_pre(self, top_of_book_obj_list: List[TopOfBook]):
        for top_of_book_obj in top_of_book_obj_list:
            await self._update_tob_cache_n_shm(top_of_book_obj)

    async def update_top_of_book_pre(self, updated_top_of_book_obj: TopOfBook):
        await self._update_tob_cache_n_shm(updated_top_of_book_obj)
        return updated_top_of_book_obj

    async def update_all_top_of_book_pre(self, updated_top_of_book_obj_list: List[TopOfBook]):
        for tob in updated_top_of_book_obj_list:
            await self._update_tob_cache_n_shm(tob)
        return updated_top_of_book_obj_list

    async def partial_update_top_of_book_pre(
        self, stored_top_of_book_obj_json: Dict[str, Any], updated_top_of_book_obj_json: Dict[str, Any]):
        return await self._partial_update_tob_cache_n_shm(updated_top_of_book_obj_json)

    async def partial_update_all_top_of_book_pre(
        self, stored_top_of_book_dict_list: List[Dict[str, Any]], updated_top_of_book_dict_list: List[Dict[str, Any]]):
        tob_patched_dict_list: List[Dict] = []
        for updated_top_of_book_obj_json in updated_top_of_book_dict_list:
            tob_patched_dict = await self._partial_update_tob_cache_n_shm(updated_top_of_book_obj_json)
            tob_patched_dict_list.append(tob_patched_dict)
        return tob_patched_dict_list

    async def _update_symbol_overview_shm(self, symbol_overview_obj: SymbolOverview):
        sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
            await self.get_sem_n_shm_producer_cont_obj(symbol_overview_obj.symbol)
        shm_producer = sem_n_shm_producer_container_obj.shm_producer_obj
        shm_producer.update_symbol_overview_shm_from_msgspec_obj(symbol_overview_obj)

        for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
            semaphore.release()

    async def _update_symbol_overview_cache_n_shm(self, symbol_overview_obj: SymbolOverview):
        # cache update
        self.id_to_symbol_overview_cache_dict[symbol_overview_obj.id] = symbol_overview_obj

        # shm update
        await self._update_symbol_overview_shm(symbol_overview_obj)

    async def _partial_update_symbol_overview_cache_n_shm(self, symbol_overview_patch_dict: Dict):
        # cache update
        symbol_overview_obj = self.id_to_symbol_overview_cache_dict.get(symbol_overview_patch_dict.get("_id"))
        patched_dict = compare_n_patch_dict(symbol_overview_obj.to_dict(), symbol_overview_patch_dict)
        symbol_overview_obj = SymbolOverview.from_dict(patched_dict)
        self.id_to_symbol_overview_cache_dict[symbol_overview_obj.id] = symbol_overview_obj

        # shm update
        await self._update_symbol_overview_shm(symbol_overview_obj)
        return patched_dict

    async def create_symbol_overview_pre(self, symbol_overview_obj: SymbolOverview):
        # not updating shm since symbol overviews are created at market data service start-up using static data
        # and by that time symbol_interests are not registered by clients so no shm exists - shm will be updated
        # once symbol_interest is created by explicit handling
        self.id_to_symbol_overview_cache_dict[symbol_overview_obj.id] = symbol_overview_obj

    async def create_all_symbol_overview_pre(self, symbol_overview_obj_list: List[SymbolOverview]):
        # not updating shm since symbol overviews are created at market data service start-up using static data
        # and by that time symbol_interests are not registered by clients so no shm exists - shm will be updated
        # once symbol_interest is created by explicit handling
        for symbol_overview_obj in symbol_overview_obj_list:
            self.id_to_symbol_overview_cache_dict[symbol_overview_obj.id] = symbol_overview_obj

    async def update_symbol_overview_pre(self, updated_symbol_overview_obj: SymbolOverview):
        await self._update_symbol_overview_cache_n_shm(updated_symbol_overview_obj)
        return updated_symbol_overview_obj

    async def update_all_symbol_overview_pre(self, updated_symbol_overview_obj_list: List[SymbolOverview]):
        for symbol_overview_obj in updated_symbol_overview_obj_list:
            await self._update_symbol_overview_cache_n_shm(symbol_overview_obj)
        return updated_symbol_overview_obj_list

    async def partial_update_symbol_overview_pre(
            self, stored_symbol_overview_obj_json: Dict[str, Any], updated_symbol_overview_obj_json: Dict[str, Any]):
        return await self._partial_update_symbol_overview_cache_n_shm(updated_symbol_overview_obj_json)

    async def partial_update_all_symbol_overview_pre(
            self, stored_symbol_overview_dict_list: List[Dict[str, Any]], updated_symbol_overview_dict_list: List[Dict[str, Any]]):
        symbol_overview_patched_dict_list: List[Dict] = []
        for symbol_overview_obj_dict in updated_symbol_overview_dict_list:
            symbol_overview_patched_dict = await self._partial_update_symbol_overview_cache_n_shm(symbol_overview_obj_dict)
            symbol_overview_patched_dict_list.append(symbol_overview_patched_dict)
        return symbol_overview_patched_dict_list

    async def get_symbol_overview_from_symbol_query_pre(self, symbol_overview_class_type: Type[SymbolOverview], symbol: str):
        return await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_overview_http(get_symbol_overview_from_symbol(symbol))

    async def on_pending_tickers_update(self, tickers: List[Ticker]):
        self.ticker_update_queue.put(tickers)

    def pending_tickers_update_listener(self):
        while True:
            tickers = self.ticker_update_queue.get()
            if not tickers:
                continue

            symbol_overview_patch_list: List[Dict] = []
            for ticker in tickers:
                # For simplicity, printing the ticker object.
                # In a real application, you would populate your data models here.
                logging.debug(f"Market data update for {ticker.contract.symbol}: {ticker}")

                # region symbol overview update
                run_coro = MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_get_symbol_overview_from_symbol_query_http(ticker.contract.symbol)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                try:
                    # block for task to finish
                    symbol_overview_list: List[SymbolOverview] = future.result()
                    if symbol_overview_list:
                        symbol_overview = symbol_overview_list[0]

                        bartering_currency = self.get_bartering_currency(symbol_overview.symbol)
                        if bartering_currency is not None:
                            run_coro = get_realtime_price_limits(self.ib, symbol_overview.symbol,
                                                                 bartering_currency, symbol_overview.exchange_code,
                                                                 ticker)
                            future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                            limit_data_dict = future.result()
                            if limit_data_dict.get("error") is not None:
                                logging.error("Something went wrong while getting realtime price limits - ignoring "
                                              f"symbol overview limit up and down price update for "
                                              f"symbol: {symbol_overview.symbol} ;;; error: {limit_data_dict.get("error")}")
                                limit_up_px = None
                                limit_dn_px = None
                            else:
                                limit_up_px = limit_data_dict.get("limit_up_price")
                                limit_dn_px = limit_data_dict.get("limit_dn_price")
                        else:
                            logging.error("Unexpected: Can't find bartering currency from static data - ignoring "
                                          f"symbol overview limit up and down price update for symbol: {symbol_overview.symbol}")
                            limit_up_px = None
                            limit_dn_px = None

                        symbol_overview_patch = {"_id": symbol_overview.id}
                        if ticker.open and not math.isnan(ticker.open):
                            symbol_overview_patch["open_px"] = ticker.open
                        if ticker.high and not math.isnan(ticker.high):
                            symbol_overview_patch["high"] = ticker.high
                        if ticker.low and not math.isnan(ticker.low):
                            symbol_overview_patch["low"] = ticker.low
                        if ticker.close and not math.isnan(ticker.close):
                            symbol_overview_patch["closing_px"] = ticker.close
                        if ticker.volume and not math.isnan(ticker.volume):
                            try:
                                vol = int(ticker.volume)
                                if not math.isclose(ticker.volume - vol, 0):
                                    raise ReceivedQtyFoundDecimalValError()
                                # else not required: using int casted last barter qty
                                symbol_overview_patch["volume"] = vol
                            except ReceivedQtyFoundDecimalValError:
                                logging.exception("Found Vol having some decimal value when subtracting actual "
                                                  "value with its int casted value - ignoring volume update in "
                                                  f"SymbolOverview for symbol: {symbol_overview.symbol}")
                        if limit_up_px is not None:
                            symbol_overview_patch["limit_up_px"] = limit_up_px
                        if limit_dn_px is not None:
                            symbol_overview_patch["limit_dn_px"] = limit_dn_px

                        if len(symbol_overview_patch) > 1:
                            symbol_overview_patch["last_update_date_time"] = (
                                pendulum.from_timestamp(ticker.time.timestamp()) if ticker.time else DateTime.utcnow())
                            symbol_overview_patch_list.append(symbol_overview_patch)

                except Exception as e:
                    err_str_ = f"Something went wrong in pending_tickers_update_listener exception: {e}"
                    logging.exception(err_str_)
                # endregion

                if ticker.last:
                    try:
                        if ticker.lastSize and not math.isnan(ticker.lastSize):
                            last_barter_qty = int(ticker.lastSize)
                            if not math.isclose(ticker.lastSize - last_barter_qty, 0):
                                raise ReceivedQtyFoundDecimalValError()
                            # else not required: using int casted last barter qty
                        else:
                            last_barter_qty = 0
                    except ReceivedQtyFoundDecimalValError:
                        logging.exception(
                            "Unsupported: Found last barter qty to be having diff when subtracted with casted int value, "
                            "last barter qty has some decimal values which is unsupported - ignoring last barter shm "
                            f"update for this ticker update;;; {ticker=}")
                    else:
                        last_barter = LastBarter(
                            symbol_n_exch_id=SymbolNExchId(symbol=ticker.contract.symbol, exch_id=ticker.contract.exchange),
                            exch_time=pendulum.from_timestamp(ticker.time.timestamp()) if ticker.time else DateTime.utcnow(),
                            arrival_time=DateTime.utcnow(),
                            px=ticker.last,
                            qty = last_barter_qty
                        )
                        if os.environ.get("DEBUG_DATA"):
                            print(f"Last barter: {last_barter=}")
                        run_coro =  MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_create_last_barter_http(last_barter)
                        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                        try:
                            # block for task to finish
                            future.result()
                        except Exception as e:
                            err_str_ = f"underlying_create_last_barter_http failed with exception: {e}"
                            logging.exception(err_str_)
                    # else not required: last barter qty being None is error case - ignoring any shm update for it

                if ticker.domBids and ticker.domAsks:
                    market_depth_bids = self.get_market_depth_dict_list_from_ticker(ticker, TickType.BID)
                    market_depth_asks = self.get_market_depth_dict_list_from_ticker(ticker, TickType.ASK)
                    if os.environ.get("DEBUG_DATA"):
                        for md in market_depth_bids:
                            print(f"Bid Market Depth: {md}")
                        for md in market_depth_asks:
                            print(f"Ask Market Depth: {md}")

                    if combined_md:=(market_depth_bids + market_depth_asks):
                        run_coro = MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_all_market_depth_http(
                            combined_md)
                        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                        try:
                            # block for task to finish
                            future.result()
                        except Exception as e:
                            err_str_ = (f"underlying_partial_update_all_market_depth_http failed with exception: {e}")
                            logging.exception(err_str_)
                    # else not required: avoiding patch with empty list

            if symbol_overview_patch_list:
                run_coro = MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_all_symbol_overview_http(symbol_overview_patch_list)
                future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
                try:
                    # block for task to finish
                    future.result()
                except Exception as e:
                    err_str_ = f"underlying_partial_update_all_symbol_overview_http failed with exception: {e}"
                    logging.exception(err_str_)

    def get_market_depth_dict_list_from_ticker(self, ticker: Ticker, side: TickType):
        run_coro = self._get_market_depth_dict_list_from_ticker(ticker, side)
        future = asyncio.run_coroutine_threadsafe(run_coro, self.asyncio_loop)
        try:
            # block for task to finish
            return future.result()
        except Exception as e:
            err_str_ = (f"get_market_depth_dict_list_from_ticker failed with exception: {e}")
            logging.exception(err_str_)
            return None

    async def _get_market_depth_dict_list_from_ticker(self, ticker: Ticker, side: TickType):
        if side == TickType.BID:
            depths = ticker.domBids
        elif side == TickType.ASK:
            depths = ticker.domAsks
        else:
            logging.error("Unsupported side passed to get depths from ticker - ignoring shm update for market "
                          f"depths received in ticker update, {side=};;; {ticker=}")
            return []

        async with self.symbol_to_mobile_book_db_id_dict_async_lock:
            bid_n_ask_market_depth_id_list_dict = self.symbol_to_mobile_book_db_id_dict.get(ticker.contract.symbol)
            # Use the ticker's timestamp for the exchange time, with a fallback to now().
            exchange_time = pendulum.from_timestamp(ticker.time.timestamp()) if ticker.time else DateTime.utcnow()
            arrival_time = DateTime.utcnow()

            market_depths = []
            for i, depth in enumerate(depths):
                try:
                    if depth.size and not math.isnan(depth.size):
                        depth_qty = int(depth.size)
                        if not math.isclose(depth.size - depth_qty, 0):
                            raise ReceivedQtyFoundDecimalValError()
                        # else not required: using int casted depth qty
                    else:
                        depth_qty = 0
                except ReceivedQtyFoundDecimalValError:
                    logging.exception(
                        "Unsupported: Found market depth qty to be having diff when subtracted with casted int value, "
                        "last barter qty has some decimal values which is unsupported - ignoring this market depth shm "
                        f"update for this ticker update;;; {ticker=}")
                else:
                    market_depths.append(
                        {
                            "_id": bid_n_ask_market_depth_id_list_dict[side][i],
                            "symbol": ticker.contract.symbol,
                            "exch_time": exchange_time,
                            "arrival_time": arrival_time,
                            "side": side,
                            "px": depth.price,
                            "qty": depth_qty,
                            "position": i
                        }
                    )
            return market_depths


    def get_bartering_currency(self, symbol: str):
        barter_records = self.static_data.barter_ready_records_by_ticker.get(symbol)
        if barter_records is None:
            logging.error(f"Can't find barter record for symbol: {symbol=} from static data - ignoring market "
                          f"subscription for this symbol")
            return None
        if barter_records.barteringCurrency is None:
            logging.error(f"Can't find barteringCurrency record for symbol: {symbol=} from static data - ignoring market "
                          f"subscription for this symbol")
            return None
        return barter_records.barteringCurrency

    async def subscribe_symbol_for_mobile_book(self, symbol: str):
        if not config_yaml_dict.get("ibkr_connection_enabled", True):
            logging.info("IBKR connection is disabled in config. Skipping subscription.")
            return
        if not self.ib.isConnected():
            await self._connect_ibkr_async()

        if not self.ib.isConnected():
            logging.error("IBKR not connected. Cannot subscribe to market data.")
            return None

        if symbol in self.ib_tickers:
            logging.warning(f"Already subscribed to {symbol}. Ignoring request.")
            return None

        symbol_overview_list: List[SymbolOverview] = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_get_symbol_overview_from_symbol_query_http(symbol)

        bartering_currency = self.get_bartering_currency(symbol)
        if bartering_currency is None:
            # error logged in get_bartering_currency
            return None

        symbol_overview = symbol_overview_list[0]
        contract = Stock(symbol, symbol_overview.exchange_code, bartering_currency)
        # contract = Stock(symbol, "TSE", 'CAD')
        contracts = await self.ib.qualifyContractsAsync(contract)
        if not contracts:
            logging.error(f"Could not qualify contract for {symbol}")
            return
        qualified_contract = contracts[0]

        # Get contract details for lot_size and tick_size
        contract_details_list = await self.ib.reqContractDetailsAsync(qualified_contract)
        if contract_details_list:
            contract_details = contract_details_list[0]

            symbol_overview_patch = {}
            if contract_details.mdSizeMultiplier and not math.isnan(contract_details.mdSizeMultiplier):
                try:
                    lot_size = int(contract_details.mdSizeMultiplier)
                    if not math.isclose(contract_details.mdSizeMultiplier - lot_size, 0):
                        raise ReceivedQtyFoundDecimalValError()
                    # else not required: using int casted last barter qty
                    symbol_overview_patch["lot_size"] = lot_size
                except ReceivedQtyFoundDecimalValError:
                    logging.exception("Found mdSizeMultiplier (lot_size) having some decimal value when subtracting actual "
                                      "value with its int casted value - ignoring lot_size update in "
                                      f"SymbolOverview for symbol: {symbol_overview.symbol}, actual value: {contract_details.minSize}")
            # else not required: not updating if not found

            if contract_details.minTick and not math.isnan(contract_details.minTick):
                symbol_overview_patch["tick_size"] = contract_details.minTick
            # else not required: Avoiding tick_size update

            if symbol_overview_patch:
                symbol_overview_patch["_id"] = symbol_overview.id
                await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_partial_update_symbol_overview_http(symbol_overview_patch)
            # else not required: not found any update in symbol_overview_patch dict - will be logged as exception

        # Subscribe to L1 and L2 data
        md_ticker = self.ib.reqMktData(qualified_contract, '', False, False)
        depth_ticker = self.ib.reqMktDepth(qualified_contract, self.depth_count)

        self.ib_tickers[symbol] = (md_ticker, depth_ticker)
        logging.info(f"Subscribed to market data for {symbol}")


    async def unsubscribe_symbol_for_mobile_book(self, symbol: str):
        if not config_yaml_dict.get("ibkr_connection_enabled", True):
            logging.info("IBKR connection is disabled in config. Skipping unsubscribe.")
            return None

        if not self.ib.isConnected():
            logging.error("IBKR not connected. Cannot unsubscribe from market data.")
            return None

        if symbol not in self.ib_tickers:
            logging.warning(f"Not subscribed to {symbol}. Ignoring request.")
            return None

        l1_ticker, depth_ticker = self.ib_tickers.pop(symbol)
        self.ib.cancelMktData(l1_ticker.contract)
        self.ib.cancelMktDepth(depth_ticker.contract)
        logging.info(f"Unsubscribed from market data for {symbol}")

    async def register_symbol_n_sem(self, symbol_interests_obj: SymbolInterests):
        async with self.symbol_to_sem_n_producer_container_dict_async_lock:
            semaphore = posix_ipc.Semaphore(symbol_interests_obj.semaphore_full_path)
            sem_n_producer_container_obj: SemaphoreNSHMProducerContainer = (
                self.symbol_to_sem_n_producer_container_dict.get(symbol_interests_obj.symbol_name))
            if sem_n_producer_container_obj:
                sem_n_producer_container_obj.semaphore_list.append(semaphore)
            else:
                producer = MobileBookSharedMemoryProducer(symbol_interests_obj.symbol_name)
                self.symbol_to_sem_n_producer_container_dict[symbol_interests_obj.symbol_name] = (
                    SemaphoreNSHMProducerContainer(semaphore_list=[semaphore], shm_producer_obj=producer))

                # creating market depth with default vals to initiate updates on api updates
                await self.create_empty_mobile_book_in_db_for_symbol_n_cache_ids(symbol_interests_obj.symbol_name)

                # registering symbol if new symbol is found
                await self.subscribe_symbol_for_mobile_book(symbol_interests_obj.symbol_name)

    async def create_empty_mobile_book_in_db_for_symbol_n_cache_ids(self, symbol: str):
        async with self.symbol_to_mobile_book_db_id_dict_async_lock:
            market_depth_list: List[MarketDepth] = []
            bid_n_ask_market_depth_id_list_dict = {TickType.BID: [None]*self.depth_count,
                                                   TickType.ASK: [None]*self.depth_count}
            self.symbol_to_mobile_book_db_id_dict[symbol] = bid_n_ask_market_depth_id_list_dict
            empty_tob = TopOfBook.from_kwargs(symbol=symbol)
            self.symbol_to_mobile_book_db_id_dict[symbol]["tob"] = empty_tob.id

            for side in [TickType.BID, TickType.ASK]:
                for depth in range(self.depth_count):
                    market_depth_ = MarketDepth.from_kwargs(symbol=symbol, side=side, position=depth,
                                                            exch_time=DateTime.utcnow(),
                                                            arrival_time=DateTime.utcnow())
                    bid_n_ask_market_depth_id_list_dict[side][depth] = market_depth_.id
                    market_depth_list.append(market_depth_)

        # calling with empty objects
        await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_create_top_of_book_http(empty_tob)
        await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_create_all_market_depth_http(
            market_depth_list)

        # symbol overview is created already at start-up using static data - just shm is not initialized yet
        # setting up shm with stored symbol overview
        symbol_overview_list = await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_get_symbol_overview_from_symbol_query_http(symbol)
        await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_update_symbol_overview_http(symbol_overview_list[0])

    async def create_symbol_interests_pre(self, symbol_interests_obj: SymbolInterests):
        # SymbolInterests.reentrant_lock already acquired here
        try:
            await self.register_symbol_n_sem(symbol_interests_obj)

        except posix_ipc.ExistentialError as e_:
            # shared memory doesn't exist yet
            err_str = (f"Can't find semaphore with name {symbol_interests_obj.semaphore_full_path} "
                       f"for symbol: {symbol_interests_obj.symbol_name};;; error: {e_}")
            logging.error(err_str)
            raise HTTPException(status_code=404, detail=err_str)

    async def create_all_symbol_interests_pre(self, symbol_interests_obj_list: List[SymbolInterests]):
        # SymbolInterests.reentrant_lock already acquired here
        for symbol_interests_obj in symbol_interests_obj_list:
            try:
                await self.register_symbol_n_sem(symbol_interests_obj)

            except posix_ipc.ExistentialError as e_:
                # shared memory doesn't exist yet
                err_str = (f"Can't find semaphore with name {symbol_interests_obj.semaphore_full_path} "
                           f"for symbol: {symbol_interests_obj.symbol_name} - ignoring entry for this symbol;;; "
                           f"error: {e_}")
                logging.error(err_str)
                symbol_interests_obj_list.remove(symbol_interests_obj)

    async def deregister_symbol_n_sem(self, symbol_interests_obj: SymbolInterests):
        async with self.symbol_to_sem_n_producer_container_dict_async_lock:
            sem_n_producer_container_obj: SemaphoreNSHMProducerContainer = (
                self.symbol_to_sem_n_producer_container_dict.get(symbol_interests_obj.symbol_name))
            if sem_n_producer_container_obj:
                for stored_semaphore in sem_n_producer_container_obj.semaphore_list:
                    if symbol_interests_obj.semaphore_full_path == stored_semaphore.name:
                        sem_n_producer_container_obj.semaphore_list.remove(stored_semaphore)

                        if not sem_n_producer_container_obj.semaphore_list:
                            # deregistering symbol
                            await self.unsubscribe_symbol_for_mobile_book(symbol_interests_obj.symbol_name)

                            # removing sem_n_producer_container obj
                            del self.symbol_to_sem_n_producer_container_dict[symbol_interests_obj.symbol_name]
                            break
                else:
                    err_str = (f"Can't find semaphore with name {symbol_interests_obj.semaphore_full_path} "
                               f"for symbol: {symbol_interests_obj.symbol_name} in sem_n_producer_container_obj")
                    logging.error(err_str)
                    raise HTTPException(status_code=404, detail=err_str)
            else:
                err_str = (f"Can't find sem_n_producer_container_obj with name for symbol: "
                           f"{symbol_interests_obj.symbol_name} in cache")
                logging.error(err_str)
                raise HTTPException(status_code=404, detail=err_str)

    async def remove_symbol_interest_by_symbol_query_pre(
            self, symbol_interests_class_type: Type[SymbolInterests], payload: Dict[str, Any]):
        async with SymbolInterests.reentrant_lock:
            symbol = payload.get('symbol')
            symbol_interest = \
                await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_read_symbol_interests_http(
                    get_symbol_interest_from_symbol(symbol))
            await MobileBookServiceRoutesCallbackBaseNativeOverride.underlying_delete_symbol_interests_http(
                symbol_interest[0].id)
            await self.deregister_symbol_n_sem(symbol_interest[0])
            return []