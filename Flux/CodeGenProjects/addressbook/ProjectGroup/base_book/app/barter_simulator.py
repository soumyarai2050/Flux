import logging
import random
from typing import ClassVar, List, Dict, Tuple
import re
import os
from pathlib import PurePath

from pendulum import DateTime
from filelock import FileLock

from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link_base import (
    BarteringLinkBase, add_to_texts)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import (
    executor_config_yaml_dict, EXECUTOR_PROJECT_DATA_DIR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.phone_book_service_helper import get_symbol_side_key
from FluxPythonUtils.scripts.file_utility_functions import (
    dict_or_list_records_csv_writer, get_fieldnames_from_record_type)
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *


def init_symbol_configs():
    symbol_configs: Dict | None = BarteringLinkBase.simulate_config_dict.get("symbol_configs") \
        if BarteringLinkBase.simulate_config_dict is not None else None
    if symbol_configs:
        regex_symbol_configs: Dict = {re.compile(k, re.IGNORECASE): v for k, v in symbol_configs.items()}
        return regex_symbol_configs


class BarterSimulator(BarteringLinkBase):

    int_id: ClassVar[int] = 1
    continuous_symbol_based_chores_counter: ClassVar[Dict | None] = {}
    cxl_rej_symbol_to_bool_dict: ClassVar[Dict | None] = {}
    symbol_configs: ClassVar[Dict | None] = init_symbol_configs()
    special_chore_counter = 0
    intraday_bartering_chores_csv_file_name: str = f"intraday_bartering_chores_{DateTime.now().strftime('%Y%m%d')}"
    intraday_bartering_chores_lock_file_name: str = f"intraday_bartering_chores.lock"
    intraday_bartering_chores_csv_file: PurePath = EXECUTOR_PROJECT_DATA_DIR / intraday_bartering_chores_csv_file_name
    intraday_bartering_chores_lock_file: PurePath = EXECUTOR_PROJECT_DATA_DIR / intraday_bartering_chores_lock_file_name

    @classmethod
    def reload_symbol_configs(cls):
        # reloading executor configs
        BarteringLinkBase.reload_executor_configs()
        cls.symbol_configs = init_symbol_configs()
        cls.special_chore_counter = 0

    @classmethod
    def get_symbol_configs(cls, symbol: str) -> Dict | None:
        """ WARNING : SLOW FUNCTION to be used only on simulator or non-critical path"""
        found_symbol_config_list: List = []
        if cls.symbol_configs is not None:
            for k, v in cls.symbol_configs.items():
                if k.match(symbol):
                    found_symbol_config_list.append(v)
            if found_symbol_config_list:
                if len(found_symbol_config_list) == 1:
                    return found_symbol_config_list[0]
                else:
                    logging.error(f"bad configuration : multiple symbol matches found for passed symbol: {symbol};;;"
                                  f"found_symbol_configurations: "
                                  f"{[str(found_symbol_config) for found_symbol_config in found_symbol_config_list]}")
            else:
                return cls.symbol_configs.get(re.compile("default", re.IGNORECASE))  # default symbol config
        return None

    def __init__(self):
        super(BarterSimulator, self).__init__(executor_config_yaml_dict.get("inst_id"))

    @classmethod
    def is_special_chore(cls, symbol: str) -> bool:

        if symbol not in cls.continuous_symbol_based_chores_counter:
            symbol_configs = cls.get_symbol_configs(symbol)
            continuous_chore_count = fetched_continuous_chore_count \
                if (fetched_continuous_chore_count := symbol_configs.get("continues_chore_count")) is not None else 1
            continues_special_chore_count = fetched_continues_special_chore_count \
                if (fetched_continues_special_chore_count := symbol_configs.get("continues_special_chore_count")) is not None else 0

            cls.continuous_symbol_based_chores_counter[symbol] = {
                "chore_counter": 0,
                "continues_chore_count": continuous_chore_count,
                "special_chore_counter": 0,
                "continues_special_chore_count": continues_special_chore_count
            }

        if cls.continuous_symbol_based_chores_counter[symbol]["chore_counter"] < \
                cls.continuous_symbol_based_chores_counter[symbol]["continues_chore_count"]:
            cls.continuous_symbol_based_chores_counter[symbol]["chore_counter"] += 1
            return False
        else:
            if cls.continuous_symbol_based_chores_counter[symbol]["special_chore_counter"] < \
                    cls.continuous_symbol_based_chores_counter[symbol]["continues_special_chore_count"]:
                cls.continuous_symbol_based_chores_counter[symbol]["special_chore_counter"] += 1
                cls.special_chore_counter += 1
                return True
            else:
                cls.continuous_symbol_based_chores_counter[symbol]["chore_counter"] = 1
                cls.continuous_symbol_based_chores_counter[symbol]["special_chore_counter"] = 0
                return False

    @classmethod
    async def process_chore_reject(cls, chore_brief: ChoreBrief):
        if BarterSimulator.chore_create_async_callable:
            create_date_time = DateTime.utcnow()

            if cls.special_chore_counter % 2 == 0:
                chore_event = ChoreEventType.OE_BRK_REJ
            else:
                chore_event = ChoreEventType.OE_EXH_REJ

            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=create_date_time,
                                         chore_event=chore_event)
            msg = f"SIM:Chore REJ for {chore_ledger.chore.security.sec_id}, chore_id {chore_ledger.chore.chore_id} " \
                  f"and side {chore_ledger.chore.side}"
            add_to_texts(chore_brief, msg)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def place_new_chore(cls, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
                              bartering_sec_type: str, account: str, exchange: str | None = None, text: List[str] | None = None,
                              client_ord_id: str | None = None, **kwargs) -> Tuple[bool, str]:
        """
        when invoked form log analyzer - all params are passed as strings
        msgspec default conversion handles conversion - any util functions called should be called with
        explicit type convertors or msgspec object converted values
        return bool indicating success/fail and unique-id-str/err-description in second param
        """
        if BarterSimulator.chore_create_async_callable:
            create_date_time = DateTime.utcnow()
            chore_id: str = f"{bartering_sec_id}-{create_date_time}"
            # use system_sec_id to create system's internal chore brief / ledger
            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            bartering_security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)

            chore_brief = ChoreBrief(chore_id=chore_id, security=security, bartering_security=bartering_security, side=side,
                                     px=px, qty=qty,
                                     underlying_account=account, exchange=exchange,
                                     user_data=client_ord_id)
            msg = f"SIM: Choreing {bartering_sec_id}/{system_sec_id}, qty {qty} and px {px}"
            add_to_texts(chore_brief, msg)

            chore_ledger = ChoreLedger(chore=chore_brief,
                                         chore_event_date_time=create_date_time,
                                         chore_event=ChoreEventType.OE_NEW)
            await BarterSimulator.chore_create_async_callable(chore_ledger)
            logging.info(f"placed new chore with Simulator, qty: {qty} for symbol_side_key: "
                         f"{get_symbol_side_key([(system_sec_id, side)])}")

            symbol_configs = cls.get_symbol_configs(system_sec_id)

            if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
                if symbol_configs.get("simulate_new_to_reject_chores") and cls.is_special_chore(system_sec_id):
                    await cls.process_chore_reject(chore_brief)
                elif symbol_configs.get("simulate_new_unsolicited_cxl_chores") and cls.is_special_chore(system_sec_id):
                    await cls.process_cxl_ack(chore_brief, is_unsol_cxl=True)
                elif symbol_configs.get("simulate_new_to_cxl_rej_chores") and cls.is_special_chore(system_sec_id):
                    cls.cxl_rej_symbol_to_bool_dict[system_sec_id] = True
                    await cls.place_cxl_chore(chore_id, side, security.sec_id, security.sec_id, account)
                elif symbol_configs.get("simulate_deals_pre_chore_ack") and cls.is_special_chore(system_sec_id):
                    await cls.process_fill(chore_id, px, qty, side, security.sec_id, security.sec_id)
                else:
                    await cls.process_chore_ack(chore_id, chore_brief.px, chore_brief.qty, chore_brief.side, system_sec_id,
                                                account)
        cls.int_id += 1
        return True, str(cls.int_id)  # indicates chore send success (send false otherwise)

    @classmethod
    def get_partial_allowed_ack_qty(cls, symbol: str, qty: int):
        symbol_configs = cls.get_symbol_configs(symbol)

        if symbol_configs is not None:
            if (ack_percent := symbol_configs.get("ack_percent")) is not None:
                qty = int((ack_percent / 100) * qty)
        return qty

    @classmethod
    def _process_chore_ack(cls, chore_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                           text: List[str] | None = None) -> ChoreLedger:
        security = Security(sec_id=sec_id, sec_id_source=SecurityIdSource.TICKER)

        qty = cls.get_partial_allowed_ack_qty(sec_id, qty)
        chore_brief_obj = ChoreBrief(chore_id=chore_id, security=security, side=side, px=px, qty=qty,
                                     underlying_account=underlying_account)
        msg = f"SIM: ACK received for {sec_id}, qty {qty} and px {px}"
        add_to_texts(chore_brief_obj, msg)

        chore_ledger_obj = ChoreLedger(chore=chore_brief_obj,
                                         chore_event_date_time=DateTime.utcnow(),
                                         chore_event=ChoreEventType.OE_ACK)
        return chore_ledger_obj

    @classmethod
    async def _process_chore_ack_symbol_specific_handling(cls, chore_ledger_obj: ChoreLedger):
        symbol_configs = cls.get_symbol_configs(chore_ledger_obj.chore.security.sec_id)
        if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
            if (symbol_configs.get("simulate_ack_to_reject_chores") and
                    cls.is_special_chore(chore_ledger_obj.chore.security.sec_id)):
                await cls.process_chore_reject(chore_ledger_obj.chore)
            elif (symbol_configs.get("simulate_ack_unsolicited_cxl_chores") and
                  cls.is_special_chore(chore_ledger_obj.chore.security.sec_id)):
                await cls.process_cxl_ack(chore_ledger_obj.chore, is_unsol_cxl=True)
            else:
                if not symbol_configs.get("simulate_avoid_fill_after_ack"):
                    await cls.process_fill(chore_ledger_obj.chore.chore_id, chore_ledger_obj.chore.px,
                                           chore_ledger_obj.chore.qty, chore_ledger_obj.chore.side,
                                           chore_ledger_obj.chore.security.sec_id,
                                           chore_ledger_obj.chore.underlying_account)

                if (symbol_configs.get("simulate_ack_to_cxl_rej_chores") and
                        cls.is_special_chore(chore_ledger_obj.chore.security.sec_id)):
                    cls.cxl_rej_symbol_to_bool_dict[chore_ledger_obj.chore.security.sec_id] = True
                    await cls.place_cxl_chore(chore_ledger_obj.chore.chore_id, chore_ledger_obj.chore.side,
                                              chore_ledger_obj.chore.security.sec_id,
                                              chore_ledger_obj.chore.security.sec_id,
                                              chore_ledger_obj.chore.underlying_account,
                                              px=chore_ledger_obj.chore.px,
                                              qty=chore_ledger_obj.chore.qty)

    @classmethod
    async def process_chore_ack(cls, chore_id, px: float, qty: int, side: Side, sec_id: str,
                                underlying_account: str, text: List[str] | None = None):
        """simulate chore's Ack """
        if BarterSimulator.chore_create_async_callable:
            chore_ledger_obj = cls._process_chore_ack(chore_id, px, qty, side, sec_id, underlying_account, text)
            await BarterSimulator.chore_create_async_callable(chore_ledger_obj)
            await cls._process_chore_ack_symbol_specific_handling(chore_ledger_obj)

    @classmethod
    def get_partial_qty_from_total_qty_and_percentage(cls, fill_percent: int, total_qty: int) -> int:
        return int((fill_percent / 100) * total_qty)

    @classmethod
    def get_partial_allowed_fill_qty(cls, symbol: str, qty: int):
        symbol_configs = cls.get_symbol_configs(symbol)

        if symbol_configs is not None:
            if (fill_percent := symbol_configs.get("fill_percent")) is not None:
                qty = cls.get_partial_qty_from_total_qty_and_percentage(fill_percent, qty)
        return qty

    @classmethod
    def _process_fill(cls, sec_id: str, qty: int) -> Tuple[int, int]:
        symbol_configs = cls.get_symbol_configs(sec_id)
        if symbol_configs is not None:
            if (total_fill_count := symbol_configs.get("total_fill_count")) is None:
                total_fill_count = 1
        else:
            total_fill_count = 1
        qty = cls.get_partial_allowed_fill_qty(sec_id, qty)
        return qty, total_fill_count

    @classmethod
    def store_intraday_chore_deals(cls, intraday_chore_deals: List[DealsLedger]):
        if not intraday_chore_deals:
            logging.warning("No intraday chore deals to store")
            return

        include_header: bool = False
        with FileLock(str(cls.intraday_bartering_chores_lock_file)):
            if not os.path.exists(f"{str(cls.intraday_bartering_chores_csv_file)}.csv"):
                include_header = True
            # file already exists, don't include headers
            fieldnames = get_fieldnames_from_record_type(DealsLedger)
            dict_or_list_records_csv_writer(cls.intraday_bartering_chores_csv_file_name, intraday_chore_deals,
                                            fieldnames, DealsLedger, EXECUTOR_PROJECT_DATA_DIR, append_mode=True,
                                            include_header=include_header, by_alias=True)

    @classmethod
    async def process_fill(cls, chore_id, px: float, qty: int, side: Side, sec_id: str,
                           underlying_account: str, use_exact_passed_qty: bool | None = None) -> bool:
        """Simulates Chore's deals - returns True if fully deals chore else returns False"""
        if BarterSimulator.fill_create_async_callable:

            if use_exact_passed_qty:
                fill_qty, total_fill_count = qty, 1
            else:
                fill_qty, total_fill_count = cls._process_fill(sec_id, qty)

            total_fill_qty = 0
            intraday_chore_deals: List[DealsLedger] = []
            for fill_count in range(total_fill_count):
                fill_ledger = DealsLedger(chore_id=chore_id, fill_px=px, fill_qty=fill_qty, fill_symbol=sec_id,
                                            fill_side=side, underlying_account=underlying_account,
                                            fill_date_time=DateTime.utcnow(),
                                            fill_id=f"F{chore_id[1:]}")
                total_fill_count += fill_count
                fill_ledger = await BarterSimulator.fill_create_async_callable(fill_ledger)
                intraday_chore_deals.append(fill_ledger)

            cls.store_intraday_chore_deals(intraday_chore_deals)
            if total_fill_qty == qty:
                return True
            else:
                return False

    @classmethod
    async def force_fully_fill(cls, chore_id, px: float, qty: int, side: Side, sec_id: str,
                               underlying_account: str):
        """Simulates Chore's force fully fill """
        if BarterSimulator.fill_create_async_callable:
            symbol_configs = cls.get_symbol_configs(sec_id)

            fill_percent = symbol_configs.get("fill_percent")

            if fill_percent is None:
                fill_qty = qty
            else:
                remaining_qty_per = 100 - fill_percent
                fill_qty = cls.get_partial_qty_from_total_qty_and_percentage(remaining_qty_per, qty)

            fill_ledger = DealsLedger(chore_id=chore_id, fill_px=px, fill_qty=fill_qty, fill_symbol=sec_id,
                                        fill_side=side, underlying_account=underlying_account,
                                        fill_date_time=DateTime.utcnow(),
                                        fill_id=f"F{chore_id[1:]}")
            await BarterSimulator.fill_create_async_callable(fill_ledger)

    @classmethod
    async def process_cxl_rej(cls, chore_brief: ChoreBrief):
        if BarterSimulator.chore_create_async_callable:
            chore_event = random.choice([ChoreEventType.OE_CXL_INT_REJ,
                                          ChoreEventType.OE_CXL_BRK_REJ,
                                          ChoreEventType.OE_CXL_EXH_REJ])
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=chore_event)
            msg = f"SIM:Cancel REJ for {chore_ledger.chore.security.sec_id}, chore_id {chore_ledger.chore.chore_id} " \
                  f"and side {chore_ledger.chore.side}"
            add_to_texts(chore_brief, msg)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def process_cxl_ack(cls, chore_brief: ChoreBrief, is_unsol_cxl: bool | None = None):
        if BarterSimulator.chore_create_async_callable:

            if is_unsol_cxl:
                chore_event = ChoreEventType.OE_UNSOL_CXL
            else:
                chore_event = ChoreEventType.OE_CXL_ACK

            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=chore_event)
            msg = f"SIM:Cancel ACK for {chore_ledger.chore.security.sec_id}, chore_id {chore_ledger.chore.chore_id} " \
                  f"and side {chore_ledger.chore.side}"
            add_to_texts(chore_brief, msg)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def place_cxl_chore(cls, chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = "bartering-account",
                              px: int | None = None, qty: int | None = None):
        """
        cls.simulate_reverse_path or not - always simulate cancel chore's Ack/Rejects (unless configured for unack)
        when invoked form log analyzer - all params are passed as strings
        msgspec default conversion handles conversion - any util functions called should be called with
        explicit type convertors or ORMModel object converted values
        """
        if BarterSimulator.chore_create_async_callable:

            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            # query chore
            chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side,
                                     underlying_account=underlying_account,
                                     user_data=executor_config_yaml_dict.get("inst_id"))
            msg = f"SIM:Cancel Request for {bartering_sec_id}/{system_sec_id}, chore_id {chore_id} and side {side}"
            add_to_texts(chore_brief, msg)
            # simulate cancel ack
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=ChoreEventType.OE_CXL)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

            if system_sec_id in cls.cxl_rej_symbol_to_bool_dict and cls.cxl_rej_symbol_to_bool_dict.get(system_sec_id):
                symbol_configs = cls.get_symbol_configs(system_sec_id)
                if symbol_configs.get("force_fully_fill"):
                    await cls.force_fully_fill(chore_id, px, qty, side, system_sec_id, underlying_account)

                cls.cxl_rej_symbol_to_bool_dict[system_sec_id] = False
                await cls.process_cxl_rej(chore_brief)
            else:
                symbol_configs = cls.get_symbol_configs(system_sec_id)
                if not symbol_configs.get("avoid_cxl_ack_after_cxl_req"):
                    await cls.process_cxl_ack(chore_brief)

    @classmethod
    async def place_amend_req_chore(cls, chore_id: str, side: Side, bartering_sec_id: str,
                                    system_sec_id: str, amend_event: ChoreEventType,
                                    underlying_account: str | None = "bartering-account",
                                    px: float | None = None, qty: int | None = None):
        if BarterSimulator.chore_create_async_callable:

            if px is None and qty is None:
                logging.error("Both Px and Qty can't be None while placing amend chore - ignoring this "
                              "amend chore creation")
                return

            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            # query chore
            chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side,
                                     underlying_account=underlying_account, px=px, qty=qty)
            msg = f"SIM:Amend Request for {bartering_sec_id}/{system_sec_id}, chore_id {chore_id} and side {side}"
            add_to_texts(chore_brief, msg)
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=amend_event)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def place_amend_ack_chore(cls, chore_id: str, side: Side, bartering_sec_id: str,
                                    system_sec_id: str, underlying_account: str | None = "bartering-account"):
        if BarterSimulator.chore_create_async_callable:

            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            # query chore
            chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side,
                                     underlying_account=underlying_account)
            msg = f"SIM:Amend ACK for {bartering_sec_id}/{system_sec_id}, chore_id {chore_id} and side {side}"
            add_to_texts(chore_brief, msg)
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=ChoreEventType.OE_AMD_ACK)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def place_amend_rej_chore(cls, chore_id: str, side: Side, bartering_sec_id: str,
                                    system_sec_id: str, underlying_account: str | None = "bartering-account"):
        if BarterSimulator.chore_create_async_callable:
            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            # query chore
            chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side,
                                     underlying_account=underlying_account)
            msg = f"SIM:Amend REJ for {bartering_sec_id}/{system_sec_id}, chore_id {chore_id} and side {side}"
            add_to_texts(chore_brief, msg)
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=ChoreEventType.OE_AMD_REJ)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def place_lapse_chore(cls, chore_id: str, side: Side, bartering_sec_id: str, system_sec_id: str,
                                underlying_account: str | None = "bartering-account", qty: int | None = None):
        if BarterSimulator.chore_create_async_callable:
            security = Security(sec_id=system_sec_id, sec_id_source=SecurityIdSource.TICKER)
            # query chore
            chore_brief = ChoreBrief(chore_id=chore_id, security=security, side=side, qty=qty,
                                     underlying_account=underlying_account)
            msg = f"SIM:LAPSE for {bartering_sec_id}/{system_sec_id}, chore_id {chore_id} and side {side}, {qty=}"
            add_to_texts(chore_brief, msg)
            chore_ledger = ChoreLedger(chore=chore_brief, chore_event_date_time=DateTime.utcnow(),
                                         chore_event=ChoreEventType.OE_LAPSE)
            await BarterSimulator.chore_create_async_callable(chore_ledger)

    @classmethod
    async def is_kill_switch_enabled(cls) -> bool:
        logging.info("Called BarteringLink.is_kill_switch_enabled from BarterSimulator")
        return False

    @classmethod
    async def trigger_kill_switch(cls) -> bool:
        logging.critical("Called BarteringLink.trigger_kill_switch from BarterSimulator")
        return True

    @classmethod
    async def revoke_kill_switch_n_resume_bartering(cls) -> bool:
        logging.critical("Called BarteringLink.revoke_kill_switch_n_resume_bartering from BarterSimulator")
        return True

    @classmethod
    async def place_amend_chore(cls, chore_id: str, px: float | None = None, qty: int | None = None,
                                bartering_sec_id: str | None = None, system_sec_id: str | None = None,
                                bartering_sec_type: str | None = None) -> bool:
        raise NotImplementedError

    @classmethod
    async def is_chore_open(cls, chore_id: str) -> bool:
        raise NotImplementedError

    @classmethod
    async def get_chore_status(cls, chore_id: str) -> Tuple[ChoreStatusType | None, str | None, int | None, float | None, int | None] | None:
        """
        returns chore_status (ChoreStatusType), any_chore_text, filled-Qty, chore-px and chore-qty as seen by bartering
        link, caller may use these for reconciliation
        returns None if chore not found by Bartering Link
        """
        raise NotImplementedError
