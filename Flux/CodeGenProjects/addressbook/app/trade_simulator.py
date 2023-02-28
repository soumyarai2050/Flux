import logging
from typing import ClassVar, List
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel
from Flux.CodeGenProjects.market_data.generated.market_data_service_web_client import MarketDataServiceWebClient
from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_web_client import \
    StratManagerServiceWebClient


def add_to_texts(order_brief: OrderBrief, msg: str):
    if order_brief.text is None:
        order_brief.text = [msg]
    else:
        order_brief.text.append(msg)


class TradeSimulator:
    strat_manager_service_web_client: ClassVar[StratManagerServiceWebClient] = StratManagerServiceWebClient()
    market_data_service_web_client: ClassVar[MarketDataServiceWebClient] = MarketDataServiceWebClient()
    order_id_counter: ClassVar[int] = 0
    fill_id_counter: ClassVar[int] = 0

    def __init__(self):
        pass

    @classmethod
    def place_new_order(cls, px: float, qty: int, side: Side, sec_id: str,
                        underlying_account: str, text: List[str] | None = None):
        cls.order_id_counter += 1
        order_id: str = f"O{cls.order_id_counter}"
        security = Security(sec_id=sec_id)

        order_brief = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                 underlying_account=underlying_account)
        msg = f"SIM: Ordering {sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief, msg)

        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_NEW)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    def process_order_ack(cls, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None):
        """simulate order's Ack """
        cls.order_id_counter += 1
        order_id = f"O{cls.order_id_counter}"

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

    @classmethod
    def process_fill(cls, px: float, qty: int, underlying_account: str):
        """Simulates Order's fills"""
        order_id = f"O{cls.order_id_counter}"

        # simulate fill
        fill_journal = FillsJournalBaseModel(order_id=order_id, fill_px=px, fill_qty=qty,
                                             underlying_account=underlying_account,
                                             fill_date_time=DateTime.utcnow(),
                                             fill_id=f"F{order_id[1:]}")
        TradeSimulator.strat_manager_service_web_client.create_fills_journal_client(fill_journal)

    @classmethod
    def place_cxl_order(cls, order_id: str, side: Side, sec_id: str, underlying_account: str):
        """simulate cancel order's Ack"""
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

    @staticmethod
    def trigger_kill_switch():
        logging.critical("Kill Switch triggered - not implemented yet")
