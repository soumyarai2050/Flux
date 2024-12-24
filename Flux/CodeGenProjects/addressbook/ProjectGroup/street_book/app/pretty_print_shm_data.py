# standard imports
import logging
from datetime import datetime
import os
os.environ['ModelType'] = 'msgspec'

# 3rd party imports
from pathlib import PurePath

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.mobile_book_structures import *
from FluxPythonUtils.scripts.utility_functions import configure_logger

total_char_count_per_pretty_int = 10
total_char_count_per_pretty_datetime = 35
total_char_count_per_pretty_str = 12


def pretty_print_str_with_space_suffix(data_str, total_char_count: int):
    data_str = str(data_str)
    total_char_count -= len(data_str)
    return data_str + " "*total_char_count


def pretty_print_str_with_space_prefix(data_str, total_char_count: int):
    data_str = str(data_str)
    total_char_count -= len(data_str)
    return " "*total_char_count + data_str


def _pretty_print_last_barter(lt: LastBarter):
    print("*" * 25, f" Last Barter ", "*" * 25)
    print(pretty_print_str_with_space_suffix("SYMBOL", total_char_count_per_pretty_str),
          pretty_print_str_with_space_suffix("EXCH ID", total_char_count_per_pretty_str),
          pretty_print_str_with_space_suffix("PRICE", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("PREMIUM", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("EXCH TS", total_char_count_per_pretty_datetime),
          pretty_print_str_with_space_suffix("ARR TS", total_char_count_per_pretty_datetime))
    print(pretty_print_str_with_space_suffix(lt.symbol_n_exch_id.symbol, total_char_count_per_pretty_str),
          pretty_print_str_with_space_suffix(lt.symbol_n_exch_id.exch_id, total_char_count_per_pretty_str),
          pretty_print_str_with_space_suffix(lt.px, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(lt.qty, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(lt.premium, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(lt.exch_time, total_char_count_per_pretty_datetime),
          pretty_print_str_with_space_suffix(lt.arrival_time, total_char_count_per_pretty_datetime), "\n")


def _pretty_print_tob(tob: TopOfBook):
    print("*" * 25, f" Top Of Book ", "*" * 25)
    print(pretty_print_str_with_space_suffix("BID QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("BID PRICE", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("ASK QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("ASK PRICE", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("LAST QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("LAST PRICE", total_char_count_per_pretty_int))
    print(pretty_print_str_with_space_suffix(tob.bid_quote.px, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(tob.bid_quote.qty, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(tob.ask_quote.px, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(tob.ask_quote.qty, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(tob.last_barter.px, total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix(tob.last_barter.qty, total_char_count_per_pretty_int), "\n")


def _pretty_print_market_depth(bid_md_list: List[MarketDepth], ask_md_list: List[MarketDepth]):
    print("*" * 25, f" Market Depth ", "*" * 25)
    print(pretty_print_str_with_space_suffix("BID QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("BID PRICE", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("ASK QTY", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("ASK PRICE", total_char_count_per_pretty_int),
          pretty_print_str_with_space_suffix("POSITION", total_char_count_per_pretty_int))
    for bid_md, last_md in zip(bid_md_list, ask_md_list):
        print(pretty_print_str_with_space_suffix(bid_md.qty, total_char_count_per_pretty_int),
              pretty_print_str_with_space_suffix(bid_md.px, total_char_count_per_pretty_int),
              pretty_print_str_with_space_suffix(last_md.qty, total_char_count_per_pretty_int),
              pretty_print_str_with_space_suffix(last_md.px, total_char_count_per_pretty_int),
              pretty_print_str_with_space_suffix(bid_md.position, total_char_count_per_pretty_int))


def pretty_print_shm_data(base_md_shared_memory_container_: BaseMDSharedMemoryContainer):

    for md_shared_memory in [base_md_shared_memory_container_.leg_1_md_shared_memory,
                             base_md_shared_memory_container_.leg_2_md_shared_memory]:
        print("*"*25, f" {md_shared_memory.symbol} ", "*"*25)
        print(f"UPDATE COUNTER: {md_shared_memory.update_counter}\n")
        lt = md_shared_memory.last_barter
        _pretty_print_last_barter(lt)
        tob = md_shared_memory.top_of_book
        _pretty_print_tob(tob)
        bid_md_list = md_shared_memory.bid_market_depth_list
        ask_md_list = md_shared_memory.ask_market_depth_list
        _pretty_print_market_depth(bid_md_list, ask_md_list)
        print("\n")


if __name__ == '__main__':
    from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.symbol_cache import *

    log_dir: PurePath = PurePath(__file__).parent.parent / "log"
    datetime_str: str = datetime.datetime.now().strftime("%Y%m%d")
    configure_logger('debug', str(log_dir), f'pretty_print_shm_data_log_{datetime_str}.log')

    # change below values based on requirement
    md_shared_memory_name = f"/dev/shm/street_book_1_shm"
    shared_memory_semaphore_name = f"/street_book_1_sem"

    # setting shm and semaphore instances
    shared_memory_found = SymbolCacheContainer.check_if_shared_memory_exists(md_shared_memory_name,
                                                                             shared_memory_semaphore_name)
    if not shared_memory_found:
        err_str = (f"Exception: Can't find shared memory or posix semaphore with names {md_shared_memory_name} and "
                   f"{shared_memory_semaphore_name} - exiting with code 1")
        logging.error(err_str)
        exit(1)

    base_md_shared_memory_container = SymbolCacheContainer.get_base_md_shared_memory_container()
    pretty_print_shm_data(base_md_shared_memory_container)
