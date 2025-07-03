# SingleSymbolShmVisualizer.py

import ctypes
import mmap
import os
import time
import logging
import argparse
import sys
import gc

import posix_ipc  # type: ignore
import pendulum

# Assuming mobile_book_structures.py is accessible
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_structure import (
    MDSharedMemoryContainer,  # The new top-level structure
    MDContainer, LastBarter, TopOfBook, MarketDepth, Quote,
    SymbolNExchId, MarketBarterVolume, SymbolOverview,
    DEPTH_LVL, TickType
)
from FluxPythonUtils.scripts.pthread_shm_mutex import PThreadShmMutex

# Import print functions from the previous visualizer or redefine them here
# For brevity, let's assume they are available (e.g., copy-pasted or imported from a common util)
# from shm_visualizer_utils import print_md_container, format_timestamp # If you modularize them
# For this example, I'll copy the relevant print functions.

EXPECTED_SHM_SIGNATURE: int = 0xFAFAFAFAFAFAFAFA
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Copied Print Functions (from previous shm_visualizer.py) ---
def format_timestamp(epoch_ns_or_dt):
    if epoch_ns_or_dt is None or (isinstance(epoch_ns_or_dt, (int, float)) and epoch_ns_or_dt == 0): return "N/A"
    if isinstance(epoch_ns_or_dt, pendulum.DateTime): return epoch_ns_or_dt.to_datetime_string()
    try:
        return pendulum.from_timestamp(epoch_ns_or_dt / 1_000_000_000.0).to_datetime_string()
    except Exception:
        return str(epoch_ns_or_dt)


def print_quote(quote: Quote, prefix="  "):
    if quote is None: print(f"{prefix}Quote: None"); return
    print(f"{prefix}Px: {quote.px}")
    print(f"{prefix}Qty: {quote.qty}")
    print(f"{prefix}Premium: {quote.premium}")
    print(f"{prefix}Last Update: {format_timestamp(quote.last_update_date_time)}")


def print_market_barter_volume(mtv: MarketBarterVolume, prefix="  "):
    if mtv is None: print(f"{prefix}MarketBarterVolume: None"); return
    print(f"{prefix}ID: {mtv.id}")
    print(f"{prefix}Participation Sum Qty: {mtv.participation_period_last_barter_qty_sum}")
    print(f"{prefix}Applicable Period (s): {mtv.applicable_period_seconds_}")


def print_last_barter(lt: LastBarter, prefix="  "):
    if lt is None: print(f"{prefix}LastBarter: None"); return
    print(f"{prefix}ID: {lt.id}")
    print(f"{prefix}Symbol: {lt.symbol_n_exch_id.symbol}")
    print(f"{prefix}ExchID: {lt.symbol_n_exch_id.exch_id}")
    print(f"{prefix}Exch Time: {format_timestamp(lt.exch_time)}")
    print(f"{prefix}Arrival Time: {format_timestamp(lt.arrival_time)}")
    print(f"{prefix}Px: {lt.px}")
    print(f"{prefix}Qty: {lt.qty}")
    print(f"{prefix}Premium: {lt.premium}")
    if lt.market_barter_volume:
        print(f"{prefix}Market Barter Volume:"); print_market_barter_volume(lt.market_barter_volume, prefix + "  ")
    else:
        print(f"{prefix}Market Barter Volume: N/A")


def print_top_of_book(tob: TopOfBook, prefix="  "):
    if tob is None: print(f"{prefix}TopOfBook: None"); return
    print(f"{prefix}ID: {tob.id}")
    print(f"{prefix}Symbol: {tob.symbol}")
    print(f"{prefix}Bid Quote:")
    print_quote(tob.bid_quote, prefix + "  ")
    print(f"{prefix}Ask Quote:")
    print_quote(tob.ask_quote, prefix + "  ")
    print(f"{prefix}Last Barter (Quote within TOB):")
    print_quote(tob.last_barter, prefix + "  ")
    print(f"{prefix}Total Bartering Security Size: {tob.total_bartering_security_size}")
    if tob.market_barter_volume:
        print(f"{prefix}Market Barter Volume:"); print_market_barter_volume(tob.market_barter_volume, prefix + "  ")
    else:
        print(f"{prefix}Market Barter Volume: N/A")
    print(f"{prefix}Last Update: {format_timestamp(tob.last_update_date_time)}")


def print_symbol_overview(so: SymbolOverview, prefix="  "):
    if so is None: print(f"{prefix}SymbolOverview: None"); return
    print(f"{prefix}ID: {so.id}")
    print(f"{prefix}Symbol: {so.symbol}")
    print(f"{prefix}Company: {so.company}")
    print(f"{prefix}Status: {so.status}")
    print(f"{prefix}Lot Size: {so.lot_size}")
    print(f"{prefix}Limit Up Px: {so.limit_up_px}")
    print(f"{prefix}Limit Dn Px: {so.limit_dn_px}")
    print(f"{prefix}Conv Px: {so.conv_px}")
    print(f"{prefix}Closing Px: {so.closing_px}")
    print(f"{prefix}Open Px: {so.open_px}")
    print(f"{prefix}High: {so.high}")
    print(f"{prefix}Low: {so.low}")
    print(f"{prefix}Volume: {so.volume}")
    print(f"{prefix}Tick Size: {so.tick_size}")
    print(f"{prefix}Force Publish: {so.force_publish}")
    print(f"{prefix}Last Update: {format_timestamp(so.last_update_date_time)}")


def print_market_depth_entry(md: MarketDepth, prefix="  "):
    if md is None or md.position == -1: return
    print(f"{prefix}Symbol: {md.symbol}")
    print(f"{prefix}Side: {md.side}")
    print(f"{prefix}Px: {md.px}")
    print(f"{prefix}Qty: {md.qty}")
    print(f"{prefix}Position: {md.position}")
    print(f"{prefix}Exch Time: {format_timestamp(md.exch_time)}")
    print(f"{prefix}Arrival Time: {format_timestamp(md.arrival_time)}")
    print(f"{prefix}Market Maker: {md.market_maker}")
    print(f"{prefix}Is Smart Depth: {md.is_smart_depth}")
    print(f"{prefix}Cum Notional: {md.cumulative_notional}")
    print(f"{prefix}Cum Qty: {md.cumulative_qty}")
    print(f"{prefix}Cum Avg Px: {md.cumulative_avg_px}")


def print_single_md_shm_contents(shm_root: MDSharedMemoryContainer):  # Updated to take MDSharedMemoryContainer
    if shm_root is None: print("Shared Memory Root: None"); return

    print(f"--- Shared Memory Snapshot (Symbol: {shm_root.mobile_book_container.symbol}) ---")
    print(f"SHM Update Signature: {hex(shm_root.shm_update_signature)}")

    md_container = shm_root.mobile_book_container
    print(f"  Update Counter: {md_container.update_counter}")

    print(f"  Last Barter Details:")
    print_last_barter(md_container.last_barter, "    ")

    print(f"  Top Of Book Details:")
    print_top_of_book(md_container.top_of_book, "    ")

    if md_container.is_symbol_overview_set:
        print(f"  Symbol Overview Details:")
        print_symbol_overview(md_container.symbol_overview, "    ")
    else:
        print(f"  Symbol Overview Details: Not Set")

    print(f"  Bid Market Depth (Top {DEPTH_LVL}):")
    for i in range(DEPTH_LVL):
        entry = md_container.bid_market_depth_list[i]
        if entry.position != -1: print(f"    Level {i} (Pos: {entry.position}):"); print_market_depth_entry(entry,
                                                                                                            "      ")

    print(f"  Ask Market Depth (Top {DEPTH_LVL}):")
    for i in range(DEPTH_LVL):
        entry = md_container.ask_market_depth_list[i]
        if entry.position != -1: print(f"    Level {i} (Pos: {entry.position}):"); print_market_depth_entry(entry,
                                                                                                            "      ")
    print(f"--- End Snapshot ---\n")


# --- End Copied Print Functions ---

def visualize_single_shm(shm_name: str):
    logging.debug(f"Attempting to visualize MDSharedMemoryContainer: {shm_name}")
    mmap_obj, shm = None, None
    copied_shm_root = None  # This will be the from_buffer_copy() object

    try:
        shm = posix_ipc.SharedMemory(shm_name, flags=posix_ipc.O_RDONLY)
        logging.debug(f"Opened SHM {shm_name}. Size: {shm.size}")
        if shm.size < ctypes.sizeof(MDSharedMemoryContainer):
            logging.error(f"SHM size ({shm.size}) < expected ({ctypes.sizeof(MDSharedMemoryContainer)}). Exiting.")
            return

        mmap_obj = mmap.mmap(shm.fd, shm.size, prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
        logging.debug(f"Mapped SHM {shm_name} with PROT_READ.")

        # Make a copy immediately for safe reading
        copied_shm_root = MDSharedMemoryContainer.from_buffer_copy(mmap_obj)
        logging.debug("Created copy of SHM data.")

        if copied_shm_root.shm_update_signature != EXPECTED_SHM_SIGNATURE:
            logging.warning(
                f"SHM sig mismatch! Expected {hex(EXPECTED_SHM_SIGNATURE)}, found {hex(copied_shm_root.shm_update_signature)}.")

        # Mutex operations would ideally still work on the "idea" of the mutex in SHM
        # PThreadShmMutex will use the address derived from the structure.
        mutex_wrapper = PThreadShmMutex(copied_shm_root.mutex)
        locked = False
        try:
            if mutex_wrapper.trylock() == 0:  # Attempt to lock to ensure a consistent read moment for the copy
                locked = True
                logging.debug("Mutex acquired for snapshot moment.")
                # If we wanted the absolute latest after lock, re-copy:
                # copied_shm_root = MDSharedMemoryContainer.from_buffer_copy(mmap_obj)
            else:
                logging.warning(
                    "Failed to acquire mutex (trylock). Displaying potentially inconsistent data (copy made before trylock).")
        except Exception as e:
            logging.error(f"Error during mutex trylock: {e}", exc_info=True)
        finally:
            if locked: mutex_wrapper.unlock(); logging.debug("Mutex released.")

        print_single_md_shm_contents(copied_shm_root)

    except posix_ipc.ExistentialError as ee:
        logging.error(f"ExistentialError: {ee}. SHM or SEM likely does not exist.")
    except Exception as e:
        logging.error(f"An error occurred in visualize_single_shm: {e}", exc_info=True)
    finally:
        if mmap_obj:
            try:
                mmap_obj.close()
            except Exception as e:
                logging.debug(f"Error closing mmap: {e}")
        if shm and hasattr(shm, 'fd') and shm.fd != -1:
            try:
                shm.close_fd()
            except Exception as e:
                logging.debug(f"Error closing shm fd: {e}")
        logging.debug("visualize_single_shm cleanup finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Single Symbol Mobile Book Shared Memory.")
    # parser.add_argument("--shm_name", type=str, required=True,
    #                     help="Name of the shared memory segment (e.g., md_shm_spy).")
    # parser.add_argument("--sem_name", type=str, required=True,
    #                     help="Name of the semaphore (e.g., md_sem_spy).")
    # parser.add_argument("--loop", action="store_true", help="Continuously refresh.")
    # parser.add_argument("--interval", type=int, default=2, help="Refresh interval (s).")
    # parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)

    # shm_name_ipc = args.shm_name if args.shm_name.startswith('/') else f"/{args.shm_name}"
    # sem_name_ipc = args.sem_name if args.sem_name.startswith('/') else f"/{args.sem_name}"

    shm_name_ipc = f"Type1_Sec_2"
    # sem_name_ipc = f"md_sem_spy"

    # if args.loop:
    if True:
        try:
            while True:
                if sys.platform != 'win32':
                    os.system('clear')
                else:
                    os.system('cls')
                visualize_single_shm(shm_name_ipc)
                # logging.info(f"Refreshing in {args.interval}s... (Ctrl+C to stop)")
                # time.sleep(args.interval)
                time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Loop stopped.")
        except Exception as e:
            logging.error(f"Loop error: {e}", exc_info=True)
    else:
        visualize_single_shm(shm_name_ipc)