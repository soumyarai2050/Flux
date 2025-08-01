# standard imports
import logging
from typing import List, Dict, ClassVar, Tuple
import os
from pathlib import PurePath

from filelock import FileLock
from pendulum import DateTime

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.ORMModel.email_book_service_model_imports import (
    Side, Position, PositionType, InstrumentType)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.bartering_link_base import BarteringLinkBase
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.executor_config_loader import (
    executor_config_yaml_dict, EXECUTOR_PROJECT_DATA_DIR)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    get_field_seperator_pattern, get_key_val_seperator_pattern, get_pattern_for_log_simulator)
from Flux.CodeGenProjects.AddressBook.ProjectGroup.base_book.app.base_book_helper import (
    get_bkr_from_underlying_account)
from FluxPythonUtils.scripts.file_utility_functions import dict_or_list_records_csv_reader
from FluxPythonUtils.scripts.general_utility_functions import transform_to_str
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.app.static_data import SecurityRecordManager
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_basket_book_core_msgspec_model import *
from Flux.CodeGenProjects.AddressBook.ORMModel.street_book_n_post_book_n_basket_book_core_msgspec_model import *


log_simulate_logger = logging.getLogger("log_simulator")


class DealsLedgerCont(DealsLedgerBaseModel):

    @staticmethod
    def transform(kwargs: Dict):
        field: str
        fields = ["fill_symbol"]
        for field in fields:
            v = kwargs.get(field)
            kwargs[field] = transform_to_str(v)

    @classmethod
    def from_kwargs(cls, **kwargs):
        cls.transform(kwargs)
        deals_ledger_cont = super().from_kwargs(**kwargs)
        return deals_ledger_cont

    @classmethod
    def from_dict_list(cls, args_dict_list: List[Dict], **kwargs):
        args_dict: Dict
        for args_dict in args_dict_list:
            cls.transform(args_dict)
        deals_ledger_cont_list = super().from_dict_list(args_dict_list, **kwargs)
        return deals_ledger_cont_list


class LogBarterSimulator(BarteringLinkBase):
    int_id: ClassVar[int] = 1
    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_simulator_pattern: str = get_pattern_for_log_simulator()
    intraday_bartering_chores_csv_file_name: str = f"intraday_bartering_chores_{DateTime.now().strftime('%Y%m%d')}"
    intraday_bartering_chores_lock_file_name: str = f"intraday_bartering_chores.lock"
    intraday_bartering_chores_csv_file: PurePath = EXECUTOR_PROJECT_DATA_DIR / intraday_bartering_chores_csv_file_name
    intraday_bartering_chores_lock_file: PurePath = EXECUTOR_PROJECT_DATA_DIR / intraday_bartering_chores_lock_file_name
    static_data: SecurityRecordManager = SecurityRecordManager.get_loaded_instance(from_cache=True)
    """
    Class to log bartering link events that needs to be simulated by underlying true simulator
    This helps improve simulator by aligning the process more closely with async bartering links
    """

    def __init__(self):
        super(LogBarterSimulator, self).__init__(executor_config_yaml_dict.get("inst_id"))

    @classmethod
    async def recover_cache(cls, **kwargs):
        pass

    @classmethod
    def load_positions_by_symbols_dict(cls, symbol_type_dict: Dict[str, str]):
        symbol_list: List[str] = [symbol for symbol in symbol_type_dict]
        broker_sec_pos_dict: Dict[str, Dict[str, List[Position]]] = {}

        if not os.path.exists(f"{str(cls.intraday_bartering_chores_csv_file)}.csv"):
            logging.warning("No positions found in barter simulator")
            return broker_sec_pos_dict

        with FileLock(str(cls.intraday_bartering_chores_lock_file)):
            intraday_chore_deals: List[DealsLedgerCont] = dict_or_list_records_csv_reader(  # noqa
                cls.intraday_bartering_chores_csv_file_name, DealsLedgerCont, EXECUTOR_PROJECT_DATA_DIR)

            if not intraday_chore_deals:
                logging.warning("No positions found in barter simulator")
                return broker_sec_pos_dict

            chore_fill: DealsLedgerCont
            for chore_fill in intraday_chore_deals:
                ticker: str = chore_fill.fill_symbol
                inst_type: InstrumentType
                sec_id: str
                if cls.static_data.is_cb_ticker(ticker):
                    inst_type = InstrumentType.CB
                    sec_id = cls.static_data.get_sedol_from_ticker(ticker)
                else:
                    inst_type = InstrumentType.EQT
                    sec_id, _ = cls.static_data.get_connect_n_qfii_rics_from_ticker(ticker)

                if sec_id not in symbol_list:
                    continue

                broker: str = get_bkr_from_underlying_account(chore_fill.underlying_account, inst_type)
                if broker not in broker_sec_pos_dict:
                    broker_sec_pos_dict[broker] = {}

                sec_pos_dict: Dict[str, List[Position]] = broker_sec_pos_dict[broker]

                if sec_id not in sec_pos_dict:
                    sec_pos_dict[sec_id] = []

                bot_size: int = chore_fill.fill_qty if chore_fill.fill_side == Side.BUY else 0
                sld_size: int = chore_fill.fill_qty if chore_fill.fill_side == Side.SELL else 0
                positions: List[Position] = sec_pos_dict[sec_id]
                position: Position
                if not positions:
                    position = Position(type=PositionType.SOD, allocated_size=0, available_size=0,
                                        consumed_size=chore_fill.fill_qty, bot_size=bot_size, sld_size=sld_size)
                    positions.append(position)
                else:
                    position = positions[0]
                    position.consumed_size += chore_fill.fill_qty
                    position.bot_size += bot_size
                    position.sld_size += sld_size
            logging.info(f"Loaded sod {broker_sec_pos_dict=}")
            return broker_sec_pos_dict

    @classmethod
    async def is_kill_switch_enabled(cls) -> bool:
        logging.info("Called BarteringLink.is_kill_switch_enabled from LogBarterSimulator")
        is_kill_switch_enabled = cls.contact_config_dict.get("is_kill_switch_enabled")
        if is_kill_switch_enabled is None:
            return False
        else:
            return is_kill_switch_enabled

    @classmethod
    async def trigger_kill_switch(cls) -> bool:
        logging.critical("Called BarteringLink.trigger_kill_switch from LogBarterSimulator")
        trigger_kill_switch = cls.contact_config_dict.get("trigger_kill_switch")
        if trigger_kill_switch is None:
            return True
        else:
            return trigger_kill_switch

    @classmethod
    async def revoke_kill_switch_n_resume_bartering(cls) -> bool:
        logging.critical("Called BarteringLink.revoke_kill_switch_n_resume_bartering from LogBarterSimulator")
        revoke_kill_switch_n_resume_bartering = cls.contact_config_dict.get("revoke_kill_switch_n_resume_bartering")
        if revoke_kill_switch_n_resume_bartering is None:
            return True
        else:
            return revoke_kill_switch_n_resume_bartering

    @classmethod
    async def place_new_chore(cls, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
                              bartering_sec_type: str, account: str, exchange: str | None = None, text: List[str] | None = None,
                              client_ord_id: str | None = None, **kwargs) -> Tuple[bool, str]:
        """
        return bool indicating success/fail and unique-id-str/err-description in second param
        """
        if LogBarterSimulator.chore_create_async_callable:
            exchange_str: str = f"{cls.fld_sep}exchange{cls.val_sep}{exchange}" if exchange else ""
            if text:
                logging.error(f"logit_simulator does not support list arguments, found: {text} for chore: "
                              f"px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}{cls.fld_sep}side{cls.val_sep}"
                              f"{side.value}{cls.fld_sep}bartering_sec_id{cls.val_sep}{bartering_sec_id}{cls.fld_sep}"
                              f"system_sec_id: {system_sec_id}{cls.fld_sep}bartering_sec_type: {bartering_sec_type}"
                              f"{cls.fld_sep}account{cls.val_sep}{account}{exchange_str}"
                              f"{cls.fld_sep}client_ord_id{cls.val_sep}{client_ord_id}")
            log_simulate_logger.info(
                f"{LogBarterSimulator.log_simulator_pattern}barter_simulator_place_new_chore_query_client{cls.fld_sep}"
                f"{cls.executor_host}{cls.fld_sep}"
                f"{cls.executor_port}{cls.fld_sep}px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}"
                f"{cls.fld_sep}side{cls.val_sep}{side.value}{cls.fld_sep}bartering_sec_id{cls.val_sep}{bartering_sec_id}"
                f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}{cls.fld_sep}"
                f"bartering_sec_type{cls.val_sep}{bartering_sec_type}{cls.fld_sep}account"
                f"{cls.val_sep}{account}{exchange_str}{cls.fld_sep}client_ord_id{cls.val_sep}{client_ord_id}")
        cls.int_id += 1
        sync_check = kwargs.get("sync_check")
        if sync_check:
            return True, f"placed_new_chore---{cls.int_id}"
        else:
            return True, str(cls.int_id)

    @classmethod
    async def place_cxl_chore(cls, chore_id: str, side: Side | None = None, bartering_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = None):
        if LogBarterSimulator.chore_create_async_callable:
            side_str: str = f"{cls.fld_sep}side{cls.val_sep}{side.value}" if side else ""
            bartering_sec_id_str: str = f"{cls.fld_sep}bartering_sec_id{cls.val_sep}{bartering_sec_id}" if bartering_sec_id else ""
            system_sec_id_str: str = f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}" if system_sec_id else ""
            underlying_account_str: str = \
                f"{cls.fld_sep}underlying_account{cls.val_sep}{underlying_account}" if underlying_account else ""
            log_simulate_logger.info(
                f"{LogBarterSimulator.log_simulator_pattern}barter_simulator_place_cxl_chore_query_client"
                f"{cls.fld_sep}{cls.executor_host}{cls.fld_sep}"
                f"{cls.executor_port}{cls.fld_sep}chore_id{cls.val_sep}{chore_id}{side_str}{bartering_sec_id_str}"
                f"{system_sec_id_str}"
                f"{underlying_account_str}")
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
        return None if chore not found by Bartering Link
        """
        raise NotImplementedError
