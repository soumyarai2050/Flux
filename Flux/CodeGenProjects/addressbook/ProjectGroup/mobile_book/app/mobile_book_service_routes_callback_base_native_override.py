# standard imports
import asyncio
import os
import logging
from threading import Thread
import time
import datetime
from typing import Dict, Any, List, Callable, Tuple
import posix_ipc

# 3rd party imports
from fastapi import HTTPException

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_routes_callback_imports import MobileBookServiceRoutesCallback
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_service_helper import (
    md_port, config_yaml_dict, config_yaml_path, is_service_up, is_view_service_up)
from FluxPythonUtils.scripts.general_utility_functions import except_n_log_alert, parse_to_int
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_shared_memory_producer import MobileBookSharedMemoryProducer
from ProjectGroup.mobile_book.app.mobile_book_service_helper import md_view_port
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.aggregate import get_symbol_interest_from_symbol
from ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_msgspec_routes import \
    underlying_remove_symbol_interest_by_symbol_query_http


class SemaphoreNSHMProducerContainer:
    def __init__(self, semaphore_list, shm_producer_obj):
        self.semaphore_list = semaphore_list
        self.shm_producer_obj = shm_producer_obj

class MobileBookServiceRoutesCallbackBaseNativeOverride(MobileBookServiceRoutesCallback):
    underlying_read_symbol_interests_by_id_http: Callable[..., Any] | None = None
    underlying_read_symbol_interests_http: Callable[..., Any] | None = None
    underlying_delete_symbol_interests_http: Callable[..., Any] | None = None
    underlying_remove_symbol_interest_by_symbol_query_http: Callable[..., Any] | None = None


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

        self.symbol_to_sem_n_producer_container_dict: Dict[str, SemaphoreNSHMProducerContainer] = {}

    @classmethod
    def initialize_underlying_http_callables(cls):
        from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.FastApi.mobile_book_service_http_msgspec_routes import (
            underlying_read_symbol_interests_by_id_http, underlying_read_symbol_interests_http,
            underlying_delete_symbol_interests_http)
        cls.underlying_read_symbol_interests_by_id_http = underlying_read_symbol_interests_by_id_http
        cls.underlying_read_symbol_interests_http = underlying_read_symbol_interests_http
        cls.underlying_delete_symbol_interests_http = underlying_delete_symbol_interests_http
        cls.underlying_remove_symbol_interest_by_symbol_query_http = underlying_remove_symbol_interest_by_symbol_query_http

    def app_launch_pre(self):
        MobileBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = md_port
        app_launch_pre_thread = Thread(target=self._app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def view_app_launch_pre(self):
        MobileBookServiceRoutesCallbackBaseNativeOverride.initialize_underlying_http_callables()
        logging.debug("Triggered server launch pre override")
        self.port = md_view_port
        app_launch_pre_thread = Thread(target=self._view_app_launch_pre_thread_func, daemon=True)
        app_launch_pre_thread.start()

    def app_launch_post(self):
        logging.debug("Triggered server launch post override")

        # closing all cached shared memory producers
        for symbol, sem_n_shm_producer_container_obj in self.symbol_to_sem_n_producer_container_dict.items():
            for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
                try:
                    semaphore.close()
                    logging.debug(f"SEM for {symbol} closed.")
                except Exception as e:
                    logging.error(f"Error closing SEM for {symbol}: {e}", exc_info=True)
            sem_n_shm_producer_container_obj.shm_producer_obj.close()

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
        service_up_no_error_retry_count = 3  # minimum retries that shouldn't raise error on UI dashboard
        should_sleep: bool = False
        recovered_cache = False
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

                    if not recovered_cache:
                        self.recover_cache()
                        recovered_cache = True
            else:
                should_sleep = True

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

    def get_sem_n_shm_producer_cont_obj(
            self, symbol: str) -> SemaphoreNSHMProducerContainer:
        # note: acquire SymbolInterests.reentrant_lock before calling this func
        sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = (
            self.symbol_to_sem_n_producer_container_dict.get(symbol))
        if sem_n_shm_producer_container_obj is not None:
            return sem_n_shm_producer_container_obj
        else:
            raise HTTPException(
                status_code=400, detail=f"Can't find sem_n_shm_producer_container_obj for symbol: {symbol}")

    async def _create_last_barter(self, last_barter_obj: LastBarter):
        async with SymbolInterests.reentrant_lock:
            sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
                self.get_sem_n_shm_producer_cont_obj(last_barter_obj.symbol_n_exch_id.symbol)
            shm_producer = sem_n_shm_producer_container_obj.shm_producer_obj
            shm_producer.update_last_barter_from_msgspec_obj(last_barter_obj)

            for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
                semaphore.release()

    async def create_last_barter_post(self, last_barter_obj: LastBarter):
        await self._create_last_barter(last_barter_obj)

    async def create_all_last_barter_post(self, last_barter_obj_list: List[LastBarter]):
        async with SymbolInterests.reentrant_lock:
            for last_barter_obj in last_barter_obj_list:
                await self._create_last_barter(last_barter_obj)

    async def _create_update_market_depth(self, market_depth_obj: MarketDepth):
        async with SymbolInterests.reentrant_lock:
            sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
                self.get_sem_n_shm_producer_cont_obj(market_depth_obj.symbol)
            shm_producer = sem_n_shm_producer_container_obj.shm_producer_obj
            shm_producer.update_market_depth_from_msgspec_obj(market_depth_obj)

            for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
                semaphore.release()

    async def create_market_depth_post(self, market_depth_obj: MarketDepth):
        await self._create_update_market_depth(market_depth_obj)

    async def create_all_market_depth_post(self, market_depth_obj_list: List[MarketDepth]):
        async with SymbolInterests.reentrant_lock:
            for market_depth_obj in market_depth_obj_list:
                await self._create_update_market_depth(market_depth_obj)

    async def update_market_depth_post(self, updated_market_depth_obj: MarketDepth):
        await self._create_update_market_depth(updated_market_depth_obj)

    async def update_all_market_depth_post(self, updated_market_depth_obj_list: List[MarketDepth]):
        async with SymbolInterests.reentrant_lock:
            for market_depth_obj in updated_market_depth_obj_list:
                await self._create_update_market_depth(market_depth_obj)

    async def partial_update_market_depth_post(self, updated_market_depth_obj_json: Dict[str, Any]):
        await self._create_update_market_depth(MarketDepth.from_dict(updated_market_depth_obj_json))

    async def partial_update_all_market_depth_post(self, updated_market_depth_dict_list: List[Dict[str, Any]]):
        async with SymbolInterests.reentrant_lock:
            for market_depth_obj_dict in updated_market_depth_dict_list:
                await self._create_update_market_depth(MarketDepth.from_dict(market_depth_obj_dict))

    async def _create_update_symbol_overview(self, symbol_overview_obj: SymbolOverview):
        async with SymbolInterests.reentrant_lock:
            sem_n_shm_producer_container_obj: SemaphoreNSHMProducerContainer = \
                self.get_sem_n_shm_producer_cont_obj(symbol_overview_obj.symbol)
            shm_producer = sem_n_shm_producer_container_obj.shm_producer_obj
            shm_producer.update_symbol_overview_from_msgspec_obj(symbol_overview_obj)

            for semaphore in sem_n_shm_producer_container_obj.semaphore_list:
                semaphore.release()

    async def create_symbol_overview_post(self, symbol_overview_obj: SymbolOverview):
        await self._create_update_symbol_overview(symbol_overview_obj)

    async def create_all_symbol_overview_post(self, symbol_overview_obj_list: List[SymbolOverview]):
        async with SymbolInterests.reentrant_lock:
            for symbol_overview_obj in symbol_overview_obj_list:
                await self._create_update_symbol_overview(symbol_overview_obj)

    async def update_symbol_overview_post(self, updated_symbol_overview_obj: SymbolOverview):
        await self._create_update_symbol_overview(updated_symbol_overview_obj)

    async def update_all_symbol_overview_post(self, updated_symbol_overview_obj_list: List[SymbolOverview]):
        async with SymbolInterests.reentrant_lock:
            for symbol_overview_obj in updated_symbol_overview_obj_list:
                await self._create_update_symbol_overview(symbol_overview_obj)

    async def partial_update_symbol_overview_post(self, updated_symbol_overview_obj_json: Dict[str, Any]):
        await self._create_update_symbol_overview(SymbolOverview.from_dict(updated_symbol_overview_obj_json))

    async def partial_update_all_symbol_overview_post(self, updated_symbol_overview_dict_list: List[Dict[str, Any]]):
        async with SymbolInterests.reentrant_lock:
            for symbol_overview_obj_dict in updated_symbol_overview_dict_list:
                await self._create_update_symbol_overview(SymbolOverview.from_dict(symbol_overview_obj_dict))

    async def subscribe_symbol_for_mobile_book(self, symbol: str):
        pass

    async def unsubscribe_symbol_for_mobile_book(self, symbol: str):
        pass

    async def register_symbol_n_sem(self, symbol_interests_obj: SymbolInterests):
        # note: acquire SymbolInterests.reentrant_lock before calling this func
        semaphore = posix_ipc.Semaphore(symbol_interests_obj.semaphore_full_path)
        sem_n_producer_container_obj: SemaphoreNSHMProducerContainer = (
            self.symbol_to_sem_n_producer_container_dict.get(symbol_interests_obj.symbol_name))
        if sem_n_producer_container_obj:
            sem_n_producer_container_obj.semaphore_list.append(semaphore)
        else:
            producer = MobileBookSharedMemoryProducer(symbol_interests_obj.symbol_name)
            self.symbol_to_sem_n_producer_container_dict[symbol_interests_obj.symbol_name] = (
                SemaphoreNSHMProducerContainer(semaphore_list=[semaphore], shm_producer_obj=producer))

            # registering symbol if new symbol is found
            await self.subscribe_symbol_for_mobile_book(symbol_interests_obj.symbol_name)

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
        # note: acquire SymbolInterests.reentrant_lock before calling this func

        semaphore = posix_ipc.Semaphore(symbol_interests_obj.semaphore_full_path)
        sem_n_producer_container_obj: SemaphoreNSHMProducerContainer = (
            self.symbol_to_sem_n_producer_container_dict.get(symbol_interests_obj.symbol_name))
        if sem_n_producer_container_obj:
            if semaphore in sem_n_producer_container_obj.semaphore_list:
                sem_n_producer_container_obj.semaphore_list.remove(semaphore)

                if not sem_n_producer_container_obj.semaphore_list:
                    # deregistering symbol
                    await self.unsubscribe_symbol_for_mobile_book(symbol_interests_obj.symbol_name)

                    # removing sem_n_producer_container obj
                    del self.symbol_to_sem_n_producer_container_dict[symbol_interests_obj.symbol_name]
        else:
            err_str = (f"Can't find semaphore with name {symbol_interests_obj.semaphore_full_path} "
                       f"for symbol: {symbol_interests_obj.symbol_name} in cache")
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
                symbol_interest.id)
            await self.deregister_symbol_n_sem(symbol_interest)
