import logging
from typing import ClassVar, List
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel, PortfolioStatusBaseModel
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase, add_to_texts


class TradeSimulator(TradingLinkBase):
    buy_order_counter: ClassVar[int] = 0
    sell_order_counter: ClassVar[int] = 0
    buy_rej_counter: ClassVar[int] = 0
    sell_rej_counter: ClassVar[int] = 0
    simulate_reverse_path: ClassVar[bool | None] = TradingLinkBase.config_dict.get("simulate_reverse_path") if TradingLinkBase.config_dict is not None else None
    simulate_new_to_reject_orders: ClassVar[bool | None] = TradingLinkBase.config_dict.get("simulate_new_to_reject_orders") if TradingLinkBase.config_dict is not None else None
    simulate_ack_to_reject_orders: ClassVar[bool | None] = TradingLinkBase.config_dict.get("simulate_ack_to_reject_orders") if TradingLinkBase.config_dict is not None else None
    simulate_cxl_rej_orders: ClassVar[bool | None] = TradingLinkBase.config_dict.get("simulate_cxl_rej_orders") if TradingLinkBase.config_dict is not None else None
    fill_percent: ClassVar[int | None] = TradingLinkBase.config_dict.get("fill_percent") if TradingLinkBase.config_dict is not None else None
    continues_buy_count: ClassVar[int | None] = TradingLinkBase.config_dict.get("continues_buy_count") if TradingLinkBase.config_dict is not None else None
    continues_buy_rej_count: ClassVar[int | None] = TradingLinkBase.config_dict.get("continues_buy_rej_count") if TradingLinkBase.config_dict is not None else None
    continues_sell_count: ClassVar[int | None] = TradingLinkBase.config_dict.get("continues_sell_count") if TradingLinkBase.config_dict is not None else None
    continues_sell_rej_count: ClassVar[int | None] = TradingLinkBase.config_dict.get("continues_sell_rej_count") if TradingLinkBase.config_dict is not None else None

    def __init__(self):
        pass

    @classmethod
    def check_do_reject(cls, side: Side):
        if side == Side.BUY:
            if cls.continues_buy_count is not None and cls.continues_buy_rej_count is not None:
                if cls.buy_order_counter < cls.continues_buy_count:
                    cls.buy_order_counter += 1
                    return False
                else:
                    if cls.buy_rej_counter < cls.continues_buy_rej_count:
                        cls.buy_rej_counter += 1
                        return True
                    else:
                        cls.buy_order_counter = 1
                        cls.buy_rej_counter = 0
                        return False
            else:
                return False
        else:
            if cls.continues_sell_count is not None and cls.continues_sell_rej_count is not None:
                if cls.sell_order_counter < cls.continues_sell_count:
                    cls.sell_order_counter += 1
                    return False
                else:
                    if cls.sell_rej_counter < cls.continues_sell_rej_count:
                        cls.sell_rej_counter += 1
                        return True
                    else:
                        cls.sell_order_counter = 1
                        cls.sell_rej_counter = 0
                        return False
            else:
                return False

    @classmethod
    def process_order_reject(cls, order_brief: OrderBrief):
        create_date_time = DateTime.utcnow()
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=create_date_time,
                                              order_event=OrderEventType.OE_REJ)
        msg = f"SIM:Order REJ for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None):
        create_date_time = DateTime.utcnow()
        order_id: str = f"{trading_sec_id}-{create_date_time}"
        security = Security(sec_id=system_sec_id)  # use system_sec_id to create system's internal order brief / journal

        order_brief = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                 underlying_account=account)
        msg = f"SIM: Ordering {trading_sec_id}/{system_sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief, msg)

        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=create_date_time,
                                              order_event=OrderEventType.OE_NEW)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)
        if cls.simulate_reverse_path:
            if cls.simulate_new_to_reject_orders and cls.check_do_reject(side):
                cls.process_order_reject(order_brief)
            else:
                cls.process_order_ack(order_id, px, qty, side, system_sec_id, account)
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
            if cls.simulate_ack_to_reject_orders and cls.check_do_reject(side):
                cls.process_order_reject(order_brief_obj)
            else:
                cls.process_fill(order_id, px, qty, side, sec_id, underlying_account)

    @classmethod
    def get_partial_allowed_fill_qty(cls, qty: int):
        qty = int((cls.fill_percent / 100) * qty)
        return qty

    @classmethod
    def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """Simulates Order's fills"""

        # simulate fill
        if cls.fill_percent:
            qty = cls.get_partial_allowed_fill_qty(qty)
        fill_journal = FillsJournalBaseModel(order_id=order_id, fill_px=px, fill_qty=qty,
                                             underlying_account=underlying_account,
                                             fill_date_time=DateTime.utcnow(),
                                             fill_id=f"F{order_id[1:]}")
        TradeSimulator.strat_manager_service_web_client.create_fills_journal_client(fill_journal)

    @classmethod
    def process_cxl_rej(cls, order_brief: OrderBrief):
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_CXL_REJ)
        msg = f"SIM:Cancel REJ for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    def process_cxl_ack(cls, order_brief: OrderBrief):
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_CXL_ACK)
        msg = f"SIM:Cancel ACK for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

    @classmethod
    def place_cxl_order(cls, order_id: str, side: Side | None = None, sec_id: str | None = None,
                        underlying_account: str | None = "trading-account"):
        """
        cls.simulate_reverse_path or not - always simulate cancel order's Ack
        """
        security = Security(sec_id=sec_id)
        # query order
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        msg = f"SIM:Cancel Request for {sec_id}, order_id {order_id} and side {side}"
        add_to_texts(order_brief, msg)
        # simulate cancel ack
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_CXL)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

        if cls.simulate_cxl_rej_orders and cls.check_do_reject(side):
            cls.process_cxl_rej(order_brief)
        else:
            cls.process_cxl_ack(order_brief)

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
