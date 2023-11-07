import logging
from typing import List
from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import Side
from Flux.CodeGenProjects.strat_executor.app.trading_link_base import TradingLinkBase


log_simulate_logger = logging.getLogger("log_simulator")


class LogTradeSimulator(TradingLinkBase):
    fld_sep: str = "~~"
    val_sep: str = "^^"
    """
    Class to log trading link events that needs to be simulated by underlying true simulator
    This helps improve simulator by aligning the process more closely with async trading links
    """
    @classmethod
    def trigger_kill_switch(cls) -> bool:
        log_simulate_logger.info("$$$trigger_kill_switch")
        return True

    @classmethod
    def revoke_kill_switch_n_resume_trading(cls) -> bool:
        log_simulate_logger.info("$$$revoke_kill_switch_n_resume_trading")
        return True

    @classmethod
    async def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                              account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        exchange_str: str = f"{cls.fld_sep}exchange{cls.val_sep}{exchange}" if exchange else ""
        if text:
            logging.error(f"logit_simulator does not support list arguments, found: {text} for order: "
                          f"px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}{cls.fld_sep}side{cls.val_sep}{side}"
                          f"{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}{cls.fld_sep}system_sec_id: "
                          f"{system_sec_id}{cls.fld_sep}account{cls.val_sep}{account}{exchange_str}")
        log_simulate_logger.info(f"$$$trade_simulator_place_new_order_query_client{cls.fld_sep}{cls.executor_host}{cls.fld_sep}"
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
        log_simulate_logger.info(f"$$$trade_simulator_place_cxl_order_query_client{cls.fld_sep}{cls.executor_host}{cls.fld_sep}"
                     f"{cls.executor_port}{cls.fld_sep}order_id{cls.val_sep}{order_id}{side_str}{trading_sec_id_str}"
                     f"{system_sec_id_str}"
                     f"{underlying_account_str}")
        return True
