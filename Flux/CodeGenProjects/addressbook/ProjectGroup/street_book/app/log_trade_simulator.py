# standard imports
import logging
from typing import List

# project imports
from Flux.CodeGenProjects.addressbook.ProjectGroup.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import Side
from Flux.CodeGenProjects.addressbook.ProjectGroup.street_book.app.trading_link_base import TradingLinkBase
from Flux.CodeGenProjects.addressbook.ProjectGroup.log_analyzer.app.log_analyzer_service_helper import (
    get_field_seperator_pattern, get_key_val_seperator_pattern, get_pattern_for_log_simulator)


log_simulate_logger = logging.getLogger("log_simulator")


class LogTradeSimulator(TradingLinkBase):
    fld_sep: str = get_field_seperator_pattern()
    val_sep: str = get_key_val_seperator_pattern()
    log_simulator_pattern: str = get_pattern_for_log_simulator()
    """
    Class to log trading link events that needs to be simulated by underlying true simulator
    This helps improve simulator by aligning the process more closely with async trading links
    """

    @classmethod
    async def is_kill_switch_enabled(cls) -> bool:
        logging.info("Called TradingLink.is_kill_switch_enabled from LogTradeSimulator")
        is_kill_switch_enabled = cls.portfolio_config_dict.get("is_kill_switch_enabled")
        if is_kill_switch_enabled is None:
            return False
        else:
            return is_kill_switch_enabled

    @classmethod
    async def trigger_kill_switch(cls) -> bool:
        logging.critical("Called TradingLink.trigger_kill_switch from LogTradeSimulator")
        trigger_kill_switch = cls.portfolio_config_dict.get("trigger_kill_switch")
        if trigger_kill_switch is None:
            return True
        else:
            return trigger_kill_switch

    @classmethod
    async def revoke_kill_switch_n_resume_trading(cls) -> bool:
        logging.critical("Called TradingLink.revoke_kill_switch_n_resume_trading from LogTradeSimulator")
        revoke_kill_switch_n_resume_trading = cls.portfolio_config_dict.get("revoke_kill_switch_n_resume_trading")
        if revoke_kill_switch_n_resume_trading is None:
            return True
        else:
            return revoke_kill_switch_n_resume_trading

    @classmethod
    async def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                              account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        exchange_str: str = f"{cls.fld_sep}exchange{cls.val_sep}{exchange}" if exchange else ""
        if text:
            logging.error(f"logit_simulator does not support list arguments, found: {text} for order: "
                          f"px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}{cls.fld_sep}side{cls.val_sep}{side}"
                          f"{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}{cls.fld_sep}system_sec_id: "
                          f"{system_sec_id}{cls.fld_sep}account{cls.val_sep}{account}{exchange_str}")
        log_simulate_logger.info(
            f"{LogTradeSimulator.log_simulator_pattern}trade_simulator_place_new_order_query_client{cls.fld_sep}"
            f"{cls.executor_host}{cls.fld_sep}"
            f"{cls.executor_port}{cls.fld_sep}px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}"
            f"{cls.fld_sep}side{cls.val_sep}{side}{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}"
            f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}{cls.fld_sep}underlying_account"
            f"{cls.val_sep}{account}{exchange_str}")
        return True

    @classmethod
    async def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = None):
        side_str: str = f"{cls.fld_sep}side{cls.val_sep}{side}" if side else ""
        trading_sec_id_str: str = f"{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}" if trading_sec_id else ""
        system_sec_id_str: str = f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}" if system_sec_id else ""
        underlying_account_str: str = \
            f"{cls.fld_sep}underlying_account{cls.val_sep}{underlying_account}" if underlying_account else ""
        log_simulate_logger.info(
            f"{LogTradeSimulator.log_simulator_pattern}trade_simulator_place_cxl_order_query_client"
            f"{cls.fld_sep}{cls.executor_host}{cls.fld_sep}"
            f"{cls.executor_port}{cls.fld_sep}order_id{cls.val_sep}{order_id}{side_str}{trading_sec_id_str}"
            f"{system_sec_id_str}"
            f"{underlying_account_str}")
        return True
