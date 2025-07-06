# standard imports
import logging
import time
import threading
from typing import Dict, Any, List, ClassVar, Tuple, Final
import os
import ctypes
import mmap

# 3rd party imports
import posix_ipc
from pendulum import DateTime, parse

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.pos_cache import PosCache
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.pretty_print_md_shm_data import pretty_print_shm_data
from FluxPythonUtils.scripts.pthread_shm_mutex import PThreadShmMutex
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_structure import *


class SymbolCache:
    def __init__(self):
        self.top_of_book: TopOfBook | None = None
        self.last_barter: LastBarter | None = None
        self.bid_market_depth: List[MarketDepth] | None = None
        self.ask_market_depth: List[MarketDepth] | None = None
        self.so: SymbolOverview | None = None
        self.buy_pos_cache: PosCache | None = None
        self.sell_pos_cache: PosCache | None = None

    def __str__(self):
        return (f"MobileBookContainer({str(self.top_of_book)}, {str(self.bid_market_depth)}, "
                f"{str(self.ask_market_depth)}, {str(self.last_barter)})")

    def get_top_of_book_bid_quote(self) -> Quote | None:
        return self.top_of_book.bid_quote

    def get_top_of_book_ask_quote(self) -> Quote | None:
        return self.top_of_book.ask_quote

    def get_top_of_book_last_barter(self) -> Quote | None:
        return self.top_of_book.last_barter

    def get_top_of_book(self, date_time: DateTime | None = None) -> TopOfBook | None:
        if date_time is None or date_time < self.top_of_book.last_update_date_time:
            return self.top_of_book
        return None

    def get_last_barter(self) -> LastBarter | None:
        return self.last_barter

    def remove_bid_market_depth_from_position(self, position: int) -> bool:
        self.bid_market_depth[position] = None
        return True

    def remove_ask_market_depth_from_position(self, position: int) -> bool:
        self.ask_market_depth[position] = None
        return True

    def get_bid_market_depths(self) -> List[MarketDepth]:
        return self.bid_market_depth

    def get_ask_market_depths(self) -> List[MarketDepth]:
        return self.ask_market_depth

    def get_bid_market_depth_from_depth(self, position: int) -> MarketDepth | None:
        if position > 0 or position < 9:
            return self.bid_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_ask_market_depth_from_depth(self, position: int) -> MarketDepth | None:
        if position > 0 or position < 9:
            return self.ask_market_depth[position]
        else:
            logging.error(f"Unsupported depth: {position} - must be between 0-9")
            return None

    def get_so(self, symbol: str | None = None):  # so getter need to get breach_px
        return self.so


class SymbolCacheContainer:
    # below None data-members must be initialized at init time of executor process
    shared_memory: Dict[str, mmap.mmap] = {}
    # shared_memory_semaphore = None
    EXPECTED_SHM_SIGNATURE: Final[hex] = 0xFAFAFAFAFAFAFAFA    # hard-coded: cpp puts same value
    shm_signature_mismatch_counts:  int = 0
    symbol_to_symbol_cache_dict: Dict[str, SymbolCache] = {}
    # semaphore = threading.Semaphore(0)
    print_shm_snapshot: bool | None = executor_config_yaml_dict.get('print_shm_snapshot')

    # @staticmethod
    # def release_semaphore():
    #     if SymbolCacheContainer.shared_memory_semaphore is not None:
    #         SymbolCacheContainer.shared_memory_semaphore.release()
    #     else:
    #         SymbolCacheContainer.semaphore.release()
    #
    # @staticmethod
    # def acquire_semaphore():
    #     if SymbolCacheContainer.shared_memory_semaphore is not None:
    #         SymbolCacheContainer.shared_memory_semaphore.acquire()
    #     else:
    #         SymbolCacheContainer.semaphore.acquire()

    @staticmethod
    def check_if_shared_memory_exists(md_shared_memory_name: str) -> bool:
        shared_memory_found = False
        try:
            shm_fd = os.open(f"/dev/shm/{md_shared_memory_name}", os.O_RDWR)
            size = ctypes.sizeof(MDSharedMemoryContainer)
            shm = mmap.mmap(shm_fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
            SymbolCacheContainer.shared_memory[md_shared_memory_name] = shm
            SymbolCacheContainer.add_symbol_cache_for_symbol(md_shared_memory_name)
        except FileNotFoundError as exp:
            # shared memory doesn't exist yet, will retry in next loop
            logging.warning(f"Something went wrong with setting up md shared memory: {exp}")

        if SymbolCacheContainer.shared_memory is not None:
            shared_memory_found = True
        # else will retry again in next loop run
        return shared_memory_found

    @staticmethod
    def get_shm_mutex(md_shared_memory_name: str) -> PThreadShmMutex | None:
        shm = SymbolCacheContainer.shared_memory.get(md_shared_memory_name)
        md_shared_memory_container: MDSharedMemoryContainer = MDSharedMemoryContainer.from_buffer(shm)
        sleep_sec = 1
        if md_shared_memory_container.shm_update_signature != SymbolCacheContainer.EXPECTED_SHM_SIGNATURE:
            # @@@ below error log is used in specific test case for string matching - if changed here
            # needs to be changed in test also
            SymbolCacheContainer.shm_signature_mismatch_counts += 1

            time.sleep(1)
            log_str = ("Couldn't find matching shm signature, ignoring this internal run cycle - sleeping for "
                       f"{sleep_sec}(s) and retrying on next semaphore release, "
                       f"{SymbolCacheContainer.EXPECTED_SHM_SIGNATURE=}, "
                       f"found {md_shared_memory_container.shm_update_signature}")
            # logging is done based on num of mismatch counts - 1 time it happens in all cpp app start up since
            # cpp sets empty shm without setting signature and then releases semaphore. Apart from it cpp app will
            # also release semaphore when signature is not set 5 times when cpp app is recovered from crash to
            # notify python so that it can get ready to use new shm. More than 1 + 5 = 6 times is not expected so
            # kept in error state
            if SymbolCacheContainer.shm_signature_mismatch_counts <= 4:
                logging.info(log_str)
            elif SymbolCacheContainer.shm_signature_mismatch_counts <= 6:
                logging.warning(log_str)
            else:
                logging.error(log_str)
            return None
        # else not required: all good

        pthread_shm_mutex: PThreadShmMutex = PThreadShmMutex(md_shared_memory_container.mutex)
        return pthread_shm_mutex

    @staticmethod
    def get_md_container(md_shared_memory_name: str) -> MDContainer | None:
        pthread_shm_mutex: PThreadShmMutex = SymbolCacheContainer.get_shm_mutex(md_shared_memory_name)
        if pthread_shm_mutex is not None:
            while True:
                lock_try_time = DateTime.utcnow()
                lock_res = pthread_shm_mutex.try_timedlock()
                if lock_res == 0:
                    try:
                        shm = SymbolCacheContainer.shared_memory.get(md_shared_memory_name)
                        md_shared_memory_container_: MDSharedMemoryContainer = (
                            MDSharedMemoryContainer.from_buffer_copy(shm))
                        mobile_book_container_ = md_shared_memory_container_.mobile_book_container
                        break
                    except Exception as e:
                        logging.exception(f"get_base_md_shared_memory_container failed: exception {e}")
                        return None
                    finally:
                        pthread_shm_mutex.unlock()
                else:
                    lock_timed_out_time = DateTime.utcnow()
                    logging.error(f"pthread lock tried to take lock at {lock_try_time}, but timed-out at "
                                  f"{lock_timed_out_time}, taking total "
                                  f"{(lock_timed_out_time - lock_try_time).total_seconds()} sec(s), {lock_res=}")
            return mobile_book_container_
        else:
            return None

    @staticmethod
    def update_md_cache_from_shared_memory(md_shared_memory_name: str) -> bool:
        mobile_book_container_ = SymbolCacheContainer.get_md_container(md_shared_memory_name)

        if mobile_book_container_ is not None:
            if SymbolCacheContainer.print_shm_snapshot:
                pretty_print_shm_data(mobile_book_container_)

            # setting leg1 md data
            symbol1 = mobile_book_container_.symbol  # Uses the property that decodes
            symbol_cache = SymbolCacheContainer.symbol_to_symbol_cache_dict.get(symbol1)
            if symbol_cache:  # Check if symbol_cache exists
                symbol_cache.top_of_book = mobile_book_container_.top_of_book
                symbol_cache.last_barter = mobile_book_container_.last_barter
                symbol_cache.bid_market_depth = [md for md in mobile_book_container_.bid_market_depth_list if
                                                 md.position != -1]
                symbol_cache.ask_market_depth = [md for md in mobile_book_container_.ask_market_depth_list if
                                                 md.position != -1]
                if mobile_book_container_.is_symbol_overview_set:  # CHECK THE FLAG
                    symbol_cache.so = mobile_book_container_.symbol_overview
                else:
                    symbol_cache.so = None  # Explicitly set to None if not set in SHM
            else:
                logging.warning(f"No SymbolCache found for leg 1 symbol: {symbol1} during SHM update.")
            return True
        else:
            return False


    @classmethod
    def get_symbol_cache(cls, symbol: str) -> SymbolCache | None:
        symbol_cache = cls.symbol_to_symbol_cache_dict.get(symbol)
        return symbol_cache

    @classmethod
    def add_symbol_cache_for_symbol(cls, symbol: str) -> SymbolCache:
        symbol_cache = cls.symbol_to_symbol_cache_dict.get(symbol)
        if symbol_cache is None:
            symbol_cache = SymbolCache()
            cls.symbol_to_symbol_cache_dict[symbol] = symbol_cache
            logging.debug(f'Added Container Obj for symbol: {symbol}')
            return symbol_cache
        else:
            logging.warning(f"SymbolCache for {symbol=} already exists - passing existing object to caller of "
                            "add_symbol_cache_for_symbol")
            return symbol_cache
