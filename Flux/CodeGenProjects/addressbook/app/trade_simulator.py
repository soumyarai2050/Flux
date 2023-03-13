import logging
from typing import ClassVar, List
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel, PortfolioStatusBaseModel
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase, add_to_texts


class TradeSimulator(TradingLinkBase):
    order_id_counter: ClassVar[int] = 0
    fill_id_counter: ClassVar[int] = 0
    simulate_reverse_path: ClassVar[bool | None] = TradingLinkBase.config_dict.get("simulate_reverse_path") if TradingLinkBase.config_dict is not None else None

    def __init__(self):
        pass

    @classmethod
    def place_new_order(cls, px: float, qty: int, side: Side, sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None):
        cls.order_id_counter += 1
        order_id: str = f"O{cls.order_id_counter}"
        security = Security(sec_id=sec_id)

        order_brief = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                 underlying_account=account)
        msg = f"SIM: Ordering {sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief, msg)

        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_NEW)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)
        if cls.simulate_reverse_path:
            cls.process_order_ack(order_id, px, qty, side, sec_id, account)
        return True  # indicates order send success (send false otherwise)

    @classmethod
    def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None):
        """simulate order's Ack """
        security = Security(sec_id=sec_id)
        order_brief_obj = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                     underlying_account=underlying_account)
        msg = f"SIM: ACK received for {sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief_obj, msg)

        # simulate ack
        order_journal_obj = OrderJournalBaseModel(order=order_brief_obj,
                                                  order_event_date_time=DateTime.utcnow(),
                                                  order_event=OrderEventType.OE_ACK)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal_obj)
        if cls.simulate_reverse_path:
            cls.process_fill(order_id, px, qty, side, sec_id, underlying_account)

    @classmethod
    def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """Simulates Order's fills"""

        # simulate fill
        fill_journal = FillsJournalBaseModel(order_id=order_id, fill_px=px, fill_qty=qty,
                                             underlying_account=underlying_account,
                                             fill_date_time=DateTime.utcnow(),
                                             fill_id=f"F{order_id[1:]}")
        TradeSimulator.strat_manager_service_web_client.create_fills_journal_client(fill_journal)

    @classmethod
    def place_cxl_order(cls, order_id: str, side: Side | None = None, sec_id: str | None = None,
                        underlying_account: str | None = "Acc1"):
        """
        cls.simulate_reverse_path or not - always simulate cancel order's Ack
        """
        security = Security(sec_id=sec_id)
        # query order
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        msg = f"SIM:Cancel Ack {sec_id}, order_id {order_id} and side {side}"
        add_to_texts(order_brief, msg)
        # simulate cancel ack
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_CXL_ACK)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    def trigger_kill_switch(cls):
        portfolio_status_id = 1
        portfolio_status = \
            TradeSimulator.strat_manager_service_web_client.get_portfolio_status_client(portfolio_status_id)

        if not portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = True
            TradeSimulator.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
            logging.debug("Portfolio_status - Kill Switch turned to True")
        else:
            logging.error("Portfolio_status - Kill Switch is already True")

    @classmethod
    def revoke_kill_switch_n_resume_trading(cls):
        portfolio_status_id = 1
        portfolio_status = \
            TradeSimulator.strat_manager_service_web_client.get_portfolio_status_client(portfolio_status_id)

        if portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = False
            TradeSimulator.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
            logging.debug("Portfolio_status - Kill Switch turned to False")
        else:
            logging.error("Portfolio_status - Kill Switch is already False")
