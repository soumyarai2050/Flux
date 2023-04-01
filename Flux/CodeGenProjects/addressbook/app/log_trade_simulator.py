import logging
from abc import ABC
from typing import List
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Side
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase


class LogTradeSimulator(TradingLinkBase):
    fld_sep: str = "~~"
    val_sep: str = "^^"
    """
    Class to log trading link events that needs to be simulated by underlying true simulator
    This helps improve simulator by aligning the process more closely with async trading links
    """
    @classmethod
    def trigger_kill_switch(cls) -> bool:
        logging.info("$$$trigger_kill_switch")
        return True

    @classmethod
    def revoke_kill_switch_n_resume_trading(cls) -> bool:
        logging.info("$$$revoke_kill_switch_n_resume_trading")
        return True

    @classmethod
    def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None) -> bool:
        exchange_str: str = f"{cls.fld_sep}exchange{cls.val_sep}{exchange}" if exchange else ""
        if text:
            logging.error(f"logit_simulator does not support list arguments, found: {text} for order: "
                          f"px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}{cls.fld_sep}side{cls.val_sep}{side}"
                          f"{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}{cls.fld_sep}system_sec_id: "
                          f"{system_sec_id}{cls.fld_sep}account{cls.val_sep}{account}{exchange_str}")
        logging.info(f"$$$place_new_order{cls.fld_sep}px{cls.val_sep}{px}{cls.fld_sep}qty{cls.val_sep}{qty}"
                     f"{cls.fld_sep}side{cls.val_sep}{side}{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}"
                     f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}{cls.fld_sep}account{cls.val_sep}"
                     f"{account}{exchange_str}")
        return True

    @classmethod
    def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                        system_sec_id: str | None = None, underlying_account: str | None = None):
        side_str: str = f"{cls.fld_sep}side{cls.val_sep}{side}" if side else ""
        trading_sec_id_str: str = f"{cls.fld_sep}trading_sec_id{cls.val_sep}{trading_sec_id}" if trading_sec_id else ""
        system_sec_id_str: str = f"{cls.fld_sep}system_sec_id{cls.val_sep}{system_sec_id}" if system_sec_id else ""
        underlying_account_str: str = \
            f"{cls.fld_sep}underlying_account{cls.val_sep}{underlying_account}" if underlying_account else ""
        logging.info(f"$$$place_cxl_order{cls.fld_sep}order_id{cls.val_sep}{order_id}{side_str}{trading_sec_id_str}"
                     f"{system_sec_id_str}"
                     f"{underlying_account_str}")
        return True
