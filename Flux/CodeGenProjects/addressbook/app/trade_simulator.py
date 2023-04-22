import logging
from typing import ClassVar, List, Dict
from pendulum import DateTime

from Flux.CodeGenProjects.addressbook.generated.strat_manager_service_model_imports import Security, \
    OrderBrief, OrderJournalBaseModel, Side, OrderEventType, FillsJournalBaseModel, PortfolioStatusBaseModel
from Flux.CodeGenProjects.addressbook.app.trading_link_base import TradingLinkBase, add_to_texts


class TradeSimulator(TradingLinkBase):
    continuous_symbol_based_orders_counter: ClassVar[Dict | None] = {}
    cxl_rej_symbol_to_bool_dict: ClassVar[Dict | None] = {}
    symbol_configs: ClassVar[Dict | None] = TradingLinkBase.config_dict.get("symbol_configs") if TradingLinkBase.config_dict is not None else None

    @classmethod
    def reload_configs(cls):
        cls.symbol_configs: ClassVar[Dict | None] = TradingLinkBase.config_dict.get("symbol_configs") \
            if TradingLinkBase.config_dict is not None else None

    def __init__(self):
        pass

    @classmethod
    def is_special_order(cls, symbol: str) -> bool:

        if symbol not in cls.continuous_symbol_based_orders_counter:
            symbol_configs = cls.get_symbol_configs(symbol)
            continuous_order_count = fetched_continuous_order_count \
                if (fetched_continuous_order_count := symbol_configs.get("continues_order_count")) is not None else 1
            continues_special_order_count = fetched_continues_special_order_count \
                if (fetched_continues_special_order_count := symbol_configs.get("continues_special_order_count")) is not None else 0

            cls.continuous_symbol_based_orders_counter[symbol] = {
                "order_counter": 0,
                "continues_order_count": continuous_order_count,
                "special_order_counter": 0,
                "continues_special_order_count": continues_special_order_count
            }

        if cls.continuous_symbol_based_orders_counter[symbol]["order_counter"] < \
                cls.continuous_symbol_based_orders_counter[symbol]["continues_order_count"]:
            cls.continuous_symbol_based_orders_counter[symbol]["order_counter"] += 1
            return False
        else:
            if cls.continuous_symbol_based_orders_counter[symbol]["special_order_counter"] < \
                    cls.continuous_symbol_based_orders_counter[symbol]["continues_special_order_count"]:
                cls.continuous_symbol_based_orders_counter[symbol]["special_order_counter"] += 1
                return True
            else:
                cls.continuous_symbol_based_orders_counter[symbol]["order_counter"] = 1
                cls.continuous_symbol_based_orders_counter[symbol]["special_order_counter"] = 0
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
    def get_symbol_configs(cls, symbol: str) -> Dict | None:
        if cls.symbol_configs is not None:
            return cls.symbol_configs.get(symbol)
        return None

    @classmethod
    def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                        account: str, exchange: str | None = None, text: List[str] | None = None):
        """
        when invoked form log analyzer - all params are passed as strings
        pydantic default conversion handles conversion - any util functions called should be called with
        explicit type convertors or pydantic object converted values
        """
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

        symbol_configs = cls.get_symbol_configs(system_sec_id)
        if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
            if symbol_configs.get("simulate_new_to_reject_orders") and cls.is_special_order(system_sec_id):
                cls.process_order_reject(order_brief)
            elif symbol_configs.get("simulate_new_unsolicited_cxl_orders") and cls.is_special_order(system_sec_id):
                cls.process_cxl_ack(order_brief)
            else:
                cls.process_order_ack(order_id, order_brief.px, order_brief.qty, order_brief.side, system_sec_id,
                                      account)
        return True  # indicates order send success (send false otherwise)

    @classmethod
    def get_partial_allowed_ack_qty(cls, symbol: str, qty: int):
        symbol_configs = cls.get_symbol_configs(symbol)

        if symbol_configs is not None:
            if (ack_percent := symbol_configs.get("ack_percent")) is not None:
                qty = int((ack_percent / 100) * qty)
        return qty

    @classmethod
    def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                          text: List[str] | None = None):
        """simulate order's Ack """
        security = Security(sec_id=sec_id)

        qty = cls.get_partial_allowed_ack_qty(sec_id, qty)
        order_brief_obj = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                     underlying_account=underlying_account)
        msg = f"SIM: ACK received for {sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief_obj, msg)

        # simulate ack
        order_journal_obj = OrderJournalBaseModel(order=order_brief_obj,
                                                  order_event_date_time=DateTime.utcnow(),
                                                  order_event=OrderEventType.OE_ACK)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal_obj)

        symbol_configs = cls.get_symbol_configs(sec_id)
        if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
            if symbol_configs.get("simulate_ack_to_reject_orders") and cls.is_special_order(sec_id):
                cls.process_order_reject(order_brief_obj)
            elif symbol_configs.get("simulate_ack_unsolicited_cxl_orders") and cls.is_special_order(sec_id):
                cls.process_cxl_ack(order_brief_obj)
            else:
                cls.process_fill(order_id, px, qty, side, sec_id, underlying_account)
                if symbol_configs.get("simulate_cxl_rej_orders") and cls.is_special_order(sec_id):
                    cls.cxl_rej_symbol_to_bool_dict[sec_id] = True
                    cls.place_cxl_order(order_id, side, sec_id, sec_id, underlying_account)

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
    def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """Simulates Order's fills"""

        symbol_configs = cls.get_symbol_configs(sec_id)
        if symbol_configs is not None:
            if (total_fill_count := symbol_configs.get("total_fill_count")) is None:
                total_fill_count = 1
        else:
            total_fill_count = 1

        qty = cls.get_partial_allowed_fill_qty(sec_id, qty)
        for fill_count in range(total_fill_count):
            fill_journal = FillsJournalBaseModel(order_id=order_id, fill_px=px, fill_qty=qty, fill_symbol=sec_id,
                                                 fill_side=side, underlying_account=underlying_account,
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
    def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                        system_sec_id: str | None = None, underlying_account: str | None = "trading-account"):
        """
        cls.simulate_reverse_path or not - always simulate cancel order's Ack/Rejects (unless configured for unack)
        when invoked form log analyzer - all params are passed as strings
        pydantic default conversion handles conversion - any util functions called should be called with
        explicit type convertors or pydantic object converted values
        """
        security = Security(sec_id=system_sec_id)
        # query order
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        msg = f"SIM:Cancel Request for {trading_sec_id}/{system_sec_id}, order_id {order_id} and side {side}"
        add_to_texts(order_brief, msg)
        # simulate cancel ack
        order_journal = OrderJournalBaseModel(order=order_brief,
                                              order_event_date_time=DateTime.utcnow(),
                                              order_event=OrderEventType.OE_CXL)
        TradeSimulator.strat_manager_service_web_client.create_order_journal_client(order_journal)

        if system_sec_id in cls.cxl_rej_symbol_to_bool_dict and cls.cxl_rej_symbol_to_bool_dict.get(system_sec_id):
            cls.cxl_rej_symbol_to_bool_dict[system_sec_id] = False
            cls.process_cxl_rej(order_brief)
        else:
            cls.process_cxl_ack(order_brief)

    @classmethod
    def trigger_kill_switch(cls) -> bool:
        portfolio_status_id = 1
        portfolio_status = \
            TradeSimulator.strat_manager_service_web_client.get_portfolio_status_client(portfolio_status_id)

        if not portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = True
            TradeSimulator.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
            logging.debug("Portfolio_status - Kill Switch turned to True")
            return True
        else:
            logging.error("Portfolio_status - Kill Switch is already True")
            return False

    @classmethod
    def revoke_kill_switch_n_resume_trading(cls) -> bool:
        portfolio_status_id = 1
        portfolio_status = \
            TradeSimulator.strat_manager_service_web_client.get_portfolio_status_client(portfolio_status_id)

        if portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = False
            TradeSimulator.strat_manager_service_web_client.patch_portfolio_status_client(portfolio_status_basemodel)
            logging.debug("Portfolio_status - Kill Switch turned to False")
            return True
        else:
            logging.error("Portfolio_status - Kill Switch is already False")
            return False
