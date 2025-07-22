# MobileBookSharedMemoryProducer.py

import ctypes
import mmap
import os
import time
import logging
from typing import Dict, Optional, Any

import posix_ipc  # type: ignore
import pendulum

# Assuming mobile_book_structures.py is accessible
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.app.mobile_book_structure import (
    MDSharedMemoryContainer,
    MDContainer,
    LastBarter,
    TopOfBook,
    MarketDepth,
    Quote,
    SymbolNExchId,
    MarketBarterVolume,
    SymbolOverview,
    MAX_STRING_LENGTH,
    DEPTH_LVL,
    TickType,
    Structure  # Base Structure
)
from FluxPythonUtils.scripts.pthread_shm_mutex import PThreadShmMutex, pthread_mutex_t
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_ts_utils import (
    get_epoch_from_pendulum_dt, get_pendulum_dt_from_epoch)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.mobile_book.generated.ORMModel.mobile_book_service_msgspec_model import (
    LastBarter as LastBarterMsgspec, LastBarterBaseModel as LastBarterMsgspecBaseModel,
    TopOfBook as TopOfBookMsgspec, TopOfBookBaseModel as TopOfBookMsgspecBaseModel,
    MarketDepth as MarketDepthMsgspec, MarketDepthBaseModel as MarketDepthMsgspecBaseModel,
    SymbolOverview as SymbolOverviewMsgspec, SymbolOverviewBaseModel as SymbolOverviewMsgspecBaseModel,
    Quote as QuoteMsgspec, MarketBarterVolume as MarketBarterVolumeMsgspec)

EXPECTED_SHM_SIGNATURE: int = 0xFAFAFAFAFAFAFAFA
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MobileBookSharedMemoryProducer:
    def __init__(self, symbol: str):
        self.shm_name = f"/{symbol}"  # posix_ipc names usually start with /
        # self.sem_name = f"/{sem_name}"
        self.instrument_symbol = symbol  # The single symbol this producer manages

        self.shm: Optional[posix_ipc.SharedMemory] = None
        self.mmap_obj: Optional[mmap.mmap] = None
        self.shm_root_ptr: Optional[MDSharedMemoryContainer] = None  # Points to the new top-level struct
        self._mobile_book_struct: Optional[MDContainer] = None  # Direct ref to the MDContainer inside MDSharedMemoryContainer

        self.mutex_wrapper: Optional[PThreadShmMutex] = None
        # self.semaphore: Optional[posix_ipc.Semaphore] = None
        self._now_ns = lambda: get_epoch_from_pendulum_dt(pendulum.DateTime.utcnow())

        try:
            self.shm = posix_ipc.SharedMemory(self.shm_name, flags=posix_ipc.O_CREAT | posix_ipc.O_RDWR,
                                              size=ctypes.sizeof(MDSharedMemoryContainer))  # Size of the new top struct
            logging.debug(f"Shared memory {self.shm_name} created or opened for symbol {self.instrument_symbol}.")

            self.mmap_obj = mmap.mmap(self.shm.fd, self.shm.size,
                                      flags=mmap.MAP_SHARED,
                                      prot=mmap.PROT_READ | mmap.PROT_WRITE)

            self.shm_root_ptr = MDSharedMemoryContainer.from_buffer(self.mmap_obj)

            # Cache direct reference to the nested MDContainer
            if self.shm_root_ptr:
                self._mobile_book_struct = self.shm_root_ptr.mobile_book_container

            self.mutex_wrapper = PThreadShmMutex(self.shm_root_ptr.mutex)  # Mutex is now at the root

            # Initialize symbols within the nested MDContainer
            if self._mobile_book_struct:
                self._populate_string(self._mobile_book_struct, "symbol_", self.instrument_symbol)
                self._mobile_book_struct.update_counter = 0
                # Also set the symbol in TopOfBook and SymbolOverview if they exist
                self._populate_string(self._mobile_book_struct.top_of_book, "symbol_", self.instrument_symbol)
                self._populate_string(self._mobile_book_struct.symbol_overview, "symbol_", self.instrument_symbol)

            current_sig = self.shm_root_ptr.shm_update_signature
            if current_sig != EXPECTED_SHM_SIGNATURE:
                logging.info(
                    f"SHM signature mismatch (found {hex(current_sig)}). Initializing for {self.instrument_symbol}.")
                self.mutex_wrapper.lock()
                try:
                    # Zero out only the mobile_book_container part, leave mutex and signature alone for a moment
                    ctypes.memset(ctypes.addressof(self._mobile_book_struct), 0,
                                  ctypes.sizeof(MDContainer))
                    # Re-initialize symbols after memset
                    self._populate_string(self._mobile_book_struct, "symbol_", self.instrument_symbol)
                    self._populate_string(self._mobile_book_struct.top_of_book, "symbol_", self.instrument_symbol)
                    self._populate_string(self._mobile_book_struct.symbol_overview, "symbol_", self.instrument_symbol)
                    # Now set the signature at the root
                    self.shm_root_ptr.shm_update_signature = EXPECTED_SHM_SIGNATURE
                finally:
                    self.mutex_wrapper.unlock()
            logging.info(
                f"Producer for symbol '{self.instrument_symbol}' initialized (SHM: {self.shm_name}).")

        except Exception as e:
            logging.error(f"Error initializing producer for '{self.instrument_symbol}': {e}", exc_info=True)
            self.close()
            raise

    # --- Public Interface Methods (symbol arg is no longer needed) ---

    def update_market_depth_shm(self, md_id: int, side: TickType, position: int,
                                px: float, qty: int, exch_time_ns: int, arrival_time_ns: int,
                                market_maker: Optional[str] = None, is_smart_depth: Optional[bool] = None,
                                cumulative_notional: Optional[float] = None, cumulative_qty: Optional[int] = None,
                                cumulative_avg_px: Optional[float] = None):
        # if not self.mutex_wrapper or not self.semaphore or not self.shm_root_ptr or not self._mobile_book_struct:
        #     return logging.error(f"Producer for '{self.instrument_symbol}' not ready for market depth update.")

        self.mutex_wrapper.lock()
        try:
            md_container = self._mobile_book_struct  # Direct reference
            depth_data = {
                "id": md_id, "symbol": self.instrument_symbol, "side": side, "position": position,
                "px": px, "qty": qty, "exch_time": exch_time_ns, "arrival_time": arrival_time_ns,
                "market_maker": market_maker, "is_smart_depth": is_smart_depth,
                "cumulative_notional": cumulative_notional, "cumulative_qty": cumulative_qty,
                "cumulative_avg_px": cumulative_avg_px
            }

            target_depth_list = None
            if side == TickType.BID:
                target_depth_list = md_container.bid_market_depth_list
            elif side == TickType.ASK:
                target_depth_list = md_container.ask_market_depth_list
            else:
                logging.error(f"Invalid side for market depth: {side}"); return

            if 0 <= position < DEPTH_LVL:
                self._populate_market_depth_entry(target_depth_list[position], depth_data)
            else:
                logging.error(f"Invalid position for market depth: {position}"); return

            md_container.update_counter += 1
            self.shm_root_ptr.shm_update_signature = EXPECTED_SHM_SIGNATURE
        finally:
            self.mutex_wrapper.unlock()
        # self.semaphore.release()

    def update_market_depth_shm_from_msgspec_obj(self, market_depth_obj: MarketDepthMsgspec):
        self.update_market_depth_shm(market_depth_obj.id, market_depth_obj.side, market_depth_obj.position,
                                     market_depth_obj.px, market_depth_obj.qty,
                                     get_epoch_from_pendulum_dt(market_depth_obj.exch_time),
                                     get_epoch_from_pendulum_dt(market_depth_obj.arrival_time),
                                     market_depth_obj.market_maker, market_depth_obj.is_smart_depth,
                                     market_depth_obj.cumulative_notional, market_depth_obj.cumulative_qty,
                                     market_depth_obj.cumulative_avg_px)

    def update_last_barter_shm(self, barter_id: int, exch_id: str,
                              px: float, qty: int, exch_time_ns: int, arrival_time_ns: int,
                              premium: Optional[float] = None,
                              market_barter_volume_data: Optional[Dict] = None):
        # if not self.mutex_wrapper or not self.semaphore or not self.shm_root_ptr or not self._mobile_book_struct:
        #     return logging.error(f"Producer for '{self.instrument_symbol}' not ready for last barter update.")

        self.mutex_wrapper.lock()
        try:
            md_container = self._mobile_book_struct
            last_barter_data = {
                "id": barter_id, "symbol": self.instrument_symbol, "exch_id": exch_id,
                "px": px, "qty": qty, "exch_time": exch_time_ns, "arrival_time": arrival_time_ns,
                "premium": premium, "market_barter_volume": market_barter_volume_data
            }
            self._populate_last_barter(md_container.last_barter, last_barter_data)

            md_container.update_counter += 1
            self.shm_root_ptr.shm_update_signature = EXPECTED_SHM_SIGNATURE
        finally:
            self.mutex_wrapper.unlock()
        # self.semaphore.release()

    def update_last_barter_shm_from_msgspec_obj(self, last_barter_obj: LastBarterMsgspec):
        self.update_last_barter_shm(last_barter_obj.id, last_barter_obj.symbol_n_exch_id.exch_id,
                                   last_barter_obj.px, last_barter_obj.qty, get_epoch_from_pendulum_dt(last_barter_obj.exch_time),
                                   get_epoch_from_pendulum_dt(last_barter_obj.arrival_time),
                                   last_barter_obj.premium, last_barter_obj.market_barter_volume)

    def update_symbol_overview_shm(
            self,
            so_id: int,  # id is required
            # symbol is implicitly self.instrument_symbol
            company: Optional[str] = None,
            exchange_code: Optional[str] = None,
            status: Optional[str] = None,
            lot_size: Optional[int] = None,
            limit_up_px: Optional[float] = None,
            limit_dn_px: Optional[float] = None,
            conv_px: Optional[float] = None,
            closing_px: Optional[float] = None,
            open_px: Optional[float] = None,
            high: Optional[float] = None,
            low: Optional[float] = None,
            volume: Optional[int] = None,
            tick_size: Optional[float] = None,
            last_update_date_time_ns: Optional[int] = None,  # Expect epoch nanoseconds
            force_publish: Optional[bool] = None,
            **kwargs: Any  # To catch any unexpected params and log them
    ):
        # if not self.mutex_wrapper or not self.semaphore or not self.shm_root_ptr or not self._mobile_book_struct:
        #     return logging.error(f"Producer for '{self.instrument_symbol}' not ready for symbol overview update.")

        if kwargs:
            logging.warning(
                f"Unexpected keyword arguments in update_symbol_overview for '{self.instrument_symbol}': {kwargs}")

        self.mutex_wrapper.lock()
        try:
            md_container = self._mobile_book_struct

            # Prepare data dict for the _populate_symbol_overview method
            overview_data = {
                "id": so_id,
                "symbol": self.instrument_symbol,  # Enforce producer's symbol
                "company": company,
                "exchange_code": exchange_code,
                "status": status,
                "lot_size": lot_size,
                "limit_up_px": limit_up_px,
                "limit_dn_px": limit_dn_px,
                "conv_px": conv_px,
                "closing_px": closing_px,
                "open_px": open_px,
                "high": high,
                "low": low,
                "volume": volume,
                "tick_size": tick_size,
                "last_update_date_time": last_update_date_time_ns,
                # Pass as is, _populate handles conversion if pendulum
                "force_publish": force_publish
            }
            # Filter out None values so _populate_symbol_overview correctly sets flags
            # for only the provided fields.
            # _populate_symbol_overview already handles None for optional fields and sets flags.

            self._populate_symbol_overview(md_container.symbol_overview, overview_data)
            md_container.is_symbol_overview_set = True  # Mark the SO as set in MDContainer

            md_container.update_counter += 1
            self.shm_root_ptr.shm_update_signature = EXPECTED_SHM_SIGNATURE
            logging.info(f"SymbolOverview updated for {self.instrument_symbol} (ID: {so_id})")
        except Exception as e:
            logging.error(f"Error updating symbol overview for {self.instrument_symbol}: {e}", exc_info=True)
        finally:
            self.mutex_wrapper.unlock()

        # self.semaphore.release()  # Release semaphore after update

    def update_symbol_overview_shm_from_msgspec_obj(self, symbol_overview_obj: SymbolOverviewMsgspec):
        last_update_date_time = (get_epoch_from_pendulum_dt(symbol_overview_obj.last_update_date_time)
                                 if symbol_overview_obj.last_update_date_time else None)
        self.update_symbol_overview_shm(symbol_overview_obj.id, symbol_overview_obj.company,
                                        symbol_overview_obj.exchange_code, symbol_overview_obj.status,
                                        symbol_overview_obj.lot_size, symbol_overview_obj.limit_up_px,
                                        symbol_overview_obj.limit_dn_px, symbol_overview_obj.conv_px,
                                        symbol_overview_obj.closing_px, symbol_overview_obj.open_px,
                                        symbol_overview_obj.high, symbol_overview_obj.low, symbol_overview_obj.volume,
                                        symbol_overview_obj.tick_size, last_update_date_time,
                                        symbol_overview_obj.force_publish)

    def update_top_of_book_shm(
            self,
            tob_id: int,
            bid_quote_data: Optional[Dict] = None,
            ask_quote_data: Optional[Dict] = None,
            last_barter_data: Optional[Dict] = None,
            total_bartering_security_size: Optional[int] = None,
            market_barter_volume_data: Optional[Dict] = None,
            last_update_date_time_ns: Optional[int] = None
    ):
        self.mutex_wrapper.lock()
        try:
            md_container = self._mobile_book_struct
            tob_container = md_container.top_of_book

            data = {
                "id": tob_id,
                "bid_quote": bid_quote_data,
                "ask_quote": ask_quote_data,
                "last_barter": last_barter_data,
                "total_bartering_security_size": total_bartering_security_size,
                "market_barter_volume": market_barter_volume_data,
                "last_update_date_time": last_update_date_time_ns
            }
            self._populate_top_of_book(tob_container, data)

            md_container.update_counter += 1
            self.shm_root_ptr.shm_update_signature = EXPECTED_SHM_SIGNATURE

        finally:
            self.mutex_wrapper.unlock()

    def update_top_of_book_shm_from_msgspec_obj(self, top_of_book_obj: TopOfBookMsgspec):
        bid_quote_data = None
        if top_of_book_obj.bid_quote:
            bid_quote_data = {"px": top_of_book_obj.bid_quote.px, "qty": top_of_book_obj.bid_quote.qty,
                              "premium": top_of_book_obj.bid_quote.premium,
                              "last_update_date_time": get_epoch_from_pendulum_dt(
                                  top_of_book_obj.bid_quote.last_update_date_time) if top_of_book_obj.bid_quote.last_update_date_time else None}

        ask_quote_data = None
        if top_of_book_obj.ask_quote:
            ask_quote_data = {"px": top_of_book_obj.ask_quote.px, "qty": top_of_book_obj.ask_quote.qty,
                              "premium": top_of_book_obj.ask_quote.premium,
                              "last_update_date_time": get_epoch_from_pendulum_dt(
                                  top_of_book_obj.ask_quote.last_update_date_time) if top_of_book_obj.ask_quote.last_update_date_time else None}

        last_barter_data = None
        if top_of_book_obj.last_barter:
            last_barter_data = {"px": top_of_book_obj.last_barter.px, "qty": top_of_book_obj.last_barter.qty,
                               "premium": top_of_book_obj.last_barter.premium,
                               "last_update_date_time": get_epoch_from_pendulum_dt(
                                   top_of_book_obj.last_barter.last_update_date_time) if top_of_book_obj.last_barter.last_update_date_time else None}

        market_barter_volume_data = None
        if top_of_book_obj.market_barter_volume and top_of_book_obj.market_barter_volume[0]:
            mtv = top_of_book_obj.market_barter_volume[0]
            market_barter_volume_data = {"id": mtv.id,
                                        "participation_period_last_barter_qty_sum": mtv.participation_period_last_barter_qty_sum,
                                        "applicable_period_seconds": mtv.applicable_period_seconds}

        last_update_date_time_ns = get_epoch_from_pendulum_dt(
            top_of_book_obj.last_update_date_time) if top_of_book_obj.last_update_date_time else None

        self.update_top_of_book_shm(
            tob_id=top_of_book_obj.id,
            bid_quote_data=bid_quote_data,
            ask_quote_data=ask_quote_data,
            last_barter_data=last_barter_data,
            total_bartering_security_size=top_of_book_obj.total_bartering_security_size,
            market_barter_volume_data=market_barter_volume_data,
            last_update_date_time_ns=last_update_date_time_ns
        )

    def _convert_c_mtv_to_msgspec_mtv(self, c_mtv: MarketBarterVolume) -> Optional[MarketBarterVolumeMsgspec]:
        if not c_mtv:
            return None

        return MarketBarterVolumeMsgspec(
            id=c_mtv.id_.decode('utf-8'),
            participation_period_last_barter_qty_sum=(
                c_mtv.participation_period_last_barter_qty_sum_ if c_mtv.is_participation_period_last_barter_qty_sum_set_ else None),
            applicable_period_seconds=(
                c_mtv.applicable_period_seconds_ if c_mtv.is_applicable_period_seconds_set_ else None)
        )

    # --- Private _populate_* methods (identical to previous versions) ---
    def _populate_string(self, parent_struct: Structure, field_name_str: str, python_string: str):
        # ... (Implementation from previous correct version)
        try:
            field_descriptor = getattr(type(parent_struct), field_name_str)
            field_address = ctypes.addressof(parent_struct) + field_descriptor.offset
            buffer_capacity = field_descriptor.size
            if buffer_capacity <= 0: return
            if python_string is None: python_string = ""
            encoded_str = python_string.encode('utf-8')
            num_bytes_to_copy = min(len(encoded_str), buffer_capacity - 1)
            ctypes.memset(field_address, 0, buffer_capacity)
            if num_bytes_to_copy > 0:
                ctypes.memmove(field_address, encoded_str, num_bytes_to_copy)
        except AttributeError:
            logging.error(f"Field '{field_name_str}' not found in {type(parent_struct).__name__}.", exc_info=True)
        except Exception as e:
            logging.error(f"Error populating string for field '{field_name_str}': {e}", exc_info=True)

    def _populate_quote(self, quote_struct: Quote, data: Dict[str, Any]):
        # ... (Implementation from previous correct version)
        if data.get("px") is not None:
            quote_struct.px_ = float(data["px"])
            quote_struct.is_px_set_ = True
        else:
            quote_struct.is_px_set_ = False
        if data.get("qty") is not None:
            quote_struct.qty_ = int(data["qty"])
            quote_struct.is_qty_set_ = True
        else:
            quote_struct.is_qty_set_ = False
        if data.get("premium") is not None:
            quote_struct.premium_ = float(data["premium"])
            quote_struct.is_premium_set_ = True
        else:
            quote_struct.is_premium_set_ = False
        if data.get("last_update_date_time") is not None:
            dt_val = data["last_update_date_time"]
            quote_struct.last_update_date_time_ = int(dt_val.timestamp() * 1_000_000_000) if isinstance(dt_val,
                                                                                                        pendulum.DateTime) else int(
                dt_val)
            quote_struct.is_last_update_date_time_set_ = True
        else:
            quote_struct.is_last_update_date_time_set_ = False

    def _populate_market_barter_volume(self, mtv_struct: MarketBarterVolume, data: Dict[str, Any]):
        # ... (Implementation from previous correct version)
        self._populate_string(mtv_struct, "id_", data.get("id", ""))
        if data.get("participation_period_last_barter_qty_sum") is not None:
            mtv_struct.participation_period_last_barter_qty_sum_ = int(data["participation_period_last_barter_qty_sum"])
            mtv_struct.is_participation_period_last_barter_qty_sum_set_ = True
        else:
            mtv_struct.is_participation_period_last_barter_qty_sum_set_ = False
        if data.get("applicable_period_seconds") is not None:
            mtv_struct.applicable_period_seconds_ = int(data["applicable_period_seconds"])
            mtv_struct.is_applicable_period_seconds_set_ = True
        else:
            mtv_struct.is_applicable_period_seconds_set_ = False

    def _populate_last_barter(self, lt_struct: LastBarter, data: Dict[str, Any]):
        # ... (Implementation from previous correct version)
        lt_struct.id = data.get("id", 0)
        self._populate_string(lt_struct.symbol_n_exch_id, "symbol_", data.get("symbol", ""))  # Symbol comes from data
        self._populate_string(lt_struct.symbol_n_exch_id, "exch_id_", data.get("exch_id", ""))
        lt_struct.exch_time_ = int(data.get("exch_time", 0))
        lt_struct.arrival_time_ = int(data.get("arrival_time", 0))
        lt_struct.px = float(data.get("px", 0.0))
        lt_struct.qty = int(data.get("qty", 0))
        if data.get("premium") is not None:
            lt_struct.premium_ = float(data["premium"])
            lt_struct.is_premium_set_ = True
        else:
            lt_struct.is_premium_set_ = False
        if data.get("market_barter_volume"):
            self._populate_market_barter_volume(lt_struct.market_barter_volume_, data["market_barter_volume"])
            lt_struct.is_market_barter_volume_set_ = True
        else:
            lt_struct.is_market_barter_volume_set_ = False

    def _populate_top_of_book(self, tob_struct: TopOfBook, data: Dict[str, Any]):
        if data.get("id") is not None:
            tob_struct.id = int(data["id"])
        # else keeping None

        if data.get("bid_quote") is not None:
            self._populate_quote(tob_struct.bid_quote_, data["bid_quote"])
            tob_struct.is_bid_quote_set_ = True
        else:
            tob_struct.is_bid_quote_set_ = False

        if data.get("ask_quote") is not None:
            self._populate_quote(tob_struct.ask_quote_, data["ask_quote"])
            tob_struct.is_ask_quote_set_ = True
        else:
            tob_struct.is_ask_quote_set_ = False

        if data.get("last_barter") is not None:
            self._populate_quote(tob_struct.last_barter_, data["last_barter"])
            tob_struct.is_last_barter_set_ = True
        else:
            tob_struct.is_last_barter_set_ = False

        if data.get("total_bartering_security_size") is not None:
            tob_struct.total_bartering_security_size_ = int(data["total_bartering_security_size"])
            tob_struct.is_total_bartering_security_size_set_ = True
        else:
            tob_struct.is_total_bartering_security_size_set_ = False

        if data.get("market_barter_volume") is not None:
            self._populate_market_barter_volume(tob_struct.market_barter_volume_, data["market_barter_volume"])
            tob_struct.is_market_barter_volume_set_ = True
        else:
            tob_struct.is_market_barter_volume_set_ = False

        if data.get("last_update_date_time") is not None:
            dt_val = data["last_update_date_time"]
            tob_struct.last_update_date_time_ = int(dt_val.timestamp() * 1_000_000_000) if isinstance(dt_val, pendulum.DateTime) else int(dt_val)
            tob_struct.is_last_update_date_time_set_ = True
        else:
            tob_struct.is_last_update_date_time_set_ = False

    def _populate_symbol_overview(self, so_struct: SymbolOverview, data: Dict[str, Any]):
        # ... (Implementation from previous correct version)
        so_struct.id_ = data.get("id", 0)
        self._populate_string(so_struct, "symbol_", data.get("symbol", ""))  # Symbol from data
        if data.get("company") is not None:
            self._populate_string(so_struct, "company_", data["company"]); so_struct.is_company_set_ = True
        else:
            so_struct.is_company_set_ = False
        if data.get("exchange_code") is not None:
            self._populate_string(so_struct, "exchange_code_", data["exchange_code"]); so_struct.is_exchange_code_set_ = True
        else:
            so_struct.is_exchange_code_set_ = False
        if data.get("status") is not None:
            self._populate_string(so_struct, "status_", data["status"]); so_struct.is_status_set_ = True
        else:
            so_struct.is_status_set_ = False
        for field_name, ctype_name_suffix in [
            ("lot_size", "int64"), ("limit_up_px", "double"), ("limit_dn_px", "double"),
            ("conv_px", "double"), ("closing_px", "double"), ("open_px", "double"),
            ("high", "double"), ("low", "double"), ("volume", "int64"),
            ("tick_size", "double"), ("force_publish", "bool")]:
            if data.get(field_name) is not None:
                if ctype_name_suffix == "int64":
                    setattr(so_struct, f"{field_name}_", int(data[field_name]))
                elif ctype_name_suffix == "double":
                    setattr(so_struct, f"{field_name}_", float(data[field_name]))
                elif ctype_name_suffix == "bool":
                    setattr(so_struct, f"{field_name}_", bool(data[field_name]))
                setattr(so_struct, f"is_{field_name}_set_", True)
            else:
                setattr(so_struct, f"is_{field_name}_set_", False)
        if data.get("last_update_date_time") is not None:
            dt_val = data["last_update_date_time"]
            so_struct.last_update_date_time_ = int(dt_val)
            so_struct.is_last_update_date_time_set_ = True
        else:
            so_struct.is_last_update_date_time_set_ = False

    def _populate_market_depth_entry(self, md_struct: MarketDepth, data: Dict[str, Any]):
        # ... (Implementation from previous correct version)
        md_struct.id = data.get("id", 0)
        self._populate_string(md_struct, "symbol_", data.get("symbol", ""))  # Symbol from data
        md_struct.exch_time_ = int(data.get("exch_time", 0))
        md_struct.arrival_time_ = int(data.get("arrival_time", 0))
        side_val = data.get("side")
        side_char = b'A'
        if side_val == TickType.BID or str(side_val).upper() == "BID" or str(side_val).upper() == "B": side_char = b'B'
        md_struct.side_ = side_char
        if data.get("px") is not None:
            md_struct.px_ = float(data["px"]); md_struct.is_px_set_ = True
        else:
            md_struct.is_px_set_ = False
        if data.get("qty") is not None:
            md_struct.qty_ = int(data["qty"]); md_struct.is_qty_set_ = True
        else:
            md_struct.is_qty_set_ = False
        md_struct.position = int(data.get("position", -1))
        if data.get("market_maker") is not None:
            self._populate_string(md_struct, "market_maker_",
                                  data["market_maker"]); md_struct.is_market_maker_set_ = True
        else:
            self._populate_string(md_struct, "market_maker_", ""); md_struct.is_market_maker_set_ = False
        if data.get("is_smart_depth") is not None:
            md_struct.is_smart_depth_ = bool(data["is_smart_depth"]); md_struct.is_is_smart_depth_set_ = True
        else:
            md_struct.is_is_smart_depth_set_ = False
        if data.get("cumulative_notional") is not None:
            md_struct.cumulative_notional_ = float(
                data["cumulative_notional"]); md_struct.is_cumulative_notional_set_ = True
        else:
            md_struct.is_cumulative_notional_set_ = False
        if data.get("cumulative_qty") is not None:
            md_struct.cumulative_qty_ = int(data["cumulative_qty"]); md_struct.is_cumulative_qty_set_ = True
        else:
            md_struct.is_cumulative_qty_set_ = False
        if data.get("cumulative_avg_px") is not None:
            md_struct.cumulative_avg_px_ = float(data["cumulative_avg_px"]); md_struct.is_cumulative_avg_px_set_ = True
        else:
            md_struct.is_cumulative_avg_px_set_ = False

    def close(self):
        logging.info(f"Closing producer for '{self.instrument_symbol}'...")
        if self.mutex_wrapper: self.mutex_wrapper = None

        self._mobile_book_struct = None  # Clear direct reference to nested MDContainer
        if self.shm_root_ptr is not None: self.shm_root_ptr = None

        import gc  # Ensure gc is imported
        gc.collect()
        gc.collect()

        if self.mmap_obj:
            try:
                self.mmap_obj.close(); logging.info(f"MMAP for {self.shm_name} closed.")
            except Exception as e:
                logging.error(f"Error closing mmap for {self.shm_name}: {e}", exc_info=True)
            finally:
                self.mmap_obj = None

        if self.shm and hasattr(self.shm, 'fd') and self.shm.fd >= 0:
            shm_fd_to_close = self.shm.fd
            try:
                self.shm.unlink() # Optional
            except Exception as e:
                logging.error(f"Error unlinking SHM {self.shm_name}: {e}", exc_info=True)
            finally:
                try:
                    if hasattr(self.shm, 'close_fd') and callable(self.shm.close_fd):
                        self.shm.close_fd()
                    elif shm_fd_to_close >= 0:
                        os.close(shm_fd_to_close)
                    logging.debug(f"SHM FD for {self.shm_name} closed.")
                except Exception as e:
                    logging.error(f"Error closing SHM FD {self.shm_name}: {e}", exc_info=True)
                self.shm = None

        # if self.semaphore:
        #     try:
        #         pass  # self.semaphore.unlink() # Optional
        #     except Exception as e:
        #         logging.error(f"Error unlinking SEM {self.sem_name}: {e}", exc_info=True)
        #     finally:
        #         try:
        #             self.semaphore.close(); logging.debug(f"SEM {self.sem_name} closed.")
        #         except Exception as e:
        #             logging.error(f"Error closing SEM {self.sem_name}: {e}", exc_info=True)
        #         self.semaphore = None
        logging.info(f"Producer for '{self.instrument_symbol}' closed.")


# --- Example Usage ---
if __name__ == "__main__":
    # Each symbol would get its own SHM name, e.g., based on the symbol itself
    SYMBOL = "SPY"
    SHM_NAME_FOR_SYMBOL = f"md_shm_{SYMBOL.lower()}"
    SEM_NAME_FOR_SYMBOL = f"md_sem_{SYMBOL.lower()}"

    try:
        posix_ipc.unlink_shared_memory(f"/{SHM_NAME_FOR_SYMBOL}")
    except posix_ipc.ExistentialError:
        pass
    try:
        posix_ipc.unlink_semaphore(f"/{SEM_NAME_FOR_SYMBOL}")
    except posix_ipc.ExistentialError:
        pass

    producer = None
    try:
        producer = MobileBookSharedMemoryProducer(SYMBOL)
        now_ns = producer._now_ns()

        logging.info(f"\n--- Updating data for {SYMBOL} ---")

        # Symbol Overview
        spy_so_data = {
            "so_id": 10, "company": "SPDR S&P 500 ETF Trust", "exchange_code": "TSE", "status": "Bartering",
            "lot_size": 1, "tick_size": 0.01, "last_update_date_time": now_ns,
            "closing_px": 450.00, "open_px": 450.50, "high": 451.00, "low": 449.00, "volume": 5000000
        }
        producer.update_symbol_overview_shm(**spy_so_data)
        time.sleep(0.1)

        # Market Depth
        producer.update_market_depth_shm(md_id=1, side=TickType.BID, position=0, px=450.55, qty=200, exch_time_ns=now_ns,
                                         arrival_time_ns=now_ns)
        producer.update_market_depth_shm(md_id=2, side=TickType.BID, position=1, px=450.54, qty=300, exch_time_ns=now_ns,
                                         arrival_time_ns=now_ns)
        producer.update_market_depth_shm(md_id=3, side=TickType.ASK, position=0, px=450.60, qty=150, exch_time_ns=now_ns,
                                         arrival_time_ns=now_ns)
        time.sleep(0.1)

        # Last Barter
        producer.update_last_barter_shm(barter_id=1001, exch_id="ARCA", px=450.58, qty=50, exch_time_ns=now_ns,
                                       arrival_time_ns=now_ns)
        time.sleep(0.1)

        # Update L0 Bid
        producer.update_market_depth_shm(md_id=4, side=TickType.BID, position=0, px=450.56, qty=250, exch_time_ns=now_ns,
                                         arrival_time_ns=now_ns)

        logging.info(f"\nFinished producing market data for {SYMBOL}.")
        logging.info(f"Run visualizer with: --shm_name {SHM_NAME_FOR_SYMBOL} --sem_name {SEM_NAME_FOR_SYMBOL}")


    except Exception as e:
        logging.error(f"Main execution error for {SYMBOL}: {e}", exc_info=True)
    finally:
        if producer:
            producer.close()
            # Optional: Unlink for testing; in prod, lifecycle might be different
            # try: posix_ipc.unlink_shared_memory(producer.shm_name)
            # except: pass
            # try: posix_ipc.unlink_semaphore(producer.sem_name)
            # except: pass
