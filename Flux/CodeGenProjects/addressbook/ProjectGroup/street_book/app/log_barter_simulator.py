# standard imports
import logging
from typing import List

# project imports
from Flux.CodeGenProjects.AddressBook.ProjectGroup.phone_book.generated.Pydentic.email_book_service_model_imports import Side
from Flux.CodeGenProjects.AddressBook.ProjectGroup.street_book.app.bartering_link_base import BarteringLinkBase
from Flux.CodeGenProjects.AddressBook.ProjectGroup.log_book.app.log_book_service_helper import (
    get_field_seperator_pattern, get_key_val_seperator_pattern, get_pattern_for_log_simulator)


log_simulate_logger = logging.getLogger("log_simulator")


class LogBarterSimulator(BarteringLinkBase):
    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_simulator_pattern: str = get_pattern_for_log_simulator()
    """
    Class to log bartering link events that needs to be simulated by underlying true simulator
    This helps improve simulator by aligning the process more closely with async bartering links
    """

    @classmethod
    async def is_kill_switch_enabled(cls) -> bool:
        logging.info("Called BarteringLink.is_kill_switch_enabled from LogBarterSimulator")
        is_kill_switch_enabled = cls.portfolio_config_dict.get("is_kill_switch_enabled")
        if is_kill_switch_enabled is None:
            return False
        else:
            return is_kill_switch_enabled

    @classmethod
    async def trigger_kill_switch(cls) -> bool:
        logging.critical("Called BarteringLink.trigger_kill_switch from LogBarterSimulator")
        trigger_kill_switch = cls.portfolio_config_dict.get("trigger_kill_switch")
        if trigger_kill_switch is None:
            return True
        else:
            return trigger_kill_switch

    @classmethod
    async def revoke_kill_switch_n_resume_bartering(cls) -> bool:
        logging.critical("Called BarteringLink.revoke_kill_switch_n_resume_bartering from LogBarterSimulator")
        revoke_kill_switch_n_resume_bartering = cls.portfolio_config_dict.get("revoke_kill_switch_n_resume_bartering")
        if revoke_kill_switch_n_resume_bartering is None:
            return True
        else:
            return revoke_kill_switch_n_resume_bartering

    @classmethod
    async def place_new_chore(cls, px: float, qty: int, side: Side, bartering_sec_id: str, system_sec_id: str,
                              account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        if LogBarterSimulator.chore_create_async_callable:
            exchange_str: str = f"{cls.fld_sep}exchange{cls.val_sep}{exchange}" if exchange else ""
            if text:
                logging.error(f"logit_simulator does not support list arguments, found: {text} for chore: "
                              f"px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}{cls.fld_sep}side{cls.val_sep}"
                              f"{side.value}{cls.fld_sep}bartering_sec_id{cls.val_sep}{bartering_sec_id}{cls.fld_sep}"
                              f"system_sec_id: {system_sec_id}{cls.fld_sep}account{cls.val_sep}{account}{exchange_str}")
            log_simulate_logger.info(
                f"{LogBarterSimulator.log_simulator_pattern}barter_simulator_place_new_chore_query_client{cls.fld_sep}"
                f"{cls.executor_host}{cls.fld_sep}"
                f"{cls.executor_port}{cls.fld_sep}px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}"
                f"{cls.fld_sep}side{cls.val_sep}{side.value}{cls.fld_sep}bartering_sec_id{cls.val_sep}{bartering_sec_id}"
                f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}{cls.fld_sep}underlying_account"
                f"{cls.val_sep}{account}{exchange_str}")
        return True

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
