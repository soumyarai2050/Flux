import logging
from typing import ClassVar, List, Dict, Tuple
import re

from pendulum import DateTime
from fastapi.encoders import jsonable_encoder

from Flux.CodeGenProjects.pair_strat_engine.generated.Pydentic.strat_manager_service_model_imports import \
    Security, Side, PortfolioStatusBaseModel, SecurityType
from Flux.CodeGenProjects.strat_executor.generated.Pydentic.strat_executor_service_model_imports import \
    OrderBrief, OrderJournalBaseModel, OrderEventType, FillsJournalBaseModel, OrderJournal, FillsJournal
from Flux.CodeGenProjects.strat_executor.app.trading_link_base import TradingLinkBase, add_to_texts


def init_symbol_configs():
    symbol_configs: Dict | None = TradingLinkBase.executor_config_dict.get("symbol_configs") \
        if TradingLinkBase.executor_config_dict is not None else None
    if symbol_configs:
        regex_symbol_configs: Dict = {re.compile(k, re.IGNORECASE): v for k, v in symbol_configs.items()}
        return regex_symbol_configs


class TradeSimulator(TradingLinkBase):
    continuous_symbol_based_orders_counter: ClassVar[Dict | None] = {}
    cxl_rej_symbol_to_bool_dict: ClassVar[Dict | None] = {}
    symbol_configs: ClassVar[Dict | None] = init_symbol_configs()

    @classmethod
    def reload_symbol_configs(cls):
        # reloading executor configs
        TradingLinkBase.reload_executor_configs()

        cls.symbol_configs = init_symbol_configs()

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
        return None

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
    async def process_order_reject(cls, order_brief: OrderBrief):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)
        create_date_time = DateTime.utcnow()
        order_journal = OrderJournal(order=order_brief,
                                     order_event_date_time=create_date_time,
                                     order_event=OrderEventType.OE_REJ)
        msg = f"SIM:Order REJ for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        await underlying_create_order_journal_http(order_journal)

    @classmethod
    async def place_new_order(cls, px: float, qty: int, side: Side, trading_sec_id: str, system_sec_id: str,
                              account: str, exchange: str | None = None, text: List[str] | None = None):
        """
        when invoked form log analyzer - all params are passed as strings
        pydantic default conversion handles conversion - any util functions called should be called with
        explicit type convertors or pydantic object converted values
        """
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)

        create_date_time = DateTime.utcnow()
        order_id: str = f"{trading_sec_id}-{create_date_time}"
        # use system_sec_id to create system's internal order brief / journal
        security = Security(sec_id=system_sec_id, sec_type=SecurityType.TICKER)

        order_brief = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                 underlying_account=account)
        msg = f"SIM: Ordering {trading_sec_id}/{system_sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief, msg)

        order_journal = OrderJournal(order=order_brief,
                                     order_event_date_time=create_date_time,
                                     order_event=OrderEventType.OE_NEW)
        await underlying_create_order_journal_http(order_journal)

        symbol_configs = cls.get_symbol_configs(system_sec_id)

        if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
            if symbol_configs.get("simulate_new_to_reject_orders") and cls.is_special_order(system_sec_id):
                await cls.process_order_reject(order_brief)
            elif symbol_configs.get("simulate_new_unsolicited_cxl_orders") and cls.is_special_order(system_sec_id):
                await cls.process_cxl_ack(order_brief)
            else:
                await cls.process_order_ack(order_id, order_brief.px, order_brief.qty, order_brief.side, system_sec_id,
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
    def _process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str,
                           text: List[str] | None = None) -> OrderJournal:
        security = Security(sec_id=sec_id, sec_type=SecurityType.TICKER)

        qty = cls.get_partial_allowed_ack_qty(sec_id, qty)
        order_brief_obj = OrderBrief(order_id=order_id, security=security, side=side, px=px, qty=qty,
                                     underlying_account=underlying_account)
        msg = f"SIM: ACK received for {sec_id}, qty {qty} and px {px}"
        add_to_texts(order_brief_obj, msg)

        order_journal_obj = OrderJournal(order=order_brief_obj,
                                         order_event_date_time=DateTime.utcnow(),
                                         order_event=OrderEventType.OE_ACK)
        return order_journal_obj

    @classmethod
    async def _process_order_ack_symbol_specfic_handling(cls, order_journal_obj: OrderJournal):
        symbol_configs = cls.get_symbol_configs(order_journal_obj.order.security.sec_id)
        if symbol_configs is not None and symbol_configs.get("simulate_reverse_path"):
            if (symbol_configs.get("simulate_ack_to_reject_orders") and
                    cls.is_special_order(order_journal_obj.order.security.sec_id)):
                await cls.process_order_reject(order_journal_obj.order)
            elif (symbol_configs.get("simulate_ack_unsolicited_cxl_orders") and
                  cls.is_special_order(order_journal_obj.order.security.sec_id)):
                await cls.process_cxl_ack(order_journal_obj.order)
            else:
                await cls.process_fill(order_journal_obj.order.order_id, order_journal_obj.order.px,
                                       order_journal_obj.order.qty, order_journal_obj.order.side,
                                       order_journal_obj.order.security.sec_id,
                                       order_journal_obj.order.underlying_account)
                if (symbol_configs.get("simulate_cxl_rej_orders") and
                        cls.is_special_order(order_journal_obj.order.security.sec_id)):
                    cls.cxl_rej_symbol_to_bool_dict[order_journal_obj.order.security.sec_id] = True
                    await cls.place_cxl_order(order_journal_obj.order.order_id, order_journal_obj.order.side,
                                              order_journal_obj.order.security.sec_id,
                                              order_journal_obj.order.underlying_account)

    @classmethod
    async def process_order_ack(cls, order_id, px: float, qty: int, side: Side, sec_id: str,
                                underlying_account: str, text: List[str] | None = None):
        """simulate order's Ack """
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)
        order_journal_obj = cls._process_order_ack(order_id, px, qty, side, sec_id, underlying_account, text)
        await underlying_create_order_journal_http(order_journal_obj)
        await cls._process_order_ack_symbol_specfic_handling(order_journal_obj)

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
    async def process_fill(cls, order_id, px: float, qty: int, side: Side, sec_id: str, underlying_account: str):
        """Simulates Order's fills"""
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_fills_journal_http)

        qty, total_fill_count = cls._process_fill(sec_id, qty)

        for fill_count in range(total_fill_count):
            fill_journal = FillsJournal(order_id=order_id, fill_px=px, fill_qty=qty, fill_symbol=sec_id,
                                        fill_side=side, underlying_account=underlying_account,
                                        fill_date_time=DateTime.utcnow(),
                                        fill_id=f"F{order_id[1:]}")
            await underlying_create_fills_journal_http(fill_journal)

    @classmethod
    async def process_cxl_rej(cls, order_brief: OrderBrief):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)
        order_journal = OrderJournal(order=order_brief, order_event_date_time=DateTime.utcnow(),
                                     order_event=OrderEventType.OE_CXL_REJ)
        msg = f"SIM:Cancel REJ for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        await underlying_create_order_journal_http(order_journal)

    @classmethod
    async def process_cxl_ack(cls, order_brief: OrderBrief):
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)
        order_journal = OrderJournal(order=order_brief,
                                     order_event_date_time=DateTime.utcnow(),
                                     order_event=OrderEventType.OE_CXL_ACK)
        msg = f"SIM:Cancel ACK for {order_journal.order.security.sec_id}, order_id {order_journal.order.order_id} " \
              f"and side {order_journal.order.side}"
        add_to_texts(order_brief, msg)
        await underlying_create_order_journal_http(order_journal)

    @classmethod
    async def place_cxl_order(cls, order_id: str, side: Side | None = None, trading_sec_id: str | None = None,
                              system_sec_id: str | None = None, underlying_account: str | None = "trading-account"):
        """
        cls.simulate_reverse_path or not - always simulate cancel order's Ack/Rejects (unless configured for unack)
        when invoked form log analyzer - all params are passed as strings
        pydantic default conversion handles conversion - any util functions called should be called with
        explicit type convertors or pydantic object converted values
        """
        from Flux.CodeGenProjects.strat_executor.generated.FastApi.strat_executor_service_http_routes import (
            underlying_create_order_journal_http)
        security = Security(sec_id=system_sec_id, sec_type=SecurityType.TICKER)
        # query order
        order_brief = OrderBrief(order_id=order_id, security=security, side=side,
                                 underlying_account=underlying_account)
        msg = f"SIM:Cancel Request for {trading_sec_id}/{system_sec_id}, order_id {order_id} and side {side}"
        add_to_texts(order_brief, msg)
        # simulate cancel ack
        order_journal = OrderJournal(order=order_brief, order_event_date_time=DateTime.utcnow(),
                                     order_event=OrderEventType.OE_CXL)
        await underlying_create_order_journal_http(order_journal)

        if system_sec_id in cls.cxl_rej_symbol_to_bool_dict and cls.cxl_rej_symbol_to_bool_dict.get(system_sec_id):
            cls.cxl_rej_symbol_to_bool_dict[system_sec_id] = False
            await cls.process_cxl_rej(order_brief)
        else:
            await cls.process_cxl_ack(order_brief)

    @classmethod
    def trigger_kill_switch(cls) -> bool:
        portfolio_status_id = 1

        portfolio_status = \
            TradeSimulator.pair_strat_web_client.get_portfolio_status_client(portfolio_status_id)

        if not portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = True
            TradeSimulator.pair_strat_web_client.patch_portfolio_status_client(
                jsonable_encoder(portfolio_status_basemodel, by_alias=True, exclude_none=True))
            logging.debug("Portfolio_status - Kill Switch turned to True")
            return True
        else:
            logging.error("Portfolio_status - Kill Switch is already True")
            return False

    @classmethod
    def revoke_kill_switch_n_resume_trading(cls) -> bool:
        portfolio_status_id = 1
        portfolio_status = \
            TradeSimulator.pair_strat_web_client.get_portfolio_status_client(portfolio_status_id)

        if portfolio_status.kill_switch:
            portfolio_status_basemodel = PortfolioStatusBaseModel(_id=1)
            portfolio_status_basemodel.kill_switch = False
            TradeSimulator.pair_strat_web_client.patch_portfolio_status_client(
                jsonable_encoder(portfolio_status_basemodel, by_alias=True, exclude_none=True))
            logging.debug("Portfolio_status - Kill Switch turned to False")
            return True
        else:
            logging.error("Portfolio_status - Kill Switch is already False")
            return False
